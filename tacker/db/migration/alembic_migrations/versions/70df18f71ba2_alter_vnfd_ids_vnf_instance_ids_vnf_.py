# Copyright 2021 OpenStack Foundation
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

"""alter vnfd_ids, vnf_instance_ids, vnf_instance_names
columns of vnf_lcm_filters

Revision ID: 70df18f71ba2
Revises: a23ebee909a8
Create Date: 2021-06-16 14:26:51.998033

"""

# revision identifiers, used by Alembic.
revision = '70df18f71ba2'
down_revision = 'a23ebee909a8'

from alembic import op  # noqa: E402


def upgrade(active_plugins=None, options=None):
    alter_sql_vnfd_ids = "ALTER TABLE vnf_lcm_filters CHANGE \
            vnfd_ids vnfd_ids mediumtext GENERATED ALWAYS AS \
            (json_unquote(json_extract(`filter`, \
            '$.vnfInstanceSubscriptionFilter.vnfdIds'))) VIRTUAL;"

    alter_sql_vnf_instance_ids = "ALTER TABLE vnf_lcm_filters CHANGE \
            vnf_instance_ids vnf_instance_ids mediumtext GENERATED ALWAYS AS \
            (json_unquote(json_extract(`filter`, \
            '$.vnfInstanceSubscriptionFilter.vnfInstanceIds'))) VIRTUAL;"

    alter_sql_vnf_instance_names = "ALTER TABLE vnf_lcm_filters CHANGE \
                vnf_instance_names vnf_instance_names mediumtext GENERATED \
                ALWAYS AS (json_unquote(json_extract(`filter`, \
                '$.vnfInstanceSubscriptionFilter.vnfInstanceNames'))) \
                VIRTUAL;"

    op.execute(alter_sql_vnfd_ids)
    op.execute(alter_sql_vnf_instance_ids)
    op.execute(alter_sql_vnf_instance_names)
