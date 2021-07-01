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

from datetime import datetime

from oslo_log import log as logging
from oslo_serialization import jsonutils
from oslo_utils import timeutils
from oslo_versionedobjects import base as ovoo_base
from sqlalchemy import exc
from sqlalchemy.orm import joinedload

from tacker.common import exceptions
from tacker.common import utils
from tacker.db import api as db_api
from tacker.db.db_sqlalchemy import api
from tacker.db.db_sqlalchemy import models
from tacker import objects
from tacker.objects import base
from tacker.objects import common
from tacker.objects import fields


LOG = logging.getLogger(__name__)


@db_api.context_manager.writer
def _vnf_lcm_op_occ_create(context, values):
    fields = {
        'id': values.id,
        'operation_state': values.operation_state,
        'state_entered_time': values.state_entered_time,
        'start_time': values.start_time,
        'vnf_instance_id': values.vnf_instance_id,
        'operation': values.operation,
        'is_automatic_invocation': values.is_automatic_invocation,
        'is_cancel_pending': values.is_cancel_pending,
        'error': values.error,
        'resource_changes': values.resource_changes,
        'changed_info': values.changed_info,
        'changed_ext_connectivity': values.changed_ext_connectivity,
        'error_point': values.error_point,
        'tenant_id': values.tenant_id,
    }
    if 'grant_id' in values:
        fields['grant_id'] = values.grant_id
    if 'operation_params' in values:
        fields['operation_params'] = values.operation_params

    context.session.execute(
        models.VnfLcmOpOccs.__table__.insert(None),
        fields)


@db_api.context_manager.writer
def _vnf_lcm_op_occ_update(context, values):
    update = {'operation_state': values.operation_state,
              'state_entered_time': values.state_entered_time,
              'error_point': values.error_point,
              'updated_at': datetime.utcnow()}
    LOG.debug('values %s', values)
    if 'resource_changes' in values:
        if values.resource_changes:
            update.update({'resource_changes': jsonutils.dumps(
                values.resource_changes.to_dict())})
    if 'error' in values:
        if values.error:
            update.update({'error': jsonutils.dumps(values.error.to_dict())})
    if 'changed_info' in values:
        if values.changed_info:
            update.update({'changed_info': jsonutils.dumps(
                values.changed_info.to_dict())})
    if 'changed_ext_connectivity' in values:
        if values.changed_ext_connectivity:
            update.update({'changed_ext_connectivity': jsonutils.dumps(
                [chg_ext_conn.to_dict() for chg_ext_conn in
                values.changed_ext_connectivity])})
    api.model_query(context, models.VnfLcmOpOccs). \
        filter_by(id=values.id). \
        update(update, synchronize_session=False)


def _make_vnf_lcm_op_occs_list(context, op_occ_list,
                               db_op_occ_list):
    lcm_op_occ_class = VnfLcmOpOcc

    op_occ_list.objects = []
    for db_op_occ in db_op_occ_list:
        if(db_op_occ['changed_info'] and
                isinstance(db_op_occ['changed_info'], str)):
            db_op_occ['changed_info'] = jsonutils.loads(
                db_op_occ['changed_info'])
        vnf_lcm_op_occ_obj = lcm_op_occ_class._from_db_object(
            context, lcm_op_occ_class(context), db_op_occ)
        op_occ_list.objects.append(vnf_lcm_op_occ_obj)

    op_occ_list.obj_reset_changes()
    return op_occ_list


@db_api.context_manager.reader
def _vnf_lcm_op_occs_get_by_id(context, vnf_lcm_op_occ_id):

    query = api.model_query(context, models.VnfLcmOpOccs,
                            read_deleted="no", project_only=True). \
        filter_by(id=vnf_lcm_op_occ_id)

    result = query.first()

    if not result:
        raise exceptions.NotFound(resource='table',
                                  name='vnf_lcm_op_occs')

    return result


