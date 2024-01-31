# Copyright 2022 KDDI
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
import os

from oslo_config import cfg
from oslo_log import log as logging
from oslo_serialization import jsonutils
from oslo_utils import timeutils
from oslo_utils import uuidutils
from tacker._i18n import _
from tacker.common import exceptions
from tacker import context
from tacker.db import api as db_api
from tacker.db.db_sqlalchemy import api
from tacker.db.db_sqlalchemy import models
from tacker.db.nfvo import nfvo_db
from tacker.db.nfvo import nfvo_db_plugin
from tacker.db.vnfm import vnfm_db
from tacker import objects
from tacker.sol_refactored.common import vim_utils
from tacker.sol_refactored.common import vnf_instance_utils as inst_utils
from tacker.sol_refactored.infra_drivers.openstack import heat_utils
from tacker.sol_refactored import objects as objects_v2
from tacker.sol_refactored.objects.v2 import fields as v2fields
from tacker.vnfm import vim_client


CONF = cfg.CONF
LOG = logging.getLogger(__name__)


def env(*_vars, **kwargs):
    # Search for the first defined of possibly many env vars.
    # Returns the first environment variable defined in vars, or
    # returns the default defined in kwargs.
    for v in _vars:
        value = os.environ.get(v, None)
        if value:
            return value
    return kwargs.get('default', '')


DEFAULT_OPTS = [
    cfg.BoolOpt('use_credential_encryption', default=False,
                help=_("Enable to encrypt the credential"))
]

CONF.register_opts(DEFAULT_OPTS)

OPTS = [cfg.StrOpt('user_domain_id',
                   default=env("OS_USER_DOMAIN_ID", default='default'),
                   help='User Domain Id'),
        cfg.StrOpt('project_domain_id',
                   default=env("OS_DOMAIN_ID", default='default'),
                   help='Project Domain Id'),
        cfg.StrOpt('password',
                   default=env("OS_PASSWORD", default="default"),
                   help='User Password'),
        cfg.StrOpt('username',
                   default=env("OS_USERNAME", default="default"),
                   help='User Name'),
        cfg.StrOpt('user_domain_name',
                   default=env("OS_USER_DOMAIN_NAME", default='Default'),
                   help='Use Domain Name'),
        cfg.StrOpt('project_name',
                   default=env("OS_PROJECT_NAME", default='default'),
                   help='Project Name'),
        cfg.StrOpt('project_domain_name',
                   default=env("OS_PROJECT_DOMAIN_NAME", default='Default'),
                   help='Project Domain Name'),
        cfg.StrOpt('auth_url',
                   default=env("OS_AUTH_URL",
                               default='http://localhost/identity/v3'),
                   help='Keystone endpoint')]

CONF.register_opts(OPTS, 'keystone_authtoken')


def option_error_check(all_flag, api_ver, keep_orig, mark_delete, vnf_id):
    if all_flag:
        if api_ver or mark_delete or vnf_id:
            msg = _("--all cannot be used with --api-ver, "
                    "--mark-delete or --vnf-id")
            raise exceptions.InvalidInput(error_message=msg)
    else:
        if not vnf_id:
            msg = _("either --all or --vnf-id must be used")
            raise exceptions.InvalidInput(error_message=msg)

    if api_ver:
        if not mark_delete:
            msg = _("--api-ver must be used with --mark-delete")
            raise exceptions.InvalidInput(error_message=msg)
        if api_ver not in {"v1", "v2"}:
            msg = _("v1 or v2 must be specified for --api-ver")
            raise exceptions.InvalidInput(error_message=msg)

    if mark_delete:
        if not api_ver:
            msg = _("--mark-delete must be used with --api-ver")
            raise exceptions.InvalidInput(error_message=msg)
        if keep_orig:
            msg = _("--mark-delete cannot be used with --keep-orig")
            raise exceptions.InvalidInput(error_message=msg)


def migrate_to_v2_tables(tacker_config, all_flag, api_ver,
                         keep_orig, mark_delete, vnf_id):
    option_error_check(all_flag, api_ver, keep_orig, mark_delete, vnf_id)
    admin_context = context.get_admin_context()
    objects.register_all()
    objects_v2.register_all()

    CONF.database = tacker_config.database

    if mark_delete:
        if api_ver == "v1":
            mark_delete_v1(admin_context, vnf_id)
        elif api_ver == "v2":
            mark_delete_v2(admin_context, vnf_id)
        return

    vnf_ids = [vnf_id]
    if all_flag:
        vnf_ids = get_all_vnfs(admin_context)
    for vnf_instance_id in vnf_ids:
        create_vnf_instance_v2(admin_context, vnf_instance_id)
        create_vnf_lcm_op_occs_v2(admin_context, vnf_instance_id)
        if not keep_orig:
            mark_delete_v1(admin_context, vnf_instance_id)


@db_api.context_manager.writer
def mark_delete_v1(context, vnf_id):
    objects.vnf_instance._destroy_vnf_instance(context, vnf_id)
    vnf_inst = \
        objects.vnf_instance._vnf_instance_get_by_id(
            context, vnf_id, columns_to_join=["instantiated_vnf_info"],
            read_deleted="yes")

    now = timeutils.utcnow()
    updated_values = {
        'deleted_at': now,
        'status': 'PENDING_DELETE'}
    api.model_query(context, vnfm_db.VNFAttribute)\
        .filter_by(vnf_id=vnf_id).delete()
    vnf_attrs = api.model_query(context, vnfm_db.VNFAttribute)\
        .filter_by(vnf_id=vnf_id).all()
    api.model_query(context, vnfm_db.VNF)\
        .filter_by(id=vnf_id).update(updated_values)
    vnf = api.model_query(context, vnfm_db.VNF)\
        .filter_by(id=vnf_id).first()

    now = timeutils.utcnow()
    updated_values = {
        'deleted': True,
        'deleted_at': now}
    _vnf_lcm_op_occs = api.model_query(context, models.VnfLcmOpOccs)\
        .filter_by(vnf_instance_id=vnf_id)
    for occ in _vnf_lcm_op_occs:
        api.model_query(context, models.VnfLcmOpOccs)\
            .filter_by(id=occ.id).first().update(updated_values)
    vnf_lcm_op_occs = api.model_query(context, models.VnfLcmOpOccs)\
        .filter_by(vnf_instance_id=vnf_id)

    return vnf_inst, vnf_attrs, vnf, vnf_lcm_op_occs


