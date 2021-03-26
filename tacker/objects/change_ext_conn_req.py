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

from tacker import objects
from tacker.objects import base
from tacker.objects import fields

LOG = logging.getLogger(__name__)


@base.TackerObjectRegistry.register
class ChangeExtConnRequest(base.TackerObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'vim_connection_info': fields.ListOfObjectsField(
            'VimConnectionInfo', nullable=True, default=[]),
        'ext_virtual_links': fields.ListOfObjectsField(
            'ExtVirtualLinkData', nullable=False),
        'additional_params': fields.DictOfNullableField(nullable=True,
            default={})
    }

    @classmethod
    def obj_from_primitive(cls, primitive, context):
        if 'tacker_object.name' in primitive:
            obj_change_ext_conn_req = super(
                ChangeExtConnRequest, cls).obj_from_primitive(
                primitive, context)
        else:
            if 'vim_connection_info' in primitive.keys():
                obj_data = [objects.VimConnectionInfo._from_dict(
                    vim_conn) for vim_conn in primitive.get(
                    'vim_connection_info', [])]
                primitive.update({'vim_connection_info': obj_data})

            if 'ext_virtual_links' in primitive.keys():
                obj_data = [objects.ExtVirtualLinkData.obj_from_primitive(
                    ext_vir_link, context) for ext_vir_link in primitive.get(
                    'ext_virtual_links', [])]
                primitive.update({'ext_virtual_links': obj_data})
            obj_change_ext_conn_req = ChangeExtConnRequest._from_dict(
                primitive)

        return obj_change_ext_conn_req

    @classmethod
    def _from_dict(cls, data_dict):
        vim_connection_info = data_dict.get('vim_connection_info', [])
        ext_virtual_links = data_dict.get('ext_virtual_links', [])
        additional_params = data_dict.get('additional_params', {})

        return cls(
            vim_connection_info=vim_connection_info,
            ext_virtual_links=ext_virtual_links,
            additional_params=additional_params)
