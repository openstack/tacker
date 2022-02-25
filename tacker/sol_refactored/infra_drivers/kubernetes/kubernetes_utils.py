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
import ipaddress
import os
import re
import time
from urllib.parse import urlparse
import urllib.request as urllib2

from kubernetes import client
from oslo_log import log as logging
from oslo_service import loopingcall
import yaml

from tacker.sol_refactored.common import config
from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.objects.v2 import fields as v2fields


LOG = logging.getLogger(__name__)
CONF = config.CONF
CHECK_INTERVAL = 10
SUPPORTED_NAMESPACE_KINDS = [
    "Pod",
    "Binding",
    "ConfigMap",
    "LimitRange",
    "PersistentVolumeClaim",
    "PodTemplate",
    "ResourceQuota",
    "Secret",
    "ServiceAccount",
    "Service",
    "ControllerRevision",
    "DaemonSet",
    "Deployment",
    "ReplicaSet",
    "StatefulSet",
    "LocalSubjectAccessReview",
    "HorizontalPodAutoscaler",
    "Job",
    "Lease",
    "NetworkPolicy",
    "RoleBinding",
    "Role"
]
RESOURCE_CREATION_ORDER = [
    "StorageClass",
    "PersistentVolume",
    "PriorityClass",
    "Namespace",
    "LimitRange",
    "ResourceQuota",
    "HorizontalPodAutoscaler",
    "NetworkPolicy",
    "Service",
    "Endpoints",
    "PersistentVolumeClaim",
    "ConfigMap",
    "Secret",
    "Pod",
    "Binding",
    "StatefulSet",
    "Job",
    "Deployment",
    "DaemonSet",
]
STATUS_CHECK_RES = [
    "Pod",
    "Service",
    "PersistentVolumeClaim",
    "Namespace",
    "Node",
    "PersistentVolume",
    "APIService",
    "DaemonSet",
    "Deployment",
    "ReplicaSet",
    "StatefulSet",
    "Job",
    "VolumeAttachment"
]


