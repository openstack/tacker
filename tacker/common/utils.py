# Copyright 2011, VMware, Inc.
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
#
# Borrowed from nova code base, more utilities will be added/borrowed as and
# when needed.

"""Utilities and helper functions."""

import functools
from functools import reduce
import inspect
import logging as std_logging
import math
import os
import random
import re
import signal
import socket
import string
import sys

from eventlet.green import subprocess
import netaddr
from oslo_concurrency import lockutils
from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import excutils
from oslo_utils import importutils
from six.moves import urllib
from six.moves.urllib import parse as urlparse
from stevedore import driver
try:
    from eventlet import sleep
except ImportError:
    from time import sleep

from tacker._i18n import _
from tacker.common import constants as q_const
from tacker.common import exceptions
from tacker.common import safe_utils


TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
LOG = logging.getLogger(__name__)
SYNCHRONIZED_PREFIX = 'tacker-'
MEM_UNITS = {
    "MB": {
        "MB": {
            "op": "*",
            "val": "1"
        },
        "GB": {
            "op": "/",
            "val": "1024"
        }
    },
    "GB": {
        "MB": {
            "op": "*",
            "val": "1024"
        },
        "GB": {
            "op": "*",
            "val": "1"
        }
    }
}
CONF = cfg.CONF
synchronized = lockutils.synchronized_with_prefix(SYNCHRONIZED_PREFIX)
MAX_COOP_READER_BUFFER_SIZE = 134217728

if hasattr(inspect, 'getfullargspec'):
    getargspec = inspect.getfullargspec
else:
    getargspec = inspect.getargspec


def find_config_file(options, config_file):
    """Return the first config file found.

    We search for the paste config file in the following order:
    * If --config-file option is used, use that
    * Search for the configuration files via common cfg directories
    :retval Full path to config file, or None if no config file found
    """
    fix_path = lambda p: os.path.abspath(os.path.expanduser(p))  # noqa: E731
    if options.get('config_file'):
        if os.path.exists(options['config_file']):
            return fix_path(options['config_file'])

    dir_to_common = os.path.dirname(os.path.abspath(__file__))
    root = os.path.join(dir_to_common, '..', '..', '..', '..')
    # Handle standard directory search for the config file
    config_file_dirs = [fix_path(os.path.join(os.getcwd(), 'etc')),
                        fix_path(os.path.join('~', '.tacker-venv', 'etc',
                                              'tacker')),
                        fix_path('~'),
                        os.path.join(cfg.CONF.state_path, 'etc'),
                        os.path.join(cfg.CONF.state_path, 'etc', 'tacker'),
                        fix_path(os.path.join('~', '.local',
                                              'etc', 'tacker')),
                        '/usr/etc/tacker',
                        '/usr/local/etc/tacker',
                        '/etc/tacker/',
                        '/etc']

    if 'plugin' in options:
        config_file_dirs = [
            os.path.join(x, 'tacker', 'plugins', options['plugin'])
            for x in config_file_dirs
        ]

    if os.path.exists(os.path.join(root, 'plugins')):
        plugins = [fix_path(os.path.join(root, 'plugins', p, 'etc'))
                   for p in os.listdir(os.path.join(root, 'plugins'))]
        plugins = [p for p in plugins if os.path.isdir(p)]
        config_file_dirs.extend(plugins)

    for cfg_dir in config_file_dirs:
        cfg_file = os.path.join(cfg_dir, config_file)
        if os.path.exists(cfg_file):
            return cfg_file


def _subprocess_setup():
    # Python installs a SIGPIPE handler by default. This is usually not what
    # non-Python subprocesses expect.
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)


def subprocess_popen(args, stdin=None, stdout=None, stderr=None, shell=False,
                     env=None):
    return subprocess.Popen(args, shell=shell, stdin=stdin, stdout=stdout,
                            stderr=stderr, preexec_fn=_subprocess_setup,
                            close_fds=True, env=env)


def get_hostname():
    return socket.gethostname()


def dict2tuple(d):
    items = list(d.items())
    items.sort()
    return tuple(items)


def log_opt_values(log):
    cfg.CONF.log_opt_values(log, std_logging.DEBUG)


def is_valid_vlan_tag(vlan):
    return q_const.MIN_VLAN_TAG <= vlan <= q_const.MAX_VLAN_TAG


def is_valid_ipv4(address):
    """Verify that address represents a valid IPv4 address."""
    try:
        return netaddr.valid_ipv4(address)
    except Exception:
        return False


