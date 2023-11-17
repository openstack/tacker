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

import copy
from oslo_utils import uuidutils


def test_instantiate_cnf_resources_create(vnfd_id):
    # All attributes are set.
    # NOTE: All of the following cardinality attributes are set.
    # In addition, 0..N or 1..N attributes are set to 2 or more.
    #  - 0..1 (1)
    #  - 0..N (2 or more)
    #  - 1
    #  - 1..N (2 or more)
    return {
        "vnfdId": vnfd_id,
        "vnfInstanceName": "test_instantiate_cnf_resources",
        "vnfInstanceDescription": "test_instantiate_cnf_resources",
        "metadata": {"dummy-key": "dummy-val"}
    }


def test_instantiate_cnf_resources_terminate():
    # All attributes are set.
    # NOTE: All of the following cardinality attributes are set.
    # In addition, 0..N or 1..N attributes are set to 2 or more.
    #  - 0..1 (1)
    #  - 0..N (2 or more)
    #  - 1
    #  - 1..N (2 or more)
    return {
        "terminationType": "GRACEFUL",
        "gracefulTerminationTimeout": 5,
        "additionalParams": {"dummy-key": "dummy-val"}
    }


def max_sample_instantiate(auth_url, bearer_token, ssl_ca_cert=None):
    # All attributes are set.
    # NOTE: All of the following cardinality attributes are set.
    # In addition, 0..N or 1..N attributes are set to 2 or more.
    #  - 0..1 (1)
    #  - 0..N (2 or more)
    #  - 1
    #  - 1..N (2 or more)
    vim_id_1 = uuidutils.generate_uuid()
    vim_id_2 = uuidutils.generate_uuid()
    vim_1 = {
        "vimId": vim_id_1,
        "vimType": "ETSINFV.KUBERNETES.V_1",
        "interfaceInfo": {"endpoint": auth_url},
        "accessInfo": {
            "bearer_token": bearer_token,
        },
        "extra": {"dummy-key": "dummy-val"}
    }
    vim_2 = {
        "vimId": vim_id_2,
        "vimType": "ETSINFV.KUBERNETES.V_1",
        "interfaceInfo": {"endpoint": auth_url},
        "accessInfo": {
            "username": "dummy_user",
            "password": "dummy_password",
        },
        "extra": {"dummy-key": "dummy-val"}
    }
    if ssl_ca_cert:
        vim_1["interfaceInfo"]["ssl_ca_cert"] = ssl_ca_cert
        vim_2["interfaceInfo"]["ssl_ca_cert"] = ssl_ca_cert
    return {
        "flavourId": "simple",
        "vimConnectionInfo": {
            "vim1": vim_1,
            "vim2": vim_2
        },
        "additionalParams": {
            "lcm-kubernetes-def-files": [
                # "Files/kubernetes/bindings.yaml",
                "Files/kubernetes/clusterrole_clusterrolebinding_SA.yaml",
                "Files/kubernetes/config-map.yaml",
                "Files/kubernetes/controller-revision.yaml",
                "Files/kubernetes/daemon-set.yaml",
                "Files/kubernetes/deployment.yaml",
                "Files/kubernetes/horizontal-pod-autoscaler.yaml",
                "Files/kubernetes/job.yaml",
                "Files/kubernetes/limit-range.yaml",
                "Files/kubernetes/local-subject-access-review.yaml",
                "Files/kubernetes/multiple_yaml_lease.yaml",
                "Files/kubernetes/multiple_yaml_network-policy.yaml",
                "Files/kubernetes/multiple_yaml_priority-class.yaml",
                "Files/kubernetes/namespace.yaml",
                "Files/kubernetes/persistent-volume-0.yaml",
                "Files/kubernetes/persistent-volume-1.yaml",
                "Files/kubernetes/pod.yaml",
                "Files/kubernetes/pod-template.yaml",
                "Files/kubernetes/replicaset_service_secret.yaml",
                "Files/kubernetes/resource-quota.yaml",
                "Files/kubernetes/role_rolebinding_SA.yaml",
                "Files/kubernetes/self-subject-access-review_and"
                "_self-subject-rule-review.yaml",
                "Files/kubernetes/statefulset.yaml",
                "Files/kubernetes/storage-class.yaml",
                "Files/kubernetes/storage-class_pv_pvc.yaml",
                "Files/kubernetes/subject-access-review.yaml",
                "Files/kubernetes/token-review.yaml"
            ],
            "namespace": "default"
        }
    }


