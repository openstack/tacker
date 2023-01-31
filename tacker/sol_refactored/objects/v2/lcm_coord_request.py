# Copyright (C) 2023 Nippon Telegraph and Telephone Corporation
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


# NFV-SOL 002
# - v3.6.1 10.5.2.2 (API version: 1.0.0)
@base.TackerObjectRegistry.register
class LcmCoordRequest(base.TackerPersistentObject,
                      base.TackerObjectDictCompat):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'vnfInstanceId': fields.StringField(nullable=False),
        'vnfLcmOpOccId': fields.StringField(nullable=False),
        # NOTE: its type is LcmOperationForCoordType according to the
        # specification, but it is same as LcmOperationType.
        'lcmOperationType': v2fields.LcmOperationTypeField(nullable=False),
        'coordinationActionName': fields.StringField(nullable=False),
        'inputParams': fields.KeyValuePairsField(nullable=True),
        '_links': fields.ObjectField('LcmCoordRequest_Links', nullable=False)
    }


@base.TackerObjectRegistry.register
class LcmCoordRequest_Links(base.TackerObject):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'vnfLcmOpOcc': fields.ObjectField('Link', nullable=False),
        'vnfInstance': fields.ObjectField('Link', nullable=False)
    }
