# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright 2013, 2014 Intel Corporation.
# Copyright 2013, 2014 Isaku Yamahata <isaku.yamahata at intel com>
#                                     <isaku.yamahata at gmail com>
# All Rights Reserved.
#
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

import uuid

import sqlalchemy as sa
from sqlalchemy import orm
from sqlalchemy.orm import exc as orm_exc

from tacker.api.v1 import attributes
from tacker import context as t_context
from tacker.db import api as qdbapi
from tacker.db import db_base
from tacker.db import model_base
from tacker.db import models_v1
from tacker.extensions import vnfm
from tacker import manager
from tacker.openstack.common import log as logging
from tacker.openstack.common import uuidutils
from tacker.plugins.common import constants

LOG = logging.getLogger(__name__)
_ACTIVE_UPDATE = (constants.ACTIVE, constants.PENDING_UPDATE)
_ACTIVE_UPDATE_ERROR_DEAD = (
    constants.PENDING_CREATE, constants.ACTIVE, constants.PENDING_UPDATE,
    constants.ERROR, constants.DEAD)


###########################################################################
# db tables

class DeviceTemplate(model_base.BASE, models_v1.HasId, models_v1.HasTenant):
    """Represents template to create hosting device."""

    # Descriptive name
    name = sa.Column(sa.String(255))
    description = sa.Column(sa.String(255))

    # service type that this service vm provides.
    # At first phase, this includes only single service
    # In future, single service VM may accomodate multiple services.
    service_types = orm.relationship('ServiceType', backref='template')

    # driver to create hosting device. e.g. noop, nova, heat, etc...
    infra_driver = sa.Column(sa.String(255))

    # driver to communicate with service managment
    mgmt_driver = sa.Column(sa.String(255))

    # (key, value) pair to spin up
    attributes = orm.relationship('DeviceTemplateAttribute',
                                  backref='template')


class ServiceType(model_base.BASE, models_v1.HasId, models_v1.HasTenant):
    """Represents service type which hosting device provides.

    Since a device may provide many services, This is one-to-many
    relationship.
    """
    template_id = sa.Column(sa.String(36), sa.ForeignKey('devicetemplates.id'),
                            nullable=False)
    service_type = sa.Column(sa.String(255), nullable=False)


class DeviceTemplateAttribute(model_base.BASE, models_v1.HasId):
    """Represents attributes necessary for spinning up VM in (key, value) pair

    key value pair is adopted for being agnostic to actuall manager of VMs
    like nova, heat or others. e.g. image-id, flavor-id for Nova.
    The interpretation is up to actual driver of hosting device.
    """
    template_id = sa.Column(sa.String(36), sa.ForeignKey('devicetemplates.id'),
                            nullable=False)
    key = sa.Column(sa.String(255), nullable=False)
    value = sa.Column(sa.TEXT(65535), nullable=True)


class Device(model_base.BASE, models_v1.HasTenant):
    """Represents devices that hosts services.

    Here the term, 'VM', is intentionally avoided because it can be
    VM or other container.
    """
    id = sa.Column(sa.String(255),
                   primary_key=True,
                   default=uuidutils.generate_uuid)

    template_id = sa.Column(sa.String(36), sa.ForeignKey('devicetemplates.id'))
    template = orm.relationship('DeviceTemplate')

    name = sa.Column(sa.String(255), nullable=True)
    description = sa.Column(sa.String(255), nullable=True)

    # sufficient information to uniquely identify hosting device.
    # In case of service VM, it's UUID of nova VM.
    instance_id = sa.Column(sa.String(255), nullable=True)

    # For a management tool to talk to manage this hosting device.
    # opaque string.
    # e.g. (driver, mgmt_url) = (ssh, ip address), ...
    mgmt_url = sa.Column(sa.String(255), nullable=True)
    attributes = orm.relationship("DeviceAttribute", backref="device")

    status = sa.Column(sa.String(255), nullable=False)
    vim_id = sa.Column(sa.String(36), sa.ForeignKey('vims.id'), nullable=False)
    placement_attr = sa.Column(sa.PickleType, nullable=True)
    vim = orm.relationship('Vim')


