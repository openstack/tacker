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
# - v3.3.1 5.5.3.5 (API version: 2.0.0)
@base.TackerObjectRegistry.register
class VnfcResourceInfoV2(base.TackerObject,
                         base.TackerObjectDictCompat):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.StringField(nullable=False),
        'vduId': fields.StringField(nullable=False),
        'vnfdId': fields.StringField(nullable=True),
        'computeResource': fields.ObjectField(
            'ResourceHandle', nullable=False),
        'zoneId': fields.StringField(nullable=True),
        'storageResourceIds': fields.ListOfStringsField(nullable=True),
        'reservationId': fields.StringField(nullable=True),
        'vnfcCpInfo': fields.ListOfObjectsField(
            'VnfcResourceInfoV2_VnfcCpInfo', nullable=True),
        'metadata': fields.KeyValuePairsField(nullable=True),
    }


@base.TackerObjectRegistry.register
class VnfcResourceInfoV2_VnfcCpInfo(base.TackerObject,
                                    base.TackerObjectDictCompat):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.StringField(nullable=False),
        'cpdId': fields.StringField(nullable=False),
        'vnfExtCpId': fields.StringField(nullable=True),
        'cpProtocolInfo': fields.ListOfObjectsField(
            'CpProtocolInfoV2', nullable=True),
        'vnfLinkPortId': fields.StringField(nullable=True),
        'metadata': fields.KeyValuePairsField(nullable=True),
    }
