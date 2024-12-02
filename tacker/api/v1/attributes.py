# Copyright (c) 2012 OpenStack Foundation.
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

import netaddr
from oslo_log import log as logging
from oslo_utils import uuidutils

from tacker._i18n import _
from tacker.common import exceptions as n_exc


LOG = logging.getLogger(__name__)

ATTRIBUTES_TO_UPDATE = 'attributes_to_update'
ATTR_NOT_SPECIFIED = object()
# Defining a constant to avoid repeating string literal in several modules
SHARED = 'shared'

# Used by range check to indicate no limit for a bound.
UNLIMITED = None


def _verify_dict_keys(expected_keys, target_dict, strict=True):
    """Allows to verify keys in a dictionary.

    :param expected_keys: A list of keys expected to be present.
    :param target_dict: The dictionary which should be verified.
    :param strict: Specifies whether additional keys are allowed to be present.
    :return: True, if keys in the dictionary correspond to the specification.
    """
    if not isinstance(target_dict, dict):
        msg = (_("Invalid input. '%(target_dict)s' must be a dictionary "
                 "with keys: %(expected_keys)s") %
               {'target_dict': target_dict, 'expected_keys': expected_keys})
        return msg

    expected_keys = set(expected_keys)
    provided_keys = set(target_dict.keys())

    predicate = expected_keys.__eq__ if strict else expected_keys.issubset

    if not predicate(provided_keys):
        msg = (_("Validation of dictionary's keys failed. "
                 "Expected keys: %(expected_keys)s "
                 "Provided keys: %(provided_keys)s") %
               {'expected_keys': expected_keys,
                'provided_keys': provided_keys})
        return msg


def is_attr_set(attribute):
    return not (attribute is None or attribute is ATTR_NOT_SPECIFIED)


def _validate_values(data, valid_values=None):
    if data not in valid_values:
        msg = (_("'%(data)s' is not in %(valid_values)s") %
               {'data': data, 'valid_values': valid_values})
        LOG.debug(msg)
        return msg


def _validate_not_empty_string_or_none(data, max_len=None):
    if data is not None:
        return _validate_not_empty_string(data, max_len=max_len)


def _validate_not_empty_string(data, max_len=None):
    msg = _validate_string(data, max_len=max_len)
    if msg:
        return msg
    if not data.strip():
        return _("'%s' Blank strings are not permitted") % data


def _validate_string_or_none(data, max_len=None):
    if data is not None:
        return _validate_string(data, max_len=max_len)


def _validate_string(data, max_len=None):
    if not isinstance(data, str):
        msg = _("'%s' is not a valid string") % data
        LOG.debug(msg)
        return msg

    if max_len is not None and len(data) > max_len:
        msg = (_("'%(data)s' exceeds maximum length of %(max_len)s") %
               {'data': data, 'max_len': max_len})
        LOG.debug(msg)
        return msg


def _validate_boolean(data, valid_values=None):
    try:
        convert_to_boolean(data)
    except n_exc.InvalidInput:
        msg = _("'%s' is not a valid boolean value") % data
        LOG.debug(msg)
        return msg


def _validate_range(data, valid_values=None):
    """Check that integer value is within a range provided.

    Test is inclusive. Allows either limit to be ignored, to allow
    checking ranges where only the lower or upper limit matter.
    It is expected that the limits provided are valid integers or
    the value None.
    """

    min_value = valid_values[0]
    max_value = valid_values[1]
    try:
        data = int(data)
    except (ValueError, TypeError):
        msg = _("'%s' is not an integer") % data
        LOG.debug(msg)
        return msg
    if min_value is not UNLIMITED and data < min_value:
        msg = _("'%(data)s' is too small - must be at least "
                "'%(limit)d'") % {'data': data, 'limit': min_value}
        LOG.debug(msg)
        return msg
    if max_value is not UNLIMITED and data > max_value:
        msg = _("'%(data)s' is too large - must be no larger than "
                "'%(limit)d'") % {'data': data, 'limit': max_value}
        LOG.debug(msg)
        return msg


def _validate_no_whitespace(data):
    """Validates that input has no whitespace."""
    if len(data.split()) > 1:
        msg = _("'%s' contains whitespace") % data
        LOG.debug(msg)
        raise n_exc.InvalidInput(error_message=msg)
    return data


def _validate_mac_address(data, valid_values=None):
    try:
        valid_mac = netaddr.valid_mac(_validate_no_whitespace(data))
        if valid_mac is False:
            msg = _("'%s' is not a valid MAC address") % data
            LOG.debug(msg)
            return msg
    except AttributeError as ex:
        msg = _("MAC address must be string: %s") % ex
        LOG.exception(msg)
        return msg


