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

import mock
from oslo.config import cfg

from tacker import context
from tacker.tests import base
from tacker.vm.agent import namespace_proxy
from tacker.vm.agent import target


class TestNamespaceAgent(base.BaseTestCase):
    def setUp(self):
        super(TestNamespaceAgent, self).setUp()
        self.addCleanup(mock.patch.stopall)
        self.mock_get_transport_p = mock.patch('oslo.messaging.get_transport')
        self.mock_get_transport = self.mock_get_transport_p.start()
        self.mock_transport = self.mock_get_transport.return_value

        def server_stop():
            pass
        self.agent = namespace_proxy.ServiceVMNamespaceAgent(
            'host', conf=cfg.CONF, src_transport=self.mock_transport,
            server_stop=server_stop)

    def test_start_stop_wait(self):
        self.agent.init_host()
        self.agent.after_start()
        self.agent.stop()
        self.agent.wait()

    def test_desstroy_namespace_agent(self):
        self.agent.init_host()
        self.agent.after_start()
        ctxt = context.Context('user', 'tenant')
        self.agent.destroy_namespace_agent(ctxt)
        self.agent.wait()

    def test_create_destroy_rpc_namespace_proxy_send(self):
        self.agent.init_host()
        self.agent.after_start()
        ctxt = context.Context('user', 'tenant')
        with mock.patch('oslo.messaging.proxy.get_proxy_server'
                        ) as mock_get_proxy_server:
            mock_proxy_server = mock_get_proxy_server.return_value
            src_unix_target = 'topic=src_topic,server=src_server'
            dst_transport_url = 'fake:///'
            dst_target = 'topic=dst_topic,server=dst_server'
            ns_proxy_id = self.agent.create_rpc_namespace_proxy(
                ctxt, src_unix_target, dst_transport_url, dst_target, 'send')
            src_unix_target = target.target_parse(src_unix_target)
            dst_target = target.target_parse(dst_target)
            mock_get_proxy_server.assert_called_once_with(
                self.mock_transport, src_unix_target, None,
                self.mock_transport, dst_target, None, executor=mock.ANY)
            # mock_proxy_server.start.assert_called_once_with()

            self.agent.destroy_rpc_namespace_proxy(ctxt, ns_proxy_id)
            mock_proxy_server.stop.assert_called_once_with()
            mock_proxy_server.wait.assert_called_once_with()
            self.mock_transport.cleanup.assert_called_once_with()
        self.agent.stop()
        self.agent.wait()

    def test_create_destroy_rpc_namespace_proxy_receive(self):
        self.agent.init_host()
        self.agent.after_start()
        ctxt = context.Context('user', 'tenant')
        with mock.patch('oslo.messaging.proxy.get_proxy_server'
                        ) as mock_get_proxy_server:
            mock_proxy_server = mock_get_proxy_server.return_value
            src_unix_target = 'topic=src_topic,server=src_server'
            dst_transport_url = 'fake:///'
            dst_target = 'topic=dst_topic,server=dst_server'
            ns_proxy_id = self.agent.create_rpc_namespace_proxy(
                ctxt, src_unix_target, dst_transport_url, dst_target,
                'receive')
            src_unix_target = target.target_parse(src_unix_target)
            dst_target = target.target_parse(dst_target)
            mock_get_proxy_server.assert_called_once_with(
                self.mock_transport, dst_target, None,
                self.mock_transport, src_unix_target, None, executor=mock.ANY)
            # mock_proxy_server.start.assert_called_once_with()

            self.agent.destroy_rpc_namespace_proxy(ctxt, ns_proxy_id)
            mock_proxy_server.stop.assert_called_once_with()
            mock_proxy_server.wait.assert_called_once_with()
            self.mock_transport.cleanup.assert_called_once_with()
        self.agent.stop()
        self.agent.wait()

    def test_create_destroy_rpc_namespace_proxy(self):
        self.agent.init_host()
        self.agent.after_start()
        ctxt = context.Context('user', 'tenant')
        with mock.patch('oslo.messaging.proxy.get_proxy_server'
                        ) as mock_get_proxy_server:
            mock_proxy_server = mock_get_proxy_server.return_value
            src_unix_target_send = ('topic=src_topic_send,'
                                    'server=src_server_send')
            dst_transport_url_send = 'fake:///'
            dst_target_send = 'topic=dst_topic_send,server=dst_server_send'
            ns_proxy_id_send = self.agent.create_rpc_namespace_proxy(
                ctxt, src_unix_target_send, dst_transport_url_send,
                dst_target_send, 'send')
            src_unix_target_send = target.target_parse(src_unix_target_send)
            dst_target_send = target.target_parse(dst_target_send)
            mock_get_proxy_server.assert_called_once_with(
                self.mock_transport, src_unix_target_send, None,
                self.mock_transport, dst_target_send, None, executor=mock.ANY)
            # mock_proxy_server.start.assert_called_once_with()

            src_unix_target_recv = ('topic=src_topic_recv,'
                                    'server=src_server_recv')
            dst_transport_url_recv = 'fake:///'
            dst_target_recv = 'topic=dst_topic_recv,server=dst_server_recv'
            self.agent.create_rpc_namespace_proxy(
                ctxt, src_unix_target_recv, dst_transport_url_recv,
                dst_target_recv, 'receive')
            src_unix_target_recv = target.target_parse(src_unix_target_recv)
            dst_target_recv = target.target_parse(dst_target_recv)

            # mock.call().__hash__()/mock.call.__hash__() doesn't work
            # due to __getattr__. So create it manually
            call_hash = mock._Call(name='().__hash__')
            mock_get_proxy_server.assert_has_calls([
                mock.call(self.mock_transport, src_unix_target_send, None,
                          self.mock_transport, dst_target_send, None,
                          executor=mock.ANY),
                # mock.call().start(),
                call_hash(),
                mock.call(self.mock_transport, dst_target_recv, None,
                          self.mock_transport, src_unix_target_recv, None,
                          executor=mock.ANY),
                # mock.call().start(),
                call_hash()])

            self.agent.destroy_rpc_namespace_proxy(ctxt, ns_proxy_id_send)
            mock_proxy_server.stop.assert_called_once_with()
            mock_proxy_server.wait.assert_called_once_with()

            self.agent.destroy_namespace_agent(ctxt)
            self.agent.wait()
            call_hash = mock._Call(name='__hash__')
            mock_proxy_server.assert_has_calls([
                # mock.call.start(),
                call_hash(),
                # mock.call.start(),
                call_hash(),
                call_hash(),
                mock.call.stop(),
                mock.call.wait(),
                mock.call.stop(),
                mock.call.wait()])
            self.mock_transport.cleanup.assert_called_once_with()
