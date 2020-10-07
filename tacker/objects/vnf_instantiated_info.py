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
from oslo_utils import timeutils

from tacker.common import exceptions
from tacker.common import utils
from tacker.db import api as db_api
from tacker.db.db_sqlalchemy import api
from tacker.db.db_sqlalchemy import models
from tacker.objects import base
from tacker.objects import fields


LOG = logging.getLogger(__name__)


@db_api.context_manager.writer
def _destroy_instantiated_vnf_info(context, uuid):
    now = timeutils.utcnow()
    updated_values = {'deleted': True,
                      'deleted_at': now
                      }
    api.model_query(context, models.VnfInstantiatedInfo). \
        filter_by(vnf_instance_id=uuid). \
        update(updated_values, synchronize_session=False)


@db_api.context_manager.writer
def _instantiate_vnf_info_update(context, vnf_instance_id, values):
    vnf_info = api.model_query(context, models.VnfInstantiatedInfo). \
        filter_by(vnf_instance_id=vnf_instance_id).first()

    needs_create = False
    if vnf_info and vnf_info['deleted']:
        raise exceptions.VnfInstantiatedInfoNotFound(
            vnf_instance_id=vnf_instance_id)
    elif not vnf_info:
        values['vnf_instance_id'] = vnf_instance_id
        vnf_info = models.VnfInstantiatedInfo(**values)
        needs_create = True

    if needs_create:
        vnf_info.save(session=context.session)
    else:
        vnf_info.update(values)
        vnf_info.save(session=context.session)

    return vnf_info


