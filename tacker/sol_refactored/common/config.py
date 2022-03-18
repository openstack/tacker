# Copyright (C) 2021 Nippon Telegraph and Telephone Corporation
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

VNFM_OPTS = [
    cfg.StrOpt('endpoint',
               default='http://127.0.0.1:9890',
               help='Endpoint of VNFM (self).'),
    cfg.IntOpt('default_graceful_termination_timeout',
               default=10,
               help='Default timeout value (second) of GRACEFUL termination.'),
    cfg.IntOpt('max_content_length',
               default=1000000,
               help='Max content length for list APIs.'),
    cfg.IntOpt('openstack_vim_stack_create_timeout',
               default=20,
               help='Timeout (in minuts) of heat stack creation.'),
    cfg.IntOpt('kubernetes_vim_rsc_wait_timeout',
               default=500,
               help='Timeout (second) of k8s res creation.'),
    # NOTE: This is for test use since it is convenient to be able to delete
    # under development.
    cfg.BoolOpt('test_enable_lcm_op_occ_delete',
                default=False,
                help=_('Enable to delete LCM operation occurrence if True. '
                       'This is intended to use under development.')),
]

CONF.register_opts(VNFM_OPTS, 'v2_vnfm')

NFVO_OPTS = [
    cfg.BoolOpt('use_external_nfvo',
                default=False,
                help=_('Use external NFVO if True, '
                       'use internal NFVO in tacker if False')),
    cfg.StrOpt('grant_api_version',
               default='1.4.0',  # SOL003 v3.3.1 9.1a
               help='Grant api_version of NFVO.'),
    cfg.StrOpt('vnfpkgm_api_version',
               default='2.1.0',  # SOL003 v3.3.1 10.1a
               help='Vnf package management api_version of NFVO.'),
    # The following four parameters are for external NFVO.
    # Must be set when using external NFVO.
    # NOTE: It is assumed the VNFM communicates only one NFVO. That is
    # the same NFVO provides both the grant and vnf package management APIs.
    cfg.StrOpt('endpoint',
               default='',
               help='Endpoint of external NFVO.'),
    cfg.StrOpt('token_endpoint',
               default='',
               help='Token endpoint for OAuth2.0 authentication.'),
    cfg.StrOpt('client_id',
               default='',
               help='Client id used by OAuth2.0 authentication.'),
    cfg.StrOpt('client_password',
               default='',
               help='Client password used by OAuth2.0 authentication.'),
    cfg.BoolOpt('test_callback_uri',
                default=True,
                help='Check to get notification from callback Uri.'),
    cfg.ListOpt('test_grant_zone_list',
                default=["nova"],
                help='Zones used for test which returned in Grant response.')
]

CONF.register_opts(NFVO_OPTS, 'v2_nfvo')


def config_opts():
    return [('v2_nfvo', NFVO_OPTS),
            ('v2_vnfm', VNFM_OPTS)]
