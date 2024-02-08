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

from oslo_log import log as logging
from oslo_utils import uuidutils

from tacker.sol_refactored.api import api_version
from tacker.sol_refactored.api.schemas import vnfpm_v2 as schema
from tacker.sol_refactored.api import validator
from tacker.sol_refactored.api import wsgi as sol_wsgi
from tacker.sol_refactored.common import config
from tacker.sol_refactored.common import coordinate
from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.common import monitoring_plugin_base as plugin
from tacker.sol_refactored.common import pm_job_utils
from tacker.sol_refactored.common import pm_threshold_utils
from tacker.sol_refactored.common import subscription_utils as subsc_utils
from tacker.sol_refactored.common import vnf_instance_utils as inst_utils
from tacker.sol_refactored.controller import vnfpm_view
from tacker.sol_refactored.nfvo import nfvo_client
from tacker.sol_refactored import objects

LOG = logging.getLogger(__name__)  # NOTE: unused at the moment

CONF = config.CONF

OBJ_TYPE_TO_GROUP_TYPE = {
    'Vnf': 'VirtualisedComputeResource',
    'Vnfc': 'VirtualisedComputeResource',
    'VnfIntCp': 'VnfInternalCp',
    'VnfExtCp': 'VnfExternalCp'
}

OBJ_TYPE_TO_METRIC_LIST = {
    'Vnf': {'VCpuUsageMeanVnf', 'VCpuUsagePeakVnf',
            'VMemoryUsageMeanVnf', 'VMemoryUsagePeakVnf',
            'VDiskUsageMeanVnf', 'VDiskUsagePeakVnf'},
    'Vnfc': {'VCpuUsageMeanVnf', 'VCpuUsagePeakVnf',
             'VMemoryUsageMeanVnf', 'VMemoryUsagePeakVnf',
             'VDiskUsageMeanVnf', 'VDiskUsagePeakVnf'},
    'VnfIntCp': {'ByteIncomingVnfIntCp', 'ByteOutgoingVnfIntCp',
                 'PacketIncomingVnfIntCp', 'PacketOutgoingVnfIntCp'},
    'VnfExtCp': {'ByteIncomingVnfExtCp', 'ByteOutgoingVnfExtCp',
                 'PacketIncomingVnfExtCp', 'PacketOutgoingVnfExtCp'}
}


def _check_performance_metric_or_group(
        obj_type, metric_group, performance_metric):
    # Check whether the object_type is consistent with the corresponding
    # group name
    if metric_group and (
            len(metric_group) != 1 or
            metric_group[0] != OBJ_TYPE_TO_GROUP_TYPE[obj_type]):
        raise sol_ex.PMJobInvalidRequest

    # Check if the type in performance metric matches the standard type.
    if performance_metric:
        metric_types = {metric.split('.')[0] for metric in performance_metric}
        if not metric_types.issubset(OBJ_TYPE_TO_METRIC_LIST[obj_type]):
            raise sol_ex.PMJobInvalidRequest


def _check_metric_and_obj_type(performance_metric, obj_type):
    metric_type = {performance_metric}
    if obj_type == 'Vnf' or obj_type == 'Vnfc':
        if metric_type.issubset(OBJ_TYPE_TO_METRIC_LIST[obj_type]):
            raise sol_ex.PMThresholdInvalidRequest
    if obj_type == 'VnfIntCp' or obj_type == 'VnfExtCp':
        if len(performance_metric.split('.')) == 2:
            raise sol_ex.PMThresholdInvalidRequest
    metric_type = {performance_metric.split('.')[0]}
    if not metric_type.issubset(OBJ_TYPE_TO_METRIC_LIST[obj_type]):
        raise sol_ex.PMThresholdInvalidRequest


