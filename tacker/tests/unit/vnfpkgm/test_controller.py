# Copyright (C) 2019 NTT DATA
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


import copy
import ddt
from http import client as http_client
import json
import os
import re
from unittest import mock
import urllib
from webob import exc

from oslo_config import cfg
from oslo_policy import policy as oslo_policy
from oslo_serialization import jsonutils
from oslo_utils import uuidutils

from tacker._i18n import _
from tacker.api.vnfpkgm.v1 import controller
from tacker.common import csar_utils
from tacker.common import exceptions as tacker_exc
from tacker.conductor.conductorrpc.vnf_pkgm_rpc import VNFPackageRPCAPI
from tacker import context
from tacker.glance_store import store as glance_store
from tacker import objects
from tacker.objects import fields
from tacker.objects import vnf_package
from tacker.objects.vnf_package import VnfPackagesList
from tacker.objects.vnf_software_image import VnfSoftwareImage
from tacker.policies import vnf_package as vnf_package_policies
from tacker import policy
from tacker.tests import constants
from tacker.tests.unit import base
from tacker.tests.unit import fake_request
from tacker.tests.unit.vnfpkgm import fakes
from tacker.tests import utils


@ddt.ddt
class TestController(base.TestCase):

    def setUp(self):
        super(TestController, self).setUp()
        self.controller = controller.VnfPkgmController()

    @property
    def app(self):
        return fakes.wsgi_app_v1()

    def _make_problem_detail(self, title, detail, status):
        res = exc.Response(content_type='application/problem+json')
        problemDetails = {}
        problemDetails['title'] = title
        problemDetails['detail'] = detail
        problemDetails['status'] = status
        res.text = json.dumps(problemDetails)
        res.status_int = status
        return res

    @mock.patch.object(vnf_package, '_vnf_package_create')
    @mock.patch.object(vnf_package.VnfPackage, '_from_db_object')
    def test_create_with_status_201(self, mock_from_db, mock_vnf_pack):
        body = {'userDefinedData': {'abc': 'xyz'}}
        req = fake_request.HTTPRequest.blank('/vnf_packages')
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'
        resp = req.get_response(self.app)
        location_pattern = (r'http://localhost/vnfpkgm/v1/vnf_packages/'
                            r'([a-f]|\d|-){36}')
        self.assertRegex(resp.headers['location'], location_pattern)
        self.assertEqual(http_client.CREATED, resp.status_code)

    @mock.patch.object(vnf_package, '_vnf_package_create')
    @mock.patch.object(vnf_package.VnfPackage, '_from_db_object')
    def test_create_without_userdefine_data(self, mock_from_db,
                                            mock_vnf_pack):
        body = {'userDefinedData': {}}
        req = fake_request.HTTPRequest.blank('/vnf_packages')
        req.body = jsonutils.dump_as_bytes(body)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'
        resp = req.get_response(self.app)
        location_pattern = (r'http://localhost/vnfpkgm/v1/vnf_packages/'
                            r'([a-f]|\d|-){36}')
        self.assertRegex(resp.headers['location'], location_pattern)
        self.assertEqual(http_client.CREATED, resp.status_code)

    @mock.patch.object(VnfSoftwareImage, 'get_by_id')
    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    def test_show(self, mock_vnf_by_id, mock_sw_image_by_id):
        req = fake_request.HTTPRequest.blank(
            '/vnfpkgm/v1/vnf_packages/%s' % constants.UUID)
        mock_vnf_by_id.return_value = fakes.return_vnfpkg_obj(
            vnf_package_updates={
                'tenant_id': req.environ['tacker.context'].project_id})
        mock_sw_image_by_id.return_value = fakes.return_software_image()
        expected_result = fakes.VNFPACKAGE_RESPONSE
        res_dict = self.controller.show(req, constants.UUID)
        self.assertEqual(expected_result, res_dict)

    def test_show_with_invalid_uuid(self):
        req = fake_request.HTTPRequest.blank(
            '/vnfpkgm/v1/vnf_packages/%s' % constants.INVALID_UUID)
        self.assertRaises(exc.HTTPNotFound, self.controller.show,
                          req, constants.INVALID_UUID)

    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    def test_show_no_vnf_package(self, mock_vnf_by_id):
        req = fake_request.HTTPRequest.blank(
            '/vnfpkgm/v1/vnf_packages/%s' % constants.UUID)
        msg = _("Can not find requested vnf package: %s") % constants.UUID
        mock_vnf_by_id.side_effect = exc.HTTPNotFound(explanation=msg)
        self.assertRaises(exc.HTTPNotFound, self.controller.show,
                          req, constants.UUID)

    @mock.patch.object(VnfPackagesList, "get_by_marker_filter")
    @ddt.data('/vnfpkgm/v1/vnf_packages')
    def test_index(self, path, mock_vnf_list):
        req = fake_request.HTTPRequest.blank(path)
        mock_vnf_list.return_value = fakes.return_vnf_package_list()
        res_dict = self.controller.index(req)
        expected_result = fakes.index_response(
            remove_attrs=[
                'softwareImages',
                'checksum',
                'userDefinedData',
                'additionalArtifacts'])
        self.assertEqual(
            jsonutils.loads(jsonutils.dump_as_bytes(expected_result,
                default=str)), res_dict.json)

    @mock.patch.object(VnfPackagesList, "get_by_marker_filter")
    def test_index_attribute_selector_all_fields(self, mock_vnf_list):
        params = {'all_fields': ''}
        query = urllib.parse.urlencode(params)
        req = fake_request.HTTPRequest.blank('/vnfpkgm/v1/vnf_packages?' +
            query)
        mock_vnf_list.return_value = fakes.return_vnf_package_list()
        res_dict = self.controller.index(req)
        expected_result = fakes.index_response()
        self.assertEqual(
            jsonutils.loads(jsonutils.dump_as_bytes(expected_result,
                default=str)), res_dict.json)

    @mock.patch.object(VnfPackagesList, "get_by_marker_filter")
    def test_index_attribute_selector_exclude_default(self, mock_vnf_list):
        params = {'exclude_default': ''}
        query = urllib.parse.urlencode(params)
        req = fake_request.HTTPRequest.blank('/vnfpkgm/v1/vnf_packages?' +
            query)
        mock_vnf_list.return_value = fakes.return_vnf_package_list()
        res_dict = self.controller.index(req)
        expected_result = fakes.index_response(
            remove_attrs=[
                'softwareImages',
                'checksum',
                'userDefinedData',
                'additionalArtifacts'])
        self.assertEqual(
            jsonutils.loads(jsonutils.dump_as_bytes(expected_result,
                default=str)), res_dict.json)

    @mock.patch.object(VnfPackagesList, "get_by_marker_filter")
    @ddt.data(
        {'exclude_fields': 'softwareImages'},
        {'exclude_fields': 'checksum'},
        {'exclude_fields': 'userDefinedData'},
        {'exclude_fields': 'additionalArtifacts'}
    )
    def test_index_attribute_selector_exclude_fields(self, params,
            mock_vnf_list):
        query = urllib.parse.urlencode(params)
        req = fake_request.HTTPRequest.blank('/vnfpkgm/v1/vnf_packages?' +
            query)
        mock_vnf_list.return_value = fakes.return_vnf_package_list()
        res_dict = self.controller.index(req)
        remove_attrs = [params['exclude_fields']]
        expected_result = fakes.index_response(remove_attrs=remove_attrs)
        self.assertEqual(
            jsonutils.loads(jsonutils.dump_as_bytes(expected_result,
                default=str)), res_dict.json)

    @mock.patch.object(VnfPackagesList, "get_by_marker_filter")
    @ddt.data(
        {'fields': 'softwareImages'},
        {'fields': 'checksum'},
        {'fields': 'userDefinedData'},
        {'fields': 'additionalArtifacts'}
    )
    def test_index_attribute_selector_fields(self, params, mock_vnf_list):
        """Test valid attribute names with fields parameter

        We can specify complex attributes in fields. Hence the data only
        contains such attributes.
        """
        complex_attrs = [
            'softwareImages',
            'checksum',
            'userDefinedData',
            'additionalArtifacts']
        query = urllib.parse.urlencode(params)
        req = fake_request.HTTPRequest.blank('/vnfpkgm/v1/vnf_packages?' +
                query)
        mock_vnf_list.return_value = fakes.return_vnf_package_list()
        res_dict = self.controller.index(req)
        remove_attrs = [x for x in complex_attrs if x != params['fields']]
        expected_result = fakes.index_response(remove_attrs=remove_attrs)
        self.assertEqual(
            jsonutils.loads(jsonutils.dump_as_bytes(expected_result,
                default=str)), res_dict.json)

    @mock.patch.object(VnfPackagesList, "get_by_marker_filter")
    def test_index_attribute_selector_user_defined_data_combination(self,
            mock_vnf_list):
        """Query user defined data with fields parameter

        This test queries combination of user defined data. i.e. fields of
        different complex attributes.
        """
        params = {
            'fields': 'userDefinedData/key1,softwareImages/userMetadata/key3',
        }
        query = urllib.parse.urlencode(params)
        req = fake_request.HTTPRequest.blank('/vnfpkgm/v1/vnf_packages?' +
            query)
        mock_vnf_list.return_value = fakes.return_vnf_package_list()
        res_dict = self.controller.index(req)
        vnf_package_updates = {
            'userDefinedData': {'key1': 'value1'},
            'softwareImages': [{'userMetadata': {'key3': 'value3'}}]
        }
        expected_result = fakes.index_response(
            remove_attrs=[
                'checksum',
                'additionalArtifacts'],
            vnf_package_updates=vnf_package_updates)
        self.assertEqual(
            jsonutils.loads(jsonutils.dump_as_bytes(expected_result,
                default=str)), res_dict.json)

    @mock.patch.object(VnfPackagesList, "get_by_marker_filter")
    def test_index_attribute_selector_user_defined_data(self, mock_vnf_list):
        params = {'fields': 'userDefinedData/key1,userDefinedData/key2'}
        query = urllib.parse.urlencode(params)
        req = fake_request.HTTPRequest.blank('/vnfpkgm/v1/vnf_packages?' +
            query)
        mock_vnf_list.return_value = fakes.return_vnf_package_list()
        res_dict = self.controller.index(req)
        expected_result = fakes.index_response(remove_attrs=[
            'checksum', 'softwareImages', 'additionalArtifacts'])
        self.assertEqual(
            jsonutils.loads(jsonutils.dump_as_bytes(expected_result,
                default=str)), res_dict.json)

    @mock.patch.object(VnfPackagesList, "get_by_marker_filter")
    def test_index_attribute_selector_nested_complex_attribute(self,
            mock_vnf_list):
        params = {'fields': 'softwareImages/checksum/algorithm,'
            'softwareImages/minRam,additionalArtifacts/metadata,'
            'additionalArtifacts/checksum/algorithm'}
        query = urllib.parse.urlencode(params)
        req = fake_request.HTTPRequest.blank('/vnfpkgm/v1/vnf_packages?' +
            query)
        mock_vnf_list.return_value = fakes.return_vnf_package_list()
        res_dict = self.controller.index(req)
        vnf_package_updates = {
            'softwareImages': [{
                'minRam': 0,
                'checksum': {'algorithm': 'fake-algorithm'}
            }],
            'additionalArtifacts': [{
                'metadata': {},
                'checksum': {'algorithm': 'SHA-256'}
            }]
        }
        expected_result = fakes.index_response(remove_attrs=[
            'checksum', 'userDefinedData'],
            vnf_package_updates=vnf_package_updates)
        self.assertEqual(
            jsonutils.loads(jsonutils.dump_as_bytes(expected_result,
                default=str)), res_dict.json)

    @mock.patch.object(VnfPackagesList, "get_by_marker_filter")
    @ddt.data(
        {'filter': '(eq,vnfdId,%s)' % constants.UUID},
        {'filter': '(in,vnfdId,%s)' % constants.UUID},
        {'filter': '(cont,vnfdId,%s)' % constants.UUID},
        {'filter': '(neq,vnfdId,%s)' % constants.UUID},
        {'filter': '(nin,vnfdId,%s)' % constants.UUID},
        {'filter': '(ncont,vnfdId,%s)' % constants.UUID},
        {'filter': '(gt,softwareImages/createdAt,2020-03-11 04:10:15+00:00)'},
        {'filter': '(gte,softwareImages/createdAt,2020-03-14 04:10:15+00:00)'},
        {'filter': '(lt,softwareImages/createdAt,2020-03-20 04:10:15+00:00)'},
        {'filter': '(lte,softwareImages/createdAt,2020-03-11 04:10:15+00:00)'},
        {'filter': '(eq,additionalArtifacts/checksum/algorithm,'
                   'SHA-256)'},
        {'filter': '(neq,additionalArtifacts/checksum/algorithm,'
                   'SHA-256)'},
        {'filter': '(in,additionalArtifacts/checksum/algorithm,'
                   'SHA-256)'},
        {'filter': '(nin,additionalArtifacts/checksum/algorithm,'
                   'SHA-256)'},
        {'filter': '(cont,additionalArtifacts/checksum/algorithm,'
                   'SHA-256)'},
        {'filter': '(ncont,additionalArtifacts/checksum/algorithm,'
                   'SHA-256)'})
    def test_index_filter_operator(self, filter_params, mock_vnf_list):
        """Tests all supported operators in filter expression """
        query = urllib.parse.urlencode(filter_params)
        req = fake_request.HTTPRequest.blank('/vnfpkgm/v1/vnf_packages?' +
            query)
        mock_vnf_list.return_value = fakes.return_vnf_package_list()
        res_dict = self.controller.index(req)
        expected_result = fakes.index_response(
            remove_attrs=[
                'softwareImages',
                'checksum',
                'userDefinedData',
                'additionalArtifacts'])
        self.assertEqual(
            jsonutils.loads(jsonutils.dump_as_bytes(expected_result,
                default=str)), res_dict.json)

    @mock.patch.object(VnfPackagesList, "get_by_marker_filter")
    def test_index_filter_combination(self, mock_vnf_list):
        """Test multiple filter parameters separated by semicolon """
        params = {'filter': '(eq,vnfdId,%s);(eq,id,%s)' %
                  (constants.UUID, constants.UUID)}
        query = urllib.parse.urlencode(params)
        req = fake_request.HTTPRequest.blank('/vnfpkgm/v1/vnf_packages?' +
            query)
        mock_vnf_list.return_value = fakes.return_vnf_package_list()
        res_dict = self.controller.index(req)
        expected_result = fakes.index_response(
            remove_attrs=[
                'softwareImages',
                'checksum',
                'userDefinedData',
                'additionalArtifacts'])
        self.assertEqual(
            jsonutils.loads(jsonutils.dump_as_bytes(expected_result,
                default=str)), res_dict.json)

    @mock.patch.object(VnfPackagesList, "get_by_marker_filter")
    @ddt.data(
        {'filter': '(eq,id,%s)' % constants.UUID},
        {'filter': '(eq,vnfdId,%s)' % constants.UUID},
        {'filter': '(eq,onboardingState,ONBOARDED)'},
        {'filter': '(eq,operationalState,ENABLED)'},
        {'filter': '(eq,usageState,NOT_IN_USE)'},
        {'filter': '(eq,vnfProvider,dummy_value)'},
        {'filter': '(eq,vnfProductName,dummy_value)'},
        {'filter': '(eq,vnfSoftwareVersion,dummy_value)'},
        {'filter': '(eq,vnfdVersion,dummy_value)'},
        {'filter': '(eq,userDefinedData/key1,dummy_value)'},
        {'filter': '(eq,checksum/algorithm,dummy_value)'},
        {'filter': '(eq,checksum/hash,dummy_value)'},
        {'filter': '(eq,softwareImages/id,%s)' % constants.UUID},
        {'filter': '(eq,softwareImages/imagePath,dummy_value)'},
        {'filter': '(eq,softwareImages/diskFormat,dummy_value)'},
        {'filter': '(eq,softwareImages/userMetadata/key3,dummy_value)'},
        {'filter': '(eq,softwareImages/size,0)'},
        {'filter': '(gt,softwareImages/createdAt,2020-03-14 04:10:15+00:00)'},
        {'filter': '(eq,softwareImages/name,dummy_value)'},
        {'filter': '(eq,softwareImages/minDisk,0)'},
        {'filter': '(eq,softwareImages/version,dummy_value)'},
        {'filter': '(eq,softwareImages/provider,dummy_value)'},
        {'filter': '(eq,softwareImages/minRam,0)'},
        {'filter': '(eq,softwareImages/containerFormat,dummy_value)'},
        {'filter': '(eq,softwareImages/checksum/hash,dummy_value)'},
        {'filter': '(eq,softwareImages/checksum/algorithm,dummy_value)'},
        {'filter': '(eq,additionalArtifacts/artifactPath,dummy_value)'},
        {'filter': '(eq,additionalArtifacts/checksum/algorithm,dummy_value)'},
        {'filter': '(eq,additionalArtifacts/checksum/hash,dummy_value)'}
    )
    def test_index_filter_attributes(self, filter_params, mock_vnf_list):
        """Test various attributes supported for filter parameter """
        query = urllib.parse.urlencode(filter_params)
        req = fake_request.HTTPRequest.blank('/vnfpkgm/v1/vnf_packages?' +
            query)
        mock_vnf_list.return_value = fakes.return_vnf_package_list()
        res_dict = self.controller.index(req)
        expected_result = fakes.index_response(
            remove_attrs=[
                'softwareImages',
                'checksum',
                'userDefinedData',
                'additionalArtifacts'])
        self.assertEqual(
            jsonutils.loads(jsonutils.dump_as_bytes(expected_result,
                default=str)), res_dict.json)

    @mock.patch.object(VnfPackagesList, "get_by_marker_filter")
    @ddt.data(
        {'filter': "(eq,vnfProductName,dummy_value)"},
        {'filter': "(eq,vnfProductName,dummy value)"},
        {'filter': "(eq,vnfProductName,'dummy value')"},
        {'filter': "(eq,vnfProductName,'dummy (hi) value')"},
        {'filter': "(eq,vnfProductName,'dummy ''hi'' value')"},
        {'filter': "(eq,vnfProductName,'''dummy ''hi'' value''')"},
    )
    def test_index_filter_valid_string_values(self, filter_params,
            mock_vnf_list):
        """Tests all the supported string values.

        For example:
        - values which are not enclosed in single quotes
        - values which are enclosed in single quotes
        - values having single quotes within them
        - values having round brackets in them
        """
        query = urllib.parse.urlencode(filter_params)
        req = fake_request.HTTPRequest.blank('/vnfpkgm/v1/vnf_packages?' +
            query)
        mock_vnf_list.return_value = fakes.return_vnf_package_list()
        res_dict = self.controller.index(req)
        expected_result = fakes.index_response(
            remove_attrs=[
                'softwareImages',
                'checksum',
                'userDefinedData',
                'additionalArtifacts'])
        self.assertEqual(
            jsonutils.loads(jsonutils.dump_as_bytes(expected_result,
                default=str)), res_dict.json)

    @mock.patch.object(VnfPackagesList, "get_by_marker_filter")
    @ddt.data(
        {'filter': "(eq,vnfProductName,value"},
        {'filter': "eq,vnfProductName,value)"},
        {'filter': "(eq,vnfProductName,value);"},
        {'filter': "(eq , vnfProductName ,value)"},
    )
    def test_index_filter_invalid_expression(self, filter_params,
            mock_vnf_list):
        """Test invalid filter expression """
        query = urllib.parse.urlencode(filter_params)
        req = fake_request.HTTPRequest.blank('/vnfpkgm/v1/vnf_packages?' +
            query)
        mock_vnf_list.return_value = fakes.return_vnf_package_list()
        mock_vnf_list.return_value = fakes.return_vnf_package_list()
        self.assertRaises(tacker_exc.ValidationError, self.controller.index,
                          req)

    @mock.patch.object(VnfPackagesList, "get_by_marker_filter")
    @ddt.data(
        {'filter': "(eq,vnfProductName,singl'quote)"},
        {'filter': "(eq,vnfProductName,three''' quotes)"},
        {'filter': "(eq,vnfProductName,round ) bracket)"},
        {'filter': "(eq,vnfProductName,'dummy 'hi' value')"},
        {'filter': "(eq,vnfProductName,'dummy's value')"},
        {'filter': "(eq,vnfProductName,'three ''' quotes')"},
    )
    def test_index_filter_invalid_string_values(self, filter_params,
            mock_vnf_list):
        """Test invalid string values as per ETSI NFV SOL013 5.2.2 """
        query = urllib.parse.urlencode(filter_params)
        req = fake_request.HTTPRequest.blank('/vnfpkgm/v1/vnf_packages?' +
            query)
        mock_vnf_list.return_value = fakes.return_vnf_package_list()
        mock_vnf_list.return_value = fakes.return_vnf_package_list()
        self.assertRaises(tacker_exc.ValidationError, self.controller.index,
                          req)

    @mock.patch.object(VnfPackagesList, "get_by_marker_filter")
    @ddt.data(
        {'filter': '(eq,vnfdId,value1,value2)'},
        {'filter': '(fake,vnfdId,dummy_vnfd_id)'},
        {'filter': '(,vnfdId,dummy_vnfd_id)'},
    )
    def test_index_filter_invalid_operator(self, params, mock_vnf_list):
        """Test invalid operator in filter expression """
        query = urllib.parse.urlencode(params)
        req = fake_request.HTTPRequest.blank('/vnfpkgm/v1/vnf_packages?' +
            query)
        mock_vnf_list.return_value = fakes.return_vnf_package_list()
        self.assertRaises(tacker_exc.ValidationError, self.controller.index,
                          req)

    @mock.patch.object(VnfPackagesList, "get_by_marker_filter")
    @ddt.data(
        {'filter': '(eq,fakeattr,fakevalue)'},
        {'filter': '(eq,,fakevalue)'},
    )
    def test_index_filter_invalid_attribute(self, params, mock_vnf_list):
        """Test invalid attribute in filter expression """
        query = urllib.parse.urlencode(params)
        req = fake_request.HTTPRequest.blank('/vnfpkgm/v1/vnf_packages?' +
            query)
        mock_vnf_list.return_value = fakes.return_vnf_package_list()
        self.assertRaises(tacker_exc.ValidationError, self.controller.index,
                          req)

    @mock.patch.object(VnfPackagesList, "get_by_marker_filter")
    @ddt.data(
        {'filter': '(eq,id,fake_value)'},
        {'filter': '(eq,vnfd_id,fake_value)'},
        {'filter': '(eq,operationalState,fake_value)'},
        {'filter': '(eq,softwareImages/size,fake_value)'},
        {'filter': '(gt,softwareImages/createdAt,fake_value)'},
        {'filter': '(eq,softwareImages/minDisk,fake_value)'},
        {'filter': '(eq,softwareImages/minRam,fake_value)'},
    )
    def test_index_filter_invalid_value_type(self, filter_params,
            mock_vnf_list):
        """Test values which doesn't match with attribute data type """
        query = urllib.parse.urlencode(filter_params)
        req = fake_request.HTTPRequest.blank('/vnfpkgm/v1/vnf_packages?' +
            query)
        mock_vnf_list.return_value = fakes.return_vnf_package_list()
        self.assertRaises(tacker_exc.ValidationError, self.controller.index,
                          req)

    @mock.patch.object(VnfPackagesList, "get_by_marker_filter")
    @ddt.data(
        {'fields': 'nonExistentField'},
        {'exclude_fields': 'nonExistentField'}
    )
    def test_index_attribute_selector_invalid_fields(self, params,
            mock_vnf_list):
        query = urllib.parse.urlencode(params)
        req = fake_request.HTTPRequest.blank('/vnfpkgm/v1/vnf_packages?' +
            query)
        mock_vnf_list.return_value = fakes.return_vnf_package_list()
        self.assertRaises(tacker_exc.ValidationError, self.controller.index,
                          req)

    @mock.patch.object(VnfPackagesList, "get_by_marker_filter")
    @ddt.data(
        {'fields': 'softwareImages', 'all_fields': ''},
        {'exclude_fields': 'checksum', 'all_fields': ''},
        {'fields': 'softwareImages', 'exclude_fields': 'checksum'}
    )
    def test_index_attribute_selector_invalid_combination(self, params,
            mock_vnf_list):
        """Test invalid combination of attribute selector parameters """
        query = urllib.parse.urlencode(params)
        req = fake_request.HTTPRequest.blank('/vnfpkgm/v1/vnf_packages?' +
            query)
        mock_vnf_list.return_value = fakes.return_vnf_package_list()
        self.assertRaises(tacker_exc.ValidationError, self.controller.index,
                          req)

    @mock.patch.object(VnfPackagesList, "get_by_marker_filter")
    @ddt.data(
        {'exclude_default': 'softwareImages'},
        {'all_fields': 'checksum'},
    )
    def test_index_attribute_selector_unexpected_value(self, params,
            mock_vnf_list):
        """Test values with the parameters which doesn't need values. """
        query = urllib.parse.urlencode(params)
        req = fake_request.HTTPRequest.blank('/vnfpkgm/v1/vnf_packages?' +
            query)
        mock_vnf_list.return_value = fakes.return_vnf_package_list()
        self.assertRaises(tacker_exc.ValidationError, self.controller.index,
                          req)

    @mock.patch.object(VnfPackagesList, "get_by_marker_filter")
    @mock.patch.object(objects.VnfPackage, "get_by_id")
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
            mock_marker_obj, mock_vnf_package_list):
        ids = ['11111111-1111-1111-1111-111111111111',
               '22222222-2222-2222-2222-222222222222',
               '33333333-3333-3333-3333-333333333333',
               '44444444-4444-4444-4444-444444444444',
               None]
        cfg.CONF.set_override('vnf_package_num', 2, group='vnf_package')
        query = urllib.parse.urlencode(values['params'])
        req = fake_request.HTTPRequest.blank('/vnfpkgm/v1/vnf_packages?' +
            query)

        target_index = []
        if 'all_records' in values['params'] \
                and values['params']['all_records'] == 'yes':
            mock_marker_obj.return_value = None
            target_index = [0, 1, 2, 3]
        elif 'nextpage_opaque_marker' in values['params']:
            mock_marker_obj.return_value = fakes.return_vnfpkg_obj(
                vnf_package_updates={'id':
                    values['params']['nextpage_opaque_marker']})
            marker_obj_index = ids.index(mock_marker_obj.return_value['id'])
            for i in range(marker_obj_index + 1, len(ids) - 1):
                target_index.append(i)
        else:
            mock_marker_obj.return_value = None
            target_index = [0, 1]

        mock_vnf_package_list.return_value = []
        for index in range(len(target_index)):
            mock_vnf_package_list.return_value.append(
                fakes.return_vnfpkg_obj(
                    vnf_package_updates={'id':
                        ids[target_index[index]]},
                    vnfd_updates={'vnf_product_name':
                        values['result_names'][index]}))

        expected_result = []
        for index in range(len(target_index)):
            _links = fakes.index_response()[0]['_links']
            expected_links = (re.sub("vnf_packages/[a-zA-Z0-9-]*",
                    "vnf_packages/{}".format(ids[target_index[index]]),
                    str(_links)))
            expected_links = json.loads(expected_links.replace("'", '"'))
            print("expected_links", expected_links)

            expected_result.append(fakes.index_response(
                remove_attrs=[
                    'softwareImages',
                    'checksum',
                    'userDefinedData',
                    'additionalArtifacts'],
                vnf_package_updates={'vnfProductName':
                    values['result_names'][index],
                    'id': ids[target_index[index]],
                    '_links': expected_links})[0])

        res_dict = self.controller.index(req)

        expected_result_link = None
        if 'all_records' not in values['params'] and len(target_index) >= 2:
            expected_result_link = (
                '<http://localhost//vnfpkgm/v1/vnf_packages' +
                '?nextpage_opaque_marker=%s>; rel="next"'
                % ids[target_index[1]])

        self.assertEqual(expected_result, res_dict.json)
        if expected_result_link is not None:
            self.assertEqual(expected_result_link, res_dict.headers['Link'])

    @mock.patch.object(vnf_package.VnfPackage, "destroy")
    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    @mock.patch.object(VNFPackageRPCAPI, "delete_vnf_package")
    def test_delete_with_204_status(self, mock_delete_rpc,
                                    mock_vnf_by_id, mock_vnf_pack_destroy):
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s' % constants.UUID)
        vnfpkg_updates = {
            'operational_state': 'DISABLED',
            'tenant_id': req.environ['tacker.context'].project_id}
        mock_vnf_by_id.return_value = fakes.return_vnfpkg_obj(
            vnf_package_updates=vnfpkg_updates)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'DELETE'
        resp = req.get_response(self.app)
        self.assertEqual(http_client.NO_CONTENT, resp.status_code)

    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    def test_delete_no_vnf_package(self, mock_vnf_by_id):
        req = fake_request.HTTPRequest.blank(
            '/vnfpkgm/v1/vnf_packages/%s' % constants.UUID)
        msg = _("Can not find requested vnf package: %s") % constants.UUID
        mock_vnf_by_id.side_effect = exc.HTTPNotFound(explanation=msg)
        self.assertRaises(exc.HTTPNotFound, self.controller.delete,
                          req, constants.UUID)

    def test_delete_with_invalid_uuid(self):
        req = fake_request.HTTPRequest.blank(
            '/vnfpkgm/v1/vnf_packages/%s' % constants.INVALID_UUID)
        self.assertRaises(exc.HTTPNotFound, self.controller.delete,
                          req, constants.INVALID_UUID)

    @mock.patch.object(objects.VnfPackage, "get_by_id")
    def test_delete_with_operational_state_enabled(self, mock_vnf_by_id):
        req = fake_request.HTTPRequest.blank(
            '/vnfpkgm/v1/vnf_packages/%s' % constants.UUID)
        vnfpkg_updates = {
            'operational_state': fields.PackageOperationalStateType.ENABLED,
            'tenant_id': req.environ['tacker.context'].project_id}
        mock_vnf_by_id.return_value = fakes.return_vnfpkg_obj(
            vnf_package_updates=vnfpkg_updates)

        self.assertRaises(exc.HTTPConflict, self.controller.delete,
                          req, constants.UUID)

    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    def test_delete_with_usage_state_in_use(self, mock_vnf_by_id):
        req = fake_request.HTTPRequest.blank(
            '/vnfpkgm/v1/vnf_packages/%s' % constants.UUID)
        vnfpkg_updates = {
            'usage_state': fields.PackageUsageStateType.IN_USE,
            'tenant_id': req.environ['tacker.context'].project_id}
        mock_vnf_by_id.return_value = fakes.return_vnfpkg_obj(
            vnf_package_updates=vnfpkg_updates)

        self.assertRaises(exc.HTTPConflict, self.controller.delete,
                          req, constants.UUID)

    @mock.patch.object(glance_store, 'store_csar')
    @mock.patch.object(VNFPackageRPCAPI, "upload_vnf_package_content")
    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    @mock.patch.object(vnf_package.VnfPackage, "save")
    def test_upload_vnf_package_content(self, mock_vnf_pack_save,
                                        mock_vnf_by_id,
                                        mock_upload_vnf_package_content,
                                        mock_glance_store):
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s/package_content'
            % constants.UUID)

        updates = {'onboarding_state': 'CREATED',
                   'operational_state': 'DISABLED',
                   'tenant_id': req.environ['tacker.context'].project_id}
        vnf_package_dict = fakes.fake_vnf_package(updates)
        vnf_package_obj = objects.VnfPackage(**vnf_package_dict)
        mock_vnf_by_id.return_value = vnf_package_obj
        mock_vnf_pack_save.return_value = vnf_package_obj
        mock_glance_store.return_value = (
            'location', 0, 'checksum', 'multihash', 'loc_meta')
        req.headers['Content-Type'] = 'application/zip'
        req.method = 'PUT'
        req.body = jsonutils.dump_as_bytes({'dummy': {'val': 'foo'}})
        resp = req.get_response(self.app)
        mock_glance_store.assert_called()
        self.assertEqual(http_client.ACCEPTED, resp.status_code)

    def test_upload_vnf_package_content_with_invalid_uuid(self):
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s/package_content'
            % constants.INVALID_UUID)
        req.headers['Content-Type'] = 'application/zip'
        req.method = 'PUT'
        req.body = jsonutils.dump_as_bytes({'dummy': {'val': 'foo'}})

        msg = _("Can not find requested vnf package: %s") \
            % constants.INVALID_UUID
        res = self._make_problem_detail('Not Found', msg, 404)
        resp = req.get_response(self.app)
        self.assertEqual(res.text, resp.text)

    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    def test_upload_vnf_package_content_without_vnf_pack(self,
                                                         mock_vnf_by_id):
        msg = _("Can not find requested vnf package: %s") % constants.UUID
        mock_vnf_by_id.side_effect = \
            tacker_exc.VnfPackageNotFound(explanation=msg)
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s/package_content' % constants.UUID)
        req.headers['Content-Type'] = 'application/zip'
        req.method = 'PUT'
        req.body = jsonutils.dump_as_bytes({'dummy': {'val': 'foo'}})

        msg = _("Can not find requested vnf package: %s") % constants.UUID
        res = self._make_problem_detail('Not Found', msg, 404)
        resp = req.get_response(self.app)
        self.assertEqual(res.text, resp.text)

    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    def test_upload_vnf_package_content_with_invalid_status(self,
                                                            mock_vnf_by_id):
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s/package_content' % constants.UUID)

        vnf_obj = fakes.return_vnfpkg_obj(
            vnf_package_updates={
                'tenant_id': req.environ['tacker.context'].project_id})
        vnf_obj.__setattr__('onboarding_state', 'ONBOARDED')
        mock_vnf_by_id.return_value = vnf_obj
        req.headers['Content-Type'] = 'application/zip'
        req.method = 'PUT'
        req.body = jsonutils.dump_as_bytes({'dummy': {'val': 'foo'}})

        msg = _("VNF Package %s onboarding state is not CREATED") \
            % constants.UUID
        res = self._make_problem_detail('Conflict', msg, 409)
        resp = req.get_response(self.app)
        self.assertEqual(res.text, resp.text)

    @mock.patch.object(urllib.request, 'urlopen')
    @mock.patch.object(VNFPackageRPCAPI, "upload_vnf_package_from_uri")
    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    @mock.patch.object(vnf_package.VnfPackage, "save")
    def test_upload_vnf_package_from_uri(self, mock_vnf_pack_save,
                                         mock_vnf_by_id,
                                         mock_upload_vnf_package_from_uri,
                                         mock_url_open):
        body = {"addressInformation": "http://localhost/test_data.zip"}
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s/package_content/upload_from_uri'
            % constants.UUID)

        updates = {'onboarding_state': 'CREATED',
                   'operational_state': 'DISABLED',
                   'tenant_id': req.environ['tacker.context'].project_id}
        vnf_package_dict = fakes.fake_vnf_package(updates)
        vnf_package_obj = objects.VnfPackage(**vnf_package_dict)
        mock_vnf_by_id.return_value = vnf_package_obj
        mock_vnf_pack_save.return_value = vnf_package_obj
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'
        req.body = jsonutils.dump_as_bytes(body)
        resp = req.get_response(self.app)
        self.assertEqual(http_client.ACCEPTED, resp.status_code)

    def test_upload_vnf_package_from_uri_with_invalid_uuid(self):
        body = {"addressInformation": "http://localhost/test_data.zip"}
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s/package_content/upload_from_uri'
            % constants.INVALID_UUID)
        self.assertRaises(exc.HTTPNotFound,
                          self.controller.upload_vnf_package_from_uri,
                          req, constants.INVALID_UUID, body=body)

    @mock.patch.object(urllib.request, 'urlopen')
    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    def test_upload_vnf_package_from_uri_without_vnf_pack(self,
                                                          mock_vnf_by_id,
                                                          mock_url_open):
        body = {"addressInformation": "http://localhost/test_data.zip"}
        msg = _("Can not find requested vnf package: %s") % constants.UUID
        mock_vnf_by_id.side_effect = exc.HTTPNotFound(explanation=msg)
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s/package_content/upload_from_uri'
            % constants.UUID)
        self.assertRaises(exc.HTTPNotFound,
                          self.controller.upload_vnf_package_from_uri,
                          req, constants.UUID, body=body)

    @mock.patch.object(urllib.request, 'urlopen')
    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    def test_upload_vnf_package_from_uri_with_invalid_status(self,
                                                             mock_vnf_by_id,
                                                             mock_url_open):
        body = {"addressInformation": "http://localhost/test_data.zip"}
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s/package_content/upload_from_uri'
            % constants.UUID)
        vnf_obj = fakes.return_vnfpkg_obj(
            vnf_package_updates={
                'tenant_id': req.environ['tacker.context'].project_id})
        vnf_obj.__setattr__('onboarding_state', 'ONBOARDED')
        mock_vnf_by_id.return_value = vnf_obj
        self.assertRaises(exc.HTTPConflict,
                          self.controller.upload_vnf_package_from_uri,
                          req, constants.UUID, body=body)

    @ddt.data("http://test_data.zip", "xyz://github.com/abc/xyz.git",
              "xyz://github.com/abc/xyz")
    def test_upload_vnf_package_from_uri_with_invalid_url(self, invalid_url):
        body = {"addressInformation": invalid_url}
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s/package_content/upload_from_uri'
            % constants.UUID)
        self.assertRaises(exc.HTTPBadRequest,
                          self.controller.upload_vnf_package_from_uri,
                          req, constants.UUID, body=body)

    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    @mock.patch.object(vnf_package.VnfPackage, "save")
    def test_patch(self, mock_save, mock_vnf_by_id):
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s'
            % constants.UUID)
        vnf_package_updates = {
            'operational_state': 'DISABLED',
            'tenant_id': req.environ['tacker.context'].project_id}
        mock_vnf_by_id.return_value = \
            fakes.return_vnfpkg_obj(vnf_package_updates=vnf_package_updates)

        req_body = {"operationalState": "ENABLED",
                "userDefinedData": {"testKey1": "val01",
                                    "testKey2": "val02", "testkey3": "val03"}}

        req.headers['Content-Type'] = 'application/json'
        req.method = 'PATCH'
        req.body = jsonutils.dump_as_bytes(req_body)
        resp = req.get_response(self.app)

        self.assertEqual(http_client.OK, resp.status_code)
        self.assertEqual(req_body, jsonutils.loads(resp.body))

    def test_patch_with_empty_body(self):
        body = {}
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s'
            % constants.UUID)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'PATCH'
        req.body = jsonutils.dump_as_bytes(body)
        resp = req.get_response(self.app)
        self.assertEqual(http_client.BAD_REQUEST, resp.status_code)

    def test_patch_with_invalid_operational_state(self):
        body = {"operationalState": "DISABLE"}
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s'
            % constants.UUID)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'PATCH'
        req.body = jsonutils.dump_as_bytes(body)
        resp = req.get_response(self.app)
        self.assertEqual(http_client.BAD_REQUEST, resp.status_code)

    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    @mock.patch.object(vnf_package.VnfPackage, "save")
    def test_patch_update_existing_user_data(self, mock_save, mock_vnf_by_id):
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s'
            % constants.UUID)

        fake_obj = fakes.return_vnfpkg_obj(vnf_package_updates={
            "operational_state": "DISABLED", "onboarding_state": "CREATED",
            "user_data": {"testKey1": "val01", "testKey2": "val02",
            "testKey3": "val03"},
            "tenant_id": req.environ['tacker.context'].project_id})
        mock_vnf_by_id.return_value = fake_obj
        req_body = {"userDefinedData": {"testKey1": "changed_val01",
                                        "testKey2": "changed_val02",
                                        "testKey3": "changed_val03"}}
        req.headers['Content-Type'] = 'application/json'
        req.method = 'PATCH'
        req.body = jsonutils.dump_as_bytes(req_body)
        resp = req.get_response(self.app)
        self.assertEqual(http_client.OK, resp.status_code)
        self.assertEqual(req_body, jsonutils.loads(resp.body))

    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    @mock.patch.object(vnf_package.VnfPackage, "save")
    def test_patch_failed_with_same_user_data(self, mock_save,
                                              mock_vnf_by_id):
        req = fake_request.HTTPRequest.blank('/vnf_packages/%s'
                                             % constants.UUID)

        vnf_package_updates = {"operational_state": "DISABLED",
            "onboarding_state": "CREATED",
            "user_data": {"testKey1": "val01",
                          "testKey2": "val02",
                          "testkey3": "val03"},
            'tenant_id': req.environ['tacker.context'].project_id}
        req_body = {"userDefinedData": {"testKey1": "val01",
                                        "testKey2": "val02",
                                        "testkey3": "val03"}}
        fake_obj = fakes.return_vnfpkg_obj(
            vnf_package_updates=vnf_package_updates)
        mock_vnf_by_id.return_value = fake_obj

        self.assertRaises(exc.HTTPConflict,
                          self.controller.patch,
                          req, constants.UUID, body=req_body)

    def test_patch_with_invalid_uuid(self):
        body = {"operationalState": "ENABLED"}
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s'
            % constants.INVALID_UUID)
        exception = self.assertRaises(exc.HTTPNotFound,
                                      self.controller.patch,
                                      req, constants.INVALID_UUID, body=body)
        self.assertEqual(
            "Can not find requested vnf package: %s" % constants.INVALID_UUID,
            exception.explanation)

    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    def test_patch_with_non_existing_vnf_package(self, mock_vnf_by_id):
        body = {"operationalState": "ENABLED"}
        msg = _("Can not find requested vnf package: %s") % constants.UUID
        mock_vnf_by_id.side_effect = exc.HTTPNotFound(explanation=msg)
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s' % constants.UUID)
        exception = self.assertRaises(
            exc.HTTPNotFound, self.controller.patch,
            req, constants.UUID, body=body)
        self.assertEqual(
            "Can not find requested vnf package: %s" % constants.UUID,
            exception.explanation)

    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    def test_patch_failed_with_same_operational_state(self, mock_vnf_by_id):
        req = fake_request.HTTPRequest.blank('/vnf_packages/%s'
                                             % constants.UUID)
        vnf_package_updates = {
            'operational_state': 'DISABLED',
            'tenant_id': req.environ['tacker.context'].project_id}
        mock_vnf_by_id.return_value = \
            fakes.return_vnfpkg_obj(vnf_package_updates=vnf_package_updates)
        body = {"operationalState": "DISABLED",
                "userDefinedData": {"testKey1": "val01",
                                    "testKey2": "val02", "testkey3": "val03"}}
        self.assertRaises(exc.HTTPConflict,
                          self.controller.patch,
                          req, constants.UUID, body=body)

    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    def test_patch_not_in_onboarded_state(self, mock_vnf_by_id):
        req = fake_request.HTTPRequest.blank('/vnf_packages/%s'
                                             % constants.UUID)
        vnf_package_updates = {'onboarding_state': 'CREATED',
            'operational_state': 'DISABLED',
            'tenant_id': req.environ['tacker.context'].project_id}
        mock_vnf_by_id.return_value = fakes.return_vnfpkg_obj(
            vnf_package_updates=vnf_package_updates)
        body = {"operationalState": "DISABLED"}
        self.assertRaises(exc.HTTPBadRequest,
                          self.controller.patch,
                          req, constants.UUID, body=body)

    @mock.patch.object(VNFPackageRPCAPI, "get_vnf_package_vnfd")
    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    @ddt.data('application/zip', 'text/plain,application/zip',
              'application/zip,text/plain')
    def test_get_vnf_package_vnfd_with_valid_accept_headers(
            self, accept_headers, mock_vnf_by_id, mock_get_vnf_package_vnfd):
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s/vnfd'
            % constants.UUID)
        mock_vnf_by_id.return_value = fakes.return_vnfpkg_obj(
            vnf_package_updates={
                'tenant_id': req.environ['tacker.context'].project_id})
        mock_get_vnf_package_vnfd.return_value = fakes.return_vnfd_data()
        req.headers['Accept'] = accept_headers
        req.method = 'GET'
        resp = req.get_response(self.app)
        self.assertEqual(http_client.OK, resp.status_code)

    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    def test_get_vnf_package_vnfd_with_invalid_accept_header(
            self, mock_vnf_by_id):
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s/vnfd'
            % constants.UUID)

        mock_vnf_by_id.return_value = fakes.return_vnfpkg_obj(
            vnf_package_updates={
                'tenant_id': req.environ['tacker.context'].project_id})
        req.headers['Accept'] = 'test-invalid-header'
        req.method = 'GET'
        self.assertRaises(exc.HTTPNotAcceptable,
                          self.controller.get_vnf_package_vnfd,
                          req, constants.UUID)

    @mock.patch.object(VNFPackageRPCAPI, "get_vnf_package_vnfd")
    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    def test_get_vnf_package_vnfd_failed_with_bad_request(
            self, mock_vnf_by_id, mock_get_vnf_package_vnfd):
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s/vnfd'
            % constants.UUID)
        mock_vnf_by_id.return_value = fakes.return_vnfpkg_obj(
            vnf_package_updates={
                'tenant_id': req.environ['tacker.context'].project_id})
        mock_get_vnf_package_vnfd.return_value = fakes.return_vnfd_data()
        req.headers['Accept'] = 'text/plain'
        req.method = 'GET'
        self.assertRaises(exc.HTTPBadRequest,
                          self.controller.get_vnf_package_vnfd,
                          req, constants.UUID)

    @mock.patch.object(VNFPackageRPCAPI, "get_vnf_package_vnfd")
    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    def test_get_vnf_package_vnfd_for_content_type_text_plain(self,
                                  mock_vnf_by_id,
                                  mock_get_vnf_package_vnfd):
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s/vnfd'
            % constants.UUID)

        mock_vnf_by_id.return_value = fakes.return_vnfpkg_obj(
            vnf_package_updates={
                'tenant_id': req.environ['tacker.context'].project_id})
        fake_vnfd_data = fakes.return_vnfd_data(csar_without_tosca_meta=True)
        mock_get_vnf_package_vnfd.return_value = fake_vnfd_data
        req.headers['Accept'] = 'text/plain'
        req.method = 'GET'
        resp = req.get_response(self.app)
        self.assertEqual(http_client.OK, resp.status_code)
        self.assertEqual('text/plain', resp.content_type)
        self.assertEqual(fake_vnfd_data[list(fake_vnfd_data.keys())[0]],
                         resp.text)

    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    def test_get_vnf_package_vnfd_failed_with_invalid_status(
            self, mock_vnf_by_id):
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s/vnfd'
            % constants.UUID)
        vnf_package_updates = {
            'onboarding_state': 'CREATED',
            'operational_state': 'DISABLED',
            'tenant_id': req.environ['tacker.context'].project_id
        }
        mock_vnf_by_id.return_value = fakes.return_vnfpkg_obj(
            vnf_package_updates=vnf_package_updates)
        req.headers['Accept'] = 'application/zip'
        req.method = 'GET'
        resp = req.get_response(self.app)
        self.assertEqual(http_client.CONFLICT, resp.status_code)

    def test_get_vnf_package_vnfd_with_invalid_uuid(self):
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s/vnfd'
            % constants.INVALID_UUID)
        req.headers['Accept'] = 'application/zip'
        req.method = 'GET'
        exception = self.assertRaises(exc.HTTPNotFound,
                                self.controller.get_vnf_package_vnfd,
                                req, constants.INVALID_UUID)
        self.assertEqual(
            "Can not find requested vnf package: %s" % constants.INVALID_UUID,
            exception.explanation)

    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    def test_get_vnf_package_vnfd_with_non_existing_vnf_packagee(
            self, mock_vnf_by_id):
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s/vnfd'
            % constants.UUID)
        req.headers['Accept'] = 'application/zip'
        req.method = 'GET'
        mock_vnf_by_id.side_effect = tacker_exc.VnfPackageNotFound
        self.assertRaises(exc.HTTPNotFound,
                          self.controller.get_vnf_package_vnfd, req,
                          constants.UUID)

    @mock.patch.object(VNFPackageRPCAPI, "get_vnf_package_vnfd")
    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    def test_get_vnf_package_vnfd_failed_with_internal_server_error(
            self, mock_vnf_by_id, mock_get_vnf_package_vnfd):
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s/vnfd'
            % constants.UUID)

        mock_vnf_by_id.return_value = fakes.return_vnfpkg_obj(
            vnf_package_updates={
                'tenant_id': req.environ['tacker.context'].project_id})
        mock_get_vnf_package_vnfd.side_effect = tacker_exc.FailedToGetVnfdData
        req.headers['Accept'] = 'application/zip'
        req.method = 'GET'
        resp = req.get_response(self.app)
        self.assertRaises(exc.HTTPInternalServerError,
                          self.controller.get_vnf_package_vnfd,
                          req, constants.UUID)
        self.assertEqual(http_client.INTERNAL_SERVER_ERROR, resp.status_code)

    def test_fetch_vnf_package_content_valid_range(self):
        request = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s/package_content/'
            % constants.UUID)
        request.headers["Range"] = 'bytes=10-99'
        range_ = self.controller._get_range_from_request(request, 120)
        self.assertEqual(10, range_.start)
        self.assertEqual(100, range_.end)  # non-inclusive

    def test_fetch_vnf_package_content_invalid_range(self):
        request = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s/package_content/'
            % constants.UUID)
        request.headers["Range"] = 'bytes=150-'
        self.assertRaises(exc.HTTPRequestRangeNotSatisfiable,
                          self.controller._get_range_from_request,
                          request, 120)
        request.headers["Range"] = 'bytes=110-100'
        self.assertRaises(exc.HTTPRequestRangeNotSatisfiable,
                          self.controller._get_range_from_request,
                          request, 120)
        request.headers["Range"] = 'bytes=100-120'
        self.assertRaises(exc.HTTPRequestRangeNotSatisfiable,
                          self.controller._get_range_from_request,
                          request, 120)

    def test_fetch_vnf_package_content_invalid_multiple_range(self):
        request = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s/package_content/'
            % constants.UUID)
        request.headers["Range"] = 'bytes=10-20,21-30'
        self.assertRaises(exc.HTTPBadRequest,
                          self.controller._get_range_from_request, request,
                          120)

    @mock.patch.object(controller.VnfPkgmController, "_download")
    @mock.patch.object(controller.VnfPkgmController, "_get_range_from_request")
    @mock.patch.object(glance_store, 'get_csar_size')
    @mock.patch.object(controller.VnfPkgmController, '_get_vnf_package')
    @mock.patch.object(vnf_package.VnfPackage, 'save')
    def test_fetch_vnf_package_content(
            self,
            mock_save,
            mock_get_vnf_package,
            mock_get_csar_size,
            mock_get_range,
            mock_download):
        request = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s/package_content/'
            % constants.UUID)
        request.headers["Range"] = 'bytes=10-20,21-30'
        request.response = ""
        mock_get_vnf_package.return_value = fakes.return_vnfpkg_obj(
            vnf_package_updates={
                'tenant_id': request.environ['tacker.context'].project_id})
        mock_get_csar_size.return_value = 1000
        mock_get_range.return_value = "10-20, 21-30"
        mock_download.return_value = "Response"
        id = constants.UUID
        result = self.controller.fetch_vnf_package_content(request, id)
        self.assertEqual(result, "Response")
        mock_get_csar_size.assert_called_once_with(
            id, fakes.return_vnfpkg_obj().location_glance_store)
        mock_get_vnf_package.assert_called_once_with(
            id, request)
        mock_get_range.assert_called_once_with(
            request, 1000)

    @mock.patch.object(controller.VnfPkgmController, '_get_vnf_package')
    def test_fetch_vnf_package_content_invalid_onboarding(
            self, mock_get):
        request = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s/package_content/'
            % constants.UUID)
        request.headers["Range"] = 'bytes=10-20,21-30'
        request.response = ""
        pkgobj = fakes.return_vnfpkg_obj(
            vnf_package_updates={
                'tenant_id': request.environ['tacker.context'].project_id})
        pkgobj.onboarding_state = fields.PackageOnboardingStateType.PROCESSING
        mock_get.return_value = pkgobj
        id = constants.UUID
        self.assertRaises(exc.HTTPConflict,
                          self.controller.fetch_vnf_package_content, request,
                          id)

    @mock.patch.object(controller.VnfPkgmController, '_get_vnf_package')
    def test_fetch_vnf_package_content_not_present(self, mock_get):
        request = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s/package_content/'
            % constants.UUID)
        request.headers["Range"] = 'bytes=10-20,21-30'
        request.response = ""
        pkgobj = fakes.return_vnfpkg_obj(
            vnf_package_updates={
                'tenant_id': request.environ['tacker.context'].project_id})
        mock_get.return_value = pkgobj
        id = constants.UUID
        self.assertRaises(exc.HTTPNotFound,
                          self.controller.fetch_vnf_package_content, request,
                          id)

    @mock.patch.object(controller.VnfPkgmController, "_download")
    @mock.patch.object(controller.VnfPkgmController, "_get_range_from_request")
    @mock.patch.object(controller.VnfPkgmController, '_get_vnf_package')
    def test_fetch_vnf_package_content_with_size(
            self,
            mock_get,
            mock_get_range,
            mock_download):
        request = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s/package_content/'
            % constants.UUID)
        request.headers["Range"] = 'bytes=10-20,21-30'
        request.response = ""
        pkgobj = fakes.return_vnfpkg_obj(
            vnf_package_updates={
                'tenant_id': request.environ['tacker.context'].project_id})
        pkgobj.size = 1000
        mock_get_range.return_value = "10-20, 21-30"
        mock_download.return_value = 1000
        mock_get.return_value = pkgobj
        id = constants.UUID
        result = self.controller.fetch_vnf_package_content(request, id)
        self.assertEqual(result, 1000)

    def test_fetch_vnf_package_artifacts_with_invalid_uuid(
            self):
        # invalid_uuid
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s/artifacts/%s'
            % (constants.INVALID_UUID, constants.ARTIFACT_PATH))
        req.method = 'GET'
        exception = self.assertRaises(exc.HTTPNotFound,
                          self.controller.fetch_vnf_package_artifacts,
                          req, constants.INVALID_UUID, constants.ARTIFACT_PATH)
        self.assertEqual(
            "Can not find requested vnf package: %s" % constants.INVALID_UUID,
            exception.explanation)

    @mock.patch.object(controller.VnfPkgmController, "_get_csar_path")
    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    def test_fetch_vnf_package_artifacts_with_invalid_path(
            self, mock_vnf_by_id, mock_get_csar_path):
        extract_path = utils.test_etc_sample(
            'sample_vnf_package_csar_in_meta_and_manifest')
        mock_get_csar_path.return_value = extract_path
        # valid_uuid
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s/artifacts/%s'
            % (constants.UUID, constants.INVALID_ARTIFACT_PATH))
        req.method = 'GET'
        mock_vnf_by_id.return_value = fakes.return_vnfpkg_obj(
            vnf_package_updates={
                'tenant_id': req.environ['tacker.context'].project_id})
        self.assertRaises(exc.HTTPNotFound,
                          self.controller.fetch_vnf_package_artifacts,
                          req, constants.UUID,
                          constants.INVALID_ARTIFACT_PATH)

    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    def test_fetch_vnf_package_artifacts_with_invalid_range(
            self, mock_vnf_by_id):
        mock_vnf_by_id.return_value = fakes.return_vnfpkg_obj()
        # valid_uuid
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s/artifacts/%s'
            % (constants.UUID, constants.ARTIFACT_PATH))
        req.headers['Range'] = 'bytes=150-'
        req.method = 'GET'
        self.assertRaises(exc.HTTPRequestRangeNotSatisfiable,
                          self.controller._get_range_from_request, req,
                          33)

    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    def test_fetch_vnf_package_artifacts_with_invalid_multiple_range(
            self, mock_vnf_by_id):
        mock_vnf_by_id.return_value = fakes.return_vnfpkg_obj()
        # valid_uuid
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s/artifacts/%s'
            % (constants.UUID, constants.ARTIFACT_PATH))
        req.headers['Range'] = 'bytes=10-20,21-30'
        req.method = 'GET'
        self.assertRaises(exc.HTTPBadRequest,
                          self.controller._get_range_from_request, req,
                          33)

    @mock.patch.object(controller.VnfPkgmController, "_get_csar_path")
    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    def test_fetch_vnf_package_artifacts_with_range(
            self, mock_vnf_by_id, mock_get_csar_path):
        mock_vnf_by_id.return_value = fakes.return_vnfpkg_obj()
        extract_path = utils.test_etc_sample(
            'sample_vnf_package_csar_in_meta_and_manifest')
        mock_get_csar_path.return_value = extract_path
        # valid_uuid
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s/artifacts/%s'
            % (constants.UUID, constants.ARTIFACT_PATH))
        req.headers['Range'] = 'bytes=10-30'
        req.method = 'GET'
        absolute_artifact_path = \
            os.path.join(extract_path, constants.ARTIFACT_PATH)
        with open(absolute_artifact_path, 'rb') as f:
            f.seek(10, 1)
            data = f.read(20)
        artifact_data = \
            self.controller._download_vnf_artifact(
                absolute_artifact_path, 10, 20)
        self.assertEqual(data, artifact_data)

    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    def test_fetch_vnf_package_artifacts_with_non_existing_vnf_package(
            self, mock_vnf_by_id):
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s/artifacts/%s'
            % (constants.UUID, constants.ARTIFACT_PATH))
        req.method = 'GET'
        mock_vnf_by_id.side_effect = tacker_exc.VnfPackageNotFound
        self.assertRaises(exc.HTTPNotFound,
                          self.controller.fetch_vnf_package_artifacts, req,
                          constants.UUID, constants.ARTIFACT_PATH)

    @mock.patch.object(controller.VnfPkgmController, "_get_csar_path")
    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    def test_fetch_vnf_package_artifacts_with_non_range(
            self, mock_vnf_by_id, mock_get_csar_path):
        mock_vnf_by_id.return_value = fakes.return_vnfpkg_obj()
        extract_path = utils.test_etc_sample(
            'sample_vnf_package_csar_in_meta_and_manifest')
        mock_get_csar_path.return_value = extract_path
        # valid_uuid
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s/artifacts/%s'
            % (constants.UUID, constants.ARTIFACT_PATH))
        req.method = 'GET'
        absolute_artifact_path = \
            os.path.join(extract_path, constants.ARTIFACT_PATH)
        with open(absolute_artifact_path, 'rb') as f:
            data = f.read()
        artifact_data = \
            self.controller._download_vnf_artifact(
                absolute_artifact_path, 0, 34)
        self.assertEqual(data, artifact_data)

    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    def test_fetch_vnf_package_artifacts_with_invalid_status(
            self, mock_vnf_by_id):
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s/artifacts/%s'
            % (constants.UUID, constants.ARTIFACT_PATH))
        vnf_package_updates = {
            'onboarding_state': 'CREATED',
            'operational_state': 'DISABLED',
            'tenant_id': req.environ['tacker.context'].project_id
        }
        mock_vnf_by_id.return_value = fakes.return_vnfpkg_obj(
            vnf_package_updates=vnf_package_updates)
        req.method = 'GET'
        self.assertRaises(exc.HTTPConflict,
                          self.controller.fetch_vnf_package_artifacts,
                          req, constants.UUID,
                          constants.ARTIFACT_PATH)


