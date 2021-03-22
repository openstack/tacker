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
Common parameter types for validating request Body.

"""

import re
import unicodedata


def _is_printable(char):
    """determine if a unicode code point is printable.

    This checks if the character is either "other" (mostly control
    codes), or a non-horizontal space. All characters that don't match
    those criteria are considered printable; that is: letters;
    combining marks; numbers; punctuation; symbols; (horizontal) space
    separators.
    """
    category = unicodedata.category(char)
    return (not category.startswith("C") and
            (not category.startswith("Z") or category == "Zs"))


def _get_all_chars():
    for i in range(0xFFFF):
        yield chr(i)


# build a regex that matches all printable characters. This allows
# spaces in the middle of the name. Also note that the regexp below
# deliberately allows the empty string. This is so only the constraint
# which enforces a minimum length for the name is triggered when an
# empty string is tested. Otherwise it is not deterministic which
# constraint fails and this causes issues for some unittests when
# PYTHONHASHSEED is set randomly.

def _build_regex_range(ws=True, invert=False, exclude=None):
    """Build a range regex for a set of characters in utf8.

    This builds a valid range regex for characters in utf8 by
    iterating the entire space and building up a set of x-y ranges for
    all the characters we find which are valid.

    :param ws: should we include whitespace in this range.
    :param invert: invert the logic
    :param exclude: any characters we want to exclude

    The inversion is useful when we want to generate a set of ranges
    which is everything that's not a certain class. For instance,
    produce all all the non printable characters as a set of ranges.
    """
    if exclude is None:
        exclude = []
    regex = ""
    # are we currently in a range
    in_range = False
    # last character we found, for closing ranges
    last = None
    # last character we added to the regex, this lets us know that we
    # already have B in the range, which means we don't need to close
    # it out with B-B. While the later seems to work, it's kind of bad form.
    last_added = None

    def valid_char(char):
        if char in exclude:
            result = False
        elif ws:
            result = _is_printable(char)
        else:
            # Zs is the unicode class for space characters, of which
            # there are about 10 in this range.
            result = (_is_printable(char) and
                      unicodedata.category(char) != "Zs")
        if invert is True:
            return not result
        return result

    # iterate through the entire character range. in_
    for c in _get_all_chars():
        if valid_char(c):
            if not in_range:
                regex += re.escape(c)
                last_added = c
            in_range = True
        else:
            if in_range and last != last_added:
                regex += "-" + re.escape(last)
            in_range = False
        last = c
    else:
        if in_range:
            regex += "-" + re.escape(c)
    return regex


valid_description_regex_base = '^[%s]*$'

valid_description_regex = valid_description_regex_base % (
    _build_regex_range())


keyvalue_pairs = {
    'type': 'object',
    'patternProperties': {
        '^[a-zA-Z0-9-_:. /]{1,255}$': {
            'anyOf': [
                {'type': 'array'},
                {'type': 'string', 'maxLength': 255},
                {'type': 'object'}
            ]
        }
    },
    'additionalProperties': False
}

description = {
    'type': 'string', 'minLength': 0, 'maxLength': 1024,
    'pattern': valid_description_regex,
}

uuid = {
    'type': 'string', 'format': 'uuid'
}

name_allow_zero_min_length = {
    'type': 'string', 'minLength': 0, 'maxLength': 255
}

ip_address = {
    'type': 'string',
    'oneOf': [
        {'format': 'ipv4'},
        {'format': 'ipv6'}
    ]
}

positive_integer = {
    'type': ['integer', 'string'],
    'pattern': '^[0-9]*$', 'minimum': 1, 'minLength': 1
}

identifier = {
    'type': 'string', 'minLength': 1, 'maxLength': 255
}

identifier_in_vim = {
    'type': 'string', 'minLength': 1, 'maxLength': 255
}

identifier_in_vnfd = {
    'type': 'string', 'minLength': 1, 'maxLength': 255
}

identifier_in_vnf = {
    'type': 'string', 'minLength': 1, 'maxLength': 255
}

mac_address_or_none = {
    'type': 'string', 'format': 'mac_address_or_none'
}
