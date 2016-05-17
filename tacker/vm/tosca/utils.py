# Copyright 2016 - Nokia
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
import re
import sys
import yaml

from tacker.common import log
from tacker.common import utils
from tacker.extensions import vnfm
from tacker.openstack.common import log as logging

from toscaparser.properties import Property
from toscaparser.utils import yamlparser


FAILURE = 'tosca.policies.tacker.Failure'
LOG = logging.getLogger(__name__)
MONITORING = 'tosca.policies.tacker.Monitoring'
PLACEMENT = 'tosca.policies.tacker.Placement'
TACKERCP = 'tosca.nodes.nfv.CP.Tacker'
TACKERVDU = 'tosca.nodes.nfv.VDU.Tacker'
TOSCA_BINDS_TO = 'tosca.relationships.network.BindsTo'
VDU = 'tosca.nodes.nfv.VDU'
IMAGE = 'tosca.artifacts.Deployment.Image.VM'
OS_RESOURCES = {
    'flavor': 'get_flavor_dict',
    'image': 'get_image_dict'
}

FLAVOR_PROPS = {
    "num_cpus": ("vcpus", 1, None),
    "disk_size": ("disk", 1, "GB"),
    "mem_size": ("ram", 512, "MB")
}

CPU_PROP_MAP = (('hw:cpu_policy', 'cpu_affinity'),
                ('hw:cpu_threads_policy', 'thread_allocation'),
                ('hw:cpu_sockets', 'socket_count'),
                ('hw:cpu_threads', 'thread_count'),
                ('hw:cpu_cores', 'core_count'))

CPU_PROP_KEY_SET = {'cpu_affinity', 'thread_allocation', 'socket_count',
                    'thread_count', 'core_count'}

FLAVOR_EXTRA_SPECS_LIST = ('cpu_allocation',
                           'mem_page_size',
                           'numa_node_count',
                           'numa_nodes')

delpropmap = {TACKERVDU: ('mgmt_driver', 'config', 'service_type',
                          'placement_policy', 'monitoring_policy',
                          'failure_policy'),
              TACKERCP: ('management',)}

convert_prop = {TACKERCP: {'anti_spoofing_protection':
                           'port_security_enabled'}}

deletenodes = (MONITORING, FAILURE, PLACEMENT)

HEAT_RESOURCE_MAP = {
    "flavor": "OS::Nova::Flavor",
    "image": "OS::Glance::Image"
}


@log.log
def updateimports(template):
    path = os.path.dirname(os.path.abspath(__file__)) + '/lib/'
    defsfile = path + 'tacker_defs.yaml'

    if 'imports' in template:
        template['imports'].append(defsfile)
    else:
        template['imports'] = [defsfile]

    if 'nfv' in template['tosca_definitions_version']:
        nfvfile = path + 'tacker_nfv_defs.yaml'

        template['imports'].append(nfvfile)

    LOG.debug(_("%s") % path)


@log.log
def get_vdu_monitoring(template):
    monitoring_dict = {'vdus': {}}
    for nt in template.nodetemplates:
        if nt.type_definition.is_derived_from(TACKERVDU):
            mon_policy = nt.get_property_value('monitoring_policy') or 'noop'
            # mon_data = {mon_policy['name']: {'actions': {'failure':
            #                                              'respawn'}}}
            if mon_policy != 'noop':
                if 'parameters' in mon_policy:
                    mon_policy['monitoring_params'] = mon_policy['parameters']
                monitoring_dict['vdus'][nt.name] = {}
                monitoring_dict['vdus'][nt.name][mon_policy['name']] = \
                    mon_policy
    return monitoring_dict


@log.log
def get_mgmt_ports(tosca):
    mgmt_ports = {}
    for nt in tosca.nodetemplates:
        if nt.type_definition.is_derived_from(TACKERCP):
            mgmt = nt.get_property_value('management') or None
            if mgmt:
                vdu = None
                for rel, node in nt.relationships.items():
                    if rel.is_derived_from(TOSCA_BINDS_TO):
                        vdu = node.name
                        break

                if vdu is not None:
                    name = 'mgmt_ip-%s' % vdu
                    mgmt_ports[name] = nt.name
    LOG.debug('mgmt_ports: %s' % mgmt_ports)
    return mgmt_ports


