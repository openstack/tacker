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
import oslo.messaging.rpc.client
from oslo.messaging import target
from oslo.messaging import transport

import tacker.agent.linux.ip_lib
from tacker import context
from tacker.tests import base
from tacker.vm.agent import agent


class TestVMService(base.BaseTestCase):
    ctxt = context.Context('user', 'tenant')
    network_id = str(uuid.uuid4())
    subnet_id = str(uuid.uuid4())
    port_id = str(uuid.uuid4())
    mac_address = '00:00:00:00:00:01'
    netmask = '/24'
    network_address = '192.168.1.0'
    cidr = network_address + netmask
    ip_address = '192.168.1.3'
    gw_address = '192.168.1.1'
    port = {
        'id': port_id,
        'network_id': network_id,
        'mac_address': mac_address,
        'fixed_ips': [{'subnet_id': subnet_id,
                       'ip_address': ip_address,
                       'subnet': {
                           'cidr': cidr,
                           'ip_version': 4,
                           'gateway_ip': gw_address}}]
    }

    def setUp(self):
        super(TestVMService, self).setUp()
        conf = cfg.CONF

        # NOTE(yamahata): work around. rpc driver-dependent config variables
        # remove this line once tacker are fully ported to oslo.messaging
        from tacker.openstack.common import rpc
        conf.unregister_opts(rpc.rpc_opts)

        conf.register_opts(transport._transport_opts)
        conf.set_override('rpc_backend',
                          'tacker.openstack.common.rpc.impl_fake')
        self.addCleanup(mock.patch.stopall)
        self.mock_get_transport_p = mock.patch('oslo.messaging.get_transport')
        self.mock_get_transport = self.mock_get_transport_p.start()
        self.mock_import_object_p = mock.patch(
            'tacker.openstack.common.importutils.import_object')
        self.mock_import_object = self.mock_import_object_p.start()
        self.vif_driver = mock.create_autospec(
            tacker.agent.linux.interface.NullDriver)
        self.mock_import_object.return_value = self.vif_driver

        self.agent = agent.ServiceVMAgent('host', conf=conf)

        self.mock_process_manager_p = mock.patch.object(
            tacker.agent.linux.external_process, 'ProcessManager')
        self.mock_process_manager = self.mock_process_manager_p.start()
        self.mock_process_manager_instance = (
            self.mock_process_manager.return_value)
        self.mock_device_exists_p = mock.patch(
            'tacker.agent.linux.ip_lib.device_exists')
        self.mock_device_exists = self.mock_device_exists_p.start()
        self.mock_device_exists.return_value = False
        self.mock_ipwrapper_p = mock.patch.object(tacker.agent.linux.ip_lib,
                                                  'IPWrapper')
        self.mock_ipwrapper = self.mock_ipwrapper_p.start()
        self.mock_ipwrapper_instance = self.mock_ipwrapper.return_value
        self.mock_rpc_client_p = mock.patch.object(oslo.messaging.rpc,
                                                   'RPCClient')
        self.mock_rpc_client = self.mock_rpc_client_p.start()
        self.mock_rpc_client_instance = self.mock_rpc_client.return_value

    def test_create_destroy_namespace_agent(self):
        self.agent.create_namespace_agent(self.ctxt, self.port)
        self.vif_driver.plug.assert_called_once_with(
            self.network_id, self.port_id, mock.ANY, self.mac_address,
            namespace=mock.ANY)
        self.vif_driver.init_l3.assert_called_once_with(
            mock.ANY, [self.ip_address + self.netmask], namespace=mock.ANY)
        self.mock_ipwrapper.assert_called_once_with(
            mock.ANY, namespace=mock.ANY)
        self.mock_ipwrapper_instance.netns.execute.assert_called_once_with(
            ['route', 'add', 'default', 'gw', self.gw_address],
            check_exit_code=False)
        self.assertTrue(self.mock_process_manager_instance.enable.called)

        self.agent.destroy_namespace_agent(self.ctxt, self.port_id)
        self.vif_driver.unplug.assert_called_once_with(mock.ANY,
                                                       namespace=mock.ANY)
        self.mock_process_manager_instance.disable.assert_called_once_with()

    def test_create_rpc_proxy_wrong_port_id(self):
        func = lambda: self.agent.create_rpc_proxy(
            self.ctxt, self.port_id, 'topic=src_topic,server=src_server',
            'topic=dst_topic,server=dst_server', 'wrong-direction')
        self.assertRaises(RuntimeError, func)

    def test_create_rpc_proxy_wrong_direction(self):
        self.agent.create_namespace_agent(self.ctxt, self.port)
        func = lambda: self.agent.create_rpc_proxy(
            self.ctxt, self.port_id, 'topic=src_topic,server=src_server',
            'topic=dst_topic,server=dst_server', 'wrong-direction')
        self.assertRaises(RuntimeError, func)
        self.agent.destroy_namespace_agent(self.ctxt, self.port_id)

    def test_create_destroy_rpc_proxy_send(self):
        self.agent.create_namespace_agent(self.ctxt, self.port)

        with mock.patch('oslo.messaging.proxy.get_proxy_server'
                        ) as mock_get_proxy_server:
            mock_transport = self.mock_get_transport.return_value
            mock_instance = mock_get_proxy_server.return_value

            proxy_id = self.agent.create_rpc_proxy(
                self.ctxt, self.port_id, 'topic=src_topic,server=src_server',
                'topic=dst_topic,server=dst_server', 'send')
            src_target = target.Target(topic='src_topic', server='src_server')
            dst_target = target.Target(topic='dst_topic', server='dst_server')
            mock_get_proxy_server.assert_called_once_with(
                mock_transport, src_target, None,
                mock_transport, dst_target, None, executor=mock.ANY)
            mock_instance.start.assert_called_once_with()

            self.agent.destroy_rpc_proxy(self.ctxt, self.port_id, proxy_id)
            mock_instance.stop.assert_called_once_with()
            mock_instance.wait.assert_called_once_with()

        self.agent.destroy_namespace_agent(self.ctxt, self.port_id)

    def test_create_destroy_rpc_proxy_receive(self):
        self.agent.create_namespace_agent(self.ctxt, self.port)

        with mock.patch('oslo.messaging.proxy.get_proxy_server'
                        ) as mock_get_proxy_server:
            mock_transport = self.mock_get_transport.return_value
            mock_instance = mock_get_proxy_server.return_value

            proxy_id = self.agent.create_rpc_proxy(
                self.ctxt, self.port_id, 'topic=src_topic,server=src_server',
                'topic=dst_topic,server=dst_server', 'receive')
            src_target = target.Target(topic='src_topic', server='src_server')
            dst_target = target.Target(topic='dst_topic', server='dst_server')
            mock_get_proxy_server.assert_called_once_with(
                mock_transport, dst_target, None,
                mock_transport, src_target, None, executor=mock.ANY)
            mock_instance.start.assert_called_once_with()

            self.agent.destroy_rpc_proxy(self.ctxt, self.port_id, proxy_id)
            mock_instance.stop.assert_called_once_with()
            mock_instance.wait.assert_called_once_with()

        self.agent.destroy_namespace_agent(self.ctxt, self.port_id)

    def test_create_destroy_rpc_proxy(self):
        self.mock_device_exists.return_value = False
        self.agent.create_namespace_agent(self.ctxt, self.port)

        with mock.patch('oslo.messaging.proxy.get_proxy_server'
                        ) as mock_get_proxy_server:
            mock_transport = self.mock_get_transport.return_value

            proxy_id_send = self.agent.create_rpc_proxy(
                self.ctxt, self.port_id,
                'topic=src_topic_send,server=src_server_send',
                'topic=dst_topic_send,server=dst_server_send', 'send')
            src_target_send = target.Target(topic='src_topic_send',
                                            server='src_server_send')
            dst_target_send = target.Target(topic='dst_topic_send',
                                            server='dst_server_send')
            self.agent.create_rpc_proxy(
                self.ctxt, self.port_id,
                'topic=src_topic_receive,server=src_server_receive',
                'topic=dst_topic_receive,server=dst_server_receive', 'receive')
            src_target_recv = target.Target(topic='src_topic_receive',
                                            server='src_server_receive')
            dst_target_recv = target.Target(topic='dst_topic_receive',
                                            server='dst_server_receive')

            self.agent.destroy_rpc_proxy(self.ctxt,
                                         self.port_id, proxy_id_send)
            self.agent.destroy_namespace_agent(self.ctxt, self.port_id)

            mock_get_proxy_server.assert_has_calls([
                mock.call(mock_transport, src_target_send, None,
                          mock_transport, dst_target_send, None,
                          executor=mock.ANY),
                mock.call().start(),
                mock.call(mock_transport, dst_target_recv, None,
                          mock_transport, src_target_recv, None,
                          executor=mock.ANY),
                mock.call().start(),
                mock.call().stop(), mock.call().wait(),
                mock.call().stop(), mock.call().wait()])

    def _test_create_destroy_rpc_namespace_proxy_direction(self, direction):
        self.agent.create_namespace_agent(self.ctxt, self.port)

        src_target = 'topic=src_topic,server=src_server'
        dst_transport_url = 'rabbit://guest:guest@host:5672'
        dst_target = 'topic=dst_topic,server=dst_server'
        ns_proxy_id = self.agent.create_rpc_namespace_proxy(
            self.ctxt, self.port_id, src_target,
            dst_transport_url, dst_target, direction)
        kwargs = {
            'src_target': src_target,
            'dst_transport_url': dst_transport_url,
            'dst_target': dst_target,
            'direction': direction,
        }
        self.mock_rpc_client_instance.call.assert_called_once_with(
            {}, 'create_rpc_namespace_proxy', **kwargs)

        self.agent.destroy_rpc_namespace_proxy(self.ctxt,
                                               self.port_id, ns_proxy_id)

        self.mock_rpc_client_instance.call.assert_has_calls([
            mock.call({}, 'create_rpc_namespace_proxy', **kwargs),
            mock.call({}, 'destroy_rpc_namespace_proxy',
                      namespace_proxy_id=ns_proxy_id)])

        self.agent.destroy_namespace_agent(self.ctxt, self.port_id)

    def test_create_destroy_rpc_namespace_proxy_send(self):
        self._test_create_destroy_rpc_namespace_proxy_direction('send')

    def test_create_destroy_rpc_namespace_proxy_receive(self):
        self._test_create_destroy_rpc_namespace_proxy_direction('receive')

    def test_create_destroy_rpc_namespace_proxy(self):
        self.agent.create_namespace_agent(self.ctxt, self.port)

        src_target_send = 'topic=src_topic_send,server=src_server_send'
        dst_transport_url_send = 'rabbit://guestsend:guestsend@sendhost:5672'
        dst_target_send = 'topic=dst_topic_send,server=dst_server_send'
        direction_send = 'send'
        ns_proxy_id_send = self.agent.create_rpc_namespace_proxy(
            self.ctxt, self.port_id, src_target_send,
            dst_transport_url_send, dst_target_send, direction_send)
        kwargs_send = {
            'src_target': src_target_send,
            'dst_transport_url': dst_transport_url_send,
            'dst_target': dst_target_send,
            'direction': direction_send,
        }

        src_target_recv = 'topic=src_topic_recv,server=src_server_recv'
        dst_transport_url_recv = 'rabbit://guestrecv:guestrecv@recvhost:5672'
        dst_target_recv = 'topic=dst_topic_recv,server=dst_server_recv'
        direction_recv = 'receive'
        self.agent.create_rpc_namespace_proxy(
            self.ctxt, self.port_id, src_target_recv,
            dst_transport_url_recv, dst_target_recv, direction_recv)
        kwargs_recv = {
            'src_target': src_target_recv,
            'dst_transport_url': dst_transport_url_recv,
            'dst_target': dst_target_recv,
            'direction': direction_recv,
        }

        self.agent.destroy_rpc_namespace_proxy(self.ctxt,
                                               self.port_id, ns_proxy_id_send)
        self.agent.destroy_namespace_agent(self.ctxt, self.port_id)

        self.mock_rpc_client_instance.call.assert_has_calls([
            mock.call({}, 'create_rpc_namespace_proxy', **kwargs_send),
            mock.call({}, 'create_rpc_namespace_proxy', **kwargs_recv),
            mock.call({}, 'destroy_rpc_namespace_proxy',
                      namespace_proxy_id=ns_proxy_id_send),
            mock.call({}, 'destroy_namespace_agent')])
