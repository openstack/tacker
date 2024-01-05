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

from tacker.tests.functional.sol_v2_common import paramgen
from tacker.tests.functional.sol_v2_common import utils
from tacker.tests import utils as test_utils


zip_file_name = os.path.basename(os.path.abspath(".")) + '.zip'
tmp_dir = tempfile.mkdtemp()
vnfd_id = uuidutils.generate_uuid()

image_path = test_utils.test_etc_sample("etsi/nfv/common/Files/images",
    "cirros-0.5.2-x86_64-disk.img")

utils.make_zip(".", tmp_dir, vnfd_id, image_path)

shutil.move(os.path.join(tmp_dir, zip_file_name), ".")
shutil.rmtree(tmp_dir)

create_req = paramgen.change_vnfpkg_create(vnfd_id)
terminate_req = paramgen.terminate_vnf_min()

net_ids = utils.get_network_ids(['net0'])
subnet_ids = utils.get_subnet_ids(['subnet0'])

# if your sample is change VM from image to image
instantiate_req_from_image_to_image = paramgen.change_vnfpkg_instantiate(
    net_ids, subnet_ids, "http://localhost/identity/v3")

# if your sample is change VM from volume to volume
instantiate_req_from_volume_to_volume = paramgen.change_vnfpkg_instantiate(
    net_ids, subnet_ids, "http://localhost/identity/v3", flavor_id='volume')

# if your sample is change VM from image to image update failed
instantiate_req_update_failed = paramgen.change_vnfpkg_instantiate(
    net_ids, subnet_ids, "http://localhost/identity/v3")

with open("create_req", "w") as f:
    f.write(json.dumps(create_req, indent=2))

with open("terminate_req", "w") as f:
    f.write(json.dumps(terminate_req, indent=2))

with open("instantiate_req_from_image_to_image", "w") as f:
    f.write(json.dumps(instantiate_req_from_image_to_image, indent=2))

with open("instantiate_req_from_volume_to_volume", "w") as f:
    f.write(json.dumps(instantiate_req_from_volume_to_volume, indent=2))

with open("instantiate_req_update_failed", "w") as f:
    f.write(json.dumps(instantiate_req_update_failed, indent=2))
