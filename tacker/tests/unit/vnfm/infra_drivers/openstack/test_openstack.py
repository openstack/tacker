# Copyright 2015 Brocade Communications System, Inc.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
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

import codecs
import os
from unittest import mock
import yaml

from tacker import context
from tacker.tests.unit import base
from tacker.tests.unit.db import utils
from tacker.vnfm.infra_drivers.openstack import openstack


class FakeHeatClient(mock.Mock):

    class Stack(mock.Mock):
        stack_status = 'CREATE_COMPLETE'
        outputs = [{'output_value': '192.168.120.31', 'description':
            'management ip address', 'output_key': 'mgmt_ip-vdu1'}]

    def create(self, *args, **kwargs):
        return {'stack': {'id': '4a4c2d44-8a52-4895-9a75-9d1c76c3e738'}}

    def get(self, id):
        return self.Stack()


def _get_template(name):
    filename = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "data/", name)
    with codecs.open(filename, encoding='utf-8', errors='strict') as f:
        return f.read()


class TestOpenStack(base.TestCase):

    def setUp(self):
        super(TestOpenStack, self).setUp()
        self.context = context.get_admin_context()
        self.infra_driver = openstack.OpenStack()
        self._mock_heat_client()
        self.addCleanup(mock.patch.stopall)
        yaml.SafeLoader.add_constructor(
            yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
            lambda loader, node: dict(loader.construct_pairs(node)))

    def _mock_heat_client(self):
        self.heat_client = mock.Mock(wraps=FakeHeatClient())
        fake_heat_client = mock.Mock()
        fake_heat_client.return_value = self.heat_client
        self._mock(
            'tacker.vnfm.infra_drivers.openstack.heat_client.HeatClient',
            fake_heat_client)

    def _mock(self, target, new=mock.DEFAULT):
        patcher = mock.patch(target, new)
        return patcher.start()

    def test_delete(self):
        vnf_id = '4a4c2d44-8a52-4895-9a75-9d1c76c3e738'
        self.infra_driver.delete(plugin=None, context=self.context,
                                vnf_id=vnf_id,
                                auth_attr=utils.get_vim_auth_obj())
        self.heat_client.delete.assert_called_once_with(vnf_id)
