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

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import encodeutils
from oslo_utils import excutils

from tacker.common import log

from tacker.common import driver_manager
from tacker.common import exceptions
from tacker import objects
from tacker.objects import fields
from tacker.vnflcm import abstract_driver
from tacker.vnflcm import utils as vnflcm_utils


LOG = logging.getLogger(__name__)
CONF = cfg.CONF


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
