# Copyright (C) 2023 NEC, Corp.
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

from unittest import mock

from tacker.api.views import vnf_lcm
import tacker.conf
from tacker import context
from tacker import objects
from tacker.tests.unit.api.v1 import fakes
from tacker.tests.unit.db.base import SqlTestCase

CONF = tacker.conf.CONF


class TestVnfInstance(SqlTestCase):

    def setUp(self):
        super(TestVnfInstance, self).setUp()
        self.context = context.get_admin_context()

    def test_vnf_instance_info_without_vnf_desc(self):
        mock_self = mock.Mock()
        vnf_instance_data = fakes.get_vnf_instance_data_without_vnf_desc()
        vnf_instance = objects.VnfInstance(context=self.context,
                                           **vnf_instance_data)
        vnf_instance.create()
        links = {
            "self": {
                "href":
                '{endpoint}/vnflcm/v1/vnf_instances/{id}'.format(
                    endpoint=CONF.vnf_lcm.endpoint_url.rstrip("/"),
                    id="abc")
            }
        }
        mock_self._get_links.return_value = {"_links": links}
        vnf_instance_dict = vnf_lcm.ViewBuilder\
            ._get_vnf_instance_info(mock_self, vnf_instance)
        self.assertNotIn("vnfInstanceDescription", vnf_instance_dict)

    def test_vnf_instance_info_with_vnf_desc(self):
        mock_self = mock.Mock()
        vnf_instance_data = fakes.get_vnf_instance_data_with_vnf_desc()
        vnf_instance = objects.VnfInstance(context=self.context,
                                           **vnf_instance_data)
        vnf_instance.create()
        links = {
            "self": {
                "href":
                '{endpoint}/vnflcm/v1/vnf_instances/{id}'.format(
                    endpoint=CONF.vnf_lcm.endpoint_url.rstrip("/"),
                    id="abc")
            }
        }
        mock_self._get_links.return_value = {"_links": links}
        vnf_instance_dict = vnf_lcm.ViewBuilder\
            ._get_vnf_instance_info(mock_self, vnf_instance)
        self.assertIn("vnfInstanceDescription", vnf_instance_dict)
