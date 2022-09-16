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

import webob

from tacker import context
from tacker.sol_refactored.common import http_client
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
        self.config_fixture.config(
            group='prometheus_plugin', performance_management=True)
        self.conductor = conductor_v2.ConductorV2()

    @mock.patch.object(http_client.HttpClient, 'do_request')
    def test_requst_scale(self, mock_do_request):
        resp = webob.Response()
        resp.status_code = 202
        mock_do_request.return_value = resp, {}
        scale_req = {
            'type': 'SCALE_OUT',
            'aspect_id': 'vdu',
        }
        self.conductor.request_scale(
            self.context, 'vnf_instance_id', scale_req)

    def test_constructor(self):
        self.config_fixture.config(
            group='prometheus_plugin', performance_management=True)
        pp_drv.PrometheusPluginDriver._instance = None

    def test_driver_stub(self):
        self.config_fixture.config(
            group='prometheus_plugin', performance_management=False)
        pp_drv.PrometheusPluginDriver._instance = None
        drv = pp_drv.PrometheusPluginDriver.instance()
        drv = pp_drv.PrometheusPluginDriver.instance()
        drv.request_scale(None, None, None)
        self.config_fixture.config(
            group='prometheus_plugin', performance_management=True)
        pp_drv.PrometheusPluginDriver._instance = None
        drv = pp_drv.PrometheusPluginDriver.instance()

    def test_driver_constructor(self):
        self.config_fixture.config(
            group='prometheus_plugin', performance_management=True)
        pp_drv.PrometheusPluginDriver._instance = None
        pp_drv.PrometheusPluginDriver.instance()
        self.assertRaises(
            SystemError,
            pp_drv.PrometheusPluginDriver)
