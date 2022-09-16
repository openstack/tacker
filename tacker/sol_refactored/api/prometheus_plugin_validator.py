# Copyright (C) 2022 Fujitsu
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

import functools

from tacker.api.validation import validators
from tacker.common import exceptions as tacker_ex

from tacker.sol_refactored.common import exceptions as sol_ex


class PrometheusPluginSchemaValidator(validators._SchemaValidator):
    def validate(self, *args, **kwargs):
        try:
            super(PrometheusPluginSchemaValidator, self).validate(
                *args, **kwargs)
        except tacker_ex.ValidationError as ex:
            raise sol_ex.PrometheusPluginValidationError(detail=str(ex))


def schema(request_body_schema):
    def add_validator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if 'body' not in kwargs:
                raise sol_ex.PrometheusPluginValidationError(
                    detail="body is missing.")
            schema_validator = PrometheusPluginSchemaValidator(
                request_body_schema)
            schema_validator.validate(kwargs['body'])

            return func(*args, **kwargs)
        return wrapper
    return add_validator