@db_api.context_manager.reader
def _vnf_lcm_op_occs_get_by_vnf_instance_id(context, vnf_instance_id):

    query = api.model_query(context, models.VnfLcmOpOccs,
                            read_deleted="no", project_only=True). \
        filter_by(vnf_instance_id=vnf_instance_id)

    result = query.first()

    if not result:
        raise exceptions.VnfInstanceNotFound(id=vnf_instance_id)

    return result


@db_api.context_manager.reader
def _vnf_lcm_op_occs_get_by_filters(context, read_deleted=None,
                                    filters=None):

    query = api.model_query(context, models.VnfLcmOpOccs,
                            read_deleted=read_deleted, project_only=True)

    if filters:
        query = common.apply_filters(query, filters)

    return query.all()


@db_api.context_manager.reader
def _vnf_notify_get_by_id(context, vnf_instance_id, columns_to_join=None):

    query = api.model_query(context, models.VnfLcmOpOccs,
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
def _vnf_notify_create(context, values):

    vnf_lcm_op_occs = models.VnfLcmOpOccs()
    vnf_lcm_op_occs.update(values)
    vnf_lcm_op_occs.save(context.session)

    return _vnf_notify_get_by_id(context, vnf_lcm_op_occs.id,
                                columns_to_join=None)


@db_api.context_manager.writer
def _vnf_notify_update(context, vnf_instance_id, values,
                      columns_to_join=None):

    vnf_lcm_op_occs = _vnf_notify_get_by_id(context, vnf_instance_id,
                                        columns_to_join=columns_to_join)
    values = values.to_dict()
    vnf_lcm_op_occs.update(values)
    vnf_lcm_op_occs.save(session=context.session)

    return vnf_lcm_op_occs


@db_api.context_manager.writer
def _destroy_vnf_notify(context, uuid):
    now = timeutils.utcnow()
    updated_values = {'deleted': True,
                      'deleted_at': now
                      }
    api.model_query(context, models.VnfLcmOpOccs). \
        filter_by(id=uuid). \
        update(updated_values, synchronize_session=False)


# decorator to catch DBAccess exception
def _wrap_object_error(method):

    def wrapper(*args, **kwargs):
        try:
            method(*args, **kwargs)
        except exc.SQLAlchemyError:
            raise exceptions.DBAccessError

    return wrapper


@base.TackerObjectRegistry.register
class VnfLcmOpOcc(base.TackerObject, base.TackerObjectDictCompat,
                  base.TackerPersistentObject):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.UUIDField(nullable=False),
        'operation_state': fields.StringField(nullable=False),
        'state_entered_time': fields.DateTimeField(nullable=False),
        'start_time': fields.DateTimeField(nullable=False),
        'vnf_instance_id': fields.StringField(nullable=False),
        'grant_id': fields.StringField(nullable=True),
        'operation': fields.StringField(nullable=False),
        'is_automatic_invocation': fields.BooleanField(default=False),
        'operation_params': fields.StringField(nullable=True),
        'is_cancel_pending': fields.BooleanField(default=False),
        'error': fields.ObjectField(
            'ProblemDetails', nullable=True, default=None),
        'resource_changes': fields.ObjectField(
            'ResourceChanges', nullable=True, default=None),
        'changed_info': fields.ObjectField(
            'VnfInfoModifications', nullable=True, default=None),
        'changed_ext_connectivity': fields.ListOfObjectsField(
            'ExtVirtualLinkInfo', nullable=True, default=[]),
        'error_point': fields.IntegerField(nullable=True, default=0),
        'tenant_id': fields.StringField(nullable=False)
    }

    ALL_ATTRIBUTES = {
        'id': ('id', 'uuid', 'VnfLcmOpOccs'),
        'operationState': ('operation_state', 'string', 'VnfLcmOpOccs'),
        'stateEnteredTime':
            ('state_entered_time', 'datetime', 'VnfLcmOpOccs'),
        'startTime': ('start_time', 'datetime', 'VnfLcmOpOccs'),
        'vnfInstanceId': ('vnf_instance_id', 'string', 'VnfLcmOpOccs'),
        'grantId': ('grant_id', 'string', 'VnfLcmOpOccs'),
        'operation': ('operation', 'string', 'VnfLcmOpOccs'),
        'isAutomaticInvocation':
            ('is_automatic_invocation', 'boolean', 'VnfLcmOpOccs'),
        'isCancelPending': ('is_cancel_pending', 'string', 'VnfLcmOpOccs'),
        'errorPoint': ('error_point', 'number', 'VnfLcmOpOccs'),
        'operationParams': ('operation_params', 'string', 'VnfLcmOpOccs'),
        'error': ('error', 'string', 'VnfLcmOpOccs'),
        'resourceChanges': ('resource_changes', 'string', 'VnfLcmOpOccs'),
        'changedInfo': ('changed_info', 'string', 'VnfLcmOpOccs')
    }

    FLATTEN_ATTRIBUTES = utils.flatten_dict(ALL_ATTRIBUTES.copy())

    SIMPLE_ATTRIBUTES = ['id', 'operationState', 'stateEnteredTime',
                         'startTime', 'vnfInstanceId', 'grantId', 'operation',
                         'isAutomaticInvocation',
                         'isCancelPending', 'errorPoint']

    COMPLEX_ATTRIBUTES = ['error', 'resourceChanges', 'changedInfo',
                          'operationParams', 'changedExtConnectivity']

    @base.remotable
    def create(self):
        updates = self.obj_clone()
        _vnf_lcm_op_occ_create(self._context, updates)

    @base.remotable
    def save(self):
        updates = self.obj_clone()
        _vnf_lcm_op_occ_update(self._context, updates)

    @staticmethod
    def _from_db_object(context, vnf_lcm_op_occ_obj, db_vnf_lcm_op_occ):

        special_fields = ['error',
                          'resource_changes',
                          'changed_info',
                          'changed_ext_connectivity']
        for key in vnf_lcm_op_occ_obj.fields:
            if key in special_fields:
                continue
            setattr(vnf_lcm_op_occ_obj, key, db_vnf_lcm_op_occ.get(key))
        if db_vnf_lcm_op_occ['error']:
            error = ProblemDetails.obj_from_primitive(
                db_vnf_lcm_op_occ['error'], context)
            vnf_lcm_op_occ_obj.error = error
        if db_vnf_lcm_op_occ['resource_changes']:
            resource_changes = ResourceChanges.obj_from_primitive(
                db_vnf_lcm_op_occ['resource_changes'], context)
            vnf_lcm_op_occ_obj.resource_changes = resource_changes
        if db_vnf_lcm_op_occ['changed_info']:
            changed_info = VnfInfoModifications.obj_from_primitive(
                db_vnf_lcm_op_occ['changed_info'], context)
            vnf_lcm_op_occ_obj.changed_info = changed_info
        if db_vnf_lcm_op_occ['changed_ext_connectivity']:
            changed_ext_conn = \
                [objects.ExtVirtualLinkInfo.obj_from_primitive(
                 chg_ext_conn, context) for chg_ext_conn in
                 jsonutils.loads(
                    db_vnf_lcm_op_occ['changed_ext_connectivity'])]
            vnf_lcm_op_occ_obj.changed_ext_connectivity = changed_ext_conn

        vnf_lcm_op_occ_obj._context = context
        vnf_lcm_op_occ_obj.obj_reset_changes()
        return vnf_lcm_op_occ_obj

    @classmethod
    def obj_from_primitive(cls, primitive, context):
        if 'tacker_object.name' in primitive:
            vnf_lcm_op_occ = super(
                VnfLcmOpOcc, cls).obj_from_primitive(
                primitive, context)
        else:
            if 'error' in primitive.keys():
                obj_data = ProblemDetails._from_dict(
                    primitive.get('error'))
                primitive.update({'error': obj_data})
            if 'resource_changes' in primitive.keys():
                obj_data = ResourceChanges._from_dict(
                    primitive.get('resource_changes'))
                primitive.update({'resource_changes': obj_data})
            if 'changed_info' in primitive.keys():
                obj_data = VnfInfoModifications._from_dict(
                    primitive.get('changed_info'))
                primitive.update({'changed_info': obj_data})
            if 'changed_ext_connectivity' in primitive.keys():
                obj_data = [objects.ExtVirtualLinkInfo.obj_from_primitive(
                    chg_ext_conn, context) for chg_ext_conn in
                    primitive.get('changed_ext_connectivity')]
                primitive.update({'changed_ext_connectivity': obj_data})
            vnf_lcm_op_occ = VnfLcmOpOcc._from_dict(primitive)

        return vnf_lcm_op_occ

    @classmethod
    def obj_from_db_obj(cls, context, db_obj):
        return cls._from_db_object(context, cls(), db_obj)

    @classmethod
    def _from_dict(cls, data_dict):
        operation_state = data_dict.get('operation_state')
        state_entered_time = data_dict.get('state_entered_time')
        start_time = data_dict.get('start_time')
        vnf_instance_id = data_dict.get('vnf_instance_id')
        grant_id = data_dict.get('grant_id')
        operation = data_dict.get('operation')
        is_automatic_invocation = data_dict.get('is_automatic_invocation')
        operation_params = data_dict.get('operation_params')
        is_cancel_pending = data_dict.get('is_cancel_pending')
        error = data_dict.get('error')
        resource_changes = data_dict.get('resource_changes')
        changed_info = data_dict.get('changed_info')
        changed_ext_connectivity = data_dict.get('changed_ext_connectivity')
        error_point = data_dict.get('error_point')
        tenant_id = data_dict.get('tenant_id')

        obj = cls(operation_state=operation_state,
                  state_entered_time=state_entered_time,
                  start_time=start_time,
                  vnf_instance_id=vnf_instance_id,
                  grant_id=grant_id,
                  operation=operation,
                  is_automatic_invocation=is_automatic_invocation,
                  operation_params=operation_params,
                  is_cancel_pending=is_cancel_pending,
                  error=error,
                  resource_changes=resource_changes,
                  changed_info=changed_info,
                  changed_ext_connectivity=changed_ext_connectivity,
                  error_point=error_point,
                  tenant_id=tenant_id
                  )

        return obj

    def _get_error(self, include_fields=None):
        key = 'error'
        if key in include_fields:
            return {key: self.error.to_dict()}

    def _get_resource_changes(self, include_fields=None):
        key = 'resourceChanges'
        if key in include_fields:
            return {key: self.resource_changes.to_dict()}

    def _get_changed_info(self, include_fields=None):
        key = 'changedInfo'
        if key in include_fields:
            return {key: self.changed_info.to_dict()}

    def _get_operation_params(self, include_fields=None):
        key = 'operationParams'
        if key in include_fields:
            return {key: self.operation_params}

    def _get_changed_ext_connectivity(self, include_fields=None):
        key = 'changedExtConnectivity'
        return {key: [chg_ext_conn.to_dict() for chg_ext_conn in
                      self.changed_ext_connectivity]}

    def to_dict(self, include_fields=None):
        data = dict()
        if not include_fields:
            include_fields = set(self.FLATTEN_ATTRIBUTES.keys())

        # add simple fields
        to_fields = set(self.SIMPLE_ATTRIBUTES).intersection(include_fields)
        for field in to_fields:
            data[field] = getattr(self, self.FLATTEN_ATTRIBUTES[field][0])

        # add complex attributes
        if self.error:
            error = self._get_error(include_fields=include_fields)
            if error:
                data.update(error)

        if self.resource_changes:
            resource_changes = self._get_resource_changes(
                include_fields=include_fields)
            if resource_changes:
                data.update(resource_changes)

        if self.changed_info:
            changed_info = self._get_changed_info(
                include_fields=include_fields)
            if changed_info:
                data.update(changed_info)

        if self.operation_params:
            operation_params = self._get_operation_params(
                include_fields=include_fields)
            if operation_params:
                data.update(operation_params)

        if self.changed_ext_connectivity:
            changed_ext_connectivity = self._get_changed_ext_connectivity(
                include_fields=include_fields)
            if changed_ext_connectivity:
                data.update(changed_ext_connectivity)

        return data

    @base.remotable_classmethod
    def get_by_id(cls, context, id):
        db_vnf_lcm_op_occs = _vnf_lcm_op_occs_get_by_id(context, id)
        return cls._from_db_object(context, cls(), db_vnf_lcm_op_occs)

    @base.remotable_classmethod
    def get_by_vnf_instance_id(cls, context, id):
        db_vnf_lcm_op_occs = _vnf_lcm_op_occs_get_by_vnf_instance_id(
            context, id)
        return cls._from_db_object(context, cls(), db_vnf_lcm_op_occs)


