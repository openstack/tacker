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

import datetime
import iso8601
import os
import shutil
from tacker import objects
from tacker.objects import fields
from tacker.tests import constants
import tempfile
import uuid
import yaml
import zipfile

from oslo_config import cfg

from tacker.db.db_sqlalchemy import models
from tacker.objects import scale_vnf_request
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


def get_vnf_package_vnfd():
    return {
        "id": uuidsentinel.vnfd_id,
        "vnf_provider": "test vnf provider",
        "vnf_product_name": "Sample VNF",
        "vnf_software_version": "1.0",
        "vnfd_version": "1.0",
        "name": 'Sample VNF Instance',
    }


def get_lcm_op_occs_data():
    return {
        "id": uuidsentinel.lcm_op_occs_id,
        "tenant_id": uuidsentinel.tenant_id,
        'operation_state': 'PROCESSING',
        'state_entered_time':
        datetime.datetime(1900, 1, 1, 1, 1, 1,
                          tzinfo=iso8601.UTC),
        'start_time': datetime.datetime(1900, 1, 1, 1, 1, 1,
                                        tzinfo=iso8601.UTC),
        'operation': 'MODIFY_INFO',
        'is_automatic_invocation': 0,
        'is_cancel_pending': 0,
    }


def get_vnf_lcm_subscriptions():
    subscription_id = uuidsentinel.subscription_id
    return {
        "id": subscription_id.encode(),
        "callback_uri": b'http://localhost:9890/'
    }


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


def fake_vnf_package_vnfd_model_dict(**updates):
    vnfd = {
        'package_uuid': uuidsentinel.package_uuid,
        'deleted': False,
        'deleted_at': None,
        'updated_at': None,
        'created_at': datetime.datetime(2020, 1, 1, 1, 1, 1,
                                        tzinfo=iso8601.UTC),
        'vnf_product_name': 'Sample VNF',
        'vnf_provider': 'test vnf provider',
        'vnf_software_version': '1.0',
        'vnfd_id': uuidsentinel.vnfd_id,
        'vnfd_version': '1.0',
        'id': constants.UUID,
    }

    if updates:
        vnfd.update(updates)

    return vnfd


def return_vnf_package_vnfd():
    model_obj = models.VnfPackageVnfd()
    model_obj.update(fake_vnf_package_vnfd_model_dict())
    return model_obj


def _model_non_instantiated_vnf_instance(**updates):
    vnf_instance = {
        'created_at': datetime.datetime(2020, 1, 1, 1, 1, 1,
                                        tzinfo=iso8601.UTC),
        'deleted': False,
        'deleted_at': None,
        'id': uuidsentinel.vnf_instance_id,
        'instantiated_vnf_info': None,
        'instantiation_state': fields.VnfInstanceState.NOT_INSTANTIATED,
        'updated_at': None,
        'vim_connection_info': [],
        'vnf_instance_description': 'Vnf instance description',
        'vnf_instance_name': 'Vnf instance name',
        'vnf_product_name': 'Sample VNF',
        'vnf_provider': 'Vnf provider',
        'vnf_software_version': '1.0',
        'tenant_id': uuidsentinel.tenant_id,
        'vnfd_id': uuidsentinel.vnfd_id,
        'vnfd_version': '1.0',
        'vnfPkgId': uuidsentinel.vnf_pkg_id}

    if updates:
        vnf_instance.update(**updates)

    return vnf_instance


def return_vnf_instance(
        instantiated_state=fields.VnfInstanceState.NOT_INSTANTIATED,
        scale_status=None,
        **updates):

    if instantiated_state == fields.VnfInstanceState.NOT_INSTANTIATED:
        data = _model_non_instantiated_vnf_instance(**updates)
        data['instantiation_state'] = instantiated_state
        vnf_instance_obj = objects.VnfInstance(**data)

    elif scale_status:
        data = _model_non_instantiated_vnf_instance(**updates)
        data['instantiation_state'] = instantiated_state
        vnf_instance_obj = objects.VnfInstance(**data)

        get_instantiated_vnf_info = {
            'flavour_id': uuidsentinel.flavour_id,
            'vnf_state': 'STARTED',
            'instance_id': uuidsentinel.instance_id
        }
        instantiated_vnf_info = get_instantiated_vnf_info

        s_status = {"aspect_id": "SP1", "scale_level": 1}
        scale_status = objects.ScaleInfo(**s_status)

        instantiated_vnf_info.update(
            {"ext_cp_info": [],
             'ext_virtual_link_info': [],
             'ext_managed_virtual_link_info': [],
             'vnfc_resource_info': [],
             'vnf_virtual_link_resource_info': [],
             'virtual_storage_resource_info': [],
             "flavour_id": "simple",
             "scale_status": [scale_status],
             "vnf_instance_id": "171f3af2-a753-468a-b5a7-e3e048160a79",
             "additional_params": {"key": "value"},
             'vnf_state': "STARTED"})
        info_data = objects.InstantiatedVnfInfo(**instantiated_vnf_info)

        vnf_instance_obj.instantiated_vnf_info = info_data
    else:
        data = _model_non_instantiated_vnf_instance(**updates)
        data['instantiation_state'] = instantiated_state
        vnf_instance_obj = objects.VnfInstance(**data)
        inst_vnf_info = objects.InstantiatedVnfInfo.obj_from_primitive({
            "ext_cp_info": [],
            'ext_virtual_link_info': [],
            'ext_managed_virtual_link_info': [],
            'vnfc_resource_info': [],
            'vnf_virtual_link_resource_info': [],
            'virtual_storage_resource_info': [],
            "flavour_id": "simple",
            "additional_params": {"key": "value"},
            'vnf_state': "STARTED"}, None)

        vnf_instance_obj.instantiated_vnf_info = inst_vnf_info

    return vnf_instance_obj


def _get_vnf(**updates):
    vnf_data = {
        'tenant_id': uuidsentinel.tenant_id,
        'name': "fake_name",
        'vnfd_id': uuidsentinel.vnfd_id,
        'vnf_instance_id': uuidsentinel.instance_id,
        'mgmt_ip_address': "fake_mgmt_ip_address",
        'status': 'ACTIVE',
        'description': 'fake_description',
        'placement_attr': 'fake_placement_attr',
        'vim_id': 'uuidsentinel.vim_id',
        'error_reason': 'fake_error_reason',
    }

    if updates:
        vnf_data.update(**updates)

    return vnf_data


def scale_request(type, number_of_steps):
    scale_request_data = {
        'type': type,
        'aspect_id': "SP1",
        'number_of_steps': number_of_steps,
        'scale_level': 1,
        'additional_params': {"test": "test_value"},
    }
    scale_request = scale_vnf_request.ScaleVnfRequest(**scale_request_data)

    return scale_request
