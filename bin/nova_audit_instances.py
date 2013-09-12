#!/usr/bin/env python

import ConfigParser
import libvirt
import os
import sys
from sqlalchemy import create_engine, select, MetaData, Table

config = ConfigParser.ConfigParser()
config.read(['os.cfg',os.path.expanduser('~/.os.cfg'),'/etc/os-maint/os.cfg'])

os_user_name = config.get('OPENSTACK', 'os_user_name')
os_password = config.get('OPENSTACK', 'os_password')
os_tenant_name = config.get('OPENSTACK', 'os_tenant_name')
os_auth_url = config.get('OPENSTACK', 'os_auth_url')
os_region_name = config.get('OPENSTACK', 'os_region_name')
connection_template = config.get('NOVA', 'libvirt_connection_template')

from novaclient.v1_1 import client
nc = client.Client(os_user_name, os_password, os_tenant_name, os_auth_url, service_type="compute")
hosts = []

nova_servers = dict()

def add_server(server):
  name = s._info['OS-EXT-SRV-ATTR:instance_name']
  hypervisor = s._info['OS-EXT-SRV-ATTR:hypervisor_hostname']
  if hypervisor not in nova_servers:
    nova_servers[hypervisor] = {} 
  nova_servers[hypervisor][name] = s

for s in nc.servers.list(True, {'all_tenants': '1'}):
  add_server(s)

for s in nc.servers.list(True, {'all_tenants': '1', 'deleted': '1'}):
  add_server(s)

if len(sys.argv) > 1:
  hosts = [sys.argv[1]]
else:
  for hv in nc.hypervisors.list():
    hosts.append(hv.hypervisor_hostname)

for hypervisor in hosts:
  print 'Auditing {}'.format(hypervisor)
  conn = libvirt.open(connection_template.replace('$host', hypervisor))

  for id in conn.listDomainsID():
    dom = conn.lookupByID(id)
    infos = dom.info()
    if hypervisor in nova_servers:
      if dom.name() not in nova_servers[hypervisor]:
        print "{} not found in nova on {}".format(dom.name(), hypervisor)
      else:
        if nova_servers[hypervisor][dom.name()].status == 'DELETED':
          print "{} supposed to be deleted on {}".format(dom.name(), hypervisor)

