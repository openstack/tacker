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

import os

from tacker import context
from tacker.sol_refactored.common import vnfd_utils
from tacker.sol_refactored.infra_drivers.openstack import openstack
from tacker.sol_refactored import objects
from tacker.sol_refactored.objects.v2 import fields
from tacker.tests import base


SAMPLE_VNFD_ID = "b1bb0ce7-ebca-4fa7-95ed-4840d7000000"
SAMPLE_FLAVOUR_ID = "simple"

# instantiateVnfRequest example
_vim_connection_info_example = {
    "vimId": "vim_id_1",
    "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_3",
    # "interfaceInfo": omitted
    # "accessInfo": omitted
}

_instantiate_req_example = {
    "flavourId": SAMPLE_FLAVOUR_ID,
    "extVirtualLinks": [
        {
            "id": "id_ext_vl_1",
            "resourceId": "res_id_ext_vl_1",
            "extCps": [
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
            "id": "id_ext_vl_2",
            "resourceId": "res_id_id_ext_vl_2",
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
                                                "subnetId": "res_id_subnet_1"
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
                            "linkPortId": "link_port_id_VDU2_CP2"
                        }
                    }
                }
            ],
            "extLinkPorts": [
                {
                    "id": "link_port_id_VDU2_CP2",
                    "resourceHandle": {
                        "resourceId": "res_id_VDU2_CP2"
                    }
                }
            ]
        }
    ],
    "extManagedVirtualLinks": [
        {
            "id": "id_ext_mgd_1",
            "vnfVirtualLinkDescId": "internalVL1",
            "resourceId": "res_id_internalVL1"
        }
    ],
    "vimConnectionInfo": {
        "vim1": _vim_connection_info_example
    }
}

# heat resources example
# NOTE:
# - following attributes which are not related to tests are omitted.
#   updated_time, logical_resource_id, resource_status, resource_status_reason
#   and "rel: self" in links.
# - some identifiers are modified to make check easy.
# - stack_id is based on real example.
_url = "http://127.0.0.1/heat-api/v1/57bcfdcbccbc4b85a9a4c94690a1164f/stacks/"
_stack_id = ("vnf-768c24d2-2ea6-4225-b1c7-79e42abfbde6/"
             "1fa212ca-e904-4109-9a96-1900d35d2a5b")
_href = "".join((_url, _stack_id))

_stack_id_VDU1_scale = (
    "vnf-768c24d2-2ea6-4225-b1c7-79e42abfbde6-VDU1_scale_group-dv4kv7qtcwhw/"
    "53ee92b6-8193-4df5-90f7-2738e61fba2c")
_href_VDU1_scale = "".join((_url, _stack_id_VDU1_scale))

_stack_id_VDU1_1 = (
    "vnf-768c24d2-2ea6-4225-b1c7-79e42abfbde6-VDU1_scale_group-dv4kv7qtcwhw-"
    "bemybz4ugeso-mrajuhqw7ath/ea59d312-bab3-4ef2-897c-88b5cee117de")
_href_VDU1_1 = "".join((_url, _stack_id_VDU1_1))

_stack_id_VDU1_2 = (
    "vnf-768c24d2-2ea6-4225-b1c7-79e42abfbde6-VDU1_scale_group-dv4kv7qtcwhw-"
    "myet4efobvvp-aptv6apap2h5/dd94d2ae-a02b-4fab-a492-514c422299ec")
_href_VDU1_2 = "".join((_url, _stack_id_VDU1_2))

