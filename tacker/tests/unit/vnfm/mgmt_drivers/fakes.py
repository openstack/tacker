# Copyright (C) 2022 FUJITSU
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

import datetime
from kubernetes import client
import os

from tacker._i18n import _
from tacker import objects
from tacker.objects import fields
from tacker.tests import uuidsentinel


def get_vnf_instance_object(
        instantiation_state=fields.VnfInstanceState.NOT_INSTANTIATED):
    inst_vnf_info = get_vnf_instantiated_info()

    vnf_instance = objects.VnfInstance(
        id=uuidsentinel.vnf_instance_id,
        vnf_instance_name="Test-Vnf-Instance",
        vnf_instance_description="vnf instance description",
        instantiation_state=instantiation_state, vnfd_id=uuidsentinel.vnfd_id,
        vnf_provider="sample provider", vnf_product_name="vnf product name",
        vnf_software_version='1.0', vnfd_version="2",
        instantiated_vnf_info=inst_vnf_info,
        vnf_metadata={"namespace": "default"}
    )

    return vnf_instance


def get_vnf_instantiated_info(flavour_id='simple',
        instantiation_level_id=None, vnfc_resource_info=None,
        virtual_storage_resource_info=None,
        vnf_virtual_link_resource_info=None,
        ext_managed_virtual_link_info=None,
        ext_virtual_link_info=None,
        ext_cp_info=None):

    vnfc_resource_info = vnfc_resource_info or []
    vnf_virtual_link_resource_info = vnf_virtual_link_resource_info or []
    virtual_storage_resource_info = virtual_storage_resource_info or []
    ext_managed_virtual_link_info = ext_managed_virtual_link_info or []
    ext_virtual_link_info = ext_virtual_link_info or []
    ext_cp_info = ext_cp_info or []

    inst_vnf_info = objects.InstantiatedVnfInfo(
        flavour_id=flavour_id,
        instantiation_level_id=instantiation_level_id,
        instance_id='9693ab84-6da8-5926-5e7a-3a1b963156c0',
        vnfc_resource_info=vnfc_resource_info,
        vnf_virtual_link_resource_info=vnf_virtual_link_resource_info,
        virtual_storage_resource_info=virtual_storage_resource_info,
        ext_managed_virtual_link_info=ext_managed_virtual_link_info,
        ext_virtual_link_info=ext_virtual_link_info,
        ext_cp_info=ext_cp_info,
        additional_params=return_cnf_additional_params())

    return inst_vnf_info


def fake_pod():
    return client.V1Pod(
        api_version='v1',
        kind='Pod',
        metadata=client.V1ObjectMeta(
            name='curry-test001',
            namespace='curryns'
        ),
        spec=client.V1PodSpec(
            containers=[
                client.V1Container(
                    image="curry",
                    name="curry"
                )
            ]
        ),
        status=client.V1PodStatus(
            phase='Running',
        )
    )


def fake_pod_container_config_changed():
    return client.V1Pod(
        api_version='v1',
        kind='Pod',
        metadata=client.V1ObjectMeta(
            name='volume-test',
            namespace='default'
        ),
        spec=client.V1PodSpec(
            containers=[
                client.V1Container(
                    image="cirros",
                    name="nginx",
                    env=[
                        client.V1EnvVar(
                            name='param0',
                            value_from=client.V1EnvVarSource(
                                config_map_key_ref=client.
                                V1ConfigMapKeySelector(
                                    key='param0',
                                    name='cm-data'
                                )
                            )
                        ),
                        client.V1EnvVar(
                            name='param1',
                            value_from=client.V1EnvVarSource(
                                secret_key_ref=client.
                                V1SecretKeySelector(
                                    key='password',
                                    name='secret-data'
                                )
                            )
                        )
                    ],
                )
            ]
        ),
        status=client.V1PodStatus(
            phase='Running',
        )
    )