@base.TackerObjectRegistry.register
class InstantiatedVnfInfo(base.TackerObject, base.TackerObjectDictCompat,
                     base.TackerPersistentObject):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'flavour_id': fields.StringField(nullable=False),
        'vnf_instance_id': fields.UUIDField(nullable=False),
        'scale_status': fields.ListOfObjectsField(
            'ScaleInfo', nullable=True, default=[]),
        'ext_cp_info': fields.ListOfObjectsField(
            'VnfExtCpInfo', nullable=False),
        'ext_virtual_link_info': fields.ListOfObjectsField(
            'ExtVirtualLinkInfo', nullable=True, default=[]),
        'ext_managed_virtual_link_info': fields.ListOfObjectsField(
            'ExtManagedVirtualLinkInfo', nullable=True, default=[]),
        'vnfc_resource_info': fields.ListOfObjectsField(
            'VnfcResourceInfo', nullable=True, default=[]),
        'vnf_virtual_link_resource_info': fields.ListOfObjectsField(
            'VnfVirtualLinkResourceInfo', nullable=True, default=[]),
        'virtual_storage_resource_info': fields.ListOfObjectsField(
            'VirtualStorageResourceInfo', nullable=True, default=[]),
        'vnfc_info': fields.ListOfObjectsField(
            'VnfcInfo', nullable=True, default=[]),
        'vnf_state': fields.VnfOperationalStateTypeField(nullable=False,
            default=fields.VnfOperationalStateType.STOPPED),
        'instance_id': fields.StringField(nullable=True, default=None),
        'instantiation_level_id': fields.StringField(nullable=True,
            default=None),
        'additional_params': fields.DictOfStringsField(nullable=True,
                                                       default={})
    }

    ALL_ATTRIBUTES = {
        'instantiatedInfo': {
            'flavourId': ('id', 'string', 'VnfInstantiatedInfo'),
            'vnfInstanceId':
                ('vnf_instance_id', 'string', 'VnfInstantiatedInfo'),
            'vnfState': ('vnf_state', 'string', 'VnfInstantiatedInfo'),
            'instanceId': ('instance_id', 'string', 'VnfInstantiatedInfo'),
            'instantiationLevelId':
                ('instantiation_level_id', 'string', 'VnfInstantiatedInfo'),
            'extCpInfo/*': ('ext_cp_info', 'key_value_pair',
                            {"key_column": "key", "value_column": "value",
                             "model": "VnfInstantiatedInfo"}),
            'extVirtualLinkInfo/*': ('ext_virtual_link_info', 'key_value_pair',
                                {"key_column": "key", "value_column": "value",
                                "model": "VnfInstantiatedInfo"}),
            'extManagedVirtualLinkInfo/*': (
                'ext_managed_virtual_link_info', 'key_value_pair',
                {"key_column": "key", "value_column": "value",
                "model": "VnfInstantiatedInfo"}),
            'vnfcResourceInfo/*': (
                'vnfc_resource_info', 'key_value_pair',
                {"key_column": "key", "value_column": "value",
                "model": "VnfInstantiatedInfo"}),
            'vnfVirtualLinkResourceInfo/*': (
                'vnf_virtual_link_resource_info', 'key_value_pair',
                {"key_column": "key", "value_column": "value",
                "model": "VnfInstantiatedInfo"}),
            'virtualStorageResourceInfo/*': (
                'virtual_storage_resource_info', 'key_value_pair',
                {"key_column": "key", "value_column": "value",
                "model": "VnfInstantiatedInfo"}),
            'additionalParams/*': (
                'additional_params', 'key_value_pair',
                {"key_column": "key", "value_column": "value",
                "model": "VnfInstantiatedInfo"}),
            'vnfcInfo/*': (
                'vnfc_info', 'key_value_pair',
                {"key_column": "key", "value_column": "value",
                "model": "VnfInstantiatedInfo"}),
        }
    }

    FLATTEN_ATTRIBUTES = utils.flatten_dict(ALL_ATTRIBUTES.copy())

    @staticmethod
    def _from_db_object(context, inst_vnf_info, db_inst_vnf_info):

        special_fields = ['scale_status',
                          'ext_cp_info', 'ext_virtual_link_info',
                          'ext_managed_virtual_link_info',
                          'vnfc_resource_info',
                          'vnf_virtual_link_resource_info',
                          'virtual_storage_resource_info',
                          'vnfc_info']
        for key in inst_vnf_info.fields:
            if key in special_fields:
                continue

            setattr(inst_vnf_info, key, db_inst_vnf_info.get(key))

        scale_status = db_inst_vnf_info['scale_status']
        scale_status_list = [ScaleInfo.obj_from_primitive(scale, context)
                    for scale in scale_status]
        inst_vnf_info.scale_status = scale_status_list

        ext_cp_info = db_inst_vnf_info['ext_cp_info']
        ext_cp_info_list = [VnfExtCpInfo.obj_from_primitive(ext_cp, context)
                    for ext_cp in ext_cp_info]
        inst_vnf_info.ext_cp_info = ext_cp_info_list

        vnfc_resource_info = db_inst_vnf_info['vnfc_resource_info']
        vnfc_resource_info_list = [VnfcResourceInfo.obj_from_primitive(
            vnfc_resource, context) for vnfc_resource in vnfc_resource_info]
        inst_vnf_info.vnfc_resource_info = vnfc_resource_info_list

        storage_res_info = db_inst_vnf_info['virtual_storage_resource_info']
        storage_res_info_list = [VirtualStorageResourceInfo.
            obj_from_primitive(storage_resource, context)
            for storage_resource in storage_res_info]
        inst_vnf_info.virtual_storage_resource_info = storage_res_info_list

        ext_virtual_link_info = db_inst_vnf_info['ext_virtual_link_info']
        ext_vl_info_list = [ExtVirtualLinkInfo.obj_from_primitive(
            ext_vl_info, context) for ext_vl_info in ext_virtual_link_info]
        inst_vnf_info.ext_virtual_link_info = ext_vl_info_list

        ext_mng_vl_info = db_inst_vnf_info['ext_managed_virtual_link_info']
        ext_managed_vl_info_list = [ExtManagedVirtualLinkInfo.
            obj_from_primitive(ext_managed_vl_info, context) for
            ext_managed_vl_info in ext_mng_vl_info]
        inst_vnf_info.ext_managed_virtual_link_info = ext_managed_vl_info_list

        vnf_vl_resource_info = db_inst_vnf_info[
            'vnf_virtual_link_resource_info']
        vnf_vl_info_list = [VnfVirtualLinkResourceInfo.
            obj_from_primitive(vnf_vl_info, context) for vnf_vl_info in
            vnf_vl_resource_info]
        inst_vnf_info.vnf_virtual_link_resource_info = vnf_vl_info_list

        vnfc_info = db_inst_vnf_info[
            'vnfc_info']
        vnfc_info_list = [VnfcInfo.
            obj_from_primitive(vnfc, context) for vnfc in
            vnfc_info]
        inst_vnf_info.vnfc_info = vnfc_info_list

        inst_vnf_info._context = context
        inst_vnf_info.obj_reset_changes()
        return inst_vnf_info

    @base.remotable
    def save(self):
        updates = {}
        changes = self.obj_what_changed()

        for field in self.fields:
            if (self.obj_attr_is_set(field) and
                    isinstance(self.fields[field], fields.ListOfObjectsField)):
                field_list = getattr(self, field)
                updates[field] = [obj.obj_to_primitive() for obj in field_list]
            elif field in changes:
                updates[field] = self[field]

        vnf_info = _instantiate_vnf_info_update(self._context,
                                                self.vnf_instance_id,
                                                updates)
        self._from_db_object(self._context, self, vnf_info)

        self.obj_reset_changes()

    @classmethod
    def obj_from_primitive(cls, primitive, context):
        if 'tacker_object.name' in primitive:
            instantiate_vnf_info = super(
                InstantiatedVnfInfo, cls).obj_from_primitive(
                primitive, context)
        else:
            if 'scale_status' in primitive.keys():
                obj_data = [ScaleInfo.obj_from_primitive(
                    scale, context) for scale in primitive.get(
                    'scale_status', [])]
                primitive.update({'scale_status': obj_data})

            if 'ext_cp_info' in primitive.keys():
                obj_data = [VnfExtCpInfo.obj_from_primitive(
                    vnf_ext_cp, context) for vnf_ext_cp in primitive.get(
                    'ext_cp_info', [])]
                primitive.update({'ext_cp_info': obj_data})

            if 'ext_virtual_link_info' in primitive.keys():
                obj_data = [ExtVirtualLinkInfo.obj_from_primitive(
                    ext_virtual_link,
                    context) for ext_virtual_link in primitive.get(
                    'ext_virtual_link_info', [])]
                primitive.update({'ext_virtual_link_info': obj_data})

            if 'ext_managed_virtual_link_info' in primitive.keys():
                obj_data = [ExtManagedVirtualLinkInfo.obj_from_primitive(
                    ext_managed_v_link,
                    context) for ext_managed_v_link in primitive.get(
                    'ext_managed_virtual_link_info', [])]
                primitive.update({'ext_managed_virtual_link_info': obj_data})

            if 'vnfc_resource_info' in primitive.keys():
                obj_data = [VnfcResourceInfo.obj_from_primitive(
                    vnf_resource_info,
                    context) for vnf_resource_info in primitive.get(
                    'vnfc_resource_info', [])]
                primitive.update({'vnfc_resource_info': obj_data})

            if 'vnf_virtual_link_resource_info' in primitive.keys():
                obj_data = [VnfVirtualLinkResourceInfo.obj_from_primitive(
                    vnf_v_link_resource,
                    context) for vnf_v_link_resource in primitive.get(
                    'vnf_virtual_link_resource_info', [])]
                primitive.update({'vnf_virtual_link_resource_info': obj_data})

            if 'virtual_storage_resource_info' in primitive.keys():
                obj_data = [VirtualStorageResourceInfo.obj_from_primitive(
                    virtual_storage_info,
                    context) for virtual_storage_info in primitive.get(
                    'virtual_storage_resource_info', [])]
                primitive.update({'virtual_storage_resource_info': obj_data})

            if 'vnfc_info' in primitive.keys():
                obj_data = [VnfcInfo.obj_from_primitive(
                    vnfc_info, context) for vnfc_info in primitive.get(
                    'vnfc_info', [])]
                primitive.update({'vnfc_info': obj_data})

            instantiate_vnf_info = \
                InstantiatedVnfInfo._from_dict(primitive)

        return instantiate_vnf_info

    @classmethod
    def obj_from_db_obj(cls, context, db_obj):
        return cls._from_db_object(context, cls(), db_obj)

    @classmethod
    def _from_dict(cls, data_dict):
        flavour_id = data_dict.get('flavour_id')
        scale_status = data_dict.get('scale_status', [])
        ext_cp_info = data_dict.get('ext_cp_info', [])
        ext_virtual_link_info = data_dict.get('ext_virtual_link_info', [])
        ext_managed_virtual_link_info = data_dict.get(
            'ext_managed_virtual_link_info', [])
        vnfc_resource_info = data_dict.get('vnfc_resource_info', [])
        vnf_virtual_link_resource_info = data_dict.get(
            'vnf_virtual_link_resource_info', [])
        virtual_storage_resource_info = data_dict.get(
            'virtual_storage_resource_info', [])
        vnf_state = data_dict.get('vnf_state')
        instantiation_level_id = data_dict.get('instantiation_level_id')
        additional_params = data_dict.get('additional_params', {})
        vnfc_info = data_dict.get('vnfc_info', [])

        obj = cls(flavour_id=flavour_id,
               scale_status=scale_status,
               ext_cp_info=ext_cp_info,
               ext_virtual_link_info=ext_virtual_link_info,
               ext_managed_virtual_link_info=ext_managed_virtual_link_info,
               vnfc_resource_info=vnfc_resource_info,
               vnf_virtual_link_resource_info=vnf_virtual_link_resource_info,
               virtual_storage_resource_info=virtual_storage_resource_info,
               vnfc_info=vnfc_info,
               vnf_state=vnf_state,
               instantiation_level_id=instantiation_level_id,
               additional_params=additional_params)
        return obj

    def to_dict(self):
        data = {'flavour_id': self.flavour_id,
            'vnf_state': self.vnf_state}

        if self.scale_status:
            scale_status_list = []
            for scale_status in self.scale_status:
                scale_status_list.append(scale_status.to_dict())

            data.update({'scale_status': scale_status_list})

        ext_cp_info_list = []
        for ext_cp_info in self.ext_cp_info:
            ext_cp_info_list.append(ext_cp_info.to_dict())

        data.update({'ext_cp_info': ext_cp_info_list})

        if self.ext_virtual_link_info:
            exp_virt_link_info_list = []
            for exp_virt_link_info in self.ext_virtual_link_info:
                exp_virt_link_info_list.append(exp_virt_link_info.to_dict())
            data.update({'ext_virtual_link_info': exp_virt_link_info_list})

        if self.ext_managed_virtual_link_info:
            ext_managed_virt_info_list = []
            for exp_managed_virt_link_info in \
                    self.ext_managed_virtual_link_info:
                info = exp_managed_virt_link_info.to_dict()
                ext_managed_virt_info_list.append(info)
            data.update({'ext_managed_virtual_link_info':
                    ext_managed_virt_info_list})

        if self.vnfc_resource_info:
            vnfc_resource_info_list = []
            for vnfc_resource_info in self.vnfc_resource_info:
                vnfc_resource_info_list.append(vnfc_resource_info.to_dict())

            data.update({'vnfc_resource_info': vnfc_resource_info_list})

        if self.vnf_virtual_link_resource_info:
            virt_link_info = []
            for vnf_virtual_link_resource_info in \
                    self.vnf_virtual_link_resource_info:
                info = vnf_virtual_link_resource_info.to_dict()
                virt_link_info.append(info)

            data.update({'vnf_virtual_link_resource_info': virt_link_info})

        if self.virtual_storage_resource_info:
            virtual_storage_resource_info_list = []
            for virtual_storage_resource_info in \
                    self.virtual_storage_resource_info:
                info = virtual_storage_resource_info.to_dict()
                virtual_storage_resource_info_list.append(info)

            data.update({'virtual_storage_resource_info':
                    virtual_storage_resource_info_list})

        if self.vnfc_info:
            vnfc_info = []
            for vnfc in self.vnfc_info:
                info = vnfc.to_dict()
                vnfc_info.append(info)

            data.update({'vnfc_info': vnfc_info})

        data.update({'additional_params':
                self.additional_params})

        return data

    def reinitialize(self):
        # Reinitialize vnf to non instantiated state.
        self.scale_status = []
        self.ext_cp_info = []
        self.ext_virtual_link_info = []
        self.ext_managed_virtual_link_info = []
        self.vnfc_resource_info = []
        self.vnf_virtual_link_resource_info = []
        self.virtual_storage_resource_info = []
        self.instance_id = None
        self.vnf_state = fields.VnfOperationalStateType.STOPPED
        self.vnfc_info = []

    @base.remotable
    def destroy(self, context):
        if not self.obj_attr_is_set('vnf_instance_id'):
            raise exceptions.ObjectActionError(action='destroy',
                                               reason='no uuid')

        _destroy_instantiated_vnf_info(context, self.vnf_instance_id)


