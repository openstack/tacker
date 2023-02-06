# Copyright (C) 2022 Fujitsu
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


import threading

from oslo_log import log as logging


from tacker.sol_refactored.api import api_version
from tacker.sol_refactored.common import config
from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.common import http_client
from tacker.sol_refactored.common import subscription_utils
from tacker.sol_refactored.common import vnfd_utils
from tacker.sol_refactored import objects


LOG = logging.getLogger(__name__)

CONF = config.CONF

TEST_NOTIFICATION_TIMEOUT = 20  # seconds
NOTIFY_TYPE_PM = 'PM'
NOTIFY_TYPE_FM = 'FM'
AUTH_TYPE_OAUTH2_CLIENT_CERT = 'OAUTH2_CLIENT_CERT'
AUTH_TYPE_OAUTH2_CLIENT_CREDENTIALS = 'OAUTH2_CLIENT_CREDENTIALS'
AUTH_TYPE_BASIC = 'BASIC'


def get_vnfd(vnfd_id, csar_dir):
    vnfd = vnfd_utils.Vnfd(vnfd_id)
    vnfd.init_from_csar_dir(csar_dir)
    return vnfd


def init_nfv_dict(hot_template):
    get_params = []

    def _get_get_param(prop):
        if isinstance(prop, dict):
            for key, value in prop.items():
                if key == 'get_param':
                    get_params.append(value)
                else:
                    _get_get_param(value)
        elif isinstance(prop, list):
            for value in prop:
                _get_get_param(value)

    for res in hot_template.get('resources', {}).values():
        _get_get_param(res.get('properties', {}))

    nfv = {}

    for param in get_params:
        if (not isinstance(param, list) or len(param) < 4 or
                param[0] != 'nfv'):
            continue
        parent = nfv
        for item in param[1:-1]:
            parent.setdefault(item, {})
            parent = parent[item]
        parent[param[-1]] = None

    # TODO(YiFeng): enhance to handle list
    # NOTE: List is not considered here and only 'fixed_ips' is treated as
    # list in userdata_default.py at the moment.
    # Note that if handling list is enhanced, userdata_default.py is
    # necessary to modify.
    return nfv


def get_param_flavor(vdu_name, flavour_id, vnfd, grant):
    # try to get from grant
    if 'vimAssets' in grant:
        assets = grant['vimAssets']
        if 'computeResourceFlavours' in assets:
            flavours = assets['computeResourceFlavours']
            for flavour in flavours:
                if flavour['vnfdVirtualComputeDescId'] == vdu_name:
                    return flavour['vimFlavourId']

    # if specified in VNFD, use it
    # NOTE: if not found. parameter is set to None.
    #       may be error when stack create
    return vnfd.get_compute_flavor(flavour_id, vdu_name)


def get_param_image(vdu_name, flavour_id, vnfd, grant, fallback_vnfd=True):
    # try to get from grant
    if 'vimAssets' in grant:
        assets = grant['vimAssets']
        if 'softwareImages' in assets:
            images = assets['softwareImages']
            for image in images:
                if image['vnfdSoftwareImageId'] == vdu_name:
                    return image['vimSoftwareImageId']

    if fallback_vnfd:
        # if this flag is True, VNFD is refered to.
        # if specified in VNFD, use it.
        # NOTE: image name is assumed to be unique in the system.
        # NFVO should be return vimAssets basically.
        sw_images = vnfd.get_sw_image(flavour_id)
        for name, image in sw_images.items():
            if name == vdu_name:
                return image

    # NOTE: if not found. parameter is set to None.
    #       may be error when stack create


def get_param_zone(vdu_name, grant_req, grant):
    if 'zones' not in grant or 'addResources' not in grant:
        return

    for res in grant['addResources']:
        if 'zoneId' not in res:
            continue
        for req_res in grant_req['addResources']:
            if req_res['id'] == res['resourceDefinitionId']:
                if req_res.get('resourceTemplateId') == vdu_name:
                    for zone in grant['zones']:
                        if zone['id'] == res['zoneId']:  # must be found
                            return zone['zoneId']


def get_param_zone_by_vnfc(res_id, grant):
    if 'zones' not in grant or 'addResources' not in grant:
        return

    for res in grant['addResources']:
        if res['resourceDefinitionId'] == res_id:
            if 'zoneId' not in res:
                return
            for zone in grant['zones']:
                if zone['id'] == res['zoneId']:  # must be found
                    return zone['zoneId']
            return


def get_current_capacity(vdu_name, inst):
    count = 0
    inst_vnfcs = (inst.get('instantiatedVnfInfo', {})
                      .get('vnfcResourceInfo', []))
    for inst_vnfc in inst_vnfcs:
        if inst_vnfc['vduId'] == vdu_name:
            count += 1

    return count


