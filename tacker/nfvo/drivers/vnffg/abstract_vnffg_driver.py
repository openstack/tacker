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
class VnffgAbstractDriver(extensions.PluginInterface):

    @abc.abstractmethod
    def get_type(self):
        """Return one of predefined type of Tacker drivers."""
        pass

    @abc.abstractmethod
    def get_name(self):
        """Return a symbolic name for the Tacker VNFFG SFC driver."""
        pass

    @abc.abstractmethod
    def get_description(self):
        pass

    @abc.abstractmethod
    def create_chain(self, name, fc_id, vnfs, symmetrical=False,
                     auth_attr=None):
        """Create service function chain and returns an ID"""
        pass

    @abc.abstractmethod
    def update_chain(self, chain_id, fc_ids, vnfs,
                     symmetrical=False,
                     auth_attr=None):
        """Update service function chain"""
        pass

    @abc.abstractmethod
    def delete_chain(self, chain_id, auth_attr=None):
        """Delete service function chain"""
        pass

    @abc.abstractmethod
    def create_flow_classifier(self, name, fc, auth_attr=None):
        """Create flow classifier and returns an ID"""
        pass

    @abc.abstractmethod
    def update_flow_classifier(self, fc_id, fc, auth_attr=None):
        """Update flow classifier"""
        pass

    @abc.abstractmethod
    def delete_flow_classifier(self, fc_id, auth_attr=None):
        """Delete flow classifier"""
        pass
