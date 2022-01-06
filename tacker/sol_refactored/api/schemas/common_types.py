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


# SOL013 7.2.2
Identifier = {
    'type': 'string', 'minLength': 1, 'maxLength': 255
}

# SOL003 4.4.2.2
IdentifierInVnfd = {
    'type': 'string', 'minLength': 1, 'maxLength': 255
}

# SOL003 4.4.2.2
IdentifierInVim = {
    'type': 'string', 'minLength': 1, 'maxLength': 255
}

# SOL003 4.4.2.2
IdentifierInVnf = {
    'type': 'string', 'minLength': 1, 'maxLength': 255
}

# SOL003 4.4.2.2
IdentifierLocal = {
    'type': 'string', 'minLength': 1, 'maxLength': 255
}

# SOL003 4.4.1.7
ResourceHandle = {
    'type': 'object',
    'properties': {
        'vimConnectionId': Identifier,
        'resourceProviderId': Identifier,
        'resourceId': IdentifierInVim,
        'vimLevelResourceType': {'type': 'string', 'maxLength': 255},
    },
    'required': ['resourceId'],
    'additionalProperties': True,
}

# SOL003 4.4.1.6
VimConnectionInfo = {
    'type': 'object',
    'properties': {
        'vimId': {'type': 'string', 'maxLength': 255},
        'vimType': {'type': 'string', 'minLength': 1, 'maxLength': 255},
        'interfaceInfo': parameter_types.keyvalue_pairs,
        'accessInfo': parameter_types.keyvalue_pairs,
        'extra': parameter_types.keyvalue_pairs,
    },
    'required': ['vimType'],
    'additionalProperties': True,
}

# SOL003 4.4.1.10c (inner)
_IpAddresses = {
    'type': 'object',
    'properties': {
        'type': {'enum': ('IPV4', 'IPV6')},
        'fixedAddresses': {'type': 'array'},
        'numDynamicAddresses': parameter_types.positive_integer,
        'addressRange': {'type': 'object'},
        'subnetId': IdentifierInVim
    },
    'if': {'properties': {'type': {'const': 'IPV4'}}},
    'then': {
        'properties': {
            'fixedAddresses': {
                'type': 'array',
                'items': {'type': 'string', 'format': 'ipv4'}
            },
            'addressRange': {
                'type': 'object',
                'properties': {
                    'minAddress': {'type': 'string', 'format': 'ipv4'},
                    'maxAddress': {'type': 'string', 'format': 'ipv4'}
                },
                'required': ['minAddress', 'maxAddress'],
                'additionalProperties': True
            },
        }
    },
    'else': {
        'properties': {
            'fixedAddresses': {
                'type': 'array',
                'items': {'type': 'string', 'format': 'ipv6'}
            },
            'addressRange': {
                'type': 'object',
                'properties': {
                    'minAddress': {'type': 'string', 'format': 'ipv6'},
                    'maxAddress': {'type': 'string', 'format': 'ipv6'}
                },
                'required': ['minAddress', 'maxAddress'],
                'additionalProperties': True
            },
        }
    },
    'required': ['type'],
    'oneOf': [
        {'required': ['numDynamicAddresses']},
        {'required': ['fixedAddresses']},
        {'required': ['addressRange']},
    ],
    'additionalProperties': True
}

# SOL003 4.4.1.10c
IpOverEthernetAddressData = {
    'type': 'object',
    'properties': {
        'macAddress': {'type': 'string', 'format': 'mac_address'},
        'segmentationId': {'type': 'string'},
        'ipAddresses': {
            'type': 'array',
            'items': _IpAddresses}
    },
    'anyOf': [
        {'required': ['macAddress']},
        {'required': ['ipAddresses']}
    ],
    'additionalProperties': True
}

# SOL003 4.4.1.10b
CpProtocolData = {
    'type': 'object',
    'properties': {
        'layerProtocol': {
            'type': 'string',
            'enum': 'IP_OVER_ETHERNET'},
        'ipOverEthernet': IpOverEthernetAddressData,
    },
    'required': ['layerProtocol'],
    'additionalProperties': True,
}

# SOL003 4.4.1.10a
VnfExtCpConfig = {
    'type': 'object',
    'properties': {
        'parentCpConfigId': IdentifierInVnf,
        'linkPortId': Identifier,
        'cpProtocolData': {
            'type': 'array',
            'items': CpProtocolData}
    },
    'additionalProperties': True
}

# SOL003 4.4.1.10
VnfExtCpData = {
    'type': 'object',
    'properties': {
        'cpdId': IdentifierInVnfd,
        'cpConfig': {
            'type': 'object',
            'minProperties': 1,
            'patternProperties': {
                '^.*$': VnfExtCpConfig
            }
        }
    },
    'required': ['cpdId', 'cpConfig'],
    'additionalProperties': True
}

# SOL003 4.4.1.14
ExtLinkPortData = {
    'type': 'object',
    'properties': {
        'id': Identifier,
        'resourceHandle': ResourceHandle,
    },
    'required': ['id', 'resourceHandle'],
    'additionalProperties': True,
}

# SOL003 4.4.1.11
ExtVirtualLinkData = {
    'type': 'object',
    'properties': {
        'id': Identifier,
        'vimConnectionId': Identifier,
        'resourceProviderId': Identifier,
        'resourceId': IdentifierInVim,
        'extCps': {
            'type': 'array',
            'minItems': 1,
            'items': VnfExtCpData},
        'extLinkPorts': {
            'type': 'array',
            'items': ExtLinkPortData}
    },
    'required': ['id', 'resourceId', 'extCps'],
    'additionalProperties': True
}

# SOL003 5.5.3.18
VnfLinkPortData = {
    'type': 'object',
    'properties': {
        'vnfLinkPortId': Identifier,
        'resourceHandle': ResourceHandle
    },
    'required': ['vnfLinkPortId', 'resourceHandle'],
    'additionalProperties': True,
}

# SOL003 4.4.1.12
ExtManagedVirtualLinkData = {
    'type': 'object',
    'properties': {
        'id': Identifier,
        'vnfVirtualLinkDescId': IdentifierInVnfd,
        'vimConnectionId': Identifier,
        'resourceProviderId': Identifier,
        'resourceId': IdentifierInVim,
        'vnfLinkPort': {
            'type': 'array',
            'items': VnfLinkPortData},
        'extManagedMultisiteVirtualLinkId': Identifier
    },
    'required': ['id', 'vnfVirtualLinkDescId', 'resourceId'],
    'additionalProperties': True,
}

# SOL002 5.5.3.24
VnfcInfoModifications = {
    'type': 'object',
    'properties': {
        'id': IdentifierInVnf,
        'vnfcConfigurableProperties': parameter_types.keyvalue_pairs,
    },
    'required': ['id', 'vnfcConfigurableProperties'],
    'additionalProperties': True,
}
