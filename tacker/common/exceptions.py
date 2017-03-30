# Copyright 2011 VMware, Inc
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

"""
Tacker base exception handling.
"""

from oslo_utils import excutils
import six

from tacker._i18n import _


class TackerException(Exception):
    """Base Tacker Exception.

    To correctly use this class, inherit from it and define
    a 'message' property. That message will get printf'd
    with the keyword arguments provided to the constructor.
    """
    message = _("An unknown exception occurred.")

    def __init__(self, **kwargs):
        try:
            super(TackerException, self).__init__(self.message % kwargs)
            self.msg = self.message % kwargs
        except Exception:
            with excutils.save_and_reraise_exception() as ctxt:
                if not self.use_fatal_exceptions():
                    ctxt.reraise = False
                    # at least get the core message out if something happened
                    super(TackerException, self).__init__(self.message)

    if six.PY2:
        def __unicode__(self):
            return unicode(self.msg)

    def __str__(self):
        return self.msg

    def use_fatal_exceptions(self):
        """Is the instance using fatal exceptions.

        :returns: Always returns False.
        """
        return False


class BadRequest(TackerException):
    message = _('Bad %(resource)s request: %(msg)s')


class NotFound(TackerException):
    pass


class Conflict(TackerException):
    pass


class NotAuthorized(TackerException):
    message = _("Not authorized.")


class ServiceUnavailable(TackerException):
    message = _("The service is unavailable")


class AdminRequired(NotAuthorized):
    message = _("User does not have admin privileges: %(reason)s")


class PolicyNotAuthorized(NotAuthorized):
    message = _("Policy doesn't allow %(action)s to be performed.")


class NetworkNotFound(NotFound):
    message = _("Network %(net_id)s could not be found")


class PolicyFileNotFound(NotFound):
    message = _("Policy configuration policy.json could not be found")


class PolicyInitError(TackerException):
    message = _("Failed to init policy %(policy)s because %(reason)s")


class PolicyCheckError(TackerException):
    message = _("Failed to check policy %(policy)s because %(reason)s")


class StateInvalid(BadRequest):
    message = _("Unsupported port state: %(port_state)s")


class InUse(TackerException):
    message = _("The resource is inuse")


class ResourceExhausted(ServiceUnavailable):
    pass


class MalformedRequestBody(BadRequest):
    message = _("Malformed request body: %(reason)s")


class Invalid(TackerException):
    def __init__(self, message=None):
        self.message = message
        super(Invalid, self).__init__()


class InvalidInput(BadRequest):
    message = _("Invalid input for operation: %(error_message)s.")


class InvalidAllocationPool(BadRequest):
    message = _("The allocation pool %(pool)s is not valid.")


class OverlappingAllocationPools(Conflict):
    message = _("Found overlapping allocation pools:"
                "%(pool_1)s %(pool_2)s for subnet %(subnet_cidr)s.")


class OutOfBoundsAllocationPool(BadRequest):
    message = _("The allocation pool %(pool)s spans "
                "beyond the subnet cidr %(subnet_cidr)s.")


class MacAddressGenerationFailure(ServiceUnavailable):
    message = _("Unable to generate unique mac on network %(net_id)s.")


class IpAddressGenerationFailure(Conflict):
    message = _("No more IP addresses available on network %(net_id)s.")


class BridgeDoesNotExist(TackerException):
    message = _("Bridge %(bridge)s does not exist.")


class PreexistingDeviceFailure(TackerException):
    message = _("Creation failed. %(dev_name)s already exists.")


class SudoRequired(TackerException):
    message = _("Sudo privilege is required to run this command.")


class QuotaResourceUnknown(NotFound):
    message = _("Unknown quota resources %(unknown)s.")


class OverQuota(Conflict):
    message = _("Quota exceeded for resources: %(overs)s")


class QuotaMissingTenant(BadRequest):
    message = _("Tenant-id was missing from Quota request")


class InvalidQuotaValue(Conflict):
    message = _("Change would make usage less than 0 for the following "
                "resources: %(unders)s")


class InvalidSharedSetting(Conflict):
    message = _("Unable to reconfigure sharing settings for network "
                "%(network)s. Multiple tenants are using it")


class InvalidExtensionEnv(BadRequest):
    message = _("Invalid extension environment: %(reason)s")


class ExtensionsNotFound(NotFound):
    message = _("Extensions not found: %(extensions)s")


class InvalidContentType(TackerException):
    message = _("Invalid content type %(content_type)s")


class ExternalIpAddressExhausted(BadRequest):
    message = _("Unable to find any IP address on external "
                "network %(net_id)s.")


class TooManyExternalNetworks(TackerException):
    message = _("More than one external network exists")


class InvalidConfigurationOption(TackerException):
    message = _("An invalid value was provided for %(opt_name)s: "
                "%(opt_value)s")


class GatewayConflictWithAllocationPools(InUse):
    message = _("Gateway ip %(ip_address)s conflicts with "
                "allocation pool %(pool)s")


class GatewayIpInUse(InUse):
    message = _("Current gateway ip %(ip_address)s already in use "
                "by port %(port_id)s. Unable to update.")


class NetworkVlanRangeError(TackerException):
    message = _("Invalid network VLAN range: '%(vlan_range)s' - '%(error)s'")

    def __init__(self, **kwargs):
        # Convert vlan_range tuple to 'start:end' format for display
        if isinstance(kwargs['vlan_range'], tuple):
            kwargs['vlan_range'] = "%d:%d" % kwargs['vlan_range']
        super(NetworkVlanRangeError, self).__init__(**kwargs)


class NetworkVxlanPortRangeError(TackerException):
    message = _("Invalid network VXLAN port range: '%(vxlan_range)s'")


class VxlanNetworkUnsupported(TackerException):
    message = _("VXLAN Network unsupported.")


class DuplicatedExtension(TackerException):
    message = _("Found duplicate extension: %(alias)s")


class DeviceIDNotOwnedByTenant(Conflict):
    message = _("The following device_id %(device_id)s is not owned by your "
                "tenant or matches another tenants router.")


class InvalidCIDR(BadRequest):
    message = _("Invalid CIDR %(input)s given as IP prefix")


class MgmtDriverException(TackerException):
    message = _("VNF configuration failed")


class AlarmUrlInvalid(BadRequest):
    message = _("Invalid alarm url for VNF %(vnf_id)s")


class TriggerNotFound(NotFound):
    message = _("Trigger %(trigger_name)s does not exist for VNF %(vnf_id)s")


class VnfPolicyNotFound(NotFound):
    message = _("Policy %(policy)s does not exist for VNF %(vnf_id)s")


class VnfPolicyActionInvalid(BadRequest):
    message = _("Invalid action %(action)s for policy %(policy)s, "
                "should be one of %(valid_acions)s")


class VnfPolicyTypeInvalid(BadRequest):
    message = _("Invalid type %(type)s for policy %(policy)s, "
                "should be one of %(valid_types)s")


class DuplicateResourceName(TackerException):
    message = _("%(resource)s with name %(name)s already exists")


class DuplicateEntity(TackerException):
    message = _("%(_type)s already exist with given %(entry)s")