@db_api.context_manager.writer
def mark_delete_v2(context, vnf_id):
    # Target object tables are VnfInstanceV2, VnfLcmOpOccV2
    vnf_inst_v2 = objects_v2.VnfInstanceV2.get_by_id(context, vnf_id)
    vnf_inst_v2.delete(context)

    op_occs_v2 = objects_v2.VnfLcmOpOccV2.get_by_filter(context,
        vnfInstanceId=vnf_id)
    for op_occ in op_occs_v2:
        op_occ.delete(context)


def get_all_vnfs(context):
    vnfs = objects.vnf_instance._vnf_instance_list(context,
                                                   columns_to_join=None)
    vnf_ids = []
    for vnf in vnfs:
        vnf_ids.append(vnf.id)

    return vnf_ids


def _to_vnf_instance_v2_instantiated_vnf_info(inst_info, vnf, op_occs,
                                              vim_connection_info=None):
    if not inst_info:
        return None
    fields = {
        "flavourId": inst_info.flavour_id,
        "vnfState": inst_info.vnf_state,
        "scaleStatus": _to_scale_status_v2(inst_info.scale_status),
        "maxScaleLevels": _to_max_scale_levels(vnf.attributes),
        "extCpInfo": _to_ext_cp_info_v2(inst_info.ext_cp_info),
        "extVirtualLinkInfo":
            _to_ext_virtual_link_info_v2(
                inst_info.ext_virtual_link_info,
                inst_info.vnf_virtual_link_resource_info, op_occs,
                vim_connection_info),
        "extManagedVirtualLinkInfo":
            _to_ext_managed_virtual_link_info_v2(
                inst_info.ext_managed_virtual_link_info,
                vim_connection_info),
        "monitoringParameters": _to_monitoring_parameters(vnf.attributes),
        "localizationLanguage": _to_localization_language(vnf.attributes),
        "vnfcResourceInfo":
            _to_vnfc_resource_info_v2(
                inst_info.vnfc_resource_info,
                inst_info.ext_virtual_link_info,
                inst_info.vnf_virtual_link_resource_info,
                vim_connection_info),
        "vnfVirtualLinkResourceInfo":
            _to_vnf_virtual_link_resource_info_v2(
                inst_info.vnf_virtual_link_resource_info,
                inst_info.ext_virtual_link_info,
                inst_info.ext_managed_virtual_link_info,
                vim_connection_info),
        "virtualStorageResourceInfo":
            _to_virtual_storage_resource_info_v2(
                inst_info.virtual_storage_resource_info,
                vim_connection_info),
        "vnfcInfo": _to_vnfc_info_v2(inst_info.vnfc_resource_info)}
    return objects_v2.VnfInstanceV2_InstantiatedVnfInfo(**fields)


def _to_vim_connection_info(vim_con_infos, vim_infos):
    # NOTE: The key of VimConnectionInfo doesn't exist in v1.
    # Therefore any value can be set to the key.
    # The values like vim_0, vim_1.. are set here.
    dict_info = {}
    for i, info in enumerate(vim_con_infos):
        _info = info.get("tacker_object.data")
        try:
            vim_auth = vim_client.VimClient()._build_vim_auth(vim_infos[i])
            vim_info = {
                'vim_auth': vim_auth,
                'vim_id': vim_infos[i]['id'],
                'vim_name': vim_infos[i].get('name', vim_infos[i]['id']),
                'vim_type': vim_infos[i]['type'],
                'tenant': vim_infos[i]['tenant_id'],
                'placement_attr': vim_infos[i].get('placement_attr', {}),
                'extra': vim_infos[i].get('extra', {})}
            vim_info_obj = vim_utils.vim_to_conn_info(vim_info)
        except Exception as ex:
            LOG.debug('Fail to get vim info %s', ex)
            fields = {
                "vimId": _info.get("vim_id"),
                "vimType": _info.get("vim_type"),
                "interfaceInfo": _info.get("interface_info"),
                "accessInfo": _info.get("access_info"),
                "extra": _info.get("extra")}
            vim_info_obj = objects_v2.VimConnectionInfo(**fields)
        dict_info["vim_{}".format(i)] = vim_info_obj
    return dict_info


def _to_scale_status_v2(scale_status_list):
    scale_status_v2_list = []
    for scale_status in scale_status_list:
        _scale_status = scale_status["tacker_object.data"]
        fields = {
            "aspectId": _scale_status.get("aspect_id"),
            "scaleLevel": _scale_status.get("scale_level")}
        scale_status_v2_list.append(objects_v2.ScaleInfoV2(**fields))
    return scale_status_v2_list


def _to_max_scale_levels(vnf_attributes):
    # NOTE: maxScaleLevels is not defined in SOL003 v2.6.1.
    # Related information can be got from vnf_attributes table.
    scale_infos_v2 = []
    for attr in vnf_attributes:
        if attr.key == 'scale_group':
            val = ast.literal_eval(attr.value)
            if val.get("scaleGroupDict"):
                for aspect_id, scale_info in val.get("scaleGroupDict").items():
                    fields = {
                        "aspectId": aspect_id,
                        "scaleLevel": scale_info.get("maxLevel")}
                    scale_infos_v2.append(objects_v2.ScaleInfoV2(**fields))
    return scale_infos_v2


def _to_ext_cp_info_v2(ext_cp_infos):
    ext_cp_infos_v2 = []
    for ext_cp_info in ext_cp_infos:
        _ext_cp_info = ext_cp_info["tacker_object.data"]
        # NOTE: Since cpConfigId is not defined in SOL003 v2.6.1,
        # there are no related information in v1 tables.
        # Therefore any value can be set to cpConfigId.
        # The value of <cpd_id>_0 is set here.
        fields = {
            "id": _ext_cp_info.get("id"),
            "cpdId": _ext_cp_info.get("cpd_id"),
            "cpConfigId": _ext_cp_info.get("cpd_id") + "_0",
            "cpProtocolInfo":
                _to_cp_protocol_info_v2(_ext_cp_info.get("cp_protocol_info")),
            "extLinkPortId": _ext_cp_info.get("ext_link_port_id"),
            "associatedVnfcCpId": _ext_cp_info.get("associated_vnfc_cp_id")}
        ext_cp_infos_v2.append(objects_v2.VnfExtCpInfoV2(**fields))
    return ext_cp_infos_v2