def _validate_mac_address_or_none(data, valid_values=None):
    if data is None:
        return
    return _validate_mac_address(data, valid_values)


def _validate_ip_address(data, valid_values=None):
    try:
        netaddr.IPAddress(_validate_no_whitespace(data))
    except Exception:
        msg = _("'%s' is not a valid IP address") % data
        LOG.debug(msg)
        return msg


def _validate_ip_pools(data, valid_values=None):
    """Validate that start and end IP addresses are present.

    In addition to this the IP addresses will also be validated
    """
    if not isinstance(data, list):
        msg = _("Invalid data format for IP pool: '%s'") % data
        LOG.debug(msg)
        return msg

    expected_keys = ['start', 'end']
    for ip_pool in data:
        msg = _verify_dict_keys(expected_keys, ip_pool)
        if msg:
            LOG.debug(msg)
            return msg
        for k in expected_keys:
            msg = _validate_ip_address(ip_pool[k])
            if msg:
                LOG.debug(msg)
                return msg


def _validate_fixed_ips(data, valid_values=None):
    if not isinstance(data, list):
        msg = _("Invalid data format for fixed IP: '%s'") % data
        LOG.debug(msg)
        return msg

    ips = []
    for fixed_ip in data:
        if not isinstance(fixed_ip, dict):
            msg = _("Invalid data format for fixed IP: '%s'") % fixed_ip
            LOG.debug(msg)
            return msg
        if 'ip_address' in fixed_ip:
            # Ensure that duplicate entries are not set - just checking IP
            # suffices. Duplicate subnet_id's are legitimate.
            fixed_ip_address = fixed_ip['ip_address']
            if fixed_ip_address in ips:
                msg = _("Duplicate IP address '%s'") % fixed_ip_address
            else:
                msg = _validate_ip_address(fixed_ip_address)
            if msg:
                LOG.debug(msg)
                return msg
            ips.append(fixed_ip_address)
        if 'subnet_id' in fixed_ip:
            msg = _validate_uuid(fixed_ip['subnet_id'])
            if msg:
                LOG.debug(msg)
                return msg


def _validate_nameservers(data, valid_values=None):
    if not hasattr(data, '__iter__'):
        msg = _("Invalid data format for nameserver: '%s'") % data
        LOG.debug(msg)
        return msg

    ips = []
    for ip in data:
        msg = _validate_ip_address(ip)
        if msg:
            # This may be a hostname
            msg = _validate_regex(ip, HOSTNAME_PATTERN)
            if msg:
                msg = _("'%s' is not a valid nameserver") % ip
                LOG.debug(msg)
                return msg
        if ip in ips:
            msg = _("Duplicate nameserver '%s'") % ip
            LOG.debug(msg)
            return msg
        ips.append(ip)


def _validate_hostroutes(data, valid_values=None):
    if not isinstance(data, list):
        msg = _("Invalid data format for hostroute: '%s'") % data
        LOG.debug(msg)
        return msg

    expected_keys = ['destination', 'nexthop']
    hostroutes = []
    for hostroute in data:
        msg = _verify_dict_keys(expected_keys, hostroute)
        if msg:
            LOG.debug(msg)
            return msg
        msg = _validate_subnet(hostroute['destination'])
        if msg:
            LOG.debug(msg)
            return msg
        msg = _validate_ip_address(hostroute['nexthop'])
        if msg:
            LOG.debug(msg)
            return msg
        if hostroute in hostroutes:
            msg = _("Duplicate hostroute '%s'") % hostroute
            LOG.debug(msg)
            return msg
        hostroutes.append(hostroute)


def _validate_ip_address_or_none(data, valid_values=None):
    if data is None:
        return None
    return _validate_ip_address(data, valid_values)


def _validate_subnet(data, valid_values=None, expand_partial_value=False):
    msg = None
    try:
        net = netaddr.IPNetwork(_validate_no_whitespace(data),
                                expand_partial=expand_partial_value)
        if '/' not in data:
            msg = _("'%(data)s' isn't a recognized IP subnet cidr,"
                    " '%(cidr)s' is recommended") % {"data": data,
                                                     "cidr": net.cidr}
        else:
            return
    except Exception:
        msg = _("'%s' is not a valid IP subnet") % data
    if msg:
        LOG.debug(msg)
    return msg


def _validate_subnet_list(data, valid_values=None,
                          expand_partial_value=False):
    if not isinstance(data, list):
        msg = _("'%s' is not a list") % data
        LOG.debug(msg)
        return msg

    if len(set(data)) != len(data):
        msg = _("Duplicate items in the list: '%s'") % ', '.join(data)
        LOG.debug(msg)
        return msg

    for item in data:
        msg = _validate_subnet(item, valid_values, expand_partial_value)
        if msg:
            return msg


