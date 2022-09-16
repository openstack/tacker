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

import os
import pickle
import sys

from oslo_log import log as logging
from tacker.common import exceptions as common_ex
from tacker.sol_refactored.common import config as cfg
from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.common import http_client
from tacker.sol_refactored.conductor import conductor_rpc_v2

LOG = logging.getLogger(__name__)
CONF = cfg.CONF


class ServerNotificationMgmtDriver(object):

    def __init__(self, req, inst, grant_req, grant, csar_dir):
        self.req = req
        self.inst = inst
        self.grant_req = grant_req
        self.grant = grant
        self.csar_dir = csar_dir
        auth_handle = http_client.NoAuthHandle()
        self.client = http_client.HttpClient(auth_handle)
        self.rpc = conductor_rpc_v2.VnfLcmRpcApiV2()

    def make_output_dict(self):
        return {'vnf_instance': self.inst}

    def request_remove_timer(self, vnf_instance_id):
        self.rpc.server_notification_remove_timer(
            None, vnf_instance_id)

    def _request_unregister(
            self, server_notifier_uri, tenant, server_id, alarm_id):
        try:
            url = (f'{server_notifier_uri}/v2/{tenant}/servers/{server_id}/'
                f'alarms/{alarm_id}')
            resp, _ = self.client.do_request(
                url, "DELETE")
            if resp.status_code >= 400:
                LOG.error(
                    "server_notification unregistration is failed: %d.",
                    resp.status_code)
            else:
                LOG.debug(
                    "server_notification unregistration is processed: %d.",
                    resp.status_code)
        except sol_ex.SolException as e:
            # Even if unregistration is failed for a single alarm_id,
            # Unregistration should be done for remaining alarm_ids.
            LOG.error(str(e))

    def request_unregister(
            self, isall=True, vnfc_res_ids=None):
        server_notifier_uri, _, tenant = self.get_params()
        found = False
        res_ids = vnfc_res_ids if vnfc_res_ids else []
        for rsc in self.inst['instantiatedVnfInfo']['vnfcResourceInfo']:
            if ('metadata' in rsc and
                    'alarmId' in rsc['metadata'] and (isall or
                    rsc['computeResource']['resourceId'] in res_ids)):
                found = True
                alarm_id = rsc['metadata']['alarmId']
                del rsc['metadata']['alarmId']
                server_id = rsc['computeResource']['resourceId']
                self._request_unregister(
                    server_notifier_uri, tenant, server_id, alarm_id)
        return found

    def request_register_cancel(self, rsc_list):
        server_notifier_uri, _, tenant = self.get_params()
        for rsc in rsc_list:
            alarm_id = rsc['metadata']['alarmId']
            del rsc['metadata']['alarmId']
            server_id = rsc['computeResource']['resourceId']
            self._request_unregister(
                server_notifier_uri, tenant, server_id, alarm_id)

    def _request_register(self, vnfc_resource):
        server_id = vnfc_resource['computeResource']['resourceId']
        server_notifier_uri, fault_id, tenant = self.get_params()
        url = f'{server_notifier_uri}/v2/{tenant}/servers/{server_id}/alarms'
        endpoint = CONF.v2_vnfm.endpoint
        prefix = CONF.server_notification.uri_path_prefix
        _id = self.inst['id']
        fault_action = (f'{endpoint}/{prefix}/vnf_instances/{_id}/'
                        f'servers/{server_id}/notify')
        req_body = {
            'fault_action': fault_action,
            'fault_id': fault_id
        }
        resp, res_body = self.client.do_request(
            url, "POST", body=req_body)
        if resp.status_code >= 400 or 'alarm_id' not in res_body:
            msg = ("server_notification registration is "
                   f"failed: {resp.status_code}.")
            raise common_ex.MgmtDriverOtherError(error_message=msg)
        if 'metadata' not in vnfc_resource:
            vnfc_resource['metadata'] = {}
        vnfc_resource['metadata']['alarmId'] = res_body['alarm_id']
        LOG.debug(
            "server_notification registration is processed: %d. "
            "alarm_id: %s", resp.status_code, res_body['alarm_id'])
        return {'alarmId': res_body['alarm_id'], 'serverId': server_id}

    def request_register(self):
        rsc_list = []
        for rsc in self.inst['instantiatedVnfInfo']['vnfcResourceInfo']:
            if ('metadata' not in rsc or
                    'alarmId' not in rsc['metadata']):
                try:
                    self._request_register(rsc)
                    rsc_list.append(rsc)
                except sol_ex.SolException as e:
                    LOG.error(str(e))
                    self.request_register_cancel(rsc_list)
                    msg = "ServerNotification registration is failed."
                    raise common_ex.MgmtDriverOtherError(
                        error_message=msg) from e

    def get_params(self):
        server_notifier_uri = None
        fault_id = None
        tenant = None
        additional_params = self.req.get('additionalParams', None)
        if 'instantiatedVnfInfo' not in self.inst:
            return (None, None, None)
        vnf_info = self.inst['instantiatedVnfInfo']

        if (additional_params and
                'ServerNotifierUri' in additional_params and
                'ServerNotifierFaultID' in additional_params):
            server_notifier_uri = additional_params['ServerNotifierUri']
            fault_id = additional_params['ServerNotifierFaultID']
        elif (vnf_info and 'metadata' in vnf_info and
                'ServerNotifierUri' in vnf_info['metadata'] and
                'ServerNotifierFaultID' in vnf_info['metadata']):
            server_notifier_uri = vnf_info['metadata']['ServerNotifierUri']
            fault_id = vnf_info['metadata']['ServerNotifierFaultID']
        if 'vimConnectionInfo' in self.inst:
            for vim_info in self.inst['vimConnectionInfo'].values():
                if ('accessInfo' in vim_info and
                        'project' in vim_info['accessInfo']):
                    tenant = vim_info['accessInfo']['project']

        if server_notifier_uri and fault_id and tenant:
            return (server_notifier_uri, fault_id, tenant)
        return (None, None, None)

    def terminate_start(self):
        at_least_one_id_unregistered = self.request_unregister()
        if at_least_one_id_unregistered:
            self.request_remove_timer(self.inst['id'])
        for key in ['ServerNotifierUri', 'ServerNotifierFaultID']:
            if ('metadata' in self.inst['instantiatedVnfInfo'] and
                    key in self.inst['instantiatedVnfInfo']['metadata']):
                del self.inst['instantiatedVnfInfo']['metadata'][key]
        return self.make_output_dict()

    def scale_start(self):
        if self.req['type'] != 'SCALE_IN':
            return
        vnfc_res_ids = [res_def['resource']['resourceId']
                        for res_def in self.grant_req['removeResources']
                        if res_def.get('type', None) == 'COMPUTE']
        self.request_unregister(
            isall=False, vnfc_res_ids=vnfc_res_ids)
        return self.make_output_dict()

    def heal_start(self):
        isall = ('additionalParams' in self.req and
            self.req['additionalParams'].get('all', False) and
            'vnfcInstanceId' not in self.req)
        vnfc_res_ids = [res_def['resource']['resourceId']
                        for res_def in self.grant_req['removeResources']
                        if res_def.get('type', None) == 'COMPUTE']
        self.request_unregister(
            isall=isall, vnfc_res_ids=vnfc_res_ids)
        return self.make_output_dict()

    def instantiate_end(self):
        self.request_register()
        server_notifier_uri, fault_id, _ = self.get_params()
        vnf_info = self.inst['instantiatedVnfInfo']
        if 'metadata' not in vnf_info:
            vnf_info['metadata'] = {}
        vnf_info['metadata']['ServerNotifierUri'] = server_notifier_uri
        vnf_info['metadata']['ServerNotifierFaultID'] = fault_id
        return self.make_output_dict()

    def scale_end(self):
        if self.req['type'] != 'SCALE_OUT':
            return
        self.request_register()
        return self.make_output_dict()

    def heal_end(self):
        self.request_register()
        return self.make_output_dict()

    def instantiate_start(self):
        pass

    def terminate_end(self):
        pass


def main():
    script_dict = pickle.load(sys.stdin.buffer)

    operation = script_dict['operation']
    req = script_dict['request']
    inst = script_dict['vnf_instance']
    grant_req = script_dict['grant_request']
    grant = script_dict['grant_response']
    csar_dir = script_dict['tmp_csar_dir']

    script = ServerNotificationMgmtDriver(
        req, inst, grant_req, grant, csar_dir)
    output_dict = getattr(script, operation)()
    sys.stdout.buffer.write(pickle.dumps(output_dict))
    sys.stdout.flush()


if __name__ == "__main__":
    try:
        main()
        os._exit(0)
    except Exception as ex:
        sys.stderr.write(str(ex))
        sys.stderr.flush()
        os._exit(1)