def _to_cp_protocol_info_v2(cp_protocol_infos):
    cp_protocol_infos_v2 = []
    for cp_protocol_info in cp_protocol_infos:
        _cp_protocol_info = cp_protocol_info.get("tacker_object.data")
        _ip_over_ethernet = _cp_protocol_info.get("ip_over_ethernet")
        fields = {"layerProtocol": _cp_protocol_info.get("layer_protocol")}
        if _ip_over_ethernet:
            fields.update({"ipOverEthernet":
                _to_ip_over_ethernet_address_info_v2(
                    _ip_over_ethernet.get("tacker_object.data"))})
        cp_protocol_infos_v2.append(objects_v2.CpProtocolInfoV2(**fields))
    return cp_protocol_infos_v2


def _to_ip_over_ethernet_address_info_v2(ip_over_ethernet):
    fields = {
        "macAddress": ip_over_ethernet.get("mac_address"),
        "ipAddresses":
            _to_ip_over_ethernet_address_info_v2_ip_addresses(
                ip_over_ethernet.get("ip_addresses"))}
    return objects_v2.IpOverEthernetAddressInfoV2(**fields)


def _to_ip_over_ethernet_address_info_v2_ip_addresses(ip_addresses):
    ip_over_eth_add_info_v2_ip_addresses = []
    for ip_address in ip_addresses:
        _ip_address = ip_address.get("tacker_object.data")
        fields = {
            "type": _ip_address.get("type"),
            "addresses": _ip_address.get("addresses"),
            "isDynamic": _ip_address.get("is_dynamic"),
            "subnetId": _ip_address.get("subnet_id")}
        ip_over_eth_add_info_v2_ip_addresses.append(
            objects_v2.IpOverEthernetAddressInfoV2_IpAddresses(**fields))
    return ip_over_eth_add_info_v2_ip_addresses


def _to_ext_virtual_link_info_v2(ext_vls, vnf_vl_rscs, op_occs,
                                 vim_connection_info=None):
    ext_vls_v2 = []
    for ext_vl in ext_vls:
        _ext_vl = ext_vl.get("tacker_object.data")
        resource_handle_data = \
            _ext_vl.get("resource_handle").get("tacker_object.data")
        fields = {
            "id": _ext_vl.get("id"),
            "resourceHandle": _to_resource_handle(
                resource_handle_data, vim_connection_info),
            "extLinkPorts":
                _to_ext_link_port_info_v2(
                    _ext_vl.get("id"), vnf_vl_rscs, vim_connection_info),
            "currentVnfExtCpData":
                _to_current_vnf_ext_cp_data(_ext_vl.get("id"), op_occs)}
        ext_vls_v2.append(objects_v2.ExtVirtualLinkInfoV2(**fields))
    return ext_vls_v2


def _to_resource_handle(resource_handle_data, vim_connection_info=None):
    fields = {
        'vimConnectionId': _get_vim_key_by_id(
            resource_handle_data.get("vim_connection_id"),
            vim_connection_info),
        'resourceProviderId': resource_handle_data.get("resource_provider_id"),
        'resourceId': resource_handle_data.get("resource_id"),
        'vimLevelResourceType':
            resource_handle_data.get("vim_level_resource_type")}
    resource_handle = objects_v2.ResourceHandle(**fields)
    return resource_handle


def _to_ext_link_port_info_v2(ext_vl_id, vnf_vl_res_infos,
                              vim_connection_info=None):
    ext_link_port_infos_v2 = []
    for vnf_vl_res_info in vnf_vl_res_infos:
        _vnf_vl_res_info = vnf_vl_res_info.get("tacker_object.data")
        if _vnf_vl_res_info.get("vnf_virtual_link_desc_id") == ext_vl_id:
            vnf_link_ports = _vnf_vl_res_info.get("vnf_link_ports")
            for link_port in vnf_link_ports:
                _link_port = link_port.get("tacker_object.data")
                resource_handle_data = \
                    _link_port.get("resource_handle").get("tacker_object.data")
                fields = {
                    "id": _link_port.get("id"),
                    "resourceHandle":
                        _to_resource_handle(
                            resource_handle_data, vim_connection_info),
                    "cpInstanceId": _link_port.get("cp_instance_id")}
                ext_link_port_infos_v2.append(
                    objects_v2.ExtLinkPortInfoV2(**fields))
    return ext_link_port_infos_v2


def _to_current_vnf_ext_cp_data(ext_vl_id, vnf_op_occs):
    # NOTE: Since CurrentVnfExtCpData is not defined in SOL003 v2.6.1,
    # this field can't be passed from v1 api objects.
    # The data type of CurrentVnfExtCpData is defined as
    # VnfExtCpData in SOL003 v3.3.1,
    # and the data is passed from InstantiateVnfRequest
    # or ChangeExtVnfConnectivityRequest.
    # Therefore this field is created from VnfLcmOpOccs objects
    # whose operation is INSTANTIATE or CHANGE_EXT_CONN.
    current_vnf_ext_cp_data = []
    ext_cps = {}
    _vnf_op_occs = \
        vnf_op_occs.filter(models.VnfLcmOpOccs.operation_state == "COMPLETED",
                           models.VnfLcmOpOccs.operation.in_(["INSTANTIATE",
                               "CHANGE_EXT_CONN"])).order_by(
            models.VnfLcmOpOccs.start_time).all()
    for op_occ in _vnf_op_occs:
        operation_param = ast.literal_eval(op_occ.operation_params)
        ext_vls = operation_param.get("extVirtualLinks")
        for ext_vl in ext_vls:
            if ext_vl.get("id") == ext_vl_id:
                for ext_cp in ext_vl.get("extCps"):
                    cpd_id = ext_cp.get("cpdId")
                    ext_cps.update({
                        cpd_id: ext_cp.get("cpConfig")})
    for cpd_id, cp_config in ext_cps.items():
        fields = {
            "cpdId": cpd_id,
            "cpConfig": {
                "{}_0".format(cpd_id): _to_vnf_ext_cp_config(cp_config[0])}}
        current_vnf_ext_cp_data.append(objects_v2.VnfExtCpData(**fields))
    return current_vnf_ext_cp_data


