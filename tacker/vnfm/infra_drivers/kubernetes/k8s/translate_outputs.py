# All Rights Reserved.
#
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

import os
import re
import toscaparser.utils.yamlparser
from urllib.parse import urlparse
import urllib.request as urllib2
import yaml

from kubernetes import client
from oslo_config import cfg
from oslo_log import log as logging
from tacker.common import exceptions


LOG = logging.getLogger(__name__)
CONF = cfg.CONF

YAML_LOADER = toscaparser.utils.yamlparser.load_yaml
NEWLINE_CHARACTER = "\n"
COLON_CHARACTER = ':'
WHITE_SPACE_CHARACTER = ' '
NON_WHITE_SPACE_CHARACTER = ''
HYPHEN_CHARACTER = '-'
DASH_CHARACTER = '_'
# Due to the dependency of k8s resource creation, according to the design,
# other resources (resources not mentioned in self.RESOURCE_CREATION_SORT)
# will be created after the NetworkPolicy resource. This number is a flag
# to ensure that when multiple resources are to be created, the order of
# other resources is after NetworkPolicy and before Service.
OTHER_RESOURCE_SORT_POSITION = 8


class Transformer(object):
    """Transform TOSCA template to Kubernetes resources"""

    def __init__(self, core_v1_api_client, app_v1_api_client,
                 scaling_api_client, k8s_client_dict):
        # the old param used when creating vnf with TOSCA template
        self.core_v1_api_client = core_v1_api_client
        self.app_v1_api_client = app_v1_api_client
        self.scaling_api_client = scaling_api_client
        # the new param used when instantiating vnf with addtionalParams
        self.k8s_client_dict = k8s_client_dict
        self.RESOURCE_CREATION_ORDER = [
            'StorageClass',
            'PersistentVolume',
            'PriorityClass',
            'Namespace',
            'LimitRange',
            'ResourceQuota',
            'HorizontalPodAutoscaler',
            'NetworkPolicy',
            'Service',
            'Endpoints',
            'PersistentVolumeClaim',
            'ConfigMap',
            'Secret',
            'StatefulSet',
            'Job',
            'Deployment',
            'DaemonSet',
            'Pod'
        ]
        self.method_value = {
            "Pod": 'create_namespaced_pod',
            "Service": 'create_namespaced_service',
            "ConfigMap": 'create_namespaced_config_map',
            "Secret": 'create_namespaced_secret',
            "PersistentVolumeClaim":
                'create_namespaced_persistent_volume_claim',
            "LimitRange": 'create_namespaced_limit_range',
            "PodTemplate": 'create_namespaced_pod_template',
            "Binding": 'create_namespaced_binding',
            "Namespace": 'create_namespace',
            "Node": 'create_node',
            "PersistentVolume": 'create_persistent_volume',
            "ResourceQuota": 'create_namespaced_resource_quota',
            "ServiceAccount": 'create_namespaced_service_account',
            "APIService": 'create_api_service',
            "DaemonSet": 'create_namespaced_daemon_set',
            "Deployment": 'create_namespaced_deployment',
            "ReplicaSet": 'create_namespaced_replica_set',
            "StatefulSet": 'create_namespaced_stateful_set',
            "ControllerRevision": 'create_namespaced_controller_revision',
            "TokenReview": 'create_token_review',
            "LocalSubjectAccessReview": 'create_namespaced_local_'
                                        'subject_access_review',
            "SelfSubjectAccessReview": 'create_self_subject_access_review',
            "SelfSubjectRulesReview": 'create_self_subject_rules_review',
            "SubjectAccessReview": 'create_subject_access_review',
            "HorizontalPodAutoscaler": 'create_namespaced_horizontal_'
                                       'pod_autoscaler',
            "Job": 'create_namespaced_job',
            "Lease": 'create_namespaced_lease',
            "NetworkPolicy": 'create_namespaced_network_policy',
            "ClusterRole": 'create_cluster_role',
            "ClusterRoleBinding": 'create_cluster_role_binding',
            "Role": 'create_namespaced_role',
            "RoleBinding": 'create_namespaced_role_binding',
            "PriorityClass": 'create_priority_class',
            "StorageClass": 'create_storage_class',
            "VolumeAttachment": 'create_volume_attachment',
        }

    def transform(self, tosca_kube_objects):
        """transform function translates from tosca_kube_object to

        kubernetes_object (ConfigMap, Deployment, Service, HPA)
        """

        # kubernetes_objects store all kubernetes objects that are transformed
        # from TOSCA VNF template
        kubernetes_objects = dict()
        for tosca_kube_obj in tosca_kube_objects:
            namespace = tosca_kube_obj.namespace
            kubernetes_objects['namespace'] = namespace
            kubernetes_objects['objects'] = list()
            kube_obj_name = tosca_kube_obj.name
            new_kube_obj_name = self.pre_process_name(kube_obj_name)

            # translate environments to ConfigMap objects
            for container in tosca_kube_obj.containers:
                config_map_object = \
                    self.init_configmap(container_props=container,
                                        kube_obj_name=new_kube_obj_name)
                if config_map_object:
                    kubernetes_objects['objects'].append(config_map_object)

            # translate Deployment object
            deployment_object = \
                self.init_deployment(tosca_kube_obj=tosca_kube_obj,
                                     kube_obj_name=new_kube_obj_name)
            kubernetes_objects['objects'].append(deployment_object)

            # translate to Horizontal Pod Autoscaler object
            hpa_object = self.init_hpa(tosca_kube_obj=tosca_kube_obj,
                                       kube_obj_name=new_kube_obj_name)
            if hpa_object:
                kubernetes_objects['objects'].append(hpa_object)

            # translate to Service object
            service_object = self.init_service(
                tosca_kube_obj=tosca_kube_obj,
                kube_obj_name=new_kube_obj_name)
            kubernetes_objects['objects'].append(service_object)

        return kubernetes_objects

    def _create_k8s_object(self, kind, file_content_dict):
        # must_param referring K8s official object page
        # *e.g:https://github.com/kubernetes-client/python/blob/master/kubernetes/docs/V1Service.md
        # initiating k8s object, you need to
        # give the must param an empty value.
        must_param = {
            'RuntimeRawExtension': '(raw="")',
            'V1LocalSubjectAccessReview': '(spec="")',
            'V1HTTPGetAction': '(port="")',
            'V1DeploymentSpec': '(selector="", template="")',
            'V1PodSpec': '(containers="")',
            'V1ConfigMapKeySelector': '(key="")',
            'V1Container': '(name="")',
            'V1EnvVar': '(name="")',
            'V1SecretKeySelector': '(key="")',
            'V1ContainerPort': '(container_port="")',
            'V1VolumeMount': '(mount_path="", name="")',
            'V1PodCondition': '(status="", type="")',
            'V1ContainerStatus': '('
                                 'image="", image_id="", '
                                 'name="", ready="", '
                                 'restart_count="")',
            'V1ServicePort': '(port="")',
            'V1TypedLocalObjectReference': '(kind="", name="")',
            'V1LabelSelectorRequirement': '(key="", operator="")',
            'V1PersistentVolumeClaimCondition': '(status="", type="")',
            'V1AWSElasticBlockStoreVolumeSource': '(volume_id="")',
            'V1AzureDiskVolumeSource': '(disk_name="", disk_uri="")',
            'V1AzureFileVolumeSource': '(secret_name="", share_name="")',
            'V1CephFSVolumeSource': '(monitors=[])',
            'V1CinderVolumeSource': '(volume_id="")',
            'V1KeyToPath': '(key="", path="")',
            'V1CSIVolumeSource': '(driver="")',
            'V1DownwardAPIVolumeFile': '(path="")',
            'V1ObjectFieldSelector': '(field_path="")',
            'V1ResourceFieldSelector': '(resource="")',
            'V1FlexVolumeSource': '(driver="")',
            'V1GCEPersistentDiskVolumeSource': '(pd_name="")',
            'V1GitRepoVolumeSource': '(repository="")',
            'V1GlusterfsVolumeSource': '(endpoints="", path="")',
            'V1HostPathVolumeSource': '(path="")',
            'V1ISCSIVolumeSource': '(iqn="", lun=0, target_portal="")',
            'V1Volume': '(name="")',
            'V1NFSVolumeSource': '(path="", server="")',
            'V1PersistentVolumeClaimVolumeSource': '(claim_name="")',
            'V1PhotonPersistentDiskVolumeSource': '(pd_id="")',
            'V1PortworxVolumeSource': '(volume_id="")',
            'V1ProjectedVolumeSource': '(sources=[])',
            'V1ServiceAccountTokenProjection': '(path="")',
            'V1QuobyteVolumeSource': '(registry="", volume="")',
            'V1RBDVolumeSource': '(image="", monitors=[])',
            'V1ScaleIOVolumeSource': '('
                                     'gateway="", secret_ref="", '
                                     'system="")',
            'V1VsphereVirtualDiskVolumeSource': '(volume_path="")',
            'V1LimitRangeSpec': '(limits=[])',
            'V1Binding': '(target="")',
            'V1ComponentCondition': '(status="", type="")',
            'V1NamespaceCondition': '(status="", type="")',
            'V1ConfigMapNodeConfigSource': '(kubelet_config_key="", '
                                           'name="", namespace="")',
            'V1Taint': '(effect="", key="")',
            'V1NodeAddress': '(address="", type="")',
            'V1NodeCondition': '(status="", type="")',
            'V1DaemonEndpoint': '(port=0)',
            'V1ContainerImage': '(names=[])',
            'V1NodeSystemInfo': '(architecture="", boot_id="", '
                                'container_runtime_version="",'
                                'kernel_version="", '
                                'kube_proxy_version="", '
                                'kubelet_version="",'
                                'machine_id="", operating_system="", '
                                'os_image="", system_uuid="")',
            'V1AttachedVolume': '(device_path="", name="")',
            'V1ScopedResourceSelectorRequirement':
                '(operator="", scope_name="")',
            'V1APIServiceSpec': '(group_priority_minimum=0, '
                                'service="", version_priority=0)',
            'V1APIServiceCondition': '(status="", type="")',
            'V1DaemonSetSpec': '(selector="", template="")',
            'V1ReplicaSetSpec': '(selector="")',
            'V1StatefulSetSpec': '(selector="", '
                                 'service_name="", template="")',
            'V1StatefulSetCondition': '(status="", type="")',
            'V1StatefulSetStatus': '(replicas="")',
            'V1ControllerRevision': '(revision=0)',
            'V1TokenReview': '(spec="")',
            'V1SubjectAccessReviewStatus': '(allowed=True)',
            'V1SelfSubjectAccessReview': '(spec="")',
            'V1SelfSubjectRulesReview': '(spec="")',
            'V1SubjectRulesReviewStatus': '(incomplete=True, '
                                          'non_resource_rules=[], '
                                          'resource_rules=[])',
            'V1NonResourceRule': '(verbs=[])',
            'V1SubjectAccessReview': '(spec="")',
            'V1HorizontalPodAutoscalerSpec':
                '(max_replicas=0, scale_target_ref="")',
            'V1CrossVersionObjectReference': '(kind="", name="")',
            'V1HorizontalPodAutoscalerStatus':
                '(current_replicas=0, desired_replicas=0)',
            'V1JobSpec': '(template="")',
            'V1NetworkPolicySpec': '(pod_selector="")',
            'V1PolicyRule': '(verbs=[])',
            'V1ClusterRoleBinding': '(role_ref="")',
            'V1RoleRef': '(api_group="", kind="", name="")',
            'V1Subject': '(kind="", name="")',
            'V1RoleBinding': '(role_ref="")',
            'V1PriorityClass': '(value=0)',
            'V1StorageClass': '(provisioner="")',
            'V1TopologySelectorLabelRequirement': '(key="", values=[])',
            'V1VolumeAttachment': '(spec="")',
            'V1VolumeAttachmentSpec':
                '(attacher="", node_name="", source="")',
            'V1VolumeAttachmentStatus': '(attached=True)',
        }
        whole_kind = 'V1' + kind
        if whole_kind in must_param.keys():
            k8s_obj = eval('client.V1' + kind + must_param.get(whole_kind))
        else:
            k8s_obj = eval('client.V1' + kind + '()')
        self._init_k8s_obj(k8s_obj, file_content_dict, must_param)
        return k8s_obj

    def get_k8s_objs_from_yaml(self, artifact_files, vnf_package_path):
        k8s_objs = []
        for artifact_file in artifact_files:
            if ((urlparse(artifact_file).scheme == 'file') or
                    (bool(urlparse(artifact_file).scheme) and
                     bool(urlparse(artifact_file).netloc))):
                file_content = urllib2.urlopen(artifact_file).read()
            else:
                artifact_file_path = os.path.join(
                    vnf_package_path, artifact_file)
                with open(artifact_file_path, 'r') as f:
                    file_content = f.read()
            file_content_dicts = list(yaml.safe_load_all(file_content))
            for file_content_dict in file_content_dicts:
                k8s_obj = {}
                kind = file_content_dict.get('kind', '')
                try:
                    k8s_obj['object'] = self._create_k8s_object(
                        kind, file_content_dict)
                except Exception as e:
                    if isinstance(e, client.rest.ApiException):
                        msg = \
                            _('{kind} create failure. Reason={reason}'.format(
                                kind=file_content_dict.get('kind', ''),
                                reason=e.body))
                    else:
                        msg = \
                            _('{kind} create failure. Reason={reason}'.format(
                                kind=file_content_dict.get('kind', ''),
                                reason=e))
                    LOG.error(msg)
                    raise exceptions.InitApiFalse(error=msg)
                if not file_content_dict.get('metadata', ''):
                    k8s_obj['namespace'] = ''
                elif file_content_dict.get('metadata', '').\
                        get('namespace', ''):
                    k8s_obj['namespace'] = \
                        file_content_dict.get('metadata', '').get(
                            'namespace', '')
                else:
                    k8s_obj['namespace'] = ''
                k8s_objs.append(k8s_obj)
        return k8s_objs

    def _select_k8s_client_and_api(
            self, kind, namespace, api_version, body):
        k8s_client_obj = self.k8s_client_dict[api_version]
        if 'namespaced' in self.method_value[kind]:
            response = getattr(k8s_client_obj, self.method_value.get(kind))(
                namespace=namespace, body=body
            )
        else:
            response = getattr(k8s_client_obj, self.method_value.get(kind))(
                body=body
            )
        return response

    def deploy(self, kubernetes_objects):
        """Deploy Kubernetes objects on Kubernetes VIM and return

        a list name of services
        """
        deployment_names = list()
        namespace = kubernetes_objects.get('namespace')
        k8s_objects = kubernetes_objects.get('objects')

        for k8s_object in k8s_objects:
            object_type = k8s_object.kind

            if object_type == 'ConfigMap':
                self.core_v1_api_client.create_namespaced_config_map(
                    namespace=namespace,
                    body=k8s_object)
                LOG.debug('Successfully created ConfigMap %s',
                          k8s_object.metadata.name)
            elif object_type == 'Deployment':
                self.app_v1_api_client.create_namespaced_deployment(
                    namespace=namespace,
                    body=k8s_object)
                LOG.debug('Successfully created Deployment %s',
                          k8s_object.metadata.name)
            elif object_type == 'HorizontalPodAutoscaler':
                self.scaling_api_client. \
                    create_namespaced_horizontal_pod_autoscaler(
                        namespace=namespace,
                        body=k8s_object)
                LOG.debug('Successfully created Horizontal Pod Autoscaler %s',
                          k8s_object.metadata.name)
            elif object_type == 'Service':
                self.core_v1_api_client.create_namespaced_service(
                    namespace=namespace,
                    body=k8s_object)
                LOG.debug('Successfully created Service %s',
                          k8s_object.metadata.name)
                deployment_names.append(namespace)
                deployment_names.append(k8s_object.metadata.name)

        # return a string that contains all deployment namespace and names
        # for tracking resources pattern:
        # namespace1,deployment1,namespace2,deployment2,namespace3,deployment3
        return ",".join(deployment_names)

    def deploy_k8s(self, kubernetes_objects):
        """Deploy kubernetes

        Deploy Kubernetes objects on Kubernetes VIM and
        return a list name of services
        """
        kubernetes_objects = self._sort_k8s_obj(kubernetes_objects)
        new_k8s_objs = list()
        for kubernetes_object in kubernetes_objects:
            namespace = kubernetes_object.get('namespace', '')
            kind = kubernetes_object.get('object', '').kind
            api_version = kubernetes_object.get('object', '').api_version
            body = kubernetes_object.get('object', '')
            if kubernetes_object.get('object', '').metadata:
                name = kubernetes_object.get('object', '').metadata.name
            else:
                name = ''
            try:
                LOG.debug("{kind} begin create.".format(kind=kind))
                self._select_k8s_client_and_api(
                    kind, namespace, api_version, body)
                kubernetes_object['status'] = 'Creating'
            except Exception as e:
                if isinstance(e, client.rest.ApiException):
                    kubernetes_object['status'] = 'creating_failed'
                    msg = '''The request to create a resource failed.
                    namespace: {namespace}, name: {name},kind: {kind},
                    Reason: {exception}'''.format(
                        namespace=namespace, name=name, kind=kind,
                        exception=e.body
                    )
                else:
                    kubernetes_object['status'] = 'creating_failed'
                    msg = '''The request to create a resource failed.
                    namespace: {namespace}, name: {name},kind: {kind},
                    Reason: {exception}'''.format(
                        namespace=namespace, name=name, kind=kind,
                        exception=e
                    )
                LOG.error(msg)
                raise exceptions.CreateApiFalse(error=msg)
            new_k8s_objs.append(kubernetes_object)
        return new_k8s_objs

    def _get_lower_case_name(self, name):
        name = name.strip()
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()

    def _init_k8s_obj(self, obj, content, must_param):
        for key, value in content.items():
            param_value = self._get_lower_case_name(key)
            if hasattr(obj, param_value) and \
                    not isinstance(value, dict) and \
                    not isinstance(value, list):
                setattr(obj, param_value, value)
            elif isinstance(value, dict):
                obj_name = obj.openapi_types.get(param_value)
                if obj_name == 'dict(str, str)':
                    setattr(obj, param_value, value)
                else:
                    if obj_name in must_param.keys():
                        rely_obj = eval('client.' + obj_name +
                                       must_param.get(obj_name))
                    else:
                        rely_obj = eval('client.' + obj_name + '()')
                    self._init_k8s_obj(rely_obj, value, must_param)
                    setattr(obj, param_value, rely_obj)
            elif isinstance(value, list):
                obj_name = obj.openapi_types.get(param_value)
                if obj_name == 'list[str]':
                    setattr(obj, param_value, value)
                else:
                    rely_objs = []
                    rely_obj_name = \
                        re.findall(r".*\[([^\[\]]*)\].*", obj_name)[0]
                    for v in value:
                        if rely_obj_name in must_param.keys():
                            rely_obj = eval('client.' + rely_obj_name +
                                           must_param.get(rely_obj_name))
                        else:
                            rely_obj = \
                                eval('client.' + rely_obj_name + '()')
                        self._init_k8s_obj(rely_obj, v, must_param)
                        rely_objs.append(rely_obj)
                    setattr(obj, param_value, rely_objs)

    def _sort_k8s_obj(self, k8s_objs):
        pos = 0
        objs = k8s_objs
        sorted_k8s_objs = list()
        for sort_index, kind in enumerate(self.RESOURCE_CREATION_ORDER):
            for obj_index, obj in enumerate(objs):
                if obj["object"].kind == kind:
                    sorted_k8s_objs.append(objs.pop(obj_index))
            if sort_index == OTHER_RESOURCE_SORT_POSITION:
                pos = len(sorted_k8s_objs)
        for obj in objs:
            sorted_k8s_objs.insert(pos, obj)

        return sorted_k8s_objs

    # config_labels configures label
    def config_labels(self, deployment_name=None, scaling_name=None):
        label = dict()
        if deployment_name:
            label.update({"selector": deployment_name})
        if scaling_name:
            label.update({"scaling_name": scaling_name})
        return label

    # Init resource requirement for container
    def init_resource_requirements(self, container):
        limits = dict()
        requests = dict()
        if container.num_cpus:
            limits.update({'cpu': container.num_cpus})
            requests.update({'cpu': container.num_cpus})
        if container.mem_size:
            limits.update({'memory': container.mem_size})
            requests.update({'memory': container.mem_size})
        return client.V1ResourceRequirements(limits=limits,
                                             requests=requests)

    def init_envs(self, container_props, name):
        config = container_props.config
        config_dict = self.pre_process_config(config)
        configmap_name = name

        list_envs = []
        for key in config_dict:
            config_map_ref = client.V1ConfigMapKeySelector(
                key=key,
                name=configmap_name)
            env_var = client.V1EnvVarSource(
                config_map_key_ref=config_map_ref)
            env_object = client.V1EnvVar(
                name=key,
                value_from=env_var)
            list_envs.append(env_object)
        return list_envs

    # Init container object
    def init_containers(self, container_props, limit_resource, name):
        list_env_var = self.init_envs(container_props, name)
        container_name = self.pre_process_name(container_props.name)
        list_container_port = list()
        if container_props.ports:
            for container_port in container_props.ports:
                port = int(container_port)
                cport = client.V1ContainerPort(container_port=port)
                list_container_port.append(cport)
        container = client.V1Container(
            name=container_name,
            image=container_props.image,
            ports=list_container_port,
            resources=limit_resource,
            command=container_props.command,
            args=container_props.args,
            env=list_env_var,
            image_pull_policy="IfNotPresent")
        return container

    # init_deployment initializes Kubernetes Pod object
    def init_deployment(self, tosca_kube_obj, kube_obj_name):
        """Instantiate the deployment object"""

        deployment_name = kube_obj_name
        # Create a list of container, which made a Pod
        containers = list()
        for container_prop in tosca_kube_obj.containers:
            limit_resource = self.init_resource_requirements(container_prop)
            container = self.init_containers(
                container_props=container_prop,
                limit_resource=limit_resource,
                name=deployment_name)
            containers.append(container)

        # Make a label with pattern {"selector": "deployment_name"}
        if tosca_kube_obj.scaling_object:
            scaling_name = tosca_kube_obj.scaling_object.scaling_name
            update_label = self.config_labels(deployment_name=deployment_name,
                                              scaling_name=scaling_name)
        else:
            update_label = self.config_labels(deployment_name=deployment_name)
        if tosca_kube_obj.labels:
            if 'selector' in update_label:
                del update_label['selector']
            update_label.update(tosca_kube_obj.labels)
        labels = update_label

        # Create and configure a spec section
        pod_template = client.V1PodTemplateSpec(
            metadata=client.V1ObjectMeta(
                labels=labels, annotations=tosca_kube_obj.annotations),
            spec=client.V1PodSpec(containers=containers))
        # Create the specification of deployment
        label_selector = client.V1LabelSelector(match_labels=labels)
        deployment_spec = client.V1DeploymentSpec(
            template=pod_template, selector=label_selector)
        metadata = client.V1ObjectMeta(name=deployment_name, labels=labels)

        # Instantiate the deployment object
        deployment = client.V1Deployment(
            api_version="apps/v1",
            kind="Deployment",
            metadata=metadata,
            spec=deployment_spec)
        return deployment

    # init_hpa initializes Kubernetes Horizon Pod Auto-scaling object
    def init_hpa(self, tosca_kube_obj, kube_obj_name):
        scaling_props = tosca_kube_obj.scaling_object
        hpa = None
        if scaling_props:
            min_replicas = scaling_props.min_replicas
            max_replicas = scaling_props.max_replicas
            cpu_util = scaling_props.target_cpu_utilization_percentage
            deployment_name = kube_obj_name

            # Create target Deployment object
            target = client.V1CrossVersionObjectReference(
                api_version="apps/v1",
                kind="Deployment",
                name=deployment_name)
            # Create the specification of horizon pod auto-scaling
            hpa_spec = client.V1HorizontalPodAutoscalerSpec(
                min_replicas=min_replicas,
                max_replicas=max_replicas,
                target_cpu_utilization_percentage=cpu_util,
                scale_target_ref=target)
            metadata = client.V1ObjectMeta(name=deployment_name)
            # Create Horizon Pod Auto-Scaling
            hpa = client.V1HorizontalPodAutoscaler(
                api_version="autoscaling/v1",
                kind="HorizontalPodAutoscaler",
                spec=hpa_spec,
                metadata=metadata)
        return hpa

    # init_service initializes Kubernetes service object
    def init_service(self, tosca_kube_obj, kube_obj_name):
        list_service_port = list()
        service_label = tosca_kube_obj.labels
        for port in tosca_kube_obj.mapping_ports:
            if COLON_CHARACTER in port:
                ports = port.split(COLON_CHARACTER)
                published_port = int(ports[0])
                target_port = int(ports[1])
            else:
                target_port = published_port = int(port)
            service_port = client.V1ServicePort(
                name=str(published_port),
                port=published_port,
                target_port=target_port)
            list_service_port.append(service_port)

        deployment_name = kube_obj_name
        selector_by_name = self.config_labels(deployment_name)
        if tosca_kube_obj.labels:
            selectors = tosca_kube_obj.labels.copy()
        else:
            selectors = selector_by_name
        if tosca_kube_obj.mgmt_connection_point:
            service_label['management_connection'] = 'True'
        if tosca_kube_obj.network_name:
            service_label['network_name'] = tosca_kube_obj.network_name
        service_label['vdu_name'] = tosca_kube_obj.name

        metadata = client.V1ObjectMeta(name=deployment_name,
                                       labels=service_label)
        if tosca_kube_obj.service_type:
            service_type = tosca_kube_obj.service_type
        else:
            service_type = None
        service_spec = client.V1ServiceSpec(
            selector=selectors,
            ports=list_service_port,
            type=service_type)

        service = client.V1Service(
            api_version="v1",
            kind="Service",
            spec=service_spec,
            metadata=metadata)
        return service

    # init_config_map initializes Kubernetes ConfigMap object
    def init_configmap(self, container_props, kube_obj_name):
        config_map = None
        if container_props.config:
            configmap_name = kube_obj_name
            metadata = client.V1ObjectMeta(name=configmap_name)
            config_dict = self.pre_process_config(container_props.config)
            config_map = client.V1ConfigMap(
                api_version="v1",
                kind="ConfigMap",
                data=config_dict,
                metadata=metadata)
        return config_map

    def pre_process_name(self, name):
        # replace '_' by '-' to meet Kubernetes' requirement
        new_name = name.replace(DASH_CHARACTER, HYPHEN_CHARACTER).lower()
        return new_name

    def pre_process_config(self, config):
        # Split by separating lines
        config_dict = {}
        if config:
            configs = config.split(NEWLINE_CHARACTER)
            for config_item in configs:
                # Ignore if config_item is null
                if config_item:
                    # Strip all types of white-space characters
                    config_item = config_item.replace(
                        WHITE_SPACE_CHARACTER,
                        NON_WHITE_SPACE_CHARACTER)
                    config_prop = config_item.split(COLON_CHARACTER)
                    config_dict[config_prop[0]] = config_prop[1]
            # config_dict has the pattern such as
            # {'param1': 'key1', 'param0': 'key0'}
        return config_dict
