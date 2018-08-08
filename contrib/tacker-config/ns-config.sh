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

client_ip=$(openstack server list | grep http_client | grep -Eo '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+')
network_source_port_id=$(openstack port list | grep $client_ip | awk '{print $2}')
ip_dst=$(openstack server list | grep http_server | grep -Eo '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+')
network_dest_port_id=$(openstack port list | grep $ip_dst | awk '{print $2}')

echo "Creating/ Updating ns_param.yaml file"
cat > ../../samples/tosca-templates/vnffg-nsd/ns_param.yaml << EOL
nsd:
  vl1_name: net_mgmt
  vl2_name: net0
  net_src_port_id: ${network_source_port_id}
  ip_dest_prefix: ${ip_dst}/24
  net_dst_port_id: ${network_dest_port_id}
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

