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

from tacker.common import exceptions
from tacker import context
from tacker import objects
from tacker.tests.unit.db.base import SqlTestCase
from tacker.tests.unit.objects import fakes
from tacker.tests import uuidsentinel


class TestVnfDeploymentFlavour(SqlTestCase):

    def setUp(self):
        super(TestVnfDeploymentFlavour, self).setUp()
        self.context = context.get_admin_context()
        self.vnf_package = self._create_vnf_package()
        self.vnf_deployment_flavour = self._create_vnf_deployment_flavour()

    def _create_vnf_package(self):
        vnfpkgm = objects.VnfPackage(context=self.context,
                                     **fakes.vnf_package_data)
        vnfpkgm.create()
        return vnfpkgm

    def _create_vnf_deployment_flavour(self):
        flavour_data = fakes.vnf_deployment_flavour
        flavour_data.update({'package_uuid': self.vnf_package.id})
        vnf_deployment_flavour = objects.VnfDeploymentFlavour(
            context=self.context, **flavour_data)
        vnf_deployment_flavour.create()
        return vnf_deployment_flavour

    def test_create(self):
        flavour_data = fakes.vnf_deployment_flavour
        flavour_data.update({'package_uuid': self.vnf_package.id})
        vnf_deployment_flavour_obj = objects.VnfDeploymentFlavour(
            context=self.context, **flavour_data)

        vnf_deployment_flavour_obj.create()
        self.assertTrue(vnf_deployment_flavour_obj.id)

    def test_create_with_software_images(self):
        software_images = objects.VnfSoftwareImage(**fakes.software_image)
        fake_software_images = objects.VnfSoftwareImagesList(
            objects=[software_images])
        flavour_data = fakes.vnf_deployment_flavour
        flavour_data.update({'software_images': fake_software_images})
        flavour_data.update({'package_uuid': self.vnf_package.id})
        vnf_deployment_flavour_obj = objects.VnfDeploymentFlavour(
            context=self.context, **flavour_data)

        vnf_deployment_flavour_obj.create()
        self.assertTrue(vnf_deployment_flavour_obj.id)

    def test_get_by_id(self):
        vnf_deployment_flavour = objects.VnfDeploymentFlavour.get_by_id(
            self.context, self.vnf_deployment_flavour.id, expected_attrs=None)
        self.compare_obj(self.vnf_deployment_flavour, vnf_deployment_flavour,
                         allow_missing=['software_images',
                                        'updated_at',
                                        'deleted', 'deleted_at'])

    def test_get_by_id_with_no_existing_id(self):
        self.assertRaises(
            exceptions.VnfDeploymentFlavourNotFound,
            objects.VnfDeploymentFlavour.get_by_id, self.context,
            uuidsentinel.invalid_uuid)

    def test_create_with_id(self):
        vnf_deployment_flavour_obj = {'id': uuidsentinel.uuid}
        vnf_deployment_flavour = objects.VnfDeploymentFlavour(
            context=self.context, **vnf_deployment_flavour_obj)
        self.assertRaises(exceptions.ObjectActionError,
                          vnf_deployment_flavour.create)

    @mock.patch('tacker.objects.vnf_deployment_flavour.'
                '_destroy_vnf_deployment_flavour')
    def test_destroy(self, mock_vnf_deployment_flavour_destroy):
        self.vnf_deployment_flavour.destroy(self.context)
        mock_vnf_deployment_flavour_destroy.assert_called_with(
            self.context, self.vnf_deployment_flavour.id)

    def test_destroy_without_id(self):
        vnf_deployment_flavour_obj = objects.VnfDeploymentFlavour(
            context=self.context)
        self.assertRaises(exceptions.ObjectActionError,
                          vnf_deployment_flavour_obj.destroy, self.context)

    def test_attribute_with_valid_data(self):
        data = {'id': self.vnf_deployment_flavour.id}
        vnf_deployment_flavour_obj = objects.VnfDeploymentFlavour(
            context=self.context, **data)
        vnf_deployment_flavour_obj.obj_load_attr('flavour_id')
        self.assertEqual('simple', vnf_deployment_flavour_obj.flavour_id)

    def test_invalid_attribute(self):
        self.assertRaises(
            exceptions.ObjectActionError,
            self.vnf_deployment_flavour.obj_load_attr, 'invalid')

    def test_obj_load_attr_without_context(self):
        data = {'id': self.vnf_deployment_flavour.id}
        vnf_deployment_flavour_obj = objects.VnfDeploymentFlavour(**data)
        self.assertRaises(exceptions.OrphanedObjectError,
                          vnf_deployment_flavour_obj.obj_load_attr,
                          'flavour_id')

    def test_obj_load_attr_without_id_in_object(self):
        data = {'flavour_id': self.vnf_deployment_flavour.flavour_id}
        vnf_deployment_flavour_obj = objects.VnfDeploymentFlavour(
            context=self.context, **data)
        self.assertRaises(exceptions.ObjectActionError,
                          vnf_deployment_flavour_obj.obj_load_attr,
                          'flavour_id')

    def test_get_by_id_with_software_images(self):
        software_image = fakes.software_image
        software_image.update(
            {'flavour_uuid': self.vnf_deployment_flavour.id})

        vnf_soft_image_obj = objects.VnfSoftwareImage(
            context=self.context, **software_image)
        vnf_soft_image_obj.create()
        vnf_deployment_flavour = objects.VnfDeploymentFlavour.get_by_id(
            self.context, self.vnf_deployment_flavour.id,
            expected_attrs=['software_images'])
        self.assertEqual(1,
                         len(vnf_deployment_flavour.software_images.objects))
        self.compare_obj(vnf_soft_image_obj,
                         vnf_deployment_flavour.software_images[0])
