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
from keystoneauth1.identity import v2
from keystoneauth1.identity import v3
from keystoneauth1 import session
from neutronclient.common import exceptions as nc_exceptions
from neutronclient.v2_0 import client as neutron_client
from oslo_config import cfg
from oslo_log import log as logging

from tacker._i18n import _
from tacker.common import log
from tacker.extensions import nfvo
from tacker.keymgr import API as KEYMGR_API
from tacker.mistral import mistral_client
from tacker.nfvo.drivers.vim import abstract_vim_driver
from tacker.nfvo.drivers.vnffg import abstract_vnffg_driver
from tacker.nfvo.drivers.workflow import workflow_generator
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
               help=_('number of ICMP packets to send')),
    cfg.StrOpt('timeout', default='1',
               help=_('number of seconds to wait for a response')),
    cfg.StrOpt('interval', default='1',
               help=_('number of seconds to wait between packets'))
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
        verify = ('True' == vim_obj['auth_cred'].get('cert_verify', 'True')
                 or False)
        auth_url = vim_obj['auth_url']
        keystone_version = self._validate_auth_url(auth_url, verify=verify)
        auth_cred = self._get_auth_creds(keystone_version, vim_obj)
        return self._initialize_keystone(keystone_version, auth_cred)

    def _get_auth_creds(self, keystone_version, vim_obj):
        auth_url = vim_obj['auth_url']
        auth_cred = vim_obj['auth_cred']
        vim_project = vim_obj['vim_project']

        if keystone_version not in auth_url:
            vim_obj['auth_url'] = auth_url + '/' + keystone_version
        if keystone_version == 'v3':
            auth_cred['project_id'] = vim_project.get('id')
            auth_cred['project_name'] = vim_project.get('name')
            auth_cred['project_domain_name'] = vim_project.get(
                'project_domain_name')
        else:
            auth_cred['tenant_id'] = vim_project.get('id')
            auth_cred['tenant_name'] = vim_project.get('name')
            # pop stuff not supported in keystone v2
            auth_cred.pop('user_domain_name', None)
            auth_cred.pop('user_id', None)
        auth_cred['auth_url'] = vim_obj['auth_url']
        return auth_cred

    def _get_auth_plugin(self, version, **kwargs):
        if version == 'v2.0':
            auth_plugin = v2.Password(**kwargs)
        else:
            auth_plugin = v3.Password(**kwargs)

        return auth_plugin

    def _validate_auth_url(self, auth_url, verify):
        try:
            keystone_version = self.keystone.get_version(auth_url, verify)
        except Exception as e:
            LOG.error('VIM Auth URL invalid')
            raise nfvo.VimConnectionException(message=str(e))
        return keystone_version

    def _initialize_keystone(self, version, auth):
        ks_client = self.keystone.initialize_client(version=version, **auth)
        return ks_client

    def _find_regions(self, ks_client):
        if ks_client.version == 'v2.0':
            service_list = ks_client.services.list()
            heat_service_id = None
            for service in service_list:
                if service.type == 'orchestration':
                    heat_service_id = service.id
            endpoints_list = ks_client.endpoints.list()
            region_list = [endpoint.region for endpoint in
                           endpoints_list if endpoint.service_id ==
                           heat_service_id]
        else:
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
    def register_vim(self, context, vim_obj):
        """Validate and set VIM placements."""

        if 'key_type' in vim_obj['auth_cred']:
            vim_obj['auth_cred'].pop(u'key_type')
        if 'secret_uuid' in vim_obj['auth_cred']:
            vim_obj['auth_cred'].pop(u'secret_uuid')

        ks_client = self.authenticate_vim(vim_obj)
        self.discover_placement_attr(vim_obj, ks_client)
        self.encode_vim_auth(context, vim_obj['id'], vim_obj['auth_cred'])
        LOG.debug('VIM registration completed for %s', vim_obj)

    @log.log
    def deregister_vim(self, context, vim_obj):
        """Deregister VIM from NFVO

        Delete VIM keys from file system
        """
        self.delete_vim_auth(context, vim_obj['id'], vim_obj['auth_cred'])

    @log.log
    def delete_vim_auth(self, context, vim_id, auth):
        """Delete vim information

        Delete vim key stored in file system
        """
        LOG.debug('Attempting to delete key for vim id %s', vim_id)

        if auth.get('key_type') == 'barbican_key':
            try:
                keystone_conf = CONF.keystone_authtoken
                secret_uuid = auth['secret_uuid']
                keymgr_api = KEYMGR_API(keystone_conf.auth_url)
                keymgr_api.delete(context, secret_uuid)
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
    def encode_vim_auth(self, context, vim_id, auth):
        """Encode VIM credentials

         Store VIM auth using fernet key encryption
         """
        fernet_key, fernet_obj = self.keystone.create_fernet_key()
        encoded_auth = fernet_obj.encrypt(auth['password'].encode('utf-8'))
        auth['password'] = encoded_auth

        if CONF.vim_keys.use_barbican:
            try:
                keystone_conf = CONF.keystone_authtoken
                keymgr_api = KEYMGR_API(keystone_conf.auth_url)
                secret_uuid = keymgr_api.store(context, fernet_key)

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
                with open(key_file, 'w') as f:
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
        if resource_type in _VALID_RESOURCE_TYPES.keys():
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
        keystone_version = self._validate_auth_url(auth_url, verify=verify)
        auth_cred = self._get_auth_creds(keystone_version, vim_obj)
        auth_plugin = self._get_auth_plugin(keystone_version, **auth_cred)
        sess = session.Session(auth=auth_plugin)
        return client_type(session=sess)

    def create_flow_classifier(self, name, fc, symmetrical=False,
                               auth_attr=None):
        def _translate_ip_protocol(ip_proto):
            if ip_proto == '1':
                return 'icmp'
            elif ip_proto == '6':
                return 'tcp'
            elif ip_proto == '17':
                return 'udp'
            else:
                return None

        if not auth_attr:
            LOG.warning("auth information required for n-sfc driver")
            return None

        if symmetrical:
            LOG.warning("n-sfc driver does not support symmetrical")
            raise NotImplementedError('symmetrical chain not supported')
        LOG.debug('fc passed is %s', fc)
        sfc_classifier_params = {}
        for field in fc:
            if field in FC_MAP:
                sfc_classifier_params[FC_MAP[field]] = fc[field]
            elif field == 'ip_proto':
                protocol = _translate_ip_protocol(str(fc[field]))
                if not protocol:
                    raise ValueError('protocol %s not supported' % fc[field])
                sfc_classifier_params['protocol'] = protocol
            else:
                LOG.warning("flow classifier %s not supported by "
                            "networking-sfc driver", field)

        LOG.debug('sfc_classifier_params is %s', sfc_classifier_params)
        if len(sfc_classifier_params) > 0:
            neutronclient_ = NeutronClient(auth_attr)

            fc_id = neutronclient_.flow_classifier_create(
                sfc_classifier_params)
            return fc_id

        raise ValueError('empty match field for input flow classifier')

    def create_chain(self, name, fc_id, vnfs, symmetrical=False,
                     auth_attr=None):
        if not auth_attr:
            LOG.warning("auth information required for n-sfc driver")
            return None

        if symmetrical:
            LOG.warning("n-sfc driver does not support symmetrical")
            raise NotImplementedError('symmetrical chain not supported')

        neutronclient_ = NeutronClient(auth_attr)
        port_pair_group_list = []
        for vnf in vnfs:
            # TODO(s3wong): once scaling is in place and VNFFG supports it
            # that model needs to be implemented to concatenate all
            # port-pairs into the port-pair-group
            # port pair group could include port-pairs from different VNFs
            port_pair_group = {}
            port_pair_group['name'] = vnf['name'] + '-port-pair-group'
            port_pair_group['description'] = \
                'port pair group for %s' % vnf['name']
            port_pair_group['port_pairs'] = []
            if CONNECTION_POINT not in vnf:
                LOG.warning("Chain creation failed due to missing "
                            "connection point info in VNF "
                            "%(vnfname)s", {'vnfname': vnf['name']})
                return None
            cp_list = vnf[CONNECTION_POINT]
            num_cps = len(cp_list)
            if num_cps != 1 and num_cps != 2:
                LOG.warning("Chain creation failed due to wrong number of "
                            "connection points: expected [1 | 2], got "
                            "%(cps)d", {'cps': num_cps})
                return None
            port_pair = {}
            port_pair['name'] = vnf['name'] + '-connection-points'
            port_pair['description'] = 'port pair for %s' % vnf['name']
            if num_cps == 1:
                port_pair['ingress'] = cp_list[0]
                port_pair['egress'] = cp_list[0]
            else:
                port_pair['ingress'] = cp_list[0]
                port_pair['egress'] = cp_list[1]
            port_pair_id = neutronclient_.port_pair_create(port_pair)
            if not port_pair_id:
                LOG.warning("Chain creation failed due to port pair creation"
                            " failed for vnf %(vnf)s", {'vnf': vnf['name']})
                return None
            port_pair_group['port_pairs'].append(port_pair_id)
            port_pair_group_id = \
                neutronclient_.port_pair_group_create(port_pair_group)
            if not port_pair_group_id:
                LOG.warning("Chain creation failed due to port pair group "
                            "creation failed for vnf "
                            "%(vnf)s", {'vnf': vnf['name']})
                return None
            port_pair_group_list.append(port_pair_group_id)

        # TODO(s3wong): should the chain name be given as a parameter?
        port_chain = {}
        port_chain['name'] = name + '-port-chain'
        port_chain['description'] = 'port-chain for Tacker VNFFG'
        port_chain['port_pair_groups'] = port_pair_group_list
        port_chain['flow_classifiers'] = [fc_id]
        return neutronclient_.port_chain_create(port_chain)

    def update_chain(self, chain_id, fc_ids, vnfs,
                     symmetrical=False, auth_attr=None):
        # TODO(s3wong): chain can be updated either for
        # the list of fc and/or list of port-pair-group
        # since n-sfc driver does NOT track the ppg id
        # it will look it up (or reconstruct) from
        # networking-sfc DB --- but the caveat is that
        # the VNF name MUST be unique
        LOG.warning("n-sfc driver does not support sf chain update")
        raise NotImplementedError('sf chain update not supported')

    def delete_chain(self, chain_id, auth_attr=None):
        if not auth_attr:
            LOG.warning("auth information required for n-sfc driver")
            return None

        neutronclient_ = NeutronClient(auth_attr)
        neutronclient_.port_chain_delete(chain_id)

    def update_flow_classifier(self, fc_id, fc,
                               symmetrical=False, auth_attr=None):
        if not auth_attr:
            LOG.warning("auth information required for n-sfc driver")
            return None

        if symmetrical:
            LOG.warning("n-sfc driver does not support symmetrical")
            raise NotImplementedError('symmetrical chain not supported')

        # for now, the only parameters allowed for flow-classifier-update
        # is 'name' and/or 'description'

        sfc_classifier_params = {}
        sfc_classifier_params['name'] = fc['name']
        sfc_classifier_params['description'] = fc['description']

        LOG.debug('sfc_classifier_params is %s', sfc_classifier_params)

        neutronclient_ = NeutronClient(auth_attr)
        return neutronclient_.flow_classifier_update(fc_id,
                                                     sfc_classifier_params)

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
            keystone.Keystone().initialize_client('2', **auth_dict),
            auth_dict['token']).get_client()

    def prepare_and_create_workflow(self, resource, action,
                                    kwargs, auth_dict=None):
        mistral_client = self.get_mistral_client(auth_dict)
        wg = workflow_generator.WorkflowGenerator(resource, action)
        wg.task(**kwargs)
        if not wg.get_tasks():
            raise nfvo.NoTasksException(resource=resource, action=action)
        definition_yaml = yaml.safe_dump(wg.definition)
        workflow = mistral_client.workflows.create(definition_yaml)
        return {'id': workflow[0].id, 'input': wg.get_input_dict()}

    def execute_workflow(self, workflow, auth_dict=None):
        return self.get_mistral_client(auth_dict)\
            .executions.create(
                workflow_identifier=workflow['id'],
                workflow_input=workflow['input'],
                wf_params={})

    def get_execution(self, execution_id, auth_dict=None):
        return self.get_mistral_client(auth_dict)\
            .executions.get(execution_id)

    def delete_execution(self, execution_id, auth_dict=None):
        return self.get_mistral_client(auth_dict).executions\
            .delete(execution_id)

    def delete_workflow(self, workflow_id, auth_dict=None):
        return self.get_mistral_client(auth_dict)\
            .workflows.delete(workflow_id)


