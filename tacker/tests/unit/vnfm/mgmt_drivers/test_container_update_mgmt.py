# Copyright (c) 2022 FUJITSU
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os

from kubernetes import client
from samples.mgmt_driver.kubernetes.container_update import (
    container_update_mgmt as mgmt_driver)
from tacker.common import exceptions
from tacker import context
from tacker.tests.unit import base
from tacker.tests.unit.vnflcm import fakes
from tacker.tests.unit.vnfm.mgmt_drivers import fakes as mgmt_fakes
from tacker.vnflcm import utils as vnflcm_utils
from tacker.vnfm.infra_drivers.kubernetes.kubernetes_driver import Kubernetes
from unittest import mock


class FakeVimClient(mock.Mock):
    pass


class TestContainerUpdate(base.TestCase):

    def setUp(self):
        super(TestContainerUpdate, self).setUp()
        self.context = context.get_admin_context()
        self.cntr_update_mgmt = mgmt_driver.ContainerUpdateMgmtDriver()
        self.vnf_instance = mgmt_fakes.get_vnf_instance_object()
        self.modify_vnf_request = None
        self._mock_vim_client()
        self._stub_get_vim()
        self._mock_get_vnf_package_path()
        self.yaml_path_before = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "../../../etc/samples/etsi/nfv/"
            "test_cnf_container_update_before/")

    def _mock_vim_client(self):
        self.vim_client = mock.Mock(wraps=FakeVimClient())
        fake_vim_client = mock.Mock()
        fake_vim_client.return_value = self.vim_client
        self._mock(
            'tacker.vnfm.vim_client.VimClient', fake_vim_client)

    def _stub_get_vim(self):
        vim_obj = {'vim_id': '15053249-6979-8ee5-67d2-189fa9379534',
                   'vim_name': 'fake_vim', 'vim_auth':
                       {'auth_url': 'http://localhost/identity', 'password':
                           'test_pw', 'username': 'test_user', 'project_name':
                           'test_project'}, 'vim_type': 'openstack', 'tenant':
                       '15053249-6979-8ee5-67d2-189fa9379534'}
        self.vim_client.get_vim.return_value = vim_obj

    def _mock_get_vnf_package_path(self):
        vnflcm_utils.get_vnf_package_path = mock.Mock(
            return_value=os.path.join(
                os.path.abspath(os.path.dirname(__file__)),
                "../../../etc/samples/etsi/nfv/"
                "test_cnf_container_update_after/")
        )

    def test_container_update_get_type(self):
        get_type = self.cntr_update_mgmt.get_type()
        self.assertEqual('mgmt-container-update', get_type)

    def test_container_update_get_name(self):
        get_name = self.cntr_update_mgmt.get_name()
        self.assertEqual('mgmt-container-update', get_name)

    def test_container_update_get_description(self):
        get_description = self.cntr_update_mgmt.get_description()
        self.assertEqual(
            'Tacker Container Update VNF Mgmt Driver', get_description)

    def test_container_update_modify_information_start(self):
        modify_start = self.cntr_update_mgmt.modify_information_start(
            self.context, self.vnf_instance, self.modify_vnf_request)
        self.assertIsNone(modify_start)

    def test_container_update_modify_container_img(self):
        old_containers = [
            client.V1Container(image="curry", name="curry")
        ]

        new_containers = [
            client.V1Container(image="curry1", name="curry")
        ]
        self.cntr_update_mgmt._modify_container_img(
            old_containers, new_containers)
        self.assertEqual('curry1', old_containers[0].image)

    @mock.patch.object(client.CoreV1Api, 'list_namespaced_pod')
    def test_container_update_replace_wait_k8s_timeout(self, mock_list_pod):
        k8s_pod_objs = [
            {'namespace': 'default', 'object': mgmt_fakes.fake_pod()}
        ]
        kube_driver = Kubernetes()
        kube_driver.STACK_RETRIES = 1
        kube_driver.STACK_RETRY_WAIT = 5
        mock_list_pod.return_value = mgmt_fakes.fake_list_pod()
        self.assertRaises(
            exceptions.MgmtDriverOtherError,
            self.cntr_update_mgmt._replace_wait_k8s, kube_driver,
            k8s_pod_objs, client.CoreV1Api, self.vnf_instance)

    @mock.patch.object(client.CoreV1Api, 'list_namespaced_pod')
    def test_container_update_replace_wait_k8s_unknown(self, mock_list_pod):
        k8s_pod_objs = [
            {'namespace': 'default', 'object': mgmt_fakes.fake_pod()}
        ]
        kube_driver = Kubernetes()
        pod_list = mgmt_fakes.fake_list_pod()
        pod_list.items[0].status.phase = 'Unknown'
        mock_list_pod.return_value = pod_list
        self.assertRaises(
            exceptions.MgmtDriverOtherError,
            self.cntr_update_mgmt._replace_wait_k8s, kube_driver,
            k8s_pod_objs, client.CoreV1Api, self.vnf_instance)

    @mock.patch('tacker.objects.vnf_instance.VnfInstance.save')
    @mock.patch('tacker.vnflcm.utils._get_vnfd_dict')
    @mock.patch.object(client.CoreV1Api, 'list_namespaced_pod')
    @mock.patch.object(client.CoreV1Api, 'replace_namespaced_secret')
    @mock.patch.object(client.CoreV1Api, 'replace_namespaced_config_map')
    @mock.patch.object(client.CoreV1Api, 'replace_namespaced_pod')
    @mock.patch.object(client.CoreV1Api, 'read_namespaced_pod')
    def test_container_update_modify_information_end(
            self, mock_read_pod, mock_replace_pod, mock_replace_config_map,
            mock_replace_secret, mock_list_pod, mock_vnfd_dict, mock_save):
        mock_read_pod.return_value = mgmt_fakes.fake_pod()
        mock_list_pod.return_value = client.V1PodList(items=[
            mgmt_fakes.get_fake_pod_info(kind='Pod', name='vdu1')])
        mock_vnfd_dict.return_value = fakes.vnfd_dict_cnf()
        kwargs = {
            'old_vnf_package_path': self.yaml_path_before,
            'configmap_secret_paths': [
                "Files/kubernetes/configmap_2.yaml",
                "Files/kubernetes/secret_2.yaml"
            ]
        }
        self.cntr_update_mgmt.modify_information_end(
            self.context, self.vnf_instance, self.modify_vnf_request, **kwargs)
        self.assertEqual(1, mock_save.call_count)
