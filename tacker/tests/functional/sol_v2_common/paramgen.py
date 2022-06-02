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


def sub_create_min(callback_uri):
    # Omit except for required attributes
    # NOTE: Only the following cardinality attributes are set.
    #  - 1
    #  - 1..N (1)
    return {
        "callbackUri": callback_uri
    }


def sub_create_max(callback_uri):
    # All attributes are set.
    # NOTE: All of the following cardinality attributes are set.
    # In addition, 0..N or 1..N attributes are set to 2 or more.
    #  - 0..1 (1)
    #  - 0..N (2 or more)
    #  - 1
    #  - 1..N (2 or more)
    vnf_provider_1 = {
        "vnfProvider": "dummy-vnfProvider-1",
        "vnfProducts": [
            {
                "vnfProductName": "dummy-vnfProductName-1-1",
                "versions": [
                    {
                        "vnfSoftwareVersion": 1.0,
                        "vnfdVersions": [1.0, 2.0]
                    },
                    {
                        "vnfSoftwareVersion": 1.1,
                        "vnfdVersions": [1.1, 2.1]
                    },
                ]
            },
            {
                "vnfProductName": "dummy-vnfProductName-1-2",
                "versions": [
                    {
                        "vnfSoftwareVersion": 1.0,
                        "vnfdVersions": [1.0, 2.0]
                    },
                    {
                        "vnfSoftwareVersion": 1.1,
                        "vnfdVersions": [1.1, 2.1]
                    },
                ]
            }
        ]
    }
    vnf_provider_2 = {
        "vnfProvider": "dummy-vnfProvider-2",
        "vnfProducts": [
            {
                "vnfProductName": "dummy-vnfProductName-2-1",
                "versions": [
                    {
                        "vnfSoftwareVersion": 1.0,
                        "vnfdVersions": [1.0, 2.0]
                    },
                    {
                        "vnfSoftwareVersion": 1.1,
                        "vnfdVersions": [1.1, 2.1]
                    },
                ]
            },
            {
                "vnfProductName": "dummy-vnfProductName-2-2",
                "versions": [
                    {
                        "vnfSoftwareVersion": 1.0,
                        "vnfdVersions": [1.0, 2.0]
                    },
                    {
                        "vnfSoftwareVersion": 1.1,
                        "vnfdVersions": [1.1, 2.1]
                    },
                ]
            }
        ]
    }

    # NOTE: The following is omitted because authType is BASIC in this case
    #  - "paramsOauth2ClientCredentials"
    return {
        "filter": {
            "vnfInstanceSubscriptionFilter": {
                "vnfdIds": [
                    "dummy-vnfdId-1",
                    "dummy-vnfdId-2"
                ],
                "vnfProductsFromProviders": [
                    vnf_provider_1,
                    vnf_provider_2
                ],
                "vnfInstanceIds": [
                    "dummy-vnfInstanceId-1",
                    "dummy-vnfInstanceId-2"
                ],
                "vnfInstanceNames": [
                    "dummy-vnfInstanceName-1",
                    "dummy-vnfInstanceName-2"
                ]
            },
            "notificationTypes": [
                "VnfLcmOperationOccurrenceNotification",
                "VnfIdentifierCreationNotification",
                "VnfLcmOperationOccurrenceNotification"
            ],
            "operationTypes": [
                "INSTANTIATE",
                "SCALE",
                "TERMINATE",
                "HEAL",
                "MODIFY_INFO",
                "CHANGE_EXT_CONN"
            ],
            "operationStates": [
                "COMPLETED",
                "FAILED",
                "FAILED_TEMP",
                "PROCESSING",
                "ROLLING_BACK",
                "ROLLED_BACK",
                "STARTING"
            ]
        },
        "callbackUri": callback_uri,
        "authentication": {
            "authType": [
                "BASIC"
            ],
            "paramsBasic": {
                "password": "test_pass",
                "userName": "test_user"
            },
            # "paramsOauth2ClientCredentials": omitted,
        },
        "verbosity": "SHORT"
    }


def create_vnf_max(vnfd_id):
    # All attributes are set.
    # NOTE: All of the following cardinality attributes are set.
    # In addition, 0..N or 1..N attributes are set to 2 or more.
    #  - 0..1 (1)
    #  - 0..N (2 or more)
    #  - 1
    #  - 1..N (2 or more)
    return {
        "vnfdId": vnfd_id,
        "vnfInstanceName": "sample",
        "vnfInstanceDescription": "test sample",
        "metadata": {"dummy-key": "dummy-val"}
    }


