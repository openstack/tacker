# Copyright 2015 Brocade Communications System, Inc.
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

import codecs
import os
import yaml

from tacker import context
from tacker.extensions import vnfm
from tacker import objects
from tacker.tests.unit import base
from tacker.tests import uuidsentinel
from tacker.vnfm.infra_drivers.openstack.translate_template import TOSCAToHOT


class TestEtsiTranslateTemplate(base.TestCase):

    def setUp(self):
        super(TestEtsiTranslateTemplate, self).setUp()
        self.tth = TOSCAToHOT(None, None)
        self.tth.fields = {}
        self.tth.vnf = {}
        self.tth.vnf['attributes'] = {}

    def _get_template(self, name):
        filename = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), name)
        with codecs.open(filename, encoding='utf-8', errors='strict') as f:
            return f.read()

    def _load_yaml(self, yaml_name, update_import=False):
        filename = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), yaml_name)
        file_abspath = os.path.dirname(os.path.abspath(filename))
        with open(filename, 'r') as f:
            heat_yaml = f.read()
            heat_dict = yaml.safe_load(heat_yaml)
            if update_import:
                self._update_imports(heat_dict, file_abspath)
            return heat_dict

    def _update_imports(self, yaml_dict, file_abspath):
        imports = yaml_dict['imports']
        new_imports = []
        for i in imports:
            new_imports.append(file_abspath + '/' + i)
        yaml_dict['imports'] = new_imports

    def test_generate_hot_from_tosca(self):
        tosca_file = './data/etsi_nfv/' \
            'tosca_generate_hot_from_tosca.yaml'
        hot_file = './data/etsi_nfv/hot/' \
            'hot_generate_hot_from_tosca.yaml'
        vnfd_dict = self._load_yaml(tosca_file, update_import=True)

        # Input params
        dev_attrs = {}

        data = [{
            "id": 'VL1',
            "resource_id": 'neutron-network-uuid_VL1',
                "ext_cps": [{
                    "cpd_id": "CP1",
                    "cp_config": [{
                        "cp_protocol_data": [{
                            "layer_protocol": "IP_OVER_ETHERNET",
                            "ip_over_ethernet": {
                                "mac_address": 'fa:16:3e:11:11:11',
                                "ip_addresses": [{
                                    'type': 'IPV4',
                                    'fixed_addresses': ['1.1.1.1'],
                                    'subnet_id': 'neutron-subnet-uuid_CP1'}]}
                        }]
                    }]}]},
               {
                "id": 'VL2',
                "resource_id": 'neutron-network-uuid_VL2',
                "ext_cps": [{
                    "cpd_id": 'CP2',
                    "cp_config": [{
                        "link_port_id": uuidsentinel.link_port_id,
                        "cp_protocol_data": [{
                            "layer_protocol": "IP_OVER_ETHERNET"}]}]
                }],
                "ext_link_ports": [{
                    "id": uuidsentinel.link_port_id,
                    "resource_handle": {
                        "resource_id": 'neutron-port-uuid_CP2'}
                }]}]

        ext_mg_vl = [{'id': 'VL3', 'vnf_virtual_link_desc_id': 'VL3',
                      'resource_id': 'neutron-network-uuid_VL3'}]
        request = {'ext_managed_virtual_links': ext_mg_vl,
                   'ext_virtual_links': data, 'flavour_id': 'simple'}
        ctxt = context.get_admin_context()
        inst_req_info = objects.InstantiateVnfRequest.obj_from_primitive(
            request, ctxt)

        # image and info
        grant_info = {
            'VDU1': [objects.VnfResource(id=uuidsentinel.id,
                    vnf_instance_id=uuidsentinel.vnf_instance_id,
                    resource_type='image',
                    resource_identifier='glance-image-uuid_VDU1')]}

        self.tth._generate_hot_from_tosca(vnfd_dict, dev_attrs,
                                     inst_req_info, grant_info)

        expected_hot_tpl = self._load_yaml(hot_file)
        actual_hot_tpl = yaml.safe_load(self.tth.heat_template_yaml)
        self.assertEqual(expected_hot_tpl, actual_hot_tpl)

    def test_generate_hot_from_tosca_with_scaling(self):
        tosca_file = './data/etsi_nfv/' \
            'tosca_generate_hot_from_tosca_with_scaling.yaml'
        hot_file = './data/etsi_nfv/hot/' \
            'scaling/' \
            'hot_generate_hot_from_tosca_with_scaling.yaml'
        hot_aspect_file = './data/etsi_nfv/hot/' \
            'scaling/' \
            'worker_instance.hot.yaml'
        vnfd_dict = self._load_yaml(tosca_file, update_import=True)

        # Input params
        dev_attrs = {}

        data = [{
            "id": 'VL1',
            "resource_id": 'neutron-network-uuid_VL1',
            "ext_cps": [{
                "cpd_id": "CP1",
                "cp_config": [{
                    "cp_protocol_data": [{
                        "layer_protocol": "IP_OVER_ETHERNET",
                        "ip_over_ethernet": {
                            "ip_addresses": [{
                                'type': 'IPV4',
                                'subnet_id': 'neutron-subnet-uuid_CP1'}]}}]
                }]}]},
            {
            "id": 'VL2',
                "resource_id": 'neutron-network-uuid_VL2',
                "ext_cps": [{
                    "cpd_id": 'CP2',
                    "cp_config": [{
                        "link_port_id": uuidsentinel.link_port_id,
                        "cp_protocol_data": [{
                            "layer_protocol": "IP_OVER_ETHERNET"}]}]
                }],
                "ext_link_ports": [{
                    "id": uuidsentinel.link_port_id,
                    "resource_handle": {
                        "resource_id": 'neutron-port-uuid_CP2'}
                }]}]

        ext_mg_vl = [{'id': 'VL3', 'vnf_virtual_link_desc_id': 'VL3',
                      'resource_id': 'neutron-network-uuid_VL3'}]
        request = {'ext_managed_virtual_links': ext_mg_vl,
                   'ext_virtual_links': data, 'flavour_id': 'simple',
                   'instantiation_level_id': 'instantiation_level_1'}
        ctxt = context.get_admin_context()
        inst_req_info = objects.InstantiateVnfRequest.obj_from_primitive(
            request, ctxt)

        # image and info
        grant_info = {
            'VDU1': [objects.VnfResource(id=uuidsentinel.id,
                    vnf_instance_id=uuidsentinel.vnf_instance_id,
                    resource_type='image',
                    resource_identifier='glance-image-uuid_VDU1')]}

        self.tth._generate_hot_from_tosca(vnfd_dict, dev_attrs,
                                     inst_req_info, grant_info)

        expected_hot_tpl = self._load_yaml(hot_file)
        actual_hot_tpl = yaml.safe_load(self.tth.heat_template_yaml)
        self.assertEqual(expected_hot_tpl, actual_hot_tpl)

        expected_hot_aspect_tpl = self._load_yaml(hot_aspect_file)
        actual_hot_aspect_tpl = \
            yaml.safe_load(
                self.tth.nested_resources['worker_instance.hot.yaml'])
        self.assertEqual(expected_hot_aspect_tpl, actual_hot_aspect_tpl)

    def test_generate_hot_from_tosca_with_substitution_mappings_error(self):
        tosca_file = './data/etsi_nfv/' \
            'tosca_generate_hot_from_tosca_' \
            'with_substitution_mappings_error.yaml'
        vnfd_dict = self._load_yaml(tosca_file, update_import=True)

        dev_attrs = {}

        self.assertRaises(vnfm.InvalidParamsForSM,
                          self.tth._generate_hot_from_tosca,
                          vnfd_dict,
                          dev_attrs,
                          None,
                          None)

    def test_generate_hot_from_tosca_with_params_error(self):
        tosca_file = './data/etsi_nfv/' \
            'tosca_generate_hot_from_tosca_with_params_error.yaml'
        param_file = './data/etsi_nfv/' \
            'tosca_params_error.yaml'
        vnfd_dict = self._load_yaml(tosca_file, update_import=True)

        param_yaml = self._get_template(param_file)
        dev_attrs = {
            u'param_values': param_yaml
        }

        self.assertRaises(vnfm.ParamYAMLNotWellFormed,
                          self.tth._generate_hot_from_tosca,
                          vnfd_dict,
                          dev_attrs,
                          None,
                          None)

    def test_generate_hot_from_tosca_parser_error(self):
        tosca_file = './data/etsi_nfv/' \
            'tosca_generate_hot_from_tosca_parser_error.yaml'
        vnfd_dict = self._load_yaml(tosca_file, update_import=True)

        # Input params
        dev_attrs = {}

        self.assertRaises(vnfm.ToscaParserFailed,
                          self.tth._generate_hot_from_tosca,
                          vnfd_dict,
                          dev_attrs,
                          None,
                          None)

    def test_generate_hot_from_tosca_translator_error(self):
        tosca_file = './data/etsi_nfv/' \
            'tosca_generate_hot_from_tosca_translator_error.yaml'
        vnfd_dict = self._load_yaml(tosca_file, update_import=True)

        # Input params
        dev_attrs = {}

        self.assertRaises(vnfm.HeatTranslatorFailed,
                          self.tth._generate_hot_from_tosca,
                          vnfd_dict,
                          dev_attrs,
                          None,
                          None)

    def test_generate_hot_from_tosca_with_scaling_invalid_inst_req(self):
        tosca_file = './data/etsi_nfv/' \
            'tosca_generate_hot_from_tosca_with_scaling_invalid_inst_req.yaml'
        vnfd_dict = self._load_yaml(tosca_file, update_import=True)

        # Input params
        dev_attrs = {}

        data = [{
            "id": 'VL1',
            "resource_id": 'neutron-network-uuid_VL1',
            "ext_cps": [{
                "cpd_id": "CP1",
                "cp_config": [{
                    "cp_protocol_data": [{
                        "layer_protocol": "IP_OVER_ETHERNET",
                        "ip_over_ethernet": {
                            "ip_addresses": [{
                                'type': 'IPV4',
                                'fixed_addresses': ['1.1.1.1'],
                                'subnet_id': 'neutron-subnet-uuid_CP1'}]}
                    }]
                }]
            }]}
        ]

        request = {'ext_virtual_links': data, 'flavour_id': 'simple'}
        ctxt = context.get_admin_context()
        inst_req_info = objects.InstantiateVnfRequest.obj_from_primitive(
            request, ctxt)

        self.assertRaises(vnfm.InvalidInstReqInfoForScaling,
                          self.tth._generate_hot_from_tosca,
                          vnfd_dict,
                          dev_attrs,
                          inst_req_info,
                          None)
