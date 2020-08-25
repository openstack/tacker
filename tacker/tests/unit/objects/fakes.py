# Copyright (C) 2019 NTT DATA
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
import datetime
import iso8601

from tacker.db.db_sqlalchemy import models
from tacker.tests import constants
from tacker.tests import uuidsentinel

vnf_package_data = {'algorithm': None, 'hash': None,
                    'location_glance_store': None,
                    'onboarding_state': 'CREATED',
                    'operational_state': 'DISABLED',
                    'tenant_id': uuidsentinel.tenant_id,
                    'usage_state': 'NOT_IN_USE',
                    'user_data': {'abc': 'xyz'},
                    'created_at': datetime.datetime(
                        2019, 8, 8, 0, 0, 0, tzinfo=iso8601.UTC),
                    'deleted': False,
                    'size': 0
                    }

software_image = {
    'software_image_id': uuidsentinel.software_image_id,
    'name': 'test', 'provider': 'test', 'version': 'test',
    'algorithm': 'sha-256',
    'hash': 'b9c3036539fd7a5f87a1bf38eb05fdde8b556a1'
            'a7e664dbeda90ed3cd74b4f9d',
    'container_format': 'test', 'disk_format': 'qcow2', 'min_disk': 1,
    'min_ram': 2, 'size': 1, 'image_path': 'test',
    'metadata': {'key1': 'value1'}
}

artifact_data = {
    'file_name': 'test', 'type': 'test',
    'algorithm': 'sha-256',
    'hash': 'b9c3036539fd7a5f87a1bf38eb05fdde8b556a1'
            'a7e664dbeda90ed3cd74b4f9d',
    'metadata': {'key1': 'value1'}
}

artifacts = {
    'json_data': 'test data',
    'type': 'tosca.artifacts.nfv.SwImage',
    'algorithm': 'sha512', 'hash': uuidsentinel.hash}

filter = {
    "usageState": ["NOT_IN_USE"],
    "vnfPkgId": ["f04857cb-abdc-405f-8254-01501f3fa059"],
    "vnfdId": ["b1bb0ce7-5555-0001-95ed-4840d70a1209"],
    "vnfProductsFromProviders": [
        {
            "vnfProvider": "xxxxx",
            "vnfProducts": [
                {
                    "vnfProductName": "artifactVNF",
                    "versions": [
                        {
                            "vnfSoftwareVersion": "1.0",
                            "vnfdVersions": ["v2.2"]
                        }
                    ]
                }
            ]
        },
        {
            "vnfProvider": "xxxxx",
            "vnfProducts": [
                {
                    "vnfProductName": "artifactVNF",
                    "versions": [
                        {
                            "vnfSoftwareVersion": "1.0",
                            "vnfdVersions": ["v2.2"]
                        }
                    ]
                }
            ]
        }
    ],
    "notificationTypes": ["VnfLcmOperationOccurrenceNotification"],
    "operationalState": ["ENABLED"]
}

subscription_data = {
    'id': "c3e5ea85-8e3d-42df-a636-3b7857cbd7f9",
    'callback_uri': "fake_url",
    'created_at': "2020-06-11 09:39:58"
}

vnfd_data = {
    "tenant_id": uuidsentinel.tenant_id,
    'name': 'test',
    'description': 'test_description',
    'mgmt_driver': 'test_mgmt_driver'
}

vnfd_attribute = {
    'key': 'test_key',
    'value': 'test_value',
}

lcm_op_occs_data = {
    "tenant_id": uuidsentinel.tenant_id,
    'operation_state': 'PROCESSING',
    'state_entered_time': datetime.datetime(1900, 1, 1, 1, 1, 1,
                                            tzinfo=iso8601.UTC),
    'start_time': datetime.datetime(1900, 1, 1, 1, 1, 1,
                                    tzinfo=iso8601.UTC),
    'operation': 'MODIFY_INFO',
    'is_automatic_invocation': 0,
    'is_cancel_pending': 0,
}

vim_data = {
    'id': uuidsentinel.vim_id,
    'type': 'test_type',
    "tenant_id": uuidsentinel.tenant_id,
    'name': "test_name",
    'description': "test_description",
    'placement_attr': "test_placement_attr",
    'shared': 0,
    'status': "REACHABLE",
    'is_default': 0
}

fake_vnf_package_response = copy.deepcopy(vnf_package_data)
fake_vnf_package_response.pop('user_data')
fake_vnf_package_response.update({'id': uuidsentinel.package_uuid})

