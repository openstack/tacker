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
from oslo_utils import uuidutils
from oslo_versionedobjects import base as ovoo_base
from sqlalchemy.orm import joinedload

from tacker._i18n import _
from tacker.common import exceptions
from tacker.db import api as db_api
from tacker.db.db_sqlalchemy import api
from tacker.db.db_sqlalchemy import models
from tacker import objects
from tacker.objects import base
from tacker.objects import fields


LOG = logging.getLogger(__name__)


@db_api.context_manager.reader
def _vnf_instance_get_by_id(context, vnf_instance_id, columns_to_join=None):

    query = api.model_query(context, models.VnfInstance,
                            read_deleted="no", project_only=True). \
        filter_by(id=vnf_instance_id)

    if columns_to_join:
        for column in columns_to_join:
            query = query.options(joinedload(column))

    result = query.first()

    if not result:
        raise exceptions.VnfInstanceNotFound(id=vnf_instance_id)

    return result


@db_api.context_manager.writer
def _vnf_instance_create(context, values):
    vnf_instance = models.VnfInstance()
    vnf_instance.update(values)
    vnf_instance.save(context.session)

    return _vnf_instance_get_by_id(context, vnf_instance.id,
                                   columns_to_join=["instantiated_vnf_info"])


@db_api.context_manager.writer
def _vnf_instance_update(context, vnf_instance_id, values,
                         columns_to_join=None):

    vnf_instance = _vnf_instance_get_by_id(context, vnf_instance_id,
                                           columns_to_join=columns_to_join)
    vnf_instance.update(values)
    vnf_instance.save(session=context.session)

    return vnf_instance


@db_api.context_manager.writer
def _destroy_vnf_instance(context, uuid):
    now = timeutils.utcnow()
    updated_values = {'deleted': True,
                      'deleted_at': now
                      }
    api.model_query(context, models.VnfInstantiatedInfo). \
        filter_by(vnf_instance_id=uuid). \
        update(updated_values, synchronize_session=False)

    api.model_query(context, models.VnfInstance).\
        filter_by(id=uuid). \
        update(updated_values, synchronize_session=False)


@db_api.context_manager.reader
def _vnf_instance_list(context, columns_to_join=None):
    query = api.model_query(context, models.VnfInstance, read_deleted="no",
                            project_only=True)

    if columns_to_join:
        for column in columns_to_join:
            query = query.options(joinedload(column))

    return query.all()


def _make_vnf_instance_list(context, vnf_instance_list, db_vnf_instance_list,
                            expected_attrs):
    vnf_instance_cls = VnfInstance

    vnf_instance_list.objects = []
    for db_vnf_instance in db_vnf_instance_list:
        vnf_instance_obj = vnf_instance_cls._from_db_object(
            context, vnf_instance_cls(context), db_vnf_instance,
            expected_attrs=expected_attrs)
        vnf_instance_list.objects.append(vnf_instance_obj)

    vnf_instance_list.obj_reset_changes()
    return vnf_instance_list


