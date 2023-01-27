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

# flake8: noqa: E402

"""change_vnf_filter_column_definition

Revision ID: df26c5871f3c
Revises: 329cd1619d41
Create Date: 2020-11-13 18:32:46.703342

"""

# revision identifiers, used by Alembic.
revision = 'df26c5871f3c'
down_revision = '329cd1619d41'

from alembic import op
import sqlalchemy as sa


from tacker.db import migration


def upgrade(active_plugins=None, options=None):
    # This migration file is to change syntax of "GENERATED ALWAYS AS"
    # from 'filter' to `filter`

    # TODO(esto-aln): (1) Need to fix SQL statement such that "mediumblob"
    # is used instead of "text". Currently, "text" is used as a workaround.
    # (2) Need to fix SQL statement to utilize sqlalchemy. Currently, we
    # use raw SQL with op.exec as a workaround since op.alter_column does
    # not work correctly.
    bind = op.get_bind()
    engine = bind.engine
    if engine.name == 'postgresql':
        alter_sql_notification_types_drop = "ALTER TABLE vnf_lcm_filters \
            DROP COLUMN notification_types;"

        alter_sql_notification_types_add = "ALTER TABLE vnf_lcm_filters ADD \
            COLUMN notification_types text GENERATED \
            ALWAYS AS (decode(filter->>\
            '$.notificationTypes','escape')) STORED;"

        alter_sql_notification_types_len_drop = "ALTER TABLE vnf_lcm_filters \
            DROP COLUMN notification_types_len;"

        alter_sql_notification_types_len_add = "ALTER TABLE vnf_lcm_filters \
            ADD COLUMN notification_types_len numeric(11) GENERATED \
            ALWAYS AS (coalesce(json_array_length(filter->\
            '$.notificationTypes'),0)) STORED;"

        alter_sql_operation_types_drop = "ALTER TABLE vnf_lcm_filters DROP \
            COLUMN operation_types;"

        alter_sql_operation_types_add = "ALTER TABLE vnf_lcm_filters ADD \
            COLUMN operation_types text GENERATED \
            ALWAYS AS (decode(filter->>\
            '$.operationTypes','escape')) STORED;"

        alter_sql_operation_types_len_drop = "ALTER TABLE vnf_lcm_filters \
            DROP COLUMN operation_types_len;"

        alter_sql_operation_types_len_add = "ALTER TABLE vnf_lcm_filters ADD \
            COLUMN operation_types_len numeric(11) GENERATED \
            ALWAYS AS (coalesce(json_array_length(filter->\
            '$.operationTypes'),0)) STORED;"

        op.execute(alter_sql_notification_types_drop)
        op.execute(alter_sql_notification_types_add)
        op.execute(alter_sql_notification_types_len_drop)
        op.execute(alter_sql_notification_types_len_add)
        op.execute(alter_sql_operation_types_drop)
        op.execute(alter_sql_operation_types_add)
        op.execute(alter_sql_operation_types_len_drop)
        op.execute(alter_sql_operation_types_len_add)

    else:
        alter_sql_notification_types = "ALTER TABLE vnf_lcm_filters CHANGE \
            notification_types notification_types text GENERATED \
            ALWAYS AS (json_unquote(json_extract(`filter`,\
            '$.notificationTypes'))) VIRTUAL;"

        alter_sql_notification_types_len = "ALTER TABLE vnf_lcm_filters \
            CHANGE notification_types_len notification_types_len int(11) \
            GENERATED ALWAYS AS \
            (ifnull(json_length(`notification_types`),0)) VIRTUAL;"

        alter_sql_operation_types = "ALTER TABLE vnf_lcm_filters CHANGE \
            operation_types operation_types text GENERATED ALWAYS AS \
            (json_unquote(json_extract(`filter`,'$.operationTypes'))) \
            VIRTUAL;"

        alter_sql_operation_types_len = "ALTER TABLE vnf_lcm_filters CHANGE \
            operation_types_len operation_types_len int(11) GENERATED ALWAYS \
            AS (ifnull(json_length(`operation_types`),0)) VIRTUAL;"

        op.execute(alter_sql_notification_types)
        op.execute(alter_sql_notification_types_len)
        op.execute(alter_sql_operation_types)
        op.execute(alter_sql_operation_types_len)
