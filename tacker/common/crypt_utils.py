# Copyright (C) 2023 Fujitsu
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
import abc
import os

from cryptography import fernet
from oslo_config import cfg
from oslo_log import log as logging
from oslo_service import service
from oslo_utils import uuidutils

from tacker.common import exceptions
from tacker import context as t_context
from tacker.keymgr import API as KEYMGR_API
from tacker.sol_refactored import objects

LOG = logging.getLogger(__name__)

CONF = cfg.CONF


def encrypt(v):
    cu = CryptUtil()
    return cu.encrypt(v)


def decrypt(v):
    cu = CryptUtil()
    return cu.decrypt(v)


def encrypt_subsc_auth_v2(auth):
    password = auth.get('paramsBasic', {}).get('password', None)
    if password:
        enc = encrypt(password)
        auth['paramsBasic']['password'] = enc
    password = (auth.get('paramsOauth2ClientCredentials', {})
                    .get('clientPassword', None))
    if password:
        enc = encrypt(password)
        auth['paramsOauth2ClientCredentials']['clientPassword'] = enc


def decrypt_subsc_auth_v2(auth):
    if (auth.obj_attr_is_set('paramsBasic') and
            auth.paramsBasic.obj_attr_is_set('password')):
        password = auth.paramsBasic.password
        dec = decrypt(password)
        auth.paramsBasic.password = dec
    if (auth.obj_attr_is_set('paramsOauth2ClientCredentials') and
            auth.paramsOauth2ClientCredentials.obj_attr_is_set(
            'clientPassword')):
        password = auth.paramsOauth2ClientCredentials.clientPassword
        dec = decrypt(password)
        auth.paramsOauth2ClientCredentials.clientPassword = dec


def encrypt_monitoring_v2(metadata):
    targets_info = metadata.get('monitoring', {}).get('targetsInfo', {})
    new_targets_info = []
    for target_info in targets_info:
        auth_info = target_info.get('authInfo', None)
        if auth_info:
            password = auth_info.get('ssh_password', None)
            if password:
                enc = encrypt(password)
                target_info['authInfo']['ssh_password'] = enc
                new_targets_info += [target_info]

    metadata['monitoring']['targetsInfo'] = new_targets_info


def decrypt_monitoring_v2(metadata):
    targets_info = metadata.get('monitoring', {}).get('targetsInfo', None)

    new_targets_info = []
    for target_info in targets_info:
        auth_info = target_info.get('authInfo', None)
        if auth_info:
            password = auth_info.get('ssh_password', None)
            if password:
                dec = decrypt(password)
                target_info['authInfo']['ssh_password'] = dec
                new_targets_info += [target_info]
    metadata['monitoring']['targetsInfo'] = new_targets_info


def encrypt_vim_infos_v2(vim_infos, pop_cred=False):
    # If the pop_cred argument is True, the credentials are removed.

    cred_data = ['password', 'bearer_token', 'client_secret']
    for vim_info in vim_infos.values():
        if 'accessInfo' not in vim_info:
            continue
        for enc_key in cred_data:
            if enc_key in vim_info['accessInfo']:
                if pop_cred:
                    vim_info['accessInfo'].pop(enc_key)
                else:
                    enc = encrypt(vim_info['accessInfo'][enc_key])
                    vim_info['accessInfo'][enc_key] = enc


def decrypt_vim_infos_v2(vim_infos):
    cred_data = ['password', 'bearer_token', 'client_secret']
    for vim_info in vim_infos.values():
        if not vim_info.obj_attr_is_set('accessInfo'):
            continue
        for dec_key in cred_data:
            if dec_key in vim_info.accessInfo:
                dec = decrypt(vim_info.accessInfo[dec_key])
                vim_info.accessInfo[dec_key] = dec


