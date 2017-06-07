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
class VimAbstractDriver(extensions.PluginInterface):

    @abc.abstractmethod
    def get_type(self):
        """Get VIM Driver type

        Return one of predefined types of VIMs.
        """
        pass

    @abc.abstractmethod
    def get_name(self):
        """Get VIM name

        Return a symbolic name for the VIM driver.
        """
        pass

    @abc.abstractmethod
    def get_description(self):
        pass

    @abc.abstractmethod
    def register_vim(self, context, vim_obj):
        """Register VIM object in to NFVO plugin

        Validate, encode and store VIM information for deploying VNFs.
        """
        pass

    @abc.abstractmethod
    def deregister_vim(self, context, vim_obj):
        """Deregister VIM object from NFVO plugin

        Cleanup VIM data and delete VIM information
        """
        pass

    @abc.abstractmethod
    def authenticate_vim(self, context, vim_obj):
        """Authenticate VIM connection parameters

        Validate authentication credentials and connectivity of VIM
        """
        pass

    @abc.abstractmethod
    def encode_vim_auth(self, context, vim_id, auth):
        """Encrypt VIM credentials

        Encrypt and store VIM sensitive information such as password
        """
        pass

    @abc.abstractmethod
    def delete_vim_auth(self, context, vim_id, auth):
        """Delete VIM auth keys

        Delete VIM sensitive information such as keys from file system or DB
        """
        pass

    @abc.abstractmethod
    def get_vim_resource_id(self, vim_obj, resource_type, resource_name):
        """Parses a VIM resource ID from a given type and name

        :param vim_obj: VIM information
        :param resource_type: type of resource, such as network, compute
        :param resource_name: name of resource, such at "test-network"
        :return: ID of resource
        """
        pass
