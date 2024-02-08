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

import datetime
import itertools
import json
import os
import paramiko
import re
import tempfile
import yaml

from keystoneauth1 import exceptions as ks_exc
from oslo_log import log as logging
from oslo_utils import uuidutils
from tacker.common import utils
from tacker.sol_refactored.api.schemas import prometheus_plugin_schemas
from tacker.sol_refactored.api import validator
from tacker.sol_refactored.common import config as cfg
from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.common import fm_alarm_utils
from tacker.sol_refactored.common import http_client
from tacker.sol_refactored.common import monitoring_plugin_base as mon_base
from tacker.sol_refactored.common import pm_job_utils
from tacker.sol_refactored.common import pm_threshold_utils
from tacker.sol_refactored.common import vnf_instance_utils as inst_utils
from tacker.sol_refactored.conductor import conductor_rpc_v2 as rpc
from tacker.sol_refactored import objects


LOG = logging.getLogger(__name__)
logging.getLogger("paramiko").setLevel(logging.WARNING)

CONF = cfg.CONF


class PrometheusPlugin():
    def __init__(self):
        self.rpc = rpc.PrometheusPluginConductor()

    def parse_datetime(self, isodate):
        t = (isodate if isinstance(isodate, datetime.datetime)
             else datetime.datetime.fromisoformat(
             isodate.replace('Z', '+00:00')))
        return t if t.tzinfo else t.astimezone()


