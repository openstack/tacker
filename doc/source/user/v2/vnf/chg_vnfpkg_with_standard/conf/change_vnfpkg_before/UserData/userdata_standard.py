# Copyright (C) 2022 Nippon Telegraph and Telephone Corporation
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
import yaml

from tacker.sol_refactored.common import common_script_utils
from tacker.sol_refactored.common import vnf_instance_utils as inst_utils
from tacker.sol_refactored.infra_drivers.openstack import userdata_utils


def add_idx(name, index):
    return f'{name}-{index}'


def rm_idx(name_idx):
    return name_idx.rpartition('-')[0]


def add_idx_to_vdu_template(vdu_template, vdu_idx):
    """Add index to the third element of get_param

    ex. input VDU template:
    ---
    VDU1:
      type: VDU1.yaml
      properties:
        flavor: { get_param: [ nfv, VDU, VDU1, computeFlavourId ] }
        image-VDU1: { get_param: [ nfv, VDU, VDU1, vcImageId ] }
        net1: { get_param: [ nfv, CP, VDU1_CP1, network ] }
    ---

    output VDU template:
    ---
    VDU1:
      type: VDU1.yaml
      properties:
        flavor: { get_param: [ nfv, VDU, VDU1-1, computeFlavourId ] }
        image-VDU1: { get_param: [ nfv, VDU, VDU1-1, vcImageId ] }
        net1: { get_param: [ nfv, CP, VDU1_CP1-1, network ] }
    ---
    """
    res = copy.deepcopy(vdu_template)
    for prop_value in res.get('properties', {}).values():
        get_param = prop_value.get('get_param')
        if (get_param is not None and
                isinstance(get_param, list) and len(get_param) >= 4):
            get_param[2] = add_idx(get_param[2], vdu_idx)
    return res


def _get_new_cps_from_req(cps, req, grant):
    # used by change_ext_conn and change_vnfpkg
    new_cps = {}
    for cp_name_idx, cp_value in cps.items():
        cp_name = rm_idx(cp_name_idx)
        if 'network' in cp_value:
            network = common_script_utils.get_param_network(
                cp_name, grant, req)
            if network is None:
                continue
            new_cps.setdefault(cp_name_idx, {})
            new_cps[cp_name_idx]['network'] = network
        if 'fixed_ips' in cp_value:
            ext_fixed_ips = common_script_utils.get_param_fixed_ips(
                cp_name, grant, req)
            fixed_ips = []
            for i in range(len(ext_fixed_ips)):
                if i not in cp_value['fixed_ips']:
                    break
                ips_i = cp_value['fixed_ips'][i]
                if 'subnet' in ips_i:
                    ips_i['subnet'] = ext_fixed_ips[i].get('subnet')
                if 'ip_address' in ips_i:
                    ips_i['ip_address'] = ext_fixed_ips[i].get(
                        'ip_address')
                fixed_ips.append(ips_i)
            new_cps.setdefault(cp_name_idx, {})
            new_cps[cp_name_idx]['fixed_ips'] = fixed_ips

    return new_cps


def _merge_additional_params(nfv_dict, req, grant):
    if 'nfv' in req.get('additionalParams', {}):
        nfv_dict = inst_utils.json_merge_patch(
            nfv_dict, req['additionalParams']['nfv'])
    if 'nfv' in grant.get('additionalParams', {}):
        nfv_dict = inst_utils.json_merge_patch(
            nfv_dict, grant['additionalParams']['nfv'])
    return nfv_dict


