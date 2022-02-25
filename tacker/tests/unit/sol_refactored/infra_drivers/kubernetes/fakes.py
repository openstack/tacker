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

from kubernetes import client


def fake_namespace():
    return client.V1Namespace(
        api_version='v1',
        kind='Namespace',
        metadata=client.V1ObjectMeta(
            name='curry'
        ),
        status=client.V1NamespaceStatus(
            phase='Active'
        )
    )


def fake_deployment(ready_replicas=0):
    return client.V1Deployment(
        api_version='apps/v1',
        kind='Deployment',
        metadata=client.V1ObjectMeta(
            name='vdu1',
            namespace='curry'
        ),
        status=client.V1DeploymentStatus(
            replicas=2,
            ready_replicas=ready_replicas
        ),
        spec=client.V1DeploymentSpec(
            replicas=2,
            selector=client.V1LabelSelector(
                match_labels={'app': 'webserver'}
            ),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(
                    labels={'app': 'webserver'}
                )
            )
        )
    )


def fake_pods(name1='vdu1-5588797866-fs6vb',
              name2='vdu1-5588797866-v8sl2',
              failed_pod=False):
    common_pods = client.V1PodList(
        items=[client.V1Pod(
            metadata=client.V1ObjectMeta(
                name=name1
            ),
            status=client.V1PodStatus(
                phase="Running"
            )
        ), client.V1Pod(
            metadata=client.V1ObjectMeta(
                name=name2
            ),
            status=client.V1PodStatus(
                phase="Running"
            )
        )]
    )
    if failed_pod:
        common_pods.items.append(client.V1Pod(
            metadata=client.V1ObjectMeta(
                name='vdu1-5588797866-v9644'
            ),
            status=client.V1PodStatus(
                phase="Unknown"
            )
        ))
    return common_pods


def fake_pod_vdu2(name='vdu2-v8sl2'):
    return client.V1PodList(
        items=[client.V1Pod(
            metadata=client.V1ObjectMeta(
                name=name
            ),
            status=client.V1PodStatus(
                phase="Running"
            )
        )]
    )


def fake_none():
    return client.exceptions.ApiException


def fake_sa():
    return client.V1ServiceAccount(
        api_version='v1',
        kind='ServiceAccount',
        metadata=client.V1ObjectMeta(
            name='curry-cluster-sa',
            namespace='default'
        )
    )


def fake_cluster_role():
    return client.V1ClusterRole(
        api_version='rbac.authorization.k8s.io/v1',
        kind='ClusterRole',
        metadata=client.V1ObjectMeta(
            name='curry-cluster-role'
        )
    )


def fake_cluster_role_binding():
    return client.V1ClusterRoleBinding(
        api_version='rbac.authorization.k8s.io/v1',
        kind='ClusterRoleBinding',
        metadata=client.V1ObjectMeta(
            name='curry-cluster-rolebinding'
        ),
        role_ref='test'
    )


def fake_role():
    return client.V1Role(
        api_version='rbac.authorization.k8s.io/v1',
        kind='Role',
        metadata=client.V1ObjectMeta(
            name='curry-role'
        )
    )


def fake_role_binding():
    return client.V1RoleBinding(
        api_version='rbac.authorization.k8s.io/v1',
        kind='RoleBinding',
        metadata=client.V1ObjectMeta(
            name='curry--rolebinding'
        ),
        role_ref='test'
    )


def fake_config_map():
    return client.V1ConfigMap(
        api_version='v1',
        kind='ConfigMap',
        metadata=client.V1ObjectMeta(
            name='curry-test001',
            namespace='default'
        )
    )


def fake_cr():
    return client.V1ControllerRevision(
        api_version='apps/v1',
        kind='ControllerRevision',
        metadata=client.V1ObjectMeta(
            name='curry-test001',
            namespace='default'
        ),
        revision='test'
    )


def fake_daemon_set(number_ready=0):
    return client.V1DaemonSet(
        api_version='apps/v1',
        kind='DaemonSet',
        metadata=client.V1ObjectMeta(
            name='curry-test001',
            namespace='default'
        ),
        status=client.V1DaemonSetStatus(
            number_ready=number_ready,
            desired_number_scheduled=1,
            current_number_scheduled=1,
            number_misscheduled=0,
        ),
        spec=client.V1DaemonSetSpec(
            selector=client.V1LabelSelector(
                match_labels={'app': 'webserver'}
            ),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(
                    labels={'app': 'webserver'}
                )
            )
        )
    )


def fake_hpa():
    return client.V1HorizontalPodAutoscaler(
        api_version='autoscaling/v1',
        kind='HorizontalPodAutoscaler',
        metadata=client.V1ObjectMeta(
            name='curry-hpa-vdu001',
            namespace='default'
        )
    )


def fake_job(succeeded=1):
    return client.V1Job(
        api_version='batch/v1',
        kind='Job',
        metadata=client.V1ObjectMeta(
            name='curry-test001',
            namespace='default'
        ),
        spec=client.V1JobSpec(
            completions=5,
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(
                    name='curry-test001',
                    namespace='default'
                ),
                spec=client.V1PodSpec(
                    hostname='job',
                    containers=['image']
                )
            )
        ),
        status=client.V1JobStatus(
            succeeded=succeeded,
        )
    )


