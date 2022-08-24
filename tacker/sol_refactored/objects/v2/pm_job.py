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
# - v3.3.1 6.5.2.7 (API version: 2.1.0)
@base.TackerObjectRegistry.register
class PmJobV2(base.TackerPersistentObject, base.TackerObjectDictCompat):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.StringField(nullable=False),
        'objectType': fields.StringField(nullable=False),
        'objectInstanceIds': fields.ListOfStringsField(nullable=False),
        'subObjectInstanceIds': fields.ListOfStringsField(nullable=True),
        'criteria': fields.ObjectField('VnfPmJobCriteriaV2', nullable=False),
        'callbackUri': fields.UriField(nullable=False),
        'reports': fields.ListOfObjectsField(
            'VnfPmJobV2_Reports', nullable=False),
        '_links': fields.ObjectField(
            'VnfPmJobV2_Links', nullable=False),
        # NOTE: 'authentication' attribute is not included in the
        # original 'PmJob' data type definition.
        # It is necessary to keep this to be used at sending
        # notifications. Note that it is dropped at GET subscription.
        'authentication': fields.ObjectField(
            'SubscriptionAuthentication', nullable=True),
        # NOTE: 'metadata' attribute is not included in the
        # original 'PmJob' data type definition.
        # It is necessary to keep this to be used at setting prometheus config.
        'metadata': fields.KeyValuePairsField(nullable=True),
    }


@base.TackerObjectRegistry.register
class VnfPmJobV2_Reports(base.TackerObject, base.TackerObjectDictCompat):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'href': fields.UriField(nullable=False),
        'readyTime': fields.DateTimeField(nullable=False),
        'expiryTime': fields.DateTimeField(nullable=True),
        'fileSize': fields.IntegerField(nullable=True),
    }


@base.TackerObjectRegistry.register
class VnfPmJobV2_Links(base.TackerObject, base.TackerObjectDictCompat):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'self': fields.ObjectField('Link', nullable=False),
        'objects': fields.ListOfObjectsField('Link', nullable=True),
    }
