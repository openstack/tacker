# -*- coding: utf-8 -*-
#
# Copyright (c) 2020 OpenStack Foundation.
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

from oslo_utils import strutils
from oslo_utils import timeutils
from oslo_utils import uuidutils
import six

from tacker.common import exceptions as exception


registered_filters = {}
SUPPORTED_OP_ONE = ['eq', 'neq', 'gt', 'lt', 'gte', 'lte']
SUPPORTED_OP_MULTI = ['in', 'nin', 'cont', 'ncont']


@six.add_metaclass(abc.ABCMeta)
class BaseFilter(object):
    """Abstract base class for Filter classes."""

    @abc.abstractmethod
    def __str__(self):
        """String representation of the filter tree rooted at this node."""

        pass

    @abc.abstractmethod
    def __call__(self, target):
        """Triggers if instance of the class is called.

        Performs the checks against operators, attribute and datatype
        of the value. Raises exception if it's invalid and finally attribute
        is mapped to the database model that's present in the target dict.
        """

        pass


class Filter(BaseFilter):
    SUPPORTED_OPERATORS = None

    FILTER_OPERATOR_SPEC_MAPPING = {
        'eq': '==',
        'neq': '!=',
        'in': 'in',
        'nin': 'not_in',
        'gt': '>',
        'gte': '>=',
        'lt': '<',
        'lte': '<=',
        'cont': 'in',
        'ncont': 'not_in'
    }

    OPERATOR_SUPPORTED_DATA_TYPES = {
        'eq': ['string', 'number', 'enum', 'boolean', 'key_value_pair'],
        'neq': ['string', 'number', 'enum', 'boolean', 'key_value_pair'],
        'in': ['string', 'number', 'enum', 'key_value_pair'],
        'nin': ['string', 'number', 'enum', 'key_value_pair'],
        'gt': ['string', 'number', 'datetime', 'key_value_pair'],
        'gte': ['string', 'number', 'datetime', 'key_value_pair'],
        'lt': ['string', 'number', 'datetime', 'key_value_pair'],
        'lte': ['string', 'number', 'datetime', 'key_value_pair'],
        'cont': ['string', 'key_value_pair'],
        'ncont': ['string', 'key_value_pair'],
    }

    def __init__(self, operator, attribute, values):
        self.operator = operator
        self.attribute = attribute
        self.values = values

    def __str__(self):
        """Return a string representation of this filter."""

        return '%s,%s,%s' % (self.operator, self.attribute,
            ",".join(self.values))

    def _attribute_special_field(self, target):
        """Check if an attribute is a special field in the target

        Look for attributes in the target that ends with '*' as
        these are special attributes whose type could be 'key_value'
        which requires special treatment. For example
        if attribute in target is 'userDefinedData/*' and if self.attribute
        is userDefinedData/key1, then it's valid even though there is no
        exact match in the target because key/value pair values are
        dynamic.
        """
        special_attributes = [attribute for attribute in target.keys() if '*'
            in attribute]

        for attribute in special_attributes:
            field = attribute.split('*')[0]
            if self.attribute.startswith(field):
                return attribute

    def _validate_operators(self):
        if not self.operator:
            msg = ("Rule '%(rule)s' cannot contain operator")
            raise exception.ValidationError(msg % {"rule": self})

        if self.SUPPORTED_OPERATORS and self.operator not in \
                self.SUPPORTED_OPERATORS:
            msg = ("Rule '%(rule)s' contains invalid operator "
                   "'%(operator)s'")
            raise exception.ValidationError(msg % {"rule": self,
                "operator": self.operator})

    def _validate_attribute_name(self, target):
        if not self.attribute:
            msg = ("Rule '%(rule)s' doesn't contain attribute name")
            raise exception.ValidationError(msg % {"rule": self})

        if '*' in self.attribute:
            msg = ("Rule '%(rule)s' contains invalid attribute name "
                   "'%(attribute)s'")
            raise exception.ValidationError(msg % {"rule": self,
                "attribute": self.attribute})

        if target and self.attribute not in target:
            if not self._attribute_special_field(target):
                msg = ("Rule '%(rule)s' contains invalid attribute name "
                       "'%(attribute)s'")
                raise exception.ValidationError(msg % {"rule": self,
                    "attribute": self.attribute})

    def _handle_string(self, value):
        if value[0] == "'" and value[-1] == "'":
            value = value.strip("'")
            # The logic below enforces single quotes to be in pairs.
            # Raises exception otherwise. It also replaces a pair of
            # single quotes with one single quote.
            # NFV_SOL013 Section 5.2.2
            num_quotes = value.count("'")
            value = value.replace("''", "'")
            if (value.count("'") * 2) != num_quotes:
                msg = ("Rule '%(rule)s' value doesn't have single "
                       "quotes in pairs")
                raise exception.ValidationError(msg % {"rule": self})
        elif any(c in value for c in [",", ")", "'"]):
            msg = ("Rule '%(rule)s' value must be enclosed in "
                   "single quotes when it contains either of "
                   "comma, single quote, closing bracket")
            raise exception.ValidationError(msg % {"rule": self})
        return value

    def _handle_values(self, target):
        special_attribute = self._attribute_special_field(target)
        if special_attribute:
            attribute_info = target.get(special_attribute)
        else:
            attribute_info = target.get(self.attribute)

        if attribute_info[1] in ['string', 'key_value_pair']:
            values = [self._handle_string(v) for v in self.values]
            self.values = values

    def _validate_data_type(self, target):
        if not self.values:
            msg = ("Rule '%(rule)s' contains empty value")
            raise exception.ValidationError(msg % {"rule": self})

        special_attribute = self._attribute_special_field(target)
        if special_attribute:
            attribute_info = target.get(special_attribute)
        else:
            attribute_info = target.get(self.attribute)

        for value in self.values:
            error = False
            if attribute_info[1] == 'string' and not isinstance(value,
                    six.string_types):
                error = True
            elif attribute_info[1] == 'number':
                if not strutils.is_int_like(value):
                    error = True
            elif attribute_info[1] == 'uuid':
                if not uuidutils.is_uuid_like(value):
                    error = True
            elif attribute_info[1] == 'datetime':
                try:
                    timeutils.parse_isotime(value)
                except ValueError:
                    error = True
            elif attribute_info[1] == 'enum':
                if value not in attribute_info[3]:
                    msg = ("Rule '%(rule)s' contains data type '%(type)s' "
                           "with invalid value. It should be one of "
                           "%(valid_value)s")
                    raise exception.ValidationError(msg % {"rule": self,
                        "valid_value": ",".join(attribute_info[3]),
                        'type': attribute_info[1]})

            if error:
                msg = ("Rule '%(rule)s' contains invalid data type for value "
                       "'%(value)s'. The data type should be '%(type)s'")
                raise exception.ValidationError(msg % {"rule": self,
                    "value": value,
                    'type': attribute_info[1]})

            # Also, check whether the data type is supported by operator
            if attribute_info[1] not in \
                    self.OPERATOR_SUPPORTED_DATA_TYPES.get(self.operator):
                msg = ("Rule '%(rule)s' contains operator '%(operator)s' "
                       "which doesn't support data type '%(type)s' for "
                       "attribute '%(attribute)s'")
                raise exception.ValidationError(msg % {"rule": self,
                                "operator": self.operator,
                                'type': attribute_info[1],
                                'attribute': self.attribute})

    def generate_expression(self, target, multiple_values=False):
        special_attribute = self._attribute_special_field(target)
        if special_attribute:
            attribute_info = target.get(special_attribute)
        else:
            attribute_info = target.get(self.attribute)

        attributes = attribute_info[0].split('.')
        key_token = self.attribute.split('/')[-1]
        if attribute_info[1] == 'key_value_pair':
            filter_spec = []
            expression_key = {'field': attribute_info[2]['key_column'],
                'model': attribute_info[2]['model'],
                'value': key_token,
                'op': self.FILTER_OPERATOR_SPEC_MAPPING.get(self.operator)}
            expression_value = {'field': attribute_info[2]['value_column'],
                'model': attribute_info[2]['model'],
                'value': self.values if multiple_values else self.values[0],
                'op': self.FILTER_OPERATOR_SPEC_MAPPING.get(self.operator)}
            filter_spec.append(expression_key)
            filter_spec.append(expression_value)
            expression = {'and': filter_spec}
        else:
            expression = {'field': attributes[-1],
                'model': attribute_info[2],
                'value': self.values if multiple_values else self.values[0],
                'op': self.FILTER_OPERATOR_SPEC_MAPPING.get(self.operator)}

        return expression


