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

from unittest import mock

from tacker.common import exceptions
from tacker import context
from tacker.db import api as sqlalchemy_api
from tacker.db.db_sqlalchemy import api
from tacker.db.nfvo import nfvo_db
from tacker import objects
from tacker.tests.unit.db.base import SqlTestCase
from tacker.tests.unit.objects import fakes
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


class TestVnfInstance(SqlTestCase):

    maxDiff = None

    def setUp(self):
        super(TestVnfInstance, self).setUp()
        self.context = context.get_admin_context()
        self.vnf_package = self._create_and_upload_vnf_package()
        self.vims = nfvo_db.Vim(**fakes.vim_data)
        self.engine = get_engine()
        self.conn = self.engine.connect()

    def _create_and_upload_vnf_package(self):
        vnf_package = objects.VnfPackage(context=self.context,
                                         **fakes.vnf_package_data)
        vnf_package.create()

        vnf_pack_vnfd = fakes.get_vnf_package_vnfd_data(
            vnf_package.id, uuidsentinel.vnfd_id)

        vnf_pack_vnfd_obj = objects.VnfPackageVnfd(
            context=self.context, **vnf_pack_vnfd)
        vnf_pack_vnfd_obj.create()

        vnf_package.vnf_package = "ONBOARDED"
        vnf_package.save()

        return vnf_pack_vnfd_obj

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

    @mock.patch('tacker.objects.vnf_instance._get_vnf_instance')
    @mock.patch('tacker.objects.vnf_package.VnfPackage.get_by_id')
    @mock.patch.object(api, 'model_query')
    def test_update_vnf_instances(
            self,
            mock_model_query,
            mock_get_vnf_package,
            mock_get_vnf):

        vnf_instance_data = fakes.fake_vnf_instance_model_dict(**{
            "vim_connection_info": [
                objects.VimConnectionInfo._from_dict({
                    "id": "testid",
                    "vim_id": "aaa",
                    "vim_type": "openstack-1",
                    "interface_info": {"endpoint": "endpoint"},
                    "access_info": {"username": "xxxxx",
                                    "region": "region",
                                    "password": "password",
                                    "tenant": "tenant"}}),
                objects.VimConnectionInfo._from_dict({
                    "id": "testid3",
                    "vim_id": "ccc",
                    "vim_type": "openstack-2",
                    "interface_info": {"endpoint": "endpoint22"},
                    "access_info": {"username": "xxxxx",
                                    "region": "region",
                                    "password": "password"}}),
                objects.VimConnectionInfo._from_dict({
                    "id": "testid5",
                    "vim_id": "eee",
                    "vim_type": "openstack-4"})
            ],
            "vnf_metadata": {"testkey": "test_value"}})
        vnf_instance = objects.VnfInstance(
            context=self.context, **vnf_instance_data)
        mock_get_vnf.return_value = \
            fakes.vnf_instance_model_object(vnf_instance)

        def mock_filter(id=None):
            print('### mock_filter ###', id)

        def mock_update(updated_values, synchronize_session=False):
            print('### mock_update ###', updated_values)

            if 'vim_connection_info' not in updated_values:
                return

            compar_updated_values = {}
            compar_updated_values['vnf_instance_name'] = "new_instance_name"
            compar_updated_values['vnf_instance_description'] = \
                "new_instance_discription"
            compar_updated_values['vnf_metadata'] = {
                "testkey": "test_value1", "testkey2": "test_value2"}
            compar_updated_values['vim_connection_info'] = [
                objects.VimConnectionInfo._from_dict({
                    "id": "testid",
                    "vim_id": "bbb",
                    "vim_type": "openstack-1A",
                    "interface_info": {"endpoint": "endpoint11"},
                    "access_info": {"username": "xxxxx1",
                                    "region": "region1",
                                    "password": "password1",
                                    "tenant": "tenant1"}}),
                objects.VimConnectionInfo._from_dict({
                    "id": "testid3",
                    "vim_id": "ccc",
                    "vim_type": "openstack-2",
                    "interface_info": {"endpoint": "endpoint22"},
                    "access_info": {"username": "xxxxx",
                                    "region": "region",
                                    "password": "password2",
                                    "tenant": "tenant2"}}),
                objects.VimConnectionInfo._from_dict({
                    "id": "testid5",
                    "vim_id": "eee",
                    "vim_type": "openstack-4"}),
                objects.VimConnectionInfo._from_dict({
                    "id": "testid7",
                    "vim_id": "fff",
                    "vim_type": "openstack-5A",
                    "interface_info": {"endpoint": "endpoint55"},
                    "access_info": {"username": "xxxxx5",
                                    "region": "region5",
                                    "password": "password5",
                                    "tenant": "tenant5"}})
            ]
            compar_updated_values['vnfd_id'] = \
                "2c69a161-0000-4b0f-bcf8-391f8fc76600"
            compar_updated_values['vnf_provider'] = \
                self.vnf_package.get('vnf_provider')
            compar_updated_values['vnf_product_name'] = \
                self.vnf_package.get('vnf_product_name')
            compar_updated_values['vnf_software_version'] = \
                self.vnf_package.get('vnf_software_version')

            expected_vci = sorted(compar_updated_values.pop(
                'vim_connection_info'), key=lambda x: x.id)
            actual_vci = sorted(
                updated_values.pop('vim_connection_info'),
                key=lambda x: x.id)
            for e, a in zip(expected_vci, actual_vci):
                self.assertDictEqual(
                    e.to_dict(),
                    a.to_dict())

            self.assertDictEqual(
                compar_updated_values,
                updated_values)

        fake_api_model_query = FakeApiModelQuery(
            callback_filter_by=mock_filter, callback_update=mock_update)
        mock_model_query.return_value = fake_api_model_query

        vnf_lcm_opoccs = {}

        body = {"vnf_instance_name": "new_instance_name",
                "vnf_instance_description": "new_instance_discription",
                "vnfd_id": "2c69a161-0000-4b0f-bcf8-391f8fc76600",
                "vnf_configurable_properties": {"test": "test_value1"},
                "vnfc_info_modifications_delete_ids": ["test1"],
                "metadata": {"testkey": "test_value1",
                             "testkey2": "test_value2"},
                "vim_connection_info": [
                    {"id": "testid",
                     "vim_id": "bbb",
                     "vim_type": "openstack-1A",
                     "interface_info": {"endpoint": "endpoint11"},
                     "access_info": {"username": "xxxxx1",
                                     "region": "region1",
                                     "password": "password1",
                                     "tenant": "tenant1"}},
                    {"id": "testid3",
                     "vim_type": "openstack-2",
                     "access_info": {"password": "password2",
                                     "tenant": "tenant2"}},
                    {"id": "testid7",
                     "vim_id": "fff",
                     "vim_type": "openstack-5A",
                     "interface_info": {"endpoint": "endpoint55"},
                     "access_info": {"username": "xxxxx5",
                                     "region": "region5",
                                     "password": "password5",
                                     "tenant": "tenant5"}},
                ]}

        vnf_instance.update(
            self.context,
            vnf_lcm_opoccs,
            body,
            self.vnf_package,
            self.vnf_package.id)
