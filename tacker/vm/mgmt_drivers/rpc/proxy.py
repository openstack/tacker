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

from oslo.config import cfg

from tacker.db.vm import proxy_db
from tacker.openstack.common import log as logging
from tacker.vm import constants
from tacker.vm.mgmt_drivers.rpc import rpc


LOG = logging.getLogger(__name__)


class AgentRpcProxyMGMTDriver(rpc.AgentRpcMGMTDriver):
    _TRANSPORT_OPTS = [
        cfg.StrOpt('dst_transport_url',
                   # TODO(yamahata): make user, pass, port configurable
                   # per servicevm
                   #'<scheme>://<user>:<pass>@<host>:<port>/'
                   default='rabbit://guest:guest@%(host)s:5672/',
                   help='A URL representing the messaging driver '
                   'to use and its full configuration.'),
    ]

    def __init__(self, conf=None):
        super(AgentRpcProxyMGMTDriver, self).__init__()
        self.db = proxy_db.RpcProxyDb()
        self.conf = conf or cfg.CONF
        self.conf.register_opts(self._TRANSPORT_OPTS)

    def get_type(self):
        return 'agent-proxy'

    def get_name(self):
        return 'agent-proxy'

    def get_description(self):
        return 'agent-proxy'

    def mgmt_create_post(self, plugin, context, device):
        LOG.debug('mgmt_create_post')
        mgmt_entries = [sc_entry for sc_entry in device['service_context']
                        if (sc_entry['role'] == constants.ROLE_MGMT and
                            sc_entry.get('port_id'))]
        assert mgmt_entries
        mgmt_entry = mgmt_entries[0]

        vm_port_id = mgmt_entry['port_id']
        vm_port = plugin._core_plugin.get_port(context, vm_port_id)
        fixed_ip = vm_port['fixed_ips'][0]['ip_address']
        # TODO(yamahata): make all parameters(scheme, user, pass, port)
        #                 configurable
        dst_transport_url = self.conf.dst_transport_url % {'host': fixed_ip}

        network_id = mgmt_entry['network_id']
        assert network_id

        proxy_api = plugin.proxy_api
        port_id = proxy_api.create_namespace_agent(plugin._core_plugin,
                                                   context, network_id)

        device_id = device['id']
        target = 'topic=%s,server=%s' % (self._mgmt_topic(device),
                                         self._mgmt_server(device))
        svr_proxy_id = proxy_api.create_rpc_proxy(
            context, port_id, target, target, 'receive')
        LOG.debug('mgmt_create_post: svr_proxy_id: %s', svr_proxy_id)
        svr_ns_proxy_id = proxy_api.create_rpc_namespace_proxy(
            context, port_id, target, dst_transport_url, target, 'receive')
        LOG.debug('mgmt_create_post: svr_ns_proxy_id: %s', svr_ns_proxy_id)
        clt_proxy_id = proxy_api.create_rpc_proxy(
            context, port_id, target, target, 'send')
        LOG.debug('mgmt_create_post: clt_proxy_id: %s', clt_proxy_id)
        clt_ns_proxy_id = proxy_api.create_rpc_namespace_proxy(
            context, port_id, target, dst_transport_url, target, 'send')
        LOG.debug('mgmt_create_post: clt_ns_proxy_id: %s', clt_ns_proxy_id)

        LOG.debug('mgmt_create_ppost: '
                  'svr: %s svr_ns: %s clt: %s clt_ns: %s ',
                  svr_proxy_id, svr_ns_proxy_id, clt_proxy_id, clt_ns_proxy_id)
        self.db.create_proxy_mgmt_port(
            context, device_id, port_id, dst_transport_url,
            svr_proxy_id, svr_ns_proxy_id, clt_proxy_id, clt_ns_proxy_id)

    def mgmt_delete_post(self, plugin, context, device):
        LOG.debug('mgmt_delete_post')
        device_id = device['id']

        proxy_mgmt_port = self.db.get_proxy_mgmt_port(context, device_id)
        port_id = proxy_mgmt_port['port_id']
        svr_proxy_id = proxy_mgmt_port['svr_proxy_id']
        svr_ns_proxy_id = proxy_mgmt_port['svr_ns_proxy_id']
        clt_proxy_id = proxy_mgmt_port['clt_proxy_id']
        clt_ns_proxy_id = proxy_mgmt_port['clt_ns_proxy_id']

        proxy_api = plugin.proxy_api
        proxy_api.destroy_rpc_namespace_proxy(context,
                                              port_id, clt_ns_proxy_id)
        proxy_api.destroy_rpc_proxy(context, port_id, clt_proxy_id)
        proxy_api.destroy_rpc_namespace_proxy(context,
                                              port_id, svr_ns_proxy_id)
        proxy_api.destroy_rpc_proxy(context, port_id, svr_proxy_id)
        proxy_api.destroy_namespace_agent(plugin._core_plugin,
                                          context, port_id)

        self.db.delete_proxy_mgmt_port(context, port_id)

    def mgmt_service_create_pre(self, plugin, context, device,
                                service_instance):
        LOG.debug('mgmt_service_create_pre')
        proxy_mgmt_port = self.db.get_proxy_mgmt_port(context, device['id'])
        port_id = proxy_mgmt_port['port_id']
        dst_transport_url = proxy_mgmt_port['dst_transport_url']

        proxy_api = plugin.proxy_api
        target = 'topic=%s,server=%s' % (
            self._mgmt_service_topic(device, service_instance),
            self._mgmt_service_server(device, service_instance))
        svr_proxy_id = proxy_api.create_rpc_proxy(
            context, port_id, target, target, 'receive')
        LOG.debug('mgmt_service_create_pre: svr_proxy_id: %s', svr_proxy_id)
        svr_ns_proxy_id = proxy_api.create_rpc_namespace_proxy(
            context, port_id, target, dst_transport_url, target, 'receive')
        LOG.debug('mgmt_service_create_pre: svr_ns_proxy_id: %s',
                  svr_ns_proxy_id)
        clt_proxy_id = proxy_api.create_rpc_proxy(
            context, port_id, target, target, 'send')
        LOG.debug('mgmt_service_create_pre: clt_proxy_id: %s', clt_proxy_id)
        clt_ns_proxy_id = proxy_api.create_rpc_namespace_proxy(
            context, port_id, target, dst_transport_url, target, 'send')
        LOG.debug('mgmt_service_create_pre: clt_ns_proxy_id: %s',
                  clt_ns_proxy_id)

        LOG.debug('mgmt_service_create_pre: '
                  'svr: %s svr_ns: %s clt: %s clt_ns: %s ',
                  svr_proxy_id, svr_ns_proxy_id, clt_proxy_id, clt_ns_proxy_id)
        self.db.create_proxy_service_port(
            context, service_instance['id'],
            svr_proxy_id, svr_ns_proxy_id, clt_proxy_id, clt_ns_proxy_id)

    def mgmt_service_delete_post(self, plugin, context, device,
                                 service_instance):
        LOG.debug('mgmt_service_delete_post')
        proxy_mgmt_port = self.db.get_proxy_mgmt_port(context, device['id'])
        port_id = proxy_mgmt_port['port_id']
        service_instance_id = service_instance['id']
        proxy_service_port = self.db.get_proxy_service_port(
            context, service_instance_id)

        svr_proxy_id = proxy_service_port['svr_proxy_id']
        svr_ns_proxy_id = proxy_service_port['svr_ns_proxy_id']
        clt_proxy_id = proxy_service_port['clt_proxy_id']
        clt_ns_proxy_id = proxy_service_port['clt_ns_proxy_id']

        proxy_api = plugin.proxy_api
        proxy_api.destroy_rpc_namespace_proxy(context,
                                              port_id, clt_ns_proxy_id)
        proxy_api.destroy_rpc_proxy(context, port_id, clt_proxy_id)
        proxy_api.destroy_rpc_namespace_proxy(context,
                                              port_id, svr_ns_proxy_id)
        proxy_api.destroy_rpc_proxy(context, port_id, svr_proxy_id)

        self.db.delete_proxy_service_port(context, service_instance_id)
