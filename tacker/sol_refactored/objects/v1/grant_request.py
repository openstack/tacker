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
from tacker.sol_refactored.objects.v1 import fields as v1fields


# NFV-SOL 003
# - v3.3.1 9.5.2.2 (API version: 1.4.0)
@base.TackerObjectRegistry.register
class GrantRequestV1(base.TackerPersistentObject,
                     base.TackerObjectDictCompat):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'vnfInstanceId': fields.StringField(nullable=False),
        'vnfLcmOpOccId': fields.StringField(nullable=False),
        'vnfdId': fields.StringField(nullable=False),
        'dstVnfdId': fields.StringField(nullable=True),
        'flavourId': fields.StringField(nullable=True),
        'operation': v1fields.GrantedLcmOperationTypeField(nullable=False),
        'isAutomaticInvocation': fields.BooleanField(nullable=False),
        'instantiationLevelId': fields.StringField(nullable=True),
        'addResources': fields.ListOfObjectsField(
            'ResourceDefinitionV1', nullable=True),
        'tempResources': fields.ListOfObjectsField(
            'ResourceDefinitionV1', nullable=True),
        'removeResources': fields.ListOfObjectsField(
            'ResourceDefinitionV1', nullable=True),
        'updateResources': fields.ListOfObjectsField(
            'ResourceDefinitionV1', nullable=True),
        'placementConstraints': fields.ListOfObjectsField(
            'PlacementConstraintV1', nullable=True),
        'vimConstraints': fields.ListOfObjectsField(
            'VimConstraintV1', nullable=True),
        'additionalParams': fields.KeyValuePairsField(nullable=True),
        '_links': fields.ObjectField('GrantRequestV1_Links', nullable=False),
    }


@base.TackerObjectRegistry.register
class GrantRequestV1_Links(base.TackerObject):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'vnfLcmOpOcc': fields.ObjectField('Link', nullable=False),
        'vnfInstance': fields.ObjectField('Link', nullable=False),
    }