def max_sample_terminate():
    # All attributes are set.
    # NOTE: All of the following cardinality attributes are set.
    # In addition, 0..N or 1..N attributes are set to 2 or more.
    #  - 0..1 (1)
    #  - 0..N (2 or more)
    #  - 1
    #  - 1..N (2 or more)
    return {
        "terminationType": "GRACEFUL",
        "gracefulTerminationTimeout": 5,
        "additionalParams": {"dummy-key": "dummy-val"}
    }


def max_sample_scale_out():
    return {
        "type": "SCALE_OUT",
        "aspectId": "vdu3_aspect",
        "numberOfSteps": 2
    }


def max_sample_scale_in():
    return {
        "type": "SCALE_IN",
        "aspectId": "vdu3_aspect",
        "numberOfSteps": 1
    }


def scale_out():
    return {
        "type": "SCALE_OUT",
        "aspectId": "vdu2_aspect",
        "numberOfSteps": 1,
        "additionalParams": {"dummy-key": "dummy-value"}
    }


def max_sample_heal(vnfc_ids):
    return {
        "vnfcInstanceId": vnfc_ids
    }


def min_sample_instantiate(vim_id_1):
    vim_1 = {
        "vimId": vim_id_1,
        "vimType": "ETSINFV.KUBERNETES.V_1",
    }
    return {
        "flavourId": "simple",
        "vimConnectionInfo": {
            "vim1": vim_1,
        },
        "additionalParams": {
            "lcm-kubernetes-def-files": [
                "Files/kubernetes/pod.yaml"
            ]
        }
    }


def min_sample_instantiate_with_vim_info(k8s_vim_info):

    vim_1 = {
        "vimId": uuidutils.generate_uuid(),
        "vimType": "ETSINFV.KUBERNETES.V_1",
        "accessInfo": k8s_vim_info.accessInfo,
        "interfaceInfo": k8s_vim_info.interfaceInfo
    }
    return {
        "flavourId": "simple",
        "vimConnectionInfo": {
            "vim1": vim_1,
        },
        "additionalParams": {
            "lcm-kubernetes-def-files": [
                "Files/kubernetes/pod.yaml"
            ]
        }
    }


def min_sample_terminate():
    # Omit except for required attributes
    # NOTE: Only the following cardinality attributes are set.
    #  - 1
    #  - 1..N (1)
    return {
        "terminationType": "FORCEFUL"
    }


def error_handling_instantiate(auth_url, bearer_token):
    vim_id_1 = uuidutils.generate_uuid()
    vim_1 = {
        "vimId": vim_id_1,
        "vimType": "ETSINFV.KUBERNETES.V_1",
        "interfaceInfo": {"endpoint": auth_url},
        "accessInfo": {
            "bearer_token": bearer_token,
        },
        "extra": {"dummy-key": "dummy-val"}
    }

    return {
        "flavourId": "simple",
        "vimConnectionInfo": {
            "vim1": vim_1
        },
        "additionalParams": {
            "lcm-kubernetes-def-files": [
                "Files/kubernetes/deployment.yaml"
            ]
        }
    }


def error_handling_scale_out():
    return {
        "type": "SCALE_OUT",
        "aspectId": "vdu2_aspect",
        "numberOfSteps": 1
    }


def error_handling_terminate():
    return {
        "terminationType": "FORCEFUL"
    }


def change_vnfpkg_instantiate(auth_url, bearer_token):
    vim_id_1 = uuidutils.generate_uuid()
    vim_1 = {
        "vimId": vim_id_1,
        "vimType": "ETSINFV.KUBERNETES.V_1",
        "interfaceInfo": {"endpoint": auth_url},
        "accessInfo": {
            "bearer_token": bearer_token,
        },
        "extra": {"dummy-key": "dummy-val"}
    }

    return {
        "flavourId": "simple",
        "vimConnectionInfo": {
            "vim1": vim_1
        },
        "additionalParams": {
            "lcm-kubernetes-def-files": [
                "Files/kubernetes/namespace.yaml",
                "Files/kubernetes/deployment.yaml"
            ],
            "namespace": "curry"
        }
    }


