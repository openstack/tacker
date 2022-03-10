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
        instantiated_vnf_info=inst_vnf_info,
        vnf_metadata={'namespace': 'default'},
        tenant_id=uuidsentinel.tenant_id)

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


def _get_ext_link_port(ext_vl_port_id, cp_instance_id,
        set_resource_id=False):
    if set_resource_id:
        resource_id = uuidsentinel.ext_virtual_link_port_resource_id
    else:
        resource_id = ""

    resource_handle = objects.ResourceHandle(
        resource_id=resource_id,
        vim_level_resource_type="OS::Neutron::Port")

    ext_vl_port = objects.ExtLinkPortInfo(
        id=ext_vl_port_id, cp_instance_id=cp_instance_id,
        resource_handle=resource_handle)

    return ext_vl_port


def get_ext_virtual_link_info(ext_virtual_link_id, desc_id="externalVL1",
        set_resource_id=True):

    network_resource = objects.ResourceHandle(
        resource_id=uuidsentinel.virtual_link_resource_id,
        vim_level_resource_type="OS::Neutron::Network")

    ext_vl_link_port = _get_ext_link_port(
        uuidsentinel.ext_vl_port_id,
        cp_instance_id=uuidsentinel.cp_instance_id,
        set_resource_id=set_resource_id)

    ext_vl_info = objects.ExtVirtualLinkInfo(
        id=uuidsentinel.ext_virtual_link_id,
        resource_handle=network_resource,
        ext_link_ports=[ext_vl_link_port])

    return ext_vl_info


def get_ext_cp_info(ext_cp_id, cpd_id='VDU1_CP1', ip_addresses=[]):

    ip_over_ethernet = objects.IpOverEthernetAddressInfo(
        ip_addresses=ip_addresses)

    cp_protocol_info = objects.CpProtocolInfo(
        layer_protocol="IP_OVER_ETHERNET",
        ip_over_ethernet=ip_over_ethernet)

    ext_cp_info = objects.VnfExtCpInfo(
        id=ext_cp_id,
        cpd_id=cpd_id,
        cp_protocol_info=[cp_protocol_info])

    return ext_cp_info


def get_ip_address(ip_type='IPV4', subnet_id=None, is_dynamic=False,
        addresses=[]):
    ip_address = objects.IpAddress(type=ip_type,
                                   subnet_id=subnet_id,
                                   is_dynamic=is_dynamic,
                                   addresses=addresses)
    return ip_address


def get_vnf_instantiated_info(flavour_id='simple',
        instantiation_level_id=None, vnfc_resource_info=None,
        virtual_storage_resource_info=None,
        vnf_virtual_link_resource_info=None,
        ext_managed_virtual_link_info=None,
        ext_virtual_link_info=None,
        ext_cp_info=None):

    vnfc_resource_info = vnfc_resource_info or []
    vnf_virtual_link_resource_info = vnf_virtual_link_resource_info or []
    virtual_storage_resource_info = virtual_storage_resource_info or []
    ext_managed_virtual_link_info = ext_managed_virtual_link_info or []
    ext_virtual_link_info = ext_virtual_link_info or []
    ext_cp_info = ext_cp_info or []

    inst_vnf_info = objects.InstantiatedVnfInfo(flavour_id=flavour_id,
        instantiation_level_id=instantiation_level_id,
        instance_id=uuidsentinel.instance_id,
        vnfc_resource_info=vnfc_resource_info,
        vnf_virtual_link_resource_info=vnf_virtual_link_resource_info,
        virtual_storage_resource_info=virtual_storage_resource_info,
        ext_managed_virtual_link_info=ext_managed_virtual_link_info,
        ext_virtual_link_info=ext_virtual_link_info,
        ext_cp_info=ext_cp_info)

    return inst_vnf_info


def get_vnf_software_image_object(image_path=None):
    image_path = image_path or ("http://download.cirros-cloud.net/0.5.2/"
                 "cirros-0.5.2-x86_64-disk.img")
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


