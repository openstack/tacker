# Copyright (c) 2023 Fujitsu
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

from oslo_config import cfg
from oslo_utils import uuidutils
from unittest import mock

from tacker.common import crypt_utils
from tacker.common import exceptions
from tacker.sol_refactored.db.sqlalchemy import models
from tacker.sol_refactored.objects.common import crypt_key
from tacker.tests import base
from tacker.tests.unit.common import fakes


class TestCryptUtils(base.BaseTestCase):

    def setUp(self):
        super(TestCryptUtils, self).setUp()
        self.tacker_key = b'1RRj9HjqzeEwPabTvIP-BCFCHMOfmYaCPEhcsZvJ4wQ='
        self.master_key = b'AFrUsb9hHAP6L0rbFv1U1bZErxpcP0dXPUC1mVpkgdU='

    @mock.patch.object(crypt_key.CryptKey, 'get_by_filter')
    @mock.patch.object(crypt_key.CryptKey, 'create')
    @mock.patch.object(crypt_utils.CryptKeyBarbican, 'save_key')
    @mock.patch.object(crypt_utils.CryptUtil, '_create_fernet_key')
    def test_create_crypt_key_to_barbican(self,
                                          mock_create_fernet_key,
                                          mock_save_to_barbican,
                                          mock_create_crypt_key,
                                          mock_get_crypt_key):
        cfg.CONF.set_override('use_credential_encryption', True)
        cfg.CONF.set_override('keymanager_type', 'barbican')
        mock_get_crypt_key.return_value = fakes.return_no_crypt_key()
        mock_create_crypt_key.return_value = None
        mock_save_to_barbican.return_value = uuidutils.generate_uuid()
        mock_create_fernet_key.return_value = self.tacker_key
        cu = crypt_utils.CryptUtil()
        self.assertEqual(cu.tacker_key, self.tacker_key)

    @mock.patch.object(crypt_key.CryptKey, 'get_by_filter')
    @mock.patch.object(crypt_key.CryptKey, 'create')
    @mock.patch.object(crypt_utils.CryptKeyLocal, 'save_key')
    @mock.patch.object(crypt_utils.CryptUtil, '_create_fernet_key')
    def test_create_crypt_key_to_local(self,
                                       mock_create_fernet_key,
                                       mock_save_to_local,
                                       mock_create_crypt_key,
                                       mock_get_crypt_key):
        cfg.CONF.set_override('use_credential_encryption', True)
        cfg.CONF.set_override('keymanager_type', 'local')
        mock_get_crypt_key.return_value = fakes.return_no_crypt_key()
        mock_create_crypt_key.return_value = None
        mock_save_to_local.return_value = uuidutils.generate_uuid()
        mock_create_fernet_key.return_value = self.tacker_key
        cu = crypt_utils.CryptUtil()
        self.assertEqual(cu.tacker_key, self.tacker_key)

    @mock.patch.object(crypt_key.CryptKey, 'get_by_filter')
    @mock.patch.object(crypt_utils.CryptKeyBarbican, 'load_key')
    @mock.patch.object(crypt_utils.CryptKeyBarbican, 'save_key')
    def test_load_crypt_key_from_barbican(self,
                                          mock_save_key_to_barbican,
                                          mock_load_key_from_barbican,
                                          mock_get_crypt_key):
        cfg.CONF.set_override('use_credential_encryption', True)
        cfg.CONF.set_override('keymanager_type', 'barbican')
        mock_get_crypt_key.return_value = fakes.return_crypt_key_barbican()
        mock_load_key_from_barbican.return_value = self.master_key
        mock_save_key_to_barbican.return_value = uuidutils.generate_uuid()
        cu = crypt_utils.CryptUtil()
        self.assertEqual(cu.tacker_key, self.tacker_key)

    @mock.patch.object(crypt_key.CryptKey, 'get_by_filter')
    @mock.patch.object(crypt_utils.CryptKeyLocal, 'load_key')
    @mock.patch.object(crypt_utils.CryptKeyLocal, 'save_key')
    def test_load_crypt_key_from_local(self,
                                       mock_save_key_to_local,
                                       mock_load_key_from_local,
                                       mock_crypt_key):
        cfg.CONF.set_override('use_credential_encryption', True)
        cfg.CONF.set_override('keymanager_type', 'local')
        mock_crypt_key.return_value = fakes.return_crypt_key_local()
        mock_load_key_from_local.return_value = self.master_key
        mock_save_key_to_local.return_value = uuidutils.generate_uuid()
        cu = crypt_utils.CryptUtil()
        self.assertEqual(cu.tacker_key, self.tacker_key)

    @mock.patch.object(crypt_key.CryptKey, 'get_by_filter')
    @mock.patch.object(models.CryptKey, 'update')
    @mock.patch.object(crypt_utils.CryptKeyLocal, 'load_key')
    @mock.patch.object(crypt_utils.CryptKeyBarbican, 'save_key')
    @mock.patch.object(os, 'remove')
    def test_change_from_local_to_barbican(self,
                                           mock_os_remove,
                                           mock_save_key_to_barbican,
                                           mock_load_key_from_local,
                                           mock_update_crypt_key,
                                           mock_get_crypt_key):
        cfg.CONF.set_override('use_credential_encryption', True)
        cfg.CONF.set_override('keymanager_type', 'barbican')
        mock_get_crypt_key.return_value = fakes.return_crypt_key_local()
        mock_update_crypt_key.return_value = None
        mock_load_key_from_local.return_value = self.master_key
        mock_save_key_to_barbican.return_value = uuidutils.generate_uuid()
        mock_os_remove.return_value = None
        cu = crypt_utils.CryptUtil()
        self.assertEqual(cu.tacker_key, self.tacker_key)

    @mock.patch.object(crypt_key.CryptKey, 'get_by_filter')
    @mock.patch.object(crypt_utils.CryptKeyLocal, 'load_key')
    @mock.patch.object(os, 'remove')
    def test_change_from_barbican_to_local(self,
                                           mock_os_remove,
                                           mock_load_key_from_local,
                                           mock_get_crypt_key):
        cfg.CONF.set_override('use_credential_encryption', True)
        cfg.CONF.set_override('keymanager_type', 'local')
        mock_get_crypt_key.return_value = fakes.return_crypt_key_barbican()
        mock_load_key_from_local.return_value = self.master_key
        mock_os_remove.return_value = None
        self.assertRaises(exceptions.FailedToGetCryptKey,
                          crypt_utils.CryptUtil)
