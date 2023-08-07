# Copyright (C) 2023 Fujitsu
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
import pickle
import sys
import webob

from tacker.common import exceptions
from tacker.common import rpc
from tacker.sol_refactored.common import http_client
from tacker.sol_refactored.common import vnfd_utils
from tacker.sol_refactored.conductor import conductor_rpc_v2
from tacker.sol_refactored.mgmt_drivers import (
    server_notification as mgmt_driver)
from tacker.sol_refactored import objects
from tacker.tests.unit import base
from tacker.tests.unit.sol_refactored.mgmt_drivers import fakes
from unittest import mock


SAMPLE_VNFD_ID = "16ca1a07-2453-47f1-9f00-7ca2dce0a5ea"


class TestServerNotification(base.TestCase):

    def setUp(self):
        super(TestServerNotification, self).setUp()
        objects.register_all()
        self.vnfd = vnfd_utils.Vnfd(SAMPLE_VNFD_ID)
        self.inst = copy.deepcopy(fakes.fault_notif_inst_example)
        self.csar_dir = None

    @mock.patch.object(http_client.HttpClient, 'do_request')
    @mock.patch.object(rpc, 'init')
    @mock.patch.object(mgmt_driver, 'CONF')
    @mock.patch.object(sys.stdout.buffer, 'write')
    @mock.patch.object(pickle, 'load')
    def test_instantiate_rollback_main(
            self, mock_script, mock_write, mock_conf, mock_init, mock_resp):
        user_script_err_handling_data = {
            'serverNotification': [
                {'serverId': 's0', 'alarmId': 'a0'}]}
        req = objects.InstantiateVnfRequest.from_dict(
            fakes.fault_notif_inst_req_example)
        mock_script.return_value = {
            "operation": "instantiate_rollback_start",
            "request": req,
            "vnf_instance": self.inst,
            "grant_request": None,
            "grant_response": None,
            "tmp_csar_dir": self.csar_dir,
            "user_script_err_handling_data": user_script_err_handling_data
        }
        resp = webob.Response()
        resp.status_code = 202
        mock_resp.return_value = resp, {}
        mgmt_driver.main()
        err_handling_data_expected = {
            'serverNotification': [{'serverId': 's0'}]}
        self.assertEqual(
            err_handling_data_expected, user_script_err_handling_data)

    @mock.patch.object(http_client.HttpClient, 'do_request')
    @mock.patch.object(rpc, 'init')
    @mock.patch.object(mgmt_driver, 'CONF')
    def test_instantiate_end(
            self, mock_conf, mock_init, mock_resp):
        user_script_err_handling_data = {
            'serverNotification': [
                {'serverId': 's0', 'alarmId': 'a0'}]}
        resp = webob.Response()
        resp.status_code = 202
        mock_resp.return_value = resp, {'alarm_id': 'alarm_id'}
        del self.inst['instantiatedVnfInfo']['vnfcResourceInfo'][2]
        del self.inst['instantiatedVnfInfo']['vnfcResourceInfo'][1]
        req = objects.InstantiateVnfRequest.from_dict(
            fakes.fault_notif_inst_req_example)
        server_notification = mgmt_driver.ServerNotificationMgmtDriver(
            req, self.inst, None, None, self.csar_dir,
            user_script_err_handling_data)
        server_notification.instantiate_end()
        err_handling_data_expected = {
            'serverNotification': [
                {'serverId': 's0', 'alarmId': 'a0'},
                {'serverId': 'env-test2', 'alarmId': 'alarm_id'}]}
        self.assertEqual(
            err_handling_data_expected, user_script_err_handling_data)
        self.assertEqual(
            {'alarmId': 'a0'}, self.inst['instantiatedVnfInfo'][
                'vnfcResourceInfo'][0]['metadata']['server_notification'])
        self.assertEqual(
            {'alarmId': 'alarm_id'},
            self.inst['instantiatedVnfInfo']['vnfcResourceInfo'][1][
                'metadata']['server_notification'])

    @mock.patch.object(http_client.HttpClient, 'do_request')
    @mock.patch.object(rpc, 'init')
    @mock.patch.object(mgmt_driver, 'CONF')
    def test_merge_recent_register(
            self, mock_conf, mock_init, mock_resp):
        user_script_err_handling_data = {
            'serverNotification': [
                {'serverId': 's0', 'alarmId': 'a0'},
                {'serverId': 's1', 'alarmId': 'a1'},
                {'serverId': 's2'}, {'serverId': 's3', 'alarmId': 'a3'}]}
        resp = webob.Response()
        resp.status_code = 202
        mock_resp.return_value = resp, {'alarm_id': 'alarm_id'}
        req = objects.InstantiateVnfRequest.from_dict(
            fakes.fault_notif_inst_req_example)
        server_notification = mgmt_driver.ServerNotificationMgmtDriver(
            req, self.inst, None, None, self.csar_dir,
            user_script_err_handling_data)
        server_notification._merge_recent_register()
        err_handling_data_expected = {
            'serverNotification': [
                {'serverId': 's0', 'alarmId': 'a0'},
                {'serverId': 's1', 'alarmId': 'a1'},
                {'serverId': 's2'}]}
        self.assertEqual(
            err_handling_data_expected, user_script_err_handling_data)
        self.assertEqual(
            {'alarmId': 'a0'}, self.inst['instantiatedVnfInfo'][
                'vnfcResourceInfo'][0]['metadata']['server_notification'])
        self.assertEqual(
            {'alarmId': 'a1'}, self.inst['instantiatedVnfInfo'][
                'vnfcResourceInfo'][1]['metadata']['server_notification'])
        self.assertEqual(
            None, self.inst['instantiatedVnfInfo'][
                'vnfcResourceInfo'][2]['metadata'].get('server_notification'))

    @mock.patch.object(http_client.HttpClient, 'do_request')
    @mock.patch.object(rpc, 'init')
    @mock.patch.object(mgmt_driver, 'CONF')
    def test_heal_start(
            self, mock_conf, mock_init, mock_resp):
        user_script_err_handling_data = {
            'serverNotification': [
                {'serverId': 's0', 'alarmId': 'a0'}]}
        resp = webob.Response()
        resp.status_code = 202
        mock_resp.return_value = resp, {'alarm_id': 'alarm_id'}
        del self.inst['instantiatedVnfInfo']['vnfcResourceInfo'][3]
        del self.inst['instantiatedVnfInfo']['vnfcResourceInfo'][2]
        del self.inst['instantiatedVnfInfo']['vnfcResourceInfo'][1]
        req = objects.HealVnfRequest(additionalParams={"all": True})
        grant_req = objects.GrantRequestV1(
            removeResources=[objects.ResourceDefinitionV1(
                type='COMPUTE', resourceTemplateId='VDU1',
                resource=objects.ResourceHandle(
                    resourceId="s0"))])
        grant = objects.GrantV1()
        server_notification = mgmt_driver.ServerNotificationMgmtDriver(
            req, self.inst, grant_req, grant, self.csar_dir,
            user_script_err_handling_data)
        server_notification.heal_start()
        err_handling_data_expected = {
            'serverNotification': [
                {'serverId': 's0'}]}
        self.assertEqual(
            err_handling_data_expected, user_script_err_handling_data)
        self.assertEqual(
            None, self.inst['instantiatedVnfInfo'][
                'vnfcResourceInfo'][0]['metadata'].get('server_notification'))

    @mock.patch.object(http_client.HttpClient, 'do_request')
    @mock.patch.object(rpc, 'init')
    @mock.patch.object(mgmt_driver, 'CONF')
    def test_heal_end(
            self, mock_conf, mock_init, mock_resp):
        user_script_err_handling_data = {
            'serverNotification': [
                {'serverId': 's1', 'alarmId': 'a1'}]}
        resp = webob.Response()
        resp.status_code = 202
        mock_resp.return_value = resp, {'alarm_id': 'alarm_id'}
        del self.inst['instantiatedVnfInfo']['vnfcResourceInfo'][3]
        del self.inst['instantiatedVnfInfo']['vnfcResourceInfo'][2]
        del self.inst['instantiatedVnfInfo']['vnfcResourceInfo'][0]
        req = objects.HealVnfRequest(additionalParams={"all": True})
        grant_req = objects.GrantRequestV1(
            removeResources=[objects.ResourceDefinitionV1(
                type='COMPUTE', resourceTemplateId='VDU1',
                resource=objects.ResourceHandle(
                    resourceId="s1"))])
        grant = objects.GrantV1()
        server_notification = mgmt_driver.ServerNotificationMgmtDriver(
            req, self.inst, grant_req, grant, self.csar_dir,
            user_script_err_handling_data)
        server_notification.heal_end()
        err_handling_data_expected = {
            'serverNotification': [
                {'serverId': 's1', 'alarmId': 'alarm_id'}]}
        self.assertEqual(
            err_handling_data_expected, user_script_err_handling_data)
        self.assertEqual(
            {'alarmId': 'alarm_id'}, self.inst['instantiatedVnfInfo'][
                'vnfcResourceInfo'][0]['metadata'].get('server_notification'))

    @mock.patch.object(http_client.HttpClient, 'do_request')
    @mock.patch.object(rpc, 'init')
    @mock.patch.object(mgmt_driver, 'CONF')
    def test_scale_start(
            self, mock_conf, mock_init, mock_resp):
        user_script_err_handling_data = {
            'serverNotification': [
                {'serverId': 's0', 'alarmId': 'a0'}]}
        resp = webob.Response()
        resp.status_code = 202
        mock_resp.return_value = resp, {'alarm_id': 'alarm_id'}
        del self.inst['instantiatedVnfInfo']['vnfcResourceInfo'][3]
        del self.inst['instantiatedVnfInfo']['vnfcResourceInfo'][2]
        del self.inst['instantiatedVnfInfo']['vnfcResourceInfo'][1]
        req = objects.ScaleVnfRequest(
            type='SCALE_IN', aspectId='aspect_id', numberOfSteps=1)
        grant_req = objects.GrantRequestV1(
            removeResources=[objects.ResourceDefinitionV1(
                type='COMPUTE', resourceTemplateId='VDU1',
                resource=objects.ResourceHandle(
                    resourceId="s0"))])
        grant = objects.GrantV1()
        server_notification = mgmt_driver.ServerNotificationMgmtDriver(
            req, self.inst, grant_req, grant, self.csar_dir,
            user_script_err_handling_data)
        server_notification.scale_start()
        err_handling_data_expected = {
            'serverNotification': [
                {'serverId': 's0'}]}
        self.assertEqual(
            err_handling_data_expected, user_script_err_handling_data)
        self.assertEqual(
            None, self.inst['instantiatedVnfInfo'][
                'vnfcResourceInfo'][0]['metadata'].get('server_notification'))

    @mock.patch.object(http_client.HttpClient, 'do_request')
    @mock.patch.object(rpc, 'init')
    @mock.patch.object(mgmt_driver, 'CONF')
    def test_scale_end(
            self, mock_conf, mock_init, mock_resp):
        user_script_err_handling_data = {
            'serverNotification': [
                {'serverId': 's0', 'alarmId': 'a0'}]}
        resp = webob.Response()
        resp.status_code = 202
        mock_resp.return_value = resp, {'alarm_id': 'alarm_id'}
        del self.inst['instantiatedVnfInfo']['vnfcResourceInfo'][3]
        del self.inst['instantiatedVnfInfo']['vnfcResourceInfo'][2]
        del self.inst['instantiatedVnfInfo']['vnfcResourceInfo'][1]
        req = objects.ScaleVnfRequest(
            type='SCALE_OUT', aspectId='aspect_id', numberOfSteps=1)
        grant_req = objects.GrantRequestV1(
            removeResources=[objects.ResourceDefinitionV1(
                type='COMPUTE', resourceTemplateId='VDU1',
                resource=objects.ResourceHandle(
                    resourceId="s0"))])
        grant = objects.GrantV1()
        server_notification = mgmt_driver.ServerNotificationMgmtDriver(
            req, self.inst, grant_req, grant, self.csar_dir,
            user_script_err_handling_data)
        server_notification.scale_end()
        err_handling_data_expected = {
            'serverNotification': [
                {'serverId': 's0', 'alarmId': 'a0'}]}
        self.assertEqual(
            err_handling_data_expected, user_script_err_handling_data)
        self.assertEqual(
            {'alarmId': 'a0'}, self.inst['instantiatedVnfInfo'][
                'vnfcResourceInfo'][0]['metadata'].get('server_notification'))

    @mock.patch.object(conductor_rpc_v2.VnfLcmRpcApiV2,
                       'server_notification_remove_timer')
    @mock.patch.object(http_client.HttpClient, 'do_request')
    @mock.patch.object(rpc, 'init')
    @mock.patch.object(mgmt_driver, 'CONF')
    def test_terminate_start(
            self, mock_conf, mock_init, mock_resp, mock_timer):
        user_script_err_handling_data = {
            'serverNotification': [
                {'serverId': 's0', 'alarmId': 'a0'}]}
        resp = webob.Response()
        resp.status_code = 202
        mock_resp.return_value = resp, {'alarm_id': 'alarm_id'}
        del self.inst['instantiatedVnfInfo']['vnfcResourceInfo'][3]
        del self.inst['instantiatedVnfInfo']['vnfcResourceInfo'][2]
        del self.inst['instantiatedVnfInfo']['vnfcResourceInfo'][1]
        req = objects.ScaleVnfRequest(
            type='SCALE_OUT', aspectId='aspect_id', numberOfSteps=1)
        grant_req = objects.GrantRequestV1(
            removeResources=[objects.ResourceDefinitionV1(
                type='COMPUTE', resourceTemplateId='VDU1',
                resource=objects.ResourceHandle(
                    resourceId="s0"))])
        grant = objects.GrantV1()
        server_notification = mgmt_driver.ServerNotificationMgmtDriver(
            req, self.inst, grant_req, grant, self.csar_dir,
            user_script_err_handling_data)
        server_notification.terminate_start()
        err_handling_data_expected = {
            'serverNotification': [
                {'serverId': 's0'}]}
        self.assertEqual(
            err_handling_data_expected, user_script_err_handling_data)
        self.assertEqual(
            None, self.inst['instantiatedVnfInfo'][
                'vnfcResourceInfo'][0]['metadata'].get('server_notification'))

    @mock.patch.object(http_client.HttpClient, 'do_request')
    @mock.patch.object(rpc, 'init')
    @mock.patch.object(mgmt_driver, 'CONF')
    def test_scale_rollback_start(
            self, mock_conf, mock_init, mock_resp):
        user_script_err_handling_data = {
            'serverNotification': [
                {'serverId': 's0', 'alarmId': 'a0'}]}
        resp = webob.Response()
        resp.status_code = 202
        mock_resp.return_value = resp, {'alarm_id': 'alarm_id'}
        del self.inst['instantiatedVnfInfo']['vnfcResourceInfo'][3]
        del self.inst['instantiatedVnfInfo']['vnfcResourceInfo'][2]
        del self.inst['instantiatedVnfInfo']['vnfcResourceInfo'][1]
        req = objects.ScaleVnfRequest(
            type='SCALE_OUT', aspectId='aspect_id', numberOfSteps=1)
        grant_req = objects.GrantRequestV1(
            removeResources=[objects.ResourceDefinitionV1(
                type='COMPUTE', resourceTemplateId='VDU1',
                resource=objects.ResourceHandle(
                    resourceId="s0"))])
        grant = objects.GrantV1()
        server_notification = mgmt_driver.ServerNotificationMgmtDriver(
            req, self.inst, grant_req, grant, self.csar_dir,
            user_script_err_handling_data)
        server_notification.scale_rollback_start()
        err_handling_data_expected = {
            'serverNotification': [
                {'serverId': 's0'}]}
        self.assertEqual(
            err_handling_data_expected, user_script_err_handling_data)
        self.assertEqual(
            {'alarmId': 'xxx'}, self.inst['instantiatedVnfInfo'][
                'vnfcResourceInfo'][0]['metadata'].get('server_notification'))

    @mock.patch.object(sys.stdout.buffer, 'write')
    @mock.patch.object(http_client.HttpClient, 'do_request')
    @mock.patch.object(rpc, 'init')
    @mock.patch.object(mgmt_driver, 'CONF')
    @mock.patch.object(pickle, 'load')
    def test_heal_end_main_error(
            self, mock_script, mock_conf, mock_init, mock_resp, mock_write):
        user_script_err_handling_data = None
        resp = webob.Response()
        resp.status_code = 400
        mock_resp.return_value = resp, None
        req = objects.HealVnfRequest(additionalParams={"all": True})
        grant_req = objects.GrantRequestV1(
            removeResources=[objects.ResourceDefinitionV1(
                type='COMPUTE', resourceTemplateId='VDU1',
                resource=objects.ResourceHandle(
                    resourceId="s1"))])
        grant = objects.GrantV1()
        mock_script.return_value = {
            "operation": "heal_end",
            "request": req,
            "vnf_instance": self.inst,
            "grant_request": grant_req,
            "grant_response": grant,
            "tmp_csar_dir": self.csar_dir,
            "user_script_err_handling_data": user_script_err_handling_data
        }
        self.assertRaises(
            exceptions.MgmtDriverOtherError, mgmt_driver.main)

    @mock.patch.object(sys.stdout.buffer, 'write')
    @mock.patch.object(rpc, 'init')
    @mock.patch.object(mgmt_driver, 'CONF')
    @mock.patch.object(pickle, 'load')
    def test_instantiate_start(
            self, mock_script, mock_conf, mock_init, mock_write):
        user_script_err_handling_data = None
        mock_script.return_value = {
            "operation": "instantiate_start",
            "request": None,
            "vnf_instance": self.inst,
            "grant_request": None,
            "grant_response": None,
            "tmp_csar_dir": self.csar_dir,
            "user_script_err_handling_data": user_script_err_handling_data
        }
        mgmt_driver.main()
        self.assertEqual(None, user_script_err_handling_data)

    @mock.patch.object(sys.stdout.buffer, 'write')
    @mock.patch.object(rpc, 'init')
    @mock.patch.object(mgmt_driver, 'CONF')
    @mock.patch.object(pickle, 'load')
    def test_terminate_end(
            self, mock_script, mock_conf, mock_init, mock_write):
        user_script_err_handling_data = None
        mock_script.return_value = {
            "operation": "terminate_end",
            "request": None,
            "vnf_instance": self.inst,
            "grant_request": None,
            "grant_response": None,
            "tmp_csar_dir": self.csar_dir,
            "user_script_err_handling_data": user_script_err_handling_data
        }
        mgmt_driver.main()
        self.assertEqual(None, user_script_err_handling_data)

    @mock.patch.object(sys.stdout.buffer, 'write')
    @mock.patch.object(rpc, 'init')
    @mock.patch.object(mgmt_driver, 'CONF')
    @mock.patch.object(pickle, 'load')
    def test_scale_end_type(
            self, mock_script, mock_conf, mock_init, mock_write):
        user_script_err_handling_data = None
        req = objects.ScaleVnfRequest(
            type='SCALE_IN', aspectId='aspect_id', numberOfSteps=1)
        mock_script.return_value = {
            "operation": "scale_end",
            "request": req,
            "vnf_instance": self.inst,
            "grant_request": None,
            "grant_response": None,
            "tmp_csar_dir": self.csar_dir,
            "user_script_err_handling_data": user_script_err_handling_data
        }
        mgmt_driver.main()
        self.assertEqual(None, user_script_err_handling_data)

    @mock.patch.object(sys.stdout.buffer, 'write')
    @mock.patch.object(rpc, 'init')
    @mock.patch.object(mgmt_driver, 'CONF')
    @mock.patch.object(pickle, 'load')
    def test_scale_start_type(
            self, mock_script, mock_conf, mock_init, mock_write):
        user_script_err_handling_data = None
        req = objects.ScaleVnfRequest(
            type='SCALE_OUT', aspectId='aspect_id', numberOfSteps=1)
        mock_script.return_value = {
            "operation": "scale_start",
            "request": req,
            "vnf_instance": self.inst,
            "grant_request": None,
            "grant_response": None,
            "tmp_csar_dir": self.csar_dir,
            "user_script_err_handling_data": user_script_err_handling_data
        }
        mgmt_driver.main()
        self.assertEqual(None, user_script_err_handling_data)

    @mock.patch.object(http_client.HttpClient, 'do_request')
    @mock.patch.object(rpc, 'init')
    @mock.patch.object(mgmt_driver, 'CONF')
    def test_instantiate_end_no_metadata(
            self, mock_conf, mock_init, mock_resp):
        user_script_err_handling_data = {
            'serverNotification': [
                {'serverId': 's0', 'alarmId': 'a0'}]}
        resp = webob.Response()
        resp.status_code = 202
        mock_resp.return_value = resp, {'alarm_id': 'alarm_id'}
        del self.inst['instantiatedVnfInfo']['vnfcResourceInfo'][2]
        del self.inst['instantiatedVnfInfo']['vnfcResourceInfo'][1]
        del self.inst['instantiatedVnfInfo']['metadata']
        req = objects.InstantiateVnfRequest.from_dict(
            fakes.fault_notif_inst_req_example)
        server_notification = mgmt_driver.ServerNotificationMgmtDriver(
            req, self.inst, None, None, self.csar_dir,
            user_script_err_handling_data)
        server_notification.instantiate_end()
        err_handling_data_expected = {
            'serverNotification': [
                {'serverId': 's0', 'alarmId': 'a0'},
                {'serverId': 'env-test2', 'alarmId': 'alarm_id'}]}
        self.assertEqual(
            err_handling_data_expected, user_script_err_handling_data)
        self.assertEqual(
            {'alarmId': 'a0'}, self.inst['instantiatedVnfInfo'][
                'vnfcResourceInfo'][0]['metadata']['server_notification'])
        self.assertEqual(
            {'alarmId': 'alarm_id'},
            self.inst['instantiatedVnfInfo']['vnfcResourceInfo'][1][
                'metadata']['server_notification'])

    @mock.patch.object(rpc, 'init')
    @mock.patch.object(mgmt_driver, 'CONF')
    def test_get_params_none(self, mock_conf, mock_init):
        user_script_err_handling_data = {
            'serverNotification': [
                {'serverId': 's0', 'alarmId': 'a0'},
                {'serverId': 's1', 'alarmId': 'a1'},
                {'serverId': 's2'}, {'serverId': 's3', 'alarmId': 'a3'}]}
        req = objects.InstantiateVnfRequest.from_dict(
            fakes.fault_notif_inst_req_example)
        server_notification = mgmt_driver.ServerNotificationMgmtDriver(
            req, self.inst, None, None, self.csar_dir,
            user_script_err_handling_data)

        del self.inst['vimConnectionInfo']
        result1 = server_notification.get_params()
        self.assertEqual((None, None, None), result1)

        del self.inst['instantiatedVnfInfo']
        result2 = server_notification.get_params()
        self.assertEqual((None, None, None), result2)

    @mock.patch.object(http_client.HttpClient, 'do_request')
    @mock.patch.object(rpc, 'init')
    @mock.patch.object(mgmt_driver, 'CONF')
    def test_request_register_no_server_notification(
            self, mock_conf, mock_init, mock_resp):
        vnfc_resource = {'computeResource': {'resourceId': 's0'}}
        user_script_err_handling_data = {}
        req = objects.InstantiateVnfRequest.from_dict(
            fakes.fault_notif_inst_req_example)
        resp = webob.Response()
        resp.status_code = 202
        mock_resp.return_value = resp, {'alarm_id': 'alarm_id'}
        server_notification = mgmt_driver.ServerNotificationMgmtDriver(
            req, self.inst, None, None, self.csar_dir,
            user_script_err_handling_data)
        server_notification._request_register(vnfc_resource)
        err_handling_data_expected = {
            'serverNotification': [
                {'serverId': 's0', 'alarmId': 'alarm_id'}]}
        self.assertEqual(
            err_handling_data_expected, user_script_err_handling_data)

    @mock.patch.object(mgmt_driver.ServerNotificationMgmtDriver,
                       '_request_unregister')
    @mock.patch.object(mgmt_driver.ServerNotificationMgmtDriver, 'get_params')
    @mock.patch.object(rpc, 'init')
    @mock.patch.object(mgmt_driver, 'CONF')
    def test_request_register_cancel(
            self, mock_conf, mock_init, mock_params, mock_unregister):
        rsc_list = [{
            'computeResource': {'resourceId': 's0'},
            'metadata': {'server_notification': {'alarmId': 'a0'}}}]
        mock_params.return_value = (None, None, None)
        user_script_err_handling_data = {}
        req = objects.InstantiateVnfRequest.from_dict(
            fakes.fault_notif_inst_req_example)
        server_notification = mgmt_driver.ServerNotificationMgmtDriver(
            req, self.inst, None, None, self.csar_dir,
            user_script_err_handling_data)
        server_notification.request_register_cancel(rsc_list)
        self.assertEqual(1, mock_unregister.call_count)

    @mock.patch.object(http_client.HttpClient, 'do_request')
    @mock.patch.object(rpc, 'init')
    @mock.patch.object(mgmt_driver, 'CONF')
    def test_request_unregister_400(
            self, mock_conf, mock_init, mock_resp):
        user_script_err_handling_data = {}
        req = objects.InstantiateVnfRequest.from_dict(
            fakes.fault_notif_inst_req_example)
        resp = webob.Response()
        resp.status_code = 400
        mock_resp.return_value = resp, {'alarm_id': 'alarm_id'}
        server_notification = mgmt_driver.ServerNotificationMgmtDriver(
            req, self.inst, None, None, self.csar_dir,
            user_script_err_handling_data)
        server_notification._request_unregister('', '', 's0', '')
        self.assertEqual(1, mock_resp.call_count)

    @mock.patch.object(http_client.HttpClient, 'do_request')
    @mock.patch.object(rpc, 'init')
    @mock.patch.object(mgmt_driver, 'CONF')
    def test_request_unregister_no_server_notification(
            self, mock_conf, mock_init, mock_resp):
        user_script_err_handling_data = {}
        req = objects.InstantiateVnfRequest.from_dict(
            fakes.fault_notif_inst_req_example)
        resp = webob.Response()
        resp.status_code = 200
        mock_resp.return_value = resp, {'alarm_id': 'alarm_id'}
        server_notification = mgmt_driver.ServerNotificationMgmtDriver(
            req, self.inst, None, None, self.csar_dir,
            user_script_err_handling_data)
        server_notification._request_unregister('', '', 's0', '')
        self.assertEqual(
            {'serverNotification': [{'serverId': 's0'}]},
            user_script_err_handling_data)
