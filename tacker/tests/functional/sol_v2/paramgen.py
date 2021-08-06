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

from oslo_utils import uuidutils


def sample1_create(vnfd_id):
    return {
        "vnfdId": vnfd_id,
        "vnfInstanceName": "sample1",
        "vnfInstanceDescription": "test sample1"
    }


def sample1_terminate():
    return {
        "terminationType": "FORCEFUL"
    }


def sample1_instantiate(net_ids, subnet_ids, auth_url):
    ext_vl_1 = {
        "id": uuidutils.generate_uuid(),
        "resourceId": net_ids['net0'],
        "extCps": [
            {
                "cpdId": "VDU1_CP1",
                "cpConfig": {
                    "VDU1_CP1_1": {
                        "cpProtocolData": [{
                            "layerProtocol": "IP_OVER_ETHERNET",
                            "ipOverEthernet": {
                                "ipAddresses": [{
                                    "type": "IPV4",
                                    "numDynamicAddresses": 1}]}}]}
                }
            },
            {
                "cpdId": "VDU2_CP1",
                "cpConfig": {
                    "VDU2_CP1_1": {
                        "cpProtocolData": [{
                            "layerProtocol": "IP_OVER_ETHERNET",
                            "ipOverEthernet": {
                                "ipAddresses": [{
                                    "type": "IPV4",
                                    "fixedAddresses": ["10.10.0.101"]}]}}]}
                }
            }
        ],
    }
    ext_vl_2 = {
        "id": uuidutils.generate_uuid(),
        "resourceId": net_ids['net1'],
        "extCps": [
            {
                "cpdId": "VDU1_CP2",
                "cpConfig": {
                    "VDU1_CP2_1": {
                        "cpProtocolData": [{
                            "layerProtocol": "IP_OVER_ETHERNET",
                            "ipOverEthernet": {
                                "ipAddresses": [{
                                    "type": "IPV4",
                                    "numDynamicAddresses": 1,
                                    "subnetId": subnet_ids['subnet1']}]}}]}
                }
            },
            {
                "cpdId": "VDU2_CP2",
                "cpConfig": {
                    "VDU2_CP2_1": {
                        "cpProtocolData": [{
                            "layerProtocol": "IP_OVER_ETHERNET",
                            "ipOverEthernet": {
                                "ipAddresses": [{
                                    "type": "IPV4",
                                    "fixedAddresses": ["10.10.1.101"],
                                    "subnetId": subnet_ids['subnet1']}]}}]}
                }
            }
        ]
    }

    return {
        "flavourId": "simple",
        "instantiationLevelId": "instantiation_level_1",
        "extVirtualLinks": [
            ext_vl_1,
            ext_vl_2
        ],
        "extManagedVirtualLinks": [
            {
                "id": uuidutils.generate_uuid(),
                "vnfVirtualLinkDescId": "internalVL1",
                "resourceId": net_ids['net_mgmt']
            },
        ],
        "vimConnectionInfo": {
            "vim1": {
                "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_3",
                "vimId": uuidutils.generate_uuid(),
                "interfaceInfo": {"endpoint": auth_url},
                "accessInfo": {
                    "username": "nfv_user",
                    "region": "RegionOne",
                    "password": "devstack",
                    "project": "nfv",
                    "projectDomain": "Default",
                    "userDomain": "Default"
                }
            }
        }
    }


def sample2_create(vnfd_id):
    return {
        "vnfdId": vnfd_id,
        "vnfInstanceName": "sample2",
        "vnfInstanceDescription": "test sample2"
    }


def sample2_terminate():
    return {
        "terminationType": "GRACEFUL",
        "gracefulTerminationTimeout": 5
    }


def sample2_instantiate(net_ids, subnet_ids, auth_url):
    ext_vl_1 = {
        "id": uuidutils.generate_uuid(),
        "resourceId": net_ids['net0'],
        "extCps": [
            {
                "cpdId": "VDU1_CP1",
                "cpConfig": {
                    "VDU1_CP1_1": {
                        "cpProtocolData": [{
                            "layerProtocol": "IP_OVER_ETHERNET",
                            "ipOverEthernet": {
                                "ipAddresses": [{
                                    "type": "IPV4",
                                    "numDynamicAddresses": 1}]}}]}
                }
            },
            {
                "cpdId": "VDU2_CP1",
                "cpConfig": {
                    "VDU2_CP1_1": {
                        "cpProtocolData": [{
                            "layerProtocol": "IP_OVER_ETHERNET",
                            "ipOverEthernet": {
                                "ipAddresses": [{
                                    "type": "IPV4",
                                    "fixedAddresses": ["10.10.0.102"]}]}}]}
                }
            }
        ],
    }
    ext_vl_2 = {
        "id": uuidutils.generate_uuid(),
        "resourceId": net_ids['net1'],
        "extCps": [
            {
                "cpdId": "VDU1_CP2",
                "cpConfig": {
                    "VDU1_CP2_1": {
                        "cpProtocolData": [{
                            "layerProtocol": "IP_OVER_ETHERNET",
                            "ipOverEthernet": {
                                "ipAddresses": [{
                                    "type": "IPV4",
                                    "numDynamicAddresses": 1,
                                    "subnetId": subnet_ids['subnet1']}]}}]}
                }
            },
            {
                "cpdId": "VDU2_CP2",
                "cpConfig": {
                    "VDU2_CP2_1": {
                        "cpProtocolData": [{
                            "layerProtocol": "IP_OVER_ETHERNET",
                            "ipOverEthernet": {
                                "ipAddresses": [{
                                    "type": "IPV4",
                                    "fixedAddresses": ["10.10.1.102"],
                                    "subnetId": subnet_ids['subnet1']}]}}]}
                }
            }
        ]
    }

    return {
        "flavourId": "simple",
        "instantiationLevelId": "instantiation_level_1",
        "extVirtualLinks": [
            ext_vl_1,
            ext_vl_2
        ],
        "extManagedVirtualLinks": [
            {
                "id": uuidutils.generate_uuid(),
                "vnfVirtualLinkDescId": "internalVL1",
                "resourceId": net_ids['net_mgmt']
            },
        ],
        "vimConnectionInfo": {
            "vim1": {
                "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_3",
                "vimId": uuidutils.generate_uuid(),
                "interfaceInfo": {"endpoint": auth_url},
                "accessInfo": {
                    "username": "nfv_user",
                    "region": "RegionOne",
                    "password": "devstack",
                    "project": "nfv",
                    "projectDomain": "Default",
                    "userDomain": "Default"
                }
            }
        },
        "additionalParams": {
            "lcm-operation-user-data": "./UserData/userdata_default.py",
            "lcm-operation-user-data-class": "DefaultUserData"
        }
    }
