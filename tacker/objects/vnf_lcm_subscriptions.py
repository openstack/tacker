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
from oslo_serialization import jsonutils as json
from oslo_utils import timeutils
from oslo_versionedobjects import base as ovoo_base
from sqlalchemy.orm import joinedload
from sqlalchemy.sql import text

from tacker.common import exceptions
from tacker.common import utils
from tacker.common.utils import convert_string_to_snakecase
import tacker.conf
from tacker.db import api as db_api
from tacker.db.db_sqlalchemy import api
from tacker.db.db_sqlalchemy import models
from tacker import objects
from tacker.objects import base
from tacker.objects import common
from tacker.objects import fields

_NO_DATA_SENTINEL = object()

LOG = logging.getLogger(__name__)
CONF = tacker.conf.CONF


VNF_INSTANCE_SUBSCRIPTION_FILTER = [
    "vnfdIds", "vnfProvider", "vnfProductName",
    "vnfSoftwareVersion", "vnfdVersions", "vnfInstanceIds",
    "vnfInstanceNames"
]


VNF_INSTANCE_SUBSCRIPTION_FILTER_LISTS = [
    "vnfdIds", "vnfdVersions", "vnfInstanceIds", "vnfInstanceNames"
]


def _get_vnf_subscription_filter_values(vnf_subscription_filter):
    vnfd_ids = vnf_subscription_filter.get('vnfdIds', [])
    vnf_instance_ids = vnf_subscription_filter.get('vnfInstanceIds', [])
    vnf_instance_names = vnf_subscription_filter.get('vnfInstanceNames', [])

    vnfd_products_from_providers = vnf_subscription_filter.get(
        'vnfProductsFromProviders', [])

    vnf_provider = ""
    vnf_product_name = ""
    vnf_software_version = ""
    vnfd_versions = []
    if vnfd_products_from_providers:
        vnfd_products_from_providers = vnfd_products_from_providers[0]
        vnf_provider = vnfd_products_from_providers.get('vnfProvider', "")
        vnf_products = vnfd_products_from_providers.get('vnfProducts', [])

        if vnf_products:
            vnf_product_name = vnf_products[0].get('vnfProductName', "")
            versions = vnf_products[0].get('versions', [])
            if versions:
                vnf_software_version = \
                    versions[0].get('vnfSoftwareVersion', "")
                vnfd_versions = versions[0].get('vnfdVersions', [])

    vnf_subscription_array = [
        {'vnfdIds': vnfd_ids},
        {'vnfInstanceIds': vnf_instance_ids},
        {'vnfInstanceNames': vnf_instance_names},
        {'vnfProvider': vnf_provider},
        {'vnfProductName': vnf_product_name},
        {'vnfSoftwareVersion': vnf_software_version},
        {'vnfdVersions': vnfd_versions}]

    return vnf_subscription_array


def _make_list(value):
    if isinstance(value, list):
        res = ""
        for i in range(len(value)):
            t = "\"{}\"".format(value[i])
            if i == 0:
                res = str(t)
            else:
                res = "{0},{1}".format(res, t)

        res = "[{}]".format(res)
    else:
        res = "[\"{}\"]".format(str(value))
    return res


@db_api.context_manager.reader
def _vnf_lcm_subscriptions_get(context,
                               notification_type,
                               operation_type=None
                               ):

    if notification_type == 'VnfLcmOperationOccurrenceNotification':
        sql = (
            "select"
            " t1.id,t1.callback_uri,t1.authentication,"
            " t1.tenant_id, t2.filter "
            " from "
            " vnf_lcm_subscriptions t1, "
            " (select distinct subscription_uuid,filter from vnf_lcm_filters "
            " where "
            " (notification_types_len = 0 \
                or JSON_CONTAINS(notification_types, '" +
            _make_list(notification_type) +
            "')) "
            " and "
            " (operation_types_len = 0 or JSON_CONTAINS(operation_types, '" +
            _make_list(operation_type) +
            "')) "
            " order by "
            "         notification_types_len desc,"
            "         operation_types_len desc"
            ") t2 "
            " where "
            " t1.id=t2.subscription_uuid "
            " and t1.deleted=0")
    else:
        sql = (
            "select"
            " t1.id,t1.callback_uri,t1.authentication,"
            " t1.tenant_id, t2.filter "
            " from "
            " vnf_lcm_subscriptions t1, "
            " (select distinct subscription_uuid,filter from vnf_lcm_filters "
            " where "
            " (notification_types_len = 0 or \
                JSON_CONTAINS(notification_types, '" +
            _make_list(notification_type) +
            "')) "
            " order by "
            "         notification_types_len desc,"
            "         operation_types_len desc"
            ") t2 "
            " where "
            " t1.id=t2.subscription_uuid "
            " and t1.deleted=0")

    result_list = []
    result = context.session.execute(sql)
    for line in result:
        result_list.append(line)
    return result_list


