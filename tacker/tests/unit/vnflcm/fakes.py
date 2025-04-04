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
from http import client as http_client
import json
import os
import webob

from tacker.api.vnflcm.v1.router import VnflcmAPIRouter
from tacker.common import utils
from tacker import context
from tacker.db.db_sqlalchemy import models
from tacker import objects
from tacker.objects.change_ext_conn_req import ChangeExtConnRequest
from tacker.objects import fields
from tacker.objects.instantiate_vnf_req import ExtManagedVirtualLinkData
from tacker.objects.instantiate_vnf_req import ExtVirtualLinkData
from tacker.objects.instantiate_vnf_req import InstantiateVnfRequest
from tacker.objects import scale_vnf_request
from tacker.objects.vim_connection import VimConnectionInfo
from tacker.policies import vnf_lcm as vnf_lcm_policies
from tacker.tests import constants
from tacker.tests import utils as test_utils
from tacker.tests import uuidsentinel
from tacker import wsgi

import tacker.db.vnfm.vnfm_db

import tacker.conf
CONF = tacker.conf.CONF


def return_vnf_interfaces():
    vnf_interface = 'vnflcm_noop'
    return vnf_interface


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
                                        tzinfo=datetime.timezone.utc),
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


def return_vnf_package_vnfd(**updates):
    model_obj = models.VnfPackageVnfd()
    model_obj.update(fake_vnf_package_vnfd_model_dict(**updates))
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
                                        tzinfo=datetime.timezone.utc),
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


def return_vnf_instance_delete(
        instantiated_state=fields.VnfInstanceState.NOT_INSTANTIATED,
        **updates):
    data = _model_non_instantiated_vnf_instance(**updates)
    data['instantiation_state'] = instantiated_state
    vnf_instance_obj = objects.VnfInstance(**data)
    return vnf_instance_obj


def return_vnf_instance(
        instantiated_state=fields.VnfInstanceState.NOT_INSTANTIATED,
        scale_status=None,
        **updates):

    if instantiated_state == fields.VnfInstanceState.NOT_INSTANTIATED:
        data = _model_non_instantiated_vnf_instance(**updates)
        data['instantiation_state'] = instantiated_state
        get_instantiated_vnf_info = {
            'flavour_id': uuidsentinel.flavour_id,
            'vnf_state': 'STARTED',
            'instance_id': ''
        }
        instantiated_vnf_info = get_instantiated_vnf_info
        info_data = objects.InstantiatedVnfInfo(**instantiated_vnf_info)
        vnf_instance_obj = objects.VnfInstance(**data)
        vnf_instance_obj.instantiated_vnf_info = info_data

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

        if scale_status == "scale_status":
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
        "self": {"href":
            '{endpoint}/vnflcm/v1/vnf_instances/{id}'.format(
                endpoint=CONF.vnf_lcm.endpoint_url.rstrip("/"),
                id=vnf_instance_id)},
        "terminate": {"href":
            '{endpoint}/vnflcm/v1/vnf_instances/{id}/terminate'.format(
                endpoint=CONF.vnf_lcm.endpoint_url.rstrip("/"),
                id=vnf_instance_id)},
        "scale": {"href":
            '{endpoint}/vnflcm/v1/vnf_instances/{id}/scale'.format(
                endpoint=CONF.vnf_lcm.endpoint_url.rstrip("/"),
                id=vnf_instance_id)},
        "heal": {"href":
            '{endpoint}/vnflcm/v1/vnf_instances/{id}/heal'.format(
                endpoint=CONF.vnf_lcm.endpoint_url.rstrip("/"),
                id=vnf_instance_id)},
        "changeExtConn": {"href":
            '{endpoint}/vnflcm/v1/vnf_instances/{id}/change_ext_conn'
             .format(endpoint=CONF.vnf_lcm.endpoint_url.rstrip("/"),
                 id=vnf_instance_id)}}

    return links


def _fake_vnf_instance_not_instantiated_response(
        **updates):
    vnf_instance = {
        'vnfInstanceDescription': 'Vnf instance description',
        'vnfInstanceName': 'Vnf instance name',
        'vnfProductName': 'Sample VNF',
        '_links': {
            'self': {
                "href":
                '{endpoint}/vnflcm/v1/vnf_instances/{id}'.format(
                    endpoint=CONF.vnf_lcm.endpoint_url.rstrip("/"),
                    id=uuidsentinel.vnf_instance_id)},
            'instantiate': {
                "href":
                '{endpoint}/vnflcm/v1/vnf_instances/{id}/{op}'.format(
                    endpoint=CONF.vnf_lcm.endpoint_url.rstrip("/"),
                    id=uuidsentinel.vnf_instance_id,
                    op='instantiate')}},
        'instantiationState': 'NOT_INSTANTIATED',
        'vnfProvider': 'Vnf provider',
        'vnfdId': uuidsentinel.vnfd_id,
        'vnfdVersion': '1.0',
        'vnfSoftwareVersion': '1.0',
        'vnfPkgId': uuidsentinel.vnf_pkg_id,
        'id': uuidsentinel.vnf_instance_id,
        'metadata': {'key': 'value'}
    }

    if updates:
        vnf_instance.update(**updates)

    return vnf_instance


def fake_vnf_instance_response(
        instantiated_state=fields.VnfInstanceState.NOT_INSTANTIATED,
        api_version=None, vimConnectionInfo=[], **updates):
    if instantiated_state == fields.VnfInstanceState.NOT_INSTANTIATED:
        data = _fake_vnf_instance_not_instantiated_response(**updates)
    else:
        data = _fake_vnf_instance_not_instantiated_response(**updates)
        data['_links'] = _instantiated_vnf_links(uuidsentinel.vnf_instance_id)
        data['instantiationState'] = instantiated_state
        data['vimConnectionInfo'] = vimConnectionInfo

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
                                        tzinfo=datetime.timezone.utc),
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
                                        tzinfo=datetime.timezone.utc)
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
                                            '192.168.11.1',
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
                             'min_disk': '1 ''GiB',
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


