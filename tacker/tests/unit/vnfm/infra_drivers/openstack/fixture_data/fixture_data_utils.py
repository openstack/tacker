# Copyright 2019 NTT DATA
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import os
import yaml

from tacker import objects
from tacker.objects import fields
from tacker.tests import uuidsentinel


def get_dummy_stack(outputs=True, status='CREATE_COMPELETE', attrs=None):
    outputs_value = [{}]
    if outputs:
        outputs_value = [{'output_value': '192.168.120.216',
                         'output_key': 'mgmt_ip-VDU1',
                         'description': 'No description given'}]

    dummy_stack = {'parent': None, 'disable_rollback': True,
            'description': 'Demo example\n',
            'deletion_time': None, 'stack_name':
                'vnf-6_3f089d15-0000-4dc0-8519-a613d577a07b',
            'stack_status_reason': 'Stack CREATE completed successfully',
            'creation_time': '2019-02-28T15:17:48Z',
            'outputs': outputs_value,
            'timeout_mins': 10, 'stack_status': status,
            'stack_owner': None,
            'updated_time': None,
            'id': uuidsentinel.instance_id}
    if attrs:
        dummy_stack.update(attrs)
    return dummy_stack


def get_dummy_resource(resource_status='CREATE_COMPLETE',
        resource_name='SP1_group', physical_resource_id=uuidsentinel.stack_id,
        resource_type='OS::Heat::AutoScalingGroup'):
    return {'resource_name': resource_name,
            'logical_resource_id': 'SP1_group',
            'creation_time': '2019-03-06T08:57:47Z',
            'resource_status_reason': 'state changed',
            'updated_time': '2019-03-06T08:57:47Z',
            'required_by': ['SP1_scale_out', 'SP1_scale_in'],
            'resource_status': resource_status,
            'physical_resource_id': physical_resource_id,
            'attributes': {'outputs_list': None, 'refs': None,
                           'refs_map': None, 'outputs': None,
                           'current_size': None, 'mgmt_ip-vdu1': 'test1'},
            'resource_type': resource_type}


def get_dummy_event(resource_status='CREATE_COMPLETE'):
    return {'resource_name': 'SP1_scale_out',
            'event_time': '2019-03-06T05:44:27Z',
            'logical_resource_id': 'SP1_scale_out',
            'resource_status': resource_status,
            'resource_status_reason': 'state changed',
            'id': uuidsentinel.event_id}


def get_dummy_policy_dict():
    return {'instance_id': uuidsentinel.instance_id,
            'vnf': {'attributes': {'scaling_group_names': '{"SP1": "G1"}'},
                    'id': uuidsentinel.vnf_id},
            'name': 'SP1',
            'action': 'out',
            'type': 'tosca.policies.tacker.Scaling',
            'properties': {}}


def get_vnf_instance_object(instantiated_vnf_info=None,
        instantiation_state=fields.VnfInstanceState.NOT_INSTANTIATED):

    inst_vnf_info = instantiated_vnf_info or get_vnf_instantiated_info()

    vnf_instance = objects.VnfInstance(id=uuidsentinel.vnf_instance_id,
        vnf_instance_name="Test-Vnf-Instance",
        vnf_instance_description="vnf instance description",
        instantiation_state=instantiation_state, vnfd_id=uuidsentinel.vnfd_id,
        vnf_provider="sample provider", vnf_product_name="vnf product name",
        vnf_software_version='1.0', vnfd_version="2",
        instantiated_vnf_info=inst_vnf_info)

    return vnf_instance


def get_virtual_storage_resource_info(desc_id="VirtualStorage",
        set_resource_id=True):

    if set_resource_id:
        resource_id = uuidsentinel.storage_resource_id
    else:
        resource_id = ""

    resource_handle = objects.ResourceHandle(
        resource_id=resource_id,
        vim_level_resource_type="OS::Cinder::Volume")

    storage_resource_info = objects.VirtualStorageResourceInfo(
        id=uuidsentinel.storage_id,
        virtual_storage_desc_id=desc_id,
        storage_resource=resource_handle)

    return storage_resource_info


