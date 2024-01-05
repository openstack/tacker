#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import os
import time
import yaml

from oslo_utils import uuidutils

from tacker.sol_refactored.common import http_client
from tacker.sol_refactored import objects
from tacker.tests.functional.sol_enhanced_policy.base import (
    BaseEnhancedPolicyTest)
from tacker.tests.functional.sol_kubernetes_v2.base_v2 import (
    BaseVnfLcmKubernetesV2Test)
from tacker.tests.functional.sol_kubernetes_v2 import paramgen
from tacker.tests import utils as base_utils

VNFLCM_V2_VERSION = "2.0.0"
WAIT_LCMOCC_UPDATE_TIME = 3


class VnflcmAPIsV2CNFBase(BaseVnfLcmKubernetesV2Test, BaseEnhancedPolicyTest):

    user_role_map = {
        'user_a': ['VENDOR_company_A', 'AREA_area_A@region_A',
                   'TENANT_namespace-a', 'manager'],
        'user_a_1': ['VENDOR_company_A', 'manager'],
        'user_b': ['VENDOR_company_B', 'AREA_area_B@region_B',
                   'TENANT_namespace-b', 'manager'],
        'user_c': ['VENDOR_company_C', 'AREA_area_C@region_C',
                   'TENANT_namespace-c', 'manager'],
        'user_all': ['VENDOR_all', 'AREA_all@all', 'TENANT_all', 'manager'],
        'user_admin': ['admin']
    }

    @classmethod
    def setUpClass(cls):
        BaseVnfLcmKubernetesV2Test.setUpClass()
        BaseEnhancedPolicyTest.setUpClass(cls)

        for user in cls.users:
            client = cls.get_local_tacker_http_client(user.name)
            setattr(
                cls, cls.TK_HTTP_CLIENT_NAME % {'username': user.name}, client)

        cls.tacker_client = cls.get_local_tacker_http_client('user_all')

        test_instantiate_cnf_resources_path = base_utils.test_sample(
            "functional/sol_kubernetes_v2/test_instantiate_cnf_resources")
        test_change_vnf_pkg_with_deployment_path = base_utils.test_sample(
            "functional/sol_kubernetes_v2",
            "test_change_vnf_pkg_with_deployment")

        cls.vnf_pkg_a, cls.vnfd_id_a = cls.create_vnf_package(
            test_instantiate_cnf_resources_path, provider='company_A',
            namespace='namespace-a')

        cls.vnf_pkg_a_1, cls.vnfd_id_a_1 = cls.create_vnf_package(
            test_change_vnf_pkg_with_deployment_path, provider='company_A',
            namespace='namespace-a')

        cls.vnf_pkg_b, cls.vnfd_id_b = cls.create_vnf_package(
            test_instantiate_cnf_resources_path, provider='company_B',
            namespace='namespace-b')

        cls.vnf_pkg_b_1, cls.vnfd_id_b_1 = cls.create_vnf_package(
            test_change_vnf_pkg_with_deployment_path, provider='company_B',
            namespace='namespace-b')

        cls.vnf_pkg_c, cls.vnfd_id_c = cls.create_vnf_package(
            test_instantiate_cnf_resources_path, provider='company_C',
            namespace='namespace-c')

        cls.vnf_pkg_c_1, cls.vnfd_id_c_1 = cls.create_vnf_package(
            test_change_vnf_pkg_with_deployment_path, provider='company_C',
            namespace='namespace-c')

    @classmethod
    def tearDownClass(cls):
        super(VnflcmAPIsV2CNFBase, cls).tearDownClass()

        cls.delete_vnf_package(cls.vnf_pkg_a)
        cls.delete_vnf_package(cls.vnf_pkg_a_1)
        cls.delete_vnf_package(cls.vnf_pkg_b)
        cls.delete_vnf_package(cls.vnf_pkg_b_1)
        cls.delete_vnf_package(cls.vnf_pkg_c)
        cls.delete_vnf_package(cls.vnf_pkg_c_1)

    @classmethod
    def get_vim_info(cls, vim_conf='local-vim.yaml'):
        vim_params = yaml.safe_load(base_utils.read_file(vim_conf))
        vim_params['auth_url'] += '/v3'

        vim_info = objects.VimConnectionInfo(
            interfaceInfo={'endpoint': vim_params['auth_url']},
            accessInfo={
                'region': 'RegionOne',
                'project': vim_params['project_name'],
                'username': vim_params['username'],
                'password': vim_params['password'],
                'userDomain': vim_params['user_domain_name'],
                'projectDomain': vim_params['project_domain_name']
            }
        )

        return vim_info

    @classmethod
    def get_local_tacker_http_client(cls, username):
        vim_info = cls.get_vim_info(vim_conf=cls.local_vim_conf_file)

        auth = http_client.KeystonePasswordAuthHandle(
            auth_url=vim_info.interfaceInfo['endpoint'],
            username=username,
            password='devstack',
            project_name=vim_info.accessInfo['project'],
            user_domain_name=vim_info.accessInfo['userDomain'],
            project_domain_name=vim_info.accessInfo['projectDomain']
        )

        return http_client.HttpClient(auth)

    def _step_lcm_create(self, username, vnfd_id, expected_status_code):
        self.tacker_client = self.get_tk_http_client_by_user(username)

        expected_inst_attrs = [
            'id',
            'vnfInstanceName',
            'vnfInstanceDescription',
            'vnfdId',
            'vnfProvider',
            'vnfProductName',
            'vnfSoftwareVersion',
            'vnfdVersion',
            # 'vnfConfigurableProperties', # omitted
            # 'vimConnectionInfo', # omitted
            'instantiationState',
            # 'instantiatedVnfInfo', # omitted
            'metadata',
            # 'extensions', # omitted
            '_links'
        ]
        create_req = paramgen.test_instantiate_cnf_resources_create(
            vnfd_id)
        resp, body = self.create_vnf_instance(create_req)
        self.assertEqual(expected_status_code, resp.status_code)
        if expected_status_code == 201:
            self.check_resp_headers_in_create(resp)
            self.check_resp_body(body, expected_inst_attrs)
            inst_id = body['id']
            return inst_id
        else:
            return None

    def _sample_instantiate(self, auth_url, bearer_token, ssl_ca_cert=None,
            namespace='default', area=None, vim_id=None):
        vim_id_1 = uuidutils.generate_uuid()
        vim_id_2 = uuidutils.generate_uuid()
        vim_1 = {
            "vimId": vim_id_1,
            "vimType": "kubernetes",
            "interfaceInfo": {"endpoint": auth_url},
            "accessInfo": {
                "bearer_token": bearer_token,
            },
            "extra": {"dummy-key": "dummy-val"}
        }
        vim_2 = {
            "vimId": vim_id_2,
            "vimType": "kubernetes",
            "interfaceInfo": {"endpoint": auth_url},
            "accessInfo": {
                "username": "dummy_user",
                "password": "dummy_password",
            },
            "extra": {"dummy-key": "dummy-val"}
        }

        if ssl_ca_cert:
            vim_1["interfaceInfo"]["ssl_ca_cert"] = ssl_ca_cert
            vim_2["interfaceInfo"]["ssl_ca_cert"] = ssl_ca_cert

        if area:
            vim_1.update({'extra': {'area': area}})
            vim_2.update({'extra': {'area': area}})

        if vim_id:
            vim_1 = {
                "vimId": vim_id,
                "vimType": "kubernetes"
            }
            vim_2 = {
                "vimId": vim_id,
                "vimType": "kubernetes"
            }

        return {
            "flavourId": "simple",
            "vimConnectionInfo": {
                "vim1": vim_1,
                "vim2": vim_2
            },
            "additionalParams": {
                "lcm-kubernetes-def-files": [
                    "Files/kubernetes/namespace.yaml",
                    "Files/kubernetes/deployment.yaml",
                ],
                "namespace": namespace
            }
        }

    def _step_lcm_instantiate(self, username, inst_id, namespace,
                              expected_status_code, area=None, vim_id=None):
        self.tacker_client = self.get_tk_http_client_by_user(username)
        # Instantiate a VNF instance
        instantiate_req = self._sample_instantiate(
            self.auth_url, self.bearer_token, ssl_ca_cert=self.ssl_ca_cert,
            namespace=namespace, area=area, vim_id=vim_id
        )
        resp, body = self.instantiate_vnf_instance(inst_id, instantiate_req)
        self.assertEqual(expected_status_code, resp.status_code)
        if expected_status_code == 202:
            self.check_resp_headers_in_operation_task(resp)
            lcmocc_id = os.path.basename(resp.headers['Location'])
            self.wait_lcmocc_complete(lcmocc_id)

    def _step_lcm_show(self, username, inst_id, expected_status_code):
        self.tacker_client = self.get_tk_http_client_by_user(username)
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(expected_status_code, resp.status_code)

    def _step_lcm_list(self, username, expected_inst_list):
        self.tacker_client = self.get_tk_http_client_by_user(username)
        path = "/vnflcm/v2/vnf_instances"
        resp, vnf_instances = self.tacker_client.do_request(
            path, "GET", version=VNFLCM_V2_VERSION)
        self.assertEqual(200, resp.status_code)
        inst_ids = set([inst.get('id') for inst in vnf_instances])
        for inst_id in expected_inst_list:
            self.assertIn(inst_id, inst_ids)

    def _step_lcm_scale_out(self, username, inst_id, expected_status_code):
        self.tacker_client = self.get_tk_http_client_by_user(username)
        scale_out_req = {
            "type": "SCALE_OUT",
            "aspectId": "vdu2_aspect",
            "numberOfSteps": 1
        }
        resp, body = self.scale_vnf_instance(inst_id, scale_out_req)
        self.assertEqual(expected_status_code, resp.status_code)
        if expected_status_code == 202:
            lcmocc_id = os.path.basename(resp.headers['Location'])
            self.wait_lcmocc_complete(lcmocc_id)

    def change_ext_conn_max(self, net_ids, subnets, auth_url, area):
        vim_id_1 = uuidutils.generate_uuid()
        vim_id_2 = uuidutils.generate_uuid()

        ext_vl_1 = {
            "id": uuidutils.generate_uuid(),
            "vimConnectionId": "vim1",
            "resourceProviderId": uuidutils.generate_uuid(),
            "resourceId": net_ids['ft-net1'],
            "extCps": [
                {
                    "cpdId": "VDU1_CP1",
                    "cpConfig": {
                        "VDU1_CP1": {
                            "cpProtocolData": [{
                                "layerProtocol": "IP_OVER_ETHERNET",
                                "ipOverEthernet": {
                                    # "macAddress": omitted,
                                    # "segmentationId": omitted,
                                    "ipAddresses": [{
                                        "type": "IPV4",
                                        # "fixedAddresses": omitted,
                                        "numDynamicAddresses": 1,
                                        # "addressRange": omitted,
                                        "subnetId": subnets[
                                            'ft-ipv4-subnet1']}]
                                }
                            }]}
                    }
                },
                {
                    "cpdId": "VDU2_CP2",
                    "cpConfig": {
                        "VDU2_CP2": {
                            "cpProtocolData": [{
                                "layerProtocol": "IP_OVER_ETHERNET",
                                "ipOverEthernet": {
                                    # "macAddress": omitted,
                                    # "segmentationId": omitted,
                                    "ipAddresses": [{
                                        "type": "IPV4",
                                        "fixedAddresses": [
                                            "22.22.22.101"
                                        ],
                                        # "numDynamicAddresses": omitted
                                        # "addressRange": omitted,
                                        "subnetId": subnets['ft-ipv4-subnet1']
                                    }, {
                                        "type": "IPV6",
                                        # "fixedAddresses": omitted,
                                        # "numDynamicAddresses": omitted,
                                        "numDynamicAddresses": 1,
                                        # "addressRange": omitted,
                                        "subnetId": subnets['ft-ipv6-subnet1']
                                    }]
                                }
                            }]
                        }}
                }
            ]
        }
        vim_1 = {
            "vimId": vim_id_1,
            "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_3",
            "interfaceInfo": {"endpoint": auth_url},
            "accessInfo": {
                "username": "nfv_user",
                "region": "RegionOne",
                "password": "devstack",
                "project": "nfv",
                "projectDomain": "Default",
                "userDomain": "Default"
            },
            "extra": {"area": area}
        }
        vim_2 = {
            "vimId": vim_id_2,
            "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_3",
            "interfaceInfo": {"endpoint": auth_url},
            "accessInfo": {
                "username": "dummy_user",
                "region": "RegionOne",
                "password": "dummy_password",
                "project": "dummy_project",
                "projectDomain": "Default",
                "userDomain": "Default"
            },
            "extra": {"area": area}
        }

        return {
            "extVirtualLinks": [
                ext_vl_1
            ],
            "vimConnectionInfo": {
                "vim1": vim_1,
                "vim2": vim_2
            },
            "additionalParams": {"dummy-key": "dummy-val"}
        }

    def _step_lcm_change_vnfpkg(self, username, inst_id, new_vnfd_id,
                                expected_status_code):
        self.tacker_client = self.get_tk_http_client_by_user(username)
        change_vnfpkg_req = paramgen.change_vnfpkg(new_vnfd_id)
        resp, body = self.change_vnfpkg(inst_id, change_vnfpkg_req)
        self.assertEqual(expected_status_code, resp.status_code)
        if expected_status_code == 202:
            lcmocc_id = os.path.basename(resp.headers['Location'])
            self.wait_lcmocc_complete(lcmocc_id)

            # wait a bit because there is a bit time lag between lcmocc DB
            # update and change_vnfpkg completion.
            time.sleep(WAIT_LCMOCC_UPDATE_TIME)

    def _step_lcm_update(self, username, inst_id,
                         expected_status_code):
        self.tacker_client = self.get_tk_http_client_by_user(username)
        update_req = {
            "vnfInstanceName": "modify_{}".format(inst_id)
        }
        path = f"/vnflcm/v2/vnf_instances/{inst_id}"
        resp, body = self.tacker_client.do_request(
            path, "PATCH", body=update_req, version=VNFLCM_V2_VERSION)
        self.assertEqual(expected_status_code, resp.status_code)
        if expected_status_code == 202:
            lcmocc_id = os.path.basename(resp.headers['Location'])
            self.wait_lcmocc_complete(lcmocc_id)

    def _step_lcm_scale_in(self, username, inst_id, expected_status_code):
        self.tacker_client = self.get_tk_http_client_by_user(username)
        scale_in_req = {
            "type": "SCALE_IN",
            "aspectId": "vdu2_aspect",
            "numberOfSteps": 1
        }
        resp, body = self.scale_vnf_instance(inst_id, scale_in_req)
        self.assertEqual(expected_status_code, resp.status_code)
        if expected_status_code == 202:
            lcmocc_id = os.path.basename(resp.headers['Location'])
            self.wait_lcmocc_complete(lcmocc_id)

    def _step_lcm_heal(self, username, inst_id, expected_status_code):
        self.tacker_client = self.get_tk_http_client_by_user('user_admin')
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)

        # check vnfc_resource_info
        vnfc_infos = body['instantiatedVnfInfo']['vnfcInfo']
        vdu2_ids = [vnfc_info['id'] for vnfc_info in vnfc_infos
                    if vnfc_info['vduId'] == 'VDU2']
        target = [vdu2_ids[0]]

        heal_req = paramgen.max_sample_heal(target)

        self.tacker_client = self.get_tk_http_client_by_user(username)

        resp, body = self.heal_vnf_instance(inst_id, heal_req)
        self.assertEqual(expected_status_code, resp.status_code)
        if expected_status_code == 202:
            lcmocc_id = os.path.basename(resp.headers['Location'])
            self.wait_lcmocc_complete(lcmocc_id)

    def _step_lcm_terminate(self, username, inst_id, expected_status_code):
        self.tacker_client = self.get_tk_http_client_by_user(username)
        terminate_req = paramgen.max_sample_terminate()
        resp, body = self.terminate_vnf_instance(inst_id, terminate_req)
        self.assertEqual(expected_status_code, resp.status_code)
        if expected_status_code == 202:
            self.check_resp_headers_in_operation_task(resp)

            lcmocc_id = os.path.basename(resp.headers['Location'])
            self.wait_lcmocc_complete(lcmocc_id)

    def _step_lcm_delete(self, username, inst_id, expected_status_code):
        self.tacker_client = self.get_tk_http_client_by_user(username)
        # Delete a VNF instance
        resp, body = self.exec_lcm_operation(self.delete_vnf_instance,
                                             inst_id)
        self.assertEqual(expected_status_code, resp.status_code)
        if expected_status_code == 204:
            # check deletion of VNF instance
            resp, body = self.show_vnf_instance(inst_id)
            self.assertEqual(404, resp.status_code)

    def vnflcm_apis_v2_cnf_test_before_instantiate(self):

        # step 1 LCM-CreateV2, Resource Group A / User Group A
        inst_id_a = self._step_lcm_create('user_a', self.vnfd_id_a, 201)

        # step 2 LCM-CreateV2, Resource Group B / User Group A
        self._step_lcm_create('user_a', self.vnfd_id_b, 403)

        # step 3 LCM-CreateV2, Resource Group B / User Group all
        inst_id_b = self._step_lcm_create('user_all', self.vnfd_id_b, 201)

        # step 4 LCM-ShowV2, Resource Group A / User Group A
        self._step_lcm_show('user_a', inst_id_a, 200)

        # step 5 LCM-ShowV2, Resource Group A / User Group A-1
        self._step_lcm_show('user_a_1', inst_id_a, 200)

        # step 6 LCM-ShowV2, Resource Group B / User Group A
        self._step_lcm_show('user_a', inst_id_b, 403)

        # step 7 LCM-ShowV2, Resource Group B / User Group all
        self._step_lcm_show('user_all', inst_id_b, 200)

        # step 8 LCM-ListV2, Resource Group A / User Group A
        self._step_lcm_list('user_a', [inst_id_a])

        # step 9 LCM-ListV2, Resource Group - / User Group A-1
        self._step_lcm_list('user_a_1', [inst_id_a])

        # step 10 LCM-ListV2, Resource Group - / User Group B
        self._step_lcm_list('user_b', [inst_id_b])

        # step 11 LCM-ListV2, Resource Group - / User Group all
        self._step_lcm_list('user_all', [inst_id_a, inst_id_b])

        return inst_id_a, inst_id_b

    def vnflcm_apis_v2_cnf_test_after_instantiate(self, inst_id_a, inst_id_b):

        # step 15 LCM-ShowV2, Resource Group A / User Group A
        self._step_lcm_show('user_a', inst_id_a, 200)

        # step 16 LCM-Show, Resource Group A / User Group A-1
        self._step_lcm_show('user_a_1', inst_id_a, 403)

        # step 17 LCM-ShowV2, Resource Group B / User Group A
        self._step_lcm_show('user_a', inst_id_b, 403)

        # step 18 LCM-ShowV2, Resource Group B / User Group all
        self._step_lcm_show('user_all', inst_id_b, 200)

        # step 19 LCM-ListV2, Resource Group - / User Group A
        self._step_lcm_list('user_a', [inst_id_a])

        # step 20 LCM-ListV2, Resource Group - / User Group A-1
        self._step_lcm_list('user_a_1', [])

        # step 21 LCM-ListV2, Resource Group - / User Group B
        self._step_lcm_list('user_b', [inst_id_b])

        # step 22 LCM-ListV2, Resource Group - / User Group all
        self._step_lcm_list('user_all', [inst_id_a, inst_id_b])

        # step 23 LCM-ScaleV2(out), Resource Group A / User Group A
        self._step_lcm_scale_out('user_a', inst_id_a, 202)

        # step 24 LCM-ScaleV2(out), Resource Group B / User Group A
        self._step_lcm_scale_out('user_a', inst_id_b, 403)

        # step 25 LCM-ScaleV2(out), Resource Group B / User Group all
        self._step_lcm_scale_out('user_all', inst_id_b, 202)

        # step 26 LCM-ScaleV2(in), Resource Group A / User Group A
        self._step_lcm_scale_in('user_a', inst_id_a, 202)

        # step 27 LCM-ScaleV2(in), Resource Group B / User Group A
        self._step_lcm_scale_in('user_a', inst_id_b, 403)

        # step 28 LCM-ScaleV2(in), Resource Group B / User Group all
        self._step_lcm_scale_in('user_all', inst_id_b, 202)

        # step 29 LCM-HealV2, Resource Group A / User Group A
        self._step_lcm_heal('user_a', inst_id_a, 202)

        # step 30 LCM-HealV2, Resource Group B / User Group A
        self._step_lcm_heal('user_a', inst_id_b, 403)

        # step 31 LCM-HealV2, Resource Group B / User Group all
        self._step_lcm_heal('user_all', inst_id_b, 202)

        # step 32 LCM-ModifyV2, Resource Group A / User Group A
        self._step_lcm_update('user_a', inst_id_a, 202)

        # step 33 LCM-ModifyV2, Resource Group b / User Group A
        self._step_lcm_update('user_a', inst_id_b, 403)

        # step 34 LCM-ModifyV2, Resource Group B / User Group all
        self._step_lcm_update('user_all', inst_id_b, 202)

        # NOTE: CNF has no LCM-Change-Connectivity
        # step 34 LCM-Change-ConnectivityV2, Resource Group A / User Group A
        # step 35 LCM-Change-ConnectivityV2, Resource Group b / User Group A
        # step 36 LCM-Change-ConnectivityV2, Resource Group B / User Group all

        # step 38 LCM-Change-VnfPkgV2, Resource Group A / User Group A
        self._step_lcm_change_vnfpkg(
            'user_a', inst_id_a, self.vnfd_id_a_1, 202)

        # step 39 LCM-Change-VnfPkgV2, Resource Group B / User Group A
        self._step_lcm_change_vnfpkg(
            'user_a', inst_id_b, self.vnfd_id_b_1, 403)

        # step 40 LCM-Change-VnfPkgV2, Resource Group B / User Group all
        self._step_lcm_change_vnfpkg(
            'user_all', inst_id_b, self.vnfd_id_b_1, 202)

        # step 41 LCM-TerminateV2, Resource Group A / User Group A
        self._step_lcm_terminate('user_a', inst_id_a, 202)

        # step 42 LCM-TerminateV2, Resource Group B / User Group A
        self._step_lcm_terminate('user_a', inst_id_b, 403)

        # step 43 LCM-TerminateV2, Resource Group B / User Group all
        self._step_lcm_terminate('user_all', inst_id_b, 202)

        # step 44 LCM-DeleteV2, Resource Group A / User Group A
        self._step_lcm_delete('user_a', inst_id_a, 204)

        # step 45 LCM-DeleteV2, Resource Group B / User Group A
        self._step_lcm_delete('user_a', inst_id_b, 403)

        # step 46 LCM-DeleteV2, Resource Group B / User Group all
        self._step_lcm_delete('user_all', inst_id_b, 204)


