# Copyright 2016 Brocade Communications System, Inc.
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

import os
import six
import yaml

from keystoneauth1 import exceptions
from keystoneauth1 import identity
from keystoneauth1.identity import v3
from keystoneauth1 import session
from neutronclient.common import exceptions as nc_exceptions
from neutronclient.v2_0 import client as neutron_client
from oslo_config import cfg
from oslo_log import log as logging

from tacker._i18n import _
from tacker.common import log
from tacker import context as t_context
from tacker.extensions import nfvo
from tacker.keymgr import API as KEYMGR_API
from tacker.mistral import mistral_client
from tacker.nfvo.drivers.vim import abstract_vim_driver
from tacker.nfvo.drivers.vnffg import abstract_vnffg_driver
from tacker.nfvo.drivers.workflow import workflow_generator
from tacker.nfvo.nfvo_plugin import NfvoPlugin
from tacker.plugins.common import constants
from tacker.vnfm import keystone

LOG = logging.getLogger(__name__)
CONF = cfg.CONF

OPTS = [cfg.StrOpt('openstack', default='/etc/tacker/vim/fernet_keys',
                   help='Dir.path to store fernet keys.'),
        cfg.BoolOpt('use_barbican', default=False,
                    help=_('Use barbican to encrypt vim password if True, '
                           'save vim credentials in local file system '
                           'if False'))
        ]

# same params as we used in ping monitor driver
OPENSTACK_OPTS = [
    cfg.StrOpt('count', default='1',
               help=_('Number of ICMP packets to send')),
    cfg.StrOpt('timeout', default='1',
               help=_('Number of seconds to wait for a response')),
    cfg.StrOpt('interval', default='1',
               help=_('Number of seconds to wait between packets'))
]
cfg.CONF.register_opts(OPTS, 'vim_keys')
cfg.CONF.register_opts(OPENSTACK_OPTS, 'vim_monitor')

_VALID_RESOURCE_TYPES = {'network': {'client': neutron_client.Client,
                                     'cmd': 'list_networks',
                                     'vim_res_name': 'networks',
                                     'filter_attr': 'name'
                                     }
                         }

FC_MAP = {'name': 'name',
          'description': 'description',
          'eth_type': 'ethertype',
          'ip_src_prefix': 'source_ip_prefix',
          'ip_dst_prefix': 'destination_ip_prefix',
          'source_port_min': 'source_port_range_min',
          'source_port_max': 'source_port_range_max',
          'destination_port_min': 'destination_port_range_min',
          'destination_port_max': 'destination_port_range_max',
          'network_src_port_id': 'logical_source_port',
          'network_dst_port_id': 'logical_destination_port'}

CONNECTION_POINT = 'connection_points'
SFC_ENCAP = 'sfc_encap'


def config_opts():
    return [('vim_keys', OPTS), ('vim_monitor', OPENSTACK_OPTS)]


