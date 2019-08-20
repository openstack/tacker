# Copyright 2017 99cloud, Inc.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
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

import ddt
import mock

from tacker import context
from tacker.extensions import vnfm
from tacker.tests.unit import base
from tacker.tests.unit.db import utils
from tacker.tests.unit.vnfm.infra_drivers.openstack.fixture_data import client
from tacker.tests.unit.vnfm.infra_drivers.openstack.fixture_data import \
    fixture_data_utils as fd_utils
from tacker.tests import uuidsentinel
from tacker.vnfm.infra_drivers.openstack import openstack


@ddt.ddt
class TestOpenStack(base.FixturedTestCase):
    client_fixture_class = client.ClientFixture

    def setUp(self):
        super(TestOpenStack, self).setUp()
        self.openstack = openstack.OpenStack()
        self.context = context.get_admin_context()
        self.url = client.HEAT_URL
        self.instance_uuid = uuidsentinel.instance_id
        self.stack_id = uuidsentinel.stack_id
        self.json_headers = {'content-type': 'application/json',
                             'location': 'http://heat-api/stacks/'
                             + self.instance_uuid + '/myStack/60f83b5e'}
        self._mock('tacker.common.clients.OpenstackClients.heat', self.cs)
        self.mock_log = mock.patch('tacker.vnfm.infra_drivers.openstack.'
                                   'openstack.LOG').start()
        mock.patch('time.sleep', return_value=None).start()

    def _response_in_wait_until_stack_ready(self, status_list,
                                            stack_outputs=True):
        # response for heat_client's get()
        for status in status_list:
            url = self.url + '/stacks/' + self.instance_uuid
            json = {'stack': fd_utils.get_dummy_stack(stack_outputs,
                                                      status=status)}
            self.requests_mock.register_uri('GET', url, json=json,
                                            headers=self.json_headers)

    def _response_in_resource_get(self, id, res_name=None):
        # response for heat_client's resource_get()
        if res_name:
            url = self.url + '/stacks/' + id + ('/myStack/60f83b5e/'
                                                'resources/') + res_name
        else:
            url = self.url + '/stacks/' + id

        json = {'resource': fd_utils.get_dummy_resource()}
        self.requests_mock.register_uri('GET', url, json=json,
                                        headers=self.json_headers)

    def test_create_wait(self):
        self._response_in_wait_until_stack_ready(["CREATE_IN_PROGRESS",
                                                 "CREATE_COMPLETE"])
        vnf_dict = utils.get_dummy_vnf(instance_id=self.instance_uuid)
        self.openstack.create_wait(None, None,
                                   vnf_dict, self.instance_uuid, None)
        self.mock_log.debug.assert_called_with('outputs %s',
                                         fd_utils.get_dummy_stack()['outputs'])
        self.assertEqual('{"VDU1": "192.168.120.216"}',
                         vnf_dict['mgmt_ip_address'])

    def test_create_wait_without_mgmt_ips(self):
        self._response_in_wait_until_stack_ready(["CREATE_IN_PROGRESS",
                                                 "CREATE_COMPLETE"],
                                                 stack_outputs=False)
        vnf_dict = utils.get_dummy_vnf(instance_id=self.instance_uuid)
        self.openstack.create_wait(None, None,
                                   vnf_dict, self.instance_uuid, None)
        self.mock_log.debug.assert_called_with('outputs %s',
                          fd_utils.get_dummy_stack(outputs=False)['outputs'])
        self.assertIsNone(vnf_dict['mgmt_ip_address'])

    def test_create_wait_with_scaling_group_names(self):
        self._response_in_wait_until_stack_ready(["CREATE_IN_PROGRESS",
                                                 "CREATE_COMPLETE"])
        self._response_in_resource_get(self.instance_uuid,
                                       res_name='SP1_group')
        url = self.url + '/stacks/' + self.stack_id + '/resources'
        json = {'resources': [fd_utils.get_dummy_resource()]}
        self.requests_mock.register_uri('GET', url, json=json,
                                        headers=self.json_headers)
        self._response_in_resource_get(self.stack_id)
        vnf_dict = utils.get_dummy_vnf(scaling_group=True)
        self.openstack.create_wait(None, None, vnf_dict, self.instance_uuid,
                                   None)
        self.assertEqual('{"vdu1": ["test1"]}', vnf_dict['mgmt_ip_address'])

    def test_create_wait_failed_with_stack_retries_0(self):
        self._response_in_wait_until_stack_ready(["CREATE_IN_PROGRESS"])
        vnf_dict = utils.get_dummy_vnf(instance_id=self.instance_uuid)
        self.assertRaises(vnfm.VNFCreateWaitFailed,
                          self.openstack.create_wait,
                          None, None, vnf_dict, self.instance_uuid, None)

    def test_create_wait_failed_with_stack_retries_not_0(self):
        self._response_in_wait_until_stack_ready(["CREATE_IN_PROGRESS",
                                                 "FAILED"])
        vnf_dict = utils.get_dummy_vnf(instance_id=self.instance_uuid)
        self.assertRaises(vnfm.VNFCreateWaitFailed,
                          self.openstack.create_wait,
                          None, None, vnf_dict, self.instance_uuid, {})

    def _exception_response(self):
        url = self.url + '/stacks/' + self.instance_uuid
        body = {"error": Exception("any stuff")}
        self.requests_mock.register_uri('GET', url, body=body,
                    status_code=404, headers=self.json_headers)

    def test_create_wait_with_exception(self):
        self._exception_response()
        vnf_dict = utils.get_dummy_vnf(instance_id=self.instance_uuid)
        self.assertRaises(vnfm.VNFCreateWaitFailed,
                          self.openstack.create_wait,
                          None, None, vnf_dict, self.instance_uuid, None)

    def test_delete_wait_failed_with_stack_retries_0(self):
        self._response_in_wait_until_stack_ready(["DELETE_IN_PROGRESS"])
        self.assertRaises(vnfm.VNFDeleteWaitFailed,
                          self.openstack.delete_wait,
                          None, None, self.instance_uuid, None, None)

    def test_delete_wait_stack_retries_not_0(self):
        self._response_in_wait_until_stack_ready(["DELETE_IN_PROGRESS",
                                                 "FAILED"])
        self.assertRaises(vnfm.VNFDeleteWaitFailed,
                          self.openstack.delete_wait,
                          None, None, self.instance_uuid, None, None)
        self.mock_log.warning.assert_called_once()

    def test_update_wait(self):
        self._response_in_wait_until_stack_ready(["CREATE_COMPLETE"])
        vnf_dict = utils.get_dummy_vnf(status='PENDING_UPDATE',
                                       instance_id=self.instance_uuid)
        self.openstack.update_wait(None, None, vnf_dict, None)
        self.mock_log.debug.assert_called_with('outputs %s',
                                    fd_utils.get_dummy_stack()['outputs'])
        self.assertEqual('{"VDU1": "192.168.120.216"}',
                         vnf_dict['mgmt_ip_address'])

    def test_heal_wait(self):
        self._response_in_wait_until_stack_ready(["UPDATE_IN_PROGRESS",
                                                 "UPDATE_COMPLETE"])
        vnf_dict = utils.get_dummy_vnf(status='PENDING_HEAL',
                                       instance_id=self.instance_uuid)
        self.openstack.heal_wait(None, None, vnf_dict, None)
        self.mock_log.debug.assert_called_with('outputs %s',
                                    fd_utils.get_dummy_stack()['outputs'])
        self.assertEqual('{"VDU1": "192.168.120.216"}',
                         vnf_dict['mgmt_ip_address'])

    def test_heal_wait_without_mgmt_ips(self):
        self._response_in_wait_until_stack_ready(["UPDATE_IN_PROGRESS",
                                                 "UPDATE_COMPLETE"],
                                                 stack_outputs=False)
        vnf_dict = utils.get_dummy_vnf(status='PENDING_HEAL',
                                       instance_id=self.instance_uuid)
        self.openstack.heal_wait(None, None, vnf_dict, None)
        self.mock_log.debug.assert_called_with('outputs %s',
                        fd_utils.get_dummy_stack(outputs=False)['outputs'])
        self.assertIsNone(vnf_dict['mgmt_ip_address'])

    def test_heal_wait_failed_with_retries_0(self):
        self._response_in_wait_until_stack_ready(["UPDATE_IN_PROGRESS"])
        vnf_dict = utils.get_dummy_vnf(status='PENDING_HEAL',
                                       instance_id=self.instance_uuid)
        self.assertRaises(vnfm.VNFHealWaitFailed,
                          self.openstack.heal_wait,
                          None, None, vnf_dict,
                          None)

    def test_heal_wait_failed_stack_retries_not_0(self):
        self._response_in_wait_until_stack_ready(["UPDATE_IN_PROGRESS",
                                                 "FAILED"])
        vnf_dict = utils.get_dummy_vnf(status='PENDING_HEAL',
                                       instance_id=self.instance_uuid)
        self.assertRaises(vnfm.VNFHealWaitFailed,
                          self.openstack.heal_wait,
                          None, None, vnf_dict,
                          None)

    def _responses_in_resource_event_list(self, dummy_event):
        # response for heat_client's resource_event_list()
        url = self.url + '/stacks/' + self.instance_uuid
        json = {'stack': [fd_utils.get_dummy_stack()]}
        self.requests_mock.register_uri('GET', url, json=json,
                                        headers=self.json_headers)
        url = self.url + '/stacks/' + self.instance_uuid + ('/myStack/60f83b5e'
        '/resources/SP1_scale_out/events?limit=1&sort_dir=desc&sort_keys='
        'event_time')
        json = {'events': [dummy_event]}
        self.requests_mock.register_uri('GET', url, json=json,
                                        headers=self.json_headers)

    def test_scale(self):
        dummy_event = fd_utils.get_dummy_event()
        self._responses_in_resource_event_list(dummy_event)
        # response for heat_client's resource_signal()
        url = self.url + '/stacks/' + self.instance_uuid + ('/myStack/60f83b5e'
                                             '/resources/SP1_scale_out/signal')
        self.requests_mock.register_uri('POST', url, json={},
                                        headers=self.json_headers)
        event_id = self.openstack.scale(plugin=self, context=self.context,
                                    auth_attr=None,
                                    policy=fd_utils.get_dummy_policy_dict(),
                                    region_name=None)
        self.assertEqual(dummy_event['id'], event_id)

    def _response_in_resource_get_list(self):
        # response for heat_client's resource_get_list()
        url = self.url + '/stacks/' + self.stack_id + '/resources'
        json = {'resources': [fd_utils.get_dummy_resource()]}
        self.requests_mock.register_uri('GET', url, json=json,
                                        headers=self.json_headers)

    def _test_scale(self, resource_status):
        dummy_event = fd_utils.get_dummy_event(resource_status)
        self._responses_in_resource_event_list(dummy_event)
        self._response_in_resource_get(self.instance_uuid, res_name='G1')
        self._response_in_resource_get_list()
        self._response_in_resource_get(self.stack_id)
        self._response_in_resource_get(self.instance_uuid,
                                       res_name='SP1_group')

    def test_scale_wait_with_different_last_event_id(self):
        self._test_scale("SIGNAL_COMPLETE")
        mgmt_ip = self.openstack.scale_wait(plugin=self, context=self.context,
                                     auth_attr=None,
                                     policy=fd_utils.get_dummy_policy_dict(),
                                     region_name=None,
                                     last_event_id=uuidsentinel.
                                            non_last_event_id)
        self.assertEqual('{"vdu1": ["test1"]}', mgmt_ip)

    @ddt.data("SIGNAL_COMPLETE", "CREATE_COMPLETE")
    def test_scale_wait_with_same_last_event_id(self, resource_status):
        self._test_scale(resource_status)
        mgmt_ip = self.openstack.scale_wait(plugin=self,
                                context=self.context,
                                auth_attr=None,
                                policy=fd_utils.get_dummy_policy_dict(),
                                region_name=None,
                                last_event_id=fd_utils.get_dummy_event()['id'])
        self.assertEqual('{"vdu1": ["test1"]}', mgmt_ip)

    @mock.patch('tacker.vnfm.infra_drivers.openstack.openstack.LOG')
    def test_scale_wait_failed_with_exception(self, mock_log):
        self._exception_response()
        self.assertRaises(vnfm.VNFScaleWaitFailed,
                          self.openstack.scale_wait,
                          plugin=self, context=self.context, auth_attr=None,
                          policy=fd_utils.get_dummy_policy_dict(),
                          region_name=None,
                          last_event_id=fd_utils.get_dummy_event()['id'])
        mock_log.warning.assert_called_once()

    def _response_in_resource_metadata(self, metadata=None):
        # response for heat_client's resource_metadata()
        url = self.url + '/stacks/' + self.instance_uuid + \
            '/myStack/60f83b5e/resources/SP1_scale_out/metadata'
        json = {'metadata': {'scaling_in_progress': metadata}}
        self.requests_mock.register_uri('GET', url, json=json,
                                        headers=self.json_headers)

    def test_scale_wait_failed_with_stack_retries_0(self):
        dummy_event = fd_utils.get_dummy_event("CREATE_IN_PROGRESS")
        self._responses_in_resource_event_list(dummy_event)
        self._response_in_resource_metadata(True)
        self.assertRaises(vnfm.VNFScaleWaitFailed,
                          self.openstack.scale_wait,
                          plugin=self, context=self.context, auth_attr=None,
                          policy=fd_utils.get_dummy_policy_dict(),
                          region_name=None,
                          last_event_id=dummy_event['id'])
        self.mock_log.warning.assert_called_once()

    def test_scale_wait_without_resource_metadata(self):
        dummy_event = fd_utils.get_dummy_event("CREATE_IN_PROGRESS")
        self._responses_in_resource_event_list(dummy_event)
        self._response_in_resource_metadata()
        self._response_in_resource_get(self.instance_uuid, res_name='G1')
        self._response_in_resource_get_list()
        self._response_in_resource_get(self.stack_id)
        self._response_in_resource_get(self.instance_uuid,
                                       res_name='SP1_group')
        mgmt_ip = self.openstack.scale_wait(plugin=self, context=self.context,
                                  auth_attr=None,
                                  policy=fd_utils.get_dummy_policy_dict(),
                                  region_name=None,
                                  last_event_id=fd_utils.get_dummy_event()
                                  ['id'])
        error_reason = ('When signal occurred within cool down '
                        'window, no events generated from heat, '
                        'so ignore it')
        self.mock_log.warning.assert_called_once_with(error_reason)
        self.assertEqual('{"vdu1": ["test1"]}', mgmt_ip)
