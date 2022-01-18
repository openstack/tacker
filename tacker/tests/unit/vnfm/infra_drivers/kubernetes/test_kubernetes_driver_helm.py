# Licensed under the Apache License, Version 2.0 (the "License"); you may
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
import eventlet
import os
import paramiko

from ddt import ddt
from kubernetes import client
from oslo_serialization import jsonutils
from tacker.common import exceptions
from tacker import context
from tacker.db.db_sqlalchemy import models
from tacker.extensions import vnfm
from tacker import objects
from tacker.tests.unit import base
from tacker.tests.unit.db import utils
from tacker.tests.unit.vnflcm import fakes as vnflcm_fakes
from tacker.tests.unit.vnfm.infra_drivers.kubernetes import fakes
from tacker.tests.unit.vnfm.infra_drivers.openstack.fixture_data import \
    fixture_data_utils as fd_utils
from tacker.vnfm.infra_drivers.kubernetes.helm import helm_client
from tacker.vnfm.infra_drivers.kubernetes import kubernetes_driver
from tacker.vnfm import vim_client
from unittest import mock


class FakeRemoteCommandExecutor(mock.Mock):
    def close_session(self):
        return


class FakeCommander(mock.Mock):
    def config(self, is_success, errmsg=None, stdout=''):
        self.is_success = is_success
        self.errmsg = errmsg
        self.stdout = stdout

    def execute_command(self, *args, **kwargs):
        is_success = self.is_success
        fake_result = FakeCmdResult()
        stderr = ''
        stdout = self.stdout
        return_code = (0) if is_success else (1)
        stderr, stdout = ('', stdout) if is_success else ('err', stdout)
        if self.errmsg:
            stderr = [self.errmsg]
        fake_result.set_std(stderr, stdout, return_code)
        return fake_result


class FakeCmdResult(mock.Mock):
    def set_std(self, stderr, stdout, return_code):
        self.stderr = stderr
        self.stdout = stdout
        self.return_code = return_code

    def get_stderr(self):
        return self.stderr

    def get_stdout(self):
        return self.stdout

    def get_return_code(self):
        return self.return_code


class FakeTransport(mock.Mock):
    pass


