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
from oslo_config import cfg
from oslo_serialization import jsonutils

from tacker.common import crypt_utils
from tacker.sol_refactored.objects import base
from tacker.sol_refactored.objects import fields

CONF = cfg.CONF


# NFV-SOL 003
# - v3.3.1 7.5.2.3 (API version: 1.3.0)
@base.TackerObjectRegistry.register
class FmSubscriptionV1(base.TackerPersistentObject,
                       base.TackerObjectDictCompat):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.StringField(nullable=False),
        'filter': fields.ObjectField(
            'FmNotificationsFilterV1', nullable=True),
        'callbackUri': fields.UriField(nullable=False),
        # NOTE: 'authentication' attribute is not included in the
        # original 'FmSubscription' data type definition.
        # It is necessary to keep this to be used at sending
        # notifications. Note that it is dropped at GET subscription.
        'authentication': fields.ObjectField(
            'SubscriptionAuthentication', nullable=True),
        '_links': fields.ObjectField(
            'FmSubscriptionV1_Links', nullable=False),
    }

    @classmethod
    def from_db_obj(cls, db_obj):
        fm_subsc = super().from_db_obj(db_obj)
        if not CONF.use_credential_encryption:
            # If use_credential_encryption in the config is False,
            # credential information is not encrypted.
            return fm_subsc

        if fm_subsc.obj_attr_is_set('authentication'):
            auth = fm_subsc.authentication
            crypt_utils.decrypt_subsc_auth_v2(auth)
        return fm_subsc

    def to_db_obj(self):
        obj = super().to_db_obj()
        if not CONF.use_credential_encryption:
            # If use_credential_encryption in the config is False,
            # credential information is not encrypted.
            return obj

        auth_db_obj = obj.get('authentication', None)
        if auth_db_obj:
            auth = jsonutils.loads(auth_db_obj)
            crypt_utils.encrypt_subsc_auth_v2(auth)
            obj['authentication'] = jsonutils.dumps(auth)
        return obj


@base.TackerObjectRegistry.register
class FmSubscriptionV1_Links(base.TackerObject, base.TackerObjectDictCompat):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'self': fields.ObjectField('Link', nullable=False),
    }
