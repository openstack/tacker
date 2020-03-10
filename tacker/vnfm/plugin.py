# Copyright 2013, 2014 Intel Corporation.
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

import inspect
import six
import yaml

import eventlet
from oslo_config import cfg
from oslo_log import log as logging
from oslo_serialization import jsonutils
from oslo_utils import excutils
from oslo_utils import uuidutils
from toscaparser.tosca_template import ToscaTemplate

from tacker._i18n import _
from tacker.api.v1 import attributes
from tacker.common import driver_manager
from tacker.common import exceptions
from tacker.common import utils
from tacker import context as t_context
from tacker.db.vnfm import vnfm_db
from tacker.extensions import vnfm
from tacker.plugins.common import constants
from tacker.plugins import fenix
from tacker.tosca import utils as toscautils
from tacker.vnfm.mgmt_drivers import constants as mgmt_constants
from tacker.vnfm import monitor
from tacker.vnfm import vim_client


LOG = logging.getLogger(__name__)
CONF = cfg.CONF


def config_opts():
    return [('tacker', VNFMMgmtMixin.OPTS),
            ('tacker', VNFMPlugin.OPTS_INFRA_DRIVER),
            ('tacker', VNFMPlugin.OPTS_POLICY_ACTION)]


class VNFMMgmtMixin(object):
    OPTS = [
        cfg.ListOpt(
            'mgmt_driver', default=['noop', 'openwrt'],
            help=_('MGMT driver to communicate with '
                   'Hosting VNF/logical service '
                   'instance tacker plugin will use')),
        cfg.IntOpt('boot_wait', default=30,
            help=_('Time interval to wait for VM to boot'))
    ]
    cfg.CONF.register_opts(OPTS, 'tacker')

    def __init__(self):
        super(VNFMMgmtMixin, self).__init__()
        self._mgmt_manager = driver_manager.DriverManager(
            'tacker.tacker.mgmt.drivers', cfg.CONF.tacker.mgmt_driver)

    def _invoke(self, vnf_dict, **kwargs):
        method = inspect.stack()[1][3]
        return self._mgmt_manager.invoke(
            self._mgmt_driver_name(vnf_dict), method, **kwargs)

    def mgmt_create_pre(self, context, vnf_dict):
        return self._invoke(
            vnf_dict, plugin=self, context=context, vnf=vnf_dict)

    def mgmt_create_post(self, context, vnf_dict):
        return self._invoke(
            vnf_dict, plugin=self, context=context, vnf=vnf_dict)

    def mgmt_update_pre(self, context, vnf_dict):
        return self._invoke(
            vnf_dict, plugin=self, context=context, vnf=vnf_dict)

    def mgmt_update_post(self, context, vnf_dict):
        return self._invoke(
            vnf_dict, plugin=self, context=context, vnf=vnf_dict)

    def mgmt_delete_pre(self, context, vnf_dict):
        return self._invoke(
            vnf_dict, plugin=self, context=context, vnf=vnf_dict)

    def mgmt_delete_post(self, context, vnf_dict):
        return self._invoke(
            vnf_dict, plugin=self, context=context, vnf=vnf_dict)

    def mgmt_get_config(self, context, vnf_dict):
        return self._invoke(
            vnf_dict, plugin=self, context=context, vnf=vnf_dict)

    def mgmt_ip_address(self, context, vnf_dict):
        return self._invoke(
            vnf_dict, plugin=self, context=context, vnf=vnf_dict)

    def mgmt_call(self, context, vnf_dict, kwargs):
        return self._invoke(
            vnf_dict, plugin=self, context=context, vnf=vnf_dict,
            kwargs=kwargs)


