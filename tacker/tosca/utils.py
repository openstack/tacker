# Copyright 2016 - Nokia
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
import re
import yaml

from collections import OrderedDict
from oslo_log import log as logging
from oslo_utils import uuidutils

from tacker.common import log
from tacker.common import utils
from tacker.extensions import vnfm
from toscaparser.utils import yamlparser


LOG = logging.getLogger(__name__)

ETSI_INST_LEVEL = 'tosca.policies.nfv.InstantiationLevels'
ETSI_SCALING_ASPECT = 'tosca.policies.nfv.ScalingAspects'
ETSI_SCALING_ASPECT_DELTA = 'tosca.policies.nfv.VduScalingAspectDeltas'
ETSI_INITIAL_DELTA = 'tosca.policies.nfv.VduInitialDelta'
HEAT_SOFTWARE_CONFIG = 'OS::Heat::SoftwareConfig'
SCALE_GROUP_RESOURCE = "OS::Heat::AutoScalingGroup"


@log.log
def check_for_substitution_mappings(template, params):
    sm_dict = params.get('substitution_mappings', {})
    requirements = sm_dict.get('requirements')
    node_tpl = template['topology_template']['node_templates']
    req_dict_tpl = template['topology_template']['substitution_mappings'].get(
        'requirements')
    # Check if substitution_mappings and requirements are empty in params but
    # not in template. If True raise exception
    if (not sm_dict or not requirements) and req_dict_tpl:
        raise vnfm.InvalidParamsForSM()
    # Check if requirements are present for SM in template, if True then return
    elif (not sm_dict or not requirements) and not req_dict_tpl:
        return
    del params['substitution_mappings']
    for req_name, req_val in (req_dict_tpl).items():
        if req_name not in requirements:
            raise vnfm.SMRequirementMissing(requirement=req_name)
        if not isinstance(req_val, list):
            raise vnfm.InvalidSubstitutionMapping(requirement=req_name)
        try:
            node_name = req_val[0]
            node_req = req_val[1]

            node_tpl[node_name]['requirements'].append({
                node_req: {
                    'node': requirements[req_name]
                }
            })
            node_tpl[requirements[req_name]] = \
                sm_dict[requirements[req_name]]
        except Exception:
            raise vnfm.InvalidSubstitutionMapping(requirement=req_name)


@log.log
def convert_unsupported_res_prop(heat_dict, unsupported_res_prop):
    res_dict = heat_dict['resources']

    for res, attr in (res_dict).items():
        res_type = attr['type']
        if res_type in unsupported_res_prop:
            prop_dict = attr['properties']
            unsupported_prop_dict = unsupported_res_prop[res_type]
            unsupported_prop = set(prop_dict.keys()) & set(
                unsupported_prop_dict.keys())
            for prop in unsupported_prop:
                # some properties are just punted to 'value_specs'
                # property if they are incompatible
                new_prop = unsupported_prop_dict[prop]
                if new_prop == 'value_specs':
                    prop_dict.setdefault(new_prop, {})[
                        prop] = prop_dict.pop(prop)
                else:
                    prop_dict[new_prop] = prop_dict.pop(prop)


@log.log
def represent_odict(dump, tag, mapping, flow_style=None):
    value = []
    node = yaml.MappingNode(tag, value, flow_style=flow_style)
    if dump.alias_key is not None:
        dump.represented_objects[dump.alias_key] = node
    best_style = True
    if hasattr(mapping, 'items'):
        mapping = mapping.items()
    for item_key, item_value in mapping:
        node_key = dump.represent_data(item_key)
        node_value = dump.represent_data(item_value)
        if not (isinstance(node_key, yaml.ScalarNode) and not node_key.style):
            best_style = False
        if not (isinstance(node_value, yaml.ScalarNode)
                and not node_value.style):
            best_style = False
        value.append((node_key, node_value))
    if flow_style is None:
        if dump.default_flow_style is not None:
            node.flow_style = dump.default_flow_style
        else:
            node.flow_style = best_style
    return node


