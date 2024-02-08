# Copyright (C) 2024 NEC, Corp.
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

from unittest import mock

from tacker.api.vnflcm.v1 import controller
from tacker import objects
from tacker.policies import vnf_lcm as policies
from tacker.tests.unit import fake_request
import tacker.tests.unit.nfvo.test_nfvo_plugin as test_nfvo_plugin
from tacker.tests.unit.policies import base as base_test
from tacker.tests.unit.vnflcm import fakes
from tacker.tests import uuidsentinel
from tacker.vnfm import vim_client


class VNFLCMPolicyTest(base_test.BasePolicyTest):
    """Test VNF LCM APIs policies with all possible context.

    This class defines the set of context with different roles
    which are allowed and not allowed to pass the policy checks.
    With those set of context, it will call the API operation and
    verify the expected behaviour.
    """

    def setUp(self):
        super(VNFLCMPolicyTest, self).setUp()
        self.patcher = mock.patch(
            'tacker.manager.TackerManager.get_service_plugins',
            return_value={'VNFM': test_nfvo_plugin.FakeVNFMPlugin()})
        self.mock_manager = self.patcher.start()
        self.controller = controller.VnfLcmController()
        self.vim_info = {
            'vim_id': uuidsentinel.vnfd_id,
            'vim_type': 'test',
            'vim_auth': {'username': 'test', 'password': 'test'},
            'placement_attr': {'region': 'TestRegionOne'},
            'tenant': 'test',
            'extra': {}
        }
        # Below user's context will be allowed to create the VNF
        # in their project.
        self.create_authorized_contexts = [
            self.legacy_admin_context, self.project_admin_context,
            self.project_member_context, self.project_reader_context,
            self.project_foo_context, self.other_project_member_context,
            self.other_project_reader_context
        ]
        self.create_unauthorized_contexts = []

    @mock.patch.object(vim_client.VimClient, "get_vim")
    @mock.patch.object(objects.VnfPackage, 'get_by_id')
    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._create_vnf')
    @mock.patch.object(objects.vnf_package.VnfPackage, 'save')
    @mock.patch.object(objects.vnf_instance, '_vnf_instance_update')
    @mock.patch.object(objects.vnf_instance, '_vnf_instance_create')
    @mock.patch.object(objects.vnf_package_vnfd.VnfPackageVnfd, 'get_by_id')
    def test_create_vnf(
            self, mock_get_by_id,
            mock_vnf_instance_create,
            mock_vnf_instance_update,
            mock_package_save,
            mock_private_create_vnf,
            mock_vnf_package_get_by_id,
            mock_get_vim):
        mock_get_vim.return_value = self.vim_info
        mock_get_by_id.return_value = fakes.return_vnf_package_vnfd()
        mock_vnf_package_get_by_id.return_value = \
            fakes.return_vnf_package_with_deployment_flavour()

        updates = {'vnfd_id': uuidsentinel.vnfd_id,
                'vnf_instance_description': 'SampleVnf Description',
                'vnf_instance_name': 'SampleVnf',
                'vnf_pkg_id': uuidsentinel.vnf_pkg_id,
                'vnf_metadata': {'key': 'value'}}

        mock_vnf_instance_create.return_value = (
            fakes.return_vnf_instance_model(**updates))
        mock_vnf_instance_update.return_value = (
            fakes.return_vnf_instance_model(**updates))

        body = {'vnfdId': uuidsentinel.vnfd_id,
                'vnfInstanceName': 'SampleVnf',
                'vnfInstanceDescription': 'SampleVnf Description',
                'metadata': {'key': 'value'}}
        req = fake_request.HTTPRequest.blank('/vnf_instances')
        rule_name = policies.VNFLCM % 'create'
        self.common_policy_check(self.create_authorized_contexts,
                                 self.create_unauthorized_contexts,
                                 rule_name,
                                 self.controller.create,
                                 req, body=body)
