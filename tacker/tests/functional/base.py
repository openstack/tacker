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

from novaclient import client as nova_client
from oslo_config import cfg
from tempest.lib import base
import yaml

from tacker.common.exceptions import TackerException
from tacker.tests import constants
from tacker.tests.utils import read_file
from tacker import version

from tackerclient.v1_0 import client as tacker_client

CONF = cfg.CONF


class BaseTackerTest(base.BaseTestCase):
    """Base test case class for all Tacker API tests."""

    @classmethod
    def setUpClass(cls):
        super(BaseTackerTest, cls).setUpClass()
        kwargs = {}

        cfg.CONF(args=['--config-file', '/etc/tacker/tacker.conf'],
                 project='tacker',
                 version='%%prog %s' % version.version_info.release_string(),
                 **kwargs)

        cls.client = cls.tackerclient()

    @classmethod
    def get_credentials(cls):
        vim_params = yaml.load(read_file('local-vim.yaml'))
        vim_params['auth_url'] += '/v2.0'
        return vim_params

    @classmethod
    def tackerclient(cls):
        vim_params = cls.get_credentials()
        return tacker_client.Client(username=vim_params['username'],
                                    password=vim_params['password'],
                                    tenant_name=vim_params['project_name'],
                                    auth_url=vim_params['auth_url'])

    @classmethod
    def novaclient(cls):
        vim_params = cls.get_credentials()
        return nova_client.Client('2', vim_params['username'],
                                  vim_params['password'],
                                  vim_params['project_name'],
                                  vim_params['auth_url'])

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
    def wait_until_vnf_delete(cls, vnf_id, timeout):
        start_time = int(time.time())
        while True:
            try:
                vnf_result = cls.client.show_vnf(vnf_id)
                time.sleep(1)
            except Exception:
                return
            status = vnf_result['vnf']['status']
            if (status != 'PENDING_DELETE') or ((
                    int(time.time()) - start_time) > timeout):
                raise TackerException(_("Failed with status: %s"), status)

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
        self.assertEqual('ACTIVE', vnf_current_status)
        self.validate_vnf_instance(vnfd_instance, vnf_instance)
        self.assertIsNotNone(self.client.show_vnf(vnf_id)['vnf']['mgmt_url'])

        vnf_current_status = self.wait_until_vnf_dead(
            vnf_id,
            constants.VNF_CIRROS_DEAD_TIMEOUT,
            constants.DEAD_SLEEP_TIME)
        self.assertEqual('DEAD', vnf_current_status)
        vnf_current_status = self.wait_until_vnf_active(
            vnf_id,
            constants.VNF_CIRROS_CREATE_TIMEOUT,
            constants.ACTIVE_SLEEP_TIME)
        self.assertEqual('ACTIVE', vnf_current_status)
        self.validate_vnf_instance(vnfd_instance, vnf_instance)

    def get_vim(self, vim_list, vim_name):
        if len(vim_list.values()) == 0:
            assert False, "vim_list is Empty: Default VIM is missing"

        for vim_list in vim_list.values():
            for vim in vim_list:
                if vim['name'] == vim_name:
                    return vim
        return None
