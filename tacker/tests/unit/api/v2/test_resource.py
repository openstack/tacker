# Copyright (c) 2012 Intel Corporation.
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

import mock
import oslo_i18n
from webob import exc
import webtest

from tacker.api.v1 import resource as wsgi_resource
from tacker.common import exceptions as n_exc
from tacker import context
from tacker.tests import base
from tacker import wsgi


class RequestTestCase(base.BaseTestCase):
    def setUp(self):
        super(RequestTestCase, self).setUp()
        self.req = wsgi_resource.Request({'foo': 'bar'})

    def test_content_type_missing(self):
        request = wsgi.Request.blank('/tests/123', method='POST')
        request.body = b"<body />"
        self.assertIsNone(request.get_content_type())

    def test_content_type_with_charset(self):
        request = wsgi.Request.blank('/tests/123')
        request.headers["Content-Type"] = "application/json; charset=UTF-8"
        result = request.get_content_type()
        self.assertEqual("application/json", result)

    def test_content_type_from_accept(self):
        content_type = 'application/json'
        request = wsgi.Request.blank('/tests/123')
        request.headers["Accept"] = content_type
        result = request.best_match_content_type()
        self.assertEqual(result, content_type)

    def test_content_type_from_accept_best(self):
        request = wsgi.Request.blank('/tests/123')
        request.headers["Accept"] = "application/json"
        result = request.best_match_content_type()
        self.assertEqual("application/json", result)

        request = wsgi.Request.blank('/tests/123')
        request.headers["Accept"] = ("application/json; q=0.3, ")
        result = request.best_match_content_type()
        self.assertEqual("application/json", result)

    def test_content_type_from_query_extension(self):
        request = wsgi.Request.blank('/tests/123.json')
        result = request.best_match_content_type()
        self.assertEqual("application/json", result)

        request = wsgi.Request.blank('/tests/123.json')
        result = request.best_match_content_type()
        self.assertEqual("application/json", result)

        request = wsgi.Request.blank('/tests/123.invalid')
        result = request.best_match_content_type()
        self.assertEqual("application/json", result)

    def test_content_type_accept_and_query_extension(self):
        request = wsgi.Request.blank('/tests/123.json')
        request.headers["Accept"] = "application/json"
        result = request.best_match_content_type()
        self.assertEqual("application/json", result)

    def test_content_type_accept_default(self):
        request = wsgi.Request.blank('/tests/123.unsupported')
        request.headers["Accept"] = "application/unsupported1"
        result = request.best_match_content_type()
        self.assertEqual("application/json", result)

    def test_context_with_tacker_context(self):
        self.skip("Not ready yet")
        ctxt = context.Context('fake_user', 'fake_tenant')
        self.req.environ['tacker.context'] = ctxt
        self.assertEqual(ctxt, self.req.context)

    def test_context_without_tacker_context(self):
        self.assertTrue(self.req.context.is_admin)

    def test_best_match_language(self):
        # Test that we are actually invoking language negotiation by webop
        request = wsgi.Request.blank('/')
        oslo_i18n.get_available_languages = mock.MagicMock()
        oslo_i18n.get_available_languages.return_value = [
            'known-language', 'es', 'zh']
        request.headers['Accept-Language'] = 'known-language'
        language = request.best_match_language()
        self.assertEqual('known-language', language)

        # If the Accept-Leader is an unknown language, missing or empty,
        # the best match locale should be None
        request.headers['Accept-Language'] = 'unknown-language'
        language = request.best_match_language()
        self.assertIsNone(language)
        request.headers['Accept-Language'] = ''
        language = request.best_match_language()
        self.assertIsNone(language)
        request.headers.pop('Accept-Language')
        language = request.best_match_language()
        self.assertIsNone(language)


