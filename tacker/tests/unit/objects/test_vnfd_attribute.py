# Copyright (C) 2021 FUJITSU
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

import ddt
from unittest import mock

from tacker import context
from tacker.db import api as sqlalchemy_api
from tacker.db.nfvo import nfvo_db
from tacker import objects
from tacker.tests.unit.db.base import SqlTestCase
from tacker.tests.unit.objects import fakes
from tacker.tests import uuidsentinel

get_engine = sqlalchemy_api.get_engine


@ddt.ddt
class TestVnfdAttribute(SqlTestCase):

    def setUp(self):
        super(TestVnfdAttribute, self).setUp()
        self.context = context.get_admin_context()
        self.vims = nfvo_db.Vim(**fakes.vim_data)
        self.engine = get_engine()
        self.conn = self.engine.connect()
        self.vim = nfvo_db.Vim()
        self.vnfd_attribute_data = {
            "id": uuidsentinel.id,
            "vnfd_id": uuidsentinel.vnfd_id,
            "key": "key",
            "value": "value"
        }
        self.vnfd_attribute_object = objects.vnfd_attribute.VnfdAttribute(
            context=self.context, **self.vnfd_attribute_data)

    @mock.patch.object(objects.vnfd_attribute, '_vnfd_attribute_create')
    def test_create(self, mock_vnfd_create):
        mock_vnfd_create.return_value = {
            "id": uuidsentinel.id,
            "vnfd_id": uuidsentinel.vnfd_id,
            "key": "key",
            "value": "value"
        }
        self.vnfd_attribute_object.create()

    def test_obj_from_db_obj(self):
        db_obj = {"key": "value"}
        result = self.vnfd_attribute_object.obj_from_db_obj(
            self.context, db_obj)
        self.assertIsInstance(result, objects.vnfd_attribute.VnfdAttribute)

    def test_destroy(self):
        self.vnfd_attribute_object.destroy(self.vnfd_attribute_object.id)

    def test_delete(self):
        self.vnfd_attribute_object.delete(self.vnfd_attribute_object.id)

    def test_check_vnfd_attribute(self):
        result = self.vnfd_attribute_object.check_vnfd_attribute(
            self.vnfd_attribute_object.id)
        self.assertEqual(result, "FALSE")
