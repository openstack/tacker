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
import tacker.vnfm.lcm_user_data.utils as UserDataUtil


class SampleUserData(AbstractUserData):
    @staticmethod
    def instantiate(base_hot_dict=None,
                    vnfd_dict=None,
                    inst_req_info=None,
                    grant_info=None):
        api_param = UserDataUtil.get_diff_base_hot_param_from_api(
            base_hot_dict, inst_req_info)
        initial_param_dict = \
            UserDataUtil.create_initial_param_server_port_dict(
                base_hot_dict)
        vdu_flavor_dict = \
            UserDataUtil.create_vdu_flavor_capability_name_dict(vnfd_dict)
        vdu_image_dict = UserDataUtil.create_sw_image_dict(vnfd_dict)
        cpd_vl_dict = UserDataUtil.create_network_dict(
            inst_req_info, initial_param_dict)
        final_param_dict = UserDataUtil.create_final_param_dict(
            initial_param_dict, vdu_flavor_dict, vdu_image_dict, cpd_vl_dict)
        return {**final_param_dict, **api_param}
