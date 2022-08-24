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
from oslo_utils import uuidutils

from tacker.sol_refactored.api import api_version
from tacker.sol_refactored.common import config
from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.common import http_client
from tacker.sol_refactored.common import vnf_instance_utils as inst_utils
from tacker.sol_refactored import objects

LOG = logging.getLogger(__name__)
CONF = config.CONF
TEST_NOTIFICATION_TIMEOUT = 20  # seconds


def update_report(context, job_id, report, timestamp):
    # update reports in the pmJob
    pm_job = get_pm_job(context, job_id)

    job_report = _gen_job_report(job_id, report, timestamp)

    if pm_job.obj_attr_is_set('reports'):
        pm_job.reports.append(job_report)
    else:
        pm_job.reports = [job_report]

    return pm_job


def _gen_job_report(job_id, report, timestamp):
    return objects.VnfPmJobV2_Reports(
        href=f'/vnfpm/v2/pm_jobs/{job_id}/reports/{report.id}',
        readyTime=timestamp
    )


def get_pm_job_all(context, marker=None):
    # get all pm-job
    return objects.PmJobV2.get_all(context, marker)


def get_pm_job(context, pm_job_id):
    # get the PM job from DB.
    pm_job = objects.PmJobV2.get_by_id(context, pm_job_id)
    if pm_job is None:
        raise sol_ex.PMJobNotExist()
    return pm_job


def get_pm_report(context, pm_job_id, report_id=None):
    if report_id:
        pm_report = objects.PerformanceReportV2.get_by_filter(
            context, id=report_id, jobId=pm_job_id)
        if not pm_report:
            raise sol_ex.PMReportNotExist()
        return pm_report[0]

    pm_reports = objects.PerformanceReportV2.get_by_filter(
        context, jobId=pm_job_id)
    return pm_reports


def pm_job_href(pm_job_id, endpoint):
    return f"{endpoint}/vnfpm/v2/pm_jobs/{pm_job_id}"


def make_pm_job_links(pm_job, endpoint):
    links = objects.VnfPmJobV2_Links()
    links.self = objects.Link(href=pm_job_href(pm_job.id, endpoint))
    links_objects = []
    for objects_id in pm_job.objectInstanceIds:
        links_objects.append(objects.Link(
            href=inst_utils.inst_href(objects_id, endpoint)))
    links.objects = links_objects
    return links


def _get_notification_auth_handle(pm_job):
    if not pm_job.obj_attr_is_set('authentication'):
        return http_client.NoAuthHandle()
    if pm_job.authentication.obj_attr_is_set('paramsBasic'):
        param = pm_job.authentication.paramsBasic
        return http_client.BasicAuthHandle(param.userName, param.password)
    if pm_job.authentication.obj_attr_is_set(
            'paramsOauth2ClientCredentials'):
        param = pm_job.authentication.paramsOauth2ClientCredentials
        return http_client.OAuth2AuthHandle(
            None, param.tokenEndpoint, param.clientId, param.clientPassword)
    return None


def test_notification(pm_job):
    auth_handle = _get_notification_auth_handle(pm_job)
    client = http_client.HttpClient(auth_handle,
                                    version=api_version.CURRENT_PM_VERSION,
                                    timeout=TEST_NOTIFICATION_TIMEOUT)

    url = pm_job.callbackUri
    try:
        resp, _ = client.do_request(url, "GET", expected_status=[204])
    except sol_ex.SolException as e:
        # any sort of error is considered. avoid 500 error.
        raise sol_ex.TestNotificationFailed() from e

    if resp.status_code != 204:
        raise sol_ex.TestNotificationFailed()


def make_pm_notif_data(instance_id, sub_instance_ids, report_id,
                       pm_job, timestamp, endpoint):
    notif_data = objects.PerformanceInformationAvailableNotificationV2(
        id=uuidutils.generate_uuid(),
        notificationType="PerformanceInformationAvailableNotification",
        timeStamp=timestamp,
        pmJobId=pm_job.id,
        objectType=pm_job.objectType,
        objectInstanceId=instance_id,
        _links=objects.PerformanceInformationAvailableNotificationV2_Links(
            objectInstance=objects.NotificationLink(
                href=inst_utils.inst_href(instance_id, endpoint)),
            pmJob=objects.NotificationLink(
                href=pm_job_href(pm_job.id, endpoint)),
            performanceReport=objects.NotificationLink(
                href=f"{endpoint}/vnfpm/v2/pm_jobs/{pm_job.id}/"
                     f"reports/{report_id}"
            )
        )
    )
    if sub_instance_ids:
        notif_data.subObjectInstanceIds = sub_instance_ids
    return notif_data


def async_call(func):
    def inner(*args, **kwargs):
        th = threading.Thread(target=func, args=args,
                              kwargs=kwargs, daemon=True)
        th.start()

    return inner


@async_call
def send_notification(pm_job, notif_data):
    auth_handle = _get_notification_auth_handle(pm_job)
    client = http_client.HttpClient(auth_handle,
                                    version=api_version.CURRENT_PM_VERSION)

    url = pm_job.callbackUri
    try:
        resp, _ = client.do_request(
            url, "POST", expected_status=[204], body=notif_data)
    except sol_ex.SolException:
        # it may occur if test_notification was not executed.
        LOG.exception("send_notification failed")

    if resp.status_code != 204:
        LOG.error(f'send_notification failed: {resp.status_code}')
