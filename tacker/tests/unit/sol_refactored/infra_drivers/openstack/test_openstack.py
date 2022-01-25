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

import copy
import os
import requests
import subprocess

from datetime import datetime
from oslo_utils import uuidutils
from unittest import mock

from tacker import context
from tacker.sol_refactored.common import vnfd_utils
from tacker.sol_refactored.infra_drivers.openstack import heat_utils
from tacker.sol_refactored.infra_drivers.openstack import openstack
from tacker.sol_refactored.nfvo import glance_utils
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

_vim_connection_info_for_change_vnfpkg = {
    "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_3",
    "vimId": uuidutils.generate_uuid(),
    "interfaceInfo": {"endpoint": "http://127.0.0.1/identity"},
    "accessInfo": {
        "username": "nfv_user",
        "region": "RegionOne",
        "password": "devstack",
        "project": "nfv",
        "projectDomain": "Default",
        "userDomain": "Default"
    }

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

# ChangeExtVnfConnectivityRequest example
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

_change_vnfpkg_example = {
    "vnfdId": uuidutils.generate_uuid(),
    "additionalParams": {
        "upgrade_type": "RollingUpdate",
        "lcm-operation-coordinate-old-vnf": "Scripts/coordinate_old_vnf.py",
        "lcm-operation-coordinate-old-vnf-class": "CoordinateOldVnf",
        "lcm-operation-coordinate-new-vnf": "Scripts/coordinate_new_vnf.py",
        "lcm-operation-coordinate-new-vnf-class": "CoordinateNewVnf",
        "vdu_params": [{
            "vdu_id": "VDU1",
            "old_vnfc_param": {
                "cp_name": "CP1",
                "username": "ubuntu",
                "password": "ubuntu"
            },
            "new_vnfc_param": {
                "cp_name": "CP1",
                "username": "ubuntu",
                "password": "ubuntu"
            },
        }]
    }
}

_change_vnfpkg_example_2 = {
    "vnfdId": uuidutils.generate_uuid(),
    "additionalParams": {
        "upgrade_type": "RollingUpdate",
        "lcm-operation-coordinate-old-vnf": "Scripts/coordinate_old_vnf.py",
        "lcm-operation-coordinate-old-vnf-class": "CoordinateOldVnf",
        "lcm-operation-coordinate-new-vnf": "Scripts/coordinate_new_vnf.py",
        "lcm-operation-coordinate-new-vnf-class": "CoordinateNewVnf",
        "vdu_params": [{
            "vdu_id": "VDU2",
            "old_vnfc_param": {
                "cp_name": "CP1",
                "username": "ubuntu",
                "password": "ubuntu"
            },
            "new_vnfc_param": {
                "cp_name": "CP1",
                "username": "ubuntu",
                "password": "ubuntu"
            },
        }]
    }
}

# heat resources examples
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

_heat_reses_example_base = [
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

_heat_reses_example_cps_before = [
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
    }
]

_heat_reses_example_cps_after = [
    {
        "creation_time": "2021-12-10T00:40:46Z",
        "resource_name": "VDU2_CP1",
        "physical_resource_id": "res_id_VDU2_CP1_modified",
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
        "creation_time": "2021-12-10T00:41:45Z",
        "resource_name": "VDU1_CP2",
        "physical_resource_id": "res_id_VDU1_CP2_1_modified",
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
        "creation_time": "2021-12-10T01:03:53Z",
        "resource_name": "VDU1_CP2",
        "physical_resource_id": "res_id_VDU1_CP2_2_modified",
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

# heat resources example for other than change_ext_conn
_heat_reses_example = (
    _heat_reses_example_base + _heat_reses_example_cps_before)

# heat resources example after executing change_ext_conn
_heat_reses_example_change_ext_conn = (
    _heat_reses_example_base + _heat_reses_example_cps_after)

# change vnfpkg before inst info
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
                "stack_id": "vnf-d8962b72-6dac-4eb5-a8c4-8c7a2abaefb7-"
                            "VDU1_scale_group-2zmsxtwtsj7n-"
                            "fkwryhyv6qbr-qoemdwxw7o5c/"
                            "d7aeba20-1b00-4bff-b050-6b42a262c84d",
                "parent_resource_name": "fkwryhyv6qbr"
            }
        },
        {
            "id": "res_id_VDU2_1",
            "vduId": "VDU2",
            "computeResource": {
                "vimConnectionId": "vim_id_1",
                "resourceId": "res_id_VDU2_1",
                "vimLevelResourceType": "OS::Nova::Server"
            },
            "storageResourceIds": [
                "res_id_VirtualStorage_2"
            ],
            "vnfcCpInfo": [
                {
                    "id": "VDU2_CP1-res_id_VDU2_1",
                    "cpdId": "VDU2_CP1",
                    "vnfExtCpId": "cp-res_id_VDU2_CP1_1"
                },
                {
                    "id": "VDU2_CP2-res_id_VDU2_1",
                    "cpdId": "VDU2_CP2",
                    "vnfExtCpId": "cp-res_id_VDU2_CP2_1"
                },
                {
                    "id": "VDU2_CP3-res_id_VDU2_1",
                    "cpdId": "VDU2_CP3",
                    "vnfLinkPortId": "res_id_VDU2_CP3_1"
                },
                {
                    "id": "VDU2_CP4-res_id_VDU2_1",
                    "cpdId": "VDU2_CP4",
                    "vnfLinkPortId": "res_id_VDU2_CP4_1"
                },
                {
                    "id": "VDU2_CP5-res_id_VDU2_1",
                    "cpdId": "VDU2_CP5",
                    "vnfLinkPortId": "res_id_VDU2_CP5_1"
                }
            ],
            "metadata": {
                "creation_time": "2021-12-10T00:41:43Z",
                "stack_id": 'vnf-d7aeba20-1b00-4bff-b050-6b42a262c84d/'
                            'd7aeba20-1b00-4bff-b050-6b42a262c84d'
            }
        },
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
    # "vnfcInfo": omitted
}

