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
from tacker import objects
from tacker.tests.unit.db.base import SqlTestCase
from tacker.tests.unit.objects import fakes
from tacker.tests import uuidsentinel


class TestVnfResource(SqlTestCase):

    def setUp(self):
        super(TestVnfResource, self).setUp()
        self.context = context.get_admin_context()
        self.vnf_instance = self._create_vnf_instance()

    def _create_vnf_instance(self):
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

        vnf_instance_data = fakes.get_vnf_instance_data(
            vnf_pack_vnfd_obj.vnfd_id)
        vnf_instance = objects.VnfInstance(context=self.context,
                                           **vnf_instance_data)
        vnf_instance.create()

        return vnf_instance

    def test_create(self):
        vnf_resource = objects.VnfResource(
            context=self.context,
            **fakes.fake_vnf_resource_data(self.vnf_instance.id))
        vnf_resource.create()
        self.assertTrue(vnf_resource.id)

    def test_create_with_id(self):

        vnf_resource_data = fakes.fake_vnf_resource_data(self.vnf_instance.id)
        vnf_resource_data.update({'id': uuidsentinel.uuid})

        vnf_resource_obj = objects.VnfResource(
            context=self.context, **vnf_resource_data)
        self.assertRaises(exceptions.ObjectActionError,
                          vnf_resource_obj.create)

    @mock.patch('tacker.objects.vnf_resources._vnf_resource_update')
    def test_save(self, mock_resource_update):
        vnf_resource = objects.VnfResource(
            context=self.context,
            **fakes.fake_vnf_resource_data(self.vnf_instance.id))
        vnf_resource.create()
        mock_resource_update.return_value = \
            fakes.vnf_resource_model_object(vnf_resource)
        vnf_resource.resource_name = 'fake'
        vnf_resource.save()
        mock_resource_update.assert_called_with(
            self.context, vnf_resource.id, {'resource_name': 'fake'})

    def test_save_error(self):
        vnf_resource = objects.VnfResource(
            context=self.context,
            **fakes.fake_vnf_resource_data(self.vnf_instance.id))
        vnf_resource.create()
        vnf_resource.destroy(self.context)
        vnf_resource.resource_name = 'fake'
        self.assertRaises(exceptions.VnfResourceNotFound, vnf_resource.save)

    @mock.patch('tacker.objects.vnf_resources._destroy_vnf_resource')
    def test_destroy(self, mock_vnf_destroy):
        vnf_resource = objects.VnfResource(
            context=self.context,
            **fakes.fake_vnf_resource_data(self.vnf_instance.id))
        vnf_resource.create()
        vnf_resource.destroy(self.context)
        mock_vnf_destroy.assert_called_with(self.context, vnf_resource.id)

    def test_destroy_failure_without_id(self):
        vnf_resource_obj = objects.VnfResource(context=self.context)
        self.assertRaises(exceptions.ObjectActionError,
                          vnf_resource_obj.destroy, self.context)

    def test_get_by_vnf_instance_id(self):
        vnf_resource = objects.VnfResource(
            context=self.context,
            **fakes.fake_vnf_resource_data(self.vnf_instance.id))
        vnf_resource.create()
        vnf_resource_list = objects.VnfResourceList()
        result = vnf_resource_list.get_by_vnf_instance_id(
            self.context, self.vnf_instance.id)
        self.assertIsInstance(result.objects, list)
        self.assertTrue(result.objects)
