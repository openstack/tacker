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
from oslo_serialization import jsonutils
from oslo_utils import timeutils
from oslo_utils import uuidutils
from oslo_versionedobjects import base as ovoo_base
from sqlalchemy.orm import joinedload

from tacker.common import exceptions
from tacker.db import api as db_api
from tacker.db.db_sqlalchemy import api
from tacker.db.db_sqlalchemy import models
from tacker import objects
from tacker.objects import base
from tacker.objects import fields


_NO_DATA_SENTINEL = object()

VNF_DEPLOYMENT_FLAVOUR_OPTIONAL_ATTRS = ['software_images']

LOG = logging.getLogger(__name__)


@db_api.context_manager.writer
def _vnf_deployment_flavour_create(context, values):
    vnf_deployment_flavour = models.VnfDeploymentFlavour()

    vnf_deployment_flavour.update(values)
    vnf_deployment_flavour.save(context.session)

    return vnf_deployment_flavour


@db_api.context_manager.reader
def _vnf_deployment_flavour_get_by_id(context, id, columns_to_join=None):

    query = api.model_query(context, models.VnfDeploymentFlavour,
                            read_deleted="no").filter_by(id=id)

    if columns_to_join:
        for column in columns_to_join:
            query = query.options(joinedload(column))

    result = query.first()

    if not result:
        raise exceptions.VnfDeploymentFlavourNotFound(id=id)

    return result


@db_api.context_manager.writer
def _destroy_vnf_deployment_flavour(context, flavour_uuid):
    now = timeutils.utcnow()
    updated_values = {'deleted': True,
                      'deleted_at': now
                      }

    software_images_query = api.model_query(
        context, models.VnfSoftwareImage,
        (models.VnfSoftwareImage.id,)).filter_by(flavour_uuid=flavour_uuid)

    api.model_query(context, models.VnfSoftwareImageMetadata). \
        filter(models.VnfSoftwareImageMetadata.image_uuid.
        in_(software_images_query.subquery())).update(
        updated_values, synchronize_session=False)

    api.model_query(context, models.VnfSoftwareImage). \
        filter_by(flavour_uuid=flavour_uuid). \
        update(updated_values, synchronize_session=False)
    api.model_query(context, models.VnfDeploymentFlavour). \
        filter_by(id=flavour_uuid). \
        update(updated_values, synchronize_session=False)


