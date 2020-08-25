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

from oslo_utils import uuidutils

from tacker import context
from tacker import objects
from tacker.tests.unit.db.base import SqlTestCase
from tacker.tests.unit.objects import fakes
from tacker.tests import uuidsentinel


class TestVnfLcmOpOcc(SqlTestCase):

    def setUp(self):
        super(TestVnfLcmOpOcc, self).setUp()
        self.context = context.get_admin_context()
        self.vnf_package = self._create_vnf_package()
        self.vnf_package_vnfd = self._create_and_upload_vnf_package_vnfd()
        self.vnf_instance = self._create_vnf_instance()
        self.vnf_lcm_op_occs = self._create_vnf_lcm_op_occs()

    def _create_vnf_package(self):
        vnfpkgm = objects.VnfPackage(context=self.context,
                                     **fakes.vnf_package_data)
        vnfpkgm.create()
        return vnfpkgm

    def _create_and_upload_vnf_package_vnfd(self):
        vnf_package = objects.VnfPackage(context=self.context,
                                         **fakes.vnf_package_data)
        vnf_package.create()

        vnf_pack_vnfd = fakes.get_vnf_package_vnfd_data(
            vnf_package.id, uuidsentinel.vnfd_id)

        vnf_pack_vnfd_obj = objects.VnfPackageVnfd(
            context=self.context, **vnf_pack_vnfd)
        vnf_pack_vnfd_obj.create()

        return vnf_pack_vnfd_obj

    def _create_vnf_instance(self):
        vnf_instance_data = fakes.get_vnf_instance_data(
            self.vnf_package_vnfd.vnfd_id)
        vnf_instance = objects.VnfInstance(context=self.context,
                                           **vnf_instance_data)
        vnf_instance.create()

        return vnf_instance

    def _create_vnf_lcm_op_occs(self):
        id = uuidutils.generate_uuid()
        vnf_lcm_op_occs_data = \
            fakes.get_lcm_op_occs_data(id, self.vnf_instance.id)
        vnf_lcm_op_occs = objects.vnf_lcm_op_occs.VnfLcmOpOcc(
            context=self.context, **vnf_lcm_op_occs_data)
        vnf_lcm_op_occs.create()
        return vnf_lcm_op_occs

    def test_create(self):
        id = uuidutils.generate_uuid()
        vnf_lcm_op_occs_data = \
            fakes.get_lcm_op_occs_data(id, self.vnf_instance.id)
        vnf_lcm_op_occs = objects.vnf_lcm_op_occs.VnfLcmOpOcc(
            context=self.context, **vnf_lcm_op_occs_data)
        vnf_lcm_op_occs.create()
        self.assertTrue(vnf_lcm_op_occs.vnf_instance_id)

    def test_save(self):
        id = uuidutils.generate_uuid()
        vnf_lcm_op_occs_data = \
            fakes.get_lcm_op_occs_data(id, self.vnf_instance.id)
        vnf_lcm_op_occs = objects.vnf_lcm_op_occs.VnfLcmOpOcc(
            context=self.context, **vnf_lcm_op_occs_data)
        vnf_lcm_op_occs.create()

        problem_obj = objects.vnf_lcm_op_occs.ProblemDetails()
        problem_obj.status = '500'
        problem_obj.detail = 'test_err'
        changed_info = objects.vnf_lcm_op_occs.VnfInfoModifications(
            context=self.context, **fakes.get_changed_info_data())
        vnf_lcm_op_occs.operation_state = 'FAILED_TEMP'
        vnf_lcm_op_occs.error = problem_obj
        vnf_lcm_op_occs.id = uuidsentinel.vnf_lcm_op_occs_id
        vnf_lcm_op_occs.changed_info = changed_info
        vnf_lcm_op_occs.save()

        self.assertEqual('FAILED_TEMP', vnf_lcm_op_occs.operation_state)
        self.assertEqual(problem_obj, vnf_lcm_op_occs.error)
