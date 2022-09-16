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


# SOL003 7.5.2.8
AlarmModifications_V130 = {
    'type': 'object',
    'properties': {
        'ackState': {
            'type': 'string',
            'enum': ['ACKNOWLEDGED', 'UNACKNOWLEDGED']
        }
    },
    'required': ['ackState'],
    'additionalProperties': True,
}

# SOL003 4.4.1.5 inner
_VnfProductVersions = {
    'type': 'array',
    'items': {
        'type': 'objects',
        'properties': {
            'vnfSoftwareVersion': {'type': 'string'},
            'vnfdVersions': {
                'type': 'array',
                'items': {'type': 'string'}
            }
        },
        'required': ['vnfSoftwareVersion'],
        'additionalProperties': True,
    }
}

# SOL003 4.4.1.5 inner
_VnfProducts = {
    'type': 'array',
    'items': {
        'type': 'object',
        'properties': {
            'vnfProductName': {'type': 'string'},
            'versions': _VnfProductVersions
        },
        'required': ['vnfProductName'],
        'additionalProperties': True,
    }
}

# SOL003 4.4.1.5 inner
_VnfProductsFromProviders = {
    'type': 'array',
    'items': {
        'type': 'object',
        'properties': {
            'type': 'object',
            'properties': {
                'vnfProvider': {'type': 'string'},
                'vnfProducts': _VnfProducts
            }
        },
        'required': ['vnfProvider'],
        'additionalProperties': True,
    }
}

# SOL003 4.4.1.5
_VnfInstanceSubscriptionFilter = {
    'type': 'object',
    'properties': {
        'vnfdIds': {
            'type': 'array',
            'items': common_types.Identifier
        },
        'vnfProductsFromProviders': _VnfProductsFromProviders,
        'vnfInstanceIds': {
            'type': 'array',
            'items': common_types.Identifier
        },
        'vnfInstanceNames': {
            'type': 'array',
            'items': {'type': 'string'}
        }
    },
    'additionalProperties': True,
}

# SOL003 7.5.3.2
_FmNotificationsFilter = {
    'type': 'object',
    'properties': {
        'vnfInstanceSubscriptionFilter': _VnfInstanceSubscriptionFilter,
        'notificationTypes': {
            'type': 'array',
            'items': {
                'type': 'string',
                'enum': [
                    'AlarmNotification',
                    'AlarmClearedNotification',
                    'AlarmListRebuiltNotification']
            }
        },
        'faultyResourceTypes': {
            'type': 'array',
            'items': {
                'type': 'string',
                'enum': [
                    'COMPUTE',
                    'STORAGE',
                    'NETWORK']
            }
        },
        'perceivedSeverities': {
            'type': 'array',
            'items': {
                'type': 'string',
                'enum': [
                    'CRITICAL',
                    'MAJOR',
                    'MINOR',
                    'WARNING',
                    'INDETERMINATE',
                    'CLEARED']
            }
        },
        'eventTypes': {
            'type': 'array',
            'items': {
                'type': 'string',
                'enum': [
                    'COMMUNICATIONS_ALARM',
                    'PROCESSING_ERROR_ALARM',
                    'ENVIRONMENTAL_ALARM',
                    'QOS_ALARM',
                    'EQUIPMENT_ALARM']
            }
        },
        'probableCauses': {
            'type': 'array',
            'items': {'type': 'string'}
        }
    },
    'additionalProperties': True,
}

# SOL003 7.5.2.2
FmSubscriptionRequest_V130 = {
    'type': 'object',
    'properties': {
        'filter': _FmNotificationsFilter,
        'callbackUri': {'type': 'string', 'maxLength': 255},
        'authentication': common_types.SubscriptionAuthentication,
        'verbosity': {
            'type': 'string',
            'enum': ['FULL', 'SHORT']
        }
    },
    'required': ['callbackUri'],
    'additionalProperties': True,
}
