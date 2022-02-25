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

from datetime import datetime
import os
from unittest import mock

from oslo_utils import uuidutils

from tacker import context
from tacker.sol_refactored.common import vnfd_utils
from tacker.sol_refactored.conductor import vnflcm_driver_v2
from tacker.sol_refactored.infra_drivers.kubernetes import kubernetes
from tacker.sol_refactored.nfvo import nfvo_client
from tacker.sol_refactored import objects
from tacker.sol_refactored.objects.v2 import fields
from tacker.tests import base


CNF_SAMPLE_VNFD_ID = "b1bb0ce7-ebca-4fa7-95ed-4840d70a1177"
SAMPLE_VNFD_ID = "b1bb0ce7-ebca-4fa7-95ed-4840d7000000"
SAMPLE_FLAVOUR_ID = "simple"


# InstantiateVnfRequest example for instantiate grant test
_ext_vl_1 = {
    "id": uuidutils.generate_uuid(),
    "resourceId": 'net0_id',
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
_ext_vl_2 = {
    "id": uuidutils.generate_uuid(),
    "resourceId": 'net1_id',
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
                                "subnetId": 'subnet1_id'}]}}]}
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
                                "subnetId": 'subnet1_id'}]}}]}
            }
        }
    ]
}
_inst_req_example = {
    "flavourId": "simple",
    "instantiationLevelId": "instantiation_level_2",
    "extVirtualLinks": [
        _ext_vl_1,
        _ext_vl_2
    ],
    "extManagedVirtualLinks": [
        {
            "id": uuidutils.generate_uuid(),
            "vnfVirtualLinkDescId": "internalVL1",
            "resourceId": 'net_mgmt_id'
        },
    ],
    "vimConnectionInfo": {
        "vim1": {
            "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_3",
            "vimId": uuidutils.generate_uuid(),
            "interfaceInfo": {"endpoint": "http://localhost/identity/v3"},
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
_inst_cnf_req_example = {
    "flavourId": "simple",
    "additionalParams": {
        "lcm-kubernetes-def-files": [
            "Files/kubernetes/deployment.yaml",
            "Files/kubernetes/namespace.yaml",
            "Files/kubernetes/pod.yaml",
        ],
        "namespace": "curry"
    },
    "vimConnectionInfo": {
        "vim1": {
            "vimType": "kubernetes",
            "vimId": uuidutils.generate_uuid(),
            "interfaceInfo": {"endpoint": "https://127.0.0.1:6443"},
            "accessInfo": {
                "bearer_token": "secret_token",
                "region": "RegionOne"
            }
        }
    }
}

#  ChangeExtVnfConnectivityRequest example for change_ext_conn grant test
_ext_vl_3 = {
    "id": uuidutils.generate_uuid(),
    "resourceId": 'net2_id',
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
                                "subnetId": 'subnet2_id'}]}}]}
            }
        },
        {
            "cpdId": "VDU2_CP1",
            "cpConfig": {
                "VDU2_CP1_1": {
                    "linkPortId": "link_port_id"
                }
            }
        }
    ],
    "extLinkPorts": [
        {
            "id": "link_port_id",
            "resourceHandle": {
                "resourceId": "res_id_VDU2_CP1"
            }
        }
    ]
}
_change_ext_conn_req_example = {
    "extVirtualLinks": [_ext_vl_3]
}

