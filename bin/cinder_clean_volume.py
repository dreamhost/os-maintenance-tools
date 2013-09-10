#!/usr/bin/python

import ConfigParser
import os
from sqlalchemy import create_engine, select, MetaData, Table

config = ConfigParser.ConfigParser()
config.read(['os.cfg',os.path.expanduser('~/.os.cfg'),'/etc/os-maint/os.cfg'])

cinder_db_conn = config.get('CINDER', 'db_connection')

engine = create_engine(cinder_db_conn, echo=True)
conn = engine.connect()
metadata = MetaData()

volumes = Table(
    'volumes',
    metadata,
    autoload=True,
    autoload_with=engine
)

quota_usages = Table(
    'quota_usages',
    metadata,
    autoload=True,
    autoload_with=engine
)

sel = select([volumes])
result = conn.execute(sel)
for vol in result:
  if vol.id == 'fb65fd79-96bb-4fd4-8cfa-5cc7a85cf324':
    print vol.id + " " + str(vol.size)
    conn.execute(volumes.update().
                 where(volumes.c.id==vol.id).
                 values(status='deleted')
                 )
    conn.execute(quota_usages.update().
                 where(quota_usages.c.project_id==vol.project_id).
                 where(quota_usages.c.resource=='gigabytes').
                 values(in_use=quota_usages.c.in_use - vol.size)
                 )
    conn.execute(quota_usages.update().
                 where(quota_usages.c.project_id==vol.project_id).
                 where(quota_usages.c.resource=='volumes').
                 values(in_use=quota_usages.c.in_use - 1)
                 )