def change_vnfpkg(vnfd_id):
    return {
        "vnfdId": vnfd_id,
        "additionalParams": {
            "upgrade_type": "RollingUpdate",
            "lcm-kubernetes-def-files": [
                "Files/kubernetes/namespace.yaml",
                "Files/new_kubernetes/new_deployment.yaml"],
            "vdu_params": [{
                "vdu_id": "VDU2"
            }]
        }
    }


def change_vnfpkg_error(vnfd_id):
    return {
        "vnfdId": vnfd_id,
        "additionalParams": {
            "upgrade_type": "RollingUpdate",
            "lcm-kubernetes-def-files": [
                "Files/kubernetes/namespace.yaml",
                "Files/new_kubernetes/not_exist_deployment.yaml"],
            "vdu_params": [{
                "vdu_id": "VDU2"
            }]
        }
    }


def change_vnfpkg_terminate():
    return {
        "terminationType": "FORCEFUL"
    }


def test_helm_instantiate_create(vnfd_id):
    return {
        "vnfdId": vnfd_id,
        "vnfInstanceName": "test_helm_instantiate",
        "vnfInstanceDescription": "test_helm_instantiate",
        "metadata": {"dummy-key": "dummy-val"}
    }


def helm_instantiate(auth_url=None, bearer_token=None, ssl_ca_cert=None,
                     vim_id=None):
    if not vim_id:
        vim_1 = {
            "vimId": uuidutils.generate_uuid(),
            "vimType": "ETSINFV.HELM.V_3",
            "interfaceInfo": {
                "endpoint": auth_url,
                "ssl_ca_cert": ssl_ca_cert
            },
            "accessInfo": {
                "bearer_token": bearer_token
            }
        }
    else:
        vim_1 = {
            "vimId": vim_id,
            "vimType": "ETSINFV.HELM.V_3",
        }
    return {
        "flavourId": "simple",
        "vimConnectionInfo": {
            "vim1": vim_1,
        },
        "additionalParams": {
            "helm_chart_path": "Files/kubernetes/test-chart-0.1.0.tgz",
            "helm_parameters": {
                "service.port": 8081,
                "service.type": "NodePort"
            },
            "helm_value_names": {
                "VDU1": {
                    "replica": "replicaCountVdu1"
                },
                "VDU2": {
                    "replica": "replicaCountVdu2"
                }
            },
            "namespace": "default"
        }
    }


def helm_terminate():
    return {
        "terminationType": "FORCEFUL"
    }


def helm_scale_out():
    return {
        "type": "SCALE_OUT",
        "aspectId": "vdu2_aspect",
        "numberOfSteps": 2
    }


def helm_scale_in():
    return {
        "type": "SCALE_IN",
        "aspectId": "vdu2_aspect",
        "numberOfSteps": 1
    }


def helm_heal(vnfc_ids):
    return {
        "vnfcInstanceId": vnfc_ids
    }


def helm_change_vnfpkg(vnfd_id):
    return {
        "vnfdId": vnfd_id,
        "additionalParams": {
            "upgrade_type": "RollingUpdate",
            "helm_chart_path": "Files/kubernetes/test-chart-0.1.1.tgz",
            "vdu_params": [{
                "vdu_id": "VDU2"
            }]
        }
    }


def helm_error_handling_change_vnfpkg(vnfd_id):
    return {
        "vnfdId": vnfd_id,
        "additionalParams": {
            "upgrade_type": "RollingUpdate",
            "helm_chart_path": "Files/kubernetes/test-chart-error-"
            "handling.tgz",
            "vdu_params": [{
                "vdu_id": "VDU2"
            }]
        }
    }


def instantiate_cnf_resources_create(vnfd_id):
    return {
        "vnfdId": vnfd_id,
        "vnfInstanceName": "test",
        "vnfInstanceDescription": "test",
        "metadata": {"dummy-key": "dummy-val"}
    }


