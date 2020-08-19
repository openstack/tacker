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

CREATE_K8S_FALSE_VALUE = None


def fake_k8s_dict():
    k8s_client_dict = {
        'namespace': 'curryns',
        'object': fake_k8s_obj()
    }
    return k8s_client_dict


def fake_k8s_obj():
    return client.V1Deployment(
        api_version='apps/v1',
        kind='Deployment',
        metadata=client.V1ObjectMeta(
            name='curry-test001',
            namespace='curryns'
        ),
        spec=client.V1DeploymentSpec(
            replicas=2,
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
                                            name='curry-test001'
                                        )
                                    )
                                ),
                                client.V1EnvVar(
                                    name='param1',
                                    value_from=client.V1EnvVarSource(
                                        config_map_key_ref=client.
                                        V1ConfigMapKeySelector(
                                            key='param1',
                                            name='curry-test001'
                                        )
                                    )
                                )
                            ],
                            image='celebdor/kuryr-demo',
                            image_pull_policy='IfNotPresent',
                            name='web-server',
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
                            )
                        )
                    ],
                    termination_grace_period_seconds=0
                )
            )
        )
    )


def fake_k8s_client_dict():
    k8s_client_dict = {
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
    return k8s_client_dict


def fake_k8s_objs_node():
    objs = [
        {
            'namespace': 'test',
            'status': 'Creating',
            'object': fake_node()
        }
    ]
    return objs


def fake_node():
    return client.V1Node(
        api_version='v1',
        kind='Node',
        metadata=client.V1ObjectMeta(
            name='curry-node-test',
            labels={'name': 'curry-node-test'}
        ),
        status=client.V1NodeStatus(
            conditions=[
                client.V1NodeCondition(
                    status='True',
                    type='Ready'
                )
            ]
        )
    )


def fake_k8s_objs_node_status_false():
    objs = [
        {
            'namespace': 'test',
            'status': 'Creating',
            'object': fake_node_false()
        }
    ]
    return objs


def fake_node_false():
    return client.V1Node(
        api_version='v1',
        kind='Node',
        metadata=client.V1ObjectMeta(
            name='curry-node-test',
            labels={'name': 'curry-node-test'}
        ),
        status=client.V1NodeStatus(
            conditions=[
                client.V1NodeCondition(
                    status='False',
                    type='Ready'
                )
            ]
        )
    )


def fake_k8s_objs_pvc():
    objs = [
        {
            'namespace': 'test',
            'status': 'Creating',
            'object': fake_pvc()
        }
    ]
    return objs


def fake_pvc():
    return client.V1PersistentVolumeClaim(
        api_version='v1',
        kind='PersistentVolumeClaim',
        metadata=client.V1ObjectMeta(
            name='curry-sc-pvc'
        ),
        status=client.V1PersistentVolumeClaimStatus(
            phase='Bound'
        )
    )


def fake_k8s_objs_pvc_false_phase():
    objs = [
        {
            'namespace': 'test',
            'status': 'Creating',
            'object': fake_pvc_false()
        }
    ]
    return objs


def fake_pvc_false():
    return client.V1PersistentVolumeClaim(
        api_version='v1',
        kind='PersistentVolumeClaim',
        metadata=client.V1ObjectMeta(
            name='curry-sc-pvc'
        ),
        status=client.V1PersistentVolumeClaimStatus(
            phase='UnBound'
        )
    )


def fake_k8s_objs_namespace():
    objs = [
        {
            'namespace': 'test',
            'status': 'Creating',
            'object': fake_namespace()
        }
    ]
    return objs


def fake_namespace():
    return client.V1Namespace(
        api_version='v1',
        kind='Namespace',
        metadata=client.V1ObjectMeta(
            name='curry-ns'
        ),
        status=client.V1NamespaceStatus(
            phase='Active'
        )
    )


def fake_k8s_objs_namespace_false_phase():
    objs = [
        {
            'namespace': 'test',
            'status': 'Creating',
            'object': fake_namespace_false()
        }
    ]
    return objs


def fake_namespace_false():
    return client.V1Namespace(
        api_version='v1',
        kind='Namespace',
        metadata=client.V1ObjectMeta(
            name='curry-ns'
        ),
        status=client.V1NamespaceStatus(
            phase='NotActive'
        )
    )


def fake_k8s_objs_service():
    objs = [
        {
            'namespace': 'default',
            'status': 'Creating',
            'object': fake_service()
        }
    ]
    return objs


def fake_service():
    return client.V1Service(
        api_version='v1',
        kind='Service',
        metadata=client.V1ObjectMeta(
            labels={
                'app': 'webserver',
                'vdu_name': 'curry-svc-vdu001'
            },
            name='curry-svc-vdu001',
            namespace='default'
        ),
        spec=client.V1ServiceSpec(
            cluster_ip=''
        )
    )


def fake_k8s_objs_service_false_cluster_ip():
    objs = [
        {
            'namespace': 'default',
            'status': 'Creating',
            'object': fake_service_false()
        }
    ]
    return objs


def fake_service_false():
    return client.V1Service(
        api_version='v1',
        kind='Service',
        metadata=client.V1ObjectMeta(
            labels={
                'app': 'webserver',
                'vdu_name': 'curry-svc-vdu001'
            },
            name='curry-svc-vdu001',
            namespace='default'
        ),
        spec=client.V1ServiceSpec(
            cluster_ip='127.0.0.1'
        )
    )


def fake_endpoinds():
    return client.V1Endpoints(
        api_version='v1',
        kind='Endpoints',
        metadata=client.V1ObjectMeta(
            namespace='default'
        )
    )


def fake_k8s_objs_deployment():
    obj = [
        {
            'namespace': 'test',
            'status': 'Creating',
            'object': fake_v1_deployment()
        }
    ]

    return obj


def fake_k8s_objs_deployment_error():
    obj = [
        {
            'namespace': 'test',
            'status': 'Creating',
            'object': fake_v1_deployment_error()
        }
    ]

    return obj


def fake_k8s_objs_replica_set():
    obj = [
        {
            'namespace': 'test',
            'status': 'Creating',
            'object': fake_v1_replica_set()
        }
    ]

    return obj


def fake_k8s_objs_replica_set_error():
    obj = [
        {
            'namespace': 'test',
            'status': 'Creating',
            'object': fake_v1_replica_set_error()
        }
    ]

    return obj


def fake_k8s_objs_stateful_set():
    obj = [
        {
            'namespace': 'test',
            'status': 'Creating',
            'object': fake_v1_stateful_set()
        }
    ]

    return obj


def fake_k8s_objs_stateful_set_error():
    obj = [
        {
            'namespace': 'test',
            'status': 'Creating',
            'object': fake_v1_stateful_set_error()
        }
    ]

    return obj


def fake_k8s_objs_job():
    obj = [
        {
            'namespace': 'test',
            'status': 'Creating',
            'object': fake_v1_job()
        }
    ]

    return obj


def fake_k8s_objs_job_error():
    obj = [
        {
            'namespace': 'test',
            'status': 'Creating',
            'object': fake_v1_job_error()
        }
    ]

    return obj


def fake_k8s_objs_volume_attachment():
    obj = [
        {
            'namespace': 'test',
            'status': 'Creating',
            'object': fake_v1_volume_attachment()
        }
    ]

    return obj


def fake_k8s_objs_volume_attachment_error():
    obj = [
        {
            'namespace': 'test',
            'status': 'Creating',
            'object': fake_v1_volume_attachment_error()
        }
    ]

    return obj


def fake_v1_deployment():
    return client.V1Deployment(
        api_version='apps/v1',
        kind='Deployment',
        metadata=client.V1ObjectMeta(
            name='curry-test001',
            namespace='curryns'
        ),
        status=client.V1DeploymentStatus(
            replicas=1,
            ready_replicas=1
        )
    )


def fake_v1_deployment_error():
    return client.V1Deployment(
        api_version='apps/v1',
        kind='Deployment',
        metadata=client.V1ObjectMeta(
            name='curry-test001',
            namespace='curryns'
        ),
        status=client.V1DeploymentStatus(
            replicas=2,
            ready_replicas=1
        )
    )


def fake_v1_replica_set():
    return client.V1ReplicaSet(
        api_version='apps/v1',
        kind='ReplicaSet',
        metadata=client.V1ObjectMeta(
            name='curry-test001',
            namespace='curryns'
        ),
        status=client.V1ReplicaSetStatus(
            replicas=1,
            ready_replicas=1
        )
    )


def fake_v1_replica_set_error():
    return client.V1ReplicaSet(
        api_version='apps/v1',
        kind='ReplicaSet',
        metadata=client.V1ObjectMeta(
            name='curry-test001',
            namespace='curryns'
        ),
        status=client.V1ReplicaSetStatus(
            replicas=2,
            ready_replicas=1
        )
    )


def fake_v1_job():
    return client.V1Job(
        api_version='batch/v1',
        kind='Job',
        metadata=client.V1ObjectMeta(
            name='curry-test001',
            namespace='curryns'
        ),
        spec=client.V1JobSpec(
            completions=1,
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(
                    name='curry-test001',
                    namespace='curryns'
                ),
                spec=client.V1PodSpec(
                    hostname='job',
                    containers=['image']
                )
            )
        ),
        status=client.V1JobStatus(
            succeeded=1,
        )
    )


