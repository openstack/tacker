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

from datetime import datetime
from unittest import mock

import ddt
from oslo_utils import uuidutils

from tacker import context
from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.common import lcm_op_occ_utils as lcmocc_utils
from tacker.sol_refactored.conductor import conductor_v2
from tacker.sol_refactored.conductor import vnflcm_driver_v2
from tacker.sol_refactored.nfvo import nfvo_client
from tacker.sol_refactored import objects
from tacker.sol_refactored.objects.v2 import fields
from tacker.tests.unit.db import base as db_base


@ddt.ddt
class TestConductorV2(db_base.SqlTestCase):

    def setUp(self):
        super(TestConductorV2, self).setUp()
        objects.register_all()
        self.conductor = conductor_v2.ConductorV2()
        self.context = context.get_admin_context()

    def _create_inst_and_lcmocc(self,
            op_state=fields.LcmOperationStateType.STARTING):
        inst = objects.VnfInstanceV2(
            # required fields
            id=uuidutils.generate_uuid(),
            vnfdId=uuidutils.generate_uuid(),
            vnfProvider='provider',
            vnfProductName='product name',
            vnfSoftwareVersion='software version',
            vnfdVersion='vnfd version',
            instantiationState='NOT_INSTANTIATED'
        )

        req = {"flavourId": "simple"}  # instantiate request
        lcmocc = objects.VnfLcmOpOccV2(
            # required fields
            id=uuidutils.generate_uuid(),
            operationState=op_state,
            stateEnteredTime=datetime.utcnow(),
            startTime=datetime.utcnow(),
            vnfInstanceId=inst.id,
            operation=fields.LcmOperationType.INSTANTIATE,
            isAutomaticInvocation=False,
            isCancelPending=False,
            operationParams=req)

        inst.create(self.context)
        lcmocc.create(self.context)

        return lcmocc

    def _change_vnfpkg_lcmocc(
            self, op_state=fields.LcmOperationStateType.STARTING):
        inst = objects.VnfInstanceV2(
            # required fields
            id=uuidutils.generate_uuid(),
            vnfdId=uuidutils.generate_uuid(),
            vnfProvider='provider',
            vnfProductName='product name',
            vnfSoftwareVersion='software version',
            vnfdVersion='vnfd version',
            instantiationState='INSTANTIATED'
        )
        req = {"vnfdId": uuidutils.generate_uuid()}
        lcmocc = objects.VnfLcmOpOccV2(
            # required fields
            id=uuidutils.generate_uuid(),
            operationState=op_state,
            stateEnteredTime=datetime.utcnow(),
            startTime=datetime.utcnow(),
            vnfInstanceId=inst.id,
            operation=fields.LcmOperationType.CHANGE_VNFPKG,
            isAutomaticInvocation=False,
            isCancelPending=False,
            operationParams=req)

        inst.create(self.context)
        lcmocc.create(self.context)

        return lcmocc

    def _make_grant_req_and_grant(self, lcmocc):
        grant_req = objects.GrantRequestV1(
            # required fields
            vnfInstanceId=lcmocc.vnfInstanceId,
            vnfLcmOpOccId=lcmocc.id,
            vnfdId=uuidutils.generate_uuid(),
            operation=lcmocc.operation,
            isAutomaticInvocation=lcmocc.isAutomaticInvocation
        )
        grant = objects.GrantV1(
            # required fields
            id=uuidutils.generate_uuid(),
            vnfInstanceId=lcmocc.vnfInstanceId,
            vnfLcmOpOccId=lcmocc.id
        )

        return grant_req, grant

    def _create_grant_req_and_grant(self, lcmocc):
        grant_req, grant = self._make_grant_req_and_grant(lcmocc)
        grant_req.create(self.context)
        grant.create(self.context)
        lcmocc.grantId = grant.id
        lcmocc.update(self.context)

    @mock.patch.object(nfvo_client.NfvoClient, 'send_lcmocc_notification')
    @mock.patch.object(nfvo_client.NfvoClient, 'get_vnfd')
    @mock.patch.object(vnflcm_driver_v2.VnfLcmDriverV2, 'grant')
    @mock.patch.object(vnflcm_driver_v2.VnfLcmDriverV2, 'post_grant')
    @mock.patch.object(vnflcm_driver_v2.VnfLcmDriverV2, 'process')
    def test_start_lcm_op_completed(self, mocked_process, mocked_post_grant,
            mocked_grant, mocked_get_vnfd, mocked_send_lcmocc_notification):
        # prepare
        lcmocc = self._create_inst_and_lcmocc()
        mocked_get_vnfd.return_value = mock.Mock()
        grant_req, grant = self._make_grant_req_and_grant(lcmocc)
        lcmocc.grantId = grant.id
        mocked_grant.return_value = grant_req, grant

        op_state = []

        def _store_state(context, lcmocc, inst, endpoint):
            op_state.append(lcmocc.operationState)

        mocked_send_lcmocc_notification.side_effect = _store_state

        # run start_lcm_op
        self.conductor.start_lcm_op(self.context, lcmocc.id)

        # check operationState transition
        self.assertEqual(3, mocked_send_lcmocc_notification.call_count)
        self.assertEqual(fields.LcmOperationStateType.STARTING, op_state[0])
        self.assertEqual(fields.LcmOperationStateType.PROCESSING, op_state[1])
        self.assertEqual(fields.LcmOperationStateType.COMPLETED, op_state[2])

        # check grant_req and grant are deleted
        self.assertRaises(sol_ex.GrantRequestOrGrantNotFound,
            lcmocc_utils.get_grant_req_and_grant, self.context, lcmocc)

    @mock.patch.object(vnflcm_driver_v2.VnfLcmDriverV2, 'process')
    @mock.patch.object(nfvo_client.NfvoClient, 'send_lcmocc_notification')
    @mock.patch.object(nfvo_client.NfvoClient, 'get_vnfd')
    @mock.patch.object(vnflcm_driver_v2.VnfLcmDriverV2, 'grant')
    def test_start_lcm_op_change_vnfpkg_completed(
            self, mocked_grant, mocked_get_vnfd,
            mocked_send_lcmocc_notification, mocked_process):
        # prepare
        lcmocc = self._change_vnfpkg_lcmocc()
        mocked_get_vnfd.return_value = mock.Mock()
        mocked_grant.return_value = self._make_grant_req_and_grant(lcmocc)
        mocked_process.return_value = mock.Mock()
        op_state = []

        def _store_state(context, lcmocc, inst, endpoint):
            op_state.append(lcmocc.operationState)

        mocked_send_lcmocc_notification.side_effect = _store_state

        # run start_lcm_op
        self.conductor.start_lcm_op(self.context, lcmocc.id)

        # check operationState transition
        self.assertEqual(3, mocked_send_lcmocc_notification.call_count)
        self.assertEqual(fields.LcmOperationStateType.STARTING, op_state[0])
        self.assertEqual(fields.LcmOperationStateType.PROCESSING, op_state[1])
        self.assertEqual(fields.LcmOperationStateType.COMPLETED, op_state[2])

    @mock.patch.object(nfvo_client.NfvoClient, 'send_lcmocc_notification')
    @mock.patch.object(nfvo_client.NfvoClient, 'get_vnfd')
    @mock.patch.object(vnflcm_driver_v2.VnfLcmDriverV2, 'grant')
    def test_start_lcm_op_rolled_back(self,
            mocked_grant, mocked_get_vnfd, mocked_send_lcmocc_notification):
        # prepare
        lcmocc = self._create_inst_and_lcmocc()
        mocked_get_vnfd.return_value = mock.Mock()
        ex = sol_ex.LocalNfvoGrantFailed(sol_detail="unit test")
        mocked_grant.side_effect = ex

        op_state = []

        def _store_state(context, lcmocc, inst, endpoint):
            op_state.append(lcmocc.operationState)

        mocked_send_lcmocc_notification.side_effect = _store_state

        # run start_lcm_op
        self.conductor.start_lcm_op(self.context, lcmocc.id)

        # check operationState transition
        self.assertEqual(2, mocked_send_lcmocc_notification.call_count)
        self.assertEqual(fields.LcmOperationStateType.STARTING, op_state[0])
        self.assertEqual(fields.LcmOperationStateType.ROLLED_BACK, op_state[1])

        # check lcmocc.error
        # get lcmocc from DB to be sure lcmocc saved to DB
        lcmocc = lcmocc_utils.get_lcmocc(self.context, lcmocc.id)
        expected = ex.make_problem_details()
        self.assertEqual(expected, lcmocc.error.to_dict())

    @mock.patch.object(nfvo_client.NfvoClient, 'send_lcmocc_notification')
    @mock.patch.object(nfvo_client.NfvoClient, 'get_vnfd')
    @mock.patch.object(vnflcm_driver_v2.VnfLcmDriverV2, 'grant')
    @mock.patch.object(vnflcm_driver_v2.VnfLcmDriverV2, 'post_grant')
    @mock.patch.object(vnflcm_driver_v2.VnfLcmDriverV2, 'process')
    def test_start_lcm_op_failed_temp(self, mocked_process, mocked_post_grant,
            mocked_grant, mocked_get_vnfd, mocked_send_lcmocc_notification):
        # prepare
        lcmocc = self._create_inst_and_lcmocc()
        mocked_get_vnfd.return_value = mock.Mock()
        mocked_grant.return_value = self._make_grant_req_and_grant(lcmocc)
        ex = sol_ex.StackOperationFailed(sol_detail="unit test",
                                         sol_title="stack failed")
        mocked_process.side_effect = ex

        op_state = []

        def _store_state(context, lcmocc, inst, endpoint):
            op_state.append(lcmocc.operationState)

        mocked_send_lcmocc_notification.side_effect = _store_state

        # run start_lcm_op
        self.conductor.start_lcm_op(self.context, lcmocc.id)

        # check operationState transition
        self.assertEqual(3, mocked_send_lcmocc_notification.call_count)
        self.assertEqual(fields.LcmOperationStateType.STARTING, op_state[0])
        self.assertEqual(fields.LcmOperationStateType.PROCESSING, op_state[1])
        self.assertEqual(fields.LcmOperationStateType.FAILED_TEMP, op_state[2])

        # check lcmocc.error
        # get lcmocc from DB to be sure lcmocc saved to DB
        lcmocc = lcmocc_utils.get_lcmocc(self.context, lcmocc.id)
        expected = ex.make_problem_details()
        self.assertEqual(expected, lcmocc.error.to_dict())

        # check grant_req and grant are saved to DB
        # it's OK if no exception raised
        lcmocc_utils.get_grant_req_and_grant(self.context, lcmocc)

    @mock.patch.object(nfvo_client.NfvoClient, 'send_lcmocc_notification')
    @mock.patch.object(nfvo_client.NfvoClient, 'get_vnfd')
    @mock.patch.object(vnflcm_driver_v2.VnfLcmDriverV2, 'post_grant')
    @mock.patch.object(vnflcm_driver_v2.VnfLcmDriverV2, 'process')
    def test_retry_lcm_op_completed(self, mocked_process, mocked_post_grant,
            mocked_get_vnfd, mocked_send_lcmocc_notification):
        # prepare
        lcmocc = self._create_inst_and_lcmocc(
            op_state=fields.LcmOperationStateType.FAILED_TEMP)
        self._create_grant_req_and_grant(lcmocc)
        mocked_get_vnfd.return_value = mock.Mock()

        op_state = []

        def _store_state(context, lcmocc, inst, endpoint):
            op_state.append(lcmocc.operationState)

        mocked_send_lcmocc_notification.side_effect = _store_state

        # run retry_lcm_op
        self.conductor.retry_lcm_op(self.context, lcmocc.id)

        # check operationState transition
        self.assertEqual(2, mocked_send_lcmocc_notification.call_count)
        self.assertEqual(fields.LcmOperationStateType.PROCESSING, op_state[0])
        self.assertEqual(fields.LcmOperationStateType.COMPLETED, op_state[1])

        # check grant_req and grant are deleted
        self.assertRaises(sol_ex.GrantRequestOrGrantNotFound,
            lcmocc_utils.get_grant_req_and_grant, self.context, lcmocc)

    @mock.patch.object(nfvo_client.NfvoClient, 'send_lcmocc_notification')
    @mock.patch.object(nfvo_client.NfvoClient, 'get_vnfd')
    @mock.patch.object(vnflcm_driver_v2.VnfLcmDriverV2, 'post_grant')
    @mock.patch.object(vnflcm_driver_v2.VnfLcmDriverV2, 'process')
    def test_retry_lcm_op_failed_temp(self, mocked_process, mocked_post_grant,
            mocked_get_vnfd, mocked_send_lcmocc_notification):
        # prepare
        lcmocc = self._create_inst_and_lcmocc(
            op_state=fields.LcmOperationStateType.FAILED_TEMP)
        self._create_grant_req_and_grant(lcmocc)
        mocked_get_vnfd.return_value = mock.Mock()
        ex = sol_ex.StackOperationFailed(sol_detail="unit test",
                                         sol_title="stack failed")
        mocked_process.side_effect = ex

        op_state = []

        def _store_state(context, lcmocc, inst, endpoint):
            op_state.append(lcmocc.operationState)

        mocked_send_lcmocc_notification.side_effect = _store_state

        # run retry_lcm_op
        self.conductor.retry_lcm_op(self.context, lcmocc.id)

        # check operationState transition
        self.assertEqual(2, mocked_send_lcmocc_notification.call_count)
        self.assertEqual(fields.LcmOperationStateType.PROCESSING, op_state[0])
        self.assertEqual(fields.LcmOperationStateType.FAILED_TEMP, op_state[1])

        # check lcmocc.error
        # get lcmocc from DB to be sure lcmocc saved to DB
        lcmocc = lcmocc_utils.get_lcmocc(self.context, lcmocc.id)
        expected = ex.make_problem_details()
        self.assertEqual(expected, lcmocc.error.to_dict())

        # check grant_req and grant remain
        # it's OK if no exception raised
        lcmocc_utils.get_grant_req_and_grant(self.context, lcmocc)

    @mock.patch.object(nfvo_client.NfvoClient, 'send_lcmocc_notification')
    @mock.patch.object(nfvo_client.NfvoClient, 'get_vnfd')
    @mock.patch.object(vnflcm_driver_v2.VnfLcmDriverV2, 'post_grant')
    @mock.patch.object(vnflcm_driver_v2.VnfLcmDriverV2, 'rollback')
    def test_rollback_lcm_op_rolled_back(self, mocked_rollback,
            mocked_post_grant, mocked_get_vnfd,
            mocked_send_lcmocc_notification):
        # prepare
        lcmocc = self._create_inst_and_lcmocc(
            op_state=fields.LcmOperationStateType.FAILED_TEMP)
        self._create_grant_req_and_grant(lcmocc)
        mocked_get_vnfd.return_value = mock.Mock()

        op_state = []

        def _store_state(context, lcmocc, inst, endpoint):
            op_state.append(lcmocc.operationState)

        mocked_send_lcmocc_notification.side_effect = _store_state

        # run rollback_lcm_op
        self.conductor.rollback_lcm_op(self.context, lcmocc.id)

        # check operationState transition
        self.assertEqual(2, mocked_send_lcmocc_notification.call_count)
        self.assertEqual(fields.LcmOperationStateType.ROLLING_BACK,
                         op_state[0])
        self.assertEqual(fields.LcmOperationStateType.ROLLED_BACK, op_state[1])

        # check grant_req and grant are deleted
        self.assertRaises(sol_ex.GrantRequestOrGrantNotFound,
            lcmocc_utils.get_grant_req_and_grant, self.context, lcmocc)

    @mock.patch.object(nfvo_client.NfvoClient, 'send_lcmocc_notification')
    @mock.patch.object(nfvo_client.NfvoClient, 'get_vnfd')
    @mock.patch.object(vnflcm_driver_v2.VnfLcmDriverV2, 'post_grant')
    @mock.patch.object(vnflcm_driver_v2.VnfLcmDriverV2, 'rollback')
    def test_rollback_lcm_op_failed_temp(self, mocked_rollback,
            mocked_post_grant, mocked_get_vnfd,
            mocked_send_lcmocc_notification):
        # prepare
        lcmocc = self._create_inst_and_lcmocc(
            op_state=fields.LcmOperationStateType.FAILED_TEMP)
        self._create_grant_req_and_grant(lcmocc)
        mocked_get_vnfd.return_value = mock.Mock()
        ex = sol_ex.StackOperationFailed(sol_detail="unit test",
                                         sol_title="stack failed")
        mocked_rollback.side_effect = ex

        op_state = []

        def _store_state(context, lcmocc, inst, endpoint):
            op_state.append(lcmocc.operationState)

        mocked_send_lcmocc_notification.side_effect = _store_state

        # run rollback_lcm_op
        self.conductor.rollback_lcm_op(self.context, lcmocc.id)

        # check operationState transition
        self.assertEqual(2, mocked_send_lcmocc_notification.call_count)
        self.assertEqual(fields.LcmOperationStateType.ROLLING_BACK,
                         op_state[0])
        self.assertEqual(fields.LcmOperationStateType.FAILED_TEMP, op_state[1])

        # check lcmocc.error
        # get lcmocc from DB to be sure lcmocc saved to DB
        lcmocc = lcmocc_utils.get_lcmocc(self.context, lcmocc.id)
        expected = ex.make_problem_details()
        self.assertEqual(expected, lcmocc.error.to_dict())

        # check grant_req and grant remain
        # it's OK if no exception raised
        lcmocc_utils.get_grant_req_and_grant(self.context, lcmocc)

    @mock.patch.object(nfvo_client.NfvoClient, 'send_lcmocc_notification')
    @mock.patch.object(nfvo_client.NfvoClient, 'get_vnfd')
    @mock.patch.object(vnflcm_driver_v2.VnfLcmDriverV2, 'process')
    def test_modify_vnfinfo_lcm_op_completed(self, mocked_process,
            mocked_get_vnfd, mocked_send_lcmocc_notification):
        # prepare
        lcmocc = self._create_inst_and_lcmocc(
            op_state=fields.LcmOperationStateType.PROCESSING)
        mocked_get_vnfd.return_value = mock.Mock()

        op_state = []

        def _store_state(context, lcmocc, inst, endpoint):
            op_state.append(lcmocc.operationState)

        mocked_send_lcmocc_notification.side_effect = _store_state

        # run modify_vnfinfo
        self.conductor.modify_vnfinfo(self.context, lcmocc.id)

        # check operationState transition
        self.assertEqual(2, mocked_send_lcmocc_notification.call_count)
        self.assertEqual(fields.LcmOperationStateType.PROCESSING, op_state[0])
        self.assertEqual(fields.LcmOperationStateType.COMPLETED, op_state[1])

    @mock.patch.object(nfvo_client.NfvoClient, 'send_lcmocc_notification')
    @mock.patch.object(nfvo_client.NfvoClient, 'get_vnfd')
    @mock.patch.object(vnflcm_driver_v2.VnfLcmDriverV2, 'process')
    def test_modify_vnfinfo_lcm_op_failed_temp(self, mocked_process,
            mocked_get_vnfd, mocked_send_lcmocc_notification):
        # prepare
        lcmocc = self._create_inst_and_lcmocc(
            op_state=fields.LcmOperationStateType.PROCESSING)
        mocked_get_vnfd.return_value = mock.Mock()
        ex = sol_ex.StackOperationFailed(sol_detail="unit test",
                                         sol_title="stack failed")
        mocked_process.side_effect = ex

        op_state = []

        def _store_state(context, lcmocc, inst, endpoint):
            op_state.append(lcmocc.operationState)

        mocked_send_lcmocc_notification.side_effect = _store_state

        # run modify_vnfinfo
        self.conductor.modify_vnfinfo(self.context, lcmocc.id)

        # check operationState transition
        self.assertEqual(2, mocked_send_lcmocc_notification.call_count)
        self.assertEqual(fields.LcmOperationStateType.PROCESSING, op_state[0])
        self.assertEqual(fields.LcmOperationStateType.FAILED_TEMP, op_state[1])

        # check lcmocc.error
        # get lcmocc from DB to be sure lcmocc saved to DB
        lcmocc = lcmocc_utils.get_lcmocc(self.context, lcmocc.id)
        expected = ex.make_problem_details()
        self.assertEqual(expected, lcmocc.error.to_dict())

    def _prepare_change_lcm_op_state(self, op_state):
        inst = objects.VnfInstanceV2(
            # required fields
            id=uuidutils.generate_uuid(),
            vnfdId=uuidutils.generate_uuid(),
            vnfProvider='provider',
            vnfProductName='product name',
            vnfSoftwareVersion='software version',
            vnfdVersion='vnfd version',
            instantiationState='INSTANTIATED'
        )

        req = {"flavourId": "simple"}  # instantiate request
        lcmocc = objects.VnfLcmOpOccV2(
            # required fields
            id=uuidutils.generate_uuid(),
            operationState=op_state,
            stateEnteredTime=datetime.utcnow(),
            startTime=datetime.utcnow(),
            vnfInstanceId=inst.id,
            operation=fields.LcmOperationType.SCALE,
            isAutomaticInvocation=False,
            isCancelPending=False,
            operationParams=req)

        inst.create(self.context)
        lcmocc.create(self.context)

        return lcmocc

    @ddt.data({'before_state': fields.LcmOperationStateType.STARTING,
               'after_state': fields.LcmOperationStateType.ROLLED_BACK},
              {'before_state': fields.LcmOperationStateType.PROCESSING,
               'after_state': fields.LcmOperationStateType.FAILED_TEMP},
              {'before_state': fields.LcmOperationStateType.ROLLING_BACK,
               'after_state': fields.LcmOperationStateType.FAILED_TEMP})
    @ddt.unpack
    @mock.patch.object(nfvo_client.NfvoClient, 'send_lcmocc_notification')
    @mock.patch.object(nfvo_client.NfvoClient, 'get_vnfd')
    def test_change_lcm_op_state(self, mocked_get_vnfd,
            mocked_send_lcmocc_notification, before_state, after_state):
        # prepare
        lcmocc = self._prepare_change_lcm_op_state(before_state)
        mocked_get_vnfd.return_value = mock.Mock()
        ex = sol_ex.ConductorProcessingError()

        op_state = []

        def _store_state(context, lcmocc, inst, endpoint):
            op_state.append(lcmocc.operationState)

        mocked_send_lcmocc_notification.side_effect = _store_state

        # run _change_lcm_op_state
        self.conductor._change_lcm_op_state()

        # check operationState transition
        self.assertEqual(1, mocked_send_lcmocc_notification.call_count)
        self.assertEqual(after_state, op_state[0])

        # check lcmocc.error
        # get lcmocc from DB to be sure lcmocc saved to DB
        lcmocc = lcmocc_utils.get_lcmocc(self.context, lcmocc.id)
        expected = ex.make_problem_details()
        self.assertEqual(expected, lcmocc.error.to_dict())
