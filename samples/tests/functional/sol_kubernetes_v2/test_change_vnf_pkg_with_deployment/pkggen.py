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
from tacker.tests.functional.sol_v2_common import utils


zip_file_name = os.path.basename(os.path.abspath(".")) + '.zip'
tmp_dir = tempfile.mkdtemp()
vnfd_id = uuidutils.generate_uuid()

# samples/tests/functional/sol_kubernetes_v2/{package_name}
utils.make_zip(".", tmp_dir, vnfd_id)

shutil.move(os.path.join(tmp_dir, zip_file_name), ".")
shutil.rmtree(tmp_dir)

# if you change_vnfpkg with all parameters
change_vnfpkg = paramgen.change_vnfpkg(vnfd_id)

# if you change_vnfpkg with no operational parameters
change_vnfpkg_error = paramgen.change_vnfpkg_error(vnfd_id)

change_vnfpkg_terminate = paramgen.change_vnfpkg_terminate()

with open("change_vnfpkg", "w", encoding='utf-8') as f:
    f.write(json.dumps(change_vnfpkg, indent=2))

with open("change_vnfpkg_error", "w", encoding='utf-8') as f:
    f.write(json.dumps(change_vnfpkg_error, indent=2))

with open("change_vnfpkg_terminate", "w", encoding='utf-8') as f:
    f.write(json.dumps(change_vnfpkg_terminate, indent=2))
