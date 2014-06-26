# Copyright 2014 Intel Corporation.
# Copyright 2014 Isaku Yamahata <isaku.yamahata at intel com>
#                               <isaku.yamahata at gmail com>
# All Rights Reserved.
#
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
#
# @author: Isaku Yamahata, Intel Corporation.

import uuid

import mock
from oslo.config import cfg

from tacker.api.v1 import attributes
import tacker.openstack.common.rpc.proxy
from tacker.tests import base
from tacker.vm import proxy_api


class TestProxyApi(base.BaseTestCase):
    network_id = str(uuid.uuid4())
    subnet_id = str(uuid.uuid4())
    port_id = str(uuid.uuid4())
    direction = 'send'
    src_target = 'topic=src_topic,server=src_server'
    dst_target = 'topic=dst_topic,server=dst_server'

    def setUp(self):
        super(TestProxyApi, self).setUp()
        cfg.CONF.set_override('rpc_backend',
                              'tacker.openstack.common.rpc.impl_fake')
        self.context = object()
        self.api = proxy_api.ServiceVMPluginApi('fake-topic')
        self.core_plugin = mock.Mock()
        self.mock_rpc_proxy_call_p = mock.patch.object(
            tacker.openstack.common.rpc.proxy.RpcProxy, 'call')
        self.mock_rpc_proxy_call = self.mock_rpc_proxy_call_p.start()

    def test_create_namespace_agent(self):
        core_plugin = self.core_plugin
        subnet = {
            'id': self.subnet_id,
        }
        core_plugin.get_subnet.return_value = subnet
        port = {
            'id': self.port_id,
            'network_id': self.network_id,
            'fixed_ips': [
                {'subnet_id': self.subnet_id}
            ]
        }
        core_plugin.create_port.return_value = port
        self.api.create_namespace_agent(core_plugin, self.context,
                                        self.network_id)

        self.core_plugin.create_port.assert_called_once_with(
            self.context, {'port': {'name': mock.ANY,
                                    'admin_state_up': True,
                                    'network_id': self.network_id,
                                    'device_owner': 'tacker:SERVICEVM',
                                    'mac_address': mock.ANY,
                                    'device_id': mock.ANY,
                                    'fixed_ips': attributes.ATTR_NOT_SPECIFIED,
                                    }})
        self.mock_rpc_proxy_call.assert_called_once_with(
            self.context,
            {'args': {'port': {
                'id': self.port_id,
                'network_id': self.network_id,
                'fixed_ips': [{
                    'subnet_id': self.subnet_id,
                    'subnet': {'id': self.subnet_id}}]}},
             'namespace': None,
             'method': 'create_namespace_agent'})

    def test_destroy_namespace_agent(self):
        self.api.destroy_namespace_agent(self.core_plugin, self.context,
                                         self.port_id)

        self.mock_rpc_proxy_call.assert_called_once_with(
            self.context, {'args': {'port_id': self.port_id},
                           'namespace': None,
                           'method': 'destroy_namespace_agent'})
        self.core_plugin.delete_port.assert_called_once_with(self.context,
                                                             self.port_id)

    def test_creeat_rpc_proxy(self):
        self.api.create_rpc_proxy(
            self.context, self.port_id, self.src_target, self.dst_target,
            self.direction)
        self.mock_rpc_proxy_call.assert_called_once_with(
            self.context, {'args': {'port_id': self.port_id,
                                    'src_target': self.src_target,
                                    'dst_unix_target': self.dst_target,
                                    'direction': self.direction},
                           'namespace': None,
                           'method': 'create_rpc_proxy'})

    def test_destroy_rpc_proxy(self):
        proxy_id = str(uuid.uuid4())
        rpc_proxy_id = str(uuid.uuid4())
        self.api.destroy_rpc_proxy(self.context, proxy_id, rpc_proxy_id)
        self.mock_rpc_proxy_call.assert_called_once_with(
            self.context, {'args': {'proxy_id': proxy_id,
                                    'rpc_proxy_id': rpc_proxy_id},
                           'namespace': None,
                           'method': 'destroy_rpc_proxy'})

    def test_create_rpc_namespace_proxy(self):
        dst_transport_url = 'fake:///'
        direction = 'send'
        self.api.create_rpc_namespace_proxy(
            self.context, self.port_id, self.src_target,
            dst_transport_url, self.dst_target, direction)
        self.mock_rpc_proxy_call.assert_called_once_with(
            self.context, {'args': {'dst_transport_url': dst_transport_url,
                                    'direction': direction,
                                    'port_id': self.port_id,
                                    'src_target': self.src_target,
                                    'dst_target': self.dst_target},
                           'namespace': None,
                           'method': 'create_rpc_namespace_proxy'})

    def test_destroy_rpc_namespace_proxy(self):
        ns_proxy_id = str(uuid.uuid4())
        self.api.destroy_rpc_namespace_proxy(self.context, self.port_id,
                                             ns_proxy_id)
        self.mock_rpc_proxy_call.assert_called_once_with(
            self.context, {'args': {'port_id': self.port_id,
                                    'namespace_proxy_id': ns_proxy_id},
                           'namespace': None,
                           'method': 'destroy_rpc_namespace_proxy'})
