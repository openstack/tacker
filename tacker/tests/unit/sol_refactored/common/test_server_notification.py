# Copyright (C) 2022 Fujitsu
# All Rights Reserved.
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

from tacker import context
from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.common import monitoring_plugin_base as mon_base
from tacker.sol_refactored.common import server_notification
from tacker.sol_refactored.common import vnf_instance_utils as inst_utils
from tacker.sol_refactored import objects
from tacker.tests.unit import base

from unittest import mock

_inst1 = {
    'id': 'test_id',
    'vnfdId': 'vnfdId',
    'vnfProvider': 'vnfProvider',
    'vnfProductName': 'vnfProductName',
    'vnfSoftwareVersion': 'vnfSoftwareVersion',
    'vnfdVersion': 'vnfdVersion',
    'instantiationState': 'NOT_INSTANTIATED',
    'instantiatedVnfInfo': {
        'id': 'id',
        'vduId': 'vduId',
        'vnfcResourceInfo': [
            {
                'id': 'vnfc_resource_id1',
                'vduId': 'vduId',
                'computeResource': {},
                'metadata': {
                    "server_notification": {
                        "alarmId": "alarm_id"
                    }
                }
            }, {
                'id': 'vnfc_resource_id2',
                'vduId': 'vduId2',
                'computeResource': {},
                'metadata': {
                    "server_notification": {
                        "alarmId": "alarm_id2"
                    }
                }
            }
        ],
        'vnfcInfo': [{
            'id': 'vnfc_info1',
            'vduId': 'vdu_id',
            'vnfcResourceInfoId': 'vnfc_resource_id1',
            'vnfcState': 'STARTED'
        }],
        'metadata': {
            'ServerNotifierUri': 'ServerNotifierUri',
            'ServerNotifierFaultID': ['1111', '1234']
        }
    }
}

_body = {
    'notification': {
        'alarm_id': 'alarm_id',
        'fault_id': '1234',
        'fault_type': '10',
    }
}


class TestServerNotification(base.TestCase):
    def setUp(self):
        super(TestServerNotification, self).setUp()
        objects.register_all()
        self.context = context.get_admin_context()
        self.request = mock.Mock()
        self.request.context = self.context
        self.config_fixture.config(
            group='server_notification', server_notification=True)
        server_notification.ServerNotification._instance = None

    def tearDown(self):
        super(TestServerNotification, self).tearDown()
        server_notification.ServerNotification._instance = None

    @mock.patch.object(inst_utils, 'get_inst')
    def test_notify(self,
            mock_inst):
        self.config_fixture.config(
            group='server_notification', server_notification=True)
        server_notification.ServerNotification._instance = None
        sn = mon_base.MonitoringPlugin.get_instance(
            server_notification.ServerNotification)

        mock_inst.return_value = objects.VnfInstanceV2.from_dict(_inst1)
        sn.notify(self.request, 'test_id', body=_body)

    @mock.patch.object(inst_utils, 'get_inst')
    def test_notify_no_callback(self,
            mock_inst):
        self.config_fixture.config(
            group='server_notification', server_notification=True)
        server_notification.ServerNotification._instance = None
        sn = mon_base.MonitoringPlugin.get_instance(
            server_notification.ServerNotification)
        sn.set_callback(None)

        mock_inst.return_value = objects.VnfInstanceV2.from_dict(_inst1)
        sn.notify(self.request, 'test_id', body=_body)

    def test_notify_error_schema(self):
        self.config_fixture.config(
            group='server_notification', server_notification=True)
        server_notification.ServerNotification._instance = None
        sn = mon_base.MonitoringPlugin.get_instance(
            server_notification.ServerNotification)
        self.assertRaises(
            sol_ex.SolValidationError,
            sn.notify, self.request, 'test_id')

    def test_constructor_error(self):
        self.config_fixture.config(
            group='server_notification', server_notification=True)
        server_notification.ServerNotification._instance = None
        mon_base.MonitoringPlugin.get_instance(
            server_notification.ServerNotification)
        self.assertRaises(
            SystemError,
            server_notification.ServerNotification)

    def test_constructor_stub(self):
        self.config_fixture.config(
            group='server_notification', server_notification=False)
        server_notification.ServerNotification._instance = None
        sn = mon_base.MonitoringPlugin.get_instance(
            server_notification.ServerNotification)
        self.assertIsInstance(sn._instance, mon_base.MonitoringPluginStub)
        sn = mon_base.MonitoringPlugin.get_instance(
            server_notification.ServerNotification)
        self.assertIsInstance(sn._instance, mon_base.MonitoringPluginStub)

    def test_monitoring_plugin(self):
        mon_base.MonitoringPluginStub._instance = None
        mon = mon_base.MonitoringPlugin.get_instance(
            mon_base.MonitoringPluginStub)
        mon.set_callback(None)
        mon.create_job()
        mon.delete_job()
        mon.alert()

    def test_monitoring_plugin_stub(self):
        mon_base.MonitoringPluginStub._instance = None
        mon_base.MonitoringPlugin.get_instance(
            mon_base.MonitoringPluginStub)
        mon = mon_base.MonitoringPlugin.get_instance(
            mon_base.MonitoringPluginStub)
        mon.set_callback(None)
        mon.create_job()
        mon.delete_job()
        mon.alert()
        self.assertRaises(
            SystemError,
            mon_base.MonitoringPluginStub)
