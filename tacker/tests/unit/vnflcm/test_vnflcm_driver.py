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

import fixtures
import os
import shutil
from unittest import mock
import yaml

from oslo_config import cfg
from oslo_serialization import jsonutils
from oslo_utils import uuidutils

from heatclient.v1 import resources
from tacker.common import driver_manager
from tacker.common import exceptions
from tacker.common import utils
from tacker.conductor.conductorrpc.vnf_lcm_rpc import VNFLcmRPCAPI
from tacker import context
from tacker.db.common_services import common_services_db_plugin
from tacker.manager import TackerManager
from tacker import objects
from tacker.objects import fields
from tacker.objects import vim_connection
from tacker.tests.unit.db import base as db_base
from tacker.tests.unit.nfvo.test_nfvo_plugin import FakeVNFMPlugin
from tacker.tests.unit.vnflcm import fakes
from tacker.tests import utils as test_utils
from tacker.tests import uuidsentinel
from tacker.vnflcm import vnflcm_driver
from tacker.vnfm.infra_drivers.openstack import heat_client
from tacker.vnfm.infra_drivers.openstack import openstack as opn
from tacker.vnfm import plugin
from tacker.vnfm import vim_client


vnf_dict = {
    'id': uuidutils.generate_uuid(),
    'mgmt_ip_address': '{"VDU1": "a.b.c.d"}',
    'vim_id': '6261579e-d6f3-49ad-8bc3-a9cb974778ff',
    'instance_id': 'a737497c-761c-11e5-89c3-9cb6541d805d',
    'vnfd': {
        'attributes': {
            'heat_template': {
                'resources': {
                    'VDU1': {
                        'properties': {
                            'networks': [{'port': {'get_resource': 'CP1'}}]}
                    }
                }
            }
        }
    }
}


OPTS_INFRA_DRIVER = [
    cfg.ListOpt(
        'infra_driver', default=['noop', 'openstack', 'kubernetes'],
        help=_('Hosting vnf drivers tacker plugin will use')),
]
cfg.CONF.register_opts(OPTS_INFRA_DRIVER, 'tacker')


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
        elif 'heal_vnf_standard' in args:
            if self.fail_method_name and \
                    self.fail_method_name == 'heal_vnf_standard':
                raise InfraDriverException("heal_vnf_standard failed")
        elif 'heal_vnf_wait' in args:
            if self.fail_method_name and \
                    self.fail_method_name == 'heal_vnf_wait':
                raise InfraDriverException("heal_vnf_wait failed")
        elif 'post_heal_vnf' in args:
            if self.fail_method_name and \
                    self.fail_method_name == 'post_heal_vnf':
                raise InfraDriverException("post_heal_vnf failed")
        if 'get_rollback_ids' in args:
            return [], [], ""


class FakeVimClient(mock.Mock):
    pass


