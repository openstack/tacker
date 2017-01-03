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
import logging as std_logging
import os
import random
import signal
import socket
import string
import sys

from eventlet.green import subprocess
import netaddr
from oslo_concurrency import lockutils
from oslo_config import cfg
from oslo_log import log as logging
from oslo_log import versionutils
from oslo_utils import importutils
from six import iteritems
from stevedore import driver

from tacker._i18n import _LE
from tacker.common import constants as q_const


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


class cache_method_results(object):
    """This decorator is intended for object methods only."""

    def __init__(self, func):
        self.func = func
        functools.update_wrapper(self, func)
        self._first_call = True
        self._not_cached = object()

    def _get_from_cache(self, target_self, *args, **kwargs):
        func_name = "%(module)s.%(class)s.%(func_name)s" % {
            'module': target_self.__module__,
            'class': target_self.__class__.__name__,
            'func_name': self.func.__name__,
        }
        key = (func_name,) + args
        if kwargs:
            key += dict2tuple(kwargs)
        try:
            item = target_self._cache.get(key, self._not_cached)
        except TypeError:
            LOG.debug(_("Method %(func_name)s cannot be cached due to "
                        "unhashable parameters: args: %(args)s, kwargs: "
                        "%(kwargs)s"),
                      {'func_name': func_name,
                       'args': args,
                       'kwargs': kwargs})
            return self.func(target_self, *args, **kwargs)

        if item is self._not_cached:
            item = self.func(target_self, *args, **kwargs)
            target_self._cache.set(key, item, None)

        return item

    def __call__(self, target_self, *args, **kwargs):
        if not hasattr(target_self, '_cache'):
            raise NotImplementedError(
                "Instance of class %(module)s.%(class)s must contain _cache "
                "attribute" % {
                    'module': target_self.__module__,
                    'class': target_self.__class__.__name__})
        if not target_self._cache:
            if self._first_call:
                LOG.debug(_("Instance of class %(module)s.%(class)s doesn't "
                            "contain attribute _cache therefore results "
                            "cannot be cached for %(func_name)s."),
                          {'module': target_self.__module__,
                           'class': target_self.__class__.__name__,
                           'func_name': self.func.__name__})
                self._first_call = False
            return self.func(target_self, *args, **kwargs)
        return self._get_from_cache(target_self, *args, **kwargs)

    def __get__(self, obj, objtype):
        return functools.partial(self.__call__, obj)


def find_config_file(options, config_file):
    """Return the first config file found.

    We search for the paste config file in the following order:
    * If --config-file option is used, use that
    * Search for the configuration files via common cfg directories
    :retval Full path to config file, or None if no config file found
    """
    fix_path = lambda p: os.path.abspath(os.path.expanduser(p))
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


def parse_mappings(mapping_list, unique_values=True):
    """Parse a list of mapping strings into a dictionary.

    :param mapping_list: a list of strings of the form '<key>:<value>'
    :param unique_values: values must be unique if True
    :returns: a dict mapping keys to values
    """
    mappings = {}
    for mapping in mapping_list:
        mapping = mapping.strip()
        if not mapping:
            continue
        split_result = mapping.split(':')
        if len(split_result) != 2:
            raise ValueError(_("Invalid mapping: '%s'") % mapping)
        key = split_result[0].strip()
        if not key:
            raise ValueError(_("Missing key in mapping: '%s'") % mapping)
        value = split_result[1].strip()
        if not value:
            raise ValueError(_("Missing value in mapping: '%s'") % mapping)
        if key in mappings:
            raise ValueError(_("Key %(key)s in mapping: '%(mapping)s' not "
                               "unique") % {'key': key, 'mapping': mapping})
        if unique_values and value in mappings.values():
            raise ValueError(_("Value %(value)s in mapping: '%(mapping)s' "
                               "not unique") % {'value': value,
                                                'mapping': mapping})
        mappings[key] = value
    return mappings


def get_hostname():
    return socket.gethostname()


def dict2tuple(d):
    items = d.items()
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
    """Changes the memory value(mem) based on the unit('to') specified.

    If the unit is not specified in 'mem', by default, it is considered
    as "MB". And this method returns only integer.
    """

    mem = str(mem) + " MB" if str(mem).isdigit() else mem.upper()
    for unit, value in iteritems(MEM_UNITS):
        mem_arr = mem.split(unit)
        if len(mem_arr) < 2:
            continue
        return eval(mem_arr[0] +
                    MEM_UNITS[unit][to]["op"] +
                    MEM_UNITS[unit][to]["val"])


def load_class_by_alias_or_classname(namespace, name):
    """Load class using stevedore alias or the class name

    Load class using the stevedore driver manager
    :param namespace: namespace where the alias is defined
    :param name: alias or class name of the class to be loaded
    :returns class if calls can be loaded
    :raises ImportError if class cannot be loaded
    """

    if not name:
        LOG.error(_LE("Alias or class name is not set"))
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
            LOG.error(_LE("Error loading class by alias"),
                      exc_info=e1_info)
            LOG.error(_LE("Error loading class by class name"),
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


def deprecate_warning(what, as_of, in_favor_of=None, remove_in=1):
    versionutils.deprecation_warning(as_of=as_of, what=what,
                                     in_favor_of=in_favor_of,
                                     remove_in=remove_in)


def generate_resource_name(resource, prefix='tmpl'):
    return prefix + '-' \
        + ''.join(random.SystemRandom().choice(
                  string.ascii_lowercase + string.digits)
          for _ in range(16)) \
        + '-' + resource
