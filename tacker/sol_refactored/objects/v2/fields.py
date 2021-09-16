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

from tacker.sol_refactored.objects import fields


# NFV-SOL 005
# - v2.7.1 9.5.4.3 (API version: 2.0.0)
# - v2.8.1 9.5.4.3 (API version: 2.1.0)
# - v3.3.1 9.5.4.3 (API version: 2.1.0)
class PackageOnboardingStateType(fields.BaseTackerEnum):
    CREATED = 'CREATED'
    UPLOADING = 'UPLOADING'
    PROCESSING = 'PROCESSING'
    ONBOARDED = 'ONBOARDED'
    ERROR = 'ERROR'

    ALL = (CREATED, UPLOADING, PROCESSING, ONBOARDED, ERROR)


class PackageOnboardingStateTypeField(fields.BaseEnumField):
    AUTO_TYPE = PackageOnboardingStateType()


# NFV-SOL 005
# - v2.7.1 9.5.4.4 (API version: 2.0.0)
# - v2.8.1 9.5.4.4 (API version: 2.1.0)
# - v3.3.1 9.5.4.4 (API version: 2.1.0)
class PackageOperationalStateType(fields.BaseTackerEnum):
    ENABLED = 'ENABLED'
    DISABLED = 'DISABLED'

    ALL = (ENABLED, DISABLED)


class PackageOperationalStateTypeField(fields.BaseEnumField):
    AUTO_TYPE = PackageOperationalStateType()


# NFV-SOL 005
# - v2.7.1 9.5.4.5 (API version: 2.0.0)
# - v2.8.1 9.5.4.5 (API version: 2.1.0)
# - v3.3.1 9.5.4.5 (API version: 2.1.0)
class PackageUsageStateType(fields.BaseTackerEnum):
    IN_USE = 'IN_USE'
    NOT_IN_USE = 'NOT_IN_USE'

    ALL = (IN_USE, NOT_IN_USE)


class PackageUsageStateTypeField(fields.BaseEnumField):
    AUTO_TYPE = PackageUsageStateType()


# NFV-SOL 005
# - v2.7.1 9.5.4.6 (API version: 2.0.0)
# - v2.8.1 9.5.4.6 (API version: 2.1.0)
# - v3.3.1 9.5.4.6 (API version: 2.1.0)
class PackageChangeType(fields.BaseTackerEnum):
    OP_STATE_CHANGE = 'OP_STATE_CHANGE'
    PKG_DELETE = 'PKG_DELETE'

    ALL = (OP_STATE_CHANGE, PKG_DELETE)


class PackageChangeTypeField(fields.BaseEnumField):
    AUTO_TYPE = PackageChangeType()


# NFV-SOL 003
# - v3.3.1 5.5.4.3 (API version: 2.0.0)
class VnfOperationalStateType(fields.BaseTackerEnum):
    STARTED = 'STARTED'
    STOPPED = 'STOPPED'

    ALL = (STARTED, STOPPED)


class VnfOperationalStateTypeField(fields.BaseEnumField):
    AUTO_TYPE = VnfOperationalStateType()


# NFV-SOL 003
# - v3.3.1 5.5.4.4 (API version: 2.0.0)
class StopType(fields.BaseTackerEnum):
    FORCEFUL = 'FORCEFUL'
    GRACEFUL = 'GRACEFUL'

    ALL = (FORCEFUL, GRACEFUL)


class StopTypeField(fields.BaseEnumField):
    AUTO_TYPE = StopType()


# NFV-SOL 003
# - v3.3.1 5.5.4.5 (API version: 2.0.0)
class LcmOperationStateType(fields.BaseTackerEnum):
    STARTING = 'STARTING'
    PROCESSING = 'PROCESSING'
    COMPLETED = 'COMPLETED'
    FAILED_TEMP = 'FAILED_TEMP'
    FAILED = 'FAILED'
    ROLLING_BACK = 'ROLLING_BACK'
    ROLLED_BACK = 'ROLLED_BACK'

    ALL = (STARTING, PROCESSING, COMPLETED, FAILED_TEMP, FAILED,
           ROLLING_BACK, ROLLED_BACK)


class LcmOperationStateTypeField(fields.BaseEnumField):
    AUTO_TYPE = LcmOperationStateType()


# NFV-SOL 003
# - v3.3.1 5.5.4.6 (API version: 2.0.0)
class CancelModeType(fields.BaseTackerEnum):
    GRACEFUL = 'GRACEFUL'
    FORCEFUL = 'FORCEFUL'

    ALL = (GRACEFUL, FORCEFUL)


class CancelModeTypeField(fields.BaseEnumField):
    AUTO_TYPE = CancelModeType()


# NFV-SOL 003
# - v3.3.1 5.5.4.7 (API version: 2.0.0)
class LcmOperationType(fields.BaseTackerEnum):
    INSTANTIATE = 'INSTANTIATE'
    SCALE = 'SCALE'
    SCALE_TO_LEVEL = 'SCALE_TO_LEVEL'
    CHANGE_FLAVOUR = 'CHANGE_FLAVOUR'
    TERMINATE = 'TERMINATE'
    HEAL = 'HEAL'
    OPERATE = 'OPERATE'
    CHANGE_EXT_CONN = 'CHANGE_EXT_CONN'
    MODIFY_INFO = 'MODIFY_INFO'
    CREATE_SNAPSHOT = 'CREATE_SNAPSHOT'
    REVERT_TO_SNAPSHOT = 'REVERT_TO_SNAPSHOT'
    CHANGE_VNFPKG = 'CHANGE_VNFPKG'

    ALL = (INSTANTIATE, SCALE, SCALE_TO_LEVEL, CHANGE_FLAVOUR,
           TERMINATE, HEAL, OPERATE, CHANGE_EXT_CONN, MODIFY_INFO,
           CREATE_SNAPSHOT, REVERT_TO_SNAPSHOT, CHANGE_VNFPKG)


class LcmOperationTypeField(fields.BaseEnumField):
    AUTO_TYPE = LcmOperationType()


# NFV-SOL 003
# - v3.3.1 5.5.4.8 (API version: 2.0.0)
class LcmOpOccNotificationVerbosityType(fields.BaseTackerEnum):
    FULL = 'FULL'
    SHORT = 'SHORT'

    ALL = (FULL, SHORT)


class LcmOpOccNotificationVerbosityTypeField(fields.BaseEnumField):
    AUTO_TYPE = LcmOpOccNotificationVerbosityType()
