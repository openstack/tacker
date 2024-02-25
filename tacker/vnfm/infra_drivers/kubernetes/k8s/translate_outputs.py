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
# Some special parameters are recorded in this variable. These parameters are
# in the form shown in the following list in k8S manifest file, but are not
# recognized by k8S client code, where they are in the form of an underscore
# before the name, for example:
#
#     Parameter in manifest: 'exec',
#     Parameter in k8s-client-code: '_exec',
#
# So we need to recognize these parameters during processing and modify them
# to a form that k8S's client can recognize. If some parameters are appended
# or removed in a later K8S release, please update this list synchronously.
SPECIAL_PARAMETERS_IN_MANIFEST = ['exec', 'not', 'except', 'continue', 'from']


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

    def _gen_k8s_obj_from_name(self, obj_name):
        """Generate kubernetes object

        The function converts the name passed in to the corresponding
        kubernetes object and returns it. By default, client_side_validation
        is True. To skip client-side validation, initialize an empty object,
        set client_side_validation to False, and pass the configuration to
        the function of initializing the kubernetes object through the
        `local_vars_configuration` parameter.
        """
        client_config = client.Configuration.get_default_copy()
        client_config.client_side_validation = False
        config = '(local_vars_configuration=client_config)'
        try:
            k8s_obj = eval('client.{}{}'.format(obj_name, config))
            return k8s_obj
        except (ValueError, SyntaxError, AttributeError) as e:
            msg = '{kind} create failure. Reason={reason}'.format(
                kind=obj_name, reason=e)
            raise exceptions.InitApiFalse(error=msg)

    def _create_k8s_object(self, kind, file_content_dict):
        k8s_obj = self._gen_k8s_obj_from_name('V1' + kind)
        self._init_k8s_obj(k8s_obj, file_content_dict)
        return k8s_obj

    def _get_k8s_obj_from_file_content_dict(self, file_content_dict,
                                            namespace=None):
        k8s_obj = {}
        kind = file_content_dict.get('kind', '')
        try:
            k8s_obj['object'] = self._create_k8s_object(
                kind, file_content_dict)
        except Exception as e:
            if isinstance(e, client.rest.ApiException):
                msg = '{kind} create failure. Reason={reason}'.format(
                    kind=file_content_dict.get('kind', ''), reason=e.body)
            else:
                msg = '{kind} create failure. Reason={reason}'.format(
                    kind=file_content_dict.get('kind', ''), reason=e)
            LOG.error(msg)
            raise exceptions.InitApiFalse(error=msg)

        k8s_obj['namespace'] = namespace
        if k8s_obj['object'].metadata:
            k8s_obj['object'].metadata.namespace = namespace

        return k8s_obj

    def get_k8s_objs_from_yaml(self, artifact_files, vnf_package_path,
                               namespace=None):
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
                k8s_obj = self._get_k8s_obj_from_file_content_dict(
                    file_content_dict, namespace)
                k8s_objs.append(k8s_obj)
        return k8s_objs

    def get_k8s_objs_from_manifest(self, mf_content, namespace):
        mkobj_kind_list = [
            "Pod",
            "Service",
            "PersistentVolumeClaim",
            "Namespace",
            "Node",
            "PersistentVolume",
            "DaemonSet",
            "Deployment",
            "ReplicaSet",
            "StatefulSet",
            "Job"
        ]
        k8s_objs = []
        mf_content_dicts = list(yaml.safe_load_all(mf_content))
        for mf_content_dict in mf_content_dicts:
            kind = mf_content_dict.get('kind', '')
            if kind in mkobj_kind_list:
                k8s_obj = self._get_k8s_obj_from_file_content_dict(
                    file_content_dict=mf_content_dict,
                    namespace=namespace)
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

    def _init_k8s_obj(self, obj, content):
        for key, value in content.items():
            param_value = self._get_lower_case_name(key)
            if param_value in SPECIAL_PARAMETERS_IN_MANIFEST:
                param_value = f'_{param_value}'
            if hasattr(obj, param_value) and \
                    not isinstance(value, dict) and \
                    not isinstance(value, list):
                setattr(obj, param_value, value)
            elif isinstance(value, dict):
                obj_name = obj.openapi_types.get(param_value)
                if obj_name == 'dict(str, str)':
                    setattr(obj, param_value, value)
                else:
                    rely_obj = self._gen_k8s_obj_from_name(obj_name)
                    self._init_k8s_obj(rely_obj, value)
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
                        rely_obj = self._gen_k8s_obj_from_name(rely_obj_name)
                        self._init_k8s_obj(rely_obj, v)
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

    def get_object_meta(self, content):
        v1_object_meta = client.V1ObjectMeta()
        self._init_k8s_obj(v1_object_meta, content)
        return v1_object_meta
