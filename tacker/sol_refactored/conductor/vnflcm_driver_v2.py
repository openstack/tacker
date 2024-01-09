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
from tacker.sol_refactored.infra_drivers.kubernetes import helm
from tacker.sol_refactored.infra_drivers.kubernetes import kubernetes
from tacker.sol_refactored.infra_drivers.openstack import openstack
from tacker.sol_refactored.infra_drivers.terraform import terraform
from tacker.sol_refactored.nfvo import nfvo_client
from tacker.sol_refactored import objects
from tacker.sol_refactored.objects.v2 import fields as v2fields


LOG = logging.getLogger(__name__)

CONF = config.CONF


# common sub method
def _get_obj_by_id(obj_id, obj_array):
    # This method assumes that an object that id is obj_id exists.
    for obj in obj_array:
        if obj.id == obj_id:
            return obj
    # not reach here


# sub method for making id
def _make_combination_id(a, b):
    return '{}-{}'.format(a, b)


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
                                 grant_req, grant, vnfd,
                                 user_script_err_handling_data, new_vnfd=None):
        script = vnfd.get_interface_script(flavour_id, operation)
        if script is None:
            return

        tmp_csar_dir = vnfd.make_tmp_csar_dir()
        script_dict = {
            'operation': operation,
            'request': req.to_dict(),
            'vnf_instance': inst.to_dict(),
            'grant_request': (grant_req.to_dict()
                              if grant_req is not None else None),
            'grant_response': (grant.to_dict()
                               if grant is not None else None),
            'tmp_csar_dir': tmp_csar_dir,
            'user_script_err_handling_data': user_script_err_handling_data
        }
        if new_vnfd:
            new_csar_dir = new_vnfd.make_tmp_csar_dir()
            script_dict['new_csar_dir'] = new_csar_dir
        # script is relative path to Definitions/xxx.yaml
        script_path = os.path.join(tmp_csar_dir, "Definitions", script)

        out = subprocess.run(["python3", script_path],
            input=pickle.dumps(script_dict),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        vnfd.remove_tmp_csar_dir(tmp_csar_dir)

        try:
            output = pickle.loads(out.stdout)
            if isinstance(output, dict):
                if 'vnf_instance' in output:
                    _inst = objects.VnfInstanceV2.from_dict(
                        output['vnf_instance'])
                    inst.__dict__.update(_inst.__dict__)
                if 'user_script_err_handling_data' in output:
                    user_script_err_handling_data.update(output[
                        'user_script_err_handling_data'])
        except EOFError:
            pass
        except pickle.UnpicklingError:
            pass

        if out.returncode != 0:
            LOG.debug("execute %s failed: %s", operation, out.stderr)
            msg = "{} failed: {}".format(operation, out.stderr)
            raise sol_ex.MgmtDriverExecutionFailed(sol_detail=msg)

        LOG.debug("execute %s of %s success.", operation, script)

    def _make_inst_info_common(self, lcmocc, inst_saved, inst, vnfd):
        if not inst.obj_attr_is_set('instantiatedVnfInfo'):
            # NOTE: This is only the case that operation is MODIFY_INFO
            # and vnf instance is never instantiated after creation.
            return

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

            if req.obj_attr_is_set('localizationLanguage'):
                inst_info.localizationLanguage = req.localizationLanguage
        elif lcmocc.operation != v2fields.LcmOperationType.TERMINATE:
            inst_info_saved = inst_saved.instantiatedVnfInfo
            if inst_info_saved.obj_attr_is_set('scaleStatus'):
                inst_info.scaleStatus = inst_info_saved.scaleStatus
                inst_info.maxScaleLevels = inst_info_saved.maxScaleLevels
            if inst_info_saved.obj_attr_is_set('localizationLanguage'):
                inst_info.localizationLanguage = (
                    inst_info_saved.localizationLanguage)

        if lcmocc.operation == v2fields.LcmOperationType.SCALE:
            # adjust scaleStatus
            num_steps = req.numberOfSteps
            if req.type == 'SCALE_IN':
                num_steps *= -1

            for aspect_info in inst_info.scaleStatus:
                if aspect_info.aspectId == req.aspectId:
                    aspect_info.scaleLevel += num_steps
                    break

    def _script_method_name(self, operation):
        # According to the definition in etsi_nfv_sol001_vnfd_types.yaml,
        # get script method name from lcmocc.operation.
        # only MODIFY_INFO, CHANGE_EXT_CONN, and CHANGE_VNFPKG are exceptional.
        if operation == v2fields.LcmOperationType.MODIFY_INFO:
            return "modify_information"
        elif operation == v2fields.LcmOperationType.CHANGE_EXT_CONN:
            return "change_external_connectivity"
        elif operation == v2fields.LcmOperationType.CHANGE_VNFPKG:
            return "change_current_package"
        else:
            return operation.lower()

    def process(self, context, lcmocc, inst, grant_req, grant, vnfd,
                user_script_err_handling_data):
        # save inst to use updating lcmocc after process done
        inst_saved = inst.obj_clone()

        # perform preamble LCM script
        req = lcmocc.operationParams
        operation = "{}_start".format(
            self._script_method_name(lcmocc.operation))
        if lcmocc.operation == v2fields.LcmOperationType.INSTANTIATE:
            flavour_id = req.flavourId
        elif inst.obj_attr_is_set('instantiatedVnfInfo'):
            flavour_id = inst.instantiatedVnfInfo.flavourId
        else:
            # NOTE: This is only the case that operation is MODIFY_INFO
            # and vnf instance is never instantiated after creation.
            flavour_id = None
        self._exec_mgmt_driver_script(
            operation, flavour_id, req, inst, grant_req, grant, vnfd,
            user_script_err_handling_data)

        # main process
        method = getattr(self, "%s_%s" % (lcmocc.operation.lower(), 'process'))
        method(context, lcmocc, inst, grant_req, grant, vnfd)

        # perform postamble LCM script
        new_vnfd = None
        if (lcmocc.operation == v2fields.LcmOperationType.MODIFY_INFO
                and req.obj_attr_is_set('vnfdId')):
            new_vnfd = self.nfvo_client.get_vnfd(
                context, req.vnfdId, all_contents=True)
        operation = "{}_end".format(self._script_method_name(lcmocc.operation))
        self._exec_mgmt_driver_script(
            operation, flavour_id, req, inst, grant_req, grant, vnfd,
            user_script_err_handling_data, new_vnfd=new_vnfd)

        self._make_inst_info_common(lcmocc, inst_saved, inst, vnfd)
        lcmocc_utils.update_lcmocc(lcmocc, inst_saved, inst)

    def rollback(self, context, lcmocc, inst, grant_req, grant, vnfd,
                 user_script_err_handling_data):
        method = getattr(self,
                         "%s_%s" % (lcmocc.operation.lower(), 'rollback'),
                         None)
        if not method:
            raise sol_ex.RollbackNotSupported(op=lcmocc.operation)

        # perform preamble LCM script
        req = lcmocc.operationParams
        operation_name = self._script_method_name(lcmocc.operation)
        operation = f"{operation_name}_rollback_start"
        if lcmocc.operation == v2fields.LcmOperationType.INSTANTIATE:
            flavour_id = req.flavourId
        elif inst.obj_attr_is_set('instantiatedVnfInfo'):
            flavour_id = inst.instantiatedVnfInfo.flavourId
        else:
            # NOTE: This is only the case that operation is MODIFY_INFO
            # and vnf instance is never instantiated after creation.
            flavour_id = None
        self._exec_mgmt_driver_script(
            operation, flavour_id, req, inst, grant_req,
            grant, vnfd, user_script_err_handling_data)

        method(context, lcmocc, inst, grant_req, grant, vnfd)

        # perform postamble LCM script
        operation = f"{operation_name}_rollback_end"
        self._exec_mgmt_driver_script(
            operation, flavour_id, req, inst, grant_req,
            grant, vnfd, user_script_err_handling_data)

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
                        id=_make_combination_id(cp_name, vdu_res_id),
                        type='LINKPORT',
                        resourceTemplateId=cp_name
                    )
                )
            for storage_name in storage_names:
                add_reses.append(
                    objects.ResourceDefinitionV1(
                        id=_make_combination_id(storage_name, vdu_res_id),
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
        self._make_placementconstraints(grant_req, vnfd, add_reses, inst)

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
            res_vim_infos = grant.vimConnectionInfo
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

        # vimType dependent parameter check
        # NOTE: controller cannot check because vim_info is not identified
        # to here, although it is better to check in controller.
        if lcmocc.operationState == v2fields.LcmOperationStateType.STARTING:
            vim_info = inst_utils.select_vim_info(vim_infos)
            if vim_info.vimType == "ETSINFV.KUBERNETES.V_1":
                if 'endpoint' not in vim_info.interfaceInfo:
                    detail = "Required attribute missing in vimConnectionInfo"
                    raise sol_ex.SolValidationError(detail=detail)
                if (not req.get('additionalParams', {}).get(
                        'lcm-kubernetes-def-files')):
                    raise sol_ex.SolValidationError(
                        detail="'lcm-kubernetes-def-files' must be specified")
            elif vim_info.vimType == "ETSINFV.HELM.V_3":
                if ('endpoint' not in vim_info.interfaceInfo or
                        'ssl_ca_cert' not in vim_info.interfaceInfo or
                        'bearer_token' not in vim_info.accessInfo):
                    detail = "Required attribute missing in vimConnectionInfo"
                    raise sol_ex.SolValidationError(detail=detail)
                if (not req.get('additionalParams', {}).get(
                        'helm_chart_path')):
                    raise sol_ex.SolValidationError(
                        detail="'helm_chart_path' must be specified")
                if (not req.get('additionalParams', {}).get(
                        'helm_value_names')):
                    raise sol_ex.SolValidationError(
                        detail="'helm_value_names' must be specified")

    def instantiate_process(self, context, lcmocc, inst, grant_req,
            grant, vnfd):
        req = lcmocc.operationParams
        for attr in ['vnfConfigurableProperties', 'extensions']:
            self._modify_from_req(inst, req, attr)

        vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
        if vim_info.vimType == 'ETSINFV.OPENSTACK_KEYSTONE.V_3':
            driver = openstack.Openstack()
            driver.instantiate(req, inst, grant_req, grant, vnfd)
        elif vim_info.vimType == 'ETSINFV.KUBERNETES.V_1':
            driver = kubernetes.Kubernetes()
            driver.instantiate(req, inst, grant_req, grant, vnfd)
        elif vim_info.vimType == 'ETSINFV.HELM.V_3':
            driver = helm.Helm()
            driver.instantiate(req, inst, grant_req, grant, vnfd)
        elif vim_info.vimType == 'TERRAFORM.V1':
            driver = terraform.Terraform()
            driver.instantiate(req, inst, grant_req, grant, vnfd)
        else:
            # should not occur
            raise sol_ex.SolException(sol_detail='not support vim type')

        inst.instantiationState = 'INSTANTIATED'

    def instantiate_rollback(self, context, lcmocc, inst, grant_req,
            grant, vnfd):
        req = lcmocc.operationParams
        vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
        if vim_info.vimType == 'ETSINFV.OPENSTACK_KEYSTONE.V_3':
            driver = openstack.Openstack()
            driver.instantiate_rollback(req, inst, grant_req, grant, vnfd)
        elif vim_info.vimType == 'ETSINFV.KUBERNETES.V_1':
            driver = kubernetes.Kubernetes()
            driver.instantiate_rollback(req, inst, grant_req, grant, vnfd)
        elif vim_info.vimType == 'ETSINFV.HELM.V_3':
            driver = helm.Helm()
            driver.instantiate_rollback(req, inst, grant_req, grant, vnfd)
        elif vim_info.vimType == 'TERRAFORM.V1':
            driver = terraform.Terraform()
            driver.instantiate_rollback(req, inst, grant_req, grant, vnfd)
        else:
            # should not occur
            raise sol_ex.SolException(sol_detail='not support vim type')

    def _make_res_def_for_remove_vnfcs(self, inst_info, inst_vnfcs,
            re_create=False):
        # common part of terminate, scale-in and heal.
        # only heal calls with re_create=True.
        rm_reses = []
        add_reses = []
        vnfc_cps = {}
        for inst_vnfc in inst_vnfcs:
            rm_vdu_res_id = uuidutils.generate_uuid()
            rm_reses.append(
                objects.ResourceDefinitionV1(
                    id=rm_vdu_res_id,
                    type='COMPUTE',
                    resourceTemplateId=inst_vnfc.vduId,
                    resource=inst_vnfc.computeResource
                )
            )
            if re_create:
                add_vdu_res_id = uuidutils.generate_uuid()
                add_reses.append(
                    objects.ResourceDefinitionV1(
                        id=add_vdu_res_id,
                        type='COMPUTE',
                        resourceTemplateId=inst_vnfc.vduId,
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
                        id=_make_combination_id(cp_info.cpdId, rm_vdu_res_id),
                        resourceTemplateId=cp_info.cpdId,
                        type='LINKPORT')
                    rm_reses.append(res_def)
                    if cp_info.obj_attr_is_set('vnfExtCpId'):
                        vnfc_cps[cp_info.vnfExtCpId] = res_def
                    else:  # vnfLinkPortId
                        vnfc_cps[cp_info.vnfLinkPortId] = res_def

                    if re_create:
                        add_reses.append(
                            objects.ResourceDefinitionV1(
                                id=_make_combination_id(cp_info.cpdId,
                                                        add_vdu_res_id),
                                resourceTemplateId=cp_info.cpdId,
                                type='LINKPORT'
                            )
                        )

            if inst_vnfc.obj_attr_is_set('storageResourceIds'):
                for storage_id in inst_vnfc.storageResourceIds:
                    inst_str = _get_obj_by_id(storage_id,
                        inst_info.virtualStorageResourceInfo)
                    str_name = inst_str.virtualStorageDescId
                    rm_reses.append(
                        objects.ResourceDefinitionV1(
                            id=_make_combination_id(str_name, rm_vdu_res_id),
                            type='STORAGE',
                            resourceTemplateId=str_name,
                            resource=inst_str.storageResource
                        )
                    )
                    if re_create:
                        add_reses.append(
                            objects.ResourceDefinitionV1(
                                id=_make_combination_id(str_name,
                                                        add_vdu_res_id),
                                type='STORAGE',
                                resourceTemplateId=str_name
                            )
                        )

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

        return rm_reses, add_reses

    def terminate_grant(self, grant_req, req, inst, vnfd):
        inst_info = inst.instantiatedVnfInfo
        rm_reses = []
        if inst_info.obj_attr_is_set('vnfcResourceInfo'):
            rm_reses, _ = self._make_res_def_for_remove_vnfcs(
                inst_info, inst_info.vnfcResourceInfo)

        if inst_info.obj_attr_is_set('vnfVirtualLinkResourceInfo'):
            rm_reses += [
                objects.ResourceDefinitionV1(
                    id=uuidutils.generate_uuid(),
                    type='VL',
                    resourceTemplateId=inst_vl.vnfVirtualLinkDescId,
                    resource=inst_vl.networkResource
                )
                for inst_vl in inst_info.vnfVirtualLinkResourceInfo
            ]

        if rm_reses:
            grant_req.removeResources = rm_reses

    def terminate_process(self, context, lcmocc, inst, grant_req,
            grant, vnfd):
        req = lcmocc.operationParams
        vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
        if vim_info.vimType == 'ETSINFV.OPENSTACK_KEYSTONE.V_3':
            driver = openstack.Openstack()
            driver.terminate(req, inst, grant_req, grant, vnfd)
        elif vim_info.vimType == 'ETSINFV.KUBERNETES.V_1':
            driver = kubernetes.Kubernetes()
            driver.terminate(req, inst, grant_req, grant, vnfd)
        elif vim_info.vimType == 'ETSINFV.HELM.V_3':
            driver = helm.Helm()
            driver.terminate(req, inst, grant_req, grant, vnfd)
        elif vim_info.vimType == 'TERRAFORM.V1':
            driver = terraform.Terraform()
            driver.terminate(req, inst, grant_req, grant, vnfd)
        else:
            # should not occur
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

        # NOTE: flavourId is not necessary according to the SOL003 spec.
        # It is for local_nfvo to handle images.
        grant_req.flavourId = flavour_id

        vdu_num_inst = vnfd.get_scale_vdu_and_num(flavour_id, aspect_id)
        if not vdu_num_inst:
            # should not occur. just check for consistency.
            raise sol_ex.InvalidScaleAspectId(aspect_id=aspect_id)

        if scale_type == 'SCALE_OUT':
            self._make_scale_out_grant_request(grant_req, inst, num_steps,
                vdu_num_inst, vnfd)
        else:
            self._make_scale_in_grant_request(grant_req, inst, num_steps,
                vdu_num_inst)

        if req.obj_attr_is_set('additionalParams'):
            grant_req.additionalParams = req.additionalParams

    def _make_scale_out_grant_request(self, grant_req, inst, num_steps,
            vdu_num_inst, vnfd):
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
                    storage_res = _get_obj_by_id(storage_id,
                        inst_info.virtualStorageResourceInfo)
                    vdu_storage_names.append(
                        storage_res.virtualStorageDescId)

            add_reses += self._make_res_def_for_new_vdu(vdu_name,
                    num_inst, vdu_cp_names, vdu_storage_names)

        if add_reses:
            grant_req.addResources = add_reses

        # placementConstraints
        self._make_placementconstraints(grant_req, vnfd, add_reses, inst)

    def _make_placementconstraints(self, grant_req, vnfd, add_reses, inst):
        affinity_policies = {
            'AFFINITY': vnfd.get_affinity_targets(grant_req.flavourId),
            'ANTI_AFFINITY': vnfd.get_anti_affinity_targets(
                grant_req.flavourId)
        }
        plc_consts = []
        for key, value in affinity_policies.items():
            for targets, scope in value:
                res_refs = []
                for res in add_reses:
                    if res.resourceTemplateId in targets:
                        res_ref = objects.ConstraintResourceRefV1(
                            idType='GRANT',
                            resourceId=res.id)
                        res_refs.append(res_ref)

                if not res_refs:
                    break

                if (inst.obj_attr_is_set('instantiatedVnfInfo') and
                        inst.instantiatedVnfInfo.obj_attr_is_set(
                            'vnfcResourceInfo')):
                    for vnfc in inst.instantiatedVnfInfo.vnfcResourceInfo:
                        if vnfc.vduId in targets:
                            res_ref = objects.ConstraintResourceRefV1(
                                idType='RES_MGMT',
                                resourceId=vnfc.computeResource.resourceId,
                                vimConnectionId=(
                                    vnfc.computeResource.vimConnectionId))
                            res_refs.append(res_ref)

                # NOTE: It is meaningless if the target resource is less
                # than 2, because it is intended to show the relationship
                # between the resources.
                if len(res_refs) < 2:
                    break

                plc_const = objects.PlacementConstraintV1(
                    affinityOrAntiAffinity=key,
                    scope=scope.upper(),
                    resource=res_refs,
                    fallbackBestEffort=(
                        CONF.v2_vnfm.placement_fallback_best_effort))
                plc_consts.append(plc_const)

        if plc_consts:
            grant_req.placementConstraints = plc_consts

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

        rm_reses, _ = self._make_res_def_for_remove_vnfcs(inst_info, rm_vnfcs)

        if rm_reses:
            grant_req.removeResources = rm_reses

    def scale_process(self, context, lcmocc, inst, grant_req,
            grant, vnfd):
        req = lcmocc.operationParams
        vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
        if vim_info.vimType == 'ETSINFV.OPENSTACK_KEYSTONE.V_3':
            driver = openstack.Openstack()
            driver.scale(req, inst, grant_req, grant, vnfd)
        elif vim_info.vimType == 'ETSINFV.KUBERNETES.V_1':
            driver = kubernetes.Kubernetes()
            driver.scale(req, inst, grant_req, grant, vnfd)
        elif vim_info.vimType == 'ETSINFV.HELM.V_3':
            driver = helm.Helm()
            driver.scale(req, inst, grant_req, grant, vnfd)
        else:
            # should not occur
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
        elif vim_info.vimType == 'ETSINFV.KUBERNETES.V_1':
            driver = kubernetes.Kubernetes()
            driver.scale_rollback(req, inst, grant_req, grant, vnfd)
        elif vim_info.vimType == 'ETSINFV.HELM.V_3':
            driver = helm.Helm()
            driver.scale_rollback(req, inst, grant_req, grant, vnfd)
        else:
            # should not occur
            raise sol_ex.SolException(sol_detail='not support vim type')

    def _modify_from_vnfd_prop(self, inst, vnfd_prop, attr):
        if vnfd_prop.get(attr):
            base = getattr(inst, attr) if inst.obj_attr_is_set(attr) else {}
            setattr(inst, attr, inst_utils.json_merge_patch(
                base, vnfd_prop[attr]))

    def _modify_from_req(self, inst, req, attr):
        if req.obj_attr_is_set(attr):
            base = getattr(inst, attr) if inst.obj_attr_is_set(attr) else {}
            setattr(inst, attr, inst_utils.json_merge_patch(
                base, getattr(req, attr)))

    def _modify_inst_vnfd_id(self, context, inst, vnfd):
        pkg_info = self.nfvo_client.get_vnf_package_info_vnfd(
            context, inst.vnfdId)

        vnfd_prop = vnfd.get_vnfd_properties()

        inst.vnfProvider = pkg_info.vnfProvider
        inst.vnfProductName = pkg_info.vnfProductName
        inst.vnfSoftwareVersion = pkg_info.vnfSoftwareVersion
        inst.vnfdVersion = pkg_info.vnfdVersion

        attrs = ['vnfConfigurableProperties', 'metadata', 'extensions']
        for attr in attrs:
            self._modify_from_vnfd_prop(inst, vnfd_prop, attr)

    def _merge_vim_connection_info(self, inst, req):
        # used by MODIFY_INFO and CHANGE_EXT_CONN
        # inst.vimConnectionInfo exists since req.vimConnectionInfo
        # can be set only if vnf instance is INSTANTIATED.
        inst_viminfo = inst.to_dict()['vimConnectionInfo']
        req_viminfo = req.to_dict()['vimConnectionInfo']
        merge = inst_utils.json_merge_patch(inst_viminfo, req_viminfo)
        inst.vimConnectionInfo = {
            key: objects.VimConnectionInfo.from_dict(value)
            for key, value in merge.items()}

    def modify_info_process(self, context, lcmocc, inst, grant_req,
            grant, vnfd):
        req = lcmocc.operationParams

        if req.obj_attr_is_set('vnfInstanceName'):
            inst.vnfInstanceName = req.vnfInstanceName

        if req.obj_attr_is_set('vnfInstanceDescription'):
            inst.vnfInstanceDescription = req.vnfInstanceDescription

        if req.obj_attr_is_set('vnfdId') and req.vnfdId != inst.vnfdId:
            # NOTE: When vnfdId is changed, the values of attributes
            # in the VnfInstance needs update from new VNFD.
            inst.vnfdId = req.vnfdId
            new_vnfd = self.nfvo_client.get_vnfd(context, inst.vnfdId)
            self._modify_inst_vnfd_id(context, inst, new_vnfd)

        attrs = ['vnfConfigurableProperties', 'metadata', 'extensions']
        for attr in attrs:
            self._modify_from_req(inst, req, attr)

        if inst.obj_attr_is_set('metadata'):
            inst_utils.check_metadata_format(inst.metadata)

        if req.obj_attr_is_set('vimConnectionInfo'):
            self._merge_vim_connection_info(inst, req)

        if req.obj_attr_is_set('vnfcInfoModifications'):
            for vnfc_mod in req.vnfcInfoModifications:
                # existence of ids are checked by controller
                for vnfc_info in inst.instantiatedVnfInfo.vnfcInfo:
                    if vnfc_mod.id == vnfc_info.id:
                        prop_base = {}
                        if vnfc_info.obj_attr_is_set(
                                'vnfcConfigurableProperties'):
                            prop_base = vnfc_info.vnfcConfigurableProperties
                        vnfc_info.vnfcConfigurableProperties = (
                            inst_utils.json_merge_patch(prop_base,
                                vnfc_mod.vnfcConfigurableProperties))
                        break

    def modify_info_rollback(self, context, lcmocc, inst, grant_req,
            grant, vnfd):
        # DB is not updated, rollback does nothing and makes it successful.
        pass

    def _set_rm_add_reses(self, rm_reses, add_reses, res_type, res_name,
            res_obj, rm_id, add_id):
        rm_reses.append(
            objects.ResourceDefinitionV1(
                id=rm_id,
                type=res_type,
                resourceTemplateId=res_name,
                resource=res_obj
            )
        )
        add_reses.append(
            objects.ResourceDefinitionV1(
                id=add_id,
                type=res_type,
                resourceTemplateId=res_name
            )
        )

    def _make_SOL002_heal_grant_request(self, grant_req, req, inst_info,
            is_all):
        rm_reses = []
        add_reses = []

        for vnfc in inst_info.vnfcInfo:
            if vnfc.id not in req.vnfcInstanceId:
                continue
            inst_vnfc = _get_obj_by_id(vnfc.vnfcResourceInfoId,
                                       inst_info.vnfcResourceInfo)
            rm_vdu_res_id = uuidutils.generate_uuid()
            add_vdu_res_id = uuidutils.generate_uuid()
            self._set_rm_add_reses(rm_reses, add_reses, 'COMPUTE',
                inst_vnfc.vduId, inst_vnfc.computeResource,
                rm_vdu_res_id, add_vdu_res_id)

            if is_all and inst_vnfc.obj_attr_is_set('storageResourceIds'):
                for storage_id in inst_vnfc.storageResourceIds:
                    inst_str = _get_obj_by_id(storage_id,
                        inst_info.virtualStorageResourceInfo)
                    str_name = inst_str.virtualStorageDescId
                    self._set_rm_add_reses(rm_reses, add_reses, 'STORAGE',
                        str_name, inst_str.storageResource,
                        _make_combination_id(str_name, rm_vdu_res_id),
                        _make_combination_id(str_name, add_vdu_res_id))

        if rm_reses:
            grant_req.removeResources = rm_reses
            grant_req.addResources = add_reses

    def _make_SOL003_heal_grant_request(self, grant_req, req, inst_info,
            is_all):
        rm_reses = []
        add_reses = []

        if is_all:
            if inst_info.obj_attr_is_set('vnfcResourceInfo'):
                rm_reses, add_reses = self._make_res_def_for_remove_vnfcs(
                    inst_info, inst_info.vnfcResourceInfo, re_create=True)

            if inst_info.obj_attr_is_set('vnfVirtualLinkResourceInfo'):
                for inst_vl in inst_info.vnfVirtualLinkResourceInfo:
                    self._set_rm_add_reses(rm_reses, add_reses, 'VL',
                        inst_vl.vnfVirtualLinkDescId, inst_vl.networkResource,
                        uuidutils.generate_uuid(), uuidutils.generate_uuid())
        else:
            if inst_info.obj_attr_is_set('vnfcResourceInfo'):
                for inst_vnfc in inst_info.vnfcResourceInfo:
                    self._set_rm_add_reses(rm_reses, add_reses, 'COMPUTE',
                        inst_vnfc.vduId, inst_vnfc.computeResource,
                        uuidutils.generate_uuid(), uuidutils.generate_uuid())

        if rm_reses:
            grant_req.removeResources = rm_reses
            grant_req.addResources = add_reses

    def heal_grant(self, grant_req, req, inst, vnfd):
        inst_info = inst.instantiatedVnfInfo

        # NOTE: flavourId is not necessary according to the SOL003 spec.
        # It is for local_nfvo to handle images.
        grant_req.flavourId = inst_info.flavourId

        is_all = False  # default is False
        if req.obj_attr_is_set('additionalParams'):
            is_all = req.additionalParams.get('all', False)
            grant_req.additionalParams = req.additionalParams

        if req.obj_attr_is_set('vnfcInstanceId'):
            self._make_SOL002_heal_grant_request(grant_req, req, inst_info,
                                                 is_all)
        else:
            self._make_SOL003_heal_grant_request(grant_req, req, inst_info,
                                                 is_all)

    def heal_process(self, context, lcmocc, inst, grant_req, grant, vnfd):
        req = lcmocc.operationParams
        vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
        if vim_info.vimType == 'ETSINFV.OPENSTACK_KEYSTONE.V_3':
            driver = openstack.Openstack()
            driver.heal(req, inst, grant_req, grant, vnfd)
        elif vim_info.vimType == 'ETSINFV.KUBERNETES.V_1':
            driver = kubernetes.Kubernetes()
            driver.heal(req, inst, grant_req, grant, vnfd)
        elif vim_info.vimType == 'ETSINFV.HELM.V_3':
            driver = helm.Helm()
            driver.heal(req, inst, grant_req, grant, vnfd)
        else:
            # should not occur
            raise sol_ex.SolException(sol_detail='not support vim type')

    def change_ext_conn_grant(self, grant_req, req, inst, vnfd):
        inst_info = inst.instantiatedVnfInfo

        cp_names = set()
        link_ports = set()
        for ext_vl in req.extVirtualLinks:
            for ext_cp in ext_vl.extCps:
                cp_names.add(ext_cp.cpdId)
                for cp_config in ext_cp.cpConfig.values():
                    if cp_config.obj_attr_is_set('linkPortId'):
                        link_ports.add(ext_cp.cpdId)

        add_reses = []
        rm_reses = []
        update_reses = []
        rm_vnfc_cps = {}
        for inst_vnfc in inst_info.vnfcResourceInfo:
            if not inst_vnfc.obj_attr_is_set('vnfcCpInfo'):
                continue
            vnfc_cps = {cp_info.cpdId for cp_info in inst_vnfc.vnfcCpInfo}
            if not vnfc_cps & cp_names:
                continue

            old_vdu_res_id = uuidutils.generate_uuid()
            new_vdu_res_id = uuidutils.generate_uuid()
            update_reses.append(
                objects.ResourceDefinitionV1(
                    id=new_vdu_res_id,
                    type='COMPUTE',
                    resourceTemplateId=inst_vnfc.vduId,
                    resource=inst_vnfc.computeResource
                )
            )

            for cp_info in inst_vnfc.vnfcCpInfo:
                if cp_info.cpdId not in cp_names:
                    continue

                if cp_info.obj_attr_is_set('vnfExtCpId'):
                    # if there is not vnfExtCpId, it means extLinkPorts of
                    # extVirtualLinks was specified.
                    res_def = objects.ResourceDefinitionV1(
                        id=_make_combination_id(cp_info.cpdId, old_vdu_res_id),
                        resourceTemplateId=cp_info.cpdId,
                        type='LINKPORT')
                    rm_reses.append(res_def)
                    rm_vnfc_cps[cp_info.vnfExtCpId] = res_def

                if cp_info.cpdId not in link_ports:
                    add_reses.append(
                        objects.ResourceDefinitionV1(
                            id=_make_combination_id(cp_info.cpdId,
                                                    new_vdu_res_id),
                            resourceTemplateId=cp_info.cpdId,
                            type='LINKPORT'
                        )
                    )

        # fill resourceHandle of rm_reses
        if inst_info.obj_attr_is_set('extVirtualLinkInfo'):
            for ext_vl in inst_info.extVirtualLinkInfo:
                if ext_vl.obj_attr_is_set('extLinkPorts'):
                    for port in ext_vl.extLinkPorts:
                        if (port.obj_attr_is_set('cpInstanceId') and
                                port.cpInstanceId in rm_vnfc_cps):
                            res_def = rm_vnfc_cps[port.cpInstanceId]
                            res_def.resource = port.resourceHandle

        if add_reses:
            grant_req.addResources = add_reses
        if rm_reses:
            grant_req.removeResources = rm_reses
        if update_reses:
            grant_req.updateResources = update_reses

        if req.obj_attr_is_set('additionalParams'):
            grant_req.additionalParams = req.additionalParams

    def change_ext_conn_process(self, context, lcmocc, inst, grant_req,
            grant, vnfd):
        req = lcmocc.operationParams
        if req.obj_attr_is_set('vimConnectionInfo'):
            self._merge_vim_connection_info(inst, req)

        vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
        if vim_info.vimType == 'ETSINFV.OPENSTACK_KEYSTONE.V_3':
            driver = openstack.Openstack()
            driver.change_ext_conn(req, inst, grant_req, grant, vnfd)
        else:
            # only support openstack at the moment
            raise sol_ex.SolException(sol_detail='not support vim type')

    def change_ext_conn_rollback(self, context, lcmocc, inst, grant_req,
            grant, vnfd):
        req = lcmocc.operationParams
        vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
        if vim_info.vimType == 'ETSINFV.OPENSTACK_KEYSTONE.V_3':
            driver = openstack.Openstack()
            driver.change_ext_conn_rollback(req, inst, grant_req, grant, vnfd)
        else:
            # only support openstack at the moment
            raise sol_ex.SolException(sol_detail='not support vim type')

    def change_vnfpkg_grant(self, grant_req, req, inst, vnfd):
        grant_req.dstVnfdId = req.vnfdId
        # NOTE: flavourId is not necessary according to the SOL003 spec.
        # It is for local_nfvo to handle images.
        grant_req.flavourId = inst.instantiatedVnfInfo.flavourId

        if req.additionalParams['upgrade_type'] == 'RollingUpdate':
            self._change_vnfpkg_grant_rolling_update(
                grant_req, req, inst, vnfd)
        else:
            # Only support RollingUpdate at the moment.
            pass

    def _change_vnfpkg_grant_rolling_update(self, grant_req, req, inst, vnfd):
        inst_info = inst.instantiatedVnfInfo
        if not inst_info.obj_attr_is_set('vnfcResourceInfo'):
            return

        vdu_ids = [vdu_param['vdu_id']
                   for vdu_param in req.additionalParams['vdu_params']]
        inst_vnfcs = [inst_vnfc
                      for inst_vnfc in inst_info.vnfcResourceInfo
                      if inst_vnfc.vduId in vdu_ids]

        add_reses = []
        rm_reses = []
        for inst_vnfc in inst_vnfcs:
            rm_vdu_res_id = uuidutils.generate_uuid()
            add_vdu_res_id = uuidutils.generate_uuid()
            self._set_rm_add_reses(rm_reses, add_reses, 'COMPUTE',
                inst_vnfc.vduId, inst_vnfc.computeResource,
                rm_vdu_res_id, add_vdu_res_id)

            if inst_vnfc.obj_attr_is_set('storageResourceIds'):
                for storage_id in inst_vnfc.storageResourceIds:
                    inst_str = _get_obj_by_id(storage_id,
                        inst_info.virtualStorageResourceInfo)
                    str_name = inst_str.virtualStorageDescId
                    self._set_rm_add_reses(rm_reses, add_reses, 'STORAGE',
                        str_name, inst_str.storageResource,
                        _make_combination_id(str_name, rm_vdu_res_id),
                        _make_combination_id(str_name, add_vdu_res_id))

        if add_reses:
            grant_req.addResources = add_reses
        if rm_reses:
            grant_req.removeResources = rm_reses

    def change_vnfpkg_process(
            self, context, lcmocc, inst, grant_req, grant, vnfd):
        req = lcmocc.operationParams
        if req.obj_attr_is_set('vimConnectionInfo'):
            self._merge_vim_connection_info(inst, req)

        vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
        if vim_info.vimType == 'ETSINFV.OPENSTACK_KEYSTONE.V_3':
            driver = openstack.Openstack()
            driver.change_vnfpkg(req, inst, grant_req, grant, vnfd)
        elif vim_info.vimType == 'ETSINFV.KUBERNETES.V_1':
            driver = kubernetes.Kubernetes()
            driver.change_vnfpkg(req, inst, grant_req, grant, vnfd)
        elif vim_info.vimType == 'ETSINFV.HELM.V_3':
            driver = helm.Helm()
            driver.change_vnfpkg(req, inst, grant_req, grant, vnfd)
        elif vim_info.vimType == 'TERRAFORM.V1':
            driver = terraform.Terraform()
            driver.change_vnfpkg(req, inst, grant_req, grant, vnfd)
        else:
            # should not occur
            raise sol_ex.SolException(sol_detail='not support vim type')

        inst.vnfdId = grant_req.dstVnfdId
        self._modify_inst_vnfd_id(context, inst, vnfd)

        attrs = ['vnfConfigurableProperties', 'extensions']
        for attr in attrs:
            self._modify_from_req(inst, req, attr)

    def change_vnfpkg_rollback(
            self, context, lcmocc, inst, grant_req, grant, vnfd):
        vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
        req = lcmocc.operationParams
        if vim_info.vimType == 'ETSINFV.OPENSTACK_KEYSTONE.V_3':
            driver = openstack.Openstack()
            driver.change_vnfpkg_rollback(
                req, inst, grant_req, grant, vnfd, lcmocc)
        elif vim_info.vimType == 'ETSINFV.KUBERNETES.V_1':
            driver = kubernetes.Kubernetes()
            driver.change_vnfpkg_rollback(
                req, inst, grant_req, grant, vnfd)
        elif vim_info.vimType == 'ETSINFV.HELM.V_3':
            driver = helm.Helm()
            driver.change_vnfpkg_rollback(req, inst, grant_req, grant, vnfd)
        elif vim_info.vimType == 'TERRAFORM.V1':
            driver = terraform.Terraform()
            driver.change_vnfpkg_rollback(req, inst, grant_req, grant, vnfd)
        else:
            # should not occur
            raise sol_ex.SolException(sol_detail='not support vim type')

    def sync_db(self, context, vnf_inst, vim_info):
        # Database synchronization works only when
        # the vimType is ETSINFV.KUBERNETES.V_1 or ETSINFV.HELM.V_3
        if vim_info.vimType == 'ETSINFV.KUBERNETES.V_1':
            driver = kubernetes.Kubernetes()
            driver.sync_db(context, vnf_inst, vim_info)
        elif vim_info.vimType == 'ETSINFV.HELM.V_3':
            driver = helm.Helm()
            driver.sync_db(context, vnf_inst, vim_info)
        else:
            # Only support CNF
            raise sol_ex.DbSyncNoDiff(
                "There are no differences in Vnfc resources.")

    def diff_check_inst(self, vnf_inst, vim_info):
        if vim_info.vimType == 'ETSINFV.KUBERNETES.V_1':
            driver = kubernetes.Kubernetes()
            driver.diff_check_inst(vnf_inst, vim_info)
        elif vim_info.vimType == 'ETSINFV.HELM.V_3':
            driver = helm.Helm()
            driver.diff_check_inst(vnf_inst, vim_info)
        else:
            # Only support CNF
            raise sol_ex.DbSyncNoDiff(
                "There are no differences in Vnfc resources.")
