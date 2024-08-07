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


# NFV-SOL 003
# - v2.6.1 9.5.4.3 (API version: 1.3.0)
# - v2.7.1 9.5.4.3 (API version: 1.3.0)
# - v2.8.1 9.5.4.3 (API version: 1.3.0)
# - v3.3.1 9.5.4.3 (API version: 1.4.0)
class GrantedLcmOperationType(fields.BaseTackerEnum):
    INSTANTIATE = 'INSTANTIATE'
    SCALE = 'SCALE'
    SCALE_TO_LEVEL = 'SCALE_TO_LEVEL'
    CHANGE_FLAVOUR = 'CHANGE_FLAVOUR'
    TERMINATE = 'TERMINATE'
    HEAL = 'HEAL'
    OPERATE = 'OPERATE'
    CHANGE_EXT_CONN = 'CHANGE_EXT_CONN'
    CHANGE_VNFPKG = 'CHANGE_VNFPKG'  # since 1.4.0
    CREATE_SNAPSHOT = 'CREATE_SNAPSHOT'  # since 1.4.0
    REVERT_TO_SNAPSHOT = 'REVERT_TO_SNAPSHOT'  # since 1.4.0

    ALL = (INSTANTIATE, SCALE, SCALE_TO_LEVEL, CHANGE_FLAVOUR,
           TERMINATE, HEAL, OPERATE, CHANGE_EXT_CONN, CHANGE_VNFPKG,
           CREATE_SNAPSHOT, REVERT_TO_SNAPSHOT)


class GrantedLcmOperationTypeField(fields.BaseEnumField):
    AUTO_TYPE = GrantedLcmOperationType()


# NFV-SOL 003
# - v2.6.1 7.5.4.3 (API version: 1.2.0)
# - v2.7.1 7.5.4.3 (API version: 1.3.0)
# - v2.8.1 7.5.4.3 (API version: 1.3.0)
# - v3.3.1 7.5.4.3 (API version: 1.3.0)
class PerceivedSeverityType(fields.BaseTackerEnum):
    CRITICAL = 'CRITICAL'
    MAJOR = 'MAJOR'
    MINOR = 'MINOR'
    WARNING = 'WARNING'
    INDETERMINATE = 'INDETERMINATE'
    CLEARED = 'CLEARED'

    ALL = (CRITICAL, MAJOR, MINOR, WARNING, INDETERMINATE, CLEARED)


class PerceivedSeverityTypeField(fields.BaseEnumField):
    AUTO_TYPE = PerceivedSeverityType()


# NFV-SOL 003
# - v2.6.1 7.5.4.5 (API version: 1.2.0)
# - v2.7.1 7.5.4.5 (API version: 1.3.0)
# - v2.8.1 7.5.4.5 (API version: 1.3.0)
# - v3.3.1 7.5.4.5 (API version: 1.3.0)
class EventType(fields.BaseTackerEnum):
    COMMUNICATIONS_ALARM = 'COMMUNICATIONS_ALARM'
    PROCESSING_ERROR_ALARM = 'PROCESSING_ERROR_ALARM'
    ENVIRONMENTAL_ALARM = 'ENVIRONMENTAL_ALARM'
    QOS_ALARM = 'QOS_ALARM'
    EQUIPMENT_ALARM = 'EQUIPMENT_ALARM'

    ALL = (COMMUNICATIONS_ALARM, PROCESSING_ERROR_ALARM,
           ENVIRONMENTAL_ALARM, QOS_ALARM, EQUIPMENT_ALARM)


class EventTypeField(fields.BaseEnumField):
    AUTO_TYPE = EventType()


# NFV-SOL 003
# - v2.6.1 7.5.4.5 (API version: 1.2.0)
# - v2.7.1 7.5.4.5 (API version: 1.3.0)
# - v2.8.1 7.5.4.5 (API version: 1.3.0)
# - v3.3.1 7.5.4.5 (API version: 1.3.0)
class FaultyResourceType(fields.BaseTackerEnum):
    COMPUTE = 'COMPUTE'
    STORAGE = 'STORAGE'
    NETWORK = 'NETWORK'

    ALL = (COMPUTE, STORAGE, NETWORK)


class FaultyResourceTypeField(fields.BaseEnumField):
    AUTO_TYPE = FaultyResourceType()
