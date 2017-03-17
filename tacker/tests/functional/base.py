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
import yaml

from keystoneauth1.identity import v3
from keystoneauth1 import session
from neutronclient.v2_0 import client as neutron_client
from novaclient import client as nova_client
from oslo_config import cfg
from tempest.lib import base

from tacker.plugins.common import constants as evt_constants
from tacker.tests import constants
from tacker.tests.functional import clients
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
        cls.h_client = cls.heatclient()

    @classmethod
    def get_credentials(cls):
        vim_params = yaml.safe_load(read_file('local-vim.yaml'))
        vim_params['auth_url'] += '/v3'
        return vim_params

    @classmethod
    def tackerclient(cls):
        vim_params = cls.get_credentials()
        auth = v3.Password(auth_url=vim_params['auth_url'],
            username=vim_params['username'],
            password=vim_params['password'],
            project_name=vim_params['project_name'],
            user_domain_name=vim_params['user_domain_name'],
            project_domain_name=vim_params['project_domain_name'])
        auth_ses = session.Session(auth=auth)
        return tacker_client.Client(session=auth_ses)

    @classmethod
    def novaclient(cls):
        vim_params = cls.get_credentials()
        auth = v3.Password(auth_url=vim_params['auth_url'],
            username=vim_params['username'],
            password=vim_params['password'],
            project_name=vim_params['project_name'],
            user_domain_name=vim_params['user_domain_name'],
            project_domain_name=vim_params['project_domain_name'])
        auth_ses = session.Session(auth=auth)
        return nova_client.Client(constants.NOVA_CLIENT_VERSION,
                                  session=auth_ses)

    @classmethod
    def neutronclient(cls):
        vim_params = cls.get_credentials()
        auth = v3.Password(auth_url=vim_params['auth_url'],
            username=vim_params['username'],
            password=vim_params['password'],
            project_name=vim_params['project_name'],
            user_domain_name=vim_params['user_domain_name'],
            project_domain_name=vim_params['project_domain_name'])
        auth_ses = session.Session(auth=auth)
        return neutron_client.Client(session=auth_ses)

    @classmethod
    def heatclient(cls):
        data = yaml.safe_load(read_file('local-vim.yaml'))
        data['auth_url'] = data['auth_url'] + '/v3'
        domain_name = data.pop('domain_name')
        data['user_domain_name'] = domain_name
        data['project_domain_name'] = domain_name
        return clients.OpenstackClients(auth_attr=data).heat

    def wait_until_vnf_status(self, vnf_id, target_status, timeout,
                              sleep_interval):
        start_time = int(time.time())
        while True:
                vnf_result = self.client.show_vnf(vnf_id)
                status = vnf_result['vnf']['status']
                if (status == target_status) or (
                        (int(time.time()) - start_time) > timeout):
                    break
                time.sleep(sleep_interval)

        self.assertEqual(status, target_status,
                         "vnf %(vnf_id)s with status %(status)s is"
                         " expected to be %(target)s" %
                         {"vnf_id": vnf_id, "status": status,
                          "target": target_status})

    def wait_until_vnf_active(self, vnf_id, timeout, sleep_interval):
        self.wait_until_vnf_status(vnf_id, 'ACTIVE', timeout,
                                   sleep_interval)

    def wait_until_vnf_delete(self, vnf_id, timeout):
        start_time = int(time.time())
        while True:
            try:
                vnf_result = self.client.show_vnf(vnf_id)
                time.sleep(1)
            except Exception:
                return
            status = vnf_result['vnf']['status']
            if (status != 'PENDING_DELETE') or ((
                    int(time.time()) - start_time) > timeout):
                raise Exception("Failed with status: %s" % status)

    def wait_until_vnf_dead(self, vnf_id, timeout, sleep_interval):
        self.wait_until_vnf_status(vnf_id, 'DEAD', timeout,
                                   sleep_interval)

    def validate_vnf_instance(self, vnfd_instance, vnf_instance):
        self.assertIsNotNone(vnf_instance)
        self.assertIsNotNone(vnf_instance['vnf']['id'])
        self.assertIsNotNone(vnf_instance['vnf']['instance_id'])
        self.assertEqual(vnf_instance['vnf']['vnfd_id'], vnfd_instance[
            'vnfd']['id'])

    def verify_vnf_restart(self, vnfd_instance, vnf_instance):
        vnf_id = vnf_instance['vnf']['id']
        self.wait_until_vnf_active(
            vnf_id,
            constants.VNF_CIRROS_CREATE_TIMEOUT,
            constants.ACTIVE_SLEEP_TIME)
        self.validate_vnf_instance(vnfd_instance, vnf_instance)
        self.assertIsNotNone(self.client.show_vnf(vnf_id)['vnf']['mgmt_url'])

        self.wait_until_vnf_dead(
            vnf_id,
            constants.VNF_CIRROS_DEAD_TIMEOUT,
            constants.DEAD_SLEEP_TIME)
        self.wait_until_vnf_active(
            vnf_id,
            constants.VNF_CIRROS_CREATE_TIMEOUT,
            constants.ACTIVE_SLEEP_TIME)
        self.validate_vnf_instance(vnfd_instance, vnf_instance)

    def verify_vnf_monitor_events(self, vnf_id, vnf_state_list):
        for state in vnf_state_list:
            params = {'resource_id': vnf_id, 'resource_state': state,
                      'event_type': evt_constants.RES_EVT_MONITOR}
            vnf_evt_list = self.client.list_vnf_events(**params)
            mesg = ("%s - state transition expected." % state)
            self.assertIsNotNone(vnf_evt_list['vnf_events'], mesg)

    def verify_vnf_crud_events(self, vnf_id, evt_type, res_state,
                               tstamp=None, cnt=1):
        params = {'resource_id': vnf_id,
                  'resource_state': res_state,
                  'resource_type': evt_constants.RES_TYPE_VNF,
                  'event_type': evt_type}
        if tstamp:
            params['timestamp'] = tstamp

        vnf_evt_list = self.client.list_vnf_events(**params)

        self.assertIsNotNone(vnf_evt_list['vnf_events'],
                             "List of VNF events are Empty")
        self.assertEqual(cnt, len(vnf_evt_list['vnf_events']))

    def verify_vnfd_events(self, vnfd_id, evt_type, res_state,
                           tstamp=None, cnt=1):
        params = {'resource_id': vnfd_id,
                  'resource_state': res_state,
                  'resource_type': evt_constants.RES_TYPE_VNFD,
                  'event_type': evt_type}
        if tstamp:
            params['timestamp'] = tstamp

        vnfd_evt_list = self.client.list_vnfd_events(**params)

        self.assertIsNotNone(vnfd_evt_list['vnfd_events'],
                             "List of VNFD events are Empty")
        self.assertEqual(cnt, len(vnfd_evt_list['vnfd_events']))

    def get_vim(self, vim_list, vim_name):
        if len(vim_list.values()) == 0:
            assert False, "vim_list is Empty: Default VIM is missing"

        for vim_list in vim_list.values():
            for vim in vim_list:
                if vim['name'] == vim_name:
                    return vim
        return None

    def verify_antispoofing_in_stack(self, stack_id, resource_name):
        resource_types = self.h_client.resources
        resource_details = resource_types.get(stack_id=stack_id,
                                              resource_name=resource_name)
        resource_dict = resource_details.to_dict()
        self.assertTrue(resource_dict['attributes']['port_security_enabled'])
