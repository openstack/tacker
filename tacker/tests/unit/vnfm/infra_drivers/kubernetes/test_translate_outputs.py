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

import os
from unittest import mock

from tacker.common import exceptions
from tacker.tests.unit import base
from tacker.tests.unit import fake_request
from tacker.tests.unit.vnfm.infra_drivers.kubernetes import fakes
from tacker.vnfm.infra_drivers.kubernetes.k8s import translate_outputs


class TestTransformer(base.TestCase):
    def setUp(self):
        super(TestTransformer, self).setUp()
        self.yaml_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "kubernetes_api_resource/")
        self.k8s_client_dict = fakes.fake_k8s_client_dict()
        self.transfromer = translate_outputs.Transformer(
            None, None, None, self.k8s_client_dict
        )

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
        req = \
            fake_request.HTTPRequest.blank(
                'apis/apps/v1/namespaces/curryns/deployments')
        mock_k8s_client_and_api.return_value = req
        kubernetes_objects = []
        k8s_obj = fakes.fake_k8s_dict()
        kubernetes_objects.append(k8s_obj)
        new_k8s_objs = self.transfromer.deploy_k8s(kubernetes_objects)
        self.assertEqual(type(new_k8s_objs), list)
        self.assertIsNotNone(new_k8s_objs)
        self.assertEqual(new_k8s_objs[0]['status'], 'Creating')

    def test_deployment(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['deployment.yaml'], self.yaml_path
        )
        self.assertIsNotNone(k8s_objs[0].get('object'))
        self.assertEqual(k8s_objs[0].get('namespace'), '')
        self.assertEqual(k8s_objs[0].get('object').kind, 'Deployment')
        self.assertEqual(k8s_objs[0].get('object').api_version, 'apps/v1')

    def test_api_service(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['api-service.yaml'], self.yaml_path
        )
        self.assertIsNotNone(k8s_objs[0].get('object'))
        self.assertEqual(k8s_objs[0].get('namespace'), '')
        self.assertEqual(k8s_objs[0].get('object').kind, 'APIService')
        self.assertEqual(k8s_objs[0].get('object').api_version,
                         'apiregistration.k8s.io/v1')

    def test_cluster_role(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['cluster-role.yaml'], self.yaml_path
        )
        self.assertIsNotNone(k8s_objs[0].get('object'))
        self.assertEqual(k8s_objs[0].get('namespace'), '')
        self.assertEqual(k8s_objs[0].get('object').kind, 'ClusterRole')
        self.assertEqual(k8s_objs[0].get('object').api_version,
                         'rbac.authorization.k8s.io/v1')

    def test_cluster_role_binding(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['cluster-role-binding.yaml'], self.yaml_path
        )
        self.assertIsNotNone(k8s_objs[0].get('object'))
        self.assertEqual(k8s_objs[0].get('namespace'), '')
        self.assertEqual(k8s_objs[0].get('object').kind,
                         'ClusterRoleBinding')
        self.assertEqual(k8s_objs[0].get('object').api_version,
                         'rbac.authorization.k8s.io/v1')

    def test_config_map(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['config-map.yaml'], self.yaml_path
        )
        self.assertIsNotNone(k8s_objs[0].get('object'))
        self.assertEqual(k8s_objs[0].get('namespace'), 'curryns')
        self.assertEqual(k8s_objs[0].get('object').kind,
                         'ConfigMap')
        self.assertEqual(k8s_objs[0].get('object').api_version, 'v1')

    def test_daemon_set(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['daemon-set.yaml'], self.yaml_path
        )
        self.assertIsNotNone(k8s_objs[0].get('object'))
        self.assertEqual(k8s_objs[0].get('namespace'), '')
        self.assertEqual(k8s_objs[0].get('object').kind,
                         'DaemonSet')
        self.assertEqual(k8s_objs[0].get('object').api_version, 'apps/v1')

    def test_horizontal_pod_autoscaler(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['horizontal-pod-autoscaler.yaml'], self.yaml_path
        )
        self.assertIsNotNone(k8s_objs[0].get('object'))
        self.assertEqual(k8s_objs[0].get('namespace'), 'default')
        self.assertEqual(k8s_objs[0].get('object').kind,
                         'HorizontalPodAutoscaler')
        self.assertEqual(k8s_objs[0].get('object').api_version,
                         'autoscaling/v1')

    def test_job(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['job.yaml'], self.yaml_path
        )
        self.assertIsNotNone(k8s_objs[0].get('object'))
        self.assertEqual(k8s_objs[0].get('namespace'), '')
        self.assertEqual(k8s_objs[0].get('object').kind, 'Job')
        self.assertEqual(k8s_objs[0].get('object').api_version,
                         'batch/v1')

    def test_lease(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['lease.yaml'], self.yaml_path
        )
        self.assertIsNotNone(k8s_objs[0].get('object'))
        self.assertEqual(k8s_objs[0].get('namespace'), 'default')
        self.assertEqual(k8s_objs[0].get('object').kind, 'Lease')
        self.assertEqual(k8s_objs[0].get('object').api_version,
                         'coordination.k8s.io/v1')

    def test_local_subject_access_review(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['local-subject-access-review.yaml'], self.yaml_path
        )
        self.assertIsNotNone(k8s_objs[0].get('object'))
        self.assertEqual(k8s_objs[0].get('namespace'), 'curry-ns')
        self.assertEqual(k8s_objs[0].get('object').kind,
                         'LocalSubjectAccessReview')
        self.assertEqual(k8s_objs[0].get('object').api_version,
                         'authorization.k8s.io/v1')

    def test_namespace(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['namespace.yaml'], self.yaml_path
        )
        self.assertIsNotNone(k8s_objs[0].get('object'))
        self.assertEqual(k8s_objs[0].get('namespace'), '')
        self.assertEqual(k8s_objs[0].get('object').kind, 'Namespace')
        self.assertEqual(k8s_objs[0].get('object').api_version, 'v1')

    def test_network_policy(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['network-policy.yaml'], self.yaml_path
        )
        self.assertIsNotNone(k8s_objs[0].get('object'))
        self.assertEqual(k8s_objs[0].get('namespace'), '')
        self.assertEqual(k8s_objs[0].get('object').kind, 'NetworkPolicy')
        self.assertEqual(k8s_objs[0].get('object').api_version,
                         'networking.k8s.io/v1')

    def test_node(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['node.yaml'], self.yaml_path
        )
        self.assertIsNotNone(k8s_objs[0].get('object'))
        self.assertEqual(k8s_objs[0].get('namespace'), '')
        self.assertEqual(k8s_objs[0].get('object').kind, 'Node')
        self.assertEqual(k8s_objs[0].get('object').api_version, 'v1')

    def test_persistent_volume(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['persistent-volume.yaml'], self.yaml_path
        )
        self.assertIsNotNone(k8s_objs[0].get('object'))
        self.assertEqual(k8s_objs[0].get('namespace'), '')
        self.assertEqual(k8s_objs[0].get('object').kind, 'PersistentVolume')
        self.assertEqual(k8s_objs[0].get('object').api_version, 'v1')

    def test_persistent_volume_claim(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['persistent-volume-claim.yaml'], self.yaml_path
        )
        self.assertIsNotNone(k8s_objs[0].get('object'))
        self.assertEqual(k8s_objs[0].get('namespace'), '')
        self.assertEqual(k8s_objs[0].get('object').kind,
                         'PersistentVolumeClaim')
        self.assertEqual(k8s_objs[0].get('object').api_version, 'v1')

    def test_pod(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['pod.yaml'], self.yaml_path
        )
        self.assertIsNotNone(k8s_objs[0].get('object'))
        self.assertEqual(k8s_objs[0].get('namespace'), '')
        self.assertEqual(k8s_objs[0].get('object').kind,
                         'Pod')
        self.assertEqual(k8s_objs[0].get('object').api_version, 'v1')

    def test_priority_class(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['priority-class.yaml'], self.yaml_path
        )
        self.assertIsNotNone(k8s_objs[0].get('object'))
        self.assertEqual(k8s_objs[0].get('namespace'), '')
        self.assertEqual(k8s_objs[0].get('object').kind,
                         'PriorityClass')
        self.assertEqual(k8s_objs[0].get('object').api_version,
                         'scheduling.k8s.io/v1')

    def test_replica_set(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['replica-set.yaml'], self.yaml_path
        )
        self.assertIsNotNone(k8s_objs[0].get('object'))
        self.assertEqual(k8s_objs[0].get('namespace'), '')
        self.assertEqual(k8s_objs[0].get('object').kind,
                         'ReplicaSet')
        self.assertEqual(k8s_objs[0].get('object').api_version,
                         'apps/v1')

    def test_resource_quota(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['resource-quota.yaml'], self.yaml_path
        )
        self.assertIsNotNone(k8s_objs[0].get('object'))
        self.assertEqual(k8s_objs[0].get('namespace'), 'curryns')
        self.assertEqual(k8s_objs[0].get('object').kind,
                         'ResourceQuota')
        self.assertEqual(k8s_objs[0].get('object').api_version,
                         'v1')

    def test_role(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['role.yaml'], self.yaml_path
        )
        self.assertIsNotNone(k8s_objs[0].get('object'))
        self.assertEqual(k8s_objs[0].get('namespace'), 'curry-ns')
        self.assertEqual(k8s_objs[0].get('object').kind,
                         'Role')
        self.assertEqual(k8s_objs[0].get('object').api_version,
                         'rbac.authorization.k8s.io/v1')

    def test_role_binding(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['role-bindings.yaml'], self.yaml_path
        )
        self.assertIsNotNone(k8s_objs[0].get('object'))
        self.assertEqual(k8s_objs[0].get('namespace'), 'curry-ns')
        self.assertEqual(k8s_objs[0].get('object').kind,
                         'RoleBinding')
        self.assertEqual(k8s_objs[0].get('object').api_version,
                         'rbac.authorization.k8s.io/v1')

    def test_secret(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['secret.yaml'], self.yaml_path
        )
        self.assertIsNotNone(k8s_objs[0].get('object'))
        self.assertEqual(k8s_objs[0].get('namespace'), 'default')
        self.assertEqual(k8s_objs[0].get('object').kind,
                         'Secret')
        self.assertEqual(k8s_objs[0].get('object').api_version,
                         'v1')

    def test_self_subject_access_review(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['self-subject-access-review.yaml'], self.yaml_path
        )
        self.assertIsNotNone(k8s_objs[0].get('object'))
        self.assertEqual(k8s_objs[0].get('namespace'), '')
        self.assertEqual(k8s_objs[0].get('object').kind,
                         'SelfSubjectAccessReview')
        self.assertEqual(k8s_objs[0].get('object').api_version,
                         'authorization.k8s.io/v1')

    def test_self_subject_rules_review(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['self-subject-rule-review.yaml'], self.yaml_path
        )
        self.assertIsNotNone(k8s_objs[0].get('object'))
        self.assertEqual(k8s_objs[0].get('namespace'), '')
        self.assertEqual(k8s_objs[0].get('object').kind,
                         'SelfSubjectRulesReview')
        self.assertEqual(k8s_objs[0].get('object').api_version,
                         'authorization.k8s.io/v1')

    def test_service(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['service.yaml'], self.yaml_path
        )
        self.assertIsNotNone(k8s_objs[0].get('object'))
        self.assertEqual(k8s_objs[0].get('namespace'), 'default')
        self.assertEqual(k8s_objs[0].get('object').kind,
                         'Service')
        self.assertEqual(k8s_objs[0].get('object').api_version,
                         'v1')

    def test_service_account(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['service-account.yaml'], self.yaml_path
        )
        self.assertIsNotNone(k8s_objs[0].get('object'))
        self.assertEqual(k8s_objs[0].get('namespace'), 'default')
        self.assertEqual(k8s_objs[0].get('object').kind,
                         'ServiceAccount')
        self.assertEqual(k8s_objs[0].get('object').api_version,
                         'v1')

    def test_stateful_set(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['stateful-set.yaml'], self.yaml_path
        )
        self.assertIsNotNone(k8s_objs[0].get('object'))
        self.assertEqual(k8s_objs[0].get('namespace'), '')
        self.assertEqual(k8s_objs[0].get('object').kind,
                         'StatefulSet')
        self.assertEqual(k8s_objs[0].get('object').api_version,
                         'apps/v1')

    def test_storage_class(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['storage-class.yaml'], self.yaml_path
        )
        self.assertIsNotNone(k8s_objs[0].get('object'))
        self.assertEqual(k8s_objs[0].get('namespace'), '')
        self.assertEqual(k8s_objs[0].get('object').kind,
                         'StorageClass')
        self.assertEqual(k8s_objs[0].get('object').api_version,
                         'storage.k8s.io/v1')

    def test_subject_access_review(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['subject-access-review.yaml'], self.yaml_path
        )
        self.assertIsNotNone(k8s_objs[0].get('object'))
        self.assertEqual(k8s_objs[0].get('namespace'), '')
        self.assertEqual(k8s_objs[0].get('object').kind,
                         'SubjectAccessReview')
        self.assertEqual(k8s_objs[0].get('object').api_version,
                         'authorization.k8s.io/v1')

    def test_token_review(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['token-review.yaml'], self.yaml_path
        )
        self.assertIsNotNone(k8s_objs[0].get('object'))
        self.assertEqual(k8s_objs[0].get('namespace'), '')
        self.assertEqual(k8s_objs[0].get('object').kind,
                         'TokenReview')
        self.assertEqual(k8s_objs[0].get('object').api_version,
                         'authentication.k8s.io/v1')

    def test_limit_range(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['limit-range.yaml'], self.yaml_path
        )
        self.assertIsNotNone(k8s_objs[0].get('object'))
        self.assertEqual(k8s_objs[0].get('namespace'), 'curryns')
        self.assertEqual(k8s_objs[0].get('object').kind,
                         'LimitRange')
        self.assertEqual(k8s_objs[0].get('object').api_version,
                         'v1')

    def test_pod_template(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['pod-template.yaml'], self.yaml_path
        )
        self.assertIsNotNone(k8s_objs[0].get('object'))
        self.assertEqual(k8s_objs[0].get('namespace'), 'curryns')
        self.assertEqual(k8s_objs[0].get('object').kind,
                         'PodTemplate')
        self.assertEqual(k8s_objs[0].get('object').api_version,
                         'v1')

    def test_volume_attachment(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['volume-attachment.yaml'], self.yaml_path
        )
        self.assertIsNotNone(k8s_objs[0].get('object'))
        self.assertEqual(k8s_objs[0].get('namespace'), 'curryns')
        self.assertEqual(k8s_objs[0].get('object').kind,
                         'VolumeAttachment')
        self.assertEqual(k8s_objs[0].get('object').api_version,
                         'storage.k8s.io/v1')

    def test_bindings(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['bindings.yaml'], self.yaml_path
        )
        self.assertIsNotNone(k8s_objs[0].get('object'))
        self.assertEqual(k8s_objs[0].get('namespace'), 'curryns')
        self.assertEqual(k8s_objs[0].get('object').kind,
                         'Binding')
        self.assertEqual(k8s_objs[0].get('object').api_version,
                         'v1')

    def test_controller_revision(self):
        k8s_objs = self.transfromer.get_k8s_objs_from_yaml(
            ['controller-revision.yaml'], self.yaml_path
        )
        self.assertIsNotNone(k8s_objs[0].get('object'))
        self.assertEqual(k8s_objs[0].get('namespace'), 'curryns')
        self.assertEqual(k8s_objs[0].get('object').kind,
                         'ControllerRevision')
        self.assertEqual(k8s_objs[0].get('object').api_version,
                         'apps/v1')
