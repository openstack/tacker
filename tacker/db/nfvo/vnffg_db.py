# Copyright 2016 Red Hat Inc
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

from oslo_utils import uuidutils
import random
import sqlalchemy as sa

from oslo_log import log as logging
from six import iteritems
from sqlalchemy import orm
from sqlalchemy.orm import exc as orm_exc
from tacker.db import db_base
from tacker.db import model_base
from tacker.db import models_v1
from tacker.db import types
from tacker.extensions import nfvo
from tacker.extensions.nfvo_plugins import vnffg
from tacker import manager
from tacker.plugins.common import constants


LOG = logging.getLogger(__name__)
_ACTIVE_UPDATE = (constants.ACTIVE, constants.PENDING_UPDATE)
_ACTIVE_UPDATE_ERROR_DEAD = (
    constants.PENDING_CREATE, constants.ACTIVE, constants.PENDING_UPDATE,
    constants.ERROR, constants.DEAD)
_VALID_VNFFG_UPDATE_ATTRIBUTES = ('name', 'description', 'vnf_mapping')
_VALID_SFC_UPDATE_ATTRIBUTES = ('chain', 'symmetrical')
_VALID_FC_UPDATE_ATTRIBUTES = ()
MATCH_CRITERIA = (
    'eth_type', 'eth_src', 'eth_dst', 'vlan_id', 'vlan_pcp', 'mpls_label',
    'mpls_tc', 'ip_dscp', 'ip_ecn', 'ip_src_prefix', 'ip_dst_prefix',
    'ip_proto', 'destination_port_range', 'source_port_range',
    'network_src_port_id', 'network_dst_port_id', 'network_id', 'network_name',
    'tenant_id', 'icmpv4_type', 'icmpv4_code', 'arp_op', 'arp_spa',
    'arp_tpa', 'arp_sha', 'arp_tha', 'ipv6_src', 'ipv6_dst', 'ipv6_flabel',
    'icmpv6_type', 'icmpv6_code', 'ipv6_nd_target', 'ipv6_nd_sll',
    'ipv6_nd_tll')

MATCH_DB_KEY_LIST = (
    'eth_type', 'eth_src', 'eth_dst', 'vlan_id', 'vlan_pcp', 'mpls_label',
    'mpls_tc', 'ip_dscp', 'ip_ecn', 'ip_src_prefix', 'ip_dst_prefix',
    'ip_proto', 'destination_port_min', 'destination_port_max',
    'source_port_min', 'source_port_max', 'network_src_port_id',
    'network_dst_port_id', 'network_id', 'tenant_id', 'icmpv4_type',
    'icmpv4_code', 'arp_op', 'arp_spa', 'arp_tpa', 'arp_sha', 'arp_tha',
    'ipv6_src', 'ipv6_dst', 'ipv6_flabel', 'icmpv6_type', 'icmpv6_code',
    'ipv6_nd_target', 'ipv6_nd_sll', 'ipv6_nd_tll'
)

CP = 'connection_points'


class VnffgTemplate(model_base.BASE, models_v1.HasId, models_v1.HasTenant):
    """Represents template to create a VNF Forwarding Graph."""

    # Descriptive name
    name = sa.Column(sa.String(255), nullable=False)
    description = sa.Column(sa.Text)

    # Vnffg template
    template = sa.Column(types.Json)

    # Vnffgd template source - onboarded
    template_source = sa.Column(sa.String(255), server_default='onboarded')


class Vnffg(model_base.BASE, models_v1.HasTenant, models_v1.HasId):
    """VNF Forwarding Graph Data Model"""

    name = sa.Column(sa.String(255), nullable=False)
    description = sa.Column(sa.String(255), nullable=True)

    # List of associated NFPs
    forwarding_paths = orm.relationship("VnffgNfp", backref="vnffg")

    vnffgd_id = sa.Column(types.Uuid, sa.ForeignKey('vnffgtemplates.id'))
    vnffgd = orm.relationship('VnffgTemplate')

    status = sa.Column(sa.String(255), nullable=False)

    # Mapping of VNFD to VNF instance names
    vnf_mapping = sa.Column(types.Json)

    attributes = sa.Column(types.Json)


class VnffgNfp(model_base.BASE, models_v1.HasTenant, models_v1.HasId):
    """Network Forwarding Path Data Model"""

    name = sa.Column(sa.String(255), nullable=False)
    vnffg_id = sa.Column(types.Uuid, sa.ForeignKey('vnffgs.id'),
                         nullable=False)
    classifier = orm.relationship('VnffgClassifier', backref='nfp',
                                  uselist=False)
    chain = orm.relationship('VnffgChain', backref='nfp',
                             uselist=False)

    status = sa.Column(sa.String(255), nullable=False)
    path_id = sa.Column(sa.String(255), nullable=False)

    # symmetry of forwarding path
    symmetrical = sa.Column(sa.Boolean(), default=False)


class VnffgChain(model_base.BASE, models_v1.HasTenant, models_v1.HasId):
    """Service Function Chain Data Model"""

    status = sa.Column(sa.String(255), nullable=False)

    instance_id = sa.Column(sa.String(255), nullable=True)

    # symmetry of forwarding path
    symmetrical = sa.Column(sa.Boolean(), default=False)

    # chain
    chain = sa.Column(types.Json)

    path_id = sa.Column(sa.String(255), nullable=False)
    nfp_id = sa.Column(types.Uuid, sa.ForeignKey('vnffgnfps.id'))


