# Copyright (C) 2020 FUJITSU
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

"""change type for vnf_resources and vnf_instantiated_info table

Revision ID: aaf461c8844c
Revises: 745e3e9fe5e2
Create Date: 2020-09-17 03:17:42.570250

"""
# flake8: noqa: E402

# revision identifiers, used by Alembic.
revision = 'aaf461c8844c'
down_revision = '745e3e9fe5e2'

from alembic import op
import sqlalchemy as sa


def upgrade(active_plugins=None, options=None):
    op.alter_column('vnf_instantiated_info',
                    'instance_id',
                    type_=sa.Text(),
                    nullable=True)
    op.alter_column('vnf_resources',
                    'resource_name',
                    type_=sa.Text(),
                    nullable=True)