@db_api.context_manager.reader
def _vnf_lcm_subscriptions_show(context, subscriptionId):

    sql = text(
        "select "
        "t1.id,t1.callback_uri,t1.tenant_id,t2.filter "
        "from vnf_lcm_subscriptions t1, "
        "(select distinct subscription_uuid,filter from vnf_lcm_filters) t2 "
        "where t1.id = t2.subscription_uuid "
        "and deleted = 0 "
        "and t1.id = :subsc_id")
    result_line = ""
    try:
        result = context.session.execute(sql, {'subsc_id': subscriptionId})
        for line in result:
            result_line = line
    except exceptions.NotFound:
        return ''
    except Exception as e:
        raise e
    return result_line


@db_api.context_manager.reader
def _vnf_lcm_subscriptions_all(context):

    sql = text(
        "select "
        "t1.id,t1.callback_uri,t2.filter "
        "from vnf_lcm_subscriptions t1, "
        "(select distinct subscription_uuid,filter from vnf_lcm_filters) t2 "
        "where t1.id = t2.subscription_uuid "
        "and deleted = 0 ")
    result_list = []
    try:
        result = context.session.execute(sql)
        for line in result:
            result_list.append(line)
    except Exception as e:
        raise e

    return result_list


@db_api.context_manager.reader
def _get_by_subscriptionid(context, subscriptionsId):

    sql = text("select id "
             "from vnf_lcm_subscriptions "
             "where id = :subsc_id "
             "and deleted = 0 ")
    try:
        result = context.session.execute(sql, {'subsc_id': subscriptionsId})
    except exceptions.NotFound:
        return ''
    except Exception as e:
        raise e

    return result


@db_api.context_manager.reader
def _vnf_lcm_subscriptions_id_get(context,
                                  callbackUri,
                                  notification_type=None,
                                  operation_type=None,
                                  operation_state=None,
                                  vnf_instance_subscription_filter=None
                                  ):

    sql = ("select "
          "t1.id "
           "from "
           "vnf_lcm_subscriptions t1, "
           "(select subscription_uuid from vnf_lcm_filters "
           "where ")

    if vnf_instance_subscription_filter:
        included_in_filter = []
        column_list = _get_vnf_subscription_filter_values(
            vnf_instance_subscription_filter)

        sql_lst = [sql]
        for column in column_list:
            for key in column:
                if key in VNF_INSTANCE_SUBSCRIPTION_FILTER:
                    value = column[key]
                    if key in VNF_INSTANCE_SUBSCRIPTION_FILTER_LISTS:
                        if value:
                            value = _make_list(value)
                            sql_lst.append(
                                " JSON_CONTAINS({}, '{}') and ".format(
                                    convert_string_to_snakecase(key), value))
                        else:
                            sql_lst.append(" {}_len=0 and ".format(
                                convert_string_to_snakecase(key)))
                    else:
                        sql_lst.append(" {}='{}' and ".format(
                            convert_string_to_snakecase(key), value))

                    included_in_filter.append(key)
        sql = ''.join(sql_lst)

        not_included_in_filter = list(
            set(VNF_INSTANCE_SUBSCRIPTION_FILTER_LISTS) -
            set(included_in_filter))

        # items not being searched for is excluded by adding
        # <name>_len=0 to the sql query
        for key in not_included_in_filter:
            sql = sql + " {}_len=0 and ".format(
                convert_string_to_snakecase(key))

    if notification_type:
        sql = (sql + " JSON_CONTAINS(notification_types, '" +
               _make_list(notification_type) + "') ")
    else:
        sql = sql + " notification_types_len=0 "
    sql = sql + "and "

    if operation_state:
        sql = (sql + " JSON_CONTAINS(operation_states, '" +
               _make_list(operation_state) + "') ")
    else:
        sql = sql + " operation_states_len=0 "
    sql = sql + "and "

    if operation_type:
        sql = sql + " JSON_CONTAINS(operation_types, '" + \
            _make_list(operation_type) + "') "
    else:
        sql = sql + " operation_types_len=0 "
    sql = (
        sql +
        ") t2 where t1.id=t2.subscription_uuid and t1.callback_uri= '" +
        callbackUri +
        "' and t1.deleted=0 ")
    LOG.debug("sql[%s]" % sql)

    try:
        result = context.session.execute(sql)
        for line in result:
            return line
    except exceptions.NotFound:
        return ''
    except Exception as exc:
        LOG.error("SQL Error: %s" % str(exc))
        return ''


