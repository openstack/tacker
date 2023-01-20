#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from tacker.tests.functional.sol_enhanced_policy.base import (
    VimAPIsTest)


class VimAPIsOpenstackTest(VimAPIsTest):

    def test_vim_apis_vim_with_area_openstack(self):
        self._test_vim_apis_enhanced_policy('openstack', 'local-vim.yaml')

    def test_vim_apis_vim_without_area_openstack(self):
        self._test_vim_apis_vim_without_area_attribute(
            'openstack', 'local-vim.yaml')
