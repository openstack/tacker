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


from tacker.sol_refactored.api import api_version
from tacker.sol_refactored.api import wsgi as sol_wsgi


class VnfLcmVersionsController(sol_wsgi.SolAPIController):
    def index(self, request):
        api_versions = (api_version.supported_versions_v1['apiVersions'] +
                        api_version.supported_versions_v2['apiVersions'])
        body = {"uriPrefix": "/vnflcm",
                "apiVersions": api_versions}
        return sol_wsgi.SolResponse(200, body)
