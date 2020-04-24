# Copyright 2015 Brocade Communications System, Inc.
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

import os
import tempfile
import yaml
import zipfile

from oslo_utils import uuidutils


def read_file(input_file):
    yaml_file = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                             'etc/samples/' + str(input_file)))
    with open(yaml_file, 'r') as f:
        return f.read()


def _update_unique_id_in_yaml(data, uid):
    try:
        prop = data['topology_template']['node_templates']['VNF'][
            'properties']
        if (prop.get('descriptor_id', None)):
            prop['descriptor_id'] = uid
    except KeyError:
        # Let's check for 'node_types'
        pass

    if not data.get('node_types', None):
        return

    for ntype in data['node_types'].values():
        if ntype['derived_from'] != 'tosca.nodes.nfv.VNF':
            continue
        try:
            desc_id = ntype['properties']['descriptor_id']
            if desc_id.get('constraints', None):
                for constraint in desc_id.get('constraints'):
                    if constraint.get('valid_values', None):
                        constraint['valid_values'] = [uid]
            if desc_id.get('default', None):
                desc_id['default'] = uid
        except KeyError:
            # Let's check next node_type
            pass


def create_csar_with_unique_vnfd_id(csar_dir):
    """Create CSAR file from a directory structure

    For various tests it is necessary to have a CSAR having unique vnfd id.
    This function reads a directory structure, updates vnfd id in yaml files
    and creates a temporary CSAR zip file.

    :returns:
        - csar_file_name
        - vnfd_id
    """
    unique_id = uuidutils.generate_uuid()
    tempfd, tempname = tempfile.mkstemp(suffix=".zip",
        dir=os.path.dirname(csar_dir))
    os.close(tempfd)
    common_dir = os.path.join(csar_dir, "../common/")
    zcsar = zipfile.ZipFile(tempname, 'w')

    for (dpath, _, fnames) in os.walk(csar_dir):
        if not fnames:
            continue
        for fname in fnames:
            src_file = os.path.join(dpath, fname)
            dst_file = os.path.relpath(os.path.join(dpath, fname), csar_dir)
            if fname.endswith('.yaml') or fname.endswith('.yml'):
                with open(src_file, 'rb') as yfile:
                    data = yaml.safe_load(yfile)
                    _update_unique_id_in_yaml(data, unique_id)
                    zcsar.writestr(dst_file, yaml.dump(
                        data, default_flow_style=False, allow_unicode=True))
            else:
                zcsar.write(src_file, dst_file)

    for (dpath, _, fnames) in os.walk(common_dir):
        if not fnames:
            continue
        for fname in fnames:
            src_file = os.path.join(dpath, fname)
            dst_file = os.path.relpath(os.path.join(dpath, fname), common_dir)
            zcsar.write(src_file, dst_file)

    zcsar.close()
    return tempname, unique_id
