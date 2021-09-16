# Copyright (C) 2021 Nippon Telegraph and Telephone Corporation
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

import threading
import time

from oslo_utils import uuidutils

from tacker.sol_refactored.common import coordinate
from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.tests import base


class TestCoordinate(base.BaseTestCase):

    def setUp(self):
        super(TestCoordinate, self).setUp()
        self.sem_1 = threading.Semaphore(value=0)
        self.sem_2 = threading.Semaphore(value=0)
        self.ok = False

    @coordinate.lock_vnf_instance('{inst_id}')
    def _work_thread_1(self, inst_id, sleep_time):
        # notify to parent
        self.sem_1.release()

        # wait to notify from parent
        self.sem_2.acquire()

        if sleep_time:
            time.sleep(sleep_time)

    @coordinate.lock_vnf_instance('{inst_id}')
    def _work_thread_2(self, inst_id):
        pass

    @coordinate.lock_vnf_instance('{inst_id}', delay=True)
    def _work_thread_3(self, inst_id):
        self.ok = True

    def test_lock_vnf_instance(self):
        inst_id = uuidutils.generate_uuid()
        th = threading.Thread(target=self._work_thread_1, args=(inst_id, 0))
        th.start()

        # wait to run _work_thread_1
        self.sem_1.acquire()

        self.assertRaises(sol_ex.OtherOperationInProgress,
            self._work_thread_2, inst_id)

        self.sem_2.release()
        th.join()

    def test_lock_vnf_instance_delay(self):
        inst_id = uuidutils.generate_uuid()
        th = threading.Thread(target=self._work_thread_1, args=(inst_id, 3))
        th.start()

        # wait to run _work_thread_1
        self.sem_1.acquire()

        self.sem_2.release()
        self._work_thread_3(inst_id=inst_id)

        th.join()

        self.assertTrue(self.ok)