class KubernetesClient(object):

    def __init__(self, vim_info):
        self.k8s_api_client = init_k8s_api_client(vim_info)
        self.k8s_clients = get_k8s_clients(self.k8s_api_client)

    def create_k8s_resource(self, sorted_k8s_reses, namespace):
        created_k8s_reses = []

        for k8s_res in sorted_k8s_reses:
            kind = k8s_res.get('kind', '')
            api_version = k8s_res.get('apiVersion', '')
            name = k8s_res.get('metadata', {}).get('name', '')
            metadata = k8s_res.get('metadata', {})
            body = k8s_res
            k8s_client = self.k8s_clients[api_version]
            try:
                if kind in SUPPORTED_NAMESPACE_KINDS:
                    k8s_method = getattr(
                        k8s_client, f"create_namespaced_{convert(kind)}")
                    k8s_method(namespace=namespace, body=body)
                    create_k8s_res = {
                        "api_version": api_version,
                        "namespace": namespace,
                        "kind": kind,
                        "name": name,
                        "metadata": metadata,
                        "status": "CREATE_IN_PROCESS"
                    }
                else:
                    k8s_method = getattr(
                        k8s_client, f"create_{convert(kind)}")
                    k8s_method(body=body)
                    create_k8s_res = {
                        "api_version": api_version,
                        "kind": kind,
                        "name": name,
                        "metadata": metadata,
                        "status": "CREATE_IN_PROCESS"
                    }
                created_k8s_reses.append(create_k8s_res)
            except Exception as ex:
                LOG.error(ex)
                raise sol_ex.ExecuteK8SResourceCreateApiFailed
        return created_k8s_reses

    def delete_k8s_resource(self, req, sorted_k8s_reses, namespace):
        if req.terminationType:
            if req.terminationType == 'GRACEFUL' and req.obj_attr_is_set(
                    'gracefulTerminationTimeout'):
                body = client.V1DeleteOptions(
                    propagation_policy='Foreground',
                    grace_period_seconds=req.gracefulTerminationTimeout)
            else:
                body = client.V1DeleteOptions(
                    propagation_policy='Foreground',
                    grace_period_seconds=0)

        for k8s_res in sorted_k8s_reses:
            kind = k8s_res.get('kind', '')
            api_version = k8s_res.get('apiVersion', '')
            name = k8s_res.get('metadata', {}).get('name', '')
            k8s_client = self.k8s_clients[api_version]

            if kind == 'StatefulSet':
                pvcs_for_delete = self._get_pvcs_for_delete(
                    sfs_name=name, namespace=namespace)

            if kind == 'ControllerRevision':
                body = client.V1DeleteOptions(
                    propagation_policy='Background')
            try:
                if kind in SUPPORTED_NAMESPACE_KINDS:
                    k8s_method = getattr(
                        k8s_client, f"delete_namespaced_{convert(kind)}")
                    k8s_method(name=name, namespace=namespace, body=body)
                else:
                    k8s_method = getattr(
                        k8s_client, f"delete_{convert(kind)}")
                    k8s_method(name=name, body=body)
                k8s_res.update(status='DELETE_IN_PROGRESS')
            except Exception as ex:
                k8s_res.update(status='DELETE_IN_PROGRESS')
                LOG.debug(ex)

            if kind == 'StatefulSet' and len(pvcs_for_delete) > 0:
                for delete_pvc_name in pvcs_for_delete:
                    try:
                        self.k8s_clients[
                            'v1'].delete_namespaced_persistent_volume_claim(
                            name=delete_pvc_name, namespace=namespace,
                            body=body)
                    except Exception as ex:
                        LOG.debug(ex)

    def update_k8s_resource(self, new_reses, namespace):
        for k8s_res in new_reses:
            kind = k8s_res.get('kind', '')
            api_version = k8s_res.get('apiVersion', '')
            name = k8s_res.get('metadata', {}).get('name', '')
            k8s_client = self.k8s_clients[api_version]
            k8s_method = getattr(
                k8s_client, f"patch_namespaced_{convert(kind)}")
            try:
                k8s_method(name=name, namespace=namespace, body=k8s_res)
                k8s_res.update(status='UPDATE_IN_PROCESS')
            except Exception as e:
                LOG.error(f'update resource failed. kind: {kind},'
                          f' name: {name}')
                raise sol_ex.UpdateK8SResourceFailed from e

    def list_namespaced_pods(self, namespace):
        if namespace is None:
            return None
        return self.k8s_clients['v1'].list_namespaced_pod(
            namespace=namespace).items

    def check_deployment_exist(self, deployment_names, namespace):
        for name in deployment_names:
            try:
                self.k8s_clients['apps/v1'].read_namespaced_deployment(
                    name=name, namespace=namespace)
            except Exception as ex:
                LOG.error(f'update deployment {name} does'
                          f' not exist in kubernetes cluster')
                raise ex

    def _get_pvcs_for_delete(self, sfs_name, namespace):
        pvcs_for_delete = []
        try:
            resp_read_sfs = self.k8s_clients[
                'apps/v1'].read_namespaced_stateful_set(sfs_name, namespace)
            sfs_spec = resp_read_sfs.spec
            volume_claim_templates = sfs_spec.volume_claim_templates

            try:
                resps_pvc = self.k8s_clients[
                    'v1'].list_namespaced_persistent_volume_claim(namespace)
                pvcs = resps_pvc.items
                for volume_claim_template in volume_claim_templates:
                    pvc_template_metadata = volume_claim_template.metadata
                    match_pattern = '-'.join(
                        [pvc_template_metadata.name, sfs_name, ""])

                    for pvc in pvcs:
                        pvc_metadata = pvc.metadata
                        pvc_name = pvc_metadata.name
                        match_result = re.match(
                            match_pattern + '[0-9]+$', pvc_name)
                        if match_result is not None:
                            pvcs_for_delete.append(pvc_name)
            except Exception:
                pass
        except Exception:
            pass
        return pvcs_for_delete

    def _wait_completion(self, k8s_reses, operation,
                         namespace=None, old_pods_names=None):
        def _check_create_status():
            for k8s_res in k8s_reses:
                if k8s_res['status'] != 'CREATE_COMPLETE':
                    if k8s_res.get('kind') in STATUS_CHECK_RES:
                        res_check_method = getattr(
                            self, f"_check_status_"
                                  f"{convert(k8s_res.get('kind'))}")
                        res_check_method(k8s_res)
                    else:
                        k8s_res.update(status='CREATE_COMPLETE')
            statuses = {res['status'] for res in k8s_reses}
            if len(statuses) == 1 and statuses.pop() == 'CREATE_COMPLETE':
                raise loopingcall.LoopingCallDone()
            if len(statuses) > 1 and (int(time.time()) - start_time > timeout):
                raise sol_ex.CreateK8SResourceFailed

        def _check_delete_status():
            for k8s_res in k8s_reses:
                kind = k8s_res.get('kind', '')
                api_version = k8s_res.get('apiVersion', '')
                name = k8s_res.get('metadata', {}).get('name', '')
                k8s_client = self.k8s_clients[api_version]
                if k8s_res['status'] != 'DELETE_COMPLETE':
                    try:
                        if kind in SUPPORTED_NAMESPACE_KINDS:
                            k8s_method = getattr(
                                k8s_client, f'read_namespaced_{convert(kind)}')
                            k8s_method(name=name, namespace=namespace)
                        else:
                            k8s_method = getattr(
                                k8s_client, f'read_{convert(kind)}')
                            k8s_method(name=name)
                    except Exception:
                        k8s_res.update(status='DELETE_COMPLETE')
            statuses = {res['status'] for res in k8s_reses}
            if len(statuses) == 1 and statuses.pop() == 'DELETE_COMPLETE':
                raise loopingcall.LoopingCallDone()
            if len(statuses) > 1 and (int(time.time()) - start_time > timeout):
                raise sol_ex.DeleteK8SResourceFailed

        def _check_update_status():
            all_namespaced_pods = self.list_namespaced_pods(namespace)
            for k8s_res in k8s_reses:
                if k8s_res['status'] not in ['UPDATE_COMPLETE',
                                             'UPDATE_FAILED']:
                    kind = k8s_res.get('kind', '')
                    api_version = k8s_res.get('apiVersion', '')
                    name = k8s_res.get('metadata', {}).get('name', '')
                    k8s_client = self.k8s_clients[api_version]
                    k8s_method = getattr(
                        k8s_client, f'read_namespaced_{convert(kind)}')
                    k8s_info = k8s_method(name=name, namespace=namespace)
                    replicas = k8s_info.spec.replicas

                    pods_info = [pod for pod in all_namespaced_pods if
                                 is_match_pod_naming_rule(
                                     kind, name, pod.metadata.name)]
                    pending_flag = False
                    unkown_flag = False
                    for pod_info in pods_info:
                        if pod_info.status.phase == 'Pending':
                            pending_flag = True
                        elif pod_info.status.phase == 'Unknown':
                            unkown_flag = True

                    if not pending_flag and not unkown_flag and len(
                            pods_info) == replicas and (
                            pods_info[0].metadata.name not in old_pods_names):
                        k8s_res.update(status='UPDATE_COMPLETE')

                    if unkown_flag:
                        k8s_res.update(status='UPDATE_FAILED')

            statuses = {res['status'] for res in k8s_reses}
            if len(statuses) == 1 and list(statuses)[0] == 'UPDATE_COMPLETE':
                raise loopingcall.LoopingCallDone()
            if (list(statuses)[0] == 'UPDATE_IN_PROCESS' and (int(
                    time.time()) - start_time > timeout)) or (
                    'UPDATE_FAILED' in statuses):
                raise sol_ex.UpdateK8SResourceFailed

        start_time = int(time.time())
        timeout = CONF.v2_vnfm.kubernetes_vim_rsc_wait_timeout

        if operation == v2fields.LcmOperationType.INSTANTIATE:
            timer = loopingcall.FixedIntervalLoopingCall(_check_create_status)
        elif operation == v2fields.LcmOperationType.TERMINATE:
            timer = loopingcall.FixedIntervalLoopingCall(_check_delete_status)
        else:
            timer = loopingcall.FixedIntervalLoopingCall(_check_update_status)
        timer.start(interval=CHECK_INTERVAL).wait()

    def _check_status_pod(self, k8s_res):
        pod = self.k8s_clients[k8s_res.get(
            'api_version')].read_namespaced_pod(
            namespace=k8s_res.get('namespace'),
            name=k8s_res.get('name'))

        if pod.status.phase and pod.status.phase == 'Running':
            k8s_res.update(status='CREATE_COMPLETE')

    def _check_status_stateful_set(self, k8s_res):
        namespace = k8s_res.get('namespace')
        name = k8s_res.get('name')

        stateful_set = self.k8s_clients[k8s_res.get(
            'api_version')].read_namespaced_stateful_set(
            namespace=namespace, name=name)
        pvc_statuses = []
        replicas = stateful_set.status.replicas
        if replicas and replicas == stateful_set.status.ready_replicas:
            for i in range(0, stateful_set.spec.replicas):
                volume_claim_templates = (
                    stateful_set.spec.volume_claim_templates)
                for volume_claim_template in volume_claim_templates:
                    pvc_name = "-".join(
                        [volume_claim_template.metadata.name,
                         k8s_res.get('name'), str(i)])
                    persistent_volume_claim = (
                        self.k8s_clients[
                            'v1'].read_namespaced_persistent_volume_claim(
                            namespace=namespace, name=pvc_name))
                    pvc_statuses.append(persistent_volume_claim.status.phase)
        if len(set(pvc_statuses)) == 1 and pvc_statuses[0] == 'Bound':
            k8s_res.update(status='CREATE_COMPLETE')

    def _check_status_service(self, k8s_res):
        namespace = k8s_res.get('namespace')
        name = k8s_res.get('name')

        service = self.k8s_clients[k8s_res.get(
            'api_version')].read_namespaced_service(
            namespace=namespace, name=name)
        status_flag = False
        if service.spec.cluster_ip in ['', None] or check_is_ip(
                service.spec.cluster_ip):
            try:
                endpoint = self.k8s_clients['v1'].read_namespaced_endpoints(
                    namespace=namespace, name=name)
                if endpoint:
                    status_flag = True
            except Exception as e:
                raise sol_ex.ReadEndpointsFalse(
                    kind=k8s_res.get('kind')) from e

        if status_flag:
            k8s_res.update(status='CREATE_COMPLETE')

    def _check_status_persistent_volume_claim(self, k8s_res):
        namespace = k8s_res.get('namespace')
        name = k8s_res.get('name')

        claim = self.k8s_clients[k8s_res.get(
            'api_version')].read_namespaced_persistent_volume_claim(
            namespace=namespace, name=name)

        if claim.status.phase and claim.status.phase == 'Bound':
            k8s_res.update(status='CREATE_COMPLETE')

    def _check_status_namespace(self, k8s_res):
        name = k8s_res.get('name')

        name_space = self.k8s_clients[k8s_res.get(
            'api_version')].read_namespace(name=name)
        if name_space.status.phase and name_space.status.phase == 'Active':
            k8s_res.update(status='CREATE_COMPLETE')

    def _check_status_node(self, k8s_res):
        name = k8s_res.get('name')

        node = self.k8s_clients[k8s_res.get(
            'api_version')].read_node(name=name)
        status_flag = False
        for condition in node.status.conditions:
            if condition.type == 'Ready':
                if condition.status == 'True':
                    status_flag = True
                    break
            else:
                continue
        if status_flag:
            k8s_res.update(status='CREATE_COMPLETE')

    def _check_status_persistent_volume(self, k8s_res):
        name = k8s_res.get('name')

        volume = self.k8s_clients[k8s_res.get(
            'api_version')].read_persistent_volume(name=name)
        if volume.status.phase and volume.status.phase in [
                'Available', 'Bound']:
            k8s_res.update(status='CREATE_COMPLETE')

    def _check_status_api_service(self, k8s_res):
        name = k8s_res.get('name')

        api_service = self.k8s_clients[k8s_res.get(
            'api_version')].read_api_service(name=name)
        status_flag = False
        for condition in api_service.status.conditions:
            if condition.type == 'Available':
                if condition.status == 'True':
                    status_flag = True
                    break
            else:
                continue
        if status_flag:
            k8s_res.update(status='CREATE_COMPLETE')

    def _check_status_daemon_set(self, k8s_res):
        namespace = k8s_res.get('namespace')
        name = k8s_res.get('name')

        daemon_set = self.k8s_clients[k8s_res.get(
            'api_version')].read_namespaced_daemon_set(
            namespace=namespace, name=name)
        if daemon_set.status.desired_number_scheduled and (
                daemon_set.status.desired_number_scheduled ==
                daemon_set.status.number_ready):
            k8s_res.update(status='CREATE_COMPLETE')

    def _check_status_deployment(self, k8s_res):
        namespace = k8s_res.get('namespace')
        name = k8s_res.get('name')

        deployment = self.k8s_clients[k8s_res.get(
            'api_version')].read_namespaced_deployment(
            namespace=namespace, name=name)
        if deployment.status.replicas and (
                deployment.status.replicas ==
                deployment.status.ready_replicas):
            k8s_res.update(status='CREATE_COMPLETE')

    def _check_status_replica_set(self, k8s_res):
        namespace = k8s_res.get('namespace')
        name = k8s_res.get('name')

        replica_set = self.k8s_clients[k8s_res.get(
            'api_version')].read_namespaced_replica_set(
            namespace=namespace, name=name)
        if replica_set.status.replicas and (
                replica_set.status.replicas ==
                replica_set.status.ready_replicas):
            k8s_res.update(status='CREATE_COMPLETE')

    def _check_status_job(self, k8s_res):
        namespace = k8s_res.get('namespace')
        name = k8s_res.get('name')

        job = self.k8s_clients[k8s_res.get(
            'api_version')].read_namespaced_job(
            namespace=namespace, name=name)
        if job.spec.completions and (
                job.spec.completions == job.status.succeeded):
            k8s_res.update(status='CREATE_COMPLETE')

    def _check_status_volume_attachment(self, k8s_res):
        name = k8s_res.get('name')

        volume = self.k8s_clients[k8s_res.get(
            'api_version')].read_volume_attachment(name=name)
        if volume.status.attached:
            k8s_res.update(status='CREATE_COMPLETE')

    def wait_k8s_res_create(self, created_k8s_reses):
        self._wait_completion(created_k8s_reses, operation='INSTANTIATE')

    def wait_k8s_res_delete(self, sorted_k8s_reses, namespace):
        self._wait_completion(
            sorted_k8s_reses, operation='TERMINATE', namespace=namespace)

    def wait_k8s_res_update(self, new_k8s_reses, namespace,
                            old_pods_names=None):
        self._wait_completion(
            new_k8s_reses, operation='UPDATE', namespace=namespace,
            old_pods_names=old_pods_names)


