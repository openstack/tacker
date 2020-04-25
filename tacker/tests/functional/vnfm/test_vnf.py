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

import yaml

from oslo_config import cfg

from tacker.plugins.common import constants as evt_constants
from tacker.tests import constants
from tacker.tests.functional import base
from tacker.tests.utils import read_file

CONF = cfg.CONF
VNF_CIRROS_CREATE_TIMEOUT = 120


class VnfTestCreate(base.BaseTackerTest):
    def _test_create_delete_vnf(self, vnf_name, vnfd_name, vim_id=None):
        input_yaml = read_file('sample-tosca-vnfd-no-monitor.yaml')
        tosca_dict = yaml.safe_load(input_yaml)
        tosca_arg = {'vnfd': {'name': vnfd_name,
                     'attributes': {'vnfd': tosca_dict}}}

        # Create vnfd with tosca template
        vnfd_instance = self.client.create_vnfd(body=tosca_arg)
        self.assertIsNotNone(vnfd_instance)

        # Create vnf with vnfd_id
        vnfd_id = vnfd_instance['vnfd']['id']
        self.addCleanup(self.client.delete_vnfd, vnfd_id)

        vnf_arg = {'vnf': {'vnfd_id': vnfd_id, 'name': vnf_name}}
        if vim_id:
            vnf_arg['vnf']['vim_id'] = vim_id
        vnf_instance = self.client.create_vnf(body=vnf_arg)
        self.validate_vnf_instance(vnfd_instance, vnf_instance)

        vnf_id = vnf_instance['vnf']['id']
        self.wait_until_vnf_active(
            vnf_id,
            constants.VNF_CIRROS_CREATE_TIMEOUT,
            constants.ACTIVE_SLEEP_TIME)
        self.assertIsNotNone(self.client.show_vnf(vnf_id)['vnf'][
            'mgmt_ip_address'])
        if vim_id:
            self.assertEqual(vim_id, vnf_instance['vnf']['vim_id'])

        # Get vnf details when vnf is in active state
        vnf_details = self.client.list_vnf_resources(vnf_id)['resources'][0]
        self.assertIn('name', vnf_details)
        self.assertIn('id', vnf_details)
        self.assertIn('type', vnf_details)

        self.verify_vnf_crud_events(
            vnf_id, evt_constants.RES_EVT_CREATE,
            evt_constants.PENDING_CREATE, cnt=2)
        self.verify_vnf_crud_events(
            vnf_id, evt_constants.RES_EVT_CREATE, evt_constants.ACTIVE)

        # update VIM name when VNFs are active.
        # check for exception.
        vim0_id = vnf_instance['vnf']['vim_id']
        msg = "VIM %s is still in use by VNF" % vim0_id
        try:
            update_arg = {'vim': {'name': "vnf_vim"}}
            self.client.update_vim(vim0_id, update_arg)
        except Exception as err:
            self.assertEqual(err.message, msg)
        else:
            self.assertTrue(
                False,
                "Name of vim(s) with active vnf(s) should not be changed!")

        # Delete vnf_instance with vnf_id
        try:
            self.client.delete_vnf(vnf_id)
        except Exception:
            assert False, "vnf Delete failed"

        self.wait_until_vnf_delete(vnf_id,
                                   constants.VNF_CIRROS_DELETE_TIMEOUT)
        self.verify_vnf_crud_events(vnf_id, evt_constants.RES_EVT_DELETE,
                                    evt_constants.PENDING_DELETE, cnt=2)

    def test_create_delete_vnf_with_default_vim(self):
        self._test_create_delete_vnf(
            vnf_name='test_vnf_with_cirros_no_monitoring_default_vim',
            vnfd_name='sample_cirros_vnf_no_monitoring_default_vim')

    def test_create_delete_vnf_with_vim_id(self):
        vim_list = self.client.list_vims()
        vim0_id = self.get_vim(vim_list, 'VIM0')['id']
        self._test_create_delete_vnf(
            vim_id=vim0_id,
            vnf_name='test_vnf_with_cirros_vim_id',
            vnfd_name='sample_cirros_vnf_no_monitoring_vim_id')
