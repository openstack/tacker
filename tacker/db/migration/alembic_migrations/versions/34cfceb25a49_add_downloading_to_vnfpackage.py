# Copyright 2023 OpenStack Foundation
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

"""add_downloading_to_vnfPackage

Revision ID: 34cfceb25a49
Revises: 2531c976c0f1
Create Date: 2023-03-08 01:56:40.134793

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '34cfceb25a49'
down_revision = '2531c976c0f1'


def upgrade(active_plugins=None, options=None):
    op.add_column('vnf_packages', sa.Column('downloading', sa.Integer(),
                                           nullable=False,
                                           server_default='0'))
