# Copyright (C) 2021 Nippon Telegraph and Telephone Corporation
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


from tacker.sol_refactored.conductor import conductor_rpc_v2
from tacker.sol_refactored.conductor import conductor_v2
from tacker.sol_refactored.objects import base as objects_base


class ConductorV2Hook(object):

    def initialize_service_hook(self, service):
        endpoints = [conductor_v2.ConductorV2()]
        serializer = objects_base.TackerObjectSerializer()
        service.conn.create_consumer(
            conductor_rpc_v2.TOPIC_CONDUCTOR_V2, endpoints,
            serializer=serializer)
