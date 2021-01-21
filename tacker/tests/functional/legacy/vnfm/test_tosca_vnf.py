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
import yaml

from glanceclient import exc
from novaclient import exceptions
from oslo_config import cfg

from tacker.plugins.common import constants as evt_constants
from tacker.tests import constants
from tacker.tests.functional import base


CONF = cfg.CONF
VNF_CIRROS_CREATE_TIMEOUT = 120


class VnfTestToscaCreate(base.BaseTackerTest):
    def _test_create_vnf(self, vnfd_file, vnf_name,
                         template_source="onboarded"):

        if template_source == "onboarded":
            (vnfd_instance,
             vnf_instance,
             tosca_dict) = self.vnfd_and_vnf_create(vnfd_file, vnf_name)

        if template_source == 'inline':
            vnf_instance, tosca_dict = self.vnfd_and_vnf_create_inline(
                vnfd_file, vnf_name)

        vnfd_id = vnf_instance['vnf']['vnfd_id']
        vnf_id = vnf_instance['vnf']['id']
        self.wait_until_vnf_active(
            vnf_id,
            constants.VNF_CIRROS_CREATE_TIMEOUT,
            constants.ACTIVE_SLEEP_TIME)
        vnf_show_out = self.client.show_vnf(vnf_id)['vnf']
        self.assertIsNotNone(vnf_show_out['mgmt_ip_address'])

        prop_dict = tosca_dict['topology_template']['node_templates'][
            'CP1']['properties']

        # Verify if ip_address is static, it is same as in show_vnf
        if prop_dict.get('ip_address'):
            mgmt_ip_address_input = prop_dict.get('ip_address')
            mgmt_info = yaml.safe_load(
                vnf_show_out['mgmt_ip_address'])
            self.assertEqual(mgmt_ip_address_input, mgmt_info['VDU1'])

        # Verify anti spoofing settings
        stack_id = vnf_show_out['instance_id']
        template_dict = tosca_dict['topology_template']['node_templates']
        for field in template_dict:
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


class VnfTestToscaCreateFlavorCreation(base.BaseTackerTest):
    def test_create_delete_vnf_tosca_no_monitoring(self):
        vnf_name = 'tosca_vnfd_with_auto_flavor'
        vnfd_file = 'sample-tosca-vnfd-flavor.yaml'
        vnfd_instance, vnf_instance, tosca_dict = self.vnfd_and_vnf_create(
            vnfd_file, vnf_name)
        vnf_id = vnf_instance['vnf']['id']
        self.wait_until_vnf_active(
            vnf_id,
            constants.VNF_CIRROS_CREATE_TIMEOUT,
            constants.ACTIVE_SLEEP_TIME)
        self.assertIsNotNone(self.client.show_vnf(vnf_id)['vnf'][
            'mgmt_ip_address'])

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
        self.assertIn('VDU1_flavor_func_flavor', flavor.name)
        # Delete vnf_instance with vnf_id
        try:
            self.client.delete_vnf(vnf_id)
        except Exception:
            assert False, "vnf Delete failed"

        self.wait_until_vnf_delete(vnf_id,
                                   constants.VNF_CIRROS_DELETE_TIMEOUT)
        self.verify_vnf_crud_events(vnf_id, evt_constants.RES_EVT_DELETE,
                                    evt_constants.PENDING_DELETE, cnt=2)

        self.assertRaises(exceptions.NotFound, nova_flavors.delete,
                          [flavor_id])


class VnfTestToscaCreateImageCreation(base.BaseTackerTest):

    def test_create_delete_vnf_tosca_no_monitoring(self):
        vnf_name = 'tosca_vnfd_with_auto_image'
        vnfd_file = 'sample-tosca-vnfd-image.yaml'
        vnfd_instance, vnf_instance, tosca_dict = self.vnfd_and_vnf_create(
            vnfd_file, vnf_name)
        vnf_id = vnf_instance['vnf']['id']
        self.wait_until_vnf_active(
            vnf_id,
            constants.VNF_CIRROS_CREATE_TIMEOUT,
            constants.ACTIVE_SLEEP_TIME)
        self.assertIsNotNone(self.client.show_vnf(vnf_id)['vnf'][
            'mgmt_ip_address'])

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
        glanceclient = self.glanceclient()
        image = glanceclient.images.get(image_id)
        self.assertIsNotNone(image)
        self.assertIn('VNFImage_image_func', image.name)
        # Delete vnf_instance with vnf_id
        try:
            self.client.delete_vnf(vnf_id)
        except Exception:
            assert False, "vnf Delete failed"

        self.wait_until_vnf_delete(vnf_id,
                                   constants.VNF_CIRROS_DELETE_TIMEOUT)
        self.verify_vnf_crud_events(vnf_id, evt_constants.RES_EVT_DELETE,
                                    evt_constants.PENDING_DELETE, cnt=2)

        self.assertRaises(exc.HTTPNotFound,
                          glanceclient.images.delete,
                          [image_id])