@log.log
def add_resources_tpl(heat_dict, hot_res_tpl):
    for res, res_dict in hot_res_tpl.iteritems():
        for vdu, vdu_dict in res_dict.iteritems():
            res_name = vdu + "_" + res
            heat_dict["resources"][res_name] = {
                "type": HEAT_RESOURCE_MAP[res],
                "properties": {}
            }

            for prop, val in vdu_dict.iteritems():
                heat_dict["resources"][res_name]["properties"][prop] = val
            heat_dict["resources"][vdu]["properties"][res] = {
                "get_resource": res_name
            }


@log.log
def convert_unsupported_res_prop(heat_dict, unsupported_res_prop):
    res_dict = heat_dict['resources']

    for res, attr in res_dict.iteritems():
        res_type = attr['type']
        if res_type in unsupported_res_prop:
            prop_dict = attr['properties']
            unsupported_prop_dict = unsupported_res_prop[res_type]
            unsupported_prop = set(prop_dict.keys()) & set(
                unsupported_prop_dict.keys())
            for prop in unsupported_prop:
                    # some properties are just punted to 'value_specs'
                    # property if they are incompatible
                    new_prop = unsupported_prop_dict[prop]
                    if new_prop == 'value_specs':
                        prop_dict.setdefault(new_prop, {})[
                            prop] = prop_dict.pop(prop)
                    else:
                        prop_dict[new_prop] = prop_dict.pop(prop)


@log.log
def post_process_heat_template(heat_tpl, mgmt_ports, res_tpl,
                               unsupported_res_prop=None):
    #
    # TODO(bobh) - remove when heat-translator can support literal strings.
    #
    def fix_user_data(user_data_string):
        user_data_string = re.sub('user_data: #', 'user_data: |\n        #',
                                 user_data_string, re.MULTILINE)
        return re.sub('\n\n', '\n', user_data_string, re.MULTILINE)

    heat_tpl = fix_user_data(heat_tpl)
    #
    # End temporary workaround for heat-translator
    #
    heat_dict = yamlparser.simple_ordered_parse(heat_tpl)
    for outputname, portname in mgmt_ports.items():
        ipval = {'get_attr': [portname, 'fixed_ips', 0, 'ip_address']}
        output = {outputname: {'value': ipval}}
        if 'outputs' in heat_dict:
            heat_dict['outputs'].update(output)
        else:
            heat_dict['outputs'] = output
        LOG.debug(_('Added output for %s') % outputname)
    add_resources_tpl(heat_dict, res_tpl)
    if unsupported_res_prop:
        convert_unsupported_res_prop(heat_dict, unsupported_res_prop)
    return yaml.dump(heat_dict)


@log.log
def post_process_template(template):
    for nt in template.nodetemplates:
        if (nt.type_definition.is_derived_from(MONITORING) or
            nt.type_definition.is_derived_from(FAILURE) or
                nt.type_definition.is_derived_from(PLACEMENT)):
            template.nodetemplates.remove(nt)
            continue

        if nt.type in delpropmap.keys():
            for prop in delpropmap[nt.type]:
                for p in nt.get_properties_objects():
                    if prop == p.name:
                        nt.get_properties_objects().remove(p)

        if nt.type in convert_prop:
            for prop in convert_prop[nt.type].keys():
                for p in nt.get_properties_objects():
                    if prop == p.name:
                        schema_dict = {'type': p.type}
                        v = nt.get_property_value(p.name)
                        newprop = Property(convert_prop[nt.type][prop], v,
                                           schema_dict)
                        nt.get_properties_objects().append(newprop)
                        nt.get_properties_objects().remove(p)


@log.log
def get_mgmt_driver(template):
    mgmt_driver = None
    for nt in template.nodetemplates:
        if nt.type_definition.is_derived_from(TACKERVDU):
            if (mgmt_driver and nt.get_property_value('mgmt_driver') !=
                    mgmt_driver):
                raise vnfm.MultipleMGMTDriversSpecified()
            else:
                mgmt_driver = nt.get_property_value('mgmt_driver')

    return mgmt_driver


def findvdus(template):
    vdus = []
    for nt in template.nodetemplates:
        if nt.type_definition.is_derived_from(TACKERVDU):
            vdus.append(nt)
    return vdus


