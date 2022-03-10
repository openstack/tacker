# Copyright (C) 2020 NTT DATA
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

import ast
import copy
from datetime import datetime
import functools
import hashlib
import inspect
import os
import re
import traceback

from oslo_config import cfg
from oslo_log import log as logging
from oslo_serialization import jsonutils
from oslo_utils import encodeutils
from oslo_utils import excutils
from oslo_utils import timeutils
from toscaparser import tosca_template

from tacker.common import driver_manager
from tacker.common import exceptions
from tacker.common import log
from tacker.common import safe_utils
from tacker.common import utils
from tacker.conductor.conductorrpc import vnf_lcm_rpc
from tacker import manager
from tacker import objects
from tacker.objects import fields
from tacker.objects.fields import ErrorPoint as EP
from tacker.vnflcm import abstract_driver
from tacker.vnflcm import utils as vnflcm_utils

LOG = logging.getLogger(__name__)
CONF = cfg.CONF
DEFAULT_VNFLCM_MGMT_DRIVER = "vnflcm_noop"


@utils.expects_func_args('vnf_info', 'vnf_instance', 'scale_vnf_request')
def revert_to_error_scale(function):
    """Decorator to revert task_state to error  on failure."""

    @functools.wraps(function)
    def decorated_function(self, context, *args, **kwargs):
        try:
            return function(self, context, *args, **kwargs)
        except Exception as ex:
            with excutils.save_and_reraise_exception():
                wrapped_func = safe_utils.get_wrapped_function(function)
                keyed_args = inspect.getcallargs(wrapped_func, self, context,
                                                 *args, **kwargs)
                try:
                    vnf_info = keyed_args['vnf_info']
                    vnf_instance = keyed_args['vnf_instance']
                    scale_vnf_request = keyed_args['scale_vnf_request']
                    vim_info = vnflcm_utils._get_vim(context,
                            vnf_instance.vim_connection_info)
                    vim_connection_info = \
                        objects.VimConnectionInfo.obj_from_primitive(
                            vim_info, context)
                    if vnf_info.get('resource_changes'):
                        resource_changes = vnf_info.get('resource_changes')
                    else:
                        resource_changes = self._scale_resource_update(context,
                                            vnf_info,
                                            vnf_instance,
                                            scale_vnf_request,
                                            vim_connection_info,
                                            error=True)
                except Exception as e:
                    LOG.warning(traceback.format_exc())
                    LOG.warning("Failed to scale resource update "
                                "instance %(id)s. Error: %(error)s",
                                {"id": vnf_instance.id, "error": e})

                try:
                    self._vnfm_plugin._update_vnf_scaling_status_err(context,
                                                                     vnf_info)
                except Exception as e:
                    LOG.warning("Failed to revert scale info for event "
                                "instance %(id)s. Error: %(error)s",
                                {"id": vnf_instance.id, "error": e})
                try:
                    vnf_instance.task_state = None
                    self._vnf_instance_update(context, vnf_instance)
                except Exception as e:
                    LOG.warning("Failed to revert instantiation info for vnf "
                                "instance %(id)s. Error: %(error)s",
                                {"id": vnf_instance.id, "error": e})
                problem = objects.ProblemDetails(status=500,
                                                 detail=str(ex))

                try:
                    timestamp = datetime.utcnow()
                    vnf_lcm_op_occ = vnf_info['vnf_lcm_op_occ']
                    vnf_lcm_op_occ.operation_state = 'FAILED_TEMP'
                    vnf_lcm_op_occ.state_entered_time = timestamp
                    vnf_lcm_op_occ.resource_changes = resource_changes
                    vnf_lcm_op_occ.error = problem
                    vnf_lcm_op_occ.error_point = \
                        vnf_info['current_error_point']
                    vnf_lcm_op_occ.save()
                except Exception as e:
                    LOG.warning("Failed to update vnf_lcm_op_occ for vnf "
                                "instance %(id)s. Error: %(error)s",
                                {"id": vnf_instance.id, "error": e})

                try:
                    notification = vnf_info['notification']
                    notification['notificationStatus'] = 'RESULT'
                    notification['operationState'] = 'FAILED_TEMP'
                    notification['error'] = problem.to_dict()
                    resource_dict = resource_changes.to_dict()
                    if resource_dict.get('affected_vnfcs'):
                        notification['affectedVnfcs'] =\
                            jsonutils.dump_as_bytes(
                            resource_dict.get('affected_vnfcs'))
                    if resource_dict.get('affected_virtual_links'):
                        notification['affectedVirtualLinks'] =\
                            jsonutils.dump_as_bytes(
                            resource_dict.get('affected_virtual_links'))
                    if resource_dict.get('affected_virtual_storages'):
                        notification['affectedVirtualStorages'] =\
                            jsonutils.dump_as_bytes(
                            resource_dict.get('affected_virtual_storages'))
                    self.rpc_api.send_notification(context, notification)
                except Exception as e:
                    LOG.warning("Failed to revert scale info for vnf "
                                "instance %(id)s. Error: %(error)s",
                                {"id": vnf_instance.id, "error": e})

    return decorated_function


@utils.expects_func_args('vnf_instance')
def revert_to_error_task_state(function):
    """Decorator to revert task_state to error  on failure."""

    @functools.wraps(function)
    def decorated_function(self, context, *args, **kwargs):
        try:
            return function(self, context, *args, **kwargs)
        except Exception:
            with excutils.save_and_reraise_exception():
                wrapped_func = safe_utils.get_wrapped_function(function)
                keyed_args = inspect.getcallargs(wrapped_func, self, context,
                                                 *args, **kwargs)
                vnf_instance = keyed_args['vnf_instance']
                previous_task_state = vnf_instance.task_state
                try:
                    self._vnf_instance_update(context, vnf_instance,
                        task_state=fields.VnfInstanceTaskState.ERROR)
                    LOG.info("Successfully reverted task state from "
                             "%(state)s to %(error)s on failure for vnf "
                             "instance %(id)s.",
                             {"state": previous_task_state,
                              "id": vnf_instance.id,
                              "error": fields.VnfInstanceTaskState.ERROR})
                except Exception as e:
                    LOG.warning("Failed to revert task state for vnf "
                                "instance %(id)s. Error: %(error)s",
                                {"id": vnf_instance.id, "error": e})

    return decorated_function


@utils.expects_func_args('vnf_info', 'vnf_instance', 'operation_params')
def revert_to_error_rollback(function):
    """Decorator to revert task_state to error  on failure."""

    @functools.wraps(function)
    def decorated_function(self, context, *args, **kwargs):
        try:
            return function(self, context, *args, **kwargs)
        except Exception as ex:
            with excutils.save_and_reraise_exception():
                wrapped_func = safe_utils.get_wrapped_function(function)
                keyed_args = inspect.getcallargs(wrapped_func, self, context,
                                                 *args, **kwargs)
                resource_changes = None
                try:
                    vnf_info = keyed_args['vnf_info']
                    vnf_instance = keyed_args['vnf_instance']
                    operation_params = keyed_args['operation_params']
                    vim_info = vnflcm_utils._get_vim(context,
                            vnf_instance.vim_connection_info)
                    vim_connection_info =\
                        objects.VimConnectionInfo.obj_from_primitive(
                            vim_info, context)
                    vnf_lcm_op_occs = vnf_info['vnf_lcm_op_occ']
                    if vnf_info.get('resource_changes'):
                        resource_changes = vnf_info.get('resource_changes')
                    else:
                        if vnf_lcm_op_occs.operation == 'SCALE':
                            scale_vnf_request =\
                                objects.ScaleVnfRequest.obj_from_primitive(
                                    operation_params, context=context)
                            scale_vnf_request_copy = \
                                copy.deepcopy(scale_vnf_request)
                            scale_vnf_request_copy.type = 'SCALE_IN'
                            resource_changes = self._scale_resource_update(
                                context,
                                vnf_info,
                                vnf_instance,
                                scale_vnf_request_copy,
                                vim_connection_info,
                                error=True)
                        else:
                            resource_changes = self._term_resource_update(
                                context,
                                vnf_info,
                                vnf_instance)
                except Exception as e:
                    LOG.warning(traceback.format_exc())
                    LOG.warning("Failed to scale resource update "
                                "instance %(id)s. Error: %(error)s",
                                {"id": vnf_instance.id, "error": e})

                try:
                    self._update_vnf_rollback_status_err(context, vnf_info)
                except Exception as e:
                    LOG.warning("Failed to revert scale info for event "
                                "instance %(id)s. Error: %(error)s",
                                {"id": vnf_instance.id, "error": e})
                try:
                    self._vnf_instance_update(context, vnf_instance)
                except Exception as e:
                    LOG.warning("Failed to revert instantiation info for vnf "
                                "instance %(id)s. Error: %(error)s",
                                {"id": vnf_instance.id, "error": e})
                problem = objects.ProblemDetails(status=500,
                                                 detail=str(ex))

                try:
                    timestamp = datetime.utcnow()
                    vnf_lcm_op_occ = vnf_info['vnf_lcm_op_occ']
                    vnf_lcm_op_occ.operation_state = 'FAILED_TEMP'
                    vnf_lcm_op_occ.state_entered_time = timestamp
                    if resource_changes:
                        vnf_lcm_op_occ.resource_changes = resource_changes
                    vnf_lcm_op_occ.error = problem
                    vnf_lcm_op_occ.save()
                except Exception as e:
                    LOG.warning("Failed to update vnf_lcm_op_occ for vnf "
                                "instance %(id)s. Error: %(error)s",
                                {"id": vnf_instance.id, "error": e})

                try:
                    notification = vnf_info['notification']
                    notification['notificationStatus'] = 'RESULT'
                    notification['operationState'] = 'FAILED_TEMP'
                    notification['error'] = problem.to_dict()
                    if resource_changes:
                        resource_dict = resource_changes.to_dict()
                        if resource_dict.get('affected_vnfcs'):
                            notification['affectedVnfcs'] = \
                                jsonutils.dump_as_bytes(
                                    resource_dict.get('affected_vnfcs'))
                        if resource_dict.get('affected_virtual_links'):
                            notification['affectedVirtualLinks'] = \
                                jsonutils.dump_as_bytes(
                                    resource_dict.get(
                                        'affected_virtual_links'))
                        if resource_dict.get('affected_virtual_storages'):
                            notification['affectedVirtualStorages'] = \
                                jsonutils.dump_as_bytes(
                                    resource_dict.get(
                                        'affected_virtual_storages'))
                    self.rpc_api.send_notification(context, notification)
                except Exception as e:
                    LOG.warning("Failed to revert scale info for vnf "
                                "instance %(id)s. Error: %(error)s",
                                {"id": vnf_instance.id, "error": e})
    return decorated_function


