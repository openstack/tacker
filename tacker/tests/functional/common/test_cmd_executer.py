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

import yaml

from oslo_config import cfg

from tacker.common import cmd_executer
from tacker.plugins.common import constants as evt_constants
from tacker.tests import constants
from tacker.tests.functional import base
from tacker.tests.utils import read_file


CONF = cfg.CONF
VNF_CIRROS_CREATE_TIMEOUT = 120


class TestRemoteCommandExecutor(base.BaseTackerTest):

    def _test_create_vnf(self, vnfd_file, vnf_name):
        input_yaml = read_file(vnfd_file)
        tosca_dict = yaml.safe_load(input_yaml)

        # create vnf directly from template
        vnf_arg = {'vnf': {'vnfd_template': tosca_dict, 'name': vnf_name}}
        vnf_instance = self.client.create_vnf(body=vnf_arg)
        vnf_id = vnf_instance['vnf']['id']
        self.wait_until_vnf_active(
            vnf_id,
            constants.VNF_CIRROS_CREATE_TIMEOUT,
            constants.ACTIVE_SLEEP_TIME)
        vnf_show_out = self.client.show_vnf(vnf_id)['vnf']
        self.assertIsNotNone(vnf_show_out['mgmt_ip_address'])

        # Fetch mgmt ip of VNF
        mgmt_ip = eval(vnf_show_out['mgmt_ip_address'])['VDU1']

        return vnf_id, mgmt_ip

    def _test_cmd_executor(self, vnfd_file, vnf_name):
        vnf_id, mgmt_ip = self._test_create_vnf(vnfd_file, vnf_name)

        # Login on VNF instance, and execute 'hostname' command to verify
        # connection and command output.
        usr = 'cirros'
        psswrd = 'gocubsgo'
        cmd = 'hostname'
        rcmd_executor = cmd_executer.RemoteCommandExecutor(user=usr,
                                                           password=psswrd,
                                                           host=mgmt_ip)
        result = rcmd_executor.execute_command(cmd)
        self.assertEqual(cmd, result.get_command())
        self.assertEqual(0, result.get_return_code())
        self.assertIn('test-vdu', result.get_stdout()[0])

        self._test_delete_vnf(vnf_id)

    def _test_delete_vnf(self, vnf_id):
        # Delete vnf_instance with vnf_id
        try:
            self.client.delete_vnf(vnf_id)
        except Exception:
            assert False, "vnf Delete failed"

        self.wait_until_vnf_delete(vnf_id,
                                   constants.VNF_CIRROS_DELETE_TIMEOUT)
        self.verify_vnf_crud_events(vnf_id, evt_constants.RES_EVT_DELETE,
                                    evt_constants.PENDING_DELETE, cnt=2)

    def test_cmd_executor(self):
        self._test_cmd_executor('sample-tosca-vnfd.yaml',
                                'test_tosca_vnf_with_cirros_inline')