def is_match_pod_naming_rule(rsc_kind, rsc_name, pod_name):
    match_result = None
    if rsc_kind == 'Pod':
        # Expected example: name
        if rsc_name == pod_name:
            match_result = True
    elif rsc_kind == 'Deployment':
        # Expected example: name-012789abef-019az
        # NOTE(horie): The naming rule of Pod in deployment is
        # "(deployment name)-(pod template hash)-(5 charactors)".
        # The "pod template hash" string is generated from 32 bit hash.
        # This may be from 1 to 10 caracters but not sure the lower limit
        # from the source code of Kubernetes.
        match_result = re.match(
            rsc_name + '-([0-9a-f]{1,10})-([0-9a-z]{5})+$',
            pod_name)
    elif rsc_kind in ('ReplicaSet', 'DaemonSet'):
        # Expected example: name-019az
        match_result = re.match(
            rsc_name + '-([0-9a-z]{5})+$',
            pod_name)
    elif rsc_kind == 'StatefulSet':
        # Expected example: name-0
        match_result = re.match(
            rsc_name + '-[0-9]+$',
            pod_name)
    if match_result:
        return True

    return False


def check_is_ip(ip_addr):
    try:
        ipaddress.ip_address(ip_addr)
        return True
    except ValueError:
        return False


