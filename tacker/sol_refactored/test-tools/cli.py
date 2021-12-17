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

import json
import os
import sys

from tacker.sol_refactored.common import http_client


# NOTE: This is the tool which intended to use it about APIs under development.
# This is not maintained at all, but reuse the code for the new APIs
# development.

auth_url = "http://127.0.0.1/identity/v3"
username = "nfv_user"
password = "devstack"
project_name = "nfv"
domain_name = "Default"
user_domain_name = "Default"
project_domain_name = "Default"


class Client(object):

    def __init__(self, path):
        self.path = path
        self.auth = http_client.KeystonePasswordAuthHandle(
            auth_url=auth_url,
            username=username,
            password=password,
            project_name=project_name,
            user_domain_name=user_domain_name,
            project_domain_name=project_domain_name)

        self.client = http_client.HttpClient(self.auth)

    def print(self, resp, body):
        print(resp.status_code)
        print(resp.headers)
        print()
        print(body)

    def create(self, req_body):
        resp, body = self.client.do_request(
            self.path, "POST", body=req_body, version="2.0.0")
        self.print(resp, body)

    def list(self, req_body):
        if req_body is not None:
            resp, body = self.client.do_request(
                self.path, "GET", version="2.0.0", params=req_body)
        else:
            resp, body = self.client.do_request(
                self.path, "GET", version="2.0.0")
        self.print(resp, body)

    def show(self, id):
        resp, body = self.client.do_request(
            self.path + '/' + id, "GET", version="2.0.0")
        self.print(resp, body)

    def delete(self, id):
        resp, body = self.client.do_request(
            self.path + '/' + id, "DELETE", version="2.0.0")
        self.print(resp, body)

    def inst(self, id, req_body):
        path = self.path + '/' + id + '/instantiate'
        resp, body = self.client.do_request(
            path, "POST", body=req_body, version="2.0.0")
        self.print(resp, body)

    def term(self, id, req_body):
        path = self.path + '/' + id + '/terminate'
        resp, body = self.client.do_request(
            path, "POST", body=req_body, version="2.0.0")
        self.print(resp, body)

    def retry(self, id):
        path = self.path + '/' + id + '/retry'
        resp, body = self.client.do_request(path, "POST", version="2.0.0")
        self.print(resp, body)


def usage():
    print("usage: cli resource action [arg...]")
    print("  inst create body(path of content)")
    print("  inst list [body(path of content)]")
    print("  inst show {id}")
    print("  inst delete {id}")
    print("  inst inst {id} body(path of content)")
    print("  inst term {id} body(path of content)")
    print("  subsc create body(path of content)")
    print("  subsc list [body(path of content)]")
    print("  subsc show {id}")
    print("  subsc delete {id}")
    print("  lcmocc list [body(path of content)]")
    print("  lcmocc show {id}")
    print("  lcmocc delete {id}")
    print("  lcmocc retry {id}")
    os._exit(1)


def get_body(arg):
    with open(arg) as fp:
        return json.load(fp)


if __name__ == '__main__':
    if len(sys.argv) < 3:
        usage()
    resource = sys.argv[1]
    action = sys.argv[2]

    if resource == "inst":
        if action not in ["create", "list", "show", "delete", "inst", "term"]:
            usage()
        client = Client("/vnflcm/v2/vnf_instances")
    elif resource == "subsc":
        if action not in ["create", "list", "show", "delete"]:
            usage()
        client = Client("/vnflcm/v2/subscriptions")
    elif resource == "lcmocc":
        if action not in ["list", "show", "delete", "retry"]:
            usage()
        client = Client("/vnflcm/v2/vnf_lcm_op_occs")
    else:
        usage()

    if action == "create":
        if len(sys.argv) != 4:
            usage()
        client.create(get_body(sys.argv[3]))
    elif action == "list":
        body = None
        if len(sys.argv) == 4:
            body = get_body(sys.argv[3])
        elif len(sys.argv) != 3:
            usage()
        client.list(body)
    elif action == "show":
        if len(sys.argv) != 4:
            usage()
        client.show(sys.argv[3])
    elif action == "delete":
        if len(sys.argv) != 4:
            usage()
        client.delete(sys.argv[3])
    elif action == "inst":
        if len(sys.argv) != 5:
            usage()
        client.inst(sys.argv[3], get_body(sys.argv[4]))
    elif action == "term":
        if len(sys.argv) != 5:
            usage()
        client.term(sys.argv[3], get_body(sys.argv[4]))
    elif action == "retry":
        if len(sys.argv) != 4:
            usage()
        client.retry(sys.argv[3])
