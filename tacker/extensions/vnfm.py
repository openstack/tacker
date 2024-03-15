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

from tacker._i18n import _
from tacker.api import extensions
from tacker.api.v1 import attributes as attr
from tacker.api.v1 import resource_helper
from tacker.common import exceptions
from tacker.plugins.common import constants
from tacker.services import service_base


LOG = logging.getLogger(__name__)


class VNFInUse(exceptions.InUse):
    message = _('VNF %(vnf_id)s is still in use')


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


class VNFChangeExtConnWaitFailed(exceptions.TackerException):
    message = _('VNF ChangeExtConn %(reason)s')


class VNFDeleteFailed(exceptions.TackerException):
    message = _('%(reason)s')


class VNFDNotFound(exceptions.NotFound):
    message = _('VNFD %(vnfd_id)s could not be found')


class CnfDefinitionNotFound(exceptions.NotFound):
    message = _(
        "CNF definition file with path %(path)s "
        "is not found in vnf_artifacts.")


class CNFCreateWaitFailed(exceptions.TackerException):
    message = _('CNF Create Failed with reason: %(reason)s')


class CNFScaleFailed(exceptions.TackerException):
    message = _('CNF Scale Failed with reason: %(reason)s')


class CNFScaleWaitFailed(exceptions.TackerException):
    message = _('CNF Scale Wait Failed with reason: %(reason)s')


class CNFHealFailed(exceptions.TackerException):
    message = _('%(reason)s')


class CNFHealWaitFailed(exceptions.TackerException):
    message = _('%(reason)s')


class InvalidVimConnectionInfo(exceptions.TackerException):
    message = _('Invalid vim_connection_info: %(reason)s')


class HelmClientRemoteCommandError(exceptions.TackerException):
    message = _('Failed to execute remote command.')


class HelmClientMissingParamsError(exceptions.TackerException):
    message = _('The specified value %(value)s was not found.')


class HelmClientOtherError(exceptions.TackerException):
    message = _('An error occurred in HelmClient: %(error_message)s.')


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


class InfraDriverUnreachable(exceptions.ServiceUnavailable):
    message = _("Could not retrieve VNF resource IDs and"
                " types. Please check %(service)s status.")


class InvalidSubstitutionMapping(exceptions.InvalidInput):
    message = _("Input for substitution mapping requirements are not"
                " valid for %(requirement)s. They must be in the form"
                " of list with two entries")


class SMRequirementMissing(exceptions.InvalidInput):
    message = _("All the requirements for substitution_mappings are not"
                " provided. Missing requirement for %(requirement)s")


class InvalidParamsForSM(exceptions.InvalidInput):
    message = _("Please provide parameters for substitution mappings")


class InvalidInstReqInfoForScaling(exceptions.InvalidInput):
    message = _("Scaling resource cannot be set to "
                "fixed ip_address or mac_address.")


class OIDCAuthFailed(exceptions.InvalidInput):
    message = _("OIDC authentication and authorization failed."
                " Detail: %(detail)s")


RESOURCE_ATTRIBUTE_MAP = {}


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


class VNFMPluginBase(service_base.NFVPluginBase, metaclass=abc.ABCMeta):
    def get_plugin_name(self):
        return constants.VNFM

    def get_plugin_type(self):
        return constants.VNFM

    def get_plugin_description(self):
        return 'Tacker VNF Manager plugin'

    @abc.abstractmethod
    def get_vnfd(self, context, vnfd_id, fields=None):
        pass

    @abc.abstractmethod
    def get_vnfs(self, context, filters=None, fields=None):
        pass

    @abc.abstractmethod
    def get_vnf(self, context, vnf_id, fields=None):
        pass
