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
#

from datetime import datetime
from unittest import mock

from oslo_utils import uuidutils

from tacker import context
from tacker.db.nfvo import nfvo_db
from tacker.objects import heal_vnf_request
from tacker.tests.unit.db import base as db_base
from tacker.vnfm import plugin
from tacker.vnfm.policy_actions.vdu_autoheal import vdu_autoheal


vnf_dict = {
    'id': uuidutils.generate_uuid(),
    'mgmt_ip_address': '{"VDU1": "a.b.c.d"}',
    'vim_id': '6261579e-d6f3-49ad-8bc3-a9cb974778ff',
    'instance_id': 'a737497c-761c-11e5-89c3-9cb6541d805d',
    'attributes': {
        'heat_template': {
            'resources': {
                'VDU1': {
                    'properties': {
                        'networks': [{'port': {'get_resource': 'CP1'}}]}
                }
            }
        }
    }
}


class FakeDriverManager(mock.Mock):
    def invoke(self, *args, **kwargs):
        if 'create' in args:
            return uuidutils.generate_uuid()

        if 'get_resource_info' in args:
            return {'resources': {'name': 'dummy_vnf',
                                  'type': 'dummy',
                                  'id': uuidutils.generate_uuid()}}


class FakeVNFMonitor(mock.Mock):
    pass


class TestVNFActionVduAutoheal(db_base.SqlTestCase):

    def setUp(self):
        super(TestVNFActionVduAutoheal, self).setUp()
        self.context = context.get_admin_context()
        self._mock_device_manager()
        self._mock_vnf_monitor()
        self._insert_dummy_vim()
        self.vnfm_plugin = plugin.VNFMPlugin()
        self.vdu_autoheal = vdu_autoheal.VNFActionVduAutoheal()
        self.addCleanup(mock.patch.stopall)

    def _mock_device_manager(self):
        self._device_manager = mock.Mock(wraps=FakeDriverManager())
        self._device_manager.__contains__ = mock.Mock(
            return_value=True)
        fake_device_manager = mock.Mock()
        fake_device_manager.return_value = self._device_manager
        self._mock(
            'tacker.common.driver_manager.DriverManager', fake_device_manager)

    def _mock_vnf_monitor(self):
        self._vnf_monitor = mock.Mock(wraps=FakeVNFMonitor())
        fake_vnf_monitor = mock.Mock()
        fake_vnf_monitor.return_value = self._vnf_monitor
        self._mock(
            'tacker.vnfm.monitor.VNFMonitor', fake_vnf_monitor)

    def _insert_dummy_vim(self):
        session = self.context.session
        vim_db = nfvo_db.Vim(
            id='6261579e-d6f3-49ad-8bc3-a9cb974778ff',
            tenant_id='ad7ebc56538745a08ef7c5e97f8bd437',
            name='fake_vim',
            description='fake_vim_description',
            type='test_vim',
            status='Active',
            deleted_at=datetime.min,
            placement_attr={'regions': ['RegionOne']})
        vim_auth_db = nfvo_db.VimAuth(
            vim_id='6261579e-d6f3-49ad-8bc3-a9cb974778ff',
            password='encrypted_pw',
            auth_url='http://localhost:5000',
            vim_project={'name': 'test_project'},
            auth_cred={'username': 'test_user', 'user_domain_id': 'default',
                       'project_domain_id': 'default'})
        session.add(vim_db)
        session.add(vim_auth_db)
        session.flush()

    @mock.patch('tacker.vnfm.plugin.VNFMPlugin.heal_vnf')
    @mock.patch('yaml.safe_load')
    @mock.patch('tacker.objects.HealVnfRequest')
    def test_vdu_autoheal_execute_action(self, mock_heal_vnf_request,
                                         mock_safe_load,
                                         mock_heal_vnf):
        # Here yaml.safe_load is mock as in the test case i am passing
        # vnf_dict containing having vnf_dict['attributes']['heat_template']
        # value in json format so while excution it giving the error as
        # dict object has no read attribute where as in actual execution the
        # value of vnf_dict['attributes']['heat_template'] is in ymal format.
        mock_safe_load.return_value = vnf_dict['attributes']['heat_template']
        resource_list = ['VDU1', 'CP1']
        additional_params = []
        for resource in resource_list:
            additional_paramas_obj = heal_vnf_request.HealVnfAdditionalParams(
                parameter=resource,
                cause=["Unable to reach while monitoring resource: '%s'" %
                       resource])
            additional_params.append(additional_paramas_obj)
        heal_request_data_obj = heal_vnf_request.HealVnfRequest(
            cause='VNF monitoring fails.',
            additional_params=additional_params)
        mock_heal_vnf_request.return_value = heal_request_data_obj
        self.vdu_autoheal.execute_action(self.vnfm_plugin, self.context,
                                         vnf_dict, args={'vdu_name': 'VDU1'})
        mock_heal_vnf.assert_called_once_with(self.context, vnf_dict['id'],
                                              heal_request_data_obj)

    @mock.patch('tacker.vnfm.policy_actions.vdu_autoheal.'
                'vdu_autoheal.LOG')
    def test_vdu_autoheal_action_with_no_vdu_name(self, mock_log):
        expected_error_msg = ("VDU resource of vnf '%s' is not present for "
                              "autoheal." % vnf_dict['id'])
        self.vdu_autoheal.execute_action(self.vnfm_plugin, self.context,
                                         vnf_dict, args={})
        mock_log.error.assert_called_with(expected_error_msg)
