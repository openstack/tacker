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
from oslo_utils import uuidutils

from tacker.sol_refactored.api import api_version
from tacker.sol_refactored.api.schemas import vnffm_v1 as schema
from tacker.sol_refactored.api import validator
from tacker.sol_refactored.api import wsgi as sol_wsgi
from tacker.sol_refactored.common import config
from tacker.sol_refactored.common import coordinate
from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.common import fm_alarm_utils
from tacker.sol_refactored.common import fm_subscription_utils as subsc_utils
from tacker.sol_refactored.controller import vnffm_view
from tacker.sol_refactored.nfvo import nfvo_client
from tacker.sol_refactored import objects


LOG = logging.getLogger(__name__)  # NOTE: unused at the moment

CONF = config.CONF


class VnfFmControllerV1(sol_wsgi.SolAPIController):

    def __init__(self):
        self.nfvo_client = nfvo_client.NfvoClient()
        self.endpoint = CONF.v2_vnfm.endpoint
        self._fm_view = vnffm_view.AlarmViewBuilder(self.endpoint)
        self._subsc_view = vnffm_view.FmSubscriptionViewBuilder(self.endpoint)

    def supported_api_versions(self, action):
        return api_version.v1_fm_versions

    def allowed_content_types(self, action):
        if action == 'update':
            # Content-Type of Modify request shall be
            # 'application/mergepatch+json' according to SOL spec.
            # But 'application/json' and 'text/plain' is OK for backward
            # compatibility.
            return ['application/mergepatch+json', 'application/json',
                    'text/plain']
        return ['application/json', 'text/plain']

    def index(self, request):
        filter_param = request.GET.get('filter')
        if filter_param is not None:
            filters = self._fm_view.parse_filter(filter_param)
        else:
            filters = None

        page_size = CONF.v2_vnfm.vnffm_alarm_page_size
        pager = self._fm_view.parse_pager(request, page_size)

        alarms = fm_alarm_utils.get_alarms_all(request.context,
                                               marker=pager.marker)

        resp_body = self._fm_view.detail_list(alarms, filters, None, pager)

        return sol_wsgi.SolResponse(
            200, resp_body, version=api_version.CURRENT_FM_VERSION,
            link=pager.get_link())

    def show(self, request, id):
        alarm = fm_alarm_utils.get_alarm(request.context, id)

        resp_body = self._fm_view.detail(alarm)

        return sol_wsgi.SolResponse(200, resp_body,
                                    version=api_version.CURRENT_FM_VERSION)

    @validator.schema(schema.AlarmModifications_V130, '1.3.0')
    @coordinate.lock_resources('{id}')
    def update(self, request, id, body):
        context = request.context
        alarm = fm_alarm_utils.get_alarm(context, id)

        ack_state = body['ackState']

        if alarm.ackState == ack_state:
            raise sol_ex.AckStateInvalid()

        alarm.ackState = ack_state
        with context.session.begin(subtransactions=True):
            alarm.update(context)

        return sol_wsgi.SolResponse(200, body,
                                    version=api_version.CURRENT_FM_VERSION)

    @validator.schema(schema.FmSubscriptionRequest_V130, '1.3.0')
    def subscription_create(self, request, body):
        context = request.context
        subsc = objects.FmSubscriptionV1(
            id=uuidutils.generate_uuid(),
            callbackUri=body['callbackUri']
        )

        if body.get('filter'):
            subsc.filter = (
                objects.FmNotificationsFilterV1.from_dict(
                    body['filter'])
            )

        auth_req = body.get('authentication')
        if auth_req:
            auth = objects.SubscriptionAuthentication(
                authType=auth_req['authType']
            )
            if 'BASIC' in auth.authType:
                basic_req = auth_req.get('paramsBasic')
                if basic_req is None:
                    msg = "ParamsBasic must be specified."
                    raise sol_ex.InvalidSubscription(sol_detail=msg)
                auth.paramsBasic = (
                    objects.SubscriptionAuthentication_ParamsBasic(
                        userName=basic_req.get('userName'),
                        password=basic_req.get('password')
                    )
                )

            if 'OAUTH2_CLIENT_CREDENTIALS' in auth.authType:
                oauth2_req = auth_req.get('paramsOauth2ClientCredentials')
                if oauth2_req is None:
                    msg = "paramsOauth2ClientCredentials must be specified."
                    raise sol_ex.InvalidSubscription(sol_detail=msg)
                auth.paramsOauth2ClientCredentials = (
                    objects.SubscriptionAuthentication_ParamsOauth2(
                        clientId=oauth2_req.get('clientId'),
                        clientPassword=oauth2_req.get('clientPassword'),
                        tokenEndpoint=oauth2_req.get('tokenEndpoint')
                    )
                )

            if 'TLS_CERT' in auth.authType:
                msg = "'TLS_CERT' is not supported at the moment."
                raise sol_ex.InvalidSubscription(sol_detail=msg)

            subsc.authentication = auth

        if CONF.v2_nfvo.test_callback_uri:
            subsc_utils.test_notification(subsc)

        subsc.create(context)

        resp_body = self._subsc_view.detail(subsc)
        self_href = subsc_utils.subsc_href(subsc.id, self.endpoint)

        return sol_wsgi.SolResponse(
            201, resp_body, version=api_version.CURRENT_FM_VERSION,
            location=self_href)

    def subscription_list(self, request):
        filter_param = request.GET.get('filter')
        if filter_param is not None:
            filters = self._subsc_view.parse_filter(filter_param)
        else:
            filters = None

        page_size = CONF.v2_vnfm.subscription_page_size
        pager = self._subsc_view.parse_pager(request, page_size)

        subscs = subsc_utils.get_subsc_all(request.context,
                                           marker=pager.marker)

        resp_body = self._subsc_view.detail_list(subscs, filters, None, pager)

        return sol_wsgi.SolResponse(
            200, resp_body, version=api_version.CURRENT_FM_VERSION,
            link=pager.get_link())

    def subscription_show(self, request, id):
        subsc = subsc_utils.get_subsc(request.context, id)

        resp_body = self._subsc_view.detail(subsc)

        return sol_wsgi.SolResponse(200, resp_body,
                                    version=api_version.CURRENT_FM_VERSION)

    def subscription_delete(self, request, id):
        context = request.context
        subsc = subsc_utils.get_subsc(request.context, id)

        subsc.delete(context)

        return sol_wsgi.SolResponse(204, None,
                                    version=api_version.CURRENT_FM_VERSION)
