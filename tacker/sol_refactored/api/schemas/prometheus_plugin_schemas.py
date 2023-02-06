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


Alert = {
    'type': 'object',
    'status': {
        'type': 'string',
        'enum': ['firing', 'resolved']
    },
    'properties': {
        'status': {
            'type': 'string',
            'enum': ['firing', 'resolved']
        },
        'labels': {
            'type': 'object',
            'properties': {
                'receiver_type': {
                    'type': 'string',
                    'enum': ['tacker']
                },
                'function_type': {
                    'type': 'string',
                    'enum': ['vnffm', 'vnfpm', 'vnfpm_threshold',
                             'auto_scale', 'auto_heal']
                },
                'job_id': {'type': 'string'},
                'threshold_id': {'type': 'string'},
                'metric': {'type': 'string'},
                'object_instance_id': {'type': 'string'},
                'vnf_instance_id': {'type': 'string'},
                'vnfc_info_id': {'type': 'string'},
                'node': {'type': 'string'},
                'perceived_severity': {
                    'type': 'string',
                    'enum': ['CRITICAL', 'MAJOR', 'MINOR', 'WARNING',
                             'INDETERMINATE', 'CLEARED']
                },
                'event_type': {'type': 'string'},
                'auto_scale_type': {
                    'type': 'string',
                    'enum': ['SCALE_OUT', 'SCALE_IN']
                },
                'aspect_id': {'type': 'string'}
            },
            'required': ['receiver_type', 'function_type'],
            'additionalProperties': True
        },
        'annotations': {
            'type': 'object',
            'properties': {
                'value': {'type': ['number', 'string']},
                'probable_cause': {'type': 'string'},
                'fault_type': {'type': 'string'},
                'fault_details': {'type': 'string'}
            },
            'required': [],
            'additionalProperties': True
        },
        'startsAt': {'type': 'string'},
        'endsAt': {'type': 'string'},
        'fingerprint': {'type': 'string'}
    },
    'required': ['status', 'labels', 'annotations', 'startsAt',
                 'fingerprint'],
    'additionalProperties': True
}

AlertMessage = {
    'type': 'object',
    'properties': {
        'alerts': {
            'type': 'array',
            'items': Alert
        }
    },
    'required': ['alerts']
}
