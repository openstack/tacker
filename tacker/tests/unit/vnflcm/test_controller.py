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
import urllib
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
import tacker.tests.unit.nfvo.test_nfvo_plugin as nfvo_plugin
from tacker.tests.unit.vnflcm import fakes
from tacker.tests import uuidsentinel
from tacker.vnfm import vim_client


class FakeVNFMPlugin(mock.Mock):

    def __init__(self):
        super(FakeVNFMPlugin, self).__init__()
        self.vnf1_vnfd_id = 'eb094833-995e-49f0-a047-dfb56aaf7c4e'
        self.vnf1_vnf_id = '91e32c20-6d1f-47a4-9ba7-08f5e5effe07'
        self.vnf1_update_vnf_id = '91e32c20-6d1f-47a4-9ba7-08f5e5effaf6'
        self.vnf2_vnfd_id = 'e4015e9f-1ef2-49fb-adb6-070791ad3c45'
        self.vnf3_vnfd_id = 'e4015e9f-1ef2-49fb-adb6-070791ad3c45'
        self.vnf3_vnf_id = '7168062e-9fa1-4203-8cb7-f5c99ff3ee1b'
        self.vnf3_update_vnf_id = '10f66bc5-b2f1-45b7-a7cd-6dd6ad0017f5'

        self.cp11_id = 'd18c8bae-898a-4932-bff8-d5eac981a9c9'
        self.cp11_update_id = 'a18c8bae-898a-4932-bff8-d5eac981a9b8'
        self.cp12_id = 'c8906342-3e30-4b2a-9401-a251a7a9b5dd'
        self.cp12_update_id = 'b8906342-3e30-4b2a-9401-a251a7a9b5cc'
        self.cp32_id = '3d1bd2a2-bf0e-44d1-87af-a2c6b2cad3ed'
        self.cp32_update_id = '064c0d99-5a61-4711-9597-2a44dc5da14b'


