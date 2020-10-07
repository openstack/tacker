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

from oslo_log import log as logging

from tacker import objects
from tacker.objects import base
from tacker.objects import fields

LOG = logging.getLogger(__name__)


def _get_vim_connection_info(vnf_instance):
    vim_connection_infos = []

    for vim_conn_info in vnf_instance.vim_connection_info:
        new_vim_conn_info = vim_conn_info.obj_clone()
        vim_connection_infos.append(new_vim_conn_info)

    return vim_connection_infos


def _get_ext_managed_virtual_links(vnf_instantiated_info):
    ext_managed_virtual_links = []

    for ext_mng_vl_info in \
            vnf_instantiated_info.ext_managed_virtual_link_info:
        network_resource = ext_mng_vl_info.network_resource

        ext_mng_vl_data = objects.ExtManagedVirtualLinkData(
            id=ext_mng_vl_info.id,
            vnf_virtual_link_desc_id=ext_mng_vl_info.vnf_virtual_link_desc_id,
            resource_id=network_resource.resource_id,
            vim_connection_id=network_resource.vim_connection_id)

        ext_managed_virtual_links.append(ext_mng_vl_data)

    return ext_managed_virtual_links


def _get_cp_instance_id(ext_virtual_link_info_id, vnf_instantiated_info):
    cp_instances = []

    for vnf_vl_res_info in \
            vnf_instantiated_info.vnf_virtual_link_resource_info:
        if ext_virtual_link_info_id == \
                vnf_vl_res_info.vnf_virtual_link_desc_id:
            for vnf_link_port in vnf_vl_res_info.vnf_link_ports:
                cp_instances.append(vnf_link_port.cp_instance_id)

    return cp_instances


def _get_cp_data_from_vnfc_resource_info(cp_instance_list,
        vnf_instantiated_info):
    vnfc_cp_infos = []

    for vnfc_resource_info in vnf_instantiated_info.vnfc_resource_info:
        for vnfc_cp_info in vnfc_resource_info.vnfc_cp_info:
            if vnfc_cp_info.id in cp_instance_list:
                vnfc_cp_infos.append(vnfc_cp_info)

    return vnfc_cp_infos


def _get_link_ports(vnfc_cp_info_list, vnf_instantiated_info):
    ext_link_ports = []

    for vnfc_cp_info in vnfc_cp_info_list:
        for ext_vl_info in vnf_instantiated_info.ext_virtual_link_info:
            for ext_vl_port in ext_vl_info.ext_link_ports:
                if ext_vl_port.id != vnfc_cp_info.vnf_ext_cp_id:
                    continue

                resource_handle = ext_vl_port.resource_handle.obj_clone()

                ext_link_port_data = objects.ExtLinkPortData(
                    id=ext_vl_port.id,
                    resource_handle=resource_handle)
                ext_link_ports.append(ext_link_port_data)
                break

    return ext_link_ports


def _get_cp_protocol_data_list(ext_cp_info):
    cp_protocol_data_list = []

    def _get_ip_addresses(ip_addresses):
        ip_addresses = []
        for ip_address in ip_addresses:
            # TODO(nitin-uikey): How to determine num_dynamic_addresses
            # back from InstantiatedVnfInfo->IpAddressReq.
            ip_address_data = IpAddressReq(
                type=ip_address.type,
                subnet_id=ip_address.subnet_id,
                fixed_addresses=ip_address.addresses)

            ip_addresses.append(ip_address_data)

        return ip_addresses

    for cp_protocol_info in ext_cp_info.cp_protocol_info:
        if cp_protocol_info.ip_over_ethernet:
            ip_addresses = _get_ip_addresses(cp_protocol_info.
                ip_over_ethernet.ip_addresses)

            ip_over_ethernet_data = objects.IpOverEthernetAddressData(
                mac_address=cp_protocol_info.ip_over_ethernet.mac_address,
                ip_addresses=ip_addresses)
        else:
            ip_over_ethernet_data = None

        cp_protocol_data = objects.CpProtocolData(
            layer_protocol=cp_protocol_info.layer_protocol,
            ip_over_ethernet=ip_over_ethernet_data)

        cp_protocol_data_list.append(cp_protocol_data)

    return cp_protocol_data_list


