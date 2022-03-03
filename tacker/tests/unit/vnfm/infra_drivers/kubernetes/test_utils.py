# Licensed under the Apache License, Version 2.0 (the "License"); you may
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

from tacker.common import exceptions
from tacker import objects
from tacker.tests.unit import base
from tacker.tests.unit.vnfm.infra_drivers.openstack.fixture_data import (
    fixture_data_utils as fd_utils
)
from tacker.vnfm.infra_drivers.kubernetes import utils as k8s_utils
from unittest import mock


class KubernetesUtilsTestCase(base.TestCase):

    @mock.patch('tacker.objects.vnf_instance.VnfInstance.save')
    def test_check_and_save_namespace_multi_namespace(self, mock_save):
        instantiate_vnf_req = objects.InstantiateVnfRequest(
            additional_params=None)
        chk_namespaces = [{"namespace": "a", "kind": "CronJob"},
                          {"namespace": "b", "kind": "Deployment"},
                          {"namespace": "c", "kind": "Service"}]
        vnf_instance = fd_utils.get_vnf_instance_object()

        self.assertRaises(
            exceptions.NamespaceIsNotUnique,
            k8s_utils.check_and_save_namespace, instantiate_vnf_req,
            chk_namespaces, vnf_instance)

    @mock.patch('tacker.objects.vnf_instance.VnfInstance.save')
    def test_check_and_save_namespace_no_namespace(self, mock_save):
        instantiate_vnf_req = objects.InstantiateVnfRequest(
            additional_params=None)
        chk_namespaces = []
        vnf_instance = fd_utils.get_vnf_instance_object()
        vnf_instance.vnf_metadata['namespace'] = ''
        k8s_utils.check_and_save_namespace(
            instantiate_vnf_req, chk_namespaces, vnf_instance)
        self.assertEqual('default', vnf_instance.vnf_metadata['namespace'])

    @mock.patch('tacker.objects.vnf_instance.VnfInstance.save')
    def test_check_and_save_namespace_additional_params(self, mock_save):
        instantiate_vnf_req = objects.InstantiateVnfRequest(
            additional_params={'namespace': 'ns1'})
        chk_namespaces = []
        vnf_instance = fd_utils.get_vnf_instance_object()
        vnf_instance.vnf_metadata['namespace'] = ''
        k8s_utils.check_and_save_namespace(
            instantiate_vnf_req, chk_namespaces, vnf_instance)
        self.assertEqual('ns1', vnf_instance.vnf_metadata['namespace'])

    @mock.patch('tacker.objects.vnf_instance.VnfInstance.save')
    def test_check_and_save_namespace_manifests(self, mock_save):
        instantiate_vnf_req = objects.InstantiateVnfRequest(
            additional_params=None)
        chk_namespaces = [{"namespace": "ns2", "kind": "Deployment"}]
        vnf_instance = fd_utils.get_vnf_instance_object()
        vnf_instance.vnf_metadata = {}
        k8s_utils.check_and_save_namespace(
            instantiate_vnf_req, chk_namespaces, vnf_instance)
        self.assertEqual('ns2', vnf_instance.vnf_metadata['namespace'])
