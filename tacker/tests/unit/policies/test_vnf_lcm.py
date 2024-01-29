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

from oslo_config import cfg

from tacker.api.vnflcm.v1 import controller
import tacker.conductor.conductorrpc.vnf_lcm_rpc as vnf_lcm_rpc
from tacker import objects
from tacker.objects import fields
from tacker.policies import vnf_lcm as policies
from tacker.tests.unit.db import utils
from tacker.tests.unit import fake_request
from tacker.tests.unit.policies import base as base_test
from tacker.tests.unit.vnflcm import fakes
from tacker.tests import uuidsentinel
from tacker.vnfm import vim_client


class FakePlugin(mock.Mock):

    def get_vnf(self, *args, **kwargs):
        return utils.get_dummy_vnf(status='ACTIVE')


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
            return_value={'VNFM': FakePlugin()})
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
        # Below user's context will be allowed to create VNF or a few of
        # the VNF operations in their project.
        self.project_authorized_contexts = [
            self.legacy_admin_context, self.project_admin_context,
            self.project_member_context, self.project_reader_context,
            self.project_foo_context, self.other_project_member_context,
            self.other_project_reader_context
        ]
        self.project_unauthorized_contexts = []

        # Admin or any user in same project will be allowed to instantiate,
        # terminate etc write operations of VNF of their project.
        self.project_member_authorized_contexts = [
            self.legacy_admin_context, self.project_admin_context,
            self.project_member_context, self.project_reader_context,
            self.project_foo_context
        ]
        # User from other project will not be allowed to perform write
        # operation on the other project's VNF operations.
        self.project_member_unauthorized_contexts = [
            self.other_project_member_context,
            self.other_project_reader_context
        ]

        # Admin or any user in same project will be allowed to get,
        # VNF of their project.
        self.project_reader_authorized_contexts = (
            self.project_member_authorized_contexts)
        # User from other project will not be allowed to get
        # the other project's VNF.
        self.project_reader_unauthorized_contexts = (
            self.project_member_unauthorized_contexts)

        # Below user's context will be allowed to list VNF or
        # get VNF LCM operation occurrence.
        self.get_authorized_contexts = [
            self.legacy_admin_context, self.project_admin_context,
            self.project_member_context, self.project_reader_context,
            self.project_foo_context, self.other_project_member_context,
            self.other_project_reader_context
        ]
        self.get_unauthorized_contexts = []

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
        self.common_policy_check(self.project_authorized_contexts,
                                 self.project_unauthorized_contexts,
                                 rule_name,
                                 self.controller.create,
                                 req, body=body)

    @mock.patch.object(objects.VnfInstance, "get_by_id")
    def test_show_vnf(self, mock_vnf_by_id):
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s' % uuidsentinel.instance_id)
        mock_vnf_by_id.return_value = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED,
            tenant_id=self.project_id)
        rule_name = policies.VNFLCM % 'show'
        self.common_policy_check(self.project_reader_authorized_contexts,
                                 self.project_reader_unauthorized_contexts,
                                 rule_name,
                                 self.controller.show,
                                 req, uuidsentinel.instance_id)

    @mock.patch.object(objects.VnfInstanceList, "get_by_marker_filter")
    def test_index_vnf(self, mock_vnf_list):
        req = fake_request.HTTPRequest.blank('/vnf_instances')
        vnf_instance_1 = fakes.return_vnf_instance()
        vnf_instance_2 = fakes.return_vnf_instance()
        mock_vnf_list.return_value = [vnf_instance_1, vnf_instance_2]
        rule_name = policies.VNFLCM % 'index'
        self.common_policy_check(self.get_authorized_contexts,
                                 self.get_unauthorized_contexts,
                                 rule_name,
                                 self.controller.index,
                                 req)

    @mock.patch.object(objects.VNF, "vnf_index_list")
    @mock.patch.object(objects.VnfInstanceList, "vnf_instance_list")
    @mock.patch.object(objects.VnfPackageVnfd, 'get_vnf_package_vnfd')
    @mock.patch.object(vnf_lcm_rpc.VNFLcmRPCAPI, "update")
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    def test_update_vnf(
            self, mock_vnf_by_id, mock_update,
            mock_vnf_package_vnf_get_vnf_package_vnfd,
            mock_vnf_instance_list,
            mock_vnf_index_list,):
        mock_vnf_by_id.return_value = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED,
            tenant_id=self.project_id)
        mock_vnf_index_list.return_value = fakes._get_vnf()
        mock_vnf_instance_list.return_value = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED,
            tenant_id=self.project_id)
        mock_vnf_package_vnf_get_vnf_package_vnfd.return_value =\
            fakes.return_vnf_package_vnfd()

        body = {"vnfInstanceName": "new_instance_name",
                "vnfInstanceDescription": "new_instance_discription",
                "vnfdId": "2c69a161-0000-4b0f-bcf8-391f8fc76600",
                "vnfConfigurableProperties": {
                    "test": "test_value"
                },
                "vnfcInfoModificationsDeleteIds": ["test1"],
                "metadata": {"testkey": "test_value"},
                "vimConnectionInfo": {"id": "testid"}}
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s' % uuidsentinel.instance_id)
        rule_name = policies.VNFLCM % 'update_vnf'
        self.common_policy_check(self.project_member_authorized_contexts,
                                 self.project_member_unauthorized_contexts,
                                 rule_name,
                                 self.controller.update,
                                 req, uuidsentinel.instance_id,
                                 body=body)

    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._get_vnf')
    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._instantiate')
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    def test_instantiate_vnf(
            self, mock_vnf_by_id, mock_instantiate, mock_vnf):
        mock_vnf_by_id.return_value = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED,
            tenant_id=self.project_id)
        mock_vnf.return_value = utils.get_dummy_vnf()
        mock_instantiate.return_value = {
            'status': 202, 'Location': 'vnf status check link'}
        body = {"flavourId": "simple",
                "instantiationLevelId": "instantiation_level_1"}
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/instantiate' % uuidsentinel.instance_id)
        rule_name = policies.VNFLCM % 'instantiate'
        self.common_policy_check(self.project_member_authorized_contexts,
                                 self.project_member_unauthorized_contexts,
                                 rule_name,
                                 self.controller.instantiate,
                                 req, uuidsentinel.instance_id,
                                 body=body)

    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._get_vnf')
    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._terminate')
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    def test_terminate_vnf(self, mock_vnf_by_id, mock_terminate, mock_vnf):
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/terminate' % uuidsentinel.instance_id)
        body = {'terminationType': 'GRACEFUL',
                'gracefulTerminationTimeout': 10}
        mock_vnf_by_id.return_value = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED,
            tenant_id=self.project_id)
        mock_vnf.return_value = utils.get_dummy_vnf()
        mock_terminate.return_value = {
            'status': 202, 'Location': 'vnf status check link'}
        rule_name = policies.VNFLCM % 'terminate'
        self.common_policy_check(self.project_member_authorized_contexts,
                                 self.project_member_unauthorized_contexts,
                                 rule_name,
                                 self.controller.terminate,
                                 req, uuidsentinel.instance_id,
                                 body=body)

    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._get_vnf')
    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._delete')
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    def test_delete_vnf(self, mock_vnf_by_id, mock_delete, mock_vnf):
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s' % uuidsentinel.instance_id)
        mock_vnf_by_id.return_value = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED,
            tenant_id=self.project_id)
        mock_vnf.return_value = utils.get_dummy_vnf()
        rule_name = policies.VNFLCM % 'delete'
        self.common_policy_check(self.project_member_authorized_contexts,
                                 self.project_member_unauthorized_contexts,
                                 rule_name,
                                 self.controller.delete,
                                 req, uuidsentinel.instance_id)

    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._get_vnf')
    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._heal')
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    def test_heal_vnf(self, mock_vnf_by_id, mock_heal, mock_vnf):
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/heal' % uuidsentinel.instance_id)
        body = {'cause': 'healing'}
        mock_vnf_by_id.return_value = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED,
            tenant_id=self.project_id)
        mock_vnf.return_value = utils.get_dummy_vnf()
        rule_name = policies.VNFLCM % 'heal'
        self.common_policy_check(self.project_member_authorized_contexts,
                                 self.project_member_unauthorized_contexts,
                                 rule_name,
                                 self.controller.heal,
                                 req, uuidsentinel.instance_id,
                                 body=body)

    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._scale')
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    def test_scale_vnf(self, mock_vnf_by_id, mock_scale):
        req = fake_request.HTTPRequest.blank(
            '/vnf_instances/%s/scale' % uuidsentinel.instance_id)
        body = {
            "type": "SCALE_OUT",
            "aspectId": "SP1",
            "numberOfSteps": 1,
            "additionalParams": {
                "test": "test_value"}}
        mock_vnf_by_id.return_value = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED,
            tenant_id=self.project_id)
        rule_name = policies.VNFLCM % 'scale'
        self.common_policy_check(self.project_member_authorized_contexts,
                                 self.project_member_unauthorized_contexts,
                                 rule_name,
                                 self.controller.scale,
                                 req, uuidsentinel.instance_id,
                                 body=body)

    @mock.patch.object(objects.VnfLcmOpOcc, "get_by_id")
    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._get_rollback_vnf')
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    def test_rollback_vnf(self, mock_vnf_by_id, mock_rollback,
            mock_lcm_by_id):
        req = fake_request.HTTPRequest.blank(
            '/vnf_lcm_op_occs/%s/rollback' % uuidsentinel.instance_id)
        mock_lcm_by_id.return_value = fakes.vnflcm_rollback_active()
        mock_vnf_by_id.return_value = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED,
            tenant_id=self.project_id)
        rule_name = policies.VNFLCM % 'rollback'
        self.common_policy_check(self.project_member_authorized_contexts,
                                 self.project_member_unauthorized_contexts,
                                 rule_name,
                                 self.controller.rollback,
                                 req, uuidsentinel.instance_id)

    @mock.patch.object(objects.VnfLcmOpOcc, "get_by_id")
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch.object(objects.VnfLcmOpOcc, "save")
    def test_cancel_vnf(self, mock_save_occ, mock_vnf, mock_vnf_by_id,
                        mock_lcm_by_id):
        req = fake_request.HTTPRequest.blank(
            '/vnf_lcm_op_occs/%s/cancel' % uuidsentinel.instance_id)
        body = {'cancelMode': 'FORCEFUL'}
        mock_lcm_by_id.return_value = fakes.vnflcm_cancel_insta()
        mock_vnf_by_id.return_value = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED,
            tenant_id=self.project_id)
        rule_name = policies.VNFLCM % 'cancel'
        self.common_policy_check(self.project_member_authorized_contexts,
                                 self.project_member_unauthorized_contexts,
                                 rule_name,
                                 self.controller.cancel,
                                 req, uuidsentinel.instance_id,
                                 body=body)

    @mock.patch.object(objects.VnfLcmOpOcc, "get_by_id")
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    @mock.patch.object(objects.VnfInstance, "save")
    @mock.patch.object(objects.VnfLcmOpOcc, "save")
    def test_fail_vnf(self, mock_save_occ, mock_vnf, mock_vnf_by_id,
                      mock_lcm_by_id):
        req = fake_request.HTTPRequest.blank(
            '/vnf_lcm_op_occs/%s/fail' % uuidsentinel.instance_id)
        mock_lcm_by_id.return_value = fakes.vnflcm_fail_insta()
        mock_vnf_by_id.return_value = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED,
            tenant_id=self.project_id)
        rule_name = policies.VNFLCM % 'fail'
        self.common_policy_check(self.project_member_authorized_contexts,
                                 self.project_member_unauthorized_contexts,
                                 rule_name,
                                 self.controller.fail,
                                 req, uuidsentinel.instance_id)

    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._get_vnf')
    @mock.patch.object(objects.VnfLcmOpOcc, "get_by_id")
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    @mock.patch.object(controller.VnfLcmController, "_instantiate")
    def test_retry_vnf(self, mock_instantiate, mock_vnf_by_id,
                       mock_lcm_by_id, mock_vnf):
        req = fake_request.HTTPRequest.blank(
            '/vnf_lcm_op_occs/%s/fail' % uuidsentinel.instance_id)
        mock_lcm_by_id.return_value = fakes.vnflcm_op_occs_retry_data()
        mock_vnf.return_value = utils.get_dummy_vnf()
        mock_vnf_by_id.return_value = fakes.return_vnf_instance(
            tenant_id=self.project_id)
        rule_name = policies.VNFLCM % 'retry'
        self.common_policy_check(self.project_member_authorized_contexts,
                                 self.project_member_unauthorized_contexts,
                                 rule_name,
                                 self.controller.retry,
                                 req, uuidsentinel.instance_id)

    @mock.patch.object(objects.VnfLcmOpOcc, "get_by_id")
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    def test_show_lcm_op_occs(self, mock_vnf_by_id, mock_lcm_by_id):
        req = fake_request.HTTPRequest.blank(
            '/vnf_lcm_op_occs/%s' % uuidsentinel.instance_id)
        mock_lcm_by_id.return_value = fakes.return_vnf_lcm_opoccs_obj()
        mock_vnf_by_id.return_value = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED,
            tenant_id=self.project_id)
        rule_name = policies.VNFLCM % 'show_lcm_op_occs'
        self.common_policy_check(self.project_reader_authorized_contexts,
                                 self.project_reader_unauthorized_contexts,
                                 rule_name,
                                 self.controller.show_lcm_op_occs,
                                 req, uuidsentinel.instance_id)

    @mock.patch.object(objects.VnfLcmOpOccList, "get_by_marker_filter")
    def test_list_lcm_op_occs(self, mock_op_occ_list):
        req = fake_request.HTTPRequest.blank(
            '/vnflcm/v1/vnf_lcm_op_occs')
        rule_name = policies.VNFLCM % 'list_lcm_op_occs'
        self.common_policy_check(self.get_authorized_contexts,
                                 self.get_unauthorized_contexts,
                                 rule_name,
                                 self.controller.list_lcm_op_occs,
                                 req)

    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._get_vnf')
    @mock.patch('tacker.api.vnflcm.v1.controller.'
                'VnfLcmController._change_ext_conn')
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    def test_change_ext_conn_vnf(self, mock_vnf_by_id,
                                 mock_change_ext_conn, mock_vnf):
        req = fake_request.HTTPRequest.blank(
            '/vnflcm/v1/vnf_instances/%s/change_ext_conn' %
            uuidsentinel.instance_id)
        body = fakes.get_change_ext_conn_request_body()
        mock_vnf_by_id.return_value = fakes.return_vnf_instance(
            fields.VnfInstanceState.INSTANTIATED,
            tenant_id=self.project_id)
        mock_vnf.return_value = utils.get_dummy_vnf()
        rule_name = policies.VNFLCM % 'change_ext_conn'
        self.common_policy_check(self.project_member_authorized_contexts,
                                 self.project_member_unauthorized_contexts,
                                 rule_name,
                                 self.controller.change_ext_conn,
                                 req, uuidsentinel.instance_id,
                                 body=body)


