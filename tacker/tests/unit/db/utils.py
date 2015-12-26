# Copyright 2015 Brocade Communications System, Inc.
# All Rights Reserved.
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


def get_dummy_vnfd_obj():
    return {u'vnfd': {u'service_types': [{u'service_type': u'vnfd'}],
                      'name': 'dummy_vnfd', 'tenant_id':
        u'ad7ebc56538745a08ef7c5e97f8bd437', u'mgmt_driver': u'noop',
                      u'infra_driver': u'fake_driver', u'attributes': {u'vnfd':
                                          u'template_name: OpenWRT'
                                          u' \r\ndescription: OpenWRT router'
                                          u'\r\n\r\nservice_properties:\r\n'
                                          u'  Id: sample-vnfd\r\n  vendor:'
                                          u' tacker\r\n  version: '
                                          u'1\r\n\r\nvdus:'
                                          u'\r\n  vdu1:\r\n    id: vdu1\r\n'
                                          u'    vm_image:'
                                          u' cirros-0.3.2-x86_64-uec\r\n'
                                          u'    instance_type: m1.tiny\r\n\r\n'
                                          u'    network_interfaces:\r\n'
                                          u'      management:\r\n'
                                          u'        network: net_mgmt\r\n'
                                          u'        management: true\r\n'
                                          u'      pkt_in:\r\n        network:'
                                          u' net0\r\n      pkt_out:\r\n'
                                          u'        network: net1\r\n\r\n'
                                          u'    placement_policy:\r\n'
                                          u'      availability_zone: nova\r\n'
                                          u'\r'
                                          u'\n    auto-scaling: noop\r\n'
                                          u'    monitoring_policy: noop\r\n'
                                          u'    failure_policy: noop\r\n\r\n'
                                          u'    config:\r\n      param0: key0'
                                          u'\r\n      param1: key1'},
                      'description': 'dummy_vnfd_description'},
            u'auth': {u'tenantName': u'admin', u'passwordCredentials': {
                u'username': u'admin', u'password': u'devstack'}}}


def get_dummy_vnf_obj():
    return {'vnf': {'description': 'dummy_vnf_description',
                    'vnfd_id': u'eb094833-995e-49f0-a047-dfb56aaf7c4e',
                    'tenant_id': u'ad7ebc56538745a08ef7c5e97f8bd437',
                    'name': 'dummy_vnf',
                    'attributes': {}}}


def get_dummy_vnf_config_obj():
    return {'vnf': {u'attributes': {u'config': {'vdus': {'vdu1': {
        'config': {'firewall': 'dummy_firewall_values'}}}}}}}


def get_dummy_device_obj():
    return {'status': 'PENDING_CREATE', 'instance_id': None, 'name':
        u'test_openwrt', 'tenant_id': u'ad7ebc56538745a08ef7c5e97f8bd437',
            'template_id': u'eb094833-995e-49f0-a047-dfb56aaf7c4e',
            'device_template': {'service_types': [{'service_type': u'vnfd',
            'id': u'4a4c2d44-8a52-4895-9a75-9d1c76c3e738'}], 'description':
        u'OpenWRT with services', 'tenant_id':
        u'ad7ebc56538745a08ef7c5e97f8bd437', 'mgmt_driver': u'openwrt',
        'infra_driver': u'heat', 'attributes': {u'vnfd': u'template_name: '
        u'OpenWRT\r\ndescription: OpenWRT with services\r\n\r\nvdus:\r\n  '
        u'vdu1:\r\n    id: vdu1\r\n    vm_image: cirros-0.3.2-x86_64-uec\r\n  '
        u'  instance_type: m1.tiny\r\n    service_type: firewall\r\n    '
        u'mgmt_driver: openwrt\r\n\r\n    network_interfaces:\r\n      '
        u'management:\r\n        network: net_mgmt\r\n        management: True'
        u'\r\n      pkt_in:\r\n        network: net0\r\n      pkt_out:\r\n    '
        u'    network: net1\r\n\r\n    placement_policy:\r\n      '
        u'availability_zone: nova\r\n\r\n    auto-scaling: noop\r\n\r\n    '
        u'monitoring_policy: noop\r\n    failure_policy: noop\r\n\r\n    '
        u'monitoring_parameter:\r\n      a:\r\n\r\n    config:\r\n      '
        u'param0: key0\r\n      param1: key1\r\n\r\n'}, 'id':
            u'fb048660-dc1b-4f0f-bd89-b023666650ec', 'name':
            u'openwrt_services'}, 'mgmt_url': None, 'service_context': [],
            'attributes': {u'param_values': u''}, 'id':
                'eb84260e-5ff7-4332-b032-50a14d6c1123', 'description':
                u'OpenWRT with services'}