@base.TackerObjectRegistry.register
class VnfLcmOpOccList(ovoo_base.ObjectListBase, base.TackerObject):

    VERSION = '1.0'

    fields = {
        'objects': fields.ListOfObjectsField('VnfLcmOpOcc')
    }

    @base.remotable_classmethod
    def get_by_filters(cls, context, read_deleted=None, filters=None):
        db_vnf_lcm_op_occs = _vnf_lcm_op_occs_get_by_filters(
            context, read_deleted=read_deleted, filters=filters)
        return _make_vnf_lcm_op_occs_list(context, cls(), db_vnf_lcm_op_occs)


@base.TackerObjectRegistry.register
class ResourceChanges(base.TackerObject,
                     base.TackerPersistentObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'affected_vnfcs': fields.ListOfObjectsField(
            'AffectedVnfc', nullable=True),
        'affected_virtual_links': fields.ListOfObjectsField(
            'AffectedVirtualLink', nullable=True),
        'affected_virtual_storages': fields.ListOfObjectsField(
            'AffectedVirtualStorage', nullable=True)
    }

    @classmethod
    def obj_from_primitive(cls, primitive, context):
        if 'tacker_object.name' in primitive:
            resource_changes = super(
                ResourceChanges, cls).obj_from_primitive(
                primitive, context)
        else:
            rs_dict = jsonutils.loads(primitive)
            if rs_dict.get('affected_vnfcs'):
                obj_data = [AffectedVnfc._from_dict(
                    affected_vnfc) for affected_vnfc in rs_dict.get(
                    'affected_vnfcs', [])]
                rs_dict.update({'affected_vnfcs': obj_data})
            if rs_dict.get('affected_virtual_links'):
                obj_data = [AffectedVirtualLink._from_dict(
                    affected_virtual_link)
                    for affected_virtual_link in rs_dict.get(
                    'affected_virtual_links', [])]
                rs_dict.update({'affected_virtual_links': obj_data})
            if rs_dict.get('affected_virtual_storages'):
                obj_data = [AffectedVirtualStorage._from_dict(
                    affected_virtual_storage)
                    for affected_virtual_storage in rs_dict.get(
                    'affected_virtual_storages', [])]
                rs_dict.update({'affected_virtual_storages': obj_data})
            resource_changes = ResourceChanges._from_dict(rs_dict)

        return resource_changes

    @classmethod
    def _from_dict(cls, data_dict):
        affected_vnfcs = data_dict.get('affected_vnfcs')
        affected_virtual_links = data_dict.get('affected_virtual_links')
        affected_virtual_storages = data_dict.get('affected_virtual_storages')

        obj = cls(affected_vnfcs=affected_vnfcs,
                  affected_virtual_links=affected_virtual_links,
                  affected_virtual_storages=affected_virtual_storages
                  )

        return obj

    def to_dict(self):
        data = {}
        if self.affected_vnfcs:
            affected_vnfcs_list = []
            for affected_vnfc in self.affected_vnfcs:
                affected_vnfcs_list.append(affected_vnfc.to_dict())

            data.update({'affected_vnfcs': affected_vnfcs_list})
        if self.affected_virtual_links:
            affected_virtual_links_list = []
            for affected_virtual_link in self.affected_virtual_links:
                affected_virtual_links_list.append(
                    affected_virtual_link.to_dict())

            data.update(
                {'affected_virtual_links': affected_virtual_links_list})
        if self.affected_virtual_storages:
            affected_virtual_storages_list = []
            for affected_virtual_storage in self.affected_virtual_storages:
                affected_virtual_storages_list.append(
                    affected_virtual_storage.to_dict())

            data.update(
                {'affected_virtual_storages': affected_virtual_storages_list})
        return data


