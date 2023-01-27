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

    bind = op.get_bind()
    engine = bind.engine
    if engine.name == 'postgresql':
        type = sa.VARCHAR(length=sql_text_length)
        operation_states = sa.Computed(
            "decode(filter->>'$.operationStates','escape')")
        operation_states_len = sa.Computed(
            "coalesce(json_array_length(filter->'$.operationStates'),0)")
        vnfd_ids = sa.Computed(
            "decode(filter->>'$.vnfdIds','escape')")
        vnfd_ids_len = sa.Computed(
            "coalesce(json_array_length(filter->'$.vnfdIds'),0)")
        vnf_provider = sa.Computed(
            "(coalesce(decode("
            "vnf_products_from_providers->>'$.vnfProvider','escape')),0)")
        vnf_product_name = sa.Computed(
            "(coalesce(decode("
            "vnf_products_from_providers->>"
            "'$.vnfProducts[0].vnfProductName','escape')),0)")
        vnf_software_version = sa.Computed(
            "(coalesce(decode("
            "vnf_products_from_providers->>'$.vnfProducts[0]"
            ".versions[0].vnfSoftwareVersion','escape')),0)")
        vnfd_versions = sa.Computed(
            "decode(vnf_products_from_providers->>"
            "'$.vnfProducts[0].versions[0].vnfdVersions','escape')")
        vnfd_versions_len = sa.Computed(
            "coalesce(json_array_length(filter->"
            "'$.vnfProducts[0].versions[0].vnfdVersions'),0)")
        vnf_instance_ids = sa.Computed(
            "decode(filter->>'$.vnfInstanceIds','escape')")
        vnf_instance_ids_len = sa.Computed(
            "coalesce(json_array_length(filter->'$.vnfInstanceIds'),0)")
        vnf_instance_names = sa.Computed(
            "decode(filter->>'$.vnfInstanceNames','escape')")
        vnf_instance_names_len = sa.Computed(
            "coalesce(json_array_length(filter->'$.vnfInstanceNames'),0)")
    else:
        type = sa.TEXT(length=sql_text_length)
        operation_states = sa.Computed(
            "json_unquote(json_extract(`filter`,'$.operationStates'))")
        operation_states_len = sa.Computed(
            "ifnull(json_length(`operation_states`),0)")
        vnfd_ids = sa.Computed(
            "json_unquote(json_extract(`filter`,'$.vnfdIds'))")
        vnfd_ids_len = sa.Computed(
            "ifnull(json_length(`vnfd_ids`),0)")
        vnf_provider = sa.Computed(
            "(ifnull(json_unquote(json_extract("
            "`vnf_products_from_providers`,'$.vnfProvider')),''))")
        vnf_product_name = sa.Computed(
            "(ifnull(json_unquote(json_extract("
            "`vnf_products_from_providers`,"
            "'$.vnfProducts[0].vnfProductName')),''))")
        vnf_software_version = sa.Computed(
            "(ifnull(json_unquote(json_extract("
            "`vnf_products_from_providers`,'$.vnfProducts[0]"
            ".versions[0].vnfSoftwareVersion')),''))")
        vnfd_versions = sa.Computed(
            "json_unquote(json_extract(`vnf_products_from_providers`,"
            "'$.vnfProducts[0].versions[0].vnfdVersions'))")
        vnfd_versions_len = sa.Computed(
            "ifnull(json_length(`vnfd_versions`),0)")
        vnf_instance_ids = sa.Computed(
            "json_unquote(json_extract(`filter`,'$.vnfInstanceIds'))")
        vnf_instance_ids_len = sa.Computed(
            "ifnull(json_length(`vnf_instance_ids`),0)")
        vnf_instance_names = sa.Computed(
            "json_unquote(json_extract(`filter`,'$.vnfInstanceNames'))")
        vnf_instance_names_len = sa.Computed(
            "ifnull(json_length(`vnf_instance_names`),0)")

    op.add_column(
        'vnf_lcm_filters',
        sa.Column(
            'vnf_products_from_providers', sa.JSON()))

    op.add_column(
        'vnf_lcm_filters',
        sa.Column(
            'operation_states', type, operation_states))

    op.add_column(
        'vnf_lcm_filters',
        sa.Column(
            'operation_states_len', sa.Integer, operation_states_len))

    op.add_column(
        'vnf_lcm_filters',
        sa.Column(
            'vnfd_ids', type, vnfd_ids))

    op.add_column(
        'vnf_lcm_filters',
        sa.Column(
            'vnfd_ids_len', sa.Integer, vnfd_ids_len))

    op.add_column(
        'vnf_lcm_filters',
        sa.Column(
            'vnf_provider', type, vnf_provider))

    op.add_column(
        'vnf_lcm_filters',
        sa.Column(
            'vnf_product_name', type, vnf_product_name))

    op.add_column(
        'vnf_lcm_filters',
        sa.Column(
            'vnf_software_version', type, vnf_software_version))

    op.add_column(
        'vnf_lcm_filters',
        sa.Column(
            'vnfd_versions', type, vnfd_versions))

    op.add_column(
        'vnf_lcm_filters',
        sa.Column(
            'vnfd_versions_len', sa.Integer, vnfd_versions_len))

    op.add_column(
        'vnf_lcm_filters',
        sa.Column(
            'vnf_instance_ids', type, vnf_instance_ids))

    op.add_column(
        'vnf_lcm_filters',
        sa.Column(
            'vnf_instance_ids_len', sa.Integer, vnf_instance_ids_len))

    op.add_column(
        'vnf_lcm_filters',
        sa.Column(
            'vnf_instance_names', type, vnf_instance_names))

    op.add_column(
        'vnf_lcm_filters',
        sa.Column(
            'vnf_instance_names_len', sa.Integer, vnf_instance_names_len))
