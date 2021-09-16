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

import abc

from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.common import vnfd_utils


class AbstractUserData(metaclass=abc.ABCMeta):

    @staticmethod
    @abc.abstractmethod
    def instantiate(req, inst, grant_req, grant, tmp_csar_dir):
        """Definition of instantiate method

        Args:
            req: InstantiateVnfRequest dict
            inst: VnfInstance dict
            grant_req: GrantRequest dict
            grant: Grant dict
            tmp_csar_dir: directory path that csar contents are extracted

        Returns:
            dict of parameters for create heat stack.
            see the example of userdata_default.py.
        """
        raise sol_ex.UserDataClassNotImplemented()


def get_vnfd(vnfd_id, csar_dir):
    vnfd = vnfd_utils.Vnfd(vnfd_id)
    vnfd.init_from_csar_dir(csar_dir)
    return vnfd


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

    # TODO(oda-g): enhance to handle list
    # NOTE: List is not considered here and only 'fixed_ips' is treated as
    # list in userdata_default.py at the moment.
    # Note that if handling list is enhanced, userdata_default.py is
    # necessary to modify.
    return nfv


def get_param_flavor(vdu_name, req, vnfd, grant):
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
    return vnfd.get_compute_flavor(req['flavourId'], vdu_name)


def get_param_image(vdu_name, req, vnfd, grant):
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
    sw_images = vnfd.get_sw_image(req['flavourId'])
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
