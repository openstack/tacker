#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import copy

from oslo_log import log as logging
from tacker.common.utils import MemoryUnit


"""Define util functions that can be used in UserData.

As for how to use the function (`create _ * _ dict`), dict can be obtained
as a return value by setting the required arguments and calling.
For detailed usage, check the docstring of each function.

NOTE: The functions defined here are limited to common and basic ones.
Please note that not all conversion logics are offered in Tacker,
different from Heat-Translator.
"""

LOG = logging.getLogger(__name__)

HOT_NOVA_SERVER = 'OS::Nova::Server'
HOT_NOVA_FLAVOR = 'OS::Nova::Flavor'
HOT_NEUTRON_PORT = 'OS::Neutron::Port'
AUTO_SCALING_GROUP = 'OS::Heat::AutoScalingGroup'
HOT_CINDER_VOLUME = 'OS::Cinder::Volume'
SUPPORTED_HOT_TYPE = [HOT_NOVA_SERVER, HOT_NOVA_FLAVOR,
                      HOT_NEUTRON_PORT, HOT_CINDER_VOLUME]
PORT_SERVER_TYPE = [HOT_NOVA_SERVER, HOT_NEUTRON_PORT, HOT_CINDER_VOLUME]


def create_initial_param_dict(base_hot_dict):
    """Create initial dict containing information about get_param resources.

    :param base_hot_dict: dict(Base HOT dict format)
    :return: dict('nfv', Initial HOT resource dict)

    NOTE: 'nfv' is a fixed value for 1st element.
          'VDU' and 'CP' are supported for 2nd element.
          3rd and 4th element are mandatory.
    """
    initial_param_dict = {
        'nfv': {
            'VDU': {
            },
            'CP': {
            }
        }
    }

    for hot_dict in base_hot_dict.values():
        param_nfv = hot_dict.get('parameters', {}).get('nfv')
        if not param_nfv:
            continue
        resources = hot_dict.get('resources', {})
        for resource_name, resource_val in resources.items():
            resource_type = resource_val.get('type')
            if resource_type in SUPPORTED_HOT_TYPE:
                resource_props = resource_val.get('properties', {})
                for prop_key, prop_val in resource_props.items():
                    if isinstance(prop_val, dict) and 'get_param' in prop_val:
                        param_list = prop_val['get_param']
                        if len(param_list) == 4:
                            resource_info = initial_param_dict.get(
                                param_list[0], {}).get(
                                    param_list[1], {})
                            if param_list[2] not in resource_info:
                                resource_info[param_list[2]] = {}
                if resource_type == HOT_NOVA_SERVER:
                    cinder_boot = resource_props.get('block_device_mapping_v2',
                                                     {})
                    if cinder_boot:
                        for boot in cinder_boot:
                            b_param = boot.get('image')
                            if b_param and \
                               isinstance(b_param, dict) and \
                               'get_param' in b_param:
                                param_list = b_param['get_param']
                                if len(param_list) == 4:
                                    resource_info = initial_param_dict.get(
                                        param_list[0], {}).get(
                                            param_list[1], {})
                                    if param_list[2] not in resource_info:
                                        resource_info[param_list[2]] = {}
            elif resource_type == AUTO_SCALING_GROUP:
                resource_nest = resource_val.get('properties').get('resource')
                resource_props = resource_nest.get('properties', {})
                for prop_key, prop_val in resource_props.items():
                    if isinstance(prop_val, dict) and 'get_param' in prop_val:
                        param_list = prop_val['get_param']
                        if len(param_list) == 4:
                            resource_info = initial_param_dict.get(
                                param_list[0], {}).get(
                                    param_list[1], {})
                            if param_list[2] not in resource_info:
                                resource_info[param_list[2]] = {}

    LOG.info('initial_param_dict: %s', initial_param_dict)
    return initial_param_dict


