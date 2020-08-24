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

from oslo_log import log as logging
import webob.exc
from webob import util as woutil

from tacker._i18n import _


LOG = logging.getLogger(__name__)


class ConvertedException(webob.exc.WSGIHTTPException):
    def __init__(self, code, title="", explanation=""):
        self.code = code
        # There is a strict rule about constructing status line for HTTP:
        # '...Status-Line, consisting of the protocol version followed by a
        # numeric status code and its associated textual phrase, with each
        # element separated by SP characters'
        # (http://www.faqs.org/rfcs/rfc2616.html)
        # 'code' and 'title' can not be empty because they correspond
        # to numeric status code and its associated text
        if title:
            self.title = title
        else:
            try:
                self.title = woutil.status_reasons[self.code]
            except KeyError:
                msg = _("Improper or unknown HTTP status code used: %d")
                LOG.error(msg, code)
                self.title = woutil.status_generic_reasons[self.code // 100]
        self.explanation = explanation
        super(ConvertedException, self).__init__()


class TackerException(Exception):
    """Base Tacker Exception.

    To correctly use this class, inherit from it and define
    a 'message' property. That message will get printf'd
    with the keyword arguments provided to the constructor.
    """
    message = _("An unknown exception occurred.")
    code = 500

    def __init__(self, message=None, **kwargs):
        if not message:
            try:
                message = self.message % kwargs
            except Exception:
                message = self.message

        self.msg = message
        super(TackerException, self).__init__(message)

    def __str__(self):
        return self.msg

    def format_message(self):
        return self.args[0]

    def use_fatal_exceptions(self):
        """Is the instance using fatal exceptions.

        :returns: Always returns False.
        """
        return False


class BadRequest(TackerException):
    message = _('Bad %(resource)s request: %(msg)s')
    code = 400


class NotFound(TackerException):
    message = _('%(resource)s %(name)s not Found')


class Conflict(TackerException):
    pass


class NotAuthorized(TackerException):
    message = _("Not authorized.")
    code = 401


class Forbidden(TackerException):
    msg_fmt = _("Forbidden")
    code = 403


class ServiceUnavailable(TackerException):
    message = _("The service is unavailable")


class AdminRequired(NotAuthorized):
    message = _("User does not have admin privileges: %(reason)s")


class PolicyNotAuthorized(Forbidden):
    message = _("Policy doesn't allow %(action)s to be performed.")


class PolicyInitError(TackerException):
    message = _("Failed to init policy %(policy)s because %(reason)s")


class PolicyCheckError(TackerException):
    message = _("Failed to check policy %(policy)s because %(reason)s")


class InUse(TackerException):
    message = _("The resource is in use")


class MalformedRequestBody(BadRequest):
    message = _("Malformed request body: %(reason)s")


class Invalid(TackerException):
    message = _("Bad Request - Invalid Parameters")


class CreateApiFalse(TackerException):
    message = _('Failed to create resource.')


class InitApiFalse(TackerException):
    message = _('Failed to init resource.')


class ReadEndpoindsFalse(TackerException):
    message = _('The method to read a resource failed.')


class InvalidInput(BadRequest):
    message = _("Invalid input for operation: %(error_message)s.")


class InvalidContentType(TackerException):
    message = _("Invalid content type %(content_type)s")


class NetworkVlanRangeError(TackerException):
    message = _("Invalid network VLAN range: '%(vlan_range)s' - '%(error)s'")

    def __init__(self, **kwargs):
        # Convert vlan_range tuple to 'start:end' format for display
        if isinstance(kwargs['vlan_range'], tuple):
            kwargs['vlan_range'] = "%d:%d" % kwargs['vlan_range']
        super(NetworkVlanRangeError, self).__init__(**kwargs)


class DuplicatedExtension(TackerException):
    message = _("Found duplicate extension: %(alias)s")


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
                "should be one of %(valid_actions)s")


class VnfPolicyTypeInvalid(BadRequest):
    message = _("Invalid type %(type)s for policy %(policy)s, "
                "should be one of %(valid_types)s")


class DuplicateResourceName(TackerException):
    message = _("%(resource)s with name %(name)s already exists")


class DuplicateEntity(Conflict):
    message = _("%(_type)s already exist with given %(entry)s")


class ValidationError(BadRequest):
    message = "%(detail)s"


class ObjectActionError(TackerException):
    message = _("Object action %(action)s failed because: %(reason)s")


