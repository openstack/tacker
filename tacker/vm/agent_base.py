# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
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

# TODO(yamahata): consolidate with l3-agent, lbaas-agent once
#                 agent consolidation is done.
# https://blueprints.launchpad.net/tacker/+spec/l3-agent-consolication

import abc
import six


# TODO(yamahata)
# communicate with service vm
@six.add_metaclass(abc.ABCMeta)
class ServiceVMAgentBase(object):

    @abc.abstractmethod
    def create(self, info):
        pass

    @abc.abstractmethod
    def delete(self, info):
        pass

    @abc.abstractmethod
    def update(self, info):
        pass
