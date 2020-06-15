# Copyright (c) 2020 NTT DATA
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os

import ddt
from oslo_config import cfg

from tacker.tests.unit import base
from tacker.tests.unit.vnflcm import fakes
from tacker.tests import uuidsentinel
from tacker.vnflcm import utils as vnflcm_utils


@ddt.ddt
class VnfLcmUtilsTestCase(base.TestCase):

    @ddt.data(
        {'image_path': 'cirros-0.4.0-x86_64-disk.img',
         'extracted_path': 'cirros-0.4.0-x86_64-disk.img'},
        {'image_path': '../ImageFiles/image/cirros-0.4.0-x86_64-disk.img',
         'extracted_path': 'ImageFiles/image/cirros-0.4.0-x86_64-disk.img'},
        {'image_path': '../../Files/image/cirros-0.4.0-x86_64-disk.img',
         'extracted_path': 'Files/image/cirros-0.4.0-x86_64-disk.img'}
    )
    @ddt.unpack
    def test_create_grant_request_with_software_image_path(self, image_path,
                                                           extracted_path):
        vnf_package_id = uuidsentinel.package_uuid
        vnfd_dict = fakes.get_vnfd_dict(image_path=image_path)
        vnf_software_images = vnflcm_utils._create_grant_request(
            vnfd_dict, vnf_package_id)
        vnf_package_path = cfg.CONF.vnf_package.vnf_package_csar_path
        expected_image_path = os.path.join(vnf_package_path, vnf_package_id,
                                           extracted_path)
        self.assertEqual(expected_image_path,
                         vnf_software_images['VDU1'].image_path)

    def test_get_param_data_with_flavour_description(self):
        vnfd_dict = fakes.get_vnfd_dict()
        vnfd_dict.update({'imports': []})
        instantiate_vnf_req = fakes.get_instantiate_vnf_request_obj()
        param_value = vnflcm_utils._get_param_data(vnfd_dict,
                                                   instantiate_vnf_req)
        expected_flavour_description = 'A simple flavor'
        self.assertEqual(expected_flavour_description,
                         param_value['flavour_description'])
