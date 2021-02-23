# Copyright (C) 2020 FUJITSU
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

from tacker.common import log
from tacker.vnfm.mgmt_drivers import vnflcm_abstract_driver


class VnflcmMgmtNoop(vnflcm_abstract_driver.VnflcmMgmtAbstractDriver):
    def get_type(self):
        return 'vnflcm_noop'

    def get_name(self):
        return 'vnflcm_noop'

    def get_description(self):
        return 'Tacker VNFMgmt VnflcmNoop Driver'

    @log.log
    def instantiate_start(self, context, vnf_instance,
                          additional_params, **kwargs):
        pass

    @log.log
    def instantiate_end(self, context, vnf_instance,
                        additional_params, **kwargs):
        pass

    @log.log
    def terminate_start(self, context, vnf_instance,
                        additional_params, **kwargs):
        pass

    @log.log
    def terminate_end(self, context, vnf_instance,
                      additional_params, **kwargs):
        pass

    @log.log
    def scale_start(self, context, vnf_instance,
                    additional_params, **kwargs):
        pass

    @log.log
    def scale_end(self, context, vnf_instance,
                  additional_params, **kwargs):
        pass

    @log.log
    def heal_start(self, context, vnf_instance,
                   additional_params, **kwargs):
        pass

    @log.log
    def heal_end(self, context, vnf_instance,
                 additional_params, **kwargs):
        pass
