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

from tacker.tests.functional.sol_v2 import paramgen
from tacker.tests.functional.sol_v2 import utils


zip_file_name = os.path.basename(os.path.abspath(".")) + '.zip'
tmp_dir = tempfile.mkdtemp()
vnfd_id = uuidutils.generate_uuid()

image_dir = "../../../../etc/samples/etsi/nfv/common/Files/images/"
image_file = "cirros-0.5.2-x86_64-disk.img"
image_path = os.path.abspath(image_dir + image_file)

utils.make_zip(".", tmp_dir, vnfd_id, image_path)

shutil.move(os.path.join(tmp_dir, zip_file_name), ".")
shutil.rmtree(tmp_dir)

# if your sample is change VM from image to volume
change_vnfpkg_req_from_image_to_volume = paramgen.change_vnfpkg(vnfd_id)
del change_vnfpkg_req_from_image_to_volume['additionalParams']['vdu_params'][0]

with open("change_vnfpkg_req_from_image_to_volume", "w",
          encoding='utf-8') as f:
    f.write(json.dumps(change_vnfpkg_req_from_image_to_volume, indent=2))

# if your sample is change VM from volume to volume
change_vnfpkg_req_from_volume_to_volume = paramgen.change_vnfpkg(vnfd_id)
del change_vnfpkg_req_from_volume_to_volume[
    'additionalParams']['vdu_params'][0]

with open("change_vnfpkg_req_from_volume", "w", encoding='utf-8') as f:
    f.write(json.dumps(change_vnfpkg_req_from_volume_to_volume, indent=2))
