# Copyright (c) 2012 OpenStack Foundation
# Copyright (C) 2022 Nippon Telegraph and Telephone Corporation
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


import os
from oslo_log import log as logging
import unittest

from tacker.agent.linux import utils
import tacker.privileged.linux_cmd
from tacker.tests import base


LOG = logging.getLogger(__name__)

# Use env 'PWD' to check if tests are run on zuul because we cannot run the
# tests require root privileges. Skip them on zuul, but still run on
# localhost to test privsep features.
_PWD = os.environ['PWD']
_PWD_ZUUL = "/home/zuul/src/opendev.org/openstack/tacker"


class PrivsepTest(base.BaseTestCase):
    """Simple unit test to test the basic privsep mechanism

    Essentially hello-world. Just run a command as root and check that
    it actually *did* run as root.
    """

    def setUp(self):
        super(PrivsepTest, self).setUp()

    @unittest.skipIf(_PWD == _PWD_ZUUL or os.getlogin() != 'stack',
            "Failed on zuul or non-devstack env for root privilege")
    def test_privsep_ls(self):
        """Run ls with root privilege

        This ls command is expected to be run on `/`.
        """

        ls = tacker.privileged.linux_cmd.ls()
        # The result is a series of dirs on '/' and separated with '\n' like
        # as 'bin\nboot\ndev\netc\n...'.
        res = ls[0].split('\n')

        # 'boot' dir must be under '/'.
        self.assertIn('boot', res)

    @unittest.skipIf(_PWD == _PWD_ZUUL or os.getlogin() != 'stack',
            "Failed on zuul or non-devstack env for root privilege")
    def test_privsep_pwd(self):
        """Run pwd with root privilege

        This ls command is expected to be run on `/`.
        """
        res = tacker.privileged.linux_cmd.pwd()[0]
        self.assertEqual('/\n', res)

    @unittest.skipIf(_PWD == _PWD_ZUUL or os.getlogin() != 'stack',
            "Failed on zuul or non-devstack env for root privilege")
    def test_rootwrap(self):
        """Confirm a command can be run with tacker-rootwrap

        pwd is used as a harmless command in this test and defined in
        '/etc/tacker/rootwrap.d/tacker.filters' as a CommandFilter.
        """

        root_helper = ["sudo", "tacker-rootwrap",
                       "/etc/tacker/rootwrap.conf"]
        cmd = "pwd"

        actual = utils.execute(root_helper + [cmd])
        expected = utils.execute([cmd])

        self.assertEqual(expected, actual)
