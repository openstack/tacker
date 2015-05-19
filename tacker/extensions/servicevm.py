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
#
# @author: Isaku Yamahata, Intel Corporation.

import abc

import six

from tacker.api import extensions
from tacker.api.v1 import attributes as attr
from tacker.api.v1 import resource_helper
from tacker.common import exceptions
from tacker.openstack.common import log as logging
from tacker.plugins.common import constants
from tacker.services.service_base import ServicePluginBase


LOG = logging.getLogger(__name__)


class InfraDriverNotSpecified(exceptions.InvalidInput):
    message = _('infra driver is not speicfied')


class ServiceTypesNotSpecified(exceptions.InvalidInput):
    message = _('service types are not speicfied')


class DeviceTemplateInUse(exceptions.InUse):
    message = _('device template %(device_template_id)s is still in use')


class DeviceInUse(exceptions.InUse):
    message = _('Device %(device_id)s is still in use')


class InvalidInfraDriver(exceptions.InvalidInput):
    message = _('invalid name for infra driver %(infra_driver)s')


class InvalidServiceType(exceptions.InvalidInput):
    message = _('invalid service type %(service_type)s')


class DeviceCreateFailed(exceptions.TackerException):
    message = _('creating device based on %(device_template_id)s failed')


class DeviceCreateWaitFailed(exceptions.TackerException):
    message = _('waiting for creation of device %(device_id)s failed')


class DeviceDeleteFailed(exceptions.TackerException):
    message = _('deleting device %(device_id)s failed')


class DeviceTemplateNotFound(exceptions.NotFound):
    message = _('device template %(device_tempalte_id)s could not be found')


class SeviceTypeNotFound(exceptions.NotFound):
    message = _('service type %(service_type_id)s could not be found')


class DeviceNotFound(exceptions.NotFound):
    message = _('device %(device_id)s could not be found')


class ServiceInstanceNotManagedByUser(exceptions.InUse):
    message = _('service instance %(service_instance_id)s is '
                'managed by other service')


class ServiceInstanceInUse(exceptions.InUse):
    message = _('service instance %(service_instance_id)s is still in use')


class ServiceInstanceNotFound(exceptions.NotFound):
    message = _('service instance %(service_instance_id)s could not be found')


def _validate_service_type_list(data, valid_values=None):
    if not isinstance(data, list):
        msg = _("invalid data format for service list: '%s'") % data
        LOG.debug(msg)
        return msg
    if not data:
        msg = _("empty list is not allowed for service list. '%s'") % data
        LOG.debug(msg)
        return msg
    key_specs = {
        'service_type': {
            'type:string': None,
        }
    }
    for service in data:
        msg = attr._validate_dict(service, key_specs)
        if msg:
            LOG.debug(msg)
            return msg


def _validate_service_context_list(data, valid_values=None):
    if not isinstance(data, list):
        msg = _("invalid data format for service context list: '%s'") % data
        LOG.debug(msg)
        return msg

    key_specs = {
        'network_id': {'type:uuid': None},
        'subnet_id': {'type:uuid': None},
        'port_id': {'type:uuid': None},
        'router_id': {'type:uuid': None},
        'role': {'type:string': None},
        'index': {'type:non_negative': None,
                  'convert_to': attr.convert_to_int},
    }
    for sc_entry in data:
        msg = attr._validate_dict_or_empty(sc_entry, key_specs=key_specs)
        if msg:
            LOG.debug(msg)
            return msg


attr.validators['type:service_type_list'] = _validate_service_type_list
attr.validators['type:service_context_list'] = _validate_service_context_list