def fake_v1_job_error():
    return client.V1Job(
        api_version='batch/v1',
        kind='Job',
        metadata=client.V1ObjectMeta(
            name='curry-test001',
            namespace='curryns'
        ),
        spec=client.V1JobSpec(
            completions=1,
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(
                    name='curry-test001',
                    namespace='curryns'
                ),
                spec=client.V1PodSpec(
                    hostname='job',
                    containers=['image']
                )
            )
        ),
        status=client.V1JobStatus(
            succeeded=2,
        )
    )


def fake_v1_volume_attachment():
    return client.V1VolumeAttachment(
        api_version='storage.k8s.io/v1',
        kind='VolumeAttachment',
        metadata=client.V1ObjectMeta(
            name='curry-test001',
            namespace='curryns'
        ),
        spec=client.V1VolumeAttachmentSpec(
            attacher='nginx',
            node_name='nginx',
            source=client.V1VolumeAttachmentSource(
                persistent_volume_name='curry-sc-pvc'
            )
        ),
        status=client.V1VolumeAttachmentStatus(
            attached=True,
        )
    )


def fake_v1_volume_attachment_error():
    return client.V1VolumeAttachment(
        api_version='storage.k8s.io/v1',
        kind='VolumeAttachment',
        metadata=client.V1ObjectMeta(
            name='curry-test001',
            namespace='curryns'
        ),
        spec=client.V1VolumeAttachmentSpec(
            attacher='nginx',
            node_name='nginx',
            source=client.V1VolumeAttachmentSource(
                persistent_volume_name='curry-sc-pvc'
            )
        ),
        status=client.V1VolumeAttachmentStatus(
            attached=False,
        )
    )


