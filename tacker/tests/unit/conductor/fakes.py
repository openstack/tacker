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

import os
from oslo_config import cfg
import shutil
import tempfile
import uuid
import yaml
import zipfile

from tacker.tests import utils
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


def create_fake_csar_dir(vnf_package_id, temp_dir,
                         csar_without_tosca_meta=False):
    csar_dir = ('sample_vnfpkg_no_meta_single_vnfd' if csar_without_tosca_meta
                else 'sample_vnfpkg_tosca_vnfd')
    fake_csar = os.path.join(temp_dir, vnf_package_id)
    cfg.CONF.set_override('vnf_package_csar_path', temp_dir,
                          group='vnf_package')
    utils.copy_csar_files(fake_csar, csar_dir, csar_without_tosca_meta)

    return fake_csar


def get_expected_vnfd_data(zip_file=None):
    if zip_file:
        csar_temp_dir = tempfile.mkdtemp()
        with zipfile.ZipFile(zip_file, 'r') as zf:
            zf.extractall(csar_temp_dir)
    else:
        unique_name = str(uuid.uuid4())
        csar_temp_dir = os.path.join('/tmp', unique_name)
        utils.copy_csar_files(csar_temp_dir, 'sample_vnfpkg_tosca_vnfd',
                              read_vnfd_only=True)

    file_names = ['TOSCA-Metadata/TOSCA.meta',
                  'Definitions/etsi_nfv_sol001_vnfd_types.yaml',
                  'Definitions/helloworld3_types.yaml',
                  'Definitions/helloworld3_df_simple.yaml',
                  'Definitions/helloworld3_top.vnfd.yaml',
                  'Definitions/etsi_nfv_sol001_common_types.yaml']
    file_path_and_data = {}
    for file_name in file_names:
        with open(os.path.join(csar_temp_dir, file_name)) as f:
            file_path_and_data.update({file_name: yaml.dump(
                yaml.safe_load(f))})

    shutil.rmtree(csar_temp_dir)
    return file_path_and_data
