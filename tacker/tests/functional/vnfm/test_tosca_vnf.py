# Copyright 2016 Brocade Communications System, Inc.
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

import time
import unittest
import yaml

from novaclient import exceptions
from oslo_config import cfg

from tacker.plugins.common import constants as evt_constants
from tacker.tests import constants
from tacker.tests.functional import base
from tacker.tests.utils import read_file


CONF = cfg.CONF
VNF_CIRROS_CREATE_TIMEOUT = 120


class VnfTestToscaCreate(base.BaseTackerTest):
    def _test_create_vnf(self, vnfd_file, vnf_name,
                         template_source="onboarded"):
        data = dict()
        values_str = read_file(vnfd_file)
        data['tosca'] = values_str
        toscal = data['tosca']
        tosca_arg = {'vnfd': {'name': vnf_name,
                              'attributes': {'vnfd': toscal}}}

        if template_source == "onboarded":
            # Create vnfd with tosca template
            vnfd_instance = self.client.create_vnfd(body=tosca_arg)
            self.assertIsNotNone(vnfd_instance)

            # Create vnf with vnfd_id
            vnfd_id = vnfd_instance['vnfd']['id']
            vnf_arg = {'vnf': {'vnfd_id': vnfd_id, 'name': vnf_name}}
            vnf_instance = self.client.create_vnf(body=vnf_arg)
            self.validate_vnf_instance(vnfd_instance, vnf_instance)

        if template_source == 'inline':
            # create vnf directly from template
            template = yaml.safe_load(values_str)
            vnf_arg = {'vnf': {'vnfd_template': template, 'name': vnf_name}}
            vnf_instance = self.client.create_vnf(body=vnf_arg)
            vnfd_id = vnf_instance['vnf']['vnfd_id']

        vnf_id = vnf_instance['vnf']['id']
        self.wait_until_vnf_active(
            vnf_id,
            constants.VNF_CIRROS_CREATE_TIMEOUT,
            constants.ACTIVE_SLEEP_TIME)
        vnf_show_out = self.client.show_vnf(vnf_id)['vnf']
        self.assertIsNotNone(vnf_show_out['mgmt_url'])

        input_dict = yaml.safe_load(values_str)
        prop_dict = input_dict['topology_template']['node_templates'][
            'CP1']['properties']

        # Verify if ip_address is static, it is same as in show_vnf
        if prop_dict.get('ip_address'):
            mgmt_url_input = prop_dict.get('ip_address')
            mgmt_info = yaml.safe_load(
                vnf_show_out['mgmt_url'])
            self.assertEqual(mgmt_url_input, mgmt_info['VDU1'])

        # Verify anti spoofing settings
        stack_id = vnf_show_out['instance_id']
        template_dict = input_dict['topology_template']['node_templates']
        for field in template_dict.keys():
            prop_dict = template_dict[field]['properties']
            if prop_dict.get('anti_spoofing_protection'):
                self.verify_antispoofing_in_stack(stack_id=stack_id,
                                                  resource_name=field)

        self.verify_vnf_crud_events(
            vnf_id, evt_constants.RES_EVT_CREATE,
            evt_constants.PENDING_CREATE, cnt=2)
        self.verify_vnf_crud_events(
            vnf_id, evt_constants.RES_EVT_CREATE, evt_constants.ACTIVE)
        return vnfd_id, vnf_id

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

    def _test_cleanup_vnfd(self, vnfd_id, vnf_id):
        # Delete vnfd_instance
        self.addCleanup(self.client.delete_vnfd, vnfd_id)
        self.addCleanup(self.wait_until_vnf_delete, vnf_id,
            constants.VNF_CIRROS_DELETE_TIMEOUT)

    def _test_create_delete_vnf_tosca(self, vnfd_file, vnf_name,
            template_source):
        vnfd_id, vnf_id = self._test_create_vnf(vnfd_file, vnf_name,
                                                template_source)
        servers = self.novaclient().servers.list()
        vdus = []
        for server in servers:
            vdus.append(server.name)
        self.assertIn('test-vdu', vdus)

        port_list = self.neutronclient().list_ports()['ports']
        vdu_ports = []
        for port in port_list:
            vdu_ports.append(port['name'])
        self.assertIn('test-cp', vdu_ports)
        self._test_delete_vnf(vnf_id)
        if template_source == "onboarded":
            self._test_cleanup_vnfd(vnfd_id, vnf_id)

    def test_create_delete_vnf_tosca_from_vnfd(self):
        self._test_create_delete_vnf_tosca('sample-tosca-vnfd.yaml',
                                           'test_tosca_vnf_with_cirros',
                                           'onboarded')

    def test_create_delete_vnf_from_template(self):
        self._test_create_delete_vnf_tosca('sample-tosca-vnfd.yaml',
                                           'test_tosca_vnf_with_cirros_inline',
                                           'inline')

    def test_re_create_delete_vnf(self):
        self._test_create_delete_vnf_tosca('sample-tosca-vnfd.yaml',
                                           'test_vnf',
                                           'inline')
        time.sleep(1)
        self._test_create_delete_vnf_tosca('sample-tosca-vnfd.yaml',
                                           'test_vnf',
                                           'inline')

    def test_create_delete_vnf_static_ip(self):
        vnfd_id, vnf_id = self._test_create_vnf(
            'sample-tosca-vnfd-static-ip.yaml',
            'test_tosca_vnf_with_cirros_no_monitoring')
        self._test_delete_vnf(vnf_id)
        self._test_cleanup_vnfd(vnfd_id, vnf_id)