_heat_reses_example = [
    {
        "creation_time": "2021-12-10T00:40:46Z",
        "resource_name": "VDU2",
        "physical_resource_id": "res_id_VDU2",
        "resource_type": "OS::Nova::Server",
        "links": [
            {
                "href": _href,
                "rel": "stack"
            }
        ],
        "required_by": []
    },
    {
        "creation_time": "2021-12-10T00:40:46Z",
        "resource_name": "VDU2_CP1",
        "physical_resource_id": "res_id_VDU2_CP1",
        "resource_type": "OS::Neutron::Port",
        "links": [
            {
                "href": _href,
                "rel": "stack"
            }
        ],
        "required_by": [
            "VDU2"
        ]
    },
    {
        "creation_time": "2021-12-10T00:40:47Z",
        "resource_name": "VDU2_CP5",
        "physical_resource_id": "res_id_VDU2_CP5",
        "resource_type": "OS::Neutron::Port",
        "links": [
            {
                "href": _href,
                "rel": "stack"
            }
        ],
        "required_by": [
            "VDU2"
        ]
    },
    {
        "creation_time": "2021-12-10T00:40:49Z",
        "resource_name": "internalVL3_subnet",
        "physical_resource_id": "06f68f37-d37c-4310-8756-3884d9b8cb4b",
        "resource_type": "OS::Neutron::Subnet",
        "links": [
            {
                "href": _href,
                "rel": "stack"
            }
        ],
        "required_by": [
            "VDU2",
            "VDU2_CP5"
        ]
    },
    {
        "creation_time": "2021-12-10T00:40:51Z",
        "resource_name": "VDU2_CP3",
        "physical_resource_id": "res_id_VDU2_CP3",
        "resource_type": "OS::Neutron::Port",
        "links": [
            {
                "href": _href,
                "rel": "stack"
            }
        ],
        "required_by": [
            "VDU2"
        ]
    },
    {
        "creation_time": "2021-12-10T00:40:53Z",
        "resource_name": "VDU2_CP4",
        "physical_resource_id": "res_id_VDU2_CP4",
        "resource_type": "OS::Neutron::Port",
        "links": [
            {
                "href": _href,
                "rel": "stack"
            }
        ],
        "required_by": [
            "VDU2"
        ]
    },
    {
        "creation_time": "2021-12-10T00:40:53Z",
        "resource_name": "VDU1_scale_out",
        "physical_resource_id": "234c78aefbaa4770ba5bbd8c7f624584",
        "resource_type": "OS::Heat::ScalingPolicy",
        "links": [
            {
                "href": _href,
                "rel": "stack"
            }
        ],
        "required_by": []
    },
    {
        "creation_time": "2021-12-10T00:40:53Z",
        "resource_name": "VDU1_scale_in",
        "physical_resource_id": "7cb738b392a64936a14f92bb79123a42",
        "resource_type": "OS::Heat::ScalingPolicy",
        "links": [
            {
                "href": _href,
                "rel": "stack"
            }
        ],
        "required_by": []
    },
    {
        "creation_time": "2021-12-10T00:40:53Z",
        "resource_name": "VDU1_scale_group",
        "physical_resource_id": "53ee92b6-8193-4df5-90f7-2738e61fba2c",
        "resource_type": "OS::Heat::AutoScalingGroup",
        "links": [
            {
                "href": _href,
                "rel": "stack"
            },
            {
                "href": _href_VDU1_scale,
                "rel": "nested"
            }
        ],
        "required_by": [
            "VDU1_scale_out",
            "VDU1_scale_in"
        ]
    },
    {
        "creation_time": "2021-12-10T00:40:55Z",
        "resource_name": "internalVL3",
        "physical_resource_id": "res_id_internalVL3",
        "resource_type": "OS::Neutron::Net",
        "links": [
            {
                "href": _href,
                "rel": "stack"
            }
        ],
        "required_by": [
            "internalVL3_subnet",
            "VDU2_CP5",
            "VDU1_scale_group"
        ]
    },
    {
        "creation_time": "2021-12-10T00:40:56Z",
        "resource_name": "internalVL2_subnet",
        "physical_resource_id": "848bc969-cc5c-47b2-94de-469556b993fb",
        "resource_type": "OS::Neutron::Subnet",
        "links": [
            {
                "href": _href,
                "rel": "stack"
            }
        ],
        "required_by": [
            "VDU2",
            "VDU2_CP4"
        ]
    },
    {
        "creation_time": "2021-12-10T00:40:58Z",
        "resource_name": "internalVL2",
        "physical_resource_id": "res_id_internalVL2",
        "resource_type": "OS::Neutron::Net",
        "links": [
            {
                "href": _href,
                "rel": "stack"
            }
        ],
        "required_by": [
            "VDU2_CP4",
            "internalVL2_subnet",
            "VDU1_scale_group"
        ]
    },
    {
        "creation_time": "2021-12-10T00:41:35Z",
        "resource_name": "bemybz4ugeso",
        "physical_resource_id": "ea59d312-bab3-4ef2-897c-88b5cee117de",
        "resource_type": "VDU1.yaml",
        "links": [
            {
                "href": _href_VDU1_scale,
                "rel": "stack"
            },
            {
                "href": _href_VDU1_1,
                "rel": "nested"
            }
        ],
        "required_by": [],
        "parent_resource": "VDU1_scale_group"
    },
    {
        "creation_time": "2021-12-10T01:03:37Z",
        "resource_name": "myet4efobvvp",
        "physical_resource_id": "dd94d2ae-a02b-4fab-a492-514c422299ec",
        "resource_type": "VDU1.yaml",
        "links": [
            {
                "href": _href_VDU1_scale,
                "rel": "stack"
            },
            {
                "href": _href_VDU1_2,
                "rel": "nested"
            }
        ],
        "required_by": [],
        "parent_resource": "VDU1_scale_group"
    },
    {
        "creation_time": "2021-12-10T00:41:43Z",
        "resource_name": "VDU1",
        "physical_resource_id": "res_id_VDU1_1",
        "resource_type": "OS::Nova::Server",
        "links": [
            {
                "href": _href_VDU1_1,
                "rel": "stack"
            }
        ],
        "required_by": [],
        "parent_resource": "bemybz4ugeso"
    },
    {
        "creation_time": "2021-12-10T00:41:45Z",
        "resource_name": "VirtualStorage",
        "physical_resource_id": "res_id_VirtualStorage_1",
        "resource_type": "OS::Cinder::Volume",
        "links": [
            {
                "href": _href_VDU1_1,
                "rel": "stack"
            }
        ],
        "required_by": [
            "VDU1"
        ],
        "parent_resource": "bemybz4ugeso"
    },
    {
        "creation_time": "2021-12-10T00:41:45Z",
        "resource_name": "multi",
        "physical_resource_id": "0690bb1b-36d0-4684-851b-9c1b13a9a5de",
        "resource_type": "OS::Cinder::VolumeType",
        "links": [
            {
                "href": _href_VDU1_1,
                "rel": "stack"
            }
        ],
        "required_by": [
            "VirtualStorage"
        ],
        "parent_resource": "bemybz4ugeso"
    },
    {
        "creation_time": "2021-12-10T00:41:45Z",
        "resource_name": "VDU1_CP2",
        "physical_resource_id": "res_id_VDU1_CP2_1",
        "resource_type": "OS::Neutron::Port",
        "links": [
            {
                "href": _href_VDU1_1,
                "rel": "stack"
            }
        ],
        "required_by": [
            "VDU1"
        ],
        "parent_resource": "bemybz4ugeso"
    },
    {
        "creation_time": "2021-12-10T00:41:45Z",
        "resource_name": "VDU1_CP1",
        "physical_resource_id": "res_id_VDU1_CP1_1",
        "resource_type": "OS::Neutron::Port",
        "links": [
            {
                "href": _href_VDU1_1,
                "rel": "stack"
            }
        ],
        "required_by": [
            "multi",
            "VDU1"
        ],
        "parent_resource": "bemybz4ugeso"
    },
    {
        "creation_time": "2021-12-10T00:41:45Z",
        "resource_name": "VDU1_CP4",
        "physical_resource_id": "res_id_VDU1_CP4_1",
        "resource_type": "OS::Neutron::Port",
        "links": [
            {
                "href": _href_VDU1_1,
                "rel": "stack"
            }
        ],
        "required_by": [
            "VDU1"
        ],
        "parent_resource": "bemybz4ugeso"
    },
    {
        "creation_time": "2021-12-10T00:41:45Z",
        "resource_name": "VDU1_CP5",
        "physical_resource_id": "res_id_VDU1_CP5_1",
        "resource_type": "OS::Neutron::Port",
        "links": [
            {
                "href": _href_VDU1_1,
                "rel": "stack"
            }
        ],
        "required_by": [
            "VDU1"
        ],
        "parent_resource": "bemybz4ugeso"
    },
    {
        "creation_time": "2021-12-10T00:41:46Z",
        "resource_name": "VDU1_CP3",
        "physical_resource_id": "res_id_VDU1_CP3_1",
        "resource_type": "OS::Neutron::Port",
        "links": [
            {
                "href": _href_VDU1_1,
                "rel": "stack"
            }
        ],
        "required_by": [
            "VDU1"
        ],
        "parent_resource": "bemybz4ugeso"
    },
    {
        "creation_time": "2021-12-10T01:03:49Z",
        "resource_name": "VDU1",
        "physical_resource_id": "res_id_VDU1_2",
        "resource_type": "OS::Nova::Server",
        "links": [
            {
                "href": _href_VDU1_2,
                "rel": "stack"
            }
        ],
        "required_by": [],
        "parent_resource": "myet4efobvvp"
    },
    {
        "creation_time": "2021-12-10T01:03:51Z",
        "resource_name": "VirtualStorage",
        "physical_resource_id": "res_id_VirtualStorage_2",
        "resource_type": "OS::Cinder::Volume",
        "links": [
            {
                "href": _href_VDU1_2,
                "rel": "stack"
            }
        ],
        "required_by": [
            "VDU1"
        ],
        "parent_resource": "myet4efobvvp"
    },
    {
        "creation_time": "2021-12-10T01:03:53Z",
        "resource_name": "multi",
        "physical_resource_id": "03433e3a-a8c4-40b3-8802-6b114922feff",
        "resource_type": "OS::Cinder::VolumeType",
        "links": [
            {
                "href": _href_VDU1_2,
                "rel": "stack"
            }
        ],
        "required_by": [
            "VirtualStorage"
        ],
        "parent_resource": "myet4efobvvp"
    },
    {
        "creation_time": "2021-12-10T01:03:53Z",
        "resource_name": "VDU1_CP2",
        "physical_resource_id": "res_id_VDU1_CP2_2",
        "resource_type": "OS::Neutron::Port",
        "links": [
            {
                "href": _href_VDU1_2,
                "rel": "stack"
            }
        ],
        "required_by": [
            "VDU1"
        ],
        "parent_resource": "myet4efobvvp"
    },
    {
        "creation_time": "2021-12-10T01:03:53Z",
        "resource_name": "VDU1_CP1",
        "physical_resource_id": "res_id_VDU1_CP1_2",
        "resource_type": "OS::Neutron::Port",
        "links": [
            {
                "href": _href_VDU1_2,
                "rel": "stack"
            }
        ],
        "required_by": [
            "multi",
            "VDU1"
        ],
        "parent_resource": "myet4efobvvp"
    },
    {
        "creation_time": "2021-12-10T01:03:53Z",
        "resource_name": "VDU1_CP4",
        "physical_resource_id": "res_id_VDU1_CP4_2",
        "resource_type": "OS::Neutron::Port",
        "links": [
            {
                "href": _href_VDU1_2,
                "rel": "stack"
            }
        ],
        "required_by": [
            "VDU1"
        ],
        "parent_resource": "myet4efobvvp"
    },
    {
        "creation_time": "2021-12-10T01:03:55Z",
        "resource_name": "VDU1_CP5",
        "physical_resource_id": "res_id_VDU1_CP5_2",
        "resource_type": "OS::Neutron::Port",
        "links": [
            {
                "href": _href_VDU1_2,
                "rel": "stack"
            }
        ],
        "required_by": [
            "VDU1"
        ],
        "parent_resource": "myet4efobvvp"
    },
    {
        "creation_time": "2021-12-10T01:03:57Z",
        "resource_name": "VDU1_CP3",
        "physical_resource_id": "res_id_VDU1_CP3_2",
        "resource_type": "OS::Neutron::Port",
        "links": [
            {
                "href": _href_VDU1_2,
                "rel": "stack"
            }
        ],
        "required_by": [
            "VDU1"
        ],
        "parent_resource": "myet4efobvvp"
    }
]