def pm_instantiate_cnf_resources_create(vnfd_id):
    return {
        "vnfdId": vnfd_id,
        "vnfInstanceName": "test",
        "vnfInstanceDescription": "test"
    }


def instantiate_vnf_min():
    # Omit except for required attributes
    # NOTE: Only the following cardinality attributes are set.
    #  - 1
    #  - 1..N (1)
    return {
        "flavourId": "simple"
    }


def sub_create_min(callback_uri):
    # Omit except for required attributes
    # NOTE: Only the following cardinality attributes are set.
    #  - 1
    #  - 1..N (1)
    return {
        "callbackUri": callback_uri
    }


def sub_create_max(callback_uri, vnfd_id, inst_id):
    return {
        "filter": {
            "vnfInstanceSubscriptionFilter": {
                "vnfdIds": [vnfd_id],
                "vnfProductsFromProviders": [
                    {
                        "vnfProvider": "Company",
                        "vnfProducts": [
                            {
                                "vnfProductName": "Sample VNF",
                                "versions": [
                                    {
                                        "vnfSoftwareVersion": "1.0",
                                        "vnfdVersions": ["1.0"]
                                    }
                                ]
                            }
                        ]
                    },
                ],
                "vnfInstanceIds": [inst_id],
                "vnfInstanceNames": ["test"],
            },
            "notificationTypes": ["AlarmNotification",
                                  "AlarmClearedNotification"],
            "faultyResourceTypes": ["COMPUTE"],
            "perceivedSeverities": ["WARNING"],
            "eventTypes": ["PROCESSING_ERROR_ALARM"],
            "probableCauses": ["Process Terminated"]
        },
        "callbackUri": callback_uri
    }


def alert_event_firing(inst_id, pod_name):
    return {
        "receiver": "receiver",
        "status": "firing",
        "alerts": [
            {
                "status": "firing",
                "labels": {
                    "receiver_type": "tacker",
                    "function_type": "vnffm",
                    "vnf_instance_id": inst_id,
                    "pod": pod_name,
                    "perceived_severity": "WARNING",
                    "event_type": "PROCESSING_ERROR_ALARM"
                },
                "annotations": {
                    "fault_type": "Server Down",
                    "probable_cause": "Process Terminated",
                    "fault_details": "pid 12345"
                },
                "startsAt": "2022-06-21T23:47:36.453Z",
                "endsAt": "0001-01-01T00:00:00Z",
                "generatorURL": "http://controller147:9090/graph?g0.expr="
                                "up%7Bjob%3D%22node%22%7D+%3D%3D+0&g0.tab=1",
                "fingerprint": "5ef77f1f8a3ecb8d"
            }
        ],
        "groupLabels": {},
        "commonLabels": {
            "alertname": "NodeInstanceDown",
            "job": "node"
        },
        "commonAnnotations": {
            "description": "sample"
        },
        "externalURL": "http://controller147:9093",
        "version": "4",
        "groupKey": "{}:{}",
        "truncatedAlerts": 0
    }


def alert_event_resolved(inst_id, pod_name):
    return {
        "receiver": "receiver",
        "status": "resolved",
        "alerts": [
            {
                "status": "resolved",
                "labels": {
                    "receiver_type": "tacker",
                    "function_type": "vnffm",
                    "vnf_instance_id": inst_id,
                    "pod": pod_name,
                    "perceived_severity": "WARNING",
                    "event_type": "PROCESSING_ERROR_ALARM"
                },
                "annotations": {
                    "fault_type": "Server Down",
                    "probable_cause": "Process Terminated",
                    "fault_details": "pid 12345"
                },
                "startsAt": "2022-06-21T23:47:36.453Z",
                "endsAt": "2022-06-22T23:47:36.453Z",
                "generatorURL": "http://controller147:9090/graph?g0.expr=up%7B"
                                "job%3D%22node%22%7D+%3D%3D+0&g0.tab=1",
                "fingerprint": "5ef77f1f8a3ecb8d"
            }
        ],
        "groupLabels": {},
        "commonLabels": {
            "alertname": "NodeInstanceDown",
            "job": "node"
        },
        "commonAnnotations": {
            "description": "sample"
        },
        "externalURL": "http://controller147:9093",
        "version": "4",
        "groupKey": "{}:{}",
        "truncatedAlerts": 0
    }


