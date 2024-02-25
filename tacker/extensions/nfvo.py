# Copyright 2016 Brocade Communications Systems Inc
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

import abc

from tacker._i18n import _
from tacker.api import extensions
from tacker.api.v1 import attributes as attr
from tacker.api.v1 import resource_helper
from tacker.common import exceptions
from tacker.plugins.common import constants
from tacker.services import service_base


class VimUnauthorizedException(exceptions.TackerException):
    message = _("%(message)s")


class VimConnectionException(exceptions.TackerException):
    message = _("%(message)s")


class VimInUseException(exceptions.TackerException):
    message = _("VIM %(vim_id)s is still in use by VNF")


class VimDefaultNotDefined(exceptions.TackerException):
    message = _("Default VIM is not defined.")


class VimDefaultDuplicateException(exceptions.TackerException):
    message = _("Default VIM already exists %(vim_id)s.")


class VimNotFoundException(exceptions.TackerException):
    message = _("Specified VIM id %(vim_id)s is invalid. Please verify and "
                "pass a valid VIM id")


class VimRegionNotFoundException(exceptions.TackerException):
    message = _("Unknown VIM region name %(region_name)s")


class VimKeyNotFoundException(exceptions.TackerException):
    message = _("Unable to find key file for VIM %(vim_id)s")


class VimEncryptKeyError(exceptions.TackerException):
    message = _("Barbican must be enabled for VIM %(vim_id)s")


class VimUnsupportedResourceTypeException(exceptions.TackerException):
    message = _("Resource type %(type)s is unsupported by VIM")


class VimGetResourceException(exceptions.TackerException):
    message = _("Error while trying to issue %(cmd)s to find resource type "
                "%(type)s by resource name %(name)s")


class VimGetResourceNameNotUnique(exceptions.TackerException):
    message = _("Getting resource id from VIM with resource name %(name)s "
                "by %(cmd)s returns more than one")


class VimGetResourceNotFoundException(exceptions.TackerException):
    message = _("Getting resource id from VIM with resource name %(name)s "
                "by %(cmd)s returns nothing")


class VimFromVnfNotFoundException(exceptions.NotFound):
    message = _('VIM from VNF %(vnf_id)s could not be found')


NAME_MAX_LEN = 255

RESOURCE_ATTRIBUTE_MAP = {

    'vims': {
        'id': {
            'allow_post': False,
            'allow_put': False,
            'validate': {'type:uuid': None},
            'is_visible': True,
            'primary_key': True,
        },
        'tenant_id': {
            'allow_post': True,
            'allow_put': False,
            'validate': {'type:string': None},
            'required_by_policy': True,
            'is_visible': True
        },
        'type': {
            'allow_post': True,
            'allow_put': False,
            'validate': {'type:not_empty_string': None},
            'is_visible': True
        },
        'auth_url': {
            'allow_post': True,
            'allow_put': False,
            'validate': {'type:string': None},
            'is_visible': True
        },
        'auth_cred': {
            'allow_post': True,
            'allow_put': True,
            'validate': {'type:dict_not_empty': None},
            'is_visible': True,
        },
        'vim_project': {
            'allow_post': True,
            'allow_put': True,
            'validate': {'type:dict_not_empty': None},
            'is_visible': True,
        },
        'name': {
            'allow_post': True,
            'allow_put': True,
            'validate': {'type:string': NAME_MAX_LEN},
            'is_visible': True,
        },
        'description': {
            'allow_post': True,
            'allow_put': True,
            'validate': {'type:string': None},
            'is_visible': True,
            'default': '',
        },
        'status': {
            'allow_post': False,
            'allow_put': False,
            'validate': {'type:string': None},
            'is_visible': True,
        },
        'placement_attr': {
            'allow_post': False,
            'allow_put': False,
            'is_visible': True,
            'default': None,
        },
        'shared': {
            'allow_post': False,
            'allow_put': False,
            'is_visible': False,
            'convert_to': attr.convert_to_boolean,
            'required_by_policy': True
        },
        'is_default': {
            'allow_post': True,
            'allow_put': True,
            'is_visible': True,
            'validate': {'type:boolean': None},
            'default': False
        },
        'created_at': {
            'allow_post': False,
            'allow_put': False,
            'is_visible': True,
        },
        'updated_at': {
            'allow_post': False,
            'allow_put': False,
            'is_visible': True,
        },
        'extra': {
            'allow_post': True,
            'allow_put': True,
            'convert_to': attr.convert_none_to_empty_dict,
            'validate': {'type:dict_or_nodata': None},
            'is_visible': True,
            'default': None
        },
    },
}


class Nfvo(extensions.ExtensionDescriptor):
    @classmethod
    def get_name(cls):
        return 'NFV Orchestrator'

    @classmethod
    def get_alias(cls):
        return 'NFVO'

    @classmethod
    def get_description(cls):
        return "Extension for NFV Orchestrator"

    @classmethod
    def get_namespace(cls):
        return 'https://wiki.openstack.org/Tacker'

    @classmethod
    def get_updated(cls):
        return "2015-12-21T10:00:00-00:00"

    @classmethod
    def get_resources(cls):
        special_mappings = {}
        plural_mappings = resource_helper.build_plural_mappings(
            special_mappings, RESOURCE_ATTRIBUTE_MAP)
        attr.PLURALS.update(plural_mappings)
        return resource_helper.build_resource_info(
            plural_mappings, RESOURCE_ATTRIBUTE_MAP, constants.NFVO,
            translate_name=True)

    @classmethod
    def get_plugin_interface(cls):
        return NFVOPluginBase

    def update_attributes_map(self, attributes):
        super(Nfvo, self).update_attributes_map(
            attributes, extension_attrs_map=RESOURCE_ATTRIBUTE_MAP)

    def get_extended_resources(self, version):
        version_map = {'1.0': RESOURCE_ATTRIBUTE_MAP}
        return version_map.get(version, {})


class NFVOPluginBase(service_base.NFVPluginBase, metaclass=abc.ABCMeta):
    def get_plugin_name(self):
        return constants.NFVO

    def get_plugin_type(self):
        return constants.NFVO

    def get_plugin_description(self):
        return 'Tacker NFV Orchestrator plugin'

    @abc.abstractmethod
    def create_vim(self, context, vim):
        pass

    @abc.abstractmethod
    def update_vim(self, context, vim_id, vim):
        pass

    @abc.abstractmethod
    def delete_vim(self, context, vim_id):
        pass

    @abc.abstractmethod
    def get_vim(self, context, vim_id, fields=None, mask_password=True):
        pass

    @abc.abstractmethod
    def get_vims(self, context, filters=None, fields=None):
        pass

    def get_default_vim(self, context):
        pass