def _get_cp_ids(vnfc_cp_info_list, vnf_instantiated_info):

    ext_cps = []
    for vnfc_cp_info in vnfc_cp_info_list:
        for ext_cp_info in vnf_instantiated_info.ext_cp_info:
            if ext_cp_info.cpd_id != vnfc_cp_info.cpd_id:
                continue

            ext_cp_configs = []
            vnf_ext_cp_data = objects.VnfExtCpData()
            vnf_ext_cp_data.cpd_id = ext_cp_info.cpd_id

            cp_protocol_data_list = _get_cp_protocol_data_list(ext_cp_info)
            # TODO(nitin-uikey) set cp_instance_id
            # and prepare 1-N objects of VnfExtCpConfig
            vnf_ext_cp_config = objects.VnfExtCpConfig(
                link_port_id=vnfc_cp_info.vnf_ext_cp_id,
                cp_protocol_data=cp_protocol_data_list)

            ext_cp_configs.append(vnf_ext_cp_config)

            vnf_ext_cp_data = objects.VnfExtCpData(
                cpd_id=ext_cp_info.cpd_id,
                cp_config=ext_cp_configs)
            ext_cps.append(vnf_ext_cp_data)
            break

    return ext_cps


def _get_ext_virtual_link_data(vnf_instantiated_info):

    ext_virtual_links = []

    for ext_vl_info in \
            vnf_instantiated_info.ext_virtual_link_info:
        resource_handle = ext_vl_info.resource_handle
        ext_vl_data = objects.ExtVirtualLinkData(
            id=ext_vl_info.id,
            resource_id=resource_handle.resource_id,
            vim_connection_id=resource_handle.vim_connection_id)

        # call vnf virtual link resource info
        cp_instances = _get_cp_instance_id(ext_vl_info.id,
            vnf_instantiated_info)

        # get cp info from vnfcresources
        vnfc_cp_infos = _get_cp_data_from_vnfc_resource_info(cp_instances,
            vnf_instantiated_info)

        ext_vl_data.ext_link_ports = _get_link_ports(vnfc_cp_infos,
            vnf_instantiated_info)

        # assign the data to extcp info and link port
        ext_vl_data.ext_cps = _get_cp_ids(vnfc_cp_infos,
            vnf_instantiated_info)

        ext_virtual_links.append(ext_vl_data)

    return ext_virtual_links