class FakeTackerManager(mock.MagicMock):
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

    @mock.patch('tacker.vnflcm.utils._make_final_vnf_dict')
    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfResource, 'create')
    @mock.patch.object(objects.VnfPackageVnfd, 'get_by_id')
    @mock.patch.object(objects.VnfInstance, "save")
    def test_instantiate_vnf(self, mock_vnf_instance_save,
                             mock_vnf_package_vnfd, mock_create,
                             mock_get_service_plugins,
                             mock_final_vnf_dict):
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
        vnf_dict = {"vnfd": {"attributes": {}}, "attributes": {}}
        driver.instantiate_vnf(self.context, vnf_instance_obj, vnf_dict,
                               instantiate_vnf_req_obj)

        self.assertEqual(1, mock_vnf_instance_save.call_count)
        self.assertEqual(3, self._vnf_manager.invoke.call_count)
        shutil.rmtree(fake_csar)

    @mock.patch('tacker.vnflcm.utils._make_final_vnf_dict')
    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfResource, 'create')
    @mock.patch.object(objects.VnfPackageVnfd, 'get_by_id')
    @mock.patch.object(objects.VnfInstance, "save")
    def test_instantiate_vnf_with_ext_virtual_links(
            self, mock_vnf_instance_save, mock_vnf_package_vnfd, mock_create,
            mock_get_service_plugins, mock_final_vnf_dict):
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
        vnf_dict = {"vnfd": {"attributes": {}}, "attributes": {}}
        driver.instantiate_vnf(self.context, vnf_instance_obj, vnf_dict,
                               instantiate_vnf_req_obj)

        self.assertEqual(1, mock_vnf_instance_save.call_count)
        self.assertEqual(3, self._vnf_manager.invoke.call_count)
        shutil.rmtree(fake_csar)

    @mock.patch('tacker.vnflcm.utils._make_final_vnf_dict')
    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfResource, 'create')
    @mock.patch.object(objects.VnfPackageVnfd, 'get_by_id')
    @mock.patch.object(objects.VnfInstance, "save")
    def test_instantiate_vnf_vim_connection_info(
            self, mock_vnf_instance_save, mock_vnf_package_vnfd, mock_create,
            mock_get_service_plugins, mock_final_vnf_dict):
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
        vnf_dict = {"vnfd": {"attributes": {}}, "attributes": {}}
        driver.instantiate_vnf(self.context, vnf_instance_obj, vnf_dict,
                               instantiate_vnf_req_obj)

        self.assertEqual(1, mock_vnf_instance_save.call_count)
        self.assertEqual(3, self._vnf_manager.invoke.call_count)
        shutil.rmtree(fake_csar)

    @mock.patch('tacker.vnflcm.utils._make_final_vnf_dict')
    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfResource, 'create')
    @mock.patch.object(objects.VnfPackageVnfd, 'get_by_id')
    @mock.patch.object(objects.VnfInstance, "save")
    def test_instantiate_vnf_infra_fails_to_instantiate(
            self, mock_vnf_instance_save, mock_vnf_package_vnfd, mock_create,
            mock_get_service_plugins, mock_final_vnf_dict):
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
        vnf_dict = {"vnfd": {"attributes": {}}, "attributes": {}}
        error = self.assertRaises(exceptions.VnfInstantiationFailed,
            driver.instantiate_vnf, self.context, vnf_instance_obj, vnf_dict,
            instantiate_vnf_req_obj)
        expected_error = ("Vnf instantiation failed for vnf %s, error: "
                          "instantiate_vnf failed")

        self.assertEqual(expected_error % vnf_instance_obj.id, str(error))
        self.assertEqual("NOT_INSTANTIATED",
            vnf_instance_obj.instantiation_state)
        # 2->1 reason: rollback_vnf_instantiated_resources deleted
        self.assertEqual(1, mock_vnf_instance_save.call_count)
        self.assertEqual(2, self._vnf_manager.invoke.call_count)
        mock_final_vnf_dict.assert_called_once()

        shutil.rmtree(fake_csar)

    @mock.patch('tacker.vnflcm.utils._make_final_vnf_dict')
    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfResource, 'create')
    @mock.patch.object(objects.VnfPackageVnfd, 'get_by_id')
    @mock.patch.object(objects.VnfInstance, "save")
    def test_instantiate_vnf_infra_fails_to_wait_after_instantiate(
            self, mock_vnf_instance_save, mock_vnf_package_vnfd, mock_create,
            mock_get_service_plugins, mock_final_vnf_dict):
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
        level = instantiate_vnf_req_obj.instantiation_level_id
        vnf_instance_obj.instantiated_vnf_info = objects.InstantiatedVnfInfo(
            flavour_id=instantiate_vnf_req_obj.flavour_id,
            instantiation_level_id=level,
            vnf_instance_id=vnf_instance_obj.id,
            ext_cp_info=[])

        fake_csar = os.path.join(self.temp_dir, vnf_package_id)
        cfg.CONF.set_override('vnf_package_csar_path', self.temp_dir,
                              group='vnf_package')
        test_utils.copy_csar_files(fake_csar, "vnflcm4")
        self._mock_vnf_manager(fail_method_name='create_wait')
        driver = vnflcm_driver.VnfLcmDriver()
        vnf_dict = {"vnfd": {"attributes": {}}, "attributes": {}}
        error = self.assertRaises(exceptions.VnfInstantiationWaitFailed,
            driver.instantiate_vnf, self.context, vnf_instance_obj, vnf_dict,
            instantiate_vnf_req_obj)
        expected_error = ("Vnf instantiation wait failed for vnf %s, error: "
                          "create_wait failed")

        self.assertEqual(expected_error % vnf_instance_obj.id, str(error))
        self.assertEqual("NOT_INSTANTIATED",
            vnf_instance_obj.instantiation_state)
        # 3->1 reason: rollback_vnf_instantiated_resources deleted
        self.assertEqual(1, mock_vnf_instance_save.call_count)
        # 5->3 reason: rollback_vnf_instantiated_resources deleted
        self.assertEqual(3, self._vnf_manager.invoke.call_count)

        shutil.rmtree(fake_csar)

    @mock.patch('tacker.vnflcm.utils._make_final_vnf_dict')
    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfResource, 'create')
    @mock.patch.object(objects.VnfPackageVnfd, 'get_by_id')
    @mock.patch.object(objects.VnfInstance, "save")
    def test_instantiate_vnf_with_short_notation(self, mock_vnf_instance_save,
                             mock_vnf_package_vnfd, mock_create,
                             mock_get_service_plugins, mock_final_vnf_dict):
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
        vnf_dict = {"vnfd": {"attributes": {}}, "attributes": {}}
        driver.instantiate_vnf(self.context, vnf_instance_obj, vnf_dict,
                               instantiate_vnf_req_obj)
        self.assertEqual(2, mock_create.call_count)
        self.assertEqual("NOT_INSTANTIATED",
        vnf_instance_obj.instantiation_state)
        mock_final_vnf_dict.assert_called_once()
        shutil.rmtree(fake_csar)

    @mock.patch('tacker.vnflcm.utils._make_final_vnf_dict')
    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfResource, 'create')
    @mock.patch.object(objects.VnfPackageVnfd, 'get_by_id')
    @mock.patch.object(objects.VnfInstance, "save")
    def test_instantiate_vnf_with_single_vnfd(self, mock_vnf_instance_save,
                             mock_vnf_package_vnfd, mock_create,
                             mock_get_service_plugins, mock_final_vnf_dict):
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
            fake_csar, "sample_vnfpkg_no_meta_single_vnfd")
        self._mock_vnf_manager(vnf_resource_count=2)
        driver = vnflcm_driver.VnfLcmDriver()
        vnf_dict = {"vnfd": {"attributes": {}}, "attributes": {}}
        driver.instantiate_vnf(self.context, vnf_instance_obj, vnf_dict,
                               instantiate_vnf_req_obj)
        self.assertEqual(2, mock_create.call_count)
        mock_final_vnf_dict.assert_called_once()
        shutil.rmtree(fake_csar)

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch.object(vim_client.VimClient, "get_vim")
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    @mock.patch.object(objects.VnfResource, "destroy")
    def test_terminate_vnf(self, mock_resource_destroy, mock_resource_list,
            mock_vim, mock_vnf_instance_save, mock_get_service_plugins):
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

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch.object(vim_client.VimClient, "get_vim")
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    @mock.patch.object(objects.VnfResource, "destroy")
    def test_terminate_vnf_graceful_no_timeout(self, mock_resource_destroy,
            mock_resource_list, mock_vim, mock_vnf_instance_save,
            mock_get_service_plugins):
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

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch.object(vim_client.VimClient, "get_vim")
    def test_terminate_vnf_delete_instance_failed(self, mock_vim,
            mock_vnf_instance_save, mock_get_service_plugins):
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

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch.object(vim_client.VimClient, "get_vim")
    def test_terminate_vnf_delete_wait_instance_failed(self, mock_vim,
            mock_vnf_instance_save, mock_get_service_plugins):
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

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch.object(vim_client.VimClient, "get_vim")
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    def test_terminate_vnf_delete_vnf_resource_failed(self, mock_resource_list,
            mock_vim, mock_vnf_instance_save, mock_get_service_plugins):
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

    @mock.patch('tacker.vnflcm.utils._make_final_vnf_dict')
    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch('tacker.vnflcm.utils._make_final_vnf_dict')
    @mock.patch.object(objects.VnfPackageVnfd, 'get_by_id')
    @mock.patch.object(vim_client.VimClient, "get_vim")
    @mock.patch.object(objects.VnfResource, "create")
    @mock.patch.object(objects.VnfResource, "destroy")
    @mock.patch.object(objects.VnfResourceList, "get_by_vnf_instance_id")
    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch('tacker.vnflcm.vnflcm_driver.LOG')
    def test_heal_vnf_without_vnfc_instance(self, mock_log, mock_save,
            mock_vnf_resource_list, mock_resource_destroy,
            mock_resource_create, mock_vim, mock_vnf_package_vnfd,
            mock_make_final_vnf_dict, mock_get_service_plugins,
            mock_final_vnf_dict):
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
        vnf_dict = {"attributes": {}}
        mock_make_final_vnf_dict.return_value = {}
        driver.heal_vnf(self.context, vnf_instance, vnf_dict, heal_vnf_req)
        self.assertEqual(1, mock_save.call_count)
        # vnf resource software images will be deleted during
        # deleting vnf instance.
        self.assertEqual(1, mock_resource_destroy.call_count)
        # Vnf resource software images will be created during
        # instantiation.
        self.assertEqual(1, mock_resource_create.call_count)
        # Invoke will be called 6 times, 3 for deleting the vnf
        # resources  and 3 during instantiation.
        self.assertEqual(6, self._vnf_manager.invoke.call_count)
        expected_msg = ("Request received for healing vnf '%s' "
                       "is completed successfully")
        mock_log.info.assert_called_with(expected_msg,
            vnf_instance.id)
        mock_final_vnf_dict.assert_called_once()
        shutil.rmtree(fake_csar)

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch('tacker.vnflcm.vnflcm_driver.LOG')
    def test_heal_vnf_without_vnfc_instance_infra_delete_fail(self, mock_log,
            mock_save, mock_get_service_plugins):
        # Heal as per SOL003 i.e. without vnfcInstanceId
        heal_vnf_req = objects.HealVnfRequest()

        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED)

        vnf_instance.instantiated_vnf_info.instance_id =\
            uuidsentinel.instance_id
        self._mock_vnf_manager(fail_method_name='delete')
        driver = vnflcm_driver.VnfLcmDriver()
        vnf_dict = {"fake": "fake_dict"}
        self.assertRaises(exceptions.VnfHealFailed,
            driver.heal_vnf, self.context, vnf_instance,
            vnf_dict, heal_vnf_req)
        self.assertEqual(1, mock_save.call_count)
        self.assertEqual(1, self._vnf_manager.invoke.call_count)
        self.assertEqual(fields.VnfInstanceTaskState.ERROR,
            vnf_instance.task_state)
        expected_msg = ('Failed to delete vnf resources for vnf instance %s '
                        'before respawning. The vnf is in inconsistent '
                        'state. Error: delete failed')
        mock_log.error.assert_called_with(expected_msg % vnf_instance.id)

    @mock.patch('tacker.vnflcm.utils._make_final_vnf_dict')
    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch('tacker.vnflcm.utils._make_final_vnf_dict')
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
            mock_vnf_package_vnfd, mock_make_final_vnf_dict,
            mock_get_service_plugins, mock_final_vnf_dict):
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
        vnf_dict = {"fake": "fake_dict"}
        mock_make_final_vnf_dict.return_value = {}
        self.assertRaises(exceptions.VnfHealFailed,
                          driver.heal_vnf, self.context,
                          vnf_instance, vnf_dict, heal_vnf_req)
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
        mock_final_vnf_dict.assert_called_once()

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch('tacker.vnflcm.vnflcm_driver.LOG')
    def test_heal_vnf_with_vnfc_instance(self, mock_log, mock_save,
            mock_get_service_plugins):
        heal_vnf_req = objects.HealVnfRequest(vnfc_instance_id=[
            uuidsentinel.vnfc_instance_id_1])

        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED,
            task_state=fields.VnfInstanceTaskState.HEALING)

        self._mock_vnf_manager()
        driver = vnflcm_driver.VnfLcmDriver()
        driver.heal_vnf(self.context, vnf_instance, mock.ANY, heal_vnf_req)
        self.assertEqual(1, mock_save.call_count)
        self.assertEqual(3, self._vnf_manager.invoke.call_count)

        self.assertEqual(None, vnf_instance.task_state)
        expected_msg = ("Request received for healing vnf '%s' "
                       "is completed successfully")
        mock_log.info.assert_called_with(expected_msg,
            vnf_instance.id)

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch('tacker.vnflcm.vnflcm_driver.LOG')
    def test_heal_vnf_with_infra_heal_vnf_fail(self, mock_log, mock_save,
            mock_get_service_plugins):
        heal_vnf_req = objects.HealVnfRequest(vnfc_instance_id=[
            uuidsentinel.vnfc_instance_id_1])

        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED,
            task_state=fields.VnfInstanceTaskState.HEALING)

        self._mock_vnf_manager(fail_method_name='heal_vnf')
        driver = vnflcm_driver.VnfLcmDriver()
        self.assertRaises(exceptions.VnfHealFailed,
            driver.heal_vnf, self.context, vnf_instance,
            mock.ANY, heal_vnf_req)
        self.assertEqual(1, mock_save.call_count)
        self.assertEqual(1, self._vnf_manager.invoke.call_count)

        self.assertEqual(fields.VnfInstanceTaskState.ERROR,
            vnf_instance.task_state)
        expected_msg = ("Failed to heal vnf %(id)s in infra driver. "
                       "Error: %(error)s")
        mock_log.error.assert_called_with(expected_msg,
            {'id': vnf_instance.id, 'error': 'heal_vnf failed'})

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch('tacker.vnflcm.vnflcm_driver.LOG')
    def test_heal_vnf_with_infra_heal_vnf_wait_fail(self, mock_log,
            mock_save, mock_get_service_plugins):
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
        driver.heal_vnf(self.context, vnf_instance, mock.ANY,
                        heal_vnf_req)
        self.assertEqual(1, mock_save.call_count)
        self.assertEqual(3, self._vnf_manager.invoke.call_count)

        self.assertEqual(None, vnf_instance.task_state)
        expected_msg = ('Failed to update vnf %(id)s resources for '
                        'instance %(instance)s. Error: %(error)s')
        mock_log.error.assert_called_with(expected_msg,
            {'id': vnf_instance.id,
             'instance': vnf_instance.instantiated_vnf_info.instance_id,
             'error': 'heal_vnf_wait failed'})

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch('tacker.vnflcm.vnflcm_driver.LOG')
    def test_heal_vnf_with_infra_post_heal_vnf_fail(self, mock_log,
            mock_save, mock_get_service_plugins):
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
            driver.heal_vnf, self.context, vnf_instance,
            mock.ANY, heal_vnf_req)
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

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(driver_manager.DriverManager, "invoke")
    def test_scale_true(self, mock_invoke, mock_get_service_plugins):
        vnf_info = fakes._get_vnf()
        vnf_info['attributes']['scale_group'] = '{\"scaleGroupDict\": ' + \
            '{ \"SP1\": { \"vdu\": [\"VDU1\"], \"num\": ' + \
            '1, \"maxLevel\": 3, \"initialNum\": 0, ' + \
            '\"initialLevel\": 0, \"default\": 0 }}}'
        scale_vnf_request = fakes.scale_request("SCALE_IN", 1, "True")
        vim_connection_info = vim_connection.VimConnectionInfo(
            vim_type="fake_type")
        scale_name_list = ["fake"]
        grp_id = "fake_id"
        driver = vnflcm_driver.VnfLcmDriver()
        driver.scale(self.context, vnf_info, scale_vnf_request,
        vim_connection_info, scale_name_list, grp_id)

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(yaml, "safe_load")
    @mock.patch.object(driver_manager.DriverManager, "invoke")
    def test_scale_false_in(self, mock_invoke, mock_safe_load,
            mock_get_service_plugins):
        vnf_info = fakes._get_vnf()
        vnf_info['attributes']['scale_group'] = '{\"scaleGroupDict\": ' + \
            '{ \"SP1\": { \"vdu\": [\"VDU1\"], \"num\": ' + \
            '1, \"maxLevel\": 3, \"initialNum\": 0, ' + \
            '\"initialLevel\": 0, \"default\": 0 }}}'
        scale_vnf_request = fakes.scale_request("SCALE_IN", 1, "False")
        vim_connection_info = vim_connection.VimConnectionInfo(
            vim_type="fake_type")
        scale_name_list = ["fake"]
        grp_id = "fake_id"
        with open(vnf_info["attributes"]["heat_template"], "r") as f:
            mock_safe_load.return_value = yaml.safe_load(f)
            print(mock_safe_load.return_value)
        driver = vnflcm_driver.VnfLcmDriver()
        driver.scale(self.context, vnf_info, scale_vnf_request,
        vim_connection_info, scale_name_list, grp_id)

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(yaml, "safe_load")
    @mock.patch.object(driver_manager.DriverManager, "invoke")
    def test_scale_false_out_initial(self, mock_invoke, mock_safe_load,
                               mock_get_service_plugins):
        vnf_info = fakes._get_vnf()
        vnf_info['attributes']['scale_group'] = '{\"scaleGroupDict\": ' + \
            '{ \"SP1\": { \"vdu\": [\"VDU1\"], \"num\": ' + \
            '1, \"maxLevel\": 3, \"initialNum\": 0, ' + \
            '\"initialLevel\": 0, \"default\": 0 }}}'
        scale_vnf_request = fakes.scale_request("SCALE_OUT", 1, "False")
        vim_connection_info = vim_connection.VimConnectionInfo(
            vim_type="fake_type")
        scale_name_list = ["fake"]
        grp_id = "fake_id"
        with open(vnf_info["attributes"]["heat_template"], "r") as f:
            mock_safe_load.return_value = yaml.safe_load(f)
            print(mock_safe_load.return_value)
        driver = vnflcm_driver.VnfLcmDriver()
        driver.scale(self.context, vnf_info, scale_vnf_request,
        vim_connection_info, scale_name_list, grp_id)

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(yaml, "safe_load")
    @mock.patch.object(driver_manager.DriverManager, "invoke")
    def test_scale_false_out_level_up(self, mock_invoke, mock_safe_load,
                               mock_get_service_plugins):
        vnf_info = fakes._get_vnf()
        vnf_info['attributes']['scale_group'] = '{\"scaleGroupDict\": ' + \
            '{ \"SP1\": { \"vdu\": [\"VDU1\"], \"num\": ' + \
            '1, \"maxLevel\": 3, \"initialNum\": 0, ' + \
            '\"initialLevel\": 0, \"default\": 1 }}}'
        scale_vnf_request = fakes.scale_request("SCALE_OUT", 1, "False")
        vim_connection_info = vim_connection.VimConnectionInfo(
            vim_type="fake_type")
        scale_name_list = ["fake"]
        grp_id = "fake_id"
        with open(vnf_info["attributes"]["heat_template"], "r") as f:
            mock_safe_load.return_value = yaml.safe_load(f)
            print(mock_safe_load.return_value)
        driver = vnflcm_driver.VnfLcmDriver()
        driver.scale(self.context, vnf_info, scale_vnf_request,
        vim_connection_info, scale_name_list, grp_id)

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfLcmOpOcc, "save")
    @mock.patch.object(VNFLcmRPCAPI, "send_notification")
    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch.object(vnflcm_driver.VnfLcmDriver, "_update_vnf_rollback_pre")
    @mock.patch.object(vnflcm_driver.VnfLcmDriver, "_update_vnf_rollback")
    def test_rollback_vnf_7(
            self,
            mock_update,
            mock_up,
            mock_insta_save,
            mock_notification,
            mock_lcm_save,
            mock_get_service_plugins):
        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED)

        vnf_instance.instantiated_vnf_info.instance_id =\
            uuidsentinel.instance_id
        vnf_lcm_op_occs = fakes.vnflcm_rollback_insta()
        vnf_info = fakes.vnf_dict()
        vnf_info['vnf_lcm_op_occ'] = vnf_lcm_op_occs
        operation_params = jsonutils.loads(vnf_lcm_op_occs.operation_params)

        self._mock_vnf_manager()
        driver = vnflcm_driver.VnfLcmDriver()
        driver.rollback_vnf(
            self.context,
            vnf_info,
            vnf_instance,
            operation_params)
        self.assertEqual(1, mock_lcm_save.call_count)

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfLcmOpOcc, "save")
    @mock.patch.object(VNFLcmRPCAPI, "send_notification")
    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch.object(vnflcm_driver.VnfLcmDriver, "_update_vnf_rollback_pre")
    @mock.patch.object(vnflcm_driver.VnfLcmDriver, "_update_vnf_rollback")
    def test_rollback_vnf_6(
            self,
            mock_update,
            mock_up,
            mock_insta_save,
            mock_notification,
            mock_lcm_save,
            mock_get_service_plugins):
        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED)

        vnf_instance.instantiated_vnf_info.instance_id =\
            uuidsentinel.instance_id
        vnf_lcm_op_occs = fakes.vnflcm_rollback_insta(error_point=6)
        vnf_info = fakes.vnf_dict()
        vnf_info['vnf_lcm_op_occ'] = vnf_lcm_op_occs
        operation_params = jsonutils.loads(vnf_lcm_op_occs.operation_params)

        self._mock_vnf_manager()
        driver = vnflcm_driver.VnfLcmDriver()
        driver.rollback_vnf(
            self.context,
            vnf_info,
            vnf_instance,
            operation_params)
        self.assertEqual(1, mock_lcm_save.call_count)

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfLcmOpOcc, "save")
    @mock.patch.object(VNFLcmRPCAPI, "send_notification")
    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch.object(vnflcm_driver.VnfLcmDriver, "_update_vnf_rollback_pre")
    @mock.patch.object(vnflcm_driver.VnfLcmDriver, "_update_vnf_rollback")
    def test_rollback_vnf_5(
            self,
            mock_update,
            mock_up,
            mock_insta_save,
            mock_notification,
            mock_lcm_save,
            mock_get_service_plugins):
        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED)

        vnf_instance.instantiated_vnf_info.instance_id =\
            uuidsentinel.instance_id
        vnf_lcm_op_occs = fakes.vnflcm_rollback_insta(error_point=5)
        vnf_info = fakes.vnf_dict()
        vnf_info['vnf_lcm_op_occ'] = vnf_lcm_op_occs
        operation_params = jsonutils.loads(vnf_lcm_op_occs.operation_params)

        self._mock_vnf_manager()
        driver = vnflcm_driver.VnfLcmDriver()
        driver.rollback_vnf(
            self.context,
            vnf_info,
            vnf_instance,
            operation_params)
        self.assertEqual(1, mock_lcm_save.call_count)

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfLcmOpOcc, "save")
    @mock.patch.object(VNFLcmRPCAPI, "send_notification")
    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch.object(vnflcm_driver.VnfLcmDriver, "_update_vnf_rollback_pre")
    @mock.patch.object(vnflcm_driver.VnfLcmDriver, "_update_vnf_rollback")
    def test_rollback_vnf_4(
            self,
            mock_update,
            mock_up,
            mock_insta_save,
            mock_notification,
            mock_lcm_save,
            mock_get_service_plugins):
        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED)

        vnf_instance.instantiated_vnf_info.instance_id =\
            uuidsentinel.instance_id
        vnf_lcm_op_occs = fakes.vnflcm_rollback_insta(error_point=4)
        vnf_info = fakes.vnf_dict()
        vnf_info['vnf_lcm_op_occ'] = vnf_lcm_op_occs
        operation_params = jsonutils.loads(vnf_lcm_op_occs.operation_params)

        self._mock_vnf_manager()
        driver = vnflcm_driver.VnfLcmDriver()
        driver.rollback_vnf(
            self.context,
            vnf_info,
            vnf_instance,
            operation_params)
        self.assertEqual(1, mock_lcm_save.call_count)

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfLcmOpOcc, "save")
    @mock.patch.object(VNFLcmRPCAPI, "send_notification")
    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch.object(vnflcm_driver.VnfLcmDriver, "_update_vnf_rollback_pre")
    @mock.patch.object(vnflcm_driver.VnfLcmDriver, "_update_vnf_rollback")
    def test_rollback_vnf_3(
            self,
            mock_update,
            mock_up,
            mock_insta_save,
            mock_notification,
            mock_lcm_save,
            mock_get_service_plugins):
        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED)

        vnf_instance.instantiated_vnf_info.instance_id =\
            uuidsentinel.instance_id
        vnf_lcm_op_occs = fakes.vnflcm_rollback_insta(error_point=3)
        vnf_info = fakes.vnf_dict()
        vnf_info['vnf_lcm_op_occ'] = vnf_lcm_op_occs
        operation_params = jsonutils.loads(vnf_lcm_op_occs.operation_params)

        self._mock_vnf_manager()
        driver = vnflcm_driver.VnfLcmDriver()
        driver.rollback_vnf(
            self.context,
            vnf_info,
            vnf_instance,
            operation_params)
        self.assertEqual(1, mock_lcm_save.call_count)

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfLcmOpOcc, "save")
    @mock.patch.object(VNFLcmRPCAPI, "send_notification")
    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch.object(vnflcm_driver.VnfLcmDriver, "_update_vnf_rollback_pre")
    @mock.patch.object(vnflcm_driver.VnfLcmDriver, "_update_vnf_rollback")
    def test_rollback_vnf_scale(
            self,
            mock_update,
            mock_up,
            mock_insta_save,
            mock_notification,
            mock_lcm_save,
            mock_get_service_plugins):
        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED)

        vnf_instance.instantiated_vnf_info.instance_id =\
            uuidsentinel.instance_id
        vnf_instance.instantiated_vnf_info.scale_status = []
        vnf_instance.instantiated_vnf_info.scale_status.append(
            objects.ScaleInfo(aspect_id='SP1', scale_level=0))
        vnf_lcm_op_occs = fakes.vnflcm_rollback()
        vnf_info = fakes.vnf_dict()
        vnf_info['vnf_lcm_op_occ'] = vnf_lcm_op_occs
        operation_params = jsonutils.loads(vnf_lcm_op_occs.operation_params)

        self._mock_vnf_manager()
        driver = vnflcm_driver.VnfLcmDriver()

        driver.rollback_vnf(
            self.context,
            vnf_info,
            vnf_instance,
            operation_params)
        self.assertEqual(1, mock_lcm_save.call_count)

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfLcmOpOcc, "save")
    @mock.patch.object(VNFLcmRPCAPI, "send_notification")
    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch.object(vnflcm_driver.VnfLcmDriver, "_update_vnf_rollback_pre")
    @mock.patch.object(vnflcm_driver.VnfLcmDriver, "_update_vnf_rollback")
    def test_rollback_vnf_scale_6(
            self,
            mock_update,
            mock_up,
            mock_insta_save,
            mock_notification,
            mock_lcm_save,
            mock_get_service_plugins):
        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED)

        vnf_instance.instantiated_vnf_info.instance_id =\
            uuidsentinel.instance_id
        vnf_instance.instantiated_vnf_info.scale_status = []
        vnf_instance.instantiated_vnf_info.scale_status.append(
            objects.ScaleInfo(aspect_id='SP1', scale_level=0))
        vnf_lcm_op_occs = fakes.vnflcm_rollback(error_point=6)
        vnf_info = fakes.vnf_dict()
        vnf_info['vnf_lcm_op_occ'] = vnf_lcm_op_occs
        operation_params = jsonutils.loads(vnf_lcm_op_occs.operation_params)

        self._mock_vnf_manager()
        driver = vnflcm_driver.VnfLcmDriver()

        driver.rollback_vnf(
            self.context,
            vnf_info,
            vnf_instance,
            operation_params)
        self.assertEqual(1, mock_lcm_save.call_count)

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfLcmOpOcc, "save")
    @mock.patch.object(VNFLcmRPCAPI, "send_notification")
    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch.object(vnflcm_driver.VnfLcmDriver, "_update_vnf_rollback_pre")
    @mock.patch.object(vnflcm_driver.VnfLcmDriver, "_update_vnf_rollback")
    def test_rollback_vnf_scale_5(
            self,
            mock_update,
            mock_up,
            mock_insta_save,
            mock_notification,
            mock_lcm_save,
            mock_get_service_plugins):
        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED)

        vnf_instance.instantiated_vnf_info.instance_id =\
            uuidsentinel.instance_id
        vnf_instance.instantiated_vnf_info.scale_status = []
        vnf_instance.instantiated_vnf_info.scale_status.append(
            objects.ScaleInfo(aspect_id='SP1', scale_level=0))
        vnf_lcm_op_occs = fakes.vnflcm_rollback(error_point=5)
        vnf_info = fakes.vnf_dict()
        vnf_info['vnf_lcm_op_occ'] = vnf_lcm_op_occs
        operation_params = jsonutils.loads(vnf_lcm_op_occs.operation_params)

        self._mock_vnf_manager()
        driver = vnflcm_driver.VnfLcmDriver()

        driver.rollback_vnf(
            self.context,
            vnf_info,
            vnf_instance,
            operation_params)
        self.assertEqual(1, mock_lcm_save.call_count)

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfLcmOpOcc, "save")
    @mock.patch.object(VNFLcmRPCAPI, "send_notification")
    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch.object(vnflcm_driver.VnfLcmDriver, "_update_vnf_rollback_pre")
    @mock.patch.object(vnflcm_driver.VnfLcmDriver, "_update_vnf_rollback")
    def test_rollback_vnf_scale_4(
            self,
            mock_update,
            mock_up,
            mock_insta_save,
            mock_notification,
            mock_lcm_save,
            mock_get_service_plugins):
        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED)

        vnf_instance.instantiated_vnf_info.instance_id =\
            uuidsentinel.instance_id
        vnf_instance.instantiated_vnf_info.scale_status = []
        vnf_instance.instantiated_vnf_info.scale_status.append(
            objects.ScaleInfo(aspect_id='SP1', scale_level=0))
        vnf_lcm_op_occs = fakes.vnflcm_rollback(error_point=4)
        vnf_info = fakes.vnf_dict()
        vnf_info['vnf_lcm_op_occ'] = vnf_lcm_op_occs
        operation_params = jsonutils.loads(vnf_lcm_op_occs.operation_params)

        self._mock_vnf_manager()
        driver = vnflcm_driver.VnfLcmDriver()

        driver.rollback_vnf(
            self.context,
            vnf_info,
            vnf_instance,
            operation_params)
        self.assertEqual(1, mock_lcm_save.call_count)

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfLcmOpOcc, "save")
    @mock.patch.object(VNFLcmRPCAPI, "send_notification")
    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch.object(vnflcm_driver.VnfLcmDriver, "_update_vnf_rollback_pre")
    @mock.patch.object(vnflcm_driver.VnfLcmDriver, "_update_vnf_rollback")
    def test_rollback_vnf_scale_3(
            self,
            mock_update,
            mock_up,
            mock_insta_save,
            mock_notification,
            mock_lcm_save,
            mock_get_service_plugins):
        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED)

        vnf_instance.instantiated_vnf_info.instance_id =\
            uuidsentinel.instance_id
        vnf_instance.instantiated_vnf_info.scale_status = []
        vnf_instance.instantiated_vnf_info.scale_status.append(
            objects.ScaleInfo(aspect_id='SP1', scale_level=0))
        vnf_lcm_op_occs = fakes.vnflcm_rollback(error_point=3)
        vnf_info = fakes.vnf_dict()
        vnf_info['vnf_lcm_op_occ'] = vnf_lcm_op_occs
        operation_params = jsonutils.loads(vnf_lcm_op_occs.operation_params)

        self._mock_vnf_manager()
        driver = vnflcm_driver.VnfLcmDriver()

        driver.rollback_vnf(
            self.context,
            vnf_info,
            vnf_instance,
            operation_params)
        self.assertEqual(1, mock_lcm_save.call_count)

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfLcmOpOcc, "save")
    def test_rollback_vnf_save_error(self, mock_lcm_save,
            mock_get_service_plugins):
        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED)

        vnf_instance.instantiated_vnf_info.instance_id =\
            uuidsentinel.instance_id
        vnf_lcm_op_occs = fakes.vnflcm_rollback_insta()
        vnf_info = fakes.vnf_dict()
        vnf_info['vnf_lcm_op_occ'] = vnf_lcm_op_occs
        operation_params = jsonutils.loads(vnf_lcm_op_occs.operation_params)
        mock_lcm_save.side_effect = exceptions.DBAccessError()

        self._mock_vnf_manager()
        driver = vnflcm_driver.VnfLcmDriver()
        self.assertRaises(
            exceptions.DBAccessError,
            driver.rollback_vnf,
            self.context,
            vnf_info,
            vnf_instance,
            operation_params)

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfLcmOpOcc, "save")
    @mock.patch.object(common_services_db_plugin.CommonServicesPluginDb,
                       "create_event")
    @mock.patch.object(heat_client.HeatClient, "__init__")
    @mock.patch.object(heat_client.HeatClient, "resource_get")
    @mock.patch.object(heat_client.HeatClient, "resource_get_list")
    @mock.patch.object(vnflcm_driver.VnfLcmDriver, "_update_vnf_rollback_pre")
    @mock.patch.object(vnflcm_driver.VnfLcmDriver, "_update_vnf_rollback")
    def test_rollback_vnf_scale_resource_error(
            self,
            mock_update,
            mock_up,
            mock_resource_get_list,
            mock_resource_get,
            mock_init,
            mock_event,
            mock_lcm_save,
            mock_get_service_plugins):
        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED)

        vnf_instance.instantiated_vnf_info.instance_id =\
            uuidsentinel.instance_id
        vnf_instance.instantiated_vnf_info.scale_status = []
        vnf_instance.instantiated_vnf_info.scale_status.append(
            objects.ScaleInfo(aspect_id='SP1', scale_level=0))
        vnf_lcm_op_occs = fakes.vnflcm_rollback()
        vnf_info = fakes.vnf_dict()
        vnf_info['vnf_lcm_op_occ'] = vnf_lcm_op_occs
        vnf_info['scale_level'] = 0
        operation_params = jsonutils.loads(vnf_lcm_op_occs.operation_params)
        mock_init.return_value = None
        mock_resource_get.side_effect = exceptions.DBAccessError()

        driver = vnflcm_driver.VnfLcmDriver()
        self.assertRaises(
            exceptions.DBAccessError,
            driver.rollback_vnf,
            self.context,
            vnf_info,
            vnf_instance,
            operation_params)
        self.assertEqual(2, mock_lcm_save.call_count)

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfLcmOpOcc, "save")
    @mock.patch.object(common_services_db_plugin.CommonServicesPluginDb,
                       "create_event")
    @mock.patch.object(heat_client.HeatClient, "__init__")
    @mock.patch.object(heat_client.HeatClient, "resource_get")
    @mock.patch.object(heat_client.HeatClient, "resource_get_list")
    @mock.patch.object(vnflcm_driver.VnfLcmDriver, "_update_vnf_rollback_pre")
    @mock.patch.object(vnflcm_driver.VnfLcmDriver, "_update_vnf_rollback")
    def test_rollback_vnf_scale_resource_list_error(
            self,
            mock_update,
            mock_up,
            mock_resource_list,
            mock_resource_get,
            mock_init,
            mock_event,
            mock_lcm_save,
            mock_get_service_plugins):
        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED)

        vnf_instance.instantiated_vnf_info.instance_id =\
            uuidsentinel.instance_id
        vnf_instance.instantiated_vnf_info.scale_status = []
        vnf_instance.instantiated_vnf_info.scale_status.append(
            objects.ScaleInfo(aspect_id='SP1', scale_level=0))
        vnf_lcm_op_occs = fakes.vnflcm_rollback()
        vnf_info = fakes.vnf_dict()
        vnf_info['vnf_lcm_op_occ'] = vnf_lcm_op_occs
        operation_params = jsonutils.loads(vnf_lcm_op_occs.operation_params)
        mock_init.return_value = None
        resource1 = resources.Resource(None, {
            'resource_name': 'SP1_group',
            'creation_time': '2020-01-01T00:00:00',
            'resource_status': 'CREATE_COMPLETE',
            'physical_resource_id': '30435eb8-1472-4cbc-abbe-00b395165ce7',
            'id': '1111'
        })
        mock_resource_get.return_value = resource1
        mock_resource_list.side_effect = exceptions.DBAccessError()

        driver = vnflcm_driver.VnfLcmDriver()
        self.assertRaises(
            exceptions.DBAccessError,
            driver.rollback_vnf,
            self.context,
            vnf_info,
            vnf_instance,
            operation_params)
        self.assertEqual(2, mock_lcm_save.call_count)
        self.assertEqual(2, mock_resource_list.call_count)

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfLcmOpOcc, "save")
    @mock.patch.object(common_services_db_plugin.CommonServicesPluginDb,
                       "create_event")
    @mock.patch.object(heat_client.HeatClient, "__init__")
    @mock.patch.object(plugin.VNFMMgmtMixin, "mgmt_call")
    @mock.patch.object(opn.OpenStack, "delete")
    @mock.patch.object(vnflcm_driver.VnfLcmDriver, "_update_vnf_rollback_pre")
    @mock.patch.object(vnflcm_driver.VnfLcmDriver, "_update_vnf_rollback")
    def test_rollback_vnf_delete_error(
            self,
            mock_update,
            mock_up,
            mock_delete,
            mock_mgmt,
            mock_init,
            mock_event,
            mock_lcm_save,
            mock_get_service_plugins):
        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED)

        vnf_instance.instantiated_vnf_info.instance_id =\
            uuidsentinel.instance_id
        vnf_lcm_op_occs = fakes.vnflcm_rollback_insta()
        vnf_info = fakes.vnf_dict()
        vnf_info['vnf_lcm_op_occ'] = vnf_lcm_op_occs
        operation_params = jsonutils.loads(vnf_lcm_op_occs.operation_params)
        mock_init.return_value = None
        mock_delete.side_effect = exceptions.DBAccessError()

        driver = vnflcm_driver.VnfLcmDriver()
        self.assertRaises(
            exceptions.DBAccessError,
            driver.rollback_vnf,
            self.context,
            vnf_info,
            vnf_instance,
            operation_params)
        self.assertEqual(2, mock_lcm_save.call_count)
        self.assertEqual(1, mock_delete.call_count)

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfLcmOpOcc, "save")
    @mock.patch.object(common_services_db_plugin.CommonServicesPluginDb,
                       "create_event")
    @mock.patch.object(heat_client.HeatClient, "__init__")
    @mock.patch.object(plugin.VNFMMgmtMixin, "mgmt_call")
    @mock.patch.object(opn.OpenStack, "delete")
    @mock.patch.object(opn.OpenStack, "delete_wait")
    @mock.patch.object(vnflcm_driver.VnfLcmDriver, "_update_vnf_rollback_pre")
    @mock.patch.object(vnflcm_driver.VnfLcmDriver, "_update_vnf_rollback")
    def test_rollback_vnf_delete_wait_error(
            self,
            mock_update,
            mock_up,
            mock_delete_wait,
            mock_delete,
            mock_mgmt,
            mock_init,
            mock_event,
            mock_lcm_save,
            mock_get_service_plugins):
        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED)

        vnf_instance.instantiated_vnf_info.instance_id =\
            uuidsentinel.instance_id
        vnf_lcm_op_occs = fakes.vnflcm_rollback_insta()
        vnf_info = fakes.vnf_dict()
        vnf_info['vnf_lcm_op_occ'] = vnf_lcm_op_occs
        operation_params = jsonutils.loads(vnf_lcm_op_occs.operation_params)
        mock_init.return_value = None
        mock_delete_wait.side_effect = exceptions.DBAccessError()

        driver = vnflcm_driver.VnfLcmDriver()
        self.assertRaises(
            exceptions.DBAccessError,
            driver.rollback_vnf,
            self.context,
            vnf_info,
            vnf_instance,
            operation_params)
        self.assertEqual(2, mock_lcm_save.call_count)
        self.assertEqual(1, mock_delete.call_count)
        self.assertEqual(1, mock_delete_wait.call_count)

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfLcmOpOcc, "save")
    @mock.patch.object(common_services_db_plugin.CommonServicesPluginDb,
                       "create_event")
    @mock.patch.object(heat_client.HeatClient, "__init__")
    @mock.patch.object(heat_client.HeatClient, "resource_get")
    @mock.patch.object(heat_client.HeatClient, "resource_get_list")
    @mock.patch.object(opn.OpenStack, "get_rollback_ids")
    @mock.patch.object(vnflcm_driver.VnfLcmDriver, "_rollback_mgmt_call")
    @mock.patch.object(opn.OpenStack, "scale_in_reverse")
    @mock.patch.object(vnflcm_driver.VnfLcmDriver, "_update_vnf_rollback_pre")
    @mock.patch.object(vnflcm_driver.VnfLcmDriver, "_update_vnf_rollback")
    def test_rollback_vnf_scale_update_error(
            self,
            mock_update,
            mock_up,
            mock_scale,
            mock_mgmt,
            mock_resource_get,
            mock_resource_get_list,
            mock_resource,
            mock_init,
            mock_event,
            mock_lcm_save,
            mock_get_service_plugins):
        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED)

        vnf_instance.instantiated_vnf_info.instance_id =\
            uuidsentinel.instance_id
        vnf_instance.instantiated_vnf_info.scale_status = []
        vnf_instance.instantiated_vnf_info.scale_status.append(
            objects.ScaleInfo(aspect_id='SP1', scale_level=0))
        vnf_lcm_op_occs = fakes.vnflcm_rollback()
        vnf_info = fakes.vnf_dict()
        vnf_info['vnf_lcm_op_occ'] = vnf_lcm_op_occs
        vnf_info['scale_level'] = 0
        operation_params = jsonutils.loads(vnf_lcm_op_occs.operation_params)
        mock_init.return_value = None
        mock_resource_get.return_value = (
            ['342bd357-7c4a-438c-9b5b-1f56702137d8'],
            ['VDU1'],
            '49c1cf71-abd4-4fb1-afb3-5f63f3b04246')

        mock_scale.side_effect = exceptions.DBAccessError()

        driver = vnflcm_driver.VnfLcmDriver()
        self.assertRaises(
            exceptions.DBAccessError,
            driver.rollback_vnf,
            self.context,
            vnf_info,
            vnf_instance,
            operation_params)
        self.assertEqual(2, mock_lcm_save.call_count)
        self.assertEqual(1, mock_scale.call_count)

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfLcmOpOcc, "save")
    @mock.patch.object(common_services_db_plugin.CommonServicesPluginDb,
                       "create_event")
    @mock.patch.object(heat_client.HeatClient, "__init__")
    @mock.patch.object(heat_client.HeatClient, "resource_get")
    @mock.patch.object(heat_client.HeatClient, "resource_get_list")
    @mock.patch.object(opn.OpenStack, "get_rollback_ids")
    @mock.patch.object(vnflcm_driver.VnfLcmDriver, "_rollback_mgmt_call")
    @mock.patch.object(opn.OpenStack, "scale_in_reverse")
    @mock.patch.object(opn.OpenStack, "scale_update_wait")
    @mock.patch.object(vnflcm_driver.VnfLcmDriver, "_update_vnf_rollback_pre")
    @mock.patch.object(vnflcm_driver.VnfLcmDriver, "_update_vnf_rollback")
    def test_rollback_vnf_scale_update_wait_error(
            self,
            mock_update,
            mock_up,
            mock_wait,
            mock_scale,
            mock_mgmt,
            mock_resource_get,
            mock_resource_get_list,
            mock_resource,
            mock_init,
            mock_event,
            mock_lcm_save,
            mock_get_service_plugins):
        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED)

        vnf_instance.instantiated_vnf_info.instance_id =\
            uuidsentinel.instance_id
        vnf_instance.instantiated_vnf_info.scale_status = []
        vnf_instance.instantiated_vnf_info.scale_status.append(
            objects.ScaleInfo(aspect_id='SP1', scale_level=0))
        vnf_lcm_op_occs = fakes.vnflcm_rollback()
        vnf_info = fakes.vnf_dict()
        vnf_info['vnf_lcm_op_occ'] = vnf_lcm_op_occs
        vnf_info['scale_level'] = 0
        operation_params = jsonutils.loads(vnf_lcm_op_occs.operation_params)
        mock_init.return_value = None
        mock_resource_get.return_value = (
            ['342bd357-7c4a-438c-9b5b-1f56702137d8'],
            ['VDU1'],
            '49c1cf71-abd4-4fb1-afb3-5f63f3b04246')

        mock_wait.side_effect = exceptions.DBAccessError()

        driver = vnflcm_driver.VnfLcmDriver()
        self.assertRaises(
            exceptions.DBAccessError,
            driver.rollback_vnf,
            self.context,
            vnf_info,
            vnf_instance,
            operation_params)
        self.assertEqual(2, mock_lcm_save.call_count)
        self.assertEqual(1, mock_scale.call_count)
        self.assertEqual(1, mock_wait.call_count)

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfLcmOpOcc, "save")
    @mock.patch.object(common_services_db_plugin.CommonServicesPluginDb,
                       "create_event")
    @mock.patch.object(heat_client.HeatClient, "__init__")
    @mock.patch.object(opn.OpenStack, "get_rollback_ids")
    @mock.patch.object(vnflcm_driver.VnfLcmDriver, "_rollback_mgmt_call")
    @mock.patch.object(opn.OpenStack, "scale_in_reverse")
    @mock.patch.object(opn.OpenStack, "scale_update_wait")
    @mock.patch.object(opn.OpenStack, "scale_resource_update")
    @mock.patch.object(vnflcm_driver.VnfLcmDriver, "_update_vnf_rollback_pre")
    @mock.patch.object(vnflcm_driver.VnfLcmDriver, "_update_vnf_rollback")
    def test_rollback_vnf_scale_resource_get_error(
            self,
            mock_update,
            mock_up,
            mock_scale_resource,
            mock_wait,
            mock_scale,
            mock_mgmt,
            mock_resource_get,
            mock_init,
            mock_event,
            mock_lcm_save,
            mock_get_service_plugins):
        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED)

        vnf_instance.instantiated_vnf_info.instance_id =\
            uuidsentinel.instance_id
        vnf_instance.instantiated_vnf_info.scale_status = []
        vnf_instance.instantiated_vnf_info.scale_status.append(
            objects.ScaleInfo(aspect_id='SP1', scale_level=0))
        vnf_lcm_op_occs = fakes.vnflcm_rollback()
        vnf_info = fakes.vnf_dict()
        vnf_info['vnf_lcm_op_occ'] = vnf_lcm_op_occs
        vnf_info['scale_level'] = 0
        operation_params = jsonutils.loads(vnf_lcm_op_occs.operation_params)
        mock_init.return_value = None
        mock_resource_get.return_value = (
            ['342bd357-7c4a-438c-9b5b-1f56702137d8'],
            ['VDU1'],
            '49c1cf71-abd4-4fb1-afb3-5f63f3b04246')
        resource1 = resources.Resource(None, {
            'resource_name': 'SP1_group',
            'creation_time': '2020-01-01T00:00:00',
            'resource_status': 'UPDATE_COMPLETE',
            'physical_resource_id': '30435eb8-1472-4cbc-abbe-00b395165ce7',
            'id': '1111'
        })

        mock_wait.return_value = resource1
        mock_scale_resource.side_effect = exceptions.DBAccessError()

        driver = vnflcm_driver.VnfLcmDriver()
        self.assertRaises(
            exceptions.DBAccessError,
            driver.rollback_vnf,
            self.context,
            vnf_info,
            vnf_instance,
            operation_params)
        self.assertEqual(2, mock_lcm_save.call_count)
        self.assertEqual(1, mock_scale.call_count)
        self.assertEqual(1, mock_wait.call_count)
        self.assertEqual(2, mock_scale_resource.call_count)
