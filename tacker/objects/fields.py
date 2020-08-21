# Copyright 2018 NTT Data.
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

import uuid

from oslo_versionedobjects import fields


# Import fields from oslo.versionedobjects
StringField = fields.StringField
ListOfObjectsField = fields.ListOfObjectsField
ListOfStringsField = fields.ListOfStringsField
DictOfStringsField = fields.DictOfStringsField
DictOfNullableStringsField = fields.DictOfNullableStringsField
DateTimeField = fields.DateTimeField
BooleanField = fields.BooleanField
BaseEnumField = fields.BaseEnumField
Enum = fields.Enum
ObjectField = fields.ObjectField
IntegerField = fields.IntegerField
FieldType = fields.FieldType


class BaseTackerEnum(Enum):
    def __init__(self):
        super(BaseTackerEnum, self).__init__(valid_values=self.__class__.ALL)


class ContainerFormat(BaseTackerEnum):
    AKI = 'AKI'
    AMI = 'AMI'
    ARI = 'ARI'
    BARE = 'BARE'
    DOCKER = 'DOCKER'
    OVA = 'OVA'
    OVF = 'OVF'

    ALL = (AKI, AMI, ARI, BARE, DOCKER, OVA, OVF)


class ContainerFormatFields(BaseEnumField):
    AUTO_TYPE = ContainerFormat()


class DiskFormat(BaseTackerEnum):
    AKI = 'AKI'
    AMI = 'AMI'
    ARI = 'ARI'
    ISO = 'ISO'
    QCOW2 = 'QCOW2'
    RAW = 'RAW'
    VDI = 'VDI'
    VHD = 'VHD'
    VHDX = 'VHDX'
    VMDK = 'VMDK'

    ALL = (AKI, AMI, ARI, ISO, QCOW2, RAW, VDI, VHD, VHDX, VMDK)


class DiskFormatFields(BaseEnumField):
    AUTO_TYPE = DiskFormat()


class PackageOnboardingStateType(BaseTackerEnum):
    CREATED = 'CREATED'
    UPLOADING = 'UPLOADING'
    PROCESSING = 'PROCESSING'
    ONBOARDED = 'ONBOARDED'

    ALL = (CREATED, UPLOADING, PROCESSING, ONBOARDED)


class PackageOnboardingStateTypeField(BaseEnumField):
    AUTO_TYPE = PackageOnboardingStateType()


class PackageOperationalStateType(BaseTackerEnum):
    ENABLED = 'ENABLED'
    DISABLED = 'DISABLED'

    ALL = (ENABLED, DISABLED)


class PackageOperationalStateTypeField(BaseEnumField):
    AUTO_TYPE = PackageOperationalStateType()


class PackageUsageStateType(BaseTackerEnum):
    IN_USE = 'IN_USE'
    NOT_IN_USE = 'NOT_IN_USE'

    ALL = (IN_USE, NOT_IN_USE)


class PackageUsageStateTypeField(BaseEnumField):
    AUTO_TYPE = PackageUsageStateType()


class DictOfNullableField(fields.AutoTypedField):
    AUTO_TYPE = fields.Dict(fields.FieldType(), nullable=True)


class UUID(fields.UUID):
    def coerce(self, obj, attr, value):
        uuid.UUID(str(value))
        return str(value)


class UUIDField(fields.AutoTypedField):
    AUTO_TYPE = UUID()


class VnfInstanceState(BaseTackerEnum):
    INSTANTIATED = 'INSTANTIATED'
    NOT_INSTANTIATED = 'NOT_INSTANTIATED'

    ALL = (INSTANTIATED, NOT_INSTANTIATED)


class VnfInstanceStateField(BaseEnumField):
    AUTO_TYPE = VnfInstanceState()


class VnfInstanceTaskState(BaseTackerEnum):
    INSTANTIATING = 'INSTANTIATING'
    HEALING = 'HEALING'
    TERMINATING = 'TERMINATING'
    ERROR = 'ERROR'

    ALL = (INSTANTIATING, HEALING, TERMINATING, ERROR)


