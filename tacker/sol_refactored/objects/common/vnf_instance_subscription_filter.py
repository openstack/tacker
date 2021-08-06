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
# - v3.3.1 4.4.1.5
@base.TackerObjectRegistry.register
class VnfInstanceSubscriptionFilter(base.TackerObject,
                                    base.TackerObjectDictCompat):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'vnfdIds': fields.ListOfStringsField(nullable=True),
        'vnfProductsFromProviders': fields.ListOfObjectsField(
            '_VnfProductsFromProviders', nullable=True),
        'vnfInstanceIds': fields.ListOfStringsField(nullable=True),
        'vnfInstanceNames': fields.ListOfStringsField(nullable=True),
    }


# NOTE: For the following names of internal classes, there should be
# 'VnfInstanceSubscriptionFilter' in the top according to a principle,
# but omits it as it is too long.

@base.TackerObjectRegistry.register
class _VnfProductsFromProviders(
        base.TackerObject, base.TackerObjectDictCompat):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'vnfProvider': fields.StringField(nullable=False),
        'vnfProducts': fields.ListOfObjectsField(
            '_VnfProductsFromProviders_VnfProducts', nullable=True),
    }


@base.TackerObjectRegistry.register
class _VnfProductsFromProviders_VnfProducts(
        base.TackerObject, base.TackerObjectDictCompat):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'vnfProductName': fields.StringField(nullable=False),
        'versions': fields.ListOfObjectsField(
            '_VnfProductsFromProviders_VnfProducts_Versions', nullable=True),
    }


@base.TackerObjectRegistry.register
class _VnfProductsFromProviders_VnfProducts_Versions(
        base.TackerObject, base.TackerObjectDictCompat):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'vnfSoftwareVersion': fields.VersionField(nullable=False),
        'vnfdVersions': fields.ListOfVersionsField(nullable=True),
    }