def convert(tmp_name):
    name_with_underscores = re.sub(
        '(.)([A-Z][a-z]+)', r'\1_\2', tmp_name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2',
                  name_with_underscores).lower()


def init_k8s_api_client(vim_info):
    k8s_config = client.Configuration()
    k8s_config.host = vim_info.interfaceInfo['endpoint']

    if ('username' in vim_info.accessInfo and 'password'
            in vim_info.accessInfo and vim_info.accessInfo.get(
                'password') is not None):
        k8s_config.username = vim_info.accessInfo['username']
        k8s_config.password = vim_info.accessInfo['password']
        basic_token = k8s_config.get_basic_auth_token()
        k8s_config.api_key['authorization'] = basic_token

    if 'bearer_token' in vim_info.accessInfo:
        k8s_config.api_key_prefix['authorization'] = 'Bearer'
        k8s_config.api_key['authorization'] = vim_info.accessInfo[
            'bearer_token']

    if 'ssl_ca_cert' in vim_info.accessInfo:
        k8s_config.ssl_ca_cert = vim_info.accessInfo['ssl_ca_cert']
        k8s_config.verify_ssl = True
    else:
        k8s_config.verify_ssl = False

    return client.api_client.ApiClient(configuration=k8s_config)


def get_k8s_clients(k8s_api_client):
    k8s_clients = {
        "v1": client.CoreV1Api(api_client=k8s_api_client),
        "apiregistration.k8s.io/v1":
            client.ApiregistrationV1Api(api_client=k8s_api_client),
        "apps/v1": client.AppsV1Api(api_client=k8s_api_client),
        "authentication.k8s.io/v1":
            client.AuthenticationV1Api(api_client=k8s_api_client),
        "authorization.k8s.io/v1":
            client.AuthorizationV1Api(api_client=k8s_api_client),
        "autoscaling/v1": client.AutoscalingV1Api(
            api_client=k8s_api_client),
        "batch/v1": client.BatchV1Api(api_client=k8s_api_client),
        "coordination.k8s.io/v1":
            client.CoordinationV1Api(api_client=k8s_api_client),
        "networking.k8s.io/v1":
            client.NetworkingV1Api(api_client=k8s_api_client),
        "rbac.authorization.k8s.io/v1":
            client.RbacAuthorizationV1Api(api_client=k8s_api_client),
        "scheduling.k8s.io/v1":
            client.SchedulingV1Api(api_client=k8s_api_client),
        "storage.k8s.io/v1":
            client.StorageV1Api(api_client=k8s_api_client)
    }

    return k8s_clients


