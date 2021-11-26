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

from oslo_log import log as logging
from oslo_utils import uuidutils

from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.common import subscription_utils as subsc_utils
from tacker.sol_refactored.common import vnf_instance_utils as inst_utils
from tacker.sol_refactored import objects
from tacker.sol_refactored.objects.v2 import fields


LOG = logging.getLogger(__name__)  # not used at the moment


def get_lcmocc(context, lcmocc_id):
    lcmocc = objects.VnfLcmOpOccV2.get_by_id(context, lcmocc_id)
    if lcmocc is None:
        raise sol_ex.VnfLcmOpOccNotFound(lcmocc_id=id)
    return lcmocc


def get_lcmocc_all(context):
    return objects.VnfLcmOpOccV2.get_all(context)


def lcmocc_href(lcmocc_id, endpoint):
    return "{}/v2/vnflcm/vnf_lcm_op_occs/{}".format(endpoint, lcmocc_id)


def lcmocc_task_href(lcmocc_id, task, endpoint):
    return "{}/v2/vnflcm/vnf_lcm_op_occs/{}/{}".format(endpoint, lcmocc_id,
                                                       task)


def make_lcmocc_links(lcmocc, endpoint):
    links = objects.VnfLcmOpOccV2_Links()
    links.self = objects.Link(href=lcmocc_href(lcmocc.id, endpoint))
    links.vnfInstance = objects.Link(
        href=inst_utils.inst_href(lcmocc.vnfInstanceId, endpoint))
    links.retry = objects.Link(
        href=lcmocc_task_href(lcmocc.id, 'retry', endpoint))
    links.rollback = objects.Link(
        href=lcmocc_task_href(lcmocc.id, 'rollback', endpoint))
    links.fail = objects.Link(
        href=lcmocc_task_href(lcmocc.id, 'fail', endpoint))
    # TODO(oda-g): add when implemented
    # links.grant
    # links.cancel
    # links.vnfSnapshot

    return links


def make_lcmocc_notif_data(subsc, lcmocc, endpoint):
    notif_data = objects.VnfLcmOperationOccurrenceNotificationV2(
        id=uuidutils.generate_uuid(),
        notificationType="VnfLcmOperationOccurrenceNotification",
        subscriptionId=subsc.id,
        timeStamp=datetime.utcnow(),
        operationState=lcmocc.operationState,
        vnfInstanceId=lcmocc.vnfInstanceId,
        operation=lcmocc.operation,
        isAutomaticInvocation=lcmocc.isAutomaticInvocation,
        verbosity=subsc.verbosity,
        vnfLcmOpOccId=lcmocc.id,
        _links=objects.LccnLinksV2(
            vnfInstance=objects.NotificationLink(
                href=inst_utils.inst_href(lcmocc.vnfInstanceId, endpoint)),
            subscription=objects.NotificationLink(
                href=subsc_utils.subsc_href(subsc.id, endpoint)),
            vnfLcmOpOcc=objects.NotificationLink(
                href=lcmocc_href(lcmocc.id, endpoint))
        )
    )

    if lcmocc.operationState == fields.LcmOperationStateType.STARTING:
        notif_data.notificationStatus = 'START'
    else:
        notif_data.notificationStatus = 'RESULT'

    if lcmocc.obj_attr_is_set('error'):
        notif_data.error = lcmocc.error

    if notif_data.verbosity == fields.LcmOpOccNotificationVerbosityType.FULL:
        if lcmocc.obj_attr_is_set('resourceChanges'):
            attrs = ['affectedVnfcs',
                     'affectedVirtualLinks',
                     'affectedExtLinkPorts',
                     'affectedVirtualStorages']
            for attr in attrs:
                if lcmocc.resourceChanges.obj_attr_is_set(attr):
                    notif_data[attr] = lcmocc.resourceChanges[attr]
        attrs = ['changedInfo',
                 'changedExtConnectivity',
                 'modificationsTriggeredByVnfPkgChange']
        for attr in attrs:
            if lcmocc.obj_attr_is_set(attr):
                notif_data[attr] = lcmocc[attr]

    return notif_data


