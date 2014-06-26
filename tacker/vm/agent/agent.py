# Copyright 2014 Intel Corporation.
# Copyright 2014 Isaku Yamahata <isaku.yamahata at intel com>
#                                <isaku.yamahata at gmail com>
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

import atexit
import inspect
import uuid

import netaddr
from oslo.config import cfg
from oslo import messaging
from oslo.messaging._drivers import impl_unix
from oslo.messaging import proxy
from oslo.messaging import rpc
from oslo.messaging import transport

from tacker.agent.common import config as agent_config
from tacker.agent.linux import external_process
from tacker.agent.linux import interface
from tacker.agent.linux import ip_lib
from tacker.common import config
from tacker.common import legacy
from tacker.common import topics
from tacker import manager
from tacker.openstack.common import excutils
from tacker.openstack.common import importutils
from tacker.openstack.common import lockutils
from tacker.openstack.common import log as logging
from tacker.openstack.common import service
from tacker import oslo_service
from tacker.services.loadbalancer.drivers.haproxy import namespace_driver
from tacker.vm.agent import config as vm_config
from tacker.vm.agent import target

# _DEBUG = False
_DEBUG = True
LOG = logging.getLogger(__name__)


class NamespaceProxyAgentApi(object):
    """
    api servicevm agent -> namespace proxy agent
    """
    def __init__(self, unix_transport):
        super(NamespaceProxyAgentApi, self).__init__()
        target_ = messaging.Target(topic=topics.SERVICEVM_AGENT_NAMEPSACE)
        self._client = rpc.RPCClient(unix_transport, target_)

    def _call(self, **kwargs):
        method = inspect.stack()[1][3]
        ctxt = {}
        return self._client.call(ctxt, method, **kwargs)

    def destroy_namespace_agent(self):
        return self._call()

    def create_rpc_namespace_proxy(self, src_target,
                                   dst_transport_url, dst_target, direction):
        return self._call(
            src_target=src_target, dst_transport_url=dst_transport_url,
            dst_target=dst_target, direction=direction)

    def destroy_rpc_namespace_proxy(self, namespace_proxy_id):
        return self._call(namespace_proxy_id=namespace_proxy_id)


class NamespaceAgent(object):
    def __init__(self, port_id, unix_transport, pm):
        super(NamespaceAgent, self).__init__()
        self.port_id = port_id
        self.unix_transport = unix_transport
        self.pm = pm
        self.local_proxies = {}
        self.api = NamespaceProxyAgentApi(unix_transport)


