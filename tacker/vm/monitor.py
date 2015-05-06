# Copyright 2015 Intel Corporation.
# Copyright 2015 Isaku Yamahata <isaku.yamahata at intel com>
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

import abc

import six

from tacker import context as t_context
from tacker.openstack.common import log as logging


LOG = logging.getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class FailurePolicy(object):
    @abc.abstractmethod
    @classmethod
    def on_failure(cls, plugin, device_dict):
        pass

    _POLICIES = {}

    @staticmethod
    def register(policy):
        def _register(cls):
            cls._POLICIES[policy] = cls
            return cls
        return _register

    @classmethod
    def get_policy(cls, policy):
        return cls._POLICIES.get(policy)


@FailurePolicy.register('respawn')
class Respawn(FailurePolicy):
    @classmethod
    def on_failure(cls, plugin, device_dict):
        LOG.error(_('device %(device_id)s dead'), device_dict['id'])
        attributes = device_dict['attributes'].copy()
        attributes['dead_device_id'] = device_dict['id']
        new_device = {
            'tenant_id': device_dict['tenant_id'],
            'template_id': device_dict['template_id'],
            'attributes': attributes,
        }
        new_device_dict = plugin.create_device(
            t_context.get_admin_context(), new_device)
        LOG.info(_('respawned new device %s'), new_device_dict['id'])


@FailurePolicy.register('log_and_kill')
class LogAndKill(FailurePolicy):
    @classmethod
    def on_failure(cls, plugin, device_dict):
        device_id = device_dict['id']
        LOG.error(_('device %(device_id)s dead'), device_id)
        plugin.delete_device(t_context.get_admin_context(), device_id)
