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
import yaml

from tacker.common import log
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


delpropmap = {TACKERVDU: ('mgmt_driver', 'config', 'service_type',
                          'placement_policy', 'monitoring_policy',
                          'failure_policy'),
              TACKERCP: ('management',)}

convert_prop = {TACKERCP: {'anti_spoofing_protection':
                           'port_security_enabled'}}

deletenodes = (MONITORING, FAILURE, PLACEMENT)


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
                monitoring_dict['vdus'][nt.name] = mon_policy
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
def post_process_heat_template(heat_tpl, mgmt_ports):
    heat_dict = yamlparser.simple_ordered_parse(heat_tpl)
    for outputname, portname in mgmt_ports.items():
        ipval = {'get_attr': [portname, 'fixed_ips', 0, 'ip_address']}
        output = {outputname: {'value': ipval}}
        if 'outputs' in heat_dict:
            heat_dict['outputs'].update(output)
        else:
            heat_dict['outputs'] = output
        LOG.debug(_('Added output for %s') % outputname)

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
