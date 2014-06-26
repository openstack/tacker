# Copyright 2014 Intel Corporation.
# Copyright 2014 Isaku Yamahata <isaku.yamahata at intel com>
#                               <isaku.yamahata at gmail com>
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
#
# @author: Isaku Yamahata, Intel Corporation.

import uuid

import mock
from oslo.config import cfg

from tacker.db import api as db
import tacker.openstack.common.rpc.proxy
from tacker.tests import base
from tacker.vm.mgmt_drivers import constants
from tacker.vm.mgmt_drivers.rpc import rpc


_uuid = lambda: str(uuid.uuid4())


class TestMgmtRpcDriver(base.BaseTestCase):
    _CONTEXT = {}
    _DEVICE = {
        'id': _uuid(),
        'mgmt_address': 'device-address'
    }
    _SERVICE_INSTANCE = {
        'id': _uuid(),
        'mgmt_address': 'service-instance-address',
    }
    _KWARGS = {
        constants.KEY_ACTION: 'action-name',
        constants.KEY_KWARGS: {
            constants.KEY_ACTION: 'method-name',
        }
    }

    def setUp(self):
        super(TestMgmtRpcDriver, self).setUp()
        db.configure_db()
        self.addCleanup(db.clear_db)
        cfg.CONF.set_override('rpc_backend',
                              'tacker.openstack.common.rpc.impl_fake')
        self.plugin = mock.Mock()
        self.mock_rpc_proxy_cast_p = mock.patch.object(
            tacker.openstack.common.rpc.proxy.RpcProxy, 'cast')
        self.mock_rpc_proxy_cast = self.mock_rpc_proxy_cast_p.start()
        self.mgmt_driver = rpc.AgentRpcMGMTDriver()

    def test_rpc_mgmt_call(self):
        self.mgmt_driver.mgmt_call(self.plugin, self._CONTEXT,
                                   self._DEVICE, self._KWARGS)
        self.mock_rpc_proxy_cast.assert_called_once_with(
            self._CONTEXT,
            {'args': {'action': 'method-name'},
             'namespace': None,
             'method': 'action-name'},
            topic='device-address')

    def test_rpc_mgmt_service_call(self):
        self.mgmt_driver.mgmt_service_call(
            self.plugin, self._CONTEXT, self._DEVICE, self._SERVICE_INSTANCE,
            self._KWARGS)
        self.mock_rpc_proxy_cast.assert_called_once_with(
            self._CONTEXT,
            {'args': {'action': 'method-name'},
             'namespace': None,
             'method': 'action-name'},
            topic='service-instance-address')
