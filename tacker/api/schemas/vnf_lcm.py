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

"""
Schema for vnf lcm APIs.

"""

from tacker.api.validation import parameter_types
from tacker.objects import fields

_extManagedVirtualLinkData = {
    'type': 'array',
    'items': {
        'type': 'object',
        'properties': {
            'id': parameter_types.identifier,
            'vnfVirtualLinkDescId': parameter_types.identifier_in_vnfd,
            'resourceId': parameter_types.identifier_in_vim,
            'vimConnectionId': parameter_types.identifier
        },
        'required': ['id', 'vnfVirtualLinkDescId', 'resourceId'],
        'additionalProperties': True,
    },
}

_ipaddresses = {
    'type': 'array',
    'items': {
        'type': 'object',
        'properties': {
            'type': {'enum': fields.IpAddressType.ALL},
            'subnetId': parameter_types.identifier_in_vim,
            'fixedAddresses': {'type': 'array'}
        },
        'if': {'properties': {'type': {'const': fields.IpAddressType.IPV4}}},
        'then': {
            'properties': {
                'fixedAddresses': {
                    'type': 'array',
                    'items': {'type': 'string', 'format': 'ipv4'}
                }
            }
        },
        'else': {
            'properties': {
                'fixedAddresses': {
                    'type': 'array',
                    'items': {'type': 'string', 'format': 'ipv6'}
                }
            }
        },
        'required': ['type', 'fixedAddresses'],
        'additionalProperties': True
    }
}

_ipOverEthernetAddressData = {
    'type': 'object',
    'properties': {
        'macAddress': parameter_types.mac_address_or_none,
        'ipAddresses': _ipaddresses,
    },
    'anyOf': [
        {'required': ['macAddress']},
        {'required': ['ipAddresses']}
    ],
    'additionalProperties': True
}

_cpProtocolData = {
    'type': 'array',
    'items': {
        'type': 'object',
        'properties': {
            'layerProtocol': {'type': 'string',
                              'enum': 'IP_OVER_ETHERNET'
                              },
            'ipOverEthernet': _ipOverEthernetAddressData,
        },
        'required': ['layerProtocol'],
        'additionalProperties': True,
    }
}

_vnfExtCpConfig = {
    'type': 'array', 'minItems': 1, 'maxItems': 1,
    'items': {
        'type': 'object',
        'properties': {
            'cpInstanceId': parameter_types.identifier_in_vnf,
            'linkPortId': parameter_types.identifier,
            'cpProtocolData': _cpProtocolData,
        },
        'additionalProperties': True,
    }
}

_vnfExtCpData = {
    'type': 'array', 'minItems': 1,
    'items': {
        'type': 'object',
        'properties': {
            'cpdId': parameter_types.identifier_in_vnfd,
            'cpConfig': _vnfExtCpConfig,
        },
        'required': ['cpdId', 'cpConfig'],
        'additionalProperties': True,
    },
}

_resourceHandle = {
    'type': 'object',
    'properties': {
        'resourceId': parameter_types.identifier_in_vim,
        'vimConnectionId': parameter_types.identifier,
        'vimLevelResourceType': {'type': 'string', 'maxLength': 255},
    },
    'required': ['resourceId'],
    'additionalProperties': True,
}

_extLinkPortData = {
    'type': 'array',
    'items': {
        'type': 'object',
        'properties': {
            'id': parameter_types.identifier,
            'resourceHandle': _resourceHandle,
        },
        'required': ['id', 'resourceHandle'],
        'additionalProperties': True,
    }
}

_extVirtualLinkData = {
    'type': 'array',
    'items': {
        'type': 'object',
        'properties': {
            'id': parameter_types.identifier,
            'resourceId': parameter_types.identifier_in_vim,
            'vimConnectionId': parameter_types.identifier,
            'extCps': _vnfExtCpData,
            'extLinkPorts': _extLinkPortData,

        },
        'required': ['id', 'resourceId', 'extCps'],
        'additionalProperties': True,
    }
}

_vimConnectionInfo = {
    'type': 'array',
    'maxItems': 1,
    'items': {
        'type': 'object',
        'properties': {
            'id': parameter_types.identifier,
            'vimId': parameter_types.identifier,
            'vimType': {'type': 'string', 'minLength': 1, 'maxLength': 255},
            'accessInfo': parameter_types.keyvalue_pairs,
        },
        'required': ['id', 'vimType'],
        'additionalProperties': True,
    }
}

create = {
    'type': 'object',
    'properties': {
        'vnfdId': parameter_types.uuid,
        'vnfInstanceName': parameter_types.name_allow_zero_min_length,
        'vnfInstanceDescription': parameter_types.description,
        'metadata': parameter_types.keyvalue_pairs,
    },
    'required': ['vnfdId'],
    'additionalProperties': True,
}

instantiate = {
    'type': 'object',
    'properties': {
        'flavourId': {'type': 'string', 'maxLength': 255},
        'instantiationLevelId': {'type': 'string', 'maxLength': 255},
        'extVirtualLinks': _extVirtualLinkData,
        'extManagedVirtualLinks': _extManagedVirtualLinkData,
        'vimConnectionInfo': _vimConnectionInfo,
        'additionalParams': parameter_types.keyvalue_pairs,
    },
    'required': ['flavourId'],
    'additionalProperties': True,
}

terminate = {
    'type': 'object',
    'properties': {
        'terminationType': {'type': 'string',
                            'enum': ['FORCEFUL', 'GRACEFUL']},
        'gracefulTerminationTimeout': {'type': 'integer', 'minimum': 0},
        'additionalParams': parameter_types.keyvalue_pairs,
    },
    'required': ['terminationType'],
    'additionalProperties': True,
}

heal = {
    'type': 'object',
    'properties': {
        'cause': {'type': 'string', 'maxLength': 255},
        'vnfcInstanceId': {
            'type': 'array',
            "items": {
                "type": "string",
                'format': 'uuid'
            }
        }

    },
    'additionalProperties': True,
}

register_subscription = {
    'type': 'object',
    'properties': {
        'filter': parameter_types.keyvalue_pairs,
        'callbackUri': {'type': 'string', 'maxLength': 255},
        'authentication': parameter_types.keyvalue_pairs,
    },
    'required': ['callbackUri'],
    'additionalProperties': True,
}

update = {
    'type': 'object',
    'properties': {
        'vnfdId': parameter_types.uuid,
        'vnfInstanceName': parameter_types.name_allow_zero_min_length,
        'vnfInstanceDescription': parameter_types.description,
        'vnfPkgId': parameter_types.uuid,
        'metadata': parameter_types.keyvalue_pairs,
        'vimConnectionInfo': _vimConnectionInfo,
    },
    'additionalProperties': True,
}

scale = {
    'type': 'object',
    'properties': {
        'type': {'type': 'string',
                 'enum': ['SCALE_OUT', 'SCALE_IN']},
        'aspectId': {'type': 'string'},
        'numberOfSteps': {'type': 'integer'},
        'additionalParams': parameter_types.keyvalue_pairs
    },
    'required': ['type', 'aspectId'],
    'additionalProperties': True,
}
