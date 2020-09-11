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

import codecs
import os

import ddt
import json
from oslo_serialization import jsonutils
from six.moves import http_client
import urllib
import webob
from webob import exc

from tacker.api.vnflcm.v1 import controller
from tacker.api.vnflcm.v1 import sync_resource
from tacker.common import exceptions
import tacker.conductor.conductorrpc.vnf_lcm_rpc as vnf_lcm_rpc
from tacker import context
import tacker.db.vnfm.vnfm_db
from tacker.extensions import nfvo
from tacker.extensions import vnfm
from tacker.manager import TackerManager
from tacker import objects
from tacker.objects import fields
from tacker.tests import constants
from tacker.tests.unit import base
from tacker.tests.unit.db import utils
from tacker.tests.unit import fake_request
import tacker.tests.unit.nfvo.test_nfvo_plugin as test_nfvo_plugin
from tacker.tests.unit.vnflcm import fakes
from tacker.tests import uuidsentinel
import tacker.vnfm.nfvo_client as nfvo_client
from tacker.vnfm import vim_client


class FakeVimClient(mock.Mock):
    pass


def _get_template(name):
    filename = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                '../../etc/samples/' + str(name)))
    f = codecs.open(filename, encoding='utf-8', errors='strict')
    return f.read()


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

    def get_vnfd(self, *args, **kwargs):
        if 'VNF1' in args:
            return {'id': self.vnf1_vnfd_id,
                    'name': 'VNF1',
                    'attributes': {'vnfd': _get_template(
                                   'test-nsd-vnfd1.yaml')}}
        elif 'VNF2' in args:
            return {'id': self.vnf3_vnfd_id,
                    'name': 'VNF2',
                    'attributes': {'vnfd': _get_template(
                                   'test-nsd-vnfd2.yaml')}}

    def get_vnfds(self, *args, **kwargs):
        if {'name': ['VNF1']} in args:
            return [{'id': self.vnf1_vnfd_id}]
        elif {'name': ['VNF3']} in args:
            return [{'id': self.vnf3_vnfd_id}]
        else:
            return []

    def get_vnfs(self, *args, **kwargs):
        if {'vnfd_id': [self.vnf1_vnfd_id]} in args:
            return [{'id': self.vnf1_vnf_id}]
        elif {'vnfd_id': [self.vnf3_vnfd_id]} in args:
            return [{'id': self.vnf3_vnf_id}]
        else:
            return None

    def get_vnf(self, *args, **kwargs):
        if self.vnf1_vnf_id in args:
            return self.get_dummy_vnf_error()
        elif self.vnf3_vnf_id in args:
            return self.get_dummy_vnf_not_error()
        else:
            return self.get_dummy_vnf_active()

    def get_vnf_resources(self, *args, **kwargs):
        if self.vnf1_vnf_id in args:
            return self.get_dummy_vnf1_details()
        elif self.vnf1_update_vnf_id in args:
            return self.get_dummy_vnf1_update_details()
        elif self.vnf3_vnf_id in args:
            return self.get_dummy_vnf3_details()
        elif self.vnf3_update_vnf_id in args:
            return self.get_dummy_vnf3_update_details()

    def get_dummy_vnf1_details(self):
        return [{'name': 'CP11', 'id': self.cp11_id},
                {'name': 'CP12', 'id': self.cp12_id}]

    def get_dummy_vnf1_update_details(self):
        return [{'name': 'CP11', 'id': self.cp11_update_id},
                {'name': 'CP12', 'id': self.cp12_update_id}]

    def get_dummy_vnf3_details(self):
        return [{'name': 'CP32', 'id': self.cp32_id}]

    def get_dummy_vnf3_update_details(self):
        return [{'name': 'CP32', 'id': self.cp32_update_id}]

    def get_dummy_vnf_active(self):
        return {'tenant_id': uuidsentinel.tenant_id,
            'name': "fake_name",
            'vnfd_id': uuidsentinel.vnfd_id,
            'vnf_instance_id': uuidsentinel.instance_id,
            'mgmt_ip_address': "fake_mgmt_ip_address",
            'status': 'ACTIVE',
            'description': 'fake_description',
            'placement_attr': 'fake_placement_attr',
            'vim_id': 'uuidsentinel.vim_id',
            'error_reason': 'fake_error_reason',
            'attributes': {
                "scale_group": '{"scaleGroupDict":' +
                    '{"SP1": {"maxLevel" : 3}}}'}}

    def get_dummy_vnf_error(self):
        return {'tenant_id': uuidsentinel.tenant_id,
            'name': "fake_name",
            'vnfd_id': uuidsentinel.vnfd_id,
            'vnf_instance_id': uuidsentinel.instance_id,
            'mgmt_ip_address': "fake_mgmt_ip_address",
            'status': 'ERROR',
            'description': 'fake_description',
            'placement_attr': 'fake_placement_attr',
            'vim_id': 'uuidsentinel.vim_id',
            'error_reason': 'fake_error_reason',
            'attributes': {
                "scale_group": '{"scaleGroupDict":' +
                    '{"SP1": {"maxLevel" : 3}}}'}}

    def get_dummy_vnf_not_error(self):
        msg = _('VNF %(vnf_id)s could not be found')
        raise vnfm.VNFNotFound(explanation=msg)


