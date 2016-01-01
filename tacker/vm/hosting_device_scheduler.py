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

import random

import sqlalchemy as sa

from tacker.db.vm import vm_db
from tacker.openstack.common import log as logging
from tacker.plugins.common import constants


LOG = logging.getLogger(__name__)


class ChanceScheduler(object):

    """Select a Device that can serve a service in a random way."""

    def schedule(self, plugin, context,
                 service_type, service_instance_id, name, service_context):
        """Scheduler.

        :param service_context: list of DeviceServiceContext
                                without service_instance_id
        [{'network_id': network_id,
          'subnet_id': subnet_id,
          'port_id': port_id,
          'router_id': router_id,
          'role': role,
          'index': index},
        ... ]
        They can be missing or None = don't care
        """
        with context.session.begin(subtransactions=True):
            # Race. prevent from inserting ServiceDeviceBinding

            # select hosting device that is capable of service_type, but
            # not yet used for it.
            # i.e.
            # device.service_type in
            #     [st.service_types for st in
            #      device.template.service_types]
            # and
            # device.sevice_type not in
            #     [ls.service_type for ls in device.services]
            query = (
                context.session.query(vm_db.Device).
                filter(vm_db.Device.status == constants.ACTIVE).
                filter(
                    sa.exists().
                    where(sa.and_(
                        vm_db.Device.template_id == vm_db.DeviceTemplate.id,
                        vm_db.DeviceTemplate.id ==
                        vm_db.ServiceType.template_id,
                        vm_db.ServiceType.service_type == service_type))).
                filter(
                    ~sa.exists().
                    where(sa.and_(
                        vm_db.Device.id ==
                        vm_db.ServiceDeviceBinding.device_id,
                        vm_db.ServiceDeviceBinding.service_instance_id ==
                        vm_db.ServiceInstance.id,
                        vm_db.ServiceInstance.service_type_id ==
                        vm_db.ServiceType.id,
                        vm_db.ServiceType.service_type == service_type))))

            for sc_entry in service_context:
                network_id = sc_entry.get('network_id')
                subnet_id = sc_entry.get('subnet_id')
                port_id = sc_entry.get('port_id')
                router_id = sc_entry.get('router_id')
                role = sc_entry.get('role')
                index = sc_entry.get('index')

                expr = [
                    vm_db.Device.id == vm_db.DeviceServiceContext.device_id]
                if network_id is not None:
                    expr.append(
                        vm_db.DeviceServiceContext.network_id == network_id)
                if subnet_id is not None:
                    expr.append(
                        vm_db.DeviceServiceContext.subnet_id == subnet_id)
                if port_id is not None:
                    expr.append(vm_db.DeviceServiceContext.port_id == port_id)
                if router_id is not None:
                    expr.append(
                        vm_db.DeviceServiceContext.router_id == router_id)
                if role is not None:
                    expr.append(vm_db.DeviceServiceContext.role == role)
                if index is not None:
                    expr.append(vm_db.DeviceServiceContext.index == index)
                query = query.filter(sa.exists().where(sa.and_(*expr)))

            candidates = query.with_lockmode("update").all()
            if not candidates:
                LOG.debug(_('no hosting device supporing %s'), service_type)
                return
            device = random.choice(candidates)

            service_type_id = [s.id for s in device.template.service_types
                               if s.service_type == service_type][0]

            service_instance_param = {
                'name': name,
                'service_table_id': service_instance_id,
                'service_type': service_type,
                'service_type_id': service_type_id,
            }
            service_instance_dict = plugin._create_service_instance(
                context, device.id, service_instance_param, False)
            return (plugin._make_device_dict(device), service_instance_dict)
