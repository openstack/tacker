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
from unittest import mock

from tacker import context
from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.common import vnf_instance_utils as inst_utils
from tacker.sol_refactored import objects
from tacker.tests import base


class TestVnfInstanceUtils(base.BaseTestCase):
    def setUp(self):
        super(TestVnfInstanceUtils, self).setUp()
        objects.register_all()
        self.context = context.get_admin_context()

    def _get_inst_example(self, kubernetes_type):
        return {
            'id': 'inst-1',
            "vimConnectionInfo": {
                "vim1": {
                    "vimType": kubernetes_type,
                    "vimId": 'vim_id_1',
                    "interfaceInfo": {"endpoint": "https://127.0.0.1:6443"},
                    "accessInfo": {
                        "bearer_token": "secret_token",
                        "region": "RegionOne"
                    }
                }
            }
        }

    def test_json_merge_patch(self):
        # patch is not dict.
        target = {"key1": "value1"}
        patch = "text"
        result = inst_utils.json_merge_patch(target, patch)
        self.assertEqual(patch, result)

        # target is not dict.
        target = "text"
        patch = {"key1": "value1"}
        result = inst_utils.json_merge_patch(target, patch)
        self.assertEqual(patch, result)

        # normal case
        target = {
            "key1": "value1",  # remine
            "key2": "value2",  # modify
            "key3": "value3",  # delete
            "key4": {  # nested
                "key4_1": "value4_1",  # remine
                "key4_2": "value4_2",  # modify
                "key4_3": {"key4_3_1", "value4_3_1"}  # delete
            }
        }
        patch = {
            "key2": "value2_x",  # modify
            "key3": None,  # delete
            "key4": {
                "key4_2": "value4_2_x",  # modify
                "key4_3": None,  # delete
                "key4_4": "value4_4"  # add
            },
            "key5": "value5"  # add
        }
        expected_result = {
            "key1": "value1",
            "key2": "value2_x",
            "key4": {
                "key4_1": "value4_1",
                "key4_2": "value4_2_x",
                "key4_4": "value4_4"
            },
            "key5": "value5"
        }
        result = inst_utils.json_merge_patch(target, patch)
        self.assertEqual(expected_result, result)

    @mock.patch.object(objects.base.TackerPersistentObject, 'get_by_id')
    def test_get_inst(self, mock_inst):
        mock_inst.return_value = objects.VnfInstanceV2(id='inst-1')

        result = inst_utils.get_inst(context, 'inst-1')
        self.assertEqual('inst-1', result.id)

    @mock.patch.object(objects.base.TackerPersistentObject, 'get_by_id')
    def test_get_inst_error(self, mock_inst):
        mock_inst.return_value = None
        self.assertRaises(
            sol_ex.VnfInstanceNotFound,
            inst_utils.get_inst, context, 'inst-1')

    @mock.patch.object(objects.base.TackerPersistentObject, 'get_all')
    def test_get_inst_all(self, mock_inst):
        mock_inst.return_value = [objects.VnfInstanceV2(id='inst-1')]

        result = inst_utils.get_inst_all(context)
        self.assertEqual('inst-1', result[0].id)

    def test_select_vim_info(self):
        # vimType is kubernetes
        inst = objects.VnfInstanceV2.from_dict(
            self._get_inst_example('kubernetes'))
        result = inst_utils.select_vim_info(inst.vimConnectionInfo)
        self.assertEqual(
            'ETSINFV.KUBERNETES.V_1', inst.vimConnectionInfo['vim1'].vimType)
        self.assertEqual('ETSINFV.KUBERNETES.V_1', result.vimType)

        # vimType is 'ETSINFV.KUBERNETES.V_1'
        inst = objects.VnfInstanceV2.from_dict(
            self._get_inst_example('ETSINFV.KUBERNETES.V_1'))
        result = inst_utils.select_vim_info(inst.vimConnectionInfo)
        self.assertEqual(
            'ETSINFV.KUBERNETES.V_1', inst.vimConnectionInfo['vim1'].vimType)
        self.assertEqual('ETSINFV.KUBERNETES.V_1', result.vimType)

        # vimType is 'ETSINFV.HELM.V_3'
        inst = objects.VnfInstanceV2.from_dict(
            self._get_inst_example('ETSINFV.HELM.V_3'))
        result = inst_utils.select_vim_info(inst.vimConnectionInfo)
        self.assertEqual(
            'ETSINFV.HELM.V_3', inst.vimConnectionInfo['vim1'].vimType)
        self.assertEqual('ETSINFV.HELM.V_3', result.vimType)

    def test_check_metadata(self):
        # VDU_VNFc_mapping is not dict
        metadata = {
            "VDU_VNFc_mapping": "a-001"
        }
        self.assertRaises(sol_ex.SolValidationError,
                          inst_utils.check_metadata_format, metadata)

        # VDU_VNFc_mapping dict value is not list.
        metadata = {
            "VDU_VNFc_mapping": {
                "VDU1": "a-001"
            }
        }
        self.assertRaises(sol_ex.SolValidationError,
                          inst_utils.check_metadata_format, metadata)

        # Duplicate vnfcInfo id.
        metadata = {
            "VDU_VNFc_mapping": {
                "VDU1": ["a-001", "a-002", "a-003"],
                "VDU2": ["a-002"]
            }
        }
        ex = self.assertRaises(sol_ex.SolValidationError,
                               inst_utils.check_metadata_format, metadata)
        expected_detail = ("Duplicated vnfcInfo ids found in "
                           "metadata['VDU_VNFc_mapping'].")
        self.assertEqual(expected_detail, ex.detail)