class ResourceTestCase(base.BaseTestCase):

    def test_unmapped_tacker_error_with_json(self):
        msg = u'\u7f51\u7edc'

        class TestException(n_exc.TackerException):
            message = msg
        expected_res = {'body': {
            'TackerError': {
                'type': 'TestException',
                'message': msg,
                'detail': ''}}}
        controller = mock.MagicMock()
        controller.test.side_effect = TestException()

        resource = webtest.TestApp(wsgi_resource.Resource(controller))

        environ = {'wsgiorg.routing_args': (None, {'action': 'test',
                                                   'format': 'json'})}
        res = resource.get('', extra_environ=environ, expect_errors=True)
        self.assertEqual(exc.HTTPInternalServerError.code, res.status_int)
        self.assertEqual(expected_res,
                         wsgi.JSONDeserializer().deserialize(res.body))

    @mock.patch('oslo_i18n.translate')
    def test_unmapped_tacker_error_localized(self, mock_translation):
        msg_translation = 'Translated error'
        mock_translation.return_value = msg_translation
        msg = _('Unmapped error')

        class TestException(n_exc.TackerException):
            message = msg

        controller = mock.MagicMock()
        controller.test.side_effect = TestException()
        resource = webtest.TestApp(wsgi_resource.Resource(controller))

        environ = {'wsgiorg.routing_args': (None, {'action': 'test',
                                                   'format': 'json'})}

        res = resource.get('', extra_environ=environ, expect_errors=True)
        self.assertEqual(exc.HTTPInternalServerError.code, res.status_int)
        self.assertIn(msg_translation,
                      str(wsgi.JSONDeserializer().deserialize(res.body)))

    def test_mapped_tacker_error_with_json(self):
        msg = u'\u7f51\u7edc'

        class TestException(n_exc.TackerException):
            message = msg
        expected_res = {'body': {
            'TackerError': {
                'type': 'TestException',
                'message': msg,
                'detail': ''}}}
        controller = mock.MagicMock()
        controller.test.side_effect = TestException()

        faults = {TestException: exc.HTTPGatewayTimeout}
        resource = webtest.TestApp(wsgi_resource.Resource(controller,
                                                          faults=faults))

        environ = {'wsgiorg.routing_args': (None, {'action': 'test',
                                                   'format': 'json'})}
        res = resource.get('', extra_environ=environ, expect_errors=True)
        self.assertEqual(exc.HTTPGatewayTimeout.code, res.status_int)
        self.assertEqual(expected_res,
                         wsgi.JSONDeserializer().deserialize(res.body))

    @mock.patch('oslo_i18n.translate')
    def test_mapped_tacker_error_localized(self, mock_translation):
        msg_translation = 'Translated error'
        mock_translation.return_value = msg_translation
        msg = _('Unmapped error')

        class TestException(n_exc.TackerException):
            message = msg

        controller = mock.MagicMock()
        controller.test.side_effect = TestException()
        faults = {TestException: exc.HTTPGatewayTimeout}
        resource = webtest.TestApp(wsgi_resource.Resource(controller,
                                                          faults=faults))

        environ = {'wsgiorg.routing_args': (None, {'action': 'test',
                                                   'format': 'json'})}

        res = resource.get('', extra_environ=environ, expect_errors=True)
        self.assertEqual(exc.HTTPGatewayTimeout.code, res.status_int)
        self.assertIn(msg_translation,
                      str(wsgi.JSONDeserializer().deserialize(res.body)))

    @staticmethod
    def _make_request_with_side_effect(side_effect):
        controller = mock.MagicMock()
        controller.test.side_effect = side_effect

        resource = webtest.TestApp(wsgi_resource.Resource(controller))

        routing_args = {'action': 'test'}
        environ = {'wsgiorg.routing_args': (None, routing_args)}
        res = resource.get('', extra_environ=environ, expect_errors=True)
        return res

    def test_http_error(self):
        res = self._make_request_with_side_effect(exc.HTTPGatewayTimeout())
        # verify that the exception structure is the one expected
        # by the python-tackerclient
        self.assertEqual(exc.HTTPGatewayTimeout().explanation,
                         res.json['TackerError']['message'])
        self.assertEqual('HTTPGatewayTimeout',
                         res.json['TackerError']['type'])
        self.assertEqual('', res.json['TackerError']['detail'])
        self.assertEqual(exc.HTTPGatewayTimeout.code, res.status_int)

    def test_unhandled_error_with_json(self):
        expected_res = {'body': {'TackerError':
                                 {'detail': '',
                                  'message':
                                      _('Request Failed: internal server error'
                                        ' while processing your request.'),
                                  'type': 'HTTPInternalServerError'}}}
        controller = mock.MagicMock()
        controller.test.side_effect = Exception()

        resource = webtest.TestApp(wsgi_resource.Resource(controller))

        environ = {'wsgiorg.routing_args': (None, {'action': 'test',
                                                   'format': 'json'})}
        res = resource.get('', extra_environ=environ, expect_errors=True)
        self.assertEqual(exc.HTTPInternalServerError.code, res.status_int)
        self.assertEqual(expected_res,
                         wsgi.JSONDeserializer().deserialize(res.body))

    def test_status_200(self):
        controller = mock.MagicMock()
        controller.test = lambda request: {'foo': 'bar'}

        resource = webtest.TestApp(wsgi_resource.Resource(controller))

        environ = {'wsgiorg.routing_args': (None, {'action': 'test'})}
        res = resource.get('', extra_environ=environ)
        self.assertEqual(200, res.status_int)

    def test_status_204(self):
        controller = mock.MagicMock()
        controller.test = lambda request: {'foo': 'bar'}

        resource = webtest.TestApp(wsgi_resource.Resource(controller))

        environ = {'wsgiorg.routing_args': (None, {'action': 'delete'})}
        res = resource.delete('', extra_environ=environ)
        self.assertEqual(204, res.status_int)

    def _test_error_log_level(self, map_webob_exc, expect_log_info=False,
                              use_fault_map=True):
        class TestException(n_exc.TackerException):
            message = 'Test Exception'

        controller = mock.MagicMock()
        controller.test.side_effect = TestException()
        faults = {TestException: map_webob_exc} if use_fault_map else {}
        resource = webtest.TestApp(wsgi_resource.Resource(controller, faults))
        environ = {'wsgiorg.routing_args': (None, {'action': 'test'})}
        with mock.patch.object(wsgi_resource, 'LOG') as log:
            res = resource.get('', extra_environ=environ, expect_errors=True)
            self.assertEqual(map_webob_exc.code, res.status_int)
        self.assertEqual(expect_log_info, log.info.called)
        self.assertNotEqual(expect_log_info, log.exception.called)

    def test_4xx_error_logged_info_level(self):
        self._test_error_log_level(exc.HTTPNotFound, expect_log_info=True)

    def test_non_4xx_error_logged_exception_level(self):
        self._test_error_log_level(exc.HTTPServiceUnavailable,
                                   expect_log_info=False)

    def test_unmapped_error_logged_exception_level(self):
        self._test_error_log_level(exc.HTTPInternalServerError,
                                   expect_log_info=False, use_fault_map=False)

    def test_no_route_args(self):
        controller = mock.MagicMock()

        resource = webtest.TestApp(wsgi_resource.Resource(controller))

        environ = {}
        res = resource.get('', extra_environ=environ, expect_errors=True)
        self.assertEqual(exc.HTTPInternalServerError.code, res.status_int)

    def test_post_with_body(self):
        controller = mock.MagicMock()
        controller.test = lambda request, body: {'foo': 'bar'}

        resource = webtest.TestApp(wsgi_resource.Resource(controller))

        environ = {'wsgiorg.routing_args': (None, {'action': 'test'})}
        res = resource.post('', params='{"key": "val"}',
                            extra_environ=environ)
        self.assertEqual(200, res.status_int)
