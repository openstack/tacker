# Copyright 2016 Brocade Communications System, Inc.
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

from oslo_utils import strutils
from oslo_utils import timeutils
import sqlalchemy as sa
from sqlalchemy import orm
from sqlalchemy.orm import exc as orm_exc
from sqlalchemy import sql

from tacker.db.common_services import common_services_db
from tacker.db import db_base
from tacker.db import model_base
from tacker.db import models_v1
from tacker.db import types
from tacker.db.vnfm import vnfm_db
from tacker.extensions import nfvo
from tacker import manager
from tacker.plugins.common import constants


VIM_ATTRIBUTES = ('id', 'type', 'tenant_id', 'name', 'description',
                  'placement_attr', 'shared', 'is_default',
                  'created_at', 'updated_at', 'status')

VIM_AUTH_ATTRIBUTES = ('auth_url', 'vim_project', 'password', 'auth_cred')


class Vim(model_base.BASE,
          models_v1.HasId,
          models_v1.HasTenant,
          models_v1.Audit):
    type = sa.Column(sa.String(64), nullable=False)
    name = sa.Column(sa.String(255), nullable=False)
    description = sa.Column(sa.Text, nullable=True)
    placement_attr = sa.Column(types.Json, nullable=True)
    shared = sa.Column(sa.Boolean, default=True, server_default=sql.true(
    ), nullable=False)
    is_default = sa.Column(sa.Boolean, default=False, server_default=sql.false(
    ), nullable=False)
    vim_auth = orm.relationship('VimAuth')
    status = sa.Column(sa.String(255), nullable=False)


class VimAuth(model_base.BASE, models_v1.HasId):
    vim_id = sa.Column(types.Uuid, sa.ForeignKey('vims.id'),
                       nullable=False)
    password = sa.Column(sa.String(255), nullable=False)
    auth_url = sa.Column(sa.String(255), nullable=False)
    vim_project = sa.Column(types.Json, nullable=False)
    auth_cred = sa.Column(types.Json, nullable=False)


