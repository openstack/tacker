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

from tacker.common import topics
from tacker import context
from tacker.db.vm import proxy_db  # noqa
from tacker.tests.unit.services.vm.mgmt_drivers import test_rpc
from tacker.vm.mgmt_drivers.rpc import proxy
from tacker.vm import proxy_api


_uuid = lambda: str(uuid.uuid4())


class TestMgmtProxyDriver(test_rpc.TestMgmtRpcDriver):
    _TENANT_ID = _uuid()
    _CONTEXT = context.Context('', _TENANT_ID)

    _NETWORK_ID = _uuid(),
    _SUBNET_ID = _uuid()
    _DEVICE_PORT_ID = _uuid()
    _DEVICE = {
        'id': _uuid(),
        'mgmt_address': 'device-address',
        'service_context': [{
            'network_id': _NETWORK_ID,
            'port_id': _DEVICE_PORT_ID,
            'role': 'mgmt',
        }],
    }

    _PORT_ID = _uuid()
    _IP_ADDRESS = '1.1.1.1'
    _PORT = {
        'id': _PORT_ID,
        'fixed_ips': [{
            'subnet_id': _SUBNET_ID,
            'ip_address': _IP_ADDRESS,
        }],
    }

    _PROXY_ID = [_uuid(), _uuid(), _uuid(), _uuid()]
    _NS_PROXY_ID = [_uuid(), _uuid(), _uuid(), _uuid()]

    def setUp(self):
        super(TestMgmtProxyDriver, self).setUp()

        self.mock_proxy_api_p = mock.patch(
            'tacker.vm.proxy_api.ServiceVMPluginApi')
        self.mock_proxy_api = self.mock_proxy_api_p.start()
        mock_proxy_api_instance = mock.Mock()
        self.mock_proxy_api.return_value = mock_proxy_api_instance
        self.mock_proxy_api_instance = mock_proxy_api_instance
        mock_proxy_api_instance.create_namespace_agent.return_value = (
            self._PORT_ID)
        mock_proxy_api_instance.create_rpc_proxy = mock.Mock(
            side_effect=self._PROXY_ID)
        mock_proxy_api_instance.create_rpc_namespace_proxy = mock.Mock(
            side_effect=self._NS_PROXY_ID)

        self.plugin.proxy_api = proxy_api.ServiceVMPluginApi('fake-topic')
        self.plugin._core_plugin.get_port.return_value = self._PORT
        self.mgmt_driver = proxy.AgentRpcProxyMGMTDriver()

    def test_mgmt_create_post_delete_post(self):
        mgmt_driver = self.mgmt_driver
        mock_instance = self.mock_proxy_api_instance

        mgmt_driver.mgmt_create_post(self.plugin, self._CONTEXT, self._DEVICE)
        mock_instance.create_namespace_agent.assert_called_once_with(
            self.plugin._core_plugin, self._CONTEXT, self._NETWORK_ID)
        target = 'topic=%s,server=%s' % (topics.SERVICEVM_AGENT,
                                         self._DEVICE['id'])
        mock_instance.create_rpc_proxy.assert_has_calls([
            mock.call(self._CONTEXT, self._PORT_ID, target, target, 'receive'),
            mock.call(self._CONTEXT, self._PORT_ID, target, target, 'send')])
        dst_transport_url = cfg.CONF.dst_transport_url % {'host':
                                                          self._IP_ADDRESS}
        mock_instance.create_rpc_namespace_proxy.assert_has_calls([
            mock.call(self._CONTEXT, self._PORT_ID, target, dst_transport_url,
                      target, 'receive'),
            mock.call(self._CONTEXT, self._PORT_ID, target, dst_transport_url,
                      target, 'send')])

        mgmt_address = mgmt_driver.mgmt_address(self.plugin, self._CONTEXT,
                                                self._DEVICE)
        self.assertEqual(mgmt_address, '%s.%s' % (topics.SERVICEVM_AGENT,
                                                  self._DEVICE['id']))

        mgmt_driver.mgmt_call(self.plugin, self._CONTEXT, self._DEVICE,
                              self._KWARGS)
        msg = {'args': self._KWARGS['kwargs'],
               'namespace': None,
               'method': 'action-name'}
        self.mock_rpc_proxy_cast.assert_called_once_with(
            self._CONTEXT, msg, topic='device-address')

        mgmt_driver.mgmt_delete_post(self.plugin, self._CONTEXT, self._DEVICE)
        mock_instance.destroy_rpc_proxy.assert_has_calls([
            mock.call(self._CONTEXT, self._PORT_ID, self._PROXY_ID[1]),
            mock.call(self._CONTEXT, self._PORT_ID, self._PROXY_ID[0])])
        mock_instance.destroy_rpc_namespace_proxy.assert_has_calls([
            mock.call(self._CONTEXT, self._PORT_ID, self._NS_PROXY_ID[1]),
            mock.call(self._CONTEXT, self._PORT_ID, self._NS_PROXY_ID[0])])
        mock_instance.destroy_namespace_agent.assert_called_once_with(
            self.plugin._core_plugin, self._CONTEXT, self._PORT_ID)

    def test_mgmt_service_create_pre_delete_post(self):
        mgmt_driver = self.mgmt_driver
        mock_instance = self.mock_proxy_api_instance

        mgmt_driver.mgmt_create_post(self.plugin, self._CONTEXT, self._DEVICE)
        mock_instance.create_namespace_agent.assert_called_once_with(
            self.plugin._core_plugin, self._CONTEXT, self._NETWORK_ID)
        target = 'topic=%s,server=%s' % (topics.SERVICEVM_AGENT,
                                         self._DEVICE['id'])
        mock_instance.create_rpc_proxy.assert_has_calls([
            mock.call(self._CONTEXT, mock.ANY, target, target, 'receive'),
            mock.call(self._CONTEXT, mock.ANY, target, target, 'send')])
        dst_transport_url = cfg.CONF.dst_transport_url % {'host':
                                                          self._IP_ADDRESS}
        mock_instance.create_rpc_namespace_proxy.assert_has_calls([
            mock.call(self._CONTEXT, self._PORT_ID, target, dst_transport_url,
                      target, 'receive'),
            mock.call(self._CONTEXT, self._PORT_ID, target, dst_transport_url,
                      target, 'send')])

        mock_instance.create_rpc_proxy.reset_mock()
        mock_instance.create_rpc_namespace_proxy.reset_mock()
        mgmt_driver.mgmt_service_create_pre(
            self.plugin, self._CONTEXT, self._DEVICE, self._SERVICE_INSTANCE)
        target = 'topic=%s-%s,server=%s' % (
            topics.SERVICEVM_AGENT, self._DEVICE['id'],
            self._SERVICE_INSTANCE['id'])
        mock_instance.create_rpc_proxy.assert_has_calls([
            mock.call(self._CONTEXT, self._PORT_ID, target, target, 'receive'),
            mock.call(self._CONTEXT, self._PORT_ID, target, target, 'send')])
        dst_transport_url = cfg.CONF.dst_transport_url % {'host':
                                                          self._IP_ADDRESS}
        mock_instance.create_rpc_namespace_proxy.assert_has_calls([
            mock.call(self._CONTEXT, self._PORT_ID, target, dst_transport_url,
                      target, 'receive'),
            mock.call(self._CONTEXT, self._PORT_ID, target, dst_transport_url,
                      target, 'send')])

        mgmt_service_address = mgmt_driver.mgmt_service_address(
            self.plugin, self._CONTEXT, self._DEVICE, self._SERVICE_INSTANCE)
        self.assertEqual(mgmt_service_address, '%s-%s.%s' % (
            topics.SERVICEVM_AGENT, self._DEVICE['id'],
            self._SERVICE_INSTANCE['id']))
        mgmt_driver.mgmt_service_call(
            self.plugin, self._CONTEXT, self._DEVICE, self._SERVICE_INSTANCE,
            self._KWARGS)
        msg = {'args': self._KWARGS['kwargs'],
               'namespace': None,
               'method': 'action-name'}
        self.mock_rpc_proxy_cast.assert_called_once_with(
            self._CONTEXT, msg, topic='service-instance-address')

        mgmt_driver.mgmt_service_delete_post(
            self.plugin, self._CONTEXT, self._DEVICE, self._SERVICE_INSTANCE)
        mock_instance.destroy_rpc_proxy.assert_has_calls([
            mock.call(self._CONTEXT, self._PORT_ID, self._PROXY_ID[3]),
            mock.call(self._CONTEXT, self._PORT_ID, self._PROXY_ID[2])])
        mock_instance.destroy_rpc_namespace_proxy.assert_has_calls([
            mock.call(self._CONTEXT, self._PORT_ID, self._NS_PROXY_ID[3]),
            mock.call(self._CONTEXT, self._PORT_ID, self._NS_PROXY_ID[2])])

        mock_instance.destroy_rpc_proxy.reset.mock()
        mock_instance.destroy_rpc_namespace_proxy.reset_mock()
        mgmt_driver.mgmt_delete_post(self.plugin, self._CONTEXT, self._DEVICE)
        mock_instance.destroy_rpc_proxy.assert_has_calls([
            mock.call(self._CONTEXT, self._PORT_ID, self._PROXY_ID[1]),
            mock.call(self._CONTEXT, self._PORT_ID, self._PROXY_ID[0])])
        mock_instance.destroy_rpc_namespace_proxy.assert_has_calls([
            mock.call(self._CONTEXT, self._PORT_ID, self._NS_PROXY_ID[1]),
            mock.call(self._CONTEXT, self._PORT_ID, self._NS_PROXY_ID[0])])
        mock_instance.destroy_namespace_agent.assert_called_once_with(
            self.plugin._core_plugin, self._CONTEXT, self._PORT_ID)