def _get_virtual_link_port(virtual_link_port_id, cp_instance_id,
        set_resource_id=False):

    if set_resource_id:
        resource_id = uuidsentinel.virtual_link_port_resource_id
    else:
        resource_id = ""

    resource_handle = objects.ResourceHandle(
        resource_id=resource_id,
        vim_level_resource_type="OS::Neutron::Port")

    v_l_port = objects.VnfLinkPortInfo(
        id=virtual_link_port_id, cp_instance_id=cp_instance_id,
        resource_handle=resource_handle)

    return v_l_port


def get_virtual_link_resource_info(virtual_link_port_id, cp_instance_id,
        desc_id="internalVL1", set_resource_id=True):

    network_resource = objects.ResourceHandle(
        resource_id=uuidsentinel.virtual_link_resource_id,
        vim_level_resource_type="OS::Neutron::Network")

    v_l_link_port = _get_virtual_link_port(virtual_link_port_id,
            cp_instance_id=cp_instance_id, set_resource_id=set_resource_id)

    v_l_resource_info = objects.VnfVirtualLinkResourceInfo(
        id=uuidsentinel.v_l_resource_info_id,
        vnf_virtual_link_desc_id=desc_id,
        network_resource=network_resource, vnf_link_ports=[v_l_link_port])

    return v_l_resource_info


def _get_ext_virtual_link_port(ext_v_l_port_id, cp_instance_id,
        set_resource_id=False):
    if set_resource_id:
        resource_id = uuidsentinel.ext_virtual_link_port_resource_id
    else:
        resource_id = ""

    resource_handle = objects.ResourceHandle(
        resource_id=resource_id,
        vim_level_resource_type="OS::Neutron::Port")

    ext_v_l_port = objects.VnfLinkPortInfo(
        id=ext_v_l_port_id, cp_instance_id=cp_instance_id,
        resource_handle=resource_handle)

    return ext_v_l_port


def get_ext_managed_virtual_link_resource_info(virtual_link_port_id,
        cp_instance_id, desc_id="externalVL1", set_resource_id=True):
    network_resource = objects.ResourceHandle(
        resource_id=uuidsentinel.ext_managed_virtual_link_resource_id)

    ext_v_l_link_port = _get_ext_virtual_link_port(virtual_link_port_id,
            cp_instance_id=cp_instance_id, set_resource_id=set_resource_id)

    ext_managed_v_l_resource_info = objects.ExtManagedVirtualLinkInfo(
        id=uuidsentinel.v_l_resource_info_id,
        vnf_virtual_link_desc_id=desc_id,
        network_resource=network_resource,
        vnf_link_ports=[ext_v_l_link_port])

    return ext_managed_v_l_resource_info


def _get_vnfc_cp_info(virtual_link_port_id, cpd_id="CP1"):
    vnfc_cp_info = objects.VnfcCpInfo(
        id=uuidsentinel.vnfc_cp_info_id,
        cpd_id=cpd_id,
        cp_protocol_info=[],
        vnf_link_port_id=virtual_link_port_id)

    return vnfc_cp_info


def get_vnfc_resource_info(vdu_id="VDU1", storage_resource_ids=None,
        set_resource_id=True):
    storage_resource_ids = storage_resource_ids or []

    if set_resource_id:
        resource_id = uuidsentinel.vdu_resource_id
    else:
        resource_id = ""

    resource_handle = objects.ResourceHandle(
        resource_id=resource_id,
        vim_level_resource_type="OS::Nova::Server")

    vnfc_cp_info = _get_vnfc_cp_info(uuidsentinel.virtual_link_port_id)

    vnfc_resource_info = objects.VnfcResourceInfo(
        id=uuidsentinel.vnfc_resource_id, vdu_id=vdu_id,
        compute_resource=resource_handle, vnfc_cp_info=[vnfc_cp_info],
        storage_resource_ids=storage_resource_ids)

    return vnfc_resource_info