def terminate_vnf_max():
    # All attributes are set.
    # NOTE: All of the following cardinality attributes are set.
    # In addition, 0..N or 1..N attributes are set to 2 or more.
    #  - 0..1 (1)
    #  - 0..N (2 or more)
    #  - 1
    #  - 1..N (2 or more)
    return {
        "terminationType": "GRACEFUL",
        "gracefulTerminationTimeout": 5,
        "additionalParams": {"dummy-key": "dummy-val"}
    }


def instantiate_vnf_max(net_ids, subnets, ports, auth_url):
    # All attributes are set.
    # NOTE: All of the following cardinality attributes are set.
    # In addition, 0..N or 1..N attributes are set to 2 or more.
    #  - 0..1 (1)
    #  - 0..N (2 or more)
    #  - 1
    #  - 1..N (2 or more)

    vim_id_1 = uuidutils.generate_uuid()
    vim_id_2 = uuidutils.generate_uuid()
    link_port_id_1 = uuidutils.generate_uuid()
    link_port_id_2 = uuidutils.generate_uuid()

    # NOTE: The following is not supported so it is omitted
    #  - "segmentationId"
    #  - "addressRange"
    #  - Multiple "cpProtocolData"
    #  - Multiple "fixedAddresses"
    ext_vl_1 = {
        "id": uuidutils.generate_uuid(),
        "vimConnectionId": vim_id_1,
        "resourceProviderId": "Company",
        "resourceId": net_ids['net0'],
        "extCps": [
            {
                "cpdId": "VDU1_CP1",
                "cpConfig": {
                    "VDU1_CP1": {
                        "parentCpConfigId": uuidutils.generate_uuid(),
                        # "linkPortId": omitted,
                        "cpProtocolData": [{
                            "layerProtocol": "IP_OVER_ETHERNET",
                            "ipOverEthernet": {
                                # "macAddress": omitted,
                                # "segmentationId": omitted,
                                "ipAddresses": [{
                                    "type": "IPV4",
                                    # "fixedAddresses": omitted,
                                    "numDynamicAddresses": 1,
                                    # "addressRange": omitted,
                                    "subnetId": subnets['subnet0']}]}}]
                    },
                    # { "VDU1_CP1_2": omitted }
                }
            },
            {
                "cpdId": "VDU2_CP1-1",
                "cpConfig": {
                    "VDU2_CP1-1": {
                        "parentCpConfigId": uuidutils.generate_uuid(),
                        "linkPortId": link_port_id_1,
                        "cpProtocolData": [{
                            "layerProtocol": "IP_OVER_ETHERNET",
                            "ipOverEthernet": {
                                # "macAddress": omitted,
                                # "segmentationId": omitted,
                                "ipAddresses": [{
                                    "type": "IPV4",
                                    # "fixedAddresses": omitted,
                                    "numDynamicAddresses": 1,
                                    # "addressRange": omitted,
                                    "subnetId": subnets['subnet0']
                                }]
                            }
                        }]
                    },
                    # { "VDU2_CP1_2": omitted }
                }
            },
            {
                "cpdId": "VDU2_CP1-2",
                "cpConfig": {
                    "VDU2_CP1-2": {
                        "parentCpConfigId": uuidutils.generate_uuid(),
                        "linkPortId": link_port_id_2,
                        "cpProtocolData": [{
                            "layerProtocol": "IP_OVER_ETHERNET",
                            "ipOverEthernet": {
                                # "macAddress": omitted,
                                # "segmentationId": omitted,
                                "ipAddresses": [{
                                    "type": "IPV4",
                                    # "fixedAddresses": omitted,
                                    "numDynamicAddresses": 1,
                                    # "addressRange": omitted,
                                    "subnetId": subnets['subnet0']
                                }]
                            }
                        }]
                    },
                    # { "VDU2_CP1_2": omitted }
                }
            }
        ],
        "extLinkPorts": [
            {
                "id": link_port_id_1,
                "resourceHandle": {
                    "resourceId": ports['VDU2_CP1-1']
                }
            },
            # NOTE: Set dummy value because it is set by "additionalParams"
            {
                "id": link_port_id_2,
                "resourceHandle": {
                    "resourceId": "dummy-id"
                }
            }
        ]
    }

    # NOTE: The following is not supported so it is omitted
    #  - "segmentationId"
    #  - "addressRange"
    #  - Multiple "cpProtocolData"
    #  - Multiple "fixedAddresses"
    ext_vl_2 = {
        "id": uuidutils.generate_uuid(),
        "vimConnectionId": vim_id_1,
        "resourceProviderId": "Company",
        "resourceId": net_ids['ft-net0'],
        "extCps": [
            {
                "cpdId": "VDU1_CP2",
                "cpConfig": {
                    "VDU1_CP2": {
                        "parentCpConfigId": uuidutils.generate_uuid(),
                        # "linkPortId": omitted,
                        "cpProtocolData": [{
                            "layerProtocol": "IP_OVER_ETHERNET",
                            "ipOverEthernet": {
                                # "macAddress": omitted,
                                # "segmentationId": omitted,
                                "ipAddresses": [{
                                    "type": "IPV4",
                                    # "fixedAddresses": omitted,
                                    "numDynamicAddresses": 1,
                                    # "addressRange": omitted,
                                    "subnetId": subnets['ft-ipv4-subnet0']}
                                ]}
                        }]
                    },
                    # { "VDU1_CP2_2": omitted }
                }
            },
            {
                "cpdId": "VDU2_CP2",
                "cpConfig": {
                    "VDU2_CP2": {
                        "parentCpConfigId": uuidutils.generate_uuid(),
                        # "linkPortId": omitted,
                        "cpProtocolData": [{
                            "layerProtocol": "IP_OVER_ETHERNET",
                            "ipOverEthernet": {
                                "macAddress": "fa:16:3e:fa:22:75",
                                # "segmentationId": omitted,
                                "ipAddresses": [{
                                    "type": "IPV4",
                                    "fixedAddresses": [
                                        "100.100.100.11",
                                        # omitted
                                    ],
                                    # "numDynamicAddresses": omitted,
                                    # "addressRange": omitted,
                                    "subnetId": subnets['ft-ipv4-subnet0']
                                }, {
                                    "type": "IPV6",
                                    # "fixedAddresses": omitted,
                                    # "numDynamicAddresses": omitted,
                                    "numDynamicAddresses": 1,
                                    # "addressRange": omitted,
                                    "subnetId": subnets['ft-ipv6-subnet0']
                                }]
                            }
                        }]
                    },
                    # { "VDU2_CP2_2": omitted }
                }
            }
        ]
        # "extLinkPorts": omitted
    }
    # NOTE: "vnfLinkPort" is omitted because it is not supported
    ext_mngd_vl_1 = {
        "id": uuidutils.generate_uuid(),
        "vnfVirtualLinkDescId": "internalVL1",
        "vimConnectionId": vim_id_1,
        "resourceProviderId": "Company",
        "resourceId": net_ids['net_mgmt'],
        # "vnfLinkPort": omitted,
        "extManagedMultisiteVirtualLinkId": uuidutils.generate_uuid()
    }
    # NOTE: "vnfLinkPort" is omitted because it is not supported
    ext_mngd_vl_2 = {
        "id": uuidutils.generate_uuid(),
        "vnfVirtualLinkDescId": "internalVL2",
        "vimConnectionId": vim_id_1,
        "resourceProviderId": "Company",
        "resourceId": net_ids['net1'],
        # "vnfLinkPort": omitted,
        "extManagedMultisiteVirtualLinkId": uuidutils.generate_uuid()
    }
    vim_1 = {
        "vimId": vim_id_1,
        "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_3",
        "interfaceInfo": {"endpoint": auth_url},
        "accessInfo": {
            "username": "nfv_user",
            "region": "RegionOne",
            "password": "devstack",
            "project": "nfv",
            "projectDomain": "Default",
            "userDomain": "Default"
        },
        "extra": {"dummy-key": "dummy-val"}
    }
    vim_2 = {
        "vimId": vim_id_2,
        "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_3",
        "interfaceInfo": {"endpoint": auth_url},
        "accessInfo": {
            "username": "dummy_user",
            "region": "RegionOne",
            "password": "dummy_password",
            "project": "dummy_project",
            "projectDomain": "Default",
            "userDomain": "Default"
        },
        "extra": {"dummy-key": "dummy-val"}
    }
    add_params = {
        "lcm-operation-user-data": "./UserData/userdata.py",
        "lcm-operation-user-data-class": "UserData",
        "nfv": {"CP": {"VDU2_CP1-2": {"port": ports['VDU2_CP1-2']}}}
    }

    return {
        "flavourId": "simple",
        "instantiationLevelId": "instantiation_level_1",
        "extVirtualLinks": [
            ext_vl_1,
            ext_vl_2
        ],
        "extManagedVirtualLinks": [
            ext_mngd_vl_1,
            ext_mngd_vl_2
        ],
        "vimConnectionInfo": {
            "vim1": vim_1,
            "vim2": vim_2
        },
        "localizationLanguage": "ja",
        "additionalParams": add_params,
        "extensions": {"dummy-key": "dummy-val"},
        "vnfConfigurableProperties": {"dummy-key": "dummy-val"}
    }


