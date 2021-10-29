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

from tacker.objects import base
from tacker.objects import fields

LOG = logging.getLogger(__name__)


@base.TackerObjectRegistry.register
class CancelMode(base.TackerObject, base.TackerPersistentObject):
    # SOL 003 5.5.2.14 Type: CancelMode
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'cancel_mode': fields.VnfInstanceTerminationTypeField(
            nullable=False),
    }

    @classmethod
    def obj_from_primitive(cls, primitive, context):
        if 'tacker_object.name' in primitive:
            return super(
                CancelMode, cls).obj_from_primitive(primitive, context)
        return CancelMode._from_dict(primitive)

    @classmethod
    def _from_dict(cls, data_dict):
        return cls(cancel_mode=data_dict.get('cancel_mode'))
