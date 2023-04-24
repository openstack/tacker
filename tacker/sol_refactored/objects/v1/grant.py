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
from oslo_config import cfg
from oslo_serialization import jsonutils

from tacker.common import crypt_utils
from tacker.sol_refactored.objects import base
from tacker.sol_refactored.objects import fields

CONF = cfg.CONF


# NFV-SOL 003
# - v3.3.1 9.5.2.3 (API version: 1.4.0)
@base.TackerObjectRegistry.register
class GrantV1(base.TackerPersistentObject,
              base.TackerObjectDictCompat):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.StringField(nullable=False),
        'vnfInstanceId': fields.StringField(nullable=False),
        'vnfLcmOpOccId': fields.StringField(nullable=False),
        'vimConnectionInfo': fields.DictOfObjectsField(
            'VimConnectionInfo', nullable=True),
        'zones': fields.ListOfObjectsField(
            'ZoneInfoV1', nullable=True),
        'zoneGroups': fields.ListOfObjectsField(
            'ZoneGroupInfoV1', nullable=True),
        'addResources': fields.ListOfObjectsField(
            'GrantInfoV1', nullable=True),
        'tempResources': fields.ListOfObjectsField(
            'GrantInfoV1', nullable=True),
        'removeResources': fields.ListOfObjectsField(
            'GrantInfoV1', nullable=True),
        'updateResources': fields.ListOfObjectsField(
            'GrantInfoV1', nullable=True),
        'vimAssets': fields.ObjectField(
            'GrantV1_VimAssets', nullable=True),
        'extVirtualLinks': fields.ListOfObjectsField(
            'ExtVirtualLinkData', nullable=True),
        'extManagedVirtualLinks': fields.ListOfObjectsField(
            'ExtManagedVirtualLinkData', nullable=True),
        'additionalParams': fields.KeyValuePairsField(nullable=True),
        '_links': fields.ObjectField('GrantV1_Links', nullable=False),
    }

    @classmethod
    def from_db_obj(cls, db_obj):
        grant = super().from_db_obj(db_obj)
        if not CONF.use_credential_encryption:
            # If use_credential_encryption in the config is False,
            # credential information is not encrypted.
            return grant

        if grant.obj_attr_is_set('vimConnectionInfo'):
            crypt_utils.decrypt_vim_infos_v2(grant.vimConnectionInfo)
        return grant

    def to_db_obj(self):
        obj = super().to_db_obj()
        if not CONF.use_credential_encryption:
            # If use_credential_encryption in the config is False,
            # credential information is not encrypted.
            return obj

        vim_infos_db_obj = obj.get('vimConnectionInfo', None)
        if vim_infos_db_obj:
            vim_infos = jsonutils.loads(vim_infos_db_obj)
            crypt_utils.encrypt_vim_infos_v2(vim_infos)
            obj['vimConnectionInfo'] = jsonutils.dumps(vim_infos)
        return obj


@base.TackerObjectRegistry.register
class GrantV1_VimAssets(base.TackerObject,
                        base.TackerObjectDictCompat):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'computeResourceFlavours': fields.ListOfObjectsField(
            'VimComputeResourceFlavourV1', nullable=True),
        'softwareImages': fields.ListOfObjectsField(
            'VimSoftwareImageV1', nullable=True),
        'snapshotResources': fields.ListOfObjectsField(
            'VimSnapshotResourceV1', nullable=True),
    }


@base.TackerObjectRegistry.register
class GrantV1_Links(base.TackerObject):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'self': fields.ObjectField('Link', nullable=False),
        'vnfLcmOpOcc': fields.ObjectField('Link', nullable=False),
        'vnfInstance': fields.ObjectField('Link', nullable=False),
    }
