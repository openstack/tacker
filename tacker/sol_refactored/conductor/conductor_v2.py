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

import threading

from oslo_log import log as logging
from oslo_service import loopingcall
from oslo_utils import encodeutils

from tacker.common import log
from tacker import context as tacker_context
from tacker.sol_refactored.common import config
from tacker.sol_refactored.common import coordinate
from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.common import lcm_op_occ_utils as lcmocc_utils
from tacker.sol_refactored.common import vnf_instance_utils as inst_utils
from tacker.sol_refactored.conductor import prometheus_plugin_driver as pp_drv
from tacker.sol_refactored.conductor import server_notification_driver as sdrv
from tacker.sol_refactored.conductor import vnffm_driver_v1
from tacker.sol_refactored.conductor import vnflcm_driver_v2
from tacker.sol_refactored.conductor import vnfpm_driver_v2
from tacker.sol_refactored.nfvo import nfvo_client
from tacker.sol_refactored import objects
from tacker.sol_refactored.objects.v2 import fields


LOG = logging.getLogger(__name__)

CONF = config.CONF
# NOTE(fengyi): After the conductor is started, since the start-up process
# is being executed, it should take a while to start the actual DB
# synchronization periodical process.
DB_SYNC_INITIAL_DELAY = 60


def async_call(func):
    def inner(*args, **kwargs):
        th = threading.Thread(target=func, args=args,
                kwargs=kwargs, daemon=True)
        th.start()
    return inner


