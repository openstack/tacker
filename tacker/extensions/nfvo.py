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


class ToscaParserFailed(exceptions.InvalidInput):
    message = _("tosca-parser failed: - %(error_msg_details)s")


class VnffgdInvalidTemplate(exceptions.InvalidInput):
    message = _("Invalid VNFFG template input: %(template)s")


class VnffgdDuplicateForwarderException(exceptions.InvalidInput):
    message = _("Invalid Forwarding Path contains duplicate forwarder not in "
                "order: %(forwarder)s")


class VnffgdDuplicateCPException(exceptions.InvalidInput):
    message = _("Invalid Forwarding Path contains duplicate connection point "
                ": %(cp)s")


class VnffgdVnfdNotFoundException(exceptions.NotFound):
    message = _("Specified VNFD %(vnfd_name)s in VNFFGD does not exist. "
                "Please create VNFDs before creating VNFFG")


class VnffgdCpNotFoundException(exceptions.NotFound):
    message = _("Specified CP %(cp_id)s could not be found in VNFD "
                "%(vnfd_name)s. Please check VNFD for correct Connection "
                "Point.")


class VnffgdCpNoForwardingException(exceptions.TackerException):
    message = _("Specified CP %(cp_id)s in VNFD %(vnfd_name)s "
                "does not have forwarding capability, which is required to be "
                "included in forwarding path")


class VnffgdWrongEndpointNumber(exceptions.TackerException):
    message = _("Specified number_of_endpoints %(number)s is not equal to "
                "the number of connection_point %(cps)s")


class VnffgdInUse(exceptions.InUse):
    message = _('VNFFGD %(vnffgd_id)s is still in use')


class VnffgdNotFoundException(exceptions.NotFound):
    message = _('VNFFG Template %(vnffgd_id)s could not be found')


class VnffgCreateFailed(exceptions.TackerException):
    message = _('Creating VNFFG based on %(vnffgd_id)s failed')


class VnffgInvalidMappingException(exceptions.TackerException):
    message = _("Matching VNF Instance for VNFD %(vnfd_name)s could not be "
                "found. Please create an instance of this VNFD before "
                "creating/updating VNFFG.")


class VnffgParamValueFormatError(exceptions.TackerException):
    message = _("Param values %(param_value)s is not in dict format.")


class VnffgTemplateParamParsingException(exceptions.TackerException):
    message = _("Failed to parse VNFFG Template due to "
                "missing input param %(get_input)s.")


class VnffgPropertyNotFoundException(exceptions.NotFound):
    message = _('VNFFG Property %(vnffg_property)s could not be found')


class VnffgCpNotFoundException(exceptions.NotFound):
    message = _("Specified CP %(cp_id)s could not be found in VNF "
                "%(vnf_id)s.")


class VnffgNotFoundException(exceptions.NotFound):
    message = _('VNFFG %(vnffg_id)s could not be found')


class VnffgInUse(exceptions.InUse):
    message = _('VNFFG %(vnffg_id)s is still in use')


class VnffgVnfNotFoundException(exceptions.NotFound):
    message = _("Specified VNF instance %(vnf_name)s in VNF Mapping could not "
                "be found")


class VnffgDeleteFailed(exceptions.TackerException):
    message = _('Deleting VNFFG %(vnffg_id)s failed')


class VnffgInUseNS(exceptions.TackerException):
    message = _('VNFFG %(vnffg_id)s belongs to active network service '
                '%(ns_id)s')


class NfpAttributeNotFoundException(exceptions.NotFound):
    message = _('NFP attribute %(attribute)s could not be found')


class NfpNotFoundException(exceptions.NotFound):
    message = _('NFP %(nfp_id)s could not be found')


class NfpInUse(exceptions.InUse):
    message = _('NFP %(nfp_id)s is still in use')


class NfpPolicyCriteriaError(exceptions.PolicyCheckError):
    message = _('%(error)s in policy')


class NfpPolicyCriteriaIndexError(exceptions.TackerException):
    message = _('Criteria list can not be empty')


class NfpDuplicatePolicyCriteria(exceptions.TackerException):
    message = _('The %(first_dict)s and %(sec_dict)s are overlapped')


class NfpDuplicatePathID(exceptions.TackerException):
    message = _('The path_id %(path_id)s is overlapped with '
                'NFP %(nfp_name)s in %(vnffg_name)s')


class NfpPolicyTypeError(exceptions.PolicyCheckError):
    message = _('Unsupported Policy Type: %(type)s')


class NfpForwarderNotFoundException(exceptions.NotFound):
    message = _('VNFD Forwarder %(vnfd)s not found in VNF Mapping %(mapping)s')


