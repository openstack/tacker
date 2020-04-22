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
import io
import iso8601
import os
import shutil
import tempfile
import webob
import yaml
import zipfile

from tacker.api.vnfpkgm.v1.router import VnfpkgmAPIRouter
from tacker import context
from tacker.db.db_sqlalchemy import models
from tacker.objects import vnf_package as vnf_package_obj
from tacker.tests import constants
from tacker.tests import uuidsentinel
from tacker import wsgi


VNFPACKAGE_RESPONSE = {'_links': {
    'packageContent': {
        'href':
            '/vnfpkgm/v1/vnf_packages/'
            'f26f181d-7891-4720-b022-b074ec1733ef/package_content'},
    'self': {
        'href':
            '/vnfpkgm/v1/vnf_packages/'
            'f26f181d-7891-4720-b022-b074ec1733ef'},
},
    'id': 'f26f181d-7891-4720-b022-b074ec1733ef',
    'onboardingState': 'CREATED',
    'operationalState': 'DISABLED',
    'usageState': 'NOT_IN_USE',
    'userDefinedData': {'abc': 'xyz'}
}

VNFPACKAGE_INDEX_RESPONSE = {'vnf_packages': [{'_links': {
    'packageContent': {
        'href':
            '/vnfpkgm/v1/vnf_packages/'
            'f26f181d-7891-4720-b022-b074ec1733ef/package_content'},
    'self': {
        'href': '/vnfpkgm/v1/vnf_packages/'
                'f26f181d-7891-4720-b022-b074ec1733ef'}},
    'id': 'f26f181d-7891-4720-b022-b074ec1733ef',
    'onboardingState': 'CREATED',
    'operationalState': 'DISABLED',
    'usageState': 'NOT_IN_USE',
    'userDefinedData': {}}]
}


def fake_vnf_package(**updates):
    vnf_package = {
        'algorithm': None,
        'deleted': False,
        'deleted_at': None,
        'updated_at': None,
        'created_at': datetime.datetime(1900, 1, 1, 1, 1, 1,
                                        tzinfo=iso8601.UTC),
        'hash': None,
        'location_glance_store': None,
        'onboarding_state': 'CREATED',
        'operational_state': 'DISABLED',
        'tenant_id': uuidsentinel.tenant_id,
        'usage_state': 'NOT_IN_USE',
        'user_data': {'abc': 'xyz'},
        'id': constants.UUID,
    }

    if updates:
        vnf_package.update(updates)

    return vnf_package


class InjectContext(wsgi.Middleware):
    """Add a 'tacker.context' to WSGI environ."""

    def __init__(self, context, *args, **kwargs):
        self.context = context
        super(InjectContext, self).__init__(*args, **kwargs)

    @webob.dec.wsgify(RequestClass=wsgi.Request)
    def __call__(self, req):
        req.environ['tacker.context'] = self.context
        return self.application


def fake_vnf_package_user_data(**updates):
    vnf_package_user_data = {
        'key': 'key',
        'value': 'value',
        'package_uuid': constants.UUID,
        'id': constants.UUID,
    }

    if updates:
        vnf_package_user_data.update(updates)

    return vnf_package_user_data


def return_vnf_package_user_data(**updates):
    model_obj = models.VnfPackageUserData()
    model_obj.update(fake_vnf_package_user_data(**updates))
    return model_obj


def return_vnf_package(onboarded=False, **updates):
    model_obj = models.VnfPackage()
    if 'user_data' in updates:
        metadata = []
        for key, value in updates.pop('user_data').items():
            vnf_package_user_data = return_vnf_package_user_data(
                **{'key': key, 'value': value})
            metadata.extend([vnf_package_user_data])
        model_obj._metadata = metadata

    if onboarded:
        updates = {'onboarding_state': 'ONBOARDED',
                   'operational_state': 'ENABLED',
                   'algorithm': 'test',
                   'hash': 'test',
                   'location_glance_store': 'file:test/path/pkg-uuid',
                   'updated_at': datetime.datetime(
                       1900, 1, 1, 1, 1, 1, tzinfo=iso8601.UTC)}
        model_obj.update(fake_vnf_package(**updates))
    else:
        model_obj.update(fake_vnf_package(**updates))

    return model_obj


def return_vnfpkg_obj(onboarded=False, **updates):
    vnf_package = vnf_package_obj.VnfPackage._from_db_object(
        context, vnf_package_obj.VnfPackage(),
        return_vnf_package(onboarded=onboarded, **updates),
        expected_attrs=None)
    return vnf_package


def return_vnf_package_list():
    vnf_package = return_vnfpkg_obj()
    return [vnf_package]


def wsgi_app_v1(fake_auth_context=None):
    inner_app_v1 = VnfpkgmAPIRouter()
    if fake_auth_context is not None:
        ctxt = fake_auth_context
    else:
        ctxt = context.ContextBase(uuidsentinel.user_id,
                                   uuidsentinel.project_id, is_admin=True)
    api_v1 = InjectContext(ctxt, inner_app_v1)
    return api_v1


def return_vnfd_data(multiple_yaml_files=True):
    base_path = os.path.dirname(os.path.abspath(__file__))
    sample_vnf_package_zip = os.path.join(
        base_path, "../../etc/samples/sample_vnf_package_csar.zip")

    csar_temp_dir = tempfile.mkdtemp()

    with zipfile.ZipFile(sample_vnf_package_zip, 'r') as zf:
        zf.extractall(csar_temp_dir)

    file_names = ['Definitions/etsi_nfv_sol001_vnfd_types.yaml']
    if multiple_yaml_files:
        file_names.extend(['TOSCA-Metadata/TOSCA.meta',
                           'Definitions/helloworld3_types.yaml',
                           'Definitions/helloworld3_df_simple.yaml',
                           'Definitions/helloworld3_top.vnfd.yaml',
                           'Definitions/etsi_nfv_sol001_common_types.yaml'])
    file_path_and_data = {}
    for file_name in file_names:
        file_path_and_data.update({file_name: yaml.dump(yaml.safe_load(
            io.open(os.path.join(csar_temp_dir, file_name))))})

    shutil.rmtree(csar_temp_dir)
    return file_path_and_data
