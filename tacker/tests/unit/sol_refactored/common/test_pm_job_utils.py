# Copyright (C) 2022 FUJITSU
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

from oslo_utils import uuidutils
from unittest import mock

from tacker import context
from tacker.sol_refactored.api import api_version
from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.common import pm_job_utils
from tacker.sol_refactored import objects
from tacker.tests import base


class TestPmJobUtils(base.BaseTestCase):

    def setUp(self):
        super(TestPmJobUtils, self).setUp()
        objects.register_all()
        self.context = context.get_admin_context()
        self.context.api_version = api_version.APIVersion('2.1.0')

    @mock.patch.object(objects.base.TackerPersistentObject, 'get_by_id')
    def test_update_report(self, mock_pm):
        _PmJobCriteriaV2 = objects.VnfPmJobCriteriaV2(
            performanceMetric=['VCpuUsageMeanVnf.VNF'],
            performanceMetricGroup=['VirtualisedComputeResource'],
            collectionPeriod=10,
            reportingPeriod=11,
            reportingBoundary='2000-05-23',
        )
        _SubscriptionAuthentication = objects.SubscriptionAuthentication(
            authType=['BASIC'],
            paramsBasic=objects.SubscriptionAuthentication_ParamsBasic(
                username='test_name',
                password='test_pwd'
            )
        )
        mock_pm.return_value = objects.PmJobV2(
            id='pm_job_1',
            objectType='VNF',
            objectInstanceIds=['id_1'],
            subObjectInstanceIds=['sub_id_1', 'sub_id_2'],
            criteria=_PmJobCriteriaV2,
            callbackUri='callbackuri',
            authentication=_SubscriptionAuthentication
        )
        report = objects.PerformanceReportV2(
            id=uuidutils.generate_uuid(),
            jobId='pm_job_1',
        )

        result = pm_job_utils.update_report(self.context, 'pm_job_1',
                                            report, '2008-01-03 08:04:34',
                                            'endpoint')
        href = result.reports[0].href
        self.assertEqual('pm_job_1', result.id)
        self.assertEqual(
            f'endpoint/vnfpm/v2/pm_jobs/pm_job_1/reports/{report.id}', href)

    @mock.patch.object(objects.base.TackerPersistentObject, 'get_all')
    def test_get_pm_job_all(self, mock_pm):
        mock_pm.return_value = [objects.PmJobV2(id='pm_job_1')]

        result = pm_job_utils.get_pm_job_all(context)
        self.assertEqual('pm_job_1', result[0].id)

    @mock.patch.object(objects.base.TackerPersistentObject, 'get_by_id')
    def test_get_pm_job(self, mock_pm):
        mock_pm.return_value = objects.PmJobV2(id='pm_job_1')

        result = pm_job_utils.get_pm_job(context, 'pm_job_1')
        self.assertEqual('pm_job_1', result.id)

    @mock.patch.object(objects.base.TackerPersistentObject, 'get_by_id')
    def test_get_pm_job_error(self, mock_pm):
        mock_pm.return_value = None
        self.assertRaises(
            sol_ex.PMJobNotExist,
            pm_job_utils.get_pm_job, context=context, pm_job_id='pm_job-1'
        )

    @mock.patch.object(objects.base.TackerPersistentObject, 'get_by_filter')
    def test_get_pm_report(self, mock_pm):
        mock_pm.return_value = [objects.PerformanceReportV2(id='report_1',
                                                            jobId='pm_job_1')]

        result = pm_job_utils.get_pm_report(context, 'pm_job_1', 'report_1')
        self.assertEqual('pm_job_1', result.jobId)

        result = pm_job_utils.get_pm_report(context, 'pm_job_1')
        self.assertEqual('pm_job_1', result[0].jobId)

    @mock.patch.object(objects.base.TackerPersistentObject, 'get_by_filter')
    def test_get_pm_report_error(self, mock_pm):
        mock_pm.return_value = None
        self.assertRaises(
            sol_ex.PMReportNotExist,
            pm_job_utils.get_pm_report, context=context,
            pm_job_id='pm_job_1', report_id='report_1'
        )

    def test_pm_job_href(self):
        result = pm_job_utils.pm_job_href('pm_job_1', 'endpoint')
        self.assertEqual('endpoint/vnfpm/v2/pm_jobs/pm_job_1', result)

    def test_pm_job_links(self):
        pm_job = objects.PmJobV2(id='pm_job_1', objectInstanceIds=["id_1"])
        result = pm_job_utils.make_pm_job_links(pm_job, 'endpoint')
        href = result.self.href
        self.assertEqual('endpoint/vnfpm/v2/pm_jobs/pm_job_1', href)
