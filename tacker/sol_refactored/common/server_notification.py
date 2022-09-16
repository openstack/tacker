# Copyright (C) 2022 Fujitsu
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

from tacker.sol_refactored.api.schemas import server_notification_schemas
from tacker.sol_refactored.api import server_notification_validator\
    as validator
from tacker.sol_refactored.common import config as cfg
from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.common import monitoring_plugin_base as mon_base
from tacker.sol_refactored.common import vnf_instance_utils as inst_utils
from tacker.sol_refactored.conductor import conductor_rpc_v2

CONF = cfg.CONF


class ServerNotification(mon_base.MonitoringPlugin):
    _instance = None

    @staticmethod
    def instance():
        if not ServerNotification._instance:
            if not CONF.server_notification.server_notification:
                stub = mon_base.MonitoringPluginStub.instance()
                ServerNotification._instance = stub
            else:
                ServerNotification()
        return ServerNotification._instance

    def __init__(self):
        if ServerNotification._instance:
            raise SystemError(
                "Not constructor but instance() should be used.")
        self.set_callback(self.default_callback)
        self.rpc = conductor_rpc_v2.VnfLcmRpcApiV2()
        ServerNotification._instance = self

    def set_callback(self, notification_callback):
        self._notification_callback = notification_callback

    def alert(self, **kwargs):
        self.notify(
            kwargs['request'], kwargs['vnf_instance_id'],
            body=kwargs['body'])

    def default_callback(self, context, vnf_instance_id, vnfcids):
        self.rpc.server_notification_notify(context, vnf_instance_id, vnfcids)

    def get_vnfc_instance_id(
            self, context, vnf_instance_id, alarm_id, fault_id):
        vnf_instance = inst_utils.get_inst(context, vnf_instance_id)
        if not vnf_instance:
            raise sol_ex.ServerNotificationValidationError(
                detail="target vnf instance not found.")

        if (not vnf_instance.obj_attr_is_set('instantiatedVnfInfo') or
                not vnf_instance.instantiatedVnfInfo.obj_attr_is_set(
                    'metadata') or
                not vnf_instance.instantiatedVnfInfo.obj_attr_is_set(
                    'vnfcResourceInfo') or
                not vnf_instance.instantiatedVnfInfo.obj_attr_is_set(
                    'vnfcInfo')):
            raise sol_ex.ServerNotificationValidationError(
                detail="access info not found in the vnf instance.")
        if fault_id != vnf_instance.instantiatedVnfInfo.metadata.get(
                'ServerNotifierFaultID'):
            raise sol_ex.ServerNotificationValidationError(
                detail="fault_id does not match.")

        # Get the list of instantiatedVnfInfo.vnfcInfo[x].id where
        #   vnfcInfo[x].vnfcResourceInfoId == vnfcResourceInfo[y].id and
        #   vnfcResourceInfo[y].metadata.alarmId == alarm_id
        rsc_info = filter(lambda x: ('metadata' in x and
            alarm_id == x['metadata'].get('alarmId')),
            vnf_instance.instantiatedVnfInfo.vnfcResourceInfo)
        rsc_ids = list(map(lambda x: x['id'], rsc_info))
        vnfc_info = filter(lambda x:
            (x.obj_attr_is_set('vnfcResourceInfoId') and
            x.vnfcResourceInfoId in rsc_ids),
            vnf_instance.instantiatedVnfInfo.vnfcInfo)
        vnfc_ids = list(map(lambda x: x.id, vnfc_info))

        if len(vnfc_ids) == 0:
            raise sol_ex.ServerNotificationValidationError(
                detail="target vnfc not found.")
        return vnfc_ids

    @validator.schema(server_notification_schemas.ServerNotification)
    def notify(self, request, vnf_instance_id, body):
        context = request.context
        vnfcids = self.get_vnfc_instance_id(
            context, vnf_instance_id, body['notification']['alarm_id'],
            body['notification']['fault_id'])
        if self._notification_callback:
            self._notification_callback(context, vnf_instance_id, vnfcids)
