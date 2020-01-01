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

from oslo_utils import timeutils
from oslo_utils import uuidutils
from oslo_versionedobjects import base as ovoo_base

from tacker._i18n import _
from tacker.common import exceptions
from tacker.db import api as db_api
from tacker.db.db_sqlalchemy import api
from tacker.db.db_sqlalchemy import models
from tacker.objects import base
from tacker.objects import fields


@db_api.context_manager.writer
def _vnf_resource_create(context, values):
    vnf_resource = models.VnfResource()
    vnf_resource.update(values)
    vnf_resource.save(context.session)

    return vnf_resource


@db_api.context_manager.reader
def _vnf_resource_get_by_id(context, id):

    query = api.model_query(context, models.VnfResource,
                            read_deleted="no", project_only=True). \
        filter_by(id=id)

    result = query.first()

    if not result:
        raise exceptions.VnfResourceNotFound(id=id)

    return result


@db_api.context_manager.writer
def _vnf_resource_update(context, id, values):

    vnf_resource = _vnf_resource_get_by_id(context, id)
    vnf_resource.update(values)
    vnf_resource.save(session=context.session)

    return vnf_resource


@db_api.context_manager.writer
def _destroy_vnf_resource(context, id):
    now = timeutils.utcnow()
    updated_values = {'deleted': True,
                      'deleted_at': now
                      }

    api.model_query(context, models.VnfResource).\
        filter_by(id=id). \
        update(updated_values, synchronize_session=False)


@db_api.context_manager.reader
def _vnf_resource_list(context, vnf_instance_id):
    query = api.model_query(context, models.VnfResource, read_deleted="no",
                            project_only=True).\
        filter_by(vnf_instance_id=vnf_instance_id)

    return query.all()


def _make_vnf_resources_list(context, vnf_resource_list, db_vnf_resource_list):
    vnf_resource_cls = VnfResource

    vnf_resource_list.objects = []
    for db_vnf_resource in db_vnf_resource_list:
        vnf_resource_obj = vnf_resource_cls._from_db_object(
            context, vnf_resource_cls(context), db_vnf_resource)
        vnf_resource_list.objects.append(vnf_resource_obj)

    vnf_resource_list.obj_reset_changes()
    return vnf_resource_list


@base.TackerObjectRegistry.register
class VnfResource(base.TackerObject, base.TackerPersistentObject):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.UUIDField(nullable=False),
        'vnf_instance_id': fields.StringField(nullable=False),
        'resource_name': fields.StringField(nullable=True),
        'resource_type': fields.StringField(nullable=False),
        'resource_identifier': fields.StringField(nullable=False),
        'resource_status': fields.StringField(nullable=True, default='status')
    }

    def __init__(self, context=None, **kwargs):
        super(VnfResource, self).__init__(context, **kwargs)
        self.obj_set_defaults()

    @staticmethod
    def _from_db_object(context, vnf_resource, db_vnf_resource):

        for key in vnf_resource.fields:
            if db_vnf_resource[key]:
                setattr(vnf_resource, key, db_vnf_resource[key])

        vnf_resource._context = context
        vnf_resource.obj_reset_changes()

        return vnf_resource

    @base.remotable
    def create(self):
        if self.obj_attr_is_set('id'):
            raise exceptions.ObjectActionError(action='create',
                                               reason=_('already created'))
        updates = self.obj_get_changes()

        if 'id' not in updates:
            updates['id'] = uuidutils.generate_uuid()
            self.id = updates['id']

        db_vnf_resource = _vnf_resource_create(self._context, updates)
        self._from_db_object(self._context, self, db_vnf_resource)

    @base.remotable
    def save(self):
        updates = self.tacker_obj_get_changes()

        db_vnf_resource = _vnf_resource_update(self._context,
                                            self.id, updates)
        self._from_db_object(self._context, self, db_vnf_resource)

    @base.remotable
    def destroy(self, context):
        if not self.obj_attr_is_set('id'):
            raise exceptions.ObjectActionError(action='destroy',
                                               reason='no uuid')

        _destroy_vnf_resource(context, self.id)

    @base.remotable_classmethod
    def get_by_id(cls, context, id):
        db_vnf_package = _vnf_resource_get_by_id(context, id)
        return cls._from_db_object(context, cls(), db_vnf_package)


@base.TackerObjectRegistry.register
class VnfResourceList(ovoo_base.ObjectListBase, base.TackerObject):

    VERSION = '1.0'

    fields = {
        'objects': fields.ListOfObjectsField('VnfResource')
    }

    @base.remotable_classmethod
    def get_by_vnf_instance_id(cls, context, vnf_instance_id):
        db_vnf_resources = _vnf_resource_list(context, vnf_instance_id)
        return _make_vnf_resources_list(context, cls(), db_vnf_resources)
