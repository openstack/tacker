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
import threading
import time
import uuid
import yaml

from cryptography import fernet
import eventlet
from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import excutils
from oslo_utils import strutils
from six import iteritems
from tempfile import mkstemp
from toscaparser.tosca_template import ToscaTemplate

from tacker._i18n import _
from tacker.common import driver_manager
from tacker.common import exceptions
from tacker.common import log
from tacker.common import utils
from tacker import context as t_context
from tacker.db.nfvo import nfvo_db
from tacker.db.nfvo import ns_db
from tacker.db.nfvo import vnffg_db
from tacker.extensions import common_services as cs
from tacker.extensions import nfvo
from tacker import manager
from tacker.plugins.common import constants
from tacker.vnfm.tosca import utils as toscautils
from tacker.vnfm import vim_client
from toscaparser import tosca_template


LOG = logging.getLogger(__name__)
CONF = cfg.CONF
MISTRAL_RETRIES = 30
MISTRAL_RETRY_WAIT = 6


def config_opts():
    return [('nfvo_vim', NfvoPlugin.OPTS)]


class NfvoPlugin(nfvo_db.NfvoPluginDb, vnffg_db.VnffgPluginDbMixin,
        ns_db.NSPluginDb):
    """NFVO reference plugin for NFVO extension

    Implements the NFVO extension and defines public facing APIs for VIM
    operations. NFVO internally invokes the appropriate VIM driver in
    backend based on configured VIM types. Plugin also interacts with VNFM
    extension for providing the specified VIM information
    """
    supported_extension_aliases = ['nfvo']
    _lock = threading.RLock()

    OPTS = [
        cfg.ListOpt(
            'vim_drivers', default=['openstack'],
            help=_('VIM driver for launching VNFs')),
        cfg.IntOpt(
            'monitor_interval', default=30,
            help=_('Interval to check for VIM health')),
    ]
    cfg.CONF.register_opts(OPTS, 'nfvo_vim')

    def __init__(self):
        super(NfvoPlugin, self).__init__()
        self._pool = eventlet.GreenPool()
        self._vim_drivers = driver_manager.DriverManager(
            'tacker.nfvo.vim.drivers',
            cfg.CONF.nfvo_vim.vim_drivers)
        self._created_vims = dict()
        self.vim_client = vim_client.VimClient()
        context = t_context.get_admin_context()
        vims = self.get_vims(context)
        for vim in vims:
            self._created_vims[vim["id"]] = vim
        self._monitor_interval = cfg.CONF.nfvo_vim.monitor_interval
        threading.Thread(target=self.__run__).start()

    def __run__(self):
        while(1):
            time.sleep(self._monitor_interval)
            for created_vim in self._created_vims.values():
                self.monitor_vim(created_vim)

    def spawn_n(self, function, *args, **kwargs):
        self._pool.spawn_n(function, *args, **kwargs)

    @log.log
    def create_vim(self, context, vim):
        LOG.debug(_('Create vim called with parameters %s'),
             strutils.mask_password(vim))
        vim_obj = vim['vim']
        name = vim_obj['name']
        if self._get_by_name(context, nfvo_db.Vim, name):
            raise exceptions.DuplicateResourceName(resource='VIM', name=name)
        vim_type = vim_obj['type']
        vim_obj['id'] = str(uuid.uuid4())
        vim_obj['status'] = 'PENDING'
        try:
            self._vim_drivers.invoke(vim_type, 'register_vim', vim_obj=vim_obj)
            res = super(NfvoPlugin, self).create_vim(context, vim_obj)
            vim_obj["status"] = "REGISTERING"
            with self._lock:
                self._created_vims[res["id"]] = res
            self.monitor_vim(vim_obj)
            return res
        except Exception:
            with excutils.save_and_reraise_exception():
                self._vim_drivers.invoke(vim_type, 'delete_vim_auth',
                                         vim_id=vim_obj['id'])

    def _get_vim(self, context, vim_id):
        if not self.is_vim_still_in_use(context, vim_id):
            return self.get_vim(context, vim_id)

    @log.log
    def update_vim(self, context, vim_id, vim):
        vim_obj = self._get_vim(context, vim_id)
        utils.deep_update(vim_obj, vim['vim'])
        vim_type = vim_obj['type']
        try:
            self._vim_drivers.invoke(vim_type, 'register_vim', vim_obj=vim_obj)
            return super(NfvoPlugin, self).update_vim(context, vim_id, vim_obj)
        except Exception:
            with excutils.save_and_reraise_exception():
                self._vim_drivers.invoke(vim_type, 'delete_vim_auth',
                                         vim_id=vim_obj['id'])

    @log.log
    def delete_vim(self, context, vim_id):
        vim_obj = self._get_vim(context, vim_id)
        self._vim_drivers.invoke(vim_obj['type'], 'deregister_vim',
                                 vim_id=vim_id)
        with self._lock:
            self._created_vims.pop(vim_id, None)
        super(NfvoPlugin, self).delete_vim(context, vim_id)

    @log.log
    def monitor_vim(self, vim_obj):
        vim_id = vim_obj["id"]
        auth_url = vim_obj["auth_url"]
        vim_status = self._vim_drivers.invoke(vim_obj['type'],
                                              'vim_status',
                                              auth_url=auth_url)
        current_status = "REACHABLE" if vim_status else "UNREACHABLE"
        if current_status != vim_obj["status"]:
            status = current_status
            with self._lock:
                context = t_context.get_admin_context()
                res = super(NfvoPlugin, self).update_vim_status(context,
                    vim_id, status)
                self._created_vims[vim_id]["status"] = status
                self._cos_db_plg.create_event(
                    context, res_id=res['id'],
                    res_type=constants.RES_TYPE_VIM,
                    res_state=res['status'],
                    evt_type=constants.RES_EVT_MONITOR,
                    tstamp=res[constants.RES_EVT_UPDATED_FLD])

    @log.log
    def validate_tosca(self, template):
        if "tosca_definitions_version" not in template:
            raise nfvo.ToscaParserFailed(
                error_msg_details='tosca_definitions_version missing in '
                                  'template'
            )

        LOG.debug(_('template yaml: %s'), template)

        toscautils.updateimports(template)

        try:
            tosca_template.ToscaTemplate(
                a_file=False, yaml_dict_tpl=template)
        except Exception as e:
            LOG.exception(_("tosca-parser error: %s"), str(e))
            raise nfvo.ToscaParserFailed(error_msg_details=str(e))

    @log.log
    def create_vnffgd(self, context, vnffgd):
        template = vnffgd['vnffgd']

        if 'vnffgd' not in template.get('template'):
            raise nfvo.VnffgdInvalidTemplate(template=template.get('template'))
        else:
            self.validate_tosca(template['template']['vnffgd'])
            temp = template['template']['vnffgd']['topology_template']
            vnffg_name = list(temp['groups'].keys())[0]
            nfp_name = temp['groups'][vnffg_name]['members'][0]
            path = self._get_nfp_attribute(template['template'], nfp_name,
                                           'path')
            prev_element = None
            known_forwarders = set()
            for element in path:
                if element.get('forwarder') in known_forwarders:
                    if prev_element is not None and element.get('forwarder')\
                            != prev_element['forwarder']:
                        raise nfvo.VnffgdDuplicateForwarderException(
                            forwarder=element.get('forwarder')
                        )
                    elif prev_element is not None and element.get(
                            'capability') == prev_element['capability']:
                        raise nfvo.VnffgdDuplicateCPException(
                            cp=element.get('capability')
                        )
                else:
                    known_forwarders.add(element.get('forwarder'))
                prev_element = element
        return super(NfvoPlugin, self).create_vnffgd(context, vnffgd)

    @log.log
    def create_vnffg(self, context, vnffg):
        vnffg_attributes = vnffg['vnffg']['attributes']
        if vnffg_attributes.get('param_values'):
            param = vnffg_attributes['param_values']
            if isinstance(param, dict):
                vnffg_attributes['param_values'] = yaml.safe_dump(param)
            else:
                raise exceptions.InvalidParam()
        vnffg_dict = super(NfvoPlugin, self)._create_vnffg_pre(context, vnffg)
        nfp = super(NfvoPlugin, self).get_nfp(context,
                                              vnffg_dict['forwarding_paths'])
        sfc = super(NfvoPlugin, self).get_sfc(context, nfp['chain_id'])
        match = super(NfvoPlugin, self).get_classifier(context,
                                                       nfp['classifier_id'],
                                                       fields='match')['match']
        # grab the first VNF to check it's VIM type
        # we have already checked that all VNFs are in the same VIM
        vim_obj = self._get_vim_from_vnf(context,
                                         list(vnffg_dict[
                                              'vnf_mapping'].values())[0])
        # TODO(trozet): figure out what auth info we actually need to pass
        # to the driver.  Is it a session, or is full vim obj good enough?
        driver_type = vim_obj['type']
        try:
            fc_id = self._vim_drivers.invoke(driver_type,
                                             'create_flow_classifier',
                                             name=vnffg_dict['name'],
                                             fc=match,
                                             auth_attr=vim_obj['auth_cred'],
                                             symmetrical=sfc['symmetrical'])
            sfc_id = self._vim_drivers.invoke(driver_type,
                                              'create_chain',
                                              name=vnffg_dict['name'],
                                              vnfs=sfc['chain'], fc_id=fc_id,
                                              symmetrical=sfc['symmetrical'],
                                              auth_attr=vim_obj['auth_cred'])
        except Exception:
            with excutils.save_and_reraise_exception():
                self.delete_vnffg(context, vnffg_id=vnffg_dict['id'])
        super(NfvoPlugin, self)._create_vnffg_post(context, sfc_id, fc_id,
                                                   vnffg_dict)
        super(NfvoPlugin, self)._create_vnffg_status(context, vnffg_dict)
        return vnffg_dict

    @log.log
    def update_vnffg(self, context, vnffg_id, vnffg):
        vnffg_dict = super(NfvoPlugin, self)._update_vnffg_pre(context,
                                                               vnffg_id)
        new_vnffg = vnffg['vnffg']
        LOG.debug(_('vnffg update: %s'), vnffg)
        nfp = super(NfvoPlugin, self).get_nfp(context,
                                              vnffg_dict['forwarding_paths'])
        sfc = super(NfvoPlugin, self).get_sfc(context, nfp['chain_id'])

        fc = super(NfvoPlugin, self).get_classifier(context,
                                                    nfp['classifier_id'])
        template_db = self._get_resource(context, vnffg_db.VnffgTemplate,
                                         vnffg_dict['vnffgd_id'])
        vnf_members = self._get_vnffg_property(template_db,
                                               'constituent_vnfs')
        new_vnffg['vnf_mapping'] = super(NfvoPlugin, self)._get_vnf_mapping(
            context, new_vnffg.get('vnf_mapping'), vnf_members)
        template_id = vnffg_dict['vnffgd_id']
        template_db = self._get_resource(context, vnffg_db.VnffgTemplate,
                                         template_id)
        # functional attributes that allow update are vnf_mapping,
        # and symmetrical.  Therefore we need to figure out the new chain if
        # it was updated by new vnf_mapping.  Symmetrical is handled by driver.

        chain = super(NfvoPlugin, self)._create_port_chain(context,
                                                           new_vnffg[
                                                               'vnf_mapping'],
                                                           template_db,
                                                           nfp['name'])
        LOG.debug(_('chain update: %s'), chain)
        sfc['chain'] = chain
        sfc['symmetrical'] = new_vnffg['symmetrical']
        vim_obj = self._get_vim_from_vnf(context,
                                         list(vnffg_dict[
                                              'vnf_mapping'].values())[0])
        driver_type = vim_obj['type']
        try:
            # we don't support updating the match criteria in first iteration
            # so this is essentially a noop.  Good to keep for future use
            # though.
            self._vim_drivers.invoke(driver_type, 'update_flow_classifier',
                                     fc_id=fc['instance_id'], fc=fc['match'],
                                     auth_attr=vim_obj['auth_cred'],
                                     symmetrical=new_vnffg['symmetrical'])
            self._vim_drivers.invoke(driver_type, 'update_chain',
                                     vnfs=sfc['chain'],
                                     fc_ids=[fc['instance_id']],
                                     chain_id=sfc['instance_id'],
                                     auth_attr=vim_obj['auth_cred'],
                                     symmetrical=new_vnffg['symmetrical'])
        except Exception:
            with excutils.save_and_reraise_exception():
                vnffg_dict['status'] = constants.ERROR
                super(NfvoPlugin, self)._update_vnffg_post(context, vnffg_id,
                                                           constants.ERROR)
        super(NfvoPlugin, self)._update_vnffg_post(context, vnffg_id,
                                                   constants.ACTIVE, new_vnffg)
        # update chain
        super(NfvoPlugin, self)._update_sfc_post(context, sfc['id'],
                                                 constants.ACTIVE, sfc)
        # update classifier - this is just updating status until functional
        # updates are supported to classifier
        super(NfvoPlugin, self)._update_classifier_post(context, fc['id'],
                                                        constants.ACTIVE)
        return vnffg_dict

    @log.log
    def delete_vnffg(self, context, vnffg_id):
        vnffg_dict = super(NfvoPlugin, self)._delete_vnffg_pre(context,
                                                               vnffg_id)
        nfp = super(NfvoPlugin, self).get_nfp(context,
                                              vnffg_dict['forwarding_paths'])
        sfc = super(NfvoPlugin, self).get_sfc(context, nfp['chain_id'])

        fc = super(NfvoPlugin, self).get_classifier(context,
                                                    nfp['classifier_id'])
        vim_obj = self._get_vim_from_vnf(context,
                                         list(vnffg_dict[
                                              'vnf_mapping'].values())[0])
        driver_type = vim_obj['type']
        try:
            if sfc['instance_id'] is not None:
                self._vim_drivers.invoke(driver_type, 'delete_chain',
                                         chain_id=sfc['instance_id'],
                                         auth_attr=vim_obj['auth_cred'])
            if fc['instance_id'] is not None:
                self._vim_drivers.invoke(driver_type,
                                         'delete_flow_classifier',
                                         fc_id=fc['instance_id'],
                                         auth_attr=vim_obj['auth_cred'])
        except Exception:
            with excutils.save_and_reraise_exception():
                vnffg_dict['status'] = constants.ERROR
                super(NfvoPlugin, self)._delete_vnffg_post(context, vnffg_id,
                                                           True)
        super(NfvoPlugin, self)._delete_vnffg_post(context, vnffg_id, False)
        return vnffg_dict

    def _get_vim_from_vnf(self, context, vnf_id):
        """Figures out VIM based on a VNF

        :param context: SQL Session Context
        :param vnf_id: VNF ID
        :return: VIM or VIM properties if fields are provided
        """
        vnfm_plugin = manager.TackerManager.get_service_plugins()['VNFM']
        vim_id = vnfm_plugin.get_vnf(context, vnf_id, fields=['vim_id'])
        vim_obj = self.get_vim(context, vim_id['vim_id'], mask_password=False)
        if vim_obj is None:
            raise nfvo.VimFromVnfNotFoundException(vnf_id=vnf_id)
        vim_auth = vim_obj['auth_cred']
        vim_auth['password'] = self._decode_vim_auth(vim_obj['id'],
                                                     vim_auth['password'].
                                                     encode('utf-8'))
        vim_auth['auth_url'] = vim_obj['auth_url']

        return vim_obj

    def _decode_vim_auth(self, vim_id, cred):
        """Decode Vim credentials

        Decrypt VIM cred. using Fernet Key
        """
        vim_key = self._find_vim_key(vim_id)
        f = fernet.Fernet(vim_key)
        if not f:
            LOG.warning(_('Unable to decode VIM auth'))
            raise nfvo.VimNotFoundException('Unable to decode VIM auth key')
        return f.decrypt(cred)

    @staticmethod
    def _find_vim_key(vim_id):
        key_file = os.path.join(CONF.vim_keys.openstack, vim_id)
        LOG.debug(_('Attempting to open key file for vim id %s'), vim_id)
        with open(key_file, 'r') as f:
                return f.read()
        LOG.warning(_('VIM id invalid or key not found for  %s'), vim_id)

    def _vim_resource_name_to_id(self, context, resource, name, vnf_id):
        """Converts a VIM resource name to its ID

        :param resource: resource type to find (network, subnet, etc)
        :param name: name of the resource to find its ID
        :param vnf_id: A VNF instance ID that is part of the chain to which
               the classifier will apply to
        :return: ID of the resource name
        """
        vim_obj = self._get_vim_from_vnf(context, vnf_id)
        driver_type = vim_obj['type']
        return self._vim_drivers.invoke(driver_type,
                                        'get_vim_resource_id',
                                        vim_auth=vim_obj['auth_cred'],
                                        resource_type=resource,
                                        resource_name=name)

    @log.log
    def create_nsd(self, context, nsd):
        nsd_data = nsd['nsd']
        template = nsd_data['attributes'].get('nsd')
        if isinstance(template, dict):
            nsd_data['attributes']['nsd'] = yaml.safe_dump(
                template)
        LOG.debug(_('nsd %s'), nsd_data)

        name = nsd_data['name']
        if self._get_by_name(context, ns_db.NSD, name):
            raise exceptions.DuplicateResourceName(resource='NSD', name=name)

        self._parse_template_input(context, nsd)
        return super(NfvoPlugin, self).create_nsd(
            context, nsd)

    def _parse_template_input(self, context, nsd):
        nsd_dict = nsd['nsd']
        nsd_yaml = nsd_dict['attributes'].get('nsd')
        inner_nsd_dict = yaml.load(nsd_yaml)
        nsd['vnfds'] = dict()
        LOG.debug(_('nsd_dict: %s'), inner_nsd_dict)

        vnfm_plugin = manager.TackerManager.get_service_plugins()['VNFM']
        vnfd_imports = inner_nsd_dict['imports']
        inner_nsd_dict['imports'] = []
        new_files = []
        for vnfd_name in vnfd_imports:
            vnfd = vnfm_plugin.get_vnfd(context, vnfd_name)
            # Copy VNF types and VNF names
            sm_dict = yaml.load(vnfd['attributes']['vnfd'])[
                'topology_template'][
                'substitution_mappings']
            nsd['vnfds'][sm_dict['node_type']] = vnfd['name']
            # Ugly Hack to validate the child templates
            # TODO(tbh): add support in tosca-parser to pass child
            # templates as dict
            fd, temp_path = mkstemp()
            with open(temp_path, 'w') as fp:
                fp.write(vnfd['attributes']['vnfd'])
            os.close(fd)
            new_files.append(temp_path)
            inner_nsd_dict['imports'].append(temp_path)
        # Prepend the tacker_defs.yaml import file with the full
        # path to the file
        toscautils.updateimports(inner_nsd_dict)

        try:
            ToscaTemplate(a_file=False,
                    yaml_dict_tpl=inner_nsd_dict)
        except Exception as e:
            LOG.exception(_("tosca-parser error: %s"), str(e))
            raise nfvo.ToscaParserFailed(error_msg_details=str(e))
        finally:
            for file_path in new_files:
                os.remove(file_path)
            inner_nsd_dict['imports'] = vnfd_imports

        if ('description' not in nsd_dict or
                nsd_dict['description'] == ''):
            nsd_dict['description'] = inner_nsd_dict.get(
                'description', '')
        if (('name' not in nsd_dict or
                not len(nsd_dict['name'])) and
                'metadata' in inner_nsd_dict):
            nsd_dict['name'] = inner_nsd_dict['metadata'].get(
                'template_name', '')

        LOG.debug(_('nsd %s'), nsd)

    def _get_vnfd_id(self, vnfd_name, onboarded_vnfds):
        for vnfd in onboarded_vnfds:
            if vnfd_name == vnfd['name']:
                return vnfd['id']

    @log.log
    def create_ns(self, context, ns):
        """Create NS and corresponding VNFs.

        :param ns ns dict which contains nsd_id and attributes
        This method has 3 steps:
        step-1: substitute all get_input params to its corresponding values
        step-2: Build params dict for substitution mappings case through which
        VNFs will actually substitute their requirements.
        step-3: Create mistral workflow and execute the workflow
        """
        nsd = self.get_nsd(context, ns['ns']['nsd_id'])
        nsd_dict = yaml.load(nsd['attributes']['nsd'])
        vnfm_plugin = manager.TackerManager.get_service_plugins()['VNFM']
        onboarded_vnfds = vnfm_plugin.get_vnfds(context, [])
        region_name = ns.setdefault('placement_attr', {}).get(
            'region_name', None)
        vim_res = self.vim_client.get_vim(context, ns['ns']['vim_id'],
                                          region_name)
        driver_type = vim_res['vim_type']
        if not ns['ns']['vim_id']:
            ns['ns']['vim_id'] = vim_res['vim_id']
        if self._get_by_name(context, ns_db.NS, ns['ns']['name']):
            raise exceptions.DuplicateResourceName(resource='NS',
                name=ns['ns']['name'])

        # Step-1
        param_values = ns['ns']['attributes'].get('param_values', {})
        if 'get_input' in str(nsd_dict):
            self._process_parameterized_input(ns['ns']['attributes'],
                    nsd_dict)
        # Step-2
        vnfds = nsd['vnfds']
        # vnfd_dict is used while generating workflow
        vnfd_dict = dict()
        for node_name, node_val in \
                iteritems(nsd_dict['topology_template']['node_templates']):
            if node_val.get('type') not in vnfds.keys():
                continue
            vnfd_name = vnfds[node_val.get('type')]
            if not vnfd_dict.get(vnfd_name):
                vnfd_dict[vnfd_name] = {
                    'id': self._get_vnfd_id(vnfd_name, onboarded_vnfds),
                    'instances': [node_name]
                }
            else:
                vnfd_dict[vnfd_name]['instances'].append(node_name)
            if not node_val.get('requirements'):
                continue
            if not param_values.get(vnfd_name):
                param_values[vnfd_name] = {}
            param_values[vnfd_name]['substitution_mappings'] = dict()
            req_dict = dict()
            requirements = node_val.get('requirements')
            for requirement in requirements:
                req_name = list(requirement.keys())[0]
                req_val = list(requirement.values())[0]
                res_name = req_val + ns['ns']['nsd_id'][:11]
                req_dict[req_name] = res_name
                if req_val in nsd_dict['topology_template']['node_templates']:
                    param_values[vnfd_name]['substitution_mappings'][
                        res_name] = nsd_dict['topology_template'][
                            'node_templates'][req_val]

            param_values[vnfd_name]['substitution_mappings'][
                'requirements'] = req_dict
        ns['vnfd_details'] = vnfd_dict
        # Step-3
        kwargs = {'ns': ns, 'params': param_values}
        workflow = self._vim_drivers.invoke(driver_type,
                                         'prepare_and_create_workflow',
                                         resource='vnf',
                                         action='create',
                                         vim_auth=vim_res['vim_auth'],
                                         auth_token=context.auth_token,
                                         kwargs=kwargs)
        try:
            mistral_execution = self._vim_drivers.invoke(
                driver_type,
                'execute_workflow',
                workflow=workflow,
                vim_auth=vim_res['vim_auth'],
                auth_token=context.auth_token)
        except Exception as ex:
            LOG.error(_('Error while executing workflow: %s'), ex)
            self._vim_drivers.invoke(driver_type,
                                     'delete_workflow',
                                     workflow_id=workflow['id'],
                                     vim_auth=vim_res['vim_auth'],
                                     auth_token=context.auth_token)
            raise ex
        ns_dict = super(NfvoPlugin, self).create_ns(context, ns)

        def _create_ns_wait(self_obj, ns_id, execution_id):
            exec_state = "RUNNING"
            mistral_retries = MISTRAL_RETRIES
            while exec_state == "RUNNING" and mistral_retries > 0:
                time.sleep(MISTRAL_RETRY_WAIT)
                exec_state = self._vim_drivers.invoke(
                    driver_type,
                    'get_execution',
                    execution_id=execution_id,
                    vim_auth=vim_res['vim_auth'],
                    auth_token=context.auth_token).state
                LOG.debug(_('status: %s'), exec_state)
                if exec_state == 'SUCCESS' or exec_state == 'ERROR':
                    break
                mistral_retries = mistral_retries - 1
            error_reason = None
            if mistral_retries == 0 and exec_state == 'RUNNING':
                error_reason = _("NS creation is not completed within"
                               " {wait} seconds as creation of mistral"
                               " exection {mistral} is not completed").format(
                                   wait=MISTRAL_RETRIES * MISTRAL_RETRY_WAIT,
                                   mistral=execution_id)
            exec_obj = self._vim_drivers.invoke(driver_type,
                                                'get_execution',
                                                execution_id=execution_id,
                                                vim_auth=vim_res['vim_auth'],
                                                auth_token=context.auth_token)
            self._vim_drivers.invoke(driver_type,
                                     'delete_execution',
                                     execution_id=execution_id,
                                     vim_auth=vim_res['vim_auth'],
                                     auth_token=context.auth_token)
            self._vim_drivers.invoke(driver_type,
                                     'delete_workflow',
                                     workflow_id=workflow['id'],
                                     vim_auth=vim_res['vim_auth'],
                                     auth_token=context.auth_token)
            super(NfvoPlugin, self).create_ns_post(context, ns_id, exec_obj,
                    vnfd_dict, error_reason)

        self.spawn_n(_create_ns_wait, self, ns_dict['id'],
                mistral_execution.id)
        return ns_dict

    @log.log
    def _update_params(self, original, paramvalues):
        for key, value in iteritems(original):
            if not isinstance(value, dict) or 'get_input' not in str(value):
                pass
            elif isinstance(value, dict):
                if 'get_input' in value:
                    if value['get_input'] in paramvalues:
                        original[key] = paramvalues[value['get_input']]
                    else:
                        LOG.debug('Key missing Value: %s', key)
                        raise cs.InputValuesMissing(key=key)
                else:
                    self._update_params(value, paramvalues)

    @log.log
    def _process_parameterized_input(self, attrs, nsd_dict):
        param_vattrs_dict = attrs.pop('param_values', None)
        if param_vattrs_dict:
            for node in \
                    nsd_dict['topology_template']['node_templates'].values():
                if 'get_input' in str(node):
                    self._update_params(node, param_vattrs_dict['nsd'])
        else:
            raise cs.ParamYAMLInputMissing()

    @log.log
    def delete_ns(self, context, ns_id):
        ns = super(NfvoPlugin, self).get_ns(context, ns_id)
        vim_res = self.vim_client.get_vim(context, ns['vim_id'])
        driver_type = vim_res['vim_type']
        workflow = self._vim_drivers.invoke(driver_type,
                                            'prepare_and_create_workflow',
                                            resource='vnf',
                                            action='delete',
                                            vim_auth=vim_res['vim_auth'],
                                            auth_token=context.auth_token,
                                            kwargs={'ns': ns})
        try:
            mistral_execution = self._vim_drivers.invoke(
                driver_type,
                'execute_workflow',
                workflow=workflow,
                vim_auth=vim_res['vim_auth'],
                auth_token=context.auth_token)
        except Exception as ex:
            LOG.error(_('Error while executing workflow: %s'), ex)
            self._vim_drivers.invoke(driver_type,
                                     'delete_workflow',
                                     workflow_id=workflow['id'],
                                     vim_auth=vim_res['vim_auth'],
                                     auth_token=context.auth_token)

            raise ex
        super(NfvoPlugin, self).delete_ns(context, ns_id)

        def _delete_ns_wait(ns_id, execution_id):
            exec_state = "RUNNING"
            mistral_retries = MISTRAL_RETRIES
            while exec_state == "RUNNING" and mistral_retries > 0:
                time.sleep(MISTRAL_RETRY_WAIT)
                exec_state = self._vim_drivers.invoke(
                    driver_type,
                    'get_execution',
                    execution_id=execution_id,
                    vim_auth=vim_res['vim_auth'],
                    auth_token=context.auth_token).state
                LOG.debug(_('status: %s'), exec_state)
                if exec_state == 'SUCCESS' or exec_state == 'ERROR':
                    break
                mistral_retries -= 1
            error_reason = None
            if mistral_retries == 0 and exec_state == 'RUNNING':
                error_reason = _("NS deletion is not completed within"
                               " {wait} seconds as deletion of mistral"
                               " exection {mistral} is not completed").format(
                                   wait=MISTRAL_RETRIES * MISTRAL_RETRY_WAIT,
                                   mistral=execution_id)
            exec_obj = self._vim_drivers.invoke(driver_type,
                                                'get_execution',
                                                execution_id=execution_id,
                                                vim_auth=vim_res['vim_auth'],
                                                auth_token=context.auth_token)
            self._vim_drivers.invoke(driver_type,
                                     'delete_execution',
                                     execution_id=execution_id,
                                     vim_auth=vim_res['vim_auth'],
                                     auth_token=context.auth_token)
            self._vim_drivers.invoke(driver_type,
                                     'delete_workflow',
                                     workflow_id=workflow['id'],
                                     vim_auth=vim_res['vim_auth'],
                                     auth_token=context.auth_token)
            super(NfvoPlugin, self).delete_ns_post(context, ns_id, exec_obj,
                    error_reason)

        self.spawn_n(_delete_ns_wait, ns['id'], mistral_execution.id)
        return ns['id']
