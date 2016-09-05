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

import mock
from webob import Request

from tacker.alarm_receiver import AlarmReceiver
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
            '05_key': 'KEY'
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

    @mock.patch('tacker.vnfm.monitor_drivers.token.Token.create_token')
    def test_process_request(self, mock_token):
        req = Request.blank(self.ordered_url)
        req.method = 'POST'
        self.alarmrc.process_request(req)
        self.assertIsNotNone(req.body)
        self.assertIn('triggers', req.environ['PATH_INFO'])
