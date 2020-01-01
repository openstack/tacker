# Copyright (c) 2020 NTT DATA
#
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
import copy

from tacker import context
from tacker import objects
from tacker.tests.unit.db.base import SqlTestCase
from tacker.tests.unit.objects import fakes
from tacker.tests import uuidsentinel


class TestInstantiatedVnfInfo(SqlTestCase):

    def setUp(self):
        super(TestInstantiatedVnfInfo, self).setUp()
        self.context = context.get_admin_context()
        self.vnf_package = self._create_and_upload_vnf_package()
        self.vnf_instance = self._create_vnf_instance()
        self.resource_handle_info = self._create_resource_handle()
        self.ext_link_port_info = self._create_ext_link_port_info()
        self.ext_virtual_link_info = self._create_ext_virtual_link_info()
        self.vnf_link_ports_info = self._create_vnf_link_ports()
        self.ip_addresses_info = self._create_ip_addresses_info()
        self.ip_over_ethernet = self._create_ip_over_ethernet_info()
        self.cp_protocol_info = self._create_cp_protocol_info()
        self.vnf_external_cp_info = self._create_vnf_external_cp_info()
        self.vnfc_cp_info = self._create_vnfc_cp_info()
        self.vnfc_resource_info = self._create_vnfc_resource_info()
        self.virtual_link_resource_info = \
            self._create_virtual_link_resource_info()
        self.virtual_storage_resource_info = \
            self._create_virtual_storage_resource_info()
        self.ext_managed_virtual_link_info = \
            self._create_ext_managed_virtual_link_info()

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
        vnf_instance_data = fakes.get_vnf_instance_data(
            self.vnf_package_vnfd.vnfd_id)
        vnf_instance = objects.VnfInstance(context=self.context,
                                           **vnf_instance_data)
        vnf_instance.create()
        return vnf_instance

    def _create_vnf_external_cp_info(self):
        vnf_external_cp_data = copy.deepcopy(fakes.vnf_external_cp_info)
        vnf_external_cp_data.update(
            {'cp_protocol_info': [self.cp_protocol_info]})
        vnf_external_cp_info = objects.VnfExtCpInfo(
            context=self.context, **vnf_external_cp_data)
        return vnf_external_cp_info

    def _create_resource_handle(self):
        resource_handle_data = copy.deepcopy(fakes.resource_handle_info)
        resource_handle_info = objects.ResourceHandle(
            context=self.context, **resource_handle_data)
        return resource_handle_info

    def _create_ext_link_port_info(self):
        ext_link_port_info = copy.deepcopy(fakes.ext_link_port_info)
        ext_link_port_info.update(
            {'resource_handle': self.resource_handle_info})
        ext_link_port_info = objects.ExtLinkPortInfo(
            context=self.context, **ext_link_port_info)
        return ext_link_port_info

    def _create_ext_virtual_link_info(self):
        ext_virtual_link_info = copy.deepcopy(fakes.ext_virtual_link_info)
        ext_virtual_link_info.update(
            {'resource_handle_info': self.resource_handle_info,
             'ext_link_ports': self.ext_link_port_info})
        ext_virtual_link_info = objects.VnfExtCpInfo(
            context=self.context, **ext_virtual_link_info)
        return ext_virtual_link_info

    def _create_vnf_link_ports(self):
        vnf_link_ports_info = copy.deepcopy(fakes.vnf_link_ports)
        vnf_link_ports_info.update(
            {'resource_handle': self.resource_handle_info})
        vnf_link_ports_info = objects.VnfLinkPortInfo(
            context=self.context, **vnf_link_ports_info)
        return vnf_link_ports_info

    def _create_ext_managed_virtual_link_info(self):
        ext_managed_virtual_link_info = copy.deepcopy(
            fakes.ext_managed_virtual_link_info)
        ext_managed_virtual_link_info.update(
            {'network_resource': self.resource_handle_info,
             'vnf_link_ports': [self.vnf_link_ports_info]})
        ext_managed_virtual_link_info = objects.ExtManagedVirtualLinkInfo(
            context=self.context, **ext_managed_virtual_link_info)
        return ext_managed_virtual_link_info

    def _create_ip_addresses_info(self):
        ip_address_info = copy.deepcopy(fakes.ip_address_info)
        ip_address_info = objects.IpAddress(
            context=self.context, **ip_address_info)
        return ip_address_info

    def _create_ip_over_ethernet_info(self):
        ip_over_ethernet_onfo = copy.deepcopy(
            fakes.ip_over_ethernet_address_info)
        ip_over_ethernet_onfo.update(
            {'ip_addresses': [self.ip_addresses_info]})
        ip_over_ethernet_onfo = objects.IpOverEthernetAddressInfo(
            context=self.context, **ip_over_ethernet_onfo)
        return ip_over_ethernet_onfo

    def _create_cp_protocol_info(self):
        cp_protocol_info = copy.deepcopy(fakes.cp_protocol_info)
        cp_protocol_info.update(
            {'ip_over_ethernet': self.ip_over_ethernet})
        cp_protocol_info = objects.CpProtocolInfo(
            context=self.context, **cp_protocol_info)
        return cp_protocol_info

    def _create_vnfc_cp_info(self):
        vnfc_cp_info = copy.deepcopy(fakes.vnfc_cp_info)
        vnfc_cp_info.update(
            {'cp_protocol_info': [self.cp_protocol_info]})
        vnfc_cp_info = objects.VnfcCpInfo(
            context=self.context, **vnfc_cp_info)
        return vnfc_cp_info

    def _create_vnfc_resource_info(self):
        vnfc_resource_info = copy.deepcopy(fakes.vnfc_resource_info)
        vnfc_resource_info.update(
            {'compute_resource': self.resource_handle_info,
             'vnf_link_ports': [self.vnf_link_ports_info],
             'vnfc_cp_info': [self.vnfc_cp_info]})
        vnfc_resource_info = objects.VnfcResourceInfo(
            context=self.context, **vnfc_resource_info)
        return vnfc_resource_info

    def _create_virtual_link_resource_info(self):
        vnf_virtual_link_resource_info = copy.deepcopy(
            fakes.vnf_virtual_link_resource_info)
        vnf_virtual_link_resource_info.update(
            {'network_resource': self.resource_handle_info,
             'vnf_link_ports': [self.vnf_link_ports_info]})
        vnf_virtual_link_resource_info = objects.VnfVirtualLinkResourceInfo(
            context=self.context, **vnf_virtual_link_resource_info)
        return vnf_virtual_link_resource_info

    def _create_virtual_storage_resource_info(self):
        virtual_storage_resource_info = copy.deepcopy(
            fakes.virtual_storage_resource_info)
        virtual_storage_resource_info.update(
            {'storage_resource': self.resource_handle_info})
        virtual_storage_resource_info = objects.VirtualStorageResourceInfo(
            context=self.context, **virtual_storage_resource_info)
        return virtual_storage_resource_info

    def test_save(self):
        instantiated_vnf_info = copy.deepcopy(
            fakes.get_instantiated_vnf_info())
        instantiated_vnf_info.update(
            {'ext_cp_info': [self.vnf_external_cp_info],
             'vnf_instance_id': self.vnf_instance.id,
             'ext_link_port_info': self.ext_link_port_info,
             'ext_managed_virtual_link_info': [
                 self.ext_managed_virtual_link_info],
             'vnfc_resource_info': [self.vnfc_resource_info],
             'vnf_virtual_link_resource_info': [
                 self.virtual_link_resource_info],
             'virtual_storage_resource_info': [
                 self.virtual_storage_resource_info]})
        instantiated_vnf_info = objects.InstantiatedVnfInfo(
            context=self.context, **instantiated_vnf_info)
        instantiated_vnf_info.save()
        self.assertIsNotNone(instantiated_vnf_info.created_at)

    def test_resource_handle_obj_from_primitive_and_object_to_dict(self):
        resource_handle = copy.deepcopy(fakes.resource_handle_info)
        result = objects.ResourceHandle.obj_from_primitive(
            resource_handle, self.context)
        self.assertTrue(isinstance(result, objects.ResourceHandle))
        self.assertEqual('TEST', result.vim_level_resource_type)
        resource_handle_dict = result.to_dict()
        self.assertTrue(isinstance(resource_handle_dict, dict))
        self.assertEqual(
            'TEST', resource_handle_dict['vim_level_resource_type'])

    def test_virt_strg_res_info_obj_from_primitive_and_obj_to_dict(self):
        virtual_storage_resource_info = copy.deepcopy(
            fakes.virtual_storage_resource_info)
        result = objects.VirtualStorageResourceInfo.obj_from_primitive(
            virtual_storage_resource_info, self.context)
        self.assertTrue(isinstance(result,
            objects.VirtualStorageResourceInfo))
        virt_strg_res_info_dict = result.to_dict()
        self.assertTrue(isinstance(virt_strg_res_info_dict, dict))

    def test_vnfc_cp_info_obj_from_primitive_and_obj_to_dict(self):
        vnfc_cp_info = copy.deepcopy(fakes.vnfc_cp_info)
        result = objects.VnfcCpInfo.obj_from_primitive(
            vnfc_cp_info, self.context)
        self.assertTrue(isinstance(result, objects.VnfcCpInfo))
        vnfc_cp_info = result.to_dict()
        self.assertTrue(isinstance(vnfc_cp_info, dict))

    def test_vnfc_resource_info_obj_from_primitive_and_obj_to_dict(self):
        vnfc_resource_info = copy.deepcopy(fakes.vnfc_resource_info)
        result = objects.VnfcResourceInfo.obj_from_primitive(
            vnfc_resource_info, self.context)
        self.assertTrue(isinstance(result, objects.VnfcResourceInfo))
        self.assertEqual({'key': 'value'}, result.metadata)
        vnfc_resource_info = result.to_dict()
        self.assertTrue(isinstance(vnfc_resource_info, dict))

    def test_ext_mng_virt_link_obj_from_primitive_and_obj_to_dict(self):
        ext_managed_virtual_link_info = copy.deepcopy(
            fakes.ext_managed_virtual_link_info)
        result = objects.ExtManagedVirtualLinkInfo.obj_from_primitive(
            ext_managed_virtual_link_info, self.context)
        self.assertTrue(isinstance(result, objects.ExtManagedVirtualLinkInfo))
        ext_mng_virt_link = result.to_dict()
        self.assertTrue(isinstance(ext_mng_virt_link, dict))

    def test_ext_link_port_info_obj_from_primitive_and_obj_to_dict(self):
        ext_link_port_info_data = copy.deepcopy(fakes.ext_link_port_info)
        result = objects.ExtLinkPortInfo.obj_from_primitive(
            ext_link_port_info_data, self.context)
        self.assertTrue(isinstance(result, objects.ExtLinkPortInfo))
        ext_link_port_info = result.to_dict()
        self.assertTrue(isinstance(ext_link_port_info, dict))

    def test_ext_virt_link_info_obj_from_primitive_and_obj_to_dict(self):
        ext_virtual_link_info = copy.deepcopy(fakes.ext_virtual_link_info)
        result = objects.ExtVirtualLinkInfo.obj_from_primitive(
            ext_virtual_link_info, self.context)
        self.assertTrue(isinstance(result, objects.ExtVirtualLinkInfo))
        ext_virt_link_info = result.to_dict()
        self.assertTrue(isinstance(ext_virt_link_info, dict))

    def test_vnf_ext_cp_info_obj_from_primitive_and_obj_to_dict(self):
        vnf_ext_cp_info = copy.deepcopy(fakes.vnf_ext_cp_info)
        result = objects.VnfExtCpInfo.obj_from_primitive(
            vnf_ext_cp_info, self.context)
        self.assertTrue(isinstance(result, objects.VnfExtCpInfo))
        ext_virt_link_info = result.to_dict()
        self.assertTrue(isinstance(ext_virt_link_info, dict))

    def test_instantiated_info_obj_from_primitive_and_obj_to_dict(self):
        instantiated_vnf_info = copy.deepcopy(fakes.instantiated_vnf_info)
        result = objects.InstantiatedVnfInfo.obj_from_primitive(
            instantiated_vnf_info, self.context)
        self.assertTrue(isinstance(result, objects.InstantiatedVnfInfo))
        instantiated_vnf_info_dict = result.to_dict()
        self.assertTrue(isinstance(instantiated_vnf_info_dict, dict))