RESOURCE_ATTRIBUTE_MAP = {

    'device_templates': {
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
            'is_visible': True,
        },
        'name': {
            'allow_post': True,
            'allow_put': True,
            'validate': {'type:string': None},
            'is_visible': True,
            'default': '',
        },
        'description': {
            'allow_post': True,
            'allow_put': True,
            'validate': {'type:string': None},
            'is_visible': True,
            'default': '',
        },
        'service_types': {
            'allow_post': True,
            'allow_put': False,
            'convert_to': attr.convert_to_list,
            'validate': {'type:service_type_list': None},
            'is_visible': True,
            'default': attr.ATTR_NOT_SPECIFIED,
        },
        'infra_driver': {
            'allow_post': True,
            'allow_put': False,
            'validate': {'type:string': None},
            'is_visible': True,
            'default': attr.ATTR_NOT_SPECIFIED,
        },
        'mgmt_driver': {
            'allow_post': True,
            'allow_put': False,
            'validate': {'type:string': None},
            'is_visible': True,
            'default': attr.ATTR_NOT_SPECIFIED,
        },
        'attributes': {
            'allow_post': True,
            'allow_put': False,
            'convert_to': attr.convert_none_to_empty_dict,
            'validate': {'type:dict_or_nodata': None},
            'is_visible': True,
            'default': None,
        },
    },

    'devices': {
        'id': {
            'allow_post': False,
            'allow_put': False,
            'validate': {'type:uuid': None},
            'is_visible': True,
            'primary_key': True
        },
        'tenant_id': {
            'allow_post': True,
            'allow_put': False,
            'validate': {'type:string': None},
            'required_by_policy': True,
            'is_visible': True
        },
        'template_id': {
            'allow_post': True,
            'allow_put': False,
            'validate': {'type:uuid': None},
            'is_visible': True,
        },
        'name': {
            'allow_post': True,
            'allow_put': True,
            'validate': {'type:string': None},
            'is_visible': True,
            'default': '',
        },
        'description': {
            'allow_post': True,
            'allow_put': True,
            'validate': {'type:string': None},
            'is_visible': True,
            'default': '',
        },
        'instance_id': {
            'allow_post': False,
            'allow_put': False,
            'validate': {'type:string': None},
            'is_visible': True,
        },
        'mgmt_url': {
            'allow_post': False,
            'allow_put': False,
            'validate': {'type:string': None},
            'is_visible': True,
        },
        'attributes': {
            'allow_post': True,
            'allow_put': True,
            'validate': {'type:dict_or_none': None},
            'is_visible': True,
            'default': {},
        },
        'service_contexts': {
            'allow_post': True,
            'allow_put': False,
            'validate': {'type:service_context_list': None},
            'is_visible': True,
            'default': [],
        },
        'services': {
            'allow_post': False,
            'allow_put': False,
            'validate': {'type:uuid': None},
            'is_visible': True,
        },
        'status': {
            'allow_post': False,
            'allow_put': False,
            'is_visible': True,
        },
    },

    # 'service_instances': {
    #     'id': {
    #         'allow_post': False,
    #         'allow_put': False,
    #         'validate': {'type:uuid': None},
    #         'is_visible': True,
    #         'primary_key': True
    #     },
    #     'tenant_id': {
    #         'allow_post': True,
    #         'allow_put': False,
    #         'validate': {'type:string': None},
    #         'required_by_policy': True,
    #         'is_visible': True
    #     },
    #     'name': {
    #         'allow_post': True,
    #         'allow_put': True,
    #         'validate': {'type:string': None},
    #         'is_visible': True,
    #     },
    #     'service_type_id': {
    #         'allow_post': True,
    #         'allow_put': False,
    #         'validate': {'type:uuid': None},
    #         'is_visible': True,
    #     },
    #     'service_table_id': {
    #         'allow_post': True,
    #         'allow_put': False,
    #         'validate': {'type:string': None},
    #         'is_visible': True,
    #     },
    #     'mgmt_driver': {
    #         'allow_post': True,
    #         'allow_put': False,
    #         'validate': {'type:string': None},
    #         'is_visible': True,
    #     },
    #     'mgmt_url': {
    #         'allow_post': True,
    #         'allow_put': False,
    #         'validate': {'type:string': None},
    #         'is_visible': True,
    #     },
    #     'service_contexts': {
    #         'allow_post': True,
    #         'allow_put': False,
    #         'validate': {'type:service_context_list': None},
    #         'is_visible': True,
    #     },
    #     'devices': {
    #         'allow_post': True,
    #         'allow_put': False,
    #         'validate': {'type:uuid_list': None},
    #         'convert_to': attr.convert_to_list,
    #         'is_visible': True,
    #     },
    #     'status': {
    #         'allow_post': False,
    #         'allow_put': False,
    #         'is_visible': True,
    #     },
    #     'kwargs': {
    #         'allow_post': True,
    #         'allow_put': True,
    #         'validate': {'type:dict_or_none': None},
    #         'is_visible': True,
    #         'default': {},
    #     },
    # },
}