class PrometheusPluginPmBase(PrometheusPlugin):
    def __init__(self):
        super(PrometheusPluginPmBase, self).__init__()
        auth_handle = http_client.NoAuthHandle()
        self.client = http_client.HttpClient(auth_handle)

    def set_callback(self, notification_callback):
        self.notification_callback = notification_callback

    def alert(self, **kwargs):
        try:
            self._alert(kwargs['request'], body=kwargs['body'])
        except Exception as e:
            # All exceptions are ignored here and 204 response will always
            # be returned because when Tacker responds errors to alertmanager,
            # alertmanager may repeat the same reports.
            LOG.error("%s: %s", e.__class__.__name__, e.args[0])

    def decompose_metrics(self, pm_job_or_threshold):
        if pm_job_or_threshold.objectType in {'Vnf', 'Vnfc'}:
            return self.decompose_metrics_vnfc(pm_job_or_threshold)
        if pm_job_or_threshold.objectType in {'VnfIntCp', 'VnfExtCp'}:
            return self.decompose_metrics_vnfintextcp(pm_job_or_threshold)
        raise sol_ex.PrometheusPluginError(
            f"Invalid objectType: {pm_job_or_threshold.objectType}.")

    def _make_rules(self, pm_job_or_threshold, metric, inst_map):
        sub_objs = []
        if (pm_job_or_threshold.obj_attr_is_set('subObjectInstanceIds')
                and pm_job_or_threshold.subObjectInstanceIds):
            sub_objs = pm_job_or_threshold.subObjectInstanceIds

        # Cardinality of objectInstanceIds and subObjectInstanceIds
        # is N:0 or 1:N.
        if len(sub_objs) > 0:
            return self._make_rules_for_each_sub_obj(
                pm_job_or_threshold, inst_map, metric)
        return self._make_rules_for_each_obj(
            pm_job_or_threshold, inst_map, metric)

    def make_rules(self, context, pm_job_or_threshold):
        target_list, reload_list = self.get_access_info(pm_job_or_threshold)
        metrics = self.decompose_metrics(pm_job_or_threshold)
        inst_map = self.get_vnf_instances(context, pm_job_or_threshold)
        rules = sum(
            [self._make_rules(pm_job_or_threshold, metric, inst_map)
             for metric in metrics], [])
        if len(rules) == 0:
            raise sol_ex.PrometheusPluginError(
                "Converting from a PM job/threshold to alert rules is failed."
                f" PM job/threshold id: {pm_job_or_threshold.id}")
        rule_group = {
            'groups': [
                {
                    'name': f'tacker_{pm_job_or_threshold.id}',
                    'rules': rules
                }
            ]
        }
        self.upload_rules(
            context, target_list, reload_list,
            rule_group, pm_job_or_threshold.id)
        return rule_group

    def convert_measurement_unit(self, metric, value):
        if re.match(r'^V(Cpu|Memory|Disk)Usage(Mean|Peak)Vnf\..+', metric):
            value = float(value)
        elif re.match(r'^(Byte|Packet)(Incoming|Outgoing)Vnf(IntCp|ExtCp)',
                      metric):
            value = int(value)
        else:
            raise sol_ex.PrometheusPluginSkipped(
                  "Failed to convert annotations.value to measurement unit.")
        return value

    def load_prom_config(self):
        config_file = utils.find_config_file({}, 'prometheus-plugin.yaml')
        if not config_file:
            raise sol_ex.PrometheusPluginError(
                "prometheus-plugin.yaml not found."
            )
        LOG.info(f"prom_config file: {config_file}")
        with open(config_file) as file:
            prom_config = yaml.safe_load(file.read())
        return prom_config

    def make_prom_ql(self, target, pod, collection_period=30,
                     reporting_period=90, sub_object_instance_id='*',
                     pm_type='PMJob', namespace='default'):
        REPORTING_PERIOD_MIN = 30
        reporting_period = max(reporting_period, REPORTING_PERIOD_MIN)
        prom_config = self.load_prom_config()
        expr = prom_config[pm_type]['PromQL'][target].format(
            pod=pod,
            collection_period=collection_period,
            reporting_period=reporting_period,
            sub_object_instance_id=sub_object_instance_id,
            namespace=namespace
        )
        LOG.info(f"promQL expr: {expr}")
        return expr

    def make_rule(self, type, id, object_instance_id, sub_object_instance_id,
                  metric, expression, collection_period=30):
        if type == 'PMJob':
            labels = {
                'alertname': '',
                'receiver_type': 'tacker',
                'function_type': 'vnfpm',
                'job_id': id,
                'object_instance_id': object_instance_id,
                'sub_object_instance_id': sub_object_instance_id,
                'metric': metric
            }
        elif type == 'Threshold':
            labels = {
                'alertname': '',
                'receiver_type': 'tacker',
                'function_type': 'vnfpm_threshold',
                'threshold_id': id,
                'object_instance_id': object_instance_id,
                'sub_object_instance_id': sub_object_instance_id,
                'metric': metric
            }
        else:
            raise sol_ex.PrometheusPluginError(
                "Invalid type in make_rule()."
            )

        labels = {k: v for k, v in labels.items() if v is not None}
        annotations = {
            'value': r'{{$value}}'
        }
        rule = {
            'alert': uuidutils.generate_uuid(),
            'expr': expression,
            'for': f'{collection_period}s',
            'labels': labels,
            'annotations': annotations
        }
        return rule

    def get_namespace(self, inst):
        return inst.instantiatedVnfInfo.metadata.get(
            'namespace', 'default') if (
            inst.obj_attr_is_set('instantiatedVnfInfo') and
            inst.instantiatedVnfInfo.obj_attr_is_set(
                'metadata')) else 'default'

    def get_vnfc_resource_info(self, inst):
        return inst.instantiatedVnfInfo.vnfcResourceInfo if (
            inst.obj_attr_is_set('instantiatedVnfInfo') and
            inst.instantiatedVnfInfo.obj_attr_is_set(
                'vnfcResourceInfo')) else None

    def get_pod_regexp(self, inst):
        # resource ids are like:
        #   ['test-test1-756757f8f-xcwmt',
        #    'test-test2-756757f8f-kmghr', ...]
        # convert them to a regex string such as:
        #   '(test-test1-[0-9a-f]{1,10}-[0-9a-z]{5}$|
        #    test-test2-[0-9a-f]{1,10}-[0-9a-z]{5}$|...)'
        resource_info = self.get_vnfc_resource_info(inst)
        if not resource_info:
            return None
        deployments = list(filter(
            lambda r:
                r.computeResource.obj_attr_is_set(
                    'vimLevelResourceType')
                and r.computeResource.obj_attr_is_set(
                    'resourceId'
                )
                and r.computeResource.vimLevelResourceType ==
                'Deployment', resource_info
        ))
        deployments = list(set(list(map(
            lambda d: re.sub(
                r'\-[0-9a-f]{1,10}\-[0-9a-z]{5}$', '',
                d.computeResource.resourceId) +
            r'-[0-9a-f]{1,10}-[0-9a-z]{5}$',
            deployments
        ))))
        return ('(' + '|'.join(deployments) + ')'
            if len(deployments) else None)

    def get_compute_resource_by_sub_obj(self, inst, sub_obj):
        if (not inst.obj_attr_is_set('instantiatedVnfInfo') or
                not inst.instantiatedVnfInfo.obj_attr_is_set(
                    'vnfcResourceInfo') or
                not inst.instantiatedVnfInfo.obj_attr_is_set('vnfcInfo')):
            return None
        vnfc_info = list(filter(
            lambda x: (x.obj_attr_is_set('vnfcResourceInfoId') and
                x.id == sub_obj),
            inst.instantiatedVnfInfo.vnfcInfo))
        if len(vnfc_info) == 0:
            return None
        resources = list(filter(
            lambda x: (vnfc_info[0].obj_attr_is_set('vnfcResourceInfoId') and
                x.id == vnfc_info[0].vnfcResourceInfoId and
                x.computeResource.obj_attr_is_set('vimLevelResourceType') and
                x.computeResource.vimLevelResourceType == 'Deployment' and
                x.computeResource.obj_attr_is_set('resourceId')),
            inst.instantiatedVnfInfo.vnfcResourceInfo))
        if len(resources) == 0:
            return None
        return resources[0].computeResource

    def _delete_rule(self, host, port, user, password, path, id):
        with paramiko.Transport(sock=(host, port)) as client:
            client.connect(username=user, password=password)
            sftp = paramiko.SFTPClient.from_transport(client)
            sftp.remove(f'{path}/{id}.json')

    def reload_prom_server(self, context, reload_uri):
        resp, _ = self.client.do_request(
            reload_uri, "PUT", context=context)
        if resp.status_code >= 400 and resp.status_code < 600:
            raise sol_ex.PrometheusPluginError(
                f"Reloading request to prometheus is failed: "
                f"{resp.status_code}.")

    def _upload_rule(self, rule_group, host, port, user, password, path, id):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, 'rule.json'),
                      'w+', encoding="utf-8") as fp:
                json.dump(rule_group, fp, indent=4, ensure_ascii=False)
                filename = fp.name
            with paramiko.Transport(sock=(host, port)) as client:
                LOG.info("Upload rule files to prometheus server: %s.", host)
                client.connect(username=user, password=password)
                sftp = paramiko.SFTPClient.from_transport(client)
                sftp.put(filename, f'{path}/{id}.json')
        self.verify_rule(host, port, user, password, path, id)

    def verify_rule(self, host, port, user, password, path, id):
        if not CONF.prometheus_plugin.test_rule_with_promtool:
            return
        with paramiko.SSHClient() as client:
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(host, port=port, username=user, password=password)
            command = f"promtool check rules {path}/{id}.json"
            LOG.info("Rule file validation command: %s", command)
            _, stdout, stderr = client.exec_command(command)
            if stdout.channel.recv_exit_status() != 0:
                error_byte = stderr.read()
                error_str = error_byte.decode('utf-8')
                LOG.error(
                    "Rule file validation with promtool failed: %s",
                    error_str)
                raise sol_ex.PrometheusPluginError(
                    "Rule file validation with promtool failed.")

    def delete_rules(self, context, pm_job_or_threshold):
        target_list, reload_list = self.get_access_info(pm_job_or_threshold)
        for target in target_list:
            try:
                self._delete_rule(
                    target['host'], target['port'], target['user'],
                    target['password'], target['path'], pm_job_or_threshold.id)
            except (sol_ex.PrometheusPluginError, ks_exc.ClientException,
                    paramiko.SSHException):
                # NOTE(shimizu-koji): This exception is ignored.
                # DELETE /pm_jobs/{id} will be success even if _delete_rule()
                # is failed. Because the rule file was already deleted.
                pass
        for uri in reload_list:
            try:
                self.reload_prom_server(context, uri)
            except (sol_ex.PrometheusPluginError, ks_exc.ClientException,
                    paramiko.SSHException):
                pass

    def get_access_info(self, pm_job_or_threshold):
        target_list = []
        reload_list = []
        if (not pm_job_or_threshold.obj_attr_is_set('metadata')
                or 'monitoring' not in pm_job_or_threshold.metadata):
            raise sol_ex.PrometheusPluginError(
                  "monitoring info is missing at metadata field.")
        access_info = pm_job_or_threshold.metadata['monitoring']
        if (access_info.get('monitorName') != 'prometheus' or
                access_info.get('driverType') != 'external'):
            raise sol_ex.PrometheusPluginError(
                  "prometheus info is missing at metadata field.")
        for info in access_info.get('targetsInfo', []):
            host = info.get('prometheusHost', '')
            port = info.get('prometheusHostPort', 22)
            auth = info.get('authInfo', {})
            user = auth.get('ssh_username', '')
            password = auth.get('ssh_password', '')
            path = info.get('alertRuleConfigPath', '')
            uri = info.get('prometheusReloadApiEndpoint', '')
            if not (host and user and path and uri):
                continue
            target_list.append({
                'host': host,
                'port': port,
                'user': user,
                'password': password,
                'path': path
            })
            reload_list.append(uri)
        return target_list, list(set(reload_list))

    def upload_rules(self, context, target_list, reload_list, rule_group, id):
        def _cleanup_error(target_list):
            for target in target_list:
                try:
                    self._delete_rule(target['host'], target['port'],
                        target['user'], target['password'], target['path'],
                        id)
                except (sol_ex.PrometheusPluginError, ks_exc.ClientException,
                        paramiko.SSHException):
                    pass

        try:
            for target in target_list:
                self._upload_rule(
                    rule_group, target['host'], target['port'],
                    target['user'], target['password'], target['path'],
                    id)
            for uri in reload_list:
                self.reload_prom_server(context, uri)
        except (sol_ex.PrometheusPluginError, ks_exc.ClientException,
                paramiko.SSHException) as e:
            LOG.error("failed to upload rule files: %s", e.args[0])
            _cleanup_error(target_list)
            raise e
        except Exception as e:
            _cleanup_error(target_list)
            raise e


