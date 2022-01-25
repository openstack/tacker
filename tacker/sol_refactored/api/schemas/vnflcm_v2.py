# Copyright (C) 2021 Nippon Telegraph and Telephone Corporation
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

from tacker.api.validation import parameter_types

from tacker.sol_refactored.api.schemas import common_types


# SOL003 5.5.2.3
CreateVnfRequest_V200 = {
    'type': 'object',
    'properties': {
        'vnfdId': common_types.Identifier,
        'vnfInstanceName': {'type': 'string', 'maxLength': 255},
        'vnfInstanceDescription': {'type': 'string', 'maxLength': 1024},
        'metadata': parameter_types.keyvalue_pairs,
    },
    'required': ['vnfdId'],
    'additionalProperties': True,
}

# SOL003 5.5.2.4
InstantiateVnfRequest_V200 = {
    'type': 'object',
    'properties': {
        'flavourId': common_types.IdentifierInVnfd,
        'instantiationLevelId': common_types.IdentifierInVnfd,
        'extVirtualLinks': {
            'type': 'array',
            'items': common_types.ExtVirtualLinkData},
        'extManagedVirtualLinks': {
            'type': 'array',
            'items': common_types.ExtManagedVirtualLinkData},
        'vimConnectionInfo': {
            'type': 'object',
            'patternProperties': {
                '^.*$': common_types.VimConnectionInfo
            },
        },
        'localizationLanguage': {'type': 'string', 'maxLength': 255},
        'additionalParams': parameter_types.keyvalue_pairs,
        'extensions': parameter_types.keyvalue_pairs,
        'vnfConfigurableProperties': parameter_types.keyvalue_pairs
    },
    'required': ['flavourId'],
    'additionalProperties': True,
}

# SOL003 5.5.2.8
TerminateVnfRequest_V200 = {
    'type': 'object',
    'properties': {
        'terminationType': {
            'type': 'string',
            'enum': [
                'FORCEFUL',
                'GRACEFUL']
        },
        'gracefulTerminationTimeout': {
            'type': 'integer', 'minimum': 1
        },
        'additionalParams': parameter_types.keyvalue_pairs,
    },
    'required': ['terminationType'],
    'additionalProperties': True,
}

# SOL002 5.5.2.11a
# SOL003 5.5.2.11a
ChangeCurrentVnfPkgRequest_V200 = {
    'type': 'object',
    'properties': {
        'vnfdId': common_types.Identifier,
        'extVirtualLinks': {
            'type': 'array',
            'items': common_types.ExtVirtualLinkData},
        'extManagedVirtualLinks': {
            'type': 'array',
            'items': common_types.ExtManagedVirtualLinkData},
        # NOTE: 'vimConnectionInfo' field supports only NFV-SOL 003
        'vimConnectionInfo': {
            'type': 'object',
            'patternProperties': {
                '^.*$': common_types.VimConnectionInfo
            },
        },
        'additionalParams': parameter_types.keyvalue_pairs,
        'extensions': parameter_types.keyvalue_pairs,
        'vnfConfigurableProperties': parameter_types.keyvalue_pairs
    },
    'required': ['vnfdId'],
    'additionalProperties': True,
}

# SOL003 5.5.2.5
ScaleVnfRequest_V200 = {
    'type': 'object',
    'properties': {
        'type': {
            'type': 'string',
            'enum': ['SCALE_OUT', 'SCALE_IN']
        },
        'aspectId': common_types.IdentifierInVnfd,
        'numberOfSteps': {'type': 'integer', 'minimum': 1},
        'additionalParams': parameter_types.keyvalue_pairs,
    },
    'required': ['type', 'aspectId'],
    'additionalProperties': True,
}

# SOL002 5.5.2.9
# SOL003 5.5.2.9
HealVnfRequest_V200 = {
    'type': 'object',
    'properties': {
        'cause': {'type': 'string', 'maxLength': 255},
        'additionalParams': parameter_types.keyvalue_pairs,
        # NOTE: following fields support only NFV-SOL 002
        'vnfcInstanceId': {
            'type': 'array',
            'items': common_types.Identifier
        },
        'healScript': {'type': 'string', 'maxLength': 255},
    },
    'additionalProperties': True,
}

