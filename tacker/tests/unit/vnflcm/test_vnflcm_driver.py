# Copyright (c) 2020 NTT DATA
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
from unittest import mock

import fixtures
from oslo_config import cfg

from tacker.common import exceptions
from tacker.common import utils
from tacker import context
from tacker import objects
from tacker.objects import fields
from tacker.tests.unit.db import base as db_base
from tacker.tests.unit.vnflcm import fakes
from tacker.tests import utils as test_utils
from tacker.tests import uuidsentinel
from tacker.vnflcm import vnflcm_driver
from tacker.vnfm import vim_client


class InfraDriverException(Exception):
    pass


class FakeDriverManager(mock.Mock):
    def __init__(self, fail_method_name=None, vnf_resource_count=1):
        super(FakeDriverManager, self).__init__()
        self.fail_method_name = fail_method_name
        self.vnf_resource_count = vnf_resource_count

    def invoke(self, *args, **kwargs):
        if 'pre_instantiation_vnf' in args:
            vnf_resource_list = [fakes.return_vnf_resource() for index in
                range(self.vnf_resource_count)]
            return {'node_name': vnf_resource_list}
        if 'instantiate_vnf' in args:
            if self.fail_method_name and \
                    self.fail_method_name == 'instantiate_vnf':
                raise InfraDriverException("instantiate_vnf failed")

            instance_id = uuidsentinel.instance_id
            vnfd_dict = kwargs.get('vnfd_dict')
            vnfd_dict['instance_id'] = instance_id
            return instance_id
        if 'create_wait' in args:
            if self.fail_method_name and \
                    self.fail_method_name == 'create_wait':
                raise InfraDriverException("create_wait failed")
        elif 'post_vnf_instantiation' in args:
            pass
        if 'delete' in args:
            if self.fail_method_name and \
                    self.fail_method_name == 'delete':
                raise InfraDriverException("delete failed")
        if 'delete_wait' in args:
            if self.fail_method_name and \
                    self.fail_method_name == 'delete_wait':
                raise InfraDriverException("delete_wait failed")
        if 'delete_vnf_instance_resource' in args:
            if self.fail_method_name and \
                    self.fail_method_name == 'delete_vnf_resource':
                raise InfraDriverException("delete_vnf_resource failed")
        elif 'heal_vnf' in args:
            if self.fail_method_name and \
                    self.fail_method_name == 'heal_vnf':
                raise InfraDriverException("heal_vnf failed")
        elif 'heal_vnf_wait' in args:
            if self.fail_method_name and \
                    self.fail_method_name == 'heal_vnf_wait':
                raise InfraDriverException("heal_vnf_wait failed")
        elif 'post_heal_vnf' in args:
            if self.fail_method_name and \
                    self.fail_method_name == 'post_heal_vnf':
                raise InfraDriverException("post_heal_vnf failed")


class FakeVimClient(mock.Mock):
    pass