class VnfPackageNotFound(NotFound):
    message = _("No vnf package with id %(id)s.")


class VnfPackageVnfdIdDuplicate(TackerException):
    message = _("Vnf package with vnfd id %(vnfd_id)s already exists.")


class VnfInstanceNotFound(NotFound):
    message = _("No vnf instance with id %(id)s.")


class VnfInstanceConflictState(Conflict):
    message = _("Vnf instance %(uuid)s in %(attr)s %(state)s. Cannot "
                "%(action)s while the vnf instance is in this state.")


class VnfConflictState(Conflict):
    message = _("Vnf %(uuid)s in %(attr)s %(state)s. Cannot "
                "%(action)s while the vnf is in this state.")


class FlavourNotFound(NotFound):
    message = _("No flavour with id '%(flavour_id)s'.")


class InstantiationLevelNotFound(NotFound):
    message = _("No instantiation level with id '%(inst_level_id)s'.")


class VimConnectionNotFound(NotFound):
    message = _("No vim found with id '%(vim_id)s'.")


class VnfResourceNotFound(NotFound):
    message = _("No vnf resource with id %(id)s.")


class VnfPackageVnfdNotFound(NotFound):
    message = _("No vnf package vnfd with vnfd_id %(id)s.")


class VnfDeploymentFlavourNotFound(NotFound):
    message = _("No vnf deployment flavour with id %(id)s.")


class VnfSoftwareImageNotFound(NotFound):
    message = _("No vnf software image  with id %(id)s.")


class VnfArtifactNotFound(NotFound):
    message = _("No vnf artifact with id %(id)s.")


class VnfInstantiatedInfoNotFound(NotFound):
    message = _("No vnf instantiated info for vnf id %(vnf_instance_id)s.")


class VnfInstantiationFailed(TackerException):
    message = _("Vnf instantiation failed for vnf %(id)s, error: %(error)s")


class VnfInstantiationWaitFailed(TackerException):
    message = _("Vnf instantiation wait failed for vnf %(id)s, "
                "error: %(error)s")


class VnfPreInstantiationFailed(TackerException):
    message = _("Vnf '%(id)s' failed during pre-instantiation due to error: "
                "%(error)s")


class VnfHealFailed(TackerException):
    message = _("Heal Vnf failed for vnf %(id)s, error: %(error)s")


class LockCreationFailed(TackerException):
    message = _('Unable to create lock. Coordination backend not started.')


class OrphanedObjectError(TackerException):
    msg_fmt = _('Cannot call %(method)s on orphaned %(objtype)s object')


class CSARFileSizeLimitExceeded(TackerException):
    message = _("The provided CSAR file is too large.")


class VNFPackageURLInvalid(Invalid):
    message = _("Failed to open URL %(url)s")


class VnfPackageLocationInvalid(Invalid):
    message = _("Failed to find location: %(location)s")


class InvalidZipFile(Invalid):
    message = _("Invalid zip file : %(path)s")


class UploadFailedToGlanceStore(Invalid):
    message = _("Failed to upload vnf package %(uuid)s to glance store: "
                "%(error)s")


class FailedToGetVnfdData(Invalid):
    message = _("Failed to get csar zip file from glance store: %(error)s")


class FailedToGetVnfArtifact(Invalid):
    message = _("Failed to get artifact file from glance store: %(error)s")


class FailedToGetVnfPackageDetails(Invalid):
    message = _("Failed to get vnf package details: %(error)s")


class InvalidCSAR(Invalid):
    message = _("Invalid csar: %(error)s")


class LimitExceeded(TackerException):
    message = _("The request returned a 413 Request Entity Too Large. This "
                "generally means that rate limiting or a quota threshold was "
                "breached.\n\nThe response body:\n%(body)s")

    def __init__(self, *args, **kwargs):
        self.retry_after = (int(kwargs['retry']) if kwargs.get('retry')
                            else None)
        super(LimitExceeded, self).__init__(*args, **kwargs)


class NotificationProcessingError(TackerException):
    message = _("Notification Processing Failed: %(error)s")


class UserDataUpdateCreateFailed(TackerException):
    msg_fmt = _("User data for VNF package  %(id)s cannot be updated "
                "or created after %(retries)d retries.")


class DBAccessError(TackerException):
    message = _("DB Access Error")


class SeeOther(TackerException):
    code = 303
