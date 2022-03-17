# Copyright (C) 2021 Nippon Telegraph and Telephone Corporation
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


import os

from oslo_log import log as logging
from oslo_utils import uuidutils

from tacker.common import utils as common_utils
import tacker.conf
from tacker.objects import fields
from tacker.objects import vnf_package
from tacker.objects import vnf_package_vnfd

from tacker.sol_refactored.common import config
from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.common import lcm_op_occ_utils as lcmocc_utils
from tacker.sol_refactored.common import vim_utils
from tacker.sol_refactored.common import vnf_instance_utils as inst_utils
from tacker.sol_refactored.common import vnfd_utils
from tacker.sol_refactored.nfvo import glance_utils
from tacker.sol_refactored import objects
from tacker.sol_refactored.objects.v2 import fields as v2_fields


CONF = tacker.conf.CONF

LOG = logging.getLogger(__name__)

# NOTE:
# It is NFVO implementation used when an external NFVO is not used.
# It implements only functions necessary for vnflcm v2.
# It uses original tacker vnfpkgm v1 for vnf package managemnet
# and adds grant functions.


class LocalNfvo(object):

    def __init__(self):
        self.inst_vim_info = {}
        self.inst_vnfd_id = {}

    def onboarded_show(self, context, id):
        pkg_vnfd = vnf_package_vnfd.VnfPackageVnfd().get_by_vnfdId(
            context, id)
        if not pkg_vnfd:
            raise sol_ex.VnfdIdNotFound(vnfd_id=id)

        vnf_pkg = vnf_package.VnfPackage().get_by_id(
            context, pkg_vnfd.package_uuid)
        if not vnf_pkg:
            # never happen. just for code consistency.
            raise sol_ex.VnfdIdNotFound(vnfd_id=id)

        if (vnf_pkg.onboarding_state !=
                fields.PackageOnboardingStateType.ONBOARDED):
            # NOTE: API itself should be return 409 but it is used by
            # only vnf_instance create and will be converted to 422 in it.
            raise sol_ex.VnfdIdNotFound(vnfd_id=id)

        # NOTE:
        # This is used for vnf_instance create at the moment.
        # It is set only attributes necessary for vnf_instance create.
        res = objects.VnfPkgInfoV2(
            id=pkg_vnfd.package_uuid,
            vnfdId=pkg_vnfd.vnfd_id,
            vnfProvider=pkg_vnfd.vnf_provider,
            vnfProductName=pkg_vnfd.vnf_product_name,
            vnfSoftwareVersion=pkg_vnfd.vnf_software_version,
            vnfdVersion=pkg_vnfd.vnfd_version,
            operationalState=vnf_pkg.operational_state
        )

        return res

    def get_csar_dir(self, context, vnfd_id):
        pkg_vnfd = vnf_package_vnfd.VnfPackageVnfd().get_by_vnfdId(
            context, vnfd_id)
        if not pkg_vnfd:
            raise sol_ex.VnfdIdNotFound(vnfd_id=vnfd_id)

        csar_dir = os.path.join(CONF.vnf_package.vnf_package_csar_path,
                                pkg_vnfd.package_uuid)
        if not os.path.isdir(csar_dir):
            raise sol_ex.VnfdIdNotFound(vnfd_id=vnfd_id)

        return csar_dir

    def get_vnfd(self, context, vnfd_id):
        vnfd = vnfd_utils.Vnfd(vnfd_id)
        vnfd.init_from_csar_dir(self.get_csar_dir(context, vnfd_id))
        return vnfd

    def _glance_create_image(self, vim_info, vnfd, sw_data, inst_id):
        min_disk = 0
        if 'min_disk' in sw_data:
            min_disk = common_utils.MemoryUnit.convert_unit_size_to_num(
                sw_data['min_disk'], 'GB')

        min_ram = 0
        if 'min_ram' in sw_data:
            min_ram = common_utils.MemoryUnit.convert_unit_size_to_num(
                sw_data['min_ram'], 'MB')

        filename = os.path.join(vnfd.csar_dir,
                                sw_data['file'].split('../')[-1])

        # NOTE: use tag to find to delete images when terminate vnf instance.
        create_args = {
            'min_disk': min_disk,
            'min_ram': min_ram,
            'disk_format': sw_data.get('disk_format'),
            'container_format': sw_data.get('container_format'),
            'filename': filename,
            'visibility': 'private',
            'tags': [inst_id]
        }

        glance_client = glance_utils.GlanceClient(vim_info)
        image = glance_client.create_image(sw_data['name'], **create_args)

        LOG.debug("image created name: %s id: %s", sw_data['name'], image.id)

        return image.id

    def _get_vim_info(self, context, grant_req):
        lcmocc = lcmocc_utils.get_lcmocc(context, grant_req.vnfLcmOpOccId)
        inst_req = lcmocc.operationParams
        if inst_req.obj_attr_is_set('vimConnectionInfo'):
            return inst_utils.select_vim_info(inst_req.vimConnectionInfo)

        # NOTE: exception is not raised.
        return vim_utils.get_default_vim(context)

    def instantiate_grant(self, context, grant_req, grant_res):
        # handle ZoneInfo
        zone_list = config.CONF.v2_nfvo.test_grant_zone_list
        zone_id = None
        if len(zone_list) > 0:
            zone_infos = []
            for zone in zone_list:
                zone_info = objects.ZoneInfoV1(
                    id=uuidutils.generate_uuid(),
                    zoneId=zone
                )
                zone_infos.append(zone_info)
            grant_res.zones = zone_infos
            zone_id = zone_infos[0].id

        # handle addResources.
        # only copy req to res. i.e. grant all.
        attr = 'addResources'
        if grant_req.obj_attr_is_set(attr):
            add_res = []
            for res_def in grant_req[attr]:
                g_info = objects.GrantInfoV1(
                    resourceDefinitionId=res_def.id
                )
                if zone_id is not None and res_def.type == 'COMPUTE':
                    g_info.zoneId = zone_id
                add_res.append(g_info)
            grant_res[attr] = add_res

        # handle vimAssets
        # if there is an artifact, create glance image.
        vnfd = self.get_vnfd(context, grant_req.vnfdId)
        sw_image_data = vnfd.get_sw_image_data(grant_req.flavourId)
        vim_sw_images = []
        for res_id, sw_data in sw_image_data.items():
            if 'file' in sw_data:
                # if artifact is specified, create glance image.
                # it may fail. catch exception and raise 403(not granted)
                # if error occur.

                # get vim_info to access glance
                vim_info = self._get_vim_info(context, grant_req)
                if vim_info is None:
                    msg = "No vimConnectionInfo to create glance image"
                    raise sol_ex.LocalNfvoGrantFailed(sol_detail=msg)

                try:
                    image = self._glance_create_image(vim_info, vnfd, sw_data,
                            grant_req.vnfInstanceId)
                except Exception:
                    msg = "glance image create failed"
                    LOG.exception(msg)
                    raise sol_ex.LocalNfvoGrantFailed(sol_detail=msg)
            else:
                # there is no artifact. suppose image already created.
                image = sw_data['name']
            vim_sw_image = objects.VimSoftwareImageV1(
                vnfdSoftwareImageId=res_id,
                vimSoftwareImageId=image)
            vim_sw_images.append(vim_sw_image)
        if vim_sw_images:
            grant_res.vimAssets = objects.GrantV1_VimAssets(
                softwareImages=vim_sw_images
            )

    def change_vnfpkg_grant(self, context, grant_req, grant_res):
        attr_list = ['updateResources', 'addResources', 'removeResources']
        for attr in attr_list:
            if grant_req.obj_attr_is_set(attr):
                res_list = []
                for res_def in grant_req[attr]:
                    g_info = objects.GrantInfoV1(res_def.id)
                    res_list.append(g_info)
                    grant_res[attr] = res_list
        vnfd = self.get_vnfd(context, grant_req.vnfdId)
        sw_image_data = vnfd.get_sw_image_data(grant_req.flavourId)
        target_vdu_ids = [res['resourceTemplateId'] for
                          res in grant_req['updateResources']]
        vdu_nodes = {key: value for key, value in vnfd.get_vdu_nodes(
            grant_req.flavourId).items() if key in target_vdu_ids}
        target_storage_nodes = []
        for key, value in vdu_nodes.items():
            target_storage_nodes.extend(vnfd.get_vdu_storages(value))

        vim_sw_images = []
        for res_id, sw_data in sw_image_data.items():
            if 'file' in sw_data and (res_id in target_storage_nodes or
                                      res_id in target_vdu_ids):
                vim_info = self._get_vim_info(context, grant_req)
                if vim_info is None:
                    msg = "No VimConnectionInfo to create glance image"
                    LOG.exception(msg)
                    raise sol_ex.LocalNfvoGrantFailed(sol_detail=msg)
                try:
                    image = self._glance_create_image(
                        vim_info, vnfd, sw_data, grant_req.vnfInstanceId)
                except Exception:
                    msg = "glance image create failed"
                    LOG.exception(msg)
                    raise sol_ex.LocalNfvoGrantFailed(sol_detail=msg)
            else:
                image = sw_data['name']
            vim_sw_image = objects.VimSoftwareImageV1(
                vnfdSoftwareImageId=res_id,
                vimSoftwareImageId=image)
            vim_sw_images.append(vim_sw_image)
        if vim_sw_images:
            grant_res.vimAssets = objects.GrantV1_VimAssets(
                softwareImages=vim_sw_images
            )

    def grant(self, context, grant_req):
        grant_res = objects.GrantV1(
            id=uuidutils.generate_uuid(),
            vnfInstanceId=grant_req.vnfInstanceId,
            vnfLcmOpOccId=grant_req.vnfLcmOpOccId
        )

        # NOTE: considered instantiate only at the moment.
        # terminate is granted with no grant_res constructed.
        if grant_req.operation == v2_fields.LcmOperationType.INSTANTIATE:
            self.instantiate_grant(context, grant_req, grant_res)

        elif grant_req.operation == v2_fields.LcmOperationType.CHANGE_VNFPKG:
            self.change_vnfpkg_grant(context, grant_req, grant_res)

        endpoint = config.CONF.v2_vnfm.endpoint
        grant_res._links = objects.GrantV1_Links(
            vnfLcmOpOcc=objects.Link(
                href=lcmocc_utils.lcmocc_href(grant_req.vnfLcmOpOccId,
                                              endpoint)),
            vnfInstance=objects.Link(
                href=inst_utils.inst_href(grant_req.vnfInstanceId,
                                          endpoint))
        )
        grant_res._links.self = objects.Link(
            href="{}/grant/v1/grants/{}".format(endpoint, grant_res.id))

        return grant_res

    def _update_vnf_pkg_usage_state(self, context, vnfd_id, state):
        pkg_vnfd = vnf_package_vnfd.VnfPackageVnfd().get_by_vnfdId(
            context, vnfd_id)
        if not pkg_vnfd:
            # should not happen. just for code consistency.
            LOG.error("VnfPackage of vnfdID %s not found.", vnfd_id)
            return

        vnf_pkg = vnf_package.VnfPackage().get_by_id(
            context, pkg_vnfd.package_uuid)
        if not vnf_pkg:
            # should not happen. just for code consistency.
            LOG.error("VnfPackage %s not found.", pkg_vnfd.package_uuid)
            return

        # Multiple vnf instances can be created with same vnfd_id,
        # so the state must be changed to `NOT_IN_USE` only when
        # there is no vnf instance.
        if state == fields.PackageUsageStateType.NOT_IN_USE:
            insts = objects.VnfInstanceV2.get_by_filter(context,
                                                        vnfdId=vnfd_id)
            if insts:
                return

        # prevent raising exception since this method is not a part of VNFM.
        try:
            vnf_pkg.usage_state = state
            vnf_pkg.save()
        except Exception as ex:
            LOG.error("Update vnfPackage %s to %s failed: %s",
                      pkg_vnfd.package_uuid, state, ex)

    def recv_inst_create_notification(self, context, inst):
        # update vnfPackage usageState to IN_USE
        self._update_vnf_pkg_usage_state(context, inst.vnfdId,
            fields.PackageUsageStateType.IN_USE)

    def recv_inst_delete_notification(self, context, inst):
        # update vnfPackage usageState to NOT_IN_USE
        self._update_vnf_pkg_usage_state(context, inst.vnfdId,
            fields.PackageUsageStateType.NOT_IN_USE)

    def _glance_delete_images(self, vim_info, inst_id):
        # prevent raising exception since this method is not a part of VNFM.
        try:
            glance_client = glance_utils.GlanceClient(vim_info)
            images = glance_client.list_images(tag=inst_id)
        except Exception:
            LOG.error("Get glance images for vnfInstance %s failed.", inst_id)
            return

        for image in images:
            try:
                glance_client.delete_image(image.id)
                LOG.debug("image deleted name: %s id: %s",
                        image.name, image.id)
            except Exception:
                LOG.error("image delete %s failed.", image.id)

    def recv_lcmocc_notification(self, context, lcmocc, inst):
        if lcmocc.operation == v2_fields.LcmOperationType.TERMINATE:
            if (lcmocc.operationState ==
                    v2_fields.LcmOperationStateType.PROCESSING):
                # register vim_info of vnf instance so that
                # it is used later to delete glance image.
                vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
                self.inst_vim_info[inst.id] = vim_info
            elif (lcmocc.operationState ==
                    v2_fields.LcmOperationStateType.FAILED_TEMP):
                self.inst_vim_info.pop(inst.id, None)
            elif (lcmocc.operationState ==
                    v2_fields.LcmOperationStateType.COMPLETED):
                vim_info = self.inst_vim_info.pop(inst.id, None)
                if vim_info is None:
                    # never happen. just for code consistency.
                    return
                if vim_info.vimType == 'ETSINFV.OPENSTACK_KEYSTONE.V_3':
                    self._glance_delete_images(vim_info, inst.id)
        elif lcmocc.operation == v2_fields.LcmOperationType.MODIFY_INFO or (
                lcmocc.operation == v2_fields.LcmOperationType.CHANGE_VNFPKG):
            if (lcmocc.operationState ==
                    v2_fields.LcmOperationStateType.PROCESSING):
                # register vnfdId of vnf instance so that
                # it is used later to check vnfdId change.
                self.inst_vnfd_id[inst.id] = inst.vnfdId
            elif (lcmocc.operationState ==
                    v2_fields.LcmOperationStateType.FAILED_TEMP):
                self.inst_vnfd_id.pop(inst.id, None)
            elif (lcmocc.operationState ==
                    v2_fields.LcmOperationStateType.COMPLETED):
                vnfd_id = self.inst_vnfd_id.pop(inst.id, None)
                if vnfd_id is None:
                    # never happen. just for code consistency.
                    return
                if vnfd_id != inst.vnfdId:
                    # vnfdId is changed. change usage_state of vnf package
                    self._update_vnf_pkg_usage_state(context, vnfd_id,
                        fields.PackageUsageStateType.NOT_IN_USE)
                    self._update_vnf_pkg_usage_state(context, inst.vnfdId,
                        fields.PackageUsageStateType.IN_USE)
