# Copyright (C) 2023 Fujitsu
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

import ddt
import os

from oslo_config import cfg
from oslo_serialization import jsonutils
from sqlalchemy import desc
from sqlalchemy.orm import joinedload

from tacker.common import crypt_utils
from tacker import context as t_context
from tacker.db import api as db_api
from tacker.db.db_sqlalchemy import api
from tacker.sol_refactored.db.sqlalchemy import models
from tacker.sol_refactored import objects
from tacker.tests.functional.sol_encrypt_cred_v2 import paramgen
from tacker.tests.functional.sol_separated_nfvo_v2 import fake_grant_v2
from tacker.tests.functional.sol_v2_common import test_vnflcm_basic_common
from tacker.tests import utils

# NOTE: Loads the Tacker configuration required to use the decrypt method in
# the test method.
CORE_OPTS = [
    cfg.BoolOpt('use_credential_encryption'),
    cfg.StrOpt('keymanager_type'),
    cfg.StrOpt('crypt_key_dir')
]
cfg.CONF.register_opts(CORE_OPTS)
OPTS = [
    cfg.StrOpt('password'),
    cfg.StrOpt('username'),
    cfg.StrOpt('user_domain_name'),
    cfg.StrOpt('project_name'),
    cfg.StrOpt('project_domain_name'),
    cfg.StrOpt('auth_url')
]
cfg.CONF.register_opts(OPTS, 'keystone_authtoken')


