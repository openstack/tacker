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
class VnfAbstractDriver(extensions.PluginInterface):

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
    def update_wait(self, plugin, context, vnf_dict):
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

    @abc.abstractmethod
    def heal_vdu(self, plugin, context, vnf_dict, heal_request_data):
        pass

    @abc.abstractmethod
    def pre_instantiation_vnf(self, context, vnf_instance,
                              vim_connection_info, vnf_software_images):
        """Create resources required for instantiating Vnf.

        :param context: A RequestContext
        :param vnf_instance: Object tacker.objects.VnfInstance
        :vim_info: Credentials to initialize Vim connection
        :vnf_software_images: Dict of key:value pair,
          <VDU/Storage node name>:tacker.objects.VnfSoftwareImage.
        """
        pass

    @abc.abstractmethod
    def delete_vnf_instance_resource(self, context, vnf_instance,
            vim_connection_info, vnf_resource):
        pass

    @abc.abstractmethod
    def instantiate_vnf(self, context, vnf_instance, vnfd_dict,
                        vim_connection_info, instantiate_vnf_req,
                        grant_response):
        pass

    @abc.abstractmethod
    def post_vnf_instantiation(self, context, vnf_instance,
                               vim_connection_info):
        pass

    @abc.abstractmethod
    def heal_vnf(self, context, vnf_instance, vim_connection_info,
                 heal_vnf_request):
        """Heal vnf

        :param context: A RequestContext
        :param vnf_instance: tacker.objects.VnfInstance to be healed
        :vim_info: Credentials to initialize Vim connection
        :heal_vnf_request: tacker.objects.HealVnfRequest object containing
                           parameters passed in the heal request
        """
        pass

    @abc.abstractmethod
    def heal_vnf_wait(self, context, vnf_instance, vim_connection_info):
        """Check vnf is healed successfully"""
        pass

    @abc.abstractmethod
    def post_heal_vnf(self, context, vnf_instance, vim_connection_info,
                      heal_vnf_request):
        """Update resource_id for each vnfc resources

        :param context: A RequestContext
        :param vnf_instance: tacker.objects.VnfInstance to be healed
        :vim_info: Credentials to initialize Vim connection
        :heal_vnf_request: tacker.objects.HealVnfRequest object containing
                           parameters passed in the heal request
        """
        pass