vnf_deployment_flavour = {'flavour_id': 'simple',
                          'flavour_description': 'simple flavour description',
                          'instantiation_levels': {
                              'levels': {
                                  'instantiation_level_1': {
                                      'description': 'Smallest size',
                                      'scale_info': {
                                          'worker_instance': {
                                              'scale_level': 0
                                          }
                                      }
                                  },
                                  'instantiation_level_2': {
                                      'description': 'Largest size',
                                      'scale_info': {
                                          'worker_instance': {
                                              'scale_level': 2
                                          }
                                      }
                                  }
                              },
                              'default_level': 'instantiation_level_1'
                          },
                          'created_at': datetime.datetime(
                              2019, 8, 8, 0, 0, 0, tzinfo=iso8601.UTC),
                          }

vnf_artifacts = {
    'artifact_path': 'scripts/install.sh',
    '_metadata': {},
    'algorithm': 'sha-256',
    'hash': 'd0e7828293355a07c2dccaaa765c80b507e60e6167067c950dc2e6b0da0dbd8b',
    'created_at': datetime.datetime(2020, 6, 29, 0, 0, 0, tzinfo=iso8601.UTC),
}


def fake_vnf_package_vnfd_dict(**updates):
    vnf_pkg_vnfd = {
        'package_uuid': uuidsentinel.package_uuid,
        'vnfd_id': uuidsentinel.vnfd_id,
        'vnf_provider': 'test vnf provider',
        'vnf_product_name': 'Sample VNF',
        'vnf_software_version': '1.0',
        'vnfd_version': '1.0'
    }

    if updates:
        vnf_pkg_vnfd.update(updates)

    return vnf_pkg_vnfd


def return_vnf_package_vnfd_data():
    model_obj = models.VnfPackageVnfd()
    model_obj.update(fake_vnf_package_vnfd_dict())
    return model_obj


def get_vnf_package_vnfd_data(vnf_package_id, vnfd_id):
    return {
        'package_uuid': vnf_package_id,
        'vnfd_id': vnfd_id,
        'vnf_provider': 'test vnf provider',
        'vnf_product_name': 'Sample VNF',
        'vnf_software_version': '1.0',
        "vnf_pkg_id": uuidsentinel.vnf_pkg_id,
        'vnfd_version': '1.0',
    }


def get_vnf_instance_data(vnfd_id):
    return {
        "vnf_software_version": "1.0",
        "vnf_product_name": "Sample VNF",
        "vnf_instance_name": 'Sample VNF Instance',
        "vnf_instance_description": 'Sample vnf_instance_description',
        "instantiation_state": "NOT_INSTANTIATED",
        "vnf_provider": "test vnf provider",
        "vnfd_id": vnfd_id,
        "vnfd_version": "1.0",
        "tenant_id": uuidsentinel.tenant_id,
        "vnf_pkg_id": uuidsentinel.vnf_pkg_id,
        "vnf_metadata": {"key": "value"},
    }


def get_vnf_instance_data_with_id(vnfd_id):
    return {
        "id": uuidsentinel.tenant_id,
        "vnf_software_version": "1.0",
        "vnf_product_name": "Sample VNF",
        "vnf_instance_name": 'Sample VNF Instance',
        "vnf_instance_description": 'Sample vnf_instance_description',
        "instantiation_state": "NOT_INSTANTIATED",
        "vnf_provider": "test vnf provider",
        "vnfd_id": vnfd_id,
        "vnfd_version": "1.0",
        "tenant_id": uuidsentinel.tenant_id,
        "vnf_pkg_id": uuidsentinel.vnf_pkg_id,
        "vnf_metadata": {"key": "value"},
    }


def get_lcm_op_occs_data(id, vnf_instance_id):
    return {
        "id": id,
        "tenant_id": uuidsentinel.tenant_id,
        'operation_state': 'PROCESSING',
        'state_entered_time': datetime.datetime(1900, 1, 1, 1, 1, 1,
                                                tzinfo=iso8601.UTC),
        'start_time': datetime.datetime(1900, 1, 1, 1, 1, 1,
                                        tzinfo=iso8601.UTC),
        'vnf_instance_id': vnf_instance_id,
        'operation': 'MODIFY_INFO',
        'is_automatic_invocation': 0,
        'is_cancel_pending': 0,
    }