def _add_filter_data(context, subscription_id, filter):
    with db_api.context_manager.writer.using(context):

        vnf_products_from_providers = (
            filter.get('vnfInstanceSubscriptionFilter', {})
            .get('vnfProductsFromProviders'))

        if vnf_products_from_providers:
            vnf_products_from_providers = vnf_products_from_providers[0]

        new_entries = []
        new_entries.append({"subscription_uuid": subscription_id,
                            "filter": filter,
                            "vnf_products_from_providers":
                                vnf_products_from_providers})

        context.session.execute(
            models.VnfLcmFilters.__table__.insert(None),
            new_entries)


@db_api.context_manager.reader
def _vnf_lcm_subscription_list_by_filters(context,
        read_deleted=None, filters=None, nextpage_opaque_marker=None):
    query = api.model_query(context, models.VnfLcmSubscriptions,
                            read_deleted=read_deleted,
                            project_only=True)
    binary_columns = ['notification_types', 'operation_types']

    if filters:
        filter_data = json.dumps(filters)
        if 'ChangeNotificationsFilter' in filter_data:
            query = query.join(models.VnfLcmFilters)

        if 'and' in filters:
            filters_and = []
            for filter in filters['and']:
                if filter['field'] in binary_columns:
                    converted_value = utils.str_to_bytes(filter['value'])
                    filter['value'] = converted_value
                filters_and.append(filter)

            filters = {'and': filters_and}
        else:
            if filters['field'] in binary_columns:
                converted_value = utils.str_to_bytes(filters['value'])
                filters.update({'value': converted_value})

        query = common.apply_filters(query, filters)

    if nextpage_opaque_marker:
        start_offset = CONF.vnf_lcm.subscription_num * nextpage_opaque_marker
        return query.order_by(
            models.VnfLcmSubscriptions.created_at).limit(
                CONF.vnf_lcm.subscription_num + 1).offset(
                    start_offset).all()
    else:
        return query.order_by(models.VnfLcmSubscriptions.created_at).all()


@db_api.context_manager.writer
def _vnf_lcm_subscriptions_create(context, values, filter):
    with db_api.context_manager.writer.using(context):

        new_entries = []
        if 'authentication' in values:
            new_entries.append({"id": values.id,
                                "callback_uri": values.callback_uri,
                                "authentication":
                                    values.authentication,
                                "tenant_id": values.tenant_id})
        else:
            new_entries.append({"id": values.id,
                                "callback_uri": values.callback_uri,
                                "tenant_id": values.tenant_id})

        context.session.execute(
            models.VnfLcmSubscriptions.__table__.insert(None),
            new_entries)

        callbackUri = values.callback_uri
        if filter:
            notification_type = filter.get('notificationTypes')
            operation_type = filter.get('operationTypes')
            operation_state = filter.get('operationStates')
            subscription_filter = filter.get('vnfInstanceSubscriptionFilter')

            vnf_lcm_subscriptions_id = _vnf_lcm_subscriptions_id_get(
                context,
                callbackUri,
                notification_type=notification_type,
                operation_type=operation_type,
                operation_state=operation_state,
                vnf_instance_subscription_filter=subscription_filter)

            if vnf_lcm_subscriptions_id:
                raise exceptions.SeeOther(message=vnf_lcm_subscriptions_id.id)

            _add_filter_data(context, values.id, filter)

        else:
            vnf_lcm_subscriptions_id = _vnf_lcm_subscriptions_id_get(context,
                                            callbackUri)

            if vnf_lcm_subscriptions_id:
                raise exceptions.SeeOther(message=vnf_lcm_subscriptions_id.id)
            _add_filter_data(context, values.id, {})

    return values


@db_api.context_manager.writer
def _destroy_vnf_lcm_subscription(context, subscriptionId):
    now = timeutils.utcnow()
    updated_values = {'deleted': 1,
                      'deleted_at': now}
    try:
        api.model_query(context, models.VnfLcmSubscriptions). \
            filter_by(id=subscriptionId). \
            update(updated_values, synchronize_session=False)
    except Exception as e:
        raise e


