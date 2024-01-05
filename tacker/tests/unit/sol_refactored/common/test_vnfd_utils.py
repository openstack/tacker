# Copyright (C) 2021 Nippon Telegraph and Telephone Corporation
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
import shutil
import tempfile

from oslo_log import log as logging
from oslo_utils import uuidutils
import yaml

from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.common import vnfd_utils
from tacker.tests import base
from tacker.tests import utils


SAMPLE_VNFD_ID = "b1bb0ce7-ebca-4fa7-95ed-4840d7000000"
SAMPLE_FLAVOUR_ID = "simple"
LOG = logging.getLogger()


class TestVnfd(base.BaseTestCase):

    def setUp(self):
        super(TestVnfd, self).setUp()
        self.vnfd_1 = vnfd_utils.Vnfd(SAMPLE_VNFD_ID)
        self.vnfd_1.init_from_csar_dir(self._sample_dir("sample1"))

    def _sample_dir(self, name):
        return utils.test_sample("unit/sol_refactored/samples", name)

    def test_get_sw_image(self):
        expected_result = {
            'VDU2': 'VDU2-image',
            'VirtualStorage': 'image-1.0.0-x86_64-disk'
        }
        result = self.vnfd_1.get_sw_image(SAMPLE_FLAVOUR_ID)

        self.assertEqual(expected_result, result)

    def test_get_sw_image_data(self):
        result = self.vnfd_1.get_sw_image_data(SAMPLE_FLAVOUR_ID)
        # check 'file' existence if 'artifact' is defined
        self.assertEqual('../Files/images/image-1.0.0-x86_64-disk.img',
                         result['VDU2']['file'])
        self.assertNotIn('file', result['VirtualStorage'])

    def test_get_nodes(self):
        expected_vdus = ['VDU1', 'VDU2']
        expected_storages = ['VirtualStorage']
        expected_vls = ['internalVL1', 'internalVL2', 'internalVL3']
        expected_cps = ['VDU1_CP1', 'VDU1_CP2', 'VDU1_CP3', 'VDU1_CP4',
                        'VDU1_CP5', 'VDU2_CP1', 'VDU2_CP2', 'VDU2_CP3',
                        'VDU2_CP4', 'VDU2_CP5']
        # check keys and sampling data
        result_vdus = self.vnfd_1.get_vdu_nodes(SAMPLE_FLAVOUR_ID)
        self.assertEqual(expected_vdus, list(result_vdus.keys()))
        self.assertEqual('VDU1 compute node',
            result_vdus['VDU1']['properties']['description'])

        result_storages = self.vnfd_1.get_storage_nodes(SAMPLE_FLAVOUR_ID)
        self.assertEqual(expected_storages, list(result_storages.keys()))
        self.assertEqual('1.0.0',
            result_storages['VirtualStorage']['properties']['sw_image_data']
            ['version'])

        result_vls = self.vnfd_1.get_virtual_link_nodes(SAMPLE_FLAVOUR_ID)
        self.assertEqual(expected_vls, list(result_vls.keys()))
        self.assertEqual(['ipv4'],
            result_vls['internalVL3']['properties']['connectivity_type']
            ['layer_protocols'])

        result_cps = self.vnfd_1.get_vducp_nodes(SAMPLE_FLAVOUR_ID)
        self.assertEqual(expected_cps, list(result_cps.keys()))
        self.assertEqual(0,
            result_cps['VDU2_CP1']['properties']['order'])

    def test_get_vdu_cps(self):
        expected_result = ['VDU1_CP1', 'VDU1_CP2', 'VDU1_CP3',
                           'VDU1_CP4', 'VDU1_CP5']
        result = self.vnfd_1.get_vdu_cps(SAMPLE_FLAVOUR_ID, 'VDU1')

        self.assertEqual(expected_result, result)

    def test_get_vdu_storages(self):
        vdu_nodes = self.vnfd_1.get_vdu_nodes(SAMPLE_FLAVOUR_ID)
        expected_result = ['VirtualStorage']
        result = self.vnfd_1.get_vdu_storages(vdu_nodes['VDU1'])
        self.assertEqual(expected_result, result)

        expected_result = []
        result = self.vnfd_1.get_vdu_storages(vdu_nodes['VDU2'])
        self.assertEqual(expected_result, result)

    def test_get_base_hot(self):
        result = self.vnfd_1.get_base_hot(SAMPLE_FLAVOUR_ID)
        # check keys and sampling data
        self.assertEqual(['VDU1.yaml'], list(result['files'].keys()))
        self.assertEqual({'get_param': 'net3'},
            result['files']['VDU1.yaml']['resources']['VDU1_CP3']
            ['properties']['network'])

    def test_get_vl_name_from_cp(self):
        vdu_cps = self.vnfd_1.get_vducp_nodes(SAMPLE_FLAVOUR_ID)
        result = self.vnfd_1.get_vl_name_from_cp(SAMPLE_FLAVOUR_ID,
            vdu_cps['VDU1_CP1'])
        # externalVL
        self.assertEqual(None, result)

        result = self.vnfd_1.get_vl_name_from_cp(SAMPLE_FLAVOUR_ID,
            vdu_cps['VDU1_CP3'])
        self.assertEqual('internalVL1', result)

    def test_get_compute_flavor(self):
        result = self.vnfd_1.get_compute_flavor(SAMPLE_FLAVOUR_ID, 'VDU1')
        self.assertEqual('m1.tiny', result)

    def test_get_default_instantiation_level(self):
        result = self.vnfd_1.get_default_instantiation_level(SAMPLE_FLAVOUR_ID)
        self.assertEqual('instantiation_level_1', result)

    def test_get_vdu_num(self):
        result = self.vnfd_1.get_vdu_num(SAMPLE_FLAVOUR_ID, 'VDU1',
            'instantiation_level_2')
        self.assertEqual(3, result)

    def test_get_placement_groups(self):
        expected_result = {'affinityOrAntiAffinityGroup1': ['VDU1', 'VDU2']}
        result = self.vnfd_1.get_placement_groups(SAMPLE_FLAVOUR_ID)
        self.assertEqual(expected_result, result)

    def test_get_target(self):
        result = self.vnfd_1.get_affinity_targets(SAMPLE_FLAVOUR_ID)
        self.assertEqual([(['VDU2'], 'zone')], result)

        expected_result = [(['VDU1', 'VDU2'], 'nfvi_node')]
        result = self.vnfd_1.get_anti_affinity_targets(SAMPLE_FLAVOUR_ID)
        self.assertEqual(expected_result, result)

    def test_get_interface_script(self):
        # script specified
        result = self.vnfd_1.get_interface_script(SAMPLE_FLAVOUR_ID,
            "instantiate_start")
        self.assertEqual("../Scripts/sample_script.py", result)

        # [] specified
        result = self.vnfd_1.get_interface_script(SAMPLE_FLAVOUR_ID,
            "scale_start")
        self.assertEqual(None, result)

        # not specified
        result = self.vnfd_1.get_interface_script(SAMPLE_FLAVOUR_ID,
            "scale_end")
        self.assertEqual(None, result)

    def test_get_scale_vdu_and_num(self):
        expected_result = {'VDU1': 1}
        result = self.vnfd_1.get_scale_vdu_and_num(SAMPLE_FLAVOUR_ID,
            'VDU1_scale')
        self.assertEqual(expected_result, result)

    def test_get_scale_vdu_and_num_no_delta(self):
        self.assertRaises(sol_ex.DeltaMissingInVnfd,
            self.vnfd_1.get_scale_vdu_and_num, SAMPLE_FLAVOUR_ID,
            'Invalid_scale')

    def test_get_scale_info_from_inst_level(self):
        expected_result = {'VDU1_scale': {'scale_level': 2}}
        result = self.vnfd_1.get_scale_info_from_inst_level(
            SAMPLE_FLAVOUR_ID, 'instantiation_level_2')
        self.assertEqual(expected_result, result)

    def test_get_max_scale_level(self):
        result = self.vnfd_1.get_max_scale_level(SAMPLE_FLAVOUR_ID,
            'VDU1_scale')
        self.assertEqual(2, result)

    def test_init_from_zip_data(self):
        vnfd_id = uuidutils.generate_uuid()
        tmp_dir = tempfile.mkdtemp()
        sample_path = self._sample_dir("sample1")
        shutil.make_archive(tmp_dir, 'zip', root_dir=sample_path)

        vnfd = vnfd_utils.Vnfd(vnfd_id)
        with open(f'{tmp_dir}.zip', "rb") as f:
            content = f.read()
        vnfd.init_from_zip_data(content)
        with open(f'{sample_path}/TOSCA-Metadata/TOSCA.meta', 'r') as f:
            tosca_content = yaml.safe_load(f.read())
        with open(f'{sample_path}/Definitions/'
                  f'ut_sample1_df_simple.yaml', 'r') as f:
            definition_content = yaml.safe_load(f.read())
        self.assertEqual(tosca_content, vnfd.tosca_meta)
        self.assertEqual(
            definition_content, vnfd.definitions['ut_sample1_df_simple.yaml'])

    def test_init_vnfd_error(self):
        vnfd_id = uuidutils.generate_uuid()
        vnfd = vnfd_utils.Vnfd(vnfd_id)
        csar_dir = 'test'
        self.assertRaises(sol_ex.InvalidVnfdFormat, vnfd._init_vnfd, csar_dir)

    def test_get_vnfd_properties(self):
        vnfd_id = uuidutils.generate_uuid()
        vnfd = vnfd_utils.Vnfd(vnfd_id)
        expected_result = {
            'vnfConfigurableProperties': {},
            'extensions': {},
            'metadata': {}
        }
        result = vnfd.get_vnfd_properties()
        self.assertEqual(expected_result, result)

    def test_get_base_hot_abnormal(self):
        flavour_id = 'simple'
        vnfd_id = uuidutils.generate_uuid()
        vnfd = vnfd_utils.Vnfd(vnfd_id)
        vnfd.csar_dir = '/test/'
        base_hot_result = vnfd.get_base_hot(flavour_id)
        self.assertEqual({}, base_hot_result)

        flavour_id = 'error'
        base_hot_result = self.vnfd_1.get_base_hot(flavour_id)
        self.assertIsNotNone(base_hot_result['template'])

    def test_remove_tmp_csar_dir(self):
        os.mkdir("/tmp/test")
        vnfd_id = uuidutils.generate_uuid()
        vnfd = vnfd_utils.Vnfd(vnfd_id)
        tmp_dir = "/tmp/test"
        vnfd.remove_tmp_csar_dir(tmp_dir)
        result = os.path.isdir(tmp_dir)
        self.assertEqual(False, result)

    def test_remove_tmp_csar_dir_error(self):
        vnfd_id = uuidutils.generate_uuid()
        vnfd = vnfd_utils.Vnfd(vnfd_id)
        log_name = "tacker.sol_refactored.common.vnfd_utils"
        with self.assertLogs(logger=log_name, level=logging.DEBUG) as cm:
            vnfd.remove_tmp_csar_dir('test')

        msg = (f'ERROR:{log_name}:rmtree test failed')
        self.assertIn(f'{msg}', cm.output[0].split('\n')[0])

    def test_get_policy_values_by_type(self):
        result = self.vnfd_1.get_policy_values_by_type(
            'error', 'tosca.policies.nfv.AntiAffinityRule')
        self.assertEqual('nfvi_node', result[0]['properties']['scope'])

    def test_get_vdu_num_none(self):
        result = self.vnfd_1.get_vdu_num('error', 'VDU1', 'default')
        self.assertEqual(0, result)

    def test_get_affinity_targets(self):
        result = self.vnfd_1.get_affinity_targets('error')
        expected_result = [(['VDU3'], 'zone')]
        self.assertEqual(expected_result, result)

    def test_get_interface_script_abnormal(self):
        result = self.vnfd_1.get_interface_script('error', 'instantiate_start')
        self.assertEqual(None, result)

        result = self.vnfd_1.get_interface_script('error', 'instantiate_end')
        self.assertEqual(None, result)

        self.vnfd_1.get_interface_script('error', 'instantiate_end')
        self.assertRaises(
            sol_ex.SolHttpError422, self.vnfd_1.get_interface_script,
            'error', 'terminate_start')

    def test_get_scale_vdu_and_num_abnormal(self):
        result = self.vnfd_1.get_scale_vdu_and_num('error', 'VDU1_scale')
        self.assertEqual({}, result)

    def test_get_scale_info_from_inst_level_abnormal(self):
        result = self.vnfd_1.get_scale_info_from_inst_level('error', 'default')
        self.assertEqual({}, result)

    def test_get_max_scale_level_abnormal(self):
        result = self.vnfd_1.get_max_scale_level('error', 'VDU1_scale')
        self.assertEqual(0, result)

    def test_get_vnf_artifact_files_manifest(self):
        result = self.vnfd_1.get_vnf_artifact_files()
        expected_result = ['Scripts/install.sh',
                           'Files/kubernetes/deployment.yaml']
        self.assertEqual(expected_result, result)
