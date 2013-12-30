#!/usr/bin/env python

import ConfigParser
import os
import sys

config = ConfigParser.ConfigParser()
config.read(['os.cfg',
    os.path.expanduser('~/.os.cfg'),
    '/etc/os-maint/os.cfg'])

os_user_name = config.get('OPENSTACK', 'os_user_name')
os_password = config.get('OPENSTACK', 'os_password')
os_tenant_name = config.get('OPENSTACK', 'os_tenant_name')
os_auth_url = config.get('OPENSTACK', 'os_auth_url')
os_region_name = config.get('OPENSTACK', 'os_region_name')

from neutronclient.v2_0 import client
nc = client.Client(username=os_user_name,
                   password=os_password,
                   tenant_name=os_tenant_name,
                   auth_url=os_auth_url)

if len(sys.argv) > 1:
    router_id = sys.argv[1]
    my_router = nc.show_router(router_id).get('router')
    my_router_id = my_router.get('id')
    print "router status is {}".format(my_router.get('status'))
    ports = []
    for port in nc.list_ports().get('ports'):
        print port.keys()
        device_id = port.get('device_id')
        if device_id == router_id:
            ports.append(port)
    if ports:
        print "We have ports"
        for port in ports:
            if port.get('device_owner') == 'network:router_gateway':
                print "skipping gateway port"
                continue
            port_id = port.get('id')
            my_port = nc.show_port(port_id).get('port')
            print "port {} status {}".format(port_id,
                    my_port.get('status'))
            info = {'id': my_router_id,
                    'port_id': port_id,
                    'tenant_id': my_router.get('tenant_id'),
                    }
            print port
            nc.remove_interface_router(my_router_id, info)
    else:
        print "Router has no ports, continuing"
    nc.delete_router(router_id)
else:
    print "Usage: neutron_router_delete.py [router_id]"
