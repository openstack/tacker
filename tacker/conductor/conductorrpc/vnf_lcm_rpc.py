# Copyright (C) 2020 NTT DATA
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


class VNFLcmRPCAPI(object):

    target = oslo_messaging.Target(
        exchange='tacker',
        topic=topics.TOPIC_CONDUCTOR,
        fanout=False,
        version='1.0')

    def instantiate(self, context, vnf_instance, vnf,
                    instantiate_vnf, vnf_lcm_op_occs_id,
                    cast=True):
        serializer = objects_base.TackerObjectSerializer()

        client = rpc.get_client(self.target, version_cap=None,
                                serializer=serializer)
        cctxt = client.prepare()
        rpc_method = cctxt.cast if cast else cctxt.call
        return rpc_method(context, 'instantiate',
                          vnf_instance=vnf_instance,
                          vnf_dict=vnf,
                          instantiate_vnf=instantiate_vnf,
                          vnf_lcm_op_occs_id=vnf_lcm_op_occs_id)

    def terminate(self, context, vnf_instance, vnf,
                terminate_vnf_req, vnf_lcm_op_occs_id,
                cast=True):
        serializer = objects_base.TackerObjectSerializer()

        client = rpc.get_client(self.target, version_cap=None,
                                serializer=serializer)
        cctxt = client.prepare()
        rpc_method = cctxt.cast if cast else cctxt.call
        return rpc_method(context, 'terminate',
                          vnf_lcm_op_occs_id=vnf_lcm_op_occs_id,
                          vnf_instance=vnf_instance,
                          terminate_vnf_req=terminate_vnf_req,
                          vnf_dict=vnf)

    def heal(self, context, vnf_instance, vnf_dict, heal_vnf_request,
             vnf_lcm_op_occs_id, cast=True):
        serializer = objects_base.TackerObjectSerializer()

        client = rpc.get_client(self.target, version_cap=None,
                                serializer=serializer)
        cctxt = client.prepare()
        rpc_method = cctxt.cast if cast else cctxt.call
        return rpc_method(context, 'heal',
                          vnf_instance=vnf_instance,
                          vnf_dict=vnf_dict,
                          heal_vnf_request=heal_vnf_request,
                          vnf_lcm_op_occs_id=vnf_lcm_op_occs_id)

    def update(self, context, vnf_lcm_opoccs, body_data,
            vnfd_pkg_data, vnfd_id, cast=True):
        serializer = objects_base.TackerObjectSerializer()

        client = rpc.get_client(self.target, version_cap=None,
                                serializer=serializer)
        cctxt = client.prepare()
        rpc_method = cctxt.cast if cast else cctxt.call
        return rpc_method(context, 'update',
                          vnf_lcm_opoccs=vnf_lcm_opoccs,
                          body_data=body_data,
                          vnfd_pkg_data=vnfd_pkg_data,
                          vnfd_id=vnfd_id)

    def scale(
            self,
            context,
            vnf_info,
            vnf_instance,
            scale_vnf_request,
            cast=True):
        serializer = objects_base.TackerObjectSerializer()

        client = rpc.get_client(self.target, version_cap=None,
                                serializer=serializer)
        cctxt = client.prepare()
        rpc_method = cctxt.cast if cast else cctxt.call
        return rpc_method(context, 'scale',
                          vnf_info=vnf_info,
                          vnf_instance=vnf_instance,
                          scale_vnf_request=scale_vnf_request)

    def send_notification(self, context, notification, cast=True):
        serializer = objects_base.TackerObjectSerializer()

        client = rpc.get_client(self.target, version_cap=None,
                                serializer=serializer)
        cctxt = client.prepare()
        rpc_method = cctxt.cast if cast else cctxt.call
        return rpc_method(context, 'send_notification',
                          notification=notification)

    def rollback(self, context, vnf_info, vnf_instance,
            operation_params, cast=True):
        serializer = objects_base.TackerObjectSerializer()

        client = rpc.get_client(self.target, version_cap=None,
                                serializer=serializer)
        cctxt = client.prepare()
        rpc_method = cctxt.cast if cast else cctxt.call
        return rpc_method(context, 'rollback',
                          vnf_info=vnf_info,
                          vnf_instance=vnf_instance,
                          operation_params=operation_params)
