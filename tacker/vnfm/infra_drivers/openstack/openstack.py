# Copyright 2015 Intel Corporation.
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

import time

from oslo_config import cfg
from oslo_log import log as logging
from oslo_serialization import jsonutils
import yaml

from tacker.common import log
from tacker.common import utils
from tacker.extensions import vnfm
from tacker.vnfm.infra_drivers import abstract_driver
from tacker.vnfm.infra_drivers.openstack import constants as infra_cnst
from tacker.vnfm.infra_drivers.openstack import heat_client as hc
from tacker.vnfm.infra_drivers.openstack import translate_template
from tacker.vnfm.infra_drivers.openstack import vdu
from tacker.vnfm.infra_drivers import scale_driver


LOG = logging.getLogger(__name__)
CONF = cfg.CONF

OPTS = [
    cfg.IntOpt('stack_retries',
               default=60,
               help=_("Number of attempts to retry for stack"
                      " creation/deletion")),
    cfg.IntOpt('stack_retry_wait',
               default=10,
               help=_("Wait time (in seconds) between consecutive stack"
                      " create/delete retries")),
]

CONF.register_opts(OPTS, group='openstack_vim')


def config_opts():
    return [('openstack_vim', OPTS)]


# Global map of individual resource type and
# incompatible properties, alternate properties pair for
# upgrade/downgrade across all Heat template versions (starting Kilo)
#
# Maintains a dictionary of {"resource type": {dict of "incompatible
# property": "alternate_prop"}}

HEAT_VERSION_INCOMPATIBILITY_MAP = {'OS::Neutron::Port': {
    'port_security_enabled': 'value_specs', }, }

HEAT_TEMPLATE_BASE = """
heat_template_version: 2013-05-23
"""

OUTPUT_PREFIX = 'mgmt_ip-'
ALARMING_POLICY = 'tosca.policies.tacker.Alarming'
SCALING_POLICY = 'tosca.policies.tacker.Scaling'


def get_scaling_policy_name(action, policy_name):
    return '%s_scale_%s' % (policy_name, action)