class PrometheusPluginPm(PrometheusPluginPmBase, mon_base.MonitoringPlugin):
    _instance = None

    @staticmethod
    def instance():
        if PrometheusPluginPm._instance is None:
            if not CONF.prometheus_plugin.performance_management:
                stub = mon_base.MonitoringPluginStub.instance()
                PrometheusPluginPm._instance = stub
            else:
                PrometheusPluginPm()
        return PrometheusPluginPm._instance

    def __init__(self):
        if PrometheusPluginPm._instance:
            raise SystemError(
                "Not constructor but instance() should be used.")
        super(PrometheusPluginPm, self).__init__()
        self.notification_callback = None
        self.reporting_period_margin = (
            CONF.prometheus_plugin.reporting_period_margin)
        self.notification_callback = self.default_callback
        PrometheusPluginPm._instance = self

    def set_callback(self, notification_callback):
        self.notification_callback = notification_callback

    def create_job(self, **kwargs):
        return self.make_rules(kwargs['context'], kwargs['pm_job'])

    def delete_job(self, **kwargs):
        self.delete_rules(kwargs['context'], kwargs['pm_job'])

    def alert(self, **kwargs):
        try:
            self._alert(kwargs['request'], body=kwargs['body'])
        except Exception as e:
            # All exceptions is ignored here and 204 response will always
            # be returned because when tacker responds error to alertmanager,
            # alertmanager may repeat the same reports.
            LOG.error("%s: %s", e.__class__.__name__, e.args[0])

    def default_callback(self, context, entries):
        self.rpc.store_job_info(context, entries)

    def get_datetime_of_latest_report(
            self, context, pm_job, object_instance_id,
            sub_object_instance_id, metric):
        report = pm_job_utils.get_pm_report(context, pm_job.id)
        if not report:
            return None

        report = list(map(lambda x: x.entries, report))
        report = list(itertools.chain.from_iterable(report))
        entries_of_same_object = list(
            filter(
                lambda x: (
                    x.objectInstanceId == object_instance_id and
                    (not x.obj_attr_is_set('subObjectInstanceId') or
                     x.subObjectInstanceId == sub_object_instance_id) and
                    x.performanceMetric == metric),
                report))
        if len(entries_of_same_object) == 0:
            return None
        values = sum(list(map(
            lambda x: x.performanceValues, entries_of_same_object)), [])
        return max(values, key=lambda value:
                   self.parse_datetime(value.timeStamp)).timeStamp

    def filter_alert_by_time(
            self, context, pm_job, datetime_now,
            object_instance_id, sub_object_instance_id, metric):
        # Ignore expired alert
        reporting_boundary = pm_job.criteria.reportingBoundary\
            if (pm_job.criteria.obj_attr_is_set('reportingBoundary') and
                pm_job.criteria.reportingBoundary) else None
        if (reporting_boundary and
                datetime_now > self.parse_datetime(reporting_boundary)):
            raise sol_ex.PrometheusPluginSkipped()

        # Ignore short period alert
        report_date = self.get_datetime_of_latest_report(
            context, pm_job, object_instance_id, sub_object_instance_id,
            metric)

        # reporting_period_margin is some margin for timing inconsistency
        # between prometheus and tacker.
        if (report_date and report_date + datetime.timedelta(
            seconds=(pm_job.criteria.reportingPeriod -
                     self.reporting_period_margin)) >= datetime_now):
            raise sol_ex.PrometheusPluginSkipped()

    def valid_alert(self, pm_job, object_instance_id, sub_object_instance_id):
        object_instance_ids = (
            pm_job.objectInstanceIds
            if (pm_job.obj_attr_is_set('objectInstanceIds') and
                pm_job.objectInstanceIds) else [])
        if object_instance_id not in object_instance_ids:
            LOG.error(
                f"labels.object_instance_id {object_instance_id} "
                f"doesn't match pmJob.")
            raise sol_ex.PrometheusPluginSkipped()
        sub_object_instance_ids = (
            pm_job.subObjectInstanceIds
            if (pm_job.obj_attr_is_set('subObjectInstanceIds') and
                pm_job.subObjectInstanceIds) else [])
        if (sub_object_instance_id and
                (not sub_object_instance_ids or
                 sub_object_instance_id not in sub_object_instance_ids)):
            LOG.error(
                f"labels.sub_object_instance_id {sub_object_instance_id} "
                f"doesn't match pmJob.")
            raise sol_ex.PrometheusPluginSkipped()

    @validator.schema_nover(prometheus_plugin_schemas.AlertMessage)
    def _alert(self, request, body):
        result = []
        context = request.context
        datetime_now = datetime.datetime.now(datetime.timezone.utc)
        for alert in body['alerts']:
            if alert['labels']['function_type'] != 'vnfpm':
                continue
            try:
                pm_job_id = alert['labels']['job_id']
                object_instance_id = alert['labels']['object_instance_id']
                metric = alert['labels']['metric']
                sub_object_instance_id = alert['labels'].get(
                    'sub_object_instance_id')
                value = alert['annotations']['value']

                pm_job = pm_job_utils.get_pm_job(context, pm_job_id)
                self.filter_alert_by_time(context, pm_job, datetime_now,
                                          object_instance_id,
                                          sub_object_instance_id, metric)
                self.valid_alert(
                    pm_job, object_instance_id, sub_object_instance_id)
                value = self.convert_measurement_unit(metric, value)

                result.append({
                    'objectType': pm_job.objectType,
                    'objectInstanceId': object_instance_id,
                    'subObjectInstanceId': sub_object_instance_id,
                    'performanceMetric': metric,
                    'performanceValues': [{
                        'timeStamp': datetime_now,
                        'value': value
                    }]
                })
            except sol_ex.PrometheusPluginSkipped:
                pass
        if len(result) > 0:
            if self.notification_callback:
                # every job_id in body['alerts'] has same id
                self.notification_callback(context, {
                    'id': uuidutils.generate_uuid(),
                    'jobId': pm_job_id,
                    'entries': result,
                })
        return result

    def decompose_metrics_vnfc(self, pm_job):
        metrics = pm_job.criteria.performanceMetric\
            if pm_job.criteria.obj_attr_is_set('performanceMetric') else None
        metrics = (list(filter(lambda x: (
            re.match(r'^V(Cpu|Memory|Disk)Usage(Mean|Peak)Vnf\..+', x) and
            re.sub(r'^V(Cpu|Memory|Disk)Usage(Mean|Peak)Vnf\.', '',
                   x) in pm_job.objectInstanceIds), metrics))
            if metrics else [])
        metric_grps = pm_job.criteria.performanceMetricGroup\
            if (pm_job.criteria.obj_attr_is_set('performanceMetricGroup') and
                pm_job.criteria.performanceMetricGroup) else []
        for obj in pm_job.objectInstanceIds:
            for grp in metric_grps:
                if grp == 'VirtualisedComputeResource':
                    metrics.append(f'VCpuUsageMeanVnf.{obj}')
                    metrics.append(f'VCpuUsagePeakVnf.{obj}')
                    metrics.append(f'VMemoryUsageMeanVnf.{obj}')
                    metrics.append(f'VMemoryUsagePeakVnf.{obj}')
                    metrics.append(f'VDiskUsageMeanVnf.{obj}')
                    metrics.append(f'VDiskUsagePeakVnf.{obj}')
        metrics = list(set(metrics))
        if len(metrics) == 0:
            raise sol_ex.PrometheusPluginError(
                "Invalid performanceMetric or performanceMetricGroup."
            )
        return metrics

    def _make_rules_for_each_obj(self, pm_job, inst_map, metric):
        target = re.sub(r'\..+$', '', metric)
        objs = pm_job.objectInstanceIds
        collection_period = pm_job.criteria.collectionPeriod
        reporting_period = pm_job.criteria.reportingPeriod
        rules = []
        for obj in objs:
            # resource ids are like:
            #   ['test-test1-756757f8f-xcwmt',
            #    'test-test2-756757f8f-kmghr', ...]
            # convert them to a regex string such as:
            #   '(test-test1-[0-9a-f]{1,10}-[0-9a-z]{5}$|
            #    test-test2-[0-9a-f]{1,10}-[0-9a-z]{5}$|...)'
            pods_regexp = self.get_pod_regexp(inst_map[obj])
            if pods_regexp is None:
                continue
            namespace = self.get_namespace(inst_map[obj])
            expr = self.make_prom_ql(
                target, pods_regexp, collection_period=collection_period,
                reporting_period=reporting_period, namespace=namespace)
            rules.append(self.make_rule(
                'PMJob', pm_job.id, obj, None, metric, expr,
                collection_period=collection_period))
        return rules

    def _make_rules_for_each_sub_obj(self, pm_job, inst_map, metric):
        target = re.sub(r'\..+$', '', metric)
        objs = pm_job.objectInstanceIds
        sub_objs = pm_job.subObjectInstanceIds\
            if (pm_job.obj_attr_is_set('subObjectInstanceIds') and
                pm_job.subObjectInstanceIds) else []
        collection_period = pm_job.criteria.collectionPeriod
        reporting_period = pm_job.criteria.reportingPeriod
        rules = []
        resource_info = self.get_vnfc_resource_info(inst_map[objs[0]])
        if not resource_info:
            return []
        if pm_job.objectType in {'Vnf', 'Vnfc'}:
            inst = inst_map[objs[0]]
            for sub_obj in sub_objs:
                compute_resource = self.get_compute_resource_by_sub_obj(
                    inst, sub_obj)
                if not compute_resource:
                    continue
                resource_id = compute_resource.resourceId
                namespace = self.get_namespace(inst)
                expr = self.make_prom_ql(
                    target, resource_id,
                    collection_period=collection_period,
                    reporting_period=reporting_period,
                    namespace=namespace)
                rules.append(self.make_rule(
                    'PMJob', pm_job.id, objs[0], sub_obj, metric, expr,
                    collection_period=collection_period))
        else:
            pods_regexp = self.get_pod_regexp(inst_map[objs[0]])
            if pods_regexp is None:
                return []
            for sub_obj in sub_objs:
                namespace = self.get_namespace(inst_map[objs[0]])
                expr = self.make_prom_ql(
                    target, pods_regexp, collection_period=collection_period,
                    reporting_period=reporting_period,
                    sub_object_instance_id=sub_obj, namespace=namespace)
                rules.append(self.make_rule(
                    'PMJob', pm_job.id, objs[0], sub_obj, metric, expr,
                    collection_period=collection_period))
        return rules

    def decompose_metrics_vnfintextcp(self, pm_job):
        group_name = 'VnfInternalCp'\
            if pm_job.objectType == 'VnfIntCp' else 'VnfExternalCp'
        metrics = pm_job.criteria.performanceMetric\
            if pm_job.criteria.obj_attr_is_set('performanceMetric') else None
        metrics = list(filter(lambda x: (
            re.match(r'^(Byte|Packet)(Incoming|Outgoing)' + pm_job.objectType,
                     x)),
            metrics)) if metrics else []
        metric_grps = pm_job.criteria.performanceMetricGroup\
            if (pm_job.criteria.obj_attr_is_set('performanceMetricGroup') and
                pm_job.criteria.performanceMetricGroup) else []
        for grp in metric_grps:
            if grp == group_name:
                metrics.append(f'ByteIncoming{pm_job.objectType}')
                metrics.append(f'ByteOutgoing{pm_job.objectType}')
                metrics.append(f'PacketIncoming{pm_job.objectType}')
                metrics.append(f'PacketOutgoing{pm_job.objectType}')
        metrics = list(set(metrics))
        if len(metrics) == 0:
            raise sol_ex.PrometheusPluginError(
                "Invalid performanceMetric or performanceMetricGroup."
            )
        return metrics

    def get_vnf_instances(self, context, pm_job):
        object_instance_ids = list(set(pm_job.objectInstanceIds))
        return dict(zip(
            object_instance_ids,
            list(map(
                lambda inst: inst_utils.get_inst(context, inst),
                object_instance_ids))))


