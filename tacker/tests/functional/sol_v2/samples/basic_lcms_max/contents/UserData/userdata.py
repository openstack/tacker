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

import yaml

from tacker.sol_refactored.common import common_script_utils
from tacker.sol_refactored.common import vnf_instance_utils as inst_utils
from tacker.sol_refactored.infra_drivers.openstack import userdata_utils


class UserData(userdata_utils.AbstractUserData):

    @staticmethod
    def instantiate(req, inst, grant_req, grant, tmp_csar_dir):
        def _get_param_port(cp_name, grant, req):
            # see grant first then instantiateVnfRequest
            vls = grant.get('extVirtualLinks', []) + req.get('extVirtualLinks',
                                                             [])
            port_ids = []
            for vl in vls:
                link_port_ids = []
                for extcp in vl['extCps']:
                    if extcp['cpdId'] == cp_name:
                        link_port_ids = _get_link_port_ids_from_extcp(extcp)
                if 'extLinkPorts' not in vl:
                    continue
                for extlp in vl['extLinkPorts']:
                    if extlp['id'] in link_port_ids:
                        port_ids.append(extlp['resourceHandle']['resourceId'])
            return port_ids

        def _get_link_port_ids_from_extcp(extcp):
            link_port_ids = []
            for cp_conf in extcp['cpConfig'].values():
                if 'linkPortId' in cp_conf:
                    link_port_ids.append(cp_conf['linkPortId'])
            return link_port_ids

        vnfd = common_script_utils.get_vnfd(inst['vnfdId'], tmp_csar_dir)
        flavour_id = req['flavourId']

        hot_dict = vnfd.get_base_hot(flavour_id)
        top_hot = hot_dict['template']

        nfv_dict = common_script_utils.init_nfv_dict(top_hot)

        vdus = nfv_dict.get('VDU', {})
        for vdu_name, vdu_value in vdus.items():
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
            if 'desired_capacity' in vdu_value:
                vdu_value['desired_capacity'] = (
                    common_script_utils.get_param_capacity(
                        vdu_name, inst, grant_req))

        cps = nfv_dict.get('CP', {})
        for cp_name, cp_value in cps.items():
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
            # NOTE: In the case where multiple cpConfigs corresponding
            # to a single cpdId are defined, always get the first element
            # of cpConfig. This is because, according to the current
            # SOL definitions, the key of cpConfig is the ID managed by
            # the API consumer, and it is not possible to uniquely determine
            # which element of cpConfig should be selected by cpdId.
            # See SOL003 v3.3.1 4.4.1.10 Type: VnfExtCpData.
            if 'port' in cp_value:
                cp_value['port'] = _get_param_port(
                    cp_name, grant, req).pop()

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