class ServiceVMAgent(manager.Manager):
    _NS_PREFIX = 'qsvcvm-'

    @staticmethod
    def _get_ns_name(port_id):
        return ServiceVMAgent._NS_PREFIX + port_id

    def __init__(self, host=None, **kwargs):
        conf = kwargs['conf']
        super(ServiceVMAgent, self).__init__(host=host)
        self.conf = conf
        self.root_helper = agent_config.get_root_helper(self.conf)
        self._proxies = {}

        try:
            vif_driver = importutils.import_object(conf.interface_driver, conf)
        except ImportError:
            with excutils.save_and_reraise_exception():
                msg = (_('Error importing interface driver: %s')
                       % conf.interface_driver)
                LOG.error(msg)
        self._vif_driver = vif_driver
        self._proxy_agents = {}
        self._src_transport = None
        self._get_src_transport()
        atexit.register(self._atexit)

    def _atexit(self):
        for ns_agent in self._proxy_agents.values():
            ns_agent.pm.disable()
        for port_id in self._proxy_agents.keys():
            self._unplug(port_id)

    def _get_src_transport(self):
        conf = self.conf

        conf.register_opts(transport._transport_opts)
        rpc_backend = conf.rpc_backend
        if conf.transport_url is not None:
            src_url = conf.transport_url
        elif (rpc_backend.endswith('.impl_kombu') or
              rpc_backend.endswith('.impl_rabbit')):
            from oslo.messaging._drivers import impl_rabbit
            conf.register_opts(impl_rabbit.rabbit_opts)
            src_url = 'rabbit://%s:%s@%s:%s/%s' % (
                conf.rabbit_userid, conf.rabbit_password,
                conf.rabbit_host, conf.rabbit_port,
                conf.rabbit_virtual_host)
        elif rpc_backend.endswith('.impl_qpid'):
            from oslo.messaging._drivers import impl_qpid
            conf.register_opts(impl_qpid.qpid_opts)
            src_url = 'qpid://%s:%s@%s:%s/' % (
                conf.pid_username, conf.qpid_password,
                conf.qpid_hostname, conf.qpid_port)
        elif rpc_backend.endswith('.impl_zmq'):
            from oslo.messaging._drivers import impl_zmq
            conf.register_opts(impl_zmq.zmq_opts)
            src_url = 'zmq://%s:%s/' % (conf.rpc_zmq_host, conf.rpc_zmq_port)
        elif rpc_backend.endswith('.impl_fake'):
            src_url = 'fake:///'
        else:
            raise NotImplementedError(
                _('rpc_backend %s is not supported') % rpc_backend)

        self._src_transport = messaging.get_transport(conf, src_url)

    def __del__(self):
        if self._src_transport is not None:
            self._src_transport.cleanup()

    # def create_device(self, context, device):
    #     LOG.debug(_('create_device %s'), device)

    # def update_device(self, context, device):
    #     LOG.debug(_('update_device %s'), device)

    # def delete_device(self, context, device):
    #     LOG.debug(_('delete_device %s'), device)

    # def create_service(self, context, device, service_instance):
    #     LOG.debug(_('create_service %(device)s %(service_instance)s'),
    #               {'device': device, 'service_instance': service_instance})

    # def update_service(self, context, device, service_instance):
    #     LOG.debug(_('update_service %(device)s %(service_instance)s'),
    #               {'device': device, 'service_instance': service_instance})

    # def delete_service(self, context, device, service_instance):
    #     LOG.debug(_('delete_service %(device)s %(service_instance)s'),
    #               {'device': device, 'service_instance': service_instance})

    # TODO(yamahata): copied from loadbalancer/drivers/haproxy/namespace_driver
    #                 consolidate it.
    def _plug(self, port_config):
        vif_driver = self._vif_driver
        namespace = self._get_ns_name(port_config['id'])
        interface_name = vif_driver.get_device_name(
            namespace_driver.Wrap(port_config))

        if not ip_lib.device_exists(interface_name, self.root_helper,
                                    namespace):
            vif_driver.plug(
                port_config['network_id'], port_config['id'], interface_name,
                port_config['mac_address'], namespace=namespace)
        cidrs = [
            '%s/%s' % (ip['ip_address'],
                       netaddr.IPNetwork(ip['subnet']['cidr']).prefixlen)
            for ip in port_config['fixed_ips']
        ]
        vif_driver.init_l3(interface_name, cidrs, namespace=namespace)

        gw_ip = port_config['fixed_ips'][0]['subnet'].get('gateway_ip')
        if gw_ip:
            cmd = ['route', 'add', 'default', 'gw', gw_ip]
            ip_wrapper = ip_lib.IPWrapper(self.root_helper,
                                          namespace=namespace)
            ip_wrapper.netns.execute(cmd, check_exit_code=False)

    def _unplug(self, port_id):
        port_stub = {'id': port_id}
        namespace = self._get_ns_name(port_id)
        vif_driver = self._vif_driver
        interface_name = vif_driver.get_device_name(
            namespace_driver.Wrap(port_stub))
        vif_driver.unplug(interface_name, namespace=namespace)

    @lockutils.synchronized('servicevm-agent', 'tacker-')
    def create_namespace_agent(self, context, port):
        conf = self.conf
        port_id = port['id']
        path = 'rpc-proxy-%s' % port_id
        unix_url = 'punix:///%s' % path
        unix_transport = messaging.get_transport(conf, unix_url)
        unix_transport._driver.punix_listening.wait()

        self._plug(port)
        pm = external_process.ProcessManager(
            conf, port_id, root_helper=self.root_helper,
            namespace=self._get_ns_name(port_id))

        def cmd_callback(pid_file_name):
            cmd = ['tacker-servicevm-ns-rpc-proxy',
                   '--pid-file=%s' % pid_file_name,
                   '--svcvm-proxy-dir=%s' % conf.svcvm_proxy_dir,
                   '--src-transport-url', 'unix:///%s' % path]
            cmd.extend(agent_config.get_log_args(
                conf, 'tacker-servicevm-ns-rpc-proxy-%s.log' % port_id))
            if _DEBUG:
                cmd += ['--log-file=/tmp/tacker-servicevm-ns-rpc-proxy-'
                        '%s.log' % port_id]
            return cmd
        pm.enable(cmd_callback)

        ns_agent = NamespaceAgent(port_id, unix_transport, pm)
        self._proxy_agents[port_id] = ns_agent

    @lockutils.synchronized('servicevm-agent', 'tacker-')
    def destroy_namespace_agent(self, context, port_id):
        ns_agent = self._proxy_agents.pop(port_id)
        ns_agent.api.destroy_namespace_agent()
        for proxy_server in ns_agent.local_proxies.values():
            proxy_server.stop()
        for proxy_server in ns_agent.local_proxies.values():
            proxy_server.wait()
        ns_agent.pm.disable()
        self._unplug(port_id)

    def _create_rpc_proxy(self, ns_agent, src_transport, src_target,
                          dst_transport, dst_target):
        rpc_proxy_id = str(uuid.uuid4())
        src_target = target.target_parse(src_target)
        assert src_target.server
        dst_target = target.target_parse(dst_target)
        assert dst_target.server
        proxy_server = proxy.get_proxy_server(
            src_transport, src_target, None,
            dst_transport, dst_target, None, executor='eventlet')
        ns_agent.local_proxies[rpc_proxy_id] = proxy_server
        proxy_server.start()
        return rpc_proxy_id

    def _get_proxy_agent(self, port_id):
        ns_agent = self._proxy_agents.get(port_id)
        if ns_agent is None:
            msg = _('unknown port_id %s') % port_id
            LOG.error(msg)
            raise RuntimeError(msg)
        return ns_agent

    @lockutils.synchronized('servicevm-agent', 'tacker-')
    def create_rpc_proxy(self, context, port_id,
                         src_target, dst_unix_target, direction):
        ns_agent = self._get_proxy_agent(port_id)
        if direction == 'send':
            return self._create_rpc_proxy(
                ns_agent, self._src_transport, src_target,
                ns_agent.unix_transport, dst_unix_target)
        elif direction == 'receive':
            return self._create_rpc_proxy(
                ns_agent, ns_agent.unix_transport, dst_unix_target,
                self._src_transport, src_target)
        else:
            msg = _('unknown direction %s') % direction
            LOG.error(msg)
            raise RuntimeError(msg)

    @lockutils.synchronized('servicevm-agent', 'tacker-')
    def destroy_rpc_proxy(self, context, port_id, rpc_proxy_id):
        ns_agent = self._get_proxy_agent(port_id)
        proxy_server = ns_agent.local_proxies.pop(rpc_proxy_id)
        proxy_server.stop()
        proxy_server.wait()

    @lockutils.synchronized('servicevm-agent', 'tacker-')
    def create_rpc_namespace_proxy(self, context, port_id, src_target,
                                   dst_transport_url, dst_target, direction):
        ns_agent = self._get_proxy_agent(port_id)
        ns_proxy_id = ns_agent.api.create_rpc_namespace_proxy(
            src_target, dst_transport_url, dst_target, direction)
        LOG.debug("create_rpc_namespace_proxy %s", ns_proxy_id)
        return ns_proxy_id

    @lockutils.synchronized('servicevm-agent', 'tacker-')
    def destroy_rpc_namespace_proxy(self, context,
                                    port_id, namespace_proxy_id):
        ns_agent = self._get_proxy_agent(port_id)
        return ns_agent.api.destroy_rpc_namespace_proxy(namespace_proxy_id)


class ServiceVMAgentWithStateReport(ServiceVMAgent):
    # TODO(yamahata)
    pass


def _register_options(conf):
    conf.register_opts(interface.OPTS)
    agent_config.register_interface_driver_opts_helper(conf)
    agent_config.register_agent_state_opts_helper(conf)
    agent_config.register_root_helper(conf)
    conf.register_opts(vm_config.OPTS)
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

    server = oslo_service.TackerService.create(
        topic=topics.SERVICEVM_AGENT,
        manager='tacker.vm.agent.agent.ServiceVMAgentWithStateReport',
        report_interval=conf.AGENT.report_interval,
        conf=conf)
    service.launch(server).wait()


if __name__ == '__main__':
    main()
