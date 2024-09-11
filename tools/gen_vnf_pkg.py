# Copyright (C) 2024 Nippon Telegraph and Telephone Corporation
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

import argparse
import glob
import json
import os
import shutil
import tempfile
import textwrap
import yaml
import zipfile

from oslo_utils import uuidutils

from tacker.tests.functional.sol_kubernetes_v2 import paramgen as k8s_paramgen
from tacker.tests.functional.sol_kubernetes_v2 import zipgen as k8s_zipgen
from tacker.tests.functional.sol_v2_common import paramgen
from tacker.tests.functional.sol_v2_common import utils
from tacker.tests.functional.sol_v2_common import zipgen


STANDARD_OUTPUT="./output/userdata_standard/"
K8S_OUTPUT="./output/test_instantiate_cnf_resources/"
HELM_OUTPUT="./output/helm_instantiate/"


parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter,
        description='Create VNF Package zip and parameter files',
        add_help=True
        )

parser.add_argument('-t', '--type',
                    help=textwrap.dedent('''\
                            specify the vim type
                              * ETSINFV.OPENSTACK_KEYSTONE.V_3
                              * ETSINFV.KUBERNETES.V_1
                              * ETSINFV.HELM.V_3
                         '''),
                    type=str, metavar='VIM_TYPE',
                    choices=['ETSINFV.OPENSTACK_KEYSTONE.V_3', 'ETSINFV.KUBERNETES.V_1', 'ETSINFV.HELM.V_3'],
                    required=True)

args = parser.parse_args()

if args.type == 'ETSINFV.OPENSTACK_KEYSTONE.V_3':
    print(f"VIM type = {args.type}")

    os.makedirs(STANDARD_OUTPUT, exist_ok=True)

    vnfd_id, zip_path = zipgen.userdata_standard()
    print(f"Zip file: {zip_path.rsplit('/', 1)[1]}")

    shutil.move(zip_path, STANDARD_OUTPUT)
    shutil.rmtree(zip_path.rsplit('/', 1)[0])

    create_req = paramgen.sample3_create(vnfd_id)
    terminate_req = paramgen.sample3_terminate()

    net_ids = utils.get_network_ids(['net0', 'net1', 'net_mgmt'])
    subnet_ids = utils.get_subnet_ids(['subnet0', 'subnet1'])

    instantiate_req = paramgen.sample3_instantiate(
            net_ids, subnet_ids, "http://localhost/identity/v3")

    scale_out_req = paramgen.sample3_scale_out()
    scale_in_req = paramgen.sample3_scale_in()
    heal_req = paramgen.sample3_heal()
    change_ext_conn_req = paramgen.sample3_change_ext_conn(net_ids)
    update_req = paramgen.sample3_update_vnf_vnfd_id("replace real vnfd id")

    with open(f"{STANDARD_OUTPUT}create_req", "w") as f:
        f.write(json.dumps(create_req, indent=2))

    with open(f"{STANDARD_OUTPUT}terminate_req", "w") as f:
        f.write(json.dumps(terminate_req, indent=2))

    with open(f"{STANDARD_OUTPUT}instantiate_req", "w") as f:
        f.write(json.dumps(instantiate_req, indent=2))

    with open(f"{STANDARD_OUTPUT}scale_out_req", "w") as f:
        f.write(json.dumps(scale_out_req, indent=2))

    with open(f"{STANDARD_OUTPUT}scale_in_req", "w") as f:
        f.write(json.dumps(scale_in_req, indent=2))

    # NOTE: vnfcInstanceId should be filled by hand
    with open(f"{STANDARD_OUTPUT}heal_req", "w") as f:
        f.write(json.dumps(heal_req, indent=2))

    with open(f"{STANDARD_OUTPUT}change_ext_conn_req", "w") as f:
        f.write(json.dumps(change_ext_conn_req, indent=2))

    with open(f"{STANDARD_OUTPUT}update_req", "w") as f:
        f.write(json.dumps(update_req, indent=2))

    print("--------------------------------------------------")

    zip_file = zipfile.ZipFile(f"{STANDARD_OUTPUT}userdata_standard.zip")
    files = zip_file.namelist()
    for file in files:
        print(file)
    zip_file.close()

    print("--------------------------------------------------")

