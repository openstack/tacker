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
import json
import os
import pprint
import shutil
import subprocess
import sys
import textwrap
import zipfile

from tacker.tests.functional.sol_kubernetes_v2 import paramgen as k8s_paramgen
from tacker.tests.functional.sol_kubernetes_v2 import zipgen as k8s_zipgen
from tacker.tests.functional.sol_v2_common import paramgen
from tacker.tests.functional.sol_v2_common import utils
from tacker.tests.functional.sol_v2_common import zipgen


OUTPUT_ROOT=f"{os.path.curdir}/output"

# Output package dirs for each VIM types.
STANDARD_OUTPUT=f"{OUTPUT_ROOT}/userdata_standard"
K8S_OUTPUT=f"{OUTPUT_ROOT}/test_instantiate_cnf_resources"
HELM_OUTPUT=f"{OUTPUT_ROOT}/helm_instantiate"

# Set of names of short and actual VIM type.
VIM_TYPES = (VIM_OPENSTACK, VIM_KUBERNETES, VIM_HELM) = \
        ('ETSINFV.OPENSTACK_KEYSTONE.V_3',
         'ETSINFV.KUBERNETES.V_1',
         'ETSINFV.HELM.V_3')

# Networks and subnets required for the Tacker's sample VNF package.
REQ_NWS = [
        {"net": "net0", "subnets": ["subnet0"]},
        {"net": "net1", "subnets": ["subnet1"]},
        {"net": "net_mgmt", "subnets": []}]

def get_args():
    """Return parsed args of argparse"""

    parser = argparse.ArgumentParser(
            formatter_class=argparse.RawTextHelpFormatter,
            description='Create VNF Package zip and parameter files',
            add_help=True)

    parser.add_argument('-t', '--type',
                        help=textwrap.dedent('''\
                                vim type (lowercase is also available)
                                * {}
                                * {}
                                * {}
                             '''.format(*VIM_TYPES)),
                        type=str, metavar='VIM_TYPE',
                        choices=list(VIM_TYPES)+[s.lower() for s in VIM_TYPES],
                        required=True)

    return parser.parse_args()


def ask_overwrite(dst_dir):
    """Ask user to overwrite contents in the dest dir if exists

    Get the answer from stdin and return True if it's yes or no input.
    """

    yes = ["y", "Y", "yes", "YES", "Yes"]
    no = ["n", "N", "no", "NO", "No"]

    if os.path.exists(dst_dir) is True:
        while True:
            print(f"Overwrite contents in {dst_dir!r}? [Y/n]")
            line = sys.stdin.readline().rstrip("\n")
            if line in yes or line == "":
                return True
            elif line in no:
                return False
    return True


def req_nw_names():
    """Get a set of lists of required nets and subnets"""

    nets = [n["net"] for n in REQ_NWS]
    subnets = [sn for n in REQ_NWS for sn in n["subnets"]]
    return nets, subnets


def has_all_req_networks():
    """Check if any required network not exists

    Return a combination of required networks not found on openstack. So,
    it returns empty list if all the required networks exist."""

    nets, subnets = req_nw_names()
    nw_no_exist = {"nets": [], "subnets": []}

    cmd_nwl = ["openstack", "network", "list", "-f", "json"]
    os_nws = json.loads(
            subprocess.run(cmd_nwl, capture_output=True).stdout)
    net_names = [n["Name"] for n in os_nws]

    cmd_snwl = ["openstack", "subnet", "list", "-f", "json"]
    os_subnws = json.loads(
            subprocess.run(cmd_snwl, capture_output=True).stdout)
    subnet_names = [sn["Name"] for sn in os_subnws]

    for n in nets:
        if n not in net_names:
            nw_no_exist["nets"].append(n)

    for sn in subnets:
        if sn not in subnet_names:
            nw_no_exist["subnets"].append(sn)

    if nw_no_exist["nets"] or nw_no_exist["subnets"]:
        return False

    return True


