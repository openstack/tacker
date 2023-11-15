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

from tacker._i18n import _


CONF = cfg.CONF

VNFM_OPTS = [
    cfg.StrOpt('endpoint',
               default='http://127.0.0.1:9890',
               help=_('Endpoint of VNFM (self).')),
    cfg.IntOpt('default_graceful_termination_timeout',
               default=10,
               help=_('Default timeout value (second) of GRACEFUL '
                      'termination.')),
    cfg.IntOpt('max_content_length',
               default=1000000,
               help=_('Max content length for list APIs.')),
    cfg.IntOpt('openstack_vim_stack_create_timeout',
               default=20,
               help=_('Timeout (in minutes) of heat stack creation.')),
    cfg.IntOpt('kubernetes_vim_rsc_wait_timeout',
               default=500,
               help=_('Timeout (second) of k8s res creation.')),
    cfg.IntOpt('vnf_instance_page_size',
               default=0,  # 0 means no paging
               help=_('Paged response size of the query result '
                      'for VNF instances.')),
    cfg.IntOpt('subscription_page_size',
               default=0,  # 0 means no paging
               help=_('Paged response size of the query result '
                      'for Subscriptions.')),
    cfg.IntOpt('lcm_op_occ_page_size',
               default=0,  # 0 means no paging
               help=_('Paged response size of the query result '
                      'for VNF LCM operation occurrences.')),
    cfg.StrOpt('notification_mtls_ca_cert_file',
               default='',
               help=_('CA Certificate file used by OAuth2.0 mTLS '
                      'authentication.')),
    cfg.StrOpt('notification_mtls_client_cert_file',
               default='',
               help=_('Client Certificate file used by OAuth2.0 mTLS '
                      'authentication.')),
    cfg.IntOpt('notify_connect_retries',
               default=0,  # 0 means no retry
               help=_('Number of retries that should be attempted for '
                      'connection error when sending a notification. '
                      'Period between retries is exponential starting '
                      '0.5 seconds up to a maximum of 60 seconds.')),
    cfg.IntOpt('vnffm_alarm_page_size',
               default=0,  # 0 means no paging
               help=_('Paged response size of the query result '
                      'for VNF Fault Management alarm.')),
    cfg.IntOpt('vnfpm_pmthreshold_page_size',
               default=0,  # 0 means no paging
               help=_('Paged response size of the query result for '
                      'VNF PM threshold.')),
    cfg.IntOpt('vnfpm_pmjob_page_size',
               default=0,  # 0 means no paging
               help=_('Paged response size of the query result for '
                      'VNF PM job.')),
    cfg.BoolOpt('placement_fallback_best_effort',
               default=False,
               help=_('If True, fallbackBestEffort setting is enabled '
                      'and run Availability Zone reselection.')),
    cfg.IntOpt('placement_az_select_retry',
               default=0,  # 0 means unlimited number of retries
               help=_('Number of retries to reselect Availability Zone. '
                      'Default value "0" means unlimited number of retries.')),
    cfg.StrOpt('placement_az_resource_error',
               default=(r'Resource CREATE failed: ResourceInError: '
                        r'resources\.(.*)\.(.*): (.*)|'
                        r'Resource UPDATE failed: resources\.(.*): '
                        r'Resource CREATE failed: ResourceInError: '
                        r'resources\.(.*): (.*)'),
               help=_('Error message for Availability Zone reselection. '
                      'These configs are regular expressions to detect '
                      'error messages from OpenStack Heat.')),
    cfg.BoolOpt('enable_rollback_stack',
                default=False,
                help=_('If True, enable rollback stack on resource create '
                       'failure.')),
    # NOTE: This is for test use since it is convenient to be able to delete
    # under development.
    cfg.BoolOpt('test_enable_lcm_op_occ_delete',
                default=False,
                help=_('Enable to delete LCM operation occurrence if True. '
                       'This is intended to use under development.')),
    cfg.BoolOpt('notification_verify_cert',
                default=False,
                help=_('Enable certificate verification during SSL/TLS '
                       'communication to notification server.')),
    cfg.StrOpt('notification_ca_cert_file',
               default='',
               help=_('Specifies the root CA certificate to use when the '
                      'notification_verify_cert option is True.')),
    cfg.BoolOpt('use_oauth2_mtls_for_heat',
                default=False,
                help=_('Enable OAuth2.0 mTLS authentication for heat '
                       'server.')),
    cfg.StrOpt('heat_mtls_ca_cert_file',
               default='',
               help=_('CA Certificate file used by OAuth2.0 mTLS '
                      'authentication.')),
    cfg.StrOpt('heat_mtls_client_cert_file',
               default='',
               help=_('Client Certificate file used by OAuth2.0 mTLS '
                      'authentication.')),
    cfg.BoolOpt('heat_verify_cert',
                default=False,
                help=_('Enable certificate verification during SSL/TLS '
                       'communication to heat server.')),
    cfg.StrOpt('heat_ca_cert_file',
               default='',
               help=_('Specifies the root CA certificate to use when the '
                      'heat_verify_cert option is True.')),
    cfg.StrOpt('tf_file_dir',
             default='/var/lib/tacker/terraform',
             help=_('Temporary directory for Terraform infra-driver to '
                    'store terraform config files'))
]

