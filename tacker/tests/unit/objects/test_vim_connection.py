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

from tacker import context
from tacker import objects
from tacker.tests.unit.db.base import SqlTestCase
from tacker.tests import uuidsentinel


class TestVnfResource(SqlTestCase):

    def setUp(self):
        super(TestVnfResource, self).setUp()
        self.context = context.get_admin_context()

    def test_obj_from_primitive_and_object_to_dict(self):
        vim_connection_dict = {'id': uuidsentinel.uuid,
                               'vim_id': uuidsentinel.uuid,
                               'vim_type': 'openstack'}
        result = objects.VimConnectionInfo.obj_from_primitive(
            vim_connection_dict, self.context)
        self.assertEqual(True, isinstance(result, objects.VimConnectionInfo))
        self.assertEqual('openstack', result.vim_type)
        vim_connection_dict = result.to_dict()
        self.assertEqual(True, isinstance(vim_connection_dict, dict))
        self.assertEqual('openstack', vim_connection_dict['vim_type'])