def get_vnf_instantiated_info(flavour_id='simple',
        instantiation_level_id=None, vnfc_resource_info=None,
        virtual_storage_resource_info=None,
        vnf_virtual_link_resource_info=None,
        ext_managed_virtual_link_info=None):

    vnfc_resource_info = vnfc_resource_info or []
    vnf_virtual_link_resource_info = vnf_virtual_link_resource_info or []
    virtual_storage_resource_info = virtual_storage_resource_info or []
    ext_managed_virtual_link_info = ext_managed_virtual_link_info or []

    inst_vnf_info = objects.InstantiatedVnfInfo(flavour_id=flavour_id,
        instantiation_level_id=instantiation_level_id,
        instance_id=uuidsentinel.instance_id,
        vnfc_resource_info=vnfc_resource_info,
        vnf_virtual_link_resource_info=vnf_virtual_link_resource_info,
        virtual_storage_resource_info=virtual_storage_resource_info,
        ext_managed_virtual_link_info=ext_managed_virtual_link_info)

    return inst_vnf_info


def get_vnf_software_image_object(image_path=None):
    image_path = image_path or ("http://download.cirros-cloud.net/0.4.0/"
                 "cirros-0.4.0-x86_64-disk.img")
    vnf_software_image = objects.VnfSoftwareImage(
        name='test-image', image_path=image_path,
        min_disk=10, min_ram=4, disk_format="qcow2",
        container_format="bare", hash="hash")

    return vnf_software_image


def get_fake_glance_image_dict(image_path=None, status='pending_create',
        hash_value='hash'):
    """Create a fake glance image.

    :return:
        Glance image dict with id, name, etc.
    """

    if not image_path:
        image_path = "http://localhost/cirros.img"

    image_attrs = {"name": 'test-image', "image_path": image_path,
                   "id": uuidsentinel.image_id,
                   "min_disk": "fake_description",
                   "min_ram": "0",
                   "disk_format": "qcow2",
                   "container_format": "bare",
                   "hash_value": hash_value,
                   "status": status}

    return image_attrs


def get_vnf_resource_object(resource_name="VDU1",
        resource_type="OS::Nova::Server"):
    vnf_resource = objects.VnfResource(
        resource_identifier=uuidsentinel.resource_identifier,
        id=uuidsentinel.vnf_resource_id,
        resource_name=resource_name,
        resource_type=resource_type,
        vnf_instance_id=uuidsentinel.vnf_instance_id)

    return vnf_resource


def get_vim_connection_info_object():
    access_info = {'auth_url': 'http://127.0.1.0/identity/v3',
                   'cert_verify': True,
                   'password': 'devstack',
                   'project_name': 'nfv',
                   'username': 'nfv_user'}

    vim_connection = objects.VimConnectionInfo(
        id=uuidsentinel.vim_connection_id, vim_id=uuidsentinel.vim_id,
        vim_type='openstack', access_info=access_info)

    return vim_connection


def get_vnfd_dict():
    filename = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "../data/",
        'test_tosca_image.yaml')
    with open(filename) as f:
        vnfd_dict = {'vnfd': {'attributes': {'vnfd': str(yaml.safe_load(f))}}}
        vnfd_dict.update({'id': '7ed39362-c551-4ce7-9ad2-17a98a6cee3d',
            'name': None, 'attributes': {'param_values': "",
            'stack_name': 'vnflcm_7ed39362-c551-4ce7-9ad2-17a98a6cee3d'},
            'placement_attr': {'region_name': None}})

    return vnfd_dict


def get_instantiate_vnf_request():
    inst_vnf_req = objects.InstantiateVnfRequest(
        flavour_id='simple')

    return inst_vnf_req


def get_grant_response_dict():
    grant_response_dict = {
        'VDU1': [get_vnf_resource_object(resource_name='VDU1')],
        'VirtualStorage': [get_vnf_resource_object(
            resource_name='VirtualStorage')]}

    return grant_response_dict
