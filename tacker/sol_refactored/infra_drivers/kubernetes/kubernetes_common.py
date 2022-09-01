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


class KubernetesCommon(object):

    def __init__(self):
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
        # res.name is properties.name itself or
        # {properties.name}-{some string}. later is helm case.
        return {vdu_ids[res.name.split("-")[0]]: res
                for res in k8s_reses
                if (res.kind in TARGET_KIND
                    and res.name.split("-")[0] in vdu_ids)}

    def _init_instantiated_vnf_info(self, inst, flavour_id,
            vdu_reses, namespace):
        metadata = {
            'namespace': namespace,
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
                if self._is_match_pod_naming_rule(
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
        def _check_updated(check_reses, k8s_api_client, namespace,
                old_pods_names):
            ok_reses = set()
            all_pods = kubernetes_utils.list_namespaced_pods(
                k8s_api_client, namespace)
            for res in check_reses:
                pods_info = [pod for pod in all_pods
                             if self._is_match_pod_naming_rule(
                                 res.kind, res.name, pod.metadata.name)]
                if res.is_update(pods_info, old_pods_names):
                    ok_reses.add(res)
            check_reses -= ok_reses
            if not check_reses:
                raise loopingcall.LoopingCallDone()

        check_reses = set(k8s_reses)
        self._check_status(_check_updated, check_reses, k8s_api_client,
                           namespace, old_pods_names)
