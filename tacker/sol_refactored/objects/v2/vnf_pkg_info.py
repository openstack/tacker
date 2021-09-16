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
# - v3.3.1 9.5.2.5 (API version: 2.1.0)
@base.TackerObjectRegistry.register
class VnfPkgInfoV2(base.TackerObject, base.TackerObjectDictCompat):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.StringField(nullable=False),
        'vnfdId': fields.StringField(nullable=True),
        'vnfProvider': fields.StringField(nullable=True),
        'vnfProductName': fields.StringField(nullable=True),
        'vnfSoftwareVersion': fields.VersionField(nullable=True),
        'vnfdVersion': fields.VersionField(nullable=True),
        'compatibleSpecificationVersions': fields.ListOfVersionsField(
            nullable=True),
        'checksum': fields.ChecksumField(nullable=True),
        'packageSecurityOption': fields.EnumField(
            valid_values=[
                'OPTION_1',
                'OPTION_2',
            ],
            nullable=False,
        ),
        'signingCertificate': fields.StringField(nullable=True),
        'softwareImages': fields.ListOfObjectsField(
            'VnfPackageSoftwareImageInfoV2', nullable=True),
        'additionalArtifacts': fields.ListOfObjectsField(
            'VnfPackageArtifactInfoV2', nullable=True),
        'onboardingState': v2fields.PackageOnboardingStateTypeField(
            nullable=False),
        'operationalState': v2fields.PackageOperationalStateTypeField(
            nullable=False),
        'usageState': v2fields.PackageUsageStateTypeField(nullable=False),
        'vnfmInfo': fields.ListOfStringsField(nullable=False),
        'userDefinedData': fields.KeyValuePairsField(nullable=True),
        'onboardingFailureDetails': fields.ObjectField(
            'ProblemDetails', nullable=True),
        '_links': fields.ObjectField('VnfPkgInfoV2_Links', nullable=False),
    }


@base.TackerObjectRegistry.register
class VnfPkgInfoV2_Links(base.TackerObject):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'self': fields.ObjectField('Link', nullable=False),
        'vnfd': fields.ObjectField('Link', nullable=False),
        'packageContent': fields.ObjectField('Link', nullable=False),
    }
