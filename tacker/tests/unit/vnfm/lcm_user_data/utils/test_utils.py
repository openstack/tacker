#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import os
import testtools
import yaml

from tacker.objects import instantiate_vnf_req
from tacker.tests import constants
from tacker.vnfm.lcm_user_data import utils

default_initial_param_dict = {
    'nfv': {
        'VDU': {
        },
        'CP': {
        }
    }
}

example_initial_param_dict = {
    'nfv': {
        'VDU': {
            'VDU1': {},
        },
        'CP': {
            'CP1': {},
        }
    }
}


class TestUtils(testtools.TestCase):

    def _read_file(self, input_file):
        yaml_file = os.path.abspath(os.path.join(os.path.dirname(__file__),
                    "../../../../etc/samples/",
                    str(input_file)))
        with open(yaml_file, 'r') as f:
            yaml_file_dict = yaml.safe_load(f)
        return yaml_file_dict

    def test_create_initial_param_dict(self):
        base_hot_dict = {}
        base_hot_dict['resources'] = self._read_file("hot_lcm_user_data.yaml")
        initial_param_dict = utils.create_initial_param_dict(base_hot_dict)
        self.assertEqual(example_initial_param_dict, initial_param_dict)

    def test_create_initial_param_dict_empty_argument(self):
        base_hot_dict = {}
        initial_param_dict = utils.create_initial_param_dict(base_hot_dict)
        self.assertEqual(default_initial_param_dict, initial_param_dict)

    def test_create_final_param_dict(self):
        initial_param_dict = {
            'nfv': {
                'CP': {
                    'CP1': {
                        'network': 'cp1_network_id'
                    }
                },
                'VDU': {
                    'VDU1': {
                        'image': 'vdu1_image_uuid',
                        'flavor': {
                            'ram': 'vdu1_flavor_ram'
                        }
                    }
                }
            }
        }
        vdu_flavor_dict = {'VDU1': {'ram': 'vdu1_flavor_ram_change'}}
        vdu_image_dict = {'VDU1': 'vdu1_image_uuid_change'}
        cpd_vl_dict = {'CP1': {'cp1_network_id_change_1',
                               'cp1_network_id_change_2'}}
        expected_final_param_dict = {
            'nfv': {
                'CP': {
                    'CP1': {
                        'network': {
                            'cp1_network_id_change_1',
                            'cp1_network_id_change_2'
                        }
                    }
                },
                'VDU': {
                    'VDU1': {
                        'image': 'vdu1_image_uuid_change',
                        'flavor': {
                            'ram': 'vdu1_flavor_ram_change'
                        }
                    }
                }
            }
        }
        actual_final_param_dict = utils.create_final_param_dict(
            initial_param_dict, vdu_flavor_dict, vdu_image_dict, cpd_vl_dict)
        self.assertEqual(expected_final_param_dict, actual_final_param_dict)

    def test_create_final_param_dict_empty_value(self):
        initial_param_dict = {'nfv': {'VDU': '', 'CP': ''}}
        expected_final_param_dict = {'nfv': {'VDU': '', 'CP': ''}}
        vdu_flavor_dict = {}
        vdu_image_dict = {}
        cpd_vl_dict = {}
        actual_final_param_dict = utils.create_final_param_dict(
            initial_param_dict, vdu_flavor_dict, vdu_image_dict, cpd_vl_dict)
        self.assertEqual(expected_final_param_dict, actual_final_param_dict)

    def test_create_final_param_dict_empty_argument(self):
        initial_param_dict = {}
        expected_final_param_dict = {}
        vdu_flavor_dict = {}
        vdu_image_dict = {}
        cpd_vl_dict = {}
        actual_final_param_dict = utils.create_final_param_dict(
            initial_param_dict, vdu_flavor_dict, vdu_image_dict, cpd_vl_dict)
        self.assertEqual(expected_final_param_dict, actual_final_param_dict)

    def test_create_vdu_flavor_dict(self):
        vnfd_dict = self._read_file('vnfd_lcm_user_data.yaml')
        test_vnfd_dict = {'VNF': {}, 'VDU1':
                {'ram': 512, 'vcpus': 1, 'disk': 1}, 'CP1': {}}
        vdu_flavor_dict = utils.create_vdu_flavor_dict(vnfd_dict)
        self.assertEqual(test_vnfd_dict, vdu_flavor_dict)

    def test_create_vdu_flavor_dict_empty_argument(self):
        vnfd_dict = {}
        vdu_flavor_dict = utils.create_vdu_flavor_dict(vnfd_dict)
        self.assertEqual({}, vdu_flavor_dict)

    def test_create_vdu_image_dict(self):
        vnf_resource = type('', (), {})
        resource_identifier = constants.INVALID_UUID
        vnf_resource.resource_identifier = resource_identifier
        grant_info = {'vdu_name': {vnf_resource}}

        vdu_image_dict = utils.create_vdu_image_dict(grant_info)
        self.assertEqual({'vdu_name': resource_identifier}, vdu_image_dict)

    def test_create_vdu_image_dict_empty_argument(self):
        grant_info = {}
        vdu_image_dict = utils.create_vdu_image_dict(grant_info)
        self.assertEqual({}, vdu_image_dict)

    def test_create_cpd_vl_dict(self):
        base_hot_dict = \
            {'resources': {'resources': {'dummy_cpd_id': "101010_d"}}}
        inst_req_info = instantiate_vnf_req.InstantiateVnfRequest()
        ext_virtual_links_test_value = instantiate_vnf_req.ExtVirtualLinkData()
        ext_virtual_links_test_value.resource_id = 'dummy_resource_id'

        ext_virtual_links_ext_cps = []
        ext_virtual_links_ext_cps_value = instantiate_vnf_req.VnfExtCpData()
        ext_virtual_links_ext_cps_value.cpd_id = 'dummy_cpd_id'
        ext_virtual_links_ext_cps.append(ext_virtual_links_ext_cps_value)

        ext_virtual_links_test_value.ext_cps = ext_virtual_links_ext_cps
        inst_req_info.ext_virtual_links.append(ext_virtual_links_test_value)
        cpd_vl_dict = utils.create_cpd_vl_dict(base_hot_dict, inst_req_info)
        self.assertEqual({'dummy_cpd_id': 'dummy_resource_id'}, cpd_vl_dict)

    def test_create_cpd_vl_dict_no_cp_resource(self):
        base_hot_dict = \
            {'resources': {'resources': {'dummy_cpd_id': "101010_d"}}}
        inst_req_info = instantiate_vnf_req.InstantiateVnfRequest()
        ext_virtual_links_test_value = instantiate_vnf_req.ExtVirtualLinkData()
        ext_virtual_links_test_value.resource_id = 'dummy_resource_id'

        ext_virtual_links_ext_cps = []
        ext_virtual_links_ext_cps_value = instantiate_vnf_req.VnfExtCpData()
        ext_virtual_links_ext_cps_value.cpd_id = ""
        ext_virtual_links_ext_cps.append(ext_virtual_links_ext_cps_value)

        ext_virtual_links_test_value.ext_cps = ext_virtual_links_ext_cps
        inst_req_info.ext_virtual_links.append(ext_virtual_links_test_value)
        cpd_vl_dict = utils.create_cpd_vl_dict(base_hot_dict, inst_req_info)
        self.assertEqual({}, cpd_vl_dict)

    def test_create_cpd_vl_dict_empty_argument(self):
        base_hot_dict = {}
        inst_req_info = type('', (), {})
        inst_req_info.ext_virtual_links = None
        cpd_vl_dict = utils.create_cpd_vl_dict(base_hot_dict, inst_req_info)
        self.assertEqual({}, cpd_vl_dict)
