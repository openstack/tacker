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

import datetime

from kubernetes import client
from oslo_serialization import jsonutils
from oslo_utils import uuidutils
from tacker.db.db_sqlalchemy import models
from tacker import objects
from tacker.objects import vim_connection
from tacker.tests import uuidsentinel

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


def fake_auth_attr():
    return {
        'username': 'fake_user_name',
        'password': 'fake_password',
        'ssl_ca_cert': '-----BEGIN CERTIFICATE-----\
                        samplevalues\
                        -----END CERTIFICATE-----',
        'auth_url': 'http://fake-url/identity/v3'
    }


def fake_vnf_dict(updates=None):
    vnf_dict = {
        'id': 'fake-id,fake-name',
        'status': 'fake-status',
        'attributes': {
            'monitoring_policy': 'fake-monitoring-policy',
            'failure_count': '1',
            'dead_instance_id_1': '00000000-0000-0000-0000-00000000001'},
        'vim_id': 'fake-vim-id',
        'vim_auth': 'fake-vim-auth',
        'instance_id': '00000000-0000-0000-0000-000000000002',
        'placement_attr': {
            'region_name': 'fake-region-name'}}
    if updates:
        vnf_dict.update(updates)
    return vnf_dict


def fake_pod_list():
    return client.V1PodList(
        items=[client.V1Pod(
            metadata=client.V1ObjectMeta(
                name="fake-name"
            ),
            status=client.V1PodStatus(
                phase="Successed"
            )
        )]
    )


def get_scale_policy(type, aspect_id='vdu1', delta_num=1, is_legacy=False,
                     vdu_name='fake_name'):
    policy = dict()
    policy['action'] = type
    policy['name'] = aspect_id
    if is_legacy:
        policy['instance_id'] = "fake_namespace,fake_name"
    else:
        policy['vnf_instance_id'] = uuidsentinel.vnf_instance_id
        policy['delta_num'] = delta_num
        policy['vdu_defs'] = {
            'VDU1': {
                'type': 'tosca.nodes.nfv.Vdu.Compute',
                'properties': {
                    'name': vdu_name,
                    'description': 'test description',
                    'vdu_profile': {
                        'min_number_of_instances': 1,
                        'max_number_of_instances': 3}}}}

    return policy


def get_vnf_resource_list(kind, name='fake_name'):
    vnf_resource = models.VnfResource()
    vnf_resource.vnf_instance_id = uuidsentinel.vnf_instance_id
    vnf_resource.resource_name = name
    vnf_resource.resource_type = f"v1,{kind}"
    vnf_resource.tenant_id = uuidsentinel.tenant_id
    return [vnf_resource]


def get_fake_pod_info(kind, name='fake_name', pod_status='Running',
                      pod_name=None):
    if not pod_name:
        if kind == 'Deployment':
            pod_name = _('{name}-1234567890-abcde').format(name=name)
        elif kind == 'ReplicaSet' or kind == 'DaemonSet':
            pod_name = _('{name}-12345').format(name=name)
        elif kind == 'StatefulSet':
            pod_name = _('{name}-1').format(name=name)
        elif kind == 'Pod':
            pod_name = name
    return client.V1Pod(
        metadata=client.V1ObjectMeta(name=pod_name,
            creation_timestamp=datetime.datetime.now().isoformat('T')),
        status=client.V1PodStatus(phase=pod_status))


def fake_vnfc_resource_info(vdu_id='VDU1', rsc_kind='Deployment',
                            rsc_name='fake_name', pod_name=None,
                            namespace=None):
    def _get_metadata_str(name, namespace="fake_namespace"):
        if namespace == "brank":
            namespace = ""
        metadata = {
            'name': name,
            'namespace': namespace}
        return jsonutils.dumps(metadata)

    vnfc_obj = objects.VnfcResourceInfo()
    vnfc_obj.id = uuidutils.generate_uuid()
    vnfc_obj.vdu_id = vdu_id
    if not pod_name:
        v1_pod = get_fake_pod_info(rsc_kind, rsc_name)
        pod_name = v1_pod.metadata.name
    compute_resource = objects.ResourceHandle(
        resource_id=pod_name,
        vim_level_resource_type=rsc_kind)
    vnfc_obj.compute_resource = compute_resource
    metadata = {}
    if namespace:
        metadata['Pod'] = _get_metadata_str(
            name=pod_name, namespace=namespace)
        if rsc_kind != 'Pod':
            metadata[rsc_kind] = _get_metadata_str(
                name=rsc_name, namespace=namespace)
    else:
        metadata['Pod'] = _get_metadata_str(name=pod_name)
        if rsc_kind != 'Pod':
            metadata[rsc_kind] = _get_metadata_str(name=rsc_name)
    vnfc_obj.metadata = metadata

    return vnfc_obj


