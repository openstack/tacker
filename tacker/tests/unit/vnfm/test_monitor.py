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

from unittest import mock

from oslo_serialization import jsonutils
from oslo_utils import timeutils
import testtools

from tacker import context
from tacker.db.common_services import common_services_db_plugin
from tacker.plugins.common import constants
from tacker.vnfm import monitor
from tacker.vnfm import plugin

MOCK_VNF_ID = 'a737497c-761c-11e5-89c3-9cb6541d805d'
MOCK_VNF = {
    'id': MOCK_VNF_ID,
    'mgmt_ip_addresses': {
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


MOCK_VNF_DEVICE_FOR_VDU_AUTOHEAL = {
    'id': MOCK_VNF_ID,
    'mgmt_ip_addresses': {
        'vdu1': 'a.b.c.d'
    },
    'monitoring_policy': {
        'vdus': {
            'vdu1': {
                'ping': {
                    'actions': {
                        'failure': 'vdu_autoheal'
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
        mock.patch('tacker.db.common_services.common_services_db_plugin.'
                   'CommonServicesPluginDb.create_event'
                   ).start()
        self._cos_db_plugin =\
            common_services_db_plugin.CommonServicesPluginDb()
        self.addCleanup(p.stop)

    def test_to_hosting_vnf(self):
        test_vnf_dict = {
            'id': MOCK_VNF_ID,
            'mgmt_ip_address': '{"vdu1": "a.b.c.d"}',
            'attributes': {
                'monitoring_policy': jsonutils.dump_as_bytes(
                    MOCK_VNF['monitoring_policy'])
            }
        }
        action_cb = mock.MagicMock()
        expected_output = {
            'id': MOCK_VNF_ID,
            'action_cb': action_cb,
            'mgmt_ip_addresses': {
                'vdu1': 'a.b.c.d'
            },
            'vnf': test_vnf_dict,
            'monitoring_policy': MOCK_VNF['monitoring_policy']
        }
        output_dict = monitor.VNFMonitor.to_hosting_vnf(test_vnf_dict,
                                                action_cb)
        self.assertEqual(expected_output, output_dict)

    @mock.patch('tacker.vnfm.monitor.VNFMonitor.__run__')
    def test_add_hosting_vnf(self, mock_monitor_run):
        test_vnf_dict = {
            'id': MOCK_VNF_ID,
            'mgmt_ip_address': '{"vdu1": "a.b.c.d"}',
            'attributes': {
                'monitoring_policy': jsonutils.dump_as_bytes(
                    MOCK_VNF['monitoring_policy'])
            },
            'status': 'ACTIVE'
        }
        action_cb = mock.MagicMock()
        test_boot_wait = 30
        test_vnfmonitor = monitor.VNFMonitor(test_boot_wait)
        new_dict = test_vnfmonitor.to_hosting_vnf(test_vnf_dict, action_cb)
        test_vnfmonitor.add_hosting_vnf(new_dict)
        test_vnf_id = list(test_vnfmonitor._hosting_vnfs.keys())[0]
        self.assertEqual(MOCK_VNF_ID, test_vnf_id)
        self._cos_db_plugin.create_event.assert_called_with(
            mock.ANY, res_id=mock.ANY, res_type=constants.RES_TYPE_VNF,
            res_state=mock.ANY, evt_type=constants.RES_EVT_MONITOR,
            tstamp=mock.ANY, details=mock.ANY)

    @mock.patch('tacker.vnfm.monitor.VNFMonitor.__run__')
    def test_run_monitor(self, mock_monitor_run):
        test_hosting_vnf = MOCK_VNF
        test_hosting_vnf['vnf'] = {'status': 'ACTIVE'}
        test_boot_wait = 30
        mock_kwargs = {
            'count': 1,
            'monitoring_delay': 0,
            'interval': 0,
            'mgmt_ip': 'a.b.c.d',
            'timeout': 2
        }
        test_vnfmonitor = monitor.VNFMonitor(test_boot_wait)
        self.mock_monitor_manager.invoke = mock.MagicMock()
        test_vnfmonitor._monitor_manager = self.mock_monitor_manager
        test_vnfmonitor.run_monitor(test_hosting_vnf)
        self.mock_monitor_manager \
            .invoke.assert_called_once_with('ping', 'monitor_call',
                                            vnf={'status': 'ACTIVE'},
                                            kwargs=mock_kwargs)

    @mock.patch('tacker.vnfm.monitor.VNFMonitor.__run__')
    @mock.patch('tacker.vnfm.monitor.VNFMonitor.monitor_call')
    def test_vdu_autoheal_action(self, mock_monitor_call, mock_monitor_run):
        test_hosting_vnf = MOCK_VNF_DEVICE_FOR_VDU_AUTOHEAL
        test_boot_wait = 30
        test_device_dict = {
            'status': 'ACTIVE',
            'id': MOCK_VNF_ID,
            'mgmt_ip_address': '{"vdu1": "a.b.c.d"}',
            'attributes': {
                'monitoring_policy': jsonutils.dump_as_bytes(
                    MOCK_VNF_DEVICE_FOR_VDU_AUTOHEAL['monitoring_policy'])
            }
        }
        test_hosting_vnf['vnf'] = test_device_dict
        mock_monitor_call.return_value = 'failure'
        test_vnfmonitor = monitor.VNFMonitor(test_boot_wait)
        test_vnfmonitor._monitor_manager = self.mock_monitor_manager
        test_vnfmonitor.run_monitor(test_hosting_vnf)
        test_hosting_vnf['action_cb'].assert_called_once_with(
            'vdu_autoheal', vdu_name='vdu1')

    @mock.patch('tacker.vnfm.monitor.VNFMonitor.__run__')
    def test_update_hosting_vnf(self, mock_monitor_run):
        test_boot_wait = 30
        test_vnfmonitor = monitor.VNFMonitor(test_boot_wait)
        vnf_dict = {
            'id': MOCK_VNF_ID,
            'mgmt_ip_address': '{"vdu1": "a.b.c.d"}',
            'mgmt_ip_addresses': 'a.b.c.d',
            'vnf': {
                'id': MOCK_VNF_ID,
                'mgmt_ip_address': '{"vdu1": "a.b.c.d"}',
                'attributes': {
                    'monitoring_policy': jsonutils.dump_as_bytes(
                        MOCK_VNF['monitoring_policy'])
                },
                'status': 'ACTIVE',
            }
        }

        test_vnfmonitor.add_hosting_vnf(vnf_dict)
        vnf_dict['status'] = 'PENDING_HEAL'
        test_vnfmonitor.update_hosting_vnf(vnf_dict)
        test_device_status = test_vnfmonitor._hosting_vnfs[MOCK_VNF_ID][
            'vnf']['status']
        self.assertEqual('PENDING_HEAL', test_device_status)


class TestVNFReservationAlarmMonitor(testtools.TestCase):

    def setUp(self):
        super(TestVNFReservationAlarmMonitor, self).setUp()
        self.context = context.get_admin_context()
        self.plugin = plugin.VNFMPlugin

    def test_process_alarm_for_vnf(self):
        vnf = {'id': 'a737497c-761c-11e5-89c3-9cb6541d805d'}
        trigger = {'params': {'data': {
            'alarm_id': 'a737497c-761c-11e5-89c3-9cb6541d805d',
            'current': 'alarm'}}}
        test_vnf_reservation_monitor = monitor.VNFReservationAlarmMonitor()
        response = test_vnf_reservation_monitor.process_alarm_for_vnf(
            vnf, trigger)
        self.assertEqual(response, True)

    @mock.patch('tacker.db.common_services.common_services_db_plugin.'
                'CommonServicesPluginDb.create_event')
    @mock.patch('tacker.vnfm.plugin.VNFMPlugin.get_vnf_policies')
    def test_update_vnf_with_alarm(self, mock_get_vnf_policies,
                                   mock_db_service):
        mock_get_vnf_policies.return_value = [
            {'name': 'SP_RSV', 'type': 'tosca.policies.tacker.Scaling'}]
        mock_db_service.return_value = {
            'event_type': 'MONITOR',
            'resource_id': '9770fa22-747d-426e-9819-057a95cb778c',
            'timestamp': '2018-10-30 06:01:45.628162',
            'event_details': {'Alarm URL set successfully': {
                'start_actions': 'alarm'}},
            'resource_state': 'CREATE',
            'id': '4583',
            'resource_type': 'vnf'}
        vnf = {'id': 'a737497c-761c-11e5-89c3-9cb6541d805d',
               'status': 'insufficient_data'}
        test_vnf_reservation_monitor = monitor.VNFReservationAlarmMonitor()
        policy_dict = {
            'type': 'tosca.policies.tacker.Reservation',
            'reservation': {'before_end_actions': ['SP_RSV'],
                            'end_actions': ['noop'],
                            'start_actions': ['SP_RSV'],
                            'properties': {
                                'lease_id':
                                    'ffa079a0-9d6f-411d-ab15-89219c0ee14d'}}}
        response = test_vnf_reservation_monitor.update_vnf_with_reservation(
            self.plugin, self.context, vnf, policy_dict)
        self.assertEqual(len(response.keys()), 3)


class TestVNFMaintenanceAlarmMonitor(testtools.TestCase):

    def setup(self):
        super(TestVNFMaintenanceAlarmMonitor, self).setUp()

    def test_process_alarm_for_vnf(self):
        vnf = {'id': MOCK_VNF_ID}
        trigger = {'params': {'data': {
            'alarm_id': MOCK_VNF_ID, 'current': 'alarm'}}}
        test_vnf_maintenance_monitor = monitor.VNFMaintenanceAlarmMonitor()
        response = test_vnf_maintenance_monitor.process_alarm_for_vnf(
            vnf, trigger)
        self.assertEqual(response, True)

    @mock.patch('tacker.db.common_services.common_services_db_plugin.'
                'CommonServicesPluginDb.create_event')
    def test_update_vnf_with_alarm(self, mock_db_service):
        mock_db_service.return_value = {
            'event_type': 'MONITOR',
            'resource_id': '9770fa22-747d-426e-9819-057a95cb778c',
            'timestamp': '2018-10-30 06:01:45.628162',
            'event_details': {'Alarm URL set successfully': {
                'start_actions': 'alarm'}},
            'resource_state': 'CREATE',
            'id': '4583',
            'resource_type': 'vnf'}
        vnf = {
            'id': MOCK_VNF_ID,
            'tenant_id': 'ad7ebc56538745a08ef7c5e97f8bd437',
            'status': 'insufficient_data'}
        vdu_names = ['VDU1']
        test_vnf_maintenance_monitor = monitor.VNFMaintenanceAlarmMonitor()
        response = test_vnf_maintenance_monitor.update_vnf_with_maintenance(
            vnf, vdu_names)
        result_keys = len(response) + len(response.get('vdus', {}))
        self.assertEqual(result_keys, 4)