def _to_vnf_ext_cp_config(cp_config):
    fields = {
        "linkPortId": cp_config.get("linkPortId"),
        "cpProtocolData":
            _to_cp_protocol_data(cp_config.get("cpProtocolData", []))}
    return objects_v2.VnfExtCpConfig(**fields)


def _to_cp_protocol_data(cp_protocol_data_list):
    _cp_protocol_data_list = []
    for cp_protocol_data in cp_protocol_data_list:
        fields = {
            "layerProtocol": cp_protocol_data.get("layerProtocol"),
            "ipOverEthernet":
                _to_ip_over_ethernet_address_data(
                    cp_protocol_data.get("ipOverEthernet"))}
        _cp_protocol_data_list.append(objects_v2.CpProtocolData(**fields))
    return _cp_protocol_data_list


def _to_ip_over_ethernet_address_data(ip_over_ethernet):
    fields = {
        "macAddress": ip_over_ethernet.get("macAddress"),
        "ipAddresses":
            _to_ip_over_ethernet_address_data_ip_addresses(
                ip_over_ethernet.get("ipAddresses", []))}
    return objects_v2.IpOverEthernetAddressData(**fields)


def _to_ip_over_ethernet_address_data_ip_addresses(ip_addresses):
    ip_over_eth_add_data_ip_addresses = []
    for ip_address in ip_addresses:
        fields = {
            "type": ip_address.get("type"),
            "fixedAddresses": ip_address.get("fixedAddresses"),
            "numDynamicAddresses": ip_address.get("numDynamicAddresses"),
            "addressRange":
                _to_ip_over_eth_address_data_ip_addresses_address_range(
                    ip_address.get("addressRange")),
            "subnetId": ip_address.get("subnetId")}
        ip_over_eth_add_data_ip_addresses.append(
            objects_v2.IpOverEthernetAddressData_IpAddresses(**fields))
    return ip_over_eth_add_data_ip_addresses


def _to_ip_over_eth_address_data_ip_addresses_address_range(address_range):
    if not address_range:
        return None
    fields = {
        "minAddress": address_range.get("minAddress"),
        "maxAddress": address_range.get("maxAddress")}
    return objects_v2.\
        IpOverEthernetAddressData_IpAddresses_AddressRange(**fields)


def _to_ext_managed_virtual_link_info_v2(ext_mng_vl_infos,
                                         vim_connection_info=None):
    ext_mng_vl_infos_v2 = []
    for ext_mng_vl_info in ext_mng_vl_infos:
        _ext_mng_vl_info = ext_mng_vl_info.get("tacker_object.data")
        resource_handle_data = \
            _ext_mng_vl_info.get("network_resource").get("tacker_object.data")
        fields = {
            "id": _ext_mng_vl_info.get("id"),
            "vnfVirtualLinkDescId":
                _ext_mng_vl_info.get("vnf_virtual_link_desc_id"),
            "networkResource": _to_resource_handle(
                resource_handle_data, vim_connection_info),
            "vnfLinkPorts": _to_vnf_link_port_info_v2(
                _ext_mng_vl_info.get("vnf_link_ports", []),
                vim_connection_info)}
        ext_mng_vl_infos_v2.append(
            objects_v2.ExtManagedVirtualLinkInfoV2(**fields))
    return ext_mng_vl_infos_v2


def _to_vnf_link_port_info_v2(vnf_link_ports, vim_connection_info=None):
    vnf_link_port_infos_v2 = []
    for vnf_link_port in vnf_link_ports:
        _vnf_link_port = vnf_link_port.get("tacker_object.data")
        resource_handle_data = \
            _vnf_link_port.get("resource_handle").get("tacker_object.data")
        # NOTE: cpInstanceType is not defined in the v1 vnfLinkPortInfo.
        # The value is temporarily set as "EXT_CP" here
        # and updated later if needed,
        # because vnfcResourceInfoV2 object is needed to determine
        # the value of cpInstanceId but the object doesn't exist at the moment.
        fields = {
            "id": _vnf_link_port.get("id"),
            "resourceHandle": _to_resource_handle(
                resource_handle_data, vim_connection_info),
            "cpInstanceId": _vnf_link_port.get("cp_instance_id"),
            "cpInstanceType": "EXT_CP"}
        vnf_link_port_infos_v2.append(objects_v2.VnfLinkPortInfoV2(**fields))
    return vnf_link_port_infos_v2


def _to_vnfc_resource_info_v2(vnfc_rsc_infos, ext_vl_infos, vnf_vl_res_infos,
                              vim_connection_info=None):
    vnfc_rsc_infos_v2 = []
    for vnfc_rsc_info in vnfc_rsc_infos:
        _vnfc_rsc_info = vnfc_rsc_info.get("tacker_object.data")
        resource_handle_data = \
            _vnfc_rsc_info.get("compute_resource").get("tacker_object.data")
        fields = {
            "id": _vnfc_rsc_info.get("id"),
            "vduId": _vnfc_rsc_info.get("vdu_id"),
            "computeResource": _to_resource_handle(
                resource_handle_data, vim_connection_info),
            "storageResourceIds":
                _vnfc_rsc_info.get("storage_resource_ids"),
            "vnfcCpInfo":
                _to_vnfc_resource_info_v2_vnfc_cp_info(
                    _vnfc_rsc_info.get("vnfc_cp_info", []),
                    ext_vl_infos, vnf_vl_res_infos),
            "metadata": _vnfc_rsc_info.get("metadata")}
        vnfc_rsc_infos_v2.append(objects_v2.VnfcResourceInfoV2(**fields))
    return vnfc_rsc_infos_v2