@db_api.context_manager.reader
def _subscription_get_by_id(context, subscription_uuid, columns_to_join=None):

    query = api.model_query(context, models.VnfLcmSubscriptions,
                            read_deleted="no", project_only=True). \
        filter_by(id=subscription_uuid)

    if columns_to_join:
        for column in columns_to_join:
            query = query.options(joinedload(column))

    result = query.first()

    if not result:
        raise exceptions.NotFound(resource='Subscription',
            id=subscription_uuid)

    return result


def _make_subscription_list(context, subscription_list, db_subscription_list,
                            expected_attrs=None):
    subscription_cls = LccnSubscription

    subscription_list.objects = []
    for db_subscription in db_subscription_list:
        subscription_obj = subscription_cls._from_db_object(
            context, subscription_cls(context), db_subscription,
            expected_attrs=expected_attrs)
        subscription_list.objects.append(subscription_obj)

    subscription_list.obj_reset_changes()
    return subscription_list


@base.TackerObjectRegistry.register
class LccnSubscriptionRequest(base.TackerObject, base.TackerPersistentObject):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.UUIDField(nullable=False),
        'callback_uri': fields.StringField(nullable=False),
        # TODO(YiFeng) define SubscriptionAuthentication object
        'authentication':
            fields.StringField(nullable=True),
        'filter': fields.StringField(nullable=True),
        'tenant_id': fields.StringField(nullable=False)
    }

    @base.remotable
    def create(self, filter):
        updates = self.obj_clone()
        db_vnf_lcm_subscriptions = _vnf_lcm_subscriptions_create(
            self._context, updates, filter)

        LOG.debug(
            'test_log: db_vnf_lcm_subscriptions %s' %
            db_vnf_lcm_subscriptions)

        return db_vnf_lcm_subscriptions

    @base.remotable_classmethod
    def vnf_lcm_subscriptions_show(cls, context, subscriptionId):
        try:
            vnf_lcm_subscriptions = _vnf_lcm_subscriptions_show(
                context, subscriptionId)
        except Exception as e:
            raise e
        return vnf_lcm_subscriptions

    @base.remotable_classmethod
    def vnf_lcm_subscriptions_list(cls, context):
        # get vnf_lcm_subscriptions data
        try:
            vnf_lcm_subscriptions = _vnf_lcm_subscriptions_all(context)
        except Exception as e:
            raise e

        return vnf_lcm_subscriptions

    @base.remotable_classmethod
    def vnf_lcm_subscriptions_get(cls, context,
                                  notification_type,
                                  operation_type=None):
        return _vnf_lcm_subscriptions_get(context,
                                          notification_type,
                                          operation_type)

    @base.remotable_classmethod
    def destroy(cls, context, subscriptionId):
        try:
            get_subscriptionid = _get_by_subscriptionid(
                context, subscriptionId)
        except Exception as e:
            raise e

        if not get_subscriptionid:
            return 404

        try:
            _destroy_vnf_lcm_subscription(context, subscriptionId)
        except Exception as e:
            raise e

        return 204


@base.TackerObjectRegistry.register
class ChangeNotificationsFilter(
        base.TackerObject, base.TackerPersistentObject):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.UUIDField(nullable=False),
        'subscription_uuid': fields.UUIDField(nullable=False),
        'filter': fields.StringField(nullable=True),
        'vnf_products_from_providers':
            fields.StringField(nullable=True),
        'vnfd_ids': fields.StringField(nullable=True),
        'vnfd_ids_len': fields.IntegerField(
            nullable=True, default=0),
        'vnf_provider': fields.StringField(nullable=True),
        'vnf_product_name': fields.StringField(nullable=True),
        'vnf_software_version': fields.StringField(nullable=True),
        'vnfd_versions': fields.StringField(nullable=True),
        'vnfd_versions_len': fields.IntegerField(
            nullable=True, default=0),
        'vnf_instance_ids': fields.StringField(nullable=True),
        'vnf_instance_ids_len': fields.IntegerField(
            nullable=True, default=0),
        'vnf_instance_names': fields.StringField(nullable=True),
        'vnf_instance_names_len': fields.IntegerField(
            nullable=True, default=0),
        'notification_types': fields.StringField(nullable=True),
        'notification_types_len': fields.IntegerField(
            nullable=True, default=0),
        'operation_types': fields.StringField(nullable=True),
        'operation_types_len': fields.IntegerField(
            nullable=True, default=0),
        'operation_states': fields.StringField(nullable=True),
        'operation_states_len': fields.IntegerField(
            nullable=True, default=0),
        'tenant_id': fields.StringField(nullable=False),
    }


