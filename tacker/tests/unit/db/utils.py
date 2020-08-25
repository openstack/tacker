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
from datetime import datetime
import os
import yaml


DUMMY_NS_2_NAME = 'dummy_ns_2'


def _get_template(name):
    filename = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "../vnfm/infra_drivers/openstack/data/", name)
    f = codecs.open(filename, encoding='utf-8', errors='strict')
    return f.read()


tosca_cvnf_vnfd = _get_template('test_tosca_cvnf.yaml')
tosca_vnfd_openwrt = _get_template('test_tosca_openwrt.yaml')
tosca_vnfd_openwrt_param = _get_template('test_tosca_openwrt_param.yaml')
tosca_invalid_vnfd = _get_template('test_tosca_parser_failure.yaml')
etsi_vnfd = _get_template('etsi_nfv/tosca_vnfd.yaml')
config_data = _get_template('config_data.yaml')
update_config_data = _get_template('update_config_data.yaml')
hot_data = _get_template('hot_data.yaml')
param_data = _get_template('param_data.yaml')
update_param_data = _get_template('update_param_data.yaml')
update_invalid_param_data = _get_template('update_invalid_param_data.yaml')
update_new_param_data = _get_template('update_new_param_data.yaml')
vnffg_params = _get_template('vnffg_params.yaml')
vnffg_multi_params = _get_template('vnffg_multi_params.yaml')
vnffgd_template = yaml.safe_load(_get_template('vnffgd_template.yaml'))
vnffgd_tosca_template = yaml.safe_load(_get_template(
    'tosca_vnffgd_template.yaml'))
vnffgd_tosca_no_classifier_template = yaml.safe_load(_get_template(
    'tosca_vnffgd_no_classifier_template.yaml'))
vnffgd_tosca_template_for_update = yaml.safe_load(_get_template(
    'tosca_vnffgd_template_for_update.yaml'))
vnffgd_legacy_template = yaml.safe_load(_get_template(
    'tosca_vnffgd_legacy_template_for_update.yaml'))
vnffgd_tosca_param_template = yaml.safe_load(_get_template(
    'tosca_vnffgd_param_template.yaml'))
vnffgd_tosca_str_param_template = yaml.safe_load(_get_template(
    'tosca_vnffgd_str_param_template.yaml'))
vnffgd_tosca_multi_param_template = yaml.safe_load(_get_template(
    'tosca_vnffgd_multi_param_template.yaml'))
vnffgd_invalid_tosca_template = yaml.safe_load(_get_template(
    'tosca_invalid_vnffgd_template.yaml'))
vnffgd_tosca_dupl_criteria_template = yaml.safe_load(_get_template(
    'tosca_vnffgd_dupl_criteria_template.yaml'))
vnfd_scale_tosca_template = _get_template('tosca_scale.yaml')
vnfd_alarm_respawn_tosca_template = _get_template(
    'test_tosca_vnfd_alarm_respawn.yaml')
vnfd_alarm_scale_tosca_template = _get_template(
    'test_tosca_vnfd_alarm_scale.yaml')
vnfd_alarm_multi_actions_tosca_template = _get_template(
    'test_tosca_vnfd_alarm_multi_actions.yaml')
nsd_tosca_template = yaml.safe_load(_get_template('tosca_nsd_template.yaml'))
vnffgd_wrong_cp_number_template = yaml.safe_load(_get_template(
    'tosca_vnffgd_wrong_cp_number_template.yaml'))
vnfd_instance_reservation_alarm_scale_tosca_template = _get_template(
    'test_tosca-vnfd-instance-reservation.yaml')
hot_grant = _get_template('hot_grant.yaml')
hot_scale_grant = _get_template('hot_scale_grant.yaml')
hot_scale_nest_grant = _get_template('hot_scale_nest_grant.yaml')
hot_scale_initial = _get_template('hot_scale_initial.yaml')
hot_scale_nest_initial = _get_template('hot_scale_nest_initial.yaml')


def get_dummy_vnfd_obj():
    return {u'vnfd': {u'service_types': [{u'service_type': u'vnfd'}],
                      'name': 'dummy_vnfd',
                      'tenant_id': u'ad7ebc56538745a08ef7c5e97f8bd437',
                      u'attributes': {u'vnfd': yaml.safe_load(
                          tosca_vnfd_openwrt)},
                      'description': 'dummy_vnfd_description',
                      'template_source': 'onboarded',
            u'auth': {u'tenantName': u'admin', u'passwordCredentials': {
                u'username': u'admin', u'password': u'devstack'}}}}


