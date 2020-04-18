# Copyright (C) 2020 NTT DATA
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

from tacker.common import exceptions
from tacker import context
from tacker.db import api as sqlalchemy_api
from tacker import objects
from tacker.tests.unit.db.base import SqlTestCase
from tacker.tests.unit.objects import fakes
from tacker.tests import uuidsentinel

get_engine = sqlalchemy_api.get_engine


class TestVnfInstance(SqlTestCase):

    def setUp(self):
        super(TestVnfInstance, self).setUp()
        self.context = context.get_admin_context()
        self.vnf_package = self._create_and_upload_vnf_package()
        self.engine = get_engine()
        self.conn = self.engine.connect()

    def _create_and_upload_vnf_package(self):
        vnf_package = objects.VnfPackage(context=self.context,
                                         **fakes.vnf_package_data)
        vnf_package.create()

        vnf_pack_vnfd = fakes.get_vnf_package_vnfd_data(
            vnf_package.id, uuidsentinel.vnfd_id)

        vnf_pack_vnfd_obj = objects.VnfPackageVnfd(
            context=self.context, **vnf_pack_vnfd)
        vnf_pack_vnfd_obj.create()

        vnf_package.vnf_package = "ONBOARDED"
        vnf_package.save()

        return vnf_pack_vnfd_obj

    def test_create(self):
        vnf_instance_data = fakes.get_vnf_instance_data(
            self.vnf_package.vnfd_id)
        vnf_instance = objects.VnfInstance(context=self.context,
                                           **vnf_instance_data)
        vnf_instance.create()
        self.assertTrue(vnf_instance.id)
        self.assertEqual('NOT_INSTANTIATED', vnf_instance.instantiation_state)
        self.assertEqual(self.vnf_package.vnfd_id,
                         vnf_instance.vnfd_id)
        self.assertEqual('test vnf provider', vnf_instance.vnf_provider)
        self.assertEqual('Sample VNF', vnf_instance.vnf_product_name)
        self.assertEqual('1.0', vnf_instance.vnf_software_version)
        self.assertEqual('1.0', vnf_instance.vnfd_version)
        self.assertEqual(vnf_instance_data.get('tenant_id'),
                         vnf_instance.tenant_id)

    def test_create_failure_with_id(self):
        vnf_instance_data = fakes.get_vnf_instance_data_with_id(
            self.vnf_package.vnfd_id)
        vnf_instance = objects.VnfInstance(context=self.context,
                                           **vnf_instance_data)
        self.assertRaises(exceptions.ObjectActionError, vnf_instance.create)

    def test_get_by_id(self):
        vnf_instance_data = fakes.get_vnf_instance_data(
            self.vnf_package.vnfd_id)
        vnf_instance = objects.VnfInstance(context=self.context,
                                           **vnf_instance_data)
        vnf_instance.create()
        vnf_instance_by_id = objects.VnfInstance.get_by_id(
            self.context, vnf_instance.id)
        self.compare_obj(vnf_instance, vnf_instance_by_id,
                         allow_missing=['instantiated_vnf_info',
                                        'vim_connection_info'])

    def test_get_by_id_non_existing_vnf_instance(self):
        self.assertRaises(
            exceptions.VnfInstanceNotFound,
            objects.VnfInstance.get_by_id, self.context,
            uuidsentinel.invalid_uuid)

    @mock.patch('tacker.objects.vnf_instance._vnf_instance_update')
    def test_save(self, mock_update_vnf):
        vnf_instance_data = fakes.get_vnf_instance_data(
            self.vnf_package.vnfd_id)
        vnf_instance = objects.VnfInstance(context=self.context,
                                           **vnf_instance_data)
        vnf_instance.create()
        mock_update_vnf.return_value = \
            fakes.vnf_instance_model_object(vnf_instance)
        vnf_instance.vnf_instance_name = 'fake-name'
        vnf_instance.save()
        mock_update_vnf.assert_called_with(
            self.context, vnf_instance.id, {
                'vnf_instance_name': 'fake-name',
                'vim_connection_info': []},
            columns_to_join=['instantiated_vnf_info'])

    def test_save_error(self):
        vnf_instance_data = fakes.get_vnf_instance_data(
            self.vnf_package.vnfd_id)
        vnf_instance = objects.VnfInstance(context=self.context,
                                           **vnf_instance_data)
        vnf_instance.id = uuidsentinel.id
        self.assertRaises(exceptions.VnfInstanceNotFound, vnf_instance.save)

    def test_get_all(self):
        vnf_instance_data = fakes.get_vnf_instance_data(
            self.vnf_package.vnfd_id)
        vnf_instance = objects.VnfInstance(context=self.context,
                                           **vnf_instance_data)
        vnf_instance.create()
        result = objects.VnfInstanceList.get_all(self.context,
                                                 expected_attrs=None)
        self.assertTrue(result.objects, list)
        self.assertTrue(result.objects)

    @mock.patch('tacker.objects.vnf_instance._destroy_vnf_instance')
    def test_destroy(self, mock_vnf_destroy):
        vnf_instance_data = fakes.get_vnf_instance_data(
            self.vnf_package.vnfd_id)
        vnf_instance = objects.VnfInstance(context=self.context,
                                           **vnf_instance_data)
        vnf_instance.create()
        vnf_instance.destroy(self.context)
        mock_vnf_destroy.assert_called_with(self.context, vnf_instance.id)

    def test_destroy_failure_without_id(self):
        vnf_instance_obj = objects.VnfInstance(context=self.context)
        self.assertRaises(exceptions.ObjectActionError,
                          vnf_instance_obj.destroy, self.context)