def get_dummy_device_obj_config_attr():
    return {'status': 'PENDING_CREATE', 'instance_id': None, 'name':
        u'test_openwrt', 'tenant_id': u'ad7ebc56538745a08ef7c5e97f8bd437',
            'template_id': u'eb094833-995e-49f0-a047-dfb56aaf7c4e',
            'device_template': {'service_types': [{'service_type': u'vnfd',
            'id': u'4a4c2d44-8a52-4895-9a75-9d1c76c3e738'}], 'description':
                u'OpenWRT with services', 'tenant_id':
                u'ad7ebc56538745a08ef7c5e97f8bd437', 'mgmt_driver': u'openwrt',
        'infra_driver': u'heat', 'attributes': {u'vnfd': u'template_name: '
        u'OpenWRT\r\ndescription: OpenWRT with services\r\n\r\nvdus:\r\n  '
        u'vdu1:\r\n    id: vdu1\r\n    vm_image: cirros-0.3.2-x86_64-uec\r\n  '
        u'  instance_type: m1.tiny\r\n    service_type: firewall\r\n    '
        u'mgmt_driver: openwrt\r\n\r\n    network_interfaces:\r\n      '
        u'management:\r\n        network: net_mgmt\r\n        management: True'
        u'\r\n      pkt_in:\r\n        network: net0\r\n      pkt_out:\r\n    '
        u'    network: net1\r\n\r\n    placement_policy:\r\n      '
        u'availability_zone: nova\r\n\r\n    auto-scaling: noop\r\n\r\n    '
        u'monitoring_policy: noop\r\n    failure_policy: noop\r\n\r\n    '
        u'monitoring_parameter:\r\n      a:\r\n\r\n    config:\r\n      '
        u'param0: key0\r\n      param1: key1\r\n\r\n'}, 'id':
            u'fb048660-dc1b-4f0f-bd89-b023666650ec', 'name':
            u'openwrt_services'}, 'mgmt_url': None, 'service_context': [],
            'attributes': {u'config': u"vdus:\n  vdu1:\n    config:\n      "
                                      u"firewall: |\n        package firewall"
                                      u"\n\n        config defaults\n         "
                                      u"       option syn_flood '1'\n         "
                                      u"       option input 'ACCEPT'\n        "
                                      u"        option output 'ACCEPT'\n      "
                                      u"          option forward "
                                      u"'REJECT'\n"}, 'id':
                'eb84260e-5ff7-4332-b032-50a14d6c1123',
            'description': u'OpenWRT with services'}


def get_dummy_device_update_config_attr():
    return {'device': {u'attributes': {u'config': u"vdus:\n  vdu1:\n    "
                                                  u"config:\n      firewall: |"
                                                  u"\n        package firewall"
                                                  u"\n\n        config default"
                                                  u"s\n                "
                                                  u"option syn_flood '10'\n   "
                                                  u"             option input "
                                                  u"'REJECT'\n                "
                                                  u"option output 'REJECT'\n  "
                                                  u"              option "
                                                  u"forward 'REJECT'\n"}}}


def get_dummy_device_obj_ipaddr_attr():
    return {'status': 'PENDING_CREATE', 'device_template': {'service_types':
            [{'service_type': u'vnfd', 'id':
                u'16f8b3f7-a9ff-4338-bbe5-eee48692c468'}, {'service_type':
                u'router', 'id': u'58878cb7-689f-47a5-9c2d-654e49e2357f'},
             {'service_type': u'firewall', 'id':
                 u'd016144f-42a6-44f4-93f6-52d201998916'}], 'description':
        u'Parameterized VNF descriptor for IP addresses', 'tenant_id':
        u'4dd6c1d7b6c94af980ca886495bcfed0', 'mgmt_driver': u'noop',
        'infra_driver': u'heat', 'attributes': {u'vnfd': u'template_name: '
        u'cirros_ipaddr_template\ndescription: Parameterized VNF descriptor '
        u'for IP addresses\nservice_properties:\n  Id: cirros\n  vendor: '
        u'ACME\n  version: 1\n  type:\n    - router\n    - firewall\n\nvdus:\n'
        u'  vdu1:\n    id: vdu1\n    vm_image: { get_input: vm_image }\n    '
        u'instance_type: {get_input: flavor }\n    service_type: {get_input: '
        u'service}\n    mgmt_driver: noop\n\n    network_interfaces:\n      '
        u'management:\n        network: { get_input: network }\n        '
        u'management: { get_input: management }\n        addresses: '
        u'{ get_input: mgmt_ip}\n      pkt_in:\n        network: { get_input: '
        u'pkt_in_network }\n        addresses: { get_input: pkt_in_ip}\n      '
        u'pkt_out:\n        network: { get_input: pkt_out_network }\n        '
        u'addresses: { get_input: pkt_out_ip}\n\n    placement_policy:\n      '
        u'availability_zone: { get_input: zone }\n\n    auto-scaling: noop\n\n'
        u'    monitoring_policy: noop\n    failure_policy: noop\n\n    config:'
        u'\n      param0: key0\n      param1: key1\n'}, 'id':
        u'24c31ea1-2e28-4de2-a6cb-8d389a502c75', 'name': u'ip_vnfd'}, 'name':
        u'test_ip', 'tenant_id': u'8273659b56fc46b68bd05856d1f08d14', 'id':
        'd1337add-d5a1-4fd4-9447-bb9243c8460b', 'instance_id': None,
            'mgmt_url': None, 'service_context': [], 'services': [],
            'attributes': {u'param_values': u'vdus:\n  vdu1:\n    param:\n    '
            u'  vm_image: cirros-0.3.4-x86_64-uec\n      flavor: m1.tiny\n    '
            u'  service: firewall\n      pkt_in_network: net0\n      '
            u'pkt_out_network: net1\n      zone: nova\n      management: True'
            u'\n      network: net_mgmt\n      mgmt_ip:\n        - '
            u'192.168.120.98\n      pkt_in_ip:\n        - 10.10.0.98\n      '
            u'pkt_out_ip:\n        - 10.10.1.98\n'}, 'template_id':
                u'24c31ea1-2e28-4de2-a6cb-8d389a502c75', 'description':
                u'Parameterized VNF descriptor for IP addresses'}


