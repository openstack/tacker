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
import freezegun
import paramiko
import sys
import webob

from tacker import context
from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.common import http_client
from tacker.sol_refactored.common import monitoring_plugin_base as mon_base
from tacker.sol_refactored.common import pm_job_utils
from tacker.sol_refactored.common import prometheus_plugin
from tacker.sol_refactored.common import vnf_instance_utils as inst_utils
from tacker.sol_refactored import objects
from tacker.tests.unit import base

from unittest import mock

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

_body_pm_alert1 = {
    'status': 'firing',
    'labels': {
        'receiver_type': 'tacker',
        'function_type': 'vnfpm',
        'job_id': '64e46b0e-887a-4691-8d2b-aa3d7b157e2c',
        'metric': 'VCpuUsageMeanVnf.'
                  '25b9b9d0-2461-4109-866e-a7767375415b',
        'object_instance_id': '25b9b9d0-2461-4109-866e-a7767375415b'
    },
    'annotations': {
        'value': '99',
    },
    'startsAt': '2022-06-21T23:47:36.453Z',
    'endsAt': '0001-01-01T00:00:00Z',
    'generatorURL': 'http://controller147:9090/graph?g0.expr='
                    'up%7Bjob%3D%22node%22%7D+%3D%3D+0&g0.tab=1',
    'fingerprint': '5ef77f1f8a3ecb8d'
}

# function_type mismatch
_body_pm_alert2 = copy.deepcopy(_body_pm_alert1)
_body_pm_alert2['labels']['function_type'] = 'vnffm'

# object_instance_id mismatch
_body_pm_alert3 = copy.deepcopy(_body_pm_alert1)
_body_pm_alert3['labels']['object_instance_id'] = 'obj_instance_mismatch'

# object_instance_id mismatch
_body_pm_alert4 = copy.deepcopy(_body_pm_alert1)
_body_pm_alert4['labels']['sub_object_instance_id'] = 'sub_object_mismatch'

_body_pm_alert5 = copy.deepcopy(_body_pm_alert1)
_body_pm_alert5['labels']['metric'] = 'ByteIncomingVnfIntCp'

_body_pm_alert6 = copy.deepcopy(_body_pm_alert1)
_body_pm_alert6['labels']['metric'] = 'InvalidMetric'

_body_pm1 = copy.copy(_body_base)
_body_pm1.update({
    'alerts': [
        _body_pm_alert1, _body_pm_alert2, _body_pm_alert3, _body_pm_alert4]
})

_body_pm2 = copy.copy(_body_base)
_body_pm2.update({
    'alerts': [_body_pm_alert5, _body_pm_alert6]
})

_pm_job = {
    'id': 'job_id',
    'objectType': 'Vnf',
    'objectInstanceIds': ['25b9b9d0-2461-4109-866e-a7767375415b'],
    'subObjectInstanceIds': [],
    'criteria': {
        'performanceMetric': [
            'VcpuUsageMeanVnf.25b9b9d0-2461-4109-866e-a7767375415b'
        ],
        'performanceMetricGroup': [
            'VirtualisedComputeResource',
            'InvalidGroupName'
        ],
        'collectionPeriod': 15,
        'reportingPeriod': 30,
        'reportingBoundary': '2022-06-23T04:56:00.910Z'
    },
    'callbackUri': '',
    'reports': [],
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
                },
                {
                    # invalid access info
                    'prometheusHost':
                        'prometheusHost',
                }
            ]
        }
    }
}

_pm_job2 = copy.deepcopy(_pm_job)
_pm_job2['objectType'] = 'VnfIntCp'
_pm_job2['criteria']['performanceMetric'] = ['ByteIncomingVnfIntCp']
_pm_job2['criteria']['performanceMetricGroup'] = [
    'VnfInternalCp', 'VnfExternalCp']