@ddt.ddt
class TestControllerEnhancedPolicy(TestController):

    def setUp(self):
        super(TestControllerEnhancedPolicy, self).setUp()
        cfg.CONF.set_override(
            "enhanced_tacker_policy", True, group='oslo_policy')

    @mock.patch.object(csar_utils, 'load_csar_data')
    @mock.patch.object(glance_store, 'load_csar')
    @mock.patch.object(glance_store, 'store_csar')
    @mock.patch.object(VNFPackageRPCAPI, "upload_vnf_package_content")
    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    @mock.patch.object(vnf_package.VnfPackage, "save")
    def test_upload_vnf_package_content(self, mock_vnf_pack_save,
                                        mock_vnf_by_id,
                                        mock_upload_vnf_package_content,
                                        mock_glance_store,
                                        mock_load_csar,
                                        mock_load_csar_data):
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s/package_content'
            % constants.UUID)

        updates = {'onboarding_state': 'CREATED',
                   'operational_state': 'DISABLED',
                   'tenant_id': req.environ['tacker.context'].project_id}
        vnf_package_dict = fakes.fake_vnf_package(updates)
        vnf_package_obj = objects.VnfPackage(**vnf_package_dict)
        mock_vnf_by_id.return_value = vnf_package_obj
        mock_vnf_pack_save.return_value = vnf_package_obj
        mock_glance_store.return_value = 'location', 0, 'checksum', \
            'multihash', 'loc_meta'
        mock_load_csar.return_value = '/var/lib/tacker/5f5d99c6-844a-4c3' \
                                      '1-9e6d-ab21b87dcfff.zip'
        mock_load_csar_data.return_value = (
            {'provider': 'company'}, mock.ANY, mock.ANY)
        req.headers['Content-Type'] = 'application/zip'
        req.method = 'PUT'
        req.body = jsonutils.dump_as_bytes({'dummy': {'val': 'foo'}})
        resp = req.get_response(self.app)
        mock_glance_store.assert_called()
        self.assertEqual(http_client.ACCEPTED, resp.status_code)

    @ddt.data(*fakes.get_test_data_pkg_to_upload('upload_package_content',
        http_client.ACCEPTED))
    @ddt.unpack
    @mock.patch.object(glance_store, 'delete_csar')
    @mock.patch.object(csar_utils, 'load_csar_data')
    @mock.patch.object(glance_store, 'load_csar')
    @mock.patch.object(glance_store, 'store_csar')
    @mock.patch.object(VNFPackageRPCAPI, "upload_vnf_package_content")
    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    @mock.patch.object(vnf_package.VnfPackage, "save")
    def test_upload_vnf_package_content_enhanced_policy(
            self, mock_vnf_pack_save,
            mock_vnf_by_id,
            mock_upload_vnf_package_content,
            mock_glance_store,
            mock_load_csar,
            mock_load_csar_data,
            mock_delete_csar,
            vnf_data, rules, roles, expected_status_code):
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s/package_content'
            % constants.UUID)

        updates = {'onboarding_state': 'CREATED',
                   'operational_state': 'DISABLED',
                   'tenant_id': req.environ['tacker.context'].project_id}
        vnf_package_dict = fakes.fake_vnf_package(updates)
        vnf_package_obj = objects.VnfPackage(**vnf_package_dict)
        mock_vnf_by_id.return_value = vnf_package_obj
        mock_vnf_pack_save.return_value = vnf_package_obj
        mock_glance_store.return_value = 'location', 0, 'checksum', \
            'multihash', 'loc_meta'
        mock_load_csar.return_value = '/var/lib/tacker/5f5d99c6-844a-4c3' \
                                      '1-9e6d-ab21b87dcfff.zip'
        mock_load_csar_data.return_value = (
            vnf_data, mock.ANY, mock.ANY)
        policy.set_rules(oslo_policy.Rules.from_dict(rules), overwrite=True)
        ctx = context.Context(
            'fake', 'fake', roles=roles)
        req.headers['Content-Type'] = 'application/zip'
        req.method = 'PUT'
        req.body = jsonutils.dump_as_bytes({'dummy': {'val': 'foo'}})
        resp = req.get_response(fakes.wsgi_app_v1(fake_auth_context=ctx))
        mock_glance_store.assert_called()
        self.assertEqual(expected_status_code, resp.status_code)
        if expected_status_code == http_client.FORBIDDEN:
            mock_delete_csar.assert_called()

    @ddt.data(*fakes.get_test_data_pkg_uploaded('show', http_client.OK))
    @ddt.unpack
    @mock.patch.object(VnfSoftwareImage, 'get_by_id')
    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    def test_show_enhanced_policy(
            self, mock_vnf_by_id, mock_sw_image_by_id,
            vnfd_updates, rules, roles, expected_status_code):

        mock_vnf_by_id.return_value = fakes.return_vnfpkg_obj(
            vnfd_updates=vnfd_updates)
        mock_sw_image_by_id.return_value = fakes.return_software_image()
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s' % constants.UUID)
        req.method = 'GET'
        policy.set_rules(oslo_policy.Rules.from_dict(rules), overwrite=True)
        ctx = context.Context(
            'fake', 'fake', roles=roles)

        resp = req.get_response(fakes.wsgi_app_v1(fake_auth_context=ctx))
        self.assertEqual(expected_status_code, resp.status_code)

    @mock.patch.object(VnfSoftwareImage, 'get_by_id')
    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    @ddt.data(['VENDOR_provider_A'], [])
    def test_show_enhanced_policy_created(
            self, roles, mock_vnf_by_id, mock_sw_image_by_id):
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s' % constants.UUID)

        updates = {'onboarding_state': 'CREATED',
                   'operational_state': 'DISABLED',
                   'tenant_id': req.environ['tacker.context'].project_id}
        mock_vnf_by_id.return_value = fakes.return_vnfpkg_obj(
            vnf_package_updates=updates)
        mock_sw_image_by_id.return_value = fakes.return_software_image()
        req.method = 'GET'
        rules = {
            vnf_package_policies.VNFPKGM % 'show':
                "vendor:%(vendor)s"
        }
        policy.set_rules(oslo_policy.Rules.from_dict(rules), overwrite=True)
        ctx = context.Context(
            'fake', 'fake', roles=roles)

        resp = req.get_response(fakes.wsgi_app_v1(fake_auth_context=ctx))
        self.assertEqual(http_client.OK, resp.status_code)

    @ddt.data(
        *fakes.get_test_data_pkg_uploaded('delete', http_client.NO_CONTENT))
    @ddt.unpack
    @mock.patch.object(vnf_package.VnfPackage, "destroy")
    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    @mock.patch.object(VNFPackageRPCAPI, "delete_vnf_package")
    def test_delete_enhanced_policy(
            self, mock_delete_rpc, mock_vnf_by_id, mock_vnf_pack_destroy,
            vnfd_updates, rules, roles, expected_status_code):
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s' % constants.UUID)
        vnfpkg_updates = {
            'operational_state': 'DISABLED',
            'tenant_id': req.environ['tacker.context'].project_id}
        mock_vnf_by_id.return_value = fakes.return_vnfpkg_obj(
            vnf_package_updates=vnfpkg_updates, vnfd_updates=vnfd_updates)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'DELETE'
        policy.set_rules(oslo_policy.Rules.from_dict(rules), overwrite=True)
        ctx = context.Context(
            'fake', 'fake', roles=roles)

        resp = req.get_response(fakes.wsgi_app_v1(fake_auth_context=ctx))
        self.assertEqual(expected_status_code, resp.status_code)

    @ddt.data(*fakes.get_test_data_pkg_uploaded('patch', http_client.OK))
    @ddt.unpack
    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    @mock.patch.object(vnf_package.VnfPackage, "save")
    def test_patch_enhanced_policy(self, mock_save, mock_vnf_by_id,
                   vnfd_updates, rules, roles, expected_status_code):
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s'
            % constants.UUID)
        vnf_package_updates = {
            'operational_state': 'DISABLED',
            'tenant_id': req.environ['tacker.context'].project_id}
        mock_vnf_by_id.return_value = \
            fakes.return_vnfpkg_obj(
                vnf_package_updates=vnf_package_updates,
                vnfd_updates=vnfd_updates
            )

        req_body = {"operationalState": "ENABLED",
                "userDefinedData": {"testKey1": "val01",
                                    "testKey2": "val02", "testkey3": "val03"}}

        req.headers['Content-Type'] = 'application/json'
        req.method = 'PATCH'
        req.body = jsonutils.dump_as_bytes(req_body)
        policy.set_rules(oslo_policy.Rules.from_dict(rules), overwrite=True)
        ctx = context.Context(
            'fake', 'fake', roles=roles)

        resp = req.get_response(fakes.wsgi_app_v1(fake_auth_context=ctx))

        self.assertEqual(expected_status_code, resp.status_code)
        if expected_status_code != http_client.FORBIDDEN:
            self.assertEqual(req_body, jsonutils.loads(resp.body))

    @ddt.data(*fakes.get_test_data_pkg_uploaded(
        'get_vnf_package_vnfd', http_client.OK))
    @ddt.unpack
    @mock.patch.object(VNFPackageRPCAPI, "get_vnf_package_vnfd")
    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    def test_get_vnf_package_vnfd_enhanced_policy(
            self, mock_vnf_by_id, mock_get_vnf_package_vnfd,
            vnfd_updates, rules, roles, expected_status_code):

        mock_vnf_by_id.return_value = fakes.return_vnfpkg_obj(
            vnfd_updates=vnfd_updates)
        mock_get_vnf_package_vnfd.return_value = fakes.return_vnfd_data()
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s/vnfd'
            % constants.UUID)
        req.headers['Accept'] = 'application/zip'
        req.method = 'GET'

        policy.set_rules(oslo_policy.Rules.from_dict(rules), overwrite=True)
        ctx = context.Context('fake', 'fake', roles=roles)

        resp = req.get_response(fakes.wsgi_app_v1(fake_auth_context=ctx))
        self.assertEqual(expected_status_code, resp.status_code)

    @ddt.data(*fakes.get_test_data_pkg_uploaded('fetch_package_content',
                                                http_client.ACCEPTED))
    @ddt.unpack
    @mock.patch.object(controller.VnfPkgmController, "_download")
    @mock.patch.object(controller.VnfPkgmController, "_get_range_from_request")
    @mock.patch.object(glance_store, 'get_csar_size')
    @mock.patch.object(controller.VnfPkgmController, '_get_vnf_package')
    @mock.patch.object(vnf_package.VnfPackage, 'save')
    def test_fetch_vnf_package_content_enhanced_policy(
            self,
            mock_save,
            mock_get_vnf_package,
            mock_get_csar_size,
            mock_get_range,
            mock_download,
            vnfd_updates, rules, roles, expected_status_code):

        mock_get_vnf_package.return_value = fakes.return_vnfpkg_obj(
            vnfd_updates=vnfd_updates)
        mock_get_csar_size.return_value = 1000
        mock_get_range.return_value = "10-20, 21-30"
        mock_download.return_value = "Response"

        request = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s/package_content' % constants.UUID)
        request.method = 'GET'

        request.headers["Range"] = 'bytes=10-20,21-30'
        request.response = ""

        policy.set_rules(oslo_policy.Rules.from_dict(rules), overwrite=True)
        ctx = context.Context('fake', 'fake', roles=roles)

        resp = request.get_response(fakes.wsgi_app_v1(fake_auth_context=ctx))

        self.assertEqual(expected_status_code, resp.status_code)

    @ddt.data(*fakes.get_test_data_pkg_uploaded('fetch_artifact',
                                                http_client.OK))
    @ddt.unpack
    @mock.patch.object(controller.VnfPkgmController, "_get_csar_path")
    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    def test_fetch_vnf_package_artifacts_enhanced_policy(
            self, mock_vnf_by_id, mock_get_csar_path,
            vnfd_updates, rules, roles, expected_status_code):
        mock_vnf_by_id.return_value = fakes.return_vnfpkg_obj(
            vnfd_updates=vnfd_updates)
        extract_path = utils.test_etc_sample(
            'sample_vnf_package_csar_in_meta_and_manifest')
        mock_get_csar_path.return_value = extract_path
        req = fake_request.HTTPRequest.blank(
            '/vnf_packages/%s/artifacts/%s'
            % (constants.UUID, constants.ARTIFACT_PATH))
        req.method = 'GET'

        policy.set_rules(oslo_policy.Rules.from_dict(rules), overwrite=True)
        ctx = context.Context('fake', 'fake', roles=roles)

        resp = req.get_response(fakes.wsgi_app_v1(fake_auth_context=ctx))

        self.assertEqual(expected_status_code, resp.status_code)

    @ddt.data(*fakes.get_test_data_pkg_index())
    @ddt.unpack
    @mock.patch.object(VnfPackagesList, "get_by_marker_filter")
    def test_index_enhanced_policy(
            self, mock_vnf_list, pkg_list, rules, roles, expected_pkg_ids):
        mock_vnf_list.return_value = pkg_list
        req = fake_request.HTTPRequest.blank('/vnf_packages')
        req.headers['Content-Type'] = 'application/json'
        req.method = 'GET'
        policy.set_rules(oslo_policy.Rules.from_dict(rules), overwrite=True)
        ctx = context.Context('fake', 'fake', roles=roles)

        resp = req.get_response(fakes.wsgi_app_v1(fake_auth_context=ctx))
        self.assertEqual(http_client.OK, resp.status_code)
        self.assertEqual(
            expected_pkg_ids, [pkg.get('id') for pkg in resp.json])

    @mock.patch.object(vnf_package.VnfPackage, "get_by_id")
    @mock.patch.object(VnfPackagesList, "get_by_marker_filter")
    def test_index_enhanced_policy_paging(self, mock_pkg_list, mock_pkg_by_id):
        cfg.CONF.set_override('vnf_package_num', 1, group='vnf_package')
        pkg_a_1 = fakes.return_vnfpkg_obj(
            vnf_package_updates={'id': uuidutils.generate_uuid()},
            vnfd_updates={
                'vnf_provider': 'provider_A',
                'id': uuidutils.generate_uuid(),
            })
        pkg_a_2 = copy.deepcopy(pkg_a_1)
        pkg_a_2.id = uuidutils.generate_uuid()
        pkg_a_2.vnfd.id = uuidutils.generate_uuid()
        pkg_b = fakes.return_vnfpkg_obj(
            vnf_package_updates={'id': uuidutils.generate_uuid()},
            vnfd_updates={
                'vnf_provider': 'provider_B',
                'id': uuidutils.generate_uuid(),
            })
        rules = {
            vnf_package_policies.VNFPKGM % 'index': "vendor:%(vendor)s"}
        roles = ['VENDOR_provider_A']
        policy.set_rules(oslo_policy.Rules.from_dict(rules), overwrite=True)
        ctx = context.Context('fake', 'fake', roles=roles)

        # first request
        mock_pkg_list.return_value = [pkg_a_1, pkg_b, pkg_a_2]
        req = fake_request.HTTPRequest.blank('/vnf_packages')
        req.headers['Content-Type'] = 'application/json'
        req.method = 'GET'
        resp = req.get_response(fakes.wsgi_app_v1(fake_auth_context=ctx))
        self.assertEqual(http_client.OK, resp.status_code)
        self.assertEqual(
            [pkg_a_1.id], [pkg.get('id') for pkg in resp.json])

        # second request with nextpage_opaque_marker
        mock_pkg_list.return_value = [pkg_b, pkg_a_2]
        mock_pkg_by_id.return_value = pkg_a_1
        req = fake_request.HTTPRequest.blank('/vnf_packages?'
            f'nextpage_opaque_marker={pkg_a_1.id}')
        req.headers['Content-Type'] = 'application/json'
        req.method = 'GET'
        resp = req.get_response(fakes.wsgi_app_v1(fake_auth_context=ctx))
        self.assertEqual(http_client.OK, resp.status_code)
        self.assertEqual(
            [pkg_a_2.id], [pkg.get('id') for pkg in resp.json])
