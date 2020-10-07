# Copyright (c) 2019 NTT DATA
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import base64
import datetime
import fixtures
import iso8601
import json
import os
import requests
import shutil
import six.moves.urllib.error as urlerr
import sys
import tacker.conf
import yaml

from glance_store import exceptions as store_exceptions
from oslo_config import cfg
from six.moves import urllib
from tacker import auth
from tacker.common import coordination
from tacker.common import csar_utils
from tacker.common import exceptions
from tacker.conductor import conductor_server
from tacker import context
from tacker import context as t_context
from tacker.glance_store import store as glance_store
from tacker import objects
from tacker.objects import fields
from tacker.plugins.common import constants
from tacker.tests.unit import base as unit_base
from tacker.tests.unit.conductor import fakes
from tacker.tests.unit.db.base import SqlTestCase
from tacker.tests.unit.db import utils as db_utils
from tacker.tests.unit.objects import fakes as fake_obj
from tacker.tests.unit.vnflcm import fakes as vnflcm_fakes
from tacker.tests.unit.vnfm.infra_drivers.openstack.fixture_data import client
from tacker.tests.unit.vnfm.infra_drivers.openstack.fixture_data import \
    fixture_data_utils as fd_utils
import tacker.tests.unit.vnfm.test_nfvo_client as nfvo_client
from tacker.tests import utils
from tacker.tests import uuidsentinel
import unittest
from unittest import mock


CONF = tacker.conf.CONF


class FakeVnfLcmDriver(mock.Mock):
    pass


class FakeVNFMPlugin(mock.Mock):
    pass


