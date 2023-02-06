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
import datetime
from unittest import mock

from tacker import context
from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.common import fm_alarm_utils
from tacker.sol_refactored.common import prometheus_plugin as plugin
from tacker.sol_refactored.common import vnf_instance_utils as inst_utils
from tacker.sol_refactored.controller import prometheus_plugin_controller
from tacker.sol_refactored import objects
from tacker.tests.unit import base


_body_base = {
    'receiver': 'receiver',
    'status': 'firing',
    'alerts': [
    ],
    'groupLabels': {},
    'commonLabels': {
        'alertname': 'NodeInstanceDown',
        'job': 'node'
    },
    'commonAnnotations': {
        'description': 'sample'
    },
    'externalURL': 'http://controller147:9093',
    'version': '4',
    'groupKey': '{}:{}',
    'truncatedAlerts': 0
}

_body_fm_alert1 = {
    'status': 'firing',
    'labels': {
        'receiver_type': 'tacker',
        'function_type': 'vnffm',
        'vnf_instance_id': 'vnf_instance_id',
        'pod': r'test\-test1\-[0-9a-f]{1,10}-[0-9a-z]{5}$',
        'perceived_severity': 'CRITICAL',
        'event_type': 'PROCESSING_ERROR_ALARM'
    },
    'annotations': {
        'probable_cause': '',
        'fault_type': '',
        'fault_details': ''
    },
    'startsAt': '2022-06-21T23:47:36.453Z',
    'endsAt': '0001-01-01T00:00:00Z',
    'generatorURL': 'http://controller147:9090/graph?g0.expr='
                    'up%7Bjob%3D%22node%22%7D+%3D%3D+0&g0.tab=1',
    'fingerprint': '5ef77f1f8a3ecb8d'
}

# function_type mismatch
_body_fm_alert2 = copy.deepcopy(_body_fm_alert1)
_body_fm_alert2['labels']['function_type'] = 'vnfpm'

# status resolved
_body_fm_alert3 = copy.deepcopy(_body_fm_alert1)
_body_fm_alert3['status'] = 'resolved'

# pod mismatch
_body_fm_alert4 = copy.deepcopy(_body_fm_alert1)
_body_fm_alert4['labels']['pod'] = 'mismatch_node'

# pod does not exist
_body_fm_alert5 = copy.deepcopy(_body_fm_alert1)
del _body_fm_alert5['labels']['pod']

_body_fm1 = copy.copy(_body_base)
_body_fm1.update({
    'alerts': [_body_fm_alert1, _body_fm_alert2]
})

_body_fm2 = copy.copy(_body_base)
_body_fm2.update({
    'alerts': [_body_fm_alert3]
})

_body_fm3 = copy.copy(_body_base)
_body_fm3.update({
    'alerts': [_body_fm_alert4]
})

_body_fm4 = copy.copy(_body_base)
_body_fm4.update({
    'alerts': [_body_fm_alert5]
})

_not_cleared_alarms = {
    'id': 'id',
    'managedObjectId': 'managedObjectId',
    'rootCauseFaultyResource': {
        'faultyResource': {
            'resourceId': 'resourceId',
            'vimConnectionId': 'vimConnectionId',
            'vimLevelResourceType': 'vimLevelResourceType'
        },
        'faultyResourceType': 'COMPUTE'
    },
    'faultDetails': [
        'fingerprint: 5ef77f1f8a3ecb8d'
    ],
    'alarmRaisedTime': '2022-06-23T04:56:00.910Z',
    'ackState': 'UNACKNOWLEDGED',
    'perceivedSeverity': 'WARNING',
    'eventTime': '2022-06-23T04:56:00.910Z',
    'eventType': 'PROCESSING_ERROR_ALARM',
    'probableCause': 'problemCause',
    'isRootCause': False
}

_body_scale_alert1 = {
    'status': 'firing',
    'labels': {
        'receiver_type': 'tacker',
        'function_type': 'auto_scale',
        'vnf_instance_id': 'vnf instance id',
        'auto_scale_type': 'SCALE_OUT',
        'aspect_id': 'aspect'
    },
    'annotations': {
    },
    'startsAt': '2022-06-21T23:47:36.453Z',
    'endsAt': '0001-01-01T00:00:00Z',
    'generatorURL': 'http://controller147:9090/graph?g0.expr='
                    'up%7Bjob%3D%22node%22%7D+%3D%3D+0&g0.tab=1',
    'fingerprint': '5ef77f1f8a3ecb8d'
}

