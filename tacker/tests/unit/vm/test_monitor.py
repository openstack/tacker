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

import json

import mock
from oslo_utils import timeutils
import testtools

from tacker.vm.monitor import VNFMonitor

MOCK_DEVICE_ID = 'a737497c-761c-11e5-89c3-9cb6541d805d'
MOCK_VNF_DEVICE = {
    'id': MOCK_DEVICE_ID,
    'management_ip_addresses': {
        'vdu1': 'a.b.c.d'
    },
    'monitoring_policy': {
        'vdus': {
            'vdu1': {
                'ping': {
                    'actions': {
                        'failure': 'respawn'
                    },
                    'monitoring_params': {
                        'count': 1,
                        'monitoring_delay': 0,
                        'interval': 0,
                        'timeout': 2
                    }
                }
            }
        }
    },
    'boot_at': timeutils.utcnow(),
    'action_cb': mock.MagicMock()
}


class TestVNFMonitor(testtools.TestCase):

    def setUp(self):
        super(TestVNFMonitor, self).setUp()
        p = mock.patch('tacker.common.driver_manager.DriverManager')
        self.mock_monitor_manager = p.start()
        self.addCleanup(p.stop)

    def test_to_hosting_vnf(self):
        test_device_dict = {
            'id': MOCK_DEVICE_ID,
            'mgmt_url': '{"vdu1": "a.b.c.d"}',
            'attributes': {
                'monitoring_policy': json.dumps(
                        MOCK_VNF_DEVICE['monitoring_policy'])
            }
        }
        action_cb = mock.MagicMock()
        expected_output = {
            'id': MOCK_DEVICE_ID,
            'action_cb': action_cb,
            'management_ip_addresses': {
                'vdu1': 'a.b.c.d'
            },
            'device': test_device_dict,
            'monitoring_policy': MOCK_VNF_DEVICE['monitoring_policy']
        }
        output_dict = VNFMonitor.to_hosting_vnf(test_device_dict,
                                                action_cb)
        self.assertDictEqual(expected_output, output_dict)

    @mock.patch('tacker.vm.monitor.VNFMonitor.__run__')
    def test_add_hosting_vnf(self, mock_monitor_run):
        test_device_dict = MOCK_VNF_DEVICE
        test_boot_wait = 30
        test_vnfmonitor = VNFMonitor(test_boot_wait)
        test_vnfmonitor.add_hosting_vnf(test_device_dict)
        test_device_id = test_vnfmonitor._hosting_vnfs.keys()[0]
        self.assertEqual(test_device_id, MOCK_DEVICE_ID)

    @mock.patch('tacker.vm.monitor.VNFMonitor.__run__')
    def test_run_monitor(self, mock_monitor_run):
        test_hosting_vnf = MOCK_VNF_DEVICE
        test_hosting_vnf['device'] = {}
        test_boot_wait = 30
        mock_kwargs = {
            'count': 1,
            'monitoring_delay': 0,
            'interval': 0,
            'mgmt_ip': 'a.b.c.d',
            'timeout': 2
        }
        test_vnfmonitor = VNFMonitor(test_boot_wait)
        self.mock_monitor_manager.invoke = mock.MagicMock()
        test_vnfmonitor._monitor_manager = self.mock_monitor_manager
        test_vnfmonitor.run_monitor(test_hosting_vnf)
        self.mock_monitor_manager\
            .invoke.assert_called_once_with('ping', 'monitor_call', device={},
                                            kwargs=mock_kwargs)
