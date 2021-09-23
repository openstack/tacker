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
from tacker.sol_refactored.objects.v2 import fields as v2fields


# NFV-SOL 003
# - v3.3.1 5.5.3.12 (API version: 2.0.0)
@base.TackerObjectRegistry.register
class LifecycleChangeNotificationsFilterV2(base.TackerObject,
                                           base.TackerObjectDictCompat):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'vnfInstanceSubscriptionFilter': fields.ObjectField(
            'VnfInstanceSubscriptionFilter', nullable=True),
        'notificationTypes': fields.ListOfEnumField(
            valid_values=[
                'VnfLcmOperationOccurrenceNotification',
                'VnfIdentifierCreationNotification',
                'VnfIdentifierDeletionNotification',
            ],
            nullable=True,
        ),
        'operationTypes': fields.Field(fields.List(
            v2fields.LcmOperationTypeField(), nullable=True)),
        'operationStatus': fields.Field(fields.List(
            v2fields.LcmOperationStateTypeField(), nullable=True)),
    }
