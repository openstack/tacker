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
import copy

from oslo_log import log as logging
from oslo_utils import timeutils
from oslo_utils import uuidutils
from oslo_versionedobjects import base as ovoo_base
from sqlalchemy import exc
from sqlalchemy.orm import joinedload
from sqlalchemy_filters import apply_filters

from tacker._i18n import _
from tacker.common import exceptions
from tacker.common import utils
from tacker.db import api as db_api
from tacker.db.db_sqlalchemy import api
from tacker.db.db_sqlalchemy import models
from tacker.db.vnfm import vnfm_db
from tacker import objects
from tacker.objects import base
from tacker.objects import fields
from tacker.objects import vnf_instantiated_info
from tacker.objects import vnf_package as vnf_package_obj
from tacker.objects import vnf_package_vnfd as vnf_package_vnfd


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


@db_api.context_manager.reader
def _vnf_instance_list_by_filter(context, columns_to_join=None,
                                 filters=None):
    query = api.model_query(context, models.VnfInstance,
                            read_deleted="no",
                            project_only=True)

    if columns_to_join:
        for column in columns_to_join:
            query = query.options(joinedload(column))

    if filters:
        query = apply_filters(query, filters)

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


# decorator to catch DBAccess exception
def _wrap_object_error(method):

    def wrapper(*args, **kwargs):
        try:
            method(*args, **kwargs)
        except exc.SQLAlchemyError:
            raise exceptions.DBAccessError

    return wrapper


@db_api.context_manager.reader
def _get_vnf_instance(context, id):
    vnf_instance = api.model_query(
        context, models.VnfInstance).filter_by(
        vnfd_id=id).first()
    return vnf_instance


@db_api.context_manager.reader
def _vnf_instance_get(context, vnfd_id, columns_to_join=None):
    query = api.model_query(context, models.VnfInstance, read_deleted="no",
                            project_only=True).filter_by(vnfd_id=vnfd_id)

    if columns_to_join:
        for column in columns_to_join:
            query = query.options(joinedload(column))

    return query.first()


def _merge_vim_connection_info(
        pre_vim_connection_info_list,
        update_vim_connection_info_list):

    def update_nested_element(pre_data, update_data):
        for key, val in update_data.items():
            if not isinstance(val, dict):
                pre_data[key] = val
                continue

            if key in pre_data:
                pre_data[key].update(val)
            else:
                pre_data.update({key: val})

    result = []
    clone_pre_list = copy.deepcopy(pre_vim_connection_info_list)

    for update_vim_connection in update_vim_connection_info_list:
        pre_data = None
        for i in range(0, len(clone_pre_list) - 1):
            if clone_pre_list[i].id == update_vim_connection.get('id'):
                pre_data = clone_pre_list.pop(i)

        if pre_data is None:
            # new elm.
            result.append(objects.VimConnectionInfo._from_dict(
                update_vim_connection))
            continue

        convert_dict = pre_data.to_dict()
        update_nested_element(convert_dict, update_vim_connection)
        result.append(objects.VimConnectionInfo._from_dict(
            convert_dict))

    # Reflecting unupdated data
    result.extend(clone_pre_list)

    return result