class VnfPmControllerV2(sol_wsgi.SolAPIController):

    def __init__(self):
        self.nfvo_client = nfvo_client.NfvoClient()
        self.endpoint = CONF.v2_vnfm.endpoint
        self._pm_job_view = vnfpm_view.PmJobViewBuilder(self.endpoint)
        self._pm_threshold_view = (
            vnfpm_view.PmThresholdViewBuilder(self.endpoint))
        cls = plugin.get_class(
            CONF.prometheus_plugin.performance_management_package,
            CONF.prometheus_plugin.performance_management_class)
        self.plugin = plugin.MonitoringPlugin.get_instance(cls)
        threshold_cls = plugin.get_class(
            CONF.prometheus_plugin.performance_management_threshold_package,
            CONF.prometheus_plugin.performance_management_threshold_class)
        self.threshold_plugin = (
            plugin.MonitoringPlugin.get_instance(threshold_cls))

    @validator.schema(schema.CreatePmJobRequest_V210, '2.1.0')
    def create(self, request, body):
        context = request.context

        # check request body
        # If this `subObjectInstanceIds` is present, the cardinality of the
        # `objectInstanceIds` attribute shall be 1.
        if (body.get("subObjectInstanceIds") and
                len(body.get("objectInstanceIds")) > 1):
            raise sol_ex.PMJobInvalidRequest

        # At least one of the two attributes (performance
        # metric or group) shall be present.
        metric_group = body["criteria"].get('performanceMetricGroup')
        performance_metric = body["criteria"].get('performanceMetric')
        if not metric_group and not performance_metric:
            raise sol_ex.PMJobInvalidRequest

        # check the value of group or performance_metric
        _check_performance_metric_or_group(
            body['objectType'], metric_group, performance_metric)

        # check vnf instance status
        inst_ids = body["objectInstanceIds"]
        for inst_id in inst_ids:
            inst = inst_utils.get_inst(context, inst_id)
            if inst.instantiationState == 'NOT_INSTANTIATED':
                raise sol_ex.VnfInstanceIsNotInstantiated(inst_id=inst_id)

        # pm_job.criteria
        pm_job_criteria = objects.VnfPmJobCriteriaV2(
            collectionPeriod=body["criteria"]['collectionPeriod'],
            reportingPeriod=body["criteria"]['reportingPeriod']
        )
        criteria = body["criteria"]
        if performance_metric:
            pm_job_criteria.performanceMetric = criteria['performanceMetric']
        if metric_group:
            pm_job_criteria.performanceMetricGroup = criteria[
                'performanceMetricGroup']
        if criteria.get('reportingBoundary'):
            try:
                dt = copy.deepcopy(criteria['reportingBoundary'])
                datetime.datetime.fromisoformat(dt.replace('Z', '+00:00'))
            except ValueError as ex:
                raise sol_ex.SolValidationError(
                    detail="invalid date format.") from ex
            pm_job_criteria.reportingBoundary = criteria['reportingBoundary']

        # pm_job
        pm_job_id = uuidutils.generate_uuid()
        pm_job = objects.PmJobV2(
            id=pm_job_id,
            objectType=body["objectType"],
            objectInstanceIds=body["objectInstanceIds"],
            criteria=pm_job_criteria,
            callbackUri=body["callbackUri"],
            reports=[],
        )
        if body.get("subObjectInstanceIds"):
            pm_job.subObjectInstanceIds = body["subObjectInstanceIds"]

        # authentication
        auth_req = body.get('authentication')
        if auth_req:
            pm_job.authentication = subsc_utils.get_subsc_auth(
                auth_req)

        # metadata
        metadata = body.get('metadata')
        if metadata:
            pm_job.metadata = metadata

        if CONF.v2_nfvo.test_callback_uri:
            subsc_utils.test_notification(
                pm_job, subsc_utils.NOTIFY_TYPE_PM)

        try:
            self.plugin.create_job(context=context, pm_job=pm_job)
        except sol_ex.PrometheusPluginError as e:
            LOG.error("Failed to create PM job: %s", e.args[0])
            raise sol_ex.PrometheusSettingFailed from e

        pm_job.create(context)

        location = pm_job_utils.pm_job_href(pm_job.id, self.endpoint)
        resp_body = self._pm_job_view.detail(pm_job)

        return sol_wsgi.SolResponse(201, resp_body,
                                    version=api_version.CURRENT_PM_VERSION,
                                    location=location)

    def index(self, request):
        filter_param = request.GET.get('filter')
        if filter_param is not None:
            filters = self._pm_job_view.parse_filter(filter_param)
        else:
            filters = None

        # validate_filter
        selector = self._pm_job_view.parse_selector(request.GET)
        page_size = CONF.v2_vnfm.vnfpm_pmjob_page_size
        pager = self._pm_job_view.parse_pager(request, page_size)
        pm_job = pm_job_utils.get_pm_job_all(request.context,
                                             marker=pager.marker)
        resp_body = self._pm_job_view.detail_list(pm_job, filters,
                                                  selector, pager)

        return sol_wsgi.SolResponse(200, resp_body,
                                    version=api_version.CURRENT_PM_VERSION,
                                    link=pager.get_link())

    def show(self, request, id):
        pm_job = pm_job_utils.get_pm_job(request.context, id)
        pm_job_resp = self._pm_job_view.detail(pm_job)
        return sol_wsgi.SolResponse(200, pm_job_resp,
                                    version=api_version.CURRENT_PM_VERSION)

    @validator.schema(schema.PmJobModificationsRequest_V210, '2.1.0')
    @coordinate.lock_resources('{id}')
    def update(self, request, id, body):
        context = request.context

        pm_job = pm_job_utils.get_pm_job(context, id)
        if body.get("callbackUri"):
            pm_job.callbackUri = body.get("callbackUri")
        if body.get("authentication"):
            pm_job.authentication = subsc_utils.get_subsc_auth(
                body.get("authentication"))

        if CONF.v2_nfvo.test_callback_uri:
            subsc_utils.test_notification(
                pm_job, subsc_utils.NOTIFY_TYPE_PM)

        with context.session.begin(subtransactions=True):
            pm_job.update(context)

        pm_job_modifications = objects.PmJobModificationsV2()
        if body.get("callbackUri"):
            setattr(pm_job_modifications, "callbackUri", body["callbackUri"])
        resp = pm_job_modifications.to_dict()

        return sol_wsgi.SolResponse(200, resp,
                                    version=api_version.CURRENT_PM_VERSION)

    @coordinate.lock_resources('{id}')
    def delete(self, request, id):
        context = request.context
        pm_job = pm_job_utils.get_pm_job(context, id)

        self.plugin.delete_job(context=context, pm_job=pm_job)

        reports = objects.PerformanceReportV2.get_by_filter(context,
                                                            jobId=pm_job.id)
        for report in reports:
            report.delete(context)
        pm_job.delete(context)

        return sol_wsgi.SolResponse(204, None,
                                    version=api_version.CURRENT_PM_VERSION)

    def report_get(self, request, id, report_id):
        pm_report = pm_job_utils.get_pm_report(
            request.context, id, report_id)
        pm_report_resp = self._pm_job_view.report_detail(pm_report)
        return sol_wsgi.SolResponse(200, pm_report_resp,
                                    version=api_version.CURRENT_PM_VERSION)

    def allowed_content_types(self, action):
        if action in {'update', 'update_threshold'}:
            # Content-Type of Modify request shall be
            # 'application/merge-patch+json' according to SOL spec.
            # But 'application/json' and 'text/plain' is OK for backward
            # compatibility.
            return ['application/merge-patch+json', 'application/json',
                    'text/plain']
        return ['application/json', 'text/plain']

    def allowed_accept(self, action):
        return ['application/json', 'application/merge-patch+json',
                'text/plain']

    def supported_api_versions(self, action):
        return api_version.v2_pm_versions

    @validator.schema(schema.CreateThresholdRequest_V210, '2.1.0')
    def create_threshold(self, request, body):
        context = request.context

        object_type = body['objectType']
        performance_metric = body["criteria"]['performanceMetric']

        # Check if the type in performance metric matches the standard type.
        _check_metric_and_obj_type(performance_metric, object_type)

        # According to nfv-sol003 6.5.3.4,
        # currently criteria.thresholdType supports only "SIMPLE".
        if body["criteria"]["thresholdType"] != "SIMPLE":
            raise sol_ex.PMThresholdInvalidRequest
        # check criteria.thresholdType and criteria.ThresholdDetails
        if not body["criteria"].get("simpleThresholdDetails"):
            raise sol_ex.PMThresholdInvalidRequest

        threshold_value = (
            body["criteria"]["simpleThresholdDetails"]["thresholdValue"])
        threshold_hysteresis = (
            body["criteria"]["simpleThresholdDetails"]["hysteresis"])

        # check vnf instance status
        inst_id = body.get("objectInstanceId")
        inst = inst_utils.get_inst(context, inst_id)
        if inst.instantiationState == 'NOT_INSTANTIATED':
            raise sol_ex.VnfInstanceIsNotInstantiated(inst_id=inst_id)

        threshold_criteria = objects.ThresholdCriteriaV2(
            performanceMetric=performance_metric,
            thresholdType=body["criteria"]['thresholdType']
        )
        threshold_details = objects.SimpleThresholdDetails(
            thresholdValue=threshold_value,
            hysteresis=threshold_hysteresis)
        threshold_criteria.simpleThresholdDetails = threshold_details

        threshold_id = uuidutils.generate_uuid()
        threshold = objects.ThresholdV2(
            id=threshold_id,
            objectType=object_type,
            objectInstanceId=inst_id,
            criteria=threshold_criteria,
            callbackUri=body["callbackUri"],
        )
        if body.get("subObjectInstanceIds"):
            threshold.subObjectInstanceIds = body["subObjectInstanceIds"]
        metadata = body.get('metadata')
        if not metadata:
            raise sol_ex.PMThresholdInvalidRequest
        threshold.metadata = metadata

        auth_req = body.get('authentication')
        if auth_req:
            threshold.authentication = subsc_utils.get_subsc_auth(
                auth_req)

        if CONF.v2_nfvo.test_callback_uri:
            subsc_utils.test_notification(
                threshold, subsc_utils.NOTIFY_TYPE_PM)

        try:
            self.threshold_plugin.create_threshold(
                context=context,
                pm_threshold=threshold)
        except sol_ex.PrometheusPluginError as e:
            LOG.error("Failed to create PM Threshold: %s", e.args[0])
            raise sol_ex.PrometheusSettingFailed from e

        threshold.create(context)

        location = pm_threshold_utils.pm_threshold_href(threshold.id,
                                                        self.endpoint)
        resp_body = self._pm_threshold_view.detail(threshold)
        return sol_wsgi.SolResponse(201, resp_body,
                                    version=api_version.CURRENT_PM_VERSION,
                                    location=location)

    def index_threshold(self, request):
        filter_param = request.GET.get('filter')
        filters = (self._pm_threshold_view.parse_filter(filter_param)
                   if filter_param else None)

        page_size = CONF.v2_vnfm.vnfpm_pmthreshold_page_size
        pager = self._pm_threshold_view.parse_pager(request, page_size)
        pm_job = pm_threshold_utils.get_pm_threshold_all(request.context,
                                                         marker=pager.marker)
        resp_body = self._pm_threshold_view.detail_list(pm_job, filters,
                                                        None, pager)

        return sol_wsgi.SolResponse(200, resp_body,
                                    version=api_version.CURRENT_PM_VERSION,
                                    link=pager.get_link())

    def show_threshold(self, request, thresholdId):
        pm_threshold = pm_threshold_utils.get_pm_threshold(
            request.context, thresholdId)
        if not pm_threshold:
            raise sol_ex.PMThresholdNotExist(threshold_id=thresholdId)
        pm_threshold_resp = self._pm_threshold_view.detail(pm_threshold)
        return sol_wsgi.SolResponse(200, pm_threshold_resp,
                                    version=api_version.CURRENT_PM_VERSION)

    @validator.schema(schema.ThresholdModifications_V210, '2.1.0')
    @coordinate.lock_resources('{thresholdId}')
    def update_threshold(self, request, thresholdId, body):
        context = request.context

        pm_threshold = pm_threshold_utils.get_pm_threshold(
            context, thresholdId)
        if not pm_threshold:
            raise sol_ex.PMThresholdNotExist(threshold_id=thresholdId)

        if body.get("callbackUri"):
            pm_threshold.callbackUri = body.get("callbackUri")
        if CONF.v2_nfvo.test_callback_uri:
            subsc_utils.test_notification(
                pm_threshold, subsc_utils.NOTIFY_TYPE_PM)
        if body.get("authentication"):
            pm_threshold.authentication = subsc_utils.get_subsc_auth(
                body.get("authentication"))

        with context.session.begin(subtransactions=True):
            pm_threshold.update(context)

        pm_threshold_modifications = objects.ThresholdModificationsV2()
        if body.get("callbackUri"):
            setattr(
                pm_threshold_modifications, "callbackUri", body["callbackUri"])
        resp = pm_threshold_modifications.to_dict()
        return sol_wsgi.SolResponse(200, resp,
                                    version=api_version.CURRENT_PM_VERSION)

    @coordinate.lock_resources('{thresholdId}')
    def delete_threshold(self, request, thresholdId):
        context = request.context
        pm_threshold = pm_threshold_utils.get_pm_threshold(
            context, thresholdId)
        if not pm_threshold:
            raise sol_ex.PMThresholdNotExist(threshold_id=thresholdId)

        self.threshold_plugin.delete_threshold(
            context=context, pm_threshold=pm_threshold)

        pm_threshold.delete(context)

        return sol_wsgi.SolResponse(204, None,
                                    version=api_version.CURRENT_PM_VERSION)

    def set_default_to_response(self, result, action):
        result.headers.setdefault('version', api_version.CURRENT_PM_VERSION)
        result.headers.setdefault('accept-ranges', 'none')
