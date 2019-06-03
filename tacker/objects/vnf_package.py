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

_NO_DATA_SENTINEL = object()

VNF_PACKAGE_OPTIONAL_ATTRS = ['vnf_deployment_flavours', 'vnfd']

LOG = logging.getLogger(__name__)


def _add_user_defined_data(context, package_uuid, user_data,
                           max_retries=10):
    for attempt in range(max_retries):
        with db_api.context_manager.writer.using(context):

            new_entries = []
            for key, value in user_data.items():
                new_entries.append({"key": key,
                                    "value": value,
                                    "package_uuid": package_uuid})
            if new_entries:
                context.session.execute(
                    models.VnfPackageUserData.__table__.insert(None),
                    new_entries)


@db_api.context_manager.reader
def _vnf_package_get_by_id(context, package_uuid, columns_to_join=None):

    query = api.model_query(context, models.VnfPackage,
                            read_deleted="no", project_only=True). \
        filter_by(id=package_uuid).options(joinedload('_metadata'))

    if columns_to_join:
        for column in columns_to_join:
            query = query.options(joinedload(column))

    result = query.first()

    if not result:
        raise exceptions.VnfPackageNotFound(id=package_uuid)

    return result


@db_api.context_manager.writer
def _vnf_package_create(context, values, user_data=None):

    vnf_package = models.VnfPackage()
    vnf_package.update(values)
    vnf_package.save(context.session)
    vnf_package._metadata = []

    if user_data:
        _add_user_defined_data(context, vnf_package.id, user_data)
        context.session.expire(vnf_package, ['_metadata'])
        vnf_package._metadata

    return vnf_package


@db_api.context_manager.reader
def _vnf_package_list(context, columns_to_join=None):
    query = api.model_query(context, models.VnfPackage, read_deleted="no",
                            project_only=True).options(joinedload('_metadata'))

    if columns_to_join:
        for column in columns_to_join:
            query = query.options(joinedload(column))

    return query.all()


@db_api.context_manager.reader
def _vnf_package_list_by_filters(context, read_deleted=None, **filters):
    query = api.model_query(context, models.VnfPackage,
                            read_deleted=read_deleted, project_only=True)
    for key, value in filters.items():
        filter_obj = getattr(models.VnfPackage, key)
        if key == 'deleted_at':
            query = query.filter(filter_obj >= value)
        else:
            query = query.filter(filter_obj == value)
    return query.all()


@db_api.context_manager.writer
def _vnf_package_update(context, package_uuid, values, columns_to_join=None):

    vnf_package = _vnf_package_get_by_id(context, package_uuid,
                                         columns_to_join=columns_to_join)
    vnf_package.update(values)
    vnf_package.save(session=context.session)

    return vnf_package


@db_api.context_manager.writer
def _destroy_vnf_package(context, package_uuid):
    now = timeutils.utcnow()
    updated_values = {'deleted': True,
                      'deleted_at': now
                      }

    flavour_query = api.model_query(
        context, models.VnfDeploymentFlavour,
        (models.VnfDeploymentFlavour.id, )).filter_by(
        package_uuid=package_uuid)

    software_images_query = api.model_query(
        context, models.VnfSoftwareImage,
        (models.VnfSoftwareImage.id, )).filter(
        models.VnfSoftwareImage.flavour_uuid.in_(flavour_query.subquery()))

    api.model_query(
        context, models.VnfSoftwareImageMetadata).filter(
        models.VnfSoftwareImageMetadata.image_uuid.in_(
            software_images_query.subquery())).update(
        updated_values, synchronize_session=False)

    software_images_query.update(updated_values, synchronize_session=False)

    api.model_query(context, models.VnfPackageUserData). \
        filter_by(package_uuid=package_uuid). \
        update(updated_values, synchronize_session=False)
    api.model_query(context, models.VnfDeploymentFlavour). \
        filter_by(package_uuid=package_uuid). \
        update(updated_values, synchronize_session=False)
    api.model_query(context, models.VnfPackageVnfd). \
        filter_by(package_uuid=package_uuid). \
        update(updated_values, synchronize_session=False)
    api.model_query(context, models.VnfPackage).\
        filter_by(id=package_uuid). \
        update(updated_values, synchronize_session=False)