# instantiatedVnfInfo example for terminate/scale grant test
# NOTE:
# - some identifiers are modified to make check easy.
# - some attributes which are not related to make terminate/scale grant
#   request are omitted.
_inst_info_example = {
    "flavourId": "simple",
    "vnfState": "STARTED",
    "extCpInfo": [
        {
            "id": "90561570-264c-4472-b84f-1fff98513475",
            "cpdId": "VDU2_CP1",
            "cpConfigId": "VDU2_CP1_1",
            # "cpProtocolInfo": omitted
            "extLinkPortId": "ac27c99b-73c8-4e91-b730-90deade72af4",
            "associatedVnfcCpId": "be955786-a0c7-4b61-8cd8-9bb8bcb1c6e3"
        },
        {
            "id": "f9f4b4b2-50e2-4c73-b89b-e0665e65ffbe",
            "cpdId": "VDU2_CP2",
            "cpConfigId": "VDU2_CP2_1",
            # "cpProtocolInfo": omitted
            "extLinkPortId": "12567a13-9fbd-4803-ad9f-d94ced266cd8",
            "associatedVnfcCpId": "c54fa2fc-185a-49a7-bb89-f30f7c3be6a4"
        },
        {
            "id": "05474d0b-a1f7-4be5-b57e-ef6873e1f3b6",
            "cpdId": "VDU1_CP2",
            "cpConfigId": "VDU1_CP2_1",
            # "cpProtocolInfo": omitted
            "extLinkPortId": "aa6646da-2e59-4de9-9b72-c62e7c4d9142",
            "associatedVnfcCpId": "fdbb289f-87c8-40d0-bf06-da07b41ba124"
        },
        {
            "id": "42ede9a6-c2b8-4c0d-a337-26342ffb236c",
            "cpdId": "VDU1_CP1",
            "cpConfigId": "VDU1_CP1_1",
            # "cpProtocolInfo": omitted
            "extLinkPortId": "efd0eb4e-4e55-4ac8-8b9b-403ec79faf2d",
            "associatedVnfcCpId": "235f920c-8b49-4894-9c36-73f5a3b9f74d"
        },
        {
            "id": "4f0ab1ad-b7de-482f-a69b-1093c71d2ceb",
            "cpdId": "VDU1_CP2",
            "cpConfigId": "VDU1_CP2_1",
            # "cpProtocolInfo": omitted
            "extLinkPortId": "a6c4c043-e082-4873-a871-02467af66224",
            "associatedVnfcCpId": "e23d970d-9ea9-4c26-9d67-8f244383ea3c"
        },
        {
            "id": "7a7fa30f-a303-4856-bc8b-b836cb682892",
            "cpdId": "VDU1_CP1",
            "cpConfigId": "VDU1_CP1_1",
            # "cpProtocolInfo": omitted
            "extLinkPortId": "f58df4d9-08ff-41b7-ab73-95ebfb8103c4",
            "associatedVnfcCpId": "259c5895-7be6-4bed-8a94-221c41b3d08f"
        }
    ],
    "extVirtualLinkInfo": [
        {
            "id": "137bdf0b-835c-43f0-b0d2-5c002599118a",
            "resourceHandle": {
                "resourceId": "6f97f400-2861-482a-ba78-65b652aaf8fc"
            },
            "extLinkPorts": [
                {
                    "id": "ac27c99b-73c8-4e91-b730-90deade72af4",
                    "resourceHandle": {
                        # "vimConnectionId": omitted
                        "resourceId": "res_id_VDU2_CP1",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "90561570-264c-4472-b84f-1fff98513475"
                },
                {
                    "id": "efd0eb4e-4e55-4ac8-8b9b-403ec79faf2d",
                    "resourceHandle": {
                        # "vimConnectionId": omitted
                        "resourceId": "res_id_VDU1_1_CP1",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "42ede9a6-c2b8-4c0d-a337-26342ffb236c"
                },
                {
                    "id": "f58df4d9-08ff-41b7-ab73-95ebfb8103c4",
                    "resourceHandle": {
                        # "vimConnectionId": omitted
                        "resourceId": "res_id_VDU1_2_CP1",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "7a7fa30f-a303-4856-bc8b-b836cb682892"
                }
            ],
            # "currentVnfExtCpData": omitted
        },
        {
            "id": "d8141a5a-6b6e-4dab-9bf5-158f23a617d7",
            "resourceHandle": {
                "resourceId": "02bc95e0-3d43-4d11-83b8-f7b15d8661a9"
            },
            "extLinkPorts": [
                {
                    "id": "12567a13-9fbd-4803-ad9f-d94ced266cd8",
                    "resourceHandle": {
                        # "vimConnectionId": omitted
                        "resourceId": "res_id_VDU2_CP2",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "f9f4b4b2-50e2-4c73-b89b-e0665e65ffbe"
                },
                {
                    "id": "aa6646da-2e59-4de9-9b72-c62e7c4d9142",
                    "resourceHandle": {
                        # "vimConnectionId": omitted
                        "resourceId": "res_id_VDU1_1_CP2",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "05474d0b-a1f7-4be5-b57e-ef6873e1f3b6"
                },
                {
                    "id": "a6c4c043-e082-4873-a871-02467af66224",
                    "resourceHandle": {
                        # "vimConnectionId": omitted
                        "resourceId": "res_id_VDU1_2_CP2",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "4f0ab1ad-b7de-482f-a69b-1093c71d2ceb"
                }
            ],
            # "currentVnfExtCpData": omitted
        }
    ],
    "extManagedVirtualLinkInfo": [
        {
            "id": "bad53df7-f1fa-482d-91b1-caec382aeec2",
            "vnfVirtualLinkDescId": "internalVL1",
            "networkResource": {
                "resourceId": "56730009-169c-4f96-8141-828acf1ee067"
            },
            "vnfLinkPorts": [
                {
                    "id": "74f387fe-6355-4af3-adc7-cdb507d5fa5f",
                    "resourceHandle": {
                        # "vimConnectionId": omitted
                        "resourceId": "res_id_VDU2_CP3",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "5b0b336b-c207-4fa8-8b41-a5ad87d85cd0",
                    "cpInstanceType": "VNFC_CP"
                },
                {
                    "id": "4064ec55-b862-4527-a911-8752d3aa765a",
                    "resourceHandle": {
                        # "vimConnectionId": omitted
                        "resourceId": "res_id_VDU1_1_CP3",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "b0732fb7-a42a-4077-aebc-d22b67b64f13",
                    "cpInstanceType": "VNFC_CP"
                },
                {
                    "id": "f3c9e62d-0f31-4a36-bd99-eecd8def0871",
                    "resourceHandle": {
                        # "vimConnectionId": omitted
                        "resourceId": "res_id_VDU1_2_CP3",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "9c65f67e-feb2-447c-b0e7-a4f896185b4f",
                    "cpInstanceType": "VNFC_CP"
                }
            ]
        }
    ],
    "vnfcResourceInfo": [
        {
            "id": "vnfc_res_info_id_VDU2",
            "vduId": "VDU2",
            "computeResource": {
                # "vimConnectionId": omitted
                "resourceId": "res_id_VDU2",
                "vimLevelResourceType": "OS::Nova::Server"
            },
            "vnfcCpInfo": [
                {
                    "id": "be955786-a0c7-4b61-8cd8-9bb8bcb1c6e3",
                    "cpdId": "VDU2_CP1",
                    "vnfExtCpId": "90561570-264c-4472-b84f-1fff98513475"
                },
                {
                    "id": "c54fa2fc-185a-49a7-bb89-f30f7c3be6a4",
                    "cpdId": "VDU2_CP2",
                    "vnfExtCpId": "f9f4b4b2-50e2-4c73-b89b-e0665e65ffbe"
                },
                {
                    "id": "5b0b336b-c207-4fa8-8b41-a5ad87d85cd0",
                    "cpdId": "VDU2_CP3",
                    "vnfLinkPortId": "74f387fe-6355-4af3-adc7-cdb507d5fa5f"
                },
                {
                    "id": "2cb2b3a8-a7a0-41da-b3b8-4b82f576b090",
                    "cpdId": "VDU2_CP4",
                    "vnfLinkPortId": "8e01813f-35fc-4a35-8f64-0da08a45ea21"
                },
                {
                    "id": "39a7d895-3b19-4330-b6ec-ae3557ea9c01",
                    "cpdId": "VDU2_CP5",
                    "vnfLinkPortId": "4dd7cadd-b9a1-484f-b2f2-1ff50ef0d90f"
                }
            ]
        },
        {
            "id": "vnfc_res_info_id_VDU1_1",
            "vduId": "VDU1",
            "computeResource": {
                # "vimConnectionId": omitted
                "resourceId": "res_id_VDU1_1",
                "vimLevelResourceType": "OS::Nova::Server"
            },
            "storageResourceIds": ["2135b13c-e630-4700-8f8d-85b6e48f7871"],
            "vnfcCpInfo": [
                {
                    "id": "235f920c-8b49-4894-9c36-73f5a3b9f74d",
                    "cpdId": "VDU1_CP1",
                    "vnfExtCpId": "42ede9a6-c2b8-4c0d-a337-26342ffb236c"
                },
                {
                    "id": "fdbb289f-87c8-40d0-bf06-da07b41ba124",
                    "cpdId": "VDU1_CP2",
                    "vnfExtCpId": "05474d0b-a1f7-4be5-b57e-ef6873e1f3b6"
                },
                {
                    "id": "b0732fb7-a42a-4077-aebc-d22b67b64f13",
                    "cpdId": "VDU1_CP3",
                    "vnfLinkPortId": "4064ec55-b862-4527-a911-8752d3aa765a"
                },
                {
                    "id": "a49f8fb8-6fd9-4e9f-a6dd-0d268e51c83c",
                    "cpdId": "VDU1_CP4",
                    "vnfLinkPortId": "1666a0f7-6a34-474e-87a2-07fb0c30ecdb"
                },
                {
                    "id": "33194d65-ecd6-48d9-8ef7-c15ce9fef46c",
                    "cpdId": "VDU1_CP5",
                    "vnfLinkPortId": "ace663cd-431b-402a-b2ae-d0824c996edb"
                }
            ]
        },
        {
            "id": "vnfc_res_info_id_VDU1_2",
            "vduId": "VDU1",
            "computeResource": {
                # "vimConnectionId": omitted
                "resourceId": "res_id_VDU1_2",
                "vimLevelResourceType": "OS::Nova::Server"
            },
            "storageResourceIds": ["739f7012-7973-485b-b34f-b006bc336150"],
            "vnfcCpInfo": [
                {
                    "id": "259c5895-7be6-4bed-8a94-221c41b3d08f",
                    "cpdId": "VDU1_CP1",
                    # when extLinkPorts of extVirtualLinks specified, there is
                    # no vnfExtCpId nor vnfLinkPortId.
                },
                {
                    "id": "e23d970d-9ea9-4c26-9d67-8f244383ea3c",
                    "cpdId": "VDU1_CP2",
                    "vnfExtCpId": "4f0ab1ad-b7de-482f-a69b-1093c71d2ceb"
                },
                {
                    "id": "9c65f67e-feb2-447c-b0e7-a4f896185b4f",
                    "cpdId": "VDU1_CP3",
                    "vnfLinkPortId": "f3c9e62d-0f31-4a36-bd99-eecd8def0871"
                },
                {
                    "id": "0716ac20-612a-4ac2-8c87-d83be31dd4b5",
                    "cpdId": "VDU1_CP4",
                    "vnfLinkPortId": "bce3159b-caca-45b7-8bb7-88015e951e56"
                },
                {
                    "id": "c9112298-61eb-4bba-b285-ed3419593b1b",
                    "cpdId": "VDU1_CP5",
                    "vnfLinkPortId": "e0f98917-70ff-4f79-8747-9d7fc22827a4"
                }
            ]
        }
    ],
    "vnfVirtualLinkResourceInfo": [
        {
            "id": "18bd0111-d5e1-4aa3-b2d8-5b89833c6351",
            "vnfVirtualLinkDescId": "internalVL3",
            "networkResource": {
                # "vimConnectionId": omitted
                "resourceId": "res_id_internalVL3",
                "vimLevelResourceType": "OS::Neutron::Net"
            },
            "vnfLinkPorts": [
                {
                    "id": "4dd7cadd-b9a1-484f-b2f2-1ff50ef0d90f",
                    "resourceHandle": {
                        # "vimConnectionId": omitted
                        "resourceId": "res_id_VDU2_CP5",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "39a7d895-3b19-4330-b6ec-ae3557ea9c01",
                    "cpInstanceType": "VNFC_CP"
                },
                {
                    "id": "ace663cd-431b-402a-b2ae-d0824c996edb",
                    "resourceHandle": {
                        # "vimConnectionId": omitted
                        "resourceId": "res_id_VDU1_1_CP5",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "33194d65-ecd6-48d9-8ef7-c15ce9fef46c",
                    "cpInstanceType": "VNFC_CP"
                },
                {
                    "id": "e0f98917-70ff-4f79-8747-9d7fc22827a4",
                    "resourceHandle": {
                        # "vimConnectionId": omitted
                        "resourceId": "res_id_VDU1_2_CP5",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "c9112298-61eb-4bba-b285-ed3419593b1b",
                    "cpInstanceType": "VNFC_CP"
                }
            ]
        },
        {
            "id": "047aa313-b591-4529-aa98-cb8ce2b82e28",
            "vnfVirtualLinkDescId": "internalVL2",
            "networkResource": {
                # "vimConnectionId": omitted
                "resourceId": "res_id_internalVL2",
                "vimLevelResourceType": "OS::Neutron::Net"
            },
            "vnfLinkPorts": [
                {
                    "id": "8e01813f-35fc-4a35-8f64-0da08a45ea21",
                    "resourceHandle": {
                        # "vimConnectionId": omitted
                        "resourceId": "res_id_VDU2_CP4",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "2cb2b3a8-a7a0-41da-b3b8-4b82f576b090",
                    "cpInstanceType": "VNFC_CP"
                },
                {
                    "id": "1666a0f7-6a34-474e-87a2-07fb0c30ecdb",
                    "resourceHandle": {
                        # "vimConnectionId": omitted
                        "resourceId": "res_id_VDU1_1_CP4",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "a49f8fb8-6fd9-4e9f-a6dd-0d268e51c83c",
                    "cpInstanceType": "VNFC_CP"
                },
                {
                    "id": "bce3159b-caca-45b7-8bb7-88015e951e56",
                    "resourceHandle": {
                        # "vimConnectionId": omitted
                        "resourceId": "res_id_VDU1_2_CP4",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "0716ac20-612a-4ac2-8c87-d83be31dd4b5",
                    "cpInstanceType": "VNFC_CP"
                }
            ]
        }
    ],
    "virtualStorageResourceInfo": [
        {
            "id": "2135b13c-e630-4700-8f8d-85b6e48f7871",
            "virtualStorageDescId": "VirtualStorage",
            "storageResource": {
                # "vimConnectionId": omitted
                "resourceId": "res_id_VirtualStorage_1",
                "vimLevelResourceType": "OS::Cinder::Volume"
            }
        },
        {
            "id": "739f7012-7973-485b-b34f-b006bc336150",
            "virtualStorageDescId": "VirtualStorage",
            "storageResource": {
                # "vimConnectionId": omitted
                "resourceId": "res_id_VirtualStorage_2",
                "vimLevelResourceType": "OS::Cinder::Volume"
            }
        }
    ],
    "vnfcInfo": [
        {
            "id": "VDU2-vnfc_res_info_id_VDU2",
            "vduId": "VDU2",
            "vnfcResourceInfoId": "vnfc_res_info_id_VDU2",
            "vnfcState": "STARTED"
        },
        {
            "id": "VDU1-vnfc_res_info_id_VDU1_1",
            "vduId": "VDU1",
            "vnfcResourceInfoId": "vnfc_res_info_id_VDU1_1",
            "vnfcState": "STARTED"
        },
        {
            "id": "VDU1-vnfc_res_info_id_VDU1_2",
            "vduId": "VDU1",
            "vnfcResourceInfoId": "vnfc_res_info_id_VDU1_2",
            "vnfcState": "STARTED"
        }
    ]
}
# instantiatedVnfInfo example for CNF terminate
_inst_info_cnf_example = {
    "flavourId": "simple",
    "vnfState": "STARTED",
    "vnfcResourceInfo": [
        {
            "id": "c8cb522d-ddf8-4136-9c85-92bab8f2993d",
            "vduId": "VDU1",
            "computeResource": {
                "resourceId": "vdu1-5588797866-fs6vb",
                "vimLevelResourceType": "OS::Nova::Server"
            },
            "metadata": {
                "Pod": {
                    "name": "vdu1-5588797866-fs6vb",
                    "namespace": "curry"
                },
                "Deployment": {
                    "name": "vdu1",
                    "namespace": "curry"
                }
            }
        },
        {
            "id": "124e74c2-cc0d-f187-add2-2000326c195b",
            "vduId": "VDU1",
            "computeResource": {
                "resourceId": "vdu1-5588797866-v8sl2",
                "vimLevelResourceType": "Deployment",
            },
            "metadata": {
                "Pod": {
                    "name": "vdu1-5588797866-v8sl2",
                    "namespace": "curry"
                },
                "Deployment": {
                    "name": "vdu1",
                    "namespace": "curry"
                }
            }
        },
        {
            "id": "55008a17-956b-66a4-77e3-340723695bac",
            "vduId": "VDU2",
            "computeResource": {
                "resourceId": "vdu2",
                "vimLevelResourceType": "Pod",
            },
            "metadata": {
                "Pod": {
                    "name": "vdu2",
                    "namespace": "curry"
                }
            }
        }
    ]
}
# modify_info_process example
_modify_inst_example = {
    "vnfInstanceName": "instance_name",
    "vnfInstanceDescription": "description",
    "vnfdId": SAMPLE_VNFD_ID,
    "vnfProvider": "provider",
    "vnfProductName": "product name",
    "vnfSoftwareVersion": "software version",
    "vnfdVersion": "vnfd version",
    "vnfConfigurableProperties": {
        "vnfproperties": "example"
    },
    "metadata": {
        "metadata": "example",
    },
    "vimConnectionInfo": {
        "vim1": {
            "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_3",
            "vimId": "464bc3b0-5af3-40ef-bfb6-e84eee444313",
            "interfaceInfo": {"endpoint": "http://localhost/identity/v3"},
            "accessInfo": {
                "username": "nfv_user",
                "region": "RegionOne",
                "password": "devstack",
                "project": "nfv",
                "projectDomain": "Default",
                "userDomain": "Default"
            },
            "extra": {
                "key": "value"
            }
        }
    }
}


_modify_vnfc_info_example = {
    "vnfcInfo": [
        {
            "id": "VDU1-vnfc_res_info_id_VDU1",
            "vnfcConfigurableProperties": {"key": "value"}
        },
        {
            "id": "VDU2-vnfc_res_info_id_VDU2",
            "vnfcConfigurableProperties": {"key": "value"}
        }
    ]
}

# change_vnfpkg example
_change_vnfpkg_example = {
    "vnfdId": '61723406-6634-2fc0-060a-0b11104d2667',
    "additionalParams": {
        "upgrade_type": "RollingUpdate",
        "lcm-operation-coordinate-old-vnf": "./Scripts/coordinate_old_vnf.py",
        "lcm-operation-coordinate-old-vnf-class": "CoordinateOldVnf",
        "lcm-operation-coordinate-new-vnf": "./Scripts/coordinate_new_vnf.py",
        "lcm-operation-coordinate-new-vnf-class": "CoordinateNewVnf",
        "vdu_params": [{
            "vdu_id": "VDU1",
            "old_vnfc_param": {
                "cp_name": "CP1",
                "username": "ubuntu",
                "password": "ubuntu"},
            "new_vnfc_param": {
                "cp_name": "CP1",
                "username": "ubuntu",
                "password": "ubuntu"},
        }]
    }
}
_change_cnf_vnfpkg_example = {
    "vnfdId": 'ff60b74a-df4d-5c78-f5bf-19e129da8fff',
    "additionalParams": {
        "upgrade_type": "RollingUpdate",
        "lcm-operation-coordinate-old-vnf": "Scripts/coordinate_old_vnf.py",
        "lcm-operation-coordinate-old-vnf-class": "CoordinateOldVnf",
        "lcm-operation-coordinate-new-vnf": "Scripts/coordinate_new_vnf.py",
        "lcm-operation-coordinate-new-vnf-class": "CoordinateNewVnf",
        "lcm-kubernetes-def-files": [
            "Files/new_kubernetes/new_deployment.yaml"
        ],
        "vdu_params": [{
            "vduId": "VDU1"
        }]
    }
}
_update_resources = {
    "affectedVnfcs": [{
        "metadata": {
            "Deployment": {
                "name": "vdu1"
            }
        },
        "changeType": "ADDED"
    }]
}


class TestVnfLcmDriverV2(base.BaseTestCase):

    def setUp(self):
        super(TestVnfLcmDriverV2, self).setUp()
        objects.register_all()
        self.driver = vnflcm_driver_v2.VnfLcmDriverV2()
        self.context = context.get_admin_context()

        cur_dir = os.path.dirname(__file__)
        sample_dir = os.path.join(cur_dir, "..", "samples")

        self.vnfd_1 = vnfd_utils.Vnfd(SAMPLE_VNFD_ID)
        self.vnfd_1.init_from_csar_dir(os.path.join(sample_dir, "sample1"))

        self.vnfd_2 = vnfd_utils.Vnfd(CNF_SAMPLE_VNFD_ID)
        self.vnfd_2.init_from_csar_dir(os.path.join(sample_dir, "sample2"))

        self.vnfd_3 = vnfd_utils.Vnfd(CNF_SAMPLE_VNFD_ID)
        self.vnfd_3.init_from_csar_dir(os.path.join(sample_dir,
                                                    "change_vnfpkg_sample"))

    def _grant_req_links(self, lcmocc_id, inst_id):
        return {
            'vnfLcmOpOcc': {
                'href': '{}/vnflcm/v2/vnf_lcm_op_occs/{}'.format(
                    self.driver.endpoint, lcmocc_id)
            },
            'vnfInstance': {
                'href': '{}/vnflcm/v2/vnf_instances/{}'.format(
                    self.driver.endpoint, inst_id)
            }
        }

    @mock.patch.object(nfvo_client.NfvoClient, 'grant')
    def test_instantiate_grant(self, mocked_grant):
        # prepare
        req = objects.InstantiateVnfRequest.from_dict(_inst_req_example)
        inst = objects.VnfInstanceV2(
            # required fields
            id=uuidutils.generate_uuid(),
            vnfdId=SAMPLE_VNFD_ID,
            vnfProvider='provider',
            vnfProductName='product name',
            vnfSoftwareVersion='software version',
            vnfdVersion='vnfd version',
            instantiationState='NOT_INSTANTIATED'
        )
        lcmocc = objects.VnfLcmOpOccV2(
            # required fields
            id=uuidutils.generate_uuid(),
            operationState=fields.LcmOperationStateType.STARTING,
            stateEnteredTime=datetime.utcnow(),
            startTime=datetime.utcnow(),
            vnfInstanceId=inst.id,
            operation=fields.LcmOperationType.INSTANTIATE,
            isAutomaticInvocation=False,
            isCancelPending=False,
            operationParams=req)

        mocked_grant.return_value = objects.GrantV1()

        # run instantiate_grant
        grant_req, _ = self.driver.grant(
            self.context, lcmocc, inst, self.vnfd_1)

        # check grant_req is constructed according to intention
        grant_req = grant_req.to_dict()
        expected_fixed_items = {
            'vnfInstanceId': inst.id,
            'vnfLcmOpOccId': lcmocc.id,
            'vnfdId': SAMPLE_VNFD_ID,
            'flavourId': SAMPLE_FLAVOUR_ID,
            'operation': 'INSTANTIATE',
            'isAutomaticInvocation': False,
            'instantiationLevelId': 'instantiation_level_2',
            '_links': self._grant_req_links(lcmocc.id, inst.id)
        }
        for key, value in expected_fixed_items.items():
            self.assertEqual(value, grant_req[key])

        add_reses = grant_req['addResources']
        check_reses = {
            'COMPUTE': {'VDU1': [], 'VDU2': []},
            'STORAGE': {'VirtualStorage': []},
            'LINKPORT': {'VDU1_CP1': [], 'VDU1_CP2': [], 'VDU1_CP3': [],
                         'VDU1_CP4': [], 'VDU1_CP5': [],
                         'VDU2_CP1': [], 'VDU2_CP2': [], 'VDU2_CP3': [],
                         'VDU2_CP4': [], 'VDU2_CP5': []},
            # internalVL1 does not exist
            'VL': {'internalVL2': [], 'internalVL3': []}
        }
        expected_num = {
            'COMPUTE': {'VDU1': 3, 'VDU2': 1},
            'STORAGE': {'VirtualStorage': 3},
            'LINKPORT': {'VDU1_CP1': 3, 'VDU1_CP2': 3, 'VDU1_CP3': 3,
                         'VDU1_CP4': 3, 'VDU1_CP5': 3,
                         'VDU2_CP1': 1, 'VDU2_CP2': 1, 'VDU2_CP3': 1,
                         'VDU2_CP4': 1, 'VDU2_CP5': 1},
            'VL': {'internalVL2': 1, 'internalVL3': 1}
        }
        for res in add_reses:
            check_reses[res['type']][res['resourceTemplateId']].append(
                res['id'])

        for key, value in check_reses.items():
            for name, ids in value.items():
                self.assertEqual(expected_num[key][name], len(ids))

        expected_placement_constraints = [{
            'affinityOrAntiAffinity': 'ANTI_AFFINITY',
            'scope': 'NFVI_NODE',
            'resource': []}]
        vdu_def_ids = (check_reses['COMPUTE']['VDU1'] +
                       check_reses['COMPUTE']['VDU2'])
        for def_id in vdu_def_ids:
            expected_placement_constraints[0]['resource'].append(
                {'idType': 'GRANT', 'resourceId': def_id})
        self.assertEqual(expected_placement_constraints,
                         grant_req['placementConstraints'])

    @mock.patch.object(nfvo_client.NfvoClient, 'grant')
    def test_terminate_grant(self, mocked_grant):
        # prepare
        inst = objects.VnfInstanceV2(
            # required fields
            id=uuidutils.generate_uuid(),
            vnfdId=SAMPLE_VNFD_ID,
            vnfProvider='provider',
            vnfProductName='product name',
            vnfSoftwareVersion='software version',
            vnfdVersion='vnfd version',
            instantiationState='INSTANTIATED'
        )
        inst_info = objects.VnfInstanceV2_InstantiatedVnfInfo.from_dict(
            _inst_info_example)
        inst.instantiatedVnfInfo = inst_info
        req = objects.TerminateVnfRequest.from_dict(
            {"terminationType": "FORCEFUL"})
        lcmocc = objects.VnfLcmOpOccV2(
            # required fields
            id=uuidutils.generate_uuid(),
            operationState=fields.LcmOperationStateType.STARTING,
            stateEnteredTime=datetime.utcnow(),
            startTime=datetime.utcnow(),
            vnfInstanceId=inst.id,
            operation=fields.LcmOperationType.TERMINATE,
            isAutomaticInvocation=False,
            isCancelPending=False,
            operationParams=req)

        mocked_grant.return_value = objects.GrantV1()

        # run terminate_grant
        grant_req, _ = self.driver.grant(
            self.context, lcmocc, inst, self.vnfd_1)

        # check grant_req is constructed according to intention
        grant_req = grant_req.to_dict()
        expected_fixed_items = {
            'vnfInstanceId': inst.id,
            'vnfLcmOpOccId': lcmocc.id,
            'vnfdId': SAMPLE_VNFD_ID,
            'operation': 'TERMINATE',
            'isAutomaticInvocation': False,
            '_links': self._grant_req_links(lcmocc.id, inst.id)
        }
        for key, value in expected_fixed_items.items():
            self.assertEqual(value, grant_req[key])

        rm_reses = grant_req['removeResources']
        check_reses = {
            'COMPUTE': {'VDU1': [], 'VDU2': []},
            'STORAGE': {'VirtualStorage': []},
            'LINKPORT': {'VDU1_CP1': [], 'VDU1_CP2': [], 'VDU1_CP3': [],
                         'VDU1_CP4': [], 'VDU1_CP5': [],
                         'VDU2_CP1': [], 'VDU2_CP2': [], 'VDU2_CP3': [],
                         'VDU2_CP4': [], 'VDU2_CP5': []},
            'VL': {'internalVL2': [], 'internalVL3': []}
        }
        expected_res_ids = {
            'COMPUTE': {
                'VDU1': ['res_id_VDU1_1', 'res_id_VDU1_2'],
                'VDU2': ['res_id_VDU2']
            },
            'STORAGE': {
                'VirtualStorage': ['res_id_VirtualStorage_1',
                                   'res_id_VirtualStorage_2']
            },
            'LINKPORT': {
                'VDU1_CP1': ['res_id_VDU1_1_CP1'],
                'VDU1_CP2': ['res_id_VDU1_1_CP2', 'res_id_VDU1_2_CP2'],
                'VDU1_CP3': ['res_id_VDU1_1_CP3', 'res_id_VDU1_2_CP3'],
                'VDU1_CP4': ['res_id_VDU1_1_CP4', 'res_id_VDU1_2_CP4'],
                'VDU1_CP5': ['res_id_VDU1_1_CP5', 'res_id_VDU1_2_CP5'],
                'VDU2_CP1': ['res_id_VDU2_CP1'],
                'VDU2_CP2': ['res_id_VDU2_CP2'],
                'VDU2_CP3': ['res_id_VDU2_CP3'],
                'VDU2_CP4': ['res_id_VDU2_CP4'],
                'VDU2_CP5': ['res_id_VDU2_CP5']
            },
            'VL': {
                'internalVL2': ['res_id_internalVL2'],
                'internalVL3': ['res_id_internalVL3']
            }
        }
        for res in rm_reses:
            check_reses[res['type']][res['resourceTemplateId']].append(
                res['resource']['resourceId'])

        for key, value in check_reses.items():
            for name, ids in value.items():
                self.assertEqual(expected_res_ids[key][name], ids)

    def _scale_grant_prepare(self, scale_type):
        inst = objects.VnfInstanceV2(
            # required fields
            id=uuidutils.generate_uuid(),
            vnfdId=SAMPLE_VNFD_ID,
            vnfProvider='provider',
            vnfProductName='product name',
            vnfSoftwareVersion='software version',
            vnfdVersion='vnfd version',
            instantiationState='INSTANTIATED'
        )
        inst_info = objects.VnfInstanceV2_InstantiatedVnfInfo.from_dict(
            _inst_info_example)
        inst.instantiatedVnfInfo = inst_info
        req = objects.ScaleVnfRequest.from_dict(
            {"type": scale_type,
             "aspectId": "VDU1_scale",
             "numberOfSteps": 1})
        lcmocc = objects.VnfLcmOpOccV2(
            # required fields
            id=uuidutils.generate_uuid(),
            operationState=fields.LcmOperationStateType.STARTING,
            stateEnteredTime=datetime.utcnow(),
            startTime=datetime.utcnow(),
            vnfInstanceId=inst.id,
            operation=fields.LcmOperationType.SCALE,
            isAutomaticInvocation=False,
            isCancelPending=False,
            operationParams=req)

        return inst, lcmocc

    @mock.patch.object(nfvo_client.NfvoClient, 'grant')
    def test_scale_grant_scale_out(self, mocked_grant):
        # prepare
        inst, lcmocc = self._scale_grant_prepare('SCALE_OUT')
        mocked_grant.return_value = objects.GrantV1()

        # run scale_grant scale-out
        grant_req, _ = self.driver.grant(
            self.context, lcmocc, inst, self.vnfd_1)

        # check grant_req is constructed according to intention
        grant_req = grant_req.to_dict()
        expected_fixed_items = {
            'vnfInstanceId': inst.id,
            'vnfLcmOpOccId': lcmocc.id,
            'vnfdId': SAMPLE_VNFD_ID,
            'operation': 'SCALE',
            'isAutomaticInvocation': False,
            '_links': self._grant_req_links(lcmocc.id, inst.id)
        }
        for key, value in expected_fixed_items.items():
            self.assertEqual(value, grant_req[key])

        add_reses = grant_req['addResources']
        check_reses = {
            'COMPUTE': {'VDU1': []},
            'STORAGE': {'VirtualStorage': []},
            'LINKPORT': {'VDU1_CP1': [], 'VDU1_CP2': [], 'VDU1_CP3': [],
                         'VDU1_CP4': [], 'VDU1_CP5': []}
        }
        expected_num = {
            'COMPUTE': {'VDU1': 1},
            'STORAGE': {'VirtualStorage': 1},
            'LINKPORT': {'VDU1_CP1': 1, 'VDU1_CP2': 1, 'VDU1_CP3': 1,
                         'VDU1_CP4': 1, 'VDU1_CP5': 1}
        }
        for res in add_reses:
            check_reses[res['type']][res['resourceTemplateId']].append(
                res['id'])

        for key, value in check_reses.items():
            for name, ids in value.items():
                self.assertEqual(expected_num[key][name], len(ids))

    @mock.patch.object(nfvo_client.NfvoClient, 'grant')
    def test_scale_grant_scale_in(self, mocked_grant):
        # prepare
        inst, lcmocc = self._scale_grant_prepare('SCALE_IN')
        mocked_grant.return_value = objects.GrantV1()

        # run scale_grant scale-in
        grant_req, _ = self.driver.grant(
            self.context, lcmocc, inst, self.vnfd_1)

        # check grant_req is constructed according to intention
        grant_req = grant_req.to_dict()
        expected_fixed_items = {
            'vnfInstanceId': inst.id,
            'vnfLcmOpOccId': lcmocc.id,
            'vnfdId': SAMPLE_VNFD_ID,
            'operation': 'SCALE',
            'isAutomaticInvocation': False,
            '_links': self._grant_req_links(lcmocc.id, inst.id)
        }
        for key, value in expected_fixed_items.items():
            self.assertEqual(value, grant_req[key])

        rm_reses = grant_req['removeResources']
        check_reses = {
            'COMPUTE': {'VDU1': []},
            'STORAGE': {'VirtualStorage': []},
            'LINKPORT': {'VDU1_CP1': [], 'VDU1_CP2': [], 'VDU1_CP3': [],
                         'VDU1_CP4': [], 'VDU1_CP5': []}
        }
        expected_res_ids = {
            'COMPUTE': {
                'VDU1': ['res_id_VDU1_1']
            },
            'STORAGE': {
                'VirtualStorage': ['res_id_VirtualStorage_1']
            },
            'LINKPORT': {
                'VDU1_CP1': ['res_id_VDU1_1_CP1'],
                'VDU1_CP2': ['res_id_VDU1_1_CP2'],
                'VDU1_CP3': ['res_id_VDU1_1_CP3'],
                'VDU1_CP4': ['res_id_VDU1_1_CP4'],
                'VDU1_CP5': ['res_id_VDU1_1_CP5']
            }
        }
        for res in rm_reses:
            check_reses[res['type']][res['resourceTemplateId']].append(
                res['resource']['resourceId'])

        for key, value in check_reses.items():
            for name, ids in value.items():
                self.assertEqual(expected_res_ids[key][name], ids)

    def test_make_inst_info_common_instantiate(self):
        # prepare
        inst_saved = objects.VnfInstanceV2(
            # only set used members in the method
            instantiatedVnfInfo=objects.VnfInstanceV2_InstantiatedVnfInfo()
        )
        inst = inst_saved.obj_clone()
        req = objects.InstantiateVnfRequest.from_dict(_inst_req_example)
        lcmocc = objects.VnfLcmOpOccV2(
            # only set used members in the method
            operation=fields.LcmOperationType.INSTANTIATE,
            operationParams=req)

        # run _make_inst_info_common
        self.driver._make_inst_info_common(
            lcmocc, inst_saved, inst, self.vnfd_1)

        inst = inst.to_dict()
        expected_scale_status = [{'aspectId': 'VDU1_scale', 'scaleLevel': 2}]
        expected_max_scale_levels = [
            {'aspectId': 'VDU1_scale', 'scaleLevel': 2}]

        self.assertEqual(expected_scale_status,
                         inst['instantiatedVnfInfo']['scaleStatus'])
        self.assertEqual(expected_max_scale_levels,
                         inst['instantiatedVnfInfo']['maxScaleLevels'])

    def test_make_inst_info_common_scale(self):
        # prepare
        inst_saved = objects.VnfInstanceV2(
            # only set used members in the method
            instantiatedVnfInfo=objects.VnfInstanceV2_InstantiatedVnfInfo()
        )
        inst_saved.instantiatedVnfInfo.scaleStatus = [
            objects.ScaleInfoV2(aspectId='VDU1_scale', scaleLevel=2)
        ]
        inst_saved.instantiatedVnfInfo.maxScaleLevels = [
            objects.ScaleInfoV2(aspectId='VDU1_scale', scaleLevel=2)
        ]
        inst = objects.VnfInstanceV2(
            # only set used members in the method
            instantiatedVnfInfo=objects.VnfInstanceV2_InstantiatedVnfInfo()
        )
        req = objects.ScaleVnfRequest.from_dict(
            {"type": "SCALE_IN",
             "aspectId": "VDU1_scale",
             "numberOfSteps": 1})
        lcmocc = objects.VnfLcmOpOccV2(
            # only set used members in the method
            operation=fields.LcmOperationType.SCALE,
            operationParams=req)

        # run _make_inst_info_common
        self.driver._make_inst_info_common(
            lcmocc, inst_saved, inst, self.vnfd_1)

        inst = inst.to_dict()
        expected_scale_status = [{'aspectId': 'VDU1_scale', 'scaleLevel': 1}]
        expected_max_scale_levels = [
            {'aspectId': 'VDU1_scale', 'scaleLevel': 2}]

        self.assertEqual(expected_scale_status,
                         inst['instantiatedVnfInfo']['scaleStatus'])
        self.assertEqual(expected_max_scale_levels,
                         inst['instantiatedVnfInfo']['maxScaleLevels'])

    @mock.patch.object(nfvo_client.NfvoClient, 'get_vnf_package_info_vnfd')
    @mock.patch.object(nfvo_client.NfvoClient, 'get_vnfd')
    @mock.patch.object(vnfd_utils.Vnfd, 'get_vnfd_properties')
    def test_modify_info_process(self, mocked_get_vnfd_properties,
            mocked_get_vnfd, mocked_get_vnf_package_info_vnfd):
        new_vnfd_id = uuidutils.generate_uuid()
        pkg_info = objects.VnfPkgInfoV2(
            id=uuidutils.generate_uuid(),
            vnfdId=new_vnfd_id,
            vnfProvider="provider_1",
            vnfProductName="product_1",
            vnfSoftwareVersion="software version",
            vnfdVersion="vnfd version",
            operationalState="ENABLED"
        )
        new_vnfd_prop = {
            "vnfConfigurableProperties": {
                "vnfproperties": "example"
            },
            "metadata": {
                "metadata": "example",
                "metadata_2": "example"
            },
            "extensions": {
                "extensions": "example"
            },
        }
        mocked_get_vnf_package_info_vnfd.return_value = pkg_info
        mocked_get_vnfd.return_value = vnfd_utils.Vnfd(new_vnfd_id)
        mocked_get_vnfd_properties.return_value = new_vnfd_prop
        req = objects.VnfInfoModificationRequest.from_dict(
            {
                "vnfInstanceName": "instance_name",
                "vnfInstanceDescription": "description_1",
                "vnfdId": new_vnfd_id,
                "vnfConfigurableProperties": {
                    "vnfproperties": "example"
                },
                "metadata": {
                    "metadata_1": "example_1",
                    "metadata_2": None
                },
                "extensions": {
                    "extensions": "example_1"
                },
                "vimConnectionInfo": {
                    "vim1": {
                        "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_3",
                        "vimId": "464bc3b0-5af3-40ef-bfb6-e84eee444313",
                        "interfaceInfo": {
                            "endpoint": "http://localhost/identity/v3"
                        },
                        "accessInfo": {
                            "username": "nfv_user",
                            "region": "RegionOne",
                            "password": "devstack",
                            "project": "nfv",
                            "projectDomain": "Default",
                            "userDomain": "Default"
                        },
                        "extra": {
                            "key_add": "value"
                        }
                    }
                },
                "vnfcInfoModifications": [
                    {
                        "id": "VDU1-vnfc_res_info_id_VDU1",
                        "vnfcConfigurableProperties": {
                            "key": "value_mod",
                            "key_add": "value"
                        }
                    },
                    {
                        "id": "VDU2-vnfc_res_info_id_VDU2",
                        "vnfcConfigurableProperties": {
                            "key": None
                        }
                    }
                ]
            }
        )
        inst = objects.VnfInstanceV2.from_dict(_modify_inst_example)
        vnfc_info = objects.VnfInstanceV2_InstantiatedVnfInfo.from_dict(
            _modify_vnfc_info_example)
        inst.instantiatedVnfInfo = vnfc_info

        lcmocc = objects.VnfLcmOpOccV2(
            # required fields
            id=uuidutils.generate_uuid(),
            operationState=fields.LcmOperationStateType.PROCESSING,
            stateEnteredTime=datetime.utcnow(),
            startTime=datetime.utcnow(),
            operation=fields.LcmOperationType.MODIFY_INFO,
            isAutomaticInvocation=False,
            isCancelPending=False,
            operationParams=req)

        # run modify_info_process
        self.driver.modify_info_process(
            self.context, lcmocc, inst, None, None, self.vnfd_1)

        inst = inst.to_dict()
        expected_modify_result = {
            "vnfInstanceName": "instance_name",
            "vnfInstanceDescription": "description_1",
            "vnfdId": new_vnfd_id,
            "vnfProvider": "provider_1",
            "vnfProductName": "product_1",
            "vnfSoftwareVersion": "software version",
            "vnfdVersion": "vnfd version",
            "vnfConfigurableProperties": {
                "vnfproperties": "example"
            },
            "metadata": {
                "metadata": "example",
                "metadata_1": "example_1"
            },
            "extensions": {
                "extensions": "example_1"
            },
            "vimConnectionInfo": {
                "vim1": {
                    "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_3",
                    "vimId": "464bc3b0-5af3-40ef-bfb6-e84eee444313",
                    "interfaceInfo": {
                        "endpoint": "http://localhost/identity/v3"
                    },
                    "accessInfo": {
                        "username": "nfv_user",
                        "region": "RegionOne",
                        "password": "devstack",
                        "project": "nfv",
                        "projectDomain": "Default",
                        "userDomain": "Default"
                    },
                    "extra": {
                        "key": "value",
                        "key_add": "value"
                    }
                }
            },
            "instantiatedVnfInfo": {
                "vnfcInfo": [
                    {
                        "id": "VDU1-vnfc_res_info_id_VDU1",
                        "vnfcConfigurableProperties": {
                            "key": "value_mod",
                            "key_add": "value"
                        }
                    },
                    {
                        "id": "VDU2-vnfc_res_info_id_VDU2",
                        "vnfcConfigurableProperties": {
                        }
                    }
                ]
            }
        }

        self.assertEqual(expected_modify_result, inst)

    @mock.patch.object(nfvo_client.NfvoClient, 'get_vnf_package_info_vnfd')
    @mock.patch.object(nfvo_client.NfvoClient, 'get_vnfd')
    @mock.patch.object(vnfd_utils.Vnfd, 'get_vnfd_properties')
    def test_modify_info_process_from_vnfd_prop(self,
            mocked_get_vnfd_properties, mocked_get_vnfd,
            mocked_get_vnf_package_info_vnfd):
        new_vnfd_id = uuidutils.generate_uuid()
        pkg_info = objects.VnfPkgInfoV2(
            id=uuidutils.generate_uuid(),
            vnfdId=new_vnfd_id,
            vnfProvider="provider_1",
            vnfProductName="product_1",
            vnfSoftwareVersion="software version",
            vnfdVersion="vnfd version",
            operationalState="ENABLED"
        )
        new_vnfd_prop = {}

        mocked_get_vnf_package_info_vnfd.return_value = pkg_info
        mocked_get_vnfd.return_value = vnfd_utils.Vnfd(new_vnfd_id)
        mocked_get_vnfd_properties.return_value = new_vnfd_prop
        req = objects.VnfInfoModificationRequest.from_dict(
            {
                "vnfInstanceName": "instance_name",
                "vnfInstanceDescription": "description_1",
                "vnfdId": new_vnfd_id,
                "vimConnectionInfo": {
                    "vim1": {
                        "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_3",
                        "vimId": "464bc3b0-5af3-40ef-bfb6-e84eee444313",
                        "interfaceInfo": {
                            "endpoint": "http://localhost/identity/v3"
                        },
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
        )
        inst = objects.VnfInstanceV2.from_dict(_modify_inst_example)
        lcmocc = objects.VnfLcmOpOccV2(
            # required fields
            id=uuidutils.generate_uuid(),
            operationState=fields.LcmOperationStateType.PROCESSING,
            stateEnteredTime=datetime.utcnow(),
            startTime=datetime.utcnow(),
            operation=fields.LcmOperationType.MODIFY_INFO,
            isAutomaticInvocation=False,
            isCancelPending=False,
            operationParams=req)

        # run modify_info_process
        self.driver.modify_info_process(
            self.context, lcmocc, inst, None, None, self.vnfd_1)

        inst = inst.to_dict()
        expected_modify_result = {
            "vnfInstanceName": "instance_name",
            "vnfInstanceDescription": "description_1",
            "vnfdId": new_vnfd_id,
            "vnfProvider": "provider_1",
            "vnfProductName": "product_1",
            "vnfSoftwareVersion": "software version",
            "vnfdVersion": "vnfd version",
            "vnfConfigurableProperties": {},
            "metadata": {},
            "vimConnectionInfo": {
                "vim1": {
                    "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_3",
                    "vimId": "464bc3b0-5af3-40ef-bfb6-e84eee444313",
                    "interfaceInfo": {
                        "endpoint": "http://localhost/identity/v3"
                    },
                    "accessInfo": {
                        "username": "nfv_user",
                        "region": "RegionOne",
                        "password": "devstack",
                        "project": "nfv",
                        "projectDomain": "Default",
                        "userDomain": "Default"
                    },
                    "extra": {
                        "key": "value"
                    }
                }
            }
        }

        self.assertEqual(expected_modify_result, inst)

    @mock.patch.object(nfvo_client.NfvoClient, 'grant')
    def test_change_ext_conn_grant(self, mocked_grant):
        # prepare
        req = objects.ChangeExtVnfConnectivityRequest.from_dict(
            _change_ext_conn_req_example)
        inst = objects.VnfInstanceV2(
            # required fields
            id=uuidutils.generate_uuid(),
            vnfdId=SAMPLE_VNFD_ID,
            vnfProvider='provider',
            vnfProductName='product name',
            vnfSoftwareVersion='software version',
            vnfdVersion='vnfd version',
            instantiationState='INSTANTIATED'
        )
        inst_info = objects.VnfInstanceV2_InstantiatedVnfInfo.from_dict(
            _inst_info_example)
        inst.instantiatedVnfInfo = inst_info
        lcmocc = objects.VnfLcmOpOccV2(
            # required fields
            id=uuidutils.generate_uuid(),
            operationState=fields.LcmOperationStateType.STARTING,
            stateEnteredTime=datetime.utcnow(),
            startTime=datetime.utcnow(),
            vnfInstanceId=inst.id,
            operation=fields.LcmOperationType.CHANGE_EXT_CONN,
            isAutomaticInvocation=False,
            isCancelPending=False,
            operationParams=req
        )

        mocked_grant.return_value = objects.GrantV1()

        # run change_ext_conn_grant
        grant_req, _ = self.driver.grant(
            self.context, lcmocc, inst, self.vnfd_1)

        # check grant_req is constructed according to intention
        grant_req = grant_req.to_dict()
        expected_fixed_items = {
            'vnfInstanceId': inst.id,
            'vnfLcmOpOccId': lcmocc.id,
            'vnfdId': SAMPLE_VNFD_ID,
            'operation': 'CHANGE_EXT_CONN',
            'isAutomaticInvocation': False,
            '_links': self._grant_req_links(lcmocc.id, inst.id)
        }
        for key, value in expected_fixed_items.items():
            self.assertEqual(value, grant_req[key])

        # check updateResources
        update_reses = grant_req['updateResources']
        check_reses = {
            'COMPUTE': {'VDU1': [], 'VDU2': []}
        }
        expected_res_ids = {
            'COMPUTE': {
                'VDU1': ['res_id_VDU1_1', 'res_id_VDU1_2'],
                'VDU2': ['res_id_VDU2']
            }
        }
        for res in update_reses:
            check_reses[res['type']][res['resourceTemplateId']].append(
                res['resource']['resourceId'])

        for key, value in check_reses.items():
            for name, ids in value.items():
                self.assertEqual(expected_res_ids[key][name], ids)

        # check removeResources
        rm_reses = grant_req['removeResources']
        check_reses = {
            'LINKPORT': {'VDU1_CP2': [], 'VDU2_CP1': []}
        }
        expected_res_ids = {
            'LINKPORT': {
                'VDU1_CP2': ['res_id_VDU1_1_CP2', 'res_id_VDU1_2_CP2'],
                'VDU2_CP1': ['res_id_VDU2_CP1']
            }
        }
        for res in rm_reses:
            check_reses[res['type']][res['resourceTemplateId']].append(
                res['resource']['resourceId'])

        for key, value in check_reses.items():
            for name, ids in value.items():
                self.assertEqual(expected_res_ids[key][name], ids)

        # check addResources
        add_reses = grant_req['addResources']
        check_reses = {
            'LINKPORT': {'VDU1_CP2': []}
        }
        expected_num = {
            'LINKPORT': {'VDU1_CP2': 2}
        }
        for res in add_reses:
            check_reses[res['type']][res['resourceTemplateId']].append(
                res['id'])

        for key, value in check_reses.items():
            for name, ids in value.items():
                self.assertEqual(expected_num[key][name], len(ids))

    def _heal_grant_prepare(self, req):
        inst = objects.VnfInstanceV2(
            # required fields
            id=uuidutils.generate_uuid(),
            vnfdId=SAMPLE_VNFD_ID,
            vnfProvider='provider',
            vnfProductName='product name',
            vnfSoftwareVersion='software version',
            vnfdVersion='vnfd version',
            instantiationState='INSTANTIATED'
        )
        inst_info = objects.VnfInstanceV2_InstantiatedVnfInfo.from_dict(
            _inst_info_example)
        inst.instantiatedVnfInfo = inst_info
        lcmocc = objects.VnfLcmOpOccV2(
            # required fields
            id=uuidutils.generate_uuid(),
            operationState=fields.LcmOperationStateType.STARTING,
            stateEnteredTime=datetime.utcnow(),
            startTime=datetime.utcnow(),
            vnfInstanceId=inst.id,
            operation=fields.LcmOperationType.HEAL,
            isAutomaticInvocation=False,
            isCancelPending=False,
            operationParams=req)

        return inst, lcmocc

    @mock.patch.object(nfvo_client.NfvoClient, 'grant')
    def test_heal_grant_SOL002(self, mocked_grant):
        # prepare
        req = objects.HealVnfRequest(
            vnfcInstanceId=["VDU1-vnfc_res_info_id_VDU1_2",
                            "VDU2-vnfc_res_info_id_VDU2"]
        )
        inst, lcmocc = self._heal_grant_prepare(req)
        mocked_grant.return_value = objects.GrantV1()

        # run heal_grant
        grant_req, _ = self.driver.grant(
            self.context, lcmocc, inst, self.vnfd_1)

        # check grant_req is constructed according to intention
        grant_req = grant_req.to_dict()
        expected_fixed_items = {
            'vnfInstanceId': inst.id,
            'vnfLcmOpOccId': lcmocc.id,
            'vnfdId': SAMPLE_VNFD_ID,
            'operation': 'HEAL',
            'isAutomaticInvocation': False,
            '_links': self._grant_req_links(lcmocc.id, inst.id)
        }
        for key, value in expected_fixed_items.items():
            self.assertEqual(value, grant_req[key])

        # check removeResources
        rm_reses = grant_req['removeResources']
        check_reses = {
            'COMPUTE': {'VDU1': [], 'VDU2': []}
        }
        expected_res_ids = {
            'COMPUTE': {
                'VDU1': ['res_id_VDU1_2'],
                'VDU2': ['res_id_VDU2']
            }
        }
        for res in rm_reses:
            check_reses[res['type']][res['resourceTemplateId']].append(
                res['resource']['resourceId'])

        for key, value in check_reses.items():
            for name, ids in value.items():
                self.assertEqual(expected_res_ids[key][name], ids)

        # check addResources
        add_reses = grant_req['addResources']
        check_reses = {
            'COMPUTE': {'VDU1': [], 'VDU2': []}
        }
        for res in add_reses:
            check_reses[res['type']][res['resourceTemplateId']].append(
                res['id'])

        for key, value in check_reses.items():
            for name, ids in value.items():
                self.assertEqual(len(expected_res_ids[key][name]), len(ids))

    @mock.patch.object(nfvo_client.NfvoClient, 'grant')
    def test_heal_grant_SOL002_all(self, mocked_grant):
        # prepare
        req = objects.HealVnfRequest(
            vnfcInstanceId=["VDU1-vnfc_res_info_id_VDU1_2",
                            "VDU2-vnfc_res_info_id_VDU2"],
            additionalParams={'all': True}
        )
        inst, lcmocc = self._heal_grant_prepare(req)
        mocked_grant.return_value = objects.GrantV1()

        # run heal_grant
        grant_req, _ = self.driver.grant(
            self.context, lcmocc, inst, self.vnfd_1)

        # check grant_req is constructed according to intention
        grant_req = grant_req.to_dict()
        expected_fixed_items = {
            'vnfInstanceId': inst.id,
            'vnfLcmOpOccId': lcmocc.id,
            'vnfdId': SAMPLE_VNFD_ID,
            'operation': 'HEAL',
            'isAutomaticInvocation': False,
            '_links': self._grant_req_links(lcmocc.id, inst.id)
        }
        for key, value in expected_fixed_items.items():
            self.assertEqual(value, grant_req[key])

        # check removeResources
        rm_reses = grant_req['removeResources']
        check_reses = {
            'COMPUTE': {'VDU1': [], 'VDU2': []},
            'STORAGE': {'VirtualStorage': []}
        }
        expected_res_ids = {
            'COMPUTE': {
                'VDU1': ['res_id_VDU1_2'],
                'VDU2': ['res_id_VDU2']
            },
            'STORAGE': {
                'VirtualStorage': ['res_id_VirtualStorage_2']
            }
        }
        for res in rm_reses:
            check_reses[res['type']][res['resourceTemplateId']].append(
                res['resource']['resourceId'])

        for key, value in check_reses.items():
            for name, ids in value.items():
                self.assertEqual(expected_res_ids[key][name], ids)

        # check addResources
        add_reses = grant_req['addResources']
        check_reses = {
            'COMPUTE': {'VDU1': [], 'VDU2': []},
            'STORAGE': {'VirtualStorage': []}
        }
        for res in add_reses:
            check_reses[res['type']][res['resourceTemplateId']].append(
                res['id'])

        for key, value in check_reses.items():
            for name, ids in value.items():
                self.assertEqual(len(expected_res_ids[key][name]), len(ids))

    @mock.patch.object(nfvo_client.NfvoClient, 'grant')
    def test_heal_grant_SOL003(self, mocked_grant):
        # prepare
        req = objects.HealVnfRequest()
        inst, lcmocc = self._heal_grant_prepare(req)
        mocked_grant.return_value = objects.GrantV1()

        # run heal_grant
        grant_req, _ = self.driver.grant(
            self.context, lcmocc, inst, self.vnfd_1)

        # check grant_req is constructed according to intention
        grant_req = grant_req.to_dict()
        expected_fixed_items = {
            'vnfInstanceId': inst.id,
            'vnfLcmOpOccId': lcmocc.id,
            'vnfdId': SAMPLE_VNFD_ID,
            'operation': 'HEAL',
            'isAutomaticInvocation': False,
            '_links': self._grant_req_links(lcmocc.id, inst.id)
        }
        for key, value in expected_fixed_items.items():
            self.assertEqual(value, grant_req[key])

        # check removeResources
        rm_reses = grant_req['removeResources']
        check_reses = {
            'COMPUTE': {'VDU1': [], 'VDU2': []}
        }
        expected_res_ids = {
            'COMPUTE': {
                'VDU1': ['res_id_VDU1_1', 'res_id_VDU1_2'],
                'VDU2': ['res_id_VDU2']
            }
        }
        for res in rm_reses:
            check_reses[res['type']][res['resourceTemplateId']].append(
                res['resource']['resourceId'])

        for key, value in check_reses.items():
            for name, ids in value.items():
                self.assertEqual(expected_res_ids[key][name], ids)

        # check addResources
        add_reses = grant_req['addResources']
        check_reses = {
            'COMPUTE': {'VDU1': [], 'VDU2': []}
        }
        for res in add_reses:
            check_reses[res['type']][res['resourceTemplateId']].append(
                res['id'])

        for key, value in check_reses.items():
            for name, ids in value.items():
                self.assertEqual(len(expected_res_ids[key][name]), len(ids))

    @mock.patch.object(nfvo_client.NfvoClient, 'grant')
    def test_heal_grant_SOL003_all(self, mocked_grant):
        # prepare
        req = objects.HealVnfRequest(
            additionalParams={'all': True}
        )
        inst, lcmocc = self._heal_grant_prepare(req)
        mocked_grant.return_value = objects.GrantV1()

        # run heal_grant
        grant_req, _ = self.driver.grant(
            self.context, lcmocc, inst, self.vnfd_1)

        # check grant_req is constructed according to intention
        grant_req = grant_req.to_dict()
        expected_fixed_items = {
            'vnfInstanceId': inst.id,
            'vnfLcmOpOccId': lcmocc.id,
            'vnfdId': SAMPLE_VNFD_ID,
            'operation': 'HEAL',
            'isAutomaticInvocation': False,
            '_links': self._grant_req_links(lcmocc.id, inst.id)
        }
        for key, value in expected_fixed_items.items():
            self.assertEqual(value, grant_req[key])

        # check removeResources
        rm_reses = grant_req['removeResources']
        check_reses = {
            'COMPUTE': {'VDU1': [], 'VDU2': []},
            'STORAGE': {'VirtualStorage': []},
            'LINKPORT': {'VDU1_CP1': [], 'VDU1_CP2': [], 'VDU1_CP3': [],
                         'VDU1_CP4': [], 'VDU1_CP5': [],
                         'VDU2_CP1': [], 'VDU2_CP2': [], 'VDU2_CP3': [],
                         'VDU2_CP4': [], 'VDU2_CP5': []},
            'VL': {'internalVL2': [], 'internalVL3': []}
        }
        expected_res_ids = {
            'COMPUTE': {
                'VDU1': ['res_id_VDU1_1', 'res_id_VDU1_2'],
                'VDU2': ['res_id_VDU2']
            },
            'STORAGE': {
                'VirtualStorage': ['res_id_VirtualStorage_1',
                                   'res_id_VirtualStorage_2']
            },
            'LINKPORT': {
                'VDU1_CP1': ['res_id_VDU1_1_CP1'],
                'VDU1_CP2': ['res_id_VDU1_1_CP2', 'res_id_VDU1_2_CP2'],
                'VDU1_CP3': ['res_id_VDU1_1_CP3', 'res_id_VDU1_2_CP3'],
                'VDU1_CP4': ['res_id_VDU1_1_CP4', 'res_id_VDU1_2_CP4'],
                'VDU1_CP5': ['res_id_VDU1_1_CP5', 'res_id_VDU1_2_CP5'],
                'VDU2_CP1': ['res_id_VDU2_CP1'],
                'VDU2_CP2': ['res_id_VDU2_CP2'],
                'VDU2_CP3': ['res_id_VDU2_CP3'],
                'VDU2_CP4': ['res_id_VDU2_CP4'],
                'VDU2_CP5': ['res_id_VDU2_CP5']
            },
            'VL': {
                'internalVL2': ['res_id_internalVL2'],
                'internalVL3': ['res_id_internalVL3']
            }
        }
        for res in rm_reses:
            check_reses[res['type']][res['resourceTemplateId']].append(
                res['resource']['resourceId'])

        for key, value in check_reses.items():
            for name, ids in value.items():
                self.assertEqual(expected_res_ids[key][name], ids)

        # check addResources
        add_reses = grant_req['addResources']
        check_reses = {
            'COMPUTE': {'VDU1': [], 'VDU2': []},
            'STORAGE': {'VirtualStorage': []},
            'LINKPORT': {'VDU1_CP1': [], 'VDU1_CP2': [], 'VDU1_CP3': [],
                         'VDU1_CP4': [], 'VDU1_CP5': [],
                         'VDU2_CP1': [], 'VDU2_CP2': [], 'VDU2_CP3': [],
                         'VDU2_CP4': [], 'VDU2_CP5': []},
            'VL': {'internalVL2': [], 'internalVL3': []}
        }
        for res in add_reses:
            check_reses[res['type']][res['resourceTemplateId']].append(
                res['id'])

        for key, value in check_reses.items():
            for name, ids in value.items():
                self.assertEqual(len(expected_res_ids[key][name]), len(ids))

    @mock.patch.object(nfvo_client.NfvoClient, 'grant')
    def test_change_vnfpkg_grant_update_reses(self, mocked_grant):
        # prepare
        inst = objects.VnfInstanceV2(
            # required fields
            id=uuidutils.generate_uuid(),
            vnfdId=SAMPLE_VNFD_ID,
            vnfProvider='provider',
            vnfProductName='product name',
            vnfSoftwareVersion='software version',
            vnfdVersion='vnfd version',
            instantiationState='INSTANTIATED'
        )
        inst_info = objects.VnfInstanceV2_InstantiatedVnfInfo.from_dict(
            _inst_info_example)
        inst.instantiatedVnfInfo = inst_info
        req = objects.ChangeCurrentVnfPkgRequest.from_dict(
            _change_vnfpkg_example)
        lcmocc = objects.VnfLcmOpOccV2(
            # required fields
            id=uuidutils.generate_uuid(),
            operationState=fields.LcmOperationStateType.PROCESSING,
            stateEnteredTime=datetime.utcnow(),
            startTime=datetime.utcnow(),
            vnfInstanceId=inst.id,
            operation=fields.LcmOperationType.CHANGE_VNFPKG,
            isAutomaticInvocation=False,
            isCancelPending=False,
            operationParams=req)

        mocked_grant.return_value = objects.GrantV1()

        # run change_vnfpkg_grant
        grant_req, _ = self.driver.grant(
            self.context, lcmocc, inst, self.vnfd_1)

        # check grant_req is constructed according to intention
        grant_req = grant_req.to_dict()
        expected_fixed_items = {
            'vnfInstanceId': inst.id,
            'vnfLcmOpOccId': lcmocc.id,
            'vnfdId': '61723406-6634-2fc0-060a-0b11104d2667',
            'operation': 'CHANGE_VNFPKG',
            'isAutomaticInvocation': False
        }
        for key, value in expected_fixed_items.items():
            self.assertEqual(value, grant_req[key])

        update_reses = grant_req['updateResources']
        target_vdu_list = [
            vdu_param.get(
                'vdu_id') for vdu_param in req.additionalParams.get(
                'vdu_params')]
        for i in range(len(update_reses)):
            self.assertEqual('COMPUTE', update_reses[i]['type'])
            for target_vdu in target_vdu_list:
                self.assertEqual(target_vdu,
                                 update_reses[i]['resourceTemplateId'])

    @mock.patch.object(nfvo_client.NfvoClient, 'grant')
    def test_change_vnfpkg_grant_add_reses(self, mocked_grant):
        # prepare
        inst = objects.VnfInstanceV2(
            # required fields
            id=uuidutils.generate_uuid(),
            vnfdId=SAMPLE_VNFD_ID,
            vnfProvider='provider',
            vnfProductName='product name',
            vnfSoftwareVersion='software version',
            vnfdVersion='vnfd version',
            instantiationState='INSTANTIATED'
        )
        inst_info = objects.VnfInstanceV2_InstantiatedVnfInfo.from_dict(
            _inst_info_example)
        inst.instantiatedVnfInfo = inst_info
        req = objects.ChangeCurrentVnfPkgRequest.from_dict(
            _change_vnfpkg_example)
        lcmocc = objects.VnfLcmOpOccV2(
            # required fields
            id=uuidutils.generate_uuid(),
            operationState=fields.LcmOperationStateType.PROCESSING,
            stateEnteredTime=datetime.utcnow(),
            startTime=datetime.utcnow(),
            vnfInstanceId=inst.id,
            operation=fields.LcmOperationType.CHANGE_VNFPKG,
            isAutomaticInvocation=False,
            isCancelPending=False,
            operationParams=req)

        mocked_grant.return_value = objects.GrantV1()

        # run change_vnfpkg_grant
        grant_req, _ = self.driver.grant(
            self.context, lcmocc, inst, self.vnfd_1)

        # check grant_req is constructed according to intention
        grant_req = grant_req.to_dict()
        expected_fixed_items = {
            'vnfInstanceId': inst.id,
            'vnfLcmOpOccId': lcmocc.id,
            'vnfdId': '61723406-6634-2fc0-060a-0b11104d2667',
            'operation': 'CHANGE_VNFPKG',
            'isAutomaticInvocation': False
        }
        for key, value in expected_fixed_items.items():
            self.assertEqual(value, grant_req[key])

        add_reses = grant_req['addResources']
        for inst_vnc in inst_info.vnfcResourceInfo:
            nodes = self.vnfd_1.get_vdu_nodes(inst_info.flavourId)
            vdu_storage_names = self.vnfd_1.get_vdu_storages(
                nodes[inst_vnc.vduId])
            for i in range(len(add_reses)):
                self.assertEqual('STORAGE', add_reses[i]['type'])
                for vdu_storage_name in vdu_storage_names:
                    self.assertEqual(vdu_storage_name,
                                     add_reses[i]['resourceTemplateId'])

    @mock.patch.object(nfvo_client.NfvoClient, 'grant')
    def test_change_vnfpkg_grant_remove_reses(self, mocked_grant):
        # prepare
        inst = objects.VnfInstanceV2(
            # required fields
            id=uuidutils.generate_uuid(),
            vnfdId=SAMPLE_VNFD_ID,
            vnfProvider='provider',
            vnfProductName='product name',
            vnfSoftwareVersion='software version',
            vnfdVersion='vnfd version',
            instantiationState='INSTANTIATED'
        )
        inst_info = objects.VnfInstanceV2_InstantiatedVnfInfo.from_dict(
            _inst_info_example)
        inst.instantiatedVnfInfo = inst_info
        req = objects.ChangeCurrentVnfPkgRequest.from_dict(
            _change_vnfpkg_example)
        lcmocc = objects.VnfLcmOpOccV2(
            # required fields
            id=uuidutils.generate_uuid(),
            operationState=fields.LcmOperationStateType.PROCESSING,
            stateEnteredTime=datetime.utcnow(),
            startTime=datetime.utcnow(),
            vnfInstanceId=inst.id,
            operation=fields.LcmOperationType.CHANGE_VNFPKG,
            isAutomaticInvocation=False,
            isCancelPending=False,
            operationParams=req)

        mocked_grant.return_value = objects.GrantV1()

        # run change_vnfpkg_grant
        grant_req, _ = self.driver.grant(
            self.context, lcmocc, inst, self.vnfd_1)

        # check grant_req is constructed according to intention
        grant_req = grant_req.to_dict()
        expected_fixed_items = {
            'vnfInstanceId': inst.id,
            'vnfLcmOpOccId': lcmocc.id,
            'vnfdId': '61723406-6634-2fc0-060a-0b11104d2667',
            'operation': 'CHANGE_VNFPKG',
            'isAutomaticInvocation': False
        }
        for key, value in expected_fixed_items.items():
            self.assertEqual(value, grant_req[key])

        remove_reses = grant_req['removeResources']
        inst_stor_info = inst_info.virtualStorageResourceInfo
        check_reses = []
        for str_info in inst_stor_info:
            check_res = {
                'resourceId': str_info.storageResource.resourceId,
                'vimLevelResourceType':
                    str_info.storageResource.vimLevelResourceType
            }
            check_reses.append(check_res)
            for i in range(len(remove_reses)):
                self.assertEqual('STORAGE', remove_reses[i]['type'])
                self.assertEqual(str_info.virtualStorageDescId,
                                 remove_reses[i]['resourceTemplateId'])
        for j in range(len(check_reses)):
            for k in range(len(remove_reses)):
                if j == k:
                    self.assertEqual(
                        check_reses[j]['resourceId'],
                        remove_reses[j]['resource']['resourceId'])
                    self.assertEqual(
                        check_reses[j]['vimLevelResourceType'],
                        remove_reses[j]['resource']['vimLevelResourceType'])

    @mock.patch.object(nfvo_client.NfvoClient, 'grant')
    def test_cnf_instantiate_grant(self, mocked_grant):
        # prepare
        req = objects.InstantiateVnfRequest.from_dict(_inst_cnf_req_example)
        inst = objects.VnfInstanceV2(
            # required fields
            id=uuidutils.generate_uuid(),
            vnfdId=CNF_SAMPLE_VNFD_ID,
            vnfProvider='provider',
            vnfProductName='product name',
            vnfSoftwareVersion='software version',
            vnfdVersion='vnfd version',
            instantiationState='NOT_INSTANTIATED'
        )
        lcmocc = objects.VnfLcmOpOccV2(
            # required fields
            id=uuidutils.generate_uuid(),
            operationState=fields.LcmOperationStateType.STARTING,
            stateEnteredTime=datetime.utcnow(),
            startTime=datetime.utcnow(),
            vnfInstanceId=inst.id,
            operation=fields.LcmOperationType.INSTANTIATE,
            isAutomaticInvocation=False,
            isCancelPending=False,
            operationParams=req)

        mocked_grant.return_value = objects.GrantV1()

        # run instantiate_grant
        grant_req, _ = self.driver.grant(
            self.context, lcmocc, inst, self.vnfd_2)

        # check grant_req is constructed according to intention
        grant_req = grant_req.to_dict()
        expected_fixed_items = {
            'vnfInstanceId': inst.id,
            'vnfLcmOpOccId': lcmocc.id,
            'vnfdId': CNF_SAMPLE_VNFD_ID,
            'flavourId': SAMPLE_FLAVOUR_ID,
            'operation': 'INSTANTIATE',
            'isAutomaticInvocation': False,
            '_links': self._grant_req_links(lcmocc.id, inst.id)
        }
        for key, value in expected_fixed_items.items():
            self.assertEqual(value, grant_req[key])

        add_reses = grant_req['addResources']
        check_reses = {
            'COMPUTE': {'VDU1': [], 'VDU2': []}
        }
        expected_num = {
            'COMPUTE': {'VDU1': 2, 'VDU2': 1}
        }
        for res in add_reses:
            check_reses[res['type']][res['resourceTemplateId']].append(
                res['id'])

        for key, value in check_reses.items():
            for name, ids in value.items():
                self.assertEqual(expected_num[key][name], len(ids))

    @mock.patch.object(nfvo_client.NfvoClient, 'grant')
    def test_cnf_terminate_grant(self, mocked_grant):
        # prepare
        inst = objects.VnfInstanceV2(
            # required fields
            id=uuidutils.generate_uuid(),
            vnfdId=CNF_SAMPLE_VNFD_ID,
            vnfProvider='provider',
            vnfProductName='product name',
            vnfSoftwareVersion='software version',
            vnfdVersion='vnfd version',
            instantiationState='INSTANTIATED'
        )
        inst_info = objects.VnfInstanceV2_InstantiatedVnfInfo.from_dict(
            _inst_info_cnf_example)
        inst.instantiatedVnfInfo = inst_info
        req = objects.TerminateVnfRequest.from_dict(
            {"terminationType": "FORCEFUL"})
        lcmocc = objects.VnfLcmOpOccV2(
            # required fields
            id=uuidutils.generate_uuid(),
            operationState=fields.LcmOperationStateType.STARTING,
            stateEnteredTime=datetime.utcnow(),
            startTime=datetime.utcnow(),
            vnfInstanceId=inst.id,
            operation=fields.LcmOperationType.TERMINATE,
            isAutomaticInvocation=False,
            isCancelPending=False,
            operationParams=req)

        mocked_grant.return_value = objects.GrantV1()

        # run terminate_grant
        grant_req, _ = self.driver.grant(
            self.context, lcmocc, inst, self.vnfd_2)

        # check grant_req is constructed according to intention
        grant_req = grant_req.to_dict()
        expected_fixed_items = {
            'vnfInstanceId': inst.id,
            'vnfLcmOpOccId': lcmocc.id,
            'vnfdId': CNF_SAMPLE_VNFD_ID,
            'operation': 'TERMINATE',
            'isAutomaticInvocation': False,
            '_links': self._grant_req_links(lcmocc.id, inst.id)
        }
        for key, value in expected_fixed_items.items():
            self.assertEqual(value, grant_req[key])

        rm_reses = grant_req['removeResources']
        check_reses = {
            'COMPUTE': {'VDU1': [], 'VDU2': []}
        }
        expected_res_ids = {
            'COMPUTE': {
                'VDU1': ['vdu1-5588797866-fs6vb', 'vdu1-5588797866-v8sl2'],
                'VDU2': ['vdu2']
            }
        }
        for res in rm_reses:
            check_reses[res['type']][res['resourceTemplateId']].append(
                res['resource']['resourceId'])

        for key, value in check_reses.items():
            for name, ids in value.items():
                self.assertEqual(expected_res_ids[key][name], ids)

    @mock.patch.object(kubernetes.Kubernetes, 'change_vnfpkg')
    @mock.patch.object(nfvo_client.NfvoClient, 'get_vnfd')
    def test_cnf_change_vnfpkg(self, mock_vnfd, mock_change_vnfpkg):
        # prepare
        req_inst = objects.InstantiateVnfRequest.from_dict(
            _inst_cnf_req_example)
        inst = objects.VnfInstanceV2(
            # required fields
            id=uuidutils.generate_uuid(),
            vnfdId=CNF_SAMPLE_VNFD_ID,
            vnfProvider='provider',
            vnfProductName='product name',
            vnfSoftwareVersion='software version',
            vnfdVersion='vnfd version',
            instantiationState='INSTANTIATED',
            vimConnectionInfo=req_inst.vimConnectionInfo,
            metadata={'lcm-kubernetes-def-files': [
                'Files/kubernetes/deployment.yaml']}
        )
        inst_info = objects.VnfInstanceV2_InstantiatedVnfInfo.from_dict(
            _inst_info_cnf_example)
        inst.instantiatedVnfInfo = inst_info

        req = objects.ChangeCurrentVnfPkgRequest.from_dict(
            _change_cnf_vnfpkg_example)
        grant_req = objects.GrantRequestV1(
            operation=fields.LcmOperationType.CHANGE_VNFPKG
        )
        grant = objects.GrantV1()
        lcmocc = objects.VnfLcmOpOccV2(
            # required fields
            id=uuidutils.generate_uuid(),
            operationState=fields.LcmOperationStateType.STARTING,
            stateEnteredTime=datetime.utcnow(),
            startTime=datetime.utcnow(),
            vnfInstanceId=inst.id,
            operation=fields.LcmOperationType.CHANGE_VNFPKG,
            isAutomaticInvocation=False,
            isCancelPending=False,
            operationParams=req)
        mock_vnfd.return_value = self.vnfd_2
        self.driver.change_vnfpkg_process(
            self.context, lcmocc, inst, grant_req, grant, self.vnfd_3)
