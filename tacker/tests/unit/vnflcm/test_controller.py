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

import ddt
import mock
from oslo_serialization import jsonutils
from six.moves import http_client
from webob import exc

from tacker.api.vnflcm.v1 import controller
from tacker.common import exceptions
from tacker import objects
from tacker.tests.unit import base
from tacker.tests.unit import fake_request
from tacker.tests.unit.vnflcm import fakes
from tacker.tests import uuidsentinel


@ddt.ddt
class TestController(base.TestCase):

    def setUp(self):
        super(TestController, self).setUp()
        self.controller = controller.VnfLcmController()

    @property
    def app(self):
        return fakes.wsgi_app_v1()

    @mock.patch.object(objects.vnf_instance, '_vnf_instance_create')
    @mock.patch.object(objects.VnfPackageVnfd, 'get_by_id')
    def test_create_without_name_and_description(
            self, mock_get_by_id, mock_vnf_instance_create):
        mock_get_by_id.return_value = fakes.return_vnf_package_vnfd()

        updates = {'vnf_instance_description': None,
            'vnf_instance_name': None}
        mock_vnf_instance_create.return_value =\
            fakes.return_vnf_instance_model(**updates)

        req = fake_request.HTTPRequest.blank('/vnf_instances')
        body = {'vnfdId': uuidsentinel.vnfd_id}
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        # Call create API
        resp = req.get_response(self.app)

        self.assertEqual(http_client.CREATED, resp.status_code)

        updates = {'vnfInstanceDescription': None, 'vnfInstanceName': None}
        expected_vnf = fakes.fake_vnf_instance_response(**updates)
        location_header = ('http://localhost/vnflcm/v1/vnf_instances/%s'
            % resp.json['id'])

        self.assertEqual(expected_vnf, resp.json)
        self.assertEqual(location_header, resp.headers['location'])

    @mock.patch.object(objects.vnf_instance, '_vnf_instance_create')
    @mock.patch.object(objects.VnfPackageVnfd, 'get_by_id')
    def test_create_with_name_and_description(
            self, mock_get_by_id, mock_vnf_instance_create):
        mock_get_by_id.return_value = fakes.return_vnf_package_vnfd()
        updates = {'vnf_instance_description': 'SampleVnf Description',
                   'vnf_instance_name': 'SampleVnf'}
        mock_vnf_instance_create.return_value =\
            fakes.return_vnf_instance_model(**updates)

        body = {'vnfdId': uuidsentinel.vnfd_id,
                "vnfInstanceName": "SampleVnf",
                "vnfInstanceDescription": "SampleVnf Description"}
        req = fake_request.HTTPRequest.blank('/vnf_instances')
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        # Call Create API
        resp = req.get_response(self.app)

        self.assertEqual(http_client.CREATED, resp.status_code)
        updates = {"vnfInstanceName": "SampleVnf",
            "vnfInstanceDescription": "SampleVnf Description"}
        expected_vnf = fakes.fake_vnf_instance_response(**updates)
        location_header = ('http://localhost/vnflcm/v1/vnf_instances/%s'
            % resp.json['id'])

        self.assertEqual(expected_vnf, resp.json)
        self.assertEqual(location_header, resp.headers['location'])

    @ddt.data(
        {'attribute': 'vnfdId', 'value': True,
         'expected_type': 'uuid'},
        {'attribute': 'vnfdId', 'value': 123,
         'expected_type': 'uuid'},
        {'attribute': 'vnfInstanceName', 'value': True,
         'expected_type': "name_allow_zero_min_length"},
        {'attribute': 'vnfInstanceName', 'value': 123,
         'expected_type': "name_allow_zero_min_length"},
        {'attribute': 'vnfInstanceDescription', 'value': True,
         'expected_type': 'description'},
        {'attribute': 'vnfInstanceDescription', 'value': 123,
         'expected_type': 'description'},
    )
    @ddt.unpack
    def test_create_with_invalid_request_body(
            self, attribute, value, expected_type):
        """value of attribute in body is of invalid type"""
        body = {"vnfInstanceName": "SampleVnf",
                "vnfdId": "29c770a3-02bc-4dfc-b4be-eb173ac00567",
                "vnfInstanceDescription": "VNF Description"}
        req = fake_request.HTTPRequest.blank('/vnf_instances')
        body.update({attribute: value})
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'
        exception = self.assertRaises(
            exceptions.ValidationError, self.controller.create,
            req, body=body)
        if expected_type == 'uuid':
            expected_message = ("Invalid input for field/attribute "
                                "{attribute}. Value: {value}. {value} is not "
                                "of type 'string'".
                 format(value=value, attribute=attribute,
                        expected_type=expected_type))
        elif expected_type in ["name_allow_zero_min_length", "description"]:
            expected_message = ("Invalid input for field/attribute "
                                "{attribute}. " "Value: {value}. {value} is "
                                "not of type 'string'".
                 format(value=value, attribute=attribute,
                        expected_type=expected_type))

        self.assertEqual(expected_message, exception.msg)

    @mock.patch.object(objects.VnfPackageVnfd, 'get_by_id')
    def test_create_non_existing_vnf_package_vnfd(self, mock_vnf_by_id):
        mock_vnf_by_id.side_effect = exceptions.VnfPackageVnfdNotFound
        body = {'vnfdId': uuidsentinel.vnfd_id}
        req = fake_request.HTTPRequest.blank('/vnf_instances')
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'
        self.assertRaises(exc.HTTPBadRequest, self.controller.create, req,
                          body=body)

    def test_create_without_vnfd_id(self):
        body = {"vnfInstanceName": "SampleVnfInstance"}
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances')
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'
        resp = req.get_response(self.app)
        self.assertEqual(http_client.BAD_REQUEST, resp.status_code)

    @ddt.data('PATCH', 'PUT', 'HEAD', 'DELETE')
    def test_create_not_allowed_http_method(self, method):
        """Wrong HTTP method"""
        body = {"vnfdId": uuidsentinel.vnfd_id}
        req = fake_request.HTTPRequest.blank('/vnf_instances')
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = method
        resp = req.get_response(self.app)
        self.assertEqual(http_client.METHOD_NOT_ALLOWED, resp.status_code)

    @ddt.data({'name': "A" * 256, 'description': "VNF Description"},
              {'name': 'Fake-VNF', 'description': "A" * 1025})
    @ddt.unpack
    def test_create_max_length_exceeded_for_vnf_name_and_description(
            self, name, description):
        # vnf instance_name and description with length greater than max
        # length defined
        body = {"vnfInstanceName": name,
                "vnfdId": uuidsentinel.vnfd_id,
                "vnfInstanceDescription": description}
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances')
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'
        resp = req.get_response(self.app)
        self.assertEqual(http_client.BAD_REQUEST, resp.status_code)
