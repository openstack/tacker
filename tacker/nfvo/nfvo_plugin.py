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

import threading
import time
import uuid

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import excutils
from oslo_utils import strutils

from tacker._i18n import _
from tacker.common import driver_manager
from tacker.common import log
from tacker.common import utils
from tacker import context as t_context
from tacker.db.nfvo import nfvo_db
from tacker.db.nfvo import vnffg_db
from tacker.extensions import nfvo
from tacker import manager
from tacker.plugins.common import constants
from tacker.vnfm.tosca import utils as toscautils
from toscaparser import tosca_template

LOG = logging.getLogger(__name__)


def config_opts():
    return [('nfvo', NfvoPlugin.OPTS)]


class NfvoPlugin(nfvo_db.NfvoPluginDb, vnffg_db.VnffgPluginDbMixin):
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
        self._vim_drivers = driver_manager.DriverManager(
            'tacker.nfvo.vim.drivers',
            cfg.CONF.nfvo_vim.vim_drivers)
        self._created_vims = dict()
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

    @log.log
    def create_vim(self, context, vim):
        LOG.debug(_('Create vim called with parameters %s'),
             strutils.mask_password(vim))
        vim_obj = vim['vim']
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
                super(NfvoPlugin, self).update_vim_status(
                    t_context.get_admin_context(),
                    vim_id, status)
                self._created_vims[vim_id]["status"] = status

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
            vnffg_name = temp['groups'].keys()[0]
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
        vnffg_dict = super(NfvoPlugin, self)._create_vnffg_pre(context, vnffg)
        nfp = super(NfvoPlugin, self).get_nfp(context,
                                              vnffg_dict['forwarding_paths'])
        sfc = super(NfvoPlugin, self).get_sfc(context, nfp['chain_id'])
        match = super(NfvoPlugin, self).get_classifier(context,
                                                       nfp['classifier_id'],
                                                       fields='match')
        # grab the first VNF to check it's VIM type
        # we have already checked that all VNFs are in the same VIM
        vim_auth = self._get_vim_from_vnf(context,
                                          vnffg_dict['vnf_mapping'].values()[0]
                                          )
        # TODO(trozet): figure out what auth info we actually need to pass
        # to the driver.  Is it a session, or is full vim obj good enough?
        driver_type = vim_auth['type']
        try:
            fc_id = self._vim_drivers.invoke(driver_type,
                                             'create_flow_classifier',
                                             fc=match, auth_attr=vim_auth,
                                             symmetrical=sfc['symmetrical'])
            sfc_id = self._vim_drivers.invoke(driver_type, 'create_chain',
                                              vnfs=sfc['chain'], fc_id=fc_id,
                                              symmetrical=sfc['symmetrical'],
                                              auth_attr=vim_auth)
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
        vim_auth = self._get_vim_from_vnf(context,
                                          vnffg_dict['vnf_mapping'].values()[0]
                                          )
        driver_type = vim_auth['type']
        try:
            # we don't support updating the match criteria in first iteration
            # so this is essentially a noop.  Good to keep for future use
            # though.
            self._vim_drivers.invoke(driver_type, 'update_flow_classifier',
                                     fc_id=fc['instance_id'], fc=fc['match'],
                                     auth_attr=vim_auth,
                                     symmetrical=new_vnffg['symmetrical'])
            self._vim_drivers.invoke(driver_type, 'update_chain',
                                     vnfs=sfc['chain'],
                                     fc_ids=[fc['instance_id']],
                                     chain_id=sfc['instance_id'],
                                     auth_attr=vim_auth,
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
        vim_auth = self._get_vim_from_vnf(context,
                                          vnffg_dict['vnf_mapping'].values()[0]
                                          )
        driver_type = vim_auth['type']
        try:
            if sfc['instance_id'] is not None:
                self._vim_drivers.invoke(driver_type, 'delete_chain',
                                         chain_id=sfc['instance_id'],
                                         auth_attr=vim_auth)
            if fc['instance_id'] is not None:
                self._vim_drivers.invoke(driver_type,
                                         'delete_flow_classifier',
                                         fc_id=fc['instance_id'],
                                         auth_attr=vim_auth)
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
        vim_obj = self.get_vim(context, vim_id['vim_id'])
        if vim_obj is None:
            raise nfvo.VimFromVnfNotFoundException(vnf_id=vnf_id)
        return vim_obj

    def _vim_resource_name_to_id(self, context, resource, name, vnf_id):
        """Converts a VIM resource name to its ID

        :param resource: resource type to find (network, subnet, etc)
        :param name: name of the resource to find its ID
        :param vnf_id: A VNF instance ID that is part of the chain to which
               the classifier will apply to
        :return: ID of the resource name
        """
        vim_auth = self._get_vim_from_vnf(context, vnf_id)
        driver_type = vim_auth['type']
        return self._vim_drivers.invoke(driver_type,
                                        'get_vim_resource_id',
                                        vim_auth=vim_auth,
                                        resource_type=resource,
                                        resource_name=name)
