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
import os
import urllib

import yaml

from tacker.sol_refactored import objects
from tacker.tests.functional import base_v2
from tacker.tests import utils as base_utils

VNFPM_V2_VERSION = "2.1.0"
VNFFM_V1_VERSION = "1.3.0"


class BaseVnfLcmKubernetesV2Test(base_v2.BaseTackerTestV2):
    """Base test case class for SOL v2 kubernetes functional tests."""

    @classmethod
    def setUpClass(cls):
        super(BaseVnfLcmKubernetesV2Test, cls).setUpClass()

        k8s_vim_info = cls.get_k8s_vim_info()
        cls.auth_url = k8s_vim_info.interfaceInfo['endpoint']
        cls.bearer_token = k8s_vim_info.accessInfo['bearer_token']
        cls.ssl_ca_cert = k8s_vim_info.interfaceInfo['ssl_ca_cert']

        cls.fake_prometheus_ip = cls.get_controller_tacker_ip()

    @classmethod
    def tearDownClass(cls):
        super(BaseVnfLcmKubernetesV2Test, cls).tearDownClass()

    @classmethod
    def get_k8s_vim_info(cls):
        vim_params = yaml.safe_load(base_utils.read_file('local-k8s-vim.yaml'))

        vim_info = objects.VimConnectionInfo(
            interfaceInfo={
                'endpoint': vim_params['auth_url'],
                'ssl_ca_cert': vim_params.get('ssl_ca_cert')
            },
            accessInfo={
                'region': 'RegionOne',
                'bearer_token': vim_params['bearer_token']
            }
        )
        return vim_info

    @classmethod
    def get_k8s_vim_id(cls, use_helm=False):
        vim_list = cls.list_vims(cls)
        if len(vim_list.values()) == 0:
            assert False, "vim_list is Empty: Default VIM is missing"

        for vim_list in vim_list.values():
            for vim in vim_list:
                if vim['name'] == 'vim-kubernetes' and not use_helm:
                    return vim['id']
                if vim['name'] == 'vim-kubernetes-helm' and use_helm:
                    return vim['id']
        return None

    @classmethod
    def create_vnf_package(cls, sample_path, user_data={}, image_path=None,
                           provider=None, namespace=None,
                           mgmt_driver=None):

        return super().create_vnf_package(sample_path, user_data=user_data,
                                          image_path=image_path,
                                          provider=provider,
                                          namespace=namespace,
                                          mgmt_driver=mgmt_driver)

    @classmethod
    def get_controller_tacker_ip(cls):
        cur_dir = os.path.dirname(__file__)
        script_path = os.path.join(
            cur_dir, "../tools/test-setup-fake-prometheus-server.sh")
        with open(script_path, 'r') as f_obj:
            content = f_obj.read()
        ip = content.split('TEST_REMOTE_URI')[1].split(
            'http://')[1].split('"')[0]
        return ip

    def list_vims(self):
        path = "/v1.0/vims.json"
        resp, body = self.tacker_client.do_request(path, "GET")
        return body

    def list_fm_subscriptions(self, filter_expr=None):
        path = "/vnffm/v1/subscriptions"
        if filter_expr:
            path = "{}?{}".format(path, urllib.parse.urlencode(filter_expr))
        return self.tacker_client.do_request(
            path, "GET", version=VNFFM_V1_VERSION)

    def create_fm_alarm(self, req_body):
        path = "/alert"
        return self.tacker_client.do_request(
            path, "POST", body=req_body, version=VNFFM_V1_VERSION)

    def list_fm_alarm(self, filter_expr=None):
        path = "/vnffm/v1/alarms"
        if filter_expr:
            path = "{}?{}".format(path, urllib.parse.urlencode(filter_expr))
        return self.tacker_client.do_request(
            path, "GET", version=VNFFM_V1_VERSION)

    def show_fm_alarm(self, alarm_id):
        path = f"/vnffm/v1/alarms/{alarm_id}"
        return self.tacker_client.do_request(
            path, "GET", version=VNFFM_V1_VERSION)

    def update_fm_alarm(self, alarm_id, req_body):
        path = f"/vnffm/v1/alarms/{alarm_id}"
        return self.tacker_client.do_request(
            path, "PATCH", body=req_body, version=VNFFM_V1_VERSION)

    def update_pm_job(self, pm_job_id, req_body):
        path = f"/vnfpm/v2/pm_jobs/{pm_job_id}"
        return self.tacker_client.do_request(
            path, "PATCH", body=req_body, version=VNFPM_V2_VERSION)

    def create_pm_event(self, req_body):
        path = "/pm_event"
        return self.tacker_client.do_request(
            path, "POST", body=req_body, version=VNFPM_V2_VERSION)

    def list_pm_job(self, filter_expr=None):
        path = "/vnfpm/v2/pm_jobs"
        if filter_expr:
            path = "{}?{}".format(path, urllib.parse.urlencode(filter_expr))
        return self.tacker_client.do_request(
            path, "GET", version=VNFPM_V2_VERSION)

    def show_pm_job_report(self, pm_job_id, report_id):
        path = f"/vnfpm/v2/pm_jobs/{pm_job_id}/reports/{report_id}"
        return self.tacker_client.do_request(
            path, "GET", version=VNFPM_V2_VERSION)

    def update_pm_threshold(self, pm_threshold_id, req_body):
        path = f"/vnfpm/v2/thresholds/{pm_threshold_id}"
        return self.tacker_client.do_request(
            path, "PATCH", body=req_body, version=VNFPM_V2_VERSION,
            content_type="application/merge-patch+json")

    def pm_threshold(self, req_body):
        path = "/pm_threshold"
        return self.tacker_client.do_request(
            path, "POST", body=req_body, version=VNFPM_V2_VERSION)

    def list_pm_threshold(self, filter_expr=None):
        path = "/vnfpm/v2/thresholds"
        if filter_expr:
            path = "{}?{}".format(path, urllib.parse.urlencode(filter_expr))
        return self.tacker_client.do_request(
            path, "GET", version=VNFPM_V2_VERSION)
