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

from oslo_config import cfg
from oslo_db.sqlalchemy import enginefacade


context_manager = enginefacade.transaction_context()
# FIXME(ueha): we need to remove reliance on autocommit semantics ASAP
# since it's not compatible with SQLAlchemy 2.0
context_manager.configure(__autocommit=True)

_FACADE = None


def _create_facade_lazily():
    global _FACADE

    if _FACADE is None:
        context_manager.configure(sqlite_fk=True, **cfg.CONF.database)
        _FACADE = context_manager._factory.get_legacy_facade()

    return _FACADE


def get_engine():
    """Helper method to grab engine."""
    facade = _create_facade_lazily()
    return facade.get_engine()


def get_session(autocommit=True, expire_on_commit=False):
    """Helper method to grab session."""
    facade = _create_facade_lazily()
    return facade.get_session(autocommit=autocommit,
                              expire_on_commit=expire_on_commit)
