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


# NFV-SOL 003
# - v3.3.1 5.5.2.12a (API version: 2.0.0)
@base.TackerObjectRegistry.register
class VnfInfoModificationsV2(base.TackerObject, base.TackerObjectDictCompat):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'vnfInstanceName': fields.StringField(nullable=True),
        'vnfInstanceDescription': fields.StringField(nullable=True),
        'vnfConfigurableProperties': fields.KeyValuePairsField(nullable=True),
        'metadata': fields.KeyValuePairsField(nullable=True),
        'extensions': fields.KeyValuePairsField(nullable=True),
        'vimConnectionInfo': fields.DictOfObjectsField(
            'VimConnectionInfo', nullable=True),
        'vnfdId': fields.StringField(nullable=True),
        'vnfProvider': fields.StringField(nullable=True),
        'vnfProductName': fields.StringField(nullable=True),
        'vnfSoftwareVersion': fields.VersionField(nullable=True),
        'vnfdVersion': fields.VersionField(nullable=True),
        # NOTE: vnfcInfoModifications is defined in
        # NFV-SOL 002 v3.3.1 5.5.2.12a
        'vnfcInfoModifications': fields.ListOfObjectsField(
            'VnfcInfoModificationsV2', nullable=True),
    }
