# Copyright (C) 2023 FUJITSU
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


def get_fake_pod_info(pod_name, pod_status='Running'):
    return client.V1Pod(
        metadata=client.V1ObjectMeta(
            name=pod_name,
            creation_timestamp=datetime.datetime.now().isoformat('T')),
        status=client.V1PodStatus(phase=pod_status))


def fake_pod_env(
        res_name, name, image, conf_key, conf_name, sec_key, sec_name):
    return client.V1Pod(
        api_version='v1',
        kind='Pod',
        metadata=client.V1ObjectMeta(
            name=res_name
        ),
        spec=pod_template_spec(
            name, image, conf_key, conf_name, sec_key, sec_name,
            is_both=False).spec,
        status=client.V1PodStatus(
            phase='Running',
        )
    )


def fake_pod_vol(
        res_name, name, image, conf_name, sec_name):
    return client.V1Pod(
        api_version='v1',
        kind='Pod',
        metadata=client.V1ObjectMeta(
            name=res_name
        ),
        spec=client.V1PodSpec(
            containers=[
                client.V1Container(
                    image=image,
                    name=name,
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
                        name=conf_name
                    ),
                ),
                client.V1Volume(
                    name='sec-volume',
                    secret=client.V1SecretVolumeSource(
                        secret_name=sec_name
                    )
                )
            ]
        ),
        status=client.V1PodStatus(
            phase='Running',
        )
    )


def pod_template_spec(
        name, image, conf_key, conf_name, sec_key, sec_name, is_both=True,
        is_volumes=False):
    pod_template = client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(
            labels={'app': 'webserver'}
        ),
        spec=client.V1PodSpec(
            containers=[
                client.V1Container(
                    image=image,
                    name=name,
                    env=[
                        client.V1EnvVar(
                            name='CMENV',
                            value_from=client.V1EnvVarSource(
                                config_map_key_ref=(
                                    client.V1ConfigMapKeySelector(
                                        key=conf_key,
                                        name=conf_name
                                    )
                                )
                            )
                        ),
                        client.V1EnvVar(
                            name='SECENV',
                            value_from=client.V1EnvVarSource(
                                secret_key_ref=client.V1SecretKeySelector(
                                    key=sec_key,
                                    name=sec_name
                                )
                            )
                        )
                    ]
                )
            ]
        )
    )
    if not is_both:
        del pod_template.spec.containers[0].env[0]
    if is_volumes:
        pod_template.spec.containers[0].env = None
        pod_template.spec.containers[0].volume_mounts = [
            client.V1VolumeMount(
                name='sec-volume',
                mount_path='/etc/secrets'
            ),
        ]
        pod_template.spec.volumes = [
            client.V1Volume(
                name='sec-volume',
                secret=client.V1SecretVolumeSource(
                    secret_name=sec_name
                )
            )
        ]
    return pod_template


def fake_deployment(
        res_name, name, image, conf_key, conf_name, sec_key, sec_name):
    return client.V1Deployment(
        api_version='apps/v1',
        kind='Deployment',
        metadata=client.V1ObjectMeta(
            name=res_name,
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
            template=pod_template_spec(
                name, image, conf_key, conf_name, sec_key, sec_name)
        )
    )


def fake_daemon_set(
        res_name, name, image, conf_key, conf_name, sec_key, sec_name):
    return client.V1DaemonSet(
        api_version='apps/v1',
        kind='DaemonSet',
        metadata=client.V1ObjectMeta(
            name=res_name,
        ),
        status=client.V1DaemonSetStatus(
            number_ready=1,
            desired_number_scheduled=1,
            current_number_scheduled=1,
            number_misscheduled=1,
        ),
        spec=client.V1DaemonSetSpec(
            selector=client.V1LabelSelector(
                match_labels={'app': 'webserver'}
            ),
            template=pod_template_spec(
                name, image, conf_key, conf_name, sec_key, sec_name,
                is_volumes=True)
        )
    )


def fake_replica_set(
        res_name, name, image, conf_key, conf_name, sec_key, sec_name):
    return client.V1ReplicaSet(
        api_version='apps/v1',
        kind='ReplicaSet',
        metadata=client.V1ObjectMeta(
            name=res_name,
        ),
        status=client.V1ReplicaSetStatus(
            replicas=1,
            ready_replicas=1
        ),
        spec=client.V1ReplicaSetSpec(
            replicas=1,
            selector=client.V1LabelSelector(
                match_labels={'app': 'webserver'}
            ),
            template=pod_template_spec(
                name, image, conf_key, conf_name, sec_key, sec_name)
        )
    )
