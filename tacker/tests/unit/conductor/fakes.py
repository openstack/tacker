# Copyright (C) 2019 NTT DATA
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

import io
import os
from oslo_config import cfg
import shutil
import tempfile
import yaml
import zipfile

from tacker.tests import uuidsentinel


VNF_UPLOAD_VNF_PACKAGE_CONTENT = {
    'algorithm': 'sha512', 'created_at': '2019-08-16T06:57:09Z',
    'deleted': False, 'deleted_at': None,
    'hash': 'ce48b8ba15bfb060fb70471cf955bef433e4513973b4bac42b37c36f57357dc35'
            'bf788c16545d3a59781914adf19fca26d6984583b7739e55c447383d774356a',
    'id': uuidsentinel.tenant_id,
    'location_glance_store': 'file:///var/lib/glance/images/'
                             'd617ea52-b16b-417e-a68c-08dfb69aab9e',
    'onboarding_state': 'PROCESSING', 'operational_state': 'DISABLED',
    'tenant_id': uuidsentinel.tenant_id,
    'updated_at': '2019-08-16T06:57:30Z',
    'usage_state': 'NOT_IN_USE', 'user_data': {'abc': 'xyz'}}

VNF_DATA = {
    'created_at': '2019-08-16T06:57:09Z',
    'deleted': False, 'deleted_at': None,
    'id': uuidsentinel.id,
    'onboarding_state': 'UPLOADING',
    'operational_state': 'DISABLED',
    'tenant_id': uuidsentinel.tenant_id,
    'updated_at': '2019-08-16T06:57:30Z',
    'usage_state': 'NOT_IN_USE',
    'user_data': {'abc': 'xyz'}
}

VNF_PACKAGE_DATA = {'algorithm': None, 'hash': None,
                    'location_glance_store': None,
                    'onboarding_state': 'CREATED',
                    'operational_state': 'DISABLED',
                    'tenant_id': uuidsentinel.tenant_id,
                    'usage_state': 'NOT_IN_USE',
                    'user_data': {'abc': 'xyz'}
                    }


def make_vnfd_files_list(csar_path):
    files_list = []
    # Checking for directory exist
    if not os.path.isdir(csar_path):
        return
    ext = ['.yaml', '.meta']
    for _, _, files in os.walk(csar_path):
        for file in files:
            if file.endswith(tuple(ext)):
                files_list.append(file)

    return files_list


def create_fake_csar_dir(vnf_package_id, single_yaml_csar=False):
    base_path = os.path.dirname(os.path.abspath(__file__))
    csar_file = ('sample_vnfpkg_no_meta_single_vnfd.zip' if single_yaml_csar
                 else 'sample_vnf_package_csar.zip')
    sample_vnf_package_zip = os.path.join(base_path, "../../etc/samples",
                                          csar_file)
    tmpdir = tempfile.mkdtemp()
    fake_csar = os.path.join('/tmp/', vnf_package_id)
    os.rename(tmpdir, fake_csar)

    with zipfile.ZipFile(sample_vnf_package_zip, 'r') as zf:
        zf.extractall(fake_csar)
    cfg.CONF.set_override('vnf_package_csar_path', '/tmp',
                          group='vnf_package')
    return fake_csar


def get_expected_vnfd_data():
    base_path = os.path.dirname(os.path.abspath(__file__))
    sample_vnf_package_zip = os.path.join(
        base_path, "../../etc/samples/sample_vnf_package_csar.zip")

    csar_temp_dir = tempfile.mkdtemp()

    with zipfile.ZipFile(sample_vnf_package_zip, 'r') as zf:
        zf.extractall(csar_temp_dir)

    file_names = ['TOSCA-Metadata/TOSCA.meta',
                  'Definitions/etsi_nfv_sol001_vnfd_types.yaml',
                  'Definitions/helloworld3_types.yaml',
                  'Definitions/helloworld3_df_simple.yaml',
                  'Definitions/helloworld3_top.vnfd.yaml',
                  'Definitions/etsi_nfv_sol001_common_types.yaml']
    file_path_and_data = {}
    for file_name in file_names:
        file_path_and_data.update({file_name: yaml.dump(yaml.safe_load(
            io.open(os.path.join(csar_temp_dir, file_name))))})

    shutil.rmtree(csar_temp_dir)
    return file_path_and_data
