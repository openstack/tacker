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
from sqlalchemy.sql import text

from tacker.common import exceptions
import tacker.conf
from tacker.db import api as db_api
from tacker.db.db_sqlalchemy import api
from tacker.db.db_sqlalchemy import models
from tacker.objects import base
from tacker.objects import fields

_NO_DATA_SENTINEL = object()

LOG = logging.getLogger(__name__)
CONF = tacker.conf.CONF


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
            " t1.id,t1.callback_uri,t1.subscription_authentication,t2.filter "
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
            " t1.id,t1.callback_uri,t1.subscription_authentication,t2.filter "
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
        "t1.id,t1.callback_uri,t2.filter "
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
                                  operation_type=None
                                  ):

    sql = ("select "
          "t1.id "
           "from "
           "vnf_lcm_subscriptions t1, "
           "(select subscription_uuid from vnf_lcm_filters "
           "where ")

    if notification_type:
        sql = (sql + " JSON_CONTAINS(notification_types, '" +
               _make_list(notification_type) + "') ")
    else:
        sql = sql + " notification_types_len=0 "
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


def _add_filter_data(context, subscription_id, filter):
    with db_api.context_manager.writer.using(context):

        new_entries = []
        new_entries.append({"subscription_uuid": subscription_id,
                            "filter": filter})

        context.session.execute(
            models.VnfLcmFilters.__table__.insert(None),
            new_entries)


@db_api.context_manager.writer
def _vnf_lcm_subscriptions_create(context, values, filter):
    with db_api.context_manager.writer.using(context):

        new_entries = []
        if 'subscription_authentication' in values:
            new_entries.append({"id": values.id,
                                "callback_uri": values.callback_uri,
                                "subscription_authentication":
                                    values.subscription_authentication})
        else:
            new_entries.append({"id": values.id,
                                "callback_uri": values.callback_uri})

        context.session.execute(
            models.VnfLcmSubscriptions.__table__.insert(None),
            new_entries)

        callbackUri = values.callback_uri
        if filter:
            notification_type = filter.get('notificationTypes')
            operation_type = filter.get('operationTypese')

            vnf_lcm_subscriptions_id = _vnf_lcm_subscriptions_id_get(
                context,
                callbackUri,
                notification_type=notification_type,
                operation_type=operation_type)

            if vnf_lcm_subscriptions_id:
                raise Exception("303" + vnf_lcm_subscriptions_id.id.decode())

            _add_filter_data(context, values.id, filter)

        else:
            vnf_lcm_subscriptions_id = _vnf_lcm_subscriptions_id_get(context,
                                            callbackUri)

            if vnf_lcm_subscriptions_id:
                raise Exception("303" + vnf_lcm_subscriptions_id.id.decode())
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


@base.TackerObjectRegistry.register
class LccnSubscriptionRequest(base.TackerObject, base.TackerPersistentObject):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.UUIDField(nullable=False),
        'callback_uri': fields.StringField(nullable=False),
        'subscription_authentication':
            fields.DictOfStringsField(nullable=True),
        'filter': fields.StringField(nullable=True)
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
