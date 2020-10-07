# Copyright (C) 2020 NTT DATA
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
import io
import os
import six
import yaml

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import uuidutils
from toscaparser import tosca_template

from tacker.common import exceptions
from tacker.common import utils
from tacker.extensions import nfvo
from tacker import objects
from tacker.objects import fields
from tacker.tosca import utils as toscautils
from tacker.vnfm import vim_client

LOG = logging.getLogger(__name__)
CONF = cfg.CONF


def _get_vim(context, vim_connection_info):
    vim_client_obj = vim_client.VimClient()

    if vim_connection_info:
        vim_id = vim_connection_info[0].vim_id
        access_info = vim_connection_info[0].access_info
        if access_info:
            region_name = access_info.get('region')
        else:
            region_name = None
    else:
        vim_id = None
        region_name = None

    try:
        vim_res = vim_client_obj.get_vim(
            context, vim_id, region_name=region_name)
    except nfvo.VimNotFoundException:
        raise exceptions.VimConnectionNotFound(vim_id=vim_id)

    vim_res['vim_auth'].update({'region': region_name})
    vim_info = {'id': vim_res['vim_id'], 'vim_id': vim_res['vim_id'],
                'vim_type': vim_res['vim_type'],
                'access_info': vim_res['vim_auth']}

    return vim_info


def _get_vnfd_dict(context, vnfd_id, flavour_id):
    vnf_package_id = _get_vnf_package_id(context, vnfd_id)
    vnf_package_base_path = cfg.CONF.vnf_package.vnf_package_csar_path
    vnf_package_csar_path = vnf_package_base_path + '/' + vnf_package_id
    vnfd_dict = _get_flavour_based_vnfd(vnf_package_csar_path, flavour_id)

    # Remove requirements from substitution mapping
    vnfd_dict.get('topology_template').get(
        'substitution_mappings').pop('requirements')
    return vnfd_dict


def _get_vnflcm_interface(context, interface, vnf_instance, flavour_id):
    '''Gets the interface found in vnfd

        ...
            node_templates:
                VNF:
                    interfaces:
                        Vnflcm:
                            <interface>
    '''
    interface_value = None
    vnfd_dict = _get_vnfd_dict(context, vnf_instance.vnfd_id, flavour_id)

    if not isinstance(vnfd_dict, dict):
        raise exceptions.InvalidContentType(msg="VNFD not valid")

    if vnfd_dict.get('topology_template'):
        topology_template = vnfd_dict.get('topology_template')
        if topology_template.get('node_templates'):
            node_templates = topology_template.get('node_templates')
            if node_templates.get('VNF'):
                vnf = node_templates.get('VNF')
                if vnf.get('interfaces'):
                    interfaces = vnf.get('interfaces')
                    if interfaces.get('Vnflcm'):
                        vnflcm = interfaces.get('Vnflcm')
                        if vnflcm:
                            interface_value = vnflcm.get(interface)

    return interface_value


def _build_affected_resources(vnf_instance,
     change_type=fields.ResourceChangeType.ADDED):
    '''build affected resources from vnf_instance instantiated info '''

    affected_resources = {}
    instantiated_vnf_info = vnf_instance.instantiated_vnf_info
    if hasattr(instantiated_vnf_info, 'instance_id'):
        if instantiated_vnf_info.instance_id:

            affected_resources['affectedVnfcs'] = []
            affected_resources['affectedVirtualLinks'] = []
            affected_resources['affectedVirtualStorages'] = []

            # build AffectedVnfc
            vnfc_resource_info = \
                instantiated_vnf_info.vnfc_resource_info
            for vnfc_resource in vnfc_resource_info:
                data = {}
                data['id'] = vnfc_resource.id
                data['vduId'] = vnfc_resource.vdu_id
                data['changeType'] = change_type
                data['computeResource'] = \
                    vnfc_resource.compute_resource.to_dict()
                data['metadata'] = vnfc_resource.metadata
                affected_resources['affectedVnfcs'].append(data)

            # build AffectedVirtualLink
            vnf_virtual_link = \
                instantiated_vnf_info.vnf_virtual_link_resource_info
            for vnf_vl_info in vnf_virtual_link:
                data = {}
                data['id'] = vnf_vl_info.id
                data['vnfVirtualLinkDescId'] = \
                    vnf_vl_info.vnf_virtual_link_desc_id
                data['changeType'] = change_type
                data['networkResource'] = \
                    vnf_vl_info.network_resource.to_dict()
                data['metadata'] = {}
                affected_resources['affectedVirtualLinks'].append(data)

            # build affectedVirtualStorages
            virtual_storage = \
                instantiated_vnf_info.virtual_storage_resource_info
            for vnf_storage_info in virtual_storage:
                data = {}
                data['id'] = vnf_storage_info.id
                data['virtualStorageDescId'] = \
                    vnf_storage_info.virtual_storage_desc_id
                data['changeType'] = change_type
                data['storageResource'] = \
                    vnf_storage_info.storage_resource.to_dict()
                data['metadata'] = {}
                affected_resources['affectedVirtualStorages'].append(data)

    return utils.convert_snakecase_to_camelcase(affected_resources)


