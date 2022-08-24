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
from tacker.sol_refactored.common import http_client
from tacker.sol_refactored.conductor import conductor_rpc_v2 as rpc
from tacker.sol_refactored import objects

LOG = logging.getLogger(__name__)
CONF = cfg.CONF


class ServerNotificationTimer():
    def __init__(self, vnf_instance_id, expiration_time, expiration_handler):
        self.lock = threading.Lock()
        self.expired = False
        self.queue = []
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
                self.vnf_instance_id, list(set(self.queue)))

    def append(self, vnfc_instance_ids):
        with self.lock:
            if not self.expired:
                self.queue.extend(vnfc_instance_ids)

    def _cancel(self):
        self.timer.cancel()
        self.expired = True

    def cancel(self):
        with self.lock:
            if not self.expired:
                self._cancel()

    def __del__(self):
        self.cancel()


class ServerNotificationDriver():
    _instance = None

    @staticmethod
    def instance():
        if not ServerNotificationDriver._instance:
            ServerNotificationDriver._instance = (
                ServerNotificationDriverMain()
                if CONF.server_notification.server_notification
                else ServerNotificationDriver())
        return ServerNotificationDriver._instance

    def notify(self, vnf_instance_id, vnfc_instance_ids):
        pass

    def remove_timer(self, vnf_instance_id):
        pass


class ServerNotificationDriverMain(ServerNotificationDriver):
    def __init__(self):
        self.timer_map = {}
        self.expiration_time = CONF.server_notification.timer_interval
        auth_handle = http_client.KeystonePasswordAuthHandle(
            auth_url=CONF.keystone_authtoken.auth_url,
            username=CONF.keystone_authtoken.username,
            password=CONF.keystone_authtoken.password,
            project_name=CONF.keystone_authtoken.project_name,
            user_domain_name=CONF.keystone_authtoken.user_domain_name,
            project_domain_name=CONF.keystone_authtoken.project_domain_name)
        self.client = http_client.HttpClient(auth_handle)
        sn_auth_handle = http_client.NoAuthHandle()
        self.sn_client = http_client.HttpClient(sn_auth_handle)
        self.rpc = rpc.VnfLcmRpcApiV2()

    def notify(self, vnf_instance_id, vnfc_instance_ids):
        if vnf_instance_id not in self.timer_map:
            self.timer_map[vnf_instance_id] = ServerNotificationTimer(
                vnf_instance_id, self.expiration_time, self.timer_expired)
        self.timer_map[vnf_instance_id].append(vnfc_instance_ids)

    def remove_timer(self, vnf_instance_id):
        if vnf_instance_id in self.timer_map:
            self.timer_map[vnf_instance_id].cancel()
            del self.timer_map[vnf_instance_id]

    def request_heal(self, vnf_instance_id, vnfc_instance_ids):
        heal_req = objects.HealVnfRequest(vnfcInstanceId=vnfc_instance_ids)
        LOG.info("server_notification auto healing is processed: %s.",
                 vnf_instance_id)
        ep = CONF.v2_vnfm.endpoint
        url = f'{ep}/vnflcm/v2/vnf_instances/{vnf_instance_id}/heal'
        resp, body = self.client.do_request(
            url, "POST", body=heal_req.to_dict(), version="2.0.0")
        if resp.status_code != 202:
            LOG.error(str(body))
            LOG.error("server_notification auto healing is failed: %d.",
                      resp.status_code)

    def timer_expired(self, vnf_instance_id, vnfc_instance_ids):
        self.remove_timer(vnf_instance_id)
        self.request_heal(vnf_instance_id, vnfc_instance_ids)
