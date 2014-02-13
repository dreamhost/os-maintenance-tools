#!/usr/bin/env python

import ConfigParser
import os
from cinderclient.v1 import client
from sqlalchemy import create_engine, select, MetaData, Table

config = ConfigParser.ConfigParser()
config.read(['os.cfg',os.path.expanduser('~/.os.cfg'),'/etc/os-maint/os.cfg'])

cinder_db_conn = config.get('CINDER', 'db_connection')
os_user_name = config.get('OPENSTACK', 'os_user_name')
os_password = config.get('OPENSTACK', 'os_password')
os_tenant_name = config.get('OPENSTACK', 'os_tenant_name')
os_auth_url = config.get('OPENSTACK', 'os_auth_url')
os_region_name = config.get('OPENSTACK', 'os_region_name')

engine = create_engine(cinder_db_conn, echo=True)
conn = engine.connect()
metadata = MetaData()
quota_usages = Table(
    'quota_usages',
     metadata,
     autoload=True,
     autoload_with=engine
)


cc = client.Client(os_user_name, os_password, os_tenant_name, os_auth_url, service_type='volume')
usage = dict()

for vol in cc.volumes.list(True, {'all_tenants': '1'}):
  if vol.status in ('available', 'in-use', 'creating'):
    project_id = getattr(vol,'os-vol-tenant-attr:tenant_id')
    if project_id not in usage:
      usage[project_id] = {'size': 0, 'volumes': 0}
    usage[project_id]['size'] += vol.size
    usage[project_id]['volumes'] += 1

for project in usage:
  print "project {} using {} gigs in {} volumes".format(project, usage[project]['size'], usage[project]['volumes'])
  update = quota_usages.update().\
            where(quota_usages.c.project_id == project).\
            where(quota_usages.c.resource == 'volumes').\
            values(in_use=usage[project]['volumes'])
  conn.execute(update)
  update = quota_usages.update().\
            where(quota_usages.c.project_id == project).\
            where(quota_usages.c.resource == 'gigabytes').\
            values(in_use=usage[project]['size'])
  conn.execute(update)