class VNFLCMScopeTypePolicyTest(VNFLCMPolicyTest):
    """Test VNF LCM APIs policies with scope enabled.

    This class set the tacker.conf [oslo_policy] enforce_scope to True
    so that we can switch on the scope checking on oslo policy side.
    This check that system scope users are not allowed to access the
    Tacker VNF LCM APIs.
    """

    def setUp(self):
        super(VNFLCMScopeTypePolicyTest, self).setUp()
        cfg.CONF.set_override('enforce_scope', True,
                              group='oslo_policy')
        self.project_authorized_contexts = [
            self.legacy_admin_context, self.project_admin_context,
            self.project_member_context, self.project_reader_context,
            self.project_foo_context, self.other_project_member_context,
            self.other_project_reader_context
        ]
        # With scope enabled, system scoped users will not be
        # allowed to create VNF or a few of the VNF operations
        # in their project.
        self.project_unauthorized_contexts = [
            self.system_admin_context, self.system_member_context,
            self.system_reader_context, self.system_foo_context
        ]
        self.project_member_authorized_contexts = [
            self.legacy_admin_context, self.project_admin_context,
            self.project_member_context, self.project_reader_context,
            self.project_foo_context
        ]
        # With scope enabled, system scoped users will not be allowed
        # to get, instantiate, terminate etc operations of VNF
        self.project_member_unauthorized_contexts = [
            self.system_admin_context, self.system_member_context,
            self.system_reader_context, self.system_foo_context,
            self.other_project_member_context,
            self.other_project_reader_context]

        self.get_authorized_contexts = [
            self.legacy_admin_context, self.project_admin_context,
            self.project_member_context, self.project_reader_context,
            self.project_foo_context, self.other_project_member_context,
            self.other_project_reader_context
        ]
        # With scope enabled, system scoped users will not be allowed
        # to list VNF and get VNF LCM operation occurrence.
        self.get_unauthorized_contexts = [
            self.system_admin_context, self.system_member_context,
            self.system_reader_context, self.system_foo_context,
        ]


