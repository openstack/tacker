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

from oslo_log import log as logging
from tacker.sol_refactored.common import config as cfg
from tacker.sol_refactored.common import http_client

LOG = logging.getLogger(__name__)

CONF = cfg.CONF


class PrometheusPluginDriverStub():
    def request_scale(self, context, vnf_instance_id, scale_req):
        pass


class PrometheusPluginDriver():
    _instance = None

    @staticmethod
    def instance():
        if PrometheusPluginDriver._instance is None:
            if (CONF.prometheus_plugin.auto_scaling or
                    CONF.prometheus_plugin.fault_management or
                    CONF.prometheus_plugin.performance_management):
                PrometheusPluginDriver()
            else:
                stub = PrometheusPluginDriverStub()
                PrometheusPluginDriver._instance = stub
        return PrometheusPluginDriver._instance

    def __init__(self):
        if PrometheusPluginDriver._instance:
            raise SystemError("Not constructor but instance() should be used.")
        auth_handle = http_client.KeystonePasswordAuthHandle(
            auth_url=CONF.keystone_authtoken.auth_url,
            username=CONF.keystone_authtoken.username,
            password=CONF.keystone_authtoken.password,
            project_name=CONF.keystone_authtoken.project_name,
            user_domain_name=CONF.keystone_authtoken.user_domain_name,
            project_domain_name=CONF.keystone_authtoken.project_domain_name)
        self.client = http_client.HttpClient(auth_handle)
        PrometheusPluginDriver._instance = self

    def request_scale(self, context, vnf_instance_id, scale_req):
        ep = CONF.v2_vnfm.endpoint
        url = f'{ep}/vnflcm/v2/vnf_instances/{vnf_instance_id}/scale'
        resp, _ = self.client.do_request(
            url, "POST", context=context, body=scale_req, version="2.0.0")
        LOG.info("AutoHealing request is processed: %d.", resp.status_code)
