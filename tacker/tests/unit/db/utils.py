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
    return {'vnf': {'description': 'dummy_vnf_description', 'tenant_id':
        u'ad7ebc56538745a08ef7c5e97f8bd437', 'name': 'dummy_vnf',
                    'service_contexts': [], 'attributes': {}}}


def get_dummy_vnf_config_obj():
    return {'vnf': {u'attributes': {u'config': {'vdus': {'vdu1': {
        'config': {'firewall': 'dummy_firewall_values'}}}}}}}