def get_change_ext_conn_request():

    def _get_ip_addresses(_type='IPV4', fixed_addrs=[], subnet_id=None):
        if fixed_addrs and subnet_id:
            return [{
                "type": _type,
                "fixed_addresses": fixed_addrs,
                "subnet_id": subnet_id,
            }]
        elif fixed_addrs and not subnet_id:
            return [{
                "type": _type,
                "fixed_addresses": fixed_addrs,
            }]
        elif not fixed_addrs and subnet_id:
            return [{
                "type": _type,
                "num_dynamic_addresses": 1,
                "subnet_id": subnet_id,
            }]
        elif not fixed_addrs and not subnet_id:
            return [{
                "type": _type,
                "num_dynamic_addresses": 1,
            }]

    def _get_ext_cp_info(cpd_id, ip_address):
        return {
            "cpd_id": cpd_id,
            "cp_config": [{
                "cp_protocol_data": [{
                    "layer_protocol": "IP_OVER_ETHERNET",
                    "ip_over_ethernet": {
                        "ip_addresses": ip_address
                    }
                }]
            }]
        }

    def _get_request():
        ext_vl_info = [{
            "id": "external_network_1",
            "vim_connection_id": uuidsentinel.vim_connection_id,
            "resource_id": "nw-resource-id-1",
            "ext_cps": [
                _get_ext_cp_info('VDU1_CP1',
                    _get_ip_addresses(fixed_addrs=["20.0.0.1"])),
                _get_ext_cp_info('VDU1_CP2',
                    _get_ip_addresses(
                        fixed_addrs=["30.0.0.2"],
                        subnet_id="changed-subnet-id-1")),
                _get_ext_cp_info('VDU1_CP3',
                    _get_ip_addresses(fixed_addrs=["10.0.0.1"])),
            ]}, {
            "id": "external_network_2",
            "vim_connection_id": uuidsentinel.vim_connection_id,
            "resource_id": "changed-nw-resource-id-2",
            "ext_cps": [
                _get_ext_cp_info('VDU2_CP1',
                    _get_ip_addresses(
                        subnet_id="changed-subnet-id-2")),
                _get_ext_cp_info('VDU2_CP2', _get_ip_addresses())
            ]
        }]

        vim_connection_info = [{
            "id": uuidsentinel.vim_connection_id,
            "vim_id": uuidsentinel.vim_id,
            "vim_type": "ETSINFV.OPENSTACK_KEYSTONE.v_2",
            "interface_info": {
                "endpoint": "endpoint_value"},
            "access_info": {
                "username": "username_value",
                "password": "password_value",
                "region": "region_value",
                "tenant": "tenant_value"}}]

        change_ext_conn_data = {
            'ext_virtual_links': ext_vl_info,
            'vim_connection_info': vim_connection_info,
            'additional_params': {'key1': 'value1'}}

        return change_ext_conn_data

    change_ext_conn_data = _get_request()
    change_ext_conn_req = objects.ChangeExtConnRequest.obj_from_primitive(
        change_ext_conn_data, None)

    return change_ext_conn_req


def get_original_stack_param():
    stack_param = \
        {'nfv': {
            'VDU': {
                'VDU1': {'flavor': 'm1.tiny', 'image': 'None'},
                'VirtualStorage': {
                    'flavor': 'None',
                    'image': 'cirros-0.5.2-x86_64-disk'},
                'VDU2': {
                    'flavor': 'm1.tiny',
                    'image': 'cirros-0.5.2-x86_64-disk'}},
                'CP': {
                    'VDU1_CP1': {
                        'network': 'nw-resource-id-1',
                        'fixed_ips': [{'ip_address': '10.0.0.1'}]},
                    'VDU1_CP2': {
                        'network': 'nw-resource-id-1',
                        'fixed_ips': [{
                            'ip_address': '10.0.0.2',
                            'subnet': 'subnet-id-2'}]},
                    'VDU2_CP1': {
                        'network': 'nw-resource-id-2',
                        'fixed_ips': [{
                            'subnet': 'subnet-id-2'}]},
                    'VDU2_CP2': {'network': 'nw-resource-id-2'}}}}
    return stack_param


def get_expect_stack_param():
    stack_param = \
        {'nfv': {
            'VDU': {
                'VDU1': {'flavor': 'm1.tiny', 'image': 'None'},
                'VirtualStorage': {
                    'flavor': 'None',
                    'image': 'cirros-0.5.2-x86_64-disk'},
                'VDU2': {
                    'flavor': 'm1.tiny',
                    'image': 'cirros-0.5.2-x86_64-disk'}},
                'CP': {
                    'VDU1_CP1': {
                        'network': 'nw-resource-id-1',
                        'fixed_ips': [{'ip_address': '20.0.0.1'}]},
                    'VDU1_CP2': {
                        'network': 'nw-resource-id-1',
                        'fixed_ips': [{
                            'ip_address': '30.0.0.2',
                            'subnet': 'changed-subnet-id-1'}]},
                    'VDU2_CP1': {
                        'network': 'changed-nw-resource-id-2',
                        'fixed_ips': [{
                            'subnet': 'changed-subnet-id-2'}]},
                    'VDU2_CP2': {'network': 'changed-nw-resource-id-2'}}}}

    return stack_param


def get_vnf_attribute_dict():
    vnf_attribute_dict = dict()
    vnf_attribute_dict.update(
        {'stack_param': str(get_original_stack_param())})

    return vnf_attribute_dict


def get_stack_template():
    stack_template = {
        'heat_template_version': '2013-05-23',
        'description': 'Simple deployment flavour for Sample VNF',
        'parameters': {},
        'resources': {
            'VDU1': {
                'type': 'OS::Nova::Server',
                'properties': {
                    'name': 'VDU1',
                    'flavor': 'm1.tiny',
                    'image': 'None',
                    'networks': [
                        {
                            'port': {'get_resource': 'VDU1_CP1'},
                        }, {
                            'port': {'get_resource': 'VDU1_CP2'},
                        }
                    ],
                },
            },
            'VDU1_CP1': {
                'type': 'OS::Neutron::Port',
                'properties': {
                    'network': "nw-resource-id-1",
                    'fixed_ips': [{
                        'ip_address': '10.10.0.1',
                    }],
                },
            },
            'VDU1_CP2': {
                'type': 'OS::Neutron::Port',
                'properties': {
                    'network': "nw-resource-id-1",
                    'fixed_ips': [{
                        'ip_address': '10.10.0.2',
                        'subnet': 'subnet-id-2',
                    }],
                },
            },
        },
    }

    return stack_template