@base.TackerObjectRegistry.register
class ChangeNotificationsFilterList(
        ovoo_base.ObjectListBase, base.TackerObject):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'objects': fields.ListOfObjectsField('ChangeNotificationsFilter')
    }


@base.TackerObjectRegistry.register
class LccnSubscription(base.TackerObject, base.TackerPersistentObject):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.UUIDField(nullable=False),
        'callback_uri': fields.StringField(nullable=False),
        'filter': fields.ObjectField(
            'ChangeNotificationsFilter', nullable=True),
    }

    ALL_ATTRIBUTES = {
        'id': ('id', 'uuid',
            'VnfLcmSubscriptions'),
        'vnfdIds': ('vnfd_ids', 'string',
            'VnfLcmFilters'),
        'vnfProvider': ('vnf_provider', 'string',
            'VnfLcmFilters'),
        'vnfProductName': ('vnf_product_name', 'string',
            'VnfLcmFilters'),
        'vnfSoftwareVersion': ('vnf_software_version', 'string',
            'VnfLcmFilters'),
        'vnfdVersions': ('vnfd_versions', 'string',
            'VnfLcmFilters'),
        'vnfInstanceIds': ('vnf_instance_ids', 'string',
            'VnfLcmFilters'),
        'vnfInstanceNames': ('vnf_instance_names', 'string',
            'VnfLcmFilters'),
        'notificationTypes': ('notification_types', 'string',
            'VnfLcmFilters'),
        'operationTypes': ('operation_types', 'string',
            'VnfLcmFilters'),
        'operationStates': ('operation_states', 'string',
            'VnfLcmFilters'),
        'callbackUri': ('callback_uri', 'string',
            'VnfLcmSubscriptions'),
        'tenantId': ('tenant_id', 'string',
            'VnfLcmSubscriptions'),
    }

    FLATTEN_ATTRIBUTES = utils.flatten_dict(ALL_ATTRIBUTES.copy())

    @staticmethod
    def _from_db_object(context, subscription, db_subscription,
                        expected_attrs=None):
        expected_attrs = expected_attrs or ['filter']

        subscription._context = context

        for key in subscription.fields:
            if key in ['filter']:
                continue
            db_key = key
            setattr(subscription, key, db_subscription[db_key])

        subscription._context = context
        subscription._extra_attributes_from_db_object(
            subscription, db_subscription, expected_attrs)

        subscription.obj_reset_changes()
        return subscription

    @staticmethod
    def _extra_attributes_from_db_object(subscription, db_subscription,
                                         expected_attrs=None):
        """Method to help with migration of extra attributes to objects."""

        if expected_attrs is None:
            expected_attrs = ['filter']

        if 'filter' in expected_attrs:
            subscription._load_subscription_filter(
                db_subscription.get('filter'))

    def _load_subscription_filter(self, db_filter=_NO_DATA_SENTINEL):
        if db_filter is _NO_DATA_SENTINEL:
            subscription = self.get_by_id(
                self._context, self.id,
                expected_attrs=['filter'])
            if 'filter' in subscription:
                self.filter = \
                    subscription.filter
                self.filter.obj_reset_changes(recursive=True)
                self.obj_reset_changes(['filter'])
            else:
                self.filter = \
                    objects.ChangeNotificationsFilterList(objects=[])
        elif db_filter:
            self.filter = base.obj_make_list(
                self._context, objects.ChangeNotificationsFilterList(
                    self._context), objects.ChangeNotificationsFilter,
                db_filter)
            self.obj_reset_changes(['filter'])

    @base.remotable_classmethod
    def get_by_id(cls, context, id, expected_attrs=None):
        db_subscription = _subscription_get_by_id(
            context, id, columns_to_join=expected_attrs)
        return cls._from_db_object(context, cls(), db_subscription,
                                   expected_attrs=expected_attrs)


@base.TackerObjectRegistry.register
class LccnSubscriptionList(ovoo_base.ObjectListBase, base.TackerObject):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'objects': fields.ListOfObjectsField('LccnSubscription')
    }

    @base.remotable_classmethod
    def get_by_filters(cls, context, read_deleted=None,
                       filters=None, nextpage_opaque_marker=None):

        db_subscriptions = _vnf_lcm_subscription_list_by_filters(context,
                                read_deleted=read_deleted,
                                filters=filters,
                                nextpage_opaque_marker=nextpage_opaque_marker)
        return _make_subscription_list(context, cls(), db_subscriptions)