def _get_affected_resources(old_vnf_instance=None,
                new_vnf_instance=None, extra_list=None):
    '''get_affected_resources

    returns affected resources in new_vnf_instance not present
    in old_vnf_instance.
    if extra_list (list of physical resource ids) is present,
        included to affected resources
    '''
    def _get_affected_cpids(affected_vnfc, vnf_instance):
        affected_cpids = []
        instantiated_vnf_info = vnf_instance.instantiated_vnf_info
        for vnfc_resource in instantiated_vnf_info.vnfc_resource_info:
            if vnfc_resource.id == affected_vnfc['id']:
                for vnfc_cp in vnfc_resource.vnfc_cp_info:
                    if vnfc_cp.cpd_id:
                        affected_cpids.append(vnfc_cp.cpd_id)
                    if vnfc_cp.vnf_ext_cp_id:
                        affected_cpids.append(vnfc_cp.vnf_ext_cp_id)
        return affected_cpids

    def _get_added_storageids(affected_vnfc, vnf_instance):
        affected_storage_ids = []
        instantiated_vnf_info = vnf_instance.instantiated_vnf_info
        for vnfc_resource in instantiated_vnf_info.vnfc_resource_info:
            if vnfc_resource.id == affected_vnfc['id']:
                for storage_resource_id in vnfc_resource.storage_resource_ids:
                    virtual_storage = \
                        instantiated_vnf_info.virtual_storage_resource_info
                    for virt_storage_res_info in virtual_storage:
                        if virt_storage_res_info.id == storage_resource_id:
                            affected_storage_ids.append(
                                virt_storage_res_info.virtual_storage_desc_id)
        return affected_storage_ids

    def diff_list(old_list, new_list):
        diff = []
        for item in new_list:
            if item not in old_list:
                diff.append(item)
        return diff

    affected_resources = {}
    affected_resources['affectedVnfcs'] = []
    affected_resources['affectedVirtualLinks'] = []
    affected_resources['affectedVirtualStorages'] = []

    if not old_vnf_instance:
        affected_resources = _build_affected_resources(
            new_vnf_instance, fields.ResourceChangeType.ADDED)
        # add affected cpids and add added storageids
        for affected_vnfc in affected_resources['affectedVnfcs']:
            affected_vnfc['affectedVnfcCpIds'] = _get_affected_cpids(
                affected_vnfc, new_vnf_instance)
            affected_vnfc['addedStorageResourceIds'] = _get_added_storageids(
                affected_vnfc, new_vnf_instance)

    elif not new_vnf_instance:
        affected_resources = _build_affected_resources(old_vnf_instance,
                                            fields.ResourceChangeType.REMOVED)
        # add affected cpids and add remove storageids
        for affected_vnfc in affected_resources['affectedVnfcs']:
            affected_vnfc['affectedVnfcCpIds'] = _get_affected_cpids(
                affected_vnfc, old_vnf_instance)
            affected_vnfc['removedStorageResourceIds'] = _get_added_storageids(
                affected_vnfc, old_vnf_instance)
    elif old_vnf_instance and new_vnf_instance:
        old_affected_resources = _build_affected_resources(old_vnf_instance)
        new_affected_resources = _build_affected_resources(new_vnf_instance,
                                            fields.ResourceChangeType.MODIFIED)

        # get resource_ids
        old_vnfc_resource_ids = []
        for vnfc_resource in old_affected_resources.get('affectedVnfcs', []):
            old_vnfc_resource_ids.append(
                vnfc_resource['computeResource']['resourceId'])

        # remove extra_list items in old_vnfc_resource_ids
        # so that this items will be considered new
        if extra_list:
            for item in extra_list:
                if item in old_vnfc_resource_ids:
                    index = old_vnfc_resource_ids.index(item)
                    old_vnfc_resource_ids.pop(index)

        new_vnfc_resource_ids = []
        for vnfc_resource in new_affected_resources.get('affectedVnfcs', []):
            resource_id = vnfc_resource['computeResource']['resourceId']
            new_vnfc_resource_ids.append(resource_id)

        old_vnf_vl_resource_ids = []
        for vnf_vl_info in old_affected_resources.get(
                'affectedVirtualLinks', []):
            resource_id = vnf_vl_info['networkResource']['resourceId']
            old_vnf_vl_resource_ids.append(resource_id)

        new_vnf_vl_resource_ids = []
        for vnf_vl_info in new_affected_resources.get(
                'affectedVirtualLinks', []):
            resource_id = vnf_vl_info['networkResource']['resourceId']
            new_vnf_vl_resource_ids.append(resource_id)

        old_vnf_storage_resource_ids = []
        for vnf_storage_info in old_affected_resources.get(
                'affectedVirtualStorages', []):
            resource_id = vnf_storage_info['storageResource']['resourceId']
            old_vnf_storage_resource_ids.append(resource_id)

        new_vnf_storage_resource_ids = []
        for vnf_storage_info in new_affected_resources.get(
                'affectedVirtualStorages', []):
            resource_id = vnf_storage_info['storageResource']['resourceId']
            new_vnf_storage_resource_ids.append(resource_id)

        # get difference between resource_ids
        vnfc_resource_ids = diff_list(old_vnfc_resource_ids,
                                      new_vnfc_resource_ids)
        vnf_vl_resource_ids = diff_list(old_vnf_vl_resource_ids,
                                        new_vnf_vl_resource_ids)
        vnf_storage_resource_ids = diff_list(old_vnf_storage_resource_ids,
                                             new_vnf_storage_resource_ids)

        # return new affected resources
        for affected_vls in new_affected_resources['affectedVirtualLinks']:
            if (affected_vls['networkResource']
                    ['resourceId'] in vnf_vl_resource_ids):
                affected_resources['affectedVirtualLinks'].append(affected_vls)

        affected_storages = new_affected_resources['affectedVirtualStorages']
        for affected_storage in affected_storages:
            if (affected_storage['storageResource']
                    ['resourceId'] in vnf_storage_resource_ids):
                affected_resources['affectedVirtualStorages'].append(
                    affected_storage)

        for affected_vnfc in new_affected_resources['affectedVnfcs']:
            if (affected_vnfc['computeResource']
                    ['resourceId'] in vnfc_resource_ids):

                # update affected affectedVnfcCpIds
                affected_vnfc['affectedVnfcCpIds'] = _get_affected_cpids(
                    affected_vnfc, new_vnf_instance)

                affected_resources['affectedVnfcs'].append(affected_vnfc)

    return affected_resources


