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

import copy
from datetime import datetime
import functools
import inspect
import re
import six
import time
import traceback
import yaml

from oslo_config import cfg
from oslo_log import log as logging
from oslo_serialization import jsonutils
from oslo_utils import encodeutils
from oslo_utils import excutils

from tacker.common import log

from tacker.common import driver_manager
from tacker.common import exceptions
from tacker.common import safe_utils
from tacker.common import utils
from tacker.conductor.conductorrpc import vnf_lcm_rpc
from tacker import manager
from tacker import objects
from tacker.objects import fields
from tacker.vnflcm import abstract_driver
from tacker.vnflcm import utils as vnflcm_utils
from tacker.vnfm.mgmt_drivers import constants as mgmt_constants

LOG = logging.getLogger(__name__)
CONF = cfg.CONF


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
                    self.rpc_api.sendNotification(context, notification)
                except Exception as e:
                    LOG.warning("Failed to revert scale info for vnf "
                                "instance %(id)s. Error: %(error)s",
                                {"id": vnf_instance.id, "error": e})
    return decorated_function


class VnfLcmDriver(abstract_driver.VnfInstanceAbstractDriver):

    def __init__(self):
        super(VnfLcmDriver, self).__init__()
        self.rpc_api = vnf_lcm_rpc.VNFLcmRPCAPI()
        self._vnfm_plugin = manager.TackerManager.get_service_plugins()['VNFM']
        self._vnf_manager = driver_manager.DriverManager(
            'tacker.tacker.vnfm.drivers',
            cfg.CONF.tacker.infra_driver)

    def _vnf_instance_update(self, context, vnf_instance, **kwargs):
        """Update vnf instance in the database using kwargs as value."""

        for k, v in kwargs.items():
            setattr(vnf_instance, k, v)
        vnf_instance.save()

    def _instantiate_vnf(self, context, vnf_instance, vnf_dict,
            vim_connection_info, instantiate_vnf_req):
        vnfd_dict = vnflcm_utils._get_vnfd_dict(context, vnf_instance.vnfd_id,
                instantiate_vnf_req.flavour_id)
        base_hot_dict, nested_hot_dict = vnflcm_utils. \
            get_base_nest_hot_dict(context,
                                   instantiate_vnf_req.flavour_id,
                                   vnf_instance.vnfd_id)
        vnf_package_path = None
        if base_hot_dict is not None:
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

        try:
            instance_id = self._vnf_manager.invoke(
                vim_connection_info.vim_type, 'instantiate_vnf',
                context=context, plugin=self._vnfm_plugin,
                vnf_instance=vnf_instance,
                vnfd_dict=final_vnf_dict, grant_response=vnf_resources,
                vim_connection_info=vim_connection_info,
                base_hot_dict=base_hot_dict,
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
           not vnf_instance.instantiated_vnf_info.instance_id:
            vnf_instance.instantiated_vnf_info.instance_id = instance_id
        if vnf_dict['attributes'].get('scaling_group_names'):
            vnf_instance.instantiated_vnf_info.scale_status = \
                vnf_dict['scale_status']

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

    @log.log
    def instantiate_vnf(self, context, vnf_instance, vnf_dict,
            instantiate_vnf_req):

        vim_connection_info_list = vnflcm_utils.\
            _get_vim_connection_info_from_vnf_req(vnf_instance,
                    instantiate_vnf_req)

        self._vnf_instance_update(context, vnf_instance,
                vim_connection_info=vim_connection_info_list)

        vim_info = vnflcm_utils._get_vim(context,
                instantiate_vnf_req.vim_connection_info)

        vim_connection_info = objects.VimConnectionInfo.obj_from_primitive(
            vim_info, context)

        self._instantiate_vnf(context, vnf_instance, vnf_dict,
                              vim_connection_info, instantiate_vnf_req)

    @log.log
    @revert_to_error_task_state
    def terminate_vnf(self, context, vnf_instance, terminate_vnf_req):

        vim_info = vnflcm_utils._get_vim(context,
            vnf_instance.vim_connection_info)

        vim_connection_info = objects.VimConnectionInfo.obj_from_primitive(
            vim_info, context)

        LOG.info("Terminating vnf %s", vnf_instance.id)
        try:
            self._delete_vnf_instance_resources(context, vnf_instance,
                    vim_connection_info, terminate_vnf_req=terminate_vnf_req)

            vnf_instance.instantiated_vnf_info.reinitialize()
            self._vnf_instance_update(context, vnf_instance,
                vim_connection_info=[], task_state=None)

            LOG.info("Vnf terminated %s successfully", vnf_instance.id)
        except Exception as exp:
            with excutils.save_and_reraise_exception():
                LOG.error("Unable to terminate vnf '%s' instance. "
                          "Error: %s", vnf_instance.id,
                          encodeutils.exception_to_unicode(exp))

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
            heal_vnf_request):
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

        try:
            self._vnf_manager.invoke(
                vim_connection_info.vim_type, 'heal_vnf_wait',
                context=context, vnf_instance=vnf_instance,
                vim_connection_info=vim_connection_info)
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
        try:
            self._delete_vnf_instance_resources(context, vnf_instance,
                vim_connection_info, update_instantiated_state=False)
        except Exception as exc:
            with excutils.save_and_reraise_exception() as exc_ctxt:
                exc_ctxt.reraise = False
                err_msg = ("Failed to delete vnf resources for vnf instance "
                          "%(id)s before respawning. The vnf is in "
                          "inconsistent state. Error: %(error)s")
                LOG.error(err_msg % {"id": vnf_instance.id,
                          "error": six.text_type(exc)})
                raise exceptions.VnfHealFailed(id=vnf_instance.id,
                    error=encodeutils.exception_to_unicode(exc))

        # InstantiateVnfRequest is not stored in the db as it's mapped
        # to InstantiatedVnfInfo version object. Convert InstantiatedVnfInfo
        # version object to InstantiateVnfRequest so that vnf can be
        # instantiated.

        instantiate_vnf_request = objects.InstantiateVnfRequest.\
            from_vnf_instance(vnf_instance)

        try:
            self._instantiate_vnf(context, vnf_instance, vnf_dict,
                                  vim_connection_info, instantiate_vnf_request)
        except Exception as exc:
            with excutils.save_and_reraise_exception() as exc_ctxt:
                exc_ctxt.reraise = False
                err_msg = ("Failed to instantiate vnf instance "
                          "%(id)s after termination. The vnf is in "
                          "inconsistent state. Error: %(error)s")
                LOG.error(err_msg % {"id": vnf_instance.id,
                          "error": six.text_type(exc)})
                raise exceptions.VnfHealFailed(id=vnf_instance.id,
                    error=encodeutils.exception_to_unicode(exc))

        self._vnf_instance_update(context, vnf_instance,
                    instantiation_state=fields.VnfInstanceState.INSTANTIATED,
                    task_state=None)

    @log.log
    @revert_to_error_task_state
    def heal_vnf(self, context, vnf_instance, vnf_dict, heal_vnf_request):
        LOG.info("Request received for healing vnf '%s'", vnf_instance.id)
        vim_info = vnflcm_utils._get_vim(context,
            vnf_instance.vim_connection_info)

        vim_connection_info = objects.VimConnectionInfo.obj_from_primitive(
            vim_info, context)

        if not heal_vnf_request.vnfc_instance_id:
            self._respawn_vnf(context, vnf_instance, vnf_dict,
                             vim_connection_info, heal_vnf_request)
        else:
            self._heal_vnf(context, vnf_instance, vim_connection_info,
                      heal_vnf_request)

        LOG.info("Request received for healing vnf '%s' is completed "
                 "successfully", vnf_instance.id)

    def _scale_vnf_pre(self, context, vnf_info, vnf_instance,
                      scale_vnf_request, vim_connection_info):
        self._vnfm_plugin._update_vnf_scaling(
            context, vnf_info, 'ACTIVE', 'PENDING_' + scale_vnf_request.type)
        vnf_lcm_op_occ = vnf_info['vnf_lcm_op_occ']
        vnf_lcm_op_occ.error_point = 2

        scale_id_list = []
        scale_name_list = []
        grp_id = None
        vnf_info['policy_name'] = scale_vnf_request.aspect_id
        if scale_vnf_request.type == 'SCALE_IN':
            vnfd_yaml = vnf_info['vnfd']['attributes'].get(
                'vnfd_' + vnf_instance.instantiated_vnf_info.flavour_id, '')
            vnfd_dict = yaml.safe_load(vnfd_yaml)
            # mgmt_driver from vnfd
            vnf_node = self._get_node_template_for_vnf(vnfd_dict)
            if vnf_node and vnf_node.get('interfaces'):
                if vnf_node['interfaces']['Vnflcm']['scale_start']:
                    vnf_info['vnfd']['mgmt_driver'] = \
                        vnf_node['interfaces']['Vnflcm']['scale_start']
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

            # mgmt_driver pre
            if len(scale_id_list) != 0 and vnf_info['vnfd'].get('mgmt_driver'):
                if len(scale_id_list) > 1:
                    stack_value = []
                    stack_value = scale_id_list
                else:
                    stack_value = scale_id_list[0]
                kwargs = {
                    mgmt_constants.KEY_ACTION:
                        mgmt_constants.ACTION_SCALE_IN_VNF,
                    mgmt_constants.KEY_KWARGS:
                        {'vnf': vnf_info},
                    mgmt_constants.KEY_SCALE:
                        stack_value,
                }
                self._vnfm_plugin.mgmt_call(context, vnf_info, kwargs)
        else:
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
        vnf_lcm_op_occ.error_point = 3
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
        vnf_lcm_op_occ = vnf_info['vnf_lcm_op_occ']
        vnf_lcm_op_occ.error_point = 6
        if scale_vnf_request.type == 'SCALE_OUT':
            vnfd_yaml =\
                vnf_info['vnfd']['attributes'].\
                get('vnfd_' + vnf_instance.instantiated_vnf_info.flavour_id,
                '')
            vnf_info['policy_name'] = scale_vnf_request.aspect_id
            vnfd_dict = yaml.safe_load(vnfd_yaml)
            # mgmt_driver from vnfd
            vnf_node = self._get_node_template_for_vnf(vnfd_dict)
            if vnf_node and vnf_node.get('interfaces'):
                if vnf_node['interfaces']['Vnflcm']['scale_end']:
                    vnf_info['vnfd']['mgmt_driver'] = \
                        vnf_node['interfaces']['Vnflcm']['scale_end']
            scale_id_after = self._vnf_manager.invoke(
                vim_connection_info.vim_type,
                'get_scale_ids',
                plugin=self,
                context=context,
                vnf_dict=vnf_info,
                auth_attr=vim_connection_info.access_info,
                region_name=vim_connection_info.access_info.get('region_name')
            )
            id_list = []
            id_list = list(set(scale_id_after) - set(scale_id_list))
            vnf_info['res_num'] = len(scale_id_after)
            if len(id_list) != 0 and vnf_info['vnfd'].get('mgmt_driver'):
                if len(id_list) > 1:
                    stack_value = []
                    stack_value = id_list
                else:
                    stack_value = id_list[0]
                kwargs = {
                    mgmt_constants.KEY_ACTION:
                        mgmt_constants.ACTION_SCALE_OUT_VNF,
                    mgmt_constants.KEY_KWARGS:
                        {'vnf': vnf_info},
                    mgmt_constants.KEY_SCALE:
                        stack_value,
                }
                self._vnfm_plugin.mgmt_call(context, vnf_info, kwargs)
        vnf_lcm_op_occ.error_point = 7
        vnf_instance.instantiated_vnf_info.scale_level =\
            vnf_info['after_scale_level']
        scaleGroupDict = \
            jsonutils.loads(vnf_info['attributes']['scale_group'])
        (scaleGroupDict
        ['scaleGroupDict'][scale_vnf_request.aspect_id]['default']) =\
            vnf_info['res_num']
        vnf_info['attributes']['scale_group'] =\
            jsonutils.dump_as_bytes(scaleGroupDict)
        vnf_lcm_op_occ = vnf_info['vnf_lcm_op_occ']
        vnf_lcm_op_occ.operation_state = 'COMPLETED'
        vnf_lcm_op_occ.resource_changes = resource_changes
        self._vnfm_plugin._update_vnf_scaling(context, vnf_info,
                                          'PENDING_' + scale_vnf_request.type,
                                          'ACTIVE',
                                          vnf_instance=vnf_instance,
                                          vnf_lcm_op_occ=vnf_lcm_op_occ)

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

    def _scale_vnf(self, context, vnf_info, vnf_instance,
                   scale_vnf_request, vim_connection_info,
                   scale_name_list, grp_id):
        # action_driver
        LOG.debug("vnf_info['vnfd']['attributes'] %s",
        vnf_info['vnfd']['attributes'])
        vnf_lcm_op_occ = vnf_info['vnf_lcm_op_occ']
        vnf_lcm_op_occ.error_point = 4
        self.scale(context, vnf_info, scale_vnf_request,
                   vim_connection_info, scale_name_list, grp_id)
        vnf_lcm_op_occ.error_point = 5

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

        vim_info = vnflcm_utils._get_vim(context,
            vnf_instance.vim_connection_info)

        vim_connection_info = objects.VimConnectionInfo.obj_from_primitive(
            vim_info, context)

        scale_id_list, scale_name_list, grp_id = self._scale_vnf_pre(
            context, vnf_info,
            vnf_instance,
            scale_vnf_request,
            vim_connection_info)

        self._scale_vnf(context, vnf_info,
                        vnf_instance,
                        scale_vnf_request,
                        vim_connection_info,
                        scale_name_list, grp_id)

        resource_changes = self._scale_resource_update(context, vnf_info,
                                    vnf_instance,
                                    scale_vnf_request,
                                    vim_connection_info)

        self._scale_vnf_post(context, vnf_info,
                             vnf_instance,
                             scale_vnf_request,
                             vim_connection_info,
                             scale_id_list,
                             resource_changes)

        LOG.info("Request received for scale vnf '%s' is completed "
                 "successfully", vnf_instance.id)

    def scale(
            self,
            context,
            vnf_info,
            scale_vnf_request,
            vim_connection_info,
            scale_name_list,
            grp_id):
        self._vnf_manager = driver_manager.DriverManager(
            'tacker.tacker.vnfm.drivers',
            cfg.CONF.tacker.infra_driver)
        policy = {}
        policy['instance_id'] = vnf_info['instance_id']
        policy['name'] = scale_vnf_request.aspect_id
        policy['vnf'] = vnf_info
        if scale_vnf_request.type == 'SCALE_IN':
            policy['action'] = 'in'
        else:
            policy['action'] = 'out'
        LOG.debug(
            "is_reverse: %s",
            scale_vnf_request.additional_params.get('is_reverse'))
        scale_json = vnf_info['attributes']['scale_group']
        scaleGroupDict = jsonutils.loads(scale_json)
        key_aspect = scale_vnf_request.aspect_id
        default = scaleGroupDict['scaleGroupDict'][key_aspect]['default']
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
                grp_id=grp_id
            )
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
                region_name=vim_connection_info.access_info.get('region_name')
            )
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
            heat_template = vnf_info['attributes']['heat_template']
            policy_in_name = scale_vnf_request.aspect_id + '_scale_in'
            policy_out_name = scale_vnf_request.aspect_id + '_scale_out'

            heat_resource = yaml.safe_load(heat_template)
            if scale_vnf_request.type == 'SCALE_IN':
                policy['action'] = 'in'
                policy_temp = heat_resource['resources'][policy_in_name]
                policy_prop = policy_temp['properties']
                cooldown = policy_prop.get('cooldown')
                policy_name = policy_in_name
            else:
                policy['action'] = 'out'
                policy_temp = heat_resource['resources'][policy_out_name]
                policy_prop = policy_temp['properties']
                cooldown = policy_prop.get('cooldown')
                policy_name = policy_out_name

            policy_temp = heat_resource['resources'][policy_name]
            policy_prop = policy_temp['properties']
            for i in range(scale_vnf_request.number_of_steps):
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
                if i != scale_vnf_request.number_of_steps - 1:
                    if cooldown:
                        time.sleep(cooldown)

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
        if 'resource_changes' in vnf_lcm_op_occs \
                and vnf_lcm_op_occs.resource_changes:
            if 'affected_vnfcs' in vnf_lcm_op_occs.resource_changes:
                if len(vnf_lcm_op_occs.resource_changes.affected_vnfcs) > 0:
                    resource_changes.affected_vnfcs.extend(
                        vnf_lcm_op_occs.resource_changes.affected_vnfcs)
            if 'affected_virtual_storages' in vnf_lcm_op_occs.resource_changes:
                if len(vnf_lcm_op_occs.resource_changes.
                       affected_virtual_storages) > 0:
                    resource_changes.affected_virtual_storages.extend(
                        vnf_lcm_op_occs.resource_changes.
                        affected_virtual_storages)
            if 'affected_virtual_links' in vnf_lcm_op_occs.resource_changes:
                if len(vnf_lcm_op_occs.resource_changes.
                        affected_virtual_links) > 0:
                    resource_changes.affected_virtual_links.extend(
                        vnf_lcm_op_occs.resource_changes.
                        affected_virtual_links)
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
                and vnf_lcm_op_occs.error_point >= 4:
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
        if vnf_lcm_op_occs.error_point == 7:
            if vnf_lcm_op_occs.operation == 'SCALE':
                vnfd_yaml = vnf_info['vnfd']['attributes'].\
                    get('vnfd_' +
                        vnf_instance.instantiated_vnf_info.flavour_id, '')
                vnfd_dict = yaml.safe_load(vnfd_yaml)
                # mgmt_driver from vnfd
                vnf_node = self._get_node_template_for_vnf(vnfd_dict)
                if vnf_node and vnf_node.get('interfaces'):
                    if vnf_node['interfaces'].get('Vnflcm'):
                        if vnf_node['interfaces']['Vnflcm'].get('scale_start'):
                            vnf_info['vnfd']['mgmt_driver'] = \
                                vnf_node['interfaces']['Vnflcm']['scale_start']
                vnf_info['action'] = 'in'
                if len(scale_id_list) != 0 and vnf_info['vnfd'].get(
                        'mgmt_driver'):
                    if len(scale_id_list) > 1:
                        stack_value = []
                        stack_value = scale_id_list
                    else:
                        stack_value = scale_id_list[0]
                    kwargs = {
                        mgmt_constants.KEY_ACTION:
                            mgmt_constants.ACTION_SCALE_IN_VNF,
                        mgmt_constants.KEY_KWARGS:
                            {'vnf': vnf_info},
                        mgmt_constants.KEY_SCALE:
                            stack_value,
                    }
                    self._rollback_mgmt_call(context, vnf_info, kwargs)

            else:
                vnfd_yaml = vnf_info['vnfd']['attributes'].\
                    get('vnfd_' +
                        vnf_instance.instantiated_vnf_info.flavour_id, '')
                vnfd_dict = yaml.safe_load(vnfd_yaml)
                # mgmt_driver from vnfd
                vnf_node = self._get_node_template_for_vnf(vnfd_dict)
                if vnf_node and vnf_node.get('interfaces'):
                    if vnf_node['interfaces'].get('Vnflcm'):
                        if vnf_node['interfaces']['Vnflcm'].get(
                                'termination_start'):
                            vnf_info['vnfd']['mgmt_driver'] = vnf_node[
                                'interfaces']['Vnflcm']['termination_start']
                if len(scale_id_list) != 0 and vnf_info['vnfd'].get(
                        'mgmt_driver'):
                    kwargs = {
                        mgmt_constants.KEY_ACTION:
                            mgmt_constants.ACTION_DELETE_VNF,
                        mgmt_constants.KEY_KWARGS:
                            {'vnf': vnf_info}
                    }
                    self._rollback_mgmt_call(context, vnf_info, kwargs)
            vnf_lcm_op_occs.error_point = 6

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
        if vnf_lcm_op_occs.error_point >= 4:
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
                    grp_id=grp_id)
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
                    vnf_id=instance_id, auth_attr=access_info)

                self._vnf_manager.invoke(vim_connection_info.vim_type,
                    'delete_wait', plugin=self, context=context,
                    vnf_id=instance_id, auth_attr=access_info)

        vnf_lcm_op_occs.error_point = 3

    def _update_vnf_rollback_pre(self, context, vnf_info):
        self._vnfm_plugin._update_vnf_rollback_pre(context, vnf_info)

    def _update_vnf_rollback(self, context, vnf_info,
                             vnf_instance, vnf_lcm_op_occs):
        self._vnfm_plugin._update_vnf_rollback(context, vnf_info,
                                              'ERROR',
                                              'ACTIVE',
                                              vnf_instance=vnf_instance,
                                              vnf_lcm_op_occ=vnf_lcm_op_occs)

    def _update_vnf_rollback_status_err(self, context, vnf_info):
        self._vnfm_plugin._update_vnf_rollback_status_err(context, vnf_info)

    def _rollback_mgmt_call(self, context, vnf_info, kwargs):
        self._vnfm_plugin.mgmt_call(context, vnf_info, kwargs)

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
            resource_changes = self._term_resource_update(
                context, vnf_info, vnf_instance)

        vnf_lcm_op_occs.error_point = 2

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
