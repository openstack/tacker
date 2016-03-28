# Copyright 2015 Brocade Communications System, Inc.
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

from oslo_config import cfg

from tacker.tests import constants
from tacker.tests.functional import base
from tacker.tests.utils import read_file

CONF = cfg.CONF
VNF_CIRROS_CREATE_TIMEOUT = 120


class VnfTestCreate(base.BaseTackerTest):
    def _test_create_delete_vnf(self, vnf_name, vim_id=None):
        data = dict()
        data['tosca'] = read_file('sample_cirros_vnf_no_monitoring.yaml')
        toscal = data['tosca']
        tosca_arg = {'vnfd': {'attributes': {'vnfd': toscal}}}

        # Create vnfd with tosca template
        vnfd_instance = self.client.create_vnfd(body=tosca_arg)
        self.assertIsNotNone(vnfd_instance)

        # Create vnf with vnfd_id
        vnfd_id = vnfd_instance['vnfd']['id']
        vnf_arg = {'vnf': {'vnfd_id': vnfd_id, 'name': vnf_name}}
        if vim_id:
            vnf_arg['vnf']['vim_id'] = vim_id
        vnf_instance = self.client.create_vnf(body=vnf_arg)
        self.validate_vnf_instance(vnfd_instance, vnf_instance)

        vnf_id = vnf_instance['vnf']['id']
        vnf_current_status = self.wait_until_vnf_active(
            vnf_id,
            constants.VNF_CIRROS_CREATE_TIMEOUT,
            constants.ACTIVE_SLEEP_TIME)
        self.assertEqual(vnf_current_status, 'ACTIVE')
        self.assertIsNotNone(self.client.show_vnf(vnf_id)['vnf']['mgmt_url'])
        if vim_id:
            self.assertEqual(vnf_instance['vnf']['vim_id'], vim_id)

        # Delete vnf_instance with vnf_id
        try:
            self.client.delete_vnf(vnf_id)
        except Exception:
            assert False, "vnf Delete failed"

        # Delete vnfd_instance
        try:
            self.client.delete_vnfd(vnfd_id)
        except Exception:
            assert False, "vnfd Delete failed"

    def test_create_delete_vnf_with_default_vim(self):
        self._test_create_delete_vnf(
            vnf_name='test_vnf_with_cirros_no_monitoring')

    def test_create_delete_vnf_with_vim_id(self):
        vim_list = self.client.list_vims()
        vim0_id = self.get_vim(vim_list, 'VIM0')['id']
        self._test_create_delete_vnf(vim_id=vim0_id,
                           vnf_name='test_vnf_with_cirros_with_default_vim_id')