class ConductorV2(object):

    def __init__(self):
        self.vnflcm_driver = vnflcm_driver_v2.VnfLcmDriverV2()
        self.vnffm_driver = vnffm_driver_v1.VnfFmDriverV1()
        self.vnfpm_driver = vnfpm_driver_v2.VnfPmDriverV2()
        self.endpoint = CONF.v2_vnfm.endpoint
        self.nfvo_client = nfvo_client.NfvoClient()
        self.prom_driver = pp_drv.PrometheusPluginDriver.instance()
        self.sn_driver = sdrv.ServerNotificationDriver.instance()
        self._change_lcm_op_state()

        self._periodic_call()

    @async_call
    def _periodic_call(self):
        self.periodic = loopingcall.FixedIntervalLoopingCall(
            self._sync_db)
        self.periodic.start(interval=CONF.db_synchronization_interval,
                            initial_delay=DB_SYNC_INITIAL_DELAY)

    def _change_lcm_op_state(self):
        # NOTE: If the conductor down during processing and
        # the LcmOperationState STARTING/PROCESSING/ROLLING_BACK remain,
        # change it at the next startup.
        context = tacker_context.get_admin_context()
        ex = sol_ex.ConductorProcessingError()

        state_list = [(fields.LcmOperationStateType.STARTING,
                       fields.LcmOperationStateType.ROLLED_BACK),
                      (fields.LcmOperationStateType.PROCESSING,
                       fields.LcmOperationStateType.FAILED_TEMP),
                      (fields.LcmOperationStateType.ROLLING_BACK,
                       fields.LcmOperationStateType.FAILED_TEMP)]
        for before_state, after_state in state_list:
            lcmoccs = objects.VnfLcmOpOccV2.get_by_filter(context,
                operationState=before_state)
            for lcmocc in lcmoccs:
                lcmocc.operationState = after_state
                self._set_lcmocc_error(lcmocc, ex)
                inst = inst_utils.get_inst(context, lcmocc.vnfInstanceId)
                lcmocc.update(context)
                # send notification
                self.nfvo_client.send_lcmocc_notification(context, lcmocc,
                                                          inst, self.endpoint)

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
        # if an error occurred lcmocc.operationState remains STARTING.
        # see the log of the tacker-conductor to investigate the cause
        # of error.

        # NOTE: the following flow follows SOL003 5.4.1.2

        # send notification STARTING
        self.nfvo_client.send_lcmocc_notification(context, lcmocc, inst,
                                                  self.endpoint)

        try:
            if lcmocc.operation == fields.LcmOperationType.CHANGE_VNFPKG:
                vnfd = self.nfvo_client.get_vnfd(
                    context, lcmocc.operationParams.vnfdId, all_contents=True)
            else:
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
                # grant_req and grant are not necessary any more.
                grant_req.delete(context)
                grant.delete(context)
        except Exception as ex:
            LOG.exception("PROCESSING %s failed", lcmocc.operation)
            lcmocc.operationState = fields.LcmOperationStateType.FAILED_TEMP
            self._set_lcmocc_error(lcmocc, ex)
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
            if lcmocc.operation == fields.LcmOperationType.CHANGE_VNFPKG:
                vnfd = self.nfvo_client.get_vnfd(
                    context, lcmocc.operationParams.vnfdId, all_contents=True)
            else:
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
                if grant_req is not None:
                    grant_req.delete(context)
                    grant.delete(context)
        except Exception as ex:
            LOG.exception("PROCESSING %s failed", lcmocc.operation)
            lcmocc.operationState = fields.LcmOperationStateType.FAILED_TEMP
            self._set_lcmocc_error(lcmocc, ex)
            lcmocc.update(context)
            # grant_req and grant are already saved. they are not deleted
            # while operationState is FAILED_TEMP.

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
            grant_req, grant = lcmocc_utils.get_grant_req_and_grant(
                context, lcmocc)
            self.vnflcm_driver.post_grant(context, lcmocc, inst, grant_req,
                                          grant, vnfd)
            self.vnflcm_driver.rollback(context, lcmocc, inst, grant_req,
                                        grant, vnfd)

            lcmocc.operationState = fields.LcmOperationStateType.ROLLED_BACK
            with context.session.begin(subtransactions=True):
                lcmocc.update(context)
                # NOTE: Basically inst is not changed. But there is a case
                # that VIM resources may be changed while rollback. Only
                # change_ext_conn_rollback and change_vnfpkg at the moment.
                if lcmocc.operation in [
                    fields.LcmOperationType.CHANGE_EXT_CONN,
                        fields.LcmOperationType.CHANGE_VNFPKG]:
                    inst.update(context)
                # grant_req and grant are not necessary any more.
                if grant_req is not None:
                    grant_req.delete(context)
                    grant.delete(context)
        except Exception as ex:
            LOG.exception("ROLLING_BACK %s failed", lcmocc.operation)
            lcmocc.operationState = fields.LcmOperationStateType.FAILED_TEMP
            self._set_lcmocc_error(lcmocc, ex)
            lcmocc.update(context)
            # grant_req and grant are already saved. they are not deleted
            # while operationState is FAILED_TEMP.

        # send notification ROLLED_BACK or FAILED_TEMP
        self.nfvo_client.send_lcmocc_notification(context, lcmocc, inst,
                                                  self.endpoint)

    @log.log
    def modify_vnfinfo(self, context, lcmocc_id):
        lcmocc = lcmocc_utils.get_lcmocc(context, lcmocc_id)

        self._modify_vnfinfo(context, lcmocc)

    @coordinate.lock_vnf_instance('{lcmocc.vnfInstanceId}', delay=True)
    def _modify_vnfinfo(self, context, lcmocc):
        # just consistency check
        if lcmocc.operationState != fields.LcmOperationStateType.PROCESSING:
            LOG.error("VnfLcmOpOcc unexpected operationState.")
            return

        inst = inst_utils.get_inst(context, lcmocc.vnfInstanceId)
        # send notification PROCESSING
        self.nfvo_client.send_lcmocc_notification(context, lcmocc, inst,
                                                  self.endpoint)

        try:
            vnfd = self.nfvo_client.get_vnfd(context, inst.vnfdId)
            self.vnflcm_driver.process(context, lcmocc, inst, None, None, vnfd)
            lcmocc.operationState = fields.LcmOperationStateType.COMPLETED
            # update inst and lcmocc at the same time
            with context.session.begin(subtransactions=True):
                inst.update(context)
                lcmocc.update(context)
        except Exception as ex:
            LOG.exception("PROCESSING %s failed", lcmocc.operation)
            lcmocc.operationState = fields.LcmOperationStateType.FAILED_TEMP
            self._set_lcmocc_error(lcmocc, ex)
            lcmocc.update(context)

        # send notification COMPLETED or FAILED_TEMP
        self.nfvo_client.send_lcmocc_notification(context, lcmocc, inst,
                                                  self.endpoint)

    def _sync_db(self):
        """Periodic database update invocation method(v2 api)"""
        LOG.debug("Starting _sync_db")
        context = tacker_context.get_admin_context()

        vnf_instances = objects.VnfInstanceV2.get_by_filter(
            context, instantiationState='INSTANTIATED')
        for inst in vnf_instances:
            try:
                vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
                self.vnflcm_driver.diff_check_inst(inst, vim_info)
                self._sync_inst(context, inst, vim_info)
            except sol_ex.DbSyncNoDiff:
                continue
            except sol_ex.DbSyncFailed as e:
                LOG.error("%s: %s", e.__class__.__name__, e.args[0])
            except sol_ex.OtherOperationInProgress:
                LOG.info("There is an LCM operation in progress, so "
                         f"skip this DB synchronization. vnf: {inst.id}.")
            except Exception as e:
                LOG.error(f"Failed to synchronize database vnf: {inst.id} "
                          f"Error: {encodeutils.exception_to_unicode(e)}")
        LOG.debug("Ended _sync_db")

    @coordinate.lock_vnf_instance('{inst.id}')
    def _sync_inst(self, context, inst, vim_info):
        vnf_inst = inst_utils.get_inst(context, inst.id)
        self.vnflcm_driver.sync_db(
            context, vnf_inst, vim_info)
        vnf_inst.update(context)

    def store_alarm_info(self, context, alarm):
        self.vnffm_driver.store_alarm_info(context, alarm)

    def store_job_info(self, context, report):
        # call pm_driver
        self.vnfpm_driver.store_job_info(context, report)

    @log.log
    def request_scale(self, context, id, scale_req):
        self.prom_driver.request_scale(context, id, scale_req)

    @log.log
    def server_notification_notify(
            self, context, vnf_instance_id, vnfc_instance_ids):
        self.sn_driver.notify(vnf_instance_id, vnfc_instance_ids)

    @log.log
    def server_notification_remove_timer(self, context, vnf_instance_id):
        self.sn_driver.remove_timer(vnf_instance_id)
