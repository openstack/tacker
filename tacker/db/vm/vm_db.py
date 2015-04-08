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
#
# @author: Isaku Yamahata, Intel Corporation.

import uuid

import sqlalchemy as sa
from sqlalchemy import orm
from sqlalchemy.orm import exc as orm_exc

from tacker.api.v1 import attributes
from tacker.db import api as qdbapi
from tacker.db import db_base
from tacker.db import model_base
from tacker.db import models_v1
from tacker.extensions import servicevm
from tacker import manager
from tacker.openstack.common import jsonutils
from tacker.openstack.common import log as logging
from tacker.plugins.common import constants

LOG = logging.getLogger(__name__)
_ACTIVE_UPDATE = (constants.ACTIVE, constants.PENDING_UPDATE)


###########################################################################
# db tables

class DeviceTemplate(model_base.BASE, models_v1.HasId, models_v1.HasTenant):
    """Represents template to create hosting device
    """
    # Descriptive name
    name = sa.Column(sa.String(255))
    description = sa.Column(sa.String(255))

    # driver to create hosting device. e.g. noop, nova, heat, etc...
    infra_driver = sa.Column(sa.String(255))

    # (key, value) pair to spin up
    attributes = orm.relationship('DeviceTemplateAttribute',
                                  backref='template')


class DeviceTemplateAttribute(model_base.BASE, models_v1.HasId):
    """Represents attributes necessary for spinning up VM in (key, value) pair
    key value pair is adopted for being agnostic to actuall manager of VMs
    like nova, heat or others. e.g. image-id, flavor-id for Nova.
    The interpretation is up to actual driver of hosting device.
    """
    template_id = sa.Column(sa.String(36), sa.ForeignKey('devicetemplates.id'),
                            nullable=False)
    key = sa.Column(sa.String(255), nullable=False)
    value = sa.Column(sa.String(255), nullable=True)


class Device(model_base.BASE, models_v1.HasId, models_v1.HasTenant):
    """Represents devices that hosts services.
    Here the term, 'VM', is intentionally avoided because it can be
    VM or other container.
    """
    template_id = sa.Column(sa.String(36), sa.ForeignKey('devicetemplates.id'))
    template = orm.relationship('DeviceTemplate')

    # sufficient information to uniquely identify hosting device.
    # In case of service VM, it's UUID of nova VM.
    instance_id = sa.Column(sa.String(255), nullable=True)

    # For a management tool to talk to manage this hosting device.
    # opaque string.
    # e.g. (driver, mgmt_url) = (ssh, ip address), ...
    mgmt_url = sa.Column(sa.String(255), nullable=True)

    status = sa.Column(sa.String(255), nullable=False)


class DeviceAttribute(model_base.BASE, models_v1.HasId):
    """Represents kwargs necessary for spinning up VM in (key, value) pair
    key value pair is adopted for being agnostic to actuall manager of VMs
    like nova, heat or others. e.g. image-id, flavor-id for Nova.
    The interpretation is up to actual driver of hosting device.
    """
    device_id = sa.Column(sa.String(36), sa.ForeignKey('devices.id'),
                          nullable=False)
    device = orm.relationship('Device', backref='kwargs')
    key = sa.Column(sa.String(255), nullable=False)
    # json encoded value. example
    # "nic": [{"net-id": <net-uuid>}, {"port-id": <port-uuid>}]
    value = sa.Column(sa.String(4096), nullable=True)


###########################################################################
# actual code to manage those tables

