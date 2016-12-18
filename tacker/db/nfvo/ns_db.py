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

import uuid

from oslo_log import log as logging
from oslo_utils import timeutils

import sqlalchemy as sa
from sqlalchemy import orm

from tacker.db.common_services import common_services_db
from tacker.db import db_base
from tacker.db import model_base
from tacker.db import models_v1
from tacker.db import types
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

    # (key, value) pair to spin up
    attributes = orm.relationship('NSDAttribute',
                                  backref='nsd')


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


class NSPluginDb(network_service.NSPluginBase, db_base.CommonDbMixin):

    def __init__(self):
        super(NSPluginDb, self).__init__()
        self._cos_db_plg = common_services_db.CommonServicesPluginDb()

    def _make_attributes_dict(self, attributes_db):
        return dict((attr.key, attr.value) for attr in attributes_db)

    def _make_nsd_dict(self, nsd, fields=None):
        res = {
            'attributes': self._make_attributes_dict(nsd['attributes']),
        }
        key_list = ('id', 'tenant_id', 'name', 'description',
                    'created_at', 'updated_at', 'vnfds')
        res.update((key, nsd[key]) for key in key_list)
        return self._fields(res, fields)

    def create_nsd(self, context, nsd):
        vnfds = nsd['vnfds']
        nsd = nsd['nsd']
        LOG.debug(_('nsd %s'), nsd)
        tenant_id = self._get_tenant_id_for_create(context, nsd)

        with context.session.begin(subtransactions=True):
            nsd_id = str(uuid.uuid4())
            nsd_db = NSD(
                id=nsd_id,
                tenant_id=tenant_id,
                name=nsd.get('name'),
                vnfds=vnfds,
                description=nsd.get('description'))
            context.session.add(nsd_db)
            for (key, value) in nsd.get('attributes', {}).items():
                attribute_db = NSDAttribute(
                    id=str(uuid.uuid4()),
                    nsd_id=nsd_id,
                    key=key,
                    value=value)
                context.session.add(attribute_db)

        LOG.debug(_('nsd_db %(nsd_db)s %(attributes)s '),
                  {'nsd_db': nsd_db,
                   'attributes': nsd_db.attributes})
        nsd_dict = self._make_nsd_dict(nsd_db)
        LOG.debug(_('nsd_dict %s'), nsd_dict)
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
                raise network_service.NSDInUse(
                    nsd_id=nsd_id)

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
        return self._get_collection(context, NSD,
                                    self._make_nsd_dict,
                                    filters=filters, fields=fields)

    # reference implementation. needs to be overrided by subclass
    def create_ns(self, context, ns):
        return {'nsd': {}}

    # reference implementation. needs to be overrided by subclass
    def delete_ns(self, context, ns_id, soft_delete=True):
        pass

    def get_ns(self, context, ns_id, fields=None):
        pass

    def get_nss(self, context, filters=None, fields=None):
        pass
