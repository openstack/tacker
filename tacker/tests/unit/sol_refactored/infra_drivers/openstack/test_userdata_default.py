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
import os

from oslo_utils import uuidutils

from tacker import context
from tacker.sol_refactored.api import api_version
from tacker.sol_refactored.infra_drivers.openstack import userdata_default
from tacker.sol_refactored import objects
from tacker.sol_refactored.objects.v2 import fields
from tacker.tests import base
from tacker.tests import utils


SAMPLE_VNFD_ID = "b1bb0ce7-ebca-4fa7-95ed-4840d7000000"
# InstantiateVnfRequest example
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

_scale_req_example = {
    'type': 'SCALE_OUT',
    'aspectId': 'VDU1_scale',
    'numberOfSteps': 1
}

_change_ext_conn_req_example = {
    "extVirtualLinks": [
        {
            "id": "id_ext_vl_3",
            "resourceId": "res_id_ext_vl_3",
            "extCps": [
                {
                    "cpdId": "VDU2_CP1",
                    "cpConfig": {
                        "VDU2_CP1_1": {
                            "cpProtocolData": [
                                {
                                    "layerProtocol": "IP_OVER_ETHERNET",
                                    "ipOverEthernet": {
                                        "ipAddresses": [
                                            {
                                                "type": "IPV4",
                                                "fixedAddresses": [
                                                    "20.10.0.102"
                                                ]
                                            }
                                        ]
                                    }
                                }
                            ]
                        }
                    }
                }
            ]
        },
        {
            "id": "id_ext_vl_4",
            "resourceId": "res_id_id_ext_vl_4",
            "extCps": [
                {
                    "cpdId": "VDU1_CP2",
                    "cpConfig": {
                        "VDU1_CP2_1": {
                            "cpProtocolData": [
                                {
                                    "layerProtocol": "IP_OVER_ETHERNET",
                                    "ipOverEthernet": {
                                        "ipAddresses": [
                                            {
                                                "type": "IPV4",
                                                "numDynamicAddresses": 1,
                                                "subnetId": "res_id_subnet_4"
                                            }
                                        ]
                                    }
                                }
                            ]
                        }
                    }
                },
                {
                    "cpdId": "VDU2_CP2",
                    "cpConfig": {
                        "VDU2_CP2_1": {
                            "linkPortId": "link_port_id_VDU2_CP2_modified"
                        }
                    }
                }
            ],
            "extLinkPorts": [
                {
                    "id": "link_port_id_VDU2_CP2_modified",
                    "resourceHandle": {
                        "resourceId": "res_id_VDU2_CP2_modified"
                    }
                }
            ]
        }
    ]
}

