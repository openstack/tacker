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

import base64

from cryptography.hazmat.primitives import hashes
from cryptography import x509

from tacker.sol_refactored.api.schemas import common_types
from tacker.sol_refactored.api import validator
from tacker.sol_refactored.common import config
from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.common import http_client
from tacker.sol_refactored.common import vnfd_utils

# NOTE: The methods defined in this file are intended to be used from
# scripts (ex. mgmt_driver, UserData class method, coordinate script)
# which executed as a separate process by tacker process (i.e.
# conductor).
# Note that 'dict' is used instead of 'objects' since 'objects' is not
# used by scripts.
# Some methods intend to be used with tacker process commonly. Note
# that objects are dict compat.

CONF = config.CONF


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


def check_subsc_auth(auth_req, validation=True):
    if validation:
        auth_validator = validator.SolSchemaValidator(
            common_types.SubscriptionAuthentication)
        auth_validator.validate(auth_req)

    auth_type = auth_req['authType']
    if 'OAUTH2_CLIENT_CERT' in auth_type:
        oauth2_mtls_req = auth_req.get('paramsOauth2ClientCert')
        if oauth2_mtls_req is None:
            msg = "paramsOauth2ClientCert must be specified."
            raise sol_ex.InvalidSubscription(sol_detail=msg)
        client_cert_file = CONF.v2_vnfm.notification_mtls_client_cert_file
        cert_ref = oauth2_mtls_req.get('certificateRef', {})
        if cert_ref.get('type') == 'x5t#S256':
            hash_type = hashes.SHA256()
        else:
            # support type is only "x5t#S256"(SHA-256)
            msg = "certificateRef type is invalid."
            raise sol_ex.InvalidSubscription(sol_detail=msg)

        with open(client_cert_file, "rb") as f:
            client_cert = x509.load_pem_x509_certificate(f.read())
            cert_fingerprint = client_cert.fingerprint(hash_type)

        fingerprint_value = (base64.urlsafe_b64encode(cert_fingerprint).
            rstrip(b'=').decode('utf-8'))
        if fingerprint_value != cert_ref.get('value'):
            msg = "certificateRef value is incorrect."
            raise sol_ex.InvalidSubscription(sol_detail=msg)
    if 'OAUTH2_CLIENT_CREDENTIALS' in auth_type:
        oauth2_req = auth_req.get('paramsOauth2ClientCredentials')
        if oauth2_req is None:
            msg = "paramsOauth2ClientCredentials must be specified."
            raise sol_ex.InvalidSubscription(sol_detail=msg)
    if 'BASIC' in auth_type:
        basic_req = auth_req.get('paramsBasic')
        if basic_req is None:
            msg = "paramsBasic must be specified."
            raise sol_ex.InvalidSubscription(sol_detail=msg)


def get_http_auth_handle(auth_req):
    # NOTE: this method uses tacker configuration. script should set
    # the following parameters before calling this method.
    # ---
    # from tacker.common import config
    # args = ["--config-file", "/etc/tacker/tacker.conf"]
    # config.init(args)
    # ---
    if auth_req is None:
        verify = CONF.v2_vnfm.notification_verify_cert
        if verify and CONF.v2_vnfm.notification_ca_cert_file:
            verify = CONF.v2_vnfm.notification_ca_cert_file
        return http_client.NoAuthHandle(verify=verify)

    # NOTE: auth_req is already validated.
    auth_type = auth_req['authType']
    # NOTE: if there are multiple auth_types, the following priority
    # applied.
    if 'OAUTH2_CLIENT_CERT' in auth_type:
        oauth2_mtls_req = auth_req['paramsOauth2ClientCert']
        ca_cert = CONF.v2_vnfm.notification_mtls_ca_cert_file
        client_cert = CONF.v2_vnfm.notification_mtls_client_cert_file
        return http_client.OAuth2MtlsAuthHandle(
            None, oauth2_mtls_req['tokenEndpoint'],
            oauth2_mtls_req['clientId'], ca_cert, client_cert)
    elif 'OAUTH2_CLIENT_CREDENTIALS' in auth_type:
        oauth2_req = auth_req.get('paramsOauth2ClientCredentials')
        verify = CONF.v2_vnfm.notification_verify_cert
        if verify and CONF.v2_vnfm.notification_ca_cert_file:
            verify = CONF.v2_vnfm.notification_ca_cert_file
        return http_client.OAuth2AuthHandle(
            None, oauth2_req.get('tokenEndpoint'),
            oauth2_req.get('clientId'), oauth2_req.get('clientPassword'),
            verify=verify)
    elif 'BASIC' in auth_type:
        basic_req = auth_req.get('paramsBasic')
        verify = CONF.v2_vnfm.notification_verify_cert
        if verify and CONF.v2_vnfm.notification_ca_cert_file:
            verify = CONF.v2_vnfm.notification_ca_cert_file
        return http_client.BasicAuthHandle(
            basic_req.get('userName'), basic_req.get('password'),
            verify=verify)