@base.TackerObjectRegistry.register
class InstantiateVnfRequest(base.TackerObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'flavour_id': fields.StringField(nullable=False),
        'instantiation_level_id': fields.StringField(nullable=True,
                                                     default=None),
        'ext_managed_virtual_links': fields.ListOfObjectsField(
            'ExtManagedVirtualLinkData', nullable=True, default=[]),
        'vim_connection_info': fields.ListOfObjectsField(
            'VimConnectionInfo', nullable=True, default=[]),
        'ext_virtual_links': fields.ListOfObjectsField(
            'ExtVirtualLinkData', nullable=True, default=[]),
        'additional_params': fields.DictOfNullableField(nullable=True,
            default={})
    }

    @classmethod
    def obj_from_primitive(cls, primitive, context):
        if 'tacker_object.name' in primitive:
            obj_instantiate_vnf_req = super(
                InstantiateVnfRequest, cls).obj_from_primitive(
                primitive, context)
        else:
            if 'ext_managed_virtual_links' in primitive.keys():
                obj_data = [ExtManagedVirtualLinkData._from_dict(
                    ext_manage) for ext_manage in primitive.get(
                    'ext_managed_virtual_links', [])]
                primitive.update({'ext_managed_virtual_links': obj_data})

            if 'vim_connection_info' in primitive.keys():
                obj_data = [objects.VimConnectionInfo._from_dict(
                    vim_conn) for vim_conn in primitive.get(
                    'vim_connection_info', [])]
                primitive.update({'vim_connection_info': obj_data})

            if 'ext_virtual_links' in primitive.keys():
                obj_data = [ExtVirtualLinkData.obj_from_primitive(
                    ext_vir_link, context) for ext_vir_link in primitive.get(
                    'ext_virtual_links', [])]
                primitive.update({'ext_virtual_links': obj_data})
            obj_instantiate_vnf_req = InstantiateVnfRequest._from_dict(
                primitive)

        return obj_instantiate_vnf_req

    @classmethod
    def _from_dict(cls, data_dict):
        flavour_id = data_dict.get('flavour_id')
        instantiation_level_id = data_dict.get('instantiation_level_id')
        ext_managed_virtual_links = data_dict.get('ext_managed_virtual_links',
                                                  [])
        vim_connection_info = data_dict.get('vim_connection_info', [])
        ext_virtual_links = data_dict.get('ext_virtual_links', [])
        additional_params = data_dict.get('additional_params', {})

        return cls(flavour_id=flavour_id,
        instantiation_level_id=instantiation_level_id,
        ext_managed_virtual_links=ext_managed_virtual_links,
        vim_connection_info=vim_connection_info,
        ext_virtual_links=ext_virtual_links,
        additional_params=additional_params)

    @classmethod
    def from_vnf_instance(cls, vnf_instance):

        vnf_instantiated_info = vnf_instance.instantiated_vnf_info

        # Vim connection info
        vim_connection_info = _get_vim_connection_info(vnf_instance)

        # Flavour id
        flavour_id = vnf_instantiated_info.flavour_id

        # Instantiation level
        instantiation_level_id = vnf_instantiated_info.instantiation_level_id

        # Externally managed virtual links
        ext_managed_virtual_links = _get_ext_managed_virtual_links(
            vnf_instantiated_info)

        # External virtual links
        ext_virtual_links = _get_ext_virtual_link_data(vnf_instantiated_info)

        additional_params = vnf_instantiated_info.additional_params

        instantiate_vnf_request = cls(flavour_id=flavour_id,
            instantiation_level_id=instantiation_level_id,
            ext_managed_virtual_links=ext_managed_virtual_links,
            vim_connection_info=vim_connection_info,
            ext_virtual_links=ext_virtual_links,
            additional_params=additional_params)

        return instantiate_vnf_request


@base.TackerObjectRegistry.register
class ExtManagedVirtualLinkData(base.TackerObject):
    # Version 1.0: Initial version
    # Version 1.1: Added field for vim_connection_id
    VERSION = '1.1'

    fields = {
        'id': fields.StringField(nullable=False),
        'vnf_virtual_link_desc_id': fields.StringField(nullable=False),
        'resource_id': fields.StringField(nullable=False),
        'vim_connection_id': fields.StringField(nullable=True)
    }

    @classmethod
    def _from_dict(cls, data_dict):
        id = data_dict.get('id')
        vnf_virtual_link_desc_id = data_dict.get(
            'vnf_virtual_link_desc_id')
        resource_id = data_dict.get('resource_id')
        vim_connection_id = data_dict.get('vim_connection_id')
        obj = cls(id=id, vnf_virtual_link_desc_id=vnf_virtual_link_desc_id,
                  resource_id=resource_id, vim_connection_id=vim_connection_id)
        return obj


