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

import os

from oslo_config import cfg
from toscaparser import tosca_template
import unittest
import yaml


from tacker.common import utils
from tacker.plugins.common import constants as evt_constants
from tacker.tests import constants
from tacker.tests.functional import base
from tacker.tests.utils import read_file
from tacker.tosca import utils as toscautils

CONF = cfg.CONF
SOFTWARE_DEPLOYMENT = 'OS::Heat::SoftwareDeployment'


class VnfTestToscaVNFC(base.BaseTackerTest):

    @unittest.skip("Until BUG 1673012")
    def test_create_delete_tosca_vnfc(self):
        input_yaml = read_file('sample_tosca_vnfc.yaml')
        tosca_dict = yaml.safe_load(input_yaml)
        path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "../../etc/samples"))
        vnfd_name = 'sample-tosca-vnfc'
        tosca_dict['topology_template']['node_templates'
                                        ]['firewall_vnfc'
                                          ]['interfaces'
                                            ]['Standard']['create'] = path \
            + '/install_vnfc.sh'
        tosca_arg = {'vnfd': {'name': vnfd_name,
                              'attributes': {'vnfd': tosca_dict}}}

        # Create vnfd with tosca template
        vnfd_instance = self.client.create_vnfd(body=tosca_arg)
        self.assertIsNotNone(vnfd_instance)

        # Create vnf with vnfd_id
        vnfd_id = vnfd_instance['vnfd']['id']
        vnf_arg = {'vnf': {'vnfd_id': vnfd_id, 'name':
                           "test_tosca_vnfc"}}
        vnf_instance = self.client.create_vnf(body=vnf_arg)

        vnf_id = vnf_instance['vnf']['id']
        self.wait_until_vnf_active(vnf_id,
                                   constants.VNFC_CREATE_TIMEOUT,
                                   constants.ACTIVE_SLEEP_TIME)
        self.assertEqual('ACTIVE',
                         self.client.show_vnf(vnf_id)['vnf']['status'])
        self.validate_vnf_instance(vnfd_instance, vnf_instance)

        self.verify_vnf_crud_events(
            vnf_id, evt_constants.RES_EVT_CREATE, evt_constants.PENDING_CREATE,
            cnt=2)
        self.verify_vnf_crud_events(
            vnf_id, evt_constants.RES_EVT_CREATE, evt_constants.ACTIVE)

        # Validate mgmt_url with input yaml file
        mgmt_url = self.client.show_vnf(vnf_id)['vnf']['mgmt_url']
        self.assertIsNotNone(mgmt_url)
        mgmt_dict = yaml.safe_load(str(mgmt_url))

        input_dict = yaml.safe_load(input_yaml)
        toscautils.updateimports(input_dict)

        tosca = tosca_template.ToscaTemplate(parsed_params={}, a_file=False,
                          yaml_dict_tpl=input_dict)

        vdus = toscautils.findvdus(tosca)

        self.assertEqual(len(vdus), len(mgmt_dict.keys()))
        for vdu in vdus:
            self.assertIsNotNone(mgmt_dict[vdu.name])
            self.assertEqual(True, utils.is_valid_ipv4(mgmt_dict[vdu.name]))

        # Check the status of SoftwareDeployment
        heat_stack_id = self.client.show_vnf(vnf_id)['vnf']['instance_id']
        resource_types = self.h_client.resources
        resources = resource_types.list(stack_id=heat_stack_id)
        for resource in resources:
            resource = resource.to_dict()
            if resource['resource_type'] == \
                    SOFTWARE_DEPLOYMENT:
                self.assertEqual('CREATE_COMPLETE',
                    resource['resource_status'])
                break

        # Delete vnf_instance with vnf_id
        try:
            self.client.delete_vnf(vnf_id)
        except Exception:
            assert False, "vnf Delete of test_vnf_with_multiple_vdus failed"

        self.wait_until_vnf_delete(vnf_id,
                                   constants.VNF_CIRROS_DELETE_TIMEOUT)
        self.verify_vnf_crud_events(vnf_id, evt_constants.RES_EVT_DELETE,
                                    evt_constants.PENDING_DELETE, cnt=2)

        # Delete vnfd_instance
        self.addCleanup(self.client.delete_vnfd, vnfd_id)