_pm_report = {
    'id': 'report_id',
    'jobId': 'pm_job_id',
    'entries': [{
        # objectType, InstanceId, Metric match the test
        # condition.
        'objectType': 'Vnf',
        'objectInstanceId':
            '25b9b9d0-2461-4109-866e-a7767375415b',
        'performanceMetric':
            'VCpuUsageMeanVnf.'
            '25b9b9d0-2461-4109-866e-a7767375415b',
        'performanceValues': [{
            # current_time - 60sec
            'timeStamp': '2022-06-22T01:22:45.678Z',
            'value': 12.3
        }, {
            # current_time - 30sec
            'timeStamp': '2022-06-22T01:23:15.678Z',
            'value': 45.6
        }]
    }, {
        # objectType, InstanceId, Metric do
        # not match the test condition.
        'objectType': 'Vnf',
        'objectInstanceId':
            '25b9b9d0-2461-4109-866e-a7767375415b',
        'subObjectInstanceId':
            'ebd40865-e3d9-4ac6-b7f0-0a8d2791d07f',
        'performanceMetric':
            'VCpuUsageMeanVnf.'
            '25b9b9d0-2461-4109-866e-a7767375415b',
        'performanceValues': [{
            # current_time - 30sec
            'timeStamp': '2022-06-22T01:23:15.678Z',
            'value': 45.6
        }]
    }, {
        # objectType, InstanceId, Metric do
        # not match the test condition.
        'objectType': 'Vnf',
        'objectInstanceId':
            '25b9b9d0-2461-4109-866e-a7767375415b',
        'performanceMetric':
            'VMemoryUsageMeanVnf.'
            '25b9b9d0-2461-4109-866e-a7767375415b',
        'performanceValues': [{
            # current_time - 5sec
            'timeStamp': '2022-06-22T01:23:40.678Z',
            'value': 78.9
        }]
    }, {
        # objectType, InstanceId, Metric do
        # not match the test condition.
        'objectType': 'Vnf',
        'objectInstanceId':
            'test_id',
        'performanceMetric':
            'VCpuUsageMeanVnf.test_id',
        'performanceValues': [{
            # current_time + 5sec
            'timeStamp': '2022-06-22T01:23:50.678Z',
            'value': 0.1
        }]
    }]
}

_pm_report2 = {
    'id': 'report_id',
    'jobId': 'pm_job_id',
    'entries': []
}

_inst_base = {
    'id': '25b9b9d0-2461-4109-866e-a7767375415b',
    'vnfdId': 'vnfdId',
    'vnfProvider': 'vnfProvider',
    'vnfProductName': 'vnfProductName',
    'vnfSoftwareVersion': 'vnfSoftwareVersion',
    'vnfdVersion': 'vnfdVersion',
    'instantiationState': 'NOT_INSTANTIATED',
}

_inst1 = copy.copy(_inst_base)
_inst1.update({
    'instantiatedVnfInfo': {
        'id': 'id',
        'vduId': 'vduId',
        'vnfcResourceInfo': [{
            'id': 'id2',
            'vduId': 'vduId2',
            'computeResource': {
                'vimLevelResourceType': 'Deployment',
                'resourceId': 'pod-pod1'
            },
            'metadata': {
                'hostname': 'node2',
            }
        }],
        'vnfcInfo': [{
            'id': 'vnfc_info1',
            'vduId': 'vdu_id',
            'vnfcResourceInfoId': 'id2',
            'vnfcState': 'STARTED'
        }]
    }
})

datetime_test = datetime.datetime.fromisoformat(
    '2022-06-22T01:23:45.678Z'.replace('Z', '+00:00'))


def unload_uuidsentinel():
    # Unload uuidsentinel module because it is conflict
    # with the freezegun module.
    if "tacker.tests.uuidsentinel" in sys.modules:
        del sys.modules["tacker.tests.uuidsentinel"]


class _ParamikoTest():
    def __init__(self):
        pass

    def connect(self, **kwargs):
        pass

    def remove(self, arg1):
        pass

    def put(self, a1, a2):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass


