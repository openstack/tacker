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

OBJ_TYPE_TO_METRIC_LISt = {
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


def _check_http_client_auth(auth_req):
    auth = objects.SubscriptionAuthentication(
        authType=auth_req['authType']
    )

    if 'BASIC' in auth.authType:
        basic_req = auth_req.get('paramsBasic')
        if basic_req is None:
            msg = "ParamsBasic must be specified."
            raise sol_ex.InvalidSubscription(sol_detail=msg)
        auth.paramsBasic = (
            objects.SubscriptionAuthentication_ParamsBasic(
                userName=basic_req.get('userName'),
                password=basic_req.get('password')
            )
        )

    if 'OAUTH2_CLIENT_CREDENTIALS' in auth.authType:
        oauth2_req = auth_req.get('paramsOauth2ClientCredentials')
        if oauth2_req is None:
            msg = "paramsOauth2ClientCredentials must be specified."
            raise sol_ex.InvalidSubscription(sol_detail=msg)
        auth.paramsOauth2ClientCredentials = (
            objects.SubscriptionAuthentication_ParamsOauth2(
                clientId=oauth2_req.get('clientId'),
                clientPassword=oauth2_req.get('clientPassword'),
                tokenEndpoint=oauth2_req.get('tokenEndpoint')
            )
        )

    if 'TLS_CERT' in auth.authType:
        msg = "'TLS_CERT' is not supported at the moment."
        raise sol_ex.InvalidSubscription(sol_detail=msg)
    return auth


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
        if not metric_types.issubset(OBJ_TYPE_TO_METRIC_LISt[obj_type]):
            raise sol_ex.PMJobInvalidRequest


class VnfPmControllerV2(sol_wsgi.SolAPIController):

    def __init__(self):
        self.nfvo_client = nfvo_client.NfvoClient()
        self.endpoint = CONF.v2_vnfm.endpoint
        self._pm_job_view = vnfpm_view.PmJobViewBuilder(self.endpoint)
        cls = plugin.get_class('pm_event')
        self.plugin = plugin.MonitoringPlugin.get_instance(cls)

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
            pm_job.authentication = _check_http_client_auth(auth_req)

        # metadata
        metadata = body.get('metadata')
        if metadata:
            pm_job.metadata = metadata

        if CONF.v2_nfvo.test_callback_uri:
            pm_job_utils.test_notification(pm_job)

        try:
            self.plugin.create_job(context=context, pm_job=pm_job)
        except sol_ex.PrometheusPluginError as e:
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
            pm_job.authentication = _check_http_client_auth(
                body.get("authentication"))

        if CONF.v2_nfvo.test_callback_uri:
            pm_job_utils.test_notification(pm_job)

        with context.session.begin(subtransactions=True):
            pm_job.update(context)

        pm_job_modifications = objects.PmJobModificationsV2(
            callbackUri=pm_job.callbackUri,
        )
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
        if action == 'update':
            # Content-Type of Modify request shall be
            # 'application/mergepatch+json' according to SOL spec.
            # But 'application/json' and 'text/plain' is OK for backward
            # compatibility.
            return ['application/mergepatch+json', 'application/json',
                    'text/plain']
        return ['application/json', 'text/plain']

    def supported_api_versions(self, action):
        return api_version.v2_pm_versions
