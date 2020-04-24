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

from tacker.vnfm.lcm_user_data.abstract_user_data import AbstractUserData


class SampleUserData(AbstractUserData):

    @staticmethod
    def instantiate(base_hot_dict=None,
                    vnfd_dict=None,
                    inst_req_info=None,
                    grant_info=None):

        # return non dict value
        return 'DUMMY'
