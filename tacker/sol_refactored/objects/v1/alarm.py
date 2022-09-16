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
from tacker.sol_refactored.objects.v1 import fields as v1fields


# NFV-SOL 003
# - v3.3.1 7.5.2.4 (API version: 1.3.0)
@base.TackerObjectRegistry.register
class AlarmV1(base.TackerPersistentObject, base.TackerObjectDictCompat):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.StringField(nullable=False),
        'managedObjectId': fields.StringField(nullable=False),
        # NOTE: vnfcInstanceIds is defined in NFV-SOL 002 v3.3.1 7.5.2.4
        'vnfcInstanceIds': fields.ListOfStringsField(nullable=True),
        'rootCauseFaultyResource': fields.ObjectField(
            'AlarmV1_FaultyResourceInfo', nullable=True),
        'alarmRaisedTime': fields.DateTimeField(nullable=False),
        'alarmChangedTime': fields.DateTimeField(nullable=True),
        'alarmClearedTime': fields.DateTimeField(nullable=True),
        'alarmAcknowledgedTime': fields.DateTimeField(nullable=True),
        'ackState': fields.EnumField(
            valid_values=[
                'UNACKNOWLEDGED',
                'ACKNOWLEDGED',
            ],
            nullable=False),
        'perceivedSeverity': v1fields.PerceivedSeverityTypeField(
            nullable=False),
        'eventTime': fields.DateTimeField(nullable=False),
        'eventType': v1fields.EventTypeField(nullable=False),
        'faultType': fields.StringField(nullable=True),
        'probableCause': fields.StringField(nullable=False),
        'isRootCause': fields.BooleanField(nullable=False),
        'correlatedAlarmIds': fields.ListOfStringsField(nullable=True),
        'faultDetails': fields.ListOfStringsField(nullable=True),
        '_links': fields.ObjectField('AlarmV1_Links', nullable=False),

    }


@base.TackerObjectRegistry.register
class AlarmV1_FaultyResourceInfo(base.TackerObject,
                        base.TackerObjectDictCompat):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'faultyResource': fields.ObjectField(
            'ResourceHandle', nullable=False),
        'faultyResourceType': v1fields.FaultyResourceTypeField(
            nullable=False)
    }


@base.TackerObjectRegistry.register
class AlarmV1_Links(base.TackerObject):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'self': fields.ObjectField('Link', nullable=False),
        'objectInstance': fields.ObjectField('Link', nullable=True)
    }