def _to_vnfc_resource_info_v2_vnfc_cp_info(vnfc_cp_infos,
                                           ext_vl_infos, vnf_vl_res_infos):
    # NOTE:In v1 api, the field of vnfLinkPortId is set
    # even if cps are connected to external networks.
    # Therefore vnfLinkPortId in v1 is migrated to vnfExtCpId in v2
    # when cp is exposed, or migrated to vnfLinkPortId in v2 otherwise.
    vnfc_rsc_info_v2_vnfc_cp_infos = []
    for vnfc_cp_info in vnfc_cp_infos:
        _vnfc_cp_info = vnfc_cp_info.get("tacker_object.data")
        fields = {
            "id": _vnfc_cp_info.get("id"),
            "cpdId": _vnfc_cp_info.get("cpd_id")}
        vnfc_rsc_info_v2_vnfc_cp_info = \
            objects_v2.VnfcResourceInfoV2_VnfcCpInfo(**fields)
        ext_vl_ids = \
            [ext_vl_info.get("tacker_object.data").get("id")
                for ext_vl_info in ext_vl_infos]
        ext_vl_res_infos = \
            [vnf_vl_res_info.get("tacker_object.data") for vnf_vl_res_info in
                vnf_vl_res_infos if vnf_vl_res_info.get("tacker_object.data").
                get("vnf_virtual_link_desc_id") in ext_vl_ids]
        for ext_vl_res_info in ext_vl_res_infos:
            for vnf_link_port in ext_vl_res_info.get("vnf_link_ports"):
                _vnf_link_port = vnf_link_port.get("tacker_object.data")
                if _vnf_link_port.get("id") == \
                        _vnfc_cp_info.get("vnf_link_port_id"):
                    vnfc_rsc_info_v2_vnfc_cp_info.vnfExtCpId = \
                        _vnfc_cp_info.get("vnf_link_port_id")
                    vnfc_rsc_info_v2_vnfc_cp_info.vnfLinkPortId = None
        if not vnfc_rsc_info_v2_vnfc_cp_info.obj_attr_is_set("vnfExtCpId"):
            vnfc_rsc_info_v2_vnfc_cp_info.vnfExtCpId = None
            vnfc_rsc_info_v2_vnfc_cp_info.vnfLinkPortId = \
                _vnfc_cp_info.get("vnf_link_port_id")
        vnfc_rsc_info_v2_vnfc_cp_infos.append(vnfc_rsc_info_v2_vnfc_cp_info)
    return vnfc_rsc_info_v2_vnfc_cp_infos


def _to_monitoring_parameters(vnf_attributes):
    # NOTE: monitoringParameters is not defined in the v1 InstantiatedVnfInfo.
    # Related information can be got from vnf_attributes table.
    monitor_params_v2 = []
    for attr in vnf_attributes:
        if attr.key == 'param_values':
            val = ast.literal_eval(attr.value)
            params = val.get("monitoring_parameters")
            if params:
                for param in params:
                    fields = {
                        "id": param.get("id", uuidutils.generate_uuid()),
                        "vnfdId": param.get("vnfd_id"),
                        "name": param.get("name"),
                        "performanceMetric": param.get("performance_metric")}
                    monitor_params_v2.append(
                        objects_v2.MonitoringParameterV2(**fields))
    return monitor_params_v2


def _to_localization_language(vnf_attributes):
    # NOTE: localizationLanguages not defined in the v1 InstantiatedVnfInfo.
    # Related information can be got from vnf_attributes table.
    for attr in vnf_attributes:
        if attr.key == 'param_values':
            val = ast.literal_eval(attr.value)
            if val.get("localization_languages"):
                return val.get("localization_languages")[0]
    return None


def _to_vnf_virtual_link_resource_info_v2(vl_rsc_infos,
                                          ext_vl_infos, ext_managed_vl_infos,
                                          vim_connection_info=None):
    vl_rsc_infos_v2 = []
    ext_vl_ids = [ext_vl_info.get("tacker_object.data").get("id") for
            ext_vl_info in ext_vl_infos]
    ext_managed_vl_desc_ids = \
        [ext_managed_vl_info.get(
            "tacker_object.data").get("vnf_virtual_link_desc_id") for
            ext_managed_vl_info in ext_managed_vl_infos]
    for vl_rsc_info in vl_rsc_infos:
        _vl_rsc_info = vl_rsc_info.get("tacker_object.data")
        resource_handle_data = \
            _vl_rsc_info.get("network_resource").get("tacker_object.data")
        vl_desc_id = _vl_rsc_info.get("vnf_virtual_link_desc_id")
        if vl_desc_id not in ext_vl_ids + ext_managed_vl_desc_ids:
            fields = {
                "id": _vl_rsc_info.get("id"),
                "vnfVirtualLinkDescId": vl_desc_id,
                "networkResource": _to_resource_handle(
                    resource_handle_data, vim_connection_info),
                "vnfLinkPorts": _to_vnf_link_port_info_v2(
                    _vl_rsc_info.get("vnf_link_ports"), vim_connection_info)}
            vl_rsc_infos_v2.append(
                objects_v2.VnfVirtualLinkResourceInfoV2(**fields))
    return vl_rsc_infos_v2


def _to_virtual_storage_resource_info_v2(vstorage_infos,
                                         vim_connection_info=None):
    vstorage_infos_v2 = []
    for vstorage_info in vstorage_infos:
        _vstorage_info = vstorage_info.get("tacker_object.data")
        resource_handle_data = \
            _vstorage_info.get("storage_resource").get("tacker_object.data")
        fields = {
            "id": _vstorage_info.get("id"),
            "virtualStorageDescId":
                _vstorage_info.get("virtual_storage_desc_id"),
            "storageResource": _to_resource_handle(
                resource_handle_data, vim_connection_info)}
        vstorage_infos_v2.append(
            objects_v2.VirtualStorageResourceInfoV2(**fields))
    return vstorage_infos_v2


def _to_vnf_configurable_properties(vnf_attributes):
    # NOTE: configurableProperties is not defined in the v1 vnfInstance.
    # Related information can be got from vnf_attributes table.
    for attr in vnf_attributes:
        if attr.key == 'param_values':
            val = ast.literal_eval(attr.value)
            if val.get("configurable_properties"):
                return val.get("configurable_properties")
    return None


def _to_vnfc_info_v2(vnfc_res_infos):
    vnfc_infos_v2 = []
    for vnfc_res_info in vnfc_res_infos:
        _vnfc_res_info = vnfc_res_info.get("tacker_object.data")
        fields = {
            "id": f'{_vnfc_res_info.get("vdu_id")}-{_vnfc_res_info.get("id")}',
            "vduId": _vnfc_res_info.get("vdu_id"),
            "vnfcResourceInfoId": _vnfc_res_info.get("id"),
            "vnfcState": "STARTED"}
        vnfc_infos_v2.append(objects_v2.VnfcInfoV2(**fields))
    return vnfc_infos_v2


