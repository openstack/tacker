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

import codecs
import copy
import ddt
from http import client as http_client
import json
import os
import re
from unittest import mock
import urllib
import webob
from webob import exc

from oslo_config import cfg
from oslo_policy import policy as oslo_policy
from oslo_serialization import jsonutils
from oslo_utils import uuidutils

from tacker.api.views import vnf_subscriptions as vnf_subscription_view
from tacker.api.vnflcm.v1 import controller
from tacker.api.vnflcm.v1 import sync_resource
from tacker.common import exceptions
from tacker.common import utils as common_utils
import tacker.conductor.conductorrpc.vnf_lcm_rpc as vnf_lcm_rpc
from tacker import context
import tacker.db.vnfm.vnfm_db
from tacker.extensions import nfvo
from tacker.extensions import vnfm
from tacker.manager import TackerManager
from tacker import objects
from tacker.objects import fields
from tacker.objects import vnf_lcm_subscriptions as subscription_obj
from tacker.policies import vnf_lcm as vnf_lcm_policies
from tacker import policy
from tacker.tests import constants
from tacker.tests.unit import base
from tacker.tests.unit.db import utils
from tacker.tests.unit import fake_request
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
        self.vnf3_vnfd_id = 'e4015e9f-1ef2-49fb-adb6-070791ad3c45'
        self.vnf3_vnf_id = '7168062e-9fa1-4203-8cb7-f5c99ff3ee1b'
        self.vnf_for_cnf_vnfd_id = 'e889e4fe-52fe-437d-b1e1-a690dc95e3f8'
        self.vnf_for_cnf_vnf_id = '436aaa6e-2db6-4d6e-a3fc-e728b2f0ac56'

    def get_vnfd(self, *args, **kwargs):
        return {'id': self.vnf1_vnfd_id,
                'name': 'dummy VNF',
                'attributes': {'vnfd': "dummy"}}

    def get_vnf(self, *args, **kwargs):
        if self.vnf1_vnf_id in args:
            return self.get_dummy_vnf_error()
        elif self.vnf3_vnf_id in args:
            return self.get_dummy_vnf_not_found_error()
        elif self.vnf_for_cnf_vnf_id in args:
            return fakes.vnf_dict_cnf()
        else:
            return self.get_dummy_vnf_active()

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

    def get_dummy_vnf_not_found_error(self):
        msg = _('VNF %(vnf_id)s could not be found')
        raise vnfm.VNFNotFound(explanation=msg)

    def _update_vnf_scaling(self, *args, **kwargs):
        pass


