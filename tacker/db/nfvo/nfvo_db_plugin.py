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
from oslo_utils import strutils
from oslo_utils import timeutils
from oslo_utils import uuidutils
from sqlalchemy.orm import exc as orm_exc
from sqlalchemy import sql

from tacker.common import exceptions
from tacker.db import db_base
from tacker.db.nfvo import nfvo_db
from tacker.db.vnfm import vnfm_db
from tacker.extensions import nfvo
from tacker import manager

VIM_ATTRIBUTES = ('id', 'type', 'tenant_id', 'name', 'description',
                  'placement_attr', 'shared', 'is_default',
                  'created_at', 'updated_at', 'extra')

VIM_AUTH_ATTRIBUTES = ('auth_url', 'vim_project', 'password', 'auth_cred')


class NfvoPluginDb(nfvo.NFVOPluginBase, db_base.CommonDbMixin):

    def __init__(self):
        super(NfvoPluginDb, self).__init__()

    @property
    def _core_plugin(self):
        return manager.TackerManager.get_plugin()

    def _make_vim_dict(self, vim_db, fields=None, mask_password=True):
        res = dict((key, vim_db[key]) for key in VIM_ATTRIBUTES)
        vim_auth_db = vim_db.vim_auth
        res['auth_url'] = vim_auth_db[0].auth_url
        res['vim_project'] = vim_auth_db[0].vim_project
        res['auth_cred'] = vim_auth_db[0].auth_cred
        # TODO(hiromu): Remove 'status' after removing status field from
        # tacker-pythonclient
        res['status'] = 'ACTIVE'
        if vim_auth_db[0].password:
            res['auth_cred']['password'] = vim_auth_db[0].password
        # NOTE(Yao Qibin): Since oidc_token_url contains keyword `token`,
        # its value will be masked.
        # To prevent its value from being masked, temporarily change its name.
        if "oidc_token_url" in res['auth_cred']:
            res['auth_cred']['oidc_x_url'] = res['auth_cred'].pop(
                'oidc_token_url')
        if mask_password:
            res['auth_cred'] = strutils.mask_dict_password(res['auth_cred'])
        # Revert to oidc_token_url
        if "oidc_x_url" in res['auth_cred']:
            res['auth_cred']['oidc_token_url'] = res['auth_cred'].pop(
                'oidc_x_url')
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
            if issubclass(model, nfvo_db.Vim):
                raise nfvo.VimNotFoundException(vim_id=id)
            else:
                raise

    def create_vim(self, context, vim):
        self._validate_default_vim(context, vim)
        vim_cred = vim['auth_cred']

        try:
            with context.session.begin(nested=True):
                vim_db = nfvo_db.Vim(
                    id=vim.get('id'),
                    type=vim.get('type'),
                    tenant_id=vim.get('tenant_id'),
                    name=vim.get('name'),
                    description=vim.get('description'),
                    placement_attr=vim.get('placement_attr'),
                    is_default=vim.get('is_default'),
                    extra=vim.get('extra'),
                    deleted_at=datetime.min)
                context.session.add(vim_db)
                vim_auth_db = nfvo_db.VimAuth(
                    id=uuidutils.generate_uuid(),
                    vim_id=vim.get('id'),
                    password=vim_cred.pop('password', None),
                    vim_project=vim.get('vim_project'),
                    auth_url=vim.get('auth_url'),
                    auth_cred=vim_cred)
                context.session.add(vim_auth_db)
                context.session.commit()
        except DBDuplicateEntry as e:
            raise exceptions.DuplicateEntity(
                _type="vim",
                entry=e.columns)
        vim_dict = self._make_vim_dict(vim_db)

        return vim_dict

    def delete_vim(self, context, vim_id, soft_delete=True):
        with context.session.begin(nested=True):
            vim_db = self._get_resource(context, nfvo_db.Vim, vim_id)
            if soft_delete:
                vim_db.update({'deleted_at': timeutils.utcnow()})
            else:
                context.session.query(nfvo_db.VimAuth).filter_by(
                    vim_id=vim_id).delete()
                context.session.delete(vim_db)
            context.session.commit()

    def is_vim_still_in_use(self, context, vim_id):
        with context.session.begin(nested=True):
            vnfs_db = self._model_query(context, vnfm_db.VNF).filter_by(
                vim_id=vim_id).first()
            if vnfs_db is not None:
                raise nfvo.VimInUseException(vim_id=vim_id)
        return vnfs_db

    def get_vim(self, context, vim_id, fields=None, mask_password=True):
        vim_db = self._get_resource(context, nfvo_db.Vim, vim_id)
        return self._make_vim_dict(vim_db, mask_password=mask_password)

    def get_vims(self, context, filters=None, fields=None):
        return self._get_collection(context, nfvo_db.Vim, self._make_vim_dict,
                                    filters=filters, fields=fields)

    def update_vim(self, context, vim_id, vim):
        self._validate_default_vim(context, vim, vim_id=vim_id)
        with context.session.begin(nested=True):
            vim_cred = vim['auth_cred']
            vim_project = vim['vim_project']
            vim_db = self._get_resource(context, nfvo_db.Vim, vim_id)
            try:
                if 'name' in vim:
                    vim_db.update({'name': vim.get('name')})
                if 'description' in vim:
                    vim_db.update({'description': vim.get('description')})
                if 'is_default' in vim:
                    vim_db.update({'is_default': vim.get('is_default')})
                if 'placement_attr' in vim:
                    vim_db.update(
                        {'placement_attr': vim.get('placement_attr')})
                if 'extra' in vim:
                    vim_db.update({'extra': vim.get('extra')})
                vim_auth_db = (self._model_query(
                    context, nfvo_db.VimAuth).filter(
                    nfvo_db.VimAuth.vim_id == vim_id).with_for_update().one())
            except orm_exc.NoResultFound:
                raise nfvo.VimNotFoundException(vim_id=vim_id)
            vim_auth_db.update({'auth_cred': vim_cred, 'password':
                                vim_cred.pop('password', None), 'vim_project':
                                vim_project})
            vim_db.update({'updated_at': timeutils.utcnow()})
            context.session.commit()

        return self.get_vim(context, vim_id)

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
        query = self._model_query(context, nfvo_db.Vim)
        return query.filter(
            nfvo_db.Vim.tenant_id == context.tenant_id).filter(
            nfvo_db.Vim.is_default == sql.true()).one()

    def get_default_vim(self, context):
        vim_db = self._get_default_vim(context)
        return self._make_vim_dict(vim_db, mask_password=False)