@log.log
def post_process_heat_template(heat_tpl,
                               unsupported_res_prop=None, unique_id=None,
                               inst_req_info=None, grant_info=None,
                               tosca=None):
    #
    # TODO(bobh) - remove when heat-translator can support literal strings.
    #
    def fix_user_data(user_data_string):
        user_data_string = re.sub('user_data: #', 'user_data: |\n        #',
                                  user_data_string, re.MULTILINE)
        return re.sub('\n\n', '\n', user_data_string, re.MULTILINE)

    heat_tpl = fix_user_data(heat_tpl)
    #
    # End temporary workaround for heat-translator
    #
    heat_dict = yamlparser.simple_ordered_parse(heat_tpl)

    for res in heat_dict["resources"].values():
        if not res['type'] == HEAT_SOFTWARE_CONFIG:
            continue
        config = res["properties"]["config"]
        if 'get_file' in config:
            res["properties"]["config"] = open(config["get_file"]).read()

    if unsupported_res_prop:
        convert_unsupported_res_prop(heat_dict, unsupported_res_prop)
    if grant_info:
        convert_grant_info(heat_dict, grant_info)
    if inst_req_info:
        convert_inst_req_info(heat_dict, inst_req_info, tosca)

    if heat_dict.get('parameters') and heat_dict.get(
            'parameters', {}).get('vnfm_info'):
        heat_dict.get('parameters').get('vnfm_info').update(
            {'type': 'comma_delimited_list'})

    yaml.SafeDumper.add_representer(OrderedDict,
    lambda dumper, value: represent_odict(dumper,
                                          'tag:yaml.org,2002:map', value))

    return yaml.safe_dump(heat_dict)


@log.log
def post_process_heat_template_for_scaling(
    heat_tpl, unsupported_res_prop=None, unique_id=None,
    inst_req_info=None, grant_info=None,
        tosca=None):
    heat_dict = yamlparser.simple_ordered_parse(heat_tpl)
    if inst_req_info:
        check_inst_req_info_for_scaling(heat_dict, inst_req_info)
        convert_inst_req_info(heat_dict, inst_req_info, tosca)
    if grant_info:
        convert_grant_info(heat_dict, grant_info)

    yaml.SafeDumper.add_representer(OrderedDict,
    lambda dumper, value: represent_odict(dumper,
                                          'tag:yaml.org,2002:map', value))
    return yaml.safe_dump(heat_dict)


@log.log
def check_inst_req_info_for_scaling(heat_dict, inst_req_info):
    # Check whether fixed ip_address or mac_address is set in CP,
    # because CP with fixed IP address cannot be scaled.
    if not inst_req_info.ext_virtual_links:
        return

    def _get_mac_ip(ext_cp):
        mac = None
        ip = None
        for cp_conf in ext_cp.cp_config:
            if cp_conf.cp_protocol_data is None:
                continue

            for cp_protocol in cp_conf.cp_protocol_data:
                if cp_protocol.ip_over_ethernet is None:
                    continue

                mac = cp_protocol.ip_over_ethernet.mac_address
                for ip_address in \
                        cp_protocol.ip_over_ethernet.ip_addresses:
                    if ip_address.fixed_addresses:
                        ip = ip_address.fixed_addresses

        return mac, ip

    for ext_vl in inst_req_info.ext_virtual_links:
        ext_cps = ext_vl.ext_cps
        for ext_cp in ext_cps:
            if not ext_cp.cp_config:
                continue

            mac, ip = _get_mac_ip(ext_cp)

            cp_resource = heat_dict['resources'].get(ext_cp.cpd_id)
            if cp_resource is not None:
                if mac or ip:
                    raise vnfm.InvalidInstReqInfoForScaling()


