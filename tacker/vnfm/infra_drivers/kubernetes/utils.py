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

"""Utilities and helper functions."""

from oslo_log import log as logging

from tacker.common import exceptions
from tacker import objects
from tacker.objects import fields

LOG = logging.getLogger(__name__)

supported_k8s_resource_kinds = {
    "Pod",
    "Binding",
    "ConfigMap",
    "LimitRange",
    "PersistentVolumeClaim",
    "PodTemplate",
    "ResourceQuota",
    "Secret",
    "ServiceAccount",
    "Service",
    "ControllerRevision",
    "DaemonSet",
    "Deployment",
    "ReplicaSet",
    "StatefulSet",
    "LocalSubjectAccessReview",
    "HorizontalPodAutoscaler",
    "Job",
    "Lease",
    "NetworkPolicy",
    "RoleBinding",
    "Role"
}


def check_and_save_namespace(
        instantiate_vnf_req, chk_namespaces, vnf_instance):
    namespace = ''
    if instantiate_vnf_req.additional_params:
        namespace = instantiate_vnf_req.additional_params.get('namespace', '')
    if not namespace:
        try:
            namespace = get_namespace_from_manifests(chk_namespaces)
        except exceptions.NamespaceIsNotUnique as e:
            LOG.error(e)
            raise e
    if not namespace:
        namespace = 'default'

    if not vnf_instance.vnf_metadata:
        vnf_instance.vnf_metadata = {}
    vnf_instance.vnf_metadata['namespace'] = namespace
    vnf_instance.vnf_metadata['tenant'] = namespace
    vnf_instance.save()


def get_namespace_from_manifests(chk_namespaces):
    namespaces = {
        chk_namespace['namespace'] for chk_namespace in
        chk_namespaces if (chk_namespace['kind'] in
                           supported_k8s_resource_kinds)
    }

    if len(namespaces) > 1:
        LOG.error(f'Multiple namespaces found: {namespaces}')
        raise exceptions.NamespaceIsNotUnique()

    if namespaces:
        return namespaces.pop()
    return None


def is_lcmocc_failure_status(context, inst_id):
    filters = {'field': 'vnf_instance_id', 'model': 'VnfLcmOpOccs',
               'value': inst_id, 'op': '=='}
    vnf_lcm_op_occs = objects.VnfLcmOpOccList.get_by_filters(
        context, read_deleted='no', filters=filters)

    failed_temp_lcmoccs = [
        lcmocc for lcmocc in vnf_lcm_op_occs.objects if
        lcmocc.operation_state == fields.LcmOccsOperationState.FAILED_TEMP]
    failed_lcmocc = [
        latest_lcmocc for latest_lcmocc in vnf_lcm_op_occs.objects
        if latest_lcmocc.start_time == max(
            [lcmocc.start_time for lcmocc in vnf_lcm_op_occs.objects])]

    if failed_temp_lcmoccs or (failed_lcmocc[0].operation_state ==
                               fields.LcmOccsOperationState.FAILED):
        return True

    return False