@base.TackerObjectRegistry.register
class ScaleInfo(base.TackerObject, base.TackerObjectDictCompat,
                base.TackerPersistentObject):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'aspect_id': fields.StringField(nullable=False),
        'scale_level': fields.IntegerField(nullable=False),
    }

    @classmethod
    def obj_from_primitive(cls, primitive, context):
        if 'tacker_object.name' in primitive:
            obj_scale_status = super(
                ScaleInfo, cls).obj_from_primitive(
                primitive, context)
        else:
            obj_scale_status = ScaleInfo._from_dict(primitive)

        return obj_scale_status

    @classmethod
    def _from_dict(cls, data_dict):
        aspect_id = data_dict.get('aspect_id')
        scale_level = data_dict.get('scale_level')

        obj = cls(aspect_id=aspect_id,
                  scale_level=scale_level)
        return obj

    def to_dict(self):

        return {'aspect_id': self.aspect_id,
                'scale_level': self.scale_level}


@base.TackerObjectRegistry.register
class VnfExtCpInfo(base.TackerObject, base.TackerObjectDictCompat,
                   base.TackerPersistentObject):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.StringField(nullable=False),
        'cpd_id': fields.StringField(nullable=False),
        'cp_protocol_info': fields.ListOfObjectsField(
            'CpProtocolInfo', nullable=False, default=[]),
        'ext_link_port_id': fields.StringField(nullable=True, default=None),
        'associated_vnfc_cp_id': fields.StringField(nullable=False)
    }

    @classmethod
    def obj_from_primitive(cls, primitive, context):
        if 'tacker_object.name' in primitive:
            obj_ext_cp_info = super(
                VnfExtCpInfo, cls).obj_from_primitive(
                primitive, context)
        else:
            if 'cp_protocol_info' in primitive.keys():
                obj_data = [CpProtocolInfo.obj_from_primitive(
                    ext_cp, context) for ext_cp in primitive.get(
                    'cp_protocol_info', [])]
                primitive.update({'cp_protocol_info': obj_data})

            obj_ext_cp_info = VnfExtCpInfo._from_dict(primitive)

        return obj_ext_cp_info

    @classmethod
    def _from_dict(cls, data_dict):
        id = data_dict.get('id')
        cpd_id = data_dict.get('cpd_id')
        cp_protocol_info = data_dict.get('cp_protocol_info', [])
        ext_link_port_id = data_dict.get('ext_link_port_id')
        associated_vnfc_cp_id = data_dict.get('associated_vnfc_cp_id')

        obj = cls(id=id, cpd_id=cpd_id,
                cp_protocol_info=cp_protocol_info,
                ext_link_port_id=ext_link_port_id,
                associated_vnfc_cp_id=associated_vnfc_cp_id)
        return obj

    def to_dict(self):
        data = {'id': self.id,
            'cpd_id': self.cpd_id,
            'ext_link_port_id': self.ext_link_port_id,
            'associated_vnfc_cp_id': self.associated_vnfc_cp_id}

        cp_protocol_info_list = []
        for cp_protocol_info in self.cp_protocol_info:
            cp_protocol_info_list.append(cp_protocol_info.to_dict())

        data.update({'cp_protocol_info': cp_protocol_info_list})

        return data


