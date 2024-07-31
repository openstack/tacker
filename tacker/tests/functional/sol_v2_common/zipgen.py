# Copyright (C) 2024 Nippon Telegraph and Telephone Corporation
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

import os
import tempfile

from oslo_utils import uuidutils
from tacker.tests.functional.sol_v2_common import utils as common_utils
from tacker.tests import utils


def userdata_standard(vnfd_id=None):
    if vnfd_id is None:
        vnfd_id = uuidutils.generate_uuid()

    tmp_dir = tempfile.mkdtemp()

    sample_path = utils.test_sample(
        "functional/sol_v2_common/userdata_standard")

    image_path = utils.test_etc_sample("etsi/nfv/common/Files/images",
        "cirros-0.5.2-x86_64-disk.img")

    userdata_path = utils.userdata("userdata_standard.py")

    common_utils.make_zip(sample_path, tmp_dir, vnfd_id, image_path=image_path,
            userdata_path=userdata_path)

    zip_file_name = f"{os.path.basename(os.path.abspath(sample_path))}.zip"
    zip_file_path = os.path.join(tmp_dir, zip_file_name)

    return vnfd_id, zip_file_path
