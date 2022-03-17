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

from tacker import context
from tacker.sol_refactored.common import lcm_op_occ_utils as lcmocc_utils
from tacker.sol_refactored import objects
from tacker.sol_refactored.objects.v2 import fields
from tacker.tests import base


# instantiatedVnfInfo examples
# NOTE:
# - some identifiers are modified to make check easy.
# - some attributes which are not related to test update_lcmocc are omitted.
_inst_info_example_1 = {
    # "flavourId", "vnfState", "scaleStatus", "maxScaleLevels" are omitted
    # "extCpInfo": omitted
    "extVirtualLinkInfo": [
        {
            "id": "bbf0932a-6142-4ea8-93cd-8059dba594a1",
            "resourceHandle": {
                "resourceId": "3529d333-dbcc-4d93-9b64-210647712569"
            },
            "extLinkPorts": [
                {
                    "id": "res_id_VDU2_CP1",
                    "resourceHandle": {
                        "vimConnectionId": "vim_connection_id",
                        "resourceId": "res_id_VDU2_CP1",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "cp-res_id_VDU2_CP1"
                },
                {
                    "id": "res_id_VDU1_CP1_1",
                    "resourceHandle": {
                        "vimConnectionId": "vim_connection_id",
                        "resourceId": "res_id_VDU1_CP1_1",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "cp-res_id_VDU1_CP1_1"
                }
            ],
            # "currentVnfExtCpData": omitted
        },
        {
            "id": "790949df-c7b3-4926-a559-3895412f1dfe",
            "resourceHandle": {
                "resourceId": "367e5b3b-34dc-47f2-85b8-c39e3272893a"
            },
            "extLinkPorts": [
                {
                    "id": "res_id_VDU2_CP2",
                    "resourceHandle": {
                        "vimConnectionId": "vim_connection_id",
                        "resourceId": "res_id_VDU2_CP2",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "cp-res_id_VDU2_CP2"
                },
                {
                    "id": "res_id_VDU1_CP2_1",
                    "resourceHandle": {
                        "vimConnectionId": "vim_connection_id",
                        "resourceId": "res_id_VDU1_CP2_1",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "cp-res_id_VDU1_CP2_1"
                }
            ],
            # "currentVnfExtCpData": omitted
        },
        # following two data are for test_update_lcmocc_change_ext_conn
        {
            "id": "cba2e572-2cc5-4d11-af60-728615883206",
            "resourceHandle": {
                "resourceId": "4529d333-dbcc-4d93-9b64-210647712569"
            },
            "extLinkPorts": [],
            "currentVnfExtCpData": [
                {
                    "cpdId": "VDU1_CP1",
                    "cpConfig": {
                        "VDU1_CP1_1": {
                            "cpProtocolData": [
                                {
                                    "layerProtocol": "IP_OVER_ETHERNET",
                                    "ipOverEthernet": {
                                        "ipAddresses": [
                                            {
                                                "type": "IPV4",
                                                "numDynamicAddresses": 1
                                            }
                                        ]
                                    }
                                }
                            ]
                        }
                    }
                },
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
                                                    "10.10.0.102"
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
            "id": "fc131806-8a4f-43a3-82c0-a38e87fe87bd",
            "resourceHandle": {
                "resourceId": "5529d333-dbcc-4d93-9b64-210647712569"
            },
            "extLinkPorts": [],
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
                                                "numDynamicAddresses": 1,
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
                                                    "10.10.1.102"
                                                ],
                                            }
                                        ]
                                    }
                                }
                            ]
                        }
                    }
                }
            ]
        }
    ],
    "extManagedVirtualLinkInfo": [
        {
            "id": "res_id_internalVL1",
            "vnfVirtualLinkDescId": "internalVL1",
            "networkResource": {
                "resourceId": "res_id_internalVL1"
            },
            "vnfLinkPorts": [
                {
                    "id": "res_id_VDU2_CP3",
                    "resourceHandle": {
                        "vimConnectionId": "vim_connection_id",
                        "resourceId": "res_id_VDU2_CP3",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "VDU2_CP3-res_id_VDU2",
                    "cpInstanceType": "VNFC_CP"
                },
                {
                    "id": "res_id_VDU1_CP3_1",
                    "resourceHandle": {
                        "vimConnectionId": "vim_connection_id",
                        "resourceId": "res_id_VDU1_CP3_1",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "VDU1_CP3-res_id_VDU1_1",
                    "cpInstanceType": "VNFC_CP"
                }
            ]
        }
    ],
    "vnfcResourceInfo": [
        {
            "id": "res_id_VDU1_1",
            "vduId": "VDU1",
            "computeResource": {
                "vimConnectionId": "vim_connection_id",
                "resourceId": "res_id_VDU1_1",
                "vimLevelResourceType": "OS::Nova::Server"
            },
            "storageResourceIds": [
                "res_id_VirtualStorage_1"
            ],
            "vnfcCpInfo": [
                {
                    "id": "VDU1_CP1-res_id_VDU1_1",
                    "cpdId": "VDU1_CP1",
                    "vnfExtCpId": "cp-res_id_VDU1_CP1_1"
                },
                {
                    "id": "VDU1_CP2-res_id_VDU1_1",
                    "cpdId": "VDU1_CP2",
                    "vnfExtCpId": "cp-res_id_VDU1_CP2_1"
                },
                {
                    "id": "VDU1_CP3-res_id_VDU1_1",
                    "cpdId": "VDU1_CP3",
                    "vnfLinkPortId": "res_id_VDU1_CP3_1"
                },
                {
                    "id": "VDU1_CP4-res_id_VDU1_1",
                    "cpdId": "VDU1_CP4",
                    "vnfLinkPortId": "res_id_VDU1_CP4_1"
                },
                {
                    "id": "VDU1_CP5-res_id_VDU1_1",
                    "cpdId": "VDU1_CP5",
                    "vnfLinkPortId": "res_id_VDU1_CP5_1"
                }
            ],
            # "metadata": omitted
        },
        {
            "id": "res_id_VDU2",
            "vduId": "VDU2",
            "computeResource": {
                "vimConnectionId": "vim_connection_id",
                "resourceId": "res_id_VDU2",
                "vimLevelResourceType": "OS::Nova::Server"
            },
            "vnfcCpInfo": [
                {
                    "id": "VDU2_CP1-res_id_VDU2",
                    "cpdId": "VDU2_CP1",
                    "vnfExtCpId": "cp-res_id_VDU2_CP1"
                },
                {
                    "id": "VDU2_CP2-res_id_VDU2",
                    "cpdId": "VDU2_CP2",
                    "vnfExtCpId": "cp-res_id_VDU2_CP2"
                },
                {
                    "id": "VDU2_CP3-res_id_VDU2",
                    "cpdId": "VDU2_CP3",
                    "vnfLinkPortId": "res_id_VDU2_CP3"
                },
                {
                    "id": "VDU2_CP4-res_id_VDU2",
                    "cpdId": "VDU2_CP4",
                    "vnfLinkPortId": "res_id_VDU2_CP4"
                },
                {
                    "id": "VDU2_CP5-res_id_VDU2",
                    "cpdId": "VDU2_CP5",
                    "vnfLinkPortId": "res_id_VDU2_CP5"
                }
            ],
            # "metadata": omitted
        }
    ],
    "vnfVirtualLinkResourceInfo": [
        {
            "id": "res_id_internalVL3",
            "vnfVirtualLinkDescId": "internalVL3",
            "networkResource": {
                "vimConnectionId": "vim_connection_id",
                "resourceId": "res_id_internalVL3",
                "vimLevelResourceType": "OS::Neutron::Net"
            },
            "vnfLinkPorts": [
                {
                    "id": "res_id_VDU2_CP5",
                    "resourceHandle": {
                        "vimConnectionId": "vim_connection_id",
                        "resourceId": "res_id_VDU2_CP5",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "VDU2_CP5-res_id_VDU2",
                    "cpInstanceType": "VNFC_CP"
                },
                {
                    "id": "res_id_VDU1_CP5_1",
                    "resourceHandle": {
                        "vimConnectionId": "vim_connection_id",
                        "resourceId": "res_id_VDU1_CP5_1",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "VDU1_CP5-res_id_VDU1_1",
                    "cpInstanceType": "VNFC_CP"
                }
            ]
        },
        {
            "id": "res_id_internalVL2",
            "vnfVirtualLinkDescId": "internalVL2",
            "networkResource": {
                "vimConnectionId": "vim_connection_id",
                "resourceId": "res_id_internalVL2",
                "vimLevelResourceType": "OS::Neutron::Net"
            },
            "vnfLinkPorts": [
                {
                    "id": "res_id_VDU2_CP4",
                    "resourceHandle": {
                        "vimConnectionId": "vim_connection_id",
                        "resourceId": "res_id_VDU2_CP4",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "VDU2_CP4-res_id_VDU2",
                    "cpInstanceType": "VNFC_CP"
                },
                {
                    "id": "res_id_VDU1_CP4_1",
                    "resourceHandle": {
                        "vimConnectionId": "vim_connection_id",
                        "resourceId": "res_id_VDU1_CP4_1",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "VDU1_CP4-res_id_VDU1_1",
                    "cpInstanceType": "VNFC_CP"
                }
            ]
        }
    ],
    "virtualStorageResourceInfo": [
        {
            "id": "res_id_VirtualStorage_1",
            "virtualStorageDescId": "VirtualStorage",
            "storageResource": {
                "vimConnectionId": "vim_connection_id",
                "resourceId": "res_id_VirtualStorage_1",
                "vimLevelResourceType": "OS::Cinder::Volume"
            }
        }
    ],
    # "vnfcInfo": omitted
}

# example_2 is added a VDU1 to example_1.
_inst_info_example_2 = {
    # "flavourId", "vnfState", "scaleStatus", "maxScaleLevels" are omitted
    # "extCpInfo": omitted
    "extVirtualLinkInfo": [
        {
            "id": "bbf0932a-6142-4ea8-93cd-8059dba594a1",
            "resourceHandle": {
                "resourceId": "3529d333-dbcc-4d93-9b64-210647712569"
            },
            "extLinkPorts": [
                {
                    "id": "res_id_VDU2_CP1",
                    "resourceHandle": {
                        "vimConnectionId": "vim_connection_id",
                        "resourceId": "res_id_VDU2_CP1",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "cp-res_id_VDU2_CP1"
                },
                {
                    "id": "res_id_VDU1_CP1_1",
                    "resourceHandle": {
                        "vimConnectionId": "vim_connection_id",
                        "resourceId": "res_id_VDU1_CP1_1",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "cp-res_id_VDU1_CP1_1"
                },
                {
                    "id": "res_id_VDU1_CP1_2",
                    "resourceHandle": {
                        "vimConnectionId": "vim_connection_id",
                        "resourceId": "res_id_VDU1_CP1_2",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "cp-res_id_VDU1_CP1_2"
                }
            ],
            # "currentVnfExtCpData": omitted
        },
        {
            "id": "790949df-c7b3-4926-a559-3895412f1dfe",
            "resourceHandle": {
                "resourceId": "367e5b3b-34dc-47f2-85b8-c39e3272893a"
            },
            "extLinkPorts": [
                {
                    "id": "res_id_VDU2_CP2",
                    "resourceHandle": {
                        "vimConnectionId": "vim_connection_id",
                        "resourceId": "res_id_VDU2_CP2",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "cp-res_id_VDU2_CP2"
                },
                {
                    "id": "res_id_VDU1_CP2_1",
                    "resourceHandle": {
                        "vimConnectionId": "vim_connection_id",
                        "resourceId": "res_id_VDU1_CP2_1",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "cp-res_id_VDU1_CP2_1"
                },
                {
                    "id": "res_id_VDU1_CP2_2",
                    "resourceHandle": {
                        "vimConnectionId": "vim_connection_id",
                        "resourceId": "res_id_VDU1_CP2_2",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "cp-res_id_VDU1_CP2_2"
                }
            ],
            # "currentVnfExtCpData": omitted
        }
    ],
    "extManagedVirtualLinkInfo": [
        {
            "id": "res_id_internalVL1",
            "vnfVirtualLinkDescId": "internalVL1",
            "networkResource": {
                "resourceId": "res_id_internalVL1"
            },
            "vnfLinkPorts": [
                {
                    "id": "res_id_VDU2_CP3",
                    "resourceHandle": {
                        "vimConnectionId": "vim_connection_id",
                        "resourceId": "res_id_VDU2_CP3",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "VDU2_CP3-res_id_VDU2",
                    "cpInstanceType": "VNFC_CP"
                },
                {
                    "id": "res_id_VDU1_CP3_1",
                    "resourceHandle": {
                        "vimConnectionId": "vim_connection_id",
                        "resourceId": "res_id_VDU1_CP3_1",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "VDU1_CP3-res_id_VDU1_1",
                    "cpInstanceType": "VNFC_CP"
                },
                {
                    "id": "res_id_VDU1_CP3_2",
                    "resourceHandle": {
                        "vimConnectionId": "vim_connection_id",
                        "resourceId": "res_id_VDU1_CP3_2",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "VDU1_CP3-res_id_VDU1_2",
                    "cpInstanceType": "VNFC_CP"
                }
            ]
        }
    ],
    "vnfcResourceInfo": [
        {
            "id": "res_id_VDU1_2",
            "vduId": "VDU1",
            "computeResource": {
                "vimConnectionId": "vim_connection_id",
                "resourceId": "res_id_VDU1_2",
                "vimLevelResourceType": "OS::Nova::Server"
            },
            "storageResourceIds": [
                "res_id_VirtualStorage_2"
            ],
            "vnfcCpInfo": [
                {
                    "id": "VDU1_CP1-res_id_VDU1_2",
                    "cpdId": "VDU1_CP1",
                    "vnfExtCpId": "cp-res_id_VDU1_CP1_2"
                },
                {
                    "id": "VDU1_CP2-res_id_VDU1_2",
                    "cpdId": "VDU1_CP2",
                    "vnfExtCpId": "cp-res_id_VDU1_CP2_2"
                },
                {
                    "id": "VDU1_CP3-res_id_VDU1_2",
                    "cpdId": "VDU1_CP3",
                    "vnfLinkPortId": "res_id_VDU1_CP3_2"
                },
                {
                    "id": "VDU1_CP4-res_id_VDU1_2",
                    "cpdId": "VDU1_CP4",
                    "vnfLinkPortId": "res_id_VDU1_CP4_2"
                },
                {
                    "id": "VDU1_CP5-res_id_VDU1_2",
                    "cpdId": "VDU1_CP5",
                    "vnfLinkPortId": "res_id_VDU1_CP5_2"
                }
            ],
            # "metadata": omitted
        },
        {
            "id": "res_id_VDU1_1",
            "vduId": "VDU1",
            "computeResource": {
                "vimConnectionId": "vim_connection_id",
                "resourceId": "res_id_VDU1_1",
                "vimLevelResourceType": "OS::Nova::Server"
            },
            "storageResourceIds": [
                "res_id_VirtualStorage_1"
            ],
            "vnfcCpInfo": [
                {
                    "id": "VDU1_CP1-res_id_VDU1_1",
                    "cpdId": "VDU1_CP1",
                    "vnfExtCpId": "cp-res_id_VDU1_CP1_1"
                },
                {
                    "id": "VDU1_CP2-res_id_VDU1_1",
                    "cpdId": "VDU1_CP2",
                    "vnfExtCpId": "cp-res_id_VDU1_CP2_1"
                },
                {
                    "id": "VDU1_CP3-res_id_VDU1_1",
                    "cpdId": "VDU1_CP3",
                    "vnfLinkPortId": "res_id_VDU1_CP3_1"
                },
                {
                    "id": "VDU1_CP4-res_id_VDU1_1",
                    "cpdId": "VDU1_CP4",
                    "vnfLinkPortId": "res_id_VDU1_CP4_1"
                },
                {
                    "id": "VDU1_CP5-res_id_VDU1_1",
                    "cpdId": "VDU1_CP5",
                    "vnfLinkPortId": "res_id_VDU1_CP5_1"
                }
            ],
            # "metadata": omitted
        },
        {
            "id": "res_id_VDU2",
            "vduId": "VDU2",
            "computeResource": {
                "vimConnectionId": "vim_connection_id",
                "resourceId": "res_id_VDU2",
                "vimLevelResourceType": "OS::Nova::Server"
            },
            "vnfcCpInfo": [
                {
                    "id": "VDU2_CP1-res_id_VDU2",
                    "cpdId": "VDU2_CP1",
                    "vnfExtCpId": "cp-res_id_VDU2_CP1"
                },
                {
                    "id": "VDU2_CP2-res_id_VDU2",
                    "cpdId": "VDU2_CP2",
                    "vnfExtCpId": "cp-res_id_VDU2_CP2"
                },
                {
                    "id": "VDU2_CP3-res_id_VDU2",
                    "cpdId": "VDU2_CP3",
                    "vnfLinkPortId": "res_id_VDU2_CP3"
                },
                {
                    "id": "VDU2_CP4-res_id_VDU2",
                    "cpdId": "VDU2_CP4",
                    "vnfLinkPortId": "res_id_VDU2_CP4"
                },
                {
                    "id": "VDU2_CP5-res_id_VDU2",
                    "cpdId": "VDU2_CP5",
                    "vnfLinkPortId": "res_id_VDU2_CP5"
                }
            ],
            # "metadata": omitted
        }
    ],
    "vnfVirtualLinkResourceInfo": [
        {
            "id": "res_id_internalVL3",
            "vnfVirtualLinkDescId": "internalVL3",
            "networkResource": {
                "vimConnectionId": "vim_connection_id",
                "resourceId": "res_id_internalVL3",
                "vimLevelResourceType": "OS::Neutron::Net"
            },
            "vnfLinkPorts": [
                {
                    "id": "res_id_VDU2_CP5",
                    "resourceHandle": {
                        "vimConnectionId": "vim_connection_id",
                        "resourceId": "res_id_VDU2_CP5",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "VDU2_CP5-res_id_VDU2",
                    "cpInstanceType": "VNFC_CP"
                },
                {
                    "id": "res_id_VDU1_CP5_1",
                    "resourceHandle": {
                        "vimConnectionId": "vim_connection_id",
                        "resourceId": "res_id_VDU1_CP5_1",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "VDU1_CP5-res_id_VDU1_1",
                    "cpInstanceType": "VNFC_CP"
                },
                {
                    "id": "res_id_VDU1_CP5_2",
                    "resourceHandle": {
                        "vimConnectionId": "vim_connection_id",
                        "resourceId": "res_id_VDU1_CP5_2",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "VDU1_CP5-res_id_VDU1_2",
                    "cpInstanceType": "VNFC_CP"
                }
            ]
        },
        {
            "id": "res_id_internalVL2",
            "vnfVirtualLinkDescId": "internalVL2",
            "networkResource": {
                "vimConnectionId": "vim_connection_id",
                "resourceId": "res_id_internalVL2",
                "vimLevelResourceType": "OS::Neutron::Net"
            },
            "vnfLinkPorts": [
                {
                    "id": "res_id_VDU2_CP4",
                    "resourceHandle": {
                        "vimConnectionId": "vim_connection_id",
                        "resourceId": "res_id_VDU2_CP4",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "VDU2_CP4-res_id_VDU2",
                    "cpInstanceType": "VNFC_CP"
                },
                {
                    "id": "res_id_VDU1_CP4_1",
                    "resourceHandle": {
                        "vimConnectionId": "vim_connection_id",
                        "resourceId": "res_id_VDU1_CP4_1",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "VDU1_CP4-res_id_VDU1_1",
                    "cpInstanceType": "VNFC_CP"
                },
                {
                    "id": "res_id_VDU1_CP4_2",
                    "resourceHandle": {
                        "vimConnectionId": "vim_connection_id",
                        "resourceId": "res_id_VDU1_CP4_2",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "VDU1_CP4-res_id_VDU1_2",
                    "cpInstanceType": "VNFC_CP"
                }
            ]
        }
    ],
    "virtualStorageResourceInfo": [
        {
            "id": "res_id_VirtualStorage_1",
            "virtualStorageDescId": "VirtualStorage",
            "storageResource": {
                "vimConnectionId": "vim_connection_id",
                "resourceId": "res_id_VirtualStorage_1",
                "vimLevelResourceType": "OS::Cinder::Volume"
            }
        },
        {
            "id": "res_id_VirtualStorage_2",
            "virtualStorageDescId": "VirtualStorage",
            "storageResource": {
                "vimConnectionId": "vim_connection_id",
                "resourceId": "res_id_VirtualStorage_2",
                "vimLevelResourceType": "OS::Cinder::Volume"
            }
        }
    ],
    # "vnfcInfo": omitted
}

# example_3 is changed external virtual link ports from example_1.
_inst_info_example_3 = {
    # "flavourId", "vnfState", "scaleStatus", "maxScaleLevels" are omitted
    # "extCpInfo": omitted
    "extVirtualLinkInfo": [
        {
            "id": "bbf0932a-6142-4ea8-93cd-8059dba594a1",
            "resourceHandle": {
                "resourceId": "3529d333-dbcc-4d93-9b64-210647712569"
            },
            "extLinkPorts": [
                {
                    "id": "res_id_VDU1_CP1_1",
                    "resourceHandle": {
                        "vimConnectionId": "vim_connection_id",
                        "resourceId": "res_id_VDU1_CP1_1",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "cp-res_id_VDU1_CP1_1"
                }
            ],
            # "currentVnfExtCpData": omitted
        },
        {
            "id": "2ff742fc-da6d-423a-8fba-6aa6af8da6f2",
            "resourceHandle": {
                "resourceId": "9113aff7-9ba2-43f4-8b1e-fff80ae001c5"
            },
            "extLinkPorts": [
                {
                    "id": "res_id_VDU2_CP1_modified",
                    "resourceHandle": {
                        "vimConnectionId": "vim_connection_id",
                        "resourceId": "res_id_VDU2_CP1_modified",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "cp-res_id_VDU2_CP1"
                },
            ],
            # "currentVnfExtCpData": omitted
        },
        {
            "id": "790949df-c7b3-4926-a559-3895412f1dfe",
            "resourceHandle": {
                "resourceId": "367e5b3b-34dc-47f2-85b8-c39e3272893a"
            },
            "extLinkPorts": [
                {
                    "id": "res_id_VDU2_CP2",
                    "resourceHandle": {
                        "vimConnectionId": "vim_connection_id",
                        "resourceId": "res_id_VDU2_CP2",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "cp-res_id_VDU2_CP2"
                },
                {
                    "id": "res_id_VDU1_CP2_1",
                    "resourceHandle": {
                        "vimConnectionId": "vim_connection_id",
                        "resourceId": "res_id_VDU1_CP2_1",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "cp-res_id_VDU1_CP2_1"
                }
            ],
            # "currentVnfExtCpData": omitted
        },
        {  # same as _inst_info_example_1
            "id": "cba2e572-2cc5-4d11-af60-728615883206",
            "resourceHandle": {
                "resourceId": "4529d333-dbcc-4d93-9b64-210647712569"
            },
            "extLinkPorts": [],
            "currentVnfExtCpData": [
                {
                    "cpdId": "VDU1_CP1",
                    "cpConfig": {
                        "VDU1_CP1_1": {
                            "cpProtocolData": [
                                {
                                    "layerProtocol": "IP_OVER_ETHERNET",
                                    "ipOverEthernet": {
                                        "ipAddresses": [
                                            {
                                                "type": "IPV4",
                                                "numDynamicAddresses": 1
                                            }
                                        ]
                                    }
                                }
                            ]
                        }
                    }
                },
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
                                                    "10.10.0.102"
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
        {  # ip address of VDU2_CP2 is changed
            "id": "fc131806-8a4f-43a3-82c0-a38e87fe87bd",
            "resourceHandle": {
                "resourceId": "5529d333-dbcc-4d93-9b64-210647712569"
            },
            "extLinkPorts": [],
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
                                                "numDynamicAddresses": 1,
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
                                                    "10.10.1.103"
                                                ],
                                            }
                                        ]
                                    }
                                }
                            ]
                        }
                    }
                }
            ]
        }
    ],
    # NOTE: vnfcCpInfo of VnfcResourceInfo is changed exactly, but it is
    # not looked at update_lcmocc.
    "vnfcResourceInfo": _inst_info_example_1["vnfcResourceInfo"],
    # other members are same as example_1
    "extManagedVirtualLinkInfo":
        _inst_info_example_1["extManagedVirtualLinkInfo"],
    "vnfVirtualLinkResourceInfo":
        _inst_info_example_1["vnfVirtualLinkResourceInfo"],
    "virtualStorageResourceInfo":
        _inst_info_example_1["virtualStorageResourceInfo"],
    # "vnfcInfo": omitted
}

# example_4 is for update_lcmocc test in case of heal. based on example_2.
# * VDU1_1: update server only. VDU1_2: update both server and volume.
# * ports of extMangagedVirtualLink are re-created.
# NOTE: combination of the above sentences can not be happened really.
# it is the data for unit test.
_inst_info_example_4 = {
    # "flavourId", "vnfState", "scaleStatus", "maxScaleLevels" are omitted
    # "extCpInfo": omitted
    "extVirtualLinkInfo": _inst_info_example_2["extVirtualLinkInfo"],
    # network resource is not changed but ports are re-receated.
    # this is for check of SOL003 all=True case.

    "extManagedVirtualLinkInfo": [
        {
            "id": "res_id_internalVL1",
            "vnfVirtualLinkDescId": "internalVL1",
            "networkResource": {
                "resourceId": "res_id_internalVL1"
            },
            "vnfLinkPorts": [
                {
                    "id": "res_id_VDU2_CP3_changed",
                    "resourceHandle": {
                        "vimConnectionId": "vim_connection_id",
                        "resourceId": "res_id_VDU2_CP3_changed",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "VDU2_CP3-res_id_VDU2",
                    "cpInstanceType": "VNFC_CP"
                },
                {
                    "id": "res_id_VDU1_CP3_1_changed",
                    "resourceHandle": {
                        "vimConnectionId": "vim_connection_id",
                        "resourceId": "res_id_VDU1_CP3_1_changed",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "VDU1_CP3-res_id_VDU1_1",
                    "cpInstanceType": "VNFC_CP"
                },
                {
                    "id": "res_id_VDU1_CP3_2_changed",
                    "resourceHandle": {
                        "vimConnectionId": "vim_connection_id",
                        "resourceId": "res_id_VDU1_CP3_2_changed",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "VDU1_CP3-res_id_VDU1_2",
                    "cpInstanceType": "VNFC_CP"
                }
            ]
        }
    ],
    "vnfcResourceInfo": [
        {
            "id": "res_id_VDU1_2_new",
            "vduId": "VDU1",
            "computeResource": {
                "vimConnectionId": "vim_connection_id",
                "resourceId": "res_id_VDU1_2_new",
                "vimLevelResourceType": "OS::Nova::Server"
            },
            "storageResourceIds": [
                "res_id_VirtualStorage_2_new"
            ],
            "vnfcCpInfo": [
                {
                    "id": "VDU1_CP1-res_id_VDU1_2_new",
                    "cpdId": "VDU1_CP1",
                    "vnfExtCpId": "cp-res_id_VDU1_CP1_2_new"
                },
                {
                    "id": "VDU1_CP2-res_id_VDU1_2_new",
                    "cpdId": "VDU1_CP2",
                    "vnfExtCpId": "cp-res_id_VDU1_CP2_2_new"
                },
                {
                    "id": "VDU1_CP3-res_id_VDU1_2_new",
                    "cpdId": "VDU1_CP3",
                    "vnfLinkPortId": "res_id_VDU1_CP3_2_new"
                },
                {
                    "id": "VDU1_CP4-res_id_VDU1_2_new",
                    "cpdId": "VDU1_CP4",
                    "vnfLinkPortId": "res_id_VDU1_CP4_2_new"
                },
                {
                    "id": "VDU1_CP5-res_id_VDU1_2_new",
                    "cpdId": "VDU1_CP5",
                    "vnfLinkPortId": "res_id_VDU1_CP5_2_new"
                }
            ],
            # "metadata": omitted
        },
        {
            "id": "res_id_VDU1_1_new",
            "vduId": "VDU1",
            "computeResource": {
                "vimConnectionId": "vim_connection_id",
                "resourceId": "res_id_VDU1_1_new",
                "vimLevelResourceType": "OS::Nova::Server"
            },
            "storageResourceIds": [
                "res_id_VirtualStorage_1"
            ],
            "vnfcCpInfo": [
                {
                    "id": "VDU1_CP1-res_id_VDU1_1_new",
                    "cpdId": "VDU1_CP1",
                    "vnfExtCpId": "cp-res_id_VDU1_CP1_1_new"
                },
                {
                    "id": "VDU1_CP2-res_id_VDU1_1_new",
                    "cpdId": "VDU1_CP2",
                    "vnfExtCpId": "cp-res_id_VDU1_CP2_1_new"
                },
                {
                    "id": "VDU1_CP3-res_id_VDU1_1_new",
                    "cpdId": "VDU1_CP3",
                    "vnfLinkPortId": "res_id_VDU1_CP3_1_new"
                },
                {
                    "id": "VDU1_CP4-res_id_VDU1_1_new",
                    "cpdId": "VDU1_CP4",
                    "vnfLinkPortId": "res_id_VDU1_CP4_1_new"
                },
                {
                    "id": "VDU1_CP5-res_id_VDU1_1_new",
                    "cpdId": "VDU1_CP5",
                    "vnfLinkPortId": "res_id_VDU1_CP5_1_new"
                }
            ],
            # "metadata": omitted
        },
        {
            "id": "res_id_VDU2",
            "vduId": "VDU2",
            "computeResource": {
                "vimConnectionId": "vim_connection_id",
                "resourceId": "res_id_VDU2",
                "vimLevelResourceType": "OS::Nova::Server"
            },
            "vnfcCpInfo": [
                {
                    "id": "VDU2_CP1-res_id_VDU2",
                    "cpdId": "VDU2_CP1",
                    "vnfExtCpId": "cp-res_id_VDU2_CP1"
                },
                {
                    "id": "VDU2_CP2-res_id_VDU2",
                    "cpdId": "VDU2_CP2",
                    "vnfExtCpId": "cp-res_id_VDU2_CP2"
                },
                {
                    "id": "VDU2_CP3-res_id_VDU2",
                    "cpdId": "VDU2_CP3",
                    "vnfLinkPortId": "res_id_VDU2_CP3"
                },
                {
                    "id": "VDU2_CP4-res_id_VDU2",
                    "cpdId": "VDU2_CP4",
                    "vnfLinkPortId": "res_id_VDU2_CP4"
                },
                {
                    "id": "VDU2_CP5-res_id_VDU2",
                    "cpdId": "VDU2_CP5",
                    "vnfLinkPortId": "res_id_VDU2_CP5"
                }
            ],
            # "metadata": omitted
        }
    ],
    "vnfVirtualLinkResourceInfo":
        _inst_info_example_2["vnfVirtualLinkResourceInfo"],
    "virtualStorageResourceInfo": [
        {
            "id": "res_id_VirtualStorage_1",
            "virtualStorageDescId": "VirtualStorage",
            "storageResource": {
                "vimConnectionId": "vim_connection_id",
                "resourceId": "res_id_VirtualStorage_1",
                "vimLevelResourceType": "OS::Cinder::Volume"
            }
        },
        {
            "id": "res_id_VirtualStorage_2_new",
            "virtualStorageDescId": "VirtualStorage",
            "storageResource": {
                "vimConnectionId": "vim_connection_id",
                "resourceId": "res_id_VirtualStorage_2_new",
                "vimLevelResourceType": "OS::Cinder::Volume"
            }
        }
    ],
    # "vnfcInfo": omitted
}

# example_5 is update VDU1 and VDU2's info from example_1.
_inst_info_example_5 = {
    # "flavourId", "vnfState", "scaleStatus", "maxScaleLevels" are omitted
    # "extCpInfo": omitted
    "extVirtualLinkInfo": [
        {
            "id": "bbf0932a-6142-4ea8-93cd-8059dba594a1",
            "resourceHandle": {
                "resourceId": "3529d333-dbcc-4d93-9b64-210647712569"
            },
            "extLinkPorts": [
                {
                    "id": "res_id_VDU2_CP1",
                    "resourceHandle": {
                        "vimConnectionId": "vim_connection_id",
                        "resourceId": "res_id_VDU2_CP1",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "cp-res_id_VDU2_CP1"
                },
                {
                    "id": "res_id_VDU1_CP1_1",
                    "resourceHandle": {
                        "vimConnectionId": "vim_connection_id",
                        "resourceId": "res_id_VDU1_CP1_1",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "cp-res_id_VDU1_CP1_1"
                }
            ],
            # "currentVnfExtCpData": omitted
        },
        {
            "id": "790949df-c7b3-4926-a559-3895412f1dfe",
            "resourceHandle": {
                "resourceId": "367e5b3b-34dc-47f2-85b8-c39e3272893a"
            },
            "extLinkPorts": [
                {
                    "id": "res_id_VDU2_CP2",
                    "resourceHandle": {
                        "vimConnectionId": "vim_connection_id",
                        "resourceId": "res_id_VDU2_CP2",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "cp-res_id_VDU2_CP2"
                },
                {
                    "id": "res_id_VDU1_CP2_1",
                    "resourceHandle": {
                        "vimConnectionId": "vim_connection_id",
                        "resourceId": "res_id_VDU1_CP2_1",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "cp-res_id_VDU1_CP2_1"
                }
            ],
            # "currentVnfExtCpData": omitted
        }
    ],
    "extManagedVirtualLinkInfo": [
        {
            "id": "res_id_internalVL1",
            "vnfVirtualLinkDescId": "internalVL1",
            "networkResource": {
                "resourceId": "res_id_internalVL1"
            },
            "vnfLinkPorts": [
                {
                    "id": "res_id_VDU2_CP3",
                    "resourceHandle": {
                        "vimConnectionId": "vim_connection_id",
                        "resourceId": "res_id_VDU2_CP3",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "VDU2_CP3-res_id_VDU2",
                    "cpInstanceType": "VNFC_CP"
                },
                {
                    "id": "res_id_VDU1_CP3_1",
                    "resourceHandle": {
                        "vimConnectionId": "vim_connection_id",
                        "resourceId": "res_id_VDU1_CP3_1",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "VDU1_CP3-res_id_VDU1_1",
                    "cpInstanceType": "VNFC_CP"
                }
            ]
        }
    ],
    "vnfcResourceInfo": [
        {
            "id": "res_id_VDU1_1_update",
            "vduId": "VDU1",
            "computeResource": {
                "vimConnectionId": "vim_connection_id",
                "resourceId": "res_id_VDU1_1_update",
                "vimLevelResourceType": "OS::Nova::Server"
            },
            "metadata": {
                "current_vnfd_id": 'new_vnfd_id'
            },
            "storageResourceIds": [
                "new_res_id_VirtualStorage_1"
            ],
            "vnfcCpInfo": [
                {
                    "id": "VDU1_CP1-res_id_VDU1_1",
                    "cpdId": "VDU1_CP1",
                    "vnfExtCpId": "cp-res_id_VDU1_CP1_1"
                },
                {
                    "id": "VDU1_CP2-res_id_VDU1_1",
                    "cpdId": "VDU1_CP2",
                    "vnfExtCpId": "cp-res_id_VDU1_CP2_1"
                },
                {
                    "id": "VDU1_CP3-res_id_VDU1_1",
                    "cpdId": "VDU1_CP3",
                    "vnfLinkPortId": "res_id_VDU1_CP3_1"
                },
                {
                    "id": "VDU1_CP4-res_id_VDU1_1",
                    "cpdId": "VDU1_CP4",
                    "vnfLinkPortId": "res_id_VDU1_CP4_1"
                },
                {
                    "id": "VDU1_CP5-res_id_VDU1_1",
                    "cpdId": "VDU1_CP5",
                    "vnfLinkPortId": "res_id_VDU1_CP5_1"
                }
            ],
        },
        {
            "id": "res_id_VDU2",
            "vduId": "VDU2",
            "computeResource": {
                "vimConnectionId": "vim_connection_id",
                "resourceId": "res_id_VDU2",
                "vimLevelResourceType": "OS::Nova::Server"
            },
            "metadata": {
                "current_vnfd_id": 'new_vnfd_id'
            },
            "vnfcCpInfo": [
                {
                    "id": "VDU2_CP1-res_id_VDU2",
                    "cpdId": "VDU2_CP1",
                    "vnfExtCpId": "cp-res_id_VDU2_CP1"
                },
                {
                    "id": "VDU2_CP2-res_id_VDU2",
                    "cpdId": "VDU2_CP2",
                    "vnfExtCpId": "cp-res_id_VDU2_CP2"
                },
                {
                    "id": "VDU2_CP3-res_id_VDU2",
                    "cpdId": "VDU2_CP3",
                    "vnfLinkPortId": "res_id_VDU2_CP3"
                },
                {
                    "id": "VDU2_CP4-res_id_VDU2",
                    "cpdId": "VDU2_CP4",
                    "vnfLinkPortId": "res_id_VDU2_CP4"
                },
                {
                    "id": "VDU2_CP5-res_id_VDU2",
                    "cpdId": "VDU2_CP5",
                    "vnfLinkPortId": "res_id_VDU2_CP5"
                }
            ],
        }
    ],
    "vnfVirtualLinkResourceInfo": [
        {
            "id": "res_id_internalVL3",
            "vnfVirtualLinkDescId": "internalVL3",
            "networkResource": {
                "vimConnectionId": "vim_connection_id",
                "resourceId": "res_id_internalVL3",
                "vimLevelResourceType": "OS::Neutron::Net"
            },
            "vnfLinkPorts": [
                {
                    "id": "res_id_VDU2_CP5",
                    "resourceHandle": {
                        "vimConnectionId": "vim_connection_id",
                        "resourceId": "res_id_VDU2_CP5",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "VDU2_CP5-res_id_VDU2",
                    "cpInstanceType": "VNFC_CP"
                },
                {
                    "id": "res_id_VDU1_CP5_1",
                    "resourceHandle": {
                        "vimConnectionId": "vim_connection_id",
                        "resourceId": "res_id_VDU1_CP5_1",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "VDU1_CP5-res_id_VDU1_1",
                    "cpInstanceType": "VNFC_CP"
                }
            ]
        },
        {
            "id": "res_id_internalVL2",
            "vnfVirtualLinkDescId": "internalVL2",
            "networkResource": {
                "vimConnectionId": "vim_connection_id",
                "resourceId": "res_id_internalVL2",
                "vimLevelResourceType": "OS::Neutron::Net"
            },
            "vnfLinkPorts": [
                {
                    "id": "res_id_VDU2_CP4",
                    "resourceHandle": {
                        "vimConnectionId": "vim_connection_id",
                        "resourceId": "res_id_VDU2_CP4",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "VDU2_CP4-res_id_VDU2",
                    "cpInstanceType": "VNFC_CP"
                },
                {
                    "id": "res_id_VDU1_CP4_1",
                    "resourceHandle": {
                        "vimConnectionId": "vim_connection_id",
                        "resourceId": "res_id_VDU1_CP4_1",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "VDU1_CP4-res_id_VDU1_1",
                    "cpInstanceType": "VNFC_CP"
                }
            ]
        }
    ],
    "virtualStorageResourceInfo": [
        {
            "id": "new_res_id_VirtualStorage_1",
            "virtualStorageDescId": "VirtualStorage",
            "storageResource": {
                "vimConnectionId": "vim_connection_id",
                "resourceId": "new_res_id_VirtualStorage_1",
                "vimLevelResourceType": "OS::Cinder::Volume"
            }
        }
    ],
}

# expected results
_expected_resource_changes_instantiate = {
    "affectedVnfcs": [
        {
            "id": "res_id_VDU1_1",
            "vduId": "VDU1",
            "changeType": "ADDED",
            "computeResource": {
                "vimConnectionId": "vim_connection_id",
                "resourceId": "res_id_VDU1_1",
                "vimLevelResourceType": "OS::Nova::Server"
            },
            "affectedVnfcCpIds": [
                "VDU1_CP1-res_id_VDU1_1",
                "VDU1_CP2-res_id_VDU1_1",
                "VDU1_CP3-res_id_VDU1_1",
                "VDU1_CP4-res_id_VDU1_1",
                "VDU1_CP5-res_id_VDU1_1"
            ],
            "addedStorageResourceIds": [
                "res_id_VirtualStorage_1"
            ]
        },
        {
            "id": "res_id_VDU2",
            "vduId": "VDU2",
            "changeType": "ADDED",
            "computeResource": {
                "vimConnectionId": "vim_connection_id",
                "resourceId": "res_id_VDU2",
                "vimLevelResourceType": "OS::Nova::Server"
            },
            "affectedVnfcCpIds": [
                "VDU2_CP1-res_id_VDU2",
                "VDU2_CP2-res_id_VDU2",
                "VDU2_CP3-res_id_VDU2",
                "VDU2_CP4-res_id_VDU2",
                "VDU2_CP5-res_id_VDU2"
            ]
        }
    ],
    "affectedVirtualLinks": [
        {
            "id": "res_id_internalVL1",
            "vnfVirtualLinkDescId": "internalVL1",
            "changeType": "LINK_PORT_ADDED",
            "networkResource": {
                "resourceId": "res_id_internalVL1"
            },
            "vnfLinkPortIds": [
                "res_id_VDU1_CP3_1",
                "res_id_VDU2_CP3"
            ]
        },
        {
            "id": "res_id_internalVL2",
            "vnfVirtualLinkDescId": "internalVL2",
            "changeType": "ADDED",
            "networkResource": {
                "vimConnectionId": "vim_connection_id",
                "resourceId": "res_id_internalVL2",
                "vimLevelResourceType": "OS::Neutron::Net"
            },
            "vnfLinkPortIds": [
                "res_id_VDU1_CP4_1",
                "res_id_VDU2_CP4"
            ]
        },
        {
            "id": "res_id_internalVL3",
            "vnfVirtualLinkDescId": "internalVL3",
            "changeType": "ADDED",
            "networkResource": {
                "vimConnectionId": "vim_connection_id",
                "resourceId": "res_id_internalVL3",
                "vimLevelResourceType": "OS::Neutron::Net"
            },
            "vnfLinkPortIds": [
                "res_id_VDU1_CP5_1",
                "res_id_VDU2_CP5"
            ]
        }
    ],
    "affectedExtLinkPorts": [
        {
            "id": "res_id_VDU1_CP1_1",
            "changeType": "ADDED",
            "extCpInstanceId": "cp-res_id_VDU1_CP1_1",
            "resourceHandle": {
                "resourceId": "res_id_VDU1_CP1_1",
                "vimConnectionId": "vim_connection_id",
                "vimLevelResourceType": "OS::Neutron::Port"
            }
        },
        {
            "id": "res_id_VDU1_CP2_1",
            "changeType": "ADDED",
            "extCpInstanceId": "cp-res_id_VDU1_CP2_1",
            "resourceHandle": {
                "resourceId": "res_id_VDU1_CP2_1",
                "vimConnectionId": "vim_connection_id",
                "vimLevelResourceType": "OS::Neutron::Port"
            }
        },
        {
            "id": "res_id_VDU2_CP1",
            "changeType": "ADDED",
            "extCpInstanceId": "cp-res_id_VDU2_CP1",
            "resourceHandle": {
                "resourceId": "res_id_VDU2_CP1",
                "vimConnectionId": "vim_connection_id",
                "vimLevelResourceType": "OS::Neutron::Port"
            }
        },
        {
            "id": "res_id_VDU2_CP2",
            "changeType": "ADDED",
            "extCpInstanceId": "cp-res_id_VDU2_CP2",
            "resourceHandle": {
                "resourceId": "res_id_VDU2_CP2",
                "vimConnectionId": "vim_connection_id",
                "vimLevelResourceType": "OS::Neutron::Port"
            }
        },
    ],
    "affectedVirtualStorages": [
        {
            "id": "res_id_VirtualStorage_1",
            "virtualStorageDescId": "VirtualStorage",
            "changeType": "ADDED",
            "storageResource": {
                "vimConnectionId": "vim_connection_id",
                "resourceId": "res_id_VirtualStorage_1",
                "vimLevelResourceType": "OS::Cinder::Volume"
            }
        }
    ]
}

_expected_resource_changes_scale_out = {
    "affectedVnfcs": [
        {
            "id": "res_id_VDU1_2",
            "vduId": "VDU1",
            "changeType": "ADDED",
            "computeResource": {
                "vimConnectionId": "vim_connection_id",
                "resourceId": "res_id_VDU1_2",
                "vimLevelResourceType": "OS::Nova::Server"
            },
            "affectedVnfcCpIds": [
                "VDU1_CP1-res_id_VDU1_2",
                "VDU1_CP2-res_id_VDU1_2",
                "VDU1_CP3-res_id_VDU1_2",
                "VDU1_CP4-res_id_VDU1_2",
                "VDU1_CP5-res_id_VDU1_2"
            ],
            "addedStorageResourceIds": [
                "res_id_VirtualStorage_2"
            ]
        }
    ],
    "affectedVirtualLinks": [
        {
            "id": "res_id_internalVL1",
            "vnfVirtualLinkDescId": "internalVL1",
            "changeType": "LINK_PORT_ADDED",
            "networkResource": {
                "resourceId": "res_id_internalVL1"
            },
            "vnfLinkPortIds": [
                "res_id_VDU1_CP3_2"
            ]
        },
        {
            "id": "res_id_internalVL2",
            "vnfVirtualLinkDescId": "internalVL2",
            "changeType": "LINK_PORT_ADDED",
            "networkResource": {
                "vimConnectionId": "vim_connection_id",
                "resourceId": "res_id_internalVL2",
                "vimLevelResourceType": "OS::Neutron::Net"
            },
            "vnfLinkPortIds": [
                "res_id_VDU1_CP4_2"
            ]
        },
        {
            "id": "res_id_internalVL3",
            "vnfVirtualLinkDescId": "internalVL3",
            "changeType": "LINK_PORT_ADDED",
            "networkResource": {
                "vimConnectionId": "vim_connection_id",
                "resourceId": "res_id_internalVL3",
                "vimLevelResourceType": "OS::Neutron::Net"
            },
            "vnfLinkPortIds": [
                "res_id_VDU1_CP5_2"
            ]
        }
    ],
    "affectedExtLinkPorts": [
        {
            "id": "res_id_VDU1_CP1_2",
            "changeType": "ADDED",
            "extCpInstanceId": "cp-res_id_VDU1_CP1_2",
            "resourceHandle": {
                "resourceId": "res_id_VDU1_CP1_2",
                "vimConnectionId": "vim_connection_id",
                "vimLevelResourceType": "OS::Neutron::Port"
            }
        },
        {
            "id": "res_id_VDU1_CP2_2",
            "changeType": "ADDED",
            "extCpInstanceId": "cp-res_id_VDU1_CP2_2",
            "resourceHandle": {
                "resourceId": "res_id_VDU1_CP2_2",
                "vimConnectionId": "vim_connection_id",
                "vimLevelResourceType": "OS::Neutron::Port"
            }
        }
    ],
    "affectedVirtualStorages": [
        {
            "id": "res_id_VirtualStorage_2",
            "virtualStorageDescId": "VirtualStorage",
            "changeType": "ADDED",
            "storageResource": {
                "vimConnectionId": "vim_connection_id",
                "resourceId": "res_id_VirtualStorage_2",
                "vimLevelResourceType": "OS::Cinder::Volume"
            }
        }
    ]
}

_expected_resource_changes_scale_in = {
    "affectedVnfcs": [
        {
            "id": "res_id_VDU1_2",
            "vduId": "VDU1",
            "changeType": "REMOVED",
            "computeResource": {
                "vimConnectionId": "vim_connection_id",
                "resourceId": "res_id_VDU1_2",
                "vimLevelResourceType": "OS::Nova::Server"
            },
            "affectedVnfcCpIds": [
                "VDU1_CP1-res_id_VDU1_2",
                "VDU1_CP2-res_id_VDU1_2",
                "VDU1_CP3-res_id_VDU1_2",
                "VDU1_CP4-res_id_VDU1_2",
                "VDU1_CP5-res_id_VDU1_2"
            ],
            "removedStorageResourceIds": [
                "res_id_VirtualStorage_2"
            ]
        }
    ],
    "affectedVirtualLinks": [
        {
            "id": "res_id_internalVL1",
            "vnfVirtualLinkDescId": "internalVL1",
            "changeType": "LINK_PORT_REMOVED",
            "networkResource": {
                "resourceId": "res_id_internalVL1"
            },
            "vnfLinkPortIds": [
                "res_id_VDU1_CP3_2"
            ]
        },
        {
            "id": "res_id_internalVL2",
            "vnfVirtualLinkDescId": "internalVL2",
            "changeType": "LINK_PORT_REMOVED",
            "networkResource": {
                "vimConnectionId": "vim_connection_id",
                "resourceId": "res_id_internalVL2",
                "vimLevelResourceType": "OS::Neutron::Net"
            },
            "vnfLinkPortIds": [
                "res_id_VDU1_CP4_2"
            ]
        },
        {
            "id": "res_id_internalVL3",
            "vnfVirtualLinkDescId": "internalVL3",
            "changeType": "LINK_PORT_REMOVED",
            "networkResource": {
                "vimConnectionId": "vim_connection_id",
                "resourceId": "res_id_internalVL3",
                "vimLevelResourceType": "OS::Neutron::Net"
            },
            "vnfLinkPortIds": [
                "res_id_VDU1_CP5_2"
            ]
        }
    ],
    "affectedExtLinkPorts": [
        {
            "id": "res_id_VDU1_CP1_2",
            "changeType": "REMOVED",
            "extCpInstanceId": "cp-res_id_VDU1_CP1_2",
            "resourceHandle": {
                "resourceId": "res_id_VDU1_CP1_2",
                "vimConnectionId": "vim_connection_id",
                "vimLevelResourceType": "OS::Neutron::Port"
            }
        },
        {
            "id": "res_id_VDU1_CP2_2",
            "changeType": "REMOVED",
            "extCpInstanceId": "cp-res_id_VDU1_CP2_2",
            "resourceHandle": {
                "resourceId": "res_id_VDU1_CP2_2",
                "vimConnectionId": "vim_connection_id",
                "vimLevelResourceType": "OS::Neutron::Port"
            }
        }
    ],
    "affectedVirtualStorages": [
        {
            "id": "res_id_VirtualStorage_2",
            "virtualStorageDescId": "VirtualStorage",
            "changeType": "REMOVED",
            "storageResource": {
                "vimConnectionId": "vim_connection_id",
                "resourceId": "res_id_VirtualStorage_2",
                "vimLevelResourceType": "OS::Cinder::Volume"
            }
        }
    ]
}

_expected_resource_changes_terminate = {
    "affectedVnfcs": [
        {
            "id": "res_id_VDU1_1",
            "vduId": "VDU1",
            "changeType": "REMOVED",
            "computeResource": {
                "vimConnectionId": "vim_connection_id",
                "resourceId": "res_id_VDU1_1",
                "vimLevelResourceType": "OS::Nova::Server"
            },
            "affectedVnfcCpIds": [
                "VDU1_CP1-res_id_VDU1_1",
                "VDU1_CP2-res_id_VDU1_1",
                "VDU1_CP3-res_id_VDU1_1",
                "VDU1_CP4-res_id_VDU1_1",
                "VDU1_CP5-res_id_VDU1_1"
            ],
            "removedStorageResourceIds": [
                "res_id_VirtualStorage_1"
            ]
        },
        {
            "id": "res_id_VDU2",
            "vduId": "VDU2",
            "changeType": "REMOVED",
            "computeResource": {
                "vimConnectionId": "vim_connection_id",
                "resourceId": "res_id_VDU2",
                "vimLevelResourceType": "OS::Nova::Server"
            },
            "affectedVnfcCpIds": [
                "VDU2_CP1-res_id_VDU2",
                "VDU2_CP2-res_id_VDU2",
                "VDU2_CP3-res_id_VDU2",
                "VDU2_CP4-res_id_VDU2",
                "VDU2_CP5-res_id_VDU2"
            ]
        }
    ],
    "affectedVirtualLinks": [
        {
            "id": "res_id_internalVL1",
            "vnfVirtualLinkDescId": "internalVL1",
            "changeType": "LINK_PORT_REMOVED",
            "networkResource": {
                "resourceId": "res_id_internalVL1"
            },
            "vnfLinkPortIds": [
                "res_id_VDU1_CP3_1",
                "res_id_VDU2_CP3"
            ]
        },
        {
            "id": "res_id_internalVL2",
            "vnfVirtualLinkDescId": "internalVL2",
            "changeType": "REMOVED",
            "networkResource": {
                "vimConnectionId": "vim_connection_id",
                "resourceId": "res_id_internalVL2",
                "vimLevelResourceType": "OS::Neutron::Net"
            },
            "vnfLinkPortIds": [
                "res_id_VDU1_CP4_1",
                "res_id_VDU2_CP4"
            ]
        },
        {
            "id": "res_id_internalVL3",
            "vnfVirtualLinkDescId": "internalVL3",
            "changeType": "REMOVED",
            "networkResource": {
                "vimConnectionId": "vim_connection_id",
                "resourceId": "res_id_internalVL3",
                "vimLevelResourceType": "OS::Neutron::Net"
            },
            "vnfLinkPortIds": [
                "res_id_VDU1_CP5_1",
                "res_id_VDU2_CP5"
            ]
        }
    ],
    "affectedExtLinkPorts": [
        {
            "id": "res_id_VDU1_CP1_1",
            "changeType": "REMOVED",
            "extCpInstanceId": "cp-res_id_VDU1_CP1_1",
            "resourceHandle": {
                "resourceId": "res_id_VDU1_CP1_1",
                "vimConnectionId": "vim_connection_id",
                "vimLevelResourceType": "OS::Neutron::Port"
            }
        },
        {
            "id": "res_id_VDU1_CP2_1",
            "changeType": "REMOVED",
            "extCpInstanceId": "cp-res_id_VDU1_CP2_1",
            "resourceHandle": {
                "resourceId": "res_id_VDU1_CP2_1",
                "vimConnectionId": "vim_connection_id",
                "vimLevelResourceType": "OS::Neutron::Port"
            }
        },
        {
            "id": "res_id_VDU2_CP1",
            "changeType": "REMOVED",
            "extCpInstanceId": "cp-res_id_VDU2_CP1",
            "resourceHandle": {
                "resourceId": "res_id_VDU2_CP1",
                "vimConnectionId": "vim_connection_id",
                "vimLevelResourceType": "OS::Neutron::Port"
            }
        },
        {
            "id": "res_id_VDU2_CP2",
            "changeType": "REMOVED",
            "extCpInstanceId": "cp-res_id_VDU2_CP2",
            "resourceHandle": {
                "resourceId": "res_id_VDU2_CP2",
                "vimConnectionId": "vim_connection_id",
                "vimLevelResourceType": "OS::Neutron::Port"
            }
        }
    ],
    "affectedVirtualStorages": [
        {
            "id": "res_id_VirtualStorage_1",
            "virtualStorageDescId": "VirtualStorage",
            "changeType": "REMOVED",
            "storageResource": {
                "vimConnectionId": "vim_connection_id",
                "resourceId": "res_id_VirtualStorage_1",
                "vimLevelResourceType": "OS::Cinder::Volume"
            }
        }
    ]
}

# update_lcmocc  modifies an "Individual VNF instance" example
_modify_inst_saved_example = {
    "id": "1098e2dc-d954-484e-b417-e594ff03c55b",
    "vnfInstanceName": "instance_name",
    "vnfInstanceDescription": "description",
    "vnfdId": "a93b7f96-f0e1-49f2-b3f0-75f5b4a94d0f",
    "vnfProvider": "provider",
    "vnfProductName": "product name",
    "vnfSoftwareVersion": "software version",
    "vnfdVersion": "vnfd version",
    "instantiationState": "INSTANTIATED",
    "vnfConfigurableProperties": {
        "vnfproperties": "example"
    },
    "metadata": {
        "metadata": "example"
    },
    "extensions": {
        "extensions": "example"
    },
    "vimConnectionInfo": {
        "vim1": {
            "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_3",
            "vimId": "ca925611-f020-4b0e-a56d-3fd5c6d5bc3d",
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
    },
    "instantiatedVnfInfo": {
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
}

_modify_inst_example = {
    "id": "1098e2dc-d954-484e-b417-e594ff03c55b",
    "vnfInstanceName": "instance_name_1",
    "vnfdId": "a93b7f96-f0e1-49f2-b3f0-75f5b4a94dff",
    "vnfProvider": "provider",
    "vnfProductName": "product name",
    "vnfSoftwareVersion": "software version_1",
    "vnfdVersion": "vnfd version_1",
    "metadata": {
        "metadata": "example_1"
    },
    "extensions": {
        "extensions": "example"
    },
    "vimConnectionInfo": {
        "vim1": {
            "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_3",
            "vimId": "ca925611-f020-4b0e-a56d-3fd5c6d5bc3d",
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
                "vnfcConfigurableProperties": {}
            }
        ]
    }
}

_expected_changedInfo = {
    "vnfInstanceName": "instance_name_1",
    "vnfdId": "a93b7f96-f0e1-49f2-b3f0-75f5b4a94dff",
    "vnfSoftwareVersion": "software version_1",
    "vnfdVersion": "vnfd version_1",
    "metadata": {
        "metadata": "example_1"
    },
    "vimConnectionInfo": {
        "vim1": {
            "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_3",
            "vimId": "ca925611-f020-4b0e-a56d-3fd5c6d5bc3d",
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
                "key": "value",
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
            "vnfcConfigurableProperties": {}
        }
    ]
}

_expected_resource_changes_change_ext_conn = {
    "affectedExtLinkPorts": [
        {
            "id": "res_id_VDU2_CP1",
            "changeType": "REMOVED",
            "extCpInstanceId": "cp-res_id_VDU2_CP1",
            "resourceHandle": {
                "resourceId": "res_id_VDU2_CP1",
                "vimConnectionId": "vim_connection_id",
                "vimLevelResourceType": "OS::Neutron::Port"
            }
        },
        {
            "id": "res_id_VDU2_CP1_modified",
            "changeType": "ADDED",
            "extCpInstanceId": "cp-res_id_VDU2_CP1",
            "resourceHandle": {
                "resourceId": "res_id_VDU2_CP1_modified",
                "vimConnectionId": "vim_connection_id",
                "vimLevelResourceType": "OS::Neutron::Port"
            }
        }
    ]
}

_expected_changed_ext_connectivity = [
    # sort by id
    _inst_info_example_3['extVirtualLinkInfo'][1],
    _inst_info_example_3['extVirtualLinkInfo'][0],
    _inst_info_example_3['extVirtualLinkInfo'][4]
]

_expected_resource_changes_heal = {
    "affectedVnfcs": [
        {
            "id": "res_id_VDU1_1",
            "vduId": "VDU1",
            "changeType": "REMOVED",
            "computeResource": {
                "vimConnectionId": "vim_connection_id",
                "resourceId": "res_id_VDU1_1",
                "vimLevelResourceType": "OS::Nova::Server"
            },
            "affectedVnfcCpIds": [
                "VDU1_CP1-res_id_VDU1_1",
                "VDU1_CP2-res_id_VDU1_1",
                "VDU1_CP3-res_id_VDU1_1",
                "VDU1_CP4-res_id_VDU1_1",
                "VDU1_CP5-res_id_VDU1_1"
            ]
        },
        {
            "id": "res_id_VDU1_1_new",
            "vduId": "VDU1",
            "changeType": "ADDED",
            "computeResource": {
                "vimConnectionId": "vim_connection_id",
                "resourceId": "res_id_VDU1_1_new",
                "vimLevelResourceType": "OS::Nova::Server"
            },
            "affectedVnfcCpIds": [
                "VDU1_CP1-res_id_VDU1_1_new",
                "VDU1_CP2-res_id_VDU1_1_new",
                "VDU1_CP3-res_id_VDU1_1_new",
                "VDU1_CP4-res_id_VDU1_1_new",
                "VDU1_CP5-res_id_VDU1_1_new"
            ]
        },
        {
            "id": "res_id_VDU1_2",
            "vduId": "VDU1",
            "changeType": "REMOVED",
            "computeResource": {
                "vimConnectionId": "vim_connection_id",
                "resourceId": "res_id_VDU1_2",
                "vimLevelResourceType": "OS::Nova::Server"
            },
            "affectedVnfcCpIds": [
                "VDU1_CP1-res_id_VDU1_2",
                "VDU1_CP2-res_id_VDU1_2",
                "VDU1_CP3-res_id_VDU1_2",
                "VDU1_CP4-res_id_VDU1_2",
                "VDU1_CP5-res_id_VDU1_2"
            ],
            "removedStorageResourceIds": [
                "res_id_VirtualStorage_2"
            ]
        },
        {
            "id": "res_id_VDU1_2_new",
            "vduId": "VDU1",
            "changeType": "ADDED",
            "computeResource": {
                "vimConnectionId": "vim_connection_id",
                "resourceId": "res_id_VDU1_2_new",
                "vimLevelResourceType": "OS::Nova::Server"
            },
            "affectedVnfcCpIds": [
                "VDU1_CP1-res_id_VDU1_2_new",
                "VDU1_CP2-res_id_VDU1_2_new",
                "VDU1_CP3-res_id_VDU1_2_new",
                "VDU1_CP4-res_id_VDU1_2_new",
                "VDU1_CP5-res_id_VDU1_2_new"
            ],
            "addedStorageResourceIds": [
                "res_id_VirtualStorage_2_new"
            ]
        },
    ],
    "affectedVirtualLinks": [
        # NOTE: id is same but expected LINK_PORT_ADDED is first based on the
        # code.
        {
            "id": "res_id_internalVL1",
            "vnfVirtualLinkDescId": "internalVL1",
            "changeType": "LINK_PORT_ADDED",
            "networkResource": {
                "resourceId": "res_id_internalVL1"
            },
            "vnfLinkPortIds": [
                "res_id_VDU1_CP3_1_changed",
                "res_id_VDU1_CP3_2_changed",
                "res_id_VDU2_CP3_changed"
            ]
        },
        {
            "id": "res_id_internalVL1",
            "vnfVirtualLinkDescId": "internalVL1",
            "changeType": "LINK_PORT_REMOVED",
            "networkResource": {
                "resourceId": "res_id_internalVL1"
            },
            "vnfLinkPortIds": [
                "res_id_VDU1_CP3_1",
                "res_id_VDU1_CP3_2",
                "res_id_VDU2_CP3"
            ]
        }
    ],
    "affectedVirtualStorages": [
        {
            "id": "res_id_VirtualStorage_2",
            "virtualStorageDescId": "VirtualStorage",
            "changeType": "REMOVED",
            "storageResource": {
                "vimConnectionId": "vim_connection_id",
                "resourceId": "res_id_VirtualStorage_2",
                "vimLevelResourceType": "OS::Cinder::Volume"
            }
        },
        {
            "id": "res_id_VirtualStorage_2_new",
            "virtualStorageDescId": "VirtualStorage",
            "changeType": "ADDED",
            "storageResource": {
                "vimConnectionId": "vim_connection_id",
                "resourceId": "res_id_VirtualStorage_2_new",
                "vimLevelResourceType": "OS::Cinder::Volume"
            }
        }
    ]
}
_expected_resource_changes_change_vnfpkg = {
    "affectedVnfcs": [
        {
            "id": "res_id_VDU1_1",
            "vduId": "VDU1",
            "changeType": "REMOVED",
            "computeResource": {
                "vimConnectionId": "vim_connection_id",
                "resourceId": "res_id_VDU1_1",
                "vimLevelResourceType": "OS::Nova::Server"
            },
            "affectedVnfcCpIds": [
                "VDU1_CP1-res_id_VDU1_1",
                "VDU1_CP2-res_id_VDU1_1",
                "VDU1_CP3-res_id_VDU1_1",
                "VDU1_CP4-res_id_VDU1_1",
                "VDU1_CP5-res_id_VDU1_1"
            ],
            "removedStorageResourceIds": [
                "res_id_VirtualStorage_1"
            ]
        },
        {
            "id": "res_id_VDU1_1_update",
            "vduId": "VDU1",
            "changeType": "ADDED",
            "computeResource": {
                "vimConnectionId": "vim_connection_id",
                "resourceId": "res_id_VDU1_1_update",
                "vimLevelResourceType": "OS::Nova::Server"
            },
            "affectedVnfcCpIds": [
                "VDU1_CP1-res_id_VDU1_1",
                "VDU1_CP2-res_id_VDU1_1",
                "VDU1_CP3-res_id_VDU1_1",
                "VDU1_CP4-res_id_VDU1_1",
                "VDU1_CP5-res_id_VDU1_1"
            ],
            "addedStorageResourceIds": [
                "new_res_id_VirtualStorage_1"
            ],
            'metadata': {
                'current_vnfd_id': 'new_vnfd_id'
            }
        },
        {
            "id": "res_id_VDU2",
            "vduId": "VDU2",
            "changeType": "MODIFIED",
            "computeResource": {
                "vimConnectionId": "vim_connection_id",
                "resourceId": "res_id_VDU2",
                "vimLevelResourceType": "OS::Nova::Server"
            },
            "affectedVnfcCpIds": [
                "VDU2_CP1-res_id_VDU2",
                "VDU2_CP2-res_id_VDU2",
                "VDU2_CP3-res_id_VDU2",
                "VDU2_CP4-res_id_VDU2",
                "VDU2_CP5-res_id_VDU2"
            ],
            'metadata': {
                'current_vnfd_id': 'new_vnfd_id'
            }
        }
    ],
    "affectedVirtualStorages": [
        {
            "id": "new_res_id_VirtualStorage_1",
            "virtualStorageDescId": "VirtualStorage",
            "changeType": "ADDED",
            "storageResource": {
                "vimConnectionId": "vim_connection_id",
                "resourceId": "new_res_id_VirtualStorage_1",
                "vimLevelResourceType": "OS::Cinder::Volume"
            }
        },
        {
            "id": "res_id_VirtualStorage_1",
            "virtualStorageDescId": "VirtualStorage",
            "changeType": "REMOVED",
            "storageResource": {
                "vimConnectionId": "vim_connection_id",
                "resourceId": "res_id_VirtualStorage_1",
                "vimLevelResourceType": "OS::Cinder::Volume"
            }
        }
    ]
}


class TestLcmOpOccUtils(base.BaseTestCase):

    def setUp(self):
        super(TestLcmOpOccUtils, self).setUp()
        objects.register_all()
        self.context = context.get_admin_context()

    def _sort_resource_changes(self, result):
        # sort lists before compare with an expected_result since
        # order of list items is unpredictable.
        # note that an expected_result is already sorted.
        def _get_key(obj):
            return obj['id']

        if 'affectedVnfcs' in result:
            result['affectedVnfcs'].sort(key=_get_key)
            for vnfc in result['affectedVnfcs']:
                if 'affectedVnfcCpIds' in vnfc:
                    vnfc['affectedVnfcCpIds'].sort()
                if 'removedStorageResourceIds' in vnfc:
                    vnfc['removedStorageResourceIds'].sort()

        if 'affectedVirtualLinks' in result:
            result['affectedVirtualLinks'].sort(key=_get_key)
            for vl in result['affectedVirtualLinks']:
                if 'vnfLinkPortIds' in vl:
                    vl['vnfLinkPortIds'].sort()

        if 'affectedExtLinkPorts' in result:
            result['affectedExtLinkPorts'].sort(key=_get_key)

        if 'affectedVirtualStorages' in result:
            result['affectedVirtualStorages'].sort(key=_get_key)

        return result

    def test_update_lcmocc_instantiate(self):
        # prepare
        inst_saved = objects.VnfInstanceV2()
        inst = objects.VnfInstanceV2()
        inst.instantiatedVnfInfo = (
            objects.VnfInstanceV2_InstantiatedVnfInfo.from_dict(
                _inst_info_example_1))
        lcmocc = objects.VnfLcmOpOccV2(
            operation=fields.LcmOperationType.INSTANTIATE)

        # execute update_lcmocc
        lcmocc_utils.update_lcmocc(lcmocc, inst_saved, inst)

        # check resourceChanges
        lcmocc = lcmocc.to_dict()
        self.assertEqual(
            _expected_resource_changes_instantiate,
            self._sort_resource_changes(lcmocc['resourceChanges']))

    def test_update_lcmocc_scale_out(self):
        # prepare
        inst_saved = objects.VnfInstanceV2()
        inst_saved.instantiatedVnfInfo = (
            objects.VnfInstanceV2_InstantiatedVnfInfo.from_dict(
                _inst_info_example_1))
        inst = objects.VnfInstanceV2()
        inst.instantiatedVnfInfo = (
            objects.VnfInstanceV2_InstantiatedVnfInfo.from_dict(
                _inst_info_example_2))
        lcmocc = objects.VnfLcmOpOccV2(
            operation=fields.LcmOperationType.SCALE)

        # execute update_lcmocc
        lcmocc_utils.update_lcmocc(lcmocc, inst_saved, inst)

        # check resourceChanges
        lcmocc = lcmocc.to_dict()
        self.assertEqual(
            _expected_resource_changes_scale_out,
            self._sort_resource_changes(lcmocc['resourceChanges']))

    def test_update_lcmocc_scale_in(self):
        # prepare
        inst_saved = objects.VnfInstanceV2()
        inst_saved.instantiatedVnfInfo = (
            objects.VnfInstanceV2_InstantiatedVnfInfo.from_dict(
                _inst_info_example_2))
        inst = objects.VnfInstanceV2()
        inst.instantiatedVnfInfo = (
            objects.VnfInstanceV2_InstantiatedVnfInfo.from_dict(
                _inst_info_example_1))
        lcmocc = objects.VnfLcmOpOccV2(
            operation=fields.LcmOperationType.SCALE)

        # execute update_lcmocc
        lcmocc_utils.update_lcmocc(lcmocc, inst_saved, inst)

        # check resourceChanges
        lcmocc = lcmocc.to_dict()
        self.assertEqual(_expected_resource_changes_scale_in,
            self._sort_resource_changes(lcmocc['resourceChanges']))

    def test_update_lcmocc_terminate(self):
        # prepare
        inst_saved = objects.VnfInstanceV2()
        inst_saved.instantiatedVnfInfo = (
            objects.VnfInstanceV2_InstantiatedVnfInfo.from_dict(
                _inst_info_example_1))
        inst = objects.VnfInstanceV2()
        inst.instantiatedVnfInfo = objects.VnfInstanceV2_InstantiatedVnfInfo(
            flavourId="SAMPLE_VNFD_ID",
            vnfState='STOPPED')
        lcmocc = objects.VnfLcmOpOccV2(
            operation=fields.LcmOperationType.TERMINATE)

        # execute update_lcmocc
        lcmocc_utils.update_lcmocc(lcmocc, inst_saved, inst)

        # check resourceChanges
        lcmocc = lcmocc.to_dict()
        self.assertEqual(_expected_resource_changes_terminate,
            self._sort_resource_changes(lcmocc['resourceChanges']))

    def test_update_lcmocc_modify(self):
        # prepare
        inst_saved = objects.VnfInstanceV2.from_dict(
            _modify_inst_saved_example)
        inst = objects.VnfInstanceV2.from_dict(_modify_inst_example)
        lcmocc = objects.VnfLcmOpOccV2(
            operation=fields.LcmOperationType.MODIFY_INFO)

        # execute update_lcmocc
        lcmocc_utils.update_lcmocc(lcmocc, inst_saved, inst)
        # check changedInfo
        lcmocc = lcmocc.to_dict()
        self.assertEqual(_expected_changedInfo, lcmocc['changedInfo'])

    def test_update_lcmocc_change_ext_conn(self):
        # prepare
        inst_saved = objects.VnfInstanceV2()
        inst_saved.instantiatedVnfInfo = (
            objects.VnfInstanceV2_InstantiatedVnfInfo.from_dict(
                _inst_info_example_1))
        inst = objects.VnfInstanceV2()
        inst.instantiatedVnfInfo = (
            objects.VnfInstanceV2_InstantiatedVnfInfo.from_dict(
                _inst_info_example_3))
        lcmocc = objects.VnfLcmOpOccV2(
            operation=fields.LcmOperationType.CHANGE_EXT_CONN)

        # execute update_lcmocc
        lcmocc_utils.update_lcmocc(lcmocc, inst_saved, inst)

        # check resourceChanges
        lcmocc = lcmocc.to_dict()
        self.assertEqual(
            _expected_resource_changes_change_ext_conn,
            self._sort_resource_changes(lcmocc['resourceChanges']))
        self.assertEqual(
            _expected_changed_ext_connectivity,
            sorted(lcmocc['changedExtConnectivity'], key=lambda x: x['id']))

    def test_update_lcmocc_heal(self):
        # NOTE: from the view point of update_lcmocc unit test coverage,
        # it is enough to check server and/or volume update.
        # prepare
        inst_saved = objects.VnfInstanceV2()
        inst_saved.instantiatedVnfInfo = (
            objects.VnfInstanceV2_InstantiatedVnfInfo.from_dict(
                _inst_info_example_2))
        inst = objects.VnfInstanceV2()
        inst.instantiatedVnfInfo = (
            objects.VnfInstanceV2_InstantiatedVnfInfo.from_dict(
                _inst_info_example_4))
        lcmocc = objects.VnfLcmOpOccV2(
            operation=fields.LcmOperationType.HEAL)

        # execute update_lcmocc
        lcmocc_utils.update_lcmocc(lcmocc, inst_saved, inst)

        # check resourceChanges
        lcmocc = lcmocc.to_dict()
        self.assertEqual(
            _expected_resource_changes_heal,
            self._sort_resource_changes(lcmocc['resourceChanges']))

    def test_update_lcmocc_change_vnfpkg(self):
        # prepare
        inst_saved = objects.VnfInstanceV2()
        inst_saved.instantiatedVnfInfo = (
            objects.VnfInstanceV2_InstantiatedVnfInfo.from_dict(
                _inst_info_example_1))
        inst_saved.vnfdId = 'old_vnfd_id'
        inst = objects.VnfInstanceV2()
        inst.instantiatedVnfInfo = (
            objects.VnfInstanceV2_InstantiatedVnfInfo.from_dict(
                _inst_info_example_5))
        lcmocc = objects.VnfLcmOpOccV2(operation='CHANGE_VNFPKG')

        # execute update_lcmocc
        lcmocc_utils.update_lcmocc(lcmocc, inst_saved, inst)

        # check resourceChanges
        lcmocc = lcmocc.to_dict()
        self.assertEqual(
            _expected_resource_changes_change_vnfpkg,
            self._sort_resource_changes(lcmocc['resourceChanges']))
