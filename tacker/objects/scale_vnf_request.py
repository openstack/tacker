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
class ScaleVnfRequest(base.TackerObject):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'type': fields.StringField(nullable=False),
        'aspect_id': fields.StringField(nullable=False),
        'number_of_steps': fields.IntegerField(nullable=True, default=1),
        'additional_params': fields.DictOfStringsField(nullable=True,
            default={}),
    }

    @classmethod
    def obj_from_primitive(cls, primitive, context):
        if 'tacker_object.name' in primitive:
            obj_scle_vnf_req = super(
                ScaleVnfRequest, cls).obj_from_primitive(primitive, context)
        else:
            obj_scle_vnf_req = ScaleVnfRequest._from_dict(primitive)

        return obj_scle_vnf_req

    @classmethod
    def _from_dict(cls, data_dict):
        type = data_dict.get('type')
        aspect_id = data_dict.get('aspect_id')
        number_of_steps = data_dict.get('number_of_steps')
        additional_params = data_dict.get('additional_params')

        obj = cls(type=type,
                  aspect_id=aspect_id,
                  number_of_steps=number_of_steps,
                  additional_params=additional_params)
        return obj
