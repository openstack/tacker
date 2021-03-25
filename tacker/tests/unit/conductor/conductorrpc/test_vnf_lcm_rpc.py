# Copyright (C) 2021 FUJITSU
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

from tacker.common.rpc import BackingOffClient
from tacker.conductor.conductorrpc import vnf_lcm_rpc
from tacker.tests import base


class VnfLcmRPCTestCase(base.BaseTestCase):

    def setUp(self):
        super(VnfLcmRPCTestCase, self).setUp()
        self.context = self.fake_admin_context()
        self.rpc_api = vnf_lcm_rpc.VNFLcmRPCAPI()
        self.cctxt_mock = mock.MagicMock()

    @mock.patch.object(BackingOffClient, 'prepare')
    def test_instantiate(self, prepare_mock):
        vnf_instance = ""
        vnf = ""
        instantiate_vnf = ""
        vnf_lcm_op_occs_id = ""
        prepare_mock.return_value = self.cctxt_mock
        self.rpc_api.instantiate(
            self.context, vnf_instance,
            vnf, instantiate_vnf, vnf_lcm_op_occs_id)
        prepare_mock.assert_called()
        self.cctxt_mock.cast.assert_called_once_with(
            self.context, 'instantiate',
            vnf_instance=vnf_instance,
            vnf_dict=vnf,
            instantiate_vnf=instantiate_vnf,
            vnf_lcm_op_occs_id=vnf_lcm_op_occs_id)

    @mock.patch.object(BackingOffClient, 'prepare')
    def test_terminate(self, prepare_mock):
        vnf_instance = ""
        vnf = ""
        terminate_vnf_req = ""
        vnf_lcm_op_occs_id = ""
        prepare_mock.return_value = self.cctxt_mock
        self.rpc_api.terminate(
            self.context, terminate_vnf_req,
            vnf, terminate_vnf_req, vnf_lcm_op_occs_id)
        prepare_mock.assert_called()
        self.cctxt_mock.cast.assert_called_once_with(
            self.context, 'terminate',
            vnf_instance=vnf_instance,
            vnf_dict=vnf,
            terminate_vnf_req=terminate_vnf_req,
            vnf_lcm_op_occs_id=vnf_lcm_op_occs_id)

    @mock.patch.object(BackingOffClient, 'prepare')
    def test_heal(self, prepare_mock):
        vnf_instance = ""
        vnf = ""
        heal_vnf_request = ""
        vnf_lcm_op_occs_id = ""
        prepare_mock.return_value = self.cctxt_mock
        self.rpc_api.heal(
            self.context, heal_vnf_request,
            vnf, heal_vnf_request, vnf_lcm_op_occs_id)
        prepare_mock.assert_called()
        self.cctxt_mock.cast.assert_called_once_with(
            self.context, 'heal',
            vnf_instance=vnf_instance,
            vnf_dict=vnf,
            heal_vnf_request=heal_vnf_request,
            vnf_lcm_op_occs_id=vnf_lcm_op_occs_id)

    @mock.patch.object(BackingOffClient, 'prepare')
    def test_scale(self, prepare_mock):
        vnf_info = ""
        vnf_instance = ""
        scale_vnf_request = ""
        prepare_mock.return_value = self.cctxt_mock
        self.rpc_api.scale(
            self.context, vnf_info,
            vnf_instance, scale_vnf_request)
        prepare_mock.assert_called()
        self.cctxt_mock.cast.assert_called_once_with(
            self.context, 'scale',
            vnf_info=vnf_info,
            vnf_instance=vnf_instance,
            scale_vnf_request=scale_vnf_request)

    @mock.patch.object(BackingOffClient, 'prepare')
    def test_update(self, prepare_mock):
        vnf_lcm_opoccs = ""
        body_data = ""
        vnfd_pkg_data = ""
        vnfd_id = ""
        prepare_mock.return_value = self.cctxt_mock
        self.rpc_api.update(
            self.context, vnf_lcm_opoccs,
            body_data, vnfd_pkg_data, vnfd_id)
        prepare_mock.assert_called()
        self.cctxt_mock.cast.assert_called_once_with(
            self.context, 'update',
            vnf_lcm_opoccs=vnf_lcm_opoccs,
            body_data=body_data,
            vnfd_pkg_data=vnfd_pkg_data,
            vnfd_id=vnfd_id)

    @mock.patch.object(BackingOffClient, 'prepare')
    def test_rollback(self, prepare_mock):
        vnf_info = ""
        vnf_instance = ""
        operation_params = ""
        prepare_mock.return_value = self.cctxt_mock
        self.rpc_api.rollback(
            self.context, vnf_info,
            vnf_instance, operation_params)
        prepare_mock.assert_called()
        self.cctxt_mock.cast.assert_called_once_with(
            self.context, 'rollback',
            vnf_info=vnf_info,
            vnf_instance=vnf_instance,
            operation_params=operation_params)
