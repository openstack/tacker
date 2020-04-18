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
from unittest import mock

import ddt
from oslo_serialization import jsonutils
from six.moves import http_client
from webob import exc

from tacker.api.vnflcm.v1 import controller
from tacker.common import exceptions
from tacker.conductor.conductorrpc.vnf_lcm_rpc import VNFLcmRPCAPI
from tacker.extensions import nfvo
from tacker import objects
from tacker.objects import fields
from tacker.tests import constants
from tacker.tests.unit import base
from tacker.tests.unit import fake_request
from tacker.tests.unit.vnflcm import fakes
from tacker.tests import uuidsentinel
from tacker.vnfm import vim_client


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
                 format(value=value, attribute=attribute))
        elif expected_type in ["name_allow_zero_min_length", "description"]:
            expected_message = ("Invalid input for field/attribute "
                                "{attribute}. " "Value: {value}. {value} is "
                                "not of type 'string'".
                 format(value=value, attribute=attribute))

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

    @mock.patch.object(vim_client.VimClient, "get_vim")
    @mock.patch.object(objects.vnf_instance, "_vnf_instance_get_by_id")
    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch.object(objects.VnfPackageVnfd, 'get_by_id')
    @mock.patch.object(objects.VnfPackage, "get_by_id")
    @mock.patch.object(VNFLcmRPCAPI, "instantiate")
    def test_instantiate_with_deployment_flavour(
            self, mock_instantiate, mock_vnf_package_get_by_id,
            mock_vnf_package_vnfd_get_by_id, mock_save,
            mock_vnf_instance_get_by_id, mock_get_vim):

        mock_vnf_instance_get_by_id.return_value =\
            fakes.return_vnf_instance_model()
        mock_vnf_package_vnfd_get_by_id.return_value = \
            fakes.return_vnf_package_vnfd()
        mock_vnf_package_get_by_id.return_value = \
            fakes.return_vnf_package_with_deployment_flavour()

        body = {"flavourId": "simple"}
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/instantiate' % uuidsentinel.vnf_instance_id)
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        # Call Instantiate API
        resp = req.get_response(self.app)
        self.assertEqual(http_client.ACCEPTED, resp.status_code)
        mock_instantiate.assert_called_once()

    @mock.patch.object(objects.vnf_instance, "_vnf_instance_get_by_id")
    @mock.patch.object(objects.VnfPackageVnfd, 'get_by_id')
    @mock.patch.object(objects.VnfPackage, "get_by_id")
    def test_instantiate_with_non_existing_deployment_flavour(
            self, mock_vnf_package_get_by_id, mock_vnf_package_vnfd_get_by_id,
            mock_vnf_instance_get_by_id):

        mock_vnf_instance_get_by_id.return_value =\
            fakes.return_vnf_instance_model()
        mock_vnf_package_vnfd_get_by_id.return_value = \
            fakes.return_vnf_package_vnfd()
        mock_vnf_package_get_by_id.return_value = \
            fakes.return_vnf_package_with_deployment_flavour()

        body = {"flavourId": "invalid"}
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/instantiate' % uuidsentinel.vnf_instance_id)
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        # Call Instantiate API
        resp = req.get_response(self.app)
        self.assertEqual(http_client.BAD_REQUEST, resp.status_code)
        self.assertEqual("No flavour with id 'invalid'.",
            resp.json['badRequest']['message'])

    @mock.patch.object(vim_client.VimClient, "get_vim")
    @mock.patch.object(objects.vnf_instance, "_vnf_instance_get_by_id")
    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch.object(objects.VnfPackageVnfd, 'get_by_id')
    @mock.patch.object(objects.VnfPackage, "get_by_id")
    @mock.patch.object(VNFLcmRPCAPI, "instantiate")
    def test_instantiate_with_instantiation_level(
            self, mock_instantiate, mock_vnf_package_get_by_id,
            mock_vnf_package_vnfd_get_by_id, mock_save,
            mock_vnf_instance_get_by_id, mock_get_vim):

        mock_vnf_instance_get_by_id.return_value =\
            fakes.return_vnf_instance_model()
        mock_vnf_package_vnfd_get_by_id.return_value = \
            fakes.return_vnf_package_vnfd()
        mock_vnf_package_get_by_id.return_value = \
            fakes.return_vnf_package_with_deployment_flavour()

        body = {"flavourId": "simple",
                "instantiationLevelId": "instantiation_level_1"}
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/instantiate' % uuidsentinel.vnf_instance_id)
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        # Call Instantiate API
        resp = req.get_response(self.app)
        self.assertEqual(http_client.ACCEPTED, resp.status_code)
        mock_instantiate.assert_called_once()

    @mock.patch.object(vim_client.VimClient, "get_vim")
    @mock.patch.object(objects.vnf_instance, "_vnf_instance_get_by_id")
    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch.object(objects.VnfPackageVnfd, 'get_by_id')
    @mock.patch.object(objects.VnfPackage, "get_by_id")
    @mock.patch.object(VNFLcmRPCAPI, "instantiate")
    def test_instantiate_with_no_inst_level_in_flavour(
            self, mock_instantiate, mock_vnf_package_get_by_id,
            mock_vnf_package_vnfd_get_by_id, mock_save,
            mock_vnf_instance_get_by_id, mock_get_vim):

        mock_vnf_instance_get_by_id.return_value =\
            fakes.return_vnf_instance_model()
        mock_vnf_package_vnfd_get_by_id.return_value = \
            fakes.return_vnf_package_vnfd()
        vnf_package = fakes.return_vnf_package_with_deployment_flavour()
        vnf_package.vnf_deployment_flavours[0].instantiation_levels = None
        mock_vnf_package_get_by_id.return_value = vnf_package

        # No instantiation level in deployment flavour but it's passed in the
        # request
        body = {"flavourId": "simple",
                "instantiationLevelId": "instantiation_level_1"}
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/instantiate' % uuidsentinel.vnf_instance_id)
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        # Call Instantiate API
        resp = req.get_response(self.app)
        self.assertEqual(http_client.BAD_REQUEST, resp.status_code)
        self.assertEqual("No instantiation level with id "
            "'instantiation_level_1'.", resp.json['badRequest']['message'])

    @mock.patch.object(objects.vnf_instance, "_vnf_instance_get_by_id")
    @mock.patch.object(objects.VnfPackageVnfd, 'get_by_id')
    @mock.patch.object(objects.VnfPackage, "get_by_id")
    @mock.patch.object(VNFLcmRPCAPI, "instantiate")
    def test_instantiate_with_non_existing_instantiation_level(
            self, mock_instantiate, mock_vnf_package_get_by_id,
            mock_vnf_package_vnfd_get_by_id,
            mock_vnf_instance_get_by_id):

        mock_vnf_instance_get_by_id.return_value =\
            fakes.return_vnf_instance_model()
        mock_vnf_package_vnfd_get_by_id.return_value = \
            fakes.return_vnf_package_vnfd()
        mock_vnf_package_get_by_id.return_value = \
            fakes.return_vnf_package_with_deployment_flavour()

        body = {"flavourId": "simple",
                "instantiationLevelId": "non-existing"}
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/instantiate' % uuidsentinel.vnf_instance_id)
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        # Call Instantiate API
        resp = req.get_response(self.app)
        self.assertEqual(http_client.BAD_REQUEST, resp.status_code)
        self.assertEqual("No instantiation level with id 'non-existing'.",
            resp.json['badRequest']['message'])

    @mock.patch.object(vim_client.VimClient, "get_vim")
    @mock.patch.object(objects.vnf_instance, "_vnf_instance_get_by_id")
    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch.object(objects.VnfPackageVnfd, 'get_by_id')
    @mock.patch.object(objects.VnfPackage, "get_by_id")
    @mock.patch.object(VNFLcmRPCAPI, "instantiate")
    def test_instantiate_with_vim_connection(
            self, mock_instantiate, mock_vnf_package_get_by_id,
            mock_vnf_package_vnfd_get_by_id, mock_save,
            mock_vnf_instance_get_by_id, mock_get_vim):

        mock_vnf_instance_get_by_id.return_value =\
            fakes.return_vnf_instance_model()
        mock_vnf_package_vnfd_get_by_id.return_value = \
            fakes.return_vnf_package_vnfd()
        mock_vnf_package_get_by_id.return_value = \
            fakes.return_vnf_package_with_deployment_flavour()

        body = {"flavourId": "simple",
                "vimConnectionInfo": [
                    {"id": uuidsentinel.vim_connection_id,
                     "vimId": uuidsentinel.vim_id,
                     "vimType": 'openstack'}
                ]}

        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/instantiate' % uuidsentinel.vnf_instance_id)
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        # Call Instantiate API
        resp = req.get_response(self.app)
        self.assertEqual(http_client.ACCEPTED, resp.status_code)
        mock_instantiate.assert_called_once()

    @mock.patch.object(vim_client.VimClient, "get_vim")
    @mock.patch.object(objects.vnf_instance, "_vnf_instance_get_by_id")
    @mock.patch.object(objects.VnfPackageVnfd, 'get_by_id')
    @mock.patch.object(objects.VnfPackage, "get_by_id")
    def test_instantiate_with_non_existing_vim(
            self, mock_vnf_package_get_by_id, mock_vnf_package_vnfd_get_by_id,
            mock_vnf_instance_get_by_id, mock_get_vim):

        mock_vnf_instance_get_by_id.return_value =\
            fakes.return_vnf_instance_model()
        mock_vnf_package_vnfd_get_by_id.return_value = \
            fakes.return_vnf_package_vnfd()
        mock_vnf_package_get_by_id.return_value = \
            fakes.return_vnf_package_with_deployment_flavour()
        mock_get_vim.side_effect = nfvo.VimNotFoundException

        body = {"flavourId": "simple",
                "vimConnectionInfo": [
                    {"id": uuidsentinel.vim_connection_id,
                     "vimId": uuidsentinel.vim_id,
                     "vimType": 'openstack'}
                ]}
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/instantiate' % uuidsentinel.vnf_instance_id)
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        # Call Instantiate API
        resp = req.get_response(self.app)
        self.assertEqual(http_client.BAD_REQUEST, resp.status_code)
        self.assertEqual("VimConnection id is not found: %s" %
                uuidsentinel.vim_id, resp.json['badRequest']['message'])

    @mock.patch.object(vim_client.VimClient, "get_vim")
    @mock.patch.object(objects.vnf_instance, "_vnf_instance_get_by_id")
    @mock.patch.object(objects.VnfPackageVnfd, 'get_by_id')
    @mock.patch.object(objects.VnfPackage, "get_by_id")
    def test_instantiate_with_non_existing_region_vim(
            self, mock_vnf_package_get_by_id, mock_vnf_package_vnfd_get_by_id,
            mock_vnf_instance_get_by_id, mock_get_vim):

        mock_vnf_instance_get_by_id.return_value =\
            fakes.return_vnf_instance_model()
        mock_vnf_package_vnfd_get_by_id.return_value = \
            fakes.return_vnf_package_vnfd()
        mock_vnf_package_get_by_id.return_value = \
            fakes.return_vnf_package_with_deployment_flavour()
        mock_get_vim.side_effect = nfvo.VimRegionNotFoundException

        body = {"flavourId": "simple",
                "vimConnectionInfo": [
                    {'id': uuidsentinel.vim_connection_id,
                     'vimId': uuidsentinel.vim_id,
                     'vimType': 'openstack',
                     'accessInfo': {"region": 'region_non_existing'}}
                ]}
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/instantiate' % uuidsentinel.vnf_instance_id)
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        # Call Instantiate API
        resp = req.get_response(self.app)
        self.assertEqual(http_client.BAD_REQUEST, resp.status_code)
        self.assertEqual("Region not found for the VimConnection: %s" %
                uuidsentinel.vim_id, resp.json['badRequest']['message'])

    @mock.patch.object(vim_client.VimClient, "get_vim")
    @mock.patch.object(objects.vnf_instance, "_vnf_instance_get_by_id")
    @mock.patch.object(objects.VnfPackageVnfd, 'get_by_id')
    @mock.patch.object(objects.VnfPackage, "get_by_id")
    def test_instantiate_with_default_vim_not_configured(
            self, mock_vnf_package_get_by_id, mock_vnf_package_vnfd_get_by_id,
            mock_vnf_instance_get_by_id, mock_get_vim):

        mock_vnf_instance_get_by_id.return_value =\
            fakes.return_vnf_instance_model()
        mock_vnf_package_vnfd_get_by_id.return_value = \
            fakes.return_vnf_package_vnfd()
        mock_vnf_package_get_by_id.return_value = \
            fakes.return_vnf_package_with_deployment_flavour()
        mock_get_vim.side_effect = nfvo.VimDefaultNotDefined

        body = {"flavourId": "simple"}
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/instantiate' % uuidsentinel.vnf_instance_id)
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        # Call Instantiate API
        resp = req.get_response(self.app)
        self.assertEqual(http_client.BAD_REQUEST, resp.status_code)
        self.assertEqual("Default VIM is not defined.",
            resp.json['badRequest']['message'])

    @mock.patch.object(objects.vnf_instance, "_vnf_instance_get_by_id")
    def test_instantiate_incorrect_instantiation_state(self, mock_vnf_by_id):
        vnf_instance = fakes.return_vnf_instance_model()
        vnf_instance.instantiation_state = 'INSTANTIATED'
        mock_vnf_by_id.return_value = vnf_instance

        body = {"flavourId": "simple"}
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/instantiate' % uuidsentinel.vnf_instance_id)
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        # Call Instantiate API
        resp = req.get_response(self.app)
        self.assertEqual(http_client.CONFLICT, resp.status_code)

    @mock.patch.object(objects.vnf_instance, "_vnf_instance_get_by_id")
    def test_instantiate_incorrect_task_state(self, mock_vnf_by_id):
        vnf_instance = fakes.return_vnf_instance_model(
            task_state=fields.VnfInstanceTaskState.INSTANTIATING)
        mock_vnf_by_id.return_value = vnf_instance

        body = {"flavourId": "simple"}
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/instantiate' % uuidsentinel.vnf_instance_id)
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        resp = req.get_response(self.app)

        self.assertEqual(http_client.CONFLICT, resp.status_code)
        expected_msg = ("Vnf instance %s in task_state INSTANTIATING. Cannot "
                        "instantiate while the vnf instance is in this state.")
        self.assertEqual(expected_msg % uuidsentinel.vnf_instance_id,
            resp.json['conflictingRequest']['message'])

    @ddt.data({'attribute': 'flavourId', 'value': 123,
               'expected_type': 'string'},
              {'attribute': 'flavourId', 'value': True,
               'expected_type': 'string'},
              {'attribute': 'instantiationLevelId', 'value': 123,
               'expected_type': 'string'},
              {'attribute': 'instantiationLevelId', 'value': True,
               'expected_type': 'string'},
              {'attribute': 'additionalParams', 'value': ['val1', 'val2'],
               'expected_type': 'object'},
              {'attribute': 'additionalParams', 'value': True,
               'expected_type': 'object'},
              {'attribute': 'additionalParams', 'value': 123,
               'expected_type': 'object'},
              )
    @ddt.unpack
    def test_instantiate_with_invalid_request_body(
            self, attribute, value, expected_type):
        body = fakes.get_vnf_instantiation_request_body()
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/instantiate' % uuidsentinel.vnf_instance_id)

        body.update({attribute: value})
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        exception = self.assertRaises(
            exceptions.ValidationError, self.controller.instantiate,
            req, body=body)
        expected_message = \
            ("Invalid input for field/attribute {attribute}. Value: {value}. "
             "{value} is not of type '{expected_type}'".
             format(value=value, attribute=attribute,
                    expected_type=expected_type))

        self.assertEqual(expected_message, exception.msg)

    def test_instantiate_without_flavour_id(self):
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/instantiate' % uuidsentinel.vnf_instance_id)
        req.body = jsonutils.dump_as_bytes({})
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        # Call Instantiate API
        resp = req.get_response(self.app)

        self.assertEqual(http_client.BAD_REQUEST, resp.status_code)
        self.assertEqual("'flavourId' is a required property",
            resp.json['badRequest']['message'])

    def test_instantiate_invalid_request_parameter(self):
        body = {"flavourId": "simple"}
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/instantiate' % uuidsentinel.vnf_instance_id)

        # Pass invalid request parameter
        body = {"flavourId": "simple"}
        body.update({'additional_property': 'test_value'})

        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        # Call Instantiate API
        resp = req.get_response(self.app)

        self.assertEqual(http_client.BAD_REQUEST, resp.status_code)
        self.assertEqual("Additional properties are not allowed "
                         "('additional_property' was unexpected)",
                         resp.json['badRequest']['message'])

    def test_instantiate_with_invalid_uuid(self):
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/instantiate' % constants.INVALID_UUID)
        body = {"flavourId": "simple"}
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        # Call Instantiate API
        resp = req.get_response(self.app)

        self.assertEqual(http_client.NOT_FOUND, resp.status_code)
        self.assertEqual(
            "Can not find requested vnf instance: %s" % constants.INVALID_UUID,
            resp.json['itemNotFound']['message'])

    @mock.patch.object(objects.VnfInstance, "get_by_id")
    def test_instantiate_with_non_existing_vnf_instance(
            self, mock_vnf_by_id):
        mock_vnf_by_id.side_effect = exceptions.VnfInstanceNotFound
        body = {"flavourId": "simple"}
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/instantiate' % uuidsentinel.vnf_instance_id)
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        # Call Instantiate API
        resp = req.get_response(self.app)

        self.assertEqual(http_client.NOT_FOUND, resp.status_code)
        self.assertEqual("Can not find requested vnf instance: %s" %
                         uuidsentinel.vnf_instance_id,
                         resp.json['itemNotFound']['message'])

    @ddt.data('HEAD', 'PUT', 'DELETE', 'PATCH', 'GET')
    def test_instantiate_invalid_http_method(self, method):
        # Wrong HTTP method
        body = fakes.get_vnf_instantiation_request_body()
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/29c770a3-02bc-4dfc-b4be-eb173ac00567/instantiate')
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = method
        resp = req.get_response(self.app)
        self.assertEqual(http_client.METHOD_NOT_ALLOWED, resp.status_code)

    @mock.patch.object(objects.vnf_instance, "_vnf_instance_get_by_id")
    def test_show_vnf_not_instantiated(self, mock_vnf_by_id):
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s' % uuidsentinel.instance_id)
        mock_vnf_by_id.return_value = fakes.return_vnf_instance_model()
        expected_result = fakes.fake_vnf_instance_response()
        res_dict = self.controller.show(req, uuidsentinel.instance_id)
        self.assertEqual(expected_result, res_dict)

    @mock.patch.object(objects.VnfInstance, "get_by_id")
    def test_show_vnf_instantiated(self, mock_vnf_by_id):
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s' % uuidsentinel.instance_id)
        mock_vnf_by_id.return_value = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED)
        expected_result = fakes.fake_vnf_instance_response(
            fields.VnfInstanceState.INSTANTIATED)
        res_dict = self.controller.show(req, uuidsentinel.instance_id)
        self.assertEqual(expected_result, res_dict)

    @mock.patch.object(objects.vnf_instance, "_vnf_instance_get_by_id")
    def test_show_with_non_existing_vnf_instance(self, mock_vnf_by_id):
        mock_vnf_by_id.side_effect = exceptions.VnfInstanceNotFound
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s' % uuidsentinel.vnf_instance_id)

        resp = req.get_response(self.app)

        self.assertEqual(http_client.NOT_FOUND, resp.status_code)
        self.assertEqual("Can not find requested vnf instance: %s" %
            uuidsentinel.vnf_instance_id,
            resp.json['itemNotFound']['message'])

    def test_show_with_invalid_uuid(self):
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s' % constants.INVALID_UUID)

        resp = req.get_response(self.app)
        self.assertEqual(http_client.NOT_FOUND, resp.status_code)
        self.assertEqual("Can not find requested vnf instance: %s" %
            constants.INVALID_UUID, resp.json['itemNotFound']['message'])

    @ddt.data('PATCH', 'HEAD', 'PUT', 'POST')
    def test_show_invalid_http_method(self, http_method):
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s' % constants.UUID)
        req.headers['Content-Type'] = 'application/json'
        req.method = http_method

        resp = req.get_response(self.app)
        self.assertEqual(http_client.METHOD_NOT_ALLOWED, resp.status_code)

    @mock.patch.object(objects.VnfInstance, "get_by_id")
    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch.object(VNFLcmRPCAPI, "terminate")
    @ddt.data({'terminationType': 'FORCEFUL'},
              {'terminationType': 'GRACEFUL'},
              {'terminationType': 'GRACEFUL',
               'gracefulTerminationTimeout': 10})
    def test_terminate(self, body, mock_terminate, mock_save, mock_get_by_id):
        vnf_instance_obj = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED)
        mock_get_by_id.return_value = vnf_instance_obj

        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/terminate' % uuidsentinel.vnf_instance_id)
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        resp = req.get_response(self.app)
        self.assertEqual(http_client.ACCEPTED, resp.status_code)
        mock_terminate.assert_called_once()

    @ddt.data(
        {'attribute': 'terminationType', 'value': "TEST",
         'expected_type': 'enum'},
        {'attribute': 'terminationType', 'value': 123,
         'expected_type': 'enum'},
        {'attribute': 'terminationType', 'value': True,
         'expected_type': 'enum'},
        {'attribute': 'gracefulTerminationTimeout', 'value': True,
         'expected_type': 'integer'},
        {'attribute': 'gracefulTerminationTimeout', 'value': "test",
         'expected_type': 'integer'}
    )
    @ddt.unpack
    def test_terminate_with_invalid_request_body(
            self, attribute, value, expected_type):
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/terminate' % uuidsentinel.vnf_instance_id)
        body = {'terminationType': 'GRACEFUL',
                'gracefulTerminationTimeout': 10}
        body.update({attribute: value})
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        expected_message = ("Invalid input for field/attribute {attribute}. "
             "Value: {value}.".format(value=value, attribute=attribute))

        exception = self.assertRaises(exceptions.ValidationError,
                                      self.controller.terminate,
                                      req, constants.UUID, body=body)
        self.assertIn(expected_message, exception.msg)

    def test_terminate_missing_termination_type(self):
        body = {'gracefulTerminationTimeout': 10}
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/terminate' % uuidsentinel.vnf_instance_id)
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        # Call terminate API
        resp = req.get_response(self.app)
        self.assertEqual(http_client.BAD_REQUEST, resp.status_code)
        self.assertEqual("'terminationType' is a required property",
            resp.json['badRequest']['message'])

    @ddt.data('GET', 'HEAD', 'PUT', 'DELETE', 'PATCH')
    def test_terminate_invalid_http_method(self, method):
        # Wrong HTTP method
        body = {'terminationType': 'GRACEFUL',
                'gracefulTerminationTimeout': 10}
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/terminate' % uuidsentinel.vnf_instance_id)
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = method
        resp = req.get_response(self.app)
        self.assertEqual(http_client.METHOD_NOT_ALLOWED, resp.status_code)

    @mock.patch.object(objects.vnf_instance, "_vnf_instance_get_by_id")
    def test_terminate_non_existing_vnf_instance(self, mock_vnf_by_id):
        body = {'terminationType': 'GRACEFUL',
                'gracefulTerminationTimeout': 10}
        mock_vnf_by_id.side_effect = exceptions.VnfInstanceNotFound
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/terminate' % uuidsentinel.vnf_instance_id)
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        resp = req.get_response(self.app)

        self.assertEqual(http_client.NOT_FOUND, resp.status_code)
        self.assertEqual("Can not find requested vnf instance: %s" %
            uuidsentinel.vnf_instance_id,
            resp.json['itemNotFound']['message'])

    @mock.patch.object(objects.vnf_instance, "_vnf_instance_get_by_id")
    def test_terminate_incorrect_instantiation_state(self, mock_vnf_by_id):
        mock_vnf_by_id.return_value = fakes.return_vnf_instance()
        body = {"terminationType": "FORCEFUL"}
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/terminate' % uuidsentinel.vnf_instance_id)
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        resp = req.get_response(self.app)

        self.assertEqual(http_client.CONFLICT, resp.status_code)
        expected_msg = ("Vnf instance %s in instantiation_state "
                        "NOT_INSTANTIATED. Cannot terminate while the vnf "
                        "instance is in this state.")
        self.assertEqual(expected_msg % uuidsentinel.vnf_instance_id,
            resp.json['conflictingRequest']['message'])

    @mock.patch.object(objects.VnfInstance, "get_by_id")
    def test_terminate_incorrect_task_state(self, mock_vnf_by_id):
        vnf_instance = fakes.return_vnf_instance(
            instantiated_state=fields.VnfInstanceState.INSTANTIATED,
            task_state=fields.VnfInstanceTaskState.TERMINATING)
        mock_vnf_by_id.return_value = vnf_instance

        body = {"terminationType": "FORCEFUL"}
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/terminate' % uuidsentinel.vnf_instance_id)
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        resp = req.get_response(self.app)

        self.assertEqual(http_client.CONFLICT, resp.status_code)
        expected_msg = ("Vnf instance %s in task_state TERMINATING. Cannot "
                        "terminate while the vnf instance is in this state.")
        self.assertEqual(expected_msg % uuidsentinel.vnf_instance_id,
            resp.json['conflictingRequest']['message'])

    @mock.patch.object(objects.VnfInstance, "get_by_id")
    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch.object(VNFLcmRPCAPI, "heal")
    @ddt.data({'cause': 'healing'}, {})
    def test_heal(self, body, mock_rpc_heal, mock_save,
            mock_vnf_by_id):
        vnf_instance_obj = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED)
        mock_vnf_by_id.return_value = vnf_instance_obj

        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/heal' % uuidsentinel.vnf_instance_id)
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        resp = req.get_response(self.app)

        self.assertEqual(http_client.ACCEPTED, resp.status_code)
        mock_rpc_heal.assert_called_once()

    def test_heal_cause_max_length_exceeded(self):
        body = {'cause': 'A' * 256}
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/heal' % uuidsentinel.vnf_instance_id)
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        resp = req.get_response(self.app)
        self.assertEqual(http_client.BAD_REQUEST, resp.status_code)

    @mock.patch.object(objects.VnfInstance, "get_by_id")
    def test_heal_incorrect_instantiated_state(self, mock_vnf_by_id):
        vnf_instance_obj = fakes.return_vnf_instance(
            fields.VnfInstanceState.NOT_INSTANTIATED)
        mock_vnf_by_id.return_value = vnf_instance_obj

        body = {}
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/heal' % uuidsentinel.vnf_instance_id)
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        resp = req.get_response(self.app)
        self.assertEqual(http_client.CONFLICT, resp.status_code)
        expected_msg = ("Vnf instance %s in instantiation_state "
                       "NOT_INSTANTIATED. Cannot heal while the vnf instance "
                       "is in this state.")
        self.assertEqual(expected_msg % uuidsentinel.vnf_instance_id,
                resp.json['conflictingRequest']['message'])

    @mock.patch.object(objects.VnfInstance, "get_by_id")
    def test_heal_incorrect_task_state(self, mock_vnf_by_id):
        vnf_instance_obj = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED,
            task_state=fields.VnfInstanceTaskState.HEALING)
        mock_vnf_by_id.return_value = vnf_instance_obj

        body = {}
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/heal' % uuidsentinel.vnf_instance_id)
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        resp = req.get_response(self.app)
        self.assertEqual(http_client.CONFLICT, resp.status_code)
        expected_msg = ("Vnf instance %s in task_state "
                       "HEALING. Cannot heal while the vnf instance "
                       "is in this state.")
        self.assertEqual(expected_msg % uuidsentinel.vnf_instance_id,
                resp.json['conflictingRequest']['message'])

    @mock.patch.object(objects.VnfInstance, "get_by_id")
    def test_heal_with_invalid_vnfc_id(self, mock_vnf_by_id):
        vnf_instance_obj = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED)
        mock_vnf_by_id.return_value = vnf_instance_obj

        body = {'vnfcInstanceId': [uuidsentinel.vnfc_instance_id]}
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/heal' % uuidsentinel.vnf_instance_id)
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        resp = req.get_response(self.app)
        self.assertEqual(http_client.BAD_REQUEST, resp.status_code)
        expected_msg = "Vnfc id %s not present in vnf instance %s"
        self.assertEqual(expected_msg % (uuidsentinel.vnfc_instance_id,
            uuidsentinel.vnf_instance_id), resp.json['badRequest']['message'])

    @ddt.data('HEAD', 'PUT', 'DELETE', 'PATCH', 'GET')
    def test_heal_invalid_http_method(self, method):
        body = {}
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/heal' % uuidsentinel.vnf_instance_id)
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = method

        resp = req.get_response(self.app)

        self.assertEqual(http_client.METHOD_NOT_ALLOWED, resp.status_code)

    @ddt.data({'attribute': 'cause', 'value': 123,
               'expected_type': 'string'},
              {'attribute': 'cause', 'value': True,
               'expected_type': 'string'},
              {'attribute': 'vnfcInstanceId', 'value': 123,
               'expected_type': 'array'},
              {'attribute': 'vnfcInstanceId', 'value': True,
               'expected_type': 'array'},
              )
    @ddt.unpack
    def test_heal_with_invalid_request_body(
            self, attribute, value, expected_type):
        body = {}
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/29c770a3-02bc-4dfc-b4be-eb173ac00567/heal')
        body.update({attribute: value})
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'
        exception = self.assertRaises(
            exceptions.ValidationError, self.controller.heal,
            req, body=body)
        expected_message = \
            ("Invalid input for field/attribute {attribute}. Value: {value}. "
             "{value} is not of type '{expected_type}'".
             format(value=value, attribute=attribute,
                    expected_type=expected_type))

        self.assertEqual(expected_message, exception.msg)

    @mock.patch.object(objects.VnfInstanceList, "get_all")
    def test_index(self, mock_vnf_list):
        req = fake_request.HTTPRequest.blank('/vnf_instances')
        vnf_instance_1 = fakes.return_vnf_instance()
        vnf_instance_2 = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED)

        mock_vnf_list.return_value = [vnf_instance_1, vnf_instance_2]
        resp = self.controller.index(req)
        expected_result = [fakes.fake_vnf_instance_response(),
            fakes.fake_vnf_instance_response(
            fields.VnfInstanceState.INSTANTIATED)]
        self.assertEqual(expected_result, resp)

    @mock.patch.object(objects.VnfInstanceList, "get_all")
    def test_index_empty_response(self, mock_vnf_list):
        req = fake_request.HTTPRequest.blank('/vnf_instances')

        mock_vnf_list.return_value = []
        resp = self.controller.index(req)
        self.assertEqual([], resp)

    @ddt.data('HEAD', 'PUT', 'DELETE', 'PATCH')
    def test_index_invalid_http_method(self, method):
        # Wrong HTTP method
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances')
        req.headers['Content-Type'] = 'application/json'
        req.method = method
        resp = req.get_response(self.app)
        self.assertEqual(http_client.METHOD_NOT_ALLOWED, resp.status_code)

    @mock.patch.object(objects.vnf_instance, "_vnf_instance_get_by_id")
    @mock.patch.object(objects.vnf_instance, '_destroy_vnf_instance')
    def test_delete(self, mock_destroy_vnf_instance, mock_vnf_by_id):
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s' % uuidsentinel.vnf_instance_id)
        req.method = 'DELETE'
        mock_vnf_by_id.return_value = fakes.return_vnf_instance()
        req.headers['Content-Type'] = 'application/json'

        # Call delete API
        resp = req.get_response(self.app)

        self.assertEqual(http_client.NO_CONTENT, resp.status_code)
        mock_destroy_vnf_instance.assert_called_once()

    @mock.patch.object(objects.VnfInstance, "get_by_id")
    def test_delete_with_non_existing_vnf_instance(self, mock_vnf_by_id):
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s' % uuidsentinel.vnf_instance_id)
        req.method = 'DELETE'

        mock_vnf_by_id.side_effect = exceptions.VnfInstanceNotFound

        # Call delete API
        resp = req.get_response(self.app)

        self.assertEqual(http_client.NOT_FOUND, resp.status_code)
        self.assertEqual("Can not find requested vnf instance: %s" %
            uuidsentinel.vnf_instance_id,
            resp.json['itemNotFound']['message'])

    def test_delete_with_invalid_uuid(self):
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s' % constants.INVALID_UUID)
        req.method = 'DELETE'

        # Call delete API
        resp = req.get_response(self.app)

        self.assertEqual(http_client.NOT_FOUND, resp.status_code)
        self.assertEqual("Can not find requested vnf instance: %s" %
            constants.INVALID_UUID,
            resp.json['itemNotFound']['message'])

    @mock.patch.object(objects.VnfInstance, "get_by_id")
    def test_delete_with_incorrect_instantiation_state(self, mock_vnf_by_id):
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s' % uuidsentinel.vnf_instance_id)
        req.method = 'DELETE'

        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED)
        mock_vnf_by_id.return_value = vnf_instance

        # Call delete API
        resp = req.get_response(self.app)

        self.assertEqual(http_client.CONFLICT, resp.status_code)
        expected_msg = ("Vnf instance %s in instantiation_state "
                       "INSTANTIATED. Cannot delete while the vnf instance "
                       "is in this state.")
        self.assertEqual(expected_msg % uuidsentinel.vnf_instance_id,
                resp.json['conflictingRequest']['message'])

    @mock.patch.object(objects.VnfInstance, "get_by_id")
    def test_delete_with_incorrect_task_state(self, mock_vnf_by_id):
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s' % uuidsentinel.vnf_instance_id)
        req.method = 'DELETE'

        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.NOT_INSTANTIATED,
            task_state=fields.VnfInstanceTaskState.ERROR)
        mock_vnf_by_id.return_value = vnf_instance

        # Call delete API
        resp = req.get_response(self.app)

        self.assertEqual(http_client.CONFLICT, resp.status_code)
        expected_msg = ("Vnf instance %s in task_state ERROR. "
                       "Cannot delete while the vnf instance "
                       "is in this state.")
        self.assertEqual(expected_msg % uuidsentinel.vnf_instance_id,
                resp.json['conflictingRequest']['message'])
