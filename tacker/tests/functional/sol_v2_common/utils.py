# Copyright (C) 2021 Nippon Telegraph and Telephone Corporation
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

import hashlib
import json
import os
import re
import shutil
import subprocess
import yaml


# vnfdId of samples must be this.
SAMPLE_VNFD_ID = "b1bb0ce7-ebca-4fa7-95ed-4840d7000000"


def make_zip(sample_dir, tmp_dir, vnfd_id, image_path=None,
        userdata_path=None, provider=None, namespace=None, mgmt_driver=None):
    # NOTE: '.zip' will be added by shutil.make_archive
    zip_file_name = os.path.basename(os.path.abspath(sample_dir))
    zip_file_path = os.path.join(tmp_dir, zip_file_name)

    tmp_contents = os.path.join(tmp_dir, "contents")
    shutil.copytree(os.path.join(sample_dir, "contents"), tmp_contents)

    # add common vnfd files
    common_dir = os.path.join(sample_dir, "../common/Definitions/")
    for entry in os.listdir(common_dir):
        shutil.copy(os.path.join(common_dir, entry),
                    os.path.join(tmp_contents, "Definitions"))

    # replace vnfd_id
    def_path = os.path.join(tmp_contents, "Definitions")
    for entry in os.listdir(def_path):
        entry_path = os.path.join(def_path, entry)
        with open(entry_path, 'r') as f:
            content = f.read()
        content = content.replace(SAMPLE_VNFD_ID, vnfd_id)
        with open(entry_path, 'w') as f:
            f.write(content)

    if image_path is not None:
        # mkdir Files/ and copy image_path into it
        file_path = os.path.join(tmp_contents, "Files", "images")
        os.makedirs(file_path)
        shutil.copy(image_path, file_path)

    if userdata_path is not None:
        # mkdir UserData/ and copy userdata_path into it
        file_path = os.path.join(tmp_contents, "UserData")
        os.makedirs(file_path)
        shutil.copy(userdata_path, file_path)

    if provider:
        # replace provider
        def_path = os.path.join(tmp_contents, "Definitions")
        for entry in os.listdir(def_path):
            entry_path = os.path.join(def_path, entry)
            with open(entry_path, 'r') as f:
                data = yaml.safe_load(f)
            _update_provider_in_yaml(data, provider)
            with open(entry_path, 'w') as f:
                yaml.dump(data, f, default_flow_style=False,
                    allow_unicode=True)
    if namespace:
        file_path = os.path.join(
            tmp_contents, "Files", "kubernetes", "namespace.yaml")
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)
        data["metadata"]["name"] = namespace
        with open(file_path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False,
                      allow_unicode=True)
        with open(file_path, 'r') as f:
            content = f.read()
        hash_value = hashlib.sha256(content.encode()).hexdigest()
        tosca_file = os.path.join(tmp_contents, "TOSCA-Metadata", "TOSCA.meta")
        with open(tosca_file, 'rb') as f:
            artifacts_data = f.read()
        artifacts_data_split = re.split(b'\n\n+', artifacts_data)
        artifact_data_strs = []
        for data in artifacts_data_split:
            artifact_data_dict = yaml.safe_load(data)
            if re.findall(b'.?Algorithm:.?|.?Hash:.?', data):
                artifact_file = (artifact_data_dict['Source']
                    if 'Source' in artifact_data_dict.keys()
                    else artifact_data_dict['Name'])
                if artifact_file.endswith('namespace.yaml'):
                    artifact_data_dict['Hash'] = hash_value
            if artifact_data_dict:
                artifact_data_strs.append(
                    yaml.dump(
                        artifact_data_dict,
                        default_flow_style=False,
                        allow_unicode=True))
        with open(tosca_file, 'w') as f:
            f.write('\n'.join(artifact_data_strs))

    if mgmt_driver is not None:
        # mkdir Scripts/ if not exist and copy mgmt_driver_path into it
        file_path = os.path.join(tmp_contents, "Scripts")
        os.makedirs(file_path)
        shutil.copy(mgmt_driver, file_path)

    shutil.make_archive(zip_file_path, "zip", tmp_contents)


def _update_provider_in_yaml(data, provider):
    try:
        prop = data['topology_template']['node_templates']['VNF'][
            'properties']
        if prop.get('provider', None):
            prop['provider'] = provider
    except KeyError:
        # Let's check for 'node_types'
        pass

    if not data.get('node_types', None):
        return

    for ntype in data['node_types'].values():
        if ntype['derived_from'] != 'tosca.nodes.nfv.VNF':
            continue
        try:
            desc_id = ntype['properties']['provider']
            if desc_id.get('constraints', None):
                for constraint in desc_id.get('constraints'):
                    if constraint.get('valid_values', None):
                        constraint['valid_values'] = [provider]
            if desc_id.get('default', None):
                desc_id['default'] = provider
        except KeyError:
            # Let's check next node_type
            pass


def create_network(network):
    # assume OS_* environment variables are already set
    subprocess.run(
        ["openstack", "net", "create", network])


def delete_network(network):
    # assume OS_* environment variables are already set
    subprocess.run(
        ["openstack", "net", "delete", network])


def get_network_ids(networks):
    # assume OS_* environment variables are already set
    net_ids = {}
    for net in networks:
        p = subprocess.run(
            ["openstack", "net", "show", net, "-c", "id", "-f", "json"],
            capture_output=True, encoding='utf-8')
        net_ids[net] = json.loads(p.stdout)['id']
    return net_ids


def create_subnet(subnet, network, sub_range, version):
    # assume OS_* environment variables are already set
    subprocess.run(
        ["openstack", "subnet", "create", subnet, "--network", network,
         "--subnet-range", sub_range, "--ip-version", version])


def get_subnet_ids(subnets):
    # assume OS_* environment variables are already set
    subnet_ids = {}
    for subnet in subnets:
        p = subprocess.run(
            ["openstack", "subnet", "show", subnet, "-c", "id", "-f", "json"],
            capture_output=True, encoding='utf-8')
        subnet_ids[subnet] = json.loads(p.stdout)['id']
    return subnet_ids


def create_port(port, network):
    # assume OS_* environment variables are already set
    subprocess.run(
        ["openstack", "port", "create", port, "--network", network])


def delete_port(port):
    # assume OS_* environment variables are already set
    subprocess.run(
        ["openstack", "port", "delete", port])


def get_port_ids(ports):
    # assume OS_* environment variables are already set
    port_ids = {}
    for port in ports:
        p = subprocess.run(
            ["openstack", "port", "show", port, "-c", "id", "-f", "json"],
            capture_output=True, encoding='utf-8')
        port_ids[port] = json.loads(p.stdout)['id']
    return port_ids
