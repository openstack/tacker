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

from tacker.sol_refactored.objects import base
from tacker.sol_refactored.objects import fields


# NFV-SOL 003
# - v3.3.1 6.5.3.3 (API version: 2.0.0)
@base.TackerObjectRegistry.register
class VnfPmJobCriteriaV2(base.TackerObject, base.TackerObjectDictCompat):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'performanceMetric': fields.ListOfStringsField(nullable=True),
        'performanceMetricGroup': fields.ListOfStringsField(nullable=True),
        'collectionPeriod': fields.IntegerField(nullable=False),
        'reportingPeriod': fields.IntegerField(nullable=False),
        'reportingBoundary': fields.DateTimeField(nullable=True),
    }
