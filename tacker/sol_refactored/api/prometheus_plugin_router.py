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

from tacker.sol_refactored.api.policies import vnffm_v1 as vnffm_policy_v1
from tacker.sol_refactored.api.policies import vnfpm_v2 as vnfpm_policy_v2
from tacker.sol_refactored.api import prometheus_plugin_wsgi as prom_wsgi
from tacker.sol_refactored.controller import prometheus_plugin_controller


class PmEventRouter(prom_wsgi.PrometheusPluginAPIRouter):
    controller = prom_wsgi.PrometheusPluginResource(
        prometheus_plugin_controller.PmEventController(),
        policy_name=vnfpm_policy_v2.POLICY_NAME_PROM_PLUGIN)
    route_list = [("", {"POST": "pm_event"})]


class PmThresholdRouter(prom_wsgi.PrometheusPluginAPIRouter):
    controller = prom_wsgi.PrometheusPluginResource(
        prometheus_plugin_controller.PmThresholdController(),
        policy_name=vnfpm_policy_v2.POLICY_NAME_PROM_PLUGIN)
    route_list = [("", {"POST": "pm_threshold"})]


class FmAlertRouter(prom_wsgi.PrometheusPluginAPIRouter):
    controller = prom_wsgi.PrometheusPluginResource(
        prometheus_plugin_controller.FmAlertController(),
        policy_name=vnffm_policy_v1.POLICY_NAME_PROM_PLUGIN)
    route_list = [("", {"POST": "alert"})]


class AutoHealingRouter(prom_wsgi.PrometheusPluginAPIRouter):
    controller = prom_wsgi.PrometheusPluginResource(
        prometheus_plugin_controller.AutoHealingController(),
        policy_name=vnfpm_policy_v2.POLICY_NAME_PROM_PLUGIN)
    route_list = [("", {"POST": "auto_healing"})]


class AutoScalingRouter(prom_wsgi.PrometheusPluginAPIRouter):
    controller = prom_wsgi.PrometheusPluginResource(
        prometheus_plugin_controller.AutoScalingController(),
        policy_name=vnfpm_policy_v2.POLICY_NAME_PROM_PLUGIN)
    route_list = [("", {"POST": "auto_scaling"})]
