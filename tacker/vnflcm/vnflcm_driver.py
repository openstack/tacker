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
import functools
import inspect
import six
import time

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import encodeutils
from oslo_utils import excutils

from tacker.common import log

from tacker.common import driver_manager
from tacker.common import exceptions
from tacker.common import safe_utils
from tacker.common import utils
from tacker import objects
from tacker.objects import fields
from tacker.vnflcm import abstract_driver
from tacker.vnflcm import utils as vnflcm_utils


LOG = logging.getLogger(__name__)
CONF = cfg.CONF


@utils.expects_func_args('vnf_instance')
def rollback_vnf_instantiated_resources(function):
    """Decorator to rollback resources created during vnf instantiation"""

    def _rollback_vnf(vnflcm_driver, context, vnf_instance):
        vim_info = vnflcm_utils._get_vim(context,
                vnf_instance.vim_connection_info)

        vim_connection_info = objects.VimConnectionInfo.obj_from_primitive(
            vim_info, context)

        LOG.info("Rollback vnf %s", vnf_instance.id)
        try:
            vnflcm_driver._delete_vnf_instance_resources(context, vnf_instance,
                    vim_connection_info)

            if vnf_instance.instantiated_vnf_info:
                vnf_instance.instantiated_vnf_info.reinitialize()

            vnflcm_driver._vnf_instance_update(context, vnf_instance,
                    vim_connection_info=[], task_state=None)

            LOG.info("Vnf %s rollback completed successfully", vnf_instance.id)
        except Exception as ex:
            LOG.error("Unable to rollback vnf instance "
                      "%s due to error: %s", vnf_instance.id, ex)

    @functools.wraps(function)
    def decorated_function(self, context, *args, **kwargs):
        try:
            return function(self, context, *args, **kwargs)
        except Exception as exp:
            with excutils.save_and_reraise_exception():
                wrapped_func = safe_utils.get_wrapped_function(function)
                keyed_args = inspect.getcallargs(wrapped_func, self, context,
                                                 *args, **kwargs)
                vnf_instance = keyed_args['vnf_instance']
                LOG.error("Failed to instantiate vnf %(id)s. Error: %(error)s",
                          {"id": vnf_instance.id,
                           "error": six.text_type(exp)})

                _rollback_vnf(self, context, vnf_instance)

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