def get_vnfd_dict_for_convert_desired_capacity():
    vnfd_dict = {
        'imports': [
            'etsi_nfv_sol001_common_types.yaml',
            'etsi_nfv_sol001_vnfd_types.yaml',
            'helloworld3_types.yaml'
        ],
        'description': 'Simple deployment flavour for Sample VNF',
        'topology_template': {
            'inputs': {
                'descriptor_id': {
                    'type': 'string'
                },
                'flavour_description': {
                    'type': 'string'
                },
                'software_version': {
                    'type': 'string'
                },
                'flavour_id': {
                    'type': 'string'
                },
                'descriptor_version': {
                    'type': 'string'
                },
                'provider': {
                    'type': 'string'
                },
                'vnfm_info': {
                    'entry_schema': {
                        'type': 'string'
                    },
                    'type': 'list'
                },
                'product_name': {
                    'type': 'string'
                }
            },
            'node_templates': {
                'VDU1': {
                    'requirements': [
                        {
                            'virtual_storage': 'VirtualStorage'
                        }
                    ],
                    'type': 'tosca.nodes.nfv.Vdu.Compute',
                    'properties': {
                        'vdu_profile': {
                            'max_number_of_instances': 3,
                            'min_number_of_instances': 1
                        },
                        'description': 'VDU1 compute node',
                        'name': 'VDU1'
                    },
                    'capabilities': {
                        'virtual_compute': {
                            'properties': {
                                'requested_additional_capabilities': {
                                    'properties': {
                                        'requested_additional_capability_name':
                                            'm1.tiny',
                                        'target_performance_parameters': {
                                            'entry_schema': 'test'
                                        },
                                        'support_mandatory': 'true'
                                    }
                                },
                                'virtual_cpu': {
                                    'num_virtual_cpu': 1
                                },
                                'virtual_memory': {
                                    'virtual_mem_size': '512 MB'
                                },
                                'virtual_local_storage': [
                                    {
                                        'size_of_storage': '3 GB'
                                    }
                                ]
                            }
                        }
                    }
                },
                'VirtualStorage': {
                    'type': 'tosca.nodes.nfv.Vdu.VirtualBlockStorage',
                    'properties': {
                        'sw_image_data': {
                            'name': 'cirros-0.5.2-x86_64-disk',
                            'checksum': {
                                'hash': 'fake hash',
                                'algorithm': 'sha-256'
                            },
                            'min_ram': '256 MB',
                            'disk_format': 'qcow2',
                            'version': '0.5.2',
                            'container_format': 'bare',
                            'min_disk': '0 GB',
                            'size': '12 GB'
                        },
                        'virtual_block_storage_data': {
                            'size_of_storage': '1 GB',
                            'rdma_enabled': 'true'
                        }
                    }
                },
                'VDU1_CP3': {
                    'requirements': [
                        {
                            'virtual_binding': 'VDU1'
                        },
                        {
                            'virtual_link': 'internalVL1'
                        }
                    ],
                    'type': 'tosca.nodes.nfv.VduCp',
                    'properties': {
                        'layer_protocols': [
                            'ipv4'
                        ],
                        'order': 2
                    }
                },
                'VDU2_CP5': {
                    'requirements': [
                        {
                            'virtual_binding': 'VDU2'
                        },
                        {
                            'virtual_link': 'internalVL3'
                        }
                    ],
                    'type': 'tosca.nodes.nfv.VduCp',
                    'properties': {
                        'layer_protocols': [
                            'ipv4'
                        ],
                        'order': 4
                    }
                },
                'VDU2_CP4': {
                    'requirements': [
                        {
                            'virtual_binding': 'VDU2'
                        },
                        {
                            'virtual_link': 'internalVL2'
                        }
                    ],
                    'type': 'tosca.nodes.nfv.VduCp',
                    'properties': {
                        'layer_protocols': [
                            'ipv4'
                        ],
                        'order': 3
                    }
                },
                'VDU2_CP1': {
                    'requirements': [
                        {
                            'virtual_binding': 'VDU2'
                        }
                    ],
                    'type': 'tosca.nodes.nfv.VduCp',
                    'properties': {
                        'layer_protocols': [
                            'ipv4'
                        ],
                        'order': 0
                    }
                },
                'VDU2_CP3': {
                    'requirements': [
                        {
                            'virtual_binding': 'VDU2'
                        },
                        {
                            'virtual_link': 'internalVL1'
                        }
                    ],
                    'type': 'tosca.nodes.nfv.VduCp',
                    'properties': {
                        'layer_protocols': [
                            'ipv4'
                        ],
                        'order': 2
                    }
                },
                'VDU2_CP2': {
                    'requirements': [
                        {
                            'virtual_binding': 'VDU2'
                        }
                    ],
                    'type': 'tosca.nodes.nfv.VduCp',
                    'properties': {
                        'layer_protocols': [
                            'ipv4'
                        ],
                        'order': 1
                    }
                },
                'internalVL1': {
                    'type': 'tosca.nodes.nfv.VnfVirtualLink',
                    'properties': {
                        'connectivity_type': {
                            'layer_protocols': [
                                'ipv4'
                            ]
                        },
                        'vl_profile': {
                            'virtual_link_protocol_data': [
                                {
                                    'l3_protocol_data': {
                                        'ip_version': 'ipv4',
                                        'cidr': '33.33.0.0/24'
                                    },
                                    'associated_layer_protocol': 'ipv4'
                                }
                            ],
                            'min_bitrate_requirements': {
                                'leaf': 1048576,
                                'root': 1048576
                            },
                            'max_bitrate_requirements': {
                                'leaf': 1048576,
                                'root': 1048576
                            }
                        },
                        'description':
                            'External Managed Virtual link in the VNF'
                    }
                },
                'internalVL2': {
                    'type': 'tosca.nodes.nfv.VnfVirtualLink',
                    'properties': {
                        'connectivity_type': {
                            'layer_protocols': [
                                'ipv4'
                            ]
                        },
                        'vl_profile': {
                            'virtual_link_protocol_data': [
                                {
                                    'l3_protocol_data': {
                                        'ip_version': 'ipv4',
                                        'cidr': '33.34.0.0/24'
                                    },
                                    'associated_layer_protocol': 'ipv4'
                                }
                            ],
                            'min_bitrate_requirements': {
                                'leaf': 1048576,
                                'root': 1048576
                            },
                            'max_bitrate_requirements': {
                                'leaf': 1048576,
                                'root': 1048576
                            }
                        },
                        'description':
                            'External Managed Virtual link in the VNF'
                    }
                },
                'VDU1_CP1': {
                    'requirements': [
                        {
                            'virtual_binding': 'VDU1'
                        }
                    ],
                    'type': 'tosca.nodes.nfv.VduCp',
                    'properties': {
                        'layer_protocols': [
                            'ipv4'
                        ],
                        'order': 0
                    }
                },
                'VDU1_CP2': {
                    'requirements': [
                        {
                            'virtual_binding': 'VDU1'
                        }
                    ],
                    'type': 'tosca.nodes.nfv.VduCp',
                    'properties': {
                        'layer_protocols': [
                            'ipv4'
                        ],
                        'order': 1
                    }
                },
                'VNF': {
                    'interfaces': {
                        'Vnflcm': {
                            'instantiate': [],
                            'modify_information_start': [],
                            'modify_information_end': [],
                            'terminate_start': [],
                            'instantiate_start': [],
                            'terminate': [],
                            'instantiate_end': [],
                            'terminate_end': [],
                            'modify_information': []
                        }
                    },
                    'type': 'company.provider.VNF',
                    'properties': {
                        'flavour_description': 'A simple flavour'
                    }
                },
                'VDU2': {
                    'type': 'tosca.nodes.nfv.Vdu.Compute',
                    'properties': {
                        'vdu_profile': {
                            'max_number_of_instances': 1,
                            'min_number_of_instances': 1
                        },
                        'description': 'VDU2 compute node',
                        'sw_image_data': {
                            'name': 'cirros-0.5.2-x86_64-disk',
                            'checksum': {
                                'hash': 'fake hash',
                                'algorithm': 'sha-256'
                            },
                            'min_ram': '256 MB',
                            'disk_format': 'qcow2',
                            'version': '0.5.2',
                            'container_format': 'bare',
                            'min_disk': '0 GB',
                            'size': '12 GB'
                        },
                        'name': 'VDU2'
                    },
                    'capabilities': {
                        'virtual_compute': {
                            'properties': {
                                'requested_additional_capabilities': {
                                    'properties': {
                                        'requested_additional_capability_name':
                                            'm1.tiny',
                                        'target_performance_parameters': {
                                            'entry_schema': 'test'
                                        },
                                        'support_mandatory': 'true'
                                    }
                                },
                                'virtual_cpu': {
                                    'num_virtual_cpu': 1
                                },
                                'virtual_memory': {
                                    'virtual_mem_size': '512 MB'
                                },
                                'virtual_local_storage': [
                                    {
                                        'size_of_storage': '3 GB'
                                    }
                                ]
                            }
                        }
                    }
                },
                'VDU1_CP4': {
                    'requirements': [
                        {
                            'virtual_binding': 'VDU1'
                        },
                        {
                            'virtual_link': 'internalVL2'
                        }
                    ],
                    'type': 'tosca.nodes.nfv.VduCp',
                    'properties': {
                        'layer_protocols': [
                            'ipv4'
                        ],
                        'order': 3
                    }
                },
                'VDU1_CP5': {
                    'requirements': [
                        {
                            'virtual_binding': 'VDU1'
                        },
                        {
                            'virtual_link': 'internalVL3'
                        }
                    ],
                    'type': 'tosca.nodes.nfv.VduCp',
                    'properties': {
                        'layer_protocols': [
                            'ipv4'
                        ],
                        'order': 4
                    }
                },
                'internalVL3': {
                    'type': 'tosca.nodes.nfv.VnfVirtualLink',
                    'properties': {
                        'connectivity_type': {
                            'layer_protocols': [
                                'ipv4'
                            ]
                        },
                        'vl_profile': {
                            'virtual_link_protocol_data': [
                                {
                                    'l3_protocol_data': {
                                        'ip_version': 'ipv4',
                                        'cidr': '33.35.0.0/24'
                                    },
                                    'associated_layer_protocol': 'ipv4'
                                }
                            ],
                            'min_bitrate_requirements': {
                                'leaf': 1048576,
                                'root': 1048576
                            },
                            'max_bitrate_requirements': {
                                'leaf': 1048576,
                                'root': 1048576
                            }
                        },
                        'description': 'Internal Virtual link in the VNF'
                    }
                }
            },
            'substitution_mappings': {
                'node_type': 'company.provider.VNF',
                'properties': {
                    'flavour_id': 'simple'
                }
            },
            'policies': [
                {
                    'scaling_aspects': {
                        'type': 'tosca.policies.nfv.ScalingAspects',
                        'properties': {
                            'aspects': {
                                'VDU1_scale': {
                                    'max_scale_level': 2,
                                    'description': 'VDU1 scaling aspect',
                                    'name': 'VDU1_scale',
                                    'step_deltas': [
                                        'delta_1'
                                    ]
                                }
                            }
                        }
                    }
                },
                {
                    'VDU1_initial_delta': {
                        'type': 'tosca.policies.nfv.VduInitialDelta',
                        'properties': {
                            'initial_delta': {
                                'number_of_instances': 1
                            }
                        },
                        'targets': [
                            'VDU1'
                        ]
                    }
                },
                {
                    'VDU2_initial_delta': {
                        'type': 'tosca.policies.nfv.VduInitialDelta',
                        'properties': {
                            'initial_delta': {
                                'number_of_instances': 1
                            }
                        },
                        'targets': [
                            'VDU2'
                        ]
                    }
                },
                {
                    'VDU1_scaling_aspect_deltas': {
                        'type': 'tosca.policies.nfv.VduScalingAspectDeltas',
                        'properties': {
                            'deltas': {
                                'delta_1': {
                                    'number_of_instances': 1
                                }
                            },
                            'aspect': 'VDU1_scale'
                        },
                        'targets': [
                            'VDU1'
                        ]
                    }
                },
                {
                    'instantiation_levels': {
                        'type': 'tosca.policies.nfv.InstantiationLevels',
                        'properties': {
                            'default_level': 'instantiation_level_1',
                            'levels': {
                                'instantiation_level_1': {
                                    'scale_info': {
                                        'VDU1_scale': {
                                            'scale_level': 0
                                        }
                                    },
                                    'description': 'Smallest size'
                                },
                                'instantiation_level_2': {
                                    'scale_info': {
                                        'VDU1_scale': {
                                            'scale_level': 2
                                        }
                                    },
                                    'description': 'Largest size'
                                }
                            }
                        }
                    }
                },
                {
                    'VDU1_instantiation_levels': {
                        'type': 'tosca.policies.nfv.VduInstantiationLevels',
                        'properties': {
                            'levels': {
                                'instantiation_level_1': {
                                    'number_of_instances': 1
                                },
                                'instantiation_level_2': {
                                    'number_of_instances': 3
                                }
                            }
                        },
                        'targets': [
                            'VDU1'
                        ]
                    }
                },
                {
                    'VDU2_instantiation_levels': {
                        'type': 'tosca.policies.nfv.VduInstantiationLevels',
                        'properties': {
                            'levels': {
                                'instantiation_level_1': {
                                    'number_of_instances': 1
                                },
                                'instantiation_level_2': {
                                    'number_of_instances': 1
                                }
                            }
                        },
                        'targets': [
                            'VDU2'
                        ]
                    }
                },
                {
                    'internalVL1_instantiation_levels': {
                        'type':
                            'tosca.policies.nfv.'
                            'VirtualLinkInstantiationLevels',
                        'properties': {
                            'levels': {
                                'instantiation_level_1': {
                                    'bitrate_requirements': {
                                        'leaf': 1048576,
                                        'root': 1048576
                                    }
                                },
                                'instantiation_level_2': {
                                    'bitrate_requirements': {
                                        'leaf': 1048576,
                                        'root': 1048576
                                    }
                                }
                            }
                        },
                        'targets': [
                            'internalVL1'
                        ]
                    }
                },
                {
                    'internalVL2_instantiation_levels': {
                        'type':
                            'tosca.policies.nfv.'
                            'VirtualLinkInstantiationLevels',
                        'properties': {
                            'levels': {
                                'instantiation_level_1': {
                                    'bitrate_requirements': {
                                        'leaf': 1048576,
                                        'root': 1048576
                                    }
                                },
                                'instantiation_level_2': {
                                    'bitrate_requirements': {
                                        'leaf': 1048576,
                                        'root': 1048576
                                    }
                                }
                            }
                        },
                        'targets': [
                            'internalVL2'
                        ]
                    }
                },
                {
                    'internalVL3_instantiation_levels': {
                        'type':
                            'tosca.policies.nfv.'
                            'VirtualLinkInstantiationLevels',
                        'properties': {
                            'levels': {
                                'instantiation_level_1': {
                                    'bitrate_requirements': {
                                        'leaf': 1048576,
                                        'root': 1048576
                                    }
                                },
                                'instantiation_level_2': {
                                    'bitrate_requirements': {
                                        'leaf': 1048576,
                                        'root': 1048576
                                    }
                                }
                            }
                        },
                        'targets': [
                            'internalVL3'
                        ]
                    }
                },
                {
                    'policy_antiaffinity_vdu1': {
                        'type': 'tosca.policies.nfv.AntiAffinityRule',
                        'properties': {
                            'scope': 'zone'
                        },
                        'targets': [
                            'VDU1'
                        ]
                    }
                },
                {
                    'policy_antiaffinity_vdu2': {
                        'type': 'tosca.policies.nfv.AntiAffinityRule',
                        'properties': {
                            'scope': 'zone'
                        },
                        'targets': [
                            'VDU2'
                        ]
                    }
                }
            ]
        },
        'tosca_definitions_version': 'tosca_simple_yaml_1_2'
    }

    return vnfd_dict