def get_dummy_device_obj_userdata_attr():
    return {'status': 'PENDING_CREATE', 'instance_id': None, 'name':
        u'test_userdata', 'tenant_id': u'8273659b56fc46b68bd05856d1f08d14',
            'template_id': u'206e343f-c580-4494-a739-525849edab7f',
            'device_template': {'service_types': [{'service_type': u'firewall',
            'id': u'1fcc2d7c-a6b6-4263-8cac-9590f059a555'}, {'service_type':
            u'router', 'id': u'8c99106d-826f-46eb-91a1-08dfdc78c04b'},
            {'service_type': u'vnfd', 'id':
                u'9bf289ec-c0e1-41fc-91d7-110735a70221'}], 'description':
                u"Parameterized VNF descriptor", 'tenant_id':
                u'8273659b56fc46b68bd05856d1f08d14', 'mgmt_driver': u'noop',
                'infra_driver': u'heat', 'attributes': {u'vnfd':
                          u"template_name: cirros_user_data\ndescription: "
                          u"Parameterized VNF descriptor\nservice_properties:"
                          u"\n  Id: cirros\n  vendor: ACME\n  version: 1\n  "
                          u"type:\n    - router\n    - firewall\n\nvdus:\n  "
                          u"vdu1:\n    id: vdu1\n    vm_image: { get_input: "
                          u"vm_image }\n    instance_type: {get_input: flavor "
                          u"}\n    service_type: {get_input: service}\n    "
                          u"mgmt_driver: noop\n    user_data: {get_input: "
                          u"user_data}\n    user_data_format: {get_input: "
                          u"user_data_format}\n\n    network_interfaces:\n    "
                          u"  management:\n        network: { get_input: "
                          u"network }\n        management: { get_input: "
                          u"management }\n      pkt_in:\n        network: "
                          u"{ get_input: pkt_in_network }\n      pkt_out:\n   "
                          u"     network: { get_input: pkt_out_network }\n\n  "
                          u"  placement_policy:\n      availability_zone: { "
                          u"get_input: zone }\n\n    auto-scaling: noop\n\n   "
                          u" monitoring_policy: noop\n    failure_policy: noop"
                          u"\n\n    config:\n      param0: key0\n      param1:"
                          u" key1\n"}, 'id':
                u'206e343f-c580-4494-a739-525849edab7f', 'name':
                u'cirros_user_data'}, 'mgmt_url': None, 'service_context': [],
            'services': [], 'attributes': {u'param_values': u'vdus:\n  vdu1:\n'
            u'    param:\n      vm_image: cirros-0.3.4-x86_64-uec\n      '
            u'flavor: m1.tiny\n      service: firewall\n      pkt_in_network: '
            u'net0\n      pkt_out_network: net1\n      zone: nova\n      '
            u'management: True\n      network: net_mgmt\n      '
            u'user_data_format: RAW\n      user_data: |\n        #!/bin/sh\n  '
            u'      echo "my hostname is `hostname`" > /tmp/hostname\n        '
            u'df -h > /home/cirros/diskinfo\n'}, 'id':
                '18685f68-2b2a-4185-8566-74f54e548811', 'description':
                u"Parameterized VNF descriptor"}
