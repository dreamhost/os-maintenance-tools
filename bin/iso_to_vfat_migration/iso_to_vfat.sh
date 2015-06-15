#!/bin/bash

set -ex

# $1 needs to be the virsh instance name
instance_name=$1

generate_iso_disk_xml () {
echo "<disk type='file' device='cdrom'>
  <driver name='qemu' type='raw' cache='none'/>
  <target dev='hdd' bus='ide'/>
  <readonly/>
  <address type='drive' controller='0' bus='1' target='0' unit='1'/>
</disk>"
}

generate_vfat_disk_xml () {
echo "<disk type='network' device='disk'>
  <driver name='qemu' type='raw' cache='none'/>
  <auth username='norse-volumes'>
    <secret type='ceph' uuid='$3'/>
  </auth>
  <source protocol='rbd' name='$1'>
    <host name='$2' port='6789'/>
  </source>
  <target dev='vdz' bus='virtio'/>
</disk>"
}

cdrom_info=$(virsh domblklist $instance_name | grep "disk.config")
device=$(echo $cdrom_info | awk '{print $1}')
path=$(echo $cdrom_info | awk '{print $2}')
if [[ "$device" =~ ^hd.* ]]; then
    if [[ "$path" =~ ^/.* ]]; then
        instance_tmp_dir="/tmp/iso_to_vfat/$instance_name"
        isomntdir="$instance_tmp_dir/iso_mount"
        vfatmntdir="$instance_tmp_dir/vfat_mount"
        vfatfile="$path"
        vfatxmlfile="$instance_tmp_dir/vfat.xml"
        isoxmlfile="$instance_tmp_dir/iso.xml"
        mkdir -p $isomntdir $vfatmntdir
        virsh change-media $instance_name $device --eject --force
        generate_iso_disk_xml > $isoxmlfile
        virsh detach-device $instance_name $isoxmlfile --config
        mount -o loop $path $isomntdir
        rm $path
        dd if=/dev/zero of=$vfatfile bs=1024 count=0 seek=1024
        mkfs.vfat $vfatfile
        mount $vfatfile $vfatmntdir
        cp -rp $isomntdir/* $vfatmntdir
	umount $isomntdir
        umount $vfatmntdir
        # nova, with the config-drive patch, might copy the config-drive to
        # ceph for us. if not, we'll need to do it ourselves.
	rbd_object_name=$(./copy_to_rbd.py $path)
        mon_host_ip=$(grep "mon host" /etc/ceph/ceph.conf | cut -d'[' -f2 | cut -d']' -f1)
        rm $path
	# ceph_uuid needs to be set to something legit. check the rbd disk devices on
	# existing VMs to see what UUID they have, and paste it here
	ceph_uuid=0
        generate_vfat_disk_xml $rbd_object_name $mon_host_ip $ceph_uuid > $vfatxmlfile
        virsh attach-device $instance_name $vfatxmlfile --persistent
    fi
fi