def get_k8s_json_file(req, inst, target_k8s_files, vnfd, operation):

    def _update_k8s_resources(namespace):
        for k8s_res in k8s_resources:
            if (k8s_res.get('kind', '') in SUPPORTED_NAMESPACE_KINDS and
                    k8s_res.get('metadata') is None):
                k8s_res.update(metadata={})
            if k8s_res.get('kind', '') in SUPPORTED_NAMESPACE_KINDS:
                k8s_res['metadata'].update(namespace=namespace)

    k8s_resources = []

    for target_k8s_file in target_k8s_files:
        if ((urlparse(target_k8s_file).scheme == 'file') or
                (bool(urlparse(target_k8s_file).scheme) and
                 bool(urlparse(target_k8s_file).netloc))):
            with urllib2.urlopen(target_k8s_file) as file_object:
                file_content = file_object.read()
        else:
            file_path = os.path.join(vnfd.csar_dir, target_k8s_file)
            with open(file_path, 'rb') as file_object:
                file_content = file_object.read()

        k8s_resources.extend(list(yaml.safe_load_all(file_content)))

    # check namespace
    if operation == v2fields.LcmOperationType.INSTANTIATE:
        if req.additionalParams.get('namespace') is None:
            _update_k8s_resources('default')
            namespaces = {
                k8s_res['metadata']['namespace'] for k8s_res in
                k8s_resources if k8s_res.get('kind') in
                SUPPORTED_NAMESPACE_KINDS}
            if len(namespaces) > 1:
                raise sol_ex.NamespaceNotUniform()
            return k8s_resources, namespaces.pop() if namespaces else None

        _update_k8s_resources(req.additionalParams.get('namespace'))
        return k8s_resources, req.additionalParams.get('namespace')

    return k8s_resources, inst.metadata.get('namespace')


