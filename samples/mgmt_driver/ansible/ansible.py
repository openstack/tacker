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
from oslo_utils import encodeutils
from tacker.common import log
from tacker.vnfm.mgmt_drivers import constants as mgmt_constants
from tacker.vnfm.mgmt_drivers import vnflcm_abstract_driver

from tacker.vnfm.mgmt_drivers.ansible import ansible_driver

LOG = logging.getLogger(__name__)


def get_class():
    '''Returns the class name of the action driver'''
    return 'DeviceMgmtAnsible'


class DeviceMgmtAnsible(vnflcm_abstract_driver.VnflcmMgmtAbstractDriver):
    def get_type(self):
        return "ansible_driver"

    def get_name(self):
        return "ansible_driver"

    def get_description(self):
        return "Tacker VNFMgmt Ansible Driver"

    def instantiate_start(self, context, vnf_instance,
                          instantiate_vnf_request, grant,
                          grant_request, **kwargs):
        pass

    @log.log
    def instantiate_end(self, context, vnf_instance,
                        instantiate_vnf_request, grant,
                        grant_request, **kwargs):
        try:
            LOG.debug("Start of Ansible Driver")
            driver = ansible_driver.AnsibleDriver()
            driver._driver_process_flow(context, vnf_instance,
                mgmt_constants.ACTION_INSTANTIATE_VNF,
                instantiate_vnf_request, **kwargs)
        except Exception as e:
            raise Exception("Ansible Driver Error: %s",
                encodeutils.exception_to_unicode(e))

    @log.log
    def terminate_start(self, context, vnf_instance,
                        terminate_vnf_request, grant,
                        grant_request, **kwargs):
        try:
            LOG.debug("Start of Ansible Driver")
            driver = ansible_driver.AnsibleDriver()
            driver._driver_process_flow(context, vnf_instance,
                mgmt_constants.ACTION_TERMINATE_VNF,
                terminate_vnf_request, **kwargs)
        except Exception as e:
            raise Exception("Ansible Driver Error: %s",
                encodeutils.exception_to_unicode(e))

    def terminate_end(self, context, vnf_instance,
                      terminate_vnf_request, grant,
                      grant_request, **kwargs):
        pass

    @log.log
    def scale_start(self, context, vnf_instance,
                    scale_vnf_request, grant,
                    grant_request, **kwargs):
        try:
            LOG.debug("Start of Ansible Driver")
            driver = ansible_driver.AnsibleDriver()
            driver._driver_process_flow(context, vnf_instance,
                mgmt_constants.ACTION_SCALE_IN_VNF,
                scale_vnf_request, **kwargs)
        except Exception as e:
            raise Exception("Ansible Driver Error: %s",
                encodeutils.exception_to_unicode(e))

    @log.log
    def scale_end(self, context, vnf_instance,
                  scale_vnf_request, grant,
                  grant_request, **kwargs):
        try:
            LOG.debug("Start of Ansible Driver")
            driver = ansible_driver.AnsibleDriver()
            driver._driver_process_flow(context, vnf_instance,
                mgmt_constants.ACTION_SCALE_OUT_VNF,
                scale_vnf_request, **kwargs)
        except Exception as e:
            raise Exception("Ansible Driver Error: %s",
                encodeutils.exception_to_unicode(e))

    def heal_start(self, context, vnf_instance,
                   heal_vnf_request, grant,
                   grant_request, **kwargs):
        pass

    @log.log
    def heal_end(self, context, vnf_instance,
                 heal_vnf_request, grant,
                 grant_request, **kwargs):
        try:
            LOG.debug("Start of Ansible Driver")
            driver = ansible_driver.AnsibleDriver()
            driver._driver_process_flow(context, vnf_instance,
                mgmt_constants.ACTION_HEAL_VNF,
                heal_vnf_request, **kwargs)
        except Exception as e:
            raise Exception("Ansible Driver Error: %s",
                encodeutils.exception_to_unicode(e))

    def change_external_connectivity_start(
            self, context, vnf_instance,
            change_ext_conn_request, grant,
            grant_request, **kwargs):
        pass

    def change_external_connectivity_end(
            self, context, vnf_instance,
            change_ext_conn_request, grant,
            grant_request, **kwargs):
        pass

    def modify_information_start(
            self, context, vnf_instance,
            modify_vnf_request, **kwargs):
        pass

    def modify_information_end(
            self, context, vnf_instance,
            modify_vnf_request, **kwargs):
        pass
