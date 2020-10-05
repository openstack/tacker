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

from oslo_log import log as logging

from tacker.db import api as db_api
from tacker.db.db_sqlalchemy import api
from tacker.db.db_sqlalchemy import models
from tacker.db.vnfm import vnfm_db
from tacker.objects import base
from tacker.objects import fields

LOG = logging.getLogger(__name__)


@db_api.context_manager.writer
def _vnfd_create(context, values):
    vnfd = vnfm_db.VNFD()

    vnfd.update(values)
    vnfd.save(context.session)

    return vnfd


@db_api.context_manager.reader
def _get_vnfd_id(context, id):
    try:
        vnf_package_vnfd = \
            api.model_query(context, models.VnfPackageVnfd).\
            filter_by(package_uuid=id).first()
    except Exception:
        LOG.info("select vnf_package_vnfd failed")
    if vnf_package_vnfd:
        return vnf_package_vnfd.vnfd_id
    else:
        return None


@db_api.context_manager.reader
def _check_vnfd(context, id):
    try:
        vnfd = api.model_query(context, vnfm_db.VNFD).filter_by(id=id).first()
    except Exception:
        LOG.info("select vnfd failed")
    if vnfd:
        return "TRUE"
    else:
        return "FALSE"


@db_api.context_manager.writer
def _vnfd_delete(context, id):
    try:
        api.model_query(context, vnfm_db.VNFD).filter_by(id=id).delete()
    except Exception:
        LOG.info("delete vnfd failed")


@db_api.context_manager.writer
def _vnfd_destroy(context, id):
    now = timeutils.utcnow()
    updated_values = {'deleted_at': now}
    try:
        api.model_query(context, vnfm_db.VNFD).\
            filter_by(id=id).\
            update(updated_values, synchronize_session=False)
    except Exception:
        LOG.info("destroy vnfdfailed")


@base.TackerObjectRegistry.register
class Vnfd(base.TackerObject, base.TackerObjectDictCompat,
        base.TackerPersistentObject):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.UUIDField(nullable=False),
        'tenant_id': fields.UUIDField(nullable=False),
        'name': fields.StringField(nullable=False),
        'description': fields.StringField(nullable=True),
        'mgmt_driver': fields.StringField(nullable=True),
        'deleted_at': fields.DateTimeField(nullable=True),
    }

    @staticmethod
    def _from_db_object(context, vnfd, db_vnfd):

        for key in vnfd.fields:
            if db_vnfd.get(key):
                setattr(vnfd, key, db_vnfd[key])

        vnfd._context = context
        vnfd.obj_reset_changes()

        return vnfd

    @base.remotable
    def create(self):
        updates = self.obj_get_changes()
        db_vnfd = _vnfd_create(
            self._context, updates)
        self._from_db_object(self._context, self, db_vnfd)

    @classmethod
    def obj_from_db_obj(cls, context, db_obj):
        return cls._from_db_object(context, cls(), db_obj)

    @base.remotable
    def destroy(self, id):
        _vnfd_destroy(self._context, id)

    @base.remotable
    def delete(self, id):
        _vnfd_delete(self._context, id)

    @base.remotable
    def check_vnfd(self, id):
        return _check_vnfd(self._context, id)
