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

import copy
from unittest import mock

from tacker import context
from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.common import monitoring_plugin_base as mon_base
from tacker.sol_refactored.common import server_notification as sn_common
from tacker.sol_refactored.common import vnf_instance_utils as inst_utils
from tacker.sol_refactored.controller import server_notification
from tacker.sol_refactored import objects
from tacker.tests.unit import base

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
    },
    'vnfConfigurableProperties': {
        'isAutohealEnabled': True
    }
}

_body = {
    'notification': {
        'alarm_id': 'alarm_id',
        'fault_id': '1234',
        'fault_type': '10',
    }
}

_body2 = {
    'error_schema': {}
}

pkg = 'tacker.tests.unit.sol_refactored.controller.test_server_notification'


class VendorSpecificMonitoringPlugin(mon_base.MonitoringPlugin):
    _instance = None

    @staticmethod
    def instance():
        if not VendorSpecificMonitoringPlugin._instance:
            VendorSpecificMonitoringPlugin()
        return VendorSpecificMonitoringPlugin._instance

    def __init__(self):
        if VendorSpecificMonitoringPlugin._instance:
            raise SystemError(
                "Not constructor but instance() should be used.")
        VendorSpecificMonitoringPlugin._instance = self

    def alert(self, **kwargs):
        pass


class NotASubClassOfMonitoringPlugin():
    pass


class TestServerNotification(base.TestCase):
    def setUp(self):
        super(TestServerNotification, self).setUp()
        objects.register_all()
        self.context = context.get_admin_context()
        self.request = mock.Mock()
        self.request.context = self.context
        self.controller = \
            server_notification.ServerNotificationController()
        self.config_fixture.config(
            group='server_notification', server_notification=True)
        sn_common.ServerNotification._instance = None

    def tearDown(self):
        super(TestServerNotification, self).tearDown()
        sn_common.ServerNotification._instance = None

    def test_notify_config_false(self):
        self.config_fixture.config(
            group='server_notification', server_notification=False)
        self.assertRaises(
            sol_ex.ServerNotificationNotEnabled,
            self.controller.notify, request=self.request,
            vnf_instance_id='test_id',
            server_id='test_server_id', body=_body)

    @mock.patch.object(inst_utils, 'get_inst')
    def test_notify(self, mock_inst):
        self.config_fixture.config(
            group='server_notification', server_notification=True)
        mock_inst.return_value = objects.VnfInstanceV2.from_dict(_inst1)
        response = self.controller.notify(
            request=self.request,
            vnf_instance_id='test_id',
            server_id='test_server_id', body=_body)
        self.assertEqual(204, response.status)

    def test_notify_error_schema(self):
        self.config_fixture.config(
            group='server_notification', server_notification=True)
        self.assertRaises(
            sol_ex.SolValidationError,
            self.controller.notify,
            request=self.request,
            vnf_instance_id='test_id',
            server_id='test_server_id', body=_body2)

    @mock.patch.object(inst_utils, 'get_inst')
    def test_notify_vnfc_mismatch(self,
            mock_inst):
        self.config_fixture.config(
            group='server_notification', server_notification=True)
        _inst = copy.deepcopy(_inst1)
        _inst['instantiatedVnfInfo']['vnfcInfo'][0]['vnfcResourceInfoId'] = (
            'vnfc_resource_id2')

        mock_inst.return_value = objects.VnfInstanceV2.from_dict(_inst)
        self.assertRaises(
            sol_ex.SolValidationError,
            self.controller.notify, request=self.request,
            vnf_instance_id='test_id',
            server_id='test_server_id', body=_body)

    @mock.patch.object(inst_utils, 'get_inst')
    def test_notify_fault_id_mismatch(self,
            mock_inst):
        self.config_fixture.config(
            group='server_notification', server_notification=True)
        _inst = copy.deepcopy(_inst1)
        metadata = _inst['instantiatedVnfInfo']['metadata']
        metadata['ServerNotifierFaultID'] = ['0000']

        mock_inst.return_value = objects.VnfInstanceV2.from_dict(_inst)
        self.assertRaises(
            sol_ex.SolValidationError,
            self.controller.notify, request=self.request,
            vnf_instance_id='test_id',
            server_id='test_server_id', body=_body)

    @mock.patch.object(inst_utils, 'get_inst')
    def test_notify_no_vnf_instance(self, mock_inst):
        self.config_fixture.config(
            group='server_notification', server_notification=True)
        mock_inst.return_value = None
        self.assertRaises(
            sol_ex.SolValidationError,
            self.controller.notify, request=self.request,
            vnf_instance_id='test_id',
            server_id='test_server_id', body=_body)

    def test_vendor_specific_plugin(self):
        self.config_fixture.config(
            group='server_notification', server_notification=True)
        self.config_fixture.config(
            group='server_notification', server_notification_package=pkg)
        self.config_fixture.config(
            group='server_notification',
            server_notification_class='VendorSpecificMonitoringPlugin')
        response = self.controller.notify(
            request=self.request,
            vnf_instance_id='test_id',
            server_id='test_server_id', body=_body)
        self.assertEqual(204, response.status)

    def test_vendor_specific_plugin_subclass(self):
        self.config_fixture.config(
            group='server_notification', server_notification=True)
        self.config_fixture.config(
            group='server_notification', server_notification_package=pkg)
        self.config_fixture.config(
            group='server_notification',
            server_notification_class='NotASubClassOfMonitoringPlugin')
        self.assertRaises(
            sol_ex.MonitoringPluginClassError, self.controller.notify,
            request=self.request, vnf_instance_id='test_id',
            server_id='test_server_id', body=_body)
