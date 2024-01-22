# Copyright (C) 2023 Nippon Telegraph and Telephone Corporation
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

from oslo_log import log as logging

from tacker.common import exceptions
from tacker.objects import vnf_package_vnfd
from tacker.sol_refactored.common import config
from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.common import vnf_instance_utils as inst_utils
from tacker.sol_refactored import objects
from tacker.sol_refactored.objects.v2 import fields as v2fields

import json
import os
import shutil
import subprocess
import tacker.conf

LOG = logging.getLogger(__name__)

CONF = config.CONF


class Terraform():
    '''Implements Terraform in Tacker'''

    def __init__(self):
        pass

    def instantiate(self, req, inst, grant_req, grant, vnfd):
        '''Implements instantiate using Terraform commands'''

        vim_conn_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
        tf_dir_path = req.additionalParams.get('tf_dir_path')
        tf_var_path = req.additionalParams.get('tf_var_path')
        working_dir = self._get_tf_vnfpkg(
            inst.id, grant_req.vnfdId, tf_dir_path)

        self._generate_provider_tf(vim_conn_info, working_dir)
        self._instantiate(vim_conn_info, working_dir, tf_var_path)
        self._make_instantiated_vnf_info(req, inst, grant_req,
                                         grant, vnfd, working_dir,
                                         tf_dir_path, tf_var_path)

    def _instantiate(self, vim_conn_info, working_dir, tf_var_path):
        '''Executes terraform init, terraform plan, and terraform apply'''

        access_info = vim_conn_info.get('accessInfo', {})

        init_cmd = ['terraform', 'init']
        self._exec_cmd(init_cmd, cwd=working_dir)
        LOG.info("Terraform init completed successfully.")

        plan_cmd = self._gen_plan_cmd(access_info, tf_var_path)
        self._exec_cmd(plan_cmd, cwd=working_dir)
        LOG.info("Terraform plan completed successfully.")

        apply_cmd = self._gen_apply_cmd(access_info, tf_var_path)
        self._exec_cmd(apply_cmd, cwd=working_dir)
        LOG.info("Terraform apply completed successfully.")

    def terminate(self, req, inst, grant_req, grant, vnfd):
        '''Terminates the terraform resources managed by the current project'''

        vim_conn_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
        working_dir = f"{CONF.v2_vnfm.tf_file_dir}/{inst.id}"
        tf_var_path = inst.instantiatedVnfInfo.metadata['tf_var_path']
        self._terminate(vim_conn_info, working_dir, tf_var_path)

    def _terminate(self, vim_conn_info, working_dir, tf_var_path):
        '''Executes Terraform Destroy and removes the working_dir'''

        access_info = vim_conn_info.get('accessInfo', {})

        destroy_cmd = self._gen_destroy_cmd(access_info, tf_var_path)
        self._exec_cmd(destroy_cmd, cwd=working_dir)
        LOG.info("Terraform destroy completed successfully.")

        try:
            # Remove the working directory and its contents
            shutil.rmtree(working_dir)
            LOG.info(f"Working directory {working_dir} destroyed successfully")
        except OSError as error:
            LOG.error(f"Error destroying working directory: {error}")
            raise

    def instantiate_rollback(self, req, inst, grant_req, grant, vnfd):
        '''Calls terminate'''
        vim_conn_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
        tf_dir_path = req.additionalParams.get('tf_dir_path')
        tf_var_path = req.additionalParams.get('tf_var_path')
        working_dir = self._get_tf_vnfpkg(
            inst.id, grant_req.vnfdId, tf_dir_path)

        # NOTE: Checks the terraform.tfstate file state to call
        # the terminate function. The reason is as follows.
        #  - For fails terraform apply command, the size of
        #    the terraform.tfstate file is 0.
        #  - For fails before terraform apply command,
        #    terraform.tfstate file does not exist.
        tfstate_file = f"{working_dir}/terraform.tfstate"
        if os.path.exists(tfstate_file):
            if os.path.getsize(tfstate_file) != 0:
                self._terminate(vim_conn_info, working_dir, tf_var_path)
            else:
                shutil.rmtree(working_dir)

    def change_vnfpkg(self, req, inst, grant_req, grant, vnfd):
        '''Calls Terraform Apply and replicates new files'''

        vim_conn_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
        tf_dir_path = req.additionalParams.get('tf_dir_path')
        tf_var_path = req.additionalParams.get('tf_var_path')
        working_dir = f"{CONF.v2_vnfm.tf_file_dir}/{inst.id}"

        if req.additionalParams['upgrade_type'] == 'RollingUpdate':
            self._change_vnfpkg_rolling_update(vim_conn_info, working_dir,
                                               req.vnfdId, tf_dir_path,
                                               tf_var_path)

        self._make_instantiated_vnf_info(req, inst, grant_req,
                                         grant, vnfd, working_dir,
                                         tf_dir_path, tf_var_path)

    def _change_vnfpkg_rolling_update(self, vim_conn_info, working_dir,
                                      vnfd_id, tf_dir_path, tf_var_path):
        '''Calls Terraform Apply'''

        excluded_files = ['.terraform', '.terraform.lock.hcl',
                  'terraform.tfstate', 'provider.tf', 'provider.tf.json']

        # Delete old files (e.g main.tf, variables.tf, modules)
        for root, dirs, files in os.walk(working_dir):
            for file_name in files:
                if file_name not in excluded_files:
                    file_path = os.path.join(root, file_name)
                    if os.path.exists(file_path):
                        os.remove(file_path)
            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                if os.path.exists(dir_path):
                    shutil.rmtree(dir_path)

        # Duplicate tf files from new VNF Package
        context = tacker.context.get_admin_context()
        try:
            pkg_vnfd = vnf_package_vnfd.VnfPackageVnfd().get_by_id(
                context, vnfd_id)
        except exceptions.VnfPackageVnfdNotFound as exc:
            raise sol_ex.VnfdIdNotFound(vnfd_id=vnfd_id) from exc
        csar_path = os.path.join(CONF.vnf_package.vnf_package_csar_path,
                                pkg_vnfd.package_uuid)
        if tf_dir_path is not None:
            vnf_package_path = f"{csar_path}/{tf_dir_path}"
        else:
            vnf_package_path = csar_path

        # Copy files from new VNF Package
        for file_name in os.listdir(vnf_package_path):
            if file_name not in excluded_files:
                source_path = os.path.join(vnf_package_path, file_name)
                if os.path.exists(source_path):
                    if os.path.isfile(source_path):
                        shutil.copy2(source_path, working_dir)
                    elif os.path.isdir(source_path):
                        destination_dir = os.path.join(working_dir, file_name)
                        shutil.copytree(source_path, destination_dir,
                                        dirs_exist_ok=True)

        access_info = vim_conn_info.get('accessInfo', {})

        init_cmd = ['terraform', 'init', '-upgrade']
        self._exec_cmd(init_cmd, cwd=working_dir)
        LOG.info("Terraform init completed successfully.")

        plan_cmd = self._gen_plan_cmd(access_info, tf_var_path)
        self._exec_cmd(plan_cmd, cwd=working_dir)
        LOG.info("Terraform plan completed successfully.")

        apply_cmd = self._gen_apply_cmd(access_info, tf_var_path)
        self._exec_cmd(apply_cmd, cwd=working_dir)
        LOG.info("Terraform apply completed successfully.")

    def change_vnfpkg_rollback(self, req, inst, grant_req, grant, vnfd):
        '''Calls _change_vnfpkg_rolling_update function'''

        vim_conn_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
        tf_dir_path = inst.instantiatedVnfInfo.metadata['tf_dir_path']
        tf_var_path = inst.instantiatedVnfInfo.metadata['tf_var_path']
        working_dir = f"{CONF.v2_vnfm.tf_file_dir}/{inst.id}"

        if req.additionalParams['upgrade_type'] == 'RollingUpdate':
            self._change_vnfpkg_rolling_update(vim_conn_info, working_dir,
                                               inst.vnfdId, tf_dir_path,
                                               tf_var_path)

        self._make_instantiated_vnf_info(req, inst, grant_req,
                                         grant, vnfd, working_dir,
                                         tf_dir_path, tf_var_path)

    def _make_instantiated_vnf_info(self, req, inst, grant_req, grant, vnfd,
                                    working_dir, tf_dir_path, tf_var_path):
        '''Updates Tacker with information on the VNF state'''

        op = grant_req.operation
        if op == v2fields.LcmOperationType.INSTANTIATE:
            flavour_id = req.flavourId
        else:
            flavour_id = inst.instantiatedVnfInfo.flavourId

        # make new instantiatedVnfInfo and replace
        inst_vnf_info = objects.VnfInstanceV2_InstantiatedVnfInfo(
            flavourId=flavour_id,
            vnfState='STARTED',
        )

        # Specify the path to the terraform.tfstate file
        tfstate_file = f"{working_dir}/terraform.tfstate"

        # Read the contents of the file
        with open(tfstate_file, "r", encoding="utf-8") as file:
            tfstate_data = json.load(file)

        vdu_nodes = vnfd.get_vdu_nodes(flavour_id)
        vdu_ids = {value.get('properties').get('name'): key
                for key, value in vdu_nodes.items()}

        # Extract the required fields from the tfstate data
        resources = tfstate_data["resources"]

        # Define vnfcResourceInfo and vnfcInfo in a single iteration
        vnfc_resource_info_list = [
            objects.VnfcResourceInfoV2(
                id=resource['name'],
                vduId=vdu_ids.get(resource['name']),
                computeResource=objects.ResourceHandle(
                    resourceId=resource['name'],
                    vimLevelResourceType=resource['type']
                ),
                metadata={}
            )
            for resource in resources
            if (resource["type"] == "aws_instance" and
                vdu_ids.get(resource['name']))
        ]

        vnfc_info_list = [
            objects.VnfcInfoV2(
                id=f"{vnfc_res_info.vduId}-{vnfc_res_info.id}",
                vduId=vnfc_res_info.vduId,
                vnfcResourceInfoId=vnfc_res_info.id,
                vnfcState='STARTED'
            )
            for vnfc_res_info in vnfc_resource_info_list
        ]

        inst_vnf_info.vnfcResourceInfo = vnfc_resource_info_list
        inst_vnf_info.vnfcInfo = vnfc_info_list

        inst_vnf_info.metadata = {}
        # Restore metadata
        if (inst.obj_attr_is_set('instantiatedVnfInfo') and
                inst.instantiatedVnfInfo.obj_attr_is_set('metadata')):
            inst_vnf_info.metadata.update(inst.instantiatedVnfInfo.metadata)

        # Store tf_dir_path
        if op == v2fields.LcmOperationType.INSTANTIATE or tf_dir_path:
            inst_vnf_info.metadata['tf_dir_path'] = tf_dir_path

        # Store tf_var_path
        if op == v2fields.LcmOperationType.INSTANTIATE or tf_var_path:
            inst_vnf_info.metadata['tf_var_path'] = tf_var_path

        inst.instantiatedVnfInfo = inst_vnf_info

    def _get_tf_vnfpkg(self, vnf_instance_id, vnfd_id, tf_dir_path):
        """Create a VNF package with given IDs

        A path of created package is returned, or failed if vnfd_id is invalid.
        """

        # Define variables
        context = tacker.context.get_admin_context()
        try:
            pkg_vnfd = vnf_package_vnfd.VnfPackageVnfd().get_by_id(
                context, vnfd_id)
        except exceptions.VnfPackageVnfdNotFound as exc:
            raise sol_ex.VnfdIdNotFound(vnfd_id=vnfd_id) from exc
        csar_path = os.path.join(CONF.vnf_package.vnf_package_csar_path,
                                 pkg_vnfd.package_uuid)

        # Assemble paths and copy recursively
        vnf_package_path = f"{csar_path}/{tf_dir_path}"
        new_tf_dir_path = f"{CONF.v2_vnfm.tf_file_dir}/{vnf_instance_id}"
        os.makedirs(new_tf_dir_path, exist_ok=True)
        # NOTE: the creation of the directory /var/lib/tacker/terraform
        # should be completed during the installation of Tacker.
        shutil.copytree(vnf_package_path, new_tf_dir_path, dirs_exist_ok=True)

        return new_tf_dir_path

    def _generate_provider_tf(self, vim_conn_info, main_tf_path):
        '''Creates provider.tf beside main.tf'''

        # Read vimConnectionInfo for information
        access_info = vim_conn_info.get('accessInfo', {})
        interface_info = vim_conn_info.get('interfaceInfo', {})
        provider_type = interface_info.get('providerType')
        provider_version = interface_info.get('providerVersion')

        # Create provider.tf content using the above information
        content = {
            "variable": {},
            "terraform": {
                "required_version": ">=0.13",
                "required_providers": {
                    provider_type: {
                        "source": f"hashicorp/{provider_type}",
                        "version": f"~> {provider_version}"
                    }
                }
            },
            "provider": {
                provider_type: {}
            }
        }

        # Add accessInfo keys as variables and provider arguments
        for key, value in access_info.items():
            if key == "endpoints":
                content["provider"][provider_type][key] = value
                continue
            content["variable"][key] = {
                "type": "string"
            }
            content["provider"][provider_type][key] = f"${{var.{key}}}"

        # Save the provider.tf file
        provider_tf_path = os.path.join(main_tf_path, 'provider.tf.json')
        with open(provider_tf_path, 'w', encoding='utf-8') as f:
            json.dump(content, f, indent=4)

        return provider_tf_path

    def _gen_cmd_args(self, access_info, tf_var_path):
        args = []
        for key, value in access_info.items():
            if key == "endpoints":
                continue
            args.extend(['-var', f'{key}={value}'])
        if tf_var_path:
            args.extend(['-var-file', tf_var_path])
        return args

    def _gen_plan_cmd(self, access_info, tf_var_path, extra_args=None):
        cmd = ['terraform', 'plan']
        args = self._gen_cmd_args(access_info, tf_var_path)
        if extra_args:
            args.extend(extra_args)
        return cmd + args

    def _gen_apply_cmd(self, access_info, tf_var_path):
        cmd = ['terraform', 'apply', '-auto-approve']
        args = self._gen_cmd_args(access_info, tf_var_path)
        return cmd + args

    def _gen_destroy_cmd(self, access_info, tf_var_path):
        cmd = ['terraform', 'destroy', '-auto-approve']
        args = self._gen_cmd_args(access_info, tf_var_path)
        return cmd + args

    def _exec_cmd(self, cmd, cwd,
                  stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                  check=True, text=True):
        """A helper for subprocess.run()

        Exec a command through subprocess.run() with common options among
        commands used in this package. All the args other than self and cmd
        the same as for subprocess.run().
        """
        try:
            subprocess.run(cmd, cwd=cwd, stdout=stdout, stderr=stderr,
                           check=check, text=text)
        except subprocess.CalledProcessError as error:
            raise sol_ex.TerraformOperationFailed(sol_detail=str(error))
