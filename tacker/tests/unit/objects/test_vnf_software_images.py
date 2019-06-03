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

from tacker.common import exceptions
from tacker import context
from tacker import objects
from tacker.tests.unit.db.base import SqlTestCase
from tacker.tests.unit.objects import fakes
from tacker.tests import uuidsentinel


class TestVnfSoftwareImages(SqlTestCase):

    def setUp(self):
        super(TestVnfSoftwareImages, self).setUp()
        self.context = context.get_admin_context()
        self.vnf_package = self._create_vnf_package()
        self.vnf_deployment_flavour = self._create_vnf_deployment_flavour()
        self.vnf_softwate_images = self._create_vnf_softwate_images()

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

    def _create_vnf_softwate_images(self):
        software_image = fakes.software_image
        software_image.update(
            {'flavour_uuid': self.vnf_deployment_flavour.id})

        vnf_soft_image_obj = objects.VnfSoftwareImage(
            context=self.context, **software_image)
        vnf_soft_image_obj.create()
        return vnf_soft_image_obj

    def test_create(self):
        software_image = fakes.software_image
        software_image.update(
            {'flavour_uuid': self.vnf_deployment_flavour.id})

        vnf_soft_image_obj = objects.VnfSoftwareImage(
            context=self.context, **software_image)
        vnf_soft_image_obj.create()
        self.assertTrue(vnf_soft_image_obj.id)

    def test_software_image_create_with_id(self):
        software_image = fakes.software_image
        software_image.update({'id': uuidsentinel.id})
        vnf_soft_image_obj = objects.VnfSoftwareImage(
            context=self.context, **software_image)
        self.assertRaises(
            exceptions.ObjectActionError,
            vnf_soft_image_obj.create)

    def test_get_by_id(self):
        vnf_software_images = objects.VnfSoftwareImage.get_by_id(
            self.context, self.vnf_softwate_images.id, expected_attrs=None)
        self.compare_obj(self.vnf_softwate_images, vnf_software_images)

    def test_get_by_id_with_no_existing_id(self):
        self.assertRaises(
            exceptions.VnfSoftwareImageNotFound,
            objects.VnfSoftwareImage.get_by_id, self.context,
            uuidsentinel.invalid_uuid)

    def test_attribute_with_valid_data(self):
        data = {'id': self.vnf_softwate_images.id}
        vnf_software_image_obj = objects.VnfSoftwareImage(
            context=self.context, **data)
        vnf_software_image_obj.obj_load_attr('name')
        self.assertEqual('test', vnf_software_image_obj.name)

    def test_invalid_attribute(self):
        self.assertRaises(exceptions.ObjectActionError,
                          self.vnf_softwate_images.obj_load_attr, 'invalid')

    def test_obj_load_attr_without_context(self):
        data = {'id': self.vnf_softwate_images.id}
        vnf_software_image_obj = objects.VnfSoftwareImage(**data)
        self.assertRaises(exceptions.OrphanedObjectError,
                          vnf_software_image_obj.obj_load_attr, 'name')

    def test_obj_load_attr_without_id_in_object(self):
        data = {'name': self.vnf_softwate_images.name}
        vnf_software_image_obj = objects.VnfSoftwareImage(
            context=self.context, **data)
        self.assertRaises(exceptions.ObjectActionError,
                          vnf_software_image_obj.obj_load_attr, 'name')
