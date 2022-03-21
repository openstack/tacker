# Copyright (C) 2021 Nippon Telegraph and Telephone Corporation
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

from tacker.vnfm import vim_client

from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored import objects


LOG = logging.getLogger(__name__)


def get_default_vim(context):
    try:
        vim = vim_client.VimClient().get_vim(context)
        return vim_to_conn_info(vim)
    except Exception as ex:
        LOG.debug("default VIM not found: %s", ex)


def get_vim(context, vim_id):
    try:
        vim = vim_client.VimClient().get_vim(context, vim_id=vim_id)
        return vim_to_conn_info(vim)
    except Exception as ex:
        LOG.error("VIM %s not found: %s", vim_id, ex)
        raise sol_ex.VimNotFound(vim_id=vim_id)


def vim_to_conn_info(vim):
    region = None
    if vim.get('placement_attr', {}).get('regions'):
        region = vim['placement_attr']['regions'][0]

    vim_auth = vim['vim_auth']

    if vim['vim_type'] == "openstack":
        # see. https://nfvwiki.etsi.org/index.php
        # ?title=ETSINFV.OPENSTACK_KEYSTONE.V_3
        access_info = {
            'username': vim_auth['username'],
            'password': vim_auth['password'],
            'region': region,
            'project': vim_auth['project_name'],
            'projectDomain': vim_auth['project_domain_name'],
            'userDomain': vim_auth['user_domain_name']
        }
        interface_info = {
            'endpoint': vim_auth['auth_url'],
            # NOTE: certification is not supported at the moment.
            # TODO(oda-g): certification support if required.
            'skipCertificateHostnameCheck': True,
            'skipCertificateVerification': True
            # trustedCertificates is omitted
        }

        return objects.VimConnectionInfo(
            vimId=vim['vim_id'],
            vimType='ETSINFV.OPENSTACK_KEYSTONE.V_3',
            interfaceInfo=interface_info,
            accessInfo=access_info
        )
    if vim['vim_type'] == "kubernetes":  # k8s
        if vim_auth['username'] and vim_auth['password']:
            access_info = {
                'username': vim_auth['username'],
                'password': vim_auth['password']
            }
        elif vim_auth['bearer_token']:
            access_info = {
                'bearer_token': vim_auth['bearer_token']
            }

        interface_info = {
            'endpoint': vim_auth['auth_url']
        }
        if 'ssl_ca_cert' in vim_auth.keys():
            interface_info['ssl_ca_cert'] = vim_auth['ssl_ca_cert']

        return objects.VimConnectionInfo(
            vimId=vim['vim_id'],
            vimType='kubernetes',
            interfaceInfo=interface_info,
            accessInfo=access_info
        )
    raise sol_ex.SolException(sol_detail='not support vim type')
