# Copyright (c) 2014-2018 China Mobile (SuZhou) Software Technology Co.,Ltd.
# All Rights Reserved
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

import testtools
from unittest import mock

from tacker.common import clients
from tacker import context
from tacker.db.common_services import common_services_db_plugin
from tacker.plugins.common import constants
from tacker.vnfm.infra_drivers.openstack import heat_client as hc
from tacker.vnfm.policy_actions.respawn import respawn as \
    policy_actions_respawn
from tacker.vnfm import vim_client


class VNFActionRespawn(testtools.TestCase):

    def setUp(self):
        super(VNFActionRespawn, self).setUp()
        self.context = context.get_admin_context()
        mock.patch('tacker.db.common_services.common_services_db_plugin.'
                   'CommonServicesPluginDb.create_event'
                   ).start()
        self._cos_db_plugin =\
            common_services_db_plugin.CommonServicesPluginDb()

    @mock.patch.object(clients.OpenstackClients, 'heat')
    @mock.patch.object(hc.HeatClient, 'delete')
    @mock.patch.object(vim_client.VimClient, 'get_vim')
    def test_execute_action(self, mock_get_vim, mock_hc_delete, mock_heat):
        action_respawn = policy_actions_respawn.VNFActionRespawn()
        vnf_dict = {
            'id': 'fake-id',
            'status': 'fake-status',
            'attributes': {
                'monitoring_policy': 'fake-monitoring-policy',
                'failure_count': '1',
                'dead_instance_id_1': '00000000-0000-0000-0000-00000000001'},
            'vim_id': 'fake-vim-id',
            'vim_auth': 'fake-vim-auth',
            'instance_id': '00000000-0000-0000-0000-000000000002',
            'placement_attr': {
                'region_name': 'fake-region-name'}}
        mock_get_vim.return_value = {'vim_auth': {
            'auth_url': 'http://fake-url/identity/v3'
        }}
        mock_hc_delete.return_value = True
        plugin = mock.Mock()
        plugin._mark_vnf_dead.return_value = True
        plugin.create_vnf_sync.return_value = {'id': 'fake-id'}
        plugin._vnf_monitor = mock.Mock()
        action_respawn.execute_action(plugin, self.context, vnf_dict, None)
        self._cos_db_plugin.create_event.assert_called_once_with(
            self.context, res_id=vnf_dict['id'],
            res_state=vnf_dict['status'],
            res_type=constants.RES_TYPE_VNF,
            evt_type=constants.RES_EVT_MONITOR,
            tstamp=mock.ANY, details="ActionRespawnHeat invoked")
        mock_get_vim.assert_called_once_with(self.context, vnf_dict['vim_id'])
        plugin.create_vnf_sync.assert_called_with(self.context, vnf_dict)
        plugin._vnf_monitor.mark_dead.assert_called_once_with(vnf_dict['id'])
