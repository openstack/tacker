# Copyright (C) 2020 FUJITSU
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
import os
from unittest import mock

from tacker.common import exceptions
from tacker.tests.unit import base
from tacker.tests.unit import fake_request
from tacker.tests.unit.vnfm.infra_drivers.kubernetes import fakes
from tacker.vnfm.infra_drivers.kubernetes.k8s import tosca_kube_object
from tacker.vnfm.infra_drivers.kubernetes.k8s import translate_outputs


class TestTransformer(base.TestCase):
    def setUp(self):
        super(TestTransformer, self).setUp()
        self.yaml_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "kubernetes_api_resource/")
        self.k8s_client_dict = fakes.fake_k8s_client_dict()
        self.transfromer = translate_outputs.Transformer(
            client.CoreV1Api,
            client.AppsV1Api,
            client.AutoscalingApi,
            self.k8s_client_dict)

    def test_deploy_k8s_create_false(self):
        kubernetes_objects = []
        k8s_obj = fakes.fake_k8s_dict()
        kubernetes_objects.append(k8s_obj)
        self.assertRaises(exceptions.CreateApiFalse,
                          self.transfromer.deploy_k8s,
                          kubernetes_objects)

    @mock.patch.object(translate_outputs.Transformer,
                       "_select_k8s_client_and_api")
    def test_deploy_k8s(self, mock_k8s_client_and_api):
        req = fake_request.HTTPRequest.blank(
            'apis/apps/v1/namespaces/curryns/deployments')
        mock_k8s_client_and_api.return_value = req
        kubernetes_objects = []
        k8s_obj = fakes.fake_k8s_dict()
        kubernetes_objects.append(k8s_obj)
        new_k8s_objs = self.transfromer.deploy_k8s(kubernetes_objects)
        self.assertIsInstance(new_k8s_objs, list)
        self.assertIsNotNone(new_k8s_objs)
        self.assertEqual(new_k8s_objs[0]['status'], 'Creating')

    def test_deployment(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['deployment.yaml'], self.yaml_path, '')
        k8s_obj = k8s_objs[0].get('object')
        self.assertIsNotNone(k8s_obj)
        self.assertEqual(k8s_objs[0].get('namespace'), '')
        self.assertEqual(k8s_obj.kind, 'Deployment')
        self.assertEqual(k8s_obj.api_version, 'apps/v1')

        # V1DeploymentCondition
        self.assertEqual(k8s_obj.status.conditions[0].status, True)
        self.assertEqual(k8s_obj.status.conditions[0].type, 'Deployment')
        # V1DeploymentSpec
        self.assertIsNotNone(k8s_obj.spec.selector)
        self.assertIsNotNone(k8s_obj.spec.template)
        # V1LabelSelectorRequirement
        self.assertEqual(k8s_obj.spec.selector.
                         match_expressions[0].key, 'test')
        self.assertEqual(k8s_obj.spec.selector.
                         match_expressions[0].operator, 'test')

    def test_api_service(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['api-service.yaml'], self.yaml_path, ''
        )
        k8s_obj = k8s_objs[0].get('object')
        self.assertIsNotNone(k8s_obj)
        self.assertEqual(k8s_objs[0].get('namespace'), '')
        self.assertEqual(k8s_obj.kind, 'APIService')
        self.assertEqual(k8s_obj.api_version, 'apiregistration.k8s.io/v1')
        # V1APIServiceSpec
        self.assertEqual(k8s_obj.spec.group_priority_minimum, 17000)
        self.assertIsNotNone(k8s_obj.spec.service)
        self.assertEqual(k8s_obj.spec.version_priority, 5)

    def test_cluster_role(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['cluster-role.yaml'], self.yaml_path, ''
        )
        k8s_obj = k8s_objs[0].get('object')
        self.assertIsNotNone(k8s_obj)
        self.assertEqual(k8s_objs[0].get('namespace'), '')
        self.assertEqual(k8s_obj.kind, 'ClusterRole')
        self.assertEqual(k8s_obj.api_version, 'rbac.authorization.k8s.io/v1')
        # V1PolicyRule
        self.assertIsNotNone(k8s_obj.rules[0].verbs)

    def test_cluster_role_binding(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['cluster-role-binding.yaml'], self.yaml_path, ''
        )
        k8s_obj = k8s_objs[0].get('object')
        self.assertIsNotNone(k8s_obj)
        self.assertEqual(k8s_objs[0].get('namespace'), '')
        self.assertEqual(k8s_obj.kind, 'ClusterRoleBinding')
        self.assertEqual(k8s_obj.api_version, 'rbac.authorization.k8s.io/v1')
        # V1ClusterRoleBinding
        self.assertIsNotNone(k8s_obj.role_ref)
        # V1RoleRef
        self.assertEqual(k8s_obj.role_ref.api_group,
                         'rbac.authorization.k8s.io')
        self.assertEqual(k8s_obj.role_ref.kind, 'ClusterRole')
        self.assertEqual(k8s_obj.role_ref.name, 'curry-cluster-role')
        # V1Subject
        self.assertEqual(k8s_obj.subjects[0].kind, 'ServiceAccount')
        self.assertEqual(k8s_obj.subjects[0].name, 'curry-cluster-sa')

    def test_config_map(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['config-map.yaml'], self.yaml_path, 'curryns'
        )
        k8s_obj = k8s_objs[0].get('object')
        self.assertIsNotNone(k8s_obj)
        self.assertEqual(k8s_objs[0].get('namespace'), 'curryns')
        self.assertEqual(k8s_obj.kind, 'ConfigMap')
        self.assertEqual(k8s_obj.api_version, 'v1')

    def test_daemon_set(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['daemon-set.yaml'], self.yaml_path, ''
        )
        k8s_obj = k8s_objs[0].get('object')
        self.assertIsNotNone(k8s_obj)
        self.assertEqual(k8s_objs[0].get('namespace'), '')
        self.assertEqual(k8s_obj.kind, 'DaemonSet')
        self.assertEqual(k8s_obj.api_version, 'apps/v1')
        # V1DaemonSetStatus
        self.assertEqual(k8s_obj.status.current_number_scheduled, 1)
        self.assertEqual(k8s_obj.status.desired_number_scheduled, 1)
        self.assertEqual(k8s_obj.status.number_misscheduled, 1)
        self.assertEqual(k8s_obj.status.number_ready, 1)
        # V1DaemonSetCondition
        self.assertEqual(k8s_obj.status.conditions[0].status, True)
        self.assertEqual(k8s_obj.status.conditions[0].type, 'DaemonSet')
        # V1DaemonSetSpec
        self.assertIsNotNone(k8s_obj.spec.selector)
        self.assertIsNotNone(k8s_obj.spec.template)

    def test_horizontal_pod_autoscaler(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['horizontal-pod-autoscaler.yaml'], self.yaml_path, 'default'
        )
        k8s_obj = k8s_objs[0].get('object')
        self.assertIsNotNone(k8s_obj)
        self.assertEqual(k8s_objs[0].get('namespace'), 'default')
        self.assertEqual(k8s_obj.kind, 'HorizontalPodAutoscaler')
        self.assertEqual(k8s_obj.api_version, 'autoscaling/v1')
        # V1HorizontalPodAutoscalerSpec
        self.assertEqual(k8s_obj.spec.max_replicas, 3)
        self.assertIsNotNone(k8s_obj.spec.scale_target_ref)
        # V1CrossVersionObjectReference
        self.assertEqual(k8s_obj.spec.scale_target_ref.kind, 'Deployment')
        self.assertEqual(k8s_obj.spec.scale_target_ref.name,
                         'curry-svc-vdu001')
        # V1HorizontalPodAutoscalerStatus
        self.assertEqual(k8s_obj.status.current_replicas, 1)
        self.assertEqual(k8s_obj.status.desired_replicas, 1)

    def test_job(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['job.yaml'], self.yaml_path, ''
        )
        k8s_obj = k8s_objs[0].get('object')
        self.assertIsNotNone(k8s_obj)
        self.assertEqual(k8s_objs[0].get('namespace'), '')
        self.assertEqual(k8s_obj.kind, 'Job')
        self.assertEqual(k8s_obj.api_version, 'batch/v1')
        # V1JobCondition
        self.assertEqual(k8s_obj.status.conditions[0].status, True)
        self.assertEqual(k8s_obj.status.conditions[0].type, 'Job')
        # V1JobSpec
        self.assertIsNotNone(k8s_obj.spec.template)

    def test_lease(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['lease.yaml'], self.yaml_path, 'default'
        )
        k8s_obj = k8s_objs[0].get('object')
        self.assertIsNotNone(k8s_obj)
        self.assertEqual(k8s_objs[0].get('namespace'), 'default')
        self.assertEqual(k8s_obj.kind, 'Lease')
        self.assertEqual(k8s_obj.api_version, 'coordination.k8s.io/v1')

    def test_local_subject_access_review(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['local-subject-access-review.yaml'], self.yaml_path, 'curry-ns'
        )
        k8s_obj = k8s_objs[0].get('object')
        self.assertIsNotNone(k8s_obj)
        self.assertEqual(k8s_objs[0].get('namespace'), 'curry-ns')
        self.assertEqual(k8s_obj.kind, 'LocalSubjectAccessReview')
        self.assertEqual(k8s_obj.api_version, 'authorization.k8s.io/v1')
        self.assertIsNotNone(k8s_obj.spec)

    def test_namespace(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['namespace.yaml'], self.yaml_path, ''
        )
        k8s_obj = k8s_objs[0].get('object')
        self.assertIsNotNone(k8s_obj)
        self.assertEqual(k8s_objs[0].get('namespace'), '')
        self.assertEqual(k8s_obj.kind, 'Namespace')
        self.assertEqual(k8s_obj.api_version, 'v1')

        # V1NamespaceCondition
        self.assertEqual(k8s_obj.status.conditions[0].status, True)
        self.assertEqual(k8s_obj.status.conditions[0].type, 'Namespace')

    def test_network_policy(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['network-policy.yaml'], self.yaml_path, ''
        )
        k8s_obj = k8s_objs[0].get('object')
        self.assertIsNotNone(k8s_obj)
        self.assertEqual(k8s_objs[0].get('namespace'), '')
        self.assertEqual(k8s_obj.kind, 'NetworkPolicy')
        self.assertEqual(k8s_obj.api_version, 'networking.k8s.io/v1')

        # V1IPBlock
        self.assertEqual(k8s_obj.spec.egress[0].to[0].ip_block.cidr,
                         '10.0.0.0/24')
        # V1NetworkPolicySpec
        self.assertIsNotNone(k8s_obj.spec.pod_selector)

    def test_node(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['node.yaml'], self.yaml_path, ''
        )
        k8s_obj = k8s_objs[0].get('object')
        self.assertIsNotNone(k8s_obj)
        self.assertEqual(k8s_objs[0].get('namespace'), '')
        self.assertEqual(k8s_obj.kind, 'Node')
        self.assertEqual(k8s_obj.api_version, 'v1')

        # V1ConfigMapNodeConfigSource
        self.assertEqual(k8s_obj.spec.config_source.
                         config_map.kubelet_config_key, 'kubelet')
        self.assertEqual(k8s_obj.spec.config_source.
                         config_map.namespace, 'kube-system')
        self.assertEqual(k8s_obj.spec.config_source.
                         config_map.name, 'CONFIG_MAP_NAME')
        # V1Taint
        self.assertEqual(k8s_obj.spec.taints[0].key, 'test')
        self.assertEqual(k8s_obj.spec.taints[0].effect, 'test')
        # V1NodeAddress
        self.assertEqual(k8s_obj.status.addresses[0].address, '1.1.1.1')
        self.assertEqual(k8s_obj.status.addresses[0].type, 'test')
        # V1NodeCondition
        self.assertEqual(k8s_obj.status.conditions[0].status, True)
        self.assertEqual(k8s_obj.status.conditions[0].type, 'Node')
        # V1DaemonEndpoint
        self.assertEqual(k8s_obj.status.daemon_endpoints.
                         kubelet_endpoint.port, 8080)
        # V1ContainerImage
        self.assertEqual(k8s_obj.status.images[0].names, 'test')
        # V1NodeSystemInfo
        self.assertEqual(k8s_obj.status.node_info.architecture, 'test')
        self.assertEqual(k8s_obj.status.node_info.boot_id, 'test')
        self.assertEqual(k8s_obj.status.node_info.
                         container_runtime_version, 'test')
        self.assertEqual(k8s_obj.status.node_info.kube_proxy_version, 'test')
        self.assertEqual(k8s_obj.status.node_info.kubelet_version, 'test')
        self.assertEqual(k8s_obj.status.node_info.machine_id, 'test')
        self.assertEqual(k8s_obj.status.node_info.operating_system, 'test')
        self.assertEqual(k8s_obj.status.node_info.os_image, 'test')
        self.assertEqual(k8s_obj.status.node_info.system_uuid, 'test')
        # V1AttachedVolume
        self.assertEqual(k8s_obj.status.volumes_attached[0].
                         device_path, 'test')
        self.assertEqual(k8s_obj.status.volumes_attached[0].name, 'test')

    def test_persistent_volume(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['persistent-volume.yaml'], self.yaml_path, ''
        )
        k8s_obj = k8s_objs[0].get('object')
        self.assertIsNotNone(k8s_obj)
        self.assertEqual(k8s_objs[0].get('namespace'), '')
        self.assertEqual(k8s_obj.kind, 'PersistentVolume')
        self.assertEqual(k8s_obj.api_version, 'v1')
        # V1AzureFilePersistentVolumeSource
        self.assertEqual(k8s_obj.spec.azure_file.secret_name, 'azure-secret')
        self.assertEqual(k8s_obj.spec.azure_file.share_name, 'aksshare')
        # V1CephFSPersistentVolumeSource
        self.assertEqual(k8s_obj.spec.cephfs.monitors[0], '10.16.154.78:6789')
        # V1CinderPersistentVolumeSource
        self.assertEqual(k8s_obj.spec.cinder.volume_id,
                         '90d6900d-808f-4ddb-a30e-5ef821f58b4e')
        # V1CSIPersistentVolumeSource
        self.assertEqual(k8s_obj.spec.csi.driver, 'csi-nfsplugin')
        self.assertEqual(k8s_objs[0].get('object').spec.csi.volume_handle,
                         'data-id')
        # V1FlexPersistentVolumeSource
        self.assertEqual(k8s_objs[0].get('object').spec.flex_volume.driver,
                         'kubernetes.io/lvm')
        # V1GlusterfsPersistentVolumeSource
        self.assertEqual(k8s_objs[0].get('object').spec.glusterfs.endpoints,
                         'glusterfs-cluster')
        self.assertEqual(k8s_obj.spec.glusterfs.path, 'kube_vol')
        # V1ISCSIPersistentVolumeSource
        self.assertEqual(k8s_obj.spec.iscsi.target_portal, '10.0.2.15:3260')
        self.assertEqual(k8s_obj.spec.iscsi.iqn,
                         'iqn.2001-04.com.example:storage.kube.sys1.xyz')
        self.assertEqual(k8s_obj.spec.iscsi.lun, 0)
        # V1LocalVolumeSource
        self.assertEqual(k8s_obj.spec.local.path, '/mnt/disks/ssd1')
        # V1RBDPersistentVolumeSource
        self.assertEqual(k8s_obj.spec.rbd.monitors[0], '10.16.154.78:6789')
        self.assertEqual(k8s_obj.spec.rbd.image, 'foo')
        # V1ScaleIOPersistentVolumeSource
        self.assertEqual(k8s_obj.spec.scale_io.gateway,
                         'https://localhost:443/api')
        self.assertIsNotNone(k8s_obj.spec.scale_io.secret_ref)
        self.assertEqual(k8s_obj.spec.scale_io.system, 'scaleio')
        # V1AWSElasticBlockStoreVolumeSource
        self.assertEqual(k8s_obj.spec.aws_elastic_block_store.volume_id,
                         '123')
        # V1AzureDiskVolumeSource
        self.assertEqual(k8s_obj.spec.azure_disk.disk_name, 'test.vhd')
        self.assertEqual(
            k8s_obj.spec.azure_disk.disk_uri,
            'https://someaccount.blob.microsoft.net/vhds/test.vhd')

    def test_persistent_volume_claim(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['persistent-volume-claim.yaml'], self.yaml_path, ''
        )
        k8s_obj = k8s_objs[0].get('object')
        self.assertIsNotNone(k8s_obj)
        self.assertEqual(k8s_objs[0].get('namespace'), '')
        self.assertEqual(k8s_obj.kind, 'PersistentVolumeClaim')
        self.assertEqual(k8s_obj.api_version, 'v1')
        # V1PersistentVolumeClaimCondition
        self.assertEqual(k8s_obj.status.conditions[0].status, True)
        self.assertEqual(k8s_obj.status.conditions[0].type,
                         'PersistentVolumeClaim')
        # V1TypedLocalObjectReference
        self.assertEqual(k8s_obj.spec.data_source.name,
                         'existing-src-pvc-name')
        self.assertEqual(k8s_obj.spec.data_source.kind,
                         'PersistentVolumeClaim')

    def test_pod(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['pod.yaml'], self.yaml_path, ''
        )
        k8s_obj = k8s_objs[0].get('object')
        self.assertIsNotNone(k8s_obj)
        self.assertEqual(k8s_objs[0].get('namespace'), '')
        self.assertEqual(k8s_obj.kind, 'Pod')
        self.assertEqual(k8s_obj.api_version, 'v1')
        # V1NodeSelector
        self.assertIsNotNone(
            k8s_obj.spec.affinity.node_affinity.
            required_during_scheduling_ignored_during_execution.
            node_selector_terms)
        # V1NodeSelectorRequirement
        self.assertEqual(
            k8s_obj.spec.affinity.node_affinity.
            required_during_scheduling_ignored_during_execution.
            node_selector_terms[0].match_expressions[0].key,
            'kubernetes.io/e2e-az-name')
        self.assertEqual(
            k8s_obj.spec.affinity.node_affinity.
            required_during_scheduling_ignored_during_execution.
            node_selector_terms[0].match_expressions[0].operator,
            'In')
        # V1PreferredSchedulingTerm
        self.assertEqual(
            k8s_obj.spec.affinity.node_affinity.
            preferred_during_scheduling_ignored_during_execution[0].
            weight, 1)
        self.assertIsNotNone(
            k8s_obj.spec.affinity.node_affinity.
            preferred_during_scheduling_ignored_during_execution[0].
            preference)
        # V1PodAffinityTerm
        self.assertEqual(
            k8s_obj.spec.affinity.pod_anti_affinity.
            preferred_during_scheduling_ignored_during_execution[0].
            pod_affinity_term.topology_key, 'topology.kubernetes.io/zone')
        # V1WeightedPodAffinityTerm
        self.assertEqual(
            k8s_obj.spec.affinity.pod_anti_affinity.
            preferred_during_scheduling_ignored_during_execution[0].
            weight, 100)
        self.assertIsNotNone(
            k8s_obj.spec.affinity.pod_anti_affinity.
            preferred_during_scheduling_ignored_during_execution[0].
            pod_affinity_term)
        # V1OwnerReference
        self.assertEqual(k8s_obj.metadata.owner_references[0].api_version,
                         'apps/v1')
        self.assertEqual(k8s_obj.metadata.owner_references[0].kind,
                         'ReplicaSet')
        self.assertEqual(k8s_obj.metadata.owner_references[0].name,
                         'my-repset')
        self.assertEqual(k8s_obj.metadata.owner_references[0].uid,
                         'd9607e19-f88f-11e6-a518-42010a800195')
        # V1HTTPHeader
        self.assertEqual(k8s_obj.spec.containers[0].liveness_probe.http_get.
                         http_headers[0].name, 'Custom-Header')
        self.assertEqual(k8s_obj.spec.containers[0].liveness_probe.http_get.
                         http_headers[0].value, 'Awesome')
        # V1TCPSocketAction
        self.assertEqual(k8s_obj.spec.containers[0].liveness_probe.
                         tcp_socket.port, 8080)
        # V1VolumeDevice
        self.assertEqual(k8s_obj.spec.containers[0].volume_devices[0].
                         device_path, '/dev/xvda')
        self.assertEqual(k8s_obj.spec.containers[0].volume_devices[0].name,
                         'data')
        # V1PodReadinessGate
        self.assertEqual(k8s_obj.spec.readiness_gates[0].condition_type,
                         'www.example.com/feature-1')
        # V1Sysctl
        self.assertEqual(k8s_obj.spec.security_context.sysctls[0].name,
                         'kernel.shm_rmid_forced')
        self.assertEqual(k8s_obj.spec.security_context.sysctls[0].value, '0')
        # V1ContainerStateTerminated
        self.assertEqual(k8s_obj.status.container_statuses[0].last_state.
                         terminated.exit_code, 1)
        # V1EphemeralContainer
        self.assertEqual(k8s_obj.spec.topology_spread_constraints[0].
                         topology_key, 'zone')
        # V1TopologySpreadConstraint
        self.assertEqual(k8s_obj.spec.ephemeral_containers[0].name,
                         'debugger')
        # V1HTTPGetAction
        self.assertEqual(k8s_obj.spec.containers[0].liveness_probe.
                         http_get.port, 8080)
        # V1ConfigMapKeySelector
        self.assertEqual(k8s_obj.spec.containers[0].env[0].value_from.
                         config_map_key_ref.key, 'test')
        # V1EnvVar
        self.assertEqual(k8s_obj.spec.containers[0].env[0].name, 'test')
        # V1SecretKeySelector
        self.assertEqual(k8s_obj.spec.containers[0].env[0].value_from.
                         secret_key_ref.key, 'test')
        # V1ContainerPort
        self.assertEqual(k8s_obj.spec.containers[0].ports[0].
                         container_port, 8080)
        # V1VolumeMount
        self.assertEqual(k8s_obj.spec.containers[0].volume_mounts[0].
                         mount_path, '/data/redis')
        self.assertEqual(k8s_obj.spec.containers[0].volume_mounts[0].
                         name, 'redis-storage')
        # V1PodCondition
        self.assertEqual(k8s_obj.status.conditions[0].status, True)
        self.assertEqual(k8s_obj.status.conditions[0].type, 'Pod')
        # V1ContainerStatus
        self.assertEqual(k8s_obj.status.container_statuses[0].image, 'test')
        self.assertEqual(k8s_obj.status.container_statuses[0].image_id, 123)
        self.assertEqual(k8s_obj.status.container_statuses[0].name, 'test')
        self.assertEqual(k8s_obj.status.container_statuses[0].ready, True)
        self.assertEqual(k8s_obj.status.container_statuses[0].restart_count, 1)

    def test_priority_class(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['priority-class.yaml'], self.yaml_path, ''
        )
        k8s_obj = k8s_objs[0].get('object')
        self.assertIsNotNone(k8s_obj)
        self.assertEqual(k8s_objs[0].get('namespace'), '')
        self.assertEqual(k8s_obj.kind, 'PriorityClass')
        self.assertEqual(k8s_obj.api_version, 'scheduling.k8s.io/v1')
        # V1PriorityClass
        self.assertEqual(k8s_obj.value, 1000000)

    def test_replica_set(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['replica-set.yaml'], self.yaml_path, ''
        )
        k8s_obj = k8s_objs[0].get('object')
        self.assertIsNotNone(k8s_obj)
        self.assertEqual(k8s_objs[0].get('namespace'), '')
        self.assertEqual(k8s_obj.kind, 'ReplicaSet')
        self.assertEqual(k8s_obj.api_version, 'apps/v1')

        # V1ReplicaSetStatus
        self.assertEqual(k8s_obj.status.replicas, 1)
        # V1ReplicaSetCondition
        self.assertEqual(k8s_obj.status.conditions[0].status, True)
        self.assertEqual(k8s_obj.status.conditions[0].type, 'ReplicaSet')
        # V1ReplicaSetSpec
        self.assertIsNotNone(k8s_obj.spec.selector)
        self.assertIsNotNone(k8s_obj.spec.template)

    def test_resource_quota(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['resource-quota.yaml'], self.yaml_path, 'curryns'
        )
        k8s_obj = k8s_objs[0].get('object')
        self.assertIsNotNone(k8s_obj)
        self.assertEqual(k8s_objs[0].get('namespace'), 'curryns')
        self.assertEqual(k8s_obj.kind, 'ResourceQuota')
        self.assertEqual(k8s_obj.api_version, 'v1')
        # V1ScopedResourceSelectorRequirement
        self.assertEqual(k8s_obj.spec.scope_selector.
                         match_expressions[0].operator, 'In')
        self.assertEqual(k8s_obj.spec.scope_selector.
                         match_expressions[0].scope_name, 'PriorityClass')

    def test_role(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['role.yaml'], self.yaml_path, 'curry-ns'
        )
        k8s_obj = k8s_objs[0].get('object')
        self.assertIsNotNone(k8s_obj)
        self.assertEqual(k8s_objs[0].get('namespace'), 'curry-ns')
        self.assertEqual(k8s_obj.kind, 'Role')
        self.assertEqual(k8s_obj.api_version, 'rbac.authorization.k8s.io/v1')

    def test_role_binding(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['role-bindings.yaml'], self.yaml_path, 'curry-ns'
        )
        k8s_obj = k8s_objs[0].get('object')
        self.assertIsNotNone(k8s_obj)
        self.assertEqual(k8s_objs[0].get('namespace'), 'curry-ns')
        self.assertEqual(k8s_obj.kind, 'RoleBinding')
        self.assertEqual(k8s_obj.api_version, 'rbac.authorization.k8s.io/v1')
        # V1RoleBinding
        self.assertIsNotNone(k8s_obj.role_ref)

    def test_secret(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['secret.yaml'], self.yaml_path, 'default'
        )
        k8s_obj = k8s_objs[0].get('object')
        self.assertIsNotNone(k8s_obj)
        self.assertEqual(k8s_objs[0].get('namespace'), 'default')
        self.assertEqual(k8s_obj.kind, 'Secret')
        self.assertEqual(k8s_obj.api_version, 'v1')

    def test_self_subject_access_review(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['self-subject-access-review.yaml'], self.yaml_path, ''
        )
        k8s_obj = k8s_objs[0].get('object')
        self.assertIsNotNone(k8s_obj)
        self.assertEqual(k8s_objs[0].get('namespace'), '')
        self.assertEqual(k8s_obj.kind, 'SelfSubjectAccessReview')
        self.assertEqual(k8s_obj.api_version, 'authorization.k8s.io/v1')
        # V1SelfSubjectAccessReview
        self.assertIsNotNone(k8s_obj.spec)

    def test_self_subject_rules_review(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['self-subject-rule-review.yaml'], self.yaml_path, ''
        )
        k8s_obj = k8s_objs[0].get('object')
        self.assertIsNotNone(k8s_obj)
        self.assertEqual(k8s_objs[0].get('namespace'), '')
        self.assertEqual(k8s_obj.kind, 'SelfSubjectRulesReview')
        self.assertEqual(k8s_obj.api_version, 'authorization.k8s.io/v1')
        # V1ResourceRule
        self.assertEqual(k8s_obj.status.resource_rules[0].verbs[0], 'test')
        # V1SelfSubjectRulesReview
        self.assertIsNotNone(k8s_obj.spec)
        # V1SubjectRulesReviewStatus
        self.assertIsNotNone(k8s_obj.status.resource_rules)
        self.assertIsNotNone(k8s_obj.status.non_resource_rules)
        self.assertEqual(k8s_obj.status.incomplete, True)
        # V1NonResourceRule
        self.assertEqual(k8s_obj.status.non_resource_rules[0].verbs[0], 'test')

    def test_service(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['service.yaml'], self.yaml_path, 'default'
        )
        k8s_obj = k8s_objs[0].get('object')
        self.assertIsNotNone(k8s_obj)
        self.assertEqual(k8s_objs[0].get('namespace'), 'default')
        self.assertEqual(k8s_obj.kind, 'Service')
        self.assertEqual(k8s_obj.api_version, 'v1')
        # V1ServicePort
        self.assertEqual(k8s_obj.spec.ports[0].port, 80)

    def test_service_account(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['service-account.yaml'], self.yaml_path, 'default'
        )
        k8s_obj = k8s_objs[0].get('object')
        self.assertIsNotNone(k8s_obj)
        self.assertEqual(k8s_objs[0].get('namespace'), 'default')
        self.assertEqual(k8s_obj.kind, 'ServiceAccount')
        self.assertEqual(k8s_obj.api_version, 'v1')

    def test_stateful_set(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['stateful-set.yaml'], self.yaml_path, ''
        )
        k8s_obj = k8s_objs[0].get('object')
        self.assertIsNotNone(k8s_obj)
        self.assertEqual(k8s_objs[0].get('namespace'), '')
        self.assertEqual(k8s_obj.kind, 'StatefulSet')
        self.assertEqual(k8s_obj.api_version, 'apps/v1')
        # V1StatefulSetSpec
        self.assertIsNotNone(k8s_obj.spec.selector)
        self.assertIsNotNone(k8s_obj.spec.template)
        self.assertEqual(k8s_obj.spec.service_name, 'nginx')
        # V1StatefulSetCondition
        self.assertEqual(k8s_obj.status.conditions[0].status, True)
        self.assertEqual(k8s_obj.status.conditions[0].type, 'StatefulSet')
        # V1StatefulSetStatus
        self.assertEqual(k8s_obj.status.replicas, 1)

    def test_storage_class(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['storage-class.yaml'], self.yaml_path, ''
        )
        k8s_obj = k8s_objs[0].get('object')
        self.assertIsNotNone(k8s_obj)
        self.assertEqual(k8s_objs[0].get('namespace'), '')
        self.assertEqual(k8s_obj.kind, 'StorageClass')
        self.assertEqual(k8s_obj.api_version, 'storage.k8s.io/v1')
        # V1StorageClass
        self.assertEqual(k8s_obj.provisioner, 'kubernetes.io/no-provisioner')
        # V1TopologySelectorLabelRequirement
        self.assertEqual(k8s_obj.allowed_topologies[0].
                         match_label_expressions[0].key,
                         'failure-domain.beta.kubernetes.io/zone')
        self.assertEqual(k8s_obj.allowed_topologies[0].
                         match_label_expressions[0].values[0],
                         'us-central1-a')

    def test_subject_access_review(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['subject-access-review.yaml'], self.yaml_path, ''
        )
        k8s_obj = k8s_objs[0].get('object')
        self.assertIsNotNone(k8s_obj)
        self.assertEqual(k8s_objs[0].get('namespace'), '')
        self.assertEqual(k8s_obj.kind, 'SubjectAccessReview')
        self.assertEqual(k8s_obj.api_version, 'authorization.k8s.io/v1')
        # V1SubjectAccessReviewStatus
        self.assertEqual(k8s_obj.status.allowed, True)
        # V1SubjectAccessReview
        self.assertIsNotNone(k8s_obj.spec)

    def test_token_review(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['token-review.yaml'], self.yaml_path, ''
        )
        k8s_obj = k8s_objs[0].get('object')
        self.assertIsNotNone(k8s_obj)
        self.assertEqual(k8s_objs[0].get('namespace'), '')
        self.assertEqual(k8s_obj.kind, 'TokenReview')
        self.assertEqual(k8s_obj.api_version, 'authentication.k8s.io/v1')
        # V1TokenReview
        self.assertIsNotNone(k8s_obj.spec)

    def test_limit_range(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['limit-range.yaml'], self.yaml_path, 'curryns'
        )
        k8s_obj = k8s_objs[0].get('object')
        self.assertIsNotNone(k8s_obj)
        self.assertEqual(k8s_objs[0].get('namespace'), 'curryns')
        self.assertEqual(k8s_obj.kind, 'LimitRange')
        self.assertEqual(k8s_obj.api_version, 'v1')
        # V1LimitRangeSpec
        self.assertIsNotNone(k8s_obj.spec.limits)
        self.assertIsNotNone(k8s_obj.spec.limits[0].type)

    def test_pod_template(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['pod-template.yaml'], self.yaml_path, 'curryns'
        )
        k8s_obj = k8s_objs[0].get('object')
        self.assertIsNotNone(k8s_obj)
        self.assertEqual(k8s_objs[0].get('namespace'), 'curryns')
        self.assertEqual(k8s_obj.kind, 'PodTemplate')
        self.assertEqual(k8s_obj.api_version, 'v1')
        # V1AzureFileVolumeSource
        self.assertEqual(k8s_obj.template.spec.volumes[0].
                         azure_file.secret_name, 'azure-secret')
        # V1CephFSVolumeSource
        self.assertEqual(
            k8s_obj.template.spec.volumes[0].cephfs.monitors[0],
            '10.16.154.78:6789')
        # V1CinderVolumeSource
        self.assertEqual(
            k8s_obj.template.spec.volumes[0].cinder.volume_id,
            '90d6900d-808f-4ddb-a30e-5ef821f58b4e')
        # V1KeyToPath
        self.assertEqual(
            k8s_obj.template.spec.volumes[0].config_map.items[0].key,
            'log_level')
        self.assertEqual(
            k8s_obj.template.spec.volumes[0].config_map.items[0].path,
            'log_level')
        # V1CSIVolumeSource
        self.assertEqual(k8s_obj.template.spec.volumes[0].csi.driver,
                         'csi-nfsplugin')
        # V1DownwardAPIVolumeFile
        self.assertEqual(k8s_obj.template.spec.volumes[0].
                         downward_api.items[0].path, 'labels')
        # V1ObjectFieldSelector
        self.assertEqual(
            k8s_obj.template.spec.volumes[0].downward_api.items[0].
            field_ref.field_path, 'metadata.labels')
        # V1ResourceFieldSelector
        self.assertEqual(
            k8s_obj.template.spec.volumes[0].downward_api.items[0].
            resource_field_ref.resource, 'limits.cpu')
        # V1FlexVolumeSource
        self.assertEqual(
            k8s_obj.template.spec.volumes[0].flex_volume.driver,
            'kubernetes.io/lvm')
        # V1GCEPersistentDiskVolumeSource
        self.assertEqual(
            k8s_obj.template.spec.volumes[0].
            gce_persistent_disk.pd_name, 'my-data-disk')
        # V1GitRepoVolumeSource
        self.assertEqual(
            k8s_obj.template.spec.volumes[0].
            git_repo.repository, 'git@somewhere:me/my-git-repository.git')
        # V1GlusterfsVolumeSource
        self.assertEqual(
            k8s_obj.template.spec.volumes[0].glusterfs.endpoints,
            'glusterfs-cluster')
        self.assertEqual(
            k8s_obj.template.spec.volumes[0].glusterfs.path,
            'kube_vol')
        # V1HostPathVolumeSource
        self.assertEqual(
            k8s_obj.template.spec.volumes[0].host_path.path,
            '/var/local/aaa')
        # V1ISCSIVolumeSource
        self.assertEqual(
            k8s_obj.template.spec.volumes[0].iscsi.target_portal,
            '10.0.2.15:3260')
        self.assertEqual(
            k8s_obj.template.spec.volumes[0].iscsi.iqn,
            'iqn.2001-04.com.example:storage.kube.sys1.xyz')
        self.assertEqual(k8s_obj.template.spec.volumes[0].iscsi.lun, 0)
        # V1Volume
        self.assertEqual(k8s_obj.template.spec.volumes[0].name,
                         'curry-claim-volume')
        # V1NFSVolumeSource
        self.assertEqual(k8s_obj.template.spec.volumes[0].nfs.path, '/')
        self.assertEqual(
            k8s_obj.template.spec.volumes[0].nfs.server,
            'nfs-server.default.svc.cluster.local')
        # V1PersistentVolumeClaimVolumeSource
        self.assertEqual(
            k8s_obj.template.spec.volumes[0].
            persistent_volume_claim.claim_name, 'curry-pv-claim')
        # V1PhotonPersistentDiskVolumeSource
        self.assertEqual(
            k8s_obj.template.spec.volumes[0].
            photon_persistent_disk.pd_id, 'test')
        # V1PortworxVolumeSource
        self.assertEqual(
            k8s_obj.template.spec.volumes[0].
            portworx_volume.volume_id, 'pxvol')
        # V1ProjectedVolumeSource
        self.assertIsNotNone(k8s_obj.template.spec.volumes[0].
                             projected.sources)
        # V1QuobyteVolumeSource
        self.assertIsNotNone(
            k8s_obj.template.spec.volumes[0].
            quobyte.registry, 'test')
        self.assertIsNotNone(
            k8s_obj.template.spec.volumes[0].
            quobyte.volume, 'test')
        # V1RBDVolumeSource
        self.assertEqual(
            k8s_obj.template.spec.volumes[0].rbd.monitors[0],
            '10.16.154.78:6789')
        self.assertEqual(k8s_obj.template.spec.volumes[0].rbd.image, 'foo')
        # V1ScaleIOVolumeSource
        self.assertEqual(
            k8s_obj.template.spec.volumes[0].scale_io.gateway,
            'https://localhost:443/api')
        self.assertIsNotNone(
            k8s_obj.template.spec.volumes[0].scale_io.secret_ref)
        self.assertEqual(
            k8s_obj.template.spec.volumes[0].scale_io.system, 'scaleio')
        # V1VsphereVirtualDiskVolumeSource
        self.assertEqual(
            k8s_obj.template.spec.volumes[0].vsphere_volume.
            volume_path, '[DatastoreName] volumes/myDisk')
        # V1ServiceAccountTokenProjection
        self.assertEqual(
            k8s_obj.template.spec.volumes[0].
            projected.sources[0].service_account_token.path, 'test')

    def test_volume_attachment(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['volume-attachment.yaml'], self.yaml_path, 'curryns'
        )
        k8s_obj = k8s_objs[0].get('object')
        self.assertIsNotNone(k8s_obj)
        self.assertEqual(k8s_objs[0].get('namespace'), 'curryns')
        self.assertEqual(k8s_obj.kind, 'VolumeAttachment')
        self.assertEqual(k8s_obj.api_version, 'storage.k8s.io/v1')
        # V1VolumeAttachment
        self.assertIsNotNone(k8s_obj.spec)
        # V1VolumeAttachmentSpec
        self.assertEqual(k8s_obj.spec.attacher, 'nginx')
        self.assertEqual(k8s_obj.spec.node_name, 'nginx')
        self.assertIsNotNone(k8s_obj.spec.source)
        # V1VolumeAttachmentStatus
        self.assertEqual(k8s_obj.status.attached, True)

    def test_bindings(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['bindings.yaml'], self.yaml_path, 'curryns'
        )
        k8s_obj = k8s_objs[0].get('object')
        self.assertIsNotNone(k8s_obj)
        self.assertEqual(k8s_objs[0].get('namespace'), 'curryns')
        self.assertEqual(k8s_obj.kind, 'Binding')
        self.assertEqual(k8s_obj.api_version, 'v1')
        # V1Binding
        self.assertIsNotNone(k8s_obj.target)

    def test_controller_revision(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['controller-revision.yaml'], self.yaml_path, 'curryns'
        )
        k8s_obj = k8s_objs[0].get('object')
        self.assertIsNotNone(k8s_obj)
        self.assertEqual(k8s_objs[0].get('namespace'), 'curryns')
        self.assertEqual(k8s_obj.kind, 'ControllerRevision')
        self.assertEqual(k8s_obj.api_version, 'apps/v1')
        # V1ControllerRevision
        self.assertEqual(k8s_obj.revision, 1)

    def test_transform(self):
        container_obj = tosca_kube_object.Container(
            config='config:abc\nconfig2:bcd',
            num_cpus=2,
            mem_size=10,
            name='container'
        )
        tosca_kube_objects = [tosca_kube_object.ToscaKubeObject(
            namespace='namespace',
            name='name',
            containers=[container_obj],
            mapping_ports=["123"],
            labels={}
        )]
        kubernetes_objects = self.transfromer.transform(tosca_kube_objects)
        self.assertEqual(kubernetes_objects['namespace'], 'namespace')
        self.assertEqual(
            kubernetes_objects['objects'][0].data, {
                'config': 'abc', 'config2': 'bcd'})

    @mock.patch.object(client.CoreV1Api, 'create_namespaced_config_map')
    @mock.patch.object(client.AppsV1Api, 'create_namespaced_deployment')
    @mock.patch.object(client.CoreV1Api, 'create_namespaced_service')
    def test_deploy(
            self,
            mock_create_namespaced_config_map,
            mock_create_namespaced_deployment,
            mock_create_namespaced_service):
        mock_create_namespaced_config_map.return_value = ""
        mock_create_namespaced_deployment.return_value = ""
        mock_create_namespaced_service.return_value = ""
        container_obj = tosca_kube_object.Container(
            config='config:abc\nconfig2:bcd',
            num_cpus=2,
            mem_size=10,
            name='container'
        )
        tosca_kube_objects = [tosca_kube_object.ToscaKubeObject(
            namespace='namespace',
            name='name',
            containers=[container_obj],
            mapping_ports=["123"],
            labels={}
        )]
        kubernetes_objects = self.transfromer.transform(tosca_kube_objects)
        result = self.transfromer.deploy(kubernetes_objects)
        self.assertEqual(result, 'namespace,name')
