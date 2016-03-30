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

from tacker.tests import constants
from tacker import version

from tackerclient.v1_0 import client as tacker_client

CONF = cfg.CONF


class BaseTackerTest(base.TestCase):
    """Base test case class for all Tacker API tests."""

    @classmethod
    def setUpClass(cls):
        core_opts = [
            cfg.StrOpt('username', default='tacker',
                       help=('Username to use for tacker API requests')),
            cfg.StrOpt('password', default = 'devstack',
                       help=('Password to use for tacker API requests')),
            cfg.StrOpt('project_name', default = 'service',
                       help=('Project name to use for tacker API requests')),
            cfg.StrOpt('auth_uri', default='http://127.0.0.1:5000',
                       help=('The keystone auth URI')),
        ]

        keystone_authtoken = cfg.OptGroup(name='keystone_authtoken',
                                          title='keystone options')
        # Register the configuration options
        cfg.CONF.register_opts(core_opts, group=keystone_authtoken)

        kwargs = {}

        cfg.CONF(args=['--config-file', '/etc/tacker/tacker.conf'],
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
    def wait_until_vnf_status(cls, vnf_id, target_status, timeout,
                              sleep_interval):
        start_time = int(time.time())
        while True:
                vnf_result = cls.client.show_vnf(vnf_id)
                status = vnf_result['vnf']['status']
                if (status == target_status) or (
                        (int(time.time()) - start_time) > timeout):
                    break
                time.sleep(sleep_interval)

        if (status == target_status):
            return target_status

    @classmethod
    def wait_until_vnf_active(cls, vnf_id, timeout, sleep_interval):
        return cls.wait_until_vnf_status(vnf_id, 'ACTIVE', timeout,
                                         sleep_interval)

    @classmethod
    def wait_until_vnf_dead(cls, vnf_id, timeout, sleep_interval):
        return cls.wait_until_vnf_status(vnf_id, 'DEAD', timeout,
                                         sleep_interval)

    def validate_vnf_instance(self, vnfd_instance, vnf_instance):
        self.assertIsNotNone(vnf_instance)
        self.assertIsNotNone(vnf_instance['vnf']['id'])
        self.assertIsNotNone(vnf_instance['vnf']['instance_id'])
        self.assertEqual(vnf_instance['vnf']['vnfd_id'], vnfd_instance[
            'vnfd']['id'])

    def verify_vnf_restart(self, vnfd_instance, vnf_instance):
        vnf_id = vnf_instance['vnf']['id']
        vnf_current_status = self.wait_until_vnf_active(
            vnf_id,
            constants.VNF_CIRROS_CREATE_TIMEOUT,
            constants.ACTIVE_SLEEP_TIME)
        self.assertEqual(vnf_current_status, 'ACTIVE')
        self.validate_vnf_instance(vnfd_instance, vnf_instance)
        self.assertIsNotNone(self.client.show_vnf(vnf_id)['vnf']['mgmt_url'])

        vnf_current_status = self.wait_until_vnf_dead(
            vnf_id,
            constants.VNF_CIRROS_DEAD_TIMEOUT,
            constants.DEAD_SLEEP_TIME)
        self.assertEqual(vnf_current_status, 'DEAD')
        vnf_current_status = self.wait_until_vnf_active(
            vnf_id,
            constants.VNF_CIRROS_CREATE_TIMEOUT,
            constants.ACTIVE_SLEEP_TIME)
        self.assertEqual(vnf_current_status, 'ACTIVE')
        self.validate_vnf_instance(vnfd_instance, vnf_instance)

    def get_vim(self, vim_list, vim_name):
        if len(vim_list.values()) == 0:
            assert False, "vim_list is Empty: Default VIM is missing"

        for vim_list in vim_list.values():
            for vim in vim_list:
                if vim['name'] == vim_name:
                    return vim
        return None