class VNFMPlugin(vnfm_db.VNFMPluginDb, VNFMMgmtMixin):
    """VNFMPlugin which supports VNFM framework.

    Plugin which supports Tacker framework
    """

    OPTS_INFRA_DRIVER = [
        cfg.ListOpt(
            'infra_driver', default=['noop', 'openstack', 'kubernetes'],
            help=_('Hosting vnf drivers tacker plugin will use')),
    ]
    cfg.CONF.register_opts(OPTS_INFRA_DRIVER, 'tacker')

    OPTS_POLICY_ACTION = [
        cfg.ListOpt(
            'policy_action', default=['autoscaling', 'respawn',
                                      'vdu_autoheal', 'log', 'log_and_kill'],
            help=_('Hosting vnf drivers tacker plugin will use')),
    ]
    cfg.CONF.register_opts(OPTS_POLICY_ACTION, 'tacker')

    supported_extension_aliases = ['vnfm']

    def __init__(self):
        super(VNFMPlugin, self).__init__()
        self._pool = eventlet.GreenPool()
        self.boot_wait = cfg.CONF.tacker.boot_wait
        self.vim_client = vim_client.VimClient()
        self._vnf_manager = driver_manager.DriverManager(
            'tacker.tacker.vnfm.drivers',
            cfg.CONF.tacker.infra_driver)
        self._vnf_action = driver_manager.DriverManager(
            'tacker.tacker.policy.actions',
            cfg.CONF.tacker.policy_action)
        self._vnf_monitor = monitor.VNFMonitor(self.boot_wait)
        self._vnf_alarm_monitor = monitor.VNFAlarmMonitor()
        self._vnf_reservation_monitor = monitor.VNFReservationAlarmMonitor()
        self._vnf_maintenance_monitor = monitor.VNFMaintenanceAlarmMonitor()
        self._vnf_app_monitor = monitor.VNFAppMonitor()
        self._vnf_maintenance_plugin = fenix.FenixPlugin()
        self._init_monitoring()

    def _init_monitoring(self):
        context = t_context.get_admin_context()
        vnfs = self.get_vnfs(context)
        for vnf in vnfs:
            # Add tenant_id in context object as it is required
            # to get VIM in monitoring.
            context.tenant_id = vnf['tenant_id']
            self.add_vnf_to_monitor(context, vnf)

    def spawn_n(self, function, *args, **kwargs):
        self._pool.spawn_n(function, *args, **kwargs)

    def create_vnfd(self, context, vnfd):
        vnfd_data = vnfd['vnfd']
        template = vnfd_data['attributes'].get('vnfd')
        if isinstance(template, dict):
            # TODO(sripriya) remove this yaml dump once db supports storing
            # json format of yaml files in a separate column instead of
            # key value string pairs in vnf attributes table
            vnfd_data['attributes']['vnfd'] = yaml.safe_dump(
                template)
        else:
            raise vnfm.InvalidAPIAttributeType(atype=type(template))
        if "tosca_definitions_version" not in template:
            raise exceptions.Invalid('Not a valid template: '
                                     'tosca_definitions_version is missing.')

        LOG.debug('vnfd %s', vnfd_data)

        service_types = vnfd_data.get('service_types')
        if not attributes.is_attr_set(service_types):
            LOG.debug('service type must be specified')
            raise vnfm.ServiceTypesNotSpecified()
        for service_type in service_types:
            # TODO(yamahata):
            # framework doesn't know what services are valid for now.
            # so doesn't check it here yet.
            pass
        if 'template_source' in vnfd_data:
            template_source = vnfd_data.get('template_source')
        else:
            template_source = 'onboarded'
        vnfd['vnfd']['template_source'] = template_source

        self._parse_template_input(vnfd)
        return super(VNFMPlugin, self).create_vnfd(
            context, vnfd)

    def _parse_template_input(self, vnfd):
        vnfd_dict = vnfd['vnfd']
        vnfd_yaml = vnfd_dict['attributes'].get('vnfd')
        if vnfd_yaml is None:
            return

        inner_vnfd_dict = yaml.safe_load(vnfd_yaml)
        LOG.debug('vnfd_dict: %s', inner_vnfd_dict)

        # Prepend the tacker_defs.yaml import file with the full
        # path to the file
        toscautils.updateimports(inner_vnfd_dict)

        try:
            tosca = ToscaTemplate(a_file=False,
                                  yaml_dict_tpl=inner_vnfd_dict)
        except Exception as e:
            LOG.exception("tosca-parser error: %s", str(e))
            raise vnfm.ToscaParserFailed(error_msg_details=str(e))

        if ('description' not in vnfd_dict or
                vnfd_dict['description'] == ''):
            vnfd_dict['description'] = inner_vnfd_dict.get(
                'description', '')
        if (('name' not in vnfd_dict or
                not len(vnfd_dict['name'])) and
                'metadata' in inner_vnfd_dict):
            vnfd_dict['name'] = inner_vnfd_dict['metadata'].get(
                'template_name', '')

        vnfd_dict['mgmt_driver'] = toscautils.get_mgmt_driver(
            tosca)

        if vnfd_dict['mgmt_driver'] not in cfg.CONF.tacker.mgmt_driver:
            LOG.error("Invalid mgmt_driver in TOSCA template")
            raise vnfm.InvalidMgmtDriver(
                mgmt_driver_name=vnfd_dict['mgmt_driver'])

        LOG.debug('vnfd %s', vnfd)

    def add_vnf_to_monitor(self, context, vnf_dict):
        dev_attrs = vnf_dict['attributes']
        mgmt_ip_address = vnf_dict['mgmt_ip_address']
        if 'monitoring_policy' in dev_attrs and mgmt_ip_address:
            def action_cb(action, **kwargs):
                LOG.debug('policy action: %s', action)
                self._vnf_action.invoke(
                    action, 'execute_action', plugin=self, context=context,
                    vnf_dict=hosting_vnf['vnf'], args=kwargs)

            hosting_vnf = self._vnf_monitor.to_hosting_vnf(
                vnf_dict, action_cb)
            LOG.debug('hosting_vnf: %s', hosting_vnf)
            self._vnf_monitor.add_hosting_vnf(hosting_vnf)

    def add_alarm_url_to_vnf(self, context, vnf_dict):
        vnfd_yaml = vnf_dict['vnfd']['attributes'].get('vnfd', '')
        vnfd_dict = yaml.safe_load(vnfd_yaml)
        if not (vnfd_dict and vnfd_dict.get('tosca_definitions_version')):
            return
        try:
            toscautils.updateimports(vnfd_dict)
            tosca_vnfd = ToscaTemplate(a_file=False,
                                  yaml_dict_tpl=vnfd_dict)
        except Exception as e:
            LOG.exception("tosca-parser error: %s", str(e))
            raise vnfm.ToscaParserFailed(error_msg_details=str(e))
        polices = vnfd_dict['topology_template'].get('policies', [])
        for policy_dict in polices:
            name, policy = list(policy_dict.items())[0]
            if policy['type'] in constants.POLICY_ALARMING:
                alarm_url =\
                    self._vnf_alarm_monitor.update_vnf_with_alarm(
                        self, context, vnf_dict, policy)
                vnf_dict['attributes']['alarming_policy'] = vnf_dict['id']
                vnf_dict['attributes'].update(alarm_url)
            elif policy['type'] in constants.POLICY_RESERVATION:
                alarm_url = \
                    self._vnf_reservation_monitor.update_vnf_with_reservation(
                        self, context, vnf_dict, policy)
                vnf_dict['attributes']['reservation_policy'] = vnf_dict['id']
                vnf_dict['attributes'].update(alarm_url)
        maintenance_vdus = toscautils.find_maintenance_vdus(tosca_vnfd)
        maintenance = \
            self._vnf_maintenance_monitor.update_vnf_with_maintenance(
                vnf_dict, maintenance_vdus)
        vnf_dict['attributes'].update({
            'maintenance': jsonutils.dumps(maintenance['vdus'])})
        vnf_dict['attributes']['maintenance_url'] = maintenance['url']

    def add_vnf_to_appmonitor(self, context, vnf_dict):
        appmonitor = self._vnf_app_monitor.create_app_dict(context, vnf_dict)
        self._vnf_app_monitor.add_to_appmonitor(appmonitor, vnf_dict)

    def config_vnf(self, context, vnf_dict):
        config = vnf_dict['attributes'].get('config')
        if not config:
            self._vnf_maintenance_plugin.create_vnf_constraints(self, context,
                                                                vnf_dict)
            return
        if isinstance(config, str):
            # TODO(dkushwaha) remove this load once db supports storing
            # json format of yaml files in a separate column instead of
            #  key value string pairs in vnf attributes table.
            config = yaml.safe_load(config)

        eventlet.sleep(self.boot_wait)      # wait for vm to be ready
        vnf_id = vnf_dict['id']
        update = {
            'vnf': {
                'id': vnf_id,
                'attributes': {'config': config},
            }
        }
        self.update_vnf(context, vnf_id, update)

    def _get_infra_driver(self, context, vnf_info):
        vim_res = self.get_vim(context, vnf_info)
        return vim_res['vim_type'], vim_res['vim_auth']

    def _create_vnf_wait(self, context, vnf_dict, auth_attr, driver_name):
        vnf_id = vnf_dict['id']
        instance_id = self._instance_id(vnf_dict)
        create_failed = False

        try:
            self._vnf_manager.invoke(
                driver_name, 'create_wait', plugin=self, context=context,
                vnf_dict=vnf_dict, vnf_id=instance_id,
                auth_attr=auth_attr)
        except vnfm.VNFCreateWaitFailed as e:
            LOG.error("VNF Create failed for vnf_id %s", vnf_id)
            create_failed = True
            vnf_dict['status'] = constants.ERROR
            self.set_vnf_error_status_reason(context, vnf_id,
                                             six.text_type(e))

        if instance_id is None or create_failed:
            mgmt_ip_address = None
        else:
            # mgmt_ip_address = self.mgmt_ip_address(context, vnf_dict)
            # FIXME(yamahata):
            mgmt_ip_address = vnf_dict['mgmt_ip_address']

        self._create_vnf_post(
            context, vnf_id, instance_id, mgmt_ip_address, vnf_dict)
        self.mgmt_create_post(context, vnf_dict)

        if instance_id is None or create_failed:
            return

        vnf_dict['mgmt_ip_address'] = mgmt_ip_address

        kwargs = {
            mgmt_constants.KEY_ACTION: mgmt_constants.ACTION_CREATE_VNF,
            mgmt_constants.KEY_KWARGS: {'vnf': vnf_dict},
        }
        new_status = constants.ACTIVE
        try:
            self.mgmt_call(context, vnf_dict, kwargs)
        except exceptions.MgmtDriverException:
            LOG.error('VNF configuration failed')
            new_status = constants.ERROR
            self.set_vnf_error_status_reason(context, vnf_id,
                                             'Unable to configure VDU')
        vnf_dict['status'] = new_status
        self._create_vnf_status(context, vnf_id, new_status)

    def get_vim(self, context, vnf):
        region_name = vnf.setdefault('placement_attr', {}).get(
            'region_name', None)
        vim_res = self.vim_client.get_vim(context, vnf['vim_id'],
                                          region_name)
        vnf['placement_attr']['vim_name'] = vim_res['vim_name']
        vnf['vim_id'] = vim_res['vim_id']
        return vim_res

    def _create_vnf(self, context, vnf, vim_auth, driver_name):
        vnf_dict = self._create_vnf_pre(
            context, vnf) if not vnf.get('id') else vnf
        vnf_id = vnf_dict['id']
        LOG.debug('vnf_dict %s', vnf_dict)
        if driver_name == 'openstack':
            self.mgmt_create_pre(context, vnf_dict)
            self.add_alarm_url_to_vnf(context, vnf_dict)
        vnf_dict['attributes']['maintenance_group'] = uuidutils.generate_uuid()

        try:
            instance_id = self._vnf_manager.invoke(
                driver_name, 'create', plugin=self,
                context=context, vnf=vnf_dict, auth_attr=vim_auth)
        except Exception:
            LOG.debug('Fail to create vnf %s in infra_driver, '
                      'so delete this vnf',
                      vnf_dict['id'])
            with excutils.save_and_reraise_exception():
                self._delete_vnf(context, vnf_id, force_delete=True)

        vnf_dict['instance_id'] = instance_id
        return vnf_dict

    def create_vnf(self, context, vnf):
        vnf_info = vnf['vnf']
        name = vnf_info['name']

        # if vnfd_template specified, create vnfd from template
        # create template dictionary structure same as needed in create_vnfd()
        if vnf_info.get('vnfd_template'):
            vnfd_name = utils.generate_resource_name(name, 'inline')
            vnfd = {'vnfd': {'attributes': {'vnfd': vnf_info['vnfd_template']},
                             'name': vnfd_name,
                             'template_source': 'inline',
                             'service_types': [{'service_type': 'vnfd'}]}}
            vnf_info['vnfd_id'] = self.create_vnfd(context, vnfd).get('id')

        infra_driver, vim_auth = self._get_infra_driver(context, vnf_info)
        if infra_driver not in self._vnf_manager:
            LOG.debug('unknown vim driver '
                      '%(infra_driver)s in %(drivers)s',
                      {'infra_driver': infra_driver,
                       'drivers': cfg.CONF.tacker.infra_driver})
            raise vnfm.InvalidInfraDriver(vim_name=infra_driver)

        vnf_attributes = vnf_info['attributes']
        if vnf_attributes.get('param_values'):
            param = vnf_attributes['param_values']
            if isinstance(param, dict):
                # TODO(sripriya) remove this yaml dump once db supports storing
                # json format of yaml files in a separate column instead of
                #  key value string pairs in vnf attributes table
                vnf_attributes['param_values'] = yaml.safe_dump(param)
            else:
                raise vnfm.InvalidAPIAttributeType(atype=type(param))
        if vnf_attributes.get('config'):
            config = vnf_attributes['config']
            if isinstance(config, dict):
                # TODO(sripriya) remove this yaml dump once db supports storing
                # json format of yaml files in a separate column instead of
                #  key value string pairs in vnf attributes table
                vnf_attributes['config'] = yaml.safe_dump(config)
            else:
                raise vnfm.InvalidAPIAttributeType(atype=type(config))

        vnf_dict = self._create_vnf(context, vnf_info, vim_auth, infra_driver)

        def create_vnf_wait():
            self._create_vnf_wait(context, vnf_dict, vim_auth, infra_driver)

            if 'app_monitoring_policy' in vnf_dict['attributes']:
                self.add_vnf_to_appmonitor(context, vnf_dict)
            if vnf_dict['status'] is not constants.ERROR:
                self.add_vnf_to_monitor(context, vnf_dict)

            self.config_vnf(context, vnf_dict)
        self.spawn_n(create_vnf_wait)
        return vnf_dict

    # not for wsgi, but for service to create hosting vnf
    # the vnf is NOT added to monitor.
    def create_vnf_sync(self, context, vnf):
        infra_driver, vim_auth = self._get_infra_driver(context, vnf)
        vnf_dict = self._create_vnf(context, vnf, vim_auth, infra_driver)
        self._create_vnf_wait(context, vnf_dict, vim_auth, infra_driver)
        return vnf_dict

    def _heal_vnf_wait(self, context, vnf_dict, vim_auth, driver_name):
        kwargs = {
            mgmt_constants.KEY_ACTION: mgmt_constants.ACTION_HEAL_VNF,
            mgmt_constants.KEY_KWARGS: {'vnf': vnf_dict},
        }
        new_status = constants.ACTIVE
        placement_attr = vnf_dict['placement_attr']
        region_name = placement_attr.get('region_name')

        try:
            self._vnf_manager.invoke(
                driver_name, 'heal_wait', plugin=self,
                context=context, vnf_dict=vnf_dict, auth_attr=vim_auth,
                region_name=region_name)
            self.mgmt_call(context, vnf_dict, kwargs)

        except vnfm.VNFHealWaitFailed as e:
            with excutils.save_and_reraise_exception():
                new_status = constants.ERROR
                self._vnf_monitor.delete_hosting_vnf(vnf_dict['id'])
                self._vnf_maintenance_plugin.post(context, vnf_dict)
                self.set_vnf_error_status_reason(context, vnf_dict['id'],
                                                 six.text_type(e))
        except exceptions.MgmtDriverException as e:
            LOG.error('VNF configuration failed')
            new_status = constants.ERROR
            self._vnf_monitor.delete_hosting_vnf(vnf_dict['id'])
            self._vnf_maintenance_plugin.post(context, vnf_dict)
            self.set_vnf_error_status_reason(context, vnf_dict['id'],
                                             six.text_type(e))

        del vnf_dict['heal_stack_id']
        vnf_dict['status'] = new_status
        self.mgmt_update_post(context, vnf_dict)

        # Update vnf status to 'ACTIVE' so that monitoring can be resumed.
        evt_details = ("Ends the heal vnf request for VNF '%s'" %
                       vnf_dict['id'])
        self._vnf_monitor.update_hosting_vnf(vnf_dict, evt_details)
        self._vnf_maintenance_plugin.update_vnf_instances(self, context,
                                                          vnf_dict)
        self._vnf_maintenance_plugin.post(context, vnf_dict)
        # _update_vnf_post() method updates vnf_status and mgmt_ip_address
        self._update_vnf_post(context, vnf_dict['id'],
                              new_status, vnf_dict,
                              constants.PENDING_HEAL,
                              constants.RES_EVT_HEAL)

    def _update_vnf_wait(self, context, vnf_dict, vim_auth, driver_name):
        kwargs = {
            mgmt_constants.KEY_ACTION: mgmt_constants.ACTION_UPDATE_VNF,
            mgmt_constants.KEY_KWARGS: {'vnf': vnf_dict},
        }
        new_status = constants.ACTIVE
        placement_attr = vnf_dict['placement_attr']
        region_name = placement_attr.get('region_name')

        try:
            self._vnf_manager.invoke(
                driver_name, 'update_wait', plugin=self,
                context=context, vnf_dict=vnf_dict, auth_attr=vim_auth,
                region_name=region_name)

            self.mgmt_call(context, vnf_dict, kwargs)
        except vnfm.VNFUpdateWaitFailed as e:
            with excutils.save_and_reraise_exception():
                new_status = constants.ERROR
                self._vnf_monitor.delete_hosting_vnf(vnf_dict['id'])
                self.set_vnf_error_status_reason(context, vnf_dict['id'],
                                                 six.text_type(e))
        except exceptions.MgmtDriverException as e:
            LOG.error('VNF configuration failed')
            new_status = constants.ERROR
            self._vnf_monitor.delete_hosting_vnf(vnf_dict['id'])
            self.set_vnf_error_status_reason(context, vnf_dict['id'],
                                             six.text_type(e))
        vnf_dict['status'] = new_status
        self.mgmt_update_post(context, vnf_dict)
        self._update_vnf_post(context, vnf_dict['id'], new_status,
                              vnf_dict, constants.PENDING_UPDATE,
                              constants.RES_EVT_UPDATE)
        self._vnf_maintenance_plugin.create_vnf_constraints(self, context,
                                                            vnf_dict)

    def update_vnf(self, context, vnf_id, vnf):
        vnf_attributes = vnf['vnf']['attributes']
        if vnf_attributes.get('config'):
            config = vnf_attributes['config']
            if isinstance(config, dict):
                # TODO(sripriya) remove this yaml dump once db supports storing
                # json format of yaml files in a separate column instead of
                #  key value string pairs in vnf attributes table
                vnf_attributes['config'] = yaml.safe_dump(config)
            else:
                raise vnfm.InvalidAPIAttributeType(atype=type(config))

        if vnf_attributes.get('param_values'):
            param = vnf_attributes['param_values']
            if isinstance(param, dict):
                # TODO(sripriya) remove this yaml dump once db supports storing
                # json format of yaml files in a separate column instead of
                #  key value string pairs in vnf attributes table
                vnf_attributes['param_values'] = yaml.safe_dump(param)
            else:
                raise vnfm.InvalidAPIAttributeType(atype=type(param))

        vnf_dict = self._update_vnf_pre(context, vnf_id,
                                        constants.PENDING_UPDATE)
        driver_name, vim_auth = self._get_infra_driver(context, vnf_dict)
        instance_id = self._instance_id(vnf_dict)

        try:
            self.mgmt_update_pre(context, vnf_dict)
            self._vnf_manager.invoke(
                driver_name, 'update', plugin=self, context=context,
                vnf_id=instance_id, vnf_dict=vnf_dict,
                vnf=vnf, auth_attr=vim_auth)
        except vnfm.VNFUpdateInvalidInput:
            with excutils.save_and_reraise_exception():
                vnf_dict['status'] = constants.ACTIVE
                self._update_vnf_post(context, vnf_id,
                                      constants.ACTIVE,
                                      vnf_dict, constants.PENDING_UPDATE,
                                      constants.RES_EVT_UPDATE)
        except Exception as e:
            with excutils.save_and_reraise_exception():
                vnf_dict['status'] = constants.ERROR
                self._vnf_monitor.delete_hosting_vnf(vnf_id)
                self.set_vnf_error_status_reason(context,
                                                 vnf_dict['id'],
                                                 six.text_type(e))
                self.mgmt_update_post(context, vnf_dict)
                self._update_vnf_post(context, vnf_id,
                                      constants.ERROR,
                                      vnf_dict, constants.PENDING_UPDATE,
                                      constants.RES_EVT_UPDATE)

        self.spawn_n(self._update_vnf_wait, context, vnf_dict, vim_auth,
                     driver_name)
        return vnf_dict

    def heal_vnf(self, context, vnf_id, heal_request_data_obj):
        vnf_dict = self._update_vnf_pre(context, vnf_id,
                                        constants.PENDING_HEAL)
        driver_name, vim_auth = self._get_infra_driver(context, vnf_dict)
        # Update vnf status to 'PENDING_HEAL' so that monitoring can
        # be paused.
        evt_details = ("Starts heal vnf request for VNF '%s'. "
                       "Reason to Heal VNF: '%s'" % (vnf_dict['id'],
                       heal_request_data_obj.cause))
        self._vnf_monitor.update_hosting_vnf(vnf_dict, evt_details)

        try:
            vnf_dict['heal_stack_id'] = heal_request_data_obj.stack_id
            self._vnf_maintenance_plugin.project_instance_pre(context,
                                                              vnf_dict)
            self.mgmt_update_pre(context, vnf_dict)
            self._vnf_manager.invoke(
                driver_name, 'heal_vdu', plugin=self,
                context=context, vnf_dict=vnf_dict,
                heal_request_data_obj=heal_request_data_obj)
        except vnfm.VNFHealFailed as e:
            with excutils.save_and_reraise_exception():
                vnf_dict['status'] = constants.ERROR
                self._vnf_monitor.delete_hosting_vnf(vnf_id)
                self.set_vnf_error_status_reason(context,
                                                 vnf_dict['id'],
                                                 six.text_type(e))
                self.mgmt_update_post(context, vnf_dict)
                self._vnf_maintenance_plugin.post(context, vnf_dict)
                self._update_vnf_post(context, vnf_id,
                                      constants.ERROR,
                                      vnf_dict, constants.PENDING_HEAL,
                                      constants.RES_EVT_HEAL)

        self.spawn_n(self._heal_vnf_wait, context, vnf_dict, vim_auth,
                     driver_name)

        return vnf_dict

    def _delete_vnf_wait(self, context, vnf_dict, auth_attr, driver_name):
        instance_id = self._instance_id(vnf_dict)
        e = None
        if instance_id:
            placement_attr = vnf_dict['placement_attr']
            region_name = placement_attr.get('region_name')
            try:
                self._vnf_manager.invoke(
                    driver_name,
                    'delete_wait',
                    plugin=self,
                    context=context,
                    vnf_id=instance_id,
                    auth_attr=auth_attr,
                    region_name=region_name)
            except Exception as e_:
                e = e_
                vnf_dict['status'] = constants.ERROR
                vnf_dict['error_reason'] = six.text_type(e)
                LOG.exception('_delete_vnf_wait')
                self.set_vnf_error_status_reason(context, vnf_dict['id'],
                                                 vnf_dict['error_reason'])

        self._vnf_maintenance_plugin.delete_vnf_constraints(self, context,
                                                            vnf_dict)
        self.mgmt_delete_post(context, vnf_dict)
        self._delete_vnf_post(context, vnf_dict, e)

    def _delete_vnf(self, context, vnf_id, force_delete=False):

        vnf_dict = self._delete_vnf_pre(context, vnf_id,
                                        force_delete=force_delete)
        driver_name, vim_auth = self._get_infra_driver(context, vnf_dict)
        self._vnf_monitor.delete_hosting_vnf(vnf_id)
        instance_id = self._instance_id(vnf_dict)
        placement_attr = vnf_dict['placement_attr']
        region_name = placement_attr.get('region_name')
        kwargs = {
            mgmt_constants.KEY_ACTION: mgmt_constants.ACTION_DELETE_VNF,
            mgmt_constants.KEY_KWARGS: {'vnf': vnf_dict},
        }
        try:
            self._vnf_maintenance_plugin.project_instance_pre(context,
                                                              vnf_dict)
            self.mgmt_delete_pre(context, vnf_dict)
            self.mgmt_call(context, vnf_dict, kwargs)
            if instance_id:
                self._vnf_manager.invoke(driver_name,
                                         'delete',
                                         plugin=self,
                                         context=context,
                                         vnf_id=instance_id,
                                         auth_attr=vim_auth,
                                         region_name=region_name)
        except Exception as e:
            # TODO(yamahata): when the device is already deleted. mask
            # the error, and delete row in db
            # Other case mark error
            with excutils.save_and_reraise_exception():
                if not force_delete:
                    vnf_dict['status'] = constants.ERROR
                    vnf_dict['error_reason'] = six.text_type(e)
                    self.set_vnf_error_status_reason(context, vnf_dict['id'],
                                                     vnf_dict['error_reason'])
                    self.mgmt_delete_post(context, vnf_dict)
                    self._delete_vnf_post(context, vnf_dict, e)

        if force_delete:
            self._delete_vnf_force(context, vnf_dict['id'])
            self.mgmt_delete_post(context, vnf_dict)
            self._delete_vnf_post(context, vnf_dict, None, force_delete=True)
        else:
            self.spawn_n(self._delete_vnf_wait, context, vnf_dict, vim_auth,
                         driver_name)

    def delete_vnf(self, context, vnf_id, vnf=None):

        # Extract "force_delete" from request's body
        force_delete = False
        if vnf and vnf['vnf'].get('attributes').get('force'):
            force_delete = vnf['vnf'].get('attributes').get('force')
        if force_delete and not context.is_admin:
            LOG.warning("force delete is admin only operation")
            raise exceptions.AdminRequired(reason="Admin only operation")

        self._delete_vnf(context, vnf_id, force_delete=force_delete)

    def _handle_vnf_scaling(self, context, policy):
        # validate
        def _validate_scaling_policy():
            type = policy['type']

            if type not in constants.POLICY_ACTIONS:
                raise exceptions.VnfPolicyTypeInvalid(
                    type=type,
                    valid_types=constants.POLICY_ACTIONS.keys(),
                    policy=policy['name']
                )
            action = policy['action']

            if action not in constants.POLICY_ACTIONS[type]:
                raise exceptions.VnfPolicyActionInvalid(
                    action=action,
                    valid_actions=constants.POLICY_ACTIONS[type],
                    policy=policy['name']
                )

            LOG.debug("Policy %s is validated successfully", policy['name'])

        def _get_status():
            if policy['action'] == constants.ACTION_SCALE_IN:
                status = constants.PENDING_SCALE_IN
            else:
                status = constants.PENDING_SCALE_OUT

            return status

        # pre
        def _handle_vnf_scaling_pre():
            status = _get_status()
            result = self._update_vnf_scaling_status(context,
                                                     policy,
                                                     [constants.ACTIVE],
                                                     status)
            LOG.debug("Policy %(policy)s vnf is at %(status)s",
                      {'policy': policy['name'],
                       'status': status})
            self._vnf_maintenance_plugin.project_instance_pre(context,
                                                              result)
            return result

        # post
        def _handle_vnf_scaling_post(new_status, mgmt_ip_address=None):
            status = _get_status()
            result = self._update_vnf_scaling_status(context,
                                                     policy,
                                                     [status],
                                                     new_status,
                                                     mgmt_ip_address)
            LOG.debug("Policy %(policy)s vnf is at %(status)s",
                      {'policy': policy['name'],
                       'status': new_status})
            action = 'delete' if policy['action'] == 'in' else 'update'
            self._vnf_maintenance_plugin.update_vnf_instances(self, context,
                                                              result,
                                                              action=action)
            return result

        # action
        def _vnf_policy_action():
            try:
                last_event_id = self._vnf_manager.invoke(
                    infra_driver,
                    'scale',
                    plugin=self,
                    context=context,
                    auth_attr=vim_auth,
                    policy=policy,
                    region_name=region_name
                )
                LOG.debug("Policy %s action is started successfully",
                          policy['name'])
                return last_event_id
            except Exception as e:
                LOG.error("Policy %s action is failed to start",
                          policy)
                with excutils.save_and_reraise_exception():
                    vnf['status'] = constants.ERROR
                    self.set_vnf_error_status_reason(
                        context,
                        policy['vnf']['id'],
                        six.text_type(e))
                    _handle_vnf_scaling_post(constants.ERROR)

        # wait
        def _vnf_policy_action_wait():
            try:
                LOG.debug("Policy %s action is in progress",
                          policy['name'])
                mgmt_ip_address = self._vnf_manager.invoke(
                    infra_driver,
                    'scale_wait',
                    plugin=self,
                    context=context,
                    auth_attr=vim_auth,
                    policy=policy,
                    region_name=region_name,
                    last_event_id=last_event_id
                )
                LOG.debug("Policy %s action is completed successfully",
                          policy['name'])
                _handle_vnf_scaling_post(constants.ACTIVE, mgmt_ip_address)
                # TODO(kanagaraj-manickam): Add support for config and mgmt
            except Exception as e:
                LOG.error("Policy %s action is failed to complete",
                          policy['name'])
                with excutils.save_and_reraise_exception():
                    self.set_vnf_error_status_reason(
                        context,
                        policy['vnf']['id'],
                        six.text_type(e))
                    _handle_vnf_scaling_post(constants.ERROR)

        _validate_scaling_policy()

        vnf = _handle_vnf_scaling_pre()
        policy['instance_id'] = vnf['instance_id']

        infra_driver, vim_auth = self._get_infra_driver(context, vnf)
        region_name = vnf.get('placement_attr', {}).get('region_name', None)
        last_event_id = _vnf_policy_action()
        self.spawn_n(_vnf_policy_action_wait)

        return policy

    def _make_policy_dict(self, vnf, name, policy):
        p = {}
        p['type'] = policy.get('type')
        p['properties'] = policy.get('properties') or policy.get(
            'triggers') or policy.get('reservation')
        p['vnf'] = vnf
        p['name'] = name
        p['id'] = uuidutils.generate_uuid()
        return p

    def get_vnf_policies(
            self, context, vnf_id, filters=None, fields=None):
        vnf = self.get_vnf(context, vnf_id)
        vnfd_tmpl = yaml.safe_load(vnf['vnfd']['attributes']['vnfd'])
        policy_list = []

        polices = vnfd_tmpl['topology_template'].get('policies', [])
        for policy_dict in polices:
            for name, policy in policy_dict.items():
                def _add(policy):
                    p = self._make_policy_dict(vnf, name, policy)
                    p['name'] = name
                    policy_list.append(p)

                # Check for filters
                if filters.get('name') or filters.get('type'):
                    if name == filters.get('name'):
                        _add(policy)
                        break
                    elif policy['type'] == filters.get('type'):
                        _add(policy)
                        break
                    else:
                        continue

                _add(policy)

        return policy_list

    def get_vnf_policy(
            self, context, policy_id, vnf_id, fields=None):
        policies = self.get_vnf_policies(context,
                                         vnf_id,
                                         filters={'name': policy_id})
        if policies:
            return policies[0]
        else:
            return None

    def create_vnf_scale(self, context, vnf_id, scale):
        policy_ = self.get_vnf_policy(context,
                                      scale['scale']['policy'],
                                      vnf_id)
        if not policy_:
            raise exceptions.VnfPolicyNotFound(policy=scale['scale']['policy'],
                                               vnf_id=vnf_id)
        policy_.update({'action': scale['scale']['type']})
        self._handle_vnf_scaling(context, policy_)

        return scale['scale']

    def get_vnf_policy_by_type(self, context, vnf_id, policy_type=None, fields=None):             # noqa
        policies = self.get_vnf_policies(context,
                                         vnf_id,
                                         filters={'type': policy_type})
        if policies:
            return policies[0]

        raise exceptions.VnfPolicyTypeInvalid(
            type=policy_type, policy=None,
            valid_types=constants.VALID_POLICY_TYPES)

    def _validate_alarming_policy(self, context, vnf_id, trigger):
        # validate alarm status

        # Trigger will contain only one action in trigger['trigger'] as it
        # filtered in _get_vnf_triggers().
        # Getting action from trigger to decide which process_alarm_for_vnf
        # method will be called.
        if list(trigger['trigger'])[0]\
                in constants.RESERVATION_POLICY_ACTIONS:
            if not self._vnf_reservation_monitor.process_alarm_for_vnf(
                    vnf_id, trigger):
                raise exceptions.AlarmUrlInvalid(vnf_id=vnf_id)
        else:
            if not self._vnf_alarm_monitor.process_alarm_for_vnf(
                    vnf_id, trigger):
                raise exceptions.AlarmUrlInvalid(vnf_id=vnf_id)

        # validate policy action. if action is composite, split it.
        # ex: respawn%notify
        action = trigger['action_name']
        action_list = action.split('%')
        pl_action_dict = dict()
        pl_action_dict['policy_actions'] = dict()
        pl_action_dict['policy_actions']['def_actions'] = list()
        pl_action_dict['policy_actions']['custom_actions'] = dict()
        for action in action_list:
            # validate policy action. if action is composite, split it.
            # ex: SP1-in, SP1-out
            action_ = None
            if action in constants.DEFAULT_ALARM_ACTIONS:
                pl_action_dict['policy_actions']['def_actions'].append(action)
            policy_ = self.get_vnf_policy(context, action, vnf_id)
            if not policy_:
                sp_action = action.split('-')
                if len(sp_action) == 2:
                    bk_policy_name = sp_action[0]
                    bk_policy_action = sp_action[1]
                    policies_ = self.get_vnf_policies(
                        context, vnf_id, filters={'name': bk_policy_name})
                    if policies_:
                        policy_ = policies_[0]
                        action_ = bk_policy_action
            if policy_:
                pl_action_dict['policy_actions']['custom_actions'].update(
                    {policy_['id']: {'bckend_policy': policy_,
                                   'bckend_action': action_}})

            LOG.debug("Trigger %s is validated successfully", trigger)

        return pl_action_dict
        # validate url

    def _get_vnf_triggers(self, context, vnf_id, filters=None, fields=None):
        if filters.get('name') in constants.RESERVATION_POLICY_ACTIONS:
            policy = self.get_vnf_policy_by_type(
                context, vnf_id, policy_type=constants.POLICY_RESERVATION)
        else:
            policy = self.get_vnf_policy_by_type(
                context, vnf_id, policy_type=constants.POLICY_ALARMING)
        triggers = policy['properties']
        vnf_trigger = dict()
        for trigger_name, trigger_dict in triggers.items():
            if trigger_name == filters.get('name'):
                vnf_trigger['trigger'] = {trigger_name: trigger_dict}
                vnf_trigger['vnf'] = policy['vnf']
                break

        return vnf_trigger

    def get_vnf_trigger(self, context, vnf_id, trigger_name):
        trigger = self._get_vnf_triggers(
            context, vnf_id, filters={'name': trigger_name})
        if not trigger:
            raise exceptions.TriggerNotFound(
                trigger_name=trigger_name,
                vnf_id=vnf_id
            )
        return trigger

    def _handle_vnf_monitoring(self, context, trigger):

        vnf_dict = trigger['vnf']
        # Multiple actions support
        if trigger.get('policy_actions'):
            policy_actions = trigger['policy_actions']
            if policy_actions.get('def_actions'):
                for action in policy_actions['def_actions']:
                    self._vnf_action.invoke(
                        action, 'execute_action', plugin=self, context=context,
                        vnf_dict=vnf_dict, args={})
            if policy_actions.get('custom_actions'):
                custom_actions = policy_actions['custom_actions']
                for pl_action, pl_action_dict in custom_actions.items():
                    bckend_policy = pl_action_dict['bckend_policy']
                    bckend_action = pl_action_dict['bckend_action']
                    bckend_policy_type = bckend_policy['type']
                    if bckend_policy_type == constants.POLICY_SCALING:
                        if vnf_dict['status'] != constants.ACTIVE:
                            LOG.info(_("Scaling Policy action "
                                       "skipped due to status "
                                       "%(status)s for vnf %(vnfid)s") %
                                     {"status": vnf_dict['status'],
                                      "vnfid": vnf_dict['id']})
                            return
                        action = 'autoscaling'
                        scale = {}
                        scale.setdefault('scale', {})
                        scale['scale']['type'] = bckend_action
                        scale['scale']['policy'] = bckend_policy['name']
                        self._vnf_action.invoke(
                            action, 'execute_action', plugin=self,
                            context=context, vnf_dict=vnf_dict, args=scale)

    def create_vnf_trigger(
            self, context, vnf_id, trigger):
        trigger_ = self.get_vnf_trigger(
            context, vnf_id, trigger['trigger']['policy_name'])
        # action_name before analyzing
        trigger_.update({'action_name': trigger['trigger']['action_name']})
        trigger_.update({'params': trigger['trigger']['params']})
        policy_actions = self._validate_alarming_policy(
            context, vnf_id, trigger_)
        if policy_actions:
            trigger_.update(policy_actions)
        self._handle_vnf_monitoring(context, trigger_)
        return trigger['trigger']

    def get_vnf_resources(self, context, vnf_id, fields=None, filters=None):
        vnf_info = self.get_vnf(context, vnf_id)
        infra_driver, vim_auth = self._get_infra_driver(context, vnf_info)
        region_name = vnf_info.get('placement_attr', {}).\
            get('region_name', None)
        if vnf_info['status'] == constants.ACTIVE:
            vnf_details = self._vnf_manager.invoke(infra_driver,
                                                   'get_resource_info',
                                                   plugin=self,
                                                   context=context,
                                                   vnf_info=vnf_info,
                                                   auth_attr=vim_auth,
                                                   region_name=region_name)
            resources = [{'name': name,
                          'type': info.get('type'),
                          'id': info.get('id')}
                        for name, info in vnf_details.items()]
            return resources
        # Raise exception when VNF.status != ACTIVE
        else:
            raise vnfm.VNFInactive(vnf_id=vnf_id,
                                   message=_(' Cannot fetch details'))

    def create_vnf_maintenance(self, context, vnf_id, maintenance):
        _maintenance = self._vnf_maintenance_plugin.validate_maintenance(
            maintenance.copy())
        vnf = self.get_vnf(context, vnf_id)
        _maintenance['vnf'] = vnf
        self._vnf_maintenance_plugin.handle_maintenance(
            self, context, _maintenance)
        policy_action = _maintenance.get('policy_action', '')
        if policy_action:
            self._vnf_action.invoke(
                policy_action['action'], 'execute_action', plugin=self,
                context=context, vnf_dict=vnf, args=policy_action['args'])
        else:
            self._vnf_maintenance_plugin.request(self, context, vnf,
                                                 _maintenance)
        return maintenance['maintenance']