class VnffgClassifier(model_base.BASE, models_v1.HasTenant, models_v1.HasId):
    """VNFFG NFP Classifier Data Model"""

    status = sa.Column(sa.String(255), nullable=False)

    instance_id = sa.Column(sa.String(255), nullable=True)

    chain_id = sa.Column(types.Uuid, sa.ForeignKey('vnffgchains.id'))
    chain = orm.relationship('VnffgChain', backref='classifier',
                             uselist=False, foreign_keys=[chain_id])
    nfp_id = sa.Column(types.Uuid, sa.ForeignKey('vnffgnfps.id'))
    # match criteria
    match = orm.relationship('ACLMatchCriteria')


class ACLMatchCriteria(model_base.BASE, models_v1.HasId):
    """Represents ACL match criteria of a classifier."""

    vnffgc_id = sa.Column(types.Uuid, sa.ForeignKey('vnffgclassifiers.id'))
    eth_src = sa.Column(sa.String(36), nullable=True)
    eth_dst = sa.Column(sa.String(36), nullable=True)
    eth_type = sa.Column(sa.String(36), nullable=True)
    vlan_id = sa.Column(sa.Integer, nullable=True)
    vlan_pcp = sa.Column(sa.Integer, nullable=True)
    mpls_label = sa.Column(sa.Integer, nullable=True)
    mpls_tc = sa.Column(sa.Integer, nullable=True)
    ip_dscp = sa.Column(sa.Integer, nullable=True)
    ip_ecn = sa.Column(sa.Integer, nullable=True)
    ip_src_prefix = sa.Column(sa.String(36), nullable=True)
    ip_dst_prefix = sa.Column(sa.String(36), nullable=True)
    source_port_min = sa.Column(sa.Integer, nullable=True)
    source_port_max = sa.Column(sa.Integer, nullable=True)
    destination_port_min = sa.Column(sa.Integer, nullable=True)
    destination_port_max = sa.Column(sa.Integer, nullable=True)
    ip_proto = sa.Column(sa.Integer, nullable=True)
    network_id = sa.Column(types.Uuid, nullable=True)
    network_src_port_id = sa.Column(types.Uuid, nullable=True)
    network_dst_port_id = sa.Column(types.Uuid, nullable=True)
    tenant_id = sa.Column(sa.String(64), nullable=True)
    icmpv4_type = sa.Column(sa.Integer, nullable=True)
    icmpv4_code = sa.Column(sa.Integer, nullable=True)
    arp_op = sa.Column(sa.Integer, nullable=True)
    arp_spa = sa.Column(sa.String(36), nullable=True)
    arp_tpa = sa.Column(sa.String(36), nullable=True)
    arp_sha = sa.Column(sa.String(36), nullable=True)
    arp_tha = sa.Column(sa.String(36), nullable=True)
    ipv6_src = sa.Column(sa.String(36), nullable=True)
    ipv6_dst = sa.Column(sa.String(36), nullable=True)
    ipv6_flabel = sa.Column(sa.Integer, nullable=True)
    icmpv6_type = sa.Column(sa.Integer, nullable=True)
    icmpv6_code = sa.Column(sa.Integer, nullable=True)
    ipv6_nd_target = sa.Column(sa.String(36), nullable=True)
    ipv6_nd_sll = sa.Column(sa.String(36), nullable=True)
    ipv6_nd_tll = sa.Column(sa.String(36), nullable=True)


