# Copyright (C) 2020 NTT DATA
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

import json

from oslo_log import log as logging

from tacker.api import views as base
from tacker.common import utils
import tacker.conf
from tacker.objects import fields
from tacker.objects import vnf_instance as _vnf_instance

CONF = tacker.conf.CONF

LOG = logging.getLogger(__name__)


class ViewBuilder(base.BaseViewBuilder):

    FLATTEN_ATTRIBUTES = _vnf_instance.VnfInstance.FLATTEN_ATTRIBUTES

    def _get_links(self, vnf_instance):
        links = {
            "self": {
                "href": '/vnflcm/v1/vnf_instances/%s' % vnf_instance.id
            }
        }

        if (vnf_instance.instantiation_state ==
                fields.VnfInstanceState.NOT_INSTANTIATED):
            instantiate_link = {
                "instantiate": {
                    "href": '/vnflcm/v1/vnf_instances/%s/instantiate'
                            % vnf_instance.id
                }
            }

            links.update(instantiate_link)

        if (vnf_instance.instantiation_state ==
                fields.VnfInstanceState.INSTANTIATED):
            instantiated_state_links = {
                "terminate": {
                    "href": '/vnflcm/v1/vnf_instances/%s/terminate'
                            % vnf_instance.id
                },
                "heal": {
                    "href": '/vnflcm/v1/vnf_instances/%s/heal'
                            % vnf_instance.id
                }
            }

            links.update(instantiated_state_links)

        return {"_links": links}

    def _get_vim_conn_info(self, vim_connection_info):
        vim_connections = []

        for vim in vim_connection_info:
            access_info = {
                'username': '',
                'region': '',
                'password': '',
                'tenant': ''
            }
            vim_conn = vim

            for key_name in access_info.keys():
                if vim['access_info'].get(key_name):
                    access_info[key_name] = vim['access_info'].get(key_name)

            vim_conn['access_info'] = access_info

            vim_connections.append(vim_conn)

        return vim_connections

    def _get_lcm_op_occs_links(self, vnf_lcm_op_occs):
        _links = {
            "self": {
                "href": '%(endpoint)s/vnflcm/v1/vnf_lcm_op_occs/%(id)s'
                % {"endpoint": CONF.vnf_lcm.endpoint_url,
                    "id": vnf_lcm_op_occs.id}
            },
            "vnfInstance": {
                "href": '%(endpoint)s/vnflcm/v1/vnf_instances/%(id)s'
                % {"endpoint": CONF.vnf_lcm.endpoint_url,
                    "id": vnf_lcm_op_occs.vnf_instance_id}
            },
            "rollback": {
                "href":
                '%(endpoint)s/vnflcm/v1/vnf_lcm_op_occs/%(id)s/rollback'
                % {"endpoint": CONF.vnf_lcm.endpoint_url,
                    "id": vnf_lcm_op_occs.id}
            },
            "grant": {
                "href": '%(endpoint)s/vnflcm/v1/vnf_lcm_op_occs/%(id)s/grant'
                % {"endpoint": CONF.vnf_lcm.endpoint_url,
                    "id": vnf_lcm_op_occs.id}
            }
        }

        return {"_links": _links}

    def _get_vnf_instance_info(self, vnf_instance):
        vnf_instance_dict = vnf_instance.to_dict()
        vnf_metadata = vnf_instance_dict.pop("vnf_metadata")
        if vnf_metadata:
            vnf_instance_dict.update({"metadata": vnf_metadata})
        vnf_instance_dict = utils.convert_snakecase_to_camelcase(
            vnf_instance_dict)

        links = self._get_links(vnf_instance)

        vnf_instance_dict.update(links)
        return vnf_instance_dict

    def _get_vnf_lcm_op_occs(self, vnf_lcm_op_occs):
        vnf_lcm_op_occs_dict = vnf_lcm_op_occs.to_dict()
        vnf_lcm_op_occs_dict.pop('error_point')
        vnf_lcm_op_occs_dict = utils.convert_snakecase_to_camelcase(
            vnf_lcm_op_occs_dict)

        links = self._get_lcm_op_occs_links(vnf_lcm_op_occs)

        vnf_lcm_op_occs_dict.update(links)
        return vnf_lcm_op_occs_dict

    def create(self, vnf_instance):
        return self._get_vnf_instance_info(vnf_instance)

    def show(self, vnf_instance):
        return self._get_vnf_instance_info(vnf_instance)

    def index(self, vnf_instances):
        return [self._get_vnf_instance_info(vnf_instance)
                for vnf_instance in vnf_instances]

    def _get_subscription_links(self, vnf_lcm_subscription):
        if isinstance(vnf_lcm_subscription.id, str):
            decode_id = vnf_lcm_subscription.id
        else:
            decode_id = vnf_lcm_subscription.id.decode()
        return {
            "_links": {
                "self": {
                    "href": '%(endpoint)s/vnflcm/v1/subscriptions/%(id)s' %
                    {
                        "endpoint": CONF.vnf_lcm.endpoint_url,
                        "id": decode_id}}}}

    def _basic_subscription_info(self, vnf_lcm_subscription, filter=None):
        if not filter:
            if 'filter' in vnf_lcm_subscription:
                filter_dict = json.loads(vnf_lcm_subscription.filter)
                return {
                    'id': vnf_lcm_subscription.id.decode(),
                    'filter': filter_dict,
                    'callbackUri': vnf_lcm_subscription.callback_uri.decode(),
                }
            return {
                'id': vnf_lcm_subscription.id.decode(),
                'callbackUri': vnf_lcm_subscription.callback_uri.decode(),
            }
        else:
            return {
                'id': vnf_lcm_subscription.id,
                'filter': filter,
                'callbackUri': vnf_lcm_subscription.callback_uri,
            }

    def _subscription_filter(
            self,
            subscription_data,
            nextpage_opaque_marker,
            paging):
        # filter processing
        lcmsubscription = []
        last_flg = False
        start_num = CONF.vnf_lcm.subscription_num * (paging - 1)
        # Subscription_data counter for comparing
        # subscription_data and start_num
        wk_counter = 0
        for cnt, line in enumerate(subscription_data):
            LOG.debug("cnt %d,line %s" % (cnt, line))

            if start_num > wk_counter:
                wk_counter = wk_counter + 1
            else:
                if (CONF.vnf_lcm.subscription_num > len(
                        lcmsubscription) and nextpage_opaque_marker):
                    # add lcmsubscription
                    vnf_subscription_res = self._basic_subscription_info(
                        line)
                    links = self._get_subscription_links(line)
                    vnf_subscription_res.update(links)
                    lcmsubscription.append(vnf_subscription_res)
                    if CONF.vnf_lcm.subscription_num == len(
                            lcmsubscription):
                        if cnt == len(subscription_data) - 1:
                            last_flg = True
                        break
                elif not nextpage_opaque_marker:
                    # add lcmsubscription
                    vnf_subscription_res = self._basic_subscription_info(
                        line)
                    links = self._get_subscription_links(line)
                    vnf_subscription_res.update(links)
                    lcmsubscription.append(vnf_subscription_res)
                    if CONF.vnf_lcm.subscription_num < len(
                            lcmsubscription):
                        return 400, False
            if cnt == len(subscription_data) - 1:
                last_flg = True

        LOG.debug("len(lcmsubscription) %s" % len(lcmsubscription))
        LOG.debug(
            "CONF.vnf_lcm.subscription_num %s" %
            CONF.vnf_lcm.subscription_num)

        return lcmsubscription, last_flg

    def _get_vnf_lcm_subscription(self, vnf_lcm_subscription, filter=None):
        vnf_lcm_subscription_response = self._basic_subscription_info(
            vnf_lcm_subscription, filter)

        links = self._get_subscription_links(vnf_lcm_subscription)
        vnf_lcm_subscription_response.update(links)

        return vnf_lcm_subscription_response

    def subscription_create(self, vnf_lcm_subscription, filter):
        return self._get_vnf_lcm_subscription(vnf_lcm_subscription, filter)

    def subscription_list(
            self,
            vnf_lcm_subscriptions,
            nextpage_opaque_marker,
            paging):
        return self._subscription_filter(
            vnf_lcm_subscriptions, nextpage_opaque_marker, paging)

    def subscription_show(self, vnf_lcm_subscriptions):
        return self._get_vnf_lcm_subscription(vnf_lcm_subscriptions)

    def show_lcm_op_occs(self, vnf_lcm_op_occs):
        return self._get_vnf_lcm_op_occs(vnf_lcm_op_occs)