def _validate_subnet_or_none(data, valid_values=None,
                             expand_partial_value=False):
    if data is None:
        return
    return _validate_subnet(data, valid_values, expand_partial_value)


def _validate_regex(data, valid_values=None):
    try:
        if re.match(valid_values, data):
            return
    except TypeError:
        pass

    msg = _("'%s' is not a valid input") % data
    LOG.debug(msg)
    return msg


def _validate_regex_or_none(data, valid_values=None):
    if data is None:
        return
    return _validate_regex(data, valid_values)


def _validate_uuid(data, valid_values=None):
    if not uuidutils.is_uuid_like(data):
        msg = _("'%s' is not a valid UUID") % data
        LOG.debug(msg)
        return msg


def _validate_uuid_or_none(data, valid_values=None):
    if data is not None:
        return _validate_uuid(data)


def _validate_uuid_list(data, valid_values=None):
    if not isinstance(data, list):
        msg = _("'%s' is not a list") % data
        LOG.debug(msg)
        return msg

    for item in data:
        msg = _validate_uuid(item)
        if msg:
            LOG.debug(msg)
            return msg

    if len(set(data)) != len(data):
        msg = _("Duplicate items in the list: '%s'") % ', '.join(data)
        LOG.debug(msg)
        return msg


def _validate_dict_item(key, key_validator, data):
    # Find conversion function, if any, and apply it
    conv_func = key_validator.get('convert_to')
    if conv_func:
        data[key] = conv_func(data.get(key))
    # Find validator function
    # TODO(salv-orlando): Structure of dict attributes should be improved
    # to avoid iterating over items
    val_func = val_params = None
    for (k, v) in (key_validator).items():
        if k.startswith('type:'):
            # ask forgiveness, not permission
            try:
                val_func = validators[k]
            except KeyError:
                return _("Validator '%s' does not exist.") % k
            val_params = v
            break
    # Process validation
    if val_func:
        return val_func(data.get(key), val_params)


def _validate_dict(data, key_specs=None):
    if not isinstance(data, dict):
        msg = _("'%s' is not a dictionary") % data
        LOG.debug(msg)
        return msg
    # Do not perform any further validation, if no constraints are supplied
    if not key_specs:
        return

    # Check whether all required keys are present
    required_keys = [key for key, spec in (key_specs).items()
                     if spec.get('required')]

    if required_keys:
        msg = _verify_dict_keys(required_keys, data, False)
        if msg:
            LOG.debug(msg)
            return msg

    # Perform validation and conversion of all values
    # according to the specifications.
    for key, key_validator in [(k, v) for k, v in (key_specs).items()
                               if k in data]:
        msg = _validate_dict_item(key, key_validator, data)
        if msg:
            LOG.debug(msg)
            return msg


def _validate_dict_or_none(data, key_specs=None):
    if data is not None:
        return _validate_dict(data, key_specs)


def _validate_dict_or_empty(data, key_specs=None):
    if data != {}:
        return _validate_dict(data, key_specs)


def _validate_dict_or_nodata(data, key_specs=None):
    if data:
        return _validate_dict(data, key_specs)


def _validate_dict_not_empty(data, key_specs=None):
    if not isinstance(data, dict) or len(data) == 0:
        msg = _("'%s' is not a valid dictionary or it is an"
                " empty dictionary") % data
        LOG.debug(msg)
        return msg
    else:
        return _validate_dict(data, key_specs)


def _validate_non_negative(data, valid_values=None):
    try:
        data = int(data)
    except (ValueError, TypeError):
        msg = _("'%s' is not an integer") % data
        LOG.debug(msg)
        return msg

    if data < 0:
        msg = _("'%s' should be non-negative") % data
        LOG.debug(msg)
        return msg


def convert_to_boolean(data):
    if isinstance(data, str):
        val = data.lower()
        if val == "true" or val == "1":
            return True
        if val == "false" or val == "0":
            return False
    elif isinstance(data, bool):
        return data
    elif isinstance(data, int):
        if data == 0:
            return False
        elif data == 1:
            return True
    msg = _("'%s' cannot be converted to boolean") % data
    raise n_exc.InvalidInput(error_message=msg)


def convert_to_int(data):
    try:
        return int(data)
    except (ValueError, TypeError):
        msg = _("'%s' is not an integer") % data
        raise n_exc.InvalidInput(error_message=msg)


def convert_kvp_str_to_list(data):
    """Convert a value of the form 'key=value' to ['key', 'value'].

    :raises n_exc.InvalidInput: if any of the strings are malformed
                                (e.g. do not contain a key).
    """
    kvp = [x.strip() for x in data.split('=', 1)]
    if len(kvp) == 2 and kvp[0]:
        return kvp
    msg = _("'%s' is not of the form <key>=[value]") % data
    raise n_exc.InvalidInput(error_message=msg)


