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

from tacker._i18n import _
from tacker.sol_refactored import objects
from tacker.sol_refactored.objects import base
from tacker.sol_refactored.objects import fields
from tacker.sol_refactored.objects.v2 import fields as v2fields


class OperationParam(fields.FieldType):
    @staticmethod
    def coerce(obj, attr, value):
        if not hasattr(obj, 'operation'):
            raise ValueError(_("'operation' must have been coerced "
                               "before 'operationParams'"))
        if obj.operation == v2fields.LcmOperationType.INSTANTIATE:
            cls = objects.InstantiateVnfRequest
        elif obj.operation == v2fields.LcmOperationType.SCALE:
            cls = objects.ScaleVnfRequest
        elif obj.operation == v2fields.LcmOperationType.SCALE_TO_LEVEL:
            cls = objects.ScaleVnfToLevelRequest
        elif obj.operation == v2fields.LcmOperationType.CHANGE_FLAVOUR:
            cls = objects.ChangeVnfFlavourRequest
        elif obj.operation == v2fields.LcmOperationType.OPERATE:
            cls = objects.OperateVnfRequest
        elif obj.operation == v2fields.LcmOperationType.HEAL:
            cls = objects.HealVnfRequest
        elif obj.operation == v2fields.LcmOperationType.CHANGE_EXT_CONN:
            cls = objects.ChangeExtVnfConnectivityRequest
        elif obj.operation == v2fields.LcmOperationType.TERMINATE:
            cls = objects.TerminateVnfRequest
        elif obj.operation == v2fields.LcmOperationType.MODIFY_INFO:
            cls = objects.VnfInfoModificationRequest
        elif obj.operation == v2fields.LcmOperationType.CREATE_SNAPSHOT:
            cls = objects.CreateVnfSnapshotRequest
        elif obj.operation == v2fields.LcmOperationType.REVERT_TO_SNAPSHOT:
            cls = objects.RevertToVnfSnapshotRequest
        elif obj.operation == v2fields.LcmOperationType.CHANGE_VNFPKG:
            cls = objects.ChangeCurrentVnfPkgRequest
        else:
            raise ValueError(_("Unexpected 'operation' found."))

        return cls.from_dict(value)

    def to_primitive(self, obj, attr, value):
        return value.to_dict()


class OperationParamsField(fields.AutoTypedField):
    AUTO_TYPE = OperationParam()


# NFV-SOL 003
# - v3.3.1 5.5.2.13 (API version: 2.0.0)
@base.TackerObjectRegistry.register
class VnfLcmOpOccV2(base.TackerPersistentObject,
                    base.TackerObjectDictCompat):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.StringField(nullable=False),
        'operationState': v2fields.LcmOperationStateTypeField(nullable=False),
        'stateEnteredTime': fields.DateTimeField(nullable=False),
        'startTime': fields.DateTimeField(nullable=False),
        'vnfInstanceId': fields.StringField(nullable=False),
        'grantId': fields.StringField(nullable=True),
        'operation': v2fields.LcmOperationTypeField(nullable=False),
        'isAutomaticInvocation': fields.BooleanField(nullable=False),
        'operationParams': OperationParamsField(nullable=True),
        'isCancelPending': fields.BooleanField(nullable=False),
        'cancelMode': v2fields.CancelModeTypeField(nullable=True),
        'error': fields.ObjectField(
            'ProblemDetails', nullable=True),
        'resourceChanges': fields.ObjectField(
            'VnfLcmOpOccV2_ResourceChanges', nullable=True),
        'changedInfo': fields.ObjectField(
            'VnfInfoModificationsV2', nullable=True),
        'changedExtConnectivity': fields.ListOfObjectsField(
            'ExtVirtualLinkInfoV2', nullable=True),
        'modificationsTriggeredByVnfPkgChange': fields.ObjectField(
            'ModificationsTriggeredByVnfPkgChangeV2', nullable=True),
        'vnfSnapshotInfoId': fields.StringField(nullable=True),
        '_links': fields.ObjectField('VnfLcmOpOccV2_Links', nullable=False),
    }


@base.TackerObjectRegistry.register
class VnfLcmOpOccV2_ResourceChanges(base.TackerObject,
                                    base.TackerObjectDictCompat):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'affectedVnfcs': fields.ListOfObjectsField(
            'AffectedVnfcV2', nullable=True),
        'affectedVirtualLinks': fields.ListOfObjectsField(
            'AffectedVirtualLinkV2', nullable=True),
        'affectedExtLinkPorts': fields.ListOfObjectsField(
            'AffectedExtLinkPortV2', nullable=True),
        'affectedVirtualStorages': fields.ListOfObjectsField(
            'AffectedVirtualStorageV2', nullable=True)
    }


@base.TackerObjectRegistry.register
class VnfLcmOpOccV2_Links(base.TackerObject):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'self': fields.ObjectField('Link', nullable=False),
        'vnfInstance': fields.ObjectField('Link', nullable=False),
        'grant': fields.ObjectField('Link', nullable=True),
        'cancel': fields.ObjectField('Link', nullable=True),
        'retry': fields.ObjectField('Link', nullable=True),
        'rollback': fields.ObjectField('Link', nullable=True),
        'fail': fields.ObjectField('Link', nullable=True),
        'vnfSnapshot': fields.ObjectField('Link', nullable=True),
    }