_body_heal_alert1 = {
    'status': 'firing',
    'labels': {
        'receiver_type': 'tacker',
        'function_type': 'auto_heal',
        'vnf_instance_id': 'vnf instance id',
        'vnfc_info_id': 'vnfc info id'
    },
    'annotations': {
    },
    'startsAt': '2022-06-21T23:47:36.453Z',
    'endsAt': '0001-01-01T00:00:00Z',
    'generatorURL': 'http://controller147:9090/graph?g0.expr='
                    'up%7Bjob%3D%22node%22%7D+%3D%3D+0&g0.tab=1',
    'fingerprint': '5ef77f1f8a3ecb8d'
}

# function_type mismatch
_body_scale_alert2 = copy.deepcopy(_body_scale_alert1)
_body_scale_alert2['labels']['function_type'] = 'vnffm'

_body_scale_alert3 = copy.deepcopy(_body_scale_alert1)
_body_scale_alert3['status'] = 'resolved'

_body_scale_alert4 = copy.deepcopy(_body_scale_alert1)
_body_scale_alert4['labels']['function_type'] = 'auto_heal'

_body_scale_alert5 = copy.deepcopy(_body_scale_alert1)
_body_scale_alert5['labels']['aspect_id'] = 'aspect id'

_body_scale = copy.deepcopy(_body_base)
_body_scale.update({
    'alerts': [_body_scale_alert1, _body_scale_alert2]
})

_body_scale_continue = copy.deepcopy(_body_base)
_body_scale_continue.update({
    'alerts': [_body_scale_alert3, _body_scale_alert4, _body_scale_alert5]
})

_body_heal = copy.deepcopy(_body_base)
_body_heal.update({
    'alerts': [_body_heal_alert1]
})

_body_heal_alert2 = copy.deepcopy(_body_heal_alert1)
_body_heal_alert2['status'] = 'resolved'

_body_heal_alert3 = copy.deepcopy(_body_heal_alert1)
_body_heal_alert3['labels']['function_type'] = 'auto_scale'

_body_heal_alert4 = copy.deepcopy(_body_heal_alert1)
_body_heal_alert4['labels']['vnfc_info_id'] = 'vnfcInfoId'

_body_heal_continue = copy.deepcopy(_body_base)
_body_heal_continue.update({
    'alerts': [_body_heal_alert2, _body_heal_alert3, _body_heal_alert4]
})

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
                'id': 'id',
                'vduId': 'vduId',
                'computeResource': {},
                'metadata': {
                    'hostname': 'node1',
                }
            }, {
                'id': 'id2',
                'vduId': 'vduId2',
                'computeResource': {
                    'vimLevelResourceType': 'Deployment',
                    'resourceId': 'test-test1-756757f8f-xcwmt'
                }
            }
        ],
        'vnfcInfo': [{
            'id': 'vnfc_info1',
            'vduId': 'vdu_id',
            'vnfcResourceInfoId': 'id2',
            'vnfcState': 'STARTED'
        }, {
            'id': 'vnfc info id',
            'vduId': 'vdu_id',
            'vnfcResourceInfoId': 'id2',
            'vnfcState': 'STARTED'
        }],
        'scaleStatus': [{
            'aspectId': 'aspect'
        }]
    },
    'metadata': {
    }
}

_inst2 = copy.deepcopy(_inst1)
_inst2.update({
    'vnfConfigurableProperties': {
        'isAutoscaleEnabled': True
    },
    'instantiationState': 'INSTANTIATED'
})

_inst3 = copy.deepcopy(_inst1)
_inst3.update({
    'vnfConfigurableProperties': {
        'isAutoscaleEnabled': False
    },
    'instantiationState': 'INSTANTIATED'
})

_inst4 = copy.deepcopy(_inst1)
_inst4.update({
    'vnfConfigurableProperties': {
        'isAutohealEnabled': False
    },
    'instantiationState': 'INSTANTIATED'
})

