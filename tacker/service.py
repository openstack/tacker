# Copyright 2011 VMware, Inc
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

import inspect
import os
import random

import logging as std_logging

from oslo_config import cfg
from oslo_log import log as logging
from oslo_service import loopingcall
from oslo_service import service
from oslo_utils import excutils
from oslo_utils import importutils

from tacker._i18n import _
from tacker.common import config
from tacker.common import rpc as n_rpc
from tacker import context
from tacker import wsgi


service_opts = [
    cfg.IntOpt('report_interval',
               default=10,
               help=_('Seconds between running components report states')),
    cfg.IntOpt('periodic_interval',
               default=40,
               help=_('Seconds between running periodic tasks')),
    cfg.IntOpt('api_workers',
               default=0,
               help=_('Number of separate worker processes for service')),
    cfg.IntOpt('periodic_fuzzy_delay',
               default=5,
               help=_('Range of seconds to randomly delay when starting the '
                      'periodic task scheduler to reduce stampeding. '
                      '(Disable by setting to 0)')),
]
CONF = cfg.CONF
CONF.register_opts(service_opts)


def config_opts():
    return [(None, service_opts)]


LOG = logging.getLogger(__name__)


class WsgiService(service.ServiceBase):
    """Base class for WSGI based services.

    For each api you define, you must also define these flags:
    :<api>_listen: The address on which to listen
    :<api>_listen_port: The port on which to listen

    """

    def __init__(self, app_name):
        self.app_name = app_name
        self.wsgi_app = None

    def start(self):
        self.wsgi_app = _run_wsgi(self.app_name)

    def wait(self):
        if self.wsgi_app:
            self.wsgi_app.wait()

    def stop(self):
        pass

    def reset(self):
        pass


class TackerApiService(WsgiService):
    """Class for tacker-api service."""

    @classmethod
    def create(cls, app_name='tacker'):

        # Setup logging early
        config.setup_logging(cfg.CONF)
        # Dump the initial option values
        cfg.CONF.log_opt_values(LOG, std_logging.DEBUG)
        service = cls(app_name)
        return service


def serve_wsgi(cls):

    try:
        service = cls.create()
    except Exception:
        with excutils.save_and_reraise_exception():
            LOG.exception('Unrecoverable error: please check log '
                          'for details.')

    return service


def _run_wsgi(app_name):
    app = config.load_paste_app(app_name)
    if not app:
        LOG.error('No known API applications configured.')
        return
    server = wsgi.Server("Tacker")
    server.start(app, cfg.CONF.bind_port, cfg.CONF.bind_host,
                 workers=cfg.CONF.api_workers)
    # Dump all option values here after all options are parsed
    cfg.CONF.log_opt_values(LOG, std_logging.DEBUG)
    LOG.info("Tacker service started, listening on %(host)s:%(port)s",
             {'host': cfg.CONF.bind_host,
              'port': cfg.CONF.bind_port})
    return server


class Service(n_rpc.Service):
    """Service object for binaries running on hosts.

    A service takes a manager and enables rpc by listening to queues based
    on topic. It also periodically runs tasks on the manager.
    """

    def __init__(self, host, binary, topic, manager, report_interval=None,
                 periodic_interval=None, periodic_fuzzy_delay=None,
                 *args, **kwargs):

        self.binary = binary
        self.manager_class_name = manager
        manager_class = importutils.import_class(self.manager_class_name)
        self.manager = manager_class(host=host, *args, **kwargs)
        self.report_interval = report_interval
        self.periodic_interval = periodic_interval
        self.periodic_fuzzy_delay = periodic_fuzzy_delay
        self.saved_args, self.saved_kwargs = args, kwargs
        self.timers = []
        super(Service, self).__init__(host, topic, manager=self.manager)

    def start(self):
        self.manager.start()
        self.manager.init_host()
        super(Service, self).start()
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

    def __getattr__(self, key):
        manager = self.__dict__.get('manager', None)
        return getattr(manager, key)

    @classmethod
    def create(cls, host=None, binary=None, topic=None, manager=None,
               report_interval=None, periodic_interval=None,
               periodic_fuzzy_delay=None):
        """Instantiates class and passes back application object.

        :param host: defaults to cfg.CONF.host
        :param binary: defaults to basename of executable
        :param topic: defaults to bin_name - 'tacker-' part
        :param manager: defaults to cfg.CONF.<topic>_manager
        :param report_interval: defaults to cfg.CONF.report_interval
        :param periodic_interval: defaults to cfg.CONF.periodic_interval
        :param periodic_fuzzy_delay: defaults to cfg.CONF.periodic_fuzzy_delay

        """
        if not host:
            host = cfg.CONF.host
        if not binary:
            binary = os.path.basename(inspect.stack()[-1][1])
        if not topic:
            topic = binary.rpartition('tacker-')[2]
            topic = topic.replace("-", "_")
        if not manager:
            manager = cfg.CONF.get('%s_manager' % topic, None)
        if report_interval is None:
            report_interval = cfg.CONF.report_interval
        if periodic_interval is None:
            periodic_interval = cfg.CONF.periodic_interval
        if periodic_fuzzy_delay is None:
            periodic_fuzzy_delay = cfg.CONF.periodic_fuzzy_delay
        service_obj = cls(host, binary, topic, manager,
                          report_interval=report_interval,
                          periodic_interval=periodic_interval,
                          periodic_fuzzy_delay=periodic_fuzzy_delay)

        return service_obj

    def kill(self):
        """Destroy the service object."""
        self.stop()

    def stop(self):
        self.manager.stop()
        super(Service, self).stop()
        for x in self.timers:
            try:
                x.stop()
            except Exception:
                LOG.exception("Exception occurs when timer stops")
        self.timers = []

    def wait(self):
        super(Service, self).wait()
        for x in self.timers:
            try:
                x.wait()
            except Exception:
                LOG.exception("Exception occurs when waiting for timer")

    def reset(self):
        config.reset_service()

    def periodic_tasks(self, raise_on_error=False):
        """Tasks to be run at a periodic interval."""
        ctxt = context.get_admin_context()
        self.manager.periodic_tasks(ctxt, raise_on_error=raise_on_error)

    def report_state(self):
        """Update the state of this service."""
        # Todo(gongysh) report state to neutron server
        pass
