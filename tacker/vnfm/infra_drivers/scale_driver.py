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
class VnfScaleAbstractDriver(extensions.PluginInterface):

    @abc.abstractmethod
    def scale(self,
              context,
              plugin,
              auth_attr,
              policy,
              region_name):
        pass

    @abc.abstractmethod
    def scale_wait(self,
                   context,
                   plugin,
                   auth_attr,
                   policy,
                   region_name):
        pass

    @abc.abstractmethod
    def get_scale_ids(self,
                      plugin,
                      context,
                      vnf_dict,
                      auth_attr,
                      region_name):
        pass

    @abc.abstractmethod
    def get_scale_in_ids(self,
                         plugin,
                         context,
                         vnf_dict,
                         is_reverse,
                         auth_attr,
                         region_name,
                         number_of_steps):
        pass

    @abc.abstractmethod
    def scale_resource_update(self, context, vnf_instance,
                              scale_vnf_request,
                              vim_connection_info):
        pass

    @abc.abstractmethod
    def scale_in_reverse(self,
              context,
              plugin,
              auth_attr,
              vnf_info,
              scale_vnf_request,
              region_name,
              scale_name_list,
              grp_id):
        pass

    @abc.abstractmethod
    def scale_out_initial(self,
              context,
              plugin,
              auth_attr,
              vnf_info,
              scale_vnf_request,
              region_name):
        pass

    @abc.abstractmethod
    def scale_update_wait(self,
                   context,
                   plugin,
                   auth_attr,
                   vnf_info,
                   region_name):
        pass

    @abc.abstractmethod
    def get_cinder_list(self,
                        vnf_info):
        pass

    @abc.abstractmethod
    def get_grant_resource(self,
                   vnf_instance,
                   vnf_info,
                   scale_vnf_request,
                   placement_obj_list,
                   vim_connection_info,
                   del_list):
        pass

    @abc.abstractmethod
    def get_rollback_ids(self,
                         plugin,
                         context,
                         vnf_dict,
                         aspect_id,
                         auth_attr,
                         region_name):
        pass
