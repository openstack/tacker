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
# - v3.3.1 6.5.2.5 (API version: 2.1.0)
@base.TackerObjectRegistry.register
class PerformanceInformationAvailableNotificationV2(
    base.TackerObject,
    base.TackerObjectDictCompat
):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.StringField(nullable=False),
        'notificationType': fields.StringField(nullable=False),
        'timeStamp': fields.DateTimeField(nullable=False),
        'pmJobId': fields.StringField(nullable=False),
        'objectType': fields.StringField(nullable=False),
        'objectInstanceId': fields.StringField(nullable=False),
        'subObjectInstanceIds': fields.ListOfStringsField(nullable=True),
        '_links': fields.ObjectField(
            'PerformanceInformationAvailableNotificationV2_Links',
            nullable=False),
    }


@base.TackerObjectRegistry.register
class PerformanceInformationAvailableNotificationV2_Links(
    base.TackerObject,
    base.TackerObjectDictCompat
):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'objectInstance': fields.ObjectField(
            'NotificationLink', nullable=True),
        'pmJob': fields.ObjectField(
            'NotificationLink', nullable=False),
        'performanceReport': fields.ObjectField(
            'NotificationLink', nullable=False),
    }