@ddt.ddt
class TestController(base.TestCase):
    expected_location_prefix = ('http://localhost:9890/'
        'vnflcm/v1/vnf_lcm_op_occs/')

    def setUp(self):
        super(TestController, self).setUp()
        self.patcher = mock.patch(
            'tacker.manager.TackerManager.get_service_plugins',
            return_value={'VNFM': FakeVNFMPlugin()})
        self.mock_manager = self.patcher.start()
        self.controller = controller.VnfLcmController()
        self.vim_info = {
            'vim_id': uuidsentinel.vnfd_id,
            'vim_type': 'test',
            'vim_auth': {'username': 'test', 'password': 'test'},
            'placement_attr': {'region': 'TestRegionOne'},
            'tenant': 'test',
            'extra': {}
        }
        self.context = context.get_admin_context()

        with mock.patch.object(TackerManager, 'get_service_plugins',
                               return_value={'VNFM': FakeVNFMPlugin()}):
            self.controller = controller.VnfLcmController()

    def tearDown(self):
        self.mock_manager.stop()
        super(TestController, self).tearDown()

    @property
    def app(self):
        return fakes.wsgi_app_v1()

    def _get_dummy_vnf(self, vnf_id=None, status=None):
        vnf_dict = utils.get_dummy_vnf_etsi()

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
                       return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.vnf_instance, '_vnf_instance_update')
    @mock.patch.object(objects.vnf_instance, '_vnf_instance_create')
    @mock.patch.object(objects.vnf_package_vnfd.VnfPackageVnfd, 'get_by_id')
    def test_create_without_name_and_description(
            self, mock_get_by_id,
            mock_vnf_instance_create,
            mock_vnf_instance_update,
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
        mock_vnf_instance_update.return_value = \
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
        location_header = ('http://localhost:9890/vnflcm/v1/vnf_instances/%s'
                           % resp.json['id'])

        self.assertEqual(expected_vnf, resp.json)
        self.assertEqual(location_header, resp.headers['location'])

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
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
                                "not of type {expected_type}".
                format(value=value, attribute=attribute,
                       expected_type=expected_type))

        self.assertEqual(expected_message, exception.msg)

    @mock.patch.object(sync_resource.SyncVnfPackage, 'create_package')
    @mock.patch.object(nfvo_client.VnfPackageRequest, "index")
    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
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
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(sync_resource.SyncVnfPackage, 'create_package')
    @mock.patch.object(nfvo_client.VnfPackageRequest, "index")
    @mock.patch.object(objects.vnf_instance, '_vnf_instance_update')
    @mock.patch.object(objects.vnf_instance, '_vnf_instance_create')
    @mock.patch.object(objects.vnf_package_vnfd.VnfPackageVnfd, 'get_by_id')
    def test_create_vnf_package_not_found(
            self, mock_get_by_id_package_vnfd,
            mock_vnf_instance_create,
            mock_vnf_instance_update,
            mock_index, mock_create_pkg,
            mock_get_service_plugins,
            mock_private_create_vnf,
            mock_vnf_package_get_by_id,
            mock_update_package_usage_state,
            mock_get_vim):
        mock_get_vim.return_value = self.vim_info
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
        mock_vnf_instance_update.return_value =\
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
        return_value={'VNFM': FakeVNFMPlugin()})
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
        return_value={'VNFM': FakeVNFMPlugin()})
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
        return_value={'VNFM': FakeVNFMPlugin()})
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
                       return_value={'VNFM': FakeVNFMPlugin()})
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
        return_value={'VNFM': FakeVNFMPlugin()})
    @ddt.data({'name': "A" * 256,
    'description': "VNF Description",
    'meta': {"key": "value"}},
        {'name': 'Fake-VNF',
    'description': "A" * 1025,
    'meta': {"key": "value"}},
        {'name': 'Fake-VNF',
    'description': "VNF Description",
     'meta': {"key": "v" * 1025}})
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
                       return_value={'VNFM': FakeVNFMPlugin()})
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

        vim = fakes.return_default_vim()
        vim.update({'extra': {"area": "area_A@region_A"}})
        mock_get_vim.return_value = vim
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/instantiate' % uuidsentinel.vnf_instance_id)
        mock_vnf_instance_get_by_id.return_value =\
            fakes.return_vnf_instance_model(
                tenant_id=req.environ['tacker.context'].project_id)
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
        body.update({"additionalParams": {"foo_number": 12}})
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        # Call Instantiate API
        resp = req.get_response(self.app)
        self.assertTrue('Location' in resp.headers.keys())
        expected_location = (self.expected_location_prefix +
                    str(mock_insta_notfi_process.return_value))
        self.assertEqual(expected_location, resp.headers['location'])
        self.assertEqual(http_client.ACCEPTED, resp.status_code)
        mock_instantiate.assert_called_once()

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
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

        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/instantiate' % uuidsentinel.vnf_instance_id)

        mock_vnf_instance_get_by_id.return_value =\
            fakes.return_vnf_instance_model(
                tenant_id=req.environ['tacker.context'].project_id)
        mock_vnf_package_vnfd_get_by_id.return_value = \
            fakes.return_vnf_package_vnfd()
        mock_vnf_package_get_by_id.return_value = \
            fakes.return_vnf_package_with_deployment_flavour()
        mock_get_vnf.return_value = \
            self._get_dummy_vnf(
                vnf_id=mock_vnf_instance_get_by_id.return_value.id,
                status='INACTIVE')

        body = {"flavourId": "invalid"}
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        # Call Instantiate API
        resp = req.get_response(self.app)
        self.assertFalse('Location' in resp.headers.keys())
        self.assertEqual(http_client.BAD_REQUEST, resp.status_code)
        self.assertIn('application/problem+json', resp.headers['Content-Type'])
        self.assertEqual("No flavour with id 'invalid'.",
                         resp.json['detail'])
        mock_get_vnf.assert_called_once()

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
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

        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/instantiate' % uuidsentinel.vnf_instance_id)
        vim = fakes.return_default_vim()
        vim.update({'extra': {"area": "area_A@region_A"}})
        mock_get_vim.return_value = vim
        mock_vnf_instance_get_by_id.return_value =\
            fakes.return_vnf_instance_model(
                tenant_id=req.environ['tacker.context'].project_id)
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
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        # Call Instantiate API
        resp = req.get_response(self.app)
        self.assertTrue('Location' in resp.headers.keys())
        expected_location = (self.expected_location_prefix +
                    str(mock_insta_notif_process.return_value))
        self.assertEqual(expected_location, resp.headers['location'])
        self.assertEqual(http_client.ACCEPTED, resp.status_code)
        mock_instantiate.assert_called_once()
        mock_get_vnf.assert_called_once()
        mock_insta_notif_process.assert_called_once()

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
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

        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/instantiate' % uuidsentinel.vnf_instance_id)

        mock_vnf_instance_get_by_id.return_value =\
            fakes.return_vnf_instance_model(
                tenant_id=req.environ['tacker.context'].project_id)
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
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        # Call Instantiate API
        resp = req.get_response(self.app)
        self.assertFalse('Location' in resp.headers.keys())
        self.assertEqual(http_client.BAD_REQUEST, resp.status_code)
        self.assertIn('application/problem+json', resp.headers['Content-Type'])
        self.assertEqual("No instantiation level with id "
                         "'instantiation_level_1'.",
                         resp.json['detail'])
        mock_get_vnf.assert_called_once()

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
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

        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/instantiate' % uuidsentinel.vnf_instance_id)

        mock_vnf_instance_get_by_id.return_value =\
            fakes.return_vnf_instance_model(
                tenant_id=req.environ['tacker.context'].project_id)
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
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        # Call Instantiate API
        resp = req.get_response(self.app)
        self.assertFalse('Location' in resp.headers.keys())
        self.assertEqual(http_client.BAD_REQUEST, resp.status_code)
        self.assertIn('application/problem+json', resp.headers['Content-Type'])
        self.assertEqual("No instantiation level with id 'non-existing'.",
                         resp.json['detail'])
        mock_get_vnf.assert_called_once()

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
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

        vim = fakes.return_default_vim()
        vim.update({'extra': {"area": "area_A@region_A"}})
        mock_get_vim.return_value = vim
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/instantiate' % uuidsentinel.vnf_instance_id)
        mock_vnf_instance_get_by_id.return_value =\
            fakes.return_vnf_instance_model(
                tenant_id=req.environ['tacker.context'].project_id)
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

        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        # Call Instantiate API
        resp = req.get_response(self.app)
        self.assertTrue('Location' in resp.headers.keys())
        expected_location = (self.expected_location_prefix +
                    str(mock_insta_notif_process.return_value))
        self.assertEqual(expected_location, resp.headers['location'])
        self.assertEqual(http_client.ACCEPTED, resp.status_code)
        mock_instantiate.assert_called_once()
        mock_get_vnf.assert_called_once()
        mock_insta_notif_process.assert_called_once()

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
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

        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/instantiate' % uuidsentinel.vnf_instance_id)
        mock_vnf_instance_get_by_id.return_value =\
            fakes.return_vnf_instance_model(
                tenant_id=req.environ['tacker.context'].project_id)
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
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        # Call Instantiate API
        resp = req.get_response(self.app)
        self.assertFalse('Location' in resp.headers.keys())
        self.assertEqual(http_client.BAD_REQUEST, resp.status_code)
        self.assertIn('application/problem+json', resp.headers['Content-Type'])
        self.assertEqual("VimConnection id is not found: %s" %
                         uuidsentinel.vim_id,
                         resp.json['detail'])
        mock_get_vnf.assert_called_once()

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
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

        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/instantiate' % uuidsentinel.vnf_instance_id)
        mock_vnf_instance_get_by_id.return_value =\
            fakes.return_vnf_instance_model(
                tenant_id=req.environ['tacker.context'].project_id)
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
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        # Call Instantiate API
        resp = req.get_response(self.app)
        self.assertFalse('Location' in resp.headers.keys())
        self.assertEqual(http_client.BAD_REQUEST, resp.status_code)
        self.assertIn('application/problem+json', resp.headers['Content-Type'])
        self.assertEqual("Region not found for the VimConnection: %s" %
                         uuidsentinel.vim_id,
                         resp.json['detail'])
        mock_get_vnf.assert_called_once()

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
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

        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/instantiate' % uuidsentinel.vnf_instance_id)
        mock_vnf_instance_get_by_id.return_value =\
            fakes.return_vnf_instance_model(
                tenant_id=req.environ['tacker.context'].project_id)
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
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        # Call Instantiate API
        resp = req.get_response(self.app)
        self.assertFalse('Location' in resp.headers.keys())
        self.assertEqual(http_client.BAD_REQUEST, resp.status_code)
        self.assertIn('application/problem+json', resp.headers['Content-Type'])
        self.assertEqual("Default VIM is not defined.",
                         resp.json['detail'])
        mock_get_vnf.assert_called_once()

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._get_vnf')
    @mock.patch.object(objects.vnf_instance, "_vnf_instance_get_by_id")
    def test_instantiate_incorrect_instantiation_state(
            self, mock_vnf_by_id, mock_get_vnf, mock_get_service_plugins):
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/instantiate' % uuidsentinel.vnf_instance_id)
        vnf_instance = fakes.return_vnf_instance_model(
            tenant_id=req.environ['tacker.context'].project_id)
        vnf_instance.instantiation_state = 'INSTANTIATED'
        mock_vnf_by_id.return_value = vnf_instance

        body = {"flavourId": "simple"}
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        # Call Instantiate API
        resp = req.get_response(self.app)
        self.assertFalse('Location' in resp.headers.keys())
        self.assertEqual(http_client.CONFLICT, resp.status_code)

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._get_vnf')
    @mock.patch.object(objects.vnf_instance, "_vnf_instance_get_by_id")
    def test_instantiate_incorrect_task_state(
            self,
            mock_vnf_by_id,
            mock_get_vnf,
            mock_get_service_plugins):
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/instantiate' % uuidsentinel.vnf_instance_id)
        vnf_instance = fakes.return_vnf_instance_model(
            task_state=fields.VnfInstanceTaskState.INSTANTIATING,
            tenant_id=req.environ['tacker.context'].project_id)
        mock_vnf_by_id.return_value = vnf_instance

        body = {"flavourId": "simple"}
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        resp = req.get_response(self.app)
        self.assertFalse('Location' in resp.headers.keys())
        self.assertEqual(http_client.CONFLICT, resp.status_code)
        self.assertIn('application/problem+json', resp.headers['Content-Type'])
        expected_msg = ("Vnf instance %s in task_state INSTANTIATING. Cannot "
                        "instantiate while the vnf instance is in this state.")
        self.assertEqual(expected_msg % uuidsentinel.vnf_instance_id,
                         resp.json['detail'])

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
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
                       return_value={'VNFM': FakeVNFMPlugin()})
    def test_instantiate_without_flavour_id(self,
                                            mock_get_service_plugins):
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/instantiate' % uuidsentinel.vnf_instance_id)
        req.body = jsonutils.dump_as_bytes({})
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        # Call Instantiate API
        resp = req.get_response(self.app)
        self.assertFalse('Location' in resp.headers.keys())
        self.assertEqual(http_client.BAD_REQUEST, resp.status_code)
        self.assertIn('application/problem+json', resp.headers['Content-Type'])
        self.assertEqual("'flavourId' is a required property",
                         resp.json['detail'])

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
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
        self.assertFalse('Location' in resp.headers.keys())
        self.assertEqual(http_client.INTERNAL_SERVER_ERROR, resp.status_code)

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
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
        self.assertFalse('Location' in resp.headers.keys())
        self.assertEqual(http_client.NOT_FOUND, resp.status_code)
        self.assertIn('application/problem+json', resp.headers['Content-Type'])
        self.assertEqual(
            "Can not find requested vnf: %s" % constants.INVALID_UUID,
            resp.json['detail'])

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
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
        self.assertFalse('Location' in resp.headers.keys())
        self.assertEqual(http_client.NOT_FOUND, resp.status_code)
        self.assertIn('application/problem+json', resp.headers['Content-Type'])
        self.assertEqual("Can not find requested vnf instance: %s" %
                         uuidsentinel.vnf_instance_id,
                         resp.json['detail'])
        mock_get_vnf.assert_called_once()

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
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
        self.assertFalse('Location' in resp.headers.keys())
        self.assertEqual(http_client.METHOD_NOT_ALLOWED, resp.status_code)

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.vnf_instance, "_vnf_instance_get_by_id")
    def test_show_vnf_not_instantiated(self, mock_vnf_by_id,
            mock_get_service_plugins):
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s' % uuidsentinel.instance_id)
        mock_vnf_by_id.return_value = fakes.return_vnf_instance_model(
            tenant_id=req.environ['tacker.context'].project_id)
        expected_result = fakes.fake_vnf_instance_response()
        res_dict = self.controller.show(req, uuidsentinel.instance_id)
        self.assertEqual(expected_result, res_dict)

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    def test_show_vnf_instantiated(self, mock_vnf_by_id,
                                   mock_get_service_plugins):
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s' % uuidsentinel.instance_id)
        mock_vnf_by_id.return_value = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED,
            tenant_id=req.environ['tacker.context'].project_id)
        expected_result = fakes.fake_vnf_instance_response(
            fields.VnfInstanceState.INSTANTIATED)
        res_dict = self.controller.show(req, uuidsentinel.instance_id)
        self.assertEqual(expected_result, res_dict)

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    def test_show_vnf_instantiated_with_vim_info(
            self, mock_vnf_by_id, mock_get_service_plugins):
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s' % uuidsentinel.instance_id)

        vim_info = {
            "id": "7d24979f-491e-4fa3-8da1-4a374fe28d55",
            "vim_id": None,
            "vim_type": "ETSINFV.OPENSTACK_KEYSTONE.V_2",
            "interface_info": {"endpoint": "http://127.0.0.1/identity"},
            "access_info": {
                "username": "nfv_user",
                "region": "RegionOne",
                "password": "devstack",
                "tenant": "85d12da99f8246dfae350dbc7334a473",
            },
            "extra": {}
        }

        vim_connection_info = objects.VimConnectionInfo(
            id=vim_info['id'], vim_id=vim_info['vim_id'],
            vim_type=vim_info['vim_type'],
            access_info=vim_info['access_info'],
            interface_info=vim_info['interface_info'],
            extra=vim_info['extra'])

        mock_vnf_by_id.return_value = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED,
            vim_connection_info=[vim_connection_info],
            tenant_id=req.environ['tacker.context'].project_id)

        vim_info = common_utils.convert_snakecase_to_camelcase(vim_info)
        expected_result = fakes.fake_vnf_instance_response(
            fields.VnfInstanceState.INSTANTIATED,
            vimConnectionInfo=[vim_info])

        res_dict = self.controller.show(req, uuidsentinel.instance_id)
        self.assertEqual(expected_result, res_dict)

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.vnf_instance, "_vnf_instance_get_by_id")
    def test_show_with_non_existing_vnf_instance(self, mock_vnf_by_id,
                                                 mock_get_service_plugins):
        mock_vnf_by_id.side_effect = exceptions.VnfInstanceNotFound
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s' % uuidsentinel.vnf_instance_id)

        resp = req.get_response(self.app)

        self.assertEqual(http_client.NOT_FOUND, resp.status_code)
        self.assertIn('application/problem+json', resp.headers['Content-Type'])
        self.assertEqual("Can not find requested vnf instance: %s" %
                         uuidsentinel.vnf_instance_id,
                         resp.json['detail'])

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
    def test_show_with_invalid_uuid(self,
                                    mock_get_service_plugins):
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s' % constants.INVALID_UUID)

        resp = req.get_response(self.app)
        self.assertEqual(http_client.NOT_FOUND, resp.status_code)
        self.assertIn('application/problem+json', resp.headers['Content-Type'])
        self.assertEqual("Can not find requested vnf instance: %s" %
                         constants.INVALID_UUID,
                         resp.json['detail'])

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
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
                       return_value={'VNFM': FakeVNFMPlugin()})
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
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/terminate' % uuidsentinel.vnf_instance_id)
        vnf_instance_obj = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED,
            tenant_id=req.environ['tacker.context'].project_id)
        mock_get_by_id.return_value = vnf_instance_obj
        mock_get_vnf.return_value = \
            self._get_dummy_vnf(vnf_id=vnf_instance_obj.id, status='ACTIVE')

        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        resp = req.get_response(self.app)
        expected_location = (self.expected_location_prefix +
                    str(mock_notification_process.return_value))
        self.assertEqual(expected_location, resp.headers['location'])
        self.assertEqual(http_client.ACCEPTED, resp.status_code)
        mock_terminate.assert_called_once()
        mock_get_vnf.assert_called_once()
        mock_notification_process.assert_called_once()

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
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
                       return_value={'VNFM': FakeVNFMPlugin()})
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
        self.assertFalse('Location' in resp.headers.keys())
        self.assertEqual(http_client.BAD_REQUEST, resp.status_code)
        self.assertIn('application/problem+json', resp.headers['Content-Type'])
        self.assertEqual("'terminationType' is a required property",
                         resp.json['detail'])

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
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
        self.assertFalse('Location' in resp.headers.keys())
        self.assertEqual(http_client.METHOD_NOT_ALLOWED, resp.status_code)

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
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
        self.assertFalse('Location' in resp.headers.keys())
        self.assertEqual(http_client.NOT_FOUND, resp.status_code)
        self.assertIn('application/problem+json', resp.headers['Content-Type'])
        self.assertEqual("Can not find requested vnf instance: %s" %
                         uuidsentinel.vnf_instance_id,
                         resp.json['detail'])
        mock_get_vnf.assert_called_once()

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._get_vnf')
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    def test_terminate_incorrect_task_state(
            self,
            mock_vnf_by_id,
            mock_get_vnf,
            mock_get_service_plugins):
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/terminate' % uuidsentinel.vnf_instance_id)
        vnf_instance = fakes.return_vnf_instance(
            instantiated_state=fields.VnfInstanceState.INSTANTIATED,
            task_state=fields.VnfInstanceTaskState.TERMINATING,
            tenant_id=req.environ['tacker.context'].project_id)
        mock_vnf_by_id.return_value = vnf_instance

        body = {"terminationType": "FORCEFUL"}
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        resp = req.get_response(self.app)
        self.assertFalse('Location' in resp.headers.keys())
        self.assertEqual(http_client.CONFLICT, resp.status_code)
        self.assertIn('application/problem+json', resp.headers['Content-Type'])
        expected_msg = ("Vnf instance %s in task_state TERMINATING. Cannot "
                        "terminate while the vnf instance is in this state.")
        self.assertEqual(expected_msg % uuidsentinel.vnf_instance_id,
                         resp.json['detail'])
        mock_get_vnf.assert_called_once()

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
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
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/heal' % uuidsentinel.vnf_instance_id)
        vnf_instance_obj = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED,
            tenant_id=req.environ['tacker.context'].project_id)
        mock_vnf_by_id.return_value = vnf_instance_obj
        mock_get_vnf.return_value = \
            self._get_dummy_vnf(vnf_id=vnf_instance_obj.id, status='ACTIVE')

        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        resp = req.get_response(self.app)
        self.assertTrue('Location' in resp.headers.keys())
        expected_location = (self.expected_location_prefix +
                    str(mock_heal_notif_process.return_value))
        self.assertEqual(expected_location, resp.headers['location'])
        self.assertEqual(http_client.ACCEPTED, resp.status_code)
        mock_rpc_heal.assert_called_once()

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
    def test_heal_cause_max_length_exceeded(self,
                                            mock_get_service_plugins):
        body = {'cause': 'A' * 256}
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/heal' % uuidsentinel.vnf_instance_id)
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        resp = req.get_response(self.app)
        self.assertFalse('Location' in resp.headers.keys())
        self.assertEqual(http_client.BAD_REQUEST, resp.status_code)

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
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
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/heal' % uuidsentinel.vnf_instance_id)
        vnf_instance_obj = fakes.return_vnf_instance(
            fields.VnfInstanceState.NOT_INSTANTIATED,
            tenant_id=req.environ['tacker.context'].project_id)
        mock_vnf_by_id.return_value = vnf_instance_obj

        body = {}
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        resp = req.get_response(self.app)
        self.assertFalse('Location' in resp.headers.keys())
        self.assertEqual(http_client.CONFLICT, resp.status_code)
        self.assertIn('application/problem+json', resp.headers['Content-Type'])
        expected_msg = ("Vnf instance %s in instantiation_state "
                        "NOT_INSTANTIATED. Cannot heal while the vnf instance "
                        "is in this state.")
        self.assertEqual(expected_msg % uuidsentinel.vnf_instance_id,
                         resp.json['detail'])

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._notification_process')
    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._get_vnf')
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    def test_heal_incorrect_task_state(self, mock_vnf_by_id, mock_get_vnf,
                                       mock_notif, mock_get_service_plugins):
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/heal' % uuidsentinel.vnf_instance_id)
        vnf_instance_obj = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED,
            task_state=fields.VnfInstanceTaskState.HEALING,
            tenant_id=req.environ['tacker.context'].project_id)
        mock_vnf_by_id.return_value = vnf_instance_obj

        body = {}
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        resp = req.get_response(self.app)
        self.assertFalse('Location' in resp.headers.keys())
        self.assertEqual(http_client.CONFLICT, resp.status_code)
        self.assertIn('application/problem+json', resp.headers['Content-Type'])
        expected_msg = ("Vnf instance %s in task_state "
                        "HEALING. Cannot heal while the vnf instance "
                        "is in this state.")
        self.assertEqual(expected_msg % uuidsentinel.vnf_instance_id,
                         resp.json['detail'])

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
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
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/heal' % uuidsentinel.vnf_instance_id)
        vnf_instance_obj = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED,
            tenant_id=req.environ['tacker.context'].project_id)
        mock_vnf_by_id.return_value = vnf_instance_obj
        mock_get_vnf.return_value = \
            self._get_dummy_vnf(vnf_id=vnf_instance_obj.id, status='ACTIVE')

        body = {'vnfcInstanceId': [uuidsentinel.vnfc_instance_id]}
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        resp = req.get_response(self.app)
        self.assertFalse('Location' in resp.headers.keys())
        self.assertEqual(http_client.BAD_REQUEST, resp.status_code)
        self.assertIn('application/problem+json', resp.headers['Content-Type'])
        expected_msg = "Vnfc id %s not present in vnf instance %s"
        self.assertEqual(expected_msg % (uuidsentinel.vnfc_instance_id,
                                         uuidsentinel.vnf_instance_id),
                         resp.json['detail'])

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
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
        self.assertFalse('Location' in resp.headers.keys())
        self.assertEqual(http_client.METHOD_NOT_ALLOWED, resp.status_code)

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
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

    @mock.patch.object(objects.VnfInstanceList, "get_by_marker_filter")
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
        self.assertEqual(expected_result, resp.json)

    @mock.patch.object(objects.VnfInstanceList, "get_by_marker_filter",
        return_value=[])
    def test_index_empty_response(self, mock_vnf_list):
        req = fake_request.HTTPRequest.blank('/vnf_instances')
        mock_vnf_list.return_value = []
        resp = self.controller.index(req)
        self.assertEqual([], resp.json)

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
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
                       return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.vnf_instance, "_vnf_instance_get_by_id")
    @mock.patch.object(objects.vnf_instance, '_destroy_vnf_instance')
    def test_delete(self, mock_destroy_vnf_instance, mock_vnf_by_id,
            mock_get_service_plugins, mock_private_delete):
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s' % uuidsentinel.vnf_instance_id)
        req.method = 'DELETE'
        mock_vnf_by_id.return_value = fakes.return_vnf_instance_delete(
            tenant_id=req.environ['tacker.context'].project_id)
        req.headers['Content-Type'] = 'application/json'

        # Call delete API
        resp = req.get_response(self.app)

        self.assertEqual(http_client.NO_CONTENT, resp.status_code)

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
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
        self.assertIn('application/problem+json', resp.headers['Content-Type'])
        self.assertEqual("Can not find requested vnf instance: %s" %
                         uuidsentinel.vnf_instance_id,
                         resp.json['detail'])

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
    def test_delete_with_invalid_uuid(self, mock_get_service_plugins):
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s' % constants.INVALID_UUID)
        req.method = 'DELETE'

        # Call delete API
        resp = req.get_response(self.app)

        self.assertEqual(http_client.NOT_FOUND, resp.status_code)
        self.assertIn('application/problem+json', resp.headers['Content-Type'])
        self.assertEqual("Can not find requested vnf instance: %s" %
                         constants.INVALID_UUID,
                         resp.json['detail'])

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    def test_delete_with_incorrect_instantiation_state(
            self, mock_vnf_by_id, mock_get_service_plugins):
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s' % uuidsentinel.vnf_instance_id)
        req.method = 'DELETE'

        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED,
            tenant_id=req.environ['tacker.context'].project_id)
        mock_vnf_by_id.return_value = vnf_instance

        # Call delete API
        resp = req.get_response(self.app)

        self.assertEqual(http_client.CONFLICT, resp.status_code)
        self.assertIn('application/problem+json', resp.headers['Content-Type'])
        expected_msg = ("Vnf instance %s in instantiation_state "
                        "INSTANTIATED. Cannot delete while the vnf instance "
                        "is in this state.")
        self.assertEqual(expected_msg % uuidsentinel.vnf_instance_id,
                         resp.json['detail'])

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    def test_delete_with_incorrect_task_state(self, mock_vnf_by_id,
                                              mock_get_service_plugins):
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s' % uuidsentinel.vnf_instance_id)
        req.method = 'DELETE'

        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.NOT_INSTANTIATED,
            task_state=fields.VnfInstanceTaskState.ERROR,
            tenant_id=req.environ['tacker.context'].project_id)
        mock_vnf_by_id.return_value = vnf_instance

        # Call delete API
        resp = req.get_response(self.app)

        self.assertEqual(http_client.CONFLICT, resp.status_code)
        self.assertIn('application/problem+json', resp.headers['Content-Type'])
        expected_msg = ("Vnf instance %s in task_state ERROR. "
                        "Cannot delete while the vnf instance "
                        "is in this state.")
        self.assertEqual(expected_msg % uuidsentinel.vnf_instance_id,
                         resp.json['detail'])

    @mock.patch.object(objects.VnfInstanceList, "get_by_marker_filter")
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
        self.assertEqual(expected_result, res_dict.json)

    @mock.patch.object(objects.VnfInstanceList, "get_by_marker_filter")
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
        self.assertEqual(expected_result, res_dict.json)

    @mock.patch.object(objects.VnfInstanceList, "get_by_marker_filter")
    @ddt.data(
        {'filter': "(eq,vnfInstanceName,dummy_value)"},
        {'filter': "(eq,vnfInstanceDescription,dummy value)"},
        {'filter': "(eq,instantiationState,'NOT_INSTANTIATED')"},
        {'filter': "(eq,taskState,'ACTIVE')"},
        {'filter': "(eq,vnfdId,%s)" % uuidsentinel.vnfd_id},
        {'filter': "(eq,vnfProvider,'''dummy ''hi'' value''')"},
        {'filter': "(eq,vnfProductName,'dummy_product_name')"},
        {'filter': "(eq,vnfSoftwareVersion,'1.0')"},
        {'filter': "(eq,vnfdVersion,'dummy_vnfd_version')"},
        {'filter': "(eq,tenantId,'dummy_tenant_id')"},
        {'filter': "(eq,vnfPkgId,%s)" % uuidsentinel.vnf_pkg_id},
        {'filter': "(eq,vimConnectionInfo/accessInfo/region,'dummy_id')"},
        {'filter': "(eq,instantiatedInfo/flavourId,'dummy_flavour')"},
        {'filter': "(eq,instantiatedInfo/vnfInstanceId,%s)" %
         uuidsentinel.vnf_instance_id},
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
        self.assertEqual(expected_result, res_dict.json)

    @mock.patch.object(objects.VnfInstanceList, "get_by_marker_filter")
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

    @mock.patch.object(objects.VnfInstanceList, "get_by_marker_filter")
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

    @mock.patch.object(objects.VnfInstanceList, "get_by_marker_filter")
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

    @mock.patch.object(objects.VnfInstanceList, "get_by_marker_filter")
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

    @mock.patch.object(objects.VnfInstanceList, "get_by_marker_filter")
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

    @mock.patch.object(objects.vnf_instance.VnfInstanceList,
                       "get_by_marker_filter")
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    @ddt.data(
        {'params': {'all_records': 'yes'},
            'result_names': ['sample1', 'sample2', 'sample3', 'sample4']},
        {'params': {'all_records': 'yes', 'nextpage_opaque_marker':
            '22222222-2222-2222-2222-222222222222'},
            'result_names': ['sample1', 'sample2', 'sample3', 'sample4']},
        {'params': {'nextpage_opaque_marker':
            '44444444-4444-4444-4444-444444444444'},
            'result_names': []},
        {'params': {'nextpage_opaque_marker':
            '22222222-2222-2222-2222-222222222222'},
            'result_names': ['sample3', 'sample4']},
        {'params': {},
            'result_names': ['sample1', 'sample2']}
    )
    def test_index_paging(self, values,
            mock_marker_obj,
            mock_vnf_instance_list):
        ids = ['11111111-1111-1111-1111-111111111111',
               '22222222-2222-2222-2222-222222222222',
               '33333333-3333-3333-3333-333333333333',
               '44444444-4444-4444-4444-444444444444',
               None]
        cfg.CONF.set_override('vnf_instance_num', 2, group='vnf_lcm')
        query = urllib.parse.urlencode(values['params'])
        req = fake_request.HTTPRequest.blank(
            '/vnflcm/v1/vnf_instances?' + query)

        target_index = []
        if 'all_records' in values['params'] \
                and values['params']['all_records'] == 'yes':
            mock_marker_obj.return_value = None
            target_index = [0, 1, 2, 3]
        elif 'nextpage_opaque_marker' in values['params']:
            mock_marker_obj.return_value = fakes.return_vnf_instance(
                **{'id': values['params']['nextpage_opaque_marker']})
            marker_obj_index = ids.index(mock_marker_obj.return_value['id'])
            for i in range(marker_obj_index + 1, len(ids) - 1):
                target_index.append(i)
        else:
            mock_marker_obj.return_value = None
            target_index = [0, 1]

        mock_vnf_instance_list.return_value = []
        for index in range(len(target_index)):
            mock_vnf_instance_list.return_value.append(
                fakes.return_vnf_instance(**{'id': ids[target_index[index]],
                    'vnf_instance_name':
                    values['result_names'][index]}))

        expected_result = []
        for index in range(len(target_index)):
            _links = fakes.fake_vnf_instance_response()['_links']
            expected_links = (re.sub("vnf_instances/[a-zA-Z0-9-]*",
                    "vnf_instances/{}".format(ids[target_index[index]]),
                    str(_links)))
            expected_links = json.loads(expected_links.replace("'", '"'))
            expected_result.append(fakes.fake_vnf_instance_response(
                **{'vnfInstanceName': values['result_names'][index],
                    'id': ids[target_index[index]],
                    '_links': expected_links}))

        expected_result_link = None
        if 'all_records' not in values['params'] and len(target_index) >= 2:
            expected_result_link = (
                '<http://localhost//vnflcm/v1/vnf_instances' +
                '?nextpage_opaque_marker=%s>; rel="next"'
                % ids[target_index[1]])

        res_dict = self.controller.index(req)

        self.assertEqual(expected_result, res_dict.json)
        if expected_result_link is not None:
            self.assertEqual(expected_result_link, res_dict.headers['Link'])

    @mock.patch.object(objects.VnfInstanceList, "get_by_marker_filter")
    @ddt.data(
        {'attribute_not_exist': 'some_value'},
        {'all_fields': {}},
        {'fields': {}},
        {'exclude_fields': {}},
        {'exclude_default': {}},
        {'attribute_not_exist': 'some_value', 'filter': {}},
        {'attribute_not_exist': 'some_value', 'fields': {}}
    )
    def test_index_not_supported_params_1(self, params,
            mock_vnf_list):
        """Test not supported params in request."""
        query = urllib.parse.urlencode(params)
        req = fake_request.HTTPRequest.blank(
            '/vnflcm/v1/vnf_instances?' + query)
        self.assertRaises(webob.exc.HTTPBadRequest,
                          self.controller.index, req)

    @mock.patch.object(objects.VnfInstanceList, "get_by_marker_filter")
    @ddt.data(
        {'attribute_not_exist': 'some_value'},
        {'all_fields': {}},
        {'fields': {}},
        {'exclude_fields': {}},
        {'exclude_default': {}},
        {'attribute_not_exist': 'some_value', 'filter': {}},
        {'attribute_not_exist': 'some_value', 'fields': {}}
    )
    def test_index_not_supported_params_2(self, params,
            mock_vnf_list):
        query = urllib.parse.urlencode(params)
        req = fake_request.HTTPRequest.blank(
            f'/vnf_instances?{query}')
        req.headers['Content-Type'] = 'application/json'
        req.method = 'GET'
        params = set(params)
        supported_params = {'filter'}
        unsupported_params = params - supported_params
        msg = _("Not supported parameters: %s") \
            % ','.join(unsupported_params)
        res = '{"title": "Bad Request", "status": 400, "detail": "%s"}' % msg
        resp = req.get_response(self.app)
        self.assertEqual(res, resp.text)

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    @mock.patch.object(objects.VnfLcmOpOcc, "get_by_id")
    def test_show_lcm_op_occs(self, mock_get_by_id,
            mock_vnf_instance, mock_get_service_plugins):
        req = fake_request.HTTPRequest.blank(
            '/vnf_lcm_op_occs/%s' % constants.UUID)
        mock_get_by_id.return_value = fakes.return_vnf_lcm_opoccs_obj()
        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.NOT_INSTANTIATED,
            task_state=fields.VnfInstanceTaskState.ERROR,
            tenant_id=req.environ['tacker.context'].project_id)
        mock_vnf_instance.return_value = vnf_instance

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

    @mock.patch.object(objects.VnfInstance, "get_by_id")
    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
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
            mock_get_service_plugins,
            mock_vnf_instance):

        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s' % constants.UUID)
        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED,
            tenant_id=req.environ['tacker.context'].project_id)
        mock_vnf_instance.return_value = vnf_instance
        mock_vnf_index_list.return_value = fakes._get_vnf()
        mock_vnf_instance_list.return_value = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED,
            tenant_id=req.environ['tacker.context'].project_id)
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
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'PATCH'

        # Call Instantiate API
        resp = req.get_response(self.app)
        self.assertEqual(http_client.ACCEPTED, resp.status_code)
        mock_update.assert_called_once()

    @mock.patch.object(objects.VnfInstance, "get_by_id")
    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VNF, "vnf_index_list")
    def test_update_vnf_none_vnf_data(
            self,
            mock_vnf_index_list,
            mock_get_service_plugins,
            mock_vnf_instance):

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
        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED,
            tenant_id=req.environ['tacker.context'].project_id)
        mock_vnf_instance.return_value = vnf_instance
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'PATCH'

        msg = _("Can not find requested vnf data: %s") % constants.UUID
        res = self._make_problem_detail(msg, 404, title='Not Found')

        resp = req.get_response(self.app)
        self.assertEqual(res.text, resp.text)

    @mock.patch.object(objects.VnfInstance, "get_by_id")
    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VNF, "vnf_index_list")
    def test_update_vnf_status_err(
            self,
            mock_vnf_index_list,
            mock_get_service_plugins,
            mock_vnf_instance):
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
        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED,
            tenant_id=req.environ['tacker.context'].project_id)
        mock_vnf_instance.return_value = vnf_instance
        req.body = jsonutils.dump_as_bytes(body)

        req.headers['Content-Type'] = 'application/json'
        req.method = 'PATCH'

        msg = _("VNF %(id)s status is %(state)s") % {
            "id": constants.UUID, "state": "ERROR"}
        res = self._make_problem_detail(msg %
                                        {"state": "ERROR"}, 409, 'Conflict')

        resp = req.get_response(self.app)
        self.assertEqual(res.text, resp.text)

    @mock.patch.object(objects.VnfInstance, "get_by_id")
    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VNF, "vnf_index_list")
    @mock.patch.object(objects.VnfInstanceList, "vnf_instance_list")
    def test_update_vnf_none_instance_data(
            self,
            mock_vnf_instance_list,
            mock_vnf_index_list,
            mock_get_service_plugins,
            mock_vnf_instance):

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
        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED,
            tenant_id=req.environ['tacker.context'].project_id)
        mock_vnf_instance.return_value = vnf_instance
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'PATCH'

        vnf_data = fakes._get_vnf()
        msg = ("Can not find requested vnf instance data: %s") % vnf_data.get(
            'vnfd_id')
        res = self._make_problem_detail(msg, 404, title='Not Found')

        resp = req.get_response(self.app)
        self.assertEqual(res.text, resp.text)

    @mock.patch.object(objects.VnfInstance, "get_by_id")
    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
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
            mock_get_service_plugins,
            mock_vnf_instance):

        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s' % constants.UUID)
        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED,
            tenant_id=req.environ['tacker.context'].project_id)
        mock_vnf_instance.return_value = vnf_instance
        mock_vnf_index_list.return_value = fakes._get_vnf()
        mock_vnf_instance_list.return_value = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED,
            tenant_id=req.environ['tacker.context'].project_id)
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
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'PATCH'

        resp = req.get_response(self.app)
        self.assertEqual(http_client.ACCEPTED, resp.status_code)
        mock_update.assert_called_once()

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VNF, "vnf_index_list")
    @mock.patch.object(objects.VnfInstanceList, "vnf_instance_list")
    @mock.patch.object(objects.VnfPackageVnfd, 'get_vnf_package_vnfd')
    @mock.patch.object(vnf_lcm_rpc.VNFLcmRPCAPI, "update")
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    def test_update_vnf_with_pkg_id(
            self, mock_vnf_instance, mock_update,
            mock_vnf_package_vnf_get_vnf_package_vnfd,
            mock_vnf_instance_list, mock_vnf_index_list,
            mock_get_service_plugins):

        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s' % constants.UUID)
        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED,
            tenant_id=req.environ['tacker.context'].project_id)
        mock_vnf_instance.return_value = vnf_instance
        mock_vnf_index_list.return_value = fakes._get_vnf()
        mock_vnf_instance_list.return_value = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED,
            tenant_id=req.environ['tacker.context'].project_id)
        mock_vnf_package_vnf_get_vnf_package_vnfd.return_value =\
            fakes.return_vnf_package_vnfd()

        body = {"vnfInstanceName": "new_instance_name",
                "vnfInstanceDescription": "new_instance_discription",
                "vnfPkgId": "2c69a161-0000-4b0f-bcf8-391f8fc76600",
                "vnfConfigurableProperties": {"test": "test_value"},
                "vnfcInfoModificationsDeleteIds": ["test1"]}
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'PATCH'

        # Call Instantiate API
        resp = req.get_response(self.app)
        self.assertEqual(http_client.ACCEPTED, resp.status_code)
        mock_update.assert_called_once()

    @mock.patch.object(objects.vnf_instance.VnfInstance, "get_by_id")
    @mock.patch.object(objects.vnf.VNF, "vnf_index_list")
    @mock.patch.object(objects.vnf_instance.VnfInstanceList,
        "vnf_instance_list")
    @mock.patch.object(objects.vnf_package_vnfd.VnfPackageVnfd,
        "get_vnf_package_vnfd")
    def test_update_vimcon_in_not_instantiated(self,
            mock_vnf_package_vnf_get_vnf_package_vnfd, mock_vnf_instance_list,
            mock_vnf_index_list, mock_vnf_instance):

        req = fake_request.HTTPRequest.blank(
            "/vnf_instances/%s" % constants.UUID)
        mock_vnf_instance.return_value = fakes.return_vnf_instance(
            fields.VnfInstanceState.NOT_INSTANTIATED)
        mock_vnf_index_list.return_value = fakes._get_vnf()
        mock_vnf_instance_list.return_value = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED,
            tenant_id=req.environ["tacker.context"].project_id)
        mock_vnf_package_vnf_get_vnf_package_vnfd.return_value =\
            fakes.return_vnf_package_vnfd()

        body = {"vnfInstanceName": "new_instance_name",
                "vnfInstanceDescription": "new_instance_discription",
                "vnfdId": "2c69a161-0000-4b0f-bcf8-391f8fc76600",
                "metadata": {"testkey": "test_value"},
                "vimConnectionInfo": {"id": "testid"}}
        req.body = jsonutils.dump_as_bytes(body)
        req.headers["Content-Type"] = "application/json"
        req.method = "PATCH"

        msg = "vimConnectionInfo cannot be modified in NOT_INSTANTIATED."
        res = self._make_problem_detail(msg, 400, title="Bad Request")

        # Call Update API
        resp = req.get_response(self.app)
        self.assertEqual(res.text, resp.text)

    @mock.patch.object(objects.VnfInstance, "get_by_id")
    @ddt.data("vnfdId", "vnfPkgId")
    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
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
            mock_get_service_plugins,
            mock_vnf_instance):

        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s' % constants.UUID)
        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED,
            tenant_id=req.environ['tacker.context'].project_id)
        mock_vnf_instance.return_value = vnf_instance
        mock_vnf_index_list.return_value = fakes._get_vnf()
        mock_vnf_instance_list.return_value = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED,
            tenant_id=req.environ['tacker.context'].project_id)
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
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'PATCH'

        resp = req.get_response(self.app)
        self.assertEqual(http_client.BAD_REQUEST, resp.status_code)

    @ddt.data("vnfdId", "vnfPkgId")
    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
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

        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s' % constants.UUID)
        mock_vnf_index_list.return_value = fakes._get_vnf()
        mock_vnf_instance_list.return_value = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED,
            tenant_id=req.environ['tacker.context'].project_id)
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
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/scale' %
            constants.UUID)
        mock_vnf_instance_get_by_id.return_value =\
            fakes.return_vnf_instance(fields.VnfInstanceState.INSTANTIATED,
            tenant_id=req.environ['tacker.context'].project_id)

        body = {
            "type": "SCALE_OUT",
            "aspectId": "SP1",
            "numberOfSteps": 1,
            "additionalParams": {
                "test": "test_value"}}
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
    @mock.patch.object(objects.VnfInstance, "save")
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
            mock_vnf_instance_save,
            mock_obj_from_primitive,
            mock_create,
            mock_get_service_plugins):

        mock_get_vnf.return_value = fakes._get_vnf()
        vim_connection_info = objects.VimConnectionInfo(
            vim_type="openstack")
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/scale' %
            constants.UUID)
        update = {'vim_connection_info': [vim_connection_info],
                  'tenant_id': req.environ['tacker.context'].project_id}
        mock_vnf_instance_get_by_id.return_value = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED, scale_status="scale_status",
            **update)
        mock_obj_from_primitive.return_value = fakes.scale_request_make(
            "SCALE_IN", 1)
        mock_create.return_value = 200

        body = {
            "type": "SCALE_IN",
            "aspectId": "SP1",
            "numberOfSteps": 1,
            "additionalParams": {
                "test": "test_value"}}
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
    @mock.patch.object(objects.VnfInstance, "save")
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
            mock_vnf_instance_save,
            mock_obj_from_primitive,
            mock_create,
            mock_get_service_plugins):

        mock_get_vnf.return_value = fakes._get_vnf()
        vim_connection_info = objects.VimConnectionInfo(
            vim_type="openstack")
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/scale' %
            constants.UUID)
        update = {'vim_connection_info': [vim_connection_info],
                  'tenant_id': req.environ['tacker.context'].project_id}
        mock_vnf_instance_get_by_id.return_value = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED, scale_status="scale_status",
            **update)
        mock_obj_from_primitive.return_value = fakes.scale_request_make(
            "SCALE_OUT", 1)
        mock_create.return_value = 200

        body = {
            "type": "SCALE_OUT",
            "aspectId": "SP1",
            "numberOfSteps": 1,
            "additionalParams": {
                "test": "test_value"}}
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
    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    @mock.patch.object(tacker.db.vnfm.vnfm_db.VNFMPluginDb, "get_vnf")
    @mock.patch.object(vnf_lcm_rpc.VNFLcmRPCAPI, "scale")
    def test_scale_in_err(
            self,
            mock_scale,
            mock_get_vnf,
            mock_vnf_instance_get_by_id,
            mock_vnf_instance_save,
            mock_obj_from_primitive,
            mock_create,
            mock_get_service_plugins):

        mock_get_vnf.return_value = fakes._get_vnf()
        vim_connection_info = objects.VimConnectionInfo(
            vim_type="openstack")
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/scale' %
            constants.UUID)
        update = {'vim_connection_info': [vim_connection_info],
                  'tenant_id': req.environ['tacker.context'].project_id}
        mock_vnf_instance_get_by_id.return_value = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED, scale_status="scale_status",
            **update)

        mock_obj_from_primitive.return_value = fakes.scale_request_make(
            "SCALE_IN", 4)
        mock_create.return_value = 200

        body = {
            "type": "SCALE_IN",
            "aspectId": "SP1",
            "numberOfSteps": 1,
            "additionalParams": {
                "test": "test_value"}}
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
        vim_connection_info = objects.VimConnectionInfo(
            vim_type="openstack")
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/scale' %
            constants.UUID)
        update = {'vim_connection_info': [vim_connection_info],
                  'tenant_id': req.environ['tacker.context'].project_id}
        mock_vnf_instance_get_by_id.return_value = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED, scale_status="scale_status",
            **update)
        mock_obj_from_primitive.return_value = fakes.scale_request_make(
            "SCALE_OUT", 4)
        mock_create.return_value = 200

        body = {
            "type": "SCALE_OUT",
            "aspectId": "SP1",
            "numberOfSteps": 1,
            "additionalParams": {
                "test": "test_value"}}
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
    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    @mock.patch.object(vnf_lcm_rpc.VNFLcmRPCAPI, "send_notification")
    @mock.patch.object(objects.VnfLcmOpOcc, "create")
    def test_scale_notification(
            self,
            mock_create,
            mock_send_notification,
            mock_vnf_instance,
            mock_vnf_instance_save,
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

        vim_connection_info = objects.VimConnectionInfo(
            vim_type="openstack")
        update = {'vim_connection_info': [vim_connection_info],
                  'tenant_id': req.environ['tacker.context'].project_id}
        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED,
            scale_status="scale_status",
            **update)

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
            fields.VnfInstanceState.INSTANTIATED, scale_status="scale_status",
            **update)
        self.controller._scale(self.context,
            vnf_instance, vnf_info, body)

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
    @mock.patch.object(objects.VnfPackageVnfd, "get_by_id")
    @mock.patch.object(objects.VnfLcmOpOcc, "create")
    @mock.patch.object(objects.ScaleVnfRequest, "obj_from_primitive")
    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    @mock.patch.object(tacker.db.vnfm.vnfm_db.VNFMPluginDb, "get_vnf")
    @mock.patch.object(vnf_lcm_rpc.VNFLcmRPCAPI, "scale")
    @mock.patch.object(vnf_lcm_rpc.VNFLcmRPCAPI, "send_notification")
    def test_scale_in_cnf(
            self,
            mock_send_notification,
            mock_scale,
            mock_get_vnf,
            mock_vnf_instance_get_by_id,
            mock_vnf_instance_save,
            mock_obj_from_primitive,
            mock_create,
            mock_vnf_package_vnfd_get_by_id,
            mock_get_service_plugins):

        mock_get_vnf.return_value = fakes.vnf_dict_cnf()
        vim_connection_info = objects.VimConnectionInfo(
            vim_type="kubernetes")
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/scale' %
            FakeVNFMPlugin().vnf_for_cnf_vnf_id)
        update = {'vim_connection_info': [vim_connection_info],
                  'tenant_id': req.environ['tacker.context'].project_id}
        scale_status = objects.ScaleInfo(
            aspect_id='vdu1_aspect', scale_level=1)
        mock_vnf_instance_get_by_id.return_value = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED, scale_status=scale_status,
            **update)
        mock_vnf_package_vnfd_get_by_id.return_value = \
            fakes.return_vnf_package_vnfd()
        scale_request = fakes.scale_request_make("SCALE_IN", 1)
        scale_request.aspect_id = "vdu1_aspect"
        mock_obj_from_primitive.return_value = scale_request
        mock_create.return_value = 200

        body = {
            "type": "SCALE_IN",
            "aspectId": "vdu1_aspect",
            "numberOfSteps": 1,
            "additionalParams": {}}
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'
        resp = req.get_response(self.app)
        self.assertEqual(http_client.ACCEPTED, resp.status_code)
        mock_scale.assert_called_once()

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch('tacker.vnflcm.utils._get_vnfd_dict')
    @mock.patch.object(objects.VnfPackageVnfd, "get_by_id")
    @mock.patch.object(objects.VnfLcmOpOcc, "create")
    @mock.patch.object(objects.ScaleVnfRequest, "obj_from_primitive")
    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    @mock.patch.object(tacker.db.vnfm.vnfm_db.VNFMPluginDb, "get_vnf")
    @mock.patch.object(vnf_lcm_rpc.VNFLcmRPCAPI, "scale")
    @mock.patch.object(vnf_lcm_rpc.VNFLcmRPCAPI, "send_notification")
    def test_scale_out_cnf(
            self,
            mock_send_notification,
            mock_scale,
            mock_get_vnf,
            mock_vnf_instance_get_by_id,
            mock_vnf_instance_save,
            mock_obj_from_primitive,
            mock_create,
            mock_vnf_package_vnfd_get_by_id,
            mock_vnfd_dict,
            mock_get_service_plugins):

        vnf_info = fakes.vnf_dict_cnf()
        mock_get_vnf.return_value = vnf_info
        vim_connection_info = objects.VimConnectionInfo(
            vim_type="kubernetes")
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/scale' %
            FakeVNFMPlugin().vnf_for_cnf_vnf_id)
        update = {'vim_connection_info': [vim_connection_info],
                  'tenant_id': req.environ['tacker.context'].project_id}
        scale_status = objects.ScaleInfo(
            aspect_id='vdu1_aspect', scale_level=1)
        mock_vnf_instance_get_by_id.return_value = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED, scale_status=scale_status,
            **update)
        mock_vnf_package_vnfd_get_by_id.return_value = \
            fakes.return_vnf_package_vnfd()
        mock_vnfd_dict.return_value = fakes.vnfd_dict_cnf()
        scale_request = fakes.scale_request_make("SCALE_OUT", 1)
        scale_request.aspect_id = "vdu1_aspect"
        mock_obj_from_primitive.return_value = scale_request
        mock_create.return_value = 200

        body = {
            "type": "SCALE_OUT",
            "aspectId": "vdu1_aspect",
            "numberOfSteps": 1,
            "additionalParams": {}}
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
    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    @mock.patch.object(tacker.db.vnfm.vnfm_db.VNFMPluginDb, "get_vnf")
    @mock.patch.object(vnf_lcm_rpc.VNFLcmRPCAPI, "scale")
    @mock.patch.object(vnf_lcm_rpc.VNFLcmRPCAPI, "send_notification")
    def test_scale_in_cnf_error_is_reverse(
            self,
            mock_send_notification,
            mock_scale,
            mock_get_vnf,
            mock_vnf_instance_get_by_id,
            mock_vnf_instance_save,
            mock_obj_from_primitive,
            mock_create,
            mock_get_service_plugins):

        mock_get_vnf.return_value = fakes.vnf_dict_cnf()
        vim_connection_info = objects.VimConnectionInfo(
            vim_type="kubernetes")
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/scale' %
            FakeVNFMPlugin().vnf_for_cnf_vnf_id)
        update = {'vim_connection_info': [vim_connection_info],
                  'tenant_id': req.environ['tacker.context'].project_id}
        scale_status = objects.ScaleInfo(
            aspect_id='vdu1_aspect', scale_level=1)
        mock_vnf_instance_get_by_id.return_value = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED, scale_status=scale_status,
            **update)
        scale_request = fakes.scale_request_make("SCALE_IN", 1)
        scale_request.aspect_id = "vdu1_aspect"
        scale_request.additional_params = {"is_reverse": "True"}
        mock_obj_from_primitive.return_value = scale_request
        mock_create.return_value = 200

        body = {
            "type": "SCALE_IN",
            "aspectId": "vdu1_aspect",
            "numberOfSteps": 1,
            "additionalParams": {
                "is_reverse": "True"}}
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'
        resp = req.get_response(self.app)
        self.assertEqual(http_client.BAD_REQUEST, resp.status_code)
        mock_scale.assert_not_called()

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch('tacker.vnflcm.utils._get_vnfd_dict')
    @mock.patch.object(objects.VnfPackageVnfd, 'get_by_id')
    @mock.patch.object(objects.VnfPackage, "get_by_id")
    @mock.patch.object(objects.VnfLcmOpOcc, "create")
    @mock.patch.object(objects.ScaleVnfRequest, "obj_from_primitive")
    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    @mock.patch.object(tacker.db.vnfm.vnfm_db.VNFMPluginDb, "get_vnf")
    @mock.patch.object(vnf_lcm_rpc.VNFLcmRPCAPI, "scale")
    @mock.patch.object(vnf_lcm_rpc.VNFLcmRPCAPI, "send_notification")
    def test_scale_out_cnf_err_over_max_scale_level(
            self,
            mock_send_notification,
            mock_scale,
            mock_get_vnf,
            mock_vnf_instance_get_by_id,
            mock_vnf_instance_save,
            mock_obj_from_primitive,
            mock_create,
            mock_vnf_package_get_by_id,
            mock_vnf_package_vnfd_get_by_id,
            mock_vnfd_dict,
            mock_get_service_plugins):

        vnf_info = fakes.vnf_dict_cnf()
        mock_get_vnf.return_value = vnf_info
        vim_connection_info = objects.VimConnectionInfo(
            vim_type="kubernetes")
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/scale' %
            FakeVNFMPlugin().vnf_for_cnf_vnf_id)
        update = {'vim_connection_info': [vim_connection_info],
                  'tenant_id': req.environ['tacker.context'].project_id}
        scale_status = objects.ScaleInfo(
            aspect_id='vdu1_aspect', scale_level=1)
        mock_vnf_instance_get_by_id.return_value = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED, scale_status=scale_status,
            **update)
        mock_vnf_package_vnfd_get_by_id.return_value = \
            fakes.return_vnf_package_vnfd()
        mock_vnf_package_get_by_id.return_value = \
            fakes.return_vnf_package_with_deployment_flavour()
        mock_vnfd_dict.return_value = fakes.vnfd_dict_cnf()
        scale_request = fakes.scale_request_make("SCALE_OUT", 3)
        scale_request.aspect_id = "vdu1_aspect"
        mock_obj_from_primitive.return_value = scale_request
        mock_create.return_value = 200

        body = {
            "type": "SCALE_OUT",
            "aspectId": "vdu1_aspect",
            "numberOfSteps": 3,
            "additionalParams": {}}
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'
        resp = req.get_response(self.app)
        self.assertEqual(http_client.BAD_REQUEST, resp.status_code)
        mock_scale.assert_not_called()

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
            task_state=fields.VnfInstanceTaskState.ERROR,
            tenant_id=req.environ['tacker.context'].project_id)
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
            task_state=fields.VnfInstanceTaskState.ERROR,
            tenant_id=req.environ['tacker.context'].project_id)
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
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    def test_rollback_not_failed_temp(self, mock_vnf_get_by_id,
            mock_lcm_by_id,
            mock_get_service_plugins):
        req = fake_request.HTTPRequest.blank(
            '/vnf_lcm_op_occs/%s/rollback' % uuidsentinel.vnf_instance_id)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'
        vnf_instance = fakes.return_vnf_instance(
            tenant_id=req.environ['tacker.context'].project_id)
        mock_vnf_get_by_id.return_value = vnf_instance

        vnf_lcm_op_occs = fakes.vnflcm_rollback_active()
        mock_lcm_by_id.return_value = vnf_lcm_op_occs

        resp = req.get_response(self.app)
        self.assertEqual(http_client.CONFLICT, resp.status_code)

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfLcmOpOcc, "get_by_id",)
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    def test_rollback_not_ope(self, mock_vnf_get_by_id,
            mock_lcm_by_id,
            mock_get_service_plugins):
        req = fake_request.HTTPRequest.blank(
            '/vnf_lcm_op_occs/%s/rollback' % uuidsentinel.vnf_instance_id)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'
        vnf_instance = fakes.return_vnf_instance(
            tenant_id=req.environ['tacker.context'].project_id)
        mock_vnf_get_by_id.return_value = vnf_instance

        vnf_lcm_op_occs = fakes.vnflcm_rollback_ope()
        mock_lcm_by_id.return_value = vnf_lcm_op_occs

        resp = req.get_response(self.app)
        self.assertEqual(http_client.CONFLICT, resp.status_code)

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfLcmOpOcc, "get_by_id")
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    def test_rollback_not_scale_in(self, mock_vnf_get_by_id,
            mock_lcm_by_id,
            mock_get_service_plugins):
        req = fake_request.HTTPRequest.blank(
            '/vnf_lcm_op_occs/%s/rollback' % uuidsentinel.vnf_instance_id)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'
        vnf_instance = fakes.return_vnf_instance(
            tenant_id=req.environ['tacker.context'].project_id)
        mock_vnf_get_by_id.return_value = vnf_instance

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
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    def test_rollback_vnf_not_found(self, mock_vnf_get_by_id,
            mock_get_vnf, mock_lcm_by_id,
            mock_get_service_plugins):
        req = fake_request.HTTPRequest.blank(
            '/vnf_lcm_op_occs/%s/rollback' % uuidsentinel.vnf_instance_id)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'
        vnf_instance = fakes.return_vnf_instance(
            tenant_id=req.environ['tacker.context'].project_id)
        mock_vnf_get_by_id.return_value = vnf_instance

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

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': mock.MagicMock()})
    @mock.patch('oslo_utils.timeutils.is_newer_than')
    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    @mock.patch.object(objects.VnfLcmOpOcc, "save")
    @mock.patch.object(objects.VnfLcmOpOcc, "get_by_id")
    @ddt.data({'cancelMode': 'FORCEFUL'},
              {'cancelMode': 'GRACEFUL'})
    def test_cancel_lcm_op_occs(self, body, mock_lcm_get_by_id, mock_lcm_save,
            mock_vnf_get_by_id, mock_vnf_save, mock_is_newer_than,
            mock_get_service_plugins):
        req = fake_request.HTTPRequest.blank(
            '/vnf_lcm_op_occs/%s/cancel' % constants.UUID)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'
        req.body = jsonutils.dump_as_bytes(body)

        mock_is_newer_than.return_value = False
        mock_lcm_get_by_id.return_value = fakes.vnflcm_cancel_insta()
        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.NOT_INSTANTIATED,
            task_state=fields.VnfInstanceTaskState.INSTANTIATING,
            tenant_id=req.environ['tacker.context'].project_id)
        mock_vnf_get_by_id.return_value = vnf_instance

        resp = req.get_response(self.app)

        self.assertEqual(http_client.ACCEPTED, resp.status_code)

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': mock.MagicMock()})
    @mock.patch('oslo_utils.timeutils.is_newer_than')
    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    @mock.patch.object(objects.VnfLcmOpOcc, "save")
    @mock.patch.object(objects.VnfLcmOpOcc, "get_by_id")
    @ddt.data({'cancelMode': 'INVALID'},
              {'cancelMode': 0},
              {'cancelMode': True},
              {'cancelMode': ''},
              {'INVALID': 'GRACEFUL'},
              )
    def test_cancel_lcm_op_occs_invalid_body(self, body, mock_lcm_get_by_id,
            mock_lcm_save, mock_vnf_get_by_id, mock_vnf_save,
            mock_is_newer_than, mock_get_service_plugins):
        req = fake_request.HTTPRequest.blank(
            '/vnf_lcm_op_occs/%s/cancel' % constants.UUID)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'
        req.body = jsonutils.dump_as_bytes(body)

        mock_is_newer_than.return_value = False
        mock_lcm_get_by_id.return_value = fakes.vnflcm_cancel_insta()
        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.NOT_INSTANTIATED,
            task_state=fields.VnfInstanceTaskState.INSTANTIATING,
            tenant_id=req.environ['tacker.context'].project_id)
        mock_vnf_get_by_id.return_value = vnf_instance

        resp = req.get_response(self.app)

        self.assertEqual(http_client.BAD_REQUEST, resp.status_code)

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': mock.MagicMock()})
    @mock.patch('oslo_utils.timeutils.is_newer_than')
    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    @mock.patch.object(objects.VnfLcmOpOcc, "save")
    @mock.patch.object(objects.VnfLcmOpOcc, "get_by_id")
    def test_cancel_lcm_op_occs_before_timeout(self, mock_lcm_get_by_id,
            mock_lcm_save, mock_vnf_get_by_id, mock_vnf_save,
            mock_is_newer_than, mock_get_service_plugins):
        req = fake_request.HTTPRequest.blank(
            '/vnf_lcm_op_occs/%s/cancel' % constants.UUID)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'
        req.body = jsonutils.dump_as_bytes({'cancelMode': 'FORCEFUL'})

        mock_is_newer_than.return_value = True
        mock_lcm_get_by_id.return_value = fakes.vnflcm_cancel_insta()
        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.NOT_INSTANTIATED,
            task_state=fields.VnfInstanceTaskState.INSTANTIATING,
            tenant_id=req.environ['tacker.context'].project_id)
        mock_vnf_get_by_id.return_value = vnf_instance

        resp = req.get_response(self.app)

        self.assertEqual(http_client.CONFLICT, resp.status_code)

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': mock.MagicMock()})
    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    @mock.patch.object(objects.VnfLcmOpOcc, "save")
    @mock.patch.object(objects.VnfLcmOpOcc, "get_by_id")
    def test_cancel_lcm_op_occs_not_processing(self, mock_lcm_get_by_id,
            mock_lcm_save, mock_vnf_get_by_id, mock_vnf_save,
            mock_get_service_plugins):
        req = fake_request.HTTPRequest.blank(
            '/vnf_lcm_op_occs/%s/cancel' % constants.UUID)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'
        req.body = jsonutils.dump_as_bytes({'cancelMode': 'FORCEFUL'})

        fake_cancel_opocc = fakes.vnflcm_cancel_insta()
        fake_cancel_opocc.operation_state = 'NOTPROCESSING'
        mock_lcm_get_by_id.return_value = fake_cancel_opocc
        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.NOT_INSTANTIATED,
            task_state=fields.VnfInstanceTaskState.INSTANTIATING,
            tenant_id=req.environ['tacker.context'].project_id)
        mock_vnf_get_by_id.return_value = vnf_instance

        resp = req.get_response(self.app)

        self.assertEqual(http_client.CONFLICT, resp.status_code)

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': mock.MagicMock()})
    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    @mock.patch.object(objects.VnfLcmOpOcc, "save")
    @mock.patch.object(objects.VnfLcmOpOcc, "get_by_id")
    def test_cancel_lcm_op_occs_not_found_vnf_instance(self,
            mock_lcm_get_by_id, mock_lcm_save, mock_vnf_get_by_id,
            mock_vnf_save, mock_get_service_plugins):
        req = fake_request.HTTPRequest.blank(
            '/vnf_lcm_op_occs/%s/cancel' % constants.UUID)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'
        req.body = jsonutils.dump_as_bytes({'cancelMode': 'FORCEFUL'})

        mock_lcm_get_by_id.return_value = fakes.vnflcm_cancel_insta()
        mock_vnf_get_by_id.side_effect = exceptions.NotFound()

        resp = req.get_response(self.app)

        self.assertEqual(http_client.NOT_FOUND, resp.status_code)

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': mock.MagicMock()})
    @mock.patch.object(objects.VnfLcmOpOcc, "save")
    @mock.patch.object(objects.VnfLcmOpOcc, "get_by_id")
    def test_cancel_lcm_op_occs_not_found_op_occ(self, mock_lcm_get_by_id,
            mock_lcm_save, mock_get_service_plugins):
        req = fake_request.HTTPRequest.blank(
            '/vnf_lcm_op_occs/%s/cancel' % constants.UUID)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'
        req.body = jsonutils.dump_as_bytes({'cancelMode': 'FORCEFUL'})

        mock_lcm_get_by_id.side_effect = webob.exc.HTTPNotFound

        resp = req.get_response(self.app)

        self.assertEqual(http_client.NOT_FOUND, resp.status_code)

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': mock.MagicMock()})
    @mock.patch.object(objects.VnfLcmOpOcc, "save")
    @mock.patch.object(objects.VnfLcmOpOcc, "get_by_id")
    def test_cancel_lcm_op_occs_server_error1(self, mock_lcm_get_by_id,
            mock_lcm_save, mock_get_service_plugins):
        req = fake_request.HTTPRequest.blank(
            '/vnf_lcm_op_occs/%s/cancel' % constants.UUID)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'
        req.body = jsonutils.dump_as_bytes({'cancelMode': 'FORCEFUL'})

        mock_lcm_get_by_id.side_effect = Exception()

        resp = req.get_response(self.app)

        self.assertEqual(http_client.INTERNAL_SERVER_ERROR, resp.status_code)

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': mock.MagicMock()})
    @mock.patch('oslo_utils.timeutils.is_newer_than')
    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    @mock.patch.object(objects.VnfLcmOpOcc, "save")
    @mock.patch.object(objects.VnfLcmOpOcc, "get_by_id")
    def test_cancel_lcm_op_occs_server_error2(self, mock_lcm_get_by_id,
            mock_lcm_save, mock_vnf_get_by_id, mock_vnf_save,
            mock_is_newer_than, mock_get_service_plugins):
        req = fake_request.HTTPRequest.blank(
            '/vnf_lcm_op_occs/%s/cancel' % constants.UUID)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'
        req.body = jsonutils.dump_as_bytes({'cancelMode': 'FORCEFUL'})

        mock_is_newer_than.return_value = False
        mock_lcm_get_by_id.return_value = fakes.vnflcm_cancel_insta()
        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.NOT_INSTANTIATED,
            task_state=fields.VnfInstanceTaskState.INSTANTIATING,
            tenant_id=req.environ['tacker.context'].project_id)
        mock_vnf_get_by_id.return_value = vnf_instance
        mock_lcm_save.side_effect = Exception()

        resp = req.get_response(self.app)

        self.assertEqual(http_client.INTERNAL_SERVER_ERROR, resp.status_code)

    @mock.patch.object(vnf_lcm_rpc.VNFLcmRPCAPI, "send_notification")
    @mock.patch.object(controller.VnfLcmController,
                       "_update_vnf_fail_status")
    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    @mock.patch.object(objects.VnfLcmOpOcc, "save")
    @mock.patch.object(objects.VnfLcmOpOcc, "get_by_id")
    def test_fail_lcm_op_occs(self, mock_lcm_get_by_id,
            mock_lcm_save, mock_vnf_get_by_id,
            mock_vnf_save,
            mock_update,
            mock_send_notification):
        req = fake_request.HTTPRequest.blank(
            '/vnf_lcm_op_occs/%s/fail' % constants.UUID)
        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED,
            tenant_id=req.environ['tacker.context'].project_id)
        mock_vnf_get_by_id.return_value = vnf_instance
        mock_lcm_get_by_id.return_value = fakes.vnflcm_fail_insta()
        res_dict = self.controller.fail(req, constants.UUID)
        self.assertEqual('FAILED', res_dict['operationState'])
        self.assertIsNone(
            mock_send_notification.call_args[0][1].get("affectedVnfcs"))
        self.assertIsNone(
            mock_send_notification.call_args[0][1].get(
                "affectedVirtualStorages"))
        self.assertIsNone(
            mock_send_notification.call_args[0][1].get("affectedVirtualLinks"))

    @mock.patch.object(objects.VnfInstance, "get_by_id")
    @mock.patch.object(objects.VnfLcmOpOcc, "get_by_id")
    def test_fail_lcm_op_occs_not_found(self, mock_lcm_get_by_id,
                                        mock_vnf_get_by_id):
        req = fake_request.HTTPRequest.blank(
            '/vnf_lcm_op_occs/%s/fail' % constants.UUID)
        mock_lcm_get_by_id.side_effect = exceptions.NotFound()

        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'
        res_dict = self.controller.fail(req, constants.UUID)

        self.assertEqual(http_client.NOT_FOUND, res_dict.status_code)

    @mock.patch.object(objects.VnfInstance, "get_by_id")
    @mock.patch.object(objects.VnfLcmOpOcc, "get_by_id")
    def test_fail_lcm_op_occs_vnf_not_found(self, mock_lcm_get_by_id,
                                            mock_vnf_get_by_id):
        req = fake_request.HTTPRequest.blank(
            '/vnf_lcm_op_occs/%s/fail' % constants.UUID)
        mock_lcm_get_by_id.return_value = fakes.vnflcm_fail_insta()
        mock_vnf_get_by_id.side_effect = exceptions.VnfInstanceNotFound()

        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'
        res_dict = self.controller.fail(req, constants.UUID)

        self.assertEqual('VNF NOT FOUND', res_dict.json['title'])
        self.assertEqual(http_client.NOT_FOUND, res_dict.status_code)

    @mock.patch.object(objects.VnfLcmOpOcc, "get_by_id")
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    def test_fail_lcm_op_occs_vnf_not_failed_temp(
            self, mock_vnf_instance, mock_lcm_get_by_id):
        req = fake_request.HTTPRequest.blank(
            '/vnf_lcm_op_occs/%s/fail' % constants.UUID)
        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED,
            tenant_id=req.environ['tacker.context'].project_id)
        mock_vnf_instance.return_value = vnf_instance
        vnflcm_fail_object = fakes.vnflcm_fail_insta()
        vnflcm_fail_object.operation_state = 'STARTED'
        mock_lcm_get_by_id.return_value = vnflcm_fail_object

        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'
        res_dict = self.controller.fail(req, constants.UUID)

        self.assertEqual(http_client.CONFLICT, res_dict.status_code)

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfLcmOpOcc, "get_by_id")
    @mock.patch.object(controller.VnfLcmController, "_get_vnf")
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    @mock.patch.object(controller.VnfLcmController, "_instantiate")
    def test_retry_instantiate_vnf_instance(
            self, mock_instantiate, mock_vnf_instance, mock_get_vnf,
            mock_lcm_by_id, mock_get_service_plugins):
        req = fake_request.HTTPRequest.blank(
            '/vnf_lcm_op_occs/%s/retry' % uuidsentinel.vnf_lcm_op_occs_id)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        vnf_lcm_op_occs = fakes.vnflcm_op_occs_retry_data()
        mock_lcm_by_id.return_value = vnf_lcm_op_occs
        vnf_obj = fakes.vnf_data()
        mock_get_vnf.return_value = vnf_obj

        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED,
            tenant_id=req.environ['tacker.context'].project_id)
        mock_vnf_instance.return_value = vnf_instance

        resp = req.get_response(self.app)
        self.assertEqual(http_client.ACCEPTED, resp.status_code)
        mock_instantiate.assert_called_once()

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfLcmOpOcc, "get_by_id")
    @mock.patch.object(controller.VnfLcmController, "_get_vnf")
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    @mock.patch.object(controller.VnfLcmController, "_terminate")
    def test_retry_terminate_vnf_instance(
            self, mock_terminate, mock_vnf_instance, mock_get_vnf,
            mock_lcm_by_id, mock_get_service_plugins):
        req = fake_request.HTTPRequest.blank(
            '/vnf_lcm_op_occs/%s/retry' % uuidsentinel.vnf_lcm_op_occs_id)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        vnf_lcm_op_occs = fakes.vnflcm_op_occs_retry_data(
            operation='TERMINATE')
        mock_lcm_by_id.return_value = vnf_lcm_op_occs
        vnf_obj = fakes.vnf_data()
        mock_get_vnf.return_value = vnf_obj

        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED,
            tenant_id=req.environ['tacker.context'].project_id)
        mock_vnf_instance.return_value = vnf_instance

        resp = req.get_response(self.app)
        self.assertEqual(http_client.ACCEPTED, resp.status_code)
        mock_terminate.assert_called_once()

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfLcmOpOcc, "get_by_id")
    @mock.patch.object(controller.VnfLcmController, "_get_vnf")
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    @mock.patch.object(controller.VnfLcmController, "_heal")
    def test_retry_heal_vnf_instance(
            self, mock_heal, mock_vnf_instance, mock_get_vnf, mock_lcm_by_id,
            mock_get_service_plugins):
        req = fake_request.HTTPRequest.blank(
            '/vnf_lcm_op_occs/%s/retry' % uuidsentinel.vnf_lcm_op_occs_id)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        vnf_lcm_op_occs = fakes.vnflcm_op_occs_retry_data(operation='HEAL')
        mock_lcm_by_id.return_value = vnf_lcm_op_occs
        vnf_obj = fakes.vnf_data()
        mock_get_vnf.return_value = vnf_obj

        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED,
            tenant_id=req.environ['tacker.context'].project_id)
        mock_vnf_instance.return_value = vnf_instance

        resp = req.get_response(self.app)
        self.assertEqual(http_client.ACCEPTED, resp.status_code)
        mock_heal.assert_called_once()

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfLcmOpOcc, "get_by_id")
    @mock.patch.object(controller.VnfLcmController, "_get_vnf")
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    @mock.patch.object(controller.VnfLcmController, "_scale")
    def test_retry_scale_vnf_instance(
            self, mock_scale, mock_vnf_instance, mock_get_vnf, mock_lcm_by_id,
            mock_get_service_plugins):
        req = fake_request.HTTPRequest.blank(
            '/vnf_lcm_op_occs/%s/retry' % uuidsentinel.vnf_lcm_op_occs_id)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        vnf_lcm_op_occs = fakes.vnflcm_op_occs_retry_data(operation='SCALE')
        mock_lcm_by_id.return_value = vnf_lcm_op_occs
        vnf_obj = fakes.vnf_data()
        mock_get_vnf.return_value = vnf_obj

        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED,
            tenant_id=req.environ['tacker.context'].project_id)
        mock_vnf_instance.return_value = vnf_instance

        resp = req.get_response(self.app)
        self.assertEqual(http_client.ACCEPTED, resp.status_code)
        mock_scale.assert_called_once()

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfLcmOpOcc, "get_by_id")
    @mock.patch.object(controller.VnfLcmController, "_get_vnf")
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    @mock.patch.object(controller.VnfLcmController, "_change_ext_conn")
    def test_retry_change_ext_conn_vnf_instance(
            self, mock_change_ext_conn, mock_vnf_instance, mock_get_vnf,
            mock_lcm_by_id, mock_get_service_plugins):
        req = fake_request.HTTPRequest.blank(
            '/vnf_lcm_op_occs/%s/retry' % uuidsentinel.vnf_lcm_op_occs_id)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        vnf_lcm_op_occs = fakes.vnflcm_op_occs_retry_data(
            operation='CHANGE_EXT_CONN')
        mock_lcm_by_id.return_value = vnf_lcm_op_occs
        vnf_obj = fakes.vnf_data()
        mock_get_vnf.return_value = vnf_obj

        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED,
            tenant_id=req.environ['tacker.context'].project_id)
        mock_vnf_instance.return_value = vnf_instance

        resp = req.get_response(self.app)
        self.assertEqual(http_client.ACCEPTED, resp.status_code)
        mock_change_ext_conn.assert_called_once()

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfLcmOpOcc, "get_by_id")
    def test_retry_vnf_lcm_occ_not_found(
            self, mock_lcm_by_id, mock_get_service_plugins):
        req = fake_request.HTTPRequest.blank(
            '/vnf_lcm_op_occs/%s/retry' % uuidsentinel.vnf_lcm_op_occs_id)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        mock_lcm_by_id.side_effect = exceptions.NotFound

        resp = req.get_response(self.app)
        self.assertEqual(http_client.NOT_FOUND, resp.status_code)

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfLcmOpOcc, "get_by_id")
    def test_retry_vnf_lcm_occ_error(
            self, mock_lcm_by_id, mock_get_service_plugins):
        req = fake_request.HTTPRequest.blank(
            '/vnf_lcm_op_occs/%s/retry' % uuidsentinel.vnf_lcm_op_occs_id)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        mock_lcm_by_id.side_effect = Exception

        resp = req.get_response(self.app)
        self.assertEqual(http_client.INTERNAL_SERVER_ERROR, resp.status_code)

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfLcmOpOcc, "get_by_id")
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    def test_retry_vnf_lcm_occ_conflict(
            self, mock_vnf_instance, mock_lcm_by_id, mock_get_service_plugins):
        req = fake_request.HTTPRequest.blank(
            '/vnf_lcm_op_occs/%s/retry' % uuidsentinel.vnf_lcm_op_occs_id)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'
        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED,
            tenant_id=req.environ['tacker.context'].project_id)
        mock_vnf_instance.return_value = vnf_instance
        vnf_lcm_op_occs = fakes.vnflcm_op_occs_retry_data(
            operation_state='invalid operation state')
        mock_lcm_by_id.return_value = vnf_lcm_op_occs

        resp = req.get_response(self.app)
        self.assertEqual(http_client.CONFLICT, resp.status_code)

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfLcmOpOcc, "get_by_id")
    @mock.patch.object(controller.VnfLcmController, "_get_vnf")
    def test_retry_vnf_not_found(
            self, mock_get_vnf, mock_lcm_by_id, mock_get_service_plugins):
        req = fake_request.HTTPRequest.blank(
            '/vnf_lcm_op_occs/%s/retry' % uuidsentinel.vnf_lcm_op_occs_id)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        vnf_lcm_op_occs = fakes.vnflcm_op_occs_retry_data()
        mock_lcm_by_id.return_value = vnf_lcm_op_occs

        mock_get_vnf.side_effect = exc.HTTPNotFound

        resp = req.get_response(self.app)
        self.assertEqual(http_client.NOT_FOUND, resp.status_code)

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfLcmOpOcc, "get_by_id")
    @mock.patch.object(controller.VnfLcmController, "_get_vnf")
    def test_retry_vnf_error(
            self, mock_get_vnf, mock_lcm_by_id, mock_get_service_plugins):
        req = fake_request.HTTPRequest.blank(
            '/vnf_lcm_op_occs/%s/retry' % uuidsentinel.vnf_lcm_op_occs_id)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        vnf_lcm_op_occs = fakes.vnflcm_op_occs_retry_data()
        mock_lcm_by_id.return_value = vnf_lcm_op_occs

        mock_get_vnf.side_effect = exc.HTTPInternalServerError

        resp = req.get_response(self.app)
        self.assertEqual(http_client.INTERNAL_SERVER_ERROR, resp.status_code)

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfLcmOpOcc, "get_by_id")
    @mock.patch.object(controller.VnfLcmController, "_get_vnf")
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    def test_retry_vnf_instance_not_found(
            self, mock_get_vnf_instance, mock_get_vnf,
            mock_lcm_by_id, mock_get_service_plugins):
        req = fake_request.HTTPRequest.blank(
            '/vnf_lcm_op_occs/%s/retry' % uuidsentinel.vnf_lcm_op_occs_id)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        vnf_lcm_op_occs = fakes.vnflcm_op_occs_retry_data()
        mock_lcm_by_id.return_value = vnf_lcm_op_occs
        vnf_obj = fakes.vnf_data()
        mock_get_vnf.return_value = vnf_obj

        mock_get_vnf_instance.side_effect = exceptions.VnfInstanceNotFound

        resp = req.get_response(self.app)
        self.assertEqual(http_client.NOT_FOUND, resp.status_code)

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfLcmOpOcc, "get_by_id")
    @mock.patch.object(controller.VnfLcmController, "_get_vnf")
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    def test_retry_vnf_instance_error(
            self, mock_get_vnf_instance, mock_get_vnf,
            mock_lcm_by_id, mock_get_service_plugins):
        req = fake_request.HTTPRequest.blank(
            '/vnf_lcm_op_occs/%s/retry' % uuidsentinel.vnf_lcm_op_occs_id)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        vnf_lcm_op_occs = fakes.vnflcm_op_occs_retry_data()
        mock_lcm_by_id.return_value = vnf_lcm_op_occs
        vnf_obj = fakes.vnf_data()
        mock_get_vnf.return_value = vnf_obj

        mock_get_vnf_instance.side_effect = Exception

        resp = req.get_response(self.app)
        self.assertEqual(http_client.INTERNAL_SERVER_ERROR, resp.status_code)

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VnfLcmOpOcc, "get_by_id")
    @mock.patch.object(controller.VnfLcmController, "_get_vnf")
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    def test_retry_invalid_operation_type(
            self, mock_get_vnf_instance, mock_get_vnf,
            mock_lcm_by_id, mock_get_service_plugins):
        req = fake_request.HTTPRequest.blank(
            '/vnf_lcm_op_occs/%s/retry' % uuidsentinel.vnf_lcm_op_occs_id)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'
        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED,
            tenant_id=req.environ['tacker.context'].project_id)
        mock_get_vnf_instance.return_value = vnf_instance
        vnf_lcm_op_occs = fakes.vnflcm_op_occs_retry_data(
            operation='Invalid operation type')
        mock_lcm_by_id.return_value = vnf_lcm_op_occs
        vnf_obj = fakes.vnf_data()
        mock_get_vnf.return_value = vnf_obj

        resp = req.get_response(self.app)
        self.assertEqual(http_client.INTERNAL_SERVER_ERROR, resp.status_code)

    @mock.patch.object(objects.VnfLcmOpOccList, "get_by_marker_filter")
    def test_op_occ_list(self, mock_op_occ_list):
        req = fake_request.HTTPRequest.blank('/vnflcm/v1/vnf_lcm_op_occs')

        complex_attributes = [
            'error',
            'resourceChanges',
            'operationParams',
            'changedInfo']

        vnf_lcm_op_occ = fakes.return_vnf_lcm_opoccs_list()
        expected_result = fakes.index_response(
            remove_attrs=complex_attributes)
        mock_op_occ_list.return_value = vnf_lcm_op_occ
        resp = self.controller.list_lcm_op_occs(req)

        self.assertEqual(
            jsonutils.loads(jsonutils.dump_as_bytes(expected_result)),
            resp.json)

    @mock.patch.object(objects.vnf_lcm_op_occs.VnfLcmOpOccList,
                       "get_by_marker_filter")
    @mock.patch.object(objects.vnf_lcm_op_occs.VnfLcmOpOcc, "get_by_id")
    @ddt.data(
        {'params': {'all_records': 'yes'},
            'result_names': ['INSTANTIATE', 'SCALE', 'HEAL', 'TERMINATE']},
        {'params': {'all_records': 'yes', 'nextpage_opaque_marker':
            '22222222-2222-2222-2222-222222222222'},
            'result_names': ['INSTANTIATE', 'SCALE', 'HEAL', 'TERMINATE']},
        {'params': {'nextpage_opaque_marker':
            '44444444-4444-4444-4444-444444444444'},
            'result_names': []},
        {'params': {'nextpage_opaque_marker':
            '22222222-2222-2222-2222-222222222222'},
            'result_names': ['HEAL', 'TERMINATE']},
        {'params': {},
            'result_names': ['INSTANTIATE', 'SCALE']}
    )
    def test_op_occ_list_paging(self, values,
            mock_marker_obj,
            mock_op_occ_list):
        ids = ['11111111-1111-1111-1111-111111111111',
               '22222222-2222-2222-2222-222222222222',
               '33333333-3333-3333-3333-333333333333',
               '44444444-4444-4444-4444-444444444444',
               None]
        cfg.CONF.set_override('lcm_op_occ_num', 2, group='vnf_lcm')
        query = urllib.parse.urlencode(values['params'])
        req = fake_request.HTTPRequest.blank(
            '/vnflcm/v1/vnf_lcm_op_occs?' + query)
        target_index = []
        if 'all_records' in values['params'] \
                and values['params']['all_records'] == 'yes':
            mock_marker_obj.return_value = None
            target_index = [0, 1, 2, 3]
        elif 'nextpage_opaque_marker' in values['params']:
            mock_marker_obj.return_value = fakes.return_vnf_lcm_opoccs_obj(
                **{'id': values['params']['nextpage_opaque_marker']})
            if len(values['result_names']) > 0:
                target_index.append(
                    ids.index(mock_marker_obj.return_value['id']) + 1)
                target_index.append(
                    ids.index(mock_marker_obj.return_value['id']) + 2)
        else:
            mock_marker_obj.return_value = None
            target_index = [0, 1]

        mock_op_occ_list.return_value = []
        for index in range(len(target_index)):
            mock_op_occ_list.return_value.append(
                fakes.return_vnf_lcm_opoccs_obj(
                    **{'id': ids[target_index[index]],
                    'operation': values['result_names'][index]}))

        complex_attributes = [
            'error',
            'resourceChanges',
            'operationParams',
            'changedInfo']

        expected_result = []
        for index in range(len(target_index)):
            _links = fakes.index_response()[0]['_links']
            expected_links = re.sub("vnf_lcm_op_occs/[a-zA-Z0-9-]*",
                    "vnf_lcm_op_occs/{}".format(
                        ids[target_index[index]]), str(_links))
            expected_links = json.loads(expected_links.replace("'", '"'))
            expected_result += fakes.index_response(
                remove_attrs=complex_attributes,
                vnf_lcm_op_occs_updates={'operation':
                    values['result_names'][index],
                    'id': ids[target_index[index]],
                    '_links': expected_links})

        expected_result_link = None
        if 'all_records' not in values['params'] and len(target_index) >= 2:
            expected_result_link = (
                '<http://localhost//vnflcm/v1/vnf_lcm_op_occs' +
                '?nextpage_opaque_marker=%s>; rel="next"'
                % ids[target_index[1]])

        resp = self.controller.list_lcm_op_occs(req)

        self.assertEqual(
            jsonutils.loads(jsonutils.dump_as_bytes(expected_result)),
            resp.json)
        if expected_result_link is not None:
            self.assertEqual(expected_result_link, resp.headers['Link'])

    @mock.patch.object(objects.VnfLcmOpOccList, "get_by_marker_filter")
    @ddt.data(
        {'filter': '(eq,id,f26f181d-7891-4720-b022-b074ec1733ef)'},
        {'filter': '(neq,operationState,COMPLETED)'},
        {'filter': '(gte,stateEnteredTime,2020-03-14 04:10:15+00:00)'},
        {'filter': '(eq,isAutomaticInvocation,False)'},
        {'filter': '(lt,errorPoint,4)'},
        {'filter':
            """(eq,error,'"{"title": "ERROR",
            "status": 500, "detail": "ERROR"}"')"""},
        {'filter':
        """(in,changedInfo,'"{"vnfInstanceName": "test"}"')"""},
        {'filter':
            """(neq,operationParams,'"{"terminationType": "FORCEFUL"}"')"""},
    )
    def test_op_occ_filter_attributes(self, filter_params,
            mock_op_occ_list):
        query = urllib.parse.urlencode(filter_params)
        req = fake_request.HTTPRequest.blank(
            '/vnflcm/v1/vnf_lcm_op_occs?' + query)

        complex_attributes = [
            'error',
            'resourceChanges',
            'operationParams',
            'changedInfo']

        vnf_lcm_op_occ = fakes.return_vnf_lcm_opoccs_list()
        expected_result = fakes.index_response(
            remove_attrs=complex_attributes)
        mock_op_occ_list.return_value = vnf_lcm_op_occ
        res_dict = self.controller.list_lcm_op_occs(req)

        self.assertEqual(
            jsonutils.loads(jsonutils.dump_as_bytes(expected_result)),
            res_dict.json)

    @mock.patch.object(objects.VnfLcmOpOccList, "get_by_marker_filter")
    def test_op_occ_filter_attributes_invalid_filter(self,
            mock_op_occ_list):
        query = urllib.parse.urlencode({'filter': '(lt,non_existing,4)'})
        req = fake_request.HTTPRequest.blank(
            '/vnflcm/v1/vnf_lcm_op_occs?' + query)

        vnf_lcm_op_occ = fakes.return_vnf_lcm_opoccs_list()
        mock_op_occ_list.return_value = vnf_lcm_op_occ
        self.assertRaises(
            exceptions.ValidationError, self.controller.list_lcm_op_occs, req)

    @mock.patch.object(objects.VnfLcmOpOccList, "get_by_marker_filter")
    def test_op_occ_attribute_selector_all_fields(self,
            mock_op_occ_list):
        params = {'all_fields': 'True'}
        query = urllib.parse.urlencode(params)
        req = fake_request.HTTPRequest.blank('/vnflcm/v1/vnf_lcm_op_occs?' +
            query)

        vnf_lcm_op_occ = fakes.return_vnf_lcm_opoccs_list()
        expected_result = fakes.index_response()
        mock_op_occ_list.return_value = vnf_lcm_op_occ
        res_dict = self.controller.list_lcm_op_occs(req)

        self.assertEqual(
            jsonutils.loads(jsonutils.dump_as_bytes(expected_result)),
            res_dict.json)

    @mock.patch.object(objects.VnfLcmOpOccList, "get_by_marker_filter")
    @ddt.data(
        {'fields': 'error'},
        {'fields': 'resourceChanges'},
        {'fields': 'operationParams'},
        {'fields': 'changedInfo'}
    )
    def test_op_occ_attribute_selector_fields(self, filter_params,
            mock_op_occ_list):
        query = urllib.parse.urlencode(filter_params)
        req = fake_request.HTTPRequest.blank(
            '/vnflcm/v1/vnf_lcm_op_occs?' + query)

        complex_attributes = [
            'error',
            'resourceChanges',
            'operationParams',
            'changedInfo']

        remove_attributes = [
            x for x in complex_attributes if x != filter_params['fields']]

        vnf_lcm_op_occ = fakes.return_vnf_lcm_opoccs_list()
        expected_result = fakes.index_response(remove_attrs=remove_attributes)
        mock_op_occ_list.return_value = vnf_lcm_op_occ
        res_dict = self.controller.list_lcm_op_occs(req)
        self.assertEqual(
            jsonutils.loads(jsonutils.dump_as_bytes(expected_result)),
            res_dict.json)

    @mock.patch.object(objects.VnfLcmOpOccList, "get_by_marker_filter")
    @ddt.data(
        {'exclude_fields': 'error'},
        {'exclude_fields': 'resourceChanges'},
        {'exclude_fields': 'operationParams'},
        {'exclude_fields': 'changedInfo'}
    )
    def test_op_occ_attribute_selector_exclude_fields(self, filter_params,
            mock_op_occ_list):
        query = urllib.parse.urlencode(filter_params)
        req = fake_request.HTTPRequest.blank(
            '/vnflcm/v1/vnf_lcm_op_occs?' + query)

        remove_attributes = [filter_params['exclude_fields']]

        vnf_lcm_op_occ = fakes.return_vnf_lcm_opoccs_list()
        expected_result = fakes.index_response(remove_attrs=remove_attributes)
        mock_op_occ_list.return_value = vnf_lcm_op_occ
        res_dict = self.controller.list_lcm_op_occs(req)
        self.assertEqual(
            jsonutils.loads(jsonutils.dump_as_bytes(expected_result)),
            res_dict.json)

    @mock.patch.object(objects.VnfLcmOpOccList, "get_by_marker_filter")
    def test_op_occ_attribute_selector_fields_error(self,
            mock_op_occ_list):
        query = urllib.parse.urlencode({'fields': 'non_existent_column'})
        req = fake_request.HTTPRequest.blank(
            '/vnflcm/v1/vnf_lcm_op_occs?' + query)

        vnf_lcm_op_occ = fakes.return_vnf_lcm_opoccs_list()
        mock_op_occ_list.return_value = vnf_lcm_op_occ
        self.assertRaises(
            exceptions.ValidationError, self.controller.list_lcm_op_occs, req)

    @mock.patch.object(controller.VnfLcmController,
                       "_update_vnf_fail_status")
    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    @mock.patch.object(objects.VnfLcmOpOcc, "save")
    @mock.patch.object(objects.VnfLcmOpOcc, "get_by_id")
    def test_fail_lcm_op_occs_changed_info_missing(self, mock_lcm_get_by_id,
                              mock_lcm_save, mock_vnf_get_by_id,
                              mock_vnf_save, mock_update):
        req = fake_request.HTTPRequest.blank(
            '/vnf_lcm_op_occs/%s/fail' % constants.UUID)
        mock_lcm_get_by_id.return_value = \
            fakes.vnflcm_fail_insta()
        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED,
            tenant_id=req.environ['tacker.context'].project_id)
        mock_vnf_get_by_id.return_value = vnf_instance

        res_dict = self.controller.fail(req, constants.UUID)
        ref_dict = copy.deepcopy(fakes.VNFLCMOPOCC_RESPONSE)
        del ref_dict["changedInfo"]
        self.assertEqual(ref_dict.keys(), res_dict.keys())
        mock_lcm_get_by_id.assert_called_once()
        mock_vnf_get_by_id.assert_called_once()

    @mock.patch.object(controller.VnfLcmController,
                       "_update_vnf_fail_status")
    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    @mock.patch.object(objects.VnfLcmOpOcc, "save")
    @mock.patch.object(objects.VnfLcmOpOcc, "get_by_id")
    def test_fail_lcm_op_occs_check_added_params(self, mock_lcm_get_by_id,
                              mock_lcm_save, mock_vnf_get_by_id,
                              mock_vnf_save, mock_update):
        req = fake_request.HTTPRequest.blank(
            '/vnf_lcm_op_occs/%s/fail' % constants.UUID)
        mock_lcm_get_by_id.return_value = \
            fakes.vnflcm_fail_check_added_params()
        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED,
            tenant_id=req.environ['tacker.context'].project_id)
        mock_vnf_get_by_id.return_value = vnf_instance

        res_dict = self.controller.fail(req, constants.UUID)
        ref_dict = fakes.VNFLCMOPOCC_RESPONSE

        self.assertEqual(ref_dict.keys(), res_dict.keys())
        self.assertEqual(
            res_dict.get('changedInfo').keys(),
            ref_dict.get('changedInfo').keys())
        self.assertEqual(
            res_dict.get('_links').keys(),
            ref_dict.get('_links').keys())

        mock_lcm_get_by_id.assert_called_once()
        mock_vnf_get_by_id.assert_called_once()

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._notification_process')
    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._get_vnf')
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch.object(vnf_lcm_rpc.VNFLcmRPCAPI, "change_ext_conn")
    def test_change_ext_conn(self, mock_rpc, mock_save,
                  mock_vnf_by_id, mock_get_vnf,
                  mock_notification_process,
                  mock_get_service_plugins):
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/change_ext_conn' % uuidsentinel.vnf_instance_id)
        vnf_instance_obj = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED,
            tenant_id=req.environ['tacker.context'].project_id)
        mock_vnf_by_id.return_value = vnf_instance_obj
        mock_get_vnf.return_value = \
            self._get_dummy_vnf(vnf_id=vnf_instance_obj.id, status='ACTIVE')

        body = fakes.get_change_ext_conn_request_body()
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        resp = req.get_response(self.app)

        self.assertEqual(http_client.ACCEPTED, resp.status_code)
        mock_rpc.assert_called_once()

    @mock.patch('tacker.api.vnflcm.v1.controller.'
            'VnfLcmController._notification_process')
    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._notification_process')
    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._get_vnf')
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch.object(vnf_lcm_rpc.VNFLcmRPCAPI, "change_ext_conn")
    def test_change_ext_conn_location(self, mock_rpc, mock_save,
            mock_vnf_by_id, mock_get_vnf,
            mock_notification_process,
            mock_get_service_plugins, mock_insta_notfi_process):
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/change_ext_conn' % uuidsentinel.vnf_instance_id)
        vnf_instance_obj = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED,
            tenant_id=req.environ['tacker.context'].project_id)
        mock_vnf_by_id.return_value = vnf_instance_obj
        mock_get_vnf.return_value = \
            self._get_dummy_vnf(vnf_id=vnf_instance_obj.id, status='ACTIVE')
        body = fakes.get_change_ext_conn_request_body()
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'
        resp = req.get_response(self.app)
        self.assertTrue('Location' in resp.headers.keys())
        expected_location = (self.expected_location_prefix +
                str(mock_insta_notfi_process.return_value))
        self.assertEqual(expected_location, resp.headers['location'])
        self.assertEqual(http_client.ACCEPTED, resp.status_code)

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._get_vnf')
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    def test_change_ext_conn_incorrect_instantiated_state(
            self, mock_vnf_by_id, mock_get_vnf,
            mock_get_service_plugins):
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/change_ext_conn' % uuidsentinel.vnf_instance_id)
        vnf_instance_obj = fakes.return_vnf_instance(
            fields.VnfInstanceState.NOT_INSTANTIATED,
            tenant_id=req.environ['tacker.context'].project_id)
        mock_vnf_by_id.return_value = vnf_instance_obj

        body = fakes.get_change_ext_conn_request_body()
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        resp = req.get_response(self.app)

        self.assertEqual(http_client.CONFLICT, resp.status_code)
        expected_msg = ("VNF is not instantiated")
        self.assertEqual(expected_msg, resp.json['detail'])

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
    @ddt.data('HEAD', 'PUT', 'DELETE', 'PATCH', 'GET')
    def test_change_ext_conn_invalid_http_method(self, method,
                                      mock_get_service_plugins):
        body = {}
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/change_ext_conn' % uuidsentinel.vnf_instance_id)
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = method

        resp = req.get_response(self.app)

        self.assertEqual(http_client.METHOD_NOT_ALLOWED, resp.status_code)

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._notification_process')
    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._get_vnf')
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch.object(vnf_lcm_rpc.VNFLcmRPCAPI, "change_ext_conn")
    @ddt.data(
        {
            "type": "IPV4",
        },
        {
            "type": "IPV4",
            "fixedAddresses": ["22.22.1.20"],
            "numDynamicAddresses": 1,
            "subnetId": '497b7a75-6c10-4a74-85fa-83d498da2501',
        },
        {
            "type": "IPV4",
            "numDynamicAddresses": 0,
            "subnetId": '497b7a75-6c10-4a74-85fa-83d498da2501',
        },
    )
    def test_change_ext_conn_with_invalid_requests(
            self,
            ip_address,
            mock_rpc,
            mock_save,
            mock_vnf_by_id,
            mock_get_vnf,
            mock_notification_process,
            mock_get_service_plugins):
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/change_ext_conn' % uuidsentinel.vnf_instance_id)
        vnf_instance_obj = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED,
            tenant_id=req.environ['tacker.context'].project_id)
        mock_vnf_by_id.return_value = vnf_instance_obj
        mock_get_vnf.return_value = \
            self._get_dummy_vnf(vnf_id=vnf_instance_obj.id, status='ACTIVE')

        body = fakes.get_change_ext_conn_request_body()
        body['extVirtualLinks'][0]['extCps'][0]['cpConfig'][0][
            'cpProtocolData'][0]['ipOverEthernet'][
                'ipAddresses'] = [ip_address]
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        resp = req.get_response(self.app)

        self.assertEqual(
            resp.status_code, http_client.BAD_REQUEST)

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
    def test_change_ext_conn_with_invalid_uuid(self, mock_get_service_plugins):
        body = fakes.get_change_ext_conn_request_body()
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/change_ext_conn' % constants.INVALID_UUID)
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        resp = req.get_response(self.app)

        self.assertEqual(http_client.NOT_FOUND, resp.status_code)
        self.assertIn('application/problem+json', resp.headers['Content-Type'])
        self.assertEqual(
            "Can not find requested vnf: %s" % constants.INVALID_UUID,
            resp.json['detail'])

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    @ddt.data('operationTypes', 'operationStates')
    def test_register_subscription_operation_mismatch(
            self, attribute, mock_get_service_plugins):
        body = {
            'callbackUri': 'http://sample_callback_uri',
            'filter': {
                'notificationType': [
                    'VnfLcmOperationOccurrenceNotification'],
                attribute: ['sample_operation']
            }
        }

        req = fake_request.HTTPRequest.blank(
            '/subscriptions')
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        resp = req.get_response(self.app)

        self.assertEqual(http_client.BAD_REQUEST, resp.status_code)

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    def test_register_subscription_operation_notification_mismatch(
            self, mock_get_service_plugins):
        body = {
            'callbackUri': 'http://sample_callback_uri',
            'filter': {
                'notificationTypes': ['sample_notification'],
            }
        }

        req = fake_request.HTTPRequest.blank(
            '/subscriptions')
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        resp = req.get_response(self.app)

        self.assertEqual(http_client.BAD_REQUEST, resp.status_code)

    @mock.patch.object(subscription_obj.LccnSubscriptionRequest, 'create')
    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    def test_register_subscription_vnf_instance_subscription_filter(
            self, mock_get_service_plugins, mock_create):
        cfg.CONF.set_override('test_callback_uri', False,
                              group='vnf_lcm')
        body = {
            'callbackUri': 'http://sample_callback_uri',
            'filter': {
                'notificationTypes': ['VnfLcmOperationOccurrenceNotification'],
                'vnfInstanceSubscriptionFilter': {
                    "vnfdIds": [],
                    "vnfProductsFromProviders": [{
                        "vnfProvider": "Vnf Provider 1",
                        "vnfProducts": [
                            {
                                "vnfProductName": "Vnf Product 1",
                                "versions": [
                                    {
                                        "vnfSoftwareVersion": "v1",
                                        "vnfdVersions": ["vnfd.v1.1"]
                                    }
                                ]
                            }
                        ]
                    }]
                }
            }
        }

        req = fake_request.HTTPRequest.blank(
            '/subscriptions')
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'
        resp = req.get_response(self.app)
        self.assertEqual(http_client.CREATED, resp.status_code)

    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    def test_register_subscription_vnf_instance_subscription_filter_error(
            self, mock_get_service_plugins):
        body = {
            'callbackUri': 'http://sample_callback_uri',
            'filter': {
                'notificationTypes': ['VnfLcmOperationOccurrenceNotification'],
                'vnfInstanceSubscriptionFilter': {
                    "vnfdIds": [],
                    "vnfProductsFromProviders": {
                        "vnfProducts": [
                            {
                                "vnfProductName": "Vnf Product 1",
                                "versions": [
                                    {
                                        "vnfSoftwareVersion": "v1",
                                        "vnfdVersions": ["vnfd.v1.1"]
                                    }
                                ]
                            }
                        ]
                    }
                }
            }
        }

        req = fake_request.HTTPRequest.blank(
            '/subscriptions')
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        resp = req.get_response(self.app)
        self.assertEqual(http_client.BAD_REQUEST, resp.status_code)

    @mock.patch.object(subscription_obj.LccnSubscriptionRequest, 'create')
    @mock.patch.object(TackerManager, 'get_service_plugins',
        return_value={'VNFM': FakeVNFMPlugin()})
    def test_register_subscription(
            self, mock_get_service_plugins, mock_create):
        cfg.CONF.set_override('test_callback_uri', False,
                              group='vnf_lcm')
        body = {
            'callbackUri': 'http://sample_callback_uri'
        }
        res_create = {
            'id': uuidsentinel.subscription_id,
            'callback_uri': body['callbackUri']
        }
        mock_create.return_value = objects.LccnSubscriptionRequest(
            **res_create)
        req = fake_request.HTTPRequest.blank(
            '/subscriptions')
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        resp = req.get_response(self.app)
        self.assertEqual(http_client.CREATED, resp.status_code)

    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._test_notification')
    @mock.patch.object(subscription_obj.LccnSubscriptionRequest, 'create')
    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
    def test_register_subscription_authentication(
            self, mock_get_service_plugins, mock_create,
            mock_test_notification):
        cfg.CONF.set_override('test_callback_uri', True,
                              group='vnf_lcm')
        mock_test_notification.return_value = 1
        auth_user_name = 'test_user'
        auth_password = 'test_password'
        token_endpoint = 'https://oauth2/tokens'
        body = {
            'callbackUri': 'http://sample_callback_uri',
            "authentication": {
                "authType": ["OAUTH2_CLIENT_CREDENTIALS"],
                "paramsOauth2ClientCredentials": {
                    "clientId": auth_user_name,
                    "clientPassword": auth_password,
                    "tokenEndpoint": token_endpoint
                }
            }
        }
        res_create = {
            'id': uuidsentinel.subscription_id,
            'callback_uri': body['callbackUri'],
            "authentication": jsonutils.dumps(body["authentication"])
        }
        mock_create.return_value = objects.LccnSubscriptionRequest(
            **res_create)

        req = fake_request.HTTPRequest.blank(
            '/subscriptions')
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        resp = req.get_response(self.app)
        self.assertEqual(http_client.CREATED, resp.status_code)

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(vnf_subscription_view.ViewBuilder,
                       "subscription_list")
    @mock.patch.object(vnf_subscription_view.ViewBuilder,
                       "validate_filter")
    @mock.patch.object(objects.LccnSubscriptionList,
                       "get_by_marker_filter")
    def test_subscription_list_all(self,
            mock_subscription_list,
            mock_subscription_filter,
            mock_subscription_view,
            mock_get_service_plugins):
        mock_subscription_filter.return_value = None
        last = True
        req = fake_request.HTTPRequest.blank('/subscriptions')
        req.method = 'GET'
        mock_subscription_list.return_value = [fakes.
            return_vnf_subscription_list(), last]
        mock_subscription_view.return_value = fakes. \
            return_vnf_subscription_list()
        resp = req.get_response(self.app)
        expected_result = fakes.return_vnf_subscription_list()
        self.assertEqual(200, resp.status_code)
        self.assertEqual(expected_result, resp.json)

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(vnf_subscription_view.ViewBuilder,
                       "subscription_list")
    @mock.patch.object(vnf_subscription_view.ViewBuilder,
                       "validate_filter")
    @mock.patch.object(objects.LccnSubscriptionList,
                       "get_by_marker_filter")
    def test_subscription_list_empty(self,
            mock_subscription_list,
            mock_subscription_filter,
            mock_subscription_view,
            mock_get_service_plugins):
        mock_subscription_filter.return_value = None
        last = True
        req = fake_request.HTTPRequest.blank('/subscriptions')
        req.method = 'GET'
        mock_subscription_list.return_value = [fakes.
            return_vnf_subscription_list(), last]
        mock_subscription_view.return_value = []
        resp = req.get_response(self.app)
        self.assertEqual(200, resp.status_code)
        self.assertEqual([], resp.json)

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(vnf_subscription_view.ViewBuilder,
                       "validate_filter")
    def test_subscription_list_error(self,
            mock_subscription_filter,
            mock_get_service_plugins):
        req = fake_request.HTTPRequest.blank(
            '/subscriptions')
        req.method = 'GET'
        mock_subscription_filter.side_effect = Exception

        resp = req.get_response(self.app)
        self.assertEqual(500, resp.status_code)

    @mock.patch.object(objects.vnf_lcm_subscriptions.LccnSubscriptionList,
                       "get_by_marker_filter")
    @mock.patch.object(objects.LccnSubscription, "get_by_id")
    @ddt.data(
        {'params': {'all_records': 'yes'},
            'result_names': ['subscription_id_1', 'subscription_id_2',
                'subscription_id_3', 'subscription_id_4']},
        {'params': {'all_records': 'yes', 'nextpage_opaque_marker':
            '22222222-2222-2222-2222-222222222222'},
            'result_names': ['subscription_id_1', 'subscription_id_2',
                'subscription_id_3', 'subscription_id_4']},
        {'params': {'nextpage_opaque_marker':
            '44444444-4444-4444-4444-444444444444'},
            'result_names': []},
        {'params': {'nextpage_opaque_marker':
            '22222222-2222-2222-2222-222222222222'},
            'result_names': ['subscription_id_3', 'subscription_id_4']},
        {'params': {},
            'result_names': ['subscription_id_1', 'subscription_id_2']}
    )
    def test_subscription_list_paging(self,
            values,
            mock_marker_obj,
            mock_subscription_list):
        ids = ['11111111-1111-1111-1111-111111111111',
               '22222222-2222-2222-2222-222222222222',
               '33333333-3333-3333-3333-333333333333',
               '44444444-4444-4444-4444-444444444444',
               None]
        mock_marker_obj.return_value = None
        cfg.CONF.set_override('subscription_num', 2, group='vnf_lcm')
        query = urllib.parse.urlencode(values['params'])
        req = fake_request.HTTPRequest.blank('/subscriptions?' + query)
        req.method = 'GET'

        target_index = []
        if 'all_records' in values['params'] \
                and values['params']['all_records'] == 'yes':
            mock_marker_obj = None
            target_index = [0, 1, 2, 3]
        elif 'nextpage_opaque_marker' in values['params']:
            mock_marker_obj.return_value = fakes.return_subscription_object(
                **{'id': values['params']['nextpage_opaque_marker']})
            marker_obj_index = ids.index(mock_marker_obj.return_value['id'])
            for i in range(marker_obj_index + 1, len(ids) - 1):
                target_index.append(i)
        else:
            mock_marker_obj.return_value = None
            target_index = [0, 1]

        mock_subscription_list.return_value = []

        for index in range(len(target_index)):
            mock_subscription_list.return_value.append(
                fakes.return_lccn_subscription_obj(**{'id':
                    ids[target_index[index]]}))

        resp = self.controller.subscription_list(req)

        expected_result = []
        for index in range(len(target_index)):
            href = ("http://localhost:9890//vnflcm/v1/subscriptions/{}"
                .format(ids[target_index[index]]))
            _link = {'self': {'href': href}}

            subscription_object = fakes.return_subscription_object(
                **{'id': ids[target_index[index]], '_links': _link})

            subscription_object['callbackUri'] = \
                subscription_object.pop('callback_uri')
            expected_result.append(subscription_object)

        expected_result_link = None
        if 'all_records' not in values['params'] and len(target_index) >= 2:
            expected_result_link = (
                '<http://localhost//subscriptions' +
                '?nextpage_opaque_marker=%s>; rel="next"'
                % ids[target_index[1]])

        self.assertEqual(200, resp.status_code)
        self.assertEqual(expected_result, resp.json)
        if expected_result_link is not None:
            self.assertEqual(expected_result_link, resp.headers['Link'])

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.LccnSubscriptionRequest,
                       "vnf_lcm_subscriptions_show")
    def test_subscription_show(self, mock_get_subscription,
            mock_get_service_plugins):
        mock_get_subscription.return_value =\
            fakes.return_lccn_subscription_obj()

        req = fake_request.HTTPRequest.blank(
            '/subscriptions/%s' % uuidsentinel.subscription_id)
        req.method = 'GET'

        resp = req.get_response(self.app)

        expected_vnf = fakes.fake_subscription_response()

        self.assertEqual(http_client.OK, resp.status_code)
        self.assertEqual(expected_vnf, resp.json)

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(vnf_subscription_view.ViewBuilder,
                       "subscription_list")
    @mock.patch.object(vnf_subscription_view.ViewBuilder,
                       "validate_filter")
    @mock.patch.object(objects.LccnSubscriptionList,
                       "get_by_marker_filter")
    @ddt.data(
        {'operator': "eq", 'key': 'id',
         'value': uuidsentinel.subscription_id},
        {'operator': "cont", 'key': 'callbackUri',
         'value': 'http://localhost/sample_callback_uri'},
        {'operator': "neq", 'key': 'id',
         'value': uuidsentinel.subscription_id},
        {'operator': "eq", 'key': 'notificationTypes',
         'value': 'VnfLcmOperationOccurrenceNotification'},
        {'operator': "neq", 'key': 'operationTypes', 'value': 'INSTANTIATE'},
        {'operator': "cont", 'key': 'operationStates', 'value': 'STARTING'}
    )
    @ddt.unpack
    def test_subscription_list_filter(self,
            mock_subscription_list,
            mock_subscription_filter,
            mock_subscription_view,
            mock_get_service_plugins,
            operator, key, value):
        """Tests all supported operators in filter expression."""
        filters = {
            'filter': ("(%s,%s,%s)" % (operator, key, value))
        }
        query = urllib.parse.urlencode(filters)

        req = fake_request.HTTPRequest.blank(
            '/subscriptions?' + query)
        req.method = 'GET'
        body_2 = {}
        mock_subscription_filter.return_value = filters
        last = True
        if operator == 'neq':
            body_2 = {key: uuidsentinel.subscription_id_2}

        mock_subscription_list.return_value = [fakes.
            return_vnf_subscription_list(), last]
        mock_subscription_view.return_value = fakes. \
            return_vnf_subscription_list()

        resp = req.get_response(self.app)
        expected_result = fakes.return_vnf_subscription_list(**body_2)

        if operator == 'neq':
            self.assertNotEqual(expected_result, resp.json)
        else:
            self.assertEqual(expected_result, resp.json)

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.LccnSubscriptionRequest,
                       "vnf_lcm_subscriptions_show")
    def test_subscription_show_not_found(self, mock_get_subscription,
            mock_get_service_plugins):
        req = fake_request.HTTPRequest.blank(
            '/subscriptions/%s' % uuidsentinel.subscription_id)
        req.method = 'GET'

        mock_get_subscription.return_value = None

        msg = _("Can not find requested vnf lcm subscriptions: %s"
                % uuidsentinel.subscription_id)
        res = self._make_problem_detail(msg, 404, title='Not Found')

        resp = req.get_response(self.app)
        self.assertEqual(res.text, resp.text)

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
    def test_subscription_list_filter_error(self,
            mock_get_service_plugins):

        req = fake_request.HTTPRequest.blank(
            '/subscriptions?filter')
        req.method = 'GET'
        resp = req.get_response(self.app)

        self.assertEqual(400, resp.status_code)

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.LccnSubscriptionRequest,
                       "vnf_lcm_subscriptions_show")
    def test_subscription_show_error(self, mock_get_subscription,
            mock_get_service_plugins):
        req = fake_request.HTTPRequest.blank(
            '/subscriptions/%s' % uuidsentinel.subscription_id)
        req.method = 'GET'

        mock_get_subscription.side_effect = Exception

        resp = req.get_response(self.app)
        self.assertEqual(500, resp.status_code)

    @mock.patch.object(vim_client.VimClient, "get_vim")
    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._update_package_usage_state')
    @mock.patch.object(objects.VnfPackage, 'get_by_id')
    @mock.patch.object(objects.vnf_package.VnfPackage, 'save')
    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.vnf_instance, '_vnf_instance_create')
    @mock.patch.object(objects.vnf_package_vnfd.VnfPackageVnfd, 'get_by_id')
    def test_create_using_internal_methods(
            self, mock_get_by_id,
            mock_vnf_instance_create,
            mock_get_service_plugins,
            mock_package_save,
            mock_vnf_package_get_by_id,
            mock_update_package_usage_state,
            mock_get_vim):
        mock_get_vim.return_value = self.vim_info
        mock_get_by_id.return_value = fakes.return_vnf_package_vnfd()
        mock_vnf_package_get_by_id.return_value = \
            fakes.return_vnf_package_with_deployment_flavour()

        req = fake_request.HTTPRequest.blank('/vnf_instances')
        updates = {'vnfd_id': uuidsentinel.vnfd_id,
                'vnf_instance_description': 'SampleVnf Description',
                'vnf_instance_name': 'SampleVnf',
                'vnf_pkg_id': uuidsentinel.vnf_pkg_id,
                'vnf_metadata': {"key": "value"},
                'tenant_id': req.environ['tacker.context'].project_id}

        mock_vnf_instance_create.return_value =\
            fakes.return_vnf_instance_model(**updates)

        body = {'vnfdId': uuidsentinel.vnfd_id,
                "vnfInstanceName": "SampleVnf",
                "vnfInstanceDescription": "SampleVnf Description",
                'metadata': {"key": "value"}}
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'
        req.environ['tacker.context'] = self.context

        # Call Create API
        resp = req.get_response(self.app)

        self.assertEqual(500, resp.status_code)
        self.assertIn('application/problem+json', resp.headers['Content-Type'])
        expected_vnf = {'tackerFault': {'code': 500,
                 'message': 'Unexpected API Error. Please report this at '
                            'http://bugs.launchpad.net/tacker/ and attach the '
                            'Tacker API log if possible.\n'
                            "<class 'webob.exc.HTTPInternalServerError'>"}}
        expected_msg = expected_vnf['tackerFault']['message']
        self.assertEqual(expected_msg, resp.json['detail'])


