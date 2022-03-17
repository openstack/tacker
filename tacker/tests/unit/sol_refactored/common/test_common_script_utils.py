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

from tacker.sol_refactored.common import common_script_utils
from tacker.tests import base


SAMPLE_VNFD_ID = "b1bb0ce7-ebca-4fa7-95ed-4840d7000000"
SAMPLE_FLAVOUR_ID = "simple"


class TestCommontScriptUtils(base.BaseTestCase):

    def setUp(self):
        super(TestCommontScriptUtils, self).setUp()
        cur_dir = os.path.dirname(__file__)
        sample_dir = os.path.join(cur_dir, "..", "samples")

        self.vnfd_1 = common_script_utils.get_vnfd(SAMPLE_VNFD_ID,
            os.path.join(sample_dir, "sample1"))

    def test_init_nfv_dict(self):
        hot_dict = self.vnfd_1.get_base_hot(SAMPLE_FLAVOUR_ID)
        top_hot = hot_dict['template']

        expected_result = {
            'VDU': {
                'VDU1': {'computeFlavourId': None},
                'VirtualStorage': {'vcImageId': None},
                'VDU2': {'computeFlavourId': None, 'vcImageId': None}
            },
            'CP': {
                'VDU1_CP1': {'network': None},
                'VDU1_CP2': {'network': None,
                             'fixed_ips': {0: {'subnet': None}}},
                'VDU2_CP1': {'network': None,
                             'fixed_ips': {0: {'ip_address': None}}},
                'VDU2_CP2': {'network': None,
                             'fixed_ips': {0: {'ip_address': None,
                                               'subnet': None}}}
            }
        }
        result = common_script_utils.init_nfv_dict(top_hot)
        self.assertEqual(expected_result, result)

    def test_get_param_flavor(self):
        flavor = 'm1.large'
        grant = {
            'vimAssets': {
                'computeResourceFlavours': [
                    {'vnfdVirtualComputeDescId': 'VDU1',
                     'vimFlavourId': flavor}
                ]
            }
        }

        result = common_script_utils.get_param_flavor(
            'VDU1', SAMPLE_FLAVOUR_ID,
            self.vnfd_1, grant)
        self.assertEqual(flavor, result)

        # if not exist in grant, get from VNFD
        result = common_script_utils.get_param_flavor(
            'VDU2', SAMPLE_FLAVOUR_ID,
            self.vnfd_1, grant)
        self.assertEqual('m1.tiny', result)

    def test_get_param_image(self):
        image_id = 'f30e149d-b3c7-497a-8b19-a092bc81e47b'
        grant = {
            'vimAssets': {
                'softwareImages': [
                    {'vnfdSoftwareImageId': 'VDU2',
                     'vimSoftwareImageId': image_id},
                    {'vnfdSoftwareImageId': 'VirtualStorage',
                     'vimSoftwareImageId': 'image-1.0.0-x86_64-disk'}
                ]
            }
        }

        result = common_script_utils.get_param_image('VDU2', SAMPLE_FLAVOUR_ID,
            self.vnfd_1, grant)
        self.assertEqual(image_id, result)

    def test_get_param_zone(self):
        grant_req = {
            'addResources': [
                {'id': 'dd60c89a-29a2-43bc-8cff-a534515523df',
                 'type': 'COMPUTE', 'resourceTemplateId': 'VDU1'}
            ]
        }
        grant = {
            'zones': [
                {'id': '717f6ae9-3094-46b6-b070-89ede8337571',
                 'zoneId': 'nova'}
            ],
            'addResources': [
                {'resourceDefinitionId':
                    'dd60c89a-29a2-43bc-8cff-a534515523df',
                 'zoneId': '717f6ae9-3094-46b6-b070-89ede8337571'}
            ]
        }

        result = common_script_utils.get_param_zone('VDU1', grant_req, grant)
        self.assertEqual('nova', result)

    def test_get_param_capacity(self):
        # test get_current_capacity at the same time
        grant_req = {
            'addResources': [
                {'id': 'dd60c89a-29a2-43bc-8cff-a534515523df',
                 'type': 'COMPUTE', 'resourceTemplateId': 'VDU1'},
                {'id': '49b99140-c897-478c-83fa-ba3698912b18',
                 'type': 'COMPUTE', 'resourceTemplateId': 'VDU1'},
                {'id': 'b03c4b75-ca17-4773-8a50-9a53df78a007',
                 'type': 'COMPUTE', 'resourceTemplateId': 'VDU2'}
            ],
            'removeResources': [
                {'id': '0837249d-ac2a-4963-bf98-bc0755eec663',
                 'type': 'COMPUTE', 'resourceTemplateId': 'VDU1'},
                {'id': '3904e9d1-c0ec-4c3c-b29e-c8942a20f866',
                 'type': 'COMPUTE', 'resourceTemplateId': 'VDU2'}
            ]
        }
        inst = {
            'instantiatedVnfInfo': {
                'vnfcResourceInfo': [
                    {'id': 'cdf36e11-f6ca-4c80-aaf1-0d2e764a2f3a',
                     'vduId': 'VDU2'},
                    {'id': 'c8cb522d-ddf8-4136-9c85-92bab8f2993d',
                     'vduId': 'VDU1'}
                ]
            }
        }

        result = common_script_utils.get_param_capacity(
            'VDU1', inst, grant_req)
        self.assertEqual(2, result)
        result = common_script_utils.get_param_capacity(
            'VDU2', inst, grant_req)
        self.assertEqual(1, result)

    def test_get_parama_network(self):
        res_id = "8fe7cc1a-e4ac-41b9-8b89-ed14689adb9c"
        req = {
            "extVirtualLinks": [
                {
                    "id": "acf5c23a-02d3-42e6-801b-fba0314bb6aa",
                    "resourceId": res_id,
                    "extCps": [
                        {
                            "cpdId": "VDU1_CP1",
                            "cpConfig": {}  # omit
                        }
                    ]
                }
            ]
        }

        result = common_script_utils.get_param_network('VDU1_CP1', {}, req)
        self.assertEqual(res_id, result)

    def test_get_param_fixed_ips(self):
        ip_address = "10.10.1.101"
        subnet_id = "9defebca-3e9c-4bd2-9fa0-c4210c56ece6"
        ext_cp = {
            "cpdId": "VDU2_CP2",
            "cpConfig": {
                "VDU2_CP2_1": {
                    "cpProtocolData": [
                        {
                            "layerProtocol": "IP_OVER_ETHERNET",
                            "ipOverEthernet": {
                                "ipAddresses": [
                                    {
                                        "type": "IPV4",
                                        "fixedAddresses": [
                                            ip_address
                                        ],
                                        "subnetId": subnet_id
                                    }
                                ]
                            }
                        }
                    ]
                }
            }
        }
        req = {
            "extVirtualLinks": [
                {
                    "id": "8b49f4b6-1ff9-4a03-99cf-ff445b788436",
                    "resourceId": "4c54f742-5f1d-4287-bb81-37bf2e6ddc3e",
                    "extCps": [ext_cp]
                }
            ]
        }
        expected_result = [{'ip_address': ip_address, 'subnet': subnet_id}]

        result = common_script_utils.get_param_fixed_ips('VDU2_CP2', {}, req)
        self.assertEqual(expected_result, result)

    def _inst_example_get_network_fixed_ips_from_inst(self):
        ext_cp = {
            "cpdId": "VDU2_CP2",
            "cpConfig": {
                "VDU2_CP2_1": {
                    "cpProtocolData": [
                        {
                            "layerProtocol": "IP_OVER_ETHERNET",
                            "ipOverEthernet": {
                                "ipAddresses": [
                                    {
                                        "type": "IPV4",
                                        "fixedAddresses": [
                                            "ip_address"
                                        ],
                                        "subnetId": "subnet_id"
                                    }
                                ]
                            }
                        }
                    ]
                }
            }
        }
        inst = {
            "instantiatedVnfInfo": {
                "extVirtualLinkInfo": [
                    {
                        "id": "8b49f4b6-1ff9-4a03-99cf-ff445b788436",
                        "resourceHandle": {
                            "resourceId": "ext_vl_res_id"
                        },
                        "currentVnfExtCpData": [ext_cp]
                    }
                ]
            }
        }
        return inst

    def test_get_parama_network_from_inst(self):
        inst = self._inst_example_get_network_fixed_ips_from_inst()

        result = common_script_utils.get_param_network_from_inst(
            'VDU2_CP2', inst)
        self.assertEqual("ext_vl_res_id", result)

    def test_get_param_fixed_ips_from_inst(self):
        inst = self._inst_example_get_network_fixed_ips_from_inst()

        expected_result = [{'ip_address': 'ip_address', 'subnet': 'subnet_id'}]

        result = common_script_utils.get_param_fixed_ips_from_inst(
            'VDU2_CP2', inst)
        self.assertEqual(expected_result, result)

    def test_apply_ext_managed_vls(self):
        hot_dict = self.vnfd_1.get_base_hot(SAMPLE_FLAVOUR_ID)
        top_hot = hot_dict['template']

        res_id = "c738c2bb-1d24-4883-a2d8-a5c7c4ee8879"
        vl = "internalVL1"
        vl_subnet = "internalVL1_subnet"
        req = {
            "extManagedVirtualLinks": [
                {
                    "id": "1c7825cf-b883-4281-b8fc-ee006df8b2ba",
                    "vnfVirtualLinkDescId": vl,
                    "resourceId": res_id
                }
            ]
        }

        # make sure before apply
        self.assertEqual({'get_resource': vl},
            top_hot['resources']['VDU1_scale_group']['properties']
            ['resource']['properties']['net3'])
        self.assertEqual({'get_resource': vl},
            top_hot['resources']['VDU2_CP3']['properties']['network'])
        self.assertIn(vl, top_hot['resources'])
        self.assertIn(vl_subnet, top_hot['resources'])

        common_script_utils.apply_ext_managed_vls(top_hot, req, {})

        # check after
        # replaced to resource id
        self.assertEqual(res_id,
            top_hot['resources']['VDU1_scale_group']['properties']
            ['resource']['properties']['net3'])
        self.assertEqual(res_id,
            top_hot['resources']['VDU2_CP3']['properties']['network'])
        # removed
        self.assertNotIn(vl, top_hot['resources'])
        self.assertNotIn(vl_subnet, top_hot['resources'])