def _get_vnf_package_id(context, vnfd_id):
    vnf_package = objects.VnfPackageVnfd.get_by_id(context, vnfd_id)
    return vnf_package.package_uuid


def _create_grant_request(vnfd_dict, package_uuid):
    node_templates = vnfd_dict.get('topology_template',
                                   {}).get('node_templates', {})
    vnf_software_images = {}
    if not node_templates:
        return vnf_software_images

    def _build_vnf_software_image(sw_image_data, artifact_image_path):
        vnf_sw_image = objects.VnfSoftwareImage()
        vnf_sw_image.image_path = artifact_image_path
        vnf_sw_image.name = sw_image_data.get('name')
        vnf_sw_image.version = sw_image_data.get('version')
        if sw_image_data.get('checksum'):
            checksum = sw_image_data.get('checksum')
            if checksum.get('algorithm'):
                vnf_sw_image.algorithm = checksum.get('algorithm')
            if checksum.get('hash'):
                vnf_sw_image.hash = checksum.get('hash')

        vnf_sw_image.container_format = sw_image_data.get(
            'container_format')
        vnf_sw_image.disk_format = sw_image_data.get('disk_format')
        if sw_image_data.get('min_disk'):
            min_disk = utils.MemoryUnit.convert_unit_size_to_num(
                sw_image_data.get('min_disk'), 'GB')
            vnf_sw_image.min_disk = min_disk
        else:
            vnf_sw_image.min_disk = 0

        if sw_image_data.get('min_ram'):
            min_ram = utils.MemoryUnit.convert_unit_size_to_num(
                sw_image_data.get('min_ram'), 'MB')
            vnf_sw_image.min_ram = min_ram
        else:
            vnf_sw_image.min_ram = 0

        return vnf_sw_image

    def _get_image_path(artifact_image_path, package_uuid):
        vnf_package_path = cfg.CONF.vnf_package.vnf_package_csar_path
        artifact_image_path = os.path.join(
            vnf_package_path, package_uuid,
            artifact_image_path.split('../')[-1])
        return artifact_image_path

    for node, value in node_templates.items():
        if not value.get(
                'type') in ['tosca.nodes.nfv.Vdu.Compute',
                            'tosca.nodes.nfv.Vdu.VirtualBlockStorage']:
            continue

        sw_image_data = value.get('properties', {}).get('sw_image_data')
        artifacts = value.get('artifacts', {})
        for artifact, sw_image in artifacts.items():
            artifact_image_path = None
            if isinstance(sw_image, six.string_types):
                artifact_image_path = sw_image
            elif sw_image.get('type') == 'tosca.artifacts.nfv.SwImage':
                artifact_image_path = sw_image.get('file', {})
            if sw_image_data and artifact_image_path:
                is_url = utils.is_url(artifact_image_path)
                if not is_url:
                    artifact_image_path = _get_image_path(artifact_image_path,
                                                          package_uuid)

                vnf_software_image = _build_vnf_software_image(
                    sw_image_data, artifact_image_path)
                vnf_software_images[node] = vnf_software_image
            break

    return vnf_software_images


def _make_final_vnf_dict(vnfd_dict, id, name, param_values, vnf_dict=None):
    if vnf_dict:
        final_vnf_dict = vnf_dict
        final_vnf_dict['vnfd']['attributes'].\
            update({'vnfd': str(vnfd_dict)})
        final_vnf_dict['attributes'].\
            update({'param_values': str(param_values)})
        final_vnf_dict['attributes'].\
            update({'stack_name': name or ("vnflcm_" + id)})
        return final_vnf_dict
    else:
        return {'vnfd': {
            'attributes': {
                'vnfd': str(vnfd_dict)}},
            'id': id,
            'name': name,
            'attributes': {
                'param_values': str(param_values),
                'stack_name': name or ("vnflcm_" + id)}}


