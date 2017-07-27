# Copyright 2016 Brocade Communications System, Inc.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
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
import mock
import os
from oslo_utils import uuidutils

from mock import patch

from tacker import context
from tacker.db.common_services import common_services_db_plugin
from tacker.db.nfvo import nfvo_db
from tacker.db.nfvo import ns_db
from tacker.db.nfvo import vnffg_db
from tacker.extensions import nfvo
from tacker.manager import TackerManager
from tacker.nfvo import nfvo_plugin
from tacker.plugins.common import constants
from tacker.tests.unit.db import base as db_base
from tacker.tests.unit.db import utils
from tacker.vnfm import vim_client

SECRET_PASSWORD = '***'
DUMMY_NS_2 = 'ba6bf017-f6f7-45f1-a280-57b073bf78ef'


def dummy_get_vim(*args, **kwargs):
    vim_obj = dict()
    vim_obj['auth_cred'] = utils.get_vim_auth_obj()
    vim_obj['type'] = 'openstack'
    return vim_obj


def _get_template(name):
    filename = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                '../../etc/samples/' + str(name)))
    f = codecs.open(filename, encoding='utf-8', errors='strict')
    return f.read()


class FakeDriverManager(mock.Mock):
    def invoke(self, *args, **kwargs):
        if any(x in ['create', 'create_chain', 'create_flow_classifier'] for
               x in args):
            return uuidutils.generate_uuid()
        elif 'execute_workflow' in args:
            mock_execution = mock.Mock()
            mock_execution.id.return_value = \
                "ba6bf017-f6f7-45f1-a280-57b073bf78ea"
            return mock_execution
        elif ('prepare_and_create_workflow' in args and
              'delete' == kwargs['action'] and
              DUMMY_NS_2 == kwargs['kwargs']['ns']['id']):
            raise nfvo.NoTasksException()
        elif ('prepare_and_create_workflow' in args and
              'create' == kwargs['action'] and
              utils.DUMMY_NS_2_NAME == kwargs['kwargs']['ns']['ns']['name']):
            raise nfvo.NoTasksException()


def get_by_name():
    return False


def get_by_id():
    return False


def dummy_get_vim_auth(*args, **kwargs):
    return {'vim_auth': {u'username': u'admin', 'password': 'devstack',
                         u'project_name': u'nfv', u'user_id': u'',
                         u'user_domain_name': u'Default',
                         u'auth_url': u'http://10.0.4.207/identity/v3',
                         u'project_id': u'',
                         u'project_domain_name': u'Default'},
            'vim_id': u'96025dd5-ca16-49f3-9823-958eb04260c4',
            'vim_type': u'openstack', 'vim_name': u'VIM0'}


class FakeClient(mock.Mock):
    def __init__(self, auth):
        pass


class FakeVNFMPlugin(mock.Mock):

    def __init__(self):
        super(FakeVNFMPlugin, self).__init__()
        self.vnf1_vnfd_id = 'eb094833-995e-49f0-a047-dfb56aaf7c4e'
        self.vnf1_vnf_id = '91e32c20-6d1f-47a4-9ba7-08f5e5effe07'
        self.vnf3_vnfd_id = 'e4015e9f-1ef2-49fb-adb6-070791ad3c45'
        self.vnf2_vnfd_id = 'e4015e9f-1ef2-49fb-adb6-070791ad3c45'
        self.vnf3_vnf_id = '7168062e-9fa1-4203-8cb7-f5c99ff3ee1b'
        self.vnf3_update_vnf_id = '10f66bc5-b2f1-45b7-a7cd-6dd6ad0017f5'

        self.cp11_id = 'd18c8bae-898a-4932-bff8-d5eac981a9c9'
        self.cp12_id = 'c8906342-3e30-4b2a-9401-a251a7a9b5dd'
        self.cp32_id = '3d1bd2a2-bf0e-44d1-87af-a2c6b2cad3ed'
        self.cp32_update_id = '064c0d99-5a61-4711-9597-2a44dc5da14b'

    def get_vnfd(self, *args, **kwargs):
        if 'VNF1' in args:
            return {'id': self.vnf1_vnfd_id,
                    'name': 'VNF1',
                    'attributes': {'vnfd': _get_template(
                                   'test-nsd-vnfd1.yaml')}}
        elif 'VNF2' in args:
            return {'id': self.vnf3_vnfd_id,
                    'name': 'VNF2',
                    'attributes': {'vnfd': _get_template(
                                   'test-nsd-vnfd2.yaml')}}

    def get_vnfds(self, *args, **kwargs):
        if {'name': ['VNF1']} in args:
            return [{'id': self.vnf1_vnfd_id}]
        elif {'name': ['VNF3']} in args:
            return [{'id': self.vnf3_vnfd_id}]
        else:
            return []

    def get_vnfs(self, *args, **kwargs):
        if {'vnfd_id': [self.vnf1_vnfd_id]} in args:
            return [{'id': self.vnf1_vnf_id}]
        elif {'vnfd_id': [self.vnf3_vnfd_id]} in args:
            return [{'id': self.vnf3_vnf_id}]
        else:
            return None

    def get_vnf(self, *args, **kwargs):
        if self.vnf1_vnf_id in args:
            return self.get_dummy_vnf1()
        elif self.vnf3_vnf_id in args:
            return self.get_dummy_vnf3()
        elif self.vnf3_update_vnf_id in args:
            return self.get_dummy_vnf3_update()

    def get_vnf_resources(self, *args, **kwargs):
        if self.vnf1_vnf_id in args:
            return self.get_dummy_vnf1_details()
        elif self.vnf3_vnf_id in args:
            return self.get_dummy_vnf3_details()
        elif self.vnf3_update_vnf_id in args:
            return self.get_dummy_vnf3_update_details()

    def get_dummy_vnf1_details(self):
        return [{'name': 'CP11', 'id': self.cp11_id},
                {'name': 'CP12', 'id': self.cp12_id}]

    def get_dummy_vnf3_details(self):
        return [{'name': 'CP32', 'id': self.cp32_id}]

    def get_dummy_vnf3_update_details(self):
        return [{'name': 'CP32', 'id': self.cp32_update_id}]

    def get_dummy_vnf1(self):
        return {'description': 'dummy_vnf_description',
                'vnfd_id': self.vnf1_vnfd_id,
                'vim_id': u'6261579e-d6f3-49ad-8bc3-a9cb974778ff',
                'tenant_id': u'ad7ebc56538745a08ef7c5e97f8bd437',
                'name': 'dummy_vnf1',
                'attributes': {}}

    def get_dummy_vnf3(self):
        return {'description': 'dummy_vnf_description',
                'vnfd_id': self.vnf3_vnfd_id,
                'vim_id': u'6261579e-d6f3-49ad-8bc3-a9cb974778ff',
                'tenant_id': u'ad7ebc56538745a08ef7c5e97f8bd437',
                'name': 'dummy_vnf2',
                'attributes': {}}

    def get_dummy_vnf3_update(self):
        return {'description': 'dummy_vnf_description',
                'vnfd_id': self.vnf3_vnfd_id,
                'vim_id': u'6261579e-d6f3-49ad-8bc3-a9cb974778ff',
                'tenant_id': u'ad7ebc56538745a08ef7c5e97f8bd437',
                'name': 'dummy_vnf_update',
                'attributes': {}}


