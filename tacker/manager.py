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

from oslo_config import cfg
from oslo_log import log as logging
import oslo_messaging
from oslo_service import periodic_task

from tacker.common import utils


LOG = logging.getLogger(__name__)


class Manager(periodic_task.PeriodicTasks):

    # Set RPC API version to 1.0 by default.
    target = oslo_messaging.Target(version='1.0')

    def __init__(self, host=None):
        if not host:
            host = cfg.CONF.host
        self.host = host
        conf = getattr(self, "conf", cfg.CONF)
        super(Manager, self).__init__(conf)

    def periodic_tasks(self, context, raise_on_error=False):
        self.run_periodic_tasks(context, raise_on_error=raise_on_error)

    def init_host(self):
        """Handle initialization if this is a standalone service.

        Child classes should override this method.

        """
        pass

    def after_start(self):
        """Handler post initialization stuff.

        Child classes can override this method.
        """
        pass


def validate_post_plugin_load():
    """Checks if the configuration variables are valid.

    If the configuration is invalid then the method will return an error
    message. If all is OK then it will return None.
    """
    message = None
    return message


def validate_pre_plugin_load():
    """Checks if the configuration variables are valid.

    If the configuration is invalid then the method will return an error
    message. If all is OK then it will return None.
    """
    message = None
    return message


class TackerManager(object):
    """Tacker's Manager class.

    Tacker's Manager class is responsible for parsing a config file and
    instantiating the correct plugin that concretely implement
    tacker_plugin_base class.
    The caller should make sure that TackerManager is a singleton.
    """
    _instance = None

    def __init__(self, options=None, config_file=None):
        # If no options have been provided, create an empty dict
        if not options:
            options = {}

        msg = validate_pre_plugin_load()
        if msg:
            LOG.critical(msg)
            raise Exception(msg)

        msg = validate_post_plugin_load()
        if msg:
            LOG.critical(msg)
            raise Exception(msg)

        self.service_plugins = {}
        self._load_service_plugins()

    @staticmethod
    def load_class_for_provider(namespace, plugin_provider):
        """Loads plugin using alias or class name

        Load class using stevedore alias or the class name
        :param namespace: namespace where alias is defined
        :param plugin_provider: plugin alias or class name
        :returns: plugin that is loaded
        :raises ImportError: if fails to load plugin
        """

        try:
            return utils.load_class_by_alias_or_classname(namespace,
                    plugin_provider)
        except ImportError:
            raise ImportError(_("Plugin '%s' not found.") % plugin_provider)

    def _get_plugin_instance(self, namespace, plugin_provider):
        plugin_class = self.load_class_for_provider(namespace, plugin_provider)
        return plugin_class()

    def _load_service_plugins(self):
        """Loads service plugins.

        Starts from the core plugin and checks if it supports
        advanced services then loads classes provided in configuration.
        """
        plugin_providers = cfg.CONF.service_plugins
        if 'commonservices' not in plugin_providers:
            plugin_providers.append('commonservices')
        LOG.debug("Loading service plugins: %s", plugin_providers)
        for provider in plugin_providers:
            if provider == '':
                continue
            LOG.info("Loading Plugin: %s", provider)

            plugin_inst = self._get_plugin_instance('tacker.service_plugins',
                                                    provider)
            # only one implementation of svc_type allowed
            # specifying more than one plugin
            # for the same type is a fatal exception
            if plugin_inst.get_plugin_type() in self.service_plugins:
                raise ValueError(_("Multiple plugins for service "
                                   "%s were configured"),
                                 plugin_inst.get_plugin_type())

            self.service_plugins[plugin_inst.get_plugin_type()] = plugin_inst
            # # search for possible agent notifiers declared in service plugin
            # # (needed by agent management extension)
            # if (hasattr(self.plugin, 'agent_notifiers') and
            #         hasattr(plugin_inst, 'agent_notifiers')):
            #     self.plugin.agent_notifiers.update(plugin_inst.agent_notifiers)

            LOG.debug("Successfully loaded %(type)s plugin. "
                      "Description: %(desc)s",
                      {"type": plugin_inst.get_plugin_type(),
                       "desc": plugin_inst.get_plugin_description()})

    @classmethod
    @utils.synchronized("manager")
    def _create_instance(cls):
        if cls._instance is None:
            cls._instance = cls()

    @classmethod
    def get_instance(cls):
        # double checked locking
        if cls._instance is None:
            cls._create_instance()
        return cls._instance

    @classmethod
    def get_plugin(cls):
        return cls.get_instance().plugin

    @classmethod
    def get_service_plugins(cls):
        return cls.get_instance().service_plugins

    @classmethod
    def has_instance(cls):
        return cls._instance is not None

    @classmethod
    def clear_instance(cls):
        cls._instance = None