@base.TackerObjectRegistry.register
class ExtVirtualLinkData(base.TackerObject):
    # Version 1.0: Initial version
    # Version 1.1: Added field for vim_connection_id
    VERSION = '1.1'

    fields = {
        'id': fields.StringField(nullable=False),
        'resource_id': fields.StringField(nullable=False),
        'vim_connection_id': fields.StringField(nullable=True),
        'ext_cps': fields.ListOfObjectsField(
            'VnfExtCpData', nullable=True, default=[]),
        'ext_link_ports': fields.ListOfObjectsField(
            'ExtLinkPortData', nullable=True, default=[]),
    }

    @classmethod
    def obj_from_primitive(cls, primitive, context):
        if 'tacker_object.name' in primitive:
            obj_ext_virt_link = super(
                ExtVirtualLinkData, cls).obj_from_primitive(
                primitive, context)
        else:
            if 'ext_cps' in primitive.keys():
                obj_data = [VnfExtCpData.obj_from_primitive(
                    ext_cp, context) for ext_cp in primitive.get(
                    'ext_cps', [])]
                primitive.update({'ext_cps': obj_data})

            if 'ext_link_ports' in primitive.keys():
                obj_data = [ExtLinkPortData.obj_from_primitive(
                    ext_link_port_data, context)
                    for ext_link_port_data in primitive.get(
                        'ext_link_ports', [])]
                primitive.update({'ext_link_ports': obj_data})

            obj_ext_virt_link = ExtVirtualLinkData._from_dict(primitive)

        return obj_ext_virt_link

    @classmethod
    def _from_dict(cls, data_dict):
        id = data_dict.get('id')
        resource_id = data_dict.get('resource_id')
        vim_connection_id = data_dict.get('vim_connection_id')
        ext_cps = data_dict.get('ext_cps', [])
        ext_link_ports = data_dict.get('ext_link_ports', [])

        obj = cls(id=id, resource_id=resource_id, ext_cps=ext_cps,
                  ext_link_ports=ext_link_ports,
                  vim_connection_id=vim_connection_id)
        return obj


@base.TackerObjectRegistry.register
class VnfExtCpData(base.TackerObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'cpd_id': fields.StringField(nullable=False),
        'cp_config': fields.ListOfObjectsField(
            'VnfExtCpConfig', nullable=True, default=[]),
    }

    @classmethod
    def obj_from_primitive(cls, primitive, context):
        if 'tacker_object.name' in primitive:
            obj_vnf_ext_cp_data = super(VnfExtCpData, cls).obj_from_primitive(
                primitive, context)
        else:
            if 'cp_config' in primitive.keys():
                obj_data = [VnfExtCpConfig.obj_from_primitive(
                    vnf_ext_cp_conf, context)
                    for vnf_ext_cp_conf in primitive.get('cp_config', [])]
                primitive.update({'cp_config': obj_data})

            obj_vnf_ext_cp_data = VnfExtCpData._from_dict(primitive)

        return obj_vnf_ext_cp_data

    @classmethod
    def _from_dict(cls, data_dict):
        cpd_id = data_dict.get('cpd_id')
        cp_config = data_dict.get('cp_config', [])

        obj = cls(cpd_id=cpd_id, cp_config=cp_config)
        return obj


@base.TackerObjectRegistry.register
class VnfExtCpConfig(base.TackerObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'cp_instance_id': fields.StringField(nullable=True, default=None),
        'link_port_id': fields.StringField(nullable=True, default=None),
        'cp_protocol_data': fields.ListOfObjectsField(
            'CpProtocolData', nullable=True, default=[]),
    }

    @classmethod
    def obj_from_primitive(cls, primitive, context):
        if 'tacker_object.name' in primitive:
            obj_ext_cp_config = super(VnfExtCpConfig, cls).obj_from_primitive(
                primitive, context)
        else:
            if 'cp_protocol_data' in primitive.keys():
                obj_data = [CpProtocolData.obj_from_primitive(
                    cp_protocol, context) for cp_protocol in primitive.get(
                    'cp_protocol_data', [])]
                primitive.update({'cp_protocol_data': obj_data})

            obj_ext_cp_config = VnfExtCpConfig._from_dict(primitive)

        return obj_ext_cp_config

    @classmethod
    def _from_dict(cls, data_dict):
        cp_instance_id = data_dict.get('cp_instance_id')
        link_port_id = data_dict.get('link_port_id')
        cp_protocol_data = data_dict.get('cp_protocol_data', [])

        obj = cls(cp_instance_id=cp_instance_id,
                  link_port_id=link_port_id, cp_protocol_data=cp_protocol_data)
        return obj


