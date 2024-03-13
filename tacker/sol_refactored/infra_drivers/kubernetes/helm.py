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

import os

from oslo_log import log as logging

from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.common import vnf_instance_utils as inst_utils
from tacker.sol_refactored.infra_drivers.kubernetes import kubernetes_common
from tacker.sol_refactored.infra_drivers.kubernetes import kubernetes_resource
from tacker.sol_refactored.infra_drivers.kubernetes import kubernetes_utils


LOG = logging.getLogger(__name__)


class Helm(kubernetes_common.KubernetesCommon):

    def __init__(self):
        pass

    def instantiate(self, req, inst, grant_req, grant, vnfd):
        vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
        with kubernetes_utils.AuthContextManager(vim_info) as acm:
            k8s_api_client = acm.init_k8s_api_client()
            helm_client = acm.init_helm_client()
            self._instantiate(req, inst, grant_req, grant, vnfd,
                              k8s_api_client, helm_client)

    def _instantiate(self, req, inst, grant_req, grant, vnfd,
            k8s_api_client, helm_client):

        namespace = req.additionalParams.get('namespace', 'default')
        helm_chart_path = req.additionalParams['helm_chart_path']
        chart_name = os.path.join(vnfd.csar_dir, helm_chart_path)
        release_name = self._get_release_name(inst)
        helm_value_names = req.additionalParams['helm_value_names']

        vdus_num = self._get_vdus_num_from_grant_req_res_defs(
            grant_req.addResources)

        # Create parameters
        parameters = req.additionalParams.get('helm_parameters', {})
        for vdu_name, vdu_num in vdus_num.items():
            replicaParam = helm_value_names.get(vdu_name, {}).get('replica')
            if replicaParam:
                parameters[replicaParam] = vdu_num

        if helm_client.is_release_exist(release_name, namespace):
            # helm upgrade. It is retry case.
            revision = helm_client.upgrade(release_name, chart_name,
                                           namespace, parameters)
        else:
            # helm install
            revision = helm_client.install(release_name, chart_name,
                                           namespace, parameters)

        # get manifest from helm chart
        k8s_resources = helm_client.get_manifest(release_name, namespace)
        k8s_reses = self._create_reses_from_manifest(k8s_api_client, namespace,
                                                     k8s_resources)
        vdu_reses = self._select_vdu_reses(vnfd, req.flavourId, k8s_reses)

        # wait k8s resource create complete
        self._wait_k8s_reses_ready(k8s_reses)

        # make instantiated info
        self._init_instantiated_vnf_info(inst, req.flavourId, vdu_reses,
            namespace, helm_chart_path, helm_value_names, release_name,
            revision)
        self._update_vnfc_info(inst, k8s_api_client)

    def instantiate_rollback(self, req, inst, grant_req, grant, vnfd):
        vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
        with kubernetes_utils.AuthContextManager(vim_info) as acm:
            k8s_api_client = acm.init_k8s_api_client()
            helm_client = acm.init_helm_client()
            namespace = req.additionalParams.get('namespace', 'default')
            release_name = self._get_release_name(inst)

            self._delete_resource(release_name, namespace,
                                  k8s_api_client, helm_client)

    def terminate(self, req, inst, grant_req, grant, vnfd):
        vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
        with kubernetes_utils.AuthContextManager(vim_info) as acm:
            k8s_api_client = acm.init_k8s_api_client()
            helm_client = acm.init_helm_client()
            namespace = inst.instantiatedVnfInfo.metadata['namespace']
            release_name = inst.instantiatedVnfInfo.metadata['release_name']

            self._delete_resource(release_name, namespace,
                                  k8s_api_client, helm_client)

    def _delete_resource(self, release_name, namespace, k8s_api_client,
            helm_client):
        if not helm_client.is_release_exist(release_name, namespace):
            LOG.info(f'HELM release {release_name} is not exist.')
            return

        # get k8s manifest from helm chart
        k8s_resources = helm_client.get_manifest(release_name, namespace)
        k8s_reses = self._create_reses_from_manifest(k8s_api_client,
                                                     namespace, k8s_resources)

        # uninstall release
        helm_client.uninstall(release_name, namespace)

        # wait k8s resource delete complete
        self._wait_k8s_reses_deleted(k8s_reses)

    def scale(self, req, inst, grant_req, grant, vnfd):
        vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
        with kubernetes_utils.AuthContextManager(vim_info) as acm:
            k8s_api_client = acm.init_k8s_api_client()
            helm_client = acm.init_helm_client()
            self._scale(req, inst, grant_req, grant, vnfd,
                        k8s_api_client, helm_client)

    def _scale(self, req, inst, grant_req, grant, vnfd,
            k8s_api_client, helm_client):
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

        metadata = inst.instantiatedVnfInfo.metadata
        namespace = metadata['namespace']
        release_name = metadata['release_name']
        chart_name = os.path.join(vnfd.csar_dir, metadata['helm_chart_path'])
        helm_value_names = metadata['helm_value_names']

        # Create scale parameters
        parameters = {}
        for vdu_name, vdu_num in vdus_num.items():
            replicaParam = helm_value_names.get(vdu_name, {}).get('replica')
            if not replicaParam:
                raise sol_ex.HelmParameterNotFound(vdu_name=vdu_name)
            parameters[replicaParam] = vdu_num

        # update
        revision = helm_client.upgrade(release_name, chart_name,
                                       namespace, parameters)

        vdu_reses = []
        for vdu_name, vdu_num in vdus_num.items():
            vdu_res = self._get_vdu_res(inst, k8s_api_client, vdu_name)
            vdu_res.body['spec']['replicas'] = vdu_num
            vdu_reses.append(vdu_res)

        # wait k8s resource create complete
        self._wait_k8s_reses_updated(vdu_reses, k8s_api_client,
                                     namespace, old_pods_names=set())

        # make instantiated info
        self._update_vnfc_info(inst, k8s_api_client)
        metadata['revision'] = revision

    def scale_rollback(self, req, inst, grant_req, grant, vnfd):
        vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
        with kubernetes_utils.AuthContextManager(vim_info) as acm:
            k8s_api_client = acm.init_k8s_api_client()
            helm_client = acm.init_helm_client()
            self._scale_rollback(req, inst, grant_req, grant, vnfd,
                                 k8s_api_client, helm_client)

    def _scale_rollback(self, req, inst, grant_req, grant, vnfd,
            k8s_api_client, helm_client):
        vdus_num = self._get_vdus_num_from_grant_req_res_defs(
            grant_req.addResources)

        metadata = inst.instantiatedVnfInfo.metadata
        namespace = metadata['namespace']
        release_name = metadata['release_name']
        revision = metadata['revision']

        # rollback
        helm_client.rollback(release_name, revision, namespace)

        vdu_reses = [self._get_vdu_res(inst, k8s_api_client, vdu_name)
                     for vdu_name in vdus_num]

        # wait k8s resource create complete
        self._wait_k8s_reses_updated(vdu_reses, k8s_api_client,
                                     namespace, old_pods_names=set())

    def change_vnfpkg(self, req, inst, grant_req, grant, vnfd):
        vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
        with kubernetes_utils.AuthContextManager(vim_info) as acm:
            k8s_api_client = acm.init_k8s_api_client()
            helm_client = acm.init_helm_client()
            if req.additionalParams['upgrade_type'] == 'RollingUpdate':
                self._change_vnfpkg_rolling_update(req, inst, grant_req,
                    grant, vnfd, k8s_api_client, helm_client)
            else:
                # not reach here
                pass

    def _change_vnfpkg_rolling_update(self, req, inst, grant_req, grant, vnfd,
            k8s_api_client, helm_client):
        metadata = inst.instantiatedVnfInfo.metadata
        namespace = metadata['namespace']
        release_name = metadata['release_name']
        helm_chart_path = req.additionalParams.get('helm_chart_path',
            metadata['helm_chart_path'])
        chart_name = os.path.join(vnfd.csar_dir, helm_chart_path)

        vdus_num = self._get_vdus_num_from_grant_req_res_defs(
            grant_req.addResources)

        # update
        revision = helm_client.upgrade(release_name, chart_name,
                                       namespace, {})

        # get manifest from helm chart
        k8s_resources = helm_client.get_manifest(release_name, namespace)
        k8s_reses = self._create_reses_from_manifest(
            k8s_api_client, namespace, k8s_resources)
        vdu_reses = self._select_vdu_reses(
            vnfd, inst.instantiatedVnfInfo.flavourId, k8s_reses)

        # wait k8s resource update complete
        target_reses = {vdu: res for vdu, res in vdu_reses.items()
                        if vdu in vdus_num.keys()}
        old_pods_names = {vnfc.computeResource.resourceId
                          for vnfc in inst.instantiatedVnfInfo.vnfcResourceInfo
                          if vnfc.vduId in vdus_num.keys()}

        self._wait_k8s_reses_updated(
            list(target_reses.values()), k8s_api_client, namespace,
            old_pods_names)

        # make instantiated info
        self._update_vnfc_info(inst, k8s_api_client)
        metadata['vdu_reses'].update(
            {vdu: res.body for vdu, res in target_reses.items()})
        metadata['helm_chart_path'] = helm_chart_path
        metadata['revision'] = revision
        inst.vnfdId = req.vnfdId

    def change_vnfpkg_rollback(self, req, inst, grant_req, grant, vnfd):
        vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
        with kubernetes_utils.AuthContextManager(vim_info) as acm:
            k8s_api_client = acm.init_k8s_api_client()
            helm_client = acm.init_helm_client()
            if req.additionalParams['upgrade_type'] == 'RollingUpdate':
                self._change_vnfpkg_rolling_update_rollback(
                    req, inst, grant_req, grant, vnfd, k8s_api_client,
                    helm_client)
            else:
                # not reach here
                pass

    def _change_vnfpkg_rolling_update_rollback(self, req, inst, grant_req,
            grant, vnfd, k8s_api_client, helm_client):
        metadata = inst.instantiatedVnfInfo.metadata
        namespace = metadata['namespace']
        release_name = metadata['release_name']
        revision = metadata['revision']

        original_pods = {vnfc.computeResource.resourceId for vnfc in
                         inst.instantiatedVnfInfo.vnfcResourceInfo}
        all_pods = kubernetes_utils.list_namespaced_pods(
            k8s_api_client, namespace)
        current_pods = {pod.metadata.name for pod in all_pods}
        old_pods_names = current_pods - original_pods

        # rollback
        helm_client.rollback(release_name, revision, namespace)

        target_vdus = {res_def.resourceTemplateId
                       for res_def in grant_req.addResources
                       if res_def.type == 'COMPUTE'}
        target_reses = [self._get_vdu_res(inst, k8s_api_client, vdu_name)
                        for vdu_name in target_vdus]

        # wait k8s resource update complete
        self._wait_k8s_reses_updated(
            target_reses, k8s_api_client, namespace, old_pods_names)

        # make instantiated info
        self._update_vnfc_info(inst, k8s_api_client)

    def _create_reses_from_manifest(self, k8s_api_client, namespace,
            k8s_resources):
        for k8s_res in k8s_resources:
            if k8s_res['kind'] in kubernetes_utils.SUPPORTED_NAMESPACE_KIND:
                k8s_res.setdefault('metadata', {})
                k8s_res['metadata'].setdefault('namespace', namespace)

        k8s_reses = []
        for k8s_res in k8s_resources:
            try:
                cls = getattr(kubernetes_resource, k8s_res['kind'])
                k8s_reses.append(cls(k8s_api_client, k8s_res))
            except AttributeError:
                LOG.info("Not support kind %s. ignored.", k8s_res['kind'])

        return k8s_reses

    def _get_release_name(self, inst):
        release_name = 'vnf' + inst.id.replace('-', '')
        return release_name

    def _select_vdu_reses(self, vnfd, flavour_id, k8s_reses):
        vdu_nodes = vnfd.get_vdu_nodes(flavour_id)
        vdu_ids = {value.get('properties').get('name'): key
                   for key, value in vdu_nodes.items()}
        # In helm case, res.name is {properties.name}-{some string}.
        # NOTE: {some string} must not include '-'.
        return {vdu_ids[res.name[:res.name.rfind("-")]]: res
                for res in k8s_reses
                if (res.kind in kubernetes_utils.TARGET_KIND
                    and res.name[:res.name.rfind("-")] in vdu_ids)}

    def _init_instantiated_vnf_info(self, inst, flavour_id, vdu_reses,
            namespace, helm_chart_path, helm_value_names, release_name,
            revision):
        super()._init_instantiated_vnf_info(inst, flavour_id, vdu_reses,
                                            namespace)
        inst.instantiatedVnfInfo.metadata.update(
            {
                'helm_chart_path': helm_chart_path,
                'helm_value_names': helm_value_names,
                'release_name': release_name,
                'revision': revision
            }
        )

    def _is_match_pod_naming_rule(self, rsc_kind, rsc_name, pod_name):
        return rsc_name in pod_name