# expected results (other than change_ext_conn)
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
                "parent_resource_name": "myet4efobvvp",
                "stack_id": _stack_id_VDU1_2
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
                "parent_resource_name": "bemybz4ugeso",
                "stack_id": _stack_id_VDU1_1
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
                "creation_time": "2021-12-10T00:40:46Z",
                "stack_id": _stack_id
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
            },
            "metadata": {"stack_id": _stack_id_VDU1_1}
        },
        {
            "id": "res_id_VirtualStorage_2",
            "virtualStorageDescId": "VirtualStorage",
            "storageResource": {
                "vimConnectionId": "vim_id_1",
                "resourceId": "res_id_VirtualStorage_2",
                "vimLevelResourceType": "OS::Cinder::Volume"
            },
            "metadata": {"stack_id": _stack_id_VDU1_2}
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

_expected_inst_info_vnfc_updated = copy.copy(_expected_inst_info)
_expected_inst_info_vnfc_updated["vnfcInfo"] = [
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
        "vnfcState": "STARTED",
        "vnfcConfigurableProperties": {"prop1": "value1"}
    },
    {
        "id": "VDU2-res_id_VDU2",
        "vduId": "VDU2",
        "vnfcResourceInfoId": "res_id_VDU2",
        "vnfcState": "STARTED"
    }
]