class CryptUtil(metaclass=service.Singleton):
    '''Use two encryption keys at the same time.

    The encryption key used to encrypt each record in the DB is called the
    Tacker key, and the key itself is encrypted and stored in the database.
    The encryption key used to encrypt the Tacker key is called the master
    key and is managed by the keymanager.
    When rotating encryption keys, register a new master key and re-encrypt
    the encrypted Tacker key.
    '''

    crypt_util = None

    def __new__(cls):
        if not cls.crypt_util:
            cls.crypt_util = super().__new__(cls)
        return cls.crypt_util

    def __init__(self):
        context = t_context.get_admin_context()
        self.tacker_key = None
        self.load_key(context)

    def _create_fernet_key(self):
        fernet_key = fernet.Fernet.generate_key()
        return fernet_key

    def load_key(self, context):
        if not CONF.use_credential_encryption:
            return

        crypt_key = objects.CryptKey.get_by_filter(context, inUse=True)

        if len(crypt_key) == 1:
            crypt_key_obj = crypt_key[0]
            if CONF.keymanager_type == "barbican":
                barbican_crypter = CryptKeyBarbican()
                if crypt_key_obj.keyType == "barbican":
                    secret_uuid = crypt_key_obj.secretUuid
                    master_key = barbican_crypter.load_key(secret_uuid)
                elif crypt_key_obj.keyType == "local":
                    local_crypter = CryptKeyLocal()
                    master_key = local_crypter.load_key(crypt_key_obj.id)
                    secret_uuid = barbican_crypter.save_key(master_key)
                    os.remove(local_crypter.load_key_file(crypt_key_obj.id))
                    crypt_key_obj.secretUuid = secret_uuid
                    crypt_key_obj.keyType = "barbican"
                    crypt_key_obj.update(context)
                else:
                    LOG.error('Invalid keyType is stored in DB.')
                    raise exceptions.FailedToGetCryptKey()
            elif (CONF.keymanager_type == "local" and
                    crypt_key_obj.keyType == "local"):
                local_crypter = CryptKeyLocal()
                master_key = local_crypter.load_key(crypt_key_obj.id)
            else:
                LOG.error('The keymanager_type specified in config does '
                          'not match the keyType stored in DB.')
                raise exceptions.FailedToGetCryptKey()
            fernet_obj = fernet.Fernet(master_key)
            if crypt_key_obj.encryptedKey:
                self.tacker_key = fernet_obj.decrypt(
                    crypt_key_obj.encryptedKey.encode('utf-8'))
            else:
                LOG.error('Failed to decrypt saved encryptedKey.')
                raise exceptions.FailedToGetCryptKey()
        elif len(crypt_key) == 0:
            secret_uuid = None
            master_key = self._create_fernet_key()
            self.tacker_key = self._create_fernet_key()
            fernet_obj = fernet.Fernet(master_key)
            encrypted_key = fernet_obj.encrypt(self.tacker_key)
            if CONF.keymanager_type == "barbican":
                barbican_crypter = CryptKeyBarbican()
                secret_uuid = barbican_crypter.save_key(master_key)
                crypt_id = uuidutils.generate_uuid()
            elif CONF.keymanager_type == "local":
                local_crypter = CryptKeyLocal()
                crypt_id = local_crypter.save_key(master_key)
            else:
                LOG.error('Invalid keymanager_type specified in config.')
                raise exceptions.FailedToGetCryptKey()

            crypt_key = objects.CryptKey(
                id=crypt_id,
                secretUuid=secret_uuid,
                encryptedKey=encrypted_key.decode('utf-8'),
                keyType=CONF.keymanager_type,
                inUse=True
            )
            crypt_key.create(context)
        else:
            LOG.error('Duplicate record in CryptKey.')
            raise exceptions.FailedToGetCryptKey()

    def encrypt(self, target_str):
        fernet_obj = fernet.Fernet(self.tacker_key)
        encrypted_data = fernet_obj.encrypt(
            target_str.encode('utf-8')).decode('utf-8')
        return encrypted_data

    def decrypt(self, target_str):
        fernet_obj = fernet.Fernet(self.tacker_key)
        decrypted_data = fernet_obj.decrypt(
            target_str.encode('utf-8')).decode('utf-8')
        return decrypted_data


class CryptKeyBase(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def load_key(self, id):
        pass

    @abc.abstractmethod
    def save_key(self, key):
        pass


class CryptKeyBarbican(CryptKeyBase):
    def load_key(self, id):
        k_context = t_context.generate_tacker_service_context()
        if CONF.ext_oauth2_auth.use_ext_oauth2_auth:
            keymgr_api = KEYMGR_API(CONF.ext_oauth2_auth.token_endpoint)
        else:
            keymgr_api = KEYMGR_API(CONF.keystone_authtoken.auth_url)
        secret_obj = keymgr_api.get(k_context, id)
        master_key = secret_obj.payload
        return master_key

    def save_key(self, key):
        k_context = t_context.generate_tacker_service_context()
        if CONF.ext_oauth2_auth.use_ext_oauth2_auth:
            keymgr_api = KEYMGR_API(CONF.ext_oauth2_auth.token_endpoint)
        else:
            keymgr_api = KEYMGR_API(CONF.keystone_authtoken.auth_url)
        secret_uuid = keymgr_api.store(k_context, key)
        return secret_uuid


class CryptKeyLocal(CryptKeyBase):
    def load_key(self, id):
        key_file = self.load_key_file(id)
        LOG.debug('Attempting to open key file')
        try:
            with open(key_file, 'r') as f:
                master_key = f.read()
        except IOError:
            LOG.error('Master key not found')
            raise exceptions.FailedToGetCryptKey()
        return master_key

    def save_key(self, key):
        id = uuidutils.generate_uuid()
        crypt_key_dir = CONF.crypt_key_dir
        self._create_key_dir(crypt_key_dir)
        key_file = os.path.join(crypt_key_dir, id)
        try:
            with open(key_file, 'wb') as f:
                f.write(key)
                LOG.debug('Master key successfully stored.')
        except IOError:
            LOG.error('Failed to save master key.')
            raise
        return id

    def load_key_file(self, id):
        return os.path.join(CONF.crypt_key_dir, id)

    @staticmethod
    def _create_key_dir(path):
        if not os.access(path, os.F_OK):
            LOG.info('The directory for key storage does not appear to exist; '
                     'attempting to create it')
            try:
                os.makedirs(path, 0o700)
            except OSError:
                LOG.error(
                    'Failed to create the directory for key storage: either '
                    'it already exists or you don\'t have sufficient '
                    'permissions to create it')
                raise