def get_dummy_vim_connection_info():
    return {'access_info': {
        'auth_url': 'fake/url',
        'cert_verify': 'False', 'password': 'admin',
        'project_domain_name': 'Default',
        'project_id': None, 'project_name': 'admin',
        'user_domain_name': 'Default', 'username': 'admin'},
        'created_at': '', 'deleted': False, 'deleted_at': '',
        'id': 'fake_id', 'updated_at': '',
        'vim_id': 'fake_vim_id', 'vim_type': 'openstack', 'extra': {}}


def get_dummy_openstack_vim_obj():
    return {'vim_id': uuidsentinel.vim_id,
            'vim_name': 'fake_vim',
            'vim_type': 'openstack',
            'vim_auth': {
                'auth_url': 'http://localhost/identity',
                'password': 'test_pw',
                'username': 'test_user',
                'project_name': 'test_project'},
            'tenant': uuidsentinel.tenant_id}


def get_dummy_k8s_vim_obj():
    return {'vim_id': uuidsentinel.vim_id,
            'vim_name': 'fake_vim',
            'vim_type': 'kubernetes',
            'vim_auth': {
                'auth_url': 'http://localhost/8443',
                'password': 'test_pw',
                'username': 'test_user',
                'project_name': 'test_project'},
            'tenant': uuidsentinel.tenant_id}


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
            "heat_template": test_utils.test_etc_sample(
                "hot_lcm_template.yaml")}}

    if updates:
        vnf_data.update(**updates)

    return vnf_data


