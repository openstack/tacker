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

from tacker.tests import constants
from tacker.tests.functional import base
from tacker.tests.utils import read_file

import yaml


class VnfmTestParam(base.BaseTackerTest):
    def _test_vnfd_create(self, vnfd_file):
        yaml_input = dict()
        yaml_input['tosca'] = read_file(vnfd_file)
        toscal = yaml_input['tosca']
        req_dict = {'vnfd': {'attributes': {'vnfd': toscal}}}

        # Create vnfd
        vnfd_instance = self.client.create_vnfd(body=req_dict)
        self.assertIsNotNone(vnfd_instance)
        vnfd_id = vnfd_instance['vnfd']['id']
        self.assertIsNotNone(vnfd_id)
        return vnfd_instance

    def _test_vnfd_delete(self, vnfd_instance):
        # Delete vnfd
        vnfd_id = vnfd_instance['vnfd']['id']
        self.assertIsNotNone(vnfd_id)
        try:
            self.client.delete_vnfd(vnfd_id)
        except Exception:
            assert False, "vnfd Delete failed"
        try:
            vfnd_d = self.client.show_vnfd(vnfd_id)
        except Exception:
            assert True, "Vnfd Delete success" + str(vfnd_d) + str(Exception)

    def _test_vnf_create(self, vnfd_instance, vnf_name, vnf_value_file):
        # Create the vnf with values
        vnfd_id = vnfd_instance['vnfd']['id']
        values_str = read_file(vnf_value_file)

        # Create vnf with values file
        vnf_dict = dict()
        vnf_dict = {'vnf': {'vnfd_id': vnfd_id, 'name': vnf_name,
                    'attributes': {'param_values': values_str}}}
        vnf_instance = self.client.create_vnf(body=vnf_dict)

        self.validate_vnf_instance(vnfd_instance, vnf_instance)
        vnf_id = vnf_instance['vnf']['id']
        vnf_current_status = self.wait_until_vnf_active(
            vnf_id,
            constants.VNF_CIRROS_CREATE_TIMEOUT,
            constants.ACTIVE_SLEEP_TIME)
        self.assertEqual('ACTIVE', vnf_current_status)
        self.assertIsNotNone(self.client.show_vnf(vnf_id)['vnf']['mgmt_url'])
        vnf_instance = self.client.show_vnf(vnf_id)

        # Verify values dictionary is same as param values from vnf_show
        input_dict = yaml.load(values_str)
        param_values = vnf_instance['vnf']['attributes']['param_values']
        param_values_dict = yaml.load(param_values)
        self.assertEqual(input_dict, param_values_dict)
        return vnf_instance

    def _test_vnf_delete(self, vnf_instance):
        # Delete Vnf
        vnf_id = vnf_instance['vnf']['id']
        try:
            self.client.delete_vnf(vnf_id)
        except Exception:
            assert False, "vnf Delete failed"

        try:
            vfn_d = self.client.show_vnf(vnf_id)
        except Exception:
            assert True, "Vnf Delete success" + str(vfn_d) + str(Exception)

    def test_vnfd_param(self):
        vnfd_instance = self._test_vnfd_create('sample_cirros_vnf_param.yaml')
        self._test_vnfd_delete(vnfd_instance)

    def test_vnf_param(self):
        vnfd_instance = self._test_vnfd_create('sample_cirros_vnf_param.yaml')
        vnf_instance = self._test_vnf_create(vnfd_instance,
                                             'test_vnf_with_parameters',
                                             'sample_cirros_vnf_values.yaml')
        self._test_vnf_delete(vnf_instance)
        self._test_vnfd_delete(vnfd_instance)
