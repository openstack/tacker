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
from tacker.tests.functional.sol_v2_common import paramgen
from tacker.tests.functional.sol_v2_common.test_vnflcm_basic_common import (
    CommonVnfLcmTest)
from tacker.tests import utils as base_utils

WAIT_LCMOCC_UPDATE_TIME = 3


class VnflcmAPIsV2VNFBase(CommonVnfLcmTest, BaseEnhancedPolicyTest):

    user_role_map = {
        'user_a': ['VENDOR_company_A', 'AREA_area_A@region_A',
                   'TENANT_tenant_A', 'manager'],
        'user_a_1': ['VENDOR_company_A', 'manager'],
        'user_b': ['VENDOR_company_B', 'AREA_area_B@region_B',
                   'TENANT_tenant_B', 'manager'],
        'user_c': ['VENDOR_company_C', 'AREA_area_C@region_C',
                   'TENANT_tenant_C', 'manager'],
        'user_all': ['VENDOR_all', 'AREA_all@all',
                     'TENANT_all', 'manager'],
        'user_admin': ['admin']
    }
    vim_user_project_map = {
        'user_a': 'tenant_A',
        'user_b': 'tenant_B',
        'user_c': 'tenant_C',
        'user_all': 'tenant_B',
        'user_admin': 'tenant_C'
    }

    @classmethod
    def setUpClass(cls):
        CommonVnfLcmTest.setUpClass()
        BaseEnhancedPolicyTest.setUpClass(cls)
        cls.create_vim_user()

        for user in cls.users:
            client = cls.get_local_tacker_http_client(user.name)
            setattr(cls,
                    cls.TK_HTTP_CLIENT_NAME % {'username': user.name}, client)

        cls.tacker_client = cls.get_local_tacker_http_client('user_all')

        image_path = base_utils.test_etc_sample("etsi/nfv/common/Files/images",
            "cirros-0.5.2-x86_64-disk.img")

        # for basic lcms tests min pattern
        basic_lcms_min_path = base_utils.test_sample(
            "functional/sol_v2_common/basic_lcms_min")

        # for update vnf test
        update_vnf_path = base_utils.test_sample(
            "functional/sol_v2_common/update_vnf")
        # for change ext conn
        change_vnfpkg_from_image_to_image_path_2 = base_utils.test_sample(
            "functional/sol_v2_common/test_change_vnf_pkg_with_new_image")

        # for user_a
        cls.vnf_pkg_a, cls.vnfd_id_a = cls.create_vnf_package(
            basic_lcms_min_path, image_path=image_path, provider='company_A')

        cls.vnf_pkg_a_1, cls.vnfd_id_a_1 = cls.create_vnf_package(
            update_vnf_path, provider='company_A')

        cls.vnf_pkg_a_2, cls.vnfd_id_a_2 = cls.create_vnf_package(
            change_vnfpkg_from_image_to_image_path_2, image_path=image_path,
            provider='company_A')

        # for user_b
        cls.vnf_pkg_b, cls.vnfd_id_b = cls.create_vnf_package(
            basic_lcms_min_path, image_path=image_path, provider='company_B')

        cls.vnf_pkg_b_1, cls.vnfd_id_b_1 = cls.create_vnf_package(
            update_vnf_path, provider='company_B')

        cls.vnf_pkg_b_2, cls.vnfd_id_b_2 = cls.create_vnf_package(
            change_vnfpkg_from_image_to_image_path_2, image_path=image_path,
            provider='company_B')

        # for user_c
        cls.vnf_pkg_c, cls.vnfd_id_c = cls.create_vnf_package(
            basic_lcms_min_path, image_path=image_path, provider='company_C')

        cls.vnf_pkg_c_1, cls.vnfd_id_c_1 = cls.create_vnf_package(
            update_vnf_path, provider='company_C')

        cls.vnf_pkg_c_2, cls.vnfd_id_c_2 = cls.create_vnf_package(
            change_vnfpkg_from_image_to_image_path_2, image_path=image_path,
            provider='company_C')

    @classmethod
    def tearDownClass(cls):
        cls.delete_vnf_package(cls.vnf_pkg_a)
        cls.delete_vnf_package(cls.vnf_pkg_a_1)
        cls.delete_vnf_package(cls.vnf_pkg_a_2)
        cls.delete_vnf_package(cls.vnf_pkg_b)
        cls.delete_vnf_package(cls.vnf_pkg_b_1)
        cls.delete_vnf_package(cls.vnf_pkg_b_2)
        cls.delete_vnf_package(cls.vnf_pkg_c)
        cls.delete_vnf_package(cls.vnf_pkg_c_1)
        cls.delete_vnf_package(cls.vnf_pkg_c_2)
        BaseEnhancedPolicyTest.tearDownClass()
        super(VnflcmAPIsV2VNFBase, cls).tearDownClass()

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

    def change_ext_conn_max(self, net_ids, subnets, auth_url, area,
                            username=None, tenant=None):
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
                "username": f'vim_{username}' if username else "nfv_user",
                "region": "RegionOne",
                "password": "devstack",
                "project": tenant if tenant else "nfv",
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
        if not area:
            vim_1.pop('extra')
            vim_2.pop('extra')
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

    def _step_lcm_create(self, username, vnfd_id, expected_status_code):
        self.tacker_client = self.get_tk_http_client_by_user(username)
        create_req = paramgen.create_vnf_min(vnfd_id)
        resp, body = self.create_vnf_instance(create_req)
        self.assertEqual(expected_status_code, resp.status_code)
        if expected_status_code == 201:
            return body['id']
        else:
            return None

    def instantiate_vnf(self, area=None, vim_id=None, username=None,
                        tenant=None):
        # Omit except for required attributes
        # NOTE: Only the following cardinality attributes are set.
        #  - 1
        #  - 1..N (1)
        vim_id_1 = uuidutils.generate_uuid()
        vim_id_2 = uuidutils.generate_uuid()
        if area:
            vim_1 = {
                "vimId": vim_id_1,
                "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_3",
                "interfaceInfo": {"endpoint": self.auth_url},
                "accessInfo": {
                    "username": f'vim_{username}' if username else "nfv_user",
                    "region": "RegionOne",
                    "password": "devstack",
                    "project": tenant if tenant else "nfv",
                    "projectDomain": "Default",
                    "userDomain": "Default"
                },
                "extra": {"area": area}
            }
            vim_2 = {
                "vimId": vim_id_2,
                "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_3",
                "interfaceInfo": {"endpoint": self.auth_url},
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
        if vim_id:
            vim_1 = {
                "vimId": vim_id,
                "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_3"
            }
            vim_2 = {
                "vimId": vim_id,
                "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_3"
            }

        return {
            "flavourId": "simple",
            "vimConnectionInfo": {
                "vim1": vim_1,
                "vim2": vim_2
            }
        }

    def _step_lcm_instantiate(self, username, inst_id, tenant, glance_image,
            flavour_vdu_dict, zone_name_list, expected_status_code,
            area=None, vim_id=None):
        self.create_image()
        self.tacker_client = self.get_tk_http_client_by_user(username)
        self._set_grant_response(
            False, 'INSTANTIATE', glance_image=glance_image,
            flavour_vdu_dict=flavour_vdu_dict, zone_name_list=zone_name_list)
        instantiate_req = self.instantiate_vnf(area, vim_id, username=username,
                                               tenant=tenant)
        resp, body = self.instantiate_vnf_instance(inst_id, instantiate_req)
        self.assertEqual(expected_status_code, resp.status_code)
        if expected_status_code == 202:
            lcmocc_id = os.path.basename(resp.headers['Location'])
            self.wait_lcmocc_complete(lcmocc_id)

            # wait a bit because there is a bit time lag between lcmocc DB
            # update and instantiate completion.
            time.sleep(WAIT_LCMOCC_UPDATE_TIME)

    def _step_lcm_show(self, username, inst_id, expected_status_code):
        self.tacker_client = self.get_tk_http_client_by_user(username)
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(expected_status_code, resp.status_code)

    def _step_lcm_list(self, username, expected_inst_list):
        self.tacker_client = self.get_tk_http_client_by_user(username)
        resp, vnf_instances = self.list_vnf_instance()
        self.assertEqual(200, resp.status_code)
        inst_ids = set([inst.get('id') for inst in vnf_instances])
        for inst_id in expected_inst_list:
            self.assertIn(inst_id, inst_ids)

    def _step_lcm_heal(self, username, inst_id, glance_image, flavour_vdu_dict,
                       zone_name_list, expected_status_code):
        self.tacker_client = self.get_tk_http_client_by_user(username)
        self._set_grant_response(
            False, 'HEAL', glance_image=glance_image,
            flavour_vdu_dict=flavour_vdu_dict, zone_name_list=zone_name_list)

        heal_req = paramgen.heal_vnf_all_min()
        resp, body = self.heal_vnf_instance(inst_id, heal_req)
        self.assertEqual(expected_status_code, resp.status_code)
        if expected_status_code == 202:
            lcmocc_id = os.path.basename(resp.headers['Location'])
            self.wait_lcmocc_complete(lcmocc_id)
            time.sleep(WAIT_LCMOCC_UPDATE_TIME)

    def _step_lcm_update(self, username, inst_id, update_vnfd_id,
                         expected_status_code):
        self.tacker_client = self.get_tk_http_client_by_user(username)
        update_req = paramgen.update_vnf_min_with_parameter(update_vnfd_id)
        resp, body = self.update_vnf_instance(inst_id, update_req)
        self.assertEqual(expected_status_code, resp.status_code)
        if expected_status_code == 202:
            lcmocc_id = os.path.basename(resp.headers['Location'])
            self.wait_lcmocc_complete(lcmocc_id)

    def _step_lcm_scale_out(self, username, inst_id, glance_image,
                            flavour_vdu_dict, zone_name_list,
                            expected_status_code):
        self.tacker_client = self.get_tk_http_client_by_user(username)
        self._set_grant_response(
            False, 'SCALE', glance_image=glance_image,
            flavour_vdu_dict=flavour_vdu_dict, zone_name_list=zone_name_list)
        scaleout_req = paramgen.scaleout_vnf_min()
        resp, body = self.scale_vnf_instance(inst_id, scaleout_req)
        self.assertEqual(expected_status_code, resp.status_code)
        if expected_status_code == 202:
            lcmocc_id = os.path.basename(resp.headers['Location'])
            self.wait_lcmocc_complete(lcmocc_id)

    def _step_lcm_scale_in(self, username, inst_id, glance_image,
                    flavour_vdu_dict, zone_name_list, expected_status_code):
        self.tacker_client = self.get_tk_http_client_by_user(username)
        self._set_grant_response(
            False, 'SCALE', glance_image=glance_image,
            flavour_vdu_dict=flavour_vdu_dict, zone_name_list=zone_name_list)
        scalein_req = paramgen.scalein_vnf_min()
        resp, body = self.scale_vnf_instance(inst_id, scalein_req)
        self.assertEqual(expected_status_code, resp.status_code)
        if expected_status_code == 202:
            lcmocc_id = os.path.basename(resp.headers['Location'])
            self.wait_lcmocc_complete(lcmocc_id)

    def _step_lcm_change_vnfpkg(self, username, inst_id, change_vnfd_id,
                        glance_image, flavour_vdu_dict, expected_status_code):
        self.tacker_client = self.get_tk_http_client_by_user(username)
        change_vnfpkg_req = paramgen.change_vnfpkg_with_ext_vl(
            change_vnfd_id, self.get_network_ids(['net1']))

        del change_vnfpkg_req[
            "additionalParams"]["lcm-operation-coordinate-old-vnf"]
        del change_vnfpkg_req[
            "additionalParams"]["lcm-operation-coordinate-new-vnf"]
        self._set_grant_response(False, 'CHANGE_VNFPKG',
                                 glance_image=glance_image,
                                 flavour_vdu_dict=flavour_vdu_dict)

        resp, body = self.change_vnfpkg(inst_id, change_vnfpkg_req)
        self.assertEqual(expected_status_code, resp.status_code)
        if expected_status_code == 202:
            lcmocc_id = os.path.basename(resp.headers['Location'])
            self.wait_lcmocc_complete(lcmocc_id)

            # wait a bit because there is a bit time lag between lcmocc DB
            # update and change_vnfpkg completion.
            time.sleep(WAIT_LCMOCC_UPDATE_TIME)

    def _step_lcm_change_ext_conn(self, username, inst_id, tenant, area,
                                  zone_name_list, expected_status_code):
        self.tacker_client = self.get_tk_http_client_by_user(username)
        self._set_grant_response(
            False, 'CHANGE_EXT_CONN', zone_name_list=zone_name_list)

        # Create a new network and subnet to check the IP allocation of
        # IPv4 and IPv6
        ft_net0_name = 'ft-net0'
        ft_net0_subs = {
            'ft-ipv4-subnet0': {
                'range': '100.100.100.0/24',
                'ip_version': 4
            },
            'ft-ipv6-subnet0': {
                'range': '1111:2222:3333::/64',
                'ip_version': 6
            }
        }
        ft_net0_id = self.create_network(ft_net0_name)
        self.addCleanup(self.delete_network, ft_net0_id)
        for sub_name, val in ft_net0_subs.items():
            # subnet is automatically deleted with network deletion
            self.create_subnet(
                ft_net0_id, sub_name, val['range'], val['ip_version'])

        # Create a new network for change external connectivity
        ft_net1_name = 'ft-net1'
        ft_net1_subs = {
            'ft-ipv4-subnet1': {
                'range': '22.22.22.0/24',
                'ip_version': 4
            },
            'ft-ipv6-subnet1': {
                'range': '1111:2222:4444::/64',
                'ip_version': 6
            }
        }
        ft_net1_id = self.create_network(ft_net1_name)
        self.addCleanup(self.delete_network, ft_net1_id)
        for sub_name, val in ft_net1_subs.items():
            # subnet is automatically deleted with network deletion
            self.create_subnet(
                ft_net1_id, sub_name, val['range'], val['ip_version'])

        net_ids = self.get_network_ids(
            ['net0', 'net1', 'net_mgmt', 'ft-net0', 'ft-net1'])
        subnet_ids = self.get_subnet_ids(
            ['subnet0', 'subnet1', 'ft-ipv4-subnet0', 'ft-ipv6-subnet0',
             'ft-ipv4-subnet1', 'ft-ipv6-subnet1'])
        port_names = ['VDU2_CP1-1', 'VDU2_CP1-2']
        port_ids = {}
        for port_name in port_names:
            port_id = self.create_port(net_ids['net0'], port_name)
            port_ids[port_name] = port_id
            self.addCleanup(self.delete_port, port_id)

        change_ext_conn_req = self.change_ext_conn_max(
            net_ids, subnet_ids, self.auth_url, area, username=username,
            tenant=tenant)
        resp, body = self.change_ext_conn(inst_id, change_ext_conn_req)
        self.assertEqual(expected_status_code, resp.status_code)
        if expected_status_code == 202:
            lcmocc_id = os.path.basename(resp.headers['Location'])
            self.wait_lcmocc_complete(lcmocc_id)
            time.sleep(WAIT_LCMOCC_UPDATE_TIME)

    def _step_lcm_terminate(self, username, inst_id, expected_status_code):
        self.tacker_client = self.get_tk_http_client_by_user(username)
        self._set_grant_response(False, 'TERMINATE')
        terminate_req = paramgen.terminate_vnf_min()
        resp, body = self.terminate_vnf_instance(inst_id, terminate_req)
        self.assertEqual(expected_status_code, resp.status_code)
        if expected_status_code == 202:
            lcmocc_id = os.path.basename(resp.headers['Location'])
            self.wait_lcmocc_complete(lcmocc_id)

    def _step_lcm_delete(self, username, inst_id, expected_status_code):
        self.tacker_client = self.get_tk_http_client_by_user(username)
        resp, body = self.exec_lcm_operation(self.delete_vnf_instance,
                                             inst_id)
        self.assertEqual(expected_status_code, resp.status_code)

    def vnflcm_apis_v2_vnf_test_before_instantiate(self):
        # Create subscription
        self.tacker_client = self.get_tk_http_client_by_user('user_all')

        callback_url = os.path.join(self.get_notify_callback_url(),
                                    self._testMethodName)
        callback_uri = ('http://localhost:'
                        f'{self.get_server_port()}'
                        f'{callback_url}')

        sub_req = paramgen.sub_create_min(callback_uri)
        resp, body = self.create_subscription(sub_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        sub_id = body['id']

        # Test notification
        self.assert_notification_get(callback_url)
        # check usageState of VNF Package
        self.check_package_usage(self.vnf_pkg_a)

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

        return sub_id, inst_id_a, inst_id_b

    def vnflcm_apis_v2_vnf_test_after_instantiate(
            self, sub_id, inst_id_a, inst_id_b, zone_name_list, glance_image,
            flavour_vdu_dict):

        # step 15 LCM-ShowV2, Resource Group A / User Group A
        self._step_lcm_show('user_a', inst_id_a, 200)

        # step 16 LCM-ShowV2, Resource Group A / User Group A-1
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
        self._step_lcm_scale_out('user_a', inst_id_a, glance_image,
                                 flavour_vdu_dict, zone_name_list, 202)

        # step 24 LCM-ScaleV2(out), Resource Group B / User Group A
        self._step_lcm_scale_out('user_a', inst_id_b, glance_image,
                                 flavour_vdu_dict, zone_name_list, 403)

        # step 25 LCM-ScaleV2(out), Resource Group B / User Group all
        self._step_lcm_scale_out('user_all', inst_id_b, glance_image,
                                 flavour_vdu_dict, zone_name_list, 202)

        # step 26 LCM-ScaleV2(in), Resource Group A / User Group A
        self._step_lcm_scale_in('user_a', inst_id_a, glance_image,
                                flavour_vdu_dict, zone_name_list, 202)

        # step 27 LCM-ScaleV2(in), Resource Group B / User Group A
        self._step_lcm_scale_in('user_a', inst_id_b, glance_image,
                                flavour_vdu_dict, zone_name_list, 403)

        # step 28 LCM-ScaleV2(in), Resource Group B / User Group all
        self._step_lcm_scale_in('user_all', inst_id_b, glance_image,
                                flavour_vdu_dict, zone_name_list, 202)

        # step 29 LCM-HealV2, Resource Group A / User Group A
        self._step_lcm_heal('user_a', inst_id_a, glance_image,
                            flavour_vdu_dict, zone_name_list, 202)

        # step 30 LCM-HealV2, Resource Group B / User Group A
        self._step_lcm_heal('user_a', inst_id_b, glance_image,
                            flavour_vdu_dict, zone_name_list, 403)

        # step 31 LCM-HealV2, Resource Group B / User Group all
        self._step_lcm_heal('user_all', inst_id_b, glance_image,
                            flavour_vdu_dict, zone_name_list, 202)

        # step 32 LCM-ModifyV2, Resource Group A / User Group A
        self._step_lcm_update('user_a', inst_id_a, self.vnfd_id_a_1, 202)

        # step 33 LCM-ModifyV2, Resource Group b / User Group A
        self._step_lcm_update('user_a', inst_id_b, self.vnfd_id_b_1, 403)

        # step 34 LCM-ModifyV2, Resource Group B / User Group all
        self._step_lcm_update('user_all', inst_id_b, self.vnfd_id_b_1, 202)

        # step 35 LCM-Change-ConnectivityV2, Resource Group A / User Group A
        self._step_lcm_change_ext_conn('user_a', inst_id_a, 'tenant_A',
                                       'area_A@region_A', zone_name_list, 202)

        # step 36 LCM-Change-ConnectivityV2, Resource Group B / User Group A
        self._step_lcm_change_ext_conn('user_a', inst_id_b, 'tenant_B',
                                       'area_B@region_B', zone_name_list, 403)

        # step 37 LCM-Change-ConnectivityV2, Resource Group B / User Group all
        self._step_lcm_change_ext_conn('user_all', inst_id_b, 'tenant_B',
                                       'area_B@region_B', zone_name_list, 202)

        # step 38 LCM-Change-VnfPkgV2, Resource Group A / User Group A
        self._step_lcm_update('user_a', inst_id_a, self.vnfd_id_a, 202)
        self._step_lcm_change_vnfpkg('user_a', inst_id_a, self.vnfd_id_a_2,
                                     glance_image, flavour_vdu_dict, 202)

        # step 39 LCM-Change-VnfPkgV2, Resource Group B / User Group A
        self._step_lcm_change_vnfpkg('user_a', inst_id_b, self.vnfd_id_b_2,
                                     glance_image, flavour_vdu_dict, 403)

        # step 40 LCM-Change-VnfPkgV2, Resource Group B / User Group all
        self._step_lcm_update('user_all', inst_id_b, self.vnfd_id_b, 202)
        self._step_lcm_change_vnfpkg('user_all', inst_id_b, self.vnfd_id_b_2,
                                     glance_image, flavour_vdu_dict, 202)

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

        # Delete subscription
        resp, body = self.delete_subscription(sub_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        # Show subscription
        resp, body = self.show_subscription(sub_id)
        self.assertEqual(404, resp.status_code)


class VnflcmAPIsV2VNFInstantiateWithArea(VnflcmAPIsV2VNFBase):

    def test_vnflcm_apis_v2_vnf_with_area_in_vim_conn_info(self):
        glance_image = None
        flavour_vdu_dict = None
        zone_name_list = None

        sub_id, inst_id_a, inst_id_b = (
            self.vnflcm_apis_v2_vnf_test_before_instantiate())

        # step 12 LCM-InstantiateV2, Resource Group A / User Group A
        self._step_lcm_instantiate('user_a', inst_id_a, 'tenant_A',
                                   glance_image, flavour_vdu_dict,
                                   zone_name_list, 202, area='area_A@region_A')

        # step 13 LCM-InstantiateV2, Resource Group B / User Group A
        self._step_lcm_instantiate('user_a', inst_id_b, 'tenant_B',
                                   glance_image, flavour_vdu_dict,
                                   zone_name_list, 403, area='area_B@region_B')

        # step 14 LCM-InstantiateV2, Resource Group B / User Group all
        self._step_lcm_instantiate('user_all', inst_id_b, 'tenant_B',
                                   glance_image, flavour_vdu_dict,
                                   zone_name_list, 202, area='area_B@region_B')

        self.vnflcm_apis_v2_vnf_test_after_instantiate(
            sub_id, inst_id_a, inst_id_b, zone_name_list, glance_image,
            flavour_vdu_dict)


class VnflcmAPIsV2VNFInstantiateWithAreaInRegisteredVim(VnflcmAPIsV2VNFBase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        vim_type = 'openstack'

        local_vim = 'local-vim.yaml'

        cls.vim_a = cls._step_vim_register(
            'user_a', vim_type, local_vim, 'vim_a', 'area_A@region_A',
            tenant='tenant_A')

        cls.vim_a_1 = cls._step_vim_register(
            'user_a', vim_type, local_vim, 'vim_a_1', 'area_A@region_A',
            tenant='tenant_A')

        cls.vim_b = cls._step_vim_register(
            'user_b', vim_type, local_vim, 'vim_b', 'area_B@region_B',
            tenant='tenant_B')

        cls.vim_b_1 = cls._step_vim_register(
            'user_b', vim_type, local_vim, 'vim_b_1', 'area_B@region_B',
            tenant='tenant_B')

    @classmethod
    def tearDownClass(cls):

        cls._step_vim_delete('user_a', cls.vim_a)
        cls._step_vim_delete('user_a', cls.vim_a_1)
        cls._step_vim_delete('user_b', cls.vim_b)
        cls._step_vim_delete('user_b', cls.vim_b_1)

        super().tearDownClass()

    def test_vnflcm_apis_v2_vnf_with_area_in_registered_vim(self):

        glance_image = None
        flavour_vdu_dict = None
        zone_name_list = None

        sub_id, inst_id_a, inst_id_b = (
            self.vnflcm_apis_v2_vnf_test_before_instantiate())

        # step 12 LCM-InstantiateV2, Resource Group A / User Group A
        self._step_lcm_instantiate('user_a', inst_id_a, 'tenant_A',
                                   glance_image,
                                   flavour_vdu_dict, zone_name_list, 202,
                                   vim_id=self.vim_a['id'])

        # step 13 LCM-InstantiateV2, Resource Group B / User Group A
        self._step_lcm_instantiate('user_a', inst_id_b, 'tenant_B',
                                   glance_image,
                                   flavour_vdu_dict, zone_name_list, 403,
                                   vim_id=self.vim_b['id'])

        # step 14 LCM-InstantiateV2, Resource Group B / User Group all
        self._step_lcm_instantiate('user_all', inst_id_b, 'tenant_B',
                                   glance_image,
                                   flavour_vdu_dict, zone_name_list, 202,
                                   vim_id=self.vim_b['id'])

        self.vnflcm_apis_v2_vnf_test_after_instantiate(
            sub_id, inst_id_a, inst_id_b, zone_name_list, glance_image,
            flavour_vdu_dict)


class VnflcmAPIsV2VNFInstantiateWithoutArea(VnflcmAPIsV2VNFBase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        vim_type = 'openstack'

        local_vim = 'local-vim.yaml'

        cls.vim_c = cls._step_vim_register(
            'user_c', vim_type, local_vim, 'vim_c', None,
            tenant='tenant_C')

        cls.vim_c_1 = cls._step_vim_register(
            'user_c', vim_type, local_vim, 'vim_c_1', None,
            tenant='tenant_C')

    @classmethod
    def tearDownClass(cls):

        cls._step_vim_delete('user_admin', cls.vim_c)
        cls._step_vim_delete('user_admin', cls.vim_c_1)

        super().tearDownClass()

    def test_vnflcm_apis_v2_vnf_without_area(self):

        glance_image = None
        flavour_vdu_dict = None
        zone_name_list = None

        # Create subscription
        self.tacker_client = self.get_tk_http_client_by_user('user_all')

        callback_url = os.path.join(self.get_notify_callback_url(),
                                    self._testMethodName)
        callback_uri = ('http://localhost:'
                        f'{self.get_server_port()}'
                        f'{callback_url}')

        sub_req = paramgen.sub_create_min(callback_uri)
        resp, body = self.create_subscription(sub_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        sub_id = body['id']

        # Test notification
        self.assert_notification_get(callback_url)
        # check usageState of VNF Package
        self.check_package_usage(self.vnf_pkg_c)

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
        self._step_lcm_instantiate('user_c', inst_id_c, 'tenant_C',
                                   glance_image,
                                   flavour_vdu_dict, zone_name_list, 202,
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
        self._step_lcm_scale_out('user_c', inst_id_c, glance_image,
                                 flavour_vdu_dict, zone_name_list, 403)

        # step 16 LCM-ScaleV2(out), Resource Group C / User Group all
        self._step_lcm_scale_out('user_all', inst_id_c, glance_image,
                                 flavour_vdu_dict, zone_name_list, 403)

        # step 17 LCM-ScaleV2(out), Resource Group C / User Group admin
        self._step_lcm_scale_out('user_admin', inst_id_c, glance_image,
                                 flavour_vdu_dict, zone_name_list, 202)

        # step 18 LCM-ScaleV2(in), Resource Group C / User Group C
        self._step_lcm_scale_in('user_c', inst_id_c, glance_image,
                                flavour_vdu_dict, zone_name_list, 403)

        # step 19 LCM-ScaleV2(in), Resource Group C / User Group A
        self._step_lcm_scale_in('user_all', inst_id_c, glance_image,
                                flavour_vdu_dict, zone_name_list, 403)

        # step 20 LCM-ScaleV2(in), Resource Group C / User Group all
        self._step_lcm_scale_in('user_admin', inst_id_c, glance_image,
                                flavour_vdu_dict, zone_name_list, 202)

        # step 21 LCM-HealV2, Resource Group C / User Group C
        self._step_lcm_heal('user_c', inst_id_c, glance_image,
                            flavour_vdu_dict, zone_name_list, 403)

        # step 22 LCM-HealV2, Resource Group C / User Group A
        self._step_lcm_heal('user_all', inst_id_c, glance_image,
                            flavour_vdu_dict, zone_name_list, 403)

        # step 23 LCM-HealV2, Resource Group C / User Group all
        self._step_lcm_heal('user_admin', inst_id_c, glance_image,
                            flavour_vdu_dict, zone_name_list, 202)

        # step 24 LCM-ModifyV2, Resource Group C / User Group C
        self._step_lcm_update('user_c', inst_id_c, self.vnfd_id_c_1, 403)

        # step 25 LCM-ModifyV2, Resource Group C / User Group A
        self._step_lcm_update('user_all', inst_id_c, self.vnfd_id_c_1, 403)

        # step 26 LCM-ModifyV2, Resource Group C / User Group all
        self._step_lcm_update('user_admin', inst_id_c, self.vnfd_id_c_1, 202)

        # step 27 LCM-Change-ConnectivityV2, Resource Group C / User Group C
        self._step_lcm_change_ext_conn(
            'user_c', inst_id_c, 'tenant_C', None, zone_name_list, 403)

        # step 28 LCM-Change-ConnectivityV2, Resource Group C / User Group A
        self._step_lcm_change_ext_conn(
            'user_all', inst_id_c, 'tenant_C', None, zone_name_list, 403)

        # step 29 LCM-Change-ConnectivityV2, Resource Group C / User Group all
        self._step_lcm_change_ext_conn(
            'user_admin', inst_id_c, 'tenant_C', None, zone_name_list, 202)

        # step 30 LCM-Change-VnfPkgV2, Resource Group C / User Group C
        self._step_lcm_change_vnfpkg('user_c', inst_id_c, self.vnfd_id_c_2,
                                     glance_image, flavour_vdu_dict, 403)

        # step 31 LCM-Change-VnfPkgV2, Resource Group C / User Group A
        self._step_lcm_change_vnfpkg('user_all', inst_id_c, self.vnfd_id_c_2,
                                     glance_image, flavour_vdu_dict, 403)

        # step 32 LCM-Change-VnfPkgV2, Resource Group C / User Group all
        self._step_lcm_update('user_admin', inst_id_c, self.vnfd_id_c, 202)
        self._step_lcm_change_vnfpkg('user_admin', inst_id_c, self.vnfd_id_c_2,
                                     glance_image, flavour_vdu_dict, 202)

        # step 33 LCM-TerminateV2, Resource Group C / User Group C
        self._step_lcm_terminate('user_c', inst_id_c, 403)

        # step 34 LCM-TerminateV2, Resource Group C / User Group A
        self._step_lcm_terminate('user_all', inst_id_c, 403)

        # step 35 LCM-TerminateV2, Resource Group C / User Group all
        self._step_lcm_terminate('user_admin', inst_id_c, 202)

        # step 36 LCM-DeleteV2, Resource Group C / User Group C
        self._step_lcm_delete('user_c', inst_id_c, 204)

        # Delete subscription
        resp, body = self.delete_subscription(sub_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        # Show subscription
        resp, body = self.show_subscription(sub_id)
        self.assertEqual(404, resp.status_code)
