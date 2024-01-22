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


import json
import os
import pickle
import re
import subprocess
import yaml

from dateutil import parser
import eventlet
from oslo_log import log as logging
from oslo_utils import uuidutils

from tacker.sol_refactored.common import common_script_utils
from tacker.sol_refactored.common import config
from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.common import lcm_op_occ_utils as lcmocc_utils
from tacker.sol_refactored.common import vnf_instance_utils as inst_utils
from tacker.sol_refactored.infra_drivers.openstack import heat_utils
from tacker.sol_refactored.infra_drivers.openstack import nova_utils
from tacker.sol_refactored.infra_drivers.openstack import userdata_default
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
    # NOTE: used for extManagedVL
    return '{}{}'.format(LINK_PORT_PREFIX, link_port_id)


def _is_link_port(link_port_id):
    # NOTE: used for extManagedVL
    return link_port_id.startswith(LINK_PORT_PREFIX)


def _make_cp_info_id(link_port_id):
    return '{}{}'.format(CP_INFO_PREFIX, link_port_id)


def _make_combination_id(a, b):
    return '{}-{}'.format(a, b)


def _get_vdu_idx(vdu_with_idx):
    part = vdu_with_idx.rpartition('-')
    if part[1] == '':
        return None
    return int(part[2])


def _rsc_with_idx(rsc, rsc_idx):
    if rsc_idx is None:
        return rsc
    return f'{rsc}-{rsc_idx}'


