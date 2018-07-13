#    Copyright 2018 NTT DATA.
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

import six

from tacker.objects import base
from tacker.objects import fields
from tacker.tests.unit import base as test_base


class TestString(test_base.TestCase):
    def setUp(self):
        super(TestString, self).setUp()
        self.field = fields.StringField()
        self.coerce_good_values = [('foo', 'foo'), (1, '1'), (True, 'True')]
        if six.PY2:
            self.coerce_good_values.append((int(1), '1'))
        self.coerce_bad_values = [None]

    def test_stringify(self):
        self.assertEqual("'123'", self.field.stringify(123))


class TestListOfStrings(test_base.TestCase):
    def setUp(self):
        super(TestListOfStrings, self).setUp()
        self.field = fields.ListOfStringsField()

    def test_list_of_string(self):
        self.assertEqual("['abc']", self.field.stringify(['abc']))


class TestListOfObjects(test_base.TestCase):

    def test_list_of_obj(self):
        @base.TackerObjectRegistry.register_if(False)
        class MyObjElement(base.TackerObject):
            fields = {'foo': fields.StringField()}

            def __init__(self, foo):
                super(MyObjElement, self).__init__()
                self.foo = foo

        @base.TackerObjectRegistry.register_if(False)
        class MyList(base.TackerObject):
            fields = {'objects': fields.ListOfObjectsField('MyObjElement')}

        mylist = MyList()
        mylist.objects = [MyObjElement('a'), MyObjElement('b')]
        self.assertEqual(['a', 'b'], [x.foo for x in mylist.objects])
