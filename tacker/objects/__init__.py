#    Copyright 2018 NTT DATA.
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

# NOTE(bhagyashris): You may scratch your head as you see code that imports
# this module and then accesses attributes for objects such as Instance,
# etc, yet you do not see these attributes in here. Never fear, there is
# a little bit of magic. When objects are registered, an attribute is set
# on this module automatically, pointing to the newest/latest version of
# the object.


def register_all():
    # NOTE(bhagyashris): You must make sure your object gets imported in this
    # function in order for it to be registered by services that may
    # need to receive it via RPC.
    __import__('tacker.objects.heal_vnf_request')
    __import__('tacker.objects.vnfd')
    __import__('tacker.objects.vnf_package')
    __import__('tacker.objects.vnf_package_vnfd')
    __import__('tacker.objects.vnf_deployment_flavour')
    __import__('tacker.objects.vnf_software_image')
    __import__('tacker.objects.vnf_instance')
    __import__('tacker.objects.vnf_instantiated_info')
    __import__('tacker.objects.vim_connection')
    __import__('tacker.objects.instantiate_vnf_req')
    __import__('tacker.objects.vnf_resources')
    __import__('tacker.objects.vnf')
    __import__('tacker.objects.vnfd')
    __import__('tacker.objects.vnf_lcm_op_occs')
    __import__('tacker.objects.terminate_vnf_req')
    __import__('tacker.objects.vnf_artifact')
    __import__('tacker.objects.vnf_lcm_subscriptions')
    __import__('tacker.objects.scale_vnf_request')
    __import__('tacker.objects.grant')
    __import__('tacker.objects.grant_request')
    __import__('tacker.objects.vnfd')
    __import__('tacker.objects.vnfd_attribute')
