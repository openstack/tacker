# Copyright (C) 2022 NEC, Corp.
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

from oslo_serialization import jsonutils
from oslo_utils import uuidutils
from tacker.tests.compliance import base as rootbase
from tacker.tests.compliance.sol002 import base


class BaseVNFLifecycleManagementTest(base.BaseComplSolTest):
    @classmethod
    def setUpClass(cls):
        cls.api = 'VNFLifecycleManagement-API'

        super(BaseVNFLifecycleManagementTest, cls).setUpClass()

        cls.vnfpkginfos = cls._create_and_upload_vnf_packages(['vnflcm1'])

    @classmethod
    def tearDownClass(cls):
        cls._disable_and_delete_vnf_packages(cls.vnfpkginfos)

        super(BaseVNFLifecycleManagementTest, cls).tearDownClass()


class BaseVNFLifecycleManagementScaleTest(base.BaseComplSolTest):
    @classmethod
    def setUpClass(cls):
        cls.api = 'VNFLifecycleManagement-API'

        super(BaseVNFLifecycleManagementScaleTest, cls).setUpClass()

        cls.vnfpkginfos = cls._create_and_upload_vnf_packages(
            ['sample_compliance_test'])

    @classmethod
    def tearDownClass(cls):
        cls._disable_and_delete_vnf_packages(cls.vnfpkginfos)

        super(BaseVNFLifecycleManagementScaleTest, cls).tearDownClass()


class VNFInstancesTest(BaseVNFLifecycleManagementTest):
    @classmethod
    def setUpClass(cls):
        cls.resource = 'VNFInstances'

        super(VNFInstancesTest, cls).setUpClass()

    def test_post_create_new_vnfinstance(self):

        # Pre-conditions:
        body = jsonutils.dumps({"vnfdId": "%s" % self.vnfpkginfos[0].vnfdid,
            "vnfInstanceName": "sol_api_test"})

        rc, output = self._run('POST Create a new vnfInstance', body=body,
            filename='createVnfRequest.json')

        # Post-Conditions: VNF instance created
        vnfid = self._get_id_from_output(output)
        if (vnfid is not None):
            self._delete_vnf_instance(vnfid)

        self.assertEqual(0, rc)

    def test_get_information_about_multiple_vnf_instances(self):

        # Pre-conditions:
        res, vnf = self._create_vnf_instance(self.vnfpkginfos[0].vnfdid)

        rc, output = self._run('GET information about multiple VNF instances')

        # Post-Conditions:
        self._delete_vnf_instance(vnf['id'])

        self.assertEqual(0, rc)


class IndividualVNFInstanceTest(BaseVNFLifecycleManagementTest):
    @classmethod
    def setUpClass(cls):
        cls.resource = 'IndividualVNFInstance'

        super(IndividualVNFInstanceTest, cls).setUpClass()

    def test_get_information_about_individual_vnf_instance(self):
        # Pre-conditions: none
        res, vnf = self._create_vnf_instance(self.vnfpkginfos[0].vnfdid,
            description="testvnf")

        variables = ['vnfInstanceId:' + vnf['id']]
        rc, output = self._run(
            'GET Information about an individual VNF Instance', variables)

        # Post-Conditions:
        self._delete_vnf_instance(vnf['id'])

        self.assertEqual(0, rc)

    def test_delete_individual_vnfinstance(self):
        # Pre-conditions: none
        res, vnf = self._create_vnf_instance(self.vnfpkginfos[0].vnfdid)

        variables = ['vnfInstanceId:' + vnf['id']]
        rc, output = self._run('DELETE Individual VNFInstance', variables)

        # Post-Conditions: VNF instance deleted

        self.assertEqual(0, rc)

    def test_modify_information_about_individual_vnf_instance(self):
        # Pre-conditions: none
        res, vnf = self._create_vnf_instance(self.vnfpkginfos[0].vnfdid)
        vnfid = vnf['id']
        variables = ['vnfInstanceId:' + vnfid]

        body = rootbase.PATCH_BODY
        body['vnfInstanceName'] = "modify_test"
        body['vnfInstanceDescription'] = "sample_testcode"

        rc, output = self._run('PATCH Individual VNFInstance',
            variables=variables,
            body=jsonutils.dumps(body))

        # Post-Conditions:
        self._delete_vnf_instance(vnfid)

        self.assertEqual(0, rc)


