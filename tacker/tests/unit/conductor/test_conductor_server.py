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

import os
import shutil
import sys
from unittest import mock

import fixtures
from glance_store import exceptions as store_exceptions
from oslo_config import cfg
from six.moves import urllib
import six.moves.urllib.error as urlerr
import yaml

from tacker.common import coordination
from tacker.common import csar_utils
from tacker.common import exceptions
from tacker.conductor import conductor_server
import tacker.conf
from tacker import context
from tacker.glance_store import store as glance_store
from tacker import objects
from tacker.objects import fields
from tacker.tests.unit.conductor import fakes
from tacker.tests.unit.db.base import SqlTestCase
from tacker.tests.unit.objects import fakes as fake_obj
from tacker.tests.unit.vnflcm import fakes as vnflcm_fakes
from tacker.tests import utils
from tacker.tests import uuidsentinel

CONF = tacker.conf.CONF


class FakeVnfLcmDriver(mock.Mock):
    pass


class FakeVNFMPlugin(mock.Mock):
    pass


class TestConductor(SqlTestCase):

    def setUp(self):
        super(TestConductor, self).setUp()
        self.addCleanup(mock.patch.stopall)
        self.context = context.get_admin_context()
        self._mock_vnflcm_driver()
        self._mock_vnfm_plugin()
        self.conductor = conductor_server.Conductor('host')
        self.vnf_package = self._create_vnf_package()
        self.temp_dir = self.useFixture(fixtures.TempDir()).path

    def _mock_vnfm_plugin(self):
        self.vnfm_plugin = mock.Mock(wraps=FakeVNFMPlugin())
        fake_vnfm_plugin = mock.Mock()
        fake_vnfm_plugin.return_value = self.vnfm_plugin
        self._mock(
            'tacker.vnfm.plugin.VNFMPlugin', fake_vnfm_plugin)

    def _mock_vnflcm_driver(self):
        self.vnflcm_driver = mock.Mock(wraps=FakeVnfLcmDriver())
        fake_vnflcm_driver = mock.Mock()
        fake_vnflcm_driver.return_value = self.vnflcm_driver
        self._mock(
            'tacker.vnflcm.vnflcm_driver.VnfLcmDriver', fake_vnflcm_driver)

    def _create_vnf_package(self):
        vnfpkgm = objects.VnfPackage(context=self.context,
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
        mock_load_csar_data.return_value = (mock.ANY, mock.ANY, mock.ANY)
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
        mock_load_csar_data.return_value = (mock.ANY, mock.ANY, mock.ANY)
        mock_load_csar.return_value = '/var/lib/tacker/5f5d99c6-844a' \
                                      '-4c31-9e6d-ab21b87dcfff.zip'
        mock_store.return_value = 'location', 0, 'checksum',\
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

    def test_get_vnf_package_vnfd_with_tosca_meta_file_in_csar(self):
        fake_csar = fakes.create_fake_csar_dir(self.vnf_package.id,
                                               self.temp_dir)
        result = self.conductor.get_vnf_package_vnfd(self.context,
                                                     self.vnf_package)
        expected_data = fakes.get_expected_vnfd_data()
        self.assertEqual(expected_data, result)
        shutil.rmtree(fake_csar)

    def test_get_vnf_package_vnfd_with_single_yaml_csar(self):
        fake_csar = fakes.create_fake_csar_dir(
            self.vnf_package.id, self.temp_dir, csar_without_tosca_meta=True)
        result = self.conductor.get_vnf_package_vnfd(self.context,
                                                     self.vnf_package)
        # only one key present in the result shows that it contains only one
        # yaml file
        self.assertEqual(1, len(result.keys()))
        shutil.rmtree(fake_csar)

    @mock.patch.object(glance_store, 'load_csar')
    def test_get_vnf_package_vnfd_download_from_glance_store(self,
                                                             mock_load_csar):
        fake_csar = os.path.join(self.temp_dir, self.vnf_package.id)
        cfg.CONF.set_override('vnf_package_csar_path', self.temp_dir,
                              group='vnf_package')
        fake_csar_zip, _ = utils.create_csar_with_unique_vnfd_id(
            './tacker/tests/etc/samples/etsi/nfv/sample_vnfpkg_tosca_vnfd')
        mock_load_csar.return_value = fake_csar_zip
        expected_data = fakes.get_expected_vnfd_data(zip_file=fake_csar_zip)
        result = self.conductor.get_vnf_package_vnfd(self.context,
                                                     self.vnf_package)
        self.assertEqual(expected_data, result)
        shutil.rmtree(fake_csar)
        os.remove(fake_csar_zip)

    @mock.patch.object(glance_store, 'load_csar')
    def test_get_vnf_package_vnfd_exception_from_glance_store(self,
                                                            mock_load_csar):
        mock_load_csar.side_effect = store_exceptions.NotFound
        self.assertRaises(exceptions.FailedToGetVnfdData,
                          self.conductor.get_vnf_package_vnfd, self.context,
                          self.vnf_package)

    @mock.patch.object(conductor_server.Conductor, '_read_vnfd_files')
    def test_get_vnf_package_vnfd_exception_from_read_vnfd_files(
            self, mock_read_vnfd_files):
        fake_csar = fakes.create_fake_csar_dir(self.vnf_package.id,
                                               self.temp_dir)
        mock_read_vnfd_files.side_effect = yaml.YAMLError
        self.assertRaises(exceptions.FailedToGetVnfdData,
                          self.conductor.get_vnf_package_vnfd, self.context,
                          self.vnf_package)
        shutil.rmtree(fake_csar)

    def _create_and_upload_vnf_package(self):
        vnf_package = objects.VnfPackage(context=self.context,
                                         **fake_obj.vnf_package_data)
        vnf_package.create()

        vnf_pack_vnfd = fake_obj.get_vnf_package_vnfd_data(
            vnf_package.id, uuidsentinel.vnfd_id)

        vnf_pack_vnfd_obj = objects.VnfPackageVnfd(
            context=self.context, **vnf_pack_vnfd)
        vnf_pack_vnfd_obj.create()

        vnf_package.onboarding_state = "ONBOARDED"
        vnf_package.save()

        return vnf_pack_vnfd_obj

    @mock.patch.object(coordination.Coordinator, 'get_lock')
    @mock.patch.object(objects.VnfPackage, 'is_package_in_use')
    def test_instantiate_vnf_instance(self, mock_package_in_use,
            mock_get_lock):
        vnf_package_vnfd = self._create_and_upload_vnf_package()
        vnf_instance_data = fake_obj.get_vnf_instance_data(
            vnf_package_vnfd.vnfd_id)
        mock_package_in_use.return_value = False
        vnf_instance = objects.VnfInstance(context=self.context,
                                           **vnf_instance_data)
        vnf_instance.create()
        instantiate_vnf_req = vnflcm_fakes.get_instantiate_vnf_request_obj()
        self.conductor.instantiate(self.context, vnf_instance,
                                   instantiate_vnf_req)
        self.vnflcm_driver.instantiate_vnf.assert_called_once_with(
            self.context, mock.ANY, instantiate_vnf_req)
        mock_package_in_use.assert_called_once()

    @mock.patch.object(coordination.Coordinator, 'get_lock')
    @mock.patch.object(objects.VnfPackage, 'is_package_in_use')
    @mock.patch('tacker.conductor.conductor_server.LOG')
    def test_instantiate_vnf_instance_already_instantiated(self,
            mock_log, mock_package_in_use, mock_get_lock):
        vnf_package_vnfd = self._create_and_upload_vnf_package()
        vnf_instance_data = fake_obj.get_vnf_instance_data(
            vnf_package_vnfd.vnfd_id)
        vnf_instance_data['instantiation_state'] =\
            fields.VnfInstanceState.INSTANTIATED
        vnf_instance = objects.VnfInstance(context=self.context,
                                           **vnf_instance_data)
        vnf_instance.create()
        instantiate_vnf_req = vnflcm_fakes.get_instantiate_vnf_request_obj()
        self.conductor.instantiate(self.context, vnf_instance,
                                   instantiate_vnf_req)
        self.vnflcm_driver.instantiate_vnf.assert_not_called()
        mock_package_in_use.assert_not_called()
        expected_log = 'Vnf instance %(id)s is already in %(state)s state.'
        mock_log.error.assert_called_once_with(expected_log,
            {'id': vnf_instance.id,
             'state': fields.VnfInstanceState.INSTANTIATED})

    @mock.patch.object(coordination.Coordinator, 'get_lock')
    @mock.patch.object(objects.VnfPackage, 'is_package_in_use')
    def test_instantiate_vnf_instance_with_vnf_package_in_use(self,
            mock_vnf_package_in_use, mock_get_lock):
        vnf_package_vnfd = self._create_and_upload_vnf_package()
        vnf_instance_data = fake_obj.get_vnf_instance_data(
            vnf_package_vnfd.vnfd_id)
        mock_vnf_package_in_use.return_value = True
        vnf_instance = objects.VnfInstance(context=self.context,
                                           **vnf_instance_data)
        vnf_instance.create()
        instantiate_vnf_req = vnflcm_fakes.get_instantiate_vnf_request_obj()
        self.conductor.instantiate(self.context, vnf_instance,
                                   instantiate_vnf_req)
        self.vnflcm_driver.instantiate_vnf.assert_called_once_with(
            self.context, mock.ANY, instantiate_vnf_req)
        mock_vnf_package_in_use.assert_called_once()

    @mock.patch.object(coordination.Coordinator, 'get_lock')
    @mock.patch.object(objects.VnfPackage, 'is_package_in_use')
    @mock.patch('tacker.conductor.conductor_server.LOG')
    def test_instantiate_vnf_instance_failed_with_exception(
            self, mock_log, mock_is_package_in_use, mock_get_lock):
        vnf_package_vnfd = self._create_and_upload_vnf_package()
        vnf_instance_data = fake_obj.get_vnf_instance_data(
            vnf_package_vnfd.vnfd_id)
        vnf_instance = objects.VnfInstance(context=self.context,
                                           **vnf_instance_data)
        vnf_instance.create()
        instantiate_vnf_req = vnflcm_fakes.get_instantiate_vnf_request_obj()
        mock_is_package_in_use.side_effect = Exception
        self.conductor.instantiate(self.context, vnf_instance,
                                   instantiate_vnf_req)
        self.vnflcm_driver.instantiate_vnf.assert_called_once_with(
            self.context, mock.ANY, instantiate_vnf_req)
        mock_is_package_in_use.assert_called_once()
        expected_log = 'Failed to update usage_state of vnf package %s'
        mock_log.error.assert_called_once_with(expected_log,
            vnf_package_vnfd.package_uuid)

    @mock.patch.object(coordination.Coordinator, 'get_lock')
    @mock.patch.object(objects.VnfPackage, 'is_package_in_use')
    def test_terminate_vnf_instance(self, mock_package_in_use, mock_get_lock):
        vnf_package_vnfd = self._create_and_upload_vnf_package()
        vnf_instance_data = fake_obj.get_vnf_instance_data(
            vnf_package_vnfd.vnfd_id)
        mock_package_in_use.return_value = True
        vnf_instance_data['instantiation_state'] =\
            fields.VnfInstanceState.INSTANTIATED
        vnf_instance = objects.VnfInstance(context=self.context,
            **vnf_instance_data)
        vnf_instance.create()

        terminate_vnf_req = objects.TerminateVnfRequest(
            termination_type=fields.VnfInstanceTerminationType.GRACEFUL)

        self.conductor.terminate(self.context, vnf_instance,
                                 terminate_vnf_req)

        self.vnflcm_driver.terminate_vnf.assert_called_once_with(
            self.context, mock.ANY, terminate_vnf_req)
        mock_package_in_use.assert_called_once()

    @mock.patch.object(coordination.Coordinator, 'get_lock')
    @mock.patch.object(objects.VnfPackage, 'is_package_in_use')
    @mock.patch('tacker.conductor.conductor_server.LOG')
    def test_terminate_vnf_instance_already_not_instantiated(self,
            mock_log, mock_package_in_use, mock_get_lock):
        vnf_package_vnfd = self._create_and_upload_vnf_package()
        vnf_instance_data = fake_obj.get_vnf_instance_data(
            vnf_package_vnfd.vnfd_id)
        mock_package_in_use.return_value = True
        vnf_instance_data['instantiation_state'] =\
            fields.VnfInstanceState.NOT_INSTANTIATED
        vnf_instance = objects.VnfInstance(context=self.context,
            **vnf_instance_data)
        vnf_instance.create()

        terminate_vnf_req = objects.TerminateVnfRequest(
            termination_type=fields.VnfInstanceTerminationType.GRACEFUL)

        self.conductor.terminate(self.context, vnf_instance,
                                 terminate_vnf_req)

        self.vnflcm_driver.terminate_vnf.assert_not_called()
        mock_package_in_use.assert_not_called()
        expected_log = ('Terminate action cannot be performed on vnf %(id)s '
                       'which is in %(state)s state.')
        mock_log.error.assert_called_once_with(expected_log,
                {'id': vnf_instance.id,
             'state': fields.VnfInstanceState.NOT_INSTANTIATED})

    @mock.patch.object(coordination.Coordinator, 'get_lock')
    @mock.patch.object(objects.VnfPackage, 'is_package_in_use')
    def test_terminate_vnf_instance_with_usage_state_not_in_use(self,
            mock_vnf_package_is_package_in_use, mock_get_lock):
        vnf_package_vnfd = self._create_and_upload_vnf_package()
        vnf_instance_data = fake_obj.get_vnf_instance_data(
            vnf_package_vnfd.vnfd_id)
        vnf_instance_data['instantiation_state'] =\
            fields.VnfInstanceState.INSTANTIATED
        vnf_instance = objects.VnfInstance(context=self.context,
            **vnf_instance_data)
        vnf_instance.create()

        mock_vnf_package_is_package_in_use.return_value = False
        terminate_vnf_req = objects.TerminateVnfRequest(
            termination_type=fields.VnfInstanceTerminationType.GRACEFUL)

        self.conductor.terminate(self.context, vnf_instance,
                                 terminate_vnf_req)

        self.vnflcm_driver.terminate_vnf.assert_called_once_with(
            self.context, mock.ANY, terminate_vnf_req)
        mock_vnf_package_is_package_in_use.assert_called_once()

    @mock.patch.object(coordination.Coordinator, 'get_lock')
    @mock.patch.object(objects.VnfPackage, 'is_package_in_use')
    def test_terminate_vnf_instance_with_usage_state_already_in_use(self,
            mock_vnf_package_is_package_in_use, mock_get_lock):
        vnf_package_vnfd = self._create_and_upload_vnf_package()
        vnf_instance_data = fake_obj.get_vnf_instance_data(
            vnf_package_vnfd.vnfd_id)
        vnf_instance_data['instantiation_state'] =\
            fields.VnfInstanceState.INSTANTIATED
        vnf_instance = objects.VnfInstance(context=self.context,
            **vnf_instance_data)
        vnf_instance.create()

        mock_vnf_package_is_package_in_use.return_value = True
        terminate_vnf_req = objects.TerminateVnfRequest(
            termination_type=fields.VnfInstanceTerminationType.GRACEFUL)

        self.conductor.terminate(self.context, vnf_instance,
                                 terminate_vnf_req)

        self.vnflcm_driver.terminate_vnf.assert_called_once_with(
            self.context, mock.ANY, terminate_vnf_req)
        mock_vnf_package_is_package_in_use.assert_called_once()

    @mock.patch.object(coordination.Coordinator, 'get_lock')
    @mock.patch.object(objects.VnfPackage, 'is_package_in_use')
    @mock.patch('tacker.conductor.conductor_server.LOG')
    def test_terminate_vnf_instance_failed_to_update_usage_state(
            self, mock_log, mock_is_package_in_use, mock_get_lock):
        vnf_package_vnfd = self._create_and_upload_vnf_package()
        vnf_instance_data = fake_obj.get_vnf_instance_data(
            vnf_package_vnfd.vnfd_id)
        vnf_instance_data['instantiation_state'] =\
            fields.VnfInstanceState.INSTANTIATED
        vnf_instance = objects.VnfInstance(context=self.context,
                                           **vnf_instance_data)
        vnf_instance.create()
        terminate_vnf_req = objects.TerminateVnfRequest(
            termination_type=fields.VnfInstanceTerminationType.GRACEFUL)
        mock_is_package_in_use.side_effect = Exception
        self.conductor.terminate(self.context, vnf_instance,
                                 terminate_vnf_req)
        self.vnflcm_driver.terminate_vnf.assert_called_once_with(
            self.context, mock.ANY, terminate_vnf_req)
        expected_msg = "Failed to update usage_state of vnf package %s"
        mock_log.error.assert_called_once_with(expected_msg,
            vnf_package_vnfd.package_uuid)

    @mock.patch.object(coordination.Coordinator, 'get_lock')
    def test_heal_vnf_instance(self, mock_get_lock):
        vnf_package_vnfd = self._create_and_upload_vnf_package()
        vnf_instance_data = fake_obj.get_vnf_instance_data(
            vnf_package_vnfd.vnfd_id)
        vnf_instance = objects.VnfInstance(context=self.context,
                                           **vnf_instance_data)
        vnf_instance.create()
        vnf_instance.instantiation_state = \
            fields.VnfInstanceState.INSTANTIATED
        vnf_instance.save()
        heal_vnf_req = objects.HealVnfRequest(cause="healing request")
        self.conductor.heal(self.context, vnf_instance, heal_vnf_req)
        self.vnflcm_driver.heal_vnf.assert_called_once_with(
            self.context, mock.ANY, heal_vnf_req)

    @mock.patch.object(coordination.Coordinator, 'get_lock')
    @mock.patch('tacker.conductor.conductor_server.LOG')
    def test_heal_vnf_instance_already_not_instantiated(self,
            mock_log, mock_get_lock):
        vnf_package_vnfd = self._create_and_upload_vnf_package()
        vnf_instance_data = fake_obj.get_vnf_instance_data(
            vnf_package_vnfd.vnfd_id)

        vnf_instance_data['instantiation_state'] =\
            fields.VnfInstanceState.NOT_INSTANTIATED
        vnf_instance = objects.VnfInstance(context=self.context,
                                           **vnf_instance_data)
        vnf_instance.create()

        heal_vnf_req = objects.HealVnfRequest(cause="healing request")
        self.conductor.heal(self.context, vnf_instance, heal_vnf_req)

        self.vnflcm_driver.heal_vnf.assert_not_called()
        expected_log = ('Heal action cannot be performed on vnf %(id)s '
                        'which is in %(state)s state.')
        mock_log.error.assert_called_once_with(expected_log,
            {'id': vnf_instance.id,
             'state': fields.VnfInstanceState.NOT_INSTANTIATED})

    @mock.patch.object(os, 'remove')
    @mock.patch.object(shutil, 'rmtree')
    @mock.patch.object(os.path, 'exists')
    @mock.patch.object(objects.VnfPackagesList, 'get_by_filters')
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

    @mock.patch.object(urllib.request, 'urlopen')
    def test_upload_vnf_package_from_uri_with_invalid_auth(self,
                                                           mock_url_open):
        address_information = "http://localhost/test.zip"
        user_name = "username"
        password = "password"
        mock_url_open.side_effect = urlerr.HTTPError(
            url='', code=401, msg='HTTP Error 401 Unauthorized', hdrs={},
            fp=None)
        self.assertRaises(exceptions.VNFPackageURLInvalid,
                          self.conductor.upload_vnf_package_from_uri,
                          self.context,
                          self.vnf_package,
                          address_information,
                          user_name=user_name,
                          password=password)
        self.assertEqual('CREATED', self.vnf_package.onboarding_state)
