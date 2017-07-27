# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import ast
from datetime import datetime

from oslo_db.exception import DBDuplicateEntry
from oslo_log import log as logging
from oslo_utils import timeutils
from oslo_utils import uuidutils
from six import iteritems

import sqlalchemy as sa
from sqlalchemy import orm
from sqlalchemy.orm import exc as orm_exc
from sqlalchemy import schema

from tacker.common import exceptions
from tacker.db.common_services import common_services_db_plugin
from tacker.db import db_base
from tacker.db import model_base
from tacker.db import models_v1
from tacker.db import types
from tacker.extensions import nfvo
from tacker.extensions.nfvo_plugins import network_service
from tacker.plugins.common import constants

LOG = logging.getLogger(__name__)
_ACTIVE_UPDATE = (constants.ACTIVE, constants.PENDING_UPDATE)
_ACTIVE_UPDATE_ERROR_DEAD = (
    constants.PENDING_CREATE, constants.ACTIVE, constants.PENDING_UPDATE,
    constants.ERROR, constants.DEAD)
CREATE_STATES = (constants.PENDING_CREATE, constants.DEAD)


###########################################################################
# db tables

class NSD(model_base.BASE, models_v1.HasId, models_v1.HasTenant,
        models_v1.Audit):
    """Represents NSD to create NS."""

    __tablename__ = 'nsd'
    # Descriptive name
    name = sa.Column(sa.String(255), nullable=False)
    description = sa.Column(sa.Text)
    vnfds = sa.Column(types.Json, nullable=True)

    # Nsd template source - onboarded
    template_source = sa.Column(sa.String(255), server_default='onboarded')

    # (key, value) pair to spin up
    attributes = orm.relationship('NSDAttribute',
                                  backref='nsd')

    __table_args__ = (
        schema.UniqueConstraint(
            "tenant_id",
            "name",
            name="uniq_nsd0tenant_id0name"),
    )


class NSDAttribute(model_base.BASE, models_v1.HasId):
    """Represents attributes necessary for creation of ns in (key, value) pair

    """

    __tablename__ = 'nsd_attribute'
    nsd_id = sa.Column(types.Uuid, sa.ForeignKey('nsd.id'),
            nullable=False)
    key = sa.Column(sa.String(255), nullable=False)
    value = sa.Column(sa.TEXT(65535), nullable=True)


class NS(model_base.BASE, models_v1.HasId, models_v1.HasTenant,
        models_v1.Audit):
    """Represents network services that deploys services.

    """

    __tablename__ = 'ns'
    nsd_id = sa.Column(types.Uuid, sa.ForeignKey('nsd.id'))
    nsd = orm.relationship('NSD')

    name = sa.Column(sa.String(255), nullable=False)
    description = sa.Column(sa.Text, nullable=True)

    # Dict of VNF details that network service launches
    vnf_ids = sa.Column(sa.TEXT(65535), nullable=True)

    # Dict of mgmt urls that network servic launches
    mgmt_urls = sa.Column(sa.TEXT(65535), nullable=True)

    status = sa.Column(sa.String(64), nullable=False)
    vim_id = sa.Column(types.Uuid, sa.ForeignKey('vims.id'), nullable=False)
    error_reason = sa.Column(sa.Text, nullable=True)

    __table_args__ = (
        schema.UniqueConstraint(
            "tenant_id",
            "name",
            name="uniq_ns0tenant_id0name"),
    )


