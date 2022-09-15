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


import threading

from oslo_log import log as logging

from tacker.sol_refactored.api import api_version
from tacker.sol_refactored.common import config
from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.common import http_client
from tacker.sol_refactored.common import subscription_utils as subsc_utils
from tacker.sol_refactored import objects


LOG = logging.getLogger(__name__)

CONF = config.CONF

TEST_NOTIFICATION_TIMEOUT = 20  # seconds


def get_subsc(context, subsc_id):
    subsc = objects.FmSubscriptionV1.get_by_id(context, subsc_id)
    if subsc is None:
        raise sol_ex.FmSubscriptionNotFound(subsc_id=subsc_id)
    return subsc


def get_subsc_all(context, marker=None):
    return objects.FmSubscriptionV1.get_all(context, marker)


def subsc_href(subsc_id, endpoint):
    return f"{endpoint}/vnffm/v1/subscriptions/{subsc_id}"


def _get_notification_auth_handle(subsc):
    if not subsc.obj_attr_is_set('authentication'):
        return http_client.NoAuthHandle()

    if subsc.authentication.obj_attr_is_set('paramsBasic'):
        param = subsc.authentication.paramsBasic
        return http_client.BasicAuthHandle(param.userName, param.password)

    if subsc.authentication.obj_attr_is_set(
            'paramsOauth2ClientCredentials'):
        param = subsc.authentication.paramsOauth2ClientCredentials
        return http_client.OAuth2AuthHandle(None,
            param.tokenEndpoint, param.clientId, param.clientPassword)

    # not reach here


def async_call(func):
    def inner(*args, **kwargs):
        th = threading.Thread(target=func, args=args,
                kwargs=kwargs, daemon=True)
        th.start()
    return inner


@async_call
def send_notification(subsc, notif_data):
    auth_handle = _get_notification_auth_handle(subsc)
    client = http_client.HttpClient(auth_handle,
        version=api_version.CURRENT_FM_VERSION)

    url = subsc.callbackUri
    try:
        resp, _ = client.do_request(
            url, "POST", expected_status=[204], body=notif_data)
    except sol_ex.SolException:
        # it may occur if test_notification was not executed.
        LOG.exception("send_notification failed")

    if resp.status_code != 204:
        LOG.error(f"send_notification failed: {resp.status_code}")


def test_notification(subsc):
    auth_handle = _get_notification_auth_handle(subsc)
    client = http_client.HttpClient(auth_handle,
        version=api_version.CURRENT_FM_VERSION,
        timeout=TEST_NOTIFICATION_TIMEOUT)

    url = subsc.callbackUri
    try:
        resp, _ = client.do_request(url, "GET", expected_status=[204])
    except sol_ex.SolException as e:
        # any sort of error is considered. avoid 500 error.
        raise sol_ex.TestNotificationFailed() from e

    if resp.status_code != 204:
        raise sol_ex.TestNotificationFailed()


def get_matched_subscs(context, inst, notif_type, alarm):
    subscs = []
    for subsc in get_subsc_all(context):
        # subsc: FmSubscription

        if not subsc.obj_attr_is_set('filter'):
            # no filter. get it.
            subscs.append(subsc)
            continue

        # subsc.filter: FmNotificationsFilter
        # - vnfInstanceSubscriptionFilter 0..1
        # - notificationTypes 0..N
        # - faultyResourceTypes 0..N
        # - perceivedSeverities 0..N
        # - eventTypes 0..N
        # - probableCauses 0..N
        if alarm.obj_attr_is_set('rootCauseFaultyResource'):
            alarm_faulty_res_type = (
                alarm.rootCauseFaultyResource.faultyResourceType)
        else:
            alarm_faulty_res_type = None

        if subsc.filter.obj_attr_is_set('vnfInstanceSubscriptionFilter'):
            inst_filter = subsc.filter.vnfInstanceSubscriptionFilter
            if not subsc_utils.match_inst_subsc_filter(inst_filter, inst):
                continue

        if subsc.filter.obj_attr_is_set('notificationTypes'):
            if notif_type not in subsc.filter.notificationTypes:
                continue

        if (alarm_faulty_res_type is not None and
                subsc.filter.obj_attr_is_set('faultyResourceTypes')):
            if alarm_faulty_res_type not in subsc.filter.faultyResourceTypes:
                continue

        if (alarm.perceivedSeverity is not None and
                subsc.filter.obj_attr_is_set('perceivedSeverities')):
            if alarm.perceivedSeverity not in subsc.filter.perceivedSeverities:
                continue

        if (alarm.eventType is not None and
                subsc.filter.obj_attr_is_set('eventTypes')):
            if alarm.eventType not in subsc.filter.eventTypes:
                continue

        if (alarm.probableCause is not None and
                subsc.filter.obj_attr_is_set('probableCauses')):
            if alarm.probableCause not in subsc.filter.probableCauses:
                continue
        # OK, matched
        subscs.append(subsc)

    return subscs


def get_alarm_subscs(context, alarm, inst):
    if alarm.obj_attr_is_set('alarmClearedTime'):
        return get_matched_subscs(
            context, inst, 'AlarmClearedNotification', alarm)

    return get_matched_subscs(
        context, inst, 'AlarmNotification', alarm)
