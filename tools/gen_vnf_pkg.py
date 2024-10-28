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
import yaml
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

# Dummy params for default value.
OS_AUTH_URL = "http://localhost/identity/v3"
K8S_AUTH_URL = "https://127.0.0.1:6443"
K8S_BEARER_TOKEN = "your_k8s_cluster_bearer_token"
K8S_SSL_CA_CERT = "k8s_ssl_ca_cert"


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

    parser.add_argument('-c', '--vim-config',
                        help='Path of VIM config file for specifying the VIM',
                        type=str, metavar='VIM_CONF')

    parser.add_argument('--vim-id',
                        help='VIM ID (Only for OpenStack and overwritten'
                             'by `--vim-config`)',
                        type=str, metavar='VIM_ID')

    parser.add_argument('--vim-name',
                        help='Name of VIM (Only for OpenStack and overwritten'
                             'by `--vim-config`)',
                        type=str, metavar='VIM_NAME')

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


def print_result(zip_fn, req_files, zip_path):
    print(f"VNF package: {zip_fn}")
    print("Request files: {}".format(", ".join(req_files)))
    print("Contents of the VNF package:")
    with zipfile.ZipFile(zip_path) as zf:
        zf.printdir()


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


def get_vim_config(fpath):
    """Get VIM info from a config file"""

    if fpath is not None:
        # Used for k8s VIM
        c_begin = "-----BEGIN CERTIFICATE-----"
        c_end = "-----END CERTIFICATE-----"

        with open(fpath) as f:
            y = yaml.safe_load(f)

        # Need to terminate each line with a new line char
        if ("ssl_ca_cert" in y.keys()) and (y["ssl_ca_cert"] is not None):
            y["ssl_ca_cert"] = y["ssl_ca_cert"].replace(
                    c_begin, "").replace(c_end, "")
            y["ssl_ca_cert"] = y["ssl_ca_cert"].replace(" ", "\n")
            y["ssl_ca_cert"] = "{}{}{}".format(
                    c_begin, y["ssl_ca_cert"], c_end)
        return y
    return {}


def get_vim_info(vim_name=None, vim_id=None):
    """Get VIM info from its ID or name

    Only used for OpenStack VIM. Get the info from `openstack vim show`
    command.
    """

    cmd_vim_show = ["openstack", "vim", "show", "-f", "json"]
    if vim_id is not None:
        cmd_vim_show.append(vim_id)
    elif vim_name is not None:
        cmd_vim_show.append(vim_name)
    else:
        return {}
    return json.loads(
        subprocess.run(cmd_vim_show, capture_output=True).stdout)


def has_unsupported_args(args):
    # TODO(yasufum): show which arg isn't supported.
    flg = False
    if args.type == VIM_OPENSTACK or args.type == VIM_OPENSTACK.lower():
        pass
    # '--vim-id' and '--vim-name' aren't supported for the two types.
    elif (args.type == VIM_KUBERNETES or args.type == VIM_KUBERNETES.lower()
            or args.type == VIM_HELM or args.type == VIM_HELM.lower()):
        if (args.vim_id is not None) or (args.vim_name is not None):
            flg = True
    return flg


