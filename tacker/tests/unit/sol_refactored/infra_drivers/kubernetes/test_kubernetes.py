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

from datetime import datetime
import os
import requests
import subprocess

from kubernetes import client
from oslo_utils import uuidutils
from unittest import mock

from tacker import context
from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.common import vnfd_utils
from tacker.sol_refactored.infra_drivers.kubernetes import kubernetes
from tacker.sol_refactored import objects
from tacker.sol_refactored.objects.v2 import fields
from tacker.tests import base
from tacker.tests.unit.sol_refactored.infra_drivers.kubernetes import fakes

CNF_SAMPLE_VNFD_ID = "b1bb0ce7-ebca-4fa7-95ed-4840d70a1177"
NEW_CNF_SAMPLE_VNFD_ID = "ff60b74a-df4d-5c78-f5bf-19e129da8fff"


# InstantiateVnfRequest example for instantiate
_instantiate_req_example = {
    "flavourId": "simple",
    "additionalParams": {
        "lcm-kubernetes-def-files": [
            "Files/kubernetes/deployment.yaml"
        ]
    },
    "vimConnectionInfo": {
        "vim1": {
            "vimType": "kubernetes",
            "vimId": uuidutils.generate_uuid(),
            "interfaceInfo": {
                "endpoint": "https://127.0.0.1:6443"},
            "accessInfo": {
                "bearer_token": "secret_token",
                "username": "test",
                "password": "test",
                "region": "RegionOne"
            }
        }
    }
}
_change_vnfpkg_example = {
    "vnfdId": NEW_CNF_SAMPLE_VNFD_ID,
    "additionalParams": {
        "upgrade_type": "RollingUpdate",
        "lcm-operation-coordinate-old-vnf": "Scripts/coordinate_old_vnf.py",
        "lcm-operation-coordinate-old-vnf-class": "CoordinateOldVnf",
        "lcm-operation-coordinate-new-vnf": "Scripts/coordinate_new_vnf.py",
        "lcm-operation-coordinate-new-vnf-class": "CoordinateNewVnf",
        "lcm-kubernetes-def-files": [
            "Files/new_kubernetes/new_deployment.yaml"
        ],
        "vdu_params": [{
            "vdu_id": "VDU1"
        }]
    }
}
_update_resources = {
    "affectedVnfcs": [{
        "metadata": {
            "Deployment": {
                "name": "vdu1"
            }
        },
        "changeType": "ADDED"
    }]
}


