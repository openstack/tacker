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
# - v2.6.1 9.5.3.6 (API version: 1.3.0)
# - v2.7.1 9.5.3.6 (API version: 1.3.0)
# - v2.8.1 9.5.3.6 (API version: 1.3.0)
# - v3.3.1 9.5.3.6 (API version: 1.4.0)
@base.TackerObjectRegistry.register
class PlacementConstraintV1(base.TackerObject, base.TackerObjectDictCompat):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'affinityOrAntiAffinity': fields.EnumField(
            valid_values=[
                'AFFINITY',
                'ANTI_AFFINITY',
            ],
            nullable=False
        ),
        'scope': fields.EnumField(
            valid_values=[
                'NFVI_POP',
                'ZONE',
                'ZONE_GROUP',
                'NFVI_NODE',
            ],
            nullable=False,
        ),
        'resource': fields.ListOfObjectsField(
            'ConstraintResourceRefV1', nullable=False),
        'fallbackBestEffort': fields.BooleanField(nullable=True),
    }