class OpenStack_Driver(abstract_vim_driver.VimAbstractDriver,
                       abstract_vnffg_driver.VnffgAbstractDriver):
    """Driver for OpenStack VIM

    OpenStack driver handles interactions with local as well as
    remote OpenStack instances. The driver invokes keystone service for VIM
    authorization and validation. The driver is also responsible for
    discovering placement attributes such as regions, availability zones
    """

    def __init__(self):
        self.keystone = keystone.Keystone()
        self.keystone.create_key_dir(CONF.vim_keys.openstack)

    def get_type(self):
        return 'openstack'

    def get_name(self):
        return 'OpenStack VIM Driver'

    def get_description(self):
        return 'OpenStack VIM Driver'

    def authenticate_vim(self, vim_obj):
        """Validate VIM auth attributes

        Initialize keystoneclient with provided authentication attributes.
        """
        verify = 'True' == vim_obj['auth_cred'].get('cert_verify', 'True') \
                 or False
        auth_url = vim_obj['auth_url']
        keystone_version = NfvoPlugin.validate_keystone_auth_url(
            auth_url=auth_url,
            verify=verify)
        auth_cred = self._get_auth_creds(vim_obj, keystone_version)
        return self._initialize_keystone(auth_cred)

    def _get_auth_creds(self, vim_obj, keystone_version):
        auth_cred = vim_obj['auth_cred']
        vim_project = vim_obj['vim_project']
        auth_cred['project_id'] = vim_project.get('id')
        auth_cred['project_name'] = vim_project.get('name')
        auth_cred['project_domain_name'] = vim_project.get(
            'project_domain_name')
        auth_cred['auth_url'] = vim_obj['auth_url']
        if keystone_version not in auth_cred['auth_url']:
            auth_cred['auth_url'] = auth_cred['auth_url'] + '/' + \
                keystone_version
        return auth_cred

    def _get_auth_plugin(self, **kwargs):
        auth_plugin = v3.Password(**kwargs)

        return auth_plugin

    def _initialize_keystone(self, auth):
        ks_client = self.keystone.initialize_client(**auth)
        return ks_client

    def _find_regions(self, ks_client):
        region_info = ks_client.regions.list()
        region_list = [region.id for region in region_info]
        return region_list

    def discover_placement_attr(self, vim_obj, ks_client):
        """Fetch VIM placement information

        Attributes can include regions, AZ.
        """
        try:
            regions_list = self._find_regions(ks_client)
        except (exceptions.Unauthorized, exceptions.BadRequest) as e:
            LOG.warning("Authorization failed for user")
            raise nfvo.VimUnauthorizedException(message=e.message)
        vim_obj['placement_attr'] = {'regions': regions_list}
        return vim_obj

    @log.log
    def register_vim(self, vim_obj):
        """Validate and set VIM placements."""

        if 'key_type' in vim_obj['auth_cred']:
            vim_obj['auth_cred'].pop(u'key_type')
        if 'secret_uuid' in vim_obj['auth_cred']:
            vim_obj['auth_cred'].pop(u'secret_uuid')

        ks_client = self.authenticate_vim(vim_obj)
        self.discover_placement_attr(vim_obj, ks_client)
        self.encode_vim_auth(vim_obj['id'], vim_obj['auth_cred'])
        LOG.debug('VIM registration completed for %s', vim_obj)

    @log.log
    def deregister_vim(self, vim_obj):
        """Deregister VIM from NFVO

        Delete VIM keys from file system
        """
        self.delete_vim_auth(vim_obj['id'], vim_obj['auth_cred'])

    @log.log
    def delete_vim_auth(self, vim_id, auth):
        """Delete vim information

        Delete vim key stored in file system
        """
        LOG.debug('Attempting to delete key for vim id %s', vim_id)

        if auth.get('key_type') == 'barbican_key':
            try:
                k_context = t_context.generate_tacker_service_context()
                keystone_conf = CONF.keystone_authtoken
                secret_uuid = auth['secret_uuid']
                keymgr_api = KEYMGR_API(keystone_conf.auth_url)
                keymgr_api.delete(k_context, secret_uuid)
                LOG.debug('VIM key deleted successfully for vim %s',
                          vim_id)
            except Exception as ex:
                LOG.warning('VIM key deletion failed for vim %s due to %s',
                            vim_id,
                            ex)
                raise
        else:
            key_file = os.path.join(CONF.vim_keys.openstack, vim_id)
            try:
                os.remove(key_file)
                LOG.debug('VIM key deleted successfully for vim %s',
                          vim_id)
            except OSError:
                LOG.warning('VIM key deletion failed for vim %s',
                            vim_id)

    @log.log
    def encode_vim_auth(self, vim_id, auth):
        """Encode VIM credentials

         Store VIM auth using fernet key encryption
         """
        fernet_key, fernet_obj = self.keystone.create_fernet_key()
        encoded_auth = fernet_obj.encrypt(auth['password'].encode('utf-8'))
        auth['password'] = encoded_auth

        if CONF.vim_keys.use_barbican:
            try:
                k_context = t_context.generate_tacker_service_context()
                keystone_conf = CONF.keystone_authtoken
                keymgr_api = KEYMGR_API(keystone_conf.auth_url)
                secret_uuid = keymgr_api.store(k_context, fernet_key)

                auth['key_type'] = 'barbican_key'
                auth['secret_uuid'] = secret_uuid
                LOG.debug('VIM auth successfully stored for vim %s',
                          vim_id)
            except Exception as ex:
                LOG.warning('VIM key creation failed for vim %s due to %s',
                            vim_id,
                            ex)
                raise

        else:
            auth['key_type'] = 'fernet_key'
            key_file = os.path.join(CONF.vim_keys.openstack, vim_id)
            try:
                with open(key_file, 'wb') as f:
                    if six.PY2:
                        f.write(fernet_key.decode('utf-8'))
                    else:
                        f.write(fernet_key)
                    LOG.debug('VIM auth successfully stored for vim %s',
                              vim_id)
            except IOError:
                raise nfvo.VimKeyNotFoundException(vim_id=vim_id)

    @log.log
    def get_vim_resource_id(self, vim_obj, resource_type, resource_name):
        """Locates openstack resource by type/name and returns ID

        :param vim_obj: VIM info used to access openstack instance
        :param resource_type: type of resource to find
        :param resource_name: name of resource to locate
        :return: ID of resource
        """
        if resource_type in _VALID_RESOURCE_TYPES:
            res_cmd_map = _VALID_RESOURCE_TYPES[resource_type]
            client_type = res_cmd_map['client']
            cmd = res_cmd_map['cmd']
            filter_attr = res_cmd_map.get('filter_attr')
            vim_res_name = res_cmd_map['vim_res_name']
        else:
            raise nfvo.VimUnsupportedResourceTypeException(type=resource_type)

        client = self._get_client(vim_obj, client_type)
        cmd_args = {}
        if filter_attr:
            cmd_args[filter_attr] = resource_name

        try:
            resources = getattr(client, "%s" % cmd)(**cmd_args)[vim_res_name]
            LOG.debug('resources output %s', resources)
        except Exception:
            raise nfvo.VimGetResourceException(
                cmd=cmd, name=resource_name, type=resource_type)

        if len(resources) > 1:
            raise nfvo.VimGetResourceNameNotUnique(
                cmd=cmd, name=resource_name)
        elif len(resources) < 1:
            raise nfvo.VimGetResourceNotFoundException(
                cmd=cmd, name=resource_name)

        return resources[0]['id']

    @log.log
    def _get_client(self, vim_obj, client_type):
        """Initializes and returns an openstack client

        :param vim_obj: VIM Information
        :param client_type: openstack client to initialize
        :return: initialized client
        """
        verify = 'True' == vim_obj.get('cert_verify', 'True') or False
        auth_url = vim_obj['auth_url']
        keystone_version = NfvoPlugin.validate_keystone_auth_url(
            auth_url=auth_url,
            verify=verify)
        auth_cred = self._get_auth_creds(vim_obj, keystone_version)
        auth_plugin = self._get_auth_plugin(**auth_cred)
        sess = session.Session(auth=auth_plugin)
        return client_type(session=sess)

    def _translate_ip_protocol(self, ip_proto):
        if ip_proto == '1':
            return 'icmp'
        elif ip_proto == '6':
            return 'tcp'
        elif ip_proto == '17':
            return 'udp'
        else:
            return None

    def _create_classifier_params(self, fc):
        classifier_params = {}
        for field in fc:
            if field in FC_MAP:
                classifier_params[FC_MAP[field]] = fc[field]
            elif field == 'ip_proto':
                protocol = self._translate_ip_protocol(str(fc[field]))
                if not protocol:
                    raise ValueError('protocol %s not supported' % fc[field])
                classifier_params['protocol'] = protocol
            else:
                LOG.warning("flow classifier %s not supported by "
                            "networking-sfc driver", field)
        return classifier_params

    def create_flow_classifier(self, name, fc, auth_attr=None):
        if not auth_attr:
            LOG.warning("auth information required for n-sfc driver")
            return None
        fc['name'] = name
        LOG.debug('fc passed is %s', fc)

        sfc_classifier_params = self._create_classifier_params(fc)
        LOG.debug('sfc_classifier_params is %s', sfc_classifier_params)

        if len(sfc_classifier_params) > 0:
            neutronclient_ = NeutronClient(auth_attr)

            fc_id = neutronclient_.flow_classifier_create(
                sfc_classifier_params)
            return fc_id

        raise ValueError('empty match field for input flow classifier')

    def create_chain(self, name, path_id, fc_ids, vnfs, symmetrical=False,
                     correlation='mpls', auth_attr=None):
        if not auth_attr:
            LOG.warning("auth information required for n-sfc driver")
            return None

        neutronclient_ = NeutronClient(auth_attr)
        port_pairs_list = neutronclient_.port_pair_list()
        port_pair_groups_list = neutronclient_.port_pair_group_list()
        port_chains_list = neutronclient_.port_chain_list()
        port_pair_group_list = []
        new_ppgs = []
        new_pps = []

        try:
            for vnf in vnfs:
                # TODO(s3wong): once scaling is in place and VNFFG supports it
                # that model needs to be implemented to concatenate all
                # port-pairs into the port-pair-group
                # port pair group could include port-pairs from different VNFs
                if CONNECTION_POINT not in vnf:
                    LOG.warning("Chain creation failed due to missing "
                                "connection point info in VNF "
                                "%(vnfname)s", {'vnfname': vnf['name']})
                    return None
                cp_list = vnf[CONNECTION_POINT]
                num_cps = len(cp_list)
                if num_cps not in [1, 2]:
                    LOG.warning("Chain creation failed due to wrong number of "
                                "connection points: expected [1 | 2], got "
                                "%(cps)d", {'cps': num_cps})
                    return None
                if num_cps == 1:
                    ingress = cp_list[0]
                    egress = cp_list[0]
                else:
                    ingress = cp_list[0]
                    egress = cp_list[1]

                # If sfc_encap is True, pp_corr is set to correlation to
                # make use of correlation, otherwise pp_corr is set to None
                # to install SFC proxy
                sfc_encap = vnf.get(SFC_ENCAP, True)
                pp_corr = correlation if sfc_encap else None

                # valid_port_in_use function is used to find out the
                # port_pair_group_id of the existing port pair group
                # which was created by ingress and egress of current VNF
                port_pair_group_id = self.valid_port_in_use(
                    ingress, egress, port_pairs_list, port_pair_groups_list)
                if not port_pair_group_id:
                    # create the new port pair group if it is not existed
                    port_pair = dict()
                    port_pair['name'] = vnf['name'] + '-connection-points'
                    port_pair['description'] = 'port pair for ' + vnf['name']
                    port_pair['ingress'] = ingress
                    port_pair['egress'] = egress
                    port_pair['service_function_parameters'] = {
                        'correlation': pp_corr}
                    port_pair_id = neutronclient_.port_pair_create(port_pair)
                    if not port_pair_id:
                        LOG.warning("Chain creation failed due to port pair "
                                    "creation failed for vnf %(vnf)s",
                                    {'vnf': vnf['name']})
                        return None
                    new_pps.append(port_pair_id)
                    port_pair_group = {}
                    port_pair_group['name'] = vnf['name'] + '-port-pair-group'
                    port_pair_group['description'] = \
                        'port pair group for ' + vnf['name']
                    port_pair_group['port_pairs'] = []
                    port_pair_group['port_pairs'].append(port_pair_id)
                    port_pair_group_id = \
                        neutronclient_.port_pair_group_create(port_pair_group)
                    new_ppgs.append(port_pair_group_id)
                if not port_pair_group_id:
                    LOG.warning("Chain creation failed due to port pair group "
                                "creation failed for vnf "
                                "%(vnf)s", {'vnf': vnf['name']})
                    raise nfvo.CreateChainException(
                        message="Failed to create port-pair-group")
                port_pair_group_list.append(port_pair_group_id)

            # Check list port pair group between new port chain and the
            # existing port chains.  Networking-sfc does not allow to create
            # two port chains with the same port pair groups and the same order
            for pc in port_chains_list['port_chains']:
                ppg_list = pc['port_pair_groups']
                if ppg_list == port_pair_group_list:
                    # raise exception when the Vnffg path is already existing
                    raise nfvo.CreateChainException(
                        message="Vnffg path already exists")
        except nfvo.CreateChainException as e:
            # clean neutron resources such as port pair, port pair group and
            # flow classifier if we create it
            for ppg in new_ppgs:
                neutronclient_.port_pair_group_delete(ppg)
            for pp in new_pps:
                neutronclient_.port_pair_delete(pp)
            for fc_id in fc_ids:
                neutronclient_.flow_classifier_delete(fc_id)
            raise e

        # TODO(s3wong): should the chain name be given as a parameter?
        port_chain = {}
        port_chain['name'] = name + '-port-chain'
        if path_id:
            port_chain['chain_id'] = path_id
        port_chain['description'] = 'port-chain for Tacker VNFFG'
        port_chain['port_pair_groups'] = port_pair_group_list
        port_chain['flow_classifiers'] = fc_ids
        port_chain['chain_parameters'] = {}
        port_chain['chain_parameters']['symmetric'] = symmetrical
        port_chain['chain_parameters']['correlation'] = correlation
        return neutronclient_.port_chain_create(port_chain)

    def update_chain(self, chain_id, fc_ids, vnfs,
                     symmetrical=None, auth_attr=None):
        # (s3wong): chain can be updated either for
        # the list of fc and/or list of port-pair-group
        # since n-sfc driver does NOT track the ppg id
        # it will look it up (or reconstruct) from
        # networking-sfc DB --- but the caveat is that
        # the VNF name MUST be unique

        # TODO(mardim) Currently we figure out which VNF belongs to what
        # port-pair-group or port-pair through the name of VNF.
        # This is not the best approach. The best approach for the future
        # propably is to maintain in the database the ID of the
        # port-pair-group and port-pair that VNF belongs to so we can
        # implemement the update in a more robust way.

        if not auth_attr:
            LOG.warning("auth information required for n-sfc driver")
            return None

        neutronclient_ = NeutronClient(auth_attr)
        port_pairs_list = neutronclient_.port_pair_list()
        port_pair_groups_list = neutronclient_.port_pair_group_list()
        port_chains_list = neutronclient_.port_chain_list()
        new_ppgs = []
        updated_port_chain = dict()

        pc_info = neutronclient_.port_chain_show(chain_id)
        if set(fc_ids) != set(pc_info['port_chain']['flow_classifiers']):
            updated_port_chain['flow_classifiers'] = fc_ids
        old_ppgs = pc_info['port_chain']['port_pair_groups']
        old_ppgs_dict = {neutronclient_.
                    port_pair_group_show(ppg_id)['port_pair_group']['name'].
                    split('-')[0]: ppg_id for ppg_id in old_ppgs}
        past_ppgs_dict = old_ppgs_dict.copy()
        try:
            for vnf in vnfs:
                port_pair_group = {}
                port_pair = {}
                if vnf['name'] in old_ppgs_dict:
                    old_ppg_id = old_ppgs_dict.pop(vnf['name'])
                    new_ppgs.append(old_ppg_id)
                else:
                    if CONNECTION_POINT not in vnf:
                        LOG.warning("Chain update failed due to missing "
                                    "connection point info in VNF "
                                    "%(vnfname)s", {'vnfname': vnf['name']})
                        raise nfvo.UpdateChainException(
                            message="Connection point not found")
                    cp_list = vnf[CONNECTION_POINT]
                    num_cps = len(cp_list)
                    if num_cps not in [1, 2]:
                        LOG.warning("Chain update failed due to wrong number "
                                    "of connection points: expected [1 | 2],"
                                    "got %(cps)d", {'cps': num_cps})
                        raise nfvo.UpdateChainException(
                            message="Invalid number of connection points")
                    if num_cps == 1:
                        ingress = cp_list[0]
                        egress = cp_list[0]
                    else:
                        ingress = cp_list[0]
                        egress = cp_list[1]

                    # valid_port_in_use function is used to find out the
                    # port_pair_group_id of the existing port pair group
                    # which was created by ingress and egress of current VNF
                    port_pair_group_id = self.valid_port_in_use(
                        ingress, egress, port_pairs_list,
                        port_pair_groups_list)
                    if not port_pair_group_id:
                        port_pair['name'] = vnf['name'] + '-connection-points'
                        port_pair['description'] = \
                            'port pair for ' + vnf['name']
                        port_pair['ingress'] = ingress
                        port_pair['egress'] = egress
                        port_pair_id = neutronclient_.port_pair_create(
                            port_pair)
                        if not port_pair_id:
                            LOG.warning("Chain update failed due to port pair "
                                        "creation failed for "
                                        "vnf %(vnf)s", {'vnf': vnf['name']})
                            raise nfvo.UpdateChainException(
                                message="Failed to create port-pair")
                        port_pair_group['name'] = \
                            vnf['name'] + '-port-pair-group'
                        port_pair_group['description'] = \
                            'port pair group for ' + vnf['name']
                        port_pair_group['port_pairs'] = []
                        port_pair_group['port_pairs'].append(port_pair_id)
                        port_pair_group_id = neutronclient_.\
                            port_pair_group_create(port_pair_group)
                    if not port_pair_group_id:
                        LOG.warning("Chain update failed due to port pair "
                                    "group creation failed for vnf "
                                    "%(vnf)s", {'vnf': vnf['name']})
                        for pp_id in port_pair_group['port_pairs']:
                            neutronclient_.port_pair_delete(pp_id)
                        raise nfvo.UpdateChainException(
                            message="Failed to create port-pair-group")
                    new_ppgs.append(port_pair_group_id)
            for pc in port_chains_list['port_chains']:
                ppg_list = pc['port_pair_groups']
                if ppg_list == new_ppgs:
                    # raise exception when the Vnffg path already exists
                    nfvo.UpdateChainException(
                        message="Vnffg path already exists")
        except nfvo.UpdateChainException as e:
            self._delete_ppgs_and_pps(neutronclient_, new_ppgs,
                                      past_ppgs_dict, port_chains_list, fc_ids)
            raise e

        updated_port_chain['port_pair_groups'] = new_ppgs
        updated_port_chain['flow_classifiers'] = fc_ids
        try:
            pc_id = neutronclient_.port_chain_update(chain_id,
                                                     updated_port_chain)
        except (nc_exceptions.BadRequest, nfvo.UpdateChainException) as e:
            self._delete_ppgs_and_pps(neutronclient_, new_ppgs,
                                      past_ppgs_dict, port_chains_list)
            raise e
        for ppg_name in old_ppgs_dict:
            ppg_info = neutronclient_. \
                port_pair_group_show(old_ppgs_dict[ppg_name])
            ppg_inuse = self.valid_ppg_for_multiple_chain(
                ppg_info['port_pair_group']['id'], port_chains_list)
            if not ppg_inuse:
                neutronclient_.port_pair_group_delete(old_ppgs_dict[ppg_name])
                port_pairs = ppg_info['port_pair_group']['port_pairs']
                if port_pairs and len(port_pairs):
                    for j in range(0, len(port_pairs)):
                        pp_id = port_pairs[j]
                        neutronclient_.port_pair_delete(pp_id)
        return pc_id

    def delete_chain(self, chain_id, auth_attr=None):
        if not auth_attr:
            LOG.warning("auth information required for n-sfc driver")
            return None

        neutronclient_ = NeutronClient(auth_attr)
        neutronclient_.port_chain_delete(chain_id)

    def update_flow_classifier(self, chain_id, fc, auth_attr=None):
        if not auth_attr:
            LOG.warning("auth information required for n-sfc driver")
            return None

        fc_id = fc.pop('instance_id')
        fc_status = fc.pop('status')
        match_dict = fc.pop('match')
        fc.update(match_dict)

        sfc_classifier_params = self._create_classifier_params(fc)
        neutronclient_ = NeutronClient(auth_attr)
        if fc_status == constants.PENDING_UPDATE:
            fc_info = neutronclient_.flow_classifier_show(fc_id)
            for field in sfc_classifier_params:
                # If the new classifier is the same with the old one then
                # no change needed.
                if (fc_info['flow_classifier'].get(field) is not None) and \
                        (sfc_classifier_params[field] == fc_info[
                            'flow_classifier'][field]):
                    continue

                # If the new classifier has different match criteria
                # with the old one then we strip the classifier from
                # the chain we delete the old classifier and we create
                # a new one with the same name as before but with different
                # match criteria. We are not using the flow_classifier_update
                # from the n-sfc because it does not support match criteria
                # update for an existing classifier yet.
                else:
                    try:
                        self._dissociate_classifier_from_chain(chain_id,
                                                               [fc_id],
                                                               neutronclient_)
                    except Exception as e:
                        raise e
                    fc_id = neutronclient_.flow_classifier_create(
                        sfc_classifier_params)
                    if fc_id is None:
                        raise nfvo.UpdateClassifierException(
                            message="Failed to update classifiers")
                    break

        # If the new classifier is completely different from the existing
        # ones (name and match criteria) then we just create it.
        else:
            fc_id = neutronclient_.flow_classifier_create(
                sfc_classifier_params)
            if fc_id is None:
                raise nfvo.UpdateClassifierException(
                    message="Failed to update classifiers")

        return fc_id

    def _dissociate_classifier_from_chain(self, chain_id, fc_ids,
                                          neutronclient):
        pc_info = neutronclient.port_chain_show(chain_id)
        current_fc_list = pc_info['port_chain']['flow_classifiers']
        for fc_id in fc_ids:
            current_fc_list.remove(fc_id)
        pc_id = neutronclient.port_chain_update(chain_id,
                {'flow_classifiers': current_fc_list})
        if pc_id is None:
            raise nfvo.UpdateClassifierException(
                message="Failed to update classifiers")
        for fc_id in fc_ids:
            try:
                neutronclient.flow_classifier_delete(fc_id)
            except ValueError as e:
                raise e

    def remove_and_delete_flow_classifiers(self, chain_id, fc_ids,
                                           auth_attr=None):
        if not auth_attr:
            LOG.warning("auth information required for n-sfc driver")
            raise EnvironmentError('auth attribute required for'
                                   ' networking-sfc driver')
        neutronclient_ = NeutronClient(auth_attr)
        try:
            self._dissociate_classifier_from_chain(chain_id, fc_ids,
                                                   neutronclient_)
        except Exception as e:
            raise e

    def delete_flow_classifier(self, fc_id, auth_attr=None):
        if not auth_attr:
            LOG.warning("auth information required for n-sfc driver")
            raise EnvironmentError('auth attribute required for'
                                   ' networking-sfc driver')

        neutronclient_ = NeutronClient(auth_attr)
        neutronclient_.flow_classifier_delete(fc_id)

    def get_mistral_client(self, auth_dict):
        if not auth_dict:
            LOG.warning("auth dict required to instantiate mistral client")
            raise EnvironmentError('auth dict required for'
                                   ' mistral workflow driver')
        return mistral_client.MistralClient(
            keystone.Keystone().initialize_client(**auth_dict),
            auth_dict['token']).get_client()

    def prepare_and_create_workflow(self, resource, action,
                                    kwargs, auth_dict=None):
        mistral_client = self.get_mistral_client(auth_dict)
        wg = workflow_generator.WorkflowGenerator(resource, action)
        wg.task(**kwargs)
        if not wg.get_tasks():
            raise nfvo.NoTasksException(resource=resource, action=action)
        yaml.SafeDumper.ignore_aliases = lambda self, data: True
        definition_yaml = yaml.safe_dump(wg.definition)
        workflow = mistral_client.workflows.create(definition_yaml)
        return {'id': workflow[0].id, 'input': wg.get_input_dict()}

    def execute_workflow(self, workflow, auth_dict=None):
        return self.get_mistral_client(auth_dict) \
            .executions.create(
            workflow_identifier=workflow['id'],
            workflow_input=workflow['input'],
            wf_params={})

    def get_execution(self, execution_id, auth_dict=None):
        return self.get_mistral_client(auth_dict) \
            .executions.get(execution_id)

    def delete_execution(self, execution_id, auth_dict=None):
        return self.get_mistral_client(auth_dict).executions \
            .delete(execution_id, force=True)

    def delete_workflow(self, workflow_id, auth_dict=None):
        return self.get_mistral_client(auth_dict) \
            .workflows.delete(workflow_id)

    def _delete_ppgs_and_pps(self, neutronclient, new_ppgs,
                             past_ppgs_dict, pcs_list, fc_ids):
        if new_ppgs:
            for item in new_ppgs:
                if item not in past_ppgs_dict.values():
                    ppg_inuse = self.valid_ppg_for_multiple_chain(
                        item, pcs_list)
                    if not ppg_inuse:
                        # clean port pair and port pair group if
                        # it is not in used
                        new_ppg_info = neutronclient.port_pair_group_show(item)
                        neutronclient.port_pair_group_delete(item)
                        new_port_pairs = new_ppg_info['port_pair_group'][
                            'port_pairs']
                        if new_port_pairs and len(new_port_pairs):
                            for j in range(0, len(new_port_pairs)):
                                new_pp_id = new_port_pairs[j]
                                neutronclient.port_pair_delete(new_pp_id)
        # clean flow classifiers
        for fc_id in fc_ids:
            neutronclient.flow_classifier_delete(fc_id)

    def valid_port_in_use(self, ingress, egress, pps_list, ppgs_list):
        # This function checks the the ports are used or not and return the
        # port pair group id of these ports
        port_pair_list = pps_list['port_pairs']
        port_pair_group_list = ppgs_list['port_pair_groups']
        port_pair_id = None
        port_pair_group_id = None
        for pp in port_pair_list:
            if (ingress == pp['ingress']) and (egress == pp['egress']):
                port_pair_id = pp['id']
                break
        if port_pair_id:
            for ppg in port_pair_group_list:
                if port_pair_id in ppg['port_pairs']:
                    port_pair_group_id = ppg['id']
                    break
        return port_pair_group_id

    def valid_ppg_for_multiple_chain(self, ppg_id, pcs_list):
        # This function returns True if a ppg belongs to more than one
        # port chain. If not return False.
        count = 0
        for pc in pcs_list['port_chains']:
            if ppg_id in pc['port_pair_groups']:
                count = count + 1
        return True if count > 1 else False