def fake_vnf_instance_model_dict(**updates):
    vnf_instance = {
        'deleted': False,
        'deleted_at': None,
        'updated_at': None,
        'created_at': datetime.datetime(1900, 1, 1, 1, 1, 1,
                                        tzinfo=iso8601.UTC),
        'vnf_product_name': 'Sample VNF',
        'vnf_instance_name': 'Sample VNF',
        'vnf_instance_description': None,
        'vnf_provider': 'test vnf provider',
        'vnf_software_version': '1.0',
        'vnfd_id': uuidsentinel.vnfd_id,
        'vnfd_version': '1.0',
        'instantiation_state': 'NOT_INSTANTIATED',
        'vim_connection_info': [],
        'tenant_id': '33f8dbdae36142eebf214c1869eb4e4c',
        'vnf_pkg_id': uuidsentinel.vnf_pkg_id,
        'id': constants.UUID,
        'vnf_metadata': {"key": "value"},
    }

    if updates:
        vnf_instance.update(updates)

    return vnf_instance


def fake_vnf_resource_data(instance_id):

    return {
        'vnf_instance_id': instance_id,
        'resource_name': "test",
        'resource_type': "image",
        'resource_identifier': uuidsentinel.image_id,
        'resource_status': "status"
    }


def vnf_pack_vnfd_data(vnf_pack_id):
    return {
        'package_uuid': vnf_pack_id,
        'vnfd_id': uuidsentinel.vnfd_id,
        'vnf_provider': 'test_provider',
        'vnf_product_name': 'test_product_name',
        'vnf_software_version': 'test_version',
        'vnfd_version': 'test_vnfd_version',
    }


def vnf_pack_artifact_data(vnf_pack_id):
    return {
        'package_uuid': vnf_pack_id,
        'artifact_path': 'scripts/install.sh',
        'algorithm': 'sha-256',
        'hash': 'd0e7828293355a07c2dccaaa765c80b507e'
                '60e6167067c950dc2e6b0da0dbd8b',
        '_metadata': {}
    }


ip_address = [{
    'type': 'IPV4',
    'is_dynamic': True
}]

ip_over_ethernet_address_info = {
    'mac_address': 'fake_mac',
    'ip_addresses': ip_address,
}

cp_protocol_info = {
    'layer_protocol': 'IP_OVER_ETHERNET',
    'ip_over_ethernet': ip_over_ethernet_address_info,
}

vnf_external_cp_info = {
    'id': uuidsentinel.external_cp_id,
    'cpd_id': uuidsentinel.cpd_id,
    'ext_link_port_id': uuidsentinel.ext_link_port_id
}

resource_handle_info = {
    'resource_id': uuidsentinel.resource_id,
    'vim_level_resource_type': 'TEST'
}

ext_link_port_info = {
    'id': uuidsentinel.ext_link_port_id,
    'resource_handle': resource_handle_info,
    'cp_instance_id': uuidsentinel.cp_instance_id,
}

ext_virtual_link_info = {
    'id': uuidsentinel.virtual_link_id,
    'resource_handle': resource_handle_info,
    'ext_link_ports': [ext_link_port_info],
}

vnf_link_ports = {
    'id': uuidsentinel.vnf_link_ports_id,
    'resource_handle': resource_handle_info,
    'cp_instance_id': uuidsentinel.cp_instance_id
}

ext_managed_virtual_link_info = {
    'id': uuidsentinel.ext_managed_virtual_link_id,
    'vnf_virtual_link_desc_id': uuidsentinel.vnf_virtual_link_desc_id,
    'network_resource': resource_handle_info,
    'vnf_link_ports': [vnf_link_ports],
}

vnfc_resource_info = {
    'id': uuidsentinel.resource_info_id,
    'vdu_id': 'vdu1',
    'compute_resource': None,
    'storage_resource_ids': [uuidsentinel.id1, uuidsentinel.id2],
    'reservation_id': uuidsentinel.reservation_id,
    'vnfc_cp_info': None,
    'metadata': {'key': 'value'}

}

vnfc_cp_info = {
    'id': uuidsentinel.cp_instance_id,
    'cpd_id': uuidsentinel.cpd_id,
    'vnf_ext_cp_id': uuidsentinel.vnf_ext_cp_id,
    'cp_protocol_info': [cp_protocol_info],
    'vnf_link_port_id': uuidsentinel.vnf_link_port_id,
}

