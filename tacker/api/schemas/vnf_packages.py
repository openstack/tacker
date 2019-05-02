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

"""
Schema for vnf packages create API.

"""

from tacker.api.validation import parameter_types

create = {
    'type': 'object',
    'properties': {
        'userDefinedData': parameter_types.keyvalue_pairs
    },
    'additionalProperties': False,
}

upload_from_uri = {
    'type': 'object',
    'properties': {
        'addressInformation': {
            'type': 'string', 'minLength': 0,
            'maxLength': 2048, 'format': 'uri'
        },
        'userName': {
            'type': 'string', 'maxLength': 255,
            'pattern': '^[a-zA-Z0-9-_]*$'
        },
        'password': {
            # Allow to specify any string for strong password.
            'type': 'string', 'maxLength': 255,
        },

    },
    'required': ['addressInformation'],
    'additionalProperties': False,
}