@base.TackerObjectRegistry.register
class CpProtocolInfo(base.TackerObject, base.TackerPersistentObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'layer_protocol': fields.StringField(nullable=False),
        'ip_over_ethernet': fields.ObjectField(
            'IpOverEthernetAddressInfo', nullable=True, default=None),
    }

    @classmethod
    def obj_from_primitive(cls, primitive, context):
        if 'tacker_object.name' in primitive:
            obj_cp_protocol = super(CpProtocolInfo, cls).obj_from_primitive(
                primitive, context)
        else:
            if 'ip_over_ethernet' in primitive.keys():
                obj_data = IpOverEthernetAddressInfo.obj_from_primitive(
                    primitive.get('ip_over_ethernet', {}), context)
                primitive.update({'ip_over_ethernet': obj_data})

            obj_cp_protocol = CpProtocolInfo._from_dict(primitive)

        return obj_cp_protocol

    @classmethod
    def _from_dict(cls, data_dict):
        layer_protocol = data_dict.get('layer_protocol')
        ip_over_ethernet = data_dict.get('ip_over_ethernet')

        obj = cls(layer_protocol=layer_protocol,
                  ip_over_ethernet=ip_over_ethernet)
        return obj

    def to_dict(self):
        data = {'layer_protocol': self.layer_protocol}

        if self.ip_over_ethernet:
            data.update({'ip_over_ethernet': self.ip_over_ethernet.to_dict()})

        return data


