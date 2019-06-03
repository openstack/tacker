#    Copyright 2019 NTT DATA.
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

from oslo_utils import uuidutils

from tacker.common import exceptions
from tacker.db import api as db_api
from tacker.db.db_sqlalchemy import models
from tacker.objects import base
from tacker.objects import fields


@db_api.context_manager.writer
def _vnf_package_vnfd_create(context, values):
    vnf_package_vnfd = models.VnfPackageVnfd()

    vnf_package_vnfd.update(values)
    vnf_package_vnfd.save(context.session)

    return vnf_package_vnfd


@base.TackerObjectRegistry.register
class VnfPackageVnfd(base.TackerObject, base.TackerObjectDictCompat,
                     base.TackerPersistentObject):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.UUIDField(nullable=False),
        'package_uuid': fields.UUIDField(nullable=False),
        'vnfd_id': fields.UUIDField(nullable=False),
        'vnf_provider': fields.StringField(nullable=False),
        'vnf_product_name': fields.StringField(nullable=False),
        'vnf_software_version': fields.StringField(nullable=False),
        'vnfd_version': fields.StringField(nullable=False),
    }

    @staticmethod
    def _from_db_object(context, vnf_package_vnfd, db_vnf_package_vnfd):

        for key in vnf_package_vnfd.fields:
            if db_vnf_package_vnfd[key]:
                setattr(vnf_package_vnfd, key, db_vnf_package_vnfd[key])

        vnf_package_vnfd._context = context
        vnf_package_vnfd.obj_reset_changes()

        return vnf_package_vnfd

    @base.remotable
    def create(self):
        if self.obj_attr_is_set('id'):
            raise exceptions.ObjectActionError(action='create',
                                               reason=_('already created'))
        updates = self.obj_get_changes()

        if 'id' not in updates:
            updates['id'] = uuidutils.generate_uuid()
            self.id = updates['id']

        updates = self.obj_get_changes()
        db_vnf_package_vnfd = _vnf_package_vnfd_create(
            self._context, updates)
        self._from_db_object(self._context, self, db_vnf_package_vnfd)

    @classmethod
    def obj_from_db_obj(cls, context, db_obj):
        return cls._from_db_object(context, cls(), db_obj)
