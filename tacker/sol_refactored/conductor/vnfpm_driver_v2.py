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

from tacker.sol_refactored.common import config
from tacker.sol_refactored.common import pm_job_utils
from tacker.sol_refactored.nfvo import nfvo_client
from tacker.sol_refactored import objects


CONF = config.CONF


class VnfPmDriverV2():

    def __init__(self):
        self.endpoint = CONF.v2_vnfm.endpoint
        self.nfvo_client = nfvo_client.NfvoClient()

    def store_job_info(self, context, report):
        # store report into db

        report = self._store_report(context, report)

        # update job reports
        job_id = report.jobId
        timestamp = report.entries[0].performanceValues[0].timeStamp
        pm_job = self._update_job_reports(
            context, job_id, report, timestamp)

        # Send a notify pm job request to the NFVO client.
        # POST /{pmjob.callbackUri}
        self.nfvo_client.send_pm_job_notification(
            report, pm_job, timestamp, self.endpoint)

    def _store_report(self, context, report):
        report = objects.PerformanceReportV2.from_dict(report)
        report.create(context)
        return report

    def _update_job_reports(self, context, job_id, report, timestamp):
        # update reports in the pmJob
        update_job = pm_job_utils.update_report(
            context, job_id, report, timestamp)
        with context.session.begin(subtransactions=True):
            update_job.update(context)
        return update_job
