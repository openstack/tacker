#!/bin/bash -x
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

PRIVATE_KEY_FILE=${PRIVATE_KEY_FILE:-"keypair.priv"}

function fixup_quota {
    echo "Disable nova compute instance & core quota"
    nova quota-class-update --instances -1 --cores -1 --ram -1 default
    projectId=$(openstack project list | awk '/\ nfv\ / {print $2}')
    echo "Disable neutron port quota on project 'nfv' $projectId"
    neutron quota-update --tenant-id $projectId --port -1
}

# Adding nova keypair if not exist to support key_name (#1578785).
function add_key_if_not_exist {
    echo "Adding nova key if not exist"
    userId=$(openstack user list | awk '/\ nfv_user\ / {print $2}')
    nova keypair-show userKey --user $userId >/dev/null
    if [[ "$?" != "0" ]]; then
        nova keypair-add userKey --user $userId > ${PRIVATE_KEY_FILE}
    else
        echo "Keypair userKey already exists"
    fi
}

# Adding nova keypair to support key_name (#1578785).
# used by OpenStack CI since it will fail if $? is not 0
function add_key {
    echo "Adding nova key"
    userId=$(openstack user list | awk '/\ nfv_user\ / {print $2}')
    nova keypair-add userKey --user $userId > ${PRIVATE_KEY_FILE}
}

# Adding nova security groups (#1591372).
function _create_secgrps {
    openstack security group create --project nfv --description "tacker functest security group" test_secgrp
    openstack security group rule create --project nfv --ingress --protocol icmp test_secgrp
    openstack security group rule create --project nfv --ingress --protocol tcp --dst-port 22 test_secgrp
}

function _check_secgrps {
    openstack security group show test_secgrp
    if [[ "$?" != "0" ]]; then
        echo "Warning: security group is not created correctly"
    fi
}

function add_secgrp_if_not_exist {
    echo "Adding nova security group"
    openstack security group show test_secgrp
    if [[ "$?" != "0" ]]; then
        _create_secgrps
        _check_secgrps
    else
        echo "Nova security group already exists"
    fi
}

# Adding nova security groups (#1591372).
function add_secgrp {
    echo "Adding nova security group"
    _create_secgrps
    _check_secgrps
}