@base.TackerObjectRegistry.register
class CpProtocolData(base.TackerObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'layer_protocol': fields.StringField(nullable=False),
        'ip_over_ethernet': fields.ObjectField(
            'IpOverEthernetAddressData', nullable=True, default=None),
    }

    @classmethod
    def obj_from_primitive(cls, primitive, context):
        if 'tacker_object.name' in primitive:
            obj_cp_protocal = super(CpProtocolData, cls).obj_from_primitive(
                primitive, context)
        else:
            if 'ip_over_ethernet' in primitive.keys():
                obj_data = IpOverEthernetAddressData.obj_from_primitive(
                    primitive.get('ip_over_ethernet', {}), context)
                primitive.update({'ip_over_ethernet': obj_data})
            obj_cp_protocal = CpProtocolData._from_dict(primitive)

        return obj_cp_protocal

    @classmethod
    def _from_dict(cls, data_dict):
        layer_protocol = data_dict.get('layer_protocol')
        ip_over_ethernet = data_dict.get('ip_over_ethernet')

        obj = cls(layer_protocol=layer_protocol,
                  ip_over_ethernet=ip_over_ethernet)
        return obj


@base.TackerObjectRegistry.register
class IpOverEthernetAddressData(base.TackerObject):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'mac_address': fields.StringField(
            nullable=True,
            default=None),
        'ip_addresses': fields.ListOfObjectsField(
            'IpAddressReq',
            nullable=True,
            default=[]),
    }

    @classmethod
    def obj_from_primitive(cls, primitive, context):
        if 'tacker_object.name' in primitive:
            ip_over_ethernet = super(
                IpOverEthernetAddressData, cls).obj_from_primitive(
                primitive, context)
        else:
            if 'ip_addresses' in primitive.keys():
                obj_data = [IpAddressReq._from_dict(
                    ip_address) for ip_address in primitive.get(
                        'ip_addresses', [])]
                primitive.update({'ip_addresses': obj_data})

            ip_over_ethernet = IpOverEthernetAddressData._from_dict(primitive)

        return ip_over_ethernet

    @classmethod
    def _from_dict(cls, data_dict):
        mac_address = data_dict.get('mac_address')
        ip_addresses = data_dict.get('ip_addresses', [])
        obj = cls(mac_address=mac_address, ip_addresses=ip_addresses)
        return obj


@base.TackerObjectRegistry.register
class IpAddressReq(base.TackerObject):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'type': fields.IpAddressTypeField(nullable=False),
        'subnet_id': fields.StringField(nullable=True, default=None),
        'fixed_addresses': fields.ListOfStringsField(nullable=True,
            default=[])
    }

    @classmethod
    def _from_dict(cls, data_dict):
        type = data_dict.get('type')
        subnet_id = data_dict.get('subnet_id')
        fixed_addresses = data_dict.get('fixed_addresses', [])

        obj = cls(type=type, subnet_id=subnet_id,
                fixed_addresses=fixed_addresses)

        return obj


@base.TackerObjectRegistry.register
class ExtLinkPortData(base.TackerObject):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.UUIDField(nullable=False),
        'resource_handle': fields.ObjectField(
            'ResourceHandle', nullable=False),
    }

    @classmethod
    def obj_from_primitive(cls, primitive, context):
        if 'tacker_object.name' in primitive:
            obj_link_port_data = super(
                ExtLinkPortData, cls).obj_from_primitive(primitive, context)
        else:
            if 'resource_handle' in primitive.keys():
                obj_data = objects.ResourceHandle._from_dict(primitive.get(
                    'resource_handle', []))
                primitive.update({'resource_handle': obj_data})

            obj_link_port_data = ExtLinkPortData._from_dict(primitive)

        return obj_link_port_data

    @classmethod
    def _from_dict(cls, data_dict):
        id = data_dict.get('id')
        resource_handle = data_dict.get('resource_handle')

        obj = cls(id=id, resource_handle=resource_handle)
        return obj
