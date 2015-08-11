# Copyright 2011 VMware, Inc
# All Rights Reserved.
#
# based on tacker.service and nova.service
# Copyright 2013, 2014 Intel Corporation.
# Copyright 2013, 2014 Isaku Yamahata <isaku.yamahata at intel com>
#                                     <isaku.yamahata at gmail com>
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
# @author: Isaku Yamahata, Intel Corporation.

import inspect
import os.path
import random

import oslo_messaging

from tacker import context
from tacker.openstack.common.gettextutils import _
from tacker.openstack.common import importutils
from tacker.openstack.common import log as logging
from tacker.openstack.common import loopingcall
from tacker.openstack.common import service
from tacker import service as tacker_service  # noqa  # for service_opts


LOG = logging.getLogger(__name__)
TRANSPORT_ALIASES = {
    'tacker.openstack.common.rpc.impl_kombu': 'rabbit',
    'tacker.openstack.common.rpc.impl_qpid': 'qpid',
    'tacker.openstack.common.rpc.impl_zmq': 'zmq',
    'tacker.openstack.common.rpc.impl_fake': 'fake',
}


# replacement for tacker.openstack.common.rpc.service.Service
class RpcService(service.Service):
    """Service object for binaries running on hosts.

    A service enables rpc by listening to queues based on topic and host.
    """
    def __init__(self, conf, host, topic, manager=None, serializer=None):
        super(RpcService, self).__init__()
        self.conf = conf
        self.host = host
        self.topic = topic
        self.serializer = serializer
        if manager is None:
            self.manager = self
        else:
            self.manager = manager

    def start(self):
        super(RpcService, self).start()

        target = oslo_messaging.Target(topic=self.topic, server=self.host)
        endpoints = [self.manager]
        transport = oslo_messaging.get_transport(self.conf,
                                            aliases=TRANSPORT_ALIASES)
        self.rpcserver = oslo_messaging.get_rpc_server(
            transport, target, endpoints, executor='eventlet',
            serializer=self.serializer)

        # Hook to allow the manager to do other initializations after
        # the rpc connection is created.
        if callable(getattr(self.manager, 'initialize_service_hook', None)):
            self.manager.initialize_service_hook(self)

        self.rpcserver.start()

    def stop(self):
        # Try to shut the connection down, but if we get any sort of
        # errors, go ahead and ignore them.. as we're shutting down anyway
        try:
            self.rpcserver.stop()
            self.rpcserver.wait()
        except Exception:
            pass
        super(RpcService, self).stop()


# replacement for tacker.service.Service
class TackerService(RpcService):
    def __init__(self, conf, host, binary, topic, manager,
                 report_interval=None,
                 periodic_interval=None, periodic_fuzzy_delay=None,
                 *args, **kwargs):
        self.binary = binary
        self.manager_class_name = manager
        manager_class = importutils.import_class(self.manager_class_name)
        self.manager = manager_class(conf=conf, host=host, *args, **kwargs)
        self.report_interval = report_interval
        self.periodic_interval = periodic_interval
        self.periodic_fuzzy_delay = periodic_fuzzy_delay
        self.saved_args, self.saved_kwargs = args, kwargs
        self.timers = []
        super(TackerService, self).__init__(conf, host, topic,
                                            manager=self.manager)

    def start(self):
        self.manager.init_host()
        super(TackerService, self).start()
        if self.report_interval:
            pulse = loopingcall.FixedIntervalLoopingCall(self.report_state)
            pulse.start(interval=self.report_interval,
                        initial_delay=self.report_interval)
            self.timers.append(pulse)

        if self.periodic_interval:
            if self.periodic_fuzzy_delay:
                initial_delay = random.randint(0, self.periodic_fuzzy_delay)
            else:
                initial_delay = None

            periodic = loopingcall.FixedIntervalLoopingCall(
                self.periodic_tasks)
            periodic.start(interval=self.periodic_interval,
                           initial_delay=initial_delay)
            self.timers.append(periodic)
        self.manager.after_start()

    def kill(self):
        """Destroy the service object."""
        self.stop()

    def stop(self):
        super(TackerService, self).stop()
        for x in self.timers:
            try:
                x.stop()
            except Exception:
                LOG.exception(_("Exception occurs when timer stops"))
                pass
        self.timers = []

    def wait(self):
        super(TackerService, self).wait()
        for x in self.timers:
            try:
                x.wait()
            except Exception:
                LOG.exception(_("Exception occurs when waiting for timer"))
                pass

    def periodic_tasks(self, raise_on_error=False):
        """Tasks to be run at a periodic interval."""
        ctxt = context.get_admin_context()
        self.manager.periodic_tasks(ctxt, raise_on_error=raise_on_error)

    def report_state(self):
        """Update the state of this service."""
        # Todo(gongysh) report state to tacker server
        pass

    def __getattr__(self, key):
        manager = self.__dict__.get('manager', None)
        return getattr(manager, key)

    @classmethod
    def create(cls, conf, host=None, binary=None, topic=None, manager=None,
               report_interval=None, periodic_interval=None,
               periodic_fuzzy_delay=None):
        """Instantiates class and passes back application object.

        :param host: defaults to conf.host
        :param binary: defaults to basename of executable
        :param topic: defaults to bin_name - 'nova-' part
        :param manager: defaults to conf.<topic>_manager
        :param report_interval: defaults to conf.report_interval
        :param periodic_interval: defaults to conf.periodic_interval
        :param periodic_fuzzy_delay: defaults to conf.periodic_fuzzy_delay

        """
        if not host:
            host = conf.host
        if not binary:
            binary = os.path.basename(inspect.stack()[-1][1])
        if not topic:
            topic = binary.rpartition('tacker-')[2]
            topic = topic.replace("-", "_")
        if not manager:
            manager = conf.get('%s_manager' % topic, None)
        if report_interval is None:
            report_interval = conf.AGENT.report_interval
        if periodic_interval is None:
            periodic_interval = conf.periodic_interval
        if periodic_fuzzy_delay is None:
            periodic_fuzzy_delay = conf.periodic_fuzzy_delay
        service_obj = cls(conf, host, binary, topic, manager,
                          report_interval=report_interval,
                          periodic_interval=periodic_interval,
                          periodic_fuzzy_delay=periodic_fuzzy_delay)

        return service_obj
