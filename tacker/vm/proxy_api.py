# Copyright 2013, 2014 Intel Corporation.
# Copyright 2013, 2014 Isaku Yamahata <isaku.yamahata at intel com>
#                                     <isaku.yamahata at gmail com>
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

import inspect

from tacker.api.v1 import attributes
from tacker.common import rpc_compat
from tacker.openstack.common import excutils
from tacker.openstack.common import log as logging
from tacker.plugins.common import constants


LOG = logging.getLogger(__name__)


# TODO(yamahata): convert oslo.messaging
class ServiceVMPluginApi(rpc_compat.RpcProxy):
    API_VERSION = '1.0'

    def __init__(self, topic):
        super(ServiceVMPluginApi, self).__init__(topic, self.API_VERSION)

    def _call(self, context, **kwargs):
        method = inspect.stack()[1][3]
        LOG.debug('ServiceVMPluginApi method = %s kwargs = %s', method, kwargs)
        return self.call(context, self.make_msg(method, **kwargs))

    def create_namespace_agent(self, core_plugin, context, network_id):
        """
        :param dst_transport_url: st
        :type dst_transport_url: str that represents
                                 oslo.messaging.transportURL
        """
        port_data = {
            'name': '_svcvm-rpc-namespace-agent-' + network_id,
            'network_id': network_id,
            'mac_address': attributes.ATTR_NOT_SPECIFIED,
            'admin_state_up': True,
            'device_id': '_svcvm-rpc-proxy-' + network_id,
            'device_owner': 'tacker:' + constants.SERVICEVM,
            'fixed_ips': attributes.ATTR_NOT_SPECIFIED,
        }
        port = core_plugin.create_port(context, {'port': port_data})
        for i in xrange(len(port['fixed_ips'])):
            ipallocation = port['fixed_ips'][i]
            subnet_id = ipallocation['subnet_id']
            subnet = core_plugin.get_subnet(context, subnet_id)
            ipallocation['subnet'] = subnet
        port_id = port['id']
        try:
            self._call(context, port=port)
        except Exception:
            with excutils.save_and_reraise_exception():
                core_plugin.delete_port(context, port_id)
        return port_id

    def destroy_namespace_agent(self, core_plugin, context, port_id):
        self._call(context, port_id=port_id)
        core_plugin.delete_port(context, port_id)

    def create_rpc_proxy(self, context, port_id, src_target, dst_unix_target,
                         direction):
        """
        :param src_target: target to listen/send
        :type src_target: oslo.messaging.Target
        :param dst_unix_target: target to send/listen
        :type dst_unix_target: oslo.messaging.Target
        :param direction: RPC direction
        :type direction: str 'send' or 'receive'
                        'send': tacker server -> agent
                        'receive': neturon server <- agent
        """
        return self._call(context, port_id=port_id, src_target=src_target,
                          dst_unix_target=dst_unix_target, direction=direction)

    def destroy_rpc_proxy(self, context, port_id, rpc_proxy_id):
        return self._call(context, proxy_id=port_id, rpc_proxy_id=rpc_proxy_id)

    def create_rpc_namespace_proxy(self, context, port_id, src_target,
                                   dst_transport_url, dst_target, direction):
        """
        :param src_target: target to listen/send
        :type src_target: oslo.messaging.Target
        :param dst_target: target to send/listen
        :type dst_target: oslo.messaging.Target
        :param direction: RPC direction
        :type direction: str 'send' or 'receive'
                        'send': tacker server -> agent
                        'receive': neturon server <- agent
        """
        return self._call(context, port_id=port_id,
                          src_target=src_target,
                          dst_transport_url=dst_transport_url,
                          dst_target=dst_target, direction=direction)

    def destroy_rpc_namespace_proxy(self, context, port_id,
                                    namespace_proxy_id):
        return self._call(context, port_id=port_id,
                          namespace_proxy_id=namespace_proxy_id)
