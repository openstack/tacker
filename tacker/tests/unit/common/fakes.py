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

from tacker.sol_refactored.db.sqlalchemy import models

# master key: b'AFrUsb9hHAP6L0rbFv1U1bZErxpcP0dXPUC1mVpkgdU='
# tacker key: b'1RRj9HjqzeEwPabTvIP-BCFCHMOfmYaCPEhcsZvJ4wQ='
# encrypted: b'gAAAAABkQTanQNo6Xfd54RW5DjBMjwr2mpWjB6YXi9UQW65'
#             'Dr90C1iqEQIdF6esuO-XaH0uLNTwjWbjkpy9LUnFARNzTmQ'
#             'PP5XagyyQNxAZ3Zx4KBd7cFAsxk0_SdLh5a10Ojep3yMy9'


def return_no_crypt_key():
    return []


def return_crypt_key_barbican():
    model_obj = models.CryptKey(
        id='test_uuid',
        secretUuid='secret_uuid',
        encryptedKey='gAAAAABkQTanQNo6Xfd54RW5DjBMjwr2mpWjB6YXi9UQW65'
                     'Dr90C1iqEQIdF6esuO-XaH0uLNTwjWbjkpy9LUnFARNzTmQ'
                     'PP5XagyyQNxAZ3Zx4KBd7cFAsxk0_SdLh5a10Ojep3yMy9',
        keyType='barbican',
        inUse=True
    )

    return [model_obj]


def return_crypt_key_local():
    model_obj = models.CryptKey(
        id='test_uuid',
        secretUuid='secret_uuid',
        encryptedKey='gAAAAABkQTanQNo6Xfd54RW5DjBMjwr2mpWjB6YXi9UQW65'
                     'Dr90C1iqEQIdF6esuO-XaH0uLNTwjWbjkpy9LUnFARNzTmQ'
                     'PP5XagyyQNxAZ3Zx4KBd7cFAsxk0_SdLh5a10Ojep3yMy9',
        keyType='local',
        inUse=True
    )

    return [model_obj]
