#!/bin/sh

POOL=$1
VOLUME=$2
if [ -z "$POOL" ]; then
  echo need a pool
  exit 2
fi
if [ -z "$VOLUME" ]; then
  echo need a volume
  exit 2
fi
export POOL
export VOLUME
rados listwatchers -p $POOL rbd_header.$(rbd info -p $POOL volume-$VOLUME | grep block_name_prefix | awk -F. '{print $2}')