def create_vnf_min(vnfd_id):
    # Omit except for required attributes
    # NOTE: Only the following cardinality attributes are set.
    #  - 1
    #  - 1..N (1)
    return {
        "vnfdId": vnfd_id,
    }


def terminate_vnf_min():
    # Omit except for required attributes
    # NOTE: Only the following cardinality attributes are set.
    #  - 1
    #  - 1..N (1)
    return {
        "terminationType": "FORCEFUL"
    }


def instantiate_vnf_min():
    # Omit except for required attributes
    # NOTE: Only the following cardinality attributes are set.
    #  - 1
    #  - 1..N (1)
    return {
        "flavourId": "simple"
    }


def scaleout_vnf_max():
    # All attributes are set.
    # NOTE: All of the following cardinality attributes are set.
    # In addition, 0..N or 1..N attributes are set to 2 or more.
    #  - 0..1 (1)
    #  - 0..N (2 or more)
    #  - 1
    #  - 1..N (2 or more)
    return {
        "type": "SCALE_OUT",
        "aspectId": "VDU1_scale",
        "numberOfSteps": 1,
        "additionalParams": {"dummy-key": "dummy-value"}
    }


def scaleout_vnf_min():
    # Omit except for required attributes
    # NOTE: Only the following cardinality attributes are set.
    #  - 1
    #  - 1..N (1)
    return {
        "type": "SCALE_OUT",
        "aspectId": "VDU1_scale"
    }


