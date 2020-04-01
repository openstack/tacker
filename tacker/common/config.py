# Copyright 2011 VMware, Inc.
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
Routines for configuring Tacker
"""

import os

from oslo_config import cfg
from oslo_db import options as db_options
from oslo_log import log as logging
import oslo_messaging
from paste import deploy

from tacker._i18n import _
from tacker.common import utils
from tacker import version


LOG = logging.getLogger(__name__)

core_opts = [
    cfg.HostAddressOpt('bind_host', default='0.0.0.0',
                       help=_("The host IP to bind to")),
    cfg.IntOpt('bind_port', default=9890,
               help=_("The port to bind to")),
    cfg.StrOpt('api_paste_config', default="api-paste.ini",
               help=_("The API paste config file to use")),
    cfg.StrOpt('api_extensions_path', default="",
               help=_("The path for API extensions")),
    cfg.ListOpt('service_plugins', default=['nfvo', 'vnfm'],
                help=_("The service plugins Tacker will use")),
    cfg.StrOpt('auth_strategy', default='keystone',
               help=_("The type of authentication to use")),
    cfg.BoolOpt('allow_bulk', default=True,
                help=_("Allow the usage of the bulk API")),
    cfg.BoolOpt('allow_pagination', default=False,
                help=_("Allow the usage of the pagination")),
    cfg.BoolOpt('allow_sorting', default=False,
                help=_("Allow the usage of the sorting")),
    cfg.StrOpt('pagination_max_limit', default="-1",
               help=_("The maximum number of items returned "
                      "in a single response, value was 'infinite' "
                      "or negative integer means no limit")),
    cfg.HostAddressOpt('host', default=utils.get_hostname(),
                       help=_("The hostname Tacker is running on")),
]

core_cli_opts = [
    cfg.StrOpt('state_path',
               default='/var/lib/tacker',
               help=_("Where to store Tacker state files. "
                      "This directory must be writable by "
                      "the agent.")),
]

logging.register_options(cfg.CONF)
# Register the configuration options
cfg.CONF.register_opts(core_opts)
cfg.CONF.register_cli_opts(core_cli_opts)


def config_opts():
    return [(None, core_opts), (None, core_cli_opts)]


# Ensure that the control exchange is set correctly
oslo_messaging.set_transport_defaults(control_exchange='tacker')


def set_db_defaults():
    # Update the default QueuePool parameters. These can be tweaked by the
    # conf variables - max_pool_size, max_overflow and pool_timeout
    db_options.set_defaults(
        cfg.CONF,
        connection='sqlite://',
        max_pool_size=10,
        max_overflow=20, pool_timeout=10)


set_db_defaults()


def init(args, **kwargs):
    cfg.CONF(args=args, project='tacker',
             version='%%prog %s' % version.version_info.release_string(),
             **kwargs)

    # FIXME(ihrachys): if import is put in global, circular import
    # failure occurs
    from tacker.common import rpc as n_rpc
    n_rpc.init(cfg.CONF)


def setup_logging(conf):
    """Sets up the logging options for a log with supplied name.

    :param conf: a cfg.ConfOpts object
    """
    product_name = "tacker"
    logging.setup(conf, product_name)
    LOG.info("Logging enabled!")


def load_paste_app(app_name):
    """Builds and returns a WSGI app from a paste config file.

    :param app_name: Name of the application to load
    :raises ConfigFilesNotFoundError: when config file cannot be located
    :raises RuntimeError: when application cannot be loaded from config file
    """

    config_path = cfg.CONF.find_file(cfg.CONF.api_paste_config)
    if not config_path:
        raise cfg.ConfigFilesNotFoundError(
            config_files=[cfg.CONF.api_paste_config])
    config_path = os.path.abspath(config_path)
    LOG.info("Config paste file: %s", config_path)

    try:
        app = deploy.loadapp("config:%s" % config_path, name=app_name)
    except (LookupError, ImportError):
        msg = (_("Unable to load %(app_name)s from "
                 "configuration file %(config_path)s.") %
               {'app_name': app_name,
                'config_path': config_path})
        LOG.exception(msg)
        raise RuntimeError(msg)
    return app
