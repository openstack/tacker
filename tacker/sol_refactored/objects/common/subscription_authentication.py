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
# - v3.4.1 Table 8.3.4-1
@base.TackerObjectRegistry.register
class SubscriptionAuthentication(base.TackerObject,
                                 base.TackerObjectDictCompat):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'authType': fields.ListOfEnumField(
            valid_values=[
                'BASIC',
                'OAUTH2_CLIENT_CREDENTIALS',
                'TLS_CERT',
            ],
            nullable=False),
        'paramsBasic': fields.ObjectField(
            'SubscriptionAuthentication_ParamsBasic', nullable=True),
        'paramsOauth2ClientCredentials': fields.ObjectField(
            'SubscriptionAuthentication_ParamsOauth2', nullable=True),
    }


@base.TackerObjectRegistry.register
class SubscriptionAuthentication_ParamsBasic(base.TackerObject,
                                             base.TackerObjectDictCompat):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'userName': fields.StringField(nullable=True),
        'password': fields.StringField(nullable=True),
    }


# NOTE: It should be
# SubscriptionAuthentication_ParamsOauth2ClientCredentials
# according to a principle, but shortened it as it is too long.

@base.TackerObjectRegistry.register
class SubscriptionAuthentication_ParamsOauth2(
        base.TackerObject, base.TackerObjectDictCompat):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'clientId': fields.StringField(nullable=True),
        'clientPassword': fields.StringField(nullable=True),
        'tokenEndpoint': fields.UriField(nullable=True),
    }
