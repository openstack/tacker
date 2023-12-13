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


def create_vnf_max(vnfd_id, description="test sample"):
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
        "vnfInstanceDescription": description,
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


def instantiate_vnf_max(net_ids, subnets, ports, auth_url, user_data=False):
    # All attributes are set.
    # NOTE: All of the following cardinality attributes are set.
    # In addition, 0..N or 1..N attributes are set to 2 or more.
    #  - 0..1 (1)
    #  - 0..N (2 or more)
    #  - 1
    #  - 1..N (2 or more)

    vim_id_1 = "vim1"
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
            }
        ]
    }
    if ports:
        vdu2_cp1_info = [{
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
        }, {
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
        }]
        ext_vl_1['extCps'].extend(vdu2_cp1_info)
        ext_vl_1['extLinkPorts'] = [
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
        "vimId": uuidutils.generate_uuid(),
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
        "vimId": uuidutils.generate_uuid(),
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
    if not user_data:
        add_params = {
            "lcm-operation-user-data": "./UserData/userdata.py",
            "lcm-operation-user-data-class": "UserData",
            "nfv": {"CP": {"VDU2_CP1-2": {"port": ports['VDU2_CP1-2']}}}
        }
    else:
        add_params = {
            "lcm-operation-user-data": "./UserData/userdata_standard.py",
            "lcm-operation-user-data-class": "StandardUserData"
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

    vim_id_1 = "vim1"

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
        "vimId": uuidutils.generate_uuid(),
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
        "vimId": uuidutils.generate_uuid(),
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
            "lcm-operation-coordinate-new-vnf":
                "./Scripts/coordinate_new_vnf.py",
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


def change_vnfpkg_with_ext_vl(vnfd_id, net_ids):
    ext_vl_1 = {
        "id": uuidutils.generate_uuid(),
        "resourceId": net_ids['net1'],
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
            }
        ]
    }
    req = change_vnfpkg(vnfd_id)
    req["extVirtualLinks"] = [ext_vl_1]

    return req


# sample3 is used for tests of StandardUserData
#
def sample3_create(vnfd_id):
    return {
        "vnfdId": vnfd_id,
        "vnfInstanceName": "sample3",
        "vnfInstanceDescription": "test for StandardUserData",
        "metadata": {
            "VDU_VNFc_mapping": {
                "VDU1": ["a-001", "a-010", "a-011"],
                "VDU2": ["b-000"]
            }
        }
    }


def sample3_terminate():
    return {
        "terminationType": "FORCEFUL"
    }


