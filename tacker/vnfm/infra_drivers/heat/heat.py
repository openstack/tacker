# Copyright 2015 Intel Corporation.
# All Rights Reserved.
#
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
from oslo_log import log as logging
from oslo_log import versionutils

from tacker.vnfm.infra_drivers.openstack import openstack


LOG = logging.getLogger(__name__)
CONF = cfg.CONF

OPTS = [
    cfg.IntOpt('stack_retries',
               default=60,
               help=_("Number of attempts to retry for stack"
                      " creation/deletion")),
    cfg.IntOpt('stack_retry_wait',
               default=5,
               help=_("Wait time (in seconds) between consecutive stack"
                      " create/delete retries")),
    cfg.DictOpt('flavor_extra_specs',
               default={},
               help=_("Flavor Extra Specs")),
]

CONF.register_opts(OPTS, group='tacker_heat')


def config_opts():
    return [('tacker_heat', OPTS)]


class DeviceHeat(openstack.OpenStack):
    """Heat driver of hosting vnf."""

    @versionutils.deprecated(
        versionutils.deprecated.NEWTON,
        what='infra_driver heat',
        in_favor_of='infra_driver openstack',
        remove_in=+1)
    def __init__(self):
        super(DeviceHeat, self).__init__()
        self.STACK_RETRIES = cfg.CONF.tacker_heat.stack_retries
        self.STACK_RETRY_WAIT = cfg.CONF.tacker_heat.stack_retry_wait
        self.STACK_FLAVOR_EXTRA = cfg.CONF.tacker_heat.flavor_extra_specs

    def get_type(self):
        return 'heat'

    def get_name(self):
        return 'heat'

    def get_description(self):
        return 'Heat infra driver'
