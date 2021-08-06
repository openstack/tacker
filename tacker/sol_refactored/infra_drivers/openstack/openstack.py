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


import eventlet
import os
import pickle
import subprocess

from oslo_log import log as logging
from oslo_utils import uuidutils

from tacker.sol_refactored.common import config
from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.common import vnf_instance_utils as inst_utils
from tacker.sol_refactored.infra_drivers.openstack import heat_utils
from tacker.sol_refactored.infra_drivers.openstack import userdata_default
from tacker.sol_refactored import objects


LOG = logging.getLogger(__name__)

CONF = config.CONF


class Openstack(object):

    def __init__(self):
        pass

    def instantiate(self, req, inst, grant_req, grant, vnfd):
        # make HOT
        fields = self.make_hot(req, inst, grant_req, grant, vnfd)

        LOG.debug("stack fields: %s", fields)

        # create stack
        vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
        heat_client = heat_utils.HeatClient(vim_info)
        heat_client.create_stack(fields)

        # wait stack created
        stack_name = fields['stack_name']
        heat_client.wait_stack_create(stack_name)

        # get stack resource
        heat_reses = heat_client.get_resources(stack_name)

        # make instantiated_vnf_info
        self.make_instantiated_vnf_info(req, inst, grant, vnfd, heat_reses)

    def make_hot(self, req, inst, grant_req, grant, vnfd):
        flavour_id = req.flavourId
        hot_dict = vnfd.get_base_hot(flavour_id)
        if not hot_dict:
            raise sol_ex.BaseHOTNotDefined()

        userdata = None
        userdata_class = None
        if req.obj_attr_is_set('additionalParams'):
            userdata = req.additionalParams.get('lcm-operation-user-data')
            userdata_class = req.additionalParams.get(
                'lcm-operation-user-data-class')

        if userdata is None and userdata_class is None:
            LOG.debug("Processing default userdata instantiate")
            # NOTE: objects used here are dict compat.
            fields = userdata_default.DefaultUserData.instantiate(
                req, inst, grant_req, grant, vnfd.csar_dir)
        elif userdata is None or userdata_class is None:
            # Both must be specified.
            raise sol_ex.UserdataMissing()
        else:
            LOG.debug("Processing %s %s instantiate", userdata, userdata_class)

            tmp_csar_dir = vnfd.make_tmp_csar_dir()
            script_dict = {
                'request': req.to_dict(),
                'vnf_instance': inst.to_dict(),
                'grant_request': grant_req.to_dict(),
                'grant_response': grant.to_dict(),
                'tmp_csar_dir': tmp_csar_dir
            }
            script_path = os.path.join(
                os.path.dirname(__file__), "userdata_main.py")

            out = subprocess.run(["python3", script_path, "INSTANTIATE"],
                input=pickle.dumps(script_dict),
                capture_output=True)

            vnfd.remove_tmp_csar_dir(tmp_csar_dir)

            if out.returncode != 0:
                LOG.debug("execute userdata class instantiate failed: %s",
                    out.stderr)
                raise sol_ex.UserdataExecutionFailed(sol_detail=out.stderr)

            fields = pickle.loads(out.stdout)

        stack_name = heat_utils.get_stack_name(inst)
        fields['stack_name'] = stack_name
        fields['timeout_mins'] = (
            CONF.v2_vnfm.openstack_vim_stack_create_timeout)

        return fields

    def _address_range_data_to_info(self, range_data):
        obj = objects.ipOverEthernetAddressInfoV2_IpAddresses_AddressRange()
        obj.minAddress = range_data.minAddress
        obj.maxAddress = range_data.maxAddress
        return obj

    def _proto_data_to_info(self, proto_data):
        # make CpProtocolInfo (5.5.3.9b) from CpProtocolData (4.4.1.10b)
        proto_info = objects.CpProtocolInfoV2(
            layerProtocol=proto_data.layerProtocol
        )
        ip_info = objects.IpOverEthernetAddressInfoV2()

        ip_data = proto_data.ipOverEthernet
        if ip_data.obj_attr_is_set('macAddress'):
            ip_info.macAddress = ip_data.macAddress
        if ip_data.obj_attr_is_set('segmentationId'):
            ip_info.segmentationId = ip_data.segmentationId
        if ip_data.obj_attr_is_set('ipAddresses'):
            addr_infos = []
            for addr_data in ip_data.ipAddresses:
                addr_info = objects.IpOverEthernetAddressInfoV2_IpAddresses(
                    type=addr_data.type)
                if addr_data.obj_attr_is_set('fixedAddresses'):
                    addr_info.addresses = addr_data.fixedAddresses
                if addr_data.obj_attr_is_set('numDynamicAddresses'):
                    addr_info.isDynamic = True
                if addr_data.obj_attr_is_set('addressRange'):
                    addr_info.addressRange = self._address_range_data_to_info(
                        addr_data.addressRange)
                if addr_data.obj_attr_is_set('subnetId'):
                    addr_info.subnetId = addr_data.subnetId
                addr_infos.append(addr_info)
            ip_info.ipAddresses = addr_infos

        proto_info.ipOverEthernet = ip_info

        return proto_info

    def make_instantiated_vnf_info(self, req, inst, grant, vnfd, heat_reses):
        flavour_id = req.flavourId
        vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
        inst_vnf_info = objects.VnfInstanceV2_InstantiatedVnfInfo(
            flavourId=flavour_id,
            vnfState='STARTED',
        )

        # make virtualStorageResourceInfo
        storages = vnfd.get_storage_nodes(flavour_id)
        reses = heat_utils.get_storage_reses(heat_reses)
        storage_infos = []
        storage_info_to_heat_res = {}

        for res in reses:
            storage_name = res['resource_name']
            if storage_name not in list(storages.keys()):
                # should not occur. just check for consistency.
                LOG.debug("%s not in VNFD storage definition.", storage_name)
                continue
            storage_info = objects.VirtualStorageResourceInfoV2(
                id=uuidutils.generate_uuid(),
                virtualStorageDescId=storage_name,
                storageResource=objects.ResourceHandle(
                    resourceId=res['physical_resource_id'],
                    vimLevelResourceType=res['resource_type'],
                    vimConnectionId=vim_info.vimId,
                )
            )
            storage_infos.append(storage_info)
            storage_info_to_heat_res[storage_info.id] = res

        if storage_infos:
            inst_vnf_info.virtualStorageResourceInfo = storage_infos

        # make vnfcResourceInfo
        vdus = vnfd.get_vdu_nodes(flavour_id)
        reses = heat_utils.get_server_reses(heat_reses)
        vnfc_res_infos = []
        vnfc_res_info_to_heat_res = {}

        for res in reses:
            vdu_name = res['resource_name']
            if vdu_name not in list(vdus.keys()):
                # should not occur. just check for consistency.
                LOG.debug("%s not in VNFD VDU definition.", vdu_name)
                continue
            vnfc_res_info = objects.VnfcResourceInfoV2(
                id=uuidutils.generate_uuid(),
                vduId=vdu_name,
                computeResource=objects.ResourceHandle(
                    resourceId=res['physical_resource_id'],
                    vimLevelResourceType=res['resource_type'],
                    vimConnectionId=vim_info.vimId,
                ),
            )
            vdu_cps = vnfd.get_vdu_cps(flavour_id, vdu_name)
            cp_infos = []
            for cp in vdu_cps:
                cp_info = objects.VnfcResourceInfoV2_VnfcCpInfo(
                    id=uuidutils.generate_uuid(),
                    cpdId=cp,
                    # vnfExtCpId or vnfLinkPortId may set later
                )
                cp_infos.append(cp_info)
            if cp_infos:
                vnfc_res_info.vnfcCpInfo = cp_infos

            # find storages used by this
            storage_ids = []
            for storage_id, storage_res in storage_info_to_heat_res.items():
                if (vdu_name in storage_res.get('required_by', []) and
                        res.get('parent_resource') ==
                        storage_res.get('parent_resource')):
                    storage_ids.append(storage_id)
            if storage_ids:
                vnfc_res_info.storageResourceIds = storage_ids

            vnfc_res_infos.append(vnfc_res_info)
            vnfc_res_info_to_heat_res[vnfc_res_info.id] = res

        if vnfc_res_infos:
            inst_vnf_info.vnfcResourceInfo = vnfc_res_infos

        # make vnfVirtualLinkResourceInfo
        vls = vnfd.get_virtual_link_nodes(flavour_id)
        reses = heat_utils.get_network_reses(heat_reses)
        vnf_vl_infos = []
        vnf_vl_info_to_heat_res = {}

        for res in reses:
            vl_name = res['resource_name']
            if vl_name not in list(vls.keys()):
                # should not occur. just check for consistency.
                LOG.debug("%s not in VNFD VL definition.", vl_name)
                continue
            vnf_vl_info = objects.VnfVirtualLinkResourceInfoV2(
                id=uuidutils.generate_uuid(),
                vnfVirtualLinkDescId=vl_name,
                networkResource=objects.ResourceHandle(
                    resourceId=res['physical_resource_id'],
                    vimLevelResourceType=res['resource_type'],
                    vimConnectionId=vim_info.vimId,
                ),
                # vnfLinkPorts set later
            )
            vnf_vl_infos.append(vnf_vl_info)
            vnf_vl_info_to_heat_res[vnf_vl_info.id] = res

        if vnf_vl_infos:
            inst_vnf_info.vnfVirtualLinkResourceInfo = vnf_vl_infos

        # make extVirtualLinkInfo
        ext_vls = []
        req_ext_vls = []
        ext_cp_infos = []
        if grant.obj_attr_is_set('extVirtualLinks'):
            req_ext_vls = grant.extVirtualLinks
        elif req.obj_attr_is_set('extVirtualLinks'):
            req_ext_vls = req.extVirtualLinks

        for req_ext_vl in req_ext_vls:
            ext_vl = objects.ExtVirtualLinkInfoV2(
                id=req_ext_vl.id,
                resourceHandle=objects.ResourceHandle(
                    id=uuidutils.generate_uuid(),
                    resourceId=req_ext_vl.resourceId
                ),
                currentVnfExtCpData=req_ext_vl.extCps
            )
            if req_ext_vl.obj_attr_is_set('vimConnectionId'):
                ext_vl.resourceHandle.vimConnectionId = (
                    req_ext_vl.vimConnectionId)
            if req_ext_vl.obj_attr_is_set('resourceProviderId'):
                ext_vl.resourceHandle.resourceProviderId = (
                    req_ext_vl.resourceProviderId)

            ext_vls.append(ext_vl)

            if not req_ext_vl.obj_attr_is_set('extLinkPorts'):
                continue
            link_ports = []
            for req_link_port in req_ext_vl.extLinkPorts:
                link_port = objects.ExtLinkPortInfoV2(
                    id=req_link_port.id,
                    resourceHandle=req_link_port.resourceHandle,
                )
                ext_cp_info = objects.VnfExtCpInfoV2(
                    id=uuidutils.generate_uuid(),
                    extLinkPortId=link_port.id
                    # associatedVnfcCpId may set later
                )
                link_port.cpInstanceId = ext_cp_info.id

                for ext_cp in req_ext_vl.extCps:
                    found = False
                    for key, cp_conf in ext_cp.cpConfig.items():
                        if (cp_conf.obj_attr_is_set('linkPortId') and
                                cp_conf.linkPortId == link_port.id):
                            ext_cp_info.cpdId = ext_cp.cpdId
                            ext_cp_info.cpConfigId = key
                            # NOTE: cpProtocolInfo can't be filled
                            found = True
                            break
                    if found:
                        break

                link_ports.append(link_port)
                ext_cp_infos.append(ext_cp_info)

            ext_vl.extLinkPorts = link_ports

        if ext_vls:
            inst_vnf_info.extVirtualLinkInfo = ext_vls
        # ext_cp_infos set later

        # make extManagedVirtualLinkInfo
        ext_mgd_vls = []
        req_mgd_vls = []
        if grant.obj_attr_is_set('extManagedVirtualLinks'):
            req_mgd_vls = grant.extManagedVirtualLinks
        elif req.obj_attr_is_set('extManagedVirtualLinks'):
            req_mgd_vls = req.extManagedVirtualLinks

        for req_mgd_vl in req_mgd_vls:
            ext_mgd_vl = objects.ExtManagedVirtualLinkInfoV2(
                id=req_mgd_vl.id,
                vnfVirtualLinkDescId=req_mgd_vl.vnfVirtualLinkDescId,
                networkResource=objects.ResourceHandle(
                    id=uuidutils.generate_uuid(),
                    resourceId=req_mgd_vl.resourceId
                ),
            )
            if req_mgd_vl.obj_attr_is_set('vimConnectionId'):
                ext_mgd_vl.networkResource.vimConnectionId = (
                    req_mgd_vl.vimConnectionId)
            if req_mgd_vl.obj_attr_is_set('resourceProviderId'):
                ext_mgd_vl.networkResource.resourceProviderId = (
                    req_mgd_vl.resourceProviderId)

            ext_mgd_vls.append(ext_mgd_vl)

            if not req_mgd_vl.obj_attr_is_set('vnfLinkPort'):
                continue
            link_ports = []
            for req_link_port in req_mgd_vl.vnfLinkPort:
                link_port = objects.VnfLinkPortInfoV2(
                    id=req_link_port.vnfLinkPortId,
                    resourceHandle=req_link_port.resourceHandle,
                    cpInstanceType='EXT_CP',  # may be changed later
                    # cpInstanceId may set later
                )
                link_ports.append(link_port)
            ext_mgd_vl.vnfLinkPort = link_ports

        if ext_mgd_vls:
            inst_vnf_info.extManagedVirtualLinkInfo = ext_mgd_vls

        # make CP related infos
        vdu_cps = vnfd.get_vducp_nodes(flavour_id)
        reses = heat_utils.get_port_reses(heat_reses)

        for res in reses:
            cp_name = res['resource_name']
            if cp_name not in list(vdu_cps.keys()):
                # should not occur. just check for consistency.
                LOG.debug("%s not in VNFD CP definition.", cp_name)
                continue
            vl_name = vnfd.get_vl_name_from_cp(flavour_id, vdu_cps[cp_name])
            is_external = False
            if vl_name is None:  # extVirtualLink
                is_external = True

                # NOTE: object is diffrent from other vl types
                vnf_link_port = objects.ExtLinkPortInfoV2(
                    id=uuidutils.generate_uuid(),
                    resourceHandle=objects.ResourceHandle(
                        resourceId=res['physical_resource_id'],
                        vimLevelResourceType=res['resource_type'],
                        vimConnectionId=vim_info.vimId,
                    )
                )
                ext_cp_info = objects.VnfExtCpInfoV2(
                    id=uuidutils.generate_uuid(),
                    extLinkPortId=vnf_link_port.id,
                    cpdId=cp_name
                    # associatedVnfcCpId may set later
                )
                vnf_link_port.cpInstanceId = ext_cp_info.id

                found = False
                for ext_vl in ext_vls:
                    for ext_cp in ext_vl.currentVnfExtCpData:
                        if ext_cp.cpdId == cp_name:
                            found = True
                            break
                    if found:
                        break

                if found:
                    if ext_vl.obj_attr_is_set('extLinkPorts'):
                        ext_vl.extLinkPorts.append(vnf_link_port)
                    else:
                        ext_vl.extLinkPorts = [vnf_link_port]

                    for key, cp_conf in ext_cp.cpConfig.items():
                        # NOTE: it is assumed that there is one item
                        # (with cpProtocolData) of cpConfig at the moment.
                        if cp_conf.obj_attr_is_set('cpProtocolData'):
                            proto_infos = []
                            for proto_data in cp_conf.cpProtocolData:
                                proto_info = self._proto_data_to_info(
                                    proto_data)
                                proto_infos.append(proto_info)
                            ext_cp_info.cpProtocolInfo = proto_infos
                            ext_cp_info.cpConfigId = key
                            break

                ext_cp_infos.append(ext_cp_info)
            else:
                # Internal VL or extManagedVirtualLink
                vnf_link_port = objects.VnfLinkPortInfoV2(
                    id=uuidutils.generate_uuid(),
                    resourceHandle=objects.ResourceHandle(
                        resourceId=res['physical_resource_id'],
                        vimLevelResourceType=res['resource_type'],
                        vimConnectionId=vim_info.vimId,
                        cpInstanceType='EXT_CP'  # may be changed later
                    )
                )

                is_internal = False
                for vnf_vl_info in vnf_vl_infos:
                    if vnf_vl_info.vnfVirtualLinkDescId == vl_name:
                        # Internal VL
                        is_internal = True
                        if vnf_vl_info.obj_attr_is_set('vnfLinkPorts'):
                            vnf_vl_info.vnfLinkPorts.append(vnf_link_port)
                        else:
                            vnf_vl_info.vnfLinkPorts = [vnf_link_port]

                if not is_internal:
                    # extManagedVirtualLink
                    for ext_mgd_vl in ext_mgd_vls:
                        # should be found
                        if ext_mgd_vl.vnfVirtualLinkDescId == vl_name:
                            if ext_mgd_vl.obj_attr_is_set('vnfLinkPorts'):
                                ext_mgd_vl.vnfLinkPorts.append(vnf_link_port)
                            else:
                                ext_mgd_vl.vnfLinkPorts = [vnf_link_port]

            # link to vnfcResourceInfo.vnfcCpInfo
            for vnfc_res_info in vnfc_res_infos:
                if not vnfc_res_info.obj_attr_is_set('vnfcCpInfo'):
                    continue
                vnfc_res = vnfc_res_info_to_heat_res[vnfc_res_info.id]
                vdu_name = vnfc_res_info.vduId
                if not (vdu_name in res.get('required_by', []) and
                        res.get('parent_resource') ==
                        vnfc_res.get('parent_resource')):
                    continue
                for vnfc_cp in vnfc_res_info.vnfcCpInfo:
                    if vnfc_cp.cpdId != cp_name:
                        continue
                    if is_external:
                        vnfc_cp.vnfExtCpId = vnf_link_port.cpInstanceId
                        for ext_cp_info in ext_cp_infos:
                            if ext_cp_info.extLinkPortId == vnf_link_port.id:
                                ext_cp_info.associatedVnfcCpId = vnfc_cp.id
                                break
                    else:
                        vnf_link_port.cpInstanceType = 'VNFC_CP'
                        vnf_link_port.cpInstanceId = vnfc_cp.id
                        vnfc_cp.vnfLinkPortId = vnf_link_port.id
                    break

        if ext_cp_infos:
            inst_vnf_info.extCpInfo = ext_cp_infos

        # NOTE: The followings are not handled at the moment.
        # - handle tosca.nodes.nfv.VnfExtCp type
        #   Note that there is no example in current tacker examples which use
        #   tosca.nodes.nfv.VnfExtCp type and related BaseHOT definitions.
        # - in the case of specifying linkPortId of extVirtualLinks or
        #   extManagedVirtualLinks, the link of vnfcCpInfo is not handled
        #   because the association of compute resource and port resource
        #   is not identified.

        # make vnfcInfo
        # NOTE: vnfcInfo only exists in SOL002
        vnfc_infos = []
        for vnfc_res_info in vnfc_res_infos:
            vnfc_info = objects.VnfcInfoV2(
                id=uuidutils.generate_uuid(),
                vduId=vnfc_res_info.vduId,
                vnfcResourceInfoId=vnfc_res_info.id,
                vnfcState='STARTED'
            )
            vnfc_infos.append(vnfc_info)

        if vnfc_infos:
            inst_vnf_info.vnfcInfo = vnfc_infos

        inst.instantiatedVnfInfo = inst_vnf_info

    def terminate(self, req, inst, grant_req, grant, vnfd):
        if req.terminationType == 'GRACEFUL':
            timeout = CONF.v2_vnfm.default_graceful_termination_timeout
            if req.obj_attr_is_set('gracefulTerminationTimeout'):
                timeout = req.gracefulTerminationTimeout
            eventlet.sleep(timeout)

        # delete stack
        vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
        heat_client = heat_utils.HeatClient(vim_info)
        stack_name = heat_utils.get_stack_name(inst)
        heat_client.delete_stack(stack_name)
        heat_client.wait_stack_delete(stack_name)