class TestPrometheusPluginPm(base.TestCase):
    def setUp(self):
        super(TestPrometheusPluginPm, self).setUp()
        objects.register_all()
        self.context = context.get_admin_context()
        self.request = mock.Mock()
        self.request.context = self.context
        prometheus_plugin.PrometheusPluginPm._instance = None

    def tearDown(self):
        super(TestPrometheusPluginPm, self).tearDown()
        # delete singleton object
        prometheus_plugin.PrometheusPluginPm._instance = None

    def test_constructor_error(self):
        self.config_fixture.config(
            group='prometheus_plugin', auto_scaling=False)
        mon_base.MonitoringPlugin.get_instance(
            prometheus_plugin.PrometheusPluginPm)
        self.assertRaises(
            SystemError,
            prometheus_plugin.PrometheusPluginPm)

    def test_constructor_stub(self):
        self.config_fixture.config(
            group='prometheus_plugin', auto_scaling=False)
        pp = mon_base.MonitoringPlugin.get_instance(
            prometheus_plugin.PrometheusPluginPm)
        self.assertIsInstance(pp._instance, mon_base.MonitoringPluginStub)
        pp = mon_base.MonitoringPlugin.get_instance(
            prometheus_plugin.PrometheusPluginPm)
        self.assertIsInstance(pp._instance, mon_base.MonitoringPluginStub)

    @mock.patch.object(pm_job_utils, 'get_pm_report')
    @mock.patch.object(pm_job_utils, 'get_pm_job')
    def test_pm(self, mock_pm_job, mock_pm_report):
        self.config_fixture.config(
            group='prometheus_plugin', performance_management=True)
        mock_pm_job.return_value = objects.PmJobV2.from_dict(_pm_job)
        mock_pm_report.return_value = [objects.PerformanceReportV2.from_dict(
            _pm_report)]
        pp = mon_base.MonitoringPlugin.get_instance(
            prometheus_plugin.PrometheusPluginPm)

        unload_uuidsentinel()
        with freezegun.freeze_time(datetime_test):
            result = pp._alert(self.request, body=_body_pm1)
            self.assertTrue(len(result) > 0)
            self.assertEqual(
                result[0]['objectInstanceId'],
                '25b9b9d0-2461-4109-866e-a7767375415b')

    @mock.patch.object(pm_job_utils, 'get_pm_report')
    @mock.patch.object(pm_job_utils, 'get_pm_job')
    def test_pm_metrics(self, mock_pm_job, mock_pm_report):
        self.config_fixture.config(
            group='prometheus_plugin', performance_management=True)
        mock_pm_job.return_value = objects.PmJobV2.from_dict(_pm_job)
        mock_pm_report.return_value = [objects.PerformanceReportV2.from_dict(
            _pm_report)]
        pp = mon_base.MonitoringPlugin.get_instance(
            prometheus_plugin.PrometheusPluginPm)
        unload_uuidsentinel()
        with freezegun.freeze_time(datetime_test):
            self.assertRaises(
                sol_ex.PrometheusPluginError,
                pp._alert, self.request, body=_body_pm2
            )

    @mock.patch.object(pm_job_utils, 'get_pm_report')
    @mock.patch.object(pm_job_utils, 'get_pm_job')
    def test_pm_report(self, mock_pm_job, mock_pm_report):
        self.config_fixture.config(
            group='prometheus_plugin', performance_management=True)
        mock_pm_job.return_value = objects.PmJobV2.from_dict(_pm_job)
        mock_pm_report.return_value = [objects.PerformanceReportV2.from_dict(
            _pm_report2)]
        pp = mon_base.MonitoringPlugin.get_instance(
            prometheus_plugin.PrometheusPluginPm)
        unload_uuidsentinel()
        with freezegun.freeze_time(datetime_test):
            result = pp._alert(self.request, body=_body_pm1)
            self.assertTrue(len(result) > 0)
            self.assertEqual(
                result[0]['objectInstanceId'],
                '25b9b9d0-2461-4109-866e-a7767375415b')
        mock_pm_report.return_value = None
        unload_uuidsentinel()
        with freezegun.freeze_time(datetime_test):
            result = pp._alert(self.request, body=_body_pm1)
            self.assertTrue(len(result) > 0)
            self.assertEqual(
                result[0]['objectInstanceId'],
                '25b9b9d0-2461-4109-866e-a7767375415b')

    @mock.patch.object(pm_job_utils, 'get_pm_report')
    @mock.patch.object(pm_job_utils, 'get_pm_job')
    def test_pm_datetime(self, mock_pm_job, mock_pm_report):
        self.config_fixture.config(
            group='prometheus_plugin', performance_management=True)
        mock_pm_job.return_value = objects.PmJobV2.from_dict(_pm_job)
        mock_pm_report.return_value = [objects.PerformanceReportV2.from_dict(
            _pm_report)]
        pp = mon_base.MonitoringPlugin.get_instance(
            prometheus_plugin.PrometheusPluginPm)
        unload_uuidsentinel()
        # a time pm job is already expired.
        datetime_now = datetime.datetime.fromisoformat(
            '2023-06-23T04:56:00.910+00:00')
        with freezegun.freeze_time(datetime_now):
            result = pp._alert(self.request, body=_body_pm1)
            self.assertTrue(len(result) == 0)
        # now < latest reporting time + reportingPeriod
        datetime_now = datetime.datetime.fromisoformat(
            '2022-06-22T01:23:25.678+00:00')
        with freezegun.freeze_time(datetime_now):
            result = pp._alert(self.request, body=_body_pm1)
            self.assertTrue(len(result) == 0)

    @mock.patch.object(pm_job_utils, 'get_pm_report')
    @mock.patch.object(pm_job_utils, 'get_pm_job')
    def test_pm_set_callback(self, mock_pm_job, mock_pm_report):
        self.config_fixture.config(
            group='prometheus_plugin', performance_management=True)
        mock_pm_job.return_value = objects.PmJobV2.from_dict(_pm_job)
        mock_pm_report.return_value = [objects.PerformanceReportV2.from_dict(
            _pm_report)]
        pp = mon_base.MonitoringPlugin.get_instance(
            prometheus_plugin.PrometheusPluginPm)
        pp.set_callback(None)
        unload_uuidsentinel()
        with freezegun.freeze_time(datetime_test):
            result = pp._alert(self.request, body=_body_pm1)
            self.assertTrue(len(result) > 0)
            self.assertEqual(
                result[0]['objectInstanceId'],
                '25b9b9d0-2461-4109-866e-a7767375415b')

    def test_pm_error_access_info(self):
        self.config_fixture.config(
            group='prometheus_plugin', performance_management=True)
        pp = mon_base.MonitoringPlugin.get_instance(
            prometheus_plugin.PrometheusPluginPm)
        job = copy.deepcopy(_pm_job)
        del job['metadata']
        job = objects.PmJobV2.from_dict(job)
        self.assertRaises(
            sol_ex.PrometheusPluginError,
            pp.delete_job, context=self.context, pm_job=job
        )
        job2 = copy.deepcopy(_pm_job)
        job2['metadata'] = {'monitoring': {}}
        job2 = objects.PmJobV2.from_dict(job2)
        self.assertRaises(
            sol_ex.PrometheusPluginError,
            pp.delete_job, context=self.context, pm_job=job2
        )

    @mock.patch.object(http_client.HttpClient, 'do_request')
    @mock.patch.object(paramiko.SFTPClient, 'from_transport')
    @mock.patch.object(paramiko, 'Transport')
    def test_delete_job(self, mock_paramiko, mock_sftp, mock_do_request):
        mock_paramiko.return_value = _ParamikoTest()
        mock_sftp.return_value = _ParamikoTest()
        resp = webob.Response()
        resp.status_code = 202
        mock_do_request.return_value = resp, {}
        self.config_fixture.config(
            group='prometheus_plugin', performance_management=True)
        pp = mon_base.MonitoringPlugin.get_instance(
            prometheus_plugin.PrometheusPluginPm)
        # noromal
        job = objects.PmJobV2.from_dict(_pm_job)
        pp.delete_job(context=self.context, pm_job=job)
        # error
        resp.status_code = 503
        pp.delete_job(context=self.context, pm_job=job)

    @mock.patch.object(http_client.HttpClient, 'do_request')
    @mock.patch.object(paramiko.SFTPClient, 'from_transport')
    @mock.patch.object(paramiko, 'Transport')
    @mock.patch.object(inst_utils, 'get_inst')
    def test_create_job(
            self, mock_inst, mock_paramiko, mock_sftp, mock_do_request):
        mock_paramiko.return_value = _ParamikoTest()
        mock_sftp.return_value = _ParamikoTest()
        resp = webob.Response()
        resp.status_code = 202
        mock_do_request.return_value = resp, {}
        mock_inst.return_value = objects.VnfInstanceV2.from_dict(_inst1)

        self.config_fixture.config(
            group='prometheus_plugin', performance_management=True)
        pp = mon_base.MonitoringPlugin.get_instance(
            prometheus_plugin.PrometheusPluginPm)
        # VirtualisedComputeResource
        job = objects.PmJobV2.from_dict(_pm_job)
        rule = pp.create_job(context=self.context, pm_job=job)
        self.assertTrue(len(rule['groups'][0]['rules']) > 0)
        # VnfInternalCp
        job = objects.PmJobV2.from_dict(_pm_job2)
        rule = pp.create_job(context=self.context, pm_job=job)
        self.assertTrue(len(rule['groups'][0]['rules']) > 0)
        self.assertTrue('interface="*"' in str(rule))

    @mock.patch.object(http_client.HttpClient, 'do_request')
    @mock.patch.object(paramiko.SFTPClient, 'from_transport')
    @mock.patch.object(paramiko, 'Transport')
    @mock.patch.object(inst_utils, 'get_inst')
    def test_create_job_subobj(
            self, mock_inst, mock_paramiko, mock_sftp, mock_do_request):
        mock_paramiko.return_value = _ParamikoTest()
        mock_sftp.return_value = _ParamikoTest()
        resp = webob.Response()
        resp.status_code = 202
        mock_do_request.return_value = resp, {}
        inst = objects.VnfInstanceV2.from_dict(_inst1)
        mock_inst.return_value = inst

        self.config_fixture.config(
            group='prometheus_plugin', performance_management=True)
        pp = mon_base.MonitoringPlugin.get_instance(
            prometheus_plugin.PrometheusPluginPm)
        # VirtualisedComputeResource
        job = copy.deepcopy(_pm_job)
        job['subObjectInstanceIds'] = ['vnfc_info1']
        job = objects.PmJobV2.from_dict(job)
        rule = pp.create_job(context=self.context, pm_job=job)
        self.assertTrue(len(rule['groups'][0]['rules']) > 0)
        self.assertEqual(
            rule['groups'][0]['rules'][0]['labels']['sub_object_instance_id'],
            job['subObjectInstanceIds'][0])
        # VnfInternalCp
        job = copy.deepcopy(_pm_job2)
        job['subObjectInstanceIds'] = ['test_if0']
        job = objects.PmJobV2.from_dict(job)
        rule = pp.create_job(context=self.context, pm_job=job)
        self.assertTrue(len(rule['groups'][0]['rules']) > 0)
        self.assertTrue('interface="test_if0"' in str(rule))

    @mock.patch.object(http_client.HttpClient, 'do_request')
    @mock.patch.object(paramiko.SFTPClient, 'from_transport')
    @mock.patch.object(paramiko, 'Transport')
    @mock.patch.object(inst_utils, 'get_inst')
    def test_create_job_error(
            self, mock_inst, mock_paramiko, mock_sftp, mock_do_request):
        mock_paramiko.return_value = _ParamikoTest()
        mock_sftp.return_value = _ParamikoTest()
        resp = webob.Response()
        resp.status_code = 202
        mock_do_request.return_value = resp, {}
        mock_inst.return_value = objects.VnfInstanceV2.from_dict(_inst1)

        self.config_fixture.config(
            group='prometheus_plugin', performance_management=True)
        pp = mon_base.MonitoringPlugin.get_instance(
            prometheus_plugin.PrometheusPluginPm)

        # invalid object type
        job = copy.deepcopy(_pm_job)
        job['objectType'] = 'invalid_type'
        job = objects.PmJobV2.from_dict(job)
        self.assertRaises(
            sol_ex.PrometheusPluginError,
            pp.create_job, context=self.context, pm_job=job
        )
        # invalid performanceMetric or performanceMetricGroup.
        job = copy.deepcopy(_pm_job)
        job['criteria']['performanceMetric'] = []
        job['criteria']['performanceMetricGroup'] = []
        job = objects.PmJobV2.from_dict(job)
        self.assertRaises(
            sol_ex.PrometheusPluginError,
            pp.create_job, context=self.context, pm_job=job
        )
        # Invalid performanceMetric or performanceMetricGroup.
        job = copy.deepcopy(_pm_job2)
        job['criteria']['performanceMetric'] = []
        job['criteria']['performanceMetricGroup'] = ['VnfExternalCp']
        job = objects.PmJobV2.from_dict(job)
        self.assertRaises(
            sol_ex.PrometheusPluginError,
            pp.create_job, context=self.context, pm_job=job
        )
        # no instantiatedVnfInfo
        mock_inst.return_value = objects.VnfInstanceV2.from_dict(_inst_base)
        job = objects.PmJobV2.from_dict(_pm_job)
        self.assertRaises(
            sol_ex.PrometheusPluginError,
            pp.create_job, context=self.context, pm_job=job
        )
        # no instantiatedVnfInfo with subObjectInstanceIds
        job = copy.deepcopy(_pm_job2)
        job['subObjectInstanceIds'] = ['test_if0']
        job = objects.PmJobV2.from_dict(job)
        self.assertRaises(
            sol_ex.PrometheusPluginError,
            pp.create_job, context=self.context, pm_job=job
        )
        # no valid computeResource
        ins = copy.deepcopy(_inst1)
        _ = ins['instantiatedVnfInfo']['vnfcResourceInfo'][0]
        _['computeResource'] = {}
        mock_inst.return_value = objects.VnfInstanceV2.from_dict(ins)
        job = objects.PmJobV2.from_dict(_pm_job)
        self.assertRaises(
            sol_ex.PrometheusPluginError,
            pp.create_job, context=self.context, pm_job=job
        )

        # no vnfcInfo
        ins = copy.deepcopy(_inst1)
        del ins['instantiatedVnfInfo']['vnfcInfo']
        mock_inst.return_value = objects.VnfInstanceV2.from_dict(ins)
        job = copy.deepcopy(_pm_job)
        job['subObjectInstanceIds'] = ['vnfc_info1']
        job = objects.PmJobV2.from_dict(job)
        self.assertRaises(
            sol_ex.PrometheusPluginError,
            pp.create_job, context=self.context, pm_job=job
        )

        # vnfcInfo mismatch
        ins = copy.deepcopy(_inst1)
        ins['instantiatedVnfInfo']['vnfcInfo'][0]['vnfcResourceInfoId'] = 'ng'
        mock_inst.return_value = objects.VnfInstanceV2.from_dict(ins)
        job = copy.deepcopy(_pm_job)
        job['subObjectInstanceIds'] = ['vnfc_info1']
        job = objects.PmJobV2.from_dict(job)
        self.assertRaises(
            sol_ex.PrometheusPluginError,
            pp.create_job, context=self.context, pm_job=job
        )

        # vnfcInfo mismatch
        ins = copy.deepcopy(_inst1)
        del ins['instantiatedVnfInfo']['vnfcInfo'][0]['vnfcResourceInfoId']
        mock_inst.return_value = objects.VnfInstanceV2.from_dict(ins)
        job = copy.deepcopy(_pm_job)
        job['subObjectInstanceIds'] = ['vnfc_info1']
        job = objects.PmJobV2.from_dict(job)
        self.assertRaises(
            sol_ex.PrometheusPluginError,
            pp.create_job, context=self.context, pm_job=job
        )

        # resourcename mismatch: VirtualisedComputeResource
        ins = copy.deepcopy(_inst1)
        _ = ins['instantiatedVnfInfo']['vnfcResourceInfo']
        del _[0]['computeResource']['resourceId']
        mock_inst.return_value = objects.VnfInstanceV2.from_dict(ins)
        job = copy.deepcopy(_pm_job)
        job['subObjectInstanceIds'] = ['vnfc_info1']
        job = objects.PmJobV2.from_dict(job)
        self.assertRaises(
            sol_ex.PrometheusPluginError,
            pp.create_job, context=self.context, pm_job=job
        )
        # resourcename mismatch: VirtualisedComputeResource
        ins = copy.deepcopy(_inst1)
        _ = ins['instantiatedVnfInfo']['vnfcResourceInfo'][0]
        _['computeResource']['resourceId'] = 'test-xxx1-756757f8f-xcwmt'
        mock_inst.return_value = objects.VnfInstanceV2.from_dict(ins)
        job = copy.deepcopy(_pm_job)
        job['subObjectInstanceIds'] = ['vnfc_info1']
        job = objects.PmJobV2.from_dict(job)
        self.assertRaises(
            sol_ex.PrometheusPluginError,
            pp.create_job, context=self.context, pm_job=job
        )

        ins = copy.deepcopy(_inst1)
        _ = ins['instantiatedVnfInfo']['vnfcResourceInfo'][0]
        _['computeResource']['vimLevelResourceType'] = 'ng'
        mock_inst.return_value = objects.VnfInstanceV2.from_dict(ins)
        job = copy.deepcopy(_pm_job2)
        job['subObjectInstanceIds'] = ['test_if0']
        job = objects.PmJobV2.from_dict(job)
        self.assertRaises(
            sol_ex.PrometheusPluginError,
            pp.create_job, context=self.context, pm_job=job
        )