@base.TackerObjectRegistry.register
class IpOverEthernetAddressInfo(base.TackerObject,
                                base.TackerPersistentObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'mac_address': fields.StringField(nullable=True, default=None),
        'ip_addresses': fields.ListOfObjectsField('IpAddress', nullable=True,
                                                  default=[]),
    }

    @classmethod
    def obj_from_primitive(cls, primitive, context):
        if 'tacker_object.name' in primitive:
            ip_over_ethernet = super(
                IpOverEthernetAddressInfo, cls).obj_from_primitive(
                primitive, context)
        else:
            if 'ip_addresses' in primitive.keys():
                obj_data = [IpAddress._from_dict(
                    ip_address) for ip_address in primitive.get(
                        'ip_addresses', [])]
                primitive.update({'ip_addresses': obj_data})

            ip_over_ethernet = IpOverEthernetAddressInfo._from_dict(primitive)

        return ip_over_ethernet

    @classmethod
    def _from_dict(cls, data_dict):
        mac_address = data_dict.get('mac_address')
        ip_addresses = data_dict.get('ip_addresses', [])
        obj = cls(mac_address=mac_address, ip_addresses=ip_addresses)
        return obj

    def to_dict(self):
        data = {'mac_address': self.mac_address}

        if self.ip_addresses:
            ip_addresses_list = []
            for ip_addresses in self.ip_addresses:
                ip_addresses_list.append(ip_addresses.to_dict())

            data.update({'ip_addresses': ip_addresses_list})

        return data


@base.TackerObjectRegistry.register
class IpAddress(base.TackerObject, base.TackerPersistentObject):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'type': fields.IpAddressTypeField(nullable=False),
        'subnet_id': fields.StringField(nullable=True, default=None),
        'is_dynamic': fields.BooleanField(nullable=True, default=False),
        'addresses': fields.ListOfStringsField(nullable=True, default=[]),
    }

    @classmethod
    def _from_dict(cls, data_dict):
        type = data_dict.get('type', fields.IpAddressType.IPV4)
        subnet_id = data_dict.get('subnet_id')
        is_dynamic = data_dict.get('is_dynamic', False)
        addresses = data_dict.get('addresses', [])

        obj = cls(type=type, subnet_id=subnet_id, is_dynamic=is_dynamic,
                  addresses=addresses)

        return obj

    def to_dict(self):
        return {'type': self.type,
            'subnet_id': self.subnet_id,
            'is_dynamic': self.is_dynamic,
            'addresses': self.addresses}


@base.TackerObjectRegistry.register
class ExtVirtualLinkInfo(base.TackerObject, base.TackerPersistentObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.StringField(nullable=False),
        'resource_handle': fields.ObjectField(
            'ResourceHandle', nullable=False),
        'ext_link_ports': fields.ListOfObjectsField(
            'ExtLinkPortInfo', nullable=True, default=[]),
    }

    @classmethod
    def obj_from_primitive(cls, primitive, context):
        if 'tacker_object.name' in primitive:
            obj_ext_virt_link = super(
                ExtVirtualLinkInfo, cls).obj_from_primitive(
                primitive, context)
        else:
            if 'resource_handle' in primitive.keys():
                obj_data = ResourceHandle._from_dict(
                    primitive.get('resource_handle'))
                primitive.update({'resource_handle': obj_data})

            if 'ext_link_ports' in primitive.keys():
                obj_data = [ExtLinkPortInfo.obj_from_primitive(
                    ext_link_port_info, context)
                    for ext_link_port_info in primitive.get(
                        'ext_link_ports', [])]
                primitive.update({'ext_link_ports': obj_data})

            obj_ext_virt_link = ExtVirtualLinkInfo._from_dict(primitive)

        return obj_ext_virt_link

    @classmethod
    def _from_dict(cls, data_dict):
        id = data_dict.get('id', '')
        resource_handle = data_dict.get('resource_handle')
        ext_link_ports = data_dict.get('ext_link_ports', [])

        obj = cls(id=id, resource_handle=resource_handle,
                  ext_link_ports=ext_link_ports)
        return obj

    def to_dict(self):
        data = {'id': self.id,
            'resource_handle': self.resource_handle.to_dict()}

        if self.ext_link_ports:
            ext_link_ports = []
            for ext_link_port in self.ext_link_ports:
                ext_link_ports.append(ext_link_port.to_dict())

            data.update({'ext_link_ports': ext_link_ports})

        return data


