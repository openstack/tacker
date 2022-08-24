# Copyright (C) 2022 Fujitsu
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

from tacker.sol_refactored.api.policies import vnflcm_v2
from tacker.sol_refactored.api import server_notification_wsgi as sn_wsgi
from tacker.sol_refactored.controller import server_notification


class ServerNotificationRouter(sn_wsgi.ServerNotificationAPIRouter):
    controller = sn_wsgi.ServerNotificationResource(
        server_notification.ServerNotificationController(),
        policy_name=vnflcm_v2.SERVER_NOTIFICATION_POLICY_NAME)
    route_list = [
        ("/vnf_instances/{vnf_instance_id}/servers/{server_id}/notify",
            {"POST": "notify"})
    ]
