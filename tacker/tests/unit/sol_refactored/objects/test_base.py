# Copyright (C) 2021 Nippon Telegraph and Telephone Corporation
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

import datetime
from unittest import mock

from oslo_serialization import jsonutils

from tacker.sol_refactored.objects import base
from tacker.sol_refactored.objects import fields
from tacker.tests import base as tests_base


@base.TackerObjectRegistry.register
class MyObj(base.TackerObject):

    VERSION = '1.0'

    fields = {
        'id': fields.StringField(nullable=False),
        'data': fields.StringField(nullable=False),
        'listData': fields.ListOfObjectsField(
            'MySubObj', nullable=True),
        'createdAt': fields.DateTimeField(nullable=False),
    }


@base.TackerObjectRegistry.register
class MySubObj(base.TackerObject):

    VERSION = '1.0'

    fields = {
        'id': fields.StringField(nullable=False),
        'data': fields.StringField(nullable=False),
    }


@base.TackerObjectRegistry.register
class MyDBObj(MyObj, base.TackerPersistentObject):

    pass


class TestTackerObject(tests_base.BaseTestCase):

    def test_tacker_obj_get_changes(self):
        o = MyObj.from_dict({'id': 'foo',
                             'data': 'abcde',
                             'createdAt': '2021-09-01T12:34:56+09:00'})
        o.obj_reset_changes()
        self.assertEqual(o.tacker_obj_get_changes(), {})
        o.data = '12345'
        o.createdAt = datetime.datetime(2021, 8, 7, 6, 5, 44,
            tzinfo=datetime.timezone(datetime.timedelta(hours=-9)))
        changes = o.tacker_obj_get_changes()
        self.assertEqual(len(changes), 2)
        self.assertIn('data', changes)
        self.assertIsNone(changes['createdAt'].tzinfo)
        self.assertEqual(changes['createdAt'].hour, o.createdAt.hour + 9)

    def test_from_dict(self):
        o = MyObj.from_dict({'id': 'foo',
                             'data': 'abcde',
                             'listData': [
                                 {'id': 'foo1', 'data': 'bar1'},
                                 {'id': 'foo2', 'data': 'bar2'},
                             ],
                             'createdAt': '2021-09-01T12:34:56+09:00'})
        self.assertEqual(o.id, 'foo')
        self.assertIsInstance(o.createdAt, datetime.datetime)
        self.assertEqual(len(o.listData), 2)
        self.assertEqual(o.listData[1].data, 'bar2')


class TestTackerObjectSerializer(tests_base.BaseTestCase):

    def test_serialize_entity(self):
        serializer = base.TackerObjectSerializer()
        o = MyObj.from_dict({'id': 'foo',
                             'data': 'abcde',
                             'listData': [
                                 {'id': 'foo1', 'data': 'bar1'},
                                 {'id': 'foo2', 'data': 'bar2'},
                             ],
                             'createdAt': '2021-09-01T12:34:56+09:00'})
        entity = serializer.serialize_entity(mock.Mock(), o)
        self.assertEqual(entity['tacker_sol_refactored_object.name'], 'MyObj')
        self.assertEqual(entity['tacker_sol_refactored_object.namespace'],
            'tacker_sol_refactored')
        data = entity['tacker_sol_refactored_object.data']
        self.assertEqual(set(data.keys()),
                         set(['id', 'data', 'listData', 'createdAt']))

        o2 = serializer.deserialize_entity(mock.Mock(), entity)
        self.assertEqual(o2.listData[1].id, o.listData[1].id)
        self.assertEqual(o2.createdAt, o.createdAt)


class TestTackerPersistentObject(tests_base.BaseTestCase):

    def test_from_db_obj(self):
        o = MyDBObj.from_db_obj(
            {'id': 'foo', 'data': 'abcde',
             'listData': '[{"id": "foo1", "data": "bar1"},'
             '{"id": "foo2", "data": "bar2"}]',
             'createdAt': datetime.datetime(2021, 9, 1, 12, 34, 56)})
        self.assertEqual(o.id, 'foo')
        self.assertEqual(len(o.listData), 2)
        self.assertEqual(o.listData[0].data, 'bar1')

    def test_to_db_obj(self):
        o = MyDBObj.from_dict({'id': 'foo',
                               'data': 'abcde',
                               'listData': [
                                   {'id': 'foo1', 'data': 'bar1'},
                                   {'id': 'foo2', 'data': 'bar2'},
                               ],
                               'createdAt': '2021-09-01T12:34:56'})
        dbobj = o.to_db_obj()
        self.assertEqual(jsonutils.loads(dbobj['listData']),
            [{"id": "foo1", "data": "bar1"}, {"id": "foo2", "data": "bar2"}])