class InstantiateVNFTaskTest(BaseVNFLifecycleManagementTest):
    @classmethod
    def setUpClass(cls):
        cls.resource = 'InstantiateVNFTask'

        super(InstantiateVNFTaskTest, cls).setUpClass()

    def test_post_instantiate_vnfinstance(self):
        # Pre-conditions: none
        res, vnf = self._create_vnf_instance(self.vnfpkginfos[0].vnfdid)

        variables = ['vnfInstanceId:' + vnf['id']]

        body = rootbase.INSTANTIATION_BODY

        body['extVirtualLinks'][0]['resourceId'] = self.net0_id
        body['vimConnectionInfo'][0]['id'] = uuidutils.generate_uuid()
        body['vimConnectionInfo'][0]['vimId'] = self.vimid

        rc, output = self._run('POST Instantiate a vnfInstance',
            variables=variables,
            body=jsonutils.dumps(body),
            filename='instantiateVnfRequest.json')

        # Post-Conditions:
        self._wait_vnf_status(vnf['id'], 'instantiationState', 'INSTANTIATED')
        self._terminate_vnf_instance(vnf['id'])
        self._delete_vnf_instance(vnf['id'])

        self.assertEqual(0, rc)


class TerminateVNFTaskTest(BaseVNFLifecycleManagementTest):
    @classmethod
    def setUpClass(cls):
        cls.resource = 'TerminateVNFTask'

        super(TerminateVNFTaskTest, cls).setUpClass()

    def test_post_terminate_vnfinstance(self):
        # Pre-conditions: none
        res, vnf = self._create_vnf_instance(self.vnfpkginfos[0].vnfdid)

        self._instantiate_vnf_instance(vnf['id'])

        variables = ['vnfInstanceId:' + vnf['id']]

        rc, output = self._run('POST Terminate a vnfInstance',
            variables=variables,
            body=jsonutils.dumps(rootbase.TERMINATION_BODY),
            filename='terminateVnfRequest.json')

        # Post-Conditions:
        self._wait_vnf_status(vnf['id'], 'instantiationState',
            'NOT_INSTANTIATED')
        self._delete_vnf_instance(vnf['id'])

        self.assertEqual(0, rc)


class ScaleVNFTaskTest(BaseVNFLifecycleManagementScaleTest):
    @classmethod
    def setUpClass(cls):
        cls.resource = 'ScaleVNFTask'

        super(ScaleVNFTaskTest, cls).setUpClass()

    def test_post_expand_by_scaleout(self):
        # Pre-conditions: none
        res, vnf = self._create_vnf_instance(self.vnfpkginfos[0].vnfdid)

        self._instantiate_vnf_instance_for_scale(vnf['id'])

        variables = ['vnfInstanceId:' + vnf['id']]
        body = rootbase.SCALE_BODY
        body['type'] = 'SCALE_OUT'

        rc, output = self._run('POST Scale a vnfInstance',
            variables=variables,
            body=jsonutils.dumps(body),
            filename='scaleVnfRequest.json')

        res = self._get_responses_from_output(output)

        # Post-Conditions:
        lcmid = self._get_lcm_op_occs_id(vnf['id'], lcm='SCALE')
        res = self._wait_lcm_status(lcmid)
        self.assertEqual(0, res)

        self.assertEqual(0, rc)

    def test_post_reduce_by_scalein(self):
        vnf_id = self._get_vnf_instance_id()

        body = rootbase.SCALE_BODY
        body['type'] = 'SCALE_IN'

        rc, output = self._run('POST Scale a vnfInstance',
            variables=['vnfInstanceId:' + vnf_id],
            body=jsonutils.dumps(body),
            filename='scaleVnfRequest.json')

        res = self._get_responses_from_output(output)

        # Post-Conditions:
        lcmid = self._get_lcm_op_occs_id(vnf_id, lcm='SCALE')
        res = self._wait_lcm_status(lcmid)
        self.assertEqual(0, res)
        self._terminate_vnf_instance(vnf_id)
        self._delete_vnf_instance(vnf_id)

        self.assertEqual(0, rc)


class CreateAndGetSubscriptionsTest(BaseVNFLifecycleManagementTest):
    @classmethod
    def setUpClass(cls):

        cls.resource = 'Subscriptions'

        super(CreateAndGetSubscriptionsTest, cls).setUpClass()

    def test_create_subscription(self):

        # Pre-conditions: none
        body = rootbase.SUBSCRIPTION_BODY

        body['filter']['vnfInstanceSubscriptionFilter']['vnfdIds'] = \
            [self.vnfpkginfos[0].vnfdid]

        rc, output = self._run('POST Create a new subscription',
            body=jsonutils.dumps(body),
            filename='lccnSubscriptionRequest.json')

        self.assertEqual(0, rc)

    def test_get_subscriptions(self):

        # Pre-conditions: none
        rc, output = self._run('GET Subscriptions')

        self.assertEqual(0, rc)


