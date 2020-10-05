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

from unittest import mock

from oslo_utils import uuidutils

from tacker.common import exceptions
from tacker import context
from tacker.db.db_sqlalchemy import models
from tacker import objects
from tacker.tests.unit.db.base import SqlTestCase
from tacker.tests.unit.objects import fakes
from tacker.tests import uuidsentinel


class TestVnfPackage(SqlTestCase):

    def setUp(self):
        super(TestVnfPackage, self).setUp()
        self.context = context.get_admin_context()
        self.vnf_package = self._create_vnf_package()

    def _create_vnf_package(self):
        vnfpkgm = objects.VnfPackage(context=self.context,
                                     **fakes.vnf_package_data)
        vnfpkgm.create()
        return vnfpkgm

    def test_create(self):
        vnfpkgm = objects.VnfPackage(context=self.context,
                                     **fakes.vnf_package_data)
        vnfpkgm.create()
        self.assertTrue(vnfpkgm.id)
        self.assertEqual('CREATED', vnfpkgm.onboarding_state)
        self.assertEqual('NOT_IN_USE', vnfpkgm.usage_state)
        self.assertEqual('DISABLED', vnfpkgm.operational_state)
        self.assertEqual(0, vnfpkgm.size)

    def test_create_without_user_define_data(self):
        vnf_pack = fakes.vnf_package_data
        vnf_pack.update({'user_data': {}})
        vnfpkgm = objects.VnfPackage(context=self.context, **vnf_pack)
        vnfpkgm.create()
        self.assertTrue(vnfpkgm.id)
        self.assertEqual('CREATED', vnfpkgm.onboarding_state)
        self.assertEqual('NOT_IN_USE', vnfpkgm.usage_state)
        self.assertEqual('DISABLED', vnfpkgm.operational_state)

    @mock.patch.object(uuidutils, 'generate_uuid')
    @mock.patch('tacker.objects.vnf_package._vnf_package_create')
    def test_create_ignore_flavours(
            self, mock_vnf_package_create, mock_uuid):
        fake_data = fakes.fake_vnf_package_response
        mock_uuid.return_value = fake_data['id']
        mock_vnf_package_create.return_value = models.VnfPackage(**fake_data)

        flavour_data = fakes.vnf_deployment_flavour
        flavour_data.update({'package_uuid': self.vnf_package.id})
        vnf_deployment_flavour = objects.VnfDeploymentFlavour(**flavour_data)

        fake_vnf_deployment_flavours = objects.VnfDeploymentFlavoursList(
            objects=[vnf_deployment_flavour])
        vnf_pack = fakes.vnf_package_data
        vnf_pack.update(
            {'vnf_deployment_flavours': fake_vnf_deployment_flavours})
        vnfpkgm = objects.VnfPackage(context=self.context, **vnf_pack)
        vnfpkgm.create()

        mock_vnf_package_create.assert_called_once_with(
            self.context, fake_data, user_data={'abc': 'xyz'})

    def test_get_by_id(self):
        vnfpkgm = objects.VnfPackage.get_by_id(self.context,
                                               self.vnf_package.id,
                                               expected_attrs=None)
        self.compare_obj(self.vnf_package, vnfpkgm,
                         allow_missing=['vnf_deployment_flavours',
                                        'vnf_artifacts'])

    def test_get_by_id_with_no_existing_id(self):
        self.assertRaises(
            exceptions.VnfPackageNotFound,
            objects.VnfPackage.get_by_id, self.context,
            uuidsentinel.invalid_uuid)

    def test_create_with_id(self):
        vnfpkgm = objects.VnfPackage(context=self.context,
                **fakes.vnf_package_data)
        vnfpkgm['id'] = uuidsentinel.uuid
        vnfpkgm.create()
        self.assertTrue(vnfpkgm.id)
        self.assertEqual('CREATED', vnfpkgm.onboarding_state)
        self.assertEqual('NOT_IN_USE', vnfpkgm.usage_state)
        self.assertEqual('DISABLED', vnfpkgm.operational_state)
        self.assertEqual(0, vnfpkgm.size)

    def test_save(self):
        self.vnf_package.onboarding_state = 'ONBOARDED'
        self.vnf_package.save()
        self.assertEqual('ONBOARDED', self.vnf_package.onboarding_state)

    def test_save_error(self):
        fake_data = {'id': uuidsentinel.uuid}
        vnf_pack_obj = objects.VnfPackage(context=self.context,
                                          **fake_data)
        self.assertRaises(exceptions.VnfPackageNotFound, vnf_pack_obj.save)

    @mock.patch('tacker.objects.vnf_package._destroy_vnf_package')
    def test_destroy(self, mock_vnf_destroy):
        self.vnf_package.destroy(self.context)
        mock_vnf_destroy.assert_called_with(self.context, self.vnf_package.id)

    def test_destroy_without_id(self):
        vnf_obj = objects.VnfPackage(context=self.context)
        self.assertRaises(exceptions.ObjectActionError, vnf_obj.destroy,
                          self.context)

    def test_get_all(self):
        result = objects.VnfPackagesList.get_all(self.context,
                                                 expected_attrs=None)
        self.assertIsInstance(result.objects, list)
        self.assertTrue(result.objects)

    def test_get_by_id_with_flavours(self):
        flavour_data = fakes.vnf_deployment_flavour
        flavour_data.update({'package_uuid': self.vnf_package.id})
        vnf_deployment_flavour_obj = objects.VnfDeploymentFlavour(
            context=self.context, **flavour_data)
        vnf_deployment_flavour_obj.create()
        vnfpkgm = objects.VnfPackage.get_by_id(
            self.context, self.vnf_package.id,
            expected_attrs=['vnf_deployment_flavours'])
        self.assertEqual(1, len(vnfpkgm.vnf_deployment_flavours.objects))
        self.compare_obj(vnf_deployment_flavour_obj,
                         vnfpkgm.vnf_deployment_flavours[0],
                         allow_missing=['software_images',
                                        'updated_at',
                                        'deleted', 'deleted_at'])

    def test_get_by_id_without_flavours(self):
        vnfpkgm = objects.VnfPackage.get_by_id(
            self.context, self.vnf_package.id, expected_attrs=None)
        self.assertEqual([], vnfpkgm.vnf_deployment_flavours.objects)

    def test_attribute_with_valid_data(self):
        data = {'id': self.vnf_package.id}
        vnf_pack_obj = objects.VnfPackage(context=self.context, **data)
        vnf_pack_obj.obj_load_attr('user_data')
        self.assertEqual({'abc': 'xyz'}, vnf_pack_obj.user_data)

    def test_invalid_attribute(self):
        self.assertRaises(exceptions.ObjectActionError,
                          self.vnf_package.obj_load_attr, 'invalid')

    def test_obj_load_attr_without_context(self):
        data = {'id': self.vnf_package.id}
        vnf_package_obj = objects.VnfPackage(**data)
        self.assertRaises(exceptions.OrphanedObjectError,
                          vnf_package_obj.obj_load_attr, 'algorithm')

    def test_obj_load_attr_without_id_in_object(self):
        data = {'user_data': {'tests': 'test_data'}}
        vnf_deployment_flavour_obj = objects.VnfDeploymentFlavour(
            context=self.context, **data)
        self.assertRaises(
            exceptions.ObjectActionError,
            vnf_deployment_flavour_obj.obj_load_attr, 'algorithm')

    def test_vnf_package_list_by_filter(self):
        filters = {'field': 'onboarding_state', 'model': 'VnfPackage',
                   'value': 'CREATED',
                   'op': '=='}
        vnfpkgm_list = objects.VnfPackagesList.get_by_filters(
            self.context, filters=filters)
        self.assertEqual(1, len(vnfpkgm_list))

    def test_obj_make_compatible(self):
        data = {'id': self.vnf_package.id}
        vnf_package_obj = objects.VnfPackage(context=self.context, **data)
        fake_vnf_package_obj = objects.VnfPackage(context=self.context, **data)
        obj_primitive = fake_vnf_package_obj.obj_to_primitive('1.0')
        obj = vnf_package_obj.obj_from_primitive(obj_primitive)
        self.assertIn('size', obj.fields)