def fake_lr():
    return client.V1LimitRange(
        api_version='v1',
        kind='LimitRange',
        metadata=client.V1ObjectMeta(
            name='limits',
            namespace='default'
        )
    )


def fake_lease():
    return client.V1Lease(
        api_version='coordination.k8s.io/v1',
        kind='Lease',
        metadata=client.V1ObjectMeta(
            name='curry-lease',
            namespace='default'
        )
    )


def fake_np():
    return client.V1NetworkPolicy(
        api_version='networking.k8s.io/v1',
        kind='NetworkPolicy',
        metadata=client.V1ObjectMeta(
            name='all-deny',
            namespace='default'
        )
    )


def fake_pc():
    return client.V1PriorityClass(
        api_version='scheduling.k8s.io/v1',
        kind='PriorityClass',
        metadata=client.V1ObjectMeta(
            name='high-priority'
        ),
        value=1000000
    )


def fake_persistent_volume(
        name='curry-sc-pv', phase='UnAvailable'):
    return client.V1PersistentVolume(
        api_version='v1',
        kind='PersistentVolume',
        metadata=client.V1ObjectMeta(
            name=name
        ),
        status=client.V1PersistentVolumeStatus(
            phase=phase
        )
    )


def fake_pod(phase='Pending'):
    return client.V1Pod(
        api_version='v1',
        kind='Pod',
        metadata=client.V1ObjectMeta(
            name='vdu2',
            namespace='default'
        ),
        status=client.V1PodStatus(
            phase=phase,
        )
    )


def fake_pt():
    return client.V1PodTemplate(
        api_version='v1',
        kind='PodTemplate',
        metadata=client.V1ObjectMeta(
            name='curry-test001',
            namespace='default'
        )
    )


def fake_rs(ready_replicas=0):
    return client.V1ReplicaSet(
        api_version='apps/v1',
        kind='ReplicaSet',
        metadata=client.V1ObjectMeta(
            name='curry-test001',
            namespace='default'
        ),
        status=client.V1ReplicaSetStatus(
            replicas=2,
            ready_replicas=ready_replicas
        ),
        spec=client.V1ReplicaSetSpec(
            replicas=2,
            selector=client.V1LabelSelector(
                match_labels={'app': 'webserver'}
            ),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(
                    labels={'app': 'webserver'}
                )
            )
        )
    )


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


def fake_sec():
    return client.V1Secret(
        api_version='v1',
        kind='Secret',
        metadata=client.V1ObjectMeta(
            name='curry-sc-multiple',
            namespace='default'
        )
    )


def fake_rq():
    return client.V1ResourceQuota(
        api_version='v1',
        kind='ResourceQuota',
        metadata=client.V1ObjectMeta(
            name='curry-rq',
            namespace='default'
        )
    )


def fake_stateful_set(ready_replicas=0):
    return client.V1StatefulSet(
        api_version='apps/v1',
        kind='StatefulSet',
        metadata=client.V1ObjectMeta(
            name='vdu1',
            namespace='default'
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
            ready_replicas=ready_replicas
        ),
    )


def fake_pvc(name):
    return client.V1PersistentVolumeClaim(
        api_version='v1',
        kind='PersistentVolumeClaim',
        metadata=client.V1ObjectMeta(
            name=name
        ),
        status=client.V1PersistentVolumeClaimStatus(
            phase='Bound'
        )
    )


def fake_pvcs():
    return client.V1PersistentVolumeClaimList(
        items=[client.V1PersistentVolumeClaim(
            api_version='v1',
            kind='PersistentVolumeClaim',
            metadata=client.V1ObjectMeta(
                name='www-vdu1-0'
            ),
            status=client.V1PersistentVolumeClaimStatus(
                phase='Bound'
            )
        ), client.V1PersistentVolumeClaim(
            api_version='v1',
            kind='PersistentVolumeClaim',
            metadata=client.V1ObjectMeta(
                name='www-vdu1-1'
            ),
            status=client.V1PersistentVolumeClaimStatus(
                phase='Bound'
            )
        ), client.V1PersistentVolumeClaim(
            api_version='v1',
            kind='PersistentVolumeClaim',
            metadata=client.V1ObjectMeta(
                name='test'
            ),
            status=client.V1PersistentVolumeClaimStatus(
                phase='Bound'
            )
        ),
        ]
    )


def fake_sc(name='curry-sc-local'):
    return client.V1StorageClass(
        api_version='v1',
        kind='StorageClass',
        metadata=client.V1ObjectMeta(
            name=name
        ),
        provisioner='kubernetes.io/no-provisioner'
    )


def fake_api_service(type='Available'):
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
                    type=type,
                    status='True'
                )
            ]
        )
    )


def fake_volume_attachment(attached='True'):
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
            attached=attached,
        )
    )


def fake_node(type='Ready', status='True'):
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
                    status=status,
                    type=type
                )
            ]
        )
    )