@ddt.ddt
class TestControllerEnhancedPolicy(TestController):

    def setUp(self):
        super(TestControllerEnhancedPolicy, self).setUp()
        cfg.CONF.set_override(
            "enhanced_tacker_policy", True, group='oslo_policy')

    @mock.patch.object(objects.VnfInstance, "get_by_id")
    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VNF, "vnf_index_list")
    @mock.patch.object(objects.VnfInstanceList, "vnf_instance_list")
    @mock.patch.object(objects.VnfPackageVnfd, 'get_vnf_package_vnfd')
    @mock.patch.object(vnf_lcm_rpc.VNFLcmRPCAPI, "update")
    def test_update_vnf_with_pkg_id(
            self, mock_update,
            mock_vnf_package_vnf_get_vnf_package_vnfd,
            mock_vnf_instance_list, mock_vnf_index_list,
            mock_get_service_plugins, mock_vnf_by_id):
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s' % constants.UUID)
        mock_vnf_by_id.return_value = fakes.return_vnf_instance()
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
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'PATCH'

        # Call Instantiate API
        resp = req.get_response(self.app)
        self.assertEqual(http_client.ACCEPTED, resp.status_code)
        mock_update.assert_called_once()

    @mock.patch.object(objects.VnfInstance, "get_by_id")
    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VNF, "vnf_index_list")
    def test_update_vnf_status_err(
            self,
            mock_vnf_index_list,
            mock_get_service_plugins,
            mock_vnf_by_id):
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s' % constants.UUID)
        mock_vnf_by_id.return_value = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED)
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
        req.body = jsonutils.dump_as_bytes(body)

        req.headers['Content-Type'] = 'application/json'
        req.method = 'PATCH'

        msg = _("VNF %(id)s status is %(state)s") % {
            "id": constants.UUID, "state": "ERROR"}
        res = self._make_problem_detail(msg %
                                        {"state": "ERROR"}, 409, 'Conflict')

        resp = req.get_response(self.app)
        self.assertEqual(res.text, resp.text)

    @mock.patch.object(objects.VnfInstance, "get_by_id")
    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
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
            mock_get_service_plugins,
            mock_vnf_by_id):

        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s' % constants.UUID)
        mock_vnf_by_id.return_value = fakes.return_vnf_instance()
        mock_vnf_index_list.return_value = fakes._get_vnf()
        mock_vnf_instance_list.return_value = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED,
            tenant_id=req.environ['tacker.context'].project_id)
        mock_vnf_package_vnf_get_vnf_package_vnfd.return_value = ""
        mock_get_vnf_package_vnfd.side_effect =\
            exceptions.VnfPackageVnfdNotFound
        mock_create_package.return_value = fakes.return_vnf_package_vnfd()
        mock_response = mock.MagicMock()
        mock_response.ok = True
        mock_response.json = mock.MagicMock()
        mock_response.json.return_value = ['aaa', 'bbb', 'ccc']

        mock_index.return_value = mock_response

        body = {
            "vnfInstanceName": "new_instance_name",
            "vnfInstanceDescription": "new_instance_discription",
            "vnfPkgId": "2c69a161-0000-4b0f-bcf8-391f8fc76600",
            "vnfConfigurableProperties": {"test": "test_value"},
            "vnfcInfoModificationsDeleteIds": ["test1"]
        }
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'PATCH'

        resp = req.get_response(self.app)
        self.assertEqual(http_client.ACCEPTED, resp.status_code)
        mock_update.assert_called_once()

    @mock.patch.object(objects.VnfInstance, "get_by_id")
    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VNF, "vnf_index_list")
    def test_update_vnf_none_vnf_data(
            self,
            mock_vnf_index_list,
            mock_get_service_plugins,
            mock_vnf_by_id):

        mock_vnf_by_id.return_value = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED)
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

    @mock.patch.object(objects.VnfInstance, "get_by_id")
    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VNF, "vnf_index_list")
    @mock.patch.object(objects.VnfInstanceList, "vnf_instance_list")
    def test_update_vnf_none_instance_data(
            self,
            mock_vnf_instance_list,
            mock_vnf_index_list,
            mock_get_service_plugins,
            mock_vnf_by_id):

        mock_vnf_by_id.return_value = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED)
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

    @mock.patch.object(objects.VnfInstance, "get_by_id")
    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
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
            mock_get_service_plugins,
            mock_vnf_by_id):

        mock_vnf_by_id.return_value = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED)
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

    @ddt.data("vnfdId", "vnfPkgId")
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
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
            mock_get_service_plugins,
            mock_vnf_by_id):
        mock_vnf_by_id.return_value = fakes.return_vnf_instance()
        mock_vnf_index_list.return_value = fakes._get_vnf()
        mock_vnf_instance_list.return_value = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED)
        mock_vnf_package_vnf_get_vnf_package_vnfd.return_value = ""
        mock_get_vnf_package_vnfd.side_effect = \
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

    @ddt.data(*fakes.get_test_data_policy_vnf_not_instantiated(
        'show'))
    @ddt.unpack
    @mock.patch.object(objects.vnf_instance, "_vnf_instance_get_by_id")
    def test_show_enhanced_policy_vnf_not_instantiated(
            self, mock_vnf_by_id, vnf_instance_updates,
            rules, roles, expected_status_code):
        mock_vnf_by_id.return_value = fakes.return_vnf_instance_model(
            **vnf_instance_updates)

        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s' % uuidsentinel.instance_id)
        req.method = 'GET'
        policy.set_rules(oslo_policy.Rules.from_dict(rules), overwrite=True)
        ctx = context.Context(
            'fake', 'fake', roles=roles)
        resp = req.get_response(fakes.wsgi_app_v1(fake_auth_context=ctx))
        self.assertEqual(expected_status_code, resp.status_code)

    @ddt.data(*fakes.get_test_data_policy_vnf_instantiated(
        'show', http_client.OK))
    @ddt.unpack
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    def test_show_enhanced_policy_vnf_instantiated(
            self, mock_vnf_by_id, vnf_instance_updates,
            rules, roles, expected_status_code):
        mock_vnf_by_id.return_value = fakes.return_vnf_instance(
            instantiated_state=fields.VnfInstanceState.INSTANTIATED,
            **vnf_instance_updates)

        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s' % uuidsentinel.instance_id)
        req.method = 'GET'
        policy.set_rules(oslo_policy.Rules.from_dict(rules), overwrite=True)
        ctx = context.Context(
            'fake', 'fake', roles=roles)
        resp = req.get_response(fakes.wsgi_app_v1(fake_auth_context=ctx))
        self.assertEqual(expected_status_code, resp.status_code)

    @ddt.data(*fakes.get_test_data_policy_create())
    @ddt.unpack
    @mock.patch.object(objects.VnfPackage, 'get_by_id')
    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._create_vnf')
    @mock.patch.object(objects.vnf_instance, '_vnf_instance_update')
    @mock.patch.object(objects.vnf_instance, '_vnf_instance_create')
    @mock.patch.object(vim_client.VimClient, "get_vim")
    @mock.patch.object(objects.VnfPackageVnfd, 'get_by_id')
    def test_create_enhanced_policy(
            self,
            mock_vnf_package_vnfd_get_by_id,
            mock_get_vim,
            mock_vnf_instance_create,
            mock_vnf_instance_update,
            mock_private_create_vnf,
            mock_vnf_package_get_by_id,
            vnfd_updates,
            rules,
            roles,
            expected_status_code):

        mock_vnf_package_vnfd_get_by_id.return_value = \
            fakes.return_vnf_package_vnfd(
                **vnfd_updates)
        updates = {'vnfd_id': uuidsentinel.vnfd_id}
        mock_vnf_instance_create.return_value = \
            fakes.return_vnf_instance_model(**updates)
        mock_vnf_instance_update.return_value = \
            fakes.return_vnf_instance_model(**updates)
        mock_get_vim.return_value = self.vim_info

        body = {'vnfdId': uuidsentinel.vnfd_id,
                'metadata': {"key": "value"}}
        req = fake_request.HTTPRequest.blank('/vnf_instances')
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        policy.set_rules(oslo_policy.Rules.from_dict(rules), overwrite=True)
        ctx = context.Context(
            'fake', 'fake', roles=roles)
        resp = req.get_response(fakes.wsgi_app_v1(fake_auth_context=ctx))
        self.assertEqual(expected_status_code, resp.status_code)

    @ddt.data(*fakes.get_test_data_policy_vnf_instantiated(
        'terminate', http_client.ACCEPTED))
    @ddt.unpack
    @mock.patch.object(vnf_lcm_rpc.VNFLcmRPCAPI, "terminate")
    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._notification_process')
    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._get_vnf')
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    def test_terminate_enhanced_policy(
            self, mock_vnf_by_id, mock_get_vnf, mock_save,
            mock_notification_process, mock_terminate,
            vnf_instance_updates,
            rules, roles, expected_status_code):
        vnf_instance_obj = fakes.return_vnf_instance(
            instantiated_state=fields.VnfInstanceState.INSTANTIATED,
            **vnf_instance_updates)
        mock_vnf_by_id.return_value = vnf_instance_obj
        mock_get_vnf.return_value = \
            self._get_dummy_vnf(vnf_id=vnf_instance_obj.id, status='ACTIVE')

        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/terminate' % uuidsentinel.instance_id)
        body = {'terminationType': 'FORCEFUL'}
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'
        policy.set_rules(oslo_policy.Rules.from_dict(rules), overwrite=True)
        ctx = context.Context(
            'fake', 'fake', roles=roles)
        resp = req.get_response(fakes.wsgi_app_v1(fake_auth_context=ctx))
        self.assertEqual(expected_status_code, resp.status_code)

    @ddt.data(*fakes.get_test_data_policy_vnf_instantiated(
        'heal', http_client.ACCEPTED))
    @ddt.unpack
    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._notification_process')
    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._get_vnf')
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    def test_heal_enhanced_policy(
            self, mock_vnf_by_id, mock_get_vnf, mock_save,
            mock_notification_process,
            vnf_instance_updates,
            rules, roles, expected_status_code):
        vnf_instance_obj = fakes.return_vnf_instance(
            instantiated_state=fields.VnfInstanceState.INSTANTIATED,
            **vnf_instance_updates)
        mock_vnf_by_id.return_value = vnf_instance_obj
        mock_get_vnf.return_value = \
            self._get_dummy_vnf(vnf_id=vnf_instance_obj.id, status='ACTIVE')

        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/heal' % uuidsentinel.instance_id)
        body = {}
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'
        policy.set_rules(oslo_policy.Rules.from_dict(rules), overwrite=True)
        ctx = context.Context(
            'fake', 'fake', roles=roles)
        resp = req.get_response(fakes.wsgi_app_v1(fake_auth_context=ctx))
        self.assertEqual(expected_status_code, resp.status_code)

    @ddt.data(*fakes.get_test_data_policy_delete())
    @ddt.unpack
    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._delete')
    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._notification_process')
    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._get_vnf')
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    def test_delete_enhanced_policy(
            self,
            mock_vnf_by_id,
            mock_get_vnf,
            mock_notification_process,
            mock_private_delete,
            vnf_instance_updates,
            rules, roles, expected_status_code):
        vnf_instance_obj = fakes.return_vnf_instance_delete(
            **vnf_instance_updates)
        mock_vnf_by_id.return_value = vnf_instance_obj
        mock_get_vnf.return_value = \
            self._get_dummy_vnf(vnf_id=vnf_instance_obj.id, status='ACTIVE')

        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s' % uuidsentinel.vnf_instance_id)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'DELETE'
        policy.set_rules(oslo_policy.Rules.from_dict(rules), overwrite=True)
        ctx = context.Context(
            'fake', 'fake', roles=roles)
        resp = req.get_response(fakes.wsgi_app_v1(fake_auth_context=ctx))
        self.assertEqual(expected_status_code, resp.status_code)

    @ddt.data(*fakes.get_test_data_policy_vnf_instantiated(
        'scale', http_client.ACCEPTED))
    @ddt.unpack
    @mock.patch.object(objects.VnfLcmOpOcc, "create")
    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(tacker.db.vnfm.vnfm_db.VNFMPluginDb, "get_vnf")
    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._notification_process')
    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    # @mock.patch.object(vnf_lcm_rpc.VNFLcmRPCAPI, "_scale")
    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._scale')
    def test_scale_enhanced_policy(
            self, mock_scale, mock_vnf_by_id,
            mock_save,
            mock_notification_process,
            mock_get_vnf,
            mock_get_service_plugins,
            mock_opocc_create,
            vnf_instance_updates,
            rules, roles, expected_status_code):
        res = webob.Response()
        res.status_int = 202
        location = ('Location', 'http://mock.mock')
        res.headerlist.append(location)
        mock_scale.return_value = res
        vnf_instance_obj = fakes.return_vnf_instance(
            instantiated_state=fields.VnfInstanceState.INSTANTIATED,
            scale_status="scale_status",
            **vnf_instance_updates)
        mock_vnf_by_id.return_value = vnf_instance_obj
        mock_get_vnf.return_value = fakes._get_vnf()

        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/scale' % uuidsentinel.instance_id)
        body = {"type": "SCALE_OUT",
            "aspectId": "SP1",
            "numberOfSteps": 1,
            "additionalParams": {
                "test": "test_value"}}
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'
        policy.set_rules(oslo_policy.Rules.from_dict(rules), overwrite=True)
        ctx = context.Context(
            'fake', 'fake', roles=roles)
        resp = req.get_response(fakes.wsgi_app_v1(fake_auth_context=ctx))
        self.assertEqual(expected_status_code, resp.status_code)

    @ddt.data(*fakes.get_test_data_policy_vnf_instantiated(
        'update_vnf', http_client.ACCEPTED))
    @ddt.unpack
    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch.object(objects.VNF, "vnf_index_list")
    @mock.patch.object(objects.VnfInstanceList, "vnf_instance_list")
    @mock.patch.object(objects.VnfPackageVnfd, 'get_vnf_package_vnfd')
    @mock.patch.object(vnf_lcm_rpc.VNFLcmRPCAPI, "update")
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    def test_update_vnf_enhanced_policy(
            self,
            mock_vnf_by_id,
            mock_update,
            mock_vnf_package_vnf_get_vnf_package_vnfd,
            mock_vnf_instance_list,
            mock_vnf_index_list,
            mock_get_service_plugins,
            vnf_instance_updates,
            rules, roles, expected_status_code):
        vnf_instance_obj = fakes.return_vnf_instance(
            instantiated_state=fields.VnfInstanceState.INSTANTIATED,
            scale_status="scale_status",
            **vnf_instance_updates)
        mock_vnf_by_id.return_value = vnf_instance_obj
        mock_vnf_index_list.return_value = fakes._get_vnf()
        mock_vnf_instance_list.return_value = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED, **vnf_instance_updates)
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
        policy.set_rules(oslo_policy.Rules.from_dict(rules), overwrite=True)
        ctx = context.Context(
            'fake', 'fake', roles=roles)
        # Call Instantiate API
        resp = req.get_response(fakes.wsgi_app_v1(fake_auth_context=ctx))
        self.assertEqual(expected_status_code, resp.status_code)
        if expected_status_code != http_client.FORBIDDEN:
            mock_update.assert_called_once()

    @ddt.data(*fakes.get_test_data_policy_vnf_instantiated(
        'change_ext_conn', http_client.ACCEPTED))
    @ddt.unpack
    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._notification_process')
    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._get_vnf')
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch.object(vnf_lcm_rpc.VNFLcmRPCAPI, "change_ext_conn")
    def test_change_ext_conn_enhanced_policy(
            self, mock_rpc, mock_save,
            mock_vnf_by_id, mock_get_vnf,
            mock_notification_process,
            mock_get_service_plugins,
            vnf_instance_updates,
            rules, roles, expected_status_code):

        vnf_instance_obj = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED,
            **vnf_instance_updates
        )
        mock_vnf_by_id.return_value = vnf_instance_obj
        mock_get_vnf.return_value = \
            self._get_dummy_vnf(vnf_id=vnf_instance_obj.id, status='ACTIVE')

        body = fakes.get_change_ext_conn_request_body()
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/change_ext_conn' % uuidsentinel.vnf_instance_id)
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'

        policy.set_rules(oslo_policy.Rules.from_dict(rules), overwrite=True)
        ctx = context.Context(
            'fake', 'fake', roles=roles)
        resp = req.get_response(fakes.wsgi_app_v1(fake_auth_context=ctx))

        self.assertEqual(expected_status_code, resp.status_code)
        if expected_status_code != http_client.FORBIDDEN:
            mock_rpc.assert_called_once()

    @ddt.data(*fakes.get_test_data_policy_instantiate())
    @ddt.unpack
    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
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
    def test_instantiate_with_vim_connection_enhanced_policy(
            self, mock_instantiate, mock_vnf_package_get_by_id,
            mock_vnf_package_vnfd_get_by_id, mock_save,
            mock_vnf_instance_get_by_id, mock_get_vim,
            mock_get_vnf, mock_insta_notif_process,
            mock_get_service_plugins, vnf_instance_updates,
            rules, roles, expected_status_code):

        vim = fakes.return_default_vim()
        vim.update({'extra': {"area": "area_A@region_A"}})
        mock_get_vim.return_value = vim
        mock_vnf_instance_get_by_id.return_value =\
            fakes.return_vnf_instance_model(**vnf_instance_updates)
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
        policy.set_rules(oslo_policy.Rules.from_dict(rules), overwrite=True)
        ctx = context.Context(
            'fake', 'fake', roles=roles)
        # Call Instantiate API
        resp = req.get_response(fakes.wsgi_app_v1(fake_auth_context=ctx))
        self.assertEqual(expected_status_code, resp.status_code)
        if expected_status_code != http_client.FORBIDDEN:
            self.assertTrue('Location' in resp.headers.keys())
            expected_location = (self.expected_location_prefix +
                str(mock_insta_notif_process.return_value))
            self.assertEqual(expected_location, resp.headers['location'])
            mock_instantiate.assert_called_once()
            mock_get_vnf.assert_called_once()
            mock_insta_notif_process.assert_called_once()

    @ddt.data(*fakes.get_test_data_policy_index())
    @ddt.unpack
    @mock.patch.object(objects.VnfInstanceList, "get_by_marker_filter")
    def test_index_enhanced_policy(self, mock_vnf_list, vnf_instance_list,
            rules, roles, expected_vnf_inst_ids):

        mock_vnf_list.return_value = vnf_instance_list

        req = fake_request.HTTPRequest.blank('/vnf_instances')
        req.headers['Content-Type'] = 'application/json'
        req.method = 'GET'
        policy.set_rules(oslo_policy.Rules.from_dict(rules), overwrite=True)
        ctx = context.Context(
            'fake', 'fake', roles=roles)
        resp = req.get_response(fakes.wsgi_app_v1(fake_auth_context=ctx))
        self.assertEqual(http_client.OK, resp.status_code)
        self.assertEqual(
            expected_vnf_inst_ids, [inst.get('id') for inst in resp.json])

    @mock.patch.object(objects.VnfInstance, "get_by_id")
    @mock.patch.object(objects.VnfInstanceList, "get_by_marker_filter")
    def test_index_enhanced_policy_paging(self, mock_vnf_list, mock_vnf_by_id):
        cfg.CONF.set_override('vnf_instance_num', 1, group='vnf_lcm')
        inst_a_1 = fakes.make_vnf_instance('openstack', 'provider_A',
            area='area_A@region_A', tenant='tenant_A')
        inst_a_2 = copy.deepcopy(inst_a_1)
        inst_a_2.id = uuidutils.generate_uuid()
        inst_b = fakes.make_vnf_instance('openstack', 'provider_B',
            area='area_B@region_B', tenant='tenant_B')
        rules = {vnf_lcm_policies.VNFLCM % 'index':
                 "area:%(area)s and vendor:%(vendor)s and tenant:%(tenant)s"}
        roles = ['AREA_area_A@region_A', 'VENDOR_provider_A',
                 'TENANT_tenant_A']
        policy.set_rules(oslo_policy.Rules.from_dict(rules), overwrite=True)
        ctx = context.Context('fake', 'fake', roles=roles)

        # first request
        mock_vnf_list.return_value = [inst_a_1, inst_b, inst_a_2]
        req = fake_request.HTTPRequest.blank('/vnf_instances')
        req.headers['Content-Type'] = 'application/json'
        req.method = 'GET'
        resp = req.get_response(fakes.wsgi_app_v1(fake_auth_context=ctx))
        self.assertEqual(http_client.OK, resp.status_code)
        self.assertEqual(
            [inst_a_1.id], [inst.get('id') for inst in resp.json])

        # second request with nextpage_opaque_marker
        mock_vnf_list.return_value = [inst_b, inst_a_2]
        mock_vnf_by_id.return_value = inst_a_1
        req = fake_request.HTTPRequest.blank('/vnf_instances?'
            f'nextpage_opaque_marker={inst_a_1.id}')
        req.headers['Content-Type'] = 'application/json'
        req.method = 'GET'
        resp = req.get_response(fakes.wsgi_app_v1(fake_auth_context=ctx))
        self.assertEqual(http_client.OK, resp.status_code)
        self.assertEqual(
            [inst_a_2.id], [inst.get('id') for inst in resp.json])

    @mock.patch.object(TackerManager, 'get_service_plugins',
                       return_value={'VNFM': FakeVNFMPlugin()})
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
    def test_instantiate_add_area(
            self, mock_instantiate, mock_vnf_package_get_by_id,
            mock_vnf_package_vnfd_get_by_id, mock_save,
            mock_vnf_instance_get_by_id, mock_get_vim,
            mock_get_vnf, mock_insta_notif_process,
            mock_get_service_plugins):
        vim = fakes.return_default_vim()
        vim.update({'extra': {"area": "area_A@region_A"}})
        mock_get_vim.return_value = vim
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
        self.assertTrue('Location' in resp.headers.keys())
        expected_location = (self.expected_location_prefix +
                    str(mock_insta_notif_process.return_value))
        self.assertEqual(expected_location, resp.headers['location'])
        self.assertEqual(http_client.ACCEPTED, resp.status_code)
        mock_instantiate.assert_called_once()
        mock_get_vnf.assert_called_once()
        mock_insta_notif_process.assert_called_once()