@log.log
def convert_inst_req_info(heat_dict, inst_req_info, tosca):
    # Case which extVls is defined.
    ext_vl_infos = inst_req_info.ext_virtual_links
    if ext_vl_infos is not None:
        for ext_vl in ext_vl_infos:
            _convert_ext_vls(heat_dict, ext_vl)

    # Case which extMngVls is defined.
    ext_mng_vl_infos = inst_req_info.ext_managed_virtual_links

    if ext_mng_vl_infos is not None:
        for ext_mng_vl in ext_mng_vl_infos:
            _convert_ext_mng_vl(
                heat_dict, ext_mng_vl.vnf_virtual_link_desc_id,
                ext_mng_vl.resource_id)

    # Check whether instLevelId is defined.
    # Extract the initial number of scalable VDUs from the instantiation
    # policy.
    inst_level_id = inst_req_info.instantiation_level_id

    # The format of dict required to calculate desired_capacity are
    # shown below.
    # { aspectId: { deltaId: deltaNum }}
    aspect_delta_dict = {}
    # { aspectId: [ vduId ]}
    aspect_vdu_dict = {}
    # { instLevelId: { aspectId: levelNum }}
    inst_level_dict = {}
    # { aspectId: deltaId }
    aspect_id_dict = {}
    # { vduId: initialDelta }
    vdu_delta_dict = {}
    # { aspectId: maxScaleLevel }
    aspect_max_level_dict = {}

    tosca_policies = tosca.topology_template.policies
    default_inst_level_id = _extract_policy_info(
        tosca_policies, inst_level_dict,
        aspect_delta_dict, aspect_id_dict,
        aspect_vdu_dict, vdu_delta_dict,
        aspect_max_level_dict)

    if inst_level_id is not None:
        # Case which instLevelId is defined.
        _convert_desired_capacity(inst_level_id, inst_level_dict,
                                  aspect_delta_dict, aspect_id_dict,
                                  aspect_vdu_dict, vdu_delta_dict,
                                  heat_dict)
    elif inst_level_id is None and default_inst_level_id is not None:
        # Case which instLevelId is not defined.
        # In this case, use the default instLevelId.
        _convert_desired_capacity(default_inst_level_id, inst_level_dict,
                                  aspect_delta_dict, aspect_id_dict,
                                  aspect_vdu_dict, vdu_delta_dict,
                                  heat_dict)
    else:
        LOG.debug('Because instLevelId is not defined and '
                  'there is no default level in TOSCA, '
                  'the conversion of desired_capacity is skipped.')


@log.log
def convert_grant_info(heat_dict, grant_info):
    # Case which grant_info is defined.
    if not grant_info:
        return

    for vdu_name, vnf_resources in grant_info.items():
        _convert_grant_info_vdu(heat_dict, vdu_name, vnf_resources)


def _convert_ext_vls(heat_dict, ext_vl):
    ext_cps = ext_vl.ext_cps
    vl_id = ext_vl.resource_id
    defined_ext_link_ports = [ext_link_port.resource_handle.resource_id
            for ext_link_port in ext_vl.ext_link_ports]

    def _replace_external_network_port(link_port_id, cpd_id):
        for ext_link_port in ext_vl.ext_link_ports:
            if ext_link_port.id == link_port_id:
                if heat_dict['resources'].get(cpd_id) is not None:
                    _convert_ext_link_port(heat_dict, cpd_id,
                            ext_link_port.resource_handle.resource_id)

    for ext_cp in ext_cps:
        cp_resource = heat_dict['resources'].get(ext_cp.cpd_id)

        if cp_resource is None:
            return
        # Update CP network properties to NEUTRON NETWORK-UUID
        # defined in extVls.
        cp_resource['properties']['network'] = vl_id

        # Check whether extLinkPorts is defined.
        for cp_config in ext_cp.cp_config:
            for cp_protocol in cp_config.cp_protocol_data:
                # Update the following CP properties to the values defined
                # in extVls.
                # - subnet
                # - ip_address
                # - mac_address
                ip_over_ethernet = cp_protocol.ip_over_ethernet
                if ip_over_ethernet:
                    if ip_over_ethernet.mac_address or\
                            ip_over_ethernet.ip_addresses:
                        if ip_over_ethernet.mac_address:
                            cp_resource['properties']['mac_address'] =\
                                ip_over_ethernet.mac_address
                        if ip_over_ethernet.ip_addresses:
                            _convert_fixed_ips_list(
                                'ip_address',
                                ip_over_ethernet.ip_addresses,
                                cp_resource)
                elif defined_ext_link_ports:
                    _replace_external_network_port(cp_config.link_port_id,
                            ext_cp.cpd_id)


def _convert_fixed_ips_list(cp_key, cp_val, cp_resource):
    for val in cp_val:
        new_dict = {}
        if val.fixed_addresses:
            new_dict['ip_address'] = ''.join(val.fixed_addresses)
        if val.subnet_id:
            new_dict['subnet'] = val.subnet_id

        fixed_ips_list = cp_resource['properties'].get('fixed_ips')

        # Add if it doesn't exist yet.
        if fixed_ips_list is None:
            cp_resource['properties']['fixed_ips'] = [new_dict]
        # Update if it already exists.
        else:
            for index, fixed_ips in enumerate(fixed_ips_list):
                if fixed_ips.get(cp_key) is not None:
                    fixed_ips_list[index] = new_dict
                else:
                    fixed_ips_list.append(new_dict)
            sorted_list = sorted(fixed_ips_list)
            cp_resource['properties']['fixed_ips'] = sorted_list