# expected results for change_ext_conn
_expected_inst_info_change_ext_conn = {
    "flavourId": "simple",
    "vnfState": "STARTED",
    "extCpInfo": [
        {
            'id': 'cp-req-link_port_id_VDU2_CP2_modified',
            'cpdId': 'VDU2_CP2',
            'cpConfigId': 'VDU2_CP2_1',
            'extLinkPortId': 'req-link_port_id_VDU2_CP2_modified',
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
            "id": "cp-res_id_VDU1_CP2_1_modified",
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
                                "subnetId": "res_id_subnet_4"
                            }
                        ]
                    }
                }
            ],
            "extLinkPortId": "res_id_VDU1_CP2_1_modified",
            "associatedVnfcCpId": "VDU1_CP2-res_id_VDU1_1"
        },
        {
            "id": "cp-res_id_VDU1_CP2_2_modified",
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
                                "subnetId": "res_id_subnet_4"
                            }
                        ]
                    }
                }
            ],
            "extLinkPortId": "res_id_VDU1_CP2_2_modified",
            "associatedVnfcCpId": "VDU1_CP2-res_id_VDU1_2"
        },
        {
            "id": "cp-res_id_VDU2_CP1_modified",
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
                                    "20.10.0.102"
                                ]
                            }
                        ]
                    }
                }
            ],
            "extLinkPortId": "res_id_VDU2_CP1_modified",
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
                }
            ]
        },
        {
            "id": "id_ext_vl_3",
            "resourceHandle": {
                "resourceId": "res_id_ext_vl_3"
            },
            "extLinkPorts": [
                {
                    "id": "res_id_VDU2_CP1_modified",
                    "resourceHandle": {
                        "vimConnectionId": "vim_id_1",
                        "resourceId": "res_id_VDU2_CP1_modified",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "cp-res_id_VDU2_CP1_modified"
                }
            ],
            "currentVnfExtCpData": [
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
            "resourceHandle": {
                "resourceId": "res_id_id_ext_vl_4"
            },
            "extLinkPorts": [
                {
                    "id": "req-link_port_id_VDU2_CP2_modified",
                    "resourceHandle": {
                        "resourceId": "res_id_VDU2_CP2_modified",
                    },
                    "cpInstanceId": "cp-req-link_port_id_VDU2_CP2_modified"
                },
                {
                    "id": "res_id_VDU1_CP2_1_modified",
                    "resourceHandle": {
                        "vimConnectionId": "vim_id_1",
                        "resourceId": "res_id_VDU1_CP2_1_modified",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "cp-res_id_VDU1_CP2_1_modified"
                },
                {
                    "id": "res_id_VDU1_CP2_2_modified",
                    "resourceHandle": {
                        "vimConnectionId": "vim_id_1",
                        "resourceId": "res_id_VDU1_CP2_2_modified",
                        "vimLevelResourceType": "OS::Neutron::Port"
                    },
                    "cpInstanceId": "cp-res_id_VDU1_CP2_2_modified"
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
                    "vnfExtCpId": "cp-res_id_VDU1_CP2_2_modified"
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
                "parent_resource_name": "myet4efobvvp",
                "stack_id": _stack_id_VDU1_2
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
                    "vnfExtCpId": "cp-res_id_VDU1_CP2_1_modified"
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
                "parent_resource_name": "bemybz4ugeso",
                "stack_id": _stack_id_VDU1_1
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
                    "vnfExtCpId": "cp-res_id_VDU2_CP1_modified"
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
                "creation_time": "2021-12-10T00:40:46Z",
                "stack_id": _stack_id
            }
        }
    ],
    # other members are not changed from _expected_inst_info
    "extManagedVirtualLinkInfo":
        _expected_inst_info["extManagedVirtualLinkInfo"],
    "vnfVirtualLinkResourceInfo":
        _expected_inst_info["vnfVirtualLinkResourceInfo"],
    "virtualStorageResourceInfo":
        _expected_inst_info["virtualStorageResourceInfo"],
    "vnfcInfo": _expected_inst_info["vnfcInfo"]
}

mock_resource = {
    'resources': [{
        'updated_time': '2021-12-27T02:53:29Z',
        'creation_time': '2021-12-27T02:53:29Z',
        'logical_resource_id': 'VDU1',
        'resource_name': 'VDU1',
        'physical_resource_id': 'e79ebeaf-1b26-4ff9-9895-f4c78a8a39a6',
        'resource_status': 'CREATE_COMPLETE',
        'resource_status_reason': 'state changed',
        'resource_type': 'OS::Nova::Server',
        'required_by': [],
        'parent_resource': 'fkwryhyv6qbr'
    }, {
        'updated_time': '2021-12-27T03:16:02Z',
        'creation_time': '2021-12-27T02:53:27Z',
        'logical_resource_id': 'fkwryhyv6qbr',
        'resource_name': 'fkwryhyv6qbr',
        'physical_resource_id': 'd7aeba20-1b00-4bff-b050-6b42a262c84d',
        'resource_status': 'UPDATE_COMPLETE',
        'resource_status_reason': 'state changed',
        'resource_type': 'VDU1.yaml',
        'required_by': [],
        'parent_resource': 'VDU1_scale_group'
    }, {
        'updated_time': '2021-12-27T03:16:01Z',
        'creation_time': '2021-12-27T02:53:20Z',
        'logical_resource_id': 'VDU1_scale_group',
        'resource_name': 'VDU1_scale_group',
        'physical_resource_id': '53ba8388-287d-411e-93c9-bd27cec8d0ec',
        'resource_status': 'UPDATE_COMPLETE',
        'resource_status_reason': 'state changed',
        'resource_type': 'OS::Heat::AutoScalingGroup',
        'required_by': ['VDU1_scale_in', 'VDU1_scale_out']
    }]
}

mock_resource_template = {
    'heat_template_version': '2015-04-30', 'resources': {
        'fkwryhyv6qbr': {'type': 'VDU1.yaml', 'properties': {
            'flavor': 'm1.tiny',
            'image': 'cirros-0.5.2-x86_64-disk',
            'net1': '9b243768-1193-414b-b7c5-b56dfa765da4',
            'net2': '094e43b4-056c-49ce-8203-c7cd955003a6',
            'net3': '31451e60-ef7b-42f2-a4c7-2ca67d6c5caf',
            'net4': 'dfc1c440-50b0-442f-bcd4-bd090b3272a5',
            'net5': '2b2ecd2d-1f53-4b29-9c9d-7855c2fee7e3',
            'subnet': '1368ba79-5710-4ef6-b481-829fa22711c7'}}},
    'outputs': {'refs_map': {'value': {'fkwryhyv6qbr': {
        'get_resource': 'fkwryhyv6qbr'}}}}}

mock_resource_template_2 = {
    'heat_template_version': '2015-04-30',
    'description': 'Simple Base HOT for Sample VNF',
    'parameters': {'nfv': {'type': 'json'}},
    'resources': {'VDU2': {
        'type': 'OS::Nova::Server',
        'properties': {
            'flavor': {'get_param': [
                'nfv', 'VDU', 'VDU2', 'computeFlavourId']},
            'image': {'get_param': [
                'nfv', 'VDU', 'VDU2', 'vcImageId']},
            'networks': [
                {'port': {'get_resource': 'VDU2_CP1'}},
                {'port': {'get_resource': 'VDU2_CP2'}},
                {'port': {'get_resource': 'VDU2_CP3'}},
                {'port': {'get_resource': 'VDU2_CP4'}},
                {'port': {'get_resource': 'VDU2_CP5'}}],
            'scheduler_hints': {
                'group': {
                    'get_resource': 'nfvi_node_affinity'}}}}
    }
}

mock_resource_template_3 = {
    'heat_template_version': '2015-04-30', 'resources': {'VDU2': {
        'type': 'VDU2.yaml',
        'properties': {'flavor': 'm1.tiny',
                       'image': 'cirros-0.5.2-x86_64-disk',
                       'net1': '9b243768-1193-414b-b7c5-b56dfa765da4',
                       'net2': '094e43b4-056c-49ce-8203-c7cd955003a6',
                       'net3': '31451e60-ef7b-42f2-a4c7-2ca67d6c5caf',
                       'net4': 'dfc1c440-50b0-442f-bcd4-bd090b3272a5',
                       'net5': '2b2ecd2d-1f53-4b29-9c9d-7855c2fee7e3',
                       'subnet': '1368ba79-5710-4ef6-b481-829fa22711c7',
                       'block_device_mapping_v2': ''}}},
    'outputs': {'refs_map': {'value': {'VDU2': {'get_resource': 'VDU2'}}}}}

mock_resource_list = {
    'resources': [{
        'updated_time': '2021-12-27T03:16:02Z',
        'creation_time': '2021-12-27T02:53:27Z',
        'logical_resource_id': 'fkwryhyv6qbr',
        'resource_name': 'fkwryhyv6qbr',
        'physical_resource_id': 'd7aeba20-1b00-4bff-b050-6b42a262c84d',
        'resource_status': 'UPDATE_COMPLETE',
        'resource_status_reason': 'state changed',
        'resource_type': 'VDU1.yaml',
        'links': [{
            'href': 'http://192.168.10.115/heat-api/v1/'
                    '11ee4693b37c4b7995ab2ae331e9adf3/stacks/'
                    'vnf-d7aeba20-1b00-4bff-b050-6b42a262c84d/'
                    'd7aeba20-1b00-4bff-b050-6b42a262c84d/resources/'
                    'fkwryhyv6qbr',
            'rel': 'self'
        }, {
            'href': 'http://192.168.10.115/heat-api/v1/'
                    '11ee4693b37c4b7995ab2ae331e9adf3/stacks/'
                    'vnf-d7aeba20-1b00-4bff-b050-6b42a262c84d/'
                    'd7aeba20-1b00-4bff-b050-6b42a262c84d',
            'rel': 'stack'
        }, {
            'href': 'http://192.168.10.115/heat-api/v1/'
                    '11ee4693b37c4b7995ab2ae331e9adf3/stacks/'
                    'vnf-d8962b72-6dac-4eb5-a8c4-8c7a2abaefb7-'
                    'VDU1_scale_group-2zmsxtwtsj7n-fkwryhyv6qbr-qoemdwxw7o5c/'
                    'd7aeba20-1b00-4bff-b050-6b42a262c84d',
            'rel': 'nested'
        }],
        'required_by': [],
        'parent_resource': 'VDU1_scale_group'
    }
    ]
}

mock_resource_list_2 = {
    'resources': [
        {
            'updated_time': '2021-12-27T02:53:29Z',
            'creation_time': '2021-12-27T02:53:29Z',
            'logical_resource_id': 'VDU1',
            'resource_name': 'VDU1',
            'physical_resource_id': 'e79ebeaf-1b26-4ff9-9895-f4c78a8a39a6',
            'resource_status': 'CREATE_COMPLETE',
            'resource_status_reason': 'state changed',
            'resource_type': 'OS::Nova::Server',
            'links': [{
                'href': 'http://192.168.10.115/heat-api/v1/'
                        '11ee4693b37c4b7995ab2ae331e9adf3/stacks/'
                        'vnf-d8962b72-6dac-4eb5-a8c4-8c7a2abaefb7-'
                        'VDU1_scale_group-2zmsxtwtsj7n-fkwryhyv6qbr-'
                        'qoemdwxw7o5c/d7aeba20-1b00-4bff-b050-6b42a262c84d'
                        '/resources/VDU1',
                'rel': 'self'
            }, {
                'href': 'http://192.168.10.115/heat-api/v1/'
                        '11ee4693b37c4b7995ab2ae331e9adf3/stacks/'
                        'vnf-d8962b72-6dac-4eb5-a8c4-8c7a2abaefb7-'
                        'VDU1_scale_group-2zmsxtwtsj7n-fkwryhyv6qbr-'
                        'qoemdwxw7o5c/d7aeba20-1b00-4bff-b050-6b42a262c84d',
                'rel': 'stack'
            }],

            'required_by': [],
            'parent_resource': 'fkwryhyv6qbr'
        }, {
            'updated_time': '2021-12-27T02:53:29Z',
            'creation_time': '2021-12-27T02:53:29Z',
            'logical_resource_id': 'VDU1_CP4',
            'resource_name': 'VDU1_CP4',
            'physical_resource_id': 'c625b32c-5b2e-4366-824e-0921f4efd954',
            'resource_status': 'CREATE_COMPLETE',
            'resource_status_reason': 'state changed',
            'resource_type': 'OS::Neutron::Port',
            'required_by': ['VDU1'],
            'parent_resource': 'fkwryhyv6qbr'
        }, {
            'updated_time': '2021-12-27T02:53:29Z',
            'creation_time': '2021-12-27T02:53:29Z',
            'logical_resource_id': 'VDU1_CP1',
            'resource_name': 'VDU1_CP1',
            'physical_resource_id': 'd13bab44-a728-4a3d-9c85-b70d77b5c7f4',
            'resource_status': 'CREATE_COMPLETE',
            'resource_status_reason': 'state changed',
            'resource_type': 'OS::Neutron::Port',
            'required_by': ['VDU1'],
            'parent_resource': 'fkwryhyv6qbr'
        }, {
            'updated_time': '2021-12-27T02:53:29Z',
            'creation_time': '2021-12-27T02:53:29Z',
            'logical_resource_id': 'VDU1_CP3',
            'resource_name': 'VDU1_CP3',
            'physical_resource_id': 'a231fd59-42e3-4636-a93d-695976ce03ef',
            'resource_status': 'CREATE_COMPLETE',
            'resource_status_reason': 'state changed',
            'resource_type': 'OS::Neutron::Port',
            'required_by': ['VDU1'],
            'parent_resource': 'fkwryhyv6qbr'
        }, {
            'updated_time': '2021-12-27T02:53:29Z',
            'creation_time': '2021-12-27T02:53:29Z',
            'logical_resource_id': 'VDU1_CP5',
            'resource_name': 'VDU1_CP5',
            'physical_resource_id': '8703f963-2e00-4931-8bce-ddbcaf1205e4',
            'resource_status': 'CREATE_COMPLETE',
            'resource_status_reason': 'state changed',
            'resource_type': 'OS::Neutron::Port',
            'required_by': ['VDU1'],
            'parent_resource': 'fkwryhyv6qbr'
        }, {
            'updated_time': '2021-12-27T02:53:29Z',
            'creation_time': '2021-12-27T02:53:29Z',
            'logical_resource_id': 'VirtualStorage',
            'resource_name': 'VirtualStorage',
            'physical_resource_id': '29809bc8-4a3d-412e-b6e2-5122995faccc',
            'resource_status': 'CREATE_COMPLETE',
            'resource_status_reason': 'state changed',
            'resource_type': 'OS::Cinder::Volume',
            'required_by': ['VDU1'],
            'parent_resource': 'fkwryhyv6qbr'
        }, {
            'updated_time': '2021-12-27T02:53:29Z',
            'creation_time': '2021-12-27T02:53:29Z',
            'logical_resource_id': 'VDU1_CP2',
            'resource_name': 'VDU1_CP2',
            'physical_resource_id': '963ba654-e3f1-4b78-8187-756dbd043916',
            'resource_status': 'CREATE_COMPLETE',
            'resource_status_reason': 'state changed',
            'resource_type': 'OS::Neutron::Port',
            'required_by': ['VDU1'],
            'parent_resource': 'fkwryhyv6qbr'
        }
    ]
}


mock_resource_list_3 = {
    'resources': [
        {
            'updated_time': '2021-12-27T02:53:29Z',
            'creation_time': '2021-12-27T02:53:29Z',
            'logical_resource_id': 'VDU2',
            'resource_name': 'VDU2',
            'physical_resource_id': 'res_id_VDU2_1',
            'resource_status': 'CREATE_COMPLETE',
            'resource_status_reason': 'state changed',
            'resource_type': 'OS::Nova::Server',
            'links': [{
                'href': 'http://192.168.10.115/heat-api/v1/'
                        '11ee4693b37c4b7995ab2ae331e9adf3/stacks/'
                        'vnf-d8962b72-6dac-4eb5-a8c4-8c7a2abaefb7/'
                        'ddea2e52-532a-491c-b8fc-9c759e35fd72/resources/VDU2',
                'rel': 'self'
            }, {
                'href': 'http://192.168.10.115/heat-api/v1/'
                        '11ee4693b37c4b7995ab2ae331e9adf3/stacks/'
                        'vnf-d8962b72-6dac-4eb5-a8c4-8c7a2abaefb7/'
                        'ddea2e52-532a-491c-b8fc-9c759e35fd72',
                'rel': 'stack'
            }],
            'required_by': []
        }, {
            'updated_time': '2021-12-27T02:53:29Z',
            'creation_time': '2021-12-27T02:53:29Z',
            'logical_resource_id': 'VDU2_CP4',
            'resource_name': 'VDU2_CP4',
            'physical_resource_id': 'c625b32c-5b2e-4366-824e-0921f4efd954',
            'resource_status': 'CREATE_COMPLETE',
            'resource_status_reason': 'state changed',
            'resource_type': 'OS::Neutron::Port',
            'links': [{
                'href': 'http://192.168.10.115/heat-api/v1/'
                        '11ee4693b37c4b7995ab2ae331e9adf3/stacks/'
                        'vnf-d8962b72-6dac-4eb5-a8c4-8c7a2abaefb7/'
                        'ddea2e52-532a-491c-b8fc-9c759e35fd72/resources/'
                        'VDU2_CP4',
                'rel': 'self'
            }, {
                'href': 'http://192.168.10.115/heat-api/v1/'
                        '11ee4693b37c4b7995ab2ae331e9adf3/stacks/'
                        'vnf-d8962b72-6dac-4eb5-a8c4-8c7a2abaefb7/'
                        'ddea2e52-532a-491c-b8fc-9c759e35fd72',
                'rel': 'stack'
            }],
            'required_by': ['VDU2']
        }, {
            'updated_time': '2021-12-27T02:53:29Z',
            'creation_time': '2021-12-27T02:53:29Z',
            'logical_resource_id': 'VDU2_CP1',
            'resource_name': 'VDU2_CP1',
            'physical_resource_id': 'd13bab44-a728-4a3d-9c85-b70d77b5c7f4',
            'resource_status': 'CREATE_COMPLETE',
            'resource_status_reason': 'state changed',
            'resource_type': 'OS::Neutron::Port',
            'links': [{
                'href': 'http://192.168.10.115/heat-api/v1/'
                        '11ee4693b37c4b7995ab2ae331e9adf3/stacks/'
                        'vnf-d8962b72-6dac-4eb5-a8c4-8c7a2abaefb7/'
                        'ddea2e52-532a-491c-b8fc-9c759e35fd72/resources/'
                        'VDU2_CP1',
                'rel': 'self'
            }, {
                'href': 'http://192.168.10.115/heat-api/v1/'
                        '11ee4693b37c4b7995ab2ae331e9adf3/stacks/'
                        'vnf-d8962b72-6dac-4eb5-a8c4-8c7a2abaefb7/'
                        'ddea2e52-532a-491c-b8fc-9c759e35fd72',
                'rel': 'stack'
            }],
            'required_by': ['VDU2']
        }, {
            'updated_time': '2021-12-27T02:53:29Z',
            'creation_time': '2021-12-27T02:53:29Z',
            'logical_resource_id': 'VDU2_CP3',
            'resource_name': 'VDU2_CP3',
            'physical_resource_id': 'a231fd59-42e3-4636-a93d-695976ce03ef',
            'resource_status': 'CREATE_COMPLETE',
            'resource_status_reason': 'state changed',
            'resource_type': 'OS::Neutron::Port',
            'links': [{
                'href': 'http://192.168.10.115/heat-api/v1/'
                        '11ee4693b37c4b7995ab2ae331e9adf3/stacks/'
                        'vnf-d8962b72-6dac-4eb5-a8c4-8c7a2abaefb7/'
                        'ddea2e52-532a-491c-b8fc-9c759e35fd72/resources/'
                        'VDU2_CP3',
                'rel': 'self'
            }, {
                'href': 'http://192.168.10.115/heat-api/v1/'
                        '11ee4693b37c4b7995ab2ae331e9adf3/stacks/'
                        'vnf-d8962b72-6dac-4eb5-a8c4-8c7a2abaefb7/'
                        'ddea2e52-532a-491c-b8fc-9c759e35fd72',
                'rel': 'stack'
            }],

            'required_by': ['VDU2']
        }, {
            'updated_time': '2021-12-27T02:53:29Z',
            'creation_time': '2021-12-27T02:53:29Z',
            'logical_resource_id': 'VDU2_CP5',
            'resource_name': 'VDU2_CP5',
            'physical_resource_id': '8703f963-2e00-4931-8bce-ddbcaf1205e4',
            'resource_status': 'CREATE_COMPLETE',
            'resource_status_reason': 'state changed',
            'resource_type': 'OS::Neutron::Port',
            'links': [{
                'href': 'http://192.168.10.115/heat-api/v1/'
                        '11ee4693b37c4b7995ab2ae331e9adf3/stacks/'
                        'vnf-d8962b72-6dac-4eb5-a8c4-8c7a2abaefb7/'
                        'ddea2e52-532a-491c-b8fc-9c759e35fd72/resources/'
                        'VDU2_CP5',
                'rel': 'self'
            }, {
                'href': 'http://192.168.10.115/heat-api/v1/'
                        '11ee4693b37c4b7995ab2ae331e9adf3/stacks/'
                        'vnf-d8962b72-6dac-4eb5-a8c4-8c7a2abaefb7/'
                        'ddea2e52-532a-491c-b8fc-9c759e35fd72',
                'rel': 'stack'
            }],
            'required_by': ['VDU2']
        }, {
            'updated_time': '2021-12-27T02:53:29Z',
            'creation_time': '2021-12-27T02:53:29Z',
            'logical_resource_id': 'VDU2_CP2',
            'resource_name': 'VDU2_CP2',
            'physical_resource_id': '963ba654-e3f1-4b78-8187-756dbd043916',
            'resource_status': 'CREATE_COMPLETE',
            'resource_status_reason': 'state changed',
            'resource_type': 'OS::Neutron::Port',
            'links': [{
                'href': 'http://192.168.10.115/heat-api/v1/'
                        '11ee4693b37c4b7995ab2ae331e9adf3/stacks/'
                        'vnf-d8962b72-6dac-4eb5-a8c4-8c7a2abaefb7/'
                        'ddea2e52-532a-491c-b8fc-9c759e35fd72/resources/'
                        'VDU2_CP2',
                'rel': 'self'
            }, {
                'href': 'http://192.168.10.115/heat-api/v1/'
                        '11ee4693b37c4b7995ab2ae331e9adf3/stacks/'
                        'vnf-d8962b72-6dac-4eb5-a8c4-8c7a2abaefb7/'
                        'ddea2e52-532a-491c-b8fc-9c759e35fd72',
                'rel': 'stack'
            }],
            'required_by': ['VDU2']
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
            result["extVirtualLinkInfo"].sort(key=_get_key)
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
        req = objects.InstantiateVnfRequest.from_dict(
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
            _expected_inst_info_vnfc_updated)
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
        self._check_inst_info(_expected_inst_info_vnfc_updated, result)

    def test_make_instantiated_vnf_info_change_ext_conn(self):
        # prepare
        req = objects.ChangeExtVnfConnectivityRequest.from_dict(
            _change_ext_conn_req_example)
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
            operation=fields.LcmOperationType.CHANGE_EXT_CONN
        )
        grant = objects.GrantV1()

        # execute make_instantiated_vnf_info
        self.driver._make_instantiated_vnf_info(req, inst, grant_req, grant,
            self.vnfd_1, _heat_reses_example_change_ext_conn)

        # check
        result = inst.to_dict()["instantiatedVnfInfo"]
        self._check_inst_info(_expected_inst_info_change_ext_conn, result)

    @mock.patch.object(heat_utils.HeatClient, 'get_parameters')
    @mock.patch.object(subprocess, 'run')
    @mock.patch.object(glance_utils.GlanceClient, 'get_image')
    @mock.patch.object(heat_utils.HeatClient, 'update_stack')
    @mock.patch.object(heat_utils.HeatClient, 'get_resource_list')
    @mock.patch.object(heat_utils.HeatClient, 'get_template')
    @mock.patch.object(heat_utils.HeatClient, 'get_resources')
    @mock.patch.object(heat_utils.HeatClient, 'get_resource_info')
    @mock.patch.object(heat_utils.HeatClient, 'get_stack_resource')
    def test_change_vnfpkg_404(
            self, mocked_get_stack_resource, mocked_get_resource_info,
            mocked_get_resources, mocked_get_template,
            mocked_get_resource_list, mocked_update_stack,
            mocked_get_image, mocked_run, mocked_get_parameters):
        # prepare
        req = objects.ChangeCurrentVnfPkgRequest.from_dict(
            _change_vnfpkg_example)
        inst_info = objects.VnfInstanceV2_InstantiatedVnfInfo.from_dict(
            _inst_info_example)
        vim_info = {
            "vim1": objects.VimConnectionInfo.from_dict(
                _vim_connection_info_for_change_vnfpkg)
        }
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
        inst.vimConnectionInfo = vim_info
        inst.instantiatedVnfInfo = inst_info
        grant_req = objects.GrantRequestV1(
            operation=fields.LcmOperationType.CHANGE_VNFPKG
        )
        grant = objects.GrantV1()
        stack_body = {'stack': {'id': uuidutils.generate_uuid(),
                                'name': 'test'}}
        stack_body_2 = {'stack': {
            'stack_name':
                'vnf-d8962b72-6dac-4eb5-a8c4-8c7a2abaefb7-VDU1_scale_group'}}
        mocked_get_stack_resource.side_effect = [stack_body, stack_body_2]

        body_2 = {"attributes": {"floating_ip_address": "192.168.0.1"}}
        body_3 = {"attributes": {
            "image": {"id": "image-1.0.0-x86_64-disk"},
            "flavor": {"original_name": "m1.tiny"}
        }
        }
        mocked_get_resource_info.side_effect = [None,
                                                body_2, body_3]
        mocked_get_resources.side_effect = [mock_resource['resources'],
                                            _heat_reses_example]
        mocked_get_template.return_value = mock_resource_template
        mocked_get_resource_list.side_effect = [mock_resource_list,
                                                mock_resource_list_2]
        mocked_update_stack.return_value = mock.Mock()
        resp_image = requests.Response()
        resp_image.name = "image-1.0.0-x86_64-disk"
        mocked_get_image.return_value = resp_image
        out = requests.Response()
        out.returncode = 0
        mocked_run.return_value = out
        parameter = {
            'nfv': '{"VDU":{"VDU1":{"vcImageId":""},'
                   '"VDU2":{"vcImageId":""},'
                   '"VirtualStorage":{"vcImageId":""}}}'
        }
        mocked_get_parameters.return_value = parameter
        # execute change_vnfpkg
        self.driver.change_vnfpkg(req, inst, grant_req, grant,
                                  self.vnfd_1)

        # check
        for vnfc_res in inst.instantiatedVnfInfo.vnfcResourceInfo:
            if vnfc_res.vduId == "VDU1":
                self.assertEqual(vnfc_res.id,
                                'e79ebeaf-1b26-4ff9-9895-f4c78a8a39a6')
                self.assertEqual(vnfc_res.computeResource.resourceId,
                                 'e79ebeaf-1b26-4ff9-9895-f4c78a8a39a6')
                self.assertIn('current_vnfd_id', vnfc_res.metadata)

    @mock.patch.object(heat_utils.HeatClient, 'get_resources')
    @mock.patch.object(subprocess, 'run')
    @mock.patch.object(glance_utils.GlanceClient, 'get_image')
    @mock.patch.object(heat_utils.HeatClient, 'get_resource_list')
    @mock.patch.object(heat_utils.HeatClient, 'update_stack')
    @mock.patch.object(heat_utils.HeatClient, 'get_parameters')
    @mock.patch.object(heat_utils.HeatClient, 'get_template')
    @mock.patch.object(heat_utils.HeatClient, 'get_resource_info')
    @mock.patch.object(heat_utils.HeatClient, 'get_stack_resource')
    def test_change_vnfpkg_200(
            self, mocked_get_stack_resource, mocked_get_resource_info,
            mocked_get_template, mocked_get_parameters,
            mocked_update_stack, mocked_get_resource_list, mocked_get_image,
            mocked_run, mocked_get_resources):
        # prepare
        req = objects.ChangeCurrentVnfPkgRequest.from_dict(
            _change_vnfpkg_example_2)
        inst_info = objects.VnfInstanceV2_InstantiatedVnfInfo.from_dict(
            _inst_info_example)
        vim_info = {
            "vim1": objects.VimConnectionInfo.from_dict(
                _vim_connection_info_for_change_vnfpkg)
        }
        inst = objects.VnfInstanceV2(
            # required fields
            id="d7aeba20-1b00-4bff-b050-6b42a262c84d",
            vnfdId=SAMPLE_VNFD_ID,
            vnfProvider='provider',
            vnfProductName='product name',
            vnfSoftwareVersion='software version',
            vnfdVersion='vnfd version',
            instantiationState='INSTANTIATED'
        )
        inst.vimConnectionInfo = vim_info
        inst.instantiatedVnfInfo = inst_info
        grant_req = objects.GrantRequestV1(
            operation=fields.LcmOperationType.CHANGE_VNFPKG
        )
        grant = objects.GrantV1()
        stack_body = {'stack': {'id': "d7aeba20-1b00-4bff-b050-6b42a262c84d",
                                'name': 'test'}}
        stack_body_2 = {'stack': {
            'stack_name':
                'vnf-d8962b72-6dac-4eb5-a8c4-8c7a2abaefb7-VDU1_scale_group'}}
        mocked_get_stack_resource.side_effect = [stack_body, stack_body_2]

        body = {"resource": "resource"}
        body_2 = {"attributes": {"floating_ip_address": "192.168.0.1"}}
        body_3 = {"attributes": {
            "image": {"id": "image-1.0.0-x86_64-disk"},
            "flavor": {"original_name": "m1.tiny"}
        }
        }
        mocked_get_resource_info.side_effect = [body['resource'], body_2,
                                                body_3]
        mocked_get_resources.side_effect = [mock_resource['resources'],
                                            _heat_reses_example]
        mocked_get_template.return_value = mock_resource_template_2
        mocked_get_resource_list.return_value = mock_resource_list_3
        mocked_update_stack.return_value = mock.Mock()
        resp_image = requests.Response()
        resp_image.name = "image-1.0.0-x86_64-disk"
        mocked_get_image.return_value = resp_image
        out = requests.Response()
        out.returncode = 0
        mocked_run.return_value = out
        parameter = {
            'nfv': '{"VDU":{"VDU1":{"vcImageId":""},'
                   '"VDU2":{"vcImageId":""},'
                   '"VirtualStorage":{"vcImageId":""}}}'
        }
        mocked_get_parameters.return_value = parameter
        # execute change_vnfpkg
        self.driver.change_vnfpkg(req, inst, grant_req, grant,
                                  self.vnfd_1)

        # check
        for vnfc_res in inst.instantiatedVnfInfo.vnfcResourceInfo:
            if vnfc_res.vduId == "VDU2":
                self.assertEqual(vnfc_res.id,
                                 'res_id_VDU2_1')
                self.assertEqual(vnfc_res.computeResource.resourceId,
                                 'res_id_VDU2_1')
                self.assertIn('current_vnfd_id', vnfc_res.metadata)

    @mock.patch.object(heat_utils.HeatClient, 'get_parameters')
    @mock.patch.object(subprocess, 'run')
    @mock.patch.object(glance_utils.GlanceClient, 'get_image')
    @mock.patch.object(heat_utils.HeatClient, 'get_resource_info')
    @mock.patch.object(heat_utils.HeatClient, 'get_resource_list')
    @mock.patch.object(heat_utils.HeatClient, 'update_stack')
    @mock.patch.object(heat_utils.HeatClient, 'get_template')
    @mock.patch.object(heat_utils.HeatClient, 'get_resources')
    @mock.patch.object(heat_utils.HeatClient, 'get_stack_resource')
    def test_change_vnfpkg_rollback(
            self, mocked_get_stack_resource, mocked_get_resources,
            mocked_get_template, mocked_update_stack,
            mocked_get_resource_list, mocked_get_resource_info,
            mocked_get_image, mocked_run, mocked_get_parameters):
        req = objects.ChangeCurrentVnfPkgRequest.from_dict(
            _change_vnfpkg_example)
        inst_info = objects.VnfInstanceV2_InstantiatedVnfInfo.from_dict(
            _inst_info_example)
        vim_info = {
            "vim1": objects.VimConnectionInfo.from_dict(
                _vim_connection_info_for_change_vnfpkg)
        }
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
        inst.vimConnectionInfo = vim_info
        inst.instantiatedVnfInfo = inst_info
        grant_req = objects.GrantRequestV1(
            operation=fields.LcmOperationType.CHANGE_VNFPKG
        )
        grant = objects.GrantV1()

        affected_vnfcs = objects.AffectedVnfcV2(
            id=uuidutils.generate_uuid(),
            vduId='VDU1',
            vnfdId=SAMPLE_VNFD_ID,
            changeType='ADDED',
            metadata={
                "creation_time": "2021-12-10T01:03:49Z",
                "stack_id": "vnf-d8962b72-6dac-4eb5-a8c4-8c7a2abaefb7-"
                            "VDU1_scale_group-2zmsxtwtsj7n-"
                            "fkwryhyv6qbr-qoemdwxw7o5c/"
                            "d7aeba20-1b00-4bff-b050-6b42a262c84d",
                "parent_resource_name": "fkwryhyv6qbr"
            }
        )
        resource_change = objects.VnfLcmOpOccV2_ResourceChanges(
            affectedVnfcs=[affected_vnfcs]
        )

        lcmocc = objects.VnfLcmOpOccV2(
            # required fields
            id=uuidutils.generate_uuid(),
            operationState=fields.LcmOperationStateType.FAILED_TEMP,
            stateEnteredTime=datetime.utcnow(),
            startTime=datetime.utcnow(),
            vnfInstanceId=inst.id,
            operation=fields.LcmOperationType.CHANGE_VNFPKG,
            resourceChanges=resource_change,
            isAutomaticInvocation=False,
            isCancelPending=False,
            operationParams=req)

        stack_body = {'stack': {'id': uuidutils.generate_uuid(),
                                'name': 'test'}}
        stack_body_2 = {'stack': {
            'stack_name':
                'vnf-d8962b72-6dac-4eb5-a8c4-8c7a2abaefb7-VDU1_scale_group'}}
        mocked_get_stack_resource.side_effect = [stack_body, stack_body_2]

        body = {"attributes": {"floating_ip_address": "192.168.0.1"}}
        body_2 = {"attributes": {
            "image": {"id": "image-1.0.0-x86_64-disk"},
            "flavor": {"original_name": "m1.tiny"}
        }
        }
        mocked_get_resource_info.side_effect = [body, body_2]
        mocked_get_resources.side_effect = [mock_resource['resources'],
                                            _heat_reses_example]
        mocked_get_template.return_value = mock_resource_template
        mocked_get_resource_list.return_value = mock_resource_list_2
        mocked_update_stack.return_value = mock.Mock()
        resp_image = requests.Response()
        resp_image.name = "image-1.0.0-x86_64-disk"
        mocked_get_image.return_value = resp_image
        out = requests.Response()
        out.returncode = 0
        mocked_run.return_value = out
        parameter = {
            'nfv': '{"VDU":{"VDU1":{"vcImageId":""},'
                   '"VDU2":{"vcImageId":""},'
                   '"VirtualStorage":{"vcImageId":""}}}'
        }
        mocked_get_parameters.return_value = parameter
        self.driver.change_vnfpkg_rollback(req, inst, grant_req, grant,
                                  self.vnfd_1, lcmocc)
        # check
        for vnfc_res in inst.instantiatedVnfInfo.vnfcResourceInfo:
            if vnfc_res.vduId == "VDU1":
                self.assertEqual(vnfc_res.id,
                                 'e79ebeaf-1b26-4ff9-9895-f4c78a8a39a6')
                self.assertEqual(vnfc_res.computeResource.resourceId,
                                 'e79ebeaf-1b26-4ff9-9895-f4c78a8a39a6')
                self.assertIn('current_vnfd_id', vnfc_res.metadata)

    @mock.patch.object(heat_utils.HeatClient, 'get_resources')
    @mock.patch.object(subprocess, 'run')
    @mock.patch.object(glance_utils.GlanceClient, 'get_image')
    @mock.patch.object(heat_utils.HeatClient, 'get_resource_info')
    @mock.patch.object(heat_utils.HeatClient, 'get_resource_list')
    @mock.patch.object(heat_utils.HeatClient, 'update_stack')
    @mock.patch.object(heat_utils.HeatClient, 'get_parameters')
    @mock.patch.object(heat_utils.HeatClient, 'get_template')
    @mock.patch.object(heat_utils.HeatClient, 'get_stack_resource')
    def test_change_vnfpkg_rollback_same(
            self, mocked_get_stack_resource, mocked_get_template,
            mocked_get_parameters, mocked_update_stack,
            mocked_get_resource_list, mocked_get_resource_info,
            mocked_get_image, mocked_run, mocked_get_resources):
        req = objects.ChangeCurrentVnfPkgRequest.from_dict(
            _change_vnfpkg_example_2)
        inst_info = objects.VnfInstanceV2_InstantiatedVnfInfo.from_dict(
            _inst_info_example)
        vim_info = {
            "vim1": objects.VimConnectionInfo.from_dict(
                _vim_connection_info_for_change_vnfpkg)
        }
        inst = objects.VnfInstanceV2(
            # required fields
            id="d7aeba20-1b00-4bff-b050-6b42a262c84d",
            vnfdId=SAMPLE_VNFD_ID,
            vnfProvider='provider',
            vnfProductName='product name',
            vnfSoftwareVersion='software version',
            vnfdVersion='vnfd version',
            instantiationState='INSTANTIATED'
        )
        inst.vimConnectionInfo = vim_info
        inst.instantiatedVnfInfo = inst_info
        grant_req = objects.GrantRequestV1(
            operation=fields.LcmOperationType.CHANGE_VNFPKG
        )
        grant = objects.GrantV1()

        affected_vnfcs = objects.AffectedVnfcV2(
            id=uuidutils.generate_uuid(),
            vduId='VDU2',
            vnfdId=SAMPLE_VNFD_ID,
            changeType='MODIFIED',
            metadata={
                "creation_time": "2021-12-10T01:03:49Z",
                "stack_id": 'vnf-d7aeba20-1b00-4bff-b050-6b42a262c84d/'
                            'd7aeba20-1b00-4bff-b050-6b42a262c84d'
            }
        )
        resource_change = objects.VnfLcmOpOccV2_ResourceChanges(
            affectedVnfcs=[affected_vnfcs]
        )

        lcmocc = objects.VnfLcmOpOccV2(
            # required fields
            id=uuidutils.generate_uuid(),
            operationState=fields.LcmOperationStateType.FAILED_TEMP,
            stateEnteredTime=datetime.utcnow(),
            startTime=datetime.utcnow(),
            vnfInstanceId=inst.id,
            operation=fields.LcmOperationType.CHANGE_VNFPKG,
            resourceChanges=resource_change,
            isAutomaticInvocation=False,
            isCancelPending=False,
            operationParams=req)

        stack_body = {'stack': {'id': 'd7aeba20-1b00-4bff-b050-6b42a262c84d',
                      'name': 'test'}}
        stack_body_2 = {'stack': {
            'stack_name':
                'vnf-d7aeba20-1b00-4bff-b050-6b42a262c84d-VDU1_scale_group'}}
        mocked_get_stack_resource.side_effect = [stack_body, stack_body_2]

        body = {"attributes": {"floating_ip_address": "192.168.0.1"}}
        body_2 = {"attributes": {
            "image": {
                "id": "image-1.0.0-x86_64-disk"},
            "flavor": {"original_name": "m1.tiny"}
        }
        }
        mocked_get_resource_info.side_effect = [body, body_2]
        mocked_get_resources.side_effect = [mock_resource['resources'],
                                            _heat_reses_example]
        mocked_get_template.return_value = mock_resource_template_3
        mocked_get_resource_list.return_value = mock_resource_list_3
        mocked_update_stack.return_value = mock.Mock()
        resp_image = requests.Response()
        resp_image.name = "image-1.0.0-x86_64-disk"
        mocked_get_image.return_value = resp_image
        out = requests.Response()
        out.returncode = 0
        mocked_run.return_value = out
        parameter = {
            'nfv': '{"VDU":{"VDU1":{"vcImageId":""},'
                   '"VDU2":{"vcImageId":""},'
                   '"VirtualStorage":{"vcImageId":""}}}'
        }
        mocked_get_parameters.return_value = parameter
        self.driver.change_vnfpkg_rollback(req, inst, grant_req, grant,
                                  self.vnfd_1, lcmocc)
        # check
        for vnfc_res in inst.instantiatedVnfInfo.vnfcResourceInfo:
            if vnfc_res.vduId == "VDU2":
                self.assertEqual(vnfc_res.id,
                                 'res_id_VDU2_1')
                self.assertEqual(vnfc_res.computeResource.resourceId,
                                 'res_id_VDU2_1')
                self.assertIn('current_vnfd_id', vnfc_res.metadata)
