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


from oslo_log import log as logging

from tacker.sol_refactored.common import config
from tacker.sol_refactored.common import http_client
from tacker.sol_refactored.common import lcm_op_occ_utils as lcmocc_utils
from tacker.sol_refactored.common import subscription_utils as subsc_utils
from tacker.sol_refactored.common import vnfd_utils
from tacker.sol_refactored.nfvo import local_nfvo
from tacker.sol_refactored import objects


LOG = logging.getLogger(__name__)

CONF = config.CONF


class NfvoClient(object):

    def __init__(self):
        self.is_local = True
        self.nfvo = local_nfvo.LocalNfvo()

        if CONF.v2_nfvo.use_external_nfvo:
            self.is_local = False
            auth_handle = http_client.OAuth2AuthHandle(
                CONF.v2_nfvo.endpoint,
                CONF.v2_nfvo.token_endpoint,
                CONF.v2_nfvo.client_id,
                CONF.v2_nfvo.client_password)
            self.client = http_client.HttpClient(auth_handle)
            self.grant_api_version = CONF.v2_nfvo.grant_api_version
            self.vnfpkgm_api_version = CONF.v2_nfvo.vnfpkgm_api_version

    def get_vnf_package_info_vnfd(self, context, vnfd_id):
        if self.is_local:
            return self.nfvo.onboarded_show(context, vnfd_id)

        url = "/vnfpkgm/v2/onboarded_vnf_packages/{}".format(vnfd_id)
        resp, body = self.client.do_request(
            url, "GET", expected_status=[200],
            version=self.vnfpkgm_api_version)
        LOG.debug("vnfpkg_info_vnfd: %s" % body)
        return objects.VnfPkgInfoV2.from_dict(body)

    def onboarded_show_vnfd(self, context, vnfd_id):
        if self.is_local:
            # this is not happen. will raise internal server error.
            LOG.error("onboarded_show_vnfd is called.")
            return

        url = "/vnfpkgm/v2/onboarded_vnf_packages/{}/vnfd".format(vnfd_id)
        resp, body = self.client.do_request(
            url, "GET", expected_status=[200],
            version=self.vnfpkgm_api_version)
        return body

    def onboarded_package_content(self, context, vnfd_id):
        if self.is_local:
            # this is not happen. will raise internal server error.
            LOG.error("onboarded_package_content is called.")
            return

        url = "/vnfpkgm/v2/onboarded_vnf_packages/{}/package_content"
        url = url.format(vnfd_id)
        resp, body = self.client.do_request(
            url, "GET", expected_status=[200],
            version=self.vnfpkgm_api_version)
        return body

    def grant(self, context, grant_req):
        LOG.debug("grant request: %s", grant_req.to_dict())

        if self.is_local:
            grant_res = self.nfvo.grant(context, grant_req)
        else:
            url = "/grant/v2/grants"
            resp, body = self.client.do_request(
                url, "POST", expected_status=[201], body=grant_req,
                version=self.grant_api_version)
            grant_res = objects.GrantV1.from_dict(body)

        LOG.debug("grant response: %s", grant_res.to_dict())
        return grant_res

    def get_vnfd(self, context, vnfd_id, all_contents=False):
        if self.is_local:
            return self.nfvo.get_vnfd(context, vnfd_id)

        if all_contents:
            zip_file = self.onboarded_package_content(context, vnfd_id)
        else:
            zip_file = self.onboarded_show_vnfd(context, vnfd_id)

        vnfd = vnfd_utils.Vnfd(vnfd_id)
        vnfd.init_from_zip_file(zip_file)

        return vnfd

    def send_inst_create_notification(self, context, inst, endpoint):
        subscs = subsc_utils.get_inst_create_subscs(context, inst)
        for subsc in subscs:
            notif_data = subsc_utils.make_create_inst_notif_data(
                subsc, inst, endpoint)
            subsc_utils.send_notification(subsc, notif_data)

        if self.is_local:
            self.nfvo.recv_inst_create_notification(context, inst)

    def send_inst_delete_notification(self, context, inst, endpoint):
        subscs = subsc_utils.get_inst_delete_subscs(context, inst)
        for subsc in subscs:
            notif_data = subsc_utils.make_delete_inst_notif_data(
                subsc, inst, endpoint)
            subsc_utils.send_notification(subsc, notif_data)

        if self.is_local:
            self.nfvo.recv_inst_delete_notification(context, inst)

    def send_lcmocc_notification(self, context, lcmocc, inst, endpoint):
        subscs = subsc_utils.get_lcmocc_subscs(context, lcmocc, inst)
        for subsc in subscs:
            notif_data = lcmocc_utils.make_lcmocc_notif_data(
                subsc, lcmocc, endpoint)
            subsc_utils.send_notification(subsc, notif_data)

        if self.is_local:
            self.nfvo.recv_lcmocc_notification(context, lcmocc, inst)
