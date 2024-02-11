# Copyright (C) 2024 NEC, Corp.
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
from unittest import mock
import urllib

from oslo_config import cfg

from tacker.api.vnfpkgm.v1 import controller
from tacker.common import csar_utils
from tacker.common import exceptions
from tacker.conductor.conductorrpc.vnf_pkgm_rpc import VNFPackageRPCAPI
from tacker.glance_store import store as glance_store
from tacker.objects import vnf_package
from tacker.objects.vnf_software_image import VnfSoftwareImage
from tacker.policies import vnf_package as policies
from tacker.tests import constants
from tacker.tests.unit import fake_request
from tacker.tests.unit.policies import base as base_test
from tacker.tests.unit.vnfpkgm import fakes
from tacker.tests import utils
from tacker import wsgi


class VNFPackagePolicyTest(base_test.BasePolicyTest):
    """Test VNF Package APIs policies with all possible context.

    This class defines the set of context with different roles
    which are allowed and not allowed to pass the policy checks.
    With those set of context, it will call the API operation and
    verify the expected behaviour.
    """

    def setUp(self):
        super(VNFPackagePolicyTest, self).setUp()
        self.controller = controller.VnfPkgmController()
        # Below user's context will be allowed to create VNF package or
        # a few of the VNF package operations in their project.
        self.project_authorized_contexts = [
            self.legacy_admin_context, self.project_admin_context,
            self.project_member_context, self.project_reader_context,
            self.project_foo_context, self.other_project_member_context,
            self.other_project_reader_context
        ]
        self.project_unauthorized_contexts = []

        # Admin or any user in same project will be allowed to
        # upload package content, delete, patch VNF package in their
        # project.
        self.project_member_authorized_contexts = [
            self.legacy_admin_context, self.project_admin_context,
            self.project_member_context, self.project_reader_context,
            self.project_foo_context
        ]
        # User from other project will not be allowed to upload
        # package content,delete, patch the other project's VNF package.
        self.project_member_unauthorized_contexts = [
            self.other_project_member_context,
            self.other_project_reader_context
        ]

        # Admin or any user in same project will be allowed to get,
        # VNF package.
        self.project_reader_authorized_contexts = (
            self.project_member_authorized_contexts)
        # User from other project will not be allowed to get
        # the other project's VNF package.
        self.project_reader_unauthorized_contexts = (
            self.project_member_unauthorized_contexts)

        # Below user's context will be allowed to list VNF package
        self.get_authorized_contexts = [
            self.legacy_admin_context, self.project_admin_context,
            self.project_member_context, self.project_reader_context,
            self.project_foo_context, self.other_project_member_context,
            self.other_project_reader_context
        ]
        self.get_unauthorized_contexts = []

    @mock.patch.object(vnf_package, '_vnf_package_create')
    @mock.patch.object(vnf_package.VnfPackage, '_from_db_object')
    def test_create_vnf_package(
            self, mock_from_db, mock_vnf_pack):
        body = {'userDefinedData': {'abc': 'xyz'}}
        req = fake_request.HTTPRequest.blank('/vnf_packages')
        rule_name = policies.VNFPKGM % 'create'
        self.common_policy_check(self.project_authorized_contexts,
                                 self.project_unauthorized_contexts,
                                 rule_name,
                                 self.controller.create,
                                 req, body=body)

    @mock.patch.object(VnfSoftwareImage, 'get_by_id')
    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    def test_show_vnf_package(
            self, mock_vnf_by_id, mock_sw_image_by_id):
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s' % constants.UUID)
        mock_vnf_by_id.return_value = fakes.return_vnfpkg_obj(
            vnf_package_updates={'tenant_id': self.project_id})
        mock_sw_image_by_id.return_value = fakes.return_software_image()
        rule_name = policies.VNFPKGM % 'show'
        self.common_policy_check(self.project_reader_authorized_contexts,
                                 self.project_reader_unauthorized_contexts,
                                 rule_name,
                                 self.controller.show,
                                 req, constants.UUID)

    @mock.patch.object(vnf_package.VnfPackagesList, "get_by_marker_filter")
    def test_index_vnf_package(
            self, mock_vnf_list):
        req = fake_request.HTTPRequest.blank('/vnf_packages/')
        rule_name = policies.VNFPKGM % 'index'
        self.common_policy_check(self.get_authorized_contexts,
                                 self.get_unauthorized_contexts,
                                 rule_name,
                                 self.controller.index,
                                 req)

    @mock.patch.object(vnf_package.VnfPackage, "destroy")
    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    @mock.patch.object(VNFPackageRPCAPI, "delete_vnf_package")
    def test_delete_vnf_package(
            self, mock_delete_rpc, mock_vnf_by_id, mock_vnf_pack_destroy):
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s' % constants.UUID)
        mock_vnf_by_id.return_value = fakes.return_vnfpkg_obj(
            vnf_package_updates={
                'tenant_id': self.project_id,
                'operational_state': 'DISABLED'})
        rule_name = policies.VNFPKGM % 'delete'
        self.common_policy_check(self.project_member_authorized_contexts,
                                 self.project_member_unauthorized_contexts,
                                 rule_name,
                                 self.controller.delete,
                                 req, constants.UUID)

    @mock.patch.object(controller.VnfPkgmController, "_download")
    @mock.patch.object(controller.VnfPkgmController, "_get_range_from_request")
    @mock.patch.object(glance_store, 'get_csar_size')
    @mock.patch.object(vnf_package.VnfPackage, 'save')
    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    def test_fetch_package_content_vnf_package(
            self, mock_vnf_by_id, mock_save,
            mock_get_csar_size,
            mock_get_range,
            mock_download):
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s/package_content/' % constants.UUID)
        req.response = ""
        mock_vnf_by_id.return_value = fakes.return_vnfpkg_obj(
            vnf_package_updates={'tenant_id': self.project_id})
        mock_get_csar_size.return_value = 1000
        mock_get_range.return_value = "10-20, 21-30"
        mock_download.return_value = "Response"
        rule_name = policies.VNFPKGM % 'fetch_package_content'
        self.common_policy_check(self.project_reader_authorized_contexts,
                                 self.project_reader_unauthorized_contexts,
                                 rule_name,
                                 self.controller.fetch_vnf_package_content,
                                 req, constants.UUID)

    @mock.patch.object(glance_store, 'delete_csar')
    @mock.patch.object(csar_utils, 'load_csar_data')
    @mock.patch.object(glance_store, 'load_csar')
    @mock.patch.object(glance_store, 'store_csar')
    @mock.patch.object(VNFPackageRPCAPI, "upload_vnf_package_content")
    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    @mock.patch.object(vnf_package.VnfPackage, "save")
    def test_upload_vnf_package_content_package(
            self, mock_vnf_pack_save,
            mock_vnf_by_id,
            mock_upload_vnf_package_content,
            mock_glance_store,
            mock_load_csar,
            mock_load_csar_data,
            mock_delete_csar):
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s/package_content/' % constants.UUID)
        mock_vnf_by_id.return_value = fakes.return_vnfpkg_obj(
            vnf_package_updates={
                'tenant_id': self.project_id,
                'onboarding_state': 'CREATED'})
        mock_glance_store.return_value = (
            'location', 0, 'checksum', 'multihash', 'loc_meta')
        rule_name = policies.VNFPKGM % 'upload_package_content'
        self.common_policy_check(self.project_member_authorized_contexts,
                                 self.project_member_unauthorized_contexts,
                                 rule_name,
                                 self.controller.upload_vnf_package_content,
                                 req, constants.UUID,
                                 body={'dummy': {'val': 'foo'}})

    @mock.patch.object(urllib.request, 'urlopen')
    @mock.patch.object(VNFPackageRPCAPI, "upload_vnf_package_from_uri")
    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    @mock.patch.object(vnf_package.VnfPackage, "save")
    def test_upload_vnf_package_from_uri(
            self, mock_vnf_pack_save,
            mock_vnf_by_id,
            mock_upload_vnf_package_from_uri,
            mock_url_open):
        rule_name = policies.VNFPKGM % 'upload_from_uri'
        body = {"addressInformation": "http://localhost/test_data.zip"}
        # NOTE(gmann): This API is little different to test from other APIs.
        # In the upload_vnf_package API, vnf package object's onboarding_state
        # is being modified to 'UPLOADING' and if we use common_policy_check()
        # then first context API call will pass but any further context API
        # call will fail. The next context API call will fail because it will
        # have the modified vnf package object whose onboarding_state is
        # 'UPLOADING' and API raise 409 error. To solve this issue, we have
        # to call the API with each context in loop so that we can reset the
        # vnf package object's onboarding_state value before API controller
        # method is called.
        for cxtx in self.project_member_authorized_contexts:
            req = fake_request.HTTPRequest.blank(
                '/vnf_packages/%s/package_content/upload_from_uri'
                % constants.UUID)
            req.environ['tacker.context'] = cxtx
            vnf_package_obj = fakes.return_vnfpkg_obj(
                vnf_package_updates={
                    'tenant_id': self.project_id,
                    'onboarding_state': 'CREATED'})
            mock_vnf_by_id.return_value = vnf_package_obj
            self.controller.upload_vnf_package_from_uri(
                req, constants.UUID, body=body)
        for cxtx in self.project_member_unauthorized_contexts:
            req = fake_request.HTTPRequest.blank(
                '/vnf_packages/%s/package_content/upload_from_uri'
                % constants.UUID)
            req.environ['tacker.context'] = cxtx
            vnf_package_obj = fakes.return_vnfpkg_obj(
                vnf_package_updates={
                    'tenant_id': self.project_id,
                    'onboarding_state': 'CREATED'})
            mock_vnf_by_id.return_value = vnf_package_obj
            exc = self.assertRaises(
                exceptions.PolicyNotAuthorized,
                self.controller.upload_vnf_package_from_uri,
                req, constants.UUID, body=body)
            self.assertEqual(
                "Policy doesn't allow %s to be performed." % rule_name,
                exc.format_message())

    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    @mock.patch.object(vnf_package.VnfPackage, "save")
    def test_patch_vnf_package(
            self, mock_vnf_pack_save,
            mock_vnf_by_id):
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s' % constants.UUID)
        vnf_package_obj = fakes.return_vnfpkg_obj(
            vnf_package_updates={
                'tenant_id': self.project_id,
                'onboarding_state': 'CREATED',
                "user_defined_data": {"testKey1": "val01"}})
        mock_vnf_by_id.return_value = vnf_package_obj
        body = {"operationalState": "ENABLED",
                "userDefinedData": {"testKey1": "val01",
                                    "testKey2": "val02",
                                    "testkey3": "val03"}}
        rule_name = policies.VNFPKGM % 'patch'
        self.common_policy_check(self.project_member_authorized_contexts,
                                 self.project_member_unauthorized_contexts,
                                 rule_name,
                                 self.controller.patch,
                                 req, constants.UUID, body=body)

    @mock.patch.object(VNFPackageRPCAPI, "get_vnf_package_vnfd")
    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    def test_get_vnf_package_vnfd(
            self, mock_vnf_by_id, mock_get_vnf_package_vnfd):
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s/vnfd' % constants.UUID)
        req.headers['Accept'] = 'application/zip'
        req.response = wsgi.ResponseObject({})
        mock_vnf_by_id.return_value = fakes.return_vnfpkg_obj(
            vnf_package_updates={'tenant_id': self.project_id})
        fake_vnfd_data = fakes.return_vnfd_data(csar_without_tosca_meta=True)
        mock_get_vnf_package_vnfd.return_value = fake_vnfd_data
        rule_name = policies.VNFPKGM % 'get_vnf_package_vnfd'
        self.common_policy_check(self.project_reader_authorized_contexts,
                                 self.project_reader_unauthorized_contexts,
                                 rule_name,
                                 self.controller.get_vnf_package_vnfd,
                                 req, constants.UUID)

    @mock.patch.object(controller.VnfPkgmController, "_download_vnf_artifact")
    @mock.patch.object(controller.VnfPkgmController, "_get_csar_path")
    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    def test_fetch_vnf_package_artifacts(
            self, mock_vnf_by_id, mock_get_csar_path,
            mock_download_vnf_artifact):
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s/artifacts/%s'
            % (constants.UUID, constants.ARTIFACT_PATH))
        req.headers['Range'] = 'bytes=10-30'
        req.response = wsgi.ResponseObject({})
        extract_path = utils.test_etc_sample(
            'sample_vnf_package_csar_in_meta_and_manifest')
        absolute_artifact_path = (
            os.path.join(extract_path, constants.ARTIFACT_PATH))
        mock_vnf_by_id.return_value = fakes.return_vnfpkg_obj(
            vnf_package_updates={'tenant_id': self.project_id},
            vnf_artifact_updates={'artifact_path': absolute_artifact_path})
        with open(absolute_artifact_path, 'rb') as f:
            data = f.read()
        mock_download_vnf_artifact.return_value = data
        rule_name = policies.VNFPKGM % 'fetch_artifact'
        self.common_policy_check(self.project_reader_authorized_contexts,
                                 self.project_reader_unauthorized_contexts,
                                 rule_name,
                                 self.controller.fetch_vnf_package_artifacts,
                                 req, constants.UUID, absolute_artifact_path)


