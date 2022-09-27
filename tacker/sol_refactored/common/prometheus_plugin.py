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

from oslo_log import log as logging
from oslo_utils import uuidutils
from tacker.sol_refactored.api import prometheus_plugin_validator as validator
from tacker.sol_refactored.api.schemas import prometheus_plugin_schemas
from tacker.sol_refactored.common import config as cfg
from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.common import fm_alarm_utils
from tacker.sol_refactored.common import http_client
from tacker.sol_refactored.common import monitoring_plugin_base as mon_base
from tacker.sol_refactored.common import pm_job_utils
from tacker.sol_refactored.common import vnf_instance_utils as inst_utils
from tacker.sol_refactored.conductor import conductor_rpc_v2 as rpc
from tacker.sol_refactored import objects


LOG = logging.getLogger(__name__)

CONF = cfg.CONF


class PrometheusPlugin():
    def __init__(self):
        self.rpc = rpc.PrometheusPluginConductor()

    def parse_datetime(self, isodate):
        t = (isodate if isinstance(isodate, datetime.datetime)
             else datetime.datetime.fromisoformat(
             isodate.replace('Z', '+00:00')))
        return t if t.tzinfo else t.astimezone()


class PrometheusPluginPm(PrometheusPlugin, mon_base.MonitoringPlugin):
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
        auth_handle = http_client.NoAuthHandle()
        self.client = http_client.HttpClient(auth_handle)
        self.reporting_period_margin = (
            CONF.prometheus_plugin.reporting_period_margin)
        self.notification_callback = self.default_callback
        self.sol_exp_map = {
            'VCpuUsageMeanVnf':
                'avg(sum(rate(pod_cpu_usage_seconds_total'
                '{{pod=~"{pod}"}}[{reporting_period}s])))',
            'VCpuUsagePeakVnf':
                'max(sum(rate(pod_cpu_usage_seconds_total'
                '{{pod=~"{pod}"}}[{reporting_period}s])))',
            'VMemoryUsageMeanVnf':
                'avg(pod_memory_working_set_bytes{{pod=~"{pod}"}} / '
                'on(pod) (kube_node_status_capacity{{resource="memory"}} * '
                'on(node) group_right kube_pod_info))',
            'VMemoryUsagePeakVnf':
                'max(pod_memory_working_set_bytes{{pod=~"{pod}"}} / '
                'on(pod) (kube_node_status_capacity{{resource="memory"}} * '
                'on(node) group_right kube_pod_info))',
            'VDiskUsageMeanVnf':
                'avg(container_fs_usage_bytes{{container="{container}",'
                'pod=~"{pod}"}}/container_fs_limit_bytes{{container='
                '"{container}",pod=~"{pod}"}})',
            'VDiskUsagePeakVnf':
                'max(container_fs_usage_bytes{{container="{container}",'
                'pod=~"{pod}"}}/container_fs_limit_bytes{{container='
                '"{container}",pod=~"{pod}"}})',
            'ByteIncomingVnfIntCp':
                'sum(container_network_receive_bytes_total'
                '{{interface="{sub_object_instance_id}",pod=~"{pod}"}})',
            'PacketIncomingVnfIntCp':
                'sum(container_network_receive_packets_total'
                '{{interface="{sub_object_instance_id}",pod=~"{pod}"}})',
            'ByteOutgoingVnfIntCp':
                'sum(container_network_transmit_bytes_total'
                '{{interface="{sub_object_instance_id}",pod=~"{pod}"}})',
            'PacketOutgoingVnfIntCp':
                'sum(container_network_transmit_packets_total'
                '{{interface="{sub_object_instance_id}",pod=~"{pod}"}})',
            'ByteIncomingVnfExtCp':
                'sum(container_network_receive_bytes_total'
                '{{interface="{sub_object_instance_id}",pod=~"{pod}"}})',
            'PacketIncomingVnfExtCp':
                'sum(container_network_receive_packets_total'
                '{{interface="{sub_object_instance_id}",pod=~"{pod}"}})',
            'ByteOutgoingVnfExtCp':
                'sum(container_network_transmit_bytes_total'
                '{{interface="{sub_object_instance_id}",pod=~"{pod}"}})',
            'PacketOutgoingVnfExtCp':
                'sum(container_network_transmit_packets_total'
                '{{interface="{sub_object_instance_id}",pod=~"{pod}"}})',
        }
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
            # be returned. Because when tacker responds error to alertmanager,
            # alertmanager may repeat the same reports.
            LOG.error("%s: %s", e.__class__.__name__, e.args[0])

    def default_callback(self, context, entries):
        self.rpc.store_job_info(context, entries)

    def convert_measurement_unit(self, metric, value):
        if re.match(r'^V(Cpu|Memory|Disk)Usage(Mean|Peak)Vnf\..+', metric):
            value = float(value)
        elif re.match(r'^(Byte|Packet)(Incoming|Outgoing)Vnf(IntCp|ExtCp)',
                      metric):
            value = int(value)
        else:
            raise sol_ex.PrometheusPluginError(
                  "Failed to convert annotations.value to measurement unit.")
        return value

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

    @validator.schema(prometheus_plugin_schemas.AlertMessage)
    def _alert(self, request, body):
        result = []
        context = request.context
        datetime_now = datetime.datetime.now(datetime.timezone.utc)
        for alt in body['alerts']:
            if alt['labels']['function_type'] != 'vnfpm':
                continue
            try:
                pm_job_id = alt['labels']['job_id']
                object_instance_id = alt['labels']['object_instance_id']
                metric = alt['labels']['metric']
                sub_object_instance_id = alt['labels'].get(
                    'sub_object_instance_id')
                value = alt['annotations']['value']

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

    def make_prom_ql(self, target, pod, container='', collection_period=30,
                     reporting_period=60, sub_object_instance_id='*'):
        reporting_period = max(reporting_period, 30)
        expr = self.sol_exp_map[target].format(
            pod=pod,
            container=container,
            collection_period=collection_period,
            reporting_period=reporting_period,
            sub_object_instance_id=sub_object_instance_id
        )
        return expr

    def make_rule(self, pm_job, object_instance_id, sub_object_instance_id,
                  metric, expression, collection_period):
        labels = {
            'alertname': '',
            'receiver_type': 'tacker',
            'function_type': 'vnfpm',
            'job_id': pm_job.id,
            'object_instance_id': object_instance_id,
            'sub_object_instance_id': sub_object_instance_id,
            'metric': metric
        }
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

    def get_vnfc_resource_info(self, _, vnf_instance_id, inst_map):
        inst = inst_map[vnf_instance_id]
        if not inst.obj_attr_is_set('instantiatedVnfInfo') or\
                not inst.instantiatedVnfInfo.obj_attr_is_set(
                    'vnfcResourceInfo'):
            return None
        return inst.instantiatedVnfInfo.vnfcResourceInfo

    def get_pod_regexp(self, resource_info):
        # resource ids are like:
        #   ['test-test1-756757f8f-xcwmt',
        #    'test-test2-756757f8f-kmghr', ...]
        # convert them to a regex string such as:
        #   '(test-test1-[0-9a-f]{1,10}-[0-9a-z]{5}$|
        #    test-test2-[0-9a-f]{1,10}-[0-9a-z]{5}$|...)'
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
        pods_regexp = '(' + '|'.join(deployments) + ')'
        return deployments, pods_regexp

    def _make_rules_for_each_obj(self, context, pm_job, inst_map, metric):
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
            resource_info = self.get_vnfc_resource_info(context, obj, inst_map)
            if not resource_info:
                continue
            deployments, pods_regexp = self.get_pod_regexp(resource_info)
            if len(deployments) == 0:
                continue
            expr = self.make_prom_ql(
                target, pods_regexp, collection_period=collection_period,
                reporting_period=reporting_period)
            rules.append(self.make_rule(
                pm_job, obj, None, metric, expr,
                collection_period))
        return rules

    def get_compute_resouce_by_sub_obj(self, vnf_instance, sub_obj):
        inst = vnf_instance
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

    def _make_rules_for_each_sub_obj(self, context, pm_job, inst_map, metric):
        target = re.sub(r'\..+$', '', metric)
        objs = pm_job.objectInstanceIds
        sub_objs = pm_job.subObjectInstanceIds\
            if (pm_job.obj_attr_is_set('subObjectInstanceIds') and
                pm_job.subObjectInstanceIds) else []
        collection_period = pm_job.criteria.collectionPeriod
        reporting_period = pm_job.criteria.reportingPeriod
        rules = []
        resource_info = self.get_vnfc_resource_info(context, objs[0], inst_map)
        if not resource_info:
            return []
        if pm_job.objectType in {'Vnf', 'Vnfc'}:
            inst = inst_map[objs[0]]
            for sub_obj in sub_objs:
                # resource id is like 'test-test1-756757f8f-xcwmt'
                # obtain 'test-test1' as deployment
                # obtain 'test' as container
                compute_resource = self.get_compute_resouce_by_sub_obj(
                    inst, sub_obj)
                if not compute_resource:
                    continue
                resource_id = compute_resource.resourceId
                deployment = re.sub(
                    r'\-[0-9a-f]{1,10}\-[0-9a-z]{5}$', '', resource_id)
                g = re.match(r'^(.+)\-\1{1,}[0-9]+', deployment)
                if not g:
                    continue
                container = g.group(1)
                expr = self.make_prom_ql(
                    target, resource_id, container=container,
                    collection_period=collection_period,
                    reporting_period=reporting_period)
                rules.append(self.make_rule(
                    pm_job, objs[0], sub_obj, metric, expr,
                    collection_period))
        else:
            deployments, pods_regexp = self.get_pod_regexp(resource_info)
            if len(deployments) == 0:
                return []
            for sub_obj in sub_objs:
                expr = self.make_prom_ql(
                    target, pods_regexp, collection_period=collection_period,
                    reporting_period=reporting_period,
                    sub_object_instance_id=sub_obj)
                rules.append(self.make_rule(
                    pm_job, objs[0], sub_obj, metric, expr,
                    collection_period))
        return rules

    def _make_rules(self, context, pm_job, metric, inst_map):
        sub_objs = pm_job.subObjectInstanceIds\
            if (pm_job.obj_attr_is_set('subObjectInstanceIds') and
                pm_job.subObjectInstanceIds) else []
        # Cardinality of objectInstanceIds and subObjectInstanceIds
        # is N:0 or 1:N.
        if len(sub_objs) > 0:
            return self._make_rules_for_each_sub_obj(
                context, pm_job, inst_map, metric)
        return self._make_rules_for_each_obj(
            context, pm_job, inst_map, metric)

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

    def _delete_rule(self, host, port, user, password, path, pm_job_id):
        with paramiko.Transport(sock=(host, port)) as client:
            client.connect(username=user, password=password)
            sftp = paramiko.SFTPClient.from_transport(client)
            sftp.remove(f'{path}/{pm_job_id}.json')

    def delete_rules(self, context, pm_job):
        target_list, reload_list = self.get_access_info(pm_job)
        for info in target_list:
            self._delete_rule(
                info['host'], info['port'], info['user'],
                info['password'], info['path'], pm_job.id)
        for uri in reload_list:
            self.reload_prom_server(context, uri)

    def decompose_metrics(self, pm_job):
        if pm_job.objectType in {'Vnf', 'Vnfc'}:
            return self.decompose_metrics_vnfc(pm_job)
        if pm_job.objectType in {'VnfIntCp', 'VnfExtCp'}:
            return self.decompose_metrics_vnfintextcp(pm_job)
        raise sol_ex.PrometheusPluginError(
            f"Invalid objectType: {pm_job.objectType}.")

    def reload_prom_server(self, context, reload_uri):
        resp, _ = self.client.do_request(
            reload_uri, "PUT", context=context)
        if resp.status_code != 202:
            LOG.error("reloading request to prometheus is failed: %d.",
                      resp.status_code)

    def _upload_rule(self, rule_group, host, port, user, password, path,
                     pm_job_id):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, 'rule.json'),
                      'w+', encoding="utf-8") as fp:
                json.dump(rule_group, fp, indent=4, ensure_ascii=False)
                filename = fp.name
            with paramiko.Transport(sock=(host, port)) as client:
                LOG.info("Upload rule files to prometheus server: %s.", host)
                client.connect(username=user, password=password)
                sftp = paramiko.SFTPClient.from_transport(client)
                sftp.put(filename, f'{path}/{pm_job_id}.json')

    def get_access_info(self, pm_job):
        target_list = []
        reload_list = []
        if (not pm_job.obj_attr_is_set('metadata')
                or 'monitoring' not in pm_job.metadata):
            raise sol_ex.PrometheusPluginError(
                  "monitoring info is missing at metadata field.")
        access_info = pm_job.metadata['monitoring']
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

    def upload_rules(
            self, context, target_list, reload_list, rule_group, pm_job):
        for info in target_list:
            self._upload_rule(
                rule_group, info['host'], info['port'], info['user'],
                info['password'], info['path'], pm_job.id)
        for uri in reload_list:
            self.reload_prom_server(context, uri)

    def get_vnf_instances(self, context, pm_job):
        object_instance_ids = list(set(pm_job.objectInstanceIds))
        return dict(zip(
            object_instance_ids,
            list(map(
                lambda inst: inst_utils.get_inst(context, inst),
                object_instance_ids))))

    def make_rules(self, context, pm_job):
        target_list, reload_list = self.get_access_info(pm_job)
        metrics = self.decompose_metrics(pm_job)
        inst_map = self.get_vnf_instances(context, pm_job)
        rules = sum([self._make_rules(context, pm_job, metric, inst_map)
                     for metric in metrics], [])
        if len(rules) == 0:
            raise sol_ex.PrometheusPluginError(
                  f"Converting from a PM job to alert rules is failed."
                  f" PM job id: {pm_job.id}")
        rule_group = {
            'groups': [
                {
                    'name': f'tacker_{pm_job.id}',
                    'rules': rules
                }
            ]
        }
        self.upload_rules(
            context, target_list, reload_list, rule_group, pm_job)
        return rule_group


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
            # be returned. Because when tacker responds error to alertmanager,
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

    @validator.schema(prometheus_plugin_schemas.AlertMessage)
    def _alert(self, request, body):
        now = datetime.datetime.now(datetime.timezone.utc)
        result = []
        for alt in body['alerts']:
            if alt['labels']['function_type'] != 'vnffm':
                continue
            try:
                alarms = self.create_or_update_alarm(
                    request.context, alt, now)
                result.extend(alarms)
            except sol_ex.PrometheusPluginSkipped:
                pass
        return result


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
        self.notification_callback = self.default_callback
        PrometheusPluginAutoScaling._instance = self

    def set_callback(self, notification_callback):
        self.notification_callback = notification_callback

    def alert(self, **kwargs):
        try:
            self._alert(kwargs['request'], body=kwargs['body'])
        except Exception as e:
            # All exceptions is ignored here and 204 response will always
            # be returned. Because when tacker responds error to alertmanager,
            # alertmanager may repeat the same reports.
            LOG.error("%s: %s", e.__class__.__name__, e.args[0])

    def default_callback(self, context, vnf_instance_id, scaling_param):
        self.rpc.request_scale(context, vnf_instance_id, scaling_param)

    def skip_if_auto_scale_not_enabled(self, vnf_instance):
        if (not vnf_instance.obj_attr_is_set('vnfConfigurableProperties') or
                not vnf_instance.vnfConfigurableProperties.get(
                    'isAutoscaleEnabled')):
            raise sol_ex.PrometheusPluginSkipped()

    def process_auto_scale(self, request, vnf_instance_id, auto_scale_type,
                           aspect_id):
        scaling_param = {
            'type': auto_scale_type,
            'aspectId': aspect_id,
        }
        context = request.context
        if self.notification_callback:
            self.notification_callback(context, vnf_instance_id, scaling_param)

    @validator.schema(prometheus_plugin_schemas.AlertMessage)
    def _alert(self, request, body):
        result = []
        for alt in body['alerts']:
            if alt['labels']['function_type'] != 'auto_scale':
                continue
            try:
                vnf_instance_id = alt['labels']['vnf_instance_id']
                auto_scale_type = alt['labels']['auto_scale_type']
                aspect_id = alt['labels']['aspect_id']
                context = request.context

                inst = inst_utils.get_inst(context, vnf_instance_id)
                self.skip_if_auto_scale_not_enabled(inst)
                self.process_auto_scale(
                    request, vnf_instance_id, auto_scale_type, aspect_id)
                result.append((vnf_instance_id, auto_scale_type, aspect_id))
            except sol_ex.PrometheusPluginSkipped:
                pass
        return result