_inst_info_example = {
    "flavourId": "simple",
    "vnfState": "STARTED",
    'scaleStatus': [],
    "extCpInfo": [
        {
            "id": "90561570-264c-4472-b84f-1fff98513475",
            "cpdId": "VDU2_CP1",
            "cpConfigId": "VDU2_CP1_1",
            "extLinkPortId": "ac27c99b-73c8-4e91-b730-90deade72af4",
            "associatedVnfcCpId": "be955786-a0c7-4b61-8cd8-9bb8bcb1c6e3"
        },
        {
            "id": "f9f4b4b2-50e2-4c73-b89b-e0665e65ffbe",
            "cpdId": "VDU2_CP2",
            "cpConfigId": "VDU2_CP2_1",
            "extLinkPortId": "12567a13-9fbd-4803-ad9f-d94ced266cd8",
            "associatedVnfcCpId": "c54fa2fc-185a-49a7-bb89-f30f7c3be6a4"
        },
        {
            "id": "05474d0b-a1f7-4be5-b57e-ef6873e1f3b6",
            "cpdId": "VDU1_CP2",
            "cpConfigId": "VDU1_CP2_1",
            "extLinkPortId": "aa6646da-2e59-4de9-9b72-c62e7c4d9142",
            "associatedVnfcCpId": "fdbb289f-87c8-40d0-bf06-da07b41ba124"
        },
        {
            "id": "42ede9a6-c2b8-4c0d-a337-26342ffb236c",
            "cpdId": "VDU1_CP1",
            "cpConfigId": "VDU1_CP1_1",
            "extLinkPortId": "efd0eb4e-4e55-4ac8-8b9b-403ec79faf2d",
            "associatedVnfcCpId": "235f920c-8b49-4894-9c36-73f5a3b9f74d"
        },
        {
            "id": "4f0ab1ad-b7de-482f-a69b-1093c71d2ceb",
            "cpdId": "VDU1_CP2",
            "cpConfigId": "VDU1_CP2_1",
            "extLinkPortId": "a6c4c043-e082-4873-a871-02467af66224",
            "associatedVnfcCpId": "e23d970d-9ea9-4c26-9d67-8f244383ea3c"
        },
        {
            "id": "7a7fa30f-a303-4856-bc8b-b836cb682892",
            "cpdId": "VDU1_CP1",
            "cpConfigId": "VDU1_CP1_1",
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
                        "resourceId": "res_id_VDU2_CP1",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "90561570-264c-4472-b84f-1fff98513475"
                },
                {
                    "id": "efd0eb4e-4e55-4ac8-8b9b-403ec79faf2d",
                    "resourceHandle": {
                        "resourceId": "res_id_VDU1_1_CP1",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "42ede9a6-c2b8-4c0d-a337-26342ffb236c"
                },
                {
                    "id": "f58df4d9-08ff-41b7-ab73-95ebfb8103c4",
                    "resourceHandle": {
                        "resourceId": "res_id_VDU1_2_CP1",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "7a7fa30f-a303-4856-bc8b-b836cb682892"
                }
            ],
            "currentVnfExtCpData": [
                {
                    "cpdId": "VDU2_CP1",
                    "cpConfig": {
                        "VDU2_CP2_1": {
                            "cpProtocolData": [
                                {
                                    "layerProtocol": "IP_OVER_ETHERNET",
                                    "ipOverEthernet": {
                                        "ipAddresses": [
                                            {
                                                "type": "IPV4",
                                                "fixedAddresses": [
                                                    '10.10.0.2'
                                                ],
                                                "subnetId": 'test'
                                            }
                                        ]
                                    }
                                }
                            ]
                        }
                    }
                }
            ]
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
                        "resourceId": "res_id_VDU2_CP2",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "f9f4b4b2-50e2-4c73-b89b-e0665e65ffbe"
                },
                {
                    "id": "aa6646da-2e59-4de9-9b72-c62e7c4d9142",
                    "resourceHandle": {
                        "resourceId": "res_id_VDU1_1_CP2",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "05474d0b-a1f7-4be5-b57e-ef6873e1f3b6"
                },
                {
                    "id": "a6c4c043-e082-4873-a871-02467af66224",
                    "resourceHandle": {
                        "resourceId": "res_id_VDU1_2_CP2",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "4f0ab1ad-b7de-482f-a69b-1093c71d2ceb"
                }
            ],
            "currentVnfExtCpData": [
                {
                    "cpdId": "VDU1_CP2",
                    "cpConfig": {
                        "VDU1_CP2_1": {
                            "cpProtocolData": [
                                {
                                    "layerProtocol": "IP_OVER_ETHERNET",
                                    "ipOverEthernet": {
                                        "ipAddresses": [
                                            {
                                                "type": "IPV4",
                                                "fixedAddresses": [
                                                    '10.10.0.3'
                                                ],
                                                "subnetId": 'test'
                                            }
                                        ]
                                    }
                                }
                            ]
                        }
                    }
                },
                {
                    "cpdId": "VDU2_CP2",
                    "cpConfig": {
                        "VDU2_CP2_1": {
                            "cpProtocolData": [
                                {
                                    "layerProtocol": "IP_OVER_ETHERNET",
                                    "ipOverEthernet": {
                                        "ipAddresses": [
                                            {
                                                "type": "IPV4",
                                                "fixedAddresses": [
                                                    '10.10.0.4'
                                                ],
                                                "subnetId": 'test'
                                            }
                                        ]
                                    }
                                }
                            ]
                        }
                    }
                },
            ]
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
                        "resourceId": "res_id_VDU2_CP3",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "5b0b336b-c207-4fa8-8b41-a5ad87d85cd0",
                    "cpInstanceType": "VNFC_CP"
                },
                {
                    "id": "4064ec55-b862-4527-a911-8752d3aa765a",
                    "resourceHandle": {
                        "resourceId": "res_id_VDU1_1_CP3",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "b0732fb7-a42a-4077-aebc-d22b67b64f13",
                    "cpInstanceType": "VNFC_CP"
                },
                {
                    "id": "f3c9e62d-0f31-4a36-bd99-eecd8def0871",
                    "resourceHandle": {
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
                },
                {
                    "id": "315a938a-b194-0c20-6398-ba92cce39c18",
                    "cpdId": "VDU2_CP6",
                    "vnfLinkPortId": "6dafdda1-db6c-492e-6dc2-4e5d323d6f98"
                }
            ]
        },
        {
            "id": "vnfc_res_info_id_VDU1_1",
            "vduId": "VDU1",
            "computeResource": {
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
        },
        {
            "id": "vnfc_res_no_cp_info",
            "vduId": "VDU1",
            "computeResource": {
                "resourceId": "res_id_VDU1_3",
                "vimLevelResourceType": "OS::Nova::Server"
            }
        }
    ],
    "vnfVirtualLinkResourceInfo": [
        {
            "id": "18bd0111-d5e1-4aa3-b2d8-5b89833c6351",
            "vnfVirtualLinkDescId": "internalVL3",
            "networkResource": {
                "resourceId": "res_id_internalVL3",
                "vimLevelResourceType": "OS::Neutron::Net"
            },
            "vnfLinkPorts": [
                {
                    "id": "4dd7cadd-b9a1-484f-b2f2-1ff50ef0d90f",
                    "resourceHandle": {
                        "resourceId": "res_id_VDU2_CP5",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "39a7d895-3b19-4330-b6ec-ae3557ea9c01",
                    "cpInstanceType": "VNFC_CP"
                },
                {
                    "id": "ace663cd-431b-402a-b2ae-d0824c996edb",
                    "resourceHandle": {
                        "resourceId": "res_id_VDU1_1_CP5",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "33194d65-ecd6-48d9-8ef7-c15ce9fef46c",
                    "cpInstanceType": "VNFC_CP"
                },
                {
                    "id": "e0f98917-70ff-4f79-8747-9d7fc22827a4",
                    "resourceHandle": {
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
                "resourceId": "res_id_internalVL2",
                "vimLevelResourceType": "OS::Neutron::Net"
            },
            "vnfLinkPorts": [
                {
                    "id": "8e01813f-35fc-4a35-8f64-0da08a45ea21",
                    "resourceHandle": {
                        "resourceId": "res_id_VDU2_CP4",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "2cb2b3a8-a7a0-41da-b3b8-4b82f576b090",
                    "cpInstanceType": "VNFC_CP"
                },
                {
                    "id": "1666a0f7-6a34-474e-87a2-07fb0c30ecdb",
                    "resourceHandle": {
                        "resourceId": "res_id_VDU1_1_CP4",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "a49f8fb8-6fd9-4e9f-a6dd-0d268e51c83c",
                    "cpInstanceType": "VNFC_CP"
                },
                {
                    "id": "bce3159b-caca-45b7-8bb7-88015e951e56",
                    "resourceHandle": {
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
                "resourceId": "res_id_VirtualStorage_1",
                "vimLevelResourceType": "OS::Cinder::Volume"
            }
        },
        {
            "id": "739f7012-7973-485b-b34f-b006bc336150",
            "virtualStorageDescId": "VirtualStorage",
            "storageResource": {
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

_vnf_instance_example = {
    "id": uuidutils.generate_uuid(),
    "vnfdId": SAMPLE_VNFD_ID,
    "vnfProvider": "provider",
    "vnfProductName": "product name",
    "vnfSoftwareVersion": "software version",
    "vnfdVersion": "vnfd version",
    "instantiationState": "NOT_INSTANTIATED",
    "vimConnectionInfo": _inst_req_example['vimConnectionInfo']
}


class TestUserdataDefault(base.BaseTestCase):

    def setUp(self):
        super(TestUserdataDefault, self).setUp()
        objects.register_all()
        self.context = context.get_admin_context()
        self.context.api_version = api_version.APIVersion('2.0.0')
        self.grant = {}
        sample_dir = utils.test_sample("unit/sol_refactored/samples")
        self.tmp_csar_dir = os.path.join(sample_dir, "sample1")
        self.userdata_default = userdata_default.DefaultUserData()

    def test_instantiate(self):
        req = _inst_req_example
        req['additionalParams'] = {"nfv": "req"}
        inst = _vnf_instance_example
        grant_req = {
            "operation": fields.LcmOperationType.INSTANTIATE
        }
        self.grant['additionalParams'] = {"nfv": "grant"}
        result = self.userdata_default.instantiate(
            req, inst, grant_req, self.grant, self.tmp_csar_dir)
        self.assertIsNotNone(result['template'])
        self.assertIsNotNone(result['parameters'])
        self.assertNotIn('req', result['parameters']['nfv'])
        self.assertIn('grant', result['parameters']['nfv'])
        self.assertIsNotNone(result['files'])

    def test_scale(self):
        req = _scale_req_example
        inst = _vnf_instance_example
        inst['instantiationState'] = 'INSTANTIATED'
        inst['instantiatedVnfInfo'] = _inst_info_example
        grant_req = {
            "operation": fields.LcmOperationType.SCALE
        }
        result = self.userdata_default.scale(
            req, inst, grant_req, self.grant, self.tmp_csar_dir)
        self.assertIn('VDU1', result['parameters']['nfv']['VDU'])

    def test_scale_rollback(self):
        req = _scale_req_example
        inst = _vnf_instance_example
        inst['instantiationState'] = 'INSTANTIATED'
        inst['instantiatedVnfInfo'] = _inst_info_example
        grant_req = {
            "operation": fields.LcmOperationType.SCALE
        }
        result = self.userdata_default.scale_rollback(
            req, inst, grant_req, self.grant, self.tmp_csar_dir)
        self.assertIn('VDU1', result['parameters']['nfv']['VDU'])

    def test_change_ext_conn(self):
        req = _change_ext_conn_req_example
        inst = _vnf_instance_example
        inst['instantiationState'] = 'INSTANTIATED'
        inst['instantiatedVnfInfo'] = _inst_info_example
        grant_req = {
            "operation": fields.LcmOperationType.CHANGE_EXT_CONN
        }
        result = self.userdata_default.change_ext_conn(
            req, inst, grant_req, self.grant, self.tmp_csar_dir)
        self.assertIn('VDU1_CP2', result['parameters']['nfv']['CP'])
        self.assertIn('VDU2_CP1', result['parameters']['nfv']['CP'])
        self.assertIn('VDU2_CP2', result['parameters']['nfv']['CP'])

    def test_change_ext_conn_rollback(self):
        req = _change_ext_conn_req_example
        inst = _vnf_instance_example
        inst['instantiationState'] = 'INSTANTIATED'
        inst['instantiatedVnfInfo'] = _inst_info_example
        grant_req = {
            "operation": fields.LcmOperationType.CHANGE_EXT_CONN
        }
        result = self.userdata_default.change_ext_conn_rollback(
            req, inst, grant_req, self.grant, self.tmp_csar_dir)
        self.assertIn('VDU1_CP2', result['parameters']['nfv']['CP'])
        self.assertIn('VDU2_CP1', result['parameters']['nfv']['CP'])
        self.assertIn('VDU2_CP2', result['parameters']['nfv']['CP'])

    def test_heal(self):
        result = self.userdata_default.heal(None, None, None, None, None)
        self.assertEqual({}, result['parameters']['nfv'])