def _get_flavour_based_vnfd(csar_path, flavour_id):
    ext = [".yaml", ".yml"]
    file_path_and_data = {}
    imp_list = []
    for item in os.listdir(csar_path):
        src_path = os.path.join(csar_path, item)
        if os.path.isdir(src_path):
            for file in os.listdir(src_path):
                if file.endswith(tuple(ext)):
                    source_file_path = os.path.join(src_path, file)
                    with open(source_file_path) as file_obj:
                        data = yaml.safe_load(file_obj)
                    substitution_map = data.get(
                        'topology_template',
                        {}).get('substitution_mappings', {})
                    if substitution_map.get(
                            'properties', {}).get('flavour_id') == flavour_id:
                        if data.get('imports'):
                            for imp in data.get('imports'):
                                imp_path = os.path.join(src_path, imp)
                                imp_list.append(imp_path)
                            data.update({'imports': imp_list})

                        return data

        elif src_path.endswith(tuple(ext)):
            file_data = yaml.safe_load(io.open(src_path))
            substitution_map = file_data.get(
                'topology_template', {}).get('substitution_mappings', {})
            if substitution_map.get(
                    'properties', {}).get('flavour_id') == flavour_id:
                if file_data.get('imports'):
                    for imp in file_data.get('imports'):
                        imp_list.append(os.path.join(src_path, imp))
                    file_data.update({'imports': imp_list})
                return file_data

    return file_path_and_data


def _get_param_data(vnfd_dict, instantiate_vnf_req):
    param_value = {}
    additional_param = instantiate_vnf_req.additional_params
    if additional_param is None:
        additional_param = {}
    substitution_map = vnfd_dict.get('topology_template',
                                     {}).get('substitution_mappings', {})
    input_attributes = vnfd_dict.get('topology_template', {}).get('inputs')
    if substitution_map is not None:
        subs_map_node_type = substitution_map.get('node_type')
        # Get properties in lower-level VNFD for top-level VNFD
        node_templates = vnfd_dict.get('topology_template',
                                    {}).get('node_templates', {})
        for node in node_templates.values():
            if node.get('type') == subs_map_node_type:
                node_property = node.get('properties', {})
                if node_property:
                    param_value.update(node_property)
        # Import `_type.yaml` file and get default properties.
        # If new value provided in additional_param, the property is updated.
        import_paths = vnfd_dict.get('imports', {})
        for imp_path in import_paths:
            with open(imp_path) as file_obj:
                import_data = yaml.safe_load(file_obj)
            imp_node_type = import_data.get('node_types')
            if imp_node_type:
                for key, value in imp_node_type.items():
                    if key == subs_map_node_type:
                        properties = value.get('properties')
                        if properties:
                            for key, prop in properties.items():
                                if additional_param.get(key):
                                    param_value.update({
                                        key: additional_param.get(key)})
                                # If the parameter is provided in lower-level
                                # VNFD, use it. Otherwise use the default.
                                elif not param_value.get(key):
                                    param_value.update(
                                        {key: prop.get('default')})

    for input_attr, value in input_attributes.items():
        if additional_param.get(input_attr):
            param_value.update({input_attr: additional_param.get(
                input_attr)})

    return param_value


def _get_vim_connection_info_from_vnf_req(vnf_instance, instantiate_vnf_req):
    vim_connection_obj_list = []

    if not instantiate_vnf_req.vim_connection_info:
        # add default vim
        if len(vnf_instance.vim_connection_info):
            vim_connection_obj_list.append(vnf_instance.vim_connection_info[0])

        return vim_connection_obj_list

    for vim_connection in instantiate_vnf_req.vim_connection_info:
        vim_conn = objects.VimConnectionInfo(id=vim_connection.id,
            vim_id=vim_connection.vim_id, vim_type=vim_connection.vim_type,
            access_info=vim_connection.access_info)

        vim_connection_obj_list.append(vim_conn)

    # add default vim
    if len(vnf_instance.vim_connection_info):
        if vim_conn.id and vnf_instance.vim_connection_info[0].id:
            is_default_vim_exist = [vim_conn for vim_conn
                in vim_connection_obj_list
                    if vim_conn.id == vnf_instance.vim_connection_info[0].id]
            if not len(is_default_vim_exist):
                vim_connection_obj_list.append(vnf_instance.
                    vim_connection_info[0])

    return vim_connection_obj_list


def _build_instantiated_vnf_info(vnfd_dict, instantiate_vnf_req,
                                 vnf_instance, vim_id):
    inst_vnf_info = vnf_instance.instantiated_vnf_info
    inst_vnf_info.vnf_state = fields.VnfOperationalStateType.STARTED

    node_templates = vnfd_dict.get(
        'topology_template', {}).get('node_templates')

    vnfc_resource_info, virtual_storage_resource_info = \
        _get_vnfc_resource_info(vnfd_dict, instantiate_vnf_req, vim_id)

    inst_vnf_info.vnfc_resource_info = vnfc_resource_info

    tmp_insta_vnf_info = copy.deepcopy(inst_vnf_info)
    inst_vnf_info.ext_cp_info = _set_ext_cp_info(instantiate_vnf_req,
        inst_vnf_info=tmp_insta_vnf_info)
    inst_vnf_info.ext_virtual_link_info = _set_ext_virtual_link_info(
        instantiate_vnf_req, inst_vnf_info.ext_cp_info)

    inst_vnf_info.virtual_storage_resource_info = \
        virtual_storage_resource_info
    inst_vnf_info.vnf_virtual_link_resource_info = \
        _build_vnf_virtual_link_resource_info(
            node_templates, instantiate_vnf_req,
            inst_vnf_info.vnfc_resource_info, vim_id)

    inst_vnf_info.ext_managed_virtual_link_info = \
        _build_ext_managed_virtual_link_info(instantiate_vnf_req,
            inst_vnf_info)

    inst_vnf_info.additional_params = instantiate_vnf_req.additional_params

    vnf_instance.instantiated_vnf_info = inst_vnf_info


