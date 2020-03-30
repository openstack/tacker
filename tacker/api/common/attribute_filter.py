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

import re
import six

from tacker.api.common import _filters
from tacker.common import exceptions as exception


def reducer(*tokens):
    """Decorator for reduction methods.

    Arguments are a sequence of tokens, in order, which should trigger running
    this reduction method.
    """

    def decorator(func):
        # Make sure we have a list of reducer sequences
        if not hasattr(func, 'reducers'):
            func.reducers = []

        # Add the tokens to the list of reducer sequences
        func.reducers.append(list(tokens))

        return func

    return decorator


class ParseStateMeta(type):
    """Metaclass for the :class:`.ParseState` class.

    Facilitates identifying reduction methods.
    """

    def __new__(mcs, name, bases, cls_dict):
        """Create the class.

        Injects the 'reducers' list, a list of tuples matching token sequences
        to the names of the corresponding reduction methods.
        """

        reducers = []

        for key, value in cls_dict.items():
            if not hasattr(value, 'reducers'):
                continue
            for reduction in value.reducers:
                reducers.append((reduction, key))

        cls_dict['reducers'] = reducers

        return super(ParseStateMeta, mcs).__new__(mcs, name, bases, cls_dict)


@six.add_metaclass(ParseStateMeta)
class ParseState(object):
    """Implement the core of parsing the policy language.

    Uses a greedy reduction algorithm to reduce a sequence of tokens into
    a single terminal, the value of which will be the root of the
    :class:`Filter` tree.

    .. note::

        Error reporting is rather lacking.  The best we can get with this
        parser formulation is an overall "parse failed" error. Fortunately, the
        policy language is simple enough that this shouldn't be that big a
        problem.
    """

    def __init__(self):
        """Initialize the ParseState."""

        self.tokens = []
        self.values = []

    def reduce(self):
        """Perform a greedy reduction of the token stream.

        If a reducer method matches, it will be executed, then the
        :meth:`reduce` method will be called recursively to search for any more
        possible reductions.
        """

        for reduction, methname in self.reducers:
            if (len(self.tokens) >= len(reduction) and
                    self.tokens[-len(reduction):] == reduction):
                # Get the reduction method
                meth = getattr(self, methname)

                # Reduce the token stream
                results = meth(*self.values[-len(reduction):])

                # Update the tokens and values
                self.tokens[-len(reduction):] = [r[0] for r in results]
                self.values[-len(reduction):] = [r[1] for r in results]

                # Check for any more reductions
                return self.reduce()

    def shift(self, tok, value):
        """Adds one more token to the state.

        Calls :meth:`reduce`.
        """

        self.tokens.append(tok)
        self.values.append(value)

        # Do a greedy reduce...
        self.reduce()

    @property
    def result(self):
        """Obtain the final result of the parse.

        :raises ValueError: If the parse failed to reduce to a single result.
        """

        if len(self.values) != 1:
            raise ValueError('Could not parse rule')
        return self.values[0]

    @reducer('(', 'filter', ')')
    @reducer('(', 'and_expr', ')')
    def _wrap_check(self, _p1, filter_data, _p2):
        """Turn parenthesized expressions into a 'filter' token."""

        return [('filter', filter_data)]

    @reducer('filter', 'and', 'filter')
    def _make_and_expr(self, filter_data1, _and, filter_data2):
        """Create an 'and_expr'.

        Join two filters by the 'and' operator.
        """
        return [('and_expr', _filters.AndFilter([filter_data1, filter_data2]))]

    @reducer('and_expr', 'and', 'filter')
    def _extend_and_expr(self, and_expr, _and, filter_data):
        """Extend an 'and_expr' by adding one more filter."""

        return [('and_expr', and_expr.add_filter_rule(filter_data))]


def _parse_filter(filter_rule):
    """Parse a filter rule and return an appropriate Filter object."""

    try:
        tokens = filter_rule.split(',')
        filter_type = None
        if len(tokens) >= 3:
            if tokens[0] in _filters.SUPPORTED_OP_ONE:
                filter_type = 'simple_filter_expr_one'
            elif tokens[0] in _filters.SUPPORTED_OP_MULTI:
                filter_type = 'simple_filter_expr_multi'
    except Exception:
        msg = 'Failed to understand filter %s' % filter_rule
        raise exception.ValidationError(msg)

    if filter_type in _filters.registered_filters:
        return _filters.registered_filters[filter_type](tokens[0],
            tokens[1], tokens[2:])
    else:
        msg = 'Failed to understand filter %s' % filter_rule
        raise exception.ValidationError(msg)


# Used for tokenizing the policy language
_tokenize_re = re.compile(r'\;+')


def _parse_tokenize(filter_rule):
    """Tokenizer for the attribute filtering language.

    Most of the single-character tokens are specified in the
    _tokenize_re; however, parentheses need to be handled specially,
    because they can appear inside a check string.  Thankfully, those
    parentheses that appear inside a check string can never occur at
    the very beginning or end ("%(variable)s" is the correct syntax).
    """
    main_tokens = _tokenize_re.split(filter_rule)
    index = 0
    for tok in main_tokens:
        # Skip empty tokens
        if not tok or tok.isspace():
            continue

        # Handle leading parens on the token
        clean = tok.lstrip('(')
        for i in range(len(tok) - len(clean)):
            yield '(', '('

        # If it was only parentheses, continue
        if not clean:
            continue
        else:
            tok = clean

        # Handle trailing parens on the token
        clean = tok.rstrip(')')
        trail = len(tok) - len(clean)

        # Yield the cleaned token
        lowered = clean.lower()
        if lowered in (';', 'and'):
            # Special tokens
            yield lowered, clean
        elif clean:
            # Not a special token, but not composed solely of ')'
            if len(tok) >= 2 and ((tok[0], tok[-1]) in
                                  [('"', '"'), ("'", "'")]):
                # It's a quoted string
                yield 'string', tok[1:-1]
            else:
                yield 'filter', _parse_filter(clean)

        # Yield the trailing parens
        for i in range(trail):
            yield ')', ')'

        if (index < len(main_tokens) - 1) and len(main_tokens) > 1:
            yield 'and', 'and'
            index += 1


def parse_filter_rule(filter_rule, target=None):
    """Parses filter query parameter to the tree.

    Translates a filter written in the filter language into a tree of
    Filter objects.
    """

    # Parse the token stream
    state = ParseState()
    for tok, value in _parse_tokenize(filter_rule):
        state.shift(tok, value)

    try:
        return state.result(target)
    except ValueError:
        err_msg = 'Failed to understand filter %s' % filter_rule
        raise exception.ValidationError(err_msg)