class IndividualSubscriptionTest(BaseVNFLifecycleManagementTest):
    @classmethod
    def setUpClass(cls):
        cls.resource = 'IndividualSubscription'

        super(IndividualSubscriptionTest, cls).setUpClass()

    def test_get_individual_subscription(self):

        # Pre-conditions: none
        subscid = self._get_subscription_id()
        variables = ['subscriptionId:' + subscid]

        rc, output = self._run('GET Individual Subscription',
            variables=variables)

        self.assertEqual(0, rc)

    def test_remove_individual_subscription(self):

        # Pre-conditions: none
        subscid = self._get_subscription_id()

        variables = ['subscriptionId:' + subscid]

        rc, output = self._run('DELETE an individual subscription',
            variables=variables)

        self.assertEqual(0, rc)


class HealVNFTaskTest(BaseVNFLifecycleManagementTest):
    @classmethod
    def setUpClass(cls):
        cls.resource = 'HealVNFTask'

        super(HealVNFTaskTest, cls).setUpClass()

    def test_post_heal_vnfinstance(self):
        # Pre-conditions: none
        res, vnf = self._create_vnf_instance(self.vnfpkginfos[0].vnfdid)
        self._instantiate_vnf_instance(vnf['id'])

        variables = ['vnfInstanceId:' + vnf['id']]
        resbody = self._get_vnf_ind_instance(vnf['id'])
        body = rootbase.HEAL_BODY
        body['vnfcInstanceId'] = resbody.get('instantiated'
            'VnfInfo').get('vnfcResourceInfo')[0].get('id')

        rc, output = self._run('POST Heal a vnfInstance',
            variables=variables,
            body=jsonutils.dumps(body),
            filename=' healVnfRequest.json')

        # Post-Conditions:
        lcmid = self._get_lcm_op_occs_id(vnf['id'], lcm='HEAL')
        res = self._wait_lcm_status(lcmid)
        self.assertEqual(0, res)
        self._terminate_vnf_instance(vnf['id'])
        self._delete_vnf_instance(vnf['id'])

        self.assertEqual(0, rc)


class RetryOperationTaskTest(BaseVNFLifecycleManagementTest):
    @classmethod
    def setUpClass(cls):
        cls.resource = 'RetryOperationTask'

        super(RetryOperationTaskTest, cls).setUpClass()

    def test_post_retry_operation(self):
        # Pre-conditions: none
        res, vnf = self._create_vnf_instance(self.vnfpkginfos[0].vnfdid)
        self._instantiate_error_vnf_instance(vnf['id'])
        lcmid = self._get_lcm_op_occs_id(vnf['id'])

        variables = ['vnfLcmOpOccId:' + lcmid]

        rc, output = self._run('Post Retry operation task',
            variables=variables)

        # Post-Conditions:
        res = self._wait_lcm_status(lcmid, value='FAILED_TEMP')
        self.assertEqual(0, res)
        self._terminate_vnf_instance(vnf['id'])
        self._delete_vnf_instance(vnf['id'])

        self.assertEqual(1, rc)


class ChangeExternalVNFConnectivityTaskTest(BaseVNFLifecycleManagementTest):
    @classmethod
    def setUpClass(cls):
        cls.resource = 'ChangeExternalVNFConnectivityTask'

        super(ChangeExternalVNFConnectivityTaskTest, cls).setUpClass()

    def test_post_chgextconn_vnfinstance(self):

        # Pre-conditions: none
        res, vnf = self._create_vnf_instance(self.vnfpkginfos[0].vnfdid)

        self._instantiate_vnf_instance(vnf['id'])

        variables = ['vnfInstanceId:' + vnf['id']]

        resbody = self._get_vnf_ind_instance(vnf['id'])

        body = rootbase.CHG_EXT_CONN_BODY
        body['extVirtualLinks'][0]['resourceId'] = resbody.get('instantiated'
            'VnfInfo').get('extVirtualLinkInfo')[0].get('resource'
            'Handle').get('resourceId')

        rc, output = self._run('POST Change external VNF connectivity',
            variables=variables,
            body=jsonutils.dumps(body),
            filename='changeExtVnfConnectivityRequest.json')

        # Post-Conditions:
        lcmid = self._get_lcm_op_occs_id(vnf['id'], lcm='CHANGE_EXT_CONN')
        res = self._wait_lcm_status(lcmid)
        self.assertEqual(0, res)
        self._terminate_vnf_instance(vnf['id'])
        self._delete_vnf_instance(vnf['id'])

        self.assertEqual(0, rc)
