#!/usr/bin/env python

import sys          # reads command-line args
import argparse
import time
import ConfigParser
import os

config = ConfigParser.ConfigParser()
config.read(['/etc/os-maint/os.cfg'
             'os.cfg',
             os.path.expanduser('~/.os.cfg')
             ])

os_user_name = config.get('OPENSTACK', 'os_user_name')
os_password = config.get('OPENSTACK', 'os_password')
os_tenant_name = config.get('OPENSTACK', 'os_tenant_name')
os_auth_url = config.get('OPENSTACK', 'os_auth_url')
os_region_name = config.get('OPENSTACK', 'os_region_name')

parser = argparse.ArgumentParser(description='replug router')
tenant_group = parser.add_mutually_exclusive_group(required=True)
tenant_group.add_argument('--tenant',
                          action='store',
                          default=[],
                          help='Tenant to work on')
args = parser.parse_args()

from keystoneclient.v2_0 import client as kclient
keystone = kclient.Client(username=os_user_name,
                          password=os_password,
                          tenant_name=os_tenant_name,
                          auth_url=os_auth_url)

from neutronclient.v2_0 import client as neutronclient
nc = neutronclient.Client(username=os_user_name,
                          password=os_password,
                          tenant_name=os_tenant_name,
                          auth_url=os_auth_url)

from novaclient.v1_1 import client as novaclient
novac = novaclient.Client(os_user_name,
                          os_password,
                          os_tenant_name,
                          os_auth_url,
                          service_type="compute")


def get_floaters_assigned():
    return nc.list_floatingips(tenant_id=tenant_id)['floatingips']


def get_router_detail():
    for router in nc.list_routers(tenant_id=tenant_id).get('routers'):
        return nc.show_router(router['id'])


def get_router_ports():
    router = get_router_detail()
    return router['router'].get('ports', [])


def get_router_port_by_owner(owner=None):
    if owner is None:
        return
    ports = get_router_ports()
    for p in ports:
        if p['device_owner'] == owner:
            return p
    # didn't find a port
    return


# main
tenant_id = None
for t in keystone.tenants.list():
    if t.id == args.tenant:
        tenant_id = args.tenant

if tenant_id is None:
    print "Could not find tenant %s" % args.tenant
    sys.exit(1)

my_router = get_router_detail()
print "Router: %s" % my_router['router']['id']

floaters = get_floaters_assigned()
for f in floaters:
    floating_id = f.get("id")
    floating_ip = f.get("floating_ip_address")
    port_id = f.get("port_id")
    print "%s %s %s" % (floating_id, floating_ip, port_id)
    nc.update_floatingip(floating_id, {
        'floatingip': {'port_id': None}
        })


print "Making sure floaters are unallocated before proceeding (infinite loop)"
while True:
    allocated = 0
    for fip in get_floaters_assigned():
        if fip.get("port_id") is not None:
            allocated += 1

    if allocated == 0:
        print "All floaters are unallocated"
        break
    else:
        continue


print "clear router gateway and remove gw port"
try:
    rd = get_router_detail()
    router = rd['router']
    nc.remove_gateway_router(router['id'])
except Exception as err:
    print "failed removing router gateway %s" % err


print "wait for the router_gateway interface to be created by the rug (infinite loop)"
while True:
    try:
        router_gw_port = get_router_port_by_owner( owner='network:router_gateway')
        if router_gw_port:
            break
    except:
        continue
    time.sleep(3)

tenant_port = get_router_port_by_owner(owner='network:router_interface')
if tenant_port is not None:
    print "delete the tenant interface"
    try:
        rd = get_router_detail()
        router = rd['router']
        tenant_port = get_router_port_by_owner(
            owner='network:router_interface')
        nc.remove_interface_router(
            router['id'],
            {'port_id': tenant_port['id']})
    except Exception as err:
        raise err

    print "add tenant interface to v4/v6 subnets"
    try:
        rd = get_router_detail()
        router = rd['router']
        subnet_id = None
        for fip in tenant_port['fixed_ips']:
            if len(fip['ip_address'].split('.')) == 4:
                subnet_id = fip['subnet_id']

        nc.add_interface_router(router['id'], {'subnet_id': subnet_id})
        new_tenant_port = get_router_port_by_owner(owner='network:router_interface') 
        fixed_ips = []
        for sub in nc.list_subnets(tenant_id=tenant_id)['subnets']:
            fixed_ips.append({'subnet_id': sub['id'], 'ip_address': sub['gateway_ip']})

        port_body = {
            'fixed_ips': fixed_ips,
            'mac_learning_enabled': True,
            'port_security_enabled': False,
            'security_groups': None
        }
        nc.update_port(new_tenant_port['id'], {'port': port_body})
    except Exception as err:
        print err
else:
    print "no tenant port"

print "restore floatingip assignments"

# go back and add all the floaters as they were before
for f in floaters:
    floating_id = f.get("id")
    floating_ip = f.get("floating_ip_address")
    fixed_ip = f.get("fixed_ip_address")
    port_id = f.get("port_id")
    print "%s %s %s" % (floating_id, floating_ip, port_id)
    nc.update_floatingip(floating_id, {
        'floatingip': {'port_id': port_id, 'fixed_ip_address': fixed_ip}
        })
