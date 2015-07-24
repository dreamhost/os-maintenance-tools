#!/bin/bash

# example usage:
# sh ./genarate_vm_mysql_cleanup.sh 95be2787-2e51-4a8e-9210-09da21dce138

echo delete from block_device_mapping where instance_uuid  = \'$1\'\;
echo delete from instance_actions_events where action_id in \(select id from instance_actions where instance_uuid = \'$1\'\)\;
echo delete from instance_actions where instance_uuid = \'$1\'\;
echo delete from instance_actions where instance_uuid = \'$1\'\;
echo delete from instance_extra where instance_uuid = \'$1\'\;
echo delete from instance_info_caches where instance_uuid =\'$1\'\;
echo delete from instance_faults where instance_uuid = \'$1\'\;
echo delete from instance_metadata where instance_uuid = \'$1\'\;
echo delete from instance_system_metadata where instance_uuid = \'$1\'\;
echo delete from instances where uuid = \'$1\'\;