def create_initial_param_server_port_dict(base_hot_dict):
    """Create initial dict containing information about get_param resources.

    :param base_hot_dict: dict(Base HOT dict format)
    :return: dict('nfv', Initial HOT resource dict)

    NOTE: 'nfv' is a fixed value for 1st element.
          'VDU' and 'CP' are supported for 2nd element.
          3rd and 4th element are mandatory.
    """
    initial_param_dict = {
        'nfv': {
            'VDU': {
            },
            'CP': {
            }
        }
    }

    for hot_dict in base_hot_dict.values():
        LOG.debug("init hot_dict: %s", hot_dict)
        param_nfv = hot_dict.get('parameters', {}).get('nfv')
        if not param_nfv:
            continue
        resources = hot_dict.get('resources', {})
        for resource_name, resource_val in resources.items():
            resource_type = resource_val.get('type')
            if resource_type in PORT_SERVER_TYPE:
                resource_props = resource_val.get('properties', {})
                for prop_key, prop_val in resource_props.items():
                    if isinstance(prop_val, dict) and 'get_param' in prop_val:
                        param_list = prop_val['get_param']
                        if len(param_list) == 4:
                            resource_info = initial_param_dict.get(
                                param_list[0], {}).get(
                                    param_list[1], {})
                            if param_list[2] not in resource_info:
                                resource_info[param_list[2]] = {}
                if resource_type == HOT_NOVA_SERVER:
                    cinder_boot = resource_props.get('block_device_mapping_v2',
                                                     {})
                    if cinder_boot:
                        for boot in cinder_boot:
                            b_param = boot.get('image')
                            if b_param and \
                               isinstance(b_param, dict) and \
                               'get_param' in b_param:
                                param_list = b_param['get_param']
                                if len(param_list) == 4:
                                    resource_info = initial_param_dict.get(
                                        param_list[0], {}).get(
                                            param_list[1], {})
                                    if param_list[2] not in resource_info:
                                        resource_info[param_list[2]] = {}
            elif resource_type == AUTO_SCALING_GROUP:
                resource_nest = resource_val.get('properties').get('resource')
                resource_props = resource_nest.get('properties', {})
                for prop_key, prop_val in resource_props.items():
                    if isinstance(prop_val, dict) and 'get_param' in prop_val:
                        param_list = prop_val['get_param']
                        if len(param_list) == 4:
                            resource_info = initial_param_dict.get(
                                param_list[0], {}).get(
                                    param_list[1], {})
                            if param_list[2] not in resource_info:
                                resource_info[param_list[2]] = {}

    LOG.info('initial_param_dict: %s', initial_param_dict)
    return initial_param_dict


def create_final_param_dict(param_dict, vdu_flavor_dict,
                            vdu_image_dict, cpd_vl_dict):
    """Create final dict containing information about HOT input parameter.

    :param param_dict: dict('nfv', Initial HOT resource dict)
    :param vdu_flavor_dict: dict(VDU name, VDU flavor dict)
    :param vdu_iamge_dict: dict(VDU name, Glance-image uuid)
    :param cpd_vl_dict: dict(external CPD ID, Neutron-network uuid)
    :return: dict('nfv', Final HOT resource dict)
    """
    final_param_dict = copy.deepcopy(param_dict)

    vdus = final_param_dict.get('nfv', {}).get('VDU', {})
    for target_vdu in vdus:
        vdus[target_vdu]['flavor'] = vdu_flavor_dict.get(target_vdu)
        vdus[target_vdu]['image'] = vdu_image_dict.get(target_vdu)

    cps = final_param_dict.get('nfv', {}).get('CP', {})
    for target_cp in cps:
        cps[target_cp]['network'] = cpd_vl_dict.get(target_cp)

    LOG.info('final_param_dict: %s', final_param_dict)
    return final_param_dict


def create_vdu_flavor_dict(vnfd_dict):
    """Create a dict containing information about VDU's flavor.

    :param vnfd_dict: dict(VNFD dict format)
    :return: dict(VDU name, VDU flavor dict)
    """
    vdu_flavor_dict = {}
    node_templates = vnfd_dict.get(
        'topology_template', {}).get(
            'node_templates', {})

    for vdu_name, val in node_templates.items():
        vdu_flavor_props = val.get(
            'capabilities', {}).get(
                'virtual_compute', {}).get('properties', {})
        if vdu_flavor_props is not {}:
            flavor_dict = {}
            for key, val in vdu_flavor_props.items():
                if key == 'virtual_cpu':
                    flavor_dict['vcpus'] = val['num_virtual_cpu']
                elif key == 'virtual_memory':
                    # Convert to MiB
                    flavor_dict['ram'] = MemoryUnit.convert_unit_size_to_num(
                        val['virtual_mem_size'], 'MiB')
                elif key == 'virtual_local_storage':
                    # Convert to GiB
                    flavor_dict['disk'] = MemoryUnit.convert_unit_size_to_num(
                        val[0]['size_of_storage'], 'GiB')
            vdu_flavor_dict[vdu_name] = flavor_dict

    LOG.info('vdu_flavor_dict: %s', vdu_flavor_dict)
    return vdu_flavor_dict


