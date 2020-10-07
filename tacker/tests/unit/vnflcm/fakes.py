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

from copy import deepcopy
import datetime
import iso8601
import os
import webob

from tacker.api.vnflcm.v1.router import VnflcmAPIRouter
from tacker import context
from tacker.db.db_sqlalchemy import models
from tacker import objects
from tacker.objects import fields
from tacker.objects.instantiate_vnf_req import ExtManagedVirtualLinkData
from tacker.objects.instantiate_vnf_req import ExtVirtualLinkData
from tacker.objects.instantiate_vnf_req import InstantiateVnfRequest
from tacker.objects import scale_vnf_request
from tacker.objects.vim_connection import VimConnectionInfo
from tacker.tests import constants
from tacker.tests import uuidsentinel
from tacker import wsgi

import tacker.db.vnfm.vnfm_db

import tacker.conf
CONF = tacker.conf.CONF


def return_default_vim():
    default_vim = {
        'vim_auth': {
            'username': 'user123',
            'password': 'pass123'
        },
        'placement_attr': {
            'region': 'RegionOne'
        },
        'tenant': uuidsentinel.tenant_uuid,
        'vim_id': uuidsentinel.vim_uuid,
        'vim_type': 'openstack'
    }

    return default_vim


def return_vim_connection_object(fields):
    access_info = {
        'username': fields.get('vim_auth', {}).
        get('username'),
        'password': fields.get('vim_auth', {}).
        get('password'),
        'region': fields.get('placement_attr', {}).
        get('region'),
        'tenant': fields.get('tenant')
    }

    vim_con_info = objects.\
        VimConnectionInfo(id=fields.get('vim_id'),
                          vim_id=fields.get('vim_id'),
                          vim_type=fields.get('vim_type'),
                          access_info=access_info)

    return vim_con_info


def fake_vnf_package_vnfd_model_dict(**updates):
    vnfd = {
        'package_uuid': uuidsentinel.package_uuid,
        'deleted': False,
        'deleted_at': None,
        'updated_at': None,
        'created_at': datetime.datetime(2020, 1, 1, 1, 1, 1,
                                        tzinfo=iso8601.UTC),
        'vnf_product_name': 'Sample VNF',
        'vnf_provider': 'test vnf provider',
        'vnf_software_version': '1.0',
        'vnfd_id': uuidsentinel.vnfd_id,
        'vnfd_version': '1.0',
        'id': constants.UUID,
    }

    if updates:
        vnfd.update(updates)

    return vnfd


def return_vnf_package_vnfd():
    model_obj = models.VnfPackageVnfd()
    model_obj.update(fake_vnf_package_vnfd_model_dict())
    return model_obj


def scale_request_make(type, number_of_steps):
    scale_request_data = {
        'type': type,
        'aspect_id': "SP1",
        'number_of_steps': number_of_steps,
        'scale_level': 1,
        'additional_params': {"test": "test_value"},
    }
    scale_request = scale_vnf_request.ScaleVnfRequest(**scale_request_data)

    return scale_request


def _model_non_instantiated_vnf_instance(**updates):
    vnf_instance = {
        'created_at': datetime.datetime(2020, 1, 1, 1, 1, 1,
                                        tzinfo=iso8601.UTC),
        'deleted': False,
        'deleted_at': None,
        'id': uuidsentinel.vnf_instance_id,
        'instantiated_vnf_info': None,
        'instantiation_state': fields.VnfInstanceState.NOT_INSTANTIATED,
        'updated_at': None,
        'vim_connection_info': [],
        'vnf_instance_description': 'Vnf instance description',
        'vnf_instance_name': 'Vnf instance name',
        'vnf_product_name': 'Sample VNF',
        'vnf_provider': 'Vnf provider',
        'vnf_software_version': '1.0',
        'tenant_id': uuidsentinel.tenant_id,
        'vnfd_id': uuidsentinel.vnfd_id,
        'vnfd_version': '1.0',
        'vnf_pkg_id': uuidsentinel.vnf_pkg_id,
        'vnf_metadata': {"key": "value"}}

    if updates:
        vnf_instance.update(**updates)

    return vnf_instance


def return_vnf_instance_model(
        instantiated_state=fields.VnfInstanceState.NOT_INSTANTIATED,
        **updates):

    model_obj = models.VnfInstance()

    if instantiated_state == fields.VnfInstanceState.NOT_INSTANTIATED:
        model_obj.update(_model_non_instantiated_vnf_instance(**updates))

    return model_obj


def return_vnf_instance(
        instantiated_state=fields.VnfInstanceState.NOT_INSTANTIATED,
        scale_status=None,
        **updates):

    if instantiated_state == fields.VnfInstanceState.NOT_INSTANTIATED:
        data = _model_non_instantiated_vnf_instance(**updates)
        data['instantiation_state'] = instantiated_state
        vnf_instance_obj = objects.VnfInstance(**data)

    elif scale_status:
        data = _model_non_instantiated_vnf_instance(**updates)
        data['instantiation_state'] = instantiated_state
        vnf_instance_obj = objects.VnfInstance(**data)

        get_instantiated_vnf_info = {
            'flavour_id': uuidsentinel.flavour_id,
            'vnf_state': 'STARTED',
            'instance_id': uuidsentinel.instance_id
        }
        instantiated_vnf_info = get_instantiated_vnf_info

        s_status = {"aspect_id": "SP1", "scale_level": 1}
        scale_status = objects.ScaleInfo(**s_status)

        instantiated_vnf_info.update(
            {"ext_cp_info": [],
            'ext_virtual_link_info': [],
            'ext_managed_virtual_link_info': [],
            'vnfc_resource_info': [],
            'vnf_virtual_link_resource_info': [],
            'virtual_storage_resource_info': [],
            "flavour_id": "simple",
            "scale_status": [scale_status],
            "vnf_instance_id": "171f3af2-a753-468a-b5a7-e3e048160a79",
            "additional_params": {"key": "value"},
           'vnf_state': "STARTED"})
        info_data = objects.InstantiatedVnfInfo(**instantiated_vnf_info)

        vnf_instance_obj.instantiated_vnf_info = info_data
    else:
        data = _model_non_instantiated_vnf_instance(**updates)
        data['instantiation_state'] = instantiated_state
        vnf_instance_obj = objects.VnfInstance(**data)
        inst_vnf_info = objects.InstantiatedVnfInfo.obj_from_primitive({
            "ext_cp_info": [],
            'ext_virtual_link_info': [],
            'ext_managed_virtual_link_info': [],
            'vnfc_resource_info': [],
            'vnf_virtual_link_resource_info': [],
            'virtual_storage_resource_info': [],
            "flavour_id": "simple",
            "additional_params": {"key": "value"},
            'vnf_state': "STARTED"}, None)

        vnf_instance_obj.instantiated_vnf_info = inst_vnf_info

    return vnf_instance_obj