def _make_vnf_packages_list(context, vnf_package_list, db_vnf_package_list,
                            expected_attrs):
    vnf_package_cls = VnfPackage

    vnf_package_list.objects = []
    for db_package in db_vnf_package_list:
        vnf_pkg_obj = vnf_package_cls._from_db_object(
            context, vnf_package_cls(context), db_package,
            expected_attrs=expected_attrs)
        vnf_package_list.objects.append(vnf_pkg_obj)

    vnf_package_list.obj_reset_changes()
    return vnf_package_list


@base.TackerObjectRegistry.register
class VnfPackage(base.TackerObject, base.TackerPersistentObject):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.UUIDField(nullable=False),
        'onboarding_state': fields.StringField(nullable=False),
        'operational_state': fields.StringField(nullable=False),
        'usage_state': fields.StringField(nullable=False),
        'user_data': fields.DictOfStringsField(),
        'tenant_id': fields.StringField(nullable=False),
        'algorithm': fields.StringField(nullable=True),
        'hash': fields.StringField(nullable=True),
        'location_glance_store': fields.StringField(nullable=True),
        'vnf_deployment_flavours': fields.ObjectField(
            'VnfDeploymentFlavoursList', nullable=True),
        'vnfd': fields.ObjectField('VnfPackageVnfd', nullable=True),
    }

    @staticmethod
    def _from_db_object(context, vnf_package, db_vnf_package,
                        expected_attrs=None):
        if expected_attrs is None:
            expected_attrs = []

        vnf_package._context = context

        for key in vnf_package.fields:
            if key in VNF_PACKAGE_OPTIONAL_ATTRS:
                continue
            if key == 'user_data':
                db_key = 'metadetails'
            else:
                db_key = key
            setattr(vnf_package, key, db_vnf_package[db_key])

        vnf_package._context = context
        vnf_package._extra_attributes_from_db_object(
            vnf_package, db_vnf_package, expected_attrs)

        vnf_package.obj_reset_changes()
        return vnf_package

    @staticmethod
    def _extra_attributes_from_db_object(vnf_package, db_vnf_package,
                                         expected_attrs=None):
        """Method to help with migration of extra attributes to objects."""

        if expected_attrs is None:
            expected_attrs = []

        if 'vnf_deployment_flavours' in expected_attrs:
            vnf_package._load_vnf_deployment_flavours(
                db_vnf_package.get('vnf_deployment_flavours'))

        if 'vnfd' in expected_attrs:
            vnf_package._load_vnfd(db_vnf_package.get('vnfd'))

    def _load_vnf_deployment_flavours(self, db_flavours=_NO_DATA_SENTINEL):
        if db_flavours is _NO_DATA_SENTINEL:
            vnf_package = self.get_by_id(
                self._context, self.id,
                expected_attrs=['vnf_deployment_flavours'])
            if 'vnf_deployment_flavours' in vnf_package:
                self.vnf_deployment_flavours = \
                    vnf_package.vnf_deployment_flavours
                self.vnf_deployment_flavours.obj_reset_changes(recursive=True)
                self.obj_reset_changes(['vnf_deployment_flavours'])
            else:
                self.vnf_deployment_flavours = \
                    objects.VnfDeploymentFlavoursList(objects=[])
        elif db_flavours:
            self.vnf_deployment_flavours = base.obj_make_list(
                self._context, objects.VnfDeploymentFlavoursList(
                    self._context), objects.VnfDeploymentFlavour, db_flavours)
            self.obj_reset_changes(['vnf_deployment_flavours'])

    def _load_vnfd(self, db_vnfd=_NO_DATA_SENTINEL):
        if db_vnfd is None:
            self.vnfd = None
        elif db_vnfd is _NO_DATA_SENTINEL:
            vnf_package = self.get_by_id(self._context, self.id,
                                         expected_attrs=['vnfd'])

            if 'vnfd' in vnf_package and vnf_package.vnfd is not None:
                self.vnfd = vnf_package.vnfd
                self.vnfd.obj_reset_changes(recursive=True)
                self.obj_reset_changes(['vnfd'])
            else:
                self.vnfd = None
        elif db_vnfd:
            self.vnfd = objects.VnfPackageVnfd.obj_from_db_obj(
                self._context, db_vnfd)
            self.obj_reset_changes(['vnfd'])

    def _load_generic(self, attrname):
        vnf_package = self.__class__.get_by_id(self._context,
                                               id=self.id,
                                               expected_attrs=None)
        if attrname not in vnf_package:
            raise exceptions.ObjectActionError(
                action='obj_load_attr',
                reason=_('loading %s requires recursion') % attrname)

        for field in self.fields:
            if field in vnf_package and field not in self:
                setattr(self, field, getattr(vnf_package, field))

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
        """Internal method for loading attributes from vnf package."""

        if attrname == 'vnf_deployment_flavours':
            self._load_vnf_deployment_flavours()
        elif attrname == 'vnfd':
            self._load_vnfd()
        elif attrname in self.fields and attrname != 'id':
            self._load_generic(attrname)
        else:
            # NOTE(nirajsingh): Raise error if non existing field is
            # requested.
            raise exceptions.ObjectActionError(
                action='obj_load_attr',
                reason=_('attribute %s not lazy-loadable') % attrname)

        self.obj_reset_changes([attrname])

    @base.remotable
    def create(self):
        if self.obj_attr_is_set('id'):
            raise exceptions.ObjectActionError(action='create',
                                               reason=_('already created'))
        updates = self.obj_get_changes()

        if 'id' not in updates:
            updates['id'] = uuidutils.generate_uuid()
            self.id = updates['id']

        for key in ['vnf_deployment_flavours']:
            if key in updates.keys():
                updates.pop(key)

        user_data = updates.pop('user_data', None)
        db_vnf_package = _vnf_package_create(self._context, updates,
                                             user_data=user_data)
        self._from_db_object(self._context, self, db_vnf_package)

    @base.remotable_classmethod
    def get_by_id(cls, context, id, expected_attrs=None):
        db_vnf_package = _vnf_package_get_by_id(
            context, id, columns_to_join=expected_attrs)
        return cls._from_db_object(context, cls(), db_vnf_package,
                                   expected_attrs=expected_attrs)

    @base.remotable
    def destroy(self, context):
        if not self.obj_attr_is_set('id'):
            raise exceptions.ObjectActionError(action='destroy',
                                               reason='no uuid')

        _destroy_vnf_package(context, self.id)

    @base.remotable
    def save(self):
        updates = self.tacker_obj_get_changes()
        for key in ['vnf_deployment_flavours']:
            if key in updates.keys():
                updates.pop(key)

        db_vnf_package = _vnf_package_update(self._context,
                                            self.id, updates)
        self._from_db_object(self._context, self, db_vnf_package)


@base.TackerObjectRegistry.register
class VnfPackagesList(ovoo_base.ObjectListBase, base.TackerObject):

    VERSION = '1.0'

    fields = {
        'objects': fields.ListOfObjectsField('VnfPackage')
    }

    @base.remotable_classmethod
    def get_all(cls, context, expected_attrs=None):
        db_vnf_packages = _vnf_package_list(context,
                                            columns_to_join=expected_attrs)
        return _make_vnf_packages_list(context, cls(), db_vnf_packages,
                                       expected_attrs)

    @base.remotable_classmethod
    def get_by_filters(self, context, read_deleted=None, **filters):
        return _vnf_package_list_by_filters(context,
                                            read_deleted=read_deleted,
                                            **filters)
