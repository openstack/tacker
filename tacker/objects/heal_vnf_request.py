# Copyright 2018 NTT Data.
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

from tacker.objects import base
from tacker.objects import fields


@base.TackerObjectRegistry.register
class HealVnfAdditionalParams(base.TackerObject):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'parameter': fields.StringField(),
        'cause': fields.ListOfStringsField()
    }


@base.TackerObjectRegistry.register
class HealVnfRequest(base.TackerObject):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'cause': fields.StringField(),
        'additional_params': fields.ListOfObjectsField(
            'HealVnfAdditionalParams')
    }