def scale_request(type, aspect_id, number_of_steps, is_reverse):
    scale_request_data = {
        'type': type,
        'aspect_id': aspect_id,
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
        created_at=datetime.datetime(
            1900, 1, 1, 1, 1, 1, tzinfo=datetime.timezone.utc),
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


def vnflcm_scale_in_cnf():
    dt = datetime.datetime(2000, 1, 1, 1, 1, 1, tzinfo=datetime.timezone.utc)
    return objects.VnfLcmOpOcc(
        state_entered_time=dt,
        start_time=dt,
        vnf_instance_id=uuidsentinel.vnf_instance_id,
        operation='SCALE',
        operation_state='STARTING',
        is_automatic_invocation=False,
        operation_params='{"type": "SCALE_IN", "aspect_id": "vdu1_aspect"}',
        error_point=1,
        id=constants.UUID,
        created_at=dt)


def vnflcm_scale_out_cnf():
    dt = datetime.datetime(2000, 1, 1, 1, 1, 1, tzinfo=datetime.timezone.utc)
    return objects.VnfLcmOpOcc(
        state_entered_time=dt,
        start_time=dt,
        vnf_instance_id=uuidsentinel.vnf_instance_id,
        operation='SCALE',
        operation_state='STARTING',
        is_automatic_invocation=False,
        operation_params='{"type": "SCALE_OUT", "aspect_id": "vdu1_aspect"}',
        error_point=1,
        id=constants.UUID,
        created_at=dt)


def vnflcm_rollback(error_point=7):
    dt = datetime.datetime(2000, 1, 1, 1, 1, 1, tzinfo=datetime.timezone.utc)
    return objects.VnfLcmOpOcc(
        state_entered_time=dt,
        start_time=dt,
        vnf_instance_id=uuidsentinel.vnf_instance_id,
        operation='SCALE',
        operation_state='FAILED_TEMP',
        is_automatic_invocation=False,
        operation_params='{"type": "SCALE_OUT", "aspect_id": "SP1"}',
        error_point=error_point,
        id=constants.UUID,
        created_at=dt)


def vnflcm_rollback_insta(error_point=7):
    dt = datetime.datetime(2000, 1, 1, 1, 1, 1, tzinfo=datetime.timezone.utc)
    return objects.VnfLcmOpOcc(
        state_entered_time=dt,
        start_time=dt,
        vnf_instance_id=uuidsentinel.vnf_instance_id,
        operation='INSTANTIATE',
        operation_state='FAILED_TEMP',
        is_automatic_invocation=False,
        operation_params='{}',
        error_point=error_point,
        id=constants.UUID,
        created_at=dt)


def vnflcm_cancel_insta(error_point=7):
    default_datetime = datetime.datetime(
        2000, 1, 1, 1, 1, 1, tzinfo=datetime.timezone.utc)
    ext_link_port_info = objects.ExtLinkPortInfo(
        resource_handle=objects.ResourceHandle(
            resource_id="109f5049-b51e-409a-9a99-d740ba5f3acb",
            vim_level_resource_type="LINKPORT"),
        cp_instance_id="f5c68d94-5736-4e38-ade5-c9462514f8b9",
        id="1d868d02-ecd4-4402-8e6b-54e77ebdcc28")
    changed_ext_connectivity_values = objects.ExtVirtualLinkInfo(
        id=constants.UUID,
        resource_handle=objects.ResourceHandle(
            vim_connection_id=constants.UUID,
            resource_id=constants.UUID,
            vim_level_resource_type="OS::Neutron::Net"),
        ext_link_ports=[ext_link_port_info]
    )
    return objects.VnfLcmOpOcc(
        state_entered_time=default_datetime,
        start_time=default_datetime,
        vnf_instance_id=uuidsentinel.vnf_instance_id,
        operation='INSTANTIATE',
        operation_state='PROCESSING',
        is_automatic_invocation=False,
        operation_params='{}',
        error_point=error_point,
        id=constants.UUID,
        grant_id=constants.UUID,
        created_at=default_datetime,
        changed_ext_connectivity=[changed_ext_connectivity_values])


def vnflcm_fail_insta(error_point=7):
    default_datetime = datetime.datetime(
        2000, 1, 1, 1, 1, 1, tzinfo=datetime.timezone.utc)
    ext_link_port_info = objects.ExtLinkPortInfo(
        resource_handle=objects.ResourceHandle(
            resource_id="109f5049-b51e-409a-9a99-d740ba5f3acb",
            vim_level_resource_type="LINKPORT"),
        cp_instance_id="f5c68d94-5736-4e38-ade5-c9462514f8b9",
        id="1d868d02-ecd4-4402-8e6b-54e77ebdcc28")
    changed_ext_connectivity_values = objects.ExtVirtualLinkInfo(
        id=constants.UUID,
        resource_handle=objects.ResourceHandle(
            vim_connection_id=constants.UUID,
            resource_id=constants.UUID,
            vim_level_resource_type="OS::Neutron::Net"),
        ext_link_ports=[ext_link_port_info]
    )
    return objects.VnfLcmOpOcc(
        state_entered_time=default_datetime,
        start_time=default_datetime,
        vnf_instance_id=uuidsentinel.vnf_instance_id,
        operation='INSTANTIATE',
        operation_state='FAILED_TEMP',
        is_automatic_invocation=False,
        operation_params='{}',
        error_point=error_point,
        id=constants.UUID,
        grant_id=constants.UUID,
        created_at=default_datetime,
        changed_ext_connectivity=[changed_ext_connectivity_values])


def vnflcm_fail_check_added_params(error_point=7):
    ext_link_port_info = objects.ExtLinkPortInfo(
        resource_handle=objects.ResourceHandle(
            resource_id="109f5049-b51e-409a-9a99-d740ba5f3acb",
            vim_level_resource_type="LINKPORT"),
        cp_instance_id="f5c68d94-5736-4e38-ade5-c9462514f8b9",
        id="1d868d02-ecd4-4402-8e6b-54e77ebdcc28")
    changed_ext_connectivity_values = objects.ExtVirtualLinkInfo(
        id=constants.UUID,
        resource_handle=objects.ResourceHandle(
            vim_connection_id=constants.UUID,
            resource_id=constants.UUID,
            vim_level_resource_type="OS::Neutron::Net"),
        ext_link_ports=[ext_link_port_info]
    )
    vim_connection_info = {"id": 'f8c35bd0-4d67-4436-9f11-14b8a84c92aa',
             "vim_id": 'f8c35bd0-4d67-4436-9f11-14b8a84c92aa',
             "vim_type": 'openstack',
             "access_info": {"key1": 'value1', "key2": 'value2'}}
    changed_info_values = objects.VnfInfoModifications(
        vnf_instance_name="fake_name",
        vnf_instance_description="fake_vnf_instance_description",
        metadata={'key': 'value'},
        vim_connection_info=[VimConnectionInfo(**vim_connection_info)],
        vim_connection_info_delete_ids=[
            'f8c35bd0-4d67-4436-9f11-14b8a84c92bb'],
        vnf_pkg_id='f26f181d-7891-4720-b022-b074ec1733ef',
        vnfd_id="f26f181d-7891-4720-b022-b074ec1733ef",
        vnf_provider="fake_vnf_provider",
        vnf_product_name="fake_vnf_product_name",
        vnf_software_version="fake_vnf_software_version",
        vnfd_version="fake_vnfd_version")
    return objects.VnfLcmOpOcc(
        state_entered_time=datetime.datetime(2000, 1, 1, 1, 1, 1,
                                             tzinfo=datetime.timezone.utc),
        start_time=datetime.datetime(2000, 1, 1, 1, 1, 1,
                                     tzinfo=datetime.timezone.utc),
        vnf_instance_id=constants.UUID,
        operation='INSTANTIATE',
        operation_state='FAILED_TEMP',
        is_automatic_invocation=False,
        operation_params='{}',
        error_point=error_point,
        id=constants.UUID,
        grant_id=constants.UUID,
        created_at=datetime.datetime(2000, 1, 1, 1, 1, 1,
                                     tzinfo=datetime.timezone.utc),
        changed_ext_connectivity=[changed_ext_connectivity_values],
        changed_info=changed_info_values)


def vnflcm_rollback_active():
    dt = datetime.datetime(2000, 1, 1, 1, 1, 1, tzinfo=datetime.timezone.utc)
    return objects.VnfLcmOpOcc(
        state_entered_time=dt,
        start_time=dt,
        vnf_instance_id=uuidsentinel.vnf_instance_id,
        operation='SCALE',
        operation_state='ACTIVE',
        is_automatic_invocation=False,
        operation_params='{"type": "SCALE_OUT", "aspect_id": "SP1"}',
        error_point=7,
        id=constants.UUID,
        created_at=dt)


def vnflcm_rollback_ope():
    dt = datetime.datetime(2000, 1, 1, 1, 1, 1, tzinfo=datetime.timezone.utc)
    return objects.VnfLcmOpOcc(
        state_entered_time=dt,
        start_time=dt,
        vnf_instance_id=uuidsentinel.vnf_instance_id,
        operation='HEAL',
        operation_state='FAILED_TEMP',
        is_automatic_invocation=False,
        operation_params='{}',
        error_point=7,
        id=constants.UUID,
        created_at=dt)


def vnflcm_rollback_scale_in():
    dt = datetime.datetime(2000, 1, 1, 1, 1, 1, tzinfo=datetime.timezone.utc)
    return objects.VnfLcmOpOcc(
        state_entered_time=dt,
        start_time=dt,
        vnf_instance_id=uuidsentinel.vnf_instance_id,
        operation='SCALE',
        operation_state='FAILED_TEMP',
        is_automatic_invocation=False,
        operation_params='{"type": "SCALE_IN", "aspect_id": "SP1"}',
        error_point=7,
        id=constants.UUID,
        created_at=dt)


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
                '{get_resource: SP1}\n      adjustment_type: ' + \
                'change_in_capacity\n      scaling_adjustment: 1\n  ' + \
                'SP1:\n    type: OS::Heat::AutoScalingGroup\n    ' + \
                'properties:\n      min_size: 0\n      desired_capacity:' + \
                ' {get_param: current_num}\n      resource:\n        ' + \
                'type: SP1_res.yaml\n        properties:\n          nfv:' + \
                ' {get_param: nfv}\n      max_size: 3\n  SP1_scale_in:\n' + \
                '    type: OS::Heat::ScalingPolicy\n    properties:\n' + \
                '      auto_scaling_group_id: {get_resource: SP1}\n' + \
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
           'topology_template:\n  groups:\n  node_templates:\n' + \
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
           '          version: \'0.5.2\'\n          checksum:\n' + \
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


def vnf_dict_cnf():
    vnf_dict = {
        'attributes': {},
        'status': 'ACTIVE',
        'vnfd_id': 'e889e4fe-52fe-437d-b1e1-a690dc95e3f8',
        'tenant_id': '13d2ca8de70d48b2a2e0dbac2c327c0b',
        'vim_id': '3f41faa7-5630-47d2-9d4a-1216953c8887',
        'instance_id': 'd1121d3c-368b-4ac2-b39d-835aa3e4ccd8',
        'placement_attr': {'vim_name': 'kubernetes-vim'},
        'id': '436aaa6e-2db6-4d6e-a3fc-e728b2f0ac56',
        'name': 'cnf_create_1',
        'vnfd': {
            'attributes': {
                'vnfd_simple': 'dummy'
            }
        }
    }
    return vnf_dict


def vnfd_dict_cnf(vdu_num=1):
    tacker_dir = os.getcwd()
    def_dir = tacker_dir + "/samples/vnf_packages/Definitions/"
    vnfd_dict = {
        "tosca_definitions_version": "tosca_simple_yaml_1_2",
        "description": "Sample VNF flavour for Sample VNF",
        "imports": [
            def_dir + "etsi_nfv_sol001_common_types.yaml",
            def_dir + "etsi_nfv_sol001_vnfd_types.yaml",
            def_dir + "helloworld3_types.yaml"],
        "topology_template": {
            "node_templates": {
                "VNF": {
                    "type": "company.provider.VNF",
                    "properties": {
                        "flavour_description": "A simple flavour"}}
                # add VDU defininition later
            },
            "policies": [
                {
                    "scaling_aspects": {
                        "type": "tosca.policies.nfv.ScalingAspects",
                        "properties": {
                            "aspects": {
                                # add aspects later
                            }}}},
                # add following policies definitions later
                # - tosca.policies.nfv.VduInitialDelta
                # - tosca.policies.nfv.VduScalingAspectDeltas
                # - tosca.policies.nfv.VduInstantiationLevels
                {
                    "instantiation_levels": {
                        "type": "tosca.policies.nfv.InstantiationLevels",
                        "properties": {
                            "levels": {
                                "instantiation_level_1": {
                                    "description": "Smallest size",
                                    "scale_info": {
                                        # add scale_info later
                                    }},
                                "instantiation_level_2": {
                                    "description": "Largest size",
                                    "scale_info": {
                                        # add scale_info later
                                    }}
                            },
                            "default_level": "instantiation_level_1"}}}
            ]
        }
    }
    topology = vnfd_dict["topology_template"]
    node_templates = topology["node_templates"]
    policies = topology["policies"]
    scaling_aspects = policies[0]["scaling_aspects"]
    levels = policies[1]["instantiation_levels"]["properties"]["levels"]
    for i in range(1, vdu_num + 1):
        node_templates[f"VDU{i}"] = {
            "type": "tosca.nodes.nfv.Vdu.Compute",
            "properties": {
                "name": f"vdu{i}",
                "description": f"vdu{i} compute node",
                "vdu_profile": {
                    "min_number_of_instances": 1,
                    "max_number_of_instances": 3}}}
        scaling_aspects["properties"]["aspects"][f"vdu{i}_aspect"] = {
            "name": f"vdu{i}_aspect",
            "description": f"vdu{i} scaling aspect",
            "max_scale_level": 2,
            "step_deltas": ["delta_1"]}
        policies.append({f"vdu{i}_initial_delta": {
            "type": "tosca.policies.nfv.VduInitialDelta",
            "properties": {
                "initial_delta": {
                    "number_of_instances": 1}},
            "targets": [f"VDU{i}"]}})
        policies.append({f"vdu{i}_scaling_aspect_deltas": {
            "type": "tosca.policies.nfv.VduScalingAspectDeltas",
            "properties": {
                "aspect": f"vdu{i}_aspect",
                "deltas": {
                    "delta_1": {
                        "number_of_instances": 1}}},
            "targets": [f"VDU{i}"]}})
        policies.append({f"vdu{i}_instantiation_levels": {
            "type": "tosca.policies.nfv.VduInstantiationLevels",
            "properties": {
                "levels": {
                    "instantiation_level_1": {
                        "number_of_instances": 1},
                    "instantiation_level_2": {
                        "number_of_instances": 3}}},
            "targets": [f"VDU{i}"]}})
        levels["instantiation_level_1"]["scale_info"] = {
            f"vdu{i}_aspect": {"scale_level": 0}}
        levels["instantiation_level_2"]["scale_info"] = {
            f"vdu{i}_aspect": {"scale_level": 2}}
    return vnfd_dict


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
            "href": CONF.vnf_lcm.endpoint_url.rstrip("/") +
            '/vnflcm/v1/vnf_lcm_op_occs/'
            'f26f181d-7891-4720-b022-b074ec1733ef'
        },
        "vnfInstance": {
            "href": CONF.vnf_lcm.endpoint_url.rstrip("/") +
            '/vnflcm/v1/vnf_instances/'
            'f26f181d-7891-4720-b022-b074ec1733ef'
        },
        "retry": {
            "href": CONF.vnf_lcm.endpoint_url.rstrip("/") +
            '/vnflcm/v1/vnf_lcm_op_occs/'
            'f26f181d-7891-4720-b022-b074ec1733ef/retry'
        },
        "rollback": {
            "href": CONF.vnf_lcm.endpoint_url.rstrip("/") +
            '/vnflcm/v1/vnf_lcm_op_occs/'
            'f26f181d-7891-4720-b022-b074ec1733ef/rollback'
        },
        "grant": {
            "href": CONF.vnf_lcm.endpoint_url.rstrip("/") +
            '/vnflcm/v1/vnf_lcm_op_occs/'
            'f26f181d-7891-4720-b022-b074ec1733ef/grant',
        },
        "fail": {
            "href": CONF.vnf_lcm.endpoint_url.rstrip("/") +
            '/vnflcm/v1/vnf_lcm_op_occs/'
            'f26f181d-7891-4720-b022-b074ec1733ef/fail'}},
    'operationState': 'COMPLETED',
    'stateEnteredTime': datetime.datetime(1900, 1, 1, 1, 1, 1,
                            tzinfo=datetime.timezone.utc),
    'startTime': datetime.datetime(1900, 1, 1, 1, 1, 1,
                            tzinfo=datetime.timezone.utc),
    'vnfInstanceId': 'f26f181d-7891-4720-b022-b074ec1733ef',
    'grantId': 'f26f181d-7891-4720-b022-b074ec1733ef',
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
        'metadata': {'key': 'value'},
        'vimConnectionInfo': [
            {"id": 'f8c35bd0-4d67-4436-9f11-14b8a84c92aa',
             "vimId": 'f8c35bd0-4d67-4436-9f11-14b8a84c92aa',
             "vimType": 'openstack',
             'interfaceInfo': {},
             "accessInfo": {"key1": 'value1', "key2": 'value2'},
             "extra": {}}],
        'vimConnectionInfoDeleteIds': ['f8c35bd0-4d67-4436-9f11-14b8a84c92bb'],
        'vnfPkgId': 'f26f181d-7891-4720-b022-b074ec1733ef',
        'vnfInstanceName': 'fake_name',
        'vnfInstanceDescription': "fake_vnf_instance_description",
        'vnfdId': 'f26f181d-7891-4720-b022-b074ec1733ef',
        'vnfProvider': 'fake_vnf_provider',
        'vnfProductName': 'fake_vnf_product_name',
        'vnfSoftwareVersion': 'fake_vnf_software_version',
        'vnfdVersion': 'fake_vnfd_version'
    },
    "changedExtConnectivity": [{
        "id": constants.UUID,
        "resourceHandle": {
            "vimConnectionId": constants.UUID,
            "resourceId": constants.UUID,
            "vimLevelResourceType": "OS::Neutron::Net",
        },
        "extLinkPorts": [{
            "id": constants.UUID,
            "resourceHandle": {
                "vimConnectionId": constants.UUID,
                "resourceId": constants.UUID,
                "vimLevelResourceType": "OS::Neutron::Port",
            },
            "cpInstanceId": constants.UUID,
        }]
    }]
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

    vim_connection_info = {
        "id": 'f8c35bd0-4d67-4436-9f11-14b8a84c92aa',
        "vim_id": 'f8c35bd0-4d67-4436-9f11-14b8a84c92aa',
        "vim_type": 'openstack',
        "access_info": {"key1": 'value1', "key2": 'value2'}}
    changed_info = {
        "vnf_instance_name": "fake_name",
        "vnf_instance_description":
            "fake_vnf_instance_description",
        'metadata': {'key': 'value'},
        'vim_connection_info': [VimConnectionInfo(**vim_connection_info)],
        'vim_connection_info_delete_ids': [
            'f8c35bd0-4d67-4436-9f11-14b8a84c92bb'],
        'vnf_pkg_id': 'f26f181d-7891-4720-b022-b074ec1733ef',
        "vnfd_id": "f26f181d-7891-4720-b022-b074ec1733ef",
        "vnf_provider": "fake_vnf_provider",
        "vnf_product_name": "fake_vnf_product_name",
        "vnf_software_version": "fake_vnf_software_version",
        "vnfd_version": "fake_vnfd_version"
    }
    changed_info_obj = objects.VnfInfoModifications(**changed_info)

    changed_ext_connectivity = [{
        "id": constants.UUID,
        "resource_handle": {
            "vim_connection_id": constants.UUID,
            "resource_id": constants.UUID,
            "vim_level_resource_type": "OS::Neutron::Net",
        },
        "ext_link_ports": [{
            "id": constants.UUID,
            "resource_handle": {
                "vim_connection_id": constants.UUID,
                "resource_id": constants.UUID,
                "vim_level_resource_type": "OS::Neutron::Port",
            },
            "cp_instance_id": constants.UUID,
        }]
    }]
    changed_ext_connectivity_obj = \
        [objects.ExtVirtualLinkInfo.obj_from_primitive(
         chg_ext_conn, context) for chg_ext_conn in
         changed_ext_connectivity]

    dt = datetime.datetime(1900, 1, 1, 1, 1, 1, tzinfo=datetime.timezone.utc)
    vnf_lcm_op_occs = {
        'id': constants.UUID,
        'operation_state': 'COMPLETED',
        'state_entered_time': dt,
        'start_time': dt,
        'vnf_instance_id': constants.UUID,
        'grant_id': constants.UUID,
        'operation': 'MODIFY_INFO',
        'is_automatic_invocation': False,
        'operation_params': '{"is_reverse": False, "is_auto": False}',
        'is_cancel_pending': False,
        'error': error_obj,
        'resource_changes': resource_changes_obj,
        'changed_info': changed_info_obj,
        'changed_ext_connectivity': changed_ext_connectivity_obj,
    }

    return vnf_lcm_op_occs