def get_param_capacity(vdu_name, inst, grant_req):
    # NOTE: refer grant_req here since interpretation of VNFD was done when
    # making grant_req.
    count = get_current_capacity(vdu_name, inst)

    add_reses = grant_req.get('addResources', [])
    for res_def in add_reses:
        if (res_def['type'] == 'COMPUTE' and
                res_def['resourceTemplateId'] == vdu_name):
            count += 1

    rm_reses = grant_req.get('removeResources', [])
    for res_def in rm_reses:
        if (res_def['type'] == 'COMPUTE' and
                res_def['resourceTemplateId'] == vdu_name):
            count -= 1

    return count


def _get_fixed_ips_from_extcp(extcp):
    fixed_ips = []
    for cp_conf in extcp['cpConfig'].values():
        if 'cpProtocolData' not in cp_conf:
            continue
        for prot_data in cp_conf['cpProtocolData']:
            if 'ipOverEthernet' not in prot_data:
                continue
            if 'ipAddresses' not in prot_data['ipOverEthernet']:
                continue
            for ip in prot_data['ipOverEthernet']['ipAddresses']:
                data = {}
                if 'fixedAddresses' in ip:
                    # pick up only one ip address
                    data['ip_address'] = str(ip['fixedAddresses'][0])
                if 'subnetId' in ip:
                    data['subnet'] = ip['subnetId']
                if data:
                    fixed_ips.append(data)
    return fixed_ips


def get_param_network(cp_name, grant, req):
    # see grant first then instantiateVnfRequest
    vls = grant.get('extVirtualLinks', []) + req.get('extVirtualLinks', [])
    for vl in vls:
        for extcp in vl['extCps']:
            if extcp['cpdId'] == cp_name:
                return vl['resourceId']


def get_param_fixed_ips(cp_name, grant, req):
    # see grant first then instantiateVnfRequest
    vls = grant.get('extVirtualLinks', []) + req.get('extVirtualLinks', [])
    for vl in vls:
        for extcp in vl['extCps']:
            if extcp['cpdId'] == cp_name:
                return _get_fixed_ips_from_extcp(extcp)


def get_param_network_from_inst(cp_name, inst):
    for vl in inst['instantiatedVnfInfo'].get('extVirtualLinkInfo', []):
        for extcp in vl.get('currentVnfExtCpData', []):
            if extcp['cpdId'] == cp_name:
                return vl['resourceHandle']['resourceId']


def get_param_fixed_ips_from_inst(cp_name, inst):
    for vl in inst['instantiatedVnfInfo'].get('extVirtualLinkInfo', []):
        for extcp in vl.get('currentVnfExtCpData', []):
            if extcp['cpdId'] == cp_name:
                return _get_fixed_ips_from_extcp(extcp)


def _apply_ext_managed_vls(hot_dict, mgd_vls):
    # NOTE: refer HOT only here, not refer VNFD.
    # HOT and VNFD must be consistent.
    for mgd_vl in mgd_vls:
        vl_name = mgd_vl['vnfVirtualLinkDescId']
        network_id = mgd_vl['resourceId']
        get_res = {'get_resource': vl_name}

        def _change(item):
            if not isinstance(item, dict):
                return
            for key, value in item.items():
                if value == get_res:
                    item[key] = network_id
                else:
                    _change(value)

        del_reses = []
        for res_name, res_data in hot_dict.get('resources', {}).items():
            # delete network definition
            if res_name == vl_name:
                del_reses.append(res_name)

            # delete subnet definition
            if res_data['type'] == 'OS::Neutron::Subnet':
                net = (res_data.get('properties', {})
                               .get('network', {})
                               .get('get_resource'))
                if net == vl_name:
                    del_reses.append(res_name)

            # change '{get_resource: vl_name}' to network_id
            _change(res_data)

        for res_name in del_reses:
            hot_dict['resources'].pop(res_name)


def apply_ext_managed_vls(hot_dict, req, grant):
    # see grant first then instantiateVnfRequest
    mgd_vls = (grant.get('extManagedVirtualLinks', []) +
               req.get('extManagedVirtualLinks', []))

    _apply_ext_managed_vls(hot_dict, mgd_vls)


def apply_ext_managed_vls_from_inst(hot_dict, inst):
    mgd_vls = inst['instantiatedVnfInfo'].get('extManagedVirtualLinkInfo')

    if mgd_vls:
        # convert ExtVirtualLinkInfo to ExtManagedVirtualLinkData.
        # necessary members only.
        mgd_vls = [
            {
                'vnfVirtualLinkDescId': mgd_vl['vnfVirtualLinkDescId'],
                'resourceId': mgd_vl['networkResource']['resourceId']
            }
            for mgd_vl in mgd_vls
        ]
        _apply_ext_managed_vls(hot_dict, mgd_vls)