def scalein_vnf_max():
    # All attributes are set.
    # NOTE: All of the following cardinality attributes are set.
    # In addition, 0..N or 1..N attributes are set to 2 or more.
    #  - 0..1 (1)
    #  - 0..N (2 or more)
    #  - 1
    #  - 1..N (2 or more)
    return {
        "type": "SCALE_IN",
        "aspectId": "VDU1_scale",
        "numberOfSteps": 1,
        "additionalParams": {"dummy-key": "dummy-value"}
    }


def scalein_vnf_min():
    # Omit except for required attributes
    # NOTE: Only the following cardinality attributes are set.
    #  - 1
    #  - 1..N (1)
    return {
        "type": "SCALE_IN",
        "aspectId": "VDU1_scale"
    }


def update_vnf_max(vnfd_id, vnfc_ids):
    # All attributes are set.
    # NOTE: All of the following cardinality attributes are set.
    # In addition, 0..N or 1..N attributes are set to 2 or more.
    #  - 0..1 (1)
    #  - 0..N (2 or more)
    #  - 1
    #  - 1..N (2 or more)
    return {
        "vnfInstanceName": "new name",
        "vnfInstanceDescription": "new description",
        "vnfdId": vnfd_id,
        "vnfConfigurableProperties": {"dummy-key": "dummy-value"},
        "metadata": {"dummy-key": "dummy-value"},
        "extensions": {"dummy-key": "dummy-value"},
        "vimConnectionInfo": {
            "vim2": {
                "vimId": "ac2d2ece-5e49-4b15-b92d-b681e9c096d8",
                "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_3",
                "interfaceInfo": {
                    "endpoint": "http://127.0.0.1/identity/v3"
                },
                "accessInfo": {
                    "username": "dummy_user",
                    "region": "RegionOne",
                    "password": "dummy_password",
                    "project": "dummy_project",
                    "projectDomain": "Default",
                    "userDomain": "Default"
                },
                "extra": {
                    "dummy-key": "dummy-val"
                }
            }
        },
        "vnfcInfoModifications": [
            {
                "id": id,
                "vnfcConfigurableProperties": {
                    "dummy-key": "dummy-value"
                }} for id in vnfc_ids]
    }


def update_vnf_min():
    # Omit except for required attributes
    # NOTE: Only the following cardinality attributes are set.
    #  - 1
    #  - 1..N (1)
    return {
        "vnfInstanceName": "new name"
    }


def update_vnf_min_with_parameter(vnfd_id):
    # Omit except for required attributes
    # NOTE: Only the following cardinality attributes are set.
    #  - 1
    #  - 1..N (1)
    return {
        "vnfdId": vnfd_id
    }


