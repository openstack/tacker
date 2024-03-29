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


# NFV-SOL 013
# - v3.4.1 6.3
@base.TackerObjectRegistry.register
class ProblemDetails(base.TackerObject, base.TackerObjectDictCompat):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'type': fields.UriField(nullable=True),
        'title': fields.StringField(nullable=True),
        'status': fields.IntegerField(nullable=False),
        'detail': fields.StringField(nullable=False),
        'instance': fields.UriField(nullable=True),
        # NOTE: userScriptErrHandlingData is not defined in SOL003.
        # It is original definition of Tacker.
        'userScriptErrHandlingData': fields.KeyValuePairsField(nullable=True),
    }