class PrometheusPluginThreshold(PrometheusPluginPmBase,
                                mon_base.MonitoringPlugin):

    _instance = None

    @staticmethod
    def instance():
        if PrometheusPluginThreshold._instance is None:
            if not CONF.prometheus_plugin.performance_management:
                stub = mon_base.MonitoringPluginStub.instance()
                PrometheusPluginThreshold._instance = stub
            else:
                PrometheusPluginThreshold()
        return PrometheusPluginThreshold._instance

    def __init__(self):
        if PrometheusPluginThreshold._instance:
            raise SystemError(
                "Not constructor but instance() should be used.")
        super(PrometheusPluginThreshold, self).__init__()
        self.notification_callback = self.default_callback
        PrometheusPluginThreshold._instance = self

    def create_threshold(self, **kwargs):
        return self.make_rules(kwargs['context'], kwargs['pm_threshold'])

    def delete_threshold(self, **kwargs):
        self.delete_rules(kwargs['context'], kwargs['pm_threshold'])

    def default_callback(self, context, threshold_states):
        self.rpc.store_threshold_state_info(context, threshold_states)

    def valid_alert(self, pm_threshold, metric, object_instance_id,
                    sub_object_instance_id):
        instance_id = (
            pm_threshold.objectInstanceId
            if (pm_threshold.obj_attr_is_set('objectInstanceId') and
                pm_threshold.objectInstanceId) else None)
        if object_instance_id != instance_id:
            LOG.error(
                f"labels.object_instance_id {object_instance_id} "
                "doesn't match pm_threshold.")
            raise sol_ex.PrometheusPluginSkipped()

        sub_object_instance_ids = (
            pm_threshold.subObjectInstanceIds
            if (pm_threshold.obj_attr_is_set('subObjectInstanceIds') and
                pm_threshold.subObjectInstanceIds) else [])
        if (sub_object_instance_id and
                (not sub_object_instance_ids or
                 sub_object_instance_id not in sub_object_instance_ids)):
            LOG.error(
                f"labels.sub_object_instance_id {sub_object_instance_id} "
                "doesn't match pm_threshold.")
            raise sol_ex.PrometheusPluginSkipped()

        if metric != pm_threshold.criteria.performanceMetric:
            LOG.error(
                f"labels.metric {metric} doesn't match pm_threshold.")
            raise sol_ex.PrometheusPluginSkipped()

    def set_threshold_last_value(
            self, threshold_value, pm_threshold_state):
        threshold_last_value = threshold_value
        if pm_threshold_state and pm_threshold_state.get('performanceValue'):
            threshold_last_value = pm_threshold_state['performanceValue']
        return float(threshold_last_value)

    def set_crossing_direction(self, threshold_new_value, threshold_last_value,
                               threshold_value, threshold_hysteresis):
        # NOTE: "IN" is simply used to mark not to send
        # ThresholdCrossedNotification.
        crossing_direction = "IN"
        if (threshold_new_value > (threshold_value + threshold_hysteresis) >=
                threshold_last_value):
            crossing_direction = "UP"
        if (threshold_new_value < (threshold_value - threshold_hysteresis) <=
                threshold_last_value):
            crossing_direction = "DOWN"
        return crossing_direction

    @validator.schema_nover(prometheus_plugin_schemas.AlertMessage)
    def _alert(self, request, body):
        result = []
        context = request.context
        alerts = (alert for alert in body['alerts'] if
                  alert['status'] == 'firing' and
                  alert['labels']['receiver_type'] == 'tacker' and
                  alert['labels']['function_type'] == 'vnfpm_threshold')

        for alert in alerts:
            try:
                pm_threshold_id = alert['labels']['threshold_id']
                object_instance_id = alert['labels']['object_instance_id']
                metric = alert['labels']['metric']
                sub_object_instance_id = alert['labels'].get(
                    'sub_object_instance_id')
                value = alert['annotations']['value']

                pm_threshold = pm_threshold_utils.get_pm_threshold(
                    context, pm_threshold_id)
                if not pm_threshold:
                    raise sol_ex.PMThresholdNotExist(
                        threshold_id=pm_threshold_id)
                threshold_type = pm_threshold.criteria.thresholdType
                simple_threshold_details = (
                    pm_threshold.criteria.simpleThresholdDetails)

                self.valid_alert(pm_threshold, metric, object_instance_id,
                                 sub_object_instance_id)

                if threshold_type == "SIMPLE" and simple_threshold_details:
                    threshold_value = simple_threshold_details.thresholdValue
                    threshold_hysteresis = simple_threshold_details.hysteresis

                    pm_threshold_state = (
                        pm_threshold_utils.get_pm_threshold_state(
                            pm_threshold, sub_object_instance_id))

                    threshold_new_value = self.convert_measurement_unit(
                        metric, value)
                    threshold_last_value = self.set_threshold_last_value(
                        threshold_value, pm_threshold_state)

                    crossing_direction = self.set_crossing_direction(
                        threshold_new_value, threshold_last_value,
                        threshold_value, threshold_hysteresis
                    )

                    result.append({
                        'thresholdId': pm_threshold.id,
                        'subObjectInstanceId': sub_object_instance_id,
                        'performanceValue': threshold_new_value,
                        'metrics': metric,
                        'crossingDirection': crossing_direction
                    })
                else:
                    LOG.error("Lack thresholdValue and hysteresis")
            except (sol_ex.PrometheusPluginSkipped,
                    sol_ex.PMThresholdNotExist):
                pass

        # Call ConductorV2
        if result and self.notification_callback:
            self.notification_callback(
                context, result)
            for res in result:
                res.pop('thresholdId')
        return result

    def decompose_metrics_vnfc(self, pm_threshold):
        # pm_threshold.criteria.performanceMetric : String  1
        # pm_threshold.objectInstanceId : String   1
        metrics = []
        metric = (pm_threshold.criteria.performanceMetric
                  if pm_threshold.criteria.obj_attr_is_set('performanceMetric')
                  else None)

        _metric = (re.match(
            r'^V(Cpu|Memory|Disk)Usage(Mean|Peak)Vnf\..+', metric) and re.sub(
            r'^V(Cpu|Memory|Disk)Usage(Mean|Peak)Vnf\.', '', metric))
        if _metric == pm_threshold.objectInstanceId:
            metrics.append(metric)
            return metrics
        else:
            raise sol_ex.PrometheusPluginError(
                "Invalid performanceMetric.")

    def decompose_metrics_vnfintextcp(self, pm_threshold):
        # pm_threshold.criteria.performanceMetric : String  1
        metrics = []
        metric = (pm_threshold.criteria.performanceMetric
                  if pm_threshold.criteria.obj_attr_is_set('performanceMetric')
                  else None)

        _metric = re.match(r'^(Byte|Packet)(Incoming|Outgoing)' +
                           pm_threshold.objectType, metric)
        if _metric:
            metrics.append(metric)
            return metrics
        else:
            raise sol_ex.PrometheusPluginError(
                "Invalid performanceMetric.")

    def _make_rules_for_each_obj(self, pm_threshold, inst_map, metric):
        target = re.sub(r'\..+$', '', metric)
        obj = pm_threshold.objectInstanceId
        rules = []
        # resource ids are like:
        #   ['test-test1-756757f8f-xcwmt',
        #    'test-test2-756757f8f-kmghr', ...]
        # convert them to a regex string such as:
        #   '(test-test1-[0-9a-f]{1,10}-[0-9a-z]{5}$|
        #    test-test2-[0-9a-f]{1,10}-[0-9a-z]{5}$|...)'
        pods_regexp = self.get_pod_regexp(inst_map[obj])
        namespace = self.get_namespace(inst_map[obj])
        reporting_period = CONF.prometheus_plugin.reporting_period_threshold
        collection_period = CONF.prometheus_plugin.collection_period_threshold

        expr = self.make_prom_ql(
            target, pods_regexp, collection_period=collection_period,
            reporting_period=reporting_period, pm_type="Threshold",
            namespace=namespace)
        rules.append(self.make_rule(
            'Threshold', pm_threshold.id, obj, None, metric, expr,
            collection_period=collection_period))
        return rules

    def _make_rules_for_each_sub_obj(self, pm_threshold, inst_map, metric):
        reporting_period = CONF.prometheus_plugin.reporting_period_threshold
        collection_period = CONF.prometheus_plugin.collection_period_threshold
        target = re.sub(r'\..+$', '', metric)
        obj = pm_threshold.objectInstanceId
        sub_objs = (pm_threshold.subObjectInstanceIds
                    if (pm_threshold.obj_attr_is_set('subObjectInstanceIds')
                        and pm_threshold.subObjectInstanceIds) else [])
        rules = []
        if pm_threshold.objectType in {'Vnf', 'Vnfc'}:
            inst = inst_map[obj]
            for sub_obj in sub_objs:
                compute_resource = self.get_compute_resource_by_sub_obj(
                    inst, sub_obj)
                if not compute_resource:
                    continue
                resource_id = compute_resource.resourceId
                namespace = self.get_namespace(inst)
                expr = self.make_prom_ql(
                    target, resource_id,
                    collection_period=collection_period,
                    reporting_period=reporting_period,
                    pm_type="Threshold",
                    namespace=namespace
                )
                rules.append(self.make_rule(
                    'Threshold', pm_threshold.id, obj, sub_obj, metric, expr,
                    collection_period=collection_period))
        else:
            pods_regexp = self.get_pod_regexp(inst_map[obj])
            if pods_regexp is None:
                return []
            for sub_obj in sub_objs:
                namespace = self.get_namespace(inst_map[obj])
                expr = self.make_prom_ql(
                    target, pods_regexp,
                    collection_period=collection_period,
                    reporting_period=reporting_period,
                    sub_object_instance_id=sub_obj,
                    pm_type="Threshold",
                    namespace=namespace
                )
                rules.append(self.make_rule(
                    'Threshold', pm_threshold.id, obj, sub_obj, metric, expr,
                    collection_period=collection_period))
        return rules

    def get_vnf_instances(self, context, pm_threshold):
        return {
            pm_threshold.objectInstanceId: inst_utils.get_inst(
                context, pm_threshold.objectInstanceId)
        }