class VnfLcmDriver(abstract_driver.VnfInstanceAbstractDriver):

    def __init__(self):
        super(VnfLcmDriver, self).__init__()
        self._vnf_manager = driver_manager.DriverManager(
            'tacker.tacker.vnfm.drivers',
            cfg.CONF.tacker.infra_driver)

    def _vnf_instance_update(self, context, vnf_instance, **kwargs):
        """Update vnf instance in the database using kwargs as value."""

        for k, v in kwargs.items():
            setattr(vnf_instance, k, v)
        vnf_instance.save()

    def _instantiate_vnf(self, context, vnf_instance, vim_connection_info,
            instantiate_vnf_req):
        vnfd_dict = vnflcm_utils._get_vnfd_dict(context, vnf_instance.vnfd_id,
                instantiate_vnf_req.flavour_id)
        base_hot_dict = vnflcm_utils._get_base_hot_dict(
            context, vnf_instance.vnfd_id)
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
            vnf_software_images=vnf_software_images)

        # save the vnf resources in the db
        for _, resources in vnf_resources.items():
            for vnf_resource in resources:
                vnf_resource.create()

        vnfd_dict_to_create_final_dict = copy.deepcopy(vnfd_dict)
        final_vnf_dict = vnflcm_utils._make_final_vnf_dict(
            vnfd_dict_to_create_final_dict, vnf_instance.id,
            vnf_instance.vnf_instance_name, param_for_subs_map)

        try:
            instance_id = self._vnf_manager.invoke(
                vim_connection_info.vim_type, 'instantiate_vnf',
                context=context, vnf_instance=vnf_instance,
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

        vnf_instance.instantiated_vnf_info = objects.InstantiatedVnfInfo(
            flavour_id=instantiate_vnf_req.flavour_id,
            instantiation_level_id=instantiate_vnf_req.instantiation_level_id,
            vnf_instance_id=vnf_instance.id,
            instance_id=instance_id,
            ext_cp_info=[])

        try:
            self._vnf_manager.invoke(
                vim_connection_info.vim_type, 'create_wait',
                plugin=self, context=context,
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

        vnflcm_utils._build_instantiated_vnf_info(vnfd_dict,
                instantiate_vnf_req, vnf_instance, vim_connection_info.vim_id)

        self._vnf_manager.invoke(vim_connection_info.vim_type,
                'post_vnf_instantiation', context=context,
                vnf_instance=vnf_instance,
                vim_connection_info=vim_connection_info)

    @log.log
    @rollback_vnf_instantiated_resources
    def instantiate_vnf(self, context, vnf_instance, instantiate_vnf_req):

        vim_connection_info_list = vnflcm_utils.\
            _get_vim_connection_info_from_vnf_req(vnf_instance,
                    instantiate_vnf_req)

        self._vnf_instance_update(context, vnf_instance,
                vim_connection_info=vim_connection_info_list)

        vim_info = vnflcm_utils._get_vim(context,
                instantiate_vnf_req.vim_connection_info)

        vim_connection_info = objects.VimConnectionInfo.obj_from_primitive(
            vim_info, context)

        self._instantiate_vnf(context, vnf_instance, vim_connection_info,
                              instantiate_vnf_req)

        self._vnf_instance_update(context, vnf_instance,
                    instantiation_state=fields.VnfInstanceState.INSTANTIATED,
                    task_state=None)

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

        if vnf_instance.instantiated_vnf_info and \
                vnf_instance.instantiated_vnf_info.instance_id:

            instance_id = vnf_instance.instantiated_vnf_info.instance_id
            access_info = vim_connection_info.access_info

            LOG.info("Deleting stack %(instance)s for vnf %(id)s ",
                    {"instance": instance_id, "id": vnf_instance.id})

            if terminate_vnf_req:
                if (terminate_vnf_req.termination_type == 'GRACEFUL' and
                        terminate_vnf_req.graceful_termination_timeout > 0):
                    time.sleep(terminate_vnf_req.graceful_termination_timeout)

            self._vnf_manager.invoke(vim_connection_info.vim_type,
                'delete', plugin=self, context=context,
                vnf_id=instance_id, auth_attr=access_info)

            if update_instantiated_state:
                vnf_instance.instantiation_state = \
                    fields.VnfInstanceState.NOT_INSTANTIATED
                vnf_instance.save()

            self._vnf_manager.invoke(vim_connection_info.vim_type,
                'delete_wait', plugin=self, context=context,
                vnf_id=instance_id, auth_attr=access_info)

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
            LOG.error("Failed to update vnf %(id)s resources for instance"
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

    def _respawn_vnf(self, context, vnf_instance, vim_connection_info,
            heal_vnf_request):
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
            self._instantiate_vnf(context, vnf_instance, vim_connection_info,
                                  instantiate_vnf_request)
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
    def heal_vnf(self, context, vnf_instance, heal_vnf_request):
        LOG.info("Request received for healing vnf '%s'", vnf_instance.id)
        vim_info = vnflcm_utils._get_vim(context,
            vnf_instance.vim_connection_info)

        vim_connection_info = objects.VimConnectionInfo.obj_from_primitive(
            vim_info, context)

        if not heal_vnf_request.vnfc_instance_id:
            self._respawn_vnf(context, vnf_instance, vim_connection_info,
                         heal_vnf_request)
        else:
            self._heal_vnf(context, vnf_instance, vim_connection_info,
                      heal_vnf_request)

        LOG.info("Request received for healing vnf '%s' is completed "
                 "successfully", vnf_instance.id)