def _convert_ext_link_port(heat_dict, cp_name, ext_link_port):
    # Delete CP resource and update VDU's properties
    # related to CP defined in extLinkPorts.
    del heat_dict['resources'][cp_name]
    for rsrc_info in heat_dict['resources'].values():
        if rsrc_info['type'] == 'OS::Nova::Server':
            vdu_networks = rsrc_info['properties']['networks']
            for index, vdu_network in enumerate(vdu_networks):
                if isinstance(vdu_network['port'], dict) and\
                        vdu_network['port'].get('get_resource') == cp_name:
                    new_dict = {'port': ext_link_port}
                    rsrc_info['properties']['networks'][index] = new_dict


def _convert_ext_mng_vl(heat_dict, vl_name, vl_id):
    # Delete resources related to VL defined in extMngVLs.
    if heat_dict['resources'].get(vl_name) is not None:
        del heat_dict['resources'][vl_name]
        del heat_dict['resources'][vl_name + '_subnet']
        del heat_dict['resources'][vl_name + '_qospolicy']
        del heat_dict['resources'][vl_name + '_bandwidth']

    for rsrc_info in heat_dict['resources'].values():
        # Update CP's properties related to VL defined in extMngVls.
        if rsrc_info['type'] == 'OS::Neutron::Port':
            cp_network = rsrc_info['properties']['network']
            if isinstance(cp_network, dict) and\
                    cp_network.get('get_resource') == vl_name:
                rsrc_info['properties']['network'] = vl_id
        # Update AutoScalingGroup's properties related to VL defined
        # in extMngVls.
        elif rsrc_info['type'] == 'OS::Heat::AutoScalingGroup':
            asg_rsrc_props = \
                rsrc_info['properties']['resource'].get('properties')
            for vl_key, vl_val in asg_rsrc_props.items():
                if vl_val.get('get_resource') == vl_name:
                    asg_rsrc_props[vl_key] = vl_id


def _extract_policy_info(tosca_policies, inst_level_dict,
                         aspect_delta_dict, aspect_id_dict,
                         aspect_vdu_dict, vdu_delta_dict,
                         aspect_max_level_dict):
    default_inst_level_id = None
    if tosca_policies:
        for p in tosca_policies:
            if p.type == ETSI_SCALING_ASPECT_DELTA:
                vdu_list = p.targets
                aspect_id = p.properties['aspect']
                deltas = p.properties['deltas']
                delta_id_dict = {}
                for delta_id, delta_val in deltas.items():
                    delta_num = delta_val['number_of_instances']
                    delta_id_dict[delta_id] = delta_num
                aspect_delta_dict[aspect_id] = delta_id_dict
                aspect_vdu_dict[aspect_id] = vdu_list

            elif p.type == ETSI_INST_LEVEL:
                inst_levels = p.properties['levels']
                for level_id, inst_val in inst_levels.items():
                    scale_info = inst_val['scale_info']
                    aspect_level_dict = {}
                    for aspect_id, scale_level in scale_info.items():
                        aspect_level_dict[aspect_id] = \
                            scale_level['scale_level']
                    inst_level_dict[level_id] = aspect_level_dict
                default_inst_level_id = p.properties.get('default_level')

            # On TOSCA definitions, step_deltas is list and
            # multiple description is possible,
            # but only single description is supported.
            # (first win)
            # Like heat-translator.
            elif p.type == ETSI_SCALING_ASPECT:
                aspects = p.properties['aspects']
                for aspect_id, aspect_val in aspects.items():
                    delta_names = aspect_val['step_deltas']
                    delta_name = delta_names[0]
                    aspect_id_dict[aspect_id] = delta_name
                    aspect_max_level_dict[aspect_id] = \
                        aspect_val['max_scale_level']
            elif p.type == ETSI_INITIAL_DELTA:
                vdus = p.targets
                initial_delta = \
                    p.properties['initial_delta']['number_of_instances']
                for vdu in vdus:
                    vdu_delta_dict[vdu] = initial_delta
    return default_inst_level_id


