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
# - v3.3.1 5.5.2.9 (API version: 2.0.0)
@base.TackerObjectRegistry.register
class HealVnfRequestV2(base.TackerObject, base.TackerObjectDictCompat):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'cause': fields.StringField(nullable=True),
        'additionalParams': fields.KeyValuePairsField(nullable=True),
        # NOTE: following fields are defined in NFV-SOL 002 v3.3.1 5.5.2.9
        'vnfcInstanceId': fields.ListOfStringsField(nullable=True),
        'healScript': fields.StringField(nullable=True),
    }