class PrometheusPluginFm(PrometheusPlugin, mon_base.MonitoringPlugin):
    _instance = None

    @staticmethod
    def instance():
        if PrometheusPluginFm._instance is None:
            if not CONF.prometheus_plugin.fault_management:
                stub = mon_base.MonitoringPluginStub.instance()
                PrometheusPluginFm._instance = stub
            else:
                PrometheusPluginFm()
        return PrometheusPluginFm._instance

    def __init__(self):
        if PrometheusPluginFm._instance:
            raise SystemError(
                "Not constructor but instance() should be used.")
        super(PrometheusPluginFm, self).__init__()
        self.notification_callback = self.default_callback
        self.endpoint = CONF.v2_vnfm.endpoint
        PrometheusPluginFm._instance = self

    def set_callback(self, notification_callback):
        self.notification_callback = notification_callback

    def alert(self, **kwargs):
        try:
            self._alert(kwargs['request'], body=kwargs['body'])
        except Exception as e:
            # All exceptions is ignored here and 204 response will always
            # be returned because when tacker responds error to alertmanager,
            # alertmanager may repeat the same reports.
            LOG.error("%s: %s", e.__class__.__name__, e.args[0])

    def default_callback(self, context, alarm):
        self.rpc.store_alarm_info(context, alarm)

    def vnfc_instance_ids(
            self, context, vnf_instance_id, alert_entry):
        inst = inst_utils.get_inst(context, vnf_instance_id)
        resources = (inst.instantiatedVnfInfo.vnfcResourceInfo
                if inst.obj_attr_is_set('instantiatedVnfInfo') and
                inst.instantiatedVnfInfo.obj_attr_is_set(
                    'vnfcResourceInfo') else [])
        vnfc_info = (inst.instantiatedVnfInfo.vnfcInfo
                if inst.obj_attr_is_set('instantiatedVnfInfo') and
                inst.instantiatedVnfInfo.obj_attr_is_set(
                    'vnfcInfo') else [])
        if 'pod' not in alert_entry['labels']:
            return []
        pod = alert_entry['labels']['pod']

        deployments = list(filter(
            lambda r: (
                r.computeResource.obj_attr_is_set('vimLevelResourceType') and
                r.computeResource.obj_attr_is_set('resourceId') and
                (r.computeResource.vimLevelResourceType in
                    {'Deployment', 'Pod'}) and
                re.match(pod, r.computeResource.resourceId)),
            resources
        ))
        vnfc_res_info_ids = list(map(
            lambda res: res.id, deployments
        ))
        vnfc_info = list(filter(
            lambda info: (
                info.obj_attr_is_set('vnfcResourceInfoId') and
                info.vnfcResourceInfoId in vnfc_res_info_ids),
            vnfc_info
        ))
        vnfc_info = list(map(lambda info: info.id, vnfc_info))
        return vnfc_info

    def update_alarm(self, context, not_cleared, ends_at, datetime_now):
        for alm in not_cleared:
            alm.alarmClearedTime = ends_at
            alm.alarmChangedTime = datetime_now
            if self.notification_callback:
                self.notification_callback(context, alm)

    def create_new_alarm(self, context, alert_entry, datetime_now):
        vnf_instance_id = alert_entry['labels']['vnf_instance_id']
        fingerprint = alert_entry['fingerprint']
        perceived_severity = alert_entry['labels']['perceived_severity']

        fault_details = [
            f"fingerprint: {fingerprint}",
            f"detail: {alert_entry['annotations'].get('fault_details')}"
        ]

        vnfc_instance_ids = self.vnfc_instance_ids(
            context, vnf_instance_id, alert_entry)
        if len(vnfc_instance_ids) == 0:
            LOG.error("failed to specify vnfc_instance for the alert.")
            raise sol_ex.PrometheusPluginSkipped()

        new_alarm = objects.AlarmV1.from_dict({
            'id':
                uuidutils.generate_uuid(),
            'managedObjectId':
                vnf_instance_id,
            'vnfcInstanceIds':
                vnfc_instance_ids,
            'alarmRaisedTime':
                datetime_now.isoformat(),
            'ackState':
                'UNACKNOWLEDGED',
            'perceivedSeverity':
                perceived_severity,
            'eventTime':
                alert_entry['startsAt'],
            'eventType':
                alert_entry['labels'].get('event_type', ''),
            'faultType':
                alert_entry['annotations'].get('fault_type', ''),
            'probableCause':
                alert_entry['annotations'].get('probable_cause', ''),
            'isRootCause':
                False,
            'faultDetails':
                fault_details,
            '_links': {}
        })

        _links = fm_alarm_utils.make_alarm_links(new_alarm, self.endpoint)
        new_alarm._links = _links
        if self.notification_callback:
            self.notification_callback(context, new_alarm)
        return new_alarm

    def get_not_cleared_alarms(self, context, vnf_instance_id, fingerprint):
        alms = fm_alarm_utils.get_not_cleared_alarms(context, vnf_instance_id)
        fpstr = f'fingerprint: {fingerprint}'
        return list(filter(
            lambda x: (not x.obj_attr_is_set('alarmClearedTime') and
                       x.obj_attr_is_set('faultDetails') and
                       fpstr in x.faultDetails), alms))

    def create_or_update_alarm(
            self, context, alert_entry, datetime_now):
        status = alert_entry['status']
        vnf_instance_id = alert_entry['labels']['vnf_instance_id']
        fingerprint = alert_entry['fingerprint']
        not_cleared = self.get_not_cleared_alarms(
            context, vnf_instance_id, fingerprint)

        if status == 'resolved' and len(not_cleared) > 0:
            ends_at = alert_entry['endsAt']
            self.update_alarm(
                context, not_cleared, ends_at, datetime_now)
            return not_cleared
        if status == 'firing' and len(not_cleared) == 0:
            new_alarm = self.create_new_alarm(
                context, alert_entry, datetime_now)
            return [new_alarm]
        raise sol_ex.PrometheusPluginSkipped()

    @validator.schema_nover(prometheus_plugin_schemas.AlertMessage)
    def _alert(self, request, body):
        now = datetime.datetime.now(datetime.timezone.utc)
        result = []
        for alert in body['alerts']:
            if alert['labels']['function_type'] != 'vnffm':
                continue
            try:
                alarms = self.create_or_update_alarm(
                    request.context, alert, now)
                result.extend(alarms)
            except sol_ex.PrometheusPluginSkipped:
                pass
        return result


