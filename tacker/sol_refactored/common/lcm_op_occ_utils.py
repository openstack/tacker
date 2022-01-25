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
    return "{}/vnflcm/v2/vnf_lcm_op_occs/{}".format(endpoint, lcmocc_id)


def lcmocc_task_href(lcmocc_id, task, endpoint):
    return "{}/vnflcm/v2/vnf_lcm_op_occs/{}/{}".format(endpoint, lcmocc_id,
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

    if ((lcmocc.operation == fields.LcmOperationType.MODIFY_INFO and
         lcmocc.operationState == fields.LcmOperationStateType.PROCESSING) or
            lcmocc.operationState == fields.LcmOperationStateType.STARTING):
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


def _make_affected_vnfc(vnfc, change_type, strgs):
    affected_vnfc = objects.AffectedVnfcV2(
        id=vnfc.id,
        vduId=vnfc.vduId,
        changeType=change_type,
        computeResource=vnfc.computeResource
    )
    if vnfc.obj_attr_is_set('metadata'):
        affected_vnfc.metadata = vnfc.metadata
    if vnfc.obj_attr_is_set('vnfcCpInfo'):
        cp_ids = [cp.id for cp in vnfc.vnfcCpInfo]
        affected_vnfc.affectedVnfcCpIds = cp_ids
    if vnfc.obj_attr_is_set('storageResourceIds'):
        # NOTE: in case of heal, volume may not be deleted/re-created.
        if change_type == 'ADDED':
            str_ids = [str_id for str_id in vnfc.storageResourceIds
                       if str_id in strgs]
            if str_ids:
                affected_vnfc.addedStorageResourceIds = str_ids
        else:  # 'REMOVED'
            str_ids = [str_id for str_id in vnfc.storageResourceIds
                       if str_id in strgs]
            if str_ids:
                affected_vnfc.removedStorageResourceIds = str_ids

    return affected_vnfc


def _make_affected_vl(vl, change_type):
    affected_vl = objects.AffectedVirtualLinkV2(
        id=vl.id,
        vnfVirtualLinkDescId=vl.vnfVirtualLinkDescId,
        changeType=change_type,
        networkResource=vl.networkResource
    )
    if vl.obj_attr_is_set('vnfLinkPorts'):
        affected_vl.vnfLinkPortIds = [port.id for port in vl.vnfLinkPorts]

    return affected_vl


def _make_affected_vls_link_port_change(vls_saved, vls, common_vls):
    affected_vls = []

    for vl_id in common_vls:
        old_ports = set()
        new_ports = set()
        for vl in vls_saved:
            if vl.id == vl_id:
                old_vl = vl
                if vl.obj_attr_is_set('vnfLinkPorts'):
                    old_ports = {port.id for port in vl.vnfLinkPorts}
        for vl in vls:
            if vl.id == vl_id:
                new_vl = vl
                if vl.obj_attr_is_set('vnfLinkPorts'):
                    new_ports = {port.id for port in vl.vnfLinkPorts}
        add_ports = new_ports - old_ports
        rm_ports = old_ports - new_ports
        # NOTE: Only for extManagedVirtualLink in case of heal
        # (SOL003 all=true) there may be both of add_ports and rm_ports.
        if add_ports:
            affected_vl = objects.AffectedVirtualLinkV2(
                id=new_vl.id,
                vnfVirtualLinkDescId=new_vl.vnfVirtualLinkDescId,
                changeType='LINK_PORT_ADDED',
                networkResource=new_vl.networkResource,
                vnfLinkPortIds=list(add_ports)
            )
            affected_vls.append(affected_vl)
        if rm_ports:
            affected_vl = objects.AffectedVirtualLinkV2(
                id=old_vl.id,
                vnfVirtualLinkDescId=old_vl.vnfVirtualLinkDescId,
                changeType='LINK_PORT_REMOVED',
                networkResource=old_vl.networkResource,
                vnfLinkPortIds=list(rm_ports)
            )
            affected_vls.append(affected_vl)

    return affected_vls


def _make_affected_strg(strg, change_type):
    return objects.AffectedVirtualStorageV2(
        id=strg.id,
        virtualStorageDescId=strg.virtualStorageDescId,
        changeType=change_type,
        storageResource=strg.storageResource
    )


def _make_affected_ext_link_ports(inst_info_saved, inst_info):
    affected_ext_link_ports = []

    ext_vl_ports_saved = set()
    ext_vl_ports = set()
    if inst_info_saved.obj_attr_is_set('extVirtualLinkInfo'):
        for ext_vl in inst_info_saved.extVirtualLinkInfo:
            if ext_vl.obj_attr_is_set('extLinkPorts'):
                ext_vl_ports_saved |= {port.id
                    for port in ext_vl.extLinkPorts}
    if inst_info.obj_attr_is_set('extVirtualLinkInfo'):
        for ext_vl in inst_info.extVirtualLinkInfo:
            if ext_vl.obj_attr_is_set('extLinkPorts'):
                ext_vl_ports |= {port.id
                    for port in ext_vl.extLinkPorts}
    add_ext_vl_ports = ext_vl_ports - ext_vl_ports_saved
    rm_ext_vl_ports = ext_vl_ports_saved - ext_vl_ports

    if add_ext_vl_ports:
        for ext_vl in inst_info.extVirtualLinkInfo:
            if not ext_vl.obj_attr_is_set('extLinkPorts'):
                continue
            affected_ext_link_ports += [
                objects.AffectedExtLinkPortV2(
                    id=port.id,
                    changeType='ADDED',
                    extCpInstanceId=port.cpInstanceId,
                    resourceHandle=port.resourceHandle
                )
                for port in ext_vl.extLinkPorts
                if port.id in add_ext_vl_ports
            ]
    if rm_ext_vl_ports:
        for ext_vl in inst_info_saved.extVirtualLinkInfo:
            if not ext_vl.obj_attr_is_set('extLinkPorts'):
                continue
            affected_ext_link_ports += [
                objects.AffectedExtLinkPortV2(
                    id=port.id,
                    changeType='REMOVED',
                    extCpInstanceId=port.cpInstanceId,
                    resourceHandle=port.resourceHandle
                )
                for port in ext_vl.extLinkPorts
                if port.id in rm_ext_vl_ports
            ]

    return affected_ext_link_ports


def _check_modification(inst_saved, inst, attr):
    if not inst.obj_attr_is_set(attr):
        return False
    if (not inst_saved.obj_attr_is_set(attr) or
            getattr(inst_saved, attr) != getattr(inst, attr)):
        return True
    return False


def _change_vnf_info(lcmocc, inst_saved, inst):
    vnf_info_modify = objects.VnfInfoModificationsV2()

    # vnfdid is required, don't check the existence of the value.
    if inst_saved.vnfdId != inst.vnfdId:
        vnf_info_modify.vnfdId = inst.vnfdId

        if inst_saved.vnfProvider != inst.vnfProvider:
            vnf_info_modify.vnfProvider = inst.vnfProvider
        if inst_saved.vnfProductName != inst.vnfProductName:
            vnf_info_modify.vnfProductName = inst.vnfProductName
        if inst_saved.vnfSoftwareVersion != inst.vnfSoftwareVersion:
            vnf_info_modify.vnfSoftwareVersion = inst.vnfSoftwareVersion
        if inst_saved.vnfdVersion != inst.vnfdVersion:
            vnf_info_modify.vnfdVersion = inst.vnfdVersion

    attrs = ['vnfInstanceName', 'vnfInstanceDescription',
             'vnfConfigurableProperties', 'metadata', 'extensions']
    for attr in attrs:
        if _check_modification(inst_saved, inst, attr):
            setattr(vnf_info_modify, attr, getattr(inst, attr))

    if (inst.obj_attr_is_set('vimConnectionInfo') and
            inst_saved.obj_attr_is_set('vimConnectionInfo')):
        inst_viminfo = inst.to_dict()["vimConnectionInfo"]
        inst_saved_viminfo = inst_saved.to_dict()["vimConnectionInfo"]
        if inst_viminfo != inst_saved_viminfo:
            vnf_info_modify.vimConnectionInfo = inst.vimConnectionInfo
    elif (inst.obj_attr_is_set('vimConnectionInfo') and
            not inst_saved.obj_attr_is_set('vimConnectionInfo')):
        vnf_info_modify.vimConnectionInfo = inst.vimConnectionInfo

    vnfc_info_mod = []
    vnfc_info = []
    if (inst.obj_attr_is_set('instantiatedVnfInfo') and
            inst.instantiatedVnfInfo.obj_attr_is_set('vnfcInfo')):
        vnfc_info = inst.instantiatedVnfInfo.vnfcInfo
    vnfc_info_saved = []
    if (inst_saved.obj_attr_is_set('instantiatedVnfInfo') and
            inst_saved.instantiatedVnfInfo.obj_attr_is_set('vnfcInfo')):
        vnfc_info_saved = inst_saved.instantiatedVnfInfo.vnfcInfo

    for vnfc in vnfc_info:
        prop_saved = {}
        for vnfc_saved in vnfc_info_saved:
            if vnfc.id == vnfc_saved.id:
                if vnfc_saved.obj_attr_is_set('vnfcConfigurableProperties'):
                    prop_saved = vnfc_saved.vnfcConfigurableProperties
                break
        prop = {}
        if vnfc.obj_attr_is_set('vnfcConfigurableProperties'):
            prop = vnfc.vnfcConfigurableProperties
        if prop != prop_saved:
            vnfc_info_mod.append(
                objects.VnfcInfoModificationsV2(
                    id=vnfc.id,
                    vnfcConfigurableProperties=prop
                )
            )
    if vnfc_info_mod:
        vnf_info_modify.vnfcInfoModifications = vnfc_info_mod

    lcmocc.changedInfo = vnf_info_modify


def update_lcmocc(lcmocc, inst_saved, inst):
    # if operation is MODIFY_INFO, make changedInfo of lcmocc.
    # for other operations, make ResourceChanges of lcmocc
    # from instantiatedVnfInfo. In addition if operation is
    # CHANGE_EXT_CONN, make changedExtConnectivity of lcmocc.
    # NOTE: grant related info such as resourceDefinitionId, zoneId
    # and so on are not included in lcmocc since such info are not
    # included in instantiatedVnfInfo.

    if lcmocc.operation == fields.LcmOperationType.MODIFY_INFO:
        _change_vnf_info(lcmocc, inst_saved, inst)
        return

    if inst_saved.obj_attr_is_set('instantiatedVnfInfo'):
        inst_info_saved = inst_saved.instantiatedVnfInfo
    else:
        # dummy
        inst_info_saved = objects.VnfInstanceV2_InstantiatedVnfInfo()

    inst_info = inst.instantiatedVnfInfo

    # NOTE: objects may be re-created. so compare 'id' instead of object
    # itself.
    def _calc_diff(attr):
        # NOTE: instantiatedVnfInfo object is dict compat
        objs_saved = set()
        if inst_info_saved.obj_attr_is_set(attr):
            objs_saved = {obj.id for obj in inst_info_saved[attr]}
        objs = set()
        if inst_info.obj_attr_is_set(attr):
            objs = {obj.id for obj in inst_info[attr]}

        # return removed_objs, added_objs, common_objs
        return objs_saved - objs, objs - objs_saved, objs_saved & objs

    removed_strgs, added_strgs, _ = _calc_diff('virtualStorageResourceInfo')
    affected_strgs = []
    if removed_strgs:
        affected_strgs += [
            _make_affected_strg(strg, 'REMOVED')
            for strg in inst_info_saved.virtualStorageResourceInfo
            if strg.id in removed_strgs
        ]
    if added_strgs:
        affected_strgs += [_make_affected_strg(strg, 'ADDED')
                           for strg in inst_info.virtualStorageResourceInfo
                           if strg.id in added_strgs]

    removed_vnfcs, added_vnfcs, common_objs = _calc_diff('vnfcResourceInfo')
    updated_vnfcs = []
    if lcmocc.operation == fields.LcmOperationType.CHANGE_VNFPKG:
        updated_vnfcs = [
            obj.id for obj in inst_info.vnfcResourceInfo
            if obj.metadata.get('current_vnfd_id') != inst_saved.vnfdId
            and obj.id in common_objs and
            obj.metadata.get('current_vnfd_id') is not None]

    affected_vnfcs = []
    if removed_vnfcs:
        affected_vnfcs += [
            _make_affected_vnfc(vnfc, 'REMOVED', removed_strgs)
            for vnfc in inst_info_saved.vnfcResourceInfo
            if vnfc.id in removed_vnfcs
        ]
    if added_vnfcs:
        affected_vnfcs += [
            _make_affected_vnfc(vnfc, 'ADDED', added_strgs)
            for vnfc in inst_info.vnfcResourceInfo
            if vnfc.id in added_vnfcs
        ]

    if updated_vnfcs:
        affected_vnfcs += [_make_affected_vnfc(vnfc, 'MODIFIED', added_strgs)
                           for vnfc in inst_info.vnfcResourceInfo
                           if vnfc.id in updated_vnfcs]

    removed_vls, added_vls, common_vls = _calc_diff(
        'vnfVirtualLinkResourceInfo')
    affected_vls = []
    if removed_vls:
        affected_vls += [_make_affected_vl(vl, 'REMOVED')
                         for vl in inst_info_saved.vnfVirtualLinkResourceInfo
                         if vl.id in removed_vls]
    if added_vls:
        affected_vls += [_make_affected_vl(vl, 'ADDED')
                         for vl in inst_info.vnfVirtualLinkResourceInfo
                         if vl.id in added_vls]
    if common_vls:
        affected_vls += _make_affected_vls_link_port_change(
            inst_info_saved.vnfVirtualLinkResourceInfo,
            inst_info.vnfVirtualLinkResourceInfo, common_vls)

    removed_mgd_vls, added_mgd_vls, common_mgd_vls = _calc_diff(
        'extManagedVirtualLinkInfo')
    if removed_mgd_vls:
        affected_vls += [_make_affected_vl(vl, 'LINK_PORT_REMOVED')
                         for vl in inst_info_saved.extManagedVirtualLinkInfo
                         if vl.id in removed_mgd_vls]
    if added_mgd_vls:
        affected_vls += [_make_affected_vl(vl, 'LINK_PORT_ADDED')
                         for vl in inst_info.extManagedVirtualLinkInfo
                         if vl.id in added_mgd_vls]
    if common_mgd_vls:
        affected_vls += _make_affected_vls_link_port_change(
            inst_info_saved.extManagedVirtualLinkInfo,
            inst_info.extManagedVirtualLinkInfo, common_mgd_vls)

    affected_ext_link_ports = _make_affected_ext_link_ports(
        inst_info_saved, inst_info)

    if (affected_vnfcs or affected_vls or affected_strgs or
            affected_ext_link_ports):
        change_info = objects.VnfLcmOpOccV2_ResourceChanges()
        if affected_vnfcs:
            change_info.affectedVnfcs = affected_vnfcs
        if affected_vls:
            change_info.affectedVirtualLinks = affected_vls
        if affected_strgs:
            change_info.affectedVirtualStorages = affected_strgs
        if affected_ext_link_ports:
            change_info.affectedExtLinkPorts = affected_ext_link_ports
        lcmocc.resourceChanges = change_info

    if lcmocc.operation == fields.LcmOperationType.CHANGE_EXT_CONN:
        _, added_ext_vls, common_ext_vls = _calc_diff('extVirtualLinkInfo')

        def _get_ext_vl(vl_id, vl_array):
            for vl in vl_array:
                if vl.id == vl_id:
                    return vl

        chg_ext_conn = [_get_ext_vl(ext_vl_id, inst_info.extVirtualLinkInfo)
                        for ext_vl_id in added_ext_vls]

        for ext_vl_id in common_ext_vls:
            ext_vl = _get_ext_vl(ext_vl_id, inst_info.extVirtualLinkInfo)
            ext_vl_saved = _get_ext_vl(ext_vl_id,
                                       inst_info_saved.extVirtualLinkInfo)
            cp_data = []
            if ext_vl.obj_attr_is_set('currentVnfExtCpData'):
                cp_data = sorted(ext_vl.to_dict()['currentVnfExtCpData'],
                                 key=lambda x: x['cpdId'])
            cp_data_saved = []
            if ext_vl_saved.obj_attr_is_set('currentVnfExtCpData'):
                cp_data_saved = sorted(
                    ext_vl_saved.to_dict()['currentVnfExtCpData'],
                    key=lambda x: x['cpdId'])
            if cp_data != cp_data_saved:
                chg_ext_conn.append(ext_vl)
                continue

            # NOTE: For ports created by the heat, the id is not changed if
            # its resourceId is not changed. But for ports given outside the
            # heat, the resourceId may be changed without changing the id,
            # so it is a policy to set changedExtConnectivity when there is
            # a change in "id" or "resourceHandle.resourceId".
            port_ids = set()
            if ext_vl.obj_attr_is_set('extLinkPorts'):
                port_ids = {(port.id, port.resourceHandle.resourceId)
                            for port in ext_vl.extLinkPorts}
            port_ids_saved = set()
            if ext_vl_saved.obj_attr_is_set('extLinkPorts'):
                port_ids_saved = {(port.id, port.resourceHandle.resourceId)
                                  for port in ext_vl_saved.extLinkPorts}
            if port_ids != port_ids_saved:
                chg_ext_conn.append(ext_vl)

        if chg_ext_conn:
            lcmocc.changedExtConnectivity = chg_ext_conn


def get_inst_lcmocc(context, inst):
    lcmoccs = objects.VnfLcmOpOccV2.get_by_filter(
        context, vnfInstanceId=inst.id,
        operationState=fields.LcmOperationStateType.COMPLETED,
        operation=fields.LcmOperationType.INSTANTIATE)
    inst_lcmocc = [inst_lcmocc for inst_lcmocc in lcmoccs
                   if inst_lcmocc.startTime ==
                   max([lcmocc.startTime for lcmocc in lcmoccs])][0]
    return inst_lcmocc


def get_grant_req_and_grant(context, lcmocc):
    if lcmocc.operation == fields.LcmOperationType.MODIFY_INFO:
        return None, None

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
    # the same vnf instance is excluded by the coordinator.
    # check here is existence of lcmocc for the vnf instance with
    # FAILED_TEMP operationState.
    lcmoccs = objects.VnfLcmOpOccV2.get_by_filter(
        context, vnfInstanceId=inst_id,
        operationState=fields.LcmOperationStateType.FAILED_TEMP)
    if lcmoccs:
        raise sol_ex.OtherOperationInProgress(inst_id=inst_id)
