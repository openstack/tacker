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

from tacker.api.vnflcm.v1 import sync_resource as sync
from tacker.conductor.conductorrpc import vnf_pkgm_rpc
from tacker import context
from tacker.db.nfvo import nfvo_db
from tacker.glance_store import store as glance_store
from tacker import objects
from tacker.tests.unit import base
from tacker.tests.unit.vnflcm import fakes as vnflcm_fakes
from tacker.tests.unit.vnfpkgm import fakes as vnfpkgm_fakes
from tacker.tests import uuidsentinel
import tacker.vnfm.nfvo_client as nfvo_client
from unittest import mock
from webob import exc


@ddt.ddt
class TestSyncVnfPackage(base.TestCase):

    def setUp(self):
        super(TestSyncVnfPackage, self).setUp()
        self.context = context.ContextBase(
            uuidsentinel.user_id,
            uuidsentinel.project_id,
            is_admin=True)
        self.vim = nfvo_db.Vim()

    def tearDown(self):
        super(TestSyncVnfPackage, self).tearDown()
        self.addCleanup(mock.patch.stopall)

    @mock.patch.object(glance_store, 'store_csar')
    @mock.patch.object(objects.vnf_package_vnfd.VnfPackageVnfd,
                       'get_by_id')
    @mock.patch.object(objects.vnf_package, '_vnf_package_create')
    @mock.patch.object(objects.vnf_package.VnfPackage, 'save')
    @mock.patch.object(objects.vnf_package.VnfPackage, '_from_db_object')
    @mock.patch.object(nfvo_client.VnfPackageRequest, 'download_vnf_packages')
    @mock.patch.object(vnf_pkgm_rpc.VNFPackageRPCAPI,
                       "upload_vnf_package_content")
    def test_package_and_package_vnfd_creation_successful(self,
            mock_upload_vnf_package_content,
            mock_nfvo_download_vnf_packages,
            mock_from_db_vnf_package,
            mock_save_vnf_package,
            mock_vnf_package,
            mock_get_by_id,
            mock_glance_store):

        # glance_store mock Settings
        mock_glance_store.return_value = 'location', 0, 'checksum',\
                                         'multihash', 'loc_meta'

        updates = {'additionalArtifacts': [
            {
                'artifactPath': 'sample1_file.yaml',
                'checksum': {
                    'hash':
                        '53b504e608eef3d19a\
                            22413bf6ee72f42091fbb5213e6a876a3a22f6c3c94fe1',
                    'algorithm': 'SHA-256'
                }
            },
            {
                'artifactPath': 'sample2_file.yaml',
                'checksum': {
                    'hash':
                        '43b504e608eef3d19a\
                            22413bf6ee72f42091fbb5213e6a876a3a22f6c3c94fe1',
                    'algorithm': 'SHA-256'
                }
            }
        ]}
        vnf_package_info = vnfpkgm_fakes.index_response(
            remove_attrs=['userDefinedData'],
            vnf_package_updates=updates)[0]

        exp_vnf_package_vnfd = \
            vnflcm_fakes.fake_vnf_package_vnfd_model_dict(**updates)
        mock_get_by_id.return_value = exp_vnf_package_vnfd

        vnf_package_vnfd = sync.SyncVnfPackage.create_package(
            self.context, vnf_package_info)

        # Expected value setting
        self.assertEqual(exp_vnf_package_vnfd.get('package_uuid'),
         vnf_package_vnfd.get('package_uuid'))
        self.assertEqual(exp_vnf_package_vnfd.get('vnfd_id'),
         vnf_package_vnfd.get('vnfd_id'))
        self.assertEqual(exp_vnf_package_vnfd.get('vnf_provider'),
         vnf_package_vnfd.get('vnf_provider'))
        self.assertEqual(exp_vnf_package_vnfd.get('vnf_product_name'),
         vnf_package_vnfd.get('vnf_product_name'))
        self.assertEqual(exp_vnf_package_vnfd.get('vnf_software_version'),
         vnf_package_vnfd.get('vnf_software_version'))
        self.assertEqual(exp_vnf_package_vnfd.get('vnfd_version'),
         vnf_package_vnfd.get('vnfd_version'))

        # Check if a mock is called even once
        mock_upload_vnf_package_content.assert_called()
        mock_nfvo_download_vnf_packages.assert_called()
        mock_from_db_vnf_package.assert_called()
        mock_save_vnf_package.assert_called()
        mock_vnf_package.assert_called()
        mock_get_by_id.assert_called()
        mock_glance_store.assert_called()

    @mock.patch.object(objects.vnf_package, '_vnf_package_create')
    def test_package_and_package_vnfd_creation_package_create_err(self,
            mock_vnf_package):

        # vnf_package mock Settings
        mock_vnf_package.side_effect = Exception

        # SyncVnfPackage.create_package
        vnf_package_info = vnfpkgm_fakes.index_response()[0]
        self.assertRaises(
            exc.HTTPInternalServerError,
            sync.SyncVnfPackage.create_package,
            self.context,
            vnf_package_info)

        # Check if a mock is called even once
        mock_vnf_package.assert_called()

    @mock.patch.object(objects.vnf_package, '_vnf_package_create')
    @mock.patch.object(objects.vnf_package.VnfPackage, '_from_db_object')
    @mock.patch.object(nfvo_client.VnfPackageRequest, 'download_vnf_packages')
    def test_package_and_package_vnfd_creation_undefinedexcep(self,
            mock_nfvo_download_vnf_packages,
            mock_from_db_vnf_package,
            mock_vnf_package):

        # VnfPackageRequest.download_vnf_packages mock Settings
        mock_nfvo_download_vnf_packages.side_effect = \
            nfvo_client.UndefinedExternalSettingException(
                "Vnf package the external setting to 'base_url' undefined.")

        # SyncVnfPackage.create_package
        vnf_package_info = vnfpkgm_fakes.index_response()[0]
        self.assertRaises(
            exc.HTTPNotFound,
            sync.SyncVnfPackage.create_package,
            self.context,
            vnf_package_info)

        # Check if a mock is called even once
        mock_vnf_package.assert_called()
        mock_from_db_vnf_package.assert_called()
        mock_nfvo_download_vnf_packages.assert_called()

    @mock.patch.object(objects.vnf_package, '_vnf_package_create')
    @mock.patch.object(objects.vnf_package.VnfPackage, '_from_db_object')
    @mock.patch.object(nfvo_client.VnfPackageRequest, 'download_vnf_packages')
    def test_package_and_package_vnfd_creation_falieddownloadexcep(self,
            mock_nfvo_download_vnf_packages,
            mock_from_db_vnf_package,
            mock_vnf_package):

        # VnfPackageRequest.download_vnf_packages mock Settings
        vnf_package_zip = ''
        mock_nfvo_download_vnf_packages.side_effect = \
            nfvo_client.FaliedDownloadContentException(
                "Failed response content, vnf_package_zip={}".format(
                    vnf_package_zip))

        # SyncVnfPackage.create_package
        vnf_package_info = vnfpkgm_fakes.index_response()[0]
        self.assertRaises(
            exc.HTTPInternalServerError,
            sync.SyncVnfPackage.create_package,
            self.context,
            vnf_package_info)

        # Check if a mock is called even once
        mock_vnf_package.assert_called()
        mock_from_db_vnf_package.assert_called()
        mock_nfvo_download_vnf_packages.assert_called()

    @mock.patch.object(objects.vnf_package, '_vnf_package_create')
    @mock.patch.object(objects.vnf_package.VnfPackage, '_from_db_object')
    @mock.patch.object(nfvo_client.VnfPackageRequest, 'download_vnf_packages')
    def test_package_and_package_vnfd_creation_exception(self,
            mock_nfvo_download_vnf_packages,
            mock_from_db_vnf_package,
            mock_vnf_package):

        # VnfPackageRequest.download_vnf_packages mock Settings
        mock_nfvo_download_vnf_packages.side_effect = Exception

        # SyncVnfPackage.create_package
        vnf_package_info = vnfpkgm_fakes.index_response()[0]
        self.assertRaises(
            exc.HTTPInternalServerError,
            sync.SyncVnfPackage.create_package,
            self.context,
            vnf_package_info)

        # Check if a mock is called even once
        mock_vnf_package.assert_called()
        mock_from_db_vnf_package.assert_called()
        mock_nfvo_download_vnf_packages.assert_called()

    @mock.patch.object(glance_store, 'store_csar')
    @mock.patch.object(objects.vnf_package, '_vnf_package_create')
    @mock.patch.object(objects.vnf_package.VnfPackage, '_from_db_object')
    @mock.patch.object(nfvo_client.VnfPackageRequest, 'download_vnf_packages')
    def test_package_and_package_vnfd_creation_store_csar_err(self,
            mock_nfvo_download_vnf_packages,
            mock_from_db_vnf_package,
            mock_vnf_package,
            mock_glance_store):

        # glance_store mock Settings
        mock_glance_store.side_effect = Exception

        # SyncVnfPackage.create_package
        vnf_package_info = vnfpkgm_fakes.index_response()[0]
        self.assertRaises(
            exc.HTTPInternalServerError,
            sync.SyncVnfPackage.create_package,
            self.context,
            vnf_package_info)

        # Check if a mock is called even once
        mock_vnf_package.assert_called()
        mock_from_db_vnf_package.assert_called()
        mock_nfvo_download_vnf_packages.assert_called()
        mock_glance_store.assert_called()

    @mock.patch.object(glance_store, 'store_csar')
    @mock.patch.object(objects.vnf_package, '_vnf_package_create')
    @mock.patch.object(objects.vnf_package.VnfPackage, 'save')
    @mock.patch.object(objects.vnf_package.VnfPackage, '_from_db_object')
    @mock.patch.object(nfvo_client.VnfPackageRequest, 'download_vnf_packages')
    def test_package_and_package_vnfd_creation_package_upde_err(self,
            mock_nfvo_download_vnf_packages,
            mock_from_db_vnf_package,
            mock_save_vnf_package,
            mock_vnf_package,
            mock_glance_store):

        # glance_store mock Settings
        mock_glance_store.return_value = 'location', 0, 'checksum',\
                                         'multihash', 'loc_meta'

        # vnf_package mock Settings
        mock_save_vnf_package.side_effect = Exception

        # SyncVnfPackage.create_package
        vnf_package_info = vnfpkgm_fakes.index_response()[0]
        self.assertRaises(
            exc.HTTPInternalServerError,
            sync.SyncVnfPackage.create_package,
            self.context,
            vnf_package_info)

        # Check if a mock is called even once
        mock_nfvo_download_vnf_packages.assert_called()
        mock_from_db_vnf_package.assert_called()
        mock_save_vnf_package.assert_called()
        mock_vnf_package.assert_called()
        mock_glance_store.assert_called()

    @mock.patch.object(glance_store, 'store_csar')
    @mock.patch.object(vnf_pkgm_rpc.VNFPackageRPCAPI,
                       'upload_vnf_package_content')
    @mock.patch.object(objects.vnf_package, '_vnf_package_create')
    @mock.patch.object(objects.vnf_package.VnfPackage, 'save')
    @mock.patch.object(objects.vnf_package.VnfPackage, '_from_db_object')
    @mock.patch.object(nfvo_client.VnfPackageRequest, 'download_vnf_packages')
    def test_package_and_package_vnfd_creation_rpc_err(self,
            mock_nfvo_download_vnf_packages,
            mock_from_db_vnf_package,
            mock_save_vnf_package,
            mock_vnf_package,
            mock_upload_vnf_package_content,
            mock_glance_store):

        # glance_store mock Settings
        mock_glance_store.return_value = 'location', 0, 'checksum',\
                                         'multihash', 'loc_meta'
        mock_upload_vnf_package_content.side_effect = Exception

        # SyncVnfPackage.create_package
        vnf_package_info = vnfpkgm_fakes.index_response()[0]
        self.assertRaises(
            exc.HTTPInternalServerError,
            sync.SyncVnfPackage.create_package,
            self.context,
            vnf_package_info)

        # Check if a mock is called even once
        mock_nfvo_download_vnf_packages.assert_called()
        mock_from_db_vnf_package.assert_called()
        mock_save_vnf_package.assert_called()
        mock_vnf_package.assert_called()
        mock_upload_vnf_package_content.assert_called()
        mock_glance_store.assert_called()

    @mock.patch.object(glance_store, 'store_csar')
    @mock.patch.object(objects.vnf_package_vnfd.VnfPackageVnfd,
                       'get_by_id')
    @mock.patch.object(objects.vnf_package, '_vnf_package_create')
    @mock.patch.object(objects.vnf_package.VnfPackage, 'save')
    @mock.patch.object(objects.vnf_package.VnfPackage, '_from_db_object')
    @mock.patch.object(nfvo_client.VnfPackageRequest, 'download_vnf_packages')
    def test_package_and_get_package_vnfd_err(self,
            mock_nfvo_download_vnf_packages,
            mock_from_db_vnf_package,
            mock_save_vnf_package,
            mock_vnf_package,
            mock_get_by_id,
            mock_glance_store):

        # glance_store mock Settings
        mock_glance_store.return_value = 'location', 0, 'checksum',\
                                         'multihash', 'loc_meta'

        # vnf_package_vnfd mock Settings
        mock_get_by_id.side_effect = Exception

        # SyncVnfPackage.create_package
        vnf_package_info = vnfpkgm_fakes.index_response()[0]
        self.assertRaises(
            exc.HTTPInternalServerError,
            sync.SyncVnfPackage.create_package,
            self.context,
            vnf_package_info)

        # Check if a mock is called even once
        mock_nfvo_download_vnf_packages.assert_called()
        mock_from_db_vnf_package.assert_called()
        mock_save_vnf_package.assert_called()
        mock_vnf_package.assert_called()
        mock_get_by_id.assert_called()
        mock_glance_store.assert_called()
