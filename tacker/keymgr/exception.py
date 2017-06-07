# Copyright (c) 2015 The Johns Hopkins University/Applied Physics Laboratory
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
Exception for keymgr
"""

from tacker._i18n import _
from tacker.common.exceptions import TackerException


class Forbidden(TackerException):
    message = _("You are not authorized to complete this action.")


class KeyManagerError(TackerException):
    message = _("Key manager error: %(reason)s")


class ManagedObjectNotFoundError(TackerException):
    message = _("Key not found, uuid: %(uuid)s")


class AuthTypeInvalidError(TackerException):
    message = _("Invalid auth_type was specified, auth_type: %(type)s")


class InsufficientCredentialDataError(TackerException):
    message = _('Insufficient credential data was provided, either '
                '"token" must be set in the passed conf, or a context '
                'with an "auth_token" property must be passed.')
