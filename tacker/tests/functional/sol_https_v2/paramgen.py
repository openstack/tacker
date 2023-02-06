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

import datetime
from oslo_utils import uuidutils

from tacker.sol_refactored import objects


def sub_create_https_no_auth(callback_uri):
    return {
        "callbackUri": callback_uri
    }


def sub_create_https_basic_auth(callback_uri):
    return {
        "callbackUri": callback_uri,
        "authentication": {
            "authType": [
                "BASIC"
            ],
            "paramsBasic": {
                "userName": "admin-user",
                "password": "devstack"
            }
        }
    }


def sub_create_https_oauth2_auth(callback_uri):
    return {
        "callbackUri": callback_uri,
        "authentication": {
            "authType": [
                "OAUTH2_CLIENT_CREDENTIALS"
            ],
            "paramsOauth2ClientCredentials": {
                "clientId": "229ec984de7547b2b662e968961af5a4",
                "clientPassword": "devstack",
                "tokenEndpoint": "https://localhost:9990/token"
            }
        }
    }


def create_vnf_min(vnfd_id):
    # Omit except for required attributes
    # NOTE: Only the following cardinality attributes are set.
    #  - 1
    #  - 1..N (1)
    return {
        "vnfdId": vnfd_id
    }


def terminate_vnf_min():
    # Omit except for required attributes
    # NOTE: Only the following cardinality attributes are set.
    #  - 1
    #  - 1..N (1)
    return {
        "terminationType": "FORCEFUL"
    }


def instantiate_vnf_min():
    # Omit except for required attributes
    # NOTE: Only the following cardinality attributes are set.
    #  - 1
    #  - 1..N (1)
    return {
        "flavourId": "simple"
    }


def alert_event_firing(inst_id):
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
                "generatorURL": "https://controller147:9090/graph?g0.expr="
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
        "externalURL": "https://controller147:9093",
        "version": "4",
        "groupKey": "{}:{}",
        "truncatedAlerts": 0
    }


def pm_job_https_no_auth(callback_uri, inst_id, host_ip):
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
                            "https://localhost:9990/-/reload",
                    }
                ]
            }
        }
    }


def pm_job_https_basic_auth(callback_uri, inst_id, host_ip):
    return {
        "objectType": "Vnf",
        "objectInstanceIds": [inst_id],
        "criteria": {
            "performanceMetric": [
                f"VCpuUsageMeanVnf.{inst_id}"],
            "collectionPeriod": 5,
            "reportingPeriod": 10,
        },
        "callbackUri": callback_uri,
        "authentication": {
            "authType": [
                "BASIC"
            ],
            "paramsBasic": {
                "userName": "admin-user",
                "password": "devstack"
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
                            "https://localhost:9990/-/reload",
                    }
                ]
            }
        }
    }


def pm_job_https_oauth2_auth(
        callback_uri, inst_id, host_ip):
    return {
        "objectType": "Vnf",
        "objectInstanceIds": [inst_id],
        "criteria": {
            "performanceMetric": [f"VCpuUsageMeanVnf.{inst_id}"],
            "collectionPeriod": 5,
            "reportingPeriod": 10,
        },
        "callbackUri": callback_uri,
        "authentication": {
            "authType": [
                "OAUTH2_CLIENT_CREDENTIALS"
            ],
            "paramsOauth2ClientCredentials": {
                "clientId": "229ec984de7547b2b662e968961af5a4",
                "clientPassword": "devstack",
                "tokenEndpoint": "https://localhost:9990/token"
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
                            "https://localhost:9990/-/reload",
                    }
                ]
            }
        }
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


def entries(body, inst_id):
    return {
        'id': uuidutils.generate_uuid(),
        'jobId': body.get("id"),
        'entries': [{
            'objectType': body.get("objectType"),
            'objectInstanceId': inst_id,
            'performanceMetric': f"VCpuUsageMeanVnf.{inst_id}",
            'performanceValues': [{
                'timeStamp': datetime.datetime.now(datetime.timezone.utc),
                'value': 0.8
            }]
        }],
    }


def alarm(inst_id):
    test_time = datetime.datetime.now(datetime.timezone.utc).isoformat()
    return objects.AlarmV1.from_dict({
        'id': uuidutils.generate_uuid(),
        'managedObjectId': inst_id,
        'vnfcInstanceIds': [],
        'alarmRaisedTime': test_time,
        'ackState': 'UNACKNOWLEDGED',
        'perceivedSeverity': "WARNING",
        'eventTime': test_time,
        'eventType': 'COMMUNICATIONS_ALARM',
        'faultType': '',
        'probableCause': '',
        'isRootCause': False,
        'faultDetails': '',
        '_links': {}
    })