@base.TackerObjectRegistry.register
class ProblemDetails(base.TackerObject,
                     base.TackerPersistentObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'title': fields.StringField(nullable=True, default=''),
        'status': fields.IntegerField(nullable=False),
        'detail': fields.StringField(nullable=False)
    }

    @classmethod
    def obj_from_primitive(cls, primitive, context):
        if 'tacker_object.name' in primitive:
            problem_detail = super(
                ProblemDetails, cls).obj_from_primitive(
                primitive, context)
        else:
            p_dict = jsonutils.loads(primitive)
            problem_detail = ProblemDetails._from_dict(p_dict)

        return problem_detail

    @classmethod
    def _from_dict(cls, data_dict):
        title = data_dict.get('title')
        status = data_dict.get('status')
        detail = data_dict.get('detail')

        obj = cls(title=title,
                  status=status,
                  detail=detail)

        return obj

    def to_dict(self):
        return {'title': self.title,
                'status': self.status,
                'detail': self.detail}


@base.TackerObjectRegistry.register
class AffectedVnfc(base.TackerObject,
                   base.TackerPersistentObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.StringField(nullable=False),
        'vdu_id': fields.StringField(nullable=False),
        'change_type': fields.StringField(nullable=False),
        'compute_resource': fields.ObjectField(
            'ResourceHandle', nullable=False),
        'affected_vnfc_cp_ids':
            fields.ListOfStringsField(nullable=True, default=[]),
        'added_storage_resource_ids':
            fields.ListOfStringsField(nullable=True, default=[]),
        'removed_storage_resource_ids':
            fields.ListOfStringsField(nullable=True, default=[])
    }

    @classmethod
    def obj_from_primitive(cls, primitive, context):
        if 'tacker_object.name' in primitive:
            affected_vnfc = super(
                AffectedVnfc, cls).obj_from_primitive(
                primitive, context)
        else:
            if 'compute_resource' in primitive.keys():
                obj_data = ResourceHandle._from_dict(
                    primitive.get('compute_resource'))
                primitive.update({'compute_resource': obj_data})
            affected_vnfc = AffectedVnfc._from_dict(primitive)

        return affected_vnfc

    @classmethod
    def _from_dict(cls, data_dict):
        id = data_dict.get('id')
        vdu_id = data_dict.get('vdu_id')
        change_type = data_dict.get('change_type')
        compute_resource = ResourceHandle._from_dict(
            data_dict.get('compute_resource'))
        affected_vnfc_cp_ids = data_dict.get('affected_vnfc_cp_ids')
        added_storage_resource_ids = data_dict.get(
            'added_storage_resource_ids')
        removed_storage_resource_ids = data_dict.get(
            'removed_storage_resource_ids')

        obj = cls(id=id,
                  vdu_id=vdu_id,
                  change_type=change_type,
                  compute_resource=compute_resource,
                  affected_vnfc_cp_ids=affected_vnfc_cp_ids,
                  added_storage_resource_ids=added_storage_resource_ids,
                  removed_storage_resource_ids=removed_storage_resource_ids
                  )

        return obj

    def to_dict(self):
        return {
            'id': self.id,
            'vdu_id': self.vdu_id,
            'change_type': self.change_type,
            'compute_resource': self.compute_resource.to_dict(),
            'affected_vnfc_cp_ids': self.affected_vnfc_cp_ids,
            'added_storage_resource_ids': self.added_storage_resource_ids,
            'removed_storage_resource_ids': self.removed_storage_resource_ids}


