# Copyright (C) 2022 FUJITSU
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

import datetime
from kubernetes import client
import os

from tacker import objects
from tacker.objects import fields
from tacker.tests import uuidsentinel


def get_vnf_instance_object(
        instantiation_state=fields.VnfInstanceState.NOT_INSTANTIATED):

    inst_vnf_info = get_vnf_instantiated_info()

    vnf_instance = objects.VnfInstance(
        id=uuidsentinel.vnf_instance_id,
        vnf_instance_name="Test-Vnf-Instance",
        vnf_instance_description="vnf instance description",
        instantiation_state=instantiation_state, vnfd_id=uuidsentinel.vnfd_id,
        vnf_provider="sample provider", vnf_product_name="vnf product name",
        vnf_software_version='1.0', vnfd_version="2",
        instantiated_vnf_info=inst_vnf_info,
        vnf_metadata={"namespace": "default"}
    )

    return vnf_instance


def get_vnf_instantiated_info(flavour_id='simple',
        instantiation_level_id=None, vnfc_resource_info=None,
        virtual_storage_resource_info=None,
        vnf_virtual_link_resource_info=None,
        ext_managed_virtual_link_info=None,
        ext_virtual_link_info=None,
        ext_cp_info=None):

    vnfc_resource_info = vnfc_resource_info or []
    vnf_virtual_link_resource_info = vnf_virtual_link_resource_info or []
    virtual_storage_resource_info = virtual_storage_resource_info or []
    ext_managed_virtual_link_info = ext_managed_virtual_link_info or []
    ext_virtual_link_info = ext_virtual_link_info or []
    ext_cp_info = ext_cp_info or []

    inst_vnf_info = objects.InstantiatedVnfInfo(
        flavour_id=flavour_id,
        instantiation_level_id=instantiation_level_id,
        instance_id='9693ab84-6da8-5926-5e7a-3a1b963156c0',
        vnfc_resource_info=vnfc_resource_info,
        vnf_virtual_link_resource_info=vnf_virtual_link_resource_info,
        virtual_storage_resource_info=virtual_storage_resource_info,
        ext_managed_virtual_link_info=ext_managed_virtual_link_info,
        ext_virtual_link_info=ext_virtual_link_info,
        ext_cp_info=ext_cp_info,
        additional_params=return_cnf_additional_params())

    return inst_vnf_info


def fake_pod():
    return client.V1Pod(
        api_version='v1',
        kind='Pod',
        metadata=client.V1ObjectMeta(
            name='curry-test001',
            namespace='curryns'
        ),
        spec=client.V1PodSpec(
            containers=[
                client.V1Container(
                    image="curry",
                    name="curry"
                )
            ]
        ),
        status=client.V1PodStatus(
            phase='Running',
        )
    )


def fake_list_pod():
    return client.V1PodList(
        items=[
            client.V1Pod(
                api_version='v1',
                kind='Pod',
                metadata=client.V1ObjectMeta(
                    name='curry-test001',
                    namespace='curryns'
                ),
                spec=client.V1PodSpec(
                    containers=[
                        client.V1Container(
                            image="curry",
                            name="curry"
                        )
                    ]
                ),
                status=client.V1PodStatus(
                    phase='Pending',
                )
            )
        ]
    )


def get_fake_pod_info(kind, name='fake_name', pod_status='Running',
                      pod_name=None):
    if not pod_name:
        if kind == 'Deployment':
            pod_name = _('{name}-1234567890-abcde').format(name=name)
        elif kind in ('ReplicaSet', 'DaemonSet'):
            pod_name = _('{name}-12345').format(name=name)
        elif kind == 'StatefulSet':
            pod_name = _('{name}-1').format(name=name)
        elif kind == 'Pod':
            pod_name = name
    return client.V1Pod(
        metadata=client.V1ObjectMeta(
            name=pod_name,
            creation_timestamp=datetime.datetime.now().isoformat('T')),
        status=client.V1PodStatus(phase=pod_status))


def vnfd_dict_cnf():
    tacker_dir = os.getcwd()
    def_dir = tacker_dir + "/samples/vnf_packages/Definitions/"
    vnfd_dict = {
        "tosca_definitions_version": "tosca_simple_yaml_1_2",
        "description": "Sample VNF flavour for Sample VNF",
        "imports": [
            def_dir + "etsi_nfv_sol001_common_types.yaml",
            def_dir + "etsi_nfv_sol001_vnfd_types.yaml",
            def_dir + "helloworld3_types.yaml"],
        "topology_template": {
            "node_templates": {
                "VNF": {
                    "type": "company.provider.VNF",
                    "properties": {
                        "flavour_description": "A simple flavour"}},
                "VDU1": {
                    "type": "tosca.nodes.nfv.Vdu.Compute",
                    "properties": {
                        "name": "vdu1",
                        "description": "vdu1 compute node",
                        "vdu_profile": {
                            "min_number_of_instances": 1,
                            "max_number_of_instances": 3}}}},
            "policies": [
                {
                    "scaling_aspects": {
                        "type": "tosca.policies.nfv.ScalingAspects",
                        "properties": {
                            "aspects": {
                                "vdu1_aspect": {
                                    "name": "vdu1_aspect",
                                    "description": "vdu1 scaling aspect",
                                    "max_scale_level": 2,
                                    "step_deltas": ["delta_1"]}}}}},
                {
                    "vdu1_initial_delta": {
                        "type": "tosca.policies.nfv.VduInitialDelta",
                        "properties": {
                            "initial_delta": {
                                "number_of_instances": 0}},
                        "targets": ["VDU1"]}},
                {
                    "vdu1_scaling_aspect_deltas": {
                        "type": "tosca.policies.nfv.VduScalingAspectDeltas",
                        "properties": {
                            "aspect": "vdu1_aspect",
                            "deltas": {
                                "delta_1": {
                                    "number_of_instances": 1}}},
                        "targets": ["VDU1"]}},
                {
                    "instantiation_levels": {
                        "type": "tosca.policies.nfv.InstantiationLevels",
                        "properties": {
                            "levels": {
                                "instantiation_level_1": {
                                    "description": "Smallest size",
                                    "scale_info": {
                                        "vdu1_aspect": {
                                            "scale_level": 0}}},
                                "instantiation_level_2": {
                                    "description": "Largest size",
                                    "scale_info": {
                                        "vdu1_aspect": {
                                            "scale_level": 2}}}
                            },
                            "default_level": "instantiation_level_1"}}},
                {
                    "vdu1_instantiation_levels": {
                        "type": "tosca.policies.nfv.VduInstantiationLevels",
                        "properties": {
                            "levels": {
                                "instantiation_level_1": {
                                    "number_of_instances": 0},
                                "instantiation_level_2": {
                                    "number_of_instances": 2}}},
                        "targets": ["VDU1"]}}
            ]
        }
    }
    return vnfd_dict


def return_cnf_additional_params():
    additional_params = {
        "lcm-kubernetes-def-files": [
            "Files/kubernetes/configmap_1.yaml",
            "Files/kubernetes/pod_volume.yaml",
            "Files/kubernetes/replicaset.yaml",
            "Files/kubernetes/secret_1.yaml"
        ],
        "namespace": "default"
    }
    return additional_params
