# Copyright (C) 2022 Nippon Telegraph and Telephone Corporation
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

import inspect
import ipaddress
import re
import time

from kubernetes import client
from oslo_log import log as logging

from tacker.sol_refactored.common import config
from tacker.sol_refactored.common import exceptions as sol_ex


LOG = logging.getLogger(__name__)

CONF = config.CONF
CHECK_INTERVAL = 10
VNF_INSTANCE_ID_LABEL = 'tacker_vnf_instance_id'


def convert(name):
    return re.sub('([A-Z])', lambda x: '_' + x.group(1).lower(), name)


class CommonResource:
    # Default API Class
    api_class = client.CoreV1Api

    def __init__(self, k8s_api_client, k8s_res):
        self.k8s_api_client = k8s_api_client
        self.k8s_client = self.api_class(api_client=self.k8s_api_client)
        self.kind = k8s_res['kind']
        self.namespace = k8s_res.get('metadata', {}).get('namespace')
        self.name = k8s_res.get('metadata', {}).get('name')
        self.metadata = k8s_res.get('metadata', {})
        self.body = k8s_res
        self.inst_id = k8s_res.get('metadata', {}).get('labels', {}).get(
            VNF_INSTANCE_ID_LABEL)

    def create(self):
        pass

    def read(self):
        pass

    def delete(self, body):
        pass

    def is_exists(self):
        try:
            info = self.read()
            if info is None:
                # resource not exists
                return False
            # resource exists
            # check if the operation uses helm.
            # if helm is used, self.inst_id is None.
            if self.inst_id is None:
                # it means check is not necessary
                return True

            # check whether other made it by "metadata.labels"
            if info.metadata.labels is None:
                # labels not exists. it means made by other
                return False
            if info.metadata.labels.get(VNF_INSTANCE_ID_LABEL) != self.inst_id:
                # made by other
                return False
            return True
        except sol_ex.K8sResourceNotFound:
            return False

    def is_ready(self):
        return True


class NamespacedResource(CommonResource):

    def create(self):
        method = getattr(self.k8s_client,
            'create_namespaced' + convert(self.__class__.__name__))
        try:
            method(namespace=self.namespace, body=self.body)
        except Exception as ex:
            operation = inspect.currentframe().f_code.co_name
            sol_title = "%s failed" % operation
            raise sol_ex.K8sOperationFailed(sol_title=sol_title,
                                            sol_detail=str(ex))

    def read(self):
        method = getattr(self.k8s_client,
            'read_namespaced' + convert(self.__class__.__name__))
        try:
            return method(namespace=self.namespace, name=self.name)
        except Exception as ex:
            if isinstance(ex, client.ApiException) and ex.status == 404:
                raise sol_ex.K8sResourceNotFound(rsc_name=self.name)
            else:
                operation = inspect.currentframe().f_code.co_name
                sol_title = "%s failed" % operation
                raise sol_ex.K8sOperationFailed(sol_title=sol_title,
                                                sol_detail=str(ex))

    def delete(self, body):
        method = getattr(self.k8s_client,
            'delete_namespaced' + convert(self.__class__.__name__))
        try:
            method(namespace=self.namespace, name=self.name, body=body)
        except Exception as ex:
            operation = inspect.currentframe().f_code.co_name
            sol_title = "%s failed" % operation
            raise sol_ex.K8sOperationFailed(sol_title=sol_title,
                                            sol_detail=str(ex))

    def patch(self):
        method = getattr(self.k8s_client,
            'patch_namespaced' + convert(self.__class__.__name__))
        try:
            method(namespace=self.namespace, name=self.name, body=self.body)
        except Exception as ex:
            operation = inspect.currentframe().f_code.co_name
            sol_title = "%s failed" % operation
            raise sol_ex.K8sOperationFailed(sol_title=sol_title,
                                            sol_detail=str(ex))

    def replace(self):
        method = getattr(self.k8s_client,
            'replace_namespaced' + convert(self.__class__.__name__))
        try:
            method(namespace=self.namespace, name=self.name, body=self.body)
        except Exception as ex:
            operation = inspect.currentframe().f_code.co_name
            sol_title = "%s failed" % operation
            raise sol_ex.K8sOperationFailed(sol_title=sol_title,
                                            sol_detail=str(ex))

    def scale(self, scale_replicas):
        body = {'spec': {'replicas': scale_replicas}}
        method = getattr(self.k8s_client,
            'patch_namespaced' + convert(self.__class__.__name__) + '_scale')
        try:
            method(namespace=self.namespace, name=self.name, body=body)
            self.body['spec']['replicas'] = scale_replicas
        except Exception as ex:
            operation = inspect.currentframe().f_code.co_name
            sol_title = "%s failed" % operation
            raise sol_ex.K8sOperationFailed(sol_title=sol_title,
                                            sol_detail=str(ex))

    def delete_pod(self, pod_name):
        body = client.V1DeleteOptions(propagation_policy='Foreground')
        v1 = client.CoreV1Api(api_client=self.k8s_api_client)
        try:
            v1.delete_namespaced_pod(namespace=self.namespace,
                                     name=pod_name, body=body)
        except Exception as ex:
            operation = inspect.currentframe().f_code.co_name
            sol_title = "%s failed" % operation
            raise sol_ex.K8sOperationFailed(sol_title=sol_title,
                                            sol_detail=str(ex))