class AndFilter(BaseFilter):
    def __init__(self, filter_rule):
        self.filter_rules = filter_rule

    def __str__(self):
        """Return a string representation of this filter."""

        return '(%s)' % ' and '.join(str(r) for r in self.filter_rules)

    def __call__(self, target):
        """Run through this filter and maps it to the database model

        :returns
            A dict containing list of filter-specs required by
            sqlalchemy-filter.
        Example::

        filter=(eq,onboardingState,'onboarded');(eq,softwareImages/size, 10)

        Result would be:
        {
          'and': [
              {
                  'field': 'onboarding_state', 'model': 'Foo',
                  'value': "'onboarded'", 'op': '=='
              },
              {
                 'field': 'size', 'model': 'Foo',
                 'value': '10', 'op': '=='
              }
          ]
        }
        """
        filter_spec = []
        for filter_rule in self.filter_rules:
            result = filter_rule(target)
            filter_spec.append(result)

        return {'and': filter_spec}

    def add_filter_rule(self, filter_rule):
        """Adds filter rule to be tested.

        Allows addition of another filter rule to the list of filter rules
        that will be tested.

        :returns: self
        :rtype: :class:`.AndFilter`
        """

        self.filter_rules.append(filter_rule)
        return self


def register(name, func=None):
    # Perform the actual decoration by registering the function or
    # class.  Returns the function or class for compliance with the
    # decorator interface.
    def decorator(func):
        registered_filters[name] = func
        return func

    # If the function or class is given, do the registration
    if func:
        return decorator(func)

    return decorator