class VNFPackageScopeTypePolicyTest(VNFPackagePolicyTest):
    """Test VNF Package APIs policies with scope enabled.

    This class set the tacker.conf [oslo_policy] enforce_scope to True
    so that we can switch on the scope checking on oslo policy side.
    This check that system scope users are not allowed to access the
    Tacker VNF Package APIs.
    """

    def setUp(self):
        super(VNFPackageScopeTypePolicyTest, self).setUp()
        cfg.CONF.set_override('enforce_scope', True,
                              group='oslo_policy')

        self.project_authorized_contexts = [
            self.legacy_admin_context, self.project_admin_context,
            self.project_member_context, self.project_reader_context,
            self.project_foo_context, self.other_project_member_context,
            self.other_project_reader_context
        ]
        # With scope enabled, system scoped users will not be
        # allowed to create VNF Package or a few of the VNF Package
        # operations in their project.
        self.project_unauthorized_contexts = [
            self.system_admin_context, self.system_member_context,
            self.system_reader_context, self.system_foo_context
        ]

        self.project_member_authorized_contexts = [
            self.legacy_admin_context, self.project_admin_context,
            self.project_member_context, self.project_reader_context,
            self.project_foo_context
        ]
        # With scope enabled, system scoped users will not be allowed
        # to upload content, delete, patch VNF Package.
        self.project_member_unauthorized_contexts = [
            self.system_admin_context, self.system_member_context,
            self.system_reader_context, self.system_foo_context,
            self.other_project_member_context,
            self.other_project_reader_context]

        self.get_authorized_contexts = [
            self.legacy_admin_context, self.project_admin_context,
            self.project_member_context, self.project_reader_context,
            self.project_foo_context, self.other_project_member_context,
            self.other_project_reader_context
        ]
        # With scope enabled, system scoped users will not be allowed
        # to list VNF package
        self.get_unauthorized_contexts = [
            self.system_admin_context, self.system_member_context,
            self.system_reader_context, self.system_foo_context,
        ]