def get_invalid_vnfd_obj():
    return {u'vnfd': {u'service_types': [{u'service_type': u'vnfd'}],
                      'name': 'dummy_vnfd',
                      'tenant_id': u'ad7ebc56538745a08ef7c5e97f8bd437',
                      u'attributes': {u'vnfd': yaml.safe_load(
                          tosca_invalid_vnfd)},
                      'description': 'dummy_vnfd_description',
                      'template_source': 'onboarded',
            u'auth': {u'tenantName': u'admin', u'passwordCredentials': {
                u'username': u'admin', u'password': u'devstack'}}}}


def get_dummy_vnfd_obj_inline():
    return {u'vnfd': {u'service_types': [{u'service_type': u'vnfd'}],
                      'name': 'tmpl-koeak4tqgoqo8cr4-dummy_inline_vnf',
                      'tenant_id': u'ad7ebc56538745a08ef7c5e97f8bd437',
                      u'attributes': {u'vnfd': yaml.safe_load(
                          tosca_vnfd_openwrt)},
                      'template_source': 'inline',
            u'auth': {u'tenantName': u'admin', u'passwordCredentials': {
                u'username': u'admin', u'password': u'devstack'}}}}


def get_dummy_inline_vnf_obj():
    return {'vnf': {'description': 'dummy_inline_vnf_description',
                    'vnfd_template': yaml.safe_load(tosca_vnfd_openwrt),
                    'vim_id': u'6261579e-d6f3-49ad-8bc3-a9cb974778ff',
                    'tenant_id': u'ad7ebc56538745a08ef7c5e97f8bd437',
                    'name': 'dummy_inline_vnf',
                    'attributes': {},
                    'vnfd_id': None}}


def get_dummy_inline_cvnf_obj():
    return {'vnf': {'description': 'dummy_inline_cvnf_description',
                    'vnfd_template': yaml.safe_load(tosca_cvnf_vnfd),
                    'vim_id': u'6261579e-d6f3-49ad-8bc3-a9cb974778ff',
                    'tenant_id': u'ad7ebc56538745a08ef7c5e97f8bd437',
                    'name': 'dummy_cvnf',
                    'attributes': {},
                    'vnfd_id': None}}


def get_dummy_vnf_obj():
    return {'vnf': {'description': 'dummy_vnf_description',
                    'vnfd_id': u'eb094833-995e-49f0-a047-dfb56aaf7c4e',
                    'vim_id': u'6261579e-d6f3-49ad-8bc3-a9cb974778ff',
                    'tenant_id': u'ad7ebc56538745a08ef7c5e97f8bd437',
                    'name': 'dummy_vnf',
                    'deleted_at': datetime.min,
                    'attributes': {},
                    'vnfd_template': None}}


def get_dummy_vnf_config_obj():
    return {'vnf': {u'attributes': {u'config': {'vdus': {'vdu1': {
        'config': {'firewall': 'dummy_firewall_values'}}}}}}}


def get_dummy_vnf_invalid_config_type_obj():
    return {'vnf': {u'attributes': {u'config': 'dummy_config'}}}


def get_dummy_vnf_invalid_param_content():
    return {'vnf': {u'attributes': {u'param_values': {}}}}


def get_dummy_vnf_param_obj():
    return {'vnf': {u'attributes': {u'param_values':
        {'flavor': 'm1.tiny',
         'reservation_id': '99999999-3925-4c9e-9074-239a902b68d7'}}}}


def get_dummy_vnf_invalid_param_type_obj():
    return {'vnf': {u'attributes': {u'param_values': 'dummy_param'}}}


def get_dummy_vnf(status='PENDING_CREATE', scaling_group=False,
                  instance_id=None):
    dummy_vnf = {'status': status, 'instance_id': instance_id, 'name':
        u'test_openwrt', 'tenant_id': u'ad7ebc56538745a08ef7c5e97f8bd437',
        'vnfd_id': u'eb094833-995e-49f0-a047-dfb56aaf7c4e',
        'vnfd': {
            'service_types': [{'service_type': u'vnfd',
            'id': u'4a4c2d44-8a52-4895-9a75-9d1c76c3e738'}],
            'description': u'OpenWRT with services',
            'tenant_id': u'ad7ebc56538745a08ef7c5e97f8bd437',
            'mgmt_driver': u'openwrt',
            'attributes': {u'vnfd': tosca_vnfd_openwrt},
            'id': u'fb048660-dc1b-4f0f-bd89-b023666650ec',
            'name': u'openwrt_services'},
        'mgmt_ip_address': None, 'service_context': [],
        'attributes': {u'param_values': u''},
        'id': 'eb84260e-5ff7-4332-b032-50a14d6c1123',
        'description': u'OpenWRT with services'}
    if scaling_group:
        dummy_vnf['attributes'].update({'scaling_group_names':
                                   '{"SP1": "SP1_group"}',
                                   'heat_template': 'test'})
    return dummy_vnf