def _instantiated_vnf_links(vnf_instance_id):
    links = {
        "self": {"href": "/vnflcm/v1/vnf_instances/%s" % vnf_instance_id},
        "terminate": {"href": "/vnflcm/v1/vnf_instances/%s/terminate" %
                      vnf_instance_id},
        "heal": {"href": "/vnflcm/v1/vnf_instances/%s/heal" %
                 vnf_instance_id}}

    return links


def _fake_vnf_instance_not_instantiated_response(
        **updates):
    vnf_instance = {
        'vnfInstanceDescription': 'Vnf instance description',
        'vnfInstanceName': 'Vnf instance name',
        'vnfProductName': 'Sample VNF',
        '_links': {
            'self': {
                'href': os.path.join(
                    '/vnflcm/v1/vnf_instances/',
                    uuidsentinel.vnf_instance_id)},
            'instantiate': {
                'href': os.path.join(
                    '/vnflcm/v1/vnf_instances',
                    uuidsentinel.vnf_instance_id,
                    'instantiate')}},
        'instantiationState': 'NOT_INSTANTIATED',
        'vnfProvider': 'Vnf provider',
        'vnfdId': uuidsentinel.vnfd_id,
        'vnfdVersion': '1.0',
        'vnfSoftwareVersion': '1.0',
        'id': uuidsentinel.vnf_instance_id,
        'metadata': {'key': 'value'}
    }

    if updates:
        vnf_instance.update(**updates)

    return vnf_instance


def fake_vnf_instance_response(
        instantiated_state=fields.VnfInstanceState.NOT_INSTANTIATED,
        api_version=None, **updates):
    if instantiated_state == fields.VnfInstanceState.NOT_INSTANTIATED:
        data = _fake_vnf_instance_not_instantiated_response(**updates)
    else:
        data = _fake_vnf_instance_not_instantiated_response(**updates)
        data['_links'] = _instantiated_vnf_links(uuidsentinel.vnf_instance_id)
        data['instantiationState'] = instantiated_state
        data['vimConnectionInfo'] = []

        def _instantiated_vnf_info():
            inst_vnf_info = {}
            inst_vnf_info['extCpInfo'] = []
            inst_vnf_info['flavourId'] = 'simple'
            inst_vnf_info['vnfState'] = 'STARTED'
            inst_vnf_info['additionalParams'] = {"key": "value"}
            return inst_vnf_info

        data['instantiatedVnfInfo'] = _instantiated_vnf_info()

    if api_version == '2.6.1':
        del data['vnfPkgId']

    return data


def fake_vnf_package(**updates):
    vnf_package = {
        'algorithm': None,
        'deleted': False,
        'deleted_at': None,
        'updated_at': None,
        'created_at': datetime.datetime(1900, 1, 1, 1, 1, 1,
                                        tzinfo=iso8601.UTC),
        'hash': None,
        'location_glance_store': None,
        'onboarding_state': 'CREATED',
        'operational_state': 'DISABLED',
        'tenant_id': uuidsentinel.tenant_id,
        'usage_state': 'NOT_IN_USE',
        'user_data': {'abc': 'xyz'},
        'id': constants.UUID,
    }

    if updates:
        vnf_package.update(updates)

    return vnf_package


def fake_vnf_package_deployment_flavour(**updates):
    vnf_package_deployment_data = {
        'flavour_description': 'flavour_description',
        'instantiation_levels': ('{"levels": {'
                                 '"instantiation_level_1":'
                                 '{"description": "Smallest size",'
                                 ' "scale_info": {"worker_instance":'
                                 '{"scale_level": 0}}}},'
                                 ' "default_level": '
                                 '"instantiation_level_1"}'),
        'package_uuid': constants.UUID,
        'flavour_id': 'simple',
    }

    if updates:
        vnf_package_deployment_data.update(updates)

    return vnf_package_deployment_data


def fake_vnf_package_software_image(**updates):
    vnf_package_software_image_data = {
        'id': constants.UUID,
        'name': 'name',
        'provider': 'provider',
        'version': 'version',
        'algorithm': 'algorithm',
        'hash': 'hash',
        'container_format': 'container_format',
        'disk_format': 'disk_format',
        'min_disk': 2,
        'min_ram': 10,
        'size': 5,
        'image_path': 'image/path',
        'flavour_uuid': constants.UUID,
        'software_image_id': constants.UUID,
        'created_at': datetime.datetime(1900, 1, 1, 1, 1, 1,
                                        tzinfo=iso8601.UTC)
    }

    if updates:
        vnf_package_software_image_data.update(updates)

    return vnf_package_software_image_data


def return_vnf_deployment_flavour():
    model_obj = models.VnfDeploymentFlavour()
    model_obj.update(fake_vnf_package_deployment_flavour())
    return model_obj


def return_vnf_software_image():
    model_obj = models.VnfSoftwareImage()
    model_obj.update(fake_vnf_package_software_image())
    return model_obj


def return_vnf_package():
    model_obj = models.VnfPackage()
    model_obj.update(fake_vnf_package())
    return model_obj


def return_vnf_package_with_deployment_flavour():
    vnf_package = objects.VnfPackage._from_db_object(
        context, objects.VnfPackage(), return_vnf_package(),
        expected_attrs=None)
    vnf_package_deployment_flavour = \
        objects.VnfDeploymentFlavour._from_db_object(
            context, objects.VnfDeploymentFlavour(),
            return_vnf_deployment_flavour(), expected_attrs=None)
    vnf_software_image = objects.VnfSoftwareImage._from_db_object(
        context, objects.VnfSoftwareImage(), return_vnf_software_image(),
        expected_attrs=None)
    vnf_software_image_list = objects.VnfSoftwareImagesList()
    vnf_software_image_list.objects = [vnf_software_image]
    vnf_package_deployment_flavour.software_images = vnf_software_image_list
    vnf_package_deployment_flavour_list = objects.VnfDeploymentFlavoursList()
    vnf_package_deployment_flavour_list.objects = \
        [vnf_package_deployment_flavour]
    vnf_package.vnf_deployment_flavours = vnf_package_deployment_flavour_list
    return vnf_package


