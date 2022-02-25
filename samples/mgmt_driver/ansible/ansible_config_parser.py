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

import ast
import datetime
import re
import six
import yaml

from heatclient import client as hclient
from keystoneauth1 import loading
from keystoneauth1 import session
from oslo_log import log as logging

from tacker.vnfm.mgmt_drivers.ansible import event_handler
from tacker.vnfm.mgmt_drivers.ansible import exceptions

from tacker.vnfm.mgmt_drivers.ansible.ansible_config_parser_cfg\
    import CONFIG_PARSER_MAP

LOG = logging.getLogger(__name__)
EVENT_HANDLER = event_handler.AnsibleEventHandler()

RE_PATTERN = r"(_VAR_[a-zA-Z_.0-9-<>]+)"
STND_MSG = "Ansible Config Parser: {}"


class ConfigParser():

    def __init__(self):
        self._vim_id = ""
        self._auth_url = ""
        self._username = ""
        self._password = ""
        self._project_name = ""
        self._project_domain_name = ""
        self._user_domain_name = ""
        self._sess = ""
        self._handle_map = {}
        self._vnf = {}
        self._config_yaml = {}
        self._current_target_ip = ""
        self._current_target_vdu = ""
        self._failed_vdu_name = ""
        self._context = {}

    def configure(self, context, vnf, plugin, config_yaml, stack_map):
        LOG.info(STND_MSG.format("Configuring parser"))
        try:
            # load context
            self._context = context

            # load configurable_properties
            self._config_yaml = config_yaml

            # get vim info
            access_info = plugin.get_vim(context, vnf)

            # get vim details
            vim_auth = access_info["vim_auth"]
            self._auth_url = vim_auth["auth_url"]
            self._username = vim_auth["username"]
            self._password = vim_auth["password"]
            self._project_name = vim_auth["project_name"]
            self._project_domain_name = vim_auth["project_domain_name"]
            self._user_domain_name = vim_auth["user_domain_name"]

            # changed password type bytes -> string
            if isinstance(self._password, bytes):
                self._password = self._password.decode('utf-8')

            # append failed_vdu_name,failed_vdu_instance_ip to vnf_dict
            failed_vdu_name = vnf.get('failed_vdu_name', "")

            # make sure vnf['mgmt_ip_address'] is of type string
            vnf_mgmt_ip_address = vnf['mgmt_ip_address']

            # make sure vnf['mgmt_ip_address'] is of type string
            if isinstance(vnf_mgmt_ip_address, bytes):
                vnf['mgmt_ip_address'] = vnf_mgmt_ip_address.decode('utf-8')

            # if vnf has scaling policy,
            # get failed vdu instance ip from heat stack_map
            # else the vnf has no scaling policy,
            # directly get mgmt_ip address from vnf_dict
            if stack_map:
                vnf['failed_vdu_instance_ip'] = stack_map.get(failed_vdu_name,
                    [""])[0] if failed_vdu_name else ""
            else:
                if vnf_mgmt_ip_address:
                    failed_vdu_mgmt_ip_list = ast.literal_eval(
                        vnf['mgmt_ip_address']).get(failed_vdu_name, "")
                    if isinstance(failed_vdu_mgmt_ip_list, list):
                        vnf['failed_vdu_instance_ip'] = \
                            (failed_vdu_mgmt_ip_list[0]
                            if failed_vdu_name else "")
                    else:
                        vnf['failed_vdu_instance_ip'] = \
                            (failed_vdu_mgmt_ip_list
                            if failed_vdu_name else "")

            # load vnf dict
            self._vnf = vnf

            LOG.debug("Auth: {} {} {} {} {} {}".format(
                self._auth_url, self._username, self._password,
                self._project_name, self._project_domain_name,
                self._user_domain_name))

            # validate config file
            config = CONFIG_PARSER_MAP
            if not config and not type(config):
                raise exceptions.InternalErrorException(
                    details="Configuration file is not valid.")

            for section, options in config.items():
                create_function = getattr(self, "_handle_{}".format(section))
                self._handle_map[section] = ConfigHandle(
                    value_map=options, create_function=create_function)
            LOG.info(STND_MSG.format("Parser configured"))

        except exceptions.AnsibleDriverException:
            raise
        except Exception as ex:
            raise exceptions.ConfigParserConfigurationError(
                ex_type=type(ex), details=ex)

    def substitute(self, command, **kwargs):
        try:
            int_flag = False
            list_flag = False
            dict_flag = False

            if isinstance(command, int):
                int_flag = True
            elif isinstance(command, list):
                list_flag = True
            elif isinstance(command, dict):
                dict_flag = True
            elif not isinstance(command, six.string_types):
                raise Exception(
                    "Value '{}' of type '{}' is not yet supported "
                    " for parameter substitution."
                    .format(command, type(command)))
            txt = str(command)
            target_dict = {}

            # check for variables fetched @ runtime
            self._current_target_ip = kwargs.get("mgmt_ip_address", "")
            self._current_target_vdu = kwargs.get("vdu", "")

            # get equivalent value for each _VAR_XXX
            res = re.findall(RE_PATTERN, txt)

            # remove duplicates and sorted the _VAR_XXX in
            # descending order based on the string length
            res = list(dict.fromkeys(res))
            res.sort(key=len, reverse=True)

            for key in res:
                target_dict[key] = self._get_value(key)

            # substitute text with fetch value
            for key, val in target_dict.items():
                txt = re.sub(key, val, txt)

            if int_flag:
                txt = int(txt)
            if list_flag or dict_flag:
                txt = eval(txt)
            return txt

        except Exception as ex:
            raise exceptions.ConfigParserParsingError(
                cmd=command, ex_type=type(ex), details=ex)

    def _get_value(self, key, **kwargs):
        val = ""

        # Get Resource Type, and varible name
        raw_var = key.rsplit("_VAR_", 1)
        if len(raw_var) != 2:
            raise Exception("{} is not valid".format(key))

        # handle key with no attributes, default handle to 'default'
        if raw_var[1].find(".") == -1:
            handle_name = 'default'
            var = raw_var[1]

            if var == 'VDU_INSTANCE_IP':
                return self._get_vdu_instance_ip()

            if var == 'VDU_INSTANCE_NAME':
                return self._get_vdu_instance_name()

        else:
            handle_name, var = raw_var[1].split(".", 1)

        # get Handle based on resource type, and get value based on parameter
        # Return Handle Execution Result
        try:
            val = self._handle_map[handle_name].get_value(var)
        except KeyError:
            LOG.error("Cannot get value for {}".format(var))
            raise

        return val

    def _get_vdu_instance_ip(self):
        if not self._current_target_ip:
            LOG.error("Cannot get value for {}".format('VDU_INSTANCE_IP'))
            raise KeyError('VDU_INSTANCE_IP')
        return self._current_target_ip

    def _get_vdu_instance_name(self):
        if not self._current_target_vdu:
            LOG.error("Cannot get value for {}".format('VDU_INSTANCE_NAME'))
            raise KeyError('VDU_INSTANCE_NAME')
        return self._current_target_vdu

    # The following defines handle create functions, parameter
    # -> value_map, return value_dict
    def _handle_vnf_resource(self, value_map=None):
        value_dict = {}
        source = yaml.safe_load(self._vnf['attributes']['heat_template'])

        if not source:
            raise ValueError("Data source is not valid!")
        for option, values in value_map.items():
            value_dict[option] = self._generate_data(source, values)

        return value_dict

    def _handle_vnf(self, value_map=None):
        source = self._vnf
        value_dict = {}

        if not source:
            raise ValueError("Data source is not valid!")
        # if no specific value map, load everything
        if not value_map:
            for option, values in source.items():
                value_dict[option] = self._generate_data(source, option)
            return value_dict

        for roption, values in value_map.items():
            # check if item is optional,'*'
            if len(roption.split('*', 1)) == 2:
                option = roption.split('*', 1)[1]
                required = False
            else:
                option = roption
                required = True

            value_dict[option] = self._generate_data(source, values, required)

        return value_dict

    def _handle_resource(self, value_map=None):
        # get necessary details to create resource tree
        value_dict = {}
        vnf_instance_id = self._vnf['instance_id']
        loader = loading.get_plugin_loader('password')
        auth = loader.load_from_options(
            auth_url=self._auth_url,
            username=self._username,
            password=self._password,
            project_name=self._project_name,
            user_domain_name=self._user_domain_name,
            project_domain_name=self._project_domain_name)
        sess = session.Session(auth=auth)
        heat = hclient.Client('1', session=sess)

        # if no scaling group defined
        if not self._vnf['attributes'].get('scaling_group_names'):
            # get stack id
            target_stack = next(
                heat.stacks.list(filters={'id': vnf_instance_id}))
            if not target_stack:
                raise ValueError("Internal Error: Target Stack not found!")
            # create resource tree from resource names
            resources = yaml.safe_load(
                self._vnf['attributes']['heat_template'])['resources']
            if not resources:
                raise ValueError("Internal Error: Resources not fetched!")
            for resource in resources.keys():
                resource_info = \
                    heat.resources.get(target_stack.id, resource).to_dict()
                value_dict[resource] = resource_info['attributes']

        return value_dict

    def _handle_default(self, value_map=None):
        value_dict = {}
        configurable_properties = \
            self._config_yaml.get("configurable_properties", {})

        if not configurable_properties:
            return value_dict

        for option_raw, value in configurable_properties.items():
            # len(re.findall(RE_PATTERN,option_raw)) > 0
            option = option_raw.rsplit("_VAR_", 1)
            if len(option) != 2:
                msg = \
                    "Config file validation error. {} is not valid "\
                    "configurable_properties key".format(option_raw)
                LOG.error(msg)
                raise ValueError(msg)

            value_dict[option[1]] = value

        return value_dict

    def _generate_data(self, source, value, required=True):
        # get filters, "... where key=value"
        if len(value.rsplit(" where ", 1)) == 2:
            raw_attributes, raw_filter = value.rsplit(" where ", 1)
        else:
            raw_filter = ""
            raw_attributes = value.strip()

        # get qualifiers, "(key/val) in ..."
        if len(raw_attributes.split(" in ", 1)) == 2:
            attribute_option, attributes = raw_attributes.split(" in ", 1)
        else:
            # default None, return everything
            attribute_option = ""
            attributes = raw_attributes.strip()

        builder = "{}".format('source')

        for attribute in attributes.strip().split('.'):
            builder = builder + "['{}']".format(attribute)

        # evalute string as python expression
        try:
            items = eval(builder)
        except KeyError:
            if required:
                raise KeyError("{} not found".format(builder))
            else:
                return ""

        # create filter funciton
        def filter_func(target_item):
            if raw_filter and len(raw_filter.strip().split('=')) == 2:
                filter_key, filter_val = raw_filter.strip().split('=')
                if target_item[1][filter_key] == filter_val:
                    return True
                else:
                    return False
            else:
                return True

        # apply filters
        if isinstance(items, dict):
            raw_result = dict(filter(filter_func, items.items()))
        elif isinstance(items, six.string_types):
            # check if instance is string dict, else return as string,
            # since item is a single value
            try:
                raw_result = dict(
                    filter(filter_func, ast.literal_eval(items).items()))
            except Exception as ex:
                LOG.warning(
                    'Defaulting item to \'{}\' since cannot be evaluated. "\
                    "Error: {}'.format(items, ex))
                return items
        elif isinstance(items, (datetime.datetime, type(None))):
            return items
        else:
            raise Exception(
                "Source items data struct of type {} is not supported."
                .format(type(items)))
        # apply qualifiers
        result = []

        # apply qualifier if present and return result as list
        for raw_res_key, raw_res_val in raw_result.items():
            if attribute_option.strip() == 'key':
                result.append(raw_res_key)
            elif attribute_option.strip() == 'val':
                result.append(raw_res_val)

        # else default, return all as dict
        if not attribute_option.strip():
            result = {}
            for raw_res_key, raw_res_val in raw_result.items():
                result[raw_res_key] = raw_res_val

        return result


