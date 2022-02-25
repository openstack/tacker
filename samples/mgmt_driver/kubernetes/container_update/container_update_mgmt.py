# Copyright (C) 2022 FUJITSU
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
import os
import re
import time
import urllib.request as urllib2
import yaml

from oslo_log import log as logging
from oslo_utils import encodeutils
from tacker.common.container import kubernetes_utils
from tacker.common import exceptions
from tacker.common import log
from tacker import objects
from tacker.vnflcm import utils as vnflcm_utils
from tacker.vnfm.infra_drivers.kubernetes.k8s import translate_outputs
from tacker.vnfm.infra_drivers.kubernetes.kubernetes_driver import Kubernetes
from tacker.vnfm.mgmt_drivers import vnflcm_abstract_driver
from toscaparser import tosca_template
from urllib.parse import urlparse

LOG = logging.getLogger(__name__)


class ContainerUpdateMgmtDriver(vnflcm_abstract_driver.
                                VnflcmMgmtAbstractDriver):

    def __init__(self):
        pass

    def get_type(self):
        return "mgmt-container-update"

    def get_name(self):
        return "mgmt-container-update"

    def get_description(self):
        return 'Tacker Container Update VNF Mgmt Driver'

    def modify_information_start(self, context, vnf_instance,
                                 modify_vnf_request=None, **kwargs):
        pass

    def _get_kind_and_name(self, file, vnf_package_path):
        # kind_and_names ----> configmap_secrets list or resources list
        kind_and_names = []
        # Read the contents of the manifest file and get the name and kind
        if ((urlparse(file).scheme == 'file') or
                (bool(urlparse(file).scheme) and
                 bool(urlparse(file).netloc))):
            file_content = urllib2.urlopen(file).read()
        else:
            manifest_file = os.path.join(vnf_package_path, file)
            with open(manifest_file, 'r', encoding='utf-8') as f:
                file_content = f.read()
        file_contents = yaml.safe_load_all(file_content)
        for file_content in file_contents:
            kind = file_content.get('kind', '')
            name = file_content.get('metadata', {}).get('name', '')
            kind_and_names.append({'kind': kind, 'name': name})
        return kind_and_names

    def _initialize_k8s_client(self, auth_cred):
        k8s_clients = (kubernetes_utils.KubernetesHTTPAPI().
                       get_k8s_client_dict(auth_cred))
        return k8s_clients

    def _get_k8s_objs(self, target_k8s_files, vnf_package_path, namespace,
                      k8s_clients):
        transformer = translate_outputs.Transformer(
            None, None, None, k8s_clients)
        k8s_objs = transformer.get_k8s_objs_from_yaml(
            target_k8s_files, vnf_package_path, namespace)
        return k8s_objs

    def _modify_container_img(self, old_containers, new_containers):
        for old_container in old_containers:
            for new_container in new_containers:
                if (old_container.name == new_container.name and
                        old_container.image != new_container.image):
                    # Replace the old image with the new image
                    old_container.image = new_container.image
                    break

    def _replace_api(self, k8s_clients, namespace, k8s_obj):
        # get api
        name = k8s_obj['object'].metadata.name
        kind = k8s_obj['object'].kind
        api_version = k8s_obj['object'].api_version
        body = k8s_obj['object']

        def convert(name):
            name_with_underscores = re.sub(
                '(.)([A-Z][a-z]+)', r'\1_\2', name)
            return re.sub('([a-z0-9])([A-Z])', r'\1_\2',
                          name_with_underscores).lower()

        snake_case_kind = convert(kind)
        try:
            replace_api = eval(f'k8s_clients["{api_version}"].'
                               f'replace_namespaced_{snake_case_kind}')
            response = replace_api(name=name, namespace=namespace,
                                   body=body)
        except Exception as exp:
            raise exceptions.MgmtDriverOtherError(
                error_message=encodeutils.exception_to_unicode(exp))

        return response

    def _replace_wait_k8s(self, kube_driver, k8s_pod_objs,
                          core_v1_api_client, vnf_instance):
        try:
            time.sleep(kube_driver.STACK_RETRY_WAIT)
            status = 'Pending'
            stack_retries = kube_driver.STACK_RETRIES

            while status == 'Pending' and stack_retries > 0:
                pods_information = []
                for k8s_pod_obj in k8s_pod_objs:
                    kind = k8s_pod_obj['object'].kind
                    namespace = k8s_pod_obj.get('namespace')
                    if k8s_pod_obj['object'].metadata:
                        name = k8s_pod_obj['object'].metadata.name
                    else:
                        name = ''

                    response = core_v1_api_client.list_namespaced_pod(
                        namespace=namespace)
                    for pod in response.items:
                        match_result = kube_driver.is_match_pod_naming_rule(
                            kind, name, pod.metadata.name)
                        if match_result:
                            pods_information.append(pod)
                status = kube_driver.get_pod_status(pods_information)
                if status == 'Unknown':
                    wait = (kube_driver.STACK_RETRIES *
                            kube_driver.STACK_RETRY_WAIT)
                    error_reason = (
                        f"Resource creation is not completed within"
                        f" {wait} seconds as creation of CNF "
                        f"{vnf_instance.id} is not completed")
                    raise exceptions.MgmtDriverOtherError(
                        error_message=error_reason)
                if status == 'Pending':
                    stack_retries = stack_retries - 1
                    time.sleep(kube_driver.STACK_RETRY_WAIT)
            if stack_retries == 0 and status != 'Running':
                LOG.error('It is time out, When modify cnf,'
                          'waiting for resource creation.')
                wait = (kube_driver.STACK_RETRIES *
                        kube_driver.STACK_RETRY_WAIT)
                error_reason = (f"Resource creation is not completed within"
                                f" {wait} seconds as creation of CNF "
                                f"{vnf_instance.id} is not completed")
                raise exceptions.MgmtDriverOtherError(
                    error_message=error_reason)
            return k8s_pod_objs
        except Exception as exp:
            raise exceptions.MgmtDriverOtherError(
                error_message=encodeutils.exception_to_unicode(exp))

    @log.log
    def modify_information_end(self, context, vnf_instance,
                               modify_vnf_request=None, **kwargs):
        kube_driver = Kubernetes()
        # get old_vnf_package_path
        old_vnf_package_path = kwargs['old_vnf_package_path']

        # get configmap_secret_paths
        configmap_secret_paths = kwargs['configmap_secret_paths']
        # Get the path of the VNF Package according to vnf_instance.vnfd_id
        new_vnf_package_path = vnflcm_utils.get_vnf_package_path(
            context, vnf_instance.vnfd_id)

        # Get the input parameters of instantiate
        inst_vnf_info = vnf_instance.instantiated_vnf_info

        # Make a deep copy of inst_vnf_info
        new_inst_vnf_info = copy.deepcopy(inst_vnf_info)

        # Get vim_connection_info from vnf_instance
        vim_info = vnflcm_utils.get_vim(context,
                                        vnf_instance.vim_connection_info)
        vim_connection_info = objects.VimConnectionInfo.obj_from_primitive(
            vim_info, context)
        for configmap_secret_path in configmap_secret_paths:
            # Read the contents of the manifest file and get name and kind
            configmap_secrets = self._get_kind_and_name(configmap_secret_path,
                                                        new_vnf_package_path)
            for index, manifest_path in enumerate(
                    inst_vnf_info.additional_params[
                        'lcm-kubernetes-def-files']):
                # Read the contents of the manifest file and get name and kind
                resources = self._get_kind_and_name(manifest_path,
                                                    old_vnf_package_path)
                resource = [obj for obj in resources if
                            obj in configmap_secrets]
                if resource:
                    if len(resource) == len(configmap_secrets):
                        # Update the manifest file path of ConfigMap/Secret
                        new_inst_vnf_info.additional_params[
                            'lcm-kubernetes-def-files'][
                            index] = configmap_secret_path
                        break
                    raise exceptions.MgmtDriverOtherError(
                        error_message='The number of resources in the '
                                      'manifest file of the changed '
                                      'ConfigMap/Secret is inconsistent '
                                      'with the previous one.')
        # Initialize k8s client api
        auth_attr = vim_connection_info.access_info
        auth_cred, _ = kube_driver.get_auth_creds(auth_attr)
        k8s_clients = self._initialize_k8s_client(auth_cred)

        # Get the namespace of this CNF
        namespace = vnf_instance.vnf_metadata['namespace']

        # Get old_k8s_objs
        target_k8s_files = inst_vnf_info.additional_params[
            'lcm-kubernetes-def-files']
        old_k8s_objs = self._get_k8s_objs(target_k8s_files,
                                          old_vnf_package_path, namespace,
                                          k8s_clients)

        # Get new_k8s_objs
        target_k8s_files = new_inst_vnf_info.additional_params[
            'lcm-kubernetes-def-files']
        new_k8s_objs = self._get_k8s_objs(target_k8s_files,
                                          new_vnf_package_path, namespace,
                                          k8s_clients)
        # Initialize k8s_pod_objs and k8s_config_objs
        k8s_pod_objs = []
        k8s_config_objs = []

        for old_k8s_obj in old_k8s_objs:
            old_k8s_obj_kind = old_k8s_obj['object'].kind
            old_k8s_obj_name = old_k8s_obj['object'].metadata.name
            if old_k8s_obj_kind in ['Pod', 'Deployment']:
                for new_k8s_obj in new_k8s_objs:
                    # If the old and new k8s_obj have the same kind and name
                    new_k8s_obj_kind = new_k8s_obj['object'].kind
                    new_k8s_obj_name = new_k8s_obj['object'].metadata.name
                    if old_k8s_obj_kind == new_k8s_obj_kind and (
                            old_k8s_obj_name == new_k8s_obj_name):
                        # Call the read API
                        old_k8s_resource_info = (
                            kube_driver.select_k8s_obj_read_api(
                                k8s_client_dict=k8s_clients,
                                namespace=namespace,
                                name=old_k8s_obj_name,
                                kind=old_k8s_obj_kind,
                                api_version=old_k8s_obj['object'].api_version
                            ))
                        # Assign old_k8s_resource_info to old_k8s_obj['object']
                        old_k8s_obj['object'] = old_k8s_resource_info

                        if old_k8s_obj_kind == 'Deployment':
                            old_containers = (old_k8s_obj['object'].spec
                                              .template.spec.containers)
                            new_containers = (new_k8s_obj['object'].spec
                                              .template.spec.containers)
                        elif old_k8s_obj_kind == 'Pod':
                            old_containers = (old_k8s_obj['object']
                                              .spec.containers)
                            new_containers = (new_k8s_obj['object']
                                              .spec.containers)
                        # Replace the old image with the new image
                        self._modify_container_img(old_containers,
                                                   new_containers)
                        break

                # Append old_k8s_obj to k8s_pod_objs
                k8s_pod_objs.append(old_k8s_obj)
            elif old_k8s_obj_kind in ['ConfigMap', 'Secret']:
                for new_k8s_obj in new_k8s_objs:
                    # If the old and new k8s_obj have the same kind and name
                    new_k8s_obj_kind = new_k8s_obj['object'].kind
                    new_k8s_obj_name = new_k8s_obj['object'].metadata.name
                    if old_k8s_obj_kind == new_k8s_obj_kind and (
                            old_k8s_obj_name == new_k8s_obj_name):
                        # Append old_k8s_obj to k8s_pod_objs
                        k8s_config_objs.append(new_k8s_obj)
                        break
        for k8s_config_obj in k8s_config_objs:
            # Call the replace API
            self._replace_api(k8s_clients, namespace, k8s_config_obj)
        for k8s_pod_obj in k8s_pod_objs:
            # Call the replace API
            self._replace_api(k8s_clients, namespace, k8s_pod_obj)

        # _replace_wait_k8s
        core_v1_api_client = k8s_clients['v1']
        self._replace_wait_k8s(kube_driver, k8s_pod_objs, core_v1_api_client,
                               vnf_instance)
        # Get all pod information under the specified namespace
        pods = core_v1_api_client.list_namespaced_pod(namespace=namespace)

        # get TOSCA node templates
        vnfd_dict = vnflcm_utils.get_vnfd_dict(
            context, vnf_instance.vnfd_id,
            vnf_instance.instantiated_vnf_info.flavour_id)
        tosca = tosca_template.ToscaTemplate(
            parsed_params={}, a_file=False, yaml_dict_tpl=vnfd_dict)
        tosca_node_tpls = tosca.topology_template.nodetemplates
        # get vdu_names dict {vdu_id: vdu_name}
        vdu_names = {}
        for node_tpl in tosca_node_tpls:
            for node_name, node_value in node_tpl.templates.items():
                if node_value.get('type') == "tosca.nodes.nfv.Vdu.Compute":
                    vdu_id = node_name
                    vdu_name = node_value.get('properties').get('name')
                    vdu_names[vdu_id] = vdu_name

        for vnfc_resource in new_inst_vnf_info.vnfc_resource_info:
            for pod in pods.items:
                # the name of the pod matches the resource_id in vnfc_resource
                match_result = kube_driver.is_match_pod_naming_rule(
                    vnfc_resource.compute_resource.vim_level_resource_type,
                    vdu_names[vnfc_resource.vdu_id],
                    pod.metadata.name)
                if match_result:
                    # Update the name of the pod in the resourceId
                    vnfc_resource.compute_resource.resource_id = (
                        pod.metadata.name)
                    # Delete the current pod from pods.items
                    pods.items.remove(pod)
                    break
        # the ConfigMap/Secret file path in inst_vnf_info.additional_params
        vnf_instance.instantiated_vnf_info.vnfc_resource_info = (
            new_inst_vnf_info.vnfc_resource_info)
        vnf_instance.instantiated_vnf_info.additional_params = (
            new_inst_vnf_info.additional_params)
        vnf_instance.save()

    def instantiate_start(self, context, vnf_instance,
                          instantiate_vnf_request, grant,
                          grant_request, **kwargs):
        pass

    def instantiate_end(self, context, vnf_instance,
                        instantiate_vnf_request, grant,
                        grant_request, **kwargs):
        pass

    def terminate_start(self, context, vnf_instance,
                        terminate_vnf_request, grant,
                        grant_request, **kwargs):
        pass

    def terminate_end(self, context, vnf_instance,
                      terminate_vnf_request, grant,
                      grant_request, **kwargs):
        pass

    def scale_start(self, context, vnf_instance,
                    scale_vnf_request, grant,
                    grant_request, **kwargs):
        pass

    def scale_end(self, context, vnf_instance,
                  scale_vnf_request, grant,
                  grant_request, **kwargs):
        pass

    def heal_start(self, context, vnf_instance,
                   heal_vnf_request, grant,
                   grant_request, **kwargs):
        pass

    def heal_end(self, context, vnf_instance,
                 heal_vnf_request, grant,
                 grant_request, **kwargs):
        pass

    def change_external_connectivity_start(
            self, context, vnf_instance,
            change_ext_conn_request, grant,
            grant_request, **kwargs):
        pass

    def change_external_connectivity_end(
            self, context, vnf_instance,
            change_ext_conn_request, grant,
            grant_request, **kwargs):
        pass
