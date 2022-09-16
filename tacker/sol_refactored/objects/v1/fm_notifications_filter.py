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
# - v3.3.1 7.5.3.2 (API version: 1.3.0)
@base.TackerObjectRegistry.register
class FmNotificationsFilterV1(base.TackerObject, base.TackerObjectDictCompat):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'vnfInstanceSubscriptionFilter': fields.ObjectField(
            'VnfInstanceSubscriptionFilter', nullable=True),
        'notificationTypes': fields.ListOfEnumField(
            valid_values=[
                'AlarmNotification',
                'AlarmClearedNotification',
                'AlarmListRebuiltNotification',
            ],
            nullable=True,
        ),
        'faultyResourceTypes': fields.Field(fields.List(
            v1fields.FaultyResourceTypeField(), nullable=True)),
        'perceivedSeverities': fields.Field(fields.List(
            v1fields.PerceivedSeverityTypeField(), nullable=True)),
        'eventTypes': fields.Field(fields.List(
            v1fields.EventTypeField(), nullable=True)),
        'probableCauses': fields.ListOfStringsField(nullable=True)
    }
