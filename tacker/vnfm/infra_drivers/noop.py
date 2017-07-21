# Copyright 2013, 2014 Intel Corporation.
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

# TODO(yamahata): once unittests are impletemted, move this there
from oslo_log import log as logging
from oslo_utils import uuidutils

from tacker.common import log
from tacker.vnfm.infra_drivers import abstract_driver


LOG = logging.getLogger(__name__)


class DeviceNoop(abstract_driver.DeviceAbstractDriver):

    """Noop driver of hosting vnf for tests."""

    def __init__(self):
        super(DeviceNoop, self).__init__()
        self._instances = set()

    def get_type(self):
        return 'noop'

    def get_name(self):
        return 'noop'

    def get_description(self):
        return 'Tacker infra noop driver'

    @log.log
    def create(self, **kwargs):
        instance_id = uuidutils.generate_uuid()
        self._instances.add(instance_id)
        return instance_id

    @log.log
    def create_wait(self, plugin, context, vnf_dict, vnf_id):
        pass

    @log.log
    def update(self, plugin, context, vnf_id, vnf_dict, vnf):
        if vnf_id not in self._instances:
            LOG.debug('not found')
            raise ValueError('No instance %s' % vnf_id)

    @log.log
    def update_wait(self, plugin, context, vnf_id):
        pass

    @log.log
    def delete(self, plugin, context, vnf_id):
        self._instances.remove(vnf_id)

    @log.log
    def delete_wait(self, plugin, context, vnf_id):
        pass

    def get_resource_info(self, plugin, context, vnf_info, auth_attr,
                          region_name=None):
        return {'noop': {'id': uuidutils.generate_uuid(), 'type': 'noop'}}