class ClusterResource(CommonResource):

    def create(self):
        method = getattr(self.k8s_client,
            'create' + convert(self.__class__.__name__))
        try:
            method(body=self.body)
        except Exception as ex:
            operation = inspect.currentframe().f_code.co_name
            sol_title = "%s failed" % operation
            raise sol_ex.K8sOperationFailed(sol_title=sol_title,
                                            sol_detail=str(ex))

    def read(self):
        method = getattr(self.k8s_client,
            'read' + convert(self.__class__.__name__))
        try:
            return method(name=self.name)
        except Exception as ex:
            if isinstance(ex, client.ApiException) and ex.status == 404:
                raise sol_ex.K8sResourceNotFound(rsc_name=self.name)
            else:
                operation = inspect.currentframe().f_code.co_name
                sol_title = "%s failed" % operation
                raise sol_ex.K8sOperationFailed(sol_title=sol_title,
                                                sol_detail=str(ex))

    def delete(self, body):
        method = getattr(self.k8s_client,
            'delete' + convert(self.__class__.__name__))
        try:
            method(name=self.name, body=body)
        except Exception as ex:
            operation = inspect.currentframe().f_code.co_name
            sol_title = "%s failed" % operation
            raise sol_ex.K8sOperationFailed(sol_title=sol_title,
                                            sol_detail=str(ex))

    def patch(self):
        method = getattr(self.k8s_client,
            'patch' + convert(self.__class__.__name__))
        try:
            method(namespace=self.namespace, name=self.name, body=self.body)
        except Exception as ex:
            operation = inspect.currentframe().f_code.co_name
            sol_title = "%s failed" % operation
            raise sol_ex.K8sOperationFailed(sol_title=sol_title,
                                            sol_detail=str(ex))


class AuthenticationResource(CommonResource):
    def create(self):
        method = getattr(self.k8s_client,
            'create' + convert(self.__class__.__name__))
        try:
            method(body=self.body)
        except Exception as ex:
            operation = inspect.currentframe().f_code.co_name
            sol_title = "%s failed" % operation
            raise sol_ex.K8sOperationFailed(sol_title=sol_title,
                                            sol_detail=str(ex))


class ComponentStatus(CommonResource):
    pass


class ConfigMap(NamespacedResource):
    pass


class Container(CommonResource):
    pass


class LimitRange(NamespacedResource):
    pass


class Namespace(ClusterResource):

    def is_ready(self):
        namespace_info = self.read()
        return (namespace_info.status.phase and
                namespace_info.status.phase == 'Active')


class Node(ClusterResource):

    def is_ready(self):
        node_info = self.read()
        for condition in node_info.status.conditions:
            if condition.type == 'Ready' and condition.status == 'True':
                return True
        return False


class PersistentVolume(ClusterResource):

    def is_ready(self):
        volume_info = self.read()
        return (volume_info.status.phase and
                volume_info.status.phase in ['Available', 'Bound'])


class PersistentVolumeClaim(NamespacedResource):

    def is_ready(self):
        claim_info = self.read()
        return claim_info.status.phase and claim_info.status.phase == 'Bound'


class Pod(NamespacedResource):

    def delete_pod(self, pod_name):
        # Get Pod information before deletition
        pod_info = self.read()
        body = client.V1DeleteOptions(propagation_policy='Foreground')
        self.delete(body=body)

        timeout = CONF.v2_vnfm.kubernetes_vim_rsc_wait_timeout
        max_check_count = (timeout / CHECK_INTERVAL)
        check_count = 0
        while (check_count < max_check_count):
            if not self.is_exists():
                break
            check_count += 1
            time.sleep(CHECK_INTERVAL)
        else:
            raise sol_ex.K8sOperaitionTimeout()

        create_info = client.V1Pod(metadata=self.metadata, spec=pod_info.spec)
        self.k8s_client.create_namespaced_pod(
            namespace=self.namespace, body=create_info)

    def is_ready(self):
        pod_info = self.read()
        return pod_info.status.phase and pod_info.status.phase == 'Running'

    def is_update(self, pods_info, old_pods_names):
        return self.is_ready()


