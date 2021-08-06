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
# - v3.3.1 9.5.3.2 (API version: 2.1.0)
@base.TackerObjectRegistry.register
class VnfPackageSoftwareImageInfoV2(base.TackerObject,
                                    base.TackerObjectDictCompat):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.StringField(nullable=False),
        'name': fields.StringField(nullable=False),
        'provider': fields.StringField(nullable=False),
        'version': fields.VersionField(nullable=False),
        'checksum': fields.ChecksumField(nullable=False),
        'isEncrypted': fields.BooleanField(nullable=False),
        'containerFormat': fields.EnumField(
            valid_values=[
                'AKI',
                'AMI',
                'ARI',
                'BARE',
                'DOCKER',
                'OVA',
                'OVF',
            ],
            nullable=False,
        ),
        'diskFormat': fields.EnumField(
            valid_values=[
                'AKI',
                'AMI',
                'ARI',
                'ISO',
                'QCOW2',
                'RAW',
                'VDI',
                'VHD',
                'VHDX',
                'VMDK',
            ],
            nullable=False,
        ),
        'createdAt': fields.DateTimeField(nullable=False),
        'minDisk': fields.NonNegativeIntegerField(nullable=False),
        'minRam': fields.NonNegativeIntegerField(nullable=False),
        'size': fields.NonNegativeIntegerField(nullable=False),
        'userMetadata': fields.KeyValuePairsField(nullable=True),
        'imagePath': fields.StringField(nullable=True),
        'imageUri': fields.UriField(nullable=True),
    }