def heal_vnf_vnfc_max(vnfc_id):
    # All attributes are set.
    # NOTE: All of the following cardinality attributes are set.
    # In addition, 0..N or 1..N attributes are set to 2 or more.
    #  - 0..1 (1)
    #  - 0..N (2 or more)
    #  - 1
    #  - 1..N (2 or more)
    return {
        "cause": "ManualHealing",
        "vnfcInstanceId": [vnfc_id],
        "additionalParams": {"dummy-key": "dummy-val"}
    }


# The input parameter is_all is bool type, which accepts only True or False.
def heal_vnf_vnfc_max_with_parameter(vnfc_ids, is_all=None):
    # All attributes are set.
    # NOTE: All of the following cardinality attributes are set.
    # In addition, 0..N or 1..N attributes are set to 2 or more.
    #  - 0..1 (1)
    #  - 0..N (2 or more)
    #  - 1
    #  - 1..N (2 or more)
    if is_all is not None:
        key = "all"
        value = is_all
    else:
        key = "dummy-key"
        value = "dummy-val"

    return {
        "cause": "ManualHealing",
        "vnfcInstanceId": [vnfc_id for vnfc_id in vnfc_ids],
        "additionalParams": {key: value}
    }


# The input parameter is_all is bool type, which accepts only True or False.
def heal_vnf_all_max_with_parameter(is_all=None):
    # All attributes are set.
    # NOTE: All of the following cardinality attributes are set.
    # In addition, 0..N or 1..N attributes are set to 2 or more.
    #  - 0..1 (1)
    #  - 0..N (2 or more)
    #  - 1
    #  - 1..N (2 or more)
    if is_all is not None:
        key = "all"
        value = is_all
    else:
        key = "dummy-key"
        value = "dummy-val"

    return {
        "cause": "ManualHealing",
        "additionalParams": {key: value}
    }


def heal_vnf_vnfc_min(vnfd_id):
    # Omit except for required attributes
    # NOTE: Only the following cardinality attributes are set.
    #  - 1
    #  - 1..N (1)
    return {
        "vnfcInstanceId": [vnfd_id]
    }


def heal_vnf_all_min():
    # Omit except for required attributes
    # NOTE: Only the following cardinality attributes are set.
    #  - 1
    #  - 1..N (1)
    return {}


def change_ext_conn_max(net_ids, subnets, auth_url):
    # All attributes are set.
    # NOTE: All of the following cardinality attributes are set.
    # In addition, 0..N or 1..N attributes are set to 2 or more.
    #  - 0..1 (1)
    #  - 0..N (2 or more)
    #  - 1
    #  - 1..N (2 or more)

    vim_id_1 = uuidutils.generate_uuid()
    vim_id_2 = uuidutils.generate_uuid()

    ext_vl_1 = {
        "id": uuidutils.generate_uuid(),
        "vimConnectionId": vim_id_1,
        "resourceProviderId": uuidutils.generate_uuid(),
        "resourceId": net_ids['ft-net1'],
        "extCps": [
            {
                "cpdId": "VDU1_CP1",
                "cpConfig": {
                    "VDU1_CP1": {
                        "cpProtocolData": [{
                            "layerProtocol": "IP_OVER_ETHERNET",
                            "ipOverEthernet": {
                                # "macAddress": omitted,
                                # "segmentationId": omitted,
                                "ipAddresses": [{
                                    "type": "IPV4",
                                    # "fixedAddresses": omitted,
                                    "numDynamicAddresses": 1,
                                    # "addressRange": omitted,
                                    "subnetId": subnets['ft-ipv4-subnet1']}]
                            }
                        }]}
                }
            },
            {
                "cpdId": "VDU2_CP2",
                "cpConfig": {
                    "VDU2_CP2": {
                        "cpProtocolData": [{
                            "layerProtocol": "IP_OVER_ETHERNET",
                            "ipOverEthernet": {
                                # "macAddress": omitted,
                                # "segmentationId": omitted,
                                "ipAddresses": [{
                                    "type": "IPV4",
                                    "fixedAddresses": [
                                        "22.22.22.101"
                                    ],
                                    # "numDynamicAddresses": omitted
                                    # "addressRange": omitted,
                                    "subnetId": subnets['ft-ipv4-subnet1']
                                }, {
                                    "type": "IPV6",
                                    # "fixedAddresses": omitted,
                                    # "numDynamicAddresses": omitted,
                                    "numDynamicAddresses": 1,
                                    # "addressRange": omitted,
                                    "subnetId": subnets['ft-ipv6-subnet1']
                                }]
                            }
                        }]
                    }}
            }
        ]
    }
    vim_1 = {
        "vimId": vim_id_1,
        "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_3",
        "interfaceInfo": {"endpoint": auth_url},
        "accessInfo": {
            "username": "nfv_user",
            "region": "RegionOne",
            "password": "devstack",
            "project": "nfv",
            "projectDomain": "Default",
            "userDomain": "Default"
        },
        "extra": {"dummy-key": "dummy-val"}
    }
    vim_2 = {
        "vimId": vim_id_2,
        "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_3",
        "interfaceInfo": {"endpoint": auth_url},
        "accessInfo": {
            "username": "dummy_user",
            "region": "RegionOne",
            "password": "dummy_password",
            "project": "dummy_project",
            "projectDomain": "Default",
            "userDomain": "Default"
        },
        "extra": {"dummy-key": "dummy-val"}
    }

    return {
        "extVirtualLinks": [
            ext_vl_1
        ],
        "vimConnectionInfo": {
            "vim1": vim_1,
            "vim2": vim_2
        },
        "additionalParams": {"dummy-key": "dummy-val"}
    }


