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
import tempfile

from oslo_utils import uuidutils

from tacker.tests.functional.sol_kubernetes_v2 import paramgen
from tacker.tests.functional.sol_v2_common import utils


zip_file_name = os.path.basename(os.path.abspath(".")) + '.zip'
tmp_dir = tempfile.mkdtemp()
vnfd_id = uuidutils.generate_uuid()

# tacker/tests/functional/sol_kubernetes_v2/samples/{package_name}
cur_dir = os.path.dirname(__file__)
mgmt_driver_path = os.path.join(
    cur_dir,
    '../../../../../sol_refactored/mgmt_drivers/container_update_mgmt_v2.py')
utils.make_zip(".", tmp_dir, vnfd_id, mgmt_driver=mgmt_driver_path)

shutil.move(os.path.join(tmp_dir, zip_file_name), ".")
shutil.rmtree(tmp_dir)

cnf_modify_update_req = paramgen.test_cnf_update_modify(vnfd_id)

with open("cnf_modify_update_req", "w", encoding='utf-8') as f:
    f.write(json.dumps(cnf_modify_update_req, indent=2))
