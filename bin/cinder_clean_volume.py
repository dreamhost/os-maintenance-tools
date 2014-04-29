#!/usr/bin/env python

import ConfigParser
import os
from cinderclient.v1 import client

config = ConfigParser.ConfigParser()
config.read(['os.cfg',os.path.expanduser('~/.os.cfg'),'/etc/os-maint/os.cfg'])

cinder_db_conn = config.get('CINDER', 'db_connection')
os_user_name = config.get('OPENSTACK', 'os_user_name')
os_password = config.get('OPENSTACK', 'os_password')
os_tenant_name = config.get('OPENSTACK', 'os_tenant_name')
os_auth_url = config.get('OPENSTACK', 'os_auth_url')
os_region_name = config.get('OPENSTACK', 'os_region_name')

cc = client.Client(os_user_name, os_password, os_tenant_name, os_auth_url, service_type='volume')
volumes = []

for vol in cc.volumes.list(True, {'all_tenants': '1'}):
  if vol.status in ('error', 'error_deleting'):
    print vol.id + " " + vol.status
    volumes.append(vol)

dialog = "Delete all errored volumes? (Y/N)"
try: 
  confirm = raw_input(dialog)
except NameError: 
  confirm = input(dialog)

if ( confirm.lower() == 'y' ):
  for vol in volumes:
    print "Deleting " + vol.id
    if not vol.force_delete():
      print "Error Deleting " + vol.id
