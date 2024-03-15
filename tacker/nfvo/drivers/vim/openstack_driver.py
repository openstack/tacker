# Copyright 2016 Brocade Communications System, Inc.
# All Rights Reserved.
#
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

import os

from keystoneauth1 import exceptions
from keystoneauth1.identity import v3
from keystoneauth1 import session
from neutronclient.v2_0 import client as neutron_client
from oslo_config import cfg
from oslo_log import log as logging

from tacker._i18n import _
from tacker.common import log
from tacker.common import utils
from tacker import context as t_context
from tacker.extensions import nfvo
from tacker.keymgr import API as KEYMGR_API
from tacker.nfvo.drivers.vim import abstract_vim_driver
from tacker.nfvo.nfvo_plugin import NfvoPlugin
from tacker.vnfm import keystone

LOG = logging.getLogger(__name__)
CONF = cfg.CONF

OPTS = [cfg.StrOpt('openstack', default='/etc/tacker/vim/fernet_keys',
                   help='Dir.path to store fernet keys.'),
        cfg.BoolOpt('use_barbican', default=False,
                    help=_('Use barbican to encrypt vim password if True, '
                           'save vim credentials in local file system '
                           'if False'))
        ]

# same params as we used in ping monitor driver
OPENSTACK_OPTS = [
    cfg.StrOpt('count', default='1',
               help=_('Number of ICMP packets to send')),
    cfg.StrOpt('timeout', default='1',
               help=_('Number of seconds to wait for a response')),
    cfg.StrOpt('interval', default='1',
               help=_('Number of seconds to wait between packets'))
]
cfg.CONF.register_opts(OPTS, 'vim_keys')

_VALID_RESOURCE_TYPES = {'network': {'client': neutron_client.Client,
                                     'cmd': 'list_networks',
                                     'vim_res_name': 'networks',
                                     'filter_attr': 'name'
                                     }
                         }

FC_MAP = {'name': 'name',
          'description': 'description',
          'eth_type': 'ethertype',
          'ip_src_prefix': 'source_ip_prefix',
          'ip_dst_prefix': 'destination_ip_prefix',
          'source_port_min': 'source_port_range_min',
          'source_port_max': 'source_port_range_max',
          'destination_port_min': 'destination_port_range_min',
          'destination_port_max': 'destination_port_range_max',
          'network_src_port_id': 'logical_source_port',
          'network_dst_port_id': 'logical_destination_port'}

CONNECTION_POINT = 'connection_points'
SFC_ENCAP = 'sfc_encap'


def config_opts():
    return [('vim_keys', OPTS)]