class TestConductor(SqlTestCase, unit_base.FixturedTestCase):
    client_fixture_class = client.ClientFixture
    sdk_connection_fixure_class = client.SdkConnectionFixture

    def setUp(self):
        super(TestConductor, self).setUp()
        self.addCleanup(mock.patch.stopall)
        self.context = context.get_admin_context()
        self._mock_vnflcm_driver()
        self._mock_vnfm_plugin()
        self.conductor = conductor_server.Conductor('host')
        self.vnf_package = self._create_vnf_package()
        self.instance_uuid = uuidsentinel.instance_id
        self.temp_dir = self.useFixture(fixtures.TempDir()).path
        self.body_data = self._create_body_data()
        self.vnf_lcm_opoccs = self._create_vnf_lcm_opoccs()
        self.vnfd_pkg_data = self._create_vnfd_pkg_data()

    def _mock_vnfm_plugin(self):
        self.vnfm_plugin = mock.Mock(wraps=FakeVNFMPlugin())
        fake_vnfm_plugin = mock.Mock()
        fake_vnfm_plugin.return_value = self.vnfm_plugin
        self._mock(
            'tacker.vnfm.plugin.VNFMPlugin', fake_vnfm_plugin)

    def _mock_vnflcm_driver(self):
        self.vnflcm_driver = mock.Mock(wraps=FakeVnfLcmDriver())
        fake_vnflcm_driver = mock.Mock()
        fake_vnflcm_driver.return_value = self.vnflcm_driver
        self._mock(
            'tacker.vnflcm.vnflcm_driver.VnfLcmDriver', fake_vnflcm_driver)

    def _create_vnf_package(self):
        vnfpkgm = objects.VnfPackage(context=self.context,
                                     **fakes.VNF_PACKAGE_DATA)
        vnfpkgm.create()
        return vnfpkgm

    def _create_vnf_package_vnfd(self):
        return fakes.get_vnf_package_vnfd()

    def _create_subscriptions(self, auth_params=None):
        class DummyLcmSubscription:
            def __init__(self, auth_params=None):
                if auth_params:
                    self.subscription_authentication = json.dumps(
                        auth_params).encode()

                self.id = uuidsentinel.lcm_subscription_id.encode()
                self.callback_uri = 'https://localhost/callback'.encode()

            def __getattr__(self, name):
                try:
                    return object.__getattr__(self, name)
                except AttributeError:
                    return None

        return [DummyLcmSubscription(auth_params)]

    def _create_body_data(self):
        body_data = {}
        body_data['vnf_instance_name'] = "new_instance_name"
        body_data['vnf_instance_description'] = "new_instance_discription"
        body_data['vnfd_id'] = "2c69a161-0000-4b0f-bcf8-391f8fc76600"
        body_data['vnf_configurable_properties'] = {"test": "test_value"}
        body_data['vnfc_info_modifications_delete_ids'] = ["test1"]
        body_data['vnf_pkg_id'] = uuidsentinel.vnf_pkg_id
        return body_data

    def _create_vnf_lcm_opoccs(self):
        vnf_lcm_opoccs = {
            'vnf_instance_id': uuidsentinel.vnf_instance_id,
            'id': uuidsentinel.id,
            'state_entered_time': datetime.datetime(
                1900, 1, 1, 1, 1, 1,
                tzinfo=iso8601.UTC),
            'operationParams': {
                "key": "value"}}
        return vnf_lcm_opoccs

    def _create_vnfd_pkg_data(self):
        vnfd_pkg_data = {}
        vnfd_pkg_data['vnf_provider'] = fakes.return_vnf_package_vnfd().get(
            'vnf_provider')
        vnfd_pkg_data['vnf_product_name'] =\
            fakes.return_vnf_package_vnfd().get('vnf_product_name')
        vnfd_pkg_data['vnf_software_version'] =\
            fakes.return_vnf_package_vnfd().get('vnf_software_version')
        vnfd_pkg_data['vnfd_version'] = fakes.return_vnf_package_vnfd().get(
            'vnfd_version')
        vnfd_pkg_data['package_uuid'] = fakes.return_vnf_package_vnfd().get(
            'package_uuid')
        return vnfd_pkg_data

    def assert_auth_basic(
            self,
            acutual_request,
            expected_user_name,
            expected_password):
        actual_auth = acutual_request._request.headers.get("Authorization")
        expected_auth = base64.b64encode(
            '{}:{}'.format(
                expected_user_name,
                expected_password).encode('utf-8')).decode()
        self.assertEqual("Basic " + expected_auth, actual_auth)

    def assert_auth_client_credentials(self, acutual_request, expected_token):
        actual_auth = acutual_request._request.headers.get(
            "Authorization")
        self.assertEqual("Bearer " + expected_token, actual_auth)

    @mock.patch.object(conductor_server.Conductor, '_onboard_vnf_package')
    @mock.patch.object(conductor_server, 'revert_upload_vnf_package')
    @mock.patch.object(csar_utils, 'load_csar_data')
    @mock.patch.object(glance_store, 'load_csar')
    def test_upload_vnf_package_content(self, mock_load_csar,
                                        mock_load_csar_data,
                                        mock_revert, mock_onboard):
        mock_load_csar_data.return_value = (mock.ANY, mock.ANY, mock.ANY)
        mock_load_csar.return_value = '/var/lib/tacker/5f5d99c6-844a-4c3' \
                                      '1-9e6d-ab21b87dcfff.zip'
        self.conductor.upload_vnf_package_content(
            self.context, self.vnf_package)
        mock_load_csar.assert_called()
        mock_load_csar_data.assert_called()
        mock_onboard.assert_called()

    @mock.patch.object(conductor_server.Conductor, '_onboard_vnf_package')
    @mock.patch.object(glance_store, 'store_csar')
    @mock.patch.object(conductor_server, 'revert_upload_vnf_package')
    @mock.patch.object(csar_utils, 'load_csar_data')
    @mock.patch.object(glance_store, 'load_csar')
    def test_upload_vnf_package_from_uri(self, mock_load_csar,
                                         mock_load_csar_data,
                                         mock_revert, mock_store,
                                         mock_onboard):
        address_information = "http://test.zip"
        mock_load_csar_data.return_value = (mock.ANY, mock.ANY, mock.ANY)
        mock_load_csar.return_value = '/var/lib/tacker/5f5d99c6-844a' \
                                      '-4c31-9e6d-ab21b87dcfff.zip'
        mock_store.return_value = 'location', 0, 'checksum',\
                                  'multihash', 'loc_meta'
        self.conductor.upload_vnf_package_from_uri(self.context,
                                                   self.vnf_package,
                                                   address_information,
                                                   user_name=None,
                                                   password=None)
        mock_load_csar.assert_called()
        mock_load_csar_data.assert_called()
        mock_store.assert_called()
        mock_onboard.assert_called()
        self.assertEqual('multihash', self.vnf_package.hash)
        self.assertEqual('location', self.vnf_package.location_glance_store)

    @mock.patch.object(glance_store, 'delete_csar')
    def test_delete_vnf_package(self, mock_delete_csar):
        self.vnf_package.__setattr__('onboarding_state', 'ONBOARDED')
        self.conductor.delete_vnf_package(self.context, self.vnf_package)
        mock_delete_csar.assert_called()

    def test_get_vnf_package_vnfd_with_tosca_meta_file_in_csar(self):
        fake_csar = fakes.create_fake_csar_dir(self.vnf_package.id,
                                               self.temp_dir)
        expected_data = fakes.get_expected_vnfd_data()
        result = self.conductor.get_vnf_package_vnfd(self.context,
                                                     self.vnf_package)
        self.assertEqual(expected_data, result)
        shutil.rmtree(fake_csar)

    def test_get_vnf_package_vnfd_with_single_yaml_csar(self):
        fake_csar = fakes.create_fake_csar_dir(
            self.vnf_package.id, self.temp_dir, csar_without_tosca_meta=True)
        result = self.conductor.get_vnf_package_vnfd(self.context,
                                                     self.vnf_package)
        # only one key present in the result shows that it contains only one
        # yaml file
        self.assertEqual(1, len(result.keys()))
        shutil.rmtree(fake_csar)

    @mock.patch.object(glance_store, 'load_csar')
    def test_get_vnf_package_vnfd_download_from_glance_store(self,
                                                             mock_load_csar):
        fake_csar = os.path.join(self.temp_dir, self.vnf_package.id)
        cfg.CONF.set_override('vnf_package_csar_path', self.temp_dir,
                              group='vnf_package')
        fake_csar_zip, _ = utils.create_csar_with_unique_vnfd_id(
            './tacker/tests/etc/samples/etsi/nfv/sample_vnfpkg_tosca_vnfd')
        mock_load_csar.return_value = fake_csar_zip
        expected_data = fakes.get_expected_vnfd_data(zip_file=fake_csar_zip)
        result = self.conductor.get_vnf_package_vnfd(self.context,
                                                     self.vnf_package)
        self.assertEqual(expected_data, result)
        shutil.rmtree(fake_csar)
        os.remove(fake_csar_zip)

    @mock.patch.object(glance_store, 'load_csar')
    def test_get_vnf_package_vnfd_exception_from_glance_store(self,
                                                              mock_load_csar):
        mock_load_csar.side_effect = store_exceptions.NotFound
        self.assertRaises(exceptions.FailedToGetVnfdData,
                          self.conductor.get_vnf_package_vnfd, self.context,
                          self.vnf_package)

    @mock.patch.object(conductor_server.Conductor, '_read_vnfd_files')
    def test_get_vnf_package_vnfd_exception_from_read_vnfd_files(
            self, mock_read_vnfd_files):
        fake_csar = fakes.create_fake_csar_dir(self.vnf_package.id,
                                               self.temp_dir)
        mock_read_vnfd_files.side_effect = yaml.YAMLError
        self.assertRaises(exceptions.FailedToGetVnfdData,
                          self.conductor.get_vnf_package_vnfd, self.context,
                          self.vnf_package)
        shutil.rmtree(fake_csar)

    def _create_and_upload_vnf_package(self):
        vnf_package = objects.VnfPackage(context=self.context,
                                         **fake_obj.vnf_package_data)
        vnf_package.create()

        vnf_pack_vnfd = fake_obj.get_vnf_package_vnfd_data(
            vnf_package.id, uuidsentinel.vnfd_id)

        vnf_pack_vnfd_obj = objects.VnfPackageVnfd(
            context=self.context, **vnf_pack_vnfd)
        vnf_pack_vnfd_obj.create()

        vnf_package.onboarding_state = "ONBOARDED"
        vnf_package.save()

        return vnf_pack_vnfd_obj

    @mock.patch('tacker.conductor.conductor_server.Conductor'
                '._update_vnf_attributes')
    @mock.patch('tacker.conductor.conductor_server.Conductor'
                '._change_vnf_status')
    @mock.patch.object(objects.VnfLcmOpOcc, "save")
    @mock.patch.object(coordination.Coordinator, 'get_lock')
    @mock.patch.object(objects.VnfLcmOpOcc, "get_by_id")
    def test_instantiate_vnf_instance(self, mock_vnf_by_id,
            mock_get_lock, mock_save, mock_change_vnf_status,
            mock_update_vnf_attributes):
        lcm_op_occs_data = fakes.get_lcm_op_occs_data()
        mock_vnf_by_id.return_value = \
            objects.VnfLcmOpOcc(context=self.context,
                                **lcm_op_occs_data)

        vnf_package_vnfd = self._create_and_upload_vnf_package()
        vnf_instance_data = fake_obj.get_vnf_instance_data(
            vnf_package_vnfd.vnfd_id)
        vnf_instance = objects.VnfInstance(context=self.context,
                                           **vnf_instance_data)
        vnf_instance.create()
        instantiate_vnf_req = vnflcm_fakes.get_instantiate_vnf_request_obj()
        vnf_lcm_op_occs_id = uuidsentinel.vnf_lcm_op_occs_id
        vnf_dict = {"status": "ACTIVE"}
        self.conductor.instantiate(self.context, vnf_instance, vnf_dict,
                                   instantiate_vnf_req, vnf_lcm_op_occs_id)
        self.vnflcm_driver.instantiate_vnf.assert_called_once_with(
            self.context, mock.ANY, vnf_dict, instantiate_vnf_req)
        self.vnflcm_driver._vnf_instance_update.assert_called_once()
        mock_change_vnf_status. \
            assert_called_once_with(self.context, vnf_instance.id,
                                    mock.ANY, 'PENDING_CREATE')
        mock_update_vnf_attributes.assert_called_once()

    @unittest.skip("Such test is no longer feasible.")
    @mock.patch.object(objects.VnfLcmOpOcc, "save")
    @mock.patch.object(coordination.Coordinator, 'get_lock')
    @mock.patch.object(objects.VnfPackage, 'is_package_in_use')
    @mock.patch('tacker.conductor.conductor_server.LOG')
    @mock.patch.object(objects.VnfLcmOpOcc, "get_by_id")
    def test_instantiate_vnf_instance_already_instantiated(
            self, mock_vnf_by_id, mock_log, mock_package_in_use, mock_get_lock,
            mock_save):
        lcm_op_occs_data = fakes.get_lcm_op_occs_data()
        mock_vnf_by_id.return_value = \
            objects.VnfLcmOpOcc(context=self.context,
                                **lcm_op_occs_data)

        vnf_package_vnfd = self._create_and_upload_vnf_package()
        vnf_instance_data = fake_obj.get_vnf_instance_data(
            vnf_package_vnfd.vnfd_id)
        vnf_instance_data['instantiation_state'] =\
            fields.VnfInstanceState.INSTANTIATED
        vnf_instance = objects.VnfInstance(context=self.context,
                                           **vnf_instance_data)
        vnf_instance.create()
        instantiate_vnf_req = vnflcm_fakes.get_instantiate_vnf_request_obj()
        vnf_lcm_op_occs_id = uuidsentinel.vnf_lcm_op_occs_id
        self.conductor.instantiate(self.context, vnf_instance,
                                   instantiate_vnf_req,
                                   vnf_lcm_op_occs_id)
        self.vnflcm_driver.instantiate_vnf.assert_not_called()
        mock_package_in_use.assert_not_called()
        expected_log = 'Vnf instance %(id)s is already in %(state)s state.'
        mock_log.error.assert_called_once_with(
            expected_log, {
                'id': vnf_instance.id,
                'state': fields.VnfInstanceState.INSTANTIATED})

    @unittest.skip("Such test is no longer feasible.")
    @mock.patch.object(objects.VnfLcmOpOcc, "save")
    @mock.patch.object(coordination.Coordinator, 'get_lock')
    @mock.patch.object(objects.VnfPackage, 'is_package_in_use')
    @mock.patch.object(objects.LccnSubscriptionRequest,
        'vnf_lcm_subscriptions_get')
    @mock.patch.object(objects.VnfLcmOpOcc, "get_by_id")
    def test_instantiate_vnf_instance_with_vnf_package_in_use(
            self,
            mock_vnf_by_id,
            mock_vnf_lcm_subscriptions_get,
            mock_vnf_package_in_use,
            mock_get_lock,
            mock_save):
        lcm_op_occs_data = fakes.get_lcm_op_occs_data()
        mock_vnf_by_id.return_value = \
            objects.VnfLcmOpOcc(context=self.context,
                                **lcm_op_occs_data)

        vnf_package_vnfd = self._create_and_upload_vnf_package()
        vnf_instance_data = fake_obj.get_vnf_instance_data(
            vnf_package_vnfd.vnfd_id)
        m_vnf_lcm_subscriptions = \
            [mock.MagicMock(**fakes.get_vnf_lcm_subscriptions())]
        mock_vnf_lcm_subscriptions_get.return_value = \
            m_vnf_lcm_subscriptions
        mock_vnf_package_in_use.return_value = True
        vnf_instance = objects.VnfInstance(context=self.context,
                                           **vnf_instance_data)
        vnf_instance.create()
        instantiate_vnf_req = vnflcm_fakes.get_instantiate_vnf_request_obj()
        vnf_lcm_op_occs_id = uuidsentinel.vnf_lcm_op_occs_id
        self.conductor.instantiate(self.context, vnf_instance,
                                   instantiate_vnf_req,
                                   vnf_lcm_op_occs_id)
        self.vnflcm_driver.instantiate_vnf.assert_called_once_with(
            self.context, mock.ANY, instantiate_vnf_req)
        mock_vnf_package_in_use.assert_called_once()

    @mock.patch('tacker.conductor.conductor_server.Conductor'
                '._update_vnf_attributes')
    @mock.patch('tacker.conductor.conductor_server.Conductor'
                '._change_vnf_status')
    @mock.patch.object(objects.VnfLcmOpOcc, "save")
    @mock.patch.object(coordination.Coordinator, 'get_lock')
    @mock.patch.object(objects.LccnSubscriptionRequest,
        'vnf_lcm_subscriptions_get')
    @mock.patch('tacker.conductor.conductor_server.LOG')
    @mock.patch.object(objects.VnfLcmOpOcc, "get_by_id")
    @mock.patch('tacker.vnflcm.utils._get_affected_resources')
    def test_instantiate_vnf_instance_failed_with_exception(
            self, mock_res, mock_vnf_by_id, mock_log,
            mock_vnf_lcm_subscriptions_get,
            mock_get_lock, mock_save, mock_change_vnf_status,
            mock_update_vnf_attributes):
        lcm_op_occs_data = fakes.get_lcm_op_occs_data()
        mock_vnf_by_id.return_value = \
            objects.VnfLcmOpOcc(context=self.context,
                                **lcm_op_occs_data)

        vnf_package_vnfd = self._create_and_upload_vnf_package()
        vnf_instance_data = fake_obj.get_vnf_instance_data(
            vnf_package_vnfd.vnfd_id)
        vnf_instance = objects.VnfInstance(context=self.context,
                                           **vnf_instance_data)
        vnf_instance.create()
        instantiate_vnf_req = vnflcm_fakes.get_instantiate_vnf_request_obj()
        vnf_lcm_op_occs_id = uuidsentinel.vnf_lcm_op_occs_id
        vnf_dict = {"status": "ACTIVE"}
        m_vnf_lcm_subscriptions = \
            [mock.MagicMock(**fakes.get_vnf_lcm_subscriptions())]
        mock_vnf_lcm_subscriptions_get.return_value = \
            m_vnf_lcm_subscriptions
        mock_update_vnf_attributes.side_effect = Exception
        mock_res.return_value = {}
        self.conductor.instantiate(self.context, vnf_instance, vnf_dict,
                                   instantiate_vnf_req, vnf_lcm_op_occs_id)
        self.vnflcm_driver.instantiate_vnf.assert_called_once_with(
            self.context, vnf_instance, vnf_dict, instantiate_vnf_req)
        mock_change_vnf_status.assert_called_with(self.context,
            vnf_instance.id, mock.ANY, 'ERROR')
        mock_update_vnf_attributes.assert_called_once()

    @mock.patch('tacker.conductor.conductor_server.Conductor'
                '._change_vnf_status')
    @mock.patch('tacker.conductor.conductor_server.Conductor'
                '._send_lcm_op_occ_notification')
    @mock.patch.object(coordination.Coordinator, 'get_lock')
    def test_terminate_vnf_instance(self, mock_get_lock,
                                    mock_send_notification,
                                    mock_change_vnf_status):
        inst_vnf_info = fd_utils.get_vnf_instantiated_info()
        vnf_instance = fd_utils. \
            get_vnf_instance_object(instantiated_vnf_info=inst_vnf_info)

        terminate_vnf_req = objects.TerminateVnfRequest(
            termination_type=fields.VnfInstanceTerminationType.GRACEFUL,
            additional_params={"key": "value"})
        vnf_lcm_op_occs_id = uuidsentinel.vnf_lcm_op_occs_id
        vnf_dict = db_utils.get_dummy_vnf(instance_id=self.instance_uuid)
        self.conductor.terminate(self.context, vnf_lcm_op_occs_id,
                                 vnf_instance, terminate_vnf_req, vnf_dict)

        self.vnflcm_driver.terminate_vnf.assert_called_once_with(
            self.context, vnf_instance, terminate_vnf_req)
        self.vnflcm_driver._vnf_instance_update.assert_called_once()
        self.assertEqual(mock_send_notification.call_count, 2)
        self.assertEqual(mock_change_vnf_status.call_count, 2)

    @mock.patch('tacker.conductor.conductor_server.Conductor'
                '._change_vnf_status')
    @mock.patch('tacker.conductor.conductor_server.Conductor'
                '._send_lcm_op_occ_notification')
    @mock.patch.object(coordination.Coordinator, 'get_lock')
    def test_terminate_vnf_instance_exception(self, mock_get_lock,
                                    mock_send_notification,
                                    mock_change_vnf_status):
        inst_vnf_info = fd_utils.get_vnf_instantiated_info()
        vnf_instance = fd_utils. \
            get_vnf_instance_object(instantiated_vnf_info=inst_vnf_info)

        mock_send_notification.side_effect = Exception
        terminate_vnf_req = objects.TerminateVnfRequest(
            termination_type=fields.VnfInstanceTerminationType.GRACEFUL,
            additional_params={"key": "value"})
        vnf_lcm_op_occs_id = uuidsentinel.vnf_lcm_op_occs_id
        vnf_dict = db_utils.get_dummy_vnf(instance_id=self.instance_uuid)
        try:
            self.conductor.terminate(self.context, vnf_lcm_op_occs_id,
                                 vnf_instance, terminate_vnf_req, vnf_dict)
        except Exception:
            pass
        self.vnflcm_driver.terminate_vnf.assert_not_called()
        mock_change_vnf_status.assert_called_once_with(self.context,
            vnf_instance.id, mock.ANY, 'ERROR')
        self.assertEqual(mock_send_notification.call_count, 2)

    @unittest.skip("Such test is no longer feasible.")
    @mock.patch('tacker.conductor.conductor_server.Conductor.'
                '_send_lcm_op_occ_notification')
    @mock.patch.object(coordination.Coordinator, 'get_lock')
    @mock.patch.object(objects.VnfPackage, 'is_package_in_use')
    @mock.patch('tacker.conductor.conductor_server.LOG')
    def test_terminate_vnf_instance_already_not_instantiated(self,
            mock_log, mock_package_in_use, mock_get_lock,
            mock_send_notification):
        vnf_package_vnfd = self._create_and_upload_vnf_package()
        vnf_instance_data = fake_obj.get_vnf_instance_data(
            vnf_package_vnfd.vnfd_id)
        mock_package_in_use.return_value = True
        vnf_instance_data['instantiation_state'] =\
            fields.VnfInstanceState.NOT_INSTANTIATED
        vnf_instance = objects.VnfInstance(context=self.context,
                                           **vnf_instance_data)
        vnf_instance.create()

        terminate_vnf_req = objects.TerminateVnfRequest(
            termination_type=fields.VnfInstanceTerminationType.GRACEFUL,
            additional_params={"key": "value"})
        vnf_lcm_op_occs_id = uuidsentinel.vnf_lcm_op_occs_id
        vnf_dict = db_utils.get_dummy_vnf(instance_id=self.instance_uuid)
        self.conductor.terminate(self.context, vnf_lcm_op_occs_id,
                                 vnf_instance,
                                 terminate_vnf_req, vnf_dict)

        self.vnflcm_driver.terminate_vnf.assert_not_called()
        mock_package_in_use.assert_not_called()
        expected_log = ('Terminate action cannot be performed on vnf %(id)s '
                        'which is in %(state)s state.')
        mock_log.error.assert_called_once_with(
            expected_log, {
                'id': vnf_instance.id,
                'state': fields.VnfInstanceState.NOT_INSTANTIATED})

    @unittest.skip("Such test is no longer feasible.")
    @mock.patch('tacker.conductor.conductor_server.Conductor.'
                '_send_lcm_op_occ_notification')
    @mock.patch.object(coordination.Coordinator, 'get_lock')
    @mock.patch.object(objects.VnfPackage, 'is_package_in_use')
    def test_terminate_vnf_instance_with_usage_state_not_in_use(self,
            mock_vnf_package_is_package_in_use, mock_get_lock,
            mock_send_notification):
        vnf_package_vnfd = self._create_and_upload_vnf_package()
        vnf_instance_data = fake_obj.get_vnf_instance_data(
            vnf_package_vnfd.vnfd_id)
        vnf_instance_data['instantiation_state'] =\
            fields.VnfInstanceState.INSTANTIATED
        vnf_instance = objects.VnfInstance(context=self.context,
                                           **vnf_instance_data)
        vnf_instance.create()

        mock_vnf_package_is_package_in_use.return_value = False
        terminate_vnf_req = objects.TerminateVnfRequest(
            termination_type=fields.VnfInstanceTerminationType.GRACEFUL,
            additional_params={"key": "value"})
        vnf_lcm_op_occs_id = uuidsentinel.vnf_lcm_op_occs_id
        vnf_dict = db_utils.get_dummy_vnf(instance_id=self.instance_uuid)
        self.conductor.terminate(self.context, vnf_lcm_op_occs_id,
                                 vnf_instance,
                                 terminate_vnf_req, vnf_dict)

        self.vnflcm_driver.terminate_vnf.assert_called_once_with(
            self.context, mock.ANY, terminate_vnf_req,
            vnf_lcm_op_occs_id)
        mock_vnf_package_is_package_in_use.assert_called_once()

    @unittest.skip("Such test is no longer feasible.")
    @mock.patch('tacker.conductor.conductor_server.Conductor.'
                '_send_lcm_op_occ_notification')
    @mock.patch.object(coordination.Coordinator, 'get_lock')
    @mock.patch.object(objects.VnfPackage, 'is_package_in_use')
    def test_terminate_vnf_instance_with_usage_state_already_in_use(self,
            mock_vnf_package_is_package_in_use, mock_get_lock,
            mock_send_notification):
        vnf_package_vnfd = self._create_and_upload_vnf_package()
        vnf_instance_data = fake_obj.get_vnf_instance_data(
            vnf_package_vnfd.vnfd_id)
        vnf_instance_data['instantiation_state'] =\
            fields.VnfInstanceState.INSTANTIATED
        vnf_instance = objects.VnfInstance(context=self.context,
                                           **vnf_instance_data)
        vnf_instance.create()

        mock_vnf_package_is_package_in_use.return_value = True
        terminate_vnf_req = objects.TerminateVnfRequest(
            termination_type=fields.VnfInstanceTerminationType.GRACEFUL,
            additional_params={"key": "value"})
        vnf_lcm_op_occs_id = uuidsentinel.vnf_lcm_op_occs_id
        vnf_dict = db_utils.get_dummy_vnf(instance_id=self.instance_uuid)
        self.conductor.terminate(self.context, vnf_lcm_op_occs_id,
                                 vnf_instance,
                                 terminate_vnf_req, vnf_dict)

        self.vnflcm_driver.terminate_vnf.assert_called_once_with(
            self.context, mock.ANY, terminate_vnf_req,
            vnf_lcm_op_occs_id)
        mock_vnf_package_is_package_in_use.assert_called_once()

    @unittest.skip("Such test is no longer feasible.")
    @mock.patch('tacker.conductor.conductor_server.Conductor.'
                '_send_lcm_op_occ_notification')
    @mock.patch.object(coordination.Coordinator, 'get_lock')
    @mock.patch.object(objects.VnfPackage, 'is_package_in_use')
    @mock.patch('tacker.conductor.conductor_server.LOG')
    def test_terminate_vnf_instance_failed_to_update_usage_state(
            self, mock_log, mock_is_package_in_use, mock_get_lock,
            mock_send_notification):
        vnf_package_vnfd = self._create_and_upload_vnf_package()
        vnf_instance_data = fake_obj.get_vnf_instance_data(
            vnf_package_vnfd.vnfd_id)
        vnf_instance_data['instantiation_state'] =\
            fields.VnfInstanceState.INSTANTIATED
        vnf_instance = objects.VnfInstance(context=self.context,
                                           **vnf_instance_data)
        vnf_instance.create()
        terminate_vnf_req = objects.TerminateVnfRequest(
            termination_type=fields.VnfInstanceTerminationType.GRACEFUL,
            additional_params={"key": "value"})
        mock_is_package_in_use.side_effect = Exception
        vnf_lcm_op_occs_id = uuidsentinel.vnf_lcm_op_occs_id
        vnf_dict = db_utils.get_dummy_vnf(instance_id=self.instance_uuid)
        self.conductor.terminate(self.context, vnf_lcm_op_occs_id,
                                 vnf_instance,
                                 terminate_vnf_req, vnf_dict)
        self.vnflcm_driver.terminate_vnf.assert_called_once_with(
            self.context, mock.ANY, terminate_vnf_req,
            vnf_lcm_op_occs_id)
        expected_msg = "Failed to update usage_state of vnf package %s"
        mock_log.error.assert_called_once_with(expected_msg,
                                               vnf_package_vnfd.package_uuid)

    @mock.patch('tacker.conductor.conductor_server.Conductor.'
                '_add_additional_vnf_info')
    @mock.patch('tacker.conductor.conductor_server.Conductor.'
                '_update_instantiated_vnf_info')
    @mock.patch('tacker.conductor.conductor_server.Conductor.'
                '_change_vnf_status')
    @mock.patch.object(objects.VnfLcmOpOcc, "save")
    @mock.patch.object(coordination.Coordinator, 'get_lock')
    @mock.patch.object(objects.VnfLcmOpOcc, "get_by_id")
    def test_heal_vnf_instance(self, mock_vnf_by_id, mock_get_lock,
            mock_save, mock_change_vnf_status,
            mock_update_insta_vnf_info, mock_add_additional_vnf_info):
        lcm_op_occs_data = fakes.get_lcm_op_occs_data()
        mock_vnf_by_id.return_value = \
            objects.VnfLcmOpOcc(context=self.context,
                                **lcm_op_occs_data)
        vnf_package_vnfd = self._create_and_upload_vnf_package()
        vnf_instance_data = fake_obj.get_vnf_instance_data(
            vnf_package_vnfd.vnfd_id)
        vnf_instance = objects.VnfInstance(context=self.context,
                                           **vnf_instance_data)
        vnf_instance.create()
        vnf_instance.instantiation_state = \
            fields.VnfInstanceState.INSTANTIATED
        vnf_instance.save()
        heal_vnf_req = objects.HealVnfRequest(cause="healing request")
        vnf_dict = {"fake": "fake_dict"}
        vnf_lcm_op_occs_id = uuidsentinel.vnf_lcm_op_occs_id
        self.conductor.heal(self.context, vnf_instance, vnf_dict,
                            heal_vnf_req, vnf_lcm_op_occs_id)
        self.assertEqual(mock_change_vnf_status.call_count, 2)
        mock_update_insta_vnf_info. \
            assert_called_once_with(self.context, vnf_instance, heal_vnf_req)
        mock_add_additional_vnf_info. \
            assert_called_once_with(self.context, vnf_instance)

    @mock.patch('tacker.conductor.conductor_server.Conductor.'
                '_send_lcm_op_occ_notification')
    @mock.patch('tacker.conductor.conductor_server.Conductor.'
                '_update_instantiated_vnf_info')
    @mock.patch('tacker.conductor.conductor_server.Conductor.'
                '_change_vnf_status')
    @mock.patch('tacker.conductor.conductor_server.Conductor.'
                '_add_additional_vnf_info')
    @mock.patch.object(coordination.Coordinator, 'get_lock')
    @mock.patch('tacker.conductor.conductor_server.LOG')
    def test_heal_vnf_instance_exception(self,
            mock_log, mock_get_lock, mock_add_additional_vnf_info,
            mock_change_vnf_status, mock_update_insta_vnf_info,
            mock_send_notification):
        vnf_package_vnfd = self._create_and_upload_vnf_package()
        vnf_instance_data = fake_obj.get_vnf_instance_data(
            vnf_package_vnfd.vnfd_id)

        vnf_instance_data['instantiation_state'] =\
            fields.VnfInstanceState.NOT_INSTANTIATED
        vnf_instance = objects.VnfInstance(context=self.context,
                                           **vnf_instance_data)
        vnf_instance.create()
        mock_add_additional_vnf_info.side_effect = Exception

        heal_vnf_req = objects.HealVnfRequest(cause="healing request")
        vnf_dict = {"fake": "fake_dict"}
        vnf_lcm_op_occs_id = uuidsentinel.vnf_lcm_op_occs_id
        self.conductor.heal(self.context, vnf_instance, vnf_dict,
                            heal_vnf_req, vnf_lcm_op_occs_id)
        mock_change_vnf_status.assert_called_with(self.context,
            vnf_instance, mock.ANY, constants.ERROR, "")
        mock_update_insta_vnf_info.assert_called_with(self.context,
            vnf_instance, heal_vnf_req)
        self.assertEqual(mock_send_notification.call_count, 2)

    @unittest.skip("Such test is no longer feasible.")
    @mock.patch.object(coordination.Coordinator, 'get_lock')
    @mock.patch('tacker.conductor.conductor_server.LOG')
    def test_heal_vnf_instance_already_not_instantiated(
            self, mock_log, mock_get_lock):
        vnf_package_vnfd = self._create_and_upload_vnf_package()
        vnf_instance_data = fake_obj.get_vnf_instance_data(
            vnf_package_vnfd.vnfd_id)

        vnf_instance_data['instantiation_state'] =\
            fields.VnfInstanceState.NOT_INSTANTIATED
        vnf_instance = objects.VnfInstance(context=self.context,
                                           **vnf_instance_data)
        vnf_instance.create()

        heal_vnf_req = objects.HealVnfRequest(cause="healing request")
        vnf_dict = {"fake": "fake_dict"}
        vnf_lcm_op_occs_id = uuidsentinel.vnf_lcm_op_occs_id
        self.conductor.heal(self.context, vnf_instance, vnf_dict,
                            heal_vnf_req, vnf_lcm_op_occs_id)

        self.vnflcm_driver.heal_vnf.assert_not_called()
        expected_log = ('Heal action cannot be performed on vnf %(id)s '
                        'which is in %(state)s state.')
        mock_log.error.assert_called_once_with(
            expected_log, {
                'id': vnf_instance.id,
                'state': fields.VnfInstanceState.NOT_INSTANTIATED})

    @mock.patch.object(os, 'remove')
    @mock.patch.object(shutil, 'rmtree')
    @mock.patch.object(os.path, 'exists')
    @mock.patch.object(objects.VnfPackagesList, 'get_by_filters')
    def test_run_cleanup_vnf_packages(self, mock_get_by_filter,
                                      mock_exists, mock_rmtree,
                                      mock_remove):
        vnf_package_data = {'algorithm': None, 'hash': None,
                            'location_glance_store': None,
                            'onboarding_state': 'CREATED',
                            'operational_state': 'DISABLED',
                            'tenant_id': uuidsentinel.tenant_id,
                            'usage_state': 'NOT_IN_USE',
                            'user_data': {'abc': 'xyz'}
                            }

        vnfpkgm = objects.VnfPackage(context=self.context, **vnf_package_data)
        vnfpkgm.create()
        vnfpkgm.destroy(self.context)

        mock_get_by_filter.return_value = [vnfpkgm]
        mock_exists.return_value = True
        conductor_server.Conductor('host')._run_cleanup_vnf_packages(
            self.context)
        mock_get_by_filter.assert_called()
        mock_rmtree.assert_called()
        mock_remove.assert_called()

    @mock.patch.object(sys, 'exit')
    @mock.patch.object(conductor_server.LOG, 'error')
    @mock.patch.object(glance_store, 'initialize_glance_store')
    @mock.patch.object(os.path, 'isdir')
    def test_init_host(self, mock_isdir, mock_initialize_glance_store,
                       mock_log_error, mock_exit):
        mock_isdir.return_value = False
        self.conductor.init_host()
        mock_log_error.assert_called()
        mock_exit.assert_called_with(1)
        self.assertIn("Config option 'vnf_package_csar_path' is not configured"
                      " correctly. VNF package CSAR path directory %s doesn't"
                      " exist", mock_log_error.call_args[0][0])

    @mock.patch.object(urllib.request, 'urlopen')
    def test_upload_vnf_package_from_uri_with_invalid_auth(self,
                                                           mock_url_open):
        address_information = "http://localhost/test.zip"
        user_name = "username"
        password = "password"
        mock_url_open.side_effect = urlerr.HTTPError(
            url='', code=401, msg='HTTP Error 401 Unauthorized', hdrs={},
            fp=None)
        self.assertRaises(exceptions.VNFPackageURLInvalid,
                          self.conductor.upload_vnf_package_from_uri,
                          self.context,
                          self.vnf_package,
                          address_information,
                          user_name=user_name,
                          password=password)
        self.assertEqual('CREATED', self.vnf_package.onboarding_state)

    @mock.patch.object(coordination.Coordinator, 'get_lock')
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    def test_scale(self, mock_vnf_by_id, mock_get_lock):
        mock_vnf_by_id.return_value = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED)

        vnf_info = fakes._get_vnf()
        vnf_instance = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED,
            scale_status="scale_status")
        scale_vnf_request = fakes.scale_request("SCALE_IN", 1)

        self.conductor.scale(
            self.context,
            vnf_info,
            vnf_instance,
            scale_vnf_request)
        self.vnflcm_driver.scale_vnf.assert_called_once_with(
            self.context, vnf_info, mock.ANY, scale_vnf_request)

    @mock.patch.object(objects.LccnSubscriptionRequest,
                       'vnf_lcm_subscriptions_get')
    def test_send_notification_not_found_subscription(self,
                                                   mock_subscriptions_get):
        mock_subscriptions_get.return_value = None
        notification = {
            'vnfInstanceId': 'Test',
            'notificationType': 'VnfLcmOperationOccurrenceNotification'}

        result = self.conductor.send_notification(self.context, notification)

        self.assertEqual(result, -1)
        mock_subscriptions_get.assert_called()

    @mock.patch.object(objects.LccnSubscriptionRequest,
                       'vnf_lcm_subscriptions_get')
    def test_send_notification_vnf_lcm_operation_occurrence(self,
                                                    mock_subscriptions_get):
        self.requests_mock.register_uri('POST',
            "https://localhost/callback",
            headers={
                'Content-Type': 'application/json'},
            status_code=204)

        mock_subscriptions_get.return_value = self._create_subscriptions()
        notification = {
            'vnfInstanceId': 'Test',
            'notificationType': 'VnfLcmOperationOccurrenceNotification',
            'operationTypes': 'SCALE',
            'operationStates': 'RESULT',
            '_links': {}}

        result = self.conductor.send_notification(self.context, notification)

        self.assertEqual(result, 0)
        mock_subscriptions_get.assert_called()

        history = self.requests_mock.request_history
        req_count = nfvo_client._count_mock_history(
            history, "https://localhost")
        self.assertEqual(1, req_count)

    @mock.patch.object(objects.LccnSubscriptionRequest,
                       'vnf_lcm_subscriptions_get')
    def test_send_notification_vnf_identifier_creation(self,
                                                    mock_subscriptions_get):
        self.requests_mock.register_uri(
            'POST',
            "https://localhost/callback",
            headers={
                'Content-Type': 'application/json'},
            status_code=204)

        mock_subscriptions_get.return_value = self._create_subscriptions()
        notification = {
            'vnfInstanceId': 'Test',
            'notificationType': 'VnfIdentifierCreationNotification',
            'links': {}}

        result = self.conductor.send_notification(self.context, notification)

        self.assertEqual(result, 0)
        mock_subscriptions_get.assert_called()

        history = self.requests_mock.request_history
        req_count = nfvo_client._count_mock_history(
            history, "https://localhost")
        self.assertEqual(1, req_count)

    @mock.patch.object(objects.LccnSubscriptionRequest,
                       'vnf_lcm_subscriptions_get')
    def test_send_notification_with_auth_basic(self, mock_subscriptions_get):
        self.requests_mock.register_uri('POST',
            "https://localhost/callback",
            headers={
                'Content-Type': 'application/json'},
            status_code=204)

        auth_user_name = 'test_user'
        auth_password = 'test_password'
        mock_subscriptions_get.return_value = self._create_subscriptions(
            {'authType': 'BASIC',
            'paramsBasic': {'userName': auth_user_name,
                            'password': auth_password}})

        notification = {
            'vnfInstanceId': 'Test',
            'notificationType': 'VnfIdentifierCreationNotification',
            'links': {}}

        result = self.conductor.send_notification(self.context, notification)

        self.assertEqual(result, 0)
        mock_subscriptions_get.assert_called()

        history = self.requests_mock.request_history
        req_count = nfvo_client._count_mock_history(
            history, "https://localhost")
        self.assertEqual(1, req_count)
        self.assert_auth_basic(
            history[0],
            auth_user_name,
            auth_password)

    @mock.patch.object(objects.LccnSubscriptionRequest,
                       'vnf_lcm_subscriptions_get')
    def test_send_notification_with_auth_client_credentials(
            self, mock_subscriptions_get):
        auth.auth_manager = auth._AuthManager()
        self.requests_mock.register_uri(
            'POST',
            "https://localhost/callback",
            headers={
                'Content-Type': 'application/json'},
            status_code=204)

        auth_user_name = 'test_user'
        auth_password = 'test_password'
        token_endpoint = 'https://oauth2/tokens'
        self.requests_mock.register_uri(
            'GET', token_endpoint, json={
                'access_token': 'test_token', 'token_type': 'bearer'},
            headers={'Content-Type': 'application/json'},
            status_code=200)

        mock_subscriptions_get.return_value = self._create_subscriptions(
            {'authType': ['OAUTH2_CLIENT_CREDENTIALS'],
            'paramsOauth2ClientCredentials': {
                'clientId': auth_user_name,
                'clientPassword': auth_password,
                'tokenEndpoint': token_endpoint}})

        notification = {
            'vnfInstanceId': 'Test',
            'notificationType': 'VnfIdentifierCreationNotification',
            'links': {}}

        result = self.conductor.send_notification(self.context, notification)

        self.assertEqual(result, 0)
        mock_subscriptions_get.assert_called()

        history = self.requests_mock.request_history
        req_count = nfvo_client._count_mock_history(
            history, "https://localhost", 'https://oauth2')
        self.assertEqual(2, req_count)
        self.assert_auth_basic(history[0], auth_user_name, auth_password)
        self.assert_auth_client_credentials(history[1], "test_token")

    @mock.patch.object(objects.LccnSubscriptionRequest,
                       'vnf_lcm_subscriptions_get')
    def test_send_notification_rety_notification(self,
                                              mock_subscriptions_get):
        self.requests_mock.register_uri('POST',
            "https://localhost/callback",
            headers={
                'Content-Type': 'application/json'},
            status_code=400)

        mock_subscriptions_get.return_value = self._create_subscriptions()
        notification = {
            'vnfInstanceId': 'Test',
            'notificationType': 'VnfIdentifierCreationNotification',
            'links': {}}

        result = self.conductor.send_notification(self.context, notification)

        self.assertEqual(result, 0)
        mock_subscriptions_get.assert_called()

        history = self.requests_mock.request_history
        req_count = nfvo_client._count_mock_history(
            history, "https://localhost")
        self.assertEqual(3, req_count)

    @mock.patch.object(objects.LccnSubscriptionRequest,
                       'vnf_lcm_subscriptions_get')
    def test_sendNotification_sendError(self,
                                        mock_subscriptions_get):
        self.requests_mock.register_uri(
            'POST',
            "https://localhost/callback",
            exc=requests.exceptions.HTTPError("MockException"))

        mock_subscriptions_get.return_value = self._create_subscriptions()
        notification = {
            'vnfInstanceId': 'Test',
            'notificationType': 'VnfIdentifierCreationNotification',
            'links': {}}

        result = self.conductor.send_notification(self.context, notification)

        self.assertEqual(result, 0)
        mock_subscriptions_get.assert_called()

        history = self.requests_mock.request_history
        req_count = nfvo_client._count_mock_history(
            history, "https://localhost")
        self.assertEqual(1, req_count)

    @mock.patch.object(objects.LccnSubscriptionRequest,
                       'vnf_lcm_subscriptions_get')
    def test_send_notification_internal_server_error(
            self, mock_subscriptions_get):
        mock_subscriptions_get.side_effect = Exception("MockException")
        notification = {
            'vnfInstanceId': 'Test',
            'notificationTypes': 'VnfIdentifierCreationNotification',
            'links': {}}

        result = self.conductor.send_notification(self.context, notification)

        self.assertEqual(result, -2)
        mock_subscriptions_get.assert_called()

    @mock.patch.object(conductor_server, 'revert_update_lcm')
    @mock.patch.object(t_context.get_admin_context().session, "add")
    @mock.patch.object(objects.vnf_lcm_op_occs.VnfLcmOpOcc, "save")
    @mock.patch.object(objects.VnfInstance, "update")
    @mock.patch.object(objects.vnf_lcm_op_occs.VnfLcmOpOcc, "create")
    def test_update(self, mock_create, mock_update, mock_save, mock_add,
                    mock_revert):
        mock_create.return_value = "OK"
        mock_update.return_value = datetime.datetime(
            1900, 1, 1, 1, 1, 1, tzinfo=iso8601.UTC)
        mock_add.return_value = "OK"
        mock_save.return_value = "OK"
        vnfd_id = "2c69a161-0000-4b0f-bcf8-391f8fc76600"

        self.conductor.update(
            self.context,
            self.vnf_lcm_opoccs,
            self.body_data,
            self.vnfd_pkg_data,
            vnfd_id)

    @mock.patch.object(conductor_server, 'revert_update_lcm')
    @mock.patch.object(t_context.get_admin_context().session, "add")
    @mock.patch.object(objects.vnf_lcm_op_occs.VnfLcmOpOcc, "save")
    @mock.patch.object(objects.VnfInstance, "update")
    @mock.patch.object(objects.vnf_lcm_op_occs.VnfLcmOpOcc, "create")
    def test_update_lcm_with_vnf_pkg_id(self, mock_create,
                                        mock_update, mock_save,
                                        mock_add, mock_revert):
        mock_create.return_value = "OK"
        mock_update.return_value = datetime.datetime(
            1900, 1, 1, 1, 1, 1, tzinfo=iso8601.UTC)
        mock_add.return_value = "OK"
        mock_save.return_value = "OK"
        vnfd_id = "2c69a161-0000-4b0f-bcf8-391f8fc76600"

        self.conductor.update(
            self.context,
            self.vnf_lcm_opoccs,
            self.body_data,
            self.vnfd_pkg_data,
            vnfd_id)