@ddt.ddt
class TestController(base.TestCase):

    def setUp(self):
        super(TestController, self).setUp()
        self.patcher = mock.patch(
            'tacker.manager.TackerManager.get_service_plugins',
            return_value={'VNFM': nfvo_plugin.FakeVNFMPlugin()})
        self.mock_manager = self.patcher.start()
        self.controller = controller.VnfLcmController()

    def tearDown(self):
        self.mock_manager.stop()
        super(TestController, self).tearDown()

    @property
    def app(self):
        return fakes.wsgi_app_v1()

    @mock.patch.object(vim_client.VimClient, "get_vim")
    @mock.patch.object(objects.vnf_package.VnfPackage, 'get_by_id')
    @mock.patch.object(objects.vnf_package.VnfPackage, 'save')
    @mock.patch.object(objects.vnf_instance, '_vnf_instance_create')
    @mock.patch.object(objects.vnf_package_vnfd.VnfPackageVnfd, 'get_by_id')
    def test_create_without_name_and_description(
            self, mock_get_by_id_package_vnfd,
            mock_vnf_instance_create, mock_package_save,
            mock_get_by_id_package, mock_get_vim):

        mock_get_by_id_package_vnfd.return_value = \
            fakes.return_vnf_package_vnfd()
        mock_get_by_id_package.return_value = \
            fakes.return_vnf_package_with_deployment_flavour()

        updates = {'vnfd_id': uuidsentinel.vnfd_id,
                'vnf_instance_description': None,
                'vnf_instance_name': None,
                'vnf_pkg_id': uuidsentinel.vnf_pkg_id,
                'vnf_metadata': {"key": "value"}}

        mock_vnf_instance_create.return_value =\
            fakes.return_vnf_instance_model(**updates)

        req = fake_request.HTTPRequest.blank('/vnf_instances')
        body = {'vnfdId': uuidsentinel.vnfd_id,
                'metadata': {"key": "value"}}
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.headers['Version'] = '2.6.1'
        req.method = 'POST'

        # Call create API
        resp = req.get_response(self.app)

        self.assertEqual(http_client.CREATED, resp.status_code)

        updates = {'vnfInstanceDescription': None, 'vnfInstanceName': None}
        expected_vnf = fakes.fake_vnf_instance_response(
            instantiated_state=fields.VnfInstanceState.NOT_INSTANTIATED,
            **updates)
        location_header = ('http://localhost/vnflcm/v1/vnf_instances/%s'
            % resp.json['id'])

        self.assertEqual(expected_vnf, resp.json)
        self.assertEqual(location_header, resp.headers['location'])

    @mock.patch.object(vim_client.VimClient, "get_vim")
    @mock.patch.object(objects.vnf_package.VnfPackage, 'get_by_id')
    @mock.patch.object(objects.vnf_package.VnfPackage, 'save')
    @mock.patch.object(objects.vnf_instance, '_vnf_instance_create')
    @mock.patch.object(objects.vnf_package_vnfd.VnfPackageVnfd, 'get_by_id')
    def test_create_with_name_and_description(
            self, mock_get_by_id_package_vnfd,
            mock_vnf_instance_create, mock_package_save,
            mock_get_by_id_package, mock_get_vim):
        mock_get_by_id_package_vnfd.return_value = \
            fakes.return_vnf_package_vnfd()
        mock_get_by_id_package.return_value = \
            fakes.return_vnf_package_with_deployment_flavour()

        updates = {'vnfd_id': uuidsentinel.vnfd_id,
                'vnf_instance_description': 'SampleVnf Description',
                'vnf_instance_name': 'SampleVnf',
                'vnf_pkg_id': uuidsentinel.vnf_pkg_id,
                'vnf_metadata': {"key": "value"}}

        mock_vnf_instance_create.return_value =\
            fakes.return_vnf_instance_model(**updates)

        body = {'vnfdId': uuidsentinel.vnfd_id,
                "vnfInstanceName": "SampleVnf",
                "vnfInstanceDescription": "SampleVnf Description",
                'metadata': {"key": "value"}}
        req = fake_request.HTTPRequest.blank('/vnf_instances')
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.headers['Version'] = '2.6.1'
        req.method = 'POST'

        # Call Create API
        resp = req.get_response(self.app)

        self.assertEqual(http_client.CREATED, resp.status_code)
        updates = {"vnfInstanceName": "SampleVnf",
            "vnfInstanceDescription": "SampleVnf Description"}
        expected_vnf = fakes.fake_vnf_instance_response(
            instantiated_state=fields.VnfInstanceState.NOT_INSTANTIATED,
            **updates)
        location_header = ('http://localhost/vnflcm/v1/vnf_instances/%s'
            % resp.json['id'])

        self.assertEqual(expected_vnf, resp.json)
        self.assertEqual(location_header, resp.headers['location'])

    @mock.patch.object(vim_client.VimClient, "get_vim")
    @mock.patch.object(objects.vnf_package.VnfPackage, 'get_by_id')
    @mock.patch.object(objects.vnf_package.VnfPackage, 'save')
    @mock.patch.object(objects.vnf_instance, '_vnf_instance_create')
    @mock.patch.object(objects.vnf_package_vnfd.VnfPackageVnfd, 'get_by_id')
    def test_create_without_name_and_description_with_v241(
            self, mock_get_by_id_package_vnfd,
            mock_vnf_instance_create, mock_package_save,
            mock_get_by_id_package, mock_get_vim):
        mock_get_by_id_package_vnfd.return_value = \
            fakes.return_vnf_package_vnfd()
        mock_get_by_id_package.return_value = \
            fakes.return_vnf_package_with_deployment_flavour()

        updates = {'vnfd_id': uuidsentinel.vnfd_id,
                'vnf_instance_description': None,
                'vnf_instance_name': None,
                'vnf_pkg_id': uuidsentinel.vnf_pkg_id,
                'metadata': {'key': 'value'}}

        mock_vnf_instance_create.return_value =\
            fakes.return_vnf_instance_model(**updates)

        req = fake_request.HTTPRequest.blank('/vnf_instances')
        body = {'vnfdId': uuidsentinel.vnfd_id}
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.headers['Version'] = ''
        req.method = 'POST'

        # Call create API
        resp = req.get_response(self.app)

        self.assertEqual(http_client.CREATED, resp.status_code)

        updates = {'vnfInstanceDescription': None, 'vnfInstanceName': None}
        expected_vnf = fakes.fake_vnf_instance_response(**updates)

        self.assertEqual(expected_vnf, resp.json)

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
        {'attribute': 'metadata', 'value': ['val1', 'val2'],
         'expected_type': 'object'},
        {'attribute': 'metadata', 'value': True,
         'expected_type': 'object'},
        {'attribute': 'metadata', 'value': 123,
         'expected_type': 'object'},
    )
    @ddt.unpack
    def test_create_with_invalid_request_body(
            self, attribute, value, expected_type):
        """value of attribute in body is of invalid type"""
        body = {"vnfInstanceName": "SampleVnf",
                "vnfdId": "29c770a3-02bc-4dfc-b4be-eb173ac00567",
                "vnfInstanceDescription": "VNF Description",
                "metadata": {"key": "value"}}
        req = fake_request.HTTPRequest.blank('/vnf_instances')
        body.update({attribute: value})
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.headers['Version'] = '2.6.1'
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
        elif expected_type == 'object':
            expected_message = ("Invalid input for field/attribute "
                                "{attribute}. " "Value: {value}. {value} is "
                                "not of type 'object'".
                format(value=value, attribute=attribute,
                       expected_type=expected_type))

        self.assertEqual(expected_message, exception.msg)

    @mock.patch.object(objects.vnf_package_vnfd.VnfPackageVnfd, 'get_by_id')
    def test_create_non_existing_vnf_package_vnfd(self, mock_vnf_by_id):
        mock_vnf_by_id.side_effect = exceptions.VnfPackageVnfdNotFound
        body = {'vnfdId': uuidsentinel.vnfd_id,
                'metadata': {"key": "value"}}
        req = fake_request.HTTPRequest.blank('/vnf_instances')
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.headers['Version'] = '2.6.1'
        req.method = 'POST'
        self.assertRaises(exc.HTTPBadRequest, self.controller.create, req,
                          body=body)

    def test_create_without_vnfd_id(self):
        body = {"vnfInstanceName": "SampleVnfInstance",
                'metadata': {"key": "value"}}
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

    @ddt.data({'name': "A" * 256, 'description': "VNF Description",
               'meta': {"key": "value"}},
              {'name': 'Fake-VNF', 'description': "A" * 1025,
               'meta': {"key": "value"}},
              {'name': 'Fake-VNF', 'description': "VNF Description",
               'meta': {"key": "v" * 256}})
    @ddt.unpack
    def test_create_max_length_exceeded_for_vnf_name_and_description(
            self, name, description, meta):
        # vnf instance_name and description with length greater than max
        # length defined
        body = {"vnfInstanceName": name,
                "vnfdId": uuidsentinel.vnfd_id,
                "vnfInstanceDescription": description,
                "metadata": meta}
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

    @mock.patch.object(objects.VnfInstanceList, "get_by_filters")
    @ddt.data(' ', '2.6.1')
    def test_index(self, api_version, mock_vnf_list):
        req = fake_request.HTTPRequest.blank('/vnf_instances')
        req.headers['Version'] = api_version
        vnf_instance_1 = fakes.return_vnf_instance()
        vnf_instance_2 = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED)

        mock_vnf_list.return_value = [vnf_instance_1, vnf_instance_2]
        resp = self.controller.index(req)
        expected_result = [fakes.fake_vnf_instance_response(
            api_version=api_version),
            fakes.fake_vnf_instance_response(
            fields.VnfInstanceState.INSTANTIATED,
            api_version=api_version)]
        self.assertEqual(expected_result, resp)

    @mock.patch.object(objects.VnfInstanceList, "get_by_filters")
    @ddt.data(' ', '2.6.1')
    def test_index_empty_response(self, api_version, mock_vnf_list):
        req = fake_request.HTTPRequest.blank('/vnf_instances')
        req.headers['Version'] = api_version
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

    @mock.patch.object(objects.VnfInstanceList, "get_by_filters")
    @ddt.data(
        {'filter': "(eq,vnfInstanceName,'dummy_name')"},
        {'filter': "(in,vnfInstanceName,'dummy_name')"},
        {'filter': "(cont,vnfInstanceName,'dummy_name')"},
        {'filter': "(neq,vnfInstanceName,'dummy_name')"},
        {'filter': "(nin,vnfInstanceName,'dummy_name')"},
        {'filter': "(ncont,vnfInstanceName,'dummy_name')"},
        {'filter': "(gt,vnfdVersion, 1)"},
        {'filter': "(gte,vnfdVersion, 1)"},
        {'filter': "(lt,vnfdVersion, 1)"},
        {'filter': "(lte,vnfdVersion, 1)"},
    )
    def test_index_filter_operator(self, filter_params, mock_vnf_list):
        """Tests all supported operators in filter expression."""
        api_version = '2.6.1'
        query = urllib.parse.urlencode(filter_params)

        req = fake_request.HTTPRequest.blank(
            '/vnflcm/v1/vnf_instances?' + query)
        req.headers['Version'] = api_version

        vnf_instance_1 = fakes.return_vnf_instance()
        vnf_instance_2 = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED)

        mock_vnf_list.return_value = [vnf_instance_1, vnf_instance_2]
        res_dict = self.controller.index(req)

        expected_result = [fakes.fake_vnf_instance_response(
            api_version=api_version),
            fakes.fake_vnf_instance_response(
            fields.VnfInstanceState.INSTANTIATED,
            api_version=api_version)]
        self.assertEqual(expected_result, res_dict)

    @mock.patch.object(objects.VnfInstanceList, "get_by_filters")
    def test_index_filter_combination(self, mock_vnf_list):
        """Test multiple filter parameters separated by semicolon."""
        params = {
            'filter': "(eq,vnfInstanceName,'dummy_name');"
                      "(eq,vnfInstanceDescription,'dummy_desc')"}

        api_version = '2.6.1'
        query = urllib.parse.urlencode(params)
        req = fake_request.HTTPRequest.blank(
            '/vnflcm/v1/vnf_instances?' + query)
        req.headers['Version'] = '2.6.1'

        vnf_instance_1 = fakes.return_vnf_instance()
        vnf_instance_2 = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED)

        mock_vnf_list.return_value = [vnf_instance_1, vnf_instance_2]
        res_dict = self.controller.index(req)

        expected_result = [fakes.fake_vnf_instance_response(
            api_version=api_version),
            fakes.fake_vnf_instance_response(
            fields.VnfInstanceState.INSTANTIATED,
            api_version=api_version)]
        self.assertEqual(expected_result, res_dict)

    @mock.patch.object(objects.VnfInstanceList, "get_by_filters")
    @ddt.data(
        {'filter': "(eq,vnfInstanceName,dummy_value)"},
        {'filter': "(eq,vnfInstanceDescription,dummy value)"},
        {'filter': "(eq,instantiationState,'NOT_INSTANTIATED')"},
        {'filter': "(eq,taskState,'ACTIVE')"},
        {'filter': "(eq,vnfdId,'dummy_vnfd_id')"},
        {'filter': "(eq,vnfProvider,'''dummy ''hi'' value''')"},
        {'filter': "(eq,vnfProductName,'dummy_product_name')"},
        {'filter': "(eq,vnfSoftwareVersion,'1.0')"},
        {'filter': "(eq,vnfdVersion,'dummy_vnfd_version')"},
        {'filter': "(eq,tenantId,'dummy_tenant_id')"},
        {'filter': "(eq,vnfPkgId,'dummy_pkg_id')"},
        {'filter': "(eq,vimConnectionInfo/accessInfo/region,'dummy_id')"},
        {'filter': "(eq,instantiatedInfo/flavourId,'dummy_flavour')"},
        {'filter': "(eq,instantiatedInfo/vnfInstanceId,'dummy_vnf_id')"},
        {'filter': "(eq,instantiatedInfo/vnfState,'ACTIVE')"},
        {'filter': "(eq,instantiatedInfo/instanceId,'dummy_vnf_id')"},
        {'filter':
            "(eq,instantiatedInfo/instantiationLevelId,'dummy_level_id')"},
        {'filter': "(eq,instantiatedInfo/extCpInfo/id,'dummy_id')"},
        {'filter': "(eq,instantiatedInfo/extVirtualLinkInfo/name,'dummy')"},
        {'filter':
            "(eq,instantiatedInfo/extManagedVirtualLinkInfo/id,'dummy_id')"},
        {'filter': "(eq,instantiatedInfo/vnfcResourceInfo/vduId,'dummy_id')"},
        {'filter':
            "(eq,instantiatedInfo/vnfVirtualLinkResourceInfo/"
            "vnfVirtualLinkDescId,'dummy_id')"},
        {'filter':
            "(eq,instantiatedInfo/virtualStorageResourceInfo/"
            "virtualStorageDescId,'dummy_id')"},
        {'filter': "(eq,instantiatedInfo/additionalParams/error,'dummy')"},
    )
    def test_index_filter_attributes(self, filter_params,
                                     mock_vnf_list):
        """Test various attributes supported for filter parameter."""
        api_version = '2.6.1'
        query = urllib.parse.urlencode(filter_params)
        req = fake_request.HTTPRequest.blank(
            '/vnflcm/v1/vnf_instances?' + query)
        req.headers['Version'] = '2.6.1'

        vnf_instance_1 = fakes.return_vnf_instance()
        vnf_instance_2 = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED)

        mock_vnf_list.return_value = [vnf_instance_1, vnf_instance_2]
        res_dict = self.controller.index(req)

        expected_result = [fakes.fake_vnf_instance_response(
            api_version=api_version),
            fakes.fake_vnf_instance_response(
            fields.VnfInstanceState.INSTANTIATED,
            api_version=api_version)]
        self.assertEqual(expected_result, res_dict)

    @mock.patch.object(objects.VnfInstanceList, "get_by_filters")
    @ddt.data(
        {'filter': "(eq,vnfInstanceName,value"},
        {'filter': "eq,vnfInstanceName,value)"},
        {'filter': "(eq,vnfInstanceName,value);"},
        {'filter': "(eq , vnfInstanceName ,value)"},
    )
    def test_index_filter_invalid_expression(self, filter_params,
                                             mock_vnf_list):
        """Test invalid filter expression."""
        api_version = '2.6.1'
        query = urllib.parse.urlencode(filter_params)
        req = fake_request.HTTPRequest.blank(
            '/vnflcm/v1/vnf_instances?' + query)
        req.headers['Version'] = api_version

        self.assertRaises(exceptions.ValidationError,
                          self.controller.index, req)

    @mock.patch.object(objects.VnfInstanceList, "get_by_filters")
    @ddt.data(
        {'filter': "(eq,vnfInstanceName,singl'quote)"},
        {'filter': "(eq,vnfInstanceName,three''' quotes)"},
        {'filter': "(eq,vnfInstanceName,round ) bracket)"},
        {'filter': "(eq,vnfInstanceName,'dummy 'hi' value')"},
        {'filter': "(eq,vnfInstanceName,'dummy's value')"},
        {'filter': "(eq,vnfInstanceName,'three ''' quotes')"},
    )
    def test_index_filter_invalid_string_values(self, filter_params,
                                                mock_vnf_list):
        """Test invalid string values as per ETSI NFV SOL013 5.2.2."""
        api_version = '2.6.1'
        query = urllib.parse.urlencode(filter_params)
        req = fake_request.HTTPRequest.blank(
            '/vnflcm/v1/vnf_instances?' + query)
        req.headers['Version'] = api_version
        self.assertRaises(exceptions.ValidationError,
                          self.controller.index, req)

    @mock.patch.object(objects.VnfInstanceList, "get_by_filters")
    @ddt.data(
        {'filter': '(eq,vnfdId,value1,value2)'},
        {'filter': '(fake,vnfdId,dummy_vnfd_id)'},
        {'filter': '(,vnfdId,dummy_vnfd_id)'},
    )
    def test_index_filter_invalid_operator(self, filter_params,
                                           mock_vnf_list):
        """Test invalid operator in filter expression."""
        api_version = '2.6.1'
        query = urllib.parse.urlencode(filter_params)
        req = fake_request.HTTPRequest.blank(
            '/vnflcm/v1/vnf_instances?' + query)
        req.headers['Version'] = api_version
        self.assertRaises(exceptions.ValidationError,
                          self.controller.index, req)

    @mock.patch.object(objects.VnfInstanceList, "get_by_filters")
    @ddt.data(
        {'filter': '(eq,fakeattr,fakevalue)'},
        {'filter': '(eq,,fakevalue)'},
    )
    def test_index_filter_invalid_attribute(self, filter_params,
                                            mock_vnf_list):
        """Test invalid attribute in filter expression."""
        api_version = '2.6.1'
        query = urllib.parse.urlencode(filter_params)
        req = fake_request.HTTPRequest.blank(
            '/vnflcm/v1/vnf_instances?' + query)
        req.headers['Version'] = api_version
        self.assertRaises(exceptions.ValidationError,
                          self.controller.index, req)

    @mock.patch.object(objects.VnfInstanceList, "get_by_filters")
    @ddt.data(
        {'filter': '(eq,data/size,fake_value)'},
        {'filter': '(gt,data/createdAt,fake_value)'},
        {'filter': '(eq,data/minDisk,fake_value)'},
        {'filter': '(eq,data/minRam,fake_value)'},
    )
    def test_index_filter_invalid_value_type(self, filter_params,
                                             mock_vnf_list):
        """Test values which doesn't match with attribute data type."""
        api_version = '2.6.1'
        query = urllib.parse.urlencode(filter_params)
        req = fake_request.HTTPRequest.blank(
            '/vnflcm/v1/vnf_instances?' + query)
        req.headers['Version'] = api_version
        self.assertRaises(exceptions.ValidationError,
                          self.controller.index, req)