def change_ext_conn_min(net_ids, subnets):
    # Omit except for required attributes
    # NOTE: Only the following cardinality attributes are set.
    #  - 1
    #  - 1..N (1)

    ext_vl_1 = {
        "id": uuidutils.generate_uuid(),
        "resourceId": net_ids['ft-net1'],
        "extCps": [
            {
                "cpdId": "VDU2_CP2",
                "cpConfig": {
                    "VDU2_CP2": {
                        "cpProtocolData": [{
                            "layerProtocol": "IP_OVER_ETHERNET",
                            "ipOverEthernet": {
                                # "macAddress": omitted,
                                # "segmentationId": omitted,
                                "ipAddresses": [{
                                    "type": "IPV4",
                                    "fixedAddresses": [
                                        "22.22.22.100"
                                    ],
                                    # "numDynamicAddresses": omitted
                                    # "addressRange": omitted,
                                    "subnetId": subnets['ft-ipv4-subnet1']
                                }, {
                                    "type": "IPV6",
                                    # "fixedAddresses": omitted,
                                    # "numDynamicAddresses": omitted,
                                    "numDynamicAddresses": 1,
                                    # "addressRange": omitted,
                                    "subnetId": subnets['ft-ipv6-subnet1']
                                }]
                            }
                        }]}
                }
            }
        ]
    }

    return {
        "extVirtualLinks": [
            ext_vl_1
        ]
    }


def change_vnfpkg_create(vnfd_id):
    return {
        "vnfdId": vnfd_id,
        "vnfInstanceName": "vnf_change_vnfpkg",
        "vnfInstanceDescription": "test_change_vnfpkg_from_image_to_image",
        "metadata": {"dummy-key": "dummy-val"}
    }


def change_vnfpkg_instantiate(net_ids, subnet_ids, auth_url,
                              flavor_id='simple'):
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

    return {
        "flavourId": flavor_id,
        "instantiationLevelId": "instantiation_level_1",
        "extVirtualLinks": [
            ext_vl_1
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
    }


def change_vnfpkg(vnfd_id):
    return {
        "vnfdId": vnfd_id,
        "additionalParams": {
            "upgrade_type": "RollingUpdate",
            "lcm-operation-coordinate-old-vnf":
                "./Scripts/coordinate_old_vnf.py",
            "lcm-operation-coordinate-old-vnf-class": "CoordinateOldVnf",
            "lcm-operation-coordinate-new-vnf":
                "./Scripts/coordinate_new_vnf.py",
            "lcm-operation-coordinate-new-vnf-class": "CoordinateNewVnf",
            "vdu_params": [{
                "vdu_id": "VDU1",
                "old_vnfc_param": {
                    "cp_name": "VDU1_CP1",
                    "username": "ubuntu",
                    "password": "ubuntu"
                },
                "new_vnfc_param": {
                    "cp_name": "VDU1_CP1",
                    "username": "ubuntu",
                    "password": "ubuntu"
                }
            }, {
                "vdu_id": "VDU2",
                "old_vnfc_param": {
                    "cp_name": "VDU2_CP1",
                    "username": "ubuntu",
                    "password": "ubuntu"
                },
                "new_vnfc_param": {
                    "cp_name": "VDU2_CP1",
                    "username": "ubuntu",
                    "password": "ubuntu"
                }
            }]
        }
    }
