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

from oslo_utils import timeutils
from oslo_utils import uuidutils
import sqlalchemy as sa

from tacker.db import types


class HasTenant(object):
    """Tenant mixin, add to subclasses that have a tenant."""

    tenant_id = sa.Column(sa.String(64), nullable=False)


class HasId(object):
    """id mixin, add to subclasses that have an id."""

    id = sa.Column(types.Uuid,
                   primary_key=True,
                   default=uuidutils.generate_uuid)


class Audit(object):
    """Helps to add time stamp for create, update and delete actions. """

    created_at = sa.Column(sa.DateTime,
                           default=lambda: timeutils.utcnow())
    updated_at = sa.Column(sa.DateTime)
    deleted_at = sa.Column(sa.DateTime)