def _make_instantiate_lcmocc(lcmocc, inst, change_type):
    # make ResourceChanges of lcmocc from instantiatedVnfInfo.
    # NOTE: grant related info such as resourceDefinitionId, zoneId
    # and so on are not included in lcmocc since such info are not
    # included in instantiatedVnfInfo.

    inst_info = inst.instantiatedVnfInfo

    lcmocc_vncs = []
    if inst_info.obj_attr_is_set('vnfcResourceInfo'):
        for inst_vnc in inst_info.vnfcResourceInfo:
            lcmocc_vnc = objects.AffectedVnfcV2(
                id=inst_vnc.id,
                vduId=inst_vnc.vduId,
                changeType=change_type,
                computeResource=inst_vnc.computeResource
            )
            if inst_vnc.obj_attr_is_set('vnfcCpInfo'):
                cp_ids = [cp.id for cp in inst_vnc.vnfcCpInfo]
                lcmocc_vnc.affectedVnfcCpIds = cp_ids
            if inst_vnc.obj_attr_is_set('storageResourceIds'):
                str_ids = inst_vnc.storageResourceIds
                if change_type == 'ADDED':
                    lcmocc_vnc.addedStorageResourceIds = str_ids
                else:  # 'REMOVED'
                    lcmocc_vnc.removedStorageResourceIds = str_ids
            lcmocc_vncs.append(lcmocc_vnc)

    lcmocc_vls = []
    if inst_info.obj_attr_is_set('vnfVirtualLinkResourceInfo'):
        for inst_vl in inst_info.vnfVirtualLinkResourceInfo:
            lcmocc_vl = objects.AffectedVirtualLinkV2(
                id=inst_vl.id,
                vnfVirtualLinkDescId=inst_vl.vnfVirtualLinkDescId,
                changeType=change_type,
                networkResource=inst_vl.networkResource
            )
            if inst_vl.obj_attr_is_set('vnfLinkPorts'):
                port_ids = [port.id for port in inst_vl.vnfLinkPorts]
                lcmocc_vl.vnfLinkPortIds = port_ids
            lcmocc_vls.append(lcmocc_vl)

    lcmocc_strs = []
    if inst_info.obj_attr_is_set('virtualStorageResourceInfo'):
        for inst_str in inst_info.virtualStorageResourceInfo:
            lcmocc_str = objects.AffectedVirtualStorageV2(
                id=inst_str.id,
                virtualStorageDescId=inst_str.virtualStorageDescId,
                changeType=change_type,
                storageResource=inst_str.storageResource
            )
            lcmocc_strs.append(lcmocc_str)

    if lcmocc_vncs or lcmocc_vls or lcmocc_strs:
        change_info = objects.VnfLcmOpOccV2_ResourceChanges()
        if lcmocc_vncs:
            change_info.affectedVnfcs = lcmocc_vncs
        if lcmocc_vls:
            change_info.affectedVirtualLinks = lcmocc_vls
        if lcmocc_strs:
            change_info.affectedVirtualStorages = lcmocc_strs
        lcmocc.resourceChanges = change_info


def make_instantiate_lcmocc(lcmocc, inst):
    _make_instantiate_lcmocc(lcmocc, inst, 'ADDED')


def make_terminate_lcmocc(lcmocc, inst):
    _make_instantiate_lcmocc(lcmocc, inst, 'REMOVED')


def get_grant_req_and_grant(context, lcmocc):
    grant_reqs = objects.GrantRequestV1.get_by_filter(context,
                                                      vnfLcmOpOccId=lcmocc.id)
    grant = objects.GrantV1.get_by_id(context, lcmocc.grantId)
    if not grant_reqs or grant is None:
        raise sol_ex.GrantRequestOrGrantNotFound(lcmocc_id=lcmocc.id)

    # len(grant_reqs) == 1 because vnfLcmOpOccId is primary key.
    return grant_reqs[0], grant


def check_lcmocc_in_progress(context, inst_id):
    # if the controller or conductor executes an operation for the vnf
    # instance (i.e. operationState is ...ING), other operation for
    # the same vnf instance is exculed by the coordinator.
    # check here is existence of lcmocc for the vnf instance with
    # FAILED_TEMP operationState.
    lcmoccs = objects.VnfLcmOpOccV2.get_by_filter(
        context, vnfInstanceId=inst_id,
        operationState=fields.LcmOperationStateType.FAILED_TEMP)
    if lcmoccs:
        raise sol_ex.OtherOperationInProgress(inst_id=inst_id)
