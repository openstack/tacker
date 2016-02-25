# Copyright 2015 Brocade Communications System, Inc.
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
import os


def _get_template(name):
    filename = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "../vm/infra_drivers/heat/data/", name)
    f = codecs.open(filename, encoding='utf-8', errors='strict')
    return f.read()

vnfd_openwrt = _get_template('openwrt.yaml')
vnfd_ipparams_template = _get_template('vnf_cirros_template_ipaddr.yaml')
ipparams = _get_template('vnf_cirros_param_values_ipaddr.yaml')
vnfd_userdata_template = _get_template('vnf_cirros_template_user_data.yaml')
userdata_params = _get_template('vnf_cirros_param_values_user_data.yaml')
config_data = _get_template('config_data.yaml')


def get_dummy_vnfd_obj():
    return {u'vnfd': {u'service_types': [{u'service_type': u'vnfd'}],
                      'name': 'dummy_vnfd',
                      'tenant_id': u'ad7ebc56538745a08ef7c5e97f8bd437',
                      u'mgmt_driver': u'noop',
                      u'infra_driver': u'fake_driver',
                      u'attributes': {u'vnfd': vnfd_openwrt},
                      'description': 'dummy_vnfd_description'},
            u'auth': {u'tenantName': u'admin', u'passwordCredentials': {
                u'username': u'admin', u'password': u'devstack'}}}


def get_dummy_vnf_obj():
    return {'vnf': {'description': 'dummy_vnf_description',
                    'vnfd_id': u'eb094833-995e-49f0-a047-dfb56aaf7c4e',
                    'vim_id': u'6261579e-d6f3-49ad-8bc3-a9cb974778ff',
                    'tenant_id': u'ad7ebc56538745a08ef7c5e97f8bd437',
                    'name': 'dummy_vnf',
                    'attributes': {}}}


def get_dummy_vnf_config_obj():
    return {'vnf': {u'attributes': {u'config': {'vdus': {'vdu1': {
        'config': {'firewall': 'dummy_firewall_values'}}}}}}}


def get_dummy_device_obj():
    return {'status': 'PENDING_CREATE', 'instance_id': None, 'name':
        u'test_openwrt', 'tenant_id': u'ad7ebc56538745a08ef7c5e97f8bd437',
        'template_id': u'eb094833-995e-49f0-a047-dfb56aaf7c4e',
        'device_template': {'service_types': [{'service_type': u'vnfd',
            'id': u'4a4c2d44-8a52-4895-9a75-9d1c76c3e738'}],
            'description': u'OpenWRT with services',
            'tenant_id': u'ad7ebc56538745a08ef7c5e97f8bd437',
            'mgmt_driver': u'openwrt',
            'infra_driver': u'heat',
            'attributes': {u'vnfd': vnfd_openwrt},
            'id': u'fb048660-dc1b-4f0f-bd89-b023666650ec',
            'name': u'openwrt_services'},
        'mgmt_url': None, 'service_context': [],
        'attributes': {u'param_values': u''},
        'id': 'eb84260e-5ff7-4332-b032-50a14d6c1123',
        'description': u'OpenWRT with services'}


def get_dummy_device_obj_config_attr():
    return {'status': 'PENDING_CREATE', 'instance_id': None, 'name':
        u'test_openwrt', 'tenant_id': u'ad7ebc56538745a08ef7c5e97f8bd437',
        'template_id': u'eb094833-995e-49f0-a047-dfb56aaf7c4e',
        'device_template': {'service_types': [{'service_type': u'vnfd',
            'id': u'4a4c2d44-8a52-4895-9a75-9d1c76c3e738'}],
            'description': u'OpenWRT with services',
            'tenant_id': u'ad7ebc56538745a08ef7c5e97f8bd437',
            'mgmt_driver': u'openwrt',
            'infra_driver': u'heat',
            'attributes': {u'vnfd': vnfd_openwrt},
            'id': u'fb048660-dc1b-4f0f-bd89-b023666650ec', 'name':
            u'openwrt_services'}, 'mgmt_url': None, 'service_context': [],
            'attributes': {u'config': config_data},
            'id': 'eb84260e-5ff7-4332-b032-50a14d6c1123',
            'description': u'OpenWRT with services'}


