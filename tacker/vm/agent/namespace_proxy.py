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

import eventlet
eventlet.monkey_patch()


import os.path
import random
import sys
import uuid

from oslo.config import cfg
from oslo import messaging
from oslo.messaging._drivers import impl_unix
from oslo.messaging import proxy
from oslo.messaging import rpc

from tacker.agent.common import config as agent_config
from tacker.agent.linux import daemon
from tacker.common import config
from tacker.common import legacy
from tacker.common import topics
from tacker.common import utils
from tacker import context
from tacker import manager
from tacker.openstack.common import importutils
from tacker.openstack.common import lockutils
from tacker.openstack.common import log as logging
from tacker.openstack.common import service
from tacker import oslo_service
from tacker.vm.agent import config as vm_config
from tacker.vm.agent import target


LOG = logging.getLogger(__name__)


class NamespaceProxies(object):
    def __init__(self):
        super(NamespaceProxies, self).__init__()
        self.urls = {}          # dict: transport_url -> transport
        self.transports = {}    # dict: transport -> transport_url
        self.proxies = {}       # uuid -> (transport, proxy_server)
        self.transport_to_proxies = {}  # transport -> set of proxy_servers

    def get_transport(self, transport_url):
        return self.urls.get(transport_url, None)

    def add_transport(self, transport_url, transport):
        assert transport_url not in self.urls
        assert transport not in self.transports
        self.transports[transport_url] = transport
        self.urls[transport] = transport_url

    def del_proxy(self, namespace_proxy_id):
        transport, proxy_server = self.proxies.pop(namespace_proxy_id)
        proxies = self.transport_to_proxies[transport]
        proxies.remove(proxy_server)
        if proxies:
            transport = None
        else:
            transport_url = self.urls.pop(transport)
            del self.transports[transport_url]
            del self.transport_to_proxies[transport]
        return (transport, proxy_server)

    def add_proxy(self, namespace_proxy_id, transport, proxy_server):
        assert namespace_proxy_id not in self.proxies
        self.proxies[namespace_proxy_id] = (transport, proxy_server)
        proxies = self.transport_to_proxies.setdefault(transport, set())
        proxies.add(proxy_server)


class ServiceVMNamespaceAgent(manager.Manager):
    def __init__(self, host=None, **kwargs):
        LOG.debug(_('host %(host)s, kwargs %(kwargs)s'),
                  {'host': host, 'kwargs': kwargs})
        super(ServiceVMNamespaceAgent, self).__init__(host=host)

        for key in ('conf', 'src_transport', 'server_stop', ):
            setattr(self, key, kwargs[key])
        assert self.src_transport is not None
        assert self.server_stop is not None

        self._proxies = NamespaceProxies()

    def stop(self):
        LOG.debug('stop')
        self.server_stop()
        ns_proxies = self._proxies
        for _transport, proxy_server in ns_proxies.proxies.values():
            proxy_server.stop()

    def wait(self):
        LOG.debug('wait')
        ns_proxies = self._proxies
        for _transport, proxy_server in ns_proxies.proxies.values():
            proxy_server.wait()
        for transport in ns_proxies.transports.values():
            transport.cleanup()

    @lockutils.synchronized('servicevm-namespace-agent', 'tacker-')
    def destroy_namespace_agent(self, context):
        self.stop()

    def _create_rpc_namespace_proxy(self, src_transport, src_target,
                                    dst_transport, dst_target):
        src_target = target.target_parse(src_target)
        assert src_target.server
        dst_target = target.target_parse(dst_target)
        assert dst_target.server
        return proxy.get_proxy_server(
            src_transport, src_target, None,
            dst_transport, dst_target, None, executor='eventlet')

    @lockutils.synchronized('servicevm-namespace-agent', 'tacker-')
    def create_rpc_namespace_proxy(self, context, src_target,
                                   dst_transport_url, dst_target, direction):
        LOG.debug('create_rpc_namespace_proxy %s %s %s %s %s',
                  context, src_target, dst_transport_url, dst_target,
                  direction)
        dst_transport = self._proxies.get_transport(dst_transport_url)
        if dst_transport is None:
            dst_transport = messaging.get_transport(self.conf,
                                                    dst_transport_url)
            self._proxies.add_transport(dst_transport_url, dst_transport)
        if direction == 'send':
            proxy_server = self._create_rpc_namespace_proxy(
                self.src_transport, src_target, dst_transport, dst_target)
        elif direction == 'receive':
            proxy_server = self._create_rpc_namespace_proxy(
                dst_transport, dst_target, self.src_transport, src_target)
        else:
            msg = _('unknown direction %s') % direction
            LOG.error(msg)
            raise RuntimeError(msg)

        # proxy_server.start()
        eventlet.spawn(proxy_server.start)
        namespace_proxy_id = str(uuid.uuid4())
        self._proxies.add_proxy(namespace_proxy_id,
                                dst_transport, proxy_server)
        LOG.debug('namespace_proxy_id %s', namespace_proxy_id)
        return namespace_proxy_id

    @lockutils.synchronized('servicevm-namespace-agent', 'tacker-')
    def destroy_rpc_namespace_proxy(self, context, namespace_proxy_id):
        LOG.debug('namespace_proxy_id %s', namespace_proxy_id)
        try:
            transport, proxy_server = self._proxies.del_proxy(
                namespace_proxy_id)
        except KeyError:
            return
        proxy_server.stop()
        proxy_server.wait()
        if transport is not None:
            transport.cleanup()


