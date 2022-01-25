# Copyright (C) 2022 Fujitsu
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

from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.common import vnfd_utils


def get_vnfd(vnfd_id, csar_dir):
    vnfd = vnfd_utils.Vnfd(vnfd_id)
    vnfd.init_from_csar_dir(csar_dir)
    return vnfd


def get_vdu_info(grant, inst, vnfd):
    volume_name = ''
    volume_size = ''
    flavour_id = inst['instantiatedVnfInfo']['flavourId']
    vdu_nodes = vnfd.get_vdu_nodes(flavour_id)
    storage_nodes = vnfd.get_storage_nodes(flavour_id)
    vdu_info_dict = {}
    for name, node in vdu_nodes.items():
        flavor = get_param_flavor(name, flavour_id, vnfd, grant)
        image = get_param_image(name, flavour_id, vnfd, grant)
        vdu_storage_names = vnfd.get_vdu_storages(node)
        for vdu_storage_name in vdu_storage_names:
            if storage_nodes[vdu_storage_name].get(
                    'properties', {}).get('sw_image_data'):
                image = get_param_image(vdu_storage_name, flavour_id, vnfd,
                                        grant)
                volume_name = vdu_storage_name
                volume_size = storage_nodes[vdu_storage_name].get(
                    'properties', {}).get(
                    'virtual_block_storage_data', '').get(
                    'size_of_storage', ''
                )
                volume_size = volume_size.rstrip(' GB')
                if not volume_size.isdigit():
                    raise sol_ex.VmRunningFailed(
                        error_info='The volume size set in VNFD is invalid.')
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


def init_nfv_dict(hot_template):
    get_params = []

    def _get_get_param(prop):
        if isinstance(prop, dict):
            for key, value in prop.items():
                if key == 'get_param':
                    get_params.append(value)
                else:
                    _get_get_param(value)
        elif isinstance(prop, list):
            for value in prop:
                _get_get_param(value)

    for res in hot_template.get('resources', {}).values():
        _get_get_param(res.get('properties', {}))

    nfv = {}

    for param in get_params:
        if (not isinstance(param, list) or len(param) < 4 or
                param[0] != 'nfv'):
            continue
        parent = nfv
        for item in param[1:-1]:
            parent.setdefault(item, {})
            parent = parent[item]
        parent[param[-1]] = None

    # TODO(YiFeng): enhance to handle list
    # NOTE: List is not considered here and only 'fixed_ips' is treated as
    # list in userdata_default.py at the moment.
    # Note that if handling list is enhanced, userdata_default.py is
    # necessary to modify.
    return nfv


def get_param_flavor(vdu_name, flavour_id, vnfd, grant):
    # try to get from grant
    if 'vimAssets' in grant:
        assets = grant['vimAssets']
        if 'computeResourceFlavours' in assets:
            flavours = assets['computeResourceFlavours']
            for flavour in flavours:
                if flavour['vnfdVirtualComputeDescId'] == vdu_name:
                    return flavour['vimFlavourId']

    # if specified in VNFD, use it
    # NOTE: if not found. parameter is set to None.
    #       may be error when stack create
    return vnfd.get_compute_flavor(flavour_id, vdu_name)


def get_param_image(vdu_name, flavour_id, vnfd, grant):
    # try to get from grant
    if 'vimAssets' in grant:
        assets = grant['vimAssets']
        if 'softwareImages' in assets:
            images = assets['softwareImages']
            for image in images:
                if image['vnfdSoftwareImageId'] == vdu_name:
                    return image['vimSoftwareImageId']

    # if specified in VNFD, use it
    # NOTE: if not found. parameter is set to None.
    #       may be error when stack create
    sw_images = vnfd.get_sw_image(flavour_id)
    for name, image in sw_images.items():
        if name == vdu_name:
            return image


def get_param_zone(vdu_name, grant_req, grant):
    if 'zones' not in grant or 'addResources' not in grant:
        return

    for res in grant['addResources']:
        if 'zoneId' not in res:
            continue
        for req_res in grant_req['addResources']:
            if req_res['id'] == res['resourceDefinitionId']:
                if req_res.get('resourceTemplateId') == vdu_name:
                    for zone in grant['zones']:
                        if zone['id'] == res['zoneId']:  # must be found
                            return zone['zoneId']