def get_vnf_instantiation_request_body():
    instantiation_req_body = {
        "flavourId": "simple",
        "instantiationLevelId": "instantiation_level_1",
        "additionalParams": {"key1": 'value1', "key2": 'value2'},
        "extVirtualLinks": [{
            "id": 'f8c35bd0-4d67-4436-9f11-14b8a84c92aa',
            "resourceId": 'f8c35bd0-4d67-4436-9f11-14b8a84c92aa',
            "extCps": [{
                "cpdId": 'f8c35bd0-4d67-4436-9f11-14b8a84c92aa',
                "cpConfig": [{
                    "cpInstanceId": 'f8c35bd0-4d67-4436-9f11-14b8a84c92aa',
                    "linkPortId": 'f8c35bd0-4d67-4436-9f11-14b8a84c92aa',
                    "cpProtocolData": [
                        {
                            "layerProtocol": 'IP_OVER_ETHERNET',
                            "ipOverEthernet": {
                                "macAddress":
                                    'fa:16:3e:11:11:11',
                                "ipAddresses": [
                                    {
                                        "type": "IPV4",
                                        "fixedAddresses": [
                                            '192.168.11.01',
                                            '192.168.21.202'
                                        ],
                                        "subnetId":
                                            'actual-subnet-id'
                                    }
                                ]
                            }
                        }
                    ]
                }
                ]
            }],
            "extLinkPorts": [
                {
                    "id": 'f8c35bd0-4d67-4436-9f11-14b8a84c92aa',
                    "resourceHandle": {
                        "resourceId":
                            'f8c35bd0-4d67-4436-9f11-14b8a84c92aa',
                        "vimLevelResourceType":
                            'f8c35bd0-4d67-4436-9f11-14b8a84c92aa',
                    }
                },
                {
                    "id": 'f8c35bd0-4d67-4436-9f11-14b8a84c92aa',
                    "resourceHandle": {
                        "resourceId":
                            'f8c35bd0-4d67-4436-9f11-14b8a84c92aa',
                        "vimLevelResourceType":
                            'f8c35bd0-4d67-4436-9f11-14b8a84c92aa',
                    }
                }],
        }],
        "extManagedVirtualLinks": [
            {"id": 'f8c35bd0-4d67-4436-9f11-14b8a84c92aa',
             "vnfVirtualLinkDescId": 'f8c35bd0-4d67-4436-9f11-14b8a84c92aa',
             "resourceId": 'f8c35bd0-4d67-4436-9f11-14b8a84c92aa'},
            {"id": 'f8c35bd0-4d67-4436-9f11-14b8a84c92aa',
             "vnfVirtualLinkDescId": 'f8c35bd0-4d67-4436-9f11-14b8a84c92aa',
             "resourceId": 'f8c35bd0-4d67-4436-9f11-14b8a84c92aa'}],
        "vimConnectionInfo": [
            {"id": 'f8c35bd0-4d67-4436-9f11-14b8a84c92aa',
             "vimId": 'f8c35bd0-4d67-4436-9f11-14b8a84c92aa',
             "vimType": 'openstack',
             "accessInfo": {"key1": 'value1', "key2": 'value2'}}],
    }

    return instantiation_req_body


def get_instantiate_vnf_request_obj():
    instantiate_vnf_req = InstantiateVnfRequest()
    ext_managed_virtual_link_data = ExtManagedVirtualLinkData()
    vim_connection_info = VimConnectionInfo()
    ext_virtual_link_data = ExtVirtualLinkData()
    ext_managed_virtual_link_data.id = uuidsentinel.ext_id
    ext_managed_virtual_link_data.vnf_virtual_link_desc_id = 'VL3'
    ext_managed_virtual_link_data.resource_id = \
        'f8c35bd0-4d67-4436-9f11-14b8a84c92aa'
    ext_managed_virtual_link_data.vim_connection_id = \
        'f8c35bd0-4d67-4436-9f11-14b8a84c92aa'
    instantiate_vnf_req.additional_params = None
    instantiate_vnf_req.deleted = 0
    instantiate_vnf_req.ext_managed_virtual_links = \
        [ext_managed_virtual_link_data]
    instantiate_vnf_req.ext_virtual_link_data = [ext_virtual_link_data]
    instantiate_vnf_req.flavour_id = 'test'
    instantiate_vnf_req.instantiation_level_id = 'instantiation_level_1'
    instantiate_vnf_req.vim_connection_info = [vim_connection_info]

    return instantiate_vnf_req


def create_types_yaml_file():
    yaml_str = ("""imports:
  - etsi_nfv_sol001_common_types.yaml
  - etsi_nfv_sol001_vnfd_types.yaml

node_types:
  company.provider.VNF:
    derived_from: tosca.nodes.nfv.VNF
    properties:
      descriptor_id:
        type: string
        constraints: [ valid_values: [ b1bb0ce7-ebca-4fa7-95ed-4840d70a1177 ]]
        default: 1111
      descriptor_version:
        type: string
        constraints: [ valid_values: [ '1.0' ] ]
        default: 'fake desc version'
      provider:
        type: string
        constraints: [ valid_values: [ 'Company' ] ]
        default: 'Company'
      product_name:
        type: string
        constraints: [ valid_values: [ 'Sample VNF' ] ]
        default: 'fake product name'
      software_version:
        type: string
        constraints: [ valid_values: [ '1.0' ] ]
        default: 'fake software version'
      vnfm_info:
        type: list
        entry_schema:
          type: string
          constraints: [ valid_values: [ Tacker ] ]
        default: [ Tacker ]
      flavour_id:
        type: string
        constraints: [ valid_values: [ simple ] ]
        default: fake id
      flavour_description:
        type: string
        default: "fake flavour"
    requirements:
      - virtual_link_external:
          capability: tosca.capabilities.nfv.VirtualLinkable
      - virtual_link_internal:
          capability: tosca.capabilities.nfv.VirtualLinkable
    interfaces:
      Vnflcm:
        type: tosca.interfaces.nfv.Vnflcm""")
    file_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), 'types.yaml'))
    yaml_file = open(file_path, "w+")
    yaml_file.write(yaml_str)
    yaml_file.close()


def delete_types_yaml_file():
    file_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), 'types.yaml'))
    if os.path.exists(file_path):
        os.remove(file_path)


def create_vnfd_dict_file():
    vnfd_dict_str = str(get_vnfd_dict())
    file_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), 'vnfd_dict.yaml'))
    vnfd_dict_file = open(file_path, "w+")
    vnfd_dict_file.write(vnfd_dict_str)
    vnfd_dict_file.close()


def delete_vnfd_dict_yaml_file():
    file_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), 'vnfd_dict.yaml'))
    if os.path.exists(file_path):
        os.remove(file_path)