def sort_k8s_resource(k8s_resources, operation):
    pos = 0
    sorted_k8s_reses = []

    if operation == v2fields.LcmOperationType.INSTANTIATE:
        sort_order = RESOURCE_CREATION_ORDER
    else:
        sort_order = list(reversed(RESOURCE_CREATION_ORDER))

    copy_k8s_resources = copy.deepcopy(k8s_resources)

    for kind in sort_order:
        for res_index, res in enumerate(copy_k8s_resources):
            if res.get('kind', '') == kind:
                index = k8s_resources.index(res)
                sorted_k8s_reses.append(k8s_resources.pop(index))
        # Other kind (such as PodTemplate, Node, and so on) that are
        # not present in `RESOURCE_CREATION_ORDER` are inserted in
        # place of the Service kind and created/deleted in the same
        # order as the Service kind.
        if kind == 'Service':
            pos = len(sorted_k8s_reses)

    for k8s_res in k8s_resources:
        sorted_k8s_reses.insert(pos, k8s_res)

    return sorted_k8s_reses


def get_new_deployment_body(
        req, inst, vnfd, deployment_names, operation):
    if operation == v2fields.LcmOperationType.CHANGE_VNFPKG:
        target_k8s_files = req.additionalParams.get(
            'lcm-kubernetes-def-files')
    else:
        target_k8s_files = inst.metadata.get('lcm-kubernetes-def-files')

    new_k8s_resources, namespace = get_k8s_json_file(
        req, inst, target_k8s_files, vnfd, operation)

    new_deploy_reses = []
    for k8s_res in new_k8s_resources:
        if k8s_res.get('kind', '') == 'Deployment' and k8s_res.get(
                'metadata', {}).get('name', '') in deployment_names:
            k8s_res['metadata']['namespace'] = namespace
            new_deploy_reses.append(k8s_res)

    return new_deploy_reses