class PodTemplate(NamespacedResource):
    pass


class ResourceQuota(NamespacedResource):
    pass


class Secret(NamespacedResource):
    pass


class Service(NamespacedResource):

    def is_ready(self):

        def _check_is_ip(ip_addr):
            try:
                ipaddress.ip_address(ip_addr)
                return True
            except ValueError:
                return False

        service_info = self.read()
        if (service_info.spec.cluster_ip == "None"
                or _check_is_ip(service_info.spec.cluster_ip)):
            try:
                endpoint_info = self.k8s_client.read_namespaced_endpoints(
                    namespace=self.namespace, name=self.name)
                if endpoint_info:
                    return True
            except Exception as ex:
                sol_title = "Read Endpoint failed"
                raise sol_ex.K8sOperationFailed(sol_title=sol_title,
                                                sol_detail=str(ex))


class ServiceAccount(NamespacedResource):
    pass


class Volume(CommonResource):
    pass


class ControllerRevision(NamespacedResource):
    api_class = client.AppsV1Api

    def delete(self, body):
        body = client.V1DeleteOptions(
            propagation_policy='Background')
        try:
            self.k8s_client.delete_namespaced_controller_revision(
                namespace=self.namespace, name=self.name, body=body)
        except Exception as ex:
            operation = inspect.currentframe().f_code.co_name
            sol_title = "%s failed" % operation
            raise sol_ex.K8sOperationFailed(sol_title=sol_title,
                                            sol_detail=str(ex))


class DaemonSet(NamespacedResource):
    api_class = client.AppsV1Api

    def is_ready(self):
        daemonset_info = self.read()
        return (daemonset_info.status.desired_number_scheduled and
                (daemonset_info.status.desired_number_scheduled ==
                 daemonset_info.status.number_ready))

    def is_update(self, pods_info, old_pods_names):
        daemonset_info = self.read()
        replicas = daemonset_info.status.desired_number_scheduled

        for pod_info in pods_info:
            if (pod_info.status.phase != 'Running' or
                    pod_info.metadata.name in old_pods_names):
                return False

        return len(pods_info) == replicas


class Deployment(NamespacedResource):
    api_class = client.AppsV1Api

    def is_ready(self):
        deployment_info = self.read()
        return (deployment_info.status.replicas and
                (deployment_info.status.replicas ==
                 deployment_info.status.ready_replicas))

    def is_update(self, pods_info, old_pods_names):
        deployment_info = self.read()
        replicas = deployment_info.spec.replicas

        for pod_info in pods_info:
            if (pod_info.status.phase != 'Running' or
                    pod_info.metadata.name in old_pods_names):
                return False

        return len(pods_info) == replicas


class ReplicaSet(NamespacedResource):
    api_class = client.AppsV1Api

    def is_ready(self):
        replicaset_info = self.read()
        return (replicaset_info.status.replicas and
                (replicaset_info.status.replicas ==
                 replicaset_info.status.ready_replicas))

    def is_update(self, pods_info, old_pods_names):
        replicaset_info = self.read()
        replicas = replicaset_info.spec.replicas

        for pod_info in pods_info:
            if (pod_info.status.phase != 'Running' or
                    pod_info.metadata.name in old_pods_names):
                return False

        return len(pods_info) == replicas