def _get_compute_nodes(vnfd_dict, instantiate_vnf_req):
    """Read the node templates and prepare VDU data in below format

    {
        'VDU1': {
            'CP': [CP1, CP2],
            'VIRTUAL_STORAGE': [virtual_storage1]
        },
    }
    """

    node_templates = vnfd_dict.get(
        'topology_template', {}).get('node_templates')

    vdu_resources = {}
    for key, value in node_templates.items():
        if value.get('type') != 'tosca.nodes.nfv.Vdu.Compute':
            continue

        desired_capacity = _convert_desired_capacity(
            instantiate_vnf_req.instantiation_level_id, vnfd_dict, key)

        cp_list = _get_cp_for_vdu(key, node_templates)

        virtual_storages = []
        requirements = value.get('requirements', [])
        for requirement in requirements:
            if requirement.get('virtual_storage'):
                virtual_storages.append(
                    requirement.get('virtual_storage'))

        vdu_resources[key] = {"CP": cp_list,
                              "VIRTUAL_STORAGE": virtual_storages,
                              "COUNT": desired_capacity}

    return vdu_resources


def _get_virtual_link_nodes(node_templates):
    virtual_link_nodes = {}

    for key, value in node_templates.items():
        if value.get('type') == 'tosca.nodes.nfv.VnfVirtualLink':
            cp_list = _get_cp_for_vl(key, node_templates)
            virtual_link_nodes[key] = cp_list

    return virtual_link_nodes


def _get_cp_for_vdu(vdu, node_templates):
    cp_list = []
    for key, value in node_templates.items():
        if value.get('type') != 'tosca.nodes.nfv.VduCp':
            continue

        requirements = value.get('requirements', [])
        for requirement in requirements:
            if requirement.get('virtual_binding') and vdu == \
                    requirement.get('virtual_binding'):
                cp_list.append(key)

    return cp_list


def _get_cp_for_vl(vl, node_templates):
    cp_list = []
    for key, value in node_templates.items():
        if value.get('type') != 'tosca.nodes.nfv.VduCp':
            continue

        requirements = value.get('requirements', [])
        for requirement in requirements:
            if requirement.get('virtual_link') and vl == \
                    requirement.get('virtual_link'):
                cp_list.append(key)

    return cp_list


def _build_vnf_virtual_link_resource_info(node_templates, instantiate_vnf_req,
                                          vnfc_resource_info, vim_id):
    virtual_link_nodes_with_cp = _get_virtual_link_nodes(node_templates)

    # Read the external networks and extcps from InstantiateVnfRequest
    for ext_virt_link in instantiate_vnf_req.ext_virtual_links:
        virtual_link_nodes_with_cp[ext_virt_link.id] = [extcp.cpd_id for extcp
                in ext_virt_link.ext_cps]

    virtual_link_resource_info_list = []

    def _get_network_resource(vl_node):
        resource_handle = objects.ResourceHandle()
        found = False
        for ext_mg_vl in instantiate_vnf_req.ext_managed_virtual_links:
            if ext_mg_vl.vnf_virtual_link_desc_id == vl_node:
                resource_handle.resource_id = ext_mg_vl.resource_id
                resource_handle.vim_connection_id = \
                    ext_mg_vl.vim_connection_id
                # TODO(tpatil): This cannot be set here.
                resource_handle.vim_level_resource_type = \
                    'OS::Neutron::Net'
                found = True
                break

        if not found:
            # check if it exists in the ext_virtual_links
            for ext_virt_link in instantiate_vnf_req.ext_virtual_links:
                if ext_virt_link.id == vl_node:
                    resource_handle.resource_id = ext_virt_link.resource_id
                    resource_handle.vim_connection_id = \
                        ext_virt_link.vim_connection_id
                    # TODO(tpatil): This cannot be set here.
                    resource_handle.vim_level_resource_type = \
                        'OS::Neutron::Net'
                    found = True
                    break

        return resource_handle

    def _get_vnf_link_port_info(cp):
        vnf_link_port_info = objects.VnfLinkPortInfo()
        vnf_link_port_info.id = uuidutils.generate_uuid()

        resource_handle = objects.ResourceHandle()
        for ext_virt_link in instantiate_vnf_req.ext_virtual_links:
            for extcp in ext_virt_link.ext_cps:
                if extcp.cpd_id == cp:
                    for cpconfig in extcp.cp_config:
                        if cpconfig.link_port_id:
                            resource_handle.resource_id = \
                                cpconfig.link_port_id
                            resource_handle.vim_connection_id = \
                                ext_virt_link.vim_connection_id
                            # TODO(tpatil): This shouldn't be set here.
                            resource_handle.vim_level_resource_type = \
                                'OS::Neutron::Port'
                            break

        vnf_link_port_info.resource_handle = resource_handle

        return vnf_link_port_info

    for node, cp_list in virtual_link_nodes_with_cp.items():
        vnf_vl_resource_info = objects.VnfVirtualLinkResourceInfo()
        vnf_vl_resource_info.id = uuidutils.generate_uuid()
        vnf_vl_resource_info.vnf_virtual_link_desc_id = node
        vnf_vl_resource_info.network_resource = _get_network_resource(node)

        vnf_link_port_info_list = []
        for cp in cp_list:
            for vnfc_resource in vnfc_resource_info:
                for vnfc_cp in vnfc_resource.vnfc_cp_info:
                    if vnfc_cp.cpd_id == cp:
                        vnf_link_port_info = _get_vnf_link_port_info(cp)
                        vnf_link_port_info.cp_instance_id = vnfc_cp.id
                        # Identifier of the "vnfLinkPorts" structure in the
                        # "vnfVirtualLinkResourceInfo" structure.
                        vnfc_cp.vnf_link_port_id = vnf_link_port_info.id
                        vnf_link_port_info_list.append(vnf_link_port_info)

        vnf_vl_resource_info.vnf_link_ports = vnf_link_port_info_list

        virtual_link_resource_info_list.append(vnf_vl_resource_info)

    return virtual_link_resource_info_list


