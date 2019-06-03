#    Copyright 2019 NTT DATA.
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
from tacker.objects import vnf_package
from tacker.objects import vnf_package_vnfd
from tacker.tests.unit.db.base import SqlTestCase
from tacker.tests.unit.objects import fakes
from tacker.tests import uuidsentinel


class TestVnfPackageVnfd(SqlTestCase):

    def setUp(self):
        super(TestVnfPackageVnfd, self).setUp()
        self.context = context.get_admin_context()

    def test_create(self):
        vnf_pack = vnf_package.VnfPackage(context=self.context,
                                          **fakes.vnf_package_data)
        vnf_pack.create()
        vnf_pack_vnfd = {
            'package_uuid': vnf_pack.id,
            'vnfd_id': uuidsentinel.vnfd_id,
            'vnf_provider': 'test_provider',
            'vnf_product_name': 'test_product_name',
            'vnf_software_version': 'test_version',
            'vnfd_version': 'test_vnfd_version',
        }

        vnf_pack_vnfd_obj = vnf_package_vnfd.VnfPackageVnfd(
            context=self.context, **vnf_pack_vnfd)
        vnf_pack_vnfd_obj.create()
        self.assertTrue(vnf_pack_vnfd_obj.id)

    def test_create_with_id(self):
        vnf_pack = vnf_package.VnfPackage(context=self.context,
                                          **fakes.vnf_package_data)
        vnf_pack.create()
        vnf_pack_vnfd = {'id': uuidsentinel.id}

        vnf_pack_vnfd_obj = vnf_package_vnfd.VnfPackageVnfd(
            context=self.context, **vnf_pack_vnfd)
        self.assertRaises(
            exceptions.ObjectActionError,
            vnf_pack_vnfd_obj.create)