def sample3_instantiate(net_ids, subnet_ids, auth_url):
    ext_vl_1 = {
        "id": "ext_vl_id_net1",
        "resourceId": net_ids['net1'],
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
                                    "numDynamicAddresses": 1,
                                    "subnetId": subnet_ids['subnet1']}]}}]}
                }
            }
        ]
    }

    return {
        "flavourId": "simple",
        "instantiationLevelId": "instantiation_level_1",
        "extVirtualLinks": [ext_vl_1],
        "extManagedVirtualLinks": [
            {
                "id": "ext_managed_vl_1",
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
            "lcm-operation-user-data": "./UserData/userdata_standard.py",
            "lcm-operation-user-data-class": "StandardUserData",
            "nfv": {
                "VDU": {
                    "VDU1-0": {"name": "VDU1-a-001-instantiate"},
                    "VDU1-1": {"name": "VDU1-a-010-instantiate"},
                    "VDU1-2": {"name": "VDU1-a-011-instantiate"}
                }
            }
        }
    }


def sample3_scale_out():
    return {
        "type": "SCALE_OUT",
        "aspectId": "VDU1_scale",
        "numberOfSteps": 2,
        "additionalParams": {
            "lcm-operation-user-data": "./UserData/userdata_standard.py",
            "lcm-operation-user-data-class": "StandardUserData",
            # In this sample, VDU1-2 nfv parameters is not set for test,
            # but in normal operation, it is recommended to set nfv parameters
            # when adding or updating.
            "nfv": {
                "VDU": {
                    "VDU1-1": {"name": "VDU1-a-010-scale_out"},
                }
            }
        }
    }


def sample3_scale_in():
    return {
        "type": "SCALE_IN",
        "aspectId": "VDU1_scale",
        "numberOfSteps": 1,
        "additionalParams": {
            "lcm-operation-user-data": "./UserData/userdata_standard.py",
            "lcm-operation-user-data-class": "StandardUserData"
        }
    }


def sample3_heal():
    return {
        "vnfcInstanceId": [],  # should be filled
        "additionalParams": {
            "lcm-operation-user-data": "./UserData/userdata_standard.py",
            "lcm-operation-user-data-class": "StandardUserData",
            "nfv": {
                "VDU": {
                    "VDU1-1": {"name": "VDU1-a-010-heal"},
                }
            }
        }
    }


def sample3_change_ext_conn(net_ids):
    return {
        "extVirtualLinks": [
            {
                "id": "ext_vl_id_net0",
                "resourceId": net_ids['net0'],
                "extCps": [
                    {
                        "cpdId": "VDU1_CP1",
                        "cpConfig": {
                            "VDU1_CP2_1": {
                                "cpProtocolData": [{
                                    "layerProtocol": "IP_OVER_ETHERNET",
                                    "ipOverEthernet": {
                                        "ipAddresses": [{
                                            "type": "IPV4",
                                            "numDynamicAddresses": 1}]}}]}
                        }
                    }
                ]
            }
        ],
        "additionalParams": {
            "lcm-operation-user-data": "./UserData/userdata_standard.py",
            "lcm-operation-user-data-class": "StandardUserData",
            "nfv": {
                "VDU": {
                    "VDU1-0": {"name": "VDU1-a-001-change_ext_conn"},
                    "VDU1-1": {"name": "VDU1-a-010-change_ext_conn"},
                    "VDU1-2": {"name": "VDU1-a-011-change_ext_conn"}
                }
            }
        }
    }


# sample3_update_vnf_vnfd_id is for test heal after vnfdId changed
# in StandardUserData.
#
def sample3_update_vnf_vnfd_id(vnfd_id):
    return {
        "vnfdId": vnfd_id
    }


# sample4 is for change_vnfpkg test of StandardUserData
#
def sample4_change_vnfpkg(vnfd_id, net_ids, subnet_ids):
    return {
        "vnfdId": vnfd_id,
        "extVirtualLinks": [
            {
                "id": "ext_vl_id_net0",
                "resourceId": net_ids['net0'],
                "extCps": [
                    {
                        "cpdId": "VDU2_CP1",
                        "cpConfig": {
                            "VDU2_CP1_1": {
                                "cpProtocolData": [{
                                    "layerProtocol": "IP_OVER_ETHERNET",
                                    "ipOverEthernet": {
                                        "ipAddresses": [{
                                            "type": "IPV4",
                                            "numDynamicAddresses": 1,
                                            "subnetId":
                                                subnet_ids['subnet0']}]}}]}
                        }
                    }
                ]
            }
        ],
        "extManagedVirtualLinks": [
            {
                "id": "ext_managed_vl_1",
                "vnfVirtualLinkDescId": "internalVL1",
                "resourceId": net_ids['net_mgmt']
            },
        ],
        "additionalParams": {
            "upgrade_type": "RollingUpdate",
            "lcm-operation-coordinate-new-vnf": "./Scripts/coordinate_vnf.py",
            "lcm-operation-coordinate-old-vnf": "./Scripts/coordinate_vnf.py",
            "vdu_params": [
                {
                    "vdu_id": "VDU1",
                    "old_vnfc_param": {
                        "cp_name": "VDU1_CP1",
                        "username": "ubuntu",
                        "password": "ubuntu",
                        "endpoint": "http://127.0.0.1:6789",
                        "authentication": {
                            "authType": ["BASIC"],
                            "paramsBasic": {
                                "userName": "tacker",
                                "password": "tacker"
                            }
                        },
                        "timeout": 30
                    },
                    "new_vnfc_param": {
                        "cp_name": "VDU1_CP1",
                        "username": "ubuntu",
                        "password": "ubuntu",
                        "endpoint": "http://127.0.0.1:6789",
                        "authentication": {
                            "authType": ["BASIC"],
                            "paramsBasic": {
                                "userName": "tacker",
                                "password": "tacker"
                            }
                        },
                        "timeout": 30
                    }
                },
                {
                    "vdu_id": "VDU2",
                    "old_vnfc_param": {
                        "cp_name": "VDU2_CP1",
                        "username": "ubuntu",
                        "password": "ubuntu",
                        "endpoint": "http://127.0.0.1:6789",
                        "authentication": {
                            "authType": ["BASIC"],
                            "paramsBasic": {
                                "userName": "tacker",
                                "password": "tacker"
                            }
                        },
                        "timeout": 30
                    },
                    "new_vnfc_param": {
                        "cp_name": "VDU2_CP1",
                        "username": "ubuntu",
                        "password": "ubuntu",
                        "endpoint": "http://127.0.0.1:6789",
                        "authentication": {
                            "authType": ["BASIC"],
                            "paramsBasic": {
                                "userName": "tacker",
                                "password": "tacker"
                            }
                        },
                        "timeout": 30
                    }
                }
            ],
            "lcm-operation-user-data": "./UserData/userdata_standard.py",
            "lcm-operation-user-data-class": "StandardUserData",
            "nfv": {
                "VDU": {
                    "VDU1-0": {"name": "VDU1-a-001-change_vnfpkg"},
                    "VDU1-1": {"name": "VDU1-a-010-change_vnfpkg"},
                    "VDU1-2": {"name": "VDU1-a-011-change_vnfpkg"},
                }
            }
        }
    }


def sample4_terminate():
    return {
        "terminationType": "FORCEFUL"
    }


def prometheus_auto_healing_alert(inst_id, vnfc_info_id):
    return {
        "receiver": "receiver",
        "status": "firing",
        "alerts": [{
            "status": "firing",
            "labels": {
                "receiver_type": "tacker",
                "function_type": "auto_heal",
                "vnf_instance_id": inst_id,
                "vnfc_info_id": vnfc_info_id
            },
            "annotations": {
            },
            "startsAt": "2022-06-21T23:47:36.453Z",
            "endsAt": "0001-01-01T00:00:00Z",
            "generatorURL": "http://controller147:9090/graph?g0.expr="
                            "up%7Bjob%3D%22node%22%7D+%3D%3D+0&g0.tab=1",
            "fingerprint": "5ef77f1f8a3ecb8d"
        }],
        "groupLabels": {},
        "commonLabels": {
            "alertname": "NodeInstanceDown",
            "job": "node"
        },
        "commonAnnotations": {
            "description": "sample"
        },
        "externalURL": "http://controller147:9093",
        "version": "4",
        "groupKey": "{}:{}",
        "truncatedAlerts": 0
    }


def prometheus_auto_scaling_alert(inst_id):
    return {
        "receiver": "receiver",
        "status": "firing",
        "alerts": [{
            "status": "firing",
            "labels": {
                "receiver_type": "tacker",
                "function_type": "auto_scale",
                "vnf_instance_id": inst_id,
                "auto_scale_type": "SCALE_OUT",
                "aspect_id": "VDU1_scale"
            },
            "annotations": {
            },
            "startsAt": "2022-06-21T23:47:36.453Z",
            "endsAt": "0001-01-01T00:00:00Z",
            "generatorURL": "http://controller147:9090/graph?g0.expr="
                            "up%7Bjob%3D%22node%22%7D+%3D%3D+0&g0.tab=1",
            "fingerprint": "5ef77f1f8a3ecb8d"
        }],
        "groupLabels": {},
        "commonLabels": {
            "alertname": "NodeInstanceDown",
            "job": "node"
        },
        "commonAnnotations": {
            "description": "sample"
        },
        "externalURL": "http://controller147:9093",
        "version": "4",
        "groupKey": "{}:{}",
        "truncatedAlerts": 0
    }


def server_notification(alarm_id):
    return {
        'notification': {
            'host_id': 'host_id',
            'alarm_id': alarm_id,
            'fault_id': '1234',
            'fault_type': '10',
            'fault_option': {
                'detail': 'server is down.'
            }
        }
    }


# sample5 is for change_vnfpkg network change test of StandardUserData
#
def sample5_change_vnfpkg(vnfd_id, net_ids, subnet_ids):
    ext_vl_4 = {
        "id": "ext_vl_id_net4",
        "resourceId": net_ids['net0'],
        "extCps": [
            {
                "cpdId": "VDU1_CP4",
                "cpConfig": {
                    "VDU1_CP4_1": {
                        "cpProtocolData": [{
                            "layerProtocol": "IP_OVER_ETHERNET",
                            "ipOverEthernet": {
                                "ipAddresses": [{
                                    "type": "IPV4",
                                    "numDynamicAddresses": 1}]}}]}
                }
            },
            {
                "cpdId": "VDU2_CP4",
                "cpConfig": {
                    "VDU2_CP4_1": {
                        "cpProtocolData": [{
                            "layerProtocol": "IP_OVER_ETHERNET",
                            "ipOverEthernet": {
                                "ipAddresses": [{
                                    "type": "IPV4",
                                    "numDynamicAddresses": 1}]}}]}
                }
            }
        ]
    }

    return {
        "vnfdId": vnfd_id,
        "extVirtualLinks": [ext_vl_4],
        "extManagedVirtualLinks": [
            {
                "id": "ext_managed_vl_1",
                "vnfVirtualLinkDescId": "internalVL1",
                "resourceId": net_ids['net_mgmt']
            },
        ],
        "additionalParams": {
            "upgrade_type": "RollingUpdate",
            "lcm-operation-coordinate-new-vnf": "./Scripts/coordinate_vnf.py",
            "lcm-operation-coordinate-old-vnf": "./Scripts/coordinate_vnf.py",
            "vdu_params": [
                {
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
                },
                {
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
                }
            ],
            "lcm-operation-user-data": "./UserData/userdata_standard.py",
            "lcm-operation-user-data-class": "StandardUserData",
            "nfv": {
                "VDU": {
                    "VDU1-0": {"name": "VDU1-a-001-change_vnfpkg"},
                    "VDU1-1": {"name": "VDU1-a-010-change_vnfpkg"},
                    "VDU1-2": {"name": "VDU1-a-011-change_vnfpkg"}
                }
            }
        }
    }


def sample5_change_vnfpkg_back(vnfd_id, net_ids, subnet_ids):
    return {
        "vnfdId": vnfd_id,
        "extManagedVirtualLinks": [
            {
                "id": "ext_managed_vl_1",
                "vnfVirtualLinkDescId": "internalVL1",
                "resourceId": net_ids['net_mgmt']
            },
        ],
        "additionalParams": {
            "upgrade_type": "RollingUpdate",
            "lcm-operation-coordinate-new-vnf": "./Scripts/coordinate_vnf.py",
            "lcm-operation-coordinate-old-vnf": "./Scripts/coordinate_vnf.py",
            "vdu_params": [
                {
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
                },
                {
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
                }
            ],
            "lcm-operation-user-data": "./UserData/userdata_standard.py",
            "lcm-operation-user-data-class": "StandardUserData"
        }
    }


def sample5_terminate():
    return {
        "terminationType": "FORCEFUL"
    }


# sample6 is for retry AZ selection test of StandardUserData
#
def sample6_create(vnfd_id):
    return {
        "vnfdId": vnfd_id,
        "vnfInstanceName": "sample6",
        "vnfInstanceDescription": "test for retry of AZ selection"
    }


def sample6_terminate():
    return {
        "terminationType": "FORCEFUL"
    }


def sample6_instantiate(net_ids, subnet_ids, auth_url):
    ext_vl_1 = {
        "id": "ext_vl_id_net1",
        "resourceId": net_ids['net1'],
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
            }
        ]
    }

    return {
        "flavourId": "simple",
        "instantiationLevelId": "instantiation_level_1",
        "extVirtualLinks": [ext_vl_1],
        "extManagedVirtualLinks": [
            {
                "id": "ext_managed_vl_1",
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
            "lcm-operation-user-data": "./UserData/userdata_standard.py",
            "lcm-operation-user-data-class": "StandardUserData"
        }
    }


def sample6_scale_out():
    return {
        "type": "SCALE_OUT",
        "aspectId": "VDU1_scale",
        "numberOfSteps": 1,
        "additionalParams": {
            "lcm-operation-user-data": "./UserData/userdata_standard.py",
            "lcm-operation-user-data-class": "StandardUserData"
        }
    }


def change_vnf_pkg_individual_vnfc_max(vnfd_id, net_ids, subnet_ids):
    return {
        "vnfdId": vnfd_id,
        "extVirtualLinks": [{
            "id": "external-net-changed",
            "resourceId": net_ids['net1'],
            "extCps": [{
                "cpdId": "VDU1_CP1",
                "cpConfig": {
                    "VDU1_CP1": {
                        "cpProtocolData": [{
                            "layerProtocol": "IP_OVER_ETHERNET",
                            "ipOverEthernet": {
                                "ipAddresses": [{
                                    "type": "IPV4",
                                    "numDynamicAddresses": 1,
                                    "subnetId": subnet_ids['subnet1']
                                }]
                            }
                        }]
                    }
                }
            }]
        }, {
            "id": "ext_vl_id_net6",
            "resourceId": net_ids['net0'],
            "extCps": [{
                "cpdId": "VDU1_CP6",
                "cpConfig": {
                    "VDU1_CP6_1": {
                        "cpProtocolData": [{
                            "layerProtocol": "IP_OVER_ETHERNET",
                            "ipOverEthernet": {
                                "ipAddresses": [{
                                    "type": "IPV4",
                                    "numDynamicAddresses": 1
                                }]
                            }
                        }]
                    }
                }
            }, {
                "cpdId": "VDU2_CP6",
                "cpConfig": {
                    "VDU2_CP6_1": {
                        "cpProtocolData": [{
                            "layerProtocol": "IP_OVER_ETHERNET",
                            "ipOverEthernet": {
                                "ipAddresses": [{
                                    "type": "IPV4",
                                    "numDynamicAddresses": 1
                                }]
                            }
                        }]
                    }
                }
            }]
        }],
        "extManagedVirtualLinks": [{
            "id": uuidutils.generate_uuid(),
            "vnfVirtualLinkDescId": "internalVL1",
            "vimConnectionId": "vim1",
            "resourceProviderId": "Company",
            "resourceId": net_ids['net_mgmt'],
            "extManagedMultisiteVirtualLinkId": uuidutils.generate_uuid()
        }, {
            "id": uuidutils.generate_uuid(),
            "vnfVirtualLinkDescId": "internalVL2",
            "vimConnectionId": "vim1",
            "resourceProviderId": "Company",
            "resourceId": net_ids['net_mgmt'],
            "extManagedMultisiteVirtualLinkId": uuidutils.generate_uuid()
        }],
        "additionalParams": {
            "upgrade_type": "RollingUpdate",
            "lcm-operation-coordinate-new-vnf": "./Scripts/coordinate_vnf.py",
            "lcm-operation-coordinate-old-vnf": "./Scripts/coordinate_vnf.py",
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
                    "cp_name": "VDU2_CP2",
                    "username": "ubuntu",
                    "password": "ubuntu"
                },
                "new_vnfc_param": {
                    "cp_name": "VDU2_CP2",
                    "username": "ubuntu",
                    "password": "ubuntu"
                }
            }],
            "lcm-operation-user-data": "./UserData/userdata_standard.py",
            "lcm-operation-user-data-class": "StandardUserData"
        }
    }


