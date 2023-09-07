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


import io
import os
import shutil
import zipfile

from oslo_log import log as logging

from tacker.sol_refactored.common import config
from tacker.sol_refactored.common import fm_alarm_utils as alarm_utils
from tacker.sol_refactored.common import fm_subscription_utils as fm_utils
from tacker.sol_refactored.common import http_client
from tacker.sol_refactored.common import lcm_op_occ_utils as lcmocc_utils
from tacker.sol_refactored.common import pm_job_utils
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
            self.endpoint = CONF.v2_nfvo.endpoint
            if CONF.v2_nfvo.use_client_secret_basic:
                verify = CONF.v2_nfvo.nfvo_verify_cert
                if verify and CONF.v2_nfvo.nfvo_ca_cert_file:
                    verify = CONF.v2_nfvo.nfvo_ca_cert_file
                auth_handle = http_client.OAuth2AuthHandle(
                    self.endpoint,
                    CONF.v2_nfvo.token_endpoint,
                    CONF.v2_nfvo.client_id,
                    CONF.v2_nfvo.client_password,
                    verify)
            else:
                auth_handle = http_client.OAuth2MtlsAuthHandle(
                    self.endpoint,
                    CONF.v2_nfvo.token_endpoint,
                    CONF.v2_nfvo.client_id,
                    CONF.v2_nfvo.mtls_ca_cert_file,
                    CONF.v2_nfvo.mtls_client_cert_file)
            self.client = http_client.HttpClient(auth_handle)
            self.grant_api_version = CONF.v2_nfvo.grant_api_version
            self.vnfpkgm_api_version = CONF.v2_nfvo.vnfpkgm_api_version
            self.csar_cache_dir = CONF.v2_nfvo.vnf_package_cache_dir
            if not os.path.exists(self.csar_cache_dir):
                os.makedirs(self.csar_cache_dir)

    def get_vnf_package_info_vnfd(self, context, vnfd_id):
        if self.is_local:
            return self.nfvo.onboarded_show(context, vnfd_id)

        url = "{}/vnfpkgm/v2/onboarded_vnf_packages/{}".format(
            self.endpoint, vnfd_id)
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

        url = "{}/vnfpkgm/v2/onboarded_vnf_packages/{}/vnfd".format(
            self.endpoint, vnfd_id)
        resp, body = self.client.do_request(
            url, "GET", expected_status=[200],
            version=self.vnfpkgm_api_version)
        return body

    def onboarded_package_content(self, context, vnfd_id):
        if self.is_local:
            # this is not happen. will raise internal server error.
            LOG.error("onboarded_package_content is called.")
            return

        url = "{}/vnfpkgm/v2/onboarded_vnf_packages/{}/package_content"
        url = url.format(self.endpoint, vnfd_id)
        resp, body = self.client.do_request(
            url, "GET", expected_status=[200],
            version=self.vnfpkgm_api_version)
        return body

    def grant(self, context, grant_req):
        LOG.debug("grant request: %s", grant_req.to_dict())

        if self.is_local:
            grant_res = self.nfvo.grant(context, grant_req)
        else:
            url = "{}/grant/v1/grants".format(self.endpoint)
            resp, body = self.client.do_request(
                url, "POST", expected_status=[201], body=grant_req,
                version=self.grant_api_version)
            grant_res = objects.GrantV1.from_dict(body)

        LOG.debug("grant response: %s", grant_res.to_dict())
        return grant_res

    def get_vnfd(self, context, vnfd_id, all_contents=False):
        if self.is_local:
            return self.nfvo.get_vnfd(context, vnfd_id)

        csar_dir = os.path.join(self.csar_cache_dir, vnfd_id)
        vnfd = vnfd_utils.Vnfd(vnfd_id)

        if os.path.isdir(csar_dir):
            # if cache exists, use it regardless of all_contents
            vnfd.init_from_csar_dir(csar_dir)
        elif not all_contents:
            # need VNFD only. not make cache.
            zip_data = self.onboarded_show_vnfd(context, vnfd_id)
            vnfd.init_from_zip_data(zip_data)
        else:  # all_contents=True
            # get vnf package contents and make cache
            zip_data = self.onboarded_package_content(context, vnfd_id)
            self._make_csar_cache(csar_dir, zip_data)
            vnfd.init_from_csar_dir(csar_dir)

        return vnfd

    def _make_csar_cache(self, csar_dir, zip_data):
        os.mkdir(csar_dir)
        try:
            buff = io.BytesIO(zip_data)
            with zipfile.ZipFile(buff, 'r') as zf:
                zf.extractall(csar_dir)
        except Exception as ex:
            self._delete_csar_dir(csar_dir)
            raise ex

    def _delete_csar_cache(self, context, vnfd_id):
        insts = objects.VnfInstanceV2.get_by_filter(context,
                                                    vnfdId=vnfd_id)

        # NOTE: assume this method called after delete VnfInstance
        if len(insts) > 0:
            # if there are other vnfinstances using the same cache, do nothing.
            return

        csar_dir = os.path.join(self.csar_cache_dir, vnfd_id)
        if os.path.exists(csar_dir):
            self._delete_csar_dir(csar_dir)

    def _delete_csar_dir(self, csar_dir):
        try:
            shutil.rmtree(csar_dir)
        except Exception:
            # NOTE: it is not failed basically since no one ought to
            # access it. maybe critical system failure if failed.
            # it is critical for tacker since incomplete cache may remain.
            # should be deleted manually.
            LOG.critical("VNF package cache '%s' could not be deleted",
                         csar_dir)

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

        if not self.is_local:
            self._delete_csar_cache(context, inst.vnfdId)

    def send_lcmocc_notification(self, context, lcmocc, inst, endpoint):
        subscs = subsc_utils.get_lcmocc_subscs(context, lcmocc, inst)
        for subsc in subscs:
            notif_data = lcmocc_utils.make_lcmocc_notif_data(
                subsc, lcmocc, endpoint)
            subsc_utils.send_notification(subsc, notif_data)

        if self.is_local:
            self.nfvo.recv_lcmocc_notification(context, lcmocc, inst)

    def send_alarm_notification(self, context, alarm, inst, endpoint):
        subscs = fm_utils.get_alarm_subscs(context, alarm, inst)
        for subsc in subscs:
            notif_data = alarm_utils.make_alarm_notif_data(
                subsc, alarm, endpoint)
            subsc_utils.send_notification(
                subsc, notif_data, subsc_utils.NOTIFY_TYPE_FM)

    def send_pm_job_notification(self, report, pm_job, timestamp, endpoint):
        report_object_instance_id = {entry.objectInstanceId
                                     for entry in report.entries}
        for instance_id in report_object_instance_id:
            sub_instance_ids = [
                entry.subObjectInstanceId for entry in report.entries
                if (entry.objectInstanceId == instance_id and
                    entry.obj_attr_is_set('subObjectInstanceId'))
            ]
            notif_data = pm_job_utils.make_pm_notif_data(
                instance_id, sub_instance_ids, report.id,
                pm_job, timestamp, endpoint)
            subsc_utils.send_notification(
                pm_job, notif_data, subsc_utils.NOTIFY_TYPE_PM)