def get_flavor_dict(template, flavor_extra_input=None):
    flavor_dict = {}
    vdus = findvdus(template)
    for nt in vdus:
        flavor_tmp = nt.get_properties().get('flavor', None)
        if flavor_tmp:
            continue
        if nt.get_capabilities().get("nfv_compute", None):
            flavor_dict[nt.name] = {}
            properties = nt.get_capabilities()["nfv_compute"].get_properties()
            for prop, (hot_prop, default, unit) in \
                    FLAVOR_PROPS.iteritems():
                hot_prop_val = (properties[prop].value
                    if properties.get(prop, None) else None)
                if unit and hot_prop_val:
                    hot_prop_val = \
                        utils.change_memory_unit(hot_prop_val, unit)
                flavor_dict[nt.name][hot_prop] = \
                    hot_prop_val if hot_prop_val else default
            if any(p in properties for p in FLAVOR_EXTRA_SPECS_LIST):
                flavor_dict[nt.name]['extra_specs'] = {}
                es_dict = flavor_dict[nt.name]['extra_specs']
                populate_flavor_extra_specs(es_dict, properties,
                                            flavor_extra_input)
    return flavor_dict


def populate_flavor_extra_specs(es_dict, properties, flavor_extra_input):
    if 'mem_page_size' in properties:
        mval = properties['mem_page_size'].value
        if str(mval).isdigit():
            mval = mval * 1024
        elif mval not in ('small', 'large', 'any'):
            raise vnfm.HugePageSizeInvalidInput(
                error_msg_details=(mval + ":Invalid Input"))
        es_dict['hw:mem_page_size'] = mval
    if 'numa_node_count' in properties:
        es_dict['hw:numa_nodes'] = \
            properties['numa_node_count'].value
    if 'numa_nodes' in properties and 'numa_node_count' not in properties:
        nodes_dict = dict(properties['numa_nodes'].value)
        dval = list(nodes_dict.values())
        for ndict in dval:
            invalid_input = set(ndict.keys()) - {'id', 'vcpus', 'memory'}
            if invalid_input:
                raise vnfm.NumaNodesInvalidKeys(
                    error_msg_details=(', '.join(invalid_input)),
                    valid_keys="id, vcpus and memory")
            if 'id' in ndict and 'vcpus' in ndict:
                vk = "hw:numa_cpus." + str(ndict['id'])
                vval = ",".join([str(x) for x in ndict['vcpus']])
                es_dict[vk] = vval
            if 'id' in ndict and 'memory' in ndict:
                mk = "hw:numa_mem." + str(ndict['id'])
                es_dict[mk] = ndict['memory']
    if 'cpu_allocation' in properties:
        cpu_dict = dict(properties['cpu_allocation'].value)
        invalid_input = set(cpu_dict.keys()) - CPU_PROP_KEY_SET
        if invalid_input:
            raise vnfm.CpuAllocationInvalidKeys(
                error_msg_details=(', '.join(invalid_input)),
                valid_keys=(', '.join(CPU_PROP_KEY_SET)))
        for(k, v) in CPU_PROP_MAP:
            if v in cpu_dict:
                es_dict[k] = cpu_dict[v]
    if flavor_extra_input:
        es_dict.update(flavor_extra_input)


def get_image_dict(template):
    image_dict = {}
    vdus = findvdus(template)
    for vdu in vdus:
        if not vdu.entity_tpl.get("artifacts", None):
            continue
        artifacts = vdu.entity_tpl["artifacts"]
        for name, artifact in artifacts.iteritems():
            if ('type' in artifact.keys() and
              artifact["type"] == IMAGE):
                if 'file' not in artifact.keys():
                    raise vnfm.FilePathMissing()
                image_dict[vdu.name] = {
                    "location": artifact["file"],
                    "container_format": "bare",
                    "disk_format": "raw",
                    "name": name
                }
    return image_dict


def get_resources_dict(template, flavor_extra_input=None):
    res_dict = dict()
    for res, method in OS_RESOURCES.iteritems():
        res_method = getattr(sys.modules[__name__], method)
        if res is 'flavor':
            res_dict[res] = res_method(template, flavor_extra_input)
        else:
            res_dict[res] = res_method(template)
    return res_dict
