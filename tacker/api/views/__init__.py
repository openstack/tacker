# Copyright (C) 2020 NTT DATA
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


from tacker.api.common import attribute_filter
from tacker.common import exceptions as exception


class BaseViewBuilder(object):

    @classmethod
    def validate_filter(cls, filters=None):
        if not filters:
            return

        return attribute_filter.parse_filter_rule(filters,
            target=cls.FLATTEN_ATTRIBUTES)

    @classmethod
    def validate_attribute_fields(cls, all_fields=None, fields=None,
            exclude_fields=None, exclude_default=None):

        if all_fields and (fields or exclude_fields or exclude_default):
            msg = ("Invalid query parameter combination: 'all_fields' "
                   "cannot be combined with 'fields' or 'exclude_fields' "
                   "or 'exclude_default'")
            raise exception.ValidationError(msg)

        if fields and (all_fields or exclude_fields):
            msg = ("Invalid query parameter combination: 'fields' "
                   "cannot be combined with 'all_fields' or 'exclude_fields' ")
            raise exception.ValidationError(msg)

        if exclude_fields and (all_fields or fields or exclude_default):
            msg = ("Invalid query parameter combination: 'exclude_fields' "
                   "cannot be combined with 'all_fields' or 'fields' "
                   "or 'exclude_default'")
            raise exception.ValidationError(msg)

        if exclude_default and (all_fields or exclude_fields):
            msg = ("Invalid query parameter combination: 'exclude_default' "
                   "cannot be combined with 'all_fields' or 'exclude_fields' ")
            raise exception.ValidationError(msg)

        def _validate_complex_attributes(query_parameter, fields):
            msg = ("Invalid query parameter '%(query_parameter)s'. "
                   "Value: %(field)s")
            for field in fields:
                if field in cls.COMPLEX_ATTRIBUTES:
                    continue
                elif '*' in field:
                    # Field should never contain '*' as it's reserved for
                    # special purpose for handling key-value pairs.
                    raise exception.ValidationError(msg %
                        {"query_parameter": query_parameter,
                         "field": field})
                elif field not in cls.FLATTEN_COMPLEX_ATTRIBUTES:
                    # Special case for field with key-value pairs.
                    # In this particular case, key will act as an attribute
                    # in structure so you need to treat it differently than
                    # other fields. All key-value pair field will be post-fix
                    # with '*' in FLATTEN_COMPLEX_ATTRIBUTES. Request
                    # with field which contains '*' will be treated as an
                    # error.
                    special_field = False
                    for attribute in cls.FLATTEN_COMPLEX_ATTRIBUTES:
                        if '*' in attribute and field.startswith(
                                attribute.split('*')[0]):
                            special_field = True

                    if not special_field:
                        raise exception.ValidationError(msg %
                            {"query_parameter": query_parameter,
                             "field": field})

        if fields:
            _validate_complex_attributes("fields", fields.split(','))
        elif exclude_fields:
            _validate_complex_attributes("exclude_fields",
                    exclude_fields.split(","))