def change_memory_unit(mem, to):
    """Change the memory value(mem) based on the unit('to') specified.

    If the unit is not specified in 'mem', by default, it is considered
    as "MB". And this method returns only integer.
    """
    mem = str(mem) + " MB" if str(mem).isdigit() else mem.upper()
    for unit, value in (MEM_UNITS).items():
        mem_arr = mem.split(unit)
        if len(mem_arr) < 2:
            continue
        return eval(mem_arr[0] +
                    MEM_UNITS[unit][to]["op"] +
                    MEM_UNITS[unit][to]["val"])


def load_class_by_alias_or_classname(namespace, name):
    """Load class using stevedore alias or the class name.

    Load class using the stevedore driver manager
    :param namespace: namespace where the alias is defined
    :param name: alias or class name of the class to be loaded
    :returns: class if calls can be loaded
    :raises ImportError: if class cannot be loaded
    """
    if not name:
        LOG.error("Alias or class name is not set")
        raise ImportError(_("Class not found."))
    try:
        # Try to resolve class by alias
        mgr = driver.DriverManager(namespace, name)
        class_to_load = mgr.driver
    except RuntimeError:
        e1_info = sys.exc_info()
        # Fallback to class name
        try:
            class_to_load = importutils.import_class(name)
        except (ImportError, ValueError):
            LOG.error("Error loading class by alias",
                      exc_info=e1_info)
            LOG.error("Error loading class by class name",
                      exc_info=True)
            raise ImportError(_("Class not found."))
    return class_to_load


def deep_update(orig_dict, new_dict):
    for key, value in new_dict.items():
        if isinstance(value, dict):
            if key in orig_dict and isinstance(orig_dict[key], dict):
                deep_update(orig_dict[key], value)
                continue

        orig_dict[key] = value


def generate_resource_name(resource, prefix='tmpl'):
    return prefix + '-' \
        + ''.join(random.SystemRandom().choice(
                  string.ascii_lowercase + string.digits)
          for _ in range(16)) \
        + '-' + resource


def get_auth_url_v3(auth_url):
    if re.match('.+v3/?$', auth_url) is not None:
        return auth_url
    else:
        return '{0}/v3'.format(auth_url)


def none_from_string(orig_str):
    none_values = ['', 'None', 'NONE', 'null', 'NULL']
    if orig_str in none_values:
        return None
    else:
        return orig_str


def expects_func_args(*args):
    def _decorator_checker(dec):
        @functools.wraps(dec)
        def _decorator(f):
            base_f = safe_utils.get_wrapped_function(f)
            argspec = getargspec(base_f)
            if argspec[1] or argspec[2] or set(args) <= set(argspec[0]):
                # NOTE (nirajsingh): We can't really tell if correct stuff will
                # be passed if it's a function with *args or **kwargs so
                # we still carry on and hope for the best
                return dec(f)
            else:
                raise TypeError("Decorated function %(f_name)s does not "
                                "have the arguments expected by the "
                                "decorator %(d_name)s" %
                                {'f_name': base_f.__name__,
                                 'd_name': dec.__name__})

        return _decorator

    return _decorator_checker


def cooperative_iter(iter):
    """Prevent eventlet thread starvation during iteration

    Return an iterator which schedules after each
    iteration. This can prevent eventlet thread starvation.

    :param iter: an iterator to wrap
    """
    try:
        for chunk in iter:
            sleep(0)
            yield chunk
    except Exception as err:
        with excutils.save_and_reraise_exception():
            msg = _("Error: cooperative_iter exception %s") % err
            LOG.error(msg)


def cooperative_read(fd):
    """Prevent eventlet thread starvationafter each read operation.

    Wrap a file descriptor's read with a partial function which schedules
    after each read. This can prevent eventlet thread starvation.

    :param fd: a file descriptor to wrap
    """
    def readfn(*args):
        result = fd.read(*args)
        sleep(0)
        return result
    return readfn


def chunkreadable(iter, chunk_size=65536):
    """Wrap a readable iterator.

    Wrap a readable iterator with a reader yielding chunks of
    a preferred size, otherwise leave iterator unchanged.

    :param iter: an iter which may also be readable
    :param chunk_size: maximum size of chunk
    """
    return chunkiter(iter, chunk_size) if hasattr(iter, 'read') else iter


