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


from copy import deepcopy
import datetime
import iso8601
import os
import shutil
import uuid
import webob
import yaml

from tacker.api.vnfpkgm.v1.router import VnfpkgmAPIRouter
from tacker import context
from tacker.objects import vnf_artifact as vnf_artifact_obj
from tacker.objects import vnf_deployment_flavour as vnf_deployment_flavour_obj
from tacker.objects import vnf_package as vnf_package_obj
from tacker.objects import vnf_package_vnfd as vnf_package_vnfd_obj
from tacker.objects import vnf_software_image as vnf_software_image_obj
from tacker.tests import constants
from tacker.tests import utils
from tacker.tests import uuidsentinel
from tacker import wsgi


VNFPACKAGE_RESPONSE = {
    '_links': {
        'packageContent': {
            'href': '/vnfpkgm/v1/vnf_packages/'
                    'f26f181d-7891-4720-b022-b074ec1733ef/package_content'},
            'self': {
                'href': '/vnfpkgm/v1/vnf_packages/'
                        'f26f181d-7891-4720-b022-b074ec1733ef'}
    },
    'checksum': {
        'algorithm': 'fake vnf package algorithm',
        'hash': 'fake vnf package hash'
    },
    'id': 'f26f181d-7891-4720-b022-b074ec1733ef',
    'onboardingState': 'ONBOARDED',
    'operationalState': 'ENABLED',
    'usageState': 'NOT_IN_USE',
    'vnfProductName': 'fake vnf product name',
    'vnfProvider': 'fake vnf provider',
    'vnfSoftwareVersion': 'fake vnf software version',
    'vnfdId': uuidsentinel.vnfd_id,
    'vnfdVersion': 'fake vnfd version',
    'userDefinedData': {'key1': 'value1', 'key2': 'value2'},
    'softwareImages': [{
        'checksum': {'algorithm': 'fake-algorithm',
                     'hash': 'fake software image hash'},
        'containerFormat': 'bare',
        'createdAt': datetime.datetime(1900, 1, 1, 1, 1, 1,
                                       tzinfo=iso8601.UTC),
        'diskFormat': 'qcow2',
        'id': 'fake_software_image_id',
        'imagePath': 'fake image path',
        'minDisk': 1,
        'minRam': 0,
        'name': 'fake software image name',
        'provider': 'fake provider',
        'size': 1,
        'userMetadata': {'key3': 'value3', 'key4': 'value4'},
        'version': '11.22.33'
    }],
    'additionalArtifacts': [{
        'artifactPath': 'Scripts/install.sh',
        'metadata': {},
        'checksum': {
            'algorithm': 'SHA-256',
            'hash': '27bbdb25d8f4ed6d07d6f6581b86515e8b2f005'
                    '9b236ef7b6f50d6674b34f02a'
        }
    }],
}

VNFPACKAGE_INDEX_RESPONSE = [VNFPACKAGE_RESPONSE]


def index_response(remove_attrs=None, vnf_package_updates=None):
    # Returns VNFPACKAGE_INDEX_RESPONSE
    # parameter remove_attrs is a list of attribute names
    # to be removed before returning the response
    if not remove_attrs:
        return VNFPACKAGE_INDEX_RESPONSE
    vnf_package = deepcopy(VNFPACKAGE_RESPONSE)
    for attr in remove_attrs:
        vnf_package.pop(attr, None)
    if vnf_package_updates:
        vnf_package.update(vnf_package_updates)
    return [vnf_package]


def _fake_software_image(updates=None):
    software_image = {
        'id': uuidsentinel.software_image_id,
        'disk_format': 'qcow2',
        'min_ram': 0,
        'min_disk': 1,
        'container_format': 'bare',
        'provider': 'fake provider',
        'image_path': 'fake image path',
        'software_image_id': 'fake_software_image_id',
        'size': 1,
        'name': 'fake software image name',
        'hash': 'fake software image hash',
        'version': '11.22.33',
        'algorithm': 'fake-algorithm',
        'metadata': {'key3': 'value3', 'key4': 'value4'},
        'created_at': datetime.datetime(1900, 1, 1, 1, 1, 1,
                                        tzinfo=iso8601.UTC),
    }
    if updates:
        software_image.update(updates)
    return software_image


def return_software_image(updates=None):
    software_image = _fake_software_image(updates)
    obj = vnf_software_image_obj.VnfSoftwareImage(**software_image)
    return obj


def _fake_deployment_flavour(updates=None):
    deployment_flavour = {
        'id': uuidsentinel.deployment_flavour_id,
        'package_uuid': 'f26f181d-7891-4720-b022-b074ec1733ef',
        'flavour_id': 'fake flavour id',
        'flavour_description': 'fake flavour description',
        'instantiation_levels': {"level1": 1, "level2": 2}
    }
    if updates:
        deployment_flavour.update(updates)
    return deployment_flavour


def _return_deployment_flavour(deployment_flavour_updates=None,
        software_image_updates=None):
    flavour = _fake_deployment_flavour(deployment_flavour_updates)
    obj = vnf_deployment_flavour_obj.VnfDeploymentFlavour(**flavour)

    software_image = return_software_image(software_image_updates)
    software_image_list = vnf_software_image_obj.VnfSoftwareImagesList()
    software_image_list.objects = [software_image]

    obj.software_images = software_image_list
    return obj