def create_vdu_image_dict(grant_info):
    """Create a dict containing information about VDU's image.

    :param grant_info: dict(Grant information format)
    :return: dict(VDU name, Glance-image uuid)
    """
    vdu_image_dict = {}
    for vdu_name, resources in grant_info.items():
        for vnf_resource in resources:
            vdu_image_dict[vdu_name] = vnf_resource.resource_identifier

    LOG.info('vdu_image_dict: %s', vdu_image_dict)
    return vdu_image_dict


def create_cpd_vl_dict(base_hot_dict, inst_req_info):
    """Create a dict containing information about CPD and VL.

    :param base_hot_dict: dict(Base HOT dict format)
    :param inst_req_info: dict(Instantiation request information format)
    :return: dict(external CPD ID, Neutron-network uuid)
    """
    cpd_vl_dict = {}
    ext_vls = inst_req_info.ext_virtual_links
    if ext_vls is not None:
        for ext_vl in ext_vls:
            ext_cps = ext_vl.ext_cps
            vl_uuid = ext_vl.resource_id
            for ext_cp in ext_cps:
                for hot_dict in base_hot_dict.values():
                    cp_resource = hot_dict['resources'].get(
                        ext_cp.cpd_id)
                    if cp_resource is None:
                        continue
                    cpd_vl_dict[ext_cp.cpd_id] = vl_uuid
                    break

    LOG.info('cpd_vl_dict: %s', cpd_vl_dict)
    return cpd_vl_dict


def get_diff_base_hot_param_from_api(base_hot_dict, inst_req_info):
    """Compare base hot param from API param.

    :param base_hot_dict: dict(Base HOT dict format)
    :param inst_req_info: dict(Instantiation request information format)
    :return: dict(Parameters)
    """
    param_value = {}
    additional_param = inst_req_info.additional_params

    if additional_param is None:
        additional_param = {}
    input_attributes = base_hot_dict['heat_template'].get('parameters')

    for input_attr, value in input_attributes.items():
        if additional_param.get(input_attr):
            param_value.update({input_attr: additional_param.get(
                input_attr)})

    return param_value


def create_vdu_flavor_capability_name_dict(vnfd_dict):
    """Create a dict containing information about VDU's flavor.

    :param vnfd_dict: dict(VNFD dict format)
    :return: dict(VDU name, VDU Capability Name dict)
    """
    vdu_flavor_dict = {}
    node_templates = vnfd_dict.get(
        'topology_template', {}).get(
            'node_templates', {})

    for vdu_name, val in node_templates.items():
        vdu_flavor_props = val.get(
            'capabilities', {}).get(
                'virtual_compute', {}).get('properties', {})
        if vdu_flavor_props is not {}:
            for key, val in vdu_flavor_props.items():
                if key == 'requested_additional_capabilities':
                    capability_props = val.get('properties', {})
                    if 'requested_additional_capability_name'\
                       in capability_props.keys():
                        vdu_flavor_dict[vdu_name] = \
                            capability_props[
                                "requested_additional"
                                "_capability_name"]

    LOG.info('vdu_flavor_dict: %s', vdu_flavor_dict)
    return vdu_flavor_dict


def create_sw_image_dict(vnfd_dict):
    """Create a dict containing information about VDU's flavor.

    :param vnfd_dict: dict(VNFD dict format)
    :return: dict(VDU name, VDU SW Image data dict)
    """
    sw_image_data = {}
    node_templates = vnfd_dict.get(
        'topology_template', {}).get(
            'node_templates', {})

    for vdu_name, val in node_templates.items():
        sw_image_data_props = val.get(
            'properties', {}).get('sw_image_data', {})
        if sw_image_data_props is not {}:
            if 'name' in sw_image_data_props.keys():
                sw_image_data[vdu_name] = sw_image_data_props['name']

    LOG.info('sw_image_data: %s', sw_image_data)
    return sw_image_data


def create_network_dict(inst_req_info, param_dict):
    """Create a dict containing information about VDU's network.

    :param inst_req_info: dict(Instantiation request information format)
    :param param_dict: dict('nfv', Initial HOT resource dict)
    :return: dict(VDU name, VDU SW Image data dict)
    """
    cp_data = {}
    ext_vl_param = inst_req_info.ext_virtual_links
    cp_param = param_dict.get('nfv', {}).get('CP')

    for ext_vl in ext_vl_param:
        for ext_cp in ext_vl.ext_cps:
            if ext_cp.cpd_id in cp_param.keys():
                cp_data[ext_cp.cpd_id] = ext_vl.resource_id

    LOG.info('cp_data: %s', cp_data)
    return cp_data