@base.TackerObjectRegistry.register
class ExtLinkPortInfo(base.TackerObject, base.TackerPersistentObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.UUIDField(nullable=False),
        'resource_handle': fields.ObjectField(
            'ResourceHandle', nullable=False),
        'cp_instance_id': fields.StringField(nullable=True, default=None)
    }

    @classmethod
    def obj_from_primitive(cls, primitive, context):
        if 'tacker_object.name' in primitive:
            obj_link_port_info = super(
                ExtLinkPortInfo, cls).obj_from_primitive(primitive, context)
        else:
            if 'resource_handle' in primitive.keys():
                obj_data = ResourceHandle._from_dict(
                    primitive.get('resource_handle'))
                primitive.update({'resource_handle': obj_data})

            obj_link_port_info = ExtLinkPortInfo._from_dict(primitive)

        return obj_link_port_info

    @classmethod
    def _from_dict(cls, data_dict):
        id = data_dict.get('id')
        resource_handle = data_dict.get('resource_handle')
        cp_instance_id = data_dict.get('cp_instance_id')
        obj = cls(id=id, resource_handle=resource_handle,
                  cp_instance_id=cp_instance_id)
        return obj

    def to_dict(self):
        return {'id': self.id,
            'resource_handle': self.resource_handle.to_dict(),
            'cp_instance_id': self.cp_instance_id}


@base.TackerObjectRegistry.register
class ExtManagedVirtualLinkInfo(base.TackerObject,
                                base.TackerPersistentObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.StringField(nullable=False),
        'vnf_virtual_link_desc_id': fields.StringField(nullable=False),
        'network_resource': fields.ObjectField(
            'ResourceHandle', nullable=False),
        'vnf_link_ports': fields.ListOfObjectsField(
            'VnfLinkPortInfo', nullable=True, default=[]),
    }

    @classmethod
    def obj_from_primitive(cls, primitive, context):
        if 'tacker_object.name' in primitive:
            obj_ext_managed_virt_link = super(
                ExtManagedVirtualLinkInfo, cls).obj_from_primitive(
                primitive, context)
        else:
            if 'network_resource' in primitive.keys():
                obj_data = ResourceHandle._from_dict(
                    primitive.get('network_resource'))
                primitive.update({'network_resource': obj_data})

            if 'vnf_link_ports' in primitive.keys():
                obj_data = [VnfLinkPortInfo.obj_from_primitive(
                    vnf_link_port, context)
                    for vnf_link_port in primitive.get(
                        'vnf_link_ports', [])]
                primitive.update({'vnf_link_ports': obj_data})

            obj_ext_managed_virt_link = ExtManagedVirtualLinkInfo._from_dict(
                primitive)

        return obj_ext_managed_virt_link

    @classmethod
    def _from_dict(cls, data_dict):
        id = data_dict.get('id')
        vnf_virtual_link_desc_id = data_dict.get('vnf_virtual_link_desc_id')
        network_resource = data_dict.get('network_resource')
        vnf_link_ports = data_dict.get('vnf_link_ports', [])

        obj = cls(id=id, vnf_virtual_link_desc_id=vnf_virtual_link_desc_id,
                  network_resource=network_resource,
                  vnf_link_ports=vnf_link_ports)
        return obj

    def to_dict(self):
        data = {'id': self.id,
            'vnf_virtual_link_desc_id': self.vnf_virtual_link_desc_id,
            'network_resource': self.network_resource.to_dict()}

        if self.vnf_link_ports:
            vnf_link_ports = []
            for vnf_link_port in self.vnf_link_ports:
                vnf_link_ports.append(vnf_link_port.to_dict())

            data.update({'vnf_link_ports': vnf_link_ports})

        return data


@base.TackerObjectRegistry.register
class VnfLinkPortInfo(base.TackerObject, base.TackerPersistentObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.StringField(nullable=False),
        'resource_handle': fields.ObjectField(
            'ResourceHandle', nullable=False),
        'cp_instance_id': fields.StringField(nullable=True, default=None)
    }

    @classmethod
    def obj_from_primitive(cls, primitive, context):
        if 'tacker_object.name' in primitive:
            vnf_port_link_info = super(
                VnfLinkPortInfo, cls).obj_from_primitive(primitive, context)
        else:
            if 'resource_handle' in primitive.keys():
                obj_data = ResourceHandle._from_dict(
                    primitive.get('resource_handle'))
                primitive.update({'resource_handle': obj_data})

            vnf_port_link_info = VnfLinkPortInfo._from_dict(primitive)

        return vnf_port_link_info

    @classmethod
    def _from_dict(cls, data_dict):
        id = data_dict.get('id')
        resource_handle = data_dict.get('resource_handle')
        cp_instance_id = data_dict.get('cp_instance_id')

        obj = cls(id=id, resource_handle=resource_handle,
                  cp_instance_id=cp_instance_id)
        return obj

    def to_dict(self):
        return {'id': self.id,
            'resource_handle': self.resource_handle.to_dict(),
            'cp_instance_id': self.cp_instance_id}


