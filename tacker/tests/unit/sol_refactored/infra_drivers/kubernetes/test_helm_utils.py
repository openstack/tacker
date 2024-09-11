# Copyright (C) 2024 Nippon Telegraph and Telephone Corporation
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

from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.infra_drivers.kubernetes import helm_utils
from tacker.tests.unit import base


RELEASE_NAME = "vnf0e222bb1a81b45f5ba51fef83559caf6"
NAMESPACE = "default"


class FakeCompletedProcess(object):

    def __init__(self, returncode, stdout, stderr):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class TestHelmClient(base.TestCase):

    def setUp(self):
        super(TestHelmClient, self).setUp()
        self.driver = helm_utils.HelmClient(mock.Mock())

    @mock.patch.object(helm_utils.HelmClient, '_execute_command')
    def test_is_release_exist(self, mock_execute_command):

        mock_execute_command.return_value = FakeCompletedProcess(
            0, 'Unit Test', '')

        # run is_release_exist
        self.assertTrue(self.driver.is_release_exist(RELEASE_NAME, NAMESPACE))

    @mock.patch.object(helm_utils.HelmClient, '_execute_command')
    def test_is_release_exist_release_not_found(self, mock_execute_command):

        mock_execute_command.return_value = FakeCompletedProcess(
            1, '', 'Error: release: not found\n')

        # run is_release_exist
        self.assertFalse(self.driver.is_release_exist(RELEASE_NAME, NAMESPACE))

    @mock.patch.object(helm_utils.HelmClient, '_execute_command')
    def test_is_release_exist_other_error(self, mock_execute_command):

        mock_execute_command.return_value = FakeCompletedProcess(
            1, '', 'Error: Kubernetes cluster unreachable\n')

        # run is_release_exist
        self.assertRaises(
            sol_ex.HelmOperationFailed,
            self.driver.is_release_exist, RELEASE_NAME, NAMESPACE)