class VNFLCMNewDefaultsPolicyTest(VNFLCMPolicyTest):
    """Test VNF LCM APIs policies with new defaults enabled

    This test class enable the new defaults means no legacy old rules
    and check how permission level looks like.
    """

    enforce_new_defaults = True

    def setUp(self):
        super(VNFLCMNewDefaultsPolicyTest, self).setUp()

        # In new defaults, admin or member roles users will be allowed
        # to create VNF or a few of the VNF operations in their project.
        # Project reader will not be able to create VNF.
        self.project_authorized_contexts = [
            self.legacy_admin_context, self.project_admin_context,
            self.project_member_context, self.other_project_member_context,
        ]
        # In new defaults, non admin or non member role (Project reader)
        # user will not be able to create VNF.
        self.project_unauthorized_contexts = [
            self.project_reader_context, self.project_foo_context,
            self.other_project_reader_context]

        # In new defaults, all admin, project members will be allowed to
        # instantiate, terminate etc write operations of VNF of their project.
        self.project_member_authorized_contexts = [
            self.legacy_admin_context, self.project_admin_context,
            self.project_member_context
        ]
        # In new defaults, Project reader or any other non admin|member
        # role (say foo role) will not be allowed to perform any write
        # operation on VNF.
        self.project_member_unauthorized_contexts = [
            self.project_reader_context, self.project_foo_context,
            self.other_project_member_context,
            self.other_project_reader_context
        ]

        # In new defaults, Project reader also can get VNF.
        self.project_reader_authorized_contexts = [
            self.legacy_admin_context, self.project_admin_context,
            self.project_member_context,
            self.project_reader_context
        ]
        # In new defaults, non admin|member|reader role (say foo role)
        # will not be able to get VNF.
        self.project_reader_unauthorized_contexts = [
            self.project_foo_context,
            self.other_project_member_context,
            self.other_project_reader_context
        ]

        # In new defaults, project random role like foo will not
        # be allowed.
        self.get_authorized_contexts = [
            self.legacy_admin_context, self.project_admin_context,
            self.project_member_context, self.project_reader_context,
            self.other_project_member_context,
            self.other_project_reader_context
        ]
        self.get_unauthorized_contexts = [
            self.project_foo_context,
        ]


