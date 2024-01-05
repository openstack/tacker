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
from datetime import datetime
import os
from unittest import mock

from oslo_utils import uuidutils

from tacker import context
from tacker.objects import vnf_package
from tacker.objects import vnf_package_vnfd
from tacker.sol_refactored.api import api_version
from tacker.sol_refactored.common import config
from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.common import lcm_op_occ_utils as lcmocc_utils
from tacker.sol_refactored.common import vnf_instance_utils as inst_utils
from tacker.sol_refactored.nfvo import glance_utils
from tacker.sol_refactored.nfvo import local_nfvo
from tacker.sol_refactored import objects
from tacker.sol_refactored.objects.v2 import fields
from tacker.tests import base
from tacker.tests import utils


SAMPLE_VNFD_ID = "b1bb0ce7-ebca-4fa7-95ed-4840d7000000"
SAMPLE_VNFPKG_ID = "d04753f1-493e-17dc-e4a9-65f73b3ccc24"
_inst_grant_req_example = {
    "vnfInstanceId": "2d004394-d0f0-406d-845a-2b148f91039a",
    "vnfLcmOpOccId": "34da9ba7-6ab1-4d8d-a68a-68892e56642c",
    "vnfdId": "b1bb0ce7-ebca-4fa7-95ed-4840d7000000",
    "flavourId": "simple",
    "operation": "INSTANTIATE",
    "isAutomaticInvocation": False,
    "instantiationLevelId": "instantiation_level_2",
    "addResources": [{
        "id": "6396a2a1-7e36-49bd-8fff-2d46394a6b29",
        "type": "COMPUTE",
        "resourceTemplateId": "VDU1"
    }, {
        "id": "VDU1_CP1-6396a2a1-7e36-49bd-8fff-2d46394a6b29",
        "type": "LINKPORT",
        "resourceTemplateId": "VDU1_CP1"
    }, {
        "id": "VDU1_CP2-6396a2a1-7e36-49bd-8fff-2d46394a6b29",
        "type": "LINKPORT",
        "resourceTemplateId": "VDU1_CP2"
    }, {
        "id": "VDU1_CP3-6396a2a1-7e36-49bd-8fff-2d46394a6b29",
        "type": "LINKPORT",
        "resourceTemplateId": "VDU1_CP3"
    }, {
        "id": "VDU1_CP5-6396a2a1-7e36-49bd-8fff-2d46394a6b29",
        "type": "LINKPORT",
        "resourceTemplateId": "VDU1_CP5"
    }, {
        "id": "VDU1_CP4-6396a2a1-7e36-49bd-8fff-2d46394a6b29",
        "type": "LINKPORT",
        "resourceTemplateId": "VDU1_CP4"
    }, {
        "id": "VirtualStorage-6396a2a1-7e36-49bd-8fff-2d46394a6b29",
        "type": "STORAGE",
        "resourceTemplateId": "VirtualStorage"
    }, {
        "id": "39e0af93-aba5-4a15-9231-cdaa4149738e",
        "type": "COMPUTE",
        "resourceTemplateId": "VDU1"
    }, {
        "id": "VDU1_CP1-39e0af93-aba5-4a15-9231-cdaa4149738e",
        "type": "LINKPORT",
        "resourceTemplateId": "VDU1_CP1"
    }, {
        "id": "VDU1_CP2-39e0af93-aba5-4a15-9231-cdaa4149738e",
        "type": "LINKPORT",
        "resourceTemplateId": "VDU1_CP2"
    }, {
        "id": "VDU1_CP3-39e0af93-aba5-4a15-9231-cdaa4149738e",
        "type": "LINKPORT",
        "resourceTemplateId": "VDU1_CP3"
    }, {
        "id": "VDU1_CP5-39e0af93-aba5-4a15-9231-cdaa4149738e",
        "type": "LINKPORT",
        "resourceTemplateId": "VDU1_CP5"
    }, {
        "id": "VDU1_CP4-39e0af93-aba5-4a15-9231-cdaa4149738e",
        "type": "LINKPORT",
        "resourceTemplateId": "VDU1_CP4"
    }, {
        "id": "VirtualStorage-39e0af93-aba5-4a15-9231-cdaa4149738e",
        "type": "STORAGE",
        "resourceTemplateId": "VirtualStorage"
    }, {
        "id": "8a3ab83f-187c-4feb-b1b5-a6bf587130fa",
        "type": "COMPUTE",
        "resourceTemplateId": "VDU1"
    }, {
        "id": "VDU1_CP1-8a3ab83f-187c-4feb-b1b5-a6bf587130fa",
        "type": "LINKPORT",
        "resourceTemplateId": "VDU1_CP1"
    }, {
        "id": "VDU1_CP2-8a3ab83f-187c-4feb-b1b5-a6bf587130fa",
        "type": "LINKPORT",
        "resourceTemplateId": "VDU1_CP2"
    }, {
        "id": "VDU1_CP3-8a3ab83f-187c-4feb-b1b5-a6bf587130fa",
        "type": "LINKPORT",
        "resourceTemplateId": "VDU1_CP3"
    }, {
        "id": "VDU1_CP5-8a3ab83f-187c-4feb-b1b5-a6bf587130fa",
        "type": "LINKPORT",
        "resourceTemplateId": "VDU1_CP5"
    }, {
        "id": "VDU1_CP4-8a3ab83f-187c-4feb-b1b5-a6bf587130fa",
        "type": "LINKPORT",
        "resourceTemplateId": "VDU1_CP4"
    }, {
        "id": "VirtualStorage-8a3ab83f-187c-4feb-b1b5-a6bf587130fa",
        "type": "STORAGE",
        "resourceTemplateId": "VirtualStorage"
    }, {
        "id": "3f2385fa-3f13-436d-b93a-47c62ef237e0",
        "type": "COMPUTE",
        "resourceTemplateId": "VDU2"
    }, {
        "id": "VDU2_CP5-3f2385fa-3f13-436d-b93a-47c62ef237e0",
        "type": "LINKPORT",
        "resourceTemplateId": "VDU2_CP5"
    }, {
        "id": "VDU2_CP2-3f2385fa-3f13-436d-b93a-47c62ef237e0",
        "type": "LINKPORT",
        "resourceTemplateId": "VDU2_CP2"
    }, {
        "id": "VDU2_CP1-3f2385fa-3f13-436d-b93a-47c62ef237e0",
        "type": "LINKPORT",
        "resourceTemplateId": "VDU2_CP1"
    }, {
        "id": "VDU2_CP3-3f2385fa-3f13-436d-b93a-47c62ef237e0",
        "type": "LINKPORT",
        "resourceTemplateId": "VDU2_CP3"
    }, {
        "id": "VDU2_CP4-3f2385fa-3f13-436d-b93a-47c62ef237e0",
        "type": "LINKPORT",
        "resourceTemplateId": "VDU2_CP4"
    }, {
        "id": "a411a968-c00b-4d46-8553-a37f3537391e",
        "type": "VL",
        "resourceTemplateId": "internalVL2"
    }, {
        "id": "f06ba7cf-f5af-4856-8d3a-56b331d1b9a5",
        "type": "VL",
        "resourceTemplateId": "internalVL3"
    }],
    "placementConstraints": [{
        "affinityOrAntiAffinity": "ANTI_AFFINITY",
        "scope": "NFVI_NODE",
        "resource": [{
            "idType": "GRANT",
            "resourceId": "6396a2a1-7e36-49bd-8fff-2d46394a6b29"
        }, {
            "idType": "GRANT",
            "resourceId": "39e0af93-aba5-4a15-9231-cdaa4149738e"
        }, {
            "idType": "GRANT",
            "resourceId": "8a3ab83f-187c-4feb-b1b5-a6bf587130fa"
        }, {
            "idType": "GRANT",
            "resourceId": "3f2385fa-3f13-436d-b93a-47c62ef237e0"
        }]
    }],
    "_links": {
        "vnfLcmOpOcc": {
            "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_lcm_op_occs/"
                    "34da9ba7-6ab1-4d8d-a68a-68892e56642c"
        },
        "vnfInstance": {
            "href": "http://127.0.0.1:9890/vnflcm/v2/vnf_instances/"
                    "2d004394-d0f0-406d-845a-2b148f91039a"
        }
    }
}

