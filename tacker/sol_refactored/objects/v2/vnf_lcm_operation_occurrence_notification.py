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
# - v3.3.1 5.5.2.17 (API version: 2.0.0)
@base.TackerObjectRegistry.register
class VnfLcmOperationOccurrenceNotificationV2(base.TackerObject,
                                              base.TackerObjectDictCompat):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.StringField(nullable=False),
        'notificationType': fields.StringField(nullable=False),
        'subscriptionId': fields.StringField(nullable=False),
        'timeStamp': fields.DateTimeField(nullable=False),
        'notificationStatus': fields.EnumField(
            valid_values=['START', 'RESULT'], nullable=False),
        'operationState': v2fields.LcmOperationStateTypeField(
            nullable=False),
        'vnfInstanceId': fields.StringField(nullable=False),
        'operation': v2fields.LcmOperationTypeField(nullable=False),
        'isAutomaticInvocation': fields.BooleanField(nullable=False),
        'verbosity': v2fields.LcmOpOccNotificationVerbosityTypeField(
            nullable=True),
        'vnfLcmOpOccId': fields.StringField(nullable=False),
        'affectedVnfcs': fields.ListOfObjectsField(
            'AffectedVnfcV2', nullable=True),
        'affectedVirtualLinks': fields.ListOfObjectsField(
            'AffectedVirtualLinkV2', nullable=True),
        'affectedExtLinkPorts': fields.ListOfObjectsField(
            'AffectedExtLinkPortV2', nullable=True),
        'affectedVirtualStorages': fields.ListOfObjectsField(
            'AffectedVirtualStorageV2', nullable=True),
        'changedInfo': fields.ObjectField(
            'VnfInfoModificationsV2', nullable=True),
        'changedExtConnectivity': fields.ListOfObjectsField(
            'ExtVirtualLinkInfoV2', nullable=True),
        'modificationsTriggeredByVnfPkgChange': fields.ObjectField(
            'ModificationsTriggeredByVnfPkgChangeV2', nullable=True),
        'error': fields.ObjectField('ProblemDetails', nullable=True),
        '_links': fields.ObjectField('LccnLinksV2', nullable=False),
    }
