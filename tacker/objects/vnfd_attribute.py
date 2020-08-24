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

from oslo_log import log as logging

from tacker.db import api as db_api
from tacker.db.db_sqlalchemy import api
from tacker.db.db_sqlalchemy import models
from tacker.db.vnfm import vnfm_db
from tacker.objects import base
from tacker.objects import fields

LOG = logging.getLogger(__name__)


@db_api.context_manager.writer
def _vnfd_attribute_create(context, values):
    vnfd_attribute = vnfm_db.VNFDAttribute()

    vnfd_attribute.update(values)
    vnfd_attribute.save(context.session)

    return vnfd_attribute


@db_api.context_manager.reader
def _get_vnfd_id(context, id):
    try:
        vnf_package_vnfd = \
            api.model_query(context, models.VnfPackageVnfd).\
            filter_by(package_uuid=id).first()
    except Exception:
        LOG.info("select vnfd_attribute failed")
    if vnf_package_vnfd:
        return vnf_package_vnfd.vnfd_id
    else:
        return None


@db_api.context_manager.reader
def _check_vnfd_attribute(context, id):
    try:
        vnfd_attribute = \
            api.model_query(context, vnfm_db.VNFDAttribute).\
            filter_by(vnfd_id=id).first()
    except Exception:
        LOG.info("select vnfd_attribute failed")
    if vnfd_attribute:
        return "TRUE"
    else:
        return "FALSE"


@db_api.context_manager.writer
def _vnfd_attribute_delete(context, id):
    try:
        api.model_query(context, vnfm_db.VNFDAttribute).\
            filter_by(vnfd_id=id).delete()
    except Exception:
        LOG.info("delete vnfd_attribute failed")


@base.TackerObjectRegistry.register
class VnfdAttribute(base.TackerObject, base.TackerObjectDictCompat,
        base.TackerPersistentObject):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.UUIDField(nullable=False),
        'vnfd_id': fields.UUIDField(nullable=False),
        'key': fields.StringField(nullable=True),
        'value': fields.StringField(nullable=True),
    }

    @staticmethod
    def _from_db_object(context, vnfd_attribute, db_vnfd_attribute):

        for key in vnfd_attribute.fields:

            if db_vnfd_attribute.get(key):
                setattr(vnfd_attribute, key, db_vnfd_attribute[key])

        vnfd_attribute._context = context
        vnfd_attribute.obj_reset_changes()

        return vnfd_attribute

    @base.remotable
    def create(self):
        updates = self.obj_get_changes()
        db_vnfd_attribute = _vnfd_attribute_create(
            self._context, updates)
        self._from_db_object(self._context, self, db_vnfd_attribute)

    @classmethod
    def obj_from_db_obj(cls, context, db_obj):
        return cls._from_db_object(context, cls(), db_obj)

    @base.remotable
    def destroy(self, id):
        vnfd_attribute_id = _get_vnfd_id(self._context, id)
        if vnfd_attribute_id:
            _vnfd_attribute_delete(self._context, vnfd_attribute_id)

    @base.remotable
    def delete(self, id):
        _vnfd_attribute_delete(self._context, id)

    @base.remotable
    def check_vnfd_attribute(self, id):
        return _check_vnfd_attribute(self._context, id)