class TestKubernetes(base.BaseTestCase):

    def setUp(self):
        super(TestKubernetes, self).setUp()
        objects.register_all()
        self.driver = kubernetes.Kubernetes()
        self.context = context.get_admin_context()

        cur_dir = os.path.dirname(__file__)
        sample_dir = os.path.join(cur_dir, "../..", "samples")

        self.vnfd_1 = vnfd_utils.Vnfd(CNF_SAMPLE_VNFD_ID)
        self.vnfd_1.init_from_csar_dir(os.path.join(sample_dir, "sample2"))

        self.vnfd_2 = vnfd_utils.Vnfd(NEW_CNF_SAMPLE_VNFD_ID)
        self.vnfd_2.init_from_csar_dir(os.path.join(
            sample_dir, "change_vnfpkg_sample"))

        self.vnfd_3 = vnfd_utils.Vnfd(CNF_SAMPLE_VNFD_ID)
        self.vnfd_3.init_from_csar_dir(os.path.join(sample_dir, "sample1"))

    def _normal_execute_procedure(self, req):
        # prepare instantiate
        inst = objects.VnfInstanceV2(
            vimConnectionInfo=req.vimConnectionInfo
        )
        grant_req = objects.GrantRequestV1(
            operation=fields.LcmOperationType.INSTANTIATE
        )
        grant = objects.GrantV1()
        # execute instantiate
        self.driver.instantiate(req, inst, grant_req, grant, self.vnfd_1)

        # prepare terminate
        req_term = objects.TerminateVnfRequest(terminationType='FORCEFUL')
        grant_req_term = objects.GrantRequestV1(
            operation=fields.LcmOperationType.TERMINATE
        )

        # execute terminate
        self.driver.terminate(
            req_term, inst, grant_req_term, grant, self.vnfd_1)

    @mock.patch.object(client.CoreV1Api, 'list_namespaced_pod')
    @mock.patch.object(client.AppsV1Api, 'delete_namespaced_deployment')
    @mock.patch.object(client.CoreV1Api, 'delete_namespace')
    @mock.patch.object(client.AppsV1Api, 'read_namespaced_deployment')
    @mock.patch.object(client.CoreV1Api, 'read_namespace')
    @mock.patch.object(client.AppsV1Api, 'create_namespaced_deployment')
    @mock.patch.object(client.CoreV1Api, 'create_namespace')
    def test_inst_and_term_deployment_with_namespace(
            self, mock_namespace, mock_deployment,
            mock_read_namespace, mock_read_deployment,
            mock_delete_namespace, mock_delete_deployment,
            mock_pods):
        # prepare instantiate
        req = objects.InstantiateVnfRequest.from_dict(
            _instantiate_req_example)
        req.additionalParams['lcm-kubernetes-def-files'].append(
            'Files/kubernetes/namespace.yaml')
        req.vimConnectionInfo['vim1']['interfaceInfo']['ssl_ca_cert '] = 'test'
        req.additionalParams['namespace'] = 'curry'
        inst = objects.VnfInstanceV2(
            vimConnectionInfo=req.vimConnectionInfo
        )
        grant_req = objects.GrantRequestV1(
            operation=fields.LcmOperationType.INSTANTIATE
        )
        grant = objects.GrantV1()
        mock_namespace.return_value = fakes.fake_namespace()
        mock_read_namespace.side_effect = [fakes.fake_namespace(),
                                           fakes.fake_none()]
        mock_read_deployment.side_effect = [
            fakes.fake_deployment(ready_replicas=2), fakes.fake_none()]
        mock_pods.return_value = fakes.fake_pods()

        # execute instantiate
        self.driver.instantiate(req, inst, grant_req, grant, self.vnfd_1)

        # check
        for vnfc_res in inst.instantiatedVnfInfo.vnfcResourceInfo:
            if vnfc_res.vduId == "VDU1":
                self.assertEqual(
                    vnfc_res.metadata['Deployment']['namespace'], 'curry')
                self.assertEqual(
                    vnfc_res.metadata['Deployment']['name'], 'vdu1')

        # prepare terminate
        req_term = objects.TerminateVnfRequest(terminationType='FORCEFUL')
        grant_req_term = objects.GrantRequestV1(
            operation=fields.LcmOperationType.TERMINATE
        )

        # execute terminate
        self.driver.terminate(
            req_term, inst, grant_req_term, grant, self.vnfd_1)

    @mock.patch.object(client.CoreV1Api, 'list_namespaced_pod')
    @mock.patch.object(client.AppsV1Api, 'delete_namespaced_deployment')
    @mock.patch.object(client.AppsV1Api, 'read_namespaced_deployment')
    @mock.patch.object(client.AppsV1Api, 'create_namespaced_deployment')
    def test_inst_and_term_deployment_no_namespace(
            self, mock_deployment, mock_read_deployment,
            mock_delete_deployment, mock_pods):
        # prepare
        req = objects.InstantiateVnfRequest.from_dict(
            _instantiate_req_example)

        inst = objects.VnfInstanceV2(
            vimConnectionInfo=req.vimConnectionInfo
        )
        grant_req = objects.GrantRequestV1(
            operation=fields.LcmOperationType.INSTANTIATE
        )
        grant = objects.GrantV1()
        mock_deployment.return_value = fakes.fake_deployment()
        mock_read_deployment.side_effect = [
            fakes.fake_deployment(ready_replicas=2), fakes.fake_none()]
        mock_pods.return_value = fakes.fake_pods()

        # execute instantiate
        self.driver.instantiate(req, inst, grant_req, grant, self.vnfd_1)

        # check
        for vnfc_res in inst.instantiatedVnfInfo.vnfcResourceInfo:
            if vnfc_res.vduId == "VDU1":
                self.assertEqual(
                    vnfc_res.metadata['Deployment']['namespace'], 'default')
                self.assertEqual(
                    vnfc_res.metadata['Deployment']['name'], 'vdu1')

        # prepare terminate
        req_term = objects.TerminateVnfRequest(terminationType='GRACEFUL',
                                               gracefulTerminationTimeout=20)
        grant_req_term = objects.GrantRequestV1(
            operation=fields.LcmOperationType.TERMINATE
        )

        # execute terminate
        self.driver.terminate(
            req_term, inst, grant_req_term, grant, self.vnfd_1)

    @mock.patch.object(client.CoreV1Api, 'list_namespaced_pod')
    @mock.patch.object(client.CoreV1Api, 'create_namespaced_binding')
    def test_inst_and_term_bindings(
            self, mock_binding, mock_pods):
        # prepare
        req = objects.InstantiateVnfRequest.from_dict(
            _instantiate_req_example)
        req.additionalParams['lcm-kubernetes-def-files'] = [
            'Files/kubernetes/bindings.yaml']

        self._normal_execute_procedure(req)

    @mock.patch.object(client.CoreV1Api, 'list_namespaced_pod')
    @mock.patch.object(client.CoreV1Api, 'delete_namespaced_service_account')
    @mock.patch.object(client.RbacAuthorizationV1Api, 'delete_cluster_role')
    @mock.patch.object(client.RbacAuthorizationV1Api,
                       'delete_cluster_role_binding')
    @mock.patch.object(client.CoreV1Api, 'read_namespaced_service_account')
    @mock.patch.object(client.RbacAuthorizationV1Api, 'read_cluster_role')
    @mock.patch.object(client.RbacAuthorizationV1Api,
                       'read_cluster_role_binding')
    @mock.patch.object(client.CoreV1Api, 'create_namespaced_service_account')
    @mock.patch.object(client.RbacAuthorizationV1Api, 'create_cluster_role')
    @mock.patch.object(client.RbacAuthorizationV1Api,
                       'create_cluster_role_binding')
    def test_inst_and_term_cluster_role_binding_and_sa(
            self, mock_cluster_rb, mock_cluster_role, mock_sa,
            mock_read_cluster_rb, mock_read_cluster_role, mock_read_sa,
            mock_del_cluster_rb, mock_del_cluster_role, mock_del_sa,
            mock_pods):
        # prepare
        req = objects.InstantiateVnfRequest.from_dict(
            _instantiate_req_example)
        req.additionalParams['lcm-kubernetes-def-files'] = [
            'Files/kubernetes/clusterrole_clusterrolebinding_SA.yaml']

        mock_read_sa.side_effect = [fakes.fake_sa(), fakes.fake_none()]
        mock_read_cluster_rb.side_effect = [
            fakes.fake_cluster_role_binding(), fakes.fake_none()]
        mock_read_cluster_role.side_effect = [
            fakes.fake_cluster_role(), fakes.fake_none()]

        self._normal_execute_procedure(req)

    @mock.patch.object(client.CoreV1Api, 'list_namespaced_pod')
    @mock.patch.object(client.CoreV1Api, 'delete_namespaced_config_map')
    @mock.patch.object(client.CoreV1Api, 'read_namespaced_config_map')
    @mock.patch.object(client.CoreV1Api, 'create_namespaced_config_map')
    def test_inst_and_term_configmap(
            self, mock_config_map, mock_read_config_map, mock_del_config_map,
            mock_pods):
        # prepare
        req = objects.InstantiateVnfRequest.from_dict(
            _instantiate_req_example)
        req.additionalParams['lcm-kubernetes-def-files'] = [
            'Files/kubernetes/config-map.yaml']
        mock_read_config_map.side_effect = [
            fakes.fake_config_map(), fakes.fake_none()]

        self._normal_execute_procedure(req)

    @mock.patch.object(client.CoreV1Api, 'list_namespaced_pod')
    @mock.patch.object(
        client.AppsV1Api, 'delete_namespaced_controller_revision')
    @mock.patch.object(client.AppsV1Api,
                       'read_namespaced_controller_revision')
    @mock.patch.object(
        client.AppsV1Api, 'create_namespaced_controller_revision')
    def test_inst_and_term_controller_revision(
            self, mock_cr, mock_read_cr, mock_del_cr, mock_pods):
        # prepare
        req = objects.InstantiateVnfRequest.from_dict(
            _instantiate_req_example)
        req.additionalParams['lcm-kubernetes-def-files'] = [
            'Files/kubernetes/controller-revision.yaml']
        mock_read_cr.side_effect = [
            fakes.fake_cr(), fakes.fake_none()]

        self._normal_execute_procedure(req)

    @mock.patch.object(client.CoreV1Api, 'list_namespaced_pod')
    @mock.patch.object(client.AppsV1Api, 'delete_namespaced_daemon_set')
    @mock.patch.object(client.AppsV1Api, 'read_namespaced_daemon_set')
    @mock.patch.object(client.AppsV1Api, 'create_namespaced_daemon_set')
    def test_inst_and_term_daemon_set(self, mock_ds, mock_read_ds, mock_del_ds,
                                      mock_pods):
        # prepare
        req = objects.InstantiateVnfRequest.from_dict(
            _instantiate_req_example)
        req.additionalParams['lcm-kubernetes-def-files'] = [
            'Files/kubernetes/daemon-set.yaml']

        inst = objects.VnfInstanceV2(
            vimConnectionInfo=req.vimConnectionInfo
        )
        grant_req = objects.GrantRequestV1(
            operation=fields.LcmOperationType.INSTANTIATE
        )
        grant = objects.GrantV1()
        mock_ds.return_value = fakes.fake_daemon_set()
        mock_read_ds.side_effect = [
            fakes.fake_daemon_set(number_ready=1), fakes.fake_none()]
        mock_pods.return_value = fakes.fake_pod_vdu2()

        # execute instantiate
        self.driver.instantiate(req, inst, grant_req, grant, self.vnfd_1)

        # check
        for vnfc_res in inst.instantiatedVnfInfo.vnfcResourceInfo:
            if vnfc_res.vduId == "VDU2":
                self.assertEqual(
                    vnfc_res.metadata['DaemonSet']['namespace'], 'default')
                self.assertEqual(
                    vnfc_res.metadata['DaemonSet']['name'], 'vdu2')

        # prepare terminate
        req_term = objects.TerminateVnfRequest(terminationType='FORCEFUL')
        grant_req_term = objects.GrantRequestV1(
            operation=fields.LcmOperationType.TERMINATE
        )

        # execute terminate
        self.driver.terminate(
            req_term, inst, grant_req_term, grant, self.vnfd_1)

    @mock.patch.object(client.CoreV1Api, 'list_namespaced_pod')
    @mock.patch.object(
        client.AutoscalingV1Api, 'delete_namespaced_horizontal_pod_autoscaler')
    @mock.patch.object(
        client.AutoscalingV1Api, 'read_namespaced_horizontal_pod_autoscaler')
    @mock.patch.object(
        client.AutoscalingV1Api, 'create_namespaced_horizontal_pod_autoscaler')
    def test_inst_and_term_hpa(
            self, mock_hpa, mock_read_hpa, mock_del_hap, mock_pods):
        # prepare
        req = objects.InstantiateVnfRequest.from_dict(
            _instantiate_req_example)
        req.additionalParams['lcm-kubernetes-def-files'] = [
            'Files/kubernetes/horizontal-pod-autoscaler.yaml']
        mock_read_hpa.side_effect = [
            fakes.fake_hpa(), fakes.fake_none()]

        self._normal_execute_procedure(req)

    @mock.patch.object(client.CoreV1Api, 'list_namespaced_pod')
    @mock.patch.object(client.BatchV1Api, 'delete_namespaced_job')
    @mock.patch.object(client.BatchV1Api, 'read_namespaced_job')
    @mock.patch.object(client.BatchV1Api, 'create_namespaced_job')
    def test_inst_and_term_job(self, mock_job, mock_read_job, mock_del_job,
                               mock_pods):
        # prepare
        req = objects.InstantiateVnfRequest.from_dict(
            _instantiate_req_example)
        req.additionalParams['lcm-kubernetes-def-files'] = [
            'Files/kubernetes/job.yaml']
        mock_job.return_value = fakes.fake_job()
        mock_read_job.side_effect = [
            fakes.fake_job(succeeded=5), fakes.fake_none()]

        self._normal_execute_procedure(req)

    @mock.patch.object(client.CoreV1Api, 'list_namespaced_pod')
    @mock.patch.object(client.CoreV1Api, 'delete_namespaced_limit_range')
    @mock.patch.object(client.CoreV1Api, 'read_namespaced_limit_range')
    @mock.patch.object(client.CoreV1Api, 'create_namespaced_limit_range')
    def test_inst_and_term_limit_range(
            self, mock_lr, mock_read_lr, mock_del_lr, mock_pods):
        # prepare
        req = objects.InstantiateVnfRequest.from_dict(
            _instantiate_req_example)
        req.additionalParams['lcm-kubernetes-def-files'] = [
            'Files/kubernetes/limit-range.yaml']
        mock_read_lr.side_effect = [
            fakes.fake_lr(), fakes.fake_none()]

        self._normal_execute_procedure(req)

    @mock.patch.object(client.CoreV1Api, 'list_namespaced_pod')
    @mock.patch.object(
        client.AuthorizationV1Api,
        'create_namespaced_local_subject_access_review')
    def test_inst_and_term_local_subject_access_review(
            self, mock_lsar, mock_pods):
        # prepare
        req = objects.InstantiateVnfRequest.from_dict(
            _instantiate_req_example)
        req.additionalParams['lcm-kubernetes-def-files'] = [
            'Files/kubernetes/local-subject-access-review.yaml']

        self._normal_execute_procedure(req)

    @mock.patch.object(client.CoreV1Api, 'list_namespaced_pod')
    @mock.patch.object(client.SchedulingV1Api, 'delete_priority_class')
    @mock.patch.object(client.NetworkingV1Api,
                       'delete_namespaced_network_policy')
    @mock.patch.object(client.CoordinationV1Api, 'delete_namespaced_lease')
    @mock.patch.object(client.SchedulingV1Api, 'read_priority_class')
    @mock.patch.object(client.NetworkingV1Api,
                       'read_namespaced_network_policy')
    @mock.patch.object(client.CoordinationV1Api, 'read_namespaced_lease')
    @mock.patch.object(client.SchedulingV1Api, 'create_priority_class')
    @mock.patch.object(client.NetworkingV1Api,
                       'create_namespaced_network_policy')
    @mock.patch.object(client.CoordinationV1Api, 'create_namespaced_lease')
    def test_inst_and_term_multiple_lease(
            self, mock_lease, mock_np, mock_pc,
            mock_read_lease, mock_read_np, mock_read_pc,
            mock_del_lease, mock_del_np, mock_del_pc,
            mock_pods):
        # prepare
        req = objects.InstantiateVnfRequest.from_dict(
            _instantiate_req_example)
        req.additionalParams['lcm-kubernetes-def-files'] = [
            'Files/kubernetes/multiple_yaml_lease.yaml',
            'Files/kubernetes/multiple_yaml_network-policy.yaml',
            'Files/kubernetes/multiple_yaml_priority-class.yaml']
        mock_read_lease.side_effect = [
            fakes.fake_lease(), fakes.fake_none()]
        mock_read_np.side_effect = [
            fakes.fake_np(), fakes.fake_none()]
        mock_read_pc.side_effect = [
            fakes.fake_pc(), fakes.fake_none()]

        self._normal_execute_procedure(req)

    @mock.patch.object(client.CoreV1Api, 'list_namespaced_pod')
    @mock.patch.object(client.CoreV1Api, 'delete_persistent_volume')
    @mock.patch.object(client.CoreV1Api, 'read_persistent_volume')
    @mock.patch.object(client.CoreV1Api, 'create_persistent_volume')
    def test_inst_and_term_multiple_pv(
            self, mock_pv, mock_read_pv, mock_del_pv, mock_pods):
        # prepare
        req = objects.InstantiateVnfRequest.from_dict(
            _instantiate_req_example)
        req.additionalParams['lcm-kubernetes-def-files'] = [
            'Files/kubernetes/persistent-volume-0.yaml',
            'Files/kubernetes/persistent-volume-1.yaml']
        mock_pv.side_effect = [
            fakes.fake_persistent_volume(),
            fakes.fake_persistent_volume(name='curry-sc-pv-0')]
        fake_read_pv_1 = fakes.fake_persistent_volume(phase='Available')
        fake_read_pv_2 = fakes.fake_persistent_volume(phase='Bound')
        mock_read_pv.side_effect = [
            fake_read_pv_1, fake_read_pv_2,
            fakes.fake_none(), fakes.fake_none()]

        self._normal_execute_procedure(req)

    @mock.patch.object(client.CoreV1Api, 'list_namespaced_pod')
    @mock.patch.object(client.CoreV1Api, 'delete_namespaced_pod')
    @mock.patch.object(client.CoreV1Api, 'read_namespaced_pod')
    @mock.patch.object(client.CoreV1Api, 'create_namespaced_pod')
    def test_inst_and_term_pod(self, mock_pod, mock_read_pod,
                               mock_del_pod, mock_pods):
        # prepare
        req = objects.InstantiateVnfRequest.from_dict(
            _instantiate_req_example)
        req.additionalParams['lcm-kubernetes-def-files'] = [
            'Files/kubernetes/pod.yaml']

        inst = objects.VnfInstanceV2(
            vimConnectionInfo=req.vimConnectionInfo
        )
        grant_req = objects.GrantRequestV1(
            operation=fields.LcmOperationType.INSTANTIATE
        )
        grant = objects.GrantV1()
        mock_pod.return_value = fakes.fake_pod()
        mock_read_pod.side_effect = [
            fakes.fake_pod(phase='Running'), fakes.fake_none()]
        mock_pods.return_value = fakes.fake_pods(name2='vdu2')

        # execute instantiate
        self.driver.instantiate(req, inst, grant_req, grant, self.vnfd_1)

        # check
        for vnfc_res in inst.instantiatedVnfInfo.vnfcResourceInfo:
            if vnfc_res.vduId == "VDU2":
                self.assertEqual(
                    vnfc_res.metadata['Pod']['namespace'], 'default')
                self.assertEqual(
                    vnfc_res.metadata['Pod']['name'], 'vdu2')

        # prepare terminate
        req_term = objects.TerminateVnfRequest(terminationType='FORCEFUL')
        grant_req_term = objects.GrantRequestV1(
            operation=fields.LcmOperationType.TERMINATE
        )

        # execute terminate
        self.driver.terminate(
            req_term, inst, grant_req_term, grant, self.vnfd_1)

    @mock.patch.object(client.CoreV1Api, 'list_namespaced_pod')
    @mock.patch.object(client.CoreV1Api, 'delete_namespaced_pod_template')
    @mock.patch.object(client.CoreV1Api, 'read_namespaced_pod_template')
    @mock.patch.object(client.CoreV1Api, 'create_namespaced_pod_template')
    def test_inst_and_term_pod_template(
            self, mock_pod_template, mock_read_pt, mock_del_pt, mock_pods):
        # prepare
        req = objects.InstantiateVnfRequest.from_dict(
            _instantiate_req_example)
        req.additionalParams['lcm-kubernetes-def-files'] = [
            'Files/kubernetes/pod-template.yaml']
        mock_read_pt.side_effect = [
            fakes.fake_pt(), fakes.fake_none()]

        self._normal_execute_procedure(req)

    @mock.patch.object(client.CoreV1Api, 'list_namespaced_pod')
    @mock.patch.object(client.CoreV1Api, 'delete_namespaced_secret')
    @mock.patch.object(client.CoreV1Api, 'delete_namespaced_service')
    @mock.patch.object(client.AppsV1Api, 'delete_namespaced_replica_set')
    @mock.patch.object(client.CoreV1Api, 'read_namespaced_endpoints')
    @mock.patch.object(client.CoreV1Api, 'read_namespaced_secret')
    @mock.patch.object(client.CoreV1Api, 'read_namespaced_service')
    @mock.patch.object(client.AppsV1Api, 'read_namespaced_replica_set')
    @mock.patch.object(client.CoreV1Api, 'create_namespaced_secret')
    @mock.patch.object(client.CoreV1Api, 'create_namespaced_service')
    @mock.patch.object(client.AppsV1Api, 'create_namespaced_replica_set')
    def test_inst_and_term_replicaset_service_secret(
            self, mock_rs, mock_srv, mock_sec,
            mock_read_rs, mock_read_srv, mock_read_sec, mock_endpoints,
            mock_del_rs, mock_del_srv, mock_del_sec, mock_pods):
        # prepare
        req = objects.InstantiateVnfRequest.from_dict(
            _instantiate_req_example)
        req.additionalParams['lcm-kubernetes-def-files'] = [
            'Files/kubernetes/replicaset_service_secret.yaml']

        inst = objects.VnfInstanceV2(
            vimConnectionInfo=req.vimConnectionInfo
        )
        grant_req = objects.GrantRequestV1(
            operation=fields.LcmOperationType.INSTANTIATE
        )
        grant = objects.GrantV1()

        mock_rs.return_value = fakes.fake_rs()
        mock_srv.return_value = fakes.fake_service()
        mock_read_rs.side_effect = [
            fakes.fake_rs(ready_replicas=2), fakes.fake_none()]
        mock_read_srv.side_effect = [fakes.fake_service(), fakes.fake_none()]
        mock_read_sec.side_effect = [fakes.fake_sec(), fakes.fake_none()]
        mock_pods.return_value = fakes.fake_pods(
            name1='vdu1-fs6vb', name2='vdu1-v8sl2')

        # execute instantiate
        self.driver.instantiate(req, inst, grant_req, grant, self.vnfd_1)

        # check
        for vnfc_res in inst.instantiatedVnfInfo.vnfcResourceInfo:
            if vnfc_res.vduId == "VDU2":
                self.assertEqual(
                    vnfc_res.metadata['ReplicaSet']['namespace'], 'default')
                self.assertEqual(
                    vnfc_res.metadata['ReplicaSet']['name'], 'vdu1')

        # prepare terminate
        req_term = objects.TerminateVnfRequest(terminationType='FORCEFUL')
        grant_req_term = objects.GrantRequestV1(
            operation=fields.LcmOperationType.TERMINATE
        )

        # execute terminate
        self.driver.terminate(
            req_term, inst, grant_req_term, grant, self.vnfd_1)

    @mock.patch.object(client.CoreV1Api, 'list_namespaced_pod')
    @mock.patch.object(client.CoreV1Api, 'delete_namespaced_resource_quota')
    @mock.patch.object(client.CoreV1Api, 'read_namespaced_resource_quota')
    @mock.patch.object(client.CoreV1Api, 'create_namespaced_resource_quota')
    def test_inst_and_term_resource_quota(self, mock_rq, mock_read_rq,
                                          mock_del_rq, mock_pods):
        # prepare
        req = objects.InstantiateVnfRequest.from_dict(
            _instantiate_req_example)
        req.additionalParams['lcm-kubernetes-def-files'] = [
            'Files/kubernetes/resource-quota.yaml']
        mock_read_rq.side_effect = [
            fakes.fake_rq(), fakes.fake_none()]

        self._normal_execute_procedure(req)

    @mock.patch.object(client.CoreV1Api, 'list_namespaced_pod')
    @mock.patch.object(client.CoreV1Api, 'delete_namespaced_service_account')
    @mock.patch.object(client.RbacAuthorizationV1Api, 'delete_namespaced_role')
    @mock.patch.object(client.RbacAuthorizationV1Api,
                       'delete_namespaced_role_binding')
    @mock.patch.object(client.CoreV1Api, 'read_namespaced_service_account')
    @mock.patch.object(client.RbacAuthorizationV1Api, 'read_namespaced_role')
    @mock.patch.object(client.RbacAuthorizationV1Api,
                       'read_namespaced_role_binding')
    @mock.patch.object(client.CoreV1Api, 'create_namespaced_service_account')
    @mock.patch.object(client.RbacAuthorizationV1Api, 'create_namespaced_role')
    @mock.patch.object(client.RbacAuthorizationV1Api,
                       'create_namespaced_role_binding')
    def test_inst_and_term_role_rolebinding_sa(
            self, mock_rb, mock_role, mock_sa,
            mock_read_rb, mock_read_role, mock_read_sa,
            mock_del_rb, mock_del_role, mock_del_sa,
            mock_pods):
        # prepare
        req = objects.InstantiateVnfRequest.from_dict(
            _instantiate_req_example)
        req.additionalParams['lcm-kubernetes-def-files'] = [
            'Files/kubernetes/role_rolebinding_SA.yaml']

        mock_read_sa.side_effect = [fakes.fake_sa(), fakes.fake_none()]
        mock_read_rb.side_effect = [
            fakes.fake_role_binding(), fakes.fake_none()]
        mock_read_role.side_effect = [
            fakes.fake_role(), fakes.fake_none()]

        self._normal_execute_procedure(req)

    @mock.patch.object(client.CoreV1Api, 'list_namespaced_pod')
    @mock.patch.object(client.AuthorizationV1Api,
                       'create_self_subject_rules_review')
    @mock.patch.object(client.AuthorizationV1Api,
                       'create_self_subject_access_review')
    def test_inst_and_term_self_sar_and_self_srr(
            self, mock_self_sar, mock_self_srr, mock_pods):
        # prepare
        req = objects.InstantiateVnfRequest.from_dict(
            _instantiate_req_example)
        req.additionalParams['lcm-kubernetes-def-files'] = [
            'Files/kubernetes/self-subject-access-review_and'
            '_self-subject-rule-review.yaml']

        self._normal_execute_procedure(req)

    @mock.patch.object(client.CoreV1Api, 'list_namespaced_pod')
    @mock.patch.object(client.CoreV1Api,
                       'delete_namespaced_persistent_volume_claim')
    @mock.patch.object(client.AppsV1Api, 'delete_namespaced_stateful_set')
    @mock.patch.object(client.CoreV1Api,
                       'list_namespaced_persistent_volume_claim')
    @mock.patch.object(client.CoreV1Api,
                       'read_namespaced_persistent_volume_claim')
    @mock.patch.object(client.AppsV1Api, 'read_namespaced_stateful_set')
    @mock.patch.object(client.AppsV1Api, 'create_namespaced_stateful_set')
    def test_inst_and_term_statefulset(
            self, mock_ss, mock_read_ss,
            mock_read_pvc, mock_list_pvc,
            mock_del_ss, mock_del_pvc, mock_pods):
        # prepare
        req = objects.InstantiateVnfRequest.from_dict(
            _instantiate_req_example)
        req.additionalParams['lcm-kubernetes-def-files'] = [
            'Files/kubernetes/statefulset.yaml']

        inst = objects.VnfInstanceV2(
            vimConnectionInfo=req.vimConnectionInfo
        )
        grant_req = objects.GrantRequestV1(
            operation=fields.LcmOperationType.INSTANTIATE
        )
        grant = objects.GrantV1()
        mock_ss.return_value = fakes.fake_stateful_set()
        fake_read_ss_1 = fakes.fake_stateful_set(ready_replicas=2)
        mock_read_pvc.side_effect = [fakes.fake_pvc('www-vdu1-0'),
                                     fakes.fake_pvc('www-vdu1-1')]
        mock_read_ss.side_effect = [fake_read_ss_1, fake_read_ss_1,
                                    fakes.fake_none()]
        mock_list_pvc.return_value = fakes.fake_pvcs()
        fake_pods = fakes.fake_pods(name1='vdu1-0', name2='vdu1-1')
        mock_pods.return_value = fake_pods

        # execute instantiate
        self.driver.instantiate(req, inst, grant_req, grant, self.vnfd_1)

        # check
        for vnfc_res in inst.instantiatedVnfInfo.vnfcResourceInfo:
            if vnfc_res.vduId == "VDU2":
                self.assertEqual(
                    vnfc_res.metadata['DaemonSet']['namespace'], 'default')
                self.assertEqual(
                    vnfc_res.metadata['DaemonSet']['name'], 'vdu2')

        # prepare terminate
        req_term = objects.TerminateVnfRequest(terminationType='FORCEFUL')
        grant_req_term = objects.GrantRequestV1(
            operation=fields.LcmOperationType.TERMINATE
        )

        # execute terminate
        self.driver.terminate(
            req_term, inst, grant_req_term, grant, self.vnfd_1)

    @mock.patch.object(client.CoreV1Api, 'list_namespaced_pod')
    @mock.patch.object(client.StorageV1Api, 'delete_storage_class')
    @mock.patch.object(client.StorageV1Api, 'read_storage_class')
    @mock.patch.object(client.StorageV1Api, 'create_storage_class')
    def test_inst_and_term_storage_class(self, mock_sc, mock_read_sc,
                                         mock_del_sc, mock_pods):
        # prepare
        req = objects.InstantiateVnfRequest.from_dict(
            _instantiate_req_example)
        req.additionalParams['lcm-kubernetes-def-files'] = [
            'Files/kubernetes/storage-class.yaml']
        mock_read_sc.side_effect = [
            fakes.fake_sc(), fakes.fake_none()]

        self._normal_execute_procedure(req)

    @mock.patch.object(client.CoreV1Api, 'list_namespaced_pod')
    @mock.patch.object(client.CoreV1Api,
                       'delete_namespaced_persistent_volume_claim')
    @mock.patch.object(client.CoreV1Api, 'delete_persistent_volume')
    @mock.patch.object(client.StorageV1Api, 'delete_storage_class')
    @mock.patch.object(client.CoreV1Api,
                       'read_namespaced_persistent_volume_claim')
    @mock.patch.object(client.CoreV1Api, 'read_persistent_volume')
    @mock.patch.object(client.StorageV1Api, 'read_storage_class')
    @mock.patch.object(client.CoreV1Api,
                       'create_namespaced_persistent_volume_claim')
    @mock.patch.object(client.CoreV1Api, 'create_persistent_volume')
    @mock.patch.object(client.StorageV1Api, 'create_storage_class')
    def test_inst_and_term_storage_class_pv_pvc(
            self, mock_sc, mock_pv, mock_pvc,
            mock_read_sc, mock_read_pv, mock_read_pvc,
            mock_del_sc, mock_del_pv, mock_del_pvc,
            mock_pods):
        # prepare
        req = objects.InstantiateVnfRequest.from_dict(
            _instantiate_req_example)
        req.additionalParams['lcm-kubernetes-def-files'] = [
            'Files/kubernetes/storage-class_pv_pvc.yaml']

        mock_read_sc.side_effect = [
            fakes.fake_sc(name='my-storage-class'), fakes.fake_none()]
        mock_read_pv.side_effect = [
            fakes.fake_persistent_volume(
                name='curry-sc-pv-1', phase='Bound'),
            fakes.fake_none()]
        mock_read_pvc.side_effect = [
            fakes.fake_pvc(name='curry-sc-pvc'), fakes.fake_none()]

        self._normal_execute_procedure(req)

    @mock.patch.object(client.CoreV1Api, 'list_namespaced_pod')
    @mock.patch.object(client.AuthorizationV1Api,
                       'create_subject_access_review')
    def test_inst_and_term_subject_access_review(self, mcok_sar, mock_pods):
        # prepare
        req = objects.InstantiateVnfRequest.from_dict(
            _instantiate_req_example)
        req.additionalParams['lcm-kubernetes-def-files'] = [
            'Files/kubernetes/subject-access-review.yaml']

        self._normal_execute_procedure(req)

    @mock.patch.object(client.CoreV1Api, 'list_namespaced_pod')
    @mock.patch.object(client.AuthenticationV1Api, 'create_token_review')
    def test_inst_and_term_token_review(self, mock_tr, mock_pods):
        # prepare
        req = objects.InstantiateVnfRequest.from_dict(
            _instantiate_req_example)
        req.additionalParams['lcm-kubernetes-def-files'] = [
            'Files/kubernetes/token-review.yaml']
        self._normal_execute_procedure(req)

    @mock.patch.object(client.CoreV1Api, 'list_namespaced_pod')
    @mock.patch.object(client.ApiregistrationV1Api, 'delete_api_service')
    @mock.patch.object(client.ApiregistrationV1Api, 'read_api_service')
    @mock.patch.object(client.ApiregistrationV1Api, 'create_api_service')
    def test_inst_and_term_api_service(
            self, mock_api_service, mock_read_api_srv,
            mock_del_api_srv, mock_pods):
        # prepare
        req = objects.InstantiateVnfRequest.from_dict(
            _instantiate_req_example)
        req.additionalParams['lcm-kubernetes-def-files'] = [
            'Files/kubernetes/api-service.yaml']
        mock_api_service.return_value = fakes.fake_api_service(type='UnKnown')
        mock_read_api_srv.side_effect = [
            fakes.fake_api_service(type='UnKnown'),
            fakes.fake_api_service(), fakes.fake_none()]

        self._normal_execute_procedure(req)

    @mock.patch.object(client.CoreV1Api, 'list_namespaced_pod')
    @mock.patch.object(client.StorageV1Api,
                       'delete_volume_attachment')
    @mock.patch.object(client.StorageV1Api,
                       'read_volume_attachment')
    @mock.patch.object(client.StorageV1Api,
                       'create_volume_attachment')
    def test_inst_and_term_volume_attachment(
            self, mock_va, mock_read_va, mock_del_va, mock_pods):
        # prepare
        req = objects.InstantiateVnfRequest.from_dict(
            _instantiate_req_example)
        req.additionalParams['lcm-kubernetes-def-files'] = [
            'Files/kubernetes/volume-attachment.yaml']

        mock_va.return_value = fakes.fake_volume_attachment(attached='False')
        mock_read_va.side_effect = [
            fakes.fake_volume_attachment(), fakes.fake_none()]

        self._normal_execute_procedure(req)

    @mock.patch.object(client.CoreV1Api, 'list_namespaced_pod')
    @mock.patch.object(client.CoreV1Api, 'delete_node')
    @mock.patch.object(client.CoreV1Api, 'read_node')
    @mock.patch.object(client.CoreV1Api, 'create_node')
    def test_inst_and_term_node(
            self, mock_node, mock_read_node, mock_del_node, mock_pods):
        # prepare
        req = objects.InstantiateVnfRequest.from_dict(
            _instantiate_req_example)
        req.additionalParams['lcm-kubernetes-def-files'] = [
            'Files/kubernetes/node.yaml']

        mock_node.return_value = fakes.fake_node(status='False')
        mock_read_node.side_effect = [
            fakes.fake_node(type='UnReady'),
            fakes.fake_node(), fakes.fake_none()]

        self._normal_execute_procedure(req)

    def test_inst_deployment_failed(self):
        # prepare
        req = objects.InstantiateVnfRequest.from_dict(
            _instantiate_req_example)

        inst = objects.VnfInstanceV2(
            vimConnectionInfo=req.vimConnectionInfo
        )
        grant_req = objects.GrantRequestV1(
            operation=fields.LcmOperationType.INSTANTIATE
        )
        grant = objects.GrantV1()

        self.assertRaises(
            sol_ex.ExecuteK8SResourceCreateApiFailed,
            self.driver.instantiate, req, inst, grant_req, grant, self.vnfd_1)

    @mock.patch.object(client.CoreV1Api, 'list_namespaced_pod')
    @mock.patch.object(client.AppsV1Api, 'delete_namespaced_stateful_set')
    @mock.patch.object(client.CoreV1Api,
                       'list_namespaced_persistent_volume_claim')
    @mock.patch.object(client.CoreV1Api,
                       'read_namespaced_persistent_volume_claim')
    @mock.patch.object(client.AppsV1Api, 'read_namespaced_stateful_set')
    @mock.patch.object(client.AppsV1Api, 'create_namespaced_stateful_set')
    def test_terminate_stateful_set_pvcs_failed(
            self, mock_ss, mock_read_ss,
            mock_read_pvc, mock_list_pvc,
            mock_del_ss, mock_pods):
        # prepare
        req = objects.InstantiateVnfRequest.from_dict(
            _instantiate_req_example)
        req.additionalParams['lcm-kubernetes-def-files'] = [
            'Files/kubernetes/statefulset.yaml']

        inst = objects.VnfInstanceV2(
            vimConnectionInfo=req.vimConnectionInfo
        )
        grant_req = objects.GrantRequestV1(
            operation=fields.LcmOperationType.INSTANTIATE
        )
        grant = objects.GrantV1()
        mock_ss.return_value = fakes.fake_stateful_set()
        fake_read_ss_1 = fakes.fake_stateful_set(ready_replicas=2)
        mock_read_pvc.side_effect = [fakes.fake_pvc('www-vdu1-0'),
                                     fakes.fake_pvc('www-vdu1-1')]
        mock_read_ss.side_effect = [fake_read_ss_1, fake_read_ss_1,
                                    fakes.fake_none()]
        mock_list_pvc.return_value = fakes.fake_pvcs()
        fake_pods = fakes.fake_pods(name1='vdu1-0', name2='vdu1-1')
        mock_pods.return_value = fake_pods

        # execute instantiate
        self.driver.instantiate(req, inst, grant_req, grant, self.vnfd_1)

        # check
        for vnfc_res in inst.instantiatedVnfInfo.vnfcResourceInfo:
            if vnfc_res.vduId == "VDU2":
                self.assertEqual(
                    vnfc_res.metadata['DaemonSet']['namespace'], 'default')
                self.assertEqual(
                    vnfc_res.metadata['DaemonSet']['name'], 'vdu2')

        # prepare terminate
        req_term = objects.TerminateVnfRequest(terminationType='FORCEFUL')
        grant_req_term = objects.GrantRequestV1(
            operation=fields.LcmOperationType.TERMINATE
        )

        # execute terminate
        self.driver.terminate(
            req_term, inst, grant_req_term, grant, self.vnfd_1)

    @mock.patch.object(client.CoreV1Api, 'read_namespaced_secret')
    @mock.patch.object(client.CoreV1Api, 'read_namespaced_service')
    @mock.patch.object(client.AppsV1Api, 'read_namespaced_replica_set')
    @mock.patch.object(client.CoreV1Api, 'create_namespaced_secret')
    @mock.patch.object(client.CoreV1Api, 'create_namespaced_service')
    @mock.patch.object(client.AppsV1Api, 'create_namespaced_replica_set')
    def test_inst_service_failed(
            self, mock_rs, mock_srv, mock_sec,
            mock_read_rs, mock_read_srv, mock_read_sec):
        # prepare
        req = objects.InstantiateVnfRequest.from_dict(
            _instantiate_req_example)
        req.additionalParams['lcm-kubernetes-def-files'] = [
            'Files/kubernetes/replicaset_service_secret.yaml']

        inst = objects.VnfInstanceV2(
            vimConnectionInfo=req.vimConnectionInfo
        )
        grant_req = objects.GrantRequestV1(
            operation=fields.LcmOperationType.INSTANTIATE
        )
        grant = objects.GrantV1()

        mock_rs.return_value = fakes.fake_rs()
        mock_srv.return_value = fakes.fake_service()
        mock_read_rs.side_effect = [
            fakes.fake_rs(ready_replicas=2), fakes.fake_none()]
        mock_read_srv.side_effect = [fakes.fake_service(), fakes.fake_none()]
        mock_read_sec.side_effect = [fakes.fake_sec(), fakes.fake_none()]

        # execute instantiate
        self.assertRaises(
            sol_ex.ReadEndpointsFalse,
            self.driver.instantiate, req, inst, grant_req, grant, self.vnfd_1)

    def test_inst_failed_with_error_artifacts(self):
        # prepare
        req = objects.InstantiateVnfRequest.from_dict(
            _instantiate_req_example)
        req.additionalParams['lcm-kubernetes-def-files'] = [
            'Files/kubernetes/error.yaml']

        inst = objects.VnfInstanceV2(
            vimConnectionInfo=req.vimConnectionInfo
        )
        grant_req = objects.GrantRequestV1(
            operation=fields.LcmOperationType.INSTANTIATE
        )
        grant = objects.GrantV1()

        # execute instantiate
        self.assertRaises(
            sol_ex.CnfDefinitionNotFound,
            self.driver.instantiate, req, inst, grant_req, grant, self.vnfd_1)

    def test_inst_failed_with_no_artifacts(self):
        # prepare
        req = objects.InstantiateVnfRequest.from_dict(
            _instantiate_req_example)
        req.additionalParams['lcm-kubernetes-def-files'] = [
            'Files/kubernetes/error.yaml']

        inst = objects.VnfInstanceV2(
            vimConnectionInfo=req.vimConnectionInfo
        )
        grant_req = objects.GrantRequestV1(
            operation=fields.LcmOperationType.INSTANTIATE
        )
        grant = objects.GrantV1()

        # execute instantiate
        self.assertRaises(
            sol_ex.CnfDefinitionNotFound,
            self.driver.instantiate, req, inst, grant_req, grant, self.vnfd_3)

    @mock.patch.object(subprocess, 'run')
    @mock.patch.object(client.CoreV1Api, 'list_namespaced_pod')
    @mock.patch.object(client.AppsV1Api, 'patch_namespaced_deployment')
    @mock.patch.object(client.AppsV1Api, 'read_namespaced_deployment')
    @mock.patch.object(client.AppsV1Api, 'create_namespaced_deployment')
    def test_change_vnfpkg_with_all_parameters(
            self, mock_deployment, mock_read_deployment,
            mock_patch_deployment, mock_pods, mock_run):
        # prepare instantiate
        req = objects.InstantiateVnfRequest.from_dict(
            _instantiate_req_example)
        inst = objects.VnfInstanceV2(
            vimConnectionInfo=req.vimConnectionInfo
        )
        grant_req = objects.GrantRequestV1(
            operation=fields.LcmOperationType.INSTANTIATE
        )
        grant = objects.GrantV1()

        mock_read_deployment.return_value = fakes.fake_deployment(
            ready_replicas=2)
        mock_pods.return_value = fakes.fake_pods()

        # execute instantiate
        self.driver.instantiate(req, inst, grant_req, grant, self.vnfd_1)

        # check
        for vnfc_res in inst.instantiatedVnfInfo.vnfcResourceInfo:
            if vnfc_res.vduId == "VDU1":
                self.assertEqual(
                    vnfc_res.metadata['Deployment']['namespace'], 'default')
                self.assertEqual(
                    vnfc_res.metadata['Deployment']['name'], 'vdu1')

        # prepare change_vnfpkg
        req_change = objects.ChangeCurrentVnfPkgRequest.from_dict(
            _change_vnfpkg_example)
        grant_req_change = objects.GrantRequestV1(
            operation=fields.LcmOperationType.CHANGE_VNFPKG
        )
        mock_pods.return_value = fakes.fake_pods(
            name1='vdu1-5588797866-fs6va', name2='vdu1-5588797866-v8sl3')
        out = requests.Response()
        out.returncode = 0
        mock_run.return_value = out

        # execute change_vnfpkg
        self.driver.change_vnfpkg(
            req_change, inst, grant_req_change, grant, self.vnfd_2)
        # check
        for vnfc_res in inst.instantiatedVnfInfo.vnfcResourceInfo:
            if vnfc_res.vduId == "VDU1":
                self.assertEqual(
                    vnfc_res.metadata['Deployment']['namespace'], 'default')
                self.assertEqual(
                    vnfc_res.metadata['Deployment']['name'], 'vdu1')
                self.assertIn(
                    vnfc_res.computeResource.resourceId,
                    ['vdu1-5588797866-fs6va', 'vdu1-5588797866-v8sl3'])

    @mock.patch.object(subprocess, 'run')
    @mock.patch.object(client.CoreV1Api, 'list_namespaced_pod')
    @mock.patch.object(client.AppsV1Api, 'patch_namespaced_deployment')
    @mock.patch.object(client.AppsV1Api, 'read_namespaced_deployment')
    @mock.patch.object(client.AppsV1Api, 'create_namespaced_deployment')
    def test_change_vnfpkg_with_no_op_parameters(
            self, mock_deployment, mock_read_deployment,
            mock_patch_deployment, mock_pods, mock_run):
        # prepare instantiate
        req = objects.InstantiateVnfRequest.from_dict(
            _instantiate_req_example)
        inst = objects.VnfInstanceV2(
            vimConnectionInfo=req.vimConnectionInfo
        )
        grant_req = objects.GrantRequestV1(
            operation=fields.LcmOperationType.INSTANTIATE
        )
        grant = objects.GrantV1()

        mock_read_deployment.return_value = fakes.fake_deployment(
            ready_replicas=2)
        mock_pods.return_value = fakes.fake_pods()

        # execute instantiate
        self.driver.instantiate(req, inst, grant_req, grant, self.vnfd_1)

        # check
        for vnfc_res in inst.instantiatedVnfInfo.vnfcResourceInfo:
            if vnfc_res.vduId == "VDU1":
                self.assertEqual(
                    vnfc_res.metadata['Deployment']['namespace'], 'default')
                self.assertEqual(
                    vnfc_res.metadata['Deployment']['name'], 'vdu1')

        # prepare change_vnfpkg
        req_change = objects.ChangeCurrentVnfPkgRequest.from_dict(
            _change_vnfpkg_example)
        del req_change.additionalParams['vdu_params']
        grant_req_change = objects.GrantRequestV1(
            operation=fields.LcmOperationType.CHANGE_VNFPKG
        )
        mock_pods.return_value = fakes.fake_pods(
            name1='vdu1-5588797866-fs6va', name2='vdu1-5588797866-v8sl3')
        out = requests.Response()
        out.returncode = 0
        mock_run.return_value = out

        # execute change_vnfpkg
        self.driver.change_vnfpkg(
            req_change, inst, grant_req_change, grant, self.vnfd_2)
        # check
        for vnfc_res in inst.instantiatedVnfInfo.vnfcResourceInfo:
            if vnfc_res.vduId == "VDU1":
                self.assertEqual(
                    vnfc_res.metadata['Deployment']['namespace'], 'default')
                self.assertEqual(
                    vnfc_res.metadata['Deployment']['name'], 'vdu1')
                self.assertIn(
                    vnfc_res.computeResource.resourceId,
                    ['vdu1-5588797866-fs6va', 'vdu1-5588797866-v8sl3'])

    @mock.patch.object(client.CoreV1Api, 'list_namespaced_pod')
    @mock.patch.object(client.AppsV1Api, 'patch_namespaced_deployment')
    @mock.patch.object(client.AppsV1Api, 'read_namespaced_deployment')
    @mock.patch.object(client.AppsV1Api, 'create_namespaced_deployment')
    def test_change_vnfpkg_failed(
            self, mock_deployment, mock_read_deployment,
            mock_patch_deployment, mock_pods):
        # prepare instantiate
        req = objects.InstantiateVnfRequest.from_dict(
            _instantiate_req_example)
        inst = objects.VnfInstanceV2(
            vimConnectionInfo=req.vimConnectionInfo
        )
        grant_req = objects.GrantRequestV1(
            operation=fields.LcmOperationType.INSTANTIATE
        )
        grant = objects.GrantV1()

        mock_read_deployment.return_value = fakes.fake_deployment(
            ready_replicas=2)
        mock_pods.return_value = fakes.fake_pods()

        # execute instantiate
        self.driver.instantiate(req, inst, grant_req, grant, self.vnfd_1)

        # check
        for vnfc_res in inst.instantiatedVnfInfo.vnfcResourceInfo:
            if vnfc_res.vduId == "VDU1":
                self.assertEqual(
                    vnfc_res.metadata['Deployment']['namespace'], 'default')
                self.assertEqual(
                    vnfc_res.metadata['Deployment']['name'], 'vdu1')

        # prepare change_vnfpkg
        req_change = objects.ChangeCurrentVnfPkgRequest.from_dict(
            _change_vnfpkg_example)
        del req_change.additionalParams['vdu_params']
        grant_req_change = objects.GrantRequestV1(
            operation=fields.LcmOperationType.CHANGE_VNFPKG
        )

        mock_pods.return_value = fakes.fake_pods(failed_pod=True)

        self.assertRaises(
            sol_ex.UpdateK8SResourceFailed,
            self.driver.change_vnfpkg, req_change, inst,
            grant_req_change, grant, self.vnfd_2)
        # check
        for vnfc_res in inst.instantiatedVnfInfo.vnfcResourceInfo:
            if vnfc_res.vduId == "VDU1":
                self.assertEqual(
                    vnfc_res.metadata['Deployment']['namespace'], 'default')
                self.assertEqual(
                    vnfc_res.metadata['Deployment']['name'], 'vdu1')
        self.assertEqual(len(inst.instantiatedVnfInfo.vnfcResourceInfo), 3)

    @mock.patch.object(subprocess, 'run')
    @mock.patch.object(client.CoreV1Api, 'list_namespaced_pod')
    @mock.patch.object(client.AppsV1Api, 'patch_namespaced_deployment')
    @mock.patch.object(client.AppsV1Api, 'read_namespaced_deployment')
    @mock.patch.object(client.AppsV1Api, 'create_namespaced_deployment')
    def test_change_vnfpkg_in_coordinate_vnf(
            self, mock_deployment, mock_read_deployment,
            mock_patch_deployment, mock_pods, mock_run):
        # prepare instantiate
        req = objects.InstantiateVnfRequest.from_dict(
            _instantiate_req_example)
        inst = objects.VnfInstanceV2(
            vimConnectionInfo=req.vimConnectionInfo
        )
        grant_req = objects.GrantRequestV1(
            operation=fields.LcmOperationType.INSTANTIATE
        )
        grant = objects.GrantV1()

        mock_read_deployment.return_value = fakes.fake_deployment(
            ready_replicas=2)
        mock_pods.return_value = fakes.fake_pods()

        # execute instantiate
        self.driver.instantiate(req, inst, grant_req, grant, self.vnfd_1)

        # check
        for vnfc_res in inst.instantiatedVnfInfo.vnfcResourceInfo:
            if vnfc_res.vduId == "VDU1":
                self.assertEqual(
                    vnfc_res.metadata['Deployment']['namespace'], 'default')
                self.assertEqual(
                    vnfc_res.metadata['Deployment']['name'], 'vdu1')

        # prepare change_vnfpkg
        req_change = objects.ChangeCurrentVnfPkgRequest.from_dict(
            _change_vnfpkg_example)
        del req_change.additionalParams['vdu_params']
        req_change.additionalParams[
            'lcm-operation-coordinate-new-vnf'] = 'error.py'
        grant_req_change = objects.GrantRequestV1(
            operation=fields.LcmOperationType.CHANGE_VNFPKG
        )

        mock_pods.return_value = fakes.fake_pods(
            name1='vdu1-5588797866-fs6va', name2='vdu1-5588797866-v8sl3')
        out = requests.Response()
        out.returncode = 1
        mock_run.return_value = out

        self.assertRaises(
            sol_ex.CoordinateVNFExecutionFailed,
            self.driver.change_vnfpkg, req_change, inst,
            grant_req_change, grant, self.vnfd_2)
        # check
        for vnfc_res in inst.instantiatedVnfInfo.vnfcResourceInfo:
            if vnfc_res.vduId == "VDU1":
                self.assertEqual(
                    vnfc_res.metadata['Deployment']['namespace'], 'default')
                self.assertEqual(
                    vnfc_res.metadata['Deployment']['name'], 'vdu1')
                self.assertIn(
                    vnfc_res.computeResource.resourceId,
                    ['vdu1-5588797866-fs6va', 'vdu1-5588797866-v8sl3'])

    @mock.patch.object(client.CoreV1Api, 'list_namespaced_pod')
    @mock.patch.object(client.AppsV1Api, 'read_namespaced_deployment')
    @mock.patch.object(client.AppsV1Api, 'create_namespaced_deployment')
    def test_change_vnfpkg_update_failed(
            self, mock_deployment, mock_read_deployment, mock_pods):
        # prepare instantiate
        req = objects.InstantiateVnfRequest.from_dict(
            _instantiate_req_example)
        inst = objects.VnfInstanceV2(
            vimConnectionInfo=req.vimConnectionInfo
        )
        grant_req = objects.GrantRequestV1(
            operation=fields.LcmOperationType.INSTANTIATE
        )
        grant = objects.GrantV1()

        mock_read_deployment.return_value = fakes.fake_deployment(
            ready_replicas=2)
        mock_pods.return_value = fakes.fake_pods()

        # execute instantiate
        self.driver.instantiate(req, inst, grant_req, grant, self.vnfd_1)

        # prepare change_vnfpkg
        req_change = objects.ChangeCurrentVnfPkgRequest.from_dict(
            _change_vnfpkg_example)
        del req_change.additionalParams['vdu_params']
        grant_req_change = objects.GrantRequestV1(
            operation=fields.LcmOperationType.CHANGE_VNFPKG
        )

        self.assertRaises(
            sol_ex.UpdateK8SResourceFailed,
            self.driver.change_vnfpkg, req_change, inst,
            grant_req_change, grant, self.vnfd_2)

    def test_change_vnfpkg_with_un_support_type(self):
        inst = objects.VnfInstanceV2()
        grant = objects.GrantV1()
        req_change = objects.ChangeCurrentVnfPkgRequest.from_dict(
            _change_vnfpkg_example)
        del req_change.additionalParams['vdu_params']
        req_change.additionalParams['upgrade_type'] = 'BlueGreen'
        grant_req_change = objects.GrantRequestV1(
            operation=fields.LcmOperationType.CHANGE_VNFPKG
        )
        self.assertRaises(
            sol_ex.SolException,
            self.driver.change_vnfpkg, req_change, inst,
            grant_req_change, grant, self.vnfd_2)

    @mock.patch.object(subprocess, 'run')
    @mock.patch.object(client.CoreV1Api, 'list_namespaced_pod')
    @mock.patch.object(client.AppsV1Api, 'patch_namespaced_deployment')
    @mock.patch.object(client.AppsV1Api, 'read_namespaced_deployment')
    @mock.patch.object(client.AppsV1Api, 'create_namespaced_deployment')
    def test_change_vnfpkg_rollback(
            self, mock_deployment, mock_read_deployment,
            mock_patch_deployment, mock_pods, mock_run):
        # prepare instantiate
        req = objects.InstantiateVnfRequest.from_dict(
            _instantiate_req_example)
        inst = objects.VnfInstanceV2(
            id=uuidutils.generate_uuid(),
            vimConnectionInfo=req.vimConnectionInfo
        )
        grant_req = objects.GrantRequestV1(
            operation=fields.LcmOperationType.INSTANTIATE
        )
        grant = objects.GrantV1()

        mock_read_deployment.return_value = fakes.fake_deployment(
            ready_replicas=2)
        mock_pods.return_value = fakes.fake_pods()

        # execute instantiate
        self.driver.instantiate(req, inst, grant_req, grant, self.vnfd_1)

        # prepare change_vnfpkg_rollback
        req_change = objects.ChangeCurrentVnfPkgRequest.from_dict(
            _change_vnfpkg_example)
        resource_changes = objects.VnfLcmOpOccV2_ResourceChanges.from_dict(
            _update_resources)
        lcmocc = objects.VnfLcmOpOccV2(
            # required fields
            id=uuidutils.generate_uuid(),
            operationState=fields.LcmOperationStateType.FAILED_TEMP,
            stateEnteredTime=datetime.utcnow(),
            startTime=datetime.utcnow(),
            vnfInstanceId=inst.id,
            operation=fields.LcmOperationType.CHANGE_VNFPKG,
            resourceChanges=resource_changes,
            isAutomaticInvocation=False,
            isCancelPending=False,
            operationParams=req_change)

        grant_req_change = objects.GrantRequestV1(
            operation=fields.LcmOperationType.CHANGE_VNFPKG
        )
        mock_pods.return_value = fakes.fake_pods(
            name1='vdu1-5588797866-fsab1', name2='vdu1-5588797866-v8sl5')
        out = requests.Response()
        out.returncode = 0
        mock_run.return_value = out

        # execute  change_vnfpkg_rollback
        self.driver.change_vnfpkg_rollback(
            req_change, inst, grant_req_change, grant, self.vnfd_1, lcmocc)

        # check
        for vnfc_res in inst.instantiatedVnfInfo.vnfcResourceInfo:
            if vnfc_res.vduId == "VDU1":
                self.assertEqual(
                    vnfc_res.metadata['Deployment']['namespace'], 'default')
                self.assertEqual(
                    vnfc_res.metadata['Deployment']['name'], 'vdu1')
                self.assertIn(
                    vnfc_res.computeResource.resourceId,
                    ['vdu1-5588797866-fsab1', 'vdu1-5588797866-v8sl5'])
