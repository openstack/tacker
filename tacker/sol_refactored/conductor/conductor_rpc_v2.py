# Copyright (C) 2021 Nippon Telegraph and Telephone Corporation
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


import oslo_messaging

from tacker.common import rpc
from tacker.sol_refactored.objects import base as objects_base


TOPIC_CONDUCTOR_V2 = 'TACKER_CONDUCTOR_V2'


class VnfLcmRpcApiV2(object):

    target = oslo_messaging.Target(
        exchange='tacker',
        topic=TOPIC_CONDUCTOR_V2,
        fanout=False,
        version='1.0')

    def _cast_lcm_op(self, context, lcmocc_id, method):
        serializer = objects_base.TackerObjectSerializer()

        client = rpc.get_client(self.target, version_cap=None,
                                serializer=serializer)
        cctxt = client.prepare()
        cctxt.cast(context, method, lcmocc_id=lcmocc_id)

    def start_lcm_op(self, context, lcmocc_id):
        self._cast_lcm_op(context, lcmocc_id, 'start_lcm_op')

    def retry_lcm_op(self, context, lcmocc_id):
        self._cast_lcm_op(context, lcmocc_id, 'retry_lcm_op')

    def rollback_lcm_op(self, context, lcmocc_id):
        self._cast_lcm_op(context, lcmocc_id, 'rollback_lcm_op')

    def modify_vnfinfo(self, context, lcmocc_id):
        self._cast_lcm_op(context, lcmocc_id, 'modify_vnfinfo')

    def server_notification_cast(self, context, method, **kwargs):
        serializer = objects_base.TackerObjectSerializer()
        client = rpc.get_client(
            self.target, version_cap=None, serializer=serializer)
        cctxt = client.prepare()
        cctxt.cast(context, method, **kwargs)

    def server_notification_notify(
            self, context, vnf_instance_id, vnfc_instance_ids):
        self.server_notification_cast(
            context, 'server_notification_notify',
            vnf_instance_id=vnf_instance_id,
            vnfc_instance_ids=vnfc_instance_ids)

    def server_notification_remove_timer(self, context, vnf_instance_id):
        self.server_notification_cast(
            context, 'server_notification_remove_timer',
            vnf_instance_id=vnf_instance_id)


TOPIC_PROMETHEUS_PLUGIN = 'TACKER_PROMETHEUS_PLUGIN'


class PrometheusPluginConductor(object):

    target = oslo_messaging.Target(
        exchange='tacker',
        topic=TOPIC_PROMETHEUS_PLUGIN,
        fanout=False,
        version='1.0')

    def cast(self, context, method, **kwargs):
        serializer = objects_base.TackerObjectSerializer()
        client = rpc.get_client(
            self.target, version_cap=None, serializer=serializer)
        cctxt = client.prepare()
        cctxt.cast(context, method, **kwargs)

    def store_alarm_info(self, context, alarm):
        self.cast(context, 'store_alarm_info', alarm=alarm)

    def store_job_info(self, context, report):
        self.cast(context, 'store_job_info', report=report)

    def request_scale(self, context, id, scale_req):
        self.cast(context, 'request_scale', id=id, scale_req=scale_req)