class DeviceAttribute(model_base.BASE, models_v1.HasId):
    """Represents kwargs necessary for spinning up VM in (key, value) pair.

    key value pair is adopted for being agnostic to actuall manager of VMs
    like nova, heat or others. e.g. image-id, flavor-id for Nova.
    The interpretation is up to actual driver of hosting device.
    """
    device_id = sa.Column(sa.String(255), sa.ForeignKey('devices.id'),
                          nullable=False)
    key = sa.Column(sa.String(255), nullable=False)
    # json encoded value. example
    # "nic": [{"net-id": <net-uuid>}, {"port-id": <port-uuid>}]
    value = sa.Column(sa.TEXT(65535), nullable=True)


class VNFMPluginDb(vnfm.VNFMPluginBase, db_base.CommonDbMixin):

    @property
    def _core_plugin(self):
        return manager.TackerManager.get_plugin()

    def subnet_id_to_network_id(self, context, subnet_id):
        subnet = self._core_plugin.get_subnet(context, subnet_id)
        return subnet['network_id']

    def __init__(self):
        qdbapi.register_models()
        super(VNFMPluginDb, self).__init__()

    def _get_resource(self, context, model, id):
        try:
            return self._get_by_id(context, model, id)
        except orm_exc.NoResultFound:
            if issubclass(model, DeviceTemplate):
                raise vnfm.DeviceTemplateNotFound(device_tempalte_id=id)
            elif issubclass(model, ServiceType):
                raise vnfm.ServiceTypeNotFound(service_type_id=id)
            if issubclass(model, Device):
                raise vnfm.DeviceNotFound(device_id=id)
            else:
                raise

    def _make_attributes_dict(self, attributes_db):
        return dict((attr.key, attr.value) for attr in attributes_db)

    def _make_service_types_list(self, service_types):
        return [{'id': service_type.id,
                 'service_type': service_type.service_type}
                for service_type in service_types]

    def _make_template_dict(self, template, fields=None):
        res = {
            'attributes': self._make_attributes_dict(template['attributes']),
            'service_types': self._make_service_types_list(
                template.service_types)
        }
        key_list = ('id', 'tenant_id', 'name', 'description',
                    'infra_driver', 'mgmt_driver')
        res.update((key, template[key]) for key in key_list)
        return self._fields(res, fields)

    def _make_dev_attrs_dict(self, dev_attrs_db):
        return dict((arg.key, arg.value) for arg in dev_attrs_db)

    def _make_device_dict(self, device_db, fields=None):
        LOG.debug(_('device_db %s'), device_db)
        LOG.debug(_('device_db attributes %s'), device_db.attributes)
        res = {
            'device_template':
            self._make_template_dict(device_db.template),
            'attributes': self._make_dev_attrs_dict(device_db.attributes),
        }
        key_list = ('id', 'tenant_id', 'name', 'description', 'instance_id',
                    'vim_id', 'placement_attr', 'template_id', 'status',
                    'mgmt_url')
        res.update((key, device_db[key]) for key in key_list)
        return self._fields(res, fields)

    @staticmethod
    def _infra_driver_name(device_dict):
        return device_dict['device_template']['infra_driver']

    @staticmethod
    def _mgmt_driver_name(device_dict):
        return device_dict['device_template']['mgmt_driver']

    @staticmethod
    def _instance_id(device_dict):
        return device_dict['instance_id']

    def create_device_template(self, context, device_template):
        template = device_template['device_template']
        LOG.debug(_('template %s'), template)
        tenant_id = self._get_tenant_id_for_create(context, template)
        infra_driver = template.get('infra_driver')
        mgmt_driver = template.get('mgmt_driver')
        service_types = template.get('service_types')

        if (not attributes.is_attr_set(infra_driver)):
            LOG.debug(_('hosting device driver unspecified'))
            raise vnfm.InfraDriverNotSpecified()
        if (not attributes.is_attr_set(mgmt_driver)):
            LOG.debug(_('mgmt driver unspecified'))
            raise vnfm.MGMTDriverNotSpecified()
        if (not attributes.is_attr_set(service_types)):
            LOG.debug(_('service types unspecified'))
            raise vnfm.ServiceTypesNotSpecified()

        with context.session.begin(subtransactions=True):
            template_id = str(uuid.uuid4())
            template_db = DeviceTemplate(
                id=template_id,
                tenant_id=tenant_id,
                name=template.get('name'),
                description=template.get('description'),
                infra_driver=infra_driver,
                mgmt_driver=mgmt_driver)
            context.session.add(template_db)
            for (key, value) in template.get('attributes', {}).items():
                attribute_db = DeviceTemplateAttribute(
                    id=str(uuid.uuid4()),
                    template_id=template_id,
                    key=key,
                    value=value)
                context.session.add(attribute_db)
            for service_type in (item['service_type']
                                 for item in template['service_types']):
                service_type_db = ServiceType(
                    id=str(uuid.uuid4()),
                    tenant_id=tenant_id,
                    template_id=template_id,
                    service_type=service_type)
                context.session.add(service_type_db)

        LOG.debug(_('template_db %(template_db)s %(attributes)s '),
                  {'template_db': template_db,
                   'attributes': template_db.attributes})
        return self._make_template_dict(template_db)

    def update_device_template(self, context, device_template_id,
                               device_template):
        with context.session.begin(subtransactions=True):
            template_db = self._get_resource(context, DeviceTemplate,
                                             device_template_id)
            template_db.update(device_template['device_template'])
        return self._make_template_dict(template_db)

    def delete_device_template(self, context, device_template_id):
        with context.session.begin(subtransactions=True):
            # TODO(yamahata): race. prevent from newly inserting hosting device
            #                 that refers to this template
            devices_db = context.session.query(Device).filter_by(
                template_id=device_template_id).first()
            if devices_db is not None:
                raise vnfm.DeviceTemplateInUse(
                    device_template_id=device_template_id)

            context.session.query(ServiceType).filter_by(
                template_id=device_template_id).delete()
            context.session.query(DeviceTemplateAttribute).filter_by(
                template_id=device_template_id).delete()
            template_db = self._get_resource(context, DeviceTemplate,
                                             device_template_id)
            context.session.delete(template_db)

    def get_device_template(self, context, device_template_id, fields=None):
        template_db = self._get_resource(context, DeviceTemplate,
                                         device_template_id)
        return self._make_template_dict(template_db)

    def get_device_templates(self, context, filters, fields=None):
        return self._get_collection(context, DeviceTemplate,
                                    self._make_template_dict,
                                    filters=filters, fields=fields)

    def choose_device_template(self, context, service_type,
                               required_attributes=None):
        required_attributes = required_attributes or []
        LOG.debug(_('required_attributes %s'), required_attributes)
        with context.session.begin(subtransactions=True):
            query = (
                context.session.query(DeviceTemplate).
                filter(
                    sa.exists().
                    where(sa.and_(
                        DeviceTemplate.id == ServiceType.template_id,
                        ServiceType.service_type == service_type))))
            for key in required_attributes:
                query = query.filter(
                    sa.exists().
                    where(sa.and_(
                        DeviceTemplate.id ==
                        DeviceTemplateAttribute.template_id,
                        DeviceTemplateAttribute.key == key)))
            LOG.debug(_('statements %s'), query)
            template_db = query.first()
            if template_db:
                return self._make_template_dict(template_db)

    def _device_attribute_update_or_create(
            self, context, device_id, key, value):
        arg = (self._model_query(context, DeviceAttribute).
               filter(DeviceAttribute.device_id == device_id).
               filter(DeviceAttribute.key == key).first())
        if arg:
            arg.value = value
        else:
            arg = DeviceAttribute(
                id=str(uuid.uuid4()), device_id=device_id,
                key=key, value=value)
            context.session.add(arg)

    # called internally, not by REST API
    def _create_device_pre(self, context, device):
        LOG.debug(_('device %s'), device)
        tenant_id = self._get_tenant_id_for_create(context, device)
        template_id = device['template_id']
        name = device.get('name')
        device_id = device.get('id') or str(uuid.uuid4())
        attributes = device.get('attributes', {})
        vim_id = device.get('vim_id')
        placement_attr = device.get('placement_attr', {})
        with context.session.begin(subtransactions=True):
            template_db = self._get_resource(context, DeviceTemplate,
                                             template_id)
            device_db = Device(id=device_id,
                               tenant_id=tenant_id,
                               name=name,
                               description=template_db.description,
                               instance_id=None,
                               template_id=template_id,
                               vim_id=vim_id,
                               placement_attr=placement_attr,
                               status=constants.PENDING_CREATE)
            context.session.add(device_db)
            for key, value in attributes.items():
                    arg = DeviceAttribute(
                        id=str(uuid.uuid4()), device_id=device_id,
                        key=key, value=value)
                    context.session.add(arg)

        return self._make_device_dict(device_db)

    # called internally, not by REST API
    # intsance_id = None means error on creation
    def _create_device_post(self, context, device_id, instance_id,
                            mgmt_url, device_dict):
        LOG.debug(_('device_dict %s'), device_dict)
        with context.session.begin(subtransactions=True):
            query = (self._model_query(context, Device).
                     filter(Device.id == device_id).
                     filter(Device.status == constants.PENDING_CREATE).
                     one())
            query.update({'instance_id': instance_id, 'mgmt_url': mgmt_url})
            if instance_id is None or device_dict['status'] == constants.ERROR:
                query.update({'status': constants.ERROR})

            for (key, value) in device_dict['attributes'].items():
                # do not store decrypted vim auth in device attr table
                if 'vim_auth' not in key:
                    self._device_attribute_update_or_create(context, device_id,
                                                            key, value)

    def _create_device_status(self, context, device_id, new_status):
        with context.session.begin(subtransactions=True):
            (self._model_query(context, Device).
                filter(Device.id == device_id).
                filter(Device.status == constants.PENDING_CREATE).
                update({'status': new_status}))

    def _get_device_db(self, context, device_id, current_statuses, new_status):
        try:
            device_db = (
                self._model_query(context, Device).
                filter(Device.id == device_id).
                filter(Device.status.in_(current_statuses)).
                with_lockmode('update').one())
        except orm_exc.NoResultFound:
            raise vnfm.DeviceNotFound(device_id=device_id)
        if device_db.status == constants.PENDING_UPDATE:
            raise vnfm.DeviceInUse(device_id=device_id)
        device_db.update({'status': new_status})
        return device_db

    def _update_device_pre(self, context, device_id):
        with context.session.begin(subtransactions=True):
            device_db = self._get_device_db(
                context, device_id, _ACTIVE_UPDATE, constants.PENDING_UPDATE)
        return self._make_device_dict(device_db)

    def _update_device_post(self, context, device_id, new_status,
                            new_device_dict=None):
        with context.session.begin(subtransactions=True):
            (self._model_query(context, Device).
             filter(Device.id == device_id).
             filter(Device.status == constants.PENDING_UPDATE).
             update({'status': new_status}))

            dev_attrs = new_device_dict.get('attributes', {})
            (context.session.query(DeviceAttribute).
             filter(DeviceAttribute.device_id == device_id).
             filter(~DeviceAttribute.key.in_(dev_attrs.keys())).
             delete(synchronize_session='fetch'))

            for (key, value) in dev_attrs.items():
                if 'vim_auth' not in key:
                    self._device_attribute_update_or_create(context, device_id,
                                                        key, value)

    def _delete_device_pre(self, context, device_id):
        with context.session.begin(subtransactions=True):
            device_db = self._get_device_db(
                context, device_id, _ACTIVE_UPDATE_ERROR_DEAD,
                constants.PENDING_DELETE)

        return self._make_device_dict(device_db)

    def _delete_device_post(self, context, device_id, error):
        with context.session.begin(subtransactions=True):
            query = (
                self._model_query(context, Device).
                filter(Device.id == device_id).
                filter(Device.status == constants.PENDING_DELETE))
            if error:
                query.update({'status': constants.ERROR})
            else:
                (self._model_query(context, DeviceAttribute).
                 filter(DeviceAttribute.device_id == device_id).delete())
                query.delete()

    # reference implementation. needs to be overrided by subclass
    def create_device(self, context, device):
        device_dict = self._create_device_pre(context, device)
        # start actual creation of hosting device.
        # Waiting for completion of creation should be done backgroundly
        # by another thread if it takes a while.
        instance_id = str(uuid.uuid4())
        device_dict['instance_id'] = instance_id
        self._create_device_post(context, device_dict['id'], instance_id, None,
                                 device_dict)
        self._create_device_status(context, device_dict['id'],
                                   constants.ACTIVE)
        return device_dict

    # reference implementation. needs to be overrided by subclass
    def update_device(self, context, device_id, device):
        device_dict = self._update_device_pre(context, device_id)
        # start actual update of hosting device
        # waiting for completion of update should be done backgroundly
        # by another thread if it takes a while
        self._update_device_post(context, device_id, constants.ACTIVE)
        return device_dict

    # reference implementation. needs to be overrided by subclass
    def delete_device(self, context, device_id):
        self._delete_device_pre(context, device_id)
        # start actual deletion of hosting device.
        # Waiting for completion of deletion should be done backgroundly
        # by another thread if it takes a while.
        self._delete_device_post(context, device_id, False)

    def get_device(self, context, device_id, fields=None):
        device_db = self._get_resource(context, Device, device_id)
        return self._make_device_dict(device_db, fields)

    def get_devices(self, context, filters=None, fields=None):
        devices = self._get_collection(context, Device, self._make_device_dict,
                                       filters=filters, fields=fields)
        # Ugly hack to mask internaly used record
        return [device for device in devices
                if uuidutils.is_uuid_like(device['id'])]

    def _mark_device_status(self, device_id, exclude_status, new_status):
        context = t_context.get_admin_context()
        with context.session.begin(subtransactions=True):
            try:
                device_db = (
                    self._model_query(context, Device).
                    filter(Device.id == device_id).
                    filter(~Device.status.in_(exclude_status)).
                    with_lockmode('update').one())
            except orm_exc.NoResultFound:
                LOG.warning(_('no device found %s'), device_id)
                return False

            device_db.update({'status': new_status})
        return True

    def _mark_device_error(self, device_id):
        return self._mark_device_status(
            device_id, [constants.DEAD], constants.ERROR)

    def _mark_device_dead(self, device_id):
        exclude_status = [
            constants.DOWN,
            constants.PENDING_CREATE,
            constants.PENDING_UPDATE,
            constants.PENDING_DELETE,
            constants.INACTIVE,
            constants.ERROR]
        return self._mark_device_status(
            device_id, exclude_status, constants.DEAD)

    # used by failure policy
    def rename_device_id(self, context, device_id, new_device_id):
        # ugly hack...
        context = t_context.get_admin_context()
        with context.session.begin(subtransactions=True):
            device_db = self._get_resource(context, Device, device_id)
            new_device_db = Device(
                id=new_device_id,
                tenant_id=device_db.tenant_id,
                template_id=device_db.template_id,
                name=device_db.name,
                description=device_db.description,
                instance_id=device_db.instance_id,
                mgmt_url=device_db.mgmt_url,
                status=device_db.status,
                vim_id=device_db.vim_id,
                placement_attr=device_db.placement_attr)
            context.session.add(new_device_db)

            (self._model_query(context, DeviceAttribute).
             filter(DeviceAttribute.device_id == device_id).
             update({'device_id': new_device_id}))
            context.session.delete(device_db)

    def get_vnfs(self, context, filters=None, fields=None):
        return self.get_devices(context, filters, fields)

    def get_vnf(self, context, vnf_id, fields=None):
        return self.get_device(context, vnf_id, fields)

    def delete_vnfd(self, context, vnfd_id):
        self.delete_device_template(context, vnfd_id)

    def get_vnfd(self, context, vnfd_id, fields=None):
        return self.get_device_template(context, vnfd_id, fields)

    def get_vnfds(self, context, filters=None, fields=None):
        return self.get_device_templates(context, filters, fields)
