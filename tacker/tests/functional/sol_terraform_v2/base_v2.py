# Copyright (C) 2023 Nippon Telegraph and Telephone Corporation
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
from oslo_config import cfg

from tacker.sol_refactored import objects
from tacker.tests.functional import base_v2
from tacker import version


class BaseVnfLcmTerraformV2Test(base_v2.BaseTackerTestV2):

    @classmethod
    def setUpClass(cls):
        super(BaseVnfLcmTerraformV2Test, cls).setUpClass()
        """Base test case class for SOL v2 terraform functional tests."""

        cfg.CONF(args=['--config-file', '/etc/tacker/tacker.conf'],
                 project='tacker',
                 version='%%prog %s' % version.version_info.release_string())
        objects.register_all()
