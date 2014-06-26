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

from tacker.common import topics
from tacker.common import rpc_compat
from tacker.vm.mgmt_drivers import abstract_driver
from tacker.vm.mgmt_drivers import constants


class ServiceVMAgentRpcApi(rpc_compat.RpcProxy):
    BASE_RPC_API_VERSION = '1.0'

    def __init__(self, topic=topics.SERVICEVM_AGENT):
        super(ServiceVMAgentRpcApi, self).__init__(
            topic=topic, default_version=self.BASE_RPC_API_VERSION)

    def rpc_cast(self, context, method, kwargs, topic):
        self.cast(context, self.make_msg(method, **kwargs), topic=topic)


# TODO(yamahata): port this to oslo.messaging
#                 address format needs be changed to
#                 oslo.messaging.target.Target
class AgentRpcMGMTDriver(abstract_driver.DeviceMGMTAbstractDriver):
    _TOPIC = topics.SERVICEVM_AGENT     # can be overridden by subclass
    _RPC_API = {}       # topic -> ServiceVMAgentRpcApi

    @property
    def _rpc_api(self):
        topic = self._TOPIC
        api = self._RPC_API.get(topic)
        if api is None:
            api = ServiceVMAgentRpcApi(topic=topic)
            api = self._RPC_API.setdefault(topic, api)
        return api

    def get_type(self):
        return 'agent-rpc'

    def get_name(self):
        return 'agent-rpc'

    def get_description(self):
        return 'agent-rpc'

    def mgmt_get_config(self, plugin, context, device):
        return {'/etc/tacker/servicevm-agent.ini':
                '[servicevm]\n'
                'topic = %s\n'
                'device_id = %s\n'
                % (self._TOPIC, device['id'])}

    @staticmethod
    def _address(topic, server):
        return '%s.%s' % (topic, server)

    def _mgmt_server(self, device):
        return device['id']

    def _mgmt_topic(self, device):
        return '%s-%s' % (self._TOPIC, self._mgmt_server(device))

    def mgmt_address(self, plugin, context, device):
        return self._address(self._mgmt_topic(device),
                             self._mgmt_server(device))

    def mgmt_call(self, plugin, context, device, kwargs):
        topic = device['mgmt_address']
        method = kwargs[constants.KEY_ACTION]
        kwargs_ = kwargs[constants.KEY_KWARGS]
        self._rpc_api.rpc_cast(context, method, kwargs_, topic)

    def _mgmt_service_server(self, device, service_instance):
        return '%s-%s' % (device['id'], service_instance['id'])

    def _mgmt_service_topic(self, device, service_instance):
        return '%s-%s' % (self._TOPIC,
                          self._mgmt_service_server(device, service_instance))

    def mgmt_service_address(self, plugin, context, device, service_instance):
        return self._address(
            self._mgmt_service_topic(device, service_instance),
            self._mgmt_service_server(device, service_instance))

    def mgmt_service_call(self, plugin, context, device,
                          service_instance, kwargs):
        method = kwargs[constants.KEY_ACTION]
        kwargs_ = kwargs[constants.KEY_KWARGS]
        topic = service_instance['mgmt_address']
        self._rpc_api.rpc_cast(context, method, kwargs_, topic)