def _build_vnf_cp_info(instantiate_vnf_req, cp_list):
    vnfc_cp_info_list = []

    if not cp_list:
        return vnfc_cp_info_list

    def _set_vnf_exp_cp_id_protocol_data(vnfc_cp_info):
        for ext_virt_link in instantiate_vnf_req.ext_virtual_links:
            for extcp in ext_virt_link.ext_cps:
                if extcp.cpd_id == cp:
                    vnfc_cp_info.cp_protocol_info = \
                        _set_cp_protocol_info(extcp)
                    for cpconfig in extcp.cp_config:
                        vnfc_cp_info.vnf_ext_cp_id = cpconfig.link_port_id
                        break

    for cp in cp_list:
        vnfc_cp_info = objects.VnfcCpInfo()
        vnfc_cp_info.id = uuidutils.generate_uuid()
        vnfc_cp_info.cpd_id = cp
        _set_vnf_exp_cp_id_protocol_data(vnfc_cp_info)
        vnfc_cp_info_list.append(vnfc_cp_info)

    return vnfc_cp_info_list


def _build_virtual_storage_info(virtual_storages):

    for storage_node in virtual_storages:
        virtual_storage = objects.VirtualStorageResourceInfo()
        virtual_storage.id = uuidutils.generate_uuid()
        virtual_storage.virtual_storage_desc_id = storage_node

        virtual_storage.storage_resource = objects.ResourceHandle()

        yield virtual_storage


def _get_vnfc_resource_info(vnfd_dict, instantiate_vnf_req, vim_id):
    vdu_resources = _get_compute_nodes(vnfd_dict, instantiate_vnf_req)
    vnfc_resource_info_list = []
    virtual_storage_resource_info_list = []

    def _build_vnfc_resource_info(vdu, vdu_resource):
        vnfc_resource_info = objects.VnfcResourceInfo()
        vnfc_resource_info.id = uuidutils.generate_uuid()
        vnfc_resource_info.vdu_id = vdu

        vnfc_resource_info.compute_resource = objects.ResourceHandle()

        vnfc_cp_info_list = _build_vnf_cp_info(instantiate_vnf_req,
                                               vdu_resource.get("CP"))
        vnfc_resource_info.vnfc_cp_info = vnfc_cp_info_list

        virtual_storages = vdu_resource.get("VIRTUAL_STORAGE")
        vdu_storages = []
        for storage in _build_virtual_storage_info(virtual_storages):
            vdu_storages.append(storage)
            virtual_storage_resource_info_list.append(storage)

        storage_resource_ids = [info.id for info in vdu_storages]
        vnfc_resource_info.storage_resource_ids = storage_resource_ids
        return vnfc_resource_info

    for vdu, vdu_resource in vdu_resources.items():
        count = vdu_resource.get('COUNT', 1)
        for num_instance in range(count):
            vnfc_resource_info = _build_vnfc_resource_info(vdu, vdu_resource)
            vnfc_resource_info_list.append(vnfc_resource_info)

    return vnfc_resource_info_list, virtual_storage_resource_info_list


def _set_ext_cp_info(instantiate_vnf_req, inst_vnf_info=None):
    ext_cp_info_list = []
    vnfc_info = []

    if inst_vnf_info.vnfc_resource_info:
        vnfc_info = inst_vnf_info.vnfc_resource_info

    if not instantiate_vnf_req.ext_virtual_links:
        return ext_cp_info_list

    for ext_virt_link in instantiate_vnf_req.ext_virtual_links:
        if not ext_virt_link.ext_cps:
            continue

        for ext_cp in ext_virt_link.ext_cps:
            ext_cp_info = objects.VnfExtCpInfo(
                id=uuidutils.generate_uuid(),
                cpd_id=ext_cp.cpd_id,
                cp_protocol_info=_set_cp_protocol_info(ext_cp),
                ext_link_port_id=_get_ext_link_port_id(ext_virt_link,
                        ext_cp.cpd_id),
                associated_vnfc_cp_id=_get_associated_vnfc_cp_id(vnfc_info,
                        ext_cp.cpd_id))

            ext_cp_info_list.append(ext_cp_info)

    return ext_cp_info_list


