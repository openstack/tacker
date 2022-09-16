# Copyright (C) 2022 Fujitsu
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

from tacker.sol_refactored.api.schemas import common_types


ServerNotification = {
    'type': 'object',
    'properties': {
        'notification': {
            'type': 'object',
            'properties': {
                'host_id': common_types.Identifier,
                'alarm_id': common_types.Identifier,
                'fault_id': {
                    'type': 'string',
                    "minLength": 4,
                    "maxLength": 4
                },
                'fault_type': {
                    'type': 'string',
                    "minLength": 2,
                    "maxLength": 2
                },
                'fault_option': {'type': 'object'}
            },
            'required': ['alarm_id', 'fault_id', 'fault_type'],
            'additionalProperties': True
        }
    },
    'required': ['notification']
}