class VnfInstanceTaskStateField(BaseEnumField):
    AUTO_TYPE = VnfInstanceTaskState()


class VnfOperationalStateType(BaseTackerEnum):
    STARTED = 'STARTED'
    STOPPED = 'STOPPED'

    ALL = (STARTED, STOPPED)


class VnfOperationalStateTypeField(BaseEnumField):
    AUTO_TYPE = VnfOperationalStateType()


class IpAddressType(BaseTackerEnum):
    IPV4 = 'IPV4'
    IPV6 = 'IPV6'

    ALL = (IPV4, IPV6)


class IpAddressTypeField(BaseEnumField):
    AUTO_TYPE = IpAddressType()


class VnfInstanceTerminationType(BaseTackerEnum):
    FORCEFUL = 'FORCEFUL'
    GRACEFUL = 'GRACEFUL'

    ALL = (FORCEFUL, GRACEFUL)


class VnfInstanceTerminationTypeField(BaseEnumField):
    AUTO_TYPE = VnfInstanceTerminationType()


class VnfcState(BaseTackerEnum):
    STARTED = 'STARTED'
    STOPPED = 'STOPPED'

    ALL = (STARTED, STOPPED)


class InstanceOperationalState(BaseTackerEnum):
    STARTING = 'STARTING'
    PROCESSING = 'PROCESSING'
    COMPLETED = 'COMPLETED'
    FAILED_TEMP = 'FAILED_TEMP'
    ROLLING_BACK = 'ROLLING_BACK'
    ROLLED_BACK = 'ROLLED_BACK'

    ALL = (STARTING, PROCESSING, COMPLETED, FAILED_TEMP,
        ROLLING_BACK, ROLLED_BACK)


class InstanceOperationalStateField(BaseEnumField):
    AUTO_TYPE = InstanceOperationalState()


class InstanceOperation(BaseTackerEnum):
    INSTANTIATE = 'INSTANTIATE'
    SCALE = 'SCALE'
    TERMINATE = 'TERMINATE'
    HEAL = 'HEAL'
    MODIFY_INFO = 'MODIFY_INFO'

    ALL = (INSTANTIATE, SCALE,
        TERMINATE, HEAL, MODIFY_INFO)


class InstanceOperationField(BaseEnumField):
    AUTO_TYPE = InstanceOperation()


class LcmOccsOperationState(BaseTackerEnum):
    STARTING = 'STARTING'
    PROCESSING = 'PROCESSING'
    COMPLETED = 'COMPLETED'
    FAILED_TEMP = 'FAILED_TEMP'

    ALL = (STARTING, PROCESSING, COMPLETED, FAILED_TEMP)


class LcmOccsOperationType(BaseTackerEnum):
    INSTANTIATE = 'INSTANTIATE'
    TERMINATE = 'TERMINATE'
    HEAL = 'HEAL'

    ALL = (INSTANTIATE, TERMINATE, HEAL)


class LcmOccsNotificationStatus(BaseTackerEnum):
    START = 'START'
    RESULT = 'RESULT'

    ALL = (START, RESULT)


class ResourceChangeType(BaseTackerEnum):
    ADDED = 'ADDED'
    REMOVED = 'REMOVED'
    MODIFIED = 'MODIFIED'
    TEMPORARY = 'TEMPORARY'

    ALL = (ADDED, REMOVED, MODIFIED, TEMPORARY)


class LcmOccsNotificationType(BaseTackerEnum):
    VNF_OP_OCC_NOTIFICATION = 'VnfLcmOperationOccurrenceNotification'
    VNF_ID_CREATION_NOTIFICATION = 'VnfIdentifierCreationNotification'

    ALL = (VNF_OP_OCC_NOTIFICATION)


class VnfStatus(BaseTackerEnum):
    ACTIVE = 'ACTIVE'
    INACTIVE = 'INACTIVE'

    ALL = (ACTIVE, INACTIVE)


class InstanceOperation(BaseTackerEnum):
    MODIFY_INFO = 'MODIFY_INFO'
