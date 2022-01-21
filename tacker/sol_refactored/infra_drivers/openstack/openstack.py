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


from dateutil import parser
import eventlet
import json
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
from tacker.sol_refactored.objects.v2 import fields as v2fields


LOG = logging.getLogger(__name__)

CONF = config.CONF

LINK_PORT_PREFIX = 'req-'
CP_INFO_PREFIX = 'cp-'


# Id of the resources in instantiatedVnfInfo related methods.
# NOTE: instantiatedVnfInfo is re-created in each operation.
# Id of the resources in instantiatedVnfInfo is based on
# heat resource-id so that id is not changed at re-creation.
# Some ids are same as heat resource-id and some ids are
# combination of prefix and other ids.
def _make_link_port_id(link_port_id):
    # prepend 'req-' to distinguish from ports which are
    # created by heat.
    return '{}{}'.format(LINK_PORT_PREFIX, link_port_id)


def _is_link_port(link_port_id):
    return link_port_id.startswith(LINK_PORT_PREFIX)


def _make_cp_info_id(link_port_id):
    return '{}{}'.format(CP_INFO_PREFIX, link_port_id)


def _make_combination_id(a, b):
    return '{}-{}'.format(a, b)


class Openstack(object):

    def __init__(self):
        pass

    def instantiate(self, req, inst, grant_req, grant, vnfd):
        # make HOT
        fields = self._make_hot(req, inst, grant_req, grant, vnfd)

        LOG.debug("stack fields: %s", fields)

        stack_name = fields['stack_name']

        # create or update stack
        vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
        heat_client = heat_utils.HeatClient(vim_info)
        status, _ = heat_client.get_status(stack_name)
        if status is None:
            heat_client.create_stack(fields)
        else:
            heat_client.update_stack(stack_name, fields)

        # get stack resource
        heat_reses = heat_client.get_resources(stack_name)

        # make instantiated_vnf_info
        self._make_instantiated_vnf_info(req, inst, grant_req, grant, vnfd,
            heat_reses)

    def instantiate_rollback(self, req, inst, grant_req, grant, vnfd):
        vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
        heat_client = heat_utils.HeatClient(vim_info)
        stack_name = heat_utils.get_stack_name(inst)
        status, _ = heat_client.get_status(stack_name)
        if status is not None:
            heat_client.delete_stack(stack_name)

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

    def _update_nfv_dict(self, heat_client, stack_name, fields):
        parameters = heat_client.get_parameters(stack_name)
        LOG.debug("ORIG parameters: %s", parameters)
        # NOTE: parameters['nfv'] is string
        orig_nfv_dict = json.loads(parameters.get('nfv', '{}'))
        if 'nfv' in fields['parameters']:
            fields['parameters']['nfv'] = inst_utils.json_merge_patch(
                orig_nfv_dict, fields['parameters']['nfv'])
        LOG.debug("NEW parameters: %s", fields['parameters'])
        return fields

    def scale(self, req, inst, grant_req, grant, vnfd):
        vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
        heat_client = heat_utils.HeatClient(vim_info)

        # make HOT
        fields = self._make_hot(req, inst, grant_req, grant, vnfd)

        LOG.debug("stack fields: %s", fields)

        stack_name = fields.pop('stack_name')

        # mark unhealthy to servers to be removed if scale in
        if req.type == 'SCALE_IN':
            vnfc_res_ids = [res_def.resource.resourceId
                            for res_def in grant_req.removeResources
                            if res_def.type == 'COMPUTE']
            for vnfc in inst.instantiatedVnfInfo.vnfcResourceInfo:
                if vnfc.computeResource.resourceId in vnfc_res_ids:
                    if 'parent_stack_id' not in vnfc.metadata:
                        # It means definition of VDU in the BaseHOT
                        # is inappropriate.
                        raise sol_ex.UnexpectedParentResourceDefinition()
                    heat_client.mark_unhealthy(
                        vnfc.metadata['parent_stack_id'],
                        vnfc.metadata['parent_resource_name'])

        # update stack
        fields = self._update_nfv_dict(heat_client, stack_name, fields)
        heat_client.update_stack(stack_name, fields)

        # get stack resource
        heat_reses = heat_client.get_resources(stack_name)

        # make instantiated_vnf_info
        self._make_instantiated_vnf_info(req, inst, grant_req, grant, vnfd,
            heat_reses)

    def scale_rollback(self, req, inst, grant_req, grant, vnfd):
        # NOTE: rollback is supported for scale out only
        vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
        heat_client = heat_utils.HeatClient(vim_info)
        stack_name = heat_utils.get_stack_name(inst)
        heat_reses = heat_client.get_resources(stack_name)

        # mark unhealthy to added servers while scale out
        vnfc_ids = [vnfc.id
                    for vnfc in inst.instantiatedVnfInfo.vnfcResourceInfo]
        for res in heat_utils.get_server_reses(heat_reses):
            if res['physical_resource_id'] not in vnfc_ids:
                metadata = self._make_vnfc_metadata(res, heat_reses)
                if 'parent_stack_id' not in metadata:
                    # It means definition of VDU in the BaseHOT
                    # is inappropriate.
                    raise sol_ex.UnexpectedParentResourceDefinition()
                heat_client.mark_unhealthy(
                    metadata['parent_stack_id'],
                    metadata['parent_resource_name'])

        # update (put back) 'desired_capacity' parameter
        fields = self._update_nfv_dict(heat_client, stack_name,
            userdata_default.DefaultUserData.scale_rollback(
                req, inst, grant_req, grant, vnfd.csar_dir))

        heat_client.update_stack(stack_name, fields)

        # NOTE: instantiatedVnfInfo is not necessary to update since it
        # should be same as before scale API started.

    def _make_hot(self, req, inst, grant_req, grant, vnfd):
        if grant_req.operation == v2fields.LcmOperationType.INSTANTIATE:
            flavour_id = req.flavourId
        else:
            flavour_id = inst.instantiatedVnfInfo.flavourId

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
            LOG.debug("Processing default userdata %s", grant_req.operation)
            # NOTE: objects used here are dict compat.
            method = getattr(userdata_default.DefaultUserData,
                             grant_req.operation.lower())
            fields = method(req, inst, grant_req, grant, vnfd.csar_dir)
        elif userdata is None or userdata_class is None:
            # Both must be specified.
            raise sol_ex.UserdataMissing()
        else:
            LOG.debug("Processing %s %s %s", userdata, userdata_class,
                grant_req.operation)

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

            out = subprocess.run(["python3", script_path],
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

    def _get_checked_reses(self, nodes, reses):
        names = list(nodes.keys())

        def _check_res_in_vnfd(res):
            if res['resource_name'] in names:
                return True
            else:
                # should not occur. just check for consistency.
                LOG.debug("%s not in VNFD definition.", res['resource_name'])
                return False

        return {res['physical_resource_id']: res
                for res in reses if _check_res_in_vnfd(res)}

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

    def _make_ext_vl_info_from_req(self, req, grant, ext_cp_infos):
        # make extVirtualLinkInfo
        ext_vls = []
        req_ext_vls = []
        if grant.obj_attr_is_set('extVirtualLinks'):
            req_ext_vls = grant.extVirtualLinks
        elif req.obj_attr_is_set('extVirtualLinks'):
            req_ext_vls = req.extVirtualLinks

        for req_ext_vl in req_ext_vls:
            ext_vl = objects.ExtVirtualLinkInfoV2(
                id=req_ext_vl.id,
                resourceHandle=objects.ResourceHandle(
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
                    id=_make_link_port_id(req_link_port.id),
                    resourceHandle=req_link_port.resourceHandle,
                )
                ext_cp_info = objects.VnfExtCpInfoV2(
                    id=_make_cp_info_id(link_port.id),
                    extLinkPortId=link_port.id
                    # associatedVnfcCpId may set later
                )
                link_port.cpInstanceId = ext_cp_info.id

                for ext_cp in req_ext_vl.extCps:
                    found = False
                    for key, cp_conf in ext_cp.cpConfig.items():
                        if (cp_conf.obj_attr_is_set('linkPortId') and
                                cp_conf.linkPortId == req_link_port.id):
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

        return ext_vls

    def _make_ext_vl_info_from_inst(self, old_inst_vnf_info, ext_cp_infos):
        # make extVirtualLinkInfo from old inst.extVirtualLinkInfo
        ext_vls = []
        old_cp_infos = []

        if old_inst_vnf_info.obj_attr_is_set('extVirtualLinkInfo'):
            ext_vls = old_inst_vnf_info.extVirtualLinkInfo
        if old_inst_vnf_info.obj_attr_is_set('extCpInfo'):
            old_cp_infos = old_inst_vnf_info.extCpInfo

        for ext_vl in ext_vls:
            if not ext_vl.obj_attr_is_set('extLinkPorts'):
                continue
            new_link_ports = []
            for link_port in ext_vl.extLinkPorts:
                if not _is_link_port(link_port.id):
                    # port created by heat. re-create later
                    continue

                new_link_ports.append(link_port)
                for ext_cp in old_cp_infos:
                    if ext_cp.id == link_port.cpInstanceId:
                        ext_cp_infos.append(ext_cp)
                        break

            ext_vl.extLinkPorts = new_link_ports

        return ext_vls

    def _make_ext_mgd_vl_info_from_req(self, vnfd, flavour_id, req, grant):
        # make extManagedVirtualLinkInfo
        ext_mgd_vls = []
        req_mgd_vls = []
        if grant.obj_attr_is_set('extManagedVirtualLinks'):
            req_mgd_vls = grant.extManagedVirtualLinks
        elif req.obj_attr_is_set('extManagedVirtualLinks'):
            req_mgd_vls = req.extManagedVirtualLinks

        vls = vnfd.get_virtual_link_nodes(flavour_id)
        for req_mgd_vl in req_mgd_vls:
            vl_name = req_mgd_vl.vnfVirtualLinkDescId
            if vl_name not in list(vls.keys()):
                # should not occur. just check for consistency.
                LOG.debug("%s not in VNFD VL definition.", vl_name)
                continue
            ext_mgd_vl = objects.ExtManagedVirtualLinkInfoV2(
                id=req_mgd_vl.id,
                vnfVirtualLinkDescId=vl_name,
                networkResource=objects.ResourceHandle(
                    id=uuidutils.generate_uuid(),
                    resourceId=req_mgd_vl.resourceId
                )
            )
            if req_mgd_vl.obj_attr_is_set('vimConnectionId'):
                ext_mgd_vl.networkResource.vimConnectionId = (
                    req_mgd_vl.vimConnectionId)
            if req_mgd_vl.obj_attr_is_set('resourceProviderId'):
                ext_mgd_vl.networkResource.resourceProviderId = (
                    req_mgd_vl.resourceProviderId)

            ext_mgd_vls.append(ext_mgd_vl)

            if req_mgd_vl.obj_attr_is_set('vnfLinkPort'):
                ext_mgd_vl.vnfLinkPort = [
                    objects.VnfLinkPortInfoV2(
                        id=_make_link_port_id(req_link_port.vnfLinkPortId),
                        resourceHandle=req_link_port.resourceHandle,
                        cpInstanceType='EXT_CP',  # may be changed later
                        # cpInstanceId may set later
                    )
                    for req_link_port in req_mgd_vl.vnfLinkPort
                ]

        return ext_mgd_vls

    def _make_ext_mgd_vl_info_from_inst(self, old_inst_vnf_info):
        # make extManagedVirtualLinkInfo
        ext_mgd_vls = []

        if old_inst_vnf_info.obj_attr_is_set('extManagedVirtualLinkInfo'):
            ext_mgd_vls = old_inst_vnf_info.extManagedVirtualLinkInfo

        for ext_mgd_vl in ext_mgd_vls:
            if ext_mgd_vl.obj_attr_is_set('vnfLinkPorts'):
                ext_mgd_vl.vnfLinkPorts = [link_port
                    for link_port in ext_mgd_vl.vnfLinkPorts
                    if _is_link_port(link_port.id)]

        return ext_mgd_vls

    def _find_ext_vl_by_cp_name(self, cp_name, ext_vl_infos):
        for ext_vl_info in ext_vl_infos:
            for ext_cp_data in ext_vl_info.currentVnfExtCpData:
                if ext_cp_data.cpdId == cp_name:
                    return ext_vl_info, ext_cp_data

        return None, None

    def _link_ext_port_info(self, ext_port_infos, ext_vl_infos, ext_cp_infos,
            port_reses):
        for ext_port_info in ext_port_infos:
            res = port_reses[ext_port_info.id]
            cp_name = res['resource_name']
            ext_cp_info = objects.VnfExtCpInfoV2(
                id=_make_cp_info_id(ext_port_info.id),
                extLinkPortId=ext_port_info.id,
                cpdId=cp_name
                # associatedVnfcCpId may set later
            )
            ext_port_info.cpInstanceId = ext_cp_info.id

            ext_vl_info, ext_cp_data = self._find_ext_vl_by_cp_name(
                cp_name, ext_vl_infos)

            if ext_vl_info:
                if ext_vl_info.obj_attr_is_set('extLinkPorts'):
                    ext_vl_info.extLinkPorts.append(ext_port_info)
                else:
                    ext_vl_info.extLinkPorts = [ext_port_info]

                for key, cp_conf in ext_cp_data.cpConfig.items():
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

    def _find_vnfc_cp_info(self, port_res, vnfc_res_infos, server_reses):
        for vnfc_res_info in vnfc_res_infos:
            if not vnfc_res_info.obj_attr_is_set('vnfcCpInfo'):
                continue
            vnfc_res = server_reses[vnfc_res_info.id]
            vdu_name = vnfc_res_info.vduId
            cp_name = port_res['resource_name']
            if (vdu_name in port_res.get('required_by', []) and
                    port_res.get('parent_resource') ==
                    vnfc_res.get('parent_resource')):
                for vnfc_cp in vnfc_res_info.vnfcCpInfo:
                    if vnfc_cp.cpdId == cp_name:
                        return vnfc_cp

    def _link_vnfc_cp_info(self, vnfc_res_infos, ext_port_infos,
            vnf_port_infos, ext_cp_infos, server_reses, port_reses):

        for ext_port_info in ext_port_infos:
            port_res = port_reses[ext_port_info.id]
            vnfc_cp = self._find_vnfc_cp_info(port_res, vnfc_res_infos,
                server_reses)
            if vnfc_cp:
                # should be found
                vnfc_cp.vnfExtCpId = ext_port_info.cpInstanceId
                for ext_cp_info in ext_cp_infos:
                    if ext_cp_info.extLinkPortId == ext_port_info.id:
                        ext_cp_info.associatedVnfcCpId = vnfc_cp.id
                        break

        for vnf_port_info in vnf_port_infos:
            port_res = port_reses[vnf_port_info.id]
            vnfc_cp = self._find_vnfc_cp_info(port_res, vnfc_res_infos,
                server_reses)
            if vnfc_cp:
                # should be found
                vnf_port_info.cpInstanceType = 'VNFC_CP'
                vnf_port_info.cpInstanceId = vnfc_cp.id
                vnfc_cp.vnfLinkPortId = vnf_port_info.id

    def _make_vnfc_metadata(self, server_res, heat_reses):
        metadata = {
            'creation_time': server_res['creation_time'],
        }
        parent_res = heat_utils.get_parent_resource(server_res, heat_reses)
        if parent_res:
            metadata['parent_stack_id'] = (
                heat_utils.get_resource_stack_id(parent_res))
            metadata['parent_resource_name'] = parent_res['resource_name']

        return metadata

    def _make_instantiated_vnf_info(self, req, inst, grant_req, grant, vnfd,
            heat_reses):
        init = False
        if grant_req.operation == v2fields.LcmOperationType.INSTANTIATE:
            init = True
            flavour_id = req.flavourId
        else:
            flavour_id = inst.instantiatedVnfInfo.flavourId
        vim_info = inst_utils.select_vim_info(inst.vimConnectionInfo)
        vducp_nodes = vnfd.get_vducp_nodes(flavour_id)

        storage_reses = self._get_checked_reses(
            vnfd.get_storage_nodes(flavour_id),
            heat_utils.get_storage_reses(heat_reses))
        server_reses = self._get_checked_reses(vnfd.get_vdu_nodes(flavour_id),
            heat_utils.get_server_reses(heat_reses))
        network_reses = self._get_checked_reses(
            vnfd.get_virtual_link_nodes(flavour_id),
            heat_utils.get_network_reses(heat_reses))
        port_reses = self._get_checked_reses(vducp_nodes,
            heat_utils.get_port_reses(heat_reses))

        def _res_to_handle(res):
            return objects.ResourceHandle(
                resourceId=res['physical_resource_id'],
                vimLevelResourceType=res['resource_type'],
                vimConnectionId=vim_info.vimId)

        storage_infos = [
            objects.VirtualStorageResourceInfoV2(
                id=res_id,
                virtualStorageDescId=res['resource_name'],
                storageResource=_res_to_handle(res)
            )
            for res_id, res in storage_reses.items()
        ]

        vnfc_res_infos = [
            objects.VnfcResourceInfoV2(
                id=res_id,
                vduId=res['resource_name'],
                computeResource=_res_to_handle(res),
                metadata=self._make_vnfc_metadata(res, heat_reses)
            )
            for res_id, res in server_reses.items()
        ]

        for vnfc_res_info in vnfc_res_infos:
            vdu_name = vnfc_res_info.vduId
            server_res = server_reses[vnfc_res_info.id]
            storage_ids = [storage_id
                for storage_id, storage_res in storage_reses.items()
                if (vdu_name in storage_res.get('required_by', []) and
                    server_res.get('parent_resource') ==
                    storage_res.get('parent_resource'))
            ]
            if storage_ids:
                vnfc_res_info.storageResourceIds = storage_ids

            vdu_cps = vnfd.get_vdu_cps(flavour_id, vdu_name)
            cp_infos = [
                objects.VnfcResourceInfoV2_VnfcCpInfo(
                    id=_make_combination_id(cp, vnfc_res_info.id),
                    cpdId=cp,
                    # vnfExtCpId or vnfLinkPortId may set later
                )
                for cp in vdu_cps
            ]
            if cp_infos:
                vnfc_res_info.vnfcCpInfo = cp_infos

        vnf_vl_res_infos = [
            objects.VnfVirtualLinkResourceInfoV2(
                id=res_id,
                vnfVirtualLinkDescId=res['resource_name'],
                networkResource=_res_to_handle(res)
            )
            for res_id, res in network_reses.items()
        ]

        ext_cp_infos = []
        if init:
            ext_vl_infos = self._make_ext_vl_info_from_req(
                req, grant, ext_cp_infos)
            ext_mgd_vl_infos = self._make_ext_mgd_vl_info_from_req(vnfd,
                flavour_id, req, grant)
        else:
            old_inst_vnf_info = inst.instantiatedVnfInfo
            ext_vl_infos = self._make_ext_vl_info_from_inst(
                old_inst_vnf_info, ext_cp_infos)
            ext_mgd_vl_infos = self._make_ext_mgd_vl_info_from_inst(
                old_inst_vnf_info)

        def _find_vl_name(port_res):
            cp_name = port_res['resource_name']
            return vnfd.get_vl_name_from_cp(flavour_id, vducp_nodes[cp_name])

        ext_port_infos = [
            objects.ExtLinkPortInfoV2(
                id=res_id,
                resourceHandle=_res_to_handle(res)
            )
            for res_id, res in port_reses.items()
            if _find_vl_name(res) is None
        ]

        self._link_ext_port_info(ext_port_infos, ext_vl_infos, ext_cp_infos,
            port_reses)

        vnf_port_infos = [
            objects.VnfLinkPortInfoV2(
                id=res_id,
                resourceHandle=_res_to_handle(res),
                cpInstanceType='EXT_CP'  # may be changed later
            )
            for res_id, res in port_reses.items()
            if _find_vl_name(res) is not None
        ]

        vl_name_to_info = {info.vnfVirtualLinkDescId: info
            for info in vnf_vl_res_infos + ext_mgd_vl_infos}

        for vnf_port_info in vnf_port_infos:
            port_res = port_reses[vnf_port_info.id]
            vl_info = vl_name_to_info.get(_find_vl_name(port_res))
            if vl_info is None:
                # should not occur. just check for consistency.
                continue

            if vl_info.obj_attr_is_set('vnfLinkPorts'):
                vl_info.vnfLinkPorts.append(vnf_port_info)
            else:
                vl_info.vnfLinkPorts = [vnf_port_info]

        self._link_vnfc_cp_info(vnfc_res_infos, ext_port_infos,
            vnf_port_infos, ext_cp_infos, server_reses, port_reses)

        # NOTE: The followings are not handled at the moment.
        # - handle tosca.nodes.nfv.VnfExtCp type
        #   Note that there is no example in current tacker examples which use
        #   tosca.nodes.nfv.VnfExtCp type and related BaseHOT definitions.
        # - in the case of specifying linkPortId of extVirtualLinks or
        #   extManagedVirtualLinks, the link of vnfcCpInfo is not handled
        #   because the association of compute resource and port resource
        #   is not identified.

        # make new instatiatedVnfInfo and replace
        inst_vnf_info = objects.VnfInstanceV2_InstantiatedVnfInfo(
            flavourId=flavour_id,
            vnfState='STARTED',
        )
        if storage_infos:
            inst_vnf_info.virtualStorageResourceInfo = storage_infos

        if vnfc_res_infos:
            # NOTE: scale-in specification of tacker SOL003 v2 API is that
            # newer VDU is selected for reduction. It is necessary to sort
            # vnfc_res_infos at this point so that the conductor should
            # choose VDUs from a head sequentially when making scale-in
            # grant request.

            def _get_key(vnfc):
                return parser.isoparse(vnfc.metadata['creation_time'])

            sorted_vnfc_res_infos = sorted(vnfc_res_infos, key=_get_key,
                                           reverse=True)
            inst_vnf_info.vnfcResourceInfo = sorted_vnfc_res_infos

        if vnf_vl_res_infos:
            inst_vnf_info.vnfVirtualLinkResourceInfo = vnf_vl_res_infos

        if ext_vl_infos:
            inst_vnf_info.extVirtualLinkInfo = ext_vl_infos

        if ext_mgd_vl_infos:
            inst_vnf_info.extManagedVirtualLinkInfo = ext_mgd_vl_infos

        if ext_cp_infos:
            inst_vnf_info.extCpInfo = ext_cp_infos

        # make vnfcInfo
        # NOTE: vnfcInfo only exists in SOL002
        if vnfc_res_infos:
            inst_vnf_info.vnfcInfo = [
                objects.VnfcInfoV2(
                    id=_make_combination_id(vnfc_res_info.vduId,
                                            vnfc_res_info.id),
                    vduId=vnfc_res_info.vduId,
                    vnfcResourceInfoId=vnfc_res_info.id,
                    vnfcState='STARTED'
                )
                for vnfc_res_info in sorted_vnfc_res_infos
            ]

        inst.instantiatedVnfInfo = inst_vnf_info
