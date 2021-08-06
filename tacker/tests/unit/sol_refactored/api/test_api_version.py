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

from unittest import mock

from tacker.sol_refactored.api import api_version
from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.tests import base


class TestAPIVersion(base.BaseTestCase):

    def test_init_null(self):
        vers = api_version.APIVersion()
        self.assertTrue(vers.is_null())

    @mock.patch.object(api_version, 'supported_versions',
                  new=["3.1.4159", "2.0.0"])
    def test_init(self):
        for vers, vers_str in [("2.0.0", "2.0.0"),
                               ("3.1.4159", "3.1.4159"),
                               ("2.0.0-impl:foobar", "2.0.0")]:
            v = api_version.APIVersion(vers)
            self.assertEqual(str(v), vers_str)

    def test_init_exceptions(self):
        self.assertRaises(sol_ex.InvalidAPIVersionString,
                          api_version.APIVersion, "0.1.2")

        self.assertRaises(sol_ex.APIVersionNotSupported,
                          api_version.APIVersion, "9.9.9")

    @mock.patch.object(api_version, 'supported_versions',
                  new=["1.3.0", "1.3.1", "2.0.0"])
    def test_compare(self):
        self.assertTrue(api_version.APIVersion("1.3.0") <
                        api_version.APIVersion("1.3.1"))

        self.assertTrue(api_version.APIVersion("2.0.0") >
                        api_version.APIVersion("1.3.1"))

    @mock.patch.object(api_version, 'supported_versions',
                  new=["1.3.0", "1.3.1", "2.0.0"])
    def test_matches(self):
        vers = api_version.APIVersion("2.0.0")
        self.assertTrue(vers.matches(api_version.APIVersion("1.3.0"),
                                     api_version.APIVersion()))

        self.assertFalse(vers.matches(api_version.APIVersion(),
                                      api_version.APIVersion("1.3.1")))