def update_alarm_acknowledged():
    return {
        "ackState": "ACKNOWLEDGED"
    }


def update_alarm_unacknowledged():
    return {
        "ackState": "UNACKNOWLEDGED"
    }


def terminate_vnf_min():
    # Omit except for required attributes
    # NOTE: Only the following cardinality attributes are set.
    #  - 1
    #  - 1..N (1)
    return {
        "terminationType": "FORCEFUL"
    }


def pm_job_external(callback_uri, inst_id, host_ip, rsc_id):
    def pm_job(
            callback_uri, inst_id, host_ip,
            object_type, performance_metric,
            sub_object_instance_id=None):
        job = {
            "objectType": object_type,
            "objectInstanceIds": [inst_id],
            "subObjectInstanceIds": ([sub_object_instance_id]
                                     if sub_object_instance_id else []),
            "criteria": {
                "performanceMetric": [performance_metric],
                "performanceMetricGroup": [],
                "collectionPeriod": 30,
                "reportingPeriod": 90
            },
            "callbackUri": callback_uri,
            "metadata": {
                "monitoring": {
                    "monitorName": "prometheus",
                    "driverType": "external",
                    "targetsInfo": [
                        {
                            "prometheusHost": host_ip,
                            "prometheusHostPort": 50022,
                            "authInfo": {
                                "ssh_username": "root",
                                "ssh_password": "root"
                            },
                            "alertRuleConfigPath":
                                "/tmp",
                            "prometheusReloadApiEndpoint":
                                "http://localhost:9990/-/reload",
                        }
                    ]
                }
            }
        }
        return copy.deepcopy(job)
    return [
        pm_job(callback_uri, inst_id, host_ip, "Vnf",
               f"VCpuUsageMeanVnf.{inst_id}"),
        pm_job(callback_uri, inst_id, host_ip, "Vnf",
               f"VCpuUsagePeakVnf.{inst_id}"),
        pm_job(callback_uri, inst_id, host_ip, "Vnf",
               f"VMemoryUsageMeanVnf.{inst_id}"),
        pm_job(callback_uri, inst_id, host_ip, "Vnf",
               f"VMemoryUsagePeakVnf.{inst_id}"),
        pm_job(callback_uri, inst_id, host_ip, "Vnf",
               f"VDiskUsageMeanVnf.{inst_id}"),
        pm_job(callback_uri, inst_id, host_ip, "Vnf",
               f"VDiskUsagePeakVnf.{inst_id}"),
        pm_job(callback_uri, inst_id, host_ip, "Vnfc",
               f"VCpuUsageMeanVnf.{inst_id}",
               sub_object_instance_id=rsc_id),
        pm_job(callback_uri, inst_id, host_ip, "Vnfc",
               f"VCpuUsagePeakVnf.{inst_id}",
               sub_object_instance_id=rsc_id),
        pm_job(callback_uri, inst_id, host_ip, "Vnfc",
               f"VMemoryUsageMeanVnf.{inst_id}",
               sub_object_instance_id=rsc_id),
        pm_job(callback_uri, inst_id, host_ip, "Vnfc",
               f"VMemoryUsagePeakVnf.{inst_id}",
               sub_object_instance_id=rsc_id),
        pm_job(callback_uri, inst_id, host_ip, "Vnfc",
               f"VDiskUsageMeanVnf.{inst_id}",
               sub_object_instance_id=rsc_id),
        pm_job(callback_uri, inst_id, host_ip, "Vnfc",
               f"VDiskUsagePeakVnf.{inst_id}",
               sub_object_instance_id=rsc_id),
        pm_job(callback_uri, inst_id, host_ip, "VnfIntCp",
               "ByteIncomingVnfIntCp", sub_object_instance_id="eth0"),
        pm_job(callback_uri, inst_id, host_ip, "VnfIntCp",
               "PacketIncomingVnfIntCp", sub_object_instance_id="eth0"),
        pm_job(callback_uri, inst_id, host_ip, "VnfIntCp",
               "ByteOutgoingVnfIntCp", sub_object_instance_id="eth0"),
        pm_job(callback_uri, inst_id, host_ip, "VnfIntCp",
               "PacketOutgoingVnfIntCp", sub_object_instance_id="eth0"),
        pm_job(callback_uri, inst_id, host_ip, "VnfExtCp",
               "ByteIncomingVnfExtCp", sub_object_instance_id="eth1"),
        pm_job(callback_uri, inst_id, host_ip, "VnfExtCp",
               "PacketIncomingVnfExtCp", sub_object_instance_id="eth1"),
        pm_job(callback_uri, inst_id, host_ip, "VnfExtCp",
               "ByteOutgoingVnfExtCp", sub_object_instance_id="eth1"),
        pm_job(callback_uri, inst_id, host_ip, "VnfExtCp",
               "PacketOutgoingVnfExtCp", sub_object_instance_id="eth1")
    ]


