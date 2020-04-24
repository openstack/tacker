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

import abc
import six

from tacker.extensions import vnfm


@six.add_metaclass(abc.ABCMeta)
class AbstractUserData(object):

    @staticmethod
    @abc.abstractmethod
    def instantiate(vnfd_dict=None,
                    vdu_image_dict=None,
                    cp_vl_dict=None):
        error_reason = _(
            "failed to execute UserData because not implemented.")
        raise vnfm.LCMUserDataFailed(reason=error_reason)