_inst5 = copy.deepcopy(_inst1)
_inst5.update({
    'vnfConfigurableProperties': {
        'isAutohealEnabled': True
    },
    'instantiationState': 'INSTANTIATED'
})

datetime_test = datetime.datetime.fromisoformat(
    '2022-06-22T01:23:45.678Z'.replace('Z', '+00:00'))


class TestPrometheusPluginPmEvent(base.TestCase):
    def setUp(self):
        super(TestPrometheusPluginPmEvent, self).setUp()
        objects.register_all()
        self.context = context.get_admin_context()
        self.request = mock.Mock()
        self.request.context = self.context
        self.controller = prometheus_plugin_controller.PmEventController()
        plugin.PrometheusPluginPm._instance = None

    def tearDown(self):
        super(TestPrometheusPluginPmEvent, self).tearDown()
        # delete singleton object
        plugin.PrometheusPluginPm._instance = None

    def test_pm_event_config_false(self):
        self.config_fixture.config(
            group='prometheus_plugin', performance_management=False)
        self.assertRaises(
            sol_ex.PrometheusPluginNotEnabled,
            self.controller.pm_event, self.request, {})

    def test_pm_exception(self):
        self.config_fixture.config(
            group='prometheus_plugin', performance_management=True)
        result = self.controller.pm_event(self.request, {})
        self.assertEqual(204, result.status)


class TestPrometheusPluginPmThreshold(base.TestCase):
    def setUp(self):
        super(TestPrometheusPluginPmThreshold, self).setUp()
        objects.register_all()
        self.context = context.get_admin_context()
        self.request = mock.Mock()
        self.request.context = self.context
        self.controller = prometheus_plugin_controller.PmThresholdController()
        plugin.PrometheusPluginThreshold._instance = None

    def tearDown(self):
        super(TestPrometheusPluginPmThreshold, self).tearDown()
        # delete singleton object
        plugin.PrometheusPluginThreshold._instance = None

    def test_pm_threshold_config_false(self):
        self.config_fixture.config(
            group='prometheus_plugin', performance_management=False)
        self.assertRaises(
            sol_ex.PrometheusPluginNotEnabled,
            self.controller.pm_threshold, self.request, {})

    def test_pm_exception(self):
        self.config_fixture.config(
            group='prometheus_plugin', performance_management=True)
        result = self.controller.pm_threshold(self.request, {})
        self.assertEqual(204, result.status)


