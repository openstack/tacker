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
        help="Retry interval(sec)")]

vnf_lcm_group = cfg.OptGroup('vnf_lcm',
    title='vnf_lcm options',
    help="Vnflcm options group")


def register_opts(conf):
    conf.register_group(vnf_lcm_group)
    conf.register_opts(OPTS, group=vnf_lcm_group)


def list_opts():
    return {vnf_lcm_group: OPTS}
