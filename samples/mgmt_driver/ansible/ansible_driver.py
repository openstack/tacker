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

import os
import yaml

from oslo_log import log as logging
from oslo_serialization import jsonutils

from tacker.vnfm.mgmt_drivers.ansible import ansible_config_parser
from tacker.vnfm.mgmt_drivers.ansible import config_validator
from tacker.vnfm.mgmt_drivers.ansible import event_handler
from tacker.vnfm.mgmt_drivers.ansible import exceptions
from tacker.vnfm.mgmt_drivers.ansible import heat_client
from tacker.vnfm.mgmt_drivers.ansible import utils

from tacker.vnfm.mgmt_drivers.ansible.config_actions.\
    vm_app_config import vm_app_config

from tacker.vnflcm import utils as vnflcm_utils
from tacker.vnfm.mgmt_drivers import constants as mgmt_constants
from tacker.vnfm import plugin

LOG = logging.getLogger(__name__)
EVENT_HANDLER = event_handler.AnsibleEventHandler()
SUPPORTED_ACTIONS = [
    mgmt_constants.ACTION_INSTANTIATE_VNF,
    mgmt_constants.ACTION_TERMINATE_VNF,
    mgmt_constants.ACTION_HEAL_VNF,
    mgmt_constants.ACTION_UPDATE_VNF,
    mgmt_constants.ACTION_SCALE_IN_VNF,
    mgmt_constants.ACTION_SCALE_OUT_VNF,
]