@db_api.context_manager.writer
def _update_vnf_instances(
        context,
        vnf_lcm_opoccs,
        body_data,
        vnfd_pkg_data,
        vnfd_id):
    updated_values = {}
    updated_values['vnf_instance_name'] = body_data.get('vnf_instance_name')
    updated_values['vnf_instance_description'] = body_data.get(
        'vnf_instance_description')

    # get vnf_instances
    vnf_instance = _get_vnf_instance(context, vnfd_id)
    if body_data.get('metadata'):
        vnf_instance.vnf_metadata.update(body_data.get('metadata'))
        updated_values['vnf_metadata'] = vnf_instance.vnf_metadata

    if body_data.get('vim_connection_info'):
        merge_vim_connection_info = _merge_vim_connection_info(
            vnf_instance.vim_connection_info,
            body_data.get('vim_connection_info'))

        updated_values['vim_connection_info'] = merge_vim_connection_info

    if vnfd_pkg_data and len(vnfd_pkg_data) > 0:
        updated_values['vnfd_id'] = vnfd_pkg_data.get('vnfd_id')
        updated_values['vnf_provider'] = vnfd_pkg_data.get('vnf_provider')
        updated_values['vnf_product_name'] = vnfd_pkg_data.get(
            'vnf_product_name')
        updated_values['vnf_software_version'] = vnfd_pkg_data.get(
            'vnf_software_version')
        updated_values['vnf_pkg_id'] = vnfd_pkg_data.get('package_uuid')

    api.model_query(context, models.VnfInstance). \
        filter_by(id=vnf_lcm_opoccs.get('vnf_instance_id')). \
        update(updated_values, synchronize_session=False)

    vnf_now = timeutils.utcnow()
    if (body_data.get('vnfd_id') or body_data.get('vnf_pkg_id')):
        # update vnf
        if body_data.get('vnfd_id'):
            updated_values = {'vnfd_id': body_data.get('vnfd_id'),
                              'updated_at': vnf_now
                              }
        elif body_data.get('vnf_pkg_id'):
            updated_values = {'vnfd_id': vnfd_pkg_data.get('vnfd_id'),
                              'updated_at': vnf_now
                              }
        api.model_query(context, vnfm_db.VNF).\
            filter_by(id=vnf_lcm_opoccs.get('vnf_instance_id')). \
            update(updated_values, synchronize_session=False)

        # get vnf_packages
        id = vnfd_pkg_data.get('package_uuid')
        try:
            vnf_package = vnf_package_obj.VnfPackage.get_by_id(context, id)
        except exceptions.VnfPackageNotFound:
            raise exceptions.VnfPackageNotFound(id=id)

        if vnf_package.usage_state == 'NOT_IN_USE':
            # update vnf_packages
            now = timeutils.utcnow()
            updated_values = {'usage_state': 'IN_USE',
                              'updated_at': now
                              }
            api.model_query(context, models.VnfPackage).\
                filter_by(id=id). \
                update(updated_values, synchronize_session=False)

        # get vnf_instances
        vnf_instance = _get_vnf_instance(context, vnfd_id)

        if not vnf_instance:
            # get vnf_package_vnfd
            vnfd_data = vnf_package_vnfd.VnfPackageVnfd.get_by_vnfdId(
                context, vnfd_id)

            # update vnf_packages
            now = timeutils.utcnow()
            updated_values = {'usage_state': 'NOT_IN_USE',
                              'updated_at': now
                              }
            api.model_query(context, models.VnfPackage).\
                filter_by(id=vnfd_data.package_uuid). \
                update(updated_values, synchronize_session=False)

    return vnf_now


