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
from tacker.sol_refactored.common import fm_alarm_utils as alarm_utils
from tacker.sol_refactored.common import fm_subscription_utils as subsc_utils
from tacker.sol_refactored.controller import vnflcm_view as base_view
from tacker.sol_refactored import objects


LOG = logging.getLogger(__name__)
CONF = config.CONF


class AlarmViewBuilder(base_view.BaseViewBuilder):
    _EXCLUDE_DEFAULT = []

    def __init__(self, endpoint):
        self.endpoint = endpoint

    def detail(self, alarm, selector=None):
        # NOTE: _links is not saved in DB. create when it is necessary.
        if not alarm.obj_attr_is_set('_links'):
            alarm._links = alarm_utils.make_alarm_links(alarm, self.endpoint)

        resp = alarm.to_dict()

        if selector is not None:
            resp = selector.filter(alarm, resp)
        return resp


class FmSubscriptionViewBuilder(base_view.BaseViewBuilder):
    def __init__(self, endpoint):
        self.endpoint = endpoint

    def detail(self, subsc, selector=None):
        # NOTE: _links is not saved in DB. create when it is necessary.
        if not subsc.obj_attr_is_set('_links'):
            self_href = subsc_utils.subsc_href(subsc.id, self.endpoint)
            subsc._links = objects.FmSubscriptionV1_Links()
            subsc._links.self = objects.Link(href=self_href)

        resp = subsc.to_dict()

        # NOTE: authentication is not included in FmSubscriptionV1
        resp.pop('authentication', None)

        if selector is not None:
            resp = selector.filter(subsc, resp)
        return resp
