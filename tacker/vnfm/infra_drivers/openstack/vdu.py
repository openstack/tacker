# Copyright 2018 NTT DATA
# All Rights Reserved.
#
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

from oslo_config import cfg
from oslo_log import log as logging

from tacker.plugins.common import constants
from tacker.vnfm.infra_drivers.openstack import heat_client as hc
from tacker.vnfm import utils as vnfm_utils
from tacker.vnfm import vim_client


LOG = logging.getLogger(__name__)
CONF = cfg.CONF


class Vdu(object):
    def __init__(self, context, vnf_dict, heal_request_data_obj):
        super(Vdu, self).__init__()
        self.context = context
        self.vnf_dict = vnf_dict
        self.heal_request_data_obj = heal_request_data_obj
        self.stack_id = self.heal_request_data_obj.stack_id
        vim_id = self.vnf_dict['vim_id']
        vim_res = vim_client.VimClient().get_vim(context, vim_id)
        placement_attr = vnf_dict.get('placement_attr', {})
        auth_attr = vim_res['vim_auth']
        region_name = placement_attr.get('region_name', None)
        self.heat_client = hc.HeatClient(auth_attr=auth_attr,
                                         region_name=region_name)

    def _get_resource_status(self, stack_id, rsc_name):
        # Get the status of VDU resource from heat
        vdu_resource = self.heat_client.resource_get(stack_id=stack_id,
                                                     rsc_name=rsc_name)
        return vdu_resource.resource_status

    def _resource_mark_unhealthy(self):
        """Mark the resource unhealthy using heat."""

        additional_params = self.heal_request_data_obj.additional_params
        for additional_param in additional_params:
            resource_name = additional_param.parameter
            res_status = self._get_resource_status(self.stack_id,
                                                   resource_name)
            if res_status != 'CHECK_FAILED':
                self.heat_client.resource_mark_unhealthy(
                    stack_id=self.stack_id,
                    resource_name=resource_name, mark_unhealthy=True,
                    resource_status_reason=additional_param.cause)
                LOG.debug("Heat stack '%s' resource '%s' marked as "
                          "unhealthy", self.stack_id,
                          resource_name)
                evt_details = (("HealVnfRequest invoked to mark resource "
                                "'%s' to unhealthy.") % resource_name)
                vnfm_utils.log_events(self.context, self.vnf_dict,
                                      constants.RES_EVT_HEAL,
                                      evt_details)
            else:
                LOG.debug("Heat stack '%s' resource '%s' already mark "
                          "unhealthy.", self.stack_id,
                          resource_name)

    def heal_vdu(self):
        """Update stack using heat.

         This will re-create the resource which are mark as unhealthy.
         """

        # Mark all the resources as unhealthy
        self._resource_mark_unhealthy()
        self.heat_client.update(stack_id=self.stack_id,
                                existing=True)
        LOG.debug("Heat stack '%s' update initiated to revive "
                  "unhealthy resources.", self.stack_id)
        evt_details = (("HealVnfRequest invoked to update the stack "
                        "'%s'") % self.stack_id)
        vnfm_utils.log_events(self.context, self.vnf_dict,
                              constants.RES_EVT_HEAL, evt_details)
