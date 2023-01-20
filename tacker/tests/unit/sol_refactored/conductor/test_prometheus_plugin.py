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

import time

from tacker import context
from tacker.sol_refactored.common import vnflcm_utils
from tacker.sol_refactored.conductor import conductor_v2
from tacker.sol_refactored.conductor import prometheus_plugin_driver as pp_drv
from tacker.sol_refactored import objects
from tacker.tests.unit.db import base as db_base

from unittest import mock


_req1 = {
    'flavourId': 'flavour'
}

_req2 = {
    'flavourId': 'flavour',
    'additionalParams': {},
}

_req3 = {
    'flavourId': 'flavour',
    'additionalParams': {
        'monitoring': {
            'monitorName': 'prometheus',
            'driverType': 'external',
            'targetsInfo': [
                {
                    'prometheusHost':
                        'prometheusHost',
                    'prometheusHostPort': '22',
                    'authInfo': {
                        'ssh_username': 'ssh_username',
                        'ssh_password': 'ssh_password'
                    },
                    'alertRuleConfigPath':
                        'alertRuleConfigPath',
                    'prometheusReloadApiEndpoint':
                        'prometheusReloadApiEndpoint'
                }
            ]
        }
    },
}

_inst1 = {
    'id': '25b9b9d0-2461-4109-866e-a7767375415b',
    'vnfdId': 'vnfdId',
    'vnfProvider': 'vnfProvider',
    'vnfProductName': 'vnfProductName',
    'vnfSoftwareVersion': 'vnfSoftwareVersion',
    'vnfdVersion': 'vnfdVersion',
    'instantiationState': 'NOT_INSTANTIATED',
}

_inst2 = {
    'id': '25b9b9d0-2461-4109-866e-a7767375415b',
    'vnfdId': 'vnfdId',
    'vnfProvider': 'vnfProvider',
    'vnfProductName': 'vnfProductName',
    'vnfSoftwareVersion': 'vnfSoftwareVersion',
    'vnfdVersion': 'vnfdVersion',
    'instantiationState': 'NOT_INSTANTIATED',
    'metadata': {}
}

_inst3 = {
    'id': '25b9b9d0-2461-4109-866e-a7767375415b',
    'vnfdId': 'vnfdId',
    'vnfProvider': 'vnfProvider',
    'vnfProductName': 'vnfProductName',
    'vnfSoftwareVersion': 'vnfSoftwareVersion',
    'vnfdVersion': 'vnfdVersion',
    'instantiationState': 'NOT_INSTANTIATED',
    'metadata': {
        'monitoring': {
            'monitorName': 'prometheus',
            'driverType': 'external',
            'targetsInfo': [
                {
                    'prometheusHost':
                        'prometheusHost',
                    'prometheusHostPort': '22',
                    'authInfo': {
                        'ssh_username': 'ssh_username',
                        'ssh_password': 'ssh_password'
                    },
                    'alertRuleConfigPath':
                        'alertRuleConfigPath',
                    'prometheusReloadApiEndpoint':
                        'prometheusReloadApiEndpoint'
                }
            ]
        }
    }
}


