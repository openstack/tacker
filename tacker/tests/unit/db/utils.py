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
import yaml


def _get_template(name):
    filename = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "../vnfm/infra_drivers/openstack/data/", name)
    f = codecs.open(filename, encoding='utf-8', errors='strict')
    return f.read()


etsi_vnfd = _get_template('etsi_nfv/tosca_vnfd.yaml')
etsi_vnfd_group = _get_template('etsi_nfv/tosca_vnfd_group_member.yaml')
hot_scale_grant = _get_template('hot_scale_grant.yaml')
hot_scale_nest_grant = _get_template('hot_scale_nest_grant.yaml')
hot_scale_initial = _get_template('hot_scale_initial.yaml')
hot_scale_nest_initial = _get_template('hot_scale_nest_initial.yaml')


def get_dummy_vnf(status='PENDING_CREATE', scaling_group=False,
                  instance_id=None):
    def_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "../vnfm/infra_drivers/openstack/data/etsi_nfv")
    vnfd = yaml.safe_load(etsi_vnfd)
    vnfd['imports'] = [
        f'{def_dir}/etsi_nfv_sol001_common_types.yaml',
        f'{def_dir}/etsi_nfv_sol001_vnfd_types.yaml']
    dummy_vnf = {'status': status, 'instance_id': instance_id, 'name':
        'test_vnf', 'tenant_id': 'ad7ebc56538745a08ef7c5e97f8bd437',
        'vnfd_id': 'eb094833-995e-49f0-a047-dfb56aaf7c4e',
        'vnfd': {
            'service_types': [{'service_type': 'vnfd',
            'id': '4a4c2d44-8a52-4895-9a75-9d1c76c3e738'}],
            'description': 'Dummy VNF',
            'tenant_id': 'ad7ebc56538745a08ef7c5e97f8bd437',
            'attributes': {'vnfd': str(vnfd)},
            'id': 'fb048660-dc1b-4f0f-bd89-b023666650ec',
            'name': 'dummy_vnf'},
        'mgmt_ip_address': None, 'service_context': [],
        'attributes': {'param_values': ''},
        'id': 'eb84260e-5ff7-4332-b032-50a14d6c1123',
        'description': 'Dummy VNF'}
    if scaling_group:
        dummy_vnf['attributes'].update({'scaling_group_names':
                                   '{"SP1": "SP1_group"}',
                                   'heat_template': 'test'})
    return dummy_vnf


def get_dummy_vnf_etsi(status='PENDING_CREATE', scaling_group=False,
                       instance_id=None, flavour='Simple', vnfd_name=None):
    vnfd_key = 'vnfd_' + flavour
    dummy_vnf = {'status': status, 'instance_id': instance_id, 'name':
        'test_vnf_etsi', 'tenant_id': 'ad7ebc56538745a08ef7c5e97f8bd437',
        'vnfd_id': 'eb094833-995e-49f0-a047-dfb56aaf7c4e',
        'vnfd': {
            'service_types': [{'service_type': 'vnfd',
            'id': '4a4c2d44-8a52-4895-9a75-9d1c76c3e738'}],
            'description': 'Dummy VNF etsi',
            'tenant_id': 'ad7ebc56538745a08ef7c5e97f8bd437',
            'id': 'fb048660-dc1b-4f0f-bd89-b023666650ec',
            'name': 'dummy_vnf_etsi'},
        'mgmt_ip_address': None, 'service_context': [],
        'attributes': {'param_values': ''},
        'id': 'eb84260e-5ff7-4332-b032-50a14d6c1123',
        'description': 'Dummy VNF etsi'}
    if not vnfd_name:
        # Set vnfd including without "tosca.groups.nfv.PlacementGroup"
        dummy_vnf['vnfd']['attributes'] = {vnfd_key: etsi_vnfd}
    else:
        # Set vnfd including with "tosca.groups.nfv.PlacementGroup"
        dummy_vnf['vnfd']['attributes'] = {vnfd_key: etsi_vnfd_group}
    if scaling_group:
        dummy_vnf['attributes'].update({'scaling_group_names':
                                   '{"SP1": "SP1_group"}',
                                   'heat_template': 'test'})
    return dummy_vnf


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
            'user_domain_name': 'Default',
            'project_domain_name': 'Default'}


def get_dummy_scale_grant_hot():
    return str(hot_scale_grant)


def get_dummy_scale_nest_grant_hot():
    return str(hot_scale_nest_grant)


def get_dummy_scale_initial_hot():
    return str(hot_scale_initial)


def get_dummy_scale_nest_initial_hot():
    return str(hot_scale_nest_initial)