@base.TackerObjectRegistry.register
class AffectedVirtualLink(base.TackerObject,
                   base.TackerPersistentObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.StringField(nullable=False),
        'vnf_virtual_link_desc_id': fields.StringField(nullable=False),
        'change_type': fields.StringField(nullable=False),
        'network_resource': fields.ObjectField(
            'ResourceHandle', nullable=False)
    }

    @classmethod
    def obj_from_primitive(cls, primitive, context):
        if 'tacker_object.name' in primitive:
            affected_virtual_link = super(
                AffectedVirtualLink, cls).obj_from_primitive(
                primitive, context)
        else:
            if 'network_resource' in primitive.keys():
                obj_data = ResourceHandle._from_dict(
                    primitive.get('network_resource'))
                primitive.update({'network_resource': obj_data})
            affected_virtual_link = AffectedVirtualLink._from_dict(primitive)

        return affected_virtual_link

    @classmethod
    def _from_dict(cls, data_dict):
        id = data_dict.get('id')
        vnf_virtual_link_desc_id = data_dict.get('vnf_virtual_link_desc_id')
        change_type = data_dict.get('change_type')
        network_resource = ResourceHandle._from_dict(
            data_dict.get('network_resource'))

        obj = cls(id=id,
                  vnf_virtual_link_desc_id=vnf_virtual_link_desc_id,
                  change_type=change_type,
                  network_resource=network_resource
                  )

        return obj

    def to_dict(self):
        return {'id': self.id,
                'vnf_virtual_link_desc_id': self.vnf_virtual_link_desc_id,
                'change_type': self.change_type,
                'network_resource': self.network_resource.to_dict()}