CONF.register_opts(VNFM_OPTS, 'v2_vnfm')

NFVO_OPTS = [
    cfg.BoolOpt('use_external_nfvo',
                default=False,
                help=_('Use external NFVO if True, '
                       'use internal NFVO in tacker if False')),
    cfg.StrOpt('grant_api_version',
               default='1.4.0',  # SOL003 v3.3.1 9.1a
               help=_('Grant api_version of NFVO.')),
    cfg.StrOpt('vnfpkgm_api_version',
               default='2.1.0',  # SOL003 v3.3.1 10.1a
               help=_('Vnf package management api_version of NFVO.')),
    # The following four parameters are for external NFVO.
    # Must be set when using external NFVO.
    # NOTE: It is assumed the VNFM communicates only one NFVO. That is
    # the same NFVO provides both the grant and vnf package management APIs.
    cfg.StrOpt('endpoint',
               default='',
               help=_('Endpoint of external NFVO.')),
    cfg.StrOpt('token_endpoint',
               default='',
               help=_('Token endpoint for OAuth2.0 authentication.')),
    cfg.StrOpt('client_id',
               default='',
               help=_('Client id used by OAuth2.0 authentication.')),
    cfg.StrOpt('client_password',
               default='',
               help=_('Client password used by OAuth2.0 authentication.')),
    cfg.StrOpt('vnf_package_cache_dir',
               default='/opt/stack/data/tacker/vnf_package_cache',
               help=_('Vnf package content cache directory.')),
    cfg.StrOpt('mtls_ca_cert_file',
               default='',
               help=_('CA Certificate file used by OAuth2.0 mTLS '
                      'authentication.')),
    cfg.StrOpt('mtls_client_cert_file',
               default='',
               help=_('Client Certificate file used by OAuth2.0 mTLS '
                      'authentication.')),
    cfg.BoolOpt('test_callback_uri',
                default=True,
                help=_('Check to get notification from callback Uri.')),
    cfg.ListOpt('test_grant_zone_list',
                default=["nova"],
                help=_('Zones used for test which returned in Grant '
                       'response.')),
    cfg.BoolOpt('use_client_secret_basic',
                default=False,
                help=_('Use password authenticatiojn if True, '
                       'use certificate authentication if False.')),
    cfg.BoolOpt('nfvo_verify_cert',
                default=False,
                help=_('Enable certificate verification during SSL/TLS '
                       'communication to NFVO.')),
    cfg.StrOpt('nfvo_ca_cert_file',
               default='',
               help=_('Specifies the root CA certificate to use when the'
                      'nfvo_verify_cert option is True.'))
]

CONF.register_opts(NFVO_OPTS, 'v2_nfvo')

