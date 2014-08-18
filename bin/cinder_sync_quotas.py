#!/usr/bin/env python

import ConfigParser
import argparse
import os
from cinderclient.v1 import client
from sqlalchemy import create_engine, distinct, select, MetaData, Table

config = ConfigParser.ConfigParser()
config.read(['os.cfg',os.path.expanduser('~/.os.cfg'),'/etc/os-maint/os.cfg'])

parser = argparse.ArgumentParser(description='Cinder Quota Sync')
tenant_group = parser.add_mutually_exclusive_group(required=True)
tenant_group.add_argument('--tenant', action='append', default=[], help='Tenant(s) to work on')
tenant_group.add_argument('--all', action='store_true', default=False, help='Work on ALL tenants')
parser.add_argument('--verbose', '-v', action='count', default=0, help='Verbose')
args = parser.parse_args()

cinder_db_conn = config.get('CINDER', 'db_connection')
os_user_name = config.get('OPENSTACK', 'os_user_name')
os_password = config.get('OPENSTACK', 'os_password')
os_tenant_name = config.get('OPENSTACK', 'os_tenant_name')
os_auth_url = config.get('OPENSTACK', 'os_auth_url')
os_region_name = config.get('OPENSTACK', 'os_region_name')

if args.verbose >= 2:
  sql_echo = True
else:
  sql_echo = False

engine = create_engine(cinder_db_conn, echo=sql_echo)
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

if args.all:
  init_select = select([quota_usages.c.project_id]).distinct()
  projects = conn.execute(init_select)
  for project in projects:
    for p in project.items():
      usage[p[1]] = {'size': 0, 'volumes': 0}
else:
  for t in args.tenant:
    usage[t] = {'size': 0, 'volumes': 0}

volumes = []

if args.all:
  volumes = cc.volumes.list(True, {'all_tenants': '1'})
else:
  for t in args.tenant:
    for v in cc.volumes.list(True, {'all_tenants': '1', 'project_id': t}):
      volumes.append(v)

for vol in volumes:
  project_id = getattr(vol,'os-vol-tenant-attr:tenant_id')
  if project_id not in usage:
    usage[project_id] = {'size': 0, 'volumes': 0}
  if vol.status in ('available', 'in-use', 'creating'):
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
