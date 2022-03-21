# Copyright (C) 2022 Fujitsu
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
from tacker.tests.functional.sol_v2 import utils


zip_file_name = os.path.basename(os.path.abspath(".")) + '.zip'
tmp_dir = tempfile.mkdtemp()
vnfd_id = uuidutils.generate_uuid()

# tacker/tests/functional/sol_kubernetes_v2/samples/{package_name}
utils.make_zip(".", tmp_dir, vnfd_id)

shutil.move(os.path.join(tmp_dir, zip_file_name), ".")
shutil.rmtree(tmp_dir)

# if you change_vnfpkg with all parameters
change_vnfpkg_all_params = paramgen.change_vnfpkg_all_params(vnfd_id)

# if you change_vnfpkg with no operational parameters
change_vnfpkg_min = paramgen.change_vnfpkg_min(vnfd_id)

with open("change_vnfpkg_all_params", "w", encoding='utf-8') as f:
    f.write(json.dumps(change_vnfpkg_all_params, indent=2))

with open("change_vnfpkg_min", "w", encoding='utf-8') as f:
    f.write(json.dumps(change_vnfpkg_min, indent=2))
