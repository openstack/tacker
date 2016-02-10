# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright (c) 2012 OpenStack Foundation.
# All Rights Reserved.
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

from oslo_config import cfg
import oslo_messaging
from oslo_messaging import serializer as om_serializer

from tacker.common import exceptions
from tacker import context
from tacker.openstack.common import log as logging


LOG = logging.getLogger(__name__)


TRANSPORT = None
NOTIFIER = None

ALLOWED_EXMODS = [
    exceptions.__name__,
]
EXTRA_EXMODS = []


TRANSPORT_ALIASES = {
    'tacker.openstack.common.rpc.impl_fake': 'fake',
    'tacker.openstack.common.rpc.impl_qpid': 'qpid',
    'tacker.openstack.common.rpc.impl_kombu': 'rabbit',
    'tacker.openstack.common.rpc.impl_zmq': 'zmq',
    'tacker.rpc.impl_fake': 'fake',
    'tacker.rpc.impl_qpid': 'qpid',
    'tacker.rpc.impl_kombu': 'rabbit',
    'tacker.rpc.impl_zmq': 'zmq',
}


def init(conf):
    global TRANSPORT, NOTIFIER
    exmods = get_allowed_exmods()
    TRANSPORT = oslo_messaging.get_transport(conf,
                                             allowed_remote_exmods=exmods,
                                             aliases=TRANSPORT_ALIASES)
    NOTIFIER = oslo_messaging.Notifier(TRANSPORT)


def cleanup():
    global TRANSPORT, NOTIFIER
    assert TRANSPORT is not None
    assert NOTIFIER is not None
    TRANSPORT.cleanup()
    TRANSPORT = NOTIFIER = None


def add_extra_exmods(*args):
    EXTRA_EXMODS.extend(args)


def clear_extra_exmods():
    del EXTRA_EXMODS[:]


def get_allowed_exmods():
    return ALLOWED_EXMODS + EXTRA_EXMODS


def get_notifier(service=None, host=None, publisher_id=None):
    assert NOTIFIER is not None
    if not publisher_id:
        publisher_id = "%s.%s" % (service, host or cfg.CONF.host)
    return NOTIFIER.prepare(publisher_id=publisher_id)


class PluginRpcSerializer(om_serializer.Serializer):
    """Serializer.

    This serializer is used to convert RPC common context into
    Tacker Context.
    """
    def __init__(self, base):
        super(PluginRpcSerializer, self).__init__()
        self._base = base

    def serialize_entity(self, ctxt, entity):
        if not self._base:
            return entity
        return self._base.serialize_entity(ctxt, entity)

    def deserialize_entity(self, ctxt, entity):
        if not self._base:
            return entity
        return self._base.deserialize_entity(ctxt, entity)

    def serialize_context(self, ctxt):
        return ctxt.to_dict()

    def deserialize_context(self, ctxt):
        rpc_ctxt_dict = ctxt.copy()
        user_id = rpc_ctxt_dict.pop('user_id', None)
        if not user_id:
            user_id = rpc_ctxt_dict.pop('user', None)
        tenant_id = rpc_ctxt_dict.pop('tenant_id', None)
        if not tenant_id:
            tenant_id = rpc_ctxt_dict.pop('project_id', None)
        return context.Context(user_id, tenant_id,
                               load_admin_roles=False, **rpc_ctxt_dict)