def _set_cp_instance_type(instance_v2):
    # NOTE: If target cp is connected to extManagedVirtualLinkInfo
    # or vnfVirtualLinkResourceInfo, its cpInstanceType is set as "VNFC_CP".
    for vl_type in ["extManagedVirtualLinkInfo", "vnfVirtualLinkResourceInfo"]:
        for vl_info in instance_v2.instantiatedVnfInfo.get(vl_type, []):
            for vnf_link_port in vl_info.vnfLinkPorts:
                port_id = vnf_link_port.id
                vnfc_resource_infos = \
                    instance_v2.instantiatedVnfInfo.get("vnfcResourceInfo", [])
                for vnfc_resource_info in vnfc_resource_infos:
                    for vnfc_cp_info in vnfc_resource_info.get("vnfcCpInfo"):
                        if vnfc_cp_info.vnfLinkPortId == port_id:
                            vnf_link_port.cpInstanceType = "VNFC_CP"


def _get_vim(context, vim_con_info):
    vim_id = vim_con_info.get("tacker_object.data").get("vim_id")
    return api.model_query(context, nfvo_db.Vim).filter_by(id=vim_id).first()


def _set_stack_id(inst_v2, vnf):
    heat_client = heat_utils.HeatClient(inst_v2.vimConnectionInfo["vim_0"])
    stack_names = []
    stack_names.append(f"vnflcm_{inst_v2.id}")
    stack_names.append(f"{inst_v2.vnfInstanceName}_{inst_v2.id}")
    failure_count = \
        [attr.get("value") for attr in
         vnf.attributes if attr.get("key") == "failure_count"]
    if failure_count != []:
        stack_names[1] += f"-RESPAWN-{failure_count[0]}"
    for stack_name in stack_names:
        try:
            heat_reses = heat_client.get_resources(stack_name)
        except Exception as e:
            LOG.debug('heat resources not found %s', e)
    for vnfc_res_info in inst_v2.instantiatedVnfInfo.vnfcResourceInfo:
        for res in heat_reses:
            if res["physical_resource_id"] == \
               vnfc_res_info.computeResource.resourceId:
                stack_id = heat_utils.get_resource_stack_id(res)
                vnfc_res_info.metadata = {"stack_id": stack_id}


@db_api.context_manager.writer
def create_vnf_instance_v2(context, vnf_id):
    _vnf_instance = objects.vnf_instance._vnf_instance_get_by_id(
        context, vnf_id, columns_to_join=None, read_deleted="no")
    _vnf_info = _vnf_instance.instantiated_vnf_info
    _vnf = api.model_query(
        context, vnfm_db.VNF).filter_by(id=_vnf_instance.id).first()
    _vnf_op_occs = \
        api.model_query(context, models.VnfLcmOpOccs, read_deleted="no",
                        project_only=True).filter(models.VnfLcmOpOccs.
                        vnf_instance_id == _vnf_instance.id)
    _vims = [_get_vim(context, vim_con_info) for
        vim_con_info in _vnf_instance.vim_connection_info]
    nfvo = nfvo_db_plugin.NfvoPluginDb()
    _vim_infos = \
        [nfvo.get_vim(context, vim.id, mask_password=False) for vim in _vims]
    vim_connection_info = _to_vim_connection_info(
        _vnf_instance.vim_connection_info, _vim_infos)

    inst_v2 = objects_v2.VnfInstanceV2(
        id=_vnf_instance.id,
        vnfInstanceName=_vnf_instance.vnf_instance_name,
        vnfInstanceDescription=_vnf_instance.vnf_instance_description,
        vnfdId=_vnf_instance.vnfd_id,
        vnfProvider=_vnf_instance.vnf_provider,
        vnfProductName=_vnf_instance.vnf_product_name,
        vnfSoftwareVersion=_vnf_instance.vnf_software_version,
        vnfdVersion=_vnf_instance.vnfd_version,
        vnfConfigurableProperties=_to_vnf_configurable_properties(
            _vnf.attributes),
        vimConnectionInfo=vim_connection_info,
        instantiationState=_vnf_instance.instantiation_state,
        instantiatedVnfInfo=_to_vnf_instance_v2_instantiated_vnf_info(
            _vnf_info, _vnf, _vnf_op_occs, vim_connection_info),
        metadata=_vnf_instance.vnf_metadata,)
    if inst_v2.instantiatedVnfInfo:
        _set_cp_instance_type(inst_v2)
    if inst_v2.vimConnectionInfo["vim_0"].accessInfo.get("project"):
        _set_stack_id(inst_v2, _vnf)
    inst_v2.create(context)
    return inst_v2


def _create_operation_params_v2(dict_operation_params_v1, operation):
    fields = dict_operation_params_v1

    # convert list -> dict
    if "vimConnectionInfo" in fields.keys():
        fields["vimConnectionInfo"] = \
            {"vim_{}".format(index): vimConnectionInfo
             for index, vimConnectionInfo
             in enumerate(fields["vimConnectionInfo"])}

    # convert list -> dict
    if "extVirtualLinks" in fields.keys():
        for extVirtualLink in fields["extVirtualLinks"]:
            for extCp in extVirtualLink["extCps"]:
                extCp["cpConfig"] = \
                    {"{}_{}".format(extCp["cpdId"], index): cpConfig_item
                        for index, cpConfig_item
                        in enumerate(extCp["cpConfig"])}

    if operation == v2fields.LcmOperationType.INSTANTIATE:
        cls = objects_v2.InstantiateVnfRequest
    elif operation == v2fields.LcmOperationType.SCALE:
        cls = objects_v2.ScaleVnfRequest
    elif operation == v2fields.LcmOperationType.SCALE_TO_LEVEL:
        cls = objects_v2.ScaleVnfToLevelRequest
    elif operation == v2fields.LcmOperationType.CHANGE_FLAVOUR:
        cls = objects_v2.ChangeVnfFlavourRequest
    elif operation == v2fields.LcmOperationType.OPERATE:
        cls = objects_v2.OperateVnfRequest
    elif operation == v2fields.LcmOperationType.HEAL:
        cls = objects_v2.HealVnfRequest
    elif operation == v2fields.LcmOperationType.CHANGE_EXT_CONN:
        cls = objects_v2.ChangeExtVnfConnectivityRequest
    elif operation == v2fields.LcmOperationType.TERMINATE:
        cls = objects_v2.TerminateVnfRequest
    elif operation == v2fields.LcmOperationType.MODIFY_INFO:
        cls = objects_v2.VnfInfoModificationRequest
    elif operation == v2fields.LcmOperationType.CREATE_SNAPSHOT:
        cls = objects_v2.CreateVnfSnapshotRequest
    elif operation == v2fields.LcmOperationType.REVERT_TO_SNAPSHOT:
        cls = objects_v2.RevertToVnfSnapshotRequest
    elif operation == v2fields.LcmOperationType.CHANGE_VNFPKG:
        cls = objects_v2.ChangeCurrentVnfPkgRequest

    return cls.from_dict(fields)


