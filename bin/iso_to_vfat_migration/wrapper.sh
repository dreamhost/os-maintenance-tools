#!/bin/bash

set -xe

for i in `virsh list | awk 'NR>2{print $2}'`; do
    ./iso_to_vfat.sh $i
done
