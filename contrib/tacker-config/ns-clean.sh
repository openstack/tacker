#!/bin/bash
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

echo "Deleting network service NS1, NS2"
for ns in NS1 NS2; do
    network_service_id=$(openstack ns list | grep $ns | awk '{print $2}')
    if [ -n "$network_service_id" ]; then
        openstack ns delete $network_service_id
    fi
done

sleep 5

echo "Deleting network service descriptor NSD-template"
nsd_id=$(openstack ns descriptor list | grep NSD-template | awk '{print $2}')
if [ -n "$nsd_id" ]; then
    openstack ns descriptor delete $nsd_id
fi

echo "Deleting vnf descriptors"
for vnfd_name in sample-tosca-vnfd1 sample-tosca-vnfd2 sample-vnfd1 sample-vnfd2; do
    vnfd_id=$(openstack vnf descriptor list | grep $vnfd_name | awk '{print $2}')
    if [ -n "$vnfd_id" ]; then
        openstack vnf descriptor delete $vnfd_id
    fi
done

echo "Deleting http_client and http_server"
for server_name in http_client http_server; do
    server_id=$(openstack server list | grep $server_name | awk '{print $2}')
    if [ -n "$server_id" ]; then
        openstack server delete $server_id
    fi
done

sleep 10

echo "Deleting VIM0"
vim_id=$(openstack vim list | grep VIM0 | awk '{print $2}')
if [ -n "$vim_id" ]; then
    openstack vim delete $vim_id
fi
