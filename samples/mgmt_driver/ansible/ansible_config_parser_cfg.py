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

CONFIG_PARSER_MAP = {
    'vnf': {
        # Data source -> vnf_dict
        # '*' Denotes optional parameters
        # 'Comment all entries to load everything from vnf_dict
        'mgmt_ip_address': 'mgmt_ip_address',
        '*failed_vdu_name': 'failed_vdu_name',
        '*failed_vdu_instance_ip': 'failed_vdu_instance_ip',
        '*vduname': 'vdu_name'
    },
    'vnf_resource': {
        # Data source -> yaml.safe_load(
        # vnf_dict['attributes']['heat_template'])
        'RESOURCE_LIST': 'key in resources',
        'VDUNAME_LIST': 'key in resources where type=OS::Nova::Server',
        'CPNAME_LIST': 'key in resources where type=OS::Neutron::Port',
        'ALARMNAME_LIST': 'key in resources where type=OS::Aodh::EventAlarm',
        'VBNAME_LIST': 'key in resources where type=OS::Cinder::Volume',
        'CBNAME_LIST': 'key in resources where '
        'type=OS::Cinder::VolumeAttachment',
    },
    'resource': {},
    # Data source ->  heat.resources.get(
    # target_stack.id,<RESOURCE NAME>).to_dict()
    # Loads all resources
    'default': {}
    # Default Data source -> config_yaml.get("configurable_properties", {})
}
