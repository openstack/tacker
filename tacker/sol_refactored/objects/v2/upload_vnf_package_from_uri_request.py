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


# NFV-SOL 005
# - v3.3.1 9.5.2.4 (API version: 2.1.0)
@base.TackerObjectRegistry.register
class UploadVnfPackageFromUriRequestV2(base.TackerObject,
                                       base.TackerObjectDictCompat):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'addressInformation': fields.UriField(nullable=False),
        'authType': fields.EnumField(
            valid_values=[
                'BASIC',
                'OAUTH2_CLIENT_CREDENTIALS',
            ],
            nullable=True,
        ),
        'userName': fields.StringField(nullable=True),
        'password': fields.StringField(nullable=True),
        'paramsOauth2ClientCredentials': fields.ObjectField(
            'UploadVnfPackageFromUriRequestV2_ParamsOauth2ClientCredentials',
            nullable=True,
        ),
    }


@base.TackerObjectRegistry.register
class UploadVnfPackageFromUriRequestV2_ParamsOauth2ClientCredentials(
        base.TackerObject, base.TackerObjectDictCompat):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'clientId': fields.StringField(nullable=False),
        'clientPassword': fields.StringField(nullable=False),
        'tokenEndpoint': fields.UriField(nullable=False),
    }
