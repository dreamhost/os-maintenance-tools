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

Under some circumstances, because of the way the neutron allocate and
deallocated ips, it may be needed to run the script two times.
The script allocate and release all the ips in the pool one-by-one
taking track of them, so when an already allocated ip is extracted
from the pool, the script knows the all the ips have been seen and
that it can stop. Let say that the ip the script starts allocating
from is 172.15.77.32 and that for some reason ip 172.15.74.0(that
should be reserved) has been allocated and released, in that case
that ip won't be recycled untill the pool will be exhausted and
so won't be reserved by this script untill the next run.
For this reason we should run this script two times and check
that all the wanted ips have been reserved(The script's output included
the reserved ips in the current run and all the ips allocated in the
tenant).
Note(rods): the script doesn't remove reserved ips already allocated
so it's safe to run it more then once.

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

    allocated = {}
    reserved = []

    special_ips = ['0', '1', '255']
    keep_going = True

    print
    print 'Start ',
    try:
        while keep_going:

            f_ip = neutron_client.create_floatingip(body).get('floatingip')
            # we allocate and release all the ips in the pool one-by-one,
            # so we can't count on the pool to be exhausted to know when
            # the work is done. Let's keep a dict of seen ips and stop
            # at the first ip seen more than once
            # Note(rods):
            #   We use a dict(with the ips as keys because) instead of just
            #   a list of ips because the search for and element in the dict
            #   should be much faster

            if f_ip['floating_ip_address'] in allocated:
                keep_going = False

            # keep track of the seen ips
            allocated[f_ip['floating_ip_address']] = f_ip

            if f_ip['floating_ip_address'].split('.')[-1] in special_ips:
                reserved.append(f_ip)
                continue
            for _ in range(3):
                try:
                    neutron_client.delete_floatingip(f_ip['id'])
                    break
                except Exception as err:
                    continue
            else:
                print ('Floating ip %s has not been removed' %
                       f_ip['floating_ip_address'])

            print_dot(len(allocated))

        print 'Done'

    except Exception as err:

        print
        exc_type, exc_value, exc_tb = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_tb)

        print '\nCleaning up all the allocated floaters ',

        for f_ip in allocated.values():
            # don't remove reserved ips already allocated
            if f_ip['floating_ip_address'].split('.')[-1] not in special_ips:
                for _ in range(3):
                    try:
                        neutron_client.delete_floatingip(f_ip['id'])
                        print_dot(len(allocated))
                        break
                    except neutron_exceptions.NotFound as err:
                        break
                    except Exception as err:
                        continue
                else:
                    print ('Floating ip %s has not been removed' %
                           f_ip['floating_ip_address'])

        print 'Done'

        return 1

    print '\nFloaters allocated/deallocated %d' % len(allocated)
    print 'Floaters reserved: %d' % len(reserved)

    if reserved:
        print '\nReserved ips'
        reserved.sort()
        for f_ip in reserved:
            print f_ip['floating_ip_address']

    print '\nIps in the tenant:'
    for f_ip in neutron_client.list_floatingips().get('floatingips', []):
        print f_ip['floating_ip_address']


if __name__ == '__main__':
    sys.exit(main())
