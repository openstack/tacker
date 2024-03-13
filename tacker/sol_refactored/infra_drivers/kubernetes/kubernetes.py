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

from kubernetes import client
from oslo_log import log as logging

from tacker.sol_refactored.common import config
from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.common import vnf_instance_utils as inst_utils
from tacker.sol_refactored.infra_drivers.kubernetes import kubernetes_common
from tacker.sol_refactored.infra_drivers.kubernetes import kubernetes_utils


LOG = logging.getLogger(__name__)

CONF = config.CONF
CHECK_INTERVAL = 10


class Kubernetes(kubernetes_common.KubernetesCommon):

    def __init__(self):
        pass

    def instantiate(self, req, inst, grant_req, grant, vnfd):
        vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
        with kubernetes_utils.AuthContextManager(vim_info) as acm:
            k8s_api_client = acm.init_k8s_api_client()
            self._instantiate(req, inst, grant_req, grant, vnfd,
                              k8s_api_client)

    def _instantiate(self, req, inst, grant_req, grant, vnfd, k8s_api_client):
        target_k8s_files = req.additionalParams['lcm-kubernetes-def-files']

        k8s_reses, namespace = self._setup_k8s_reses(
            vnfd, target_k8s_files, k8s_api_client,
            req.additionalParams.get('namespace'), inst.id)

        vdus_num = self._get_vdus_num_from_grant_req_res_defs(
            grant_req.addResources)
        vdu_reses = self._select_vdu_reses(vnfd, req.flavourId, k8s_reses)

        for vdu_name, vdu_res in vdu_reses.items():
            if vdu_name not in vdus_num:
                LOG.debug(f'resource name {vdu_res.name} in the kubernetes'
                          f' manifest does not match the VNFD.')
                continue

            if vdu_res.kind in kubernetes_utils.SCALABLE_KIND:
                vdu_res.body['spec']['replicas'] = vdus_num[vdu_name]

        # deploy k8s resources
        for k8s_res in k8s_reses:
            if not k8s_res.is_exists():
                k8s_res.create()

        # wait k8s resource create complete
        self._wait_k8s_reses_ready(k8s_reses)

        # make instantiated info
        self._init_instantiated_vnf_info(inst, req.flavourId, vdu_reses,
            namespace, target_k8s_files)
        self._update_vnfc_info(inst, k8s_api_client)

    def _setup_k8s_reses(self, vnfd, target_k8s_files, k8s_api_client,
            namespace, inst_id):
        # NOTE: this check should be done in STARTING phase.
        vnf_artifact_files = vnfd.get_vnf_artifact_files()
        diff_files = set(target_k8s_files) - set(vnf_artifact_files)
        if diff_files:
            diff_files = ','.join(list(diff_files))
            raise sol_ex.CnfDefinitionNotFound(diff_files=diff_files)

        # get k8s content from yaml file
        return kubernetes_utils.get_k8s_reses_from_json_files(
            target_k8s_files, vnfd, k8s_api_client, namespace, inst_id)

    def instantiate_rollback(self, req, inst, grant_req, grant, vnfd):
        vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
        with kubernetes_utils.AuthContextManager(vim_info) as acm:
            k8s_api_client = acm.init_k8s_api_client()
            self._instantiate_rollback(req, inst, grant_req, grant, vnfd,
                                       k8s_api_client)

    def _instantiate_rollback(self, req, inst, grant_req, grant, vnfd,
            k8s_api_client):
        target_k8s_files = req.additionalParams['lcm-kubernetes-def-files']

        try:
            k8s_reses, _ = self._setup_k8s_reses(
                vnfd, target_k8s_files, k8s_api_client,
                req.additionalParams.get('namespace'), inst.id)
        except sol_ex.SolException:
            # it means it failed in a basic check and it failes always.
            # nothing to do since instantiate failed in it too.
            return
        k8s_reses.reverse()

        # delete k8s resources
        body = client.V1DeleteOptions(propagation_policy='Foreground')
        self._delete_k8s_resource(k8s_reses, body)
        # wait k8s resource delete complete
        self._wait_k8s_reses_deleted(k8s_reses)

    def _delete_k8s_resource(self, k8s_reses, body):
        for k8s_res in k8s_reses:
            if k8s_res.is_exists():
                k8s_res.delete(body)

    def terminate(self, req, inst, grant_req, grant, vnfd):
        vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
        with kubernetes_utils.AuthContextManager(vim_info) as acm:
            k8s_api_client = acm.init_k8s_api_client()
            self._terminate(req, inst, grant_req, grant, vnfd,
                            k8s_api_client)

    def _terminate(self, req, inst, grant_req, grant, vnfd, k8s_api_client):
        target_k8s_files = inst.instantiatedVnfInfo.metadata[
            'lcm-kubernetes-def-files']

        # get k8s content from yaml file
        namespace = inst.instantiatedVnfInfo.metadata['namespace']
        k8s_reses, _ = kubernetes_utils.get_k8s_reses_from_json_files(
            target_k8s_files, vnfd, k8s_api_client, namespace, inst.id)
        k8s_reses.reverse()

        # delete k8s resources
        timeout = 0
        if req.terminationType == 'GRACEFUL':
            timeout = CONF.v2_vnfm.default_graceful_termination_timeout
            if req.obj_attr_is_set('gracefulTerminationTimeout'):
                timeout = req.gracefulTerminationTimeout

        body = client.V1DeleteOptions(propagation_policy='Foreground',
                                      grace_period_seconds=timeout)
        self._delete_k8s_resource(k8s_reses, body)

        # wait k8s resource delete complete
        self._wait_k8s_reses_deleted(k8s_reses)

    def _change_vnfpkg_rolling_update(
            self, inst, grant_req, grant, vnfd, k8s_api_client,
            namespace, old_pods_names):

        vdus_num = self._get_vdus_num_from_grant_req_res_defs(
            grant_req.addResources)
        vdu_reses = []
        for vdu_name, vdu_num in vdus_num.items():
            vdu_res = self._get_vdu_res(inst, k8s_api_client, vdu_name)
            vdu_res.body['spec']['replicas'] = vdu_num
            vdu_reses.append(vdu_res)

        # apply new deployment
        for vdu_res in vdu_reses:
            vdu_res.patch()

        # wait k8s resource update complete
        self._wait_k8s_reses_updated(
            vdu_reses, k8s_api_client, namespace, old_pods_names)

        # update cnf instantiated info
        self._update_vnfc_info(inst, k8s_api_client)

    def change_vnfpkg(self, req, inst, grant_req, grant, vnfd):
        vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
        with kubernetes_utils.AuthContextManager(vim_info) as acm:
            k8s_api_client = acm.init_k8s_api_client()
            self._change_vnfpkg(req, inst, grant_req, grant, vnfd,
                                k8s_api_client)

    def _change_vnfpkg(self, req, inst, grant_req, grant, vnfd,
            k8s_api_client):
        if req.additionalParams['upgrade_type'] == 'RollingUpdate':
            target_k8s_files = req.additionalParams[
                'lcm-kubernetes-def-files']
            namespace = inst.instantiatedVnfInfo.metadata['namespace']

            target_vdus = {res_def.resourceTemplateId
                           for res_def in grant_req.addResources
                           if res_def.type == 'COMPUTE'}
            old_pods_names = {vnfc.computeResource.resourceId
                for vnfc in inst.instantiatedVnfInfo.vnfcResourceInfo
                if vnfc.vduId in target_vdus}

            k8s_reses, _ = self._setup_k8s_reses(
                vnfd, target_k8s_files, k8s_api_client, namespace, inst.id)

            vdu_reses = self._select_vdu_reses(
                vnfd, inst.instantiatedVnfInfo.flavourId, k8s_reses)

            self._init_instantiated_vnf_info(
                inst, inst.instantiatedVnfInfo.flavourId, vdu_reses,
                namespace, target_k8s_files)

            self._change_vnfpkg_rolling_update(
                inst, grant_req, grant, vnfd, k8s_api_client, namespace,
                old_pods_names)
        else:
            # not reach here
            pass

        inst.vnfdId = req.vnfdId

    def change_vnfpkg_rollback(self, req, inst, grant_req, grant, vnfd):
        vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
        with kubernetes_utils.AuthContextManager(vim_info) as acm:
            k8s_api_client = acm.init_k8s_api_client()
            self._change_vnfpkg_rollback(req, inst, grant_req, grant, vnfd,
                                         k8s_api_client)

    def _change_vnfpkg_rollback(self, req, inst, grant_req, grant, vnfd,
            k8s_api_client):
        if req.additionalParams['upgrade_type'] == 'RollingUpdate':
            namespace = inst.instantiatedVnfInfo.metadata['namespace']

            original_pods = {vnfc.computeResource.resourceId for vnfc in
                             inst.instantiatedVnfInfo.vnfcResourceInfo}
            all_pods = kubernetes_utils.list_namespaced_pods(
                k8s_api_client, namespace)
            current_pods = {pod.metadata.name for pod in all_pods}
            old_pods_names = current_pods - original_pods

            self._change_vnfpkg_rolling_update(
                inst, grant_req, grant, vnfd, k8s_api_client, namespace,
                old_pods_names)
        else:
            # not reach here
            pass

    def _scale_k8s_resource(self, inst, vdus_num, k8s_api_client):
        namespace = inst.instantiatedVnfInfo.metadata['namespace']

        vdu_reses = []
        for vdu_name, vdu_num in vdus_num.items():
            vdu_res = self._get_vdu_res(inst, k8s_api_client, vdu_name)
            if vdu_res.kind not in kubernetes_utils.SCALABLE_KIND:
                LOG.error(f'scale vdu {vdu_name}'
                          f' is not scalable resource')
                continue
            vdu_res.scale(vdu_num)
            vdu_reses.append(vdu_res)

        # wait k8s resource create complete
        self._wait_k8s_reses_updated(vdu_reses, k8s_api_client,
                                     namespace, old_pods_names=set())

        # make instantiated info
        self._update_vnfc_info(inst, k8s_api_client)

    def scale(self, req, inst, grant_req, grant, vnfd):

        if req.type == 'SCALE_OUT':
            vdus_num = self._get_vdus_num_from_grant_req_res_defs(
                grant_req.addResources)
            for vdu_name, vdu_num in vdus_num.items():
                vdus_num[vdu_name] = (self._get_current_vdu_num(inst, vdu_name)
                                      + vdu_num)
        elif req.type == 'SCALE_IN':
            vdus_num = self._get_vdus_num_from_grant_req_res_defs(
                grant_req.removeResources)
            for vdu_name, vdu_num in vdus_num.items():
                vdus_num[vdu_name] = (self._get_current_vdu_num(inst, vdu_name)
                                      - vdu_num)

        vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
        with kubernetes_utils.AuthContextManager(vim_info) as acm:
            k8s_api_client = acm.init_k8s_api_client()
            self._scale_k8s_resource(inst, vdus_num, k8s_api_client)

    def scale_rollback(self, req, inst, grant_req, grant, vnfd):

        vdus_num = self._get_vdus_num_from_grant_req_res_defs(
            grant_req.addResources)
        for vdu_name, _ in vdus_num.items():
            vdus_num[vdu_name] = self._get_current_vdu_num(inst, vdu_name)

        vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
        with kubernetes_utils.AuthContextManager(vim_info) as acm:
            k8s_api_client = acm.init_k8s_api_client()
            self._scale_k8s_resource(inst, vdus_num, k8s_api_client)

    def _select_vdu_reses(self, vnfd, flavour_id, k8s_reses):
        vdu_nodes = vnfd.get_vdu_nodes(flavour_id)
        vdu_ids = {value.get('properties').get('name'): key
                   for key, value in vdu_nodes.items()}
        # res.name is properties.name itself
        return {vdu_ids[res.name]: res
                for res in k8s_reses
                if (res.kind in kubernetes_utils.TARGET_KIND
                    and res.name in vdu_ids)}

    def _init_instantiated_vnf_info(self, inst, flavour_id, vdu_reses,
            namespace, target_k8s_files):
        super()._init_instantiated_vnf_info(inst, flavour_id,
                                            vdu_reses, namespace)
        inst.instantiatedVnfInfo.metadata.update(
            {'lcm-kubernetes-def-files': target_k8s_files}
        )

    def _is_match_pod_naming_rule(self, rsc_kind, rsc_name, pod_name):
        return self.is_match_pod_naming(rsc_kind, rsc_name, pod_name)
