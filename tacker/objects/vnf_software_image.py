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
from oslo_utils import uuidutils
from oslo_versionedobjects import base as ovoo_base
from sqlalchemy.orm import joinedload

from tacker.common import exceptions
from tacker.db import api as db_api
from tacker.db.db_sqlalchemy import api
from tacker.db.db_sqlalchemy import models
from tacker.objects import base
from tacker.objects import fields


VNF_SOFTWARE_IMAGE_OPTIONAL_ATTRS = ['metadata']

LOG = logging.getLogger(__name__)


def _metadata_add_to_db(context, id, metadata, max_retries=10):
    for attempt in range(max_retries):
        with db_api.context_manager.writer.using(context):

            new_entries = []
            for key, value in metadata.items():
                new_entries.append({"key": key,
                                    "value": value,
                                    "image_uuid": id})
            if new_entries:
                context.session.execute(
                    models.VnfSoftwareImageMetadata.__table__.insert(None),
                    new_entries)

            return metadata


@db_api.context_manager.writer
def _vnf_sw_image_create(context, values, metadata=None):
    vnf_sw_image = models.VnfSoftwareImage()

    vnf_sw_image.update(values)
    vnf_sw_image.save(context.session)
    vnf_sw_image._metadata = []

    if metadata:
        _metadata_add_to_db(context, vnf_sw_image.id, metadata)
        context.session.expire(vnf_sw_image, ['_metadata'])
        vnf_sw_image._metadata

    return vnf_sw_image


@db_api.context_manager.reader
def _vnf_sw_image_get_by_id(context, id):

    query = api.model_query(context, models.VnfSoftwareImage,
        read_deleted="no").filter_by(id=id).options(joinedload('_metadata'))

    result = query.first()

    if not result:
        raise exceptions.VnfSoftwareImageNotFound(id=id)

    return result


@base.TackerObjectRegistry.register
class VnfSoftwareImage(base.TackerObject, base.TackerPersistentObject):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.UUIDField(nullable=False),
        'software_image_id': fields.StringField(nullable=False),
        'flavour_uuid': fields.UUIDField(nullable=False),
        'name': fields.StringField(nullable=True),
        'provider': fields.StringField(nullable=True),
        'version': fields.StringField(nullable=True),
        'algorithm': fields.StringField(nullable=True),
        'hash': fields.StringField(nullable=True),
        'container_format': fields.StringField(nullable=True),
        'disk_format': fields.StringField(nullable=True),
        'min_disk': fields.IntegerField(),
        'min_ram': fields.IntegerField(default=0),
        'size': fields.IntegerField(),
        'image_path': fields.StringField(),
        'metadata': fields.DictOfStringsField(nullable=True)
    }

    @staticmethod
    def _from_db_object(context, vnf_sw_image, db_sw_image,
                        expected_attrs=None):

        vnf_sw_image._context = context
        for key in vnf_sw_image.fields:
            if key in VNF_SOFTWARE_IMAGE_OPTIONAL_ATTRS:
                continue
            else:
                db_key = key

            setattr(vnf_sw_image, key, db_sw_image[db_key])

        vnf_sw_image._extra_attributes_from_db_object(vnf_sw_image,
                          db_sw_image, expected_attrs)

        vnf_sw_image.obj_reset_changes()

        return vnf_sw_image

    @staticmethod
    def _extra_attributes_from_db_object(vnf_sw_image, db_sw_image,
                                         expected_attrs=None):
        """Method to help with migration of extra attributes to objects.

        """
        if expected_attrs is None:
            expected_attrs = []

        if 'metadata' in expected_attrs:
            setattr(vnf_sw_image, 'metadata', db_sw_image['metadetails'])

    def obj_load_attr(self, attrname):
        if not self._context:
            raise exceptions.OrphanedObjectError(method='obj_load_attr',
                                                objtype=self.obj_name())
        if 'id' not in self:
            raise exceptions.ObjectActionError(
                action='obj_load_attr',
                reason=_('attribute %s not lazy-loadable') % attrname)

        LOG.debug("Lazy-loading '%(attr)s' on %(name)s id %(id)s",
                  {'attr': attrname,
                   'name': self.obj_name(),
                   'id': self.id,
                   })

        self._obj_load_attr(attrname)

    def _obj_load_attr(self, attrname):
        """Internal method for loading attributes from vnf flavour."""

        if attrname in self.fields and attrname != 'id':
            self._load_generic(attrname)
        else:
            # NOTE(nirajsingh): Raise error if non existing field is
            # requested.
            raise exceptions.ObjectActionError(
                action='obj_load_attr',
                reason=_('attribute %s not lazy-loadable') % attrname)

        self.obj_reset_changes([attrname])

    def _load_generic(self, attrname):
        software_image = self.__class__.get_by_id(self._context,
                                              id=self.id,
                                              expected_attrs=attrname)
        if attrname not in software_image:
            raise exceptions.ObjectActionError(
                action='obj_load_attr',
                reason=_('loading %s requires recursion') % attrname)

        for field in self.fields:
            if field in software_image and field not in self:
                    setattr(self, field, getattr(software_image, field))

    @base.remotable
    def create(self):
        if self.obj_attr_is_set('id'):
            raise exceptions.ObjectActionError(action='create',
                                               reason=_('already created'))
        updates = self.obj_get_changes()

        if 'id' not in updates:
            updates['id'] = uuidutils.generate_uuid()
            self.id = updates['id']

        metadata = updates.pop('metadata', None)
        db_sw_image = _vnf_sw_image_create(self._context, updates,
                                           metadata=metadata)
        self._from_db_object(self._context, self, db_sw_image)

    @base.remotable_classmethod
    def get_by_id(cls, context, id, expected_attrs=None):
        db_sw_image = _vnf_sw_image_get_by_id(context, id)
        return cls._from_db_object(context, cls(), db_sw_image,
                                   expected_attrs=expected_attrs)


@base.TackerObjectRegistry.register
class VnfSoftwareImagesList(ovoo_base.ObjectListBase, base.TackerObject):

    VERSION = '1.0'

    fields = {
        'objects': fields.ListOfObjectsField('VnfSoftwareImage')
    }
