#!/usr/bin/env python

import ConfigParser
from datetime import datetime
import os
from sqlalchemy import create_engine, MetaData, Table

config = ConfigParser.ConfigParser()
config.read(['os.cfg',os.path.expanduser('~/.os.cfg'),'/etc/os-maint/os.cfg'])

keystone_db_conn = config.get('KEYSTONE', 'db_connection')

engine = create_engine(keystone_db_conn, echo=True)
conn = engine.connect()
metadata = MetaData()
token = Table(
    'token',
    metadata,
    autoload=True,
    autoload_with=engine
)

conn.execute(token.delete(token.c.expires<=datetime.now()))
