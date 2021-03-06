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

from tacker import context
from tacker.db.common_services import common_services_db_plugin
from tacker.plugins.common import constants
from tacker.vnfm.policy_actions.autoscaling import autoscaling \
    as policy_actions_autoscaling


class TestVNFActionAutoscaling(testtools.TestCase):

    def setUp(self):
        super(TestVNFActionAutoscaling, self).setUp()
        self.context = context.get_admin_context()
        mock.patch('tacker.db.common_services.common_services_db_plugin.'
                   'CommonServicesPluginDb.create_event'
                   ).start()
        self._cos_db_plugin =\
            common_services_db_plugin.CommonServicesPluginDb()

    def test_execute_action(self):
        action_autoscaling = policy_actions_autoscaling.VNFActionAutoscaling()
        vnf_dict = {
            'id': '00000000-0000-0000-0000-000000000001',
            'status': 'fake-status'}
        plugin = mock.Mock()
        plugin.create_vnf_scale.return_value = None
        action_autoscaling.execute_action(plugin, self.context, vnf_dict, None)
        self._cos_db_plugin.create_event.assert_called_once_with(
            self.context, res_id=vnf_dict['id'],
            res_state=vnf_dict['status'],
            res_type=constants.RES_TYPE_VNF,
            evt_type=constants.RES_EVT_MONITOR,
            tstamp=mock.ANY, details="ActionAutoscalingHeat invoked")
        plugin.create_vnf_scale.assert_called_once_with(
            self.context, vnf_dict['id'], None)