@base.TackerObjectRegistry.register
class VnfInstance(base.TackerObject, base.TackerPersistentObject,
                  base.TackerObjectDictCompat):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.UUIDField(nullable=False),
        'vnf_instance_name': fields.StringField(nullable=True),
        'vnf_instance_description': fields.StringField(nullable=True),
        'instantiation_state':
        fields.VnfInstanceStateField(
            nullable=False,
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
        'vnf_metadata': fields.DictOfStringsField(nullable=True, default={}),
        'vnf_pkg_id': fields.StringField(nullable=False),
        'instantiated_vnf_info': fields.ObjectField('InstantiatedVnfInfo',
                                                nullable=True, default=None)
    }

    ALL_ATTRIBUTES = {
        'id': ('id', "string", 'VnfInstance'),
        'vnfInstanceName': ('vnf_instance_name', 'string', 'VnfInstance'),
        'vnfInstanceDescription': (
            'vnf_instance_description', 'string', 'VnfInstance'),
        'instantiationState': ('instantiation_state', 'string', 'VnfInstance'),
        'taskState': ('task_state', 'string', 'VnfInstance'),
        'vnfdId': ('vnfd_id', 'string', 'VnfInstance'),
        'vnfProvider': ('vnf_provider', 'string', 'VnfInstance'),
        'vnfProductName': ('vnf_product_name', 'string', 'VnfInstance'),
        'vnfSoftwareVersion': (
            'vnf_software_version', 'string', 'VnfInstance'),
        'vnfdVersion': ('vnfd_version', 'string', 'VnfInstance'),
        'tenantId': ('tenant_id', 'string', 'VnfInstance'),
        'vnfPkgId': ('vnf_pkg_id', 'string', 'VnfInstance'),
        'vimConnectionInfo/*': ('vim_connection_info', 'key_value_pair',
                                {"key_column": "key", "value_column": "value",
                                 "model": "VnfInstance"}),
        'metadata/*': ('vnf_metadata', 'key_value_pair',
                       {"key_column": "key", "value_column": "value",
                        "model": "VnfInstance"}),
    }

    ALL_ATTRIBUTES.update(
        vnf_instantiated_info.InstantiatedVnfInfo.ALL_ATTRIBUTES)

    FLATTEN_ATTRIBUTES = utils.flatten_dict(ALL_ATTRIBUTES.copy())

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

        VnfInstance._load_instantiated_vnf_info_from_db_object(
            context, vnf_instance, db_vnf_instance)

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
            inst_vnf_info = objects.InstantiatedVnfInfo.obj_from_db_obj(
                context, db_vnf_instance['instantiated_vnf_info'])
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

        # add default vnf_instance_name if not specified
        # format: 'vnf' + <vnf instance id>
        if 'vnf_instance_name' not in updates or \
                not updates.get("vnf_instance_name"):
            updates['vnf_instance_name'] = 'vnf-' + self.id
            self.vnf_instance_name = updates['vnf_instance_name']

        db_vnf_instance = _vnf_instance_create(self._context, updates)
        expected_attrs = ["instantiated_vnf_info"]
        self._from_db_object(self._context, self, db_vnf_instance,
                             expected_attrs=expected_attrs)

    @base.remotable
    @_wrap_object_error
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
                if (field == 'vnf_instance_name' and
                        not self[field]):
                    self.vnf_instance_name = 'vnf-' + self.id

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
    @_wrap_object_error
    def update_metadata(self, data):
        _metadata = copy.deepcopy(self['vnf_metadata'])
        _metadata.update(data)
        self['vnf_metadata'] = _metadata
        self.save()

    @base.remotable
    @_wrap_object_error
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
            'vnfd_version': self.vnfd_version,
            'vnf_metadata': self.vnf_metadata}

        if (self.instantiation_state == fields.VnfInstanceState.INSTANTIATED
                and self.instantiated_vnf_info):
            data.update({'instantiated_vnf_info':
                         self.instantiated_vnf_info.to_dict()})

            vim_connection_info_list = []
            for vim_connection_info in self.vim_connection_info:
                vim_connection_info_list.append(vim_connection_info.to_dict())
            data.update({'vim_connection_info': vim_connection_info_list})

        return data

    @base.remotable
    def update(
            self,
            context,
            vnf_lcm_opoccs,
            body_data,
            vnfd_pkg_data,
            vnfd_id):

        # update vnf_instances
        return _update_vnf_instances(
            context,
            vnf_lcm_opoccs,
            body_data,
            vnfd_pkg_data,
            vnfd_id)

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

    @base.remotable_classmethod
    def get_by_filters(cls, context, filters=None,
                       expected_attrs=None):
        expected_attrs = ["instantiated_vnf_info"]
        db_vnf_instances = _vnf_instance_list_by_filter(
            context, columns_to_join=expected_attrs,
            filters=filters)

        return _make_vnf_instance_list(context, cls(), db_vnf_instances,
                                       expected_attrs)

    @base.remotable_classmethod
    def vnf_instance_list(cls, vnfd_id, context):
        # get vnf_instance data
        expected_attrs = ["instantiated_vnf_info"]
        db_vnf_instances = _vnf_instance_get(context, vnfd_id,
                                             columns_to_join=expected_attrs)

        vnf_instance_cls = VnfInstance
        vnf_instance_data = ""
        vnf_instance_obj = vnf_instance_cls._from_db_object(
            context, vnf_instance_cls(context), db_vnf_instances,
            expected_attrs=expected_attrs)
        vnf_instance_data = vnf_instance_obj

        return vnf_instance_data
