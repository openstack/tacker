# Copyright (C) 2019 NTT DATA
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
Internal implementation of request Body validating middleware.

"""

import jsonschema
from jsonschema import exceptions as jsonschema_exc
import netaddr
from oslo_utils import uuidutils
import rfc3986
import six
import webob

from tacker.common import exceptions as exception


@jsonschema.FormatChecker.cls_checks('uri')
def _validate_uri(instance):
    uri = rfc3986.uri_reference(instance)
    validator = rfc3986.validators.Validator().require_presence_of(
        'scheme', 'host',
    ).check_validity_of(
        'scheme', 'userinfo', 'host', 'path', 'query', 'fragment',)
    try:
        validator.validate(uri)
    except rfc3986.exceptions.RFC3986Exception:
        return False
    return True


@jsonschema.FormatChecker.cls_checks('uuid')
def _validate_uuid_format(instance):
    return uuidutils.is_uuid_like(instance)


@jsonschema.FormatChecker.cls_checks('mac_address_or_none',
        webob.exc.HTTPBadRequest)
def validate_mac_address_or_none(instance):
    """Validate instance is a MAC address"""

    if instance is None:
        return

    if not netaddr.valid_mac(instance):
        msg = _("'%s' is not a valid mac address")
        raise webob.exc.HTTPBadRequest(explanation=msg % instance)

    return True


def _validate_query_parameter_without_value(parameter_name, instance):
    """The query parameter is a flag without a value."""
    if not (isinstance(instance, six.text_type) and len(instance)):
        return True

    msg = _("The parameter '%s' is a flag. It shouldn't contain any value.")
    raise webob.exc.HTTPBadRequest(explanation=msg % parameter_name)


@jsonschema.FormatChecker.cls_checks('all_fields',
        webob.exc.HTTPBadRequest)
def _validate_all_fields_query_parameter(instance):
    return _validate_query_parameter_without_value('all_fields', instance)


@jsonschema.FormatChecker.cls_checks('exclude_default',
        webob.exc.HTTPBadRequest)
def _validate_exclude_default_query_parameter(instance):
    return _validate_query_parameter_without_value('exclude_default',
            instance)


class FormatChecker(jsonschema.FormatChecker):
    """A FormatChecker can output the message from cause exception

    We need understandable validation errors messages for users. When a
    custom checker has an exception, the FormatChecker will output a
    readable message provided by the checker.
    """

    def check(self, param_value, format):
        """Check whether the param_value conforms to the given format.

        :argument param_value: the param_value to check
        :type: any primitive type (str, number, bool)
        :argument str format: the format that param_value should conform to
        :raises: :exc:`FormatError` if param_value does not conform to format
        """

        if format not in self.checkers:
            return

        # For safety reasons custom checkers can be registered with
        # allowed exception types. Anything else will fall into the
        # default formatter.
        func, raises = self.checkers[format]
        result, cause = None, None

        try:
            result = func(param_value)
        except raises as e:
            cause = e
        if not result:
            msg = "%r is not a %r" % (param_value, format)
            raise jsonschema_exc.FormatError(msg, cause=cause)


class _SchemaValidator(object):
    """A validator class

    This class is changed from Draft7Validator to validate minimum/maximum
    value of a string number(e.g. '10'). This changes can be removed when
    we tighten up the API definition and the XML conversion.
    Also FormatCheckers are added for checking data formats which would be
    passed through cinder api commonly.

    """
    validator_org = jsonschema.Draft7Validator

    def __init__(self, schema):
        validator_cls = jsonschema.validators.extend(self.validator_org,
                                                     validators={})
        format_checker = FormatChecker()
        self.validator = validator_cls(schema, format_checker=format_checker)

    def validate(self, *args, **kwargs):
        try:
            self.validator.validate(*args, **kwargs)
        except jsonschema.ValidationError as ex:
            if isinstance(ex.cause, webob.exc.HTTPBadRequest):
                detail = str(ex.cause)
            elif len(ex.path) > 0:
                detail = _("Invalid input for field/attribute %(path)s."
                           " Value: %(value)s. %(message)s") % {
                    'path': ex.path.pop(), 'value': ex.instance,
                    'message': ex.message
                }
            else:
                detail = ex.message
            raise exception.ValidationError(detail=detail)
        except TypeError as ex:
            # NOTE: If passing non string value to patternProperties parameter,
            #       TypeError happens. Here is for catching the TypeError.
            detail = six.text_type(ex)
            raise exception.ValidationError(detail=detail)
