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

from oslo_utils import uuidutils


class VnfPackage:

    @staticmethod
    def make_get_vnf_pkg_info_resp(vnfdid):
        data = {
            "id": uuidutils.generate_uuid(),
            "vnfdId": vnfdid,
            "vnfProvider": "Company",
            "vnfProductName": "Sample VNF",
            "vnfSoftwareVersion": "1.0",
            "vnfdVersion": "1.0",
            "onboardingState": "ONBOARDED",
            "operationalState": "ENABLED",
            "usageState": "NOT_IN_USE"
        }
        return data
