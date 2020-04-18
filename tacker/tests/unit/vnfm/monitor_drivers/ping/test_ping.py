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
#

import testtools
from unittest import mock

from tacker.vnfm.monitor_drivers.ping import ping


class TestVNFMonitorPing(testtools.TestCase):

    def setUp(self):
        super(TestVNFMonitorPing, self).setUp()
        self.monitor_ping = ping.VNFMonitorPing()

    @mock.patch('tacker.agent.linux.utils.execute')
    def test_monitor_call_for_success(self, mock_utils_execute):
        test_vnf = {}
        test_kwargs = {
            'mgmt_ip': 'a.b.c.d'
        }
        mock_ping_cmd = ['ping',
                         '-c', 5,
                         '-W', 5.0,
                         '-i', 1.0,
                         'a.b.c.d']
        self.monitor_ping.monitor_call(test_vnf,
                                       test_kwargs)
        mock_utils_execute.assert_called_once_with(mock_ping_cmd,
                                                   check_exit_code=True)

    @mock.patch('tacker.agent.linux.utils.execute')
    def test_monitor_call_for_failure(self, mock_utils_execute):
        mock_utils_execute.side_effect = RuntimeError()
        test_vnf = {}
        test_kwargs = {
            'mgmt_ip': 'a.b.c.d'
        }
        monitor_return = self.monitor_ping.monitor_call(test_vnf,
                                                        test_kwargs)
        self.assertEqual('failure', monitor_return)

    def test_monitor_url(self):
        test_vnf = {
            'monitor_url': 'a.b.c.d'
        }
        test_monitor_url = self.monitor_ping.monitor_url(mock.ANY,
                                                         mock.ANY,
                                                         test_vnf)
        self.assertEqual('a.b.c.d', test_monitor_url)

    @mock.patch('tacker.agent.linux.utils.execute')
    def test_monitor_call_with_params(self, mock_utils_execute):
        check_ping_counts = 2
        check_ping_timeout = 5.0
        check_ping_interval = 0.5
        test_vnf = {}
        test_kwargs = {
            'mgmt_ip': 'a:b:c:d:e:f:1:2',
            'count': check_ping_counts,
            'timeout': check_ping_timeout,
            'interval': check_ping_interval
        }
        mock_ping_cmd = ['ping6',
                         '-c', check_ping_counts,
                         '-W', check_ping_timeout,
                         '-i', check_ping_interval,
                         'a:b:c:d:e:f:1:2']
        self.monitor_ping.monitor_call(test_vnf,
                                       test_kwargs)
        mock_utils_execute.assert_called_once_with(mock_ping_cmd,
                                                   check_exit_code=True)

    @mock.patch('tacker.agent.linux.utils.execute')
    def test_monitor_call_for_counts(self, mock_utils_execute):
        check_retury_counts = 5
        mock_utils_execute.side_effect = RuntimeError()
        test_vnf = {}
        test_kwargs = {
            'mgmt_ip': 'a:b:c:d:e:f:1:2',
            'retry': check_retury_counts
        }
        self.monitor_ping.monitor_call(test_vnf,
                                       test_kwargs)
        self.assertEqual(check_retury_counts,
                         mock_utils_execute.call_count)
