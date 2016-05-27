# Copyright 2016 OpenStack Foundation
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

"""uuid consistency

Revision ID: f958f58e5daa
Revises: acf941e54075
Create Date: 2016-05-28 07:13:07.125562

"""

# revision identifiers, used by Alembic.
revision = 'f958f58e5daa'
down_revision = 'acf941e54075'


from alembic import op

from tacker.db import types


def upgrade(active_plugins=None, options=None):
    for table in ['vims', 'vimauths', 'devices', 'deviceattributes',
                  'servicetypes', 'devicetemplates',
                  'devicetemplateattributes']:
        op.alter_column(table,
                        'id',
                        type_=types.Uuid)

    for table in ['devices', 'servicetypes', 'devicetemplateattributes']:
        op.alter_column(table,
                        'template_id',
                        type_=types.Uuid)

    for table in ['devices', 'vimauths']:
        op.alter_column(table,
                        'vim_id',
                        type_=types.Uuid)

    for table in ['deviceattributes', 'proxymgmtports']:
        op.alter_column(table,
                        'device_id',
                        type_=types.Uuid)
