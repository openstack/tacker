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
from oslo_service import loopingcall

from tacker.sol_refactored.common import config
from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.common import vnf_instance_utils as inst_utils
from tacker.sol_refactored.infra_drivers.kubernetes import kubernetes_resource
from tacker.sol_refactored.infra_drivers.kubernetes import kubernetes_utils
from tacker.sol_refactored import objects


LOG = logging.getLogger(__name__)

CONF = config.CONF
CHECK_INTERVAL = 10

TARGET_KIND = {"Pod", "Deployment", "DaemonSet", "StatefulSet", "ReplicaSet"}
SCALABLE_KIND = {"Deployment", "ReplicaSet", "StatefulSet"}


class Kubernetes(object):

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
            req.additionalParams.get('namespace'))

        vdus_num = self._get_vdus_num_from_grant_req_res_defs(
            grant_req.addResources)
        vdu_reses = self._select_vdu_reses(vnfd, req.flavourId, k8s_reses)

        for vdu_name, vdu_res in vdu_reses.items():
            if vdu_name not in vdus_num:
                LOG.debug(f'resource name {vdu_res.name} in the kubernetes'
                          f' manifest does not match the VNFD.')
                continue

            if vdu_res.kind in SCALABLE_KIND:
                vdu_res.body['spec']['replicas'] = vdus_num[vdu_name]

        # deploy k8s resources
        for k8s_res in k8s_reses:
            if not k8s_res.is_exists():
                k8s_res.create()

        # wait k8s resource create complete
        self._wait_k8s_reses_ready(k8s_reses)

        # make instantiated info
        self._init_instantiated_vnf_info(
            inst, req.flavourId, target_k8s_files, vdu_reses, namespace)
        self._update_vnfc_info(inst, k8s_api_client)

    def _setup_k8s_reses(self, vnfd, target_k8s_files, k8s_api_client,
            namespace):
        # NOTE: this check should be done in STARTING phase.
        vnf_artifact_files = vnfd.get_vnf_artifact_files()
        diff_files = set(target_k8s_files) - set(vnf_artifact_files)
        if diff_files:
            diff_files = ','.join(list(diff_files))
            raise sol_ex.CnfDefinitionNotFound(diff_files=diff_files)

        # get k8s content from yaml file
        return kubernetes_utils.get_k8s_reses_from_json_files(
            target_k8s_files, vnfd, k8s_api_client, namespace)

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
                req.additionalParams.get('namespace'))
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
            target_k8s_files, vnfd, k8s_api_client, namespace)
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
                vnfd, target_k8s_files, k8s_api_client, namespace)

            vdu_reses = self._select_vdu_reses(
                vnfd, inst.instantiatedVnfInfo.flavourId, k8s_reses)

            self._init_instantiated_vnf_info(
                inst, inst.instantiatedVnfInfo.flavourId, target_k8s_files,
                vdu_reses, namespace)

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

    def heal(self, req, inst, grant_req, grant, vnfd):
        vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
        with kubernetes_utils.AuthContextManager(vim_info) as acm:
            k8s_api_client = acm.init_k8s_api_client()
            self._heal(req, inst, grant_req, grant, vnfd, k8s_api_client)

    def _heal(self, req, inst, grant_req, grant, vnfd, k8s_api_client):
        namespace = inst.instantiatedVnfInfo.metadata['namespace']

        # get heal Pod name
        vnfc_res_ids = [res_def.resource.resourceId
                        for res_def in grant_req.removeResources
                        if res_def.type == 'COMPUTE']

        target_vnfcs = [vnfc
                        for vnfc in inst.instantiatedVnfInfo.vnfcResourceInfo
                        if vnfc.computeResource.resourceId in vnfc_res_ids]

        # check running Pod
        all_pods = kubernetes_utils.list_namespaced_pods(
            k8s_api_client, namespace)
        current_pods_name = [pod.metadata.name for pod in all_pods]

        old_pods_names = set()
        vdu_reses = {}
        for vnfc in target_vnfcs:
            if vnfc.id not in current_pods_name:
                # may happen when retry or auto healing
                msg = f'heal target pod {vnfc.id} is not in the running pod.'
                LOG.error(msg)
                continue
            if vnfc.vduId in vdu_reses:
                res = vdu_reses[vnfc.vduId]
            else:
                res = self._get_vdu_res(inst, k8s_api_client, vnfc.vduId)
                vdu_reses[vnfc.vduId] = res
            res.delete_pod(vnfc.id)
            old_pods_names.add(vnfc.id)

        # wait k8s resource create complete
        if old_pods_names:
            self._wait_k8s_reses_updated(list(vdu_reses.values()),
                k8s_api_client, namespace, old_pods_names)

        # make instantiated info
        self._update_vnfc_info(inst, k8s_api_client)

    def _scale_k8s_resource(self, inst, vdus_num, k8s_api_client):
        namespace = inst.instantiatedVnfInfo.metadata['namespace']

        vdu_reses = []
        for vdu_name, vdu_num in vdus_num.items():
            vdu_res = self._get_vdu_res(inst, k8s_api_client, vdu_name)
            if vdu_res.kind not in SCALABLE_KIND:
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

    def _get_vdus_num_from_grant_req_res_defs(self, res_defs):
        vdus_num = {}
        for res_def in res_defs:
            if res_def.type == 'COMPUTE':
                vdus_num.setdefault(res_def.resourceTemplateId, 0)
                vdus_num[res_def.resourceTemplateId] += 1
        return vdus_num

    def _get_current_vdu_num(self, inst, vdu):
        num = 0
        for vnfc in inst.instantiatedVnfInfo.vnfcResourceInfo:
            if vnfc.vduId == vdu:
                num += 1
        return num

    def _select_vdu_reses(self, vnfd, flavour_id, k8s_reses):
        vdu_nodes = vnfd.get_vdu_nodes(flavour_id)
        vdu_ids = {value.get('properties').get('name'): key
                   for key, value in vdu_nodes.items()}
        return {vdu_ids[res.name]: res
                for res in k8s_reses
                if res.kind in TARGET_KIND and res.name in vdu_ids}

    def _init_instantiated_vnf_info(self, inst, flavour_id, def_files,
            vdu_reses, namespace):
        metadata = {
            'namespace': namespace,
            'lcm-kubernetes-def-files': def_files,
            'vdu_reses': {vdu_name: vdu_res.body
                          for vdu_name, vdu_res in vdu_reses.items()}
        }
        inst.instantiatedVnfInfo = objects.VnfInstanceV2_InstantiatedVnfInfo(
            flavourId=flavour_id,
            vnfState='STARTED',
            metadata=metadata
        )

    def _get_vdu_res(self, inst, k8s_api_client, vdu):
        # must be found
        res = inst.instantiatedVnfInfo.metadata['vdu_reses'][vdu]
        cls = getattr(kubernetes_resource, res['kind'])
        return cls(k8s_api_client, res)

    def _update_vnfc_info(self, inst, k8s_api_client):
        all_pods = kubernetes_utils.list_namespaced_pods(
            k8s_api_client, inst.instantiatedVnfInfo.metadata['namespace'])
        vnfc_resources = []
        for pod in all_pods:
            pod_name = pod.metadata.name
            for vdu_name, vdu_res in (
                    inst.instantiatedVnfInfo.metadata['vdu_reses'].items()):
                if kubernetes_utils.is_match_pod_naming_rule(
                        vdu_res['kind'], vdu_res['metadata']['name'],
                        pod_name):
                    vnfc_resources.append(objects.VnfcResourceInfoV2(
                        id=pod_name,
                        vduId=vdu_name,
                        computeResource=objects.ResourceHandle(
                            resourceId=pod_name,
                            vimLevelResourceType=vdu_res['kind']
                        ),
                        # lcmocc_utils.update_lcmocc assumes its existence
                        metadata={}
                    ))

        inst.instantiatedVnfInfo.vnfcResourceInfo = vnfc_resources

        # make vnfcInfo
        # NOTE: vnfcInfo only exists in SOL002
        inst.instantiatedVnfInfo.vnfcInfo = [
            objects.VnfcInfoV2(
                id=f'{vnfc_res_info.vduId}-{vnfc_res_info.id}',
                vduId=vnfc_res_info.vduId,
                vnfcResourceInfoId=vnfc_res_info.id,
                vnfcState='STARTED'
            )
            for vnfc_res_info in vnfc_resources
        ]

    def _check_status(self, check_func, *args):
        timer = loopingcall.FixedIntervalWithTimeoutLoopingCall(
            check_func, *args)
        try:
            timer.start(interval=CHECK_INTERVAL,
                timeout=CONF.v2_vnfm.kubernetes_vim_rsc_wait_timeout).wait()
        except loopingcall.LoopingCallTimeOut:
            raise sol_ex.K8sOperaitionTimeout()

    def _wait_k8s_reses_ready(self, k8s_reses):
        def _check_ready(check_reses):
            ok_reses = {res for res in check_reses if res.is_ready()}
            check_reses -= ok_reses
            if not check_reses:
                raise loopingcall.LoopingCallDone()

        check_reses = set(k8s_reses)
        self._check_status(_check_ready, check_reses)

    def _wait_k8s_reses_deleted(self, k8s_reses):
        def _check_deleted(check_reses):
            ok_reses = {res for res in check_reses if not res.is_exists()}
            check_reses -= ok_reses
            if not check_reses:
                raise loopingcall.LoopingCallDone()

        check_reses = set(k8s_reses)
        self._check_status(_check_deleted, check_reses)

    def _wait_k8s_reses_updated(self, k8s_reses, k8s_api_client, namespace,
            old_pods_names):
        def _check_update(check_reses, k8s_api_client, namespace,
                old_pods_names):
            ok_reses = set()
            all_pods = kubernetes_utils.list_namespaced_pods(
                k8s_api_client, namespace)
            for res in check_reses:
                pods_info = [pod for pod in all_pods
                             if kubernetes_utils.is_match_pod_naming_rule(
                                 res.kind, res.name, pod.metadata.name)]
                if res.is_update(pods_info, old_pods_names):
                    ok_reses.add(res)
            check_reses -= ok_reses
            if not check_reses:
                raise loopingcall.LoopingCallDone()

        check_reses = set(k8s_reses)
        self._check_status(_check_update, check_reses, k8s_api_client,
                           namespace, old_pods_names)
