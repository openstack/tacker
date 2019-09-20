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

from tacker.tests import uuidsentinel


VNF_UPLOAD_VNF_PACKAGE_CONTENT = {
    'algorithm': 'sha512', 'created_at': '2019-08-16T06:57:09Z',
    'deleted': False, 'deleted_at': None,
    'hash': 'ce48b8ba15bfb060fb70471cf955bef433e4513973b4bac42b37c36f57357dc35'
            'bf788c16545d3a59781914adf19fca26d6984583b7739e55c447383d774356a',
    'id': uuidsentinel.tenant_id,
    'location_glance_store': 'file:///var/lib/glance/images/'
                             'd617ea52-b16b-417e-a68c-08dfb69aab9e',
    'onboarding_state': 'PROCESSING', 'operational_state': 'DISABLED',
    'tenant_id': uuidsentinel.tenant_id,
    'updated_at': '2019-08-16T06:57:30Z',
    'usage_state': 'NOT_IN_USE', 'user_data': {'abc': 'xyz'}}

VNF_DATA = {
    'created_at': '2019-08-16T06:57:09Z',
    'deleted': False, 'deleted_at': None,
    'id': uuidsentinel.id,
    'onboarding_state': 'UPLOADING',
    'operational_state': 'DISABLED',
    'tenant_id': uuidsentinel.tenant_id,
    'updated_at': '2019-08-16T06:57:30Z',
    'usage_state': 'NOT_IN_USE',
    'user_data': {'abc': 'xyz'}
}

VNF_PACKAGE_DATA = {'algorithm': None, 'hash': None,
                    'location_glance_store': None,
                    'onboarding_state': 'CREATED',
                    'operational_state': 'DISABLED',
                    'tenant_id': uuidsentinel.tenant_id,
                    'usage_state': 'NOT_IN_USE',
                    'user_data': {'abc': 'xyz'}
                    }