PROMETHEUS_PLUGIN_OPTS = [
    cfg.BoolOpt('performance_management',
                default=False,
                help=_('Enable prometheus plugin performance management')),
    cfg.IntOpt('reporting_period_margin',
               default=1,
               help=_('Some margin time for PM jos\'s reportingPeriod')),
    cfg.BoolOpt('fault_management',
                default=False,
                help=_('Enable prometheus plugin fault management')),
    cfg.BoolOpt('auto_healing',
                default=False,
                help=_('Enable prometheus plugin autohealing')),
    cfg.BoolOpt('auto_scaling',
                default=False,
                help=_('Enable prometheus plugin autoscaling')),
    cfg.StrOpt('performance_management_package',
               default='tacker.sol_refactored.common.prometheus_plugin',
               help=_('Package name for performance management PMJob. '
                      'This configuration is changed in case of replacing '
                      'the original function with a vendor specific '
                      'function.')),
    cfg.StrOpt('performance_management_threshold_package',
               default='tacker.sol_refactored.common.prometheus_plugin',
               help=_('Package name for performance management threshold. '
                      'This configuration is changed in case of replacing '
                      'the original function with a vendor specific '
                      'function.')),
    cfg.StrOpt('performance_management_class',
               default='PrometheusPluginPm',
               help=_('Class name for performance management PMJob. '
                      'This configuration is changed in case of replacing '
                      'the original function with a vendor specific '
                      'function.')),
    cfg.StrOpt('performance_management_threshold_class',
               default='PrometheusPluginThreshold',
               help=_('Class name for performance management threshold. '
                      'This configuration is changed in case of replacing '
                      'the original function with a vendor specific '
                      'function.')),
    cfg.StrOpt('fault_management_package',
               default='tacker.sol_refactored.common.prometheus_plugin',
               help=_('Package name for fault management. '
                      'This configuration is changed in case of replacing '
                      'the original function with a vendor specific '
                      'function.')),
    cfg.StrOpt('fault_management_class',
               default='PrometheusPluginFm',
               help=_('Class name for fault management. '
                      'This configuration is changed in case of replacing '
                      'the original function with a vendor specific '
                      'function.')),
    cfg.StrOpt('auto_healing_package',
               default='tacker.sol_refactored.common.prometheus_plugin',
               help=_('Package name for auto healing. '
                      'This configuration is changed in case of replacing '
                      'the original function with a vendor specific '
                      'function.')),
    cfg.StrOpt('auto_healing_class',
               default='PrometheusPluginAutoHealing',
               help=_('Class name for auto healing. '
                      'This configuration is changed in case of replacing '
                      'the original function with a vendor specific '
                      'function.')),
    cfg.IntOpt('timer_interval',
               default=20,
               help=_('Timeout (second) of packing for multiple '
                      'auto healing.')),
    cfg.StrOpt('auto_scaling_package',
               default='tacker.sol_refactored.common.prometheus_plugin',
               help=_('Package name for auto scaling. '
                      'This configuration is changed in case of replacing '
                      'the original function with a vendor specific '
                      'function.')),
    cfg.StrOpt('auto_scaling_class',
               default='PrometheusPluginAutoScaling',
               help=_('Class name for auto scaling. '
                      'This configuration is changed in case of replacing '
                      'the original function with a vendor specific '
                      'function.')),
    cfg.BoolOpt('test_rule_with_promtool',
                default=False,
                help=_('Enable rule file validation using promtool.')),
    cfg.IntOpt('reporting_period_threshold',
               default=90,
               help=_('The time of reportingPeriod for the PM Threshold. '
                      'If there is a PromQL '
                      'that requires `reporting_period`, '
                      'it is read from the configuration file. '
                      'The unit shall be seconds.')),
    cfg.IntOpt('collection_period_threshold',
               default=30,
               help=_('The time of collectionPeriod for the PM threshold. '
                      'If there is a PromQL '
                      'that requires `collection_period`, '
                      'it is read from the configuration file. '
                      'The unit shall be seconds.')),
]

CONF.register_opts(PROMETHEUS_PLUGIN_OPTS, 'prometheus_plugin')

SERVER_NOTIFICATION_OPTS = [
    cfg.BoolOpt('server_notification',
                default=False,
                help=_('Enable server notification autohealing')),
    cfg.StrOpt('uri_path_prefix',
               default='/server_notification',
               help=_('Uri path prefix string for server notification. '
                      'When changing this configuration, '
                      'server_notification description in api-paste.ini '
                      'must be changed to the same value.')),
    cfg.IntOpt('timer_interval',
               default=20,
               help=_('Timeout (second) of packing for multiple '
                      'server notification.')),
    cfg.StrOpt('server_notification_package',
               default='tacker.sol_refactored.common.server_notification',
               help=_('Package name for server notification. '
                      'This configuration is changed in case of replacing '
                      'the original function with a vendor specific '
                      'function.')),
    cfg.StrOpt('server_notification_class',
               default='ServerNotification',
               help=_('Class name for server notification. '
                      'This configuration is changed in case of replacing '
                      'the original function with a vendor specific '
                      'function.')),
]

CONF.register_opts(SERVER_NOTIFICATION_OPTS, 'server_notification')


def config_opts():
    return [('v2_nfvo', NFVO_OPTS),
            ('v2_vnfm', VNFM_OPTS),
            ('prometheus_plugin', PROMETHEUS_PLUGIN_OPTS),
            ('server_notification', SERVER_NOTIFICATION_OPTS)]
