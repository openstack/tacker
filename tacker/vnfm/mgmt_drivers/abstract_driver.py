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
class VnfMGMTAbstractDriver(extensions.PluginInterface):

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

    def mgmt_create_pre(self, plugin, context, vnf):
        pass

    def mgmt_create_post(self, plugin, context, vnf):
        pass

    def mgmt_update_pre(self, plugin, context, vnf):
        pass

    def mgmt_update_post(self, plugin, context, vnf):
        pass

    def mgmt_delete_pre(self, plugin, context, vnf):
        pass

    def mgmt_delete_post(self, plugin, context, vnf):
        pass

    def mgmt_get_config(self, plugin, context, vnf):
        """Get a dict of objects.

        Returns dict of file-like objects which will be passed to hosting
        vnf.
        It depends on drivers how to use it.
        for nova case, it can be used for meta data, file injection or
        config drive
        i.e.
        metadata case: nova --meta <key>=<value>
        file injection case: nova --file <dst-path>:<src-path>
        config drive case: nova --config-drive=true --file \
                                <dst-path>:<src-path>
        """
        return {}

    @abc.abstractmethod
    def mgmt_ip_address(self, plugin, context, vnf):
        pass

    @abc.abstractmethod
    def mgmt_call(self, plugin, context, vnf, kwargs):
        pass