def pm_job_min(callback_uri, inst_id, host_ip):
    return {
        "objectType": "Vnf",
        "objectInstanceIds": [inst_id],
        "criteria": {
            "performanceMetric": [
                f"VCpuUsageMeanVnf.{inst_id}"],
            "collectionPeriod": 5,
            "reportingPeriod": 10
        },
        "callbackUri": callback_uri,
        "metadata": {
            "monitoring": {
                "monitorName": "prometheus",
                "driverType": "external",
                "targetsInfo": [
                    {
                        "prometheusHost": host_ip,
                        "prometheusHostPort": 50022,
                        "authInfo": {
                            "ssh_username": "root",
                            "ssh_password": "root"
                        },
                        "alertRuleConfigPath":
                            "/tmp",
                        "prometheusReloadApiEndpoint":
                            "http://localhost:9990/-/reload",
                    }
                ]
            }
        }

    }


def pm_job_max(callback_uri, inst_id, host_ip):
    return {
        "objectType": "Vnf",
        "objectInstanceIds": [inst_id],
        "subObjectInstanceIds": [],
        "criteria": {
            "performanceMetric": [
                f"VCpuUsageMeanVnf.{inst_id}"],
            "performanceMetricGroup": ["VirtualisedComputeResource"],
            "collectionPeriod": 5,
            "reportingPeriod": 10,
            "reportingBoundary": "2099-08-05T02:24:46Z"
        },
        "callbackUri": callback_uri,
        "metadata": {
            "monitoring": {
                "monitorName": "prometheus",
                "driverType": "external",
                "targetsInfo": [
                    {
                        "prometheusHost": host_ip,
                        "prometheusHostPort": 50022,
                        "authInfo": {
                            "ssh_username": "root",
                            "ssh_password": "root"
                        },
                        "alertRuleConfigPath":
                            "/tmp",
                        "prometheusReloadApiEndpoint":
                            "http://localhost:9990/-/reload"
                    }
                ]
            }
        }
    }


def update_pm_job(callback_uri):
    return {
        "callbackUri": callback_uri
    }


def pm_threshold_min(
        callback_uri, inst_id, host_ip,
        objectType="Vnf",
        sub_object_instance_id=None,
        p_metric=None,
        thresholdValue=55,
        hysteresis=30):
    metric = f"VCpuUsageMeanVnf.{inst_id}"
    if p_metric:
        metric = f"{p_metric}"
    return {
        "objectType": objectType,
        "objectInstanceId": inst_id,
        "subObjectInstanceIds": ([sub_object_instance_id]
                                 if sub_object_instance_id else []),
        "criteria": {
            "performanceMetric": metric,
            "thresholdType": "SIMPLE",
            "simpleThresholdDetails": {
                "thresholdValue": thresholdValue,
                "hysteresis": hysteresis
            }
        },
        "callbackUri": callback_uri,
        "metadata": {
            "monitoring": {
                "monitorName": "prometheus",
                "driverType": "external",
                "targetsInfo": [
                    {
                        "prometheusHost": host_ip,
                        "prometheusHostPort": 50022,
                        "authInfo": {
                            "ssh_username": "root",
                            "ssh_password": "root"
                        },
                        "alertRuleConfigPath":
                            "/tmp",
                        "prometheusReloadApiEndpoint":
                            "http://localhost:9990/-/reload"
                    }
                ]
            }
        }
    }


