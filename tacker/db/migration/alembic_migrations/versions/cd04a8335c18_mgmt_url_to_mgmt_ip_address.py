# Copyright 2019 OpenStack Foundation
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

"""mgmt_url to mgmt_ip_address

Revision ID: cd04a8335c18
Revises: 13ecc2dd6f7f
Create Date: 2019-01-25 13:43:10.499421

"""

# flake8: noqa: E402

# revision identifiers, used by Alembic.
revision = 'cd04a8335c18'
down_revision = '13ecc2dd6f7f'

from alembic import op
import sqlalchemy as sa


def upgrade(active_plugins=None, options=None):
    op.alter_column('ns',
        'mgmt_urls', new_column_name='mgmt_ip_addresses',
        existing_type=sa.TEXT(65535), nullable=True)
    op.alter_column('vnf',
        'mgmt_url', new_column_name='mgmt_ip_address',
        existing_type=sa.String(255), nullable=True)
