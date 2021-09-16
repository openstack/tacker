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

from oslo_log import log as logging
from oslo_service import loopingcall

from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.common import http_client


LOG = logging.getLogger(__name__)


CHECK_INTERVAL = 5


class HeatClient(object):

    def __init__(self, vim_info):
        auth = http_client.KeystonePasswordAuthHandle(
            auth_url=vim_info.interfaceInfo['endpoint'],
            username=vim_info.accessInfo['username'],
            password=vim_info.accessInfo['password'],
            project_name=vim_info.accessInfo['project'],
            user_domain_name=vim_info.accessInfo['userDomain'],
            project_domain_name=vim_info.accessInfo['projectDomain']
        )
        self.client = http_client.HttpClient(auth,
                                             service_type='orchestration')

    def create_stack(self, fields):
        path = "stacks"
        resp, body = self.client.do_request(path, "POST",
                expected_status=[201], body=fields)

    def delete_stack(self, stack_name):
        path = "stacks/{}".format(stack_name)
        resp, body = self.client.do_request(path, "DELETE",
                expected_status=[204, 404])

    def get_status(self, stack_name):
        path = "stacks/{}".format(stack_name)
        resp, body = self.client.do_request(path, "GET",
                expected_status=[200, 404])

        if resp.status_code == 404:
            return None, None

        return (body["stack"]["stack_status"],
                body["stack"]["stack_status_reason"])

    def get_resources(self, stack_name):
        # NOTE: Because it is necessary to get nested stack info, it is
        # necessary to specify 'nested_depth=2'.
        path = "stacks/{}/resources?nested_depth=2".format(stack_name)
        resp, body = self.client.do_request(path, "GET",
                expected_status=[200])

        return body['resources']

    def _wait_completion(self, stack_name, operation, complete_status,
            progress_status, failed_status, none_is_done=False):
        # NOTE: timeout is specified for each stack operation. so it is
        # not forever loop.
        def _check_status():
            status, status_reason = self.get_status(stack_name)
            if (status == complete_status or
                    (status is None and none_is_done)):
                LOG.info("%s %s done.", operation, stack_name)
                raise loopingcall.LoopingCallDone()
            elif status == failed_status:
                LOG.error("% %s failed.", operation, stack_name)
                sol_title = "%s failed" % operation
                raise sol_ex.StackOperationFailed(sol_title=sol_title,
                                                  sol_detail=status_reason)
            elif status != progress_status:
                LOG.error("%s %s failed. status: %s", operation,
                          stack_name, status)
                sol_title = "%s failed" % operation
                raise sol_ex.StackOperationFailed(sol_title=sol_title,
                                                  sol_detail='Unknown error')
            LOG.debug("%s %s %s", operation, stack_name, progress_status)

        timer = loopingcall.FixedIntervalLoopingCall(_check_status)
        timer.start(interval=CHECK_INTERVAL).wait()

    def wait_stack_create(self, stack_name):
        self._wait_completion(stack_name, "Stack create",
            "CREATE_COMPLETE", "CREATE_IN_PROGRESS", "CREATE_FAILED")

    def wait_stack_delete(self, stack_name):
        self._wait_completion(stack_name, "Stack delete",
            "DELETE_COMPLETE", "DELETE_IN_PROGRESS", "DELETE_FAILED",
            none_is_done=True)


def get_reses_by_types(heat_reses, types):
    return [res for res in heat_reses if res['resource_type'] in types]


def get_server_reses(heat_reses):
    return get_reses_by_types(heat_reses, ['OS::Nova::Server'])


def get_network_reses(heat_reses):
    return get_reses_by_types(heat_reses, ['OS::Neutron::Net'])


def get_storage_reses(heat_reses):
    return get_reses_by_types(heat_reses, ['OS::Cinder::Volume'])


def get_port_reses(heat_reses):
    return get_reses_by_types(heat_reses, ['OS::Neutron::Port'])


def get_stack_name(inst):
    return "vnf-" + inst.id
