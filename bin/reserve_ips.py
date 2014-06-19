#!/usr/bin/env python

""" Allocate reserved IP's to a given tenant

If a subnet is larger than /24, neutron doesn't reserve special IPs
(.0, .1 and .255). In the case of a public network of an OpenStack
deployment that means we are distributing floating ips that may not
work properly. Let's workaround this problem allocating those special
IPs in a tenant created for this purpose.

To run this script, the following environment variables need to be
defined in the shell

  - OS_USERNAME: openstack user that own the tenant where ips will be allocated
  - OS_PASSWORD: password for the user
  - OS_TENANT_NAME: name of the tenant ips are going to be allocated
  - OS_PUBLIC_NET_ID: id of the net to reserve the ips from

"""

import os
import sys
import traceback

import neutronclient.common.exceptions as neutron_exceptions
from neutronclient.v2_0 import client as neutron_client


def get_neutron_client():
    """ Instanciate the neutron client """
    return neutron_client.Client(
        username=os.getenv('OS_USERNAME'),
        password=os.getenv('OS_PASSWORD'),
        tenant_name=os.getenv('OS_TENANT_NAME'),
        auth_url=os.getenv('OS_AUTH_URL'),
    )


def print_dot(index, steps=20):
    """ Print a dot at every steps value """
    if index % steps == 0:
        print '\b.',
        sys.stdout.flush()


def main():
    neutron_client = get_neutron_client()
    public_network_id = os.getenv('OS_PUBLIC_NET_ID')

    body = {'floatingip': {'floating_network_id': public_network_id}}

    allocated = 0

    print '\nAllocating temporary floating ips ',

    try:
        while True:
            neutron_client.create_floatingip(body).get('floatingip')
            allocated += 1
            print_dot(allocated)
    except neutron_exceptions.IpAddressGenerationFailureClient:
        print 'Done'
        print '\nFloaters allocated: %d' % allocated
    except Exception as err:
        print
        exc_type, exc_value, exc_tb = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_tb)

        print '\nFloaters allocated: %d' % allocated
        print '\nCleaning up all the allocated floaters',

        deallocated = 0

        for ip in neutron_client.list_floatingips().get('floatingips', []):
            for i in range(3):
                try:
                    neutron_client.delete_floatingip(ip['id'])
                    deallocated += 1
                    print_dot(deallocated)
                    break
                except Exception as err:
                    continue
            else:
                print ('Floating ip %s has not been removed' %
                       ip['floating_ip_address'])

        print 'Done'

        print '\nFloaters deallocated: %d' % deallocated
        return 1


    print '\nDeallocate temporary floating ips ',

    deallocated = 0
    reserved = []

    for ip in neutron_client.list_floatingips().get('floatingips', []):
        if ip['floating_ip_address'].split('.')[-1] in ['0', '1', '255']:
            reserved.append(ip)
            continue
        for i in range(3):
            try:
                neutron_client.delete_floatingip(ip['id'])
                deallocated += 1
                print_dot(deallocated)
                break
            except Exception as err:
                continue
            else:
                print ('Floating ip %s has not been removed' %
                       ip['floating_ip_address'])
    print 'Done'

    print '\nFloaters deallocated: %d' % deallocated
    print 'Floaters reserved: %d' % len(reserved)

    if reserved:
        print '\nReserved ips'
        reserved.sort()
        for ip in reserved:
            print ip['floating_ip_address']

    print ''

if __name__ == '__main__':
    sys.exit(main())
