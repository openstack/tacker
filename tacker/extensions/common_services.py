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

import six

from tacker.api import extensions
from tacker.api.v1 import attributes as attr
from tacker.api.v1 import resource_helper
from tacker.common import exceptions
from tacker.plugins.common import constants
from tacker.services import service_base


class EventCreationFailureException(exceptions.TackerException):
    message = _("Failed to create an event: %(error_str)s")


class EventNotFoundException(exceptions.TackerException):
    message = _("Specified Event id %(evt_id)s is invalid. Please verify and "
                "pass a valid Event id")


class InvalidModelException(exceptions.TackerException):
    message = _("Specified model is invalid, only Event model supported")


class InputValuesMissing(exceptions.InvalidInput):
    message = _("Parameter input values missing for the key '%(key)s'")


class ParamYAMLInputMissing(exceptions.InvalidInput):
    message = _("Parameter YAML input missing")


RESOURCE_ATTRIBUTE_MAP = {

    'events': {
        'id': {
            'allow_post': False,
            'allow_put': False,
            'is_visible': True,
        },
        'resource_id': {
            'allow_post': False,
            'allow_put': False,
            'is_visible': True
        },
        'resource_type': {
            'allow_post': False,
            'allow_put': False,
            'is_visible': True
        },
        'resource_state': {
            'allow_post': False,
            'allow_put': False,
            'is_visible': True
        },
        'timestamp': {
            'allow_post': False,
            'allow_put': False,
            'is_visible': True,
        },
        'event_details': {
            'allow_post': False,
            'allow_put': False,
            'is_visible': True,
        },
        'event_type': {
            'allow_post': False,
            'allow_put': False,
            'is_visible': True,
        },
    }
}


class Common_services(extensions.ExtensionDescriptor):
    @classmethod
    def get_name(cls):
        return 'COMMONSERVICES'

    @classmethod
    def get_alias(cls):
        return 'Commonservices'

    @classmethod
    def get_description(cls):
        return "Extension for CommonServices"

    @classmethod
    def get_namespace(cls):
        return 'http://wiki.openstack.org/Tacker'

    @classmethod
    def get_updated(cls):
        return "2016-06-06T13:00:00-00:00"

    @classmethod
    def get_resources(cls):
        special_mappings = {}
        plural_mappings = resource_helper.build_plural_mappings(
            special_mappings, RESOURCE_ATTRIBUTE_MAP)
        attr.PLURALS.update(plural_mappings)
        return resource_helper.build_resource_info(
            plural_mappings, RESOURCE_ATTRIBUTE_MAP, constants.COMMONSERVICES,
            translate_name=True)

    @classmethod
    def get_plugin_interface(cls):
        return CommonServicesPluginBase

    def update_attributes_map(self, attributes):
        super(Common_services, self).update_attributes_map(
            attributes, extension_attrs_map=RESOURCE_ATTRIBUTE_MAP)

    def get_extended_resources(self, version):
        version_map = {'1.0': RESOURCE_ATTRIBUTE_MAP}
        return version_map.get(version, {})


@six.add_metaclass(abc.ABCMeta)
class CommonServicesPluginBase(service_base.NFVPluginBase):
    def get_plugin_name(self):
        return constants.COMMONSERVICES

    def get_plugin_type(self):
        return constants.COMMONSERVICES

    def get_plugin_description(self):
        return 'Tacker CommonServices plugin'

    @abc.abstractmethod
    def get_event(self, context, event_id, fields=None):
        pass

    @abc.abstractmethod
    def get_events(self, context, filters=None, fields=None, sorts=None,
                   limit=None, marker_obj=None, page_reverse=False):
        pass
