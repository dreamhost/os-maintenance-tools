#!/usr/bin/env python

import ConfigParser
import argparse
import libvirt
import os
import sys

parser = argparse.ArgumentParser(description='Nova Auditor')
parser.add_argument('--clean', action='store_true', default=False, help='auto-clean orphans')
parser.add_argument('--hypervisor', action='append', default=[], help='specify a hypervisor to check')
args = parser.parse_args()

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
    nova_servers[hypervisor] = dict()
  nova_servers[hypervisor][name] = s

for s in nc.servers.list(True, {'all_tenants': '1'}):
  add_server(s)

for s in nc.servers.list(True, {'all_tenants': '1', 'deleted': '1'}):
  add_server(s)

if args.hypervisor:
  hosts = args.hypervisor
else:
  for hv in nc.hypervisors.list():
    hosts.append(hv.hypervisor_hostname)

for hypervisor in hosts:
  print 'Auditing {}'.format(hypervisor)
  try:
    conn = libvirt.open(connection_template.replace('$host', hypervisor))
  except:
    print "Connection to {} failed".format(hypervisor)
    conn = False
  if conn:
    for id in conn.listDomainsID():
      dom = conn.lookupByID(id)
      infos = dom.info()
      if hypervisor in nova_servers:
        if dom.name() not in nova_servers[hypervisor]:
          uuid = dom.UUIDString()
          print "name: {}, id: {} not found in first check of nova on {}".format(dom.name(), id, hypervisor)
          try:
            if nc.servers.get(uuid):
              print "name: {}, id: {} APPEARED after second check of nova on {}".format(dom.name(), id, hypervisor)
              continue
          except:
            pass
          if args.clean:
            print "auto-cleaning %s" % dom.name()
            try:
              dom.destroy()
            except libvirt.libvirtError:
              pass
        else:
          if nova_servers[hypervisor][dom.name()].status == 'DELETED':
            print "{} supposed to be deleted on {}".format(dom.name(), hypervisor)
            if args.clean:
              print "auto-cleaning %s" % dom.name()
              try:
                dom.destroy()
              except libvirt.libvirtError:
                pass
  
