# Copyright (c) 2019 NTT DATA
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import mock
import os
import shutil
import sys

from tacker.common import csar_utils
from tacker.conductor import conductor_server
from tacker import context
from tacker.glance_store import store as glance_store
from tacker import objects
from tacker.objects import vnf_package
from tacker.tests.unit.conductor import fakes
from tacker.tests.unit.db.base import SqlTestCase
from tacker.tests import uuidsentinel


class TestConductor(SqlTestCase):

    def setUp(self):
        super(TestConductor, self).setUp()
        self.context = context.get_admin_context()
        self.conductor = conductor_server.Conductor('host')
        self.vnf_package = self._create_vnf_package()

    def _create_vnf_package(self):
        vnfpkgm = vnf_package.VnfPackage(context=self.context,
                                         **fakes.VNF_PACKAGE_DATA)
        vnfpkgm.create()
        return vnfpkgm

    @mock.patch.object(conductor_server.Conductor, '_onboard_vnf_package')
    @mock.patch.object(conductor_server, 'revert_upload_vnf_package')
    @mock.patch.object(csar_utils, 'load_csar_data')
    @mock.patch.object(glance_store, 'load_csar')
    def test_upload_vnf_package_content(self, mock_load_csar,
                                        mock_load_csar_data,
                                        mock_revert, mock_onboard):
        mock_load_csar_data.return_value = (mock.ANY, mock.ANY)
        mock_load_csar.return_value = '/var/lib/tacker/5f5d99c6-844a-4c3' \
                                      '1-9e6d-ab21b87dcfff.zip'
        self.conductor.upload_vnf_package_content(
            self.context, self.vnf_package)
        mock_load_csar.assert_called()
        mock_load_csar_data.assert_called()
        mock_onboard.assert_called()

    @mock.patch.object(conductor_server.Conductor, '_onboard_vnf_package')
    @mock.patch.object(glance_store, 'store_csar')
    @mock.patch.object(conductor_server, 'revert_upload_vnf_package')
    @mock.patch.object(csar_utils, 'load_csar_data')
    @mock.patch.object(glance_store, 'load_csar')
    def test_upload_vnf_package_from_uri(self, mock_load_csar,
                                         mock_load_csar_data,
                                         mock_revert, mock_store,
                                         mock_onboard):
        address_information = "http://test.zip"
        mock_load_csar_data.return_value = (mock.ANY, mock.ANY)
        mock_load_csar.return_value = '/var/lib/tacker/5f5d99c6-844a' \
                                      '-4c31-9e6d-ab21b87dcfff.zip'
        mock_store.return_value = 'location', 'size', 'checksum',\
                                  'multihash', 'loc_meta'
        self.conductor.upload_vnf_package_from_uri(self.context,
                                                   self.vnf_package,
                                                   address_information,
                                                   user_name=None,
                                                   password=None)
        mock_load_csar.assert_called()
        mock_load_csar_data.assert_called()
        mock_store.assert_called()
        mock_onboard.assert_called()
        self.assertEqual('multihash', self.vnf_package.hash)
        self.assertEqual('location', self.vnf_package.location_glance_store)

    @mock.patch.object(glance_store, 'delete_csar')
    def test_delete_vnf_package(self, mock_delete_csar):
        self.vnf_package.__setattr__('onboarding_state', 'ONBOARDED')
        self.conductor.delete_vnf_package(self.context, self.vnf_package)
        mock_delete_csar.assert_called()

    @mock.patch.object(os, 'remove')
    @mock.patch.object(shutil, 'rmtree')
    @mock.patch.object(os.path, 'exists')
    @mock.patch.object(vnf_package.VnfPackagesList, 'get_by_filters')
    def test_run_cleanup_vnf_packages(self, mock_get_by_filter,
                                      mock_exists, mock_rmtree,
                                      mock_remove):
        vnf_package_data = {'algorithm': None, 'hash': None,
                            'location_glance_store': None,
                            'onboarding_state': 'CREATED',
                            'operational_state': 'DISABLED',
                            'tenant_id': uuidsentinel.tenant_id,
                            'usage_state': 'NOT_IN_USE',
                            'user_data': {'abc': 'xyz'}
                            }

        vnfpkgm = objects.VnfPackage(context=self.context, **vnf_package_data)
        vnfpkgm.create()
        vnfpkgm.destroy(self.context)

        mock_get_by_filter.return_value = [vnfpkgm]
        mock_exists.return_value = True
        conductor_server.Conductor('host')._run_cleanup_vnf_packages(
            self.context)
        mock_get_by_filter.assert_called()
        mock_rmtree.assert_called()
        mock_remove.assert_called()

    @mock.patch.object(sys, 'exit')
    @mock.patch.object(conductor_server.LOG, 'error')
    @mock.patch.object(glance_store, 'initialize_glance_store')
    @mock.patch.object(os.path, 'isdir')
    def test_init_host(self, mock_isdir, mock_initialize_glance_store,
                       mock_log_error, mock_exit):
        mock_isdir.return_value = False
        self.conductor.init_host()
        mock_log_error.assert_called()
        mock_exit.assert_called_with(1)
        self.assertIn("Config option 'vnf_package_csar_path' is not configured"
                      " correctly. VNF package CSAR path directory %s doesn't"
                      " exist", mock_log_error.call_args[0][0])
