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

from unittest import mock

from webob import exc
import webtest

from tacker._i18n import _
from tacker.api.v1 import resource as wsgi_resource
from tacker.common import exceptions as n_exc
from tacker import context
from tacker.tests import base
from tacker import wsgi


class RequestTestCase(base.BaseTestCase):
    def setUp(self):
        super(RequestTestCase, self).setUp()
        self.req = wsgi_resource.Request({'foo': 'bar'})

    def test_context_with_tacker_context(self):
        ctxt = context.Context('fake_user', 'fake_tenant')
        self.req.environ['tacker.context'] = ctxt
        self.assertEqual(ctxt, self.req.context)

    def test_context_without_tacker_context(self):
        self.assertTrue(self.req.context.is_admin)


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
