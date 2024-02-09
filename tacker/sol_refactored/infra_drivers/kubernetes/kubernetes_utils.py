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

import os
import re
import tempfile
from urllib.parse import urlparse
import urllib.request as urllib2

from kubernetes import client
from oslo_log import log as logging
import yaml

from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.common import oidc_utils
from tacker.sol_refactored.infra_drivers.kubernetes import helm_utils
from tacker.sol_refactored.infra_drivers.kubernetes import kubernetes_resource


LOG = logging.getLogger(__name__)

SUPPORTED_NAMESPACE_KIND = {
    "Binding",
    "ConfigMap",
    "ControllerRevision",
    "DaemonSet",
    "Deployment",
    "HorizontalPodAutoscaler",
    "Job",
    "Lease",
    "LimitRange",
    "LocalSubjectAccessReview",
    "NetworkPolicy",
    "PersistentVolumeClaim",
    "Pod",
    "PodTemplate",
    "ReplicaSet",
    "ResourceQuota",
    "Role"
    "RoleBinding",
    "Secret",
    "Service",
    "ServiceAccount",
    "StatefulSet",
}
SCALABLE_KIND = {"Deployment", "ReplicaSet", "StatefulSet"}
TARGET_KIND = {"Pod", "Deployment", "DaemonSet", "StatefulSet", "ReplicaSet"}
UNLABELED_KIND = {"SubjectAccessReview", "LocalSubjectAccessReview",
                  "SelfSubjectAccessReview", "SelfSubjectRulesReview",
                  "TokenReview"}


def get_k8s_reses_from_json_files(target_k8s_files, vnfd, k8s_api_client,
        namespace, inst_id):

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

    for k8s_res in k8s_resources:
        if not k8s_res.get('kind'):
            raise sol_ex.K8sInvalidManifestFound()
        if k8s_res['kind'] in SUPPORTED_NAMESPACE_KIND:
            k8s_res.setdefault('metadata', {})
            if namespace is None:
                k8s_res['metadata'].setdefault('namespace', 'default')
            else:
                k8s_res['metadata']['namespace'] = namespace
        # Set label to identify the VnfInstance
        if k8s_res['kind'] not in UNLABELED_KIND:
            k8s_res.setdefault('metadata', {})
            k8s_res['metadata'].setdefault('labels', {})
            k8s_res['metadata']['labels'][
                kubernetes_resource.VNF_INSTANCE_ID_LABEL] = inst_id

    # check namespace
    if namespace is None:
        namespaces = {k8s_res['metadata']['namespace']
                      for k8s_res in k8s_resources
                      if k8s_res['kind'] in SUPPORTED_NAMESPACE_KIND}
        if len(namespaces) > 1:
            raise sol_ex.NamespaceNotUniform()
        namespace = namespaces.pop() if namespaces else 'default'

    k8s_reses = []
    for k8s_res in k8s_resources:
        try:
            cls = getattr(kubernetes_resource, k8s_res['kind'])
            k8s_reses.append(cls(k8s_api_client, k8s_res))
        except AttributeError:
            LOG.info("Not support kind %s. ignored.", k8s_res['kind'])

    return k8s_reses, namespace


def list_namespaced_pods(k8s_api_client, namespace):
    k8s_client = client.CoreV1Api(api_client=k8s_api_client)
    return k8s_client.list_namespaced_pod(namespace=namespace).items


class AuthContextManager:
    def __init__(self, vim_info):
        self.vim_info = vim_info
        self.ca_cert_file = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if self.ca_cert_file:
            os.remove(self.ca_cert_file)

    def _create_ca_cert_file(self, ca_cert_str):
        if self.ca_cert_file:
            return
        file_descriptor, self.ca_cert_file = tempfile.mkstemp()
        ca_cert = re.sub(r'\s', '\n', ca_cert_str)
        ca_cert = re.sub(r'BEGIN\nCERT', r'BEGIN CERT', ca_cert)
        ca_cert = re.sub(r'END\nCERT', r'END CERT', ca_cert)
        # write ca cert file
        os.write(file_descriptor, ca_cert.encode())
        os.close(file_descriptor)

    def init_k8s_api_client(self):
        k8s_config = client.Configuration()
        k8s_config.host = self.vim_info.interfaceInfo['endpoint']

        if 'ssl_ca_cert' in self.vim_info.interfaceInfo:
            self._create_ca_cert_file(
                self.vim_info.interfaceInfo['ssl_ca_cert'])

        if 'oidc_token_url' in self.vim_info.accessInfo:
            # Obtain a openid token from openid provider
            id_token = oidc_utils.get_id_token_with_password_grant(
                self.vim_info.accessInfo.get('oidc_token_url'),
                self.vim_info.accessInfo.get('username'),
                self.vim_info.accessInfo.get('password'),
                self.vim_info.accessInfo.get('client_id'),
                client_secret=self.vim_info.accessInfo.get('client_secret'),
                ssl_ca_cert=self.ca_cert_file
            )
            k8s_config.api_key_prefix['authorization'] = 'Bearer'
            k8s_config.api_key['authorization'] = id_token
        else:
            if ('username' in self.vim_info.accessInfo and
                    self.vim_info.accessInfo.get('password') is not None):
                k8s_config.username = self.vim_info.accessInfo['username']
                k8s_config.password = self.vim_info.accessInfo['password']
                basic_token = k8s_config.get_basic_auth_token()
                k8s_config.api_key['authorization'] = basic_token

            if 'bearer_token' in self.vim_info.accessInfo:
                k8s_config.api_key_prefix['authorization'] = 'Bearer'
                k8s_config.api_key['authorization'] = self.vim_info.accessInfo[
                    'bearer_token']

        if self.ca_cert_file:
            k8s_config.ssl_ca_cert = self.ca_cert_file
            k8s_config.verify_ssl = True
        else:
            k8s_config.verify_ssl = False

        return client.api_client.ApiClient(configuration=k8s_config)

    def _get_helm_auth_params(self):
        kube_apiserver = self.vim_info.interfaceInfo['endpoint']
        kube_token = self.vim_info.accessInfo['bearer_token']
        self._create_ca_cert_file(
            self.vim_info.interfaceInfo['ssl_ca_cert'])
        helm_auth_params = ["--kube-apiserver", kube_apiserver,
                            "--kube-ca-file", self.ca_cert_file,
                            "--kube-token", kube_token]

        return helm_auth_params

    def init_helm_client(self):
        return helm_utils.HelmClient(self._get_helm_auth_params())