@ddt
class TestKubernetesHelm(base.TestCase):
    def setUp(self):
        super(TestKubernetesHelm, self).setUp()
        self.kubernetes = kubernetes_driver.Kubernetes()
        self.kubernetes.STACK_RETRIES = 1
        self.kubernetes.STACK_RETRY_WAIT = 5
        self.k8s_client_dict = fakes.fake_k8s_client_dict()
        self.context = context.get_admin_context()
        self.vnf_instance = fd_utils.get_vnf_instance_object()
        self.package_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "../../../../etc/samples/etsi/nfv/test_cnf_helmchart")
        self._mock_remote_command_executor()
        self._mock_transport()
        self.helm_client = helm_client.HelmClient('127.0.0.1', 'user', 'pass')
        self.helm_client.commander = FakeCommander()

    def _mock_remote_command_executor(self):
        self.commander = mock.Mock(wraps=FakeRemoteCommandExecutor())
        fake_commander = mock.Mock()
        fake_commander.return_value = self.commander
        self._mock(
            'tacker.common.cmd_executer.RemoteCommandExecutor',
            fake_commander)

    def _mock_transport(self):
        self.transport = mock.Mock(wraps=FakeTransport())
        fake_transport = mock.Mock()
        fake_transport.return_value = self.transport
        self._mock('paramiko.Transport', fake_transport)

    def _mock(self, target, new=mock.DEFAULT):
        patcher = mock.patch(target, new)
        return patcher.start()

    @mock.patch.object(eventlet, 'monkey_patch')
    def test_execute_command_success(self, mock_monkey_patch):
        self.helm_client.commander.config(True)
        ssh_command = 'helm install'
        timeout = 120
        retry = 1
        self.helm_client._execute_command(
            ssh_command, timeout, retry)

    @mock.patch.object(eventlet, 'monkey_patch')
    def test_execute_command_failed(self, mock_monkey_patch):
        self.helm_client.commander.config(False)
        ssh_command = 'helm install'
        timeout = 120
        retry = 1
        self.assertRaises(vnfm.HelmClientRemoteCommandError,
                          self.helm_client._execute_command,
                          ssh_command, timeout, retry)

    @mock.patch.object(eventlet, 'monkey_patch')
    @mock.patch.object(FakeCommander, 'execute_command')
    def test_execute_command_timeout(self, mock_execute_command,
                                     mock_monkey_patch):
        mock_execute_command.side_effect = eventlet.timeout.Timeout
        ssh_command = 'helm install'
        timeout = 120
        retry = 1
        self.assertRaises(vnfm.HelmClientOtherError,
                          self.helm_client._execute_command,
                          ssh_command, timeout, retry)

    @mock.patch.object(eventlet, 'monkey_patch')
    def test_helmclient_get_value_nested_param(self, mock_monkey_patch):
        stdout = ['{"foo":{"bar":1}}']
        self.helm_client.commander.config(True, stdout=stdout)
        res = self.helm_client.get_value('fake_release_name', '', 'foo.bar')
        self.assertEqual(res, 1)

    @mock.patch.object(eventlet, 'monkey_patch')
    def test_helmclient_get_value_missing_param(self, mock_monkey_patch):
        stdout = ['{"foo":1}']
        self.helm_client.commander.config(True, stdout=stdout)
        self.assertRaises(vnfm.HelmClientMissingParamsError,
                          self.helm_client.get_value,
                          'fake_release_name', '', 'foo.bar')

    @mock.patch('tacker.objects.vnf_instance.VnfInstance.save')
    @mock.patch.object(objects.VnfPackageVnfd, "get_by_id")
    @mock.patch('tacker.vnflcm.utils._get_vnfd_dict')
    def test_pre_instantiation_vnf_helm(self, mock_vnfd_dict,
                                        mock_vnf_package_vnfd_get_by_id,
                                        mock_save):
        vnf_instance = fd_utils.get_vnf_instance_object()
        vim_connection_info = fakes.fake_vim_connection_info_with_extra()
        vnf_software_images = None
        vnf_package_path = self.package_path
        instantiate_vnf_req = fakes.fake_inst_vnf_req_for_helmchart()
        mock_vnfd_dict.return_value = vnflcm_fakes.vnfd_dict_cnf()
        mock_vnf_package_vnfd_get_by_id.return_value = (
            vnflcm_fakes.return_vnf_package_vnfd())
        vnf_resources = self.kubernetes.pre_instantiation_vnf(
            self.context, vnf_instance, vim_connection_info,
            vnf_software_images,
            instantiate_vnf_req, vnf_package_path)
        self.assertEqual(vnf_resources, {})

    @mock.patch('tacker.objects.vnf_instance.VnfInstance.save')
    @mock.patch.object(objects.VnfPackageVnfd, "get_by_id")
    @mock.patch('tacker.vnflcm.utils._get_vnfd_dict')
    def test_pre_helm_install_with_bool_param(self, mock_vnfd_dict,
                                              mock_vnf_package_vnfd_get_by_id,
                                              mock_save):
        vnf_instance = fd_utils.get_vnf_instance_object()
        vim_connection_info = fakes.fake_vim_connection_info_with_extra()
        vnf_software_images = None
        vnf_package_path = self.package_path
        instantiate_vnf_req = fakes.fake_inst_vnf_req_for_helmchart()
        instantiate_vnf_req.additional_params['use_helm'] = True
        using_helm_inst_params = instantiate_vnf_req.additional_params[
            'using_helm_install_param']
        using_helm_inst_params[0]['exthelmchart'] = True
        using_helm_inst_params[1]['exthelmchart'] = False
        mock_vnfd_dict.return_value = vnflcm_fakes.vnfd_dict_cnf()
        mock_vnf_package_vnfd_get_by_id.return_value = (
            vnflcm_fakes.return_vnf_package_vnfd())
        vnf_resources = self.kubernetes.pre_instantiation_vnf(
            self.context, vnf_instance, vim_connection_info,
            vnf_software_images,
            instantiate_vnf_req, vnf_package_path)
        self.assertEqual(vnf_resources, {})

    def test_pre_helm_install_invaid_vimconnectioninfo_no_helm_info(self):
        vnf_instance = fd_utils.get_vnf_instance_object()
        vim_connection_info = fakes.fake_vim_connection_info_with_extra()
        del vim_connection_info.extra['helm_info']
        vnf_package_path = self.package_path
        instantiate_vnf_req = fakes.fake_inst_vnf_req_for_helmchart()
        exc = self.assertRaises(vnfm.InvalidVimConnectionInfo,
                                self.kubernetes._pre_helm_install,
                                self.context, vnf_instance,
                                vim_connection_info, instantiate_vnf_req,
                                vnf_package_path)
        msg = ("Invalid vim_connection_info: "
               "helm_info is missing in vim_connection_info.extra.")
        self.assertEqual(msg, exc.format_message())

    def test_pre_helm_install_invaid_vimconnectioninfo_no_masternode_ip(self):
        vnf_instance = fd_utils.get_vnf_instance_object()
        vim_connection_info = fakes.fake_vim_connection_info_with_extra(
            del_field='masternode_ip')
        vnf_package_path = self.package_path
        instantiate_vnf_req = fakes.fake_inst_vnf_req_for_helmchart()
        exc = self.assertRaises(vnfm.InvalidVimConnectionInfo,
                                self.kubernetes._pre_helm_install,
                                self.context, vnf_instance,
                                vim_connection_info, instantiate_vnf_req,
                                vnf_package_path)
        msg = ("Invalid vim_connection_info: "
               "content of helm_info is invalid.")
        self.assertEqual(msg, exc.format_message())

    def test_pre_helm_install_invalid_helm_param(self):
        vnf_instance = fd_utils.get_vnf_instance_object()
        vim_connection_info = fakes.fake_vim_connection_info_with_extra()
        vnf_package_path = self.package_path
        instantiate_vnf_req = fakes.fake_inst_vnf_req_for_helmchart(
            external=True)
        using_helm_inst_params = instantiate_vnf_req.additional_params[
            'using_helm_install_param']
        del using_helm_inst_params[0]['exthelmchart']
        exc = self.assertRaises(exceptions.InvalidInput,
                                self.kubernetes._pre_helm_install,
                                self.context, vnf_instance,
                                vim_connection_info, instantiate_vnf_req,
                                vnf_package_path)
        msg = ("Parameter input values missing for the key '{param}'".format(
            param='exthelmchart'))
        self.assertEqual(msg, exc.format_message())

    def test_pre_helm_install_empty_helm_param(self):
        vnf_instance = fd_utils.get_vnf_instance_object()
        vim_connection_info = fakes.fake_vim_connection_info_with_extra()
        vnf_package_path = self.package_path
        instantiate_vnf_req = fakes.fake_inst_vnf_req_for_helmchart(
            external=False, local=False)
        exc = self.assertRaises(exceptions.InvalidInput,
                                self.kubernetes._pre_helm_install,
                                self.context, vnf_instance,
                                vim_connection_info, instantiate_vnf_req,
                                vnf_package_path)
        msg = ("Parameter input values missing for the key '{param}'".format(
            param='using_helm_install_param'))
        self.assertEqual(msg, exc.format_message())

    def test_pre_helm_install_invalid_chartfile_path(self):
        vnf_instance = fd_utils.get_vnf_instance_object()
        vim_connection_info = fakes.fake_vim_connection_info_with_extra()
        vnf_package_path = self.package_path
        instantiate_vnf_req = fakes.fake_inst_vnf_req_for_helmchart(
            external=False)
        using_helm_inst_params = instantiate_vnf_req.additional_params[
            'using_helm_install_param']
        using_helm_inst_params[0]['helmchartfile_path'] = 'invalid_path'
        exc = self.assertRaises(vnfm.CnfDefinitionNotFound,
                                self.kubernetes._pre_helm_install,
                                self.context, vnf_instance,
                                vim_connection_info, instantiate_vnf_req,
                                vnf_package_path)
        msg = _("CNF definition file with path {path} is not found "
                "in vnf_artifacts.").format(
            path=using_helm_inst_params[0]['helmchartfile_path'])
        self.assertEqual(msg, exc.format_message())

    @mock.patch.object(objects.VnfPackageVnfd, "get_by_id")
    @mock.patch('tacker.vnflcm.utils._get_vnfd_dict')
    def test_pre_helm_install_missing_replica_values(
            self, mock_vnfd_dict, mock_vnf_package_vnfd_get_by_id):
        vnf_instance = fd_utils.get_vnf_instance_object()
        vim_connection_info = fakes.fake_vim_connection_info_with_extra()
        vnf_package_path = self.package_path
        instantiate_vnf_req = fakes.fake_inst_vnf_req_for_helmchart(
            external=False)
        instantiate_vnf_req.additional_params['helm_replica_values'] = {}
        mock_vnfd_dict.return_value = vnflcm_fakes.vnfd_dict_cnf()
        mock_vnf_package_vnfd_get_by_id.return_value = (
            vnflcm_fakes.return_vnf_package_vnfd())
        exc = self.assertRaises(exceptions.InvalidInput,
                                self.kubernetes._pre_helm_install,
                                self.context, vnf_instance,
                                vim_connection_info, instantiate_vnf_req,
                                vnf_package_path)
        aspect_id = 'vdu1_aspect'
        msg = f"Replica value for aspectId '{aspect_id}' is missing"
        self.assertEqual(msg, exc.format_message())

    @mock.patch.object(objects.VnfResource, 'create')
    @mock.patch.object(paramiko.Transport, 'close')
    @mock.patch.object(paramiko.SFTPClient, 'put')
    @mock.patch.object(paramiko.SFTPClient, 'from_transport')
    @mock.patch.object(paramiko.Transport, 'connect')
    @mock.patch.object(helm_client.HelmClient, '_execute_command')
    @mock.patch.object(client.AppsV1Api, 'read_namespaced_deployment')
    def test_instantiate_vnf_using_helmchart(
            self, mock_read_namespaced_deployment, mock_command,
            mock_connect, mock_from_transport, mock_put, mock_close,
            mock_vnf_resource_create):
        vnf_instance = fd_utils.get_vnf_instance_object()
        vim_connection_info = fakes.fake_vim_connection_info_with_extra()
        deployment_obj = fakes.fake_v1_deployment_for_helm()
        mock_read_namespaced_deployment.return_value = deployment_obj
        vnfd_dict = fakes.fake_vnf_dict()
        instantiate_vnf_req = fakes.fake_inst_vnf_req_for_helmchart(
            external=False)
        grant_response = None
        base_hot_dict = None
        vnf_package_path = self.package_path
        mock_command.side_effect = fakes.execute_cmd_helm_client
        result = self.kubernetes.instantiate_vnf(
            self.context, vnf_instance, vnfd_dict, vim_connection_info,
            instantiate_vnf_req, grant_response, vnf_package_path,
            base_hot_dict)
        self.assertEqual(
            result,
            "{'namespace': 'default', 'name': 'vdu1', " +
            "'apiVersion': 'apps/v1', 'kind': 'Deployment', " +
            "'status': 'Create_complete'}")
        self.assertEqual(mock_read_namespaced_deployment.call_count, 1)

    @mock.patch.object(objects.VnfResource, 'create')
    @mock.patch.object(paramiko.Transport, 'close')
    @mock.patch.object(paramiko.SFTPClient, 'put')
    @mock.patch.object(paramiko.SFTPClient, 'from_transport')
    @mock.patch.object(paramiko.Transport, 'connect')
    @mock.patch.object(helm_client.HelmClient, '_execute_command')
    @mock.patch.object(client.AppsV1Api, 'read_namespaced_deployment')
    def test_instantiate_vnf_using_helmchart_with_namespace(
            self, mock_read_namespaced_deployment, mock_command,
            mock_connect, mock_from_transport, mock_put, mock_close,
            mock_vnf_resource_create):
        vnf_instance = fd_utils.get_vnf_instance_object()
        vnf_instance.vnf_metadata['namespace'] = 'dummy_namespace'
        vim_connection_info = fakes.fake_vim_connection_info_with_extra()
        deployment_obj = fakes.fake_v1_deployment_for_helm()
        mock_read_namespaced_deployment.return_value = deployment_obj
        vnfd_dict = fakes.fake_vnf_dict()
        instantiate_vnf_req = fakes.fake_inst_vnf_req_for_helmchart(
            local=False, namespace='dummy_namespace')
        grant_response = None
        base_hot_dict = None
        vnf_package_path = self.package_path
        mock_command.side_effect = fakes.execute_cmd_helm_client
        result = self.kubernetes.instantiate_vnf(
            self.context, vnf_instance, vnfd_dict, vim_connection_info,
            instantiate_vnf_req, grant_response, vnf_package_path,
            base_hot_dict)
        self.assertEqual(
            result,
            "{'namespace': 'dummy_namespace', 'name': 'vdu1', " +
            "'apiVersion': 'apps/v1', 'kind': 'Deployment', " +
            "'status': 'Create_complete'}")
        self.assertEqual(mock_read_namespaced_deployment.call_count, 1)

    @mock.patch.object(objects.VnfResource, 'create')
    @mock.patch.object(paramiko.Transport, 'close')
    @mock.patch.object(paramiko.SFTPClient, 'put')
    @mock.patch.object(paramiko.SFTPClient, 'from_transport')
    @mock.patch.object(paramiko.Transport, 'connect')
    @mock.patch.object(helm_client.HelmClient, '_execute_command')
    @mock.patch.object(client.AppsV1Api, 'read_namespaced_deployment')
    def test_instantiate_vnf_using_helmchart_multiple_ips(
            self, mock_read_namespaced_deployment, mock_command,
            mock_connect, mock_from_transport, mock_put, mock_close,
            mock_vnf_resource_create):
        vnf_instance = fd_utils.get_vnf_instance_object()
        vim_connection_info = fakes.fake_vim_connection_info_with_extra(
            multi_ip=True)
        deployment_obj = fakes.fake_v1_deployment_for_helm()
        mock_read_namespaced_deployment.return_value = deployment_obj
        vnfd_dict = fakes.fake_vnf_dict()
        instantiate_vnf_req = fakes.fake_inst_vnf_req_for_helmchart(
            external=False)
        grant_response = None
        base_hot_dict = None
        vnf_package_path = self.package_path
        mock_command.side_effect = fakes.execute_cmd_helm_client
        result = self.kubernetes.instantiate_vnf(
            self.context, vnf_instance, vnfd_dict, vim_connection_info,
            instantiate_vnf_req, grant_response, vnf_package_path,
            base_hot_dict)
        self.assertEqual(
            result,
            "{'namespace': 'default', 'name': 'vdu1', " +
            "'apiVersion': 'apps/v1', 'kind': 'Deployment', " +
            "'status': 'Create_complete'}")
        self.assertEqual(mock_read_namespaced_deployment.call_count, 1)

    @mock.patch.object(paramiko.Transport, 'close')
    @mock.patch.object(paramiko.SFTPClient, 'put')
    @mock.patch.object(paramiko.SFTPClient, 'from_transport')
    @mock.patch.object(paramiko.Transport, 'connect')
    @mock.patch.object(helm_client.HelmClient, '_execute_command')
    def test_instantiate_vnf_using_helmchart_put_helmchart_fail(
            self, mock_command,
            mock_connect, mock_from_transport, mock_put, mock_close):
        vnf_instance = fd_utils.get_vnf_instance_object()
        vim_connection_info = fakes.fake_vim_connection_info_with_extra()
        vnfd_dict = fakes.fake_vnf_dict()
        instantiate_vnf_req = fakes.fake_inst_vnf_req_for_helmchart(
            external=False)
        grant_response = None
        base_hot_dict = None
        vnf_package_path = self.package_path
        mock_command.side_effect = fakes.execute_cmd_helm_client
        mock_from_transport.side_effect = paramiko.SSHException()
        self.assertRaises(paramiko.SSHException,
            self.kubernetes.instantiate_vnf,
            self.context, vnf_instance, vnfd_dict, vim_connection_info,
            instantiate_vnf_req, grant_response, vnf_package_path,
            base_hot_dict)

    @mock.patch.object(helm_client.HelmClient, '_execute_command')
    @mock.patch.object(client.CoreV1Api, 'list_namespaced_pod')
    @mock.patch.object(objects.VnfPackageVnfd, 'get_by_id')
    @mock.patch('tacker.vnflcm.utils._get_vnfd_dict')
    def test_post_vnf_instantiation_using_helmchart(
            self, mock_vnfd_dict, mock_vnf_package_vnfd_get_by_id,
            mock_list_namespaced_pod, mock_command):
        vim_connection_info = fakes.fake_vim_connection_info_with_extra()
        mock_vnfd_dict.return_value = vnflcm_fakes.vnfd_dict_cnf()
        mock_vnf_package_vnfd_get_by_id.return_value = \
            vnflcm_fakes.return_vnf_package_vnfd()
        mock_list_namespaced_pod.return_value =\
            client.V1PodList(items=[
                fakes.get_fake_pod_info(kind='Deployment', name='vdu1')])
        instantiate_vnf_req = fakes.fake_inst_vnf_req_for_helmchart(
            external=False)
        mock_command.side_effect = fakes.execute_cmd_helm_client
        self.kubernetes.post_vnf_instantiation(
            context=self.context,
            vnf_instance=self.vnf_instance,
            vim_connection_info=vim_connection_info,
            instantiate_vnf_req=instantiate_vnf_req)
        self.assertEqual(mock_list_namespaced_pod.call_count, 1)
        # validate stored VnfcResourceInfo
        vnfc_resource_info_after = \
            self.vnf_instance.instantiated_vnf_info.vnfc_resource_info
        self.assertEqual(len(vnfc_resource_info_after), 1)
        expected_pod = fakes.get_fake_pod_info('Deployment', 'vdu1')
        self.assertEqual(
            vnfc_resource_info_after[0].compute_resource.resource_id,
            expected_pod.metadata.name)
        self.assertEqual(vnfc_resource_info_after[0].compute_resource.
            vim_level_resource_type, 'Deployment')
        self.assertEqual(vnfc_resource_info_after[0].vdu_id, 'VDU1')
        metadata_after = vnfc_resource_info_after[0].metadata
        self.assertEqual(jsonutils.loads(
            metadata_after.get('Deployment')).get('name'), 'vdu1')

    @mock.patch.object(helm_client.HelmClient, '_execute_command')
    @mock.patch.object(vim_client.VimClient, 'get_vim')
    def test_delete_using_helmchart(
            self, mock_get_vim, mock_command):
        vnf_id = 'fake_vnf_id'
        mock_get_vim.return_value = fakes.fake_k8s_vim_obj()
        vim_connection_info = fakes.fake_vim_connection_info_with_extra()
        instantiate_vnf_req = fakes.fake_inst_vnf_req_for_helmchart(
            external=False)
        vnf_instance = copy.deepcopy(self.vnf_instance)
        vnf_instance.vim_connection_info = [vim_connection_info]
        vnf_instance.instantiated_vnf_info.additional_params = \
            instantiate_vnf_req.additional_params
        terminate_vnf_req = objects.TerminateVnfRequest()
        mock_command.side_effect = fakes.execute_cmd_helm_client
        self.kubernetes.delete(plugin=None, context=self.context,
                               vnf_id=vnf_id,
                               auth_attr=utils.get_vim_auth_obj(),
                               vnf_instance=vnf_instance,
                               terminate_vnf_req=terminate_vnf_req)

    @mock.patch.object(helm_client.HelmClient, '_execute_command')
    @mock.patch.object(vim_client.VimClient, 'get_vim')
    def test_delete_using_helmchart_with_namespace(
            self, mock_get_vim, mock_command):
        vnf_id = 'fake_vnf_id'
        mock_get_vim.return_value = fakes.fake_k8s_vim_obj()
        vim_connection_info = fakes.fake_vim_connection_info_with_extra()
        instantiate_vnf_req = fakes.fake_inst_vnf_req_for_helmchart(
            local=False, namespace='dummy_namespace')
        vnf_instance = copy.deepcopy(self.vnf_instance)
        vnf_instance.vim_connection_info = [vim_connection_info]
        vnf_instance.instantiated_vnf_info.additional_params = \
            instantiate_vnf_req.additional_params
        terminate_vnf_req = objects.TerminateVnfRequest()
        mock_command.side_effect = fakes.execute_cmd_helm_client
        self.kubernetes.delete(plugin=None, context=self.context,
                               vnf_id=vnf_id,
                               auth_attr=utils.get_vim_auth_obj(),
                               vnf_instance=vnf_instance,
                               terminate_vnf_req=terminate_vnf_req)

    @mock.patch.object(helm_client.HelmClient, '_execute_command')
    @mock.patch.object(vim_client.VimClient, 'get_vim')
    @mock.patch.object(client.AppsV1Api, 'read_namespaced_deployment')
    @mock.patch.object(objects.VnfResourceList, 'get_by_vnf_instance_id')
    def test_delete_wait_using_helmchart(
            self, mock_vnf_resource_list, mock_read_namespaced_deployment,
            mock_get_vim, mock_command):
        vnf_id = 'fake_vnf_id'
        mock_get_vim.return_value = fakes.fake_k8s_vim_obj()
        vim_connection_info = fakes.fake_vim_connection_info_with_extra()
        instantiate_vnf_req = fakes.fake_inst_vnf_req_for_helmchart(
            external=False)
        vnf_instance = copy.deepcopy(self.vnf_instance)
        vnf_instance.vim_connection_info = [vim_connection_info]
        vnf_instance.instantiated_vnf_info.additional_params = \
            instantiate_vnf_req.additional_params
        vnf_resource = models.VnfResource()
        vnf_resource.vnf_instance_id = vnf_instance.id
        vnf_resource.resource_name = 'default,vdu1'
        vnf_resource.resource_type = 'apps/v1,Deployment'
        mock_vnf_resource_list.return_value = [vnf_resource]
        mock_command.side_effect = fakes.execute_cmd_helm_client
        self.kubernetes.delete_wait(plugin=None, context=self.context,
                                    vnf_id=vnf_id,
                                    auth_attr=utils.get_vim_auth_obj(),
                                    region_name=None,
                                    vnf_instance=vnf_instance)
        self.assertEqual(mock_read_namespaced_deployment.call_count, 1)

    @mock.patch.object(helm_client.HelmClient, '_execute_command')
    @mock.patch.object(vim_client.VimClient, 'get_vim')
    @mock.patch.object(client.AppsV1Api, 'read_namespaced_deployment')
    @mock.patch.object(objects.VnfResourceList, 'get_by_vnf_instance_id')
    def test_delete_wait_using_helmchart_unknown_apiversion(
            self, mock_vnf_resource_list, mock_read_namespaced_deployment,
            mock_get_vim, mock_command):
        vnf_id = 'fake_vnf_id'
        mock_get_vim.return_value = fakes.fake_k8s_vim_obj()
        vim_connection_info = fakes.fake_vim_connection_info_with_extra()
        instantiate_vnf_req = fakes.fake_inst_vnf_req_for_helmchart(
            local=False)
        vnf_instance = copy.deepcopy(self.vnf_instance)
        vnf_instance.vim_connection_info = [vim_connection_info]
        vnf_instance.instantiated_vnf_info.additional_params = \
            instantiate_vnf_req.additional_params
        vnf_resource = models.VnfResource()
        vnf_resource.vnf_instance_id = vnf_instance.id
        vnf_resource.resource_name = 'default,vdu1'
        vnf_resource.resource_type = 'apps/v1unknown,Deployment'
        mock_vnf_resource_list.return_value = [vnf_resource]
        mock_command.side_effect = fakes.execute_cmd_helm_client
        self.kubernetes.delete_wait(plugin=None, context=self.context,
                                    vnf_id=vnf_id,
                                    auth_attr=utils.get_vim_auth_obj(),
                                    region_name=None,
                                    vnf_instance=vnf_instance)
        self.assertEqual(mock_read_namespaced_deployment.call_count, 0)

    @mock.patch.object(helm_client.HelmClient, '_execute_command')
    @mock.patch.object(vim_client.VimClient, 'get_vim')
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    def test_scale_in_with_local_helmchart(self, mock_vnf_instance_get_by_id,
                                           mock_get_vim, mock_command):
        policy = fakes.get_scale_policy(type='in', aspect_id='vdu1_aspect',
                                        vdu_name='myrelease-ext-mychart-ext')
        scale_status = objects.ScaleInfo(
            aspect_id='vdu1_aspect', scale_level=1)
        mock_get_vim.return_value = fakes.fake_k8s_vim_obj()
        vim_connection_info = fakes.fake_vim_connection_info_with_extra()
        instantiate_vnf_req = fakes.fake_inst_vnf_req_for_helmchart(
            local=False)
        vnf_instance = copy.deepcopy(self.vnf_instance)
        vnf_instance.vim_connection_info = [vim_connection_info]
        vnf_instance.scale_status = [scale_status]
        vnf_instance.instantiated_vnf_info.additional_params = \
            instantiate_vnf_req.additional_params
        mock_vnf_instance_get_by_id.return_value = vnf_instance
        mock_command.side_effect = fakes.execute_cmd_helm_client
        self.kubernetes.scale(context=self.context, plugin=None,
                              auth_attr=utils.get_vim_auth_obj(),
                              policy=policy,
                              region_name=None)

    @mock.patch.object(helm_client.HelmClient, '_execute_command')
    @mock.patch.object(vim_client.VimClient, 'get_vim')
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    def test_scale_out_with_ext_helmchart(self, mock_vnf_instance_get_by_id,
                                          mock_get_vim, mock_command):
        policy = fakes.get_scale_policy(type='out', aspect_id='vdu1_aspect',
                                        vdu_name='myrelease-local-localhelm')
        scale_status = objects.ScaleInfo(
            aspect_id='vdu1_aspect', scale_level=1)
        mock_get_vim.return_value = fakes.fake_k8s_vim_obj()
        vim_connection_info = fakes.fake_vim_connection_info_with_extra()
        instantiate_vnf_req = fakes.fake_inst_vnf_req_for_helmchart(
            external=False, namespace='dummy_namespace')
        vnf_instance = copy.deepcopy(self.vnf_instance)
        vnf_instance.vim_connection_info = [vim_connection_info]
        vnf_instance.scale_status = [scale_status]
        vnf_instance.instantiated_vnf_info.additional_params = \
            instantiate_vnf_req.additional_params
        mock_vnf_instance_get_by_id.return_value = vnf_instance
        mock_command.side_effect = fakes.execute_cmd_helm_client
        self.kubernetes.scale(context=self.context, plugin=None,
                              auth_attr=utils.get_vim_auth_obj(),
                              policy=policy,
                              region_name=None)

    @mock.patch.object(helm_client.HelmClient, '_execute_command')
    @mock.patch.object(vim_client.VimClient, 'get_vim')
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    def test_scale_in_less_than_min_replicas(self, mock_vnf_instance_get_by_id,
                                             mock_get_vim, mock_command):
        policy = fakes.get_scale_policy(type='in', aspect_id='vdu1_aspect',
                                        vdu_name='myrelease-ext-mychart-ext')
        scale_status = objects.ScaleInfo(
            aspect_id='vdu1_aspect', scale_level=1)
        mock_get_vim.return_value = fakes.fake_k8s_vim_obj()
        vim_connection_info = fakes.fake_vim_connection_info_with_extra()
        instantiate_vnf_req = fakes.fake_inst_vnf_req_for_helmchart(
            local=False)
        vnf_instance = copy.deepcopy(self.vnf_instance)
        vnf_instance.vim_connection_info = [vim_connection_info]
        vnf_instance.scale_status = [scale_status]
        vnf_instance.instantiated_vnf_info.additional_params = \
            instantiate_vnf_req.additional_params
        mock_vnf_instance_get_by_id.return_value = vnf_instance
        mock_command.side_effect = [['{"replicaCount":1}'], '']
        exc = self.assertRaises(vnfm.CNFScaleFailed,
                                self.kubernetes.scale,
                                self.context, None, utils.get_vim_auth_obj(),
                                policy, None)
        msg = ("CNF Scale Failed with reason: The number of target replicas "
               "after scaling [0] is out of range")
        self.assertEqual(msg, exc.format_message())

    @mock.patch.object(helm_client.HelmClient, '_execute_command')
    @mock.patch.object(vim_client.VimClient, 'get_vim')
    @mock.patch.object(objects.VnfInstance, "get_by_id")
    def test_scale_out_over_max_replicas(self, mock_vnf_instance_get_by_id,
                                         mock_get_vim, mock_command):
        policy = fakes.get_scale_policy(type='out', aspect_id='vdu1_aspect',
                                        vdu_name='myrelease-local-localhelm')
        scale_status = objects.ScaleInfo(
            aspect_id='vdu1_aspect', scale_level=1)
        mock_get_vim.return_value = fakes.fake_k8s_vim_obj()
        vim_connection_info = fakes.fake_vim_connection_info_with_extra()
        instantiate_vnf_req = fakes.fake_inst_vnf_req_for_helmchart(
            external=False)
        vnf_instance = copy.deepcopy(self.vnf_instance)
        vnf_instance.vim_connection_info = [vim_connection_info]
        vnf_instance.scale_status = [scale_status]
        vnf_instance.instantiated_vnf_info.additional_params = \
            instantiate_vnf_req.additional_params
        mock_vnf_instance_get_by_id.return_value = vnf_instance
        mock_command.side_effect = [['{"replicaCount":3}'], '']
        exc = self.assertRaises(vnfm.CNFScaleFailed,
                                self.kubernetes.scale,
                                self.context, None, utils.get_vim_auth_obj(),
                                policy, None)
        msg = ("CNF Scale Failed with reason: The number of target replicas "
               "after scaling [4] is out of range")
        self.assertEqual(msg, exc.format_message())
