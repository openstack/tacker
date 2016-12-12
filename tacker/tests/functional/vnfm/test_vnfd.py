# Copyright 2015 Brocade Communications System, Inc.
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

from tacker.plugins.common import constants as evt_constants
from tacker.tests.functional import base
from tacker.tests.utils import read_file

CONF = cfg.CONF


class VnfdTestCreate(base.BaseTackerTest):
    def _test_create_list_delete_vnfd(self, vnfd_file):
        data = dict()
        data['tosca'] = read_file(vnfd_file)
        toscal = data['tosca']
        vnfd_name = 'sample_cirros_vnf'
        tosca_arg = {'vnfd': {'name': vnfd_name,
                              'attributes': {'vnfd': toscal}}}
        vnfd_instance = self.client.create_vnfd(body=tosca_arg)
        self.assertIsNotNone(vnfd_instance)

        vnfds = self.client.list_vnfds().get('vnfds')
        self.assertIsNotNone(vnfds, "List of vnfds are Empty after Creation")

        vnfd_id = vnfd_instance['vnfd']['id']

        self.verify_vnfd_events(
            vnfd_id, evt_constants.RES_EVT_CREATE,
            evt_constants.RES_EVT_VNFD_ONBOARDED)
        try:
            self.client.delete_vnfd(vnfd_id)
        except Exception:
            assert False, "vnfd Delete failed"
        self.verify_vnfd_events(vnfd_id, evt_constants.RES_EVT_DELETE,
                                evt_constants.RES_EVT_VNFD_NA_STATE)

    def test_vnfd(self):
        self._test_create_list_delete_vnfd('sample_cirros_vnf.yaml')
