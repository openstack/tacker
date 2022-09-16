# Copyright (C) 2022 Fujitsu
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

from datetime import datetime

from oslo_log import log as logging
from oslo_utils import uuidutils

from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.common import fm_subscription_utils as subsc_utils
from tacker.sol_refactored.common import vnf_instance_utils as inst_utils
from tacker.sol_refactored import objects


LOG = logging.getLogger(__name__)  # not used at the moment


def get_alarm(context, alarm_id):
    alarm = objects.AlarmV1.get_by_id(context, alarm_id)
    if alarm is None:
        raise sol_ex.AlarmNotFound(alarm_id=alarm_id)
    return alarm


def get_alarms_all(context, marker=None):
    return objects.AlarmV1.get_all(context, marker)


def get_not_cleared_alarms(context, inst_id):
    return objects.AlarmV1.get_by_filter(context, managedObjectId=inst_id)


def alarm_href(alarm_id, endpoint):
    return f"{endpoint}/vnffm/v1/alarms/{alarm_id}"


def make_alarm_links(alarm, endpoint):
    links = objects.AlarmV1_Links()
    links.self = objects.Link(href=alarm_href(alarm.id, endpoint))
    links.objectInstance = objects.Link(
        href=inst_utils.inst_href(alarm.managedObjectId, endpoint))

    return links


def make_alarm_notif_data(subsc, alarm, endpoint):
    if alarm.obj_attr_is_set('alarmClearedTime'):
        notif_data = objects.AlarmClearedNotificationV1(
            id=uuidutils.generate_uuid(),
            notificationType="AlarmClearedNotification",
            subscriptionId=subsc.id,
            timeStamp=datetime.utcnow(),
            alarmId=alarm.id,
            alarmClearedTime=alarm.alarmClearedTime,
            _links=objects.AlarmClearedNotificationV1_Links(
                alarm=objects.NotificationLink(
                    href=alarm_href(alarm.id, endpoint)),
                subscription=objects.NotificationLink(
                    href=subsc_utils.subsc_href(subsc.id, endpoint))
            )
        )
    else:
        notif_data = objects.AlarmNotificationV1(
            id=uuidutils.generate_uuid(),
            notificationType="AlarmNotification",
            subscriptionId=subsc.id,
            timeStamp=datetime.utcnow(),
            alarm=alarm,
            _links=objects.AlarmNotificationV1_Links(
                subscription=objects.NotificationLink(
                    href=subsc_utils.subsc_href(subsc.id, endpoint))
            )
        )
    return notif_data
