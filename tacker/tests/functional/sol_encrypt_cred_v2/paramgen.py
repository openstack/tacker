# Copyright (C) 2023 Fujitsu
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
from oslo_utils import uuidutils


def create_vnf_min(vnfd_id):
    return {
        "vnfdId": vnfd_id
    }


def update_vnf(auth_url, password):
    # Normally, password, client_secret, and bearer_token are not
    # specified at the same time, but this time they are all included for
    # the DB registration test.
    vim_1 = {
        "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_3",
        "interfaceInfo": {"endpoint": auth_url},
        "accessInfo": {
            "username": "nfv_user",
            "region": "RegionOne",
            "password": password,
            "project": "nfv",
            "projectDomain": "Default",
            "userDomain": "Default",
            "client_secret": password,
            "bearer_token": password
        },
    }
    return {
        "vnfInstanceName": "new name",
        "vimConnectionInfo": {
            "vim1": vim_1
        }
    }


def terminate_vnf_min():
    return {
        "terminationType": "GRACEFUL",
        "gracefulTerminationTimeout": 5,
        "additionalParams": {"dummy-key": "dummy-val"}
    }


def instantiate_vnf(auth_url, password):
    # Normally, password, client_secret, and bearer_token are not
    # specified at the same time, but this time they are all included for
    # the DB registration test.
    vim_id_1 = uuidutils.generate_uuid()
    vim_1 = {
        "vimId": vim_id_1,
        "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_3",
        "interfaceInfo": {"endpoint": auth_url},
        "accessInfo": {
            "username": "nfv_user",
            "region": "RegionOne",
            "password": password,
            "project": "nfv",
            "projectDomain": "Default",
            "userDomain": "Default",
            "client_secret": password,
            "bearer_token": password
        },
        "extra": {"dummy-key": "dummy-val"}
    }
    return {
        "flavourId": "simple",
        "vimConnectionInfo": {
            "vim1": vim_1
        }
    }


def sub_create_basic(callback_uri, password):
    return {
        "callbackUri": callback_uri,
        "authentication": {
            "authType": [
                "BASIC"
            ],
            "paramsBasic": {
                "password": password,
                "userName": "test_user"
            }
        }
    }


def sub_create_oauth2(callback_uri, password):
    return {
        "callbackUri": callback_uri,
        "authentication": {
            "authType": [
                "OAUTH2_CLIENT_CREDENTIALS"
            ],
            "paramsOauth2ClientCredentials": {
                "clientId": "229ec984de7547b2b662e968961af5a4",
                "clientPassword": password,
                "tokenEndpoint": "https://localhost:9990/token"
            }
        }
    }


def change_vnfpkg(vnfd_id, password):
    return {
        "vnfdId": vnfd_id,
        "additionalParams": {
            "upgrade_type": "RollingUpdate",
            "vdu_params": [{
                "vdu_id": "VDU1",
                "old_vnfc_param": {
                    "cp_name": "VDU1_CP1",
                    "username": "ubuntu",
                    "password": password,
                    "authentication": {
                        "authType": [
                            "BASIC",
                            "OAUTH2_CLIENT_CREDENTIALS"
                        ],
                        "paramsBasic": {
                            "userName": "test",
                            "password": password
                        },
                        "paramsOauth2ClientCredentials": {
                            "clientId": "229ec984de7547b2b662e968961af5a4",
                            "clientPassword": password,
                            "tokenEndpoint": "https://localhost:9990/token"
                        }
                    }
                },
                "new_vnfc_param": {
                    "cp_name": "VDU1_CP1",
                    "username": "ubuntu",
                    "password": password,
                    "authentication": {
                        "authType": [
                            "BASIC",
                            "OAUTH2_CLIENT_CREDENTIALS"
                        ],
                        "paramsBasic": {
                            "userName": "test",
                            "password": password
                        },
                        "paramsOauth2ClientCredentials": {
                            "clientId": "229ec984de7547b2b662e968961af5a4",
                            "clientPassword": password,
                            "tokenEndpoint": "https://localhost:9990/token"
                        }
                    }
                }
            }]
        }
    }


def pm_job_basic(callback_uri, inst_id, host_ip, password):
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
        "authentication": {
            "authType": ["BASIC"],
            "paramsBasic": {
                "userName": "test",
                "password": password
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
                            "ssh_password": password
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


def pm_job_oauth2(callback_uri, inst_id, host_ip, password):
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
        "authentication": {
            "authType": ["OAUTH2_CLIENT_CREDENTIALS"],
            "paramsOauth2ClientCredentials": {
                "clientId": "229ec984de7547b2b662e968961af5a4",
                "clientPassword": password,
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
                            "ssh_password": password
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


def pm_threshold_basic(
        callback_uri, inst_id, host_ip, password,
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
                "password": password
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
                            "ssh_password": password
                        },
                        "alertRuleConfigPath":
                            "/tmp",
                        "prometheusReloadApiEndpoint":
                            "https://localhost:9990/-/reload"
                    }
                ]
            }
        }
    }


def pm_threshold_oauth2(
        callback_uri, inst_id, host_ip, password,
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
            "authType": ["OAUTH2_CLIENT_CREDENTIALS"],
            "paramsOauth2ClientCredentials": {
                "clientId": "229ec984de7547b2b662e968961af5a4",
                "clientPassword": password,
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
                            "ssh_password": password
                        },
                        "alertRuleConfigPath":
                            "/tmp",
                        "prometheusReloadApiEndpoint":
                            "https://localhost:9990/-/reload"
                    }
                ]
            }
        }
    }