class TestPrometheusPluginFm(base.TestCase):
    def setUp(self):
        super(TestPrometheusPluginFm, self).setUp()
        objects.register_all()
        self.context = context.get_admin_context()
        self.request = mock.Mock()
        self.request.context = self.context
        self.controller = prometheus_plugin_controller.FmAlertController()
        plugin.PrometheusPluginFm._instance = None

    def tearDown(self):
        super(TestPrometheusPluginFm, self).tearDown()
        # delete singleton object
        plugin.PrometheusPluginFm._instance = None

    def test_fm_config_false(self):
        self.config_fixture.config(
            group='prometheus_plugin', fault_management=False)
        self.assertRaises(
            sol_ex.PrometheusPluginNotEnabled,
            self.controller.alert, self.request, {})

    @mock.patch.object(fm_alarm_utils, 'get_not_cleared_alarms')
    @mock.patch.object(inst_utils, 'get_inst')
    def test_fm_firing(self, mock_inst, mock_alarms):
        self.config_fixture.config(
            group='prometheus_plugin', fault_management=True)
        mock_alarms.return_value = []
        mock_inst.return_value = objects.VnfInstanceV2.from_dict(_inst1)
        result = self.controller.alert(self.request, _body_fm1)
        self.assertEqual(204, result.status)

    @mock.patch.object(fm_alarm_utils, 'get_not_cleared_alarms')
    def test_fm_firing_exception(self, mock_alarms):
        self.config_fixture.config(
            group='prometheus_plugin', fault_management=True)
        mock_alarms.side_effect = Exception("test exception")
        result = self.controller.alert(self.request, _body_fm1)
        self.assertEqual(204, result.status)

    @mock.patch.object(fm_alarm_utils, 'get_not_cleared_alarms')
    @mock.patch.object(inst_utils, 'get_inst')
    def test_fm_firing_mismatch(self, mock_inst, mock_alarms):
        self.config_fixture.config(
            group='prometheus_plugin', fault_management=True)
        mock_alarms.return_value = []
        mock_inst.return_value = objects.VnfInstanceV2.from_dict(_inst1)
        result = self.controller.alert(self.request, _body_fm3)
        self.assertEqual(204, result.status)
        result = self.controller.alert(self.request, _body_fm4)
        self.assertEqual(204, result.status)

    @mock.patch.object(fm_alarm_utils, 'get_not_cleared_alarms')
    @mock.patch.object(inst_utils, 'get_inst')
    def test_fm_already_firing(self, mock_inst, mock_alarms):
        self.config_fixture.config(
            group='prometheus_plugin', fault_management=True)
        mock_alarms.return_value = [
            objects.AlarmV1.from_dict(_not_cleared_alarms)]
        mock_inst.return_value = objects.VnfInstanceV2.from_dict(_inst1)
        result = self.controller.alert(self.request, _body_fm1)
        self.assertEqual(204, result.status)

    @mock.patch.object(fm_alarm_utils, 'get_not_cleared_alarms')
    @mock.patch.object(inst_utils, 'get_inst')
    def test_fm_resolved(self, mock_inst, mock_alarms):
        self.config_fixture.config(
            group='prometheus_plugin', fault_management=True)
        mock_alarms.return_value = [
            objects.AlarmV1.from_dict(_not_cleared_alarms)]
        mock_inst.return_value = objects.VnfInstanceV2.from_dict(_inst1)
        result = self.controller.alert(self.request, _body_fm2)
        self.assertEqual(204, result.status)

    @mock.patch.object(fm_alarm_utils, 'get_not_cleared_alarms')
    @mock.patch.object(inst_utils, 'get_inst')
    def test_fm_set_callback(self, mock_inst, mock_alarms):
        self.config_fixture.config(
            group='prometheus_plugin', fault_management=True)
        mock_alarms.return_value = [
            objects.AlarmV1.from_dict(_not_cleared_alarms)]
        mock_inst.return_value = objects.VnfInstanceV2.from_dict(_inst1)
        _plugin = plugin.PrometheusPluginFm.instance()
        _plugin.set_callback(None)
        result = self.controller.alert(self.request, _body_fm2)
        self.assertEqual(204, result.status)
        mock_alarms.return_value = []
        result = self.controller.alert(self.request, _body_fm1)
        self.assertEqual(204, result.status)


class TestPrometheusPluginAutoHealing(base.TestCase):
    def setUp(self):
        super(TestPrometheusPluginAutoHealing, self).setUp()
        objects.register_all()
        self.context = context.get_admin_context()
        self.request = mock.Mock()
        self.request.context = self.context
        self.controller = prometheus_plugin_controller.AutoHealingController()
        plugin.PrometheusPluginAutoHealing._instance = None

    def tearDown(self):
        super(TestPrometheusPluginAutoHealing, self).tearDown()
        # delete singleton object
        plugin.PrometheusPluginAutoHealing._instance = None

    def test_auto_healing_config_false(self):
        self.config_fixture.config(
            group='prometheus_plugin', auto_healing=False)
        self.assertRaises(
            sol_ex.PrometheusPluginNotEnabled,
            self.controller.auto_healing, self.request, {})

    @mock.patch.object(inst_utils, 'get_inst')
    def test_auto_healing_no_autoheal_enabled(self, mock_inst):
        self.config_fixture.config(
            group='prometheus_plugin', auto_healing=True)
        mock_inst.return_value = objects.VnfInstanceV2.from_dict(_inst4)
        result = self.controller.auto_healing(
            self.request, _body_heal)
        self.assertEqual(204, result.status)

    @mock.patch.object(inst_utils, 'get_inst')
    def test_auto_healing_is_autoheal_enabled(self, mock_inst):
        self.config_fixture.config(
            group='prometheus_plugin', auto_healing=True)
        mock_inst.return_value = objects.VnfInstanceV2.from_dict(_inst5)
        result = self.controller.auto_healing(self.request, _body_heal)
        self.assertEqual(204, result.status)

    @mock.patch.object(inst_utils, 'get_inst')
    def test_auto_healing_multiple_continue(self, mock_inst):
        self.config_fixture.config(
            group='prometheus_plugin', auto_healing=True)
        mock_inst.return_value = objects.VnfInstanceV2.from_dict(_inst5)
        result = self.controller.auto_healing(
            self.request, _body_heal_continue)
        self.assertEqual(204, result.status)

    @mock.patch.object(inst_utils, 'get_inst')
    def test_auto_healing_not_instantiated(self, mock_inst):
        self.config_fixture.config(
            group='prometheus_plugin', auto_healing=True)
        mock_inst.return_value = objects.VnfInstanceV2.from_dict(_inst1)
        result = self.controller.auto_healing(
            self.request, _body_heal)
        self.assertEqual(204, result.status)