class NeutronClient(object):
    """Neutron Client class for networking-sfc driver"""

    def __init__(self, auth_attr):
        auth_cred = auth_attr.copy()
        verify = 'True' == auth_cred.pop('cert_verify', 'True') or False
        auth = identity.Password(**auth_cred)
        sess = session.Session(auth=auth, verify=verify)
        self.client = neutron_client.Client(session=sess)

    def flow_classifier_show(self, fc_id):
        try:
            fc = self.client.show_sfc_flow_classifier(fc_id)
            if fc is None:
                raise ValueError('classifier %s not found' % fc_id)
            return fc
        except nc_exceptions.NotFound:
            LOG.error('classifier %s not found', fc_id)
            raise ValueError('classifier %s not found' % fc_id)

    def flow_classifier_create(self, fc_dict):
        LOG.debug("fc_dict passed is {fc_dict}".format(fc_dict=fc_dict))
        try:
            fc = self.client.create_sfc_flow_classifier(
                {'flow_classifier': fc_dict})
            return fc['flow_classifier']['id']
        except Exception as ex:
            LOG.error("Error while creating Flow Classifier: %s", str(ex))
            raise nfvo.FlowClassiferCreationFailed(message=str(ex))

    def flow_classifier_update(self, fc_id, update_fc):
        update_fc_dict = {'flow_classifier': update_fc}
        return self.client.update_sfc_flow_classifier(fc_id, update_fc_dict)

    def flow_classifier_delete(self, fc_id):
        try:
            self.client.delete_sfc_flow_classifier(fc_id)
        except nc_exceptions.NotFound:
            LOG.warning("fc %s not found", fc_id)
            raise ValueError('fc %s not found' % fc_id)

    def port_pair_create(self, port_pair_dict):
        try:
            pp = self.client.create_sfc_port_pair(
                {'port_pair': port_pair_dict})
        except nc_exceptions.BadRequest as e:
            LOG.error("create port pair returns %s", e)
            raise ValueError(str(e))

        if pp and len(pp):
            return pp['port_pair']['id']
        else:
            return None

    def port_pair_list(self):
        pp_list = self.client.list_sfc_port_pairs()
        return pp_list

    def port_pair_delete(self, port_pair_id):
        try:
            self.client.delete_sfc_port_pair(port_pair_id)
        except nc_exceptions.NotFound:
            LOG.warning('port pair %s not found', port_pair_id)
            raise ValueError('port pair %s not found' % port_pair_id)

    def port_pair_group_create(self, ppg_dict):
        try:
            ppg = self.client.create_sfc_port_pair_group(
                {'port_pair_group': ppg_dict})
        except nc_exceptions.BadRequest as e:
            LOG.warning('create port pair group returns %s', e)
            raise ValueError(str(e))

        if ppg and len(ppg):
            return ppg['port_pair_group']['id']
        else:
            return None

    def port_pair_group_list(self):
        ppg_list = self.client.list_sfc_port_pair_groups()
        return ppg_list

    def port_pair_group_delete(self, ppg_id):
        try:
            self.client.delete_sfc_port_pair_group(ppg_id)
        except nc_exceptions.NotFound:
            LOG.warning('port pair group %s not found', ppg_id)
            raise ValueError('port pair group %s not found' % ppg_id)

    def port_chain_create(self, port_chain_dict):
        try:
            pc = self.client.create_sfc_port_chain(
                {'port_chain': port_chain_dict})
        except nc_exceptions.BadRequest as e:
            LOG.warning('create port chain returns %s', e)
            raise ValueError(str(e))

        if pc and len(pc):
            return pc['port_chain']['id'], pc['port_chain']['chain_id']
        else:
            return None

    def port_chain_delete(self, port_chain_id):
        try:
            port_chain = self.client.show_sfc_port_chain(port_chain_id)
            if port_chain:
                self.client.delete_sfc_port_chain(port_chain_id)
                port_chain_list = \
                    self.client.list_sfc_port_chains()['port_chains']
                ppg_list = port_chain['port_chain'].get('port_pair_groups')
                if ppg_list and len(ppg_list):
                    for i in range(0, len(ppg_list)):
                        ppg_in_use = False
                        # Firstly, Tacker delete port chain, if a port pair
                        # group still belong to other port chains, Tacker
                        # will mark it as in_use and does not delete it.
                        for pc in port_chain_list:
                            if ppg_list[i] in pc['port_pair_groups']:
                                ppg_in_use = True
                                break
                        if not ppg_in_use:
                            ppg = self.client.show_sfc_port_pair_group(
                                ppg_list[i])
                            if ppg:
                                self.client.delete_sfc_port_pair_group(
                                    ppg_list[i])
                                port_pairs = \
                                    ppg['port_pair_group']['port_pairs']
                                if port_pairs and len(port_pairs):
                                    for j in range(0, len(port_pairs)):
                                        pp_id = port_pairs[j]
                                        self.client.delete_sfc_port_pair(pp_id)
        except nc_exceptions.NotFound:
            LOG.warning('port chain %s not found', port_chain_id)
            raise ValueError('port chain %s not found' % port_chain_id)

    def port_chain_update(self, port_chain_id, port_chain):
        try:
            pc = self.client.update_sfc_port_chain(port_chain_id,
                                    {'port_chain': port_chain})
        except nc_exceptions.BadRequest as e:
            LOG.warning('update port chain returns %s', e)
            raise ValueError(str(e))
        if pc and len(pc):
            return pc['port_chain']['id']
        else:
            raise nfvo.UpdateChainException(message="Failed to update "
                                                    "port-chain")

    def port_chain_list(self):
        pc_list = self.client.list_sfc_port_chains()
        return pc_list

    def port_chain_show(self, port_chain_id):
        try:
            port_chain = self.client.show_sfc_port_chain(port_chain_id)
            if port_chain is None:
                raise ValueError('port chain %s not found' % port_chain_id)

            return port_chain
        except nc_exceptions.NotFound:
            LOG.error('port chain %s not found', port_chain_id)
            raise ValueError('port chain %s not found' % port_chain_id)

    def port_pair_group_show(self, ppg_id):
        try:
            port_pair_group = self.client.show_sfc_port_pair_group(ppg_id)
            if port_pair_group is None:
                raise ValueError('port pair group %s not found' % ppg_id)

            return port_pair_group
        except nc_exceptions.NotFound:
            LOG.warning('port pair group %s not found', ppg_id)
            raise ValueError('port pair group %s not found' % ppg_id)