@base.TackerObjectRegistry.register
class AffectedVirtualStorage(base.TackerObject,
                   base.TackerPersistentObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.StringField(nullable=False),
        'virtual_storage_desc_id': fields.StringField(nullable=False),
        'change_type': fields.StringField(nullable=False),
        'storage_resource': fields.ObjectField(
            'ResourceHandle', nullable=False)
    }

    @classmethod
    def obj_from_primitive(cls, primitive, context):
        if 'tacker_object.name' in primitive:
            affected_virtual_storage = super(
                AffectedVirtualStorage, cls).obj_from_primitive(
                primitive, context)
        else:
            if 'storage_resource' in primitive.keys():
                obj_data = ResourceHandle._from_dict(
                    primitive.get('storage_resource'))
                primitive.update({'storage_resource': obj_data})
            affected_virtual_storage = AffectedVirtualStorage._from_dict(
                primitive)

        return affected_virtual_storage

    @classmethod
    def _from_dict(cls, data_dict):
        id = data_dict.get('id')
        virtual_storage_desc_id = data_dict.get('virtual_storage_desc_id')
        change_type = data_dict.get('change_type')
        storage_resource = ResourceHandle._from_dict(
            data_dict.get('storage_resource'))

        obj = cls(id=id,
                  virtual_storage_desc_id=virtual_storage_desc_id,
                  change_type=change_type,
                  storage_resource=storage_resource
                  )

        return obj

    def to_dict(self):
        return {'id': self.id,
                'virtual_storage_desc_id': self.virtual_storage_desc_id,
                'change_type': self.change_type,
                'storage_resource': self.storage_resource.to_dict()}


