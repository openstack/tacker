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

# SOL003 6.5.3.3
_PmJobCriteria_V210 = {
    'type': 'object',
    'properties': {
        'performanceMetric': {
            'type': 'array',
            'items': {'type:': 'string'}
        },
        'performanceMetricGroup': {
            'type': 'array',
            'items': {'type:': 'string'}
        },
        'collectionPeriod': {'type': 'integer'},
        'reportingPeriod': {'type': 'integer'},
        'reportingBoundary': {'type': 'string'}
    },
    'anyOf': [
        {'required': ['performanceMetric']},
        {'required': ['performanceMetricGroup']}
    ],
    'required': ['collectionPeriod', 'reportingPeriod'],
    'additionalProperties': True,
}

# SOL003 6.5.2.6
CreatePmJobRequest_V210 = {
    'type': 'object',
    'properties': {
        'objectType': {
            'type': 'string',
            'enum': [
                # TODO(YiFeng): Currently, this API only supports CNF, and
                # supports the following types. When VNF is supported,
                # the types can be extended.
                'Vnf',
                'Vnfc',
                'VnfIntCp',
                'VnfExtCp']
        },
        'objectInstanceIds': {
            'type': 'array',
            'items': common_types.Identifier
        },
        'subObjectInstanceIds': {
            'type': 'array',
            'items': common_types.IdentifierInVnf
        },
        'criteria': _PmJobCriteria_V210,
        'callbackUri': {'type': 'string'},
        'authentication': common_types.SubscriptionAuthentication,
    },
    'required': ['objectType', 'objectInstanceIds', 'criteria', 'callbackUri'],
    'additionalProperties': True,
}

# SOL003 6.5.2.12
PmJobModificationsRequest_V210 = {
    'type': 'object',
    'properties': {
        'callbackUri': {'type': 'string'},
        'authentication': common_types.SubscriptionAuthentication
    },
    'anyOf': [
        {'required': ['callbackUri']},
        {'required': ['authentication']}
    ],
    'required': [],
    'additionalProperties': True,
}

# SOL003 6.5.3.4
ThresholdCriteria_V210 = {
    'type': 'object',
    'properties': {
        'performanceMetric': {'type': 'string'},
        'thresholdType': {
            'type': 'string',
            'enum': ['SIMPLE']
        },
        'simpleThresholdDetails': {
            'type': 'object',
            'properties': {
                'thresholdValue': {'type': 'number'},
                'hysteresis': {'type': 'number', 'minimum': 0.0},
            },
            'required': ['thresholdValue', 'hysteresis'],
            'additionalProperties': True
        },
    },
    'required': ['performanceMetric', 'thresholdType'],
    'additionalProperties': True,
}

# SOL003 6.5.2.8
CreateThresholdRequest_V210 = {
    'type': 'object',
    'properties': {
        'objectType': {
            'type': 'string',
            'enum': [
                # TODO(YiFeng): Currently, this API only supports CNF, and
                # supports the following types. When VNF is supported,
                # the types can be extended.
                'Vnf',
                'Vnfc',
                'VnfIntCp',
                'VnfExtCp']
        },
        'objectInstanceId': {
            'type': 'string',
        },
        'subObjectInstanceIds': {
            'type': 'array',
            'items': common_types.IdentifierInVnf
        },
        'criteria': ThresholdCriteria_V210,
        'callbackUri': {'type': 'string'},
        'authentication': common_types.SubscriptionAuthentication,
    },
    'required': ['objectType', 'objectInstanceId', 'criteria', 'callbackUri'],
    'additionalProperties': True,
}

# SOL003 6.5.2.11
ThresholdModifications_V210 = {
    'type': 'object',
    'properties': {
        'callbackUri': {'type': 'string'},
        'authentication': common_types.SubscriptionAuthentication
    },
    'anyOf': [
        {'required': ['callbackUri']},
        {'required': ['authentication']}
    ],
    'required': [],
    'additionalProperties': True,
}