def return_vnf_lcm_opoccs_obj(**updates):
    vnf_lcm_op_occs = fake_vnf_lcm_op_occs()

    if updates:
        vnf_lcm_op_occs.update(**updates)

    obj = objects.VnfLcmOpOcc(**vnf_lcm_op_occs)

    return obj


def vnflcm_op_occs_retry_data(error_point=7, operation='INSTANTIATE',
        operation_state='FAILED_TEMP'):
    now = datetime.datetime(2000, 1, 1, 1, 1, 1, tzinfo=datetime.timezone.utc)
    return objects.VnfLcmOpOcc(
        state_entered_time=now,
        start_time=now,
        vnf_instance_id=uuidsentinel.vnf_instance_id,
        operation=operation,
        operation_state=operation_state,
        is_automatic_invocation=False,
        operation_params='{}',
        error_point=error_point,
        id=constants.UUID,
        created_at=now)


def vnf_data(status='ACTIVE'):
    return tacker.db.vnfm.vnfm_db.VNF(id=constants.UUID,
        vnfd_id=uuidsentinel.vnfd_id,
        name='test',
        status=status,
        vim_id=uuidsentinel.vim_id)


def return_vnf_lcm_opoccs_list():
    vnf_lcm_op_occs = fake_vnf_lcm_op_occs()
    obj = objects.VnfLcmOpOcc(**vnf_lcm_op_occs)

    return [obj]


