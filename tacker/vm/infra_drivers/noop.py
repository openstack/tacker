# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright 2013, 2014 Intel Corporation.
# Copyright 2013, 2014 Isaku Yamahata <isaku.yamahata at intel com>
#                                     <isaku.yamahata at gmail com>
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
import uuid

from tacker.common import log
from tacker.openstack.common import log as logging
from tacker.vm.infra_drivers import abstract_driver


LOG = logging.getLogger(__name__)


class DeviceNoop(abstract_driver.DeviceAbstractDriver):

    """Noop driver of hosting device for tests."""

    def __init__(self):
        super(DeviceNoop, self).__init__()
        self._instances = set()

    def get_type(self):
        return 'noop'

    def get_name(self):
        return 'noop'

    def get_description(self):
        return 'Nuetron Device Noop driver'

    @log.log
    def create(self, **kwargs):
        instance_id = str(uuid.uuid4())
        self._instances.add(instance_id)
        return instance_id

    @log.log
    def create_wait(self, plugin, context, device_dict, device_id):
        pass

    @log.log
    def update(self, plugin, context, device_id, device_dict, device):
        if device_id not in self._instances:
            LOG.debug(_('not found'))
            raise ValueError('No instance %s' % device_id)

    @log.log
    def update_wait(self, plugin, context, device_id):
        pass

    @log.log
    def delete(self, plugin, context, device_id):
        self._instances.remove(device_id)

    @log.log
    def delete_wait(self, plugin, context, device_id):
        pass