class NeutronClient(object):
    """Neutron Client class for networking-sfc driver"""

    def __init__(self, auth_attr):
        auth_cred = auth_attr.copy()
        verify = 'True' == auth_cred.pop('cert_verify', 'True') or False
        auth = identity.Password(**auth_cred)
        sess = session.Session(auth=auth, verify=verify)
        self.client = neutron_client.Client(session=sess)

    def flow_classifier_create(self, fc_dict):
        LOG.debug("fc_dict passed is {fc_dict}".format(fc_dict=fc_dict))
        fc = self.client.create_flow_classifier({'flow_classifier': fc_dict})
        if fc:
            return fc['flow_classifier']['id']
        else:
            return None

    def flow_classifier_update(self, fc_id, update_fc):
        update_fc_dict = {'flow_classifier': update_fc}
        return self.client.update_flow_classifier(fc_id, update_fc_dict)

    def flow_classifier_delete(self, fc_id):
        try:
            self.client.delete_flow_classifier(fc_id)
        except nc_exceptions.NotFound:
            LOG.warning("fc %s not found", fc_id)
            raise ValueError('fc %s not found' % fc_id)

    def port_pair_create(self, port_pair_dict):
        try:
            pp = self.client.create_port_pair({'port_pair': port_pair_dict})
        except nc_exceptions.BadRequest as e:
            LOG.error("create port pair returns %s", e)
            raise ValueError(str(e))

        if pp and len(pp):
            return pp['port_pair']['id']
        else:
            return None

    def port_pair_delete(self, port_pair_id):
        try:
            self.client.delete_port_pair(port_pair_id)
        except nc_exceptions.NotFound:
            LOG.warning('port pair %s not found', port_pair_id)
            raise ValueError('port pair %s not found' % port_pair_id)

    def port_pair_group_create(self, ppg_dict):
        try:
            ppg = self.client.create_port_pair_group(
                {'port_pair_group': ppg_dict})
        except nc_exceptions.BadRequest as e:
            LOG.warning('create port pair group returns %s', e)
            raise ValueError(str(e))

        if ppg and len(ppg):
            return ppg['port_pair_group']['id']
        else:
            return None

    def port_pair_group_delete(self, ppg_id):
        try:
            self.client.delete_port_pair_group(ppg_id)
        except nc_exceptions.NotFound:
            LOG.warning('port pair group %s not found', ppg_id)
            raise ValueError('port pair group %s not found' % ppg_id)

    def port_chain_create(self, port_chain_dict):
        try:
            pc = self.client.create_port_chain(
                {'port_chain': port_chain_dict})
        except nc_exceptions.BadRequest as e:
            LOG.warning('create port chain returns %s', e)
            raise ValueError(str(e))

        if pc and len(pc):
            return pc['port_chain']['id']
        else:
            return None

    def port_chain_delete(self, port_chain_id):
        try:
            port_chain = self.client.show_port_chain(port_chain_id)
            if port_chain:
                self.client.delete_port_chain(port_chain_id)
                ppg_list = port_chain['port_chain'].get('port_pair_groups')
                if ppg_list and len(ppg_list):
                    for i in xrange(0, len(ppg_list)):
                        ppg = self.client.show_port_pair_group(ppg_list[i])
                        if ppg:
                            self.client.delete_port_pair_group(ppg_list[i])
                            port_pairs = ppg['port_pair_group']['port_pairs']
                            if port_pairs and len(port_pairs):
                                for j in xrange(0, len(port_pairs)):
                                    pp_id = port_pairs[j]
                                    self.client.delete_port_pair(pp_id)
        except nc_exceptions.NotFound:
            LOG.warning('port chain %s not found', port_chain_id)
            raise ValueError('port chain %s not found' % port_chain_id)