class StatefulSet(NamespacedResource):
    api_class = client.AppsV1Api

    def delete(self, body):
        pvcs_for_delete = []
        try:
            resp_read_sfs = self.read()
            sfs_spec = resp_read_sfs.spec
            volume_claim_templates = sfs_spec.volume_claim_templates

            v1 = client.CoreV1Api(api_client=self.k8s_api_client)
            resps_pvc = v1.list_namespaced_persistent_volume_claim(
                namespace=self.namespace)
            pvcs = resps_pvc.items
            for volume_claim_template in volume_claim_templates:
                pvc_template_metadata = volume_claim_template.metadata
                match_pattern = '-'.join(
                    [pvc_template_metadata.name, self.name, ""])

                for pvc in pvcs:
                    pvc_metadata = pvc.metadata
                    pvc_name = pvc_metadata.name
                    match_result = re.match(
                        match_pattern + '[0-9]+$', pvc_name)
                    if match_result is not None:
                        pvcs_for_delete.append(pvc_name)
        except Exception:
            pass

        try:
            self.k8s_client.delete_namespaced_stateful_set(
                namespace=self.namespace, name=self.name, body=body)

            for delete_pvc_name in pvcs_for_delete:
                try:
                    v1 = client.CoreV1Api(api_client=self.k8s_api_client)
                    v1.delete_namespaced_persistent_volume_claim(
                        name=delete_pvc_name, namespace=self.namespace,
                        body=body)
                except Exception as ex:
                    operation = inspect.currentframe().f_code.co_name
                    sol_title = "%s failed" % operation
                    raise sol_ex.K8sOperationFailed(sol_title=sol_title,
                                                    sol_detail=str(ex))
        except Exception as ex:
            operation = inspect.currentframe().f_code.co_name
            sol_title = "%s failed" % operation
            raise sol_ex.K8sOperationFailed(sol_title=sol_title,
                                            sol_detail=str(ex))

    def is_ready(self):
        statefulset_info = self.read()
        replicas = statefulset_info.status.replicas
        if replicas == statefulset_info.status.ready_replicas:
            volume_claim_templates = (
                statefulset_info.spec.volume_claim_templates)
            if volume_claim_templates is None:
                return True
            for i in range(0, statefulset_info.spec.replicas):
                for volume_claim_template in volume_claim_templates:
                    pvc_name = "-".join(
                        [volume_claim_template.metadata.name,
                         self.name, str(i)])
                    v1 = client.CoreV1Api(api_client=self.k8s_api_client)
                    persistent_volume_claim = (
                        v1.read_namespaced_persistent_volume_claim(
                            namespace=self.namespace, name=pvc_name))
                    if persistent_volume_claim.status.phase != 'Bound':
                        return False
            return True
        else:
            return False

    def is_update(self, pods_info, old_pods_names):
        statefulset_info = self.read()
        replicas = statefulset_info.spec.replicas

        for pod_info in pods_info:
            if pod_info.status.phase != 'Running':
                return False

        return len(pods_info) == replicas


class HorizontalPodAutoscaler(NamespacedResource):
    api_class = client.AutoscalingV1Api


class Job(NamespacedResource):
    api_class = client.BatchV1Api

    def is_ready(self):
        job_info = self.read()
        return (job_info.spec.completions and
                job_info.spec.completions == job_info.status.succeeded)


class APIService(ClusterResource):
    api_class = client.ApiregistrationV1Api

    def is_ready(self):
        api_service_info = self.read()
        for condition in api_service_info.status.conditions:
            if condition.type == 'Available':
                if condition.status != 'True':
                    return False
        return True


class TokenReview(AuthenticationResource):
    api_class = client.AuthenticationV1Api


class LocalSubjectAccessReview(AuthenticationResource):
    api_class = client.AuthorizationV1Api

    def create(self):
        try:
            self.k8s_client.create_namespaced_local_subject_access_review(
                namespace=self.namespace, body=self.body)
        except Exception as ex:
            operation = inspect.currentframe().f_code.co_name
            sol_title = "%s failed" % operation
            raise sol_ex.K8sOperationFailed(sol_title=sol_title,
                                            sol_detail=str(ex))


class SelfSubjectAccessReview(AuthenticationResource):
    api_class = client.AuthorizationV1Api


class SelfSubjectRulesReview(AuthenticationResource):
    api_class = client.AuthorizationV1Api


class SubjectAccessReview(AuthenticationResource):
    api_class = client.AuthorizationV1Api


class Lease(NamespacedResource):
    api_class = client.CoordinationV1Api


class NetworkPolicy(NamespacedResource):
    api_class = client.NetworkingV1Api


class ClusterRole(ClusterResource):
    api_class = client.RbacAuthorizationV1Api


class ClusterRoleBinding(ClusterResource):
    api_class = client.RbacAuthorizationV1Api


class Role(NamespacedResource):
    api_class = client.RbacAuthorizationV1Api


class RoleBinding(NamespacedResource):
    api_class = client.RbacAuthorizationV1Api


class PriorityClass(ClusterResource):
    api_class = client.SchedulingV1Api


class StorageClass(ClusterResource):
    api_class = client.StorageV1Api


class VolumeAttachment(ClusterResource):
    api_class = client.StorageV1Api

    def is_ready(self):
        volume_info = self.read()
        return volume_info.status.attached
