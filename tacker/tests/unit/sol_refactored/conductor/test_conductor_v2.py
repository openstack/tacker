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
from kubernetes import client
from oslo_log import log as logging
from oslo_utils import uuidutils
from tooz.drivers import file

from tacker import context
from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.common import lcm_op_occ_utils as lcmocc_utils
from tacker.sol_refactored.conductor import conductor_v2
from tacker.sol_refactored.conductor import vnflcm_driver_v2
from tacker.sol_refactored.nfvo import nfvo_client
from tacker.sol_refactored import objects
from tacker.sol_refactored.objects.v2 import fields
from tacker.tests.unit.db import base as db_base
from tacker.tests.unit.sol_refactored.infra_drivers.kubernetes import fakes
from tacker.vnfm.infra_drivers.kubernetes import kubernetes_driver


CNF_SAMPLE_VNFD_ID = "b1bb0ce7-ebca-4fa7-95ed-4840d70a1177"


@ddt.ddt
class TestConductorV2(db_base.SqlTestCase):

    def setUp(self):
        super(TestConductorV2, self).setUp()
        objects.register_all()
        self.conductor = conductor_v2.ConductorV2()
        self.context = context.get_admin_context()

    def _create_inst_and_lcmocc(
            self, op_state=fields.LcmOperationStateType.STARTING,
            is_change_vnfpkg=False):
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

        if is_change_vnfpkg:
            lcmocc.operation = fields.LcmOperationType.CHANGE_VNFPKG

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
        op_state_entered_time = []

        def _store_state(context, lcmocc, inst, endpoint):
            op_state.append(lcmocc.operationState)
            op_state_entered_time.append(lcmocc.stateEnteredTime)

        mocked_send_lcmocc_notification.side_effect = _store_state

        # run start_lcm_op
        self.conductor.start_lcm_op(self.context, lcmocc.id)

        # check operationState transition
        self.assertEqual(3, mocked_send_lcmocc_notification.call_count)
        self.assertEqual(fields.LcmOperationStateType.STARTING, op_state[0])
        self.assertEqual(fields.LcmOperationStateType.PROCESSING, op_state[1])
        self.assertEqual(fields.LcmOperationStateType.COMPLETED, op_state[2])

        # check stateEnteredTime
        self.assertNotEqual(op_state_entered_time[0], op_state_entered_time[1])
        self.assertNotEqual(op_state_entered_time[1], op_state_entered_time[2])

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
        op_state_entered_time = []

        def _store_state(context, lcmocc, inst, endpoint):
            op_state.append(lcmocc.operationState)
            op_state_entered_time.append(lcmocc.stateEnteredTime)

        mocked_send_lcmocc_notification.side_effect = _store_state

        # run start_lcm_op
        self.conductor.start_lcm_op(self.context, lcmocc.id)

        # check operationState transition
        self.assertEqual(3, mocked_send_lcmocc_notification.call_count)
        self.assertEqual(fields.LcmOperationStateType.STARTING, op_state[0])
        self.assertEqual(fields.LcmOperationStateType.PROCESSING, op_state[1])
        self.assertEqual(fields.LcmOperationStateType.COMPLETED, op_state[2])

        # check stateEnteredTime
        self.assertNotEqual(op_state_entered_time[0], op_state_entered_time[1])
        self.assertNotEqual(op_state_entered_time[1], op_state_entered_time[2])

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
        op_state_entered_time = []

        def _store_state(context, lcmocc, inst, endpoint):
            op_state.append(lcmocc.operationState)
            op_state_entered_time.append(lcmocc.stateEnteredTime)

        mocked_send_lcmocc_notification.side_effect = _store_state

        # run start_lcm_op
        self.conductor.start_lcm_op(self.context, lcmocc.id)

        # check operationState transition
        self.assertEqual(2, mocked_send_lcmocc_notification.call_count)
        self.assertEqual(fields.LcmOperationStateType.STARTING, op_state[0])
        self.assertEqual(fields.LcmOperationStateType.ROLLED_BACK, op_state[1])

        # check stateEnteredTime
        self.assertNotEqual(op_state_entered_time[0], op_state_entered_time[1])

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
        op_state_entered_time = []

        def _store_state(context, lcmocc, inst, endpoint):
            op_state.append(lcmocc.operationState)
            op_state_entered_time.append(lcmocc.stateEnteredTime)

        mocked_send_lcmocc_notification.side_effect = _store_state

        # run start_lcm_op
        self.conductor.start_lcm_op(self.context, lcmocc.id)

        # check operationState transition
        self.assertEqual(3, mocked_send_lcmocc_notification.call_count)
        self.assertEqual(fields.LcmOperationStateType.STARTING, op_state[0])
        self.assertEqual(fields.LcmOperationStateType.PROCESSING, op_state[1])
        self.assertEqual(fields.LcmOperationStateType.FAILED_TEMP, op_state[2])

        # check stateEnteredTime
        self.assertNotEqual(op_state_entered_time[0], op_state_entered_time[1])
        self.assertNotEqual(op_state_entered_time[1], op_state_entered_time[2])

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
        op_state_entered_time = []

        def _store_state(context, lcmocc, inst, endpoint):
            op_state.append(lcmocc.operationState)
            op_state_entered_time.append(lcmocc.stateEnteredTime)

        mocked_send_lcmocc_notification.side_effect = _store_state

        # run retry_lcm_op
        self.conductor.retry_lcm_op(self.context, lcmocc.id)

        # check operationState transition
        self.assertEqual(2, mocked_send_lcmocc_notification.call_count)
        self.assertEqual(fields.LcmOperationStateType.PROCESSING, op_state[0])
        self.assertEqual(fields.LcmOperationStateType.COMPLETED, op_state[1])

        # check stateEnteredTime
        self.assertNotEqual(op_state_entered_time[0], op_state_entered_time[1])

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
        problem_details = {'userScriptErrHandlingData': {"key": "value"}}
        lcmocc.error = objects.ProblemDetails.from_dict(problem_details)
        self._create_grant_req_and_grant(lcmocc)
        mocked_get_vnfd.return_value = mock.Mock()
        ex = sol_ex.StackOperationFailed(sol_detail="unit test",
                                         sol_title="stack failed")
        mocked_process.side_effect = ex

        op_state = []
        op_state_entered_time = []

        def _store_state(context, lcmocc, inst, endpoint):
            op_state.append(lcmocc.operationState)
            op_state_entered_time.append(lcmocc.stateEnteredTime)

        mocked_send_lcmocc_notification.side_effect = _store_state

        # run retry_lcm_op
        self.conductor.retry_lcm_op(self.context, lcmocc.id)

        # check operationState transition
        self.assertEqual(2, mocked_send_lcmocc_notification.call_count)
        self.assertEqual(fields.LcmOperationStateType.PROCESSING, op_state[0])
        self.assertEqual(fields.LcmOperationStateType.FAILED_TEMP, op_state[1])

        # check stateEnteredTime
        self.assertNotEqual(op_state_entered_time[0], op_state_entered_time[1])

        # check lcmocc.error
        # get lcmocc from DB to be sure lcmocc saved to DB
        lcmocc = lcmocc_utils.get_lcmocc(self.context, lcmocc.id)
        expected = ex.make_problem_details()
        expected['userScriptErrHandlingData'] = {"key": "value"}
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
        problem_details = {'userScriptErrHandlingData': {"key": "value"}}
        lcmocc.error = objects.ProblemDetails.from_dict(problem_details)
        self._create_grant_req_and_grant(lcmocc)
        mocked_get_vnfd.return_value = mock.Mock()

        op_state = []
        op_state_entered_time = []

        def _store_state(context, lcmocc, inst, endpoint):
            op_state.append(lcmocc.operationState)
            op_state_entered_time.append(lcmocc.stateEnteredTime)

        mocked_send_lcmocc_notification.side_effect = _store_state

        # run rollback_lcm_op
        self.conductor.rollback_lcm_op(self.context, lcmocc.id)

        # check operationState transition
        self.assertEqual(2, mocked_send_lcmocc_notification.call_count)
        self.assertEqual(fields.LcmOperationStateType.ROLLING_BACK,
                         op_state[0])
        self.assertEqual(fields.LcmOperationStateType.ROLLED_BACK, op_state[1])

        # check stateEnteredTime
        self.assertNotEqual(op_state_entered_time[0], op_state_entered_time[1])

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
        problem_details = {'userScriptErrHandlingData': {"key": "value"}}
        lcmocc.error = objects.ProblemDetails.from_dict(problem_details)
        self._create_grant_req_and_grant(lcmocc)
        mocked_get_vnfd.return_value = mock.Mock()
        ex = sol_ex.StackOperationFailed(sol_detail="unit test",
                                         sol_title="stack failed")
        mocked_rollback.side_effect = ex

        op_state = []
        op_state_entered_time = []

        def _store_state(context, lcmocc, inst, endpoint):
            op_state.append(lcmocc.operationState)
            op_state_entered_time.append(lcmocc.stateEnteredTime)

        mocked_send_lcmocc_notification.side_effect = _store_state

        # run rollback_lcm_op
        self.conductor.rollback_lcm_op(self.context, lcmocc.id)

        # check operationState transition
        self.assertEqual(2, mocked_send_lcmocc_notification.call_count)
        self.assertEqual(fields.LcmOperationStateType.ROLLING_BACK,
                         op_state[0])
        self.assertEqual(fields.LcmOperationStateType.FAILED_TEMP, op_state[1])

        # check stateEnteredTime
        self.assertNotEqual(op_state_entered_time[0], op_state_entered_time[1])

        # check lcmocc.error
        # get lcmocc from DB to be sure lcmocc saved to DB
        lcmocc = lcmocc_utils.get_lcmocc(self.context, lcmocc.id)
        expected = ex.make_problem_details()
        expected['userScriptErrHandlingData'] = {"key": "value"}
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
        op_state_entered_time = []

        def _store_state(context, lcmocc, inst, endpoint):
            op_state.append(lcmocc.operationState)
            op_state_entered_time.append(lcmocc.stateEnteredTime)

        mocked_send_lcmocc_notification.side_effect = _store_state

        # run modify_vnfinfo
        self.conductor.modify_vnfinfo(self.context, lcmocc.id)

        # check operationState transition
        self.assertEqual(2, mocked_send_lcmocc_notification.call_count)
        self.assertEqual(fields.LcmOperationStateType.PROCESSING, op_state[0])
        self.assertEqual(fields.LcmOperationStateType.COMPLETED, op_state[1])

        # check stateEnteredTime
        self.assertNotEqual(op_state_entered_time[0], op_state_entered_time[1])

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
        op_state_entered_time = []

        def _store_state(context, lcmocc, inst, endpoint):
            op_state.append(lcmocc.operationState)
            op_state_entered_time.append(lcmocc.stateEnteredTime)

        mocked_send_lcmocc_notification.side_effect = _store_state

        # run modify_vnfinfo
        self.conductor.modify_vnfinfo(self.context, lcmocc.id)

        # check operationState transition
        self.assertEqual(2, mocked_send_lcmocc_notification.call_count)
        self.assertEqual(fields.LcmOperationStateType.PROCESSING, op_state[0])
        self.assertEqual(fields.LcmOperationStateType.FAILED_TEMP, op_state[1])

        # check stateEnteredTime
        self.assertNotEqual(op_state_entered_time[0], op_state_entered_time[1])

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
        before_state_entered_time = lcmocc.stateEnteredTime
        mocked_get_vnfd.return_value = mock.Mock()
        ex = sol_ex.ConductorProcessingError()

        op_state = []
        op_state_entered_time = []

        def _store_state(context, lcmocc, inst, endpoint):
            op_state.append(lcmocc.operationState)
            op_state_entered_time.append(lcmocc.stateEnteredTime)

        mocked_send_lcmocc_notification.side_effect = _store_state

        # run _change_lcm_op_state
        self.conductor._change_lcm_op_state()

        # check operationState transition
        self.assertEqual(1, mocked_send_lcmocc_notification.call_count)
        self.assertEqual(after_state, op_state[0])

        # check stateEnteredTime
        self.assertNotEqual(before_state_entered_time,
                            op_state_entered_time[0])

        # check lcmocc.error
        # get lcmocc from DB to be sure lcmocc saved to DB
        lcmocc = lcmocc_utils.get_lcmocc(self.context, lcmocc.id)
        expected = ex.make_problem_details()
        self.assertEqual(expected, lcmocc.error.to_dict())

    def test_start_lcm_op_abnormal(self):
        # prepare
        lcmocc = self._create_inst_and_lcmocc(
            op_state=fields.LcmOperationStateType.PROCESSING)

        result = self.conductor.start_lcm_op(self.context, lcmocc.id)
        self.assertEqual(None, result)

    @mock.patch.object(nfvo_client.NfvoClient, 'send_lcmocc_notification')
    @mock.patch.object(nfvo_client.NfvoClient, 'get_vnfd')
    @mock.patch.object(vnflcm_driver_v2.VnfLcmDriverV2, 'post_grant')
    @mock.patch.object(vnflcm_driver_v2.VnfLcmDriverV2, 'process')
    def test_retry_lcm_op_abnormal(self, mocked_process, mocked_post_grant,
            mocked_get_vnfd, mocked_send_lcmocc_notification):
        # operation state incorrect
        lcmocc = self._create_inst_and_lcmocc(
            op_state=fields.LcmOperationStateType.PROCESSING)
        result = self.conductor.retry_lcm_op(self.context, lcmocc.id)
        self.assertEqual(None, result)

        # operation is change_vnfpkg
        # prepare
        lcmocc = self._create_inst_and_lcmocc(
            op_state=fields.LcmOperationStateType.FAILED_TEMP)
        lcmocc.operation = fields.LcmOperationType.CHANGE_VNFPKG
        lcmocc.operationParams = objects.ChangeCurrentVnfPkgRequest(
            vnfdId='test-vnfdid')
        self._create_grant_req_and_grant(lcmocc)
        mocked_get_vnfd.return_value = mock.Mock()

        op_state = []
        op_state_entered_time = []

        def _store_state(context, lcmocc, inst, endpoint):
            op_state.append(lcmocc.operationState)
            op_state_entered_time.append(lcmocc.stateEnteredTime)

        mocked_send_lcmocc_notification.side_effect = _store_state

        # run retry_lcm_op
        self.conductor.retry_lcm_op(self.context, lcmocc.id)

        # check operationState transition
        self.assertEqual(2, mocked_send_lcmocc_notification.call_count)
        self.assertEqual(fields.LcmOperationStateType.PROCESSING, op_state[0])
        self.assertEqual(fields.LcmOperationStateType.COMPLETED, op_state[1])

        # check stateEnteredTime
        self.assertNotEqual(op_state_entered_time[0], op_state_entered_time[1])

        # check grant_req and grant are deleted
        self.assertRaises(sol_ex.GrantRequestOrGrantNotFound,
            lcmocc_utils.get_grant_req_and_grant, self.context, lcmocc)

    @mock.patch.object(nfvo_client.NfvoClient, 'send_lcmocc_notification')
    @mock.patch.object(nfvo_client.NfvoClient, 'get_vnfd')
    @mock.patch.object(vnflcm_driver_v2.VnfLcmDriverV2, 'post_grant')
    @mock.patch.object(vnflcm_driver_v2.VnfLcmDriverV2, 'rollback')
    def test_rollback_lcm_op_abnormal(self, mocked_rollback,
            mocked_post_grant, mocked_get_vnfd,
            mocked_send_lcmocc_notification):
        # operation state incorrect
        lcmocc = self._create_inst_and_lcmocc(
            op_state=fields.LcmOperationStateType.PROCESSING)
        result = self.conductor.rollback_lcm_op(self.context, lcmocc.id)
        self.assertEqual(None, result)

        # operation is change_vnfpkg
        lcmocc = self._create_inst_and_lcmocc(
            op_state=fields.LcmOperationStateType.FAILED_TEMP,
            is_change_vnfpkg=True)
        self._create_grant_req_and_grant(lcmocc)
        mocked_get_vnfd.return_value = mock.Mock()

        op_state = []
        op_state_entered_time = []

        def _store_state(context, lcmocc, inst, endpoint):
            op_state.append(lcmocc.operationState)
            op_state_entered_time.append(lcmocc.stateEnteredTime)

        mocked_send_lcmocc_notification.side_effect = _store_state

        # run rollback_lcm_op
        self.conductor.rollback_lcm_op(self.context, lcmocc.id)

        # check operationState transition
        self.assertEqual(2, mocked_send_lcmocc_notification.call_count)
        self.assertEqual(fields.LcmOperationStateType.ROLLING_BACK,
                         op_state[0])
        self.assertEqual(fields.LcmOperationStateType.ROLLED_BACK, op_state[1])

        # check stateEnteredTime
        self.assertNotEqual(op_state_entered_time[0], op_state_entered_time[1])

        # check grant_req and grant are deleted
        self.assertRaises(sol_ex.GrantRequestOrGrantNotFound,
            lcmocc_utils.get_grant_req_and_grant, self.context, lcmocc)

    def test_modify_vnfinfo_abnormal(self):
        lcmocc = self._create_inst_and_lcmocc()

        result = self.conductor.modify_vnfinfo(self.context, lcmocc.id)
        self.assertEqual(None, result)

    @mock.patch.object(vnflcm_driver_v2.VnfLcmDriverV2,
                       'sync_db')
    @mock.patch.object(kubernetes_driver.Kubernetes,
                       '_check_pod_information')
    @mock.patch.object(client.CoreV1Api, 'list_namespaced_pod')
    @mock.patch.object(objects.base.TackerPersistentObject, "get_by_filter")
    def test_sync_db(
            self, mock_db_sync, mock_get_by_filters,
            mock_list_namespaced_pod, mock_check_pod_information):
        vnf_instance_obj = fakes.fake_vnf_instance()
        vnf_instance_obj.id = CNF_SAMPLE_VNFD_ID
        vnfc_rsc_info_obj1, vnfc_info_obj1 = fakes.fake_vnfc_resource_info(
            vdu_id='VDU1', rsc_kind='Pod')
        vnf_instance_obj.instantiatedVnfInfo.vnfcResourceInfo = [
            vnfc_rsc_info_obj1
        ]
        vim_connection_object = fakes.fake_vim_connection_info()
        vnf_instance_obj.vimConnectionInfo['vim1'] = vim_connection_object

        mock_get_by_filters.return_value = [
            vnf_instance_obj, vnf_instance_obj]
        mock_list_namespaced_pod.return_value = client.V1PodList(
            items=[fakes.get_fake_pod_info(kind='Pod')])
        mock_check_pod_information.return_value = True
        self.conductor._sync_db()
        mock_db_sync.assert_called_once()

    @mock.patch.object(kubernetes_driver.Kubernetes,
                       '_check_pod_information')
    @mock.patch.object(client.CoreV1Api, 'list_namespaced_pod')
    @mock.patch.object(objects.base.TackerPersistentObject, "get_by_filter")
    def test_sync_db_exception(
            self, mock_get_by_filters, mock_list_namespaced_pod,
            mock_check_pod_information):
        vnf_instance_obj = fakes.fake_vnf_instance()
        vnf_instance_obj.id = CNF_SAMPLE_VNFD_ID
        vnfc_rsc_info_obj1, vnfc_info_obj1 = fakes.fake_vnfc_resource_info(
            vdu_id='VDU1', rsc_kind='Pod')
        vnf_instance_obj.instantiatedVnfInfo.vnfcResourceInfo = [
            vnfc_rsc_info_obj1
        ]
        vim_connection_object = fakes.fake_vim_connection_info()
        vnf_instance_obj.vimConnectionInfo['vim1'] = vim_connection_object

        mock_get_by_filters.return_value = [
            vnf_instance_obj, vnf_instance_obj]
        mock_list_namespaced_pod.return_value = client.V1PodList(
            items=[fakes.get_fake_pod_info(kind='Pod')])
        mock_check_pod_information.return_value = True

        log_name = "tacker.sol_refactored.conductor.conductor_v2"
        with self.assertLogs(logger=log_name, level=logging.DEBUG) as cm:
            self.conductor._sync_db()

        msg = (f'ERROR:{log_name}:Failed to synchronize database vnf: '
               f'{vnf_instance_obj.id} Error: ')
        self.assertIn(f'{msg}', cm.output[1])

    @mock.patch.object(file.FileLock, 'acquire')
    @mock.patch.object(kubernetes_driver.Kubernetes,
                       '_check_pod_information')
    @mock.patch.object(client.CoreV1Api, 'list_namespaced_pod')
    @mock.patch.object(objects.base.TackerPersistentObject, "get_by_filter")
    def test_sync_db_sol_ex(
            self, mock_get_by_filters, mock_list_namespaced_pod,
            mock_check_pod_information, mock_acquire):
        vnf_instance_obj = fakes.fake_vnf_instance()
        # vnf_instance_obj.id = CNF_SAMPLE_VNFD_ID
        vnfc_rsc_info_obj1, vnfc_info_obj1 = fakes.fake_vnfc_resource_info(
            vdu_id='VDU1', rsc_kind='Pod')
        vnf_instance_obj.instantiatedVnfInfo.vnfcResourceInfo = [
            vnfc_rsc_info_obj1
        ]
        vim_connection_object = fakes.fake_vim_connection_info()
        vnf_instance_obj.vimConnectionInfo['vim1'] = vim_connection_object

        vnf_instance_obj1 = fakes.fake_vnf_instance()
        vnf_instance_obj1.vimConnectionInfo['vim1'] = vim_connection_object
        mock_get_by_filters.return_value = [
            vnf_instance_obj]
        mock_list_namespaced_pod.return_value = client.V1PodList(
            items=[fakes.get_fake_pod_info(kind='Pod')])
        mock_check_pod_information.return_value = True
        mock_acquire.return_value = False

        log_name = "tacker.sol_refactored.conductor.conductor_v2"
        with self.assertLogs(logger=log_name, level=logging.DEBUG) as cm:
            self.conductor._sync_db()

        msg = (f'INFO:{log_name}:There is an LCM operation in progress, '
               f'so skip this DB synchronization. '
               f'vnf: {vnf_instance_obj.id}.')
        self.assertIn(f'{msg}', cm.output)