class NfpRequirementsException(exceptions.TackerException):
    message = _('VNFD Forwarder %(vnfd)s specified more than twice in '
                'requirements path')


class SfcInUse(exceptions.InUse):
    message = _('SFC %(sfc_id)s is still in use')


class SfcNotFoundException(exceptions.NotFound):
    message = _('Service Function Chain %(sfc_id)s could not be found')


class ClassifierInUse(exceptions.InUse):
    message = _('Classifier %(classifier_id)s is still in use')


class ClassifierNotFoundException(exceptions.NotFound):
    message = _('Classifier %(classifier_id)s could not be found')


class VnfMappingNotFoundException(exceptions.NotFound):
    message = _('VNF mapping not found/defined')


class VnfMappingNotValidException(exceptions.TackerException):
    message = _('The %(vnfd)s is not found in constituent VNFDs')


class NSDInUse(exceptions.InUse):
    message = _('NSD %(nsd_id)s is still in use')


class NSInUse(exceptions.InUse):
    message = _('NS %(ns_id)s is still in use')


class NoTasksException(exceptions.TackerException):
    message = _('No tasks to run for %(action)s on %(resource)s')


class UpdateChainException(exceptions.TackerException):
    message = _("%(message)s")


class CreateChainException(exceptions.TackerException):
    message = _("%(message)s")


class UpdateClassifierException(exceptions.TackerException):
    message = _("%(message)s")


class UpdateVnffgException(exceptions.TackerException):
    message = _("%(message)s")


