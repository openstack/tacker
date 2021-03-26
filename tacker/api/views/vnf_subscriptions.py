# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import json

from oslo_log import log as logging

from tacker.api import views as base
import tacker.conf
from tacker.objects import vnf_lcm_subscriptions as vnf_subscription

CONF = tacker.conf.CONF

LOG = logging.getLogger(__name__)


class ViewBuilder(base.BaseViewBuilder):

    FLATTEN_ATTRIBUTES = vnf_subscription.LccnSubscription. \
        FLATTEN_ATTRIBUTES

    def _get_subscription_links(self, vnf_lcm_subscription):
        if isinstance(vnf_lcm_subscription.id, str):
            decode_id = vnf_lcm_subscription.id
        else:
            decode_id = vnf_lcm_subscription.id
        return {
            "_links": {
                "self": {
                    "href": '%(endpoint)s/vnflcm/v1/subscriptions/%(id)s' %
                    {
                        "endpoint": CONF.vnf_lcm.endpoint_url,
                        "id": decode_id}}}}

    def _basic_subscription_info(self, vnf_lcm_subscription, filter=None):
        if filter is None:
            if 'filter' in vnf_lcm_subscription:
                filter_dict = {}

                if 'filter' in vnf_lcm_subscription.filter:
                    filter_dict = json.loads(
                        vnf_lcm_subscription.filter.filter)
                return {
                    'id': vnf_lcm_subscription.id,
                    'filter': filter_dict,
                    'callbackUri': vnf_lcm_subscription.callback_uri,
                }
            return {
                'id': vnf_lcm_subscription.id,
                'callbackUri': vnf_lcm_subscription.callback_uri,
            }
        else:
            return {
                'id': vnf_lcm_subscription.id,
                'filter': filter,
                'callbackUri': vnf_lcm_subscription.callback_uri,
            }

    def _get_subscription(self, subscription):
        subscription_response = self._basic_subscription_info(subscription)

        links = self._get_subscription_links(subscription)
        subscription_response.update(links)

        return subscription_response

    def subscription_list(
            self,
            vnf_lcm_subscriptions):
        return [self._get_subscription(subscription)
            for subscription in vnf_lcm_subscriptions]
