# Copyright 2016 Brocade Communications System, Inc.
# All Rights Reserved.
#
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

import sqlalchemy as sa
from sqlalchemy import orm
from sqlalchemy import schema
from sqlalchemy import sql

from tacker.db import model_base
from tacker.db import models_v1
from tacker.db import types


class Vim(model_base.BASE,
          models_v1.HasId,
          models_v1.HasTenant,
          models_v1.Audit):
    type = sa.Column(sa.String(64), nullable=False)
    name = sa.Column(sa.String(255), nullable=False)
    description = sa.Column(sa.Text, nullable=True)
    placement_attr = sa.Column(types.Json, nullable=True)
    shared = sa.Column(sa.Boolean, default=False, server_default=sql.false(
    ), nullable=False)
    is_default = sa.Column(sa.Boolean, default=False, server_default=sql.false(
    ), nullable=False)
    vim_auth = orm.relationship('VimAuth')
    status = sa.Column(sa.String(255), nullable=False)

    __table_args__ = (
        schema.UniqueConstraint(
            "tenant_id",
            "name",
            "deleted_at",
            name="uniq_vim0tenant_id0name0deleted_at"),
    )


class VimAuth(model_base.BASE, models_v1.HasId):
    vim_id = sa.Column(types.Uuid, sa.ForeignKey('vims.id'),
                       nullable=False)
    password = sa.Column(sa.String(255), nullable=False)
    auth_url = sa.Column(sa.String(255), nullable=False)
    vim_project = sa.Column(types.Json, nullable=False)
    auth_cred = sa.Column(types.Json, nullable=False)