class VNFLCMNewDefaultsWithScopePolicyTest(VNFLCMNewDefaultsPolicyTest):
    """Test VNF LCM APIs policies with new defaults rules and scope enabled

    This means scope enabled and no legacy old rules. This is the end goal
    when operators will enable scope and new defaults.
    """

    def setUp(self):
        super(VNFLCMNewDefaultsWithScopePolicyTest, self).setUp()
        cfg.CONF.set_override('enforce_scope', True,
                              group='oslo_policy')

        # With scope enable and no legacy rule, only project admin/member
        # will be able to create VNF in their project.
        self.project_authorized_contexts = [
            self.legacy_admin_context, self.project_admin_context,
            self.project_member_context, self.other_project_member_context
        ]
        # System scoped users will not be allowed.
        self.project_unauthorized_contexts = [
            self.system_admin_context, self.system_member_context,
            self.system_reader_context, self.system_foo_context,
            self.project_reader_context, self.project_foo_context,
            self.other_project_reader_context]

        self.project_member_authorized_contexts = [
            self.legacy_admin_context, self.project_admin_context,
            self.project_member_context,
        ]
        # System scoped users will not be allowed.
        self.project_member_unauthorized_contexts = [
            self.system_admin_context, self.system_member_context,
            self.system_reader_context, self.system_foo_context,
            self.project_reader_context, self.project_foo_context,
            self.other_project_member_context,
            self.other_project_reader_context]

        self.project_reader_authorized_contexts = [
            self.legacy_admin_context, self.project_admin_context,
            self.project_member_context,
            self.project_reader_context
        ]
        # System scoped users will not be allowed.
        self.project_reader_unauthorized_contexts = [
            self.system_admin_context, self.system_member_context,
            self.system_reader_context, self.system_foo_context,
            self.project_foo_context,
            self.other_project_member_context,
            self.other_project_reader_context
        ]

        self.get_authorized_contexts = [
            self.legacy_admin_context, self.project_admin_context,
            self.project_member_context, self.project_reader_context,
            self.other_project_member_context,
            self.other_project_reader_context
        ]
        # With scope enabled, system scoped users will not be allowed
        # to list VNF and get VNF LCM operation occurrence.
        self.get_unauthorized_contexts = [
            self.project_foo_context, self.system_admin_context,
            self.system_member_context, self.system_reader_context,
            self.system_foo_context,
        ]
