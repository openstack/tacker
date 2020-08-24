# Copyright (C) 2019 NTT DATA
# All Rights Reserved.
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

from oslo_config import cfg


CONF = cfg.CONF

OPTS = [
    cfg.StrOpt('vnf_package_csar_path',
               default='/var/lib/tacker/vnfpackages/',
               help="Path to store extracted CSAR file"),

    cfg.FloatOpt('csar_file_size_cap', default=1024, min=0.000001,
               max=9223372036,
               help=_("""
Maximum size of CSAR file a user can upload in GB.

An CSAR file upload greater than the size mentioned here would result
in an CSAR upload failure. This configuration option defaults to
1024 GB (1 TiB).

NOTES:
    * This value should only be increased after careful
      consideration and must be set less than or equal to
      8 EiB (~9223372036).
    * This value must be set with careful consideration of the
      backend storage capacity. Setting this to a very low value
      may result in a large number of image failures. And, setting
      this to a very large value may result in faster consumption
      of storage. Hence, this must be set according to the nature of
      images created and storage capacity available.

Possible values:
    * Any positive number less than or equal to 9223372036854775808
""")),
    cfg.StrOpt('hashing_algorithm',
               default='sha512',
               help=_("""
Secure hashing algorithm used for computing the 'hash' property.

Possible values:
    * sha256, sha512

Related options:
    * None
""")),

    cfg.ListOpt('get_top_list',
                default=['tosca_definitions_version',
                    'description', 'metadata'],
                help=_("List of items to get from top-vnfd")),

    cfg.ListOpt('exclude_node',
                default=['VNF'],
                help=_("Exclude node from node_template")),

    cfg.ListOpt('get_lower_list',
                default=['tosca.nodes.nfv.VNF', 'tosca.nodes.nfv.VDU.Tacker'],
                help=_("List of types to get from lower-vnfd")),

    cfg.ListOpt('del_input_list',
                default=['descriptor_id', 'descriptor_version'
                'provider', 'product_name', 'software_version',
                'vnfm_info', 'flavour_id', 'flavour_description'],
                help=_("List of del inputs from lower-vnfd")),

]

vnf_package_group = cfg.OptGroup('vnf_package',
    title='vnf_package options',
    help="""
Options under this group are used to store vnf packages in glance store.
""")


def register_opts(conf):
    conf.register_group(vnf_package_group)
    conf.register_opts(OPTS, group=vnf_package_group)


def list_opts():
    return {vnf_package_group: OPTS}