class Servicevm(extensions.ExtensionDescriptor):
    @classmethod
    def get_name(cls):
        return 'Service VM'

    @classmethod
    def get_alias(cls):
        return 'servicevm'

    @classmethod
    def get_description(cls):
        return "Extension for ServiceVM service"

    @classmethod
    def get_namespace(cls):
        return 'http://wiki.openstack.org/Tacker/ServiceVM'

    @classmethod
    def get_updated(cls):
        return "2013-11-19T10:00:00-00:00"

    @classmethod
    def get_resources(cls):
        special_mappings = {}
        plural_mappings = resource_helper.build_plural_mappings(
            special_mappings, RESOURCE_ATTRIBUTE_MAP)
        plural_mappings['devices'] = 'device'
        plural_mappings['service_types'] = 'service_type'
        plural_mappings['service_contexts'] = 'service_context'
        plural_mappings['services'] = 'service'
        attr.PLURALS.update(plural_mappings)
        action_map = {'device': {'attach_interface': 'PUT',
                                 'detach_interface': 'PUT'}}
        return resource_helper.build_resource_info(
            plural_mappings, RESOURCE_ATTRIBUTE_MAP, constants.SERVICEVM,
            translate_name=True, action_map=action_map)

    @classmethod
    def get_plugin_interface(cls):
        return ServiceVMPluginBase

    def update_attributes_map(self, attributes):
        super(Servicevm, self).update_attributes_map(
            attributes, extension_attrs_map=RESOURCE_ATTRIBUTE_MAP)

    def get_extended_resources(self, version):
        version_map = {'1.0': RESOURCE_ATTRIBUTE_MAP}
        return version_map.get(version, {})


@six.add_metaclass(abc.ABCMeta)
class ServiceVMPluginBase(ServicePluginBase):

    def get_plugin_name(self):
        return constants.SERVICEVM

    def get_plugin_type(self):
        return constants.SERVICEVM

    def get_plugin_description(self):
        return 'Service VM plugin'

    @abc.abstractmethod
    def create_device_template(self, context, device_template):
        pass

    @abc.abstractmethod
    def delete_device_template(self, context, device_template_id):
        pass

    @abc.abstractmethod
    def get_device_template(self, context, device_template_id, fields=None):
        pass

    @abc.abstractmethod
    def get_device_templates(self, context, filters=None, fields=None):
        pass

    @abc.abstractmethod
    def get_devices(self, context, filters=None, fields=None):
        pass

    @abc.abstractmethod
    def get_device(self, context, device_id, fields=None):
        pass

    @abc.abstractmethod
    def create_device(self, context, device):
        pass

    @abc.abstractmethod
    def update_device(
            self, context, device_id, device):
        pass

    @abc.abstractmethod
    def delete_device(self, context, device_id):
        pass

    @abc.abstractmethod
    def attach_interface(self, context, id, port_id):
        pass

    @abc.abstractmethod
    def detach_interface(self, contexct, id, port_id):
        pass

    @abc.abstractmethod
    def get_service_instances(self, context, filters=None, fields=None):
        pass

    @abc.abstractmethod
    def get_service_instance(self, context, service_instance_id, fields=None):
        pass

    @abc.abstractmethod
    def update_service_instance(self, context, service_instance_id,
                                service_instance):
        pass