def fake_v1_stateful_set():
    return client.V1StatefulSet(
        api_version='apps/v1',
        kind='StatefulSet',
        metadata=client.V1ObjectMeta(
            name='curry-test001',
            namespace='curryns'
        ),
        spec=client.V1StatefulSetSpec(
            replicas=1,
            volume_claim_templates=[
                client.V1PersistentVolumeClaim(
                    metadata=client.V1ObjectMeta(
                        name='www'
                    )
                )
            ],
            selector=client.V1LabelSelector(
                match_labels={'app': 'nginx'}
            ),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(
                    name='curry-test001',
                    namespace='curryns'
                )
            ),
            service_name='nginx'
        ),
        status=client.V1StatefulSetStatus(
            replicas=1,
            ready_replicas=1
        ),
    )


def fake_v1_stateful_set_error():
    return client.V1StatefulSet(
        api_version='apps/v1',
        kind='StatefulSet',
        metadata=client.V1ObjectMeta(
            name='curry-test001',
            namespace='curryns'
        ),
        spec=client.V1StatefulSetSpec(
            replicas=1,
            volume_claim_templates=[
                client.V1PersistentVolumeClaim(
                    metadata=client.V1ObjectMeta(
                        name='www'
                    )
                )
            ],
            selector=client.V1LabelSelector(
                match_labels={'app': 'nginx'}
            ),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(
                    name='curry-test001',
                    namespace='curryns'
                )
            ),
            service_name='nginx'
        ),
        status=client.V1StatefulSetStatus(
            replicas=2,
            ready_replicas=1
        )
    )


def fake_v1_persistent_volume_claim():
    return client.V1PersistentVolumeClaim(
        api_version='v1',
        kind='PersistentVolumeClaim',
        metadata=client.V1ObjectMeta(
            name='www-curry-test001-0',
            namespace='curryns'
        ),
        status=client.V1PersistentVolumeClaimStatus(
            phase='Bound'
        )
    )


def fake_v1_persistent_volume_claim_error():
    return client.V1PersistentVolumeClaim(
        api_version='v1',
        kind='PersistentVolumeClaim',
        metadata=client.V1ObjectMeta(
            name='curry-test001',
            namespace='curryns'
        ),
        status=client.V1PersistentVolumeClaimStatus(
            phase='Bound1'
        )
    )