def fake_vim_connection_info():
    access_info = {
        'auth_url': 'http://fake_url:6443',
        'ssl_ca_cert': None}

    return vim_connection.VimConnectionInfo(
        vim_type="kubernetes",
        access_info=access_info)


def fake_vim_connection_info_with_extra(del_field=None, multi_ip=False):
    access_info = {
        'auth_url': 'http://fake_url:6443',
        'ssl_ca_cert': None}
    masternode_ip = ["192.168.0.1"]
    if multi_ip:
        masternode_ip.append("192.168.0.2")

    helm_info = {
        'masternode_ip': masternode_ip,
        'masternode_username': 'dummy_user',
        'masternode_password': 'dummy_pass'
    }
    if del_field and helm_info.get(del_field):
        del helm_info[del_field]
    extra = {
        'helm_info': str(helm_info)
    }
    return vim_connection.VimConnectionInfo(
        vim_type="kubernetes",
        access_info=access_info,
        extra=extra)


def fake_inst_vnf_req_for_helmchart(external=True, local=True, namespace=None):
    additional_params = {"use_helm": "true"}
    using_helm_install_param = list()
    if external:
        using_helm_install_param.append(
            {
                "exthelmchart": "true",
                "helmreleasename": "myrelease-ext",
                "helmrepositoryname": "sample-charts",
                "helmchartname": "mychart-ext",
                "exthelmrepo_url": "http://helmrepo.example.com/sample-charts"
            }
        )
    if local:
        using_helm_install_param.append(
            {
                "exthelmchart": "false",
                "helmchartfile_path": "Files/kubernetes/localhelm-0.1.0.tgz",
                "helmreleasename": "myrelease-local",
                "helmparameter": [
                    "key1=value1",
                    "key2=value2"
                ]
            }
        )
    additional_params['using_helm_install_param'] = using_helm_install_param
    additional_params['helm_replica_values'] = {"vdu1_aspect": "replicaCount"}
    if namespace:
        additional_params['namespace'] = namespace

    return objects.InstantiateVnfRequest(
        flavour_id="simple", additional_params=additional_params)


def execute_cmd_helm_client(*args, **kwargs):
    ssh_command = args[0]
    if 'helm get manifest' in ssh_command:
        result = [
            '---\n',
            '# Source: localhelm/templates/deployment.yaml\n',
            'apiVersion: apps/v1\n',
            'kind: Deployment\n',
            'metadata:\n',
            '  name: vdu1\n',
            'spec:\n',
            '  replicas: 1\n',
            '  selector:\n',
            '    matchLabels:\n',
            '      app: webserver\n',
            '  template:\n',
            '    metadata:\n'
            '      labels:\n'
            '        app: webserver\n'
            '    spec:\n',
            '      containers:\n',
            '        - name: nginx\n'
        ]
    elif 'helm get values' in ssh_command:
        result = ['{"replicaCount":2}']
    else:
        result = ""
    return result


def fake_k8s_objs_deployment_for_helm():
    obj = [
        {
            'status': 'Creating',
            'object': fake_v1_deployment_for_helm()
        }
    ]

    return obj


def fake_v1_deployment_for_helm():
    return client.V1Deployment(
        api_version='apps/v1',
        kind='Deployment',
        metadata=client.V1ObjectMeta(
            name='vdu1',
        ),
        status=client.V1DeploymentStatus(
            replicas=1,
            ready_replicas=1
        ),
        spec=client.V1DeploymentSpec(
            replicas=1,
            selector=client.V1LabelSelector(
                match_labels={'app': 'webserver'}
            ),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(
                    labels={'app': 'webserver'}
                ),
                spec=client.V1PodSpec(
                    containers=[
                        client.V1Container(
                            name='nginx'
                        )
                    ]
                )
            )
        )
    )


def fake_k8s_vim_obj():
    vim_obj = {'vim_id': '76107920-e588-4865-8eca-f33a0f827071',
               'vim_name': 'fake_k8s_vim',
               'vim_auth': {
                   'auth_url': 'http://localhost:6443',
                   'password': 'test_pw',
                   'username': 'test_user',
                   'project_name': 'test_project'},
               'vim_type': 'kubernetes',
               'tenant': uuidsentinel.tenant_id,
               'extra': {}}
    return vim_obj