class FlowClassiferCreationFailed(exceptions.TackerException):
    message = _("%(message)s")


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
    },

    'vnffgds': {
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
        'template': {
            'allow_post': True,
            'allow_put': False,
            'convert_to': attr.convert_none_to_empty_dict,
            'validate': {'type:dict_or_nodata': None},
            'is_visible': True,
            'default': None,
        },
        'template_source': {
            'allow_post': False,
            'allow_put': False,
            'is_visible': True,
            'default': 'onboarded'
        }
    },

    'vnffgs': {
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
        'vnffgd_id': {
            'allow_post': True,
            'allow_put': False,
            'validate': {'type:uuid': None},
            'is_visible': True,
            'default': None
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
        'vnf_mapping': {
            'allow_post': True,
            'allow_put': True,
            'convert_to': attr.convert_none_to_empty_dict,
            'validate': {'type:dict_or_nodata': None},
            'is_visible': True,
            'default': None,
        },
        'attributes': {
            'allow_post': True,
            'allow_put': True,
            'convert_to': attr.convert_none_to_empty_dict,
            'validate': {'type:dict_or_nodata': None},
            'is_visible': True,
            'default': None,
        },
        'symmetrical': {
            'allow_post': True,
            'allow_put': True,
            'is_visible': True,
            'validate': {'type:boolean': None},
            'default': False,
        },
        'forwarding_paths': {
            'allow_post': False,
            'allow_put': False,
            'is_visible': True,
        },
        'status': {
            'allow_post': False,
            'allow_put': False,
            'is_visible': True,
        },
        'vnffgd_template': {
            'allow_post': True,
            'allow_put': True,
            'validate': {'type:dict_or_nodata': None},
            'is_visible': True,
            'default': None,
        },
        'ns_id': {
            'allow_post': True,
            'allow_put': False,
            'is_visible': True,
            'default': None,
        },
    },

    'nfps': {
        'id': {
            'allow_post': False,
            'allow_put': False,
            'validate': {'type:uuid': None},
            'is_visible': True,
            'primary_key': True
        },
        'tenant_id': {
            'allow_post': False,
            'allow_put': False,
            'validate': {'type:string': None},
            'required_by_policy': True,
            'is_visible': True
        },
        'vnffg_id': {
            'allow_post': False,
            'allow_put': False,
            'validate': {'type:uuid': None},
            'is_visible': True,
        },
        'name': {
            'allow_post': False,
            'allow_put': False,
            'validate': {'type:string': None},
            'is_visible': True,
        },
        'classifier_id': {
            'allow_post': False,
            'allow_put': False,
            'validate': {'type:uuid': None},
            'is_visible': True,
        },
        'chain_id': {
            'allow_post': False,
            'allow_put': False,
            'validate': {'type:uuid': None},
            'is_visible': True,
        },
        'path_id': {
            'allow_post': False,
            'allow_put': False,
            'validate': {'type:string': None},
            'is_visible': True,
        },
        'symmetrical': {
            'allow_post': False,
            'allow_put': False,
            'is_visible': True,
            'validate': {'type:boolean': None},
            'default': False,
        },
        'status': {
            'allow_post': False,
            'allow_put': False,
            'is_visible': True,
        },
    },
    'sfcs': {
        'id': {
            'allow_post': False,
            'allow_put': False,
            'validate': {'type:uuid': None},
            'is_visible': True,
            'primary_key': True
        },
        'tenant_id': {
            'allow_post': False,
            'allow_put': False,
            'validate': {'type:string': None},
            'required_by_policy': True,
            'is_visible': True
        },
        'nfp_id': {
            'allow_post': False,
            'allow_put': False,
            'validate': {'type:uuid': None},
            'is_visible': True,
        },
        'instance_id': {
            'allow_post': False,
            'allow_put': False,
            'validate': {'type:uuid': None},
            'is_visible': True,
        },
        'chain': {
            'allow_post': False,
            'allow_put': False,
            'is_visible': True,
        },
        'path_id': {
            'allow_post': False,
            'allow_put': False,
            'is_visible': True,
        },
        'symmetrical': {
            'allow_post': False,
            'allow_put': False,
            'is_visible': True,
            'validate': {'type:boolean': None},
            'default': False,
        },
        'status': {
            'allow_post': False,
            'allow_put': False,
            'is_visible': True,
        },
    },
    'classifiers': {
        'id': {
            'allow_post': False,
            'allow_put': False,
            'validate': {'type:uuid': None},
            'is_visible': True,
            'primary_key': True
        },
        'tenant_id': {
            'allow_post': False,
            'allow_put': False,
            'validate': {'type:string': None},
            'required_by_policy': True,
            'is_visible': True
        },
        'nfp_id': {
            'allow_post': False,
            'allow_put': False,
            'validate': {'type:uuid': None},
            'is_visible': True,
        },
        'instance_id': {
            'allow_post': False,
            'allow_put': False,
            'validate': {'type:uuid': None},
            'is_visible': True,
        },
        'match': {
            'allow_post': False,
            'allow_put': False,
            'is_visible': True,
        },
        'chain_id': {
            'allow_post': False,
            'allow_put': False,
            'is_visible': True,
        },
        'status': {
            'allow_post': False,
            'allow_put': False,
            'is_visible': True,
        },
        'name': {
            'allow_post': True,
            'allow_put': True,
            'validate': {'type:string': NAME_MAX_LEN},
            'is_visible': True,
        },
    },

    'nsds': {
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
        'attributes': {
            'allow_post': True,
            'allow_put': False,
            'convert_to': attr.convert_none_to_empty_dict,
            'validate': {'type:dict_or_nodata': None},
            'is_visible': True,
            'default': None,
        },
        'template_source': {
            'allow_post': False,
            'allow_put': False,
            'is_visible': True,
            'default': 'onboarded'
        },

    },

    'nss': {
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
            'validate': {'type:string': NAME_MAX_LEN},
            'is_visible': True,
            'default': '',
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
        'vnf_ids': {
            'allow_post': True,
            'allow_put': False,
            'validate': {'type:string': None},
            'is_visible': True,
            'default': '',
        },
        'vnffg_ids': {
            'allow_post': True,
            'allow_put': False,
            'validate': {'type:string': None},
            'is_visible': True,
            'default': '',
        },
        'nsd_id': {
            'allow_post': True,
            'allow_put': False,
            'validate': {'type:uuid': None},
            'is_visible': True,
            'default': None,
        },
        'placement_attr': {
            'allow_post': True,
            'allow_put': False,
            'validate': {'type:dict_or_none': None},
            'is_visible': True,
            'default': {},
        },
        'vim_id': {
            'allow_post': True,
            'allow_put': False,
            'validate': {'type:string': None},
            'is_visible': True,
            'default': '',
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
        'attributes': {
            'allow_post': True,
            'allow_put': False,
            'convert_to': attr.convert_none_to_empty_dict,
            'validate': {'type:dict_or_nodata': None},
            'is_visible': True,
            'default': None,
        },
        'mgmt_ip_addresses': {
            'allow_post': False,
            'allow_put': False,
            'convert_to': attr.convert_none_to_empty_dict,
            'validate': {'type:dict_or_nodata': None},
            'is_visible': True,
        },
        'nsd_template': {
            'allow_post': True,
            'allow_put': False,
            'validate': {'type:dict_or_nodata': None},
            'is_visible': True,
            'default': None,
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


@six.add_metaclass(abc.ABCMeta)
class NFVOPluginBase(service_base.NFVPluginBase):
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

    def get_vim_by_name(self, context, vim_name, fields=None,
                        mask_password=True):
        raise NotImplementedError()

    def get_default_vim(self, context):
        pass