class VnffgPluginDbMixin(vnffg.VNFFGPluginBase, db_base.CommonDbMixin):

    def __init__(self):
        super(VnffgPluginDbMixin, self).__init__()

    def create_vnffg(self, context, vnffg):
        vnffg_dict = self._create_vnffg_pre(context, vnffg)
        sfc_instance = uuidutils.generate_uuid()
        fc_instance = uuidutils.generate_uuid()
        self._create_vnffg_post(context, sfc_instance,
                                fc_instance, vnffg_dict)
        self._create_vnffg_status(context, vnffg_dict)
        return vnffg_dict

    def get_vnffg(self, context, vnffg_id, fields=None):
        vnffg_db = self._get_resource(context, Vnffg, vnffg_id)
        return self._make_vnffg_dict(vnffg_db, fields)

    def get_vnffgs(self, context, filters=None, fields=None):
        return self._get_collection(context, Vnffg, self._make_vnffg_dict,
                                    filters=filters, fields=fields)

    def update_vnffg(self, context, vnffg_id, vnffg):
        vnffg_dict = self._update_vnffg_pre(context, vnffg_id)
        self._update_vnffg_post(context, vnffg_id, constants.ACTIVE, vnffg)
        return vnffg_dict

    def delete_vnffg(self, context, vnffg_id):
        self._delete_vnffg_pre(context, vnffg_id)
        self._delete_vnffg_post(context, vnffg_id, False)

    def create_vnffgd(self, context, vnffgd):
        template = vnffgd['vnffgd']
        LOG.debug('template %s', template)
        tenant_id = self._get_tenant_id_for_create(context, template)
        template_source = template.get('template_source')

        with context.session.begin(subtransactions=True):
            template_id = uuidutils.generate_uuid()
            template_db = VnffgTemplate(
                id=template_id,
                tenant_id=tenant_id,
                name=template.get('name'),
                description=template.get('description'),
                template=template.get('template'),
                template_source=template_source)
            context.session.add(template_db)

        LOG.debug('template_db %(template_db)s',
                  {'template_db': template_db})
        return self._make_template_dict(template_db)

    def get_vnffgd(self, context, vnffgd_id, fields=None):
        template_db = self._get_resource(context, VnffgTemplate,
                                         vnffgd_id)
        return self._make_template_dict(template_db, fields)

    def get_vnffgds(self, context, filters=None, fields=None):
        if ('template_source' in filters) and \
                (filters['template_source'][0] == 'all'):
            filters.pop('template_source')
        return self._get_collection(context, VnffgTemplate,
                                    self._make_template_dict,
                                    filters=filters, fields=fields)

    def delete_vnffgd(self, context, vnffgd_id):
        with context.session.begin(subtransactions=True):
            vnffg_db = context.session.query(Vnffg).filter_by(
                vnffgd_id=vnffgd_id).first()
            if vnffg_db is not None:
                raise nfvo.VnffgdInUse(vnffgd_id=vnffgd_id)

            template_db = self._get_resource(context, VnffgTemplate,
                                             vnffgd_id)
            context.session.delete(template_db)

    def get_classifier(self, context, classifier_id, fields=None):
        classifier_db = self._get_resource(context, VnffgClassifier,
                                           classifier_id)
        return self._make_classifier_dict(classifier_db, fields)

    def get_classifiers(self, context, filters=None, fields=None):
        return self._get_collection(context, VnffgClassifier,
                                    self._make_classifier_dict,
                                    filters=filters, fields=fields)

    def get_nfp(self, context, nfp_id, fields=None):
        nfp_db = self._get_resource(context, VnffgNfp, nfp_id)
        return self._make_nfp_dict(nfp_db, fields)

    def get_nfps(self, context, filters=None, fields=None):
        return self._get_collection(context, VnffgNfp,
                                    self._make_nfp_dict,
                                    filters=filters, fields=fields)

    def get_sfc(self, context, sfc_id, fields=None):
        chain_db = self._get_resource(context, VnffgChain, sfc_id)
        return self._make_chain_dict(chain_db, fields)

    def get_sfcs(self, context, filters=None, fields=None):
        return self._get_collection(context, VnffgChain,
                                    self._make_chain_dict,
                                    filters=filters, fields=fields)

    def _update_template_params(self, original, paramvalues, param_matched):
        if 'get_input' not in str(original):
            return
        if isinstance(original, dict):
            for key_, value in iteritems(original):
                if isinstance(value, dict) and 'get_input' in value:
                    if value['get_input'] in paramvalues:
                        original[key_] = paramvalues[value['get_input']]
                        param_matched.setdefault(value['get_input'], 0)
                        param_matched[value['get_input']] += 1
                    else:
                        raise nfvo.VnffgTemplateParamParsingException(
                            get_input=value['get_input'])
                else:
                    self._update_template_params(value,
                                                 paramvalues, param_matched)
        elif isinstance(original, list):
            for element in original:
                self._update_template_params(element,
                                             paramvalues, param_matched)

    def _process_parameterized_template(self, dev_attrs, vnffgd_template):
        param_vattrs_dict = dev_attrs.pop('param_values', None)
        param_matched = {}
        if isinstance(param_vattrs_dict, dict):
            self._update_template_params(vnffgd_template,
                                param_vattrs_dict, param_matched)
        else:
            raise nfvo.VnffgParamValueFormatError(
                param_value=param_vattrs_dict)
        for param_key in param_vattrs_dict.keys():
            if param_matched.get(param_key) is None:
                raise nfvo.VnffgParamValueNotUsed(param_key=param_key)

    # called internally, not by REST API
    def _create_vnffg_pre(self, context, vnffg):
        vnffg = vnffg['vnffg']
        LOG.debug('vnffg %s', vnffg)
        tenant_id = self._get_tenant_id_for_create(context, vnffg)
        name = vnffg.get('name')
        vnffg_id = vnffg.get('id') or uuidutils.generate_uuid()
        template_id = vnffg['vnffgd_id']
        symmetrical = vnffg['symmetrical']

        with context.session.begin(subtransactions=True):
            template_db = self._get_resource(context, VnffgTemplate,
                                             template_id)
            LOG.debug('vnffg template %s', template_db)

            if vnffg.get('attributes') and \
                    vnffg['attributes'].get('param_values'):
                vnffg_param = vnffg['attributes']
                vnffgd_topology_template = \
                    template_db.template['vnffgd']['topology_template']
                self._process_parameterized_template(vnffg_param,
                                                     vnffgd_topology_template)
                template_db.template['vnffgd']['topology_template'] = \
                    vnffgd_topology_template

            vnf_members = self._get_vnffg_property(template_db.template,
                                                   'constituent_vnfs')
            LOG.debug('Constituent VNFs: %s', vnf_members)
            vnf_mapping = self._get_vnf_mapping(context, vnffg.get(
                                                'vnf_mapping'), vnf_members)
            LOG.debug('VNF Mapping: %s', vnf_mapping)
            # create NFP dict
            nfp_dict = self._create_nfp_pre(template_db)
            LOG.debug('NFP: %s', nfp_dict)
            vnffg_db = Vnffg(id=vnffg_id,
                             tenant_id=tenant_id,
                             name=name,
                             description=template_db.description,
                             vnf_mapping=vnf_mapping,
                             vnffgd_id=template_id,
                             attributes=template_db.get('template'),
                             status=constants.PENDING_CREATE)
            context.session.add(vnffg_db)

            nfp_id = uuidutils.generate_uuid()
            sfc_id = uuidutils.generate_uuid()
            classifier_id = uuidutils.generate_uuid()

            nfp_db = VnffgNfp(id=nfp_id, vnffg_id=vnffg_id,
                              tenant_id=tenant_id,
                              name=nfp_dict['name'],
                              status=constants.PENDING_CREATE,
                              path_id=nfp_dict['path_id'],
                              symmetrical=symmetrical)
            context.session.add(nfp_db)

            chain = self._create_port_chain(context, vnf_mapping, template_db,
                                            nfp_dict['name'])
            LOG.debug('chain: %s', chain)
            sfc_db = VnffgChain(id=sfc_id,
                                tenant_id=tenant_id,
                                status=constants.PENDING_CREATE,
                                symmetrical=symmetrical,
                                chain=chain,
                                nfp_id=nfp_id,
                                path_id=nfp_dict['path_id'])

            context.session.add(sfc_db)

            sfcc_db = VnffgClassifier(id=classifier_id,
                                      tenant_id=tenant_id,
                                      status=constants.PENDING_CREATE,
                                      nfp_id=nfp_id,
                                      chain_id=sfc_id)
            context.session.add(sfcc_db)

            match = self._policy_to_acl_criteria(context, template_db,
                                                 nfp_dict['name'],
                                                 vnf_mapping)
            LOG.debug('acl_match %s', match)

            match_db_table = ACLMatchCriteria(
                id=uuidutils.generate_uuid(),
                vnffgc_id=classifier_id,
                **match)

            context.session.add(match_db_table)

        return self._make_vnffg_dict(vnffg_db)

    @staticmethod
    def _create_nfp_pre(template_db):
        template = template_db.template['vnffgd']['topology_template']
        nfp_dict = dict()
        vnffg_name = list(template['groups'].keys())[0]
        # we assume only one NFP for initial implementation
        nfp_dict['name'] = template['groups'][vnffg_name]['members'][0]
        nfp_dict['path_id'] = template['node_templates'][nfp_dict['name']][
            'properties']['id']

        if not nfp_dict['path_id']:
            # TODO(trozet): do we need to check if this path ID is already
            # taken by another VNFFG
            nfp_dict['path_id'] = random.randint(1, 16777216)

        return nfp_dict

    def _create_port_chain(self, context, vnf_mapping, template_db, nfp_name):
        """Creates a list of physical port ids to represent an ordered chain

        :param context: SQL session context
        :param vnf_mapping: dict of VNFD to VNF instance mappings
        :param template_db: VNFFG Descriptor
        :param nfp_name: name of the forwarding path with chain requirements
        :return: list of port chain including vnf name and list of CPs
        """
        chain_list = []
        prev_forwarder = None
        vnfm_plugin = manager.TackerManager.get_service_plugins()['VNFM']
        # Build the list of logical chain representation
        logical_chain = self._get_nfp_attribute(template_db.template,
                                                nfp_name, 'path')
        # Build physical port chain
        for element in logical_chain:
            if element['forwarder'] not in vnf_mapping.keys():
                raise nfvo.NfpForwarderNotFoundException(vnfd=element[
                                                         'forwarder'],
                                                         mapping=vnf_mapping)
            # TODO(trozet): validate CP in VNFD has forwarding capability
            # Find VNF resources
            vnf = vnfm_plugin.get_vnf_resources(context,
                                                vnf_mapping[element[
                                                    'forwarder']]
                                                )
            vnf_info = vnfm_plugin.get_vnf(context,
                                           vnf_mapping[element['forwarder']])
            vnf_cp = None
            for resource in vnf:
                if resource['name'] == element['capability']:
                    vnf_cp = resource['id']
                    break
            if vnf_cp is None:
                raise nfvo.VnffgCpNotFoundException(cp_id=element[
                    'capability'], vnf_id=vnf_mapping[element['forwarder']])
            # Check if this is a new VNF entry in the chain
            if element['forwarder'] != prev_forwarder:
                chain_list.append({'name': vnf_info['name'],
                                   CP: [vnf_cp]})
                prev_forwarder = element['forwarder']
            # Must be an egress CP
            else:
                if len(chain_list[-1][CP]) > 1:
                    raise nfvo.NfpRequirementsException(vnfd=element[
                        'forwarder'])
                else:
                    chain_list[-1][CP].append(vnf_cp)

        return chain_list

    @staticmethod
    def _get_vnffg_property(template, vnffg_property):
        template = template['vnffgd']['topology_template']
        vnffg_name = list(template['groups'].keys())[0]
        try:
            return template['groups'][vnffg_name]['properties'][vnffg_property]
        except KeyError:
            raise nfvo.VnffgPropertyNotFoundException(
                vnffg_property=vnffg_property)

    @staticmethod
    def _get_nfp_attribute(template, nfp, attribute):
        """Finds any attribute of an NFP described in a template

        :param template: VNFFGD template
        :param nfp: name of NFP
        :param attribute: attribute to find
        :return: value of attribute from template
        """
        template = template['vnffgd']['topology_template']
        try:
            attr_val = VnffgPluginDbMixin._search_value(
                template['node_templates'][nfp], attribute)
            if attr_val is None:
                LOG.debug('NFP %(nfp)s, attr %(attr)s',
                          {'nfp': template['node_templates'][nfp],
                           'attr': attribute})
                raise nfvo.NfpAttributeNotFoundException(attribute=attribute)
            else:
                return attr_val
        except KeyError:
            raise nfvo.NfpAttributeNotFoundException(attribute=attribute)

    @staticmethod
    def _search_value(search_dict, search_key):
        for k, v in search_dict.items():
            if k == search_key:
                return v
            elif isinstance(v, dict):
                val = VnffgPluginDbMixin._search_value(v, search_key)
                if val is not None:
                    return val

    def _get_vnf_mapping(self, context, vnf_mapping, vnf_members):
        """Creates/validates a mapping of VNFD names to VNF IDs for NFP.

        :param context: SQL session context
        :param vnf_mapping: dict of requested VNFD:VNF_ID mappings
        :param vnf_members: list of constituent VNFs from a VNFFG
        :return: dict of VNFD:VNF_ID mappings
        """
        vnfm_plugin = manager.TackerManager.get_service_plugins()['VNFM']
        new_mapping = dict()

        for vnfd in vnf_members:
            # there should only be one ID returned for a unique name
            try:
                vnfd_id = vnfm_plugin.get_vnfds(context, {'name': [vnfd]},
                                                fields=['id']).pop()['id']
            except Exception:
                raise nfvo.VnffgdVnfdNotFoundException(vnfd_name=vnfd)
            if vnfd_id is None:
                raise nfvo.VnffgdVnfdNotFoundException(vnfd_name=vnfd)
            else:
                # if no VNF mapping, we need to abstractly look for instances
                # that match VNFD
                if vnf_mapping is None or vnfd not in vnf_mapping.keys():
                    # find suitable VNFs from vnfd_id
                    LOG.debug('Searching VNFS with id %s', vnfd_id)
                    vnf_list = vnfm_plugin.get_vnfs(context,
                                                    {'vnfd_id': [vnfd_id]},
                                                    fields=['id'])
                    if len(vnf_list) == 0:
                        raise nfvo.VnffgInvalidMappingException(vnfd_name=vnfd)
                    else:
                        LOG.debug('Matching VNFs found %s', vnf_list)
                        vnf_list = [vnf['id'] for vnf in vnf_list]
                    if len(vnf_list) > 1:
                        new_mapping[vnfd] = random.choice(vnf_list)
                    else:
                        new_mapping[vnfd] = vnf_list[0]
                # if VNF mapping, validate instances exist and match the VNFD
                else:
                    vnf_vnfd = vnfm_plugin.get_vnf(context, vnf_mapping[vnfd],
                                                   fields=['vnfd_id'])
                    if vnf_vnfd is not None:
                        vnf_vnfd_id = vnf_vnfd['vnfd_id']
                    else:
                        raise nfvo.VnffgInvalidMappingException(vnfd_name=vnfd)
                    if vnfd_id != vnf_vnfd_id:
                        raise nfvo.VnffgInvalidMappingException(vnfd_name=vnfd)
                    else:
                        new_mapping[vnfd] = vnf_mapping.pop(vnfd)
        self._validate_vim(context, new_mapping.values())
        return new_mapping

    def _validate_vim(self, context, vnfs):
        """Validates all VNFs are in the same VIM

        :param context: SQL Session Context
        :param vnfs: List of VNF instance IDs
        :return: None
        """
        LOG.debug('validating vim for vnfs %s', vnfs)
        vnfm_plugin = manager.TackerManager.get_service_plugins()['VNFM']
        vim_id = None
        for vnf in vnfs:
            vnf_dict = vnfm_plugin.get_vnf(context, vnf)
            if vim_id is None:
                vim_id = vnf_dict['vim_id']
            elif vnf_dict['vim_id'] != vim_id:
                raise nfvo.VnffgVimMappingException(vnf_id=vnf, vim_id=vim_id)

    def _policy_to_acl_criteria(self, context, template_db, nfp_name,
                                vnf_mapping):
        template = template_db.template['vnffgd']['topology_template']
        nfp = template['node_templates'][nfp_name]
        try:
            policy = nfp['properties']['policy']
        except KeyError:
            raise nfvo.NfpPolicyNotFoundException(policy=nfp)

        if 'type' in policy:
            if policy['type'] != 'ACL':
                raise nfvo.NfpPolicyTypeError(type=policy['type'])

        if 'criteria' not in policy:
            raise nfvo.NfpPolicyCriteriaError(error="Missing criteria in "
                                              "policy")
        match = dict()
        for criteria in policy['criteria']:
            for key, val in criteria.items():
                if key in MATCH_CRITERIA:
                    match.update(self._convert_criteria(context, key, val,
                                                        vnf_mapping))
                else:
                    raise nfvo.NfpPolicyCriteriaError(error="Unsupported "
                                                      "criteria: "
                                                      "{}".format(key))
        return match

    def _convert_criteria(self, context, criteria, value, vnf_mapping):
        """Method is used to convert criteria to proper db value from template

        :param context: SQL session context
        :param criteria: input criteria name
        :param value: input value
        :param vnf_mapping: mapping of VNFD to VNF instances
        :return: converted dictionary
        """

        if criteria.endswith('_range'):
            prefix = criteria[:-6]
            criteria_min = prefix + "_min"
            criteria_max = prefix + "_max"
            try:
                min_val, max_val = value.split('-')
            except ValueError:
                raise nfvo.NfpPolicyCriteriaError(error="Range missing or "
                                                  "incorrect for "
                                                  "%s".format(criteria))
            return {criteria_min: int(min_val), criteria_max: int(max_val)}

        elif criteria.endswith('_name'):
            prefix = criteria[:-5]
            vnf_id = list(vnf_mapping.values())[0]
            new_value = self._vim_resource_name_to_id(context, prefix, value,
                                                      vnf_id)
            new_name = prefix + "_id"
            return {new_name: new_value}

        else:
            return {criteria: value}

    def _vim_resource_name_to_id(self, context, resource, name, vnf_id):
        """Converts a VIM resource name to its ID

        :param context: SQL session context
        :param resource: resource type to find (network, subnet, etc)
        :param name: name of the resource to find its ID
        :param vnf_id: A VNF instance ID that is part of the chain to which
               the classifier will apply to
        :return: ID of the resource name
        """
        # this should be overridden with driver call to find ID given name
        # for resource
        return uuidutils.generate_uuid()

    # called internally, not by REST API
    # instance_id = None means error on creation
    def _create_vnffg_post(self, context, sfc_instance_id,
                           fc_instance_id, vnffg_dict):
        LOG.debug('SFC created instance is %s', sfc_instance_id)
        LOG.debug('Flow Classifier created instance is %s', fc_instance_id)
        nfp_dict = self.get_nfp(context, vnffg_dict['forwarding_paths'])
        sfc_id = nfp_dict['chain_id']
        classifier_id = nfp_dict['classifier_id']
        with context.session.begin(subtransactions=True):
            query = (self._model_query(context, VnffgChain).
                     filter(VnffgChain.id == sfc_id).
                     filter(VnffgChain.status == constants.PENDING_CREATE).
                     one())
            query.update({'instance_id': sfc_instance_id})
            if sfc_instance_id is None:
                query.update({'status': constants.ERROR})
            else:
                query.update({'status': constants.ACTIVE})

            query = (self._model_query(context, VnffgClassifier).
                     filter(VnffgClassifier.id == classifier_id).
                     filter(VnffgClassifier.status ==
                            constants.PENDING_CREATE).
                     one())
            query.update({'instance_id': fc_instance_id})

            if fc_instance_id is None:
                query.update({'status': constants.ERROR})
            else:
                query.update({'status': constants.ACTIVE})

    def _create_vnffg_status(self, context, vnffg):
        nfp = self.get_nfp(context, vnffg['forwarding_paths'])
        chain = self.get_sfc(context, nfp['chain_id'])
        classifier = self.get_classifier(context, nfp['classifier_id'])

        if classifier['status'] == constants.ERROR or chain['status'] ==\
                constants.ERROR:
            self._update_all_status(context, vnffg['id'], nfp['id'],
                                    constants.ERROR)
        elif classifier['status'] == constants.ACTIVE and \
                chain['status'] == constants.ACTIVE:
            self._update_all_status(context, vnffg['id'], nfp['id'],
                                    constants.ACTIVE)

    def _update_all_status(self, context, vnffg_id, nfp_id, status):
        with context.session.begin(subtransactions=True):
            query = (self._model_query(context, Vnffg).
                     filter(Vnffg.id == vnffg_id))
            query.update({'status': status})
            nfp_query = (self._model_query(context, VnffgNfp).
                         filter(VnffgNfp.id == nfp_id))
            nfp_query.update({'status': status})

    def _make_vnffg_dict(self, vnffg_db, fields=None):
        LOG.debug('vnffg_db %s', vnffg_db)
        LOG.debug('vnffg_db nfp %s', vnffg_db.forwarding_paths)
        res = {
            'forwarding_paths': vnffg_db.forwarding_paths[0]['id']
        }
        key_list = ('id', 'tenant_id', 'name', 'description',
                    'vnf_mapping', 'status', 'vnffgd_id', 'attributes')
        res.update((key, vnffg_db[key]) for key in key_list)
        return self._fields(res, fields)

    def _update_vnffg_pre(self, context, vnffg_id):
        vnffg = self.get_vnffg(context, vnffg_id)
        nfp = self.get_nfp(context, vnffg['forwarding_paths'])
        sfc = self.get_sfc(context, nfp['chain_id'])
        fc = self.get_classifier(context, nfp['classifier_id'])
        with context.session.begin(subtransactions=True):
            vnffg_db = self._get_vnffg_db(context, vnffg['id'], _ACTIVE_UPDATE,
                                          constants.PENDING_UPDATE)
            self._get_nfp_db(context, nfp['id'], _ACTIVE_UPDATE,
                             constants.PENDING_UPDATE)
            self._get_sfc_db(context, sfc['id'], _ACTIVE_UPDATE,
                             constants.PENDING_UPDATE)
            self._get_classifier_db(context, fc['id'], _ACTIVE_UPDATE,
                                    constants.PENDING_UPDATE)
        return self._make_vnffg_dict(vnffg_db)

    def _update_vnffg_post(self, context, vnffg_id, new_status,
                           new_vnffg=None):
        vnffg = self.get_vnffg(context, vnffg_id)
        nfp = self.get_nfp(context, vnffg['forwarding_paths'])
        with context.session.begin(subtransactions=True):
            query = (self._model_query(context, Vnffg).
                     filter(Vnffg.id == vnffg['id']).
                     filter(Vnffg.status == constants.PENDING_UPDATE))
            query.update({'status': new_status})

            nfp_query = (self._model_query(context, VnffgNfp).
                         filter(VnffgNfp.id == nfp['id']).
                         filter(VnffgNfp.status == constants.PENDING_UPDATE))
            nfp_query.update({'status': new_status})

            if new_vnffg is not None:
                for key in _VALID_VNFFG_UPDATE_ATTRIBUTES:
                    query.update({key: new_vnffg[key]})
                nfp_query.update({'symmetrical': new_vnffg['symmetrical']})

    def _update_sfc_post(self, context, sfc_id, new_status, new_sfc=None):
        with context.session.begin(subtransactions=True):
            sfc_query = (self._model_query(context, VnffgChain).
                         filter(VnffgChain.id == sfc_id).
                         filter(VnffgChain.status == constants.PENDING_UPDATE))
            sfc_query.update({'status': new_status})

            if new_sfc is not None:
                for key in _VALID_SFC_UPDATE_ATTRIBUTES:
                    sfc_query.update({key: new_sfc[key]})

    def _update_classifier_post(self, context, sfc_id, new_status,
                               new_fc=None):
        with context.session.begin(subtransactions=True):
            fc_query = (self._model_query(context, VnffgClassifier).
                        filter(VnffgClassifier.id == sfc_id).
                        filter(VnffgClassifier.status ==
                        constants.PENDING_UPDATE))
            fc_query.update({'status': new_status})

            if new_fc is not None:
                for key in _VALID_FC_UPDATE_ATTRIBUTES:
                    fc_query.update({key: new_fc[key]})

    def _get_vnffg_db(self, context, vnffg_id, current_statuses, new_status):
        try:
            vnffg_db = (
                self._model_query(context, Vnffg).
                filter(Vnffg.id == vnffg_id).
                filter(Vnffg.status.in_(current_statuses)).
                with_lockmode('update').one())
        except orm_exc.NoResultFound:
            raise nfvo.VnffgNotFoundException(vnffg_id=vnffg_id)
        if vnffg_db.status == constants.PENDING_UPDATE:
            raise nfvo.VnffgInUse(vnffg_id=vnffg_id)
        vnffg_db.update({'status': new_status})
        return vnffg_db

    def _get_nfp_db(self, context, nfp_id, current_statuses, new_status):
        try:
            nfp_db = (
                self._model_query(context, VnffgNfp).
                filter(VnffgNfp.id == nfp_id).
                filter(VnffgNfp.status.in_(current_statuses)).
                with_lockmode('update').one())
        except orm_exc.NoResultFound:
            raise nfvo.NfpNotFoundException(nfp_id=nfp_id)
        if nfp_db.status == constants.PENDING_UPDATE:
            raise nfvo.NfpInUse(nfp_id=nfp_id)
        nfp_db.update({'status': new_status})
        return nfp_db

    def _get_sfc_db(self, context, sfc_id, current_statuses, new_status):
        try:
            sfc_db = (
                self._model_query(context, VnffgChain).
                filter(VnffgChain.id == sfc_id).
                filter(VnffgChain.status.in_(current_statuses)).
                with_lockmode('update').one())
        except orm_exc.NoResultFound:
            raise nfvo.SfcNotFoundException(sfc_id=sfc_id)
        if sfc_db.status == constants.PENDING_UPDATE:
            raise nfvo.SfcInUse(sfc_id=sfc_id)
        sfc_db.update({'status': new_status})
        return sfc_db

    def _get_classifier_db(self, context, fc_id, current_statuses, new_status):
        try:
            fc_db = (
                self._model_query(context, VnffgClassifier).
                filter(VnffgClassifier.id == fc_id).
                filter(VnffgClassifier.status.in_(current_statuses)).
                with_lockmode('update').one())
        except orm_exc.NoResultFound:
            raise nfvo.ClassifierNotFoundException(fc_id=fc_id)
        if fc_db.status == constants.PENDING_UPDATE:
            raise nfvo.ClassifierInUse(fc_id=fc_id)
        fc_db.update({'status': new_status})
        return fc_db

    def _delete_vnffg_pre(self, context, vnffg_id):
        vnffg = self.get_vnffg(context, vnffg_id)
        nfp = self.get_nfp(context, vnffg['forwarding_paths'])
        chain = self.get_sfc(context, nfp['chain_id'])
        classifier = self.get_classifier(context, nfp['classifier_id'])
        with context.session.begin(subtransactions=True):
            vnffg_db = self._get_vnffg_db(
                context, vnffg['id'], _ACTIVE_UPDATE_ERROR_DEAD,
                constants.PENDING_DELETE)
            self._get_nfp_db(context, nfp['id'], _ACTIVE_UPDATE_ERROR_DEAD,
                             constants.PENDING_DELETE)
            self._get_sfc_db(context, chain['id'], _ACTIVE_UPDATE_ERROR_DEAD,
                             constants.PENDING_DELETE)
            self._get_classifier_db(context, classifier['id'],
                                    _ACTIVE_UPDATE_ERROR_DEAD,
                                    constants.PENDING_DELETE)

        return self._make_vnffg_dict(vnffg_db)

    def _delete_vnffg_post(self, context, vnffg_id, error):
        vnffg = self.get_vnffg(context, vnffg_id)
        nfp = self.get_nfp(context, vnffg['forwarding_paths'])
        chain = self.get_sfc(context, nfp['chain_id'])
        classifier = self.get_classifier(context, nfp['classifier_id'])
        with context.session.begin(subtransactions=True):
            vnffg_query = (
                self._model_query(context, Vnffg).
                filter(Vnffg.id == vnffg['id']).
                filter(Vnffg.status == constants.PENDING_DELETE))
            nfp_query = (
                self._model_query(context, VnffgNfp).
                filter(VnffgNfp.id == nfp['id']).
                filter(VnffgNfp.status == constants.PENDING_DELETE))
            sfc_query = (
                self._model_query(context, VnffgChain).
                filter(VnffgChain.id == chain['id']).
                filter(VnffgChain.status == constants.PENDING_DELETE))
            fc_query = (
                self._model_query(context, VnffgClassifier).
                filter(VnffgClassifier.id == classifier['id']).
                filter(VnffgClassifier.status == constants.PENDING_DELETE))
            match_query = (
                self._model_query(context, ACLMatchCriteria).
                filter(ACLMatchCriteria.vnffgc_id == classifier['id']))
            if error:
                vnffg_query.update({'status': constants.ERROR})
                nfp_query.update({'status': constants.ERROR})
                sfc_query.update({'status': constants.ERROR})
                fc_query.update({'status': constants.ERROR})
            else:
                match_query.delete()
                fc_query.delete()
                sfc_query.delete()
                nfp_query.delete()
                vnffg_query.delete()

            vnffgd_id = vnffg.get('vnffgd_id')
            template_db = self._get_resource(context, VnffgTemplate,
                                             vnffgd_id)

            if template_db.get('template_source') == 'inline':
                self.delete_vnffgd(context, vnffgd_id)

    def _make_template_dict(self, template, fields=None):
        res = {}
        key_list = ('id', 'tenant_id', 'name', 'description', 'template',
                    'template_source')
        res.update((key, template[key]) for key in key_list)
        return self._fields(res, fields)

    def _make_acl_match_dict(self, acl_match_db):
        key_list = MATCH_DB_KEY_LIST
        return {key: entry[key] for key in key_list for entry in acl_match_db
                if entry[key]}

    def _make_classifier_dict(self, classifier_db, fields=None):
        LOG.debug('classifier_db %s', classifier_db)
        LOG.debug('classifier_db match %s', classifier_db.match)
        res = {
            'match': self._make_acl_match_dict(classifier_db.match)
        }
        key_list = ('id', 'tenant_id', 'instance_id', 'status', 'chain_id',
                    'nfp_id')
        res.update((key, classifier_db[key]) for key in key_list)
        return self._fields(res, fields)

    def _make_nfp_dict(self, nfp_db, fields=None):
        LOG.debug('nfp_db %s', nfp_db)
        res = {'chain_id': nfp_db.chain['id'],
               'classifier_id': nfp_db.classifier['id']}
        key_list = ('name', 'id', 'tenant_id', 'symmetrical', 'status',
                    'path_id', 'vnffg_id')
        res.update((key, nfp_db[key]) for key in key_list)
        return self._fields(res, fields)

    def _make_chain_dict(self, chain_db, fields=None):
        LOG.debug('chain_db %s', chain_db)
        res = {}
        key_list = ('id', 'tenant_id', 'symmetrical', 'status', 'chain',
                    'path_id', 'nfp_id', 'instance_id')
        res.update((key, chain_db[key]) for key in key_list)
        return self._fields(res, fields)

    def _get_resource(self, context, model, res_id):
        try:
            return self._get_by_id(context, model, res_id)
        except orm_exc.NoResultFound:
            if issubclass(model, Vnffg):
                raise nfvo.VnffgNotFoundException(vnffg_id=res_id)
            elif issubclass(model, VnffgClassifier):
                raise nfvo.ClassifierNotFoundException(classifier_id=res_id)
            if issubclass(model, VnffgTemplate):
                raise nfvo.VnffgdNotFoundException(vnffgd_id=res_id)
            if issubclass(model, VnffgChain):
                raise nfvo.SfcNotFoundException(sfc_id=res_id)
            else:
                raise
