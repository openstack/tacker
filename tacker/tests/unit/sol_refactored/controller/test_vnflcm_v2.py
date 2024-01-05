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
from datetime import datetime
import ddt
from http import client as http_client
import requests
from unittest import mock

from oslo_policy import policy as oslo_policy
from oslo_utils import uuidutils

from tacker.common.exceptions import PolicyNotAuthorized
from tacker import context
from tacker import policy
from tacker.sol_refactored.api import api_version
from tacker.sol_refactored.api.policies.vnflcm_v2 import POLICY_NAME
from tacker.sol_refactored.common import config
from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.common import lcm_op_occ_utils as lcmocc_utils
from tacker.sol_refactored.common import subscription_utils as subsc_utils
from tacker.sol_refactored.common import vim_utils
from tacker.sol_refactored.common import vnf_instance_utils as inst_utils
from tacker.sol_refactored.common import vnfd_utils
from tacker.sol_refactored.conductor import conductor_rpc_v2
from tacker.sol_refactored.controller import vnflcm_v2
from tacker.sol_refactored.nfvo import nfvo_client
from tacker.sol_refactored import objects
from tacker.sol_refactored.objects.v2 import fields
from tacker.tests.unit.db import base as db_base
from tacker.tests import utils


objects.register_all()


_change_ext_conn_req_example = {
    "extVirtualLinks": [
        {
            "id": "id_ext_vl_1",
            "resourceId": "res_id_ext_vl_1",
            "extCps": [
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
    ]
}

_vim_connection_info_example = {
    "vimId": "vim_id_1",
    "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_3",
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

_inst_req_example = {
    "flavourId": "simple",
    "vimConnectionInfo": {
        "vim1": _vim_connection_info_example
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
            "vimType": "ETSINFV.KUBERNETES.V_1",
            "vimId": uuidutils.generate_uuid(),
            "interfaceInfo": {"endpoint": "https://127.0.0.1:6443"},
            "accessInfo": {
                "bearer_token": "secret_token",
                "region": "RegionOne"
            }
        }
    }
}

SAMPLE_VNFD_ID = "b1bb0ce7-ebca-4fa7-95ed-4840d7000000"

CONF = config.CONF


def get_test_data_policy_instantiate():
    rules = {POLICY_NAME.format('instantiate'): "vendor:%(vendor)s"}
    test_data = [
        # 'expected_status_code': http_client.ACCEPTED
        {
            'vnf_instance_updates': {'vnfProvider': 'provider_A'},
            'rules': rules,
            'roles': ['VENDOR_provider_A'],
            'expected_status_code': http_client.ACCEPTED
        },
        {
            'vnf_instance_updates': {'vnfProvider': 'provider_A'},
            'rules': rules,
            'roles': ['VENDOR_all'],
            'expected_status_code': http_client.ACCEPTED
        },
        # 'expected_status_code': http_client.FORBIDDEN
        {
            'vnf_instance_updates': {'vnfProvider': 'provider_A'},
            'rules': rules,
            'roles': [],
            'expected_status_code': http_client.FORBIDDEN
        },
        {
            'vnf_instance_updates': {'vnfProvider': 'provider_A'},
            'rules': rules,
            'roles': ['VENDOR_provider_B'],
            'expected_status_code': http_client.FORBIDDEN
        },
    ]
    return test_data


def get_test_data_policy_vnf_instantiated(action, success_status_code):
    vim_connection_info_area_a_region_a = objects.VimConnectionInfo(
        id='f8c35bd0-4d67-4436-9f11-14b8a84c92aa',
        vimId='f8c35bd0-4d67-4436-9f11-14b8a84c92aa',
        vimType='openstack',
        access_info={"key1": 'value1', "key2": 'value2'},
        extra={'area': 'area_A@region_A'}
    )
    vim_connection_info_without_area = objects.VimConnectionInfo(
        id='f8c35bd0-4d67-4436-9f11-14b8a84c92aa',
        vimId='f8c35bd0-4d67-4436-9f11-14b8a84c92aa',
        vimType='openstack',
        access_info={"key1": 'value1', "key2": 'value2'}
    )
    vnf_instance_updates = {
        'vnfProvider': 'provider_A',
        'vimConnectionInfo': {'vim1': vim_connection_info_area_a_region_a}
    }
    vnf_instance_updates_without_area = {
        'vnfProvider': 'provider_A',
        'vimConnectionInfo': {'vim1': vim_connection_info_without_area}
    }
    rule_area_vendor_tenant = {
        POLICY_NAME.format(action):
            "area:%(area)s and vendor:%(vendor)s and "
            "tenant:%(tenant)s"
    }
    rule_vendor = {
        POLICY_NAME.format(action): "vendor:%(vendor)s"
    }
    test_data = [
        # 'expected_status_code': success_status_code
        {
            'vnf_instance_updates': vnf_instance_updates,
            'tenant': 'tenant_A',
            'rules': rule_area_vendor_tenant,
            'roles': [
                'AREA_area_A@region_A',
                'VENDOR_provider_A',
                'TENANT_tenant_A'
            ],
            'expected_status_code': success_status_code
        },
        {
            'vnf_instance_updates': vnf_instance_updates,
            'tenant': 'tenant_A',
            'rules': rule_area_vendor_tenant,
            'roles': [
                'AREA_all@all', 'VENDOR_all', 'TENANT_all'
            ],
            'expected_status_code': success_status_code
        },
        {
            'vnf_instance_updates': vnf_instance_updates,
            'tenant': 'tenant_A',
            'rules': rule_area_vendor_tenant,
            'roles': [
                'AREA_all@region_A', 'VENDOR_all', 'TENANT_all'
            ],
            'expected_status_code': success_status_code
        },
        {
            'vnf_instance_updates': vnf_instance_updates,
            'tenant': 'tenant_A',
            'rules': rule_vendor,
            'roles': [
                'AREA_area_A@region_A',
                'VENDOR_provider_A',
                'TENANT_tenant_A'
            ],
            'expected_status_code': success_status_code
        },
        # 'expected_status_code': http_client.FORBIDDEN
        {
            'vnf_instance_updates': vnf_instance_updates,
            'tenant': None,
            'rules': rule_area_vendor_tenant,
            'roles': [
                'AREA_area_A@region_A',
                'VENDOR_provider_A',
                'TENANT_tenant_A'
            ],
            'expected_status_code': http_client.FORBIDDEN
        },
        {
            'vnf_instance_updates': vnf_instance_updates_without_area,
            'tenant': 'tenant_A',
            'rules': rule_area_vendor_tenant,
            'roles': [
                'AREA_area_A@region_A',
                'VENDOR_provider_A',
                'TENANT_tenant_A'
            ],
            'expected_status_code': http_client.FORBIDDEN
        },
        {
            'vnf_instance_updates':
                vnf_instance_updates_without_area,
            'tenant': None,
            'rules': rule_area_vendor_tenant,
            'roles': [
                'AREA_area_A@region_A',
                'VENDOR_provider_A',
                'TENANT_tenant_A'
            ],
            'expected_status_code': http_client.FORBIDDEN
        },
        {
            'vnf_instance_updates': vnf_instance_updates,
            'tenant': 'tenant_A',
            'rules': rule_area_vendor_tenant,
            'roles': [
                'AREA_area_B@region_A',
                'VENDOR_provider_A',
                'TENANT_tenant_A'
            ],
            'expected_status_code': http_client.FORBIDDEN
        },
        {
            'vnf_instance_updates': vnf_instance_updates,
            'tenant': 'tenant_A',
            'rules': rule_area_vendor_tenant,
            'roles': [
                'AREA_area_A@region_A',
                'VENDOR_provider_B',
                'TENANT_tenant_A'
            ],
            'expected_status_code': http_client.FORBIDDEN
        },
        {
            'vnf_instance_updates': vnf_instance_updates,
            'tenant': 'tenant_A',
            'rules': rule_area_vendor_tenant,
            'roles': [
                'AREA_area_A@region_A',
                'VENDOR_provider_A',
                'TENANT_tenant_B'
            ],
            'expected_status_code': http_client.FORBIDDEN
        },
        {
            'vnf_instance_updates': vnf_instance_updates,
            'tenant': 'tenant_A',
            'rules': rule_area_vendor_tenant,
            'roles': [
                'VENDOR_provider_A',
                'TENANT_tenant_A'
            ],
            'expected_status_code': http_client.FORBIDDEN
        },
        {
            'vnf_instance_updates': vnf_instance_updates,
            'tenant': 'tenant_A',
            'rules': rule_area_vendor_tenant,
            'roles': [
                'AREA_area_A@region_A',
                'TENANT_tenant_A'
            ],
            'expected_status_code': http_client.FORBIDDEN
        },
        {
            'vnf_instance_updates': vnf_instance_updates,
            'tenant': 'tenant_A',
            'rules': rule_area_vendor_tenant,
            'roles': [
                'AREA_area_A@region_A',
                'VENDOR_provider_A',
            ],
            'expected_status_code': http_client.FORBIDDEN
        },
        {
            'vnf_instance_updates': vnf_instance_updates,
            'tenant': 'tenant_A',
            'rules': rule_area_vendor_tenant,
            'roles': [],
            'expected_status_code': http_client.FORBIDDEN
        },
        {
            'vnf_instance_updates': vnf_instance_updates,
            'tenant': 'tenant_A',
            'rules': rule_area_vendor_tenant,
            'roles': [
                'AREA_all@region_B',
                'VENDOR_provider_A',
                'TENANT_tenant_A'
            ],
            'expected_status_code': http_client.FORBIDDEN
        },
        {
            'vnf_instance_updates': vnf_instance_updates,
            'tenant': 'tenant_A',
            'rules': rule_vendor,
            'roles': [
                'AREA_area_A@region_A',
                'VENDOR_provider_B',
                'TENANT_tenant_A'
            ],
            'expected_status_code': http_client.FORBIDDEN
        },
        {
            'vnf_instance_updates': vnf_instance_updates,
            'tenant': 'tenant_A',
            'rules': rule_vendor,
            'roles': [
                'AREA_area_A@region_A',
                'TENANT_tenant_A'
            ],
            'expected_status_code': http_client.FORBIDDEN
        },
        {
            'vnf_instance_updates':
                vnf_instance_updates_without_area,
            'tenant': None,
            'rules': rule_area_vendor_tenant,
            'roles': [
                'AREA_area_B@region_A',
                'VENDOR_provider_B',
                'TENANT_tenant_A'
            ],
            'expected_status_code': http_client.FORBIDDEN
        },
        {
            'vnf_instance_updates':
                vnf_instance_updates_without_area,
            'tenant': None,
            'rules': rule_area_vendor_tenant,
            'roles': [
                'VENDOR_provider_B',
            ],
            'expected_status_code': http_client.FORBIDDEN
        },
        {
            'vnf_instance_updates':
                vnf_instance_updates_without_area,
            'tenant': None,
            'rules': rule_vendor,
            'roles': [
                'VENDOR_provider_B',
            ],
            'expected_status_code': http_client.FORBIDDEN
        }
    ]
    return test_data


def get_test_data_policy_delete():
    rules = {POLICY_NAME.format('delete'): "vendor:%(vendor)s"}
    test_data = [
        # 'expected_status_code': http_client.NO_CONTENT
        {
            'vnf_instance_updates': {'vnfProvider': 'provider_A'},
            'rules': rules,
            'roles': ['VENDOR_provider_A'],
            'expected_status_code': http_client.NO_CONTENT
        },
        {
            'vnf_instance_updates': {'vnfProvider': 'provider_A'},
            'rules': rules,
            'roles': ['VENDOR_all'],
            'expected_status_code': http_client.NO_CONTENT
        },
        # 'expected_status_code': http_client.FORBIDDEN
        {
            'vnf_instance_updates': {'vnfProvider': 'provider_A'},
            'rules': rules,
            'roles': [],
            'expected_status_code': http_client.FORBIDDEN
        },
        {
            'vnf_instance_updates': {'vnfProvider': 'provider_A'},
            'rules': rules,
            'roles': ['VENDOR_provider_B'],
            'expected_status_code': http_client.FORBIDDEN
        },
    ]
    return test_data


def make_vnf_instance(
        vim_type, instantiation_state, vendor, area=None, tenant=None):
    vim_connection_info = objects.VimConnectionInfo(
        id='f8c35bd0-4d67-4436-9f11-14b8a84c92aa',
        vimId='f8c35bd0-4d67-4436-9f11-14b8a84c92aa',
        vimType=vim_type,
        access_info={"key1": 'value1', "key2": 'value2'},
    )

    if area:
        vim_connection_info.update({'extra': {'area': area}})

    vnf_instance_updates = {
        'id': uuidutils.generate_uuid(),
        'vnfProvider': vendor,
        'vimConnectionInfo': {'vim1': vim_connection_info}
    }
    vnf_inst_fields = {
        'id': uuidutils.generate_uuid(),
        'vnfdId': uuidutils.generate_uuid(),
        'vnfProductName': 'product name',
        'vnfSoftwareVersion': 'software version',
        'vnfdVersion': 'vnfd version',
        'instantiationState': instantiation_state
    }

    vnf_instance_updates.update(vnf_inst_fields)

    vnf_instance = objects.VnfInstanceV2(**vnf_instance_updates)

    if tenant:
        vnf_instance.instantiatedVnfInfo = (
            objects.VnfInstanceV2_InstantiatedVnfInfo(
                flavourId='fake_flavour_id',
                vnfState='STARTED',
                metadata={'tenant': tenant}))
        vnf_inst_fields.update({'metadata': {'tenant': tenant}})

    return vnf_instance


def get_test_data_policy_index():
    rule_area_vendor_tenant = {
        POLICY_NAME.format('index'):
            "area:%(area)s and vendor:%(vendor)s and "
            "tenant:%(tenant)s"
    }

    test_data = []

    inst_1 = make_vnf_instance(
        'ETSINFV.OPENSTACK_KEYSTONE.V_3', 'INSTANTIATED', 'provider_A',
        area='area_A@region_A', tenant='tenant_A')
    # OK
    test_data.append({
        'vnf_instance_list': [inst_1],
        'rules': rule_area_vendor_tenant,
        'roles': ['AREA_area_A@region_A', 'VENDOR_provider_A',
                  'TENANT_tenant_A'],
        'expected_vnf_inst_ids': [inst_1.id]
    })
    test_data.append({
        'vnf_instance_list': [inst_1],
        'rules': rule_area_vendor_tenant,
        'roles': ['AREA_all@all', 'VENDOR_all', 'TENANT_all'],
        'expected_vnf_inst_ids': [inst_1.id]
    })
    test_data.append({
        'vnf_instance_list': [inst_1],
        'rules': rule_area_vendor_tenant,
        'roles': ['AREA_all@region_A', 'VENDOR_all', 'TENANT_all'],
        'expected_vnf_inst_ids': [inst_1.id]
    })
    # wrong region role
    test_data.append({
        'vnf_instance_list': [inst_1],
        'rules': rule_area_vendor_tenant,
        'roles': ['AREA_all@region_B', 'VENDOR_all', 'TENANT_all'],
        'expected_vnf_inst_ids': []
    })
    # wrong area role
    test_data.append({
        'vnf_instance_list': [inst_1],
        'rules': rule_area_vendor_tenant,
        'roles': ['AREA_area_B@region_A', 'VENDOR_provider_A', 'TENANT_all'],
        'expected_vnf_inst_ids': []
    })
    # wrong vendor role
    test_data.append({
        'vnf_instance_list': [inst_1],
        'rules': rule_area_vendor_tenant,
        'roles': ['AREA_area_A@region_A', 'VENDOR_provider_B', 'TENANT_all'],
        'expected_vnf_inst_ids': []
    })
    # wrong tenant role
    test_data.append({
        'vnf_instance_list': [inst_1],
        'rules': rule_area_vendor_tenant,
        'roles': ['AREA_area_A@region_A', 'VENDOR_provider_A', 'TENANT_B'],
        'expected_vnf_inst_ids': []
    })
    # without area
    inst_2 = make_vnf_instance(
        'ETSINFV.OPENSTACK_KEYSTONE.V_3', 'INSTANTIATED', 'provider_A',
        tenant='tenant_A')
    test_data.append({
        'vnf_instance_list': [inst_2],
        'rules': rule_area_vendor_tenant,
        'roles': ['AREA_area_A@region_A', 'VENDOR_provider_A'],
        'expected_vnf_inst_ids': []
    })
    # NOT_INSTANTIATED
    inst_3 = make_vnf_instance(
        'ETSINFV.OPENSTACK_KEYSTONE.V_3', 'NOT_INSTANTIATED', 'provider_A',
        tenant='tenant_A')
    test_data.append({
        'vnf_instance_list': [inst_3],
        'rules': rule_area_vendor_tenant,
        'roles': ['VENDOR_provider_A'],
        'expected_vnf_inst_ids': [inst_3.id]
    })

    inst_4 = make_vnf_instance(
        'kubernetes', 'INSTANTIATED', 'provider_A', area='area_A@region_A',
        tenant='namespace_A')
    # OK
    test_data.append({
        'vnf_instance_list': [inst_4],
        'rules': rule_area_vendor_tenant,
        'roles': [
            'AREA_area_A@region_A',
            'VENDOR_provider_A',
            'TENANT_namespace_A'],
        'expected_vnf_inst_ids': [inst_4.id]
    })
    test_data.append({
        'vnf_instance_list': [inst_4],
        'rules': rule_area_vendor_tenant,
        'roles': [
            'AREA_all@region_A',
            'VENDOR_all',
            'TENANT_all'],
        'expected_vnf_inst_ids': [inst_4.id]
    })
    test_data.append({
        'vnf_instance_list': [inst_4],
        'rules': rule_area_vendor_tenant,
        'roles': [
            'AREA_all@all',
            'VENDOR_all',
            'TENANT_all'],
        'expected_vnf_inst_ids': [inst_4.id]
    })
    # wrong region role
    test_data.append({
        'vnf_instance_list': [inst_4],
        'rules': rule_area_vendor_tenant,
        'roles': [
            'AREA_all@region_B',
            'VENDOR_all',
            'TENANT_all'],
        'expected_vnf_inst_ids': []
    })
    # wrong region role
    test_data.append({
        'vnf_instance_list': [inst_4],
        'rules': rule_area_vendor_tenant,
        'roles': [
            'AREA_area_B@region_A',
            'VENDOR_all',
            'TENANT_all'],
        'expected_vnf_inst_ids': []
    })
    # wrong vendor role
    test_data.append({
        'vnf_instance_list': [inst_4],
        'rules': rule_area_vendor_tenant,
        'roles': [
            'AREA_area_A@region_A',
            'VENDOR_provider_B',
            'TENANT_all'],
        'expected_vnf_inst_ids': []
    })
    # wrong namespace
    test_data.append({
        'vnf_instance_list': [inst_4],
        'rules': rule_area_vendor_tenant,
        'roles': [
            'AREA_all@all',
            'VENDOR_all',
            'TENANT_namespace_b'],
        'expected_vnf_inst_ids': []
    })
    # without namespace
    inst_5 = make_vnf_instance(
        'kubernetes', 'INSTANTIATED', 'provider_A', area='area_A@region_A')
    test_data.append({
        'vnf_instance_list': [inst_5],
        'rules': rule_area_vendor_tenant,
        'roles': [
            'AREA_area_A@region_A',
            'VENDOR_provider_A',
            'TENANT_all'],
        'expected_vnf_inst_ids': []
    })
    inst_6 = make_vnf_instance(
        'kubernetes', 'NOT_INSTANTIATED', 'provider_A')
    # OK
    test_data.append({
        'vnf_instance_list': [inst_6],
        'rules': rule_area_vendor_tenant,
        'roles': [
            'VENDOR_provider_A',
        ],
        'expected_vnf_inst_ids': [inst_6.id]
    })

    return test_data


class TestVnflcmV2(db_base.SqlTestCase):

    def setUp(self):
        super(TestVnflcmV2, self).setUp()
        objects.register_all()
        self.controller = vnflcm_v2.VnfLcmControllerV2()
        self.context = context.get_admin_context()
        self.context.api_version = api_version.APIVersion("2.0.0")
        self.request = mock.Mock()
        self.request.context = self.context
        self.vnfd_1 = vnfd_utils.Vnfd(SAMPLE_VNFD_ID)

    def _set_inst_and_lcmocc(self, inst_state, op_state):
        inst = objects.VnfInstanceV2(
            # required fields
            id=uuidutils.generate_uuid(),
            vnfdId=uuidutils.generate_uuid(),
            vnfProvider='provider',
            vnfProductName='product name',
            vnfSoftwareVersion='software version',
            vnfdVersion='vnfd version',
            instantiationState=inst_state
        )

        req = {"flavourId": "simple"}  # instantiate request
        lcmocc = objects.VnfLcmOpOccV2(
            # required fields
            id=uuidutils.generate_uuid(),
            operationState=op_state,
            stateEnteredTime=datetime.utcnow(),
            startTime=datetime.utcnow(),
            vnfInstanceId=inst.id,
            operation=fields.LcmOperationType.INSTANTIATE,
            isAutomaticInvocation=False,
            isCancelPending=False,
            operationParams=req
        )

        return inst, lcmocc

    def _create_inst_and_lcmocc(self, inst_state, op_state):
        inst, lcmocc = self._set_inst_and_lcmocc(inst_state, op_state)

        inst.create(self.context)
        lcmocc.create(self.context)

        return inst.id, lcmocc.id

    @mock.patch.object(nfvo_client.NfvoClient, 'get_vnf_package_info_vnfd')
    def test_create_pkg_disabled(self, mocked_get_vnf_package_info_vnfd):
        vnfd_id = uuidutils.generate_uuid()
        pkg_info = objects.VnfPkgInfoV2(
            id=uuidutils.generate_uuid(),
            vnfdId=vnfd_id,
            vnfProvider="provider",
            vnfProductName="product",
            vnfSoftwareVersion="software version",
            vnfdVersion="vnfd version",
            operationalState="DISABLED"
        )
        mocked_get_vnf_package_info_vnfd.return_value = pkg_info
        body = {
            "vnfdId": vnfd_id,
            "vnfInstanceName": "test",
            "vnfInstanceDescription": "test"
        }
        self.assertRaises(sol_ex.VnfdIdNotEnabled,
            self.controller.create, request=self.request, body=body)

    @mock.patch.object(nfvo_client.NfvoClient, 'get_vnf_package_info_vnfd')
    @mock.patch.object(nfvo_client.NfvoClient, 'get_vnfd')
    @mock.patch.object(nfvo_client.NfvoClient, 'send_inst_create_notification')
    @mock.patch.object(vnfd_utils.Vnfd, 'get_vnfd_properties')
    def test_create_201(
            self, mock_prop, mock_send, mock_vnfd,
            mocked_get_vnf_package_info_vnfd):
        vnfd_id = uuidutils.generate_uuid()
        pkg_info = objects.VnfPkgInfoV2(
            id=uuidutils.generate_uuid(),
            vnfdId=vnfd_id,
            vnfProvider="provider",
            vnfProductName="product",
            vnfSoftwareVersion="software version",
            vnfdVersion="vnfd version",
            operationalState="ENABLED"
        )
        mocked_get_vnf_package_info_vnfd.return_value = pkg_info
        mock_vnfd.return_value = self.vnfd_1
        mock_prop.return_value = {
            'vnfConfigurableProperties': {"test": "test"},
            'extensions': {"test": "test"},
            'metadata': {}
        }
        body = {
            "vnfdId": vnfd_id,
            "vnfInstanceName": "test",
            "vnfInstanceDescription": "test",
            "metadata": {
                "key": "value",
                "VDU_VNFc_mapping": {
                    "VDU1": ["a-001", "a-002", "a-003"],
                    "VDU2": ["b-001"]
                }
            }
        }
        result = self.controller.create(request=self.request, body=body)
        self.assertEqual(201, result.status)

    @mock.patch.object(inst_utils, 'get_inst_all')
    def test_index(self, mock_inst):
        request = requests.Request()
        request.context = self.context
        request.GET = {'filter': f'(eq,vnfdId,{SAMPLE_VNFD_ID})'}
        mock_inst.return_value = [objects.VnfInstanceV2(
            id='inst-1', vnfdId=SAMPLE_VNFD_ID,
            instantiationState='NOT_INSTANTIATED')]

        result = self.controller.index(request)
        self.assertEqual(200, result.status)

        # no filter
        request.GET = {}
        result = self.controller.index(request)
        self.assertEqual(200, result.status)

    @mock.patch.object(inst_utils, 'get_inst')
    def test_show(self, mock_inst):
        request = requests.Request()
        request.context = self.context
        mock_inst.return_value = objects.VnfInstanceV2(
            id='inst-1', vnfdId=SAMPLE_VNFD_ID,
            instantiationState='NOT_INSTANTIATED')
        result = self.controller.show(request, 'inst-1')
        self.assertEqual(200, result.status)

    @mock.patch.object(nfvo_client.NfvoClient, 'get_vnf_package_info_vnfd')
    def test_change_vnfpkg_pkg_disabled(self,
                                        mocked_get_vnf_package_info_vnfd):
        vnfd_id = uuidutils.generate_uuid()
        inst_id = self._prepare_db_for_change_vnfpkg_param()
        body = {"vnfdId": vnfd_id}
        pkg_info = objects.VnfPkgInfoV2(
            id=uuidutils.generate_uuid(),
            vnfdId=vnfd_id,
            vnfProvider="provider",
            vnfProductName="product",
            vnfSoftwareVersion="software version",
            vnfdVersion="vnfd version",
            operationalState="DISABLED"
        )
        mocked_get_vnf_package_info_vnfd.return_value = pkg_info
        self.assertRaises(sol_ex.VnfdIdNotEnabled,
            self.controller.change_vnfpkg, request=self.request, id=inst_id,
                          body=body)

    @mock.patch.object(nfvo_client.NfvoClient, 'get_vnf_package_info_vnfd')
    def test_change_vnfpkg_pkg_no_additional_params(
            self, mocked_get_vnf_package_info_vnfd):
        vnfd_id = uuidutils.generate_uuid()
        inst_id = self._prepare_db_for_change_vnfpkg_param()
        body = {"vnfdId": vnfd_id}
        pkg_info = objects.VnfPkgInfoV2(
            id=uuidutils.generate_uuid(),
            vnfdId=vnfd_id,
            vnfProvider="provider",
            vnfProductName="product",
            vnfSoftwareVersion="software version",
            vnfdVersion="vnfd version",
            operationalState="ENABLED"
        )
        mocked_get_vnf_package_info_vnfd.return_value = pkg_info
        self.assertRaises(sol_ex.SolValidationError,
            self.controller.change_vnfpkg, request=self.request, id=inst_id,
                          body=body)

    @mock.patch.object(nfvo_client.NfvoClient, 'get_vnf_package_info_vnfd')
    def test_change_vnfpkg_pkg_upgrade_type(
            self, mocked_get_vnf_package_info_vnfd):
        vnfd_id = uuidutils.generate_uuid()
        inst_id = self._prepare_db_for_change_vnfpkg_param()
        body = {
            "vnfdId": vnfd_id,
            "additionalParams": {
                "upgrade_type": "BuleGreen"
            }
        }
        pkg_info = objects.VnfPkgInfoV2(
            id=uuidutils.generate_uuid(),
            vnfdId=vnfd_id,
            vnfProvider="provider",
            vnfProductName="product",
            vnfSoftwareVersion="software version",
            vnfdVersion="vnfd version",
            operationalState="ENABLED"
        )
        mocked_get_vnf_package_info_vnfd.return_value = pkg_info
        self.assertRaises(sol_ex.NotSupportUpgradeType,
            self.controller.change_vnfpkg, request=self.request, id=inst_id,
                          body=body)

    @mock.patch.object(nfvo_client.NfvoClient, 'get_vnf_package_info_vnfd')
    def test_change_vnfpkg_pkg_no_vduId(
            self, mocked_get_vnf_package_info_vnfd):
        vnfd_id = uuidutils.generate_uuid()
        inst_id = self._prepare_db_for_change_vnfpkg_param()
        body = {
            "vnfdId": vnfd_id,
            "additionalParams": {
                "upgrade_type": "RollingUpdate",
                "vdu_params": [{}]
            }
        }
        pkg_info = objects.VnfPkgInfoV2(
            id=uuidutils.generate_uuid(),
            vnfdId=vnfd_id,
            vnfProvider="provider",
            vnfProductName="product",
            vnfSoftwareVersion="software version",
            vnfdVersion="vnfd version",
            operationalState="ENABLED"
        )
        mocked_get_vnf_package_info_vnfd.return_value = pkg_info
        self.assertRaises(sol_ex.SolValidationError,
                          self.controller.change_vnfpkg, request=self.request,
                          id=inst_id,
                          body=body)

    @mock.patch.object(nfvo_client.NfvoClient, 'get_vnf_package_info_vnfd')
    def test_change_vnfpkg_pkg_no_username(
            self, mocked_get_vnf_package_info_vnfd):
        vnfd_id = uuidutils.generate_uuid()
        inst_id = self._prepare_db_for_change_vnfpkg_param()
        body = {
            "vnfdId": vnfd_id,
            "additionalParams": {
                "upgrade_type": "RollingUpdate",
                "lcm-operation-coordinate-new-vnf": "test",
                "vdu_params": [{
                    "vdu_id": "VDU1",
                    "new_vnfc_param": {
                        "passoword": "test",
                        "cp_name": "VDU1_CP1"
                    }
                }]
            }
        }
        pkg_info = objects.VnfPkgInfoV2(
            id=uuidutils.generate_uuid(),
            vnfdId=vnfd_id,
            vnfProvider="provider",
            vnfProductName="product",
            vnfSoftwareVersion="software version",
            vnfdVersion="vnfd version",
            operationalState="ENABLED"
        )
        mocked_get_vnf_package_info_vnfd.return_value = pkg_info
        self.assertRaises(sol_ex.SolValidationError,
                          self.controller.change_vnfpkg, request=self.request,
                          id=inst_id,
                          body=body)

    @mock.patch.object(nfvo_client.NfvoClient, 'get_vnf_package_info_vnfd')
    @mock.patch.object(conductor_rpc_v2.VnfLcmRpcApiV2, 'start_lcm_op')
    def test_change_vnfpkg_pkg_202(
            self, mock_start, mocked_get_vnf_package_info_vnfd):
        vnfd_id = uuidutils.generate_uuid()
        inst_id = self._prepare_db_for_change_vnfpkg_param()
        body = {
            "vnfdId": vnfd_id,
            "additionalParams": {
                "upgrade_type": "RollingUpdate",
                "vdu_params": [{
                    "vdu_id": "VDU1",
                    "new_vnfc_param": {
                        "username": "test",
                        "password": "test",
                        "cp_name": "VDU1_CP1"
                    },
                    "old_vnfc_param": {
                        "username": "test",
                        "password": "test",
                        "cp_name": "VDU1_CP1"
                    }
                }]
            }
        }
        pkg_info = objects.VnfPkgInfoV2(
            id=uuidutils.generate_uuid(),
            vnfdId=vnfd_id,
            vnfProvider="provider",
            vnfProductName="product",
            vnfSoftwareVersion="software version",
            vnfdVersion="vnfd version",
            operationalState="ENABLED"
        )
        mocked_get_vnf_package_info_vnfd.return_value = pkg_info
        result = self.controller.change_vnfpkg(
            request=self.request, id=inst_id, body=body)
        self.assertEqual(202, result.status)

    def _prepare_db_for_change_vnfpkg_param(self):
        inst = objects.VnfInstanceV2(
            # required fields
            id=uuidutils.generate_uuid(),
            vnfdId=uuidutils.generate_uuid(),
            vnfProvider='provider',
            vnfProductName='product name',
            vnfSoftwareVersion='software version',
            vnfdVersion='vnfd version',
            instantiationState='INSTANTIATED'
        )
        inst.instantiatedVnfInfo = objects.VnfInstanceV2_InstantiatedVnfInfo(
            flavourId='small',
            vnfState='STARTED',
            vnfcResourceInfo=[
                objects.VnfcResourceInfoV2(
                    id="VDU1-vnfc_res_info_id_VDU1",
                    vduId="VDU1"
                )
            ]
        )
        inst.vimConnectionInfo = {
            "vim1": objects.VimConnectionInfo.from_dict(
                _vim_connection_info_example)}
        inst.create(self.context)
        return inst.id

    def test_delete_instantiated(self):
        inst_id, _ = self._create_inst_and_lcmocc('INSTANTIATED',
            fields.LcmOperationStateType.COMPLETED)

        self.assertRaises(sol_ex.VnfInstanceIsInstantiated,
            self.controller.delete, request=self.request, id=inst_id)

    def test_delete_lcmocc_in_progress(self):
        inst_id, _ = self._create_inst_and_lcmocc('NOT_INSTANTIATED',
            fields.LcmOperationStateType.FAILED_TEMP)

        self.assertRaises(sol_ex.OtherOperationInProgress,
            self.controller.delete, request=self.request, id=inst_id)

    @mock.patch.object(nfvo_client.NfvoClient, 'send_inst_delete_notification')
    def test_delete_204(self, mock_delete):
        inst_id, _ = self._create_inst_and_lcmocc('NOT_INSTANTIATED',
            fields.LcmOperationStateType.COMPLETED)
        result = self.controller.delete(self.request, id=inst_id)
        self.assertEqual(204, result.status)

    def test_instantiate_instantiated(self):
        inst_id, _ = self._create_inst_and_lcmocc('INSTANTIATED',
            fields.LcmOperationStateType.COMPLETED)
        body = {"flavourId": "small"}

        self.assertRaises(sol_ex.VnfInstanceIsInstantiated,
            self.controller.instantiate, request=self.request, id=inst_id,
            body=body)

    def test_instantiate_lcmocc_in_progress(self):
        inst_id, _ = self._create_inst_and_lcmocc('NOT_INSTANTIATED',
            fields.LcmOperationStateType.FAILED_TEMP)
        body = {"flavourId": "small"}

        self.assertRaises(sol_ex.OtherOperationInProgress,
            self.controller.instantiate, request=self.request, id=inst_id,
            body=body)

    @mock.patch.object(vim_utils, 'get_vim')
    @mock.patch.object(conductor_rpc_v2.VnfLcmRpcApiV2, 'start_lcm_op')
    def test_instantiate_202(self, mock_start, mock_vim):
        inst_id, _ = self._create_inst_and_lcmocc('NOT_INSTANTIATED',
            fields.LcmOperationStateType.COMPLETED)
        body = {
            "flavourId": "small",
            "vimConnectionInfo": {
                "vim1": {
                    "vimId": "vim_id_1",
                    "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_3"
                }
            }
        }
        mock_vim.return_value = objects.VimConnectionInfo.from_dict(
            _vim_connection_info_example)
        result = self.controller.instantiate(
            request=self.request, id=inst_id, body=body)
        self.assertEqual(202, result.status)

    def test_change_vnfpkg_not_instantiated(self):
        vnfd_id = uuidutils.generate_uuid()
        inst_id, _ = self._create_inst_and_lcmocc('NOT_INSTANTIATED',
            fields.LcmOperationStateType.COMPLETED)
        body = {"vnfdId": vnfd_id}

        self.assertRaises(sol_ex.VnfInstanceIsNotInstantiated,
            self.controller.change_vnfpkg, request=self.request, id=inst_id,
            body=body)

    def test_change_vnfpkg_lcmocc_in_progress(self):
        vnfd_id = uuidutils.generate_uuid()
        inst_id, _ = self._create_inst_and_lcmocc('INSTANTIATED',
            fields.LcmOperationStateType.FAILED_TEMP)
        body = {"vnfdId": vnfd_id}

        self.assertRaises(sol_ex.OtherOperationInProgress,
            self.controller.change_vnfpkg, request=self.request, id=inst_id,
            body=body)

    def test_terminate_not_instantiated(self):
        inst_id, _ = self._create_inst_and_lcmocc('NOT_INSTANTIATED',
            fields.LcmOperationStateType.COMPLETED)
        body = {"terminationType": "FORCEFUL"}

        self.assertRaises(sol_ex.VnfInstanceIsNotInstantiated,
            self.controller.terminate, request=self.request, id=inst_id,
            body=body)

    def test_terminate_lcmocc_in_progress(self):
        inst_id, _ = self._create_inst_and_lcmocc('INSTANTIATED',
            fields.LcmOperationStateType.FAILED_TEMP)
        body = {"terminationType": "FORCEFUL"}

        self.assertRaises(sol_ex.OtherOperationInProgress,
            self.controller.terminate, request=self.request, id=inst_id,
            body=body)

    @mock.patch.object(conductor_rpc_v2.VnfLcmRpcApiV2, 'start_lcm_op')
    def test_terminate_202(self, mock_start):
        inst_id, _ = self._create_inst_and_lcmocc(
            'INSTANTIATED', fields.LcmOperationStateType.COMPLETED)
        body = {"terminationType": "FORCEFUL"}

        result = self.controller.terminate(request=self.request, id=inst_id,
            body=body)
        self.assertEqual(202, result.status)

    def test_invalid_subscription(self):
        body_1 = {
            "callbackUri": "http://127.0.0.1:6789/notification",
            "authentication": {
                "authType": ["BASIC"]
            }
        }
        ex = self.assertRaises(sol_ex.InvalidSubscription,
            self.controller.subscription_create, request=self.request,
            body=body_1)
        self.assertEqual("paramsBasic must be specified.", ex.detail)

        body_2 = {
            "callbackUri": "http://127.0.0.1:6789/notification",
            "authentication": {
                "authType": ["OAUTH2_CLIENT_CREDENTIALS"]
            }
        }
        ex = self.assertRaises(sol_ex.InvalidSubscription,
            self.controller.subscription_create, request=self.request,
            body=body_2)
        self.assertEqual("paramsOauth2ClientCredentials must be specified.",
                         ex.detail)

        body_3 = {
            "callbackUri": "http://127.0.0.1:6789/notification",
            "authentication": {
                "authType": ["OAUTH2_CLIENT_CERT"]
            }
        }
        ex = self.assertRaises(sol_ex.InvalidSubscription,
            self.controller.subscription_create, request=self.request,
            body=body_3)
        self.assertEqual("paramsOauth2ClientCert must be specified.",
                         ex.detail)

    @mock.patch.object(subsc_utils, 'test_notification')
    def test_subscription_create_201(self, mock_test):
        sample_cert = utils.test_sample(
            "unit/sol_refactored/samples/sample_cert",
            "notification_client_cert.pem")
        CONF.v2_vnfm.notification_mtls_client_cert_file = sample_cert
        body_1 = {
            "callbackUri": "http://127.0.0.1:6789/notification",
            "authentication": {
                "authType": ["BASIC", "OAUTH2_CLIENT_CREDENTIALS",
                             "OAUTH2_CLIENT_CERT"],
                "paramsBasic": {
                    "userName": "test",
                    "password": "test"
                },
                "paramsOauth2ClientCredentials": {
                    "clientId": "test",
                    "clientPassword": "test",
                    "tokenEndpoint": "https://127.0.0.1/token"
                },
                "paramsOauth2ClientCert": {
                    "clientId": "test",
                    "certificateRef": {
                        "type": "x5t#S256",
                        "value": "8Shbulz8zlFdKG-iMCUz5CCv0A7q0k6X7wL3NcZpshM"
                    },
                    "tokenEndpoint": "https://127.0.0.1/token"
                }
            },
            "filter": {
                "operationTypes": [fields.LcmOperationType.INSTANTIATE]
            }
        }
        result = self.controller.subscription_create(
            request=self.request, body=body_1)
        self.assertEqual(201, result.status)

        body_2 = {
            "callbackUri": "http://127.0.0.1:6789/notification",
            "authentication": {
                "authType": ["BASIC"],
                "paramsBasic": {
                    "userName": "test",
                    "password": "test"
                }
            },
            "filter": {
                "operationTypes": [fields.LcmOperationType.INSTANTIATE]
            }
        }
        result = self.controller.subscription_create(
            request=self.request, body=body_2)
        self.assertEqual(201, result.status)

        body_3 = {
            "callbackUri": "http://127.0.0.1:6789/notification",
            "authentication": {
                "authType": ["OAUTH2_CLIENT_CREDENTIALS"],
                "paramsOauth2ClientCredentials": {
                    "clientId": "test",
                    "clientPassword": "test",
                    "tokenEndpoint": "https://127.0.0.1/token"
                }
            },
            "filter": {
                "operationTypes": [fields.LcmOperationType.INSTANTIATE]
            }
        }
        result = self.controller.subscription_create(
            request=self.request, body=body_3)
        self.assertEqual(201, result.status)

        body_4 = {
            "callbackUri": "http://127.0.0.1:6789/notification",
            "authentication": {
                "authType": ["OAUTH2_CLIENT_CERT"],
                "paramsOauth2ClientCert": {
                    "clientId": "test",
                    "certificateRef": {
                        "type": "x5t#S256",
                        "value": "8Shbulz8zlFdKG-iMCUz5CCv0A7q0k6X7wL3NcZpshM"
                    },
                    "tokenEndpoint": "https://127.0.0.1/token"
                }
            },
            "filter": {
                "operationTypes": [fields.LcmOperationType.INSTANTIATE]
            }
        }
        result = self.controller.subscription_create(
            request=self.request, body=body_4)
        self.assertEqual(201, result.status)

    @mock.patch.object(subsc_utils, 'get_subsc_all')
    def test_subscription_list(self, mock_subsc):
        request = requests.Request()
        request.context = self.context
        request.GET = {
            'filter': '(eq,callbackUri,http://127.0.0.1:6789/notification)'}
        lccn_subsc = {
            "id": "subsc-1",
            "callbackUri": "http://127.0.0.1:6789/notification"
        }
        mock_subsc.return_value = [
            objects.LccnSubscriptionV2.from_dict(lccn_subsc)]

        result = self.controller.subscription_list(request)
        self.assertEqual(200, result.status)

        # no filter
        request.GET = {}
        result = self.controller.subscription_list(request)
        self.assertEqual(200, result.status)

    @mock.patch.object(subsc_utils, 'get_subsc')
    def test_subscription_show(self, mock_subsc):
        mock_subsc.return_value = objects.LccnSubscriptionV2(id='subsc-1')
        result = self.controller.subscription_show(
            request=self.request, id='subsc-1')
        self.assertEqual(200, result.status)

    @mock.patch.object(subsc_utils, 'get_subsc')
    def test_subscription_delete(self, mock_subsc):
        mock_subsc.return_value = objects.LccnSubscriptionV2(id='subsc-1')
        result = self.controller.subscription_delete(
            request=self.request, id='subsc-1')
        self.assertEqual(204, result.status)

    @mock.patch.object(lcmocc_utils, 'get_lcmocc_all')
    def test_lcm_op_occ_list(self, mock_lcmocc):
        request = requests.Request()
        request.context = self.context
        request.GET = {
            'filter': f'(eq,operation,'
                      f'{fields.LcmOperationType.INSTANTIATE})'}
        mock_lcmocc.return_value = [objects.VnfLcmOpOccV2(
            id='lcmocc-1', operation='INSTANTIATE', vnfInstanceId='inst-1')]

        result = self.controller.lcm_op_occ_list(request)
        self.assertEqual(200, result.status)

        # no filter
        request.GET = {}
        result = self.controller.lcm_op_occ_list(request)
        self.assertEqual(200, result.status)

    @mock.patch.object(lcmocc_utils, 'get_lcmocc')
    def test_lcm_op_occ_show(self, mock_lcmocc):
        mock_lcmocc.return_value = objects.VnfLcmOpOccV2(
            id='lcmocc-1', operation='INSTANTIATE', vnfInstanceId='inst-1')
        result = self.controller.lcm_op_occ_show(
            request=self.request, id='lcmocc-1')
        self.assertEqual(200, result.status)

    def test_retry_not_failed_temp(self):
        _, lcmocc_id = self._create_inst_and_lcmocc('INSTANTIATED',
            fields.LcmOperationStateType.COMPLETED)

        self.assertRaises(sol_ex.LcmOpOccNotFailedTemp,
            self.controller.lcm_op_occ_retry, request=self.request,
            id=lcmocc_id)

    @mock.patch.object(lcmocc_utils, 'get_lcmocc')
    @mock.patch.object(vim_utils, 'get_default_vim')
    @mock.patch.object(conductor_rpc_v2.VnfLcmRpcApiV2, 'retry_lcm_op')
    @mock.patch.object(inst_utils, 'get_inst')
    def test_retry_202(self, mock_inst, mock_retry, mock_vim, mock_lcmocc):
        # instantiate with vimConnectionInfo
        req = objects.InstantiateVnfRequest.from_dict(
            _inst_req_example)
        mock_lcmocc.return_value = objects.VnfLcmOpOccV2(
            # required fields
            id=uuidutils.generate_uuid(),
            operationState=fields.LcmOperationStateType.FAILED_TEMP,
            stateEnteredTime=datetime.utcnow(),
            startTime=datetime.utcnow(),
            vnfInstanceId='inst-1',
            operation=fields.LcmOperationType.INSTANTIATE,
            isAutomaticInvocation=False,
            isCancelPending=False,
            operationParams=req)
        result = self.controller.lcm_op_occ_retry(
            request=self.request, id=mock_lcmocc.return_value.id)
        self.assertEqual(202, result.status)

        # instantiate with no vimConnectionInfo
        del mock_lcmocc.return_value.operationParams.vimConnectionInfo
        mock_vim.return_value = objects.VimConnectionInfo.from_dict(
            _vim_connection_info_example)
        result = self.controller.lcm_op_occ_retry(
            request=self.request, id=mock_lcmocc.return_value.id)
        self.assertEqual(202, result.status)

        # other operation
        mock_lcmocc.return_value = objects.VnfLcmOpOccV2(
            # required fields
            id=uuidutils.generate_uuid(),
            operationState=fields.LcmOperationStateType.FAILED_TEMP,
            stateEnteredTime=datetime.utcnow(),
            startTime=datetime.utcnow(),
            vnfInstanceId='inst-1',
            operation=fields.LcmOperationType.HEAL,
            isAutomaticInvocation=False,
            isCancelPending=False)
        mock_inst.return_value = objects.VnfInstanceV2(
            # required fields
            id=uuidutils.generate_uuid(),
            vnfdId=SAMPLE_VNFD_ID,
            vnfProvider='provider',
            vnfProductName='product name',
            vnfSoftwareVersion='software version',
            vnfdVersion='vnfd version',
            instantiationState='INSTANTIATED',
            vimConnectionInfo={"vim1": mock_vim.return_value}
        )
        result = self.controller.lcm_op_occ_retry(
            request=self.request, id=mock_lcmocc.return_value.id)
        self.assertEqual(202, result.status)

    def test_rollback_not_failed_temp(self):
        _, lcmocc_id = self._create_inst_and_lcmocc('INSTANTIATED',
            fields.LcmOperationStateType.COMPLETED)

        self.assertRaises(sol_ex.LcmOpOccNotFailedTemp,
            self.controller.lcm_op_occ_rollback, request=self.request,
            id=lcmocc_id)

    @mock.patch.object(lcmocc_utils, 'get_lcmocc')
    @mock.patch.object(vim_utils, 'get_default_vim')
    @mock.patch.object(conductor_rpc_v2.VnfLcmRpcApiV2, 'retry_lcm_op')
    @mock.patch.object(inst_utils, 'get_inst')
    def test_rollback_202(self, mock_inst, mock_retry, mock_vim, mock_lcmocc):
        # instantiate with vimConnectionInfo
        req = objects.InstantiateVnfRequest.from_dict(
            _inst_req_example)
        mock_lcmocc.return_value = objects.VnfLcmOpOccV2(
            # required fields
            id=uuidutils.generate_uuid(),
            operationState=fields.LcmOperationStateType.FAILED_TEMP,
            stateEnteredTime=datetime.utcnow(),
            startTime=datetime.utcnow(),
            vnfInstanceId='inst-1',
            operation=fields.LcmOperationType.INSTANTIATE,
            isAutomaticInvocation=False,
            isCancelPending=False,
            operationParams=req)
        result = self.controller.lcm_op_occ_rollback(
            request=self.request, id=mock_lcmocc.return_value.id)
        self.assertEqual(202, result.status)

        # instantiate with no vimConnectionInfo
        del mock_lcmocc.return_value.operationParams.vimConnectionInfo
        mock_vim.return_value = objects.VimConnectionInfo.from_dict(
            _vim_connection_info_example)
        result = self.controller.lcm_op_occ_rollback(
            request=self.request, id=mock_lcmocc.return_value.id)
        self.assertEqual(202, result.status)

        # other operation
        mock_lcmocc.return_value = objects.VnfLcmOpOccV2(
            # required fields
            id=uuidutils.generate_uuid(),
            operationState=fields.LcmOperationStateType.FAILED_TEMP,
            stateEnteredTime=datetime.utcnow(),
            startTime=datetime.utcnow(),
            vnfInstanceId='inst-1',
            operation=fields.LcmOperationType.HEAL,
            isAutomaticInvocation=False,
            isCancelPending=False)
        mock_inst.return_value = objects.VnfInstanceV2(
            # required fields
            id=uuidutils.generate_uuid(),
            vnfdId=SAMPLE_VNFD_ID,
            vnfProvider='provider',
            vnfProductName='product name',
            vnfSoftwareVersion='software version',
            vnfdVersion='vnfd version',
            instantiationState='INSTANTIATED',
            vimConnectionInfo={"vim1": mock_vim.return_value}
        )
        result = self.controller.lcm_op_occ_rollback(
            request=self.request, id=mock_lcmocc.return_value.id)
        self.assertEqual(202, result.status)

    def test_fail_not_failed_temp(self):
        _, lcmocc_id = self._create_inst_and_lcmocc('INSTANTIATED',
            fields.LcmOperationStateType.COMPLETED)

        self.assertRaises(sol_ex.LcmOpOccNotFailedTemp,
            self.controller.lcm_op_occ_fail, request=self.request,
            id=lcmocc_id)

    def test_lcm_op_occ_delete(self):
        _, lcmocc_id = self._create_inst_and_lcmocc(
            'INSTANTIATED', fields.LcmOperationStateType.FAILED_TEMP)
        # True
        CONF.v2_vnfm.test_enable_lcm_op_occ_delete = True
        result = self.controller.lcm_op_occ_delete(
            request=self.request, id=lcmocc_id)
        self.assertEqual(204, result.status)

        # False
        CONF.v2_vnfm.test_enable_lcm_op_occ_delete = False
        self.assertRaises(
            sol_ex.MethodNotAllowed, self.controller.lcm_op_occ_delete,
            request=self.request,
            id=lcmocc_id)

    def _prepare_db_for_fail(self):
        inst, lcmocc = self._set_inst_and_lcmocc('NOT_INSTANTIATED',
            fields.LcmOperationStateType.FAILED_TEMP)

        inst.create(self.context)
        lcmocc.create(self.context)

        grant_req = objects.GrantRequestV1(
            # required fields
            vnfInstanceId=lcmocc.vnfInstanceId,
            vnfLcmOpOccId=lcmocc.id,
            vnfdId=uuidutils.generate_uuid(),
            operation=lcmocc.operation,
            isAutomaticInvocation=lcmocc.isAutomaticInvocation
        )

        grant = objects.GrantV1(
            # required fields
            id=uuidutils.generate_uuid(),
            vnfInstanceId=lcmocc.vnfInstanceId,
            vnfLcmOpOccId=lcmocc.id
        )

        grant_req.create(self.context)
        grant.create(self.context)
        lcmocc.grantId = grant.id
        lcmocc.update(self.context)

        return lcmocc

    @mock.patch.object(nfvo_client.NfvoClient, 'send_lcmocc_notification')
    def test_lcm_op_occ_fail(self, mocked_send_lcmocc_notification):
        # prepare
        lcmocc = self._prepare_db_for_fail()
        before_state_entered_time = lcmocc.stateEnteredTime

        op_state = []
        op_state_entered_time = []

        def _store_state(context, lcmocc, inst, endpoint):
            op_state.append(lcmocc.operationState)
            op_state_entered_time.append(lcmocc.stateEnteredTime)

        mocked_send_lcmocc_notification.side_effect = _store_state

        # run lcm_op_occ_fail
        self.controller.lcm_op_occ_fail(self.request, lcmocc.id)

        # check operationstate
        self.assertEqual(1, mocked_send_lcmocc_notification.call_count)
        self.assertEqual(fields.LcmOperationStateType.FAILED, op_state[0])

        # check stateEnteredTime
        self.assertNotEqual(before_state_entered_time,
                            op_state_entered_time[0])

        # check grant_req and grant are deleted
        self.assertRaises(sol_ex.GrantRequestOrGrantNotFound,
            lcmocc_utils.get_grant_req_and_grant, self.context, lcmocc)

    def test_scale_not_instantiated(self):
        inst_id, _ = self._create_inst_and_lcmocc('NOT_INSTANTIATED',
            fields.LcmOperationStateType.COMPLETED)
        body = {"aspectId": "aspect_1", "type": "SCALE_OUT"}

        self.assertRaises(sol_ex.VnfInstanceIsNotInstantiated,
            self.controller.scale, request=self.request, id=inst_id,
            body=body)

    def test_scale_lcmocc_in_progress(self):
        inst_id, _ = self._create_inst_and_lcmocc('INSTANTIATED',
            fields.LcmOperationStateType.FAILED_TEMP)
        body = {"aspectId": "aspect_1", "type": "SCALE_OUT"}

        self.assertRaises(sol_ex.OtherOperationInProgress,
            self.controller.scale, request=self.request, id=inst_id,
            body=body)

    def _prepare_db_for_scale_param_check(self, scale_status,
            max_scale_levels):
        inst = objects.VnfInstanceV2(
            # required fields
            id=uuidutils.generate_uuid(),
            vnfdId=uuidutils.generate_uuid(),
            vnfProvider='provider',
            vnfProductName='product name',
            vnfSoftwareVersion='software version',
            vnfdVersion='vnfd version',
            instantiationState='INSTANTIATED'
        )
        inst.instantiatedVnfInfo = objects.VnfInstanceV2_InstantiatedVnfInfo(
            flavourId='small',
            vnfState='STARTED',
            scaleStatus=scale_status,
            maxScaleLevels=max_scale_levels
        )
        inst.create(self.context)

        return inst.id

    def test_scale_invalid_aspect_id(self):
        scale_status = [
            objects.ScaleInfoV2(
                aspectId="aspect_2",
                scaleLevel=0
            )
        ]
        max_scale_levels = [
            objects.ScaleInfoV2(
                aspectId="aspect_2",
                scaleLevel=3
            )
        ]
        inst_id = self._prepare_db_for_scale_param_check(scale_status,
                                                         max_scale_levels)
        body = {"aspectId": "aspect_1", "type": "SCALE_OUT"}

        self.assertRaises(sol_ex.InvalidScaleAspectId,
            self.controller.scale, request=self.request, id=inst_id,
            body=body)

    def test_scale_invalid_number_of_steps(self):
        scale_status = [
            objects.ScaleInfoV2(
                aspectId="aspect_1",
                scaleLevel=1
            )
        ]
        max_scale_levels = [
            objects.ScaleInfoV2(
                aspectId="aspect_1",
                scaleLevel=3
            )
        ]
        inst_id = self._prepare_db_for_scale_param_check(scale_status,
                                                         max_scale_levels)
        body = {"aspectId": "aspect_1", "type": "SCALE_OUT",
                "numberOfSteps": 3}

        self.assertRaises(sol_ex.InvalidScaleNumberOfSteps,
            self.controller.scale, request=self.request, id=inst_id,
            body=body)

        body = {"aspectId": "aspect_1", "type": "SCALE_IN",
                "numberOfSteps": 2}

        self.assertRaises(sol_ex.InvalidScaleNumberOfSteps,
            self.controller.scale, request=self.request, id=inst_id,
            body=body)

    @mock.patch.object(conductor_rpc_v2.VnfLcmRpcApiV2, 'start_lcm_op')
    def test_scale_202(self, mock_start):
        scale_status = [
            objects.ScaleInfoV2(
                aspectId="aspect_1",
                scaleLevel=1
            )
        ]
        max_scale_levels = [
            objects.ScaleInfoV2(
                aspectId="aspect_1",
                scaleLevel=3
            )
        ]
        inst_id = self._prepare_db_for_scale_param_check(scale_status,
                                                         max_scale_levels)
        body = {"aspectId": "aspect_1", "type": "SCALE_OUT",
                "numberOfSteps": 1}

        result = self.controller.scale(request=self.request, id=inst_id,
                                       body=body)
        self.assertEqual(202, result.status)

    def test_update_lcmocc_in_progress(self):
        inst_id, _ = self._create_inst_and_lcmocc('INSTANTIATED',
            fields.LcmOperationStateType.FAILED_TEMP)

        body = {"vnfInstanceDescription": "example1"}

        self.assertRaises(sol_ex.OtherOperationInProgress,
            self.controller.update, request=self.request, id=inst_id,
            body=body)

    def test_update_vim_connection_info_not_instantiated(self):
        inst = objects.VnfInstanceV2(
            # required fields
            id=uuidutils.generate_uuid(),
            vnfdId=uuidutils.generate_uuid(),
            vnfProvider='provider',
            vnfProductName='product name',
            vnfSoftwareVersion='software version',
            vnfdVersion='vnfd version',
            instantiationState='NOT_INSTANTIATED'
        )
        inst.create(self.context)

        body = {
            "vimConnectionInfo": {
                "vim1": {
                    "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_3",
                    "vimId": "c36428ef-3071-4b74-8d9a-f39c4dd30065",
                    "interfaceInfo": {
                        "endpoint": "http://localhost/identity/v3"
                    }
                }
            }
        }
        self.assertRaises(sol_ex.SolValidationError,
            self.controller.update, request=self.request, id=inst.id,
            body=body)

    @mock.patch.object(nfvo_client.NfvoClient, 'get_vnf_package_info_vnfd')
    def test_update_vnf_package_disabled(self,
            mocked_get_vnf_package_info_vnfd):
        inst = objects.VnfInstanceV2(
            # required fields
            id=uuidutils.generate_uuid(),
            vnfdId=uuidutils.generate_uuid(),
            vnfProvider='provider',
            vnfProductName='product name',
            vnfSoftwareVersion='software version',
            vnfdVersion='vnfd version',
            instantiationState='INSTANTIATED'
        )
        inst.create(self.context)

        req_vnfd_id = uuidutils.generate_uuid()
        pkg_info = objects.VnfPkgInfoV2(
            id=uuidutils.generate_uuid(),
            vnfdId=req_vnfd_id,
            vnfProvider="provider_1",
            vnfProductName="product_1",
            vnfSoftwareVersion="software version",
            vnfdVersion="vnfd version",
            operationalState="DISABLED"
        )

        mocked_get_vnf_package_info_vnfd.return_value = pkg_info

        body = {"vnfdId": req_vnfd_id}

        self.assertRaises(sol_ex.VnfdIdNotEnabled,
            self.controller.update, request=self.request, id=inst.id,
            body=body)

    def test_update_not_exist_vnfc_info_id(self):
        inst = objects.VnfInstanceV2(
            # required fields
            id=uuidutils.generate_uuid(),
            vnfdId=uuidutils.generate_uuid(),
            vnfProvider='provider',
            vnfProductName='product name',
            vnfSoftwareVersion='software version',
            vnfdVersion='vnfd version',
            instantiationState='INSTANTIATED'
        )
        inst.instantiatedVnfInfo = objects.VnfInstanceV2_InstantiatedVnfInfo(
            flavourId='small',
            vnfState='STARTED',
            vnfcInfo=[
                objects.VnfcInfoV2(
                    id="VDU1-vnfc_res_info_id_VDU1",
                    vduId="VDU1",
                    vnfcResourceInfoId="vnfc_res_info_id_VDU1",
                    vnfcState="STARTED"
                )
            ]
        )
        inst.create(self.context)

        body = {
            "vnfcInfoModifications": [
                {
                    "id": "VDU2-vnfc_res_info_id_VDU2",
                    "vnfcConfigurableProperties": {"key": "value"}
                }
            ]
        }

        self.assertRaises(sol_ex.SolValidationError,
            self.controller.update, request=self.request, id=inst.id,
            body=body)

    @mock.patch.object(conductor_rpc_v2.VnfLcmRpcApiV2, 'modify_vnfinfo')
    def test_update_202(self, mock_modify):
        inst = objects.VnfInstanceV2(
            # required fields
            id=uuidutils.generate_uuid(),
            vnfdId=uuidutils.generate_uuid(),
            vnfProvider='provider',
            vnfProductName='product name',
            vnfSoftwareVersion='software version',
            vnfdVersion='vnfd version',
            instantiationState='INSTANTIATED'
        )
        inst.instantiatedVnfInfo = objects.VnfInstanceV2_InstantiatedVnfInfo(
            flavourId='small',
            vnfState='STARTED',
            vnfcInfo=[
                objects.VnfcInfoV2(
                    id="VDU1-vnfc_res_info_id_VDU1",
                    vduId="VDU1",
                    vnfcResourceInfoId="vnfc_res_info_id_VDU1",
                    vnfcState="STARTED"
                )
            ]
        )
        inst.create(self.context)

        body = {
            "vnfcInfoModifications": [
                {
                    "id": "VDU1-vnfc_res_info_id_VDU1",
                    "vnfcConfigurableProperties": {"key": "value"}
                }
            ]
        }
        result = self.controller.update(
            request=self.request, id=inst.id, body=body)
        self.assertEqual(202, result.status)

    def test_change_ext_conn_not_instantiated(self):
        inst_id, _ = self._create_inst_and_lcmocc('NOT_INSTANTIATED',
            fields.LcmOperationStateType.COMPLETED)

        self.assertRaises(sol_ex.VnfInstanceIsNotInstantiated,
            self.controller.change_ext_conn, request=self.request, id=inst_id,
            body=_change_ext_conn_req_example)

    def test_change_ext_conn_lcmocc_in_progress(self):
        inst_id, _ = self._create_inst_and_lcmocc('INSTANTIATED',
            fields.LcmOperationStateType.FAILED_TEMP)

        self.assertRaises(sol_ex.OtherOperationInProgress,
            self.controller.change_ext_conn, request=self.request, id=inst_id,
            body=_change_ext_conn_req_example)

    @mock.patch.object(conductor_rpc_v2.VnfLcmRpcApiV2, 'start_lcm_op')
    def test_change_ext_conn_202(self, mock_start):
        inst_id, _ = self._create_inst_and_lcmocc('INSTANTIATED',
            fields.LcmOperationStateType.COMPLETED)

        result = self.controller.change_ext_conn(
            request=self.request, id=inst_id,
            body=_change_ext_conn_req_example)
        self.assertEqual(202, result.status)

    def test_heal_not_instantiated(self):
        inst_id, _ = self._create_inst_and_lcmocc('NOT_INSTANTIATED',
            fields.LcmOperationStateType.COMPLETED)
        body = {"cause": "Healing VNF instance"}

        self.assertRaises(sol_ex.VnfInstanceIsNotInstantiated,
            self.controller.heal, request=self.request, id=inst_id,
            body=body)

    def test_heal_lcmocc_in_progress(self):
        inst_id, _ = self._create_inst_and_lcmocc('INSTANTIATED',
            fields.LcmOperationStateType.FAILED_TEMP)
        body = {"cause": "Healing VNF instance"}

        self.assertRaises(sol_ex.OtherOperationInProgress,
            self.controller.heal, request=self.request, id=inst_id,
            body=body)

    @mock.patch.object(conductor_rpc_v2.VnfLcmRpcApiV2, 'start_lcm_op')
    def test_heal_202(self, mock_start):
        inst_id, _ = self._create_inst_and_lcmocc('INSTANTIATED',
            fields.LcmOperationStateType.COMPLETED)
        body = {"cause": "Healing VNF instance"}

        result = self.controller.heal(request=self.request, id=inst_id,
                                      body=body)
        self.assertEqual(202, result.status)

    def _prepare_db_for_heal_param_check(self):
        inst = objects.VnfInstanceV2(
            # required fields
            id=uuidutils.generate_uuid(),
            vnfdId=uuidutils.generate_uuid(),
            vnfProvider='provider',
            vnfProductName='product name',
            vnfSoftwareVersion='software version',
            vnfdVersion='vnfd version',
            instantiationState='INSTANTIATED'
        )
        inst.instantiatedVnfInfo = objects.VnfInstanceV2_InstantiatedVnfInfo(
            flavourId='small',
            vnfState='STARTED',
            vnfcInfo=[
                objects.VnfcInfoV2(
                    id="VDU2-vnfc_res_info_id_VDU2",
                    vduId="VDU2",
                    vnfcResourceInfoId="vnfc_res_info_id_VDU2",
                    vnfcState="STARTED"
                ),
                objects.VnfcInfoV2(
                    id="VDU1-vnfc_res_info_id_VDU1",
                    vduId="VDU1",
                    vnfcResourceInfoId="vnfc_res_info_id_VDU1",
                    vnfcState="STARTED"
                ),
                objects.VnfcInfoV2(
                    id="VDU1-vnfc_res_info_id_VDU2",
                    vduId="VDU1",
                    vnfcResourceInfoId="vnfc_res_info_id_VDU2",
                    vnfcState="STARTED"
                ),
            ]
        )
        inst.create(self.context)

        return inst.id

    def test_heal_invalid_additional_params(self):
        inst_id = self._prepare_db_for_heal_param_check()
        body = {
            "additionalParams": {"all": "string"}
        }

        self.assertRaises(sol_ex.SolValidationError,
            self.controller.heal, request=self.request, id=inst_id,
            body=body)

    def test_heal_invalid_vnfcinstance_id(self):
        inst_id = self._prepare_db_for_heal_param_check()
        body = {
            "vnfcInstanceId": [
                "VDU2-vnfc_res_info_id_VDU2",
                "VDU2-vnfc_res_info_id_VDU1"
            ]
        }

        self.assertRaises(sol_ex.SolValidationError,
            self.controller.heal, request=self.request, id=inst_id,
            body=body)


@ddt.ddt
class TestVnflcmV2EnhancedPolicy(TestVnflcmV2):

    def setUp(self):
        super(TestVnflcmV2EnhancedPolicy, self).setUp()
        CONF.set_override(
            "enhanced_tacker_policy", True, group='oslo_policy')

    def _create_inst_and_lcmocc(self, inst_state, op_state,
                                vnf_inst_updates=None,
                                tenant=None):
        inst, lcmocc = self._set_inst_and_lcmocc(
            inst_state, op_state, vnf_inst_updates=vnf_inst_updates)
        if tenant:
            inst.instantiatedVnfInfo = (
                objects.VnfInstanceV2_InstantiatedVnfInfo(
                    flavourId='fake_flavour_id',
                    vnfState='STARTED',
                    metadata={'tenant': 'tenant_A'}))
        inst.create(self.context)
        lcmocc.create(self.context)

        return inst.id, lcmocc.id

    def _set_inst_and_lcmocc(
            self, inst_state, op_state, vnf_inst_updates=None):
        vnf_inst_fields = {
            # required fields
            'id': uuidutils.generate_uuid(),
            'vnfdId': uuidutils.generate_uuid(),
            'vnfProvider': 'provider',
            'vnfProductName': 'product name',
            'vnfSoftwareVersion': 'software version',
            'vnfdVersion': 'vnfd version',
            'instantiationState': inst_state
        }
        if vnf_inst_updates:
            vnf_inst_fields.update(vnf_inst_updates)
        inst = objects.VnfInstanceV2(**vnf_inst_fields)

        req = {"flavourId": "simple"}  # instantiate request
        lcmocc = objects.VnfLcmOpOccV2(
            # required fields
            id=uuidutils.generate_uuid(),
            operationState=op_state,
            stateEnteredTime=datetime.utcnow(),
            startTime=datetime.utcnow(),
            vnfInstanceId=inst.id,
            operation=fields.LcmOperationType.INSTANTIATE,
            isAutomaticInvocation=False,
            isCancelPending=False,
            operationParams=req
        )

        return inst, lcmocc

    def _prepare_db_for_scale_param_check(self, scale_status,
            max_scale_levels, vnf_inst_updates=None, tenant=None):
        vnf_inst_fields = {
            # required fields
            'id': uuidutils.generate_uuid(),
            'vnfdId': uuidutils.generate_uuid(),
            'vnfProvider': 'provider',
            'vnfProductName': 'product name',
            'vnfSoftwareVersion': 'software version',
            'vnfdVersion': 'vnfd version',
            'instantiationState': 'INSTANTIATED'
        }
        if vnf_inst_updates:
            vnf_inst_fields.update(vnf_inst_updates)
        inst = objects.VnfInstanceV2(**vnf_inst_fields)
        instantiated_vnf_info = {
            'flavourId': 'small',
            'vnfState': 'STARTED',
            'scaleStatus': scale_status,
            'maxScaleLevels': max_scale_levels,
        }
        if tenant:
            instantiated_vnf_info.update({'metadata': {'tenant': tenant}})
        inst.instantiatedVnfInfo = objects.VnfInstanceV2_InstantiatedVnfInfo(
            **instantiated_vnf_info
        )
        inst.create(self.context)

        return inst.id

    def _prepare_db_for_change_vnfpkg_param(
            self, vnf_inst_updates=None, tenant=None):
        vnf_inst_fields = {
            # required fields
            'id': uuidutils.generate_uuid(),
            'vnfdId': uuidutils.generate_uuid(),
            'vnfProvider': 'provider',
            'vnfProductName': 'product name',
            'vnfSoftwareVersion': 'software version',
            'vnfdVersion': 'vnfd version',
            'instantiationState': 'INSTANTIATED'
        }
        if vnf_inst_updates:
            vnf_inst_fields.update(vnf_inst_updates)
        inst = objects.VnfInstanceV2(**vnf_inst_fields)
        inst.instantiatedVnfInfo = objects.VnfInstanceV2_InstantiatedVnfInfo(
            flavourId='small',
            vnfState='STARTED',
            vnfcResourceInfo=[
                objects.VnfcResourceInfoV2(
                    id="VDU1-vnfc_res_info_id_VDU1",
                    vduId="VDU1"
                )
            ]
        )
        if tenant:
            inst.instantiatedVnfInfo.metadata = {'tenant': tenant}
        if not vnf_inst_updates:
            inst.vimConnectionInfo = {
                "vim1": objects.VimConnectionInfo.from_dict(
                    _vim_connection_info_example)}
        inst.create(self.context)
        return inst.id

    def _fake_request(self, roles):
        request = requests.Request()
        ctx = context.Context('fake', 'fake', roles=roles)
        ctx.api_version = api_version.APIVersion("2.0.0")
        request.context = ctx
        return request

    def _overwrite_policy(self, rules):
        policy.set_rules(oslo_policy.Rules.from_dict(rules), overwrite=True)

    @mock.patch.object(inst_utils, 'get_inst_all')
    def test_index(self, mock_inst):
        request = requests.Request()
        request.context = self.context
        request.GET = {'filter': f'(eq,vnfdId,{SAMPLE_VNFD_ID})'}
        mock_inst.return_value = [objects.VnfInstanceV2(
            id='inst-1', vnfdId=SAMPLE_VNFD_ID, vnfProvider='Company',
            instantiationState='NOT_INSTANTIATED')]

        result = self.controller.index(request)
        self.assertEqual(200, result.status)

        # no filter
        request.GET = {}
        result = self.controller.index(request)
        self.assertEqual(200, result.status)

    @mock.patch.object(inst_utils, 'get_inst')
    def test_show(self, mock_inst):
        request = requests.Request()
        request.context = self.context
        mock_inst.return_value = objects.VnfInstanceV2(
            id='inst-1', vnfdId=SAMPLE_VNFD_ID, vnfProvider='Company',
            instantiationState='NOT_INSTANTIATED')
        result = self.controller.show(request, 'inst-1')
        self.assertEqual(200, result.status)

    @ddt.data(*get_test_data_policy_instantiate())
    @ddt.unpack
    @mock.patch.object(vim_utils, 'get_vim')
    @mock.patch.object(conductor_rpc_v2.VnfLcmRpcApiV2, 'start_lcm_op')
    def test_instantiate_enhanced_policy(self, mock_start,
            mock_vim, vnf_instance_updates, rules, roles,
            expected_status_code):
        self._overwrite_policy(rules)
        inst_id, _ = self._create_inst_and_lcmocc('NOT_INSTANTIATED',
            fields.LcmOperationStateType.COMPLETED,
            vnf_inst_updates=vnf_instance_updates)
        body = {
            "flavourId": "small",
            "vimConnectionInfo": {
                "vim1": {
                    "vimId": "vim_id_1",
                    "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_3"
                }
            }
        }
        mock_vim.return_value = objects.VimConnectionInfo.from_dict(
            _vim_connection_info_example)
        try:
            result = self.controller.instantiate(
                request=self._fake_request(roles), id=inst_id, body=body)
            self.assertEqual(expected_status_code, result.status)
        except PolicyNotAuthorized:
            if expected_status_code != http_client.FORBIDDEN:
                raise

    @mock.patch.object(vim_utils, 'get_vim')
    @mock.patch.object(conductor_rpc_v2.VnfLcmRpcApiV2, 'start_lcm_op')
    def test_instantiate_add_area(self, mock_start, mock_vim):
        inst_id, _ = self._create_inst_and_lcmocc(
            'NOT_INSTANTIATED', fields.LcmOperationStateType.COMPLETED)
        body = {
            "flavourId": "small",
            "vimConnectionInfo": {
                "vim1": {
                    "vimId": "vim_id_1",
                    "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_3"
                }
            }
        }
        vim = copy.copy(_vim_connection_info_example)
        vim.update({'extra': {'area': 'area_A@region_A'}})
        mock_vim.return_value = objects.VimConnectionInfo.from_dict(vim)
        result = self.controller.instantiate(
            request=self.request, id=inst_id, body=body)
        self.assertEqual(202, result.status)

    @mock.patch.object(vim_utils, 'get_vim')
    @mock.patch.object(conductor_rpc_v2.VnfLcmRpcApiV2, 'start_lcm_op')
    def test_instantiate_with_area_in_vim_conn_info(
            self, mock_start, mock_vim):
        inst_id, _ = self._create_inst_and_lcmocc(
            'NOT_INSTANTIATED', fields.LcmOperationStateType.COMPLETED)
        body = {
            "flavourId": "small",
            "vimConnectionInfo": {
                "vim1": {
                    "vimId": "vim_id_1",
                    "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_3",
                    "interfaceInfo": {"endpoint": "http://127.0.0.1/identity"},
                    "accessInfo": {
                        "username": "nfv_user",
                        "region": "RegionOne",
                        "password": "devstack",
                        "project": "nfv",
                        "projectDomain": "Default",
                        "userDomain": "Default"
                    },
                    "extra": {"area": "area_A@region_A"}
                }
            }
        }
        vim = copy.copy(_vim_connection_info_example)
        mock_vim.return_value = objects.VimConnectionInfo.from_dict(vim)
        result = self.controller.instantiate(
            request=self.request, id=inst_id, body=body)
        self.assertEqual(202, result.status)

    @ddt.data(*get_test_data_policy_vnf_instantiated(
        'terminate', http_client.ACCEPTED))
    @ddt.unpack
    @mock.patch.object(conductor_rpc_v2.VnfLcmRpcApiV2, 'start_lcm_op')
    def test_terminate_enhanced_policy(self, mock_start, vnf_instance_updates,
            tenant, rules, roles, expected_status_code):
        self._overwrite_policy(rules)
        inst_id, _ = self._create_inst_and_lcmocc(
            'INSTANTIATED', fields.LcmOperationStateType.COMPLETED,
            vnf_inst_updates=vnf_instance_updates,
            tenant=tenant)
        body = {"terminationType": "FORCEFUL"}
        try:
            result = self.controller.terminate(
                request=self._fake_request(roles), id=inst_id,
                body=body)
            self.assertEqual(202, result.status)
        except PolicyNotAuthorized:
            if expected_status_code != http_client.FORBIDDEN:
                raise

    @ddt.data(*get_test_data_policy_vnf_instantiated(
        'heal', http_client.ACCEPTED))
    @ddt.unpack
    @mock.patch.object(conductor_rpc_v2.VnfLcmRpcApiV2, 'start_lcm_op')
    def test_heal_enhanced_policy(self, mock_start, vnf_instance_updates,
            tenant, rules, roles, expected_status_code):
        self._overwrite_policy(rules)
        inst_id, _ = self._create_inst_and_lcmocc('INSTANTIATED',
            fields.LcmOperationStateType.COMPLETED,
            vnf_inst_updates=vnf_instance_updates,
            tenant=tenant)
        body = {"cause": "Healing VNF instance"}
        try:
            result = self.controller.heal(
                request=self._fake_request(roles), id=inst_id,
                body=body)
            self.assertEqual(http_client.ACCEPTED, result.status)
        except PolicyNotAuthorized:
            if expected_status_code != http_client.FORBIDDEN:
                raise

    @ddt.data(*get_test_data_policy_delete())
    @ddt.unpack
    @mock.patch.object(nfvo_client.NfvoClient, 'send_inst_delete_notification')
    def test_delete_enhanced_policy(self, mock_delete, vnf_instance_updates,
            rules, roles, expected_status_code):
        self._overwrite_policy(rules)
        inst_id, _ = self._create_inst_and_lcmocc('NOT_INSTANTIATED',
            fields.LcmOperationStateType.COMPLETED,
            vnf_inst_updates=vnf_instance_updates)
        try:
            result = self.controller.delete(
                self._fake_request(roles), id=inst_id)
            self.assertEqual(http_client.NO_CONTENT, result.status)
        except PolicyNotAuthorized:
            if expected_status_code != http_client.FORBIDDEN:
                raise

    @ddt.data(*get_test_data_policy_vnf_instantiated(
        'show', http_client.OK))
    @ddt.unpack
    @mock.patch.object(inst_utils, 'get_inst')
    def test_show_enhanced_policy(self, mock_inst, vnf_instance_updates,
            tenant, rules, roles, expected_status_code):
        self._overwrite_policy(rules)
        mock_inst.return_value = objects.VnfInstanceV2(
            id='inst-1', vnfdId=SAMPLE_VNFD_ID,
            instantiationState='NOT_INSTANTIATED', **vnf_instance_updates)
        try:
            result = self.controller.show(self._fake_request(roles), 'inst-1')
            self.assertEqual(200, result.status)
        except PolicyNotAuthorized:
            if expected_status_code != http_client.FORBIDDEN:
                raise

    @ddt.data(*get_test_data_policy_vnf_instantiated(
        'scale', http_client.ACCEPTED))
    @ddt.unpack
    @mock.patch.object(conductor_rpc_v2.VnfLcmRpcApiV2, 'start_lcm_op')
    def test_scale_enhanced_policy(self, mock_start, vnf_instance_updates,
            tenant, rules, roles, expected_status_code):
        self._overwrite_policy(rules)
        scale_status = [
            objects.ScaleInfoV2(
                aspectId="aspect_1",
                scaleLevel=1
            )
        ]
        max_scale_levels = [
            objects.ScaleInfoV2(
                aspectId="aspect_1",
                scaleLevel=3
            )
        ]
        inst_id = self._prepare_db_for_scale_param_check(
            scale_status, max_scale_levels,
            vnf_inst_updates=vnf_instance_updates,
            tenant=tenant)
        body = {"aspectId": "aspect_1", "type": "SCALE_OUT",
                "numberOfSteps": 1}

        try:
            result = self.controller.scale(
                request=self._fake_request(roles),
                id=inst_id,
                body=body)
            self.assertEqual(http_client.ACCEPTED, result.status)
        except PolicyNotAuthorized:
            if expected_status_code != http_client.FORBIDDEN:
                raise

    @ddt.data(*get_test_data_policy_vnf_instantiated(
        'update', http_client.ACCEPTED))
    @ddt.unpack
    @mock.patch.object(conductor_rpc_v2.VnfLcmRpcApiV2, 'modify_vnfinfo')
    def test_update_enhanced_policy(self, mock_modify, vnf_instance_updates,
            tenant, rules, roles, expected_status_code):
        self._overwrite_policy(rules)
        inst_fields = {
            # required fields
            'id': uuidutils.generate_uuid(),
            'vnfdId': uuidutils.generate_uuid(),
            'vnfProvider': 'provider',
            'vnfProductName': 'product name',
            'vnfSoftwareVersion': 'software version',
            'vnfdVersion': 'vnfd version',
            'instantiationState': 'INSTANTIATED'
        }
        if vnf_instance_updates:
            inst_fields.update(vnf_instance_updates)
        inst = objects.VnfInstanceV2(**inst_fields)
        inst.instantiatedVnfInfo = objects.VnfInstanceV2_InstantiatedVnfInfo(
            flavourId='small',
            vnfState='STARTED',
            vnfcInfo=[
                objects.VnfcInfoV2(
                    id="VDU1-vnfc_res_info_id_VDU1",
                    vduId="VDU1",
                    vnfcResourceInfoId="vnfc_res_info_id_VDU1",
                    vnfcState="STARTED"
                )
            ]
        )
        if tenant:
            inst.instantiatedVnfInfo.metadata = {'tenant': tenant}
        # inst.instantiatedVnfInfo = objects.VnfInstanceV2_InstantiatedVnfInfo(
        #     flavourId='fake_flavour_id',
        #     vnfState='STARTED',
        #     metadata={'tenant': tenant}
        # )
        inst.create(self.context)

        body = {
            "vnfcInfoModifications": [
                {
                    "id": "VDU1-vnfc_res_info_id_VDU1",
                    "vnfcConfigurableProperties": {"key": "value"}
                }
            ]
        }
        try:
            result = self.controller.update(
                request=self._fake_request(roles), id=inst.id, body=body)
            self.assertEqual(202, result.status)
        except PolicyNotAuthorized:
            if expected_status_code != http_client.FORBIDDEN:
                raise

    @ddt.data(*get_test_data_policy_vnf_instantiated(
        'change_ext_conn', http_client.ACCEPTED))
    @ddt.unpack
    @mock.patch.object(conductor_rpc_v2.VnfLcmRpcApiV2, 'start_lcm_op')
    def test_change_ext_conn_enhanced_policy(self, mock_start,
            vnf_instance_updates, tenant, rules, roles,
            expected_status_code):
        self._overwrite_policy(rules)
        inst_id, _ = self._create_inst_and_lcmocc('INSTANTIATED',
            fields.LcmOperationStateType.COMPLETED,
            vnf_inst_updates=vnf_instance_updates,
            tenant=tenant)
        try:
            result = self.controller.change_ext_conn(
                request=self._fake_request(roles), id=inst_id,
                body=_change_ext_conn_req_example)
            self.assertEqual(202, result.status)
        except PolicyNotAuthorized:
            if expected_status_code != http_client.FORBIDDEN:
                raise

    @ddt.data(*get_test_data_policy_vnf_instantiated(
        'change_vnfpkg', http_client.ACCEPTED))
    @ddt.unpack
    @mock.patch.object(nfvo_client.NfvoClient, 'get_vnf_package_info_vnfd')
    @mock.patch.object(conductor_rpc_v2.VnfLcmRpcApiV2, 'start_lcm_op')
    def test_change_vnfpkg_pkg_enhanced_policy(
            self, mock_start, mocked_get_vnf_package_info_vnfd,
            vnf_instance_updates, tenant, rules, roles,
            expected_status_code):
        self._overwrite_policy(rules)
        vnfd_id = uuidutils.generate_uuid()
        inst_id = self._prepare_db_for_change_vnfpkg_param(
            vnf_inst_updates=vnf_instance_updates, tenant=tenant)
        body = {
            "vnfdId": vnfd_id,
            "additionalParams": {
                "upgrade_type": "RollingUpdate",
                "vdu_params": [{
                    "vdu_id": "VDU1",
                    "new_vnfc_param": {
                        "username": "test",
                        "password": "test",
                        "cp_name": "VDU1_CP1"
                    },
                    "old_vnfc_param": {
                        "username": "test",
                        "password": "test",
                        "cp_name": "VDU1_CP1"
                    }
                }]
            }
        }
        pkg_info = objects.VnfPkgInfoV2(
            id=uuidutils.generate_uuid(),
            vnfdId=vnfd_id,
            vnfProvider="provider",
            vnfProductName="product",
            vnfSoftwareVersion="software version",
            vnfdVersion="vnfd version",
            operationalState="ENABLED"
        )
        mocked_get_vnf_package_info_vnfd.return_value = pkg_info
        try:
            result = self.controller.change_vnfpkg(
                request=self._fake_request(roles), id=inst_id, body=body)
            self.assertEqual(202, result.status)
        except PolicyNotAuthorized:
            if expected_status_code != http_client.FORBIDDEN:
                raise

    @ddt.data(*get_test_data_policy_index())
    @ddt.unpack
    @mock.patch.object(inst_utils, 'get_inst_all')
    def test_index_enhanced_policy(self, mock_inst, vnf_instance_list,
            rules, roles, expected_vnf_inst_ids):
        self._overwrite_policy(rules)
        mock_inst.return_value = vnf_instance_list
        request = self._fake_request(roles)
        request.GET = {}

        result = self.controller.index(request)
        self.assertEqual(200, result.status)
        result = result.body
        self.assertEqual(
            expected_vnf_inst_ids, [inst.get('id') for inst in result])
