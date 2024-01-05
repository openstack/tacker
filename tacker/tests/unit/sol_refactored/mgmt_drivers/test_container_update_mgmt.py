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
import copy
import os
import pickle
import sys
import urllib.request as urllib2

from kubernetes import client
from oslo_config import cfg

from tacker.common import exceptions
from tacker.sol_refactored.common import vnfd_utils
from tacker.sol_refactored.mgmt_drivers import (
    container_update_mgmt_v2 as mgmt_driver)
from tacker.tests.unit import base
from tacker.tests.unit.sol_refactored.mgmt_drivers import fakes
from tacker.tests import utils
from unittest import mock

SAMPLE_OLD_VNFD_ID = "16ca1a07-2453-47f1-9f00-7ca2dce0a5ea"
SAMPLE_NEW_VNFD_ID = "5484de3b-ff51-4c1a-b54c-4215a8130078"

_inst_info_example_before = {
    "id": "c80f7afa-65f3-4be6-94ae-fdf438ac2d61",
    "vnfInstanceName": "modify_vnf_before",
    "vnfdId": SAMPLE_OLD_VNFD_ID,
    "vnfProvider": "Company",
    "vnfProductName": "Sample VNF",
    "vnfSoftwareVersion": "1.0",
    "vnfdVersion": "1.0",
    "vimConnectionInfo": {
        "vim1": {
            "vimId": "013b247c-818c-415e-b487-c27ca1b5547f",
            "vimType": "kubernetes",
            "interfaceInfo": {
                "endpoint": "https://kubernetes.default.svc:6443",
                "ssl_ca_cert": "fake_cert"
            },
            "accessInfo": {
                "bearer_token": "fake_token"
            }
        }
    },
    "instantiationState": "INSTANTIATED",
    "instantiatedVnfInfo": {
        "flavourId": "simple",
        "vnfState": "STARTED",
        "scaleStatus": [{
            "aspectId": "vdu1_aspect",
            "scaleLevel": 0
        }, {
            "aspectId": "vdu2_aspect",
            "scaleLevel": 0
        }],
        "maxScaleLevels": [{
            "aspectId": "vdu1_aspect",
            "scaleLevel": 2
        }, {
            "aspectId": "vdu2_aspect",
            "scaleLevel": 2
        }],
        "vnfcResourceInfo": [{
            "id": "daemonset-vdu5-wh824",
            "vduId": "VDU5",
            "computeResource": {
                "resourceId": "daemonset-vdu5-wh824",
                "vimLevelResourceType": "DaemonSet"
            },
            "metadata": {}
        }, {
            "id": "deployment2-vdu6-6f8c5c5ddb-9ptn9",
            "vduId": "VDU6",
            "computeResource": {
                "resourceId": "deployment2-vdu6-6f8c5c5ddb-9ptn9",
                "vimLevelResourceType": "Deployment"
            },
            "metadata": {}
        }, {
            "id": "env-test",
            "vduId": "VDU3",
            "computeResource": {
                "resourceId": "env-test",
                "vimLevelResourceType": "Pod"
            },
            "metadata": {}
        }, {
            "id": "env-test2",
            "vduId": "VDU7",
            "computeResource": {
                "resourceId": "env-test2",
                "vimLevelResourceType": "Pod"
            },
            "metadata": {}
        }, {
            "id": "vdu1-update-5b9d95d894-dxs6l",
            "vduId": "VDU1",
            "computeResource": {
                "resourceId": "vdu1-update-5b9d95d894-dxs6l",
                "vimLevelResourceType": "Deployment"
            },
            "metadata": {}
        }, {
            "id": "vdu2-update-ckcjn",
            "vduId": "VDU2",
            "computeResource": {
                "resourceId": "vdu2-update-ckcjn",
                "vimLevelResourceType": "ReplicaSet"
            },
            "metadata": {}
        }, {
            "id": "volume-test",
            "vduId": "VDU4",
            "computeResource": {
                "resourceId": "volume-test",
                "vimLevelResourceType": "Pod"
            },
            "metadata": {}
        }, {
            "id": "volume-test2",
            "vduId": "VDU8",
            "computeResource": {
                "resourceId": "volume-test2",
                "vimLevelResourceType": "Pod"
            },
            "metadata": {}
        }],
        "vnfcInfo": [{
            "id": "VDU5-daemonset-vdu5-wh824",
            "vduId": "VDU5",
            "vnfcResourceInfoId": "daemonset-vdu5-wh824",
            "vnfcState": "STARTED"
        }, {
            "id": "VDU6-deployment2-vdu6-6f8c5c5ddb-9ptn9",
            "vduId": "VDU6",
            "vnfcResourceInfoId": "deployment2-vdu6-6f8c5c5ddb-9ptn9",
            "vnfcState": "STARTED"
        }, {
            "id": "VDU3-env-test",
            "vduId": "VDU3",
            "vnfcResourceInfoId": "env-test",
            "vnfcState": "STARTED"
        }, {
            "id": "VDU7-env-test2",
            "vduId": "VDU7",
            "vnfcResourceInfoId": "env-test2",
            "vnfcState": "STARTED"
        }, {
            "id": "VDU1-vdu1-update-5b9d95d894-dxs6l",
            "vduId": "VDU1",
            "vnfcResourceInfoId": "vdu1-update-5b9d95d894-dxs6l",
            "vnfcState": "STARTED"
        }, {
            "id": "VDU2-vdu2-update-ckcjn",
            "vduId": "VDU2",
            "vnfcResourceInfoId": "vdu2-update-ckcjn",
            "vnfcState": "STARTED"
        }, {
            "id": "VDU4-volume-test",
            "vduId": "VDU4",
            "vnfcResourceInfoId": "volume-test",
            "vnfcState": "STARTED"
        }, {
            "id": "VDU8-volume-test2",
            "vduId": "VDU8",
            "vnfcResourceInfoId": "volume-test2",
            "vnfcState": "STARTED"
        }],
        "metadata": {
            "namespace": "default",
            "vdu_reses": {
                "VDU1": {
                    "apiVersion": "apps/v1",
                    "kind": "Deployment",
                    "metadata": {
                        "name": "vdu1-update",
                        "namespace": "default"
                    },
                    "spec": {
                        "replicas": 1,
                        "selector": {
                            "matchLabels": {
                                "app": "webserver"
                            }
                        },
                        "template": {
                            "metadata": {
                                "labels": {
                                    "app": "webserver"
                                }
                            },
                            "spec": {
                                "containers": [{
                                    "name": "nginx",
                                    "image": "nginx",
                                    "imagePullPolicy": "IfNotPresent",
                                    "ports": [{
                                        "containerPort": 80,
                                        "protocol": "TCP"
                                    }],
                                    "env": [{
                                        "name": "CMENV",
                                        "valueFrom": {
                                            "configMapKeyRef": {
                                                "name": "cm-data",
                                                "key": "cmKey1.txt"
                                            }
                                        }
                                    }, {
                                        "name": "SECENV",
                                        "valueFrom": {
                                            "secretKeyRef": {
                                                "name": "secret-data",
                                                "key": "password"
                                            }
                                        }
                                    }],
                                    "envFrom": [{
                                        "prefix": "CM_",
                                        "configMapRef": {
                                            "name": "cm-data"
                                        }
                                    }, {
                                        "prefix": "SEC_",
                                        "secretRef": {
                                            "name": "secret-data"
                                        }
                                    }]
                                }]
                            }
                        }
                    }
                },
                "VDU3": {
                    "apiVersion": "v1",
                    "kind": "Pod",
                    "metadata": {
                        "name": "env-test",
                        "namespace": "default"
                    },
                    "spec": {
                        "containers": [{
                            "image": "nginx",
                            "name": "nginx",
                            "env": [{
                                "name": "CMENV",
                                "valueFrom": {
                                    "configMapKeyRef": {
                                        "name": "cm-data",
                                        "key": "cmKey1.txt"
                                    }
                                }
                            }, {
                                "name": "SECENV",
                                "valueFrom": {
                                    "secretKeyRef": {
                                        "name": "secret-data",
                                        "key": "password"
                                    }
                                }
                            }],
                            "envFrom": [{
                                "prefix": "CM_",
                                "configMapRef": {
                                    "name": "cm-data"
                                }
                            }, {
                                "prefix": "SEC_",
                                "secretRef": {
                                    "name": "secret-data"
                                }
                            }]
                        }]
                    }
                },
                "VDU4": {
                    "apiVersion": "v1",
                    "kind": "Pod",
                    "metadata": {
                        "name": "volume-test",
                        "namespace": "default"
                    },
                    "spec": {
                        "containers": [{
                            "image": "nginx",
                            "name": "nginx",
                            "volumeMounts": [{
                                "name": "cm-volume",
                                "mountPath": "/config"
                            }, {
                                "name": "sec-volume",
                                "mountPath": "/etc/secrets"
                            }]
                        }],
                        "volumes": [{
                            "name": "cm-volume",
                            "configMap": {
                                "name": "cm-data",
                                "defaultMode": 438,
                                "items": [{
                                    "key": "cmKey1.txt",
                                    "path": "cm/config.txt"
                                }]
                            }
                        }, {
                            "name": "sec-volume",
                            "secret": {
                                "secretName": "secret-data",
                                "defaultMode": 384,
                                "items": [{
                                    "key": "secKey1.txt",
                                    "path": "creds/secret.txt"
                                }]
                            }
                        }]
                    }
                },
                "VDU2": {
                    "apiVersion": "apps/v1",
                    "kind": "ReplicaSet",
                    "metadata": {
                        "name": "vdu2-update",
                        "namespace": "default"
                    },
                    "spec": {
                        "replicas": 1,
                        "selector": {
                            "matchLabels": {
                                "app": "webserver"
                            }
                        },
                        "template": {
                            "metadata": {
                                "labels": {
                                    "app": "webserver"
                                }
                            },
                            "spec": {
                                "containers": [{
                                    "name": "nginx",
                                    "image": "nginx",
                                    "imagePullPolicy": "IfNotPresent",
                                    "ports": [{
                                        "containerPort": 80,
                                        "protocol": "TCP"
                                    }],
                                    "volumeMounts": [{
                                        "name": "cm-volume",
                                        "mountPath": "/config"
                                    }, {
                                        "name": "sec-volume",
                                        "mountPath": "/etc/secrets"
                                    }]
                                }],
                                "volumes": [{
                                    "name": "cm-volume",
                                    "configMap": {
                                        "name": "cm-data",
                                        "defaultMode": 438,
                                        "items": [{
                                            "key": "cmKey1.txt",
                                            "path": "cm/config.txt"
                                        }]
                                    }
                                }, {
                                    "name": "sec-volume",
                                    "secret": {
                                        "secretName": "secret-data",
                                        "defaultMode": 384,
                                        "items": [{
                                            "key": "secKey1.txt",
                                            "path": "creds/secret.txt"
                                        }]
                                    }
                                }]
                            }
                        }
                    }
                },
                "VDU7": {
                    "apiVersion": "v1",
                    "kind": "Pod",
                    "metadata": {
                        "name": "env-test2",
                        "namespace": "default"
                    },
                    "spec": {
                        "containers": [{
                            "image": "nginx",
                            "name": "nginx",
                            "env": [{
                                "name": "CMENV",
                                "valueFrom": {
                                    "configMapKeyRef": {
                                        "name": "cm-data3",
                                        "key": "cmKey1.txt"
                                    }
                                }
                            }, {
                                "name": "SECENV",
                                "valueFrom": {
                                    "secretKeyRef": {
                                        "name": "secret-data3",
                                        "key": "password"
                                    }
                                }
                            }],
                            "envFrom": [{
                                "prefix": "CM_",
                                "configMapRef": {
                                    "name": "cm-data3"
                                }
                            }, {
                                "prefix": "SEC_",
                                "secretRef": {
                                    "name": "secret-data3"
                                }
                            }]
                        }]
                    }
                },
                "VDU8": {
                    "apiVersion": "v1",
                    "kind": "Pod",
                    "metadata": {
                        "name": "volume-test2",
                        "namespace": "default"
                    },
                    "spec": {
                        "containers": [{
                            "image": "nginx",
                            "name": "nginx",
                            "volumeMounts": [{
                                "name": "cm-volume",
                                "mountPath": "/config"
                            }, {
                                "name": "sec-volume",
                                "mountPath": "/etc/secrets"
                            }]
                        }],
                        "volumes": [{
                            "name": "cm-volume",
                            "configMap": {
                                "name": "cm-data3",
                                "defaultMode": 438,
                                "items": [{
                                    "key": "cmKey1.txt",
                                    "path": "cm/config.txt"
                                }]
                            }
                        }, {
                            "name": "sec-volume",
                            "secret": {
                                "secretName": "secret-data3",
                                "defaultMode": 384,
                                "items": [{
                                    "key": "secKey1.txt",
                                    "path": "creds/secret.txt"
                                }]
                            }
                        }]
                    }
                },
                "VDU5": {
                    "apiVersion": "apps/v1",
                    "kind": "DaemonSet",
                    "metadata": {
                        "name": "daemonset-vdu5",
                        "namespace": "default"
                    },
                    "spec": {
                        "selector": {
                            "matchLabels": {
                                "app": "nginx"
                            }
                        },
                        "template": {
                            "metadata": {
                                "labels": {
                                    "app": "nginx"
                                }
                            },
                            "spec": {
                                "containers": [{
                                    "image": "nginx",
                                    "name": "nginx",
                                    "imagePullPolicy": "IfNotPresent",
                                    "ports": [{
                                        "containerPort": 80,
                                        "protocol": "TCP"
                                    }],
                                    "env": [{
                                        "name": "CMENV",
                                        "valueFrom": {
                                            "configMapKeyRef": {
                                                "name": "cm-data",
                                                "key": "cmKey1.txt"
                                            }
                                        }
                                    }, {
                                        "name": "SECENV",
                                        "valueFrom": {
                                            "secretKeyRef": {
                                                "name": "secret-data",
                                                "key": "password"
                                            }
                                        }
                                    }],
                                    "envFrom": [{
                                        "prefix": "CM_",
                                        "configMapRef": {
                                            "name": "cm-data"
                                        }
                                    }, {
                                        "prefix": "SEC_",
                                        "secretRef": {
                                            "name": "secret-data"
                                        }
                                    }]
                                }]
                            }
                        }
                    }
                },
                "VDU6": {
                    "apiVersion": "apps/v1",
                    "kind": "Deployment",
                    "metadata": {
                        "name": "deployment2-vdu6",
                        "namespace": "default"
                    },
                    "spec": {
                        "replicas": 1,
                        "selector": {
                            "matchLabels": {
                                "app": "webserver"
                            }
                        },
                        "template": {
                            "metadata": {
                                "labels": {
                                    "app": "webserver"
                                }
                            },
                            "spec": {
                                "containers": [{
                                    "name": "nginx",
                                    "image": "nginx",
                                    "imagePullPolicy": "IfNotPresent",
                                    "ports": [{
                                        "containerPort": 80,
                                        "protocol": "TCP"
                                    }],
                                    "env": [{
                                        "name": "CMENV",
                                        "valueFrom": {
                                            "configMapKeyRef": {
                                                "name": "cm-data3",
                                                "key": "cmKey1.txt"
                                            }
                                        }
                                    }, {
                                        "name": "SECENV",
                                        "valueFrom": {
                                            "secretKeyRef": {
                                                "name": "secret-data3",
                                                "key": "password"
                                            }
                                        }
                                    }],
                                    "envFrom": [{
                                        "prefix": "CM_",
                                        "configMapRef": {
                                            "name": "cm-data3"
                                        }
                                    }, {
                                        "prefix": "SEC_",
                                        "secretRef": {
                                            "name": "secret-data3"
                                        }
                                    }]
                                }]
                            }
                        }
                    }
                }
            },
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
    },
    "_links": {
        "self": {
            "href": "http://127.0.0.1:9890/vnflcm/v2/"
                    "vnf_instances/c80f7afa-65f3-4be6-94ae-fdf438ac2d61"
        },
        "terminate": {
            "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/"
                    "c80f7afa-65f3-4be6-94ae-fdf438ac2d61/terminate"
        },
        "scale": {
            "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/"
                    "c80f7afa-65f3-4be6-94ae-fdf438ac2d61/scale"
        },
        "heal": {
            "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/"
                    "c80f7afa-65f3-4be6-94ae-fdf438ac2d61/heal"
        },
        "changeExtConn": {
            "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/"
                    "c80f7afa-65f3-4be6-94ae-fdf438ac2d61/change_ext_conn"
        }
    }
}


class TestContainerUpdate(base.TestCase):

    def setUp(self):
        super(TestContainerUpdate, self).setUp()
        cfg.CONF.v2_vnfm.kubernetes_vim_rsc_wait_timeout = 0
        sample_dir = utils.test_sample("functional/sol_kubernetes_v2")
        self.old_vnfd = vnfd_utils.Vnfd(SAMPLE_OLD_VNFD_ID)
        self.old_vnfd.init_from_csar_dir(os.path.join(
            sample_dir, "test_cnf_container_update_before/contents"))
        self.new_vnfd = vnfd_utils.Vnfd(SAMPLE_NEW_VNFD_ID)
        self.new_vnfd.init_from_csar_dir(os.path.join(
            sample_dir, "test_cnf_container_update_after/contents"))
        self.req = {
            "vnfdId": SAMPLE_NEW_VNFD_ID,
            "vnfInstanceName": "modify_vnf_after",
            "metadata": {
                "configmap_secret_paths": [
                    "Files/kubernetes/configmap_2.yaml",
                    "Files/kubernetes/secret_2.yaml"
                ]
            }
        }
        self.inst = copy.deepcopy(_inst_info_example_before)
        grant_req = None
        grant = None
        self.old_csar_dir = self.old_vnfd.make_tmp_csar_dir()
        self.new_csar_dir = self.new_vnfd.make_tmp_csar_dir()

        self.cntr_update_mgmt = mgmt_driver.ContainerUpdateMgmtDriver(
            self.req, self.inst, grant_req, grant, self.old_csar_dir,
            self.new_csar_dir)

    def test_container_update_modify_container_img(self):
        old_containers = [
            client.V1Container(image="curry", name="curry")
        ]

        new_containers = [{"image": "curry1", "name": "curry"}]
        self.cntr_update_mgmt._modify_container_img(
            old_containers, new_containers)
        self.assertEqual('curry1', old_containers[0].image)

    @mock.patch.object(mgmt_driver.ContainerUpdateMgmtDriver,
                       'modify_information_start')
    @mock.patch.object(sys.stdout.buffer, 'write')
    @mock.patch.object(pickle, 'load')
    def test_container_update_main(self, mock_script, mock_write, mock_start):
        mock_script.return_value = {
            "operation": "modify_information_start",
            "request": self.req,
            "vnf_instance": self.inst,
            "grant_request": None,
            "grant_response": None,
            "tmp_csar_dir": self.old_csar_dir,
            "new_csar_dir": self.new_csar_dir
        }
        mock_start.return_value = {"modify_information_start": "called"}
        mgmt_driver.main()
        self.assertEqual(1, mock_start.call_count)

        mgmt_driver.main()
        mock_script.return_value['operation'] = 'fake'
        self.assertRaises(exceptions.MgmtDriverOtherError, mgmt_driver.main)

    @mock.patch.object(urllib2, 'urlopen')
    def test_container_update_modify_information_end_error(
            self, mock_urlopen):
        req = {
            "vnfdId": SAMPLE_NEW_VNFD_ID,
            "vnfInstanceName": "modify_vnf_after",
            "metadata": {
                "configmap_secret_paths": [
                    "http://fake.configmap_2.yaml",
                    "http://fake.secret_2.yaml"
                ]
            }
        }
        inst = _inst_info_example_before
        new_mgmt_driver = mgmt_driver.ContainerUpdateMgmtDriver(
            req, inst, None, None, self.old_csar_dir,
            self.new_csar_dir)
        cur_dir = os.path.dirname(__file__)
        mock_urlopen.return_value = open(
            os.path.join(cur_dir, 'fake_configmap.yaml'))
        self.assertRaises(
            exceptions.MgmtDriverOtherError,
            new_mgmt_driver.modify_information_end)

    @mock.patch.object(client.CoreV1Api, 'list_namespaced_pod')
    @mock.patch.object(client.CoreV1Api, 'delete_namespaced_pod')
    @mock.patch.object(client.CoreV1Api, 'replace_namespaced_secret')
    @mock.patch.object(client.CoreV1Api, 'replace_namespaced_config_map')
    @mock.patch.object(client.AppsV1Api, 'replace_namespaced_daemon_set')
    @mock.patch.object(client.CoreV1Api, 'replace_namespaced_pod')
    @mock.patch.object(client.AppsV1Api, 'replace_namespaced_replica_set')
    @mock.patch.object(client.AppsV1Api, 'replace_namespaced_deployment')
    @mock.patch.object(client.AppsV1Api, 'read_namespaced_daemon_set')
    @mock.patch.object(client.CoreV1Api, 'read_namespaced_pod')
    @mock.patch.object(client.AppsV1Api, 'read_namespaced_replica_set')
    @mock.patch.object(client.AppsV1Api, 'read_namespaced_deployment')
    def test_container_update_modify_information_end(
            self, mock_read_deployment, mock_read_replica_set,
            mock_read_pod, mock_read_daemon_set, mock_replace_deployment,
            mock_replace_replica_set, mock_replace_pod,
            mock_replace_daemon_set, mock_replace_config_map,
            mock_replace_secret, mock_delete_pod, mock_list_pod):
        inst_before = copy.deepcopy(self.cntr_update_mgmt.inst)
        mock_read_deployment.side_effect = [
            fakes.fake_deployment('vdu1-update', 'nginx', 'nginx',
                                  'cmKey1.txt', 'cm-data', 'password',
                                  'secret-data'),
            fakes.fake_deployment('deployment2-vdu6', 'nginx', 'nginx',
                                  'cmKey1.txt', 'cm-data3', 'password',
                                  'secret-data3'),
            fakes.fake_deployment('vdu1-update', 'nginx', 'cirros',
                                  'cmKey1.txt', 'cm-data', 'password',
                                  'secret-data')
        ]
        mock_read_daemon_set.side_effect = [
            fakes.fake_daemon_set('daemonset-vdu5', 'nginx', 'nginx',
                                  'cmKey1.txt', 'cm-data', 'password',
                                  'secret-data'),
            fakes.fake_daemon_set('daemonset-vdu5', 'nginx', 'cirros',
                                  'cmKey1.txt', 'cm-data', 'password',
                                  'secret-data')
        ]
        mock_read_replica_set.side_effect = [
            fakes.fake_replica_set('vdu2-update', 'nginx', 'nginx',
                                   'cmKey1.txt', 'cm-data', 'password',
                                   'secret-data'),
            fakes.fake_replica_set('vdu2-update', 'nginx',
                                   'celebdor/kuryr-demo', 'cmKey1.txt',
                                   'cm-data', 'password', 'secret-data')
        ]
        mock_read_pod.side_effect = [
            fakes.fake_pod_env('env-test', 'nginx', 'nginx', 'cmKey1.txt',
                               'cm-data', 'password', 'secret-data'),
            fakes.fake_pod_vol('volume-test', 'nginx', 'nginx',
                               'cm-data', 'secret-data'),
            fakes.fake_pod_env('env-test2', 'nginx', 'nginx', 'cmKey1.txt',
                               'cm-data3', 'password', 'secret-data3'),
            fakes.fake_pod_vol('volume-test2', 'nginx', 'nginx',
                               'cm-data3', 'secret-data3'),
            fakes.fake_pod_env('env-test', 'nginx', 'tomcat', 'cmKey1.txt',
                               'cm-data', 'password', 'secret-data'),
            fakes.fake_pod_vol('volume-test', 'nginx', 'cirros',
                               'cm-data', 'secret-data'),
        ]
        mock_list_pod.side_effect = [
            client.V1PodList(items=[
                fakes.get_fake_pod_info(
                    pod_name='vdu1-update-5b9d95d894-dxs6l'),
                fakes.get_fake_pod_info(pod_name='env-test'),
                fakes.get_fake_pod_info(pod_name='volume-test'),
                fakes.get_fake_pod_info(pod_name='vdu2-update-ckcjn'),
                fakes.get_fake_pod_info(pod_name='env-test2'),
                fakes.get_fake_pod_info(pod_name='volume-test2'),
                fakes.get_fake_pod_info(pod_name='daemonset-vdu5-wh824'),
                fakes.get_fake_pod_info(
                    pod_name='deployment2-vdu6-6f8c5c5ddb-9ptn9'),
            ]),
            client.V1PodList(items=[
                fakes.get_fake_pod_info(
                    pod_name='vdu1-update-764bbf8846-2zv8q'),
                fakes.get_fake_pod_info(pod_name='env-test'),
                fakes.get_fake_pod_info(pod_name='volume-test'),
                fakes.get_fake_pod_info(pod_name='vdu2-update-kct28'),
                fakes.get_fake_pod_info(pod_name='env-test2'),
                fakes.get_fake_pod_info(pod_name='volume-test2'),
                fakes.get_fake_pod_info(pod_name='daemonset-vdu5-5wgc4'),
                fakes.get_fake_pod_info(
                    pod_name='deployment2-vdu6-6f8c5c5ddb-9ptn9'),
            ]),
            client.V1PodList(items=[
                fakes.get_fake_pod_info(
                    pod_name='vdu1-update-764bbf8846-2zv8q'),
                fakes.get_fake_pod_info(pod_name='env-test'),
                fakes.get_fake_pod_info(pod_name='volume-test'),
                fakes.get_fake_pod_info(pod_name='vdu2-update-kct28'),
                fakes.get_fake_pod_info(pod_name='env-test2'),
                fakes.get_fake_pod_info(pod_name='volume-test2'),
                fakes.get_fake_pod_info(pod_name='daemonset-vdu5-5wgc4'),
                fakes.get_fake_pod_info(
                    pod_name='deployment2-vdu6-6f8c5c5ddb-9ptn9'),
            ])
        ]
        output = self.cntr_update_mgmt.modify_information_end()['vnf_instance']
        for vnfc_res_info in output['instantiatedVnfInfo']['vnfcResourceInfo']:
            if vnfc_res_info['vduId'] in ['VDU1', 'VDU2', 'VDU5']:
                vnfc_id_before = [
                    vnfc_res_before['id'] for vnfc_res_before in
                    inst_before['instantiatedVnfInfo']['vnfcResourceInfo'] if
                    vnfc_res_before['vduId'] == vnfc_res_info['vduId']][0]
                self.assertNotEqual(vnfc_id_before, vnfc_res_info['id'])
