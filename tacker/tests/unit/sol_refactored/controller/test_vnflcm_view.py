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

from unittest import mock

from dateutil import parser

from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.controller import vnflcm_view
from tacker.tests import base


class FakeField(object):

    def __init__(self, nullable):
        self.nullable = nullable


class TestFilterExpr(base.BaseTestCase):

    def test_match_datetime(self):
        fexp = vnflcm_view.FilterExpr('lte',
            ['fooTime'], ['2021-08-24T02:26:46.796695+00:00'])
        val = {'fooTime': parser.isoparse("2021-08-11T08:09:10+00:00")}
        self.assertTrue(fexp.match(val))

        val2 = {'fooTime': parser.isoparse("2021-09-01T08:09:10+00:00")}
        self.assertFalse(fexp.match(val2))

    def test_match_int(self):
        fexp = vnflcm_view.FilterExpr('in',
            ['fooNum'], ['11', '13', '17', '19', '23'])
        self.assertTrue(fexp.match(dict(fooNum=11)))
        self.assertFalse(fexp.match(dict(fooNum=15)))

    def test_match_bool(self):
        fexp = vnflcm_view.FilterExpr('eq',
            ['foo', 'bar'], ['false'])
        self.assertFalse(fexp.match({'foo': {'bar': True}}))

        fexp2 = vnflcm_view.FilterExpr('eq',
            ['foo', 'bar'], ['true'])
        self.assertTrue(fexp2.match({'foo': {'bar': True}}))

        fexp3 = vnflcm_view.FilterExpr('eq',
            ['foo', 'bar'], ['invalid'])
        self.assertRaises(sol_ex.InvalidAttributeFilter,
                          fexp3.match,
                          {'foo': {'bar': True}})

    def test_match_key(self):
        fexp = vnflcm_view.FilterExpr('eq',
            ['foo', vnflcm_view.KeyAttribute()], ['abc'])
        self.assertFalse(fexp.match({'foo': {'bar': True}}))
        self.assertTrue(fexp.match({'foo': {'abc': False}}))

    def test_match_invalid(self):
        fexp = vnflcm_view.FilterExpr('eq',
            ['foo', 'bar', vnflcm_view.KeyAttribute()], ['abc'])
        self.assertRaises(sol_ex.InvalidAttributeFilter,
                          fexp.match, {'foo': 1})
        self.assertRaises(sol_ex.InvalidAttributeFilter,
                          fexp.match, {'foo': [1, 2, 3]})


class TestAttributeSelector(base.BaseTestCase):

    def test_invalid_params(self):
        self.assertRaises(sol_ex.InvalidAttributeSelector,
                          vnflcm_view.AttributeSelector,
                          [], all_fields='1', exclude_default='1')

        self.assertRaises(sol_ex.InvalidAttributeSelector,
                          vnflcm_view.AttributeSelector,
                          [], fields='a', exclude_fields='b')

        self.assertRaises(sol_ex.InvalidAttributeSelector,
                          vnflcm_view.AttributeSelector,
                          [], exclude_default='1', exclude_fields='b')

    def test_filter_default(self):
        selector = vnflcm_view.AttributeSelector(
            ['foo', 'hoge/foo1', 'bar'])
        obj = mock.NonCallableMagicMock()
        obj.fields.__getitem__.return_value = FakeField(True)
        r = selector.filter(obj, {'foo': 1, 'bar': 2, 'baz': 3})
        self.assertEqual(r, {'baz': 3})
        obj.fields.__getitem__.assert_called_with('bar')

    def test_filter_exclude_default(self):
        selector = vnflcm_view.AttributeSelector(['foo', 'bar'],
                                                 exclude_default='1')
        obj = mock.NonCallableMagicMock()
        obj.fields.__getitem__.return_value = FakeField(True)
        r = selector.filter(obj, {'foo': 1, 'bar': 2, 'baz': 3})
        self.assertEqual(r, {'baz': 3})

    def test_filter_default_not_omittable(self):
        selector = vnflcm_view.AttributeSelector(['foo', 'bar'])
        obj = mock.NonCallableMagicMock()
        obj.fields.__getitem__.return_value = FakeField(False)
        r = selector.filter(obj, {'foo': 1, 'bar': 2})
        self.assertEqual(r, {'foo': 1, 'bar': 2})

    def test_filter_all_fields(self):
        selector = vnflcm_view.AttributeSelector(['foo', 'bar'])
        obj = mock.NonCallableMagicMock()
        obj.fields.__getitem__.return_value = FakeField(True)
        odict = {'foo': 1, 'bar': 2, 'baz': 3}
        r = selector.filter(obj, odict)
        self.assertEqual(r, odict)

    def test_filter_exclude_fields(self):
        selector = vnflcm_view.AttributeSelector(['foo', 'bar'],
                                                 exclude_fields='bar,baz')
        obj = mock.NonCallableMagicMock()
        obj.fields.__getitem__.return_value = FakeField(True)
        r = selector.filter(obj, {'foo': 1, 'bar': 2, 'baz': 3})
        self.assertEqual(r, {'foo': 1})

    def test_filter_fields(self):
        selector = vnflcm_view.AttributeSelector(['foo', 'bar'],
                                                 exclude_default='1',
                                                 fields='bar')
        obj = mock.NonCallableMagicMock()
        obj.fields.__getitem__.return_value = FakeField(True)
        r = selector.filter(obj, {'foo': 1, 'bar': 2, 'baz': 3})
        self.assertEqual(r, {'bar': 2, 'baz': 3})


class TestBaseViewBuilder(base.BaseTestCase):

    def test_parse_filter(self):
        builder = vnflcm_view.BaseViewBuilder()
        f1 = builder.parse_filter("(eq,foo/bar,abc)")
        self.assertEqual(len(f1), 1)
        self.assertEqual(f1[0].attr, ['foo', 'bar'])

        f2 = builder.parse_filter("(eq,foo/bar,')1');(neq,baz,'''a')")
        self.assertEqual(len(f2), 2)
        self.assertEqual(f2[0].attr, ['foo', 'bar'])
        self.assertEqual(f2[0].values, [')1'])
        self.assertEqual(f2[1].attr, ['baz'])
        self.assertEqual(f2[1].values, ["'a"])

        f3 = builder.parse_filter("(eq,~01/c~1~a/~be,10)")
        self.assertEqual(len(f3), 1)
        self.assertEqual(f3[0].attr, ['~1', 'c/,', '@e'])

        f4 = builder.parse_filter("(in,foo,'a','bc');(cont,bar,'def','ghi')")
        self.assertEqual(len(f4), 2)
        self.assertEqual(len(f4[0].values), 2)
        self.assertEqual(len(f4[1].values), 2)

        f5 = builder.parse_filter("(eq,foo/@key,'abc')")
        self.assertEqual(len(f5), 1)
        self.assertEqual(len(f5[0].attr), 2)
        self.assertEqual(f5[0].attr[0], 'foo')
        self.assertIsInstance(f5[0].attr[1], vnflcm_view.KeyAttribute)
        self.assertEqual(len(f5[0].values), 1)

    def test_parse_filter_invalid(self):
        builder = vnflcm_view.BaseViewBuilder()
        self.assertRaises(sol_ex.InvalidAttributeFilter,
                          builder.parse_filter,
                          "(le,foo/bar,abc)")

        self.assertRaises(sol_ex.InvalidAttributeFilter,
                          builder.parse_filter,
                          "(gt,foo/bar)")

        self.assertRaises(sol_ex.InvalidAttributeFilter,
                          builder.parse_filter,
                          "(gt,foo,1,2)")
