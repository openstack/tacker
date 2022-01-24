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
    cfg.StrOpt(
        'endpoint_url',
        default='http://localhost:9890/',
        help="endpoint_url"),
    cfg.IntOpt(
        'subscription_num',
        default=100,
        help="Number of subscriptions"),
    cfg.IntOpt(
        'retry_num',
        default=3,
        help="Number of retry"),
    cfg.IntOpt(
        'retry_wait',
        default=10,
        help="Retry interval (sec)"),
    cfg.IntOpt(
        'retry_timeout',
        default=10,
        help="Retry timeout (sec)"),
    cfg.BoolOpt(
        'test_callback_uri',
        default=True,
        help="Test callbackUri"),
    cfg.IntOpt(
        'operation_timeout',
        default=60,
        help="LCM operation timeout (sec)"),
    cfg.BoolOpt(
        'verify_notification_ssl',
        default=True,
        help="Verify the certificate to send notification by ssl"),
    cfg.IntOpt(
        'lcm_op_occ_num',
        default=100,
        help="Number of lcm_op_occs contained in 1 page"),
    cfg.IntOpt(
        'vnf_instance_num',
        default=100,
        help="Number of vnf_instances contained in 1 page"),
    cfg.IntOpt(
        'nextpage_expiration_time',
        default=3600,
        help="Expiration time (sec) for paging")]

vnf_lcm_group = cfg.OptGroup('vnf_lcm',
    title='vnf_lcm options',
    help="Vnflcm options group")


def register_opts(conf):
    conf.register_group(vnf_lcm_group)
    conf.register_opts(OPTS, group=vnf_lcm_group)


def list_opts():
    return {vnf_lcm_group: OPTS}
