# Copyright (C) 2019 NTT DATA
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
from tacker.common import topics
from tacker.objects import base as objects_base


class VNFPackageRPCAPI(object):

    target = oslo_messaging.Target(
        exchange='tacker',
        topic=topics.TOPIC_CONDUCTOR,
        fanout=False,
        version='1.0')

    def upload_vnf_package_content(self, context, vnf_package, cast=True):
        serializer = objects_base.TackerObjectSerializer()

        client = rpc.get_client(self.target, version_cap=None,
                                serializer=serializer)
        cctxt = client.prepare()
        rpc_method = cctxt.cast if cast else cctxt.call
        return rpc_method(context, 'upload_vnf_package_content',
                          vnf_package=vnf_package)

    def upload_vnf_package_from_uri(self, context, vnf_package,
                                    address_information, user_name=None,
                                    password=None, cast=True):
        serializer = objects_base.TackerObjectSerializer()

        client = rpc.get_client(self.target, version_cap=None,
                                serializer=serializer)
        cctxt = client.prepare()
        rpc_method = cctxt.cast if cast else cctxt.call
        return rpc_method(context, 'upload_vnf_package_from_uri',
                          vnf_package=vnf_package,
                          address_information=address_information,
                          user_name=user_name, password=password)

    def delete_vnf_package(self, context, vnf_package, cast=True):
        serializer = objects_base.TackerObjectSerializer()

        client = rpc.get_client(self.target, version_cap=None,
                                serializer=serializer)
        cctxt = client.prepare()
        rpc_method = cctxt.cast if cast else cctxt.call
        return rpc_method(context, 'delete_vnf_package',
                          vnf_package=vnf_package)

    def get_vnf_package_vnfd(self, context, vnf_package, cast=False):
        serializer = objects_base.TackerObjectSerializer()
        client = rpc.get_client(self.target, version_cap=None,
                                serializer=serializer)
        cctxt = client.prepare()
        rpc_method = cctxt.cast if cast else cctxt.call
        return rpc_method(context, 'get_vnf_package_vnfd',
                          vnf_package=vnf_package)
