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

from oslo_log import log as logging
import six

from tacker._i18n import _
from tacker.api import extensions
from tacker.api.v1 import attributes as attr
from tacker.api.v1 import base
from tacker.api.v1 import resource_helper
from tacker.common import exceptions
from tacker import manager
from tacker.plugins.common import constants
from tacker.services import service_base


LOG = logging.getLogger(__name__)


class MultipleMGMTDriversSpecified(exceptions.InvalidInput):
    message = _('More than one MGMT Driver per vnfd is not supported')


class ServiceTypesNotSpecified(exceptions.InvalidInput):
    message = _('service types are not specified')


class VNFDInUse(exceptions.InUse):
    message = _('VNFD %(vnfd_id)s is still in use')


class VNFInUse(exceptions.InUse):
    message = _('VNF %(vnf_id)s is still in use')


class InvalidMgmtDriver(exceptions.InvalidInput):
    message = _('Invalid Mgmt driver %(mgmt_driver_name)s.')


class InvalidInfraDriver(exceptions.InvalidInput):
    message = _('VIM type %(vim_name)s is not supported as an infra driver')


class InvalidAPIAttributeType(exceptions.InvalidInput):
    message = _('Expecting dict type for API attribute instead of %(atype)s ')


class VNFCreateFailed(exceptions.TackerException):
    message = _('creating VNF based on %(vnfd_id)s failed')


class VNFUpdateInvalidInput(exceptions.TackerException):
    message = _('VNF Update Invalid Input %(reason)s')


class VNFUpdateWaitFailed(exceptions.TackerException):
    message = _('VNF Update %(reason)s')


class VNFCreateWaitFailed(exceptions.TackerException):
    message = _('VNF Create %(reason)s')


class VNFScaleWaitFailed(exceptions.TackerException):
    message = _('%(reason)s')


class VNFDeleteWaitFailed(exceptions.TackerException):
    message = _('VNF Delete %(reason)s')


class VNFHealWaitFailed(exceptions.TackerException):
    message = _('VNF Heal %(reason)s')


class VNFDeleteFailed(exceptions.TackerException):
    message = _('%(reason)s')


class VNFHealFailed(exceptions.TackerException):
    message = _('VNF %(vnf_id)s failed to heal')


class VNFDNotFound(exceptions.NotFound):
    message = _('VNFD %(vnfd_id)s could not be found')


class CnfDefinitionNotFound(exceptions.NotFound):
    message = _(
        "CNF definition file with path %(path)s "
        "is not found in vnf_artifacts.")


class CNFCreateWaitFailed(exceptions.TackerException):
    message = _('CNF Create Failed with reason: %(reason)s')


class ServiceTypeNotFound(exceptions.NotFound):
    message = _('service type %(service_type_id)s could not be found')


class VNFNotFound(exceptions.NotFound):
    message = _('VNF %(vnf_id)s could not be found')


class LCMUserDataFailed(exceptions.TackerException):
    message = _('LCM user data %(reason)s')


class ParamYAMLNotWellFormed(exceptions.InvalidInput):
    message = _("Parameter YAML not well formed - %(error_msg_details)s")


class ToscaParserFailed(exceptions.InvalidInput):
    message = _("tosca-parser failed: - %(error_msg_details)s")


class HeatTranslatorFailed(exceptions.InvalidInput):
    message = _("heat-translator failed: - %(error_msg_details)s")


class HeatClientException(exceptions.TackerException):
    message = _("%(msg)s")


class IPAddrInvalidInput(exceptions.InvalidInput):
    message = _("IP Address input values should be in a list format")


class HugePageSizeInvalidInput(exceptions.InvalidInput):
    message = _("Value specified for mem_page_size is invalid: "
                "%(error_msg_details)s. The valid values are 'small', 'large',"
                " 'any' or an integer value in MB")


class CpuAllocationInvalidKeys(exceptions.InvalidInput):
    message = _("Invalid keys specified in VNFD - %(error_msg_details)s."
                "Supported keys are: %(valid_keys)s")


