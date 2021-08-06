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


# NFV-SOL 003
# - v3.3.1 5.5.2.2 (API version: 2.0.0)
@base.TackerObjectRegistry.register
class VnfInstanceV2(base.TackerPersistentObject,
                    base.TackerObjectDictCompat):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.StringField(nullable=False),
        'vnfInstanceName': fields.StringField(nullable=True),
        'vnfInstanceDescription': fields.StringField(nullable=True),
        'vnfdId': fields.StringField(nullable=False),
        'vnfProvider': fields.StringField(nullable=False),
        'vnfProductName': fields.StringField(nullable=False),
        'vnfSoftwareVersion': fields.VersionField(nullable=False),
        'vnfdVersion': fields.VersionField(nullable=False),
        'vnfConfigurableProperties': fields.KeyValuePairsField(nullable=True),
        'vimConnectionInfo': fields.DictOfObjectsField(
            'VimConnectionInfo', nullable=True),
        'instantiationState': fields.EnumField(
            valid_values=[
                'NOT_INSTANTIATED',
                'INSTANTIATED',
            ],
            nullable=False),
        'instantiatedVnfInfo': fields.ObjectField(
            'VnfInstanceV2_InstantiatedVnfInfo', nullable=True),
        'metadata': fields.KeyValuePairsField(nullable=True),
        'extensions': fields.KeyValuePairsField(nullable=True),
        '_links': fields.ObjectField('VnfInstanceV2_Links', nullable=False),
    }


@base.TackerObjectRegistry.register
class VnfInstanceV2_InstantiatedVnfInfo(base.TackerObject,
                                        base.TackerObjectDictCompat):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'flavourId': fields.StringField(nullable=False),
        'vnfState': v2fields.VnfOperationalStateTypeField(nullable=False),
        'scaleStatus': fields.ListOfObjectsField(
            'ScaleInfoV2', nullable=True),
        'maxScaleLevels': fields.ListOfObjectsField(
            'ScaleInfoV2', nullable=True),
        'extCpInfo': fields.ListOfObjectsField(
            'VnfExtCpInfoV2', nullable=False),
        'extVirtualLinkInfo': fields.ListOfObjectsField(
            'ExtVirtualLinkInfoV2', nullable=True),
        'extManagedVirtualLinkInfo': fields.ListOfObjectsField(
            'ExtManagedVirtualLinkInfoV2', nullable=True),
        'monitoringParameters': fields.ListOfObjectsField(
            'MonitoringParameterV2', nullable=True),
        'localizationLanguage': fields.StringField(nullable=True),
        'vnfcResourceInfo': fields.ListOfObjectsField(
            'VnfcResourceInfoV2', nullable=True),
        'vnfVirtualLinkResourceInfo': fields.ListOfObjectsField(
            'VnfVirtualLinkResourceInfoV2', nullable=True),
        'virtualStorageResourceInfo': fields.ListOfObjectsField(
            'VirtualStorageResourceInfoV2', nullable=True),
        # NOTE: vnfcInfo exists in SOL002 only.
        'vnfcInfo': fields.ListOfObjectsField('VnfcInfoV2', nullable=True),
    }


@base.TackerObjectRegistry.register
class VnfInstanceV2_Links(base.TackerObject):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'self': fields.ObjectField('Link', nullable=False),
        'indicators': fields.ObjectField('Link', nullable=True),
        'instantiate': fields.ObjectField('Link', nullable=True),
        'terminate': fields.ObjectField('Link', nullable=True),
        'scale': fields.ObjectField('Link', nullable=True),
        'scaleToLevel': fields.ObjectField('Link', nullable=True),
        'changeFlavour': fields.ObjectField('Link', nullable=True),
        'heal': fields.ObjectField('Link', nullable=True),
        'operate': fields.ObjectField('Link', nullable=True),
        'changeExtConn': fields.ObjectField('Link', nullable=True),
        'createSnapshot': fields.ObjectField('Link', nullable=True),
        'revertToSnapshot': fields.ObjectField('Link', nullable=True),
    }
