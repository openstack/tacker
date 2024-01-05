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

import time

from oslo_log import log as logging

import tacker.vnfm.lcm_user_data.utils as UserDataUtil

from tacker.vnfm.lcm_user_data.abstract_user_data import AbstractUserData
from tacker.vnfm.lcm_user_data.constants import USER_DATA_TIMEOUT

LOG = logging.getLogger(__name__)


class SampleUserData(AbstractUserData):

    @staticmethod
    def instantiate(base_hot_dict=None,
                    vnfd_dict=None,
                    inst_req_info=None,
                    grant_info=None):

        # Sleep more than timeout.
        LOG.debug('Sleep start.')
        time.sleep(USER_DATA_TIMEOUT + 60)
        LOG.debug('Sleep end.')

        # Create HOT input parameter using util functions.
        initial_param_dict = UserDataUtil.create_initial_param_dict(
            base_hot_dict)

        vdu_flavor_dict = UserDataUtil.create_vdu_flavor_dict(vnfd_dict)
        vdu_image_dict = UserDataUtil.create_vdu_image_dict(grant_info)
        cpd_vl_dict = UserDataUtil.create_cpd_vl_dict(
            base_hot_dict, inst_req_info)

        final_param_dict = UserDataUtil.create_final_param_dict(
            initial_param_dict, vdu_flavor_dict, vdu_image_dict, cpd_vl_dict)

        return final_param_dict
