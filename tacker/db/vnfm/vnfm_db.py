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

from oslo_log import log as logging
from oslo_serialization import jsonutils
from oslo_utils import timeutils
from oslo_utils import uuidutils

import sqlalchemy as sa
from sqlalchemy import orm
from sqlalchemy.orm import exc as orm_exc
from sqlalchemy import schema

from tacker._i18n import _
from tacker.common import exceptions
import tacker.conf
from tacker.db import db_base
from tacker.db.db_sqlalchemy import models
from tacker.db import model_base
from tacker.db import models_v1
from tacker.db.nfvo import nfvo_db  # noqa: F401
from tacker.db import types
from tacker.extensions import vnfm
from tacker import manager
from tacker.plugins.common import constants

CONF = tacker.conf.CONF

LOG = logging.getLogger(__name__)
CREATE_STATES = (constants.PENDING_CREATE, constants.DEAD)


###########################################################################
# db tables

class VNFD(model_base.BASE, models_v1.HasTenant, models_v1.Audit):
    """Represents VNFD to create VNF."""

    __tablename__ = 'vnfd'
    # vnfdId
    id = sa.Column(sa.String(255), primary_key=True,
                   default=uuidutils.generate_uuid)

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
    vnfd_id = sa.Column(sa.String(255), sa.ForeignKey('vnfd.id'),
                        nullable=False)
    service_type = sa.Column(sa.String(64), nullable=False)


class VNFDAttribute(model_base.BASE, models_v1.HasId):
    """Represents attributes necessary for spinning up VM in (key, value) pair

    key value pair is adopted for being agnostic to actuall manager of VMs.
    The interpretation is up to actual driver of hosting vnf.
    """

    __tablename__ = 'vnfd_attribute'
    vnfd_id = sa.Column(sa.String(255), sa.ForeignKey('vnfd.id'),
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
    vnfd_id = sa.Column(sa.String(255), sa.ForeignKey('vnfd.id'))
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

    def __init__(self):
        super(VNFMPluginDb, self).__init__()

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

    def get_vnfd(self, context, vnfd_id, fields=None):
        vnfd_db = self._get_resource(context, VNFD, vnfd_id)
        if not vnfd_db:
            raise exceptions.NotFound(resource='VNFD', name=vnfd_id)
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

    def _get_vnf_db(self, context, vnf_id, current_statuses):
        try:
            vnf_db = (
                self._model_query(context, VNF).
                filter(VNF.id == vnf_id).
                filter(VNF.status.in_(current_statuses)).
                with_for_update().one())
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

    def update_vnf_cancel_status(self, context, vnf_id, status):
        with context.session.begin(subtransactions=True):
            self._update_vnf_status_db_no_check(
                context, vnf_id, [*constants.PENDING_STATUSES], status)

    def update_vnf_fail_status(self,
                               context,
                               vnf_id,
                               status):
        with context.session.begin(subtransactions=True):
            self._update_vnf_status_db(
                context, vnf_id, [constants.ERROR], status)

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
            LOG.error("Failed to revert scale info for vnf "
                      "instance %(id)s. Error: %(error)s",
                      {"id": vnf_info['id'], "error": e})

    def _update_vnf_scaling(self,
                            context,
                            vnf_info,
                            previous_statuses,
                            status):
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

    def get_vnf(self, context, vnf_id, fields=None):
        vnf_db = self._get_resource(context, VNF, vnf_id)
        return self._make_vnf_dict(vnf_db, fields)

    def get_vnfs(self, context, filters=None, fields=None):
        return self._get_collection(context, VNF, self._make_vnf_dict,
                                    filters=filters, fields=fields)

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

    def _update_vnf_rollback(self,
                            context,
                            vnf_info,
                            previous_statuses,
                            status):
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