@base.TackerObjectRegistry.register
class VnfcResourceInfo(base.TackerObject, base.TackerPersistentObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.StringField(nullable=False),
        'vdu_id': fields.StringField(nullable=False),
        'compute_resource': fields.ObjectField(
            'ResourceHandle', nullable=False),
        'storage_resource_ids': fields.ListOfStringsField(nullable=True,
                                                          default=[]),
        'vnfc_cp_info': fields.ListOfObjectsField(
            'VnfcCpInfo', nullable=True, default=[]),
        'metadata': fields.DictOfStringsField(nullable=True, default={})

    }

    @classmethod
    def obj_from_primitive(cls, primitive, context):
        if 'tacker_object.name' in primitive:
            vnfc_resource_info = super(
                VnfcResourceInfo, cls).obj_from_primitive(primitive, context)
        else:
            if 'compute_resource' in primitive.keys():
                obj_data = ResourceHandle._from_dict(
                    primitive.get('compute_resource'))
                primitive.update({'compute_resource': obj_data})

            if 'vnfc_cp_info' in primitive.keys():
                obj_data = [VnfcCpInfo.obj_from_primitive(
                    vnfc_cp_info, context)
                    for vnfc_cp_info in primitive.get(
                        'vnfc_cp_info', [])]
                primitive.update({'vnfc_cp_info': obj_data})

            vnfc_resource_info = VnfcResourceInfo._from_dict(primitive)

        return vnfc_resource_info

    @classmethod
    def _from_dict(cls, data_dict):
        id = data_dict.get('id')
        vdu_id = data_dict.get('vdu_id')
        compute_resource = data_dict.get('compute_resource')
        storage_resource_ids = data_dict.get('storage_resource_ids', [])
        vnfc_cp_info = data_dict.get('vnfc_cp_info', [])
        metadata = data_dict.get('metadata', {})

        obj = cls(id=id, vdu_id=vdu_id,
                  compute_resource=compute_resource,
                  storage_resource_ids=storage_resource_ids,
                  vnfc_cp_info=vnfc_cp_info, metadata=metadata)

        return obj

    def to_dict(self):
        data = {'id': self.id,
            'vdu_id': self.vdu_id,
            'compute_resource': self.compute_resource.to_dict(),
            'storage_resource_ids': self.storage_resource_ids}

        if self.vnfc_cp_info:
            vnfc_cp_info_list = []
            for vnfc_cp_info in self.vnfc_cp_info:
                vnfc_cp_info_list.append(vnfc_cp_info.to_dict())

            data.update({'vnfc_cp_info': vnfc_cp_info_list})

        return data


@base.TackerObjectRegistry.register
class VnfcCpInfo(base.TackerObject, base.TackerPersistentObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.StringField(nullable=False),
        'cpd_id': fields.StringField(nullable=False),
        'vnf_ext_cp_id': fields.StringField(nullable=True, default=None),
        'cp_protocol_info': fields.ListOfObjectsField(
            'CpProtocolInfo', nullable=True, default=[]),
        'vnf_link_port_id': fields.StringField(nullable=True, default=None)
    }

    @classmethod
    def obj_from_primitive(cls, primitive, context):
        if 'tacker_object.name' in primitive:
            obj_vnfc_cp_info = super(VnfcCpInfo, cls).obj_from_primitive(
                primitive, context)
        else:
            if 'cp_protocol_info' in primitive.keys():
                obj_data = [CpProtocolInfo.obj_from_primitive(
                    ext_cp, context) for ext_cp in primitive.get(
                    'cp_protocol_info', [])]
                primitive.update({'cp_protocol_info': obj_data})

            obj_vnfc_cp_info = VnfcCpInfo._from_dict(primitive)

        return obj_vnfc_cp_info

    @classmethod
    def _from_dict(cls, data_dict):
        id = data_dict.get('id')
        cpd_id = data_dict.get('cpd_id')
        vnf_ext_cp_id = data_dict.get('vnf_ext_cp_id')
        cp_protocol_info = data_dict.get('cp_protocol_info', [])
        vnf_link_port_id = data_dict.get('vnf_link_port_id')

        obj = cls(id=id, cpd_id=cpd_id,
                  vnf_ext_cp_id=vnf_ext_cp_id,
                  cp_protocol_info=cp_protocol_info,
                  vnf_link_port_id=vnf_link_port_id)

        return obj

    def to_dict(self):
        data = {'id': self.id,
             'cpd_id': self.cpd_id,
             'vnf_ext_cp_id': self.vnf_ext_cp_id,
             'vnf_link_port_id': self.vnf_link_port_id}

        if self.cp_protocol_info:
            cp_protocol_info_list = []
            for cp_protocol_info in self.cp_protocol_info:
                cp_protocol_info_list.append(cp_protocol_info.to_dict())

            data.update({'cp_protocol_info': cp_protocol_info_list})

        return data