def get_stack_nested_template():
    stack_nested_template = {
        'heat_template_version': '2013-05-23',
        'description': 'Simple deployment flavour for Sample VNF',
        'parameters': {},
        'resources': {
            'VDU2': {
                'type': 'OS::Nova::Server',
                'properties': {
                    'name': 'VDU2',
                    'flavor': 'm1.tiny',
                    'image': 'cirros-0.4.0-x86_64-disk',
                    'networks': [
                        {
                            'port': {'get_resource': 'VDU2_CP1'},
                        }, {
                            'port': {'get_resource': 'VDU2_CP2'},
                        }
                    ],
                },
            },
            'VDU2_CP1': {
                'type': 'OS::Neutron::Port',
                'properties': {
                    'network': 'nw-resource-id-2',
                    'fixed_ips': [{
                        'subnet': 'subnet-id-2',
                    }],
                },
            },
            'VDU2_CP2': {
                'type': 'OS::Neutron::Port',
                'properties': {
                    'network': 'nw-resource-id-2',
                },
            },
        },
    }

    return stack_nested_template


def get_expected_update_resource_property_calls():
    calls = {
        'VDU1_CP1': {
            'resource_types': ['OS::Neutron::Port'],
            'network': 'nw-resource-id-1',
            'fixed_ips': [{
                'ip_address': '20.0.0.1'
            }],
        },
        'VDU1_CP2': {
            'resource_types': ['OS::Neutron::Port'],
            'network': 'nw-resource-id-1',
            'fixed_ips': [{
                'ip_address': '30.0.0.2',
                'subnet': 'changed-subnet-id-1',
            }],
        },
        'VDU1_CP3': {
            'resource_types': ['OS::Neutron::Port'],
            'network': 'nw-resource-id-1',
            'fixed_ips': [{
                'ip_address': '10.0.0.1'
            }],
        },
        'VDU2_CP1': {
            'resource_types': ['OS::Neutron::Port'],
            'network': 'changed-nw-resource-id-2',
            'fixed_ips': [{
                'subnet': 'changed-subnet-id-2',
            }],
        },
        'VDU2_CP2': {
            'resource_types': ['OS::Neutron::Port'],
            'network': 'changed-nw-resource-id-2',
            'fixed_ips': None,
        },
    }
    return calls


def get_lcm_op_occs_object(operation="INSTANTIATE",
        error_point=0):
    vnf_lcm_op_occs = objects.VnfLcmOpOcc(
        id=uuidsentinel.lcm_op_occs_id,
        tenant_id=uuidsentinel.tenant_id,
        operation_state='PROCESSING',
        state_entered_time='2019-03-06T05:44:27Z',
        start_time='2019-03-06T05:44:27Z',
        operation=operation,
        is_automatic_invocation=0,
        is_cancel_pending=0,
        error_point=error_point)

    return vnf_lcm_op_occs


def get_vnfc_resource_info_with_vnf_info(vdu_id="workerNode",
                                      storage_resource_ids=None):
    storage_resource_ids = storage_resource_ids or []

    vnfc_cp_info = _get_vnfc_cp_info_with_vnf_info(cpd_id='workerNode_CP2')

    vnfc_resource_info = objects.VnfcResourceInfo(
        id=uuidsentinel.vnfc_resource_id, vdu_id=vdu_id,
        vnfc_cp_info=[vnfc_cp_info],
        storage_resource_ids=storage_resource_ids)

    return vnfc_resource_info


def _get_vnfc_cp_info_with_vnf_info(cpd_id="CP1"):
    vnfc_cp_info = objects.VnfcCpInfo(
        id=uuidsentinel.vnfc_cp_info_id,
        cpd_id=cpd_id)

    return vnfc_cp_info


def get_virtual_storage_resource_info_for_grant(desc_id="VirtualStorage"):

    storage_resource_info = objects.VirtualStorageResourceInfo(
        id=uuidsentinel.storage_id_1,
        virtual_storage_desc_id=desc_id)

    return storage_resource_info


def _make_add_resources(req_add_resources):
    add_resources = []
    for req_add_resource in req_add_resources:
        res_add_resource = {
            "resourceDefinitionId": req_add_resource['id'],
            "vimConnectionId": uuidsentinel.vim_connection_id
        }

        if req_add_resource['type'] == 'COMPUTE':
            res_add_resource["zoneId"] = uuidsentinel.zone_id

        add_resources.append(res_add_resource)

    return add_resources