_inst_req_example = {
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

_change_vnfkg_grant_req_example = {
    'vnfInstanceId': '5eb4b136-6dac-4af1-b880-4e5eea6ec358',
    'vnfLcmOpOccId': '4ed07654-d459-4ae7-85c5-bed63c563646',
    'vnfdId': '1440b128-be42-4eed-9c4b-7df4b59c35d2',
    'dstVnfdId': 'b1bb0ce7-ebca-4fa7-95ed-4840d7000000',
    'flavourId': 'simple',
    'operation': 'CHANGE_VNFPKG',
    'isAutomaticInvocation': False,
    'addResources': [{
        'id': 'aab5201a-7516-41d9-9bf3-6a2579df7004',
        'type': 'COMPUTE',
        'resourceTemplateId': 'VDU2'
    }, {
        'id': '36027157-a86b-4294-95e8-4ebd4bd91abf',
        'type': 'COMPUTE',
        'resourceTemplateId': 'VDU1'
    }, {
        'id': 'VirtualStorage-36027157-a86b-4294-95e8-4ebd4bd91abf',
        'type': 'STORAGE',
        'resourceTemplateId': 'VirtualStorage'
    }, {
        'id': 'cf40bb5a-046d-4113-b69b-9e34878ba781',
        'type': 'COMPUTE',
        'resourceTemplateId': 'VDU1'
    }, {
        'id': 'VirtualStorage-cf40bb5a-046d-4113-b69b-9e34878ba781',
        'type': 'STORAGE',
        'resourceTemplateId': 'VirtualStorage'
    }, {
        'id': '7c093596-c98c-40a0-b2cb-f0c30ce6fb87',
        'type': 'COMPUTE',
        'resourceTemplateId': 'VDU1'
    }],
    'removeResources': [{
        'id': '0c8c248d-69cd-4dde-8b75-9791a02899c8',
        'type': 'COMPUTE',
        'resourceTemplateId': 'VDU2',
        'resource': {
            'resourceId': 'res_id_VDU2',
            'vimLevelResourceType': 'OS::Nova::Server'
        }
    }, {
        'id': '374dfdae-6add-4a96-a37f-95b8e1b3f79b',
        'type': 'COMPUTE',
        'resourceTemplateId': 'VDU1',
        'resource': {
            'resourceId': 'res_id_VDU1_1',
            'vimLevelResourceType': 'OS::Nova::Server'
        }
    }, {
        'id': 'VirtualStorage-374dfdae-6add-4a96-a37f-95b8e1b3f79b',
        'type': 'STORAGE',
        'resourceTemplateId': 'VirtualStorage',
        'resource': {
            'resourceId': 'res_id_VirtualStorage_1',
            'vimLevelResourceType': 'OS::Cinder::Volume'
        }
    }, {
        'id': '4e601248-185f-4405-91bb-ea579c1b866b',
        'type': 'COMPUTE',
        'resourceTemplateId': 'VDU1',
        'resource': {
            'resourceId': 'res_id_VDU1_2',
            'vimLevelResourceType': 'OS::Nova::Server'
        }
    }, {
        'id': 'VirtualStorage-4e601248-185f-4405-91bb-ea579c1b866b',
        'type': 'STORAGE',
        'resourceTemplateId': 'VirtualStorage',
        'resource': {
            'resourceId': 'res_id_VirtualStorage_2',
            'vimLevelResourceType': 'OS::Cinder::Volume'
        }
    }, {
        'id': 'cd8bee39-a7b1-4652-8de4-56f5863c9157',
        'type': 'COMPUTE',
        'resourceTemplateId': 'VDU1',
        'resource': {
            'resourceId': 'res_id_VDU1_3',
            'vimLevelResourceType': 'OS::Nova::Server'
        }
    }],
    '_links': {
        'vnfLcmOpOcc': {
            'href': 'http://127.0.0.1:9890/vnflcm/v2/vnf_lcm_op_occs/'
                    '4ed07654-d459-4ae7-85c5-bed63c563646'
        },
        'vnfInstance': {
            'href': 'http://127.0.0.1:9890/vnflcm/v2/vnf_instances/'
                    '5eb4b136-6dac-4af1-b880-4e5eea6ec358'
        }
    }
}

_change_vnfpkg_example = {
    "vnfdId": '61723406-6634-2fc0-060a-0b11104d2667',
    "additionalParams": {
        "upgrade_type": "RollingUpdate",
        "lcm-operation-coordinate-old-vnf": "./Scripts/coordinate_old_vnf.py",
        "lcm-operation-coordinate-new-vnf": "./Scripts/coordinate_new_vnf.py",
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

CONF = config.CONF


class TestLocalNfvo(base.BaseTestCase):

    def setUp(self):
        super(TestLocalNfvo, self).setUp()
        objects.register_all()
        self.context = context.get_admin_context()
        CONF.vnf_package.vnf_package_csar_path = (
            '/opt/stack/data/tacker/vnfpackage/')
        self.context.api_version = api_version.APIVersion('2.0.0')
        self.local_nfvo = local_nfvo.LocalNfvo()

    def _sample_dir(self, name):
        return utils.test_sample("unit/sol_refactored/samples", name)

    def _get_vnfpkg_or_vnfd(
            self, type, state=fields.PackageOnboardingStateType.ONBOARDED):
        if type == 'vnfd':
            return vnf_package_vnfd.VnfPackageVnfd(
                id=uuidutils.generate_uuid(),
                package_uuid=SAMPLE_VNFPKG_ID, vnfd_id=SAMPLE_VNFD_ID,
                vnf_provider='provider', vnf_product_name='product',
                vnf_software_version='2.0', vnfd_version='3.3.1')
        else:
            return vnf_package.VnfPackage(
                id=SAMPLE_VNFPKG_ID,
                onboarding_state=state,
                operational_state=fields.PackageOperationalStateType.DISABLED)

    @mock.patch.object(vnf_package_vnfd.VnfPackageVnfd, 'get_by_id')
    @mock.patch.object(vnf_package.VnfPackage, 'get_by_id')
    def test_onboarded_show(self, mock_vnfpackage, mock_vnfd):
        mock_vnfd.return_value = self._get_vnfpkg_or_vnfd('vnfd')
        mock_vnfpackage.return_value = self._get_vnfpkg_or_vnfd('vnfpkg')
        result = self.local_nfvo.onboarded_show(self.context, SAMPLE_VNFD_ID)
        self.assertEqual(SAMPLE_VNFPKG_ID, result.id)
        self.assertEqual(SAMPLE_VNFD_ID, result.vnfdId)

    @mock.patch.object(vnf_package_vnfd.VnfPackageVnfd, 'get_by_id')
    @mock.patch.object(vnf_package.VnfPackage, 'get_by_id')
    def test_onboarded_show_vnfpackage_error(self, mock_vnfpackage, mock_vnfd):
        mock_vnfd.return_value = self._get_vnfpkg_or_vnfd('vnfd')
        self.assertRaises(
            sol_ex.VnfdIdNotFound, self.local_nfvo.onboarded_show,
            self.context, SAMPLE_VNFD_ID)

    @mock.patch.object(vnf_package_vnfd.VnfPackageVnfd, 'get_by_id')
    @mock.patch.object(vnf_package.VnfPackage, 'get_by_id')
    def test_onboarded_show_error(self, mock_vnfpackage, mock_vnfd):
        mock_vnfd.return_value = self._get_vnfpkg_or_vnfd('vnfd')
        mock_vnfpackage.return_value = self._get_vnfpkg_or_vnfd(
            'vnfpkg', fields.PackageOnboardingStateType.CREATED)
        self.assertRaises(
            sol_ex.VnfdIdNotFound, self.local_nfvo.onboarded_show,
            self.context, SAMPLE_VNFD_ID)

    @mock.patch.object(vnf_package_vnfd.VnfPackageVnfd, 'get_by_id')
    @mock.patch.object(os.path, 'isdir')
    def test_get_csar_dir(self, mock_isdir, mock_vnfd):
        mock_vnfd.return_value = self._get_vnfpkg_or_vnfd('vnfd')
        mock_isdir.return_value = True
        result = self.local_nfvo.get_csar_dir(self.context, SAMPLE_VNFD_ID)
        self.assertEqual(
            f'/opt/stack/data/tacker/vnfpackage/{SAMPLE_VNFPKG_ID}', result)

    @mock.patch.object(vnf_package_vnfd.VnfPackageVnfd, 'get_by_id')
    def test_get_csar_dir_vnfd_error(self, mock_vnfd):
        self.assertRaises(
            sol_ex.VnfdIdNotFound, self.local_nfvo.get_csar_dir,
            self.context, SAMPLE_VNFD_ID)

    @mock.patch.object(vnf_package_vnfd.VnfPackageVnfd, 'get_by_id')
    @mock.patch.object(os.path, 'isdir')
    def test_get_csar_dir_path_error(self, mock_isdir, mock_vnfd):
        mock_vnfd.return_value = self._get_vnfpkg_or_vnfd('vnfd')
        mock_isdir.return_value = False
        self.assertRaises(
            sol_ex.VnfdIdNotFound, self.local_nfvo.get_csar_dir,
            self.context, SAMPLE_VNFD_ID)

    @mock.patch.object(local_nfvo.LocalNfvo, 'get_csar_dir')
    def test_get_vnfd(self, mock_dir):
        mock_dir.return_value = self._sample_dir("sample1")
        result = self.local_nfvo.get_vnfd(self.context, SAMPLE_VNFD_ID)
        self.assertEqual(SAMPLE_VNFD_ID, result.vnfd_id)

    @mock.patch.object(local_nfvo.LocalNfvo, 'get_csar_dir')
    @mock.patch.object(lcmocc_utils, 'get_lcmocc')
    @mock.patch.object(glance_utils.GlanceClient, 'create_image')
    def test_instantiate_grant(self, mock_image, mock_lcmocc, mock_dir):
        grant_req = objects.GrantRequestV1.from_dict(_inst_grant_req_example)
        grant_res = objects.GrantV1(
            id=uuidutils.generate_uuid(),
            vnfInstanceId=grant_req.vnfInstanceId,
            vnfLcmOpOccId=grant_req.vnfLcmOpOccId
        )
        mock_dir.return_value = self._sample_dir("sample1")
        req = objects.InstantiateVnfRequest.from_dict(_inst_req_example)
        mock_lcmocc.return_value = objects.VnfLcmOpOccV2(
            # only set used members in the method
            operation=fields.LcmOperationType.INSTANTIATE,
            operationParams=req)
        mock_image.return_value = objects.GrantV1(
            id=uuidutils.generate_uuid()
        )
        self.local_nfvo.instantiate_grant(self.context, grant_req, grant_res)
        result = grant_res.to_dict()
        self.assertIsNotNone(result['addResources'])
        self.assertEqual(mock_image.return_value.id, result[
            'vimAssets']['softwareImages'][0]['vimSoftwareImageId'])

    @mock.patch.object(local_nfvo.LocalNfvo, 'get_csar_dir')
    @mock.patch.object(local_nfvo.LocalNfvo, '_get_vim_info')
    def test_instantiate_grant_no_vim_info(self, mock_vim_info, mock_dir):
        mock_dir.return_value = self._sample_dir("sample1")
        grant_req = objects.GrantRequestV1.from_dict(_inst_grant_req_example)
        grant_res = objects.GrantV1(
            id=uuidutils.generate_uuid(),
            vnfInstanceId=grant_req.vnfInstanceId,
            vnfLcmOpOccId=grant_req.vnfLcmOpOccId
        )
        mock_vim_info.return_value = None
        self.assertRaises(
            sol_ex.LocalNfvoGrantFailed, self.local_nfvo.instantiate_grant,
            self.context, grant_req, grant_res)

    @mock.patch.object(local_nfvo.LocalNfvo, 'get_csar_dir')
    @mock.patch.object(lcmocc_utils, 'get_lcmocc')
    @mock.patch.object(glance_utils.GlanceClient, 'create_image')
    def test_instantiate_grant_no_image(
            self, mock_image, mock_lcmocc, mock_dir):
        grant_req = objects.GrantRequestV1.from_dict(_inst_grant_req_example)
        grant_res = objects.GrantV1(
            id=uuidutils.generate_uuid(),
            vnfInstanceId=grant_req.vnfInstanceId,
            vnfLcmOpOccId=grant_req.vnfLcmOpOccId
        )
        mock_dir.return_value = self._sample_dir("sample1")
        req = objects.InstantiateVnfRequest.from_dict(_inst_req_example)
        mock_lcmocc.return_value = objects.VnfLcmOpOccV2(
            # only set used members in the method
            operation=fields.LcmOperationType.INSTANTIATE,
            operationParams=req)
        mock_image.return_value = Exception()
        self.assertRaises(
            sol_ex.LocalNfvoGrantFailed, self.local_nfvo.instantiate_grant,
            self.context, grant_req, grant_res)

    @mock.patch.object(local_nfvo.LocalNfvo, 'get_csar_dir')
    @mock.patch.object(lcmocc_utils, 'get_lcmocc')
    @mock.patch.object(glance_utils.GlanceClient, 'list_images')
    @mock.patch.object(glance_utils.GlanceClient, 'create_image')
    @mock.patch.object(inst_utils, 'get_inst')
    def test_change_vnfpkg_grant(self, mock_inst, mock_image,
            mock_list_images, mock_lcmocc, mock_dir):
        grant_req = objects.GrantRequestV1.from_dict(
            _change_vnfkg_grant_req_example)
        grant_res = objects.GrantV1(
            id=uuidutils.generate_uuid(),
            vnfInstanceId=grant_req.vnfInstanceId,
            vnfLcmOpOccId=grant_req.vnfLcmOpOccId
        )
        mock_dir.return_value = self._sample_dir("sample1")
        req = objects.ChangeCurrentVnfPkgRequest.from_dict(
            _change_vnfpkg_example)
        mock_lcmocc.return_value = objects.VnfLcmOpOccV2(
            operation=fields.LcmOperationType.CHANGE_VNFPKG,
            operationParams=req)
        mock_list_images.return_value = []
        mock_image.return_value = objects.GrantV1(
            id=uuidutils.generate_uuid()
        )
        req = objects.InstantiateVnfRequest.from_dict(
            _inst_req_example)
        inst = objects.VnfInstanceV2(
            # required fields
            id=uuidutils.generate_uuid(),
            vnfdId=SAMPLE_VNFD_ID,
            vnfProvider='provider',
            vnfProductName='product name',
            vnfSoftwareVersion='software version',
            vnfdVersion='vnfd version',
            instantiationState='INSTANTIATED',
            vimConnectionInfo=req.vimConnectionInfo
        )
        mock_inst.return_value = inst
        self.local_nfvo.change_vnfpkg_grant(self.context, grant_req, grant_res)
        result = grant_res.to_dict()
        self.assertEqual(mock_image.return_value.id, result[
            'vimAssets']['softwareImages'][0]['vimSoftwareImageId'])

    @mock.patch.object(local_nfvo.LocalNfvo, 'get_csar_dir')
    @mock.patch.object(local_nfvo.LocalNfvo, '_get_vim_info')
    def test_change_vnfpkg_grant_no_vim_info(self, mock_vim_info, mock_dir):
        mock_dir.return_value = self._sample_dir("sample1")
        grant_req = objects.GrantRequestV1.from_dict(
            _change_vnfkg_grant_req_example)
        grant_res = objects.GrantV1(
            id=uuidutils.generate_uuid(),
            vnfInstanceId=grant_req.vnfInstanceId,
            vnfLcmOpOccId=grant_req.vnfLcmOpOccId
        )
        mock_vim_info.return_value = None
        self.assertRaises(
            sol_ex.LocalNfvoGrantFailed, self.local_nfvo.change_vnfpkg_grant,
            self.context, grant_req, grant_res)

    @mock.patch.object(local_nfvo.LocalNfvo, 'get_csar_dir')
    @mock.patch.object(lcmocc_utils, 'get_lcmocc')
    @mock.patch.object(glance_utils.GlanceClient, 'list_images')
    @mock.patch.object(glance_utils.GlanceClient, 'create_image')
    @mock.patch.object(inst_utils, 'get_inst')
    def test_change_vnfpkg_grant_no_image(self, mock_inst, mock_image,
            mock_list_images, mock_lcmocc, mock_dir):
        grant_req = objects.GrantRequestV1.from_dict(
            _change_vnfkg_grant_req_example)
        grant_res = objects.GrantV1(
            id=uuidutils.generate_uuid(),
            vnfInstanceId=grant_req.vnfInstanceId,
            vnfLcmOpOccId=grant_req.vnfLcmOpOccId
        )
        mock_dir.return_value = self._sample_dir("sample1")
        req = objects.ChangeCurrentVnfPkgRequest.from_dict(
            _change_vnfpkg_example)
        mock_lcmocc.return_value = objects.VnfLcmOpOccV2(
            operation=fields.LcmOperationType.CHANGE_VNFPKG,
            operationParams=req)
        req = objects.InstantiateVnfRequest.from_dict(
            _inst_req_example)
        inst = objects.VnfInstanceV2(
            # required fields
            id=uuidutils.generate_uuid(),
            vnfdId=SAMPLE_VNFD_ID,
            vnfProvider='provider',
            vnfProductName='product name',
            vnfSoftwareVersion='software version',
            vnfdVersion='vnfd version',
            instantiationState='INSTANTIATED',
            vimConnectionInfo=req.vimConnectionInfo
        )
        mock_inst.return_value = inst
        mock_list_images.return_value = []
        mock_image.return_value = Exception()
        self.assertRaises(
            sol_ex.LocalNfvoGrantFailed, self.local_nfvo.change_vnfpkg_grant,
            self.context, grant_req, grant_res)

    @mock.patch.object(local_nfvo.LocalNfvo, 'get_csar_dir')
    @mock.patch.object(lcmocc_utils, 'get_lcmocc')
    @mock.patch.object(glance_utils.GlanceClient, 'list_images')
    @mock.patch.object(glance_utils.GlanceClient, 'create_image')
    @mock.patch.object(inst_utils, 'get_inst')
    def test_grant(self, mock_inst, mock_image, mock_list_images,
            mock_lcmocc, mock_dir):
        # instantiate
        grant_req = objects.GrantRequestV1.from_dict(_inst_grant_req_example)
        mock_dir.return_value = self._sample_dir("sample1")
        req = objects.InstantiateVnfRequest.from_dict(_inst_req_example)
        mock_lcmocc.return_value = objects.VnfLcmOpOccV2(
            # only set used members in the method
            operation=fields.LcmOperationType.INSTANTIATE,
            operationParams=req)
        mock_image.return_value = objects.GrantV1(
            id=uuidutils.generate_uuid()
        )
        grant_res = self.local_nfvo.grant(self.context, grant_req)
        result = grant_res.to_dict()
        self.assertIsNotNone(result['addResources'])
        self.assertEqual(mock_image.return_value.id, result[
            'vimAssets']['softwareImages'][0]['vimSoftwareImageId'])

        # change_vnfpkg
        grant_req = objects.GrantRequestV1.from_dict(
            _change_vnfkg_grant_req_example)
        mock_dir.return_value = self._sample_dir("sample1")
        req = objects.ChangeCurrentVnfPkgRequest.from_dict(
            _change_vnfpkg_example)
        mock_lcmocc.return_value = objects.VnfLcmOpOccV2(
            operation=fields.LcmOperationType.CHANGE_VNFPKG,
            operationParams=req
        )
        mock_list_images.return_value = []
        mock_image.return_value = objects.GrantV1(
            id=uuidutils.generate_uuid()
        )
        req = objects.InstantiateVnfRequest.from_dict(
            _inst_req_example)
        inst = objects.VnfInstanceV2(
            # required fields
            id=uuidutils.generate_uuid(),
            vnfdId=SAMPLE_VNFD_ID,
            vnfProvider='provider',
            vnfProductName='product name',
            vnfSoftwareVersion='software version',
            vnfdVersion='vnfd version',
            instantiationState='INSTANTIATED',
            vimConnectionInfo=req.vimConnectionInfo
        )
        mock_inst.return_value = inst
        grant_res = self.local_nfvo.grant(self.context, grant_req)
        result = grant_res.to_dict()
        self.assertEqual(mock_image.return_value.id, result[
            'vimAssets']['softwareImages'][0]['vimSoftwareImageId'])

    @mock.patch.object(vnf_package_vnfd.VnfPackageVnfd, 'get_by_id')
    @mock.patch.object(vnf_package.VnfPackage, 'get_by_id')
    @mock.patch.object(vnf_package.VnfPackage, 'save')
    def test_recv_inst_create_notification(
            self, mock_save, mock_vnfpackage, mock_vnfd):
        req = objects.InstantiateVnfRequest.from_dict(
            _inst_req_example)
        inst = objects.VnfInstanceV2(
            # required fields
            id=uuidutils.generate_uuid(),
            vnfdId=SAMPLE_VNFD_ID,
            vnfProvider='provider',
            vnfProductName='product name',
            vnfSoftwareVersion='software version',
            vnfdVersion='vnfd version',
            instantiationState='NOT_INSTANTIATED',
            vimConnectionInfo=req.vimConnectionInfo
        )
        mock_vnfd.return_value = self._get_vnfpkg_or_vnfd('vnfd')
        mock_vnfpackage.return_value = self._get_vnfpkg_or_vnfd('vnfpkg')
        self.local_nfvo.recv_inst_create_notification(self.context, inst)

    @mock.patch.object(vnf_package_vnfd.VnfPackageVnfd, 'get_by_id')
    @mock.patch.object(vnf_package.VnfPackage, 'get_by_id')
    @mock.patch.object(vnf_package.VnfPackage, 'save')
    @mock.patch.object(objects.base.TackerPersistentObject, 'get_by_filter')
    def test_recv_inst_delete_notification(
            self, mock_inst, mock_save, mock_vnfpackage, mock_vnfd):
        req = objects.InstantiateVnfRequest.from_dict(
            _inst_req_example)
        inst = objects.VnfInstanceV2(
            # required fields
            id=uuidutils.generate_uuid(),
            vnfdId=SAMPLE_VNFD_ID,
            vnfProvider='provider',
            vnfProductName='product name',
            vnfSoftwareVersion='software version',
            vnfdVersion='vnfd version',
            instantiationState='INSTANTIATED',
            vimConnectionInfo=req.vimConnectionInfo
        )
        mock_inst.return_value = None
        mock_vnfd.return_value = self._get_vnfpkg_or_vnfd('vnfd')
        mock_vnfpackage.return_value = self._get_vnfpkg_or_vnfd('vnfpkg')
        self.local_nfvo.recv_inst_delete_notification(self.context, inst)

    @mock.patch.object(local_nfvo.LocalNfvo, '_glance_delete_images')
    @mock.patch.object(local_nfvo.LocalNfvo, '_update_vnf_pkg_usage_state')
    def test_recv_lcmocc_notification(self, mock_update, mock_delete_image):
        # terminate-processing

        req_inst = objects.InstantiateVnfRequest.from_dict(_inst_req_example)
        inst = objects.VnfInstanceV2(
            # required fields
            id=uuidutils.generate_uuid(),
            vnfdId=SAMPLE_VNFD_ID,
            vnfProvider='provider',
            vnfProductName='product name',
            vnfSoftwareVersion='software version',
            vnfdVersion='vnfd version',
            instantiationState='INSTANTIATED',
            vimConnectionInfo=req_inst.vimConnectionInfo,
        )
        req = objects.TerminateVnfRequest(terminationType='FORCEFUL')
        lcmocc = objects.VnfLcmOpOccV2(
            # required fields
            id=uuidutils.generate_uuid(),
            operationState=fields.LcmOperationStateType.PROCESSING,
            stateEnteredTime=datetime.utcnow(),
            startTime=datetime.utcnow(),
            vnfInstanceId=inst.id,
            operation=fields.LcmOperationType.TERMINATE,
            isAutomaticInvocation=False,
            isCancelPending=False,
            operationParams=req)
        self.local_nfvo.recv_lcmocc_notification(self.context, lcmocc, inst)

        # terminate-failed_temp
        lcmocc.operationState = fields.LcmOperationStateType.FAILED_TEMP
        self.local_nfvo.recv_lcmocc_notification(self.context, lcmocc, inst)

        # terminate-completed
        self.local_nfvo.inst_vim_info = {
            inst.id: req_inst.vimConnectionInfo['vim1']
        }
        lcmocc.operationState = fields.LcmOperationStateType.COMPLETED
        self.local_nfvo.recv_lcmocc_notification(self.context, lcmocc, inst)
        self.assertEqual(1, mock_delete_image.call_count)

        # change_vnfpkg-processing
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
        self.local_nfvo.recv_lcmocc_notification(self.context, lcmocc, inst)

        # change_vnfpkg-failed_temp
        lcmocc.operationState = fields.LcmOperationStateType.FAILED_TEMP
        self.local_nfvo.recv_lcmocc_notification(self.context, lcmocc, inst)

        # change_vnfpkg-completed
        self.local_nfvo.inst_vnfd_id = {inst.id: req.vnfdId}
        lcmocc.operationState = fields.LcmOperationStateType.COMPLETED
        self.local_nfvo.recv_lcmocc_notification(self.context, lcmocc, inst)

        # instantiate-rolled_back
        req_inst = objects.InstantiateVnfRequest.from_dict(_inst_req_example)
        inst = objects.VnfInstanceV2(
            # required fields
            id=uuidutils.generate_uuid(),
            vnfdId=SAMPLE_VNFD_ID,
            vnfProvider='provider',
            vnfProductName='product name',
            vnfSoftwareVersion='software version',
            vnfdVersion='vnfd version',
            instantiationState='NOT_INSTANTIATED',
            vimConnectionInfo=req_inst.vimConnectionInfo,
        )
        lcmocc = objects.VnfLcmOpOccV2(
            # required fields
            id=uuidutils.generate_uuid(),
            operationState=fields.LcmOperationStateType.ROLLED_BACK,
            stateEnteredTime=datetime.utcnow(),
            startTime=datetime.utcnow(),
            vnfInstanceId=inst.id,
            operation=fields.LcmOperationType.INSTANTIATE,
            isAutomaticInvocation=False,
            isCancelPending=False,
            operationParams=req_inst)

        mock_delete_image.reset_mock()
        self.local_nfvo.recv_lcmocc_notification(self.context, lcmocc, inst)
        self.assertEqual(1, mock_delete_image.call_count)
