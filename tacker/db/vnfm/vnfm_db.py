# Copyright 2013, 2014 Intel Corporation.
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

from datetime import datetime

from oslo_db.exception import DBDuplicateEntry
from oslo_log import log as logging
from oslo_serialization import jsonutils
from oslo_utils import timeutils
from oslo_utils import uuidutils

import sqlalchemy as sa
from sqlalchemy import orm
from sqlalchemy.orm import exc as orm_exc
from sqlalchemy import schema

from tacker._i18n import _
from tacker.api.v1 import attributes
from tacker.common import exceptions
import tacker.conf
from tacker import context as t_context
from tacker.db.common_services import common_services_db_plugin
from tacker.db import db_base
from tacker.db.db_sqlalchemy import models
from tacker.db import model_base
from tacker.db import models_v1
from tacker.db.nfvo import ns_db
from tacker.db import types
from tacker.extensions import vnfm
from tacker import manager
from tacker.plugins.common import constants

CONF = tacker.conf.CONF

LOG = logging.getLogger(__name__)
_ACTIVE_UPDATE = (constants.ACTIVE, constants.PENDING_UPDATE,
                  constants.PENDING_HEAL)
_ACTIVE_UPDATE_ERROR_DEAD = (
    constants.PENDING_CREATE, constants.ACTIVE, constants.PENDING_UPDATE,
    constants.PENDING_SCALE_IN, constants.PENDING_SCALE_OUT, constants.ERROR,
    constants.PENDING_DELETE, constants.DEAD, constants.PENDING_HEAL)
CREATE_STATES = (constants.PENDING_CREATE, constants.DEAD)


###########################################################################
# db tables

class VNFD(model_base.BASE, models_v1.HasId, models_v1.HasTenant,
           models_v1.Audit):
    """Represents VNFD to create VNF."""

    __tablename__ = 'vnfd'
    # Descriptive name
    name = sa.Column(sa.String(255), nullable=False)
    description = sa.Column(sa.Text)

    # service type that this service vm provides.
    # At first phase, this includes only single service
    # In future, single service VM may accommodate multiple services.
    service_types = orm.relationship('ServiceType', backref='vnfd')

    # driver to communicate with service management
    mgmt_driver = sa.Column(sa.String(255))

    # (key, value) pair to spin up
    attributes = orm.relationship('VNFDAttribute',
                                  backref='vnfd')

    # vnfd template source - inline or onboarded
    template_source = sa.Column(sa.String(255), server_default='onboarded')

    __table_args__ = (
        schema.UniqueConstraint(
            "tenant_id",
            "name",
            "deleted_at",
            name="uniq_vnfd0tenant_id0name0deleted_at"),
    )


class ServiceType(model_base.BASE, models_v1.HasId, models_v1.HasTenant):
    """Represents service type which hosting vnf provides.

    Since a vnf may provide many services, This is one-to-many
    relationship.
    """
    vnfd_id = sa.Column(types.Uuid, sa.ForeignKey('vnfd.id'),
                        nullable=False)
    service_type = sa.Column(sa.String(64), nullable=False)


class VNFDAttribute(model_base.BASE, models_v1.HasId):
    """Represents attributes necessary for spinning up VM in (key, value) pair

    key value pair is adopted for being agnostic to actuall manager of VMs.
    The interpretation is up to actual driver of hosting vnf.
    """

    __tablename__ = 'vnfd_attribute'
    vnfd_id = sa.Column(types.Uuid, sa.ForeignKey('vnfd.id'),
                        nullable=False)
    key = sa.Column(sa.String(255), nullable=False)
    value = sa.Column(sa.TEXT(65535), nullable=True)


class VNF(model_base.BASE, models_v1.HasId, models_v1.HasTenant,
          models_v1.Audit):
    """Represents vnfs that hosts services.

    Here the term, 'VM', is intentionally avoided because it can be
    VM or other container.
    """

    __tablename__ = 'vnf'
    vnfd_id = sa.Column(types.Uuid, sa.ForeignKey('vnfd.id'))
    vnfd = orm.relationship('VNFD')

    name = sa.Column(sa.String(255), nullable=False)
    description = sa.Column(sa.Text, nullable=True)

    # sufficient information to uniquely identify hosting vnf.
    # In case of openstack manager, it's UUID of heat stack.
    instance_id = sa.Column(sa.String(64), nullable=True)

    # For a management tool to talk to manage this hosting vnf.
    # opaque string.
    # e.g. (driver, mgmt_ip_address) = (ssh, ip address), ...
    mgmt_ip_address = sa.Column(sa.String(255), nullable=True)
    attributes = orm.relationship("VNFAttribute", backref="vnf")

    status = sa.Column(sa.String(64), nullable=False)
    vim_id = sa.Column(types.Uuid, sa.ForeignKey('vims.id'), nullable=False)
    placement_attr = sa.Column(types.Json, nullable=True)
    vim = orm.relationship('Vim')
    error_reason = sa.Column(sa.Text, nullable=True)

    __table_args__ = (
        schema.UniqueConstraint(
            "tenant_id",
            "name",
            "deleted_at",
            name="uniq_vnf0tenant_id0name0deleted_at"),
    )