@ddt.ddt
class VnfLcmTest(test_vnflcm_basic_common.CommonVnfLcmTest):
    CRYPT_AUTH_KEYS = ['password', 'client_secret', 'bearer_token']
    CRYPT_VNFC_PARAMS_KEYS = ['new_vnfc_param', 'old_vnfc_param']

    @classmethod
    def setUpClass(cls):
        # In this test, the behavior of Prometheus is simulated by a stub
        # rather than a fake server, and the fake server is not needed and will
        # not start.
        cls.is_https = True
        super(VnfLcmTest, cls).setUpClass()
        cls.fake_prometheus_ip = "127.0.0.1"
        cls.context = t_context.get_admin_context()
        cls.password = "devstack"
        cls.chg_password = "dummy_password"

    @classmethod
    def tearDownClass(cls):
        super(VnfLcmTest, cls).tearDownClass()

    def setUp(self):
        super().setUp()
        self.set_server_callback(
            'PUT', "/-/reload", status_code=202,
            response_headers={"Content-Type": "text/plain"})

    @classmethod
    @db_api.context_manager.reader
    def _get_vnflcm_op_occs_by_id(cls, context, id,
                                  columns_to_join=None):
        query = api.model_query(
            context, models.VnfLcmOpOccV2, project_only=True).filter_by(
            id=id).order_by(desc("stateEnteredTime"))

        if columns_to_join:
            for column in columns_to_join:
                query = query.options(joinedload(column))

        db_vnflcm_op_occ = query.first()

        return db_vnflcm_op_occ

    @classmethod
    @db_api.context_manager.reader
    def _get_grant_by_id(cls, context, op_occ_id,
                         columns_to_join=None):
        query = api.model_query(
            context, models.GrantV1, project_only=True).filter_by(
                vnfLcmOpOccId=op_occ_id)

        if columns_to_join:
            for column in columns_to_join:
                query = query.options(joinedload(column))

        db_grant = query.first()

        return db_grant

    @classmethod
    @db_api.context_manager.reader
    def _get_vnf_instance_by_id(cls, context, vnf_instance_id,
                                columns_to_join=None):
        query = api.model_query(
            context, models.VnfInstanceV2, project_only=True).filter_by(
                id=vnf_instance_id)

        if columns_to_join:
            for column in columns_to_join:
                query = query.options(joinedload(column))

        db_inst = query.first()

        return db_inst

    @classmethod
    @db_api.context_manager.reader
    def _get_lccn_subscription_by_id(cls, context, id,
                                     columns_to_join=None):
        query = api.model_query(
            context, models.LccnSubscriptionV2, project_only=True).filter_by(
            id=id)

        if columns_to_join:
            for column in columns_to_join:
                query = query.options(joinedload(column))

        db_lccn_subsc = query.first()

        return db_lccn_subsc

    @classmethod
    @db_api.context_manager.reader
    def _get_pm_job_by_id(cls, context, pm_job_id,
                          columns_to_join=None):
        query = api.model_query(
            context, models.PmJobV2, project_only=True).filter_by(
                id=pm_job_id)

        if columns_to_join:
            for column in columns_to_join:
                query = query.options(joinedload(column))

        db_pm_job = query.first()

        return db_pm_job

    @classmethod
    @db_api.context_manager.reader
    def _get_pm_threshold_by_id(cls, context, threshold_id,
                                columns_to_join=None):
        query = api.model_query(
            context, models.ThresholdV2, project_only=True).filter_by(
                id=threshold_id)

        if columns_to_join:
            for column in columns_to_join:
                query = query.options(joinedload(column))

        db_threshold = query.first()

        return db_threshold

    @classmethod
    @db_api.context_manager.reader
    def _get_fm_subscription_by_id(cls, context, fm_subscription_id,
                                   columns_to_join=None):
        query = api.model_query(
            context, models.FmSubscriptionV1, project_only=True).filter_by(
                id=fm_subscription_id)

        if columns_to_join:
            for column in columns_to_join:
                query = query.options(joinedload(column))

        db_fm_subsc = query.first()

        return db_fm_subsc

    def test_encrypt_vnflcm_subsc_basic(self):
        """Test encrypt LCM operations for subscription with basic auth

        * FT-checkpoints:
          This FT confirms the following points.
          - That the data retrieved directly from the DB is encrypted.
          - That the data retrieved from DB via object is automatically
            decrypted.

        * About LCM operations:
          This test includes the following operations.
          - 1. Create subscription
          - 2. Create VNF instance
          - 3. Instantiate VNF instance
          - 4. Update VNF
          - 5. Update VNF (will fail)
          - 6. Rollback update VNF
          - 7. Change current VNF package (will fail)
          - 8. Failed change current VNF package
          - 9. Create PM Job
          - 10. Create PM Threshold
          - 11. Create FM Subscription
          - 12. Delete FM Subscription
          - 13. Delete PM Threshold
          - 14. Delete PM Job
          - 15. Terminate VNF instance
          - 16. Delete VNF instance
          - 17. Delete subscription
          - 18. Create VNF instance
          - 19. Instantiate VNF (will fail)
          - 20. Rollback instantiation operation
          - 21. Delete VNF instance
        """

        # setup
        basic_lcms_min_path = utils.test_sample("functional/sol_v2_common",
                                                "basic_lcms_min")
        min_zip_path, min_vnfd_id = self.create_vnf_package(
            basic_lcms_min_path, nfvo=True)

        vnfd_path = "contents/Definitions/v2_sample2_df_simple.yaml"
        self._register_vnf_package_mock_response(min_vnfd_id,
                                                 min_zip_path)

        glance_image = fake_grant_v2.GrantV2.get_sw_image(
            basic_lcms_min_path, vnfd_path)
        flavour_vdu_dict = fake_grant_v2.GrantV2.get_compute_flavor(
            basic_lcms_min_path, vnfd_path)

        chg_pkg_failed_path = utils.test_sample("functional/sol_v2_common",
            "test_change_vnf_pkg_with_update_failed")
        chg_zip_path, chg_vnfd_id = self.create_vnf_package(
            chg_pkg_failed_path, nfvo=True)
        chg_vnfd_path = ("contents/Definitions/"
                         "change_vnf_pkg_error_image_df_simple.yaml")

        self._register_vnf_package_mock_response(chg_vnfd_id,
                                                 chg_zip_path)

        zone_name_list = self.get_zone_list()
        create_req = paramgen.create_vnf_min(min_vnfd_id)

        # 1. Create subscription
        callback_url = os.path.join(self.get_notify_callback_url(),
                                    self._testMethodName)
        callback_uri = ('https://localhost:'
                        f'{self.get_server_port()}'
                        f'{callback_url}')
        sub_req = paramgen.sub_create_basic(callback_uri, self.password)
        resp, body = self.create_subscription(sub_req)
        self.assertEqual(201, resp.status_code)
        sub_id = body['id']

        # check encrypt LccnSubscriptionV2
        subsc = self._get_lccn_subscription_by_id(self.context, sub_id)
        auth = jsonutils.loads(subsc['authentication'])
        self.assertEqual(self.password,
                         crypt_utils.decrypt(auth['paramsBasic']['password']))
        subsc_obj = objects.v2.lccn_subscription.LccnSubscriptionV2.get_by_id(
            self.context, sub_id)
        self.assertEqual(self.password,
                         subsc_obj['authentication']['paramsBasic']
                                  ['password'])

        # check show LccnSubscriptionV2
        resp, body = self.show_subscription(sub_id)
        self.assertIsNone(body.get('authentication', None))

        # 2. Create VNF instance
        resp, body = self.create_vnf_instance(create_req)
        self.assertEqual(201, resp.status_code)
        inst_id = body['id']

        # 3. Instantiate VNF instance
        self._set_grant_response(
            True, 'INSTANTIATE', glance_image=glance_image,
            flavour_vdu_dict=flavour_vdu_dict, zone_name_list=zone_name_list,
            password=self.password)
        instantiate_req = paramgen.instantiate_vnf(
            self.auth_url, self.password)
        resp, body = self.instantiate_vnf_instance(inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # check encrypt VnfInstanceV2
        inst = self._get_vnf_instance_by_id(self.context, inst_id)
        dict_vim_conn = jsonutils.loads(inst['vimConnectionInfo'])
        for cred_key in self.CRYPT_AUTH_KEYS:
            self.assertEqual(self.password,
                             crypt_utils.decrypt(dict_vim_conn['vim1']
                                                 ['accessInfo'][cred_key]))
        inst_obj = objects.v2.vnf_instance.VnfInstanceV2.get_by_id(
            self.context, inst_id)
        for cred_key in self.CRYPT_AUTH_KEYS:
            self.assertEqual(self.password,
                             inst_obj['vimConnectionInfo']['vim1']
                                     ['accessInfo'][cred_key])

        # check not saved VnfLcmOpOccV2 vimConnectionInfo
        opocc = self._get_vnflcm_op_occs_by_id(self.context, lcmocc_id)
        opocc_vim_conn = opocc['operationParams']['vimConnectionInfo']
        for cred_key in self.CRYPT_AUTH_KEYS:
            self.assertIsNone(
                opocc_vim_conn['vim1']['accessInfo'].get(cred_key, None))

        # check show VnfInstanceV2 vimConnectionInfo
        # Normally, password, client_secret, and bearer_token are not
        # specified at the same time, but this time they are all included for
        # the DB registration test.
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        for cred_key in self.CRYPT_AUTH_KEYS:
            self.assertIsNone(
                body['vimConnectionInfo']['vim1']['accessInfo'].get(
                    cred_key, None))

        # 4. Update VNF
        update_req = paramgen.update_vnf(self.auth_url, self.chg_password)
        resp, body = self.update_vnf_instance(inst_id, update_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # check encrypt VnfInstanceV2
        inst = self._get_vnf_instance_by_id(self.context, inst_id)
        dict_vim_conn = jsonutils.loads(inst['vimConnectionInfo'])
        for cred_key in self.CRYPT_AUTH_KEYS:
            self.assertEqual(self.chg_password,
                             crypt_utils.decrypt(dict_vim_conn['vim1']
                                                 ['accessInfo'][cred_key]))
        inst_obj = objects.v2.vnf_instance.VnfInstanceV2.get_by_id(
            self.context, inst_id)
        for cred_key in self.CRYPT_AUTH_KEYS:
            self.assertEqual(self.chg_password,
                             inst_obj['vimConnectionInfo']['vim1']
                             ['accessInfo'][cred_key])

        # check not saved VnfLcmOpOccV2 vimConnectionInfo
        opocc = self._get_vnflcm_op_occs_by_id(self.context, lcmocc_id)
        opocc_vim_conn = opocc['operationParams']['vimConnectionInfo']
        for cred_key in self.CRYPT_AUTH_KEYS:
            self.assertIsNone(
                opocc_vim_conn['vim1']['accessInfo'].get(cred_key, None))

        # check not saved VnfLcmOpOccV2 changedInfo
        chg_info = jsonutils.loads(opocc['changedInfo'])
        for cred_key in self.CRYPT_AUTH_KEYS:
            self.assertIsNone(chg_info['vimConnectionInfo']['vim1']
                              ['accessInfo'].get(cred_key, None))

        # check show VnfLcmOpOccV2 vimConnectionInfo
        resp, body = self.show_lcmocc(lcmocc_id)
        self.assertEqual(200, resp.status_code)
        for cred_key in self.CRYPT_AUTH_KEYS:
            self.assertIsNone(
                body['operationParams']['vimConnectionInfo']['vim1']
                ['accessInfo'].get(cred_key, None))

        # check show VnfLcmOpOccV2 changedInfo
        for cred_key in self.CRYPT_AUTH_KEYS:
            self.assertIsNone(
                body['changedInfo']['vimConnectionInfo']['vim1']['accessInfo']
                .get(cred_key, None))

        update_req = paramgen.update_vnf(self.auth_url, self.password)
        resp, body = self.update_vnf_instance(inst_id, update_req)
        self.assertEqual(202, resp.status_code)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 5. Update VNF (will fail)
        path = '/tmp/modify_information_start'
        with open(path, 'w', encoding='utf-8') as f:
            f.write('')
        self.addCleanup(os.remove, path)
        update_req = paramgen.update_vnf(self.auth_url, self.chg_password)
        resp, body = self.update_vnf_instance(inst_id, update_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_failed_temp(lcmocc_id)

        # check encrypted VnfLcmOpOccV2 vimConnectionInfo
        opocc = self._get_vnflcm_op_occs_by_id(self.context, lcmocc_id)
        opocc_vim_conn = opocc['operationParams']['vimConnectionInfo']
        for cred_key in self.CRYPT_AUTH_KEYS:
            self.assertEqual(self.chg_password,
                             crypt_utils.decrypt(opocc_vim_conn['vim1']
                                                 ['accessInfo'][cred_key]))
        opocc_obj = objects.v2.vnf_lcm_op_occ.VnfLcmOpOccV2.get_by_id(
            self.context, lcmocc_id)
        for cred_key in self.CRYPT_AUTH_KEYS:
            self.assertEqual(self.chg_password,
                             opocc_obj['operationParams']['vimConnectionInfo']
                                      ['vim1']['accessInfo'][cred_key])

        # check encrypted VnfLcmOpOccV2 changedInfo
        # If failed to update, changedInfo is registered with a NULL value,
        # so the encrypted changedInfo information is never registered.
        chg_info = opocc.get('changedInfo', None)
        self.assertIsNone(chg_info)

        # check show VnfLcmOpOccV2 vimConnectionInfo
        resp, body = self.show_lcmocc(lcmocc_id)
        self.assertEqual(200, resp.status_code)
        for cred_key in self.CRYPT_AUTH_KEYS:
            self.assertIsNone(
                body['operationParams']['vimConnectionInfo']['vim1']
                ['accessInfo'].get(cred_key, None))

        # check show VnfLcmOpOccV2 changedInfo
        # If failed to update, changedInfo is registered with a NULL value,
        # so the encrypted changedInfo information is never registered.
        self.assertIsNone(
            body.get('changedInfo', None))

        # 6. Rollback update VNF
        resp, body = self.rollback_lcmocc(lcmocc_id)
        self.assertEqual(202, resp.status_code)
        self.wait_lcmocc_rolled_back(lcmocc_id)

        # check not saved VnfLcmOpOccV2 vimConnectionInfo
        opocc = self._get_vnflcm_op_occs_by_id(self.context, lcmocc_id)
        opocc_vim_conn = opocc['operationParams']['vimConnectionInfo']
        for cred_key in self.CRYPT_AUTH_KEYS:
            self.assertIsNone(opocc_vim_conn['vim1']['accessInfo']
                              .get(cred_key, None))

        # 7. Change current VNF package (will fail)
        chg_glance_image = fake_grant_v2.GrantV2.get_sw_image(
            chg_pkg_failed_path, chg_vnfd_path)
        chg_flavour_vdu_dict = fake_grant_v2.GrantV2.get_compute_flavor(
            chg_pkg_failed_path, chg_vnfd_path)
        self._set_grant_response(
            True, 'CHANGE_VNFPKG', glance_image=chg_glance_image,
            flavour_vdu_dict=chg_flavour_vdu_dict,
            zone_name_list=zone_name_list)
        change_vnfpkg_req = paramgen.change_vnfpkg(chg_vnfd_id, self.password)
        resp, body = self.change_vnfpkg(inst_id, change_vnfpkg_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_failed_temp(lcmocc_id)

        # check encrypted VnfLcmOpOccV2 additionalParams
        opocc = self._get_vnflcm_op_occs_by_id(self.context, lcmocc_id)
        vdu_param = (opocc['operationParams']['additionalParams']
                          ['vdu_params'][0])
        for vnfc_param_key in self.CRYPT_VNFC_PARAMS_KEYS:
            self.assertEqual(self.password,
                             crypt_utils.decrypt(
                                 vdu_param[vnfc_param_key]['password']))
            self.assertEqual(self.password,
                             crypt_utils.decrypt(
                                 vdu_param[vnfc_param_key]
                                 ['authentication']
                                 ['paramsBasic']['password']))
            self.assertEqual(self.password,
                             crypt_utils.decrypt(
                                 vdu_param[vnfc_param_key]
                                 ['authentication']
                                 ['paramsOauth2ClientCredentials']
                                 ['clientPassword']))
        opocc_obj = objects.v2.vnf_lcm_op_occ.VnfLcmOpOccV2.get_by_id(
            self.context, lcmocc_id)
        vdu_param_obj = (opocc_obj['operationParams']['additionalParams']
                         ['vdu_params'][0])
        for vnfc_param_key in self.CRYPT_VNFC_PARAMS_KEYS:
            self.assertEqual(self.password,
                             vdu_param_obj[vnfc_param_key]['password'])
            self.assertEqual(self.password,
                             vdu_param_obj[vnfc_param_key]['authentication']
                             ['paramsBasic']['password'])
            self.assertEqual(self.password,
                             vdu_param_obj[vnfc_param_key]['authentication']
                             ['paramsOauth2ClientCredentials']
                             ['clientPassword'])

        # check show lcmocc additionalParams
        resp, body = self.show_lcmocc(lcmocc_id)
        self.assertEqual(200, resp.status_code)
        for vnfc_param_key in self.CRYPT_VNFC_PARAMS_KEYS:
            self.assertIsNone(body['operationParams']['additionalParams']
                              ['vdu_params'][0][vnfc_param_key]
                              .get('password', None))
            self.assertIsNone(body['operationParams']['additionalParams']
                              ['vdu_params'][0][vnfc_param_key]
                              ['authentication']['paramsBasic']
                              .get('password', None))
            self.assertIsNone(body['operationParams']['additionalParams']
                              ['vdu_params'][0][vnfc_param_key]
                              ['authentication']
                              ['paramsOauth2ClientCredentials']
                              .get('clientPassword', None))

        # 8. Failed change current VNF package
        resp, body = self.fail_lcmocc(lcmocc_id)
        self.assertEqual(200, resp.status_code)

        # check not saved VnfLcmOpOccV2 additionalParams
        opocc = self._get_vnflcm_op_occs_by_id(self.context, lcmocc_id)
        self.assertEqual("FAILED", opocc.operationState)
        vdu_param = (opocc['operationParams']['additionalParams']
                          ['vdu_params'][0])
        for cred_key in self.CRYPT_VNFC_PARAMS_KEYS:
            self.assertIsNone(vdu_param[cred_key].get('password', None))
            self.assertIsNone(vdu_param[cred_key]['authentication']
                              ['paramsBasic'].get('password', None))
            self.assertIsNone(vdu_param[cred_key]['authentication']
                              ['paramsOauth2ClientCredentials']
                              .get('clientPassword', None))

        # 9. Create PM Job
        # Normally only CNF is used for PM jobs, but VNF is also acceptable for
        # DB registration tests, so VNF is used for testing so as not to
        # increase the number of jobs.
        callback_url = os.path.join(self.get_notify_callback_url(),
                                    self._testMethodName)
        callback_uri = ('https://localhost:'
                        f'{self.get_server_port()}'
                        f'{callback_url}')
        sub_req = paramgen.pm_job_basic(
            callback_uri, inst_id, self.fake_prometheus_ip, self.password)
        resp, body = self.create_pm_job(sub_req)
        self.assertEqual(201, resp.status_code)
        pm_job_id = body.get('id')

        # check encrypt PmJobV2
        pm_job = self._get_pm_job_by_id(self.context, pm_job_id)
        self.assertEqual(self.password,
                         crypt_utils.decrypt(pm_job['metadata__']['monitoring']
                                                   ['targetsInfo'][0]
                                                   ['authInfo']
                                                   ['ssh_password']))
        auth = jsonutils.loads(pm_job['authentication'])
        self.assertEqual(self.password,
                         crypt_utils.decrypt(auth['paramsBasic']['password']))
        pm_job_obj = objects.v2.pm_job.PmJobV2.get_by_id(
            self.context, pm_job_id)
        self.assertEqual(self.password,
                         pm_job_obj['metadata']['monitoring']['targetsInfo']
                                   [0]['authInfo']['ssh_password'])
        self.assertEqual(self.password,
                         pm_job_obj['authentication']['paramsBasic']
                                   ['password'])

        # check show pm job
        resp, body = self.show_pm_job(pm_job_id)
        self.assertIsNone(body.get('authentication', None))
        self.assertIsNone(body.get('metadata', None))

        # 10. Create PM Threshold
        # Normally only CNF is used for PM Threshold, but VNF is also
        # acceptable for DB registration tests, so VNF is used for testing so
        # as not to increase the number of jobs.
        subsc_req = paramgen.pm_threshold_basic(
            callback_uri, inst_id, self.fake_prometheus_ip,
            password=self.password
        )
        resp, body = self.create_pm_threshold(subsc_req)
        self.assertEqual(201, resp.status_code)
        pm_threshold_id = body.get('id')

        # check encrypt ThresholdV2
        pm_threshold = self._get_pm_threshold_by_id(
            self.context, pm_threshold_id)
        self.assertEqual(self.password,
                         crypt_utils.decrypt(pm_threshold['metadata__']
                                                         ['monitoring']
                                                         ['targetsInfo'][0]
                                                         ['authInfo']
                                                         ['ssh_password']))
        auth = jsonutils.loads(pm_threshold['authentication'])
        self.assertEqual(self.password,
                         crypt_utils.decrypt(auth['paramsBasic']['password']))
        pm_threshold_obj = objects.v2.threshold.ThresholdV2.get_by_id(
            self.context, pm_threshold_id)
        self.assertEqual(self.password,
                         pm_threshold_obj['metadata']['monitoring']
                                         ['targetsInfo'][0]['authInfo']
                                         ['ssh_password'])
        self.assertEqual(self.password,
                         pm_threshold_obj['authentication']
                                         ['paramsBasic']['password'])

        # check show pm threshold
        resp, body = self.show_pm_threshold(pm_threshold_id)
        self.assertIsNone(body.get('authentication', None))
        self.assertIsNone(body.get('metadata', None))

        # 11. Create FM Subscription
        # Normally only CNF is used for FM Subscription, but VNF is also
        # acceptable for DB registration tests, so VNF is used for testing so
        # as not to increase the number of jobs.
        subsc_req = paramgen.sub_create_basic(callback_uri, self.password)
        resp, body = self.create_fm_subscription(subsc_req)
        self.assertEqual(201, resp.status_code)
        subsc_id = body['id']

        # check encrypt FmSubscriptionV1
        fm_subsc = self._get_fm_subscription_by_id(self.context, subsc_id)
        auth = jsonutils.loads(fm_subsc['authentication'])
        self.assertEqual(self.password,
                         crypt_utils.decrypt(auth['paramsBasic']['password']))
        fm_subsc_obj = objects.v1.fm_subscription.FmSubscriptionV1.get_by_id(
            self.context, subsc_id)
        self.assertEqual(self.password,
                         fm_subsc_obj['authentication']
                         ['paramsBasic']['password'])

        # check show fm subscription
        resp, body = self.show_fm_subscription(subsc_id)
        self.assertIsNone(body.get('authentication', None))

        # 12. Delete FM Subscription
        resp, body = self.delete_fm_subscription(subsc_id)
        self.assertEqual(204, resp.status_code)

        # 13. Delete PM Threshold
        resp, body = self.delete_pm_threshold(pm_threshold_id)
        self.assertEqual(204, resp.status_code)

        # 14. Delete PM Job
        resp, body = self.delete_pm_job(pm_job_id)
        self.assertEqual(204, resp.status_code)

        # 15. Terminate VNF instance
        terminate_req = paramgen.terminate_vnf_min()
        resp, body = self.terminate_vnf_instance(inst_id, terminate_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 16. Delete VNF instance
        resp, body = self.exec_lcm_operation(self.delete_vnf_instance, inst_id)
        self.assertEqual(204, resp.status_code)

        # 17. Delete subscription
        resp, body = self.delete_subscription(sub_id)
        self.assertEqual(204, resp.status_code)

    def test_encrypt_vnflcm_subsc_oauth2(self):
        """Test encrypt LCM operations for subscription with oauth2.0 auth

        * FT-checkpoints:
          This FT confirms the following points.
          - That the data retrieved directly from the DB is encrypted.
          - That the data retrieved from DB via object is automatically
            decrypted.

        * About LCM operations:
          This test includes the following operations.
          - 1. Create subscription
          - 2. Create VNF instance
          - 3. Instantiate VNF instance
          - 4. Create PM Job
          - 5. Create PM Threshold
          - 6. Create FM Subscription
          - 7. Delete FM Subscription
          - 8. Delete PM Threshold
          - 9. Delete PM Job
          - 10. Terminate VNF instance
          - 11. Delete VNF instance
          - 12. Delete subscription
        """

        # setup
        basic_lcms_min_path = utils.test_sample("functional/sol_v2_common",
                                                "basic_lcms_min")
        min_zip_path, min_vnfd_id = self.create_vnf_package(
            basic_lcms_min_path, nfvo=True)

        vnfd_path = "contents/Definitions/v2_sample2_df_simple.yaml"
        self._register_vnf_package_mock_response(min_vnfd_id,
                                                 min_zip_path)

        glance_image = fake_grant_v2.GrantV2.get_sw_image(
            basic_lcms_min_path, vnfd_path)
        flavour_vdu_dict = fake_grant_v2.GrantV2.get_compute_flavor(
            basic_lcms_min_path, vnfd_path)

        zone_name_list = self.get_zone_list()
        create_req = paramgen.create_vnf_min(min_vnfd_id)

        # 1. Create subscription
        callback_url = os.path.join(self.get_notify_callback_url(),
                                    self._testMethodName)
        callback_uri = ('https://localhost:'
                        f'{self.get_server_port()}'
                        f'{callback_url}')
        sub_req = paramgen.sub_create_oauth2(callback_uri, self.password)
        resp, body = self.create_subscription(sub_req)
        self.assertEqual(201, resp.status_code)
        sub_id = body['id']

        # check encrypt LccnSubscriptionV2
        subsc = self._get_lccn_subscription_by_id(self.context, sub_id)
        auth = jsonutils.loads(subsc['authentication'])
        self.assertEqual(self.password,
                         crypt_utils.decrypt(auth
                                             ['paramsOauth2ClientCredentials']
                                             ['clientPassword']))
        subsc_obj = objects.v2.lccn_subscription.LccnSubscriptionV2.get_by_id(
            self.context, sub_id)
        self.assertEqual(self.password,
                         subsc_obj['authentication']
                                  ['paramsOauth2ClientCredentials']
                                  ['clientPassword'])

        # check show LccnSubscriptionV2
        resp, body = self.show_subscription(sub_id)
        self.assertIsNone(body.get('authentication', None))

        # 2. Create VNF instance
        resp, body = self.create_vnf_instance(create_req)
        self.assertEqual(201, resp.status_code)
        inst_id = body['id']

        # 3. Instantiate VNF instance
        self._set_grant_response(
            True, 'INSTANTIATE', glance_image=glance_image,
            flavour_vdu_dict=flavour_vdu_dict, zone_name_list=zone_name_list,
            password=self.password)
        instantiate_req = paramgen.instantiate_vnf(
            self.auth_url, self.password)
        resp, body = self.instantiate_vnf_instance(inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 4. Create PM Job
        # Normally only CNF is used for PM jobs, but VNF is also acceptable for
        # DB registration tests, so VNF is used for testing so as not to
        # increase the number of jobs.
        callback_url = os.path.join(self.get_notify_callback_url(),
                                    self._testMethodName)
        callback_uri = ('https://localhost:'
                        f'{self.get_server_port()}'
                        f'{callback_url}')
        sub_req = paramgen.pm_job_oauth2(
            callback_uri, inst_id, self.fake_prometheus_ip, self.password)
        resp, body = self.create_pm_job(sub_req)
        self.assertEqual(201, resp.status_code)
        pm_job_id = body.get('id')

        # check encrypt PmJobV2
        pm_job = self._get_pm_job_by_id(self.context, pm_job_id)
        self.assertEqual(self.password,
                         crypt_utils.decrypt(pm_job['metadata__']['monitoring']
                                                   ['targetsInfo'][0]
                                                   ['authInfo']
                                                   ['ssh_password']))
        auth = jsonutils.loads(pm_job['authentication'])
        self.assertEqual(self.password,
                         crypt_utils.decrypt(auth
                                             ['paramsOauth2ClientCredentials']
                                             ['clientPassword']))
        pm_job_obj = objects.v2.pm_job.PmJobV2.get_by_id(
            self.context, pm_job_id)
        self.assertEqual(self.password,
                         pm_job_obj['metadata']['monitoring']['targetsInfo']
                                   [0]['authInfo']['ssh_password'])
        self.assertEqual(self.password,
                         pm_job_obj['authentication']
                                   ['paramsOauth2ClientCredentials']
                                   ['clientPassword'])

        # check show pm job
        resp, body = self.show_pm_job(pm_job_id)
        self.assertIsNone(body.get('authentication', None))
        self.assertIsNone(body.get('metadata', None))

        # 5. Create PM Threshold
        # Normally only CNF is used for PM Threshold, but VNF is also
        # acceptable for DB registration tests, so VNF is used for testing so
        # as not to increase the number of jobs.
        subsc_req = paramgen.pm_threshold_oauth2(
            callback_uri, inst_id, self.fake_prometheus_ip,
            password=self.password
        )
        resp, body = self.create_pm_threshold(subsc_req)
        self.assertEqual(201, resp.status_code)
        pm_threshold_id = body.get('id')

        # check encrypt ThresholdV2
        pm_threshold = self._get_pm_threshold_by_id(
            self.context, pm_threshold_id)
        self.assertEqual(self.password,
                         crypt_utils.decrypt(pm_threshold['metadata__']
                                                         ['monitoring']
                                                         ['targetsInfo'][0]
                                                         ['authInfo']
                                                         ['ssh_password']))
        auth = jsonutils.loads(pm_threshold['authentication'])
        self.assertEqual(self.password,
                         crypt_utils.decrypt(auth
                                             ['paramsOauth2ClientCredentials']
                                             ['clientPassword']))
        pm_threshold_obj = objects.v2.threshold.ThresholdV2.get_by_id(
            self.context, pm_threshold_id)
        self.assertEqual(self.password,
                         pm_threshold_obj['metadata']['monitoring']
                                         ['targetsInfo'][0]['authInfo']
                                         ['ssh_password'])
        self.assertEqual(self.password,
                         pm_threshold_obj['authentication']
                                         ['paramsOauth2ClientCredentials']
                                         ['clientPassword'])

        # check show pm threshold
        resp, body = self.show_pm_threshold(pm_threshold_id)
        self.assertIsNone(body.get('authentication', None))
        self.assertIsNone(body.get('metadata', None))

        # 6. Create FM Subscription
        # Normally only CNF is used for FM Subscription, but VNF is also
        # acceptable for DB registration tests, so VNF is used for testing so
        # as not to increase the number of jobs.
        subsc_req = paramgen.sub_create_oauth2(callback_uri, self.password)
        resp, body = self.create_fm_subscription(subsc_req)
        self.assertEqual(201, resp.status_code)
        subsc_id = body['id']

        # check encrypt FmSubscriptionV1
        fm_subsc = self._get_fm_subscription_by_id(self.context, subsc_id)
        auth = jsonutils.loads(fm_subsc['authentication'])
        self.assertEqual(self.password,
                         crypt_utils.decrypt(auth
                                             ['paramsOauth2ClientCredentials']
                                             ['clientPassword']))
        fm_subsc_obj = objects.v1.fm_subscription.FmSubscriptionV1.get_by_id(
            self.context, subsc_id)
        self.assertEqual(self.password,
                         fm_subsc_obj['authentication']
                                     ['paramsOauth2ClientCredentials']
                                     ['clientPassword'])

        # check show fm subscription
        resp, body = self.show_fm_subscription(subsc_id)
        self.assertIsNone(body.get('authentication', None))

        # 7. Delete FM Subscription
        resp, body = self.delete_fm_subscription(subsc_id)
        self.assertEqual(204, resp.status_code)

        # 8. Delete PM Threshold
        resp, body = self.delete_pm_threshold(pm_threshold_id)
        self.assertEqual(204, resp.status_code)

        # 9. Delete PM Job
        resp, body = self.delete_pm_job(pm_job_id)
        self.assertEqual(204, resp.status_code)

        # 10. Terminate VNF instance
        terminate_req = paramgen.terminate_vnf_min()
        resp, body = self.terminate_vnf_instance(inst_id, terminate_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 11. Delete VNF instance
        resp, body = self.exec_lcm_operation(self.delete_vnf_instance, inst_id)
        self.assertEqual(204, resp.status_code)

        # 12. Delete subscription
        resp, body = self.delete_subscription(sub_id)
        self.assertEqual(204, resp.status_code)

    def test_encrypt_grant(self):
        """Test encrypt LCM operations for grant

        * FT-checkpoints:
          This FT confirms the following points.
          - That the data retrieved directly from the DB is encrypted.
          - That the data retrieved from DB via object is automatically
            decrypted.

        * About LCM operations:
          This test includes the following operations.
          - 1. Create VNF instance
          - 2. Instantiate VNF (will fail)
          - 3. Rollback instantiation operation
          - 4. Delete VNF instance
        """
        # setup
        error_network_path = utils.test_sample("functional/sol_v2_common",
                                               "error_network")
        err_vnf_pkg, err_vnfd_id = self.create_vnf_package(
            error_network_path, nfvo=True)

        vnfd_path = "contents/Definitions/v2_sample2_df_simple.yaml"

        self._register_vnf_package_mock_response(
            err_vnfd_id, err_vnf_pkg)
        glance_image = fake_grant_v2.GrantV2.get_sw_image(
            error_network_path, vnfd_path)
        flavour_vdu_dict = fake_grant_v2.GrantV2.get_compute_flavor(
            error_network_path, vnfd_path)
        zone_name_list = self.get_zone_list()

        # 1. Create VNF instance
        create_req = paramgen.create_vnf_min(err_vnfd_id)
        resp, body = self.create_vnf_instance(create_req)
        self.assertEqual(201, resp.status_code)
        inst_id = body['id']

        # 2. Instantiate VNF (will fail)
        self._set_grant_response(
            True, 'INSTANTIATE', glance_image=glance_image,
            flavour_vdu_dict=flavour_vdu_dict, zone_name_list=zone_name_list,
            password=self.password)
        instantiate_req = paramgen.instantiate_vnf(
            self.auth_url, self.password)
        resp, body = self.instantiate_vnf_instance(inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_failed_temp(lcmocc_id)

        opocc = self._get_vnflcm_op_occs_by_id(self.context, lcmocc_id)
        grant = self._get_grant_by_id(self.context, lcmocc_id)

        # check encrypted GrantV2
        grant_vim_conn = grant['vimConnectionInfo']
        dict_grant_vim_conn = jsonutils.loads(grant_vim_conn)
        for cred_key in self.CRYPT_AUTH_KEYS:
            self.assertEqual(
                self.password,
                crypt_utils.decrypt(dict_grant_vim_conn['vim1']['accessInfo']
                                    [cred_key]))
        grant_obj = objects.v1.grant.GrantV1.get_by_id(
            self.context, opocc['grantId'])
        for cred_key in self.CRYPT_AUTH_KEYS:
            self.assertEqual(
                self.password,
                grant_obj['vimConnectionInfo']['vim1']['accessInfo']
                         [cred_key])

        # 3. Rollback instantiation operation
        resp, body = self.rollback_lcmocc(lcmocc_id)
        self.assertEqual(202, resp.status_code)
        self.wait_lcmocc_rolled_back(lcmocc_id)

        # 4. Delete VNF instance
        resp, body = self.delete_vnf_instance(inst_id)
        self.assertEqual(204, resp.status_code)
