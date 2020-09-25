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

import ddt
import os

from kubernetes import client
from tacker.common import exceptions
from tacker import context
from tacker.db.db_sqlalchemy import models
from tacker.extensions import vnfm
from tacker import objects
from tacker.objects import fields
from tacker.objects.vnf_instance import VnfInstance
from tacker.objects import vnf_package
from tacker.objects import vnf_package_vnfd
from tacker.objects import vnf_resources as vnf_resource_obj
from tacker.tests.unit import base
from tacker.tests.unit.db import utils
from tacker.tests.unit.vnfm.infra_drivers.kubernetes import fakes
from tacker.tests.unit.vnfm.infra_drivers.openstack.fixture_data import \
    fixture_data_utils as fd_utils
from tacker.vnfm.infra_drivers.kubernetes import kubernetes_driver
from unittest import mock


@ddt.ddt
class TestKubernetes(base.TestCase):
    def setUp(self):
        super(TestKubernetes, self).setUp()
        self.kubernetes = kubernetes_driver.Kubernetes()
        self.kubernetes.STACK_RETRIES = 1
        self.kubernetes.STACK_RETRY_WAIT = 5
        self.k8s_client_dict = fakes.fake_k8s_client_dict()
        self.context = context.get_admin_context()
        self.vnf_instance = fd_utils.get_vnf_instance_object()
        self.yaml_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "../../../../etc/samples/etsi/nfv/"
            "sample_kubernetes_driver/Files/kubernetes/")

    @mock.patch.object(client.CoreV1Api, 'read_node')
    def test_create_wait_k8s_success_node(self, mock_read_node):
        k8s_objs = fakes.fake_k8s_objs_node()
        k8s_client_dict = self.k8s_client_dict
        mock_read_node.return_value = fakes.fake_node()
        checked_objs = self.kubernetes.\
            create_wait_k8s(k8s_objs, k8s_client_dict,
                            self.vnf_instance)
        self.assertEqual(checked_objs[0].get('status'), 'Create_complete')

    @mock.patch.object(client.CoreV1Api, 'read_node')
    def test_create_wait_k8s_failure_node(self, mock_read_node):
        k8s_objs = fakes.fake_k8s_objs_node_status_false()
        k8s_client_dict = self.k8s_client_dict
        mock_read_node.return_value = fakes.fake_node_false()
        self.assertRaises(vnfm.CNFCreateWaitFailed,
                          self.kubernetes.create_wait_k8s,
                          k8s_objs, k8s_client_dict, self.vnf_instance)

    @mock.patch.object(client.CoreV1Api,
                       'read_namespaced_persistent_volume_claim')
    def test_create_wait_k8s_success_persistent_volume_claim(
            self, mock_read_claim):
        k8s_objs = fakes.fake_k8s_objs_pvc()
        k8s_client_dict = self.k8s_client_dict
        mock_read_claim.return_value = fakes.fake_pvc()
        checked_objs = self.kubernetes. \
            create_wait_k8s(k8s_objs, k8s_client_dict,
                            self.vnf_instance)
        self.assertEqual(checked_objs[0].get('status'), 'Create_complete')

    @mock.patch.object(client.CoreV1Api,
                       'read_namespaced_persistent_volume_claim')
    def test_create_wait_k8s_failure_persistent_volume_claim(
            self, mock_read_claim):
        k8s_objs = fakes.fake_k8s_objs_pvc_false_phase()
        k8s_client_dict = self.k8s_client_dict
        mock_read_claim.return_value = fakes.fake_pvc_false()
        self.assertRaises(vnfm.CNFCreateWaitFailed,
                          self.kubernetes.create_wait_k8s,
                          k8s_objs, k8s_client_dict, self.vnf_instance)

    @mock.patch.object(client.CoreV1Api, 'read_namespace')
    def test_create_wait_k8s_success_namespace(self, mock_read_namespace):
        k8s_objs = fakes.fake_k8s_objs_namespace()
        k8s_client_dict = self.k8s_client_dict
        mock_read_namespace.return_value = fakes.fake_namespace()
        checked_objs = self.kubernetes. \
            create_wait_k8s(k8s_objs, k8s_client_dict,
                            self.vnf_instance)
        self.assertEqual(checked_objs[0].get('status'), 'Create_complete')

    @mock.patch.object(client.CoreV1Api, 'read_namespace')
    def test_create_wait_k8s_failure_namespace(self, mock_read_namespace):
        k8s_objs = fakes.fake_k8s_objs_namespace_false_phase()
        k8s_client_dict = self.k8s_client_dict
        mock_read_namespace.return_value = fakes.fake_namespace_false()
        self.assertRaises(vnfm.CNFCreateWaitFailed,
                          self.kubernetes.create_wait_k8s,
                          k8s_objs, k8s_client_dict, self.vnf_instance)

    @mock.patch.object(client.CoreV1Api, 'read_namespaced_service')
    @mock.patch.object(client.CoreV1Api, 'read_namespaced_endpoints')
    def test_create_wait_k8s_success_service(
            self, mock_endpoinds, mock_read_service):
        k8s_objs = fakes.fake_k8s_objs_service()
        k8s_client_dict = self.k8s_client_dict
        mock_endpoinds.return_value = fakes.fake_endpoinds()
        mock_read_service.return_value = fakes.fake_service()
        checked_objs = self.kubernetes.\
            create_wait_k8s(k8s_objs, k8s_client_dict,
                            self.vnf_instance)
        self.assertEqual(checked_objs[0].get('status'), 'Create_complete')

    @mock.patch.object(client.CoreV1Api, 'read_namespaced_service')
    @mock.patch.object(client.CoreV1Api, 'read_namespaced_endpoints')
    def test_create_wait_k8s_failure_service(
            self, mock_endpoinds, mock_read_service):
        k8s_objs = fakes.fake_k8s_objs_service_false_cluster_ip()
        k8s_client_dict = self.k8s_client_dict
        mock_endpoinds.return_value = None
        mock_read_service.return_value = fakes.fake_service_false()
        self.assertRaises(vnfm.CNFCreateWaitFailed,
                          self.kubernetes.create_wait_k8s,
                          k8s_objs, k8s_client_dict, self.vnf_instance)

    @mock.patch.object(client.CoreV1Api, 'read_namespaced_service')
    def test_create_wait_k8s_failure_service_read_endpoinds(
            self, mock_read_service):
        k8s_objs = fakes.fake_k8s_objs_service_false_cluster_ip()
        k8s_client_dict = self.k8s_client_dict
        mock_read_service.return_value = fakes.fake_service()
        self.assertRaises(exceptions.ReadEndpoindsFalse,
                          self.kubernetes.create_wait_k8s,
                          k8s_objs, k8s_client_dict, self.vnf_instance)

    @mock.patch.object(client.AppsV1Api, 'read_namespaced_deployment')
    def test_create_wait_k8s_deployment(self, mock_read_namespaced_deployment):
        k8s_objs = fakes.fake_k8s_objs_deployment()
        k8s_client_dict = self.k8s_client_dict
        deployment_obj = fakes.fake_v1_deployment()
        mock_read_namespaced_deployment.return_value = deployment_obj
        checked_objs = self.kubernetes. \
            create_wait_k8s(k8s_objs, k8s_client_dict,
                            self.vnf_instance)
        flag = True
        for obj in checked_objs:
            if obj.get('status') != 'Create_complete':
                flag = False

        self.assertEqual(flag, True)

    @mock.patch.object(client.AppsV1Api, 'read_namespaced_deployment')
    def test_create_wait_k8s_deployment_error(self,
                                              mock_read_namespaced_deployment):
        k8s_objs = fakes.fake_k8s_objs_deployment_error()
        k8s_client_dict = self.k8s_client_dict
        deployment_obj = fakes.fake_v1_deployment_error()
        mock_read_namespaced_deployment.return_value = deployment_obj
        exc = self.assertRaises(vnfm.CNFCreateWaitFailed,
                                self.kubernetes.create_wait_k8s,
                                k8s_objs, k8s_client_dict, self.vnf_instance)
        msg = _(
            "CNF Create Failed with reason: "
            "Resource creation is not completed within"
            " {wait} seconds as creation of stack {stack}"
            " is not completed").format(
            wait=(self.kubernetes.STACK_RETRIES *
                  self.kubernetes.STACK_RETRY_WAIT),
            stack=self.vnf_instance.id
        )
        self.assertEqual(msg, exc.format_message())

    @mock.patch.object(client.AppsV1Api, 'read_namespaced_replica_set')
    def test_create_wait_k8s_replica_set(self,
                                         mock_read_namespaced_replica_set):
        k8s_objs = fakes.fake_k8s_objs_replica_set()
        k8s_client_dict = self.k8s_client_dict
        replica_set_obj = fakes.fake_v1_replica_set()
        mock_read_namespaced_replica_set.return_value = replica_set_obj
        checked_objs = self.kubernetes. \
            create_wait_k8s(k8s_objs, k8s_client_dict,
                            self.vnf_instance)
        flag = True
        for obj in checked_objs:
            if obj.get('status') != 'Create_complete':
                flag = False

        self.assertEqual(flag, True)

    @mock.patch.object(client.AppsV1Api, 'read_namespaced_replica_set')
    def test_create_wait_k8s_replica_set_error(
            self, mock_read_namespaced_replica_set):
        k8s_objs = fakes.fake_k8s_objs_replica_set_error()
        k8s_client_dict = self.k8s_client_dict
        replica_set_obj = fakes.fake_v1_replica_set_error()
        mock_read_namespaced_replica_set.return_value = replica_set_obj
        exc = self.assertRaises(vnfm.CNFCreateWaitFailed,
                                self.kubernetes.create_wait_k8s,
                                k8s_objs, k8s_client_dict, self.vnf_instance)

        msg = _(
            "CNF Create Failed with reason: "
            "Resource creation is not completed within"
            " {wait} seconds as creation of stack {stack}"
            " is not completed").format(
            wait=(self.kubernetes.STACK_RETRIES *
                  self.kubernetes.STACK_RETRY_WAIT),
            stack=self.vnf_instance.id
        )
        self.assertEqual(msg, exc.format_message())

    @mock.patch.object(client.CoreV1Api,
                       'read_namespaced_persistent_volume_claim')
    @mock.patch.object(client.AppsV1Api, 'read_namespaced_stateful_set')
    def test_create_wait_k8s_stateful_set(
            self, mock_read_namespaced_stateful_set,
            mock_read_namespaced_persistent_volume_claim):
        k8s_objs = fakes.fake_k8s_objs_stateful_set()
        k8s_client_dict = self.k8s_client_dict
        stateful_set_obj = fakes.fake_v1_stateful_set()
        persistent_volume_claim_obj = fakes. \
            fake_v1_persistent_volume_claim()
        mock_read_namespaced_stateful_set.return_value = stateful_set_obj
        mock_read_namespaced_persistent_volume_claim.return_value = \
            persistent_volume_claim_obj
        checked_objs = self.kubernetes. \
            create_wait_k8s(k8s_objs, k8s_client_dict,
                            self.vnf_instance)
        flag = True
        for obj in checked_objs:
            if obj.get('status') != 'Create_complete':
                flag = False

        self.assertEqual(flag, True)

    @mock.patch.object(client.CoreV1Api,
                       'read_namespaced_persistent_volume_claim')
    @mock.patch.object(client.AppsV1Api, 'read_namespaced_stateful_set')
    def test_create_wait_k8s_stateful_set_error(
            self, mock_read_namespaced_stateful_set,
            mock_read_namespaced_persistent_volume_claim):
        k8s_objs = fakes.fake_k8s_objs_stateful_set_error()
        k8s_client_dict = self.k8s_client_dict
        stateful_set_obj = fakes.fake_v1_stateful_set_error()
        persistent_volume_claim_obj = fakes. \
            fake_v1_persistent_volume_claim_error()
        mock_read_namespaced_stateful_set.return_value = stateful_set_obj
        mock_read_namespaced_persistent_volume_claim \
            .return_value = persistent_volume_claim_obj
        exc = self.assertRaises(vnfm.CNFCreateWaitFailed,
                                self.kubernetes.create_wait_k8s,
                                k8s_objs, k8s_client_dict, self.vnf_instance)
        msg = _(
            "CNF Create Failed with reason: "
            "Resource creation is not completed within"
            " {wait} seconds as creation of stack {stack}"
            " is not completed").format(
            wait=(self.kubernetes.STACK_RETRIES *
                  self.kubernetes.STACK_RETRY_WAIT),
            stack=self.vnf_instance.id
        )
        self.assertEqual(msg, exc.format_message())

    @mock.patch.object(client.BatchV1Api, 'read_namespaced_job')
    def test_create_wait_k8s_job(self, mock_read_namespaced_job):
        k8s_objs = fakes.fake_k8s_objs_job()
        k8s_client_dict = self.k8s_client_dict
        job_obj = fakes.fake_v1_job()
        mock_read_namespaced_job.return_value = job_obj
        checked_objs = self.kubernetes. \
            create_wait_k8s(k8s_objs, k8s_client_dict,
                            self.vnf_instance)
        flag = True
        for obj in checked_objs:
            if obj.get('status') != 'Create_complete':
                flag = False

        self.assertEqual(flag, True)

    @mock.patch.object(client.BatchV1Api, 'read_namespaced_job')
    def test_create_wait_k8s_job_error(self, mock_read_namespaced_job):
        k8s_objs = fakes.fake_k8s_objs_job_error()
        k8s_client_dict = self.k8s_client_dict
        job_obj = fakes.fake_v1_job_error()
        mock_read_namespaced_job.return_value = job_obj
        exc = self.assertRaises(vnfm.CNFCreateWaitFailed,
                                self.kubernetes.create_wait_k8s,
                                k8s_objs, k8s_client_dict, self.vnf_instance)
        msg = _(
            "CNF Create Failed with reason: "
            "Resource creation is not completed within"
            " {wait} seconds as creation of stack {stack}"
            " is not completed").format(
            wait=(self.kubernetes.STACK_RETRIES *
                  self.kubernetes.STACK_RETRY_WAIT),
            stack=self.vnf_instance.id
        )
        self.assertEqual(msg, exc.format_message())

    @mock.patch.object(client.StorageV1Api, 'read_volume_attachment')
    def test_create_wait_k8s_volume_attachment(self,
                                               mock_read_volume_attachment):
        k8s_objs = fakes.fake_k8s_objs_volume_attachment()
        k8s_client_dict = self.k8s_client_dict
        volume_attachment_obj = fakes.fake_v1_volume_attachment()
        mock_read_volume_attachment.return_value = volume_attachment_obj
        checked_objs = self.kubernetes. \
            create_wait_k8s(k8s_objs, k8s_client_dict,
                            self.vnf_instance)
        flag = True
        for obj in checked_objs:
            if obj.get('status') != 'Create_complete':
                flag = False

        self.assertEqual(flag, True)

    @mock.patch.object(client.StorageV1Api, 'read_volume_attachment')
    def test_create_wait_k8s_volume_attachment_error(
            self, mock_read_volume_attachment):
        k8s_objs = fakes.fake_k8s_objs_volume_attachment_error()
        k8s_client_dict = self.k8s_client_dict
        volume_attachment_obj = fakes.fake_v1_volume_attachment_error()
        mock_read_volume_attachment.return_value = volume_attachment_obj
        self.assertRaises(vnfm.CNFCreateWaitFailed,
                          self.kubernetes.create_wait_k8s,
                          k8s_objs, k8s_client_dict, self.vnf_instance)

    @mock.patch.object(client.CoreV1Api, 'read_namespaced_pod')
    def test_create_wait_k8s_pod(self, mock_read_namespaced_pod):
        k8s_objs = fakes.fake_k8s_objs_pod()
        k8s_client_dict = self.k8s_client_dict
        pod_obj = fakes.fake_pod()
        mock_read_namespaced_pod.return_value = pod_obj
        checked_objs = self.kubernetes. \
            create_wait_k8s(k8s_objs, k8s_client_dict,
                            self.vnf_instance)
        flag = True
        for obj in checked_objs:
            if obj.get('status') != 'Create_complete':
                flag = False
        self.assertEqual(flag, True)

    @mock.patch.object(client.CoreV1Api, 'read_namespaced_pod')
    def test_create_wait_k8s_pod_error(self, mock_read_namespaced_pod):
        k8s_objs = fakes.fake_k8s_objs_pod_error()
        k8s_client_dict = self.k8s_client_dict
        pod_obj = fakes.fake_pod_error()
        mock_read_namespaced_pod.return_value = pod_obj
        exc = self.assertRaises(vnfm.CNFCreateWaitFailed,
                                self.kubernetes.create_wait_k8s,
                                k8s_objs, k8s_client_dict, self.vnf_instance)
        msg = _(
            "CNF Create Failed with reason: "
            "Resource creation is not completed within"
            " {wait} seconds as creation of stack {stack}"
            " is not completed").format(
            wait=(self.kubernetes.STACK_RETRIES *
                  self.kubernetes.STACK_RETRY_WAIT),
            stack=self.vnf_instance.id
        )
        self.assertEqual(msg, exc.format_message())

    @mock.patch.object(client.CoreV1Api, 'read_persistent_volume')
    def test_create_wait_k8s_persistent_volume(self,
                                               mock_read_persistent_volume):
        k8s_objs = fakes.fake_k8s_objs_persistent_volume()
        k8s_client_dict = self.k8s_client_dict
        persistent_volume_obj = fakes.fake_persistent_volume()
        mock_read_persistent_volume.return_value = persistent_volume_obj
        checked_objs = self.kubernetes. \
            create_wait_k8s(k8s_objs, k8s_client_dict,
                            self.vnf_instance)
        flag = True
        for obj in checked_objs:
            if obj.get('status') != 'Create_complete':
                flag = False

        self.assertEqual(flag, True)

    @mock.patch.object(client.CoreV1Api, 'read_persistent_volume')
    def test_create_wait_k8s_persistent_volume_error(
            self, mock_read_persistent_volume):
        k8s_objs = fakes.fake_k8s_objs_persistent_volume_error()
        k8s_client_dict = self.k8s_client_dict
        persistent_volume_obj = fakes.fake_persistent_volume_error()
        mock_read_persistent_volume.return_value = persistent_volume_obj
        exc = self.assertRaises(vnfm.CNFCreateWaitFailed,
                                self.kubernetes.create_wait_k8s,
                                k8s_objs, k8s_client_dict, self.vnf_instance)
        msg = _(
            "CNF Create Failed with reason: "
            "Resource creation is not completed within"
            " {wait} seconds as creation of stack {stack}"
            " is not completed").format(
            wait=(self.kubernetes.STACK_RETRIES *
                  self.kubernetes.STACK_RETRY_WAIT),
            stack=self.vnf_instance.id
        )
        self.assertEqual(msg, exc.format_message())

    @mock.patch.object(client.ApiregistrationV1Api, 'read_api_service')
    def test_create_wait_k8s_api_service(self, mock_read_api_service):
        k8s_objs = fakes.fake_k8s_objs_api_service()
        k8s_client_dict = self.k8s_client_dict
        api_service_obj = fakes.fake_api_service()
        mock_read_api_service.return_value = api_service_obj
        checked_objs = self.kubernetes. \
            create_wait_k8s(k8s_objs, k8s_client_dict,
                            self.vnf_instance)
        flag = True
        for obj in checked_objs:
            if obj.get('status') != 'Create_complete':
                flag = False

        self.assertEqual(flag, True)

    @mock.patch.object(client.ApiregistrationV1Api, 'read_api_service')
    def test_create_wait_k8s_api_service_error(self, mock_read_api_service):
        k8s_objs = fakes.fake_k8s_objs_api_service_error()
        k8s_client_dict = self.k8s_client_dict
        api_service_obj = fakes.fake_api_service_error()
        mock_read_api_service.return_value = api_service_obj
        exc = self.assertRaises(vnfm.CNFCreateWaitFailed,
                                self.kubernetes.create_wait_k8s,
                                k8s_objs, k8s_client_dict, self.vnf_instance)
        msg = _(
            "CNF Create Failed with reason: "
            "Resource creation is not completed within"
            " {wait} seconds as creation of stack {stack}"
            " is not completed").format(
            wait=(self.kubernetes.STACK_RETRIES *
                  self.kubernetes.STACK_RETRY_WAIT),
            stack=self.vnf_instance.id
        )
        self.assertEqual(msg, exc.format_message())

    @mock.patch.object(client.AppsV1Api, 'read_namespaced_daemon_set')
    def test_create_wait_k8s_daemon_set(self,
                                        mock_read_namespaced_daemon_set):
        k8s_objs = fakes.fake_k8s_objs_daemon_set()
        k8s_client_dict = self.k8s_client_dict
        daemon_set_obj = fakes.fake_daemon_set()
        mock_read_namespaced_daemon_set.return_value = daemon_set_obj
        checked_objs = self.kubernetes. \
            create_wait_k8s(k8s_objs, k8s_client_dict,
                            self.vnf_instance)
        flag = True
        for obj in checked_objs:
            if obj.get('status') != 'Create_complete':
                flag = False
        self.assertEqual(flag, True)

    @mock.patch.object(client.AppsV1Api, 'read_namespaced_daemon_set')
    def test_create_wait_k8s_daemon_set_error(
            self, mock_read_namespaced_daemon_set):
        k8s_objs = fakes.fake_k8s_objs_daemon_set_error()
        k8s_client_dict = self.k8s_client_dict
        daemon_set_obj = fakes.fake_daemon_set_error()
        mock_read_namespaced_daemon_set.return_value = daemon_set_obj
        exc = self.assertRaises(vnfm.CNFCreateWaitFailed,
                                self.kubernetes.create_wait_k8s,
                                k8s_objs, k8s_client_dict, self.vnf_instance)
        msg = _(
            "CNF Create Failed with reason: "
            "Resource creation is not completed within"
            " {wait} seconds as creation of stack {stack}"
            " is not completed").format(
            wait=(self.kubernetes.STACK_RETRIES *
                  self.kubernetes.STACK_RETRY_WAIT),
            stack=self.vnf_instance.id
        )
        self.assertEqual(msg, exc.format_message())

    def test_pre_instantiation_vnf_artifacts_file_none(self):
        instantiate_vnf_req = objects.InstantiateVnfRequest(
            additional_params={'a': ["Files/kubernets/pod.yaml"]})
        new_k8s_objs = self.kubernetes.pre_instantiation_vnf(
            None, None, None, None,
            instantiate_vnf_req, None)
        self.assertEqual(new_k8s_objs, {})

    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    @mock.patch.object(vnf_package_vnfd.VnfPackageVnfd, "get_by_id")
    @mock.patch.object(VnfInstance, "save")
    def test_pre_instantiation_vnf_vnfpackage_vnfartifacts_none(
            self, mock_save, mock_vnfd_by_id, mock_vnf_by_id):
        vnf_instance = fd_utils.get_vnf_instance_object()
        vim_connection_info = None
        vnf_software_images = None
        vnf_package_path = self.yaml_path
        instantiate_vnf_req = objects.InstantiateVnfRequest(
            additional_params={
                'lcm-kubernetes-def-files':
                    ["testdata_artifact_file_content.yaml"]
            }
        )
        fake_vnfd_get_by_id = models.VnfPackageVnfd()
        fake_vnfd_get_by_id.package_uuid = "f8c35bd0-4d67-4436-" \
                                           "9f11-14b8a84c92aa"
        fake_vnfd_get_by_id.vnfd_id = "f8c35bd0-4d67-4436-9f11-14b8a84c92aa"
        fake_vnfd_get_by_id.vnf_provider = "fake_provider"
        fake_vnfd_get_by_id.vnf_product_name = "fake_product_name"
        fake_vnfd_get_by_id.vnf_software_version = "fake_software_version"
        fake_vnfd_get_by_id.vnfd_version = "fake_vnfd_version"
        mock_vnfd_by_id.return_value = fake_vnfd_get_by_id
        fake_vnf_get_by_id = models.VnfPackage()
        fake_vnf_get_by_id.onboarding_state = "ONBOARD"
        fake_vnf_get_by_id.operational_state = ""
        fake_vnf_get_by_id.usage_state = "NOT_IN_USE"
        fake_vnf_get_by_id.size = 128
        fake_vnf_get_by_id.vnf_artifacts = []
        mock_vnf_by_id.return_value = fake_vnf_get_by_id
        vnf_resource = vnf_resource_obj.VnfResource(context=self.context)
        vnf_resource.vnf_instance_id = vnf_instance.id
        vnf_resource.resource_name = "curry-ns,curry-endpoint-test001"
        vnf_resource.resource_type = "v1,Pod"
        vnf_resource.resource_identifier = ''
        vnf_resource.resource_status = ''

        self.assertRaises(exceptions.VnfArtifactNotFound,
                          self.kubernetes.pre_instantiation_vnf,
                          self.context, vnf_instance, vim_connection_info,
                          vnf_software_images,
                          instantiate_vnf_req, vnf_package_path)

    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    @mock.patch.object(vnf_package_vnfd.VnfPackageVnfd, "get_by_id")
    @mock.patch.object(VnfInstance, "save")
    def test_pre_instantiation_vnf_raise(self, mock_save, mock_vnfd_by_id,
                                         mock_vnf_by_id):
        vnf_instance = fd_utils.get_vnf_instance_object()
        vim_connection_info = None
        vnf_software_images = None
        vnf_package_path = self.yaml_path
        instantiate_vnf_req = objects.InstantiateVnfRequest(
            additional_params={
                'lcm-kubernetes-def-files':
                    ["testdata_artifact_file_content.yaml"]
            }
        )
        fake_vnfd_get_by_id = models.VnfPackageVnfd()
        fake_vnfd_get_by_id.package_uuid = "f8c35bd0-4d67-4436-" \
                                           "9f11-14b8a84c92aa"
        fake_vnfd_get_by_id.vnfd_id = "f8c35bd0-4d67-4436-9f11-14b8a84c92aa"
        fake_vnfd_get_by_id.vnf_provider = "fake_provider"
        fake_vnfd_get_by_id.vnf_product_name = "fake_providername"
        fake_vnfd_get_by_id.vnf_software_version = "fake_software_version"
        fake_vnfd_get_by_id.vnfd_version = "fake_vnfd_version"
        mock_vnfd_by_id.return_value = fake_vnfd_get_by_id
        fake_vnf_get_by_id = models.VnfPackage()
        fake_vnf_get_by_id.onboarding_state = "ONBOARD"
        fake_vnf_get_by_id.operational_state = "ENABLED"
        fake_vnf_get_by_id.usage_state = "NOT_IN_USE"
        fake_vnf_get_by_id.size = 128
        mock_artifacts = models.VnfPackageArtifactInfo()
        mock_artifacts.package_uuid = "f8c35bd0-4d67-4436-9f11-14b8a84c92aa"
        mock_artifacts.artifact_path = "a"
        mock_artifacts.algorithm = "SHA-256"
        mock_artifacts.hash = "fake_hash"
        fake_vnf_get_by_id.vnf_artifacts = [mock_artifacts]
        mock_vnf_by_id.return_value = fake_vnf_get_by_id
        self.assertRaises(vnfm.CnfDefinitionNotFound,
                          self.kubernetes.pre_instantiation_vnf,
                          self.context, vnf_instance, vim_connection_info,
                          vnf_software_images,
                          instantiate_vnf_req, vnf_package_path)

    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    @mock.patch.object(vnf_package_vnfd.VnfPackageVnfd, "get_by_id")
    def test_pre_instantiation_vnf(self, mock_vnfd_by_id, mock_vnf_by_id):
        vnf_instance = fd_utils.get_vnf_instance_object()
        vim_connection_info = None
        vnf_software_images = None
        vnf_package_path = self.yaml_path
        instantiate_vnf_req = objects.InstantiateVnfRequest(
            additional_params={
                'lcm-kubernetes-def-files':
                    ["testdata_artifact_file_content.yaml"]
            }
        )
        fake_vnfd_get_by_id = models.VnfPackageVnfd()
        fake_vnfd_get_by_id.package_uuid = "f8c35bd0-4d67" \
                                           "-4436-9f11-14b8a84c92aa"
        fake_vnfd_get_by_id.vnfd_id = "f8c35bd0-4d67-4436-9f11-14b8a84c92aa"
        fake_vnfd_get_by_id.vnf_provider = "fake_provider"
        fake_vnfd_get_by_id.vnf_product_name = "fake_providername"
        fake_vnfd_get_by_id.vnf_software_version = "fake_software_version"
        fake_vnfd_get_by_id.vnfd_version = "fake_vnfd_version"
        mock_vnfd_by_id.return_value = fake_vnfd_get_by_id
        fake_vnf_get_by_id = models.VnfPackage()
        fake_vnf_get_by_id.onboarding_state = "ONBOARD"
        fake_vnf_get_by_id.operational_state = "ENABLED"
        fake_vnf_get_by_id.usage_state = "NOT_IN_USE"
        fake_vnf_get_by_id.size = 128
        mock_artifacts = models.VnfPackageArtifactInfo()
        mock_artifacts.package_uuid = "f8c35bd0-4d67-4436-9f11-14b8a84c92aa"
        mock_artifacts.artifact_path = "testdata_artifact_file_content.yaml"
        mock_artifacts.algorithm = "SHA-256"
        mock_artifacts.hash = "fake_hash"
        fake_vnf_get_by_id.vnf_artifacts = [mock_artifacts]
        mock_vnf_by_id.return_value = fake_vnf_get_by_id
        new_k8s_objs = self.kubernetes.pre_instantiation_vnf(
            self.context, vnf_instance, vim_connection_info,
            vnf_software_images,
            instantiate_vnf_req, vnf_package_path)
        for item in new_k8s_objs.values():
            self.assertEqual(item[0].resource_name, 'curry-ns,'
                                                    'curry-endpoint-test001')
            self.assertEqual(item[0].resource_type, 'v1,Pod')

    def _delete_single_vnf_resource(self, mock_vnf_resource_list,
                                    resource_name, resource_type,
                                    terminate_vnf_req=None):
        vnf_id = 'fake_vnf_id'
        vnf_instance = fd_utils.get_vnf_instance_object()
        vnf_instance_id = vnf_instance.id
        vnf_resource = models.VnfResource()
        vnf_resource.vnf_instance_id = vnf_instance_id
        vnf_resource.resource_name = resource_name
        vnf_resource.resource_type = resource_type
        mock_vnf_resource_list.return_value = [vnf_resource]
        self.kubernetes.delete(plugin=None, context=self.context,
                               vnf_id=vnf_id,
                               auth_attr=utils.get_vim_auth_obj(),
                               vnf_instance=vnf_instance,
                               terminate_vnf_req=terminate_vnf_req)

    @mock.patch.object(client.CoreV1Api, 'delete_namespaced_pod')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_pod_terminate_vnfreq_graceful(self, mock_vnf_resource_list,
                                                  mock_delete_namespaced_pod):
        terminate_vnf_req = objects.TerminateVnfRequest(
            termination_type=fields.VnfInstanceTerminationType.GRACEFUL,
            graceful_termination_timeout=5)
        resource_name = "fake_namespace,fake_name"
        resource_type = "v1,Pod"
        mock_delete_namespaced_pod.return_value = client.V1Status()
        self._delete_single_vnf_resource(
            mock_vnf_resource_list=mock_vnf_resource_list,
            resource_name=resource_name,
            resource_type=resource_type,
            terminate_vnf_req=terminate_vnf_req)
        mock_delete_namespaced_pod.assert_called_once()

    @mock.patch.object(client.CoreV1Api, 'delete_namespaced_pod')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_pod_terminate_vnfreq_forceful(self, mock_vnf_resource_list,
                                                  mock_delete_namespaced_pod):
        terminate_vnf_req = objects.TerminateVnfRequest(
            termination_type=fields.VnfInstanceTerminationType.FORCEFUL)
        resource_name = "fake_namespace,fake_name"
        resource_type = "v1,Pod"
        mock_delete_namespaced_pod.return_value = client.V1Status()
        self._delete_single_vnf_resource(
            mock_vnf_resource_list=mock_vnf_resource_list,
            resource_name=resource_name,
            resource_type=resource_type,
            terminate_vnf_req=terminate_vnf_req)
        mock_delete_namespaced_pod.assert_called_once()

    @mock.patch.object(client.CoreV1Api, 'delete_namespaced_pod')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_pod_terminate_vnfreq_none(self, mock_vnf_resource_list,
                                              mock_delete_namespaced_pod):
        resource_name = "fake_namespace,fake_name"
        resource_type = "v1,Pod"
        mock_delete_namespaced_pod.return_value = client.V1Status()
        self._delete_single_vnf_resource(
            mock_vnf_resource_list=mock_vnf_resource_list,
            resource_name=resource_name,
            resource_type=resource_type,
            terminate_vnf_req=None)
        mock_delete_namespaced_pod.assert_called_once()

    @mock.patch.object(client.CoreV1Api, 'delete_namespaced_service')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_service(self, mock_vnf_resource_list,
                            mock_delete_namespaced_service):
        resource_name = "fake_namespace,fake_name"
        resource_type = "v1,Service"
        mock_delete_namespaced_service.return_value = client.V1Status()
        self._delete_single_vnf_resource(
            mock_vnf_resource_list=mock_vnf_resource_list,
            resource_name=resource_name,
            resource_type=resource_type,
            terminate_vnf_req=None)
        mock_delete_namespaced_service.assert_called_once()

    @mock.patch.object(client.CoreV1Api, 'delete_namespaced_secret')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_secret(self, mock_vnf_resource_list,
                           mock_delete_namespaced_secret):
        resource_name = "fake_namespace,fake_name"
        resource_type = "v1,Secret"
        mock_delete_namespaced_secret.return_value = client.V1Status()
        self._delete_single_vnf_resource(
            mock_vnf_resource_list=mock_vnf_resource_list,
            resource_name=resource_name,
            resource_type=resource_type,
            terminate_vnf_req=None)
        mock_delete_namespaced_secret.assert_called_once()

    @mock.patch.object(client.CoreV1Api, 'delete_namespaced_config_map')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_config_map(self, mock_vnf_resource_list,
                               mock_delete_namespaced_config_map):
        resource_name = "fake_namespace,fake_name"
        resource_type = "v1,ConfigMap"
        mock_delete_namespaced_config_map.return_value = client.V1Status()
        self._delete_single_vnf_resource(
            mock_vnf_resource_list=mock_vnf_resource_list,
            resource_name=resource_name,
            resource_type=resource_type,
            terminate_vnf_req=None)
        mock_delete_namespaced_config_map.assert_called_once()

    @mock.patch.object(client.CoreV1Api,
            'delete_namespaced_persistent_volume_claim')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_persistent_volume_claim(self, mock_vnf_resource_list,
                            mock_delete_namespaced_persistent_volume_claim):
        resource_name = "fake_namespace,fake_name"
        resource_type = "v1,PersistentVolumeClaim"
        mock_delete_namespaced_persistent_volume_claim.return_value = \
            client.V1Status()
        self._delete_single_vnf_resource(
            mock_vnf_resource_list=mock_vnf_resource_list,
            resource_name=resource_name,
            resource_type=resource_type,
            terminate_vnf_req=None)
        mock_delete_namespaced_persistent_volume_claim.assert_called_once()

    @mock.patch.object(client.CoreV1Api, 'delete_namespaced_limit_range')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_limit_range(self, mock_vnf_resource_list,
                                mock_delete_namespaced_limit_range):
        resource_name = "fake_namespace,fake_name"
        resource_type = "v1,LimitRange"
        mock_delete_namespaced_limit_range.return_value = client.V1Status()
        self._delete_single_vnf_resource(
            mock_vnf_resource_list=mock_vnf_resource_list,
            resource_name=resource_name,
            resource_type=resource_type,
            terminate_vnf_req=None)
        mock_delete_namespaced_limit_range.assert_called_once()

    @mock.patch.object(client.CoreV1Api, 'delete_namespaced_pod_template')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_pod_template(self, mock_vnf_resource_list,
                                 mock_delete_namespaced_pod_template):
        resource_name = "fake_namespace,fake_name"
        resource_type = "v1,PodTemplate"
        mock_delete_namespaced_pod_template.return_value = client.V1Status()
        self._delete_single_vnf_resource(
            mock_vnf_resource_list=mock_vnf_resource_list,
            resource_name=resource_name,
            resource_type=resource_type,
            terminate_vnf_req=None)
        mock_delete_namespaced_pod_template.assert_called_once()

    @mock.patch.object(client.CoreV1Api, 'delete_namespace')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_namespace(self, mock_vnf_resource_list,
                              mock_delete_namespace):
        resource_name = ",fake_name"
        resource_type = "v1,Namespace"
        mock_delete_namespace.return_value = client.V1Status()
        self._delete_single_vnf_resource(
            mock_vnf_resource_list=mock_vnf_resource_list,
            resource_name=resource_name,
            resource_type=resource_type,
            terminate_vnf_req=None)
        mock_delete_namespace.assert_called_once()

    @mock.patch.object(client.CoreV1Api, 'delete_persistent_volume')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_persistent_volume(self, mock_vnf_resource_list,
                                      mock_delete_persistent_volume):
        resource_name = ",fake_name"
        resource_type = "v1,PersistentVolume"
        mock_delete_persistent_volume.return_value = client.V1Status()
        self._delete_single_vnf_resource(
            mock_vnf_resource_list=mock_vnf_resource_list,
            resource_name=resource_name,
            resource_type=resource_type,
            terminate_vnf_req=None)
        mock_delete_persistent_volume.assert_called_once()

    @mock.patch.object(client.CoreV1Api, 'delete_namespaced_resource_quota')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_resource_quota(self, mock_vnf_resource_list,
                                   mock_delete_namespaced_resource_quota):
        resource_name = "fake_namespace,fake_name"
        resource_type = "v1,ResourceQuota"
        mock_delete_namespaced_resource_quota.return_value = client.V1Status()
        self._delete_single_vnf_resource(
            mock_vnf_resource_list=mock_vnf_resource_list,
            resource_name=resource_name,
            resource_type=resource_type,
            terminate_vnf_req=None)
        mock_delete_namespaced_resource_quota.assert_called_once()

    @mock.patch.object(client.CoreV1Api, 'delete_namespaced_service_account')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_service_account(self, mock_vnf_resource_list,
                                    mock_delete_namespaced_service_account):
        resource_name = "fake_namespace,fake_name"
        resource_type = "v1,ServiceAccount"
        mock_delete_namespaced_service_account.return_value = client.V1Status()
        self._delete_single_vnf_resource(
            mock_vnf_resource_list=mock_vnf_resource_list,
            resource_name=resource_name,
            resource_type=resource_type,
            terminate_vnf_req=None)
        mock_delete_namespaced_service_account.assert_called_once()

    @mock.patch.object(client.ApiregistrationV1Api, 'delete_api_service')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_api_service(self, mock_vnf_resource_list,
                                mock_delete_api_service):
        resource_name = ",fake_name"
        resource_type = "apiregistration.k8s.io/v1,APIService"
        mock_delete_api_service.return_value = client.V1Status()
        self._delete_single_vnf_resource(
            mock_vnf_resource_list=mock_vnf_resource_list,
            resource_name=resource_name,
            resource_type=resource_type,
            terminate_vnf_req=None)
        mock_delete_api_service.assert_called_once()

    @mock.patch.object(client.AppsV1Api, 'delete_namespaced_daemon_set')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_daemon_set(self, mock_vnf_resource_list,
                               mock_delete_namespaced_daemon_set):
        resource_name = "fake_namespace,fake_name"
        resource_type = "apps/v1,DaemonSet"
        mock_delete_namespaced_daemon_set.return_value = client.V1Status()
        self._delete_single_vnf_resource(
            mock_vnf_resource_list=mock_vnf_resource_list,
            resource_name=resource_name,
            resource_type=resource_type,
            terminate_vnf_req=None)
        mock_delete_namespaced_daemon_set.assert_called_once()

    @mock.patch.object(client.AppsV1Api, 'delete_namespaced_deployment')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_deployment(self, mock_vnf_resource_list,
                               mock_delete_namespaced_deployment):
        resource_name = "fake_namespace,fake_name"
        resource_type = "apps/v1,Deployment"
        mock_delete_namespaced_deployment.return_value = client.V1Status()
        self._delete_single_vnf_resource(
            mock_vnf_resource_list=mock_vnf_resource_list,
            resource_name=resource_name,
            resource_type=resource_type,
            terminate_vnf_req=None)
        mock_delete_namespaced_deployment.assert_called_once()

    @mock.patch.object(client.AppsV1Api, 'delete_namespaced_replica_set')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_replica_set(self, mock_vnf_resource_list,
                                mock_delete_namespaced_replica_set):
        resource_name = "fake_namespace,fake_name"
        resource_type = "apps/v1,ReplicaSet"
        mock_delete_namespaced_replica_set.return_value = client.V1Status()
        self._delete_single_vnf_resource(
            mock_vnf_resource_list=mock_vnf_resource_list,
            resource_name=resource_name,
            resource_type=resource_type,
            terminate_vnf_req=None)
        mock_delete_namespaced_replica_set.assert_called_once()

    @mock.patch.object(client.CoreV1Api,
                       'delete_namespaced_persistent_volume_claim')
    @mock.patch.object(client.CoreV1Api,
                       'list_namespaced_persistent_volume_claim')
    @mock.patch.object(client.AppsV1Api, 'read_namespaced_stateful_set')
    @mock.patch.object(client.AppsV1Api, 'delete_namespaced_stateful_set')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_stateful_set(self, mock_vnf_resource_list,
                            mock_delete_namespaced_stateful_set,
                            mock_read_namespaced_stateful_set,
                            mock_list_namespaced_persistent_volume_claim,
                            mock_delete_namespaced_persistent_volume_claim):
        resource_name = "curryns,curry-test001"
        resource_type = "apps/v1,StatefulSet"
        mock_delete_namespaced_stateful_set.return_value = client.V1Status()
        mock_delete_namespaced_persistent_volume_claim.return_value = \
            client.V1Status()
        stateful_set_obj = fakes.fake_v1_stateful_set()
        mock_read_namespaced_stateful_set.return_value = stateful_set_obj
        persistent_volume_claim_obj = fakes.\
            fake_v1_persistent_volume_claim()
        persistent_volume_claim_obj2 = fakes.\
            fake_v1_persistent_volume_claim()
        persistent_volume_claim_obj2.metadata.name = 'www-curry-test002-0'
        list_persistent_volume_claim_obj = \
            client.V1PersistentVolumeClaimList(
                items=[persistent_volume_claim_obj,
                       persistent_volume_claim_obj2])
        mock_list_namespaced_persistent_volume_claim.return_value = \
            list_persistent_volume_claim_obj
        self._delete_single_vnf_resource(
            mock_vnf_resource_list=mock_vnf_resource_list,
            resource_name=resource_name,
            resource_type=resource_type,
            terminate_vnf_req=None)
        mock_delete_namespaced_stateful_set.assert_called_once()
        mock_read_namespaced_stateful_set.assert_called_once()
        mock_list_namespaced_persistent_volume_claim.assert_called_once()
        mock_delete_namespaced_persistent_volume_claim.assert_called_once()

    @mock.patch.object(client.AppsV1Api,
            'delete_namespaced_controller_revision')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_controller_revision(self, mock_vnf_resource_list,
                                mock_delete_namespaced_controller_revision):
        resource_name = "fake_namespace,fake_name"
        resource_type = "apps/v1,ControllerRevision"
        mock_delete_namespaced_controller_revision.return_value = \
            client.V1Status()
        self._delete_single_vnf_resource(
            mock_vnf_resource_list=mock_vnf_resource_list,
            resource_name=resource_name,
            resource_type=resource_type,
            terminate_vnf_req=None)
        mock_delete_namespaced_controller_revision.assert_called_once()

    @mock.patch.object(client.AutoscalingV1Api,
            'delete_namespaced_horizontal_pod_autoscaler')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_horizontal_pod_autoscaler(self, mock_vnf_resource_list,
                            mock_delete_namespaced_horizontal_pod_autoscaler):
        resource_name = "fake_namespace,fake_name"
        resource_type = "autoscaling/v1,HorizontalPodAutoscaler"
        mock_delete_namespaced_horizontal_pod_autoscaler.return_value = \
            client.V1Status()
        self._delete_single_vnf_resource(
            mock_vnf_resource_list=mock_vnf_resource_list,
            resource_name=resource_name,
            resource_type=resource_type,
            terminate_vnf_req=None)
        mock_delete_namespaced_horizontal_pod_autoscaler.assert_called_once()

    @mock.patch.object(client.BatchV1Api, 'delete_namespaced_job')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_job(self, mock_vnf_resource_list,
                        mock_delete_namespaced_job):
        resource_name = "fake_namespace,fake_name"
        resource_type = "batch/v1,Job"
        mock_delete_namespaced_job.return_value = client.V1Status()
        self._delete_single_vnf_resource(
            mock_vnf_resource_list=mock_vnf_resource_list,
            resource_name=resource_name,
            resource_type=resource_type,
            terminate_vnf_req=None)
        mock_delete_namespaced_job.assert_called_once()

    @mock.patch.object(client.CoordinationV1Api, 'delete_namespaced_lease')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_lease(self, mock_vnf_resource_list,
                          mock_delete_namespaced_lease):
        resource_name = "fake_namespace,fake_name"
        resource_type = "coordination.k8s.io/v1,Lease"
        mock_delete_namespaced_lease.return_value = client.V1Status()
        self._delete_single_vnf_resource(
            mock_vnf_resource_list=mock_vnf_resource_list,
            resource_name=resource_name,
            resource_type=resource_type,
            terminate_vnf_req=None)
        mock_delete_namespaced_lease.assert_called_once()

    @mock.patch.object(client.NetworkingV1Api,
            'delete_namespaced_network_policy')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_network_policy(self, mock_vnf_resource_list,
                                   mock_delete_namespaced_network_policy):
        resource_name = "fake_namespace,fake_name"
        resource_type = "networking.k8s.io/v1,NetworkPolicy"
        mock_delete_namespaced_network_policy.return_value = client.V1Status()
        self._delete_single_vnf_resource(
            mock_vnf_resource_list=mock_vnf_resource_list,
            resource_name=resource_name,
            resource_type=resource_type,
            terminate_vnf_req=None)
        mock_delete_namespaced_network_policy.assert_called_once()

    @mock.patch.object(client.RbacAuthorizationV1Api,
            'delete_cluster_role')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_cluster_role(self, mock_vnf_resource_list,
                                 mock_delete_cluster_role):
        resource_name = ",fake_name"
        resource_type = "rbac.authorization.k8s.io/v1,ClusterRole"
        mock_delete_cluster_role.return_value = client.V1Status()
        self._delete_single_vnf_resource(
            mock_vnf_resource_list=mock_vnf_resource_list,
            resource_name=resource_name,
            resource_type=resource_type,
            terminate_vnf_req=None)
        mock_delete_cluster_role.assert_called_once()

    @mock.patch.object(client.RbacAuthorizationV1Api,
            'delete_cluster_role_binding')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_cluster_role_binding(self, mock_vnf_resource_list,
                                         mock_delete_cluster_role_binding):
        resource_name = ",fake_name"
        resource_type = "rbac.authorization.k8s.io/v1,ClusterRoleBinding"
        mock_delete_cluster_role_binding.return_value = \
            client.V1Status()
        self._delete_single_vnf_resource(
            mock_vnf_resource_list=mock_vnf_resource_list,
            resource_name=resource_name,
            resource_type=resource_type,
            terminate_vnf_req=None)
        mock_delete_cluster_role_binding.assert_called_once()

    @mock.patch.object(client.RbacAuthorizationV1Api,
            'delete_namespaced_role')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_role(self, mock_vnf_resource_list,
                         mock_delete_namespaced_role):
        resource_name = "fake_namespace,fake_name"
        resource_type = "rbac.authorization.k8s.io/v1,Role"
        mock_delete_namespaced_role.return_value = client.V1Status()
        self._delete_single_vnf_resource(
            mock_vnf_resource_list=mock_vnf_resource_list,
            resource_name=resource_name,
            resource_type=resource_type,
            terminate_vnf_req=None)
        mock_delete_namespaced_role.assert_called_once()

    @mock.patch.object(client.RbacAuthorizationV1Api,
            'delete_namespaced_role_binding')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_role_binding(self, mock_vnf_resource_list,
                                 mock_delete_namespaced_role_binding):
        resource_name = "fake_namespace,fake_name"
        resource_type = "rbac.authorization.k8s.io/v1,RoleBinding"
        mock_delete_namespaced_role_binding.return_value = client.V1Status()
        self._delete_single_vnf_resource(
            mock_vnf_resource_list=mock_vnf_resource_list,
            resource_name=resource_name,
            resource_type=resource_type,
            terminate_vnf_req=None)
        mock_delete_namespaced_role_binding.assert_called_once()

    @mock.patch.object(client.SchedulingV1Api, 'delete_priority_class')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_priority_class(self, mock_vnf_resource_list,
                                   mock_delete_priority_class):
        resource_name = ",fake_name"
        resource_type = "scheduling.k8s.io/v1,PriorityClass"
        mock_delete_priority_class.return_value = client.V1Status()
        self._delete_single_vnf_resource(
            mock_vnf_resource_list=mock_vnf_resource_list,
            resource_name=resource_name,
            resource_type=resource_type,
            terminate_vnf_req=None)
        mock_delete_priority_class.assert_called_once()

    @mock.patch.object(client.StorageV1Api, 'delete_storage_class')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_storage_class(self, mock_vnf_resource_list,
                                  mock_delete_storage_class):
        resource_name = ",fake_name"
        resource_type = "storage.k8s.io/v1,StorageClass"
        mock_delete_storage_class.return_value = client.V1Status()
        self._delete_single_vnf_resource(
            mock_vnf_resource_list=mock_vnf_resource_list,
            resource_name=resource_name,
            resource_type=resource_type,
            terminate_vnf_req=None)
        mock_delete_storage_class.assert_called_once()

    @mock.patch.object(client.StorageV1Api, 'delete_volume_attachment')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_volume_attachment(self, mock_vnf_resource_list,
                                      mock_delete_volume_attachment):
        resource_name = ",fake_name"
        resource_type = "storage.k8s.io/v1,VolumeAttachment"
        mock_delete_volume_attachment.return_value = client.V1Status()
        self._delete_single_vnf_resource(
            mock_vnf_resource_list=mock_vnf_resource_list,
            resource_name=resource_name,
            resource_type=resource_type,
            terminate_vnf_req=None)
        mock_delete_volume_attachment.assert_called_once()

    @mock.patch.object(client.CoreV1Api,
            'delete_namespaced_persistent_volume_claim')
    @mock.patch.object(client.CoreV1Api, 'delete_persistent_volume')
    @mock.patch.object(client.StorageV1Api, 'delete_storage_class')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_multiple_resources(self, mock_vnf_resource_list,
                            mock_delete_storage_class,
                            mock_delete_persistent_volume,
                            mock_delete_namespaced_persistent_volume_claim):
        vnf_id = 'fake_vnf_id'
        vnf_instance = fd_utils.get_vnf_instance_object()
        vnf_instance_id = vnf_instance.id
        terminate_vnf_req = objects.TerminateVnfRequest(
            termination_type=fields.VnfInstanceTerminationType.GRACEFUL,
            graceful_termination_timeout=5)
        vnf_resource1 = models.VnfResource()
        vnf_resource1.vnf_instance_id = vnf_instance_id
        vnf_resource1.resource_name = ",fake_name1"
        vnf_resource1.resource_type = "storage.k8s.io/v1,StorageClass"
        vnf_resource2 = models.VnfResource()
        vnf_resource2.vnf_instance_id = vnf_instance_id
        vnf_resource2.resource_name = ",fake_name2"
        vnf_resource2.resource_type = "v1,PersistentVolume"
        vnf_resource3 = models.VnfResource()
        vnf_resource3.vnf_instance_id = vnf_instance_id
        vnf_resource3.resource_name = "fake_namespace,fake_name3"
        vnf_resource3.resource_type = "v1,PersistentVolumeClaim"
        mock_vnf_resource_list.return_value = \
            [vnf_resource1, vnf_resource2, vnf_resource3]
        mock_delete_storage_class.return_value = client.V1Status()
        mock_delete_persistent_volume.return_value = \
            client.V1Status()
        mock_delete_namespaced_persistent_volume_claim.return_value = \
            client.V1Status()
        self.kubernetes.delete(plugin=None, context=self.context,
                               vnf_id=vnf_id,
                               auth_attr=utils.get_vim_auth_obj(),
                               vnf_instance=vnf_instance,
                               terminate_vnf_req=terminate_vnf_req)
        mock_delete_storage_class.assert_called_once()
        mock_delete_persistent_volume.assert_called_once()
        mock_delete_namespaced_persistent_volume_claim.assert_called_once()

    @mock.patch.object(client.CoreV1Api, 'delete_namespaced_pod')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_pod_api_fail(self, mock_vnf_resource_list,
                                 mock_delete_namespaced_pod):
        resource_name = "fake_namespace,fake_name"
        resource_type = "v1,Pod"
        mock_delete_namespaced_pod.side_effect = Exception()
        self._delete_single_vnf_resource(
            mock_vnf_resource_list=mock_vnf_resource_list,
            resource_name=resource_name,
            resource_type=resource_type,
            terminate_vnf_req=None)
        mock_delete_namespaced_pod.assert_called_once()

    @mock.patch.object(client.CoreV1Api,
                       'list_namespaced_persistent_volume_claim')
    @mock.patch.object(client.AppsV1Api, 'read_namespaced_stateful_set')
    @mock.patch.object(client.AppsV1Api, 'delete_namespaced_stateful_set')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_stateful_set_pvc_not_exist(self, mock_vnf_resource_list,
                            mock_delete_namespaced_stateful_set,
                            mock_read_namespaced_stateful_set,
                            mock_list_namespaced_persistent_volume_claim):
        resource_name = "curryns,curry-test001"
        resource_type = "apps/v1,StatefulSet"
        mock_delete_namespaced_stateful_set.return_value = client.V1Status()
        stateful_set_obj = fakes.fake_v1_stateful_set()
        mock_read_namespaced_stateful_set.return_value = stateful_set_obj
        mock_list_namespaced_persistent_volume_claim.side_effect = Exception()
        self._delete_single_vnf_resource(
            mock_vnf_resource_list=mock_vnf_resource_list,
            resource_name=resource_name,
            resource_type=resource_type,
            terminate_vnf_req=None)
        mock_delete_namespaced_stateful_set.assert_called_once()
        mock_read_namespaced_stateful_set.assert_called_once()
        mock_list_namespaced_persistent_volume_claim.assert_called_once()

    @mock.patch.object(client.AppsV1Api, 'read_namespaced_stateful_set')
    @mock.patch.object(client.AppsV1Api, 'delete_namespaced_stateful_set')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_stateful_set_read_sfs_fail(self, mock_vnf_resource_list,
                                        mock_delete_namespaced_stateful_set,
                                        mock_read_namespaced_stateful_set):
        resource_name = "curryns,curry-test001"
        resource_type = "apps/v1,StatefulSet"
        mock_delete_namespaced_stateful_set.return_value = client.V1Status()
        mock_read_namespaced_stateful_set.side_effect = Exception()
        self._delete_single_vnf_resource(
            mock_vnf_resource_list=mock_vnf_resource_list,
            resource_name=resource_name,
            resource_type=resource_type,
            terminate_vnf_req=None)
        mock_delete_namespaced_stateful_set.assert_called_once()
        mock_read_namespaced_stateful_set.assert_called_once()

    def _delete_wait_single_vnf_resource(self, mock_vnf_resource_list,
                                         resource_name, resource_type):
        vnf_id = 'fake_vnf_id'
        vnf_instance_id = '4a4c2d44-8a52-4895-9a75-9d1c76c3e738'
        vnf_instance = fd_utils.get_vnf_instance_object()
        vnf_instance.id = vnf_instance_id
        vnf_resource = models.VnfResource()
        vnf_resource.vnf_instance_id = vnf_instance_id
        vnf_resource.resource_name = resource_name
        vnf_resource.resource_type = resource_type
        mock_vnf_resource_list.return_value = [vnf_resource]
        self.kubernetes.delete_wait(plugin=None, context=self.context,
                                    vnf_id=vnf_id,
                                    auth_attr=utils.get_vim_auth_obj(),
                                    region_name=None,
                                    vnf_instance=vnf_instance)

    @mock.patch.object(client.CoreV1Api, 'read_namespaced_pod')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_wait_pod(self, mock_vnf_resource_list,
                             mock_read_namespaced_pod):
        resource_name = "fake_namespace,fake_name"
        resource_type = "v1,Pod"
        mock_read_namespaced_pod.side_effect = Exception()
        self._delete_wait_single_vnf_resource(
            mock_vnf_resource_list=mock_vnf_resource_list,
            resource_name=resource_name,
            resource_type=resource_type)
        mock_read_namespaced_pod.assert_called_once()

    @mock.patch.object(client.CoreV1Api, 'read_namespaced_service')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_wait_service(self, mock_vnf_resource_list,
                                 mock_read_namespaced_service):
        resource_name = "fake_namespace,fake_name"
        resource_type = "v1,Service"
        mock_read_namespaced_service.side_effect = Exception()
        self._delete_wait_single_vnf_resource(
            mock_vnf_resource_list=mock_vnf_resource_list,
            resource_name=resource_name,
            resource_type=resource_type)
        mock_read_namespaced_service.assert_called_once()

    @mock.patch.object(client.CoreV1Api, 'read_namespaced_secret')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_wait_secret(self, mock_vnf_resource_list,
                                mock_read_namespaced_secret):
        resource_name = "fake_namespace,fake_name"
        resource_type = "v1,Secret"
        mock_read_namespaced_secret.side_effect = Exception()
        self._delete_wait_single_vnf_resource(
            mock_vnf_resource_list=mock_vnf_resource_list,
            resource_name=resource_name,
            resource_type=resource_type)
        mock_read_namespaced_secret.assert_called_once()

    @mock.patch.object(client.CoreV1Api, 'read_namespaced_config_map')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_wait_config_map(self, mock_vnf_resource_list,
                                    mock_read_namespaced_config_map):
        resource_name = "fake_namespace,fake_name"
        resource_type = "v1,ConfigMap"
        mock_read_namespaced_config_map.side_effect = Exception()
        self._delete_wait_single_vnf_resource(
            mock_vnf_resource_list=mock_vnf_resource_list,
            resource_name=resource_name,
            resource_type=resource_type)
        mock_read_namespaced_config_map.assert_called_once()

    @mock.patch.object(client.CoreV1Api,
            'read_namespaced_persistent_volume_claim')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_wait_persistent_volume_claim(self, mock_vnf_resource_list,
                                mock_read_namespaced_persistent_volume_claim):
        resource_name = "fake_namespace,fake_name"
        resource_type = "v1,PersistentVolumeClaim"
        mock_read_namespaced_persistent_volume_claim.side_effect = Exception()
        self._delete_wait_single_vnf_resource(
            mock_vnf_resource_list=mock_vnf_resource_list,
            resource_name=resource_name,
            resource_type=resource_type)
        mock_read_namespaced_persistent_volume_claim.assert_called_once()

    @mock.patch.object(client.CoreV1Api, 'read_namespaced_limit_range')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_wait_limit_range(self, mock_vnf_resource_list,
                                     mock_read_namespaced_limit_range):
        resource_name = "fake_namespace,fake_name"
        resource_type = "v1,LimitRange"
        mock_read_namespaced_limit_range.side_effect = Exception()
        self._delete_wait_single_vnf_resource(
            mock_vnf_resource_list=mock_vnf_resource_list,
            resource_name=resource_name,
            resource_type=resource_type)
        mock_read_namespaced_limit_range.assert_called_once()

    @mock.patch.object(client.CoreV1Api, 'read_namespaced_pod_template')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_wait_pod_template(self, mock_vnf_resource_list,
                                      mock_read_namespaced_pod_template):
        resource_name = "fake_namespace,fake_name"
        resource_type = "v1,PodTemplate"
        mock_read_namespaced_pod_template.side_effect = Exception()
        self._delete_wait_single_vnf_resource(
            mock_vnf_resource_list=mock_vnf_resource_list,
            resource_name=resource_name,
            resource_type=resource_type)
        mock_read_namespaced_pod_template.assert_called_once()

    @mock.patch.object(client.CoreV1Api, 'read_namespace')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_wait_namespace(self, mock_vnf_resource_list,
                                   mock_read_namespace):
        resource_name = ",fake_name"
        resource_type = "v1,Namespace"
        mock_read_namespace.side_effect = Exception()
        self._delete_wait_single_vnf_resource(
            mock_vnf_resource_list=mock_vnf_resource_list,
            resource_name=resource_name,
            resource_type=resource_type)
        mock_read_namespace.assert_called_once()

    @mock.patch.object(client.CoreV1Api, 'read_persistent_volume')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_wait_persistent_volume(self, mock_vnf_resource_list,
                                           mock_read_persistent_volume):
        resource_name = ",fake_name"
        resource_type = "v1,PersistentVolume"
        mock_read_persistent_volume.side_effect = Exception()
        self._delete_wait_single_vnf_resource(
            mock_vnf_resource_list=mock_vnf_resource_list,
            resource_name=resource_name,
            resource_type=resource_type)
        mock_read_persistent_volume.assert_called_once()

    @mock.patch.object(client.CoreV1Api, 'read_namespaced_resource_quota')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_wait_resource_quota(self, mock_vnf_resource_list,
                                        mock_read_namespaced_resource_quota):
        resource_name = "fake_namespace,fake_name"
        resource_type = "v1,ResourceQuota"
        mock_read_namespaced_resource_quota.side_effect = Exception()
        self._delete_wait_single_vnf_resource(
            mock_vnf_resource_list=mock_vnf_resource_list,
            resource_name=resource_name,
            resource_type=resource_type)
        mock_read_namespaced_resource_quota.assert_called_once()

    @mock.patch.object(client.CoreV1Api, 'read_namespaced_service_account')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_wait_service_account(self, mock_vnf_resource_list,
                                         mock_read_namespaced_service_account):
        resource_name = "fake_namespace,fake_name"
        resource_type = "v1,ServiceAccount"
        mock_read_namespaced_service_account.side_effect = Exception()
        self._delete_wait_single_vnf_resource(
            mock_vnf_resource_list=mock_vnf_resource_list,
            resource_name=resource_name,
            resource_type=resource_type)
        mock_read_namespaced_service_account.assert_called_once()

    @mock.patch.object(client.ApiregistrationV1Api, 'read_api_service')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_wait_api_service(self, mock_vnf_resource_list,
                                     mock_read_api_service):
        resource_name = ",fake_name"
        resource_type = "apiregistration.k8s.io/v1,APIService"
        mock_read_api_service.side_effect = Exception()
        self._delete_wait_single_vnf_resource(
            mock_vnf_resource_list=mock_vnf_resource_list,
            resource_name=resource_name,
            resource_type=resource_type)
        mock_read_api_service.assert_called_once()

    @mock.patch.object(client.AppsV1Api, 'read_namespaced_daemon_set')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_wait_daemon_set(self, mock_vnf_resource_list,
                                    mock_read_namespaced_daemon_set):
        resource_name = "fake_namespace,fake_name"
        resource_type = "apps/v1,DaemonSet"
        mock_read_namespaced_daemon_set.side_effect = Exception()
        self._delete_wait_single_vnf_resource(
            mock_vnf_resource_list=mock_vnf_resource_list,
            resource_name=resource_name,
            resource_type=resource_type)
        mock_read_namespaced_daemon_set.assert_called_once()

    @mock.patch.object(client.AppsV1Api, 'read_namespaced_deployment')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_wait_deployment(self, mock_vnf_resource_list,
                                    mock_read_namespaced_deployment):
        resource_name = "fake_namespace,fake_name"
        resource_type = "apps/v1,Deployment"
        mock_read_namespaced_deployment.side_effect = Exception()
        self._delete_wait_single_vnf_resource(
            mock_vnf_resource_list=mock_vnf_resource_list,
            resource_name=resource_name,
            resource_type=resource_type)
        mock_read_namespaced_deployment.assert_called_once()

    @mock.patch.object(client.AppsV1Api, 'read_namespaced_replica_set')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_wait_replica_set(self, mock_vnf_resource_list,
                                     mock_read_namespaced_replica_set):
        resource_name = "fake_namespace,fake_name"
        resource_type = "apps/v1,ReplicaSet"
        mock_read_namespaced_replica_set.side_effect = Exception()
        self._delete_wait_single_vnf_resource(
            mock_vnf_resource_list=mock_vnf_resource_list,
            resource_name=resource_name,
            resource_type=resource_type)
        mock_read_namespaced_replica_set.assert_called_once()

    @mock.patch.object(client.AppsV1Api, 'read_namespaced_stateful_set')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_wait_stateful_set(self, mock_vnf_resource_list,
                                      mock_read_namespaced_stateful_set):
        resource_name = "curryns,curry-test001"
        resource_type = "apps/v1,StatefulSet"
        mock_read_namespaced_stateful_set.side_effect = Exception()
        self._delete_wait_single_vnf_resource(
            mock_vnf_resource_list=mock_vnf_resource_list,
            resource_name=resource_name,
            resource_type=resource_type)
        mock_read_namespaced_stateful_set.assert_called_once()

    @mock.patch.object(client.AppsV1Api,
            'read_namespaced_controller_revision')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_wait_controller_revision(self, mock_vnf_resource_list,
                                mock_read_namespaced_controller_revision):
        resource_name = "fake_namespace,fake_name"
        resource_type = "apps/v1,ControllerRevision"
        mock_read_namespaced_controller_revision.side_effect = Exception()
        self._delete_wait_single_vnf_resource(
            mock_vnf_resource_list=mock_vnf_resource_list,
            resource_name=resource_name,
            resource_type=resource_type)
        mock_read_namespaced_controller_revision.assert_called_once()

    @mock.patch.object(client.AutoscalingV1Api,
            'read_namespaced_horizontal_pod_autoscaler')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_wait_horizontal_pod_autoscaler(self,
                            mock_vnf_resource_list,
                            mock_read_namespaced_horizontal_pod_autoscaler):
        resource_name = "fake_namespace,fake_name"
        resource_type = "autoscaling/v1,HorizontalPodAutoscaler"
        mock_read_namespaced_horizontal_pod_autoscaler.side_effect = \
            Exception()
        self._delete_wait_single_vnf_resource(
            mock_vnf_resource_list=mock_vnf_resource_list,
            resource_name=resource_name,
            resource_type=resource_type)
        mock_read_namespaced_horizontal_pod_autoscaler.assert_called_once()

    @mock.patch.object(client.BatchV1Api, 'read_namespaced_job')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_wait_job(self, mock_vnf_resource_list,
                             mock_read_namespaced_job):
        resource_name = "fake_namespace,fake_name"
        resource_type = "batch/v1,Job"
        mock_read_namespaced_job.side_effect = Exception()
        self._delete_wait_single_vnf_resource(
            mock_vnf_resource_list=mock_vnf_resource_list,
            resource_name=resource_name,
            resource_type=resource_type)
        mock_read_namespaced_job.assert_called_once()

    @mock.patch.object(client.CoordinationV1Api, 'read_namespaced_lease')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_wait_lease(self, mock_vnf_resource_list,
                               mock_read_namespaced_lease):
        resource_name = "fake_namespace,fake_name"
        resource_type = "coordination.k8s.io/v1,Lease"
        mock_read_namespaced_lease.side_effect = Exception()
        self._delete_wait_single_vnf_resource(
            mock_vnf_resource_list=mock_vnf_resource_list,
            resource_name=resource_name,
            resource_type=resource_type)
        mock_read_namespaced_lease.assert_called_once()

    @mock.patch.object(client.NetworkingV1Api,
            'read_namespaced_network_policy')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_wait_network_policy(self, mock_vnf_resource_list,
                                        mock_read_namespaced_network_policy):
        resource_name = "fake_namespace,fake_name"
        resource_type = "networking.k8s.io/v1,NetworkPolicy"
        mock_read_namespaced_network_policy.side_effect = Exception()
        self._delete_wait_single_vnf_resource(
            mock_vnf_resource_list=mock_vnf_resource_list,
            resource_name=resource_name,
            resource_type=resource_type)
        mock_read_namespaced_network_policy.assert_called_once()

    @mock.patch.object(client.RbacAuthorizationV1Api,
            'read_cluster_role')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_wait_cluster_role(self, mock_vnf_resource_list,
                                      mock_read_cluster_role):
        resource_name = ",fake_name"
        resource_type = "rbac.authorization.k8s.io/v1,ClusterRole"
        mock_read_cluster_role.side_effect = Exception()
        self._delete_wait_single_vnf_resource(
            mock_vnf_resource_list=mock_vnf_resource_list,
            resource_name=resource_name,
            resource_type=resource_type)
        mock_read_cluster_role.assert_called_once()

    @mock.patch.object(client.RbacAuthorizationV1Api,
            'read_cluster_role_binding')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_wait_cluster_role_binding(self, mock_vnf_resource_list,
                                              mock_read_cluster_role_binding):
        resource_name = ",fake_name"
        resource_type = "rbac.authorization.k8s.io/v1,ClusterRoleBinding"
        mock_read_cluster_role_binding.side_effect = Exception()
        self._delete_wait_single_vnf_resource(
            mock_vnf_resource_list=mock_vnf_resource_list,
            resource_name=resource_name,
            resource_type=resource_type)
        mock_read_cluster_role_binding.assert_called_once()

    @mock.patch.object(client.RbacAuthorizationV1Api,
            'read_namespaced_role')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_wait_role(self, mock_vnf_resource_list,
                              mock_read_namespaced_role):
        resource_name = "fake_namespace,fake_name"
        resource_type = "rbac.authorization.k8s.io/v1,Role"
        mock_read_namespaced_role.side_effect = Exception()
        self._delete_wait_single_vnf_resource(
            mock_vnf_resource_list=mock_vnf_resource_list,
            resource_name=resource_name,
            resource_type=resource_type)
        mock_read_namespaced_role.assert_called_once()

    @mock.patch.object(client.RbacAuthorizationV1Api,
            'read_namespaced_role_binding')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_wait_role_binding(self, mock_vnf_resource_list,
                                      mock_read_namespaced_role_binding):
        resource_name = "fake_namespace,fake_name"
        resource_type = "rbac.authorization.k8s.io/v1,RoleBinding"
        mock_read_namespaced_role_binding.side_effect = Exception()
        self._delete_wait_single_vnf_resource(
            mock_vnf_resource_list=mock_vnf_resource_list,
            resource_name=resource_name,
            resource_type=resource_type)
        mock_read_namespaced_role_binding.assert_called_once()

    @mock.patch.object(client.SchedulingV1Api, 'read_priority_class')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_wait_priority_class(self, mock_vnf_resource_list,
                                        mock_read_priority_class):
        resource_name = ",fake_name"
        resource_type = "scheduling.k8s.io/v1,PriorityClass"
        mock_read_priority_class.side_effect = Exception()
        self._delete_wait_single_vnf_resource(
            mock_vnf_resource_list=mock_vnf_resource_list,
            resource_name=resource_name,
            resource_type=resource_type)
        mock_read_priority_class.assert_called_once()

    @mock.patch.object(client.StorageV1Api, 'read_storage_class')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_wait_storage_class(self, mock_vnf_resource_list,
                                       mock_read_storage_class):
        resource_name = ",fake_name"
        resource_type = "storage.k8s.io/v1,StorageClass"
        mock_read_storage_class.side_effect = Exception()
        self._delete_wait_single_vnf_resource(
            mock_vnf_resource_list=mock_vnf_resource_list,
            resource_name=resource_name,
            resource_type=resource_type)
        mock_read_storage_class.assert_called_once()

    @mock.patch.object(client.StorageV1Api, 'read_volume_attachment')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_wait_volume_attachment(self, mock_vnf_resource_list,
                                           mock_read_volume_attachment):
        resource_name = ",fake_name"
        resource_type = "storage.k8s.io/v1,VolumeAttachment"
        mock_read_volume_attachment.side_effect = Exception()
        self._delete_wait_single_vnf_resource(
            mock_vnf_resource_list=mock_vnf_resource_list,
            resource_name=resource_name,
            resource_type=resource_type)
        mock_read_volume_attachment.assert_called_once()

    @mock.patch.object(client.CoreV1Api, 'read_namespaced_pod')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_wait_retry(self, mock_vnf_resource_list,
                             mock_read_namespaced_pod):
        resource_name = "fake_namespace,fake_name"
        resource_type = "v1,Pod"
        mock_read_namespaced_pod.return_value = client.V1Status()
        self._delete_wait_single_vnf_resource(
            mock_vnf_resource_list=mock_vnf_resource_list,
            resource_name=resource_name,
            resource_type=resource_type)
        mock_read_namespaced_pod.assert_called()

    @mock.patch.object(client.AppsV1Api, 'delete_namespaced_deployment')
    @mock.patch.object(client.AutoscalingV1Api,
            'delete_namespaced_horizontal_pod_autoscaler')
    @mock.patch.object(client.CoreV1Api, 'delete_namespaced_service')
    @mock.patch.object(client.CoreV1Api, 'delete_namespaced_config_map')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_legacy(self, mock_vnf_resource_list,
                           mock_delete_namespaced_config_map,
                           mock_delete_namespaced_service,
                           mock_delete_namespaced_horizontal_pod_autoscaler,
                           mock_delete_namespaced_deployment):
        vnf_id = "fake_namespace,fake_name"
        mock_vnf_resource_list.return_value = list()
        mock_delete_namespaced_config_map.return_value = client.V1Status()
        mock_delete_namespaced_service.return_value = client.V1Status()
        mock_delete_namespaced_horizontal_pod_autoscaler.return_value = \
            client.V1Status()
        mock_delete_namespaced_deployment.return_value = client.V1Status()
        self.kubernetes.delete(plugin=None, context=self.context,
                               vnf_id=vnf_id,
                               auth_attr=utils.get_vim_auth_obj(),
                               vnf_instance=None,
                               terminate_vnf_req=None)
        mock_delete_namespaced_config_map.assert_called_once()
        mock_delete_namespaced_horizontal_pod_autoscaler.assert_called_once()
        mock_delete_namespaced_service.assert_called_once()
        mock_delete_namespaced_config_map.assert_called_once()

    @mock.patch.object(client.AppsV1Api, 'delete_namespaced_deployment')
    @mock.patch.object(client.AutoscalingV1Api,
            'delete_namespaced_horizontal_pod_autoscaler')
    @mock.patch.object(client.CoreV1Api, 'delete_namespaced_service')
    @mock.patch.object(client.CoreV1Api, 'delete_namespaced_config_map')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_legacy_delete_api_fail(self, mock_vnf_resource_list,
                           mock_delete_namespaced_config_map,
                           mock_delete_namespaced_service,
                           mock_delete_namespaced_horizontal_pod_autoscaler,
                           mock_delete_namespaced_deployment):
        vnf_id = "fake_namespace,fake_name"
        mock_vnf_resource_list.return_value = list()
        mock_delete_namespaced_config_map.side_effect = Exception()
        mock_delete_namespaced_service.side_effect = Exception()
        mock_delete_namespaced_horizontal_pod_autoscaler.side_effect = \
            Exception()
        mock_delete_namespaced_deployment.side_effect = Exception()
        self.kubernetes.delete(plugin=None, context=self.context,
                               vnf_id=vnf_id,
                               auth_attr=utils.get_vim_auth_obj(),
                               vnf_instance=None,
                               terminate_vnf_req=None)
        mock_delete_namespaced_config_map.assert_called_once()
        mock_delete_namespaced_horizontal_pod_autoscaler.assert_called_once()
        mock_delete_namespaced_service.assert_called_once()
        mock_delete_namespaced_config_map.assert_called_once()

    @mock.patch.object(client.AppsV1Api, 'read_namespaced_deployment')
    @mock.patch.object(client.AutoscalingV1Api,
            'read_namespaced_horizontal_pod_autoscaler')
    @mock.patch.object(client.CoreV1Api, 'read_namespaced_service')
    @mock.patch.object(client.CoreV1Api, 'read_namespaced_config_map')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_wait_legacy(self, mock_vnf_resource_list,
                            mock_read_namespaced_config_map,
                            mock_read_namespaced_service,
                            mock_read_namespaced_horizontal_pod_autoscaler,
                            mock_read_namespaced_deployment):
        vnf_id = "fake_namespace,fake_name"
        mock_vnf_resource_list.return_value = list()
        mock_read_namespaced_config_map.side_effect = Exception()
        mock_read_namespaced_service.side_effect = Exception()
        mock_read_namespaced_horizontal_pod_autoscaler.side_effect = \
            Exception()
        mock_read_namespaced_deployment.side_effect = Exception()
        self.kubernetes.delete_wait(plugin=None, context=self.context,
                                    vnf_id=vnf_id,
                                    auth_attr=utils.get_vim_auth_obj(),
                                    region_name=None,
                                    vnf_instance=None)
        mock_read_namespaced_config_map.assert_called_once()
        mock_read_namespaced_service.assert_called_once()
        mock_read_namespaced_horizontal_pod_autoscaler.assert_called_once()
        mock_read_namespaced_deployment.assert_called_once()

    @mock.patch.object(client.AppsV1Api, 'read_namespaced_deployment')
    @mock.patch.object(client.AutoscalingV1Api,
            'read_namespaced_horizontal_pod_autoscaler')
    @mock.patch.object(client.CoreV1Api, 'read_namespaced_service')
    @mock.patch.object(client.CoreV1Api, 'read_namespaced_config_map')
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_delete_wait_legacy_retry(self, mock_vnf_resource_list,
                            mock_read_namespaced_config_map,
                            mock_read_namespaced_service,
                            mock_read_namespaced_horizontal_pod_autoscaler,
                            mock_read_namespaced_deployment):
        vnf_id = "fake_namespace,fake_name"
        mock_vnf_resource_list.return_value = list()
        mock_read_namespaced_config_map.return_value = client.V1Status()
        mock_read_namespaced_service.return_value = client.V1Status()
        mock_read_namespaced_horizontal_pod_autoscaler.return_value = \
            client.V1Status()
        mock_read_namespaced_deployment.return_value = client.V1Status()
        self.kubernetes.delete_wait(plugin=None, context=self.context,
                                    vnf_id=vnf_id,
                                    auth_attr=utils.get_vim_auth_obj(),
                                    region_name=None,
                                    vnf_instance=None)
        mock_read_namespaced_config_map.assert_called()
        mock_read_namespaced_service.assert_called()
        mock_read_namespaced_horizontal_pod_autoscaler.assert_called()
        mock_read_namespaced_deployment.assert_called()
