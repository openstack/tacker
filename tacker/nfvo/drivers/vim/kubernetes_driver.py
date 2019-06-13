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

from oslo_config import cfg
from oslo_log import log as logging

from tacker._i18n import _
from tacker.common.container import kubernetes_utils
from tacker.common import log
from tacker.common import utils
from tacker import context as t_context
from tacker.extensions import nfvo
from tacker.keymgr import API as KEYMGR_API
from tacker.nfvo.drivers.vim import abstract_vim_driver

LOG = logging.getLogger(__name__)
CONF = cfg.CONF

KUBERNETES_OPTS = [
    cfg.BoolOpt('use_barbican', default=True,
                help=_('Use barbican to encrypt vim password if True'
                       ', save vim credentials in local file system'
                       ' if False'))
]
cfg.CONF.register_opts(KUBERNETES_OPTS, 'k8s_vim')


def config_opts():
    return [('k8s_vim', KUBERNETES_OPTS)]


class Kubernetes_Driver(abstract_vim_driver.VimAbstractDriver):
    """Driver for Kubernetes VIM

    """

    def __init__(self):
        self.kubernetes = kubernetes_utils.KubernetesHTTPAPI()

    def get_type(self):
        return 'kubernetes'

    def get_name(self):
        return 'Kubernetes VIM Driver'

    def get_description(self):
        return 'Kubernetes VIM Driver'

    def authenticate_vim(self, vim_obj):
        """Validate VIM auth attributes

        """
        auth_cred, file_descriptor = self._get_auth_creds(vim_obj)
        self._validate_vim(auth_cred, file_descriptor)
        self.clean_authenticate_vim(auth_cred, file_descriptor)

    def _get_auth_creds(self, vim_obj):
        auth_cred = vim_obj['auth_cred']
        file_descriptor = self._create_ssl_ca_file(auth_cred)
        auth_cred['auth_url'] = vim_obj['auth_url']
        if ('username' not in auth_cred) and ('password' not in auth_cred):
            auth_cred['username'] = 'None'
            auth_cred['password'] = None
        return auth_cred, file_descriptor

    def _create_ssl_ca_file(self, auth_cred):
        ca_cert = utils.none_from_string(auth_cred.get('ssl_ca_cert'))
        if ca_cert:
            file_descriptor, file_path = \
                self.kubernetes.create_ca_cert_tmp_file(ca_cert)
            auth_cred['ca_cert_file'] = file_path
            return file_descriptor
        else:
            return None

    def _validate_vim(self, auth, file_descriptor):
        # If Tacker can get k8s_info, Kubernetes authentication is valid
        # if not, it is invalid
        auth_dict = dict(auth)
        try:
            core_api_client = \
                self.kubernetes.get_core_api_client(auth_dict)
            k8s_info = core_api_client.get_api_versions()
            LOG.info(k8s_info)
        except Exception as e:
            LOG.info('VIM Kubernetes authentication is wrong.')
            # delete temp file
            self.clean_authenticate_vim(auth_dict, file_descriptor)
            raise nfvo.VimUnauthorizedException(message=str(e))

    def _find_regions(self, core_v1_api_client):
        list_namespaces = core_v1_api_client.list_namespace()
        namespaces = [namespace.metadata.name
                      for namespace in list_namespaces.items]
        return namespaces

    def discover_placement_attr(self, vim_obj):
        """Fetch VIM placement information

        Attributes can include regions, AZ, namespaces.
        """
        # in Kubernetes environment, user can deploy resource
        # on specific namespace
        auth_cred, file_descriptor = self._get_auth_creds(vim_obj)
        core_v1_api_client = \
            self.kubernetes.get_core_v1_api_client(auth_cred)
        namespace_list = self._find_regions(core_v1_api_client)
        self.clean_authenticate_vim(auth_cred, file_descriptor)
        vim_obj['placement_attr'] = {'regions': namespace_list}
        return vim_obj

    def clean_authenticate_vim(self, vim_auth, file_descriptor):
        # remove ca_cert_file from vim_obj if it exists
        # close and delete temp ca_cert_file
        if file_descriptor is not None:
            file_path = vim_auth.pop('ca_cert_file')
            self.kubernetes.close_tmp_file(file_descriptor, file_path)

    @log.log
    def register_vim(self, vim_obj):
        """Validate Kubernetes VIM."""
        if 'key_type' in vim_obj['auth_cred']:
            vim_obj['auth_cred'].pop(u'key_type')
        if 'secret_uuid' in vim_obj['auth_cred']:
            vim_obj['auth_cred'].pop(u'secret_uuid')
        self.authenticate_vim(vim_obj)
        self.discover_placement_attr(vim_obj)
        self.encode_vim_auth(vim_obj['id'],
                             vim_obj['auth_cred'])
        LOG.debug('VIM registration completed for %s', vim_obj)

    @log.log
    def deregister_vim(self, vim_obj):
        """Deregister Kubernetes VIM from NFVO

        Delete VIM keys from file system
        """
        self.delete_vim_auth(vim_obj['id'],
                             vim_obj['auth_cred'])

    @log.log
    def delete_vim_auth(self, vim_id, auth):
        """Delete kubernetes vim information

        Delete vim key stored in file system
        """
        if 'secret_uuid' in auth:
            # Delete secret id of barbican
            LOG.debug('Attempting to delete key for vim id %s',
                      vim_id)
            if auth.get('key_type') == 'barbican_key':
                try:
                    k_context = \
                        t_context.generate_tacker_service_context()
                    keystone_conf = CONF.keystone_authtoken
                    secret_uuid = auth['secret_uuid']
                    keymgr_api = KEYMGR_API(keystone_conf.auth_url)
                    keymgr_api.delete(k_context, secret_uuid)
                    LOG.debug('VIM key deleted successfully for vim %s',
                              vim_id)
                except Exception as exception:
                    LOG.warning('VIM key deletion failed for vim %s due to %s',
                                vim_id,
                                exception)
                    raise
            else:
                raise nfvo.VimEncryptKeyError(vim_id=vim_id)

    @log.log
    def encode_vim_auth(self, vim_id, auth):
        """Encode VIM credentials

        Store VIM auth using fernet key encryption
        """
        fernet_key, fernet_obj = self.kubernetes.create_fernet_key()
        if ('password' in auth) and (auth['password'] is not None):
            encoded_auth = fernet_obj.encrypt(
                auth['password'].encode('utf-8'))
            auth['password'] = encoded_auth
        if 'bearer_token' in auth:
            encoded_auth = fernet_obj.encrypt(
                auth['bearer_token'].encode('utf-8'))
            auth['bearer_token'] = encoded_auth
        if utils.none_from_string(auth.get('ssl_ca_cert')):
            encoded_auth = fernet_obj.encrypt(
                auth['ssl_ca_cert'].encode('utf-8'))
            auth['ssl_ca_cert'] = encoded_auth

        if CONF.k8s_vim.use_barbican:
            try:
                k_context = t_context.generate_tacker_service_context()
                keystone_conf = CONF.keystone_authtoken
                keymgr_api = KEYMGR_API(keystone_conf.auth_url)
                secret_uuid = keymgr_api.store(k_context, fernet_key)

                auth['key_type'] = 'barbican_key'
                auth['secret_uuid'] = secret_uuid
                LOG.debug('VIM auth successfully stored for vim %s',
                          vim_id)
            except Exception as exception:
                LOG.warning('VIM key creation failed for vim %s due to %s',
                            vim_id,
                            exception)
                raise
        else:
            raise nfvo.VimEncryptKeyError(vim_id=vim_id)

    def get_vim_resource_id(self):
        # TODO(phuoc): will update which vim resource need to get
        pass