# expected results
_expected_inst_info = {
    "flavourId": "simple",
    "vnfState": "STARTED",
    "extCpInfo": [
        {
            'id': 'cp-req-link_port_id_VDU2_CP2',
            'cpdId': 'VDU2_CP2',
            'cpConfigId': 'VDU2_CP2_1',
            'extLinkPortId': 'req-link_port_id_VDU2_CP2',
        },
        {
            "id": "cp-res_id_VDU1_CP1_1",
            "cpdId": "VDU1_CP1",
            "cpConfigId": "VDU1_CP1_1",
            "cpProtocolInfo": [
                {
                    "layerProtocol": "IP_OVER_ETHERNET",
                    "ipOverEthernet": {
                        "ipAddresses": [
                            {
                                "type": "IPV4",
                                "isDynamic": True
                            }
                        ]
                    }
                }
            ],
            "extLinkPortId": "res_id_VDU1_CP1_1",
            "associatedVnfcCpId": "VDU1_CP1-res_id_VDU1_1"
        },
        {
            "id": "cp-res_id_VDU1_CP1_2",
            "cpdId": "VDU1_CP1",
            "cpConfigId": "VDU1_CP1_1",
            "cpProtocolInfo": [
                {
                    "layerProtocol": "IP_OVER_ETHERNET",
                    "ipOverEthernet": {
                        "ipAddresses": [
                            {
                                "type": "IPV4",
                                "isDynamic": True
                            }
                        ]
                    }
                }
            ],
            "extLinkPortId": "res_id_VDU1_CP1_2",
            "associatedVnfcCpId": "VDU1_CP1-res_id_VDU1_2"
        },
        {
            "id": "cp-res_id_VDU1_CP2_1",
            "cpdId": "VDU1_CP2",
            "cpConfigId": "VDU1_CP2_1",
            "cpProtocolInfo": [
                {
                    "layerProtocol": "IP_OVER_ETHERNET",
                    "ipOverEthernet": {
                        "ipAddresses": [
                            {
                                "type": "IPV4",
                                "isDynamic": True,
                                "subnetId": "res_id_subnet_1"
                            }
                        ]
                    }
                }
            ],
            "extLinkPortId": "res_id_VDU1_CP2_1",
            "associatedVnfcCpId": "VDU1_CP2-res_id_VDU1_1"
        },
        {
            "id": "cp-res_id_VDU1_CP2_2",
            "cpdId": "VDU1_CP2",
            "cpConfigId": "VDU1_CP2_1",
            "cpProtocolInfo": [
                {
                    "layerProtocol": "IP_OVER_ETHERNET",
                    "ipOverEthernet": {
                        "ipAddresses": [
                            {
                                "type": "IPV4",
                                "isDynamic": True,
                                "subnetId": "res_id_subnet_1"
                            }
                        ]
                    }
                }
            ],
            "extLinkPortId": "res_id_VDU1_CP2_2",
            "associatedVnfcCpId": "VDU1_CP2-res_id_VDU1_2"
        },
        {
            "id": "cp-res_id_VDU2_CP1",
            "cpdId": "VDU2_CP1",
            "cpConfigId": "VDU2_CP1_1",
            "cpProtocolInfo": [
                {
                    "layerProtocol": "IP_OVER_ETHERNET",
                    "ipOverEthernet": {
                        "ipAddresses": [
                            {
                                "type": "IPV4",
                                "addresses": [
                                    "10.10.0.102"
                                ]
                            }
                        ]
                    }
                }
            ],
            "extLinkPortId": "res_id_VDU2_CP1",
            "associatedVnfcCpId": "VDU2_CP1-res_id_VDU2"
        }
    ],
    "extVirtualLinkInfo": [
        {
            "id": "id_ext_vl_1",
            "resourceHandle": {
                "resourceId": "res_id_ext_vl_1"
            },
            "extLinkPorts": [
                {
                    "id": "res_id_VDU1_CP1_1",
                    "resourceHandle": {
                        "vimConnectionId": "vim_id_1",
                        "resourceId": "res_id_VDU1_CP1_1",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "cp-res_id_VDU1_CP1_1"
                },
                {
                    "id": "res_id_VDU1_CP1_2",
                    "resourceHandle": {
                        "vimConnectionId": "vim_id_1",
                        "resourceId": "res_id_VDU1_CP1_2",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "cp-res_id_VDU1_CP1_2"
                },
                {
                    "id": "res_id_VDU2_CP1",
                    "resourceHandle": {
                        "vimConnectionId": "vim_id_1",
                        "resourceId": "res_id_VDU2_CP1",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "cp-res_id_VDU2_CP1"
                }
            ],
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
            "id": "id_ext_vl_2",
            "resourceHandle": {
                "resourceId": "res_id_id_ext_vl_2"
            },
            "extLinkPorts": [
                {
                    "id": "req-link_port_id_VDU2_CP2",
                    "resourceHandle": {
                        "resourceId": "res_id_VDU2_CP2",
                    },
                    "cpInstanceId": "cp-req-link_port_id_VDU2_CP2"
                },
                {
                    "id": "res_id_VDU1_CP2_1",
                    "resourceHandle": {
                        "vimConnectionId": "vim_id_1",
                        "resourceId": "res_id_VDU1_CP2_1",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "cp-res_id_VDU1_CP2_1"
                },
                {
                    "id": "res_id_VDU1_CP2_2",
                    "resourceHandle": {
                        "vimConnectionId": "vim_id_1",
                        "resourceId": "res_id_VDU1_CP2_2",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "cp-res_id_VDU1_CP2_2"
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
                                                "numDynamicAddresses": 1,
                                                "subnetId": "res_id_subnet_1"
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
                            "linkPortId": "link_port_id_VDU2_CP2"
                        }
                    }
                }
            ]
        }
    ],
    "extManagedVirtualLinkInfo": [
        {
            "id": "id_ext_mgd_1",
            "vnfVirtualLinkDescId": "internalVL1",
            "networkResource": {
                "resourceId": "res_id_internalVL1"
            },
            "vnfLinkPorts": [
                {
                    "id": "res_id_VDU1_CP3_1",
                    "resourceHandle": {
                        "vimConnectionId": "vim_id_1",
                        "resourceId": "res_id_VDU1_CP3_1",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "VDU1_CP3-res_id_VDU1_1",
                    "cpInstanceType": "VNFC_CP"
                },
                {
                    "id": "res_id_VDU1_CP3_2",
                    "resourceHandle": {
                        "vimConnectionId": "vim_id_1",
                        "resourceId": "res_id_VDU1_CP3_2",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "VDU1_CP3-res_id_VDU1_2",
                    "cpInstanceType": "VNFC_CP"
                },
                {
                    "id": "res_id_VDU2_CP3",
                    "resourceHandle": {
                        "vimConnectionId": "vim_id_1",
                        "resourceId": "res_id_VDU2_CP3",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "VDU2_CP3-res_id_VDU2",
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
                "vimConnectionId": "vim_id_1",
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
            "metadata": {
                "creation_time": "2021-12-10T01:03:49Z",
                "parent_stack_id": _stack_id_VDU1_scale,
                "parent_resource_name": "myet4efobvvp"
            }
        },
        {
            "id": "res_id_VDU1_1",
            "vduId": "VDU1",
            "computeResource": {
                "vimConnectionId": "vim_id_1",
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
            "metadata": {
                "creation_time": "2021-12-10T00:41:43Z",
                "parent_stack_id": _stack_id_VDU1_scale,
                "parent_resource_name": "bemybz4ugeso"
            }
        },
        {
            "id": "res_id_VDU2",
            "vduId": "VDU2",
            "computeResource": {
                "vimConnectionId": "vim_id_1",
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
                    # "vnfExtCpId" does not exist since it is specified by
                    # linkPortIds.
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
            "metadata": {
                "creation_time": "2021-12-10T00:40:46Z"
            }
        }
    ],
    "vnfVirtualLinkResourceInfo": [
        {
            "id": "res_id_internalVL2",
            "vnfVirtualLinkDescId": "internalVL2",
            "networkResource": {
                "vimConnectionId": "vim_id_1",
                "resourceId": "res_id_internalVL2",
                "vimLevelResourceType": "OS::Neutron::Net"
            },
            "vnfLinkPorts": [
                {
                    "id": "res_id_VDU1_CP4_1",
                    "resourceHandle": {
                        "vimConnectionId": "vim_id_1",
                        "resourceId": "res_id_VDU1_CP4_1",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "VDU1_CP4-res_id_VDU1_1",
                    "cpInstanceType": "VNFC_CP"
                },
                {
                    "id": "res_id_VDU1_CP4_2",
                    "resourceHandle": {
                        "vimConnectionId": "vim_id_1",
                        "resourceId": "res_id_VDU1_CP4_2",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "VDU1_CP4-res_id_VDU1_2",
                    "cpInstanceType": "VNFC_CP"
                },
                {
                    "id": "res_id_VDU2_CP4",
                    "resourceHandle": {
                        "vimConnectionId": "vim_id_1",
                        "resourceId": "res_id_VDU2_CP4",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "VDU2_CP4-res_id_VDU2",
                    "cpInstanceType": "VNFC_CP"
                }
            ]
        },
        {
            "id": "res_id_internalVL3",
            "vnfVirtualLinkDescId": "internalVL3",
            "networkResource": {
                "vimConnectionId": "vim_id_1",
                "resourceId": "res_id_internalVL3",
                "vimLevelResourceType": "OS::Neutron::Net"
            },
            "vnfLinkPorts": [
                {
                    "id": "res_id_VDU1_CP5_1",
                    "resourceHandle": {
                        "vimConnectionId": "vim_id_1",
                        "resourceId": "res_id_VDU1_CP5_1",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "VDU1_CP5-res_id_VDU1_1",
                    "cpInstanceType": "VNFC_CP"
                },
                {
                    "id": "res_id_VDU1_CP5_2",
                    "resourceHandle": {
                        "vimConnectionId": "vim_id_1",
                        "resourceId": "res_id_VDU1_CP5_2",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "VDU1_CP5-res_id_VDU1_2",
                    "cpInstanceType": "VNFC_CP"
                },
                {
                    "id": "res_id_VDU2_CP5",
                    "resourceHandle": {
                        "vimConnectionId": "vim_id_1",
                        "resourceId": "res_id_VDU2_CP5",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "VDU2_CP5-res_id_VDU2",
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
                "vimConnectionId": "vim_id_1",
                "resourceId": "res_id_VirtualStorage_1",
                "vimLevelResourceType": "OS::Cinder::Volume"
            }
        },
        {
            "id": "res_id_VirtualStorage_2",
            "virtualStorageDescId": "VirtualStorage",
            "storageResource": {
                "vimConnectionId": "vim_id_1",
                "resourceId": "res_id_VirtualStorage_2",
                "vimLevelResourceType": "OS::Cinder::Volume"
            }
        }
    ],
    "vnfcInfo": [
        {
            "id": "VDU1-res_id_VDU1_2",
            "vduId": "VDU1",
            "vnfcResourceInfoId": "res_id_VDU1_2",
            "vnfcState": "STARTED"
        },
        {
            "id": "VDU1-res_id_VDU1_1",
            "vduId": "VDU1",
            "vnfcResourceInfoId": "res_id_VDU1_1",
            "vnfcState": "STARTED"
        },
        {
            "id": "VDU2-res_id_VDU2",
            "vduId": "VDU2",
            "vnfcResourceInfoId": "res_id_VDU2",
            "vnfcState": "STARTED"
        }
    ]
}


class TestOpenstack(base.BaseTestCase):

    def setUp(self):
        super(TestOpenstack, self).setUp()
        objects.register_all()
        self.driver = openstack.Openstack()
        self.context = context.get_admin_context()

        cur_dir = os.path.dirname(__file__)
        sample_dir = os.path.join(cur_dir, "../..", "samples")

        self.vnfd_1 = vnfd_utils.Vnfd(SAMPLE_VNFD_ID)
        self.vnfd_1.init_from_csar_dir(os.path.join(sample_dir, "sample1"))

    def _check_inst_info(self, expected, result):
        # sort lists before compare with an expected result since
        # order of list items is unpredictable.
        # note that an expected_result is already sorted.
        def _get_key(obj):
            return obj['id']

        if "extCpInfo" in expected:
            self.assertIn("extCpInfo", result)
            result["extCpInfo"].sort(key=_get_key)
            # assume len(cpProtocolInfo) == 1
            self.assertEqual(expected["extCpInfo"], result["extCpInfo"])

        if "extVirtualLinkInfo" in expected:
            self.assertIn("extVirtualLinkInfo", result)
            for ext_vl in result["extVirtualLinkInfo"]:
                if "extLinkPorts" in ext_vl:
                    ext_vl["extLinkPorts"].sort(key=_get_key)
                # order of currentVnfExtCpData is same as order of
                # instantiateVnfRequest
            self.assertEqual(expected["extVirtualLinkInfo"],
                result["extVirtualLinkInfo"])

        if "extManagedVirtualLinkInfo" in expected:
            self.assertIn("extManagedVirtualLinkInfo", result)
            for ext_mgd in result["extManagedVirtualLinkInfo"]:
                if "vnfLinkPorts" in ext_mgd:
                    ext_mgd["vnfLinkPorts"].sort(key=_get_key)
            self.assertEqual(expected["extManagedVirtualLinkInfo"],
                result["extManagedVirtualLinkInfo"])

        # vnfcResourceInfo is sorted by creation_time (reverse)
        if "vnfcResourceInfo" in expected:
            self.assertIn("vnfcResourceInfo", result)
            for vnfc in result["vnfcResourceInfo"]:
                if "storageResourceIds" in vnfc:
                    vnfc["storageResourceIds"].sort()
                if "vnfcCpInfo" in vnfc:
                    vnfc["vnfcCpInfo"].sort(key=_get_key)
            self.assertEqual(expected["vnfcResourceInfo"],
                result["vnfcResourceInfo"])

        if "vnfVirtualLinkResourceInfo" in expected:
            self.assertIn("vnfVirtualLinkResourceInfo", result)
            result["vnfVirtualLinkResourceInfo"].sort(key=_get_key)
            for vl_info in result["vnfVirtualLinkResourceInfo"]:
                if "vnfLinkPorts" in vl_info:
                    vl_info["vnfLinkPorts"].sort(key=_get_key)
            self.assertEqual(expected["vnfVirtualLinkResourceInfo"],
                result["vnfVirtualLinkResourceInfo"])

        if "virtualStorageResourceInfo" in expected:
            self.assertIn("virtualStorageResourceInfo", result)
            result["virtualStorageResourceInfo"].sort(key=_get_key)
            self.assertEqual(expected["virtualStorageResourceInfo"],
                result["virtualStorageResourceInfo"])

        # order of vnfcInfo is same as vnfcResourceInfo
        if "vnfcInfo" in expected:
            self.assertIn("vnfcInfo", result)
            self.assertEqual(expected["vnfcInfo"], result["vnfcInfo"])

    def test_make_instantiated_vnf_info_new(self):
        # prepare
        req = objects.InstantiateVnfRequestV2.from_dict(
            _instantiate_req_example)
        inst = objects.VnfInstanceV2(
            vimConnectionInfo=req.vimConnectionInfo
        )
        grant_req = objects.GrantRequestV1(
            operation=fields.LcmOperationType.INSTANTIATE
        )
        grant = objects.GrantV1()

        # execute make_instantiated_vnf_info
        self.driver._make_instantiated_vnf_info(req, inst, grant_req, grant,
            self.vnfd_1, _heat_reses_example)

        # check
        result = inst.to_dict()["instantiatedVnfInfo"]
        self._check_inst_info(_expected_inst_info, result)

    def test_make_instantiated_vnf_info_update(self):
        # prepare
        req = None  # not used
        inst_info = objects.VnfInstanceV2_InstantiatedVnfInfo.from_dict(
            _expected_inst_info)
        vim_info = {
            "vim1": objects.VimConnectionInfo.from_dict(
                _vim_connection_info_example)
        }
        inst = objects.VnfInstanceV2(
            instantiatedVnfInfo=inst_info,
            vimConnectionInfo=vim_info
        )
        grant_req = objects.GrantRequestV1(
            operation=fields.LcmOperationType.SCALE
        )
        grant = objects.GrantV1()

        # execute make_instantiated_vnf_info
        self.driver._make_instantiated_vnf_info(req, inst, grant_req, grant,
            self.vnfd_1, _heat_reses_example)

        # check
        result = inst.to_dict()["instantiatedVnfInfo"]
        self._check_inst_info(_expected_inst_info, result)