# SOL003 5.5.2.11
ChangeExtVnfConnectivityRequest_V200 = {
    'type': 'object',
    'properties': {
        'extVirtualLinks': {
            'type': 'array',
            'items': common_types.ExtVirtualLinkData
        },
        'vimConnectionInfo': {
            'type': 'object',
            'patternProperties': {
                '^.*$': common_types.VimConnectionInfo
            },
        },
        'additionalParams': parameter_types.keyvalue_pairs,
    },
    'required': ['extVirtualLinks'],
    'additionalProperties': True,
}

# SOL013 8.3.4
_SubscriptionAuthentication = {
    'type': 'object',
    'properties': {
        'authType': {
            'type': 'array',
            'items': {
                'type': 'string',
                'enum': [
                    'BASIC',
                    'OAUTH2_CLIENT_CREDENTIALS',
                    'TLS_CERT']
            }
        },
        'paramsBasic': {
            'type': 'object',
            'properties': {
                'userName': {'type': 'string'},
                'password': {'type': 'string'}
            },
            # NOTE: must be specified since the way to specify them out of
            # band is not supported.
            'required': ['userName', 'password']
        },
        'paramsOauth2ClientCredentials': {
            'type': 'object',
            'properties': {
                'clientId': {'type': 'string'},
                'clientPassword': {'type': 'string'},
                'tokenEndpoint': {'type': 'string'}
            },
            # NOTE: must be specified since the way to specify them out of
            # band is not supported.
            'required': ['clientId', 'clientPassword', 'tokenEndpoint']
        }
    },
    'required': ['authType'],
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

# SOL003 5.5.3.12
_LifecycleChangeNotificationsFilter = {
    'type': 'object',
    'properties': {
        'vnfInstanceSubscriptionFilter': _VnfInstanceSubscriptionFilter,
        'notificationTypes': {
            'type': 'array',
            'items': {
                'type': 'string',
                'enum': [
                    'VnfLcmOperationOccurrenceNotification',
                    'VnfIdentifierCreationNotification',
                    'VnfIdentifierDeletionNotification']
            }
        },
        'operationTypes': {
            'type': 'array',
            'items': {
                'type': 'string',
                'enum': [
                    'INSTANTIATE',
                    'SCALE',
                    'SCALE_TO_LEVEL',
                    'CHANGE_FLAVOUR',
                    'CHANGE_VNFPKG',
                    'TERMINATE',
                    'HEAL',
                    'OPERATE',
                    'CHANGE_EXT_CONN',
                    'MODIFY_INFO']
            }
        },
        'operationStates': {
            'type': 'array',
            'items': {
                'type': 'string',
                'enum': [
                    'STARTING',
                    'PROCESSING',
                    'COMPLETED',
                    'FAILED_TEMP',
                    'FAILED',
                    'ROLLING_BACK',
                    'ROLLED_BACK']
            }
        }
    },
    'additionalProperties': True,
}

# SOL003 5.5.2.15
LccnSubscriptionRequest_V200 = {
    'type': 'object',
    'properties': {
        'filter': _LifecycleChangeNotificationsFilter,
        'callbackUri': {'type': 'string', 'maxLength': 255},
        'authentication': _SubscriptionAuthentication,
        'verbosity': {
            'type': 'string',
            'enum': ['FULL', 'SHORT']
        }
    },
    'required': ['callbackUri'],
    'additionalProperties': True,
}

# SOL003 5.5.2.12
VnfInfoModificationRequest_V200 = {
    'type': 'object',
    'properties': {
        'vnfInstanceName': {'type': 'string', 'maxLength': 255},
        'vnfInstanceDescription': {'type': 'string', 'maxLength': 1024},
        'vnfdId': common_types.Identifier,
        'vnfConfigurableProperties': parameter_types.keyvalue_pairs,
        'metadata': parameter_types.keyvalue_pairs,
        'extensions': parameter_types.keyvalue_pairs,
        'vimConnectionInfo': {
            'type': 'object',
            'patternProperties': {
                '^.*$': common_types.VimConnectionInfo
            },
        },
        'vnfcInfoModifications': {
            'type': 'array',
            'items': common_types.VnfcInfoModifications
        },
    },
    'additionalProperties': True,
}
