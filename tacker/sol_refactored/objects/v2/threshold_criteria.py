# Copyright (C) 2023 Fujitsu
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
# - v3.3.1 6.5.3.4 (API version: 2.1.0)
@base.TackerObjectRegistry.register
class ThresholdCriteriaV2(base.TackerObject, base.TackerObjectDictCompat):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'performanceMetric': fields.StringField(nullable=False),
        'thresholdType': fields.StringField(nullable=False),
        'simpleThresholdDetails': fields.ObjectField(
            'SimpleThresholdDetails', nullable=True),
    }


@base.TackerObjectRegistry.register
class SimpleThresholdDetails(base.TackerObject, base.TackerObjectDictCompat):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'thresholdValue': fields.FloatField(nullable=False),
        'hysteresis': fields.NonNegativeFloatField(nullable=False),
    }