class VNFAttribute(model_base.BASE, models_v1.HasId):
    """Represents kwargs necessary for spinning up VM in (key, value) pair.

    key value pair is adopted for being agnostic to actuall manager of VMs.
    The interpretation is up to actual driver of hosting vnf.
    """

    __tablename__ = 'vnf_attribute'
    vnf_id = sa.Column(types.Uuid, sa.ForeignKey('vnf.id'),
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
        super(VNFMPluginDb, self).__init__()
        self._cos_db_plg = common_services_db_plugin.CommonServicesPluginDb()

    def _get_resource(self, context, model, id):
        try:
            if uuidutils.is_uuid_like(id):
                return self._get_by_id(context, model, id)
            return self._get_by_name(context, model, id)
        except orm_exc.NoResultFound:
            if issubclass(model, VNFD):
                raise vnfm.VNFDNotFound(vnfd_id=id)
            elif issubclass(model, ServiceType):
                raise vnfm.ServiceTypeNotFound(service_type_id=id)
            if issubclass(model, VNF):
                raise vnfm.VNFNotFound(vnf_id=id)
            else:
                raise

    def _make_attributes_dict(self, attributes_db):
        return dict((attr.key, attr.value) for attr in attributes_db)

    def _make_service_types_list(self, service_types):
        return [service_type.service_type
                for service_type in service_types]

    def _make_vnfd_dict(self, vnfd, fields=None):
        res = {
            'attributes': self._make_attributes_dict(vnfd['attributes']),
            'service_types': self._make_service_types_list(
                vnfd.service_types)
        }
        key_list = ('id', 'tenant_id', 'name', 'description',
                    'mgmt_driver', 'created_at', 'updated_at',
                    'template_source')
        res.update((key, vnfd[key]) for key in key_list)
        return self._fields(res, fields)

    def _make_dev_attrs_dict(self, dev_attrs_db):
        return dict((arg.key, arg.value) for arg in dev_attrs_db)

    def _make_vnf_dict(self, vnf_db, fields=None):
        LOG.debug('vnf_db %s', vnf_db)
        LOG.debug('vnf_db attributes %s', vnf_db.attributes)
        res = {
            'vnfd':
            self._make_vnfd_dict(vnf_db.vnfd),
            'attributes': self._make_dev_attrs_dict(vnf_db.attributes),
        }
        key_list = ('id', 'tenant_id', 'name', 'description', 'instance_id',
                    'vim_id', 'placement_attr', 'vnfd_id', 'status',
                    'mgmt_ip_address', 'error_reason', 'created_at',
                    'updated_at')
        res.update((key, vnf_db[key]) for key in key_list)
        return self._fields(res, fields)

    @staticmethod
    def _mgmt_driver_name(vnf_dict):
        return vnf_dict['vnfd']['mgmt_driver']

    @staticmethod
    def _instance_id(vnf_dict):
        return vnf_dict['instance_id']

    def create_vnfd(self, context, vnfd):
        vnfd = vnfd['vnfd']
        LOG.debug('vnfd %s', vnfd)
        tenant_id = self._get_tenant_id_for_create(context, vnfd)
        service_types = vnfd.get('service_types')
        mgmt_driver = vnfd.get('mgmt_driver')
        template_source = vnfd.get("template_source")

        if (not attributes.is_attr_set(service_types)):
            LOG.debug('service types unspecified')
            raise vnfm.ServiceTypesNotSpecified()

        try:
            with context.session.begin(subtransactions=True):
                vnfd_id = uuidutils.generate_uuid()
                vnfd_db = VNFD(
                    id=vnfd_id,
                    tenant_id=tenant_id,
                    name=vnfd.get('name'),
                    description=vnfd.get('description'),
                    mgmt_driver=mgmt_driver,
                    template_source=template_source,
                    deleted_at=datetime.min)
                context.session.add(vnfd_db)
                for (key, value) in vnfd.get('attributes', {}).items():
                    attribute_db = VNFDAttribute(
                        id=uuidutils.generate_uuid(),
                        vnfd_id=vnfd_id,
                        key=key,
                        value=value)
                    context.session.add(attribute_db)
                for service_type in (item['service_type']
                                     for item in vnfd['service_types']):
                    service_type_db = ServiceType(
                        id=uuidutils.generate_uuid(),
                        tenant_id=tenant_id,
                        vnfd_id=vnfd_id,
                        service_type=service_type)
                    context.session.add(service_type_db)
        except DBDuplicateEntry as e:
            raise exceptions.DuplicateEntity(
                _type="vnfd",
                entry=e.columns)
        LOG.debug('vnfd_db %(vnfd_db)s %(attributes)s ',
                  {'vnfd_db': vnfd_db,
                   'attributes': vnfd_db.attributes})
        vnfd_dict = self._make_vnfd_dict(vnfd_db)
        LOG.debug('vnfd_dict %s', vnfd_dict)
        self._cos_db_plg.create_event(
            context, res_id=vnfd_dict['id'],
            res_type=constants.RES_TYPE_VNFD,
            res_state=constants.RES_EVT_ONBOARDED,
            evt_type=constants.RES_EVT_CREATE,
            tstamp=vnfd_dict[constants.RES_EVT_CREATED_FLD])
        return vnfd_dict

    def update_vnfd(self, context, vnfd_id,
                    vnfd):
        with context.session.begin(subtransactions=True):
            vnfd_db = self._get_resource(context, VNFD,
                                         vnfd_id)
            vnfd_db.update(vnfd['vnfd'])
            vnfd_db.update({'updated_at': timeutils.utcnow()})
            vnfd_dict = self._make_vnfd_dict(vnfd_db)
            self._cos_db_plg.create_event(
                context, res_id=vnfd_dict['id'],
                res_type=constants.RES_TYPE_VNFD,
                res_state=constants.RES_EVT_NA_STATE,
                evt_type=constants.RES_EVT_UPDATE,
                tstamp=vnfd_dict[constants.RES_EVT_UPDATED_FLD])
        return vnfd_dict

    def delete_vnfd(self,
                    context,
                    vnfd_id,
                    soft_delete=True):
        with context.session.begin(subtransactions=True):
            # TODO(yamahata): race. prevent from newly inserting hosting vnf
            #                 that refers to this vnfd
            vnfs_db = context.session.query(VNF).filter_by(
                vnfd_id=vnfd_id).first()
            if vnfs_db is not None and vnfs_db.deleted_at is None:
                raise vnfm.VNFDInUse(vnfd_id=vnfd_id)
            vnfd_db = self._get_resource(context, VNFD,
                                         vnfd_id)
            if soft_delete:
                vnfd_db.update({'deleted_at': timeutils.utcnow()})
                self._cos_db_plg.create_event(
                    context, res_id=vnfd_db['id'],
                    res_type=constants.RES_TYPE_VNFD,
                    res_state=constants.RES_EVT_NA_STATE,
                    evt_type=constants.RES_EVT_DELETE,
                    tstamp=vnfd_db[constants.RES_EVT_DELETED_FLD])
            else:
                context.session.query(ServiceType).filter_by(
                    vnfd_id=vnfd_id).delete()
                context.session.query(VNFDAttribute).filter_by(
                    vnfd_id=vnfd_id).delete()
                context.session.delete(vnfd_db)

    def get_vnfd(self, context, vnfd_id, fields=None):
        vnfd_db = self._get_resource(context, VNFD, vnfd_id)
        if not vnfd_db:
            raise exceptions.NotFound(resource='VNFD', name=vnfd_id)
        return self._make_vnfd_dict(vnfd_db)

    def get_vnfds(self, context, filters, fields=None):
        if ('template_source' in filters and
                filters['template_source'][0] == 'all'):
            filters.pop('template_source')
        return self._get_collection(context, VNFD,
                                    self._make_vnfd_dict,
                                    filters=filters, fields=fields)

    def choose_vnfd(self, context, service_type,
                    required_attributes=None):
        required_attributes = required_attributes or []
        LOG.debug('required_attributes %s', required_attributes)
        with context.session.begin(subtransactions=True):
            query = (
                context.session.query(VNFD).
                filter(
                    sa.exists().
                    where(sa.and_(
                        VNFD.id == ServiceType.vnfd_id,
                        ServiceType.service_type == service_type))))
            for key in required_attributes:
                query = query.filter(
                    sa.exists().
                    where(sa.and_(
                        VNFD.id ==
                        VNFDAttribute.vnfd_id,
                        VNFDAttribute.key == key)))
            LOG.debug('statements %s', query)
            vnfd_db = query.first()
            if vnfd_db:
                return self._make_vnfd_dict(vnfd_db)

    def _vnf_attribute_update_or_create(
            self, context, vnf_id, key, value):
        arg = (self._model_query(context, VNFAttribute).
               filter(VNFAttribute.vnf_id == vnf_id).
               filter(VNFAttribute.key == key).first())
        if arg:
            arg.value = value
        else:
            arg = VNFAttribute(
                id=uuidutils.generate_uuid(), vnf_id=vnf_id,
                key=key, value=value)
            context.session.add(arg)

    # called internally, not by REST API
    def _create_vnf_pre(self, context, vnf):
        LOG.debug('vnf %s', vnf)
        tenant_id = self._get_tenant_id_for_create(context, vnf)
        vnfd_id = vnf['vnfd_id']
        name = vnf.get('name')
        vnf_id = uuidutils.generate_uuid()
        attributes = vnf.get('attributes', {})
        vim_id = vnf.get('vim_id')
        placement_attr = vnf.get('placement_attr', {})
        try:
            with context.session.begin(subtransactions=True):
                vnfd_db = self._get_resource(context, VNFD,
                                             vnfd_id)
                vnf_db = VNF(id=vnf_id,
                             tenant_id=tenant_id,
                             name=name,
                             description=vnfd_db.description,
                             instance_id=None,
                             vnfd_id=vnfd_id,
                             vim_id=vim_id,
                             placement_attr=placement_attr,
                             status=constants.PENDING_CREATE,
                             error_reason=None,
                             deleted_at=datetime.min)
                context.session.add(vnf_db)
                for key, value in attributes.items():
                    arg = VNFAttribute(
                        id=uuidutils.generate_uuid(), vnf_id=vnf_id,
                        key=key, value=value)
                    context.session.add(arg)
        except DBDuplicateEntry as e:
            raise exceptions.DuplicateEntity(
                _type="vnf",
                entry=e.columns)
        evt_details = "VNF UUID assigned."
        self._cos_db_plg.create_event(
            context, res_id=vnf_id,
            res_type=constants.RES_TYPE_VNF,
            res_state=constants.PENDING_CREATE,
            evt_type=constants.RES_EVT_CREATE,
            tstamp=vnf_db[constants.RES_EVT_CREATED_FLD],
            details=evt_details)
        return self._make_vnf_dict(vnf_db)

    # called internally, not by REST API
    # intsance_id = None means error on creation
    def _create_vnf_post(self, context, vnf_id, instance_id,
                         mgmt_ip_address, vnf_dict):
        LOG.debug('vnf_dict %s', vnf_dict)
        with context.session.begin(subtransactions=True):
            query = (self._model_query(context, VNF).
                     filter(VNF.id == vnf_id).
                     filter(VNF.status.in_(CREATE_STATES)).
                     one())
            query.update({'instance_id': instance_id,
                          'mgmt_ip_address': mgmt_ip_address})
            if instance_id is None or vnf_dict['status'] == constants.ERROR:
                query.update({'status': constants.ERROR})

            for (key, value) in vnf_dict['attributes'].items():
                # do not store decrypted vim auth in vnf attr table
                if 'vim_auth' not in key:
                    self._vnf_attribute_update_or_create(context, vnf_id,
                                                         key, value)
        evt_details = ("Infra Instance ID created: %s and "
                       "Mgmt IP address set: %s") % (instance_id,
                                                     mgmt_ip_address)
        self._cos_db_plg.create_event(
            context, res_id=vnf_dict['id'],
            res_type=constants.RES_TYPE_VNF,
            res_state=vnf_dict['status'],
            evt_type=constants.RES_EVT_CREATE,
            tstamp=timeutils.utcnow(), details=evt_details)

    def _create_vnf_status(self, context, vnf_id, new_status):
        with context.session.begin(subtransactions=True):
            query = (self._model_query(context, VNF).
                     filter(VNF.id == vnf_id).
                     filter(VNF.status.in_(CREATE_STATES)).one())
            query.update({'status': new_status})
            self._cos_db_plg.create_event(
                context, res_id=vnf_id,
                res_type=constants.RES_TYPE_VNF,
                res_state=new_status,
                evt_type=constants.RES_EVT_CREATE,
                tstamp=timeutils.utcnow(), details="VNF creation completed")

    def _get_vnf_db(self, context, vnf_id, current_statuses):
        try:
            vnf_db = (
                self._model_query(context, VNF).
                filter(VNF.id == vnf_id).
                filter(VNF.status.in_(current_statuses)).
                with_lockmode('update').one())
        except orm_exc.NoResultFound:
            raise vnfm.VNFNotFound(vnf_id=vnf_id)
        return vnf_db

    def _update_vnf_status_db(self, context, vnf_id, current_statuses,
                              new_status, vnf_db=None):
        if not vnf_db:
            vnf_db = self._get_vnf_db(context, vnf_id, current_statuses)
        if self.check_vnf_status_legality(vnf_db, vnf_id):
            vnf_db.update({'status': new_status})
        return vnf_db

    def _update_vnf_status_db_no_check(self, context, vnf_id, current_statuses,
                              new_status):
        vnf_db = self._get_vnf_db(context, vnf_id, current_statuses)
        vnf_db.update({'status': new_status})
        return vnf_db

    @staticmethod
    def check_vnf_status_legality(vnf_db, vnf_id):
        if vnf_db.status == constants.PENDING_DELETE:
            error_reason = _("Operation on PENDING_DELETE VNF "
                             "is not permitted. Please contact your "
                             "Administrator.")
            raise vnfm.VNFDeleteFailed(reason=error_reason)
        if(vnf_db.status in [constants.PENDING_UPDATE,
                             constants.PENDING_HEAL]):
            raise vnfm.VNFInUse(vnf_id=vnf_id)
        return True

    def _update_vnf_scaling_status(self,
                                   context,
                                   policy,
                                   previous_statuses,
                                   status,
                                   mgmt_ip_address=None):
        with context.session.begin(subtransactions=True):
            vnf_db = self._update_vnf_status_db(
                context, policy['vnf']['id'], previous_statuses, status)
            if mgmt_ip_address:
                vnf_db.update({'mgmt_ip_address': mgmt_ip_address})
        updated_vnf_dict = self._make_vnf_dict(vnf_db)
        self._cos_db_plg.create_event(
            context, res_id=updated_vnf_dict['id'],
            res_type=constants.RES_TYPE_VNF,
            res_state=updated_vnf_dict['status'],
            evt_type=constants.RES_EVT_SCALE,
            tstamp=timeutils.utcnow())
        return updated_vnf_dict

    def _update_vnf_scaling_status_err(self,
                                       context,
                                       vnf_info):
        previous_statuses = ['PENDING_SCALE_OUT', 'PENDING_SCALE_IN', 'ACTIVE']

        try:
            with context.session.begin(subtransactions=True):
                self._update_vnf_status_db(
                    context, vnf_info['id'], previous_statuses, 'ERROR')
        except Exception as e:
            LOG.warning("Failed to revert scale info for vnf "
                        "instance %(id)s. Error: %(error)s",
                        {"id": vnf_info['id'], "error": e})
        self._cos_db_plg.create_event(
            context, res_id=vnf_info['id'],
            res_type=constants.RES_TYPE_VNF,
            res_state='ERROR',
            evt_type=constants.RES_EVT_SCALE,
            tstamp=timeutils.utcnow())

    def _update_vnf_scaling(self,
                            context,
                            vnf_info,
                            previous_statuses,
                            status,
                            vnf_instance=None,
                            vnf_lcm_op_occ=None):
        with context.session.begin(subtransactions=True):
            timestamp = timeutils.utcnow()
            (self._model_query(context, VNF).
             filter(VNF.id == vnf_info['id']).
             filter(VNF.status == previous_statuses).
             update({'status': status,
                     'updated_at': timestamp}))

            dev_attrs = vnf_info.get('attributes', {})
            (context.session.query(VNFAttribute).
             filter(VNFAttribute.vnf_id == vnf_info['id']).
             filter(~VNFAttribute.key.in_(dev_attrs.keys())).
             delete(synchronize_session='fetch'))

            for (key, value) in dev_attrs.items():
                if 'vim_auth' not in key:
                    self._vnf_attribute_update_or_create(
                        context, vnf_info['id'], key, value)
            self._cos_db_plg.create_event(
                context, res_id=vnf_info['id'],
                res_type=constants.RES_TYPE_VNF,
                res_state=status,
                evt_type=constants.RES_EVT_SCALE,
                tstamp=timestamp)
            if vnf_lcm_op_occ:
                vnf_lcm_op_occ.state_entered_time = timestamp
                vnf_lcm_op_occ.save()
            if vnf_instance:
                vnf_instance.save()

    def _update_vnf_pre(self, context, vnf_id, new_status):
        with context.session.begin(subtransactions=True):
            vnf_db = self._update_vnf_status_db(
                context, vnf_id, _ACTIVE_UPDATE, new_status)
        updated_vnf_dict = self._make_vnf_dict(vnf_db)
        if new_status in constants.VNF_STATUS_TO_EVT_TYPES:
            self._cos_db_plg.create_event(
                context, res_id=vnf_id,
                res_type=constants.RES_TYPE_VNF,
                res_state=updated_vnf_dict['status'],
                evt_type=constants.VNF_STATUS_TO_EVT_TYPES[new_status],
                tstamp=timeutils.utcnow())
        return updated_vnf_dict

    def _update_vnf_post(self, context, vnf_id, new_status,
                         new_vnf_dict, vnf_status, evt_type):
        updated_time_stamp = timeutils.utcnow()
        with context.session.begin(subtransactions=True):
            (self._model_query(context, VNF).
             filter(VNF.id == vnf_id).
             filter(VNF.status == vnf_status).
             update({'status': new_status,
                     'updated_at': updated_time_stamp,
                     'mgmt_ip_address': new_vnf_dict['mgmt_ip_address']}))

            dev_attrs = new_vnf_dict.get('attributes', {})
            (context.session.query(VNFAttribute).
             filter(VNFAttribute.vnf_id == vnf_id).
             filter(~VNFAttribute.key.in_(dev_attrs.keys())).
             delete(synchronize_session='fetch'))

            for (key, value) in dev_attrs.items():
                if 'vim_auth' not in key:
                    self._vnf_attribute_update_or_create(context, vnf_id,
                                                         key, value)
        self._cos_db_plg.create_event(
            context, res_id=vnf_id,
            res_type=constants.RES_TYPE_VNF,
            res_state=new_status,
            evt_type=evt_type,
            tstamp=updated_time_stamp)

    def _delete_vnf_pre(self, context, vnf_id, force_delete=False):
        with context.session.begin(subtransactions=True):

            nss_db = context.session.query(ns_db.NS).filter(
                ns_db.NS.vnf_ids.like("%" + vnf_id + "%")).first()

            if not force_delete:
                # If vnf is deleted by NFVO, then vnf_id would
                # exist in the nss_db otherwise it should be queried from
                # vnf db table.
                if nss_db is not None:
                    if nss_db.status not in [constants.PENDING_DELETE,
                                             constants.ERROR]:
                        raise vnfm.VNFInUse(vnf_id=vnf_id)
                else:
                    vnf_db = self._get_vnf_db(context, vnf_id,
                                              _ACTIVE_UPDATE_ERROR_DEAD)
                    if (vnf_db is not None and vnf_db.status == constants.
                            PENDING_CREATE):
                        raise vnfm.VNFInUse(
                            message="Operation on PENDING_CREATE VNF is not "
                                    "permitted.")

                    vnf_db = self._update_vnf_status_db(
                        context, vnf_id, _ACTIVE_UPDATE_ERROR_DEAD,
                        constants.PENDING_DELETE, vnf_db=vnf_db)
            else:
                vnf_db = self._update_vnf_status_db_no_check(context,
                    vnf_id, _ACTIVE_UPDATE_ERROR_DEAD,
                constants.PENDING_DELETE)
        deleted_vnf_db = self._make_vnf_dict(vnf_db)
        details = "VNF delete initiated" if not force_delete else \
            "VNF force delete initiated"
        self._cos_db_plg.create_event(
            context, res_id=vnf_id,
            res_type=constants.RES_TYPE_VNF,
            res_state=deleted_vnf_db['status'],
            evt_type=constants.RES_EVT_DELETE,
            tstamp=timeutils.utcnow(), details=details)
        return deleted_vnf_db

    def _delete_vnf_force(self, context, vnf_id):
        # Check mapping vnf in vnffg_db
        with context.session.begin(subtransactions=True):
            nss_db = context.session.query(ns_db.NS).filter(
                ns_db.NS.vnf_ids.like("%" + vnf_id + "%")).first()
            if nss_db:
                pass

    def _delete_vnf_post(self, context, vnf_dict, error,
                         soft_delete=True, force_delete=False):
        vnf_id = vnf_dict['id']
        with context.session.begin(subtransactions=True):
            if force_delete:
                query = (
                    self._model_query(context, VNF).
                    filter(VNF.id == vnf_id))
            else:
                query = (
                    self._model_query(context, VNF).
                    filter(VNF.id == vnf_id).
                    filter(VNF.status == constants.PENDING_DELETE))
            if error:
                query.update({'status': constants.ERROR})
                self._cos_db_plg.create_event(
                    context, res_id=vnf_id,
                    res_type=constants.RES_TYPE_VNF,
                    res_state=constants.ERROR,
                    evt_type=constants.RES_EVT_DELETE,
                    tstamp=timeutils.utcnow(),
                    details="VNF Delete ERROR")
            else:
                if soft_delete:
                    deleted_time_stamp = timeutils.utcnow()
                    query.update({'deleted_at': deleted_time_stamp})
                    self._cos_db_plg.create_event(
                        context, res_id=vnf_id,
                        res_type=constants.RES_TYPE_VNF,
                        res_state=constants.PENDING_DELETE,
                        evt_type=constants.RES_EVT_DELETE,
                        tstamp=deleted_time_stamp,
                        details="VNF Delete Complete")
                else:
                    (self._model_query(context, VNFAttribute).
                     filter(VNFAttribute.vnf_id == vnf_id).delete())
                    query.delete()

                # Delete corresponding vnfd
                if vnf_dict['vnfd']['template_source'] == "inline":
                    self.delete_vnfd(context, vnf_dict["vnfd_id"])

    # reference implementation. needs to be overrided by subclass
    def create_vnf(self, context, vnf):
        vnf_dict = self._create_vnf_pre(context, vnf)
        # start actual creation of hosting vnf.
        # Waiting for completion of creation should be done backgroundly
        # by another thread if it takes a while.
        instance_id = uuidutils.generate_uuid()
        vnf_dict['instance_id'] = instance_id
        self._create_vnf_post(context, vnf_dict['id'], instance_id, None,
                              vnf_dict)
        self._create_vnf_status(context, vnf_dict['id'],
                                constants.ACTIVE)
        return vnf_dict

    # reference implementation. needs to be overrided by subclass
    def update_vnf(self, context, vnf_id, vnf):
        new_status = constants.PENDING_UPDATE
        vnf_dict = self._update_vnf_pre(context, vnf_id, new_status)
        # start actual update of hosting vnf
        # waiting for completion of update should be done backgroundly
        # by another thread if it takes a while
        self._update_vnf_post(context, vnf_id,
                              constants.ACTIVE,
                              vnf_dict)
        return vnf_dict

    # reference implementation. needs to be overrided by subclass
    def delete_vnf(self, context, vnf_id, soft_delete=True):
        vnf_dict = self._delete_vnf_pre(context, vnf_id)
        # start actual deletion of hosting vnf.
        # Waiting for completion of deletion should be done backgroundly
        # by another thread if it takes a while.
        self._delete_vnf_post(context,
                              vnf_dict,
                              False,
                              soft_delete=soft_delete)

    def get_vnf(self, context, vnf_id, fields=None):
        vnf_db = self._get_resource(context, VNF, vnf_id)
        return self._make_vnf_dict(vnf_db, fields)

    def get_vnfs(self, context, filters=None, fields=None):
        return self._get_collection(context, VNF, self._make_vnf_dict,
                                    filters=filters, fields=fields)

    def set_vnf_error_status_reason(self, context, vnf_id, new_reason):
        with context.session.begin(subtransactions=True):
            (self._model_query(context, VNF).
                filter(VNF.id == vnf_id).
                update({'error_reason': new_reason}))

    def _mark_vnf_status(self, vnf_id, exclude_status, new_status):
        context = t_context.get_admin_context()
        with context.session.begin(subtransactions=True):
            try:
                vnf_db = (
                    self._model_query(context, VNF).
                    filter(VNF.id == vnf_id).
                    filter(~VNF.status.in_(exclude_status)).
                    with_lockmode('update').one())
            except orm_exc.NoResultFound:
                LOG.warning('no vnf found %s', vnf_id)
                return False

            vnf_db.update({'status': new_status})
            self._cos_db_plg.create_event(
                context, res_id=vnf_id,
                res_type=constants.RES_TYPE_VNF,
                res_state=new_status,
                evt_type=constants.RES_EVT_MONITOR,
                tstamp=timeutils.utcnow())
        return True

    def _mark_vnf_error(self, vnf_id):
        return self._mark_vnf_status(
            vnf_id, [constants.DEAD], constants.ERROR)

    def _mark_vnf_dead(self, vnf_id):
        exclude_status = [
            constants.PENDING_CREATE,
            constants.PENDING_UPDATE,
            constants.PENDING_DELETE,
            constants.ERROR]
        return self._mark_vnf_status(
            vnf_id, exclude_status, constants.DEAD)

    def create_placement_constraint(self, context, placement_obj_list):
        context.session.add_all(placement_obj_list)

    def get_placement_constraint(self, context, vnf_instance_id):
        placement_constraint = (
            self._model_query(context, models.PlacementConstraint).filter(
                models.PlacementConstraint.vnf_instance_id == vnf_instance_id).
            filter(models.PlacementConstraint.deleted == 0).all())
        return placement_constraint

    def update_placement_constraint_heal(self, context,
                                         vnf_info,
                                         vnf_instance):
        if not vnf_info.get('grant'):
            return
        placement_obj_list = vnf_info['placement_obj_list']
        inst_info = vnf_instance.instantiated_vnf_info
        for vnfc in inst_info.vnfc_resource_info:
            for placement_obj in placement_obj_list:
                rsc_dict = jsonutils.loads(placement_obj.resource)
                for rsc in rsc_dict:
                    if vnfc.id == rsc.get('resource_id') and\
                       rsc.get('id_type') == 'GRANT':
                        rsc['id_type'] = 'RES_MGMT'
                        rsc['resource_id'] = vnfc.\
                            compute_resource.resource_id
                        rsc['vim_connection_id'] = vnfc.\
                            compute_resource.vim_connection_id
                placement_obj.resource = jsonutils.dumps(rsc_dict)
                self.update_placement_constraint(context, placement_obj)

    def delete_placement_constraint(self, context, vnf_instance_id):
        (self._model_query(context, models.PlacementConstraint).
            filter(
                models.PlacementConstraint.vnf_instance_id == vnf_instance_id).
            filter(models.PlacementConstraint.deleted == 0).
            update({'deleted': 0, 'deleted_at': timeutils.utcnow()}))

    def update_placement_constraint(self, context, placement_obj):
        (self._model_query(
            context,
            models.PlacementConstraint).filter(
                models.PlacementConstraint.id == placement_obj.id).
            filter(models.PlacementConstraint.deleted == 0).
            update({
                'resource': placement_obj.resource,
                'updated_at': timeutils.utcnow()}))

    def update_vnf_rollback_status_err(self,
                                       context,
                                       vnf_info):
        vnf_lcm_op_occs = vnf_info['vnf_lcm_op_occ']
        if vnf_lcm_op_occs.operation == 'SCALE':
            self._cos_db_plg.create_event(
                context, res_id=vnf_info['id'],
                res_type=constants.RES_TYPE_VNF,
                res_state='ERROR',
                evt_type=constants.RES_EVT_SCALE,
                tstamp=timeutils.utcnow())
        else:
            self._cos_db_plg.create_event(
                context, res_id=vnf_info['id'],
                res_type=constants.RES_TYPE_VNF,
                res_state='ERROR',
                evt_type=constants.RES_EVT_CREATE,
                tstamp=timeutils.utcnow())

    def _update_vnf_rollback_pre(self,
                                 context,
                                 vnf_info):
        vnf_lcm_op_occs = vnf_info['vnf_lcm_op_occ']
        if vnf_lcm_op_occs.operation == 'SCALE':
            self._cos_db_plg.create_event(
                context, res_id=vnf_info['id'],
                res_type=constants.RES_TYPE_VNF,
                res_state='ROLL_BACK',
                evt_type=constants.RES_EVT_SCALE,
                tstamp=timeutils.utcnow())
        else:
            self._cos_db_plg.create_event(
                context, res_id=vnf_info['id'],
                res_type=constants.RES_TYPE_VNF,
                res_state='ROLL_BACK',
                evt_type=constants.RES_EVT_CREATE,
                tstamp=timeutils.utcnow())

    def _update_vnf_rollback(self,
                            context,
                            vnf_info,
                            previous_statuses,
                            status,
                            vnf_instance=None,
                            vnf_lcm_op_occ=None):
        with context.session.begin(subtransactions=True):
            timestamp = timeutils.utcnow()
            (self._model_query(context, VNF).
             filter(VNF.id == vnf_info['id']).
             filter(VNF.status == previous_statuses).
             update({'status': status,
                     'updated_at': timestamp}))

            dev_attrs = vnf_info.get('attributes', {})
            (context.session.query(VNFAttribute).
             filter(VNFAttribute.vnf_id == vnf_info['id']).
             filter(~VNFAttribute.key.in_(dev_attrs.keys())).
             delete(synchronize_session='fetch'))

            vnf_lcm_op_occs = vnf_info['vnf_lcm_op_occ']
            if vnf_lcm_op_occs.operation == 'SCALE':
                for (key, value) in dev_attrs.items():
                    if 'vim_auth' not in key:
                        self._vnf_attribute_update_or_create(
                            context, vnf_info['id'], key, value)
                self._cos_db_plg.create_event(
                    context, res_id=vnf_info['id'],
                    res_type=constants.RES_TYPE_VNF,
                    res_state=status,
                    evt_type=constants.RES_EVT_SCALE,
                    tstamp=timestamp)
            else:
                self._cos_db_plg.create_event(
                    context, res_id=vnf_info['id'],
                    res_type=constants.RES_TYPE_VNF,
                    res_state=status,
                    evt_type=constants.RES_EVT_CREATE,
                    tstamp=timestamp)
            if vnf_lcm_op_occ:
                vnf_lcm_op_occ.state_entered_time = timestamp
                vnf_lcm_op_occ.save()
            if vnf_instance:
                vnf_instance.save()
