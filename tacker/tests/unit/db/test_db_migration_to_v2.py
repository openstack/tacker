# Copyright (C) 2022 KDDI
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

import copy
import datetime
import iso8601
import sys

from oslo_utils import uuidutils
from tacker.common import exceptions
from tacker import context
from tacker.db.db_sqlalchemy import api
from tacker.db.db_sqlalchemy import models
from tacker.db.migration import cli
from tacker.db.migration import migrate_to_v2
from tacker.db.nfvo import nfvo_db
from tacker.db.vnfm import vnfm_db
from tacker import objects
from tacker.sol_refactored.common import vnf_instance_utils as inst_utils
from tacker.sol_refactored import objects as objects_v2
from tacker.sol_refactored.objects.v2 import fields as fields_v2
from tacker.tests.base import BaseTestCase
from tacker.tests.unit.db.base import SqlTestCase
from tacker.tests.unit.objects import fakes
from tacker.tests.unit.vnflcm import fakes as fakes_vnflcm
from tacker.tests import uuidsentinel
from unittest import mock


class TestCliMigrateToV2(BaseTestCase):
    def setUp(self):
        super(TestCliMigrateToV2, self).setUp()
        self.addCleanup(mock.patch.stopall)
        mock.patch('tacker.db.migration.migrate_to_v2'
                   '.mark_delete_v1').start()
        mock.patch('tacker.db.migration.migrate_to_v2'
                   '.mark_delete_v2').start()
        mock.patch('tacker.db.migration.migrate_to_v2'
                   '.get_all_vnfs').start()
        mock.patch('tacker.db.migration.migrate_to_v2'
                   '.create_vnf_instance_v2').start()
        mock.patch('tacker.db.migration.migrate_to_v2'
                   '.create_vnf_lcm_op_occs_v2').start()
        self.argv = ['prog', 'migrate-to-v2']

    def _main_test_helper(self, argv):
        with mock.patch.object(sys, 'argv', argv):
            cli.main()

    def test_no_option_invalid(self):
        self.assertRaises(exceptions.InvalidInput,
            self._main_test_helper, self.argv)

    def test_all_option(self):
        self.assertRaises(exceptions.InvalidInput,
            self._main_test_helper, self.argv + ['--all', '--vnf-id', 'foo'])

        self.assertRaises(exceptions.InvalidInput,
            self._main_test_helper, self.argv + ['--all', '--api-ver', 'foo'])

        self.assertRaises(exceptions.InvalidInput,
            self._main_test_helper, self.argv + ['--all', '--mark-delete'])

        self._main_test_helper(self.argv + ['--all'])
        migrate_to_v2.get_all_vnfs.assert_called_once_with(mock.ANY)

        migrate_to_v2.get_all_vnfs.reset_mock()

        self._main_test_helper(self.argv + ['--vnf-id', 'foo'])
        migrate_to_v2.get_all_vnfs.assert_not_called()

    def test_vnf_id_option(self):
        self._main_test_helper(self.argv + ['--vnf-id', 'foo'])
        migrate_to_v2.create_vnf_instance_v2\
            .assert_called_once_with(mock.ANY, 'foo')
        migrate_to_v2.create_vnf_lcm_op_occs_v2\
            .assert_called_once_with(mock.ANY, 'foo')

    def test_keep_orig_option(self):
        self._main_test_helper(self.argv + ['--vnf-id', 'foo', '--keep-orig'])
        migrate_to_v2.mark_delete_v1.assert_not_called()

        self._main_test_helper(self.argv + ['--vnf-id', 'foo'])
        migrate_to_v2.mark_delete_v1\
            .assert_called_once_with(mock.ANY, 'foo')

    def test_api_ver_option(self):
        self.assertRaises(exceptions.InvalidInput, self._main_test_helper,
            self.argv + ['--vnf-id', 'foo', '--api-ver', 'v1'])

        self.assertRaises(exceptions.InvalidInput, self._main_test_helper,
            self.argv + ['--vnf-id', 'foo',
                         '--mark-delete', '--api-ver', 'foo'])

        self._main_test_helper(self.argv + ['--vnf-id', 'foo', '--mark-delete',
                                            '--api-ver', 'v1'])
        migrate_to_v2.mark_delete_v1\
            .assert_called_once_with(mock.ANY, 'foo')
        migrate_to_v2.mark_delete_v2.assert_not_called()

        migrate_to_v2.mark_delete_v1.reset_mock()

        self._main_test_helper(self.argv + ['--vnf-id', 'foo', '--mark-delete',
                                            '--api-ver', 'v2'])
        migrate_to_v2.mark_delete_v1.assert_not_called()
        migrate_to_v2.mark_delete_v2.\
            assert_called_once_with(mock.ANY, 'foo')

    def test_mark_delete_option(self):
        self.assertRaises(exceptions.InvalidInput, self._main_test_helper,
            self.argv + ['--vnf-id', 'foo', '--mark-delete'])

        self._main_test_helper(self.argv + ['--vnf-id', 'foo', '--mark-delete',
                                            '--api-ver', 'v1'])
        migrate_to_v2.mark_delete_v1.assert_called_once_with(mock.ANY, 'foo')
        migrate_to_v2.mark_delete_v2.assert_not_called()
        migrate_to_v2.create_vnf_instance_v2.assert_not_called()
        migrate_to_v2.create_vnf_lcm_op_occs_v2.assert_not_called()


