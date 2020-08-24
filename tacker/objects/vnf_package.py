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
from oslo_serialization import jsonutils as json
from oslo_utils import excutils
from oslo_utils import timeutils
from oslo_utils import uuidutils
from oslo_utils import versionutils
from oslo_versionedobjects import base as ovoo_base
from sqlalchemy.orm import joinedload
from sqlalchemy.sql import func
from sqlalchemy_filters import apply_filters

from tacker._i18n import _
from tacker.common import exceptions
from tacker.common import utils
from tacker.db import api as db_api
from tacker.db.db_sqlalchemy import api
from tacker.db.db_sqlalchemy import models
from tacker import objects
from tacker.objects import base
from tacker.objects import fields
from tacker.objects import vnf_artifact
from tacker.objects import vnf_software_image

_NO_DATA_SENTINEL = object()

VNF_PACKAGE_OPTIONAL_ATTRS = [
    'vnf_deployment_flavours',
    'vnfd',
    'vnf_artifacts']

LOG = logging.getLogger(__name__)


def _add_user_defined_data(context, package_uuid, user_data,
                           max_retries=10):
    for attempt in range(max_retries):
        try:
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

                return user_data
        except db_exc.DBDuplicateEntry:
            # a concurrent transaction has been committed,
            # try again unless this was the last attempt
            with excutils.save_and_reraise_exception() as context:
                if attempt < max_retries - 1:
                    context.reraise = False
                else:
                    raise exceptions.UserDataUpdateCreateFailed(
                        id=package_uuid, retries=max_retries)


def _vnf_package_user_data_get_query(context, package_uuid, model):
    return api.model_query(context, model, read_deleted="no",
                           project_only=True).\
        filter_by(package_uuid=package_uuid)


@db_api.context_manager.writer
def _update_user_defined_data(context, package_uuid, user_data):
    model = models.VnfPackageUserData
    user_data = user_data.copy()
    session = context.session
    with session.begin(subtransactions=True):
        # Get existing user_data
        db_user_data = _vnf_package_user_data_get_query(context, package_uuid,
                                                        model).all()
        save = []
        skip = []
        # We only want to send changed user_data.
        for row in db_user_data:
            if row.key in user_data:
                value = user_data.pop(row.key)
                if row.value != value:
                    # ORM objects will not be saved until we do the bulk save
                    row.value = value
                    save.append(row)
                    continue
            skip.append(row)

        # We also want to save non-existent user_data
        save.extend(model(key=key, value=value, package_uuid=package_uuid)
                    for key, value in user_data.items())
        # Do a bulk save
        if save:
            session.bulk_save_objects(save, update_changed_only=True)

        # Construct result dictionary with current user_data
        save.extend(skip)
        result = {row['key']: row['value'] for row in save}

    return result


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
def _vnf_package_list_by_filters(context, read_deleted=None, filters=None):
    query = api.model_query(context, models.VnfPackage,
                            read_deleted=read_deleted,
                            project_only=True).options(joinedload('_metadata'))

    if filters:
        # Need to join VnfDeploymentFlavour, VnfSoftwareImage and
        # VnfSoftwareImageMetadata db table explicitly
        # only when filters contains one of the column matching
        # from VnfSoftwareImage or VnfSoftwareImageMetadata db table.
        filter_data = json.dumps(filters)
        if 'VnfSoftwareImageMetadata' in filter_data:
            query = query.join(models.VnfDeploymentFlavour).join(
                models.VnfSoftwareImage).join(
                models.VnfSoftwareImageMetadata)
        elif 'VnfSoftwareImage' in filter_data:
            query = query.join(models.VnfDeploymentFlavour).join(
                models.VnfSoftwareImage)

        if 'VnfPackageArtifactInfo' in filter_data:
            query = query.join(models.VnfPackageArtifactInfo)

        query = apply_filters(query, filters)

    return query.all()


@db_api.context_manager.writer
def _update_vnf_package_except_user_data(context, vnf_package):
    vnf_package.save(session=context.session)


def _vnf_package_update(context, package_uuid, values, columns_to_join=None):
    user_data = values.pop('user_data', None)
    if user_data:
        _update_user_defined_data(context, package_uuid, user_data)

    vnf_package = _vnf_package_get_by_id(
        context, package_uuid, columns_to_join=columns_to_join)
    if values:
        vnf_package.update(values)
        _update_vnf_package_except_user_data(context, vnf_package)

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
    api.model_query(context, models.VnfPackageArtifactInfo). \
        filter_by(package_uuid=package_uuid). \
        update(updated_values, synchronize_session=False)
    api.model_query(context, models.VnfPackageVnfd). \
        filter_by(package_uuid=package_uuid). \
        soft_delete(synchronize_session=False)
    api.model_query(context, models.VnfPackage).\
        filter_by(id=package_uuid). \
        update(updated_values, synchronize_session=False)


