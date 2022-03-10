# Copyright 2022 OpenStack Foundation
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

"""rename the field a to b

Revision ID: 85c06a0714b7
Revises: d6ae359ab0d6
Create Date: 2022-01-14 06:25:30.427454

"""

# flake8: noqa: E402

# revision identifiers, used by Alembic.
revision = '85c06a0714b7'
down_revision = 'd6ae359ab0d6'

from alembic import op
import sqlalchemy as sa


def upgrade(active_plugins=None, options=None):

    op.alter_column('vnf_lcm_subscriptions',
                    'subscription_authentication',
                    new_column_name='authentication',
                    existing_type=sa.JSON(), nullable=True)