class CpuAllocationInvalidValues(exceptions.InvalidInput):
    message = _("Invalid values specified in VNFD - %(error_msg_details)s."
                "Supported Values are: %(valid_values)s")


class NumaNodesInvalidKeys(exceptions.InvalidInput):
    message = _("Invalid keys specified in VNFD - %(error_msg_details)s."
                "Supported keys are: %(valid_keys)s")


class FilePathMissing(exceptions.InvalidInput):
    message = _("'file' attribute is missing for "
                "tosca.artifacts.Deployment.Image.VM artifact type")


class InfraDriverUnreachable(exceptions.ServiceUnavailable):
    message = _("Could not retrieve VNF resource IDs and"
                " types. Please check %(service)s status.")


class VNFInactive(exceptions.InvalidInput):
    message = _("VNF %(vnf_id)s is not in Active state: %(message)s")


class MetadataNotMatched(exceptions.InvalidInput):
    message = _("Metadata for alarm policy is not matched")


class InvalidResourceType(exceptions.InvalidInput):
    message = _("Resource type %(resource_type)s for alarm policy "
                "is not supported")


class InvalidSubstitutionMapping(exceptions.InvalidInput):
    message = _("Input for substitution mapping requirements are not"
                " valid for %(requirement)s. They must be in the form"
                " of list with two entries")


class SMRequirementMissing(exceptions.InvalidInput):
    message = _("All the requirements for substitution_mappings are not"
                " provided. Missing requirement for %(requirement)s")


class InvalidParamsForSM(exceptions.InvalidInput):
    message = _("Please provide parameters for substitution mappings")


class InvalidKubernetesScalingPolicyNumber(exceptions.InvalidInput):
    message = _("Please provide only one Scaling policy")


class InvalidKubernetesNetworkNumber(exceptions.InvalidInput):
    message = _("Please provide one network for all vdus")


class InvalidKubernetesInputParameter(exceptions.InvalidInput):
    message = _("Found unsupported keys for %(found_keys)s ")


class InvalidInstReqInfoForScaling(exceptions.InvalidInput):
    message = _("Scaling resource cannot be set to "
                "fixed ip_address or mac_address.")


class InvalidMaintenanceParameter(exceptions.InvalidInput):
    message = _("Could not find the required params for maintenance")


def _validate_service_type_list(data, valid_values=None):
    if not isinstance(data, list):
        msg = _("Invalid data format for service list: '%s'") % data
        LOG.debug(msg)
        return msg
    if not data:
        msg = _("Empty list is not allowed for service list. '%s'") % data
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