def chunkiter(fp, chunk_size=65536):
    """Convert iterator to a file-like object.

    Return an iterator to a file-like obj which yields fixed size chunks

    :param fp: a file-like object
    :param chunk_size: maximum size of chunk
    """
    while True:
        chunk = fp.read(chunk_size)
        if chunk:
            yield chunk
        else:
            break


def convert_camelcase_to_snakecase(request_data):
    """Converts dict keys or list of dict keys from camelCase to snake_case.

    Returns a dict with keys or list with dict keys, in snake_case.
    This method takes care only keys in a `dict` or `dicts in a list`.
    For simple list with string items, the elements which are actual values
    are ignored during conversion.

    :param request_data: dict with keys or list with items, in camelCase.
    """
    def convert(name):
        name_with_underscores = re.sub(
            '(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2',
                      name_with_underscores).lower()

    if isinstance(request_data, dict):
        new_dict = {}
        for key, property_value in request_data.items():
            property_value = convert_camelcase_to_snakecase(property_value)
            underscore_joined = convert(key)
            new_dict[underscore_joined] = property_value
        return new_dict

    if isinstance(request_data, list):
        new_list = []
        for property_value in request_data:
            new_list.append(
                convert_camelcase_to_snakecase(property_value))
        return new_list

    return request_data


def convert_snakecase_to_camelcase(request_data):
    """Converts dict keys or list of dict keys from snake_case to camelCase.

    Returns a dict with keys or list with dict key, in camelCase.
    This method takes care only keys in a `dict` or `dicts in a list`.
    For simple list with string items, the elements which are actual values
    are ignored during conversion.

    :param request_data: dict with keys or list with items, in snake_case.
    """
    def convert(name):
        return re.sub('_([a-z])',
                      lambda match: match.group(1).upper(), name)

    if isinstance(request_data, dict):
        new_dict = {}
        for key, property_value in request_data.items():
            property_value = convert_snakecase_to_camelcase(property_value)
            camelcase = convert(key)
            new_dict[camelcase] = property_value
        return new_dict

    if isinstance(request_data, list):
        new_list = []
        for property_value in request_data:
            new_list.append(
                convert_snakecase_to_camelcase(property_value))
        return new_list

    return request_data


def is_url(url):
    try:
        urllib.request.urlopen(url)
        return True
    except Exception:
        return False


def flatten_dict(data, prefix=''):
    ret = {}
    for key, val in data.items():
        key = prefix + key
        if isinstance(val, dict):
            ret.update(flatten_dict(val, key + '/'))
        else:
            ret[key] = val
    return ret


def deepgetattr(obj, attr):
    """Recurses through an attribute chain to get the ultimate value."""
    return reduce(getattr, attr.split('.'), obj)


def is_valid_url(url):
    url_parts = urlparse.urlparse(url)

    if not (url_parts.scheme and url_parts.netloc and url_parts.path):
        return False

    schemes = ['http', 'https', 'ftp']
    if url_parts.scheme not in schemes:
        return False

    return True


class CooperativeReader(object):
    """An eventlet thread friendly class for reading in image data.

    When accessing data either through the iterator or the read method
    we perform a sleep to allow a co-operative yield. When there is more than
    one image being uploaded/downloaded this prevents eventlet thread
    starvation, ie allows all threads to be scheduled periodically rather than
    having the same thread be continuously active.
    """
    def __init__(self, fd):
        """Construct an CooperativeReader object.

        :param fd: Underlying image file object

        """
        self.fd = fd
        self.iterator = None
        # NOTE(nirajsingh): if the underlying supports read(), overwrite the
        # default iterator-based implementation with cooperative_read which
        # is more straightforward
        if hasattr(fd, 'read'):
            self.read = cooperative_read(fd)
        else:
            self.iterator = None
            self.buffer = b''
            self.position = 0

    def read(self, length=None):
        """Return the requested amount of bytes.

        Fetching the next chunk of the underlying iterator when needed.
        This is replaced with cooperative_read in __init__ if the underlying
        fd already supports read().

        """

        if length is None:
            if len(self.buffer) - self.position > 0:
                # if no length specified but some data exists in buffer,
                # return that data and clear the buffer
                result = self.buffer[self.position:]
                self.buffer = b''
                self.position = 0
                return bytes(result)
            else:
                # otherwise read the next chunk from the underlying iterator
                # and return it as a whole. Reset the buffer, as subsequent
                # calls may specify the length
                try:
                    if self.iterator is None:
                        self.iterator = self.__iter__()
                    return next(self.iterator)
                except StopIteration:
                    return b''
                finally:
                    self.buffer = b''
                    self.position = 0
        else:
            result = bytearray()
            while len(result) < length:
                if self.position < len(self.buffer):
                    to_read = length - len(result)
                    chunk = self.buffer[self.position:self.position + to_read]
                    result.extend(chunk)

                    # This check is here to prevent potential OOM issues if
                    # this code is called with unreasonably high values of read
                    # size. Currently it is only called from the HTTP clients
                    # of Glance backend stores, which use httplib for data
                    # streaming, which has readsize hardcoded to 8K, so this
                    # check should never fire. Regardless it still worths to
                    # make the check, as the code may be reused somewhere else.
                    if len(result) >= MAX_COOP_READER_BUFFER_SIZE:
                        raise exceptions.LimitExceeded()
                    self.position += len(chunk)
                else:
                    try:
                        if self.iterator is None:
                            self.iterator = self.__iter__()
                        self.buffer = next(self.iterator)
                        self.position = 0
                    except StopIteration:
                        self.buffer = b''
                        self.position = 0
                        return bytes(result)
            return bytes(result)

    def __iter__(self):
        return cooperative_iter(self.fd.__iter__())