class AnsibleDriver(object):

    def __init__(self):
        self._config_queue = {}
        self._has_error = False
        self._cfg_parser = ansible_config_parser.ConfigParser()
        self._cfg_validator = config_validator.AnsibleConfigValidator()

        self._config_actions = {}
        self._config_actions["vm_app_config"] = \
            vm_app_config.VmAppConfigAction()

        self._vnf = None
        self._plugin = plugin.VNFMPlugin()
        self._vnf_instance = None
        self._context = None

        LOG.debug("Ansible Driver initialized successfully!")

    def get_type(self):
        """Mgmt driver for ansible"""
        pass

    def get_name(self):
        """Ansible Mgmt Driver"""
        pass

    def get_description(self):
        pass

    def _driver_process_flow(self, context, vnf_instance, action,
            request_obj, **kwargs):
        # set global, prevent passing for every function call
        self._vnf = kwargs['vnf']
        self._vnf_instance = vnf_instance
        self._context = context

        start_msg = ("Ansible Management Driver invoked for configuration of"
                     "VNF: {}".format(self._vnf.get("name")))

        insta_info = self._vnf_instance.instantiated_vnf_info

        if action == mgmt_constants.ACTION_HEAL_VNF:
            for vnfc_info in insta_info.vnfc_resource_info:
                is_exist = [instance_id for instance_id in
                    request_obj.vnfc_instance_id
                    if instance_id == vnfc_info.id]

                if (not len(request_obj.vnfc_instance_id)
                        or len(is_exist)):
                    self._vnf['failed_vdu_name'] = vnfc_info.vdu_id
                    break

        EVENT_HANDLER.create_event(context, self._vnf,
            utils.get_event_by_action(action,
                self._vnf.get("failed_vdu_name", None)),
            start_msg)

        # get the mgmt_url
        vnf_mgmt_ip_address = self._vnf.get("mgmt_ip_address", None)
        if vnf_mgmt_ip_address is not None:
            mgmt_url = jsonutils.loads(vnf_mgmt_ip_address)
            LOG.debug("mgmt_url %s", mgmt_url)
        else:
            LOG.info("Unable to retrieve mgmt_ip_address of VNF")
            return

        # load the configuration file
        config_yaml = self._load_ansible_config(request_obj)
        if not config_yaml:
            return

        # validate config file
        self._cfg_validator.validate(config_yaml)

        # filter VDUs
        if (action != mgmt_constants.ACTION_SCALE_IN_VNF and
                action != mgmt_constants.ACTION_SCALE_OUT_VNF):
            config_yaml = self._cfg_validator.filter_vdus(context, self._vnf,
                utils.get_event_by_action(action,
                    self._vnf.get("failed_vdu_name", None)), mgmt_url,
                config_yaml)

        # load stack map
        stack_map = self._get_stack_map(action, **kwargs)

        # configure config parser for vnf parameter passing
        self._cfg_parser.configure(self._context, self._vnf, self._plugin,
            config_yaml, stack_map)

        self._sort_config(config_yaml)

        self._process_config(stack_map, config_yaml, mgmt_url, action)

    def _sort_config(self, config_yaml):
        self._config_queue = {}
        for vdu, vdu_dict in config_yaml.get("vdus", {}).items():
            self._add_to_config_queue(vdu, vdu_dict.get("config", {}))

    def _process_config(self, stack_map, config_yaml, mgmt_url, action):
        for vdu_order in sorted(self._config_queue):
            config_info_list = self._config_queue[vdu_order]
            for config_info in config_info_list:
                vdu = config_info["vdu"]
                config = config_info["config"]

                for key, conf_value in config.items():
                    if key not in self._config_actions:
                        continue

                    LOG.debug("Processing configuration: {}".format(key))
                    self._config_actions[key].execute(
                        vdu=vdu,
                        vnf=self._vnf,
                        context=self._context,
                        conf_value=conf_value,
                        mgmt_url=mgmt_url,
                        cfg_parser=self._cfg_parser,
                        stack_map=stack_map,
                        config_yaml=config_yaml,
                        action=action,
                    )

    def _add_to_config_queue(self, vdu, config):
        if "order" not in config:
            raise exceptions.MandatoryKeyNotDefinedError(vdu=vdu, key="order")

        try:
            order = int(config["order"])
        except ValueError:
            raise exceptions.InvalidValueError(vdu=vdu, key="order")

        config_info = {
            "vdu": vdu,
            "config": config
        }

        if order in self._config_queue:
            self._config_queue[order].append(config_info)
        else:
            entity_list = []
            entity_list.append(config_info)
            self._config_queue[order] = entity_list

    def _get_stack_map(self, action, **kwargs):
        stack_id_map = {}
        stack_id = None
        stack_id_list = None
        scaling_actions = [
            mgmt_constants.ACTION_SCALE_IN_VNF,
            mgmt_constants.ACTION_SCALE_OUT_VNF,
        ]

        if action in scaling_actions:
            stack_id = kwargs["scale_stack_id"]
        else:
            stack_id = self._vnf_instance.instantiated_vnf_info.instance_id

        LOG.debug("stack_id: {}".format(stack_id))
        if stack_id:
            if not isinstance(stack_id, list):
                stack_id_list = [stack_id]
            else:
                stack_id_list = stack_id

        hc = heat_client.AnsibleHeatClient(self._context, self._plugin,
            self._vnf)

        for stack_ids in stack_id_list:
            parent_stack_id = hc.get_parent_stack_id(stack_ids)
            for resource in hc.get_resource_list(parent_stack_id):
                if resource.physical_resource_id == stack_ids:
                    attr = hc.get_resource_attributes(
                        parent_stack_id, resource.resource_name)
                    stack_id_map = self._add_to_stack_map(stack_id_map, attr)

        LOG.debug("stack_id_map: {}".format(stack_id_map))
        return stack_id_map

    def _add_to_stack_map(self, map, attributes):
        for key, value in attributes.items():
            if "mgmt_ip-" in key:
                vdu_name = key.replace("mgmt_ip-", "")
                if vdu_name in map:
                    map[vdu_name].append(value)
                else:
                    map[vdu_name] = [value]
        return map

    def _get_config(self, config_data, config_params, vnf_package_path):
        configurable_properties = config_data.get('configurable_properties')

        # add vnf_package_path to vnf_configurable properties
        if not configurable_properties:
            configurable_properties = {
                '_VAR_vnf_package_path': vnf_package_path + '/'
            }
        else:
            configurable_properties.update(
                {'_VAR_vnf_package_path': vnf_package_path + '/'})

        for k, v in config_params.items():
            var_key = '_VAR_' + k
            configurable_properties.update({var_key: v})

        config_data.update(
            {'configurable_properties': configurable_properties})

        LOG.debug('Modified config {}'.format(config_data))

        return yaml.dump(config_data)

    def _load_ansible_config(self, request_obj):
        # load vnf package path
        vnf_package_path = vnflcm_utils._get_vnf_package_path(self._context,
            self._vnf_instance.vnfd_id)
        script_ansible_path = os.path.join(vnf_package_path,
            utils.CONFIG_FOLDER)

        script_ansible_config = None

        # load ScriptANSIBLE/config.yaml
        if os.path.exists(script_ansible_path):
            for file in os.listdir(script_ansible_path):
                if file.endswith('yaml') and file.startswith('config'):
                    with open(
                            os.path.join(
                                script_ansible_path, file)) as file_obj:
                        script_ansible_config = yaml.safe_load(file_obj)

        if script_ansible_config is None:
            LOG.error("not defined ansible script config")

        config_params = {}

        if hasattr(self._vnf_instance.instantiated_vnf_info,
                'additional_params'):
            config_params = self._vnf_instance.instantiated_vnf_info.\
                additional_params
        elif hasattr(request_obj, 'additional_params'):
            config_params = request_obj.additional_params

        self._vnf['attributes']['config'] = self._get_config(
            script_ansible_config, config_params, vnf_package_path)

        return script_ansible_config
