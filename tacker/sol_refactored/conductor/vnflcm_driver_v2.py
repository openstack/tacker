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
import pickle
import subprocess

from oslo_log import log as logging
from oslo_utils import uuidutils

from tacker.sol_refactored.common import config
from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.common import lcm_op_occ_utils as lcmocc_utils
from tacker.sol_refactored.common import vim_utils
from tacker.sol_refactored.common import vnf_instance_utils as inst_utils
from tacker.sol_refactored.infra_drivers.openstack import openstack
from tacker.sol_refactored.nfvo import nfvo_client
from tacker.sol_refactored import objects
from tacker.sol_refactored.objects.v2 import fields as v2fields


LOG = logging.getLogger(__name__)

CONF = config.CONF


class VnfLcmDriverV2(object):

    def __init__(self):
        self.endpoint = CONF.v2_vnfm.endpoint
        self.nfvo_client = nfvo_client.NfvoClient()

    def grant(self, context, lcmocc, inst, vnfd):
        # grant exchange
        # NOTE: the api_version of NFVO supposes 1.4.0 at the moment.

        # make common part of grant_req among operations
        grant_req = objects.GrantRequestV1(
            vnfInstanceId=inst.id,
            vnfLcmOpOccId=lcmocc.id,
            vnfdId=inst.vnfdId,
            operation=lcmocc.operation,
            isAutomaticInvocation=lcmocc.isAutomaticInvocation
        )
        grant_req._links = objects.GrantRequestV1_Links(
            vnfLcmOpOcc=objects.Link(
                href=lcmocc_utils.lcmocc_href(lcmocc.id, self.endpoint)),
            vnfInstance=objects.Link(
                href=inst_utils.inst_href(inst.id, self.endpoint)))

        # make operation specific part of grant_req and check request
        # parameters if necessary.
        method = getattr(self, "%s_%s" % (lcmocc.operation.lower(), 'grant'))
        method(grant_req, lcmocc.operationParams, inst, vnfd)

        # NOTE: if not granted, 403 error raised.
        grant = self.nfvo_client.grant(context, grant_req)

        return grant_req, grant

    def post_grant(self, context, lcmocc, inst, grant_req, grant, vnfd):
        method = getattr(self,
                         "%s_%s" % (lcmocc.operation.lower(), 'post_grant'),
                         None)
        if method:
            method(context, lcmocc, inst, grant_req, grant, vnfd)

    def _exec_mgmt_driver_script(self, operation, flavour_id, req, inst,
            grant_req, grant, vnfd):
        script = vnfd.get_interface_script(flavour_id, operation)
        if script is None:
            return

        tmp_csar_dir = vnfd.make_tmp_csar_dir()
        script_dict = {
            'operation': operation,
            'request': req.to_dict(),
            'vnf_instance': inst.to_dict(),
            'grant_request': grant_req.to_dict(),
            'grant_response': grant.to_dict(),
            'tmp_csar_dir': tmp_csar_dir
        }
        # script is relative path to Definitions/xxx.yaml
        script_path = os.path.join(tmp_csar_dir, "Definitions", script)

        out = subprocess.run(["python3", script_path],
            input=pickle.dumps(script_dict),
            capture_output=True)

        vnfd.remove_tmp_csar_dir(tmp_csar_dir)

        if out.returncode != 0:
            LOG.debug("execute %s failed: %s", operation, out.stderr)
            msg = "{} failed: {}".format(operation, out.stderr)
            raise sol_ex.MgmtDriverExecutionFailed(sol_detail=msg)

        LOG.debug("execute %s of %s success.", operation, script)

    def _make_inst_info_common(self, lcmocc, inst_saved, inst, vnfd):
        # make vim independent part of instantiatedVnfInfo.
        # scaleStatus and maxScaleLevels at the moment.
        inst_info = inst.instantiatedVnfInfo
        req = lcmocc.operationParams

        if lcmocc.operation == v2fields.LcmOperationType.INSTANTIATE:
            # create scaleStatus and maxScaleLevels
            flavour_id = req.flavourId
            if req.obj_attr_is_set('instantiationLevelId'):
                inst_level = req.instantiationLevelId
            else:
                inst_level = vnfd.get_default_instantiation_level(flavour_id)

            # make scaleStatus from tosca.policies.nfv.InstantiationLevels
            # definition.
            scale_info = vnfd.get_scale_info_from_inst_level(flavour_id,
                                                             inst_level)
            scale_status = [
                objects.ScaleInfoV2(
                    aspectId=aspect_id,
                    scaleLevel=value['scale_level']
                )
                for aspect_id, value in scale_info.items()
            ]
            max_scale_levels = [
                objects.ScaleInfoV2(
                    aspectId=obj.aspectId,
                    scaleLevel=vnfd.get_max_scale_level(flavour_id,
                                                        obj.aspectId)
                )
                for obj in scale_status
            ]

            if scale_status:
                inst_info.scaleStatus = scale_status
                inst_info.maxScaleLevels = max_scale_levels
        elif lcmocc.operation != v2fields.LcmOperationType.TERMINATE:
            inst_info_saved = inst_saved.instantiatedVnfInfo
            if inst_info_saved.obj_attr_is_set('scaleStatus'):
                inst_info.scaleStatus = inst_info_saved.scaleStatus
                inst_info.maxScaleLevels = inst_info_saved.maxScaleLevels

        if lcmocc.operation == v2fields.LcmOperationType.SCALE:
            # adjust scaleStatus
            num_steps = req.numberOfSteps
            if req.type == 'SCALE_IN':
                num_steps *= -1

            for aspect_info in inst_info.scaleStatus:
                if aspect_info.aspectId == req.aspectId:
                    aspect_info.scaleLevel += num_steps
                    break

    def process(self, context, lcmocc, inst, grant_req, grant, vnfd):
        # save inst to use updating lcmocc after process done
        inst_saved = inst.obj_clone()

        # perform preamble LCM script
        req = lcmocc.operationParams
        operation = "%s_%s" % (lcmocc.operation.lower(), 'start')
        if lcmocc.operation == v2fields.LcmOperationType.INSTANTIATE:
            flavour_id = req.flavourId
        else:
            flavour_id = inst.instantiatedVnfInfo.flavourId
        self._exec_mgmt_driver_script(operation,
            flavour_id, req, inst, grant_req, grant, vnfd)

        # main process
        method = getattr(self, "%s_%s" % (lcmocc.operation.lower(), 'process'))
        method(context, lcmocc, inst, grant_req, grant, vnfd)

        # perform postamble LCM script
        operation = "%s_%s" % (lcmocc.operation.lower(), 'end')
        self._exec_mgmt_driver_script(operation,
            flavour_id, req, inst, grant_req, grant, vnfd)

        self._make_inst_info_common(lcmocc, inst_saved, inst, vnfd)
        lcmocc_utils.update_lcmocc(lcmocc, inst_saved, inst)

    def rollback(self, context, lcmocc, inst, grant_req, grant, vnfd):
        method = getattr(self,
                         "%s_%s" % (lcmocc.operation.lower(), 'rollback'),
                         None)
        if method:
            method(context, lcmocc, inst, grant_req, grant, vnfd)
        else:
            raise sol_ex.RollbackNotSupported(op=lcmocc.operation)

    def _get_link_ports(self, inst_req):
        names = set()
        if inst_req.obj_attr_is_set('extVirtualLinks'):
            for ext_vl in inst_req.extVirtualLinks:
                for ext_cp in ext_vl.extCps:
                    for cp_config in ext_cp.cpConfig.values():
                        if cp_config.obj_attr_is_set('linkPortId'):
                            names.add(ext_cp.cpdId)

        if inst_req.obj_attr_is_set('extManagedVirtualLinks'):
            for ext_mgd_vl in inst_req.extManagedVirtualLinks:
                if ext_mgd_vl.obj_attr_is_set('vnfLinkPort'):
                    names.add(ext_mgd_vl.vnfVirtualLinkDescId)

        return names

    def _make_res_def_for_new_vdu(self, vdu_name, num_inst, cp_names,
            storage_names):
        # common part of instantiate and scale out
        add_reses = []
        for _ in range(num_inst):
            vdu_res_id = uuidutils.generate_uuid()
            add_reses.append(
                objects.ResourceDefinitionV1(
                    id=vdu_res_id,
                    type='COMPUTE',
                    resourceTemplateId=vdu_name
                )
            )
            for cp_name in cp_names:
                add_reses.append(
                    objects.ResourceDefinitionV1(
                        id="{}-{}".format(cp_name, vdu_res_id),
                        type='LINKPORT',
                        resourceTemplateId=cp_name
                    )
                )
            for storage_name in storage_names:
                add_reses.append(
                    objects.ResourceDefinitionV1(
                        id="{}-{}".format(storage_name, vdu_res_id),
                        type='STORAGE',
                        resourceTemplateId=storage_name
                    )
                )

        return add_reses

    def instantiate_grant(self, grant_req, req, inst, vnfd):
        flavour_id = req.flavourId

        if vnfd.get_vnfd_flavour(flavour_id) is None:
            raise sol_ex.FlavourIdNotFound(flavour_id=flavour_id)

        grant_req.flavourId = flavour_id

        if req.obj_attr_is_set('instantiationLevelId'):
            inst_level = req.instantiationLevelId
            grant_req.instantiationLevelId = inst_level
        else:
            inst_level = vnfd.get_default_instantiation_level(flavour_id)

        add_reses = []
        nodes = vnfd.get_vdu_nodes(flavour_id)
        link_port_names = self._get_link_ports(req)
        for name, node in nodes.items():
            num = vnfd.get_vdu_num(flavour_id, name, inst_level)
            vdu_cp_names = vnfd.get_vdu_cps(flavour_id, name)
            vdu_storage_names = vnfd.get_vdu_storages(node)

            add_reses += self._make_res_def_for_new_vdu(name, num,
                set(vdu_cp_names) - link_port_names, vdu_storage_names)

        ext_mgd_vls = []
        if req.obj_attr_is_set('extManagedVirtualLinks'):
            ext_mgd_vls = [ext_mgd_vl.vnfVirtualLinkDescId
                           for ext_mgd_vl in req.extManagedVirtualLinks]
        nodes = vnfd.get_virtual_link_nodes(flavour_id)
        for name in nodes.keys():
            if name in ext_mgd_vls:
                continue
            res_def = objects.ResourceDefinitionV1(
                id=uuidutils.generate_uuid(),
                type='VL',
                resourceTemplateId=name)
            add_reses.append(res_def)

        if add_reses:
            grant_req.addResources = add_reses

        # placementConstraints
        affinity_policies = {
            'AFFINITY': vnfd.get_affinity_targets(flavour_id),
            'ANTI_AFFINITY': vnfd.get_anti_affinity_targets(flavour_id)
        }
        plc_consts = []
        for key, value in affinity_policies.items():
            for targets, scope in value:
                res_refs = []
                for target in targets:
                    for res in add_reses:
                        if res.resourceTemplateId == target:
                            res_ref = objects.ConstraintResourceRefV1(
                                idType='GRANT',
                                resourceId=res.id)
                            res_refs.append(res_ref)

                plc_const = objects.PlacementConstraintV1(
                    affinityOrAntiAffinity=key,
                    scope=scope.upper(),
                    resource=res_refs)
                plc_consts.append(plc_const)

        if plc_consts:
            grant_req.placementConstraints = plc_consts

        if req.obj_attr_is_set('additionalParams'):
            grant_req.additionalParams = req.additionalParams

    def instantiate_post_grant(self, context, lcmocc, inst, grant_req,
            grant, vnfd):
        # set inst vimConnectionInfo
        req = lcmocc.operationParams
        vim_infos = {}
        if req.obj_attr_is_set('vimConnectionInfo'):
            vim_infos = req.vimConnectionInfo

        if grant.obj_attr_is_set('vimConnectionInfo'):
            # if NFVO returns vimConnectionInfo use it.
            # As the controller does for req.vimConnectionInfo, if accessInfo
            # or interfaceInfo is not specified, get them from VIM DB.
            # vimId must be in VIM DB.
            res_vim_infos = grant.vimConnectioninfo
            for key, res_vim_info in res_vim_infos.items():
                if not (res_vim_info.obj_attr_is_set('accessInfo') and
                        res_vim_info.obj_attr_is_set('interfaceInfo')):
                    vim_info = vim_utils.get_vim(context, res_vim_info.vimId)
                    res_vim_infos[key] = vim_info

            vim_infos = inst_utils.json_merge_patch(vim_infos, res_vim_infos)

        if not vim_infos:
            # use the default VIM for the project. tacker special.
            vim_info = vim_utils.get_default_vim(context)
            if vim_info:
                vim_infos["default"] = vim_info
            else:
                # must be one vimConnectionInfo at least.
                raise sol_ex.NoVimConnectionInfo()

        inst.vimConnectionInfo = vim_infos

    def instantiate_process(self, context, lcmocc, inst, grant_req,
            grant, vnfd):
        req = lcmocc.operationParams
        vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
        if vim_info.vimType == 'ETSINFV.OPENSTACK_KEYSTONE.V_3':
            driver = openstack.Openstack()
            driver.instantiate(req, inst, grant_req, grant, vnfd)
        else:
            # only support openstack at the moment
            raise sol_ex.SolException(sol_detail='not support vim type')

        inst.instantiationState = 'INSTANTIATED'

    def instantiate_rollback(self, context, lcmocc, inst, grant_req,
            grant, vnfd):
        req = lcmocc.operationParams
        vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
        if vim_info.vimType == 'ETSINFV.OPENSTACK_KEYSTONE.V_3':
            driver = openstack.Openstack()
            driver.instantiate_rollback(req, inst, grant_req, grant, vnfd)
        else:
            # only support openstack at the moment
            raise sol_ex.SolException(sol_detail='not support vim type')

    def _make_res_def_for_remove_vnfcs(self, inst_info, inst_vnfcs):
        # common part of terminate and scale in
        rm_reses = []
        vnfc_cps = {}
        for inst_vnfc in inst_vnfcs:
            vdu_res_id = uuidutils.generate_uuid()
            rm_reses.append(
                objects.ResourceDefinitionV1(
                    id=vdu_res_id,
                    type='COMPUTE',
                    resourceTemplateId=inst_vnfc.vduId,
                    resource=inst_vnfc.computeResource
                )
            )

            if inst_vnfc.obj_attr_is_set('vnfcCpInfo'):
                for cp_info in inst_vnfc.vnfcCpInfo:
                    if not (cp_info.obj_attr_is_set('vnfExtCpId') or
                            cp_info.obj_attr_is_set('vnfLinkPortId')):
                        # it means extLinkPorts of extVirtualLinks was
                        # specified. so it is not the resource to be
                        # deleted.
                        continue
                    res_def = objects.ResourceDefinitionV1(
                        id="{}-{}".format(cp_info.cpdId, vdu_res_id),
                        resourceTemplateId=cp_info.cpdId,
                        type='LINKPORT')
                    rm_reses.append(res_def)
                    if cp_info.obj_attr_is_set('vnfExtCpId'):
                        vnfc_cps[cp_info.vnfExtCpId] = res_def
                    else:  # vnfLinkPortId
                        vnfc_cps[cp_info.vnfLinkPortId] = res_def

            if inst_vnfc.obj_attr_is_set('storageResourceIds'):
                for storage_id in inst_vnfc.storageResourceIds:
                    for inst_str in inst_info.virtualStorageResourceInfo:
                        if inst_str.id == storage_id:
                            str_name = inst_str.virtualStorageDescId
                            rm_reses.append(
                                objects.ResourceDefinitionV1(
                                    id="{}-{}".format(str_name, vdu_res_id),
                                    type='STORAGE',
                                    resourceTemplateId=str_name,
                                    resource=inst_str.storageResource
                                )
                            )
                            break

        # fill resourceHandle of ports
        if inst_info.obj_attr_is_set('vnfVirtualLinkResourceInfo'):
            for inst_vl in inst_info.vnfVirtualLinkResourceInfo:
                if inst_vl.obj_attr_is_set('vnfLinkPorts'):
                    for port in inst_vl.vnfLinkPorts:
                        if port.id in vnfc_cps:
                            res_def = vnfc_cps[port.id]
                            res_def.resource = port.resourceHandle

        if inst_info.obj_attr_is_set('extVirtualLinkInfo'):
            for ext_vl in inst_info.extVirtualLinkInfo:
                if ext_vl.obj_attr_is_set('extLinkPorts'):
                    for port in ext_vl.extLinkPorts:
                        if (port.obj_attr_is_set('cpInstanceId') and
                                port.cpInstanceId in vnfc_cps):
                            res_def = vnfc_cps[port.cpInstanceId]
                            res_def.resource = port.resourceHandle

        if inst_info.obj_attr_is_set('extManagedVirtualLinkInfo'):
            for ext_mgd_vl in inst_info.extManagedVirtualLinkInfo:
                if ext_mgd_vl.obj_attr_is_set('vnfLinkPorts'):
                    for port in ext_mgd_vl.vnfLinkPorts:
                        if (port.obj_attr_is_set('cpInstanceId') and
                                port.id in vnfc_cps):
                            res_def = vnfc_cps[port.id]
                            res_def.resource = port.resourceHandle

        return rm_reses

    def terminate_grant(self, grant_req, req, inst, vnfd):
        inst_info = inst.instantiatedVnfInfo
        rm_reses = []
        if inst_info.obj_attr_is_set('vnfcResourceInfo'):
            rm_reses += self._make_res_def_for_remove_vnfcs(
                inst_info, inst_info.vnfcResourceInfo)

        if inst_info.obj_attr_is_set('vnfVirtualLinkResourceInfo'):
            for inst_vl in inst_info.vnfVirtualLinkResourceInfo:
                rm_reses.append(
                    objects.ResourceDefinitionV1(
                        id=uuidutils.generate_uuid(),
                        type='VL',
                        resourceTemplateId=inst_vl.vnfVirtualLinkDescId,
                        resource=inst_vl.networkResource
                    )
                )

        if rm_reses:
            grant_req.removeResources = rm_reses

    def terminate_process(self, context, lcmocc, inst, grant_req,
            grant, vnfd):
        req = lcmocc.operationParams
        vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
        if vim_info.vimType == 'ETSINFV.OPENSTACK_KEYSTONE.V_3':
            driver = openstack.Openstack()
            driver.terminate(req, inst, grant_req, grant, vnfd)
        else:
            # only support openstack at the moment
            raise sol_ex.SolException(sol_detail='not support vim type')

        inst.instantiationState = 'NOT_INSTANTIATED'

        # reset instantiatedVnfInfo
        # NOTE: reset after update lcmocc
        inst_vnf_info = objects.VnfInstanceV2_InstantiatedVnfInfo(
            flavourId=inst.instantiatedVnfInfo.flavourId,
            vnfState='STOPPED',
            # NOTE: extCpInfo is omitted. its cardinality is 1..N but it is
            # meaningless to have it for terminated vnf instance.
        )
        inst.instantiatedVnfInfo = inst_vnf_info

        # reset vimConnectionInfo
        inst.vimConnectionInfo = {}

    def scale_grant(self, grant_req, req, inst, vnfd):
        flavour_id = inst.instantiatedVnfInfo.flavourId
        scale_type = req.type
        aspect_id = req.aspectId
        num_steps = req.numberOfSteps

        vdu_num_inst = vnfd.get_scale_vdu_and_num(flavour_id, aspect_id)
        if not vdu_num_inst:
            # should not occur. just check for consistency.
            raise sol_ex.InvalidScaleAspectId(aspect_id=aspect_id)

        if scale_type == 'SCALE_OUT':
            self._make_scale_out_grant_request(grant_req, inst, num_steps,
                vdu_num_inst)
        else:
            self._make_scale_in_grant_request(grant_req, inst, num_steps,
                vdu_num_inst)

        if req.obj_attr_is_set('additionalParams'):
            grant_req.additionalParams = req.additionalParams

    def _make_scale_out_grant_request(self, grant_req, inst, num_steps,
            vdu_num_inst):
        inst_info = inst.instantiatedVnfInfo
        add_reses = []

        # get one of vnfc for the vdu from inst.instantiatedVnfInfo
        vdu_sample = {}
        for vdu_name in vdu_num_inst.keys():
            for inst_vnfc in inst_info.vnfcResourceInfo:
                if inst_vnfc.vduId == vdu_name:
                    vdu_sample[vdu_name] = inst_vnfc
                    break

        for vdu_name, inst_vnfc in vdu_sample.items():
            num_inst = vdu_num_inst[vdu_name] * num_steps

            vdu_cp_names = []
            if inst_vnfc.obj_attr_is_set('vnfcCpInfo'):
                # NOTE: it is expected that there are only dynamic ports
                # for vdus which enable scaling.
                vdu_cp_names = [cp_info.cpdId
                                for cp_info in inst_vnfc.vnfcCpInfo]

            vdu_storage_names = []
            if inst_vnfc.obj_attr_is_set('storageResourceIds'):
                for storage_id in inst_vnfc.storageResourceIds:
                    for storage_res in inst_info.virtualStorageResourceInfo:
                        if storage_res.id == storage_id:
                            vdu_storage_names.append(
                                storage_res.virtualStorageDescId)
                            break

            add_reses += self._make_res_def_for_new_vdu(vdu_name,
                    num_inst, vdu_cp_names, vdu_storage_names)

        if add_reses:
            grant_req.addResources = add_reses

    def _make_scale_in_grant_request(self, grant_req, inst, num_steps,
            vdu_num_inst):
        inst_info = inst.instantiatedVnfInfo
        rm_vnfcs = []

        # select remove VDUs
        # NOTE: scale-in specification of tacker SOL003 v2 API is that
        # newer VDU is selected for reduction.
        # It is expected that vnfcResourceInfo is sorted by creation_time
        # of VDU, newer is earlier.
        for vdu_name, num_inst in vdu_num_inst.items():
            num_inst = num_inst * num_steps

            count = 0
            for inst_vnfc in inst_info.vnfcResourceInfo:
                if inst_vnfc.vduId == vdu_name:
                    rm_vnfcs.append(inst_vnfc)
                    count += 1
                    if count == num_inst:
                        break

        rm_reses = self._make_res_def_for_remove_vnfcs(inst_info, rm_vnfcs)

        if rm_reses:
            grant_req.removeResources = rm_reses

    def scale_process(self, context, lcmocc, inst, grant_req,
            grant, vnfd):
        req = lcmocc.operationParams
        vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
        if vim_info.vimType == 'ETSINFV.OPENSTACK_KEYSTONE.V_3':
            driver = openstack.Openstack()
            driver.scale(req, inst, grant_req, grant, vnfd)
        else:
            # only support openstack at the moment
            raise sol_ex.SolException(sol_detail='not support vim type')

    def scale_rollback(self, context, lcmocc, inst, grant_req,
            grant, vnfd):
        req = lcmocc.operationParams
        if req.type == 'SCALE_IN':
            raise sol_ex.RollbackNotSupported(op='SCALE IN')

        vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
        if vim_info.vimType == 'ETSINFV.OPENSTACK_KEYSTONE.V_3':
            driver = openstack.Openstack()
            driver.scale_rollback(req, inst, grant_req, grant, vnfd)
        else:
            # only support openstack at the moment
            raise sol_ex.SolException(sol_detail='not support vim type')
