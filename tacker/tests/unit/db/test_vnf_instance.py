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
from tacker import objects
from tacker.objects import vnf_instance
from tacker.objects import vnf_package_vnfd
from tacker.tests.unit.db.base import SqlTestCase
from tacker.tests.unit.objects import fakes
from tacker.tests import uuidsentinel


class TestVnfLcm(SqlTestCase):

    def setUp(self):
        super(TestVnfLcm, self).setUp()
        self.context = context.get_admin_context()
        self.vnf_instance = self._create_vnf_instance()

    def _create_vnf_instance(self):
        vnf_package_vnfd = self._create_and_upload_vnf_package()
        vnf_instance_data = fakes.get_vnf_instance_data(
            vnf_package_vnfd.vnfd_id)
        vnf_instance = objects.VnfInstance(context=self.context,
                                           **vnf_instance_data)
        vnf_instance.create()
        return vnf_instance

    def _create_and_upload_vnf_package(self):
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

        return vnf_pack_vnfd_obj

    def test_vnf_instance_get_by_id(self):
        result = vnf_instance._vnf_instance_get_by_id(
            self.context, self.vnf_instance.id, columns_to_join=None)
        self.assertEqual(self.vnf_instance.id, result.id)

    def test_vnf_instance_create(self):
        result = vnf_instance._vnf_instance_create(
            self.context, fakes.fake_vnf_instance_model_dict())
        self.assertTrue(result.id)

    def test_vnf_instance_update(self):
        update = {"vnf_instance_name": 'updated_instance'}
        result = vnf_instance._vnf_instance_update(
            self.context, self.vnf_instance.id, update)
        self.assertEqual('updated_instance', result.vnf_instance_name)

    def test_destroy_vnf_instance(self):
        vnf_instance._destroy_vnf_instance(self.context,
                                         self.vnf_instance.id)
        self.assertRaises(
            exceptions.VnfInstanceNotFound,
            objects.VnfInstance.get_by_id, self.context,
            self.vnf_instance.id)
