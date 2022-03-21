# Copyright (C) 2022 NEC, Corp.
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

from tacker.tests.compliance.sol005 import base


class BaseVNFPackageManagementTest(base.BaseComplSolTest):
    @classmethod
    def setUpClass(cls):
        cls.api = 'VNFPackageManagement-API'

        super(BaseVNFPackageManagementTest, cls).setUpClass()


class VNFPackagesTest(BaseVNFPackageManagementTest):
    @classmethod
    def setUpClass(cls):
        cls.resource = 'VNFPackages'

        super(VNFPackagesTest, cls).setUpClass()

    def test_get_all_vnf_packages(self):
        # Pre-conditions: One or more VNF packages are onboarded in the NFVO.
        vnfpkginfos = self._create_and_upload_vnf_packages(
            ['vnflcm1', 'vnflcm2'])

        rc, output = self._run('GET all VNF Packages')

        # Post-Conditions: none
        self._disable_and_delete_vnf_packages(vnfpkginfos)

        self.assertEqual(0, rc)

    def test_get_vnf_packages_with_attribute_based_filter(self):
        # Pre-conditions: One or more VNF packages are onboarded in the NFVO.
        self._run('GET VNF Packages with attribute-based filter')
        # Post-Conditions: none

    def test_get_vnf_packages_with_all_fields_attribute_selector(self):
        # Pre-conditions: One or more VNF packages are onboarded in the NFVO.
        self._run('GET VNF Packages with "all_fields" attribute selector')
        # Post-Conditions: none

    def test_vnf_packages_with_exclude_default_attribute_selector(self):
        # Pre-conditions: One or more VNF packages are onboarded in the NFVO.
        self._run('GET VNF Packages with "exclude_default" attribute selector')
        # Post-Conditions: none

    def test_get_vnf_packages_with_fields_attribute_selector(self):
        # Pre-conditions: One or more VNF packages are onboarded in the NFVO.
        self._run('GET VNF Packages with "fields" attribute selector')
        # Post-Conditions: none

    def test_get_vnf_packages_with_exclude_fields_attribute_selector(self):
        # Pre-conditions: One or more VNF packages are onboarded in the NFVO.
        self._run('GET VNF Packages with "exclude_fields" attribute selector')
        # Post-Conditions: none

    def test_create_vnf_package(self):
        # Pre-conditions: none
        rc, output = self._run('Create new VNF Package Resource')

        # Post-Conditions: The VNF Package Resource is successfully created
        # on the NFVO
        res = self._get_responses_from_output(output)
        if ('status' in res[0] and res[0]['status'] == 201):
            if ('body' in res[0] and 'id' in res[0]['body']):
                # delete created vnf package
                self._delete_vnf_package(res[0]['body']['id'])

        self.assertEqual(0, rc)


class IndividualVNFPackageTest(BaseVNFPackageManagementTest):
    @classmethod
    def setUpClass(cls):
        cls.resource = 'IndividualVNFPackage'

        super(IndividualVNFPackageTest, cls).setUpClass()

    def test_get_individual_vnf_package(self):

        # Pre-conditions: One or more VNF packages are onboarded in the NFVO.
        vnfpkginfos = self._create_and_upload_vnf_packages(['vnflcm1'])
        variables = ['vnfPackageId:' + vnfpkginfos[0].vnfpkgid]

        rc, output = self._run('GET Individual VNF Package', variables)

        # Post-Conditions: none
        self._disable_and_delete_vnf_packages(vnfpkginfos)

        self.assertEqual(0, rc)

    def test_disable_individual_vnf_package(self):
        # Pre-conditions: One or more VNF Packages are onboarded in the NFVO
        # in ENABLED operational state.
        vnfpkginfos = self._create_and_upload_vnf_packages(['vnflcm1'])
        variables = ['vnfPackageId:' + vnfpkginfos[0].vnfpkgid]

        rc, output = self._run('Disable Individual VNF Package', variables)

        # Post-Conditions: The VNF Package is in operational state DISABLED
        self._delete_vnf_package(vnfpkginfos[0].vnfpkgid)

        self.assertEqual(0, rc)

    def test_enable_individual_vnf_package(self):
        # Pre-conditions: One or more VNF Packages are onboarded in the NFVO
        # in DISABLED operational state.
        vnfpkginfos = self._create_and_upload_vnf_packages(['vnflcm1'])
        self._disable_vnf_package(vnfpkginfos[0].vnfpkgid)
        variables = ['vnfPackageId:' + vnfpkginfos[0].vnfpkgid]

        rc, output = self._run('Enable Individual VNF Package', variables)

        # Post-Conditions: The VNF Package is in operational state ENABLED
        self._disable_and_delete_vnf_packages(vnfpkginfos)

        self.assertEqual(0, rc)

    def test_delete_individual_vnf_package(self):
        # Pre-conditions: One or more VNF packages are onboarded in the NFVO
        # in DISABLED operational state
        vnfpkginfos = self._create_and_upload_vnf_packages(['vnflcm1'])
        self._disable_vnf_package(vnfpkginfos[0].vnfpkgid)
        variables = ['disabledVnfPackageId:' + vnfpkginfos[0].vnfpkgid]

        rc, output = self._run('DELETE Individual VNF Package', variables)

        # Post-Conditions: The VNF Package is not available anymore in the NFVO
        self.assertEqual(0, rc)
