# Copyright 2012 OpenStack Foundation.
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

"""Context: context for security/db session."""

import copy
import datetime

from castellan.common.credentials import keystone_password
from oslo_config import cfg
from oslo_context import context as oslo_context
from oslo_db.sqlalchemy import enginefacade

from tacker.common import exceptions
from tacker.db import api as db_api
from tacker import policy

CONF = cfg.CONF


class ContextBase(oslo_context.RequestContext):
    """Security context and request information.

    Represents the user taking a given action within the system.

    """

    def __init__(self, user_id=None, tenant_id=None, is_admin=None,
                 timestamp=None, tenant_name=None, user_name=None,
                 is_advsvc=None, **kwargs):
        # NOTE(jamielennox): We maintain this argument in order for tests that
        # pass arguments positionally.
        kwargs.setdefault('project_id', tenant_id)
        # prefer project_name, as that's what's going to be set by
        # keystone. Fall back to tenant_name if for some reason it's blank.
        kwargs.setdefault('project_name', tenant_name)
        super(ContextBase, self).__init__(
            is_admin=is_admin, user_id=user_id, **kwargs)

        self.user_name = user_name

        if not timestamp:
            timestamp = datetime.datetime.utcnow()
        self.timestamp = timestamp
        # self.is_advsvc = is_advsvc
        # if self.is_advsvc is None:
        #     self.is_advsvc = self.is_admin or policy.check_is_advsvc(self)
        if self.is_admin is None:
            self.is_admin = policy.check_is_admin(self)

    @property
    def tenant_id(self):
        return self.project_id

    @tenant_id.setter
    def tenant_id(self, tenant_id):
        self.project_id = tenant_id

    @property
    def tenant_name(self):
        return self.project_name

    @tenant_name.setter
    def tenant_name(self, tenant_name):
        self.project_name = tenant_name

    def to_dict(self):
        context = super(ContextBase, self).to_dict()
        context.update({
            'user_id': self.user_id,
            'tenant_id': self.tenant_id,
            'project_id': self.project_id,
            'timestamp': str(self.timestamp),
            'tenant_name': self.tenant_name,
            'project_name': self.tenant_name,
            'user_name': self.user_name,
        })
        return context

    @classmethod
    def from_dict(cls, values):
        return cls(user_id=values.get('user_id'),
                   tenant_id=values.get('tenant_id', values.get('project_id')),
                   is_admin=values.get('is_admin'),
                   roles=values.get('roles'),
                   timestamp=values.get('timestamp'),
                   request_id=values.get('request_id'),
                   tenant_name=values.get('tenant_name'),
                   user_name=values.get('user_name'),
                   auth_token=values.get('auth_token'))

    def to_policy_values(self):
        values = super(ContextBase, self).to_policy_values()
        values['tenant_id'] = self.project_id
        values['is_admin'] = self.is_admin

        # NOTE(jamielennox): These are almost certainly unused and non-standard
        # but kept for backwards compatibility. Remove them in Pike
        # (oslo.context from Ocata release already issues deprecation warnings
        # for non-standard keys).
        values['user_id'] = self.user_id
        values['project_id'] = self.project_id
        values['domain'] = self.domain_id
        values['user_domain'] = self.user_domain_id
        values['project_domain'] = self.project_domain_id
        values['tenant_name'] = self.project_name
        values['project_name'] = self.project_name
        values['user_name'] = self.user_name

        return values

    def elevated(self):
        """Return a version of this context with admin flag set."""
        context = copy.copy(self)
        context.is_admin = True

        if 'admin' not in [x.lower() for x in context.roles]:
            context.roles = context.roles + ["admin"]

        return context

    def can(self, action, target=None, fatal=True):
        """Verifies that the given action is valid on the target in this context.

        :param action: string representing the action to be checked.
        :param target: dictionary representing the object of the action
            for object creation this should be a dictionary representing the
            location of the object e.g. ``{'project_id': context.project_id}``.
            If None, then this default target will be considered:
            {'project_id': self.project_id, 'user_id': self.user_id}
        :param fatal: if False, will return False when an exception.Forbidden
           occurs.

        :raises tacker.exception.Forbidden: if verification fails and fatal
            is True.

        :return: returns a non-False value (not necessarily "True") if
            authorized and False if not authorized and fatal is False.
        """
        if target is None:
            target = {'tenant_id': self.tenant_id,
                      'user_id': self.user_id}
        try:
            return policy.authorize(self, action, target)
        except exceptions.Forbidden:
            if fatal:
                raise
            return False


@enginefacade.transaction_context_provider
class ContextBaseWithSession(ContextBase):
    pass


class Context(ContextBaseWithSession):
    def __init__(self, *args, **kwargs):
        super(Context, self).__init__(*args, **kwargs)
        self._session = None

    @property
    def session(self):
        # TODO(akamyshnikova): checking for session attribute won't be needed
        # when reader and writer will be used
        if hasattr(super(Context, self), 'session'):
            return super(Context, self).session
        if self._session is None:
            self._session = db_api.get_session()
        return self._session


def get_admin_context():
    return Context(user_id=None,
                   tenant_id=None,
                   is_admin=True,
                   overwrite=False)


def get_admin_context_without_session():
    return ContextBase(user_id=None,
                       tenant_id=None,
                       is_admin=True)


def is_user_context(context):
    """Indicates if the request context is a normal user."""
    if not context:
        return False
    if context.is_admin:
        return False
    if not context.user_id or not context.project_id:
        return False
    return True


def generate_tacker_service_context():
    return keystone_password.KeystonePassword(
        password=CONF.keystone_authtoken.password,
        auth_url=CONF.keystone_authtoken.auth_url,
        username=CONF.keystone_authtoken.username,
        user_domain_name=CONF.keystone_authtoken.user_domain_name,
        project_name=CONF.keystone_authtoken.project_name,
        project_domain_name=CONF.keystone_authtoken.project_domain_name)
