# Copyright (C) 2020 FUJITSU
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


import fixtures
import os
import shutil

from oslo_config import cfg
from oslo_utils import uuidutils

from tacker.common import exceptions
from tacker import context
from tacker.manager import TackerManager
from tacker import objects
from tacker.objects import fields
from tacker.tests.unit.db import base as db_base
from tacker.tests.unit.nfvo.test_nfvo_plugin import FakeVNFMPlugin
from tacker.tests.unit.vnflcm import fakes
from tacker.tests import utils as test_utils
from tacker.tests import uuidsentinel
from tacker.vnflcm import vnflcm_driver
from tacker.vnflcm.vnflcm_driver import VnfLcmDriver
from unittest import mock


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
        if 'mgmt-drivers-custom' in args:
            if self.fail_method_name and \
                    self.fail_method_name == 'mgmt-drivers-custom':
                raise InfraDriverException("mgmt-drivers-custom failed")


class FakeVimClient(mock.Mock):
    pass


class FakeTackerManager(mock.MagicMock):
    pass


class MgmtVnfLcmDriverTest(db_base.SqlTestCase):

    def setUp(self):
        super(MgmtVnfLcmDriverTest, self).setUp()
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
                   'vim_name': 'fake_vim',
                   'vim_auth':
                       {'auth_url': 'http://localhost/identity',
                        'password': 'test_pw', 'username': 'test_user',
                        'project_name': 'test_project'},
                   'vim_type': 'openstack',
                   'tenant': uuidsentinel.tenant_id}
        self.vim_client.get_vim.return_value = vim_obj

    @mock.patch('tacker.vnflcm.utils.get_default_scale_status')
    @mock.patch('tacker.vnflcm.utils._make_final_vnf_dict')
    @mock.patch.object(VnfLcmDriver, '_init_mgmt_driver_hash')
    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfResource, 'create')
    @mock.patch.object(objects.VnfPackageVnfd, 'get_by_id')
    @mock.patch.object(objects.VnfInstance, "save")
    def test_instantiate_vnf(self, mock_vnf_instance_save,
                             mock_vnf_package_vnfd, mock_create,
                             mock_get_service_plugins, mock_init_hash,
                             mock_final_vnf_dict, mock_default_status):
        mock_init_hash.return_value = {
            "vnflcm_noop": "ffea638bfdbde3fb01f191bbe75b031859"
                           "b18d663b127100eb72b19eecd7ed51"
        }
        vnf_package_vnfd = fakes.return_vnf_package_vnfd()
        vnf_package_id = vnf_package_vnfd.package_uuid
        mock_vnf_package_vnfd.return_value = vnf_package_vnfd
        instantiate_vnf_req_dict = fakes.get_dummy_instantiate_vnf_request()
        instantiate_vnf_req_obj = \
            objects.InstantiateVnfRequest.obj_from_primitive(
                instantiate_vnf_req_dict, self.context)
        vnf_instance_obj = fakes.return_vnf_instance()
        mock_default_status.return_value = None

        fake_csar = os.path.join(self.temp_dir, vnf_package_id)
        cfg.CONF.set_override('vnf_package_csar_path', self.temp_dir,
                              group='vnf_package')
        test_utils.copy_csar_files(fake_csar, "refactor_mgmt_driver1")
        self._mock_vnf_manager()
        driver = vnflcm_driver.VnfLcmDriver()
        vnf_dict = {
            "vnfd": {"attributes": {}}, "attributes": {},
            "before_error_point": fields.ErrorPoint.VNF_CONFIG_START}
        driver.instantiate_vnf(self.context, vnf_instance_obj, vnf_dict,
                               instantiate_vnf_req_obj)

        self.assertEqual(1, mock_vnf_instance_save.call_count)
        self.assertEqual(6, self._vnf_manager.invoke.call_count)
        shutil.rmtree(fake_csar)

    @mock.patch('tacker.vnflcm.utils._make_final_vnf_dict')
    @mock.patch.object(VnfLcmDriver, '_init_mgmt_driver_hash')
    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfResource, 'create')
    @mock.patch.object(objects.VnfPackageVnfd, 'get_by_id')
    @mock.patch.object(objects.VnfInstance, "save")
    def test_instantiate_vnf_py_name_false(
            self, mock_vnf_instance_save, mock_vnf_package_vnfd,
            mock_create, mock_get_service_plugins, mock_init_hash,
            mock_final_vnf_dict):
        mock_init_hash.return_value = {
            "vnflcm_noop": "ffea638bfdbde3fb01f191bbe75b031859"
                           "b18d663b127100eb72b19eecd7ed51"
        }
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
        test_utils.copy_csar_files(fake_csar, "refactor_mgmt_driver2")
        self._mock_vnf_manager()
        driver = vnflcm_driver.VnfLcmDriver()
        vnf_dict = {
            "vnfd": {"attributes": {}}, "attributes": {},
            "before_error_point": fields.ErrorPoint.VNF_CONFIG_START}
        self.assertRaises(exceptions.MgmtDriverInconsistent,
                          driver.instantiate_vnf, self.context,
                          vnf_instance_obj, vnf_dict,
                          instantiate_vnf_req_obj)
        shutil.rmtree(fake_csar)

    @mock.patch('tacker.vnflcm.utils._make_final_vnf_dict')
    @mock.patch.object(VnfLcmDriver, '_init_mgmt_driver_hash')
    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfResource, 'create')
    @mock.patch.object(objects.VnfPackageVnfd, 'get_by_id')
    @mock.patch.object(objects.VnfInstance, "save")
    def test_instantiate_vnf_py_hash_false(
            self, mock_vnf_instance_save, mock_vnf_package_vnfd,
            mock_create, mock_get_service_plugins, mock_init_hash,
            mock_final_vnf_dict):
        mock_init_hash.return_value = {
            "vnflcm_noop": "ffea638bfdbde3fb01f191bbe75b031859"
                           "b18d663b127100eb72b19eecd7ed51"
        }
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
        test_utils.copy_csar_files(fake_csar, "refactor_mgmt_driver3")
        self._mock_vnf_manager()
        driver = vnflcm_driver.VnfLcmDriver()
        vnf_dict = {
            "vnfd": {"attributes": {}}, "attributes": {},
            "before_error_point": fields.ErrorPoint.VNF_CONFIG_START}
        self.assertRaises(exceptions.MgmtDriverHashMatchFailure,
                          driver.instantiate_vnf, self.context,
                          vnf_instance_obj, vnf_dict,
                          instantiate_vnf_req_obj)
        shutil.rmtree(fake_csar)