class VNFPackageNewDefaultsPolicyTest(VNFPackagePolicyTest):
    """Test VNF Package APIs policies with new defaults enabled

    This test class enable the new defaults means no legacy old rules
    and check how permission level looks like.
    """

    enforce_new_defaults = True

    def setUp(self):
        super(VNFPackageNewDefaultsPolicyTest, self).setUp()

        # In new defaults, admin or member roles users will be allowed
        # to create VNF package in their project.
        # Project reader will not be able to create VNF package.
        self.project_authorized_contexts = [
            self.legacy_admin_context, self.project_admin_context,
            self.project_member_context, self.other_project_member_context,
        ]
        # In new defaults, non admin or non member role (Project reader)
        # user will not be able to create VNF package.
        self.project_unauthorized_contexts = [
            self.project_reader_context, self.project_foo_context,
            self.other_project_reader_context]

        # In new defaults, all admin, project members will be allowed to
        # upload content, delete, patch VNF of their project.
        self.project_member_authorized_contexts = [
            self.legacy_admin_context, self.project_admin_context,
            self.project_member_context
        ]
        # In new defaults, Project reader or any other non admin|member
        # role (say foo role) will not be allowed to upload content,
        # delete, patch VNF package.
        self.project_member_unauthorized_contexts = [
            self.project_reader_context, self.project_foo_context,
            self.other_project_member_context,
            self.other_project_reader_context
        ]

        # In new defaults, Project reader also can get VNF package.
        self.project_reader_authorized_contexts = [
            self.legacy_admin_context, self.project_admin_context,
            self.project_member_context,
            self.project_reader_context
        ]
        # In new defaults, non admin|member|reader role (say foo role)
        # will not be able to get VNF package.
        self.project_reader_unauthorized_contexts = [
            self.project_foo_context,
            self.other_project_member_context,
            self.other_project_reader_context
        ]

        self.get_authorized_contexts = [
            self.legacy_admin_context, self.project_admin_context,
            self.project_member_context, self.project_reader_context,
            self.other_project_member_context,
            self.other_project_reader_context
        ]
        # In new defaults, project random role like foo will not
        # be allowed to list the VNF package.
        self.get_unauthorized_contexts = [
            self.project_foo_context
        ]