def get_dummy_vnf_test(status='PENDING_CREATE', scaling_group=False,
                  instance_id=None):
    dummy_vnf = {'status': status, 'instance_id': instance_id, 'name':
        u'test_openwrt', 'tenant_id': u'ad7ebc56538745a08ef7c5e97f8bd437',
        'vnfd_id': u'eb094833-995e-49f0-a047-dfb56aaf7c4e',
        'vnfd': {
            'service_types': [{'service_type': u'vnfd',
            'id': u'4a4c2d44-8a52-4895-9a75-9d1c76c3e738'}],
            'description': u'OpenWRT with services',
            'tenant_id': u'ad7ebc56538745a08ef7c5e97f8bd437',
            'mgmt_driver': u'openwrt',
            'attributes': {u'vnfd_simple': tosca_vnfd_openwrt},
            'id': u'fb048660-dc1b-4f0f-bd89-b023666650ec',
            'name': u'openwrt_services'},
        'mgmt_ip_address': None, 'service_context': [],
        'attributes': {u'param_values': u''},
        'id': 'eb84260e-5ff7-4332-b032-50a14d6c1123',
        'description': u'OpenWRT with services'}
    if scaling_group:
        dummy_vnf['attributes'].update({'scaling_group_names':
                                   '{"SP1": "SP1_group"}',
                                   'heat_template': 'test'})
    return dummy_vnf


def get_dummy_vnf_etsi(status='PENDING_CREATE', scaling_group=False,
                       instance_id=None, flavour='Simple'):
    vnfd_key = 'vnfd_' + flavour
    dummy_vnf = {'status': status, 'instance_id': instance_id, 'name':
        u'test_openwrt', 'tenant_id': u'ad7ebc56538745a08ef7c5e97f8bd437',
        'vnfd_id': u'eb094833-995e-49f0-a047-dfb56aaf7c4e',
        'vnfd': {
            'service_types': [{'service_type': u'vnfd',
            'id': u'4a4c2d44-8a52-4895-9a75-9d1c76c3e738'}],
            'description': u'OpenWRT with services',
            'tenant_id': u'ad7ebc56538745a08ef7c5e97f8bd437',
            'mgmt_driver': u'openwrt',
            'attributes': {vnfd_key: etsi_vnfd},
            'id': u'fb048660-dc1b-4f0f-bd89-b023666650ec',
            'name': u'openwrt_services'},
        'mgmt_ip_address': None, 'service_context': [],
        'attributes': {u'param_values': u''},
        'id': 'eb84260e-5ff7-4332-b032-50a14d6c1123',
        'description': u'OpenWRT with services'}
    if scaling_group:
        dummy_vnf['attributes'].update({'scaling_group_names':
                                   '{"SP1": "SP1_group"}',
                                   'heat_template': 'test'})
    return dummy_vnf


def get_dummy_vnf_config_attr():
    return {'status': 'PENDING_CREATE', 'instance_id': None, 'name':
        u'test_openwrt', 'tenant_id': u'ad7ebc56538745a08ef7c5e97f8bd437',
        'vnfd_id': u'eb094833-995e-49f0-a047-dfb56aaf7c4e',
        'vnfd': {'service_types': [{'service_type': u'vnfd',
            'id': u'4a4c2d44-8a52-4895-9a75-9d1c76c3e738'}],
            'description': u'OpenWRT with services',
            'tenant_id': u'ad7ebc56538745a08ef7c5e97f8bd437',
            'mgmt_driver': u'openwrt',
            'attributes': {u'vnfd': tosca_vnfd_openwrt},
            'id': u'fb048660-dc1b-4f0f-bd89-b023666650ec', 'name':
            u'openwrt_services'}, 'mgmt_ip_address': None,
            'service_context': [],
            'attributes': {u'config': config_data},
            'id': 'eb84260e-5ff7-4332-b032-50a14d6c1123',
            'description': u'OpenWRT with services'}


