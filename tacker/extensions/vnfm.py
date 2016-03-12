# Copyright 2015 Intel Corporation..
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
from tacker.openstack.common import log as logging
from tacker.plugins.common import constants
from tacker.services import service_base


LOG = logging.getLogger(__name__)


class InfraDriverNotSpecified(exceptions.InvalidInput):
    message = _('infra driver is not specified')


class MGMTDriverNotSpecified(exceptions.InvalidInput):
    message = _('mgmt driver is not specified')


class MultipleMGMTDriversSpecified(exceptions.InvalidInput):
    message = _('More than one MGMT Driver per template is not supported')


class ServiceTypesNotSpecified(exceptions.InvalidInput):
    message = _('service types are not specified')


class DeviceTemplateInUse(exceptions.InUse):
    message = _('VNFD %(device_template_id)s is still in use')


class DeviceInUse(exceptions.InUse):
    message = _('VNF %(device_id)s is still in use')


class InvalidInfraDriver(exceptions.InvalidInput):
    message = _('invalid name for infra driver %(infra_driver)s')


class InvalidServiceType(exceptions.InvalidInput):
    message = _('invalid service type %(service_type)s')


class DeviceCreateFailed(exceptions.TackerException):
    message = _('creating VNF based on %(device_template_id)s failed')


class DeviceCreateWaitFailed(exceptions.TackerException):
    message = _('waiting for creation of VNF %(device_id)s failed')


class DeviceDeleteFailed(exceptions.TackerException):
    message = _('deleting VNF %(device_id)s failed')


class DeviceTemplateNotFound(exceptions.NotFound):
    message = _('VNFD template %(device_tempalte_id)s could not be found')


class ServiceTypeNotFound(exceptions.NotFound):
    message = _('service type %(service_type_id)s could not be found')


class DeviceNotFound(exceptions.NotFound):
    message = _('VNF %(device_id)s could not be found')


class ParamYAMLNotWellFormed(exceptions.InvalidInput):
    message = _("Parameter YAML not well formed - %(error_msg_details)s")


class ToscaParserFailed(exceptions.InvalidInput):
    message = _("tosca-parser failed: - %(error_msg_details)s")


class HeatTranslatorFailed(exceptions.InvalidInput):
    message = _("heat-translator failed: - %(error_msg_details)s")


class InputValuesMissing(exceptions.InvalidInput):
    message = _("Parameter input values missing for the key '%(key)s'")


class ParamYAMLInputMissing(exceptions.InvalidInput):
    message = _("Parameter YAML input missing")


class HeatClientException(exceptions.TackerException):
    message = _("%(msg)s")


class UserDataFormatNotFound(exceptions.NotFound):
    message = _("user_data and/or user_data_format not provided")


class IPAddrInvalidInput(exceptions.InvalidInput):
    message = _("IP Address input values should be in a list format")


class HugePageSizeInvalidInput(exceptions.InvalidInput):
    message = _("Value specified for mem_page_size is invalid:"
                "%(error_msg_details)s. The valid values are 'small', 'large',"
                "'any' or an integer value in MB")


class CpuAllocationInvalidKeys(exceptions.InvalidInput):
    message = _("Invalid keys specified in VNFD - %(error_msg_details)s."
                "Supported keys are: %(valid_keys)s")


class NumaNodesInvalidKeys(exceptions.InvalidInput):
    message = _("Invalid keys specified in VNFD - %(error_msg_details)s."
                "Supported keys are: %(valid_keys)s")


class FilePathMissing(exceptions.InvalidInput):
    message = _("'file' attribute is missing for "
                "tosca.artifacts.Deployment.Image.VM artifact type")


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


attr.validators['type:service_type_list'] = _validate_service_type_list


RESOURCE_ATTRIBUTE_MAP = {

    'vnfds': {
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

    'vnfs': {
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
        'vnfd_id': {
            'allow_post': True,
            'allow_put': False,
            'validate': {'type:uuid': None},
            'is_visible': True,
        },
        'vim_id': {
            'allow_post': True,
            'allow_put': False,
            'validate': {'type:string': None},
            'is_visible': True,
            'default': '',
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
        'placement_attr': {
            'allow_post': True,
            'allow_put': False,
            'validate': {'type:dict_or_none': None},
            'is_visible': True,
            'default': {},
        },
        'status': {
            'allow_post': False,
            'allow_put': False,
            'is_visible': True,
        },
    },
}


class Vnfm(extensions.ExtensionDescriptor):
    @classmethod
    def get_name(cls):
        return 'VNFM'

    @classmethod
    def get_alias(cls):
        return 'VNF Manager'

    @classmethod
    def get_description(cls):
        return "Extension for VNF Manager"

    @classmethod
    def get_namespace(cls):
        return 'http://wiki.openstack.org/Tacker'

    @classmethod
    def get_updated(cls):
        return "2013-11-19T10:00:00-00:00"

    @classmethod
    def get_resources(cls):
        special_mappings = {}
        plural_mappings = resource_helper.build_plural_mappings(
            special_mappings, RESOURCE_ATTRIBUTE_MAP)
        plural_mappings['service_types'] = 'service_type'
        attr.PLURALS.update(plural_mappings)
        return resource_helper.build_resource_info(
            plural_mappings, RESOURCE_ATTRIBUTE_MAP, constants.VNFM,
            translate_name=True)

    @classmethod
    def get_plugin_interface(cls):
        return VNFMPluginBase

    def update_attributes_map(self, attributes):
        super(Vnfm, self).update_attributes_map(
            attributes, extension_attrs_map=RESOURCE_ATTRIBUTE_MAP)

    def get_extended_resources(self, version):
        version_map = {'1.0': RESOURCE_ATTRIBUTE_MAP}
        return version_map.get(version, {})


@six.add_metaclass(abc.ABCMeta)
class VNFMPluginBase(service_base.NFVPluginBase):
    def get_plugin_name(self):
        return constants.VNFM

    def get_plugin_type(self):
        return constants.VNFM

    def get_plugin_description(self):
        return 'Tacker VNF Manager plugin'

    @abc.abstractmethod
    def create_vnfd(self, context, vnfd):
        pass

    @abc.abstractmethod
    def delete_vnfd(self, context, vnfd_id):
        pass

    @abc.abstractmethod
    def get_vnfd(self, context, vnfd_id, fields=None):
        pass

    @abc.abstractmethod
    def get_vnfds(self, context, filters=None, fields=None):
        pass

    @abc.abstractmethod
    def get_vnfs(self, context, filters=None, fields=None):
        pass

    @abc.abstractmethod
    def get_vnf(self, context, vnf_id, fields=None):
        pass

    @abc.abstractmethod
    def create_vnf(self, context, vnf):
        pass

    @abc.abstractmethod
    def update_vnf(
            self, context, vnf_id, vnf):
        pass

    @abc.abstractmethod
    def delete_vnf(self, context, vnf_id):
        pass