def convert_kvp_list_to_dict(kvp_list):
    """Convert a list of 'key=value' strings to a dict.

    :raises n_exc.InvalidInput: if any of the strings are malformed
                                (e.g. do not contain a key) or if any
                                of the keys appear more than once.
    """
    if kvp_list == ['True']:
        # No values were provided (i.e. '--flag-name')
        return {}
    kvp_map = {}
    for kvp_str in kvp_list:
        key, value = convert_kvp_str_to_list(kvp_str)
        kvp_map.setdefault(key, set())
        kvp_map[key].add(value)
    return dict((x, list(y)) for x, y in (kvp_map).items())


def convert_none_to_empty_list(value):
    return [] if value is None else value


def convert_none_to_empty_dict(value):
    return {} if value is None else value


def convert_to_list(data):
    if data is None:
        return []
    elif hasattr(data, '__iter__') and not isinstance(data, str):
        return list(data)
    else:
        return [data]


HOSTNAME_PATTERN = (r"(?=^.{1,254}$)(^(?:(?!\d+\.|-)[a-zA-Z0-9_\-]"
                    r"{1,63}(?<!-)\.?)+(?:[a-zA-Z]{2,})$)")

HEX_ELEM = '[0-9A-Fa-f]'
UUID_PATTERN = '-'.join([HEX_ELEM + '{8}', HEX_ELEM + '{4}',
                         HEX_ELEM + '{4}', HEX_ELEM + '{4}',
                         HEX_ELEM + '{12}'])
# Note: In order to ensure that the MAC address is unicast the first byte
# must be even.
MAC_PATTERN = "^%s[aceACE02468](:%s{2}){5}$" % (HEX_ELEM, HEX_ELEM)

# Dictionary that maintains a list of validation functions
validators = {'type:dict': _validate_dict,
              'type:dict_or_none': _validate_dict_or_none,
              'type:dict_or_empty': _validate_dict_or_empty,
              'type:dict_or_nodata': _validate_dict_or_nodata,
              'type:dict_not_empty': _validate_dict_not_empty,
              'type:fixed_ips': _validate_fixed_ips,
              'type:hostroutes': _validate_hostroutes,
              'type:ip_address': _validate_ip_address,
              'type:ip_address_or_none': _validate_ip_address_or_none,
              'type:ip_pools': _validate_ip_pools,
              'type:mac_address': _validate_mac_address,
              'type:mac_address_or_none': _validate_mac_address_or_none,
              'type:nameservers': _validate_nameservers,
              'type:non_negative': _validate_non_negative,
              'type:range': _validate_range,
              'type:regex': _validate_regex,
              'type:regex_or_none': _validate_regex_or_none,
              'type:string': _validate_string,
              'type:string_or_none': _validate_string_or_none,
              'type:not_empty_string': _validate_not_empty_string,
              'type:not_empty_string_or_none':
              _validate_not_empty_string_or_none,
              'type:subnet': _validate_subnet,
              'type:subnet_list': _validate_subnet_list,
              'type:subnet_or_none': _validate_subnet_or_none,
              'type:uuid': _validate_uuid,
              'type:uuid_or_none': _validate_uuid_or_none,
              'type:uuid_list': _validate_uuid_list,
              'type:values': _validate_values,
              'type:boolean': _validate_boolean}

# Define constants for base resource name

# Note: a default of ATTR_NOT_SPECIFIED indicates that an
# attribute is not required, but will be generated by the plugin
# if it is not specified.  Particularly, a value of ATTR_NOT_SPECIFIED
# is different from an attribute that has been specified with a value of
# None.  For example, if 'gateway_ip' is omitted in a request to
# create a subnet, the plugin will receive ATTR_NOT_SPECIFIED
# and the default gateway_ip will be generated.
# However, if gateway_ip is specified as None, this means that
# the subnet does not have a gateway IP.
# The following is a short reference for understanding attribute info:
# default: default value of the attribute (if missing, the attribute
# becomes mandatory.
# allow_post: the attribute can be used on POST requests.
# allow_put: the attribute can be used on PUT requests.
# validate: specifies rules for validating data in the attribute.
# convert_to: transformation to apply to the value before it is returned
# is_visible: the attribute is returned in GET responses.
# required_by_policy: the attribute is required by the policy engine and
# should therefore be filled by the API layer even if not present in
# request body.
# enforce_policy: the attribute is actively part of the policy enforcing
# mechanism, ie: there might be rules which refer to this attribute.

# Identify the attribute used by a resource to reference another resource

RESOURCE_ATTRIBUTE_MAP = {}

RESOURCE_FOREIGN_KEYS = {}

PLURALS = {'extensions': 'extension'}
