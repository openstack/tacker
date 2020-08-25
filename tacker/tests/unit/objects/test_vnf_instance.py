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

import ddt
from unittest import mock

from oslo_utils import uuidutils

from tacker.common import exceptions
from tacker import context
from tacker.db import api as sqlalchemy_api
from tacker.db.nfvo import nfvo_db
from tacker import objects
from tacker.tests.unit.db.base import SqlTestCase
from tacker.tests.unit.objects import fakes
from tacker.tests.unit.vnflcm import fakes as fakes_vnflcm
from tacker.tests import uuidsentinel

get_engine = sqlalchemy_api.get_engine


class FakeApiModelQuery:

    def __init__(
            self,
            callback_filter_by=None,
            callback_update=None,
            callback_options=None):
        self.callback_filter_by = callback_filter_by
        self.callback_update = callback_update
        self.callback_options = callback_options

    def options(self, *args, **kwargs):
        if self.callback_options:
            self.callback_options(*args, **kwargs)

    def filter_by(self, *args, **kwargs):
        if self.callback_filter_by:
            self.callback_filter_by(*args, **kwargs)
        return self

    def update(self, *args, **kwargs):
        if self.callback_update:
            self.callback_update(*args, **kwargs)
        return self


@ddt.ddt
class TestVnfInstance(SqlTestCase):

    maxDiff = None

    def setUp(self):
        super(TestVnfInstance, self).setUp()
        self.context = context.get_admin_context()
        self.vnf_package = self._create_and_upload_vnf_package()
        self.vims = nfvo_db.Vim(**fakes.vim_data)
        self.engine = get_engine()
        self.conn = self.engine.connect()
        self.body_data = self._create_body_data()
        self.vnfd_pkg_data = self._create_vnfd_pkg_data()
        self.vim = nfvo_db.Vim()

    @mock.patch.object(objects.VnfPackageVnfd, 'create')
    def _create_and_upload_vnf_package(self, mock_create):
        vnf_package = objects.VnfPackage(context=self.context,
                                         **fakes.vnf_package_data)
        vnf_package.create()

        vnf_pack_vnfd = fakes.get_vnf_package_vnfd_data(
            vnf_package.id, uuidsentinel.vnfd_id)

        mock_create.return_value = fakes.return_vnf_package_vnfd_data()
        vnf_pack_vnfd_obj = objects.VnfPackageVnfd(
            context=self.context, **vnf_pack_vnfd)
        vnf_pack_vnfd_obj.create()

        vnf_package.vnf_package = "ONBOARDED"
        vnf_package.save()

        return vnf_pack_vnfd_obj

    def _create_body_data(self):
        body_data = {}
        body_data['vnf_instance_name'] = "new_instance_name"
        body_data['vnf_instance_description'] = "new_instance_discription"
        body_data['vnfd_id'] = "2c69a161-0000-4b0f-bcf8-391f8fc76600"
        body_data['vnf_configurable_properties'] = {"test": "test_value"}
        body_data['vnfc_info_modifications_delete_ids'] = ["test1"]
        body_data['vnf_pkg_id'] = uuidsentinel.vnf_pkg_id
        return body_data

    def _create_vnfd_pkg_data(self):
        vnfd_pkg_data = {}
        vnfd_pkg_data['vnf_provider'] =\
            fakes.return_vnf_package_vnfd_data().get('vnf_provider')
        vnfd_pkg_data['vnf_product_name'] =\
            fakes.return_vnf_package_vnfd_data().get('vnf_product_name')
        vnfd_pkg_data['vnf_software_version'] =\
            fakes.return_vnf_package_vnfd_data().get('vnf_software_version')
        vnfd_pkg_data['vnfd_version'] =\
            fakes.return_vnf_package_vnfd_data().get('vnfd_version')
        vnfd_pkg_data['package_uuid'] =\
            fakes.return_vnf_package_vnfd_data().get('package_uuid')
        vnfd_pkg_data['vnfd_id'] =\
            fakes.return_vnf_package_vnfd_data().get('vnfd_id')
        return vnfd_pkg_data

    def test_create(self):
        vnf_instance_data = fakes.get_vnf_instance_data(
            self.vnf_package.vnfd_id)
        vnf_instance = objects.VnfInstance(context=self.context,
                                           **vnf_instance_data)
        vnf_instance.create()
        self.assertTrue(vnf_instance.id)
        self.assertEqual('NOT_INSTANTIATED', vnf_instance.instantiation_state)
        self.assertEqual(self.vnf_package.vnfd_id,
                         vnf_instance.vnfd_id)
        self.assertEqual('test vnf provider', vnf_instance.vnf_provider)
        self.assertEqual('Sample VNF', vnf_instance.vnf_product_name)
        self.assertEqual('1.0', vnf_instance.vnf_software_version)
        self.assertEqual('1.0', vnf_instance.vnfd_version)
        self.assertEqual(vnf_instance_data.get('tenant_id'),
                         vnf_instance.tenant_id)

    def test_create_failure_with_id(self):
        vnf_instance_data = fakes.get_vnf_instance_data_with_id(
            self.vnf_package.vnfd_id)
        vnf_instance = objects.VnfInstance(context=self.context,
                                           **vnf_instance_data)
        self.assertRaises(exceptions.ObjectActionError, vnf_instance.create)

    def test_get_by_id(self):
        vnf_instance_data = fakes.get_vnf_instance_data(
            self.vnf_package.vnfd_id)
        vnf_instance = objects.VnfInstance(context=self.context,
                                           **vnf_instance_data)
        vnf_instance.create()
        vnf_instance_by_id = objects.VnfInstance.get_by_id(
            self.context, vnf_instance.id)
        self.compare_obj(vnf_instance, vnf_instance_by_id,
                         allow_missing=['instantiated_vnf_info',
                                        'vim_connection_info'])

    def test_get_by_id_non_existing_vnf_instance(self):
        self.assertRaises(
            exceptions.VnfInstanceNotFound,
            objects.VnfInstance.get_by_id, self.context,
            uuidsentinel.invalid_uuid)

    @mock.patch('tacker.objects.vnf_instance._vnf_instance_update')
    def test_save(self, mock_update_vnf):
        vnf_instance_data = fakes.get_vnf_instance_data(
            self.vnf_package.vnfd_id)
        vnf_instance = objects.VnfInstance(context=self.context,
                                           **vnf_instance_data)
        vnf_instance.create()
        mock_update_vnf.return_value = \
            fakes.vnf_instance_model_object(vnf_instance)
        vnf_instance.vnf_instance_name = 'fake-name'
        vnf_instance.save()
        mock_update_vnf.assert_called_with(
            self.context, vnf_instance.id, {
                'vnf_instance_name': 'fake-name',
                'vim_connection_info': []},
            columns_to_join=['instantiated_vnf_info'])

    def test_save_error(self):
        vnf_instance_data = fakes.get_vnf_instance_data(
            self.vnf_package.vnfd_id)
        vnf_instance = objects.VnfInstance(context=self.context,
                                           **vnf_instance_data)
        vnf_instance.id = uuidsentinel.id
        self.assertRaises(exceptions.VnfInstanceNotFound, vnf_instance.save)

    def test_get_all(self):
        vnf_instance_data = fakes.get_vnf_instance_data(
            self.vnf_package.vnfd_id)
        vnf_instance = objects.VnfInstance(context=self.context,
                                           **vnf_instance_data)
        vnf_instance.create()
        result = objects.VnfInstanceList.get_all(self.context,
                                                 expected_attrs=None)
        self.assertTrue(result.objects, list)
        self.assertTrue(result.objects)

    def test_vnf_instance_list_get_by_filters(self):
        vnf_instance_data = fakes.get_vnf_instance_data(
            self.vnf_package.vnfd_id)
        vnf_instance = objects.VnfInstance(context=self.context,
                                           **vnf_instance_data)
        vnf_instance.create()
        filters = {'field': 'instantiation_state', 'model': 'VnfInstance',
                   'value': 'NOT_INSTANTIATED',
                   'op': '=='}
        vnf_instance_list = objects.VnfInstanceList.get_by_filters(
            self.context, filters=filters)
        self.assertEqual(1, len(vnf_instance_list))

    @mock.patch('tacker.objects.vnf_instance._destroy_vnf_instance')
    def test_destroy(self, mock_vnf_destroy):
        vnf_instance_data = fakes.get_vnf_instance_data(
            self.vnf_package.vnfd_id)
        vnf_instance = objects.VnfInstance(context=self.context,
                                           **vnf_instance_data)
        vnf_instance.create()
        vnf_instance.destroy(self.context)
        mock_vnf_destroy.assert_called_with(self.context, vnf_instance.id)

    def test_destroy_failure_without_id(self):
        vnf_instance_obj = objects.VnfInstance(context=self.context)
        self.assertRaises(exceptions.ObjectActionError,
                          vnf_instance_obj.destroy, self.context)

    @mock.patch.object(objects.vnf_package.VnfPackage, 'get_by_id')
    def test_update(self, mock_get_by_id):
        mock_get_by_id.return_value =\
            fakes_vnflcm.return_vnf_package_with_deployment_flavour()
        vnf_instance_data = fakes.get_vnf_instance_data(
            self.vnf_package.vnfd_id)
        vnf_instance = objects.VnfInstance(context=self.context,
                                           **vnf_instance_data)
        vnf_instance.create()
        id = uuidutils.generate_uuid()
        vnf_lcm_oppccs = fakes.get_lcm_op_occs_data(
            id,
            vnf_instance.id)

        vnf_instance.update(
            self.context,
            vnf_lcm_oppccs,
            self.body_data,
            self.vnfd_pkg_data,
            vnf_instance_data['vnfd_id'])
