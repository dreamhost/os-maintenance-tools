#!/usr/bin/env python

import sys          # reads command-line args
import ConfigParser
import os

os_user_name = os.getenv('OS_USERNAME') 
os_password = os.getenv('OS_PASSWORD') 
os_tenant_name = os.getenv('OS_TENANT_NAME')
os_auth_url = os.getenv('OS_AUTH_URL')

from neutronclient.v2_0 import client as neutronclient
nc = neutronclient.Client(username=os_user_name,
                   password=os_password,
                   tenant_name=os_tenant_name,
                   auth_url=os_auth_url)

pubnet = sys.argv[1]

#print dir(nc)

subnets = []
subnet_cidr = {}
subnet_usage = {}
used_ips = {}

for pubnet in nc.list_networks(name=pubnet).get('networks'):
  for s in pubnet.get('subnets'):
    subnet = nc.list_subnets(id=s).get('subnets')[0]
    if subnet.get('ip_version') == 4:
      subnet_cidr[s] = subnet.get('cidr')
      subnets.append(s)

for p in nc.list_ports().get('ports'):
  for ip in p.get('fixed_ips'):
    subnet_id = ip.get('subnet_id')
    if subnet_id in subnets:
      print ip
      try:
        subnet_usage[subnet_id] += 1
      except KeyError:
        subnet_usage[subnet_id] = 1
      try:
        used_ips[subnet_id].append(ip.get('ip_address'))
      except KeyError:
        used_ips[subnet_id] = [ip.get('ip_address')]


print "Totals Used Per Subnet:"

for sn in subnet_usage:
  print "%s: %s" % (subnet_cidr[sn], subnet_usage[sn])

print "IPs in use:"

for sn in used_ips:
  for ip in used_ips[sn]:
    print ip + " - Private Customer - DreamHost LLC"