def get_vnfd_dict(image_path=None):

    if image_path is None:
        image_path = 'fake/image/path'

    vnfd_dict = {
        'description': 'Simple deployment flavour for Sample VNF',
        'imports': ['/opt/stack/tacker/tacker/tests/unit/vnflcm/types.yaml'],
        'topology_template':
            {'inputs': {'descriptor_id': {'type': 'string'},
                        'descriptor_version': {'type': 'string'},
                        'flavour_description': {'type': 'string'},
                        'flavour_id': {'type': 'string'},
                        'product_name': {'type': 'string'},
                        'provider': {'type': 'string'},
                        'software_version': {'type': 'string'},
                        'vnfm_info': {
                            'entry_schema': {'type': 'string'},
                            'type': 'list'}},
             'node_templates': {
                 'CP3': {'properties': {
                     'layer_protocols': ['ipv4'], 'order': 2},
                     'requirements': [{'virtual_binding': 'VDU1'},
                                      {'virtual_link': 'VL3'}],
                     'type': 'tosca.nodes.nfv.VduCp'},
                 'CP4': {'properties': {'layer_protocols': ['ipv4'],
                                        'order': 3},
                         'requirements': [{'virtual_binding': 'VDU1'},
                                          {'virtual_link': 'VL4'}],
                         'type': 'tosca.nodes.nfv.VduCp'},
                 'VDU1': {'artifacts': {
                     'sw_image': {
                         'file': image_path,
                         'type': 'tosca.artifacts.nfv.SwImage'}},
                     'capabilities': {
                         'virtual_compute': {'properties': {
                             'virtual_cpu': {'num_virtual_cpu': 1},
                             'virtual_local_storage': [
                                 {'size_of_storage': '1 ''GiB'}],
                             'virtual_memory': {
                                 'virtual_mem_size': '512 ''MiB'}}}},
                     'properties': {
                         'description': 'VDU1 compute node',
                         'name': 'VDU1',
                         'sw_image_data': {
                             'checksum': {
                                 'algorithm': 'fake algo',
                                 'hash': 'fake hash'},
                             'container_format':
                                 'fake container format',
                             'disk_format': 'fake disk format',
                             'min_disk': '1''GiB',
                             'name': 'fake name',
                             'size': 'fake size ' 'GiB',
                             'version': 'fake version'},
                         'vdu_profile': {
                             'max_number_of_instances': 1,
                             'min_number_of_instances': 1}},
                     'type': 'tosca.nodes.nfv.Vdu.Compute'},
                 'VL3': {'properties': {
                     'connectivity_type': {'layer_protocols': []},
                     'description': 'Internal virtual link in VNF',
                     'vl_profile': {
                         'max_bitrate_requirements': {
                             'leaf': 1048576,
                             'root': 1048576
                         },
                         'min_bitrate_requirements': {
                             'leaf': 1048576,
                             'root': 1048576
                         },
                         'virtual_link_protocol_data': [
                             {'layer_protocol': 'ipv4',
                              'l3_protocol_data': {}
                              }]}},
                         'type': 'tosca.nodes.nfv.VnfVirtualLink'},
                 'VL4': {'properties': {'connectivity_type': {
                     'layer_protocols': ['ipv4']},
                     'description': 'Internal virtual link in VNF',
                     'vl_profile': {}},
                     'type': 'tosca.nodes.nfv.VnfVirtualLink'},
                 'VNF': {'interfaces': {'Vnflcm': {
                     'instantiate': [],
                     'instantiate_end': [],
                     'instantiate_start': [],
                     'modify_information': [],
                     'modify_information_end': [],
                     'modify_information_start': [], 'terminate': [],
                     'terminate_end': [], 'terminate_start': []}},
                     'properties': {
                         'flavour_description': 'A simple flavor'},
                     'type': 'company.provider.VNF'}},
             'substitution_mappings': {
                 'node_type': 'company.provider.VNF',
                 'properties': {'flavour_id': 'simple'},
                 'requirements': {
                     'virtual_link_external': [
                         'CP1', 'virtual_link']}}},
        'tosca_definitions_version': 'tosca_simple_yaml_1_2'}

    return vnfd_dict


def get_dummy_vnf_instance():
    connection_info = get_dummy_vim_connection_info()
    return {'created_at': '', 'deleted': False, 'deleted_at': None,
            'id': 'fake_id', 'instantiated_vnf_info': None,
            'instantiation_state': 'NOT_INSTANTIATED',
            'tenant_id': 'fake_tenant_id', 'updated_at': '',
            'vim_connection_info': [connection_info],
            'vnf_instance_description': 'VNF Description',
            'vnf_instance_name': 'test', 'vnf_product_name': 'Sample VNF',
            'vnf_provider': 'Company', 'vnf_software_version': '1.0',
            'vnfd_id': 'fake_vnfd_id', 'vnfd_version': '1.0'}


def get_dummy_vim_connection_info():
    return {'access_info': {
        'auth_url': 'fake/url',
        'cert_verify': 'False', 'password': 'admin',
        'project_domain_name': 'Default',
        'project_id': None, 'project_name': 'admin',
        'user_domain_name': 'Default', 'username': 'admin'},
        'created_at': '', 'deleted': False, 'deleted_at': '',
        'id': 'fake_id', 'updated_at': '',
        'vim_id': 'fake_vim_id', 'vim_type': 'openstack'}


def get_dummy_instantiate_vnf_request(**updates):
    instantiate_vnf_request = {
        'additional_params': None, 'created_at': '', 'deleted': '',
        'deleted_at': '', 'flavour_id': 'simple',
        'instantiation_level_id': 'instantiation_level_1',
        'updated_at': '', 'vim_connection_info': []}

    if updates:
        instantiate_vnf_request['vim_connection_info'].append(updates)

    return instantiate_vnf_request