@register('simple_filter_expr_one')
class SimpleFilterExprOne(Filter):

    SUPPORTED_OPERATORS = SUPPORTED_OP_ONE

    def __call__(self, target):
        """Run through this filter and maps it to the database model

        :returns
            A dict containing list of filter-specs required by
            sqlalchemy-filter.
        Example::
        operator=eq, attribute=onBoardingState, and value='onboarded', then
        it would be mapped to following expression.
            {
                'field': 'onboarding_state', -> Mapped to the version field
                'model': 'Foo', -> Mapped to database model
                'value': "onboarded", -> Value to be used for filtering
                                         records
                'op': '==', -> Operator for comparison
            },
        """

        self._validate_operators()
        self._validate_attribute_name(target)
        self._validate_data_type(target)
        self._handle_values(target)

        return self.generate_expression(target, multiple_values=False)

    def _validate_operators(self):
        super(SimpleFilterExprOne, self)._validate_operators()
        if self.values and isinstance(self.values, list) and \
                len(self.values) > 1:
            msg = _("Rule '%(rule)s' contains operator '%(operator)s' "
                    "which supports only one value, but multiple values "
                    "'%(values)s' are provided")
            raise exception.ValidationError(msg % {"rule": self,
                            "operator": self.operator,
                            'values': ",".join(self.values)})


@register('simple_filter_expr_multi')
class SimpleFilterExprMulti(Filter):

    SUPPORTED_OPERATORS = SUPPORTED_OP_MULTI

    def __call__(self, target):
        """Run through this filter and maps it to the database model

        This filter is exactly same as SimpleFilterExprOne, except
        it supports different operators like 'in'|'nin'|'cont'|'ncont'
        which contains more than one value in the list.

        :returns
            A dict containing list of filter-specs required by
            sqlalchemy-filter.
        Example::
        operator=in, attribute=softwareImages/size, and value=[10,20]',
        then it would be mapped to following expression.
            {
                'field': 'size', -> Mapped to the version field
                'model': 'Foo', -> Mapped to database model
                'value': [10,20], -> Value to be used for filtering
                                     records
                'op': 'in', -> Attribute equal to one of the values in the
                               list ("in set" relationship)
            },
        """
        self._validate_operators()
        self._validate_attribute_name(target)
        self._validate_data_type(target)
        self._handle_values(target)

        return self.generate_expression(target, multiple_values=True)
