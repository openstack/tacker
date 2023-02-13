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

from tacker.tests.functional.sol_v2_common import paramgen
from tacker.tests.functional.sol_v2_common import utils


zip_file_name = os.path.basename(os.path.abspath(".")) + '.zip'
tmp_dir = tempfile.mkdtemp()
vnfd_id = uuidutils.generate_uuid()

# tacker/tests/etc...
image_dir = "../../../../etc/samples/etsi/nfv/common/Files/images/"
image_file = "cirros-0.5.2-x86_64-disk.img"
image_path = os.path.abspath(image_dir + image_file)

# tacker/sol_refactored/infra_drivers/openstack/userdata_standard.py
#       /tests/functional/sol_v2_common/samples/sampleX
userdata_dir = "../../../../../sol_refactored/infra_drivers/openstack/"
userdata_file = "userdata_standard.py"
userdata_path = os.path.abspath(userdata_dir + userdata_file)

utils.make_zip(".", tmp_dir, vnfd_id, image_path=image_path,
               userdata_path=userdata_path)

shutil.copy(os.path.join(tmp_dir, zip_file_name), ".")
shutil.rmtree(tmp_dir)

update_min_req = paramgen.update_vnf_min_with_parameter(vnfd_id)

change_vnf_pkg_individual_vnfc_min = (
    paramgen.change_vnf_pkg_individual_vnfc_min(vnfd_id))

with open("change_vnf_pkg_individual_vnfc_min_req", "w") as f:
    f.write(json.dumps(change_vnf_pkg_individual_vnfc_min, indent=2))

with open("update_min_req", "w", encoding='utf-8') as f:
    f.write(json.dumps(update_min_req, indent=2))