def get_change_ext_conn_request_body():
    change_ext_conn_req_body = {
        "extVirtualLinks": [{
            "id": 'f8c35bd0-4d67-4436-9f11-14b8a84c92aa',
            "vimConnectionId": '2b3beeff-d4a1-4dc7-a1f8-066f92cfcb75',
            "resourceId": 'e08f5e67-55de-4c4a-815b-cf3f1e2bae04',
            "extCps": [{
                "cpdId": 'VDU2_CP2',
                "cpConfig": [{
                    "cpInstanceId": '924d0ea7-786d-468b-bf45-65bfd483ee79',
                    "linkPortId": 'f8c35bd0-4d67-4436-9f11-14b8a84c92aa',
                    "cpProtocolData": [{
                        "layerProtocol": 'IP_OVER_ETHERNET',
                        "ipOverEthernet": {
                            "macAddress":
                                'fa:16:3e:11:11:11',
                            "ipAddresses": [{
                                "type": "IPV4",
                                "fixedAddresses": ["22.22.1.20"],
                                "subnetId":
                                    '497b7a75-6c10-4a74-85fa-83d498da2501'
                            }]
                        }
                    }]
                }]
            }],
            "extLinkPorts": [{
                "id": 'decd78d2-993c-4112-9a8f-1ad54cade4d7',
                "resourceHandle": {
                    "resourceId": 'cb602960-05ee-4e03-8fe2-ea0b64e08332',
                    "vimConnectionId": '2b3beeff-d4a1-4dc7-a1f8-066f92cfcb75',
                    "vimLevelResourceType":
                        'f8c35bd0-4d67-4436-9f11-14b8a84c92aa',
                }
            }],
            "vimConnectionInfo": [{
                "id": '2b3beeff-d4a1-4dc7-a1f8-066f92cfcb75',
                "vimId": 'f8c35bd0-4d67-4436-9f11-14b8a84c92aa',
                "vimType": 'openstack',
                "interfaceInfo": {"key1": 'value1', "key2": 'value2'},
                "accessInfo": {"key1": 'value1', "key2": 'value2'}
            }],
        }]
    }

    return change_ext_conn_req_body


def get_change_ext_conn_request_obj():
    """Return ChangeExtConnRequest Object

    obj_from_primitive() needs snake_case dictionary
    """
    body = utils.convert_camelcase_to_snakecase(
        get_change_ext_conn_request_body())
    return ChangeExtConnRequest.obj_from_primitive(
        body, context)


def _fake_subscription_obj(**updates):
    subscription = {
        'id': uuidsentinel.subscription_id,
        'filter': {
            "vnfInstanceSubscriptionFilter": {
                "vnfdIds": [uuidsentinel.vnfd_id],
                "vnfProductsFromProviders": {
                    "vnfProvider": "Vnf Provider 1",
                    "vnfProducts": [
                        {
                            "vnfProductName": "Vnf Product 1",
                            "versions": [
                                {
                                    "vnfSoftwareVersion": "v1",
                                    "vnfdVersions": [
                                        "vnfd.v1.1"
                                    ]
                                }
                            ]
                        }
                    ]
                },
                "vnfInstanceIds": [
                    uuidsentinel.vnf_instance_id
                ],
                "vnfInstanceNames": ["Vnf Name 1"]
            },
            "notificationTypes": [
                "VnfLcmOperationOccurrenceNotification",
                "VnfIdentifierCreationNotification",
                "VnfIdentifierDeletionNotification"
            ],
            "operationTypes": [
                "INSTANTIATE",
                "SCALE",
                "TERMINATE",
                "HEAL",
                "CHANGE_EXT_CONN",
                "MODIFY_INFO"
            ],
            "operationStates": [
                "STARTING",
                "PROCESSING",
                "COMPLETED",
                "FAILED_TEMP",
                "FAILED",
                "ROLLING_BACK",
                "ROLLED_BACK"
            ]
        },
        'callback_uri': 'http://localhost/sample_callback_uri'}

    if updates:
        subscription.update(**updates)

    return subscription


def return_subscription_object(**updates):
    vnf_lcm_subscription = _fake_subscription_obj(**updates)
    return vnf_lcm_subscription


def return_vnf_subscription_list(**updates):
    vnc_lcm_subscription = return_subscription_object(**updates)
    return [vnc_lcm_subscription]


def _subscription_links(subscription_dict):
    links = {
        "_links": {
            "self": {
                "href":
                "{endpoint}/vnflcm/v1/subscriptions/{id}".format(
                    id=subscription_dict['id'],
                    endpoint=CONF.vnf_lcm.endpoint_url.rstrip("/"))
            }
        }
    }
    subscription_dict.update(links)

    return subscription_dict


def return_lccn_subscription(**updates):
    subscription = _fake_subscription_obj(**updates)
    subscription['filter'] = json.dumps(subscription['filter'])
    obj = objects.LccnSubscription(**subscription)

    return obj


def return_lccn_subscription_obj(**updates):
    subscription = _fake_subscription_obj(**updates)
    subscription['filter'] = json.dumps(subscription['filter'])
    obj = objects.LccnSubscriptionRequest(**subscription)

    return obj


def fake_subscription_response(**updates):
    data = _fake_subscription_obj(**updates)
    data = utils.convert_snakecase_to_camelcase(data)
    data = _subscription_links(data)

    return data


def get_test_data_policy_create():
    rules = {vnf_lcm_policies.VNFLCM % 'create': "vendor:%(vendor)s"}
    test_data = [
        # 'expected_status_code': http_client.OK
        {
            'vnfd_updates': {'vnf_provider': 'provider_A'},
            'rules': rules,
            'roles': ['VENDOR_provider_A'],
            'expected_status_code': http_client.CREATED
        },
        {
            'vnfd_updates': {'vnf_provider': 'provider_A'},
            'rules': rules,
            'roles': ['VENDOR_all'],
            'expected_status_code': http_client.CREATED
        },
        {
            'vnfd_updates': {'vnf_provider': 'provider_B'},
            'rules': rules,
            'roles': ['VENDOR_provider_B'],
            'expected_status_code': http_client.CREATED
        },
        {
            'vnfd_updates': {'vnf_provider': 'provider_B'},
            'rules': rules,
            'roles': ['VENDOR_all'],
            'expected_status_code': http_client.CREATED
        },
        {
            'vnfd_updates': {'vnf_provider': 'provider_B'},
            'rules': {vnf_lcm_policies.VNFLCM % 'create': "@"},
            'roles': [],
            'expected_status_code': http_client.CREATED
        },
        # 'expected_status_code': http_client.FORBIDDEN
        {
            'vnfd_updates': {'vnf_provider': ''},
            'rules': rules,
            'roles': ['VENDOR_'],
            'expected_status_code': http_client.FORBIDDEN
        },
        {
            'vnfd_updates': {'vnf_provider': 'provider_A'},
            'rules': rules,
            'roles': ['VENDOR_B'],
            'expected_status_code': http_client.FORBIDDEN
        },
        {
            'vnfd_updates': {'vnf_provider': 'provider_B'},
            'rules': rules,
            'roles': ['VENDOR_A'],
            'expected_status_code': http_client.FORBIDDEN
        },
        {
            'vnfd_updates': {'vnf_provider': 'provider_A'},
            'rules': rules,
            'roles': [],
            'expected_status_code': http_client.FORBIDDEN
        },
    ]
    return test_data


def make_vnf_instance(vim_type, vendor, area=None, tenant=None,
        instantiated_state=fields.VnfInstanceState.NOT_INSTANTIATED):
    vnf_instance_updates = make_vnf_instance_updates(
        vim_type, vendor, area=area, tenant=tenant)
    return return_vnf_instance(instantiated_state, **vnf_instance_updates)


