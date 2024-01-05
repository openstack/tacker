# Copyright (C) 2023 Fujitsu
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import json
import os
import shutil
import string
import tempfile

from tacker.tests.functional.sol_v2_common import paramgen
from tacker.tests.functional.sol_v2_common import utils


SUPPORT_STRING_FOR_VNFD_ID = string.ascii_letters + string.digits + "-._ "
vnfd_id = SUPPORT_STRING_FOR_VNFD_ID + "new_max_vnfd_id"
zip_file_name = os.path.basename(os.path.abspath(".")) + '.zip'
tmp_dir = tempfile.mkdtemp()

# tacker/sol_refactored/infra_drivers/openstack/userdata_standard.py
# samples/functional/sol_v2_common/sampleX
userdata_dir = "../../../../tacker/sol_refactored/infra_drivers/openstack/"
userdata_file = "userdata_standard.py"
userdata_path = os.path.abspath(userdata_dir + userdata_file)

utils.make_zip(".", tmp_dir, vnfd_id, userdata_path=userdata_path)

shutil.copy(os.path.join(tmp_dir, zip_file_name), ".")
shutil.rmtree(tmp_dir)

print('#####################################################################\n'
      '# Run pre.py if an error occurs                                     #\n'
      '#  - If an error occurs, run the pre.py script in advance           #\n'
      '#    to create the openstack resource required to run this script.  #\n'
      '# Run post.py when you finish tests                                 #\n'
      '#  - When you no longer need these openstack resources              #\n'
      '#    after testing, run post.py and delete them.                    #\n'
      '#####################################################################')

net_ids = utils.get_network_ids(['net0', 'net1', 'net_mgmt', 'ft-net0',
    'ft-net1'])
subnet_ids = utils.get_subnet_ids(['subnet0', 'subnet1', 'ft-ipv4-subnet0',
    'ft-ipv6-subnet0', 'ft-ipv4-subnet1', 'ft-ipv6-subnet1'])

change_vnf_pkg_individual_vnfc_max = (
    paramgen.change_vnf_pkg_individual_vnfc_max(vnfd_id, net_ids, subnet_ids))

with open("change_vnf_pkg_individual_vnfc_max_req", "w") as f:
    f.write(json.dumps(change_vnf_pkg_individual_vnfc_max, indent=2))