class TestPrometheusPlugin(db_base.SqlTestCase):
    def setUp(self):
        super(TestPrometheusPlugin, self).setUp()
        objects.register_all()
        self.context = context.get_admin_context()
        self.request = mock.Mock()
        self.request.context = self.context
        self.timer_test = (None, None)
        self.config_fixture.config(
            group='prometheus_plugin', performance_management=True)
        self.conductor = conductor_v2.ConductorV2()
        pp_drv.PrometheusPluginDriver._instance = None

    def tearDown(self):
        super(TestPrometheusPlugin, self).tearDown()
        # delete singleton object
        pp_drv.PrometheusPluginDriver._instance = None

    @mock.patch.object(vnflcm_utils, 'scale')
    def test_trigger_scale(self, mock_do_scale):
        scale_req = {
            'type': 'SCALE_OUT',
            'aspectId': 'vdu',
        }
        self.conductor.trigger_scale(
            self.context, 'vnf_instance_id', scale_req)

    def test_constructor(self):
        self.config_fixture.config(
            group='prometheus_plugin', performance_management=True)

    def test_driver_stub(self):
        self.config_fixture.config(
            group='prometheus_plugin', performance_management=False)
        pp_drv.PrometheusPluginDriver._instance = None
        drv = pp_drv.PrometheusPluginDriver.instance()
        drv.trigger_scale(None, None, None)
        self.config_fixture.config(
            group='prometheus_plugin', performance_management=True)
        drv = pp_drv.PrometheusPluginDriver.instance()

    def test_driver_constructor(self):
        self.config_fixture.config(
            group='prometheus_plugin', performance_management=True)
        pp_drv.PrometheusPluginDriver.instance()
        self.assertRaises(
            SystemError,
            pp_drv.PrometheusPluginDriver)

    def test_conductor_vnfm_auto_heal_queue(self):
        self.config_fixture.config(
            group='prometheus_plugin', auto_healing=True)
        pp_drv.PrometheusPluginDriver._instance = None
        self.conductor.prom_driver = pp_drv.PrometheusPluginDriver.instance()
        self.config_fixture.config(
            group='prometheus_plugin', timer_interval=1)
        # queueing test
        id = 'test_id'
        self.conductor.enqueue_auto_heal_instance(
            self.context, id, 'id')
        self.conductor.enqueue_auto_heal_instance(
            self.context, id, 'id2')
        self.assertEqual(
            self.conductor.prom_driver.timer_map[id].queue,
            {'id', 'id2'})
        # Since the timeout period of `VnfmAutoHealTimer` is set to 1 second,
        # it is also necessary to wait for 1 second before asserting.
        time.sleep(1)
        # remove_timer test
        self.conductor.dequeue_auto_heal_instance(self.context, id)
        self.assertNotIn(id, self.conductor.prom_driver.timer_map)
        # remove_timer test: invalid_id
        self.conductor.dequeue_auto_heal_instance(
            self.context, 'invalid_id')

    @mock.patch.object(vnflcm_utils, 'heal')
    def test_conductor_timer_expired(self, mock_do_heal):
        self.config_fixture.config(
            group='prometheus_plugin', auto_healing=True)
        pp_drv.PrometheusPluginDriver._instance = None
        self.conductor.prom_driver = pp_drv.PrometheusPluginDriver.instance()
        self.conductor.prom_driver._timer_expired(
            self.context, 'test_id', ['id'])

    def expired(self, context, id, queue):
        queue.sort()
        self.timer_test = (id, queue)

    def test_timer(self):
        # queueing test
        timer = pp_drv.VnfmAutoHealTimer(self.context, 'id', 1, self.expired)
        timer.add_vnfc_info_id('1')
        timer.add_vnfc_info_id('3')
        # Since the timeout period of `VnfmAutoHealTimer` is set to 1 second,
        # it is also necessary to wait for 1 second before asserting.
        time.sleep(1)
        self.assertEqual(self.timer_test[0], 'id')
        self.assertEqual(self.timer_test[1], ['1', '3'])

    def test_timer_cancel(self):
        # cancel test
        timer = pp_drv.VnfmAutoHealTimer(self.context, 'id2', 1, self.expired)
        timer.add_vnfc_info_id('5')
        timer.cancel()
        # Since the timeout period of `VnfmAutoHealTimer` is set to 1 second,
        # it is also necessary to wait for 1 second before asserting.
        time.sleep(1)
        self.assertIsNone(self.timer_test[0])
        self.assertIsNone(self.timer_test[1])

    def test_timer_destructor(self):
        # method call after cancel()
        timer = pp_drv.VnfmAutoHealTimer(self.context, 'id', 1, self.expired)
        timer.cancel()
        timer.expire()
        timer.add_vnfc_info_id(['4'])
        timer.cancel()
        timer.__del__()