class OpenStack_Driver(abstract_vim_driver.VimAbstractDriver):
    """Driver for OpenStack VIM

    OpenStack driver handles interactions with local as well as
    remote OpenStack instances. The driver invokes keystone service for VIM
    authorization and validation. The driver is also responsible for
    discovering placement attributes such as regions, availability zones
    """

    def __init__(self):
        self.keystone = keystone.Keystone()
        self.keystone.create_key_dir(CONF.vim_keys.openstack)

    def get_type(self):
        return 'openstack'

    def get_name(self):
        return 'OpenStack VIM Driver'

    def get_description(self):
        return 'OpenStack VIM Driver'

    def authenticate_vim(self, vim_obj):
        """Validate VIM auth attributes

        Initialize keystoneclient with provided authentication attributes.
        """
        verify = utils.str_to_bool(vim_obj['auth_cred']
                                   .get('cert_verify', 'True'))
        auth_url = vim_obj['auth_url']
        NfvoPlugin.validate_keystone_auth_url(
            auth_url=auth_url,
            verify=verify)
        auth_cred = self._get_auth_creds(vim_obj)
        return self._initialize_keystone(auth_cred)

    def _get_auth_creds(self, vim_obj):
        auth_cred = vim_obj['auth_cred']
        vim_project = vim_obj['vim_project']
        auth_cred['project_id'] = vim_project.get('id')
        auth_cred['project_name'] = vim_project.get('name')
        auth_cred['project_domain_name'] = vim_project.get(
            'project_domain_name')
        auth_cred['auth_url'] = vim_obj['auth_url']
        if 'v3' not in auth_cred['auth_url']:
            auth_cred['auth_url'] = f'{auth_cred["auth_url"]}/v3'
        return auth_cred

    def _get_auth_plugin(self, **kwargs):
        auth_plugin = v3.Password(**kwargs)

        return auth_plugin

    def _initialize_keystone(self, auth):
        return self.keystone.initialize_client(**auth)

    def _find_regions(self, ks_client):
        # TODO(h-asahina): implement this method into KeystoneClient module
        resp = ks_client.get('/v3/regions')
        return [region['id'] for region in resp.json().get('regions', [])]

    def discover_placement_attr(self, vim_obj, ks_client):
        """Fetch VIM placement information

        Attributes can include regions, AZ.
        """
        try:
            regions = self._find_regions(ks_client)
        except (exceptions.Unauthorized, exceptions.BadRequest) as e:
            LOG.error("Authorization failed for user")
            raise nfvo.VimUnauthorizedException(message=e.message)
        vim_obj['placement_attr'] = {'regions': regions}
        return vim_obj

    @log.log
    def register_vim(self, vim_obj):
        """Validate and set VIM placements."""

        if 'key_type' in vim_obj['auth_cred']:
            vim_obj['auth_cred'].pop('key_type')
        if 'secret_uuid' in vim_obj['auth_cred']:
            vim_obj['auth_cred'].pop('secret_uuid')

        ks_client = self.authenticate_vim(vim_obj)
        self.discover_placement_attr(vim_obj, ks_client)
        self.encode_vim_auth(vim_obj['id'], vim_obj['auth_cred'])
        LOG.debug('VIM registration completed for %s', vim_obj)

    @log.log
    def deregister_vim(self, vim_obj):
        """Deregister VIM from NFVO

        Delete VIM keys from file system
        """
        self.delete_vim_auth(vim_obj['id'], vim_obj['auth_cred'])

    @log.log
    def delete_vim_auth(self, vim_id, auth):
        """Delete vim information

        Delete vim key stored in file system
        """
        LOG.debug('Attempting to delete key for vim id %s', vim_id)

        if auth.get('key_type') == 'barbican_key':
            try:
                k_context = t_context.generate_tacker_service_context()
                secret_uuid = auth['secret_uuid']
                if CONF.ext_oauth2_auth.use_ext_oauth2_auth:
                    keymgr_api = KEYMGR_API(
                        CONF.ext_oauth2_auth.token_endpoint)
                else:
                    keymgr_api = KEYMGR_API(CONF.keystone_authtoken.auth_url)
                keymgr_api.delete(k_context, secret_uuid)
                LOG.debug('VIM key deleted successfully for vim %s',
                          vim_id)
            except Exception as ex:
                LOG.error('VIM key deletion failed for vim %s due to %s',
                          vim_id, ex)
                raise
        else:
            key_file = os.path.join(CONF.vim_keys.openstack, vim_id)
            try:
                os.remove(key_file)
                LOG.debug('VIM key deleted successfully for vim %s',
                          vim_id)
            except OSError:
                LOG.warning('VIM key deletion failed for vim %s',
                            vim_id)

    @log.log
    def encode_vim_auth(self, vim_id, auth):
        """Encode VIM credentials

         Store VIM auth using fernet key encryption
         """
        fernet_key, fernet_obj = self.keystone.create_fernet_key()
        encoded_auth = fernet_obj.encrypt(auth['password'].encode('utf-8'))
        auth['password'] = encoded_auth

        if CONF.vim_keys.use_barbican:
            try:
                k_context = t_context.generate_tacker_service_context()
                if CONF.ext_oauth2_auth.use_ext_oauth2_auth:
                    keymgr_api = KEYMGR_API(
                        CONF.ext_oauth2_auth.token_endpoint)
                else:
                    keymgr_api = KEYMGR_API(CONF.keystone_authtoken.auth_url)
                secret_uuid = keymgr_api.store(k_context, fernet_key)

                auth['key_type'] = 'barbican_key'
                auth['secret_uuid'] = secret_uuid
                LOG.debug('VIM auth successfully stored for vim %s',
                          vim_id)
            except Exception as ex:
                LOG.error('VIM key creation failed for vim %s due to %s',
                          vim_id, ex)
                raise

        else:
            auth['key_type'] = 'fernet_key'
            key_file = os.path.join(CONF.vim_keys.openstack, vim_id)
            try:
                with open(key_file, 'wb') as f:
                    f.write(fernet_key)
                    LOG.debug('VIM auth successfully stored for vim %s',
                              vim_id)
            except IOError:
                raise nfvo.VimKeyNotFoundException(vim_id=vim_id)

    @log.log
    def get_vim_resource_id(self, vim_obj, resource_type, resource_name):
        """Locates openstack resource by type/name and returns ID

        :param vim_obj: VIM info used to access openstack instance
        :param resource_type: type of resource to find
        :param resource_name: name of resource to locate
        :return: ID of resource
        """
        if resource_type in _VALID_RESOURCE_TYPES:
            res_cmd_map = _VALID_RESOURCE_TYPES[resource_type]
            client_type = res_cmd_map['client']
            cmd = res_cmd_map['cmd']
            filter_attr = res_cmd_map.get('filter_attr')
            vim_res_name = res_cmd_map['vim_res_name']
        else:
            raise nfvo.VimUnsupportedResourceTypeException(type=resource_type)

        client = self._get_client(vim_obj, client_type)
        cmd_args = {}
        if filter_attr:
            cmd_args[filter_attr] = resource_name

        try:
            resources = getattr(client, "%s" % cmd)(**cmd_args)[vim_res_name]
            LOG.debug('resources output %s', resources)
        except Exception:
            raise nfvo.VimGetResourceException(
                cmd=cmd, name=resource_name, type=resource_type)

        if len(resources) > 1:
            raise nfvo.VimGetResourceNameNotUnique(
                cmd=cmd, name=resource_name)
        elif len(resources) < 1:
            raise nfvo.VimGetResourceNotFoundException(
                cmd=cmd, name=resource_name)

        return resources[0]['id']

    @log.log
    def _get_client(self, vim_obj, client_type):
        """Initializes and returns an openstack client

        :param vim_obj: VIM Information
        :param client_type: openstack client to initialize
        :return: initialized client
        """
        verify = utils.str_to_bool(vim_obj.get('cert_verify', 'True'))
        auth_url = vim_obj['auth_url']
        NfvoPlugin.validate_keystone_auth_url(
            auth_url=auth_url,
            verify=verify)
        auth_cred = self._get_auth_creds(vim_obj)
        auth_plugin = self._get_auth_plugin(**auth_cred)
        sess = session.Session(auth=auth_plugin)
        return client_type(session=sess)
