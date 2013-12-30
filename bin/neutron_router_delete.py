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
    router = sys.argv[1]
    my_router = nc.show_router(router).get('router')
#  print my_router.values()
    print my_router.get('status')
    if 'ports' in my_router.keys:
        print "We have ports"
        ports = my_router.get('ports')
        for port in ports:
            print port.get('id')
    else:
        print "Router has no ports, continuing"
