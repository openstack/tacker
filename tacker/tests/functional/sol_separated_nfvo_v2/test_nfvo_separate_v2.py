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

from tacker.tests.functional.sol_v2_common import test_vnflcm_basic_common


class VnfLcmWithNfvoSeparator(test_vnflcm_basic_common.CommonVnfLcmTest):

    def test_basic_lcms_max(self):
        self.basic_lcms_max_common_test(True)

    def test_basic_lcms_min(self):
        self.basic_lcms_min_common_test(True)

    def test_change_vnfpkg(self):
        self.change_vnfpkg_from_image_to_image_common_test(True)

    def test_retry_rollback_scale_out(self):
        self.retry_rollback_scale_out_common_test(True)

    def test_fail_instantiate(self):
        self.fail_instantiate_common_test(True)