class Openstack(object):

    def __init__(self):
        pass

    def instantiate(self, req, inst, grant_req, grant, vnfd):
        # make HOT
        fields = self._make_hot(req, inst, grant_req, grant, vnfd)
        vdu_ids = self._get_additional_vdu_id(grant_req, inst)

        # create or update stack
        vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
        heat_client = heat_utils.HeatClient(vim_info)
        stack_name = heat_utils.get_stack_name(inst)
        stack_id = heat_client.get_stack_id(stack_name)

        if stack_id is None:
            fields['stack_name'] = stack_name
            try:
                stack_id = heat_client.create_stack(fields)
            except sol_ex.StackOperationFailed as ex:
                anti_rules = vnfd.get_anti_affinity_targets(req.flavourId)
                self._update_stack_retry(heat_client, fields, inst, None,
                    ex, vim_info, vdu_ids, anti_rules)
                stack_id = heat_client.get_stack_id(stack_name)
        else:
            try:
                heat_client.update_stack(f'{stack_name}/{stack_id}', fields)
            except sol_ex.StackOperationFailed as ex:
                anti_rules = vnfd.get_anti_affinity_targets(req.flavourId)
                self._update_stack_retry(heat_client, fields, inst, stack_id,
                    ex, vim_info, vdu_ids, anti_rules)

        # make instantiated_vnf_info
        self._make_instantiated_vnf_info(req, inst, grant_req, grant, vnfd,
            heat_client, stack_id=stack_id)

    def instantiate_rollback(self, req, inst, grant_req, grant, vnfd):
        vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
        heat_client = heat_utils.HeatClient(vim_info)
        stack_name = heat_utils.get_stack_name(inst)
        stack_id = heat_client.get_stack_id(stack_name)
        if stack_id is not None:
            heat_client.delete_stack(f'{stack_name}/{stack_id}')

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

        status, _ = heat_client.get_status(stack_name)
        if status == "DELETE_COMPLETE":
            # NOTE: After heal all (all=true) recreates the stack, if it
            # fails before saving the vnf_instance data.
            # The fail operation in error-handling is performed on the heal
            # operation. Then directly terminate, the result will fail,
            # because the stack id does not exist on VIM.
            # When calling the heat API, the stack id is not used here,
            # but the stack name is used instead.
            LOG.debug("Since heal all (all=true) was executed before, "
                      f"stack: {stack_name} does not exist in VIM, and now "
                      f"stack: {stack_name.split('/')[0]} is used instead.")
            stack_name = stack_name.split('/')[0]

        heat_client.delete_stack(stack_name)

    def _is_full_fields(self, fields):
        # NOTE: fields made by UserData class contains only update parts
        # and 'existing' is not specified (and is thought as True) by
        # default. if 'existing' is specified and it is False, fields is
        # a full content.
        return not fields.get('existing', True)

    def _update_fields(self, heat_client, stack_name, fields):
        if self._is_full_fields(fields):
            # used by change_vnfpkg(, rollback) only at the moment.
            return fields

        if 'nfv' in fields.get('parameters', {}):
            parameters = heat_client.get_parameters(stack_name)
            LOG.debug("ORIG parameters: %s", parameters)
            # NOTE: Using json.loads because parameters['nfv'] is string
            orig_nfv_dict = json.loads(parameters.get('nfv', '{}'))
            fields['parameters']['nfv'] = inst_utils.json_merge_patch(
                orig_nfv_dict, fields['parameters']['nfv'])

        if 'template' in fields:
            orig_template = heat_client.get_template(stack_name)
            template = inst_utils.json_merge_patch(
                orig_template, yaml.safe_load(fields['template']))
            fields['template'] = yaml.safe_dump(template)

        LOG.debug("NEW fields: %s", fields)
        return fields

    def scale(self, req, inst, grant_req, grant, vnfd):
        # make HOT
        fields = self._make_hot(req, inst, grant_req, grant, vnfd)
        if req.type == 'SCALE_OUT':
            vdu_ids = self._get_additional_vdu_id(grant_req, inst)

        vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
        heat_client = heat_utils.HeatClient(vim_info)

        # mark unhealthy to servers to be removed if scale in
        if req.type == 'SCALE_IN':
            vnfc_res_ids = [res_def.resource.resourceId
                            for res_def in grant_req.removeResources
                            if res_def.type == 'COMPUTE']
            for vnfc in inst.instantiatedVnfInfo.vnfcResourceInfo:
                if vnfc.computeResource.resourceId in vnfc_res_ids:
                    if 'parent_stack_id' in vnfc.metadata:
                        # AutoScalingGroup
                        heat_client.mark_unhealthy(
                            vnfc.metadata['parent_stack_id'],
                            vnfc.metadata['parent_resource_name'])
                    elif 'vdu_idx' not in vnfc.metadata:
                        # It means definition of VDU in the BaseHOT
                        # is inappropriate.
                        raise sol_ex.UnexpectedParentResourceDefinition()

        # update stack
        stack_name = heat_utils.get_stack_name(inst)
        fields = self._update_fields(heat_client, stack_name, fields)
        try:
            heat_client.update_stack(stack_name, fields)
        except sol_ex.StackOperationFailed as ex:
            if req.type == 'SCALE_OUT':
                anti_rules = vnfd.get_anti_affinity_targets(
                    inst.instantiatedVnfInfo.flavourId)
                self._update_stack_retry(heat_client, fields, inst, None, ex,
                    vim_info, vdu_ids, anti_rules)
            else:
                raise ex

        # make instantiated_vnf_info
        self._make_instantiated_vnf_info(req, inst, grant_req, grant, vnfd,
            heat_client)

    def scale_rollback(self, req, inst, grant_req, grant, vnfd):
        # NOTE: rollback is supported for scale out only
        # make HOT
        fields = self._make_hot(req, inst, grant_req, grant, vnfd,
                                is_rollback=True)

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
                if 'parent_stack_id' in metadata:
                    # AutoScalingGroup
                    heat_client.mark_unhealthy(
                        metadata['parent_stack_id'],
                        metadata['parent_resource_name'])
                elif 'vdu_idx' not in metadata:
                    # It means definition of VDU in the BaseHOT
                    # is inappropriate.
                    raise sol_ex.UnexpectedParentResourceDefinition()

        # update (put back) 'desired_capacity' parameter
        fields = self._update_fields(heat_client, stack_name, fields)
        heat_client.update_stack(stack_name, fields)

        # NOTE: instantiatedVnfInfo is not necessary to update since it
        # should be same as before scale API started.

    def change_ext_conn(self, req, inst, grant_req, grant, vnfd):
        # make HOT
        fields = self._make_hot(req, inst, grant_req, grant, vnfd)

        # update stack
        vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
        heat_client = heat_utils.HeatClient(vim_info)
        stack_name = heat_utils.get_stack_name(inst)
        fields = self._update_fields(heat_client, stack_name, fields)
        heat_client.update_stack(stack_name, fields)

        # make instantiated_vnf_info
        self._make_instantiated_vnf_info(req, inst, grant_req, grant, vnfd,
            heat_client)

    def change_ext_conn_rollback(self, req, inst, grant_req, grant, vnfd):
        # make HOT
        fields = self._make_hot(req, inst, grant_req, grant, vnfd,
                                is_rollback=True)

        # update stack
        vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
        heat_client = heat_utils.HeatClient(vim_info)
        stack_name = heat_utils.get_stack_name(inst)
        fields = self._update_fields(heat_client, stack_name, fields)
        heat_client.update_stack(stack_name, fields)

        # NOTE: it is necessary to re-create instantiatedVnfInfo because
        # ports may be changed.
        self._make_instantiated_vnf_info(req, inst, grant_req, grant, vnfd,
            heat_client, is_rollback=True)

    def heal(self, req, inst, grant_req, grant, vnfd):
        # make HOT
        # NOTE: _make_hot() is called as other operations, but it returns
        # empty 'nfv' dict by default. Therefore _update_fields() returns
        # current heat parameters as is.
        fields = self._make_hot(req, inst, grant_req, grant, vnfd)

        # "re_create" is set to True only when SOL003 heal(without
        # vnfcInstanceId) and "all=True" in additionalParams.
        re_create = False
        if (req.obj_attr_is_set('additionalParams') and
                req.additionalParams.get('all', False) and
                not req.obj_attr_is_set('vnfcInstanceId')):
            re_create = True

        vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
        heat_client = heat_utils.HeatClient(vim_info)
        stack_name = heat_utils.get_stack_name(inst)

        if re_create:
            status, _ = heat_client.get_status(stack_name)
            if status == "DELETE_COMPLETE":
                # NOTE: After heal all (all=true) recreates the stack,
                # if it fails before saving the vnf_instance data,
                # and then performs a retry operation, the stack_id
                # contained in the stack_name variable does not exist on VIM.
                # When calling Heat-API, only the stack name is used.
                LOG.debug("Since heal all (all=true) was executed before, "
                          f"stack: {stack_name} does not exist in VIM, and "
                          f"now stack: {stack_name.split('/')[0]} is used "
                          "instead.")
                stack_name = stack_name.split('/')[0]

        fields = self._update_fields(heat_client, stack_name, fields)

        if re_create:
            # NOTE: DefaultUserData::heal() don't care about "template" and
            # "files". Get and set current "template" and "files".
            if "template" not in fields:
                fields["template"] = heat_client.get_template(stack_name)
            if "files" not in fields:
                fields["files"] = heat_client.get_files(stack_name)
            fields["stack_name"] = stack_name.split('/')[0]

            # stack delete and create
            heat_client.delete_stack(stack_name)
            try:
                stack_id = heat_client.create_stack(fields)
            except sol_ex.StackOperationFailed as ex:
                vdu_ids = self._get_vdu_id_from_grant_req(grant_req, inst)
                anti_rules = vnfd.get_anti_affinity_targets(
                    inst.instantiatedVnfInfo.flavourId)
                self._update_stack_retry(heat_client, fields, inst, None,
                    ex, vim_info, vdu_ids, anti_rules)
                stack_id = heat_client.get_stack_id(stack_name)
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
            try:
                heat_client.update_stack(stack_name, fields)
            except sol_ex.StackOperationFailed as ex:
                vdu_ids = self._get_vdu_id_from_grant_req(grant_req, inst)
                anti_rules = vnfd.get_anti_affinity_targets(
                    inst.instantiatedVnfInfo.flavourId)
                self._update_stack_retry(heat_client, fields, inst, None,
                    ex, vim_info, vdu_ids, anti_rules)

            stack_id = inst.instantiatedVnfInfo.metadata['stack_id']

        # make instantiated_vnf_info
        self._make_instantiated_vnf_info(req, inst, grant_req, grant, vnfd,
            heat_client, stack_id=stack_id)

    def change_vnfpkg(self, req, inst, grant_req, grant, vnfd):
        # make HOT
        fields = self._make_hot(req, inst, grant_req, grant, vnfd)

        vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
        heat_client = heat_utils.HeatClient(vim_info)

        if req.additionalParams['upgrade_type'] == 'RollingUpdate':
            self._change_vnfpkg_rolling_update(req, inst, grant_req, grant,
                vnfd, fields, heat_client, False)
        else:
            # not reach here
            pass

        # update stack
        stack_name = heat_utils.get_stack_name(inst)
        fields = self._update_fields(heat_client, stack_name, fields)
        heat_client.update_stack(stack_name, fields)

        # make instantiated_vnf_info
        self._make_instantiated_vnf_info(req, inst, grant_req, grant, vnfd,
            heat_client)

    def _get_flavor_from_vdu_dict(self, vnfc, vdu_dict):
        vdu_name = _rsc_with_idx(vnfc.vduId, vnfc.metadata.get('vdu_idx'))
        return vdu_dict.get(vdu_name, {}).get('computeFlavourId')

    def _get_zone_from_vdu_dict(self, vnfc, vdu_dict):
        vdu_name = _rsc_with_idx(vnfc.vduId, vnfc.metadata.get('vdu_idx'))
        return vdu_dict.get(vdu_name, {}).get('locationConstraints')

    def _get_images_from_vdu_dict(self, vnfc, storage_infos, vdu_dict):
        vdu_idx = vnfc.metadata.get('vdu_idx')
        vdu_name = _rsc_with_idx(vnfc.vduId, vdu_idx)
        vdu_names = [vdu_name]
        if vnfc.obj_attr_is_set('storageResourceIds'):
            vdu_names += [
                _rsc_with_idx(storage_info.virtualStorageDescId, vdu_idx)
                for storage_info in storage_infos
                if storage_info.id in vnfc.storageResourceIds
            ]
        images = {}
        for vdu_name in vdu_names:
            image = vdu_dict.get(vdu_name, {}).get('vcImageId')
            if image:
                images[vdu_name] = image

        return images

    def _change_vnfpkg_rolling_update(self, req, inst, grant_req, grant,
            vnfd, fields, heat_client, is_rollback):
        if not grant_req.obj_attr_is_set('removeResources'):
            return

        vnfc_res_ids = [res_def.resource.resourceId
                        for res_def in grant_req.removeResources
                        if res_def.type == 'COMPUTE']
        vnfcs = [vnfc
                 for vnfc in inst.instantiatedVnfInfo.vnfcResourceInfo
                 if vnfc.computeResource.resourceId in vnfc_res_ids]

        if self._is_full_fields(fields):
            # NOTE: it is used by StandardUserData only at the moment,
            # use it to check the fields is constructed by
            # StandardUserData (and its inheritance) or not.
            method = self._change_vnfpkg_rolling_update_user_data_standard
        else:
            # method for DefaultUserData (and its inheritance)
            method = self._change_vnfpkg_rolling_update_user_data_default

        method(req, inst, grant_req, grant, vnfd, fields, heat_client,
            vnfcs, is_rollback)

    def _change_vnfpkg_rolling_update_user_data_default(self, req, inst,
            grant_req, grant, vnfd, fields, heat_client, vnfcs, is_rollback):
        templates = {}

        def _get_template(parent_stack_id):
            if parent_stack_id not in templates:
                templates[parent_stack_id] = heat_client.get_template(
                    parent_stack_id)
            return templates[parent_stack_id]

        vdu_dict = fields['parameters']['nfv']['VDU']
        cp_dict = fields['parameters']['nfv']['CP']
        stack_name = heat_utils.get_stack_name(inst)

        for vnfc in vnfcs:
            if 'parent_stack_id' in vnfc.metadata:
                # it means the VM is created by OS::Heat::AutoScalingGroup
                parent_stack_id = vnfc.metadata['parent_stack_id']
                template = _get_template(parent_stack_id)
                parent_name = vnfc.metadata['parent_resource_name']
                props = template['resources'][parent_name]['properties']
                # replace 'flavor' and 'image-{vdu name}' in properties
                props['flavor'] = vdu_dict[vnfc.vduId]['computeFlavourId']
                for key in props.keys():
                    if key.startswith('image-'):
                        vdu_name = key.replace('image-', '')
                        props[key] = vdu_dict[vdu_name]['vcImageId']
                vdu_fields = {
                    "stack_id": parent_stack_id,
                    "template": template
                }
                LOG.debug("stack fields: %s", vdu_fields)
                # NOTE: for VMs with AutoScalingGroups, rolling-update does
                # not update CPs one by one. There are updated in once after
                # returning this method.
                heat_client.update_stack(parent_stack_id, vdu_fields)
            else:
                # pickup 'vcImageId' and 'computeFlavourId' from vdu_dict
                vdu_name = vnfc.vduId
                new_vdus = {}
                flavor = self._get_flavor_from_vdu_dict(vnfc, vdu_dict)
                if flavor:
                    new_vdus[vdu_name] = {'computeFlavourId': flavor}
                storage_infos = (
                    inst.instantiatedVnfInfo.virtualStorageResourceInfo
                    if vnfc.obj_attr_is_set('storageResourceIds') else [])
                images = self._get_images_from_vdu_dict(vnfc,
                    storage_infos, vdu_dict)
                for vdu_name, image in images.items():
                    new_vdus.setdefault(vdu_name, {})
                    new_vdus[vdu_name]['vcImageId'] = image

                # pickup 'CP' updates
                cp_names = vnfd.get_vdu_cps(
                    inst.instantiatedVnfInfo.flavourId, vnfc.vduId)
                new_cps = {cp_name: cp_dict[cp_name]
                           for cp_name in cp_names if cp_name in cp_dict}

                update_fields = {
                    'parameters': {'nfv': {'VDU': new_vdus, 'CP': new_cps}}
                }
                update_fields = self._update_fields(heat_client, stack_name,
                    update_fields)
                LOG.debug("stack fields: %s", update_fields)
                heat_client.update_stack(stack_name, update_fields)

            # execute coordinate_vnf_script
            self._execute_coordinate_vnf_script(
                req, vnfd, vnfc, inst, grant_req, heat_client, is_rollback)

    def _change_vnfpkg_rolling_update_user_data_standard(self, req, inst,
            grant_req, grant, vnfd, fields, heat_client, vnfcs, is_rollback):
        stack_name = heat_utils.get_stack_name(inst)

        # make base template
        base_template = heat_client.get_template(stack_name)
        new_template = yaml.safe_load(fields['template'])
        diff_reses = {
            res_name: res_value
            for res_name, res_value in new_template['resources'].items()
            if res_name not in base_template['resources'].keys()
        }
        base_template['resources'].update(diff_reses)

        base_files = heat_client.get_files(stack_name)
        base_files.update(fields['files'])

        base_parameters = heat_client.get_parameters(stack_name)
        # NOTE: Using json.loads because parameters['nfv'] is string
        base_nfv_dict = json.loads(base_parameters.get('nfv', '{}'))
        new_nfv_dict = fields['parameters']['nfv']

        def _get_param_third_keys(res):
            """Get third parameter keys

            example:
            ---
            VDU1-1:
              type: VDU1.yaml
              properties:
                flavor: { get_param: [ nfv, VDU, VDU1-1, computeFlavourId ] }
                image-VDU1: { get_param: [ nfv, VDU, VDU1-1, vcImageId ] }
                net1: { get_param: [ nfv, CP, VDU1_CP1-1, network ] }
            ---
            returns {'VDU1-1', 'VDU1_CP1-1'}
            """

            keys = set()
            for prop_value in res.get('properties', {}).values():
                if not isinstance(prop_value, dict):
                    continue
                for key, value in prop_value.items():
                    if (key == 'get_param' and isinstance(value, list) and
                            len(value) >= 4 and value[0] == 'nfv'):
                        keys.add(value[2])
            return keys

        for vnfc in vnfcs:
            vdu_idx = vnfc.metadata.get('vdu_idx')
            vdu_name = _rsc_with_idx(vnfc.vduId, vdu_idx)

            # replace VDU_{idx} part
            target_res = new_template['resources'][vdu_name]
            base_template['resources'][vdu_name] = target_res

            # update parameters
            third_keys = _get_param_third_keys(target_res)
            for item in ['VDU', 'CP']:
                for key, value in new_nfv_dict.get(item, {}).items():
                    if key in third_keys:
                        base_nfv_dict[item][key] = value

            update_fields = {
                'template': base_template,
                'files': base_files,
                'parameters': {'nfv': base_nfv_dict}
            }
            LOG.debug("update %s: stack fields: %s", vdu_name, update_fields)
            heat_client.update_stack(stack_name, update_fields)

            # execute coordinate_vnf_script
            self._execute_coordinate_vnf_script(
                req, vnfd, vnfc, inst, grant_req, heat_client, is_rollback)

    def _get_ssh_ip(self, stack_id, cp_name, heat_client):
        # NOTE: It is assumed that if the user want to use floating_ip,
        # he must specify the resource name of 'OS::Neutron::FloatingIP'
        # resource as cp_name (ex. VDU1_FloatingIp).
        cp_info = heat_client.get_resource_info(stack_id, cp_name)
        if cp_info.get('attributes', {}).get('floating_ip_address'):
            return cp_info['attributes']['floating_ip_address']
        elif cp_info.get('attributes', {}).get('fixed_ips'):
            return cp_info['attributes']['fixed_ips'][0].get('ip_address')

    def _execute_coordinate_vnf_script(self, req, vnfd, vnfc, inst, grant_req,
            heat_client, is_rollback):
        if is_rollback:
            script = req.additionalParams.get(
                'lcm-operation-coordinate-old-vnf')
        else:
            script = req.additionalParams.get(
                'lcm-operation-coordinate-new-vnf')
        if not script:
            return

        for vdu_param in req.additionalParams['vdu_params']:
            if vnfc.vduId == vdu_param['vdu_id']:
                break
        if is_rollback:
            vnfc_param = vdu_param['old_vnfc_param']
        else:
            vnfc_param = vdu_param['new_vnfc_param']

        ssh_ip = self._get_ssh_ip(vnfc.metadata['stack_id'],
                                  vnfc_param['cp_name'], heat_client)
        if not ssh_ip:
            raise sol_ex.SshIpNotFoundException()

        vnfc_param['ssh_ip'] = ssh_ip
        vnfc_param['is_rollback'] = is_rollback

        coord_req = objects.LcmCoordRequest(
            vnfInstanceId=inst.id,
            vnfLcmOpOccId=grant_req.vnfLcmOpOccId,
            lcmOperationType=grant_req.operation,
            # NOTE: coordinationActionName is set to the dummy value.
            # The value of coordinationActionName must be set in the
            # coordinateVNF script.
            coordinationActionName="should_be_set_by_script",
            _links=objects.LcmCoordRequest_Links(
                vnfLcmOpOcc=objects.Link(
                    href=lcmocc_utils.lcmocc_href(grant_req.vnfLcmOpOccId,
                                                  CONF.v2_vnfm.endpoint)),
                vnfInstance=objects.Link(
                    href=inst_utils.inst_href(inst.id,
                                              CONF.v2_vnfm.endpoint))
            )
        )
        vnfc_param['LcmCoordRequest'] = coord_req.to_dict()
        vnfc_param['inst'] = inst.to_dict()
        for vnfc_info in inst.instantiatedVnfInfo.vnfcInfo:
            if vnfc_info.vnfcResourceInfoId == vnfc.id:
                vnfc_param['vnfc_info_id'] = vnfc_info.id
                break

        tmp_csar_dir = vnfd.make_tmp_csar_dir()
        script_path = os.path.join(tmp_csar_dir, script)
        out = subprocess.run(["python3", script_path],
            input=pickle.dumps(vnfc_param),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        vnfd.remove_tmp_csar_dir(tmp_csar_dir)
        if out.returncode != 0:
            LOG.error(str(out.stderr))
            raise sol_ex.CoordinateVNFExecutionFailed(
                sol_detail=str(out.stderr))

    def change_vnfpkg_rollback(self, req, inst, grant_req, grant, vnfd,
            lcmocc):
        # make HOT
        fields = self._make_hot(req, inst, grant_req, grant, vnfd,
                                is_rollback=True)

        vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
        heat_client = heat_utils.HeatClient(vim_info)

        if req.additionalParams['upgrade_type'] == 'RollingUpdate':
            self._change_vnfpkg_rolling_update(req, inst, grant_req, grant,
                vnfd, fields, heat_client, True)
        else:
            # not reach here
            pass

        # stack update
        stack_name = heat_utils.get_stack_name(inst)
        fields = self._update_fields(heat_client, stack_name, fields)
        heat_client.update_stack(stack_name, fields)

        # NOTE: it is necessary to re-create instantiatedVnfInfo because
        # some resources may be changed.
        self._make_instantiated_vnf_info(req, inst, grant_req, grant, vnfd,
            heat_client, is_rollback=True)

    def _update_stack_retry(self, heat_client, fields, inst, stack_id,
            error_ex, vim_info, vdu_ids, anti_rules):
        if not CONF.v2_vnfm.placement_fallback_best_effort:
            # NOTE: If fallback_best_effort is False,
            # AZ reselection is not executed.
            raise error_ex

        vdu_dict = fields['parameters']['nfv']['VDU']
        failed_vdu_id, failed_zone = self._check_and_get_failed_zone(
            error_ex.detail, vdu_dict)
        if failed_zone is None:
            raise error_ex

        stack_name = heat_utils.get_stack_name(inst, stack_id)
        nova_client = nova_utils.NovaClient(vim_info)
        zones = nova_client.get_zone()
        failed_zones = set()
        failed_zones.add(failed_zone)

        retry_count = (CONF.v2_vnfm.placement_az_select_retry
                       if CONF.v2_vnfm.placement_az_select_retry
                       else len(zones))
        while retry_count > 0:
            exclude_zones = self._get_exclude_zone(
                inst, anti_rules, failed_vdu_id, vdu_ids, vdu_dict)
            if zones - exclude_zones - failed_zones:
                new_zone = list(zones - exclude_zones - failed_zones)[0]
            elif exclude_zones - failed_zones:
                # If there is no zone that matches the Anti-Affinity rules,
                # selected zone does not comply with the Anti-Affinity
                # rules.
                new_zone = list(exclude_zones - failed_zones)[0]
            else:
                message = ("Availability Zone reselection failed. "
                           "No Availability Zone available.")
                LOG.error(message)
                raise error_ex

            for vdu_id, parameters in vdu_dict.items():
                if vdu_id in vdu_ids:
                    if parameters.get('locationConstraints') == failed_zone:
                        parameters['locationConstraints'] = new_zone

            LOG.debug("stack fields: %s", fields)
            try:
                heat_client.update_stack(stack_name, fields)
                return
            except sol_ex.StackOperationFailed as ex:
                failed_vdu_id, failed_zone = self._check_and_get_failed_zone(
                    ex.detail, vdu_dict)
                if failed_zone is None:
                    raise ex
                failed_zones.add(failed_zone)
                retry_count -= 1
                error_ex = ex
        else:
            message = ("Availability Zone reselection failed. "
                       "Reached the retry count limit.")
            LOG.error(message)
            raise error_ex

    def _check_and_get_failed_zone(self, ex_detail, vdu_dict):
        if not re.match(CONF.v2_vnfm.placement_az_resource_error, ex_detail):
            return None, None

        match_result = re.search(r'resources\.((.*)-([0-9]+))', ex_detail)
        if match_result is None:
            LOG.warning(
                "CONF v2_vnfm.placement_az_resource_error is invalid. "
                "'{}' is not match. Please check it.".format(ex_detail))
            return None, None

        vdu_id = match_result.group(1)
        return (vdu_id,
                vdu_dict.get(vdu_id, {}).get('locationConstraints'))

    def _get_additional_vdu_id(self, grant_req, inst):
        add_vdus = {}
        for res_def in grant_req.addResources:
            if res_def.type == 'COMPUTE':
                add_vdus.setdefault(res_def.resourceTemplateId, 0)
                add_vdus[res_def.resourceTemplateId] += 1

        vdu_ids = set()
        for vdu_name, num in add_vdus.items():
            current_vdu_num = common_script_utils.get_current_capacity(
                vdu_name, inst)
            for idx in range(current_vdu_num, current_vdu_num + num):
                vdu_ids.add(f'{vdu_name}-{idx}')
        return vdu_ids

    def _get_vdu_id_from_grant_req(self, grant_req, inst):
        vnfc_res_ids = [res_def.resource.resourceId
                        for res_def in grant_req.removeResources
                        if res_def.type == 'COMPUTE']
        vdu_ids = {_rsc_with_idx(vnfc.vduId, vnfc.metadata.get('vdu_idx'))
                   for vnfc in inst.instantiatedVnfInfo.vnfcResourceInfo
                   if vnfc.computeResource.resourceId in vnfc_res_ids}
        return vdu_ids

    def _get_anti_vdus(self, anti_rules, target_vdu):
        anti_vdus = set()
        for (targets, scope) in anti_rules:
            if scope == 'zone' and target_vdu in targets:
                if len(targets) == 1:
                    anti_vdus.add(target_vdu)
                else:
                    anti_vdus |= {vdu for vdu in targets if vdu != target_vdu}
        return anti_vdus

    def _get_exclude_zone(self, inst, anti_rules, failed_vdu_id, vdu_ids,
            vdu_dict):
        # return zones which are used by VDUs (in inst and vdu_dict[vdu_ids])
        # that are Anti-Affinity relation(anti_rules) of re-selection target
        # VDU(failed_vdu_id).
        def _get_vdu_from_vdu_with_idx(vdu_with_idx):
            part = vdu_with_idx.rpartition('-')
            if part[1] == '':
                return None
            return part[0]

        target_vdu = _get_vdu_from_vdu_with_idx(failed_vdu_id)
        anti_vdus = self._get_anti_vdus(anti_rules, target_vdu)

        exclude_zones = {vdu_dict[vdu_id].get('locationConstraints')
                         for vdu_id in vdu_ids
                         if (_get_vdu_from_vdu_with_idx(vdu_id) in anti_vdus
                             and vdu_dict.get(vdu_id, {}).get(
                                 'locationConstraints') is not None)}

        if (inst.obj_attr_is_set('instantiatedVnfInfo') and
                inst.instantiatedVnfInfo.obj_attr_is_set('vnfcResourceInfo')):
            exclude_zones |= {vnfc.metadata.get('zone') for vnfc
                              in inst.instantiatedVnfInfo.vnfcResourceInfo
                              if (vnfc.vduId in anti_vdus and
                                  vnfc.metadata.get('zone') is not None)}
        return exclude_zones

    def _make_hot(self, req, inst, grant_req, grant, vnfd, is_rollback=False):
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
            operation = grant_req.operation.lower()
            if is_rollback:
                operation = operation + '_rollback'
            LOG.debug("Processing default userdata %s", operation)
            # NOTE: objects used here are dict compat.
            method = getattr(userdata_default.DefaultUserData, operation)
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
                'tmp_csar_dir': tmp_csar_dir,
                'is_rollback': is_rollback
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

        LOG.debug("stack fields: %s", fields)

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
                id=req_link_port.id,
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

    def _is_ext_vl_link_port(self, port_id, ext_cp_data):
        ext_port_ids = []
        for ext_cp in ext_cp_data:
            for cp_config in ext_cp.cpConfig.values():
                if cp_config.obj_attr_is_set('linkPortId'):
                    ext_port_ids.append(cp_config.linkPortId)

        return port_id in ext_port_ids

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
                if self._is_ext_vl_link_port(link_port.id,
                                             ext_vl.currentVnfExtCpData):
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
        else:
            # may happen in case of change_vnfpkg
            return self._make_ext_vl_info_from_inst(old_inst_info,
                                                    ext_cp_infos)

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
                        self._is_ext_vl_link_port(link_port.id,
                                                  ext_vl.currentVnfExtCpData)):
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
            parent_parent_res = heat_utils.get_parent_resource(parent_res,
                                                               heat_reses)
            if (parent_parent_res and
                    parent_parent_res['resource_type'] ==
                    'OS::Heat::AutoScalingGroup'):
                metadata['parent_stack_id'] = (
                    heat_utils.get_resource_stack_id(parent_res))
                metadata['parent_resource_name'] = parent_res['resource_name']
            else:
                metadata['vdu_idx'] = _get_vdu_idx(parent_res['resource_name'])

        return metadata

    def _update_vnfc_metadata(self, vnfc_res_infos, storage_infos,
            heat_client, nfv_dict, inst):
        for vnfc_res_info in vnfc_res_infos:
            metadata = vnfc_res_info.metadata
            if 'parent_stack_id' in metadata:
                # VDU defined by AutoScalingGroup
                template = heat_client.get_template(
                    metadata['parent_stack_id'])
                properties = (template['resources']
                                      [metadata['parent_resource_name']]
                                      ['properties'])
                metadata['flavor'] = properties['flavor']
                for k, v in properties.items():
                    if k.startswith('image-'):
                        metadata[k] = v
            else:
                # assume it is found
                metadata['flavor'] = self._get_flavor_from_vdu_dict(
                    vnfc_res_info, nfv_dict['VDU'])
                images = self._get_images_from_vdu_dict(vnfc_res_info,
                    storage_infos, nfv_dict['VDU'])
                for vdu_name, image in images.items():
                    metadata[f'image-{vdu_name}'] = image
                zone = self._get_zone_from_vdu_dict(vnfc_res_info,
                    nfv_dict['VDU'])
                if zone is not None:
                    metadata['zone'] = zone
                    vnfc_res_info.zoneId = zone

            self._add_extra_metadata_from_inst(metadata, vnfc_res_info.id,
                                               inst)

    def _make_vnfc_info_id(self, inst, vnfc_res_info):
        vdu_idx = vnfc_res_info.metadata.get('vdu_idx')
        if (vdu_idx is not None and inst.obj_attr_is_set('metadata') and
                'VDU_VNFc_mapping' in inst.metadata):
            vnfc_info_ids = inst.metadata['VDU_VNFc_mapping'].get(
                vnfc_res_info.vduId)
            if vnfc_info_ids is not None and len(vnfc_info_ids) > vdu_idx:
                return vnfc_info_ids[vdu_idx]

        # default vnfc_id
        return _make_combination_id(vnfc_res_info.vduId, vnfc_res_info.id)

    def _add_extra_metadata_from_inst(self, metadata, vnfc_res_id, inst):
        if (not inst.obj_attr_is_set('instantiatedVnfInfo') or
                not inst.instantiatedVnfInfo.obj_attr_is_set(
                    'vnfcResourceInfo')):
            return

        extra_keys = ['server_notification']
        for vnfc_res_info in inst.instantiatedVnfInfo.vnfcResourceInfo:
            if vnfc_res_info.id == vnfc_res_id and vnfc_res_info.metadata:
                for key in extra_keys:
                    if key in vnfc_res_info.metadata:
                        metadata[key] = vnfc_res_info.metadata[key]
                return

    def _make_instantiated_vnf_info(self, req, inst, grant_req, grant, vnfd,
            heat_client, is_rollback=False, stack_id=None):
        # get heat resources
        stack_id = stack_id if stack_id else inst.instantiatedVnfInfo.metadata[
            'stack_id']
        stack_name = heat_utils.get_stack_name(inst, stack_id)
        heat_reses = heat_client.get_resources(stack_name)
        # NOTE: Using json.loads because parameters['nfv'] is string
        nfv_dict = json.loads(heat_client.get_parameters(stack_name)['nfv'])

        op = grant_req.operation
        if op == v2fields.LcmOperationType.INSTANTIATE:
            flavour_id = req.flavourId
        else:
            flavour_id = inst.instantiatedVnfInfo.flavourId
        vim_key, vim_info = inst_utils.select_vim_info(
            inst.vimConnectionInfo, return_key=True)
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
                vimConnectionId=vim_key)

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
                if (server_res.get('parent_resource') ==
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

        self._update_vnfc_metadata(vnfc_res_infos, storage_infos,
                                   heat_client, nfv_dict, inst)

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
            if ((op == v2fields.LcmOperationType.CHANGE_EXT_CONN or
                 op == v2fields.LcmOperationType.CHANGE_VNFPKG) and
                    not is_rollback):
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
                vdu_idx = vnfc.metadata.get('vdu_idx', 0)
                creation_time = parser.isoparse(vnfc.metadata['creation_time'])
                return (vdu_idx, creation_time)

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
                for old_vnfc_info in old_vnfc_infos:
                    if old_vnfc_info.vnfcResourceInfoId == vnfc_res_info.id:
                        # re-use current object since
                        # vnfcConfigurableProperties may be set.
                        vnfc_info = old_vnfc_info
                        # metadata['VDU_VNFc_mapping'] may be changed
                        vnfc_info.id = self._make_vnfc_info_id(inst,
                                                               vnfc_res_info)
                        break
                if vnfc_info is None:
                    vnfc_info_id = self._make_vnfc_info_id(inst, vnfc_res_info)
                    vnfc_info = objects.VnfcInfoV2(
                        id=vnfc_info_id,
                        vduId=vnfc_res_info.vduId,
                        vnfcResourceInfoId=vnfc_res_info.id,
                        vnfcState='STARTED'
                    )
                vnfc_infos.append(vnfc_info)

            inst_vnf_info.vnfcInfo = vnfc_infos

        inst_vnf_info.metadata = {}
        # restore metadata
        if (inst.obj_attr_is_set('instantiatedVnfInfo') and
                inst.instantiatedVnfInfo.obj_attr_is_set('metadata')):
            inst_vnf_info.metadata.update(inst.instantiatedVnfInfo.metadata)

        # store stack_id and nfv parameters into metadata
        inst_vnf_info.metadata['stack_id'] = stack_id
        inst_vnf_info.metadata['nfv'] = nfv_dict
        # store tenant name for enhanced policy
        inst_vnf_info.metadata['tenant'] = vim_info.accessInfo.get('project')

        inst.instantiatedVnfInfo = inst_vnf_info
