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

import ddt
import mock
from oslo_serialization import jsonutils
from six.moves import http_client
from six.moves import urllib
from webob import exc

from tacker.api.vnfpkgm.v1 import controller
from tacker.common import exceptions
from tacker.conductor.conductorrpc.vnf_pkgm_rpc import VNFPackageRPCAPI
from tacker.glance_store import store as glance_store
from tacker import objects
from tacker.objects import fields
from tacker.objects import vnf_package
from tacker.objects.vnf_package import VnfPackagesList
from tacker.tests import constants
from tacker.tests.unit import base
from tacker.tests.unit import fake_request
from tacker.tests.unit.vnfpkgm import fakes


@ddt.ddt
class TestController(base.TestCase):

    def setUp(self):
        super(TestController, self).setUp()
        self.controller = controller.VnfPkgmController()

    @property
    def app(self):
        return fakes.wsgi_app_v1()

    @mock.patch.object(vnf_package, '_vnf_package_create')
    @mock.patch.object(vnf_package.VnfPackage, '_from_db_object')
    def test_create_with_status_202(self, mock_from_db, mock_vnf_pack):
        body = {'userDefinedData': {'abc': 'xyz'}}
        req = fake_request.HTTPRequest.blank('/vnf_packages')
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'
        resp = req.get_response(self.app)
        self.assertEqual(http_client.CREATED, resp.status_code)

    @mock.patch.object(vnf_package, '_vnf_package_create')
    @mock.patch.object(vnf_package.VnfPackage, '_from_db_object')
    def test_create_without_userdefine_data(self, mock_from_db,
                                            mock_vnf_pack):
        body = {'userDefinedData': {}}
        req = fake_request.HTTPRequest.blank('/vnf_packages')
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'
        resp = req.get_response(self.app)
        self.assertEqual(http_client.CREATED, resp.status_code)

    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    def test_show(self, mock_vnf_by_id):
        req = fake_request.HTTPRequest.blank(
            '/vnfpkgm/v1/vnf_packages/%s' % constants.UUID)
        mock_vnf_by_id.return_value = fakes.return_vnf_package()
        expected_result = fakes.VNFPACKAGE_RESPONSE
        res_dict = self.controller.show(req, constants.UUID)
        self.assertEqual(expected_result, res_dict)

    def test_show_with_invalid_uuid(self):
        req = fake_request.HTTPRequest.blank(
            '/vnfpkgm/v1/vnf_packages/%s' % constants.INVALID_UUID)
        self.assertRaises(exc.HTTPNotFound, self.controller.show,
                          req, constants.INVALID_UUID)

    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    def test_show_no_vnf_package(self, mock_vnf_by_id):
        req = fake_request.HTTPRequest.blank(
            '/vnfpkgm/v1/vnf_packages/%s' % constants.UUID)
        msg = _("Can not find requested vnf package: %s") % constants.UUID
        mock_vnf_by_id.side_effect = exc.HTTPNotFound(explanation=msg)
        self.assertRaises(exc.HTTPNotFound, self.controller.show,
                          req, constants.UUID)

    @mock.patch.object(VnfPackagesList, "get_all")
    def test_index(self, mock_vnf_list):
        req = fake_request.HTTPRequest.blank('/vnfpkgm/v1/vnf_packages/')
        mock_vnf_list.return_value = fakes.return_vnf_package_list()
        res_dict = self.controller.index(req)
        expected_result = fakes.VNFPACKAGE_INDEX_RESPONSE
        self.assertEqual(expected_result, res_dict)

    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    @mock.patch.object(VNFPackageRPCAPI, "delete_vnf_package")
    def test_delete_with_204_status(self, mock_delete_rpc, mock_vnf_by_id):
        mock_vnf_by_id.return_value = fakes.return_vnfpkg_obj()
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s' % constants.UUID)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'DELETE'
        resp = req.get_response(self.app)
        self.assertEqual(http_client.NO_CONTENT, resp.status_code)

    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    def test_delete_no_vnf_package(self, mock_vnf_by_id):
        req = fake_request.HTTPRequest.blank(
            '/vnfpkgm/v1/vnf_packages/%s' % constants.UUID)
        msg = _("Can not find requested vnf package: %s") % constants.UUID
        mock_vnf_by_id.side_effect = exc.HTTPNotFound(explanation=msg)
        self.assertRaises(exc.HTTPNotFound, self.controller.delete,
                          req, constants.UUID)

    def test_delete_with_invalid_uuid(self):
        req = fake_request.HTTPRequest.blank(
            '/vnfpkgm/v1/vnf_packages/%s' % constants.INVALID_UUID)
        self.assertRaises(exc.HTTPNotFound, self.controller.delete,
                          req, constants.INVALID_UUID)

    @mock.patch.object(objects.VnfPackage, "get_by_id")
    def test_delete_with_operational_state_enabled(self, mock_vnf_by_id):
        req = fake_request.HTTPRequest.blank(
            '/vnfpkgm/v1/vnf_packages/%s' % constants.UUID)
        vnf_package_dict = fakes.fake_vnf_package()
        vnf_package_dict['operational_state'] = \
            fields.PackageOperationalStateType.ENABLED
        vnf_package = objects.VnfPackage(**vnf_package_dict)
        mock_vnf_by_id.return_value = vnf_package
        self.assertRaises(exc.HTTPConflict, self.controller.delete,
                          req, constants.UUID)

    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    def test_delete_with_usage_state_in_use(self, mock_vnf_by_id):
        req = fake_request.HTTPRequest.blank(
            '/vnfpkgm/v1/vnf_packages/%s' % constants.UUID)
        vnf_package_dict = fakes.fake_vnf_package()
        vnf_package_dict['usage_state'] = \
            fields.PackageUsageStateType.IN_USE
        vnf_package = objects.VnfPackage(**vnf_package_dict)
        mock_vnf_by_id.return_value = vnf_package
        self.assertRaises(exc.HTTPConflict, self.controller.delete,
                          req, constants.UUID)

    @mock.patch.object(glance_store, 'store_csar')
    @mock.patch.object(VNFPackageRPCAPI, "upload_vnf_package_content")
    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    @mock.patch.object(vnf_package.VnfPackage, "save")
    def test_upload_vnf_package_content(self, mock_vnf_pack_save,
                                        mock_vnf_by_id,
                                        mock_upload_vnf_package_content,
                                        mock_glance_store):
        file_path = "tacker/tests/etc/samples/test_data.zip"
        file_obj = open(file_path, "rb")
        mock_vnf_by_id.return_value = fakes.return_vnfpkg_obj()
        mock_glance_store.return_value = 'location', 'size', 'checksum',\
                                         'multihash', 'loc_meta'
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s/package_content'
            % constants.UUID)
        req.headers['Content-Type'] = 'application/zip'
        req.method = 'PUT'
        req.body = jsonutils.dump_as_bytes(file_obj)
        resp = req.get_response(self.app)
        mock_glance_store.assert_called()
        self.assertEqual(http_client.ACCEPTED, resp.status_code)

    def test_upload_vnf_package_content_with_invalid_uuid(self):
        file_path = "tacker/tests/etc/samples/test_data.zip"
        file_obj = open(file_path, "rb")
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s/package_content'
            % constants.INVALID_UUID)
        exception = self.assertRaises(exc.HTTPNotFound,
                                self.controller.upload_vnf_package_content,
                                req, constants.INVALID_UUID, body=file_obj)
        self.assertEqual(
            "Can not find requested vnf package: %s" % constants.INVALID_UUID,
            exception.explanation)

    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    def test_upload_vnf_package_content_without_vnf_pack(self,
                                                         mock_vnf_by_id):
        file_path = "tacker/tests/etc/samples/test_data.zip"
        file_obj = open(file_path, "rb")
        msg = _("Can not find requested vnf package: %s") % constants.UUID
        mock_vnf_by_id.side_effect = exc.HTTPNotFound(explanation=msg)
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s/package_content' % constants.UUID)
        exception = self.assertRaises(
            exc.HTTPNotFound, self.controller.upload_vnf_package_content,
            req, constants.UUID, body=file_obj)
        self.assertEqual(
            "Can not find requested vnf package: %s" % constants.UUID,
            exception.explanation)

    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    def test_upload_vnf_package_content_with_invalid_status(self,
                                                            mock_vnf_by_id):
        file_path = "tacker/tests/etc/samples/test_data.zip"
        file_obj = open(file_path, "rb")
        vnf_obj = fakes.return_vnfpkg_obj()
        vnf_obj.__setattr__('onboarding_state', 'test')
        mock_vnf_by_id.return_value = vnf_obj
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s/package_content' % constants.UUID)
        self.assertRaises(exc.HTTPConflict,
                          self.controller.upload_vnf_package_content,
                          req, constants.UUID, body=file_obj)

    @mock.patch.object(urllib.request, 'urlopen')
    @mock.patch.object(VNFPackageRPCAPI, "upload_vnf_package_from_uri")
    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    @mock.patch.object(vnf_package.VnfPackage, "save")
    def test_upload_vnf_package_from_uri(self, mock_vnf_pack_save,
                                         mock_vnf_by_id,
                                         mock_upload_vnf_package_from_uri,
                                         mock_url_open):
        body = {"addressInformation": "http://test_data.zip"}
        mock_vnf_by_id.return_value = fakes.return_vnfpkg_obj()
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s/package_content/upload_from_uri'
            % constants.UUID)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'
        req.body = jsonutils.dump_as_bytes(body)
        resp = req.get_response(self.app)
        self.assertEqual(http_client.ACCEPTED, resp.status_code)

    def test_upload_vnf_package_from_uri_with_invalid_uuid(self):
        body = {"addressInformation": "http://test_data.zip"}
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s/package_content/upload_from_uri'
            % constants.INVALID_UUID)
        self.assertRaises(exc.HTTPNotFound,
                          self.controller.upload_vnf_package_from_uri,
                          req, constants.INVALID_UUID, body=body)

    @mock.patch.object(urllib.request, 'urlopen')
    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    def test_upload_vnf_package_from_uri_without_vnf_pack(self,
                                                          mock_vnf_by_id,
                                                          mock_url_open):
        body = {"addressInformation": "http://test_data.zip"}
        msg = _("Can not find requested vnf package: %s") % constants.UUID
        mock_vnf_by_id.side_effect = exc.HTTPNotFound(explanation=msg)
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s/package_content/upload_from_uri'
            % constants.UUID)
        self.assertRaises(exc.HTTPNotFound,
                          self.controller.upload_vnf_package_from_uri,
                          req, constants.UUID, body=body)

    @mock.patch.object(urllib.request, 'urlopen')
    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    def test_upload_vnf_package_from_uri_with_invalid_status(self,
                                                             mock_vnf_by_id,
                                                             mock_url_open):
        body = {"addressInformation": "http://test.zip"}
        vnf_obj = fakes.return_vnfpkg_obj()
        vnf_obj.__setattr__('onboarding_state', 'test')
        mock_vnf_by_id.return_value = vnf_obj
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s/package_content/upload_from_uri'
            % constants.UUID)
        self.assertRaises(exc.HTTPConflict,
                          self.controller.upload_vnf_package_from_uri,
                          req, constants.UUID, body=body)

    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    def test_upload_vnf_package_from_uri_with_invalid_url(
            self, mock_vnf_by_id):
        mock_vnf_by_id.return_value = fakes.return_vnfpkg_obj()
        body = {"addressInformation": "http://test_data.zip"}
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s/package_content/upload_from_uri'
            % constants.UUID)
        self.assertRaises(exc.HTTPBadRequest,
                          self.controller.upload_vnf_package_from_uri,
                          req, constants.UUID, body=body)

    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    @mock.patch.object(vnf_package.VnfPackage, "save")
    def test_patch(self, mock_save, mock_vnf_by_id):
        update_onboarding_state = {'onboarding_state': 'ONBOARDED'}
        mock_vnf_by_id.return_value = \
            fakes.return_vnfpkg_obj(**update_onboarding_state)

        req_body = {"operationalState": "ENABLED",
                "userDefinedData": {"testKey1": "val01",
                                    "testKey2": "val02", "testkey3": "val03"}}

        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s'
            % constants.UUID)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'PATCH'
        req.body = jsonutils.dump_as_bytes(req_body)
        resp = req.get_response(self.app)

        self.assertEqual(http_client.OK, resp.status_code)
        self.assertEqual(req_body, jsonutils.loads(resp.body))

    def test_patch_with_empty_body(self):
        body = {}
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s'
            % constants.UUID)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'PATCH'
        req.body = jsonutils.dump_as_bytes(body)
        resp = req.get_response(self.app)
        self.assertEqual(http_client.BAD_REQUEST, resp.status_code)

    def test_patch_with_invalid_operational_state(self):
        body = {"operationalState": "DISABLE"}
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s'
            % constants.UUID)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'PATCH'
        req.body = jsonutils.dump_as_bytes(body)
        resp = req.get_response(self.app)
        self.assertEqual(http_client.BAD_REQUEST, resp.status_code)

    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    @mock.patch.object(vnf_package.VnfPackage, "save")
    def test_patch_update_existing_user_data(self, mock_save, mock_vnf_by_id):
        fake_obj = fakes.return_vnfpkg_obj(
            **{'user_data': {"testKey1": "val01", "testKey2": "val02",
                             "testKey3": "val03"}})
        mock_vnf_by_id.return_value = fake_obj
        req_body = {"userDefinedData": {"testKey1": "changed_val01",
                                        "testKey2": "changed_val02",
                                        "testKey3": "changed_val03"}}
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s'
            % constants.UUID)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'PATCH'
        req.body = jsonutils.dump_as_bytes(req_body)
        resp = req.get_response(self.app)
        self.assertEqual(http_client.OK, resp.status_code)
        self.assertEqual(req_body, jsonutils.loads(resp.body))

    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    @mock.patch.object(vnf_package.VnfPackage, "save")
    def test_patch_failed_with_same_user_data(self, mock_save,
                                              mock_vnf_by_id):
        body = {"userDefinedData": {"testKey1": "val01",
                                    "testKey2": "val02", "testkey3": "val03"}}
        fake_obj = fakes.return_vnfpkg_obj(
            **{'user_data': body["userDefinedData"]})
        mock_vnf_by_id.return_value = fake_obj

        req = fake_request.HTTPRequest.blank('/vnf_packages/%s'
                                             % constants.UUID)
        self.assertRaises(exc.HTTPConflict,
                          self.controller.patch,
                          req, constants.UUID, body=body)

    def test_patch_with_invalid_uuid(self):
        body = {"operationalState": "ENABLED"}
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s'
            % constants.INVALID_UUID)
        exception = self.assertRaises(exc.HTTPNotFound,
                                      self.controller.patch,
                                      req, constants.INVALID_UUID, body=body)
        self.assertEqual(
            "Can not find requested vnf package: %s" % constants.INVALID_UUID,
            exception.explanation)

    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    def test_patch_with_non_existing_vnf_package(self, mock_vnf_by_id):
        body = {"operationalState": "ENABLED"}
        msg = _("Can not find requested vnf package: %s") % constants.UUID
        mock_vnf_by_id.side_effect = exc.HTTPNotFound(explanation=msg)
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s' % constants.UUID)
        exception = self.assertRaises(
            exc.HTTPNotFound, self.controller.patch,
            req, constants.UUID, body=body)
        self.assertEqual(
            "Can not find requested vnf package: %s" % constants.UUID,
            exception.explanation)

    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    def test_patch_failed_with_same_operational_state(self, mock_vnf_by_id):
        update_operational_state = {'onboarding_state': 'ONBOARDED'}
        vnf_obj = fakes.return_vnfpkg_obj(**update_operational_state)
        mock_vnf_by_id.return_value = vnf_obj
        body = {"operationalState": "DISABLED",
                "userDefinedData": {"testKey1": "val01",
                                    "testKey2": "val02", "testkey3": "val03"}}
        req = fake_request.HTTPRequest.blank('/vnf_packages/%s'
                                             % constants.UUID)
        self.assertRaises(exc.HTTPConflict,
                          self.controller.patch,
                          req, constants.UUID, body=body)

    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    def test_patch_not_in_onboarded_state(self, mock_vnf_by_id):
        mock_vnf_by_id.return_value = fakes.return_vnfpkg_obj()
        body = {"operationalState": "DISABLED"}
        req = fake_request.HTTPRequest.blank('/vnf_packages/%s'
                                             % constants.UUID)
        self.assertRaises(exc.HTTPBadRequest,
                          self.controller.patch,
                          req, constants.UUID, body=body)

    @mock.patch.object(VNFPackageRPCAPI, "get_vnf_package_vnfd")
    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    @ddt.data('application/zip', 'text/plain,application/zip',
              'application/zip,text/plain')
    def test_get_vnf_package_vnfd_with_valid_accept_headers(
            self, accept_headers, mock_vnf_by_id, mock_get_vnf_package_vnfd):
        mock_vnf_by_id.return_value = fakes.return_vnfpkg_obj(onboarded=True)
        mock_get_vnf_package_vnfd.return_value = fakes.return_vnfd_data()
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s/vnfd'
            % constants.UUID)
        req.headers['Accept'] = accept_headers
        req.method = 'GET'
        resp = req.get_response(self.app)
        self.assertEqual(http_client.OK, resp.status_code)

    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    def test_get_vnf_package_vnfd_with_invalid_accept_header(
            self, mock_vnf_by_id):
        mock_vnf_by_id.return_value = fakes.return_vnfpkg_obj(onboarded=True)
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s/vnfd'
            % constants.UUID)
        req.headers['Accept'] = 'test-invalid-header'
        req.method = 'GET'
        self.assertRaises(exc.HTTPNotAcceptable,
                          self.controller.get_vnf_package_vnfd,
                          req, constants.UUID)

    @mock.patch.object(VNFPackageRPCAPI, "get_vnf_package_vnfd")
    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    def test_get_vnf_package_vnfd_failed_with_bad_request(
            self, mock_vnf_by_id, mock_get_vnf_package_vnfd):
        mock_vnf_by_id.return_value = fakes.return_vnfpkg_obj(onboarded=True)
        mock_get_vnf_package_vnfd.return_value = fakes.return_vnfd_data()
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s/vnfd'
            % constants.UUID)
        req.headers['Accept'] = 'text/plain'
        req.method = 'GET'
        self.assertRaises(exc.HTTPBadRequest,
                          self.controller.get_vnf_package_vnfd,
                          req, constants.UUID)

    @mock.patch.object(VNFPackageRPCAPI, "get_vnf_package_vnfd")
    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    def test_get_vnf_package_vnfd_for_content_type_text_plain(self,
                                  mock_vnf_by_id,
                                  mock_get_vnf_package_vnfd):
        mock_vnf_by_id.return_value = fakes.return_vnfpkg_obj(onboarded=True)
        fake_vnfd_data = fakes.return_vnfd_data(multiple_yaml_files=False)
        mock_get_vnf_package_vnfd.return_value = fake_vnfd_data
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s/vnfd'
            % constants.UUID)
        req.headers['Accept'] = 'text/plain'
        req.method = 'GET'
        resp = req.get_response(self.app)
        self.assertEqual(http_client.OK, resp.status_code)
        self.assertEqual('text/plain', resp.content_type)
        self.assertEqual(fake_vnfd_data[list(fake_vnfd_data.keys())[0]],
                         resp.text)

    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    def test_get_vnf_package_vnfd_failed_with_invalid_status(
            self, mock_vnf_by_id):
        mock_vnf_by_id.return_value = fakes.return_vnfpkg_obj(onboarded=False)
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s/vnfd'
            % constants.UUID)
        req.headers['Accept'] = 'application/zip'
        req.method = 'GET'
        resp = req.get_response(self.app)
        self.assertEqual(http_client.CONFLICT, resp.status_code)

    def test_get_vnf_package_vnfd_with_invalid_uuid(self):
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s/vnfd'
            % constants.INVALID_UUID)
        req.headers['Accept'] = 'application/zip'
        req.method = 'GET'
        exception = self.assertRaises(exc.HTTPNotFound,
                                self.controller.get_vnf_package_vnfd,
                                req, constants.INVALID_UUID)
        self.assertEqual(
            "Can not find requested vnf package: %s" % constants.INVALID_UUID,
            exception.explanation)

    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    def test_get_vnf_package_vnfd_with_non_existing_vnf_packagee(
            self, mock_vnf_by_id):
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s/vnfd'
            % constants.UUID)
        req.headers['Accept'] = 'application/zip'
        req.method = 'GET'
        mock_vnf_by_id.side_effect = exceptions.VnfPackageNotFound
        self.assertRaises(exc.HTTPNotFound,
                          self.controller.get_vnf_package_vnfd, req,
                          constants.UUID)

    @mock.patch.object(VNFPackageRPCAPI, "get_vnf_package_vnfd")
    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    def test_get_vnf_package_vnfd_failed_with_internal_server_error(
            self, mock_vnf_by_id, mock_get_vnf_package_vnfd):
        mock_vnf_by_id.return_value = fakes.return_vnfpkg_obj(onboarded=True)
        mock_get_vnf_package_vnfd.side_effect = exceptions.FailedToGetVnfdData
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s/vnfd'
            % constants.UUID)
        req.headers['Accept'] = 'application/zip'
        req.method = 'GET'
        resp = req.get_response(self.app)
        self.assertRaises(exc.HTTPInternalServerError,
                          self.controller.get_vnf_package_vnfd,
                          req, constants.UUID)
        self.assertEqual(http_client.INTERNAL_SERVER_ERROR, resp.status_code)
