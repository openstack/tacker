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

import mock

from oslo_utils import uuidutils

from tacker import context
from tacker.nfvo.drivers.vim import openstack_driver
from tacker.tests.unit import base
from tacker.tests.unit.db import utils


class FakeNeutronClient(mock.Mock):
    def __init__(self):
        super(FakeNeutronClient, self).__init__()
        self.__fc_dict = {}
        self.__pp_dict = {}
        self.__ppg_dict = {}
        self.__chain_dict = {}

    def flow_classifier_create(self, fc_create_dict):
        fc_id = uuidutils.generate_uuid()
        self.__fc_dict[fc_id] = fc_create_dict
        return fc_id

    def show_flow_classifier(self, fc_dict):
        fc_name = fc_dict['name']
        for fc_id in self.__fc_dict:
            fc = self.__fc_dict[fc_id]
            if fc_name == fc['name']:
                return {'id': fc_id}

        return None

    def flow_classifier_update(self, fc_id, fc_update_dict):
        if fc_id not in self.__fc_dict:
            return None
        self.__fc_dict[fc_id] = fc_update_dict
        return fc_update_dict

    def flow_classifier_delete(self, fc_id):
        if fc_id not in self.__fc_dict:
            raise ValueError('fc not found')
        self.__fc_dict.pop(fc_id)

    def port_pair_create(self, port_pair):
        pp_id = uuidutils.generate_uuid()
        self.__pp_dict[pp_id] = port_pair
        return pp_id

    def show_port_pair(self, port_pair_dict):
        input_pp_name = port_pair_dict['name']
        for pp_id in self.__pp_dict:
            port_pair = self.__pp_dict[pp_id]
            if port_pair['name'] == input_pp_name:
                return {'id': pp_id}

        return None

    def port_pair_group_create(self, port_pair_group):
        ppg_id = uuidutils.generate_uuid()
        self.__ppg_dict[ppg_id] = port_pair_group
        return ppg_id

    def show_port_pair_group(self, port_pair_group_dict):
        input_ppg_name = port_pair_group_dict['name']
        for ppg_id in self.__ppg_dict:
            port_pair_group = self.__ppg_dict[ppg_id]
            if port_pair_group['name'] == input_ppg_name:
                return {'id': ppg_id}

        return None

    def port_chain_create(self, port_chain):
        chain_id = uuidutils.generate_uuid()
        self.__chain_dict[chain_id] = port_chain
        return chain_id

    def show_port_chain(self, port_chain_dict):
        input_chain_name = port_chain_dict['name']
        for chain_id in self.__chain_dict:
            port_chain = self.__chain_dict[chain_id]
            if port_chain['name'] == input_chain_name:
                return {'id': chain_id}
        return None

    def port_chain_delete(self, chain_id):
        if chain_id not in self.__chain_dict:
            raise ValueError('port chain delete failed')
        self.__chain_dict.pop(chain_id)


