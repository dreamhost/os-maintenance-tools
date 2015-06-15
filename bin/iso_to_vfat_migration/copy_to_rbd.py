#!/usr/bin/env python

import sys
import rbd
import rados
import ConfigParser

# disk_name should be something like:
# /var/lib/nova/instances/6b43471e-0f50-415a-ba3b-12ffd3f5fc53/disk.config
#
# we'll then split this into what we really want, which will look like:
# 6b43471e-0f50-415a-ba3b-12ffd3f5fc53_disk.config
#
# this will be used to name the object in ceph
config_drive = sys.argv[1]
tmp_disk_name = config_drive.split('/')
disk_name = '_'.join(tmp_disk_name[-2:])

config = ConfigParser.ConfigParser()
config.read('/etc/nova/nova.conf')
rbd_id = config.get('libvirt', 'rbd_secret_uuid')
rbd_pool = config.get('libvirt', 'images_rbd_pool')
rbd_user = config.get('libvirt', 'rbd_user')

cluster = rados.Rados(rados_id=rbd_user, conffile='/etc/ceph/ceph.conf')
cluster.connect()
ioctx = cluster.open_ioctx(rbd_pool)

rbd_inst = rbd.RBD()
size = 1 * 1024 * 1024
rbd_inst.create(ioctx, disk_name, size)

image = rbd.Image(ioctx, disk_name)
image.write(open(config_drive).read(), 0)

print '%s/%s' % (rbd_pool, disk_name)