def get_current_capacity(vdu_name, inst):
    count = 0
    inst_vnfcs = (inst.get('instantiatedVnfInfo', {})
                      .get('vnfcResourceInfo', []))
    for inst_vnfc in inst_vnfcs:
        if inst_vnfc['vduId'] == vdu_name:
            count += 1

    return count


def get_param_capacity(vdu_name, inst, grant_req):
    # NOTE: refer grant_req here since interpretation of VNFD was done when
    # making grant_req.
    count = get_current_capacity(vdu_name, inst)

    add_reses = grant_req.get('addResources', [])
    for res_def in add_reses:
        if (res_def['type'] == 'COMPUTE' and
                res_def['resourceTemplateId'] == vdu_name):
            count += 1

    rm_reses = grant_req.get('removeResources', [])
    for res_def in rm_reses:
        if (res_def['type'] == 'COMPUTE' and
                res_def['resourceTemplateId'] == vdu_name):
            count -= 1

    return count


def _get_fixed_ips_from_extcp(extcp):
    fixed_ips = []
    for cp_conf in extcp['cpConfig'].values():
        if 'cpProtocolData' not in cp_conf:
            continue
        for prot_data in cp_conf['cpProtocolData']:
            if 'ipOverEthernet' not in prot_data:
                continue
            if 'ipAddresses' not in prot_data['ipOverEthernet']:
                continue
            for ip in prot_data['ipOverEthernet']['ipAddresses']:
                data = {}
                if 'fixedAddresses' in ip:
                    # pick up only one ip address
                    data['ip_address'] = str(ip['fixedAddresses'][0])
                if 'subnetId' in ip:
                    data['subnet'] = ip['subnetId']
                if data:
                    fixed_ips.append(data)
    return fixed_ips


def get_param_network(cp_name, grant, req):
    # see grant first then instantiateVnfRequest
    vls = grant.get('extVirtualLinks', []) + req.get('extVirtualLinks', [])
    for vl in vls:
        for extcp in vl['extCps']:
            if extcp['cpdId'] == cp_name:
                return vl['resourceId']


def get_param_fixed_ips(cp_name, grant, req):
    # see grant first then instantiateVnfRequest
    vls = grant.get('extVirtualLinks', []) + req.get('extVirtualLinks', [])
    for vl in vls:
        for extcp in vl['extCps']:
            if extcp['cpdId'] == cp_name:
                return _get_fixed_ips_from_extcp(extcp)


def get_param_network_from_inst(cp_name, inst):
    for vl in inst['instantiatedVnfInfo'].get('extVirtualLinkInfo', []):
        for extcp in vl.get('currentVnfExtCpData', []):
            if extcp['cpdId'] == cp_name:
                return vl['resourceHandle']['resourceId']


def get_param_fixed_ips_from_inst(cp_name, inst):
    for vl in inst['instantiatedVnfInfo'].get('extVirtualLinkInfo', []):
        for extcp in vl.get('currentVnfExtCpData', []):
            if extcp['cpdId'] == cp_name:
                return _get_fixed_ips_from_extcp(extcp)


def apply_ext_managed_vls(hot_dict, req, grant):
    # see grant first then instantiateVnfRequest
    mgd_vls = (grant.get('extManagedVirtualLinks', []) +
               req.get('extManagedVirtualLinks', []))

    # NOTE: refer HOT only here, not refer VNFD.
    # HOT and VNFD must be consistent.

    for mgd_vl in mgd_vls:
        vl_name = mgd_vl['vnfVirtualLinkDescId']
        network_id = mgd_vl['resourceId']
        get_res = {'get_resource': vl_name}

        def _change(item):
            if not isinstance(item, dict):
                return
            for key, value in item.items():
                if value == get_res:
                    item[key] = network_id
                else:
                    _change(value)

        del_reses = []
        for res_name, res_data in hot_dict.get('resources', {}).items():
            # delete network definition
            if res_name == vl_name:
                del_reses.append(res_name)

            # delete subnet definition
            if res_data['type'] == 'OS::Neutron::Subnet':
                net = (res_data.get('properties', {})
                               .get('network', {})
                               .get('get_resource'))
                if net == vl_name:
                    del_reses.append(res_name)

            # change '{get_resource: vl_name}' to network_id
            _change(res_data)

        for res_name in del_reses:
            hot_dict['resources'].pop(res_name)
