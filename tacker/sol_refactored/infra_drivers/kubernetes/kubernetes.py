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
import pickle
import subprocess

from oslo_log import log as logging
from oslo_utils import uuidutils

from tacker.sol_refactored.common import config
from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.common import vnf_instance_utils as inst_utils
from tacker.sol_refactored.infra_drivers.kubernetes import kubernetes_utils
from tacker.sol_refactored import objects


LOG = logging.getLogger(__name__)

CONF = config.CONF


class Kubernetes(object):

    def __init__(self):
        pass

    def instantiate(self, req, inst, grant_req, grant, vnfd):
        # pre instantiate cnf
        target_k8s_files = req.additionalParams.get(
            'lcm-kubernetes-def-files')
        vnf_artifact_files = vnfd.get_vnf_artifact_files()

        if vnf_artifact_files is None or set(target_k8s_files).difference(
                set(vnf_artifact_files)):
            if vnf_artifact_files:
                diff_files = ','.join(list(set(
                    target_k8s_files).difference(set(vnf_artifact_files))))
            else:
                diff_files = ','.join(target_k8s_files)
            raise sol_ex.CnfDefinitionNotFound(diff_files=diff_files)

        # get k8s content from yaml file
        k8s_resources, namespace = kubernetes_utils.get_k8s_json_file(
            req, inst, target_k8s_files, vnfd, 'INSTANTIATE')

        # sort k8s resource
        sorted_k8s_reses = kubernetes_utils.sort_k8s_resource(
            k8s_resources, 'INSTANTIATE')

        # deploy k8s resources with sorted resources
        vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
        k8s_client = kubernetes_utils.KubernetesClient(vim_info)
        created_k8s_reses = k8s_client.create_k8s_resource(
            sorted_k8s_reses, namespace)

        # wait k8s resource create complete
        k8s_client.wait_k8s_res_create(created_k8s_reses)

        # make instantiated info
        all_pods = k8s_client.list_namespaced_pods(namespace)
        self._make_cnf_instantiated_info(
            req, inst, vnfd, namespace, created_k8s_reses, all_pods)

    def terminate(self, req, inst, grant_req, grant, vnfd):
        target_k8s_files = inst.metadata.get('lcm-kubernetes-def-files')

        # get k8s content from yaml file
        k8s_resources, namespace = kubernetes_utils.get_k8s_json_file(
            req, inst, target_k8s_files, vnfd, 'TERMINATE')

        # sort k8s resource
        sorted_k8s_reses = kubernetes_utils.sort_k8s_resource(
            k8s_resources, 'TERMINATE')

        # delete k8s resources with sorted resources
        vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
        k8s_client = kubernetes_utils.KubernetesClient(vim_info)
        k8s_client.delete_k8s_resource(req, sorted_k8s_reses, namespace)

        # wait k8s resource delete complete
        k8s_client.wait_k8s_res_delete(sorted_k8s_reses, namespace)

    def change_vnfpkg(self, req, inst, grant_req, grant, vnfd):
        if req.additionalParams.get('upgrade_type') == 'RollingUpdate':
            # get deployment name from vnfd
            deployment_names, namespace = (
                self._get_update_deployment_names_and_namespace(
                    vnfd, req, inst))

            # check deployment exists in kubernetes
            vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
            k8s_client = kubernetes_utils.KubernetesClient(vim_info)
            k8s_client.check_deployment_exist(deployment_names, namespace)

            # get new deployment body
            new_deploy_reses = kubernetes_utils.get_new_deployment_body(
                req, inst, vnfd, deployment_names, operation='CHANGE_VNFPKG')

            # apply new deployment
            k8s_client.update_k8s_resource(new_deploy_reses, namespace)

            # wait k8s resource update complete
            old_pods_names = [vnfc.computeResource.resourceId for vnfc in
                              inst.instantiatedVnfInfo.vnfcResourceInfo]
            try:
                k8s_client.wait_k8s_res_update(
                    new_deploy_reses, namespace, old_pods_names)
            except sol_ex.UpdateK8SResourceFailed as ex:
                self._update_cnf_instantiated_info(
                    inst, deployment_names, k8s_client.list_namespaced_pods(
                        namespace=namespace))
                raise ex

            # execute coordinate vnf script
            try:
                self._execute_coordinate_vnf_script(
                    req, inst, grant_req, grant, vnfd, 'CHANGE_VNFPKG',
                    namespace, new_deploy_reses)
            except sol_ex.CoordinateVNFExecutionFailed as ex:
                self._update_cnf_instantiated_info(
                    inst, deployment_names, k8s_client.list_namespaced_pods(
                        namespace=namespace))
                raise ex

            # update cnf instantiated info
            all_pods = k8s_client.list_namespaced_pods(namespace)
            self._update_cnf_instantiated_info(
                inst, deployment_names, all_pods)

        else:
            # TODO(YiFeng): Blue-Green type will be supported in next version.
            raise sol_ex.SolException(sol_detail='not support update type')

        inst.vnfdId = req.vnfdId
        if set(req.additionalParams.get(
                'lcm-kubernetes-def-files')).difference(set(
                inst.metadata.get('lcm-kubernetes-def-files'))):
            inst.metadata['lcm-kubernetes-def-files'] = (
                req.additionalParams.get('lcm-kubernetes-def-files'))

    def change_vnfpkg_rollback(
            self, req, inst, grant_req, grant, vnfd, lcmocc):
        if not lcmocc.obj_attr_is_set('resourceChanges'):
            return
        if req.additionalParams.get('upgrade_type') == 'RollingUpdate':
            deployment_names = list({
                affected_vnfc.metadata['Deployment']['name'] for affected_vnfc
                in lcmocc.resourceChanges.affectedVnfcs if
                affected_vnfc.changeType == 'ADDED'})
            namespace = inst.metadata.get('namespace')

            old_deploy_reses = kubernetes_utils.get_new_deployment_body(
                req, inst, vnfd, deployment_names,
                operation='CHANGE_VNFPKG_ROLLBACK')

            # apply old deployment
            vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
            k8s_client = kubernetes_utils.KubernetesClient(vim_info)
            k8s_client.update_k8s_resource(old_deploy_reses, namespace)

            # wait k8s resource update complete
            old_pods_names = [vnfc.computeResource.resourceId for vnfc in
                              inst.instantiatedVnfInfo.vnfcResourceInfo]
            try:
                k8s_client.wait_k8s_res_update(
                    old_deploy_reses, namespace, old_pods_names)
            except sol_ex.UpdateK8SResourceFailed as ex:
                raise ex

            # execute coordinate vnf script
            try:
                self._execute_coordinate_vnf_script(
                    req, inst, grant_req, grant, vnfd,
                    'CHANGE_VNFPKG_ROLLBACK',
                    namespace, old_deploy_reses)
            except sol_ex.CoordinateVNFExecutionFailed as ex:
                raise ex

            # update cnf instantiated info
            all_pods = k8s_client.list_namespaced_pods(namespace)
            self._update_cnf_instantiated_info(
                inst, deployment_names, all_pods)

        else:
            # TODO(YiFeng): Blue-Green type will be supported in next version.
            raise sol_ex.SolException(sol_detail='not support update type')

    def _get_update_deployment_names_and_namespace(self, vnfd, req, inst):
        vdu_nodes = vnfd.get_vdu_nodes(
            flavour_id=inst.instantiatedVnfInfo.flavourId)

        if req.additionalParams.get('vdu_params'):
            target_vdus = [vdu_param.get('vdu_id') for vdu_param
                           in req.additionalParams.get('vdu_params')]
            if None in target_vdus:
                raise sol_ex.MissingParameterException
        else:
            target_vdus = [inst_vnc.vduId for inst_vnc in
                           inst.instantiatedVnfInfo.vnfcResourceInfo]

        deployment_names = [value.get('properties', {}).get('name')
                            for name, value in vdu_nodes.items()
                            if name in target_vdus]
        namespace = inst.metadata.get('namespace')

        return deployment_names, namespace

    def _make_cnf_instantiated_info(
            self, req, inst, vnfd, namespace, created_k8s_reses, all_pods):
        flavour_id = req.flavourId
        target_kinds = {"Pod", "Deployment", "DaemonSet",
                        "StatefulSet", "ReplicaSet"}

        vdu_nodes = vnfd.get_vdu_nodes(flavour_id)
        vdu_ids = {value.get('properties').get('name'): key
                   for key, value in vdu_nodes.items()}

        vnfc_resources = []
        for k8s_res in created_k8s_reses:
            if k8s_res.get('kind', '') not in target_kinds:
                continue
            for pod in all_pods:
                pod_name = pod.metadata.name
                match_result = kubernetes_utils.is_match_pod_naming_rule(
                    k8s_res.get('kind', ''), k8s_res.get('name', ''),
                    pod_name)
                if match_result:
                    metadata = {}
                    metadata[k8s_res.get('kind')] = k8s_res.get('metadata')
                    if k8s_res.get('kind') != 'Pod':
                        metadata['Pod'] = pod.metadata.to_dict()
                    vnfc_resource = objects.VnfcResourceInfoV2(
                        id=uuidutils.generate_uuid(),
                        vduId=vdu_ids.get(k8s_res.get('name', '')),
                        computeResource=objects.ResourceHandle(
                            resourceId=pod_name,
                            vimLevelResourceType=k8s_res.get('kind')
                        ),
                        metadata=metadata
                    )
                    vnfc_resources.append(vnfc_resource)

        inst_vnf_info = objects.VnfInstanceV2_InstantiatedVnfInfo(
            flavourId=flavour_id,
            vnfState='STARTED',
        )

        if vnfc_resources:
            inst_vnf_info.vnfcResourceInfo = vnfc_resources
            # make vnfcInfo
            # NOTE: vnfcInfo only exists in SOL002
            inst_vnf_info.vnfcInfo = [
                objects.VnfcInfoV2(
                    id=f'{vnfc_res_info.vduId}-{vnfc_res_info.id}',
                    vduId=vnfc_res_info.vduId,
                    vnfcResourceInfoId=vnfc_res_info.id,
                    vnfcState='STARTED'
                )
                for vnfc_res_info in vnfc_resources
            ]

        inst.instantiatedVnfInfo = inst_vnf_info
        inst.metadata = {"namespace": namespace if namespace else None}
        inst.metadata['lcm-kubernetes-def-files'] = req.additionalParams.get(
            'lcm-kubernetes-def-files')

    def _execute_coordinate_vnf_script(
            self, req, inst, grant_req, grant, vnfd,
            operation, namespace, new_deploy_reses):
        coordinate_vnf = None
        coordinate_vnf_class = None
        if req.obj_attr_is_set('additionalParams'):
            if operation == 'CHANGE_VNFPKG':
                coordinate_vnf = req.additionalParams.get(
                    'lcm-operation-coordinate-new-vnf')
                coordinate_vnf_class = req.additionalParams.get(
                    'lcm-operation-coordinate-new-vnf-class')
            else:
                coordinate_vnf = req.additionalParams.get(
                    'lcm-operation-coordinate-old-vnf')
                coordinate_vnf_class = req.additionalParams.get(
                    'lcm-operation-coordinate-old-vnf-class')

        if coordinate_vnf and coordinate_vnf_class:
            tmp_csar_dir = vnfd.make_tmp_csar_dir()
            script_dict = {
                "request": req.to_dict(),
                "vnf_instance": inst.to_dict(),
                "grant_request": grant_req.to_dict(),
                "grant_response": grant.to_dict(),
                "tmp_csar_dir": tmp_csar_dir,
                "k8s_info": {
                    "namespace": namespace,
                    "new_deploy_reses": new_deploy_reses
                }
            }
            script_path = os.path.join(tmp_csar_dir, coordinate_vnf)
            out = subprocess.run(["python3", script_path],
                input=pickle.dumps(script_dict),
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if out.returncode != 0:
                LOG.error(out)
                raise sol_ex.CoordinateVNFExecutionFailed

    def _update_cnf_instantiated_info(self, inst, deployment_names, all_pods):
        error_resource = None
        for vnfc in inst.instantiatedVnfInfo.vnfcResourceInfo:
            if (vnfc.computeResource.vimLevelResourceType == 'Deployment'
                ) and (vnfc.metadata.get('Deployment').get(
                    'name') in deployment_names):
                pods_info = [pod for pod in all_pods if
                            kubernetes_utils.is_match_pod_naming_rule(
                                'Deployment',
                                vnfc.metadata.get('Deployment').get('name'),
                                pod.metadata.name)]
                if 'Pending' in [pod.status.phase for pod in pods_info] or (
                        'Unknown' in [pod.status.phase for pod in pods_info]):
                    pod_name = [pod.metadata.name for pod in pods_info
                                if pod.status.phase in [
                                    'Pending', 'Unknown']][0]
                    error_resource = objects.VnfcResourceInfoV2(
                        id=uuidutils.generate_uuid(),
                        vduId=vnfc.vduId,
                        computeResource=objects.ResourceHandle(
                            resourceId=pod_name,
                            vimLevelResourceType='Deployment'
                        ),
                        metadata={'Deployment': vnfc.metadata.get(
                            'Deployment')}
                    )
                    continue
                pod_info = pods_info.pop(-1)
                vnfc.id = uuidutils.generate_uuid()
                vnfc.computeResource.resourceId = pod_info.metadata.name
                vnfc.metadata['Pod'] = pod_info.metadata.to_dict()
                all_pods.remove(pod_info)

        if error_resource:
            inst.instantiatedVnfInfo.vnfcResourceInfo.append(error_resource)
