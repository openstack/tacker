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

from oslo_log import log as logging

from tacker.sol_refactored.common import config
from tacker.sol_refactored.common import pm_job_utils
from tacker.sol_refactored.common import pm_threshold_utils
from tacker.sol_refactored.controller import vnflcm_view as base_view


LOG = logging.getLogger(__name__)
CONF = config.CONF


class PmJobViewBuilder(base_view.BaseViewBuilder):
    _EXCLUDE_DEFAULT = []

    def __init__(self, endpoint):
        self.endpoint = endpoint

    def detail(self, pm_job, selector=None):
        # NOTE: _links is not saved in DB. create when it is necessary.
        if not pm_job.obj_attr_is_set('_links'):
            pm_job._links = pm_job_utils.make_pm_job_links(
                pm_job, self.endpoint)

        resp = pm_job.to_dict()
        if resp.get('authentication'):
            resp.pop('authentication', None)
        if resp.get('metadata'):
            resp.pop('metadata', None)
        if selector is not None:
            resp = selector.filter(pm_job, resp)
        return resp

    def report_detail(self, pm_report):
        resp = pm_report.to_dict()
        if resp.get('id'):
            resp.pop('id')
        if resp.get('jobId'):
            resp.pop('jobId')
        return resp


class PmThresholdViewBuilder(base_view.BaseViewBuilder):
    _EXCLUDE_DEFAULT = []

    def __init__(self, endpoint):
        self.endpoint = endpoint

    def detail(self, threshold, selector=None):
        # NOTE: _links is not saved in DB. create when it is necessary.
        if not threshold.obj_attr_is_set('_links'):
            threshold._links = pm_threshold_utils.make_pm_threshold_links(
                threshold, self.endpoint)

        resp = threshold.to_dict()
        resp.pop('authentication', None)
        resp.pop('metadata', None)
        if selector is not None:
            resp = selector.filter(threshold, resp)
        return resp