class StandardUserData(userdata_utils.AbstractUserData):

    @staticmethod
    def instantiate(req, inst, grant_req, grant, tmp_csar_dir):
        vnfd = common_script_utils.get_vnfd(inst['vnfdId'], tmp_csar_dir)
        flavour_id = req['flavourId']

        hot_dict = vnfd.get_base_hot(flavour_id)
        top_hot = hot_dict['template']

        # first modify VDU resources
        popped_vdu = {}
        vdu_idxes = {}
        for vdu_name in vnfd.get_vdu_nodes(flavour_id).keys():
            popped_vdu[vdu_name] = top_hot.get('resources', {}).pop(vdu_name)
            vdu_idxes[vdu_name] = 0
        zones = {}
        for res in grant_req['addResources']:
            if res['type'] != 'COMPUTE':
                continue
            vdu_name = res['resourceTemplateId']
            if vdu_name not in popped_vdu:
                continue
            vdu_idx = vdu_idxes[vdu_name]
            vdu_idxes[vdu_name] += 1
            zones[add_idx(vdu_name, vdu_idx)] = (
                common_script_utils.get_param_zone_by_vnfc(
                    res['id'], grant))
            res = add_idx_to_vdu_template(popped_vdu[vdu_name], vdu_idx)
            top_hot['resources'][add_idx(vdu_name, vdu_idx)] = res

        nfv_dict = common_script_utils.init_nfv_dict(top_hot)

        vdus = nfv_dict.get('VDU', {})
        for vdu_name_idx, vdu_value in vdus.items():
            vdu_name = rm_idx(vdu_name_idx)
            if 'computeFlavourId' in vdu_value:
                vdu_value['computeFlavourId'] = (
                    common_script_utils.get_param_flavor(
                        vdu_name, flavour_id, vnfd, grant))
            if 'vcImageId' in vdu_value:
                vdu_value['vcImageId'] = common_script_utils.get_param_image(
                    vdu_name, flavour_id, vnfd, grant)
            if 'locationConstraints' in vdu_value:
                vdu_value['locationConstraints'] = zones[vdu_name_idx]

        cps = nfv_dict.get('CP', {})
        for cp_name, cp_value in cps.items():
            cp_name = rm_idx(cp_name)
            if 'network' in cp_value:
                cp_value['network'] = common_script_utils.get_param_network(
                    cp_name, grant, req)
            if 'fixed_ips' in cp_value:
                ext_fixed_ips = common_script_utils.get_param_fixed_ips(
                    cp_name, grant, req)
                fixed_ips = []
                for i in range(len(ext_fixed_ips)):
                    if i not in cp_value['fixed_ips']:
                        break
                    ips_i = cp_value['fixed_ips'][i]
                    if 'subnet' in ips_i:
                        ips_i['subnet'] = ext_fixed_ips[i].get('subnet')
                    if 'ip_address' in ips_i:
                        ips_i['ip_address'] = ext_fixed_ips[i].get(
                            'ip_address')
                    fixed_ips.append(ips_i)
                cp_value['fixed_ips'] = fixed_ips

        common_script_utils.apply_ext_managed_vls(top_hot, req, grant)
        nfv_dict = _merge_additional_params(nfv_dict, req, grant)

        fields = {
            'template': yaml.safe_dump(top_hot),
            'parameters': {'nfv': nfv_dict},
            'files': {}
        }
        for key, value in hot_dict.get('files', {}).items():
            fields['files'][key] = yaml.safe_dump(value)

        return fields

    @staticmethod
    def scale(req, inst, grant_req, grant, tmp_csar_dir):
        if req['type'] == 'SCALE_OUT':
            return StandardUserData._scale_out(req, inst, grant_req, grant,
                                              tmp_csar_dir)
        else:
            return StandardUserData._scale_in(req, inst, grant_req, grant,
                                             tmp_csar_dir)

    @staticmethod
    def _scale_out(req, inst, grant_req, grant, tmp_csar_dir):
        vnfd = common_script_utils.get_vnfd(inst['vnfdId'], tmp_csar_dir)
        flavour_id = inst['instantiatedVnfInfo']['flavourId']

        hot_dict = vnfd.get_base_hot(flavour_id)
        top_hot = hot_dict['template']

        # first modify VDU resources
        popped_vdu = {}
        vdu_idxes = {}
        for vdu_name in vnfd.get_vdu_nodes(flavour_id).keys():
            popped_vdu[vdu_name] = top_hot.get('resources', {}).pop(vdu_name)
            vdu_idxes[vdu_name] = common_script_utils.get_current_capacity(
                vdu_name, inst)

        zones = {}
        for res in grant_req['addResources']:
            if res['type'] != 'COMPUTE':
                continue
            vdu_name = res['resourceTemplateId']
            if vdu_name not in popped_vdu:
                continue
            vdu_idx = vdu_idxes[vdu_name]
            vdu_idxes[vdu_name] += 1
            zones[add_idx(vdu_name, vdu_idx)] = (
                common_script_utils.get_param_zone_by_vnfc(
                    res['id'], grant))
            res = add_idx_to_vdu_template(popped_vdu[vdu_name], vdu_idx)
            top_hot['resources'][add_idx(vdu_name, vdu_idx)] = res

        nfv_dict = common_script_utils.init_nfv_dict(top_hot)

        vdus = nfv_dict.get('VDU', {})
        for vdu_name_idx, vdu_value in vdus.items():
            vdu_name = rm_idx(vdu_name_idx)
            if 'computeFlavourId' in vdu_value:
                vdu_value['computeFlavourId'] = (
                    common_script_utils.get_param_flavor(
                        vdu_name, flavour_id, vnfd, grant))
            if 'vcImageId' in vdu_value:
                vdu_value['vcImageId'] = common_script_utils.get_param_image(
                    vdu_name, flavour_id, vnfd, grant)
            if 'locationConstraints' in vdu_value:
                vdu_value['locationConstraints'] = zones[vdu_name_idx]
            exclude_params = [param for param, value in vdu_value.items()
                              if value is None]
            for exclude_param in exclude_params:
                del vdu_value[exclude_param]

        cps = nfv_dict.get('CP', {})
        for cp_name, cp_value in cps.items():
            cp_name = rm_idx(cp_name)
            if 'network' in cp_value:
                cp_value['network'] = (
                    common_script_utils.get_param_network_from_inst(
                        cp_name, inst))
            if 'fixed_ips' in cp_value:
                ext_fixed_ips = (
                    common_script_utils.get_param_fixed_ips_from_inst(
                        cp_name, inst))
                fixed_ips = []
                for i in range(len(ext_fixed_ips)):
                    if i not in cp_value['fixed_ips']:
                        break
                    ips_i = cp_value['fixed_ips'][i]
                    if 'subnet' in ips_i:
                        ips_i['subnet'] = ext_fixed_ips[i].get('subnet')
                    if 'ip_address' in ips_i:
                        ips_i['ip_address'] = ext_fixed_ips[i].get(
                            'ip_address')
                    fixed_ips.append(ips_i)
                cp_value['fixed_ips'] = fixed_ips
            exclude_params = [param for param, value in cp_value.items()
                              if value is None]
            for exclude_param in exclude_params:
                del cp_value[exclude_param]

        common_script_utils.apply_ext_managed_vls_from_inst(top_hot, inst)
        nfv_dict = _merge_additional_params(nfv_dict, req, grant)

        fields = {
            'template': yaml.safe_dump(top_hot),
            'parameters': {'nfv': nfv_dict}
        }

        return fields

    @staticmethod
    def _scale_in(req, inst, grant_req, grant, tmp_csar_dir):
        template = {'resources': {}}

        for res in grant_req['removeResources']:
            if res['type'] != 'COMPUTE':
                continue
            for inst_vnfc in inst['instantiatedVnfInfo']['vnfcResourceInfo']:
                if (inst_vnfc['computeResource']['resourceId'] ==
                        res['resource']['resourceId']):
                    # must be found
                    vdu_idx = inst_vnfc['metadata']['vdu_idx']
                    break
            vdu_name = res['resourceTemplateId']
            template['resources'][add_idx(vdu_name, vdu_idx)] = None

        fields = {
            'template': yaml.safe_dump(template),
        }

        return fields

    @staticmethod
    def scale_rollback(req, inst, grant_req, grant, tmp_csar_dir):
        vnfd = common_script_utils.get_vnfd(inst['vnfdId'], tmp_csar_dir)
        flavour_id = inst['instantiatedVnfInfo']['flavourId']

        vdu_nodes = vnfd.get_vdu_nodes(flavour_id)
        vdu_idxes = {}
        for vdu_name in vdu_nodes.keys():
            vdu_idxes[vdu_name] = common_script_utils.get_current_capacity(
                vdu_name, inst)

        template = {'resources': {}}
        for res in grant_req['addResources']:
            if res['type'] != 'COMPUTE':
                continue
            vdu_name = res['resourceTemplateId']
            vdu_idx = vdu_idxes[vdu_name]
            vdu_idxes[vdu_name] += 1
            template['resources'][add_idx(vdu_name, vdu_idx)] = None

        fields = {
            'template': yaml.safe_dump(template),
        }

        return fields

    @staticmethod
    def change_ext_conn(req, inst, grant_req, grant, tmp_csar_dir):
        # change_ext_conn is interested in 'CP' only.
        # This method returns only 'CP' part in the 'nfv' dict from
        # ChangeExtVnfConnectivityRequest.
        # It is applied to json merge patch against the existing 'nfv'
        # dict by the caller.
        # NOTE: complete 'nfv' dict can not be made at the moment
        # since InstantiateVnfRequest is necessary to make it.

        vnfd = common_script_utils.get_vnfd(inst['vnfdId'], tmp_csar_dir)
        flavour_id = inst['instantiatedVnfInfo']['flavourId']

        hot_dict = vnfd.get_base_hot(flavour_id)
        top_hot = hot_dict['template']

        # first modify VDU resources
        popped_vdu = {}
        for vdu_name in vnfd.get_vdu_nodes(flavour_id).keys():
            popped_vdu[vdu_name] = top_hot.get('resources', {}).pop(vdu_name)

        for inst_vnfc in inst['instantiatedVnfInfo'].get(
                'vnfcResourceInfo', []):
            vdu_idx = inst_vnfc['metadata'].get('vdu_idx')
            if vdu_idx is None:
                continue
            vdu_name = inst_vnfc['vduId']
            res = add_idx_to_vdu_template(popped_vdu[vdu_name], vdu_idx)
            top_hot['resources'][add_idx(vdu_name, vdu_idx)] = res

        nfv_dict = common_script_utils.init_nfv_dict(top_hot)

        cps = nfv_dict.get('CP', {})
        new_cps = _get_new_cps_from_req(cps, req, grant)

        nfv_dict = _merge_additional_params({'CP': new_cps}, req, grant)
        fields = {'parameters': {'nfv': nfv_dict}}

        return fields

    @staticmethod
    def change_ext_conn_rollback(req, inst, grant_req, grant, tmp_csar_dir):
        fields = {
            'parameters': {
                'nfv': inst['instantiatedVnfInfo']['metadata']['nfv']
            }
        }

        return fields

    @staticmethod
    def heal(req, inst, grant_req, grant, tmp_csar_dir):
        vnfd = common_script_utils.get_vnfd(inst['vnfdId'], tmp_csar_dir)
        flavour_id = inst['instantiatedVnfInfo']['flavourId']

        vdus = inst['instantiatedVnfInfo']['metadata']['nfv'].get('VDU', {})
        for res in grant_req['removeResources']:
            if res['type'] != 'COMPUTE':
                continue
            for inst_vnfc in inst['instantiatedVnfInfo']['vnfcResourceInfo']:
                if (inst_vnfc['computeResource']['resourceId'] ==
                        res['resource']['resourceId']):
                    # must be found
                    vdu_name = inst_vnfc['vduId']
                    vdu_idx = inst_vnfc['metadata']['vdu_idx']
                    image = common_script_utils.get_param_image(
                        vdu_name, flavour_id, vnfd, grant, fallback_vnfd=False)
                    if image is not None:
                        vdus[add_idx(vdu_name, vdu_idx)]['vcImageId'] = image
                    break

        nfv_dict = _merge_additional_params({'VDU': vdus}, req, grant)
        fields = {'parameters': {'nfv': nfv_dict}}

        return fields

    @staticmethod
    def change_vnfpkg(req, inst, grant_req, grant, tmp_csar_dir):
        vnfd = common_script_utils.get_vnfd(grant_req['dstVnfdId'],
                                            tmp_csar_dir)
        flavour_id = inst['instantiatedVnfInfo']['flavourId']

        hot_dict = vnfd.get_base_hot(flavour_id)
        top_hot = hot_dict['template']

        # first modify VDU resources
        popped_vdu = {}
        for vdu_name in vnfd.get_vdu_nodes(flavour_id).keys():
            popped_vdu[vdu_name] = top_hot.get('resources', {}).pop(vdu_name)

        target_vnfc_res_ids = [
            res['resource']['resourceId']
            for res in grant_req['removeResources']
            if res['type'] == 'COMPUTE'
        ]

        cur_hot_reses = {}
        new_hot_reses = {}
        for inst_vnfc in inst['instantiatedVnfInfo']['vnfcResourceInfo']:
            vdu_idx = inst_vnfc['metadata'].get('vdu_idx')
            if vdu_idx is None:
                # should not be None. just check for consistency.
                continue
            vdu_name = inst_vnfc['vduId']
            vdu_name_idx = add_idx(vdu_name, vdu_idx)

            res = add_idx_to_vdu_template(popped_vdu[vdu_name], vdu_idx)
            top_hot['resources'][vdu_name_idx] = res

            if (inst_vnfc['computeResource']['resourceId'] in
                    target_vnfc_res_ids):
                new_hot_reses[vdu_name_idx] = res
            else:
                cur_hot_reses[vdu_name_idx] = res

        cur_nfv_dict = common_script_utils.init_nfv_dict(
            {'resources': cur_hot_reses})
        new_nfv_dict = common_script_utils.init_nfv_dict(
            {'resources': new_hot_reses})
        new_vdus = new_nfv_dict.get('VDU', {})
        vdus = inst['instantiatedVnfInfo']['metadata']['nfv'].get('VDU', {})

        for vdu_name_idx, vdu_value in new_vdus.items():
            vdu_name = rm_idx(vdu_name_idx)
            if 'computeFlavourId' in vdu_value:
                vdus[vdu_name_idx]['computeFlavourId'] = (
                    common_script_utils.get_param_flavor(
                        vdu_name, flavour_id, vnfd, grant))
            if 'vcImageId' in vdu_value:
                vdus[vdu_name_idx]['vcImageId'] = (
                    common_script_utils.get_param_image(
                        vdu_name, flavour_id, vnfd, grant))

        cps = cur_nfv_dict.get('CP', {})
        cps.update(new_nfv_dict.get('CP', {}))
        # NOTE: req includes only different part. some CPs in new_nfv_dict
        # may be necessary to get from inst.
        cur_cps = inst['instantiatedVnfInfo']['metadata']['nfv'].get('CP', {})
        req_cps = _get_new_cps_from_req(cps, req, grant)
        for cp_name in cps.keys():
            if cp_name in req_cps:
                cps[cp_name] = req_cps[cp_name]
            else:
                cps[cp_name] = cur_cps[cp_name]

        common_script_utils.apply_ext_managed_vls(top_hot, req, grant)

        nfv_dict = _merge_additional_params({'VDU': vdus, 'CP': cps},
                                            req, grant)

        fields = {
            'template': yaml.safe_dump(top_hot),
            'parameters': {'nfv': nfv_dict},
            'files': {},
            'existing': False
        }
        for key, value in hot_dict.get('files', {}).items():
            fields['files'][key] = yaml.safe_dump(value)

        return fields

    @staticmethod
    def change_vnfpkg_rollback(req, inst, grant_req, grant, tmp_csar_dir):
        vnfd = common_script_utils.get_vnfd(inst['vnfdId'], tmp_csar_dir)
        flavour_id = inst['instantiatedVnfInfo']['flavourId']

        hot_dict = vnfd.get_base_hot(flavour_id)
        top_hot = hot_dict['template']

        # first modify VDU resources
        popped_vdu = {}
        for vdu_name in vnfd.get_vdu_nodes(flavour_id).keys():
            popped_vdu[vdu_name] = top_hot.get('resources', {}).pop(vdu_name)

        for inst_vnfc in inst['instantiatedVnfInfo']['vnfcResourceInfo']:
            vdu_idx = inst_vnfc['metadata'].get('vdu_idx')
            if vdu_idx is None:
                # should not be None. just check for consistency.
                continue
            vdu_name = inst_vnfc['vduId']
            vdu_name_idx = add_idx(vdu_name, vdu_idx)

            res = add_idx_to_vdu_template(popped_vdu[vdu_name], vdu_idx)
            top_hot['resources'][vdu_name_idx] = res

        common_script_utils.apply_ext_managed_vls(top_hot, req, grant)

        fields = {
            'template': yaml.safe_dump(top_hot),
            'parameters': {
                'nfv': inst['instantiatedVnfInfo']['metadata']['nfv']},
            'files': {},
            'existing': False
        }
        for key, value in hot_dict.get('files', {}).items():
            fields['files'][key] = yaml.safe_dump(value)

        return fields