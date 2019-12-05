# Copyright (C) 2020 NTT DATA
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

from tacker import context
from tacker import objects
from tacker.tests.unit.db.base import SqlTestCase


class TestTerminateVnfRequest(SqlTestCase):

    def setUp(self):
        super(TestTerminateVnfRequest, self).setUp()
        self.context = context.get_admin_context()

    def _get_terminate_vnf_request(self):
        terminate_vnf_request = {
            'termination_type': 'GRACEFUL',
            'graceful_termination_timeout': 10
        }
        return terminate_vnf_request

    def test_obj_from_primitive(self):
        terminate_vnf_request = self._get_terminate_vnf_request()
        result = objects.TerminateVnfRequest.obj_from_primitive(
            terminate_vnf_request, self.context)
        self.assertTrue(isinstance(result, objects.TerminateVnfRequest))
        self.assertEqual('GRACEFUL', result.termination_type)
        self.assertEqual(terminate_vnf_request['graceful_termination_timeout'],
            result.graceful_termination_timeout)

    def test_obj_from_primitive_without_timeout(self):
        terminate_vnf_request = self._get_terminate_vnf_request()
        terminate_vnf_request.pop('graceful_termination_timeout')

        result = objects.TerminateVnfRequest.obj_from_primitive(
            terminate_vnf_request, self.context)
        self.assertTrue(isinstance(result, objects.TerminateVnfRequest))
        self.assertEqual('GRACEFUL', result.termination_type)
        self.assertEqual(0, result.graceful_termination_timeout)
