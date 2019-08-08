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

import mock
from oslo_serialization import jsonutils
from six.moves import http_client
from six.moves import urllib
from webob import exc

from tacker.api.vnfpkgm.v1 import controller
from tacker.conductor.conductorrpc.vnf_pkgm_rpc import VNFPackageRPCAPI
from tacker.glance_store import store as glance_store
from tacker.objects import vnf_package
from tacker.objects.vnf_package import VnfPackagesList
from tacker.tests import constants
from tacker.tests.unit import base
from tacker.tests.unit import fake_request
from tacker.tests.unit.vnfpkgm import fakes


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
        mock_vnf_pack_save.return_value = fakes.return_vnfpkg_obj()
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
        mock_vnf_pack_save.return_value = fakes.return_vnfpkg_obj()
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

    def test_upload_vnf_package_from_uri_with_invalid_url(self):
        body = {"addressInformation": "http://test_data.zip"}
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s/package_content/upload_from_uri'
            % constants.UUID)
        self.assertRaises(exc.HTTPBadRequest,
                          self.controller.upload_vnf_package_from_uri,
                          req, constants.UUID, body=body)