elif args.type == 'ETSINFV.KUBERNETES.V_1':
    print(f"VIM type: {args.type}")

    os.makedirs(K8S_OUTPUT, exist_ok=True)

    vnfd_id, zip_path = k8s_zipgen.test_instantiate_cnf_resources()
    print(f"Zip file: {zip_path.rsplit('/', 1)[1]}")

    shutil.move(zip_path, K8S_OUTPUT)
    shutil.rmtree(zip_path.rsplit('/', 1)[0])

    create_req = k8s_paramgen.test_instantiate_cnf_resources_create(vnfd_id)

    # please change auth_url, bearer_token and ssl_ca_cert
    # to your own k8s cluster's info
    auth_url = "https://127.0.0.1:6443"
    bearer_token = "your_k8s_cluster_bearer_token"
    ssl_ca_cert = "k8s_ssl_ca_cert"
    max_sample_instantiate = k8s_paramgen.max_sample_instantiate(
        auth_url, bearer_token, ssl_ca_cert)

    max_sample_terminate = k8s_paramgen.max_sample_terminate()
    max_sample_scale_out = k8s_paramgen.max_sample_scale_out()
    max_sample_scale_in = k8s_paramgen.max_sample_scale_in()
    max_sample_heal = k8s_paramgen.max_sample_heal(["replace real vnfc ids"])

    with open(f"{K8S_OUTPUT}create_req", "w", encoding='utf-8') as f:
        f.write(json.dumps(create_req, indent=2))

    with open(f"{K8S_OUTPUT}max_sample_instantiate", "w", encoding='utf-8') as f:
        f.write(json.dumps(max_sample_instantiate, indent=2))

    with open(f"{K8S_OUTPUT}max_sample_terminate", "w", encoding='utf-8') as f:
        f.write(json.dumps(max_sample_terminate, indent=2))

    with open(f"{K8S_OUTPUT}max_sample_scale_out", "w", encoding='utf-8') as f:
        f.write(json.dumps(max_sample_scale_out, indent=2))

    with open(f"{K8S_OUTPUT}max_sample_scale_in", "w", encoding='utf-8') as f:
        f.write(json.dumps(max_sample_scale_in, indent=2))

    with open(f"{K8S_OUTPUT}max_sample_heal", "w", encoding='utf-8') as f:
        f.write(json.dumps(max_sample_heal, indent=2))

    print("--------------------------------------------------")

    zip_file = zipfile.ZipFile(f"{K8S_OUTPUT}test_instantiate_cnf_resources.zip")
    files = zip_file.namelist()
    for file in files:
        print(file)
    zip_file.close()

    print("--------------------------------------------------")

elif args.type == 'ETSINFV.HELM.V_3':
    print(f"VIM type = {args.type}")

    os.makedirs(HELM_OUTPUT, exist_ok=True)

    vnfd_id, zip_path = k8s_zipgen.test_helm_instantiate()
    print(f"Zip file: {zip_path.rsplit('/', 1)[1]}")

    shutil.move(zip_path, HELM_OUTPUT)
    shutil.rmtree(zip_path.rsplit('/', 1)[0])

    create_req = k8s_paramgen.test_helm_instantiate_create(vnfd_id)

    # please change auth_url, bearer_token and ssl_ca_cert
    # to your own k8s cluster's info
    auth_url = "https://127.0.0.1:6443"
    bearer_token = "your_k8s_cluster_bearer_token"
    ssl_ca_cert = "k8s_ssl_ca_cert"
    helm_instantiate_req = k8s_paramgen.helm_instantiate(
            auth_url, bearer_token, ssl_ca_cert)

    helm_terminate_req = k8s_paramgen.helm_terminate()
    helm_scale_out = k8s_paramgen.helm_scale_out()
    helm_scale_in = k8s_paramgen.helm_scale_in()
    helm_heal = k8s_paramgen.helm_heal(["replace real vnfc ids"])

    with open(f"{HELM_OUTPUT}create_req", "w", encoding='utf-8') as f:
        f.write(json.dumps(create_req, indent=2))

    with open(f"{HELM_OUTPUT}helm_instantiate_req", "w", encoding='utf-8') as f:
        f.write(json.dumps(helm_instantiate_req, indent=2))

    with open(f"{HELM_OUTPUT}helm_terminate_req", "w", encoding='utf-8') as f:
        f.write(json.dumps(helm_terminate_req, indent=2))

    with open(f"{HELM_OUTPUT}helm_scale_out", "w", encoding='utf-8') as f:
        f.write(json.dumps(helm_scale_out, indent=2))

    with open(f"{HELM_OUTPUT}helm_scale_in", "w", encoding='utf-8') as f:
        f.write(json.dumps(helm_scale_in, indent=2))

    with open(f"{HELM_OUTPUT}helm_heal", "w", encoding='utf-8') as f:
        f.write(json.dumps(helm_heal, indent=2))

    print("--------------------------------------------------")

    zip_file = zipfile.ZipFile(f"{HELM_OUTPUT}test_helm_instantiate.zip")
    files = zip_file.namelist()
    for file in files:
        print(file)
    zip_file.close()

    print("--------------------------------------------------")
