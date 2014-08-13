#!/usr/bin/env python

import ConfigParser
import os
from novaclient.v1_1 import client
from sqlalchemy import create_engine, distinct, select, MetaData, Table, or_

config = ConfigParser.ConfigParser()
config.read(['os.cfg',os.path.expanduser('~/.os.cfg'),'/etc/os-maint/os.cfg'])

cinder_db_conn = config.get('NOVA', 'db_connection')
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
instances = Table(
    'instances',
    metadata,
    autoload=True,
    autoload_with=engine
)

nc = client.Client(os_user_name, os_password, os_tenant_name, os_auth_url, service_type='compute')
usage = dict()

usage_select = select([quota_usages])
initial_usages = conn.execute(usage_select)
initial_usage = dict()
for u in initial_usages:
  if u.project_id not in initial_usage:
    initial_usage[u.project_id] = dict()
  if u.user_id not in initial_usage[u.project_id]:
    initial_usage[u.project_id][u.user_id] = {'instances': 0, 'cores': 0, 'ram': 0}
  initial_usage[u.project_id][u.user_id][u.resource] = u.in_use

init_select = select([quota_usages.c.project_id, quota_usages.c.user_id]).distinct()
qu = conn.execute(init_select)
for q in qu:
  usage[q.project_id] = dict()
  usage[q.project_id][q.user_id] = {'instances': 0, 'cores': 0, 'ram': 0}

## These are the only states that should count against one's quota
instance_select = select([instances]).where(or_(instances.c.vm_state == 'active',
                                                instances.c.vm_state == 'suspended',
                                                instances.c.vm_state == 'paused',
                                                instances.c.vm_state == 'shutoff'))
instances = conn.execute(instance_select)
for i in instances:
  project_id = i.project_id
  if project_id not in usage:
    usage[project_id] = dict()
  if i.user_id not in usage[project_id]:
    usage[project_id][i.user_id] = {'instances': 0, 'cores': 0, 'ram': 0}
  usage[project_id][i.user_id]['ram'] += getattr(i, 'memory_mb')
  usage[project_id][i.user_id]['instances'] += 1
  usage[project_id][i.user_id]['cores'] += i.vcpus

for project in usage:
  for user in usage[project]:
    if project not in initial_usage:
      initial_usage[project] = dict()
    if user not in initial_usage[project]:
      initial_usage[project][user] = {'instances': 0, 'cores': 0, 'ram': 0}
    if (initial_usage[project][user]['ram'] != usage[project][user]['ram'] or
      initial_usage[project][user]['cores'] != usage[project][user]['cores'] or
      initial_usage[project][user]['instances'] != usage[project][user]['instances']):
      print "OLD: project {}, user {} using {} megabytes, {} cores in {} instances".format(project, user, initial_usage[project][user]['ram'], initial_usage[project][user]['cores'], initial_usage[project][user]['instances'])
      print "NEW: project {}, user {} using {} megabytes, {} cores in {} instances".format(project, user, usage[project][user]['ram'], usage[project][user]['cores'], usage[project][user]['instances'])
      update = quota_usages.update().\
            where(quota_usages.c.project_id == project).\
            where(quota_usages.c.user_id == user).\
            where(quota_usages.c.resource == 'instances').\
            values(in_use=usage[project][user]['instances'])
      conn.execute(update)
      update = quota_usages.update().\
            where(quota_usages.c.project_id == project).\
            where(quota_usages.c.user_id == user).\
            where(quota_usages.c.resource == 'cores').\
            values(in_use=usage[project][user]['cores'])
      conn.execute(update)
      update = quota_usages.update().\
            where(quota_usages.c.project_id == project).\
            where(quota_usages.c.user_id == user).\
            where(quota_usages.c.resource == 'ram').\
            values(in_use=usage[project][user]['ram'])
      conn.execute(update)
    else:
      print "project {}, user {} already synced".format(project, user)
