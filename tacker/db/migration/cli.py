# Copyright 2012 New Dream Network, LLC (DreamHost)
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

import os

from alembic import command as alembic_command
from alembic import config as alembic_config
from alembic import script as alembic_script
from alembic import util as alembic_util
from oslo_config import cfg

from tacker._i18n import _
from tacker.db.migration.models import head  # noqa
from tacker.db.migration import purge_tables

HEAD_FILENAME = 'HEAD'


_db_opts = [
    cfg.StrOpt('connection',
               deprecated_name='sql_connection',
               default='',
               secret=True,
               help=_('URL to database')),
    cfg.StrOpt('engine',
               default='',
               help=_('Database engine')),
]

CONF = cfg.ConfigOpts()
CONF.register_cli_opts(_db_opts, 'database')


def do_alembic_command(config, cmd, *args, **kwargs):
    try:
        getattr(alembic_command, cmd)(config, *args, **kwargs)
    except alembic_util.CommandError as e:
        alembic_util.err(str(e))


def do_check_migration(config, cmd):
    do_alembic_command(config, 'branches')
    validate_head_file(config)


def do_upgrade(config, cmd):
    if not CONF.command.revision and not CONF.command.delta:
        raise SystemExit(_('You must provide a revision or relative delta'))

    revision = CONF.command.revision

    if CONF.command.delta:
        revision = '+%s' % str(CONF.command.delta)
    else:
        revision = CONF.command.revision

    do_alembic_command(config, cmd, revision, sql=CONF.command.sql)


def do_stamp(config, cmd):
    do_alembic_command(config, cmd,
                       CONF.command.revision,
                       sql=CONF.command.sql)


def do_revision(config, cmd):
    do_alembic_command(config, cmd,
                       message=CONF.command.message,
                       autogenerate=CONF.command.autogenerate,
                       sql=CONF.command.sql)
    update_head_file(config)


def validate_head_file(config):
    script = alembic_script.ScriptDirectory.from_config(config)
    if len(script.get_heads()) > 1:
        alembic_util.err(_('Timeline branches unable to generate timeline'))

    head_path = os.path.join(str(script.versions), HEAD_FILENAME)
    if (os.path.isfile(head_path) and
            open(head_path).read().strip() == script.get_current_head()):
        return
    else:
        alembic_util.err(_('HEAD file does not match migration timeline head'))


def update_head_file(config):
    script = alembic_script.ScriptDirectory.from_config(config)
    if len(script.get_heads()) > 1:
        alembic_util.err(_('Timeline branches unable to generate timeline'))

    head_path = os.path.join(str(script.versions), HEAD_FILENAME)
    with open(head_path, 'w+') as f:
        f.write(script.get_current_head())


def purge_deleted(config, cmd):
    """Remove database records that have been previously soft deleted."""
    purge_tables.purge_deleted(config.tacker_config,
                      CONF.command.resource,
                      CONF.command.age,
                      CONF.command.granularity)


def add_command_parsers(subparsers):
    for name in ['current', 'history', 'branches']:
        parser = subparsers.add_parser(name)
        parser.set_defaults(func=do_alembic_command)

    parser = subparsers.add_parser('check_migration')
    parser.set_defaults(func=do_check_migration)

    parser = subparsers.add_parser('upgrade')
    parser.add_argument('--delta', type=int)
    parser.add_argument('--sql', action='store_true')
    parser.add_argument('revision', nargs='?')
    parser.set_defaults(func=do_upgrade)

    parser = subparsers.add_parser('stamp')
    parser.add_argument('--sql', action='store_true')
    parser.add_argument('revision')
    parser.set_defaults(func=do_stamp)

    parser = subparsers.add_parser('revision')
    parser.add_argument('-m', '--message')
    parser.add_argument('--autogenerate', action='store_true')
    parser.add_argument('--sql', action='store_true')
    parser.set_defaults(func=do_revision)

    parser = subparsers.add_parser('purge_deleted')
    parser.set_defaults(func=purge_deleted)
    # positional parameter
    parser.add_argument(
        'resource',
        choices=['all', 'events', 'vnf', 'vnfd', 'vims'],
        help=_('Resource name for which deleted entries are to be purged.'))
    # optional parameter, can be skipped. default='90'
    parser.add_argument('-a', '--age', nargs='?', default='90',
                        help=_('How long to preserve deleted data, '
                               'defaults to 90'))
    # optional parameter, can be skipped. default='days'
    parser.add_argument(
        '-g', '--granularity', default='days',
        choices=['days', 'hours', 'minutes', 'seconds'],
        help=_('Granularity to use for age argument, defaults to days.'))


command_opt = cfg.SubCommandOpt('command',
                                title='Command',
                                help=_('Available commands'),
                                handler=add_command_parsers)

CONF.register_cli_opt(command_opt)


def main():
    config = alembic_config.Config(
        os.path.join(os.path.dirname(__file__), 'alembic.ini')
    )
    config.set_main_option('script_location',
                           'tacker.db.migration:alembic_migrations')
    # attach the Tacker conf to the Alembic conf
    config.tacker_config = CONF

    CONF()
    # TODO(gongysh) enable logging
    CONF.command.func(config, CONF.command.name)