@ddt.ddt
class TestController(base.TestCase):

    def setUp(self):
        super(TestController, self).setUp()
        self.patcher = mock.patch(
            'tacker.manager.TackerManager.get_service_plugins',
            return_value={'VNFM': test_nfvo_plugin.FakeVNFMPlugin()})
        self.mock_manager = self.patcher.start()
        self.controller = controller.VnfLcmController()
        self.vim_info = {
            'vim_id': uuidsentinel.vnfd_id,
            'vim_type': 'test',
            'vim_auth': {'username': 'test', 'password': 'test'},
            'placement_attr': {'region': 'TestRegionOne'},
            'tenant': 'test'
        }
        self.context = context.get_admin_context()

        with mock.patch.object(tacker.db.vnfm.vnfm_db.VNFMPluginDb, 'get_vnfs',
                               return_value=[]):
            with mock.patch.object(TackerManager, 'get_service_plugins',
                                   return_value={'VNFM':
                                   test_nfvo_plugin.FakeVNFMPlugin()}):
                self.controller = controller.VnfLcmController()

    def tearDown(self):
        self.mock_manager.stop()
        super(TestController, self).tearDown()

    @property
    def app(self):
        return fakes.wsgi_app_v1()

    def _get_dummy_vnf(self, vnf_id=None, status=None):
        vnf_dict = utils.get_dummy_vnf()

        if status:
            vnf_dict['status'] = status

        if vnf_id:
            vnf_dict['id'] = vnf_id

        return vnf_dict

    def _make_problem_detail(
            self,
            detail,
            status,
            title=None,
            type=None,
            instance=None):
        res = webob.Response(content_type='application/problem+json')
        problemDetails = {}
        if type:
            problemDetails['type'] = type
        if title:
            problemDetails['title'] = title
        problemDetails['detail'] = detail
        problemDetails['status'] = status
        if instance:
            problemDetails['instance'] = instance
        res.text = json.dumps(problemDetails)
        res.status_int = status
        return res

    @mock.patch.object(vim_client.VimClient, "get_vim")
    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._update_package_usage_state')
    @mock.patch.object(objects.VnfPackage, 'get_by_id')
    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._create_vnf')
    @mock.patch.object(objects.vnf_package.VnfPackage, 'save')
    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM':
                       test_nfvo_plugin.FakeVNFMPlugin()})
    @mock.patch.object(objects.vnf_instance, '_vnf_instance_create')
    @mock.patch.object(objects.vnf_package_vnfd.VnfPackageVnfd, 'get_by_id')
    def test_create_without_name_and_description(
            self, mock_get_by_id,
            mock_vnf_instance_create,
            mock_get_service_plugins,
            mock_package_save,
            mock_private_create_vnf,
            mock_vnf_package_get_by_id,
            mock_update_package_usage_state,
            mock_get_vim):
        mock_get_vim.return_value = self.vim_info
        mock_get_by_id.return_value = fakes.return_vnf_package_vnfd()
        mock_vnf_package_get_by_id.return_value = \
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

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM':
                       test_nfvo_plugin.FakeVNFMPlugin()})
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
         'expected_type': 'description'}
    )
    @ddt.unpack
    def test_create_with_invalid_request_body(
            self, mock_get_service_plugins, attribute, value, expected_type):
        """value of attribute in body is of invalid type"""
        body = {"vnfInstanceName": "SampleVnf",
                "vnfdId": "29c770a3-02bc-4dfc-b4be-eb173ac00567",
                "vnfInstanceDescription": "VNF Description",
                "metadata": {"key": "value"}}
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
        elif expected_type == 'object':
            expected_message = ("Invalid input for field/attribute "
                                "{attribute}. " "Value: {value}. {value} is "
                                "not of type 'object'".
                format(value=value, attribute=attribute,
                       expected_type=expected_type))

        self.assertEqual(expected_message, exception.msg)

    @mock.patch.object(sync_resource.SyncVnfPackage, 'create_package')
    @mock.patch.object(nfvo_client.VnfPackageRequest, "index")
    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': test_nfvo_plugin.FakeVNFMPlugin()})
    @mock.patch.object(objects.vnf_package_vnfd.VnfPackageVnfd, 'get_by_id')
    def test_create_non_existing_vnf_package_vnfd(self, mock_vnf_by_id,
            mock_get_service_plugins,
            mock_index,
            mock_create_package):
        mock_vnf_by_id.side_effect = exceptions.VnfPackageVnfdNotFound
        mock_create_package.return_value = fakes.return_vnf_package_vnfd()
        mock_response = mock.MagicMock()
        mock_response.ok = True
        mock_response.json = mock.MagicMock()
        mock_response.json.return_value = ['aaa', 'bbb', 'ccc']
        mock_index.return_value = mock_response
        body = {'vnfdId': uuidsentinel.vnfd_id,
                'metadata': {"key": "value"}}
        req = fake_request.HTTPRequest.blank('/vnf_instances')
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'
        self.assertRaises(exc.HTTPBadRequest, self.controller.create, req,
                          body=body)

    @mock.patch.object(vim_client.VimClient, "get_vim")
    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._update_package_usage_state')
    @mock.patch.object(objects.VnfPackage, 'get_by_id')
    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._create_vnf')
    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': test_nfvo_plugin.FakeVNFMPlugin()})
    @mock.patch.object(sync_resource.SyncVnfPackage, 'create_package')
    @mock.patch.object(nfvo_client.VnfPackageRequest, "index")
    @mock.patch.object(objects.vnf_instance, '_vnf_instance_create')
    @mock.patch.object(objects.vnf_package_vnfd.VnfPackageVnfd, 'get_by_id')
    def test_create_vnf_package_not_found(
            self, mock_get_by_id_package_vnfd,
            mock_vnf_instance_create,
            mock_index, mock_create_pkg,
            mock_get_service_plugins,
            mock_private_create_vnf,
            mock_vnf_package_get_by_id,
            mock_update_package_usage_state,
            mock_get_vim):
        mock_get_by_id_package_vnfd.side_effect =\
            exceptions.VnfPackageVnfdNotFound

        mock_response = mock.MagicMock()
        mock_response.ok = True
        mock_response.json = mock.MagicMock()
        mock_response.json.return_value = ['aaa', 'bbb', 'ccc']

        mock_index.return_value = mock_response
        mock_create_pkg.return_value = fakes.return_vnf_package_vnfd()

        updates = {'vnfd_id': uuidsentinel.vnfd_id}
        mock_vnf_instance_create.return_value =\
            fakes.return_vnf_instance_model(**updates)

        body = {'vnfdId': uuidsentinel.vnfd_id}
        req = fake_request.HTTPRequest.blank('/vnf_instances')
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'
        req.environ['tacker.context'] = self.context

        # Call Create API
        resp = req.get_response(self.app)
        self.assertEqual(http_client.CREATED, resp.status_code)

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': test_nfvo_plugin.FakeVNFMPlugin()})
    @mock.patch.object(sync_resource.SyncVnfPackage, 'create_package')
    @mock.patch.object(nfvo_client.VnfPackageRequest, "index")
    @mock.patch.object(objects.vnf_instance, '_vnf_instance_create')
    @mock.patch.object(objects.vnf_package_vnfd.VnfPackageVnfd, 'get_by_id')
    def test_create_vnf_package_vnfd_not_found(
            self, mock_get_by_id_package_vnfd,
            mock_vnf_instance_create,
            mock_index, mock_create_pkg,
            mock_get_service_plugins):
        mock_get_by_id_package_vnfd.side_effect =\
            exceptions.VnfPackageVnfdNotFound

        mock_response = mock.MagicMock()
        mock_response.ok = True
        mock_response.json = mock.MagicMock()
        mock_response.json.return_value = ['aaa', 'bbb', 'ccc']

        mock_index.return_value = mock_response
        mock_create_pkg.return_value = None

        updates = {'vnfd_id': uuidsentinel.vnfd_id}
        mock_vnf_instance_create.return_value =\
            fakes.return_vnf_instance_model(**updates)

        body = {'vnfdId': uuidsentinel.vnfd_id}
        req = fake_request.HTTPRequest.blank('/vnf_instances')
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        # Call Create API
        resp = req.get_response(self.app)
        self.assertEqual(http_client.INTERNAL_SERVER_ERROR, resp.status_code)

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': test_nfvo_plugin.FakeVNFMPlugin()})
    @mock.patch.object(nfvo_client.VnfPackageRequest, "index")
    @mock.patch.object(objects.vnf_instance, '_vnf_instance_create')
    @mock.patch.object(objects.vnf_package_vnfd.VnfPackageVnfd, 'get_by_id')
    def test_create_non_vnf_package_info(
            self, mock_get_by_id_package_vnfd,
            mock_vnf_instance_create,
            mock_index, mock_get_service_plugins):
        mock_get_by_id_package_vnfd.side_effect =\
            exceptions.VnfPackageVnfdNotFound

        mock_response = mock.MagicMock()
        mock_response.ok = False
        mock_response.json = mock.MagicMock()
        mock_response.json.return_value = {}

        mock_index.return_value = mock_response

        updates = {'vnfd_id': uuidsentinel.vnfd_id}
        mock_vnf_instance_create.return_value =\
            fakes.return_vnf_instance_model(**updates)

        body = {'vnfdId': uuidsentinel.vnfd_id}
        req = fake_request.HTTPRequest.blank('/vnf_instances')
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        # Call Create API
        resp = req.get_response(self.app)

        self.assertEqual(http_client.NOT_FOUND, resp.status_code)

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': test_nfvo_plugin.FakeVNFMPlugin()})
    def test_create_without_vnfd_id(self, mock_get_service_plugins):
        body = {"vnfInstanceName": "SampleVnfInstance",
                "metadata": {"key": "value"}}
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances')
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'
        resp = req.get_response(self.app)

        self.assertEqual(http_client.BAD_REQUEST, resp.status_code)

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM':
                       test_nfvo_plugin.FakeVNFMPlugin()})
    @ddt.data('PATCH', 'PUT', 'HEAD', 'DELETE')
    def test_create_not_allowed_http_method(self, method,
                                            mock_get_service_plugins):
        """Wrong HTTP method"""
        body = {"vnfdId": uuidsentinel.vnfd_id}
        req = fake_request.HTTPRequest.blank('/vnf_instances')
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = method
        resp = req.get_response(self.app)

        self.assertEqual(http_client.METHOD_NOT_ALLOWED, resp.status_code)

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': test_nfvo_plugin.FakeVNFMPlugin()})
    @ddt.data({'name': "A" * 256,
    'description': "VNF Description",
    'meta': {"key": "value"}},
        {'name': 'Fake-VNF',
    'description': "A" * 1025,
    'meta': {"key": "value"}},
        {'name': 'Fake-VNF',
    'description': "VNF Description",
     'meta': {"key": "v" * 256}})
    def test_create_max_length_exceeded_for_vnf_name_and_description(
            self, values, mock_get_service_plugins):
        name = values['name']
        meta = values['meta']
        description = values['description']
        # vnf instance_name and description with length greater than max
        # length defined
        body = {"vnfInstanceName": name,
                "vnfdId": uuidsentinel.vnfd_id,
                "vnfInstanceDescription": description,
                'metadata': meta}
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances')
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'
        resp = req.get_response(self.app)

        self.assertEqual(http_client.BAD_REQUEST, resp.status_code)

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM':
                       test_nfvo_plugin.FakeVNFMPlugin()})
    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._notification_process')
    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._get_vnf')
    @mock.patch.object(vim_client.VimClient, "get_vim")
    @mock.patch.object(objects.vnf_instance, "_vnf_instance_get_by_id")
    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch.object(objects.VnfPackageVnfd, 'get_by_id')
    @mock.patch.object(objects.VnfPackage, "get_by_id")
    @mock.patch.object(vnf_lcm_rpc.VNFLcmRPCAPI, "instantiate")
    def test_instantiate_with_deployment_flavour(
            self, mock_instantiate, mock_vnf_package_get_by_id,
            mock_vnf_package_vnfd_get_by_id, mock_save,
            mock_vnf_instance_get_by_id, mock_get_vim,
            mock_get_vnf, mock_insta_notfi_process,
            mock_get_service_plugins):

        mock_vnf_instance_get_by_id.return_value =\
            fakes.return_vnf_instance_model()
        mock_vnf_package_vnfd_get_by_id.return_value = \
            fakes.return_vnf_package_vnfd()
        mock_vnf_package_get_by_id.return_value = \
            fakes.return_vnf_package_with_deployment_flavour()
        mock_get_vnf.return_value = \
            self._get_dummy_vnf(
                vnf_id=mock_vnf_instance_get_by_id.return_value.id,
                status='INACTIVE')

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

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM':
                       test_nfvo_plugin.FakeVNFMPlugin()})
    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._get_vnf')
    @mock.patch.object(objects.vnf_instance, "_vnf_instance_get_by_id")
    @mock.patch.object(objects.VnfPackageVnfd, 'get_by_id')
    @mock.patch.object(objects.VnfPackage, "get_by_id")
    def test_instantiate_with_non_existing_deployment_flavour(
            self, mock_vnf_package_get_by_id,
            mock_vnf_package_vnfd_get_by_id,
            mock_vnf_instance_get_by_id, mock_get_vnf,
            mock_get_service_plugins):

        mock_vnf_instance_get_by_id.return_value =\
            fakes.return_vnf_instance_model()
        mock_vnf_package_vnfd_get_by_id.return_value = \
            fakes.return_vnf_package_vnfd()
        mock_vnf_package_get_by_id.return_value = \
            fakes.return_vnf_package_with_deployment_flavour()
        mock_get_vnf.return_value = \
            self._get_dummy_vnf(
                vnf_id=mock_vnf_instance_get_by_id.return_value.id,
                status='INACTIVE')

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
        mock_get_vnf.assert_called_once()

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM':
                       test_nfvo_plugin.FakeVNFMPlugin()})
    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._notification_process')
    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._get_vnf')
    @mock.patch.object(vim_client.VimClient, "get_vim")
    @mock.patch.object(objects.vnf_instance, "_vnf_instance_get_by_id")
    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch.object(objects.VnfPackageVnfd, 'get_by_id')
    @mock.patch.object(objects.VnfPackage, "get_by_id")
    @mock.patch.object(vnf_lcm_rpc.VNFLcmRPCAPI, "instantiate")
    def test_instantiate_with_instantiation_level(
            self, mock_instantiate, mock_vnf_package_get_by_id,
            mock_vnf_package_vnfd_get_by_id, mock_save,
            mock_vnf_instance_get_by_id, mock_get_vim,
            mock_get_vnf, mock_insta_notif_process,
            mock_get_service_plugins):

        mock_vnf_instance_get_by_id.return_value =\
            fakes.return_vnf_instance_model()
        mock_vnf_package_vnfd_get_by_id.return_value = \
            fakes.return_vnf_package_vnfd()
        mock_vnf_package_get_by_id.return_value = \
            fakes.return_vnf_package_with_deployment_flavour()
        mock_get_vnf.return_value = \
            self._get_dummy_vnf(
                vnf_id=mock_vnf_instance_get_by_id.return_value.id,
                status='INACTIVE')

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
        mock_get_vnf.assert_called_once()
        mock_insta_notif_process.assert_called_once()

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM':
                       test_nfvo_plugin.FakeVNFMPlugin()})
    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._get_vnf')
    @mock.patch.object(vim_client.VimClient, "get_vim")
    @mock.patch.object(objects.vnf_instance, "_vnf_instance_get_by_id")
    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch.object(objects.VnfPackageVnfd, 'get_by_id')
    @mock.patch.object(objects.VnfPackage, "get_by_id")
    @mock.patch.object(vnf_lcm_rpc.VNFLcmRPCAPI, "instantiate")
    def test_instantiate_with_no_inst_level_in_flavour(
            self, mock_instantiate, mock_vnf_package_get_by_id,
            mock_vnf_package_vnfd_get_by_id, mock_save,
            mock_vnf_instance_get_by_id, mock_get_vim,
            mock_get_vnf, mock_get_service_plugins):

        mock_vnf_instance_get_by_id.return_value =\
            fakes.return_vnf_instance_model()
        mock_vnf_package_vnfd_get_by_id.return_value = \
            fakes.return_vnf_package_vnfd()
        vnf_package = fakes.return_vnf_package_with_deployment_flavour()
        vnf_package.vnf_deployment_flavours[0].instantiation_levels = None
        mock_vnf_package_get_by_id.return_value = vnf_package
        mock_get_vnf.return_value = \
            self._get_dummy_vnf(
                vnf_id=mock_vnf_instance_get_by_id.return_value.id,
                status='INACTIVE')

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
                         "'instantiation_level_1'.",
                         resp.json['badRequest']['message'])
        mock_get_vnf.assert_called_once()

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM':
                       test_nfvo_plugin.FakeVNFMPlugin()})
    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._get_vnf')
    @mock.patch.object(objects.vnf_instance, "_vnf_instance_get_by_id")
    @mock.patch.object(objects.VnfPackageVnfd, 'get_by_id')
    @mock.patch.object(objects.VnfPackage, "get_by_id")
    @mock.patch.object(vnf_lcm_rpc.VNFLcmRPCAPI, "instantiate")
    def test_instantiate_with_non_existing_instantiation_level(
            self, mock_instantiate, mock_vnf_package_get_by_id,
            mock_vnf_package_vnfd_get_by_id,
            mock_vnf_instance_get_by_id, mock_get_vnf,
            mock_get_service_plugins):

        mock_vnf_instance_get_by_id.return_value =\
            fakes.return_vnf_instance_model()
        mock_vnf_package_vnfd_get_by_id.return_value = \
            fakes.return_vnf_package_vnfd()
        mock_vnf_package_get_by_id.return_value = \
            fakes.return_vnf_package_with_deployment_flavour()
        mock_get_vnf.return_value = \
            self._get_dummy_vnf(
                vnf_id=mock_vnf_instance_get_by_id.return_value.id,
                status='INACTIVE')

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
        mock_get_vnf.assert_called_once()

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM':
                       test_nfvo_plugin.FakeVNFMPlugin()})
    @mock.patch('tacker.api.vnflcm.v1.controller.VnfLcmController.'
                '_notification_process')
    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._get_vnf')
    @mock.patch.object(vim_client.VimClient, "get_vim")
    @mock.patch.object(objects.vnf_instance, "_vnf_instance_get_by_id")
    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch.object(objects.VnfPackageVnfd, 'get_by_id')
    @mock.patch.object(objects.VnfPackage, "get_by_id")
    @mock.patch.object(vnf_lcm_rpc.VNFLcmRPCAPI, "instantiate")
    def test_instantiate_with_vim_connection(
            self, mock_instantiate, mock_vnf_package_get_by_id,
            mock_vnf_package_vnfd_get_by_id, mock_save,
            mock_vnf_instance_get_by_id, mock_get_vim,
            mock_get_vnf, mock_insta_notif_process,
            mock_get_service_plugins):

        mock_vnf_instance_get_by_id.return_value =\
            fakes.return_vnf_instance_model()
        mock_vnf_package_vnfd_get_by_id.return_value = \
            fakes.return_vnf_package_vnfd()
        mock_vnf_package_get_by_id.return_value = \
            fakes.return_vnf_package_with_deployment_flavour()
        mock_get_vnf.return_value = \
            self._get_dummy_vnf(
                vnf_id=mock_vnf_instance_get_by_id.return_value.id,
                status='INACTIVE')

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
        mock_get_vnf.assert_called_once()
        mock_insta_notif_process.assert_called_once()

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM':
                       test_nfvo_plugin.FakeVNFMPlugin()})
    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._get_vnf')
    @mock.patch.object(vim_client.VimClient, "get_vim")
    @mock.patch.object(objects.vnf_instance, "_vnf_instance_get_by_id")
    @mock.patch.object(objects.VnfPackageVnfd, 'get_by_id')
    @mock.patch.object(objects.VnfPackage, "get_by_id")
    def test_instantiate_with_non_existing_vim(
            self, mock_vnf_package_get_by_id,
            mock_vnf_package_vnfd_get_by_id,
            mock_vnf_instance_get_by_id, mock_get_vim,
            mock_get_vnf, mock_get_service_plugins):

        mock_vnf_instance_get_by_id.return_value =\
            fakes.return_vnf_instance_model()
        mock_vnf_package_vnfd_get_by_id.return_value = \
            fakes.return_vnf_package_vnfd()
        mock_vnf_package_get_by_id.return_value = \
            fakes.return_vnf_package_with_deployment_flavour()
        mock_get_vim.side_effect = nfvo.VimNotFoundException
        mock_get_vnf.return_value = \
            self._get_dummy_vnf(
                vnf_id=mock_vnf_instance_get_by_id.return_value.id,
                status='INACTIVE')

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
                         uuidsentinel.vim_id,
                         resp.json['badRequest']['message'])
        mock_get_vnf.assert_called_once()

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM':
                       test_nfvo_plugin.FakeVNFMPlugin()})
    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._get_vnf')
    @mock.patch.object(vim_client.VimClient, "get_vim")
    @mock.patch.object(objects.vnf_instance, "_vnf_instance_get_by_id")
    @mock.patch.object(objects.VnfPackageVnfd, 'get_by_id')
    @mock.patch.object(objects.VnfPackage, "get_by_id")
    def test_instantiate_with_non_existing_region_vim(
            self, mock_vnf_package_get_by_id,
            mock_vnf_package_vnfd_get_by_id,
            mock_vnf_instance_get_by_id, mock_get_vim,
            mock_get_vnf, mock_get_service_plugins):

        mock_vnf_instance_get_by_id.return_value =\
            fakes.return_vnf_instance_model()
        mock_vnf_package_vnfd_get_by_id.return_value = \
            fakes.return_vnf_package_vnfd()
        mock_vnf_package_get_by_id.return_value = \
            fakes.return_vnf_package_with_deployment_flavour()
        mock_get_vim.side_effect = nfvo.VimRegionNotFoundException
        mock_get_vnf.return_value = \
            self._get_dummy_vnf(
                vnf_id=mock_vnf_instance_get_by_id.return_value.id,
                status='INACTIVE')

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
                         uuidsentinel.vim_id,
                         resp.json['badRequest']['message'])
        mock_get_vnf.assert_called_once()

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM':
                       test_nfvo_plugin.FakeVNFMPlugin()})
    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._get_vnf')
    @mock.patch.object(vim_client.VimClient, "get_vim")
    @mock.patch.object(objects.vnf_instance, "_vnf_instance_get_by_id")
    @mock.patch.object(objects.VnfPackageVnfd, 'get_by_id')
    @mock.patch.object(objects.VnfPackage, "get_by_id")
    def test_instantiate_with_default_vim_not_configured(
            self, mock_vnf_package_get_by_id,
            mock_vnf_package_vnfd_get_by_id,
            mock_vnf_instance_get_by_id, mock_get_vim,
            mock_get_vnf, mock_get_service_plugins):

        mock_vnf_instance_get_by_id.return_value =\
            fakes.return_vnf_instance_model()
        mock_vnf_package_vnfd_get_by_id.return_value = \
            fakes.return_vnf_package_vnfd()
        mock_vnf_package_get_by_id.return_value = \
            fakes.return_vnf_package_with_deployment_flavour()
        mock_get_vim.side_effect = nfvo.VimDefaultNotDefined
        mock_get_vnf.return_value = \
            self._get_dummy_vnf(
                vnf_id=mock_vnf_instance_get_by_id.return_value.id,
                status='INACTIVE')

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
        mock_get_vnf.assert_called_once()

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM':
                       test_nfvo_plugin.FakeVNFMPlugin()})
    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._get_vnf')
    @mock.patch.object(objects.vnf_instance, "_vnf_instance_get_by_id")
    def test_instantiate_incorrect_instantiation_state(
            self, mock_vnf_by_id, mock_get_vnf, mock_get_service_plugins):
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

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM':
                       test_nfvo_plugin.FakeVNFMPlugin()})
    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._get_vnf')
    @mock.patch.object(objects.vnf_instance, "_vnf_instance_get_by_id")
    def test_instantiate_incorrect_task_state(
            self,
            mock_vnf_by_id,
            mock_get_vnf,
            mock_get_service_plugins):
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

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM':
                       test_nfvo_plugin.FakeVNFMPlugin()})
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
            self, mock_get_service_plugins, attribute, value, expected_type):
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

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM':
                       test_nfvo_plugin.FakeVNFMPlugin()})
    def test_instantiate_without_flavour_id(self,
                                            mock_get_service_plugins):
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

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM':
                       test_nfvo_plugin.FakeVNFMPlugin()})
    def test_instantiate_invalid_request_parameter(self,
                                                   mock_get_service_plugins):
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

        self.assertEqual(http_client.INTERNAL_SERVER_ERROR, resp.status_code)

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM':
                       test_nfvo_plugin.FakeVNFMPlugin()})
    def test_instantiate_with_invalid_uuid(self,
                                           mock_get_service_plugins):
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
            "Can not find requested vnf: %s" % constants.INVALID_UUID,
            resp.json['itemNotFound']['message'])

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM':
                       test_nfvo_plugin.FakeVNFMPlugin()})
    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._get_vnf')
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    def test_instantiate_with_non_existing_vnf_instance(
            self, mock_vnf_by_id, mock_get_vnf,
            mock_get_service_plugins):
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
        mock_get_vnf.assert_called_once()

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM':
                       test_nfvo_plugin.FakeVNFMPlugin()})
    @ddt.data('HEAD', 'PUT', 'DELETE', 'PATCH', 'GET')
    def test_instantiate_invalid_http_method(self, method,
                                             mock_get_service_plugins):
        # Wrong HTTP method
        body = fakes.get_vnf_instantiation_request_body()
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/29c770a3-02bc-4dfc-b4be-eb173ac00567/instantiate')
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = method
        resp = req.get_response(self.app)
        self.assertEqual(http_client.METHOD_NOT_ALLOWED, resp.status_code)

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': test_nfvo_plugin.FakeVNFMPlugin()})
    @mock.patch.object(objects.vnf_instance, "_vnf_instance_get_by_id")
    def test_show_vnf_not_instantiated(self, mock_vnf_by_id,
            mock_get_service_plugins):
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s' % uuidsentinel.instance_id)
        mock_vnf_by_id.return_value = fakes.return_vnf_instance_model()
        expected_result = fakes.fake_vnf_instance_response()
        res_dict = self.controller.show(req, uuidsentinel.instance_id)
        self.assertEqual(expected_result, res_dict)

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM':
                       test_nfvo_plugin.FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    def test_show_vnf_instantiated(self, mock_vnf_by_id,
                                   mock_get_service_plugins):
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s' % uuidsentinel.instance_id)
        mock_vnf_by_id.return_value = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED)
        expected_result = fakes.fake_vnf_instance_response(
            fields.VnfInstanceState.INSTANTIATED)
        res_dict = self.controller.show(req, uuidsentinel.instance_id)
        self.assertEqual(expected_result, res_dict)

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM':
                       test_nfvo_plugin.FakeVNFMPlugin()})
    @mock.patch.object(objects.vnf_instance, "_vnf_instance_get_by_id")
    def test_show_with_non_existing_vnf_instance(self, mock_vnf_by_id,
                                                 mock_get_service_plugins):
        mock_vnf_by_id.side_effect = exceptions.VnfInstanceNotFound
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s' % uuidsentinel.vnf_instance_id)

        resp = req.get_response(self.app)

        self.assertEqual(http_client.NOT_FOUND, resp.status_code)
        self.assertEqual("Can not find requested vnf instance: %s" %
                         uuidsentinel.vnf_instance_id,
                         resp.json['itemNotFound']['message'])

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM':
                       test_nfvo_plugin.FakeVNFMPlugin()})
    def test_show_with_invalid_uuid(self,
                                    mock_get_service_plugins):
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s' % constants.INVALID_UUID)

        resp = req.get_response(self.app)
        self.assertEqual(http_client.NOT_FOUND, resp.status_code)
        self.assertEqual("Can not find requested vnf instance: %s" %
                         constants.INVALID_UUID,
                         resp.json['itemNotFound']['message'])

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM':
                       test_nfvo_plugin.FakeVNFMPlugin()})
    @ddt.data('HEAD', 'PUT', 'POST')
    def test_show_invalid_http_method(self, http_method,
                                      mock_get_service_plugins):
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s' % constants.UUID)
        req.headers['Content-Type'] = 'application/json'
        req.method = http_method

        resp = req.get_response(self.app)
        self.assertEqual(http_client.METHOD_NOT_ALLOWED, resp.status_code)

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM':
                       test_nfvo_plugin.FakeVNFMPlugin()})
    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._notification_process')
    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._get_vnf')
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch.object(vnf_lcm_rpc.VNFLcmRPCAPI, "terminate")
    @ddt.data({'terminationType': 'FORCEFUL'},
              {'terminationType': 'GRACEFUL'},
              {'terminationType': 'GRACEFUL',
               'gracefulTerminationTimeout': 10})
    def test_terminate(self, body, mock_terminate, mock_save,
                       mock_get_by_id, mock_get_vnf,
                       mock_notification_process,
                       mock_get_service_plugins):
        vnf_instance_obj = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED)
        mock_get_by_id.return_value = vnf_instance_obj
        mock_get_vnf.return_value = \
            self._get_dummy_vnf(vnf_id=vnf_instance_obj.id, status='ACTIVE')

        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/terminate' % uuidsentinel.vnf_instance_id)
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        resp = req.get_response(self.app)
        self.assertEqual(http_client.ACCEPTED, resp.status_code)
        mock_terminate.assert_called_once()
        mock_get_vnf.assert_called_once()
        mock_notification_process.assert_called_once()

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM':
                       test_nfvo_plugin.FakeVNFMPlugin()})
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
    def test_terminate_with_invalid_request_body(
            self, values, mock_get_service_plugins):
        attribute = values['attribute']
        value = values['value']
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/terminate' % uuidsentinel.vnf_instance_id)
        body = {'terminationType': 'GRACEFUL',
                'gracefulTerminationTimeout': 10}
        body.update({attribute: value})
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        expected_message = ("Invalid input for field/attribute {attribute}. "
                            "Value: {value}.".
                            format(value=value, attribute=attribute))

        exception = self.assertRaises(exceptions.ValidationError,
                                      self.controller.terminate,
                                      req, constants.UUID, body=body)
        self.assertIn(expected_message, exception.msg)

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM':
                       test_nfvo_plugin.FakeVNFMPlugin()})
    def test_terminate_missing_termination_type(self,
                                                mock_get_service_plugins):
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

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM':
                       test_nfvo_plugin.FakeVNFMPlugin()})
    @ddt.data('GET', 'HEAD', 'PUT', 'DELETE', 'PATCH')
    def test_terminate_invalid_http_method(self, method,
                                           mock_get_service_plugins):
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

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM':
                       test_nfvo_plugin.FakeVNFMPlugin()})
    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._get_vnf')
    @mock.patch.object(objects.vnf_instance, "_vnf_instance_get_by_id")
    def test_terminate_non_existing_vnf_instance(
            self, mock_vnf_by_id, mock_get_vnf, mock_get_service_plugins):
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
        mock_get_vnf.assert_called_once()

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM':
                       test_nfvo_plugin.FakeVNFMPlugin()})
    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._get_vnf')
    @mock.patch.object(objects.vnf_instance, "_vnf_instance_get_by_id")
    def test_terminate_incorrect_instantiation_state(
            self, mock_vnf_by_id, mock_get_vnf, mock_get_service_plugins):
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
        mock_get_vnf.assert_called_once()

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM':
                       test_nfvo_plugin.FakeVNFMPlugin()})
    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._get_vnf')
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    def test_terminate_incorrect_task_state(
            self,
            mock_vnf_by_id,
            mock_get_vnf,
            mock_get_service_plugins):
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
        mock_get_vnf.assert_called_once()

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM':
                       test_nfvo_plugin.FakeVNFMPlugin()})
    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._notification_process')
    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._get_vnf')
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch.object(vnf_lcm_rpc.VNFLcmRPCAPI, "heal")
    @ddt.data({'cause': 'healing'}, {})
    def test_heal(self, body, mock_rpc_heal, mock_save,
                  mock_vnf_by_id, mock_get_vnf,
                  mock_heal_notif_process,
                  mock_get_service_plugins):
        vnf_instance_obj = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED)
        mock_vnf_by_id.return_value = vnf_instance_obj
        mock_get_vnf.return_value = \
            self._get_dummy_vnf(vnf_id=vnf_instance_obj.id, status='ACTIVE')

        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/heal' % uuidsentinel.vnf_instance_id)
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        resp = req.get_response(self.app)

        self.assertEqual(http_client.ACCEPTED, resp.status_code)
        mock_rpc_heal.assert_called_once()

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM':
                       test_nfvo_plugin.FakeVNFMPlugin()})
    def test_heal_cause_max_length_exceeded(self,
                                            mock_get_service_plugins):
        body = {'cause': 'A' * 256}
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/heal' % uuidsentinel.vnf_instance_id)
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        resp = req.get_response(self.app)
        self.assertEqual(http_client.BAD_REQUEST, resp.status_code)

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM':
                       test_nfvo_plugin.FakeVNFMPlugin()})
    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._notification_process')
    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._get_vnf')
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    def test_heal_incorrect_instantiated_state(
            self,
            mock_vnf_by_id,
            mock_get_vnf,
            mock_notif,
            mock_get_service_plugins):
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

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM':
                       test_nfvo_plugin.FakeVNFMPlugin()})
    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._notification_process')
    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._get_vnf')
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    def test_heal_incorrect_task_state(self, mock_vnf_by_id, mock_get_vnf,
                                       mock_notif, mock_get_service_plugins):
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

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM':
                       test_nfvo_plugin.FakeVNFMPlugin()})
    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._notification_process')
    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._get_vnf')
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    def test_heal_with_invalid_vnfc_id(
            self,
            mock_vnf_by_id,
            mock_get_vnf,
            mock_notif,
            mock_get_service_plugins):
        vnf_instance_obj = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED)
        mock_vnf_by_id.return_value = vnf_instance_obj
        mock_get_vnf.return_value = \
            self._get_dummy_vnf(vnf_id=vnf_instance_obj.id, status='ACTIVE')

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
                                         uuidsentinel.vnf_instance_id),
                         resp.json['badRequest']['message'])

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM':
                       test_nfvo_plugin.FakeVNFMPlugin()})
    @ddt.data('HEAD', 'PUT', 'DELETE', 'PATCH', 'GET')
    def test_heal_invalid_http_method(self, method,
                                      mock_get_service_plugins):
        body = {}
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/heal' % uuidsentinel.vnf_instance_id)
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = method

        resp = req.get_response(self.app)

        self.assertEqual(http_client.METHOD_NOT_ALLOWED, resp.status_code)

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM':
                       test_nfvo_plugin.FakeVNFMPlugin()})
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
            self, mock_get_service_plugins, attribute, value, expected_type):
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

    @mock.patch.object(objects.VnfInstanceList, "get_by_filters")
    def test_index_empty_response(self, mock_vnf_list):
        req = fake_request.HTTPRequest.blank('/vnf_instances')
        mock_vnf_list.return_value = []
        resp = self.controller.index(req)
        self.assertEqual([], resp)

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM':
                       test_nfvo_plugin.FakeVNFMPlugin()})
    @ddt.data('HEAD', 'PUT', 'DELETE', 'PATCH')
    def test_index_invalid_http_method(self, method,
                                       mock_get_service_plugins):
        # Wrong HTTP method
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances')
        req.headers['Content-Type'] = 'application/json'
        req.method = method
        resp = req.get_response(self.app)
        self.assertEqual(http_client.METHOD_NOT_ALLOWED, resp.status_code)

    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._delete')
    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM':
                       test_nfvo_plugin.FakeVNFMPlugin()})
    @mock.patch.object(objects.vnf_instance, "_vnf_instance_get_by_id")
    @mock.patch.object(objects.vnf_instance, '_destroy_vnf_instance')
    def test_delete(self, mock_destroy_vnf_instance, mock_vnf_by_id,
            mock_get_service_plugins, mock_private_delete):
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s' % uuidsentinel.vnf_instance_id)
        req.method = 'DELETE'
        mock_vnf_by_id.return_value = fakes.return_vnf_instance()
        req.headers['Content-Type'] = 'application/json'

        # Call delete API
        resp = req.get_response(self.app)

        self.assertEqual(http_client.NO_CONTENT, resp.status_code)

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM':
                       test_nfvo_plugin.FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    def test_delete_with_non_existing_vnf_instance(self, mock_vnf_by_id,
                                                   mock_get_service_plugins):
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

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM':
                       test_nfvo_plugin.FakeVNFMPlugin()})
    def test_delete_with_invalid_uuid(self, mock_get_service_plugins):
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s' % constants.INVALID_UUID)
        req.method = 'DELETE'

        # Call delete API
        resp = req.get_response(self.app)

        self.assertEqual(http_client.NOT_FOUND, resp.status_code)
        self.assertEqual("Can not find requested vnf instance: %s" %
                         constants.INVALID_UUID,
                         resp.json['itemNotFound']['message'])

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM':
                       test_nfvo_plugin.FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    def test_delete_with_incorrect_instantiation_state(
            self, mock_vnf_by_id, mock_get_service_plugins):
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

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM':
                       test_nfvo_plugin.FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    def test_delete_with_incorrect_task_state(self, mock_vnf_by_id,
                                              mock_get_service_plugins):
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
        query = urllib.parse.urlencode(filter_params)

        req = fake_request.HTTPRequest.blank(
            '/vnflcm/v1/vnf_instances?' + query)

        vnf_instance_1 = fakes.return_vnf_instance()
        vnf_instance_2 = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED)

        mock_vnf_list.return_value = [vnf_instance_1, vnf_instance_2]
        res_dict = self.controller.index(req)

        expected_result = [fakes.fake_vnf_instance_response(),
            fakes.fake_vnf_instance_response(
            fields.VnfInstanceState.INSTANTIATED)]
        self.assertEqual(expected_result, res_dict)

    @mock.patch.object(objects.VnfInstanceList, "get_by_filters")
    def test_index_filter_combination(self, mock_vnf_list):
        """Test multiple filter parameters separated by semicolon."""
        params = {
            'filter': "(eq,vnfInstanceName,'dummy_name');"
                      "(eq,vnfInstanceDescription,'dummy_desc')"}

        query = urllib.parse.urlencode(params)
        req = fake_request.HTTPRequest.blank(
            '/vnflcm/v1/vnf_instances?' + query)

        vnf_instance_1 = fakes.return_vnf_instance()
        vnf_instance_2 = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED)

        mock_vnf_list.return_value = [vnf_instance_1, vnf_instance_2]
        res_dict = self.controller.index(req)

        expected_result = [fakes.fake_vnf_instance_response(),
            fakes.fake_vnf_instance_response(
            fields.VnfInstanceState.INSTANTIATED)]
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
        query = urllib.parse.urlencode(filter_params)
        req = fake_request.HTTPRequest.blank(
            '/vnflcm/v1/vnf_instances?' + query)

        vnf_instance_1 = fakes.return_vnf_instance()
        vnf_instance_2 = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED)

        mock_vnf_list.return_value = [vnf_instance_1, vnf_instance_2]
        res_dict = self.controller.index(req)

        expected_result = [fakes.fake_vnf_instance_response(),
            fakes.fake_vnf_instance_response(
            fields.VnfInstanceState.INSTANTIATED)]
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
        query = urllib.parse.urlencode(filter_params)
        req = fake_request.HTTPRequest.blank(
            '/vnflcm/v1/vnf_instances?' + query)

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
        query = urllib.parse.urlencode(filter_params)
        req = fake_request.HTTPRequest.blank(
            '/vnflcm/v1/vnf_instances?' + query)
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
        query = urllib.parse.urlencode(filter_params)
        req = fake_request.HTTPRequest.blank(
            '/vnflcm/v1/vnf_instances?' + query)
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
        query = urllib.parse.urlencode(filter_params)
        req = fake_request.HTTPRequest.blank(
            '/vnflcm/v1/vnf_instances?' + query)
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
        query = urllib.parse.urlencode(filter_params)
        req = fake_request.HTTPRequest.blank(
            '/vnflcm/v1/vnf_instances?' + query)
        self.assertRaises(exceptions.ValidationError,
                          self.controller.index, req)

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfLcmOpOcc, "get_by_id")
    def test_show_lcm_op_occs(self, mock_get_by_id,
            mock_get_service_plugins):
        req = fake_request.HTTPRequest.blank(
            '/vnf_lcm_op_occs/%s' % constants.UUID)
        mock_get_by_id.return_value = fakes.return_vnf_lcm_opoccs_obj()
        expected_result = fakes.VNFLCMOPOCC_RESPONSE
        res_dict = self.controller.show_lcm_op_occs(req, constants.UUID)
        self.assertEqual(expected_result, res_dict)

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfLcmOpOcc, "get_by_id")
    def test_show_lcm_op_occs_not_found(self, mock_get_by_id,
            mock_get_service_plugins):
        req = fake_request.HTTPRequest.blank(
            '/vnfpkgm/v1/vnf_packages/%s' % constants.UUID)
        mock_get_by_id.side_effect = exceptions.NotFound()

        req.headers['Content-Type'] = 'application/json'
        req.method = 'GET'
        resp = req.get_response(self.app)

        self.assertEqual(http_client.NOT_FOUND, resp.status_code)

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM':
                       test_nfvo_plugin.FakeVNFMPlugin()})
    @mock.patch.object(objects.VNF, "vnf_index_list")
    @mock.patch.object(objects.VnfInstanceList, "vnf_instance_list")
    @mock.patch.object(objects.VnfPackageVnfd, 'get_vnf_package_vnfd')
    @mock.patch.object(vnf_lcm_rpc.VNFLcmRPCAPI, "update")
    def test_update_vnf(
            self,
            mock_update,
            mock_vnf_package_vnf_get_vnf_package_vnfd,
            mock_vnf_instance_list,
            mock_vnf_index_list,
            mock_get_service_plugins):

        mock_vnf_index_list.return_value = fakes._get_vnf()
        mock_vnf_instance_list.return_value = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED)
        mock_vnf_package_vnf_get_vnf_package_vnfd.return_value =\
            fakes.return_vnf_package_vnfd()

        body = {"vnfInstanceName": "new_instance_name",
                "vnfInstanceDescription": "new_instance_discription",
                "vnfdId": "2c69a161-0000-4b0f-bcf8-391f8fc76600",
                "vnfConfigurableProperties": {
                    "test": "test_value"
                },
                "vnfcInfoModificationsDeleteIds": ["test1"],
                "metadata": {"testkey": "test_value"},
                "vimConnectionInfo": {"id": "testid"}}
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s' % constants.UUID)
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'PATCH'

        # Call Instantiate API
        resp = req.get_response(self.app)
        self.assertEqual(http_client.ACCEPTED, resp.status_code)
        mock_update.assert_called_once()

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM':
                       test_nfvo_plugin.FakeVNFMPlugin()})
    @mock.patch.object(objects.VNF, "vnf_index_list")
    def test_update_vnf_none_vnf_data(
            self,
            mock_vnf_index_list,
            mock_get_service_plugins):

        mock_vnf_index_list.return_value = None

        body = {"vnfInstanceName": "new_instance_name",
                "vnfInstanceDescription": "new_instance_discription",
                "vnfdId": "2c69a161-0000-4b0f-bcf8-391f8fc76600",
                "vnfConfigurableProperties": {
                    "test": "test_value"
                },
                "vnfcInfoModificationsDeleteIds": ["test1"],
                "metadata": {"testkey": "test_value"},
                "vimConnectionInfo": {"id": "testid"}}
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s' % constants.UUID)
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'PATCH'

        msg = _("Can not find requested vnf data: %s") % constants.UUID
        res = self._make_problem_detail(msg, 404, title='Not Found')

        resp = req.get_response(self.app)
        self.assertEqual(res.text, resp.text)

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM':
                       test_nfvo_plugin.FakeVNFMPlugin()})
    @mock.patch.object(objects.VNF, "vnf_index_list")
    def test_update_vnf_status_err(
            self,
            mock_vnf_index_list,
            mock_get_service_plugins):
        updates = {'status': 'ERROR'}
        mock_vnf_index_list.return_value = fakes._get_vnf(**updates)

        body = {"vnfInstanceName": "new_instance_name",
                "vnfInstanceDescription": "new_instance_discription",
                "vnfdId": "2c69a161-0000-4b0f-bcf8-391f8fc76600",
                "vnfConfigurableProperties": {
                    "test": "test_value"
                },
                "vnfcInfoModificationsDeleteIds": ["test1"],
                "metadata": {"testkey": "test_value"},
                "vimConnectionInfo": {"id": "testid"}}
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s' % constants.UUID)
        req.body = jsonutils.dump_as_bytes(body)

        req.headers['Content-Type'] = 'application/json'
        req.method = 'PATCH'

        msg = _("VNF %(id)s status is %(state)s") % {
            "id": constants.UUID, "state": "ERROR"}
        res = self._make_problem_detail(msg %
                                        {"state": "ERROR"}, 409, 'Conflict')

        resp = req.get_response(self.app)
        self.assertEqual(res.text, resp.text)

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM':
                       test_nfvo_plugin.FakeVNFMPlugin()})
    @mock.patch.object(objects.VNF, "vnf_index_list")
    @mock.patch.object(objects.VnfInstanceList, "vnf_instance_list")
    def test_update_vnf_none_instance_data(
            self,
            mock_vnf_instance_list,
            mock_vnf_index_list,
            mock_get_service_plugins):

        mock_vnf_index_list.return_value = fakes._get_vnf()
        mock_vnf_instance_list.return_value = ""

        body = {"vnfInstanceName": "new_instance_name",
                "vnfInstanceDescription": "new_instance_discription",
                "vnfdId": "2c69a161-0000-4b0f-bcf8-391f8fc76600",
                "vnfConfigurableProperties": {
                    "test": "test_value"
                },
                "vnfcInfoModificationsDeleteIds": ["test1"],
                "metadata": {"testkey": "test_value"},
                "vimConnectionInfo": {"id": "testid"}}
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s' % constants.UUID)
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'PATCH'

        vnf_data = fakes._get_vnf()
        msg = ("Can not find requested vnf instance data: %s") % vnf_data.get(
            'vnfd_id')
        res = self._make_problem_detail(msg, 404, title='Not Found')

        resp = req.get_response(self.app)
        self.assertEqual(res.text, resp.text)

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM':
                       test_nfvo_plugin.FakeVNFMPlugin()})
    @mock.patch.object(sync_resource.SyncVnfPackage, 'create_package')
    @mock.patch.object(objects.vnf_package_vnfd.VnfPackageVnfd,
    "get_vnf_package_vnfd")
    @mock.patch.object(nfvo_client.VnfPackageRequest, "index")
    @mock.patch.object(objects.VNF, "vnf_index_list")
    @mock.patch.object(objects.VnfInstanceList, "vnf_instance_list")
    @mock.patch.object(objects.VnfPackageVnfd, 'get_vnf_package_vnfd')
    @mock.patch.object(vnf_lcm_rpc.VNFLcmRPCAPI, "update")
    def test_update_vnf_none_vnfd(
            self,
            mock_update,
            mock_vnf_package_vnf_get_vnf_package_vnfd,
            mock_vnf_instance_list,
            mock_vnf_index_list,
            mock_index,
            mock_get_vnf_package_vnfd,
            mock_create_package,
            mock_get_service_plugins):

        mock_vnf_index_list.return_value = fakes._get_vnf()
        mock_vnf_instance_list.return_value = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED)
        mock_vnf_package_vnf_get_vnf_package_vnfd.return_value = ""
        mock_get_vnf_package_vnfd.side_effect =\
            exceptions.VnfPackageVnfdNotFound
        mock_create_package.return_value = fakes.return_vnf_package_vnfd()
        mock_response = mock.MagicMock()
        mock_response.ok = True
        mock_response.json = mock.MagicMock()
        mock_response.json.return_value = ['aaa', 'bbb', 'ccc']

        mock_index.return_value = mock_response

        body = {"vnfInstanceName": "new_instance_name",
    "vnfInstanceDescription": "new_instance_discription",
    "vnfPkgId": "2c69a161-0000-4b0f-bcf8-391f8fc76600",
    "vnfConfigurableProperties": {"test": "test_value"},
     "vnfcInfoModificationsDeleteIds": ["test1"]}
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s' % constants.UUID)
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'PATCH'

        resp = req.get_response(self.app)
        self.assertEqual(http_client.ACCEPTED, resp.status_code)
        mock_update.assert_called_once()

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM':
                       test_nfvo_plugin.FakeVNFMPlugin()})
    @mock.patch.object(objects.VNF, "vnf_index_list")
    @mock.patch.object(objects.VnfInstanceList, "vnf_instance_list")
    @mock.patch.object(objects.VnfPackageVnfd, 'get_vnf_package_vnfd')
    @mock.patch.object(vnf_lcm_rpc.VNFLcmRPCAPI, "update")
    def test_update_vnf_with_pkg_id(
            self, mock_update,
            mock_vnf_package_vnf_get_vnf_package_vnfd,
            mock_vnf_instance_list, mock_vnf_index_list,
            mock_get_service_plugins):

        mock_vnf_index_list.return_value = fakes._get_vnf()
        mock_vnf_instance_list.return_value = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED)
        mock_vnf_package_vnf_get_vnf_package_vnfd.return_value =\
            fakes.return_vnf_package_vnfd()

        body = {"vnfInstanceName": "new_instance_name",
                "vnfInstanceDescription": "new_instance_discription",
                "vnfPkgId": "2c69a161-0000-4b0f-bcf8-391f8fc76600",
                "vnfConfigurableProperties": {"test": "test_value"},
                "vnfcInfoModificationsDeleteIds": ["test1"]}
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s' % constants.UUID)
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'PATCH'

        # Call Instantiate API
        resp = req.get_response(self.app)
        self.assertEqual(http_client.ACCEPTED, resp.status_code)
        mock_update.assert_called_once()

    @ddt.data("vnfdId", "vnfPkgId")
    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM':
                       test_nfvo_plugin.FakeVNFMPlugin()})
    @mock.patch.object(sync_resource.SyncVnfPackage, 'create_package')
    @mock.patch.object(objects.vnf_package_vnfd.VnfPackageVnfd,
    "get_vnf_package_vnfd")
    @mock.patch.object(nfvo_client.VnfPackageRequest, "index")
    @mock.patch.object(objects.VNF, "vnf_index_list")
    @mock.patch.object(objects.VnfInstanceList, "vnf_instance_list")
    @mock.patch.object(objects.VnfPackageVnfd, 'get_vnf_package_vnfd')
    @mock.patch.object(vnf_lcm_rpc.VNFLcmRPCAPI, "update")
    def test_update_none_vnf_package_info(
            self, input_id,
            mock_update,
            mock_vnf_package_vnf_get_vnf_package_vnfd,
            mock_vnf_instance_list,
            mock_vnf_index_list,
            mock_index,
            mock_get_vnf_package_vnfd,
            mock_create_package,
            mock_get_service_plugins):

        mock_vnf_index_list.return_value = fakes._get_vnf()
        mock_vnf_instance_list.return_value = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED)
        mock_vnf_package_vnf_get_vnf_package_vnfd.return_value = ""
        mock_get_vnf_package_vnfd.side_effect =\
            exceptions.VnfPackageVnfdNotFound
        mock_create_package.return_value = fakes.return_vnf_package_vnfd()
        mock_response = mock.MagicMock()
        mock_response.ok = False
        mock_response.json = mock.MagicMock()
        mock_response.json.return_value = ['aaa', 'bbb', 'ccc']

        mock_index.return_value = mock_response

        body = {"vnfInstanceName": "new_instance_name",
    "vnfInstanceDescription": "new_instance_discription",
    input_id: "2c69a161-0000-4b0f-bcf8-391f8fc76600",
    "vnfConfigurableProperties": {"test": "test_value"},
     "vnfcInfoModificationsDeleteIds": ["test1"]}
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s' % constants.UUID)
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'PATCH'

        resp = req.get_response(self.app)
        self.assertEqual(http_client.BAD_REQUEST, resp.status_code)

    @ddt.data("vnfdId", "vnfPkgId")
    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM':
                       test_nfvo_plugin.FakeVNFMPlugin()})
    @mock.patch.object(sync_resource.SyncVnfPackage, 'create_package')
    @mock.patch.object(objects.vnf_package_vnfd.VnfPackageVnfd,
    "get_vnf_package_vnfd")
    @mock.patch.object(nfvo_client.VnfPackageRequest, "index")
    @mock.patch.object(objects.VNF, "vnf_index_list")
    @mock.patch.object(objects.VnfInstanceList, "vnf_instance_list")
    @mock.patch.object(objects.VnfPackageVnfd, 'get_vnf_package_vnfd')
    @mock.patch.object(vnf_lcm_rpc.VNFLcmRPCAPI, "update")
    def test_update_none_vnf_package_vnfd(
            self, input_id,
            mock_update,
            mock_vnf_package_vnf_get_vnf_package_vnfd,
            mock_vnf_instance_list,
            mock_vnf_index_list,
            mock_index,
            mock_get_vnf_package_vnfd,
            mock_create_package,
            mock_get_service_plugins):

        mock_vnf_index_list.return_value = fakes._get_vnf()
        mock_vnf_instance_list.return_value = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED)
        mock_vnf_package_vnf_get_vnf_package_vnfd.return_value = ""
        mock_get_vnf_package_vnfd.return_value = None
        mock_create_package.return_value = None
        mock_response = mock.MagicMock()
        mock_response.ok = True
        mock_response.json = mock.MagicMock()
        mock_response.json.return_value = ['aaa', 'bbb', 'ccc']

        mock_index.return_value = mock_response

        body = {"vnfInstanceName": "new_instance_name",
    "vnfInstanceDescription": "new_instance_discription",
    input_id: "2c69a161-0000-4b0f-bcf8-391f8fc76600",
    "vnfConfigurableProperties": {"test": "test_value"},
     "vnfcInfoModificationsDeleteIds": ["test1"]}
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s' % constants.UUID)
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'PATCH'

        resp = req.get_response(self.app)
        self.assertEqual(http_client.INTERNAL_SERVER_ERROR, resp.status_code)

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    def test_scale_not_scale_err(
            self,
            mock_vnf_instance_get_by_id,
            mock_get_service_plugins):
        mock_vnf_instance_get_by_id.return_value =\
            fakes.return_vnf_instance(fields.VnfInstanceState.INSTANTIATED)

        body = {
            "type": "SCALE_OUT",
            "aspectId": "SP1",
            "numberOfSteps": 1,
            "additionalParams": {
                "test": "test_value"}}
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/scale' %
            constants.UUID)
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'
        res = self._make_problem_detail(
            'NOT SCALE VNF', 409, title='NOT SCALE VNF')
        resp = req.get_response(self.app)
        self.assertEqual(res.text, resp.text)

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    def test_scale_not_active_err(self,
            mock_get_service_plugins):

        body = {
            "type": "SCALE_OUT",
            "aspectId": "SP1",
            "numberOfSteps": 1,
            "additionalParams": {
                "test": "test_value"}}
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/scale' %
            '91e32c20-6d1f-47a4-9ba7-08f5e5effe07')
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'
        res = self._make_problem_detail(
            'VNF IS NOT ACTIVE', 409, title='VNF IS NOT ACTIVE')
        resp = req.get_response(self.app)
        self.assertEqual(res.text, resp.text)

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    def test_scale_vnfnotfound_err(self,
            mock_get_service_plugins):
        msg = _('VNF %(vnf_id)s could not be found')

        body = {
            "type": "SCALE_OUT",
            "aspectId": "SP1",
            "numberOfSteps": 1,
            "additionalParams": {
                "test": "test_value"}}
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/scale' %
            '7168062e-9fa1-4203-8cb7-f5c99ff3ee1b')
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        res = self._make_problem_detail(msg, 404, title='VNF NOT FOUND')
        resp = req.get_response(self.app)
        self.assertEqual(res.text, resp.text)

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfLcmOpOcc, "create")
    @mock.patch.object(objects.ScaleVnfRequest, "obj_from_primitive")
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    @mock.patch.object(tacker.db.vnfm.vnfm_db.VNFMPluginDb, "get_vnf")
    @mock.patch.object(vnf_lcm_rpc.VNFLcmRPCAPI, "scale")
    @mock.patch.object(vnf_lcm_rpc.VNFLcmRPCAPI, "send_notification")
    def test_scale_in(
            self,
            mock_send_notification,
            mock_scale,
            mock_get_vnf,
            mock_vnf_instance_get_by_id,
            mock_obj_from_primitive,
            mock_create,
            mock_get_service_plugins):

        mock_get_vnf.return_value = fakes._get_vnf()
        mock_vnf_instance_get_by_id.return_value = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED, scale_status="scale_status")
        mock_obj_from_primitive.return_value = fakes.scale_request_make(
            "SCALE_IN", 1)
        mock_create.return_value = 200

        body = {
            "type": "SCALE_IN",
            "aspectId": "SP1",
            "numberOfSteps": 1,
            "additionalParams": {
                "test": "test_value"}}
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/scale' %
            constants.UUID)
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'
        resp = req.get_response(self.app)
        self.assertEqual(http_client.ACCEPTED, resp.status_code)
        mock_scale.assert_called_once()

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfLcmOpOcc, "create")
    @mock.patch.object(objects.ScaleVnfRequest, "obj_from_primitive")
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    @mock.patch.object(tacker.db.vnfm.vnfm_db.VNFMPluginDb, "get_vnf")
    @mock.patch.object(vnf_lcm_rpc.VNFLcmRPCAPI, "scale")
    @mock.patch.object(vnf_lcm_rpc.VNFLcmRPCAPI, "send_notification")
    def test_scale_out(
            self,
            mock_send_notification,
            mock_scale,
            mock_get_vnf,
            mock_vnf_instance_get_by_id,
            mock_obj_from_primitive,
            mock_create,
            mock_get_service_plugins):

        mock_get_vnf.return_value = fakes._get_vnf()
        mock_vnf_instance_get_by_id.return_value = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED, scale_status="scale_status")
        mock_obj_from_primitive.return_value = fakes.scale_request_make(
            "SCALE_OUT", 1)
        mock_create.return_value = 200

        body = {
            "type": "SCALE_OUT",
            "aspectId": "SP1",
            "numberOfSteps": 1,
            "additionalParams": {
                "test": "test_value"}}
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/scale' %
            constants.UUID)
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'
        resp = req.get_response(self.app)
        self.assertEqual(http_client.ACCEPTED, resp.status_code)
        mock_scale.assert_called_once()

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfLcmOpOcc, "create")
    @mock.patch.object(objects.ScaleVnfRequest, "obj_from_primitive")
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    @mock.patch.object(tacker.db.vnfm.vnfm_db.VNFMPluginDb, "get_vnf")
    @mock.patch.object(vnf_lcm_rpc.VNFLcmRPCAPI, "scale")
    def test_scale_in_err(
            self,
            mock_scale,
            mock_get_vnf,
            mock_vnf_instance_get_by_id,
            mock_obj_from_primitive,
            mock_create,
            mock_get_service_plugins):

        mock_get_vnf.return_value = fakes._get_vnf()
        mock_vnf_instance_get_by_id.return_value = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED, scale_status="scale_status")
        mock_obj_from_primitive.return_value = fakes.scale_request_make(
            "SCALE_IN", 4)
        mock_create.return_value = 200

        body = {
            "type": "SCALE_IN",
            "aspectId": "SP1",
            "numberOfSteps": 1,
            "additionalParams": {
                "test": "test_value"}}
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/scale' %
            constants.UUID)
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        res = self._make_problem_detail(
            'can not scale_in', 400, title='can not scale_in')
        resp = req.get_response(self.app)
        self.assertEqual(res.text, resp.text)

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfLcmOpOcc, "create")
    @mock.patch.object(objects.ScaleVnfRequest, "obj_from_primitive")
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    @mock.patch.object(tacker.db.vnfm.vnfm_db.VNFMPluginDb, "get_vnf")
    @mock.patch.object(vnf_lcm_rpc.VNFLcmRPCAPI, "scale")
    def test_scale_out_err(
            self,
            mock_scale,
            mock_get_vnf,
            mock_vnf_instance_get_by_id,
            mock_obj_from_primitive,
            mock_create,
            mock_get_service_plugins):

        mock_get_vnf.return_value = fakes._get_vnf()
        mock_vnf_instance_get_by_id.return_value = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED, scale_status="scale_status")
        mock_obj_from_primitive.return_value = fakes.scale_request_make(
            "SCALE_OUT", 4)
        mock_create.return_value = 200

        body = {
            "type": "SCALE_OUT",
            "aspectId": "SP1",
            "numberOfSteps": 1,
            "additionalParams": {
                "test": "test_value"}}
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/scale' %
            constants.UUID)
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        res = self._make_problem_detail(
            'can not scale_out', 400, title='can not scale_out')
        resp = req.get_response(self.app)
        self.assertEqual(res.text, resp.text)

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.ScaleVnfRequest, "obj_from_primitive")
    @mock.patch.object(controller.VnfLcmController, "_get_rollback_vnf")
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    @mock.patch.object(vnf_lcm_rpc.VNFLcmRPCAPI, "send_notification")
    @mock.patch.object(objects.VnfLcmOpOcc, "create")
    def test_scale_notification(
            self,
            mock_create,
            mock_send_notification,
            mock_vnf_instance,
            mock_get_vnf,
            mock_obj_from_primitive,
            get_service_plugins):
        body = {"type": "SCALE_OUT", "aspect_id": "SP1"}
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/scale' % uuidsentinel.vnf_instance_id)
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        vnf_obj = fakes.vnf_scale()
        mock_obj_from_primitive.return_value = fakes.scale_request_make(
            "SCALE_IN", 1)
        mock_get_vnf.return_value = vnf_obj

        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED,
            scale_status="scale_status")

        vnf_instance.instantiated_vnf_info.instance_id =\
            uuidsentinel.instance_id
        vnf_instance.instantiated_vnf_info.vnf_instance_id =\
            uuidsentinel.vnf_instance_id
        vnf_instance.instantiated_vnf_info.scale_status = []
        vnf_instance.instantiated_vnf_info.scale_status.append(
            objects.ScaleInfo(aspect_id='SP1', scale_level=0))
        mock_vnf_instance.return_value = vnf_instance

        vnf_info = fakes._get_vnf()
        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED, scale_status="scale_status")
        self.controller._scale(self.context,
            vnf_info, vnf_instance, body)

        mock_send_notification.assert_called_once()
        self.assertEqual(mock_send_notification.call_args[0][1].get(
            'notificationType'), 'VnfLcmOperationOccurrenceNotification')
        self.assertEqual(
            mock_send_notification.call_args[0][1].get('vnfInstanceId'),
            vnf_instance.instantiated_vnf_info.vnf_instance_id)
        self.assertEqual(mock_send_notification.call_args[0][1].get(
            'notificationStatus'), 'START')
        self.assertEqual(
            mock_send_notification.call_args[0][1].get('operation'),
            'SCALE')
        self.assertEqual(
            mock_send_notification.call_args[0][1].get('operationState'),
            'STARTING')
        self.assertEqual(mock_send_notification.call_args[0][1].get(
            'isAutomaticInvocation'), 'False')

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfLcmOpOcc, "get_by_id")
    @mock.patch.object(controller.VnfLcmController, "_get_rollback_vnf")
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    @mock.patch.object(vnf_lcm_rpc.VNFLcmRPCAPI, "rollback")
    def test_rollback(
            self,
            mock_rollback,
            mock_vnf_instance,
            mock_get_vnf,
            mock_lcm_by_id,
            mock_get_service_plugins):
        req = fake_request.HTTPRequest.blank(
            '/vnf_lcm_op_occs/%s/rollback' % uuidsentinel.vnf_instance_id)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        vnf_lcm_op_occs = fakes.vnflcm_rollback()
        mock_lcm_by_id.return_value = vnf_lcm_op_occs
        vnf_obj = fakes.vnf_rollback()
        mock_get_vnf.return_value = vnf_obj

        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.NOT_INSTANTIATED,
            task_state=fields.VnfInstanceTaskState.ERROR)
        mock_vnf_instance.return_value = vnf_instance

        resp = req.get_response(self.app)
        self.assertEqual(http_client.ACCEPTED, resp.status_code)
        mock_rollback.assert_called_once()

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfLcmOpOcc, "get_by_id")
    @mock.patch.object(controller.VnfLcmController, "_get_rollback_vnf")
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    @mock.patch.object(vnf_lcm_rpc.VNFLcmRPCAPI, "rollback")
    def test_rollback_2(
            self,
            mock_rollback,
            mock_vnf_instance,
            mock_get_vnf,
            mock_lcm_by_id,
            mock_get_service_plugins):
        req = fake_request.HTTPRequest.blank(
            '/vnf_lcm_op_occs/%s/rollback' % uuidsentinel.vnf_instance_id)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        vnf_lcm_op_occs = fakes.vnflcm_rollback_insta()
        mock_lcm_by_id.return_value = vnf_lcm_op_occs
        vnf_obj = fakes.vnf_rollback()
        mock_get_vnf.return_value = vnf_obj

        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.NOT_INSTANTIATED,
            task_state=fields.VnfInstanceTaskState.ERROR)
        mock_vnf_instance.return_value = vnf_instance

        resp = req.get_response(self.app)
        self.assertEqual(http_client.ACCEPTED, resp.status_code)
        mock_rollback.assert_called_once()

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    def test_rollback_vnf_lcm_op_occs_access_error(self,
            mock_get_service_plugins):
        req = fake_request.HTTPRequest.blank(
            '/vnf_lcm_op_occs/%s/rollback' % uuidsentinel.vnf_instance_id)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        resp = req.get_response(self.app)
        self.assertEqual(500, resp.status_code)

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfLcmOpOcc, "get_by_id")
    def test_rollback_lcm_not_found(self, mock_lcm_by_id,
            mock_get_service_plugins):
        req = fake_request.HTTPRequest.blank(
            '/vnf_lcm_op_occs/%s/rollback' % constants.INVALID_UUID)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        mock_lcm_by_id.side_effect = exceptions.NotFound(resource='table',
                                  name='vnf_lcm_op_occs')

        resp = req.get_response(self.app)
        self.assertEqual(http_client.NOT_FOUND, resp.status_code)

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfLcmOpOcc, "get_by_id")
    def test_rollback_not_failed_temp(self, mock_lcm_by_id,
            mock_get_service_plugins):
        req = fake_request.HTTPRequest.blank(
            '/vnf_lcm_op_occs/%s/rollback' % uuidsentinel.vnf_instance_id)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        vnf_lcm_op_occs = fakes.vnflcm_rollback_active()
        mock_lcm_by_id.return_value = vnf_lcm_op_occs

        resp = req.get_response(self.app)
        self.assertEqual(http_client.CONFLICT, resp.status_code)

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfLcmOpOcc, "get_by_id",)
    def test_rollback_not_ope(self, mock_lcm_by_id,
            mock_get_service_plugins):
        req = fake_request.HTTPRequest.blank(
            '/vnf_lcm_op_occs/%s/rollback' % uuidsentinel.vnf_instance_id)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        vnf_lcm_op_occs = fakes.vnflcm_rollback_ope()
        mock_lcm_by_id.return_value = vnf_lcm_op_occs

        resp = req.get_response(self.app)
        self.assertEqual(http_client.CONFLICT, resp.status_code)

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfLcmOpOcc, "get_by_id")
    def test_rollback_not_scale_in(self, mock_lcm_by_id,
            mock_get_service_plugins):
        req = fake_request.HTTPRequest.blank(
            '/vnf_lcm_op_occs/%s/rollback' % uuidsentinel.vnf_instance_id)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        vnf_lcm_op_occs = fakes.vnflcm_rollback_scale_in()
        mock_lcm_by_id.return_value = vnf_lcm_op_occs

        resp = req.get_response(self.app)
        self.assertEqual(http_client.CONFLICT, resp.status_code)

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(controller.VnfLcmController, "_get_rollback_vnf")
    @mock.patch.object(objects.VnfLcmOpOcc, "get_by_id")
    def test_rollback_vnf_error(self, mock_lcm_by_id, mock_get_vnf,
            mock_get_service_plugins):
        req = fake_request.HTTPRequest.blank(
            '/vnf_lcm_op_occs/%s/rollback' % uuidsentinel.vnf_instance_id)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        vnf_lcm_op_occs = fakes.vnflcm_rollback_insta()
        mock_lcm_by_id.return_value = vnf_lcm_op_occs
        mock_get_vnf.side_effect = Exception("error")

        resp = req.get_response(self.app)
        self.assertEqual(500, resp.status_code)

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfLcmOpOcc, "get_by_id")
    @mock.patch.object(controller.VnfLcmController, "_get_rollback_vnf")
    def test_rollback_vnf_not_found(self, mock_get_vnf, mock_lcm_by_id,
            mock_get_service_plugins):
        req = fake_request.HTTPRequest.blank(
            '/vnf_lcm_op_occs/%s/rollback' % uuidsentinel.vnf_instance_id)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        vnf_lcm_op_occs = fakes.vnflcm_rollback_insta()
        mock_lcm_by_id.return_value = vnf_lcm_op_occs
        mock_get_vnf.side_effect = vnfm.VNFNotFound(
            vnf_id=uuidsentinel.vnf_instance_id)

        resp = req.get_response(self.app)
        self.assertEqual(http_client.NOT_FOUND, resp.status_code)

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfLcmOpOcc, "get_by_id")
    @mock.patch.object(controller.VnfLcmController, "_get_rollback_vnf")
    def test_rollback_vnf_instance_error(self, mock_get_vnf, mock_lcm_by_id,
            mock_get_service_plugins):
        req = fake_request.HTTPRequest.blank(
            '/vnf_lcm_op_occs/%s/rollback' % uuidsentinel.vnf_instance_id)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        vnf_lcm_op_occs = fakes.vnflcm_rollback_insta()
        mock_lcm_by_id.return_value = vnf_lcm_op_occs
        vnf_obj = fakes.vnf_rollback()
        mock_get_vnf.return_value = vnf_obj

        resp = req.get_response(self.app)
        self.assertEqual(500, resp.status_code)

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfLcmOpOcc, "get_by_id")
    @mock.patch.object(controller.VnfLcmController, "_get_rollback_vnf")
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    def test_rollback_vnf_instance_not_found(
            self, mock_vnf_instance, mock_get_vnf, mock_lcm_by_id,
            mock_get_service_plugins):
        req = fake_request.HTTPRequest.blank(
            '/vnf_lcm_op_occs/%s/rollback' % uuidsentinel.vnf_instance_id)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        vnf_lcm_op_occs = fakes.vnflcm_rollback_insta()
        mock_lcm_by_id.return_value = vnf_lcm_op_occs
        vnf_obj = fakes.vnf_rollback()
        mock_get_vnf.return_value = vnf_obj

        mock_vnf_instance.side_effect = vnfm.VNFNotFound(
            vnf_id=uuidsentinel.vnf_instance_id)

        resp = req.get_response(self.app)
        self.assertEqual(http_client.NOT_FOUND, resp.status_code)
