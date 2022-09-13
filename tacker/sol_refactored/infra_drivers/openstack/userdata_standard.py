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


def _get_new_cps_from_inst(cps, inst):
    # used by change_ext_conn_rollback and change_vnfpkg_rollback
    new_cps = {}
    for cp_name_idx, cp_value in cps.items():
        cp_name = rm_idx(cp_name_idx)
        if 'network' in cp_value:
            network = common_script_utils.get_param_network_from_inst(
                cp_name, inst)
            if network is None:
                continue
            new_cps.setdefault(cp_name_idx, {})
            new_cps[cp_name_idx]['network'] = network
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
            new_cps.setdefault(cp_name_idx, {})
            new_cps[cp_name_idx]['fixed_ips'] = fixed_ips

    return new_cps


class StandardUserData(userdata_utils.AbstractUserData):

    @staticmethod
    def instantiate(req, inst, grant_req, grant, tmp_csar_dir):
        vnfd = common_script_utils.get_vnfd(inst['vnfdId'], tmp_csar_dir)
        flavour_id = req['flavourId']

        hot_dict = vnfd.get_base_hot(flavour_id)
        top_hot = hot_dict['template']

        # first modify VDU resources
        poped_vdu = {}
        vdu_idxes = {}
        for vdu_name in vnfd.get_vdu_nodes(flavour_id).keys():
            poped_vdu[vdu_name] = top_hot.get('resources', {}).pop(vdu_name)
            vdu_idxes[vdu_name] = 0

        for res in grant_req['addResources']:
            if res['type'] != 'COMPUTE':
                continue
            vdu_name = res['resourceTemplateId']
            if vdu_name not in poped_vdu:
                continue
            vdu_idx = vdu_idxes[vdu_name]
            vdu_idxes[vdu_name] += 1
            res = add_idx_to_vdu_template(poped_vdu[vdu_name], vdu_idx)
            top_hot['resources'][add_idx(vdu_name, vdu_idx)] = res

        nfv_dict = common_script_utils.init_nfv_dict(top_hot)

        vdus = nfv_dict.get('VDU', {})
        for vdu_name, vdu_value in vdus.items():
            vdu_name = rm_idx(vdu_name)
            if 'computeFlavourId' in vdu_value:
                vdu_value['computeFlavourId'] = (
                    common_script_utils.get_param_flavor(
                        vdu_name, flavour_id, vnfd, grant))
            if 'vcImageId' in vdu_value:
                vdu_value['vcImageId'] = common_script_utils.get_param_image(
                    vdu_name, flavour_id, vnfd, grant)
            if 'locationConstraints' in vdu_value:
                vdu_value['locationConstraints'] = (
                    common_script_utils.get_param_zone(
                        vdu_name, grant_req, grant))

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

        if 'nfv' in req.get('additionalParams', {}):
            nfv_dict = inst_utils.json_merge_patch(nfv_dict,
                    req['additionalParams']['nfv'])
        if 'nfv' in grant.get('additionalParams', {}):
            nfv_dict = inst_utils.json_merge_patch(nfv_dict,
                    grant['additionalParams']['nfv'])

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
        poped_vdu = {}
        vdu_idxes = {}
        for vdu_name in vnfd.get_vdu_nodes(flavour_id).keys():
            poped_vdu[vdu_name] = top_hot.get('resources', {}).pop(vdu_name)
            vdu_idxes[vdu_name] = common_script_utils.get_current_capacity(
                vdu_name, inst)

        for res in grant_req['addResources']:
            if res['type'] != 'COMPUTE':
                continue
            vdu_name = res['resourceTemplateId']
            if vdu_name not in poped_vdu:
                continue
            vdu_idx = vdu_idxes[vdu_name]
            vdu_idxes[vdu_name] += 1
            res = add_idx_to_vdu_template(poped_vdu[vdu_name], vdu_idx)
            top_hot['resources'][add_idx(vdu_name, vdu_idx)] = res

        nfv_dict = common_script_utils.init_nfv_dict(top_hot)

        vdus = nfv_dict.get('VDU', {})
        for vdu_name, vdu_value in vdus.items():
            vdu_name = rm_idx(vdu_name)
            if 'computeFlavourId' in vdu_value:
                vdu_value['computeFlavourId'] = (
                    common_script_utils.get_param_flavor(
                        vdu_name, flavour_id, vnfd, grant))
            if 'vcImageId' in vdu_value:
                vdu_value['vcImageId'] = common_script_utils.get_param_image(
                    vdu_name, flavour_id, vnfd, grant)
            if 'locationConstraints' in vdu_value:
                vdu_value['locationConstraints'] = (
                    common_script_utils.get_param_zone(
                        vdu_name, grant_req, grant))

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

        fields = {
            'template': yaml.safe_dump(top_hot),
            'parameters': {'nfv': nfv_dict}
        }

        return fields

    @staticmethod
    def _scale_in(req, inst, grant_req, grant, tmp_csar_dir):
        vnfd = common_script_utils.get_vnfd(inst['vnfdId'], tmp_csar_dir)
        flavour_id = inst['instantiatedVnfInfo']['flavourId']

        vdu_nodes = vnfd.get_vdu_nodes(flavour_id)
        template = {'resources': {}}
        vdus = {}
        cps = {}
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
            vdus[add_idx(vdu_name, vdu_idx)] = None

            for str_name in vnfd.get_vdu_storages(vdu_nodes[vdu_name]):
                # may overspec, but no problem
                vdus[add_idx(str_name, vdu_idx)] = None

            for cp_name in vnfd.get_vdu_cps(flavour_id, vdu_name):
                # may overspec, but no problem
                cps[add_idx(cp_name, vdu_idx)] = None

        fields = {
            'template': yaml.safe_dump(template),
            'parameters': {'nfv': {'VDU': vdus, 'CP': cps}}
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
        vdus = {}
        cps = {}
        for res in grant_req['addResources']:
            if res['type'] != 'COMPUTE':
                continue
            vdu_name = res['resourceTemplateId']
            vdu_idx = vdu_idxes[vdu_name]
            vdu_idxes[vdu_name] += 1
            template['resources'][add_idx(vdu_name, vdu_idx)] = None
            vdus[add_idx(vdu_name, vdu_idx)] = None

            for str_name in vnfd.get_vdu_storages(vdu_nodes[vdu_name]):
                # may overspec, but no problem
                vdus[add_idx(str_name, vdu_idx)] = None

            for cp_name in vnfd.get_vdu_cps(flavour_id, vdu_name):
                # may overspec, but no problem
                cps[add_idx(cp_name, vdu_idx)] = None

        fields = {
            'template': yaml.safe_dump(template),
            'parameters': {'nfv': {'VDU': vdus, 'CP': cps}}
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
        poped_vdu = {}
        for vdu_name in vnfd.get_vdu_nodes(flavour_id).keys():
            poped_vdu[vdu_name] = top_hot.get('resources', {}).pop(vdu_name)

        for inst_vnfc in inst['instantiatedVnfInfo'].get(
                'vnfcResourceInfo', []):
            vdu_idx = inst_vnfc['metadata'].get('vdu_idx')
            if vdu_idx is None:
                continue
            vdu_name = inst_vnfc['vduId']
            res = add_idx_to_vdu_template(poped_vdu[vdu_name], vdu_idx)
            top_hot['resources'][add_idx(vdu_name, vdu_idx)] = res

        nfv_dict = common_script_utils.init_nfv_dict(top_hot)

        cps = nfv_dict.get('CP', {})
        new_cps = _get_new_cps_from_req(cps, req, grant)

        fields = {'parameters': {'nfv': {'CP': new_cps}}}

        return fields

    @staticmethod
    def change_ext_conn_rollback(req, inst, grant_req, grant, tmp_csar_dir):
        vnfd = common_script_utils.get_vnfd(inst['vnfdId'], tmp_csar_dir)
        flavour_id = inst['instantiatedVnfInfo']['flavourId']

        hot_dict = vnfd.get_base_hot(flavour_id)
        top_hot = hot_dict['template']

        # first modify VDU resources
        poped_vdu = {}
        for vdu_name in vnfd.get_vdu_nodes(flavour_id).keys():
            poped_vdu[vdu_name] = top_hot.get('resources', {}).pop(vdu_name)

        for inst_vnfc in inst['instantiatedVnfInfo'].get(
                'vnfcResourceInfo', []):
            vdu_idx = inst_vnfc['metadata'].get('vdu_idx')
            if vdu_idx is None:
                continue
            vdu_name = inst_vnfc['vduId']
            res = add_idx_to_vdu_template(poped_vdu[vdu_name], vdu_idx)
            top_hot['resources'][add_idx(vdu_name, vdu_idx)] = res

        nfv_dict = common_script_utils.init_nfv_dict(top_hot)

        cps = nfv_dict.get('CP', {})
        new_cps = _get_new_cps_from_inst(cps, inst)

        fields = {'parameters': {'nfv': {'CP': new_cps}}}

        return fields

    @staticmethod
    def heal(req, inst, grant_req, grant, tmp_csar_dir):
        # It is not necessary to change parameters at heal basically.

        fields = {'parameters': {'nfv': {}}}

        return fields

    @staticmethod
    def change_vnfpkg(req, inst, grant_req, grant, tmp_csar_dir):
        vnfd = common_script_utils.get_vnfd(grant_req['dstVnfdId'],
                                            tmp_csar_dir)
        flavour_id = inst['instantiatedVnfInfo']['flavourId']

        hot_dict = vnfd.get_base_hot(flavour_id)
        top_hot = hot_dict['template']

        # first modify VDU resources
        poped_vdu = {}
        for vdu_name in vnfd.get_vdu_nodes(flavour_id).keys():
            poped_vdu[vdu_name] = top_hot.get('resources', {}).pop(vdu_name)

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
            res = add_idx_to_vdu_template(poped_vdu[vdu_name], vdu_idx)
            top_hot['resources'][add_idx(vdu_name, vdu_idx)] = res

        nfv_dict = common_script_utils.init_nfv_dict(top_hot)

        vdus = nfv_dict.get('VDU', {})
        for vdu_name, vdu_value in vdus.items():
            vdu_name = rm_idx(vdu_name)
            if 'computeFlavourId' in vdu_value:
                vdu_value['computeFlavourId'] = (
                    common_script_utils.get_param_flavor(
                        vdu_name, flavour_id, vnfd, grant))
            if 'vcImageId' in vdu_value:
                vdu_value['vcImageId'] = common_script_utils.get_param_image(
                    vdu_name, flavour_id, vnfd, grant)
            if 'locationConstraints' in vdu_value:
                vdu_value.pop('locationConstraints')

        cps = nfv_dict.get('CP', {})
        new_cps = _get_new_cps_from_req(cps, req, grant)

        fields = {
            'parameters': {'nfv': {'VDU': vdus, 'CP': new_cps}}
        }

        return fields

    @staticmethod
    def change_vnfpkg_rollback(req, inst, grant_req, grant, tmp_csar_dir):
        vnfd = common_script_utils.get_vnfd(inst['vnfdId'], tmp_csar_dir)
        flavour_id = inst['instantiatedVnfInfo']['flavourId']

        hot_dict = vnfd.get_base_hot(flavour_id)
        top_hot = hot_dict['template']

        # first modify VDU resources
        poped_vdu = {}
        for vdu_name in vnfd.get_vdu_nodes(flavour_id).keys():
            poped_vdu[vdu_name] = top_hot.get('resources', {}).pop(vdu_name)

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
            res = add_idx_to_vdu_template(poped_vdu[vdu_name], vdu_idx)
            top_hot['resources'][add_idx(vdu_name, vdu_idx)] = res

        nfv_dict = common_script_utils.init_nfv_dict(top_hot)

        images = {}
        flavors = {}
        for inst_vnfc in inst['instantiatedVnfInfo']['vnfcResourceInfo']:
            vdu_idx = inst_vnfc['metadata'].get('vdu_idx')
            if vdu_idx is None:
                continue
            vdu_name = inst_vnfc['vduId']
            if vdu_name in flavors:
                continue
            for key, value in inst_vnfc['metadata'].items():
                if key == 'flavor':
                    flavors[add_idx(vdu_name, vdu_idx)] = value
                elif key.startswith('image-'):
                    image_vdu = key.replace('image-', '')
                    images[image_vdu] = value

        vdus = nfv_dict.get('VDU', {})
        new_vdus = {}
        for vdu_name, vdu_value in vdus.items():
            if 'computeFlavourId' in vdu_value:
                new_vdus.setdefault(vdu_name, {})
                new_vdus[vdu_name]['computeFlavourId'] = flavors.get(vdu_name)
            if 'vcImageId' in vdu_value:
                new_vdus.setdefault(vdu_name, {})
                new_vdus[vdu_name]['vcImageId'] = images.get(vdu_name)

        cps = nfv_dict.get('CP', {})
        new_cps = _get_new_cps_from_inst(cps, inst)

        fields = {
            'parameters': {'nfv': {'VDU': new_vdus, 'CP': new_cps}}
        }

        return fields