def fake_pod_volume_config_changed():
    return client.V1Pod(
        api_version='v1',
        kind='Pod',
        metadata=client.V1ObjectMeta(
            name='volume-test',
            namespace='default'
        ),
        spec=client.V1PodSpec(
            containers=[
                client.V1Container(
                    image="cirros",
                    name="nginx",
                    volume_mounts=[
                        client.V1VolumeMount(
                            name='cm-volume',
                            mount_path='/config'
                        ),
                        client.V1VolumeMount(
                            name='sec-volume',
                            mount_path='/etc/secrets'
                        ),
                    ]
                )
            ],
            volumes=[
                client.V1Volume(
                    name='cm-volume',
                    config_map=client.V1ConfigMapVolumeSource(
                        name='cm-data'
                    ),
                ),
                client.V1Volume(
                    name='sec-volume',
                    secret=client.V1SecretVolumeSource(
                        secret_name='secret-data'
                    )
                )
            ]
        ),
        status=client.V1PodStatus(
            phase='Running',
        )
    )


def fake_pod_image_changed():
    return client.V1Pod(
        api_version='v1',
        kind='Pod',
        metadata=client.V1ObjectMeta(
            name='volume-test',
            namespace='default'
        ),
        spec=client.V1PodSpec(
            containers=[
                client.V1Container(
                    image="nginx-old",
                    name="nginx",
                )
            ]
        ),
        status=client.V1PodStatus(
            phase='Running',
        )
    )


def fake_replicaset_container_config_changed():
    return client.V1ReplicaSet(
        api_version='apps/v1',
        kind='ReplicaSet',
        metadata=client.V1ObjectMeta(
            name='vdu2',
            namespace='default'
        ),
        spec=client.V1ReplicaSetSpec(
            selector=client.V1LabelSelector(
                match_labels={'app': 'webserver'}
            ),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(
                    labels={'app': 'webserver',
                            'scaling_name': 'SP1'}
                ),
                spec=client.V1PodSpec(
                    containers=[
                        client.V1Container(
                            env=[
                                client.V1EnvVar(
                                    name='param0',
                                    value_from=client.V1EnvVarSource(
                                        config_map_key_ref=client.
                                        V1ConfigMapKeySelector(
                                            key='param0',
                                            name='cm-data'
                                        )
                                    )
                                ),
                                client.V1EnvVar(
                                    name='param1',
                                    value_from=client.V1EnvVarSource(
                                        secret_key_ref=client.
                                        V1SecretKeySelector(
                                            key='password',
                                            name='secret-data'
                                        )
                                    )
                                )
                            ],
                            image='celebdor/kuryr-demo',
                            image_pull_policy='IfNotPresent',
                            name='nginx',
                            ports=[
                                client.V1ContainerPort(
                                    container_port=8080
                                )
                            ],
                            resources=client.V1ResourceRequirements(
                                limits={
                                    'cpu': '500m', 'memory': '512M'
                                },
                                requests={
                                    'cpu': '500m', 'memory': '512M'
                                }
                            ),
                            volume_mounts=[
                                client.V1VolumeMount(
                                    name='curry-claim-volume',
                                    mount_path='/data'
                                )
                            ]
                        )
                    ],
                    termination_grace_period_seconds=0
                )
            )
        ),
        status=client.V1ReplicaSetStatus(
            replicas=1,
        )
    )


