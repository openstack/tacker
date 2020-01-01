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


from tacker.common import exceptions
from tacker import context
from tacker.db.db_sqlalchemy.models import VnfResource
from tacker import objects
from tacker.objects import vnf_package_vnfd
from tacker.objects import vnf_resources
from tacker.tests.unit.db.base import SqlTestCase
from tacker.tests.unit.objects import fakes
from tacker.tests import uuidsentinel


class TestVnfResource(SqlTestCase):

    def setUp(self):
        super(TestVnfResource, self).setUp()
        self.context = context.get_admin_context()
        self.vnf_instance = self._create_vnf_instance()
        self.vnf_resource = self._create_vnf_resource()

    def _create_vnf_instance(self):
        vnf_package = objects.VnfPackage(context=self.context,
                                         **fakes.vnf_package_data)
        vnf_package.create()

        vnf_pack_vnfd = fakes.get_vnf_package_vnfd_data(
            vnf_package.id, uuidsentinel.vnfd_id)

        vnf_pack_vnfd_obj = vnf_package_vnfd.VnfPackageVnfd(
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

    def _create_vnf_resource(self):
        vnf_resource = vnf_resources.VnfResource(
            context=self.context,
            **fakes.fake_vnf_resource_data(self.vnf_instance.id))
        vnf_resource.create()
        return vnf_resource

    def test_vnf_resource_create(self):
        resource_data = fakes.fake_vnf_resource_data(
            self.vnf_instance.id)
        resource_data.update({'id': uuidsentinel.id})
        result = vnf_resources._vnf_resource_create(
            self.context, resource_data)
        self.assertTrue(result.id)
        self.assertEqual('test', result.resource_name)

    def test_vnf_resource_get_by_id(self):
        result = vnf_resources._vnf_resource_get_by_id(
            self.context, self.vnf_resource.id)
        self.assertEqual(self.vnf_resource.id, result.id)

    def test_vnf_resource_update(self):
        update = {'resource_name': 'fake'}
        result = vnf_resources._vnf_resource_update(
            self.context, self.vnf_resource.id, update)
        self.assertEqual('fake', result.resource_name)

    def test_destroy_vnf_resource(self):
        vnf_resources._destroy_vnf_resource(
            self.context, self.vnf_resource.id)
        self.assertRaises(
            exceptions.VnfResourceNotFound,
            vnf_resources.VnfResource.get_by_id, self.context,
            self.vnf_resource.id)

    def test_vnf_resource_list(self):
        result = vnf_resources._vnf_resource_list(
            self.context, self.vnf_instance.id)
        self.assertTrue(result[0].id)
        self.assertIsInstance(result[0], VnfResource)

    def test_make_vnf_resources_list(self):
        vnf_resource_db = vnf_resources._vnf_resource_list(
            self.context, self.vnf_instance.id)
        vnf_resource_list = vnf_resources._make_vnf_resources_list(
            self.context, vnf_resources.VnfResourceList(), vnf_resource_db)
        self.assertIsInstance(vnf_resource_list,
                              vnf_resources.VnfResourceList)
        self.assertTrue(vnf_resource_list.objects[0].id)