class NSPluginDb(network_service.NSPluginBase, db_base.CommonDbMixin):

    def __init__(self):
        super(NSPluginDb, self).__init__()
        self._cos_db_plg = common_services_db_plugin.CommonServicesPluginDb()

    def _get_resource(self, context, model, id):
        try:
            return self._get_by_id(context, model, id)
        except orm_exc.NoResultFound:
            if issubclass(model, NSD):
                raise network_service.NSDNotFound(nsd_id=id)
            if issubclass(model, NS):
                raise network_service.NSNotFound(ns_id=id)
            else:
                raise

    def _get_ns_db(self, context, ns_id, current_statuses, new_status):
        try:
            ns_db = (
                self._model_query(context, NS).
                filter(NS.id == ns_id).
                filter(NS.status.in_(current_statuses)).
                with_lockmode('update').one())
        except orm_exc.NoResultFound:
            raise network_service.NSNotFound(ns_id=ns_id)
        ns_db.update({'status': new_status})
        return ns_db

    def _make_attributes_dict(self, attributes_db):
        return dict((attr.key, attr.value) for attr in attributes_db)

    def _make_nsd_dict(self, nsd, fields=None):
        res = {
            'attributes': self._make_attributes_dict(nsd['attributes']),
        }
        key_list = ('id', 'tenant_id', 'name', 'description',
                    'created_at', 'updated_at', 'vnfds', 'template_source')
        res.update((key, nsd[key]) for key in key_list)
        return self._fields(res, fields)

    def _make_dev_attrs_dict(self, dev_attrs_db):
        return dict((arg.key, arg.value) for arg in dev_attrs_db)

    def _make_ns_dict(self, ns_db, fields=None):
        LOG.debug('ns_db %s', ns_db)
        res = {}
        key_list = ('id', 'tenant_id', 'nsd_id', 'name', 'description',
                    'vnf_ids', 'status', 'mgmt_urls', 'error_reason',
                    'vim_id', 'created_at', 'updated_at')
        res.update((key, ns_db[key]) for key in key_list)
        return self._fields(res, fields)

    def create_nsd(self, context, nsd):
        vnfds = nsd['vnfds']
        nsd = nsd['nsd']
        LOG.debug('nsd %s', nsd)
        tenant_id = self._get_tenant_id_for_create(context, nsd)
        template_source = nsd.get('template_source')

        try:
            with context.session.begin(subtransactions=True):
                nsd_id = uuidutils.generate_uuid()
                nsd_db = NSD(
                    id=nsd_id,
                    tenant_id=tenant_id,
                    name=nsd.get('name'),
                    vnfds=vnfds,
                    description=nsd.get('description'),
                    deleted_at=datetime.min,
                    template_source=template_source)
                context.session.add(nsd_db)
                for (key, value) in nsd.get('attributes', {}).items():
                    attribute_db = NSDAttribute(
                        id=uuidutils.generate_uuid(),
                        nsd_id=nsd_id,
                        key=key,
                        value=value)
                    context.session.add(attribute_db)
        except DBDuplicateEntry as e:
            raise exceptions.DuplicateEntity(
                _type="nsd",
                entry=e.columns)
        LOG.debug('nsd_db %(nsd_db)s %(attributes)s ',
                  {'nsd_db': nsd_db,
                   'attributes': nsd_db.attributes})
        nsd_dict = self._make_nsd_dict(nsd_db)
        LOG.debug('nsd_dict %s', nsd_dict)
        self._cos_db_plg.create_event(
            context, res_id=nsd_dict['id'],
            res_type=constants.RES_TYPE_NSD,
            res_state=constants.RES_EVT_ONBOARDED,
            evt_type=constants.RES_EVT_CREATE,
            tstamp=nsd_dict[constants.RES_EVT_CREATED_FLD])
        return nsd_dict

    def delete_nsd(self,
            context,
            nsd_id,
            soft_delete=True):
        with context.session.begin(subtransactions=True):
            nss_db = context.session.query(NS).filter_by(
                nsd_id=nsd_id).first()
            if nss_db is not None and nss_db.deleted_at is None:
                raise nfvo.NSDInUse(nsd_id=nsd_id)

            nsd_db = self._get_resource(context, NSD,
                                        nsd_id)
            if soft_delete:
                nsd_db.update({'deleted_at': timeutils.utcnow()})
                self._cos_db_plg.create_event(
                    context, res_id=nsd_db['id'],
                    res_type=constants.RES_TYPE_NSD,
                    res_state=constants.RES_EVT_NA_STATE,
                    evt_type=constants.RES_EVT_DELETE,
                    tstamp=nsd_db[constants.RES_EVT_DELETED_FLD])
            else:
                context.session.query(NSDAttribute).filter_by(
                    nsd_id=nsd_id).delete()
                context.session.delete(nsd_db)

    def get_nsd(self, context, nsd_id, fields=None):
        nsd_db = self._get_resource(context, NSD, nsd_id)
        return self._make_nsd_dict(nsd_db)

    def get_nsds(self, context, filters, fields=None):
        if ('template_source' in filters) and \
                (filters['template_source'][0] == 'all'):
            filters.pop('template_source')
        return self._get_collection(context, NSD,
                                    self._make_nsd_dict,
                                    filters=filters, fields=fields)

    # reference implementation. needs to be overrided by subclass
    def create_ns(self, context, ns):
        LOG.debug('ns %s', ns)
        ns = ns['ns']
        tenant_id = self._get_tenant_id_for_create(context, ns)
        nsd_id = ns['nsd_id']
        vim_id = ns['vim_id']
        name = ns.get('name')
        ns_id = uuidutils.generate_uuid()
        try:
            with context.session.begin(subtransactions=True):
                nsd_db = self._get_resource(context, NSD,
                                            nsd_id)
                ns_db = NS(id=ns_id,
                           tenant_id=tenant_id,
                           name=name,
                           description=nsd_db.description,
                           vnf_ids=None,
                           status=constants.PENDING_CREATE,
                           mgmt_urls=None,
                           nsd_id=nsd_id,
                           vim_id=vim_id,
                           error_reason=None,
                           deleted_at=datetime.min)
                context.session.add(ns_db)
        except DBDuplicateEntry as e:
            raise exceptions.DuplicateEntity(
                _type="ns",
                entry=e.columns)
        evt_details = "NS UUID assigned."
        self._cos_db_plg.create_event(
            context, res_id=ns_id,
            res_type=constants.RES_TYPE_NS,
            res_state=constants.PENDING_CREATE,
            evt_type=constants.RES_EVT_CREATE,
            tstamp=ns_db[constants.RES_EVT_CREATED_FLD],
            details=evt_details)
        return self._make_ns_dict(ns_db)

    def create_ns_post(self, context, ns_id, mistral_obj,
            vnfd_dict, error_reason):
        LOG.debug('ns ID %s', ns_id)
        output = ast.literal_eval(mistral_obj.output)
        mgmt_urls = dict()
        vnf_ids = dict()
        if len(output) > 0:
            for vnfd_name, vnfd_val in iteritems(vnfd_dict):
                for instance in vnfd_val['instances']:
                    if 'mgmt_url_' + instance in output:
                        mgmt_urls[instance] = ast.literal_eval(
                            output['mgmt_url_' + instance].strip())
                        vnf_ids[instance] = output['vnf_id_' + instance]
            vnf_ids = str(vnf_ids)
            mgmt_urls = str(mgmt_urls)

        if not vnf_ids:
            vnf_ids = None
        if not mgmt_urls:
            mgmt_urls = None
        status = constants.ACTIVE if mistral_obj.state == 'SUCCESS' \
            else constants.ERROR
        with context.session.begin(subtransactions=True):
            ns_db = self._get_resource(context, NS,
                                       ns_id)
            ns_db.update({'vnf_ids': vnf_ids})
            ns_db.update({'mgmt_urls': mgmt_urls})
            ns_db.update({'status': status})
            ns_db.update({'error_reason': error_reason})
            ns_db.update({'updated_at': timeutils.utcnow()})
            ns_dict = self._make_ns_dict(ns_db)
            self._cos_db_plg.create_event(
                context, res_id=ns_dict['id'],
                res_type=constants.RES_TYPE_NS,
                res_state=constants.RES_EVT_NA_STATE,
                evt_type=constants.RES_EVT_UPDATE,
                tstamp=ns_dict[constants.RES_EVT_UPDATED_FLD])
        return ns_dict

    # reference implementation. needs to be overrided by subclass
    def delete_ns(self, context, ns_id):
        with context.session.begin(subtransactions=True):
            ns_db = self._get_ns_db(
                context, ns_id, _ACTIVE_UPDATE_ERROR_DEAD,
                constants.PENDING_DELETE)
        deleted_ns_db = self._make_ns_dict(ns_db)
        self._cos_db_plg.create_event(
            context, res_id=ns_id,
            res_type=constants.RES_TYPE_NS,
            res_state=deleted_ns_db['status'],
            evt_type=constants.RES_EVT_DELETE,
            tstamp=timeutils.utcnow(), details="NS delete initiated")
        return deleted_ns_db

    def delete_ns_post(self, context, ns_id, mistral_obj,
                       error_reason, soft_delete=True):
        ns = self.get_ns(context, ns_id)
        nsd_id = ns.get('nsd_id')
        with context.session.begin(subtransactions=True):
            query = (
                self._model_query(context, NS).
                filter(NS.id == ns_id).
                filter(NS.status == constants.PENDING_DELETE))
            if mistral_obj and mistral_obj.state == 'ERROR':
                query.update({'status': constants.ERROR})
                self._cos_db_plg.create_event(
                    context, res_id=ns_id,
                    res_type=constants.RES_TYPE_NS,
                    res_state=constants.ERROR,
                    evt_type=constants.RES_EVT_DELETE,
                    tstamp=timeutils.utcnow(),
                    details="NS Delete ERROR")
            else:
                if soft_delete:
                    deleted_time_stamp = timeutils.utcnow()
                    query.update({'deleted_at': deleted_time_stamp})
                    self._cos_db_plg.create_event(
                        context, res_id=ns_id,
                        res_type=constants.RES_TYPE_NS,
                        res_state=constants.PENDING_DELETE,
                        evt_type=constants.RES_EVT_DELETE,
                        tstamp=deleted_time_stamp,
                        details="ns Delete Complete")
                else:
                    query.delete()
            template_db = self._get_resource(context, NSD, nsd_id)
            if template_db.get('template_source') == 'inline':
                self.delete_nsd(context, nsd_id)

    def get_ns(self, context, ns_id, fields=None):
        ns_db = self._get_resource(context, NS, ns_id)
        return self._make_ns_dict(ns_db)

    def get_nss(self, context, filters=None, fields=None):
        return self._get_collection(context, NS,
                                    self._make_ns_dict,
                                    filters=filters, fields=fields)