class VnfTestToscaCreateFlavorCreation(base.BaseTackerTest):
    def test_create_delete_vnf_tosca_no_monitoring(self):
        vnfd_name = 'tosca_vnfd_with_auto_flavor'
        input_yaml = read_file('sample-tosca-vnfd-flavor.yaml')
        tosca_dict = yaml.safe_load(input_yaml)
        tosca_arg = {'vnfd': {'name': vnfd_name, 'attributes': {'vnfd':
                                                                tosca_dict}}}

        # Create vnfd with tosca template
        vnfd_instance = self.client.create_vnfd(body=tosca_arg)
        self.assertIsNotNone(vnfd_instance)

        # Create vnf with vnfd_id
        vnf_name = 'tosca_vnf_with_auto_flavor'
        vnfd_id = vnfd_instance['vnfd']['id']
        vnf_arg = {'vnf': {'vnfd_id': vnfd_id, 'name': vnf_name}}
        vnf_instance = self.client.create_vnf(body=vnf_arg)

        self.validate_vnf_instance(vnfd_instance, vnf_instance)

        vnf_id = vnf_instance['vnf']['id']
        self.wait_until_vnf_active(
            vnf_id,
            constants.VNF_CIRROS_CREATE_TIMEOUT,
            constants.ACTIVE_SLEEP_TIME)
        self.assertIsNotNone(self.client.show_vnf(vnf_id)['vnf']['mgmt_url'])

        self.verify_vnf_crud_events(
            vnf_id, evt_constants.RES_EVT_CREATE,
            evt_constants.PENDING_CREATE, cnt=2)
        self.verify_vnf_crud_events(
            vnf_id, evt_constants.RES_EVT_CREATE, evt_constants.ACTIVE)

        servers = self.novaclient().servers.list()
        vdu_server = None
        for server in servers:
            if 'VDU1_flavor_func' in server.name:
                vdu_server = server
                break
        self.assertIsNotNone(vdu_server)
        flavor_id = server.flavor["id"]
        nova_flavors = self.novaclient().flavors
        flavor = nova_flavors.get(flavor_id)
        self.assertIsNotNone(flavor)
        self.assertEqual(True, "VDU1_flavor_func_flavor" in flavor.name)
        # Delete vnf_instance with vnf_id
        try:
            self.client.delete_vnf(vnf_id)
        except Exception:
            assert False, "vnf Delete failed"

        self.wait_until_vnf_delete(vnf_id,
                                   constants.VNF_CIRROS_DELETE_TIMEOUT)
        self.verify_vnf_crud_events(vnf_id, evt_constants.RES_EVT_DELETE,
                                    evt_constants.PENDING_DELETE, cnt=2)

        # Delete vnfd_instance
        self.addCleanup(self.client.delete_vnfd, vnfd_id)
        self.assertRaises(exceptions.NotFound, nova_flavors.delete,
                          [flavor_id])


class VnfTestToscaCreateImageCreation(base.BaseTackerTest):

    @unittest.skip("Until BUG 1673099")
    def test_create_delete_vnf_tosca_no_monitoring(self):
        vnfd_name = 'tosca_vnfd_with_auto_image'
        input_yaml = read_file('sample-tosca-vnfd-image.yaml')
        tosca_dict = yaml.safe_load(input_yaml)
        tosca_arg = {'vnfd': {'name': vnfd_name, 'attributes': {'vnfd':
                                                                tosca_dict}}}

        # Create vnfd with tosca template
        vnfd_instance = self.client.create_vnfd(body=tosca_arg)
        self.assertIsNotNone(vnfd_instance)

        # Create vnf with vnfd_id
        vnfd_id = vnfd_instance['vnfd']['id']
        vnf_name = 'tosca_vnf_with_auto_image'
        vnf_arg = {'vnf': {'vnfd_id': vnfd_id, 'name': vnf_name}}
        vnf_instance = self.client.create_vnf(body=vnf_arg)

        self.validate_vnf_instance(vnfd_instance, vnf_instance)

        vnf_id = vnf_instance['vnf']['id']
        self.wait_until_vnf_active(
            vnf_id,
            constants.VNF_CIRROS_CREATE_TIMEOUT,
            constants.ACTIVE_SLEEP_TIME)
        self.assertIsNotNone(self.client.show_vnf(vnf_id)['vnf']['mgmt_url'])

        self.verify_vnf_crud_events(
            vnf_id, evt_constants.RES_EVT_CREATE,
            evt_constants.PENDING_CREATE, cnt=2)
        self.verify_vnf_crud_events(
            vnf_id, evt_constants.RES_EVT_CREATE, evt_constants.ACTIVE)

        servers = self.novaclient().servers.list()
        vdu_server = None
        for server in servers:
            if 'VDU1_image_func' in server.name:
                vdu_server = server
                break
        self.assertIsNotNone(vdu_server)
        image_id = vdu_server.image["id"]
        nova_images = self.novaclient().images
        image = nova_images.get(image_id)
        self.assertIsNotNone(image)
        self.assertEqual(True, "VNFImage_image_func" in image.name)
        # Delete vnf_instance with vnf_id
        try:
            self.client.delete_vnf(vnf_id)
        except Exception:
            assert False, "vnf Delete failed"

        self.wait_until_vnf_delete(vnf_id,
                                   constants.VNF_CIRROS_DELETE_TIMEOUT)
        self.verify_vnf_crud_events(vnf_id, evt_constants.RES_EVT_DELETE,
                                    evt_constants.PENDING_DELETE, cnt=2)

        # Delete vnfd_instance
        self.addCleanup(self.client.delete_vnfd, vnfd_id)
        self.assertRaises(exceptions.NotFound, nova_images.delete,
                          [image_id])
