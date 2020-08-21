# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from unittest import mock

import datetime
import iso8601
from tacker import context
from tacker.db.nfvo import nfvo_db
from tacker import objects
from tacker.tests.unit.db.base import SqlTestCase
from tacker.tests.unit.objects import fakes
from tacker.tests import uuidsentinel


class TestVnf(SqlTestCase):

    def setUp(self):
        super(TestVnf, self).setUp()
        self.context = context.get_admin_context()
        self.vnfd = self._create_vnfd()
        self.vims = self._create_vims()

    def _create_vnfd(self):
        vnfd_obj = objects.Vnfd(context=self.context, **fakes.vnfd_data)
        vnfd_obj.create()

        return vnfd_obj

    def _create_vims(self):
        vim_obj = nfvo_db.Vim(**fakes.vim_data)

        return vim_obj

    def test_save(self):
        vnf_data = fakes.get_vnf(self.vnfd.id, self.vims.id)
        vnf_obj = objects.vnf.VNF(context=self.context, **vnf_data)

        vnf_obj.id = uuidsentinel.instance_id
        vnf_obj.status = 'ERROR'
        vnf_obj.updated_at = datetime.datetime(
            1900, 1, 1, 1, 1, 1, tzinfo=iso8601.UTC)
        vnf_obj.save()

        self.assertEqual('ERROR', vnf_obj.status)

    @mock.patch('tacker.objects.vnf._vnf_get')
    def test_vnf_index_list(self, mock_vnf_get):
        vnf_data = fakes.get_vnf(self.vnfd.id, self.vims.id)
        vnf_obj = objects.vnf.VNF(context=self.context, **vnf_data)

        vnf_obj.id = uuidsentinel.instance_id
        vnf_obj.updated_at = datetime.datetime(
            1900, 1, 1, 1, 1, 1, tzinfo=iso8601.UTC)
        vnf_obj.save()

        mock_vnf_get.return_value = vnf_obj
        vnf_data_result = vnf_obj.vnf_index_list(vnf_obj.id, self.context)
        self.assertEqual('ACTIVE', vnf_data_result.status)
