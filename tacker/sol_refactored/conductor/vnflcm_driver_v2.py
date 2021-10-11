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
        method = getattr(self, "%s_%s" % (lcmocc.operation.lower(), 'grant'))
        return method(context, lcmocc, inst, vnfd)

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

    def process(self, context, lcmocc, inst, grant_req, grant, vnfd):
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

    def rollback(self, context, lcmocc, inst, grant_req, grant, vnfd):
        method = getattr(self,
                         "%s_%s" % (lcmocc.operation.lower(), 'rollback'),
                         None)
        if method:
            method(context, lcmocc, inst, grant_req, grant, vnfd)
        else:
            raise sol_ex.RollbackNotSupported(op=lcmocc.operation)

    def _get_link_ports(self, inst_req):
        names = []
        if inst_req.obj_attr_is_set('extVirtualLinks'):
            for ext_vl in inst_req.extVirtualLinks:
                for ext_cp in ext_vl.extCps:
                    for cp_config in ext_cp.cpConfig.values():
                        if cp_config.obj_attr_is_set('linkPortId'):
                            names.append(ext_cp.cpdId)

        if inst_req.obj_attr_is_set('extManagedVirtualLinks'):
            for ext_mgd_vl in inst_req.extManagedVirtualLinks:
                if ext_mgd_vl.obj_attr_is_set('vnfLinkPort'):
                    names.append(ext_mgd_vl.vnfVirtualLinkDescId)

        return names

    def instantiate_grant(self, context, lcmocc, inst, vnfd):
        req = lcmocc.operationParams
        flavour_id = req.flavourId

        if vnfd.get_vnfd_flavour(flavour_id) is None:
            raise sol_ex.FlavourIdNotFound(flavour_id=flavour_id)

        # grant exchange
        # NOTE: the api_version of NFVO supposes 1.4.0 at the moment.
        grant_req = objects.GrantRequestV1(
            vnfInstanceId=inst.id,
            vnfLcmOpOccId=lcmocc.id,
            vnfdId=inst.vnfdId,
            flavourId=flavour_id,
            operation=lcmocc.operation,
            isAutomaticInvocation=lcmocc.isAutomaticInvocation
        )

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

            for _ in range(num):
                res_def = objects.ResourceDefinitionV1(
                    id=uuidutils.generate_uuid(),
                    type='COMPUTE',
                    resourceTemplateId=name)
                add_reses.append(res_def)

            for cp_name in vdu_cp_names:
                if cp_name in link_port_names:
                    continue
                for _ in range(num):
                    res_def = objects.ResourceDefinitionV1(
                        id=uuidutils.generate_uuid(),
                        type='LINKPORT',
                        resourceTemplateId=cp_name)
                    add_reses.append(res_def)

            for storage_name in vdu_storage_names:
                for _ in range(num):
                    res_def = objects.ResourceDefinitionV1(
                        id=uuidutils.generate_uuid(),
                        type='STORAGE',
                        resourceTemplateId=storage_name)
                    add_reses.append(res_def)

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

        grant_req._links = objects.GrantRequestV1_Links(
            vnfLcmOpOcc=objects.Link(
                href=lcmocc_utils.lcmocc_href(lcmocc.id, self.endpoint)),
            vnfInstance=objects.Link(
                href=inst_utils.inst_href(inst.id, self.endpoint)))

        # NOTE: if not granted, 403 error raised.
        grant = self.nfvo_client.grant(context, grant_req)

        return grant_req, grant

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
        lcmocc_utils.make_instantiate_lcmocc(lcmocc, inst)

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

    def terminate_grant(self, context, lcmocc, inst, vnfd):
        # grant exchange
        # NOTE: the api_version of NFVO supposes 1.4.0 at the moment.
        grant_req = objects.GrantRequestV1(
            vnfInstanceId=inst.id,
            vnfLcmOpOccId=lcmocc.id,
            vnfdId=inst.vnfdId,
            operation=lcmocc.operation,
            isAutomaticInvocation=lcmocc.isAutomaticInvocation
        )

        inst_info = inst.instantiatedVnfInfo
        rm_reses = []
        vnfc_cps = {}
        if inst_info.obj_attr_is_set('vnfcResourceInfo'):
            for inst_vnc in inst_info.vnfcResourceInfo:
                res_def = objects.ResourceDefinitionV1(
                    id=uuidutils.generate_uuid(),
                    type='COMPUTE',
                    resourceTemplateId=inst_vnc.vduId,
                    resource=inst_vnc.computeResource)
                rm_reses.append(res_def)

                if inst_vnc.obj_attr_is_set('vnfcCpInfo'):
                    for cp_info in inst_vnc.vnfcCpInfo:
                        res_def = objects.ResourceDefinitionV1(
                            id=uuidutils.generate_uuid(),
                            resourceTemplateId=cp_info.cpdId,
                            type='LINKPORT')
                        rm_reses.append(res_def)
                        if cp_info.obj_attr_is_set('vnfExtCpId'):
                            vnfc_cps[cp_info.vnfExtCpId] = res_def
                        else:  # vnfLinkPortId
                            vnfc_cps[cp_info.vnfLinkPortId] = res_def

        if inst_info.obj_attr_is_set('vnfVirtualLinkResourceInfo'):
            for inst_vl in inst_info.vnfVirtualLinkResourceInfo:
                res_def = objects.ResourceDefinitionV1(
                    id=uuidutils.generate_uuid(),
                    type='VL',
                    resourceTemplateId=inst_vl.vnfVirtualLinkDescId,
                    resource=inst_vl.networkResource)
                rm_reses.append(res_def)

                if inst_vl.obj_attr_is_set('vnfLinkPorts'):
                    for port in inst_vl.vnfLinkPorts:
                        if port.id in vnfc_cps:
                            res_def = vnfc_cps[port.id]
                            res_def.resource = port.resourceHandle

        if inst_info.obj_attr_is_set('virtualStorageResourceInfo'):
            for inst_str in inst_info.virtualStorageResourceInfo:
                res_def = objects.ResourceDefinitionV1(
                    id=uuidutils.generate_uuid(),
                    type='STORAGE',
                    resourceTemplateId=inst_str.virtualStorageDescId,
                    resource=inst_str.storageResource)
                rm_reses.append(res_def)

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

        if rm_reses:
            grant_req.removeResources = rm_reses

        grant_req._links = objects.GrantRequestV1_Links(
            vnfLcmOpOcc=objects.Link(
                href=lcmocc_utils.lcmocc_href(lcmocc.id, self.endpoint)),
            vnfInstance=objects.Link(
                href=inst_utils.inst_href(inst.id, self.endpoint)))

        # NOTE: if not granted, 403 error raised.
        grant_res = self.nfvo_client.grant(context, grant_req)

        return grant_req, grant_res

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
        lcmocc_utils.make_terminate_lcmocc(lcmocc, inst)

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