def _convert_desired_capacity(inst_level_id, inst_level_dict,
                              aspect_delta_dict, aspect_id_dict,
                              aspect_vdu_dict, vdu_delta_dict,
                              heat_dict):
    al_dict = inst_level_dict.get(inst_level_id)
    if al_dict is not None:
        # Get level_num.
        for aspect_id, level_num in al_dict.items():
            delta_id = aspect_id_dict.get(aspect_id)

            # Get delta_num.
            if delta_id is not None:
                delta_num = \
                    aspect_delta_dict.get(aspect_id).get(delta_id)

            # Get initial_delta.
            vdus = aspect_vdu_dict.get(aspect_id)
            initial_delta = None
            for vdu in vdus:
                initial_delta = vdu_delta_dict.get(vdu)

            if initial_delta is not None:
                # Calculate desired_capacity.
                desired_capacity = initial_delta + delta_num * level_num
                # Convert desired_capacity on HOT.
                for rsrc_key, rsrc_info in heat_dict['resources'].items():
                    if rsrc_info['type'] == 'OS::Heat::AutoScalingGroup' and \
                            rsrc_key == aspect_id:
                        rsrc_info['properties']['desired_capacity'] = \
                            desired_capacity
    else:
        LOG.warning('Because target instLevelId is not defined in TOSCA, '
                    'the conversion of desired_capacity is skipped.')
        pass


def _convert_grant_info_vdu(heat_dict, vdu_name, vnf_resources):
    for vnf_resource in vnf_resources:
        if vnf_resource.resource_type == "image":
            # Update VDU's properties related to
            # image defined in grant_info.
            vdu_info = heat_dict.get('resources').get(vdu_name)
            if vdu_info is not None:
                vdu_props = vdu_info.get('properties')
                if vdu_props.get('image') is None:
                    vdu_props.update({'image':
                        vnf_resource.resource_identifier})


@log.log
def get_scaling_group_dict(ht_template, scaling_policy_names):
    scaling_group_dict = dict()
    scaling_group_names = list()
    heat_dict = yamlparser.simple_ordered_parse(ht_template)
    for resource_name, resource_dict in heat_dict['resources'].items():
        if resource_dict['type'] == SCALE_GROUP_RESOURCE:
            scaling_group_names.append(resource_name)
    if scaling_group_names:
        scaling_group_dict[scaling_policy_names[0]] = scaling_group_names[0]
    return scaling_group_dict


def get_nested_resources_name(hot):
    nested_resource_names = []
    hot_yaml = yaml.safe_load(hot)
    for r_key, r_val in hot_yaml.get('resources').items():
        if r_val.get('type') == 'OS::Heat::AutoScalingGroup':
            nested_resource_name = r_val.get('properties', {}).get(
                'resource', {}).get('type', None)
            nested_resource_names.append(nested_resource_name)
    return nested_resource_names


def get_sub_heat_tmpl_name(tmpl_name):
    return uuidutils.generate_uuid() + tmpl_name


def update_nested_scaling_resources(nested_resources,
                                    unsupported_res_prop=None,
                                    grant_info=None, inst_req_info=None):
    nested_tpl = dict()
    yaml.SafeDumper.add_representer(
        OrderedDict, lambda dumper, value: represent_odict(
            dumper, 'tag:yaml.org,2002:map', value))
    for nested_resource_name, nested_resources_yaml in \
            nested_resources.items():
        nested_resources_dict =\
            yamlparser.simple_ordered_parse(nested_resources_yaml)
        convert_grant_info(nested_resources_dict, grant_info)

        # Replace external virtual links if specified in the inst_req_info
        if inst_req_info is not None:
            for ext_vl in inst_req_info.ext_virtual_links:
                _convert_ext_vls(nested_resources_dict, ext_vl)

        for res in nested_resources_dict["resources"].values():
            if not res['type'] == HEAT_SOFTWARE_CONFIG:
                continue
            config = res["properties"]["config"]
            if 'get_file' in config:
                res["properties"]["config"] = open(config["get_file"]).read()

        if unsupported_res_prop:
            convert_unsupported_res_prop(nested_resources_dict,
                                         unsupported_res_prop)

        nested_tpl[nested_resource_name] =\
            yaml.safe_dump(nested_resources_dict)

    return nested_tpl


def get_policies_from_dict(vnfd_dict, policy_type=None):
    final_policies = dict()
    policies = vnfd_dict.get('topology_template', {}).get('policies', {})
    for policy in policies:
        for policy_name, policy_dict in policy.items():
            if policy_type:
                if policy_dict.get('type') == policy_type:
                    final_policies.update({policy_name: policy_dict})
            else:
                final_policies.update({policy_name: policy_dict})
    return final_policies