class TestPrometheusPluginAutoScaling(base.TestCase):
    def setUp(self):
        super(TestPrometheusPluginAutoScaling, self).setUp()
        objects.register_all()
        self.context = context.get_admin_context()
        self.request = mock.Mock()
        self.request.context = self.context
        self.controller = prometheus_plugin_controller.AutoScalingController()
        plugin.PrometheusPluginAutoScaling._instance = None

    def tearDown(self):
        super(TestPrometheusPluginAutoScaling, self).tearDown()
        # delete singleton object
        plugin.PrometheusPluginAutoScaling._instance = None

    def test_auto_scaling_config_false(self):
        self.config_fixture.config(
            group='prometheus_plugin', auto_scaling=False)
        self.assertRaises(
            sol_ex.PrometheusPluginNotEnabled,
            self.controller.auto_scaling, self.request, {})

    @mock.patch.object(inst_utils, 'get_inst')
    def test_auto_scaling_no_autoscale_enabled(self, mock_inst):
        self.config_fixture.config(
            group='prometheus_plugin', auto_scaling=True)
        mock_inst.return_value = objects.VnfInstanceV2.from_dict(_inst3)
        result = self.controller.auto_scaling(
            self.request, _body_scale)
        self.assertEqual(204, result.status)

    @mock.patch.object(inst_utils, 'get_inst')
    def test_auto_scaling_is_autoscale_enabled(self, mock_inst):
        self.config_fixture.config(
            group='prometheus_plugin', auto_scaling=True)
        mock_inst.return_value = objects.VnfInstanceV2.from_dict(_inst2)
        result = self.controller.auto_scaling(self.request, _body_scale)
        self.assertEqual(204, result.status)

    @mock.patch.object(inst_utils, 'get_inst')
    def test_auto_scaling_set_callback(self, mock_inst):
        self.config_fixture.config(
            group='prometheus_plugin', auto_scaling=True)
        _plugin = plugin.PrometheusPluginAutoScaling.instance()
        _plugin.set_callback(None)
        mock_inst.return_value = objects.VnfInstanceV2.from_dict(_inst2)
        result = self.controller.auto_scaling(self.request, _body_scale)
        self.assertEqual(204, result.status)

    def test_auto_scaling_error_body(self):
        self.config_fixture.config(
            group='prometheus_plugin', auto_scaling=True)
        result = self.controller.auto_scaling(self.request, {})
        self.assertEqual(204, result.status)

    @mock.patch.object(inst_utils, 'get_inst')
    def test_auto_scaling_multiple_continue(self, mock_inst):
        self.config_fixture.config(
            group='prometheus_plugin', auto_scaling=True)
        mock_inst.return_value = objects.VnfInstanceV2.from_dict(_inst2)
        result = self.controller.auto_scaling(
            self.request, _body_scale_continue)
        self.assertEqual(204, result.status)

    @mock.patch.object(inst_utils, 'get_inst')
    def test_auto_scaling_not_instantiated(self, mock_inst):
        self.config_fixture.config(
            group='prometheus_plugin', auto_scaling=True)
        mock_inst.return_value = objects.VnfInstanceV2.from_dict(_inst1)
        result = self.controller.auto_scaling(
            self.request, _body_scale)
        self.assertEqual(204, result.status)