@base.TackerObjectRegistry.register
class VnfInfoModifications(base.TackerObject,
                   base.TackerPersistentObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'vnf_instance_name': fields.StringField(nullable=True),
        'vnf_instance_description': fields.StringField(nullable=True),
        'metadata': fields.DictOfStringsField(nullable=True, default={}),
        'vim_connection_info': fields.ListOfObjectsField(
            'VimConnectionInfo', nullable=True, default=[]),
        'vim_connection_info_delete_ids':
            fields.ListOfStringsField(nullable=True, default=[]),
        'vnf_pkg_id': fields.StringField(nullable=True, default=None),
        'vnfd_id': fields.StringField(nullable=True),
        'vnf_provider': fields.StringField(nullable=True),
        'vnf_product_name': fields.StringField(nullable=True),
        'vnf_software_version': fields.StringField(nullable=True),
        'vnfd_version': fields.StringField(nullable=True)
    }

    @classmethod
    def obj_from_primitive(cls, primitive, context):
        if 'tacker_object.name' in primitive:
            vnf_info_modifications = super(
                VnfInfoModifications, cls).obj_from_primitive(
                primitive, context)
        else:
            if isinstance(primitive, str):
                primitive = jsonutils.loads(primitive)

            if 'vim_connection_info' in primitive.keys():
                obj_data = [objects.VimConnectionInfo._from_dict(
                    vim_conn) for vim_conn in primitive.get(
                    'vim_connection_info', [])]
                primitive.update({'vim_connection_info': obj_data})
            vnf_info_modifications = VnfInfoModifications._from_dict(primitive)

        return vnf_info_modifications

    @classmethod
    def _from_dict(cls, data_dict):
        vnf_instance_name = data_dict.get('vnf_instance_name')
        vnf_instance_description = data_dict.get('vnf_instance_description')
        metadata = data_dict.get('metadata')
        vim_connection_info = data_dict.get('vim_connection_info', [])
        vim_connection_info_delete_ids = data_dict.get(
            'vim_connection_info_delete_ids')
        vnf_pkg_id = data_dict.get('vnf_pkg_id')
        vnfd_id = data_dict.get('vnfd_id')
        vnf_provider = data_dict.get('vnf_provider')
        vnf_product_name = data_dict.get('vnf_product_name')
        vnf_software_version = data_dict.get('vnf_software_version')
        vnfd_version = data_dict.get('vnfd_version')

        obj = cls(
            vnf_instance_name=vnf_instance_name,
            vnf_instance_description=vnf_instance_description,
            metadata=metadata,
            vim_connection_info=vim_connection_info,
            vim_connection_info_delete_ids=vim_connection_info_delete_ids,
            vnf_pkg_id=vnf_pkg_id,
            vnfd_id=vnfd_id,
            vnf_provider=vnf_provider,
            vnf_product_name=vnf_product_name,
            vnf_software_version=vnf_software_version,
            vnfd_version=vnfd_version)

        return obj

    def to_dict(self):
        """For the attributes of this class, if an attribute exists and is not

        null, it means that the attribute has been modified. This method

        returns a dictionary containing the modified attributes.
        """
        dct = {}
        for field in self.fields:
            if field in self and getattr(self, field):
                value = getattr(self, field)
                # Since the type of vim_connection_info is ListOfObjectsField,
                # the objects in vim_connection_info also need to be converted
                # into dictionary, otherwise an error will occur
                # when serialized.
                if field == "vim_connection_info":
                    value = [vim_conn.to_dict() for vim_conn in value]
                dct[field] = value
        return dct


