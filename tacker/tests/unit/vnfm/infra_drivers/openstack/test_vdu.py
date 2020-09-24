# Copyright 2018 NTT DATA
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

from unittest import mock

from tacker import context
from tacker.db.common_services import common_services_db_plugin
from tacker.objects import heal_vnf_request
from tacker.plugins.common import constants
from tacker.tests.unit import base
from tacker.vnfm.infra_drivers.openstack import vdu


vnf_dict = {
    'attributes': {
        'heat_template': {
            'outputs': {
                'mgmt_ip-VDU1': {
                    'value': {
                        'get_attr': [
                            'CP1', 'fixed_ips', 0, 'ip_address']
                    }
                }
            },
            'description': 'Demo example\n',
            'parameters': {},
            'resources': {
                'VDU1': {
                    'type': 'OS::Nova::Server',
                    'properties': {
                        'user_data_format': 'SOFTWARE_CONFIG',
                        'availability_zone': 'nova',
                        'image': 'cirros-0.4.0-x86_64-disk',
                        'config_drive': False,
                        'flavor': {'get_resource': 'VDU1_flavor'},
                        'networks': [{'port': {'get_resource': 'CP1'}}]
                    }
                },
                'CP1': {
                    'type': 'OS::Neutron::Port',
                    'properties': {
                        'port_security_enabled': False,
                        'network': 'net_mgmt'
                    }
                },
                'VDU1_flavor': {
                    'type': 'OS::Nova::Flavor',
                    'properties': {'vcpus': 1, 'disk': 1, 'ram': 512}
                }
            }
        }
    },
    'status': 'ACTIVE',
    'vnfd_id': '576acf48-b9df-491d-a57c-342de660ec78',
    'tenant_id': '13d2ca8de70d48b2a2e0dbac2c327c0b',
    'vim_id': '3f41faa7-5630-47d2-9d4a-1216953c8887',
    'instance_id': 'd1121d3c-368b-4ac2-b39d-835aa3e4ccd8',
    'placement_attr': {'vim_name': 'openstack-vim'},
    'id': 'a27fc58e-66ae-4031-bba4-efede318c60b',
    'name': 'vnf_create_1'
}


class FakeHeatClient(mock.Mock):

    class Stack(mock.Mock):
        stack_status = 'CREATE_COMPLETE'
        outputs = [{u'output_value': u'192.168.120.31', u'description':
            u'management ip address', u'output_key': u'mgmt_ip-vdu1'}]

    def create(self, *args, **kwargs):
        return {'stack': {'id': '4a4c2d44-8a52-4895-9a75-9d1c76c3e738'}}

    def get(self, id):
        return self.Stack()

    def update(self, stack_id, **kwargs):
        return self.Stack()

    def resource_mark_unhealthy(self, stack_id, resource_name,
                                mark_unhealthy, resource_status_reason):
        return self.Stack()


class TestVDU(base.TestCase):

    def setUp(self):
        super(TestVDU, self).setUp()
        self.context = context.get_admin_context()
        self._mock_heat_client()

        mock.patch('tacker.vnfm.vim_client.VimClient.get_vim').start()
        self.additional_paramas_obj = heal_vnf_request.HealVnfAdditionalParams(
            parameter='VDU1',
            cause=["Unable to reach while monitoring resource: 'VDU1'"])
        self.heal_request_data_obj = heal_vnf_request.HealVnfRequest(
            cause='VNF monitoring fails.',
            stack_id=vnf_dict['instance_id'],
            additional_params=[self.additional_paramas_obj])
        self.heal_vdu = vdu.Vdu(self.context, vnf_dict,
                           self.heal_request_data_obj)

        mock.patch('tacker.db.common_services.common_services_db_plugin.'
                   'CommonServicesPluginDb.create_event'
                   ).start()
        self._cos_db_plugin = \
            common_services_db_plugin.CommonServicesPluginDb()
        self.addCleanup(mock.patch.stopall)

    def _mock_heat_client(self):
        self.heat_client = mock.Mock(wraps=FakeHeatClient())
        fake_heat_client = mock.Mock()
        fake_heat_client.return_value = self.heat_client
        self._mock(
            'tacker.vnfm.infra_drivers.openstack.heat_client.HeatClient',
            fake_heat_client)

    @mock.patch('tacker.vnfm.vim_client.VimClient.get_vim')
    def test_heal_vdu(self, mock_get_vim):
        mock_get_vim.return_value = mock.MagicMock()

        self.heal_vdu.heal_vdu()

        self.heat_client.update.assert_called_once_with(
            stack_id=vnf_dict['instance_id'], existing=True)

        self._cos_db_plugin.create_event.assert_called_with(
            self.context, res_id=vnf_dict['id'],
            res_type=constants.RES_TYPE_VNF, res_state=vnf_dict['status'],
            evt_type=constants.RES_EVT_HEAL, tstamp=mock.ANY,
            details=("HealVnfRequest invoked to update the stack '%s'" %
                     vnf_dict['instance_id']))

    @mock.patch('tacker.vnfm.vim_client.VimClient.get_vim')
    def test_resource_mark_unhealthy(self, mock_get_vim):
        mock_get_vim.return_value = mock.MagicMock()

        self.heal_vdu._resource_mark_unhealthy()

        self.heat_client.resource_mark_unhealthy.assert_called_once_with(
            stack_id=vnf_dict['instance_id'],
            resource_name=self.additional_paramas_obj.parameter,
            mark_unhealthy=True,
            resource_status_reason=self.additional_paramas_obj.cause)

        self._cos_db_plugin.create_event.assert_called_with(
            self.context, res_id=vnf_dict['id'],
            res_type=constants.RES_TYPE_VNF, res_state=vnf_dict['status'],
            evt_type=constants.RES_EVT_HEAL, tstamp=mock.ANY,
            details="HealVnfRequest invoked to mark resource 'VDU1' "
                    "to unhealthy.")