class LimitingReader(object):
    """Limit Reader to read data past to configured allowed amount.

    Reader designed to fail when reading image data past the configured
    allowable amount.
    """
    def __init__(self, data, limit,
                 exception_class=exceptions.CSARFileSizeLimitExceeded):
        """Construct an LimitingReader object.

        :param data: Underlying image data object
        :param limit: maximum number of bytes the reader should allow
        :param exception_class: Type of exception to be raised
        """
        self.data = data
        self.limit = limit
        self.bytes_read = 0
        self.exception_class = exception_class

    def __iter__(self):
        for chunk in self.data:
            self.bytes_read += len(chunk)
            if self.bytes_read > self.limit:
                raise self.exception_class()
            else:
                yield chunk

    def read(self, i):
        result = self.data.read(i)
        self.bytes_read += len(result)
        if self.bytes_read > self.limit:
            raise self.exception_class()
        return result


class MemoryUnit(object):

    UNIT_SIZE_DEFAULT = 'B'
    UNIT_SIZE_DICT = {'B': 1, 'kB': 1000, 'KiB': 1024, 'MB': 1000000,
                      'MiB': 1048576, 'GB': 1000000000,
                      'GiB': 1073741824, 'TB': 1000000000000,
                      'TiB': 1099511627776}

    @staticmethod
    def convert_unit_size_to_num(size, unit=None):
        """Convert given size to a number representing given unit.

        If unit is None, convert to a number representing UNIT_SIZE_DEFAULT
        :param size: unit size e.g. 1 TB
        :param unit: unit to be converted to e.g GB
        :return: converted number e.g. 1000 for 1 TB size and unit GB
        """
        if unit:
            unit = MemoryUnit.validate_unit(unit)
        else:
            unit = MemoryUnit.UNIT_SIZE_DEFAULT
            LOG.info(_('A memory unit is not provided for size; using the '
                       'default unit %(default)s.') % {'default': 'B'})
        regex = re.compile(r'(\d*)\s*(\w*)')
        result = regex.match(str(size)).groups()
        if result[1]:
            unit_size = MemoryUnit.validate_unit(result[1])
            converted = int(str_to_num(result[0]) *
                            MemoryUnit.UNIT_SIZE_DICT[unit_size] *
                            math.pow(MemoryUnit.UNIT_SIZE_DICT
                                     [unit], -1))
            LOG.info(_('Given size %(size)s is converted to %(num)s '
                       '%(unit)s.') % {'size': size,
                     'num': converted, 'unit': unit})
        else:
            converted = (str_to_num(result[0]))
        return converted

    @staticmethod
    def validate_unit(unit):
        if unit in MemoryUnit.UNIT_SIZE_DICT.keys():
            return unit
        else:
            for key in MemoryUnit.UNIT_SIZE_DICT.keys():
                if key.upper() == unit.upper():
                    return key

            msg = _('Provided unit "{0}" is not valid. The valid units are '
                    '{1}').format(unit, MemoryUnit.UNIT_SIZE_DICT.keys())
            LOG.error(msg)
            raise ValueError(msg)


def str_to_num(value):
    """Convert a string representation of a number into a numeric type."""
    if (isinstance(value, int) or
            isinstance(value, float)):
        return value

    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return None