@base.TackerObjectRegistry.register
class VnfVirtualLinkResourceInfo(base.TackerObject,
                                base.TackerPersistentObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.StringField(nullable=False),
        'vnf_virtual_link_desc_id': fields.StringField(nullable=False),
        'network_resource': fields.ObjectField(
            'ResourceHandle', nullable=False),
        'vnf_link_ports': fields.ListOfObjectsField(
            'VnfLinkPortInfo', nullable=True, default=[])
    }

    @classmethod
    def obj_from_primitive(cls, primitive, context):
        if 'tacker_object.name' in primitive:
            obj_vnf_virtual_link = super(
                VnfVirtualLinkResourceInfo, cls).obj_from_primitive(
                primitive, context)
        else:
            if 'network_resource' in primitive.keys():
                obj_data = ResourceHandle._from_dict(
                    primitive.get('network_resource'))
                primitive.update({'network_resource': obj_data})

            if 'vnf_link_ports' in primitive.keys():
                obj_data = [VnfLinkPortInfo.obj_from_primitive(
                    vnf_link_port, context)
                    for vnf_link_port in primitive.get(
                        'vnf_link_ports', [])]
                primitive.update({'vnf_link_ports': obj_data})

            obj_vnf_virtual_link = VnfVirtualLinkResourceInfo._from_dict(
                primitive)

        return obj_vnf_virtual_link

    @classmethod
    def _from_dict(cls, data_dict):
        id = data_dict.get('id')
        vnf_virtual_link_desc_id = data_dict.get(
            'vnf_virtual_link_desc_id')
        network_resource = data_dict.get('network_resource')
        vnf_link_ports = data_dict.get('vnf_link_ports', [])

        obj = cls(id=id, vnf_virtual_link_desc_id=vnf_virtual_link_desc_id,
                  network_resource=network_resource,
                  vnf_link_ports=vnf_link_ports)

        return obj

    def to_dict(self):
        data = {'id': self.id,
            'vnf_virtual_link_desc_id': self.vnf_virtual_link_desc_id,
            'network_resource': self.network_resource.to_dict()}

        if self.vnf_link_ports:
            vnf_link_ports = []
            for vnf_link_port in self.vnf_link_ports:
                vnf_link_ports.append(vnf_link_port.to_dict())

            data['vnf_link_ports'] = vnf_link_ports

        return data


@base.TackerObjectRegistry.register
class VirtualStorageResourceInfo(base.TackerObject,
                                base.TackerPersistentObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.StringField(nullable=False),
        'virtual_storage_desc_id': fields.StringField(nullable=False),
        'storage_resource': fields.ObjectField(
            'ResourceHandle', nullable=False)
    }

    @classmethod
    def obj_from_primitive(cls, primitive, context):
        if 'tacker_object.name' in primitive:
            obj_virtual_storage = super(
                VirtualStorageResourceInfo, cls).obj_from_primitive(
                primitive, context)
        else:
            if 'storage_resource' in primitive.keys():
                obj_data = ResourceHandle._from_dict(
                    primitive.get('storage_resource'))
                primitive.update({'storage_resource': obj_data})

            obj_virtual_storage = VirtualStorageResourceInfo._from_dict(
                primitive)

        return obj_virtual_storage

    @classmethod
    def _from_dict(cls, data_dict):
        id = data_dict.get('id')
        virtual_storage_desc_id = data_dict.get('virtual_storage_desc_id')
        storage_resource = data_dict.get('storage_resource')

        obj = cls(id=id, virtual_storage_desc_id=virtual_storage_desc_id,
                  storage_resource=storage_resource)

        return obj

    def to_dict(self):
        return {'id': self.id,
            'virtual_storage_desc_id': self.virtual_storage_desc_id,
            'storage_resource': self.storage_resource.to_dict()}


@base.TackerObjectRegistry.register
class VnfcInfo(base.TackerObject, base.TackerPersistentObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.StringField(nullable=False),
        'vdu_id': fields.StringField(nullable=False),
        'vnfc_state': fields.StringField(nullable=False)
    }

    @classmethod
    def obj_from_primitive(cls, primitive, context):
        if 'tacker_object.name' in primitive:
            obj_vnfc_info = super(
                VnfcInfo, cls).obj_from_primitive(
                primitive, context)
        else:
            obj_vnfc_info = VnfcInfo._from_dict(
                primitive)

        return obj_vnfc_info

    @classmethod
    def _from_dict(cls, data_dict):
        id = data_dict.get('id')
        vdu_id = data_dict.get('vdu_id')
        vnfc_state = data_dict.get('vnfc_state')

        obj = cls(id=id, vdu_id=vdu_id,
                  vnfc_state=vnfc_state)

        return obj

    def to_dict(self):
        return {'id': self.id,
            'vdu_id': self.vdu_id,
            'vnfc_state': self.vnfc_state}


@base.TackerObjectRegistry.register
class ResourceHandle(base.TackerObject,
                     base.TackerPersistentObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'vim_connection_id': fields.StringField(nullable=True,
                                                default=None),
        'resource_id': fields.StringField(nullable=False, default=""),
        'vim_level_resource_type': fields.StringField(nullable=True,
                                                      default=None)
    }

    @classmethod
    def obj_from_primitive(cls, primitive, context):
        if 'tacker_object.name' in primitive:
            resource_handle = super(
                ResourceHandle, cls).obj_from_primitive(
                primitive, context)
        else:
            resource_handle = ResourceHandle._from_dict(primitive)

        return resource_handle

    @classmethod
    def _from_dict(cls, data_dict):
        vim_connection_id = data_dict.get('vim_connection_id')
        resource_id = data_dict.get('resource_id', "")
        vim_level_resource_type = data_dict.get('vim_level_resource_type')

        obj = cls(vim_connection_id=vim_connection_id,
                  resource_id=resource_id,
                  vim_level_resource_type=vim_level_resource_type)

        return obj

    def to_dict(self):
        return {'vim_connection_id': self.vim_connection_id,
                'resource_id': self.resource_id,
                'vim_level_resource_type': self.vim_level_resource_type}
