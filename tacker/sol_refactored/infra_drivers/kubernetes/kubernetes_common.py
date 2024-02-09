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

import copy
import operator
import re

from oslo_log import log as logging
from oslo_service import loopingcall

from tacker.sol_refactored.common import config
from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.common import vnf_instance_utils as inst_utils
from tacker.sol_refactored.infra_drivers.kubernetes import kubernetes_resource
from tacker.sol_refactored.infra_drivers.kubernetes import kubernetes_utils
from tacker.sol_refactored.nfvo import nfvo_client
from tacker.sol_refactored import objects


LOG = logging.getLogger(__name__)

CONF = config.CONF
CHECK_INTERVAL = 10


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

    def _init_instantiated_vnf_info(self, inst, flavour_id,
            vdu_reses, namespace):
        metadata = {
            'namespace': namespace,
            'tenant': namespace,
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

    def diff_check_inst(self, inst, vim_info):
        inst_tmp = copy.deepcopy(inst)
        self.diff_check_and_update_vnfc(inst_tmp, vim_info)

    def diff_check_and_update_vnfc(self, vnf_instance, vim_info):
        with kubernetes_utils.AuthContextManager(vim_info) as acm:
            k8s_api_client = acm.init_k8s_api_client()
            old_pods_names = {
                vnfc.computeResource.resourceId for vnfc in
                vnf_instance.instantiatedVnfInfo.vnfcResourceInfo}
            self._update_vnfc_info(vnf_instance, k8s_api_client)
            new_pods_names = {
                vnfc.computeResource.resourceId for vnfc in
                vnf_instance.instantiatedVnfInfo.vnfcResourceInfo}
            if operator.eq(old_pods_names, new_pods_names):
                raise sol_ex.DbSyncNoDiff(
                    "There are no differences in Vnfc resources.")

    def sync_db(self, context, vnf_instance, vim_info):
        self.diff_check_and_update_vnfc(vnf_instance, vim_info)

        vdu_id_list = self._get_vdu_list(vnf_instance)
        for vdu_id in vdu_id_list:
            resource_type = ""
            resource_name = ""
            # get pod information
            for vnfc in vnf_instance.instantiatedVnfInfo.vnfcResourceInfo:
                if vnfc.vduId == vdu_id:
                    resource_type = (vnfc.computeResource
                                     .vimLevelResourceType)
                    resource_name = self._get_resource_name(
                        vnfc.computeResource.resourceId, resource_type)
                    break
            pod_resources_from_k8s = self._get_pod_information(
                resource_name, resource_type, vnf_instance, vim_info)

            vnfcs = [vnfc for vnfc in
                     vnf_instance.instantiatedVnfInfo.vnfcResourceInfo if
                     vnfc.vduId == vdu_id]
            replicas = vnf_instance.instantiatedVnfInfo.metadata[
                'vdu_reses'][vdu_id]['spec'].get('replicas')
            if replicas is not None:
                vnf_instance.instantiatedVnfInfo.metadata[
                    'vdu_reses'][vdu_id]['spec']['replicas'] = len(vnfcs)

            self._calc_scale_level(
                context, vnf_instance, vdu_id,
                len(pod_resources_from_k8s))

    def _calc_scale_level(self, context, vnf_instance,
            vdu_id, current_pod_num):
        """calc scale_level and set"""
        aspect_id = ""
        flavour_id = vnf_instance.instantiatedVnfInfo.flavourId
        client = nfvo_client.NfvoClient()
        vnfd = client.get_vnfd(context, vnf_instance.vnfdId)
        for aspect_delta in vnfd.get_policy_values_by_type(flavour_id,
                              'tosca.policies.nfv.VduScalingAspectDeltas'):
            if vdu_id in aspect_delta.get('targets', []):
                aspect_id = aspect_delta.get('properties', {}).get('aspect')
                break
        if not aspect_id:
            return

        delta = vnfd.get_scale_vdu_and_num(flavour_id, aspect_id).get(vdu_id)
        initial_delta = vnfd.get_initial_delta(flavour_id, vdu_id)

        if (current_pod_num - initial_delta) % delta != 0:
            raise sol_ex.DbSyncFailed(
                "Error computing 'scale_level'. current Pod num: "
                f"{current_pod_num} delta: {delta}. vnf: {vnf_instance.id} "
                f"vdu: {vdu_id}")

        scale_level = (current_pod_num - initial_delta) // delta

        for inst_vnf in vnf_instance.instantiatedVnfInfo.scaleStatus:
            if inst_vnf.aspectId == aspect_id:
                inst_vnf.scaleLevel = scale_level
                break

        self._check_pod_range(
            vnf_instance, vnfd, vdu_id, flavour_id, current_pod_num)

    def _check_pod_range(self, vnf_instance, vnfd, vdu_id,
            flavour_id, current_pod_num):
        """Check the range of the maximum or minimum number of pods.

        If it finds out of range, output a error log and do not update
        database.
        """
        vdu_profile = (vnfd.get_vdu_nodes(flavour_id)
                           .get(vdu_id, {})
                           .get("properties", {})
                           .get("vdu_profile", {}))
        max_number_of_instances = vdu_profile.get("max_number_of_instances")
        min_number_of_instances = vdu_profile.get("min_number_of_instances")

        if (current_pod_num > max_number_of_instances
                or current_pod_num < min_number_of_instances):
            raise sol_ex.DbSyncFailed(
                f"Failed to update database vnf {vnf_instance.id} "
                f"vdu: {vdu_id}. Pod num is out of range. "
                f"pod_num: {current_pod_num}")

    def _get_pod_information(self, resource_name,
            resource_type, vnf_instance, vim_connection_info):
        """Extract a Pod starting with the specified 'resource_name' name"""
        namespace = vnf_instance.instantiatedVnfInfo.metadata.get('namespace')
        if not namespace:
            namespace = "default"

        with kubernetes_utils.AuthContextManager(vim_connection_info) as acm:
            k8s_api_client = acm.init_k8s_api_client()
            all_pods = kubernetes_utils.list_namespaced_pods(
                k8s_api_client, namespace)

        resource_pods = {}

        for pod in all_pods:
            if self.is_match_pod_naming(resource_type,
                  resource_name, pod.metadata.name):
                resource_pods[pod.metadata.name] = pod.metadata.to_dict()
        return resource_pods

    def _get_vdu_list(self, vnf_instance):
        """get vdu_list"""
        vdu_id_list = set()

        for vnfc in vnf_instance.instantiatedVnfInfo.vnfcResourceInfo:
            vdu_id_list.add(vnfc.vduId)
        return vdu_id_list

    def _get_resource_name(self, resource_id, resource_type):
        """get resource name"""
        if resource_type == 'Pod':
            resource_name = resource_id
        else:
            name_list = resource_id.split("-")
            if resource_type == 'Deployment':
                del name_list[-2:]
            elif resource_type in ('ReplicaSet', 'DaemonSet', 'StatefulSet'):
                del name_list[-1]
            resource_name = '-'.join(name_list)

        return resource_name

    def is_match_pod_naming(self, rsc_kind, rsc_name, pod_name):
        match_result = None
        if rsc_kind == 'Pod':
            # Expected example: name
            if rsc_name == pod_name:
                return True
        elif rsc_kind == 'Deployment':
            # Expected example: name-012789abef-019az
            # NOTE(horie): The naming rule of Pod in deployment is
            # "(deployment name)-(pod template hash)-(5 charactors)".
            # The "pod template hash" string is generated from 32 bit hash.
            # This may be from 1 to 10 caracters but not sure the lower limit
            # from the source code of Kubernetes.
            match_result = re.match(
                rsc_name + '-([0-9a-f]{1,10})-([0-9a-z]{5})+$', pod_name)
        elif rsc_kind in ('ReplicaSet', 'DaemonSet'):
            # Expected example: name-019az
            match_result = re.match(rsc_name + '-([0-9a-z]{5})+$', pod_name)
        elif rsc_kind == 'StatefulSet':
            # Expected example: name-0
            match_result = re.match(rsc_name + '-[0-9]+$', pod_name)
        if match_result:
            return True

        return False