class TestPrometheusPluginFm(base.TestCase):
    def setUp(self):
        super(TestPrometheusPluginFm, self).setUp()
        objects.register_all()
        self.context = context.get_admin_context()
        self.request = mock.Mock()
        self.request.context = self.context
        prometheus_plugin.PrometheusPluginFm._instance = None

    def tearDown(self):
        super(TestPrometheusPluginFm, self).tearDown()
        # delete singleton object
        prometheus_plugin.PrometheusPluginFm._instance = None

    def test_constructor_error(self):
        self.config_fixture.config(
            group='prometheus_plugin', auto_scaling=False)
        mon_base.MonitoringPlugin.get_instance(
            prometheus_plugin.PrometheusPluginFm)
        self.assertRaises(
            SystemError,
            prometheus_plugin.PrometheusPluginFm)

    def test_constructor_stub(self):
        self.config_fixture.config(
            group='prometheus_plugin', auto_scaling=False)
        pp = mon_base.MonitoringPlugin.get_instance(
            prometheus_plugin.PrometheusPluginFm)
        self.assertIsInstance(pp._instance, mon_base.MonitoringPluginStub)
        pp = mon_base.MonitoringPlugin.get_instance(
            prometheus_plugin.PrometheusPluginFm)
        self.assertIsInstance(pp._instance, mon_base.MonitoringPluginStub)

    def test_pm_no_body(self):
        self.config_fixture.config(
            group='prometheus_plugin', performance_management=True)
        pp = mon_base.MonitoringPlugin.get_instance(
            prometheus_plugin.PrometheusPluginPm)
        self.assertRaises(
            sol_ex.PrometheusPluginValidationError,
            pp._alert, self.request)


