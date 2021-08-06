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


import re

from tacker.sol_refactored.common import exceptions as sol_ex


supported_versions_v1 = {
    'uriPrefix': '/vnflcm/v1',
    'apiVersions': [
        {'version': '1.3.0', 'isDeprecated': False}
    ]
}

supported_versions_v2 = {
    'uriPrefix': '/vnflcm/v2',
    'apiVersions': [
        {'version': '2.0.0', 'isDeprecated': False}
    ]
}

CURRENT_VERSION = '2.0.0'

supported_versions = [
    item['version'] for item in supported_versions_v2['apiVersions']
]


class APIVersion(object):

    def __init__(self, version_string=None):
        self.ver_major = 0
        self.ver_minor = 0
        self.ver_patch = 0

        if version_string is None:
            return

        version_string = self._get_version_id(version_string)
        match = re.match(r"^([1-9]\d*)\.([1-9]\d*|0)\.([1-9]\d*|0)$",
                         version_string)
        if match:
            self.ver_major = int(match.group(1))
            self.ver_minor = int(match.group(2))
            self.ver_patch = int(match.group(3))
        else:
            raise sol_ex.InvalidAPIVersionString(version=version_string)

        if version_string not in supported_versions:
            raise sol_ex.APIVersionNotSupported(version=version_string)

    def _get_version_id(self, version_string):
        # version example (see. SOL013 Table 4.2.2-1)
        # `1.2.0` or `1.2.0-impl:example.com:myProduct:4`
        # This method checks the later case and return the part of
        # version identifier. check is loose.
        if '-' not in version_string:
            return version_string
        items = version_string.split('-')
        if len(items) == 2 and items[1].startswith("impl:"):
            return items[0]
        raise sol_ex.InvalidAPIVersionString(version=version_string)

    def is_null(self):
        return (self.ver_major, self.ver_minor, self.ver_patch) == (0, 0, 0)

    def __str__(self):
        return "%d.%d.%d" % (self.ver_major, self.ver_minor, self.ver_patch)

    def __lt__(self, other):
        return ((self.ver_major, self.ver_minor, self.ver_patch) <
                (other.ver_major, other.ver_minor, other.ver_patch))

    def __eq__(self, other):
        return ((self.ver_major, self.ver_minor, self.ver_patch) ==
                (other.ver_major, other.ver_minor, other.ver_patch))

    def __gt__(self, other):
        return ((self.ver_major, self.ver_minor, self.ver_patch) >
                (other.ver_major, other.ver_minor, other.ver_patch))

    def __le__(self, other):
        return self < other or self == other

    def __ne__(self, other):
        return not self.__eq__(other)

    def __ge__(self, other):
        return self > other or self == other

    def matches(self, min_version, max_version):
        if self.is_null():
            return False
        if max_version.is_null() and min_version.is_null():
            return True
        elif max_version.is_null():
            return min_version <= self
        elif min_version.is_null():
            return self <= max_version
        else:
            return min_version <= self <= max_version
