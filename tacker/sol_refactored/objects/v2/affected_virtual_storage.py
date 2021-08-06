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
# - v3.3.1 5.5.3.15 (API version: 2.0.0)
@base.TackerObjectRegistry.register
class AffectedVirtualStorageV2(base.TackerObject, base.TackerObjectDictCompat):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.StringField(nullable=False),
        'virtualStorageDescId': fields.StringField(nullable=False),
        'vnfdId': fields.StringField(nullable=True),
        'changeType': fields.EnumField(
            valid_values=[
                'ADDED',
                'REMOVED',
                'MODIFIED',
                'TEMPORARY',
            ],
            nullable=False,
        ),
        'storageResource': fields.ObjectField(
            'ResourceHandle', nullable=False),
        'resourceDefinitionId': fields.StringField(nullable=True),
        'zoneId': fields.StringField(nullable=True),
        'metadata': fields.KeyValuePairsField(nullable=True),
    }
