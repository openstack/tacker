# Copyright 2016 Brocade Communications System, Inc.
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

from tacker.plugins.common import constants
from tacker.tests.functional import base
from tacker.tests.utils import read_file

CONF = cfg.CONF


class VnfdTestEvent(base.BaseTackerTest):
    def _test_create_delete_vnfd_events(self, vnfd_file):
        data = dict()
        data['tosca'] = read_file(vnfd_file)
        toscal = data['tosca']
        vnfd_name = 'sample_cirros_vnf'
        tosca_arg = {'vnfd': {'name': vnfd_name,
                              'attributes': {'vnfd': toscal}}}
        vnfd_instance = self.client.create_vnfd(body=tosca_arg)
        self.assertIsNotNone(vnfd_instance)

        vnfd_id = vnfd_instance['vnfd']['id']
        params = {'resource_id': vnfd_id,
                  'event_type': constants.RES_EVT_CREATE,
                  'timestamp': vnfd_instance['vnfd'][
                      constants.RES_EVT_CREATED_FLD]}
        vnfd_evt_list = self.client.list_vnfd_events(params)

        self.assertIsNotNone(vnfd_evt_list,
                             "List of vnfds events are Empty after Creation")
        self.assertEqual(1, len(vnfd_evt_list))

        try:
            self.client.delete_vnfd(vnfd_id)
        except Exception:
            assert False, "vnfd Delete failed"

        params = {'resource_id': vnfd_id,
                  'event_type': constants.RES_EVT_DELETE}
        vnfd_evt_list = self.client.list_vnfd_events(params)

        self.assertIsNotNone(vnfd_evt_list,
                             "List of vnfds events are Empty after Deletion")
        self.assertEqual(1, len(vnfd_evt_list))

    def test_vnfd_events(self):
        self._test_create_delete_vnfd_events('sample_cirros_vnf.yaml')
