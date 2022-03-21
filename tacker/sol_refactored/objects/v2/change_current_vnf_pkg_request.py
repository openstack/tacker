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
# - v3.3.1 5.5.2.11a (API version: 2.0.0)
@base.TackerObjectRegistry.register
class ChangeCurrentVnfPkgRequest(base.TackerObject,
                                 base.TackerObjectDictCompat):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'vnfdId': fields.StringField(nullable=False),
        # NOTE: 'extVirtualLinks' is not supported.
        # It can be specified but make no effect at all.
        'extVirtualLinks': fields.ListOfObjectsField(
            'ExtVirtualLinkData', nullable=True),
        # NOTE: 'extManagedVirtualLinks' is not supported.
        # It can be specified but make no effect at all.
        'extManagedVirtualLinks': fields.ListOfObjectsField(
            'ExtManagedVirtualLinkData', nullable=True),
        # NOTE: 'vimConnectionInfo' is not supported.
        # It can be specified but make no effect at all.
        'vimConnectionInfo': fields.DictOfObjectsField(
            'VimConnectionInfo', nullable=True),
        'additionalParams': fields.KeyValuePairsField(nullable=True),
        # NOTE: 'extensions' is not supported.
        # It can be specified but make no effect at all.
        'extensions': fields.KeyValuePairsField(nullable=True),
        # NOTE: 'vnfConfigurableProperties' is not supported.
        # It can be specified but make no effect at all.
        'vnfConfigurableProperties': fields.KeyValuePairsField(nullable=True),
    }
