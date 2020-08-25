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

from oslo_db import exception as db_exc
from oslo_log import log as logging
from oslo_utils import uuidutils

from tacker.common import exceptions
import tacker.context
from tacker.db import api as db_api
from tacker.db.db_sqlalchemy import api
from tacker.db.db_sqlalchemy import models
from tacker.objects import base
from tacker.objects import fields

LOG = logging.getLogger(__name__)


@db_api.context_manager.writer
def _vnf_package_vnfd_create(context, values):
    vnf_package_vnfd = models.VnfPackageVnfd()

    vnf_package_vnfd.update(values)
    try:
        vnf_package_vnfd.save(context.session)
    except db_exc.DBDuplicateEntry as e:
        if 'vnfd_id' in e.columns:
            raise exceptions.VnfPackageVnfdIdDuplicate(
                vnfd_id=values.get('vnfd_id'))

    return vnf_package_vnfd


@db_api.context_manager.reader
def _get_vnf_package_vnfd(context, id, package_uuid=None, del_flg=None):
    if package_uuid and not del_flg:
        query = api.model_query(
            context,
            models.VnfPackageVnfd).filter_by(
            package_uuid=id).filter_by(
            deleted=0)
    elif package_uuid and del_flg:
        query = api.model_query(
            context, models.VnfPackageVnfd).filter_by(
            package_uuid=id)
    else:
        query = api.model_query(
            context,
            models.VnfPackageVnfd).filter_by(
            vnfd_id=id).filter_by(
            deleted=0)
    try:
        result = query.all()
        result_line = ""
        for line in result:
            result_line = line

    except Exception:
        LOG.error("select vnf_package_vnfd failed")

    if result_line:
        return result_line
    else:
        return None


@db_api.context_manager.writer
def _vnf_package_vnfd_delete(context, id):
    try:
        api.model_query(
            context, models.VnfPackageVnfd).filter_by(
            package_uuid=id).delete()
    except Exception:
        LOG.error("delete vnf_package_vnfd failed")


@db_api.context_manager.reader
def _vnf_package_vnfd_get_by_id(context, vnfd_id):

    query = api.model_query(context, models.VnfPackageVnfd,
                            read_deleted="no", project_only=False). \
        filter_by(vnfd_id=vnfd_id).\
        join((models.VnfPackage, models.VnfPackage.id ==
              models.VnfPackageVnfd.package_uuid))

    if tacker.context.is_user_context(context):
        query = query.filter(models.VnfPackage.tenant_id == context.project_id)

    result = query.first()

    if not result:
        raise exceptions.VnfPackageVnfdNotFound(id=vnfd_id)

    return result


def _vnf_package_vnfd_get_by_packageId(context, packageId):

    query = api.model_query(
        context,
        models.VnfPackageVnfd,
        read_deleted="no",
        project_only=True).filter_by(
        package_uuid=packageId)

    result = query.first()

    if not result:
        return None

    return result


@db_api.context_manager.reader
def _vnf_package_vnfd_get_by_vnfdId(context, vnfdId):
    query = api.model_query(context,
                            models.VnfPackageVnfd,
                            read_deleted="no",
                            project_only=True).filter_by(vnfd_id=vnfdId)

    result = query.first()

    if not result:
        return None

    return result


@db_api.context_manager.reader
def _get_vnf_package_vnfd_by_vnfid(context, vnfpkgid):

    sql = ("select"
           " t1.vnfd_id,"
           " t1.vnf_provider,"
           " t1.vnf_product_name,"
           " t1.vnf_software_version,"
           " t1.vnfd_version,"
           " t2.name"
           " from "
           " vnf_package_vnfd t1,"
           " vnf t2 "
           " where"
           " t1.vnfd_id=t2.vnfd_id"
           " and"
           " t2.id= :vnfpkgid")

    result = context.session.execute(sql, {'vnfpkgid': vnfpkgid})
    for line in result:
        return line


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

    @base.remotable
    def get_vnf_package_vnfd(self, id, package_uuid=None, del_flg=None):
        return _get_vnf_package_vnfd(self._context, id, package_uuid, del_flg)

    @base.remotable_classmethod
    def get_vnf_package_vnfd_by_vnfid(self, context, vnfid):
        return _get_vnf_package_vnfd_by_vnfid(context, vnfid)

    @base.remotable
    def delete(self, id):
        _vnf_package_vnfd_delete(self._context, id)

    @classmethod
    def obj_from_db_obj(cls, context, db_obj):
        return cls._from_db_object(context, cls(), db_obj)

    @base.remotable_classmethod
    def get_by_id(cls, context, id):
        db_vnf_package_vnfd = _vnf_package_vnfd_get_by_id(context, id)
        return cls._from_db_object(context, cls(), db_vnf_package_vnfd)

    @base.remotable_classmethod
    def get_by_vnfdId(cls, context, id):
        db_vnf_package_vnfd = _vnf_package_vnfd_get_by_vnfdId(
            context, id)
        if not db_vnf_package_vnfd:
            return db_vnf_package_vnfd
        return cls._from_db_object(context, cls(), db_vnf_package_vnfd)

    @base.remotable_classmethod
    def get_by_packageId(cls, context, id):
        db_vnf_package_vnfd = _vnf_package_vnfd_get_by_packageId(
            context, id)
        if not db_vnf_package_vnfd:
            return db_vnf_package_vnfd
        return cls._from_db_object(context, cls(), db_vnf_package_vnfd)