class ConfigHandle():

    def __init__(self, value_map, create_function=None):
        """parameter

        value_map: contains hash map for finding value
        value_dict: contains the fetch value based on value_map
        create_function:
            ld the function to generate value_dict, parameter is value_map
        """

        self._value_map = value_map
        self._value_dict = {}
        self._create_function = create_function

        # Populate Value Dict
        if not create_function:
            raise ValueError("Config Handle: Create function is Null!")
        self._value_dict = self._create_function(self._value_map)

        LOG.debug("Value Dict: {}".format(self._value_dict))

    def get_value(self, key):
        # this function returns the string equivalent of the data requested

        # handle exec <custom_function>
        if key in self._value_dict.keys():
            if isinstance(self._value_dict[key], str) and\
                    self._value_dict[key].find(" exec ") != -1:
                custom_func = \
                    self._value_dict[key].rsplit(" exec ", 1)[1].strip()
                # execute custom function
                try:
                    res = getattr(self, "_custom_{}".format(custom_func))()
                except Exception as ex:
                    LOG.exception(ex)
                    raise Exception(
                        "Config Handle: error encountered on "
                        "executing custom function {}".format(custom_func))
                return res

        # for normal operation
        res = ""
        builder = "{}".format('self._value_dict')
        for attribute in key.strip().split('.'):
            builder = builder + "['{}']".format(attribute)

        items = eval(builder)

        # if item is a type of dict, tuple, or list, seriliaze values
        #     into space delimeted string
        # else if string, return as is
        if isinstance(items, (dict, list, tuple)):
            for item in items:
                if not res:
                    res = res + "{}".format(item)
                else:
                    res = res + ",{}".format(item)
        elif isinstance(items, six.string_types):
            res = items
        else:
            raise Exception(
                "Result items of type {} data struct is not supported."
                .format(type(items)))
        return res