class ServiceResourcePluginDb(servicevm.ServiceVMPluginBase,
                              db_base.CommonDbMixin):

    @property
    def _core_plugin(self):
        return manager.TackerManager.get_plugin()

    def subnet_id_to_network_id(self, context, subnet_id):
        subnet = self._core_plugin.get_subnet(context, subnet_id)
        return subnet['network_id']

    def __init__(self):
        qdbapi.register_models()
        super(ServiceResourcePluginDb, self).__init__()

    def _get_resource(self, context, model, id):
        try:
            return self._get_by_id(context, model, id)
        except orm_exc.NoResultFound:
            if issubclass(model, DeviceTemplate):
                raise servicevm.DeviceTemplateNotFound(device_tempalte_id=id)
            if issubclass(model, Device):
                raise servicevm.DeviceNotFound(device_id=id)
            else:
                raise

    def _make_attributes_dict(self, attributes_db):
        return dict((attr.key, attr.value) for attr in attributes_db)

    def _make_template_dict(self, template, fields=None):
        res = {
            'attributes': self._make_attributes_dict(template['attributes']),
        }
        key_list = ('id', 'tenant_id', 'name', 'description', 'infra_driver')
        res.update((key, template[key]) for key in key_list)
        return self._fields(res, fields)

    def _make_kwargs_dict(self, kwargs_db):
        return dict((arg.key, jsonutils.loads(arg.value)) for arg in kwargs_db)

    def _make_device_dict(self, device_db, fields=None):
        LOG.debug(_('device_db %s'), device_db)
        res = {
            'device_template':
            self._make_template_dict(device_db.template),
            'kwargs': self._make_kwargs_dict(device_db.kwargs),
        }
        key_list = ('id', 'tenant_id', 'instance_id', 'template_id', 'status',
                    'mgmt_url')
        res.update((key, device_db[key]) for key in key_list)
        return self._fields(res, fields)

    @staticmethod
    def _infra_driver_name(device_dict):
        return device_dict['device_template']['infra_driver']

    @staticmethod
    def _instance_id(device_dict):
        return device_dict['instance_id']

    ###########################################################################
    # hosting device template

    def create_device_template(self, context, device_template):
        template = device_template['device_template']
        LOG.debug(_('template %s'), template)
        tenant_id = self._get_tenant_id_for_create(context, template)
        infra_driver = template.get('infra_driver')

        if (not attributes.is_attr_set(infra_driver)):
            LOG.debug(_('hosting device driver unspecified'))
            raise servicevm.InfraDriverNotSpecified()

        with context.session.begin(subtransactions=True):
            template_id = str(uuid.uuid4())
            template_db = DeviceTemplate(
                id=template_id,
                tenant_id=tenant_id,
                name=template.get('name'),
                description=template.get('description'),
                infra_driver=infra_driver)
            context.session.add(template_db)
            for (key, value) in template.get('attributes', {}).items():
                attribute_db = DeviceTemplateAttribute(
                    id=str(uuid.uuid4()),
                    template_id=template_id,
                    key=key,
                    value=value)
                context.session.add(attribute_db)

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
                raise servicevm.DeviceTemplateInUse(
                    device_template_id=device_template_id)

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

    # called internally, not by REST API
    # need enhancement?
    def choose_device_template(self, context, required_attributes=None):
        required_attributes = required_attributes or []
        LOG.debug(_('required_attributes %s'), required_attributes)
        with context.session.begin(subtransactions=True):
            query = context.session.query(DeviceTemplate)
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

    ###########################################################################
    # hosting device

    # called internally, not by REST API
    def _create_device_pre(self, context, device):
        device = device['device']
        LOG.debug(_('device %s'), device)
        tenant_id = self._get_tenant_id_for_create(context, device)
        template_id = device['template_id']
        device_id = device.get('id') or str(uuid.uuid4())
        kwargs = device.get('kwargs', {})
        with context.session.begin(subtransactions=True):
            device_db = Device(id=device_id,
                               tenant_id=tenant_id,
                               instance_id=None,
                               template_id=template_id,
                               status=constants.PENDING_CREATE)
            context.session.add(device_db)
            for key, value in kwargs.items():
                arg = DeviceAttribute(
                    id=str(uuid.uuid4()), device_id=device_id,
                    key=key, value=jsonutils.dumps(value))
                context.session.add(arg)

        return self._make_device_dict(device_db)

    # called internally, not by REST API
    # intsance_id = None means error on creation
    def _create_device_post(self, context, device_id, instance_id,
                            mgmt_url):
        with context.session.begin(subtransactions=True):
            query = (self._model_query(context, Device).
                     filter(Device.id == device_id).
                     filter(Device.status == constants.PENDING_CREATE).
                     one())
            query.update({'instance_id': instance_id, 'mgmt_url': mgmt_url})
            if instance_id is None:
                query.update({'status': constants.ERROR})

    def _create_device_status(self, context, device_id, new_status):
        with context.session.begin(subtransactions=True):
            (self._model_query(context, Device).
                filter(Device.id == device_id).
                filter(Device.status == constants.PENDING_CREATE).
                update({'status': new_status}))

    def _get_device_db(self, context, device_id, new_status):
        try:
            device_db = (
                self._model_query(context, Device).
                filter(Device.id == device_id).
                filter(Device.status.in_(_ACTIVE_UPDATE)).
                filter(Device.status == constants.ACTIVE).
                with_lockmode('update').one())
        except orm_exc.NoResultFound:
            raise servicevm.DeviceNotFound(device_id=device_id)
        if device_db.status == constants.PENDING_UPDATE:
            raise servicevm.DeviceInUse(device_id=device_id)
        device_db.update({'status': new_status})
        return device_db

    def _update_device_pre(self, context, device_id):
        with context.session.begin(subtransactions=True):
            device_db = self._get_device_db(context, device_id,
                                            constants.PENDING_UPDATE)
        return self._make_device_dict(device_db)

    def _update_device_post(self, context, device_id, new_status):
        with context.session.begin(subtransactions=True):
            (self._model_query(context, Device).
             filter(Device.id == device_id).
             filter(Device.status == constants.PENDING_UPDATE).
             update({'status': new_status}))

    def _delete_device_pre(self, context, device_id):
        with context.session.begin(subtransactions=True):
            device_db = self._get_device_db(context, device_id,
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
        self._create_device_post(context, device_dict['id'], instance_id, None)
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
        return self._get_collection(context, Device, self._make_device_dict,
                                    filters=filters, fields=fields)
