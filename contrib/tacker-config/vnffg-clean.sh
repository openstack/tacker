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

echo "Deleting VNF forwarding graph VNFFG1"
for vnffg in VNFFG1; do
    vnffg_id=$(openstack vnf graph list | grep $vnffg | awk '{print $2}')
    if [ -n "$vnffg_id" ]; then
        openstack vnf graph delete $vnffg_id
    fi
done

sleep 5

echo "Deleting VNFs"
for vnf_name in VNF1 VNF2; do
    vnf_id=$(openstack vnf list | grep $vnf_name | awk '{print $2}')
    if [ -n "$vnf_id" ]; then
        openstack vnf delete $vnf_id
    fi
done

echo "Deleting VNF descriptors"
for vnfd_name in VNFD1 VNFD2; do
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

sleep 5

echo "Deleting VIM0"
vim_id=$(openstack vim list | grep VIM0 | awk '{print $2}')
if [ -n "$vim_id" ]; then
    openstack vim delete $vim_id
fi

