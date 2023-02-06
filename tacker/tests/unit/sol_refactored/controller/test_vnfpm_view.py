# Copyright (C) 2021 Nippon Telegraph and Telephone Corporation
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
from tacker.tests import base
from unittest import mock

from tacker.sol_refactored.common import config
from tacker.sol_refactored.controller.vnflcm_view import BaseViewBuilder
from tacker.sol_refactored.controller.vnfpm_view import PmJobViewBuilder
from tacker.sol_refactored.controller.vnfpm_view import PmThresholdViewBuilder
from tacker.sol_refactored import objects


CONF = config.CONF


class TestPmJobViewBuilder(base.BaseTestCase):

    def setUp(self):
        super(TestPmJobViewBuilder, self).setUp()
        objects.register_all()
        self.context = context.get_admin_context()
        self.request = mock.Mock()
        self.request.context = self.context
        self.endpoint = CONF.v2_vnfm.endpoint

    @mock.patch.object(BaseViewBuilder, 'parse_filter')
    def test_parse_filter(self, mock_parse_filter):
        mock_parse_filter.return_value = 1
        result = PmJobViewBuilder(self.endpoint).parse_filter('filter_param')
        self.assertEqual(1, result)

    @mock.patch.object(BaseViewBuilder, 'parse_pager')
    def test_parse_pager(self, mock_parse_pager):
        mock_parse_pager.return_value = 1
        page_size = CONF.v2_vnfm.vnfpm_pmjob_page_size
        result = PmJobViewBuilder(self.endpoint).parse_pager(
            self.request, page_size)
        self.assertEqual(1, result)

    def test_detail(self):
        pm_job = objects.PmJobV2(
            id='pm_job_1',
            objectInstanceIds=["id_1"],
            authentication=objects.SubscriptionAuthentication(
                authType=["BASIC"],
                paramsBasic=objects.SubscriptionAuthentication_ParamsBasic(
                    userName='test',
                    password='test'
                ),
            )
        )
        result = PmJobViewBuilder(self.endpoint).detail(pm_job)
        self.assertEqual('pm_job_1', result.get('id'))

    @mock.patch.object(BaseViewBuilder, 'detail_list')
    def test_report_detail(self, mock_detail_list):
        mock_detail_list.return_value = 1
        result = PmJobViewBuilder(self.endpoint).detail_list(
            'pm_jobs', 'filters', 'selector', 'pager')
        self.assertEqual(1, result)


class TestPmThresholdViewBuilder(base.BaseTestCase):

    def setUp(self):
        super(TestPmThresholdViewBuilder, self).setUp()
        objects.register_all()
        self.context = context.get_admin_context()
        self.request = mock.Mock()
        self.request.context = self.context
        self.endpoint = CONF.v2_vnfm.endpoint

    @mock.patch.object(BaseViewBuilder, 'parse_filter')
    def test_parse_filter(self, mock_parse_filter):
        mock_parse_filter.return_value = 1
        result = PmThresholdViewBuilder(
            self.endpoint).parse_filter('filter_param')
        self.assertEqual(1, result)

    @mock.patch.object(BaseViewBuilder, 'parse_pager')
    def test_parse_pager(self, mock_parse_pager):
        mock_parse_pager.return_value = 1
        page_size = CONF.v2_vnfm.vnfpm_pmthreshold_page_size
        result = PmThresholdViewBuilder(self.endpoint).parse_pager(
            self.request, page_size)
        self.assertEqual(1, result)

    def test_detail(self):
        pm_threshold = objects.ThresholdV2(
            id='pm_threshold_1',
            objectInstanceId='id_1',
            authentication=objects.SubscriptionAuthentication(
                authType=["BASIC"],
                paramsBasic=objects.SubscriptionAuthentication_ParamsBasic(
                    userName='test',
                    password='test'
                ),
            )
        )
        result = PmThresholdViewBuilder(self.endpoint).detail(pm_threshold)
        self.assertEqual('pm_threshold_1', result.get('id'))