def get_dummy_vnf_param_attr():
    return {'status': 'PENDING_CREATE', 'instance_id': None, 'name':
        u'test_openwrt', 'tenant_id': u'ad7ebc56538745a08ef7c5e97f8bd437',
        'vnfd_id': u'eb094833-995e-49f0-a047-dfb56aaf7c4e',
        'vnfd': {'service_types': [{'service_type': u'vnfd',
            'id': u'4a4c2d44-8a52-4895-9a75-9d1c76c3e738'}],
            'description': u'OpenWRT with services',
            'tenant_id': u'ad7ebc56538745a08ef7c5e97f8bd437',
            'mgmt_driver': u'openwrt',
            'attributes': {u'vnfd': tosca_vnfd_openwrt_param},
            'id': u'fb048660-dc1b-4f0f-bd89-b023666650ec',
            'name': u'openwrt_services'},
        'mgmt_url': None, 'service_context': [],
        'attributes': {'heat_template': hot_data,
                       'param_values': param_data},
        'id': 'eb84260e-5ff7-4332-b032-50a14d6c1123',
        'description': u'OpenWRT with services'}


def get_dummy_vnf_update_config():
    return {'vnf': {'attributes': {'config': update_config_data}}}


def get_dummy_vnf_update_param():
    return {'vnf': {'attributes': {'param_values': update_param_data}}}


def get_dummy_vnf_update_new_param():
    return {'vnf': {'attributes': {'param_values': update_new_param_data}}}


def get_dummy_vnf_update_invalid_param():
    return {'vnf': {'attributes': {'param_values': update_invalid_param_data}}}


def get_dummy_vnf_update_empty_param():
    return {'vnf': {'attributes': {'param_values': {}}}}


def get_vim_obj():
    return {'vim': {'type': 'openstack',
                    'auth_url': 'http://localhost/identity',
                    'vim_project': {'name': 'test_project'},
                    'auth_cred': {'username': 'test_user',
                                  'password': 'test_password',
                                  'cert_verify': 'True'},
                    'name': 'VIM0',
                    'tenant_id': 'test-project'}}


def get_vim_auth_obj():
    return {'username': 'test_user',
            'password': 'test_password',
            'project_id': None,
            'project_name': 'test_project',
            'cert_verify': 'True',
            'auth_url': 'http://localhost/identity/v3',
            'user_domain_name': 'default',
            'project_domain_name': 'default'}


def get_dummy_vnffgd_obj():
    return {u'vnffgd': {'name': 'dummy_vnffgd',
                        'tenant_id': u'ad7ebc56538745a08ef7c5e97f8bd437',
                        u'template': {u'vnffgd': vnffgd_tosca_template},
                        'description': 'dummy_vnffgd_description',
                        'template_source': 'onboarded'}}


def get_dummy_vnffgd_obj_inline():
    return {u'vnffgd': {'name': 'dummy_vnffgd_inline',
                        'tenant_id': u'ad7ebc56538745a08ef7c5e97f8bd437',
                        u'template': {u'vnffgd': vnffgd_tosca_template},
                        'description': 'dummy_vnffgd_description_inline',
                        'template_source': 'inline'}}


def get_dummy_vnffgd_obj_no_description():
    return {u'vnffgd': {'name': 'dummy_vnffgd',
                        'tenant_id': u'ad7ebc56538745a08ef7c5e97f8bd437',
                        u'template': {u'vnffgd': vnffgd_tosca_template},
                        'template_source': 'onboarded'}}


def get_dummy_vnffgd_obj_no_name():
    return {u'vnffgd': {'tenant_id': u'ad7ebc56538745a08ef7c5e97f8bd437',
                        u'template': {u'vnffgd': vnffgd_tosca_template},
                        'description': 'dummy_vnffgd_description',
                        'template_source': 'onboarded'}}


def get_dummy_vnffg_obj():
    return {'vnffg': {'description': 'dummy_vnffg_description',
                      'vnffgd_id': u'eb094833-995e-49f0-a047-dfb56aaf7c4e',
                      'tenant_id': u'ad7ebc56538745a08ef7c5e97f8bd437',
                      'name': 'dummy_vnffg',
                      u'attributes': {u'template': vnffgd_tosca_template},
                      'vnf_mapping': {},
                      'symmetrical': False}}