def fake_replicaset_volume_config_changed():
    return client.V1ReplicaSet(
        api_version='apps/v1',
        kind='ReplicaSet',
        metadata=client.V1ObjectMeta(
            name='vdu2',
            namespace='default'
        ),
        spec=client.V1ReplicaSetSpec(
            selector=client.V1LabelSelector(
                match_labels={'app': 'webserver'}
            ),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(
                    labels={'app': 'webserver',
                            'scaling_name': 'SP1'}
                ),
                spec=client.V1PodSpec(
                    containers=[
                        client.V1Container(
                            image='celebdor/kuryr-demo',
                            image_pull_policy='IfNotPresent',
                            name='nginx',
                            ports=[
                                client.V1ContainerPort(
                                    container_port=8080
                                )
                            ],
                            resources=client.V1ResourceRequirements(
                                limits={
                                    'cpu': '500m', 'memory': '512M'
                                },
                                requests={
                                    'cpu': '500m', 'memory': '512M'
                                }
                            ),
                            volume_mounts=[
                                client.V1VolumeMount(
                                    name='curry-claim-volume',
                                    mount_path='/data'
                                )
                            ]
                        )
                    ],
                    volumes=[
                        client.V1Volume(
                            name='curry-claim-volume',
                            persistent_volume_claim=client.
                            V1PersistentVolumeClaimVolumeSource(
                                claim_name='curry-pv-claim'
                            ),
                            config_map=client.V1ConfigMapVolumeSource(
                                default_mode=438,
                                name='cm-data'

                            ),
                            secret=client.V1SecretVolumeSource(
                                secret_name='secret-data'
                            )
                        )
                    ],
                    termination_grace_period_seconds=0
                )
            )
        ),
        status=client.V1ReplicaSetStatus(
            replicas=1,
        )
    )


def fake_replicaset_image_changed():
    return client.V1ReplicaSet(
        api_version='apps/v1',
        kind='ReplicaSet',
        metadata=client.V1ObjectMeta(
            name='vdu2',
            namespace='default'
        ),
        spec=client.V1ReplicaSetSpec(
            selector=client.V1LabelSelector(
                match_labels={'app': 'webserver'}
            ),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(
                    labels={'app': 'webserver',
                            'scaling_name': 'SP1'}
                ),
                spec=client.V1PodSpec(
                    containers=[
                        client.V1Container(
                            image='celebdor/kuryr-demo-old',
                            image_pull_policy='IfNotPresent',
                            name='nginx',
                            ports=[
                                client.V1ContainerPort(
                                    container_port=8080
                                )
                            ],
                            resources=client.V1ResourceRequirements(
                                limits={
                                    'cpu': '500m', 'memory': '512M'
                                },
                                requests={
                                    'cpu': '500m', 'memory': '512M'
                                }
                            ),
                        )
                    ],
                    termination_grace_period_seconds=0
                )
            )
        ),
        status=client.V1ReplicaSetStatus(
            replicas=1,
        )
    )


def fake_list_pod():
    return client.V1PodList(
        items=[
            client.V1Pod(
                api_version='v1',
                kind='Pod',
                metadata=client.V1ObjectMeta(
                    name='curry-test001',
                    namespace='curryns'
                ),
                spec=client.V1PodSpec(
                    containers=[
                        client.V1Container(
                            image="curry",
                            name="curry"
                        )
                    ]
                ),
                status=client.V1PodStatus(
                    phase='Pending',
                )
            )
        ]
    )


def get_fake_pod_info(kind, name='fake_name', pod_status='Running',
                      pod_name=None):
    if not pod_name:
        if kind == 'Deployment':
            pod_name = _('{name}-1234567890-abcde').format(name=name)
        elif kind in ('ReplicaSet', 'DaemonSet'):
            pod_name = _('{name}-12345').format(name=name)
        elif kind == 'StatefulSet':
            pod_name = _('{name}-1').format(name=name)
        elif kind == 'Pod':
            pod_name = name
    return client.V1Pod(
        metadata=client.V1ObjectMeta(
            name=pod_name,
            creation_timestamp=datetime.datetime.now().isoformat('T')),
        status=client.V1PodStatus(phase=pod_status))


