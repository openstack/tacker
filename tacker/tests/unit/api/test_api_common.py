# Copyright (c) 2013 Intel Corporation.
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

import netaddr

from testtools import matchers
from webob import exc

from oslo_policy import policy as oslo_policy
from oslo_serialization import jsonutils
from tacker.api import api_common as common
from tacker.api.v1 import resource as wsgi_resource
from tacker.common import exceptions
from tacker.tests import base


class FakeController(common.TackerController):
    _resource_name = 'fake'


class APICommonTestCase(base.BaseTestCase):
    def setUp(self):
        super(APICommonTestCase, self).setUp()
        self.controller = FakeController(None)

    def test_prepare_request_body(self):
        body = {
            'fake': {
                'name': 'terminator',
                'model': 'T-800',
            }
        }
        params = [
            {'param-name': 'name',
             'required': True},
            {'param-name': 'model',
             'required': True},
            {'param-name': 'quote',
             'required': False,
             'default-value': "i'll be back"},
        ]
        expect = {
            'fake': {
                'name': 'terminator',
                'model': 'T-800',
                'quote': "i'll be back",
            }
        }
        actual = self.controller._prepare_request_body(body, params)
        self.assertThat(expect, matchers.Equals(actual))

    def test_prepare_request_body_none(self):
        body = None
        params = [
            {'param-name': 'quote',
             'required': False,
             'default-value': "I'll be back"},
        ]
        expect = {
            'fake': {
                'quote': "I'll be back",
            }
        }
        actual = self.controller._prepare_request_body(body, params)
        self.assertThat(expect, matchers.Equals(actual))

    def test_prepare_request_body_keyerror(self):
        body = {'t2': {}}
        params = []
        self.assertRaises(exc.HTTPBadRequest,
                          self.controller._prepare_request_body,
                          body,
                          params)

    def test_prepare_request_param_value_none(self):
        body = {
            'fake': {
                'name': None,
            }
        }
        params = [
            {'param-name': 'name',
             'required': True},
        ]
        self.assertRaises(exc.HTTPBadRequest,
                          self.controller._prepare_request_body,
                          body,
                          params)

    def test_http_client_exception(self):
        req = wsgi_resource.Request({})
        language = req.best_match_language()
        e = exc.HTTPClientError()
        result = common.convert_exception_to_http_exc(e, {}, language)

        except_res = {'message': 'The server could not comply with'
                                 ' the request since it is either '
                                 'malformed or otherwise incorrect.',
                      'type': 'HTTPClientError',
                      'detail': ''}

        self.assertEqual(
            except_res, jsonutils.loads(result.body)["TackerError"])
        self.assertEqual(400, result.code)

    def test_http_exception(self):
        req = wsgi_resource.Request({})
        language = req.best_match_language()
        e = exc.HTTPException
        result = common.convert_exception_to_http_exc(e, {}, language)

        except_res = {"message": "Request Failed: internal server error "
                                 "while processing your request.",
                      "type": "HTTPInternalServerError",
                      "detail": ""}

        self.assertEqual(
            except_res, jsonutils.loads(result.body)["TackerError"])
        self.assertEqual(500, result.code)

    def test_tacker_exception(self):
        req = wsgi_resource.Request({})
        language = req.best_match_language()
        e = exceptions.TackerException()
        result = common.convert_exception_to_http_exc(e, {}, language)

        except_res = {'message': 'An unknown exception occurred.',
                      'type': 'TackerException',
                      'detail': ''}

        self.assertEqual(
            except_res, jsonutils.loads(result.body)["TackerError"])
        self.assertEqual(500, result.code)

    def test_addr_format_error_exception(self):
        req = wsgi_resource.Request({})
        language = req.best_match_language()
        e = netaddr.AddrFormatError()
        result = common.convert_exception_to_http_exc(e, {}, language)

        except_res = {'message': '',
                      'type': 'AddrFormatError',
                      'detail': ''}

        self.assertEqual(
            except_res, jsonutils.loads(result.body)["TackerError"])
        self.assertEqual(500, result.code)

    def test_policy_not_authorized_exception(self):
        req = wsgi_resource.Request({})
        language = req.best_match_language()
        e = oslo_policy.PolicyNotAuthorized(None, None, None)
        result = common.convert_exception_to_http_exc(e, {}, language)

        except_res = {'message': 'None is disallowed by policy',
                      'type': 'PolicyNotAuthorized',
                      'detail': ''}

        self.assertEqual(
            except_res, jsonutils.loads(result.body)["TackerError"])
        self.assertEqual(500, result.code)

    def test_not_implemented_error_exception(self):
        req = wsgi_resource.Request({})
        language = req.best_match_language()
        e = NotImplementedError()
        result = common.convert_exception_to_http_exc(e, {}, language)

        except_res = {'NotImplementedError': {'message': '',
                                              'type': 'NotImplementedError',
                                              'detail': ''}}

        self.assertEqual(except_res, jsonutils.loads(result.body))
        self.assertEqual(501, result.code)

    def test_get_exception_data(self):
        result = common.get_exception_data(exc.HTTPClientError)
        self.assertEqual("", result["detail"])
        self.assertEqual("type", result["type"])
        self.assertEqual(exc.HTTPClientError, result["message"])


