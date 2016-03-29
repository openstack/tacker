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

import abc

import six

from tacker.api import extensions


@six.add_metaclass(abc.ABCMeta)
class DeviceAbstractDriver(extensions.PluginInterface):

    @abc.abstractmethod
    def get_type(self):
        """Return one of predefined type of the hosting device drivers."""
        pass

    @abc.abstractmethod
    def get_name(self):
        """Return a symbolic name for the service VM plugin."""
        pass

    @abc.abstractmethod
    def get_description(self):
        pass

    # @abc.abstractmethod
    def create_device_template_pre(self, plugin, context, device_template):
        """Called before creating device template."""
        pass

    @abc.abstractmethod
    def create(self, plugin, context, device):
        """Create device and return its id."""

    @abc.abstractmethod
    def create_wait(self, plugin, context, device_dict, device_id):
        """wait for device creation to complete."""

    @abc.abstractmethod
    def update(self, plugin, context, device_id, device_dict, device):
        # device_dict: old device_dict to be updated
        # device: update with device dict
        pass

    @abc.abstractmethod
    def update_wait(self, plugin, context, device_id):
        pass

    @abc.abstractmethod
    def delete(self, plugin, context, device_id):
        pass

    @abc.abstractmethod
    def delete_wait(self, plugin, context, device_id):
        pass