def fake_k8s_objs_pod():
    objs = [
        {
            'namespace': 'test',
            'status': 'Creating',
            'object': fake_pod()
        }
    ]
    return objs


def fake_k8s_objs_pod_error():
    objs = [
        {
            'namespace': 'test',
            'status': 'Creating',
            'object': fake_pod_error()
        }
    ]
    return objs


def fake_pod():
    return client.V1Pod(
        api_version='v1',
        kind='Pod',
        metadata=client.V1ObjectMeta(
            name='curry-test001',
            namespace='curryns'
        ),
        status=client.V1PodStatus(
            phase='Running',
        )
    )


def fake_pod_error():
    return client.V1Pod(
        api_version='v1',
        kind='Pod',
        metadata=client.V1ObjectMeta(
            name='curry-test001',
            namespace='curryns'
        ),
        status=client.V1PodStatus(
            phase='Terminated',
        )
    )


def fake_k8s_objs_persistent_volume():
    objs = [
        {
            'namespace': 'test',
            'status': 'Creating',
            'object': fake_persistent_volume()
        }
    ]
    return objs


def fake_k8s_objs_persistent_volume_error():
    objs = [
        {
            'namespace': 'test',
            'status': 'Creating',
            'object': fake_persistent_volume_error()
        }
    ]
    return objs


def fake_persistent_volume():
    return client.V1PersistentVolume(
        api_version='v1',
        kind='PersistentVolume',
        metadata=client.V1ObjectMeta(
            name='curry-test001',
            namespace='curryns'
        ),
        status=client.V1PersistentVolumeStatus(
            phase='Available',
        )
    )


def fake_persistent_volume_error():
    return client.V1PersistentVolume(
        api_version='v1',
        kind='PersistentVolume',
        metadata=client.V1ObjectMeta(
            name='curry-test001',
            namespace='curryns'
        ),
        status=client.V1PersistentVolumeStatus(
            phase='UnBound',
        )
    )


def fake_k8s_objs_api_service():
    objs = [
        {
            'namespace': 'test',
            'status': 'Creating',
            'object': fake_api_service()
        }
    ]
    return objs


def fake_k8s_objs_api_service_error():
    objs = [
        {
            'namespace': 'test',
            'status': 'Creating',
            'object': fake_api_service_error()
        }
    ]
    return objs


def fake_api_service():
    return client.V1APIService(
        api_version='apiregistration.k8s.io/v1',
        kind='APIService',
        metadata=client.V1ObjectMeta(
            name='curry-test001',
            namespace='curryns'
        ),
        status=client.V1APIServiceStatus(
            conditions=[
                client.V1APIServiceCondition(
                    type='Available',
                    status='True'
                )
            ]
        )
    )


def fake_api_service_error():
    return client.V1APIService(
        api_version='apiregistration.k8s.io/v1',
        kind='APIService',
        metadata=client.V1ObjectMeta(
            name='curry-test001',
            namespace='curryns'
        ),
        status=client.V1APIServiceStatus(
            conditions=[
                client.V1APIServiceCondition(
                    type='Unavailable',
                    status='True'
                )
            ]
        )
    )


def fake_k8s_objs_daemon_set():
    objs = [
        {
            'namespace': 'test',
            'status': 'Creating',
            'object': fake_daemon_set()
        }
    ]
    return objs


def fake_k8s_objs_daemon_set_error():
    objs = [
        {
            'namespace': 'test',
            'status': 'Creating',
            'object': fake_daemon_set_error()
        }
    ]
    return objs


def fake_daemon_set():
    return client.V1DaemonSet(
        api_version='apps/v1',
        kind='DaemonSet',
        metadata=client.V1ObjectMeta(
            name='curry-test001',
            namespace='curryns'
        ),
        status=client.V1DaemonSetStatus(
            number_ready=13,
            desired_number_scheduled=13,
            current_number_scheduled=4,
            number_misscheduled=2,
        )
    )


def fake_daemon_set_error():
    return client.V1DaemonSet(
        api_version='apps/v1',
        kind='DaemonSet',
        metadata=client.V1ObjectMeta(
            name='curry-test001',
            namespace='curryns'
        ),
        status=client.V1DaemonSetStatus(
            number_ready=13,
            desired_number_scheduled=12,
            current_number_scheduled=4,
            number_misscheduled=2,
        )
    )
