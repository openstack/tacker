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
import requests

from unittest import mock

from tacker import context
from tacker.sol_refactored.api import api_version
from tacker.sol_refactored.common import config
from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.common import pm_job_utils
from tacker.sol_refactored.common.prometheus_plugin import (
    PrometheusPluginThreshold)
from tacker.sol_refactored.common import subscription_utils as subsc_utils
from tacker.sol_refactored.controller.vnflcm_view import BaseViewBuilder
from tacker.sol_refactored.controller.vnflcm_view import Pager
from tacker.sol_refactored.controller import vnfpm_v2
from tacker.sol_refactored.controller import vnfpm_view
from tacker.sol_refactored.controller.vnfpm_view import PmJobViewBuilder
from tacker.sol_refactored import objects
from tacker.tests import base

CONF = config.CONF


class TestVnfpmV2(base.BaseTestCase):

    def setUp(self):
        super(TestVnfpmV2, self).setUp()
        objects.register_all()
        self.context = context.get_admin_context()
        self.context.api_version = api_version.APIVersion("2.1.0")
        self.request = mock.Mock()
        self.request.context = self.context
        self.controller = vnfpm_v2.VnfPmControllerV2()
        self.endpoint = CONF.v2_vnfm.endpoint
        self._pm_job_view = vnfpm_view.PmJobViewBuilder(self.endpoint)

    def test_check_performance_metric_or_group(self):
        vnfpm_v2._check_performance_metric_or_group(
            obj_type='Vnf',
            metric_group=['VirtualisedComputeResource'],
            performance_metric=['VCpuUsageMeanVnf.VNF'])

        self.assertRaises(sol_ex.PMJobInvalidRequest,
                          vnfpm_v2._check_performance_metric_or_group,
                          obj_type='Vnf',
                          metric_group=['VirtualisedComputeResource',
                                        'VnfInternalCp'],
                          performance_metric=['VCpuUsageMeanVnf.VNF'])

        self.assertRaises(sol_ex.PMJobInvalidRequest,
                          vnfpm_v2._check_performance_metric_or_group,
                          obj_type='Vnf',
                          metric_group=['VirtualisedComputeResource'],
                          performance_metric=['ByteIncomingVnfExtCp.VNF'])

    def test_create_error_1(self):
        _PmJobCriteriaV2 = {
            'performanceMetric': ['VCpuUsageMeanVnf.VNF'],
            'performanceMetricGroup': ['VirtualisedComputeResource'],
            'collectionPeriod': 10,
            'reportingPeriod': 11,
            'reportingBoundary': '2022-08-05T02:24:46Z',
        }
        _SubscriptionAuthentication = {
            'authType': ['BASIC'],
            'paramsBasic': {
                'userName': 'test_name',
                'password': 'test_pwd'
            }
        }
        body = {
            "objectType": "Vnf",
            "objectInstanceIds": ["id_1", "id_2", "id_3"],
            "subObjectInstanceIds": ["sub_id_1", "sub_id_2"],
            "criteria": _PmJobCriteriaV2,
            "authentication": _SubscriptionAuthentication,
            "callbackUri": 'callbackuri',
        }
        self.assertRaises(sol_ex.PMJobInvalidRequest,
                          self.controller.create,
                          request=self.request, body=body)

    def test_create_error_2(self):
        _PmJobCriteriaV2 = {
            'performanceMetric': [],
            'performanceMetricGroup': [],
            'collectionPeriod': 10,
            'reportingPeriod': 11,
            'reportingBoundary': '2022-08-05T02:24:46Z',
        }
        _SubscriptionAuthentication = {
            'authType': ['BASIC'],
            'paramsBasic': {
                'userName': 'test_name',
                'password': 'test_pwd'
            }
        }
        body = {
            'objectType': 'Vnf',
            'objectInstanceIds': ['id_1'],
            'subObjectInstanceIds': ['sub_id_1', 'sub_id_2'],
            'criteria': _PmJobCriteriaV2,
            'callbackUri': 'callbackuri',
            'authentication': _SubscriptionAuthentication
        }
        self.assertRaises(sol_ex.PMJobInvalidRequest,
                          self.controller.create,
                          request=self.request, body=body)

    def test_create_error_3(self):
        _PmJobCriteriaV2 = {
            'performanceMetric': ['VCpuUsageMeanVnf.VNF'],
            'performanceMetricGroup': ['error-test'],
            'collectionPeriod': 10,
            'reportingPeriod': 11,
            'reportingBoundary': '2022-08-05T02:24:46Z',
        }
        _SubscriptionAuthentication = {
            'authType': ['BASIC'],
            'paramsBasic': {
                'userName': 'test_name',
                'password': 'test_pwd'
            }
        }
        body = {
            'objectType': 'Vnf',
            'objectInstanceIds': ['id_1'],
            'subObjectInstanceIds': ['sub_id_1', 'sub_id_2'],
            'criteria': _PmJobCriteriaV2,
            'callbackUri': 'callbackuri',
            'authentication': _SubscriptionAuthentication
        }
        self.assertRaises(sol_ex.PMJobInvalidRequest,
                          self.controller.create,
                          request=self.request, body=body)

    def test_create_error_4(self):
        _PmJobCriteriaV2 = {
            'performanceMetric': ['error.VNF'],
            'performanceMetricGroup': ['VirtualisedComputeResource'],
            'collectionPeriod': 10,
            'reportingPeriod': 11,
            'reportingBoundary': '2022-08-05T02:24:46Z',
        }
        _SubscriptionAuthentication = {
            'authType': ['BASIC'],
            'paramsBasic': {
                'userName': 'test_name',
                'password': 'test_pwd'
            }
        }
        body = {
            'objectType': 'Vnf',
            'objectInstanceIds': ['id_1'],
            'subObjectInstanceIds': ['sub_id_1', 'sub_id_2'],
            'criteria': _PmJobCriteriaV2,
            'callbackUri': 'callbackuri',
            'authentication': _SubscriptionAuthentication
        }
        self.assertRaises(sol_ex.PMJobInvalidRequest,
                          self.controller.create,
                          request=self.request, body=body)

    @mock.patch.object(objects.base.TackerPersistentObject, 'get_by_id')
    def test_create_error_5(self, mock_inst):
        mock_inst.return_value = objects.VnfInstanceV2(
            id='dummy-vnfInstanceId-1', vnfdId='dummy-vnfdId-1',
            vnfProvider='dummy-vnfProvider-1',
            instantiationState='NOT_INSTANTIATED',
            vnfProductName='dummy-vnfProductName-1-1',
            vnfSoftwareVersion='1.0', vnfdVersion='1.0',
            vnfInstanceName='dummy-vnfInstanceName-1')
        _PmJobCriteriaV2 = {
            'performanceMetric': ['VCpuUsageMeanVnf.VNF'],
            'performanceMetricGroup': ['VirtualisedComputeResource'],
            'collectionPeriod': 10,
            'reportingPeriod': 11,
            'reportingBoundary': '2022-08-05T02:24:46Z',
        }
        _SubscriptionAuthentication = {
            'authType': ['BASIC'],
            'paramsBasic': {
                'userName': 'test_name',
                'password': 'test_pwd'
            }
        }
        body = {
            'objectType': 'Vnf',
            'objectInstanceIds': ['id_1'],
            'subObjectInstanceIds': ['sub_id_1', 'sub_id_2'],
            'criteria': _PmJobCriteriaV2,
            'callbackUri': 'callbackuri',
            'authentication': _SubscriptionAuthentication
        }
        self.assertRaises(sol_ex.VnfInstanceIsNotInstantiated,
                          self.controller.create,
                          request=self.request, body=body)

    @mock.patch.object(objects.base.TackerPersistentObject, 'get_by_id')
    def test_create_error6(self, mock_inst):
        mock_inst.return_value = objects.VnfInstanceV2(
            id='dummy-vnfInstanceId-1', vnfdId='dummy-vnfdId-1',
            vnfProvider='dummy-vnfProvider-1',
            instantiationState='INSTANTIATED',
            vnfProductName='dummy-vnfProductName-1-1',
            vnfSoftwareVersion='1.0', vnfdVersion='1.0',
            vnfInstanceName='dummy-vnfInstanceName-1')
        _PmJobCriteriaV2 = {
            "performanceMetric": ["VCpuUsageMeanVnf.VNF"],
            "performanceMetricGroup": ["VirtualisedComputeResource"],
            "collectionPeriod": 10,
            "reportingPeriod": 11,
            "reportingBoundary": "invalid datetime format",
        }
        _SubscriptionAuthentication = {
            'authType': ['BASIC'],
            'paramsBasic': {
                'userName': 'test_name',
                'password': 'test_pwd'
            }
        }
        body = {
            "objectType": "Vnf",
            "objectInstanceIds": ["id_1"],
            "subObjectInstanceIds": ["sub_id_1", "sub_id_2"],
            "criteria": _PmJobCriteriaV2,
            "authentication": _SubscriptionAuthentication,
            "callbackUri": "http://127.0.0.1:6789/notification",
            'metadata': {"metadata": "example"}
        }
        self.assertRaises(
            sol_ex.SolValidationError,
            self.controller.create, request=self.request, body=body)

    @mock.patch.object(objects.base.TackerPersistentObject, 'create')
    @mock.patch.object(subsc_utils, 'test_notification')
    @mock.patch.object(objects.base.TackerPersistentObject, 'get_by_id')
    def test_create_201(self, mock_inst, mock_notifi, mock_create):
        mock_inst.return_value = objects.VnfInstanceV2(
            id='dummy-vnfInstanceId-1', vnfdId='dummy-vnfdId-1',
            vnfProvider='dummy-vnfProvider-1',
            instantiationState='INSTANTIATED',
            vnfProductName='dummy-vnfProductName-1-1',
            vnfSoftwareVersion='1.0', vnfdVersion='1.0',
            vnfInstanceName='dummy-vnfInstanceName-1')
        mock_notifi.return_value = None
        mock_create.return_value = None
        _PmJobCriteriaV2 = {
            "performanceMetric": ["VCpuUsageMeanVnf.VNF"],
            "performanceMetricGroup": ["VirtualisedComputeResource"],
            "collectionPeriod": 10,
            "reportingPeriod": 11,
            "reportingBoundary": "2022-08-05T02:24:46Z",
        }
        _SubscriptionAuthentication = {
            'authType': ['BASIC'],
            'paramsBasic': {
                'userName': 'test_name',
                'password': 'test_pwd'
            }
        }
        body = {
            "objectType": "Vnf",
            "objectInstanceIds": ["id_1"],
            "subObjectInstanceIds": ["sub_id_1", "sub_id_2"],
            "criteria": _PmJobCriteriaV2,
            "authentication": _SubscriptionAuthentication,
            "callbackUri": "http://127.0.0.1:6789/notification",
            'metadata': {"metadata": "example"}
        }

        result = self.controller.create(request=self.request, body=body)
        self.assertEqual(201, result.status)

    @mock.patch.object(Pager, 'get_link')
    @mock.patch.object(BaseViewBuilder, 'detail_list')
    @mock.patch.object(objects.base.TackerPersistentObject, 'get_all')
    @mock.patch.object(vnfpm_view.PmJobViewBuilder, 'parse_pager')
    @mock.patch.object(vnfpm_view.PmJobViewBuilder, 'parse_filter')
    @mock.patch.object(vnfpm_view.PmJobViewBuilder, 'parse_selector')
    def test_index(self, mock_parse_selector, mock_parse_filter,
                   mock_parse_pager,
                   mock_pm,
                   mock_detail_list,
                   mock_get_link):
        mock_parse_selector.return_value = 'selector'
        mock_parse_filter.return_value = 'filter'

        request = requests.Request()
        request.GET = {
            'filter': 'pm_job_id', 'nextpage_opaque_marker': 'marker'}
        request.url = 'url'
        page_size = CONF.v2_vnfm.vnf_instance_page_size
        pager = Pager(request.GET.get('nextpage_opaque_marker'),
                      request.url,
                      page_size)
        mock_parse_pager.return_value = pager

        mock_pm.return_value = [objects.PmJobV2(id='pm_job_1')]
        mock_detail_list.return_value = 1
        mock_get_link.return_value = 'url'

        result = self.controller.index(self.request)
        self.assertEqual(200, result.status)

    @mock.patch.object(objects.base.TackerPersistentObject, 'get_by_id')
    def test_show(self, mock_pm):
        mock_pm.return_value = objects.PmJobV2(
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
        result = self.controller.show(self.request, 'pm_job_1')
        self.assertEqual(200, result.status)

    @mock.patch.object(objects.base.TackerPersistentObject, 'update')
    @mock.patch.object(objects.base.TackerPersistentObject, 'get_by_id')
    @mock.patch.object(subsc_utils, 'test_notification')
    def test_update(self, mock_notifi, mock_pm, mock_update):
        mock_notifi.return_value = None
        mock_pm.return_value = objects.PmJobV2(id='pm_job_1')
        mock_update.return_value = None

        _SubscriptionAuthentication = {
            'authType': ['BASIC'],
            'paramsBasic': {
                'userName': 'test_name',
                'password': 'test_pwd'
            }
        }
        body = {
            'callbackUri': 'callbackUri',
            'authentication': _SubscriptionAuthentication
        }

        result = self.controller.update(request=self.request, id='id',
                                        body=body)
        self.assertEqual(200, result.status)
        self.assertEqual("callbackUri", result.body["callbackUri"])
        self.assertNotIn("authentication", result.body)

        body = {
            'authentication': _SubscriptionAuthentication
        }

        result = self.controller.update(request=self.request, id='id',
                                        body=body)
        self.assertEqual({}, result.body)

    @mock.patch.object(objects.base.TackerPersistentObject, 'get_by_filter')
    @mock.patch.object(objects.base.TackerPersistentObject, 'get_by_id')
    def test_delete(self, mock_pm, mock_report):
        mock_pm.return_value = objects.PmJobV2(id='pm_job_1')
        mock_report.return_value = [objects.PerformanceReportV2(
            id='report_id',
            jobId='pm_job_1')]
        result = self.controller.delete(self.request, 'pm_job_1')
        self.assertEqual(204, result.status)

    @mock.patch.object(PmJobViewBuilder, 'report_detail')
    @mock.patch.object(pm_job_utils, 'get_pm_report')
    def test_report_get(self, mock_get, mock_report):
        mock_get.return_value = 'pm_report'
        mock_report.return_value = 'pm_report_resp'
        result = self.controller.report_get(
            self.request, 'pm_job_id', 'report_id')
        self.assertEqual(200, result.status)

    def test_allowed_content_types(self):
        result = self.controller.allowed_content_types('update')
        top = ['application/merge-patch+json', 'application/json',
               'text/plain']
        self.assertEqual(top, result)

        result = self.controller.allowed_content_types('create')
        top = ['application/json', 'text/plain']
        self.assertEqual(top, result)

    def test_supported_api_version(self):
        result = self.controller.supported_api_versions('create')
        self.assertEqual(['2.1.0'], result)

    # 'performanceMetric' doesn't match objectType
    def test_create_pm_threshold_error_1(self):
        _ThresholdCriteria_V2 = {
            'performanceMetric': 'ByteIncomingVnfIntCp.VNF',
            'thresholdType': 'SIMPLE',
            'simpleThresholdDetails': {
                'thresholdValue': 500.5,
                'hysteresis': 10.5
            }
        }
        _SubscriptionAuthentication = {
            'authType': ['BASIC'],
            'paramsBasic': {
                'userName': 'test_name',
                'password': 'test_pwd'
            }
        }
        body = {
            "objectType": "Vnf",
            "objectInstanceId": "id_1",
            "subObjectInstanceIds": ["sub_id_1", "sub_id_2"],
            "criteria": _ThresholdCriteria_V2,
            "callbackUri": 'callbackuri',
            "authentication": _SubscriptionAuthentication,
            'metadata': {"metadata": "example"}
        }
        self.assertRaises(sol_ex.PMThresholdInvalidRequest,
                          self.controller.create_threshold,
                          request=self.request, body=body)

    # 'simpleThresholdDetails' is not assigned
    def test_create_pm_threshold_error_2(self):
        _ThresholdCriteria_V2 = {
            'performanceMetric': 'VCpuUsageMeanVnf.VNF',
            'thresholdType': 'SIMPLE',
        }
        _SubscriptionAuthentication = {
            'authType': ['BASIC'],
            'paramsBasic': {
                'userName': 'test_name',
                'password': 'test_pwd'
            }
        }
        body = {
            "objectType": "Vnf",
            "objectInstanceId": "id_1",
            "subObjectInstanceIds": ["sub_id_1", "sub_id_2"],
            "criteria": _ThresholdCriteria_V2,
            "callbackUri": 'callbackuri',
            "authentication": _SubscriptionAuthentication,
            'metadata': {"metadata": "example"}
        }
        self.assertRaises(sol_ex.PMThresholdInvalidRequest,
                          self.controller.create_threshold,
                          request=self.request, body=body)

    # vnf instance status: "NOT_INSTANTIATED"
    @mock.patch.object(objects.base.TackerPersistentObject, 'get_by_id')
    def test_create_pm_threshold_error_5(self, mock_inst):
        mock_inst.return_value = objects.VnfInstanceV2(
            id='dummy-vnfInstanceId-1', vnfdId='dummy-vnfdId-1',
            vnfProvider='dummy-vnfProvider-1',
            instantiationState='NOT_INSTANTIATED',
            vnfProductName='dummy-vnfProductName-1-1',
            vnfSoftwareVersion='1.0', vnfdVersion='1.0',
            vnfInstanceName='dummy-vnfInstanceName-1')
        _ThresholdCriteria_V2 = {
            'performanceMetric': 'VCpuUsageMeanVnf.VNF',
            'thresholdType': 'SIMPLE',
            'simpleThresholdDetails': {
                'thresholdValue': 100.5,
                'hysteresis': 10.5
            }
        }
        _SubscriptionAuthentication = {
            'authType': ['BASIC'],
            'paramsBasic': {
                'userName': 'test_name',
                'password': 'test_pwd'
            }
        }
        body = {
            "objectType": "Vnf",
            "objectInstanceId": "id_1",
            "subObjectInstanceIds": ["sub_id_1", "sub_id_2"],
            "criteria": _ThresholdCriteria_V2,
            "callbackUri": 'callbackuri',
            "authentication": _SubscriptionAuthentication,
            'metadata': {"metadata": "example"}
        }
        self.assertRaises(sol_ex.VnfInstanceIsNotInstantiated,
                          self.controller.create_threshold,
                          request=self.request, body=body)

    @mock.patch.object(objects.base.TackerPersistentObject, 'create')
    @mock.patch.object(PrometheusPluginThreshold, 'create_threshold')
    @mock.patch.object(subsc_utils, 'test_notification')
    @mock.patch.object(objects.base.TackerPersistentObject, 'get_by_id')
    def test_create_pm_threshold(
            self, mock_inst, mock_notifi, mock_create_threshold, mock_create):
        mock_inst.return_value = objects.VnfInstanceV2(
            id='dummy-vnfInstanceId-1', vnfdId='dummy-vnfdId-1',
            vnfProvider='dummy-vnfProvider-1',
            instantiationState='INSTANTIATED',
            vnfProductName='dummy-vnfProductName-1-1',
            vnfSoftwareVersion='1.0', vnfdVersion='1.0',
            vnfInstanceName='dummy-vnfInstanceName-1')
        mock_notifi.return_value = None
        mock_create_threshold.return_value = None
        mock_create.return_value = None

        _ThresholdCriteria_V2 = {
            'performanceMetric': 'VCpuUsageMeanVnf.VNF',
            'thresholdType': 'SIMPLE',
            'simpleThresholdDetails': {
                'thresholdValue': 100.5,
                'hysteresis': 10.5
            }
        }
        _SubscriptionAuthentication = {
            'authType': ['BASIC'],
            'paramsBasic': {
                'userName': 'test_name',
                'password': 'test_pwd'
            }
        }
        body = {
            "objectType": "Vnf",
            "objectInstanceId": "id_1",
            "subObjectInstanceIds": ["sub_id_1", "sub_id_2"],
            "criteria": _ThresholdCriteria_V2,
            "callbackUri": 'callbackuri',
            "authentication": _SubscriptionAuthentication,
            'metadata': {"metadata": "example"}
        }

        result = self.controller.create_threshold(
            request=self.request, body=body)
        self.assertEqual(201, result.status)

    @mock.patch.object(Pager, 'get_link')
    @mock.patch.object(BaseViewBuilder, 'detail_list')
    @mock.patch.object(objects.base.TackerPersistentObject, 'get_all')
    @mock.patch.object(vnfpm_view.PmThresholdViewBuilder, 'parse_pager')
    @mock.patch.object(vnfpm_view.PmThresholdViewBuilder, 'parse_filter')
    @mock.patch.object(vnfpm_view.PmThresholdViewBuilder, 'parse_selector')
    def test_pm_threshold_index(self, mock_parse_selector, mock_parse_filter,
                                mock_parse_pager, mock_pm, mock_detail_list,
                                mock_get_link):
        mock_parse_selector.return_value = 'selector'
        mock_parse_filter.return_value = 'filter'

        request = requests.Request()
        request.GET = {
            'filter': 'threshold', 'nextpage_opaque_marker': 'marker'}
        request.url = 'url'
        page_size = CONF.v2_vnfm.vnfpm_pmthreshold_page_size
        pager = Pager(request.GET.get('nextpage_opaque_marker'),
                      request.url,
                      page_size)
        mock_parse_pager.return_value = pager

        mock_pm.return_value = [objects.ThresholdV2(id='pm_threshold_1')]
        mock_detail_list.return_value = 1
        mock_get_link.return_value = 'url'

        result = self.controller.index_threshold(self.request)
        self.assertEqual(200, result.status)

    @mock.patch.object(objects.base.TackerPersistentObject, 'get_by_id')
    def test_pm_threshold_show(self, mock_pm):
        mock_pm.return_value = objects.ThresholdV2(
            id='pm_threshold_1',
            objectInstanceId="id_1",
            authentication=objects.SubscriptionAuthentication(
                authType=["BASIC"],
                paramsBasic=objects.SubscriptionAuthentication_ParamsBasic(
                    userName='test',
                    password='test'
                ),
            )
        )
        result = self.controller.show_threshold(self.request, 'pm_threshold_1')
        self.assertEqual(200, result.status)

    @mock.patch.object(objects.base.TackerPersistentObject, 'get_by_id')
    def test_pm_threshold_show_not_exist(self, mock_pm):
        mock_pm.return_value = None
        self.assertRaises(
            sol_ex.PMThresholdNotExist, self.controller.show_threshold,
            request=self.request, thresholdId='pm_threshold_1')

    @mock.patch.object(objects.base.TackerPersistentObject, 'update')
    @mock.patch.object(objects.base.TackerPersistentObject, 'get_by_id')
    @mock.patch.object(subsc_utils, 'test_notification')
    def test_pm_threshold_update(self, mock_notifi, mock_pm, mock_update):
        mock_notifi.return_value = None
        mock_pm.return_value = objects.ThresholdV2(
            id='pm_threshold_1',
            objectInstanceId="id_1",
            callbackUri='http://127.0.0.1/callback',
            authentication=objects.SubscriptionAuthentication(
                authType=["BASIC"],
                paramsBasic=objects.SubscriptionAuthentication_ParamsBasic(
                    userName='test',
                    password='test'
                ),
            )
        )
        mock_update.return_value = None

        _SubscriptionAuthentication = {
            'authType': ['BASIC'],
            'paramsBasic': {
                'userName': 'test_name',
                'password': 'test_pwd'
            }
        }
        body = {
            'callbackUri': 'callbackUri',
            'authentication': _SubscriptionAuthentication
        }

        result = self.controller.update_threshold(
            request=self.request, thresholdId='id',
            body=body)
        self.assertEqual(200, result.status)
        self.assertEqual('callbackUri', result.body['callbackUri'])
        self.assertNotIn("authentication", result.body)

        body = {
            'authentication': _SubscriptionAuthentication
        }

        result = self.controller.update_threshold(
            request=self.request, thresholdId='id',
            body=body)
        self.assertEqual({}, result.body)

    @mock.patch.object(objects.base.TackerPersistentObject, 'get_by_id')
    def test_pm_threshold_update_not_exist(self, mock_pm):
        mock_pm.return_value = None
        _SubscriptionAuthentication = {
            'authType': ['BASIC'],
            'paramsBasic': {
                'userName': 'test_name',
                'password': 'test_pwd'
            }
        }
        body = {
            'callbackUri': 'callbackuri_update',
            'authentication': _SubscriptionAuthentication
        }
        self.assertRaises(
            sol_ex.PMThresholdNotExist, self.controller.update_threshold,
            request=self.request, thresholdId='id', body=body)

    @mock.patch.object(PrometheusPluginThreshold, 'create_threshold')
    @mock.patch.object(objects.base.TackerPersistentObject, 'get_by_id')
    def test_pm_threshold_delete(
            self, mock_pm, mock_create_threshold):
        mock_pm.return_value = objects.ThresholdV2(id='pm_threshold_1')
        mock_create_threshold.return_value = None

        result = self.controller.delete_threshold(
            self.request, 'pm_threshold_1')
        self.assertEqual(204, result.status)

    @mock.patch.object(objects.base.TackerPersistentObject, 'get_by_id')
    def test_pm_threshold_delete_not_exist(self, mock_pm):
        mock_pm.return_value = None
        self.assertRaises(
            sol_ex.PMThresholdNotExist, self.controller.delete_threshold,
            request=self.request, thresholdId='pm_threshold_1')
