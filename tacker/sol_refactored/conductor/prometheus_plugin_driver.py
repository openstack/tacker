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

import threading

from oslo_log import log as logging
from tacker.sol_refactored.common import config as cfg
from tacker.sol_refactored.common import vnflcm_utils
from tacker.sol_refactored import objects

LOG = logging.getLogger(__name__)

CONF = cfg.CONF


class VnfmAutoHealTimer():
    def __init__(self, context, vnf_instance_id,
                 expiration_time, expiration_handler):
        self.lock = threading.Lock()
        self.expired = False
        self.queue = set()
        self.context = context
        self.vnf_instance_id = vnf_instance_id
        self.expiration_handler = expiration_handler
        self.timer = threading.Timer(expiration_time, self.expire)
        self.timer.start()

    def expire(self):
        _expired = False
        with self.lock:
            if not self.expired:
                self._cancel()
                _expired = True
        if _expired:
            self.expiration_handler(
                self.context, self.vnf_instance_id, list(self.queue))

    def add_vnfc_info_id(self, vnfc_info_id):
        with self.lock:
            if not self.expired:
                self.queue.add(vnfc_info_id)

    def _cancel(self):
        self.timer.cancel()
        self.expired = True

    def cancel(self):
        with self.lock:
            if not self.expired:
                self._cancel()

    def __del__(self):
        self.cancel()


class PrometheusPluginDriverStub():
    def trigger_scale(self, context, vnf_instance_id, scale_req):
        pass

    def enqueue_heal(self, context, vnf_instance_id, vnfc_info_id):
        pass

    def dequeue_heal(self, vnf_instance_id):
        pass


class PrometheusPluginDriver():
    _instance = None

    @staticmethod
    def instance():
        if PrometheusPluginDriver._instance is None:
            if (CONF.prometheus_plugin.auto_scaling or
                    CONF.prometheus_plugin.auto_healing or
                    CONF.prometheus_plugin.fault_management or
                    CONF.prometheus_plugin.performance_management):
                PrometheusPluginDriver()
            else:
                stub = PrometheusPluginDriverStub()
                PrometheusPluginDriver._instance = stub
        return PrometheusPluginDriver._instance

    def __init__(self):
        if PrometheusPluginDriver._instance:
            raise SystemError("Not constructor but instance() should be used.")
        PrometheusPluginDriver._instance = self
        self.timer_map = {}
        self.expiration_time = CONF.prometheus_plugin.timer_interval

    def enqueue_heal(self, context, vnf_instance_id, vnfc_info_id):
        if vnf_instance_id not in self.timer_map:
            self.timer_map[vnf_instance_id] = VnfmAutoHealTimer(
                context, vnf_instance_id, self.expiration_time,
                self._timer_expired)
        self.timer_map[vnf_instance_id].add_vnfc_info_id(vnfc_info_id)

    def dequeue_heal(self, vnf_instance_id):
        if vnf_instance_id in self.timer_map:
            self.timer_map[vnf_instance_id].cancel()
            del self.timer_map[vnf_instance_id]

    def _trigger_heal(self, context, vnf_instance_id, vnfc_info_ids):
        heal_req = objects.HealVnfRequest(vnfcInstanceId=vnfc_info_ids)
        body = heal_req.to_dict()
        LOG.info(f"VNFM AutoHealing is triggered. vnf: {vnf_instance_id}, "
                 f"vnfcInstanceId: {vnfc_info_ids}")
        vnflcm_utils.heal(context, vnf_instance_id, body, auto_invocation=True)

    def _timer_expired(self, context, vnf_instance_id, vnfc_info_ids):
        self.dequeue_heal(vnf_instance_id)
        self._trigger_heal(context, vnf_instance_id, vnfc_info_ids)

    def trigger_scale(self, context, vnf_instance_id, scale_req):
        LOG.info(f"VNFM AutoScaling is triggered. vnf: {vnf_instance_id}, "
                 f"type: {scale_req['type']}, aspectId: "
                 f"{scale_req['aspectId']}")
        vnflcm_utils.scale(context, vnf_instance_id, scale_req,
                           auto_invocation=True)
