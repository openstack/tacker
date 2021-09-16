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
from tacker.sol_refactored.objects.v2 import fields as v2fields


# NFV-SOL 005
# - v3.3.1 9.5.3.4 (API version: 2.1.0)
@base.TackerObjectRegistry.register
class PkgmNotificationFilterV2(base.TackerObject, base.TackerObjectDictCompat):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'notificationTypes': fields.ListOfEnumField(
            valid_values=[
                'VnfPackageOnboardingNotification',
                'VnfPackageChangeNotification',
            ],
            nullable=True,
        ),
        'vnfProductsFromProviders': fields.ListOfObjectsField(
            'PkgmNotificationFilterV2_VnfProductsFromProviders',
            nullable=True),
        'vnfdId': fields.ListOfStringsField(nullable=True),
        'vnfPkgId': fields.ListOfStringsField(nullable=True),
        'operationalState': fields.Field(fields.List(
            v2fields.PackageOperationalStateType), nullable=True),
        'usageState': fields.Field(fields.List(
            v2fields.PackageUsageStateType), nullable=True),
        'vnfmInfo': fields.ListOfStringsField(nullable=True),
    }


@base.TackerObjectRegistry.register
class PkgmNotificationFilterV2_VnfProductsFromProviders(
        base.TackerObject, base.TackerObjectDictCompat):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'vnfProvider': fields.StringField(nullable=False),
        'vnfProducts': fields.ListOfObjectsField(
            'PkgmNotificationFilterV2_VnfProductsFromProviders_VnfProducts',
            nullable=True),
    }


@base.TackerObjectRegistry.register
class PkgmNotificationFilterV2_VnfProductsFromProviders_VnfProducts(
        base.TackerObject, base.TackerObjectDictCompat):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'vnfProductName': fields.StringField(nullable=False),
        'vnfVersions': fields.ListOfObjectsField(
            'PkgmNotificationFilterV2_VnfProductsFromProviders_'
            'VnfProducts_Versions',
            nullable=True),
    }


@base.TackerObjectRegistry.register
class PkgmNotificationFilterV2_VnfProductsFromProviders_VnfProducts_Versions(
        base.TackerObject, base.TackerObjectDictCompat):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'vnfSoftwareVersion': fields.VersionField(nullable=False),
        'vnfdVersion': fields.VersionField(nullable=False),
    }