def _make_vnf_packages_list(context, vnf_package_list, db_vnf_package_list,
                            expected_attrs=None):
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
class VnfPackage(base.TackerObject, base.TackerPersistentObject,
                 base.TackerObjectDictCompat):

    # Key corresponds to the name of the parameter as defined
    # in type VnfPkgInfo of SOL003 document and value will contain tuple
    # of following values:-
    # 1. Parameter that is mapped to version object
    # 2. Data type of the field as per the data types supported by
    # attribute-based filtering
    # 3. DB model that's mapped to the version object.
    # 4. Valid values for a given data type if any. This value is set
    # especially for 'enum' data type.
    ALL_ATTRIBUTES = {
        'id': ('id', "string", 'VnfPackage'),
        'onboardingState': ('onboarding_state', "enum", 'VnfPackage',
            fields.PackageOnboardingStateTypeField().valid_values),
        'operationalState': ('operational_state', 'enum', 'VnfPackage',
            fields.PackageOperationalStateTypeField().valid_values),
        'usageState': ('usage_state', 'enum', 'VnfPackage',
            fields.PackageUsageStateTypeField().valid_values),
        'vnfProvider': ('vnfd.vnf_provider', 'string', 'VnfPackageVnfd'),
        'vnfProductName': ('vnfd.vnf_product_name', 'string',
                           'VnfPackageVnfd'),
        'vnfdId': ('vnfd.vnfd_id', 'string', 'VnfPackageVnfd'),
        'vnfSoftwareVersion': ('vnfd.vnf_software_version', 'string',
                               'VnfPackageVnfd'),
        'vnfdVersion': ('vnfd.vnfd_version', 'string', 'VnfPackageVnfd'),
        'userDefinedData/*': ('user_data', 'key_value_pair',
            {"key_column": "key", "value_column": "value",
             "model": "VnfPackageUserData"}),
        "checksum": {
            'algorithm': ('algorithm', 'string', 'VnfPackage'),
            'hash': ('hash', 'string', 'VnfPackage'),
        }
    }

    ALL_ATTRIBUTES.update(vnf_software_image.VnfSoftwareImage.ALL_ATTRIBUTES)
    ALL_ATTRIBUTES.update(vnf_artifact.VnfPackageArtifactInfo.ALL_ATTRIBUTES)

    FLATTEN_ATTRIBUTES = utils.flatten_dict(ALL_ATTRIBUTES.copy())

    simple_attributes = ['id', 'onboardingState', 'operationalState',
                         'usageState']
    simple_instantiated_attributes = ['vnfProvider', 'vnfProductName',
                         'vnfdId', 'vnfSoftwareVersion', 'vnfdVersion']

    COMPLEX_ATTRIBUTES = ["checksum", "userDefinedData"]
    COMPLEX_ATTRIBUTES.extend(
        vnf_software_image.VnfSoftwareImage.COMPLEX_ATTRIBUTES)
    COMPLEX_ATTRIBUTES.extend(vnf_artifact.VnfPackageArtifactInfo.
                              COMPLEX_ATTRIBUTES)

    # Version 1.1: Added 'size' to persist size of VnfPackage.
    VERSION = '1.1'

    fields = {
        'id': fields.UUIDField(nullable=False),
        'onboarding_state': fields.PackageOnboardingStateTypeField(
            nullable=False),
        'operational_state': fields.PackageOperationalStateTypeField(
            nullable=False),
        'usage_state': fields.PackageUsageStateTypeField(nullable=False),
        'user_data': fields.DictOfStringsField(),
        'tenant_id': fields.StringField(nullable=False),
        'algorithm': fields.StringField(nullable=True),
        'hash': fields.StringField(nullable=True),
        'location_glance_store': fields.StringField(nullable=True),
        'vnf_deployment_flavours': fields.ObjectField(
            'VnfDeploymentFlavoursList', nullable=True),
        'vnfd': fields.ObjectField('VnfPackageVnfd', nullable=True),
        'size': fields.IntegerField(nullable=False, default=0),
        'vnf_artifacts': fields.ObjectField('VnfPackageArtifactInfoList',
                                            nullable=True)
    }

    def __init__(self, context=None, **kwargs):
        super(VnfPackage, self).__init__(context, **kwargs)
        self.obj_set_defaults()

    def obj_make_compatible(self, primitive, target_version):
        super(VnfPackage, self).obj_make_compatible(primitive, target_version)
        target_version = versionutils.convert_version_to_tuple(target_version)
        if target_version < (1, 1) and 'size' in primitive:
            del primitive['size']

    @staticmethod
    def _from_db_object(context, vnf_package, db_vnf_package,
                        expected_attrs=None):
        expected_attrs = expected_attrs or []

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

        if 'vnf_artifacts' in expected_attrs:
            vnf_package._load_vnf_artifacts(
                db_vnf_package.get('vnf_artifacts'))

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

    def _load_vnf_artifacts(self, db_artifact=_NO_DATA_SENTINEL):
        if db_artifact is _NO_DATA_SENTINEL:
            vnf_package = self.get_by_id(
                self._context, self.id,
                expected_attrs=['vnf_artifacts'])
            if 'vnf_artifacts' in vnf_package:
                self.vnf_artifacts = vnf_package.vnf_artifacts
                self.vnf_artifacts.obj_reset_changes(recursive=True)
                self.obj_reset_changes(['vnf_artifacts'])
            else:
                self.vnf_artifacts = objects.\
                    VnfPackageArtifactInfoList(objects=[])
        elif db_artifact:
            self.vnf_artifacts = base.obj_make_list(
                self._context, objects.VnfPackageArtifactInfoList(
                    self._context), objects.VnfPackageArtifactInfo,
                db_artifact)
            self.obj_reset_changes(['vnf_artifacts'])

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
        elif attrname == 'vnf_artifacts':
            self._load_vnf_artifacts()
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
        updates = self.obj_get_changes()

        if 'id' not in updates:
            updates['id'] = uuidutils.generate_uuid()
            self.id = updates['id']

        for key in ['vnf_deployment_flavours']:
            if key in updates.keys():
                updates.pop(key)

        for key in ['vnf_artifacts']:
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

    @base.remotable
    def is_package_in_use(self, context):
        if self.onboarding_state == \
                fields.PackageOnboardingStateType.ONBOARDED:
            # check if vnf package is used by any vnf instances.
            query = context.session.query(
                func.count(models.VnfInstance.id)).\
                filter_by(
                instantiation_state=fields.VnfInstanceState.INSTANTIATED).\
                filter_by(tenant_id=self.tenant_id).\
                filter_by(vnfd_id=self.vnfd.vnfd_id).\
                filter_by(deleted=False)
            result = query.scalar()
            return True if result > 0 else False
        else:
            return False

    def _get_vnfd(self, include_fields=None):
        response = dict()
        to_fields = set(self.simple_instantiated_attributes).intersection(
            include_fields)
        for field in to_fields:
            response[field] = utils.deepgetattr(self,
                self.FLATTEN_ATTRIBUTES[field][0])
        return response

    def _get_checksum(self, include_fields=None):
        response = dict()
        to_fields = set([key for key in self.FLATTEN_ATTRIBUTES.keys()
            if key.startswith('checksum')])
        to_fields = to_fields.intersection(include_fields)
        for field in to_fields:
            display_field = field.split("/")[-1]
            response[display_field] = getattr(self,
                self.FLATTEN_ATTRIBUTES[field][0])
        return {'checksum': response} if response else None

    def _get_user_defined_data(self, include_fields=None):
        # Need special handling for field containing key-value pair.
        # If user requests userDefined/key1 and if userDefineData contains
        # key1=value1, key2-value2, it should return only keys that are
        # requested in include_fields. If user requests only userDefinedData,
        # then in that case,it should return all key/value pairs. In case,
        # if any of the requested key is not present, then it should
        # siliently ignore it.
        key = 'userDefinedData'
        if key in include_fields or 'userDefinedData/*' in include_fields:
            return {key: self.user_data}
        else:
            # Check if user has requested specified keys from
            # userDefinedData.
            data_resp = dict()
            key_list = []
            special_key = 'userDefinedData/'
            for field in include_fields:
                if field.startswith(special_key):
                    key_list.append(field[len(special_key):])

            for key_req in key_list:
                if key_req in self.user_data:
                    data_resp[key_req] = self.user_data[key_req]

            if data_resp:
                return {key: data_resp}

    def _basic_vnf_package_info(self, include_fields=None):
        response = dict()
        to_fields = set(self.simple_attributes).intersection(include_fields)
        for field in to_fields:
            response[field] = getattr(self, self.FLATTEN_ATTRIBUTES[field][0])
        return response

    def to_dict(self, include_fields=None):
        if not include_fields:
            include_fields = set(self.FLATTEN_ATTRIBUTES.keys())

        vnf_package_response = self._basic_vnf_package_info(
            include_fields=include_fields)

        user_defined_data = self._get_user_defined_data(
            include_fields=include_fields)

        if user_defined_data:
            vnf_package_response.update(user_defined_data)

        if (self.onboarding_state ==
                fields.PackageOnboardingStateType.ONBOARDED):

            software_images = self.vnf_deployment_flavours.to_dict(
                include_fields=include_fields)
            if software_images:
                vnf_package_response.update(
                    {'softwareImages': software_images})

            vnf_package_response.update(self._get_vnfd(
                include_fields=include_fields))

            checksum = self._get_checksum(include_fields=include_fields)
            if checksum:
                vnf_package_response.update(checksum)

            artifacts = self.vnf_artifacts.to_dict(
                include_fields=include_fields)
            if artifacts:
                vnf_package_response.update(
                    {'additionalArtifacts': artifacts})

        return vnf_package_response


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
    def get_by_filters(cls, context, read_deleted=None, filters=None):
        db_vnf_packages = _vnf_package_list_by_filters(context,
                                            read_deleted=read_deleted,
                                            filters=filters)
        return _make_vnf_packages_list(context, cls(), db_vnf_packages)