class TestPrometheusPluginAutoScaling(base.TestCase):
    def setUp(self):
        super(TestPrometheusPluginAutoScaling, self).setUp()
        objects.register_all()
        self.context = context.get_admin_context()
        self.request = mock.Mock()
        self.request.context = self.context
        prometheus_plugin.PrometheusPluginAutoScaling._instance = None

    def tearDown(self):
        super(TestPrometheusPluginAutoScaling, self).tearDown()
        # delete singleton object
        prometheus_plugin.PrometheusPluginAutoScaling._instance = None

    def test_constructor_error(self):
        self.config_fixture.config(
            group='prometheus_plugin', auto_scaling=False)
        mon_base.MonitoringPlugin.get_instance(
            prometheus_plugin.PrometheusPluginAutoScaling)
        self.assertRaises(
            SystemError,
            prometheus_plugin.PrometheusPluginAutoScaling)

    def test_constructor_stub(self):
        self.config_fixture.config(
            group='prometheus_plugin', auto_scaling=False)
        pp = mon_base.MonitoringPlugin.get_instance(
            prometheus_plugin.PrometheusPluginAutoScaling)
        self.assertIsInstance(pp._instance, mon_base.MonitoringPluginStub)
        pp = mon_base.MonitoringPlugin.get_instance(
            prometheus_plugin.PrometheusPluginAutoScaling)
        self.assertIsInstance(pp._instance, mon_base.MonitoringPluginStub)

    def test_monitoring_plugin(self):
        mon = mon_base.MonitoringPlugin.get_instance(
            mon_base.MonitoringPluginStub)
        mon.set_callback(None)
        mon.create_job()
        mon.delete_job()
        mon.alert()

    def test_monitoring_plugin_stub(self):
        mon_base.MonitoringPlugin.get_instance(
            mon_base.MonitoringPluginStub)
        mon = mon_base.MonitoringPlugin.get_instance(
            mon_base.MonitoringPluginStub)
        mon.set_callback(None)
        mon.create_job()
        mon.delete_job()
        mon.alert()
        self.assertRaises(
            SystemError,
            mon_base.MonitoringPluginStub)
