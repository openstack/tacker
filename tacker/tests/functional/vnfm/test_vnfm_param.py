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

from tacker.tests import constants
from tacker.tests.functional import base
from tacker.tests.utils import read_file


class VnfmTestParam(base.BaseTackerTest):
    def _test_vnfd_create(self, vnfd_file):
        yaml_input = read_file(vnfd_file)
        vnfd_name = 'sample_cirros_vnf'
        # TODO(anyone) remove this condition check once old templates
        # are deprecated
        if "tosca_definitions_version" in yaml_input:
            yaml_input = yaml.safe_load(yaml_input)
        req_dict = {'vnfd': {'name': vnfd_name,
                    'attributes': {'vnfd': yaml_input}}}

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

    def _test_vnf_create(self, vnfd_instance, vnf_name, param_values):
        # Create the vnf with values
        vnfd_id = vnfd_instance['vnfd']['id']
        # Create vnf with values file
        vnf_dict = dict()
        vnf_dict = {'vnf': {'vnfd_id': vnfd_id, 'name': vnf_name,
                    'attributes': {'param_values': param_values}}}
        vnf_instance = self.client.create_vnf(body=vnf_dict)

        self.validate_vnf_instance(vnfd_instance, vnf_instance)
        vnf_id = vnf_instance['vnf']['id']
        self.wait_until_vnf_active(
            vnf_id,
            constants.VNF_CIRROS_CREATE_TIMEOUT,
            constants.ACTIVE_SLEEP_TIME)
        self.assertIsNotNone(self.client.show_vnf(vnf_id)['vnf']['mgmt_url'])
        vnf_instance = self.client.show_vnf(vnf_id)

        # Verify values dictionary is same as param values from vnf_show

        param_values = vnf_instance['vnf']['attributes']['param_values']
        param_values_dict = yaml.safe_load(param_values)

        return vnf_instance, param_values_dict

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

    def test_vnf_param(self):
        vnfd_instance = self._test_vnfd_create(
            'sample_cirros_vnf_param.yaml')
        values_str = read_file('sample_cirros_vnf_values.yaml')
        vnf_instance, param_values_dict = self._test_vnf_create(vnfd_instance,
                                             'test_vnf_with_parameters',
                                             values_str)
        # Verify values dictionary is same as param values from vnf_show
        input_dict = yaml.safe_load(values_str)
        self.assertEqual(input_dict, param_values_dict)
        self._test_vnf_delete(vnf_instance)
        vnf_id = vnf_instance['vnf']['id']
        self.addCleanup(self.client.delete_vnfd, vnfd_instance['vnfd']['id'])
        self.addCleanup(self.wait_until_vnf_delete, vnf_id,
            constants.VNF_CIRROS_DELETE_TIMEOUT)

    def test_vnfd_param_tosca_template(self):
        vnfd_instance = self._test_vnfd_create(
            'sample-tosca-vnfd-param.yaml')
        self._test_vnfd_delete(vnfd_instance)

    def test_vnf_param_tosca_template(self):
        vnfd_instance = self._test_vnfd_create(
            'sample-tosca-vnfd-param.yaml')
        values_str = read_file('sample-tosca-vnf-values.yaml')
        values_dict = yaml.safe_load(values_str)
        vnf_instance, param_values_dict = self._test_vnf_create(vnfd_instance,
                                    'test_vnf_with_parameters_tosca_template',
                                                                values_dict)
        self.assertEqual(values_dict, param_values_dict)
        self._test_vnf_delete(vnf_instance)
        vnf_id = vnf_instance['vnf']['id']
        self.addCleanup(self.client.delete_vnfd, vnfd_instance['vnfd']['id'])
        self.addCleanup(self.wait_until_vnf_delete, vnf_id,
            constants.VNF_CIRROS_DELETE_TIMEOUT)
