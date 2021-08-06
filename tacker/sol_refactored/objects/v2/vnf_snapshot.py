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
# - v3.3.1 5.5.2.23 (API version: 2.0.0)
@base.TackerObjectRegistry.register
class VnfSnapshotV2(base.TackerObject, base.TackerObjectDictCompat):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.StringField(nullable=False),
        'vnfInstanceId': fields.StringField(nullable=False),
        'creationStartedAt': fields.DateTimeField(nullable=False),
        'creationFinishedAt': fields.DateTimeField(nullable=True),
        'vnfdId': fields.StringField(nullable=False),
        'vnfInstance': fields.ObjectField(
            'VnfInstanceV2', nullable=False),
        'vnfcSnapshots': fields.ListOfObjectsField(
            'VnfcSnapshotInfoV2', nullable=False),
        'vnfStateSnapshotInfo': fields.ObjectField(
            'VnfStateSnapshotInfoV2', nullable=True),
        'userDefinedData': fields.KeyValuePairsField(nullable=True),
        '_links': fields.ObjectField('VnfSnapshotV2_Links', nullable=False),
    }


@base.TackerObjectRegistry.register
class VnfSnapshotV2_Links(base.TackerObject):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'self': fields.ObjectField('Link', nullable=False),
        'vnfStateSnapshot': fields.ObjectField('Link', nullable=True),
    }
