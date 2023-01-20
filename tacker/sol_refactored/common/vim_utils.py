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
    extra = vim.get('extra', {})

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
            accessInfo=access_info,
            extra=extra
        )
    if vim['vim_type'] == "kubernetes":
        # When vimType is kubernetes, it will be converted to the vimType name
        # defined by ETSI and used in lifecycle.
        # Typically, it will be converted to ETSINFV.KUBERNETES.V_1. If the
        # content of helm is included in vim's extra information, it will be
        # converted to ETSINFV.HELM.V_3.
        # You can see
        # https://nfvwiki.etsi.org/index.php?title=ETSINFV.KUBERNETES.V_1
        # https://nfvwiki.etsi.org/index.php?title=ETSINFV.HELM.V_3
        # for details.
        if 'oidc_token_url' in vim_auth:
            access_info = {
                'oidc_token_url': vim_auth.get('oidc_token_url'),
                'username': vim_auth.get('username'),
                'password': vim_auth.get('password'),
                'client_id': vim_auth.get('client_id'),
                'client_secret': vim_auth.get('client_secret')
            }
        elif vim_auth.get('username') and vim_auth.get('password'):
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

        vim_type = ('ETSINFV.HELM.V_3'
                    if vim.get('extra', {}).get('use_helm', False)
                    else 'ETSINFV.KUBERNETES.V_1')
        return objects.VimConnectionInfo(
            vimId=vim['vim_id'],
            vimType=vim_type,
            interfaceInfo=interface_info,
            accessInfo=access_info,
            extra=extra
        )

    raise sol_ex.SolException(sol_detail='not support vim type')
