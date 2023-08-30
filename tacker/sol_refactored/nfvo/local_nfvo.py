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

from tacker.common import exceptions
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
# It uses original tacker vnfpkgm v1 for vnf package management
# and adds grant functions.


class LocalNfvo(object):

    def __init__(self):
        self.inst_vim_info = {}
        self.inst_vnfd_id = {}

    def onboarded_show(self, context, id):
        try:
            pkg_vnfd = vnf_package_vnfd.VnfPackageVnfd().get_by_id(context, id)
            vnf_pkg = vnf_package.VnfPackage().get_by_id(
                context, pkg_vnfd.package_uuid)
        except (exceptions.VnfPackageVnfdNotFound,
                exceptions.VnfPackageNotFound):
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
        try:
            pkg_vnfd = vnf_package_vnfd.VnfPackageVnfd().get_by_id(
                context, vnfd_id)
        except exceptions.VnfPackageVnfdNotFound:
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
        req = lcmocc.operationParams
        if grant_req.operation == v2_fields.LcmOperationType.INSTANTIATE:
            if req.obj_attr_is_set('vimConnectionInfo'):
                return inst_utils.select_vim_info(req.vimConnectionInfo)
        else:
            # should be found
            inst = inst_utils.get_inst(context, grant_req.vnfInstanceId)
            return inst_utils.select_vim_info(inst.vimConnectionInfo)

        # NOTE: exception is not raised.
        return vim_utils.get_default_vim(context)

    def _handle_vim_assets(self, context, grant_req, grant_res, vnfd):
        vim_info = self._get_vim_info(context, grant_req)
        if vim_info is None:
            msg = "No vimConnectionInfo to handle glance image"
            raise sol_ex.LocalNfvoGrantFailed(sol_detail=msg)
        elif vim_info.vimType != 'ETSINFV.OPENSTACK_KEYSTONE.V_3':
            return

        target_vdus = {res['resourceTemplateId']
                       for res in grant_req['addResources']}
        all_sw_image_data = vnfd.get_sw_image_data(grant_req.flavourId)
        sw_image_data = {res_id: sw_data
                         for res_id, sw_data in all_sw_image_data.items()
                         if res_id in target_vdus}

        vim_sw_images = []
        image_names = {}
        if grant_req.operation != v2_fields.LcmOperationType.INSTANTIATE:
            glance_client = glance_utils.GlanceClient(vim_info)
            images = glance_client.list_images(tag=grant_req.vnfInstanceId)
            image_names = {image.name: image.id for image in images}

        for res_id, sw_data in sw_image_data.items():
            if 'file' in sw_data and sw_data['name'] in image_names:
                image = image_names[sw_data['name']]
            elif 'file' in sw_data:
                # if artifact is specified, create glance image.
                # it may fail. catch exception and raise 403(not granted)
                # if error occurs.
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

    def _handle_zoneinfo(self, grant_res):
        zone_list = config.CONF.v2_nfvo.test_grant_zone_list
        if len(zone_list) == 0:
            return None
        zone_infos = []
        for zone in zone_list:
            zone_info = objects.ZoneInfoV1(
                id=uuidutils.generate_uuid(),
                zoneId=zone
            )
            zone_infos.append(zone_info)
        grant_res.zones = zone_infos
        return zone_infos[0].id

    def _handle_addresources(self, grant_req, grant_res, zone_id):
        # only copy req to res. i.e. grant all.
        attr = 'addResources'
        if not grant_req.obj_attr_is_set(attr):
            return
        add_res = []
        for res_def in grant_req[attr]:
            g_info = objects.GrantInfoV1(
                resourceDefinitionId=res_def.id
            )
            if zone_id is not None and res_def.type == 'COMPUTE':
                g_info.zoneId = zone_id
            add_res.append(g_info)
        grant_res[attr] = add_res

    def instantiate_grant(self, context, grant_req, grant_res):
        # handle ZoneInfo
        zone_id = self._handle_zoneinfo(grant_res)

        # handle addResources
        self._handle_addresources(grant_req, grant_res, zone_id)

        # handle vimAssets
        # if there is an artifact, create glance image.
        vnfd = self.get_vnfd(context, grant_req.vnfdId)
        self._handle_vim_assets(context, grant_req, grant_res, vnfd)

    def change_vnfpkg_grant(self, context, grant_req, grant_res):
        if not grant_req.obj_attr_is_set('addResources'):
            return

        # handle vimAssets
        # if there is an artifact, create glance image.
        vnfd = self.get_vnfd(context, grant_req.dstVnfdId)
        self._handle_vim_assets(context, grant_req, grant_res, vnfd)

    def scale_grant(self, context, grant_req, grant_res):
        if not grant_req.obj_attr_is_set('addResources'):
            return
        # handle ZoneInfo
        zone_id = self._handle_zoneinfo(grant_res)

        # handle addResources
        self._handle_addresources(grant_req, grant_res, zone_id)

        # handle vimAssets
        # if there is an artifact, create glance image.
        vnfd = self.get_vnfd(context, grant_req.vnfdId)
        self._handle_vim_assets(context, grant_req, grant_res, vnfd)

    def heal_grant(self, context, grant_req, grant_res):
        if not grant_req.obj_attr_is_set('addResources'):
            return

        # handle vimAssets
        # if there is an artifact, create glance image.
        vnfd = self.get_vnfd(context, grant_req.vnfdId)
        self._handle_vim_assets(context, grant_req, grant_res, vnfd)

    def grant(self, context, grant_req):
        grant_res = objects.GrantV1(
            id=uuidutils.generate_uuid(),
            vnfInstanceId=grant_req.vnfInstanceId,
            vnfLcmOpOccId=grant_req.vnfLcmOpOccId
        )

        # NOTE: considered instantiate and change_vnfpkg only at the moment.
        if grant_req.operation == v2_fields.LcmOperationType.INSTANTIATE:
            self.instantiate_grant(context, grant_req, grant_res)
        elif grant_req.operation == v2_fields.LcmOperationType.CHANGE_VNFPKG:
            self.change_vnfpkg_grant(context, grant_req, grant_res)
        elif grant_req.operation == v2_fields.LcmOperationType.SCALE:
            self.scale_grant(context, grant_req, grant_res)
        elif grant_req.operation == v2_fields.LcmOperationType.HEAL:
            self.heal_grant(context, grant_req, grant_res)

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
        try:
            pkg_vnfd = vnf_package_vnfd.VnfPackageVnfd().get_by_id(
                context, vnfd_id)
        except exceptions.VnfPackageVnfdNotFound:
            # should not happen. just for code consistency.
            LOG.error("VnfPackage of vnfdID %s not found.", vnfd_id)
            return

        try:
            vnf_pkg = vnf_package.VnfPackage().get_by_id(
                context, pkg_vnfd.package_uuid)
        except exceptions.VnfPackageNotFound:
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
        elif lcmocc.operation == v2_fields.LcmOperationType.INSTANTIATE:
            if (lcmocc.operationState ==
                    v2_fields.LcmOperationStateType.ROLLED_BACK):
                vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
                if vim_info is None:
                    # never happen. just for code consistency.
                    return
                if vim_info.vimType == 'ETSINFV.OPENSTACK_KEYSTONE.V_3':
                    self._glance_delete_images(vim_info, inst.id)
