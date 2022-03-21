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


import copy
import json
import os
import pickle
import subprocess

from dateutil import parser
import eventlet
from oslo_log import log as logging
from oslo_utils import uuidutils
import yaml

from tacker.sol_refactored.common import cinder_utils
from tacker.sol_refactored.common import config
from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.common import vnf_instance_utils as inst_utils
from tacker.sol_refactored.infra_drivers.openstack import heat_utils
from tacker.sol_refactored.infra_drivers.openstack import userdata_default
from tacker.sol_refactored.nfvo import glance_utils
from tacker.sol_refactored import objects
from tacker.sol_refactored.objects.v2 import fields as v2fields


LOG = logging.getLogger(__name__)

CONF = config.CONF

LINK_PORT_PREFIX = 'req-'
CP_INFO_PREFIX = 'cp-'


# Id of the resources in instantiatedVnfInfo related methods.
# NOTE: instantiatedVnfInfo is re-created in each operation.
# Id of the resources in instantiatedVnfInfo is based on
# heat resource-id so that id is not changed at re-creation.
# Some ids are same as heat resource-id and some ids are
# combination of prefix and other ids.
def _make_link_port_id(link_port_id):
    # prepend 'req-' to distinguish from ports which are
    # created by heat.
    return '{}{}'.format(LINK_PORT_PREFIX, link_port_id)


def _is_link_port(link_port_id):
    return link_port_id.startswith(LINK_PORT_PREFIX)


def _make_cp_info_id(link_port_id):
    return '{}{}'.format(CP_INFO_PREFIX, link_port_id)


def _make_combination_id(a, b):
    return '{}-{}'.format(a, b)


