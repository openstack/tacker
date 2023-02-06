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
# - v3.3.1 6.5.2.4 (API version: 2.1.0)
@base.TackerObjectRegistry.register
class ThresholdCrossedNotificationV2(
    base.TackerObject,
    base.TackerObjectDictCompat
):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.StringField(nullable=False),
        'notificationType': fields.StringField(nullable=False),
        'timeStamp': fields.DateTimeField(nullable=False),
        'thresholdId': fields.StringField(nullable=False),
        'crossingDirection': fields.StringField(nullable=False),
        'objectType': fields.StringField(nullable=False),
        'objectInstanceId': fields.StringField(nullable=False),
        'subObjectInstanceId': fields.StringField(nullable=True),
        'performanceMetric': fields.StringField(nullable=False),
        'performanceValue': fields.StringField(nullable=False),
        # NOTE: ThresholdCrossedNotificationV2 does not support 'context' now
        'context': fields.KeyValuePairsField(nullable=True),
        '_links': fields.ObjectField(
            'ThresholdCrossedNotificationV2_Links',
            nullable=False),
    }


@base.TackerObjectRegistry.register
class ThresholdCrossedNotificationV2_Links(
    base.TackerObject,
    base.TackerObjectDictCompat
):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'objectInstance': fields.ObjectField(
            'NotificationLink', nullable=True),
        'threshold': fields.ObjectField(
            'NotificationLink', nullable=False),
    }