def config_opts():
    return [('tacker', VnfLcmDriver.OPTS)]


class VnfLcmDriver(abstract_driver.VnfInstanceAbstractDriver):
    OPTS = [
        cfg.ListOpt(
            'vnflcm_infra_driver', default=['openstack', 'kubernetes'],
            help=_('Hosting vnf drivers tacker plugin will use')
        ),
        cfg.ListOpt(
            'vnflcm_mgmt_driver', default=[DEFAULT_VNFLCM_MGMT_DRIVER],
            help=_('MGMT driver to communicate with '
                   'Hosting VNF/logical service '
                   'instance tacker plugin will use')
        )
    ]
    cfg.CONF.register_opts(OPTS, 'tacker')

    def __init__(self):
        super(VnfLcmDriver, self).__init__()
        self.rpc_api = vnf_lcm_rpc.VNFLcmRPCAPI()
        self._vnfm_plugin = manager.TackerManager.get_service_plugins()['VNFM']
        self._vnf_manager = driver_manager.DriverManager(
            'tacker.tacker.vnfm.drivers',
            cfg.CONF.tacker.vnflcm_infra_driver)
        self._mgmt_manager = driver_manager.DriverManager(
            'tacker.tacker.mgmt.drivers', cfg.CONF.tacker.vnflcm_mgmt_driver)
        self._mgmt_driver_hash = self._init_mgmt_driver_hash()

    def _init_mgmt_driver_hash(self):

        driver_hash = {}
        for mgmt_driver in cfg.CONF.tacker.vnflcm_mgmt_driver:
            path = inspect.getfile(self._mgmt_manager[mgmt_driver].__class__)
            driver_hash[mgmt_driver] = self._get_file_hash(path)
        return driver_hash

    def _vnf_instance_update(self, context, vnf_instance, **kwargs):
        """Update vnf instance in the database using kwargs as value."""

        for k, v in kwargs.items():
            setattr(vnf_instance, k, v)
        vnf_instance.save()

    def _instantiate_vnf(self, context, vnf_instance, vnf_dict,
            vim_connection_info, instantiate_vnf_req):
        vnfd_dict = vnflcm_utils._get_vnfd_dict(context, vnf_instance.vnfd_id,
                instantiate_vnf_req.flavour_id)
        vnf_package_path = vnflcm_utils._get_vnf_package_path(
            context, vnf_instance.vnfd_id)

        param_for_subs_map = vnflcm_utils._get_param_data(vnfd_dict,
                instantiate_vnf_req)

        package_uuid = vnflcm_utils._get_vnf_package_id(context,
                vnf_instance.vnfd_id)
        vnf_software_images = vnflcm_utils._create_grant_request(vnfd_dict,
                package_uuid)
        vnf_resources = self._vnf_manager.invoke(
            vim_connection_info.vim_type, 'pre_instantiation_vnf',
            context=context, vnf_instance=vnf_instance,
            vim_connection_info=vim_connection_info,
            vnf_software_images=vnf_software_images,
            instantiate_vnf_req=instantiate_vnf_req,
            vnf_package_path=vnf_package_path)

        # save the vnf resources in the db
        for _, resources in vnf_resources.items():
            for vnf_resource in resources:
                vnf_resource.create()

        vnfd_dict_to_create_final_dict = copy.deepcopy(vnfd_dict)
        final_vnf_dict = vnflcm_utils._make_final_vnf_dict(
            vnfd_dict_to_create_final_dict, vnf_instance.id,
            vnf_instance.vnf_instance_name, param_for_subs_map, vnf_dict)

        final_vnf_dict['before_error_point'] = \
            vnf_dict['before_error_point']

        try:
            instance_id = self._vnf_manager.invoke(
                vim_connection_info.vim_type, 'instantiate_vnf',
                context=context, plugin=self._vnfm_plugin,
                vnf_instance=vnf_instance,
                vnfd_dict=final_vnf_dict, grant_response=vnf_resources,
                vim_connection_info=vim_connection_info,
                vnf_package_path=vnf_package_path,
                instantiate_vnf_req=instantiate_vnf_req)
        except Exception as exp:
            with excutils.save_and_reraise_exception():
                exp.reraise = False
                LOG.error("Unable to instantiate vnf instance "
                    "%(id)s due to error : %(error)s",
                    {"id": vnf_instance.id, "error":
                    encodeutils.exception_to_unicode(exp)})
                raise exceptions.VnfInstantiationFailed(
                    id=vnf_instance.id,
                    error=encodeutils.exception_to_unicode(exp))

        if vnf_instance.instantiated_vnf_info and\
                vnf_instance.instantiated_vnf_info.instance_id != instance_id:
            # TODO(h-asahina): rename instance_id to stack_id
            vnf_instance.instantiated_vnf_info.instance_id = instance_id

        if vnf_dict['attributes'].get('scaling_group_names'):
            vnf_instance.instantiated_vnf_info.scale_status = \
                vnf_dict['scale_status']
        elif vnf_instance.instantiated_vnf_info:
            default_scale_status = vnflcm_utils.\
                get_default_scale_status(
                    context=context,
                    vnf_instance=vnf_instance,
                    vnfd_dict=vnfd_dict)
            if default_scale_status is not None:
                vnf_instance.instantiated_vnf_info.scale_status = \
                    default_scale_status

        if vnf_dict['before_error_point'] <= EP.PRE_VIM_CONTROL:
            try:
                self._vnf_manager.invoke(
                    vim_connection_info.vim_type, 'create_wait',
                    plugin=self._vnfm_plugin, context=context,
                    vnf_dict=final_vnf_dict,
                    vnf_id=final_vnf_dict['instance_id'],
                    auth_attr=vim_connection_info.access_info)

            except Exception as exp:
                with excutils.save_and_reraise_exception():
                    exp.reraise = False
                    LOG.error("Vnf creation wait failed for vnf instance "
                        "%(id)s due to error : %(error)s",
                        {"id": vnf_instance.id, "error":
                        encodeutils.exception_to_unicode(exp)})
                    raise exceptions.VnfInstantiationWaitFailed(
                        id=vnf_instance.id,
                        error=encodeutils.exception_to_unicode(exp))
        elif vnf_dict['before_error_point'] == EP.POST_VIM_CONTROL:
            try:
                self._vnf_manager.invoke(
                    vim_connection_info.vim_type, 'update_stack_wait',
                    plugin=self._vnfm_plugin, context=context,
                    vnf_dict=final_vnf_dict,
                    stack_id=instance_id,
                    auth_attr=vim_connection_info.access_info)

            except Exception as exp:
                with excutils.save_and_reraise_exception():
                    exp.reraise = False
                    LOG.error("Vnf update wait failed for vnf instance "
                        "%(id)s due to error : %(error)s",
                        {"id": vnf_instance.id, "error":
                        encodeutils.exception_to_unicode(exp)})
                    raise exceptions.VnfInstantiationWaitFailed(
                        id=vnf_instance.id,
                        error=encodeutils.exception_to_unicode(exp))

        if vnf_instance.instantiated_vnf_info.instance_id:
            self._vnf_manager.invoke(vim_connection_info.vim_type,
                                    'post_vnf_instantiation', context=context,
                                    vnf_instance=vnf_instance,
                                    vim_connection_info=vim_connection_info,
                                    instantiate_vnf_req=instantiate_vnf_req)

    def _get_file_hash(self, path):
        hash_obj = hashlib.sha256()
        with open(path) as f:
            hash_obj.update(f.read().encode('utf-8'))
        return hash_obj.hexdigest()

    def _check_mgmt_driver(self, artifact_mgmt_driver, artifacts_value,
                           vnf_package_path):
        # check implementation and artifacts exist in cfg.CONF.tacker
        if artifact_mgmt_driver not in self._mgmt_driver_hash:
            LOG.error('The {} specified in the VNFD '
                      'is inconsistent with the MgmtDriver in '
                      'the configuration file.'.format(artifact_mgmt_driver))
            raise exceptions.MgmtDriverInconsistent(
                MgmtDriver=artifact_mgmt_driver)

        # check file content
        pkg_mgmt_driver_path = os.path.join(vnf_package_path,
            artifacts_value[artifact_mgmt_driver]['file'])
        pkg_mgmt_driver_hash = self._get_file_hash(pkg_mgmt_driver_path)
        if pkg_mgmt_driver_hash == \
                self._mgmt_driver_hash[artifact_mgmt_driver]:
            return artifact_mgmt_driver
        else:
            LOG.error('The hash verification of VNF Package MgmtDriver '
                      'and Tacker MgmtDriver does not match.')
            raise exceptions.MgmtDriverHashMatchFailure()

    def _load_vnf_interface(self, context, method_name,
                            vnf_instance, vnfd_dict):
        VNF_value = vnfd_dict['topology_template']['node_templates']['VNF']
        tacker_mgmt_driver = DEFAULT_VNFLCM_MGMT_DRIVER
        interfaces_vnflcm_value = \
            VNF_value.get('interfaces', {}).get('Vnflcm', {})
        if not interfaces_vnflcm_value:
            return tacker_mgmt_driver
        artifacts_value = VNF_value.get('artifacts')
        if not artifacts_value:
            return tacker_mgmt_driver
        vnf_package_path = vnflcm_utils._get_vnf_package_path(
            context, vnf_instance.vnfd_id)

        if interfaces_vnflcm_value.get(method_name):
            artifact_mgmt_driver = interfaces_vnflcm_value.get(
                method_name).get('implementation')
            if artifact_mgmt_driver:
                tacker_mgmt_driver = self._check_mgmt_driver(
                    artifact_mgmt_driver, artifacts_value, vnf_package_path)

        return tacker_mgmt_driver

    @log.log
    def modify_vnf(self, context, vnf_lcm_opoccs,
                   body_data, vnfd_pkg_data, vnfd_id):
        # Get vnf_instance from DB by vnf_instance_id
        vnf_instance_id = vnf_lcm_opoccs.get('vnf_instance_id')
        vnf_instance = objects.VnfInstance.get_by_id(context, vnf_instance_id)
        vnfd_dict = vnflcm_utils.get_vnfd_dict(
            context, vnf_instance.vnfd_id,
            vnf_instance.instantiated_vnf_info.flavour_id)

        # modify_information_start(context, vnf_instance)
        self._mgmt_manager.invoke(
            self._load_vnf_interface(
                context, 'modify_information_start', vnf_instance, vnfd_dict),
            'modify_information_start', context=context,
            modify_vnf_request=None, vnf_instance=vnf_instance)

        # Get the old vnf package path according to vnfd_id
        old_vnf_package_path = vnflcm_utils.get_vnf_package_path(
            context, vnf_instance.vnfd_id)

        # Update vnf_instance
        try:
            _vnf_instance = objects.VnfInstance(context=context)
            updated_time = _vnf_instance.update(
                context, vnf_lcm_opoccs, body_data, vnfd_pkg_data, vnfd_id)
        except Exception as msg:
            raise Exception(str(msg))
        vnf_instance = objects.VnfInstance.get_by_id(context, vnf_instance_id)

        vim_info = vnflcm_utils.get_vim(
            context, vnf_instance.vim_connection_info)

        vim_connection_info = objects.VimConnectionInfo.obj_from_primitive(
            vim_info, context)

        kwargs = {}
        if vim_connection_info.vim_type == 'kubernetes':
            # If the file path of ConfigMap/Secret is changed
            cm_secret_paths = []
            # Get the metadata from vnf_lcm_opoccs
            operation_params = vnf_lcm_opoccs.get('operationParams')
            if operation_params:
                try:
                    cm_secret_paths = (ast.literal_eval(operation_params)
                                       .get('metadata', {})
                                       .get('configmap_secret_paths', []))
                except Exception as e:
                    LOG.error('Invalid format operationParams')
                    raise exceptions.InvalidInput(str(e))
            kwargs = {"old_vnf_package_path": old_vnf_package_path,
                      "configmap_secret_paths": cm_secret_paths}

        self._mgmt_manager.invoke(
            self._load_vnf_interface(
                context, 'modify_information_end', vnf_instance, vnfd_dict),
            'modify_information_end', context=context,
            modify_vnf_request=None,
            vnf_instance=vnf_instance, **kwargs)
        return updated_time

    @log.log
    def instantiate_vnf(self, context, vnf_instance, vnf_dict,
            instantiate_vnf_req):

        vnf_dict['current_error_point'] = EP.VNF_CONFIG_START
        vim_connection_info_list = vnflcm_utils.\
            _get_vim_connection_info_from_vnf_req(vnf_instance,
                    instantiate_vnf_req)

        self._vnf_instance_update(context, vnf_instance,
                vim_connection_info=vim_connection_info_list)

        vim_info = vnflcm_utils._get_vim(context,
                instantiate_vnf_req.vim_connection_info)

        if vim_info['tenant_id'] != vnf_instance.tenant_id:
            LOG.error('The target VNF %(id)s cannot be instantiate '
                      'from a VIM of a different tenant.',
                      {"id": vnf_instance.id})
            raise exceptions.TenantMatchFailure(resource='VNF',
                id=vnf_instance.id,
                action='instantiate')

        vim_connection_info = objects.VimConnectionInfo.obj_from_primitive(
            vim_info, context)

        vnfd_dict = vnflcm_utils._get_vnfd_dict(
            context, vnf_instance.vnfd_id, instantiate_vnf_req.flavour_id)

        if vnf_dict['before_error_point'] <= EP.VNF_CONFIG_START:
            # TODO(LiangLu): grant_request here is planned to pass
            # as a parameter, however due to grant_request is not
            # passed from conductor to vnflcm_driver, thus we put Null
            # value to grant_reqeust temporary.
            # This part will be updated in next release.
            self._mgmt_manager.invoke(
                self._load_vnf_interface(
                    context, 'instantiate_start', vnf_instance, vnfd_dict),
                'instantiate_start', context=context,
                vnf_instance=vnf_instance,
                instantiate_vnf_request=instantiate_vnf_req,
                grant=vnf_dict.get('grant'), grant_request=None)

        vnf_dict['current_error_point'] = EP.PRE_VIM_CONTROL
        if vnf_dict['before_error_point'] <= EP.POST_VIM_CONTROL:
            try:
                self._instantiate_vnf(context, vnf_instance, vnf_dict,
                                      vim_connection_info, instantiate_vnf_req)
            except Exception as exc:
                if (hasattr(vnf_instance.instantiated_vnf_info, 'instance_id')
                        and vnf_instance.instantiated_vnf_info.instance_id):
                    vnf_dict['current_error_point'] = EP.POST_VIM_CONTROL
                raise exc

        vnf_dict['current_error_point'] = EP.INTERNAL_PROCESSING
        vnf_dict['current_error_point'] = EP.VNF_CONFIG_END
        if vnf_dict['before_error_point'] <= EP.VNF_CONFIG_END:
            # TODO(LiangLu): grant_request here is planned to pass
            # as a parameter, however due to grant_request is not
            # passed from conductor to vnflcm_driver, thus we put Null
            # value to grant_reqeust temporary.
            # This part will be updated in next release.
            kwargs = {'vnf': copy.deepcopy(vnf_dict)}
            self._mgmt_manager.invoke(
                self._load_vnf_interface(
                    context, 'instantiate_end', vnf_instance, vnfd_dict),
                'instantiate_end', context=context,
                vnf_instance=vnf_instance,
                instantiate_vnf_request=instantiate_vnf_req,
                grant=vnf_dict.get('grant'), grant_request=None, **kwargs)

    @log.log
    @revert_to_error_task_state
    def terminate_vnf(self, context, vnf_instance, terminate_vnf_req,
            vnf_dict):
        vnf_dict['current_error_point'] = EP.VNF_CONFIG_START

        vim_info = vnflcm_utils._get_vim(context,
            vnf_instance.vim_connection_info)

        vim_connection_info = objects.VimConnectionInfo.obj_from_primitive(
            vim_info, context)

        vnfd_dict = vnflcm_utils._get_vnfd_dict(
            context, vnf_instance.vnfd_id,
            vnf_instance.instantiated_vnf_info.flavour_id)

        if vnf_dict['before_error_point'] <= EP.VNF_CONFIG_START:
            # TODO(LiangLu): grant_request and grant here is planned to
            # pass as a parameter, however due to they are not
            # passed from conductor to vnflcm_driver, thus we put Null
            # value to grant and grant_reqeust temporary.
            # This part will be updated in next release.
            kwargs = {'vnf': copy.deepcopy(vnf_dict)}
            self._mgmt_manager.invoke(
                self._load_vnf_interface(
                    context, 'terminate_start', vnf_instance, vnfd_dict),
                'terminate_start', context=context,
                vnf_instance=vnf_instance,
                terminate_vnf_request=terminate_vnf_req,
                grant=None, grant_request=None, **kwargs)

        vnf_dict['current_error_point'] = EP.PRE_VIM_CONTROL

        LOG.info("Terminating vnf %s", vnf_instance.id)
        try:
            if vnf_dict['before_error_point'] <= EP.POST_VIM_CONTROL:
                self._delete_vnf_instance_resources(context, vnf_instance,
                        vim_connection_info,
                        terminate_vnf_req=terminate_vnf_req)

            vnf_dict['current_error_point'] = EP.INTERNAL_PROCESSING
            vnf_instance.instantiated_vnf_info.reinitialize()
            self._vnf_instance_update(context, vnf_instance,
                vim_connection_info=[], task_state=None)

            LOG.info("Vnf terminated %s successfully", vnf_instance.id)
        except Exception as exp:
            with excutils.save_and_reraise_exception():
                if vnf_dict['current_error_point'] == EP.PRE_VIM_CONTROL:
                    if hasattr(vnf_instance.instantiated_vnf_info,
                            'instance_id'):
                        if vnf_instance.instantiated_vnf_info.instance_id:
                            vnf_dict['current_error_point'] = \
                                EP.POST_VIM_CONTROL

                LOG.error("Unable to terminate vnf '%s' instance. "
                          "Error: %s", vnf_instance.id,
                          encodeutils.exception_to_unicode(exp))

        vnf_dict['current_error_point'] = EP.VNF_CONFIG_END
        if vnf_dict['before_error_point'] <= EP.VNF_CONFIG_END:
            # TODO(LiangLu): grant_request and grant here is planned to
            # pass as a parameter, however due to they are not
            # passed from conductor to vnflcm_driver, thus we put Null
            # value to grant and grant_reqeust temporary.
            # This part will be updated in next release.
            self._mgmt_manager.invoke(
                self._load_vnf_interface(
                    context, 'terminate_end', vnf_instance, vnfd_dict),
                'terminate_end', context=context,
                vnf_instance=vnf_instance,
                terminate_vnf_request=terminate_vnf_req,
                grant=None, grant_request=None)

    def _delete_vnf_instance_resources(self, context, vnf_instance,
            vim_connection_info, terminate_vnf_req=None,
            update_instantiated_state=True):

        if (vnf_instance.instantiated_vnf_info and
            vnf_instance.instantiated_vnf_info.instance_id) or \
                vim_connection_info.vim_type == 'kubernetes':

            instance_id = vnf_instance.instantiated_vnf_info.instance_id \
                if vnf_instance.instantiated_vnf_info else None
            access_info = vim_connection_info.access_info

            LOG.info("Deleting stack %(instance)s for vnf %(id)s ",
                    {"instance": instance_id, "id": vnf_instance.id})

            self._vnf_manager.invoke(vim_connection_info.vim_type,
                'delete', plugin=self, context=context,
                vnf_id=instance_id, auth_attr=access_info,
                vnf_instance=vnf_instance, terminate_vnf_req=terminate_vnf_req)

            if update_instantiated_state:
                vnf_instance.instantiation_state = \
                    fields.VnfInstanceState.NOT_INSTANTIATED
                vnf_instance.save()

            self._vnf_manager.invoke(vim_connection_info.vim_type,
                'delete_wait', plugin=self, context=context,
                vnf_id=instance_id, auth_attr=access_info,
                vnf_instance=vnf_instance)

        vnf_resources = objects.VnfResourceList.get_by_vnf_instance_id(
            context, vnf_instance.id)

        for vnf_resource in vnf_resources:
            self._vnf_manager.invoke(vim_connection_info.vim_type,
                    'delete_vnf_instance_resource',
                    context=context, vnf_instance=vnf_instance,
                    vim_connection_info=vim_connection_info,
                    vnf_resource=vnf_resource)

            vnf_resource.destroy(context)

    def _heal_vnf(self, context, vnf_instance, vim_connection_info,
            heal_vnf_request, vnf):
        inst_vnf_info = vnf_instance.instantiated_vnf_info
        try:
            self._vnf_manager.invoke(
                vim_connection_info.vim_type, 'heal_vnf',
                context=context, vnf_instance=vnf_instance,
                vim_connection_info=vim_connection_info,
                heal_vnf_request=heal_vnf_request)
        except Exception as exp:
            with excutils.save_and_reraise_exception() as exc_ctxt:
                exc_ctxt.reraise = False
                LOG.error("Failed to heal vnf %(id)s in infra driver. "
                          "Error: %(error)s", {"id": vnf_instance.id, "error":
                          encodeutils.exception_to_unicode(exp)})
                raise exceptions.VnfHealFailed(id=vnf_instance.id,
                    error=encodeutils.exception_to_unicode(exp))

        vnf['current_error_point'] = EP.POST_VIM_CONTROL

        try:
            self._vnf_manager.invoke(
                vim_connection_info.vim_type, 'heal_vnf_wait',
                context=context, vnf_instance=vnf_instance,
                vim_connection_info=vim_connection_info,
                heal_vnf_request=heal_vnf_request)
        except Exception as exp:
            LOG.error("Failed to update vnf %(id)s resources for instance "
                      "%(instance)s. Error: %(error)s",
                      {'id': vnf_instance.id, 'instance':
                      inst_vnf_info.instance_id, 'error':
                      encodeutils.exception_to_unicode(exp)})

        try:
            self._vnf_manager.invoke(
                vim_connection_info.vim_type, 'post_heal_vnf',
                context=context, vnf_instance=vnf_instance,
                vim_connection_info=vim_connection_info,
                heal_vnf_request=heal_vnf_request)
            self._vnf_instance_update(context, vnf_instance, task_state=None)
        except Exception as exp:
            with excutils.save_and_reraise_exception() as exc_ctxt:
                exc_ctxt.reraise = False
                LOG.error("Failed to store updated resources information for "
                          "instance %(instance)s for vnf %(id)s. "
                          "Error: %(error)s",
                          {'id': vnf_instance.id, 'instance':
                          inst_vnf_info.instance_id, 'error':
                          encodeutils.exception_to_unicode(exp)})
                raise exceptions.VnfHealFailed(id=vnf_instance.id,
                    error=encodeutils.exception_to_unicode(exp))

    def _respawn_vnf(self, context, vnf_instance, vnf_dict,
                    vim_connection_info, heal_vnf_request):
        if vnf_dict['before_error_point'] != EP.POST_VIM_CONTROL:
            try:
                self._delete_vnf_instance_resources(context, vnf_instance,
                    vim_connection_info, update_instantiated_state=False)
            except Exception as exc:
                with excutils.save_and_reraise_exception() as exc_ctxt:
                    exc_ctxt.reraise = False
                    err_msg = ("Failed to delete vnf resources for "
                              "vnf instance %(id)s before respawning. "
                              "The vnf is in inconsistent state. "
                              "Error: %(error)s")
                    LOG.error(err_msg % {"id": vnf_instance.id,
                              "error": str(exc)})
                    raise exceptions.VnfHealFailed(id=vnf_instance.id,
                        error=encodeutils.exception_to_unicode(exc))

        # InstantiateVnfRequest is not stored in the db as it's mapped
        # to InstantiatedVnfInfo version object. Convert InstantiatedVnfInfo
        # version object to InstantiateVnfRequest so that vnf can be
        # instantiated.

        instantiate_vnf_request = objects.InstantiateVnfRequest.\
            from_vnf_instance(vnf_instance)
        vnf_instance.instantiated_vnf_info.reinitialize()
        vnf_instance.task_state = fields.VnfInstanceTaskState.INSTANTIATING
        vnfd_dict = vnflcm_utils._get_vnfd_dict(
            context, vnf_instance.vnfd_id, instantiate_vnf_request.flavour_id)
        if vnf_dict.get('vnf_instance_after'):
            vnf_instance.instantiated_vnf_info = \
                vnf_dict.get('vnf_instance_after').instantiated_vnf_info
        else:
            vnflcm_utils._build_instantiated_vnf_info(
                vnfd_dict, instantiate_vnf_request, vnf_instance,
                vim_connection_info.vim_id)

        try:
            self._instantiate_vnf(context, vnf_instance, vnf_dict,
                                  vim_connection_info, instantiate_vnf_request)
            self._vnf_manager.invoke(
                vim_connection_info.vim_type, 'post_vnf_instantiation',
                context=context, vnf_instance=vnf_instance,
                vim_connection_info=vim_connection_info,
                instantiate_vnf_req=instantiate_vnf_request)

        except Exception as exc:
            with excutils.save_and_reraise_exception() as exc_ctxt:
                exc_ctxt.reraise = False
                err_msg = ("Failed to instantiate vnf instance "
                          "%(id)s after termination. The vnf is in "
                          "inconsistent state. Error: %(error)s")
                LOG.error(err_msg % {"id": vnf_instance.id,
                          "error": str(exc)})
                raise exceptions.VnfHealFailed(id=vnf_instance.id,
                    error=encodeutils.exception_to_unicode(exc))

        self._vnf_instance_update(context, vnf_instance,
                    instantiation_state=fields.VnfInstanceState.INSTANTIATED,
                    task_state=None)

    @log.log
    @revert_to_error_task_state
    def heal_vnf(self, context, vnf_instance, vnf_dict, heal_vnf_request):
        vnf_dict['current_error_point'] = EP.VNF_CONFIG_START

        LOG.info("Request received for healing vnf '%s'", vnf_instance.id)
        vim_info = vnflcm_utils._get_vim(context,
            vnf_instance.vim_connection_info)

        vim_connection_info = objects.VimConnectionInfo.obj_from_primitive(
            vim_info, context)

        vnfd_dict = vnflcm_utils._get_vnfd_dict(
            context, vnf_instance.vnfd_id,
            vnf_instance.instantiated_vnf_info.flavour_id)

        if vnf_dict['before_error_point'] <= EP.VNF_CONFIG_START:
            # TODO(LiangLu): grant_request here is planned to pass
            # as a parameter, however due to grant_request are not
            # passed from conductor to vnflcm_driver, thus we put Null
            # value to grant and grant_reqeust temporary.
            # This part will be updated in next release.
            self._mgmt_manager.invoke(
                self._load_vnf_interface(
                    context, 'heal_start', vnf_instance, vnfd_dict),
                'heal_start', context=context,
                vnf_instance=vnf_instance,
                heal_vnf_request=heal_vnf_request,
                grant=vnf_dict.get('grant'), grant_request=None)

        vnf_dict['current_error_point'] = EP.PRE_VIM_CONTROL

        try:
            heal_flag = False
            if vnf_dict['before_error_point'] <= EP.POST_VIM_CONTROL:
                if not heal_vnf_request.vnfc_instance_id:
                    self._respawn_vnf(context, vnf_instance, vnf_dict,
                                    vim_connection_info, heal_vnf_request)
                else:
                    heal_flag = True
                    self._heal_vnf(context, vnf_instance, vim_connection_info,
                            heal_vnf_request, vnf_dict)

                LOG.info("Request received for healing vnf '%s' is completed "
                        "successfully", vnf_instance.id)
        except Exception as exp:
            with excutils.save_and_reraise_exception():
                if vnf_dict['current_error_point'] == EP.PRE_VIM_CONTROL:
                    if not heal_flag:
                        if hasattr(vnf_instance.instantiated_vnf_info,
                                'instance_id'):
                            if vnf_instance.instantiated_vnf_info.instance_id:
                                vnf_dict['current_error_point'] = \
                                    EP.POST_VIM_CONTROL

                LOG.error("Unable to heal vnf '%s' instance. "
                          "Error: %s", heal_vnf_request.vnfc_instance_id,
                          encodeutils.exception_to_unicode(exp))

                raise exceptions.VnfHealFailed(id=vnf_instance.id,
                    error=encodeutils.exception_to_unicode(exp))

        vnf_dict['current_error_point'] = EP.VNF_CONFIG_END

        if vnf_dict['before_error_point'] <= EP.VNF_CONFIG_END:
            # TODO(LiangLu): grant_request here is planned to pass
            # as a parameter, however due to grant_request are not
            # passed from conductor to vnflcm_driver, thus we put Null
            # value to grant and grant_reqeust temporary.
            # This part will be updated in next release.
            kwargs = {'vnf': copy.deepcopy(vnf_dict)}
            self._mgmt_manager.invoke(
                self._load_vnf_interface(
                    context, 'heal_end', vnf_instance, vnfd_dict),
                'heal_end', context=context,
                vnf_instance=vnf_instance,
                heal_vnf_request=heal_vnf_request,
                grant=vnf_dict.get('grant'), grant_request=None, **kwargs)

    def _scale_vnf_pre(self, context, vnf_info, vnf_instance,
                      scale_vnf_request, vim_connection_info):
        if vnf_info['before_error_point'] <= EP.NOTIFY_PROCESSING:
            self._vnfm_plugin._update_vnf_scaling(
                context, vnf_info, 'ACTIVE', 'PENDING_'
                + scale_vnf_request.type)
        vnf_info['current_error_point'] = EP.VNF_CONFIG_START

        scale_name_list = []
        grp_id = None
        vnf_info['policy_name'] = scale_vnf_request.aspect_id
        if scale_vnf_request.type == 'SCALE_IN':
            vnfd_dict = vnflcm_utils._get_vnfd_dict(
                context, vnf_instance.vnfd_id,
                vnf_instance.instantiated_vnf_info.flavour_id)

            vnf_info['action'] = 'in'
            scale_id_list, scale_name_list, grp_id, res_num = \
                self._vnf_manager.invoke(
                    vim_connection_info.vim_type,
                    'get_scale_in_ids',
                    plugin=self,
                    context=context,
                    vnf_dict=vnf_info,
                    is_reverse=scale_vnf_request.additional_params.get('\
                        is_reverse'),
                    auth_attr=vim_connection_info.access_info,
                    region_name=vim_connection_info.access_info.get('\
                        region_name'),
                    number_of_steps=scale_vnf_request.number_of_steps
                )
            vnf_info['res_num'] = res_num

            if vnf_info['before_error_point'] <= EP.VNF_CONFIG_START:
                # TODO(LiangLu): grant_request here is planned to pass
                # as a parameter, however due to grant_request are not
                # passed from conductor to vnflcm_driver, thus we put Null
                # value to grant and grant_reqeust temporary.
                # This part will be updated in next release.
                if len(scale_id_list) != 0 or \
                        vim_connection_info.vim_type == 'kubernetes':
                    kwargs = {'scale_name_list': scale_name_list,
                              'scale_stack_id': scale_id_list,
                              'vnf': copy.deepcopy(vnf_info)}
                    self._mgmt_manager.invoke(
                        self._load_vnf_interface(
                            context, 'scale_start', vnf_instance, vnfd_dict),
                        'scale_start', context=context,
                        vnf_instance=vnf_instance,
                        scale_vnf_request=scale_vnf_request,
                        grant=vnf_info.get('grant'), grant_request=None,
                        **kwargs)
        elif scale_vnf_request.type == 'SCALE_OUT':
            vnf_info['action'] = 'out'
            scale_id_list = self._vnf_manager.invoke(
                vim_connection_info.vim_type,
                'get_scale_ids',
                plugin=self,
                context=context,
                vnf_dict=vnf_info,
                auth_attr=vim_connection_info.access_info,
                region_name=vim_connection_info.access_info.get('region_name')
            )
        else:
            msg = 'Unknown vim type: %s' % vim_connection_info.vim_type
            raise exceptions.VnfScaleFailed(id=vnf_info['instance_id'],
                                            error=msg)

        vnf_info['current_error_point'] = EP.PRE_VIM_CONTROL
        return scale_id_list, scale_name_list, grp_id

    def _get_node_template_for_vnf(self, vnfd_dict):
        node_tmp = vnfd_dict['topology_template']['node_templates']
        for node_template in node_tmp.values():
            LOG.debug("node_template %s", node_template)
            if not re.match('^tosca', node_template['type']):
                LOG.debug("VNF node_template %s", node_template)
                return node_template
        return {}

    def _scale_vnf_post(self, context, vnf_info, vnf_instance,
                       scale_vnf_request, vim_connection_info,
                       scale_id_list,
                       resource_changes):
        vnf_info['current_error_point'] = EP.VNF_CONFIG_END
        if scale_vnf_request.type == 'SCALE_OUT':
            vnfd_dict = vnflcm_utils._get_vnfd_dict(
                context, vnf_instance.vnfd_id,
                vnf_instance.instantiated_vnf_info.flavour_id)

            scale_id_after = self._vnf_manager.invoke(
                vim_connection_info.vim_type,
                'get_scale_ids',
                plugin=self,
                context=context,
                vnf_dict=vnf_info,
                auth_attr=vim_connection_info.access_info,
                region_name=vim_connection_info.access_info.get('region_name')
            )
            id_list = list(set(scale_id_after) - set(scale_id_list))
            vnf_info['res_num'] = len(scale_id_after)

            if vnf_info['before_error_point'] <= EP.VNF_CONFIG_END:
                # TODO(LiangLu): grant_request here is planned to pass
                # as a parameter, however due to grant_request are not
                # passed from conductor to vnflcm_driver, thus we put Null
                # value to grant and grant_reqeust temporary.
                # This part will be updated in next release.
                if len(id_list) != 0 or \
                        vim_connection_info.vim_type == 'kubernetes':
                    kwargs = {'scale_stack_id': id_list,
                              'vnf': copy.deepcopy(vnf_info)}
                    self._mgmt_manager.invoke(
                        self._load_vnf_interface(
                            context, 'scale_end', vnf_instance, vnfd_dict),
                        'scale_end', context=context,
                        vnf_instance=vnf_instance,
                        scale_vnf_request=scale_vnf_request,
                        grant=vnf_info.get('grant'), grant_request=None,
                        **kwargs)

        vnf_instance.instantiated_vnf_info.scale_level =\
            vnf_info['after_scale_level']
        if vim_connection_info.vim_type != 'kubernetes':
            # NOTE(ueha): The logic of Scale for OpenStack VIM is widely hard
            # coded with `vnf_info`. This dependency is to be refactored in
            # future.
            scaleGroupDict = \
                jsonutils.loads(vnf_info['attributes']['scale_group'])
            (scaleGroupDict
            ['scaleGroupDict'][scale_vnf_request.aspect_id]['default']) =\
                vnf_info['res_num']
            vnf_info['attributes']['scale_group'] =\
                jsonutils.dump_as_bytes(scaleGroupDict)

        if vnf_info['before_error_point'] < EP.NOTIFY_COMPLETED:
            self._vnfm_plugin._update_vnf_scaling(context, vnf_info,
                    'PENDING_' + scale_vnf_request.type, 'ACTIVE')
            vnf_lcm_op_occ = vnf_info['vnf_lcm_op_occ']
            vnf_lcm_op_occ.operation_state = 'COMPLETED'
            vnf_lcm_op_occ.resource_changes = resource_changes
            vnf_lcm_op_occ.state_entered_time = timeutils.utcnow()
            vnf_lcm_op_occ.save()
            vnf_instance.task_state = None
            vnf_instance.save()

        vnf_info['current_error_point'] = EP.NOTIFY_COMPLETED

        notification = vnf_info['notification']
        notification['notificationStatus'] = 'RESULT'
        notification['operationState'] = 'COMPLETED'
        resource_dict = resource_changes.to_dict()
        if resource_dict.get('affected_vnfcs'):
            notification['affectedVnfcs'] = resource_dict.get('affected_vnfcs')
        if resource_dict.get('affected_virtual_links'):
            notification['affectedVirtualLinks'] =\
                resource_dict.get('affected_virtual_links')
        if resource_dict.get('affected_virtual_storages'):
            notification['affectedVirtualStorages'] =\
                resource_dict.get('affected_virtual_storages')
        self.rpc_api.send_notification(context, notification)

    def _scale_resource_update(self, context, vnf_info, vnf_instance,
                               scale_vnf_request,
                               vim_connection_info,
                               error=False):
        vnf_lcm_op_occs = vnf_info['vnf_lcm_op_occ']
        instantiated_vnf_before = \
            copy.deepcopy(vnf_instance.instantiated_vnf_info)

        self._vnf_manager.invoke(
            vim_connection_info.vim_type,
            'scale_resource_update',
            context=context,
            vnf_instance=vnf_instance,
            vnf_info=vnf_info,
            scale_vnf_request=scale_vnf_request,
            vim_connection_info=vim_connection_info
        )
        for scale in vnf_instance.instantiated_vnf_info.scale_status:
            if scale_vnf_request.aspect_id == scale.aspect_id:
                if not error:
                    scale.scale_level = vnf_info['after_scale_level']
                    break
                else:
                    scale.scale_level = vnf_info['scale_level']
                    break
        LOG.debug("vnf_instance.instantiated_vnf_info %s",
        vnf_instance.instantiated_vnf_info)
        affected_vnfcs = []
        affected_virtual_storages = []
        affected_virtual_links = []
        if scale_vnf_request.type == 'SCALE_IN':
            for vnfc in instantiated_vnf_before.vnfc_resource_info:
                vnfc_delete = True
                for rsc in vnf_instance.instantiated_vnf_info.\
                        vnfc_resource_info:
                    if vnfc.compute_resource.resource_id == \
                            rsc.compute_resource.resource_id:
                        vnfc_delete = False
                        break
                if vnfc_delete:
                    affected_vnfc = objects.AffectedVnfc(id=vnfc.id,
                                       vdu_id=vnfc.vdu_id,
                                       change_type='REMOVED',
                                       compute_resource=vnfc.compute_resource)
                    affected_vnfcs.append(affected_vnfc)

            for st in instantiated_vnf_before.virtual_storage_resource_info:
                st_delete = True
                for rsc in vnf_instance.instantiated_vnf_info.\
                        virtual_storage_resource_info:
                    if st.storage_resource.resource_id == \
                            rsc.storage_resource.resource_id:
                        st_delete = False
                        break
                if st_delete:
                    affected_st = objects.AffectedVirtualStorage(
                        id=st.id,
                        virtual_storage_desc_id=st.virtual_storage_desc_id,
                        change_type='REMOVED',
                        storage_resource=st.storage_resource)
                    affected_virtual_storages.append(affected_st)

            for vl in instantiated_vnf_before.vnf_virtual_link_resource_info:
                port_delete = False
                for rsc in vnf_instance.\
                        instantiated_vnf_info.vnf_virtual_link_resource_info:
                    if vl.network_resource.resource_id == \
                            rsc.network_resource.resource_id:
                        if len(vl.vnf_link_ports) != len(rsc.vnf_link_ports):
                            port_delete = True
                            break
                if port_delete:
                    affected_vl = objects.AffectedVirtualLink(
                        id=vl.id,
                        vnf_virtual_link_desc_id=vl.vnf_virtual_link_desc_id,
                        change_type='LINK_PORT_REMOVED',
                        network_resource=vl.network_resource)
                    affected_virtual_links.append(affected_vl)
        else:
            for rsc in vnf_instance.instantiated_vnf_info.vnfc_resource_info:
                vnfc_add = True
                for vnfc in instantiated_vnf_before.vnfc_resource_info:
                    if vnfc.compute_resource.resource_id == \
                            rsc.compute_resource.resource_id:
                        vnfc_add = False
                        break
                if vnfc_add:
                    affected_vnfc = objects.AffectedVnfc(
                        id=rsc.id,
                        vdu_id=rsc.vdu_id,
                        change_type='ADDED',
                        compute_resource=rsc.compute_resource)
                    affected_vnfcs.append(affected_vnfc)
            for rsc in vnf_instance.instantiated_vnf_info.\
                    virtual_storage_resource_info:
                st_add = True
                for st in instantiated_vnf_before.\
                        virtual_storage_resource_info:
                    if st.storage_resource.resource_id == \
                            rsc.storage_resource.resource_id:
                        st_add = False
                        break
                if st_add:
                    affected_st = objects.AffectedVirtualStorage(
                        id=rsc.id,
                        virtual_storage_desc_id=rsc.virtual_storage_desc_id,
                        change_type='ADDED',
                        storage_resource=rsc.storage_resource)
                    affected_virtual_storages.append(affected_st)
            for vl in instantiated_vnf_before.vnf_virtual_link_resource_info:
                port_add = False
                for rsc in vnf_instance.instantiated_vnf_info.\
                        vnf_virtual_link_resource_info:
                    if vl.network_resource.resource_id == \
                            rsc.network_resource.resource_id:
                        if len(vl.vnf_link_ports) != len(rsc.vnf_link_ports):
                            port_add = True
                            break
                if port_add:
                    affected_vl = objects.AffectedVirtualLink(
                        id=vl.id,
                        vnf_virtual_link_desc_id=vl.vnf_virtual_link_desc_id,
                        change_type='LINK_PORT_ADDED',
                        network_resource=vl.network_resource)
                    affected_virtual_links.append(affected_vl)
        resource_changes = objects.ResourceChanges()
        resource_changes.affected_vnfcs = []
        resource_changes.affected_virtual_links = []
        resource_changes.affected_virtual_storages = []
        if 'resource_changes' in \
                vnf_lcm_op_occs and vnf_lcm_op_occs.resource_changes:
            res_chg = vnf_lcm_op_occs.resource_changes
            if 'affected_vnfcs' in res_chg:
                if res_chg.affected_vnfcs and \
                   len(res_chg.affected_vnfcs) > 0:
                    resource_changes.affected_vnfcs.\
                        extend(res_chg.affected_vnfcs)
            if 'affected_virtual_storages' in res_chg:
                if res_chg.affected_virtual_storages and \
                   len(res_chg.affected_virtual_storages) > 0:
                    resource_changes.affected_virtual_storages.extend(
                        res_chg.affected_virtual_storages)
            if 'affected_virtual_links' in res_chg:
                if res_chg.affected_virtual_links and \
                   len(res_chg.affected_virtual_links) > 0:
                    resource_changes.affected_virtual_links.\
                        extend(res_chg.affected_virtual_links)
        resource_changes.affected_vnfcs.extend(affected_vnfcs)
        resource_changes.affected_virtual_storages.extend(
            affected_virtual_storages)
        resource_changes.affected_virtual_links = []
        resource_changes.affected_virtual_links.extend(affected_virtual_links)

        vnf_info['resource_changes'] = resource_changes
        return resource_changes

    @log.log
    @revert_to_error_scale
    def scale_vnf(self, context, vnf_info, vnf_instance, scale_vnf_request):
        LOG.info("Request received for scale vnf '%s'", vnf_instance.id)

        timestamp = datetime.utcnow()
        vnf_lcm_op_occ = vnf_info['vnf_lcm_op_occ']

        vnf_lcm_op_occ.operation_state = 'PROCESSING'
        vnf_lcm_op_occ.state_entered_time = timestamp
        LOG.debug("vnf_lcm_op_occ %s", vnf_lcm_op_occ)
        vnf_lcm_op_occ.save()

        notification = vnf_info['notification']
        notification['operationState'] = 'PROCESSING'
        self.rpc_api.send_notification(context, notification)

        vnf_info['current_error_point'] = EP.NOTIFY_PROCESSING
        vim_info = vnflcm_utils._get_vim(context,
            vnf_instance.vim_connection_info)

        vim_connection_info = objects.VimConnectionInfo.obj_from_primitive(
            vim_info, context)

        scale_id_list, scale_name_list, grp_id = self._scale_vnf_pre(
            context, vnf_info,
            vnf_instance,
            scale_vnf_request,
            vim_connection_info)

        if vnf_info['before_error_point'] <= EP.POST_VIM_CONTROL:
            self._scale_vnf(context, vnf_info, vnf_instance, scale_vnf_request,
                           vim_connection_info, scale_name_list, grp_id,
                           vnf_lcm_op_occ)

            resource_changes = self._scale_resource_update(context, vnf_info,
                                    vnf_instance,
                                    scale_vnf_request,
                                    vim_connection_info)
        else:
            resource_changes = vnf_info.get('resource_changes')
            if not resource_changes:
                resource_changes = self._scale_resource_update(
                    context, vnf_info, vnf_instance, scale_vnf_request,
                    vim_connection_info, error=True)

        vnf_info['current_error_point'] = EP.INTERNAL_PROCESSING

        self._scale_vnf_post(context, vnf_info,
                             vnf_instance,
                             scale_vnf_request,
                             vim_connection_info,
                             scale_id_list,
                             resource_changes)

        LOG.info("Request received for scale vnf '%s' is completed "
                 "successfully", vnf_instance.id)

    def _scale_vnf(self, context, vnf_info, vnf_instance, scale_vnf_request,
            vim_connection_info, scale_name_list, grp_id,
            vnf_lcm_op_occ):
        # action_driver
        LOG.debug("vnf_info['vnfd']['attributes'] %s", (vnf_info
                                                        .get('vnfd', {})
                                                        .get('attributes')))
        self._vnf_manager = driver_manager.DriverManager(
            'tacker.tacker.vnfm.drivers',
            cfg.CONF.tacker.infra_driver)

        if scale_vnf_request.type == 'SCALE_IN':
            action = 'in'
        elif scale_vnf_request.type == 'SCALE_OUT':
            action = 'out'
        else:
            msg = 'Unknown scale type: %s' % scale_vnf_request.type
            raise exceptions.VnfScaleFailed(id=vnf_instance.id, error=msg)

        stack_id = vnf_instance.instantiated_vnf_info.instance_id
        # TODO(h-asahina): change the key name `instance_id` attr to `stack_id`
        policy = {'instance_id': stack_id,
                  'name': scale_vnf_request.aspect_id,
                  'vnf': vnf_info,
                  'action': action}

        LOG.debug(
            "is_reverse: %s",
            scale_vnf_request.additional_params.get('is_reverse'))
        default = None
        if vim_connection_info.vim_type == 'kubernetes':
            policy['vnf_instance_id'] = vnf_lcm_op_occ.get('vnf_instance_id')
            vnf_instance = objects.VnfInstance.get_by_id(context,
                policy['vnf_instance_id'])
            vnfd_dict = vnflcm_utils._get_vnfd_dict(context,
                vnf_instance.vnfd_id,
                vnf_instance.instantiated_vnf_info.flavour_id)
            tosca = tosca_template.ToscaTemplate(
                parsed_params={}, a_file=False, yaml_dict_tpl=vnfd_dict)
            extract_policy_infos = vnflcm_utils.get_extract_policy_infos(tosca)
            policy['vdu_defs'] = vnflcm_utils.get_target_vdu_def_dict(
                extract_policy_infos=extract_policy_infos,
                aspect_id=scale_vnf_request.aspect_id,
                tosca=tosca)
            policy['delta_num'] = vnflcm_utils.get_scale_delta_num(
                extract_policy_infos=extract_policy_infos,
                aspect_id=scale_vnf_request.aspect_id)
        elif vim_connection_info.vim_type == 'openstack':
            # NOTE(ueha): The logic of Scale for OpenStack VIM is widely hard
            # coded with `vnf_info`. This dependency is to be refactored in
            # future.
            scale_json = vnf_info['attributes']['scale_group']
            scale_group_dict = jsonutils.loads(scale_json)
            key_aspect = scale_vnf_request.aspect_id
            default = scale_group_dict['scaleGroupDict'][key_aspect]['default']
        else:
            msg = 'Unknown vim type: %s' % vim_connection_info.vim_type
            raise exceptions.VnfScaleFailed(id=vnf_instance.id, error=msg)

        if (scale_vnf_request.type == 'SCALE_IN' and
                scale_vnf_request.additional_params['is_reverse'] == 'True'):
            self._vnf_manager.invoke(
                vim_connection_info.vim_type,
                'scale_in_reverse',
                plugin=self,
                context=context,
                auth_attr=vim_connection_info.access_info,
                vnf_info=vnf_info,
                scale_vnf_request=scale_vnf_request,
                region_name=vim_connection_info.access_info.get('region_name'),
                scale_name_list=scale_name_list,
                grp_id=grp_id,
                vnf_instance=vnf_instance
            )
            vnf_info['current_error_point'] = EP.POST_VIM_CONTROL
            self._vnf_manager.invoke(
                vim_connection_info.vim_type,
                'scale_update_wait',
                plugin=self,
                context=context,
                auth_attr=vim_connection_info.access_info,
                vnf_info=vnf_info,
                region_name=vim_connection_info.access_info.get('region_name')
            )
        elif scale_vnf_request.type == 'SCALE_OUT' and default == 0:
            self._vnf_manager.invoke(
                vim_connection_info.vim_type,
                'scale_out_initial',
                plugin=self,
                context=context,
                auth_attr=vim_connection_info.access_info,
                vnf_info=vnf_info,
                scale_vnf_request=scale_vnf_request,
                region_name=vim_connection_info.access_info.get('region_name'),
                vnf_instance=vnf_instance
            )
            vnf_info['current_error_point'] = EP.POST_VIM_CONTROL
            self._vnf_manager.invoke(
                vim_connection_info.vim_type,
                'scale_update_wait',
                plugin=self,
                context=context,
                auth_attr=vim_connection_info.access_info,
                vnf_info=vnf_info,
                region_name=vim_connection_info.access_info.get('region_name')
            )
        else:
            for _ in range(scale_vnf_request.number_of_steps):
                last_event_id = self._vnf_manager.invoke(
                    vim_connection_info.vim_type,
                    'scale',
                    plugin=self,
                    context=context,
                    auth_attr=vim_connection_info.access_info,
                    policy=policy,
                    region_name=vim_connection_info.access_info.get('\
                        region_name')
                )
                vnf_info['current_error_point'] = EP.POST_VIM_CONTROL
                self._vnf_manager.invoke(
                    vim_connection_info.vim_type,
                    'scale_wait',
                    plugin=self,
                    context=context,
                    auth_attr=vim_connection_info.access_info,
                    policy=policy,
                    region_name=vim_connection_info.access_info.get('\
                        region_name'),
                    last_event_id=last_event_id)

    def _term_resource_update(self, context, vnf_info, vnf_instance,
                              error=False):
        if not vnf_instance.instantiated_vnf_info:
            resource_changes = objects.ResourceChanges()
            resource_changes.affected_vnfcs = []
            resource_changes.affected_virtual_links = []
            resource_changes.affected_virtual_storages = []
            vnf_info['resource_changes'] = resource_changes
            return resource_changes
        instantiated_vnf_before = copy.deepcopy(
            vnf_instance.instantiated_vnf_info)
        vnf_instance.instantiated_vnf_info.reinitialize()
        if not error:
            vnf_instance.vim_connection_info = []
            vnf_instance.task_state = None
        LOG.debug(
            "vnf_instance.instantiated_vnf_info %s",
            vnf_instance.instantiated_vnf_info)
        affected_vnfcs = []
        affected_virtual_storages = []
        affected_virtual_links = []
        for vnfc in instantiated_vnf_before.vnfc_resource_info:
            vnfc_delete = True
            for rsc in vnf_instance.instantiated_vnf_info.vnfc_resource_info:
                if vnfc.compute_resource.resource_id == \
                        rsc.compute_resource.resource_id:
                    vnfc_delete = False
                    break
            if vnfc_delete:
                affected_vnfc = objects.AffectedVnfc(
                    id=vnfc.id,
                    vdu_id=vnfc.vdu_id,
                    change_type='REMOVED',
                    compute_resource=vnfc.compute_resource)
                affected_vnfcs.append(affected_vnfc)

        for st in instantiated_vnf_before.virtual_storage_resource_info:
            st_delete = True
            for rsc in \
                    vnf_instance.instantiated_vnf_info.\
                    virtual_storage_resource_info:
                if st.storage_resource.resource_id == \
                        rsc.storage_resource.resource_id:
                    st_delete = False
                    break
            if st_delete:
                affected_st = objects.AffectedVirtualStorage(
                    id=st.id,
                    virtual_storage_desc_id=st.virtual_storage_desc_id,
                    change_type='REMOVED',
                    storage_resource=st.storage_resource)
                affected_virtual_storages.append(affected_st)

        for vl in instantiated_vnf_before.vnf_virtual_link_resource_info:
            vm_delete = False
            for rsc in \
                    vnf_instance.instantiated_vnf_info.\
                    vnf_virtual_link_resource_info:
                if st.network_resource.resource_id == \
                        rsc.network_resource.resource_id:
                    vm_delete = False
                    break
            if vm_delete:
                affected_vl = objects.AffectedVirtualLink(
                    id=vl.id,
                    vnf_virtual_link_desc_id=vl.vnf_virtual_link_desc_id,
                    change_type='REMOVED',
                    network_resource=vl.network_resource)
                affected_virtual_links.append(affected_vl)
        vnf_lcm_op_occs = vnf_info['vnf_lcm_op_occ']
        resource_changes = objects.ResourceChanges()
        resource_changes.affected_vnfcs = []
        resource_changes.affected_virtual_links = []
        resource_changes.affected_virtual_storages = []
        if 'resource_changes' in vnf_lcm_op_occs and \
                vnf_lcm_op_occs.resource_changes:
            res_chg = vnf_lcm_op_occs.resource_changes
            if 'affected_vnfcs' in res_chg:
                if res_chg.affected_vnfcs and \
                        len(res_chg.affected_vnfcs) > 0:
                    resource_changes.affected_vnfcs.extend(
                        res_chg.affected_vnfcs)
            if 'affected_virtual_storages' in res_chg:
                if res_chg.affected_virtual_storages and \
                        len(res_chg.affected_virtual_storages) > 0:
                    resource_changes.affected_virtual_storages.extend(
                        res_chg.affected_virtual_storages)
            if 'affected_virtual_links' in res_chg:
                if res_chg.affected_virtual_links and \
                        len(res_chg.affected_virtual_links) > 0:
                    resource_changes.affected_virtual_links.extend(
                        res_chg.affected_virtual_links)
        resource_changes.affected_vnfcs.extend(affected_vnfcs)
        resource_changes.affected_virtual_storages.extend(
            affected_virtual_storages)
        resource_changes.affected_virtual_links.extend(affected_virtual_links)

        vnf_info['resource_changes'] = resource_changes
        return resource_changes

    def _rollback_vnf_pre(
            self,
            context,
            vnf_info,
            vnf_instance,
            operation_params,
            vim_connection_info):
        vnf_lcm_op_occs = vnf_info['vnf_lcm_op_occ']
        scale_id_list = []
        scale_name_list = []
        grp_id = None
        self._update_vnf_rollback_pre(context, vnf_info)
        if vnf_lcm_op_occs.operation == 'SCALE':
            if vim_connection_info.vim_type != 'kubernetes':
                # NOTE(ueha): The logic of Scale for OpenStack VIM is widely
                # hard coded with `vnf_info`. This dependency is to be
                # refactored in future.
                scaleGroupDict = jsonutils.loads(
                    vnf_info['attributes']['scale_group'])
                cap_size = scaleGroupDict['scaleGroupDict'][operation_params
                    ['aspect_id']]['default']
                vnf_info['res_num'] = cap_size
            scale_vnf_request = objects.ScaleVnfRequest.obj_from_primitive(
                operation_params, context=context)
            for scale in vnf_instance.instantiated_vnf_info.scale_status:
                if scale_vnf_request.aspect_id == scale.aspect_id:
                    vnf_info['after_scale_level'] = scale.scale_level
                    break
        if vnf_lcm_op_occs.operation == 'SCALE' \
           and vnf_lcm_op_occs.error_point >= EP.POST_VIM_CONTROL:
            scale_id_list, scale_name_list, grp_id = self._vnf_manager.invoke(
                vim_connection_info.vim_type,
                'get_rollback_ids',
                plugin=self,
                context=context,
                vnf_dict=vnf_info,
                aspect_id=operation_params['aspect_id'],
                auth_attr=vim_connection_info.access_info,
                region_name=vim_connection_info.access_info.get('region_name')
            )
        if vnf_lcm_op_occs.error_point == EP.NOTIFY_COMPLETED:
            if vnf_lcm_op_occs.operation == 'SCALE':
                vnfd_dict = vnflcm_utils._get_vnfd_dict(
                    context, vnf_instance.vnfd_id,
                    vnf_instance.instantiated_vnf_info.flavour_id)
                vnf_info['action'] = 'in'
                if len(scale_id_list) != 0:
                    kwargs = {'scale_name_list': scale_name_list}
                    # TODO(LiangLu): grant_request here is planned to pass
                    # as a parameter, however due to grant_request are not
                    # passed from conductor to vnflcm_driver, thus we put Null
                    # value to grant and grant_reqeust temporary.
                    # This part will be updated in next release.
                    self._mgmt_manager.invoke(
                        self._load_vnf_interface(context, 'scale_start',
                                                 vnf_instance, vnfd_dict),
                        'scale_start', context=context,
                        vnf_instance=vnf_instance,
                        scale_vnf_request=scale_vnf_request,
                        grant=vnf_info.get('grant'), grant_request=None,
                        **kwargs)

            else:
                vnfd_dict = vnflcm_utils._get_vnfd_dict(
                    context, vnf_instance.vnfd_id,
                    vnf_instance.instantiated_vnf_info.flavour_id)
                # TODO(LiangLu): grant_request and grant here is planned to
                # pass as a parameter, however due to they are not
                # passed from conductor to vnflcm_driver, thus we put Null
                # value to grant and grant_reqeust temporary.
                # This part will be updated in next release.
                if len(scale_id_list) != 0:
                    self._mgmt_manager.invoke(
                        self._load_vnf_interface(
                            context, 'terminate_start',
                            vnf_instance, vnfd_dict),
                        'terminate_start', context=context,
                        vnf_instance=vnf_instance,
                        terminate_vnf_request=None,
                        grant=None, grant_request=None)
            vnf_lcm_op_occs.error_point = EP.VNF_CONFIG_END

        return scale_name_list, grp_id

    def _rollback_vnf(
            self,
            context,
            vnf_info,
            vnf_instance,
            operation_params,
            vim_connection_info,
            scale_name_list,
            grp_id):
        vnf_lcm_op_occs = vnf_info['vnf_lcm_op_occ']
        if vnf_lcm_op_occs.error_point >= EP.POST_VIM_CONTROL:
            if vnf_lcm_op_occs.operation == 'SCALE':
                scale_vnf_request = objects.ScaleVnfRequest.obj_from_primitive(
                    operation_params, context=context)
                self._vnf_manager.invoke(
                    vim_connection_info.vim_type,
                    'scale_in_reverse',
                    plugin=self,
                    context=context,
                    auth_attr=vim_connection_info.access_info,
                    vnf_info=vnf_info,
                    scale_vnf_request=scale_vnf_request,
                    region_name=vim_connection_info.access_info.get(
                        'region_name'),
                    scale_name_list=scale_name_list,
                    grp_id=grp_id,
                    vnf_instance=vnf_instance)
                self._vnf_manager.invoke(
                    vim_connection_info.vim_type,
                    'scale_update_wait',
                    plugin=self,
                    context=context,
                    auth_attr=vim_connection_info.access_info,
                    vnf_info=vnf_info,
                    region_name=vim_connection_info.access_info.get(
                        'region_name'))

            else:
                instance_id = vnf_instance.instantiated_vnf_info.instance_id
                access_info = vim_connection_info.access_info
                self._vnf_manager.invoke(vim_connection_info.vim_type,
                    'delete', plugin=self, context=context,
                    vnf_id=instance_id, auth_attr=access_info,
                    vnf_instance=vnf_instance)

                self._vnf_manager.invoke(vim_connection_info.vim_type,
                    'delete_wait', plugin=self, context=context,
                    vnf_id=instance_id, auth_attr=access_info,
                    vnf_instance=vnf_instance)

        vnf_lcm_op_occs.error_point = EP.PRE_VIM_CONTROL

    def _update_vnf_rollback_pre(self, context, vnf_info):
        self._vnfm_plugin._update_vnf_rollback_pre(context, vnf_info)

    def _update_vnf_rollback(self, context, vnf_info,
                             vnf_instance, vnf_lcm_op_occs):
        if vnf_lcm_op_occs.operation == 'SCALE':
            status = 'ACTIVE'
        else:
            status = 'INACTIVE'
        vnf_instance.task_state = None
        self._vnfm_plugin._update_vnf_rollback(context, vnf_info, 'ERROR',
                                               status)
        vnf_lcm_op_occs.state_entered_time = timeutils.utcnow()
        vnf_lcm_op_occs.save()
        vnf_instance.save()

    def _update_vnf_rollback_status_err(self, context, vnf_info):
        self._vnfm_plugin.update_vnf_rollback_status_err(context, vnf_info)

    def _rollback_vnf_post(
            self,
            context,
            vnf_info,
            vnf_instance,
            operation_params,
            vim_connection_info):
        vnf_lcm_op_occs = vnf_info['vnf_lcm_op_occ']
        if vnf_lcm_op_occs.operation == 'SCALE':
            scale_vnf_request = objects.ScaleVnfRequest.obj_from_primitive(
                operation_params, context=context)
            scale_vnf_request_copy = copy.deepcopy(scale_vnf_request)
            scale_vnf_request_copy.type = 'SCALE_IN'
            resource_changes = self._scale_resource_update(context, vnf_info,
                                    vnf_instance,
                                    scale_vnf_request_copy,
                                    vim_connection_info)

        else:
            vnfd_dict = vnflcm_utils.get_vnfd_dict(
                context, vnf_instance.vnfd_id,
                vnf_instance.instantiated_vnf_info.flavour_id)
            # TODO(LiangLu): grant_request and grant here is planned to
            # pass as a parameter, however due to they are not
            # passed from conductor to vnflcm_driver, thus we put Null
            # value to grant and grant_reqeust temporary.
            # This part will be updated in next release.
            self._mgmt_manager.invoke(
                self._load_vnf_interface(
                    context, 'terminate_end',
                    vnf_instance, vnfd_dict),
                'terminate_end', context=context,
                vnf_instance=vnf_instance,
                terminate_vnf_request=None,
                grant=None, grant_request=None)
            resource_changes = self._term_resource_update(
                context, vnf_info, vnf_instance)

        vnf_lcm_op_occs.error_point = EP.VNF_CONFIG_START

        timestamp = datetime.utcnow()
        vnf_lcm_op_occs.operation_state = 'ROLLED_BACK'
        vnf_lcm_op_occs.state_entered_time = timestamp
        vnf_lcm_op_occs.resource_changes = resource_changes
        self._update_vnf_rollback(context, vnf_info,
                                 vnf_instance,
                                 vnf_lcm_op_occs)
        notification = vnf_info['notification']
        notification['notificationStatus'] = 'RESULT'
        notification['operationState'] = 'ROLLED_BACK'
        resource_dict = resource_changes.to_dict()
        if resource_dict.get('affected_vnfcs'):
            notification['affectedVnfcs'] = resource_dict.get('affected_vnfcs')
        if resource_dict.get('affected_virtual_links'):
            notification['affectedVirtualLinks'] = \
                resource_dict.get('affected_virtual_links')
        if resource_dict.get('affected_virtual_storages'):
            notification['affectedVirtualStorages'] = \
                resource_dict.get('affected_virtual_storages')
        self.rpc_api.send_notification(context, notification)

    @log.log
    @revert_to_error_rollback
    def rollback_vnf(self, context, vnf_info, vnf_instance, operation_params):
        LOG.info("Request received for rollback vnf '%s'", vnf_instance.id)
        vnf_lcm_op_occs = vnf_info['vnf_lcm_op_occ']
        if vnf_lcm_op_occs.operation == 'SCALE':
            scale_vnf_request = objects.ScaleVnfRequest.obj_from_primitive(
                operation_params, context=context)
            for scale in vnf_instance.instantiated_vnf_info.scale_status:
                if scale_vnf_request.aspect_id == scale.aspect_id:
                    vnf_info['after_scale_level'] = scale.scale_level
                    break

        timestamp = datetime.utcnow()

        vnf_lcm_op_occs.operation_state = 'ROLLING_BACK'
        vnf_lcm_op_occs.state_entered_time = timestamp
        LOG.debug("vnf_lcm_op_occs %s", vnf_lcm_op_occs)

        insta_url = CONF.vnf_lcm.endpoint_url + \
            "/vnflcm/v1/vnf_instances/" + \
            vnf_instance.id
        vnflcm_url = CONF.vnf_lcm.endpoint_url + \
            "/vnflcm/v1/vnf_lcm_op_occs/" + \
            vnf_lcm_op_occs.id
        notification = {}
        notification['notificationType'] = \
            'VnfLcmOperationOccurrenceNotification'
        notification['vnfInstanceId'] = vnf_instance.id
        notification['notificationStatus'] = 'START'
        notification['operation'] = vnf_lcm_op_occs.operation
        notification['operationState'] = 'ROLLING_BACK'
        if vnf_lcm_op_occs.operation == 'SCALE':
            notification['isAutomaticInvocation'] = \
                vnf_lcm_op_occs.is_automatic_invocation
        else:
            notification['isAutomaticInvocation'] = False
        notification['vnfLcmOpOccId'] = vnf_lcm_op_occs.id
        notification['_links'] = {}
        notification['_links']['vnfInstance'] = {}
        notification['_links']['vnfInstance']['href'] = insta_url
        notification['_links']['vnfLcmOpOcc'] = {}
        notification['_links']['vnfLcmOpOcc']['href'] = vnflcm_url
        vnf_info['notification'] = notification
        vnf_lcm_op_occs.save()
        self.rpc_api.send_notification(context, notification)

        vim_info = vnflcm_utils._get_vim(context,
            vnf_instance.vim_connection_info)

        vim_connection_info = objects.VimConnectionInfo.obj_from_primitive(
            vim_info, context)

        scale_name_list, grp_id = self._rollback_vnf_pre(
            context, vnf_info, vnf_instance,
            operation_params, vim_connection_info)

        self._rollback_vnf(
            context,
            vnf_info,
            vnf_instance,
            operation_params,
            vim_connection_info,
            scale_name_list,
            grp_id)

        self._rollback_vnf_post(
            context,
            vnf_info,
            vnf_instance,
            operation_params,
            vim_connection_info)

    def _change_ext_conn_vnf(self, context, vnf_instance, vnf_dict,
            vim_connection_info, change_ext_conn_req):
        inst_vnf_info = vnf_instance.instantiated_vnf_info
        try:
            self._vnf_manager.invoke(
                vim_connection_info.vim_type, 'change_ext_conn_vnf',
                context=context, vnf_instance=vnf_instance, vnf_dict=vnf_dict,
                vim_connection_info=vim_connection_info,
                change_ext_conn_req=change_ext_conn_req)
        except Exception as exp:
            with excutils.save_and_reraise_exception() as exc_ctxt:
                exc_ctxt.reraise = False
                LOG.error("Failed to change external connectivity "
                          "vnf %(id)s in infra driver. "
                          "Error: %(error)s", {"id": vnf_instance.id, "error":
                          encodeutils.exception_to_unicode(exp)})
                raise exceptions.VnfChangeExtConnFailed(id=vnf_instance.id,
                    error=encodeutils.exception_to_unicode(exp))
        vnf_dict['current_error_point'] = fields.ErrorPoint.POST_VIM_CONTROL
        try:
            self._vnf_manager.invoke(
                vim_connection_info.vim_type, 'change_ext_conn_vnf_wait',
                context=context, vnf_instance=vnf_instance,
                vim_connection_info=vim_connection_info)
        except Exception as exp:
            LOG.error("Failed to update vnf %(id)s resources for instance "
                      "%(instance)s. Error: %(error)s",
                      {'id': vnf_instance.id, 'instance':
                      inst_vnf_info.instance_id, 'error':
                      encodeutils.exception_to_unicode(exp)})
            raise exceptions.VnfChangeExtConnWaitFailed(
                id=vnf_instance.id,
                error=encodeutils.exception_to_unicode(exp))

    @log.log
    @revert_to_error_task_state
    def change_ext_conn_vnf(
            self,
            context,
            vnf_instance,
            vnf_dict,
            change_ext_conn_req):
        LOG.info("Request received for changing external connectivity "
                 "vnf '%s'", vnf_instance.id)

        vnfd_dict = vnflcm_utils._get_vnfd_dict(
            context, vnf_instance.vnfd_id,
            vnf_instance.instantiated_vnf_info.flavour_id)

        vnf_dict['current_error_point'] = EP.VNF_CONFIG_START
        if vnf_dict['before_error_point'] <= EP.VNF_CONFIG_START:
            # TODO(esto-aln): grant_request here is planned to pass
            # as a parameter, however due to grant_request are not
            # passed from conductor to vnflcm_driver, thus we put Null
            # value to grant and grant_reqeust temporary.
            # This part will be updated in next release.
            self._mgmt_manager.invoke(
                self._load_vnf_interface(
                    context, 'change_external_connectivity_start',
                    vnf_instance, vnfd_dict),
                'change_external_connectivity_start', context=context,
                vnf_instance=vnf_instance,
                change_ext_conn_request=change_ext_conn_req,
                grant=vnf_dict.get('grant'), grant_request=None)

        vnf_dict['current_error_point'] = EP.PRE_VIM_CONTROL
        if vnf_dict['before_error_point'] <= EP.POST_VIM_CONTROL:
            vim_info = vnflcm_utils._get_vim(context,
                vnf_instance.vim_connection_info)

            vim_connection_info = \
                objects.VimConnectionInfo.obj_from_primitive(
                    vim_info, context)

            self._change_ext_conn_vnf(context, vnf_instance, vnf_dict,
                vim_connection_info, change_ext_conn_req)

        # Since there is no processing corresponding to
        # EP.INTERNAL_PROCESSING, it transitions to EP.VNF_CONFIG_END.
        vnf_dict['current_error_point'] = EP.VNF_CONFIG_END
        if vnf_dict['before_error_point'] <= EP.VNF_CONFIG_END:
            # TODO(esto-aln): grant_request here is planned to pass
            # as a parameter, however due to grant_request are not
            # passed from conductor to vnflcm_driver, thus we put Null
            # value to grant and grant_reqeust temporary.
            # This part will be updated in next release.
            self._mgmt_manager.invoke(
                self._load_vnf_interface(
                    context, 'change_external_connectivity_end',
                    vnf_instance, vnfd_dict),
                'change_external_connectivity_end', context=context,
                vnf_instance=vnf_instance,
                change_ext_conn_request=change_ext_conn_req,
                grant=vnf_dict.get('grant'), grant_request=None)

        LOG.info("Request received for changing external connectivity "
                 "vnf '%s' is completed successfully", vnf_instance.id)
