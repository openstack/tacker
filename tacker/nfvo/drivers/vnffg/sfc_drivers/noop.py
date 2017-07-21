# Copyright 2016 Red Hat Inc
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

from oslo_log import log as logging
from oslo_utils import uuidutils
from tacker.common import log
from tacker.nfvo.drivers.vnffg import abstract_vnffg_driver

LOG = logging.getLogger(__name__)


class VNFFGNoop(abstract_vnffg_driver.VnffgAbstractDriver):

    """Noop driver for VNFFG tests"""

    def __init__(self):
        super(VNFFGNoop, self).__init__()
        self._instances = set()

    def get_type(self):
        return 'noop'

    def get_name(self):
        return 'noop'

    def get_description(self):
        return 'VNFFG Noop driver'

    @log.log
    def create_chain(self, name, fc_id, vnfs, auth_attr=None):
        instance_id = uuidutils.generate_uuid()
        self._instances.add(instance_id)
        return instance_id

    @log.log
    def update_chain(self, chain_id, fc_ids, vnfs, auth_attr=None):
        if chain_id not in self._instances:
            LOG.debug('Chain not found')
            raise ValueError('No chain instance %s' % chain_id)

    @log.log
    def delete_chain(self, chain_id, auth_attr=None):
        self._instances.remove(chain_id)

    @log.log
    def create_flow_classifier(self, name, fc, auth_attr=None):
        instance_id = uuidutils.generate_uuid()
        self._instances.add(instance_id)
        return instance_id

    @log.log
    def update_flow_classifier(self, fc_id, fc, auth_attr=None):
        if fc_id not in self._instances:
            LOG.debug('FC not found')
            raise ValueError('No FC instance %s' % fc_id)

    @log.log
    def delete_flow_classifier(self, fc_id, auth_attr=None):
        self._instances.remove(fc_id)