vnfc_resource_info = {
    'id': uuidsentinel.resource_info_id,
    'vdu_id': uuidsentinel.vdu_id,
    'compute_resource': resource_handle_info,
    'storage_resource_ids': [uuidsentinel.id1, uuidsentinel.id2],
    'reservation_id': uuidsentinel.reservation_id,
    'vnfc_cp_info': [vnfc_cp_info],
    'metadata': {'key': 'value'}
}

ip_address_info = {
    'type': 'IPV4',
    'subnet_id': uuidsentinel.subnet_id,
    'is_dynamic': False,
    'addresses': ['10.10.1', '10.10.2'],
}

vnf_virtual_link_resource_info = {
    'id': uuidsentinel.virtual_link_resource_id,
    'vnf_virtual_link_desc_id': uuidsentinel.vnf_virtual_link_desc_id,
    'network_resource': resource_handle_info,
    'vnf_link_ports': vnf_link_ports,
}

virtual_storage_resource_info = {
    'id': uuidsentinel.virtual_storage_resource_id,
    'virtual_storage_desc_id': uuidsentinel.virtual_storage_desc_id,
    'storage_resource': resource_handle_info,
}

vnf_ext_cp_info = {
    'id': uuidsentinel.id,
    'cpd_id': 'CP1',
    'cp_protocol_info': [cp_protocol_info],
    'associated_vnfc_cp_id': uuidsentinel.associated_vnfc_cp_id
}


def get_instantiated_vnf_info():
    instantiated_vnf_info = {
        'flavour_id': uuidsentinel.flavour_id,
        'vnf_state': 'STARTED',
        'instance_id': uuidsentinel.instance_id
    }
    return instantiated_vnf_info


instantiated_vnf_info = {
    'ext_cp_info': [vnf_ext_cp_info],
    'flavour_id': uuidsentinel.flavour_id,
    'vnf_state': 'STARTED',
    'vnf_instance_id': uuidsentinel.vnf_instance_id
}


def vnf_resource_model_object(vnf_resource):
    resource_dict = {
        'id': vnf_resource.id,
        'vnf_instance_id': vnf_resource.vnf_instance_id,
        'resource_name': vnf_resource.resource_name,
        'resource_type': vnf_resource.resource_type,
        'resource_identifier': vnf_resource.resource_identifier,
        'resource_status': vnf_resource.resource_status
    }

    vnf_resource_db_obj = models.VnfResource()
    vnf_resource_db_obj.update(resource_dict)
    return vnf_resource_db_obj


def vnf_instance_model_object(vnf_instance):
    instance_dict = {
        'id': vnf_instance.id,
        'vnf_instance_name': vnf_instance.vnf_instance_name,
        'vnf_instance_description': vnf_instance.vnf_instance_description,
        'instantiation_state': vnf_instance.instantiation_state,
        'task_state': vnf_instance.task_state,
        'vnfd_id': vnf_instance.vnfd_id,
        'vnf_provider': vnf_instance.vnf_provider,
        'vnf_product_name': vnf_instance.vnf_product_name,
        'vnf_software_version': vnf_instance.vnf_software_version,
        'vnfd_version': vnf_instance.vnfd_version,
        'vim_connection_info': vnf_instance.vim_connection_info,
        'tenant_id': vnf_instance.tenant_id,
        'created_at': vnf_instance.created_at,
        'vnf_pkg_id': vnf_instance.vnf_pkg_id,
        'vnf_metadata': vnf_instance.vnf_metadata,
    }

    vnf_instance_db_obj = models.VnfInstance()
    vnf_instance_db_obj.update(instance_dict)
    return vnf_instance_db_obj


def get_changed_info_data():
    return {
        "vnf_instance_name": "",
        "vnf_instance_description": "",
        "vnf_configurable_properties": {"test": "test_value"},
        "vnfc_info_modifications_delete_ids": ["test1"],
        "vnfd_id": "2c69a161-0000-4b0f-bcf8-391f8fc76600",
        "vnf_provider": "NEC",
        "vnf_product_name": "MME",
        "vnf_software_version": "1.0",
        "vnfd_version": "MME_1.0"
    }


def get_vnf(vnfd_id, vim_id):
    return {
        'tenant_id': uuidsentinel.tenant_id,
        'name': "test_name",
        'vnfd_id': vnfd_id,
        'mgmt_ip_address': "test_mgmt_ip_address",
        'status': "ACTIVE",
        'description': "test_description",
        'placement_attr': "test_placement_attr",
        'vim_id': vim_id
    }
