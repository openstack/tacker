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


def max_sample_instantiate(auth_url, bearer_token):
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
        "vimType": "kubernetes",
        "interfaceInfo": {"endpoint": auth_url},
        "accessInfo": {
            "bearer_token": bearer_token,
            "region": "RegionOne",
        },
        "extra": {"dummy-key": "dummy-val"}
    }
    vim_2 = {
        "vimId": vim_id_2,
        "vimType": "kubernetes",
        "interfaceInfo": {"endpoint": auth_url},
        "accessInfo": {
            "username": "dummy_user",
            "region": "RegionOne",
            "password": "dummy_password",
        },
        "extra": {"dummy-key": "dummy-val"}
    }
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


def min_sample_instantiate(vim_id_1):
    vim_1 = {
        "vimId": vim_id_1,
        "vimType": "kubernetes",
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


def change_vnfpkg_instantiate(auth_url, bearer_token):
    # All attributes are set.
    # NOTE: All of the following cardinality attributes are set.
    # In addition, 0..N or 1..N attributes are set to 2 or more.
    #  - 0..1 (1)
    #  - 0..N (2 or more)
    #  - 1
    #  - 1..N (2 or more)
    vim_id_1 = uuidutils.generate_uuid()
    vim_1 = {
        "vimId": vim_id_1,
        "vimType": "kubernetes",
        "interfaceInfo": {"endpoint": auth_url},
        "accessInfo": {
            "bearer_token": bearer_token,
            "region": "RegionOne",
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
                "Files/kubernetes/deployment.yaml",
                "Files/kubernetes/namespace.yaml"
            ],
            "namespace": "curry"
        }
    }


def change_vnfpkg_all_params(vnfd_id):
    return {
        "vnfdId": vnfd_id,
        "additionalParams": {
            "upgrade_type": "RollingUpdate",
            "lcm-operation-coordinate-old-vnf":
                "Scripts/coordinate_old_vnf.py",
            "lcm-operation-coordinate-old-vnf-class": "CoordinateOldVnf",
            "lcm-operation-coordinate-new-vnf":
                "Scripts/coordinate_new_vnf.py",
            "lcm-operation-coordinate-new-vnf-class": "CoordinateNewVnf",
            "lcm-kubernetes-def-files": [
                "Files/new_kubernetes/new_deployment.yaml"],
            "vdu_params": [{
                "vdu_id": "VDU2"
            }]
        }
    }


def change_vnfpkg_instantiate_min(vim_id_1):
    vim_1 = {
        "vimId": vim_id_1,
        "vimType": "kubernetes",
    }
    return {
        "flavourId": "simple",
        "vimConnectionInfo": {
            "vim1": vim_1,
        },
        "additionalParams": {
            "lcm-kubernetes-def-files": [
                "Files/kubernetes/deployment.yaml"
            ]
        }
    }


def change_vnfpkg_min(vnfd_id):
    return {
        "vnfdId": vnfd_id,
        "additionalParams": {
            "upgrade_type": "RollingUpdate",
            "lcm-operation-coordinate-old-vnf":
                "Scripts/coordinate_old_vnf.py",
            "lcm-operation-coordinate-old-vnf-class": "CoordinateOldVnf",
            "lcm-operation-coordinate-new-vnf":
                "Scripts/coordinate_new_vnf.py",
            "lcm-operation-coordinate-new-vnf-class": "CoordinateNewVnf"
        }
    }


def change_vnfpkg_instantiate_error_handing(vim_id_1):
    vim_1 = {
        "vimId": vim_id_1,
        "vimType": "kubernetes",
    }
    return {
        "flavourId": "simple",
        "vimConnectionInfo": {
            "vim1": vim_1,
        },
        "additionalParams": {
            "lcm-kubernetes-def-files": [
                "Files/kubernetes/deployment_fail_test.yaml"
            ]
        }
    }


def change_vnfpkg_error(vnfd_id):
    return {
        "vnfdId": vnfd_id,
        "additionalParams": {
            "upgrade_type": "RollingUpdate",
            "lcm-operation-coordinate-old-vnf":
                "Scripts/coordinate_old_vnf.py",
            "lcm-operation-coordinate-old-vnf-class": "CoordinateOldVnf",
            "lcm-operation-coordinate-new-vnf":
                "Scripts/coordinate_new_vnf.py",
            "lcm-operation-coordinate-new-vnf-class": "CoordinateNewVnf",
            "lcm-kubernetes-def-files": [
                "Files/new_kubernetes/error_deployment.yaml"]
        }
    }