@log.log
def get_scale_group(vnf_dict, vnfd_dict, inst_req_info):
    scaling_group_dict = dict()
    data_dict = dict()
    if vnf_dict['attributes'].get('scaling_group_names'):
        for policy_name, policy_dict in \
            get_policies_from_dict(vnfd_dict,
                ETSI_SCALING_ASPECT_DELTA).items():
            aspect = policy_dict['properties']['aspect']
            vdu = policy_dict['targets']
            deltas = policy_dict['properties']['deltas']
            for delta_key, delta_dict in deltas.items():
                num = delta_dict['number_of_instances']
            data_dict.update({
                aspect: {
                    'vdu': vdu,
                    'num': num
                }
            })

        for aspect_name, aspect_dict in data_dict.items():
            aspect_policy = \
                get_policies_from_dict(vnfd_dict, ETSI_SCALING_ASPECT)
            for policy_name, policy_dict in aspect_policy.items():
                aspect = policy_dict['properties']['aspects'][aspect_name]
                max_level = aspect.get('max_scale_level')
                data_dict[aspect_name].update({'maxLevel': max_level})

            delta_policy = \
                get_policies_from_dict(vnfd_dict, ETSI_INITIAL_DELTA)
            for policy_name, policy_dict in delta_policy.items():
                for target in policy_dict['targets']:
                    if target in aspect_dict['vdu']:
                        delta = policy_dict['properties']['initial_delta']
                        number_of_instances = delta['number_of_instances']
                        data_dict[aspect_name].update(
                            {'initialNum': number_of_instances})

            level_policy = \
                get_policies_from_dict(vnfd_dict, ETSI_INST_LEVEL)
            for policy_name, policy_dict in level_policy.items():

                instantiation_level_id = ""
                if hasattr(inst_req_info, 'instantiation_level_id'):
                    instantiation_level_id = \
                        inst_req_info.instantiation_level_id

                if not instantiation_level_id:
                    instantiation_level_id = \
                        policy_dict['properties']['default_level']

                levels = policy_dict['properties']['levels']
                scale_info = levels[instantiation_level_id]['scale_info']
                initial_level = scale_info[aspect_name]['scale_level']
                increase = aspect_dict['num'] * initial_level
                default = aspect_dict['initialNum'] + increase
                data_dict[aspect_name].update({'initialLevel': initial_level,
                                               'default': default})

        scaling_group_dict.update({'scaleGroupDict': data_dict})

    return scaling_group_dict


def tosca_tmpl_local_defs():
    """Return local defs for ToscaTemplate

    It's a remedy to avoid a failure for a busy access while importing remote
    definition in a TOSCA template. While instantiating a ToscaTemplate obj
    with given local_defs arg, it uses a local file instead of remote one by
    referring the local defs returned from this function. The returned value
    is a dict consists of entries of url and local path such as below.

    .. code-block:: python

        {
            "https://forge.etsi.org/.../aaa.yaml": "/path/to/aaa.yaml",
            "https://forge.etsi.org/.../bbb.yaml": "/path/to/bbb.yaml"
        }

    :return: A set of url and local file path as a dict
    """

    def sol001_url(ver, fname):
        baseurl = "https://forge.etsi.org/rep/nfv/SOL001"
        return os.path.join(baseurl, "raw", "v" + ver, fname)

    def path_sol001_def(ver, fname):
        """Return a path of specified ETSI's def file.

        The name of file given with `fname` follows the original repo
        https://forge.etsi.org/rep/nfv/SOL001.
        """

        fpath = os.path.join(utils.proj_root(), "etc", "etsi-nfv", "sol001",
                ver, fname)
        try:
            if os.path.isfile(fpath) is not True:
                raise FileNotFoundError
        except FileNotFoundError:
            LOG.error("No SOL001 def file found '%'", fpath)
        return fpath

    ldefs = {}
    # NOTE(yasufum): There are several updates made for each definitions under
    #     SOL001, but no all of versions are required for tests in tacker
    #     currently.
    # TODO(yasufum): Add all required defs for supporting several usecases
    #     although tacker uses just a few defs as below. We can find all the
    #     version in commits of SOL001's repo.
    fname = "etsi_nfv_sol001_common_types.yaml"
    def_ver = "2.6.1"
    k = sol001_url(def_ver, fname)
    v = path_sol001_def(def_ver, fname)
    ldefs[k] = v

    return ldefs
