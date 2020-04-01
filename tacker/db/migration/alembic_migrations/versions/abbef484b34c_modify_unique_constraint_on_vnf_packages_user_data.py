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

"""modify_unique_constraint_on_vnf_packages_user_data

Revision ID: abbef484b34c
Revises: 9d425296f2c3
Create Date: 2019-11-18 19:34:26.853715

"""

# revision identifiers, used by Alembic.
revision = 'abbef484b34c'
down_revision = '9d425296f2c3'

from alembic import op  # noqa: E402


def upgrade(active_plugins=None, options=None):
    op.drop_constraint(
        constraint_name='uniq_vnf_packages_user_data0idid0key0deleted',
        table_name='vnf_packages_user_data',
        type_='unique')

    op.create_unique_constraint(
        constraint_name='uniq_vnf_packages_user_data0package_uuid0key0deleted',
        table_name='vnf_packages_user_data',
        columns=['package_uuid', 'key', 'deleted'])
