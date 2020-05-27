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


import eventlet
import importlib
import os
import sys
import time

from collections import OrderedDict
from oslo_config import cfg
from oslo_log import log as logging
from oslo_serialization import jsonutils
from oslo_utils import encodeutils
from oslo_utils import excutils
import yaml

from tacker._i18n import _
from tacker.common import exceptions
from tacker.common import log
from tacker.common import utils
from tacker.extensions import vnflcm
from tacker.extensions import vnfm
from tacker import objects
from tacker.tosca.utils import represent_odict
from tacker.vnfm.infra_drivers import abstract_driver
from tacker.vnfm.infra_drivers.openstack import constants as infra_cnst
from tacker.vnfm.infra_drivers.openstack import glance_client as gc
from tacker.vnfm.infra_drivers.openstack import heat_client as hc
from tacker.vnfm.infra_drivers.openstack import translate_template
from tacker.vnfm.infra_drivers.openstack import vdu
from tacker.vnfm.infra_drivers import scale_driver
from tacker.vnfm.lcm_user_data.constants import USER_DATA_TIMEOUT

eventlet.monkey_patch(time=True)

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
        self.IMAGE_RETRIES = 10
        self.IMAGE_RETRY_WAIT = 10

    def get_type(self):
        return 'openstack'

    def get_name(self):
        return 'openstack'

    def get_description(self):
        return 'Openstack infra driver'

    @log.log
    def create(self, plugin, context, vnf, auth_attr,
               base_hot_dict=None, vnf_package_path=None,
               inst_req_info=None, grant_info=None):
        LOG.debug('vnf %s', vnf)
        region_name = vnf.get('placement_attr', {}).get('region_name', None)
        heatclient = hc.HeatClient(auth_attr, region_name)
        additional_param = None
        if inst_req_info is not None:
            additional_param = inst_req_info.additional_params

        user_data_path = None
        user_data_class = None
        if additional_param is not None:
            LOG.debug('additional_param: %s', additional_param)
            user_data_path = additional_param.get(
                'lcm-operation-user-data')
            user_data_class = additional_param.get(
                'lcm-operation-user-data-class')
            LOG.debug('UserData path: %s', user_data_path)
            LOG.debug('UserData class: %s', user_data_class)

        if user_data_path is not None and user_data_class is not None:
            LOG.info('Execute user data and create heat-stack.')
            if base_hot_dict is None:
                error_reason = _("failed to get Base HOT.")
                raise vnfm.LCMUserDataFailed(reason=error_reason)

            vnfd_str = vnf['vnfd']['attributes']['vnfd']
            vnfd_dict = yaml.safe_load(vnfd_str)
            LOG.debug('VNFD: %s', vnfd_dict)
            LOG.debug('VNF package path: %s', vnf_package_path)
            sys.path.append(vnf_package_path)
            user_data_module = os.path.splitext(
                user_data_path.lstrip('./'))[0].replace('/', '.')
            LOG.debug('UserData module: %s', user_data_module)
            LOG.debug('Append sys.path: %s', sys.path)
            try:
                module = importlib.import_module(user_data_module)
                LOG.debug('Append sys.modules: %s', sys.modules)
            except Exception:
                self._delete_user_data_module(user_data_module)
                error_reason = _(
                    "failed to get UserData path based on "
                    "lcm-operation-user-data from additionalParams.")
                raise vnfm.LCMUserDataFailed(reason=error_reason)
            finally:
                sys.path.remove(vnf_package_path)
                LOG.debug('Remove sys.path: %s', sys.path)

            try:
                klass = getattr(module, user_data_class)
            except Exception:
                self._delete_user_data_module(user_data_module)
                error_reason = _(
                    "failed to get UserData class based on "
                    "lcm-operation-user-data-class from additionalParams.")
                raise vnfm.LCMUserDataFailed(reason=error_reason)

            # Set the timeout and execute the UserData script.
            hot_param_dict = None
            with eventlet.timeout.Timeout(USER_DATA_TIMEOUT, False):
                try:
                    hot_param_dict = klass.instantiate(
                        base_hot_dict, vnfd_dict, inst_req_info, grant_info)
                except Exception:
                    raise
                finally:
                    self._delete_user_data_module(user_data_module)

            if hot_param_dict is not None:
                LOG.info('HOT input parameter: %s', hot_param_dict)
            else:
                error_reason = _(
                    "fails due to timeout[sec]: %s") % USER_DATA_TIMEOUT
                raise vnfm.LCMUserDataFailed(reason=error_reason)
            if not isinstance(hot_param_dict, dict):
                error_reason = _(
                    "return value as HOT parameter from UserData "
                    "is not in dict format.")
                raise vnfm.LCMUserDataFailed(reason=error_reason)

            # Create heat-stack with BaseHOT and parameters
            stack = self._create_stack_with_user_data(
                heatclient, vnf, base_hot_dict, hot_param_dict)

        elif user_data_path is None and user_data_class is None:
            LOG.info('Execute heat-translator and create heat-stack.')
            tth = translate_template.TOSCAToHOT(vnf, heatclient,
                                                inst_req_info, grant_info)
            tth.generate_hot()
            stack = self._create_stack(heatclient, tth.vnf, tth.fields)
        else:
            error_reason = _(
                "failed to get lcm-operation-user-data or "
                "lcm-operation-user-data-class from additionalParams.")
            raise vnfm.LCMUserDataFailed(reason=error_reason)

        return stack['stack']['id']

    @log.log
    def _delete_user_data_module(self, user_data_module):
        # Delete module recursively.
        mp_list = user_data_module.split('.')
        while True:
            del_module = '.'.join(mp_list)
            print(del_module)
            if del_module in sys.modules:
                del sys.modules[del_module]
            if len(mp_list) == 1:
                break
            mp_list = mp_list[0:-1]
        LOG.debug('Remove sys.modules: %s', sys.modules)

    @log.log
    def _create_stack_with_user_data(self, heatclient, vnf,
                                     base_hot_dict, hot_param_dict):
        fields = {}
        fields['stack_name'] = ("vnflcm_" + vnf["id"])
        fields['template'] = self._format_base_hot(base_hot_dict)
        fields['parameters'] = hot_param_dict

        LOG.debug('fields: %s', fields)
        LOG.debug('template: %s', fields['template'])
        stack = heatclient.create(fields)

        return stack

    @log.log
    def _format_base_hot(self, base_hot_dict):
        yaml.SafeDumper.add_representer(OrderedDict,
        lambda dumper, value: represent_odict(dumper,
                                              u'tag:yaml.org,2002:map', value))

        return yaml.safe_dump(base_hot_dict)

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

        stack = self._wait_until_stack_ready(
            vnf_id, auth_attr, infra_cnst.STACK_CREATE_IN_PROGRESS,
            infra_cnst.STACK_CREATE_COMPLETE,
            vnfm.VNFCreateWaitFailed, region_name=region_name)

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
                                expected_status, exception_class,
                                region_name=None):
        heatclient = hc.HeatClient(auth_attr, region_name)
        stack_retries = self.STACK_RETRIES
        status = wait_status
        stack = None
        while stack_retries > 0:
            try:
                stack_retries = stack_retries - 1
                stack = heatclient.get(vnf_id)
                status = stack.stack_status
                if status == expected_status:
                    LOG.debug('stack status: %(stack)s %(status)s',
                              {'stack': str(stack), 'status': status})
                    return stack
                time.sleep(self.STACK_RETRY_WAIT)
                LOG.debug('status: %s', status)
            except Exception:
                LOG.warning("VNF Instance setup may not have "
                            "happened because Heat API request failed "
                            "while waiting for the stack %(stack)s to be "
                            "created", {'stack': vnf_id})
                # continue to avoid temporary connection error to target
                # VIM
            if stack_retries == 0 and status != expected_status:
                error_reason = _("action is not completed within {wait} "
                                 "seconds on stack {stack}").format(
                    wait=(self.STACK_RETRIES *
                          self.STACK_RETRY_WAIT),
                    stack=vnf_id)
                raise exception_class(reason=error_reason)
            elif stack_retries != 0 and status != wait_status:
                error_reason = stack.stack_status_reason
                LOG.warning(error_reason)
                raise exception_class(reason=error_reason)

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

        update_param_yaml = vnf['vnf'].get('attributes', {}).get(
            'param_values', '')
        update_config_yaml = vnf['vnf'].get('attributes', {}).get(
            'config', '')

        if update_param_yaml:
            # conversion param_values
            param_yaml = vnf_dict.get('attributes', {}).get('param_values', '')
            param_dict = yaml.safe_load(param_yaml)
            update_param_dict = yaml.safe_load(update_param_yaml)

            # check update values
            update_values = {}
            for key, value in update_param_dict.items():
                if key not in param_dict or\
                        update_param_dict[key] != param_dict[key]:
                    update_values[key] = value

            if not update_values:
                error_reason = _("at vnf_id {} because all parameters "
                                 "match the existing one.").format(vnf_id)
                LOG.warning(error_reason)
                raise vnfm.VNFUpdateInvalidInput(reason=error_reason)

            # update vnf_dict
            utils.deep_update(param_dict, update_param_dict)
            new_param_yaml = yaml.safe_dump(param_dict)
            vnf_dict.setdefault(
                'attributes', {})['param_values'] = new_param_yaml

            # run stack update
            stack_update_param = {
                'parameters': update_values,
                'existing': True}
            heatclient.update(vnf_id, **stack_update_param)

        elif not update_param_yaml and not update_config_yaml:
            error_reason = _("at vnf_id {} because the target "
                             "yaml is empty.").format(vnf_id)
            LOG.warning(error_reason)
            raise vnfm.VNFUpdateInvalidInput(reason=error_reason)

        # update config attribute
        config_yaml = vnf_dict.get('attributes', {}).get('config', '')
        LOG.debug('yaml orig %(orig)s update %(update)s',
                  {'orig': config_yaml, 'update': update_config_yaml})

        # If config_yaml is None, yaml.safe_load() will raise Attribute Error.
        # So set config_yaml to {}, if it is None.
        if not config_yaml:
            config_dict = {}
        else:
            config_dict = yaml.safe_load(config_yaml) or {}
        update_dict = yaml.safe_load(update_config_yaml)
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
        # do nothing but checking if the stack exists at the moment
        heatclient = hc.HeatClient(auth_attr, region_name)
        stack = heatclient.get(vnf_dict['instance_id'])

        mgmt_ips = self._find_mgmt_ips(stack.outputs)
        if mgmt_ips:
            vnf_dict['mgmt_ip_address'] = jsonutils.dump_as_bytes(mgmt_ips)

    @log.log
    def heal_wait(self, plugin, context, vnf_dict, auth_attr,
                  region_name=None):
        stack = self._wait_until_stack_ready(vnf_dict['instance_id'],
            auth_attr, infra_cnst.STACK_UPDATE_IN_PROGRESS,
            infra_cnst.STACK_UPDATE_COMPLETE,
            vnfm.VNFHealWaitFailed, region_name=region_name)

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
        self._wait_until_stack_ready(vnf_id, auth_attr,
            infra_cnst.STACK_DELETE_IN_PROGRESS,
            infra_cnst.STACK_DELETE_COMPLETE, vnfm.VNFDeleteWaitFailed,
                                     region_name=region_name)

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
                    "VNF scaling failed to complete within %(wait)s seconds "
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

    @log.log
    def pre_instantiation_vnf(self, context, vnf_instance,
                              vim_connection_info, vnf_software_images):
        glance_client = gc.GlanceClient(vim_connection_info)
        vnf_resources = {}

        def _roll_back_images():
            # Delete all previously created images for vnf
            for key, resources in vnf_resources.items():
                for vnf_resource in resources:
                    try:
                        glance_client.delete(vnf_resource.resource_identifier)
                    except Exception:
                        LOG.error("Failed to delete image %(uuid)s "
                                  "for vnf %(id)s",
                                  {"uuid": vnf_resource.resource_identifier,
                                  "id": vnf_instance.id})

        for node_name, vnf_sw_image in vnf_software_images.items():
            name = vnf_sw_image.name
            image_path = vnf_sw_image.image_path
            is_url = utils.is_url(image_path)

            if not is_url:
                filename = image_path
            else:
                filename = None

            try:
                LOG.info("Creating image %(name)s for vnf %(id)s",
                         {"name": name, "id": vnf_instance.id})

                image_data = {"min_disk": vnf_sw_image.min_disk,
                    "min_ram": vnf_sw_image.min_ram,
                    "disk_format": vnf_sw_image.disk_format,
                    "container_format": vnf_sw_image.container_format,
                    "visibility": "private"}

                if filename:
                    image_data.update({"filename": filename})

                image = glance_client.create(name, **image_data)

                LOG.info("Image %(name)s created successfully for vnf %(id)s",
                         {"name": name, "id": vnf_instance.id})
            except Exception as exp:
                with excutils.save_and_reraise_exception():
                    exp.reraise = False
                    LOG.error("Failed to create image %(name)s for vnf %(id)s "
                              "due to error: %(error)s",
                              {"name": name, "id": vnf_instance.id,
                              "error": encodeutils.exception_to_unicode(exp)})

                    # Delete previously created images
                    _roll_back_images()

                    raise exceptions.VnfPreInstantiationFailed(
                        id=vnf_instance.id,
                        error=encodeutils.exception_to_unicode(exp))
            try:
                if is_url:
                    glance_client.import_image(image, image_path)

                self._image_create_wait(image.id, vnf_sw_image, glance_client,
                    'active', vnflcm.ImageCreateWaitFailed)

                vnf_resource = objects.VnfResource(context=context,
                    vnf_instance_id=vnf_instance.id,
                    resource_name=name, resource_type="image",
                    resource_status="CREATED", resource_identifier=image.id)
                vnf_resources[node_name] = [vnf_resource]
            except Exception as exp:
                with excutils.save_and_reraise_exception():
                    exp.reraise = False
                    LOG.error("Image %(name)s not active for vnf %(id)s "
                              "error: %(error)s",
                              {"name": name, "id": vnf_instance.id,
                              "error": encodeutils.exception_to_unicode(exp)})

                    err_msg = "Failed to delete image %(uuid)s for vnf %(id)s"
                    # Delete the image
                    try:
                        glance_client.delete(image.id)
                    except Exception:
                        LOG.error(err_msg, {"uuid": image.id,
                                  "id": vnf_instance.id})

                    # Delete all previously created images for vnf
                    _roll_back_images()

                    raise exceptions.VnfPreInstantiationFailed(
                        id=vnf_instance.id,
                        error=encodeutils.exception_to_unicode(exp))

        return vnf_resources

    def _image_create_wait(self, image_uuid, vnf_software_image, glance_client,
                           expected_status, exception_class):
        retries = self.IMAGE_RETRIES

        while retries > 0:
            retries = retries - 1
            image = glance_client.get(image_uuid)
            status = image.status
            if status == expected_status:
                # NOTE(tpatil): If image is uploaded using import_image
                # ,sdk doesn't validate checksum. So, verify checksum/hash
                # for both scenarios upload from file and URL here.
                if vnf_software_image.hash != image.hash_value:
                    msg = ("Image %(image_uuid)s checksum verification failed."
                           " Glance calculated checksum is %(hash_algo)s:"
                           "%(hash_value)s. Checksum in VNFD is "
                           "%(image_hash_algo)s:%(image_hash_value)s.")
                    raise Exception(msg % {"image_uuid": image_uuid,
                        "hash_algo": image.hash_algo,
                        "hash_value": image.hash_value,
                        "image_hash_algo": vnf_software_image.algorithm,
                        "image_hash_value": vnf_software_image.hash})

                LOG.debug('Image status: %(image_uuid)s %(status)s',
                          {'image_uuid': image_uuid, 'status': status})
                return True
            time.sleep(self.IMAGE_RETRY_WAIT)
            LOG.debug('Image %(image_uuid)s status: %(status)s',
                      {"image_uuid": image_uuid, "status": status})

            if retries == 0 and image.status != expected_status:
                error_reason = ("Image {image_uuid} could not get active "
                                "within {wait} seconds").format(
                    wait=(self.IMAGE_RETRIES *
                          self.IMAGE_RETRY_WAIT),
                    image_uuid=image_uuid)
                raise exception_class(reason=error_reason)

    @log.log
    def delete_vnf_instance_resource(self, context, vnf_instance,
            vim_connection_info, vnf_resource):
        LOG.info("Deleting resource '%(name)s' of type ' %(type)s' for vnf "
                 "%(id)s", {"type": vnf_resource.resource_type,
                 "name": vnf_resource.resource_name,
                 "id": vnf_instance.id})
        glance_client = gc.GlanceClient(vim_connection_info)
        try:
            glance_client.delete(vnf_resource.resource_identifier)
            LOG.info("Deleted resource '%(name)s' of type ' %(type)s' for vnf "
                 "%(id)s", {"type": vnf_resource.resource_type,
                 "name": vnf_resource.resource_name,
                 "id": vnf_instance.id})
        except Exception:
            LOG.info("Failed to delete resource '%(name)s' of type"
                    " %(type)s' for vnf %(id)s",
                    {"type": vnf_resource.resource_type,
                     "name": vnf_resource.resource_name,
                     "id": vnf_instance.id})

    def instantiate_vnf(self, context, vnf_instance, vnfd_dict,
                        vim_connection_info, instantiate_vnf_req,
                        grant_response,
                        base_hot_dict=None, vnf_package_path=None):
        access_info = vim_connection_info.access_info
        region_name = access_info.get('region')
        placement_attr = vnfd_dict.get('placement_attr', {})
        placement_attr.update({'region_name': region_name})
        vnfd_dict['placement_attr'] = placement_attr

        instance_id = self.create(None, context, vnfd_dict,
            access_info, base_hot_dict, vnf_package_path,
            inst_req_info=instantiate_vnf_req,
            grant_info=grant_response)
        vnfd_dict['instance_id'] = instance_id
        return instance_id

    @log.log
    def post_vnf_instantiation(self, context, vnf_instance,
            vim_connection_info):
        inst_vnf_info = vnf_instance.instantiated_vnf_info
        access_info = vim_connection_info.access_info

        heatclient = hc.HeatClient(access_info,
            region_name=access_info.get('region'))
        stack_resources = self._get_stack_resources(
            inst_vnf_info.instance_id, heatclient)

        self._update_vnfc_resources(vnf_instance, stack_resources)

    def _update_resource_handle(self, vnf_instance, resource_handle,
                                stack_resources, resource_name):
        if not stack_resources:
            LOG.warning("Failed to set resource handle for resource "
                    "%(resource)s for vnf %(id)s", {"resource": resource_name,
                        "id": vnf_instance.id})
            return

        resource_data = stack_resources.pop(resource_name, None)
        if not resource_data:
            LOG.warning("Failed to set resource handle for resource "
                        "%(resource)s for vnf %(id)s",
                        {"resource": resource_name, "id": vnf_instance.id})
            return

        resource_handle.resource_id = resource_data.get(
            'physical_resource_id')
        resource_handle.vim_level_resource_type = resource_data.get(
            'resource_type')

    def _update_vnfc_resource_info(self, vnf_instance, vnfc_res_info,
            stack_resources, update_network_resource=True):
        inst_vnf_info = vnf_instance.instantiated_vnf_info

        def _pop_stack_resources(resource_name):
            for stack_id, resources in stack_resources.items():
                if resource_name in resources.keys():
                    return stack_id, resources
            return None, {}

        def _populate_virtual_link_resource_info(vnf_virtual_link_desc_id,
                                                 pop_resources):
            vnf_virtual_link_resource_info = \
                inst_vnf_info.vnf_virtual_link_resource_info
            for vnf_vl_resource_info in vnf_virtual_link_resource_info:
                if (vnf_vl_resource_info.vnf_virtual_link_desc_id !=
                        vnf_virtual_link_desc_id):
                    continue

                vl_resource_data = pop_resources.pop(
                    vnf_virtual_link_desc_id, None)
                if not vl_resource_data:
                    _, resources = _pop_stack_resources(
                        vnf_virtual_link_desc_id)
                    if not resources:
                        # NOTE(tpatil): network_resource is already set
                        # from the instantiatevnfrequest during instantiation.
                        continue
                    vl_resource_data = resources.get(
                        vnf_virtual_link_desc_id)

                resource_handle = vnf_vl_resource_info.network_resource
                resource_handle.resource_id = \
                    vl_resource_data.get('physical_resource_id')
                resource_handle.vim_level_resource_type = \
                    vl_resource_data.get('resource_type')

        def _populate_virtual_link_port(vnfc_cp_info, pop_resources):
            vnf_virtual_link_resource_info = \
                inst_vnf_info.vnf_virtual_link_resource_info
            for vnf_vl_resource_info in vnf_virtual_link_resource_info:
                vl_link_port_found = False
                for vl_link_port in vnf_vl_resource_info.vnf_link_ports:
                    if vl_link_port.cp_instance_id == vnfc_cp_info.id:
                        vl_link_port_found = True
                        self._update_resource_handle(vnf_instance,
                                vl_link_port.resource_handle, pop_resources,
                                vnfc_cp_info.cpd_id)

                if vl_link_port_found:
                    yield vnf_vl_resource_info.vnf_virtual_link_desc_id

        def _populate_virtual_storage(vnfc_resource_info, pop_resources):
            virtual_storage_resource_info = inst_vnf_info. \
                virtual_storage_resource_info
            for storage_id in vnfc_resource_info.storage_resource_ids:
                for vir_storage_res_info in virtual_storage_resource_info:
                    if vir_storage_res_info.id == storage_id:
                        self._update_resource_handle(vnf_instance,
                                vir_storage_res_info.storage_resource,
                                pop_resources,
                                vir_storage_res_info.virtual_storage_desc_id)
                        break

        stack_id, pop_resources = _pop_stack_resources(
            vnfc_res_info.vdu_id)

        self._update_resource_handle(vnf_instance,
                vnfc_res_info.compute_resource, pop_resources,
                vnfc_res_info.vdu_id)

        vnfc_res_info.metadata.update({"stack_id": stack_id})
        _populate_virtual_storage(vnfc_res_info, pop_resources)

        # Find out associated VLs, and CP used by vdu_id
        virtual_links = set()
        for vnfc_cp_info in vnfc_res_info.vnfc_cp_info:
            for vl_desc_id in _populate_virtual_link_port(vnfc_cp_info,
                    pop_resources):
                virtual_links.add(vl_desc_id)

        if update_network_resource:
            for vl_desc_id in virtual_links:
                _populate_virtual_link_resource_info(vl_desc_id,
                                                     pop_resources)

    def _update_ext_managed_virtual_link_ports(self, inst_vnf_info,
            ext_managed_vl_info):
        vnf_virtual_link_resource_info = \
            inst_vnf_info.vnf_virtual_link_resource_info

        def _update_link_port(vl_port):
            for ext_vl_port in ext_managed_vl_info.vnf_link_ports:
                if vl_port.id == ext_vl_port.id:
                    # Update the resource_id
                    ext_vl_port.resource_handle.resource_id =\
                        vl_port.resource_handle.resource_id
                    ext_vl_port.resource_handle.vim_level_resource_type =\
                        vl_port.resource_handle.vim_level_resource_type
                    break

        for vnf_vl_resource_info in vnf_virtual_link_resource_info:
            if (vnf_vl_resource_info.vnf_virtual_link_desc_id !=
                    ext_managed_vl_info.vnf_virtual_link_desc_id):
                continue

            for vl_port in vnf_vl_resource_info.vnf_link_ports:
                _update_link_port(vl_port)

    def _update_vnfc_resources(self, vnf_instance, stack_resources):
        inst_vnf_info = vnf_instance.instantiated_vnf_info
        for vnfc_res_info in inst_vnf_info.vnfc_resource_info:
            self._update_vnfc_resource_info(vnf_instance, vnfc_res_info,
                    stack_resources)

        # update vnf_link_ports of ext_managed_virtual_link_info using already
        # populated vnf_link_ports from vnf_virtual_link_resource_info.
        for ext_mng_vl_info in inst_vnf_info.ext_managed_virtual_link_info:
            self._update_ext_managed_virtual_link_ports(inst_vnf_info,
                ext_mng_vl_info)

    def _get_stack_resources(self, stack_id, heatclient):
        def _stack_ids(stack_id):
            filters = {
                "owner_id": stack_id,
                "show_nested": True
            }
            yield stack_id
            for stack in heatclient.stacks.list(**{"filters": filters}):
                if stack.parent and stack.parent == stack_id:
                    for x in _stack_ids(stack.id):
                        yield x

        resource_details = {}
        for id in _stack_ids(stack_id):
            resources = {}
            child_stack = False if id == stack_id else True
            for stack_resource in heatclient.resources.list(id):
                resource_data = {"resource_type":
                    stack_resource.resource_type,
                    "physical_resource_id":
                    stack_resource.physical_resource_id}
                resources[stack_resource.resource_name] = resource_data
            resource_details[id] = resources
            resource_details[id].update({'child_stack': child_stack})

        return resource_details

    def _get_vnfc_resources_from_heal_request(self, inst_vnf_info,
                                              heal_vnf_request):
        if not heal_vnf_request.vnfc_instance_id:
            # include all vnfc resources
            return [resource for resource in inst_vnf_info.vnfc_resource_info]

        vnfc_resources = []
        for vnfc_resource in inst_vnf_info.vnfc_resource_info:
            if vnfc_resource.id in heal_vnf_request.vnfc_instance_id:
                vnfc_resources.append(vnfc_resource)
        return vnfc_resources

    @log.log
    def heal_vnf(self, context, vnf_instance, vim_connection_info,
                 heal_vnf_request):
        access_info = vim_connection_info.access_info
        region_name = access_info.get('region')
        inst_vnf_info = vnf_instance.instantiated_vnf_info
        heatclient = hc.HeatClient(access_info, region_name=region_name)

        def _get_storage_resources(vnfc_resource):
            # Prepare list of storage resources to be marked unhealthy
            for storage_id in vnfc_resource.storage_resource_ids:
                for storage_res_info in inst_vnf_info. \
                        virtual_storage_resource_info:
                    if storage_res_info.id == storage_id:
                        yield storage_res_info.virtual_storage_desc_id, \
                            storage_res_info.storage_resource.resource_id

        def _get_vdu_resources(vnfc_resources):
            # Prepare list of vdu resources to be marked unhealthy
            vdu_resources = []
            for vnfc_resource in vnfc_resources:
                resource_details = {"resource_name": vnfc_resource.vdu_id,
                        "physical_resource_id":
                        vnfc_resource.compute_resource.resource_id}
                vdu_resources.append(resource_details)

                # Get storage resources
                for resource_name, resource_id in \
                        _get_storage_resources(vnfc_resource):
                    resource_details = {"resource_name": resource_name,
                        "physical_resource_id": resource_id}
                    vdu_resources.append(resource_details)

            return vdu_resources

        def _prepare_stack_resources_for_updation(vdu_resources,
                stack_resources):
            for resource in vdu_resources:
                for stack_uuid, resources in stack_resources.items():
                    res_details = resources.get(resource['resource_name'])
                    if (res_details and res_details['physical_resource_id'] ==
                            resource['physical_resource_id']):
                        yield stack_uuid, resource['resource_name']

        def _resource_mark_unhealthy():
            vnfc_resources = self._get_vnfc_resources_from_heal_request(
                inst_vnf_info, heal_vnf_request)

            vdu_resources = _get_vdu_resources(vnfc_resources)
            stack_resources = self._get_stack_resources(
                inst_vnf_info.instance_id, heatclient)

            cause = heal_vnf_request.cause or "Healing"
            for stack_uuid, resource_name in \
                    _prepare_stack_resources_for_updation(
                        vdu_resources, stack_resources):
                try:
                    LOG.info("Marking resource %(resource)s as unhealthy for "
                             "stack %(stack)s for vnf instance %(id)s",
                             {"resource": resource_name,
                              "stack": stack_uuid,
                              "id": vnf_instance.id})

                    heatclient.resource_mark_unhealthy(
                        stack_id=stack_uuid,
                        resource_name=resource_name, mark_unhealthy=True,
                        resource_status_reason=cause)
                except Exception as exp:
                    msg = ("Failed to mark stack '%(stack_id)s' resource as "
                           "unhealthy for resource '%(resource)s', "
                           "Error: %(error)s")
                    raise exceptions.VnfHealFailed(id=vnf_instance.id,
                        error=msg % {"stack_id": inst_vnf_info.instance_id,
                                     "resource": resource_name,
                                     "error": str(exp)})

        def _get_stack_status():
            stack_statuses = ["CREATE_COMPLETE", "UPDATE_COMPLETE"]
            stack = heatclient.get(inst_vnf_info.instance_id)
            if stack.stack_status not in stack_statuses:
                error = ("Healing of vnf instance %(id)s is possible only "
                         "when stack %(stack_id)s status is %(statuses)s, "
                         "current stack status is %(status)s")
                raise exceptions.VnfHealFailed(id=vnf_instance.id,
                    error=error % {"id": vnf_instance.id,
                    "stack_id": inst_vnf_info.instance_id,
                    "statuses": ",".join(stack_statuses),
                    "status": stack.stack_status})

        _get_stack_status()
        _resource_mark_unhealthy()

        LOG.info("Updating stack %(stack)s for vnf instance %(id)s",
                {"stack": inst_vnf_info.instance_id, "id": vnf_instance.id})

        heatclient.update(stack_id=inst_vnf_info.instance_id, existing=True)

    @log.log
    def heal_vnf_wait(self, context, vnf_instance, vim_connection_info):
        """Check vnf is healed successfully"""

        access_info = vim_connection_info.access_info
        region_name = access_info.get('region')
        inst_vnf_info = vnf_instance.instantiated_vnf_info
        stack = self._wait_until_stack_ready(inst_vnf_info.instance_id,
            access_info, infra_cnst.STACK_UPDATE_IN_PROGRESS,
            infra_cnst.STACK_UPDATE_COMPLETE, vnfm.VNFHealWaitFailed,
            region_name=region_name)
        return stack

    def post_heal_vnf(self, context, vnf_instance, vim_connection_info,
                      heal_vnf_request):
        """Update resource_id for each vnfc resources

        :param context: A RequestContext
        :param vnf_instance: tacker.objects.VnfInstance to be healed
        :vim_info: Credentials to initialize Vim connection
        :heal_vnf_request: tacker.objects.HealVnfRequest object containing
                           parameters passed in the heal request
        """
        access_info = vim_connection_info.access_info
        region_name = access_info.get('region')

        heatclient = hc.HeatClient(access_info, region_name)
        inst_vnf_info = vnf_instance.instantiated_vnf_info
        stack_resources = self._get_stack_resources(inst_vnf_info.instance_id,
                heatclient)

        vnfc_resources = self._get_vnfc_resources_from_heal_request(
            inst_vnf_info, heal_vnf_request)
        for vnfc_res_info in vnfc_resources:
            stack_id = vnfc_res_info.metadata.get("stack_id")
            resources = stack_resources.get(stack_id)
            if not resources:
                # NOTE(tpatil): This could happen when heat child stacks
                # and the stack_id stored in metadata of vnfc_res_info are
                # not in sync. There is no point in syncing inconsistent
                # resources information so exit with an error,
                error = "Failed to find stack_id %s" % stack_id
                raise exceptions.VnfHealFailed(id=vnf_instance.id,
                                               error=error)

            self._update_vnfc_resource_info(vnf_instance, vnfc_res_info,
                    {stack_id: resources}, update_network_resource=False)