class OpenStack(abstract_driver.VnfAbstractDriver,
                scale_driver.VnfScaleAbstractDriver):
    """Openstack infra driver for hosting vnfs"""

    def __init__(self):
        super(OpenStack, self).__init__()
        self.STACK_RETRIES = cfg.CONF.openstack_vim.stack_retries
        self.STACK_RETRY_WAIT = cfg.CONF.openstack_vim.stack_retry_wait

    def get_type(self):
        return 'openstack'

    def get_name(self):
        return 'openstack'

    def get_description(self):
        return 'Openstack infra driver'

    @log.log
    def create(self, plugin, context, vnf, auth_attr):
        LOG.debug('vnf %s', vnf)

        region_name = vnf.get('placement_attr', {}).get('region_name', None)
        heatclient = hc.HeatClient(auth_attr, region_name)

        tth = translate_template.TOSCAToHOT(vnf, heatclient)
        tth.generate_hot()
        stack = self._create_stack(heatclient, tth.vnf, tth.fields)
        return stack['stack']['id']

    @log.log
    def _create_stack(self, heatclient, vnf, fields):
        if 'stack_name' not in fields:
            name = vnf['name'].replace(' ', '_') + '_' + vnf['id']
            if vnf['attributes'].get('failure_count'):
                name += ('-RESPAWN-%s') % str(vnf['attributes'][
                    'failure_count'])
            fields['stack_name'] = name

        # service context is ignored
        LOG.debug('service_context: %s', vnf.get('service_context', []))
        LOG.debug('fields: %s', fields)
        LOG.debug('template: %s', fields['template'])
        stack = heatclient.create(fields)

        return stack

    @log.log
    def create_wait(self, plugin, context, vnf_dict, vnf_id, auth_attr):
        region_name = vnf_dict.get('placement_attr', {}).get(
            'region_name', None)
        heatclient = hc.HeatClient(auth_attr, region_name)

        stack, status, stack_retries = self._wait_until_stack_ready(
            vnf_id, auth_attr, infra_cnst.STACK_CREATE_IN_PROGRESS,
            region_name=region_name)

        if stack_retries == 0 and status != infra_cnst.STACK_CREATE_COMPLETE:
            error_reason = _("Resource creation is not completed within"
                             " {wait} seconds as creation of stack {stack}"
                             " is not completed").format(
                wait=(self.STACK_RETRIES *
                      self.STACK_RETRY_WAIT),
                stack=vnf_id)
            LOG.warning("VNF Creation failed: %(reason)s",
                        {'reason': error_reason})
            raise vnfm.VNFCreateWaitFailed(reason=error_reason)

        elif stack_retries != 0 and status != infra_cnst.STACK_CREATE_COMPLETE:
            error_reason = stack.stack_status_reason
            raise vnfm.VNFCreateWaitFailed(reason=error_reason)

        # scaling enabled
        if vnf_dict['attributes'].get('scaling_group_names'):
            group_names = jsonutils.loads(
                vnf_dict['attributes'].get('scaling_group_names')).values()
            mgmt_ips = self._find_mgmt_ips_from_groups(heatclient,
                                                       vnf_id,
                                                       group_names)
        else:
            mgmt_ips = self._find_mgmt_ips(stack.outputs)

        if mgmt_ips:
            vnf_dict['mgmt_ip_address'] = jsonutils.dump_as_bytes(mgmt_ips)

    def _wait_until_stack_ready(self, vnf_id, auth_attr, wait_status,
                                region_name=None):
        heatclient = hc.HeatClient(auth_attr, region_name)
        stack = heatclient.get(vnf_id)
        status = stack.stack_status
        stack_retries = self.STACK_RETRIES
        while status == wait_status and stack_retries > 0:
            time.sleep(self.STACK_RETRY_WAIT)
            try:
                stack = heatclient.get(vnf_id)
            except Exception:
                LOG.warning("VNF Instance setup may not have "
                            "happened because Heat API request failed "
                            "while waiting for the stack %(stack)s to be "
                            "created", {'stack': vnf_id})
                # continue to avoid temporary connection error to target
                # VIM
            status = stack.stack_status
            LOG.debug('status: %s', status)
            stack_retries = stack_retries - 1
        LOG.debug('stack status: %(stack)s %(status)s',
                  {'stack': str(stack), 'status': status})

        return stack, status, stack_retries

    def _find_mgmt_ips(self, outputs):
        LOG.debug('outputs %s', outputs)
        mgmt_ips = dict((output['output_key'][len(OUTPUT_PREFIX):],
                         output['output_value'])
                        for output in outputs
                        if output.get('output_key',
                                      '').startswith(OUTPUT_PREFIX))
        return mgmt_ips

    @log.log
    def update(self, plugin, context, vnf_id, vnf_dict, vnf,
               auth_attr):
        region_name = vnf_dict.get('placement_attr', {}).get(
            'region_name', None)
        heatclient = hc.HeatClient(auth_attr, region_name)
        heatclient.get(vnf_id)

        # update config attribute
        config_yaml = vnf_dict.get('attributes', {}).get('config', '')
        update_yaml = vnf['vnf'].get('attributes', {}).get('config', '')
        LOG.debug('yaml orig %(orig)s update %(update)s',
                  {'orig': config_yaml, 'update': update_yaml})

        # If config_yaml is None, yaml.safe_load() will raise Attribute Error.
        # So set config_yaml to {}, if it is None.
        if not config_yaml:
            config_dict = {}
        else:
            config_dict = yaml.safe_load(config_yaml) or {}
        update_dict = yaml.safe_load(update_yaml)
        if not update_dict:
            return

        LOG.debug('dict orig %(orig)s update %(update)s',
                  {'orig': config_dict, 'update': update_dict})
        utils.deep_update(config_dict, update_dict)
        LOG.debug('dict new %(new)s update %(update)s',
                  {'new': config_dict, 'update': update_dict})
        new_yaml = yaml.safe_dump(config_dict)
        vnf_dict.setdefault('attributes', {})['config'] = new_yaml

    @log.log
    def update_wait(self, plugin, context, vnf_dict, auth_attr,
                    region_name=None):
        stack, status, stack_retries = self._wait_until_stack_ready(
            vnf_dict['instance_id'], auth_attr,
            infra_cnst.STACK_UPDATE_IN_PROGRESS,
            region_name=region_name)

        if stack_retries == 0 and status != infra_cnst.STACK_UPDATE_COMPLETE:
            error_reason = _("Resource updation is not completed within"
                             " {wait} seconds as updation of stack {stack}"
                             " is not completed").format(
                wait=(self.STACK_RETRIES * self.STACK_RETRY_WAIT),
                stack=vnf_dict['instance_id'])
            LOG.error("VNF Updation failed: %(reason)s",
                      {'reason': error_reason})
            raise vnfm.VNFUpdateWaitFailed(reason=error_reason)

        elif stack_retries != 0 and (status !=
                                     infra_cnst.STACK_UPDATE_COMPLETE):
            error_reason = stack.stack_status_reason
            raise vnfm.VNFUpdateWaitFailed(reason=error_reason)

        mgmt_ips = self._find_mgmt_ips(stack.outputs)

        if mgmt_ips:
            vnf_dict['mgmt_ip_address'] = jsonutils.dump_as_bytes(mgmt_ips)

    @log.log
    def delete(self, plugin, context, vnf_id, auth_attr, region_name=None):
        heatclient = hc.HeatClient(auth_attr, region_name)
        heatclient.delete(vnf_id)

    @log.log
    def delete_wait(self, plugin, context, vnf_id, auth_attr,
                    region_name=None):
        stack, status, stack_retries = self._wait_until_stack_ready(
            vnf_id, auth_attr, infra_cnst.STACK_DELETE_IN_PROGRESS,
            region_name=region_name)

        if stack_retries == 0 and status != infra_cnst.STACK_DELETE_COMPLETE:
            error_reason = _("Resource cleanup for vnf is"
                             " not completed within {wait} seconds as "
                             "deletion of Stack {stack} is "
                             "not completed").format(stack=vnf_id,
                             wait=(self.STACK_RETRIES * self.STACK_RETRY_WAIT))
            LOG.warning(error_reason)
            raise vnfm.VNFDeleteWaitFailed(reason=error_reason)

        if stack_retries != 0 and status != infra_cnst.STACK_DELETE_COMPLETE:
            error_reason = _("VNF {vnf_id} deletion is not completed. "
                            "{stack_status}").format(vnf_id=vnf_id,
                            stack_status=status)
            LOG.warning(error_reason)
            raise vnfm.VNFDeleteWaitFailed(reason=error_reason)

    @classmethod
    def _find_mgmt_ips_from_groups(cls, heat_client, instance_id, group_names):

        def _find_mgmt_ips(attributes):
            mgmt_ips = {}
            for k, v in attributes.items():
                if k.startswith(OUTPUT_PREFIX):
                    mgmt_ips[k.replace(OUTPUT_PREFIX, '')] = v

            return mgmt_ips

        mgmt_ips = {}
        for group_name in group_names:
            # Get scale group
            grp = heat_client.resource_get(instance_id, group_name)
            for rsc in heat_client.resource_get_list(grp.physical_resource_id):
                # Get list of resources in scale group
                scale_rsc = heat_client.resource_get(grp.physical_resource_id,
                                                     rsc.resource_name)

                # findout the mgmt ips from attributes
                for k, v in _find_mgmt_ips(scale_rsc.attributes).items():
                    if k not in mgmt_ips:
                        mgmt_ips[k] = [v]
                    else:
                        mgmt_ips[k].append(v)

        return mgmt_ips

    @log.log
    def scale(self, context, plugin, auth_attr, policy, region_name):
        heatclient = hc.HeatClient(auth_attr, region_name)
        policy_rsc = get_scaling_policy_name(policy_name=policy['name'],
                                             action=policy['action'])
        events = heatclient.resource_event_list(policy['instance_id'],
                                                policy_rsc, limit=1,
                                                sort_dir='desc',
                                                sort_keys='event_time')

        heatclient.resource_signal(policy['instance_id'], policy_rsc)
        return events[0].id

    @log.log
    def scale_wait(self, context, plugin, auth_attr, policy, region_name,
                   last_event_id):
        heatclient = hc.HeatClient(auth_attr, region_name)

        # TODO(kanagaraj-manickam) make wait logic into separate utility method
        # and make use of it here and other actions like create and delete
        stack_retries = self.STACK_RETRIES
        while (True):
            try:
                time.sleep(self.STACK_RETRY_WAIT)
                stack_id = policy['instance_id']
                policy_name = get_scaling_policy_name(
                    policy_name=policy['name'], action=policy['action'])
                events = heatclient.resource_event_list(stack_id, policy_name,
                                                        limit=1,
                                                        sort_dir='desc',
                                                        sort_keys='event_time')

                if events[0].id != last_event_id:
                    if events[0].resource_status == 'SIGNAL_COMPLETE':
                        break
                else:
                    # When the number of instance reaches min or max, the below
                    # comparision will let VNF status turn into ACTIVE state.
                    if events[0].resource_status == 'CREATE_COMPLETE' or \
                            events[0].resource_status == 'SIGNAL_COMPLETE':
                        break
            except Exception as e:
                error_reason = _("VNF scaling failed for stack %(stack)s with "
                                 "error %(error)s") % {
                                     'stack': policy['instance_id'],
                                     'error': str(e)}
                LOG.warning(error_reason)
                raise vnfm.VNFScaleWaitFailed(vnf_id=policy['vnf']['id'],
                                              reason=error_reason)

            if stack_retries == 0:
                metadata = heatclient.resource_metadata(stack_id, policy_name)
                if not metadata['scaling_in_progress']:
                    error_reason = _('When signal occurred within cool down '
                                     'window, no events generated from heat, '
                                     'so ignore it')
                    LOG.warning(error_reason)
                    break
                error_reason = _(
                    "VNF scaling failed to complete within %{wait}s seconds "
                    "while waiting for the stack %(stack)s to be "
                    "scaled.") % {'stack': stack_id,
                                  'wait': self.STACK_RETRIES *
                                  self.STACK_RETRY_WAIT}
                LOG.warning(error_reason)
                raise vnfm.VNFScaleWaitFailed(vnf_id=policy['vnf']['id'],
                                              reason=error_reason)
            stack_retries -= 1

        def _fill_scaling_group_name():
            vnf = policy['vnf']
            scaling_group_names = vnf['attributes']['scaling_group_names']
            policy['group_name'] = jsonutils.loads(
                scaling_group_names)[policy['name']]

        _fill_scaling_group_name()

        mgmt_ips = self._find_mgmt_ips_from_groups(heatclient,
                                                   policy['instance_id'],
                                                   [policy['group_name']])

        return jsonutils.dump_as_bytes(mgmt_ips)

    @log.log
    def get_resource_info(self, plugin, context, vnf_info, auth_attr,
                          region_name=None):
        instance_id = vnf_info['instance_id']
        heatclient = hc.HeatClient(auth_attr, region_name)
        try:
            # nested_depth=2 is used to get VDU resources
            # in case of nested template
            resources_ids =\
                heatclient.resource_get_list(instance_id, nested_depth=2)
            details_dict = {resource.resource_name:
                            {"id": resource.physical_resource_id,
                             "type": resource.resource_type}
                            for resource in resources_ids}
            return details_dict
        # Raise exception when Heat API service is not available
        except Exception:
            raise vnfm.InfraDriverUnreachable(service="Heat API service")

    def heal_vdu(self, plugin, context, vnf_dict, heal_request_data_obj):
        try:
            heal_vdu = vdu.Vdu(context, vnf_dict, heal_request_data_obj)
            heal_vdu.heal_vdu()
        except Exception:
            LOG.error("VNF '%s' failed to heal", vnf_dict['id'])
            raise vnfm.VNFHealFailed(vnf_id=vnf_dict['id'])
