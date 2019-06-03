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

artifacts = {
    'json_data': 'test data',
    'type': 'tosca.artifacts.nfv.SwImage',
    'algorithm': 'sha512', 'hash': uuidsentinel.hash}

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
