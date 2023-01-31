# Copyright (C) 2022 Fujitsu
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

import time
import webob

from oslo_log import log as logging

from tacker import context
from tacker.sol_refactored.common import http_client
from tacker.sol_refactored.common import vnflcm_utils
from tacker.sol_refactored.conductor import conductor_v2
from tacker.sol_refactored.conductor import server_notification_driver as snd
from tacker.sol_refactored import objects
from tacker.tests.unit.db import base as db_base
from unittest import mock


class TestServerNotification(db_base.SqlTestCase):
    def setUp(self):
        super(TestServerNotification, self).setUp()
        objects.register_all()
        self.context = context.get_admin_context()
        self.request = mock.Mock()
        self.request.context = self.context
        self.timer_test = (None, None)
        self.config_fixture.config(
            group='server_notification', server_notification=True)
        self.conductor = conductor_v2.ConductorV2()
        snd.ServerNotificationDriver._instance = None

    def tearDown(self):
        super(TestServerNotification, self).tearDown()
        snd.ServerNotificationDriver._instance = None

    @mock.patch.object(http_client.HttpClient, 'do_request')
    def test_conductor_notify_server_notification(self, mock_do_request):
        self.config_fixture.config(
            group='server_notification', server_notification=True)
        snd.ServerNotificationDriver._instance = None
        self.conductor.sn_driver = snd.ServerNotificationDriver.instance()
        self.config_fixture.config(
            group='server_notification', timer_interval=1)
        resp = webob.Response()
        resp.status_code = 202
        mock_do_request.return_value = resp, {}
        # queueing test
        id = 'test_id'
        self.conductor.server_notification_notify(
            self.context, id, ['id'])
        self.conductor.server_notification_notify(
            self.context, id, ['id2', 'id3'])
        self.assertEqual(
            self.conductor.sn_driver.timer_map[id].queue, ['id', 'id2', 'id3'])
        time.sleep(2)
        # remove_timer test
        self.conductor.server_notification_remove_timer(self.context, id)
        self.assertNotIn(id, self.conductor.sn_driver.timer_map)
        # remove_timer test: invalid_id
        self.conductor.server_notification_remove_timer(
            self.context, 'invalid_id')

    @mock.patch.object(vnflcm_utils, 'heal')
    def test_conductor_timer_expired(self, mock_heal):
        self.config_fixture.config(
            group='server_notification', server_notification=True)
        snd.ServerNotificationDriver._instance = None
        self.conductor.sn_driver = snd.ServerNotificationDriver.instance()
        self.conductor.sn_driver.timer_expired('test_id', ['id'])

    def test_conductor_timer_expired_error(self):
        self.config_fixture.config(
            group='server_notification', server_notification=True)
        snd.ServerNotificationDriver._instance = None
        self.conductor.sn_driver = snd.ServerNotificationDriver.instance()

        log_name = "tacker.sol_refactored.conductor.server_notification_driver"
        with self.assertLogs(logger=log_name, level=logging.ERROR) as cm:
            self.conductor.sn_driver.timer_expired('test_id', ['id'])
        msg = f'ERROR:{log_name}:server_notification auto healing is failed:'
        self.assertIn(msg, cm.output[1])

    def expired(self, id, queue):
        queue.sort()
        self.timer_test = (id, queue)

    def test_timer(self):
        # queueing test
        timer = snd.ServerNotificationTimer(
            'id', 1, self.expired)
        timer.append(['1', '2'])
        timer.append(['3', '4'])
        time.sleep(2)
        self.assertEqual(self.timer_test[0], 'id')
        self.assertEqual(self.timer_test[1], ['1', '2', '3', '4'])

    def test_timer_cancel(self):
        # cancel test
        timer = snd.ServerNotificationTimer(
            'id2', 1, self.expired)
        timer.append(['5'])
        timer.cancel()
        time.sleep(2)
        self.assertIsNone(self.timer_test[0])
        self.assertIsNone(self.timer_test[1])

    def test_timer_destructor(self):
        # method call after cancel()
        timer = snd.ServerNotificationTimer(
            'id', 1, self.expired)
        timer.cancel()
        timer.expire()
        timer.append(['4'])
        timer.cancel()
        timer.__del__()

    def test_driver_stub(self):
        self.config_fixture.config(
            group='server_notification', server_notification=False)
        drv = snd.ServerNotificationDriver.instance()
        drv = snd.ServerNotificationDriver.instance()
        drv.notify('id', ['id'])
        drv.remove_timer('id')
        self.config_fixture.config(
            group='server_notification', server_notification=True)
        snd.ServerNotificationDriver._instance = None
        drv = snd.ServerNotificationDriver.instance()
