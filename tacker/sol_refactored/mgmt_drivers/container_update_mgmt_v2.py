# Copyright (C) 2023 FUJITSU
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
import pickle
import sys
from urllib.parse import urlparse
import urllib.request as urllib2
import yaml

from oslo_log import log as logging
from oslo_utils import uuidutils

from tacker.common import exceptions
from tacker.sol_refactored.common import vnfd_utils
from tacker.sol_refactored.infra_drivers.kubernetes import kubernetes
from tacker.sol_refactored.infra_drivers.kubernetes import kubernetes_utils
from tacker.sol_refactored import objects

LOG = logging.getLogger(__name__)


class ContainerUpdateMgmtDriver(kubernetes.Kubernetes):

    def __init__(self, req, inst, grant_req, grant, old_csar_dir,
                 new_csar_dir):
        self.req = req
        self.inst = inst
        self.grant_req = grant_req
        self.grant = grant
        self.new_csar_dir = new_csar_dir
        self.old_csar_dir = old_csar_dir
        # NOTE: In this script, vimConnectionInfo in the form of object is
        # needed to initialize k8s_client, but the input parameter is in the
        # form of dict and needs to be converted. However, the script is
        # executed by the started child process, so it needs to register
        # objects again.
        objects.register_all()

    def _get_kind_and_name(self, file, vnf_package_path):
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

    def _modify_container_img(self, containers, new_values):
        flag = False
        for old_container in containers:
            for new_container in new_values:
                if (old_container.name == new_container['name'] and
                        old_container.image != new_container['image']):
                    # Replace the old image with the new image
                    flag = True
                    old_container.image = new_container['image']
                    break
        return flag

    def _is_config_updated(self, k8s_resource_info, modify_config_names):
        containers = None
        volumes = None
        k8s_obj_kind = k8s_resource_info.kind
        if k8s_obj_kind == 'Pod':
            containers = k8s_resource_info.spec.containers
            volumes = k8s_resource_info.spec.volumes
        elif k8s_obj_kind in ('Deployment', 'ReplicaSet', 'DaemonSet'):
            containers = k8s_resource_info.spec.template.spec.containers
            volumes = k8s_resource_info.spec.template.spec.volumes
        if containers:
            for container in containers:
                if container.env:
                    for env in container.env:
                        if env.value_from.config_map_key_ref and (
                                env.value_from.config_map_key_ref.name
                                in modify_config_names["ConfigMap"]):
                            return True
                        if env.value_from.secret_key_ref and (
                                env.value_from.secret_key_ref.name
                                in modify_config_names["Secret"]):
                            return True
        if volumes:
            for volume in volumes:
                if volume.config_map and (
                        volume.config_map.name in
                        modify_config_names["ConfigMap"]):
                    return True
                if volume.secret and (
                        volume.secret.secret_name in
                        modify_config_names["Secret"]):
                    return True
        return False

    def _update_vdu_res_image_info(self, containers, new_image_info):
        for container in containers:
            container['image'] = [new_image for container_name, new_image
                                  in new_image_info.items() if
                                  container_name == container['name']][0]

    def _update_vnfc_info(self, inst, k8s_api_client):
        all_pods = kubernetes_utils.list_namespaced_pods(
            k8s_api_client,
            inst['instantiatedVnfInfo']['metadata']['namespace'])
        vnfc_resources = []
        for pod in all_pods:
            pod_name = pod.metadata.name
            for vdu_name, vdu_res in (
                    inst['instantiatedVnfInfo'][
                        'metadata']['vdu_reses'].items()):
                if self._is_match_pod_naming_rule(
                        vdu_res['kind'], vdu_res['metadata']['name'],
                        pod_name):
                    vnfc_res = {
                        "id": pod_name,
                        "vduId": vdu_name,
                        "computeResource": {
                            "resourceId": pod_name,
                            "vimLevelResourceType": vdu_res['kind']
                        },
                        "metadata": {}
                    }
                    vnfc_resources.append(vnfc_res)

        inst['instantiatedVnfInfo']['vnfcResourceInfo'] = vnfc_resources

        # make vnfcInfo
        # NOTE: vnfcInfo only exists in SOL002
        inst['instantiatedVnfInfo']['vnfcInfo'] = [
            {
                "id": f"{vnfc_res_info['vduId']}-{vnfc_res_info['id']}",
                "vduId": vnfc_res_info['vduId'],
                "vnfcResourceInfoId": vnfc_res_info['id'],
                "vnfcState": 'STARTED'
            }
            for vnfc_res_info in vnfc_resources
        ]

    def _select_vim_info(self, vim_connection_info):
        for vim_info in vim_connection_info.values():
            if vim_info['vimType'] == 'kubernetes':
                vim_info['vimType'] = 'ETSINFV.KUBERNETES.V_1'
            return vim_info

    def modify_information_end(self):
        # get old_vnf_package_path
        old_vnf_package_path = self.old_csar_dir
        vnf_instance = self.inst

        # get configmap_secret_paths
        configmap_secret_paths = self.req.get('metadata', {}).get(
            'configmap_secret_paths', [])
        # Get the path of the VNF Package according to vnf_instance.vnfdId
        new_vnf_package_path = self.new_csar_dir

        # Get instantiatedVnfInfo from vnf_instance
        inst_vnf_info = vnf_instance['instantiatedVnfInfo']

        # Make a deep copy of inst_vnf_info
        new_inst_vnf_info = copy.deepcopy(inst_vnf_info)

        # Get vim_connection_info from vnf_instance
        vim_connection_info = objects.VimConnectionInfo.from_dict(
            self._select_vim_info(vnf_instance['vimConnectionInfo']))

        # the name of updated configmap/secret will be in this set
        modify_config_names = {"ConfigMap": [], "Secret": []}
        for configmap_secret_path in configmap_secret_paths:
            # Read the contents of the manifest file and get name and kind
            configmap_secrets = self._get_kind_and_name(configmap_secret_path,
                                                        new_vnf_package_path)
            for index, manifest_path in enumerate(
                    inst_vnf_info['metadata'].get('lcm-kubernetes-def-files')):
                # Read the contents of the manifest file and get name and kind
                resources = self._get_kind_and_name(manifest_path,
                                                    old_vnf_package_path)
                resource = [obj for obj in resources if
                            obj in configmap_secrets]
                if resource:
                    if len(resource) == len(configmap_secrets):
                        # Update the manifest file path of ConfigMap/Secret
                        new_inst_vnf_info['metadata'][
                            'lcm-kubernetes-def-files'][
                            index] = configmap_secret_path
                        for obj in resource:
                            modify_config_names[obj["kind"]].append(
                                obj["name"])
                        break
                    raise exceptions.MgmtDriverOtherError(
                        error_message='The number of resources in the '
                                      'manifest file of the changed '
                                      'ConfigMap/Secret is inconsistent '
                                      'with the previous one.')
        # Initialize k8s client api
        acm = kubernetes_utils.AuthContextManager(vim_connection_info)
        k8s_api_client = acm.init_k8s_api_client()

        # Get the namespace of this CNF
        namespace = inst_vnf_info['metadata']['namespace']

        # Get old_k8s_objs
        target_k8s_files = inst_vnf_info['metadata'][
            'lcm-kubernetes-def-files']
        old_vnfd = vnfd_utils.Vnfd(uuidutils.generate_uuid())
        old_vnfd.init_from_csar_dir(self.old_csar_dir)
        old_k8s_objs, _ = self._setup_k8s_reses(
            old_vnfd, target_k8s_files, k8s_api_client, namespace,
            vnf_instance['id'])
        # Get new_k8s_objs
        target_k8s_files = new_inst_vnf_info['metadata'][
            'lcm-kubernetes-def-files']
        new_vnfd = vnfd_utils.Vnfd(self.req['vnfdId'])
        new_vnfd.init_from_csar_dir(self.new_csar_dir)
        new_k8s_objs, _ = self._setup_k8s_reses(
            new_vnfd, target_k8s_files, k8s_api_client, namespace,
            vnf_instance['id'])
        # Initialize k8s_pod_objs and k8s_config_objs
        k8s_pod_objs = []
        k8s_config_objs = []
        vdu_image_changed_info = {}

        for old_k8s_obj in old_k8s_objs:
            old_k8s_obj_kind = old_k8s_obj.kind
            old_k8s_obj_name = old_k8s_obj.name
            if old_k8s_obj_kind in ('Pod', 'Deployment',
                                    'ReplicaSet', 'DaemonSet'):
                image_modify_flag = False
                config_modify_flag = False
                for new_k8s_obj in new_k8s_objs:
                    # If the old and new k8s_obj have the same kind and name
                    new_k8s_obj_kind = new_k8s_obj.kind
                    new_k8s_obj_name = new_k8s_obj.name
                    if old_k8s_obj_kind == new_k8s_obj_kind and (
                            old_k8s_obj_name == new_k8s_obj_name):
                        # Call the read API
                        old_k8s_resource_info = old_k8s_obj.read()
                        # Assign old_k8s_resource_info to old_k8s_obj['object']
                        old_k8s_obj.body = old_k8s_resource_info

                        # if config of Pod/Deployment/ReplicaSet/DaemonSet
                        # is to be updated then set config_modify_flag True
                        config_modify_flag = self._is_config_updated(
                            old_k8s_resource_info, modify_config_names)
                        if old_k8s_obj_kind in ('Deployment', 'ReplicaSet',
                                                'DaemonSet'):
                            old_containers = (old_k8s_obj.body.spec
                                              .template.spec.containers)
                            new_containers = (
                                new_k8s_obj.body['spec'][
                                    'template']['spec']['containers'])
                        elif old_k8s_obj_kind == 'Pod':
                            old_containers = (old_k8s_obj.body
                                              .spec.containers)
                            new_containers = (
                                new_k8s_obj.body['spec']['containers'])
                        # Replace the old image with the new image
                        image_modify_flag = self._modify_container_img(
                            old_containers, new_containers)
                        if image_modify_flag:
                            vdu_image_changed_info[new_k8s_obj_name] = {
                                old_container.name: old_container.image
                                for old_container in old_containers}
                        break
                # Append only old_k8s_obj whose image or config would
                # be updated to k8s_pod_objs
                if image_modify_flag or config_modify_flag:
                    k8s_pod_objs.append(old_k8s_obj)
            elif old_k8s_obj_kind in ['ConfigMap', 'Secret']:
                for new_k8s_obj in new_k8s_objs:
                    # If the old and new k8s_obj have the same kind and name
                    new_k8s_obj_kind = new_k8s_obj.kind
                    new_k8s_obj_name = new_k8s_obj.name
                    if old_k8s_obj_kind == new_k8s_obj_kind and (
                            old_k8s_obj_name == new_k8s_obj_name):
                        # Append new_k8s_obj to k8s_config_objs
                        k8s_config_objs.append(new_k8s_obj)
                        break
        for k8s_config_obj in k8s_config_objs:
            # Call the replace API
            k8s_config_obj.replace()

        pods = kubernetes_utils.list_namespaced_pods(
            k8s_api_client, namespace=namespace)
        old_pods_names = set()
        for k8s_pod_obj in k8s_pod_objs:
            # Call the replace API
            k8s_pod_obj.replace()
            for pod in pods:
                # TODO(YiFeng): The function of `is_match_pod_naming` is
                # called too frequently, resulting in reduced performance.
                # In the future, during instantiate processing, the label of
                # `vnfInstanceId: xxxxx` will be added to the specified
                # resource of CNF, and then the parameter `label_selector`
                # will be added when calling `list_namespaced_pods` above to
                # filter to get the pods belonging to the CNF.
                match_result = self.is_match_pod_naming(
                    k8s_pod_obj.kind,
                    k8s_pod_obj.name,
                    pod.metadata.name)
                if match_result:
                    # delete pod of modified replicaset
                    # After using the replace_namespaced_replicaset API of k8s,
                    # the new configuration cannot be applied to the pod
                    # created by the replicaset, so you need to delete the pod
                    # first, and then the replicaset will automatically rebuild
                    # the pod to make the new configuration take effect.
                    if k8s_pod_obj.kind == 'ReplicaSet':
                        k8s_pod_obj.delete_pod(pod.metadata.name)
                    old_pods_names.add(pod.metadata.name)
                    pods.remove(pod)

        # _replace_wait_k8s
        self._wait_k8s_reses_updated(
            k8s_pod_objs, k8s_api_client, namespace, old_pods_names)

        # update DB
        # update vdu_reses
        updated_vdu = [vnfc_res_info['vduId'] for vnfc_res_info in
                       new_inst_vnf_info['vnfcResourceInfo'] if
                       vnfc_res_info['id'] in old_pods_names]
        for vdu, vdu_res in new_inst_vnf_info['metadata']['vdu_reses'].items():
            k8s_ojb_name = vdu_res.get('metadata', {}).get('name')
            if (vdu in updated_vdu and k8s_ojb_name
                    in list(vdu_image_changed_info.keys())):
                if vdu_res['kind'] == 'Pod':
                    self._update_vdu_res_image_info(
                        vdu_res['spec']['containers'],
                        vdu_image_changed_info[k8s_ojb_name])
                else:
                    self._update_vdu_res_image_info(
                        vdu_res['spec']['template']['spec']['containers'],
                        vdu_image_changed_info[k8s_ojb_name])

        vnf_instance['instantiatedVnfInfo'] = new_inst_vnf_info
        self._update_vnfc_info(vnf_instance, k8s_api_client)
        output = {'vnf_instance': vnf_instance}
        return output

    def modify_information_start(self):
        pass


def main():
    script_dict = pickle.load(sys.stdin.buffer)

    operation = script_dict['operation']
    req = script_dict['request']
    inst = script_dict['vnf_instance']
    grant_req = script_dict['grant_request']
    grant = script_dict['grant_response']
    csar_dir = script_dict['tmp_csar_dir']
    new_csar_dir = script_dict['new_csar_dir']

    try:
        script = ContainerUpdateMgmtDriver(
            req, inst, grant_req, grant, csar_dir, new_csar_dir)
        output_dict = getattr(script, operation)()
        sys.stdout.buffer.write(pickle.dumps(output_dict))
        sys.stdout.flush()
    except (Exception, AttributeError) as exc:
        raise exceptions.MgmtDriverOtherError(error_message=str(exc))


if __name__ == "__main__":
    try:
        main()
        os._exit(0)
    except exceptions.MgmtDriverOtherError as ex:
        sys.stderr.write(str(ex))
        sys.stderr.flush()
        os._exit(1)