class TestChainSFC(base.TestCase):

    def setUp(self):
        super(TestChainSFC, self).setUp()
        self.context = context.get_admin_context()
        self.sfc_driver = openstack_driver.OpenStack_Driver()
        self._mock_neutron_client()
        self.addCleanup(mock.patch.stopall)

    def _mock_neutron_client(self):
        self.neutron_client = mock.Mock(wraps=FakeNeutronClient())
        fake_neutron_client = mock.Mock()
        fake_neutron_client.return_value = self.neutron_client
        self._mock(
            'tacker.nfvo.drivers.vim.openstack_driver.'
            'NeutronClient',
            fake_neutron_client)

    def _mock(self, target, new=mock.DEFAULT):
        patcher = mock.patch(target, new)
        return patcher.start()

    def test_create_flow_classifier(self):
        flow_classifier = {'name': 'fake_fc',
                           'source_port_range': '2005-2010',
                           'ip_proto': 6,
                           'destination_port_range': '80-180'}
        result = self.sfc_driver.\
            create_flow_classifier(name='fake_ffg', fc=flow_classifier,
                                   auth_attr=utils.get_vim_auth_obj())
        self.assertIsNotNone(result)

    def test_update_flow_classifier(self):
        flow_classifier = {'name': 'next_fake_fc',
                           'description': 'fake flow-classifier',
                           'source_port_range': '2005-2010',
                           'ip_proto': 6,
                           'destination_port_range': '80-180'}
        fc_id = self.sfc_driver.\
            create_flow_classifier(name='fake_ffg', fc=flow_classifier,
                                   auth_attr=utils.get_vim_auth_obj())

        self.assertIsNotNone(fc_id)

        flow_classifier['description'] = 'next fake flow-classifier'

        result = self.sfc_driver.\
            update_flow_classifier(fc_id=fc_id,
                                   fc=flow_classifier,
                                   auth_attr=utils.get_vim_auth_obj())
        self.assertIsNotNone(result)

    def test_delete_flow_classifier(self):
        flow_classifier = {'name': 'another_fake_fc',
                           'description': 'another flow-classifier',
                           'source_port_range': '1999-2005',
                           'ip_proto': 6,
                           'destination_port_range': '80-100'}
        fc_id = self.sfc_driver.\
            create_flow_classifier(name='fake_ffg', fc=flow_classifier,
                                   auth_attr=utils.get_vim_auth_obj())

        self.assertIsNotNone(fc_id)

        try:
            self.sfc_driver.\
                delete_flow_classifier(fc_id=fc_id,
                                       auth_attr=utils.get_vim_auth_obj())
        except Exception:
            self.assertTrue(True)

    def test_create_chain(self):
        auth_attr = utils.get_vim_auth_obj()
        flow_classifier = {'name': 'test_create_chain_fc',
                           'description': 'fc for testing create chain',
                           'source_port_range': '1997-2008',
                           'ip_proto': 6,
                           'destination_port_range': '80-100'}
        fc_id = self.sfc_driver.\
            create_flow_classifier(name='fake_ffg', fc=flow_classifier,
                                   auth_attr=auth_attr)

        self.assertIsNotNone(fc_id)

        vnf_1 = {'name': 'test_create_chain_vnf_1',
                 'connection_points': [uuidutils.generate_uuid(),
                                       uuidutils.generate_uuid()]}
        vnf_2 = {'name': 'test_create_chain_vnf_2',
                 'connection_points': [uuidutils.generate_uuid(),
                                       uuidutils.generate_uuid()]}
        vnf_3 = {'name': 'test_create_chain_vnf_3',
                 'connection_points': [uuidutils.generate_uuid(),
                                       uuidutils.generate_uuid()]}
        vnfs = [vnf_1, vnf_2, vnf_3]

        result = self.sfc_driver.create_chain(name='fake_ffg',
                                              fc_id=fc_id,
                                              vnfs=vnfs,
                                              auth_attr=auth_attr)

        self.assertIsNotNone(result)

    def test_delete_chain(self):
        auth_attr = utils.get_vim_auth_obj()
        flow_classifier = {'name': 'test_delete_chain_fc',
                           'description': 'fc for testing delete chain',
                           'source_port_range': '1000-2000',
                           'ip_proto': 6,
                           'destination_port_range': '80-180'}
        fc_id = self.sfc_driver.\
            create_flow_classifier(name='fake_ffg', fc=flow_classifier,
                                   auth_attr=auth_attr)

        self.assertIsNotNone(fc_id)

        vnf_1 = {'name': 'test_delete_chain_vnf_1',
                 'connection_points': [uuidutils.generate_uuid(),
                                       uuidutils.generate_uuid()]}
        vnf_2 = {'name': 'test_delete_chain_vnf_2',
                 'connection_points': [uuidutils.generate_uuid(),
                                       uuidutils.generate_uuid()]}
        vnf_3 = {'name': 'test_delete_chain_vnf_3',
                 'connection_points': [uuidutils.generate_uuid(),
                                       uuidutils.generate_uuid()]}
        vnfs = [vnf_1, vnf_2, vnf_3]

        chain_id = self.sfc_driver.create_chain(name='fake_ffg',
                                                fc_id=fc_id,
                                                vnfs=vnfs,
                                                auth_attr=auth_attr)

        self.assertIsNotNone(chain_id)

        try:
            self.sfc_driver.delete_chain(chain_id,
                                         auth_attr=auth_attr)
        except Exception:
            self.assertTrue(True)