def vnfd_dict_cnf():
    tacker_dir = os.getcwd()
    def_dir = tacker_dir + "/samples/vnf_packages/Definitions/"
    vnfd_dict = {
        "tosca_definitions_version": "tosca_simple_yaml_1_2",
        "description": "Sample VNF flavour for Sample VNF",
        "imports": [
            def_dir + "etsi_nfv_sol001_common_types.yaml",
            def_dir + "etsi_nfv_sol001_vnfd_types.yaml",
            def_dir + "helloworld3_types.yaml"],
        "topology_template": {
            "node_templates": {
                "VNF": {
                    "type": "company.provider.VNF",
                    "properties": {
                        "flavour_description": "A simple flavour"}},
                "VDU1": {
                    "type": "tosca.nodes.nfv.Vdu.Compute",
                    "properties": {
                        "name": "vdu1",
                        "description": "vdu1 compute node",
                        "vdu_profile": {
                            "min_number_of_instances": 1,
                            "max_number_of_instances": 3}}}},
            "policies": [
                {
                    "scaling_aspects": {
                        "type": "tosca.policies.nfv.ScalingAspects",
                        "properties": {
                            "aspects": {
                                "vdu1_aspect": {
                                    "name": "vdu1_aspect",
                                    "description": "vdu1 scaling aspect",
                                    "max_scale_level": 2,
                                    "step_deltas": ["delta_1"]}}}}},
                {
                    "vdu1_initial_delta": {
                        "type": "tosca.policies.nfv.VduInitialDelta",
                        "properties": {
                            "initial_delta": {
                                "number_of_instances": 0}},
                        "targets": ["VDU1"]}},
                {
                    "vdu1_scaling_aspect_deltas": {
                        "type": "tosca.policies.nfv.VduScalingAspectDeltas",
                        "properties": {
                            "aspect": "vdu1_aspect",
                            "deltas": {
                                "delta_1": {
                                    "number_of_instances": 1}}},
                        "targets": ["VDU1"]}},
                {
                    "instantiation_levels": {
                        "type": "tosca.policies.nfv.InstantiationLevels",
                        "properties": {
                            "levels": {
                                "instantiation_level_1": {
                                    "description": "Smallest size",
                                    "scale_info": {
                                        "vdu1_aspect": {
                                            "scale_level": 0}}},
                                "instantiation_level_2": {
                                    "description": "Largest size",
                                    "scale_info": {
                                        "vdu1_aspect": {
                                            "scale_level": 2}}}
                            },
                            "default_level": "instantiation_level_1"}}},
                {
                    "vdu1_instantiation_levels": {
                        "type": "tosca.policies.nfv.VduInstantiationLevels",
                        "properties": {
                            "levels": {
                                "instantiation_level_1": {
                                    "number_of_instances": 0},
                                "instantiation_level_2": {
                                    "number_of_instances": 2}}},
                        "targets": ["VDU1"]}}
            ]
        }
    }
    return vnfd_dict


def return_cnf_additional_params():
    additional_params = {
        "lcm-kubernetes-def-files": [
            "Files/kubernetes/configmap_1.yaml",
            "Files/kubernetes/pod_volume.yaml",
            "Files/kubernetes/replicaset.yaml",
            "Files/kubernetes/secret_1.yaml"
        ],
        "namespace": "default"
    }
    return additional_params


def fake_k8s_clients():
    k8s_clients = {
        'v1': client.CoreV1Api(),
        'apiregistration.k8s.io/v1': client.ApiregistrationV1Api(),
        'apps/v1': client.AppsV1Api(),
        'authentication.k8s.io/v1': client.AuthenticationV1Api(),
        'authorization.k8s.io/v1': client.AuthorizationV1Api(),
        'autoscaling/v1': client.AutoscalingV1Api(),
        'batch/v1': client.BatchV1Api(),
        'coordination.k8s.io/v1': client.CoordinationV1Api(),
        'networking.k8s.io/v1': client.NetworkingV1Api(),
        'rbac.authorization.k8s.io/v1': client.RbacAuthorizationV1Api(),
        'scheduling.k8s.io/v1': client.SchedulingV1Api(),
        'storage.k8s.io/v1': client.StorageV1Api()
    }
    return k8s_clients