class PrometheusPluginAutoHealing(PrometheusPlugin, mon_base.MonitoringPlugin):
    _instance = None

    @staticmethod
    def instance():
        if PrometheusPluginAutoHealing._instance is None:
            if not CONF.prometheus_plugin.auto_healing:
                stub = mon_base.MonitoringPluginStub.instance()
                PrometheusPluginAutoHealing._instance = stub
            else:
                PrometheusPluginAutoHealing()
        return PrometheusPluginAutoHealing._instance

    def __init__(self):
        if PrometheusPluginAutoHealing._instance:
            raise SystemError(
                "Not constructor but instance() should be used.")
        super(PrometheusPluginAutoHealing, self).__init__()
        self.set_callback(self.default_callback)
        PrometheusPluginAutoHealing._instance = self

    def set_callback(self, notification_callback):
        self.notification_callback = notification_callback

    def alert(self, **kwargs):
        try:
            self._alert(kwargs['request'], body=kwargs['body'])
        except Exception as e:
            # All exceptions is ignored here and 204 response will always
            # be returned because when tacker responds error to alertmanager,
            # alertmanager may repeat the same reports.
            LOG.error("%s: %s", e.__class__.__name__, e.args[0])

    def default_callback(self, context, vnf_instance_id, vnfc_info_id):
        self.rpc.enqueue_auto_heal_instance(
            context, vnf_instance_id, vnfc_info_id)

    @validator.schema_nover(prometheus_plugin_schemas.AlertMessage)
    def _alert(self, request, body):
        context = request.context
        alerts = (alert for alert in body['alerts'] if
                  alert['status'] == 'firing' and
                  alert['labels']['receiver_type'] == 'tacker' and
                  alert['labels']['function_type'] == 'auto_heal')

        for alert in alerts:
            vnf_instance_id = alert['labels']['vnf_instance_id']
            try:
                inst = inst_utils.get_inst(context, vnf_instance_id)
            except sol_ex.VnfInstanceNotFound:
                continue
            if inst.instantiationState != 'INSTANTIATED':
                self.rpc.dequeue_auto_heal_instance(
                    None, vnf_instance_id)

            if (not inst.obj_attr_is_set('vnfConfigurableProperties')
                    or not inst.vnfConfigurableProperties.get(
                        'isAutohealEnabled')):
                continue

            vnfc_info_id = alert['labels']['vnfc_info_id']
            result = {
                vnfcInfo for vnfcInfo in inst.instantiatedVnfInfo.vnfcInfo
                if vnfcInfo.id == vnfc_info_id
            }
            if not result:
                continue

            if self.notification_callback:
                self.notification_callback(
                    context, vnf_instance_id, vnfc_info_id)