# TODO(yamahata): class Service is stolen from nova.service and modified.
#                 port tacker to oslo.messaging and delete this class.
class Service(service.Service):
    def __init__(self, conf, host, binary, topic, manager_,
                 report_interval=None, periodic_enable=None,
                 periodic_fuzzy_delay=None, periodic_interval_max=None,
                 *args, **kwargs):
        super(Service, self).__init__()
        self.conf = conf
        self.host = host
        self.binary = binary
        self.topic = topic
        self.manager_class_name = manager_
        manager_class = importutils.import_class(self.manager_class_name)
        kwargs_ = kwargs.copy()
        kwargs_['conf'] = conf
        self.manager = manager_class(host=self.host, *args, **kwargs_)
        self.src_transport = kwargs['src_transport']
        self.rpcserver = None
        self.report_interval = report_interval
        self.periodic_enable = periodic_enable
        self.periodic_fuzzy_delay = periodic_fuzzy_delay
        self.periodic_interval_max = periodic_interval_max
        self.saved_args, self.saved_kwargs = args, kwargs

    def start(self):
        self.manager.init_host()
        LOG.debug(_("Creating RPC server for service %(topic)s %(driver)s"),
                  {'topic': self.topic, 'driver': self.src_transport._driver})

        target = messaging.Target(topic=self.topic, server=self.host)
        endpoints = [self.manager]
        self.rpcserver = rpc.get_rpc_server(self.src_transport, target,
                                            endpoints, executor='eventlet')
        self.rpcserver.start()

        if self.periodic_enable:
            if self.periodic_fuzzy_delay:
                initial_delay = random.randint(0, self.periodic_fuzzy_delay)
            else:
                initial_delay = None

            self.tg.add_dynamic_timer(
                self.periodic_tasks, initial_delay=initial_delay,
                periodic_interval_max=self.periodic_interval_max)
        self.manager.after_start()
        LOG.debug('start done')

    @classmethod
    def create(cls, conf, src_transport,
               host=None, binary=None, topic=None, manager_=None, **kwargs):
        if not host:
            host = conf.host
        if not binary:
            binary = os.path.basename(sys.argv[0])
        if not topic:
            topic = binary.rpartition('tacker-')[2]
            topic = topic.replace('-', '_')
        if not manager_:
            manager_ = conf.get('%s_manager' % topic, None)
        service_obj = cls(conf, host, binary, topic, manager_,
                          src_transport=src_transport, **kwargs)
        return service_obj

    def kill(self):
        self.stop()

    def stop(self):
        try:
            self.rpcserver.stop()
            self.manager.stop()
        except Exception:
            LOG.exception(_('failed to stop rpcserver'))

        super(Service, self).stop()

    def wait(self):
        try:
            self.rpcserver.wait()
            self.manager.wait()
        except Exception:
            LOG.exception(_('failed to wait rpcserver'))

        super(Service, self).wait()

    def periodic_tasks(self, raise_on_error=False):
        """Tasks to be run at a periodic interval."""
        ctxt = context.get_admin_context()
        return self.manager.periodic_tasks(ctxt, raise_on_error=raise_on_error)

    def report_state(self):
        pass


class ProxyDaemon(daemon.Daemon):
    def __init__(self, conf):
        self._conf = conf
        super(ProxyDaemon, self).__init__(conf.pid_file, uuid=conf.port_id)

    def run(self):
        conf = self._conf

        def server_stop():
            server.stop()
        LOG.debug(_('src transport url %s'), conf.src_transport_url)
        src_transport = messaging.get_transport(
            conf, conf.src_transport_url,
            aliases=oslo_service.TRANSPORT_ALIASES)
        server = Service.create(
            conf=conf, topic=topics.SERVICEVM_AGENT_NAMEPSACE,
            manager_=('tacker.vm.agent.namespace_proxy.'
                      'ServiceVMNamespaceAgent'),
            src_transport=src_transport, server_stop=server_stop)
        service.launch(server).wait()
        src_transport.cleanup()


def _register_options(conf):
    cli_opts = [
        cfg.StrOpt('pid-file', help=_('pid file of this process.')),
        cfg.StrOpt('port-id', help=_('uuid of port')),
        cfg.StrOpt('src-transport-url', help='src transport url'),
        cfg.BoolOpt('daemonize', default=True, help=_('Run as daemon'))
    ]
    conf.register_cli_opts(cli_opts)
    agent_config.register_agent_state_opts_helper(conf)
    agent_config.register_root_helper(conf)
    conf.register_cli_opts(vm_config.OPTS)
    conf.register_opts(impl_unix.unix_opts)


def main():
    conf = cfg.CONF

    # NOTE(yamahata): work around. rpc driver-dependent config variables
    # remove this line once tacker are fully ported to oslo.messaging
    from tacker.openstack.common import rpc
    conf.unregister_opts(rpc.rpc_opts)

    # NOTE(yamahata): corresponds to
    # tacker.common.config.rpc.set_default(control_exchange='tacker')
    messaging.set_transport_defaults('tacker')

    _register_options(conf)
    conf(project='tacker')
    config.setup_logging(conf)
    legacy.modernize_quantum_config(conf)
    # NOTE(yamahata): workaround for state_path
    #                 oslo.messaging doesn't know state_path
    conf.set_override('rpc_unix_ipc_dir', conf.svcvm_proxy_dir)
    utils.log_opt_values(LOG)

    proxy = ProxyDaemon(conf)
    if conf.daemonize:
        proxy.start()
    else:
        proxy.run()


if __name__ == '__main__':
    main()