@base.TackerObjectRegistry.register
class VnfInstance(base.TackerObject, base.TackerPersistentObject,
                  base.TackerObjectDictCompat):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.UUIDField(nullable=False),
        'vnf_instance_name': fields.StringField(nullable=True),
        'vnf_instance_description': fields.StringField(nullable=True),
        'instantiation_state': fields.VnfInstanceStateField(nullable=False,
            default=fields.VnfInstanceState.NOT_INSTANTIATED),
        'task_state': fields.StringField(nullable=True, default=None),
        'vnfd_id': fields.StringField(nullable=False),
        'vnf_provider': fields.StringField(nullable=False),
        'vnf_product_name': fields.StringField(nullable=False),
        'vnf_software_version': fields.StringField(nullable=False),
        'vnfd_version': fields.StringField(nullable=False),
        'vim_connection_info': fields.ListOfObjectsField(
            'VimConnectionInfo', nullable=True, default=[]),
        'tenant_id': fields.StringField(nullable=False),
        'instantiated_vnf_info': fields.ObjectField('InstantiatedVnfInfo',
                                                nullable=True, default=None)
    }

    def __init__(self, context=None, **kwargs):
        super(VnfInstance, self).__init__(context, **kwargs)
        self.obj_set_defaults()

    @staticmethod
    def _from_db_object(context, vnf_instance, db_vnf_instance,
                        expected_attrs=None):

        special_fields = ["instantiated_vnf_info", "vim_connection_info"]
        for key in vnf_instance.fields:
            if key in special_fields:
                continue

            setattr(vnf_instance, key, db_vnf_instance[key])

        VnfInstance._load_instantiated_vnf_info_from_db_object(context,
                                           vnf_instance, db_vnf_instance)

        vim_connection_info = db_vnf_instance['vim_connection_info']
        vim_connection_list = [objects.VimConnectionInfo.obj_from_primitive(
            vim_info, context) for vim_info in vim_connection_info]
        vnf_instance.vim_connection_info = vim_connection_list

        vnf_instance._context = context
        vnf_instance.obj_reset_changes()

        return vnf_instance

    @staticmethod
    def _load_instantiated_vnf_info_from_db_object(context, vnf_instance,
                                                   db_vnf_instance):
        if db_vnf_instance['instantiated_vnf_info']:
            inst_vnf_info = \
                objects.InstantiatedVnfInfo.obj_from_db_obj(context,
                        db_vnf_instance['instantiated_vnf_info'])
            vnf_instance.instantiated_vnf_info = inst_vnf_info

    @base.remotable
    def create(self):
        if self.obj_attr_is_set('id'):
            raise exceptions.ObjectActionError(action='create',
                                               reason=_('already created'))
        updates = self.obj_get_changes()

        if 'id' not in updates:
            updates['id'] = uuidutils.generate_uuid()
            self.id = updates['id']

        db_vnf_instance = _vnf_instance_create(self._context, updates)
        expected_attrs = ["instantiated_vnf_info"]
        self._from_db_object(self._context, self, db_vnf_instance,
                             expected_attrs=expected_attrs)

    @base.remotable
    def save(self):
        context = self._context

        updates = {}
        changes = self.obj_what_changed()

        for field in self.fields:
            if (self.obj_attr_is_set(field) and
                    isinstance(self.fields[field], fields.ObjectField)):
                try:
                    getattr(self, '_save_%s' % field)(context)
                except AttributeError:
                    LOG.exception('No save handler for %s', field)
            elif (self.obj_attr_is_set(field) and
                    isinstance(self.fields[field], fields.ListOfObjectsField)):
                field_list = getattr(self, field)
                updates[field] = [obj.obj_to_primitive() for obj in field_list]
            elif field in changes:
                updates[field] = self[field]

        expected_attrs = ["instantiated_vnf_info"]
        db_vnf_instance = _vnf_instance_update(self._context,
                                            self.id, updates,
                                            columns_to_join=expected_attrs)
        self._from_db_object(self._context, self, db_vnf_instance)

    def _save_instantiated_vnf_info(self, context):
        if self.instantiated_vnf_info:
            with self.instantiated_vnf_info.obj_alternate_context(context):
                self.instantiated_vnf_info.save()

    @base.remotable
    def destroy(self, context):
        if not self.obj_attr_is_set('id'):
            raise exceptions.ObjectActionError(action='destroy',
                                               reason='no uuid')

        _destroy_vnf_instance(context, self.id)

    def to_dict(self):
        data = {'id': self.id,
            'vnf_instance_name': self.vnf_instance_name,
            'vnf_instance_description': self.vnf_instance_description,
            'instantiation_state': self.instantiation_state,
            'vnfd_id': self.vnfd_id,
            'vnf_provider': self.vnf_provider,
            'vnf_product_name': self.vnf_product_name,
            'vnf_software_version': self.vnf_software_version,
            'vnfd_version': self.vnfd_version}

        if (self.instantiation_state == fields.VnfInstanceState.INSTANTIATED
                and self.instantiated_vnf_info):
            data.update({'instantiated_vnf_info':
                self.instantiated_vnf_info.to_dict()})

            vim_connection_info_list = []
            for vim_connection_info in self.vim_connection_info:
                vim_connection_info_list.append(vim_connection_info.to_dict())
            data.update({'vim_connection_info': vim_connection_info_list})

        return data

    @base.remotable_classmethod
    def get_by_id(cls, context, id):
        expected_attrs = ["instantiated_vnf_info"]
        db_vnf_instance = _vnf_instance_get_by_id(
            context, id, columns_to_join=expected_attrs)
        return cls._from_db_object(context, cls(), db_vnf_instance,
                                   expected_attrs=expected_attrs)


@base.TackerObjectRegistry.register
class VnfInstanceList(ovoo_base.ObjectListBase, base.TackerObject):

    VERSION = '1.0'

    fields = {
        'objects': fields.ListOfObjectsField('VnfInstance')
    }

    @base.remotable_classmethod
    def get_all(cls, context, expected_attrs=None):
        expected_attrs = ["instantiated_vnf_info"]
        db_vnf_instances = _vnf_instance_list(context,
                                              columns_to_join=expected_attrs)
        return _make_vnf_instance_list(context, cls(), db_vnf_instances,
                                       expected_attrs)