def change_vnf_pkg_individual_vnfc_min(vnfd_id, vdu2_old_vnfc='VDU2_CP1'):
    return {
        "vnfdId": vnfd_id,
        "additionalParams": {
            "upgrade_type": "RollingUpdate",
            "lcm-operation-coordinate-new-vnf": "./Scripts/coordinate_vnf.py",
            "lcm-operation-coordinate-old-vnf": "./Scripts/coordinate_vnf.py",
            "vdu_params": [
                {
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
                },
                {
                    "vdu_id": "VDU2",
                    "old_vnfc_param": {
                        "cp_name": vdu2_old_vnfc,
                        "username": "ubuntu",
                        "password": "ubuntu"
                    },
                    "new_vnfc_param": {
                        "cp_name": "VDU2_CP1",
                        "username": "ubuntu",
                        "password": "ubuntu"
                    }
                }],
            "lcm-operation-user-data": "./UserData/userdata_standard.py",
            "lcm-operation-user-data-class": "StandardUserData"
        }
    }


# sample7 is for attach non-boot volume to VDU test of StandardUserData
#
def sample7_create(vnfd_id):
    return {
        "vnfdId": vnfd_id,
        "vnfInstanceName": "sample7",
        "vnfInstanceDescription": "test for attach non-boot volume of "
                                  "StandardUserData",
        "metadata": {
            "VDU_VNFc_mapping": {
                "VDU1": ["a-001", "a-010", "a-011"],
                "VDU2": ["b-000"]
            }
        }
    }


def sample7_terminate():
    return {
        "terminationType": "FORCEFUL"
    }


def sample7_instantiate(net_ids, subnet_ids, auth_url):
    ext_vl_1 = {
        "id": "ext_vl_id_net1",
        "resourceId": net_ids['net1'],
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
            }
        ]
    }

    return {
        "flavourId": "simple",
        "instantiationLevelId": "instantiation_level_1",
        "extVirtualLinks": [ext_vl_1],
        "extManagedVirtualLinks": [
            {
                "id": "ext_managed_vl_1",
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
            "lcm-operation-user-data": "./UserData/userdata_standard.py",
            "lcm-operation-user-data-class": "StandardUserData"
        }
    }


def sample7_heal(vnfc_id):
    return {
        "vnfcInstanceId": [vnfc_id],
        "additionalParams": {
            "all": True,
            "lcm-operation-user-data": "./UserData/userdata_standard.py",
            "lcm-operation-user-data-class": "StandardUserData"
        }
    }
