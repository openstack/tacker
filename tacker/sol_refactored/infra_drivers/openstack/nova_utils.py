# Copyright (C) 2022 Nippon Telegraph and Telephone Corporation
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

from tacker.sol_refactored.common import http_client


LOG = logging.getLogger(__name__)


class NovaClient(object):

    def __init__(self, vim_info):
        auth = http_client.KeystonePasswordAuthHandle(
            auth_url=vim_info.interfaceInfo['endpoint'],
            username=vim_info.accessInfo['username'],
            password=vim_info.accessInfo['password'],
            project_name=vim_info.accessInfo['project'],
            user_domain_name=vim_info.accessInfo['userDomain'],
            project_domain_name=vim_info.accessInfo['projectDomain']
        )
        self.client = http_client.HttpClient(auth,
                                             service_type='compute')

    def get_zone(self):
        path = "os-availability-zone/detail"
        resp, body = self.client.do_request(path, "GET",
                expected_status=[200])

        def _use_zone_for_retry(zone):
            for host_info in zone['hosts'].values():
                for service in host_info.keys():
                    if service == 'nova-compute':
                        return zone['zoneState']['available']
            return False

        zones = {zone['zoneName'] for zone in body['availabilityZoneInfo']
                 if _use_zone_for_retry(zone)}
        return zones