def _get_ext_link_port_id(ext_virtual_link, cpd_id):
    if not ext_virtual_link.ext_link_ports:
        return

    for ext_link in ext_virtual_link.ext_link_ports:
        if ext_link.id == cpd_id:
            return ext_link.id


def _get_associated_vnfc_cp_id(vnfc_info, cpd_id):
    if not isinstance(vnfc_info, list):
        return

    for vnfc in vnfc_info:
        if vnfc.vnfc_cp_info:
            for cp_info in vnfc.vnfc_cp_info:
                if cp_info.cpd_id == cpd_id:
                    return vnfc.id


def _build_ip_over_ethernet_address_info(cp_protocol_data):
    """Convert IpOverEthernetAddressData to IpOverEthernetAddressInfo"""

    if not cp_protocol_data.ip_over_ethernet:
        return

    ip_over_ethernet_add_info = objects.IpOverEthernetAddressInfo()
    ip_over_ethernet_add_info.mac_address = \
        cp_protocol_data.ip_over_ethernet.mac_address

    if not cp_protocol_data.ip_over_ethernet.ip_addresses:
        return ip_over_ethernet_add_info

    ip_address_list = []
    for ip_address in cp_protocol_data.ip_over_ethernet.ip_addresses:
        ip_address_info = objects.vnf_instantiated_info.IpAddress(
            type=ip_address.type,
            addresses=ip_address.fixed_addresses,
            is_dynamic=(False if ip_address.fixed_addresses else True),
            subnet_id=ip_address.subnet_id)

        ip_address_list.append(ip_address_info)

    ip_over_ethernet_add_info.ip_addresses = ip_address_list

    return ip_over_ethernet_add_info


def _build_cp_protocol_info(cp_protocol_data):
    ip_over_ethernet_add_info = _build_ip_over_ethernet_address_info(
        cp_protocol_data)
    cp_protocol_info = objects.CpProtocolInfo(
        layer_protocol=cp_protocol_data.layer_protocol,
        ip_over_ethernet=ip_over_ethernet_add_info)

    return cp_protocol_info


def _set_cp_protocol_info(ext_cp):
    """Convert CpProtocolData to CpProtocolInfo"""

    cp_protocol_info_list = []
    if not ext_cp.cp_config:
        return cp_protocol_info_list

    for cp_config in ext_cp.cp_config:
        for cp_protocol_data in cp_config.cp_protocol_data:
            cp_protocol_info = _build_cp_protocol_info(cp_protocol_data)
            cp_protocol_info_list.append(cp_protocol_info)

    return cp_protocol_info_list


def _set_ext_virtual_link_info(instantiate_vnf_req, ext_cp_info):
    ext_virtual_link_list = []

    if not instantiate_vnf_req.ext_virtual_links:
        return ext_virtual_link_list

    for ext_virtual_link in instantiate_vnf_req.ext_virtual_links:
        res_handle = objects.ResourceHandle()
        res_handle.resource_id = ext_virtual_link.resource_id
        res_handle.vim_connection_id = ext_virtual_link.vim_connection_id

        ext_virtual_link_info = objects.ExtVirtualLinkInfo(
            id=ext_virtual_link.id,
            resource_handle=res_handle,
            ext_link_ports=_set_ext_link_port(ext_virtual_link,
                ext_cp_info))

        ext_virtual_link_list.append(ext_virtual_link_info)

    return ext_virtual_link_list


def _set_ext_link_port(ext_virtual_links, ext_cp_info):
    ext_link_port_list = []

    if not ext_virtual_links.ext_link_ports:
        return ext_link_port_list

    for ext_link_port in ext_virtual_links.ext_link_ports:
        resource_handle = ext_link_port.resource_handle.obj_clone()
        cp_instance_id = None
        if ext_virtual_links.ext_cps:
            for ext_cp in ext_cp_info:
                cp_instance_id = ext_cp.id

        ext_link_port_info = objects.ExtLinkPortInfo(id=ext_link_port.id,
            resource_handle=resource_handle, cp_instance_id=cp_instance_id)

        ext_link_port_list.append(ext_link_port_info)

    return ext_link_port_list


