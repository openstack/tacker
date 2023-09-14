# Copyright (C) 2023 Fujitsu
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

from tacker.common import crypt_utils
from tacker.sol_refactored.objects import base
from tacker.sol_refactored.objects import fields

CONF = cfg.CONF


# NFV-SOL 003
# - v3.3.1 6.5.2.9 (API version: 2.1.0)
@base.TackerObjectRegistry.register
class ThresholdV2(base.TackerPersistentObject, base.TackerObjectDictCompat):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.StringField(nullable=False),
        'objectType': fields.StringField(nullable=False),
        'objectInstanceId': fields.StringField(nullable=False),
        'subObjectInstanceIds': fields.ListOfStringsField(nullable=True),
        'criteria': fields.ObjectField('ThresholdCriteriaV2', nullable=False),
        'callbackUri': fields.UriField(nullable=False),
        '_links': fields.ObjectField(
            'ThresholdV2_Links', nullable=False),
        # NOTE: 'authentication' attribute is not included in the
        # original 'Threshold' data type definition.
        # It is necessary to keep this to be used at sending
        # notifications. Note that it is dropped at GET subscription.
        'authentication': fields.ObjectField(
            'SubscriptionAuthentication', nullable=True),
        # NOTE: 'metadata' attribute is not included in the
        # original 'Threshold' data type definition.
        # It is necessary to keep this to be used at setting prometheus config.
        'metadata': fields.KeyValuePairsField(nullable=True),
    }

    @classmethod
    def from_db_obj(cls, db_obj):
        threshold = super().from_db_obj(db_obj)
        if not CONF.use_credential_encryption:
            # If use_credential_encryption in the config is False,
            # credential information is not encrypted.
            return threshold

        if threshold.obj_attr_is_set('authentication'):
            auth = threshold.authentication
            crypt_utils.decrypt_subsc_auth_v2(auth)

        if threshold.obj_attr_is_set('metadata'):
            metadata = threshold.metadata
            crypt_utils.decrypt_monitoring_v2(metadata)
        return threshold

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

        metadata = obj.get('metadata__', None)
        if metadata:
            metadata = copy.deepcopy(metadata)
            crypt_utils.encrypt_monitoring_v2(metadata)
            obj['metadata__'] = metadata
        return obj


@base.TackerObjectRegistry.register
class ThresholdV2_Links(base.TackerObject, base.TackerObjectDictCompat):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'self': fields.ObjectField('Link', nullable=False),
        'object': fields.ObjectField('Link', nullable=True),
    }