def get_dummy_vnffg_no_classifier_obj():
    return {'vnffg': {'description': 'dummy_vnffg_no_classifier_description',
                      'vnffgd_id': u'eb094833-995e-49f0-a047-dfb56aaf7c4e',
                      'tenant_id': u'ad7ebc56538745a08ef7c5e97f8bd437',
                      'name': 'dummy_vnffg',
                      u'attributes': {
                          u'template': vnffgd_tosca_no_classifier_template},
                      'vnf_mapping': {},
                      'symmetrical': False}}


def get_dummy_vnffg_obj_inline():
    return {'vnffg': {'description': 'dummy_vnffg_description_inline',
                      'tenant_id': u'ad7ebc56538745a08ef7c5e97f8bd437',
                      'name': 'dummy_vnffg_inline',
                      u'attributes': {u'template': vnffgd_tosca_template},
                      'vnf_mapping': {},
                      'symmetrical': False,
                      'vnffgd_template': vnffgd_tosca_template}}


def get_dummy_vnffg_obj_update_vnffgd_template():
    return {'vnffg': {'tenant_id': u'ad7ebc56538745a08ef7c5e97f8bd437',
                      'name': 'dummy_vnffg',
                      'symmetrical': False,
                      'vnffgd_template': vnffgd_tosca_template_for_update}}


def get_dummy_vnffg_obj_legacy_vnffgd_template():
    return {'vnffg': {'tenant_id': u'ad7ebc56538745a08ef7c5e97f8bd437',
                      'name': 'dummy_vnffg',
                      'symmetrical': False,
                      'vnffgd_template': vnffgd_legacy_template}}


def get_dummy_vnffg_param_obj():
    return {'vnffg': {'description': 'dummy_vnf_description',
                      'vnffgd_id': u'eb094833-995e-49f0-a047-dfb56aaf7c4e',
                      'tenant_id': u'ad7ebc56538745a08ef7c5e97f8bd437',
                      'name': 'dummy_vnffg',
                      u'attributes': {
                          u'template': vnffgd_tosca_param_template,
                          u'param_values':
                              yaml.safe_load(vnffg_params)
                      },
                      'vnf_mapping': {},
                      'symmetrical': False}}


def get_dummy_vnffg_str_param_obj():
    return {'vnffg': {'description': 'dummy_vnf_description',
                      'vnffgd_id': u'eb094833-995e-49f0-a047-dfb56aaf7c4e',
                      'tenant_id': u'ad7ebc56538745a08ef7c5e97f8bd437',
                      'name': 'dummy_vnffg',
                      u'attributes': {
                          u'template': vnffgd_tosca_param_template,
                          u'param_values': 'value not dict format'},
                      'vnf_mapping': {},
                      'symmetrical': False}}


def get_dummy_vnffg_multi_param_obj():
    return {'vnffg': {'description': 'dummy_vnf_description',
                      'vnffgd_id': u'eb094833-995e-49f0-a047-dfb56aaf7c4e',
                      'tenant_id': u'ad7ebc56538745a08ef7c5e97f8bd437',
                      'name': 'dummy_vnffg',
                      u'attributes': {
                          u'template': vnffgd_tosca_multi_param_template,
                          u'param_values':
                              yaml.safe_load(vnffg_multi_params)
                      },
                      'vnf_mapping': {},
                      'symmetrical': False}}


def get_dummy_vnffg_obj_vnf_mapping():
    return {'vnffg': {'description': 'dummy_vnf_description',
                      'vnffgd_id': u'eb094833-995e-49f0-a047-dfb56aaf7c4e',
                      'tenant_id': u'ad7ebc56538745a08ef7c5e97f8bd437',
                      'name': 'dummy_vnffg',
                      u'attributes': {u'template': vnffgd_tosca_template},
                      'vnf_mapping': {
                          'VNF1': '91e32c20-6d1f-47a4-9ba7-08f5e5effe07',
                          'VNF3': '7168062e-9fa1-4203-8cb7-f5c99ff3ee1b'
                      },
                      'symmetrical': False}}


def get_dummy_vnffg_obj_dupl_criteria():
    return {'vnffg': {'description': 'dummy_vnffg_description',
                      'vnffgd_id': u'eb094833-995e-49f0-a047-dfb56aaf7c4e',
                      'tenant_id': u'ad7ebc56538745a08ef7c5e97f8bd437',
                      'name': 'dummy_vnffg',
                      u'attributes': {u'template':
                                      vnffgd_tosca_dupl_criteria_template},
                      'vnf_mapping': {},
                      'symmetrical': False}}


