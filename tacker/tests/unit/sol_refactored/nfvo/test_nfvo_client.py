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
import os
import requests
from unittest import mock
import zipfile

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import uuidutils

from tacker import context
from tacker.sol_refactored.api import api_version
from tacker.sol_refactored.common import config
from tacker.sol_refactored.common import http_client
from tacker.sol_refactored.common import pm_job_utils
from tacker.sol_refactored.common import subscription_utils as subsc_utils
from tacker.sol_refactored.common import vnfd_utils
from tacker.sol_refactored.nfvo import local_nfvo
from tacker.sol_refactored.nfvo import nfvo_client
from tacker.sol_refactored import objects
from tacker.tests import base

CONF = config.CONF

SAMPLE_VNFD_ID = "b1bb0ce7-ebca-4fa7-95ed-4840d7000000"
_vnfpkg_body_example = {
    "id": uuidutils.generate_uuid(),
    "vnfdId": SAMPLE_VNFD_ID,
    "vnfProvider": "Company",
    "vnfProductName": "Sample VNF",
    "vnfSoftwareVersion": "1.0",
    "vnfdVersion": "1.0",
    "onboardingState": "ONBOARDED",
    "operationalState": "ENABLED",
    "usageState": "NOT_IN_USE"
}
_grant_res = {
    'id': 'b94d05c9-eb45-4855-9132-20e1d3e7cecf',
    'vnfInstanceId': '2d004394-d0f0-406d-845a-2b148f91039a',
    'vnfLcmOpOccId': '34da9ba7-6ab1-4d8d-a68a-68892e56642c',
    'zones': [{
        'id': 'b4eba78c-e957-4e66-8bd7-14822f954413',
        'zoneId': 'nova'
    }],
    'addResources': [{
        'resourceDefinitionId': '6396a2a1-7e36-49bd-8fff-2d46394a6b29',
        'zoneId': 'b4eba78c-e957-4e66-8bd7-14822f954413'
    }, {
        'resourceDefinitionId': 'VDU1_CP1-6396a2a1-7e36-49bd-8fff-2d46394a6b29'
    }, {
        'resourceDefinitionId': 'VDU1_CP2-6396a2a1-7e36-49bd-8fff-2d46394a6b29'
    }, {
        'resourceDefinitionId': 'VDU1_CP3-6396a2a1-7e36-49bd-8fff-2d46394a6b29'
    }, {
        'resourceDefinitionId': 'VDU1_CP5-6396a2a1-7e36-49bd-8fff-2d46394a6b29'
    }, {
        'resourceDefinitionId': 'VDU1_CP4-6396a2a1-7e36-49bd-8fff-2d46394a6b29'
    }, {
        'resourceDefinitionId': 'VirtualStorage-6396a2a1-7e36-'
                                '49bd-8fff-2d46394a6b29'
    }, {
        'resourceDefinitionId': '39e0af93-aba5-4a15-9231-cdaa4149738e',
        'zoneId': 'b4eba78c-e957-4e66-8bd7-14822f954413'
    }, {
        'resourceDefinitionId': 'VDU1_CP1-39e0af93-aba5-4a15-9231-cdaa4149738e'
    }, {
        'resourceDefinitionId': 'VDU1_CP2-39e0af93-aba5-4a15-9231-cdaa4149738e'
    }, {
        'resourceDefinitionId': 'VDU1_CP3-39e0af93-aba5-4a15-9231-cdaa4149738e'
    }, {
        'resourceDefinitionId': 'VDU1_CP5-39e0af93-aba5-4a15-9231-cdaa4149738e'
    }, {
        'resourceDefinitionId': 'VDU1_CP4-39e0af93-aba5-4a15-9231-cdaa4149738e'
    }, {
        'resourceDefinitionId': 'VirtualStorage-39e0af93-aba5-'
                                '4a15-9231-cdaa4149738e'
    }, {
        'resourceDefinitionId': '8a3ab83f-187c-4feb-b1b5-a6bf587130fa',
        'zoneId': 'b4eba78c-e957-4e66-8bd7-14822f954413'
    }, {
        'resourceDefinitionId': 'VDU1_CP1-8a3ab83f-187c-4feb-b1b5-a6bf587130fa'
    }, {
        'resourceDefinitionId': 'VDU1_CP2-8a3ab83f-187c-4feb-b1b5-a6bf587130fa'
    }, {
        'resourceDefinitionId': 'VDU1_CP3-8a3ab83f-187c-4feb-b1b5-a6bf587130fa'
    }, {
        'resourceDefinitionId': 'VDU1_CP5-8a3ab83f-187c-4feb-b1b5-a6bf587130fa'
    }, {
        'resourceDefinitionId': 'VDU1_CP4-8a3ab83f-187c-4feb-b1b5-a6bf587130fa'
    }, {
        'resourceDefinitionId': 'VirtualStorage-8a3ab83f-187c-'
                                '4feb-b1b5-a6bf587130fa'
    }, {
        'resourceDefinitionId': '3f2385fa-3f13-436d-b93a-47c62ef237e0',
        'zoneId': 'b4eba78c-e957-4e66-8bd7-14822f954413'
    }, {
        'resourceDefinitionId': 'VDU2_CP5-3f2385fa-3f13-436d-b93a-47c62ef237e0'
    }, {
        'resourceDefinitionId': 'VDU2_CP2-3f2385fa-3f13-436d-b93a-47c62ef237e0'
    }, {
        'resourceDefinitionId': 'VDU2_CP1-3f2385fa-3f13-436d-b93a-47c62ef237e0'
    }, {
        'resourceDefinitionId': 'VDU2_CP3-3f2385fa-3f13-436d-b93a-47c62ef237e0'
    }, {
        'resourceDefinitionId': 'VDU2_CP4-3f2385fa-3f13-436d-b93a-47c62ef237e0'
    }, {
        'resourceDefinitionId': 'a411a968-c00b-4d46-8553-a37f3537391e'
    }, {
        'resourceDefinitionId': 'f06ba7cf-f5af-4856-8d3a-56b331d1b9a5'
    }],
    'vimAssets': {
        'softwareImages': [{
            'vnfdSoftwareImageId': 'VDU2',
            'vimSoftwareImageId': '44fd5841-ce98-4d54-a828-6ef51f941c8a'
        }, {
            'vnfdSoftwareImageId': 'VirtualStorage',
            'vimSoftwareImageId': 'image-1.0.0-x86_64-disk'
        }]
    }
}
_inst_grant_req_example = {
    "vnfInstanceId": "2d004394-d0f0-406d-845a-2b148f91039a",
    "vnfLcmOpOccId": "34da9ba7-6ab1-4d8d-a68a-68892e56642c",
    "vnfdId": "b1bb0ce7-ebca-4fa7-95ed-4840d7000000",
    "flavourId": "simple",
    "operation": "INSTANTIATE",
    "isAutomaticInvocation": False,
    "instantiationLevelId": "instantiation_level_2",
    "addResources": [{
        "id": "6396a2a1-7e36-49bd-8fff-2d46394a6b29",
        "type": "COMPUTE",
        "resourceTemplateId": "VDU1"
    }, {
        "id": "VDU1_CP1-6396a2a1-7e36-49bd-8fff-2d46394a6b29",
        "type": "LINKPORT",
        "resourceTemplateId": "VDU1_CP1"
    }, {
        "id": "VDU1_CP2-6396a2a1-7e36-49bd-8fff-2d46394a6b29",
        "type": "LINKPORT",
        "resourceTemplateId": "VDU1_CP2"
    }, {
        "id": "VDU1_CP3-6396a2a1-7e36-49bd-8fff-2d46394a6b29",
        "type": "LINKPORT",
        "resourceTemplateId": "VDU1_CP3"
    }, {
        "id": "VDU1_CP5-6396a2a1-7e36-49bd-8fff-2d46394a6b29",
        "type": "LINKPORT",
        "resourceTemplateId": "VDU1_CP5"
    }, {
        "id": "VDU1_CP4-6396a2a1-7e36-49bd-8fff-2d46394a6b29",
        "type": "LINKPORT",
        "resourceTemplateId": "VDU1_CP4"
    }, {
        "id": "VirtualStorage-6396a2a1-7e36-49bd-8fff-2d46394a6b29",
        "type": "STORAGE",
        "resourceTemplateId": "VirtualStorage"
    }, {
        "id": "39e0af93-aba5-4a15-9231-cdaa4149738e",
        "type": "COMPUTE",
        "resourceTemplateId": "VDU1"
    }, {
        "id": "VDU1_CP1-39e0af93-aba5-4a15-9231-cdaa4149738e",
        "type": "LINKPORT",
        "resourceTemplateId": "VDU1_CP1"
    }, {
        "id": "VDU1_CP2-39e0af93-aba5-4a15-9231-cdaa4149738e",
        "type": "LINKPORT",
        "resourceTemplateId": "VDU1_CP2"
    }, {
        "id": "VDU1_CP3-39e0af93-aba5-4a15-9231-cdaa4149738e",
        "type": "LINKPORT",
        "resourceTemplateId": "VDU1_CP3"
    }, {
        "id": "VDU1_CP5-39e0af93-aba5-4a15-9231-cdaa4149738e",
        "type": "LINKPORT",
        "resourceTemplateId": "VDU1_CP5"
    }, {
        "id": "VDU1_CP4-39e0af93-aba5-4a15-9231-cdaa4149738e",
        "type": "LINKPORT",
        "resourceTemplateId": "VDU1_CP4"
    }, {
        "id": "VirtualStorage-39e0af93-aba5-4a15-9231-cdaa4149738e",
        "type": "STORAGE",
        "resourceTemplateId": "VirtualStorage"
    }, {
        "id": "8a3ab83f-187c-4feb-b1b5-a6bf587130fa",
        "type": "COMPUTE",
        "resourceTemplateId": "VDU1"
    }, {
        "id": "VDU1_CP1-8a3ab83f-187c-4feb-b1b5-a6bf587130fa",
        "type": "LINKPORT",
        "resourceTemplateId": "VDU1_CP1"
    }, {
        "id": "VDU1_CP2-8a3ab83f-187c-4feb-b1b5-a6bf587130fa",
        "type": "LINKPORT",
        "resourceTemplateId": "VDU1_CP2"
    }, {
        "id": "VDU1_CP3-8a3ab83f-187c-4feb-b1b5-a6bf587130fa",
        "type": "LINKPORT",
        "resourceTemplateId": "VDU1_CP3"
    }, {
        "id": "VDU1_CP5-8a3ab83f-187c-4feb-b1b5-a6bf587130fa",
        "type": "LINKPORT",
        "resourceTemplateId": "VDU1_CP5"
    }, {
        "id": "VDU1_CP4-8a3ab83f-187c-4feb-b1b5-a6bf587130fa",
        "type": "LINKPORT",
        "resourceTemplateId": "VDU1_CP4"
    }, {
        "id": "VirtualStorage-8a3ab83f-187c-4feb-b1b5-a6bf587130fa",
        "type": "STORAGE",
        "resourceTemplateId": "VirtualStorage"
    }, {
        "id": "3f2385fa-3f13-436d-b93a-47c62ef237e0",
        "type": "COMPUTE",
        "resourceTemplateId": "VDU2"
    }, {
        "id": "VDU2_CP5-3f2385fa-3f13-436d-b93a-47c62ef237e0",
        "type": "LINKPORT",
        "resourceTemplateId": "VDU2_CP5"
    }, {
        "id": "VDU2_CP2-3f2385fa-3f13-436d-b93a-47c62ef237e0",
        "type": "LINKPORT",
        "resourceTemplateId": "VDU2_CP2"
    }, {
        "id": "VDU2_CP1-3f2385fa-3f13-436d-b93a-47c62ef237e0",
        "type": "LINKPORT",
        "resourceTemplateId": "VDU2_CP1"
    }, {
        "id": "VDU2_CP3-3f2385fa-3f13-436d-b93a-47c62ef237e0",
        "type": "LINKPORT",
        "resourceTemplateId": "VDU2_CP3"
    }, {
        "id": "VDU2_CP4-3f2385fa-3f13-436d-b93a-47c62ef237e0",
        "type": "LINKPORT",
        "resourceTemplateId": "VDU2_CP4"
    }, {
        "id": "a411a968-c00b-4d46-8553-a37f3537391e",
        "type": "VL",
        "resourceTemplateId": "internalVL2"
    }, {
        "id": "f06ba7cf-f5af-4856-8d3a-56b331d1b9a5",
        "type": "VL",
        "resourceTemplateId": "internalVL3"
    }],
    "placementConstraints": [{
        "affinityOrAntiAffinity": "ANTI_AFFINITY",
        "scope": "NFVI_NODE",
        "resource": [{
            "idType": "GRANT",
            "resourceId": "6396a2a1-7e36-49bd-8fff-2d46394a6b29"
        }, {
            "idType": "GRANT",
            "resourceId": "39e0af93-aba5-4a15-9231-cdaa4149738e"
        }, {
            "idType": "GRANT",
            "resourceId": "8a3ab83f-187c-4feb-b1b5-a6bf587130fa"
        }, {
            "idType": "GRANT",
            "resourceId": "3f2385fa-3f13-436d-b93a-47c62ef237e0"
        }]
    }],
    "_links": {
        "vnfLcmOpOcc": {
            "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_lcm_op_occs/"
                    "34da9ba7-6ab1-4d8d-a68a-68892e56642c"
        },
        "vnfInstance": {
            "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/"
                    "2d004394-d0f0-406d-845a-2b148f91039a"
        }
    }
}
_lcmocc_inst_value = {
    'id': 'test-1',
    'vnfInstanceId': 'instance-1',
    'operation': 'INSTANTIATE',
    'operationState': 'COMPLETED',
    'isAutomaticInvocation': False,
    'startTime': '2021-01-23 13:41:03+00:00'
}


