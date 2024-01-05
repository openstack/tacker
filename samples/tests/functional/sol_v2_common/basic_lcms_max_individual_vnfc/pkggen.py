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
from tacker.tests import utils as test_utils


SUPPORT_STRING_FOR_VNFD_ID = string.ascii_letters + string.digits + "-._ "
vnfd_id = SUPPORT_STRING_FOR_VNFD_ID + "max_vnfd_id"
zip_file_name = os.path.basename(os.path.abspath(".")) + '.zip'
tmp_dir = tempfile.mkdtemp()

image_path = test_utils.test_etc_sample("etsi/nfv/common/Files/images",
    "cirros-0.5.2-x86_64-disk.img")

# tacker/sol_refactored/infra_drivers/openstack/userdata_standard.py
# samples/functional/sol_v2_common/sampleX
userdata_dir = "../../../../tacker/sol_refactored/infra_drivers/openstack/"
userdata_file = "userdata_standard.py"
userdata_path = os.path.abspath(userdata_dir + userdata_file)

utils.make_zip(".", tmp_dir, vnfd_id, image_path=image_path,
               userdata_path=userdata_path)

shutil.move(os.path.join(tmp_dir, zip_file_name), ".")
shutil.rmtree(tmp_dir)


def add_additional_params(req):
    if not req.get('additionalParams'):
        req['additionalParams'] = {}
    req['additionalParams']['lcm-operation-user-data'] = (
        './UserData/userdata_standard.py')
    req['additionalParams']['lcm-operation-user-data-class'] = (
        'StandardUserData')


create_req = paramgen.create_vnf_max(
    vnfd_id, description='test for basic_lcms_max_individual_vnfc')
scaleout_req = paramgen.scaleout_vnf_max()
add_additional_params(scaleout_req)
scalein_req = paramgen.scalein_vnf_max()
add_additional_params(scalein_req)
terminate_req = paramgen.terminate_vnf_max()

print('#####################################################################\n'
      '# Run pre.py if an error occurs                                     #\n'
      '#  - If an error occurs, run the pre.py script in advance           #\n'
      '#    to create the openstack resource required to run this script.  #\n'
      '# Run post.py when you finish tests                                 #\n'
      '#  - When you no longer need these openstack resources              #\n'
      '#    after testing, run post.py and delete them.                    #\n'
      '# vnfc ids should be changed in heal req files by show vnf manually.#\n'
      '#####################################################################')

net_ids = utils.get_network_ids(['net0', 'net1', 'net_mgmt', 'ft-net0',
    'ft-net1'])
subnet_ids = utils.get_subnet_ids(['subnet0', 'subnet1', 'ft-ipv4-subnet0',
    'ft-ipv6-subnet0', 'ft-ipv4-subnet1', 'ft-ipv6-subnet1'])

instantiate_req = paramgen.instantiate_vnf_max(
    net_ids, subnet_ids, None, "http://localhost/identity/v3", user_data=True)

# fake vnfc id, should be get from show vnf
vnfc_ids = ['VDU1-9300a3cb-bd3b-45e4-9967-095040caf827',
    'VDU2-39681281-e6e6-4179-8898-d9ec70f1642a']
heal_vnfc_req = paramgen.heal_vnf_vnfc_max(vnfc_ids[0])
add_additional_params(heal_vnfc_req)
heal_vnfc_with_omit_all_req = paramgen.heal_vnf_vnfc_max_with_parameter(
    vnfc_ids)
add_additional_params(heal_vnfc_with_omit_all_req)
heal_vnfc_with_all_false_req = paramgen.heal_vnf_vnfc_max_with_parameter(
    vnfc_ids, False)
add_additional_params(heal_vnfc_with_all_false_req)
heal_vnfc_with_all_true_req = paramgen.heal_vnf_vnfc_max_with_parameter(
    vnfc_ids, True)
add_additional_params(heal_vnfc_with_all_true_req)
heal_all_with_omit_all_req = paramgen.heal_vnf_all_max_with_parameter()
add_additional_params(heal_all_with_omit_all_req)
heal_all_with_all_true_req = paramgen.heal_vnf_all_max_with_parameter(True)
add_additional_params(heal_all_with_all_true_req)
heal_all_with_all_false_req = paramgen.heal_vnf_all_max_with_parameter(False)
add_additional_params(heal_all_with_all_false_req)
change_ext_conn_max_req = paramgen.change_ext_conn_max(net_ids, subnet_ids,
    "http://localhost/identity/v3")
add_additional_params(change_ext_conn_max_req)
# Only this package have external connectivity.
# So min pattern also use this package.
change_ext_conn_min_req = paramgen.change_ext_conn_min(net_ids, subnet_ids)
add_additional_params(change_ext_conn_min_req)
update_req = paramgen.update_vnf_min_with_parameter(vnfd_id)

with open("create_req", "w", encoding='utf-8') as f:
    f.write(json.dumps(create_req, indent=2))

with open("terminate_req", "w", encoding='utf-8') as f:
    f.write(json.dumps(terminate_req, indent=2))

with open("scaleout_req", "w", encoding='utf-8') as f:
    f.write(json.dumps(scaleout_req, indent=2))

with open("scalein_req", "w", encoding='utf-8') as f:
    f.write(json.dumps(scalein_req, indent=2))

with open("instantiate_req", "w", encoding='utf-8') as f:
    f.write(json.dumps(instantiate_req, indent=2))

with open("heal_vnfc_req", "w", encoding='utf-8') as f:
    f.write(json.dumps(heal_vnfc_req, indent=2))

with open("heal_vnfc_with_omit_all_req", "w", encoding='utf-8') as f:
    f.write(json.dumps(heal_vnfc_with_omit_all_req, indent=2))

with open("heal_vnfc_with_all_false_req", "w", encoding='utf-8') as f:
    f.write(json.dumps(heal_vnfc_with_all_false_req, indent=2))

with open("heal_vnfc_with_all_true_req", "w", encoding='utf-8') as f:
    f.write(json.dumps(heal_vnfc_with_all_true_req, indent=2))

with open("heal_all_with_omit_all_req", "w", encoding='utf-8') as f:
    f.write(json.dumps(heal_all_with_omit_all_req, indent=2))

with open("heal_all_with_all_true_req", "w", encoding='utf-8') as f:
    f.write(json.dumps(heal_all_with_all_true_req, indent=2))

with open("heal_all_with_all_false_req", "w", encoding='utf-8') as f:
    f.write(json.dumps(heal_all_with_all_false_req, indent=2))

with open("change_ext_conn_max_req", "w", encoding='utf-8') as f:
    f.write(json.dumps(change_ext_conn_max_req, indent=2))

with open("change_ext_conn_min_req", "w", encoding='utf-8') as f:
    f.write(json.dumps(change_ext_conn_min_req, indent=2))

with open("update_req", "w", encoding='utf-8') as f:
    f.write(json.dumps(update_req, indent=2))
