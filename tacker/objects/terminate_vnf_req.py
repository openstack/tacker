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

from oslo_log import log as logging

from tacker.objects import base
from tacker.objects import fields

LOG = logging.getLogger(__name__)


@base.TackerObjectRegistry.register
class TerminateVnfRequest(base.TackerObject, base.TackerPersistentObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'termination_type': fields.VnfInstanceTerminationTypeField(
            nullable=False),
        'graceful_termination_timeout': fields.IntegerField(nullable=True,
                                                            default=0),
        'additional_params': fields.DictOfStringsField(nullable=True,
            default={}),
    }

    @classmethod
    def obj_from_primitive(cls, primitive, context):
        if 'tacker_object.name' in primitive:
            obj_terminate_vnf_req = super(
                TerminateVnfRequest, cls).obj_from_primitive(
                primitive, context)
        else:
            obj_terminate_vnf_req = TerminateVnfRequest._from_dict(primitive)

        return obj_terminate_vnf_req

    @classmethod
    def _from_dict(cls, data_dict):
        termination_type = data_dict.get('termination_type')
        graceful_termination_timeout = \
            data_dict.get('graceful_termination_timeout', 0)
        additional_params = data_dict.get('additional_params', {})

        return cls(termination_type=termination_type,
                   graceful_termination_timeout=graceful_termination_timeout,
                   additional_params=additional_params)
