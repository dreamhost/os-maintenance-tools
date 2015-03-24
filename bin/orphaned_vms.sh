#!/bin/bash

# your OpenStack creds are expected to be in your environment variables

vm_tenants=$(mktemp)
keystone_tenants=$(mktemp)

echo -en "Retrieving list of all VMs...\r"
nova list --all-tenants --fields tenant_id | tail -n +4 | awk '{print $4}' | sort -u > $vm_tenants

echo -en "Retrieving list of all tenants...\r"
keystone tenant-list | tail -n +4 | awk '{print $2}' | sort -u > $keystone_tenants

echo -en "Comparing outputs to locate orphaned VMs....\r"
iter=0
for tenant_id in `comm --nocheck-order -13 $keystone_tenants $vm_tenants`; do
	if [[ $iter == 0 ]]; then
		nova list --all-tenants --tenant=$tenant_id --fields tenant_id,name,status,created,updated | head -n -1
		let "iter++"
	else
		nova list --all-tenants --tenant=$tenant_id --fields tenant_id,name,status,created,updated | tail -n +4 | head -n -1
	fi
done

rm $keystone_tenants $vm_tenants