def get_instantiate_vnf_request_with_ext_virtual_links(**updates):
    instantiate_vnf_request = \
        {"flavourId": "simple",
         "instantiationLevelId": "instantiation_level_1",
         "extVirtualLinks": [{
             "id": "ext-vl-uuid-VL1",
             "vimConnectionId": "8a3adb69-0784-43c7-833e-aab0b6ab4470",
             "resourceId": "f671ea41-bb4a-4b86-b6bd-b058f68f0498",
             "extCps": [{
                 "cpdId": "CP1",
                 "cpConfig": [{
                     "linkPortId": "ee2982f6-8d0d-4649-9357-e527bcb68ed1",
                     "cpProtocolData": [{
                         "layerProtocol": "IP_OVER_ETHERNET",
                         "ipOverEthernet": {
                             "ipAddresses": [{
                                 "type": "IPV4",
                                 "fixedAddresses": ["192.168.120.95"],
                                 "subnetId": "f577b050-b80a-baed-96db88cd529b"
                             }]}}]}]}]},
             {
                 "id": "ext-vl-uuid-VL1",
                 "vimConnectionId": "8a3adb69-0784-43c7-833e-aab0b6ab4470",
                 "resourceId": "f671ea41-bb4a-4b86-b6bd-b058f68f0498",
                 "extCps": [{
                     "cpdId": "CP2",
                     "cpConfig": [{
                         "cpProtocolData": [{
                             "layerProtocol": "IP_OVER_ETHERNET",
                             "ipOverEthernet": {
                                 "ipAddresses": [{
                                     "type": "IPV4",
                                     "fixedAddresses": ["192.168.120.96"],
                                     "subnetId": "f577b050-b80a-96db88cd529b"
                                 }]}}]}]}]}],
         "extManagedVirtualLinks": [{
             "id": "extMngVLnk-uuid_VL3",
             "vnfVirtualLinkDescId": "VL3",
             "vimConnectionId": "8a3adb69-0784-43c7-833e-aab0b6ab4470",
             "resourceId": "f671ea41-bb4a-4b86-b6bd-b058f68f0498"
         }],
         "vimConnectionInfo": []
         }

    if updates:
        instantiate_vnf_request.update(updates)

    return instantiate_vnf_request


def _get_vnf(**updates):
    vnf_data = {
        'tenant_id': uuidsentinel.tenant_id,
        'name': "fake_name",
        'vnfd_id': uuidsentinel.vnfd_id,
        'vnf_instance_id': uuidsentinel.instance_id,
        'mgmt_ip_address': "fake_mgmt_ip_address",
        'status': 'ACTIVE',
        'description': 'fake_description',
        'placement_attr': 'fake_placement_attr',
        'vim_id': 'uuidsentinel.vim_id',
        'error_reason': 'fake_error_reason',
        'instance_id': uuidsentinel.instance_id,
        'attributes': {
            "scale_group": '{"scaleGroupDict" : {"SP1": {"maxLevel" : 3}}}',
            "heat_template": os.path.dirname(__file__) +
            "/../../etc/samples/hot_lcm_template.yaml"}}

    if updates:
        vnf_data.update(**updates)

    return vnf_data


def scale_request(type, number_of_steps, is_reverse):
    scale_request_data = {
        'type': type,
        'aspect_id': "SP1",
        'number_of_steps': number_of_steps,
        'scale_level': 1,
        'additional_params': {"is_reverse": is_reverse},
    }
    scale_request = \
        scale_vnf_request.ScaleVnfRequest(**scale_request_data)

    return scale_request


def get_dummy_grant_response():
    return {'VDU1': {'checksum': {'algorithm': 'fake algo',
                                  'hash': 'fake hash'},
                     'container_format': 'fake container format',
                     'disk_format': 'fake disk format',
                     'image_path': ('/var/lib/tacker/vnfpackages/' +
                                    uuidsentinel.instance_id +
                                    '/Files/images/path'),
                     'min_disk': 1,
                     'min_ram': 0,
                     'name': 'fake name',
                     'version': 'fake version'}}


def return_vnf_resource():
    version_obj = objects.VnfResource(
        created_at=datetime.datetime(1900, 1, 1, 1, 1, 1, tzinfo=iso8601.UTC),
        deleted=False,
        deleted_at=None,
        id=uuidsentinel.vnf_resource_id,
        resource_identifier=uuidsentinel.resource_identifier,
        resource_name='test-image',
        resource_status='CREATED',
        resource_type='image',
        updated_at=None,
        vnf_instance_id=uuidsentinel.vnf_instance_id
    )
    return version_obj


def vnf_scale():
    return tacker.db.vnfm.vnfm_db.VNF(id=constants.UUID,
        vnfd_id=uuidsentinel.vnfd_id,
        name='test',
        status='ACTIVE',
        vim_id=uuidsentinel.vim_id)


def vnflcm_rollback(error_point=7):
    return objects.VnfLcmOpOcc(
        state_entered_time=datetime.datetime(2000, 1, 1, 1, 1, 1,
                                             tzinfo=iso8601.UTC),
        start_time=datetime.datetime(2000, 1, 1, 1, 1, 1,
                                     tzinfo=iso8601.UTC),
        vnf_instance_id=uuidsentinel.vnf_instance_id,
        operation='SCALE',
        operation_state='FAILED_TEMP',
        is_automatic_invocation=False,
        operation_params='{"type": "SCALE_OUT", "aspect_id": "SP1"}',
        error_point=error_point,
        id=constants.UUID,
        created_at=datetime.datetime(2000, 1, 1, 1, 1, 1,
                                     tzinfo=iso8601.UTC))


def vnflcm_rollback_insta(error_point=7):
    return objects.VnfLcmOpOcc(
        state_entered_time=datetime.datetime(2000, 1, 1, 1, 1, 1,
                                             tzinfo=iso8601.UTC),
        start_time=datetime.datetime(2000, 1, 1, 1, 1, 1,
                                     tzinfo=iso8601.UTC),
        vnf_instance_id=uuidsentinel.vnf_instance_id,
        operation='INSTANTIATION',
        operation_state='FAILED_TEMP',
        is_automatic_invocation=False,
        operation_params='{}',
        error_point=error_point,
        id=constants.UUID,
        created_at=datetime.datetime(2000, 1, 1, 1, 1, 1,
                                     tzinfo=iso8601.UTC))


def vnflcm_rollback_active():
    return objects.VnfLcmOpOcc(
        state_entered_time=datetime.datetime(2000, 1, 1, 1, 1, 1,
                                             tzinfo=iso8601.UTC),
        start_time=datetime.datetime(2000, 1, 1, 1, 1, 1,
                                     tzinfo=iso8601.UTC),
        vnf_instance_id=uuidsentinel.vnf_instance_id,
        operation='SCALE',
        operation_state='ACTIVE',
        is_automatic_invocation=False,
        operation_params='{"type": "SCALE_OUT", "aspect_id": "SP1"}',
        error_point=7,
        id=constants.UUID,
        created_at=datetime.datetime(2000, 1, 1, 1, 1, 1,
                                     tzinfo=iso8601.UTC))


def vnflcm_rollback_ope():
    return objects.VnfLcmOpOcc(
        state_entered_time=datetime.datetime(2000, 1, 1, 1, 1, 1,
                                             tzinfo=iso8601.UTC),
        start_time=datetime.datetime(2000, 1, 1, 1, 1, 1,
                                     tzinfo=iso8601.UTC),
        vnf_instance_id=uuidsentinel.vnf_instance_id,
        operation='HEAL',
        operation_state='FAILED_TEMP',
        is_automatic_invocation=False,
        operation_params='{}',
        error_point=7,
        id=constants.UUID,
        created_at=datetime.datetime(2000, 1, 1, 1, 1, 1,
                                     tzinfo=iso8601.UTC))


