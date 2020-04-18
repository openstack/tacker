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

from tacker.vnfm.monitor_drivers.zabbix import zabbix
import testtools
from unittest import mock


class TestVNFMonitorZabbix(testtools.TestCase):

    def setUp(self):
        super(TestVNFMonitorZabbix, self).setUp()
        zabbix.VNFMonitorZabbix.tacker_token = 'a1b2c3d4e5'
        self.monitor_zabbix = zabbix.VNFMonitorZabbix()

    @mock.patch('tacker.vnfm.monitor_drivers.zabbix.zabbix.'
                'VNFMonitorZabbix.add_to_appmonitor')
    def test_add_to_appmonitor(self, mock_ac):
        mock_ac.return_value = None

        test_vnf = {'vnfd': {'tenant_id': u'd1e6919c73074d18ab6cd49a02e08391'},
                    'id': 'b9af3cb5-6e43-4b2c-a056-67bda3f71e1a'}
        test_kwargs = {'vdus': {'VDU1':
                                {'parameters':
                                 {'application':
                                  {'app_name': 'apache2',
                                   'app_status': {'actionname': 'cmd',
                                                  'cmd-action': 'sudo service \
                                                  apache2 restart',
                                                  'condition': ['down']},
                                   'ssh_username': 'ubuntu',
                                   'app_port': 80,
                                   'ssh_password': 'ubuntu'}},
                                 'name': 'zabbix',
                                 'zabbix_username': 'Admin',
                                 'zabbix_password': 'zabbix',
                                 'zabbix_server_ip': '192.168.11.53',
                                 'zabbix_server_port': 80,
                                 'mgmt_ip': '192.168.11.206'}}}

        monitor_return = self.monitor_zabbix.\
            add_to_appmonitor(test_kwargs, test_vnf)
        self.assertEqual(None, monitor_return)
