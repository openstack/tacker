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
import tempfile

from oslo_utils import uuidutils

from tacker.tests.functional.sol_v2_common import paramgen
from tacker.tests.functional.sol_v2_common import utils


zip_file_name = os.path.basename(os.path.abspath(".")) + '.zip'
tmp_dir = tempfile.mkdtemp()
vnfd_id = uuidutils.generate_uuid()
utils.make_zip(".", tmp_dir, vnfd_id)

shutil.copy(os.path.join(tmp_dir, zip_file_name), ".")
shutil.rmtree(tmp_dir)

create_req = paramgen.create_vnf_min(vnfd_id)
terminate_req = paramgen.terminate_vnf_min()
instantiate_req = paramgen.instantiate_vnf_min()
scaleout_req = paramgen.scaleout_vnf_min()
scalein_req = paramgen.scalein_vnf_min()
update_req = paramgen.update_vnf_min()
# fake vnfc id, should be get from show vnf
VNFC_ID = "VDU1-9300a3cb-bd3b-45e4-9967-095040caf827"
heal_req = paramgen.heal_vnf_vnfc_min(VNFC_ID)
heal_without_parameter_req = paramgen.heal_vnf_all_min()

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

with open("update_req", "w", encoding='utf-8') as f:
    f.write(json.dumps(update_req, indent=2))

with open("heal_req", "w", encoding='utf-8') as f:
    f.write(json.dumps(heal_req, indent=2))

with open("heal_without_parameter_req", "w", encoding='utf-8') as f:
    f.write(json.dumps(heal_without_parameter_req, indent=2))