class Openstack(object):

    def __init__(self):
        pass

    def instantiate(self, req, inst, grant_req, grant, vnfd):
        # make HOT
        fields = self._make_hot(req, inst, grant_req, grant, vnfd)
        LOG.debug("stack fields: %s", fields)

        # create or update stack
        vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
        heat_client = heat_utils.HeatClient(vim_info)
        stack_name = heat_utils.get_stack_name(inst)
        status, _ = heat_client.get_status(stack_name)
        if status is None:
            fields['stack_name'] = stack_name
            heat_client.create_stack(fields)
        else:
            heat_client.update_stack(stack_name, fields)

        # get stack resource
        heat_reses = heat_client.get_resources(stack_name)

        # make instantiated_vnf_info
        self._make_instantiated_vnf_info(req, inst, grant_req, grant, vnfd,
            heat_reses)

    def instantiate_rollback(self, req, inst, grant_req, grant, vnfd):
        vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
        heat_client = heat_utils.HeatClient(vim_info)
        stack_name = heat_utils.get_stack_name(inst)
        status, _ = heat_client.get_status(stack_name)
        if status is not None:
            heat_client.delete_stack(stack_name)

    def terminate(self, req, inst, grant_req, grant, vnfd):
        if req.terminationType == 'GRACEFUL':
            timeout = CONF.v2_vnfm.default_graceful_termination_timeout
            if req.obj_attr_is_set('gracefulTerminationTimeout'):
                timeout = req.gracefulTerminationTimeout
            eventlet.sleep(timeout)

        # delete stack
        vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
        heat_client = heat_utils.HeatClient(vim_info)
        stack_name = heat_utils.get_stack_name(inst)
        heat_client.delete_stack(stack_name)

    def _update_nfv_dict(self, heat_client, stack_name, fields):
        parameters = heat_client.get_parameters(stack_name)
        LOG.debug("ORIG parameters: %s", parameters)
        # NOTE: parameters['nfv'] is string
        orig_nfv_dict = json.loads(parameters.get('nfv', '{}'))
        if 'nfv' in fields['parameters']:
            fields['parameters']['nfv'] = inst_utils.json_merge_patch(
                orig_nfv_dict, fields['parameters']['nfv'])
        LOG.debug("NEW parameters: %s", fields['parameters'])
        return fields

    def scale(self, req, inst, grant_req, grant, vnfd):
        # make HOT
        fields = self._make_hot(req, inst, grant_req, grant, vnfd)
        LOG.debug("stack fields: %s", fields)

        vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
        heat_client = heat_utils.HeatClient(vim_info)

        # mark unhealthy to servers to be removed if scale in
        if req.type == 'SCALE_IN':
            vnfc_res_ids = [res_def.resource.resourceId
                            for res_def in grant_req.removeResources
                            if res_def.type == 'COMPUTE']
            for vnfc in inst.instantiatedVnfInfo.vnfcResourceInfo:
                if vnfc.computeResource.resourceId in vnfc_res_ids:
                    if 'parent_stack_id' not in vnfc.metadata:
                        # It means definition of VDU in the BaseHOT
                        # is inappropriate.
                        raise sol_ex.UnexpectedParentResourceDefinition()
                    heat_client.mark_unhealthy(
                        vnfc.metadata['parent_stack_id'],
                        vnfc.metadata['parent_resource_name'])

        # update stack
        stack_name = heat_utils.get_stack_name(inst)
        fields = self._update_nfv_dict(heat_client, stack_name, fields)
        heat_client.update_stack(stack_name, fields)

        # get stack resource
        heat_reses = heat_client.get_resources(stack_name)

        # make instantiated_vnf_info
        self._make_instantiated_vnf_info(req, inst, grant_req, grant, vnfd,
            heat_reses)

    def scale_rollback(self, req, inst, grant_req, grant, vnfd):
        # NOTE: rollback is supported for scale out only
        vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
        heat_client = heat_utils.HeatClient(vim_info)
        stack_name = heat_utils.get_stack_name(inst)
        heat_reses = heat_client.get_resources(stack_name)

        # mark unhealthy to added servers while scale out
        vnfc_ids = [vnfc.id
                    for vnfc in inst.instantiatedVnfInfo.vnfcResourceInfo]
        for res in heat_utils.get_server_reses(heat_reses):
            if res['physical_resource_id'] not in vnfc_ids:
                metadata = self._make_vnfc_metadata(res, heat_reses)
                if 'parent_stack_id' not in metadata:
                    # It means definition of VDU in the BaseHOT
                    # is inappropriate.
                    raise sol_ex.UnexpectedParentResourceDefinition()
                heat_client.mark_unhealthy(
                    metadata['parent_stack_id'],
                    metadata['parent_resource_name'])

        # update (put back) 'desired_capacity' parameter
        fields = self._update_nfv_dict(heat_client, stack_name,
            userdata_default.DefaultUserData.scale_rollback(
                req, inst, grant_req, grant, vnfd.csar_dir))

        heat_client.update_stack(stack_name, fields)

        # NOTE: instantiatedVnfInfo is not necessary to update since it
        # should be same as before scale API started.

    def change_ext_conn(self, req, inst, grant_req, grant, vnfd):
        # make HOT
        fields = self._make_hot(req, inst, grant_req, grant, vnfd)
        LOG.debug("stack fields: %s", fields)

        # update stack
        vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
        heat_client = heat_utils.HeatClient(vim_info)
        stack_name = heat_utils.get_stack_name(inst)
        fields = self._update_nfv_dict(heat_client, stack_name, fields)
        heat_client.update_stack(stack_name, fields)

        # get stack resource
        heat_reses = heat_client.get_resources(stack_name)

        # make instantiated_vnf_info
        self._make_instantiated_vnf_info(req, inst, grant_req, grant, vnfd,
            heat_reses)

    def change_ext_conn_rollback(self, req, inst, grant_req, grant, vnfd):
        vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
        heat_client = heat_utils.HeatClient(vim_info)
        stack_name = heat_utils.get_stack_name(inst)
        fields = self._update_nfv_dict(heat_client, stack_name,
            userdata_default.DefaultUserData.change_ext_conn_rollback(
                req, inst, grant_req, grant, vnfd.csar_dir))
        heat_client.update_stack(stack_name, fields)

        # NOTE: it is necessary to re-create instantiatedVnfInfo because
        # ports may be changed.
        heat_reses = heat_client.get_resources(stack_name)
        self._make_instantiated_vnf_info(req, inst, grant_req, grant, vnfd,
            heat_reses)

    def heal(self, req, inst, grant_req, grant, vnfd):
        # make HOT
        # NOTE: _make_hot() is called as other operations, but it returns
        # empty 'nfv' dict by default. Therefore _update_nfv_dict() returns
        # current heat parameters as is.
        fields = self._make_hot(req, inst, grant_req, grant, vnfd)
        LOG.debug("stack fields: %s", fields)

        vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
        heat_client = heat_utils.HeatClient(vim_info)
        stack_name = heat_utils.get_stack_name(inst)
        fields = self._update_nfv_dict(heat_client, stack_name, fields)

        # "re_create" is set to True only when SOL003 heal(without
        # vnfcInstanceId) and "all=True" in additionalParams.
        re_create = False
        if (req.obj_attr_is_set('additionalParams') and
                req.additionalParams.get('all', False) and
                not req.obj_attr_is_set('vnfcInstanceId')):
            re_create = True

        if re_create:
            # NOTE: DefaultUserData::heal() don't care about "template" and
            # "files". Get and set current "template" and "files".
            if "template" not in fields:
                fields["template"] = heat_client.get_template(stack_name)
            if "files" not in fields:
                fields["files"] = heat_client.get_files(stack_name)
            fields["stack_name"] = stack_name

            # stack delete and create
            heat_client.delete_stack(stack_name)
            heat_client.create_stack(fields)
        else:
            # mark unhealthy to target resources.
            # As the target resources has been already selected in
            # constructing grant_req, use it here.
            inst_info = inst.instantiatedVnfInfo

            vnfc_res_ids = [res_def.resource.resourceId
                            for res_def in grant_req.removeResources
                            if res_def.type == 'COMPUTE']
            for vnfc in inst_info.vnfcResourceInfo:
                if vnfc.computeResource.resourceId in vnfc_res_ids:
                    heat_client.mark_unhealthy(
                        vnfc.metadata['stack_id'], vnfc.vduId)

            storage_ids = [res_def.resource.resourceId
                           for res_def in grant_req.removeResources
                           if res_def.type == 'STORAGE']
            if storage_ids:
                for storage_info in inst_info.virtualStorageResourceInfo:
                    if storage_info.storageResource.resourceId in storage_ids:
                        heat_client.mark_unhealthy(
                            storage_info.metadata['stack_id'],
                            storage_info.virtualStorageDescId)

            # update stack
            heat_client.update_stack(stack_name, fields)

        # get stack resource
        heat_reses = heat_client.get_resources(stack_name)

        # make instantiated_vnf_info
        self._make_instantiated_vnf_info(req, inst, grant_req, grant, vnfd,
            heat_reses)

    def change_vnfpkg(self, req, inst, grant_req, grant, vnfd):
        group_vdu_ids = []
        if req.additionalParams.get('upgrade_type') == 'RollingUpdate':
            vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
            heat_client = heat_utils.HeatClient(vim_info)
            stack_name = heat_utils.get_stack_name(inst)
            stack_id = heat_client.get_stack_resource(
                stack_name)['stack']["id"]
            vdu_infos = self._get_vdu_info(vnfd, grant, inst)
            new_res_ids = {}
            for vdu_param in req.additionalParams.get('vdu_params'):
                vdu_id = vdu_param.get('vdu_id')
                new_res_ids[vdu_id] = []
                body = heat_client.get_resource_info(
                    f"{stack_name}/{stack_id}", vdu_id)
                if uuidutils.is_uuid_like(
                        vdu_infos[vdu_id]['image']):
                    vdu_image_id_flag = True
                else:
                    vdu_image_id_flag = False
                # The previous processing is to obtain the VM information under
                # the current stack according to vduId, excluding the resources
                # under nested. When the status_code is 404, it means that
                # there is no VM under the stack, and the VM is created by
                # `OS::Heat::AutoScalingGroup` by default.
                if body is None:
                    # handle VM under `OS::Heat::AutoScalingGroup`
                    # In this case, the VM does not support changing from
                    # image creation to volume creation, or changing from
                    # volume creation to image creation. Because it cannot
                    # change VDU.yaml under nested directory.
                    heat_reses = heat_client.get_resources(stack_name)
                    group_stack_id = heat_utils.get_group_stack_id(
                        heat_reses, vdu_id)
                    templates = heat_client.get_template(
                        group_stack_id)
                    reses = heat_client.get_resource_list(
                        group_stack_id)['resources']

                    # update VM one by one
                    for res in reses:
                        templates['resources'][res.get('resource_name')][
                            'properties']['image'] = vdu_infos[
                            vdu_id].get('image')
                        templates['resources'][res.get('resource_name')][
                            'properties']['flavor'] = vdu_infos[
                            vdu_id].get('flavor')
                        fields = {
                            "stack_id": group_stack_id,
                            "template": templates
                        }
                        try:
                            heat_client.update_stack(
                                group_stack_id, fields)
                        except sol_ex.StackOperationFailed:
                            self._handle_exception(
                                res, new_res_ids, vdu_infos,
                                vdu_id, heat_client, req, inst, vnfd,
                                stack_name, get_res_flag=True)
                        self._get_new_res_info(
                            res.get('resource_name'),
                            new_res_ids[vdu_id],
                            heat_utils.get_parent_nested_id(res),
                            vdu_infos[vdu_id], vdu_id,
                            heat_client)

                        # execute coordinate_vnf_script
                        try:
                            self._execute_coordinate_vnf_script(
                                req, inst, grant_req, grant, vnfd,
                                heat_utils.get_parent_nested_id(res),
                                heat_client, vdu_param, vim_info,
                                vdu_image_id_flag)
                        except (sol_ex.SshIpNotFoundException,
                                sol_ex.CoordinateVNFExecutionFailed) as ex:
                            self._handle_exception(
                                res, new_res_ids, vdu_infos,
                                vdu_id, heat_client, req, inst, vnfd,
                                stack_name, ex=ex)
                    group_vdu_ids.append(vdu_id)
                else:
                    # handle single VM
                    res = {
                        "resource_name": stack_name,
                        "physical_resource_id": stack_id,
                    }
                    new_template = vnfd.get_base_hot(
                        inst.instantiatedVnfInfo.flavourId)['template']
                    heat_parameter = self._update_vnf_template_and_parameter(
                        stack_id, vdu_infos, vdu_id, heat_client, new_template)
                    fields = {
                        "stack_id": stack_id,
                        "parameters": {"nfv": heat_parameter.get('nfv')},
                        "template": yaml.safe_dump(
                            heat_parameter.get('templates')),
                    }
                    try:
                        heat_client.update_stack(stack_id, fields, wait=True)
                    except sol_ex.StackOperationFailed:
                        self._handle_exception(
                            res, new_res_ids, vdu_infos,
                            vdu_id, heat_client, req, inst, vnfd,
                            stack_name, get_res_flag=True)
                    self._get_new_res_info(
                        stack_name,
                        new_res_ids[vdu_id],
                        f'{stack_name}/{stack_id}',
                        vdu_infos[vdu_id], vdu_id,
                        heat_client)

                    # execute coordinate_vnf_script
                    try:
                        self._execute_coordinate_vnf_script(
                            req, inst, grant_req, grant, vnfd,
                            f"{stack_name}/{stack_id}",
                            heat_client, vdu_param, vim_info,
                            vdu_image_id_flag,
                            operation='change_vnfpkg')
                    except (sol_ex.SshIpNotFoundException,
                            sol_ex.CoordinateVNFExecutionFailed) as ex:
                        self._handle_exception(
                            res, new_res_ids, vdu_infos,
                            vdu_id, heat_client, req, inst, vnfd,
                            stack_name, ex=ex)

            # Because external parameters are not updated after the image
            # of the nested-VM is updated, scale will create the original
            # VM again, so the overall update needs to be performed
            # at the end.
            fields = self._get_entire_stack_fields(
                heat_client, stack_id, group_vdu_ids, vdu_infos)
            try:
                heat_client.update_stack(stack_id, fields)
            except sol_ex.StackOperationFailed:
                self._handle_exception(
                    res, new_res_ids, vdu_infos,
                    vdu_id, heat_client, req, inst, vnfd,
                    stack_name)
            self._update_vnf_instantiated_info(
                req, new_res_ids, inst, vnfd,
                heat_client, stack_name)
            inst.vnfdId = req.vnfdId
        else:
            # TODO(YiFeng): Blue-Green type will be supported in Zed release.
            raise sol_ex.NotSupportUpgradeType(
                upgrade_type=req.additionalParams.get('upgrade_type'))

    def change_vnfpkg_rollback(
            self, req, inst, grant_req, grant, vnfd, lcmocc):
        group_vdu_ids = []
        if req.additionalParams.get('upgrade_type') == 'RollingUpdate':
            vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
            heat_client = heat_utils.HeatClient(vim_info)
            stack_name = heat_utils.get_stack_name(inst)
            stack_id = heat_client.get_stack_resource(
                stack_name)['stack']["id"]
            vdu_infos = self._get_vdu_info(vnfd, grant, inst)
            new_res_ids = {}
            templates = {}
            affected_vnfcs = [affected_vnfc for affected_vnfc in
                             lcmocc.resourceChanges.affectedVnfcs if
                             affected_vnfc.changeType in {'ADDED', 'MODIFIED'}]
            for lcmocc_vnf in affected_vnfcs:
                if new_res_ids.get(lcmocc_vnf.vduId) is None:
                    new_res_ids[lcmocc_vnf.vduId] = []
                image = vdu_infos[lcmocc_vnf.vduId]['image']
                if uuidutils.is_uuid_like(image):
                    vdu_image_id_flag = True
                else:
                    vdu_image_id_flag = False
                if lcmocc_vnf.metadata.get(
                        'current_vnfd_id') is not inst.vnfdId:
                    parent_resource_name = lcmocc_vnf.metadata.get(
                        'parent_resource_name')
                    if parent_resource_name:
                        vdu_stack_id = lcmocc_vnf.metadata.get(
                            'stack_id')
                        if not templates.get(lcmocc_vnf.vduId):
                            templates[lcmocc_vnf.vduId] = {}
                            heat_reses = heat_client.get_resources(stack_name)
                            group_stack_id = heat_utils.get_group_stack_id(
                                heat_reses, lcmocc_vnf.vduId)
                            template = heat_client.get_template(
                                group_stack_id)
                            templates[lcmocc_vnf.vduId] = template
                        template['resources'][parent_resource_name][
                            'properties']['image'] = vdu_infos[
                            lcmocc_vnf.vduId].get('image')
                        template['resources'][parent_resource_name][
                            'properties']['flavor'] = vdu_infos[
                            lcmocc_vnf.vduId].get('flavor')
                        fields = {
                            "stack_id": group_stack_id,
                            "template": template
                        }
                        heat_client.update_stack(
                            group_stack_id, fields, wait=True)
                        self._get_new_res_info(
                            parent_resource_name,
                            new_res_ids[lcmocc_vnf.vduId], vdu_stack_id,
                            vdu_infos[lcmocc_vnf.vduId],
                            lcmocc_vnf.vduId, heat_client)
                        vdu_param = [vdu_param for vdu_param in
                                     req.get('additionalParams').get(
                                         'vdu_params')
                                     if vdu_param.get('vdu_id')
                                     == lcmocc_vnf.vduId][0]
                        self._execute_coordinate_vnf_script(
                            req, inst, grant_req, grant, vnfd,
                            vdu_stack_id,
                            heat_client, vdu_param, vim_info,
                            vdu_image_id_flag,
                            operation="change_vnfpkg_rollback")
                        group_vdu_ids.append(lcmocc_vnf.vduId)
                    else:
                        vdu_stack_id = lcmocc_vnf.metadata.get('stack_id')
                        new_template = vnfd.get_base_hot(
                            inst.instantiatedVnfInfo.flavourId)['template']
                        heat_parameter = (
                            self._update_vnf_template_and_parameter(
                                stack_id, vdu_infos,
                                lcmocc_vnf.vduId, heat_client, new_template))
                        fields = {
                            "stack_id": stack_id,
                            "parameters": {"nfv": heat_parameter.get('nfv')},
                            "template": yaml.safe_dump(
                                heat_parameter.get('templates')),
                        }
                        heat_client.update_stack(stack_id,
                                                 fields, wait=True)
                        self._get_new_res_info(
                            stack_name, new_res_ids[lcmocc_vnf.vduId],
                            vdu_stack_id, vdu_infos[lcmocc_vnf.vduId],
                            lcmocc_vnf.vduId, heat_client)
                        vdu_param = [vdu_param for vdu_param in
                                     req.get('additionalParams').get(
                                         'vdu_params')
                                     if vdu_param.get('vdu_id')
                                     == lcmocc_vnf.vduId][0]
                        self._execute_coordinate_vnf_script(
                            req, inst, grant_req, grant, vnfd, vdu_stack_id,
                            heat_client, vdu_param, vim_info,
                            vdu_image_id_flag,
                            operation="change_vnfpkg_rollback")
            fields = self._get_entire_stack_fields(
                heat_client, stack_id, group_vdu_ids, vdu_infos)
            heat_client.update_stack(stack_id, fields, wait=True)
            self._update_vnf_instantiated_info(
                req, new_res_ids, inst, vnfd,
                heat_client, stack_name, operation='change_vnfpkg_rollback')
        else:
            # TODO(YiFeng): Blue-Green type will be supported in Zed release.
            raise sol_ex.NotSupportUpgradeType(
                upgrade_type=req.additionalParams.get('upgrade_type'))

    def _make_hot(self, req, inst, grant_req, grant, vnfd):
        if grant_req.operation == v2fields.LcmOperationType.INSTANTIATE:
            flavour_id = req.flavourId
        else:
            flavour_id = inst.instantiatedVnfInfo.flavourId

        hot_dict = vnfd.get_base_hot(flavour_id)
        if not hot_dict:
            raise sol_ex.BaseHOTNotDefined()

        userdata = None
        userdata_class = None
        if req.obj_attr_is_set('additionalParams'):
            userdata = req.additionalParams.get('lcm-operation-user-data')
            userdata_class = req.additionalParams.get(
                'lcm-operation-user-data-class')

        if userdata is None and userdata_class is None:
            LOG.debug("Processing default userdata %s", grant_req.operation)
            # NOTE: objects used here are dict compat.
            method = getattr(userdata_default.DefaultUserData,
                             grant_req.operation.lower())
            fields = method(req, inst, grant_req, grant, vnfd.csar_dir)
        elif userdata is None or userdata_class is None:
            # Both must be specified.
            raise sol_ex.UserdataMissing()
        else:
            LOG.debug("Processing %s %s %s", userdata, userdata_class,
                grant_req.operation)

            tmp_csar_dir = vnfd.make_tmp_csar_dir()
            script_dict = {
                'request': req.to_dict(),
                'vnf_instance': inst.to_dict(),
                'grant_request': grant_req.to_dict(),
                'grant_response': grant.to_dict(),
                'tmp_csar_dir': tmp_csar_dir
            }
            script_path = os.path.join(
                os.path.dirname(__file__), "userdata_main.py")

            out = subprocess.run(["python3", script_path],
                input=pickle.dumps(script_dict),
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            vnfd.remove_tmp_csar_dir(tmp_csar_dir)

            if out.returncode != 0:
                LOG.debug("execute userdata class instantiate failed: %s",
                    out.stderr)
                raise sol_ex.UserdataExecutionFailed(
                    sol_detail=str(out.stderr))

            fields = pickle.loads(out.stdout)

        fields['timeout_mins'] = (
            CONF.v2_vnfm.openstack_vim_stack_create_timeout)

        return fields

    def _get_checked_reses(self, nodes, reses):
        names = list(nodes.keys())

        def _check_res_in_vnfd(res):
            if res['resource_name'] in names:
                return True
            else:
                # should not occur. just check for consistency.
                LOG.debug("%s not in VNFD definition.", res['resource_name'])
                return False

        return {res['physical_resource_id']: res
                for res in reses if _check_res_in_vnfd(res)}

    def _address_range_data_to_info(self, range_data):
        obj = objects.ipOverEthernetAddressInfoV2_IpAddresses_AddressRange()
        obj.minAddress = range_data.minAddress
        obj.maxAddress = range_data.maxAddress
        return obj

    def _execute_coordinate_vnf_script(
            self, req, inst, grant_req, grant,
            vnfd, nested_stack_id, heat_client, vdu_param,
            vim_info, vdu_image_id_flag, operation='change_vnfpkg'):
        coordinate_vnf = None
        coordinate_vnf_class = None
        if req.obj_attr_is_set('additionalParams'):
            if operation == 'change_vnfpkg':
                coordinate_vnf = req.additionalParams.get(
                    'lcm-operation-coordinate-new-vnf')
                coordinate_vnf_class = req.additionalParams.get(
                    'lcm-operation-coordinate-new-vnf-class')
            else:
                coordinate_vnf = req.additionalParams.get(
                    'lcm-operation-coordinate-old-vnf')
                coordinate_vnf_class = req.additionalParams.get(
                    'lcm-operation-coordinate-old-vnf-class')

        if coordinate_vnf and coordinate_vnf_class:
            if operation == 'change_vnfpkg':
                ssh_ip = self._get_ssh_ip(nested_stack_id,
                    vdu_param.get('new_vnfc_param'),
                    heat_client)
            else:
                ssh_ip = self._get_ssh_ip(nested_stack_id,
                    vdu_param.get('old_vnfc_param'),
                    heat_client)
            if not ssh_ip:
                raise sol_ex.SshIpNotFoundException
            image, flavor = self._get_current_vdu_image_and_flavor(
                nested_stack_id, vdu_param.get('vdu_id'),
                heat_client, vim_info, vdu_image_id_flag)
            tmp_csar_dir = vnfd.make_tmp_csar_dir()
            script_dict = {
                "request": req.to_dict(),
                "vnf_instance": inst.to_dict(),
                "grant_request": grant_req.to_dict(),
                "grant_response": grant.to_dict(),
                "tmp_csar_dir": tmp_csar_dir,
                "vdu_info": {
                    "ssh_ip": ssh_ip,
                    "new_image": image,
                    "new_flavor": flavor,
                    "vdu_param": vdu_param
                }
            }
            script_path = os.path.join(tmp_csar_dir, coordinate_vnf)
            out = subprocess.run(["python3", script_path],
                input=pickle.dumps(script_dict),
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if out.returncode != 0:
                LOG.error(out)
                raise sol_ex.CoordinateVNFExecutionFailed

    def _proto_data_to_info(self, proto_data):
        # make CpProtocolInfo (5.5.3.9b) from CpProtocolData (4.4.1.10b)
        proto_info = objects.CpProtocolInfoV2(
            layerProtocol=proto_data.layerProtocol
        )
        ip_info = objects.IpOverEthernetAddressInfoV2()

        ip_data = proto_data.ipOverEthernet
        if ip_data.obj_attr_is_set('macAddress'):
            ip_info.macAddress = ip_data.macAddress
        if ip_data.obj_attr_is_set('segmentationId'):
            ip_info.segmentationId = ip_data.segmentationId
        if ip_data.obj_attr_is_set('ipAddresses'):
            addr_infos = []
            for addr_data in ip_data.ipAddresses:
                addr_info = objects.IpOverEthernetAddressInfoV2_IpAddresses(
                    type=addr_data.type)
                if addr_data.obj_attr_is_set('fixedAddresses'):
                    addr_info.addresses = addr_data.fixedAddresses
                if addr_data.obj_attr_is_set('numDynamicAddresses'):
                    addr_info.isDynamic = True
                if addr_data.obj_attr_is_set('addressRange'):
                    addr_info.addressRange = self._address_range_data_to_info(
                        addr_data.addressRange)
                if addr_data.obj_attr_is_set('subnetId'):
                    addr_info.subnetId = addr_data.subnetId
                addr_infos.append(addr_info)
            ip_info.ipAddresses = addr_infos

        proto_info.ipOverEthernet = ip_info

        return proto_info

    def _make_link_ports(self, req_ext_vl, ext_cp_infos):
        link_ports = []
        if not req_ext_vl.obj_attr_is_set('extLinkPorts'):
            return link_ports

        for req_link_port in req_ext_vl.extLinkPorts:
            link_port = objects.ExtLinkPortInfoV2(
                id=_make_link_port_id(req_link_port.id),
                resourceHandle=req_link_port.resourceHandle,
            )
            ext_cp_info = objects.VnfExtCpInfoV2(
                id=_make_cp_info_id(link_port.id),
                extLinkPortId=link_port.id
                # associatedVnfcCpId may set later
            )
            link_port.cpInstanceId = ext_cp_info.id

            for ext_cp in req_ext_vl.extCps:
                found = False
                for key, cp_conf in ext_cp.cpConfig.items():
                    if (cp_conf.obj_attr_is_set('linkPortId') and
                            cp_conf.linkPortId == req_link_port.id):
                        ext_cp_info.cpdId = ext_cp.cpdId
                        ext_cp_info.cpConfigId = key
                        # NOTE: cpProtocolInfo can't be filled
                        found = True
                        break
                if found:
                    break

            link_ports.append(link_port)
            ext_cp_infos.append(ext_cp_info)

        return link_ports

    def _make_ext_vl_from_req(self, req_ext_vl, ext_cp_infos):
        ext_vl = objects.ExtVirtualLinkInfoV2(
            id=req_ext_vl.id,
            resourceHandle=objects.ResourceHandle(
                resourceId=req_ext_vl.resourceId
            ),
            currentVnfExtCpData=req_ext_vl.extCps
        )
        if req_ext_vl.obj_attr_is_set('vimConnectionId'):
            ext_vl.resourceHandle.vimConnectionId = (
                req_ext_vl.vimConnectionId)
        if req_ext_vl.obj_attr_is_set('resourceProviderId'):
            ext_vl.resourceHandle.resourceProviderId = (
                req_ext_vl.resourceProviderId)

        link_ports = self._make_link_ports(req_ext_vl, ext_cp_infos)
        if link_ports:
            ext_vl.extLinkPorts = link_ports

        ext_vl.extLinkPorts = link_ports

        return ext_vl

    def _get_vdu_info(self, vnfd, grant, inst):
        flavour_id = inst.instantiatedVnfInfo.flavourId
        vdu_nodes = vnfd.get_vdu_nodes(flavour_id)
        storage_nodes = vnfd.get_storage_nodes(flavour_id)
        vdu_info_dict = {}
        for name, node in vdu_nodes.items():
            flavor = self._get_param_flavor(vnfd, name, flavour_id, grant)
            image = self._get_param_image(vnfd, name, flavour_id, grant)
            vdu_storage_names = vnfd.get_vdu_storages(node)
            volume_name = ''
            volume_size = ''
            for vdu_storage_name in vdu_storage_names:
                if storage_nodes[vdu_storage_name].get(
                        'properties').get('sw_image_data'):
                    image = self._get_param_image(
                        vnfd, vdu_storage_name, flavour_id, grant)
                    volume_name = vdu_storage_name
                    volume_size = storage_nodes[vdu_storage_name].get(
                        'properties', {}).get(
                        'virtual_block_storage_data', '').get(
                        'size_of_storage', ''
                    )
                    volume_size = volume_size.rstrip(' GB')
                    if not volume_size.isdigit():
                        raise sol_ex.InvalidVolumeSize
                    break

            vdu_info_dict[name] = {
                "flavor": flavor,
                "image": image
            }

            if volume_name:
                vdu_info_dict[name]['volume_info'] = {
                    "volume_name": volume_name,
                    "volume_size": volume_size
                }
        return vdu_info_dict

    def _get_param_flavor(self, vnfd, vdu_name, flavour_id, grant):
        # try to get from grant
        if grant.obj_attr_is_set('vimAssets'):
            assets = grant.vimAssets
            if assets.obj_attr_is_set('computeResourceFlavours'):
                flavours = assets.computeResourceFlavours
                for flavour in flavours:
                    if flavour.vnfdVirtualComputeDescId == vdu_name:
                        return flavour.vimFlavourId
        # if specified in VNFD, use it
        # NOTE: if not found. parameter is set to None.
        #       may be error when stack create
        return vnfd.get_compute_flavor(flavour_id, vdu_name)

    def _get_param_image(self, vnfd, vdu_name, flavour_id, grant):
        # try to get from grant
        if grant.obj_attr_is_set('vimAssets'):
            assets = grant.vimAssets
            if assets.obj_attr_is_set('softwareImages'):
                images = assets.softwareImages
                for image in images:
                    if image.vnfdSoftwareImageId == vdu_name:
                        return image.vimSoftwareImageId

        # if specified in VNFD, use it
        # NOTE: if not found. parameter is set to None.
        #       may be error when stack create
        sw_images = vnfd.get_sw_image(flavour_id)
        for name, image in sw_images.items():
            if name == vdu_name:
                return image

        return None

    def _get_current_vdu_image_and_flavor(
            self, nested_stack_id, resource_name,
            heat_client, vim_info, vdu_image_id_flag):
        vdu_info = heat_client.get_resource_info(
            nested_stack_id, resource_name)
        if vdu_info.get('attributes').get('image'):
            image = vdu_info.get('attributes').get('image').get('id')
            if not vdu_image_id_flag:
                glance_client = glance_utils.GlanceClient(vim_info)
                image = glance_client.get_image(image).name

        else:
            volume_ids = [volume.get('id') for volume in vdu_info.get(
                'attributes').get('os-extended-volumes:volumes_attached')]
            cinder_client = cinder_utils.CinderClient(vim_info)
            if vdu_image_id_flag:
                image = [cinder_client.get_volume(
                    volume_id).volume_image_metadata.get('image_id')
                    for volume_id in volume_ids if cinder_client.get_volume(
                    volume_id).volume_image_metadata][0]
            else:
                image = [cinder_client.get_volume(
                    volume_id).volume_image_metadata.get('image_name')
                    for volume_id in volume_ids if cinder_client.get_volume(
                    volume_id).volume_image_metadata][0]
        flavor_name = vdu_info.get('attributes').get('flavor').get(
            'original_name')

        return image, flavor_name

    def _get_new_res_info(self, parent_resource_name, vdu_infos,
                          stack_id, vnfd_info, vdu_id, heat_client):
        new_res_infos = {
            "stack_id": stack_id,
            "parent_resource_name": parent_resource_name
        }
        nested_reses = heat_client.get_resource_list(
            stack_id.split('/')[1])['resources']
        for nested_res in nested_reses:
            if nested_res.get(
                    'resource_type') == 'OS::Nova::Server' and nested_res.get(
                    'resource_name') == vdu_id:
                new_res_infos["vdu_id"] = nested_res.get(
                    'physical_resource_id')
            elif nested_res.get(
                    'resource_type'
            ) == 'OS::Cinder::Volume' and nested_res.get(
                    'resource_name') == vnfd_info.get(
                    'volume_info').get('volume_name'):
                new_res_infos['volume_info'] = {
                    "volume_name": nested_res.get('resource_name'),
                    "volume_id": nested_res.get('physical_resource_id')
                }
        vdu_infos.append(new_res_infos)

    def _get_ssh_ip(self, nested_stack_id, vnfc_param, heat_client):
        cp_name = vnfc_param.get('cp_name')
        cp_info = heat_client.get_resource_info(nested_stack_id, cp_name)
        if cp_info.get('attributes').get('floating_ip_address'):
            ssh_ip = cp_info.get('attributes').get('floating_ip_address')
        else:
            ssh_ip = cp_info.get('attributes').get('fixed_ips')[0].get(
                'ip_address')
        return ssh_ip

    def _update_vnf_instantiated_info(
            self, req, new_res_ids, inst, vnfd, heat_client, stack_name,
            operation='change_vnfpkg'):
        instantiated_vnf_info = inst.instantiatedVnfInfo
        vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
        heat_reses = heat_client.get_resources(stack_name)
        storage_reses = self._get_checked_reses(
            vnfd.get_storage_nodes(inst.instantiatedVnfInfo.flavourId),
            heat_utils.get_storage_reses(heat_reses))

        # handle storage_info
        def _res_to_handle(res):
            return objects.ResourceHandle(
                resourceId=res['physical_resource_id'],
                vimLevelResourceType=res['resource_type'],
                vimConnectionId=vim_info.vimId)

        storage_infos = [
            objects.VirtualStorageResourceInfoV2(
                id=res_id,
                virtualStorageDescId=res['resource_name'],
                storageResource=_res_to_handle(res)
            )
            for res_id, res in storage_reses.items()
        ]

        # handle vnfc_resource_info
        for vnfc_res in instantiated_vnf_info.vnfcResourceInfo:
            if new_res_ids.get(vnfc_res.vduId):
                new_res_info = [vnfc_info for vnfc_info
                                in new_res_ids.get(vnfc_res.vduId)
                                if vnfc_info['stack_id']
                                == vnfc_res.metadata['stack_id']]
                if not new_res_info:
                    continue
                new_res_info = new_res_info[0]
                current_vnfc = []
                if instantiated_vnf_info.obj_attr_is_set('vnfcInfo'):
                    current_vnfc = [
                        vnfc for vnfc in instantiated_vnf_info.vnfcInfo
                        if vnfc.id == _make_combination_id(
                            vnfc_res.vduId, vnfc_res.id)][0]
                vnfc_res.id = new_res_info.get('vdu_id')
                vnfc_res.computeResource.resourceId = new_res_info.get(
                    'vdu_id')
                if current_vnfc:
                    current_vnfc.id = _make_combination_id(
                        vnfc_res.vduId, vnfc_res.id)
                    current_vnfc.vnfcResourceInfoId = vnfc_res.id
                if operation == 'change_vnfpkg':
                    vnfc_res.metadata['current_vnfd_id'] = req.vnfdId
                else:
                    vnfc_res.metadata['current_vnfd_id'] = inst.vnfdId
                storage_ids = [
                    storage_id for storage_id, storage_res in
                    storage_reses.items()
                    if (vnfc_res.vduId in storage_res.get(
                        'required_by', []))]
                if vnfc_res.metadata.get('parent_resource_name') != stack_name:
                    storage_ids = [
                        storage_id for storage_id, storage_res in
                        storage_reses.items()
                        if (vnfc_res.vduId in storage_res.get(
                            'required_by', []) and vnfc_res.metadata.get(
                            'parent_resource_name') == storage_res.get(
                            'parent_resource'))]
                if storage_ids:
                    vnfc_res.storageResourceIds = storage_ids
                else:
                    if vnfc_res.obj_attr_is_set('storageResourceIds'):
                        del vnfc_res.storageResourceIds

        if storage_infos:
            instantiated_vnf_info.virtualStorageResourceInfo = storage_infos
        else:
            if instantiated_vnf_info.obj_attr_is_set(
                    'virtualStorageResourceInfo'):
                del instantiated_vnf_info.virtualStorageResourceInfo

    def _update_vnf_template_and_parameter(
            self, stack_id, vdu_infos, vdu_id, heat_client, new_template):
        vdu_info = vdu_infos[vdu_id]
        volume_info = vdu_info.get('volume_info', {})
        base_templates = heat_client.get_template(stack_id)
        old_parameter = heat_client.get_parameters(stack_id)['nfv']
        new_parameter = json.loads(copy.deepcopy(old_parameter))

        # old VM(created by volume) -> new VM(created by volume)
        if volume_info and 'image' not in base_templates[
                'resources'][vdu_id]['properties']:
            new_parameter['VDU'][vdu_id]['computeFlavourId'] = vdu_info.get(
                'flavor')
            new_parameter['VDU'][volume_info.get('volume_name')][
                'vcImageId'] = vdu_info.get('image')

        # old VM(created by volume) -> new VM(created by image)
        elif vdu_info.get(
                'volume_info') is None and 'image' not in base_templates[
                'resources'][vdu_id]['properties']:
            # delete vdu's volume definition info
            if len(base_templates['resources'][vdu_id]['properties'][
                    'block_device_mapping_v2']) > 1:
                old_volumes = [name for name, value in
                               base_templates['resources'].items()
                               if value['type'] == 'OS::Cinder::Volume'
                               and value['properties']['image']]
                for volume in base_templates['resources'][
                        vdu_id]['properties']['block_device_mapping_v2']:
                    if volume['volume_id']['get_resource'] in old_volumes:
                        target_volume_name = volume['volume_id'][
                            'get_resource']
            else:
                target_volume_name = base_templates['resources'][
                    vdu_id]['properties']['block_device_mapping_v2'][0][
                    'volume_id']['get_resource']
            del new_parameter['VDU'][target_volume_name]
            new_parameter['VDU'][vdu_id]['computeFlavourId'] = vdu_info.get(
                'flavor')
            new_parameter['VDU'][vdu_id]['vcImageId'] = vdu_info.get('image')

        # old VM(created by image) -> new VM(created by volume)
        elif volume_info and 'image' in base_templates[
                'resources'][vdu_id]['properties']:
            del new_parameter['VDU'][vdu_id]['vcImageId']
            new_parameter['VDU'][vdu_id]['computeFlavourId'] = vdu_info.get(
                'flavor')
            new_parameter['VDU'][volume_info.get('volume_name')] = {
                "vcImageId": vdu_infos[vdu_id].get('image')
            }
        # old VM(created by image) -> new VM(created by image)
        else:
            new_parameter['VDU'][vdu_id]['computeFlavourId'] = vdu_info.get(
                'flavor')
            new_parameter['VDU'][vdu_id]['vcImageId'] = vdu_info.get('image')

        heat_parameter = {
            "templates": new_template,
            "nfv": new_parameter
        }
        return heat_parameter

    def _make_ext_vl_info_from_req(self, req, grant, ext_cp_infos):
        # make extVirtualLinkInfo
        req_ext_vls = []
        if grant.obj_attr_is_set('extVirtualLinks'):
            req_ext_vls = grant.extVirtualLinks
        elif req.obj_attr_is_set('extVirtualLinks'):
            req_ext_vls = req.extVirtualLinks

        return [self._make_ext_vl_from_req(req_ext_vl, ext_cp_infos)
                for req_ext_vl in req_ext_vls]

    def _find_ext_cp_info(self, link_port, ext_cp_infos):
        for ext_cp in ext_cp_infos:
            if ext_cp.id == link_port.cpInstanceId:
                return ext_cp
        # never reach here

    def _make_ext_vl_info_from_inst(self, old_inst_vnf_info, ext_cp_infos):
        # make extVirtualLinkInfo from old inst.extVirtualLinkInfo
        ext_vls = []
        old_cp_infos = []

        if old_inst_vnf_info.obj_attr_is_set('extVirtualLinkInfo'):
            ext_vls = old_inst_vnf_info.extVirtualLinkInfo
        if old_inst_vnf_info.obj_attr_is_set('extCpInfo'):
            old_cp_infos = old_inst_vnf_info.extCpInfo

        for ext_vl in ext_vls:
            if not ext_vl.obj_attr_is_set('extLinkPorts'):
                continue
            new_link_ports = []
            for link_port in ext_vl.extLinkPorts:
                if _is_link_port(link_port.id):
                    new_link_ports.append(link_port)
                    ext_cp_infos.append(self._find_ext_cp_info(link_port,
                                                               old_cp_infos))
            ext_vl.extLinkPorts = new_link_ports

        return ext_vls

    def _make_ext_vl_info_from_req_and_inst(self, req, grant, old_inst_info,
            ext_cp_infos):
        req_ext_vls = []
        if grant.obj_attr_is_set('extVirtualLinks'):
            req_ext_vls = grant.extVirtualLinks
        elif req.obj_attr_is_set('extVirtualLinks'):
            req_ext_vls = req.extVirtualLinks

        req_ext_vl_ids = {ext_vl.id for ext_vl in req_ext_vls}
        inst_ext_vl_ids = set()
        if old_inst_info.obj_attr_is_set('extVirtualLinkInfo'):
            inst_ext_vl_ids = {ext_vl.id
                               for ext_vl in old_inst_info.extVirtualLinkInfo}

        added_ext_vl_ids = req_ext_vl_ids - inst_ext_vl_ids
        req_all_cp_names = {ext_cp.cpdId
                            for req_ext_vl in req_ext_vls
                            for ext_cp in req_ext_vl.extCps}

        ext_vls = [self._make_ext_vl_from_req(req_ext_vl, ext_cp_infos)
                   for req_ext_vl in req_ext_vls
                   # added ext_vls
                   if req_ext_vl.id in added_ext_vl_ids]

        old_ext_vls = []
        old_cp_infos = []
        if old_inst_info.obj_attr_is_set('extVirtualLinkInfo'):
            old_ext_vls = old_inst_info.extVirtualLinkInfo
        if old_inst_info.obj_attr_is_set('extCpInfo'):
            old_cp_infos = old_inst_info.extCpInfo

        for ext_vl in old_ext_vls:
            old_ext_cp_data = ext_vl.currentVnfExtCpData
            old_link_ports = (ext_vl.extLinkPorts
                if ext_vl.obj_attr_is_set('extLinkPorts') else [])
            new_ext_cp_data = []
            new_link_ports = []

            for ext_cp_data in old_ext_cp_data:
                if ext_cp_data.cpdId not in req_all_cp_names:
                    new_ext_cp_data.append(ext_cp_data)

            for link_port in old_link_ports:
                ext_cp = self._find_ext_cp_info(link_port, old_cp_infos)
                if (ext_cp.cpdId not in req_all_cp_names and
                        _is_link_port(link_port.id)):
                    new_link_ports.append(link_port)
                    ext_cp_infos.append(ext_cp)

            def _find_req_ext_vl(ext_vl):
                for req_ext_vl in req_ext_vls:
                    if req_ext_vl.id == ext_vl.id:
                        return req_ext_vl

            req_ext_vl = _find_req_ext_vl(ext_vl)
            if req_ext_vl is not None:
                new_ext_cp_data += req_ext_vl.extCps
                new_link_ports += self._make_link_ports(req_ext_vl,
                                                        ext_cp_infos)

            if new_ext_cp_data:
                # if it is empty, it means all cps of this ext_vl are replaced
                # by another ext_vl.
                ext_vl.currentVnfExtCpData = new_ext_cp_data
                ext_vl.extLinkPorts = new_link_ports
                ext_vls.append(ext_vl)

        return ext_vls

    def _make_ext_mgd_vl_info_from_req(self, vnfd, flavour_id, req, grant):
        # make extManagedVirtualLinkInfo
        ext_mgd_vls = []
        req_mgd_vls = []
        if grant.obj_attr_is_set('extManagedVirtualLinks'):
            req_mgd_vls = grant.extManagedVirtualLinks
        elif req.obj_attr_is_set('extManagedVirtualLinks'):
            req_mgd_vls = req.extManagedVirtualLinks

        vls = vnfd.get_virtual_link_nodes(flavour_id)
        for req_mgd_vl in req_mgd_vls:
            vl_name = req_mgd_vl.vnfVirtualLinkDescId
            if vl_name not in list(vls.keys()):
                # should not occur. just check for consistency.
                LOG.debug("%s not in VNFD VL definition.", vl_name)
                continue
            ext_mgd_vl = objects.ExtManagedVirtualLinkInfoV2(
                id=req_mgd_vl.id,
                vnfVirtualLinkDescId=vl_name,
                networkResource=objects.ResourceHandle(
                    id=uuidutils.generate_uuid(),
                    resourceId=req_mgd_vl.resourceId
                )
            )
            if req_mgd_vl.obj_attr_is_set('vimConnectionId'):
                ext_mgd_vl.networkResource.vimConnectionId = (
                    req_mgd_vl.vimConnectionId)
            if req_mgd_vl.obj_attr_is_set('resourceProviderId'):
                ext_mgd_vl.networkResource.resourceProviderId = (
                    req_mgd_vl.resourceProviderId)

            ext_mgd_vls.append(ext_mgd_vl)

            if req_mgd_vl.obj_attr_is_set('vnfLinkPort'):
                ext_mgd_vl.vnfLinkPort = [
                    objects.VnfLinkPortInfoV2(
                        id=_make_link_port_id(req_link_port.vnfLinkPortId),
                        resourceHandle=req_link_port.resourceHandle,
                        cpInstanceType='EXT_CP',  # may be changed later
                        # cpInstanceId may set later
                    )
                    for req_link_port in req_mgd_vl.vnfLinkPort
                ]

        return ext_mgd_vls

    def _make_ext_mgd_vl_info_from_inst(self, old_inst_vnf_info):
        # make extManagedVirtualLinkInfo
        ext_mgd_vls = []

        if old_inst_vnf_info.obj_attr_is_set('extManagedVirtualLinkInfo'):
            ext_mgd_vls = old_inst_vnf_info.extManagedVirtualLinkInfo

        for ext_mgd_vl in ext_mgd_vls:
            if ext_mgd_vl.obj_attr_is_set('vnfLinkPorts'):
                ext_mgd_vl.vnfLinkPorts = [link_port
                    for link_port in ext_mgd_vl.vnfLinkPorts
                    if _is_link_port(link_port.id)]

        return ext_mgd_vls

    def _find_ext_vl_by_cp_name(self, cp_name, ext_vl_infos):
        for ext_vl_info in ext_vl_infos:
            for ext_cp_data in ext_vl_info.currentVnfExtCpData:
                if ext_cp_data.cpdId == cp_name:
                    return ext_vl_info, ext_cp_data

        return None, None

    def _link_ext_port_info(self, ext_port_infos, ext_vl_infos, ext_cp_infos,
            port_reses):
        for ext_port_info in ext_port_infos:
            res = port_reses[ext_port_info.id]
            cp_name = res['resource_name']
            ext_cp_info = objects.VnfExtCpInfoV2(
                id=_make_cp_info_id(ext_port_info.id),
                extLinkPortId=ext_port_info.id,
                cpdId=cp_name
                # associatedVnfcCpId may set later
            )
            ext_port_info.cpInstanceId = ext_cp_info.id

            ext_vl_info, ext_cp_data = self._find_ext_vl_by_cp_name(
                cp_name, ext_vl_infos)

            if ext_vl_info:
                if ext_vl_info.obj_attr_is_set('extLinkPorts'):
                    ext_vl_info.extLinkPorts.append(ext_port_info)
                else:
                    ext_vl_info.extLinkPorts = [ext_port_info]

                for key, cp_conf in ext_cp_data.cpConfig.items():
                    # NOTE: it is assumed that there is one item
                    # (with cpProtocolData) of cpConfig at the moment.
                    if cp_conf.obj_attr_is_set('cpProtocolData'):
                        proto_infos = []
                        for proto_data in cp_conf.cpProtocolData:
                            proto_info = self._proto_data_to_info(
                                proto_data)
                            proto_infos.append(proto_info)
                        ext_cp_info.cpProtocolInfo = proto_infos
                        ext_cp_info.cpConfigId = key
                        break

            ext_cp_infos.append(ext_cp_info)

    def _find_vnfc_cp_info(self, port_res, vnfc_res_infos, server_reses):
        for vnfc_res_info in vnfc_res_infos:
            if not vnfc_res_info.obj_attr_is_set('vnfcCpInfo'):
                continue
            vnfc_res = server_reses[vnfc_res_info.id]
            vdu_name = vnfc_res_info.vduId
            cp_name = port_res['resource_name']
            if (vdu_name in port_res.get('required_by', []) and
                    port_res.get('parent_resource') ==
                    vnfc_res.get('parent_resource')):
                for vnfc_cp in vnfc_res_info.vnfcCpInfo:
                    if vnfc_cp.cpdId == cp_name:
                        return vnfc_cp

    def _link_vnfc_cp_info(self, vnfc_res_infos, ext_port_infos,
            vnf_port_infos, ext_cp_infos, server_reses, port_reses):

        for ext_port_info in ext_port_infos:
            port_res = port_reses[ext_port_info.id]
            vnfc_cp = self._find_vnfc_cp_info(port_res, vnfc_res_infos,
                server_reses)
            if vnfc_cp:
                # should be found
                vnfc_cp.vnfExtCpId = ext_port_info.cpInstanceId
                for ext_cp_info in ext_cp_infos:
                    if ext_cp_info.extLinkPortId == ext_port_info.id:
                        ext_cp_info.associatedVnfcCpId = vnfc_cp.id
                        break

        for vnf_port_info in vnf_port_infos:
            port_res = port_reses[vnf_port_info.id]
            vnfc_cp = self._find_vnfc_cp_info(port_res, vnfc_res_infos,
                server_reses)
            if vnfc_cp:
                # should be found
                vnf_port_info.cpInstanceType = 'VNFC_CP'
                vnf_port_info.cpInstanceId = vnfc_cp.id
                vnfc_cp.vnfLinkPortId = vnf_port_info.id

    def _make_vnfc_metadata(self, server_res, heat_reses):
        metadata = {
            'creation_time': server_res['creation_time'],
            'stack_id': heat_utils.get_resource_stack_id(server_res)
        }
        parent_res = heat_utils.get_parent_resource(server_res, heat_reses)
        if parent_res:
            metadata['parent_stack_id'] = (
                heat_utils.get_resource_stack_id(parent_res))
            metadata['parent_resource_name'] = parent_res['resource_name']

        return metadata

    def _make_instantiated_vnf_info(self, req, inst, grant_req, grant, vnfd,
            heat_reses):
        op = grant_req.operation
        if op == v2fields.LcmOperationType.INSTANTIATE:
            flavour_id = req.flavourId
        else:
            flavour_id = inst.instantiatedVnfInfo.flavourId
        vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
        vducp_nodes = vnfd.get_vducp_nodes(flavour_id)

        storage_reses = self._get_checked_reses(
            vnfd.get_storage_nodes(flavour_id),
            heat_utils.get_storage_reses(heat_reses))
        server_reses = self._get_checked_reses(vnfd.get_vdu_nodes(flavour_id),
            heat_utils.get_server_reses(heat_reses))
        network_reses = self._get_checked_reses(
            vnfd.get_virtual_link_nodes(flavour_id),
            heat_utils.get_network_reses(heat_reses))
        port_reses = self._get_checked_reses(vducp_nodes,
            heat_utils.get_port_reses(heat_reses))

        def _res_to_handle(res):
            return objects.ResourceHandle(
                resourceId=res['physical_resource_id'],
                vimLevelResourceType=res['resource_type'],
                vimConnectionId=vim_info.vimId)

        storage_infos = [
            objects.VirtualStorageResourceInfoV2(
                id=res_id,
                virtualStorageDescId=res['resource_name'],
                storageResource=_res_to_handle(res),
                metadata={
                    'stack_id': heat_utils.get_resource_stack_id(res)
                }
            )
            for res_id, res in storage_reses.items()
        ]

        vnfc_res_infos = [
            objects.VnfcResourceInfoV2(
                id=res_id,
                vduId=res['resource_name'],
                computeResource=_res_to_handle(res),
                metadata=self._make_vnfc_metadata(res, heat_reses)
            )
            for res_id, res in server_reses.items()
        ]

        for vnfc_res_info in vnfc_res_infos:
            vdu_name = vnfc_res_info.vduId
            server_res = server_reses[vnfc_res_info.id]
            storage_ids = [storage_id
                for storage_id, storage_res in storage_reses.items()
                if (vdu_name in storage_res.get('required_by', []) and
                    server_res.get('parent_resource') ==
                    storage_res.get('parent_resource'))
            ]
            if storage_ids:
                vnfc_res_info.storageResourceIds = storage_ids

            vdu_cps = vnfd.get_vdu_cps(flavour_id, vdu_name)
            cp_infos = [
                objects.VnfcResourceInfoV2_VnfcCpInfo(
                    id=_make_combination_id(cp, vnfc_res_info.id),
                    cpdId=cp,
                    # vnfExtCpId or vnfLinkPortId may set later
                )
                for cp in vdu_cps
            ]
            if cp_infos:
                vnfc_res_info.vnfcCpInfo = cp_infos

        vnf_vl_res_infos = [
            objects.VnfVirtualLinkResourceInfoV2(
                id=res_id,
                vnfVirtualLinkDescId=res['resource_name'],
                networkResource=_res_to_handle(res)
            )
            for res_id, res in network_reses.items()
        ]

        ext_cp_infos = []
        if op == v2fields.LcmOperationType.INSTANTIATE:
            ext_vl_infos = self._make_ext_vl_info_from_req(
                req, grant, ext_cp_infos)
            ext_mgd_vl_infos = self._make_ext_mgd_vl_info_from_req(vnfd,
                flavour_id, req, grant)
        else:
            old_inst_vnf_info = inst.instantiatedVnfInfo
            if op == v2fields.LcmOperationType.CHANGE_EXT_CONN:
                ext_vl_infos = self._make_ext_vl_info_from_req_and_inst(
                    req, grant, old_inst_vnf_info, ext_cp_infos)
            else:
                ext_vl_infos = self._make_ext_vl_info_from_inst(
                    old_inst_vnf_info, ext_cp_infos)
            ext_mgd_vl_infos = self._make_ext_mgd_vl_info_from_inst(
                old_inst_vnf_info)

        def _find_vl_name(port_res):
            cp_name = port_res['resource_name']
            return vnfd.get_vl_name_from_cp(flavour_id, vducp_nodes[cp_name])

        ext_port_infos = [
            objects.ExtLinkPortInfoV2(
                id=res_id,
                resourceHandle=_res_to_handle(res)
            )
            for res_id, res in port_reses.items()
            if _find_vl_name(res) is None
        ]

        self._link_ext_port_info(ext_port_infos, ext_vl_infos, ext_cp_infos,
            port_reses)

        vnf_port_infos = [
            objects.VnfLinkPortInfoV2(
                id=res_id,
                resourceHandle=_res_to_handle(res),
                cpInstanceType='EXT_CP'  # may be changed later
            )
            for res_id, res in port_reses.items()
            if _find_vl_name(res) is not None
        ]

        vl_name_to_info = {info.vnfVirtualLinkDescId: info
            for info in vnf_vl_res_infos + ext_mgd_vl_infos}

        for vnf_port_info in vnf_port_infos:
            port_res = port_reses[vnf_port_info.id]
            vl_info = vl_name_to_info.get(_find_vl_name(port_res))
            if vl_info is None:
                # should not occur. just check for consistency.
                continue

            if vl_info.obj_attr_is_set('vnfLinkPorts'):
                vl_info.vnfLinkPorts.append(vnf_port_info)
            else:
                vl_info.vnfLinkPorts = [vnf_port_info]

        self._link_vnfc_cp_info(vnfc_res_infos, ext_port_infos,
            vnf_port_infos, ext_cp_infos, server_reses, port_reses)

        # NOTE: The followings are not handled at the moment.
        # - handle tosca.nodes.nfv.VnfExtCp type
        #   Note that there is no example in current tacker examples which use
        #   tosca.nodes.nfv.VnfExtCp type and related BaseHOT definitions.
        # - in the case of specifying linkPortId of extVirtualLinks or
        #   extManagedVirtualLinks, the link of vnfcCpInfo is not handled
        #   because the association of compute resource and port resource
        #   is not identified.

        # make new instantiatedVnfInfo and replace
        inst_vnf_info = objects.VnfInstanceV2_InstantiatedVnfInfo(
            flavourId=flavour_id,
            vnfState='STARTED',
        )
        if storage_infos:
            inst_vnf_info.virtualStorageResourceInfo = storage_infos

        if vnfc_res_infos:
            # NOTE: scale-in specification of tacker SOL003 v2 API is that
            # newer VDU is selected for reduction. It is necessary to sort
            # vnfc_res_infos at this point so that the conductor should
            # choose VDUs from a head sequentially when making scale-in
            # grant request.

            def _get_key(vnfc):
                return parser.isoparse(vnfc.metadata['creation_time'])

            sorted_vnfc_res_infos = sorted(vnfc_res_infos, key=_get_key,
                                           reverse=True)
            inst_vnf_info.vnfcResourceInfo = sorted_vnfc_res_infos

        if vnf_vl_res_infos:
            inst_vnf_info.vnfVirtualLinkResourceInfo = vnf_vl_res_infos

        if ext_vl_infos:
            inst_vnf_info.extVirtualLinkInfo = ext_vl_infos

        if ext_mgd_vl_infos:
            inst_vnf_info.extManagedVirtualLinkInfo = ext_mgd_vl_infos

        if ext_cp_infos:
            inst_vnf_info.extCpInfo = ext_cp_infos

        # make vnfcInfo
        # NOTE: vnfcInfo only exists in SOL002
        if vnfc_res_infos:
            vnfc_infos = []
            old_vnfc_infos = []
            if (inst.obj_attr_is_set('instantiatedVnfInfo') and
                    inst.instantiatedVnfInfo.obj_attr_is_set('vnfcInfo')):
                old_vnfc_infos = inst.instantiatedVnfInfo.vnfcInfo

            for vnfc_res_info in sorted_vnfc_res_infos:
                vnfc_info = None
                vnfc_id = _make_combination_id(vnfc_res_info.vduId,
                                               vnfc_res_info.id)
                for old_vnfc_info in old_vnfc_infos:
                    if old_vnfc_info.id == vnfc_id:
                        # re-use current object since
                        # vnfcConfigurableProperties may be set.
                        vnfc_info = old_vnfc_info
                        break
                if vnfc_info is None:
                    vnfc_info = objects.VnfcInfoV2(
                        id=vnfc_id,
                        vduId=vnfc_res_info.vduId,
                        vnfcResourceInfoId=vnfc_res_info.id,
                        vnfcState='STARTED'
                    )
                vnfc_infos.append(vnfc_info)

            inst_vnf_info.vnfcInfo = vnfc_infos

        inst.instantiatedVnfInfo = inst_vnf_info

    def _handle_exception(
            self, res, new_res_ids, vdu_infos,
            vdu_id, heat_client, req, inst, vnfd,
            stack_name, ex=None, get_res_flag=False):
        if get_res_flag:
            if len(res.keys()) == 2:
                par_stack_id = '{}/{}'.format(
                    res.get('resource_name'),
                    res.get('physical_resource_id'))
            else:
                par_stack_id = heat_utils.get_parent_nested_id(res)
            self._get_new_res_info(
                res.get('resource_name'),
                new_res_ids[vdu_id],
                par_stack_id,
                vdu_infos[vdu_id], vdu_id,
                heat_client)
        self._update_vnf_instantiated_info(
            req, new_res_ids, inst,
            vnfd, heat_client, stack_name)
        if ex:
            raise ex
        raise sol_ex.StackOperationFailed

    def _get_entire_stack_fields(self, heat_client, stack_id,
                                 group_vdu_ids, vdu_infos):
        parameter = json.loads(heat_client.get_parameters(stack_id)['nfv'])
        for group_vdu_id in group_vdu_ids:
            if not parameter['VDU'][group_vdu_id].get('vcImageId'):
                volume_info = vdu_infos[
                    group_vdu_id].get('volume_info')
                parameter['VDU'][volume_info.get('volume_name')][
                    'vcImageId'] = vdu_infos[group_vdu_id].get(
                    'image')
            else:
                parameter['VDU'][group_vdu_id][
                    'vcImageId'] = vdu_infos[group_vdu_id].get(
                    'image')
        fields = {
            "stack_id": stack_id,
            "parameters": {"nfv": parameter}
        }
        return fields