def get_notification_auth_handle(obj_data):
    auth_req = obj_data.get('authentication', None)
    if auth_req:
        auth = objects.SubscriptionAuthentication(
            authType=auth_req['authType']
        )
        if AUTH_TYPE_OAUTH2_CLIENT_CERT in auth.authType:
            param = obj_data.authentication.paramsOauth2ClientCert
            ca_cert = CONF.v2_vnfm.notification_mtls_ca_cert_file
            client_cert = CONF.v2_vnfm.notification_mtls_client_cert_file
            return http_client.OAuth2MtlsAuthHandle(
                None, param.tokenEndpoint,
                param.clientId, ca_cert, client_cert)
        elif AUTH_TYPE_OAUTH2_CLIENT_CREDENTIALS in auth.authType:
            param = obj_data.authentication.paramsOauth2ClientCredentials
            verify = CONF.v2_vnfm.notification_verify_cert
            if verify and CONF.v2_vnfm.notification_ca_cert_file:
                verify = CONF.v2_vnfm.notification_ca_cert_file
            return http_client.OAuth2AuthHandle(
                None, param.tokenEndpoint, param.clientId,
                param.clientPassword,
                verify=verify)
        elif AUTH_TYPE_BASIC in auth.authType:
            param = obj_data.authentication.paramsBasic
            verify = CONF.v2_vnfm.notification_verify_cert
            if verify and CONF.v2_vnfm.notification_ca_cert_file:
                verify = CONF.v2_vnfm.notification_ca_cert_file
            return http_client.BasicAuthHandle(
                param.userName, param.password,
                verify=verify)
        else:
            raise sol_ex.AuthTypeNotFound(auth.authType)
    else:
        verify = CONF.v2_vnfm.notification_verify_cert
        if verify and CONF.v2_vnfm.notification_ca_cert_file:
            verify = CONF.v2_vnfm.notification_ca_cert_file
        return http_client.NoAuthHandle(verify=verify)


def async_call(func):
    def inner(*args, **kwargs):
        th = threading.Thread(target=func, args=args,
                              kwargs=kwargs, daemon=True)
        th.start()
    return inner


@async_call
def send_notification(obj_data, notif_data, notify_type=None):
    version = api_version.CURRENT_VERSION
    auth_handle = subscription_utils.get_notification_auth_handle(obj_data)
    connect_retries = (CONF.v2_vnfm.notify_connect_retries
                       if CONF.v2_vnfm.notify_connect_retries else None)
    client = http_client.HttpClient(auth_handle,
                                    version=version,
                                    connect_retries=connect_retries)
    if notify_type == NOTIFY_TYPE_PM:
        version = api_version.CURRENT_PM_VERSION
        auth_handle = get_notification_auth_handle(obj_data)
        client = http_client.HttpClient(auth_handle,
                                        version=version)
    if notify_type == NOTIFY_TYPE_FM:
        version = api_version.CURRENT_FM_VERSION
        auth_handle = get_notification_auth_handle(obj_data)
        client = http_client.HttpClient(auth_handle,
                                        version=version)

    url = obj_data.callbackUri
    try:
        resp, _ = client.do_request(
            url, "POST", expected_status=[204], body=notif_data)
    except sol_ex.SolException as ex:
        # it may occur if test_notification was not executed.
        LOG.exception(f"send_notification failed: {ex}")

    if resp.status_code != 204:
        LOG.error(f"send_notification failed: {resp.__dict__}")


def test_notification(obj_data, notify_type=None):
    version = api_version.CURRENT_VERSION
    auth_handle = subscription_utils.get_notification_auth_handle(obj_data)
    if notify_type == NOTIFY_TYPE_PM:
        version = api_version.CURRENT_PM_VERSION
        auth_handle = get_notification_auth_handle(obj_data)
    if notify_type == NOTIFY_TYPE_FM:
        version = api_version.CURRENT_FM_VERSION
        auth_handle = get_notification_auth_handle(obj_data)

    client = http_client.HttpClient(auth_handle,
                                    version=version,
                                    timeout=TEST_NOTIFICATION_TIMEOUT)

    url = obj_data.callbackUri
    try:
        resp, _ = client.do_request(url, "GET", expected_status=[204])
    except sol_ex.SolException as e:
        # any notify_type of error is considered. avoid 500 error.
        raise sol_ex.TestNotificationFailed() from e

    if resp.status_code != 204:
        raise sol_ex.TestNotificationFailed()
