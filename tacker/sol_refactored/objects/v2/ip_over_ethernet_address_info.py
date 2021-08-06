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

from tacker.sol_refactored.objects import base
from tacker.sol_refactored.objects import fields


# NFV-SOL 003
# - v3.3.1 5.5.3.10 (API version: 2.0.0)
@base.TackerObjectRegistry.register
class IpOverEthernetAddressInfoV2(base.TackerObject,
                                  base.TackerObjectDictCompat):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'macAddress': fields.MACAddressField(nullable=True),
        'segmentationId': fields.StringField(nullable=True),
        'ipAddresses': fields.ListOfObjectsField(
            'IpOverEthernetAddressInfoV2_IpAddresses', nullable=True),
    }


@base.TackerObjectRegistry.register
class IpOverEthernetAddressInfoV2_IpAddresses(
        base.TackerObject, base.TackerObjectDictCompat):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'type': fields.EnumField(
            valid_values=['IPV4', 'IPV6'], nullable=False),
        'addresses': fields.ListOfIPAddressesField(nullable=True),
        'isDynamic': fields.BooleanField(nullable=True),
        'addressRange': fields.ObjectField(
            'IpOverEthernetAddressInfoV2_IpAddresses_AddressRange',
            nullable=True),
        'subnetId': fields.StringField(nullable=True),
    }


@base.TackerObjectRegistry.register
class IpOverEthernetAddressInfoV2_IpAddresses_AddressRange(
        base.TackerObject, base.TackerObjectDictCompat):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'minAddress': fields.IPAddressField(nullable=False),
        'maxAddress': fields.IPAddressField(nullable=False),
    }