NAME_MAX_LEN = 255

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
        'service_types': {
            'allow_post': True,
            'allow_put': False,
            'convert_to': attr.convert_to_list,
            'validate': {'type:service_type_list': None},
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
        'template_source': {
            'allow_post': False,
            'allow_put': False,
            'is_visible': True,
            'default': 'onboarded'
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
            'default': None
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
        'instance_id': {
            'allow_post': False,
            'allow_put': False,
            'validate': {'type:string': None},
            'is_visible': True,
        },
        'mgmt_ip_address': {
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
        'error_reason': {
            'allow_post': False,
            'allow_put': False,
            'is_visible': True,
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
        'vnfd_template': {
            'allow_post': True,
            'allow_put': False,
            'validate': {'type:dict_or_none': None},
            'is_visible': True,
            'default': None,
        },
    },
}


SUB_RESOURCE_ATTRIBUTE_MAP = {
    'actions': {
        'parent': {
            'collection_name': 'vnfs',
            'member_name': 'vnf'
        },
        'members': {
            'scale': {
                'parameters': {
                    'policy': {
                        'allow_post': True,
                        'allow_put': False,
                        'is_visible': True,
                        'validate': {'type:string': None}
                    },
                    'type': {
                        'allow_post': True,
                        'allow_put': False,
                        'is_visible': True,
                        'validate': {'type:string': None}
                    },
                    'tenant_id': {
                        'allow_post': True,
                        'allow_put': False,
                        'validate': {'type:string': None},
                        'required_by_policy': False,
                        'is_visible': False
                    },
                }
            },
        }
    },
    'triggers': {
        'parent': {
            'collection_name': 'vnfs',
            'member_name': 'vnf'
        },
        'members': {
            'trigger': {
                'parameters': {
                    'policy_name': {
                        'allow_post': True,
                        'allow_put': False,
                        'is_visible': True,
                        'validate': {'type:string': None}
                    },
                    'action_name': {
                        'allow_post': True,
                        'allow_put': False,
                        'is_visible': True,
                        'validate': {'type:string': None}
                    },
                    'params': {
                        'allow_post': True,
                        'allow_put': False,
                        'is_visible': True,
                        'validate': {'type:dict_or_none': None}
                    },
                    'tenant_id': {
                        'allow_post': True,
                        'allow_put': False,
                        'validate': {'type:string': None},
                        'required_by_policy': False,
                        'is_visible': False
                    }
                }
            },
        }
    },
    'resources': {
        'parent': {
            'collection_name': 'vnfs',
            'member_name': 'vnf'
        },
        'members': {
            'resource': {
                'parameters': {
                    'name': {
                        'allow_post': False,
                        'allow_put': False,
                        'is_visible': True,
                    },
                    'type': {
                        'allow_post': False,
                        'allow_put': False,
                        'is_visible': True,
                    },
                    'id': {
                        'allow_post': False,
                        'allow_put': False,
                        'is_visible': True,
                    },
                }
            }
        }
    },
    'maintenances': {
        'parent': {
            'collection_name': 'vnfs',
            'member_name': 'vnf'
        },
        'members': {
            'maintenance': {
                'parameters': {
                    'params': {
                        'allow_post': True,
                        'allow_put': False,
                        'is_visible': True,
                        'validate': {'type:dict_or_none': None}
                    },
                    'tenant_id': {
                        'allow_post': True,
                        'allow_put': False,
                        'validate': {'type:string': None},
                        'required_by_policy': False,
                        'is_visible': False
                    },
                    'response': {
                        'allow_post': False,
                        'allow_put': False,
                        'validate': {'type:dict_or_none': None},
                        'is_visible': True
                    }
                }
            }
        }
    }
}


class Vnfm(extensions.ExtensionDescriptor):
    @classmethod
    def get_name(cls):
        return 'VNF Manager'

    @classmethod
    def get_alias(cls):
        return 'VNFM'

    @classmethod
    def get_description(cls):
        return "Extension for VNF Manager"

    @classmethod
    def get_namespace(cls):
        return 'https://wiki.openstack.org/Tacker'

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
        resources = resource_helper.build_resource_info(
            plural_mappings, RESOURCE_ATTRIBUTE_MAP, constants.VNFM,
            translate_name=True)
        plugin = manager.TackerManager.get_service_plugins()[
            constants.VNFM]
        for collection_name in SUB_RESOURCE_ATTRIBUTE_MAP:
            parent = SUB_RESOURCE_ATTRIBUTE_MAP[collection_name]['parent']

            for resource_name in SUB_RESOURCE_ATTRIBUTE_MAP[
                    collection_name]['members']:
                params = SUB_RESOURCE_ATTRIBUTE_MAP[
                    collection_name]['members'][resource_name]['parameters']

                controller = base.create_resource(collection_name,
                                                  resource_name,
                                                  plugin, params,
                                                  allow_bulk=True,
                                                  parent=parent)

                resource = extensions.ResourceExtension(
                    collection_name,
                    controller, parent,
                    attr_map=params)
                resources.append(resource)
        return resources

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
    def get_vnf_resources(self, context, vnf_id, fields=None, filters=None):
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

    @abc.abstractmethod
    def create_vnf_scale(
            self, context, vnf_id, scale):
        pass

    @abc.abstractmethod
    def create_vnf_trigger(
            self, context, vnf_id, trigger):
        pass

    @abc.abstractmethod
    def create_vnf_maintenance(self, context, vnf_id, maintenance):
        pass
