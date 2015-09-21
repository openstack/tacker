# Copyright 2015 Brocade Communications System, Inc.
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

import time

from oslo_config import cfg
from tempest_lib.tests import base

from tacker import version
from tackerclient.v1_0 import client as tacker_client

CONF = cfg.CONF


class BaseTackerTest(base.TestCase):
    """Base test case class for all Tacker API tests."""

    @classmethod
    def setUpClass(cls):
        core_opts = [
            cfg.StrOpt('username', default='tacker',
                       help=('The uuid of the admin nova tenant')),
            cfg.StrOpt('password', default = 'devstack',
                       help=('The uuid of the admin nova tenant')),
            cfg.StrOpt('project_name', default = 'service',
                       help=('The uuid of the admin nova tenant')),
            cfg.StrOpt('auth_uri', default='http://127.0.0.1:5000',
                       help=('URL for connection to nova')),
        ]

        keystone_authtoken = cfg.OptGroup(name='keystone_authtoken',
                                          title='keystone options')
        # Register the configuration options
        cfg.CONF.register_opts(core_opts, group = keystone_authtoken)

        kwargs = {}

        cfg.CONF(args = ['--config-file', '/etc/tacker/tacker.conf'],
                 project='tacker',
                 version='%%prog %s' % version.version_info.release_string(),
                 **kwargs)

        cls.client = cls.tackerclient()

    @classmethod
    def tackerclient(cls):
        username = cfg.CONF.keystone_authtoken.username
        password = cfg.CONF.keystone_authtoken.password
        tenant_name = cfg.CONF.keystone_authtoken.project_name
        auth_uri = cfg.CONF.keystone_authtoken.auth_uri + '/v2.0'
        return tacker_client.Client(username=username, password=password,
                                 tenant_name=tenant_name,
                                 auth_url=auth_uri)

    @classmethod
    def wait_until_vnf_status(cls, vnf_id, target_status, timeout):
        start_time = int(time.time())
        while True:
                vnf_result = cls.client.show_vnf(vnf_id)
                status = vnf_result['vnf']['status']
                if (status == target_status) or ((int(time.time()) -
                                            start_time) > timeout):
                    break
                time.sleep(5)

    @classmethod
    def wait_until_vnf_active(cls, vnf_id, timeout):
        cls.wait_until_vnf_status(vnf_id,'ACTIVE',timeout)