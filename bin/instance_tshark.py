#!/usr/bin/env python

from subprocess import call
import sys
import xml.etree.ElementTree as ET

if len(sys.argv) == 2:
  instance_id = sys.argv[1]
else:
  print "Usage: %s [instance_id]" % sys.argv[0]
  sys.exit(1)
tree = ET.parse('/etc/libvirt/qemu/' + instance_id + '.xml')
root = tree.getroot()
for dev in root.iter('devices'):
  for iface in dev.findall('interface'):
    tgt = iface.find('target')
    tap = tgt.get('dev')
    tshark = 'tshark -w /var/log/%s-%s -b filesize:1024 -b files:5 -i %s' % (instance_id, tap, tap)
    if call(['tmux', 'has-session', '-t', '%s-%s' % (instance_id, tap)]) == 0:
      print "Already running a dump on %s-%s" % (instance_id, tap)
      continue
    else:
      call(['tmux', 'new', '-d', '-s', '%s-%s' % (instance_id, tap), tshark])
