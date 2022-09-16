# Copyright (C) 2022 FUJITSU
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
import requests
from unittest import mock

from oslo_utils import uuidutils

from tacker import context
from tacker.sol_refactored.api import api_version
from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.common import http_client
from tacker.sol_refactored.common import subscription_utils as subsc_utils
from tacker.sol_refactored import objects
from tacker.tests import base


class TestSubscriptionUtils(base.BaseTestCase):

    def setUp(self):
        super(TestSubscriptionUtils, self).setUp()
        objects.register_all()
        self.context = context.get_admin_context()
        self.context.api_version = api_version.APIVersion('2.0.0')

    @mock.patch.object(objects.base.TackerPersistentObject, 'get_by_id')
    def test_get_subsc(self, mock_subsc):
        mock_subsc.return_value = objects.LccnSubscriptionV2(id='subsc-1')

        result = subsc_utils.get_subsc(context, 'subsc-1')
        self.assertEqual('subsc-1', result.id)

    @mock.patch.object(objects.base.TackerPersistentObject, 'get_by_id')
    def test_get_subsc_error(self, mock_subsc):
        mock_subsc.return_value = None
        self.assertRaises(
            sol_ex.LccnSubscriptionNotFound,
            subsc_utils.get_subsc, context, 'subsc-1')

    @mock.patch.object(objects.base.TackerPersistentObject, 'get_all')
    def test_get_subsc_all(self, mock_subsc):
        mock_subsc.return_value = [objects.LccnSubscriptionV2(id='subsc-1')]

        result = subsc_utils.get_subsc_all(context)
        self.assertEqual('subsc-1', result[0].id)

    @mock.patch.object(http_client.HttpClient, 'do_request')
    def test_send_notification(self, mock_resp):
        subsc_no_auth = objects.LccnSubscriptionV2(
            id='sub-1', verbosity='SHORT',
            callbackUri='http://127.0.0.1/callback')
        notif_data_no_auth = objects.VnfLcmOperationOccurrenceNotificationV2(
            id=uuidutils.generate_uuid()
        )
        resp_no_auth = requests.Response()
        resp_no_auth.status_code = 204
        mock_resp.return_value = (resp_no_auth, None)

        # execute no_auth
        subsc_utils.send_notification(subsc_no_auth, notif_data_no_auth)

        subsc_basic_auth = objects.LccnSubscriptionV2(
            id='sub-2', verbosity='SHORT',
            callbackUri='http://127.0.0.1/callback',
            authentication=objects.SubscriptionAuthentication(
                paramsBasic=objects.SubscriptionAuthentication_ParamsBasic(
                    userName='test', password='test')))

        # execute basic_auth
        subsc_utils.send_notification(subsc_basic_auth, notif_data_no_auth)

        subsc_oauth2 = objects.LccnSubscriptionV2(
            id='sub-3', verbosity='SHORT',
            callbackUri='http://127.0.0.1/callback',
            authentication=objects.SubscriptionAuthentication(
                paramsOauth2ClientCredentials=(
                    objects.SubscriptionAuthentication_ParamsOauth2(
                        clientId='test', clientPassword='test',
                        tokenEndpoint='http://127.0.0.1/token'))))

        # execute oauth2
        subsc_utils.send_notification(subsc_oauth2, notif_data_no_auth)

    @mock.patch.object(http_client.HttpClient, 'do_request')
    def test_send_notification_error_code(self, mock_resp):
        subsc_no_auth = objects.LccnSubscriptionV2(
            id='sub-1', verbosity='SHORT',
            callbackUri='http://127.0.0.1/callback')
        notif_data_no_auth = objects.VnfLcmOperationOccurrenceNotificationV2(
            id=uuidutils.generate_uuid()
        )
        resp_no_auth = requests.Response()
        resp_no_auth.status_code = 200
        mock_resp.return_value = (resp_no_auth, None)

        # execute no_auth
        subsc_utils.send_notification(subsc_no_auth, notif_data_no_auth)

    @mock.patch.object(http_client.HttpClient, 'do_request')
    def test_send_notification_error(self, mock_resp):
        subsc_no_auth = objects.LccnSubscriptionV2(
            id='sub-1', verbosity='SHORT',
            callbackUri='http://127.0.0.1/callback')
        notif_data_no_auth = objects.VnfLcmOperationOccurrenceNotificationV2(
            id=uuidutils.generate_uuid()
        )
        resp_no_auth = Exception()
        mock_resp.return_value = (resp_no_auth, None)

        # execute no_auth
        subsc_utils.send_notification(subsc_no_auth, notif_data_no_auth)

    @mock.patch.object(http_client.HttpClient, 'do_request')
    def test_test_notification(self, mock_resp):
        subsc_no_auth = objects.LccnSubscriptionV2(
            id='sub-1', verbosity='SHORT',
            callbackUri='http://127.0.0.1/callback')

        resp_no_auth = requests.Response()
        resp_no_auth.status_code = 204
        mock_resp.return_value = (resp_no_auth, None)

        # execute no_auth
        subsc_utils.test_notification(subsc_no_auth)

    @mock.patch.object(http_client.HttpClient, 'do_request')
    def test_test_notification_error_code(self, mock_resp):
        subsc_no_auth = objects.LccnSubscriptionV2(
            id='sub-1', verbosity='SHORT',
            callbackUri='http://127.0.0.1/callback')
        resp_no_auth = requests.Response()
        resp_no_auth.status_code = 200
        mock_resp.return_value = (resp_no_auth, None)

        # execute no_auth
        self.assertRaises(sol_ex.TestNotificationFailed,
                          subsc_utils.test_notification, subsc_no_auth)

    class mock_session():

        def request(url, method, raise_exc=False, **kwargs):
            resp = requests.Response()
            resp.status_code = 400
            resp.headers['Content-Type'] = 'application/zip'
            return resp

    @mock.patch.object(http_client.HttpClient, '_decode_body')
    @mock.patch.object(http_client.NoAuthHandle, 'get_session')
    def test_test_notification_error(self, mock_session, mock_decode_body):
        subsc_no_auth = objects.LccnSubscriptionV2(
            id='sub-1', verbosity='SHORT',
            callbackUri='http://127.0.0.1/callback')
        mock_session.return_value = self.mock_session
        mock_decode_body.return_value = None

        self.assertRaises(sol_ex.TestNotificationFailed,
                          subsc_utils.test_notification, subsc_no_auth)

    def test_match_version(self):
        inst = objects.VnfInstanceV2(
            id='test-instance', vnfSoftwareVersion='1.1.1', vnfdVersion='1.2')
        version_mismatch = (
            objects._VnfProductsFromProviders_VnfProducts_Versions(
                vnfSoftwareVersion='1.1.2'))
        result_1 = subsc_utils.match_version(version_mismatch, inst)
        self.assertEqual(False, result_1)

        version_match = (
            objects._VnfProductsFromProviders_VnfProducts_Versions(
                vnfSoftwareVersion='1.1.1'))
        result_2 = subsc_utils.match_version(version_match, inst)
        self.assertEqual(True, result_2)

        version_vnfd = (
            objects._VnfProductsFromProviders_VnfProducts_Versions(
                vnfSoftwareVersion='1.1.1', vnfdVersions=['1.2']))
        result_3 = subsc_utils.match_version(version_vnfd, inst)
        self.assertEqual(True, result_3)

    def test_match_products_per_provider(self):
        inst = objects.VnfInstanceV2(
            id='test-instance', vnfProvider='company',
            vnfSoftwareVersion='1.1.1', vnfdVersion='1.2',
            vnfProductName='test')
        products_mismatch = objects._VnfProductsFromProviders(
            vnfProvider='test')
        result_1 = subsc_utils.match_products_per_provider(
            products_mismatch, inst)
        self.assertEqual(False, result_1)

        products_vnfproducts_no_exist = objects._VnfProductsFromProviders(
            vnfProvider='company')
        result_2 = subsc_utils.match_products_per_provider(
            products_vnfproducts_no_exist, inst)
        self.assertEqual(True, result_2)

        products_vnf_mismatch = objects._VnfProductsFromProviders(
            vnfProvider='company', vnfProducts=[
                objects._VnfProductsFromProviders_VnfProducts(
                    vnfProductName='error'),
                objects._VnfProductsFromProviders_VnfProducts(
                    vnfProductName='test', versions=[
                        objects._VnfProductsFromProviders_VnfProducts_Versions(
                            vnfSoftwareVersion='1.1.2'
                        )])
            ])
        result_3 = subsc_utils.match_products_per_provider(
            products_vnf_mismatch, inst)
        self.assertEqual(False, result_3)

        products_vnf_match_with_no_versions = (
            objects._VnfProductsFromProviders(
                vnfProvider='company', vnfProducts=[
                    objects._VnfProductsFromProviders_VnfProducts(
                        vnfProductName='test')]))

        result_4 = subsc_utils.match_products_per_provider(
            products_vnf_match_with_no_versions, inst)
        self.assertEqual(True, result_4)

        products_vnf_match_with_versions = objects._VnfProductsFromProviders(
            vnfProvider='company', vnfProducts=[
                objects._VnfProductsFromProviders_VnfProducts(
                    vnfProductName='test', versions=[
                        objects._VnfProductsFromProviders_VnfProducts_Versions(
                            vnfSoftwareVersion='1.1.1'
                        )])
            ])

        result_5 = subsc_utils.match_products_per_provider(
            products_vnf_match_with_versions, inst)
        self.assertEqual(True, result_5)

    def test_match_inst_subsc_filter(self):
        inst = objects.VnfInstanceV2(
            id='test-instance', vnfProvider='company',
            vnfSoftwareVersion='1.1.1', vnfdVersion='1.2',
            vnfProductName='test', vnfdId='vnfdid-1',
            vnfInstanceName='test')
        inst_filter_mismatch_vnfdid = objects.VnfInstanceSubscriptionFilter(
            vnfdIds=['error'])
        result_1 = subsc_utils.match_inst_subsc_filter(
            inst_filter_mismatch_vnfdid, inst)
        self.assertEqual(False, result_1)

        products_vnfproducts_no_exist = objects._VnfProductsFromProviders(
            vnfProvider='company')
        inst_filter_match_products = objects.VnfInstanceSubscriptionFilter(
            vnfProductsFromProviders=[products_vnfproducts_no_exist])
        result_2 = subsc_utils.match_inst_subsc_filter(
            inst_filter_match_products, inst)
        self.assertEqual(True, result_2)

        products_mismatch = objects._VnfProductsFromProviders(
            vnfProvider='test')
        inst_filter_mismatch_products = objects.VnfInstanceSubscriptionFilter(
            vnfProductsFromProviders=[products_mismatch])
        result_3 = subsc_utils.match_inst_subsc_filter(
            inst_filter_mismatch_products, inst)
        self.assertEqual(False, result_3)

        inst_filter_mismatch_inst_id = objects.VnfInstanceSubscriptionFilter(
            vnfInstanceIds=['instanceid-2'])
        result_4 = subsc_utils.match_inst_subsc_filter(
            inst_filter_mismatch_inst_id, inst)
        self.assertEqual(False, result_4)

        inst_filter_mismatch_inst_name = objects.VnfInstanceSubscriptionFilter(
            vnfInstanceNames=['instance_name-2'])
        result_5 = subsc_utils.match_inst_subsc_filter(
            inst_filter_mismatch_inst_name, inst)
        self.assertEqual(False, result_5)

    @mock.patch.object(objects.base.TackerPersistentObject, 'get_all')
    def test_get_inst_create_subscs(self, mock_subscs):
        inst = objects.VnfInstanceV2(id='test-instance')
        mock_subscs.return_value = [objects.LccnSubscriptionV2(id='subsc-1')]
        result = subsc_utils.get_inst_create_subscs(context, inst)

        self.assertEqual('subsc-1', result[0].id)

    @mock.patch.object(objects.base.TackerPersistentObject, 'get_all')
    def test_get_inst_delete_subscs(self, mock_subscs):
        inst = objects.VnfInstanceV2(id='test-instance')
        mock_subscs.return_value = [objects.LccnSubscriptionV2(id='subsc-1')]
        result = subsc_utils.get_inst_delete_subscs(context, inst)

        self.assertEqual('subsc-1', result[0].id)

    @mock.patch.object(objects.base.TackerPersistentObject, 'get_all')
    def test_get_lcmocc_subscs(self, mock_subscs):
        inst = objects.VnfInstanceV2(id='test-instance')
        lcmocc = objects.VnfLcmOpOccV2(operationState='COMPLETED',
                                       operation='INSTANTIATE')
        mock_subscs.return_value = [objects.LccnSubscriptionV2(id='subsc-1')]
        result = subsc_utils.get_lcmocc_subscs(context, lcmocc, inst)

        self.assertEqual('subsc-1', result[0].id)

    @mock.patch.object(objects.base.TackerPersistentObject, 'get_all')
    def test_get_matched_subscs(self, mock_subscs):
        inst = objects.VnfInstanceV2(id='test-instance', vnfProvider='company')
        notif_type = 'VnfLcmOperationOccurrenceNotification'
        op_type = 'INSTANTIATE'
        op_status = 'COMPLETED'

        subscs_no_fileter = objects.LccnSubscriptionV2(id='subsc-1')

        products_vnfproducts_no_exist = objects._VnfProductsFromProviders(
            vnfProvider='company')
        inst_filter_match_products = objects.VnfInstanceSubscriptionFilter(
            vnfProductsFromProviders=[products_vnfproducts_no_exist])
        subscs_filter_match = objects.LccnSubscriptionV2(
            id='subsc-2',
            filter=objects.LifecycleChangeNotificationsFilterV2(
                vnfInstanceSubscriptionFilter=inst_filter_match_products))

        products_mismatch = objects._VnfProductsFromProviders(
            vnfProvider='test')
        inst_filter_mismatch_products = objects.VnfInstanceSubscriptionFilter(
            vnfProductsFromProviders=[products_mismatch])
        subscs_filter_mismatch = objects.LccnSubscriptionV2(
            id='subsc-3',
            filter=objects.LifecycleChangeNotificationsFilterV2(
                vnfInstanceSubscriptionFilter=inst_filter_mismatch_products))

        subscs_noti_type_match = objects.LccnSubscriptionV2(
            id='subsc-4', filter=objects.LifecycleChangeNotificationsFilterV2(
                notificationTypes=['VnfLcmOperationOccurrenceNotification']))
        subscs_noti_type_mismatch = objects.LccnSubscriptionV2(
            id='subsc-5', filter=objects.LifecycleChangeNotificationsFilterV2(
                notificationTypes=['VnfIdentifierCreationNotification']))

        subscs_op_type_match = objects.LccnSubscriptionV2(
            id='subsc-6', filter=objects.LifecycleChangeNotificationsFilterV2(
                operationTypes=['INSTANTIATE']))
        subscs_op_type_mismatch = objects.LccnSubscriptionV2(
            id='subsc-7', filter=objects.LifecycleChangeNotificationsFilterV2(
                operationTypes=['TERMINATE']))

        subscs_op_status_match = objects.LccnSubscriptionV2(
            id='subsc-8', filter=objects.LifecycleChangeNotificationsFilterV2(
                operationStatus=['COMPLETED']))
        subscs_op_status_mismatch = objects.LccnSubscriptionV2(
            id='subsc-9', filter=objects.LifecycleChangeNotificationsFilterV2(
                operationStatus=['FAILED_TEMP']))

        mock_subscs.return_value = [
            subscs_no_fileter, subscs_filter_match, subscs_filter_mismatch,
            subscs_noti_type_match, subscs_noti_type_mismatch,
            subscs_op_type_match, subscs_op_type_mismatch,
            subscs_op_status_match, subscs_op_status_mismatch]

        result = subsc_utils.get_matched_subscs(
            context, inst, notif_type, op_type, op_status)

        expected_ids = ['subsc-1', 'subsc-2', 'subsc-4', 'subsc-6', 'subsc-8']

        result_ids = [sub.id for sub in result]
        self.assertEqual(expected_ids, result_ids)

    def test_make_create_inst_notif_data(self):
        subsc = objects.LccnSubscriptionV2(id='subsc-1')
        inst = objects.VnfInstanceV2(id='test-instance')
        endpoint = 'http://127.0.0.1:9890'

        result = subsc_utils.make_create_inst_notif_data(subsc, inst, endpoint)

        self.assertEqual('subsc-1', result.subscriptionId)
        self.assertEqual('test-instance', result.vnfInstanceId)

    def test_make_delete_inst_notif_data(self):
        subsc = objects.LccnSubscriptionV2(id='subsc-1')
        inst = objects.VnfInstanceV2(id='test-instance')
        endpoint = 'http://127.0.0.1:9890'

        result = subsc_utils.make_delete_inst_notif_data(subsc, inst, endpoint)

        self.assertEqual('subsc-1', result.subscriptionId)
        self.assertEqual('test-instance', result.vnfInstanceId)