def main():

    args = get_args()

    if has_all_req_networks() is False:
        print("Error: Create all the required nets and subnets below "
              "before running this script.")
        pprint.pprint(REQ_NWS, indent=2)
        exit()

    if args.type == VIM_OPENSTACK or args.type == VIM_OPENSTACK.lower():
        if has_unsupported_args(args):
            print("WARN: Some option VIM config isn't supported for"
                  "this VIM type. So, default values are used instead.")

        if ask_overwrite(STANDARD_OUTPUT) is not True:
            print("Skip to generate package.")
            exit()
        os.makedirs(STANDARD_OUTPUT, exist_ok=True)

        vnfd_id, zip_src = zipgen.userdata_standard()
        zip_fn = zip_src.rsplit('/', 1)[1]
        zip_dst = f"{STANDARD_OUTPUT}/{zip_fn}"

        print(f"Generating package and request files in '{STANDARD_OUTPUT}/' ...")

        shutil.move(os.path.abspath(zip_src), os.path.abspath(zip_dst))
        shutil.rmtree(zip_src.rsplit('/', 1)[0])

        nets, subnets = req_nw_names()
        net_ids = utils.get_network_ids(nets)
        subnet_ids = utils.get_subnet_ids(subnets)

        vim_info = {}
        if args.vim_config is not None:
            vim_info = get_vim_config(args.vim_config)
            if (args.vim_name is not None) or (args.vim_id is not None):
                vim_info["id"] = get_vim_info(args.vim_name, args.vim_id)["id"]

        elif (args.vim_name is not None) or (args.vim_id is not None):
            vim_info = get_vim_info(args.vim_name, args.vim_id)

        if (vim_info is not None) and ("auth_url" in vim_info):
            os_auth_url = vim_info["auth_url"]
        elif "OS_AUTH_URL" in os.environ:
            os_auth_url = os.environ["OS_AUTH_URL"]
        else:
            os_auth_url = OS_AUTH_URL

        def _instantiate_req():
            "Update VIM info from paramgen script for your env"

            res = paramgen.sample3_instantiate(net_ids, subnet_ids, os_auth_url)
            vim1 = res["vimConnectionInfo"]["vim1"]

            if vim_info is not None and "id" in vim_info.keys():
                vim1["vimId"] = vim_info["id"]
            vim1["vimType"] = VIM_OPENSTACK
            return res

        req_files = {
            "create_req": paramgen.sample3_create(vnfd_id),
            "terminate_req": paramgen.sample3_terminate(),
            "instantiate_req": _instantiate_req(),
            "scale_out_req": paramgen.sample3_scale_out(),
            "scale_in_req": paramgen.sample3_scale_in(),
            # TODO(yasufum): support replacing vnfcInstanceId
            "heal_req": paramgen.sample3_heal(),
            "change_ext_conn_req": paramgen.sample3_change_ext_conn(net_ids),
            # TODO(yasufum): support replacing vnfdId
            "update_req": paramgen.sample3_update_vnf_vnfd_id("replace real vnfd id")
            }

        for fn in req_files.keys():
            with open(f"{STANDARD_OUTPUT}/{fn}", "w") as f:
                f.write(json.dumps(req_files[fn], indent=2))

        print_result(zip_fn, req_files.keys(), zip_dst)

    elif args.type == VIM_KUBERNETES or args.type == VIM_KUBERNETES.lower():
        if has_unsupported_args(args):
            print("WARN: Some option VIM config isn't supported for"
                  "this VIM type. So, default values are used instead.")

        if ask_overwrite(K8S_OUTPUT) is not True:
            print("Skip to generate package.")
            exit()
        os.makedirs(K8S_OUTPUT, exist_ok=True)

        vnfd_id, zip_src = k8s_zipgen.test_instantiate_cnf_resources()
        zip_fn = zip_src.rsplit('/', 1)[1]
        zip_dst = f"{K8S_OUTPUT}/{zip_fn}"

        print(f"Generating package and request files in '{K8S_OUTPUT}/' ...")

        shutil.move(os.path.abspath(zip_src), os.path.abspath(zip_dst))
        shutil.rmtree(zip_src.rsplit('/', 1)[0])

        vim_info = get_vim_config(args.vim_config)
        if vim_info:
            auth_url = vim_info["auth_url"]
            bearer_token = vim_info["bearer_token"]
            ssl_ca_cert = vim_info["ssl_ca_cert"]
        else:  # Use dummy values instead.
            auth_url = K8S_AUTH_URL
            bearer_token = K8S_BEARER_TOKEN
            ssl_ca_cert = K8S_SSL_CA_CERT

        req_files = {
            "create_req": k8s_paramgen.test_instantiate_cnf_resources_create(vnfd_id),
            "max_sample_instantiate": k8s_paramgen.max_sample_instantiate(
                auth_url, bearer_token, ssl_ca_cert),
            "max_sample_terminate": k8s_paramgen.max_sample_terminate(),
            "max_sample_scale_out": k8s_paramgen.max_sample_scale_out(),
            "max_sample_scale_in": k8s_paramgen.max_sample_scale_in(),
            # TODO(yasufum): support replacing vnfcInstanceId
            "max_sample_heal": k8s_paramgen.max_sample_heal(["replace real vnfc ids"])
            }

        for fn in req_files.keys():
            with open(f"{K8S_OUTPUT}/{fn}", "w", encoding='utf-8') as f:
                f.write(json.dumps(req_files[fn], indent=2))

        print_result(zip_fn, req_files.keys(), zip_dst)

    elif args.type == VIM_HELM or args.type == VIM_HELM.lower():
        if has_unsupported_args(args):
            print("WARN: Some option VIM config isn't supported for"
                  "this VIM type. So, default values are used instead.")

        if ask_overwrite(HELM_OUTPUT) is not True:
            print("Skip to generate package.")
            exit()
        os.makedirs(HELM_OUTPUT, exist_ok=True)

        vnfd_id, zip_src = k8s_zipgen.test_helm_instantiate()
        zip_fn = zip_src.rsplit('/', 1)[1]
        zip_dst = f"{HELM_OUTPUT}/{zip_fn}"

        print(f"Generating package and request files into '{HELM_OUTPUT}/' ...")

        shutil.move(os.path.abspath(zip_src), os.path.abspath(zip_dst))
        shutil.rmtree(zip_src.rsplit('/', 1)[0])

        vim_info = get_vim_config(args.vim_config)
        if vim_info:
            auth_url = vim_info["auth_url"]
            bearer_token = vim_info["bearer_token"]
            ssl_ca_cert = vim_info["ssl_ca_cert"]
        else:  # Use dummy values instead.
            auth_url = K8S_AUTH_URL
            bearer_token = K8S_BEARER_TOKEN
            ssl_ca_cert = K8S_SSL_CA_CERT

        req_files = {
            "create_req": k8s_paramgen.test_helm_instantiate_create(vnfd_id),
            "helm_instantiate_req": k8s_paramgen.helm_instantiate(
                auth_url, bearer_token, ssl_ca_cert),
            "helm_terminate_req": k8s_paramgen.helm_terminate(),
            "helm_scale_out": k8s_paramgen.helm_scale_out(),
            "helm_scale_in": k8s_paramgen.helm_scale_in(),
            # TODO(yasufum): support replacing vnfcInstanceId
            "helm_heal": k8s_paramgen.helm_heal(["replace real vnfc ids"])
            }
        for fn in req_files.keys():
            with open(f"{HELM_OUTPUT}/{fn}", "w", encoding='utf-8') as f:
                f.write(json.dumps(req_files[fn], indent=2))

        print_result(zip_fn, req_files.keys(), zip_dst)


# NOTE(yasufum): Do not examine if __file__ is '__main__' for considering
# this script can be run from tox.
main()