class TestDbMigrationToV2(SqlTestCase):

    def setUp(self):
        super(TestDbMigrationToV2, self).setUp()
        objects_v2.register_all()

        self.context = context.get_admin_context()
        self.vnf_package = self._create_and_upload_vnf_package()
        self.vnfd = self._create_vnfd()
        self.vims = self._create_vims()
        self.vim_connection_info = self._create_vim_connection_info()
        self.vnf_instance = self._create_vnf_instance()
        self.vl_res_info_int_vl_id = uuidsentinel.int_vl_id
        self.vl_res_info_ext_vl_id = uuidsentinel.ext_vl_id
        self.resource_handle_infos = self._create_resource_handle()
        self.ext_link_port_info = self._create_ext_link_port_info()
        self.ext_virtual_link_info = self._create_ext_virtual_link_info()
        self.ip_addresses_infos = self._create_ip_addresses_info()
        self.ip_over_ethernet_infos = self._create_ip_over_ethernet_info()
        self.cp_protocol_infos = self._create_cp_protocol_info()
        self.vnf_external_cp_infos = self._create_vnf_external_cp_info()
        self.vnfc_cp_infos = self._create_vnfc_cp_info()
        self.virtual_storage_resource_infos = \
            self._create_virtual_storage_resource_info()
        self.vnfc_resource_infos = self._create_vnfc_resource_info()
        self.vnf_link_ports_infos = self._create_vnf_link_ports()
        self.vnf_external_cp_infos = self._create_vnf_external_cp_info()
        self.virtual_link_resource_infos = \
            self._create_virtual_link_resource_info()
        self.ext_managed_virtual_link_info = \
            self._create_ext_managed_virtual_link_info()
        self.vnfc_infos = self._create_vnfc_info()
        self.scale_status = self._create_scale_status()
        self.vnf_instantiated_info = \
            self._create_vnf_instantiated_info()
        self.vnf_attributes = self._create_vnf_attributes()
        self.vnf = self._create_vnf()
        # lcm_op_occ
        self.vnf_lcm_op_occs = self._create_vnf_lcm_op_occs(2)

    def _create_vnf_lcm_op_occs(self, record_num):
        vnf_lcm_op_occs = list()
        vnf_instance_id = self.vnf_instance.id

        for i in range(record_num):
            id = uuidsentinel.__getattr__(f"id{i}")
            tenant_id = uuidsentinel.__getattr__(f"tenant_id{i}")

            vnf_lcm_op_occ_data = fakes_vnflcm.fake_vnf_lcm_op_occs()
            vnf_lcm_op_occ_data["id"] = id
            vnf_lcm_op_occ_data["tenant_id"] = tenant_id
            vnf_lcm_op_occ_data["vnf_instance_id"] = vnf_instance_id
            vnf_lcm_op_occ_data["operation_params"] = \
                '{"vnfInstanceName": "modified"}'

            error_obj = vnf_lcm_op_occ_data["error"]
            resource_changes_obj = vnf_lcm_op_occ_data["resource_changes"]
            changed_info_obj = vnf_lcm_op_occ_data["changed_info"]
            changed_ext_connectivity_obj = \
                vnf_lcm_op_occ_data["changed_ext_connectivity"]
            vnf_lcm_op_occ_data["error"] = None
            vnf_lcm_op_occ_data["resource_changes"] = None
            vnf_lcm_op_occ_data["changed_info"] = None
            vnf_lcm_op_occ_data["changed_ext_connectivity"] = None

            vnf_lcm_op_occ = \
                objects.VnfLcmOpOcc(context=self.context,
                                    **vnf_lcm_op_occ_data)
            vnf_lcm_op_occ.create()

            vnf_lcm_op_occ.error = error_obj
            vnf_lcm_op_occ.resource_changes = resource_changes_obj
            vnf_lcm_op_occ.changed_info = changed_info_obj
            vnf_lcm_op_occ.changed_ext_connectivity = \
                changed_ext_connectivity_obj
            vnf_lcm_op_occ.save()

            vnf_lcm_op_occs.append(vnf_lcm_op_occ)

        return vnf_lcm_op_occs

    def _create_vnfd(self):
        vnfd_obj = objects.Vnfd(context=self.context, **fakes.vnfd_data)
        vnfd_obj.create()
        return vnfd_obj

    def _create_vims(self):
        session = self.context.session
        vim_db = nfvo_db.Vim(
            id='6261579e-d6f3-49ad-8bc3-a9cb974778ff',
            tenant_id='ad7ebc56538745a08ef7c5e97f8bd437',
            name='fake_vim',
            description='fake_vim_description',
            type='openstack',
            deleted_at=datetime.datetime.min,
            placement_attr={'regions': ['RegionOne']})
        vim_auth_db = nfvo_db.VimAuth(
            vim_id='6261579e-d6f3-49ad-8bc3-a9cb974778ff',
            password='encrypted_pw',
            auth_url='http://localhost/identity',
            vim_project={'name': 'test_project'},
            auth_cred={'username': 'test_user', 'user_domain_id': 'default',
                       'project_domain_id': 'default',
                       'key_type': 'fernet_key'})
        session.add(vim_db)
        session.add(vim_auth_db)
        return vim_db

    def _create_vnf_attributes(self, vnf_inst_id=None):
        if not vnf_inst_id:
            vnf_inst_id = self.vnf_instance.id
        self.valid_configurable_properties = {
            'configurable_properties': {
                'is_autoscale_enabled': False,
                'is_autoheal_enabled': False}}
        fake_attr_configurable_properties = {
            'vnf_id': vnf_inst_id,
            'key': 'param_values',
            'value': str(self.valid_configurable_properties)}

        self.valid_monitoring_parameters = {
            'monitoring_parameters': [{
                'id': uuidsentinel.id,
                'name': 'dummy',
                'performance_metric': 'v_cpu_usage_mean_vnf'}]}
        fake_attr_monitoring_parameters = {
            'vnf_id': vnf_inst_id,
            'key': 'param_values',
            'value': str(self.valid_monitoring_parameters)}

        fake_attr_localization_languages = {
            'vnf_id': vnf_inst_id,
            'key': 'param_values',
            'value': str({
                'localization_languages': ["ja"]})}

        self.valid_scale_group = {
            'scaleGroupDict': {
                'VDU_2': {
                    'vdu': ['VDU_2'],
                    'num': 1,
                    'maxLevel': 1,
                    'initialNum': 0,
                    'initialLevel': 0,
                    'default': 0}}}

        fake_attr_scale_group = {
            'vnf_id': vnf_inst_id,
            'key': 'scale_group',
            'value': str(self.valid_scale_group)}
        ext_net = self.ext_virtual_link_info.resource_handle.resource_id
        ext_subnet = uuidsentinel.ext_subnet_id
        fake_attr_stack_param = {
            'vnf_id': vnf_inst_id,
            'key': 'stack_param',
            'value': str({
                "nfv": {
                    "VDU": {
                        "VDU_0": {
                            "flavor": "dummy_flavor",
                            "image": "dummy_image",
                            "connection_points": {
                                "VDU0_CP0": {
                                    "order": 0},
                                "VDU0_CP1": {
                                    "order": 0}},
                            "number_of_instance": 1},
                        "VDU_1": {
                            "flavor": "dummy_flavor",
                            "image": "dummy_image",
                            "connection_points": {
                                "VDU1_CP0": {
                                    "order": 0},
                                "VDU1_CP1": {
                                    "order": 0}},
                            "number_of_instance": 1}},
                   "CP": {
                       "VDU0_CP0": {
                           "network_id": ext_net,
                           "subnets": [{
                               "subnet_id": ext_subnet,
                               "fixed_ip_addresses": [
                                   "192.168.0.1"],
                               "ethertype": "IPV4"}],
                           "order": 0},
                       "VDU1_CP0": {
                           "network_id": ext_net,
                           "subnets": [{
                               "subnet_id": ext_subnet,
                               "fixed_ip_addresses": [
                                   "192.168.0.2"],
                               "ethertype": "IPV4"}],
                           "order": 0}}}})}
        configurable_properties = \
            vnfm_db.VNFAttribute(**fake_attr_configurable_properties)
        monitoring_parameters = \
            vnfm_db.VNFAttribute(**fake_attr_monitoring_parameters)
        localizaiton_language = \
            vnfm_db.VNFAttribute(**fake_attr_localization_languages)
        scale_group = vnfm_db.VNFAttribute(**fake_attr_scale_group)
        stack_param = vnfm_db.VNFAttribute(**fake_attr_stack_param)
        return [configurable_properties, monitoring_parameters,
                localizaiton_language, scale_group, stack_param]

    def _create_vnf(self, vnf_inst_id=None):
        if not vnf_inst_id:
            vnf_inst_id = self.vnf_instance.id
        vnf_data = {
            'id': vnf_inst_id,
            'tenant_id': uuidsentinel.tenant_id,
            'name': "test_vnf",
            'vnfd_id': self.vnfd.id,
            'instance_id': uuidsentinel.instance_id,
            'mgmt_ip_address':
                "{'VDU_0': ['192.168.1.10'], 'VDU_1': ['192.168.1.11']}",
            'status': "ACTIVE",
            'description': "test_description",
            'placement_attr': "test_placement_attr",
            'vim_id': self.vims.id,
            'attributes': self.vnf_attributes}
        vnf_db = vnfm_db.VNF(**vnf_data)
        vnf_db.save(self.context.session)
        return vnf_db

    def _create_and_upload_vnf_package(self):
        vnf_package = objects.VnfPackage(context=self.context,
                                         **fakes.vnf_package_data)
        vnf_package.create()
        vnf_pack_vnfd = fakes.get_vnf_package_vnfd_data(
            vnf_package.id, uuidsentinel.vnfd_id)
        vnf_pack_vnfd_obj = objects.VnfPackageVnfd(
            context=self.context, **vnf_pack_vnfd)
        vnf_pack_vnfd_obj.create()
        self.vnf_package_vnfd = vnf_pack_vnfd_obj
        vnf_package.vnf_package = "ONBOARDED"
        vnf_package.save()
        return vnf_package

    def _create_vnf_instance(self):
        vnf_instance_data = fakes.get_vnf_instance_data(self.vnfd.id)
        vnf_instance = objects.VnfInstance(context=self.context,
                                           **vnf_instance_data)
        vnf_instance.create()

        vnf_instance.vim_connection_info = [self.vim_connection_info]
        vnf_instance.save()

        vnf_instance.vim_connection_info = [self.vim_connection_info]
        vnf_instance.save()
        return vnf_instance

    def _create_vim_connection_info(self):
        vim_connection_info_data = {
            'id': self.vims.id,
            'vim_id': self.vims.id,
            'vim_type': 'openstack',
            "interface_info": {
                "endpoint": "endpoint_value"},
            "access_info": {
                "username": "username_value",
                "password": "password_value",
                "region": "region_value",
                "tenant": "tenant_value"},
            "extra": {"key": "val"}}
        vim_connection_info = objects.VimConnectionInfo(
            context=self.context, **vim_connection_info_data)
        return vim_connection_info

    def _create_vnf_instantiated_info(self, vnf_inst_id=None):
        if not vnf_inst_id:
            vnf_inst_id = self.vnf_instance.id
        data = {
            'flavour_id': 'test_flavour',
            'vnf_state': 'STARTED',
            'scale_status': [self.scale_status],
            'ext_cp_info': self.vnf_external_cp_infos,
            'vnf_instance_id': vnf_inst_id,
            'ext_virtual_link_info': [self.ext_virtual_link_info],
            'ext_managed_virtual_link_info': [
                self.ext_managed_virtual_link_info],
            'vnfc_resource_info': self.vnfc_resource_infos,
            'vnf_virtual_link_resource_info':
                self.virtual_link_resource_infos,
            'virtual_storage_resource_info':
                self.virtual_storage_resource_infos,
            'vnfc_info': self.vnfc_infos}
        instantiated_vnf_info = objects.InstantiatedVnfInfo(
            context=self.context, **data)
        instantiated_vnf_info.save()
        return instantiated_vnf_info

    def _create_scale_status(self):
        data = {
            'aspect_id': 'VDU_2',
            'scale_level': 0}
        scale_status = objects.ScaleInfo(**data)
        return scale_status

    def _create_vnf_external_cp_info(self):
        vnf_external_cp_infos = list()
        data_0 = {
            'id': uuidsentinel.vdu0_cp1_id,
            'cpd_id': "VDU0_CP1",
            'cp_protocol_info': [self.cp_protocol_infos["VDU0_CP1"]],
            'associated_vnfc_cp_id': uuidsentinel.vdu_0_id}
        ext_cp_info_0 = objects.VnfExtCpInfo(
            context=self.context, **data_0)
        vnf_external_cp_infos.append(ext_cp_info_0)

        data_1 = {
            'id': uuidsentinel.vdu1_cp1_id,
            'cpd_id': "VDU1_CP1",
            'cp_protocol_info': [self.cp_protocol_infos["VDU1_CP1"]],
            'associated_vnfc_cp_id': uuidsentinel.vdu_1_id}
        ext_cp_info_1 = objects.VnfExtCpInfo(
            context=self.context, **data_1)
        vnf_external_cp_infos.append(ext_cp_info_1)

        data_2 = {
            'id': uuidsentinel.vdu2_cp1_id,
            'cpd_id': "VDU2_CP1",
            'cp_protocol_info': [self.cp_protocol_infos["VDU2_CP1"]],
            'associated_vnfc_cp_id': uuidsentinel.vdu_2_id}
        ext_cp_info_2 = objects.VnfExtCpInfo(
            context=self.context, **data_2)
        vnf_external_cp_infos.append(ext_cp_info_2)

        return vnf_external_cp_infos

    def _create_cp_protocol_info(self):
        cp_protocol_infos = dict()
        data_0 = {
            'layer_protocol': 'IP_OVER_ETHERNET',
            'ip_over_ethernet': self.ip_over_ethernet_infos["VDU0_CP1"]}
        cp_protocol_info_0 = objects.CpProtocolInfo(
            context=self.context, **data_0)
        cp_protocol_infos["VDU0_CP1"] = cp_protocol_info_0

        data_1 = {
            'layer_protocol': 'IP_OVER_ETHERNET',
            'ip_over_ethernet': self.ip_over_ethernet_infos["VDU1_CP1"]}
        cp_protocol_info_1 = objects.CpProtocolInfo(
            context=self.context, **data_1)
        cp_protocol_infos["VDU1_CP1"] = cp_protocol_info_1

        data_2 = {
            'layer_protocol': 'IP_OVER_ETHERNET',
            'ip_over_ethernet': self.ip_over_ethernet_infos["VDU2_CP1"]}
        cp_protocol_info_2 = objects.CpProtocolInfo(
            context=self.context, **data_2)
        cp_protocol_infos["VDU2_CP1"] = cp_protocol_info_2
        return cp_protocol_infos

    def _create_ip_over_ethernet_info(self):
        ip_over_ethernet_infos = dict()
        data_0 = {'ip_addresses': [self.ip_addresses_infos["VDU0_CP1"]]}
        ip_over_ethernet_info_0 = objects.IpOverEthernetAddressInfo(
            context=self.context, **data_0)
        ip_over_ethernet_infos["VDU0_CP1"] = ip_over_ethernet_info_0

        data_1 = {'ip_addresses': [self.ip_addresses_infos["VDU1_CP1"]]}
        ip_over_ethernet_info_1 = objects.IpOverEthernetAddressInfo(
            context=self.context, **data_1)
        ip_over_ethernet_infos["VDU1_CP1"] = ip_over_ethernet_info_1

        data_2 = {'ip_addresses': [self.ip_addresses_infos["VDU2_CP1"]]}
        ip_over_ethernet_info_2 = objects.IpOverEthernetAddressInfo(
            context=self.context, **data_2)
        ip_over_ethernet_infos["VDU2_CP1"] = ip_over_ethernet_info_2

        return ip_over_ethernet_infos

    def _create_ip_addresses_info(self):
        ip_address_infos = dict()
        data_0 = {
            'type': 'IPV4',
            'subnet_id': uuidsentinel.subet_id,
            'is_dynamic': False,
            'addresses': ["192.168.0.1"]}
        ip_address_info_0 = objects.IpAddress(
            context=self.context, **data_0)
        ip_address_infos["VDU0_CP1"] = ip_address_info_0

        data_1 = data_0
        data_1["addresses"] = ["192.168.0.2"]
        ip_address_info_1 = objects.IpAddress(
            context=self.context, **data_1)
        ip_address_infos["VDU1_CP1"] = ip_address_info_1

        data_2 = data_0
        data_2["addresses"] = ["192.168.0.3"]
        ip_address_info_2 = objects.IpAddress(
            context=self.context, **data_2)
        ip_address_infos["VDU2_CP1"] = ip_address_info_2

        return ip_address_infos

    def _create_ext_virtual_link_info(self):
        data = {
            'id': "ext_vl",
            'resource_handle': self.resource_handle_infos["ext_vl"],
            'ext_link_ports': [self.ext_link_port_info]}
        ext_virtual_link_info = objects.ExtVirtualLinkInfo(
            context=self.context, **data)
        return ext_virtual_link_info

    def _create_resource_handle(self):
        resource_handle_infos = dict()
        data_ext_vl = {'resource_id': uuidsentinel.ext_vl_res_id}
        resource_handle_infos["ext_vl"] = objects.ResourceHandle(
            context=self.context, **data_ext_vl)

        data_int_vl = {'resource_id': uuidsentinel.int_vl_res_id}
        resource_handle_infos["int_vl"] = objects.ResourceHandle(
            context=self.context, **data_int_vl)

        data_ext_managed_vl = {
            'resource_id': uuidsentinel.ext_managed_vl_res_id}
        resource_handle_infos["ext_managed_vl"] = objects.ResourceHandle(
            context=self.context, **data_ext_managed_vl)

        data_virtual_storage = {
            'resource_id': uuidsentinel.virtual_storage_id}
        resource_handle_infos["virtual_storage"] = objects.ResourceHandle(
            context=self.context, **data_virtual_storage)

        data_vdu0_cp0 = {'resource_id': uuidsentinel.vdu0_cp0_id}
        resource_handle_infos["VDU0_CP0"] = objects.ResourceHandle(
            context=self.context, **data_vdu0_cp0)

        data_vdu1_cp0 = {'resource_id': uuidsentinel.vdu1_cp0_id}
        resource_handle_infos["VDU1_CP0"] = objects.ResourceHandle(
            context=self.context, **data_vdu1_cp0)

        data_vdu0_cp2 = {'resource_id': uuidsentinel.vdu0_cp2_id}
        resource_handle_infos["VDU0_CP2"] = objects.ResourceHandle(
            context=self.context, **data_vdu0_cp2)

        data_vdu0_cp1 = {'resource_id': uuidsentinel.vdu0_cp1_id}
        resource_handle_infos["VDU0_CP1"] = objects.ResourceHandle(
            context=self.context, **data_vdu0_cp1)

        data_vdu1_cp1 = {'resource_id': uuidsentinel.vdu1_cp1_id}
        resource_handle_infos["VDU1_CP1"] = objects.ResourceHandle(
            context=self.context, **data_vdu1_cp1)
        data_vdu_0 = {'resource_id': uuidsentinel.vdu_0_id}
        resource_handle_infos["VDU_0"] = objects.ResourceHandle(
            context=self.context, **data_vdu_0)

        data_vdu_1 = {'resource_id': uuidsentinel.vdu_0_id}
        resource_handle_infos["VDU_1"] = objects.ResourceHandle(
            context=self.context, **data_vdu_1)
        return resource_handle_infos

    def _create_ext_link_port_info(self):
        ext_link_port_info = copy.deepcopy(fakes.ext_link_port_info)
        ext_link_port_info.update(
            {'resource_handle': self.resource_handle_infos["ext_vl"]})
        ext_link_port_info = objects.ExtLinkPortInfo(
            context=self.context, **ext_link_port_info)
        return ext_link_port_info

    def _create_ext_managed_virtual_link_info(self):
        data = {
            'id': uuidsentinel.vnf_vl_id,
            'vnf_virtual_link_desc_id': "ext_managed_vl",
            'network_resource': self.resource_handle_infos["ext_managed_vl"],
            'vnf_link_ports': self.vnf_link_ports_infos["ext_managed_vl"]}
        ext_managed_virtual_link_info = objects.ExtManagedVirtualLinkInfo(
            context=self.context, **data)
        return ext_managed_virtual_link_info

    def _create_vnf_link_ports(self):
        def _get_cp_id(vnfc_res_infos, vdu, cp):
            for vnfc_res_info in vnfc_res_infos:
                if vnfc_res_info.vdu_id == vdu:
                    for cp_info in vnfc_res_info.vnfc_cp_info:
                        if cp_info.cpd_id == cp:
                            return cp_info.id
            return None

        vnf_link_ports_infos = dict()

        vnf_link_ports_infos["ext_managed_vl"] = list()
        data_0 = {
            'id': self.vnfc_cp_infos["VDU_0"][2].vnf_link_port_id,
            'resource_handle': self.resource_handle_infos["VDU0_CP2"],
            'cp_instance_id':
                _get_cp_id(self.vnfc_resource_infos, "VDU_0", "VDU0_CP2")}
        vnf_link_ports_info_0 = objects.VnfLinkPortInfo(
            context=self.context, **data_0)
        vnf_link_ports_infos["ext_managed_vl"].append(vnf_link_ports_info_0)

        vnf_link_ports_infos["int_vl"] = list()
        data_1 = {
            'id': self.vnfc_cp_infos["VDU_0"][0].vnf_link_port_id,
            'resource_handle': self.resource_handle_infos["VDU0_CP0"],
            'cp_instance_id':
                _get_cp_id(self.vnfc_resource_infos, "VDU_0", "VDU0_CP0")}
        vnf_link_ports_info_1 = objects.VnfLinkPortInfo(
            context=self.context, **data_1)
        vnf_link_ports_infos["int_vl"].append(vnf_link_ports_info_1)

        data_2 = {
            'id': self.vnfc_cp_infos["VDU_1"][0].vnf_link_port_id,
            'resource_handle': self.resource_handle_infos["VDU1_CP0"],
            'cp_instance_id':
                _get_cp_id(self.vnfc_resource_infos, "VDU_1", "VDU1_CP0")}
        vnf_link_ports_info_2 = objects.VnfLinkPortInfo(
            context=self.context, **data_2)
        vnf_link_ports_infos["int_vl"].append(vnf_link_ports_info_2)

        vnf_link_ports_infos["ext_vl"] = list()
        data_3 = {
            'id': self.vnfc_cp_infos["VDU_0"][1].vnf_link_port_id,
            'resource_handle': self.resource_handle_infos["VDU0_CP1"],
            'cp_instance_id':
                _get_cp_id(self.vnfc_resource_infos, "VDU_0", "VDU0_CP1")}
        vnf_link_ports_info_3 = objects.VnfLinkPortInfo(
            context=self.context, **data_3)
        vnf_link_ports_infos["ext_vl"].append(vnf_link_ports_info_3)

        data_4 = {
            'id': self.vnfc_cp_infos["VDU_1"][1].vnf_link_port_id,
            'resource_handle': self.resource_handle_infos["VDU1_CP1"],
            'cp_instance_id':
                _get_cp_id(self.vnfc_resource_infos, "VDU_1", "VDU1_CP1")}
        vnf_link_ports_info_4 = objects.VnfLinkPortInfo(
            context=self.context, **data_4)
        vnf_link_ports_infos["ext_vl"].append(vnf_link_ports_info_4)
        return vnf_link_ports_infos

    def _create_vnfc_resource_info(self):
        vnfc_resource_infos = list()
        data_0 = {
            'id': uuidsentinel.vdu_0_id,
            'vdu_id': 'VDU_0',
            'compute_resource': self.resource_handle_infos["VDU_0"],
            'storage_resource_ids':
                [storage_res_info.storage_resource.resource_id for
                 storage_res_info in self.virtual_storage_resource_infos],
            'vnfc_cp_info': self.vnfc_cp_infos["VDU_0"]}
        vnfc_resource_infos.append(objects.VnfcResourceInfo(
            context=self.context, **data_0))

        data_1 = {
            'id': uuidsentinel.vdu_1_id,
            'vdu_id': 'VDU_1',
            'compute_resource': self.resource_handle_infos["VDU_1"],
            'vnfc_cp_info': self.vnfc_cp_infos["VDU_1"]}
        vnfc_resource_infos.append(objects.VnfcResourceInfo(
            context=self.context, **data_1))

        return vnfc_resource_infos

    def _create_vnfc_cp_info(self):
        vnfc_cp_infos = dict()

        vnfc_cp_infos["VDU_0"] = list()
        data_vdu0_cp0 = {
            'id': uuidsentinel.vdu0_cp0_id,
            'cpd_id': "VDU0_CP0",
            'vnf_link_port_id': uuidsentinel.vdu0_cp0_link_port_id}
        vnfc_cp_infos["VDU_0"].append(objects.VnfcCpInfo(
            context=self.context, **data_vdu0_cp0))

        data_vdu0_cp1 = {
            'id': uuidsentinel.vdu0_cp1_id,
            'cpd_id': "VDU0_CP1",
            'vnf_link_port_id': uuidsentinel.vdu0_cp1_link_port_id,
            "cp_protocol_info": [self.cp_protocol_infos["VDU0_CP1"]]}
        vnfc_cp_infos["VDU_0"].append(objects.VnfcCpInfo(
            context=self.context, **data_vdu0_cp1))

        data_vdu0_cp2 = {
            'id': uuidsentinel.vdu0_cp2_id,
            'cpd_id': "VDU0_CP2",
            'vnf_link_port_id': uuidsentinel.vdu0_cp2_link_port_id}
        vnfc_cp_infos["VDU_0"].append(objects.VnfcCpInfo(
            context=self.context, **data_vdu0_cp2))

        vnfc_cp_infos["VDU_1"] = list()
        data_vdu1_cp0 = {
            'id': uuidsentinel.vdu1_cp0_id,
            'cpd_id': "VDU1_CP0",
            'vnf_link_port_id': uuidsentinel.vdu1_cp0_link_port_id}
        vnfc_cp_infos["VDU_1"].append(objects.VnfcCpInfo(
            context=self.context, **data_vdu1_cp0))

        data_vdu1_cp1 = {
            'id': uuidsentinel.vdu1_cp1_id,
            'cpd_id': "VDU1_CP1",
            'vnf_link_port_id': uuidsentinel.vdu1_cp1_link_port_id,
            "cp_protocol_info": [self.cp_protocol_infos["VDU1_CP1"]]}
        vnfc_cp_infos["VDU_1"].append(objects.VnfcCpInfo(
            context=self.context, **data_vdu1_cp1))

        vnfc_cp_infos["VDU_2"] = list()
        data_vdu2_cp0 = {
            'id': uuidsentinel.vdu2_cp0_id,
            'cpd_id': "VDU2_CP0",
            'vnf_link_port_id': self.vl_res_info_int_vl_id}
        vnfc_cp_infos["VDU_2"].append(objects.VnfcCpInfo(
            context=self.context, **data_vdu2_cp0))

        data_vdu2_cp1 = {
            'id': uuidsentinel.vdu2_cp1_id,
            'cpd_id': "VDU2_CP1",
            'vnf_link_port_id': self.vl_res_info_ext_vl_id,
            "cp_protocol_info": [self.cp_protocol_infos["VDU2_CP1"]]}
        vnfc_cp_infos["VDU_2"].append(objects.VnfcCpInfo(
            context=self.context, **data_vdu2_cp1))
        return vnfc_cp_infos

    def _create_virtual_link_resource_info(self):
        vnf_virtual_link_resource_infos = list()

        data_0 = {
            'id': self.vl_res_info_int_vl_id,
            'vnf_virtual_link_desc_id': "int_vl",
            'network_resource': self.resource_handle_infos["int_vl"],
            'vnf_link_ports': self.vnf_link_ports_infos["int_vl"]}
        vnf_virtual_link_resource_info_0 = objects.VnfVirtualLinkResourceInfo(
            context=self.context, **data_0)
        vnf_virtual_link_resource_infos.append(
            vnf_virtual_link_resource_info_0)

        data_1 = {
            'id': self.vl_res_info_ext_vl_id,
            'vnf_virtual_link_desc_id': "ext_vl",
            'network_resource': self.resource_handle_infos["ext_vl"],
            'vnf_link_ports': self.vnf_link_ports_infos["ext_vl"]}
        vnf_virtual_link_resource_info_1 = objects.VnfVirtualLinkResourceInfo(
            context=self.context, **data_1)
        vnf_virtual_link_resource_infos.append(
            vnf_virtual_link_resource_info_1)
        return vnf_virtual_link_resource_infos

    def _create_virtual_storage_resource_info(self):
        virtual_storage_resource_infos = list()
        data = {
            'id': uuidsentinel.virtual_storage_resource_id,
            'virtual_storage_desc_id': uuidsentinel.virtual_storage_desc_id,
            'storage_resource': self.resource_handle_infos["virtual_storage"]}
        virtual_storage_resource_infos.append(
            objects.VirtualStorageResourceInfo(context=self.context, **data))
        return virtual_storage_resource_infos

    def _create_vnfc_info(self):
        vnfc_infos = list()
        data_0 = {
            "id": uuidsentinel.vdu_0_vnfc_id,
            "vdu_id": "VDU_0",
            "vnfc_state": "STARTED"}
        vnfc_infos.append(objects.VnfcInfo(
            context=self.context, **data_0))

        data_1 = {
            "id": uuidsentinel.vdu_1_vnfc_id,
            "vdu_id": "VDU_1",
            "vnfc_state": "STARTED"}
        vnfc_infos.append(objects.VnfcInfo(
            context=self.context, **data_1))

        return vnfc_infos

    def _create_vnf_lcm_op_occs_for_v2_inst_test(self):
        id_0 = uuidsentinel.id_0
        vnf_lcm_op_occs_data_0 = \
            fakes.get_lcm_op_occs_data(id_0, self.vnf_instance.id)
        operation_params = {
            "flavourId": "default",
            "extVirtualLinks": [{
                "extCps": [{
                    "cpConfig": [{
                        "cpProtocolData": [{
                            "layerProtocol": "IP_OVER_ETHERNET",
                            "ipOverEthernet": {
                                "ipAddresses": [{
                                    "subnetId":
                                        "31c9f520-810c-4feb-8828-fdeea7b38c92",
                                    "type": "IPV4",
                                    "fixedAddresses": ["192.168.0.1"]}]}}]}],
                    "cpdId": "VDU0_CP1"}, {
                    "cpConfig": [{
                        "cpProtocolData": [{
                            "layerProtocol": "IP_OVER_ETHERNET",
                            "ipOverEthernet": {
                                "ipAddresses": [{
                                    "subnetId":
                                        "31c9f520-810c-4feb-8828-fdeea7b38c92",
                                    "type": "IPV4",
                                    "fixedAddresses": ["192.168.0.2"]}]}}]}],
                    "cpdId": "VDU1_CP1"}, {
                    "cpConfig": [{
                        "cpProtocolData": [{
                            "layerProtocol": "IP_OVER_ETHERNET",
                            "ipOverEthernet": {
                                "ipAddresses": [{
                                    "subnetId":
                                        "31c9f520-810c-4feb-8828-fdeea7b38c92",
                                    "type": "IPV4",
                                    "fixedAddresses": ["192.168.0.3"]}]}}]}],
                    "cpdId": "VDU2_CP1"}],
                "id": self.ext_virtual_link_info.id,
                "resourceId":
                    self.ext_virtual_link_info.resource_handle.resource_id}]}
        vnf_lcm_op_occs_data_0.update({
            "operation_state": "COMPLETED",
            "operation": "INSTANTIATE",
            "operation_params": str(operation_params)})
        vnf_lcm_op_occs_0 = objects.vnf_lcm_op_occs.VnfLcmOpOcc(
            context=self.context, **vnf_lcm_op_occs_data_0)
        vnf_lcm_op_occs_0.create()

        id_1 = uuidsentinel.id_1
        vnf_lcm_op_occs_data_1 = \
            fakes.get_lcm_op_occs_data(id_1, self.vnf_instance.id)
        operation_params = {
            "extVirtualLinks": [{
                "extCps": [{
                    "cpConfig": [{
                        "cpProtocolData": [{
                            "layerProtocol": "IP_OVER_ETHERNET",
                            "ipOverEthernet": {
                                "ipAddresses": [{
                                    "subnetId":
                                        "31c9f520-810c-4feb-8828-fdeea7b38c92",
                                    "type": "IPV4",
                                    "fixedAddresses": ["192.168.0.4"]}]}}]}],
                    "cpdId": "VDU0_CP1"}],
                "id": self.ext_virtual_link_info.id,
                "resourceId":
                    self.ext_virtual_link_info.resource_handle.resource_id}]}
        vnf_lcm_op_occs_data_1.update({
            "operation_state": "COMPLETED",
            "start_time":
                datetime.datetime(1900, 1, 1, 1, 1, 2, tzinfo=iso8601.UTC),
            "operation": "CHANGE_EXT_CONN",
            "operation_params": str(operation_params)})
        vnf_lcm_op_occs_1 = objects.vnf_lcm_op_occs.VnfLcmOpOcc(
            context=self.context, **vnf_lcm_op_occs_data_1)
        vnf_lcm_op_occs_1.create()
        return [vnf_lcm_op_occs_0, vnf_lcm_op_occs_1]

    def _set_inst_and_lcmoccs(self, inst_state, op_state):
        inst = objects_v2.VnfInstanceV2(
            # required fields
            id=uuidutils.generate_uuid(),
            vnfdId=uuidutils.generate_uuid(),
            vnfProvider='provider',
            vnfProductName='product name',
            vnfSoftwareVersion='software version',
            vnfdVersion='vnfd version',
            instantiationState=inst_state
        )

        req = {"flavourId": "simple"}  # instantiate request
        lcmocc0 = objects_v2.VnfLcmOpOccV2(
            # required fields
            id=uuidutils.generate_uuid(),
            operationState=op_state,
            stateEnteredTime=datetime.datetime.utcnow(),
            startTime=datetime.datetime.utcnow(),
            vnfInstanceId=inst.id,
            operation=fields_v2.LcmOperationType.INSTANTIATE,
            isAutomaticInvocation=False,
            isCancelPending=False,
            operationParams=req
        )

        lcmocc1 = objects_v2.VnfLcmOpOccV2(
            # required fields
            id=uuidutils.generate_uuid(),
            operationState=op_state,
            stateEnteredTime=datetime.datetime.utcnow(),
            startTime=datetime.datetime.utcnow(),
            vnfInstanceId=inst.id,
            operation=fields_v2.LcmOperationType.INSTANTIATE,
            isAutomaticInvocation=False,
            isCancelPending=False,
            operationParams=req
        )
        return inst, lcmocc0, lcmocc1

    def _create_inst_and_lcmoccs(self, inst_state, op_state):
        inst, lcmocc0, lcmocc1 = self._set_inst_and_lcmoccs(inst_state,
                op_state)

        inst.create(self.context)
        lcmocc0.create(self.context)
        lcmocc1.create(self.context)

        return inst.id, lcmocc0.id, lcmocc1.id

    def test_get_all_vnfs(self):
        iteration = 10
        for i in range(iteration):
            _vnf_instance = self._create_vnf_instance()
            self._create_vnf_instantiated_info(_vnf_instance.id)
            self._create_vnf_attributes(_vnf_instance.id)
            self._create_vnf(_vnf_instance.id)

        vnfs = migrate_to_v2.get_all_vnfs(self.context)
        self.assertEqual(len(vnfs), iteration + 1)

        self.vnf_instance.destroy(self.context)
        vnfs = migrate_to_v2.get_all_vnfs(self.context)
        self.assertEqual(len(vnfs), iteration)

    def test_mark_delete_v1(self):
        vnf_id = self.vnf_instance.id

        _vnf_instance = objects.vnf_instance._vnf_instance_get_by_id(
            self.context,
            vnf_id, columns_to_join=["instantiated_vnf_info"],
            read_deleted="yes")
        self.assertEqual(_vnf_instance.deleted, 0)
        _vnf_info = _vnf_instance.instantiated_vnf_info
        self.assertTrue(_vnf_info)

        _vnf = api.model_query(self.context, vnfm_db.VNF)\
            .filter_by(id=vnf_id).first()
        self.assertEqual(_vnf.status, 'ACTIVE')
        _vnf_attribute = api.model_query(self.context, vnfm_db.VNFAttribute)\
            .filter_by(vnf_id=vnf_id).first()
        self.assertTrue(_vnf_attribute)

        _vnf_lcm_op_occs = api.model_query(self.context, models.VnfLcmOpOccs)\
            .filter_by(vnf_instance_id=vnf_id)
        for _vnf_lcm_op_occ in _vnf_lcm_op_occs:
            self.assertEqual(_vnf_lcm_op_occ.deleted, 0)

        vnf_inst, vnf_attrs, vnf, occs = \
            migrate_to_v2.mark_delete_v1(self.context, vnf_id)

        self.assertEqual(vnf_inst.deleted, 1)
        self.assertFalse(vnf_inst.instantiated_vnf_info)

        self.assertEqual(vnf.status, 'PENDING_DELETE')
        self.assertFalse(vnf_attrs)

        for occ in occs:
            self.assertEqual(occ.deleted, 1)

    def test_mark_delete_v2(self):
        vnf_id, lcmocc0_id, lcmocc1_id = self._create_inst_and_lcmoccs(
            'INSTANTIATED',
            fields_v2.LcmOperationStateType.COMPLETED)

        migrate_to_v2.mark_delete_v2(self.context, vnf_id)

        vnf_inst_v2 = objects_v2.VnfInstanceV2.get_by_id(
            self.context, vnf_id)
        op_occs_v2 = objects_v2.VnfLcmOpOccV2.get_by_filter(
            self.context, vnfInstanceId=vnf_id)
        self.assertIsNone(vnf_inst_v2)
        self.assertEqual(op_occs_v2, [])

    def test_create_vnf_instance_v2(self):
        def _assert_resouce_handle(res_handle_v1, res_handle_v2):
            self.assertEqual(res_handle_v2.vimConnectionId,
                             res_handle_v1.vim_connection_id)
            self.assertEqual(res_handle_v2.resourceId,
                             res_handle_v1.resource_id)
            self.assertEqual(res_handle_v2.vimLevelResourceType,
                             res_handle_v1.vim_level_resource_type)

        self._create_vnf_lcm_op_occs_for_v2_inst_test()
        vnf_instance_v1 = self.vnf_instance
        vnf_v1 = self.vnf
        vnf_instance_v2 = \
            migrate_to_v2.create_vnf_instance_v2(self.context, vnf_v1.id)

        # VnfInstanceV2 object
        self.assertEqual(vnf_instance_v2.id, vnf_instance_v1.id)
        self.assertEqual(vnf_instance_v2.vnfInstanceName,
                         vnf_instance_v1.vnf_instance_name)
        self.assertEqual(vnf_instance_v2.vnfInstanceDescription,
                         vnf_instance_v1.vnf_instance_description)
        self.assertEqual(vnf_instance_v2.vnfdId, vnf_instance_v1.vnfd_id)
        self.assertEqual(vnf_instance_v2.vnfProvider,
                         vnf_instance_v1.vnf_provider)
        self.assertEqual(vnf_instance_v2.vnfProductName,
                         vnf_instance_v1.vnf_product_name)
        self.assertEqual(vnf_instance_v2.vnfSoftwareVersion,
                         vnf_instance_v1.vnf_software_version)
        self.assertEqual(vnf_instance_v2.vnfdVersion,
                         vnf_instance_v1.vnfd_version)
        self.assertEqual(vnf_instance_v2.vnfConfigurableProperties,
                         self.valid_configurable_properties[
                             "configurable_properties"])

        # vimConnectionInfo
        vim_conn_info_v2 = vnf_instance_v2.vimConnectionInfo
        vim_conn_info_v1 = vnf_instance_v1.vim_connection_info
        self.assertEqual(vim_conn_info_v2["vim_0"].vimId,
                         vim_conn_info_v1[0].vim_id)
        self.assertEqual(vim_conn_info_v2["vim_0"].vimType,
                         vim_conn_info_v1[0].vim_type)
        self.assertEqual(vim_conn_info_v2["vim_0"].interfaceInfo,
                         vim_conn_info_v1[0].interface_info)
        self.assertEqual(vim_conn_info_v2["vim_0"].accessInfo,
                         vim_conn_info_v1[0].access_info)
        self.assertEqual(vim_conn_info_v2["vim_0"].extra,
                         vim_conn_info_v1[0].extra)

        self.assertEqual(vnf_instance_v2.instantiationState,
                         vnf_instance_v1.instantiation_state)

        # VnfInstanceV2_InstantiatedVnfInfo
        inst_info_v2 = vnf_instance_v2.instantiatedVnfInfo
        inst_info_v1 = self.vnf_instantiated_info
        self.assertEqual(inst_info_v2.flavourId, inst_info_v1.flavour_id)
        self.assertEqual(inst_info_v2.vnfState, inst_info_v1.vnf_state)

        # scaleStatus
        scale_status_v2 = inst_info_v2.scaleStatus
        scale_status_v1 = inst_info_v1.scale_status
        self.assertEqual(scale_status_v2[0].aspectId,
                         scale_status_v1[0].aspect_id)
        self.assertEqual(scale_status_v2[0].scaleLevel,
                         scale_status_v1[0].scale_level)

        # maxScaleLevels
        max_scale_levels_v2 = inst_info_v2.maxScaleLevels
        self.assertEqual(max_scale_levels_v2[0].aspectId, "VDU_2")
        self.assertEqual(max_scale_levels_v2[0].scaleLevel,
                         self.valid_scale_group["scaleGroupDict"][
                             "VDU_2"]["maxLevel"])

        # extCpInfo
        ext_cp_infos_v2 = inst_info_v2.extCpInfo
        ext_cp_infos_v1 = inst_info_v1.ext_cp_info
        for ext_cp_info_v2 in ext_cp_infos_v2:
            ext_cp_info_v1 = [ext_cp_info for ext_cp_info in ext_cp_infos_v1
                if ext_cp_info.cpd_id == ext_cp_info_v2.cpdId][0]
            self.assertEqual(ext_cp_info_v2.id, ext_cp_info_v1.id)
            self.assertEqual(ext_cp_info_v2.cpdId, ext_cp_info_v1.cpd_id)
            self.assertEqual(ext_cp_info_v2.cpConfigId,
                             f"{ext_cp_info_v1.cpd_id}_0")

            # cpProtocolInfo
            cp_protocol_info_v2 = ext_cp_info_v2.cpProtocolInfo
            cp_protocol_info_v1 = ext_cp_info_v1.cp_protocol_info
            self.assertEqual(cp_protocol_info_v2[0].layerProtocol,
                             cp_protocol_info_v1[0].layer_protocol)

            # ipOverEthernet
            ip_over_eth_v2 = cp_protocol_info_v2[0].ipOverEthernet
            ip_over_eth_v1 = cp_protocol_info_v1[0].ip_over_ethernet
            self.assertEqual(ip_over_eth_v2.macAddress,
                             ip_over_eth_v1.mac_address)

            # ipAddresses
            ip_addresses_v2 = ip_over_eth_v2.ipAddresses
            ip_addresses_v1 = ip_over_eth_v1.ip_addresses
            self.assertEqual(ip_addresses_v2[0].type, ip_addresses_v1[0].type)
            self.assertEqual(str(ip_addresses_v2[0].addresses[0]),
                             ip_addresses_v1[0].addresses[0])
            self.assertEqual(ip_addresses_v2[0].isDynamic,
                             ip_addresses_v1[0].is_dynamic)
            self.assertEqual(ip_addresses_v2[0].subnetId,
                             ip_addresses_v1[0].subnet_id)

        # extVirtualLinkInfo
        ext_vl_infos_v2 = inst_info_v2.extVirtualLinkInfo
        ext_vl_infos_v1 = inst_info_v1.ext_virtual_link_info
        for ext_vl_info_v2 in ext_vl_infos_v2:
            ext_vl_info_v1 = [ext_vl_info for ext_vl_info in ext_vl_infos_v1
                if ext_vl_info.id == ext_vl_info_v2.id][0]
            self.assertEqual(ext_vl_info_v2.id, ext_vl_info_v1.id)

            # resourceHandle
            res_handle_v2 = ext_vl_info_v2.resourceHandle
            res_handle_v1 = ext_vl_info_v1.resource_handle
            _assert_resouce_handle(res_handle_v1, res_handle_v2)

            # extLinkPorts
            ext_link_ports_v2 = ext_vl_info_v2.extLinkPorts
            vl_res_infos_v1 = inst_info_v1.vnf_virtual_link_resource_info
            vl_res_info_v1 = [vl_res_info for vl_res_info in vl_res_infos_v1
                if vl_res_info.vnf_virtual_link_desc_id == ext_vl_info_v2.id]
            vnf_link_ports_v1 = sorted(vl_res_info_v1[0].vnf_link_ports,
                                       key=lambda x: x.id)
            for i, ext_link_port_v2 in enumerate(sorted(ext_link_ports_v2,
                                                 key=lambda x: x["id"])):
                self.assertEqual(ext_link_port_v2.id, vnf_link_ports_v1[i].id)

                # resourceHandle
                res_handle_v2 = ext_link_port_v2.resourceHandle
                res_handle_v1 = vnf_link_ports_v1[i].resource_handle
                _assert_resouce_handle(res_handle_v1, res_handle_v2)

                self.assertEqual(ext_link_port_v2.cpInstanceId,
                                 vnf_link_ports_v1[i].cp_instance_id)

            # currentVnfExtCpData
            current_vnf_ext_cp_data_v2_list = \
                ext_vl_info_v2.currentVnfExtCpData
            current_vnf_ext_cp_data_v2_list.sort(key=lambda x: x["cpdId"])
            for i, current_vnf_ext_cp_data_v2 \
                    in enumerate(current_vnf_ext_cp_data_v2_list):
                self.assertEqual(current_vnf_ext_cp_data_v2.cpdId,
                                 f"VDU{i}_CP1")

                # cpConfig
                cp_config_v2 = current_vnf_ext_cp_data_v2.cpConfig

                # cpProtocolData
                for key, val in cp_config_v2.items():
                    self.assertEqual(key, f"VDU{i}_CP1_0")
                    cp_proto_data_v2 = val.cpProtocolData
                    self.assertEqual(cp_proto_data_v2[0].layerProtocol,
                                     "IP_OVER_ETHERNET")

                    # ipOverEthernet
                    ip_over_eth_v2 = cp_proto_data_v2[0].ipOverEthernet

                    # ipAddresses
                    ip_addresses_v2 = ip_over_eth_v2.ipAddresses
                    self.assertEqual(ip_addresses_v2[0].type, "IPV4")
                    if current_vnf_ext_cp_data_v2.cpdId == "VDU0_CP1":
                        self.assertEqual(str(ip_addresses_v2[0].
                            fixedAddresses[0]), "192.168.0.4")
                    if current_vnf_ext_cp_data_v2.cpdId == "VDU1_CP1":
                        self.assertEqual(str(ip_addresses_v2[0].
                            fixedAddresses[0]), "192.168.0.2")
                    if current_vnf_ext_cp_data_v2.cpdId == "VDU2_CP1":
                        self.assertEqual(str(ip_addresses_v2[0].
                            fixedAddresses[0]), "192.168.0.3")
                    self.assertEqual(ip_addresses_v2[0].subnetId,
                                     "31c9f520-810c-4feb-8828-fdeea7b38c92")

        # extManagedVirtualLinkInfo
        ext_mg_vl_infos_v2 = inst_info_v2.extManagedVirtualLinkInfo
        ext_mg_vl_infos_v1 = inst_info_v1.ext_managed_virtual_link_info
        for ext_mg_vl_info_v2 in ext_mg_vl_infos_v2:
            ext_mg_vl_info_v1 = [ext_mg_vl_info for ext_mg_vl_info in
                                 ext_mg_vl_infos_v1 if
                                 ext_mg_vl_info.id == ext_mg_vl_info_v2.id][0]
            self.assertEqual(ext_mg_vl_info_v2.id, ext_mg_vl_info_v1.id)
            self.assertEqual(ext_mg_vl_info_v2.vnfVirtualLinkDescId,
                             ext_mg_vl_info_v1.vnf_virtual_link_desc_id)

            # networkResource
            res_handle_v2 = ext_mg_vl_info_v2.networkResource
            res_handle_v1 = ext_mg_vl_info_v1.network_resource
            _assert_resouce_handle(res_handle_v1, res_handle_v2)

            # vnfLinkPorts
            vnf_link_ports_v2 = sorted(ext_mg_vl_info_v2.vnfLinkPorts,
                                       key=lambda x: x.id)
            vnf_link_ports_v1 = sorted(ext_mg_vl_info_v1.vnf_link_ports,
                                       key=lambda x: x.id)
            for i, vnf_link_port_v2 in enumerate(vnf_link_ports_v2):
                self.assertEqual(vnf_link_port_v2.id, vnf_link_ports_v1[i].id)

                # ResourceHandle
                res_handle_v2 = vnf_link_port_v2.resourceHandle
                res_handle_v1 = vnf_link_ports_v1[i].resource_handle
                _assert_resouce_handle(res_handle_v1, res_handle_v2)

                self.assertEqual(vnf_link_port_v2.cpInstanceId,
                                 vnf_link_ports_v1[i].cp_instance_id)
                self.assertEqual(vnf_link_port_v2.cpInstanceType, "VNFC_CP")

        # monitoringParameters
        monitoring_params_v2 = inst_info_v2.monitoringParameters
        monitoring_params_v1 = \
            self.valid_monitoring_parameters["monitoring_parameters"]
        self.assertEqual(monitoring_params_v2[0].id,
                         monitoring_params_v1[0]["id"])
        self.assertEqual(monitoring_params_v2[0].name,
                         monitoring_params_v1[0]["name"])
        self.assertEqual(monitoring_params_v2[0].performanceMetric,
                         monitoring_params_v1[0]["performance_metric"])

        # vnfcResourceInfo
        vnfc_res_infos_v2 = sorted(inst_info_v2.vnfcResourceInfo,
                                   key=lambda x: x.id)
        vnfc_res_infos_v1 = sorted(inst_info_v1.vnfc_resource_info,
                                   key=lambda x: x.id)
        for i, vnfc_res_info_v2 in enumerate(vnfc_res_infos_v2):
            vnfc_res_info_v1 = vnfc_res_infos_v1[i]
            self.assertEqual(vnfc_res_info_v2.id, vnfc_res_info_v1.id)
            self.assertEqual(vnfc_res_info_v2.vduId, vnfc_res_info_v1.vdu_id)

            # computeResource
            res_handle_v2 = vnfc_res_info_v2.computeResource
            res_handle_v1 = vnfc_res_info_v1.compute_resource
            _assert_resouce_handle(res_handle_v1, res_handle_v2)

            self.assertEqual(vnfc_res_info_v2.storageResourceIds,
                             vnfc_res_info_v1.storage_resource_ids)

            # vnfcCpInfo
            vnfc_cp_infos_v2 = sorted(vnfc_res_info_v2.vnfcCpInfo,
                                      key=lambda x: x.id)
            vnfc_cp_infos_v1 = sorted(vnfc_res_info_v1.vnfc_cp_info,
                                      key=lambda x: x.id)
            for i, vnfc_cp_info_v2 in enumerate(vnfc_cp_infos_v2):
                self.assertEqual(vnfc_cp_info_v2.id, vnfc_cp_infos_v1[i].id)
                self.assertEqual(vnfc_cp_info_v2.cpdId,
                                 vnfc_cp_infos_v1[i].cpd_id)
                if vnfc_cp_info_v2.cpdId[-1] == "1":
                    self.assertEqual(vnfc_cp_info_v2.vnfExtCpId,
                                     vnfc_cp_infos_v1[i].vnf_link_port_id)
                else:
                    self.assertEqual(vnfc_cp_info_v2.vnfLinkPortId,
                                     vnfc_cp_infos_v1[i].vnf_link_port_id)

            self.assertEqual(vnfc_res_info_v2.metadata,
                             vnfc_res_info_v1.metadata)

        # vnfVirtualLinkResourceInfo
        vl_res_infos_v2 = inst_info_v2.vnfVirtualLinkResourceInfo
        vl_res_infos_v1 = inst_info_v1.vnf_virtual_link_resource_info
        vl_res_info_v1 = [vl_res_info_v1 for vl_res_info_v1 in vl_res_infos_v1
                          if vl_res_info_v1.id == vl_res_infos_v2[0].id][0]
        self.assertEqual(vl_res_infos_v2[0].id, vl_res_info_v1.id)
        self.assertEqual(vl_res_infos_v2[0].vnfVirtualLinkDescId,
                         vl_res_info_v1.vnf_virtual_link_desc_id)

        # computeResource
        res_handle_v2 = vl_res_infos_v2[0].networkResource
        res_handle_v1 = vl_res_info_v1.network_resource
        _assert_resouce_handle(res_handle_v1, res_handle_v2)

        # vnfLinkPorts
        vnf_link_ports_v2 = sorted(vl_res_infos_v2[0].vnfLinkPorts,
                                   key=lambda x: x.id)
        vnf_link_ports_v1 = sorted(vl_res_info_v1.vnf_link_ports,
                                   key=lambda x: x.id)
        for i, vnf_link_port_v2 in enumerate(vnf_link_ports_v2):
            self.assertEqual(vnf_link_port_v2.id, vnf_link_ports_v1[i].id)

            # ResourceHandle
            res_handle_v2 = vnf_link_port_v2.resourceHandle
            res_handle_v1 = vnf_link_ports_v1[i].resource_handle
            _assert_resouce_handle(res_handle_v1, res_handle_v2)

            self.assertEqual(vnf_link_port_v2.cpInstanceId,
                             vnf_link_ports_v1[i].cp_instance_id)
            self.assertEqual(vnf_link_port_v2.cpInstanceType, "VNFC_CP")

        # VirtualStorageResourceInfo
        storage_res_infos_v2 = \
            sorted(inst_info_v2.virtualStorageResourceInfo, key=lambda x: x.id)
        storage_res_infos_v1 = \
            sorted(inst_info_v1.virtual_storage_resource_info,
                   key=lambda x: x.id)
        for i, storage_res_info_v2 in enumerate(storage_res_infos_v2):
            self.assertEqual(storage_res_info_v2.id,
                             storage_res_infos_v1[i].id)
            self.assertEqual(storage_res_info_v2.virtualStorageDescId,
                             storage_res_infos_v1[i].virtual_storage_desc_id)

            # ResourceHandle
            res_handle_v2 = storage_res_info_v2.storageResource
            res_handle_v1 = storage_res_infos_v1[i].storage_resource
            _assert_resouce_handle(res_handle_v1, res_handle_v2)

        # vnfcInfo
        vnfc_infos_v2 = sorted(inst_info_v2.vnfcInfo, key=lambda x: x.id)
        vnfc_res_infos_v1 = sorted(inst_info_v1.vnfc_resource_info,
                                   key=lambda x: (x.vdu_id, x.id))
        for i, vnfc_info_v2 in enumerate(vnfc_infos_v2):
            self.assertEqual(
                vnfc_info_v2.id,
                f"{vnfc_res_infos_v1[i].vdu_id}-{vnfc_res_infos_v1[i].id}")
            self.assertEqual(vnfc_info_v2.vduId, vnfc_res_infos_v1[i].vdu_id)
            self.assertEqual(vnfc_info_v2.vnfcResourceInfoId,
                             vnfc_res_infos_v1[i].id)
            self.assertEqual(vnfc_info_v2.vnfcState, "STARTED")

    @mock.patch.object(inst_utils, 'get_inst')
    def test_create_vnf_lcm_op_occ_v2(self, mock_inst):
        vim_connection_info = objects_v2.VimConnectionInfo.from_dict({
            "vimId": uuidutils.generate_uuid(),
            "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_3"
        })
        mock_inst.return_value = objects_v2.VnfInstanceV2(
            id=uuidutils.generate_uuid(),
            vnfdId=uuidutils.generate_uuid(),
            vnfProvider='provider',
            vnfProductName='product name',
            vnfSoftwareVersion='software version',
            vnfdVersion='vnfd version',
            instantiationState='INSTANTIATED',
            vimConnectionInfo={"vim_0": vim_connection_info}
        )
        vnf_lcm_op_occs_v1 = self.vnf_lcm_op_occs
        vnf_lcm_op_occs_v2 = \
            migrate_to_v2.create_vnf_lcm_op_occs_v2(self.context,
                                                    self.vnf_instance.id)

        self.assertEqual(len(vnf_lcm_op_occs_v1), len(vnf_lcm_op_occs_v2))

        for i in range(len(vnf_lcm_op_occs_v1)):
            self.assertEqual(vnf_lcm_op_occs_v1[i].id,
                             vnf_lcm_op_occs_v2[i].id)
            self.assertEqual(vnf_lcm_op_occs_v1[i].operation_state,
                             vnf_lcm_op_occs_v2[i].operationState)
            self.assertEqual(vnf_lcm_op_occs_v1[i].state_entered_time,
                             vnf_lcm_op_occs_v2[i].stateEnteredTime)
            self.assertEqual(vnf_lcm_op_occs_v1[i].start_time,
                             vnf_lcm_op_occs_v2[i].startTime)
            self.assertEqual(vnf_lcm_op_occs_v1[i].vnf_instance_id,
                             vnf_lcm_op_occs_v2[i].vnfInstanceId)
            self.assertEqual(vnf_lcm_op_occs_v1[i].grant_id,
                             vnf_lcm_op_occs_v2[i].grantId)
            self.assertEqual(vnf_lcm_op_occs_v1[i].operation,
                             vnf_lcm_op_occs_v2[i].operation)
            self.assertEqual(vnf_lcm_op_occs_v1[i].is_automatic_invocation,
                             vnf_lcm_op_occs_v2[i].isAutomaticInvocation)
            self.assertEqual(vnf_lcm_op_occs_v1[i].is_cancel_pending,
                             vnf_lcm_op_occs_v2[i].isCancelPending)