def _fake_vnfd(updates=None):
    vnfd = {
        'id': uuidsentinel.vnfd_unused_id,
        'package_uuid': 'f26f181d-7891-4720-b022-b074ec1733ef',
        'vnfd_id': uuidsentinel.vnfd_id,
        'vnf_provider': 'fake vnf provider',
        'vnf_product_name': 'fake vnf product name',
        'vnfd_version': 'fake vnfd version',
        'vnf_software_version': 'fake vnf software version'
    }
    if updates:
        vnfd.update(updates)
    return vnfd


def _return_vnfd(updates=None):
    vnfd = _fake_vnfd(updates)
    return vnf_package_vnfd_obj.VnfPackageVnfd(**vnfd)


def _fake_artifact(updates=None):
    artifact = {
        'id': uuidsentinel.vnf_artifact_id,
        'package_uuid': 'f26f181d-7891-4720-b022-b074ec1733ef',
        'artifact_path': 'Scripts/install.sh',
        'metadata': {},
        'algorithm': 'SHA-256',
        'hash': '27bbdb25d8f4ed6d07d6f6581b86515e8b2f0059b236ef'
                '7b6f50d6674b34f02a'}
    if updates:
        artifact.update(updates)
    return artifact


def _return_artifact(update=None):
    artifact = _fake_artifact(update)
    return vnf_artifact_obj.VnfPackageArtifactInfo(**artifact)


def _return_artifact_list(update=None):
    artifact_obj = _return_artifact(update)
    artifact_list = vnf_artifact_obj.VnfPackageArtifactInfoList()
    artifact_list.objects = [artifact_obj]
    return artifact_list


def fake_vnf_package(updates=None):
    vnf_package = {
        'id': constants.UUID,
        'hash': 'fake vnf package hash',
        'algorithm': 'fake vnf package algorithm',
        'location_glance_store': 'fake location',
        'onboarding_state': 'ONBOARDED',
        'operational_state': 'ENABLED',
        'tenant_id': uuidsentinel.tenant_id,
        'usage_state': 'NOT_IN_USE',
        'user_data': {'key1': 'value1', 'key2': 'value2'},
    }
    if updates:
        vnf_package.update(updates)
    return vnf_package


def return_vnfpkg_obj(
        vnf_package_updates=None,
        vnfd_updates=None,
        deployment_flavour_updates=None,
        software_image_updates=None,
        vnf_artifact_updates=None):
    vnf_package = fake_vnf_package(vnf_package_updates)
    obj = vnf_package_obj.VnfPackage(**vnf_package)
    obj.vnfd = _return_vnfd(vnfd_updates)

    deployment_flavour = _return_deployment_flavour(
        deployment_flavour_updates, software_image_updates)
    flavour_list = vnf_deployment_flavour_obj.VnfDeploymentFlavoursList()
    flavour_list.objects = [deployment_flavour]
    obj.vnf_deployment_flavours = flavour_list
    obj.vnf_artifacts = _return_artifact_list(vnf_artifact_updates)
    return obj


def return_vnf_package_list():
    vnf_package = return_vnfpkg_obj()
    return [vnf_package]


class InjectContext(wsgi.Middleware):
    """Add a 'tacker.context' to WSGI environ."""

    def __init__(self, context, *args, **kwargs):
        self.context = context
        super(InjectContext, self).__init__(*args, **kwargs)

    @webob.dec.wsgify(RequestClass=wsgi.Request)
    def __call__(self, req):
        req.environ['tacker.context'] = self.context
        return self.application


def wsgi_app_v1(fake_auth_context=None):
    inner_app_v1 = VnfpkgmAPIRouter()
    if fake_auth_context is not None:
        ctxt = fake_auth_context
    else:
        ctxt = context.ContextBase(uuidsentinel.user_id,
                                   uuidsentinel.project_id, is_admin=True)
    api_v1 = InjectContext(ctxt, inner_app_v1)
    return api_v1


def return_vnfd_data(csar_without_tosca_meta=False):
    csar_dir = ('sample_vnfpkg_no_meta_single_vnfd'
                if csar_without_tosca_meta else 'vnfpkgm1')
    unique_name = str(uuid.uuid4())
    csar_temp_dir = os.path.join('/tmp', unique_name)
    utils.copy_artifact_files(
        csar_temp_dir, csar_dir, csar_without_tosca_meta,
        read_vnfd_only=True)
    if csar_without_tosca_meta:
        file_names = ['vnfd_helloworld_single.yaml']
    else:
        file_names = ['TOSCA-Metadata/TOSCA.meta',
                      'Definitions/helloworld3_types.yaml',
                      'Definitions/helloworld3_df_simple.yaml',
                      'Definitions/helloworld3_top.vnfd.yaml',
                      'Definitions/etsi_nfv_sol001_common_types.yaml',
                      'Definitions/etsi_nfv_sol001_vnfd_types.yaml']
    file_path_and_data = {}
    for file_name in file_names:
        with open(os.path.join(csar_temp_dir, file_name)) as f:
            file_path_and_data.update({file_name: yaml.dump(
                yaml.safe_load(f))})

    shutil.rmtree(csar_temp_dir)
    return file_path_and_data