def get_test_data_policy_index():
    rule_area_vendor_tenant = {
        vnf_lcm_policies.VNFLCM % 'index':
            "area:%(area)s and vendor:%(vendor)s and "
            "tenant:%(tenant)s"
    }
    test_data = []
    inst_1 = make_vnf_instance('openstack', 'provider_A',
                               area='area_A@region_A', tenant='tenant_A')
    test_data.append({
        'vnf_instance_list': [inst_1],
        'rules': rule_area_vendor_tenant,
        'roles': ['AREA_area_A@region_A', 'VENDOR_provider_A',
                  'TENANT_tenant_A'],
        'expected_vnf_inst_ids': [inst_1.id]
    })
    test_data.append({
        'vnf_instance_list': [inst_1],
        'rules': rule_area_vendor_tenant,
        'roles': ['AREA_all@region_A', 'VENDOR_provider_A',
                  'TENANT_tenant_A'],
        'expected_vnf_inst_ids': [inst_1.id]
    })
    test_data.append({
        'vnf_instance_list': [inst_1],
        'rules': rule_area_vendor_tenant,
        'roles': ['AREA_all@all', 'VENDOR_all',
                  'TENANT_tenant_A'],
        'expected_vnf_inst_ids': [inst_1.id]
    })
    test_data.append({
        'vnf_instance_list': [inst_1],
        'rules': rule_area_vendor_tenant,
        'roles': ['AREA_all@all', 'VENDOR_all',
                  'TENANT_all'],
        'expected_vnf_inst_ids': [inst_1.id]
    })
    inst_2 = make_vnf_instance(
        'openstack', 'provider_A', area='area_A@region_A', tenant='tenant_A',
        instantiated_state=fields.VnfInstanceState.INSTANTIATED)
    test_data.append({
        'vnf_instance_list': [inst_2],
        'rules': rule_area_vendor_tenant,
        'roles': ['AREA_area_A@region_A', 'VENDOR_provider_A',
                  'TENANT_tenant_A'],
        'expected_vnf_inst_ids': [inst_2.id]
    })
    test_data.append({
        'vnf_instance_list': [inst_2],
        'rules': rule_area_vendor_tenant,
        'roles': ['AREA_all@region_A', 'VENDOR_provider_A',
                  'TENANT_tenant_A'],
        'expected_vnf_inst_ids': [inst_2.id]
    })
    test_data.append({
        'vnf_instance_list': [inst_2],
        'rules': rule_area_vendor_tenant,
        'roles': ['AREA_all@all', 'VENDOR_all',
                  'TENANT_tenant_A'],
        'expected_vnf_inst_ids': [inst_2.id]
    })
    test_data.append({
        'vnf_instance_list': [inst_2],
        'rules': rule_area_vendor_tenant,
        'roles': ['AREA_all@all', 'VENDOR_all',
                  'TENANT_all'],
        'expected_vnf_inst_ids': [inst_2.id]
    })
    inst_3 = make_vnf_instance(
        'openstack', 'provider_A', tenant='tenant_A',
        instantiated_state=fields.VnfInstanceState.INSTANTIATED)
    test_data.append({
        'vnf_instance_list': [inst_3],
        'rules': rule_area_vendor_tenant,
        'roles': ['AREA_area_A@region_A', 'VENDOR_provider_A',
                  'TENANT_tenant_A'],
        'expected_vnf_inst_ids': []
    })
    test_data.append({
        'vnf_instance_list': [inst_3],
        'rules': rule_area_vendor_tenant,
        'roles': ['AREA_all@region_A', 'VENDOR_provider_A',
                  'TENANT_tenant_A'],
        'expected_vnf_inst_ids': []
    })
    test_data.append({
        'vnf_instance_list': [inst_3],
        'rules': rule_area_vendor_tenant,
        'roles': ['AREA_all@all', 'VENDOR_all',
                  'TENANT_tenant_A'],
        'expected_vnf_inst_ids': []
    })
    test_data.append({
        'vnf_instance_list': [inst_3],
        'rules': rule_area_vendor_tenant,
        'roles': ['AREA_all@all', 'VENDOR_all',
                  'TENANT_all'],
        'expected_vnf_inst_ids': []
    })
    inst_4 = make_vnf_instance(
        'kubernetes', 'provider_A',
        tenant='namespace_A',
        area='area_A@region_A',
        instantiated_state=fields.VnfInstanceState.INSTANTIATED)
    test_data.append({
        'vnf_instance_list': [inst_4],
        'rules': rule_area_vendor_tenant,
        'roles': [
            'AREA_area_A@region_A',
            'VENDOR_provider_A',
            'TENANT_namespace_A'
        ],
        'expected_vnf_inst_ids': [inst_4.id]
    })
    test_data.append({
        'vnf_instance_list': [inst_4],
        'rules': rule_area_vendor_tenant,
        'roles': [
            'AREA_all@region_A',
            'VENDOR_provider_A',
            'TENANT_namespace_A'
        ],
        'expected_vnf_inst_ids': [inst_4.id]
    })
    test_data.append({
        'vnf_instance_list': [inst_4],
        'rules': rule_area_vendor_tenant,
        'roles': [
            'AREA_all@all',
            'VENDOR_all',
            'TENANT_namespace_A'
        ],
        'expected_vnf_inst_ids': [inst_4.id]
    })

    return test_data


def get_test_data_policy_instantiate():
    test_data = [
        # 'expected_status_code': http_client.ACCEPTED
        {
            'vnf_instance_updates': {'vnf_provider': 'provider_A'},
            'rules': {
                "os_nfv_orchestration_api:vnf_instances:instantiate":
                    "vendor:%(vendor)s"
            },
            'roles': ['VENDOR_provider_A'],
            'expected_status_code': http_client.ACCEPTED
        },
        {
            'vnf_instance_updates': {'vnf_provider': 'provider_A'},
            'rules': {
                "os_nfv_orchestration_api:vnf_instances:instantiate":
                    "vendor:%(vendor)s"
            },
            'roles': ['VENDOR_all'],
            'expected_status_code': http_client.ACCEPTED
        },
        # 'expected_status_code': http_client.FORBIDDEN
        {
            'vnf_instance_updates': {'vnf_provider': 'provider_A'},
            'rules': {
                "os_nfv_orchestration_api:vnf_instances:instantiate":
                    "vendor:%(vendor)s"
            },
            'roles': [],
            'expected_status_code': http_client.FORBIDDEN
        },
        {
            'vnf_instance_updates': {'vnf_provider': 'provider_A'},
            'rules': {
                "os_nfv_orchestration_api:vnf_instances:instantiate":
                    "vendor:%(vendor)s"
            },
            'roles': ['VENDOR_provider_B'],
            'expected_status_code': http_client.FORBIDDEN
        },
    ]
    return test_data


def get_test_data_policy_delete():
    test_data = [
        # 'expected_status_code': http_client.NO_CONTENT
        {
            'vnf_instance_updates': {'vnf_provider': 'provider_A'},
            'rules': {
                "os_nfv_orchestration_api:vnf_instances:delete":
                    "vendor:%(vendor)s"
            },
            'roles': ['VENDOR_provider_A'],
            'expected_status_code': http_client.NO_CONTENT
        },
        {
            'vnf_instance_updates': {'vnf_provider': 'provider_A'},
            'rules': {
                "os_nfv_orchestration_api:vnf_instances:delete":
                    "vendor:%(vendor)s"
            },
            'roles': ['VENDOR_all'],
            'expected_status_code': http_client.NO_CONTENT
        },
        # 'expected_status_code': http_client.FORBIDDEN
        {
            'vnf_instance_updates': {'vnf_provider': 'provider_A'},
            'rules': {
                "os_nfv_orchestration_api:vnf_instances:delete":
                    "vendor:%(vendor)s"
            },
            'roles': [],
            'expected_status_code': http_client.FORBIDDEN
        },
        {
            'vnf_instance_updates': {'vnf_provider': 'provider_A'},
            'rules': {
                "os_nfv_orchestration_api:vnf_instances:delete":
                    "vendor:%(vendor)s"
            },
            'roles': ['VENDOR_provider_B'],
            'expected_status_code': http_client.FORBIDDEN
        },
    ]
    return test_data


