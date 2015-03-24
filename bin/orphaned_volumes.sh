#!/bin/bash

# your OpenStack creds are expected to be in your environment variables

volume_ids=$(mktemp)
cinder_reported_tenants=$(mktemp)
keystone_tenants=$(mktemp)
final_report=$(mktemp)

echo -en "Retrieving list of all volumes...\r"
# oh cinder...
for volume in `cinder list --all-tenants | tail -n +4 | awk '{print $2}'`; do
	for line in `cinder show $volume | grep 'os-vol-tenant-attr:tenant_id\| id ' | awk '{print $4}'`; do
	    echo -en " $line" >> $volume_ids
        done
	echo "" >> $volume_ids
done 

# make a list of just tenant_ids as reported by cinder
awk '{print $2}' < $volume_ids | sort -u > $cinder_reported_tenants

echo -en "Retrieving list of all tenants...\r"
keystone tenant-list | tail -n +4 | awk '{print $2}' | sort -u > $keystone_tenants

echo "Comparing outputs to locate orphaned volumes...\r"
echo "+--------------------------------------+-----------------------------------+------------+--------------+------+--------+"
echo "|             volume_id                |            tenant_id              | created_at | display_name | size | status |"
echo "+--------------------------------------+-----------------------------------+------------+--------------+------+--------+"
for tenant_id in `comm --nocheck-order -13 $keystone_tenants $cinder_reported_tenants`; do
	for volume_id in `grep $tenant_id $volume_ids | awk '{print $1}'`; do
		echo -en "| $volume_id | $tenant_id |"
		for attr in `cinder show $volume_id | grep ' status \| size \| display_name \| created_at ' | awk '{print $4}'`; do
			echo -en " $attr |"
		done
		echo ""
	done
done

rm $keystone_tenants $volume_ids $cinder_reported_tenants $final_report
