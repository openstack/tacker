# Copyright (C) 2025 KDDI
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

from cryptography.fernet import Fernet
import os
from tacker.db.migration import cli as db_cli
import tempfile
import unittest


class TestGenerateSecretKey(unittest.TestCase):
    def test_generate_secret_key_writes_fernet_key(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "gen.key")
            db_cli.CONF(
                ['generate_secret_key', '--file', out])
            db_cli.generate_secret_key(None, None)
            data = open(out, 'rb').read()
            Fernet(data)
            self.assertGreaterEqual(len(data), 32)