class SortingEmulatedHelperTestcase(base.BaseTestCase):

    class request(object):
        class GET(object):
            @staticmethod
            def getall(cont):
                if cont == "sort_key":
                    return {"sort_key": "test"}
                return {'asc': "test"}

    def test_sort_emulate_class(self):
        sort = common.SortingEmulatedHelper(self.request, ["sort_key"])
        self.assertEqual([('sort_key', True)], list(sort.sort_dict))

    def test_update_fields(self):
        sort = common.SortingEmulatedHelper(self.request, ["sort_key"])
        original_fields = ["sort_dir"]
        fields_to_add = []
        sort.update_fields(original_fields, fields_to_add)
        self.assertEqual(["sort_dir", "sort_key"], original_fields)
        self.assertEqual(["sort_key"], fields_to_add)

    def test_sort(self):
        sort = common.SortingEmulatedHelper(self.request, ["sort_key"])
        items = [{"sort_key": 9}, {"sort_key": 6}, {"sort_key": 7}]
        expect_res = [{"sort_key": 6}, {"sort_key": 7}, {"sort_key": 9}]
        result = sort.sort(items)
        self.assertEqual(expect_res, result)

        items = [{"sort_key": 9, "sort_key_1": None},
                 {"sort_key": 6, "sort_key_2": {"sort_key_3": 8,
                                                "sort_key": 3}},
                 {"sort_key": 7}]
        expect_res = [{"sort_key": 6, "sort_key_2": {"sort_key": 3,
                                                     "sort_key_3": 8}},
                      {"sort_key": 7},
                      {"sort_key": 9, "sort_key_1": None}]
        result = sort.sort(items)
        self.assertEqual(expect_res, result)


class PaginationEmulatedHelperTestcase(base.BaseTestCase):

    class request(object):
        path_url = "http://127.0.0.1"

        class GET(object):

            @staticmethod
            def get(limit, reverse):
                if limit == "page_reverse":
                    return "True"
                return 5

            @staticmethod
            def copy():
                return {}

    class request_revs(object):
        path_url = "http://127.0.0.1"

        class GET(object):

            @staticmethod
            def get(limit, reverse):
                if limit == "page_reverse":
                    return "False"
                return 5

            @staticmethod
            def copy():
                return {}

    def test_pagination_emulate_class(self):
        page = common.PaginationEmulatedHelper(self.request)
        self.assertEqual(5, page.limit)
        self.assertEqual(True, page.page_reverse)
        self.assertEqual(5, page.marker)

    def test_update_fields(self):
        page = common.PaginationEmulatedHelper(self.request)
        original_fields = ["name"]
        fields_to_add = []
        page.update_fields(original_fields, fields_to_add)
        self.assertEqual(["name", "id"], original_fields)
        self.assertEqual(["id"], fields_to_add)

    def test_paginate(self):
        page = common.PaginationEmulatedHelper(self.request)
        items = [{"id": 6}, {"id": 4}, {"id": 2}]
        expect_res = [{"id": 6}, {"id": 4}]
        result = page.paginate(items)
        self.assertEqual(expect_res, result)

        items = [{"id": 6}, {"id": 4}, {"id": 2}, {"id": 7},
                 {"id": 3}, {"id": 8}, {"id": 5}]
        expect_res = [{"id": 4}, {"id": 2}, {"id": 7}, {"id": 3}, {"id": 8}]
        result = page.paginate(items)
        self.assertEqual(expect_res, result)

        items = [{"id": 6}, {"id": 4}, {"id": 5}, {"id": 7},
                 {"id": 3}, {"id": 8}, {"id": 2}]
        result = page.paginate(items)
        self.assertEqual([], result)

    def test_get_links(self):
        page = common.PaginationEmulatedHelper(self.request)
        items = [{"id": 6}, {"id": 4}, {"id": 2}]
        expect_res = [{'href': 'http://127.0.0.1?marker=2', 'rel': 'next'}]
        result = page.get_links(items)
        self.assertEqual(expect_res, result)

        page_previous = common.PaginationEmulatedHelper(self.request_revs)
        items = [{"id": 6}, {"id": 4}, {"id": 2}]
        expect_href = ('http://127.0.0.1?page_reverse=True&marker=6',
                       'http://127.0.0.1?marker=6&page_reverse=True')
        result = page_previous.get_links(items)

        self.assertEqual('previous', result[0]['rel'])
        self.assertEqual(True, result[0]['href'] in expect_href)
