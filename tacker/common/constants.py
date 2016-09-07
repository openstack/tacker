# Copyright (c) 2012 OpenStack Foundation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# TODO(salv-orlando): Verify if a single set of operational
# status constants is achievable

TYPE_BOOL = "bool"
TYPE_INT = "int"
TYPE_LONG = "long"
TYPE_FLOAT = "float"
TYPE_LIST = "list"
TYPE_DICT = "dict"

PAGINATION_INFINITE = 'infinite'

SORT_DIRECTION_ASC = 'asc'
SORT_DIRECTION_DESC = 'desc'

# attribute name for nova boot
ATTR_NAME_IMAGE = 'image'
ATTR_NAME_FLAVOR = 'flavor'
ATTR_NAME_META = 'meta'
ATTR_NAME_FILES = "files"
ATTR_NAME_RESERVEATION_ID = 'reservation_id'
ATTR_NAME_SECURITY_GROUPS = 'security_groups'
ATTR_NAME_USER_DATA = 'user_data'
ATTR_NAME_KEY_NAME = 'key_name'
ATTR_NAME_AVAILABILITY_ZONE = 'availability_zone'
ATTR_NAME_BLOCK_DEVICE_MAPPING = 'block_device_mapping'
ATTR_NAME_BLOCK_DEVICE_MAPPING_V2 = 'block_device_mapping_v2'
ATTR_NAME_NICS = 'nics'
ATTR_NAME_NIC = 'nic'
ATTR_NAME_SCHEDULER_HINTS = 'sheculer_hints'
ATTR_NAME_CONFIG_DRIVE = 'config_drive'
ATTR_NAME_DISK_CONFIG = 'disk_config'
