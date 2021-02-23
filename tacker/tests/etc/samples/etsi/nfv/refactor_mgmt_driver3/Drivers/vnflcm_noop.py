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

from oslo_log import log as logging

from tacker.vnfm.mgmt_drivers import vnflcm_abstract_driver


LOG = logging.getLogger(__name__)


class VnflcmMgmtNoop(vnflcm_abstract_driver.VnflcmMgmtAbstractDriver):

    # instantiate start
    def instantiate_start(self, vnf_instance, additional_params, **kwargs):
        LOG.debug('instantiate_start %(vnf_instance)s '
                  '%(additional_params)s %(kwargs)s',
                  {'vnf_instance': vnf_instance,
                   'additional_params': additional_params, 'kwargs': kwargs})
        pass

    def instantiate_end(self, vnf_instance, additional_params, **kwargs):
        LOG.debug('instantiate_end %(vnf_instance)s '
                  '%(additional_params)s %(kwargs)s',
                  {'vnf_instance': vnf_instance,
                   'additional_params': additional_params, 'kwargs': kwargs})
        pass

    def terminate_start(self, vnf_instance, additional_params, **kwargs):
        LOG.debug('terminate_start %(vnf_instance)s '
                  '%(additional_params)s %(kwargs)s',
                  {'vnf_instance': vnf_instance,
                   'additional_params': additional_params, 'kwargs': kwargs})
        pass

    def terminate_end(self, vnf_instance, additional_params, **kwargs):
        LOG.debug('terminate_end %(vnf_instance)s '
                  '%(additional_params)s %(kwargs)s',
                  {'vnf_instance': vnf_instance,
                   'additional_params': additional_params, 'kwargs': kwargs})
        pass

    def scale_start(self, vnf_instance, additional_params, **kwargs):
        LOG.debug('scale_start %(vnf_instance)s '
                  '%(additional_params)s %(kwargs)s',
                  {'vnf_instance': vnf_instance,
                   'additional_params': additional_params, 'kwargs': kwargs})
        pass

    def scale_end(self, vnf_instance, additional_params, **kwargs):
        LOG.debug('scale_end %(vnf_instance)s '
                  '%(additional_params)s %(kwargs)s',
                  {'vnf_instance': vnf_instance,
                   'additional_params': additional_params, 'kwargs': kwargs})
        pass

    def heal_start(self, vnf_instance, additional_params, **kwargs):
        LOG.debug('heal_start %(vnf_instance)s '
                  '%(additional_params)s %(kwargs)s',
                  {'vnf_instance': vnf_instance,
                   'additional_params': additional_params, 'kwargs': kwargs})
        pass

    def heal_end(self, vnf_instance, additional_params, **kwargs):
        LOG.debug('heal_end %(vnf_instance)s '
                  '%(additional_params)s %(kwargs)s',
                  {'vnf_instance': vnf_instance,
                   'additional_params': additional_params, 'kwargs': kwargs})
        pass
