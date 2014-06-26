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

from tacker.common import topics


_RPC_AGENT_OPTS = [
    cfg.StrOpt('device_id', default=None, help=_('The device id')),
    cfg.StrOpt('topic', default=topics.SERVICEVM_AGENT,
               help=_('rpc topic for agent to subscribe')),
]


def register_servicevm_agent_opts(conf):
    conf.register_opts(_RPC_AGENT_OPTS, group='servicevm_agent')