def _create_resource_changes_v2(dict_resource_changes,
                                vim_connection_info=None):
    resource_changes = dict_resource_changes

    # create affected_vnfcs_v2 list
    affected_vnfcs_v2 = []
    for affected_vnfc in resource_changes["affected_vnfcs"]:
        compute_res = affected_vnfc["compute_resource"]
        compute_res["vim_connection_id"] = _get_vim_key_by_id(
            compute_res["vim_connection_id"], vim_connection_info)
        fields = {
            "id": affected_vnfc["id"],
            'vduId': affected_vnfc["vdu_id"],
            'changeType': affected_vnfc["change_type"],
            'affectedVnfcCpIds': affected_vnfc["affected_vnfc_cp_ids"],
            'addedStorageResourceIds':
                affected_vnfc["added_storage_resource_ids"],
            'removedStorageResourceIds':
                affected_vnfc["removed_storage_resource_ids"],
            # v1 -> v2
            'computeResource':
                _to_resource_handle(affected_vnfc["compute_resource"]),
            'vnfdId': None,
            'resourceDefinitionId': None,
            'zoneId': None,
            'metadata': None,
        }
        affected_vnfcs_v2.append(objects_v2.AffectedVnfcV2(**fields))

    # create affected_virtual_links_v2 list
    affected_vls_v2 = []
    for affected_vl in resource_changes["affected_virtual_links"]:
        network_res = affected_vl["network_resource"]
        network_res["vim_connection_id"] = _get_vim_key_by_id(
            network_res["vim_connection_id"], vim_connection_info)
        fields = {
            'id': affected_vl["id"],
            'vnfVirtualLinkDescId':
                affected_vl["vnf_virtual_link_desc_id"],
            'changeType': affected_vl["change_type"],
            # v1 -> v2
            'vnfdId': None,
            'networkResource':
                _to_resource_handle(affected_vl["network_resource"]),
            'vnfLinkPortIds': None,
            'resourceDefinitionId': None,
            'zoneId': None,
            'metadata': None
        }
        affected_vls_v2.append(objects_v2.AffectedVirtualLinkV2(**fields))

    # create affected_virtual_storages_v2 list
    affected_vstorages_v2 = []
    for affected_vstorage \
            in resource_changes.get("affected_virtual_storages", []):
        storage_res = affected_vstorage["storage_resource"]
        storage_res["vim_connection_id"] = _get_vim_key_by_id(
            storage_res["vim_connection_id"], vim_connection_info)

        fields = {
            'id': affected_vstorage["id"],
            'virtualStorageDescId':
                affected_vstorage["virtual_storage_desc_id"],
            'changeType': affected_vstorage["change_type"],
            # v1 -> v2
            'storageResource':
                _to_resource_handle(affected_vstorage["storage_resource"]),
            'vnfdId': None,
            'resourceDefinitionId': None,
            'zoneId': None,
            'metadata': None
        }
        affected_vstorages_v2.append(
            objects_v2.AffectedVirtualStorageV2(**fields))

    fields = {
        "affectedVnfcs": affected_vnfcs_v2,
        "affectedVirtualLinks": affected_vls_v2,
        "affectedVirtualStorages": affected_vstorages_v2,
        "affectedExtLinkPorts": None}
    return objects_v2.VnfLcmOpOccV2_ResourceChanges(**fields)


def _create_vnf_info_modifications_v2(
        dict_changed_info, operation, dict_operation_param_v2):
    changed_info = dict_changed_info
    operation_param_v2 = dict_operation_param_v2

    if changed_info is None or operation not in ["MODIFY_INFO"]:
        return None
    else:
        fields = {
            'vnfInstanceName': changed_info["vnf_instance_name"],
            'vnfInstanceDescription': changed_info["vnf_instance_description"],
            'metadata': changed_info["metadata"],
            'vnfdId': changed_info["vnfd_id"],
            'vnfProvider': changed_info["vnf_provider"],
            'vnfProductName': changed_info["vnf_product_name"],
            'vnfSoftwareVersion': changed_info["vnf_software_version"],
            'vnfdVersion': changed_info["vnfd_version"],
            # v1 -> v2
            'extensions': None,
            'vnfcInfoModifications': None,
            'vnfConfigurableProperties':
                operation_param_v2.get("vnfConfigurableProperties", None),
            'vimConnectionInfo':
                operation_param_v2.get("vimConnectionInfo", None)
        }
        return objects_v2.VnfInfoModificationsV2(**fields)


