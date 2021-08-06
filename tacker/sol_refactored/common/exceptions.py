# Copyright (C) 2021 Nippon Telegraph and Telephone Corporation
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


class SolException(Exception):
    """Exception for SOL ProblemDetails

    Generally status, title and message should be defined in derived class.
    detail is constructed from message and kwargs.

    Attributes in ProblemDetails can be specified in kwargs of object
    initialization. Use `sol_*` (ex. `sol_instance`) to avoid confliction
    with kwargs.
    """

    status = 500
    title = None
    message = 'Internal Server Error'

    def __init__(self, **kwargs):
        self.status = kwargs.pop('sol_status', self.status)
        self.title = kwargs.pop('sol_title', self.title)
        self.type = kwargs.pop('sol_type', None)
        self.instance = kwargs.pop('sol_instance', None)
        self.detail = kwargs.pop('sol_detail', self.message % kwargs)
        super().__init__(self.detail)

    def make_problem_details(self):
        res = {'status': self.status,
               'detail': self.detail}
        if self.title is not None:
            res['title'] = self.title
        if self.type is not None:
            res['type'] = self.type
        if self.instance is not None:
            res['instance'] = self.instance

        return res


class SolHttpError400(SolException):
    status = 400
    title = 'Bad Request'


class SolHttpError403(SolException):
    status = 403
    title = 'Forbidden'


class SolHttpError404(SolException):
    status = 404
    title = 'Not Found'


class SolHttpError405(SolException):
    status = 405
    title = 'Method Not Allowed'


class SolHttpError406(SolException):
    status = 406
    title = 'Not Acceptable'


class SolHttpError409(SolException):
    status = 409
    title = 'Conflict'


class SolHttpError422(SolException):
    status = 422
    title = 'Unprocessable Entity'


class MethodNotAllowed(SolHttpError405):
    message = _("Method %(method)s is not supported.")


class SolValidationError(SolHttpError400):
    message = _("%(detail)s")


class InvalidAPIVersionString(SolHttpError400):
    message = _("Version String %(version)s is of invalid format. Must "
                "be of format Major.Minor.Patch.")


class APIVersionMissing(SolHttpError400):
    message = _("'Version' HTTP header missing.")


class APIVersionNotSupported(SolHttpError406):
    message = _("Version %(version)s not supported.")


class VnfdIdNotEnabled(SolHttpError422):
    message = _("VnfId %(vnfd_id)s not ENABLED.")


class VnfInstanceNotFound(SolHttpError404):
    message = _("VnfInstance %(inst_id)s not found.")


class VnfInstanceIsInstantiated(SolHttpError409):
    message = _("VnfInstance %(inst_id)s is instantiated.")


class VnfInstanceIsNotInstantiated(SolHttpError409):
    message = _("VnfInstance %(inst_id)s isn't instantiated.")


class SubscriptionNotFound(SolHttpError404):
    message = _("Subscription %(subsc_id)s not found.")


class VnfLcmOpOccNotFound(SolHttpError404):
    message = _("VnfLcmOpOcc %(lcmocc_id)s not found.")


class VnfdIdNotFound(SolHttpError422):
    message = _("VnfPackage of vnfdId %(vnfd_id)s is not found or "
                "not operational.")


class FlavourIdNotFound(SolHttpError400):
    message = _("FlavourId %(flavour_id)s not found in the vnfd.")


class NoVimConnectionInfo(SolHttpError422):
    message = _("No VimConnectionInfo set to the VnfInstance.")


class InvalidVnfdFormat(SolHttpError400):
    message = _("Vnfd is unexpected format.")


class StackOperationFailed(SolHttpError422):
    # title and detail are set in the code from stack_status_reason
    pass


class MgmtDriverExecutionFailed(SolHttpError422):
    title = 'Mgmt driver execution failed'
    # detail set in the code


class BaseHOTNotDefined(SolHttpError400):
    message = _("BaseHOT is not defined.")


class UserdataMissing(SolHttpError400):
    message = _("'lcm-operation-user-data' or "
                "'lcm-operation-user-data-class' missing.")


class UserdataExecutionFailed(SolHttpError422):
    title = 'Userdata execution failed'
    # detail set in the code


class TestNotificationFailed(SolHttpError422):
    message = _("Can't get from notification callback Uri.")


class VimNotFound(SolHttpError404):
    message = _("VIM %(vim_id)s not found.")


class OtherOperationInProgress(SolHttpError409):
    message = _("Other LCM operation of vnfInstance %(inst_id)s "
                "is in progress.")


class UserDataClassNotImplemented(SolHttpError400):
    message = _("Userdata class not implemented.")


class InvalidAttributeFilter(SolHttpError400):
    message = _("Attribute filter expression is invalid.")


class InvalidAttributeSelector(SolHttpError400):
    message = _("Attribute selector expression is invalid.")


class InvalidSubscription(SolHttpError400):
    # detail set in the code
    pass


class ResponseTooBig(SolHttpError400):
    title = 'Response too big'
    message = _("Content length of the response is larger "
                "than %(size)d bytes.")


class LocalNfvoGrantFailed(SolHttpError403):
    title = 'Grant failed'
    # detail set in the code
