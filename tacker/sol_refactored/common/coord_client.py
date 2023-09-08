# Copyright (C) 2023 Nippon Telegraph and Telephone Corporation
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


import time

from oslo_log import log as logging

from tacker.sol_refactored.common import common_script_utils
from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.common import http_client


LOG = logging.getLogger(__name__)

DEFAULT_INTERVAL = 5
DEFAULT_TIMEOUT = 3600


class CoordinationApiClient(object):

    def __init__(self, endpoint, auth_handle):
        self.endpoint = endpoint
        self.client = http_client.HttpClient(auth_handle)

    def create_coordination(self, coord_request):
        url = "{}/lcmcoord/v1/coordinations".format(self.endpoint)
        resp, body = self.client.do_request(
            url, "POST", expected_status=[201, 202, 503], version="1.0.0",
            body=coord_request)
        return resp, body

    def get_coordination(self, coord_id):
        url = "{}/lcmcoord/v1/coordinations/{}".format(self.endpoint, coord_id)
        resp, body = self.client.do_request(
            url, "GET", expected_status=[200, 202], version="1.0.0")
        return resp, body


# NOTE: The following are notes on this feature.
# - "cancel" function is not implemented.
# - Only calling from "change_vnfpkg" is assumed via the coordinationVNF
#   script.
def create_coordination(endpoint, authentication, coord_request, timeout=None):
    # create auth_handle
    common_script_utils.check_subsc_auth(authentication)
    auth_handle = common_script_utils.get_http_auth_handle(authentication)

    client = CoordinationApiClient(endpoint, auth_handle)

    # check timeout value
    try:
        timeout = int(timeout)
    except Exception:
        # If the timeout value cannot be converted to a number,
        # use DEFAULT_TIMEOUT.
        timeout = DEFAULT_TIMEOUT

    def _get_retry_after(resp):
        if resp.headers.get('Retry-After') is None:
            LOG.debug("Retry-After header not included in response. "
                      "Use DEFAULT_INTERVAL.")
            return DEFAULT_INTERVAL
        try:
            # The value of "delay-seconds" in Retry-After does not return
            # a negative number, but if a negative number is returned,
            # use DEFAULT_INTERVAL.
            if int(resp.headers.get('Retry-After')) < 0:
                return DEFAULT_INTERVAL
            return int(resp.headers.get('Retry-After'))
        except ValueError:
            # may be HTTP-date format. it is not supported.
            # use DEFAULT_INTERVAL
            LOG.warning("The value of Retry-After header may be "
                        "HTTP-date format. It is not supported, "
                        "use DEFAULT_INTERVAL.")
            return DEFAULT_INTERVAL

    def _execute_sleep(timeout, interval):
        if timeout < interval:
            msg = ("coordinationVNF script did not complete within "
                   "the timeout period.")
            raise sol_ex.SolException(sol_detail=msg)
        return time.sleep(interval)

    while (1):
        resp, body = client.create_coordination(coord_request)
        if resp.status_code == 201:
            # synchronous mode. done.
            return body
        elif resp.status_code == 202:
            # asynchronous mode.
            break
        # else: 503
        interval = _get_retry_after(resp)
        _execute_sleep(timeout, interval)
        timeout -= interval

    # asynchronous mode.
    location = resp.headers.get('Location')
    if location is None:
        msg = "Location header not included in response."
        raise sol_ex.SolException(sol_detail=msg)

    coord_id = location.split('/')[-1]
    while (1):
        interval = _get_retry_after(resp)
        _execute_sleep(timeout, interval)
        timeout -= interval

        resp, body = client.get_coordination(coord_id)

        if resp.status_code == 200:
            # asynchronous mode. done.
            return body
        # else: 202