def pm_threshold_max(
        callback_uri, inst_id, host_ip,
        objectType="Vnf",
        sub_object_instance_id=None,
        p_metric=None,
        thresholdValue=55,
        hysteresis=30):
    metric = f"VCpuUsageMeanVnf.{inst_id}"
    if p_metric:
        metric = f"{p_metric}"
    return {
        "objectType": objectType,
        "objectInstanceId": inst_id,
        "subObjectInstanceIds": ([sub_object_instance_id]
                                 if sub_object_instance_id else []),
        "criteria": {
            "performanceMetric": metric,
            "thresholdType": "SIMPLE",
            "simpleThresholdDetails": {
                "thresholdValue": thresholdValue,
                "hysteresis": hysteresis
            }
        },
        "callbackUri": callback_uri,
        "authentication": {
            "authType": ["BASIC"],
            "paramsBasic": {
                "userName": "test",
                "password": "test"
            }
        },
        "metadata": {
            "monitoring": {
                "monitorName": "prometheus",
                "driverType": "external",
                "targetsInfo": [
                    {
                        "prometheusHost": host_ip,
                        "prometheusHostPort": 50022,
                        "authInfo": {
                            "ssh_username": "root",
                            "ssh_password": "root"
                        },
                        "alertRuleConfigPath":
                            "/tmp",
                        "prometheusReloadApiEndpoint":
                            "http://localhost:9990/-/reload"
                    }
                ]
            }
        }
    }


def update_pm_threshold(callback_uri):
    return {
        "callbackUri": callback_uri
    }


def pm_event(job_id, inst_id):
    return {
        "receiver": "receiver",
        "status": "firing",
        "alerts": [
            {
                "status": "firing",
                "labels": {
                    "receiver_type": "tacker",
                    "function_type": "vnfpm",
                    "job_id": job_id,
                    "metric": f"VCpuUsageMeanVnf.{inst_id}",
                    "object_instance_id": inst_id
                },
                "annotations": {
                    "value": 99,
                },
                "startsAt": "2022-06-21T23:47:36.453Z",
                "endsAt": "0001-01-01T00:00:00Z",
                "generatorURL": "http://controller147:9090/graph?g0.expr=up%7B"
                                "job%3D%22node%22%7D+%3D%3D+0&g0.tab=1",
                "fingerprint": "5ef77f1f8a3ecb8d"
            }
        ],
        "groupLabels": {},
        "commonLabels": {
            "alertname": "NodeInstanceDown",
            "job": "node"
        },
        "commonAnnotations": {
            "description": "sample"
        },
        "externalURL": "http://controller147:9093",
        "version": "4",
        "groupKey": "{}:{}",
        "truncatedAlerts": 0
    }


def pm_threshold(threshold_id, inst_id,
                 sub_inst_id=None, value=99, p_metric=None):
    metric = f"VCpuUsageMeanVnf.{inst_id}"
    if p_metric:
        metric = f"{p_metric}"
    # This data simulates the complete request body sent by alertmanager.
    return {
        "receiver": "receiver",
        "status": "firing",
        "alerts": [
            {
                "status": "firing",
                "labels": {
                    "receiver_type": "tacker",
                    "function_type": "vnfpm_threshold",
                    "threshold_id": threshold_id,
                    "metric": metric,
                    "object_instance_id": inst_id,
                    "sub_object_instance_id": sub_inst_id
                },
                "annotations": {
                    "value": value,
                },
                "startsAt": "2022-12-15T23:47:36.453Z",
                "endsAt": "0001-01-01T00:00:00Z",
                "generatorURL": "http://controller147:9090/graph?g0.expr=up%7B"
                                "job%3D%22node%22%7D+%3D%3D+0&g0.tab=1",
                "fingerprint": "5ef77f1f8a3ecb8d"
            }
        ],
        "groupLabels": {},
        "commonLabels": {
            "alertname": "NodeInstanceDown",
            "job": "node"
        },
        "commonAnnotations": {
            "description": "sample"
        },
        "externalURL": "http://controller147:9093",
        "version": "4",
        "groupKey": "{}:{}",
        "truncatedAlerts": 0
    }


