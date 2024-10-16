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
import shutil

import ddt
from oslo_config import cfg
import yaml

from tacker.common import exceptions
from tacker.objects import fields
from tacker.objects.instantiate_vnf_req import InstantiateVnfRequest
from tacker.objects.vim_connection import VimConnectionInfo
from tacker.tests.unit import base
from tacker.tests.unit.vnflcm import fakes
from tacker.tests import utils
from tacker.tests import uuidsentinel
from tacker.vnflcm import utils as vnflcm_utils


@ddt.ddt
class VnfLcmUtilsTestCase(base.TestCase):

    @ddt.data(
        {'image_path': 'cirros-0.5.2-x86_64-disk.img',
         'extracted_path': 'cirros-0.5.2-x86_64-disk.img'},
        {'image_path': '../ImageFiles/image/cirros-0.5.2-x86_64-disk.img',
         'extracted_path': 'ImageFiles/image/cirros-0.5.2-x86_64-disk.img'},
        {'image_path': '../../Files/image/cirros-0.5.2-x86_64-disk.img',
         'extracted_path': 'Files/image/cirros-0.5.2-x86_64-disk.img'}
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

    def test_topology_template_param_of_vnf_dict(self):
        vnf_dict = fakes.vnf_dict()
        vnf_keys = vnf_dict['vnfd']['attributes']['vnfd_simple']
        self.assertIn('node_templates', vnf_keys)
        self.assertIn('policies', vnf_keys)
        self.assertIn('groups', vnf_keys)

    def test_vim_connection_info_extra_param(self):
        id = "817954e4-c321-4a31-ae06-cedcc4ddb85c"
        vim_id = "690edc6b-7581-48d8-9ac9-910c2c3d7c02"
        vim_type = "kubernetes"
        extra = {
            "helm_info": {
                "masternode_ip": [
                    "192.168.1.1"
                ],
                "masternode_username": "dummy_user",
                "masternode_password": "dummy_pass"
            }
        }

        vim_conn = VimConnectionInfo(id=id,
            vim_id=vim_id, vim_type=vim_type,
            extra=extra)

        instantiate_vnf_req = InstantiateVnfRequest()
        instantiate_vnf_req.vim_connection_info = [vim_conn]
        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.NOT_INSTANTIATED)
        result = vnflcm_utils._get_vim_connection_info_from_vnf_req(
            vnf_instance, instantiate_vnf_req)
        self.assertEqual(result[0].extra, vim_conn.extra)

    def test_get_current_num_of_instances(self):
        aspect_id = "vdu1_aspect"
        extract_policy_infos = fakes.fake_extract_policy_infos()
        result = vnflcm_utils.get_current_num_of_instances(
            extract_policy_infos, aspect_id, 0)
        self.assertEqual(result, 1)
        result = vnflcm_utils.get_current_num_of_instances(
            extract_policy_infos, aspect_id, 2)
        self.assertEqual(result, 3)

    def test_get_current_num_of_instances_no_step_deltas(self):
        aspect_id = "vdu1_aspect"
        extract_policy_infos = fakes.fake_extract_policy_infos()
        extract_policy_infos.get("aspect_id_dict").pop(aspect_id)
        error = self.assertRaises(exceptions.InvalidPoliciesDefinition,
            vnflcm_utils.get_current_num_of_instances, extract_policy_infos,
            aspect_id, 0)
        expected_error = ('Cannot retrieve the step_deltas id in '
                          'ScalingAspects parameter from policies '
                          'definition in VNFD.')
        self.assertEqual(expected_error, str(error))

    def test_get_current_num_of_instances_no_delta_num(self):
        aspect_id = "vdu1_aspect"
        extract_policy_infos = fakes.fake_extract_policy_infos()
        extract_policy_infos.get("aspect_delta_dict").pop(aspect_id)
        error = self.assertRaises(exceptions.InvalidPoliciesDefinition,
            vnflcm_utils.get_current_num_of_instances, extract_policy_infos,
            aspect_id, 0)
        expected_error = ('Cannot retrieve the delta num in '
                          'VduScalingAspectDeltas parameter from policies '
                          'definition in VNFD.')
        self.assertEqual(expected_error, str(error))

    def test_get_current_num_of_instances_no_initial_delta(self):
        aspect_id = "vdu1_aspect"
        extract_policy_infos = fakes.fake_extract_policy_infos()
        extract_policy_infos.get("vdu_delta_dict").pop("VDU1")
        error = self.assertRaises(exceptions.InvalidPoliciesDefinition,
            vnflcm_utils.get_current_num_of_instances, extract_policy_infos,
            aspect_id, 0)
        expected_error = ('Cannot retrieve the initial_delta num in '
                          'VduInitialDelta parameter from policies '
                          'definition in VNFD.')
        self.assertEqual(expected_error, str(error))

    def test_convert_desired_capacity_scale_status_none(self):
        vnfd_dict = fakes.get_vnfd_dict_for_convert_desired_capacity()

        etsi_common_file_path = utils.test_etc_sample('etsi/nfv',
            'common/Definitions/etsi_nfv_sol001_common_types.yaml')
        etsi_vnfd_file_path = utils.test_etc_sample('etsi/nfv',
            'common/Definitions/etsi_nfv_sol001_vnfd_types.yaml')
        helloworld_path = utils.test_etc_sample('etsi/nfv',
            'common_artifact/Definitions/helloworld3_types.yaml')

        etsi_common_file_path_tmp = os.path.join(
            os.path.dirname(__file__), 'etsi_nfv_sol001_common_types.yaml')
        types_file_path_tmp = os.path.abspath(
            os.path.join(os.path.dirname(__file__), 'types.yaml'))

        shutil.copy(etsi_common_file_path, etsi_common_file_path_tmp)
        self.addCleanup(os.remove, etsi_common_file_path_tmp)
        shutil.copy(helloworld_path, types_file_path_tmp)
        self.addCleanup(os.remove, types_file_path_tmp)

        with open(types_file_path_tmp) as f:
            data = yaml.safe_load(f)
            data['imports'] = [etsi_common_file_path, etsi_vnfd_file_path]
        with open(types_file_path_tmp, 'w', encoding='utf-8') as f:
            yaml.dump(data, f)

        vnfd_dict['imports'] = [etsi_common_file_path, etsi_vnfd_file_path,
                                types_file_path_tmp]

        desired_capacity = vnflcm_utils._convert_desired_capacity(
            'instantiation_level_1', vnfd_dict, 'VDU1')
        self.assertEqual(desired_capacity, 1)

    def test_convert_desired_capacity_scale_status_specified(self):
        vnfd_dict = fakes.get_vnfd_dict_for_convert_desired_capacity()

        etsi_common_file_path = utils.test_etc_sample('etsi/nfv',
            'common/Definitions/etsi_nfv_sol001_common_types.yaml')
        etsi_vnfd_file_path = utils.test_etc_sample('etsi/nfv',
            'common/Definitions/etsi_nfv_sol001_vnfd_types.yaml')
        helloworld_path = utils.test_etc_sample('etsi/nfv',
            'common_artifact/Definitions/helloworld3_types.yaml')

        etsi_common_file_path_tmp = os.path.join(
            os.path.dirname(__file__), 'etsi_nfv_sol001_common_types.yaml')
        types_file_path_tmp = os.path.abspath(
            os.path.join(os.path.dirname(__file__), 'types.yaml'))

        shutil.copy(etsi_common_file_path, etsi_common_file_path_tmp)
        self.addCleanup(os.remove, etsi_common_file_path_tmp)
        shutil.copy(helloworld_path, types_file_path_tmp)
        self.addCleanup(os.remove, types_file_path_tmp)

        with open(types_file_path_tmp) as f:
            data = yaml.safe_load(f)
            data['imports'] = [etsi_common_file_path, etsi_vnfd_file_path]
        with open(types_file_path_tmp, 'w', encoding='utf-8') as f:
            yaml.dump(data, f)

        vnfd_dict['imports'] = [etsi_common_file_path, etsi_vnfd_file_path,
                                types_file_path_tmp]

        scale_status = [{'aspect_id': 'VDU1_scale', 'scale_level': 1}]

        desired_capacity = vnflcm_utils._convert_desired_capacity(
            'instantiation_level_1', vnfd_dict, 'VDU1',
            scale_status=scale_status)
        self.assertEqual(desired_capacity, 2)
