# Copyright 2013, 2014 Intel Corporation.
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
        """Return one of predefined type of the hosting vnf drivers."""
        pass

    @abc.abstractmethod
    def get_name(self):
        """Return a symbolic name for the service VM plugin."""
        pass

    @abc.abstractmethod
    def get_description(self):
        pass

    @abc.abstractmethod
    def create(self, plugin, context, vnf):
        """Create vnf and return its id."""

    @abc.abstractmethod
    def create_wait(self, plugin, context, vnf_dict, vnf_id):
        """wait for vnf creation to complete."""

    @abc.abstractmethod
    def update(self, plugin, context, vnf_id, vnf_dict, vnf):
        # vnf_dict: old vnf_dict to be updated
        # vnf: update with vnf dict
        pass

    @abc.abstractmethod
    def update_wait(self, plugin, context, vnf_id):
        pass

    @abc.abstractmethod
    def delete(self, plugin, context, vnf_id):
        pass

    @abc.abstractmethod
    def delete_wait(self, plugin, context, vnf_id):
        pass

    @abc.abstractmethod
    def get_resource_info(self, plugin, context, vnf_info, auth_attr,
                          region_name=None):
        '''Fetches optional details of a VNF'''
        pass