def prometheus_auto_scaling_alert(inst_id):
    return {
        "receiver": "receiver",
        "status": "firing",
        "alerts": [{
            "status": "firing",
            "labels": {
                "receiver_type": "tacker",
                "function_type": "auto_scale",
                "vnf_instance_id": inst_id,
                "auto_scale_type": "SCALE_OUT",
                "aspect_id": "vdu2_aspect"
            },
            "annotations": {
            },
            "startsAt": "2022-06-21T23:47:36.453Z",
            "endsAt": "0001-01-01T00:00:00Z",
            "generatorURL": "http://controller147:9090/graph?g0.expr="
                            "up%7Bjob%3D%22node%22%7D+%3D%3D+0&g0.tab=1",
            "fingerprint": "5ef77f1f8a3ecb8d"
        }],
        "groupLabels": {},
        "commonLabels": {
            "alertname": "NodeInstanceDown",
            "job": "node"
        },
        "commonAnnotations": {
            "description": "sample"
        },
        "externalURL": "http://controller147:9093",
        "version": "4",
        "groupKey": "{}:{}",
        "truncatedAlerts": 0
    }


def prometheus_auto_healing_alert(inst_id, vnfc_info_id):
    return {
        "receiver": "receiver",
        "status": "firing",
        "alerts": [{
            "status": "firing",
            "labels": {
                "receiver_type": "tacker",
                "function_type": "auto_heal",
                "vnf_instance_id": inst_id,
                "vnfc_info_id": vnfc_info_id
            },
            "annotations": {
            },
            "startsAt": "2022-06-21T23:47:36.453Z",
            "endsAt": "0001-01-01T00:00:00Z",
            "generatorURL": "http://controller147:9090/graph?g0.expr="
                            "up%7Bjob%3D%22node%22%7D+%3D%3D+0&g0.tab=1",
            "fingerprint": "5ef77f1f8a3ecb8d"
        }],
        "groupLabels": {},
        "commonLabels": {
            "alertname": "NodeInstanceDown",
            "job": "node"
        },
        "commonAnnotations": {
            "description": "sample"
        },
        "externalURL": "http://controller147:9093",
        "version": "4",
        "groupKey": "{}:{}",
        "truncatedAlerts": 0
    }


def test_cnf_update_create(vnfd_id):
    return {
        "vnfdId": vnfd_id,
        "vnfInstanceName": "container_update_multi_kinds",
        "vnfInstanceDescription": "container update multi kinds"
    }


def test_cnf_update_instantiate(vim_id):
    return {
        "flavourId": "simple",
        "vimConnectionInfo": {
            "vim1": {
                "vimId": vim_id,
                "vimType": "ETSINFV.KUBERNETES.V_1"
            }
        },
        "additionalParams": {
            "lcm-kubernetes-def-files": [
                "Files/kubernetes/configmap_1.yaml",
                "Files/kubernetes/deployment.yaml",
                "Files/kubernetes/pod_env.yaml",
                "Files/kubernetes/pod_volume.yaml",
                "Files/kubernetes/replicaset.yaml",
                "Files/kubernetes/secret_1.yaml",
                "Files/kubernetes/configmap_3.yaml",
                "Files/kubernetes/pod_env_2.yaml",
                "Files/kubernetes/pod_volume_2.yaml",
                "Files/kubernetes/daemonset.yaml",
                "Files/kubernetes/deployment_2.yaml",
                "Files/kubernetes/secret_3.yaml"
            ]
        }
    }


def test_cnf_update_modify(vnfd_id):
    return {
        "vnfdId": vnfd_id,
        "vnfInstanceName": "modify_vnf_after",
        "metadata": {
            "configmap_secret_paths": [
                "Files/kubernetes/configmap_2.yaml",
                "Files/kubernetes/secret_2.yaml"
            ]
        }
    }
