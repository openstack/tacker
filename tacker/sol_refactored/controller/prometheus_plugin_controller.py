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

from tacker.sol_refactored.api import wsgi as sol_wsgi
from tacker.sol_refactored.common import config as cfg
from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.common import monitoring_plugin_base as mon_base

CONF = cfg.CONF


class PmEventController(sol_wsgi.SolAPIController):
    def pm_event(self, request, body):
        if not CONF.prometheus_plugin.performance_management:
            raise sol_ex.PrometheusPluginNotEnabled(
                name='Performance management')
        cls = mon_base.get_class(
            CONF.prometheus_plugin.performance_management_package,
            CONF.prometheus_plugin.performance_management_class)
        mon_base.MonitoringPlugin.get_instance(cls).alert(
            request=request, body=body)
        return sol_wsgi.SolResponse(204, None)


class PmThresholdController(sol_wsgi.SolAPIController):
    def pm_threshold(self, request, body):
        if not CONF.prometheus_plugin.performance_management:
            raise sol_ex.PrometheusPluginNotEnabled(
                name='Performance management')
        cls = mon_base.get_class(
            CONF.prometheus_plugin.performance_management_threshold_package,
            CONF.prometheus_plugin.performance_management_threshold_class)
        mon_base.MonitoringPlugin.get_instance(cls).alert(
            request=request, body=body)
        return sol_wsgi.SolResponse(204, None)


class FmAlertController(sol_wsgi.SolAPIController):
    def alert(self, request, body):
        if not CONF.prometheus_plugin.fault_management:
            raise sol_ex.PrometheusPluginNotEnabled(
                name='Fault management')
        cls = mon_base.get_class(
            CONF.prometheus_plugin.fault_management_package,
            CONF.prometheus_plugin.fault_management_class)
        mon_base.MonitoringPlugin.get_instance(cls).alert(
            request=request, body=body)
        return sol_wsgi.SolResponse(204, None)


class AutoHealingController(sol_wsgi.SolAPIController):
    def auto_healing(self, request, body):
        if not CONF.prometheus_plugin.auto_healing:
            raise sol_ex.PrometheusPluginNotEnabled(
                name='Auto healing')
        cls = mon_base.get_class(
            CONF.prometheus_plugin.auto_healing_package,
            CONF.prometheus_plugin.auto_healing_class)
        mon_base.MonitoringPlugin.get_instance(cls).alert(
            request=request, body=body)
        return sol_wsgi.SolResponse(204, None)


class AutoScalingController(sol_wsgi.SolAPIController):
    def auto_scaling(self, request, body):
        if not CONF.prometheus_plugin.auto_scaling:
            raise sol_ex.PrometheusPluginNotEnabled(
                name='Auto scaling')
        cls = mon_base.get_class(
            CONF.prometheus_plugin.auto_scaling_package,
            CONF.prometheus_plugin.auto_scaling_class)
        mon_base.MonitoringPlugin.get_instance(cls).alert(
            request=request, body=body)
        return sol_wsgi.SolResponse(204, None)