def get_test_data_policy_vnf_not_instantiated(
        action, success_status_code=http_client.OK):
    # openstack
    vim_connection_info = {
        "id": 'f8c35bd0-4d67-4436-9f11-14b8a84c92aa',
        "vim_id": 'f8c35bd0-4d67-4436-9f11-14b8a84c92aa',
        "vim_type": 'openstack',
        "access_info": {"key1": 'value1', "key2": 'value2'},
        'extra': {'area': 'area_A@region_A'}
    }
    vim_connection_info_wrong_area = {
        "id": 'f8c35bd0-4d67-4436-9f11-14b8a84c92aa',
        "vim_id": 'f8c35bd0-4d67-4436-9f11-14b8a84c92aa',
        "vim_type": 'openstack',
        "access_info": {"key1": 'value1', "key2": 'value2'},
        'extra': {'area': 'area_A'}
    }
    vnf_instance_updates = {
        'vnf_provider': 'provider_A',
        'vim_connection_info': [vim_connection_info]
    }
    vnf_instance_updates_with_wrong_area = {
        'vnf_provider': 'provider_A',
        'vim_connection_info': [vim_connection_info_wrong_area]
    }
    rule_area_vendor_tenant = {
        vnf_lcm_policies.VNFLCM % action:
            "area:%(area)s and vendor:%(vendor)s and "
            "tenant:%(tenant)s"
    }
    rule_vendor = {
        vnf_lcm_policies.VNFLCM % action: "vendor:%(vendor)s"
    }
    test_data = [
        # 'expected_status_code': http_client.OK
        {
            'vnf_instance_updates': vnf_instance_updates,
            'rules': rule_area_vendor_tenant,
            'roles': ['AREA_area_A@region_A', 'VENDOR_provider_A',
                      'TENANT_tenant_A'],
            'expected_status_code': success_status_code
        },
        {
            'vnf_instance_updates': vnf_instance_updates,
            'rules': rule_area_vendor_tenant,
            'roles': ['AREA_all@all', 'VENDOR_all', 'TENANT_all'],
            'expected_status_code': success_status_code
        },
        {
            'vnf_instance_updates': vnf_instance_updates,
            'rules': rule_area_vendor_tenant,
            'roles': ['AREA_all@region_A', 'VENDOR_all', 'TENANT_all'],
            'expected_status_code': success_status_code
        },
        {
            'vnf_instance_updates': vnf_instance_updates,
            'rules': rule_area_vendor_tenant,
            'roles': [
                'AREA_all@region_A', 'AREA_all@all', 'VENDOR_all',
                'TENANT_all'],
            'expected_status_code': success_status_code
        },
        {
            'vnf_instance_updates': vnf_instance_updates,
            'rules': rule_vendor,
            'roles': ['AREA_area_A@region_A', 'VENDOR_provider_A',
                      'TENANT_tenant_A'],
            'expected_status_code': success_status_code
        },
        {
            'vnf_instance_updates': vnf_instance_updates,
            'rules': rule_vendor,
            'roles': ['AREA_all@all', 'VENDOR_all', 'TENANT_all'],
            'expected_status_code': success_status_code
        },
        {
            'vnf_instance_updates': vnf_instance_updates,
            'rules': rule_vendor,
            'roles': ['AREA_all@region_A', 'VENDOR_all', 'TENANT_all'],
            'expected_status_code': success_status_code
        },
        {
            'vnf_instance_updates': vnf_instance_updates,
            'rules': rule_area_vendor_tenant,
            'roles': ['AREA_area_A@region_A', 'VENDOR_provider_A',
                      'TENANT_tenant_B'],
            'expected_status_code': success_status_code
        },
        # 'expected_status_code': http_client.FORBIDDEN
        {
            'vnf_instance_updates': vnf_instance_updates,
            'rules': rule_area_vendor_tenant,
            'roles': [],
            'expected_status_code': http_client.FORBIDDEN
        },
        {
            'vnf_instance_updates': vnf_instance_updates,
            'rules': rule_area_vendor_tenant,
            'roles': ['AREA_area_A@region_A'],
            'expected_status_code': http_client.FORBIDDEN
        },
        {
            'vnf_instance_updates': vnf_instance_updates,
            'rules': rule_area_vendor_tenant,
            'roles': ['VENDOR_provider_A'],
            'expected_status_code': http_client.FORBIDDEN
        },
        {
            'vnf_instance_updates': vnf_instance_updates,
            'rules': rule_area_vendor_tenant,
            'roles': ['TENANT_tenant_A'],
            'expected_status_code': http_client.FORBIDDEN
        },
        {
            'vnf_instance_updates': vnf_instance_updates,
            'rules': rule_area_vendor_tenant,
            'roles': ['AREA_area_A@region_A', 'VENDOR_provider_B',
                      'TENANT_tenant_A'],
            'expected_status_code': http_client.FORBIDDEN
        },
        {
            'vnf_instance_updates': vnf_instance_updates,
            'rules': rule_area_vendor_tenant,
            'roles': ['AREA_area_B@region_A', 'VENDOR_provider_A',
                      'TENANT_tenant_A'],
            'expected_status_code': http_client.FORBIDDEN
        },
        {
            'vnf_instance_updates': vnf_instance_updates,
            'rules': rule_area_vendor_tenant,
            'roles': ['AREA_all@region_B', 'VENDOR_provider_A',
                      'TENANT_tenant_A'],
            'expected_status_code': http_client.FORBIDDEN
        },
        {
            'vnf_instance_updates': vnf_instance_updates,
            'rules': rule_area_vendor_tenant,
            'roles': ['AREA_all', 'VENDOR_provider_A',
                      'TENANT_tenant_A'],
            'expected_status_code': http_client.FORBIDDEN
        },
        {
            'vnf_instance_updates': vnf_instance_updates,
            'rules': rule_area_vendor_tenant,
            'roles': ['AREA_all@', 'VENDOR_provider_A',
                      'TENANT_tenant_A'],
            'expected_status_code': http_client.FORBIDDEN
        },
        {
            'vnf_instance_updates': vnf_instance_updates_with_wrong_area,
            'rules': rule_area_vendor_tenant,
            'roles': ['AREA_all@', 'VENDOR_provider_A',
                      'TENANT_tenant_A'],
            'expected_status_code': http_client.FORBIDDEN
        },
    ]
    return test_data


def make_vnf_instance_updates(
        vim_type, vendor, area=None, tenant=None):
    vim_connection_info = VimConnectionInfo(
        id='f8c35bd0-4d67-4436-9f11-14b8a84c92aa',
        vim_id='f8c35bd0-4d67-4436-9f11-14b8a84c92aa',
        vim_type=vim_type,
        access_info={"key1": 'value1', "key2": 'value2'},
    )
    if area:
        vim_connection_info.extra = {'area': area}
    vnf_instance_updates = {
        'vnf_provider': vendor,
        'vim_connection_info': [vim_connection_info]
    }
    if tenant:
        vnf_instance_updates.update({'vnf_metadata': {"tenant": tenant}})

    return vnf_instance_updates


def get_test_data_policy_vnf_instantiated(action, success_status_code):
    rule_area_vendor_tenant = {
        vnf_lcm_policies.VNFLCM % action:
            "area:%(area)s and vendor:%(vendor)s and "
            "tenant:%(tenant)s"
    }

    test_data = []
    # openstack
    vnf_instance_updates_1 = make_vnf_instance_updates(
        'openstack', 'provider_A', area='area_A@region_A',
        tenant='tenant_A')
    test_data.append({
        'vnf_instance_updates': vnf_instance_updates_1,
        'rules': rule_area_vendor_tenant,
        'roles': [
            'AREA_area_A@region_A',
            'VENDOR_provider_A',
            'TENANT_tenant_A'
        ],
        'expected_status_code': success_status_code
    })
    test_data.append({
        'vnf_instance_updates': vnf_instance_updates_1,
        'rules': rule_area_vendor_tenant,
        'roles': [
            'AREA_all@region_A',
            'VENDOR_provider_A',
            'TENANT_tenant_A'
        ],
        'expected_status_code': success_status_code
    })
    test_data.append({
        'vnf_instance_updates': vnf_instance_updates_1,
        'rules': rule_area_vendor_tenant,
        'roles': [
            'AREA_all@all',
            'VENDOR_provider_A',
            'TENANT_tenant_A'
        ],
        'expected_status_code': success_status_code
    })
    test_data.append({
        'vnf_instance_updates': vnf_instance_updates_1,
        'rules': rule_area_vendor_tenant,
        'roles': [
            'AREA_all@all',
            'VENDOR_all',
            'TENANT_tenant_A'
        ],
        'expected_status_code': success_status_code
    })
    test_data.append({
        'vnf_instance_updates': vnf_instance_updates_1,
        'rules': rule_area_vendor_tenant,
        'roles': [
            'AREA_all@all',
            'VENDOR_all',
            'TENANT_all'
        ],
        'expected_status_code': success_status_code
    })
    # wrong area role
    test_data.append({
        'vnf_instance_updates': vnf_instance_updates_1,
        'rules': rule_area_vendor_tenant,
        'roles': [
            'AREA_area_B@region_A',
            'VENDOR_provider_A',
            'TENANT_tenant_A'
        ],
        'expected_status_code': http_client.FORBIDDEN
    })
    # wrong region role
    test_data.append({
        'vnf_instance_updates': vnf_instance_updates_1,
        'rules': rule_area_vendor_tenant,
        'roles': [
            'AREA_area_A@region_B',
            'VENDOR_provider_A',
            'TENANT_tenant_A'
        ],
        'expected_status_code': http_client.FORBIDDEN
    })
    # wrong vendor role
    test_data.append({
        'vnf_instance_updates': vnf_instance_updates_1,
        'rules': rule_area_vendor_tenant,
        'roles': [
            'AREA_area_A@region_A',
            'VENDOR_provider_B',
            'TENANT_tenant_A'
        ],
        'expected_status_code': http_client.FORBIDDEN
    })
    # wrong tenant role
    test_data.append({
        'vnf_instance_updates': vnf_instance_updates_1,
        'rules': rule_area_vendor_tenant,
        'roles': [
            'AREA_area_A@region_A',
            'VENDOR_provider_A',
            'TENANT_tenant_B'
        ],
        'expected_status_code': http_client.FORBIDDEN
    })
    vnf_instance_updates_2 = make_vnf_instance_updates(
        'openstack', 'provider_A')
    test_data.append({
        'vnf_instance_updates': vnf_instance_updates_2,
        'rules': rule_area_vendor_tenant,
        'roles': [
            'AREA_area_A@region_A',
            'VENDOR_provider_A',
            'TENANT_tenant_A'
        ],
        'expected_status_code': http_client.FORBIDDEN
    })

    # kubernetes
    vnf_instance_updates_3 = make_vnf_instance_updates(
        'kubernetes', 'provider_A', area='area_A@region_A',
        tenant='namespace_A')
    test_data.append({
        'vnf_instance_updates': vnf_instance_updates_3,
        'rules': rule_area_vendor_tenant,
        'roles': [
            'AREA_area_A@region_A',
            'VENDOR_provider_A',
            'TENANT_namespace_A'
        ],
        'expected_status_code': success_status_code
    })
    test_data.append({
        'vnf_instance_updates': vnf_instance_updates_3,
        'rules': rule_area_vendor_tenant,
        'roles': [
            'AREA_all@all',
            'VENDOR_all',
            'TENANT_all'
        ],
        'expected_status_code': success_status_code
    })

    return test_data


def fake_extract_policy_infos():
    return {
        'inst_level_dict': {
            'instantiation_level_1': {'vdu1_aspect': 0},
            'instantiation_level_2': {'vdu1_aspect': 2}
        },
        'aspect_delta_dict': {'vdu1_aspect': {'delta_1': 1}},
        'aspect_id_dict': {'vdu1_aspect': 'delta_1'},
        'aspect_vdu_dict': {'vdu1_aspect': ['VDU1']},
        'vdu_delta_dict': {'VDU1': 1},
        'aspect_max_level_dict': {'vdu1_aspect': 2},
        'default_inst_level_id': 'instantiation_level_1'
    }