def get_dummy_nsd_obj():
    return {'nsd': {'description': 'dummy_nsd_description',
                    'name': 'dummy_NSD',
                    'tenant_id': u'8819a1542a5948b68f94d4be0fd50496',
                    'attributes': {u'nsd': nsd_tosca_template},
                    'template_source': 'onboarded'}}


def get_dummy_nsd_obj_inline():
    return {'nsd': {'description': 'dummy_nsd_description_inline',
                    'name': 'dummy_NSD_inline',
                    'tenant_id': u'8819a1542a5948b68f94d4be0fd50496',
                    'attributes': {u'nsd': nsd_tosca_template},
                    'template_source': 'inline'}}


def get_dummy_ns_obj():
    return {'ns': {'description': 'dummy_ns_description',
                   'id': u'ba6bf017-f6f7-45f1-a280-57b073bf78ea',
                   'nsd_id': u'eb094833-995e-49f0-a047-dfb56aaf7c4e',
                   'vim_id': u'6261579e-d6f3-49ad-8bc3-a9cb974778ff',
                   'tenant_id': u'ad7ebc56538745a08ef7c5e97f8bd437',
                   'name': 'dummy_ns',
                   'attributes': {
                       'param_values': {'nsd': {'vl1_name': 'net_mgmt',
                                                'vl2_name': 'net0'}}}}}


def get_dummy_ns_obj_inline():
    return {'ns': {'description': 'dummy_ns_description_inline',
                   'id': u'ff35e3f0-0a11-4071-bce6-279fdf1c8bf9',
                   'vim_id': u'6261579e-d6f3-49ad-8bc3-a9cb974778ff',
                   'tenant_id': u'ad7ebc56538745a08ef7c5e97f8bd437',
                   'name': 'dummy_ns_inline',
                   'attributes': {
                       'param_values': {'nsd': {'vl1_name': 'net_mgmt',
                                                'vl2_name': 'net0'}}},
                   'nsd_template': nsd_tosca_template}}


def get_dummy_ns_obj_2():
    return {'ns': {'description': 'dummy_ns_description',
                   'id': u'ba6bf017-f6f7-45f1-a280-57b073bf78ea',
                   'nsd_id': u'eb094833-995e-49f0-a047-dfb56aaf7c4e',
                   'vim_id': u'6261579e-d6f3-49ad-8bc3-a9cb974778ff',
                   'tenant_id': u'ad7ebc56538745a08ef7c5e97f8bd437',
                   'name': DUMMY_NS_2_NAME,
                   'attributes': {
                       'param_values': {'nsd': {'vl1_name': 'net_mgmt',
                                                'vl2_name': 'net0'}}}}}


def get_dummy_vnf_instance():
    connection_info = get_dummy_vim_connection_info()
    return {'created_at': '', 'deleted': False, 'deleted_at': None,
            'id': 'fake_id', 'instantiated_vnf_info': None,
            'instantiation_state': 'NOT_INSTANTIATED',
            'tenant_id': 'fake_tenant_id', 'updated_at': '',
            'vim_connection_info': [connection_info],
            'vnf_instance_description': 'VNF Description',
            'vnf_instance_name': 'test', 'vnf_product_name': 'Sample VNF',
            'vnf_provider': 'Company', 'vnf_software_version': '1.0',
            'vnfd_id': 'fake_vnfd_id', 'vnfd_version': '1.0'}


def get_dummy_vim_connection_info():
    return {'access_info': {
        'auth_url': 'fake/url',
        'cert_verify': 'False', 'password': 'admin',
        'project_domain_name': 'Default',
        'project_id': None, 'project_name': 'admin',
        'user_domain_name': 'Default', 'username': 'admin'},
        'created_at': '', 'deleted': False, 'deleted_at': '',
        'id': 'fake_id', 'updated_at': '',
        'vim_id': 'fake_vim_id', 'vim_type': 'openstack'}


def get_dummy_grant_hot():
    return str(hot_grant)


def get_dummy_scale_grant_hot():
    return str(hot_scale_grant)


def get_dummy_scale_nest_grant_hot():
    return str(hot_scale_nest_grant)


def get_dummy_scale_initial_hot():
    return str(hot_scale_initial)


def get_dummy_scale_nest_initial_hot():
    return str(hot_scale_nest_initial)