def get_dummy_device_update_config_attr():
    return {'device': {u'attributes': {u'config': u"vdus:\n  vdu1:\n    "
                                                  u"config:\n      firewall: |"
                                                  u"\n        package firewall"
                                                  u"\n\n        config default"
                                                  u"s\n                "
                                                  u"option syn_flood '10'\n   "
                                                  u"             option input "
                                                  u"'REJECT'\n                "
                                                  u"option output 'REJECT'\n  "
                                                  u"              option "
                                                  u"forward 'REJECT'\n"}}}


def get_dummy_device_obj_ipaddr_attr():
    return {'status': 'PENDING_CREATE',
        'device_template': {'service_types':
            [{'service_type': u'vnfd', 'id':
                u'16f8b3f7-a9ff-4338-bbe5-eee48692c468'}, {'service_type':
                u'router', 'id': u'58878cb7-689f-47a5-9c2d-654e49e2357f'},
             {'service_type': u'firewall', 'id':
                 u'd016144f-42a6-44f4-93f6-52d201998916'}],
            'description': u'Parameterized VNF descriptor for IP addresses',
            'tenant_id': u'4dd6c1d7b6c94af980ca886495bcfed0',
            'mgmt_driver': u'noop',
            'infra_driver': u'heat',
            'attributes': {u'vnfd': vnfd_ipparams_template},
            'id': u'24c31ea1-2e28-4de2-a6cb-8d389a502c75', 'name': u'ip_vnfd'},
        'name': u'test_ip',
        'tenant_id': u'8273659b56fc46b68bd05856d1f08d14',
        'id': 'd1337add-d5a1-4fd4-9447-bb9243c8460b',
        'instance_id': None, 'mgmt_url': None, 'service_context': [],
        'services': [],
        'attributes': {u'param_values': ipparams},
        'template_id': u'24c31ea1-2e28-4de2-a6cb-8d389a502c75',
        'description': u'Parameterized VNF descriptor for IP addresses'}


def get_dummy_device_obj_userdata_attr():
    return {'status': 'PENDING_CREATE', 'instance_id': None,
        'name': u'test_userdata',
        'tenant_id': u'8273659b56fc46b68bd05856d1f08d14',
        'template_id': u'206e343f-c580-4494-a739-525849edab7f',
        'device_template': {'service_types': [{'service_type': u'firewall',
            'id': u'1fcc2d7c-a6b6-4263-8cac-9590f059a555'}, {'service_type':
            u'router', 'id': u'8c99106d-826f-46eb-91a1-08dfdc78c04b'},
            {'service_type': u'vnfd', 'id':
                u'9bf289ec-c0e1-41fc-91d7-110735a70221'}],
            'description': u"Parameterized VNF descriptor",
            'tenant_id': u'8273659b56fc46b68bd05856d1f08d14',
            'mgmt_driver': u'noop',
            'infra_driver': u'heat',
            'attributes': {u'vnfd': vnfd_userdata_template},
            'id': u'206e343f-c580-4494-a739-525849edab7f', 'name':
            u'cirros_user_data'}, 'mgmt_url': None, 'service_context': [],
            'services': [], 'attributes': {u'param_values': userdata_params},
            'id': '18685f68-2b2a-4185-8566-74f54e548811',
            'description': u"Parameterized VNF descriptor"}


def get_vim_auth_obj():
    return {'username': 'test_user', 'password': 'test_password',
            'project_id': None, 'project_name': 'test_project',
            'auth_url': 'http://localhost:5000/v3', 'user_domain_id':
                'default', 'project_domain_id': 'default'}
