# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
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

import abc

import six

from tacker.api import extensions


@six.add_metaclass(abc.ABCMeta)
class VNFMonitorAbstractDriver(extensions.PluginInterface):

    @abc.abstractmethod
    def get_type(self):
        """Return one of predefined type of the hosting device drivers."""
        pass

    @abc.abstractmethod
    def get_name(self):
        """Return a symbolic name for the VNF Monitor plugin."""
        pass

    @abc.abstractmethod
    def get_description(self):
        """Return description of VNF Monitor plugin."""
        pass

    def monitor_get_config(self, plugin, context, device):
        """Return dict of monitor configuration data.

        :param plugin:
        :param context:
        :param device:
        :returns: dict
        :returns: dict of monitor configuration data
        """
        return {}

    @abc.abstractmethod
    def monitor_url(self, plugin, context, device):
        """Return the url of device to monitor.

        :param plugin:
        :param context:
        :param device:
        :returns: string
        :returns: url of device to monitor
        """
        pass

    @abc.abstractmethod
    def monitor_call(self, device, kwargs):
        """Monitor.

        Return boolean value True if VNF is healthy
        or return a event string like 'failure' or 'calls-capacity-reached'
        for specific VNF health condition.

        :param device:
        :param kwargs:
        :returns: boolean
        :returns: True if VNF is healthy
        """
        pass

    def monitor_service_driver(self, plugin, context, device,
                               service_instance):
        # use same monitor driver to communicate with service
        return self.get_name()