@base.TackerObjectRegistry.register
class ResourceHandle(base.TackerObject,
                     base.TackerPersistentObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'vim_connection_id': fields.StringField(nullable=True,
                                                default=None),
        'resource_id': fields.StringField(nullable=False, default=""),
        'vim_level_resource_type': fields.StringField(nullable=True,
                                                      default=None)
    }

    @classmethod
    def obj_from_primitive(cls, primitive, context):
        if 'tacker_object.name' in primitive:
            resource_handle = super(
                ResourceHandle, cls).obj_from_primitive(
                primitive, context)
        else:
            resource_handle = ResourceHandle._from_dict(primitive)

        return resource_handle

    @classmethod
    def _from_dict(cls, data_dict):
        LOG.debug("data_dict %s", data_dict)
        vim_connection_id = data_dict.get('vim_connection_id')
        resource_id = data_dict.get('resource_id', "")
        vim_level_resource_type = data_dict.get('vim_level_resource_type')

        obj = cls(vim_connection_id=vim_connection_id,
                  resource_id=resource_id,
                  vim_level_resource_type=vim_level_resource_type)

        return obj

    def to_dict(self):
        return {'vim_connection_id': self.vim_connection_id,
                'resource_id': self.resource_id,
                'vim_level_resource_type': self.vim_level_resource_type}