def _build_ext_managed_virtual_link_info(instantiate_vnf_req, inst_vnf_info):

    def _network_resource(ext_managed_vl):
        resource_handle = objects.ResourceHandle(
            resource_id=ext_managed_vl.resource_id)
        # TODO(tpatil): Remove hard coding of resource type as
        # OS::Neutron::Net resource type is specific to OpenStack infra
        # driver. It could be different for other infra drivers like
        # Kubernetes.
        resource_handle.vim_level_resource_type = 'OS::Neutron::Net'
        resource_handle.vim_connection_id = \
            ext_managed_vl.vim_connection_id

        return resource_handle

    ext_managed_virtual_link_info = []
    ext_managed_virt_link_from_req = \
        instantiate_vnf_req.ext_managed_virtual_links
    for ext_managed_vl in ext_managed_virt_link_from_req:
        ext_managed_virt_info = objects.ExtManagedVirtualLinkInfo()
        ext_managed_virt_info.id = ext_managed_vl.id
        ext_managed_virt_info.vnf_virtual_link_desc_id =\
            ext_managed_vl.vnf_virtual_link_desc_id

        ext_managed_virt_info.network_resource =\
            _network_resource(ext_managed_vl)

        # Populate the vnf_link_ports from vnf_virtual_link_resource_info
        # of instantiated_vnf_info.
        for vnf_vl_res_info in inst_vnf_info.vnf_virtual_link_resource_info:
            if ext_managed_vl.vnf_virtual_link_desc_id ==\
                    vnf_vl_res_info.vnf_virtual_link_desc_id:
                vnf_link_ports = []
                for vnf_lp in vnf_vl_res_info.vnf_link_ports:
                    vnf_link_ports.append(vnf_lp.obj_clone())
                ext_managed_virt_info.vnf_link_ports = vnf_link_ports

        ext_managed_virtual_link_info.append(ext_managed_virt_info)
    return ext_managed_virtual_link_info


def _convert_desired_capacity(inst_level_id, vnfd_dict, vdu):
    aspect_delta_dict = {}
    aspect_vdu_dict = {}
    inst_level_dict = {}
    aspect_id_dict = {}
    vdu_delta_dict = {}
    desired_capacity = 1

    tosca = tosca_template.ToscaTemplate(parsed_params={}, a_file=False,
                                         yaml_dict_tpl=vnfd_dict)
    tosca_policies = tosca.topology_template.policies
    default_inst_level_id = toscautils._extract_policy_info(
        tosca_policies, inst_level_dict,
        aspect_delta_dict, aspect_id_dict,
        aspect_vdu_dict, vdu_delta_dict)

    if vdu_delta_dict.get(vdu) is None:
        return desired_capacity

    if inst_level_id:
        instantiation_level = inst_level_id
    elif default_inst_level_id:
        instantiation_level = default_inst_level_id
    else:
        return desired_capacity

    al_dict = inst_level_dict.get(instantiation_level)

    if not al_dict:
        return desired_capacity

    for aspect_id, level_num in al_dict.items():
        delta_id = aspect_id_dict.get(aspect_id)

        if delta_id is not None:
            delta_num = \
                aspect_delta_dict.get(aspect_id).get(delta_id)

        vdus = aspect_vdu_dict.get(aspect_id)
        initial_delta = None
        for vdu in vdus:
            initial_delta = vdu_delta_dict.get(vdu)

        if initial_delta is not None:
            desired_capacity = initial_delta + delta_num * level_num

    return desired_capacity


def _get_vnf_package_path(context, vnfd_id):
    vnf_package_id = _get_vnf_package_id(context, vnfd_id)
    vnf_package_base_path = cfg.CONF.vnf_package.vnf_package_csar_path
    vnf_package_path = vnf_package_base_path + '/' + vnf_package_id
    return vnf_package_path


def _get_base_hot_dict(context, vnfd_id):
    vnf_package_id = _get_vnf_package_id(context, vnfd_id)
    vnf_package_base_path = cfg.CONF.vnf_package.vnf_package_csar_path
    vnf_package_csar_path = vnf_package_base_path + '/' + vnf_package_id
    base_hot_dir = 'BaseHOT'
    ext = [".yaml", ".yml"]

    base_hot_path = vnf_package_csar_path + '/' + base_hot_dir
    base_hot_dict = None
    if os.path.exists(base_hot_path):
        for file in os.listdir(base_hot_path):
            if file.endswith(tuple(ext)):
                source_file_path = os.path.join(base_hot_path, file)
                base_hot_dict = yaml.safe_load(open(source_file_path))
    LOG.debug("Loaded base hot: %s", base_hot_dict)
    return base_hot_dict


def get_base_nest_hot_dict(context, flavour_id, vnfd_id):
    vnf_package_id = _get_vnf_package_id(context, vnfd_id)
    vnf_package_base_path = cfg.CONF.vnf_package.vnf_package_csar_path
    vnf_package_csar_path = vnf_package_base_path + '/' + vnf_package_id
    base_hot_dir = 'BaseHOT'
    ext = [".yaml", ".yml"]

    base_hot_path = vnf_package_csar_path + '/' + \
        base_hot_dir + '/' + flavour_id
    base_hot_dict = None
    nested_hot_path = base_hot_path + '/nested'
    nested_hot_dict = {}
    if os.path.exists(base_hot_path):
        for file in os.listdir(base_hot_path):
            if file.endswith(tuple(ext)):
                source_file_path = os.path.join(base_hot_path, file)
                base_hot_dict = yaml.safe_load(open(source_file_path))
    if os.path.exists(nested_hot_path):
        for file in os.listdir(nested_hot_path):
            if file.endswith(tuple(ext)):
                source_file_path = os.path.join(nested_hot_path, file)
                nested_hot = yaml.safe_load(open(source_file_path))
                nested_hot_dict[file] = nested_hot
    LOG.debug("Loaded base hot: %s", base_hot_dict)
    LOG.debug("Loaded nested_hot_dict: %s", nested_hot_dict)
    return base_hot_dict, nested_hot_dict
