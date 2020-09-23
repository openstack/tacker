#    Copyright 2020 NTT DATA.
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
from tacker.objects import vnf_artifact
from tacker.objects import vnf_package
from tacker.tests.unit.db.base import SqlTestCase
from tacker.tests.unit.objects import fakes
from tacker.tests import uuidsentinel


class TestVnfPackageArtifact(SqlTestCase):

    def setUp(self):
        super(TestVnfPackageArtifact, self).setUp()
        self.context = context.get_admin_context()
        self.vnf_artifacts = self._create_vnf_artifact()

    def test_vnf_package_artifact_create(self):
        vnf_pack = vnf_package.VnfPackage(context=self.context,
                                          **fakes.vnf_package_data)
        vnf_pack.create()
        vnf_pack_artifact_data = fakes.vnf_pack_artifact_data(vnf_pack.id)
        result = vnf_artifact._vnf_artifacts_create(
            self.context, vnf_pack_artifact_data)
        self.assertTrue(result.id)

    def _create_vnf_artifact(self):
        vnf_pack = vnf_package.VnfPackage(context=self.context,
                                          **fakes.vnf_package_data)
        vnf_pack.create()
        vnf_pack_artifact_data = fakes.vnf_pack_artifact_data(vnf_pack.id)
        vnf_artifact_obj = vnf_artifact.VnfPackageArtifactInfo(
            context=self.context, **vnf_pack_artifact_data)
        vnf_artifact_obj.create()
        self.assertEqual('scripts/install.sh', vnf_artifact_obj.artifact_path)
        return vnf_artifact_obj

    def test_get_by_id(self):
        vnf_artifacts = vnf_artifact.VnfPackageArtifactInfo.get_by_id(
            self.context, self.vnf_artifacts.id)
        self.compare_obj(self.vnf_artifacts, vnf_artifacts)

    def test_get_by_id_with_no_existing_id(self):
        self.assertRaises(
            exceptions.VnfArtifactNotFound,
            vnf_artifact.VnfPackageArtifactInfo.get_by_id, self.context,
            uuidsentinel.invalid_uuid)

    def test_attribute_with_valid_data(self):
        data = {'id': self.vnf_artifacts.id}
        vnf_artifact_obj = vnf_artifact.VnfPackageArtifactInfo(
            context=self.context, **data)
        vnf_artifact_obj.obj_load_attr('artifact_path')
        self.assertEqual('scripts/install.sh', vnf_artifact_obj.artifact_path)

    def test_invalid_attribute(self):
        self.assertRaises(exceptions.ObjectActionError,
                          self.vnf_artifacts.obj_load_attr, 'invalid')

    def test_obj_load_attr_without_context(self):
        data = {'id': self.vnf_artifacts.id}
        vnf_artifact_obj = vnf_artifact.VnfPackageArtifactInfo(**data)
        self.assertRaises(exceptions.OrphanedObjectError,
                          vnf_artifact_obj.obj_load_attr, 'artifact_path')

    def test_obj_load_attr_without_id_in_object(self):
        data = {'artifact_path': self.vnf_artifacts.artifact_path}
        vnf_artifact_obj = vnf_artifact.VnfPackageArtifactInfo(
            context=self.context, **data)
        self.assertRaises(exceptions.ObjectActionError,
                          vnf_artifact_obj.obj_load_attr, 'artifact_path')
