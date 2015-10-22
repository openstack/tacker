# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright 2013, 2014 Intel Corporation.
# Copyright 2013, 2014 Isaku Yamahata <isaku.yamahata at intel com>
#                                     <isaku.yamahata at gmail com>
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
#
# @author: Isaku Yamahata, Intel Corporation.

import copy
import eventlet
import inspect

from oslo_config import cfg
from sqlalchemy.orm import exc as orm_exc

from tacker.api.v1 import attributes
from tacker.common import driver_manager
from tacker.db.vm import proxy_db  # noqa
from tacker.db.vm import vm_db
from tacker.extensions import vnfm
from tacker.openstack.common import excutils
from tacker.openstack.common import log as logging
from tacker.plugins.common import constants
from tacker.vm.mgmt_drivers import constants as mgmt_constants
from tacker.vm import monitor

LOG = logging.getLogger(__name__)


class VNFMMgmtMixin(object):
    OPTS = [
        cfg.MultiStrOpt(
            'mgmt_driver', default=[],
            help=_('MGMT driver to communicate with '
                   'Hosting Device/logical service '
                   'instance servicevm plugin will use')),
        cfg.IntOpt('boot_wait', default=30,
            help=_('Time interval to wait for VM to boot')),
    ]
    cfg.CONF.register_opts(OPTS, 'servicevm')

    def __init__(self):
        super(VNFMMgmtMixin, self).__init__()
        self._mgmt_manager = driver_manager.DriverManager(
            'tacker.servicevm.mgmt.drivers', cfg.CONF.servicevm.mgmt_driver)

    def _invoke(self, device_dict, **kwargs):
        method = inspect.stack()[1][3]
        return self._mgmt_manager.invoke(
            self._mgmt_driver_name(device_dict), method, **kwargs)

    def mgmt_create_pre(self, context, device_dict):
        return self._invoke(
            device_dict, plugin=self, context=context, device=device_dict)

    def mgmt_create_post(self, context, device_dict):
        return self._invoke(
            device_dict, plugin=self, context=context, device=device_dict)

    def mgmt_update_pre(self, context, device_dict):
        return self._invoke(
            device_dict, plugin=self, context=context, device=device_dict)

    def mgmt_update_post(self, context, device_dict):
        return self._invoke(
            device_dict, plugin=self, context=context, device=device_dict)

    def mgmt_delete_pre(self, context, device_dict):
        return self._invoke(
            device_dict, plugin=self, context=context, device=device_dict)

    def mgmt_delete_post(self, context, device_dict):
        return self._invoke(
            device_dict, plugin=self, context=context, device=device_dict)

    def mgmt_get_config(self, context, device_dict):
        return self._invoke(
            device_dict, plugin=self, context=context, device=device_dict)

    def mgmt_url(self, context, device_dict):
        return self._invoke(
            device_dict, plugin=self, context=context, device=device_dict)

    def mgmt_call(self, context, device_dict, kwargs):
        return self._invoke(
            device_dict, plugin=self, context=context, device=device_dict,
            kwargs=kwargs)

    def mgmt_service_driver(self, context, device_dict, service_instance_dict):
        return self._invoke(
            device_dict, plugin=self, context=context, device=device_dict,
            service_instance=service_instance_dict)

    def mgmt_service_create_pre(self, context, device_dict,
                                service_instance_dict):
        return self._invoke(
            device_dict, plugin=self, context=context, device=device_dict,
            service_instance=service_instance_dict)

    def mgmt_service_create_post(self, context, device_dict,
                                 service_instance_dict):
        return self._invoke(
            device_dict, plugin=self, context=context, device=device_dict,
            service_instance=service_instance_dict)

    def mgmt_service_update_pre(self, context, device_dict,
                                service_instance_dict):
        return self._invoke(
            device_dict, plugin=self, context=context, device=device_dict,
            service_instance=service_instance_dict)

    def mgmt_service_update_post(self, context, device_dict,
                                 service_instance_dict):
        return self._invoke(
            device_dict, plugin=self, context=context, device=device_dict,
            service_instance=service_instance_dict)

    def mgmt_service_delete_pre(self, context, device_dict,
                                service_instance_dict):
        return self._invoke(
            device_dict, plugin=self, context=context, device=device_dict,
            service_instance=service_instance_dict)

    def mgmt_service_delete_post(self, context, device_dict,
                                 service_instance_dict):
        return self._invoke(
            device_dict, plugin=self, context=context, device=device_dict,
            service_instance=service_instance_dict)

    def mgmt_service_address(self, context, device_dict,
                             service_instance_dict):
        return self._invoke(
            device_dict, plugin=self, context=context, device=device_dict,
            service_instance=service_instance_dict)

    def mgmt_service_call(self, context, device_dict, service_instance_dict,
                          kwargs):
        return self._invoke(
            device_dict, plugin=self, context=context, device=device_dict,
            service_instance=service_instance_dict, kwargs=kwargs)