def vnflcm_rollback_scale_in():
    return objects.VnfLcmOpOcc(
        state_entered_time=datetime.datetime(2000, 1, 1, 1, 1, 1,
                                             tzinfo=iso8601.UTC),
        start_time=datetime.datetime(2000, 1, 1, 1, 1, 1,
                                     tzinfo=iso8601.UTC),
        vnf_instance_id=uuidsentinel.vnf_instance_id,
        operation='SCALE',
        operation_state='FAILED_TEMP',
        is_automatic_invocation=False,
        operation_params='{"type": "SCALE_IN", "aspect_id": "SP1"}',
        error_point=7,
        id=constants.UUID,
        created_at=datetime.datetime(2000, 1, 1, 1, 1, 1,
                                     tzinfo=iso8601.UTC))


def vnf_rollback():
    return tacker.db.vnfm.vnfm_db.VNF(id=constants.UUID,
                                      vnfd_id=uuidsentinel.vnfd_id,
                                      name='test',
                                      status='ERROR',
                                      vim_id=uuidsentinel.vim_id)


def vnf_dict():
    heat_temp = 'heat_template_version: ' + \
                '2013-05-23\ndescription: \'VNF Descriptor (TEST)' + \
                '\n\n  \'\nparameters:\n  current_num:\n    type: ' + \
                'number\n  nfv:\n    type: json\nresources:\n  ' + \
                'SP1_scale_out:\n    type: OS::Heat::ScalingPolicy\n' + \
                '    properties:\n      auto_scaling_group_id: ' + \
                '{get_resource: SP1_group}\n      adjustment_type: ' + \
                'change_in_capacity\n      scaling_adjustment: 1\n  ' + \
                'SP1_group:\n    type: OS::Heat::AutoScalingGroup\n    ' + \
                'properties:\n      min_size: 0\n      desired_capacity:' + \
                ' {get_param: current_num}\n      resource:\n        ' + \
                'type: SP1_res.yaml\n        properties:\n          nfv:' + \
                ' {get_param: nfv}\n      max_size: 3\n  SP1_scale_in:\n' + \
                '    type: OS::Heat::ScalingPolicy\n    properties:\n' + \
                '      auto_scaling_group_id: {get_resource: SP1_group}\n' + \
                '      adjustment_type: change_in_capacity\n      ' + \
                'scaling_adjustment: -1\noutputs: {}\n'
    scale_g = '{\"scaleGroupDict\": { \"SP1\": { \"vdu\":' + \
              ' [\"VDU1\"], \"num\": 1, \"maxLevel\": 3, \"initialNum\":' + \
              ' 0, \"initialLevel\": 0, \"default\": 0 }}}'
    vnfd = 'tosca_definitions_version: ' + \
           'tosca_simple_yaml_1_2\n\ndescription: Simple deployment' + \
           ' flavour for Sample VNF\n\nimports:\n' + \
           '  - etsi_nfv_sol001_common_types.yaml\n' + \
           '  - etsi_nfv_sol001_vnfd_types.yaml\n\n' + \
           'topology_template:\n  node_templates:\n' + \
           '    VNF:\n      type: nec.ossmano.VNF\n' + \
           '      properties:\n' + \
           '        flavour_description: A simple flavour\n' + \
           '      interfaces:\n        Vnflcm:\n' + \
           '          scale_start: noop\n' + \
           '          scale: scale_standard\n' + \
           '          scale_end: noop\n      artifacts:\n' + \
           '        hot:\n' + \
           '          type: tosca.artifacts.Implementation.nfv.Hot\n' + \
           '          file: ../Files/scale.yaml\n        hot-nest:\n' + \
           '          type: tosca.artifacts.Implementation.nfv.Hot\n' + \
           '          file: ../Files/SP1_res.yaml\n' + \
           '          properties:\n            nest: "True"\n\n' + \
           '    VDU1:\n      type: tosca.nodes.nfv.Vdu.Compute\n' + \
           '      properties:\n        name: VDU1\n' + \
           '        description: VDU1 compute node\n' + \
           '        vdu_profile:\n' + \
           '          min_number_of_instances: 1\n' + \
           '          max_number_of_instances: 3\n\n' + \
           '      capabilities:\n        virtual_compute:\n' + \
           '          properties:\n            virtual_memory:\n' + \
           '              virtual_mem_size: 512 MB\n' + \
           '            virtual_cpu:\n' + \
           '              num_virtual_cpu: 1\n' + \
           '            virtual_local_storage:\n' + \
           '              - size_of_storage: 1 GB\n' + \
           '      requirements:\n' + \
           '        - virtual_storage: VirtualStorage\n\n' + \
           '    VirtualStorage:\n' + \
           '      type: tosca.nodes.nfv.Vdu.VirtualBlockStorage\n' + \
           '      properties:\n        virtual_block_storage_data:\n' + \
           '          size_of_storage: 1 GB\n' + \
           '          rdma_enabled: true\n        sw_image_data:\n' + \
           '          name: VirtualStorage\n' + \
           '          version: \'0.4.0\'\n          checksum:\n' + \
           '            algorithm: sha-512\n' + \
           '            hash: 6513f21e44aa3da349f248188a44bc304a3' + \
           '653a04122d8fb4535423c8e1d14cd6a153f735bb0982e2161b5b5' + \
           '186106570c17a9e58b64dd39390617cd5a350f78\n' + \
           '          container_format: bare\n' + \
           '          disk_format: qcow2\n' + \
           '          min_disk: 2 GB\n' + \
           '          min_ram: 256 MB\n' + \
           '          size: 1 GB\n\n    CP1:\n' + \
           '      type: tosca.nodes.nfv.VduCp\n' + \
           '      properties:\n        layer_protocols: [ ipv4 ]\n' + \
           '        order: 2\n      requirements:\n' + \
           '        - virtual_binding: VDU1\n' + \
           '        - virtual_link: internalVL1\n\n' + \
           '    internalVL1:\n' + \
           '      type: tosca.nodes.nfv.VnfVirtualLink\n' + \
           '      properties:\n        connectivity_type:\n' + \
           '          layer_protocols: [ ipv4 ]\n' + \
           '        description: Internal Virtual link in the VNF\n' + \
           '        vl_profile:\n' + \
           '          max_bitrate_requirements:\n' + \
           '            root: 1048576\n' + \
           '            leaf: 1048576\n' + \
           '          min_bitrate_requirements:\n' + \
           '            root: 1048576\n            leaf: 1048576\n' + \
           '          virtual_link_protocol_data:\n' + \
           '            - associated_layer_protocol: ipv4\n' + \
           '              l3_protocol_data:\n' + \
           '                ip_version: ipv4\n' + \
           '                cidr: 33.33.0.0/24\n\n  policies:\n' + \
           '    - scaling_aspects:\n' + \
           '        type: tosca.policies.nfv.ScalingAspects\n' + \
           '        properties:\n          aspects:\n' + \
           '            SP1:\n              name: SP1_aspect\n' + \
           '              description: SP1 scaling aspect\n' + \
           '              max_scale_level: 2\n' + \
           '              step_deltas:\n' + \
           '                - delta_1\n\n' + \
           '    - VDU1_initial_delta:\n' + \
           '        type: tosca.policies.nfv.VduInitialDelta\n' + \
           '        properties:\n          initial_delta:\n' + \
           '            number_of_instances: 0\n' + \
           '        targets: [ VDU1 ]\n\n' + \
           '    - VDU1_scaling_aspect_deltas:\n' + \
           '        type: tosca.policies.nfv.VduScalingAspectDeltas\n' + \
           '        properties:\n          aspect: SP1\n' + \
           '          deltas:\n            delta_1:\n' + \
           '              number_of_instances: 1\n' + \
           '        targets: [ VDU1 ]\n\n' + \
           '    - instantiation_levels:\n' + \
           '        type: tosca.policies.nfv.InstantiationLevels\n' + \
           '        properties:\n          levels:\n' + \
           '            instantiation_level_1:\n' + \
           '              description: Smallest size\n' + \
           '              scale_info:\n                SP1:\n' + \
           '                  scale_level: 0\n' + \
           '            instantiation_level_2:\n' + \
           '              description: Largest size\n' + \
           '              scale_info:\n                SP1:\n' + \
           '                  scale_level: 3\n' + \
           '          default_level: instantiation_level_1\n\n' + \
           '    - VDU1_instantiation_levels:\n' + \
           '        type: tosca.policies.nfv.VduInstantiationLevels\n' + \
           '        properties:\n          levels:\n' + \
           '            instantiation_level_1:\n' + \
           '              number_of_instances: 0\n' + \
           '            instantiation_level_2:\n' + \
           '              number_of_instances: 3\n' + \
           '        targets: [ VDU1 ]\n'
    vnf_dict = {
        'attributes': {
            'heat_template': heat_temp,
            'scale_group': scale_g
        },
        'status': 'ERROR',
        'vnfd_id': '576acf48-b9df-491d-a57c-342de660ec78',
        'tenant_id': '13d2ca8de70d48b2a2e0dbac2c327c0b',
        'vim_id': '3f41faa7-5630-47d2-9d4a-1216953c8887',
        'instance_id': 'd1121d3c-368b-4ac2-b39d-835aa3e4ccd8',
        'placement_attr': {'vim_name': 'openstack-vim'},
        'id': 'a27fc58e-66ae-4031-bba4-efede318c60b',
        'name': 'vnf_create_1',
        'vnfd': {
            'attributes': {
                'vnfd_simple': vnfd
            }
        }
    }
    return vnf_dict


