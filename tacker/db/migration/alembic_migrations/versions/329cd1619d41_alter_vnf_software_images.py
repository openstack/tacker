# Copyright 2020 OpenStack Foundation
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

"""alter min_ram, min_disk columns of vnf_software_images

Revision ID: 329cd1619d41
Revises: d25c7c865ce8
Create Date: 2020-05-28 03:54:52.871841

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '329cd1619d41'
down_revision = 'd25c7c865ce8'


def upgrade(active_plugins=None, options=None):
    op.alter_column('vnf_software_images',
                    'min_disk',
                    type_=sa.BigInteger)
    op.alter_column('vnf_software_images',
                    'min_ram',
                    type_=sa.BigInteger)