def main():
    args = get_args()

    if has_all_req_networks() is False:
        print("Error: Create all the required nets and subnets below "
              "before running this script.")
        pprint.pprint(REQ_NWS, indent=2)
        exit()

    if args.type == VIM_OPENSTACK or args.type == VIM_OPENSTACK.lower():
        if ask_overwrite(STANDARD_OUTPUT) is not True:
            print("Skip to generate package.")
            exit()
        os.makedirs(STANDARD_OUTPUT, exist_ok=True)

        vnfd_id, zip_src = zipgen.userdata_standard()
        zip_fn = zip_src.rsplit('/', 1)[1]
        zip_dst = f"{STANDARD_OUTPUT}/{zip_fn}"

        print(f"Generating zip file: {STANDARD_OUTPUT}/{zip_fn} ...")

        shutil.move(os.path.abspath(zip_src), os.path.abspath(zip_dst))
        shutil.rmtree(zip_src.rsplit('/', 1)[0])

        nets, subnets = req_nw_names()
        net_ids = utils.get_network_ids(nets)
        subnet_ids = utils.get_subnet_ids(subnets)

        req_files = {
            "create_req": paramgen.sample3_create(vnfd_id),
            "terminate_req": paramgen.sample3_terminate(),
            "instantiate_req": paramgen.sample3_instantiate(
                    net_ids, subnet_ids, "http://localhost/identity/v3"),
            "scale_out_req": paramgen.sample3_scale_out(),
            "scale_in_req": paramgen.sample3_scale_in(),
            "heal_req": paramgen.sample3_heal(),
            "change_ext_conn_req": paramgen.sample3_change_ext_conn(net_ids),
            "update_req": paramgen.sample3_update_vnf_vnfd_id("replace real vnfd id")
            }

        for fn in req_files.keys():
            with open(f"{STANDARD_OUTPUT}/{fn}", "w") as f:
                f.write(json.dumps(req_files[fn], indent=2))

        with zipfile.ZipFile(zip_dst) as zf:
            zf.printdir()

    elif args.type == VIM_KUBERNETES or args.type == VIM_KUBERNETES.lower():
        if ask_overwrite(K8S_OUTPUT) is not True:
            print("Skip to generate package.")
            exit()
        os.makedirs(K8S_OUTPUT, exist_ok=True)

        vnfd_id, zip_src = k8s_zipgen.test_instantiate_cnf_resources()
        zip_fn = zip_src.rsplit('/', 1)[1]
        zip_dst = f"{K8S_OUTPUT}/{zip_fn}"

        print(f"Generating zip file: {K8S_OUTPUT}/{zip_fn} ...")

        shutil.move(os.path.abspath(zip_src), os.path.abspath(zip_dst))
        shutil.rmtree(zip_src.rsplit('/', 1)[0])


        # TODO(yasufum) Enable to change auth_url, bearer_token and ssl_ca_cert
        # to your own k8s cluster's info
        auth_url = "https://127.0.0.1:6443"
        bearer_token = "your_k8s_cluster_bearer_token"
        ssl_ca_cert = "k8s_ssl_ca_cert"

        req_files = {
            "create_req": k8s_paramgen.test_instantiate_cnf_resources_create(vnfd_id),
            "max_sample_instantiate": k8s_paramgen.max_sample_instantiate(
                auth_url, bearer_token, ssl_ca_cert),
            "max_sample_terminate": k8s_paramgen.max_sample_terminate(),
            "max_sample_scale_out": k8s_paramgen.max_sample_scale_out(),
            "max_sample_scale_in": k8s_paramgen.max_sample_scale_in(),
            "max_sample_heal": k8s_paramgen.max_sample_heal(["replace real vnfc ids"])
            }

        for fn in req_files.keys():
            with open(f"{K8S_OUTPUT}/{fn}", "w", encoding='utf-8') as f:
                f.write(json.dumps(req_files[fn], indent=2))

        with zipfile.ZipFile(zip_dst) as zf:
            zf.printdir()

    elif args.type == VIM_HELM or args.type == VIM_HELM.lower():
        if ask_overwrite(HELM_OUTPUT) is not True:
            print("Skip to generate package.")
            exit()
        os.makedirs(HELM_OUTPUT, exist_ok=True)

        vnfd_id, zip_src = k8s_zipgen.test_helm_instantiate()
        zip_fn = zip_src.rsplit('/', 1)[1]
        zip_dst = f"{HELM_OUTPUT}/{zip_fn}"

        print(f"Generating zip file: {HELM_OUTPUT}/{zip_fn} ...")

        shutil.move(os.path.abspath(zip_src), os.path.abspath(zip_dst))
        shutil.rmtree(zip_src.rsplit('/', 1)[0])

        # TODO(yasufum) Enable to change auth_url, bearer_token and ssl_ca_cert
        # to your own k8s cluster's info
        auth_url = "https://127.0.0.1:6443"
        bearer_token = "your_k8s_cluster_bearer_token"
        ssl_ca_cert = "k8s_ssl_ca_cert"

        req_files = {
            "create_req": k8s_paramgen.test_helm_instantiate_create(vnfd_id),
            "helm_instantiate_req": k8s_paramgen.helm_instantiate(
                auth_url, bearer_token, ssl_ca_cert),
            "helm_terminate_req": k8s_paramgen.helm_terminate(),
            "helm_scale_out": k8s_paramgen.helm_scale_out(),
            "helm_scale_in": k8s_paramgen.helm_scale_in(),
            "helm_heal": k8s_paramgen.helm_heal(["replace real vnfc ids"])
            }
        for fn in req_files.keys():
            with open(f"{HELM_OUTPUT}/{fn}", "w", encoding='utf-8') as f:
                f.write(json.dumps(req_files[fn], indent=2))

        with zipfile.ZipFile(zip_dst) as zf:
            zf.printdir()


# NOTE(yasufum): Do not examine if __file__ is '__main__' for considering
# this script can be run from tox.
main()
