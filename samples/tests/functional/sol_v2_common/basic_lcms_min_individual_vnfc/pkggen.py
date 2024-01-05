# Copyright (C) 2021 Nippon Telegraph and Telephone Corporation
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
vnfd_id = SUPPORT_STRING_FOR_VNFD_ID + "min_vnfd_id"
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


def add_additional_params(req):
    if not req.get('additionalParams'):
        req['additionalParams'] = {}
    req['additionalParams']['lcm-operation-user-data'] = (
        './UserData/userdata_standard.py')
    req['additionalParams']['lcm-operation-user-data-class'] = (
        'StandardUserData')


create_req = paramgen.create_vnf_min(vnfd_id)
terminate_req = paramgen.terminate_vnf_min()
instantiate_req = paramgen.instantiate_vnf_min()
add_additional_params(instantiate_req)
scaleout_req = paramgen.scaleout_vnf_min()
add_additional_params(scaleout_req)
scalein_req = paramgen.scalein_vnf_min()
add_additional_params(scalein_req)

# fake vnfc id, should be get from show vnf
VNFC_ID = "VDU1-9300a3cb-bd3b-45e4-9967-095040caf827"
heal_req = paramgen.heal_vnf_vnfc_min(VNFC_ID)
add_additional_params(heal_req)
heal_without_parameter_req = paramgen.heal_vnf_all_min()
add_additional_params(heal_without_parameter_req)

print('#####################################################################\n'
      '# vnfc id should be changed in heal req file by show vnf manually.  #\n'
      '#####################################################################')

with open("create_req", "w", encoding='utf-8') as f:
    f.write(json.dumps(create_req, indent=2))

with open("terminate_req", "w", encoding='utf-8') as f:
    f.write(json.dumps(terminate_req, indent=2))

with open("instantiate_req", "w", encoding='utf-8') as f:
    f.write(json.dumps(instantiate_req, indent=2))

with open("scaleout_req", "w", encoding='utf-8') as f:
    f.write(json.dumps(scaleout_req, indent=2))

with open("scalein_req", "w", encoding='utf-8') as f:
    f.write(json.dumps(scalein_req, indent=2))

with open("heal_req", "w", encoding='utf-8') as f:
    f.write(json.dumps(heal_req, indent=2))

with open("heal_without_parameter_req", "w", encoding='utf-8') as f:
    f.write(json.dumps(heal_without_parameter_req, indent=2))
