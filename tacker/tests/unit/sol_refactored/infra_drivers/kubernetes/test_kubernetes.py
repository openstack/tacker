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

import os

from kubernetes import client
from oslo_utils import uuidutils
from unittest import mock

from tacker import context
from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.common import vnfd_utils
from tacker.sol_refactored.infra_drivers.kubernetes import kubernetes
from tacker.sol_refactored.nfvo import nfvo_client
from tacker.sol_refactored import objects
from tacker.tests.unit import base
from tacker.tests.unit.sol_refactored.infra_drivers.kubernetes import fakes
from tacker.tests import utils


CNF_SAMPLE_VNFD_ID = "b1bb0ce7-ebca-4fa7-95ed-4840d70a1177"


class TestKubernetes(base.TestCase):

    def setUp(self):
        super(TestKubernetes, self).setUp()
        objects.register_all()
        self.driver = kubernetes.Kubernetes()
        self.context = context.get_admin_context()

        sample_dir = utils.test_sample("unit/sol_refactored/samples")
        self.vnfd_1 = vnfd_utils.Vnfd(CNF_SAMPLE_VNFD_ID)
        self.vnfd_1.init_from_csar_dir(os.path.join(sample_dir, "sample2"))

    def test_setup_k8s_reses_fail_diffs(self):
        not_exist = 'Files/kubernetes/not_exist.yaml'
        expected_ex = sol_ex.CnfDefinitionNotFound(
            diff_files=not_exist)
        target_k8s_files = [not_exist]
        ex = self.assertRaises(sol_ex.CnfDefinitionNotFound,
            self.driver._setup_k8s_reses, self.vnfd_1,
            target_k8s_files, mock.Mock(), mock.Mock(), mock.Mock())
        self.assertEqual(expected_ex.detail, ex.detail)

    def test_wait_k8s_reses_ready(self):
        res1 = mock.Mock()
        res1.is_ready = mock.MagicMock(side_effect=[True, True])
        res2 = mock.Mock()
        res2.is_ready = mock.MagicMock(side_effect=[False, True])
        k8s_reses = [res1, res2]

        kubernetes.CHECK_INTERVAL = 1
        self.driver._wait_k8s_reses_ready(k8s_reses)

        self.assertEqual(1, res1.is_ready.call_count)
        self.assertEqual(2, res2.is_ready.call_count)

    def test_wait_k8s_reses_deleted(self):
        res1 = mock.Mock()
        res1.is_exists = mock.MagicMock(side_effect=[True, False])
        res2 = mock.Mock()
        res2.is_exists = mock.MagicMock(side_effect=[True, False])
        k8s_reses = [res1, res2]

        kubernetes.CHECK_INTERVAL = 1
        self.driver._wait_k8s_reses_deleted(k8s_reses)

        self.assertEqual(2, res1.is_exists.call_count)
        self.assertEqual(2, res2.is_exists.call_count)

    @mock.patch('tacker.sol_refactored.infra_drivers.kubernetes.'
                'kubernetes_utils.list_namespaced_pods')
    def test_wait_k8s_reses_updated(self, mock_list_namespaced_pods):
        mock_list_namespaced_pods.return_value = []
        res1 = mock.Mock()
        res1.is_update = mock.MagicMock(side_effect=[False, True])
        res2 = mock.Mock()
        res2.is_update = mock.MagicMock(side_effect=[True, True])
        k8s_reses = [res1, res2]

        kubernetes.CHECK_INTERVAL = 1
        self.driver._wait_k8s_reses_updated(k8s_reses, mock.Mock(),
                                            mock.Mock(), mock.Mock())

        self.assertEqual(2, res1.is_update.call_count)
        self.assertEqual(1, res2.is_update.call_count)

    def test_check_status_timeout(self):
        res1 = mock.Mock()
        res1.is_ready = mock.MagicMock(return_value=False)
        k8s_reses = [res1]

        self.config_fixture.config(group='v2_vnfm',
                                   kubernetes_vim_rsc_wait_timeout=2)
        kubernetes.CHECK_INTERVAL = 1
        self.assertRaises(sol_ex.K8sOperaitionTimeout,
            self.driver._wait_k8s_reses_ready, k8s_reses)

        # maybe 3 but possible 2
        self.assertTrue(res1.is_ready.call_count >= 2)

    @mock.patch.object(nfvo_client.NfvoClient, 'get_vnfd')
    @mock.patch.object(client.CoreV1Api, 'list_namespaced_pod')
    def test_sync_db(
            self, mock_list_namespaced_pod, mock_get_vnfd):
        vnf_instance_obj = fakes.fake_vnf_instance()

        vnfc_rsc_info_obj1, vnfc_info_obj1 = fakes.fake_vnfc_resource_info(
            vdu_id='VDU1', rsc_kind='Deployment',
            pod_name="vdu1-1234567890-abcd", rsc_name="vdu1")

        vnf_instance_obj.instantiatedVnfInfo.vnfcResourceInfo = [
            vnfc_rsc_info_obj1
        ]
        vim_connection_object = fakes.fake_vim_connection_info()
        vnf_instance_obj.vimConnectionInfo['vim1'] = vim_connection_object

        mock_list_namespaced_pod.return_value = client.V1PodList(
            items=[
                fakes.get_fake_pod_info(
                    kind='Deployment', pod_name="vdu1-1234567890-abcd1"),
                fakes.get_fake_pod_info(
                    kind='Deployment', pod_name="vdu1-1234567890-abcd2")])
        mock_get_vnfd.return_value = self.vnfd_1
        vnf_instance_obj.vnfdId = uuidutils.generate_uuid()
        vnf_instance_obj.instantiatedVnfInfo.scaleStatus = [
            fakes.fake_scale_status(vnfd_id=vnf_instance_obj.vnfdId)
        ]

        self.driver.sync_db(
            context=self.context, vnf_instance=vnf_instance_obj,
            vim_info=vim_connection_object)

        self.assertEqual(
            2, vnf_instance_obj.instantiatedVnfInfo.metadata[
                'vdu_reses']['VDU1']['spec']['replicas'])

    @mock.patch.object(nfvo_client.NfvoClient, 'get_vnfd')
    @mock.patch.object(client.CoreV1Api, 'list_namespaced_pod')
    def test_sync_db_no_diff(
            self, mock_list_namespaced_pod, mock_get_vnfd):
        vnf_instance_obj = fakes.fake_vnf_instance()

        vnfc_rsc_info_obj1, vnfc_info_obj1 = fakes.fake_vnfc_resource_info(
            vdu_id='VDU1', rsc_kind='Deployment',
            pod_name="vdu1-1234567890-abcd1", rsc_name="vdu1")

        vnf_instance_obj.instantiatedVnfInfo.vnfcResourceInfo = [
            vnfc_rsc_info_obj1
        ]
        vim_connection_object = fakes.fake_vim_connection_info()
        vnf_instance_obj.vimConnectionInfo['vim1'] = vim_connection_object

        mock_list_namespaced_pod.return_value = client.V1PodList(
            items=[
                fakes.get_fake_pod_info(
                    kind='Deployment', pod_name="vdu1-1234567890-abcd1")])
        mock_get_vnfd.return_value = self.vnfd_1
        vnf_instance_obj.vnfdId = uuidutils.generate_uuid()
        vnf_instance_obj.instantiatedVnfInfo.scaleStatus = [
            fakes.fake_scale_status(vnfd_id=vnf_instance_obj.vnfdId)
        ]

        ex = self.assertRaises(
            sol_ex.DbSyncNoDiff, self.driver.sync_db,
            self.context, vnf_instance_obj, vim_connection_object)
        self.assertEqual(
            "There are no differences in Vnfc resources.", ex.args[0])

    @mock.patch.object(vnfd_utils.Vnfd, 'get_scale_vdu_and_num')
    @mock.patch.object(nfvo_client.NfvoClient, 'get_vnfd')
    @mock.patch.object(client.CoreV1Api, 'list_namespaced_pod')
    def test_sync_db_scale_level(
            self, mock_list_namespaced_pod, mock_get_vnfd,
            mock_scale_vdu_and_num):
        vnf_instance_obj = fakes.fake_vnf_instance()

        vnfc_rsc_info_obj1, vnfc_info_obj1 = fakes.fake_vnfc_resource_info(
            vdu_id='VDU1', rsc_kind='Deployment',
            pod_name="vdu1-1234567890-abcd1", rsc_name="vdu1")

        vnf_instance_obj.instantiatedVnfInfo.vnfcResourceInfo = [
            vnfc_rsc_info_obj1
        ]
        vim_connection_object = fakes.fake_vim_connection_info()
        vnf_instance_obj.vimConnectionInfo['vim1'] = vim_connection_object

        mock_list_namespaced_pod.return_value = client.V1PodList(
            items=[
                fakes.get_fake_pod_info(
                    kind='Deployment', pod_name="vdu1-1234567890-abcd1"),
                fakes.get_fake_pod_info(
                    kind='Deployment', pod_name="vdu1-1234567890-abcd2"),
                fakes.get_fake_pod_info(
                    kind='Deployment', pod_name="vdu1-1234567890-abcd3"),
                fakes.get_fake_pod_info(
                    kind='Deployment', pod_name="vdu1-1234567890-abcd4")
            ])
        mock_get_vnfd.return_value = self.vnfd_1
        vnf_instance_obj.vnfdId = uuidutils.generate_uuid()
        vnf_instance_obj.instantiatedVnfInfo.scaleStatus = [
            fakes.fake_scale_status(vnfd_id=vnf_instance_obj.vnfdId)
        ]
        delta = 2
        mock_scale_vdu_and_num.return_value = {'VDU1': delta}
        current_pod_num = 4
        vdu_id = "VDU1"

        ex = self.assertRaises(
            sol_ex.DbSyncFailed, self.driver.sync_db,
            self.context, vnf_instance_obj, vim_connection_object)
        self.assertEqual(
            "Error computing 'scale_level'. current Pod num: "
            f"{current_pod_num} delta: {delta}. vnf: {vnf_instance_obj.id} "
            f"vdu: {vdu_id}", ex.args[0])

    @mock.patch.object(vnfd_utils.Vnfd, 'get_scale_vdu_and_num')
    @mock.patch.object(nfvo_client.NfvoClient, 'get_vnfd')
    @mock.patch.object(client.CoreV1Api, 'list_namespaced_pod')
    def test_sync_db_pod_range(
            self, mock_list_namespaced_pod, mock_get_vnfd,
            mock_scale_vdu_and_num):
        vnf_instance_obj = fakes.fake_vnf_instance()

        vnfc_rsc_info_obj1, vnfc_info_obj1 = fakes.fake_vnfc_resource_info(
            vdu_id='VDU1', rsc_kind='Deployment',
            pod_name="vdu1-1234567890-abcd1", rsc_name="vdu1")

        vnf_instance_obj.instantiatedVnfInfo.vnfcResourceInfo = [
            vnfc_rsc_info_obj1
        ]
        vim_connection_object = fakes.fake_vim_connection_info()
        vnf_instance_obj.vimConnectionInfo['vim1'] = vim_connection_object

        mock_list_namespaced_pod.return_value = client.V1PodList(
            items=[
                fakes.get_fake_pod_info(
                    kind='Deployment', pod_name="vdu1-1234567890-abcd1"),
                fakes.get_fake_pod_info(
                    kind='Deployment', pod_name="vdu1-1234567890-abcd2"),
                fakes.get_fake_pod_info(
                    kind='Deployment', pod_name="vdu1-1234567890-abcd3"),
                fakes.get_fake_pod_info(
                    kind='Deployment', pod_name="vdu1-1234567890-abcd4"),
                fakes.get_fake_pod_info(
                    kind='Deployment', pod_name="vdu1-1234567890-abcd5")
            ])
        mock_get_vnfd.return_value = self.vnfd_1
        vnf_instance_obj.vnfdId = uuidutils.generate_uuid()
        vnf_instance_obj.instantiatedVnfInfo.scaleStatus = [
            fakes.fake_scale_status(vnfd_id=vnf_instance_obj.vnfdId)
        ]
        delta = 2
        mock_scale_vdu_and_num.return_value = {'VDU1': delta}
        current_pod_num = 5
        vdu_id = "VDU1"

        ex = self.assertRaises(
            sol_ex.DbSyncFailed, self.driver.sync_db,
            self.context, vnf_instance_obj, vim_connection_object)
        self.assertEqual(
            f"Failed to update database vnf {vnf_instance_obj.id} "
            f"vdu: {vdu_id}. Pod num is out of range. "
            f"pod_num: {current_pod_num}", ex.args[0])
