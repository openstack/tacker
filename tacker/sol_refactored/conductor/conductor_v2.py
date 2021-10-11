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

from oslo_log import log as logging

from tacker.common import log
from tacker.sol_refactored.common import config
from tacker.sol_refactored.common import coordinate
from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.common import lcm_op_occ_utils as lcmocc_utils
from tacker.sol_refactored.common import vnf_instance_utils as inst_utils
from tacker.sol_refactored.conductor import vnflcm_driver_v2
from tacker.sol_refactored.nfvo import nfvo_client
from tacker.sol_refactored import objects
from tacker.sol_refactored.objects.v2 import fields


LOG = logging.getLogger(__name__)

CONF = config.CONF


class ConductorV2(object):

    def __init__(self):
        self.vnflcm_driver = vnflcm_driver_v2.VnfLcmDriverV2()
        self.endpoint = CONF.v2_vnfm.endpoint
        self.nfvo_client = nfvo_client.NfvoClient()

    def _set_lcmocc_error(self, lcmocc, ex):
        if isinstance(ex, sol_ex.SolException):
            problem_details = ex.make_problem_details()
        else:
            # program bug. it occurs only under development.
            problem_details = {'status': 500,
                               'detail': str(ex)}
        lcmocc.error = objects.ProblemDetails.from_dict(problem_details)

    @log.log
    def start_lcm_op(self, context, lcmocc_id):
        lcmocc = lcmocc_utils.get_lcmocc(context, lcmocc_id)

        self._start_lcm_op(context, lcmocc)

    @coordinate.lock_vnf_instance('{lcmocc.vnfInstanceId}', delay=True)
    def _start_lcm_op(self, context, lcmocc):
        # just consistency check
        if lcmocc.operationState != fields.LcmOperationStateType.STARTING:
            LOG.error("VnfLcmOpOcc unexpected operationState.")
            return

        inst = inst_utils.get_inst(context, lcmocc.vnfInstanceId)

        # NOTE: error cannot happen to here basically.
        # if an error occurred lcmocc.opetationState remains STARTING.
        # see the log of the tacker-conductor to investigate the cause
        # of error.

        # NOTE: the following flow follows SOL003 5.4.1.2

        # send notification STARTING
        self.nfvo_client.send_lcmocc_notification(context, lcmocc, inst,
                                                  self.endpoint)

        try:
            vnfd = self.nfvo_client.get_vnfd(context, inst.vnfdId,
                                             all_contents=True)

            # NOTE: perform grant exchange mainly but also perform
            # something to do at STATING phase ex. request check.
            grant_req, grant = self.vnflcm_driver.grant(context, lcmocc,
                                                        inst, vnfd)
            self.vnflcm_driver.post_grant(context, lcmocc, inst, grant_req,
                                          grant, vnfd)

            lcmocc.operationState = fields.LcmOperationStateType.PROCESSING
            lcmocc.grantId = grant.id
            lcmocc.update(context)
        except Exception as ex:
            LOG.exception("STARTING %s failed", lcmocc.operation)
            lcmocc.operationState = fields.LcmOperationStateType.ROLLED_BACK
            self._set_lcmocc_error(lcmocc, ex)
            lcmocc.update(context)

        # send notification PROCESSING or ROLLED_BACK
        self.nfvo_client.send_lcmocc_notification(context, lcmocc, inst,
                                                  self.endpoint)

        if lcmocc.operationState != fields.LcmOperationStateType.PROCESSING:
            return

        try:
            self.vnflcm_driver.process(context, lcmocc, inst, grant_req,
                                       grant, vnfd)

            lcmocc.operationState = fields.LcmOperationStateType.COMPLETED
            # update inst and lcmocc at the same time
            with context.session.begin(subtransactions=True):
                inst.update(context)
                lcmocc.update(context)
        except Exception as ex:
            LOG.exception("PROCESSING %s failed", lcmocc.operation)
            lcmocc.operationState = fields.LcmOperationStateType.FAILED_TEMP
            self._set_lcmocc_error(lcmocc, ex)
            with context.session.begin(subtransactions=True):
                # save grant_req and grant to be used when retry
                # NOTE: grant_req is saved because it is necessary to interpret
                # the contents of grant. Though grant can be gotten from NFVO,
                # it is saved here with grant_req so that it is not necessary
                # to communicate with NFVO when retry. They are saved temporary
                # and will be deleted when operationState becomes an end state
                # (COMPLETED/FAILED/ROLLED_BACK).
                grant_req.create(context)
                grant.create(context)
                lcmocc.update(context)

        # send notification COMPLETED or FAILED_TEMP
        self.nfvo_client.send_lcmocc_notification(context, lcmocc, inst,
                                                  self.endpoint)

    @log.log
    def retry_lcm_op(self, context, lcmocc_id):
        lcmocc = lcmocc_utils.get_lcmocc(context, lcmocc_id)

        self._retry_lcm_op(context, lcmocc)

    @coordinate.lock_vnf_instance('{lcmocc.vnfInstanceId}', delay=True)
    def _retry_lcm_op(self, context, lcmocc):
        # just consistency check
        if lcmocc.operationState != fields.LcmOperationStateType.FAILED_TEMP:
            LOG.error("VnfLcmOpOcc unexpected operationState.")
            return

        inst = inst_utils.get_inst(context, lcmocc.vnfInstanceId)

        lcmocc.operationState = fields.LcmOperationStateType.PROCESSING
        lcmocc.update(context)
        # send notification PROCESSING
        self.nfvo_client.send_lcmocc_notification(context, lcmocc, inst,
                                                  self.endpoint)

        try:
            vnfd = self.nfvo_client.get_vnfd(context, inst.vnfdId,
                                             all_contents=True)
            grant_req, grant = lcmocc_utils.get_grant_req_and_grant(context,
                                                                    lcmocc)
            self.vnflcm_driver.post_grant(context, lcmocc, inst, grant_req,
                                          grant, vnfd)
            self.vnflcm_driver.process(context, lcmocc, inst, grant_req,
                                       grant, vnfd)

            lcmocc.operationState = fields.LcmOperationStateType.COMPLETED
            lcmocc.error = None  # clear error
            # update inst and lcmocc at the same time
            with context.session.begin(subtransactions=True):
                inst.update(context)
                lcmocc.update(context)
                # grant_req and grant are not necessary any more.
                grant_req.delete(context)
                grant.delete(context)
        except Exception as ex:
            LOG.exception("PROCESSING %s failed", lcmocc.operation)
            lcmocc.operationState = fields.LcmOperationStateType.FAILED_TEMP
            self._set_lcmocc_error(lcmocc, ex)
            lcmocc.update(context)
            # grant_req and grant are already saved. they are not deleted
            # while oprationState is FAILED_TEMP.

        # send notification COMPLETED or FAILED_TEMP
        self.nfvo_client.send_lcmocc_notification(context, lcmocc, inst,
                                                  self.endpoint)

    @log.log
    def rollback_lcm_op(self, context, lcmocc_id):
        lcmocc = lcmocc_utils.get_lcmocc(context, lcmocc_id)

        self._rollback_lcm_op(context, lcmocc)

    @coordinate.lock_vnf_instance('{lcmocc.vnfInstanceId}', delay=True)
    def _rollback_lcm_op(self, context, lcmocc):
        # just consistency check
        if lcmocc.operationState != fields.LcmOperationStateType.FAILED_TEMP:
            LOG.error("VnfLcmOpOcc unexpected operationState.")
            return

        inst = inst_utils.get_inst(context, lcmocc.vnfInstanceId)

        lcmocc.operationState = fields.LcmOperationStateType.ROLLING_BACK
        lcmocc.update(context)
        # send notification ROLLING_BACK
        self.nfvo_client.send_lcmocc_notification(context, lcmocc, inst,
                                                  self.endpoint)

        try:
            vnfd = self.nfvo_client.get_vnfd(context, inst.vnfdId)
            grant_req, grant = lcmocc_utils.get_grant_req_and_grant(context,
                                                                    lcmocc)
            self.vnflcm_driver.post_grant(context, lcmocc, inst, grant_req,
                                          grant, vnfd)
            self.vnflcm_driver.rollback(context, lcmocc, inst, grant_req,
                                        grant, vnfd)

            lcmocc.operationState = fields.LcmOperationStateType.ROLLED_BACK
            with context.session.begin(subtransactions=True):
                # it is not necessary to update inst DB because it was not
                # changed when the operationState became FAILED_TEMP.
                # NOTE: inst object may be changed in driver's rollback
                # method temporary but must not save it.
                lcmocc.update(context)
                # grant_req and grant are not necessary any more.
                grant_req.delete(context)
                grant.delete(context)
        except Exception as ex:
            LOG.exception("ROLLING_BACK %s failed", lcmocc.operation)
            lcmocc.operationState = fields.LcmOperationStateType.FAILED_TEMP
            self._set_lcmocc_error(lcmocc, ex)
            lcmocc.update(context)
            # grant_req and grant are already saved. they are not deleted
            # while oprationState is FAILED_TEMP.

        # send notification ROLLED_BACK or FAILED_TEMP
        self.nfvo_client.send_lcmocc_notification(context, lcmocc, inst,
                                                  self.endpoint)
