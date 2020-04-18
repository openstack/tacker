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

from unittest import mock

from tacker.common.rpc import BackingOffClient
from tacker.conductor.conductorrpc import vnf_pkgm_rpc
from tacker.objects import vnf_package
from tacker.tests import base
from tacker.tests.unit.conductor import fakes


class VnfPackageRPCTestCase(base.BaseTestCase):

    def setUp(self):
        super(VnfPackageRPCTestCase, self).setUp()
        self.context = self.fake_admin_context()
        self.rpc_api = vnf_pkgm_rpc.VNFPackageRPCAPI()
        self.cctxt_mock = mock.MagicMock()

    def test_upload_vnf_package_content(self):

        @mock.patch.object(BackingOffClient, 'prepare')
        def _test(prepare_mock):
            prepare_mock.return_value = self.cctxt_mock
            vnf_package_obj = vnf_package.VnfPackage(
                self.context, **fakes.VNF_UPLOAD_VNF_PACKAGE_CONTENT)
            self.rpc_api.upload_vnf_package_content(self.context,
                                            vnf_package_obj, cast=True)
            prepare_mock.assert_called()
            self.cctxt_mock.cast.assert_called_once_with(
                self.context, 'upload_vnf_package_content',
                vnf_package=vnf_package_obj)
        _test()

    def test_upload_vnf_package_from_uri(self):
        fake_addressInformation = "http://test_csar.zip"

        @mock.patch.object(BackingOffClient, 'prepare')
        def _test(prepare_mock):
            prepare_mock.return_value = self.cctxt_mock
            vnf_package_obj = vnf_package.VnfPackage(self.context,
                                                     **fakes.VNF_DATA)
            self.rpc_api.upload_vnf_package_from_uri(self.context,
                                                     vnf_package_obj,
                                                     fake_addressInformation,
                                                     cast=True)
            prepare_mock.assert_called()
            self.cctxt_mock.cast.assert_called_once_with(
                self.context, 'upload_vnf_package_from_uri',
                vnf_package=vnf_package_obj,
                address_information=fake_addressInformation,
                password=None, user_name=None)
        _test()

    def test_delete_vnf_package(self):

        @mock.patch.object(BackingOffClient, 'prepare')
        def _test(prepare_mock):
            prepare_mock.return_value = self.cctxt_mock
            vnf_package_obj = vnf_package.VnfPackage(self.context,
                                                     **fakes.VNF_DATA)
            self.rpc_api.delete_vnf_package(self.context,
                                            vnf_package_obj, cast=True)
            prepare_mock.assert_called()
            self.cctxt_mock.cast.assert_called_once_with(
                self.context, 'delete_vnf_package',
                vnf_package=vnf_package_obj)
        _test()

    def test_get_vnf_package_vnfd(self):

        @mock.patch.object(BackingOffClient, 'prepare')
        def _test(prepare_mock):
            prepare_mock.return_value = self.cctxt_mock
            vnf_package_obj = vnf_package.VnfPackage(self.context,
                                                     **fakes.VNF_DATA)
            self.rpc_api.get_vnf_package_vnfd(self.context,
                                            vnf_package_obj, cast=False)
            prepare_mock.assert_called()
            self.cctxt_mock.call.assert_called_once_with(
                self.context, 'get_vnf_package_vnfd',
                vnf_package=vnf_package_obj)
        _test()