class TestNfvoClient(base.BaseTestCase):

    def setUp(self):
        super(TestNfvoClient, self).setUp()
        objects.register_all()
        self.context = context.get_admin_context()
        CONF.vnf_package.vnf_package_csar_path = (
            '/opt/stack/data/tacker/vnfpackage/')
        self.context.api_version = api_version.APIVersion('2.0.0')
        self.nfvo_client = nfvo_client.NfvoClient()
        self.nfvo_client.endpoint = 'http://127.0.0.1:9990'
        auth_handle = http_client.OAuth2AuthHandle(
            self.nfvo_client.endpoint,
            'http://127.0.0.1:9990/token',
            'test',
            'test'
        )
        self.nfvo_client.client = http_client.HttpClient(auth_handle)
        self.nfvo_client.grant_api_version = '1.4.0'
        self.nfvo_client.vnfpkgm_api_version = '2.1.0'

        cfg.CONF.set_override("nfvo_verify_cert", True, group="v2_nfvo")
        self.nfvo_client_https = nfvo_client.NfvoClient()
        self.nfvo_client_https.endpoint = 'http://127.0.0.1:9990'
        self.nfvo_client_https.client = http_client.HttpClient(auth_handle)
        self.nfvo_client_https.grant_api_version = '1.4.0'
        self.nfvo_client_https.vnfpkgm_api_version = '2.1.0'

        cfg.CONF.set_override("use_external_nfvo", True, group="v2_nfvo")
        cfg.CONF.set_override("mtls_ca_cert_file", "/path/to/cacert",
            group="v2_nfvo")
        cfg.CONF.set_override("mtls_client_cert_file", "/path/to/clientcert",
            group="v2_nfvo")
        cfg.CONF.set_override("token_endpoint", "http://127.0.0.1:9990/token",
            group="v2_nfvo")
        cfg.CONF.set_override("client_id", "test", group="v2_nfvo")
        self.addCleanup(mock.patch.stopall)
        mock.patch('os.makedirs').start()
        self.nfvo_client_mtls = nfvo_client.NfvoClient()
        self.nfvo_client_mtls.endpoint = 'http://127.0.0.1:9990'
        auth_handle_mtls = http_client.OAuth2MtlsAuthHandle(
            self.nfvo_client.endpoint,
            'http://127.0.0.1:9990/token',
            'test',
            '/path/to/cacert',
            '/path/to/clientcert'
        )
        self.nfvo_client_mtls.client = http_client.HttpClient(auth_handle_mtls)
        self.nfvo_client_mtls.grant_api_version = '1.4.0'
        self.nfvo_client_mtls.vnfpkgm_api_version = '2.1.0'

    @mock.patch.object(local_nfvo.LocalNfvo, 'onboarded_show')
    @mock.patch.object(http_client.HttpClient, 'do_request')
    def test_get_vnf_package_info_vnfd(
            self, mock_request, mock_onboarded_show):
        # local nfvo
        cfg.CONF.clear_override("use_external_nfvo", group="v2_nfvo")
        self.nfvo_client.is_local = True
        mock_onboarded_show.return_value = vnfd_utils.Vnfd(
            vnfd_id=SAMPLE_VNFD_ID)
        result = self.nfvo_client.get_vnf_package_info_vnfd(
            self.context, SAMPLE_VNFD_ID)
        self.assertEqual(SAMPLE_VNFD_ID, result.vnfd_id)

        # external nfvo oauth2
        cfg.CONF.clear_override("mtls_client_cert_file", group="v2_nfvo")
        cfg.CONF.set_override("use_external_nfvo", True, group="v2_nfvo")
        self.nfvo_client.is_local = False
        mock_request.return_value = (requests.Response(), _vnfpkg_body_example)
        result = self.nfvo_client.get_vnf_package_info_vnfd(
            self.context, SAMPLE_VNFD_ID)
        self.assertEqual(SAMPLE_VNFD_ID, result.vnfdId)

        # external nfvo oauth2 https
        self.nfvo_client_https.is_local = False
        result = self.nfvo_client_https.get_vnf_package_info_vnfd(
            self.context, SAMPLE_VNFD_ID)
        self.assertEqual(SAMPLE_VNFD_ID, result.vnfdId)

        # external nfvo oauth2 mtls
        cfg.CONF.set_override("mtls_client_cert_file", "/path/to/clientcert",
            group="v2_nfvo")
        result = self.nfvo_client_mtls.get_vnf_package_info_vnfd(
            self.context, SAMPLE_VNFD_ID)
        self.assertEqual(SAMPLE_VNFD_ID, result.vnfdId)

    @mock.patch.object(http_client.HttpClient, 'do_request')
    def test_onboarded_show_vnfd(self, mock_request):
        # local nfvo
        cfg.CONF.clear_override("use_external_nfvo", group="v2_nfvo")
        self.nfvo_client.is_local = True
        result = self.nfvo_client.onboarded_show_vnfd(
            self.context, SAMPLE_VNFD_ID)
        self.assertIsNone(result)

        # external nfvo oauth2
        cfg.CONF.clear_override("mtls_client_cert_file", group="v2_nfvo")
        cfg.CONF.set_override("use_external_nfvo", True, group="v2_nfvo")
        self.nfvo_client.is_local = False
        mock_request.return_value = (requests.Response(), 'test')
        result = self.nfvo_client.onboarded_show_vnfd(
            self.context, SAMPLE_VNFD_ID)
        self.assertEqual('test', result)

        # external nfvo oauth2 mtls
        cfg.CONF.set_override("mtls_client_cert_file", "/path/to/clientcert",
            group="v2_nfvo")
        result = self.nfvo_client_mtls.onboarded_show_vnfd(
            self.context, SAMPLE_VNFD_ID)
        self.assertEqual('test', result)

    @mock.patch.object(http_client.HttpClient, 'do_request')
    def test_onboarded_package_content(self, mock_request):
        # local nfvo
        cfg.CONF.clear_override("use_external_nfvo", group="v2_nfvo")
        self.nfvo_client.is_local = True
        result = self.nfvo_client.onboarded_package_content(
            self.context, SAMPLE_VNFD_ID)
        self.assertIsNone(result)

        # external nfvo oauth2
        cfg.CONF.clear_override("mtls_client_cert_file", group="v2_nfvo")
        cfg.CONF.set_override("use_external_nfvo", True, group="v2_nfvo")
        self.nfvo_client.is_local = False
        mock_request.return_value = (requests.Response(), 'test')
        result = self.nfvo_client.onboarded_package_content(
            self.context, SAMPLE_VNFD_ID)
        self.assertEqual('test', result)

        # external nfvo oauth2 mtls
        cfg.CONF.set_override("mtls_client_cert_file", "/path/to/clientcert",
            group="v2_nfvo")
        result = self.nfvo_client_mtls.onboarded_package_content(
            self.context, SAMPLE_VNFD_ID)
        self.assertEqual('test', result)

    @mock.patch.object(local_nfvo.LocalNfvo, 'grant')
    @mock.patch.object(http_client.HttpClient, 'do_request')
    def test_grant(self, mock_request, mock_grant):
        # local nfvo
        cfg.CONF.clear_override("use_external_nfvo", group="v2_nfvo")
        self.nfvo_client.is_local = True
        mock_grant.return_value = objects.GrantV1.from_dict(_grant_res)
        grant_req = objects.GrantRequestV1.from_dict(_inst_grant_req_example)
        grant_res = self.nfvo_client.grant(self.context, grant_req)
        result = grant_res.to_dict()
        self.assertIsNotNone(result['addResources'])
        self.assertEqual('44fd5841-ce98-4d54-a828-6ef51f941c8a', result[
            'vimAssets']['softwareImages'][0]['vimSoftwareImageId'])

        # external nfvo
        cfg.CONF.clear_override("mtls_client_cert_file", group="v2_nfvo")
        cfg.CONF.set_override("use_external_nfvo", True, group="v2_nfvo")
        self.nfvo_client.is_local = False
        mock_request.return_value = (requests.Response(), _grant_res)
        grant_res = self.nfvo_client.grant(self.context, grant_req)
        result = grant_res.to_dict()
        self.assertIsNotNone(result['addResources'])
        self.assertEqual('44fd5841-ce98-4d54-a828-6ef51f941c8a', result[
            'vimAssets']['softwareImages'][0]['vimSoftwareImageId'])

        # external nfvo oauth2 mtls
        cfg.CONF.set_override("mtls_client_cert_file", "/path/to/clientcert",
            group="v2_nfvo")
        grant_res = self.nfvo_client_mtls.grant(self.context, grant_req)
        result = grant_res.to_dict()
        self.assertIsNotNone(result['addResources'])
        self.assertEqual('44fd5841-ce98-4d54-a828-6ef51f941c8a', result[
            'vimAssets']['softwareImages'][0]['vimSoftwareImageId'])

    @mock.patch.object(objects.base.TackerPersistentObject, 'get_all')
    @mock.patch.object(subsc_utils, 'send_notification')
    @mock.patch.object(local_nfvo.LocalNfvo, 'recv_inst_create_notification')
    def test_send_inst_create_notification(
            self, mock_recv, mock_send, mock_subscs):
        cfg.CONF.clear_override("use_external_nfvo", group="v2_nfvo")
        self.nfvo_client.is_local = True
        inst = objects.VnfInstanceV2(id='test-instance')
        mock_subscs.return_value = [objects.LccnSubscriptionV2(id='subsc-1')]
        self.nfvo_client.send_inst_create_notification(
            self.context, inst, 'http://127.0.0.1:9890')
        self.assertEqual(1, mock_recv.call_count)
        self.assertEqual(1, mock_send.call_count)

    @mock.patch.object(objects.base.TackerPersistentObject, 'get_all')
    @mock.patch.object(subsc_utils, 'send_notification')
    @mock.patch.object(local_nfvo.LocalNfvo, 'recv_inst_delete_notification')
    def test_send_inst_delete_notification(
            self, mock_recv, mock_send, mock_subscs):
        cfg.CONF.clear_override("use_external_nfvo", group="v2_nfvo")
        self.nfvo_client.is_local = True
        inst = objects.VnfInstanceV2(id='test-instance')
        mock_subscs.return_value = [objects.LccnSubscriptionV2(id='subsc-1')]
        self.nfvo_client.send_inst_delete_notification(
            self.context, inst, 'http://127.0.0.1:9890')
        self.assertEqual(1, mock_recv.call_count)
        self.assertEqual(1, mock_send.call_count)

    @mock.patch.object(objects.base.TackerPersistentObject, 'get_all')
    @mock.patch.object(subsc_utils, 'send_notification')
    @mock.patch.object(local_nfvo.LocalNfvo, 'recv_lcmocc_notification')
    def test_send_lcmocc_notification(self, mock_recv, mock_send, mock_subscs):
        inst = objects.VnfInstanceV2(id='test-instance')
        lcmocc = objects.VnfLcmOpOccV2.from_dict(_lcmocc_inst_value)
        mock_subscs.return_value = [objects.LccnSubscriptionV2(
            id='subsc-1', verbosity='FULL')]
        self.nfvo_client.send_lcmocc_notification(
            self.context, lcmocc, inst, 'http://127.0.0.1:9890')
        self.assertEqual(1, mock_recv.call_count)
        self.assertEqual(1, mock_send.call_count)

    @mock.patch.object(subsc_utils, 'send_notification')
    @mock.patch.object(pm_job_utils, 'make_pm_notif_data')
    def test_send_pm_job_notification(self, mock_notif, mock_send):
        mock_notif.return_value = 'mock_notif'
        mock_send.return_value = None
        entries = {
            'objectType': "VNF",
            'objectInstanceId': "instance_id_1",
            'subObjectInstanceId': "subObjectInstanceId_1"
        }
        report = objects.PerformanceReportV2(
            id=uuidutils.generate_uuid(),
            jobId='pm_job_id',
            entries=[objects.VnfPmReportV2_Entries.from_dict(entries)]
        )
        self.nfvo_client.send_pm_job_notification(
            report, "pm_job", 'timestamp', self.nfvo_client.endpoint
        )

    def test_make_csar_cache_error(self):
        csar_dir = "/tmp/test_csar_dir"
        zip_file = b"no zip content"
        self.assertRaises(zipfile.BadZipFile,
            self.nfvo_client._make_csar_cache, csar_dir, zip_file)
        self.assertFalse(os.path.exists(csar_dir))

    def test_delete_csar_dir(self):
        log_name = "tacker.sol_refactored.nfvo.nfvo_client"
        csar_dir = "/tmp/not_exist"
        with self.assertLogs(logger=log_name, level=logging.CRITICAL) as cm:
            self.nfvo_client._delete_csar_dir(csar_dir)

        msg = (f"CRITICAL:{log_name}:VNF package cache '{csar_dir}' "
               "could not be deleted")
        self.assertIn(msg, cm.output[0])
