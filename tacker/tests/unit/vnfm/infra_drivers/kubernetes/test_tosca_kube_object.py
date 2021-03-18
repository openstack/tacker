# Copyright (C) 2021 FUJITSU
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

from tacker.tests.unit import base
from tacker.vnfm.infra_drivers.kubernetes.k8s import tosca_kube_object


class TestToscaKubeObject(base.TestCase):
    def setUp(self):
        super(TestToscaKubeObject, self).setUp()
        self.tosca_kube_object = tosca_kube_object.ToscaKubeObject(
            name='name',
            namespace='namespace',
            mapping_ports='mappingports',
            containers=[
                tosca_kube_object.Container(
                    name="name")],
            network_name="network",
            mgmt_connection_point=True,
            scaling_object=[
                tosca_kube_object.ScalingObject(
                    scale_target_name='scalingname')],
            service_type='servicetype',
            labels={
                'lable': 'lable'},
            annotations="annotations")

    def test_tosca_kube_object(self):
        self.assertEqual('name', self.tosca_kube_object.name)
        self.assertEqual('namespace', self.tosca_kube_object.namespace)


class TestContainerObject(base.TestCase):
    def setUp(self):
        super(TestContainerObject, self).setUp()
        self.container_object = tosca_kube_object.Container(
            name='container',
            num_cpus=1,
            mem_size="100MB",
            image="ubuntu",
            command='command',
            args=['args'],
            ports=['22'],
            config='config'
        )

    def test_container_object(self):
        self.assertEqual('container', self.container_object.name)
        self.assertEqual(1, self.container_object.num_cpus)
        self.assertEqual('100MB', self.container_object.mem_size)
        self.assertEqual('ubuntu', self.container_object.image)


class TestScalingObject(base.TestCase):
    def setUp(self):
        super(TestScalingObject, self).setUp()
        self.scaling_object = tosca_kube_object.ScalingObject(
            scaling_name='scalingname',
            min_replicas=1,
            max_replicas=3,
            scale_target_name="cp1",
            target_cpu_utilization_percentage="40"
        )

    def test_scaling_object(self):
        self.assertEqual('scalingname', self.scaling_object.scaling_name)
        self.assertEqual(1, self.scaling_object.min_replicas)
        self.assertEqual(3, self.scaling_object.max_replicas)
        self.assertEqual("cp1", self.scaling_object.scale_target_name)
        self.assertEqual(
            "40", self.scaling_object.target_cpu_utilization_percentage)