class TestVnflcmDriver(db_base.SqlTestCase):

    def setUp(self):
        super(TestVnflcmDriver, self).setUp()
        self.addCleanup(mock.patch.stopall)
        self.context = context.get_admin_context()
        self._mock_vim_client()
        self._stub_get_vim()
        self.temp_dir = self.useFixture(fixtures.TempDir()).path

    def _mock_vnf_manager(self, fail_method_name=None, vnf_resource_count=1):
        self._vnf_manager = mock.Mock(wraps=FakeDriverManager(
            fail_method_name=fail_method_name,
            vnf_resource_count=vnf_resource_count))
        self._vnf_manager.__contains__ = mock.Mock(
            return_value=True)
        fake_vnf_manager = mock.Mock()
        fake_vnf_manager.return_value = self._vnf_manager
        self._mock(
            'tacker.common.driver_manager.DriverManager', fake_vnf_manager)

    def _mock_vim_client(self):
        self.vim_client = mock.Mock(wraps=FakeVimClient())
        fake_vim_client = mock.Mock()
        fake_vim_client.return_value = self.vim_client
        self._mock(
            'tacker.vnfm.vim_client.VimClient', fake_vim_client)

    def _stub_get_vim(self):
        vim_obj = {'vim_id': '6261579e-d6f3-49ad-8bc3-a9cb974778ff',
                   'vim_name': 'fake_vim', 'vim_auth':
                       {'auth_url': 'http://localhost/identity', 'password':
                           'test_pw', 'username': 'test_user', 'project_name':
                           'test_project'}, 'vim_type': 'openstack'}
        self.vim_client.get_vim.return_value = vim_obj

    @mock.patch.object(objects.VnfResource, 'create')
    @mock.patch.object(objects.VnfPackageVnfd, 'get_by_id')
    @mock.patch.object(objects.VnfInstance, "save")
    def test_instantiate_vnf(self, mock_vnf_instance_save,
                             mock_vnf_package_vnfd, mock_create):
        vnf_package_vnfd = fakes.return_vnf_package_vnfd()
        vnf_package_id = vnf_package_vnfd.package_uuid
        mock_vnf_package_vnfd.return_value = vnf_package_vnfd
        instantiate_vnf_req_dict = fakes.get_dummy_instantiate_vnf_request()
        instantiate_vnf_req_obj = \
            objects.InstantiateVnfRequest.obj_from_primitive(
                instantiate_vnf_req_dict, self.context)
        vnf_instance_obj = fakes.return_vnf_instance()

        fake_csar = os.path.join(self.temp_dir, vnf_package_id)
        cfg.CONF.set_override('vnf_package_csar_path', self.temp_dir,
                              group='vnf_package')
        test_utils.copy_csar_files(fake_csar, "vnflcm4")
        self._mock_vnf_manager()
        driver = vnflcm_driver.VnfLcmDriver()
        driver.instantiate_vnf(self.context, vnf_instance_obj,
                               instantiate_vnf_req_obj)

        self.assertEqual("INSTANTIATED", vnf_instance_obj.instantiation_state)
        self.assertEqual(2, mock_vnf_instance_save.call_count)
        self.assertEqual(4, self._vnf_manager.invoke.call_count)
        shutil.rmtree(fake_csar)

    @mock.patch.object(objects.VnfResource, 'create')
    @mock.patch.object(objects.VnfPackageVnfd, 'get_by_id')
    @mock.patch.object(objects.VnfInstance, "save")
    def test_instantiate_vnf_with_ext_virtual_links(
            self, mock_vnf_instance_save, mock_vnf_package_vnfd, mock_create):
        vnf_package_vnfd = fakes.return_vnf_package_vnfd()
        vnf_package_id = vnf_package_vnfd.package_uuid
        mock_vnf_package_vnfd.return_value = vnf_package_vnfd
        req_body = fakes.get_instantiate_vnf_request_with_ext_virtual_links()
        instantiate_vnf_req_dict = utils.convert_camelcase_to_snakecase(
            req_body)
        instantiate_vnf_req_obj = \
            objects.InstantiateVnfRequest.obj_from_primitive(
                instantiate_vnf_req_dict, self.context)
        vnf_instance_obj = fakes.return_vnf_instance()

        fake_csar = os.path.join(self.temp_dir, vnf_package_id)
        cfg.CONF.set_override('vnf_package_csar_path', self.temp_dir,
                              group='vnf_package')
        test_utils.copy_csar_files(fake_csar, "vnflcm4")
        self._mock_vnf_manager()
        driver = vnflcm_driver.VnfLcmDriver()
        driver.instantiate_vnf(self.context, vnf_instance_obj,
                               instantiate_vnf_req_obj)

        self.assertEqual("INSTANTIATED", vnf_instance_obj.instantiation_state)
        self.assertEqual(2, mock_vnf_instance_save.call_count)
        self.assertEqual(4, self._vnf_manager.invoke.call_count)
        shutil.rmtree(fake_csar)

    @mock.patch.object(objects.VnfResource, 'create')
    @mock.patch.object(objects.VnfPackageVnfd, 'get_by_id')
    @mock.patch.object(objects.VnfInstance, "save")
    def test_instantiate_vnf_vim_connection_info(
            self, mock_vnf_instance_save, mock_vnf_package_vnfd, mock_create):
        vnf_package_vnfd = fakes.return_vnf_package_vnfd()
        vnf_package_id = vnf_package_vnfd.package_uuid
        mock_vnf_package_vnfd.return_value = vnf_package_vnfd
        vim_connection_info = fakes.get_dummy_vim_connection_info()
        instantiate_vnf_req_dict = \
            fakes.get_dummy_instantiate_vnf_request(**vim_connection_info)
        instantiate_vnf_req_obj = \
            objects.InstantiateVnfRequest.obj_from_primitive(
                instantiate_vnf_req_dict, self.context)
        vnf_instance_obj = fakes.return_vnf_instance()

        fake_csar = os.path.join(self.temp_dir, vnf_package_id)
        cfg.CONF.set_override('vnf_package_csar_path', self.temp_dir,
                              group='vnf_package')
        test_utils.copy_csar_files(fake_csar, "vnflcm4")
        self._mock_vnf_manager()
        driver = vnflcm_driver.VnfLcmDriver()
        driver.instantiate_vnf(self.context, vnf_instance_obj,
                               instantiate_vnf_req_obj)

        self.assertEqual("INSTANTIATED", vnf_instance_obj.instantiation_state)
        self.assertEqual(2, mock_vnf_instance_save.call_count)
        self.assertEqual(4, self._vnf_manager.invoke.call_count)
        shutil.rmtree(fake_csar)

    @mock.patch.object(objects.VnfResource, 'create')
    @mock.patch.object(objects.VnfPackageVnfd, 'get_by_id')
    @mock.patch.object(objects.VnfInstance, "save")
    def test_instantiate_vnf_infra_fails_to_instantiate(
            self, mock_vnf_instance_save, mock_vnf_package_vnfd, mock_create):
        vnf_package_vnfd = fakes.return_vnf_package_vnfd()
        vnf_package_id = vnf_package_vnfd.package_uuid
        mock_vnf_package_vnfd.return_value = vnf_package_vnfd
        vim_connection_info = fakes.get_dummy_vim_connection_info()
        instantiate_vnf_req_dict = \
            fakes.get_dummy_instantiate_vnf_request(**vim_connection_info)
        instantiate_vnf_req_obj = \
            objects.InstantiateVnfRequest.obj_from_primitive(
                instantiate_vnf_req_dict, self.context)
        vnf_instance_obj = fakes.return_vnf_instance()

        fake_csar = os.path.join(self.temp_dir, vnf_package_id)
        cfg.CONF.set_override('vnf_package_csar_path', self.temp_dir,
                              group='vnf_package')
        test_utils.copy_csar_files(fake_csar, "vnflcm4")
        self._mock_vnf_manager(fail_method_name="instantiate_vnf")
        driver = vnflcm_driver.VnfLcmDriver()
        error = self.assertRaises(exceptions.VnfInstantiationFailed,
            driver.instantiate_vnf, self.context, vnf_instance_obj,
            instantiate_vnf_req_obj)
        expected_error = ("Vnf instantiation failed for vnf %s, error: "
                          "instantiate_vnf failed")

        self.assertEqual(expected_error % vnf_instance_obj.id, str(error))
        self.assertEqual("NOT_INSTANTIATED",
            vnf_instance_obj.instantiation_state)
        self.assertEqual(2, mock_vnf_instance_save.call_count)
        self.assertEqual(2, self._vnf_manager.invoke.call_count)

        shutil.rmtree(fake_csar)

    @mock.patch.object(objects.VnfResource, 'create')
    @mock.patch.object(objects.VnfPackageVnfd, 'get_by_id')
    @mock.patch.object(objects.VnfInstance, "save")
    def test_instantiate_vnf_infra_fails_to_wait_after_instantiate(
            self, mock_vnf_instance_save, mock_vnf_package_vnfd, mock_create):
        vnf_package_vnfd = fakes.return_vnf_package_vnfd()
        vnf_package_id = vnf_package_vnfd.package_uuid
        mock_vnf_package_vnfd.return_value = vnf_package_vnfd
        vim_connection_info = fakes.get_dummy_vim_connection_info()
        instantiate_vnf_req_dict = \
            fakes.get_dummy_instantiate_vnf_request(**vim_connection_info)
        instantiate_vnf_req_obj = \
            objects.InstantiateVnfRequest.obj_from_primitive(
                instantiate_vnf_req_dict, self.context)
        vnf_instance_obj = fakes.return_vnf_instance()

        fake_csar = os.path.join(self.temp_dir, vnf_package_id)
        cfg.CONF.set_override('vnf_package_csar_path', self.temp_dir,
                              group='vnf_package')
        test_utils.copy_csar_files(fake_csar, "vnflcm4")
        self._mock_vnf_manager(fail_method_name='create_wait')
        driver = vnflcm_driver.VnfLcmDriver()
        error = self.assertRaises(exceptions.VnfInstantiationWaitFailed,
            driver.instantiate_vnf, self.context, vnf_instance_obj,
            instantiate_vnf_req_obj)
        expected_error = ("Vnf instantiation wait failed for vnf %s, error: "
                          "create_wait failed")

        self.assertEqual(expected_error % vnf_instance_obj.id, str(error))
        self.assertEqual("NOT_INSTANTIATED",
            vnf_instance_obj.instantiation_state)
        self.assertEqual(3, mock_vnf_instance_save.call_count)
        self.assertEqual(5, self._vnf_manager.invoke.call_count)

        shutil.rmtree(fake_csar)

    @mock.patch.object(objects.VnfResource, 'create')
    @mock.patch.object(objects.VnfPackageVnfd, 'get_by_id')
    @mock.patch.object(objects.VnfInstance, "save")
    def test_instantiate_vnf_with_short_notation(self, mock_vnf_instance_save,
                             mock_vnf_package_vnfd, mock_create):
        vnf_package_vnfd = fakes.return_vnf_package_vnfd()
        vnf_package_id = vnf_package_vnfd.package_uuid
        mock_vnf_package_vnfd.return_value = vnf_package_vnfd
        instantiate_vnf_req_dict = fakes.get_dummy_instantiate_vnf_request()
        instantiate_vnf_req_obj = \
            objects.InstantiateVnfRequest.obj_from_primitive(
                instantiate_vnf_req_dict, self.context)
        vnf_instance_obj = fakes.return_vnf_instance()

        fake_csar = os.path.join(self.temp_dir, vnf_package_id)
        cfg.CONF.set_override('vnf_package_csar_path', self.temp_dir,
                              group='vnf_package')
        test_utils.copy_csar_files(
            fake_csar, "sample_vnf_package_csar_with_short_notation")
        self._mock_vnf_manager(vnf_resource_count=2)
        driver = vnflcm_driver.VnfLcmDriver()
        driver.instantiate_vnf(self.context, vnf_instance_obj,
                               instantiate_vnf_req_obj)
        self.assertEqual(2, mock_create.call_count)
        self.assertEqual("INSTANTIATED", vnf_instance_obj.instantiation_state)
        shutil.rmtree(fake_csar)

    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch.object(vim_client.VimClient, "get_vim")
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    @mock.patch.object(objects.VnfResource, "destroy")
    def test_terminate_vnf(self, mock_resource_destroy, mock_resource_list,
            mock_vim, mock_vnf_instance_save):
        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED)
        vnf_instance.instantiated_vnf_info.instance_id =\
            uuidsentinel.instance_id

        mock_resource_list.return_value = [fakes.return_vnf_resource()]
        terminate_vnf_req = objects.TerminateVnfRequest(
            termination_type=fields.VnfInstanceTerminationType.FORCEFUL)

        self._mock_vnf_manager()
        driver = vnflcm_driver.VnfLcmDriver()
        driver.terminate_vnf(self.context, vnf_instance, terminate_vnf_req)
        self.assertEqual(2, mock_vnf_instance_save.call_count)
        self.assertEqual(1, mock_resource_destroy.call_count)
        self.assertEqual(3, self._vnf_manager.invoke.call_count)

    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch.object(vim_client.VimClient, "get_vim")
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    @mock.patch.object(objects.VnfResource, "destroy")
    def test_terminate_vnf_graceful_no_timeout(self, mock_resource_destroy,
            mock_resource_list, mock_vim, mock_vnf_instance_save):
        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED)
        vnf_instance.instantiated_vnf_info.instance_id =\
            uuidsentinel.instance_id

        mock_resource_list.return_value = [fakes.return_vnf_resource()]
        terminate_vnf_req = objects.TerminateVnfRequest(
            termination_type=fields.VnfInstanceTerminationType.GRACEFUL)

        self._mock_vnf_manager()
        driver = vnflcm_driver.VnfLcmDriver()
        driver.terminate_vnf(self.context, vnf_instance, terminate_vnf_req)
        self.assertEqual(2, mock_vnf_instance_save.call_count)
        self.assertEqual(1, mock_resource_destroy.call_count)

    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch.object(vim_client.VimClient, "get_vim")
    def test_terminate_vnf_delete_instance_failed(self, mock_vim,
            mock_vnf_instance_save):
        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED)
        vnf_instance.instantiated_vnf_info.instance_id =\
            uuidsentinel.instance_id
        terminate_vnf_req = objects.TerminateVnfRequest(
            termination_type=fields.VnfInstanceTerminationType.GRACEFUL,
            graceful_termination_timeout=10)

        self._mock_vnf_manager(fail_method_name='delete')
        driver = vnflcm_driver.VnfLcmDriver()
        error = self.assertRaises(InfraDriverException, driver.terminate_vnf,
            self.context, vnf_instance, terminate_vnf_req)
        self.assertEqual("delete failed", str(error))
        self.assertEqual(1, mock_vnf_instance_save.call_count)
        self.assertEqual(1, self._vnf_manager.invoke.call_count)

    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch.object(vim_client.VimClient, "get_vim")
    def test_terminate_vnf_delete_wait_instance_failed(self, mock_vim,
            mock_vnf_instance_save):
        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED)
        vnf_instance.instantiated_vnf_info.instance_id =\
            uuidsentinel.instance_id
        terminate_vnf_req = objects.TerminateVnfRequest(
            termination_type=fields.VnfInstanceTerminationType.FORCEFUL)

        self._mock_vnf_manager(fail_method_name='delete_wait')
        driver = vnflcm_driver.VnfLcmDriver()
        error = self.assertRaises(InfraDriverException, driver.terminate_vnf,
            self.context, vnf_instance, terminate_vnf_req)
        self.assertEqual("delete_wait failed", str(error))
        self.assertEqual(2, mock_vnf_instance_save.call_count)
        self.assertEqual(2, self._vnf_manager.invoke.call_count)

    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch.object(vim_client.VimClient, "get_vim")
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_terminate_vnf_delete_vnf_resource_failed(self, mock_resource_list,
            mock_vim, mock_vnf_instance_save):
        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED)
        vnf_instance.instantiated_vnf_info.instance_id =\
            uuidsentinel.instance_id
        terminate_vnf_req = objects.TerminateVnfRequest(
            termination_type=fields.VnfInstanceTerminationType.FORCEFUL)

        mock_resource_list.return_value = [fakes.return_vnf_resource()]
        self._mock_vnf_manager(fail_method_name='delete_vnf_resource')
        driver = vnflcm_driver.VnfLcmDriver()
        error = self.assertRaises(InfraDriverException, driver.terminate_vnf,
            self.context, vnf_instance, terminate_vnf_req)
        self.assertEqual("delete_vnf_resource failed", str(error))
        self.assertEqual(2, mock_vnf_instance_save.call_count)
        self.assertEqual(3, self._vnf_manager.invoke.call_count)

    @mock.patch.object(objects.VnfPackageVnfd, 'get_by_id')
    @mock.patch.object(vim_client.VimClient, "get_vim")
    @mock.patch.object(objects.VnfResource, "create")
    @mock.patch.object(objects.VnfResource, "destroy")
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch('tacker.vnflcm.vnflcm_driver.LOG')
    def test_heal_vnf_without_vnfc_instance(self, mock_log, mock_save,
            mock_vnf_resource_list, mock_resource_destroy,
            mock_resource_create, mock_vim, mock_vnf_package_vnfd):
        vnf_package_vnfd = fakes.return_vnf_package_vnfd()
        vnf_package_id = vnf_package_vnfd.package_uuid
        mock_vnf_package_vnfd.return_value = vnf_package_vnfd

        fake_csar = os.path.join(self.temp_dir, vnf_package_id)
        cfg.CONF.set_override('vnf_package_csar_path', self.temp_dir,
                              group='vnf_package')
        test_utils.copy_csar_files(fake_csar, "vnflcm4")
        mock_vnf_resource_list.return_value = [fakes.return_vnf_resource()]
        # Heal as per SOL003 i.e. without vnfcInstanceId
        heal_vnf_req = objects.HealVnfRequest()

        vim_obj = {'vim_id': uuidsentinel.vim_id,
                   'vim_name': 'fake_vim',
                   'vim_type': 'openstack',
                   'vim_auth': {
                       'auth_url': 'http://localhost/identity',
                       'password': 'test_pw',
                       'username': 'test_user',
                       'project_name': 'test_project'}}

        mock_vim.return_value = vim_obj

        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED)

        vnf_instance.instantiated_vnf_info.instance_id =\
            uuidsentinel.instance_id
        self._mock_vnf_manager()
        driver = vnflcm_driver.VnfLcmDriver()
        driver.heal_vnf(self.context, vnf_instance, heal_vnf_req)
        self.assertEqual(1, mock_save.call_count)
        # vnf resource software images will be deleted during
        # deleting vnf instance.
        self.assertEqual(1, mock_resource_destroy.call_count)
        # Vnf resource software images will be created during
        # instantiation.
        self.assertEqual(1, mock_resource_create.call_count)
        # Invoke will be called 7 times, 3 for deleting the vnf
        # resources  and 4 during instantiation.
        self.assertEqual(7, self._vnf_manager.invoke.call_count)
        expected_msg = ("Request received for healing vnf '%s' "
                       "is completed successfully")
        mock_log.info.assert_called_with(expected_msg,
            vnf_instance.id)

        shutil.rmtree(fake_csar)

    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch('tacker.vnflcm.vnflcm_driver.LOG')
    def test_heal_vnf_without_vnfc_instance_infra_delete_fail(self, mock_log,
            mock_save):
        # Heal as per SOL003 i.e. without vnfcInstanceId
        heal_vnf_req = objects.HealVnfRequest()

        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED)

        vnf_instance.instantiated_vnf_info.instance_id =\
            uuidsentinel.instance_id
        self._mock_vnf_manager(fail_method_name='delete')
        driver = vnflcm_driver.VnfLcmDriver()
        self.assertRaises(exceptions.VnfHealFailed,
            driver.heal_vnf, self.context, vnf_instance, heal_vnf_req)
        self.assertEqual(1, mock_save.call_count)
        self.assertEqual(1, self._vnf_manager.invoke.call_count)
        self.assertEqual(fields.VnfInstanceTaskState.ERROR,
            vnf_instance.task_state)
        expected_msg = ('Failed to delete vnf resources for vnf instance %s '
                        'before respawning. The vnf is in inconsistent '
                        'state. Error: delete failed')
        mock_log.error.assert_called_with(expected_msg % vnf_instance.id)

    @mock.patch.object(objects.VnfPackageVnfd, 'get_by_id')
    @mock.patch.object(vim_client.VimClient, "get_vim")
    @mock.patch.object(objects.VnfResource, "create")
    @mock.patch.object(objects.VnfResource, "destroy")
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch('tacker.vnflcm.vnflcm_driver.LOG')
    def test_heal_vnf_without_vnfc_instance_infra_instantiate_vnf_fail(self,
            mock_log, mock_save, mock_vnf_resource_list,
            mock_resource_destroy, mock_resource_create, mock_vim,
            mock_vnf_package_vnfd):
        vnf_package_vnfd = fakes.return_vnf_package_vnfd()
        vnf_package_id = vnf_package_vnfd.package_uuid
        mock_vnf_package_vnfd.return_value = vnf_package_vnfd

        fake_csar = os.path.join(self.temp_dir, vnf_package_id)
        cfg.CONF.set_override('vnf_package_csar_path', self.temp_dir,
                              group='vnf_package')
        test_utils.copy_csar_files(fake_csar, "vnflcm4")
        mock_vnf_resource_list.return_value = [fakes.return_vnf_resource()]
        # Heal as per SOL003 i.e. without vnfcInstanceId
        heal_vnf_req = objects.HealVnfRequest()

        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED)

        vnf_instance.instantiated_vnf_info.instance_id =\
            uuidsentinel.instance_id
        self._mock_vnf_manager(fail_method_name='instantiate_vnf')
        driver = vnflcm_driver.VnfLcmDriver()
        self.assertRaises(exceptions.VnfHealFailed,
            driver.heal_vnf, self.context, vnf_instance, heal_vnf_req)
        self.assertEqual(1, mock_save.call_count)
        # vnf resource software images will be deleted during
        # deleting vnf instance.
        self.assertEqual(1, mock_resource_destroy.call_count)
        # Vnf resource software images will be created during
        # instantiation.
        self.assertEqual(1, mock_resource_create.call_count)

        self.assertEqual(5, self._vnf_manager.invoke.call_count)
        self.assertEqual(fields.VnfInstanceTaskState.ERROR,
            vnf_instance.task_state)
        expected_msg = ('Failed to instantiate vnf instance %s '
                        'after termination. The vnf is in inconsistent '
                        'state. Error: Vnf instantiation failed for vnf %s, '
                        'error: instantiate_vnf failed')
        mock_log.error.assert_called_with(expected_msg % (vnf_instance.id,
            vnf_instance.id))

    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch('tacker.vnflcm.vnflcm_driver.LOG')
    def test_heal_vnf_with_vnfc_instance(self, mock_log, mock_save):
        heal_vnf_req = objects.HealVnfRequest(vnfc_instance_id=[
            uuidsentinel.vnfc_instance_id_1])

        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED,
            task_state=fields.VnfInstanceTaskState.HEALING)

        self._mock_vnf_manager()
        driver = vnflcm_driver.VnfLcmDriver()
        driver.heal_vnf(self.context, vnf_instance, heal_vnf_req)
        self.assertEqual(1, mock_save.call_count)
        self.assertEqual(3, self._vnf_manager.invoke.call_count)

        self.assertEqual(None, vnf_instance.task_state)
        expected_msg = ("Request received for healing vnf '%s' "
                       "is completed successfully")
        mock_log.info.assert_called_with(expected_msg,
            vnf_instance.id)

    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch('tacker.vnflcm.vnflcm_driver.LOG')
    def test_heal_vnf_with_infra_heal_vnf_fail(self, mock_log, mock_save):
        heal_vnf_req = objects.HealVnfRequest(vnfc_instance_id=[
            uuidsentinel.vnfc_instance_id_1])

        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED,
            task_state=fields.VnfInstanceTaskState.HEALING)

        self._mock_vnf_manager(fail_method_name='heal_vnf')
        driver = vnflcm_driver.VnfLcmDriver()
        self.assertRaises(exceptions.VnfHealFailed,
            driver.heal_vnf, self.context, vnf_instance,
            heal_vnf_req)
        self.assertEqual(1, mock_save.call_count)
        self.assertEqual(1, self._vnf_manager.invoke.call_count)

        self.assertEqual(fields.VnfInstanceTaskState.ERROR,
            vnf_instance.task_state)
        expected_msg = ("Failed to heal vnf %(id)s in infra driver. "
                       "Error: %(error)s")
        mock_log.error.assert_called_with(expected_msg,
            {'id': vnf_instance.id, 'error': 'heal_vnf failed'})

    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch('tacker.vnflcm.vnflcm_driver.LOG')
    def test_heal_vnf_with_infra_heal_vnf_wait_fail(self, mock_log,
            mock_save):
        heal_vnf_req = objects.HealVnfRequest(vnfc_instance_id=[
            uuidsentinel.vnfc_instance_id_1])

        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED,
            task_state=fields.VnfInstanceTaskState.HEALING)

        vnf_instance.instantiated_vnf_info.instance_id =\
            uuidsentinel.instance_id
        self._mock_vnf_manager(fail_method_name='heal_vnf_wait')
        driver = vnflcm_driver.VnfLcmDriver()
        # It won't raise any exception if infra driver raises
        # heal_vnf_wait because there is a possibility the vnfc
        # resources could go into inconsistent state so it would
        # proceed further and call post_heal_vnf with a hope
        # it will work and vnflcm can update the vnfc resources
        # properly and hence the _vnf_manager.invoke.call_count
        # should be 3 instead of 2.
        driver.heal_vnf(self.context, vnf_instance, heal_vnf_req)
        self.assertEqual(1, mock_save.call_count)
        self.assertEqual(3, self._vnf_manager.invoke.call_count)

        self.assertEqual(None, vnf_instance.task_state)
        expected_msg = ('Failed to update vnf %(id)s resources for '
                        'instance %(instance)s. Error: %(error)s')
        mock_log.error.assert_called_with(expected_msg,
            {'id': vnf_instance.id,
             'instance': vnf_instance.instantiated_vnf_info.instance_id,
             'error': 'heal_vnf_wait failed'})

    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch('tacker.vnflcm.vnflcm_driver.LOG')
    def test_heal_vnf_with_infra_post_heal_vnf_fail(self, mock_log,
            mock_save):
        heal_vnf_req = objects.HealVnfRequest(vnfc_instance_id=[
            uuidsentinel.vnfc_instance_id_1])

        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED,
            task_state=fields.VnfInstanceTaskState.HEALING)

        vnf_instance.instantiated_vnf_info.instance_id =\
            uuidsentinel.instance_id
        self._mock_vnf_manager(fail_method_name='post_heal_vnf')
        driver = vnflcm_driver.VnfLcmDriver()
        self.assertRaises(exceptions.VnfHealFailed,
            driver.heal_vnf, self.context, vnf_instance, heal_vnf_req)
        self.assertEqual(1, mock_save.call_count)
        self.assertEqual(3, self._vnf_manager.invoke.call_count)

        self.assertEqual(fields.VnfInstanceTaskState.ERROR,
            vnf_instance.task_state)
        expected_msg = ('Failed to store updated resources information for '
                        'instance %(instance)s for vnf %(id)s. '
                        'Error: %(error)s')
        mock_log.error.assert_called_with(expected_msg,
            {'instance': vnf_instance.instantiated_vnf_info.instance_id,
             'id': vnf_instance.id,
             'error': 'post_heal_vnf failed'})