class PrometheusPluginAutoScaling(PrometheusPlugin, mon_base.MonitoringPlugin):
    _instance = None

    @staticmethod
    def instance():
        if PrometheusPluginAutoScaling._instance is None:
            if not CONF.prometheus_plugin.auto_scaling:
                stub = mon_base.MonitoringPluginStub.instance()
                PrometheusPluginAutoScaling._instance = stub
            else:
                PrometheusPluginAutoScaling()
        return PrometheusPluginAutoScaling._instance

    def __init__(self):
        if PrometheusPluginAutoScaling._instance:
            raise SystemError(
                "Not constructor but instance() should be used.")
        super(PrometheusPluginAutoScaling, self).__init__()
        self.set_callback(self.default_callback)
        PrometheusPluginAutoScaling._instance = self

    def set_callback(self, notification_callback):
        self.notification_callback = notification_callback

    def alert(self, **kwargs):
        try:
            self._alert(kwargs['request'], body=kwargs['body'])
        except Exception as e:
            # All exceptions is ignored here and 204 response will always
            # be returned because when tacker responds error to alertmanager,
            # alertmanager may repeat the same reports.
            LOG.error("%s: %s", e.__class__.__name__, e.args[0])

    def default_callback(self, context, vnf_instance_id, scaling_param):
        self.rpc.trigger_scale(context, vnf_instance_id, scaling_param)

    @validator.schema_nover(prometheus_plugin_schemas.AlertMessage)
    def _alert(self, request, body):
        context = request.context
        alerts = (alert for alert in body['alerts'] if
                  alert['status'] == 'firing' and
                  alert['labels']['receiver_type'] == 'tacker' and
                  alert['labels']['function_type'] == 'auto_scale')

        for alert in alerts:
            vnf_instance_id = alert['labels']['vnf_instance_id']
            try:
                inst = inst_utils.get_inst(context, vnf_instance_id)
            except sol_ex.VnfInstanceNotFound:
                continue
            if (inst.instantiationState != 'INSTANTIATED' or
                    not inst.obj_attr_is_set('vnfConfigurableProperties') or
                    not inst.vnfConfigurableProperties.get(
                        'isAutoscaleEnabled')):
                continue

            aspect_id = alert['labels']['aspect_id']
            result = {
                scaleStatus for scaleStatus in
                inst.instantiatedVnfInfo.scaleStatus
                if scaleStatus.aspectId == aspect_id
            }
            if not result:
                continue

            scaling_param = {
                'type': alert['labels']['auto_scale_type'],
                'aspectId': aspect_id,
            }
            if self.notification_callback:
                self.notification_callback(
                    context, vnf_instance_id, scaling_param)
