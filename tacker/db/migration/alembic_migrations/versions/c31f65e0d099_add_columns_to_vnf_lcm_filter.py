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

"""Add columns to vnf_lcm_filter

Revision ID: c31f65e0d099
Revises: 3adac34764da
Create Date: 2021-02-03 22:53:36.352774

"""


from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c31f65e0d099'
down_revision = '3adac34764da'


def upgrade(active_plugins=None, options=None):
    sql_text_length = 65535

    op.add_column(
        'vnf_lcm_filters',
        sa.Column(
            'vnf_products_from_providers', sa.JSON()))

    op.add_column(
        'vnf_lcm_filters',
        sa.Column(
            'operation_states', sa.TEXT(length=sql_text_length),
            sa.Computed(
                "json_unquote(json_extract(`filter`,'$.operationStates'))")))

    op.add_column(
        'vnf_lcm_filters',
        sa.Column(
            'operation_states_len', sa.Integer,
            sa.Computed(
                "ifnull(json_length(`operation_states`),0)")))

    op.add_column(
        'vnf_lcm_filters',
        sa.Column(
            'vnfd_ids', sa.TEXT(length=sql_text_length),
            sa.Computed(
                "json_unquote(json_extract(`filter`,'$.vnfdIds'))")))

    op.add_column(
        'vnf_lcm_filters',
        sa.Column(
            'vnfd_ids_len', sa.Integer,
            sa.Computed(
                "ifnull(json_length(`vnfd_ids`),0)")))

    op.add_column(
        'vnf_lcm_filters',
        sa.Column(
            'vnf_provider', sa.TEXT(length=sql_text_length),
            sa.Computed(
                "(ifnull(json_unquote(json_extract("
                "`vnf_products_from_providers`,'$.vnfProvider')),''))")))

    op.add_column(
        'vnf_lcm_filters',
        sa.Column(
            'vnf_product_name', sa.TEXT(length=sql_text_length),
            sa.Computed(
                "(ifnull(json_unquote(json_extract("
                "`vnf_products_from_providers`,"
                "'$.vnfProducts[0].vnfProductName')),''))")))

    op.add_column(
        'vnf_lcm_filters',
        sa.Column(
            'vnf_software_version', sa.TEXT(length=sql_text_length),
            sa.Computed(
                "(ifnull(json_unquote(json_extract("
                "`vnf_products_from_providers`,'$.vnfProducts[0]"
                ".versions[0].vnfSoftwareVersion')),''))")))

    op.add_column(
        'vnf_lcm_filters',
        sa.Column(
            'vnfd_versions', sa.TEXT(length=sql_text_length),
            sa.Computed(
                "json_unquote(json_extract(`vnf_products_from_providers`,"
                "'$.vnfProducts[0].versions[0].vnfdVersions'))")))

    op.add_column(
        'vnf_lcm_filters',
        sa.Column(
            'vnfd_versions_len', sa.Integer,
            sa.Computed(
                "ifnull(json_length(`vnfd_versions`),0)")))

    op.add_column(
        'vnf_lcm_filters',
        sa.Column(
            'vnf_instance_ids', sa.TEXT(length=sql_text_length),
            sa.Computed(
                "json_unquote(json_extract(`filter`,'$.vnfInstanceIds'))")))

    op.add_column(
        'vnf_lcm_filters',
        sa.Column(
            'vnf_instance_ids_len', sa.Integer,
            sa.Computed(
                "ifnull(json_length(`vnf_instance_ids`),0)")))

    op.add_column(
        'vnf_lcm_filters',
        sa.Column(
            'vnf_instance_names', sa.TEXT(length=sql_text_length),
            sa.Computed(
                "json_unquote(json_extract(`filter`,'$.vnfInstanceNames'))")))

    op.add_column(
        'vnf_lcm_filters',
        sa.Column(
            'vnf_instance_names_len', sa.Integer,
            sa.Computed(
                "ifnull(json_length(`vnf_instance_names`),0)")))
