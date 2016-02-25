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

import sqlalchemy as sa
from sqlalchemy import orm
from sqlalchemy.orm import exc as orm_exc
from sqlalchemy import sql

from tacker.db import api as tdbapi
from tacker.db import db_base
from tacker.db import model_base
from tacker.db import models_v1
from tacker.db.vm import vm_db
from tacker.extensions import nfvo
from tacker import manager
from tacker.openstack.common.db import exception
from tacker.openstack.common import uuidutils


VIM_ATTRIBUTES = ('id', 'type', 'tenant_id', 'name', 'description',
                  'placement_attr', 'shared')
VIM_AUTH_ATTRIBUTES = ('auth_url', 'vim_project', 'password', 'auth_cred')


class Vim(model_base.BASE, models_v1.HasTenant):
    id = sa.Column(sa.String(255),
                   primary_key=True,
                   default=uuidutils.generate_uuid)
    type = sa.Column(sa.String(255), nullable=False)
    tenant_id = sa.Column(sa.String(255), nullable=True)
    name = sa.Column(sa.String(255), nullable=True)
    description = sa.Column(sa.String(255), nullable=True)
    placement_attr = sa.Column(sa.PickleType, nullable=True)
    shared = sa.Column(sa.Boolean, default=True, server_default=sql.true(
    ), nullable=False)
    vim_auth = orm.relationship('VimAuth')


class VimAuth(model_base.BASE, models_v1.HasId):
    vim_id = sa.Column(sa.String(255), sa.ForeignKey('vims.id'),
                       nullable=False)
    password = sa.Column(sa.String(128), nullable=False)
    auth_url = sa.Column(sa.String(255), nullable=False)
    vim_project = sa.Column(sa.PickleType, nullable=False)
    auth_cred = sa.Column(sa.PickleType, nullable=False)
    __table_args__ = (sa.UniqueConstraint('auth_url'), {})


class NfvoPluginDb(nfvo.NFVOPluginBase, db_base.CommonDbMixin):

    def __init__(self):
        tdbapi.register_models()
        super(NfvoPluginDb, self).__init__()

    @property
    def _core_plugin(self):
        return manager.TackerManager.get_plugin()

    def _make_vim_dict(self, vim_db, fields=None):
        res = dict((key, vim_db[key]) for key in VIM_ATTRIBUTES)
        vim_auth_db = vim_db.vim_auth
        res['auth_url'] = vim_auth_db[0].auth_url
        res['vim_project'] = vim_auth_db[0].vim_project
        res['auth_cred'] = vim_auth_db[0].auth_cred
        res['auth_cred']['password'] = vim_auth_db[0].password
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

    def create_vim(self, context, vim):
        vim_cred = vim['auth_cred']
        try:
            with context.session.begin(subtransactions=True):
                vim_db = Vim(
                    id=vim.get('id'),
                    type=vim.get('type'),
                    tenant_id=vim.get('tenant_id'),
                    name=vim.get('name'),
                    description=vim.get('description'),
                    placement_attr=vim.get('placement_attr'))
                context.session.add(vim_db)
                vim_auth_db = VimAuth(
                    id=str(uuid.uuid4()),
                    vim_id=vim.get('id'),
                    password=vim_cred.pop('password'),
                    vim_project=vim.get('vim_project'),
                    auth_url=vim.get('auth_url'),
                    auth_cred=vim_cred)
                context.session.add(vim_auth_db)
        except exception.DBDuplicateEntry:
                raise nfvo.VimDuplicateUrlException()
        return self._make_vim_dict(vim_db)

    def delete_vim(self, context, vim_id):
        with context.session.begin(subtransactions=True):
            vim_db = self._get_resource(context, Vim, vim_id)
            context.session.query(VimAuth).filter_by(
                vim_id=vim_id).delete()
            context.session.delete(vim_db)

    def is_vim_still_in_use(self, context, vim_id):
        with context.session.begin(subtransactions=True):
            devices_db = context.session.query(vm_db.Device).filter_by(
                vim_id=vim_id).first()
            if devices_db is not None:
                raise nfvo.VimInUseException(vim_id=vim_id)
        return devices_db

    def get_vim(self, context, vim_id, fields=None):
        vim_db = self._get_resource(context, Vim, vim_id)
        return self._make_vim_dict(vim_db)

    def get_vims(self, context, filters=None, fields=None):
        return self._get_collection(context, Vim, self._make_vim_dict,
                                    filters=filters, fields=fields)

    def update_vim(self, context, vim_id, vim):
        with context.session.begin(subtransactions=True):
            vim_cred = vim['auth_cred']
            vim_project = vim['vim_project']
            try:
                vim_auth_db = (self._model_query(context, VimAuth).filter(
                    VimAuth.vim_id == vim_id).with_lockmode('update').one())
            except orm_exc.NoResultFound:
                    raise nfvo.VimNotFound(vim_id=vim_id)
            vim_auth_db.update({'auth_cred': vim_cred, 'password':
                               vim_cred.pop('password'), 'vim_project':
                               vim_project})
        return self.get_vim(context, vim_id)

    def get_vim_by_name(self, context, vim_name, fields=None):
        vim_db = self._get_by_name(context, Vim, vim_name)
        return self._make_vim_dict(vim_db)

    def _get_by_name(self, context, model, name):
        try:
            query = self._model_query(context, model)
            return query.filter(model.name == name).one()
        except orm_exc.NoResultFound:
            if issubclass(model, Vim):
                raise
