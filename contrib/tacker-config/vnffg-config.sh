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

network_name='net0'
network_id=$(openstack network list | grep $network_name | awk '{print $2}')
if [ -z "$network_id" ]; then
    echo "Creating network net0"
    openstack network create $network_name --provider-network-type=vxlan --provider-segment 1005
    openstack subnet create --network $network_name --subnet-range 10.0.10.0/24 subnet-test
    network_id=$(openstack network list | grep $network_name | awk '{print $2}')
fi

echo "Creating HTTP client"
openstack server create --flavor m1.tiny --image cirros-0.4.0-x86_64-disk --nic net-id=$network_id http_client
echo "Creating HTTP server"
openstack server create --flavor m1.tiny --image cirros-0.4.0-x86_64-disk --nic net-id=$network_id http_server

sleep 15

ip_src=$(openstack server list | grep http_client | grep -Eo '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+')
network_source_port_id=$(openstack port list | grep $ip_src | awk '{print $2}')
ip_dst=$(openstack server list | grep http_server | grep -Eo '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+')
network_dest_port_id=$(openstack port list | grep $ip_dst | awk '{print $2}')

echo "Creating/ Updating ns_param.yaml file"
cat > ../../samples/tosca-templates/vnffgd/vnffg-param-file.yaml << EOL
net_src_port_id: ${network_source_port_id}
ip_dst_pre: ${ip_dst}/24
net_dst_port_id: ${network_dest_port_id}
dst_port_range: 80-80
EOL

vim_default=$(openstack vim list | grep openstack | awk '{print $10}')
if [ "$vim_default" != "True" ]; then
    echo "Creating default VIM"
    cat > ./vim_config.yaml << EOL
auth_url: $OS_AUTH_URL
username: $OS_USERNAME
password: $OS_PASSWORD
project_name: $OS_PROJECT_NAME
project_domain_name: $OS_PROJECT_DOMAIN_ID
user_domain_name: $OS_USER_DOMAIN_ID
EOL
    openstack vim register --config-file vim_config.yaml --is-default VIM0
    rm ./vim_config.yaml
fi

echo "Create VNF1 and VNF2"
openstack vnf descriptor create --vnfd-file ../../samples/tosca-templates/vnffgd/tosca-vnffg-vnfd1.yaml VNFD1
openstack vnf create --vnfd-name VNFD1 --vim-name VIM0 VNF1
openstack vnf descriptor create --vnfd-file ../../samples/tosca-templates/vnffgd/tosca-vnffg-vnfd2.yaml VNFD2
openstack vnf create --vnfd-name VNFD2 --vim-name VIM0 VNF2