class VnflcmAPIsV2VNFInstantiateWithArea(VnflcmAPIsV2CNFBase):

    def test_vnflcm_apis_v2_cnf_without_area_in_vim_conn_info(self):

        inst_id_a, inst_id_b = (
            self.vnflcm_apis_v2_cnf_test_before_instantiate())

        # step 12 LCM-InstantiateV2, Resource Group A / User Group A
        self._step_lcm_instantiate(
            'user_a', inst_id_a, 'namespace-a', 202, area='area_A@region_A')

        # step 13 LCM-InstantiateV2, Resource Group B / User Group A
        self._step_lcm_instantiate(
            'user_a', inst_id_b, 'namespace-b', 403, area='area_B@region_B')

        # step 14 LCM-InstantiateV2, Resource Group B / User Group all
        self._step_lcm_instantiate(
            'user_all', inst_id_b, 'namespace-b', 202, area='area_B@region_B')

        self.vnflcm_apis_v2_cnf_test_after_instantiate(inst_id_a, inst_id_b)


class VnflcmAPIsV2CNFInstantiateWithoutArea(VnflcmAPIsV2CNFBase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        vim_type = 'kubernetes'

        local_k8s_vim = 'local-k8s-vim.yaml'

        cls.vim_a = cls._step_vim_register(
            'user_a', vim_type, local_k8s_vim, 'vim_a', 'area_A@region_A')

        cls.vim_a_1 = cls._step_vim_register(
            'user_a', vim_type, local_k8s_vim, 'vim_a_1', 'area_A@region_A')

        cls.vim_b = cls._step_vim_register(
            'user_b', vim_type, local_k8s_vim, 'vim_b', 'area_B@region_B')

        cls.vim_b_1 = cls._step_vim_register(
            'user_b', vim_type, local_k8s_vim, 'vim_b_1', 'area_B@region_B')

    @classmethod
    def tearDownClass(cls):

        cls._step_vim_delete('user_a', cls.vim_a)
        cls._step_vim_delete('user_a', cls.vim_a_1)
        cls._step_vim_delete('user_b', cls.vim_b)
        cls._step_vim_delete('user_b', cls.vim_b_1)

        super().tearDownClass()

    def test_vnflcm_apis_v2_cnf_with_area_in_vim_conn_info(self):
        inst_id_a, inst_id_b = (
            self.vnflcm_apis_v2_cnf_test_before_instantiate())

        # step 12 LCM-InstantiateV2, Resource Group A / User Group A
        self._step_lcm_instantiate(
            'user_a', inst_id_a, 'namespace-a', 202, vim_id=self.vim_a['id'])

        # step 13 LCM-InstantiateV2, Resource Group B / User Group A
        self._step_lcm_instantiate(
            'user_a', inst_id_b, 'namespace-b', 403, vim_id=self.vim_b['id'])

        # step 14 LCM-InstantiateV2, Resource Group B / User Group all
        self._step_lcm_instantiate(
            'user_all', inst_id_b, 'namespace-b', 202, vim_id=self.vim_b['id'])

        self.vnflcm_apis_v2_cnf_test_after_instantiate(inst_id_a, inst_id_b)


class VnflcmAPIsV2CNFInstanceWithoutArea(VnflcmAPIsV2CNFBase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        vim_type = 'kubernetes'

        local_k8s_vim = 'local-k8s-vim.yaml'

        cls.vim_c = cls._step_vim_register(
            'user_c', vim_type, local_k8s_vim, 'vim_c', None)

        cls.vim_c_1 = cls._step_vim_register(
            'user_c', vim_type, local_k8s_vim, 'vim_c_1', None)

    @classmethod
    def tearDownClass(cls):

        cls._step_vim_delete('user_admin', cls.vim_c)
        cls._step_vim_delete('user_admin', cls.vim_c_1)

        super().tearDownClass()

    def test_vnflcm_apis_v2_cnf_instance_without_area(self):

        # step 1 LCM-CreateV2, Resource Group C / User Group C
        inst_id_c = self._step_lcm_create('user_c', self.vnfd_id_c, 201)

        # step 2 LCM-ShowV2, Resource Group C / User Group C
        self._step_lcm_show('user_c', inst_id_c, 200)

        # step 3 LCM-ShowV2, Resource Group C / User Group all
        self._step_lcm_show('user_all', inst_id_c, 200)

        # step 4 LCM-ShowV2, Resource Group C / User Group admin
        self._step_lcm_show('user_admin', inst_id_c, 200)

        # step 5 LCM-ListV2, Resource Group - / User Group C
        self._step_lcm_list('user_c', [inst_id_c])

        # step 6 LCM-ListV2, Resource Group - / User Group all
        self._step_lcm_list('user_all', [inst_id_c])

        # step 7 LCM-ListV2, Resource Group - / User Group admin
        self._step_lcm_list('user_admin', [inst_id_c])

        # step 8 LCM-InstantiateV2, Resource Group C / User Group C
        self._step_lcm_instantiate('user_c', inst_id_c, 'namespace-c', 202,
                                   vim_id=self.vim_c['id'])

        # step 9 LCM-ShowV2, Resource Group C / User Group C
        self._step_lcm_show('user_c', inst_id_c, 403)

        # step 10 LCM-ShowV2, Resource Group C / User Group all
        self._step_lcm_show('user_all', inst_id_c, 403)

        # step 11 LCM-ShowV2, Resource Group C / User Group admin
        self._step_lcm_show('user_admin', inst_id_c, 200)

        # step 12 LCM-ListV2, Resource Group - / User Group C
        self._step_lcm_list('user_c', [])

        # step 13 LCM-ListV2, Resource Group - / User Group all
        self._step_lcm_list('user_all', [])

        # step 14 LCM-ListV2, Resource Group - / User Group admin
        self._step_lcm_list('user_admin', [inst_id_c])

        # step 15 LCM-ScaleV2(out), Resource Group C / User Group C
        self._step_lcm_scale_out('user_c', inst_id_c, 403)

        # step 16 LCM-ScaleV2(out), Resource Group C / User Group all
        self._step_lcm_scale_out('user_all', inst_id_c, 403)

        # step 17 LCM-ScaleV2(out), Resource Group C / User Group admin
        self._step_lcm_scale_out('user_admin', inst_id_c, 202)

        # step 18 LCM-ScaleV2(in), Resource Group C / User Group C
        self._step_lcm_scale_in('user_c', inst_id_c, 403)

        # step 19 LCM-ScaleV2(in), Resource Group C / User Group A
        self._step_lcm_scale_in('user_all', inst_id_c, 403)

        # step 20 LCM-ScaleV2(in), Resource Group C / User Group all
        self._step_lcm_scale_in('user_admin', inst_id_c, 202)

        # step 21 LCM-HealV2, Resource Group C / User Group C
        self._step_lcm_heal('user_c', inst_id_c, 403)

        # step 22 LCM-HealV2, Resource Group C / User Group A
        self._step_lcm_heal('user_all', inst_id_c, 403)

        # step 23 LCM-HealV2, Resource Group C / User Group all
        self._step_lcm_heal('user_admin', inst_id_c, 202)

        # step 24 LCM-ModifyV2, Resource Group C / User Group C
        self._step_lcm_update('user_c', inst_id_c, 403)

        # step 25 LCM-ModifyV2, Resource Group C / User Group A
        self._step_lcm_update('user_all', inst_id_c, 403)

        # step 26 LCM-ModifyV2, Resource Group C / User Group all
        self._step_lcm_update('user_admin', inst_id_c, 202)

        # NOTE: CNF has no LCM-Change-Connectivity
        # step 27 LCM-Change-ConnectivityV2, Resource Group C / User Group C
        # step 28 LCM-Change-ConnectivityV2, Resource Group C / User Group all
        # step 29 LCM-Change-ConnectivityV2,
        # Resource Group C / User Group admin

        # step 30 LCM-Change-VnfPkgV2, Resource Group C / User Group C
        self._step_lcm_change_vnfpkg(
            'user_c', inst_id_c, self.vnfd_id_c_1, 403)

        # step 31 LCM-Change-VnfPkgV2, Resource Group C / User Group A
        self._step_lcm_change_vnfpkg(
            'user_all', inst_id_c, self.vnfd_id_c_1, 403)

        # step 32 LCM-Change-VnfPkgV2, Resource Group C / User Group all
        self._step_lcm_change_vnfpkg(
            'user_admin', inst_id_c, self.vnfd_id_c_1, 202)

        # step 33 LCM-TerminateV2, Resource Group C / User Group C
        self._step_lcm_terminate('user_c', inst_id_c, 403)

        # step 34 LCM-TerminateV2, Resource Group C / User Group A
        self._step_lcm_terminate('user_all', inst_id_c, 403)

        # step 35 LCM-TerminateV2, Resource Group C / User Group all
        self._step_lcm_terminate('user_admin', inst_id_c, 202)

        # step 36 LCM-DeleteV2, Resource Group C / User Group C
        self._step_lcm_delete('user_c', inst_id_c, 204)
