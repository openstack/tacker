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
# - v3.3.1 6.5.2.10 (API version: 2.1.0)
@base.TackerObjectRegistry.register
class PerformanceReportV2(base.TackerPersistentObject,
                          base.TackerObjectDictCompat):

    # Version 1.0: Initial version
    VERSION = '1.0'

    # PerformanceReportV2 need 'id' and 'jobId'
    fields = {
        'id': fields.StringField(nullable=False),
        'jobId': fields.StringField(nullable=False),
        'entries': fields.ListOfObjectsField(
            'VnfPmReportV2_Entries', nullable=False),
    }


@base.TackerObjectRegistry.register
class VnfPmReportV2_Entries(base.TackerObject, base.TackerObjectDictCompat):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'objectType': fields.StringField(nullable=False),
        'objectInstanceId': fields.StringField(nullable=False),
        'subObjectInstanceId': fields.StringField(nullable=True),
        'performanceMetric': fields.StringField(nullable=False),
        'performanceValues': fields.ListOfObjectsField(
            'VnfPmReportV2_Entries_PerformanceValues', nullable=False),
    }


@base.TackerObjectRegistry.register
class VnfPmReportV2_Entries_PerformanceValues(base.TackerObject,
                                              base.TackerObjectDictCompat):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'timeStamp': fields.DateTimeField(nullable=False),
        'value': fields.StringField(nullable=False),
        'context': fields.KeyValuePairsField(nullable=True),
    }
