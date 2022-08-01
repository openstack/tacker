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

"""Utilities functions for get openid token."""

import requests

from tacker.sol_refactored.common.exceptions import OIDCAuthFailed


def get_id_token_with_password_grant(
        token_endpoint, username, password, client_id,
        client_secret=None, ssl_ca_cert=None, timeout=20):

    if not token_endpoint or not username or not password or not client_id:
        raise OIDCAuthFailed(detail='token_endpoint, username, password,'
                                    ' client_id can not be empty.')

    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    body = {
        'grant_type': 'password',
        'scope': 'openid',
        'client_id': client_id,
        'client_secret': client_secret,
        'username': username,
        'password': password
    }

    verify = ssl_ca_cert if ssl_ca_cert else False

    try:
        resp = requests.post(token_endpoint, headers=headers, data=body,
                             verify=verify, timeout=timeout)

        if (resp.status_code == 200
                and resp.headers['Content-Type'] == 'application/json'):
            return resp.json()['id_token']

        raise OIDCAuthFailed(
            detail=f'response code: {resp.status_code}, body: {resp.text}')
    except requests.exceptions.RequestException as exc:
        raise OIDCAuthFailed(detail=str(exc))