class InjectContext(wsgi.Middleware):
    """Add a 'tacker.context' to WSGI environ."""

    def __init__(self, context, *args, **kwargs):
        self.context = context
        super(InjectContext, self).__init__(*args, **kwargs)

    @webob.dec.wsgify(RequestClass=wsgi.Request)
    def __call__(self, req):
        req.environ['tacker.context'] = self.context
        return self.application


def wsgi_app_v1(fake_auth_context=None):
    inner_app_v1 = VnflcmAPIRouter()
    if fake_auth_context is not None:
        ctxt = fake_auth_context
    else:
        ctxt = context.ContextBase(uuidsentinel.user_id,
                                   uuidsentinel.project_id, is_admin=True)
    api_v1 = InjectContext(ctxt, inner_app_v1)
    return api_v1


VNFLCMOPOCC_RESPONSE = {
    '_links': {
        "self": {
            "href": CONF.vnf_lcm.endpoint_url + '/vnflcm/v1/vnf_lcm_op_occs/'
            'f26f181d-7891-4720-b022-b074ec1733ef'
        },
        "vnfInstance": {
            "href": CONF.vnf_lcm.endpoint_url + '/vnflcm/v1/vnf_instances/'
            'f26f181d-7891-4720-b022-b074ec1733ef'
        },
        "rollback": {
            "href": CONF.vnf_lcm.endpoint_url + '/vnflcm/v1/vnf_lcm_op_occs/'
            'f26f181d-7891-4720-b022-b074ec1733ef/rollback'
        },
        "grant": {
            "href": CONF.vnf_lcm.endpoint_url + '/vnflcm/v1/vnf_lcm_op_occs/'
            'f26f181d-7891-4720-b022-b074ec1733ef/grant'
        }},
    'operationState': 'COMPLETED',
    'stateEnteredTime': datetime.datetime(1900, 1, 1, 1, 1, 1,
                            tzinfo=iso8601.UTC),
    'startTime': datetime.datetime(1900, 1, 1, 1, 1, 1,
                            tzinfo=iso8601.UTC),
    'vnfInstanceId': 'f26f181d-7891-4720-b022-b074ec1733ef',
    'operation': 'MODIFY_INFO',
    'isAutomaticInvocation': False,
    'operationParams': '{"is_reverse": False, "is_auto": False}',
    'error': {
        'status': 500,
        'detail': "name 'con' is not defined",
        'title': "ERROR"
    },
    'id': 'f26f181d-7891-4720-b022-b074ec1733ef',
    'isCancelPending': False,
    'resourceChanges': {
        'affectedVnfcs': [{
            'id': 'f26f181d-7891-4720-b022-b074ec1733ef',
            'vduId': 'VDU1',
            'changeType': 'ADDED',
            'computeResource': {
                'vimConnectionId': 'f26f181d-7891-4720-b022-b074ec1733ef',
                'resourceId': 'f26f181d-7891-4720-b022-b074ec1733ef',
                'vimLevelResourceType': "OS::Nova::Server",
            },
            'affectedVnfcCpIds': [],
            'addedStorageResourceIds': [],
            'removedStorageResourceIds': []
        }],
        'affectedVirtualLinks': [{
            'id': 'f26f181d-7891-4720-b022-b074ec1733ef',
            'vnfVirtualLinkDescId': 'f26f181d-7891-4720-b022-b074ec1733ef',
            'changeType': 'ADDED',
            'networkResource': {
                'vimConnectionId': 'f26f181d-7891-4720-b022-b074ec1733ef',
                'resourceId': 'f26f181d-7891-4720-b022-b074ec1733ef',
                'vimLevelResourceType': 'COMPUTE'
            }
        }],
        'affectedVirtualStorages': [{
            'id': 'f26f181d-7891-4720-b022-b074ec1733ef',
            'virtualStorageDescId': 'f26f181d-7891-4720-b022-b074ec1733ef',
            'changeType': 'ADDED',
            'storageResource': {
                'vimConnectionId': 'f26f181d-7891-4720-b022-b074ec1733ef',
                'resourceId': 'f26f181d-7891-4720-b022-b074ec1733ef',
                'vimLevelResourceType': 'COMPUTE'
            }
        }]
    },
    'changedInfo': {
        'vimConnectionInfo': [],
        'vimConnectionInfoDeleteIds': [],
        'vnfPkgId': None,
        'vnfInstanceName': 'fake_name',
        'vnfInstanceDescription': "fake_vnf_instance_description",
        'vnfdId': 'f26f181d-7891-4720-b022-b074ec1733ef',
        'vnfProvider': 'fake_vnf_provider',
        'vnfProductName': 'fake_vnf_product_name',
        'vnfSoftwareVersion': 'fake_vnf_software_version',
        'vnfdVersion': 'fake_vnfd_version'
    }
}

