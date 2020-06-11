# Copyright 2016 - Nokia
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

import testtools
import yaml

from tacker.extensions import vnfm
from tacker.tosca import utils as toscautils
from toscaparser import tosca_template
from translator.hot import tosca_translator


def _get_template(name):
    filename = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "../infra_drivers/openstack/data/", name)
    with codecs.open(filename, encoding='utf-8', errors='strict') as f:
        return f.read()


class TestToscaUtils(testtools.TestCase):
    tosca_openwrt = _get_template('test_tosca_openwrt.yaml')
    vnfd_dict = yaml.safe_load(tosca_openwrt)
    toscautils.updateimports(vnfd_dict)

    def setUp(self):
        super(TestToscaUtils, self).setUp()
        self.tosca = tosca_template.ToscaTemplate(
            parsed_params={}, a_file=False, yaml_dict_tpl=self.vnfd_dict)
        self.tosca_flavor = _get_template('test_tosca_flavor.yaml')

    def test_updateimport(self):
        importspath = os.path.abspath('./tacker/tosca/lib/')
        file1 = importspath + '/tacker_defs.yaml'
        file2 = importspath + '/tacker_nfv_defs.yaml'
        expected_imports = [file1, file2]
        self.assertEqual(expected_imports, self.vnfd_dict['imports'])

    def test_get_mgmt_driver(self):
        expected_mgmt_driver = 'openwrt'
        mgmt_driver = toscautils.get_mgmt_driver(self.tosca)
        self.assertEqual(expected_mgmt_driver, mgmt_driver)

    def test_get_vdu_monitoring(self):
        expected_monitoring = {'vdus': {'VDU1': {'ping': {
                               'actions':
                               {'failure': 'respawn'},
                               'name': 'ping',
                               'parameters': {'count': 3,
                                              'interval': 10},
                               'monitoring_params': {'count': 3,
                                                  'interval': 10}}}}}
        monitoring = toscautils.get_vdu_monitoring(self.tosca)
        self.assertEqual(expected_monitoring, monitoring)

    def test_get_mgmt_ports(self):
        expected_mgmt_ports = {'mgmt_ip-VDU1': 'CP1'}
        mgmt_ports = toscautils.get_mgmt_ports(self.tosca)
        self.assertEqual(expected_mgmt_ports, mgmt_ports)

    def test_post_process_template(self):
        tosca_post_process_tpl = _get_template(
            'test_tosca_post_process_template.yaml')
        vnfd_dict = yaml.safe_load(tosca_post_process_tpl)
        toscautils.updateimports(vnfd_dict)
        tosca = tosca_template.ToscaTemplate(parsed_params={}, a_file=False,
                                             yaml_dict_tpl=vnfd_dict)
        toscautils.post_process_template(tosca)

        invalidNodes = 0
        deletedProperties = 0
        convertedValues = 0
        convertedProperties = 0

        for nt in tosca.nodetemplates:
            if (nt.type_definition.is_derived_from(toscautils.MONITORING) or
                    nt.type_definition.is_derived_from(toscautils.FAILURE) or
                    nt.type_definition.is_derived_from(toscautils.PLACEMENT)):
                invalidNodes += 1

            if nt.type in toscautils.delpropmap:
                for prop in toscautils.delpropmap[nt.type]:
                    for p in nt.get_properties_objects():
                        if prop == p.name:
                            deletedProperties += 1

            if nt.type in toscautils.convert_prop_values:
                for prop in toscautils.convert_prop_values[nt.type]:
                    convertmap = toscautils.convert_prop_values[nt.type][prop]
                    for p in nt.get_properties_objects():
                        if (prop == p.name and
                                p.value in convertmap):
                            convertedValues += 1

            if nt.type in toscautils.convert_prop:
                for prop in toscautils.convert_prop[nt.type]:
                    for p in nt.get_properties_objects():
                        if prop == p.name:
                            convertedProperties += 1

            if nt.name == 'VDU1':
                vdu1_hints = nt.get_properties().get('scheduler_hints')
                vdu1_rsv = vdu1_hints.value.get('reservation')

        self.assertEqual(0, invalidNodes)
        self.assertEqual(0, deletedProperties)
        self.assertEqual(0, convertedValues)
        self.assertEqual(0, convertedProperties)
        self.assertEqual(vdu1_rsv, '459e94c9-efcd-4320-abf5-8c18cd82c331')

    def test_post_process_heat_template(self):
        tosca1 = tosca_template.ToscaTemplate(parsed_params={}, a_file=False,
                          yaml_dict_tpl=self.vnfd_dict)
        toscautils.post_process_template(tosca1)
        translator = tosca_translator.TOSCATranslator(tosca1, {})
        heat_template_yaml = translator.translate()
        expected_heat_tpl = _get_template('hot_tosca_openwrt.yaml')
        mgmt_ports = toscautils.get_mgmt_ports(self.tosca)
        heat_tpl = toscautils.post_process_heat_template(
            heat_template_yaml, mgmt_ports, {}, {}, {})

        heatdict = yaml.safe_load(heat_tpl)
        expecteddict = yaml.safe_load(expected_heat_tpl)
        self.assertEqual(expecteddict, heatdict)

    def test_findvdus(self):
        vdus = toscautils.findvdus(self.tosca)

        self.assertEqual(1, len(vdus))

        for vdu in vdus:
            self.assertEqual(True, vdu.type_definition.is_derived_from(
                toscautils.TACKERVDU))

    def test_get_flavor_dict(self):
        vnfd_dict = yaml.safe_load(self.tosca_flavor)
        toscautils.updateimports(vnfd_dict)
        tosca = tosca_template.ToscaTemplate(a_file=False,
                                             yaml_dict_tpl=vnfd_dict)
        expected_flavor_dict = {
            "VDU1": {
                "vcpus": 2,
                "disk": 10,
                "ram": 512
            }
        }
        actual_flavor_dict = toscautils.get_flavor_dict(tosca)
        self.assertEqual(expected_flavor_dict, actual_flavor_dict)

    def test_add_resources_tpl_for_flavor(self):
        dummy_heat_dict = yaml.safe_load(_get_template(
            'hot_flavor_and_capabilities.yaml'))
        expected_dict = yaml.safe_load(_get_template('hot_flavor.yaml'))
        dummy_heat_res = {
            "flavor": {
                "VDU1": {
                    "vcpus": 2,
                    "ram": 512,
                    "disk": 10
                }
            }
        }
        toscautils.add_resources_tpl(dummy_heat_dict, dummy_heat_res)
        self.assertEqual(expected_dict, dummy_heat_dict)

    def test_get_flavor_dict_extra_specs_all_numa_count(self):
        tosca_fes_all_numa_count = _get_template(
            'tosca_flavor_all_numa_count.yaml')
        vnfd_dict = yaml.safe_load(tosca_fes_all_numa_count)
        toscautils.updateimports(vnfd_dict)
        tosca = tosca_template.ToscaTemplate(a_file=False,
                                             yaml_dict_tpl=vnfd_dict)
        expected_flavor_dict = {
            "VDU1": {
                "vcpus": 8,
                "disk": 10,
                "ram": 4096,
                "extra_specs": {
                    'hw:cpu_policy': 'dedicated', 'hw:mem_page_size': 'any',
                    'hw:cpu_sockets': 2, 'hw:cpu_threads': 2,
                    'hw:numa_nodes': 2, 'hw:cpu_cores': 2,
                    'hw:cpu_threads_policy': 'avoid'
                }
            }
        }
        actual_flavor_dict = toscautils.get_flavor_dict(tosca)
        self.assertEqual(expected_flavor_dict, actual_flavor_dict)

    def test_get_flavor_dict_with_wrong_cpu(self):
        tosca_fes = _get_template(
            'tosca_flavor_with_wrong_cpu.yaml')
        vnfd_dict = yaml.safe_load(tosca_fes)
        toscautils.updateimports(vnfd_dict)
        tosca = tosca_template.ToscaTemplate(a_file=False,
                                             yaml_dict_tpl=vnfd_dict)

        self.assertRaises(vnfm.CpuAllocationInvalidValues,
                          toscautils.get_flavor_dict,
                          tosca)

    def test_tacker_conf_heat_extra_specs_all_numa_count(self):
        tosca_fes_all_numa_count = _get_template(
            'tosca_flavor_all_numa_count.yaml')
        vnfd_dict = yaml.safe_load(tosca_fes_all_numa_count)
        toscautils.updateimports(vnfd_dict)
        tosca = tosca_template.ToscaTemplate(a_file=False,
                                             yaml_dict_tpl=vnfd_dict)
        expected_flavor_dict = {
            "VDU1": {
                "vcpus": 8,
                "disk": 10,
                "ram": 4096,
                "extra_specs": {
                    'hw:cpu_policy': 'dedicated', 'hw:mem_page_size': 'any',
                    'hw:cpu_sockets': 2, 'hw:cpu_threads': 2,
                    'hw:numa_nodes': 2, 'hw:cpu_cores': 2,
                    'hw:cpu_threads_policy': 'avoid',
                    'aggregate_instance_extra_specs:nfv': 'true'
                }
            }
        }
        actual_flavor_dict = toscautils.get_flavor_dict(
            tosca, {"aggregate_instance_extra_specs:nfv": "true"})
        self.assertEqual(expected_flavor_dict, actual_flavor_dict)

    def test_add_resources_tpl_for_image(self):
        dummy_heat_dict = yaml.safe_load(_get_template(
            'hot_image_before_processed_image.yaml'))
        expected_dict = yaml.safe_load(_get_template(
            'hot_image_after_processed_image.yaml'))
        dummy_heat_res = {
            "image": {
                "VDU1": {
                    "location": "http://URL/v1/openwrt.qcow2",
                    "container_format": "bare",
                    "disk_format": "raw"
                }
            }
        }
        toscautils.add_resources_tpl(dummy_heat_dict, dummy_heat_res)
        self.assertEqual(expected_dict, dummy_heat_dict)

    def test_convert_unsupported_res_prop_kilo_ver(self):
        unsupported_res_prop_dict = {'OS::Neutron::Port': {
            'port_security_enabled': 'value_specs', }, }
        dummy_heat_dict = yaml.safe_load(_get_template(
            'hot_tosca_openwrt.yaml'))
        expected_heat_dict = yaml.safe_load(_get_template(
            'hot_tosca_openwrt_kilo.yaml'))
        toscautils.convert_unsupported_res_prop(dummy_heat_dict,
                                                unsupported_res_prop_dict)
        self.assertEqual(expected_heat_dict, dummy_heat_dict)

    def test_check_for_substitution_mappings(self):
        tosca_sb_map = _get_template('../../../../../etc/samples/test-nsd-'
                                     'vnfd1.yaml')
        param = {'substitution_mappings': {
                 'VL2': {'type': 'tosca.nodes.nfv.VL', 'properties': {
                         'network_name': 'net0', 'vendor': 'tacker'}},
                 'VL1': {'type': 'tosca.nodes.nfv.VL', 'properties': {
                         'network_name': 'net_mgmt', 'vendor': 'tacker'}},
                 'requirements': {'virtualLink2': 'VL2',
                                  'virtualLink1': 'VL1'}}}
        template = yaml.safe_load(tosca_sb_map)
        toscautils.updateimports(template)
        toscautils.check_for_substitution_mappings(template, param)
        self.assertNotIn('substitution_mappings', param)

    def test_get_block_storage_details(self):
        tosca_vol = _get_template('tosca_block_storage.yaml')
        vnfd_dict = yaml.safe_load(tosca_vol)
        expected_dict = {
            'volumes': {
                'VB1': {
                    'image': 'cirros-0.4.0-x86_64-disk',
                    'size': '1'
                }
            },
            'volume_attachments': {
                'CB1': {
                    'instance_uuid': {'get_resource': 'VDU1'},
                    'mountpoint': '/dev/vdb',
                    'volume_id': {'get_resource': 'VB1'}}
            }
        }
        volume_details = toscautils.get_block_storage_details(vnfd_dict)
        self.assertEqual(expected_dict, volume_details)
