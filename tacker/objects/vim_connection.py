# Copyright (C) 2020 NTT DATA
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
class VimConnectionInfo(base.TackerObject, base.TackerPersistentObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.StringField(nullable=False),
        'vim_id': fields.StringField(nullable=True, default=None),
        'vim_type': fields.StringField(nullable=False),
        'interface_info': fields.DictOfNullableStringsField(nullable=True,
                                                         default={}),
        'access_info': fields.DictOfNullableStringsField(nullable=True,
                                                         default={}),
    }

    @classmethod
    def _from_dict(cls, data_dict):
        id = data_dict.get('id')
        vim_id = data_dict.get('vim_id')
        vim_type = data_dict.get('vim_type')
        access_info = data_dict.get('access_info', {})
        interface_info = data_dict.get('interface_info', {})
        obj = cls(id=id,
                  vim_id=vim_id,
                  vim_type=vim_type,
                  interface_info=interface_info,
                  access_info=access_info)
        return obj

    @classmethod
    def obj_from_primitive(cls, primitive, context):
        if 'tacker_object.name' in primitive:
            vim_connection_info = super(
                VimConnectionInfo, cls).obj_from_primitive(
                primitive, context)
        else:
            vim_connection_info = VimConnectionInfo._from_dict(primitive)

        return vim_connection_info

    def to_dict(self):
        return {'id': self.id,
                'vim_id': self.vim_id,
                'vim_type': self.vim_type,
                'interface_info': self.interface_info,
                'access_info': self.access_info}