VNFLCMOPOCC_INDEX_RESPONSE = [VNFLCMOPOCC_RESPONSE]


def index_response(remove_attrs=None, vnf_lcm_op_occs_updates=None):
    # Returns VNFLCMOPOCC_RESPONSE
    # parameter remove_attrs is a list of attribute names
    # to be removed before returning the response
    if not remove_attrs:
        return VNFLCMOPOCC_INDEX_RESPONSE
    vnf_lcm_op_occs = deepcopy(VNFLCMOPOCC_RESPONSE)
    for attr in remove_attrs:
        vnf_lcm_op_occs.pop(attr, None)
    if vnf_lcm_op_occs_updates:
        vnf_lcm_op_occs.update(vnf_lcm_op_occs_updates)
    return [vnf_lcm_op_occs]


def fake_vnf_lcm_op_occs():
    error = {"status": 500, "detail": "name 'con' is not defined",
            "title": "ERROR"}
    error_obj = objects.ProblemDetails(**error)

    compute_resource = {
        "vim_connection_id":
        "f26f181d-7891-4720-b022-b074ec1733ef",
        "resource_id":
        "f26f181d-7891-4720-b022-b074ec1733ef",
        "vim_level_resource_type": "OS::Nova::Server"}
    compute_resource_obj = objects.ResourceHandle(**compute_resource)
    affected_vnfcs = {
        "id": "f26f181d-7891-4720-b022-b074ec1733ef",
        "vdu_id": "VDU1",
        "change_type": "ADDED",
        "compute_resource": compute_resource_obj,
        "affected_vnfc_cp_ids": [],
        "added_storage_resource_ids": [],
        "removed_storage_sesource_ids": []
    }
    affected_vnfcs_obj = objects.AffectedVnfc(**affected_vnfcs)

    network_resource = {
        "vim_connection_id":
        "f26f181d-7891-4720-b022-b074ec1733ef",
        "resource_id":
        "f26f181d-7891-4720-b022-b074ec1733ef",
        "vim_level_resource_type": "COMPUTE"
    }
    network_resource_obj = \
        objects.ResourceHandle(**network_resource)
    affected_virtual_links = {
        "id": "f26f181d-7891-4720-b022-b074ec1733ef",
        "vnf_virtual_link_desc_id":
        "f26f181d-7891-4720-b022-b074ec1733ef",
        "change_type": "ADDED",
        "network_resource": network_resource_obj,
    }
    affected_virtual_links_obj = \
        objects.AffectedVirtualLink(**affected_virtual_links)

    storage_resource = {
        "vim_connection_id":
        "f26f181d-7891-4720-b022-b074ec1733ef",
        "resource_id":
        "f26f181d-7891-4720-b022-b074ec1733ef",
        "vim_level_resource_type": "COMPUTE"}
    storage_resource_obj = \
        objects.ResourceHandle(**storage_resource)
    affected_virtual_storages = {
        "id": "f26f181d-7891-4720-b022-b074ec1733ef",
        "virtual_storage_desc_id":
        "f26f181d-7891-4720-b022-b074ec1733ef",
        "change_type": "ADDED",
        "storage_resource": storage_resource_obj,
    }
    affected_virtual_storages_obj = \
        objects.AffectedVirtualStorage(**affected_virtual_storages)

    resource_changes = {
        "affected_vnfcs": [affected_vnfcs_obj],
        "affected_virtual_links": [affected_virtual_links_obj],
        "affected_virtual_storages": [affected_virtual_storages_obj]
    }
    resource_changes_obj = objects.ResourceChanges(**resource_changes)

    changed_info = {
        "vnf_instance_name": "fake_name",
        "vnf_instance_description":
            "fake_vnf_instance_description",
        "metadata": {},
        "vnfd_id": "f26f181d-7891-4720-b022-b074ec1733ef",
        "vnf_provider": "fake_vnf_provider",
        "vnf_product_name": "fake_vnf_product_name",
        "vnf_software_version": "fake_vnf_software_version",
        "vnfd_version": "fake_vnfd_version"
    }
    changed_info_obj = objects.VnfInfoModifications(**changed_info)

    vnf_lcm_op_occs = {
        'id': constants.UUID,
        'operation_state': 'COMPLETED',
        'state_entered_time': datetime.datetime(1900, 1, 1, 1, 1, 1,
                                tzinfo=iso8601.UTC),
        'start_time': datetime.datetime(1900, 1, 1, 1, 1, 1,
                                tzinfo=iso8601.UTC),
        'vnf_instance_id': constants.UUID,
        'operation': 'MODIFY_INFO',
        'is_automatic_invocation': False,
        'operation_params': '{"is_reverse": False, "is_auto": False}',
        'is_cancel_pending': False,
        'error': error_obj,
        'resource_changes': resource_changes_obj,
        'changed_info': changed_info_obj
    }

    return vnf_lcm_op_occs


def return_vnf_lcm_opoccs_obj():
    vnf_lcm_op_occs = fake_vnf_lcm_op_occs()
    obj = objects.VnfLcmOpOcc(**vnf_lcm_op_occs)

    return obj
