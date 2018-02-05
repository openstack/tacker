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

from kubernetes import client
from oslo_config import cfg
from oslo_log import log as logging
import toscaparser.utils.yamlparser

LOG = logging.getLogger(__name__)
CONF = cfg.CONF

YAML_LOADER = toscaparser.utils.yamlparser.load_yaml
NEWLINE_CHARACTER = "\n"
COLON_CHARACTER = ':'
WHITE_SPACE_CHARACTER = ' '
NON_WHITE_SPACE_CHARACTER = ''
HYPHEN_CHARACTER = '-'
DASH_CHARACTER = '_'


class Transformer(object):
    """Transform TOSCA template to Kubernetes resources"""

    def __init__(self, core_v1_api_client, extension_api_client,
                 scaling_api_client):
        self.core_v1_api_client = core_v1_api_client
        self.extension_api_client = extension_api_client
        self.scaling_api_client = scaling_api_client

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
            service_object = self.init_service(tosca_kube_obj=tosca_kube_obj,
                                               kube_obj_name=new_kube_obj_name)
            kubernetes_objects['objects'].append(service_object)

        return kubernetes_objects

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
                self.extension_api_client.create_namespaced_deployment(
                    namespace=namespace,
                    body=k8s_object)
                LOG.debug('Successfully created Deployment %s',
                          k8s_object.metadata.name)
            elif object_type == 'HorizontalPodAutoscaler':
                self.scaling_api_client.\
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
            labels = dict(tosca_kube_obj.labels.items() + update_label.items())
        else:
            labels = update_label

        # Create and configure a spec section
        pod_template = client.V1PodTemplateSpec(
            metadata=client.V1ObjectMeta(labels=labels),
            spec=client.V1PodSpec(containers=containers))

        # Create the specification of deployment
        deployment_spec = client.ExtensionsV1beta1DeploymentSpec(
            template=pod_template)
        metadata = client.V1ObjectMeta(name=deployment_name)

        # Instantiate the deployment object
        deployment = client.ExtensionsV1beta1Deployment(
            api_version="extensions/v1beta1",
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
                api_version="extensions/v1beta1",
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
