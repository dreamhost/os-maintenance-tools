#!/usr/bin/env python

import sys          # reads command-line args
import ConfigParser
import os

config = ConfigParser.ConfigParser()
config.read(['os.cfg',
    os.path.expanduser('~/.os.cfg'),
    '/etc/os-maint/os.cfg'])

os_user_name = config.get('OPENSTACK', 'os_user_name')
os_password = config.get('OPENSTACK', 'os_password')
os_tenant_name = config.get('OPENSTACK', 'os_tenant_name')
os_auth_url = config.get('OPENSTACK', 'os_auth_url')
os_region_name = config.get('OPENSTACK', 'os_region_name')

broken_n_sgroups = []
known_tids = []

from neutronclient.v2_0 import client as neutronclient
nc = neutronclient.Client(username=os_user_name,
                   password=os_password,
                   tenant_name=os_tenant_name,
                   auth_url=os_auth_url)


from keystoneclient.v2_0 import client as kclient
keystone = kclient.Client(username=os_user_name,
                         password=os_password,
                         tenant_name=os_tenant_name,
                         auth_url=os_auth_url
                         )
for tenant in keystone.tenants.list():
  known_tids.append(tenant.id)

security_groups = nc.list_security_groups()
for n_sgroup in security_groups.get('security_groups'):
  tid = n_sgroup.get('tenant_id')
  if tid not in known_tids:
    print "stray sgroup %s (tenant %s DNE)" % (n_sgroup.get('id'), tid)