class NfvoPluginDb(nfvo.NFVOPluginBase, db_base.CommonDbMixin):

    def __init__(self):
        super(NfvoPluginDb, self).__init__()
        self._cos_db_plg = common_services_db.CommonServicesPluginDb()

    @property
    def _core_plugin(self):
        return manager.TackerManager.get_plugin()

    def _make_vim_dict(self, vim_db, fields=None, mask_password=True):
        res = dict((key, vim_db[key]) for key in VIM_ATTRIBUTES)
        vim_auth_db = vim_db.vim_auth
        res['auth_url'] = vim_auth_db[0].auth_url
        res['vim_project'] = vim_auth_db[0].vim_project
        res['auth_cred'] = vim_auth_db[0].auth_cred
        res['auth_cred']['password'] = vim_auth_db[0].password
        if mask_password:
            res['auth_cred'] = strutils.mask_dict_password(res['auth_cred'])
        return self._fields(res, fields)

    def _fields(self, resource, fields):
        if fields:
            return dict(((key, item) for key, item in resource.items()
                         if key in fields))
        return resource

    def _get_resource(self, context, model, id):
        try:
            return self._get_by_id(context, model, id)
        except orm_exc.NoResultFound:
            if issubclass(model, Vim):
                raise nfvo.VimNotFoundException(vim_id=id)
            else:
                raise

    def _does_already_exist(self, context, vim):
        try:
            query = self._model_query(context, VimAuth)
            for v_auth in query.filter(VimAuth.auth_url == vim.get('auth_url')
                                       ).all():
                vim = self._get_by_id(context, Vim, v_auth.get('vim_id'))
                if vim.get('deleted_at') is None:
                    return True
        except orm_exc.NoResultFound:
            pass

        return False

    def create_vim(self, context, vim):
        self._validate_default_vim(context, vim)
        vim_cred = vim['auth_cred']
        if not self._does_already_exist(context, vim):
            with context.session.begin(subtransactions=True):
                vim_db = Vim(
                    id=vim.get('id'),
                    type=vim.get('type'),
                    tenant_id=vim.get('tenant_id'),
                    name=vim.get('name'),
                    description=vim.get('description'),
                    placement_attr=vim.get('placement_attr'),
                    is_default=vim.get('is_default'),
                    status=vim.get('status'))
                context.session.add(vim_db)
                vim_auth_db = VimAuth(
                    id=str(uuid.uuid4()),
                    vim_id=vim.get('id'),
                    password=vim_cred.pop('password'),
                    vim_project=vim.get('vim_project'),
                    auth_url=vim.get('auth_url'),
                    auth_cred=vim_cred)
                context.session.add(vim_auth_db)
        else:
                raise nfvo.VimDuplicateUrlException()
        vim_dict = self._make_vim_dict(vim_db)
        self._cos_db_plg.create_event(
            context, res_id=vim_dict['id'],
            res_type=constants.RES_TYPE_VIM,
            res_state=vim_dict['status'],
            evt_type=constants.RES_EVT_CREATE,
            tstamp=vim_dict['created_at'])
        return vim_dict

    def delete_vim(self, context, vim_id, soft_delete=True):
        with context.session.begin(subtransactions=True):
            vim_db = self._get_resource(context, Vim, vim_id)
            if soft_delete:
                vim_db.update({'deleted_at': timeutils.utcnow()})
                self._cos_db_plg.create_event(
                    context, res_id=vim_db['id'],
                    res_type=constants.RES_TYPE_VIM,
                    res_state=vim_db['status'],
                    evt_type=constants.RES_EVT_DELETE,
                    tstamp=vim_db[constants.RES_EVT_DELETED_FLD])
            else:
                context.session.query(VimAuth).filter_by(
                    vim_id=vim_id).delete()
                context.session.delete(vim_db)

    def is_vim_still_in_use(self, context, vim_id):
        with context.session.begin(subtransactions=True):
            vnfs_db = self._model_query(context, vnfm_db.VNF).filter_by(
                vim_id=vim_id).first()
            if vnfs_db is not None:
                raise nfvo.VimInUseException(vim_id=vim_id)
        return vnfs_db

    def get_vim(self, context, vim_id, fields=None, mask_password=True):
        vim_db = self._get_resource(context, Vim, vim_id)
        return self._make_vim_dict(vim_db, mask_password=mask_password)

    def get_vims(self, context, filters=None, fields=None):
        return self._get_collection(context, Vim, self._make_vim_dict,
                                    filters=filters, fields=fields)

    def update_vim(self, context, vim_id, vim):
        self._validate_default_vim(context, vim, vim_id=vim_id)
        with context.session.begin(subtransactions=True):
            vim_cred = vim['auth_cred']
            vim_project = vim['vim_project']
            is_default = vim.get('is_default')
            vim_db = self._get_resource(context, Vim, vim_id)
            try:
                if is_default:
                    vim_db.update({'is_default': is_default})
                vim_auth_db = (self._model_query(context, VimAuth).filter(
                    VimAuth.vim_id == vim_id).with_lockmode('update').one())
            except orm_exc.NoResultFound:
                    raise nfvo.VimNotFoundException(vim_id=vim_id)
            vim_auth_db.update({'auth_cred': vim_cred, 'password':
                               vim_cred.pop('password'), 'vim_project':
                               vim_project})
            vim_db.update({'updated_at': timeutils.utcnow()})
            self._cos_db_plg.create_event(
                context, res_id=vim_db['id'],
                res_type=constants.RES_TYPE_VIM,
                res_state=vim_db['status'],
                evt_type=constants.RES_EVT_UPDATE,
                tstamp=vim_db[constants.RES_EVT_UPDATED_FLD])

        return self.get_vim(context, vim_id)

    def update_vim_status(self, context, vim_id, status):
        with context.session.begin(subtransactions=True):
            try:
                vim_db = (self._model_query(context, Vim).filter(
                    Vim.id == vim_id).with_lockmode('update').one())
            except orm_exc.NoResultFound:
                    raise nfvo.VimNotFoundException(vim_id=vim_id)
            vim_db.update({'status': status,
                           'updated_at': timeutils.utcnow()})
        return self._make_vim_dict(vim_db)

    def _validate_default_vim(self, context, vim, vim_id=None):
        if not vim.get('is_default'):
            return True
        try:
            vim_db = self._get_default_vim(context)
        except orm_exc.NoResultFound:
            return True
        if vim_id == vim_db.id:
            return True
        raise nfvo.VimDefaultDuplicateException(vim_id=vim_db.id)

    def _get_default_vim(self, context):
        query = self._model_query(context, Vim)
        return query.filter(Vim.is_default == sql.true()).one()

    def get_default_vim(self, context):
        vim_db = self._get_default_vim(context)
        return self._make_vim_dict(vim_db, mask_password=False)
