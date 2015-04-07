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

import inspect

import eventlet
from oslo_config import cfg

from tacker.api.v1 import attributes
from tacker.common import driver_manager
from tacker.db.vm import vm_db
from tacker.extensions import servicevm
from tacker.openstack.common import excutils
from tacker.openstack.common import log as logging
from tacker.plugins.common import constants
from tacker.vm.mgmt_drivers import constants as mgmt_constants

LOG = logging.getLogger(__name__)


class ServiceVMMgmtMixin(object):
    OPTS = [
        cfg.MultiStrOpt(
            'mgmt_driver', default=[],
            help=_('MGMT driver to communicate with '
                   'Hosting Device/logical service '
                   'instance servicevm plugin will use')),
    ]
    cfg.CONF.register_opts(OPTS, 'servicevm')

    def __init__(self):
        super(ServiceVMMgmtMixin, self).__init__()
        self._mgmt_manager = driver_manager.DriverManager(
            'tacker.servicevm.mgmt.drivers', cfg.CONF.servicevm.mgmt_driver)

    def _invoke(self, device_dict, **kwargs):
        method = inspect.stack()[1][3]
        return self._mgmt_manager.invoke(
            self._mgmt_device_driver(device_dict), method, **kwargs)

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

    def mgmt_address(self, context, device_dict):
        return self._invoke(
            device_dict, plugin=self, context=context, device=device_dict)

    def mgmt_call(self, context, device_dict, kwargs):
        return self._invoke(
            device_dict, plugin=self, context=context, device=device_dict,
            kwargs=kwargs)


class ServiceVMPlugin(vm_db.ServiceResourcePluginDb, ServiceVMMgmtMixin):
    """ServiceVMPlugin which supports ServiceVM framework
    """
    OPTS = [
        cfg.MultiStrOpt(
            'infra_driver', default=[],
            help=_('Hosting device drivers servicevm plugin will use')),
    ]
    cfg.CONF.register_opts(OPTS, 'servicevm')
    supported_extension_aliases = ['servicevm']

    def __init__(self):
        super(ServiceVMPlugin, self).__init__()
        self._pool = eventlet.GreenPool()
        self._device_manager = driver_manager.DriverManager(
            'tacker.servicevm.device.drivers',
            cfg.CONF.servicevm.infra_driver)

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
            raise servicevm.InfraDriverNotSpecified()
        if infra_driver not in self._device_manager:
            LOG.debug(_('unknown hosting device driver '
                        '%(infra_driver)s in %(drivers)s'),
                      {'infra_driver': infra_driver,
                       'drivers': cfg.CONF.servicevm.infra_driver})
            raise servicevm.InvalidInfraDriver(infra_driver=infra_driver)

        return super(ServiceVMPlugin, self).create_device_template(
            context, device_template)

    ###########################################################################
    # hosting device

    def _create_device_wait(self, context, device_dict):
        driver_name = self._infra_driver_name(device_dict)
        device_id = device_dict['id']
        instance_id = self._instance_id(device_dict)

        try:
            self._device_manager.invoke(
                driver_name, 'create_wait', plugin=self,
                context=context, device_id=instance_id)
        except servicevm.DeviceCreateWaitFailed:
            instance_id = None
            del device_dict['instance_id']

        if instance_id is None:
            mgmt_address = None
        else:
            mgmt_address = self.mgmt_address(context, device_dict)

        self._create_device_post(
            context, device_id, instance_id, mgmt_address,
            device_dict['service_context'])
        if instance_id is None:
            self.mgmt_create_post(context, device_dict)
            return

        self.mgmt_create_post(context, device_dict)
        device_dict['mgmt_address'] = mgmt_address

        kwargs = {
            mgmt_constants.KEY_ACTION: mgmt_constants.ACTION_CREATE_DEVICE,
            mgmt_constants.KEY_KWARGS: {'device': device_dict},
        }
        new_status = constants.ACTIVE
        try:
            self.mgmt_call(context, device_dict, kwargs)
        except Exception:
            new_status = constants.ERROR
        device_dict['status'] = new_status
        self._create_device_status(context, device_id, new_status)

    def _create_device(self, context, device):
        device_dict = self._create_device_pre(context, device)
        device_id = device_dict['id']
        driver_name = self._infra_driver_name(device_dict)
        LOG.debug(_('device_dict %s'), device_dict)
        self.mgmt_create_pre(context, device_dict)
        instance_id = self._device_manager.invoke(
            driver_name, 'create', plugin=self,
            context=context, device=device_dict)

        if instance_id is None:
            self._create_device_post(context, device_id, None, None)
            return

        device_dict['instance_id'] = instance_id
        return device_dict

    def create_device(self, context, device):
        device_dict = self._create_device(context, device)
        self.spawn_n(self._create_device_wait, context, device_dict)
        return device_dict

    # not for wsgi, but for service to creaste hosting device
    def create_device_sync(self, context, template_id, kwargs):
        assert template_id is not None
        device = {
            'device': {
                'template_id': template_id,
                'kwargs': kwargs,
            },
        }
        device_dict = self._create_device(context, device)
        if 'instance_id' not in device_dict:
            raise servicevm.DeviceCreateFailed(device_template_id=template_id)

        self._create_device_wait(context, device_dict)
        if 'instance_id' not in device_dict:
            raise servicevm.DeviceCreateFailed(device_template_id=template_id)

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
            new_status = constants.ERROR
        device_dict['status'] = new_status
        self.mgmt_update_post(context, device_dict)
        self._update_device_post(context, device_dict['id'], new_status)

    def update_device(self, context, device_id, device):
        device_dict = self._update_device_pre(context, device_id)
        driver_name = self._infra_driver_name(device_dict)
        instance_id = self._instance_id(device_dict)

        try:
            self.mgmt_update_pre(context, device_dict)
            self._device_manager.invoke(driver_name, 'update', plugin=self,
                                        context=context, device_id=instance_id)
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
        self.mgmt_delete_post(context, device_dict)
        device_id = device_dict['id']
        self._delete_device_post(context, device_id, e)

    def delete_device(self, context, device_id):
        device_dict = self._delete_device_pre(context, device_id)
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

    def _do_interface(self, context, device_id, port_id, action):
        device_dict = self._update_device_pre(context, device_id)
        driver_name = self._infra_driver_name(device_dict)
        instance_id = self._instance_id(device_dict)

        try:
            self._device_manager.invoke(driver_name, action, plugin=self,
                                        context=context, device_id=instance_id)
        except Exception:
            with excutils.save_and_reraise_exception():
                device_dict['status'] = constants.ERROR
                self._update_device_post(context, device_id, constants.ERROR)

        self._update_device_post(context, device_dict['id'], constants.ACTIVE)

    def attach_interface(self, context, id, port_id):
        return self._do_interface(context, id, port_id, 'attach_interface')

    def detach_interface(self, context, id, port_id):
        return self._do_interface(context, id, port_id, 'dettach_interface')
