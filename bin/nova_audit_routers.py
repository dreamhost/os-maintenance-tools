#!/usr/bin/env python

import ConfigParser
import argparse
import os
import sys
from novaclient import client as novaclient
from neutronclient.v2_0 import client as neutronclient
from keystoneclient.v2_0 import client as keystoneclient

parser = argparse.ArgumentParser(description='Nova Auditor')
parser.add_argument('--clean', action='store_true', default=False,
                    help='auto-clean orphans')
parser.add_argument('--os-tenant-name', action='store',
                    default=None, dest="OS_TENANT_NAME",
                    help='OpenStack tenant name used for authentication')
parser.add_argument('--os-username', action='store',
                    default=None, dest="OS_USERNAME",
                    help='OpenStack username used for authentication')
parser.add_argument('--os-password', action='store',
                    default=None, dest="OS_PASSWORD",
                    help='OpenStack user password used for authentication')
parser.add_argument('--os-auth-url', action='store',
                    default=None, dest="OS_AUTH_URL",
                    help='OpenStack auth-url used for authentication')
args = parser.parse_args()


def get_os_vars():
    """Return a dict of variables used for OpenStack client authentication.
    This will determine the values first by checking ~/.os.cfg, then next by
    checking the OS_* environment variables, and finally, by checking CLI
    params.  Each step will overwrite the previous values learned."""

    os_vars = {'OS_PASSWORD': None,
               'OS_AUTH_URL': None,
               'OS_USERNAME': None,
               'OS_TENANT_NAME': None,
               'OS_SERVICE_TENANT_NAME': 'service'}

    for os_var in os_vars.keys():
        try:
            config = ConfigParser.ConfigParser()
            config.read(['os.cfg', os.path.expanduser('~/.os.cfg')])
            os_vars[os_var] = config.get('OPENSTACK', os_var.lower())
        except (ConfigParser.NoOptionError, ConfigParser.NoSectionError):
            continue

    for os_var in os_vars.keys():
        try:
            os_vars[os_var] = os.environ[os_var]
        except KeyError:
            continue

    for os_var in os_vars.keys():
        try:
            if getattr(args, os_var):
                os_vars[os_var] = getattr(args, os_var)
        except AttributeError:
            continue

    for os_var in os_vars.keys():
        if not os_vars[os_var]:
            os_vars[os_var] = raw_input('%s: ' % os_var)

    return os_vars


def get_service_tenant_id(osvars):
    """Return the ID of the service tenant"""
    keystonec = keystoneclient.Client(
        username=osvars['OS_USERNAME'],
        password=osvars['OS_PASSWORD'],
        tenant_name=osvars['OS_TENANT_NAME'],
        auth_url=osvars['OS_AUTH_URL'])

    return keystonec.tenants.find(name=osvars['OS_SERVICE_TENANT_NAME']).id


def get_routers_list(osvars):
    """Returns a list of neutron IDs as reported by neutron"""

    neutronc = neutronclient.Client(username=osvars['OS_USERNAME'],
                                    password=osvars['OS_PASSWORD'],
                                    tenant_name=osvars['OS_TENANT_NAME'],
                                    auth_url=osvars['OS_AUTH_URL'])

    routers = neutronc.list_routers().get('routers', [])

    router_ids = []
    for r in routers:
        router_ids.append(r.get('id', ''))

    return router_ids


def list_all_vms(osvars):
    """Returns a listing of all VM objects as reported by Nova"""

    novac = novaclient.Client('2',
                              osvars['OS_USERNAME'],
                              osvars['OS_PASSWORD'],
                              osvars['OS_TENANT_NAME'],
                              osvars['OS_AUTH_URL'],
                              service_type="compute")

    return novac.servers.list(True, {'all_tenants': '1'})


def check_vm_is_router(router_ids, vm):
    vm_id = vm.name[3:]
    stray = 0
    if vm_id not in router_ids:
        stray = 1
        print "stray: %s (rid %s) created %s on %s (status: %s, %s)" % (
            vm.id, vm_id, vm.created,
            vm._info['OS-EXT-SRV-ATTR:hypervisor_hostname'],
            vm.status, vm._info['OS-EXT-STS:task_state'])
        if args.clean:
            print "Cleaning"
            # novac.servers.delete(vm.id)

    return stray


def main():
    """The main loop"""
    osvars = get_os_vars()

    service_tenant_id = get_service_tenant_id(osvars)
    router_ids = get_routers_list(osvars)

    strays = 0
    for vm in list_all_vms(osvars):
        if vm.tenant_id == service_tenant_id:
            strays = strays + check_vm_is_router(router_ids, vm)

    if strays > 1:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
