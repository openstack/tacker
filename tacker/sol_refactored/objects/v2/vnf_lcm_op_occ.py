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
import copy

from oslo_config import cfg
from oslo_serialization import jsonutils

from tacker._i18n import _
from tacker.common import crypt_utils
from tacker.sol_refactored import objects
from tacker.sol_refactored.objects import base
from tacker.sol_refactored.objects import fields
from tacker.sol_refactored.objects.v2 import fields as v2fields

CONF = cfg.CONF


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

    @classmethod
    def from_db_obj(cls, db_obj):
        lcmocc = super().from_db_obj(db_obj)
        if not CONF.use_credential_encryption:
            # If use_credential_encryption in the config is False,
            # credential information is not encrypted.
            return lcmocc

        if lcmocc.obj_attr_is_set('operationParams'):
            op_param = lcmocc.operationParams
            try:
                vim_infos_exist = op_param.obj_attr_is_set('vimConnectionInfo')
            except AttributeError:
                vim_infos_exist = False
            if vim_infos_exist:
                crypt_utils.decrypt_vim_infos_v2(op_param.vimConnectionInfo)

            try:
                add_param_exist = op_param.obj_attr_is_set('additionalParams')
            except AttributeError:
                add_param_exist = False
            if add_param_exist:
                for vdu_param in (op_param.additionalParams
                                          .get('vdu_params', [])):
                    for vnfc_param_key in ['old_vnfc_param', 'new_vnfc_param']:
                        vnfc_param = vdu_param.get(vnfc_param_key, None)
                        if not vnfc_param:
                            continue
                        password = (vnfc_param.get('password', None))
                        if password:
                            dec = crypt_utils.decrypt(password)
                            vdu_param[vnfc_param_key]['password'] = dec
                        password = (vnfc_param.get('authentication', {})
                                              .get('paramsBasic', {})
                                              .get('password', None))
                        if password:
                            dec = crypt_utils.decrypt(password)
                            vdu_param[vnfc_param_key]['authentication'][
                                'paramsBasic']['password'] = dec
                        password = (vnfc_param.get('authentication', {})
                                    .get('paramsOauth2ClientCredentials', {})
                                    .get('clientPassword', None))
                        if password:
                            dec = crypt_utils.decrypt(password)
                            vdu_param[vnfc_param_key]['authentication'][
                                'paramsOauth2ClientCredentials'][
                                'clientPassword'] = dec

        if lcmocc.obj_attr_is_set('changedInfo'):
            chg_info = lcmocc.changedInfo
            if chg_info.obj_attr_is_set('vimConnectionInfo'):
                crypt_utils.decrypt_vim_infos_v2(chg_info.vimConnectionInfo)
        return lcmocc

    def to_db_obj(self):
        obj = super().to_db_obj()
        if not CONF.use_credential_encryption:
            # If use_credential_encryption in the config is False,
            # credential information is not encrypted.
            return obj

        # The credentials for lcm_op_occ are removed because they are never
        # referenced after lcm transitions to terminal states.
        pop_cred = (
            obj.get('operationState') in
            (v2fields.LcmOperationStateType.COMPLETED,
             v2fields.LcmOperationStateType.FAILED,
             v2fields.LcmOperationStateType.ROLLED_BACK))

        def pop_or_encrypt(target_dict, key):
            if pop_cred:
                target_dict.pop(key)
            else:
                enc = crypt_utils.encrypt(target_dict[key])
                target_dict[key] = enc

        op_param_db_obj = obj.get('operationParams', None)
        if op_param_db_obj:
            op_param_db_obj = copy.deepcopy(op_param_db_obj)
            vim_infos = op_param_db_obj.get('vimConnectionInfo', None)
            if vim_infos:
                crypt_utils.encrypt_vim_infos_v2(vim_infos, pop_cred)

            if op_param_db_obj.get('additionalParams', None):
                for vdu_param in (op_param_db_obj['additionalParams']
                                  .get('vdu_params', [])):
                    for vnfc_param_key in ['old_vnfc_param', 'new_vnfc_param']:
                        vnfc_param = vdu_param.get(vnfc_param_key, None)
                        if not vnfc_param:
                            continue
                        if vnfc_param.get('password', None):
                            pop_or_encrypt(vnfc_param, 'password')
                        if (vnfc_param.get('authentication', {})
                                      .get('paramsBasic', {})
                                      .get('password', None)):
                            pop_or_encrypt(vnfc_param['authentication']
                                           ['paramsBasic'],
                                           'password')
                        if (vnfc_param.get('authentication', {})
                                      .get('paramsOauth2ClientCredentials', {})
                                      .get('clientPassword', None)):
                            pop_or_encrypt(vnfc_param['authentication']
                                           ['paramsOauth2ClientCredentials'],
                                           'clientPassword')
            obj['operationParams'] = op_param_db_obj

        chg_info_db_obj = obj.get('changedInfo', None)
        if chg_info_db_obj:
            chg_info = jsonutils.loads(chg_info_db_obj)
            vim_infos = chg_info.get('vimConnectionInfo', None)
            if vim_infos:
                crypt_utils.encrypt_vim_infos_v2(vim_infos, pop_cred)
                obj['changedInfo'] = jsonutils.dumps(chg_info)
        return obj


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