class VNFMPlugin(vm_db.VNFMPluginDb, VNFMMgmtMixin):
    """ServiceVMPlugin which supports ServiceVM framework
    """
    OPTS = [
        cfg.ListOpt(
            'infra_driver', default=['heat'],
            help=_('Hosting device drivers servicevm plugin will use')),
    ]
    cfg.CONF.register_opts(OPTS, 'servicevm')
    supported_extension_aliases = ['vnfm']

    def __init__(self):
        super(VNFMPlugin, self).__init__()
        self._pool = eventlet.GreenPool()
        self.boot_wait = cfg.CONF.servicevm.boot_wait
        self._device_manager = driver_manager.DriverManager(
            'tacker.servicevm.device.drivers',
            cfg.CONF.servicevm.infra_driver)
        self._vnf_monitor = monitor.VNFMonitor(self.boot_wait)

    def spawn_n(self, function, *args, **kwargs):
        self._pool.spawn_n(function, *args, **kwargs)

    ###########################################################################
    # hosting device template

    def create_device_template(self, context, device_template):
        template = device_template['device_template']
        LOG.debug(_('template %s'), template)

        infra_driver = template.get('infra_driver')
        if not attributes.is_attr_set(infra_driver):
            LOG.debug(_('hosting device driver must be specified'))
            raise vnfm.InfraDriverNotSpecified()
        if infra_driver not in self._device_manager:
            LOG.debug(_('unknown hosting device driver '
                        '%(infra_driver)s in %(drivers)s'),
                      {'infra_driver': infra_driver,
                       'drivers': cfg.CONF.servicevm.infra_driver})
            raise vnfm.InvalidInfraDriver(infra_driver=infra_driver)

        service_types = template.get('service_types')
        if not attributes.is_attr_set(service_types):
            LOG.debug(_('service type must be specified'))
            raise vnfm.ServiceTypesNotSpecified()
        for service_type in service_types:
            # TODO(yamahata):
            # framework doesn't know what services are valid for now.
            # so doesn't check it here yet.
            pass

        self._device_manager.invoke(
            infra_driver, 'create_device_template_pre', plugin=self,
            context=context, device_template=device_template)

        return super(VNFMPlugin, self).create_device_template(
            context, device_template)

    ###########################################################################
    # hosting device
    def add_device_to_monitor(self, device_dict):
        dev_attrs = device_dict['attributes']

        if 'monitoring_policy' in dev_attrs:
            def action_cb(hosting_vnf_, action):
                action_cls = monitor.ActionPolicy.get_policy(action,
                    device_dict)
                if action_cls:
                    action_cls.execute_action(self, hosting_vnf['device'])

            hosting_vnf = self._vnf_monitor.to_hosting_vnf(
                device_dict, action_cb)
            LOG.debug('hosting_vnf: %s', hosting_vnf)
            self._vnf_monitor.add_hosting_vnf(hosting_vnf)

    def config_device(self, context, device_dict):
        config = device_dict['attributes'].get('config')
        if not config:
            return
        eventlet.sleep(self.boot_wait)      # wait for vm to be ready
        device_id = device_dict['id']
        update = {
            'device': {
                'id': device_id,
                'attributes': {'config': config},
            }
        }
        self.update_device(context, device_id, update)

    def _create_device_wait(self, context, device_dict):
        driver_name = self._infra_driver_name(device_dict)
        device_id = device_dict['id']
        instance_id = self._instance_id(device_dict)
        create_failed = False

        try:
            self._device_manager.invoke(
                driver_name, 'create_wait', plugin=self, context=context,
                device_dict=device_dict, device_id=instance_id)
        except vnfm.DeviceCreateWaitFailed:
            create_failed = True
            device_dict['status'] = constants.ERROR

        if instance_id is None or create_failed:
            mgmt_url = None
        else:
            # mgmt_url = self.mgmt_url(context, device_dict)
            # FIXME(yamahata):
            mgmt_url = device_dict['mgmt_url']

        self._create_device_post(
            context, device_id, instance_id, mgmt_url, device_dict)
        self.mgmt_create_post(context, device_dict)

        if instance_id is None or create_failed:
            return

        device_dict['mgmt_url'] = mgmt_url

        kwargs = {
            mgmt_constants.KEY_ACTION: mgmt_constants.ACTION_CREATE_DEVICE,
            mgmt_constants.KEY_KWARGS: {'device': device_dict},
        }
        new_status = constants.ACTIVE
        try:
            self.mgmt_call(context, device_dict, kwargs)
        except Exception:
            LOG.exception(_('create_device_wait'))
            new_status = constants.ERROR
        device_dict['status'] = new_status
        self._create_device_status(context, device_id, new_status)

    def _create_device(self, context, device):
        device_dict = self._create_device_pre(context, device)
        device_id = device_dict['id']
        driver_name = self._infra_driver_name(device_dict)
        LOG.debug(_('device_dict %s'), device_dict)
        self.mgmt_create_pre(context, device_dict)
        try:
            instance_id = self._device_manager.invoke(
                driver_name, 'create', plugin=self,
                context=context, device=device_dict)
        except Exception:
            with excutils.save_and_reraise_exception():
                self.delete_device(context, device_id)

        if instance_id is None:
            self._create_device_post(context, device_id, None, None,
                device_dict)
            return

        device_dict['instance_id'] = instance_id
        return device_dict

    def create_device(self, context, device):
        device_dict = self._create_device(context, device)

        def create_device_wait():
            self._create_device_wait(context, device_dict)
            self.add_device_to_monitor(device_dict)
            self.config_device(context, device_dict)
        self.spawn_n(create_device_wait)
        return device_dict

    # not for wsgi, but for service to create hosting device
    # the device is NOT added to monitor.
    def create_device_sync(self, context, device):
        device_dict = self._create_device(context, device)
        self._create_device_wait(context, device_dict)
        return device_dict

    def _update_device_wait(self, context, device_dict):
        driver_name = self._infra_driver_name(device_dict)
        instance_id = self._instance_id(device_dict)
        kwargs = {
            mgmt_constants.KEY_ACTION: mgmt_constants.ACTION_UPDATE_DEVICE,
            mgmt_constants.KEY_KWARGS: {'device': device_dict},
        }
        new_status = constants.ACTIVE
        try:
            self._device_manager.invoke(
                driver_name, 'update_wait', plugin=self,
                context=context, device_id=instance_id)
            self.mgmt_call(context, device_dict, kwargs)
        except Exception:
            LOG.exception(_('_update_device_wait'))
            new_status = constants.ERROR
        device_dict['status'] = new_status
        self.mgmt_update_post(context, device_dict)

        self._update_device_post(context, device_dict['id'],
                                 new_status, device_dict)

    def update_device(self, context, device_id, device):
        device_dict = self._update_device_pre(context, device_id)
        driver_name = self._infra_driver_name(device_dict)
        instance_id = self._instance_id(device_dict)

        try:
            self.mgmt_update_pre(context, device_dict)
            self._device_manager.invoke(
                driver_name, 'update', plugin=self, context=context,
                device_id=instance_id, device_dict=device_dict, device=device)
        except Exception:
            with excutils.save_and_reraise_exception():
                device_dict['status'] = constants.ERROR
                self.mgmt_update_post(context, device_dict)
                self._update_device_post(context, device_id, constants.ERROR)

        self.spawn_n(self._update_device_wait, context, device_dict)
        return device_dict

    def _delete_device_wait(self, context, device_dict):
        driver_name = self._infra_driver_name(device_dict)
        instance_id = self._instance_id(device_dict)

        e = None
        try:
            self._device_manager.invoke(
                driver_name, 'delete_wait', plugin=self,
                context=context, device_id=instance_id)
        except Exception as e_:
            e = e_
            device_dict['status'] = constants.ERROR
            LOG.exception(_('_delete_device_wait'))
        self.mgmt_delete_post(context, device_dict)
        device_id = device_dict['id']
        self._delete_device_post(context, device_id, e)

    def delete_device(self, context, device_id):
        device_dict = self._delete_device_pre(context, device_id)
        self._vnf_monitor.delete_hosting_vnf(device_id)
        driver_name = self._infra_driver_name(device_dict)
        instance_id = self._instance_id(device_dict)

        kwargs = {
            mgmt_constants.KEY_ACTION: mgmt_constants.ACTION_DELETE_DEVICE,
            mgmt_constants.KEY_KWARGS: {'device': device_dict},
        }
        try:
            self.mgmt_delete_pre(context, device_dict)
            self.mgmt_call(context, device_dict, kwargs)
            self._device_manager.invoke(driver_name, 'delete', plugin=self,
                                        context=context, device_id=instance_id)
        except Exception as e:
            # TODO(yamahata): when the devaice is already deleted. mask
            # the error, and delete row in db
            # Other case mark error
            with excutils.save_and_reraise_exception():
                device_dict['status'] = constants.ERROR
                self.mgmt_delete_post(context, device_dict)
                self._delete_device_post(context, device_id, e)

        self._delete_device_post(context, device_id, None)
        self.spawn_n(self._delete_device_wait, context, device_dict)

    ###########################################################################
    # logical service instance
    #
    def _create_service_instance_mgmt(
            self, context, device_dict, service_instance_dict):
        kwargs = {
            mgmt_constants.KEY_ACTION: mgmt_constants.ACTION_CREATE_SERVICE,
            mgmt_constants.KEY_KWARGS: {
                'device': device_dict,
                'service_instance': service_instance_dict,
            },
        }
        self.mgmt_call(context, device_dict, kwargs)

        mgmt_driver = self.mgmt_service_driver(
            context, device_dict, service_instance_dict)
        service_instance_dict['mgmt_driver'] = mgmt_driver
        mgmt_url = self.mgmt_service_address(
            context, device_dict, service_instance_dict)
        service_instance_dict['mgmt_url'] = mgmt_url
        LOG.debug(_('service_instance_dict '
                    '%(service_instance_dict)s '
                    'mgmt_driver %(mgmt_driver)s '
                    'mgmt_url %(mgmt_url)s'),
                  {'service_instance_dict':
                   service_instance_dict,
                   'mgmt_driver': mgmt_driver, 'mgmt_url': mgmt_url})
        self._update_service_instance_mgmt(
            context, service_instance_dict['id'], mgmt_driver, mgmt_url)

        self.mgmt_service_create_pre(
            context, device_dict, service_instance_dict)
        self.mgmt_service_call(
            context, device_dict, service_instance_dict, kwargs)

    def _create_service_instance_db(self, context, device_id,
                                    service_instance_param, managed_by_user):
        return super(VNFMPlugin, self)._create_service_instance(
            context, device_id, service_instance_param, managed_by_user)

    def _create_service_instance_by_type(
            self, context, device_dict,
            name, service_type, service_table_id):
        LOG.debug(_('device_dict %(device_dict)s '
                    'service_type %(service_type)s'),
                  {'device_dict': device_dict,
                   'service_type': service_type})
        service_type_id = [
            s['id'] for s in
            device_dict['device_template']['service_types']
            if s['service_type'].upper() == service_type.upper()][0]

        service_instance_param = {
            'name': name,
            'service_table_id': service_table_id,
            'service_type': service_type,
            'service_type_id': service_type_id,
        }
        service_instance_dict = self._create_service_instance_db(
            context, device_dict['id'], service_instance_param, False)

        new_status = constants.ACTIVE
        try:
            self._create_service_instance_mgmt(
                context, device_dict, service_instance_dict)
        except Exception:
            LOG.exception(_('_create_service_instance_by_type'))
            new_status = constants.ERROR
            raise
        finally:
            service_instance_dict['status'] = new_status
            self.mgmt_service_create_post(
                context, device_dict, service_instance_dict)
            self._update_service_instance_post(
                context, service_instance_dict['id'], new_status)
        return service_instance_dict

    # for service drivers. e.g. hosting_driver of loadbalancer
    def create_service_instance_by_type(self, context, device_dict,
                                        name, service_type, service_table_id):
        self._update_device_pre(context, device_dict['id'])
        new_status = constants.ACTIVE
        try:
            return self._create_service_instance_by_type(
                context, device_dict, name, service_type,
                service_table_id)
        except Exception:
            LOG.exception(_('create_service_instance_by_type'))
            new_status = constants.ERROR
        finally:
            self._update_device_post(context, device_dict['id'], new_status)

    def _create_service_instance_wait(self, context, device_id,
                                      service_instance_dict):
        device_dict = self.get_device(context, device_id)

        new_status = constants.ACTIVE
        try:
            self._create_service_instance_mgmt(
                context, device_dict, service_instance_dict)
        except Exception:
            LOG.exception(_('_create_service_instance_mgmt'))
            new_status = constants.ERROR
        service_instance_dict['status'] = new_status
        self.mgmt_service_create_post(
            context, device_dict, service_instance_dict)
        self._update_service_instance_post(
            context, service_instance_dict['id'], new_status)

    # for service drivers. e.g. hosting_driver of loadbalancer
    def _create_service_instance(self, context, device_id,
                                 service_instance_param, managed_by_user):
        service_instance_dict = self._create_service_instance_db(
            context, device_id, service_instance_param, managed_by_user)
        self.spawn_n(self._create_service_instance_wait, context,
                     device_id, service_instance_dict)
        return service_instance_dict

    def create_service_instance(self, context, service_instance):
        service_instance_param = service_instance['service_instance'].copy()
        device = service_instance_param.pop('devices')
        device_id = device[0]
        service_instance_dict = self._create_service_instance(
            context, device_id, service_instance_param, True)
        return service_instance_dict

    def _update_service_instance_wait(self, context, service_instance_dict,
                                      mgmt_kwargs, callback, errorback):
        devices = service_instance_dict['devices']
        assert len(devices) == 1
        device_dict = self.get_device(context, devices[0])
        kwargs = {
            mgmt_constants.KEY_ACTION: mgmt_constants.ACTION_UPDATE_SERVICE,
            mgmt_constants.KEY_KWARGS: {
                'device': device_dict,
                'service_instance': service_instance_dict,
                mgmt_constants.KEY_KWARGS: mgmt_kwargs,
            }
        }
        try:
            self.mgmt_call(context, device_dict, kwargs)
            self.mgmt_service_update_pre(context, device_dict,
                                         service_instance_dict)
            self.mgmt_service_call(context, device_dict,
                                   service_instance_dict, kwargs)
        except Exception:
            LOG.exception(_('mgmt call failed %s'), kwargs)
            service_instance_dict['status'] = constants.ERROR
            self.mgmt_service_update_post(context, device_dict,
                                          service_instance_dict)
            self._update_service_instance_post(
                context, service_instance_dict['id'], constants.ERROR)
            if errorback:
                errorback()
        else:
            service_instance_dict['status'] = constants.ACTIVE
            self.mgmt_service_update_post(context, device_dict,
                                          service_instance_dict)
            self._update_service_instance_post(
                context, service_instance_dict['id'], constants.ACTIVE)
            if callback:
                callback()

    # for service drivers. e.g. hosting_driver of loadbalancer
    def _update_service_instance(self, context, service_instance_id,
                                 mgmt_kwargs, callback, errorback):
        service_instance_dict = self._update_service_instance_pre(
            context, service_instance_id, {})
        self.spawn_n(self._update_service_instance_wait, context,
                     service_instance_dict, mgmt_kwargs, callback, errorback)

    # for service drivers. e.g. hosting_driver of loadbalancer
    def _update_service_table_instance(
            self, context, service_table_id, mgmt_kwargs, callback, errorback):
        _device_dict, service_instance_dict = self.get_by_service_table_id(
            context, service_table_id)
        service_instance_dict = self._update_service_instance_pre(
            context, service_instance_dict['id'], {})
        self.spawn_n(self._update_service_instance_wait, context,
                     service_instance_dict, mgmt_kwargs, callback, errorback)

    def update_service_instance(self, context, service_instance_id,
                                service_instance):
        mgmt_kwargs = service_instance['service_instance'].get('kwarg', {})
        service_instance_dict = self._update_service_instance_pre(
            context, service_instance_id, service_instance)

        self.spawn_n(self._update_service_instance_wait, context,
                     service_instance_dict, mgmt_kwargs, None, None)
        return service_instance_dict

    def _delete_service_instance_wait(self, context, device, service_instance,
                                      mgmt_kwargs, callback, errorback):
        service_instance_id = service_instance['id']
        kwargs = {
            mgmt_constants.KEY_ACTION: mgmt_constants.ACTION_DELETE_SERVICE,
            mgmt_constants.KEY_KWARGS: {
                'device': device,
                'service_instance': service_instance,
                mgmt_constants.KEY_KWARGS: mgmt_kwargs,
            }
        }
        try:
            self.mgmt_service_delete_pre(context, device, service_instance)
            self.mgmt_service_call(context, device, service_instance, kwargs)
            self.mgmt_call(context, device, kwargs)
        except Exception:
            LOG.exception(_('mgmt call failed %s'), kwargs)
            service_instance['status'] = constants.ERROR
            self.mgmt_service_delete_post(context, device, service_instance)
            self._update_service_instance_post(context, service_instance_id,
                                               constants.ERROR)
            if errorback:
                errorback()
        else:
            service_instance['status'] = constants.ACTIVE
            self.mgmt_service_delete_post(context, device, service_instance)
            self._delete_service_instance_post(context, service_instance_id)
            if callback:
                callback()

    # for service drivers. e.g. hosting_driver of loadbalancer
    def _delete_service_table_instance(
            self, context, service_table_instance_id,
            mgmt_kwargs, callback, errorback):
        try:
            device, service_instance = self.get_by_service_table_id(
                context, service_table_instance_id)
        except orm_exc.NoResultFound:
            # there are no entry for some reason.
            # e.g. partial creation due to error
            callback()
            return
        self._delete_service_instance_pre(context, service_instance['id'],
                                          False)
        self.spawn_n(
            self._delete_service_instance_wait, context, device,
            service_instance, mgmt_kwargs, callback, errorback)

    def delete_service_instance(self, context, service_instance_id):
        # mgmt_kwargs is needed?
        device, service_instance = self.get_by_service_instance_id(
            context, service_instance_id)
        self._delete_service_instance_pre(context, service_instance_id, True)
        self.spawn_n(
            self._delete_service_instance_wait, context, device,
            service_instance, {}, None, None)

    def create_vnf(self, context, vnf):
        vnf['device'] = vnf.pop('vnf')
        vnf_attributes = vnf['device']
        vnf_attributes['template_id'] = vnf_attributes.pop('vnfd_id')
        vnf_dict = self.create_device(context, vnf)
        vnf_response = copy.deepcopy(vnf_dict)
        vnf_response['vnfd_id'] = vnf_response.pop('template_id')
        return vnf_response

    def update_vnf(
            self, context, vnf_id, vnf):
        vnf['device'] = vnf.pop('vnf')
        return self.update_device(context, vnf_id, vnf)

    def delete_vnf(self, context, vnf_id):
        self.delete_device(context, vnf_id)

    def create_vnfd(self, context, vnfd):
        vnfd['device_template'] = vnfd.pop('vnfd')
        new_dict = self.create_device_template(context, vnfd)
        return new_dict