@base.TackerObjectRegistry.register
class VnfDeploymentFlavour(base.TackerObject, base.TackerPersistentObject):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.UUIDField(nullable=False),
        'package_uuid': fields.UUIDField(nullable=False),
        'flavour_id': fields.StringField(nullable=False),
        'flavour_description': fields.StringField(nullable=False),
        'instantiation_levels': fields.DictOfNullableField(nullable=True),
        'software_images': fields.ObjectField('VnfSoftwareImagesList'),
    }

    @staticmethod
    def _from_db_object(context, flavour, db_flavour, expected_attrs=None):
        flavour._context = context

        special_cases = set(['instantiation_levels'])
        fields = set(flavour.fields) - special_cases

        for key in fields:
            if key in VNF_DEPLOYMENT_FLAVOUR_OPTIONAL_ATTRS:
                continue
            if db_flavour[key]:
                setattr(flavour, key, db_flavour[key])

        inst_levels = db_flavour['instantiation_levels']
        if inst_levels:
            flavour.instantiation_levels = jsonutils.loads(inst_levels)

        flavour._extra_attributes_from_db_object(flavour, db_flavour,
                                                expected_attrs)

        flavour.obj_reset_changes()

        return flavour

    @staticmethod
    def _extra_attributes_from_db_object(flavour, db_flavour,
                                         expected_attrs=None):
        """Method to help with migration of extra attributes to objects.

        """
        if expected_attrs is None:
            expected_attrs = []

        if 'software_images' in expected_attrs:
            flavour._load_sw_images(db_flavour.get('software_images'))

    @base.remotable
    def create(self):
        if self.obj_attr_is_set('id'):
            raise exceptions.ObjectActionError(action='create',
                                               reason='already created')
        updates = self.obj_get_changes()

        if 'id' not in updates:
            updates['id'] = uuidutils.generate_uuid()
            self.id = updates['id']

        if 'software_images' in updates:
            updates.pop('software_images')

        special_key = 'instantiation_levels'
        if special_key in updates:
            updates[special_key] = jsonutils.dumps(updates.get(special_key))

        db_flavour = _vnf_deployment_flavour_create(self._context, updates)
        self._from_db_object(self._context, self, db_flavour)

    @base.remotable_classmethod
    def get_by_id(cls, context, id, expected_attrs=None):
        db_flavour = _vnf_deployment_flavour_get_by_id(
            context, id, columns_to_join=expected_attrs)
        return cls._from_db_object(context, cls(), db_flavour,
                                   expected_attrs=expected_attrs)

    @base.remotable
    def destroy(self, context):
        if not self.obj_attr_is_set('id'):
            raise exceptions.ObjectActionError(
                action='destroy', reason='no uuid')

        _destroy_vnf_deployment_flavour(context, self.id)

    def obj_load_attr(self, attrname):
        if not self._context:
            raise exceptions.OrphanedObjectError(
                method='obj_load_attr', objtype=self.obj_name())
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
        """Internal method for loading attributes from vnf deployment flavour.

        """

        if attrname == 'software_images':
            self._load_sw_images()
        elif attrname in self.fields and attrname != 'id':
            self._load_generic(attrname)
        else:
            # NOTE(nirajsingh): Raise error if non existing field is
            # requested.
            raise exceptions.ObjectActionError(
                action='obj_load_attr',
                reason=_('attribute %s not lazy-loadable') % attrname)

        self.obj_reset_changes([attrname])

    def _load_generic(self, attrname):
        vnf_deployment_flavour = self.__class__.get_by_id(
            self._context, id=self.id, expected_attrs=None)
        if attrname not in vnf_deployment_flavour:
            raise exceptions.ObjectActionError(
                action='obj_load_attr',
                reason=_('loading %s requires recursion') % attrname)

        for field in self.fields:
            if field in vnf_deployment_flavour and field not in self:
                setattr(self, field, getattr(vnf_deployment_flavour, field))

    def _load_sw_images(self, db_sw_images=_NO_DATA_SENTINEL):
        if db_sw_images is _NO_DATA_SENTINEL:
            vnf_deployment_flavour = self.get_by_id(
                self._context, self.id, expected_attrs=['software_images'])
            if 'software_images' in vnf_deployment_flavour:
                self.software_images = vnf_deployment_flavour.software_images
                self.software_images.obj_reset_changes(recursive=True)
                self.obj_reset_changes(['software_images'])
            else:
                self.software_images = (
                    objects.VnfSoftwareImagesList(objects=[]))
        elif db_sw_images:
            self.software_images = base.obj_make_list(
                self._context, objects.VnfSoftwareImagesList(
                    self._context),
                objects.VnfSoftwareImage, db_sw_images)
            self.obj_reset_changes(['software_images'])

    def to_dict(self, include_fields=None):
        software_images = list()
        for software_image in self.software_images:
            sw_image_dict = software_image.to_dict(
                include_fields=include_fields)
            if sw_image_dict:
                software_images.append(sw_image_dict)

        return software_images


@base.TackerObjectRegistry.register
class VnfDeploymentFlavoursList(ovoo_base.ObjectListBase, base.TackerObject):

    VERSION = '1.0'

    fields = {
        'objects': fields.ListOfObjectsField('VnfDeploymentFlavour')
    }

    def to_dict(self, include_fields=None):
        software_images = list()
        for deployment_flavour in self.objects:
            images = deployment_flavour.to_dict(include_fields=include_fields)
            if images:
                software_images.extend(images)

        return software_images