def _create_list_of_ext_virtual_link_infos_v2(
        list_of_dict_changed_ext_connectivity, operation, operation_param_v2,
        vim_connection_info=None):
    changed_ext_connectivity = list_of_dict_changed_ext_connectivity

    if changed_ext_connectivity is None or \
       operation not in ["INSTANTIATE", "CHANGE_EXT_CONN"]:
        return None
    else:
        ext_vl_infos_v2 = []
        for ext_vl_info in changed_ext_connectivity:
            # create resourceHandle
            resource_handle_v1 = ext_vl_info["resource_handle"]
            fields = {
                'vimConnectionId': _get_vim_key_by_id(
                    resource_handle_v1["vim_connection_id"],
                    vim_connection_info),
                'resourceId': resource_handle_v1["resource_id"],
                'vimLevelResourceType':
                    resource_handle_v1["vim_level_resource_type"],
                # v1 -> v2
                'resourceProviderId': None}
            ext_vl_info_resourceHandle_v2 = objects_v2.ResourceHandle(**fields)

            # create list of extLinkPorts
            ext_link_ports_v2 = []
            for ext_link_port in ext_vl_info["ext_link_ports"]:
                # create resourceHandle
                resource_handle_v1 = ext_link_port["resource_handle"]
                fields = {
                    'vimConnectionId':
                        _get_vim_key_by_id(
                            resource_handle_v1["vim_connection_id"],
                            vim_connection_info),
                    'resourceProviderId': None,
                    'resourceId': resource_handle_v1["resource_id"],
                    'vimLevelResourceType':
                        resource_handle_v1["vim_level_resource_type"]}

                ext_link_port_resourceHandle_v2 = \
                    objects_v2.ResourceHandle(**fields)

                fields = {
                    'id': ext_link_port["id"],
                    'resourceHandle': ext_link_port_resourceHandle_v2,
                    'cpInstanceId': ext_link_port["cp_instance_id"]}
                ext_link_port_v2 = objects_v2.ExtLinkPortInfoV2(**fields)
                ext_link_ports_v2.append(ext_link_port_v2)

            # create currentVnfExtCpData
            _currentVnfExtCpData = []
            for extVirtualLink in operation_param_v2.extVirtualLinks:
                if extVirtualLink.id == ext_vl_info["id"]:
                    _currentVnfExtCpData = extVirtualLink.extCps
                    break

            fields = {
                'id': ext_vl_info["id"],
                'resourceHandle': ext_vl_info_resourceHandle_v2,
                'extLinkPorts': ext_link_ports_v2,
                'currentVnfExtCpData': _currentVnfExtCpData}
            ext_vl_infos_v2.append(objects_v2.ExtVirtualLinkInfoV2(**fields))
        return ext_vl_infos_v2


def _get_vim_key_by_id(vim_id, vim_connection_info):
    if not vim_id:
        return vim_id
    # Note: If no vimId matching vim_id is found in vim_connection_info,
    # "vim_0" is returned as vim_connection_id.
    vim_connection_id = "vim_0"
    if vim_connection_info:
        for key, value in vim_connection_info.items():
            if value.vimId == vim_id:
                vim_connection_id = key
                break
    return vim_connection_id


def _create_vnf_lcm_op_occ_v2(context, op_occ_v1):
    # create v2 ProblemDetails
    _ProblemDetails_v2 = None
    if op_occ_v1.error:
        _ProblemDetails_v2 = \
            objects_v2.ProblemDetails(**jsonutils.loads(op_occ_v1.error))

    # create v2 OperationParam
    _dict_operation_params = jsonutils.loads(op_occ_v1.operation_params)
    _operation = op_occ_v1.operation

    _OperationParam_v2 = \
        _create_operation_params_v2(_dict_operation_params, _operation)

    # create VnfLcmOpOccV2_ResourceChanges
    _dict_resource_changes = jsonutils.loads(op_occ_v1.resource_changes)

    inst_v2 = inst_utils.get_inst(context, op_occ_v1.vnf_instance_id)
    _VnfLcmOpOccV2_ResourceChanges = \
        _create_resource_changes_v2(
            _dict_resource_changes, inst_v2.vimConnectionInfo)

    # create VnfInfoModificationsV2
    _VnfInfoModificationsV2 = None
    if op_occ_v1.changed_info:
        _dict_changed_info = jsonutils.loads(op_occ_v1.changed_info)
        _operation = op_occ_v1.operation
        _dict_operation_param = dict(_OperationParam_v2)

        _VnfInfoModificationsV2 = \
            _create_vnf_info_modifications_v2(
                _dict_changed_info, _operation, _dict_operation_param)

    # create list of ExtVirtualLinkInfoV2
    _list_of_ExtVirtualLinkInfoV2 = []
    if op_occ_v1.changed_ext_connectivity != []:
        _list_of_dict_changed_ext_conn = \
            jsonutils.loads(op_occ_v1.changed_ext_connectivity)
        _operation = op_occ_v1.operation

        _list_of_ExtVirtualLinkInfoV2 = \
            _create_list_of_ext_virtual_link_infos_v2(
                _list_of_dict_changed_ext_conn, _operation, _OperationParam_v2,
                inst_v2.vimConnectionInfo)

    vnf_lcm_op_occ_v2 = objects_v2.VnfLcmOpOccV2(
        id=op_occ_v1.id,
        operationState=op_occ_v1.operation_state,
        stateEnteredTime=op_occ_v1.state_entered_time,
        startTime=op_occ_v1.start_time,
        vnfInstanceId=op_occ_v1.vnf_instance_id,
        grantId=op_occ_v1.grant_id,
        operation=op_occ_v1.operation,
        isAutomaticInvocation=op_occ_v1.is_automatic_invocation,
        isCancelPending=op_occ_v1.is_cancel_pending,
        # v1 -> v2
        changedExtConnectivity=_list_of_ExtVirtualLinkInfoV2,
        error=_ProblemDetails_v2,
        resourceChanges=_VnfLcmOpOccV2_ResourceChanges,
        operationParams=_OperationParam_v2,
        changedInfo=_VnfInfoModificationsV2,
        cancelMode=None,
        modificationsTriggeredByVnfPkgChange=None,
        vnfSnapshotInfoId=None,
        # _links=
    )

    vnf_lcm_op_occ_v2.create(context)
    return vnf_lcm_op_occ_v2


@db_api.context_manager.writer
def create_vnf_lcm_op_occs_v2(context, vnf_id):
    _op_occs_v2 = []

    # get all op_occ_v1 in (vnf_instance_id==vnf_id)
    _list_op_occs_v1 = \
        api.model_query(
            context,
            models.VnfLcmOpOccs,
            read_deleted="no",
            project_only=True
        ).filter(models.VnfLcmOpOccs.vnf_instance_id == vnf_id)\
        .order_by(models.VnfLcmOpOccs.start_time).all()

    for _op_occ_v1 in _list_op_occs_v1:
        _op_occ_v2 = _create_vnf_lcm_op_occ_v2(context, _op_occ_v1)
        _op_occs_v2.append(_op_occ_v2)

    return _op_occs_v2