class VNFPackageNewDefaultsWithScopePolicyTest(
        VNFPackageNewDefaultsPolicyTest):
    """Test VNF Package APIs policies with new defaults rules and scope enabled

    This means scope enabled and no legacy old rules. This is the end goal
    when operators will enable scope and new defaults.
    """

    def setUp(self):
        super(VNFPackageNewDefaultsWithScopePolicyTest, self).setUp()
        cfg.CONF.set_override('enforce_scope', True,
                              group='oslo_policy')

        # With scope enable and no legacy rule, only project admin/member
        # will be able to create VNF Package in their project.
        self.project_authorized_contexts = [
            self.legacy_admin_context, self.project_admin_context,
            self.project_member_context, self.other_project_member_context
        ]
        # System scoped users will not be allowed.
        self.project_unauthorized_contexts = [
            self.system_admin_context, self.system_member_context,
            self.system_reader_context, self.system_foo_context,
            self.project_reader_context, self.project_foo_context,
            self.other_project_reader_context]

        self.project_member_authorized_contexts = [
            self.legacy_admin_context, self.project_admin_context,
            self.project_member_context,
        ]
        # System scoped users will not be allowed.
        self.project_member_unauthorized_contexts = [
            self.system_admin_context, self.system_member_context,
            self.system_reader_context, self.system_foo_context,
            self.project_reader_context, self.project_foo_context,
            self.other_project_member_context,
            self.other_project_reader_context]

        self.project_reader_authorized_contexts = [
            self.legacy_admin_context, self.project_admin_context,
            self.project_member_context,
            self.project_reader_context
        ]
        # System scoped users will not be allowed.
        self.project_reader_unauthorized_contexts = [
            self.system_admin_context, self.system_member_context,
            self.system_reader_context, self.system_foo_context,
            self.project_foo_context,
            self.other_project_member_context,
            self.other_project_reader_context
        ]

        self.get_authorized_contexts = [
            self.legacy_admin_context, self.project_admin_context,
            self.project_member_context, self.project_reader_context,
            self.other_project_member_context,
            self.other_project_reader_context
        ]
        # With scope enabled, system scoped users will not be allowed
        self.get_unauthorized_contexts = [
            self.project_foo_context, self.system_admin_context,
            self.system_member_context, self.system_reader_context,
            self.system_foo_context,
        ]
