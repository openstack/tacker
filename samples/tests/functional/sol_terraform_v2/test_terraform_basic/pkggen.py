# Copyright (C) 2023 Nippon Telegraph and Telephone Corporation
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

from tacker.tests.functional.sol_terraform_v2 import paramgen as tf_paramgen
from tacker.tests.functional.sol_v2_common import utils


zip_file_name = os.path.basename(os.path.abspath(".")) + '.zip'
tmp_dir = tempfile.mkdtemp()
vnfd_id = uuidutils.generate_uuid()

# samples/tests/functional/sol_terraform_v2/{package_name}
utils.make_zip(".", tmp_dir, vnfd_id)

shutil.move(os.path.join(tmp_dir, zip_file_name), ".")
shutil.rmtree(tmp_dir)

create_req = tf_paramgen.create_req_by_vnfd_id(vnfd_id)
instantiate_req = tf_paramgen.instantiate_req()
terminate_req = tf_paramgen.terminate_req()

with open("create_req", "w", encoding='utf-8') as f:
    f.write(json.dumps(create_req, indent=2))

with open("instantiate_req", "w", encoding='utf-8') as f:
    f.write(json.dumps(instantiate_req, indent=2))

with open("terminate_req", "w", encoding='utf-8') as f:
    f.write(json.dumps(terminate_req, indent=2))
