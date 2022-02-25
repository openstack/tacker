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

from tacker.tests.functional.sol_v2 import paramgen
from tacker.tests.functional.sol_v2 import utils


zip_file_name = os.path.basename(os.path.abspath(".")) + '.zip'
tmp_dir = tempfile.mkdtemp()
vnfd_id = uuidutils.generate_uuid()
utils.make_zip(".", tmp_dir, vnfd_id)

shutil.copy(os.path.join(tmp_dir, zip_file_name), ".")
shutil.rmtree(tmp_dir)

print('#####################################################################\n'
      '# vnfc id should be changed in update req file by show vnf manually.#\n'
      '#####################################################################')

update_min_req = paramgen.update_vnf_min_with_parameter(vnfd_id)
# fake vnfc id, should be get from show vnf
vnfc_ids = ["VDU1-9300a3cb-bd3b-45e4-9967-095040caf827",
    "VDU2-39681281-e6e6-4179-8898-d9ec70f1642a"]
update_max_req = paramgen.update_vnf_max(vnfd_id, vnfc_ids)

with open("update_min_req", "w", encoding='utf-8') as f:
    f.write(json.dumps(update_min_req, indent=2))

with open("update_max_req", "w", encoding='utf-8') as f:
    f.write(json.dumps(update_max_req, indent=2))