class TestNfvoPlugin(db_base.SqlTestCase):
    def setUp(self):
        super(TestNfvoPlugin, self).setUp()
        self.addCleanup(mock.patch.stopall)
        self.context = context.get_admin_context()
        self._mock_driver_manager()
        mock.patch('tacker.nfvo.nfvo_plugin.NfvoPlugin._get_vim_from_vnf',
                   side_effect=dummy_get_vim).start()
        self.nfvo_plugin = nfvo_plugin.NfvoPlugin()
        mock.patch('tacker.db.common_services.common_services_db_plugin.'
                   'CommonServicesPluginDb.create_event'
                   ).start()
        self._cos_db_plugin =\
            common_services_db_plugin.CommonServicesPluginDb()

    def _mock_driver_manager(self):
        self._driver_manager = mock.Mock(wraps=FakeDriverManager())
        self._driver_manager.__contains__ = mock.Mock(
            return_value=True)
        fake_driver_manager = mock.Mock()
        fake_driver_manager.return_value = self._driver_manager
        self._mock(
            'tacker.common.driver_manager.DriverManager', fake_driver_manager)

    def _insert_dummy_vim(self):
        session = self.context.session
        vim_db = nfvo_db.Vim(
            id='6261579e-d6f3-49ad-8bc3-a9cb974778ff',
            tenant_id='ad7ebc56538745a08ef7c5e97f8bd437',
            name='fake_vim',
            description='fake_vim_description',
            type='openstack',
            status='Active',
            deleted_at=datetime.min,
            placement_attr={'regions': ['RegionOne']})
        vim_auth_db = nfvo_db.VimAuth(
            vim_id='6261579e-d6f3-49ad-8bc3-a9cb974778ff',
            password='encrypted_pw',
            auth_url='http://localhost:5000',
            vim_project={'name': 'test_project'},
            auth_cred={'username': 'test_user', 'user_domain_id': 'default',
                       'project_domain_id': 'default',
                       'key_type': 'fernet_key'})
        session.add(vim_db)
        session.add(vim_auth_db)
        session.flush()

    def _insert_dummy_vim_barbican(self):
        session = self.context.session
        vim_db = nfvo_db.Vim(
            id='6261579e-d6f3-49ad-8bc3-a9cb974778ff',
            tenant_id='ad7ebc56538745a08ef7c5e97f8bd437',
            name='fake_vim',
            description='fake_vim_description',
            type='openstack',
            status='Active',
            deleted_at=datetime.min,
            placement_attr={'regions': ['RegionOne']})
        vim_auth_db = nfvo_db.VimAuth(
            vim_id='6261579e-d6f3-49ad-8bc3-a9cb974778ff',
            password='encrypted_pw',
            auth_url='http://localhost:5000',
            vim_project={'name': 'test_project'},
            auth_cred={'username': 'test_user', 'user_domain_id': 'default',
                       'project_domain_id': 'default',
                       'key_type': 'barbican_key',
                       'secret_uuid': 'fake-secret-uuid'})
        session.add(vim_db)
        session.add(vim_auth_db)
        session.flush()

    def test_create_vim(self):
        vim_dict = utils.get_vim_obj()
        vim_type = 'openstack'
        res = self.nfvo_plugin.create_vim(self.context, vim_dict)
        self._cos_db_plugin.create_event.assert_any_call(
            self.context, evt_type=constants.RES_EVT_CREATE, res_id=mock.ANY,
            res_state=mock.ANY, res_type=constants.RES_TYPE_VIM,
            tstamp=mock.ANY)
        self._driver_manager.invoke.assert_any_call(
            vim_type, 'register_vim',
            context=self.context, vim_obj=vim_dict['vim'])
        self.assertIsNotNone(res)
        self.assertEqual(SECRET_PASSWORD, res['auth_cred']['password'])
        self.assertIn('id', res)
        self.assertIn('placement_attr', res)
        self.assertIn('created_at', res)
        self.assertIn('updated_at', res)

    def test_delete_vim(self):
        self._insert_dummy_vim()
        vim_type = u'openstack'
        vim_id = '6261579e-d6f3-49ad-8bc3-a9cb974778ff'
        vim_obj = self.nfvo_plugin._get_vim(self.context, vim_id)
        self.nfvo_plugin.delete_vim(self.context, vim_id)
        self._driver_manager.invoke.assert_called_once_with(
            vim_type, 'deregister_vim',
            context=self.context,
            vim_obj=vim_obj)
        self._cos_db_plugin.create_event.assert_called_with(
            self.context, evt_type=constants.RES_EVT_DELETE, res_id=mock.ANY,
            res_state=mock.ANY, res_type=constants.RES_TYPE_VIM,
            tstamp=mock.ANY)

    def test_update_vim(self):
        vim_dict = {'vim': {'id': '6261579e-d6f3-49ad-8bc3-a9cb974778ff',
                            'vim_project': {'name': 'new_project'},
                            'auth_cred': {'username': 'new_user',
                                          'password': 'new_password'}}}
        vim_type = u'openstack'
        vim_auth_username = vim_dict['vim']['auth_cred']['username']
        vim_project = vim_dict['vim']['vim_project']
        self._insert_dummy_vim()
        res = self.nfvo_plugin.update_vim(self.context, vim_dict['vim']['id'],
                                          vim_dict)
        vim_obj = self.nfvo_plugin._get_vim(
            self.context, vim_dict['vim']['id'])
        vim_obj['updated_at'] = None
        self._driver_manager.invoke.assert_called_with(
            vim_type, 'register_vim',
            context=self.context,
            vim_obj=vim_obj)
        self.assertIsNotNone(res)
        self.assertIn('id', res)
        self.assertIn('placement_attr', res)
        self.assertEqual(vim_project, res['vim_project'])
        self.assertEqual(vim_auth_username, res['auth_cred']['username'])
        self.assertEqual(SECRET_PASSWORD, res['auth_cred']['password'])
        self.assertIn('updated_at', res)
        self._cos_db_plugin.create_event.assert_called_with(
            self.context, evt_type=constants.RES_EVT_UPDATE, res_id=mock.ANY,
            res_state=mock.ANY, res_type=constants.RES_TYPE_VIM,
            tstamp=mock.ANY)

    def test_update_vim_barbican(self):
        vim_dict = {'vim': {'id': '6261579e-d6f3-49ad-8bc3-a9cb974778ff',
                            'vim_project': {'name': 'new_project'},
                            'auth_cred': {'username': 'new_user',
                                          'password': 'new_password'}}}
        vim_type = u'openstack'
        vim_auth_username = vim_dict['vim']['auth_cred']['username']
        vim_project = vim_dict['vim']['vim_project']
        self._insert_dummy_vim_barbican()
        old_vim_obj = self.nfvo_plugin._get_vim(
            self.context, vim_dict['vim']['id'])
        res = self.nfvo_plugin.update_vim(self.context, vim_dict['vim']['id'],
                                          vim_dict)
        vim_obj = self.nfvo_plugin._get_vim(
            self.context, vim_dict['vim']['id'])
        vim_obj['updated_at'] = None
        self._driver_manager.invoke.assert_called_with(
            vim_type, 'delete_vim_auth',
            context=self.context,
            vim_id=vim_obj['id'],
            auth=old_vim_obj['auth_cred'])
        self.assertIsNotNone(res)
        self.assertIn('id', res)
        self.assertIn('placement_attr', res)
        self.assertEqual(vim_project, res['vim_project'])
        self.assertEqual(vim_auth_username, res['auth_cred']['username'])
        self.assertEqual(SECRET_PASSWORD, res['auth_cred']['password'])
        self.assertIn('updated_at', res)
        self._cos_db_plugin.create_event.assert_called_with(
            self.context, evt_type=constants.RES_EVT_UPDATE, res_id=mock.ANY,
            res_state=mock.ANY, res_type=constants.RES_TYPE_VIM,
            tstamp=mock.ANY)

    def _insert_dummy_vnffg_template(self):
        session = self.context.session
        vnffg_template = vnffg_db.VnffgTemplate(
            id='eb094833-995e-49f0-a047-dfb56aaf7c4e',
            tenant_id='ad7ebc56538745a08ef7c5e97f8bd437',
            name='fake_template',
            description='fake_template_description',
            template={u'vnffgd': utils.vnffgd_tosca_template},
            template_source='onboarded')
        session.add(vnffg_template)
        session.flush()
        return vnffg_template

    def _insert_dummy_vnffg_template_inline(self):
        session = self.context.session
        vnffg_template = vnffg_db.VnffgTemplate(
            id='11da9f20-9347-4283-bc68-eb98061ef8f7',
            tenant_id='ad7ebc56538745a08ef7c5e97f8bd437',
            name='dummy_vnffgd_inline',
            description='dummy_vnffgd_description_inline',
            template={u'vnffgd': utils.vnffgd_tosca_template},
            template_source='inline')
        session.add(vnffg_template)
        session.flush()
        return vnffg_template

    def _insert_dummy_vnffg_param_template(self):
        session = self.context.session
        vnffg_template = vnffg_db.VnffgTemplate(
            id='eb094833-995e-49f0-a047-dfb56aaf7c4e',
            tenant_id='ad7ebc56538745a08ef7c5e97f8bd437',
            name='fake_template',
            description='fake_template_description',
            template={u'vnffgd': utils.vnffgd_tosca_param_template})
        session.add(vnffg_template)
        session.flush()
        return vnffg_template

    def _insert_dummy_vnffg_str_param_template(self):
        session = self.context.session
        vnffg_template = vnffg_db.VnffgTemplate(
            id='eb094833-995e-49f0-a047-dfb56aaf7c4e',
            tenant_id='ad7ebc56538745a08ef7c5e97f8bd437',
            name='fake_template',
            description='fake_template_description',
            template={u'vnffgd': utils.vnffgd_tosca_str_param_template})
        session.add(vnffg_template)
        session.flush()
        return vnffg_template

    def _insert_dummy_vnffg_multi_param_template(self):
        session = self.context.session
        vnffg_template = vnffg_db.VnffgTemplate(
            id='eb094833-995e-49f0-a047-dfb56aaf7c4e',
            tenant_id='ad7ebc56538745a08ef7c5e97f8bd437',
            name='fake_template',
            description='fake_template_description',
            template={u'vnffgd': utils.vnffgd_tosca_multi_param_template})
        session.add(vnffg_template)
        session.flush()
        return vnffg_template

    def _insert_dummy_vnffg(self):
        session = self.context.session
        vnffg = vnffg_db.Vnffg(
            id='ffc1a59b-65bb-4874-94d3-84f639e63c74',
            tenant_id='ad7ebc56538745a08ef7c5e97f8bd437',
            name='dummy_vnffg',
            description="fake vnffg",
            vnffgd_id='eb094833-995e-49f0-a047-dfb56aaf7c4e',
            status='ACTIVE',
            vnf_mapping={'VNF1': '91e32c20-6d1f-47a4-9ba7-08f5e5effe07',
                         'VNF3': '7168062e-9fa1-4203-8cb7-f5c99ff3ee1b'})
        session.add(vnffg)
        nfp = vnffg_db.VnffgNfp(
            id='768f76a7-9025-4acd-b51c-0da609759983',
            tenant_id='ad7ebc56538745a08ef7c5e97f8bd437',
            status="ACTIVE",
            name='Forwarding_path1',
            vnffg_id='ffc1a59b-65bb-4874-94d3-84f639e63c74',
            path_id=51,
            symmetrical=False)
        session.add(nfp)
        sfc = vnffg_db.VnffgChain(
            id='f28e33bc-1061-4762-b942-76060bbd59c4',
            tenant_id='ad7ebc56538745a08ef7c5e97f8bd437',
            symmetrical=False,
            chain=[{'connection_points': [
                'd18c8bae-898a-4932-bff8-d5eac981a9c9',
                'c8906342-3e30-4b2a-9401-a251a7a9b5dd'],
                'name': 'dummy_vnf1'},
                {'connection_points': ['3d1bd2a2-bf0e-44d1-87af-a2c6b2cad3ed'],
                 'name': 'dummy_vnf2'}],
            path_id=51,
            status='ACTIVE',
            nfp_id='768f76a7-9025-4acd-b51c-0da609759983',
            instance_id='bcfb295e-578e-405b-a349-39f06b25598c')
        session.add(sfc)
        fc = vnffg_db.VnffgClassifier(
            id='a85f21b5-f446-43f0-86f4-d83bdc5590ab',
            tenant_id='ad7ebc56538745a08ef7c5e97f8bd437',
            status='ACTIVE',
            instance_id='3007dc2d-30dc-4651-9184-f1e6273cc0b6',
            chain_id='f28e33bc-1061-4762-b942-76060bbd59c4',
            nfp_id='768f76a7-9025-4acd-b51c-0da609759983')
        session.add(fc)
        match = vnffg_db.ACLMatchCriteria(
            id='bdb0f2db-d4c2-42a2-a1df-426079ecc443',
            vnffgc_id='a85f21b5-f446-43f0-86f4-d83bdc5590ab',
            eth_src=None, eth_dst=None, eth_type=None, vlan_id=None,
            vlan_pcp=None, mpls_label=None, mpls_tc=None, ip_dscp=None,
            ip_ecn=None, ip_src_prefix=None, ip_dst_prefix='192.168.1.2/24',
            source_port_min=None, source_port_max=None,
            destination_port_min=80, destination_port_max=1024, ip_proto=6,
            network_id=None, network_src_port_id=None,
            network_dst_port_id=None, tenant_id=None, icmpv4_type=None,
            icmpv4_code=None, arp_op=None, arp_spa=None, arp_tpa=None,
            arp_sha=None, arp_tha=None, ipv6_src=None, ipv6_dst=None,
            ipv6_flabel=None, icmpv6_type=None, icmpv6_code=None,
            ipv6_nd_target=None, ipv6_nd_sll=None, ipv6_nd_tll=None)
        session.add(match)
        session.flush()
        return vnffg

    def test_validate_tosca(self):
        template = utils.vnffgd_tosca_template
        self.nfvo_plugin.validate_tosca(template)

    def test_validate_tosca_missing_tosca_ver(self):
        template = utils.vnffgd_template
        self.assertRaises(nfvo.ToscaParserFailed,
                          self.nfvo_plugin.validate_tosca,
                          template)

    def test_validate_tosca_invalid(self):
        template = utils.vnffgd_invalid_tosca_template
        self.assertRaises(nfvo.ToscaParserFailed,
                          self.nfvo_plugin.validate_tosca,
                          template)

    def test_validate_vnffg_properties(self):
        template = {'vnffgd': utils.vnffgd_tosca_template}
        self.nfvo_plugin.validate_vnffg_properties(template)

    def test_validate_vnffg_properties_wrong_number(self):
        template = {'vnffgd': utils.vnffgd_wrong_cp_number_template}
        self.assertRaises(nfvo.VnffgdWrongEndpointNumber,
                          self.nfvo_plugin.validate_vnffg_properties,
                          template)

    def test_create_vnffgd(self):
        vnffgd_obj = utils.get_dummy_vnffgd_obj()
        result = self.nfvo_plugin.create_vnffgd(self.context, vnffgd_obj)
        self.assertIsNotNone(result)
        self.assertIn('id', result)
        self.assertIn('template', result)
        self.assertIn('template_source', result)
        self.assertEqual('onboarded', result['template_source'])

    def test_create_vnffgd_inline(self):
        vnffgd_obj = utils.get_dummy_vnffgd_obj_inline()
        result = self.nfvo_plugin.create_vnffgd(self.context, vnffgd_obj)
        self.assertIsNotNone(result)
        self.assertIn('id', result)
        self.assertIn('template', result)
        self.assertEqual('inline', result['template_source'])

    def test_create_vnffg_abstract_types(self):
        with patch.object(TackerManager, 'get_service_plugins') as \
                mock_plugins:
            mock_plugins.return_value = {'VNFM': FakeVNFMPlugin()}
            mock.patch('tacker.common.driver_manager.DriverManager',
                       side_effect=FakeDriverManager()).start()
            self._insert_dummy_vnffg_template()
            vnffg_obj = utils.get_dummy_vnffg_obj()
            result = self.nfvo_plugin.create_vnffg(self.context, vnffg_obj)
            self.assertIsNotNone(result)
            self.assertIn('id', result)
            self.assertIn('status', result)
            self.assertEqual('PENDING_CREATE', result['status'])
            self._driver_manager.invoke.assert_called_with(mock.ANY, mock.ANY,
                                                           name=mock.ANY,
                                                           vnfs=mock.ANY,
                                                           fc_id=mock.ANY,
                                                           auth_attr=mock.ANY,
                                                           symmetrical=mock.ANY
                                                           )

    @mock.patch('tacker.nfvo.nfvo_plugin.NfvoPlugin.create_vnffgd')
    def test_create_vnffg_abstract_types_inline(self, mock_create_vnffgd):
        with patch.object(TackerManager, 'get_service_plugins') as \
                mock_plugins:
            mock_plugins.return_value = {'VNFM': FakeVNFMPlugin()}
            mock.patch('tacker.common.driver_manager.DriverManager',
                       side_effect=FakeDriverManager()).start()
            mock_create_vnffgd.return_value = {'id':
                    '11da9f20-9347-4283-bc68-eb98061ef8f7'}
            self._insert_dummy_vnffg_template_inline()
            vnffg_obj = utils.get_dummy_vnffg_obj_inline()
            result = self.nfvo_plugin.create_vnffg(self.context, vnffg_obj)
            self.assertIsNotNone(result)
            self.assertIn('id', result)
            self.assertIn('status', result)
            self.assertEqual('PENDING_CREATE', result['status'])
            self.assertEqual('dummy_vnffg_inline', result['name'])
            mock_create_vnffgd.assert_called_once_with(mock.ANY, mock.ANY)
            self._driver_manager.invoke.assert_called_with(mock.ANY, mock.ANY,
                                                           name=mock.ANY,
                                                           vnfs=mock.ANY,
                                                           fc_id=mock.ANY,
                                                           auth_attr=mock.ANY,
                                                           symmetrical=mock.ANY
                                                           )

    def test_create_vnffg_param_values(self):
        with patch.object(TackerManager, 'get_service_plugins') as \
                mock_plugins:
            mock_plugins.return_value = {'VNFM': FakeVNFMPlugin()}
            mock.patch('tacker.common.driver_manager.DriverManager',
                       side_effect=FakeDriverManager()).start()
            self._insert_dummy_vnffg_param_template()
            vnffg_obj = utils.get_dummy_vnffg_param_obj()
            result = self.nfvo_plugin.create_vnffg(self.context, vnffg_obj)
            self.assertIsNotNone(result)
            self.assertIn('id', result)
            self.assertIn('status', result)
            self.assertEqual('PENDING_CREATE', result['status'])
            self._driver_manager.invoke.assert_called_with(mock.ANY, mock.ANY,
                                                           name=mock.ANY,
                                                           vnfs=mock.ANY,
                                                           fc_id=mock.ANY,
                                                           auth_attr=mock.ANY,
                                                           symmetrical=mock.ANY
                                                           )

    @mock.patch.object(nfvo_plugin.NfvoPlugin, '_get_by_id')
    def test_create_vnffg_param_value_format_error(self, mock_get_by_id):
        with patch.object(TackerManager, 'get_service_plugins') as \
                mock_plugins:
            mock_plugins.return_value = {'VNFM': FakeVNFMPlugin()}
            mock_get_by_id.value = get_by_id()
            vnffg_obj = utils.get_dummy_vnffg_str_param_obj()
            self.assertRaises(nfvo.VnffgParamValueFormatError,
                              self.nfvo_plugin.create_vnffg,
                              self.context, vnffg_obj)

    def test_create_vnffg_template_param_not_parse(self):
        with patch.object(TackerManager, 'get_service_plugins') as \
                mock_plugins:
            mock_plugins.return_value = {'VNFM': FakeVNFMPlugin()}
            self._insert_dummy_vnffg_multi_param_template()
            vnffg_obj = utils.get_dummy_vnffg_param_obj()
            self.assertRaises(nfvo.VnffgTemplateParamParsingException,
                              self.nfvo_plugin.create_vnffg,
                              self.context, vnffg_obj)

    def test_create_vnffg_param_value_not_use(self):
        with patch.object(TackerManager, 'get_service_plugins') as \
                mock_plugins:
            mock_plugins.return_value = {'VNFM': FakeVNFMPlugin()}
            self._insert_dummy_vnffg_param_template()
            vnffg_obj = utils.get_dummy_vnffg_multi_param_obj()
            self.assertRaises(nfvo.VnffgParamValueNotUsed,
                              self.nfvo_plugin.create_vnffg,
                              self.context, vnffg_obj)

    def test_create_vnffg_vnf_mapping(self):
        with patch.object(TackerManager, 'get_service_plugins') as \
                mock_plugins:
            mock_plugins.return_value = {'VNFM': FakeVNFMPlugin()}
            mock.patch('tacker.common.driver_manager.DriverManager',
                       side_effect=FakeDriverManager()).start()
            self._insert_dummy_vnffg_template()
            vnffg_obj = utils.get_dummy_vnffg_obj_vnf_mapping()
            result = self.nfvo_plugin.create_vnffg(self.context, vnffg_obj)
            self.assertIsNotNone(result)
            self.assertIn('id', result)
            self.assertIn('status', result)
            self.assertEqual('PENDING_CREATE', result['status'])
            self._driver_manager.invoke.assert_called_with(mock.ANY, mock.ANY,
                                                           name=mock.ANY,
                                                           vnfs=mock.ANY,
                                                           fc_id=mock.ANY,
                                                           auth_attr=mock.ANY,
                                                           symmetrical=mock.ANY
                                                           )

    def test_update_vnffg_nonexistent_vnf(self):
        with patch.object(TackerManager, 'get_service_plugins') as \
                mock_plugins:
            mock_plugins.return_value = {'VNFM': FakeVNFMPlugin()}
            mock.patch('tacker.common.driver_manager.DriverManager',
                       side_effect=FakeDriverManager()).start()
            self._insert_dummy_vnffg_template()
            vnffg = self._insert_dummy_vnffg()
            updated_vnffg = utils.get_dummy_vnffg_obj_vnf_mapping()
            updated_vnffg['vnffg']['symmetrical'] = True
            updated_vnf_mapping = \
                {'VNF1': '91e32c20-6d1f-47a4-9ba7-08f5e5effe07',
                 'VNF3': '5c7f5631-9e74-46e8-b3d2-397c0eda9d0b'}
            updated_vnffg['vnffg']['vnf_mapping'] = updated_vnf_mapping
            self.assertRaises(nfvo.VnffgInvalidMappingException,
                              self.nfvo_plugin.update_vnffg,
                              self.context, vnffg['id'], updated_vnffg)

    def test_update_vnffg(self):
        with patch.object(TackerManager, 'get_service_plugins') as \
                mock_plugins:
            mock_plugins.return_value = {'VNFM': FakeVNFMPlugin()}
            mock.patch('tacker.common.driver_manager.DriverManager',
                       side_effect=FakeDriverManager()).start()
            self._insert_dummy_vnffg_template()
            vnffg = self._insert_dummy_vnffg()
            updated_vnffg = utils.get_dummy_vnffg_obj_vnf_mapping()
            updated_vnffg['vnffg']['symmetrical'] = True
            updated_vnf_mapping = \
                {'VNF1': '91e32c20-6d1f-47a4-9ba7-08f5e5effe07',
                 'VNF3': '10f66bc5-b2f1-45b7-a7cd-6dd6ad0017f5'}
            updated_vnffg['vnffg']['vnf_mapping'] = updated_vnf_mapping
            self.nfvo_plugin.update_vnffg(self.context, vnffg['id'],
                                          updated_vnffg)
            self._driver_manager.invoke.assert_called_with(mock.ANY, mock.ANY,
                                                           vnfs=mock.ANY,
                                                           fc_ids=mock.ANY,
                                                           chain_id=mock.ANY,
                                                           auth_attr=mock.ANY,
                                                           symmetrical=True)

    def test_delete_vnffg(self):
        self._insert_dummy_vnffg_template()
        vnffg = self._insert_dummy_vnffg()
        self.nfvo_plugin.delete_vnffg(self.context, vnffg['id'])
        self._driver_manager.invoke.assert_called_with(mock.ANY, mock.ANY,
                                                       fc_id=mock.ANY,
                                                       auth_attr=mock.ANY)

    def _insert_dummy_ns_template(self):
        session = self.context.session
        attributes = {
            u'nsd': 'imports: [VNF1, VNF2]\ntopology_template:\n  inputs:\n  '
                    '  vl1_name: {default: net_mgmt, description: name of VL1'
                    ' virtuallink, type: string}\n    vl2_name: {default: '
                    'net0, description: name of VL2 virtuallink, type: string'
                    '}\n  node_templates:\n    VL1:\n      properties:\n     '
                    '   network_name: {get_input: vl1_name}\n        vendor: '
                    'tacker\n      type: tosca.nodes.nfv.VL\n    VL2:\n      '
                    'properties:\n        network_name: {get_input: vl2_name}'
                    '\n        vendor: tacker\n      type: tosca.nodes.nfv.VL'
                    '\n    VNF1:\n      requirements:\n      - {virtualLink1: '
                    'VL1}\n      - {virtualLink2: VL2}\n      type: tosca.node'
                    's.nfv.VNF1\n    VNF2: {type: tosca.nodes.nfv.VNF2}\ntosca'
                    '_definitions_version: tosca_simple_profile_for_nfv_1_0_0'
                    '\n'}
        nsd_template = ns_db.NSD(
            id='eb094833-995e-49f0-a047-dfb56aaf7c4e',
            tenant_id='ad7ebc56538745a08ef7c5e97f8bd437',
            name='fake_template',
            vnfds={'tosca.nodes.nfv.VNF1': 'vnf1',
                   'tosca.nodes.nfv.VNF2': 'vnf2'},
            description='fake_nsd_template_description',
            deleted_at=datetime.min,
            template_source='onboarded')
        session.add(nsd_template)
        for (key, value) in attributes.items():
            attribute_db = ns_db.NSDAttribute(
                id=uuidutils.generate_uuid(),
                nsd_id='eb094833-995e-49f0-a047-dfb56aaf7c4e',
                key=key,
                value=value)
            session.add(attribute_db)
        session.flush()
        return nsd_template

    def _insert_dummy_ns_template_inline(self):
        session = self.context.session
        attributes = {
            u'nsd': 'imports: [VNF1, VNF2]\ntopology_template:\n  inputs:\n  '
                    '  vl1_name: {default: net_mgmt, description: name of VL1'
                    ' virtuallink, type: string}\n    vl2_name: {default: '
                    'net0, description: name of VL2 virtuallink, type: string'
                    '}\n  node_templates:\n    VL1:\n      properties:\n     '
                    '   network_name: {get_input: vl1_name}\n        vendor: '
                    'tacker\n      type: tosca.nodes.nfv.VL\n    VL2:\n      '
                    'properties:\n        network_name: {get_input: vl2_name}'
                    '\n        vendor: tacker\n      type: tosca.nodes.nfv.VL'
                    '\n    VNF1:\n      requirements:\n      - {virtualLink1: '
                    'VL1}\n      - {virtualLink2: VL2}\n      type: tosca.node'
                    's.nfv.VNF1\n    VNF2: {type: tosca.nodes.nfv.VNF2}\ntosca'
                    '_definitions_version: tosca_simple_profile_for_nfv_1_0_0'
                    '\n'}
        nsd_template = ns_db.NSD(
            id='be18005d-5656-4d81-b499-6af4d4d8437f',
            tenant_id='ad7ebc56538745a08ef7c5e97f8bd437',
            name='dummy_NSD',
            vnfds={'tosca.nodes.nfv.VNF1': 'vnf1',
                   'tosca.nodes.nfv.VNF2': 'vnf2'},
            description='dummy_nsd_description',
            deleted_at=datetime.min,
            template_source='inline')
        session.add(nsd_template)
        for (key, value) in attributes.items():
            attribute_db = ns_db.NSDAttribute(
                id=uuidutils.generate_uuid(),
                nsd_id='be18005d-5656-4d81-b499-6af4d4d8437f',
                key=key,
                value=value)
            session.add(attribute_db)
        session.flush()
        return nsd_template

    def _insert_dummy_ns(self):
        session = self.context.session
        ns = ns_db.NS(
            id='ba6bf017-f6f7-45f1-a280-57b073bf78ea',
            name='dummy_ns',
            tenant_id='ad7ebc56538745a08ef7c5e97f8bd437',
            status='ACTIVE',
            nsd_id='eb094833-995e-49f0-a047-dfb56aaf7c4e',
            vim_id='6261579e-d6f3-49ad-8bc3-a9cb974778ff',
            description='dummy_ns_description',
            deleted_at=datetime.min)
        session.add(ns)
        session.flush()
        return ns

    def _insert_dummy_ns_2(self):
        session = self.context.session
        ns = ns_db.NS(
            id=DUMMY_NS_2,
            name='fake_ns',
            tenant_id='ad7ebc56538745a08ef7c5e97f8bd437',
            status='ACTIVE',
            nsd_id='eb094833-995e-49f0-a047-dfb56aaf7c4e',
            vim_id='6261579e-d6f3-49ad-8bc3-a9cb974778ff',
            description='fake_ns_description',
            deleted_at=datetime.min)
        session.add(ns)
        session.flush()
        return ns

    def test_create_nsd(self):
        nsd_obj = utils.get_dummy_nsd_obj()
        with patch.object(TackerManager, 'get_service_plugins') as \
                mock_plugins:
            mock_plugins.return_value = {'VNFM': FakeVNFMPlugin()}
            result = self.nfvo_plugin.create_nsd(self.context, nsd_obj)
            self.assertIsNotNone(result)
            self.assertEqual('dummy_NSD', result['name'])
            self.assertIn('id', result)
            self.assertEqual('dummy_NSD', result['name'])
            self.assertEqual('onboarded', result['template_source'])
            self.assertEqual('8819a1542a5948b68f94d4be0fd50496',
                             result['tenant_id'])
            self.assertIn('attributes', result)
            self.assertIn('created_at', result)
            self.assertIn('updated_at', result)

    def test_create_nsd_inline(self):
        nsd_obj = utils.get_dummy_nsd_obj_inline()
        with patch.object(TackerManager, 'get_service_plugins') as \
                mock_plugins:
            mock_plugins.return_value = {'VNFM': FakeVNFMPlugin()}
            result = self.nfvo_plugin.create_nsd(self.context, nsd_obj)
            self.assertIsNotNone(result)
            self.assertIn('id', result)
            self.assertEqual('dummy_NSD_inline', result['name'])
            self.assertEqual('inline', result['template_source'])
            self.assertEqual('8819a1542a5948b68f94d4be0fd50496',
                             result['tenant_id'])
            self.assertIn('attributes', result)
            self.assertIn('created_at', result)
            self.assertIn('updated_at', result)

    @mock.patch.object(nfvo_plugin.NfvoPlugin, 'get_auth_dict')
    @mock.patch.object(vim_client.VimClient, 'get_vim')
    @mock.patch.object(nfvo_plugin.NfvoPlugin, '_get_by_name')
    def test_create_ns(self, mock_get_by_name, mock_get_vimi, mock_auth_dict):
        self._insert_dummy_ns_template()
        self._insert_dummy_vim()
        mock_auth_dict.return_value = {
            'auth_url': 'http://127.0.0.1',
            'token': 'DummyToken',
            'project_domain_name': 'dummy_domain',
            'project_name': 'dummy_project'
        }
        with patch.object(TackerManager, 'get_service_plugins') as \
                mock_plugins:
            mock_plugins.return_value = {'VNFM': FakeVNFMPlugin()}
            mock_get_by_name.return_value = get_by_name()

            ns_obj = utils.get_dummy_ns_obj()
            result = self.nfvo_plugin.create_ns(self.context, ns_obj)
            self.assertIsNotNone(result)
            self.assertIn('id', result)
            self.assertEqual(ns_obj['ns']['nsd_id'], result['nsd_id'])
            self.assertEqual(ns_obj['ns']['name'], result['name'])
            self.assertIn('status', result)
            self.assertIn('tenant_id', result)

    @mock.patch('tacker.nfvo.nfvo_plugin.NfvoPlugin.create_nsd')
    @mock.patch.object(nfvo_plugin.NfvoPlugin, 'get_auth_dict')
    @mock.patch.object(vim_client.VimClient, 'get_vim')
    @mock.patch.object(nfvo_plugin.NfvoPlugin, '_get_by_name')
    def test_create_ns_inline(self, mock_get_by_name, mock_get_vimi,
                              mock_auth_dict, mock_create_nsd):
        self._insert_dummy_ns_template_inline()
        self._insert_dummy_vim()
        mock_auth_dict.return_value = {
            'auth_url': 'http://127.0.0.1',
            'token': 'DummyToken',
            'project_domain_name': 'dummy_domain',
            'project_name': 'dummy_project'
        }
        with patch.object(TackerManager, 'get_service_plugins') as \
                mock_plugins:
            mock_plugins.return_value = {'VNFM': FakeVNFMPlugin()}
            mock_get_by_name.return_value = get_by_name()
            mock_create_nsd.return_value = {'id':
                            'be18005d-5656-4d81-b499-6af4d4d8437f'}

            ns_obj = utils.get_dummy_ns_obj_inline()
            result = self.nfvo_plugin.create_ns(self.context, ns_obj)
            self.assertIsNotNone(result)
            self.assertIn('id', result)
            self.assertEqual(ns_obj['ns']['nsd_id'], result['nsd_id'])
            self.assertEqual(ns_obj['ns']['name'], result['name'])
            self.assertEqual('dummy_ns_inline', result['name'])
            self.assertIn('status', result)
            self.assertIn('tenant_id', result)
            mock_create_nsd.assert_called_once_with(mock.ANY, mock.ANY)

    @mock.patch.object(nfvo_plugin.NfvoPlugin, 'get_auth_dict')
    @mock.patch.object(vim_client.VimClient, 'get_vim')
    @mock.patch.object(nfvo_plugin.NfvoPlugin, '_get_by_name')
    def test_create_ns_workflow_no_task_exception(
            self, mock_get_by_name, mock_get_vimi, mock_auth_dict):
        self._insert_dummy_ns_template()
        self._insert_dummy_vim()
        mock_auth_dict.return_value = {
            'auth_url': 'http://127.0.0.1',
            'token': 'DummyToken',
            'project_domain_name': 'dummy_domain',
            'project_name': 'dummy_project'
        }
        with patch.object(TackerManager, 'get_service_plugins') as \
                mock_plugins:
            mock_plugins.return_value = {'VNFM': FakeVNFMPlugin()}
            mock_get_by_name.return_value = get_by_name()

            ns_obj = utils.get_dummy_ns_obj_2()
            self.assertRaises(nfvo.NoTasksException,
                              self.nfvo_plugin.create_ns,
                              self.context, ns_obj)

    @mock.patch.object(nfvo_plugin.NfvoPlugin, 'get_auth_dict')
    @mock.patch.object(vim_client.VimClient, 'get_vim')
    @mock.patch.object(nfvo_plugin.NfvoPlugin, '_get_by_name')
    def test_delete_ns(self, mock_get_by_name, mock_get_vim, mock_auth_dict):
        self._insert_dummy_vim()
        self._insert_dummy_ns_template()
        self._insert_dummy_ns()
        mock_auth_dict.return_value = {
            'auth_url': 'http://127.0.0.1',
            'token': 'DummyToken',
            'project_domain_name': 'dummy_domain',
            'project_name': 'dummy_project'
        }

        with patch.object(TackerManager, 'get_service_plugins') as \
                mock_plugins:
            mock_plugins.return_value = {'VNFM': FakeVNFMPlugin()}
            mock_get_by_name.return_value = get_by_name()
            result = self.nfvo_plugin.delete_ns(self.context,
                'ba6bf017-f6f7-45f1-a280-57b073bf78ea')
            self.assertIsNotNone(result)

    @mock.patch.object(nfvo_plugin.NfvoPlugin, 'get_auth_dict')
    @mock.patch.object(vim_client.VimClient, 'get_vim')
    @mock.patch.object(nfvo_plugin.NfvoPlugin, '_get_by_name')
    @mock.patch("tacker.db.nfvo.ns_db.NSPluginDb.delete_ns_post")
    def test_delete_ns_no_task_exception(
            self, mock_delete_ns_post, mock_get_by_name, mock_get_vim,
            mock_auth_dict):

        self._insert_dummy_vim()
        self._insert_dummy_ns_template()
        self._insert_dummy_ns_2()
        mock_auth_dict.return_value = {
            'auth_url': 'http://127.0.0.1',
            'token': 'DummyToken',
            'project_domain_name': 'dummy_domain',
            'project_name': 'dummy_project'
        }

        with patch.object(TackerManager, 'get_service_plugins') as \
                mock_plugins:
            mock_plugins.return_value = {'VNFM': FakeVNFMPlugin()}
            mock_get_by_name.return_value = get_by_name()
            self.nfvo_plugin.delete_ns(self.context,
                DUMMY_NS_2)
        mock_delete_ns_post.assert_called_with(
            self.context, DUMMY_NS_2, None, None)
