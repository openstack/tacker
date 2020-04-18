# Copyright 2015 Brocade Communications System, Inc.
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

from unittest import mock

from oslo_serialization import jsonutils
from webob import Request

from tacker.alarm_receiver import AlarmReceiver
from tacker.tests.common import helpers
from tacker.tests.unit import base


class TestAlarmReceiver(base.TestCase):
    def setUp(self):
        '''url:

        http://tacker:9890/v1.0/vnfs/vnf-uuid/mon-policy-name/
        action-name/8ef785
        '''
        super(TestAlarmReceiver, self).setUp()
        self.alarmrc = AlarmReceiver(None)
        self.alarm_url = {
            '00_base': 'http://tacker:9890/v1.0',
            '01_url_base': '/vnfs/vnf-uuid/',
            '02_vnf_id': 'vnf-uuid',
            '03_monitoring_policy_name': 'mon-policy-name',
            '04_action_name': 'action-name',
            '05_key': '8ef785'
        }
        self.vnf_id = 'vnf-uuid'
        self.ordered_url = self._generate_alarm_url()

    def _generate_alarm_url(self):
        return 'http://tacker:9890/v1.0/vnfs/vnf-uuid/mon-policy-name/'\
               'action-name/8ef785'

    def test_handle_url(self):
        prefix_url, p, params = self.alarmrc.handle_url(self.ordered_url)
        self.assertEqual(self.alarm_url['01_url_base'], prefix_url)
        self.assertEqual(self.alarm_url['02_vnf_id'], p[3])
        self.assertEqual(self.alarm_url['03_monitoring_policy_name'], p[4])
        self.assertEqual(self.alarm_url['04_action_name'], p[5])
        self.assertEqual(self.alarm_url['05_key'], p[6])

    def test_handle_url_action_name(self):
        new_url = 'http://tacker:9890/v1.0/vnfs/vnf-uuid/mon-policy-name/'\
                  'respawn%25log/8ef785'
        prefix_url, p, params = self.alarmrc.handle_url(new_url)
        self.assertEqual(self.alarm_url['01_url_base'], prefix_url)
        self.assertEqual(self.alarm_url['02_vnf_id'], p[3])
        self.assertEqual(self.alarm_url['03_monitoring_policy_name'], p[4])
        self.assertEqual('respawn%log', p[5])
        self.assertEqual(self.alarm_url['05_key'], p[6])

    @mock.patch('tacker.vnfm.monitor_drivers.token.Token.create_token')
    def test_process_request(self, mock_create_token):
        mock_create_token.return_value = 'fake_token'
        req = Request.blank(self.ordered_url)
        req.method = 'POST'
        self.alarmrc.process_request(req)

        self.assertEqual(helpers.compact_byte(''), req.body)
        self.assertEqual('fake_token', req.headers['X_AUTH_TOKEN'])
        self.assertIn(self.alarm_url['01_url_base'], req.environ['PATH_INFO'])
        self.assertIn('triggers', req.environ['PATH_INFO'])
        self.assertEqual('', req.environ['QUERY_STRING'])
        mock_create_token.assert_called_once_with()

    @mock.patch('tacker.vnfm.monitor_drivers.token.Token.create_token')
    def test_process_request_with_body(self, mock_create_token):
        req = Request.blank(self.ordered_url)
        req.method = 'POST'
        old_body = {'fake_key': 'fake_value'}
        req.body = jsonutils.dump_as_bytes(old_body)

        self.alarmrc.process_request(req)

        body_dict = jsonutils.loads(req.body)
        self.assertDictEqual(old_body,
                             body_dict['trigger']['params']['data'])
        self.assertEqual(self.alarm_url['05_key'],
                         body_dict['trigger']['params']['credential'])
        self.assertEqual(self.alarm_url['03_monitoring_policy_name'],
                         body_dict['trigger']['policy_name'])
        self.assertEqual(self.alarm_url['04_action_name'],
                         body_dict['trigger']['action_name'])
