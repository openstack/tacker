#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
import os
import tempfile
import time
from urllib.parse import urlparse
import yaml
import zipfile

from oslo_serialization import jsonutils
from oslo_utils import uuidutils

from tacker.objects import fields
from tacker.tests.functional import base
from tacker.tests.functional.common.fake_server import FakeServerManager
from tacker.tests import utils
from tacker.vnfm.infra_drivers.openstack import constants as infra_cnst


VNF_PACKAGE_UPLOAD_TIMEOUT = 60
VNF_INSTANTIATE_TIMEOUT = 60
VNF_TERMINATE_TIMEOUT = 60
VNF_SUBSCRIPTION_TIMEOUT = 60
VNF_INSTANTIATE_ERROR_WAIT = 80
VNF_DELETE_COMPLETION_WAIT = 60
VNF_HEAL_TIMEOUT = 600
VNF_LCM_DONE_TIMEOUT = 600
RETRY_WAIT_TIME = 5
FAKE_SERVER_MANAGER = FakeServerManager.get_instance()
MOCK_NOTIFY_CALLBACK_URL = '/notification/callback'
UUID_RE = r'\w{8}-\w{4}-\w{4}-\w{4}-\w{12}'


def _get_external_virtual_links(net0_id):
    return [
        {
            "id": "net0",
            "resourceId": net0_id,
            "extCps": [{
                "cpdId": "CP1",
                "cpConfig": [{
                    "cpProtocolData": [{
                        "layerProtocol": "IP_OVER_ETHERNET",
                    }]
                }]
            }]
        }
    ]


def _create_csar_user_data_common(csar_dir):
    ud_common_dir = os.path.join(csar_dir, "../user_data_common/")
    return _create_csar_with_unique_vnfd_id(
        csar_dir, ud_common_dir)


def _create_csar_with_unique_vnfd_id(csar_dir, *include_dirs):
    tempfd, tempname = tempfile.mkstemp(suffix=".zip",
        dir=os.path.dirname(csar_dir))
    os.close(tempfd)

    common_dir = os.path.join(csar_dir, "../common/")
    target_dirs = [csar_dir, common_dir]
    target_dirs.extend(include_dirs)

    unique_id = uuidutils.generate_uuid()
    with zipfile.ZipFile(tempname, 'w') as zcsar:
        _write_zipfile(zcsar, unique_id, target_dirs)

    return tempname, unique_id


def _write_zipfile(zcsar, unique_id, target_dir_list):
    for target_dir in target_dir_list:
        for (dpath, _, fnames) in os.walk(target_dir):
            if not fnames:
                continue
            for fname in fnames:
                src_file = os.path.join(dpath, fname)
                dst_file = os.path.relpath(
                    os.path.join(dpath, fname), target_dir)
                if fname.endswith('.yaml') or fname.endswith('.yml'):
                    with open(src_file, 'rb') as yfile:
                        data = yaml.safe_load(yfile)
                        utils._update_unique_id_in_yaml(data, unique_id)
                        zcsar.writestr(dst_file, yaml.dump(
                            data, default_flow_style=False,
                            allow_unicode=True))
                else:
                    zcsar.write(src_file, dst_file)


def _create_and_upload_vnf_package(
        tacker_client,
        user_defined_data,
        temp_csar_path):
    # create vnf package
    body = jsonutils.dumps({"userDefinedData": user_defined_data})
    resp, vnf_package = tacker_client.do_request(
        '/vnfpkgm/v1/vnf_packages', "POST", body=body)

    with open(temp_csar_path, 'rb') as file_object:
        resp, resp_body = tacker_client.do_request(
            '/vnfpkgm/v1/vnf_packages/{id}/package_content'.format(
                id=vnf_package['id']),
            "PUT", body=file_object, content_type='application/zip')

    # wait for onboard
    timeout = VNF_PACKAGE_UPLOAD_TIMEOUT
    start_time = int(time.time())
    show_url = os.path.join('/vnfpkgm/v1/vnf_packages', vnf_package['id'])
    vnfd_id = None
    while True:
        resp, body = tacker_client.do_request(show_url, "GET")
        if body['onboardingState'] == "ONBOARDED":
            vnfd_id = body['vnfdId']
            break

        if ((int(time.time()) - start_time) > timeout):
            raise Exception("Failed to onboard vnf package")

        time.sleep(1)

    # remove temporarily created CSAR file
    os.remove(temp_csar_path)
    return vnf_package['id'], vnfd_id


def _delete_vnf_package(tacker_client, vnf_package_id):
    url = '/vnfpkgm/v1/vnf_packages/%s' % vnf_package_id

    # Update vnf package before delete
    req_body = jsonutils.dumps({"operationalState": "DISABLED"})
    tacker_client.do_request(url, "PATCH", body=req_body)

    # Delete vnf package before delete
    tacker_client.do_request(url, "DELETE")


def _show_vnf_package(tacker_client, vnf_package_id):
    # wait for onboard
    timeout = VNF_PACKAGE_UPLOAD_TIMEOUT
    start_time = int(time.time())
    show_url = os.path.join('/vnfpkgm/v1/vnf_packages', vnf_package_id)
    while True:
        resp, body = tacker_client.do_request(show_url, "GET")
        if resp.ok:
            return resp, body

        if ((int(time.time()) - start_time) > timeout):
            raise Exception("Failed to onboard vnf package")

        time.sleep(1)


def _list_vnf_package(tacker_client, **kwargs):
    # wait for onboard
    timeout = VNF_PACKAGE_UPLOAD_TIMEOUT
    start_time = int(time.time())
    while True:
        resp, body = tacker_client.do_request(
            '/vnfpkgm/v1/vnf_packages', "GET", **kwargs)
        if resp.ok:
            return resp, body

        if ((int(time.time()) - start_time) > timeout):
            raise Exception("Failed to onboard vnf package")

        time.sleep(1)


def _create_instantiate_vnf_request_body(flavour_id,
        instantiation_level_id=None, vim_id=None, ext_vl=None,
        add_params=None):
    request_body = {"flavourId": flavour_id}

    if instantiation_level_id:
        request_body["instantiationLevelId"] = instantiation_level_id

    if ext_vl:
        request_body["extVirtualLinks"] = ext_vl

    if vim_id:
        request_body["vimConnectionInfo"] = [
            {"id": uuidutils.generate_uuid(),
                "vimId": vim_id,
                "vimType": "ETSINFV.OPENSTACK_KEYSTONE.v_2"}]

    if add_params:
        request_body["additionalParams"] = add_params

    return request_body


class BaseVnfLcmTest(base.BaseTackerTest):

    @classmethod
    def setUpClass(cls):
        '''Set up test class.

        we set up fake NFVO server for test at here.
        '''
        super(BaseVnfLcmTest, cls).setUpClass()
        FAKE_SERVER_MANAGER.prepare_http_server()
        FAKE_SERVER_MANAGER.start_server()

        FAKE_SERVER_MANAGER.set_callback(
            'POST',
            MOCK_NOTIFY_CALLBACK_URL,
            status_code=204
        )

    @classmethod
    def tearDownClass(cls):
        super(BaseVnfLcmTest, cls).tearDownClass()
        FAKE_SERVER_MANAGER.stop_server()

    def setUp(self):
        super(BaseVnfLcmTest, self).setUp()

        self.tacker_client = base.BaseTackerTest.tacker_http_client()

        self.base_vnf_instances_url = "/vnflcm/v1/vnf_instances"
        self.base_subscriptions_url = "/vnflcm/v1/subscriptions"
        self.base_vnf_lcm_op_occs_url = "/vnflcm/v1/vnf_lcm_op_occs"

        vim_list = self.client.list_vims()
        self.vim = self.get_vim(vim_list, 'VIM0')
        if not self.vim:
            assert False, "vim_list is Empty: Default VIM is missing"

        # Create external external.
        self.ext_networks = list()
        # Create external managed networks
        self.ext_mngd_networks = list()  # Store ids for cleaning.

        networks = self.neutronclient().list_networks()
        for nw in networks.get('networks'):
            if nw['name'] == 'net0':
                self.ext_networks.append(nw['id'])
            elif nw['name'] == 'net1':
                self.ext_mngd_networks.append(nw['id'])

        # create new network.
        self.ext_networks.append(
            self._create_network("external_net"))
        self.ext_mngd_networks.append(
            self._create_network("external_managed_internal_net"))

        # Create external link ports in net0
        self.ext_link_ports = list()
        # Create external subnet in net1
        self.ext_subnets = list()  # Store ids for cleaning.

        # Chack how many networks are created.
        networks = self.neutronclient().list_networks()
        for nw in networks.get('networks'):
            if nw['name'] not in ['net0', 'external_net']:
                continue
            if self.vim['tenant_id'] != nw['tenant_id']:
                continue

            self.ext_networks.append(nw['id'])
            self.ext_link_ports.append(self._create_port(nw['id']))
            self.ext_subnets.append(self._create_subnet(nw))

    @classmethod
    def _list_glance_image(cls, filter_name='cirros-0.4.0-x86_64-disk'):
        try:
            images = cls.glance_client.images.list()
        except Exception:
            print("glance-image does not exists.")
            return []

        if filter_name is None:
            return images

        return list(filter(lambda image: image.name == filter_name, images))

    @classmethod
    def _get_glance_image(cls, image_id):
        try:
            image = cls.glance_client.images.get(image_id)
        except Exception:
            print("glance-image does not exists.")
            return None

        return image

    @classmethod
    def _create_glance_image(cls, image_data, file_url):
        image = cls.glance_client.images.create(**image_data)
        cls.glance_client.images.upload(image.id, file_url)

        return image.id

    def _get_glance_image_list_from_stack_resource(
            self, stack_id, stack_resource_name):
        image_id_list = []
        for resource_name in stack_resource_name:
            resource_details = self._get_heat_resource(stack_id, resource_name)
            image = self._get_image_id_from_resource_attributes(
                resource_details)
            if image:
                image_id_list.append(image.id)

        return image_id_list

    def _register_subscription(self, request_body):
        resp, response_body = self.http_client.do_request(
            self.base_subscriptions_url,
            "POST",
            body=jsonutils.dumps(request_body))
        return resp, response_body

    def _delete_subscription(self, subscription_id):
        delete_url = os.path.join(self.base_subscriptions_url, subscription_id)
        resp, body = self.tacker_client.do_request(delete_url, "DELETE")

        return resp, body

    def _show_subscription(self, subscription_id):
        show_url = os.path.join(self.base_subscriptions_url, subscription_id)
        resp, body = self.tacker_client.do_request(show_url, "GET")

        return resp, body

    def _list_subscription(self):
        resp, body = self.tacker_client.do_request(
            self.base_subscriptions_url, "GET")

        return resp, body

    def _create_vnf_instance(self, vnfd_id, vnf_instance_name=None,
            vnf_instance_description=None):
        request_body = {'vnfdId': vnfd_id}
        if vnf_instance_name:
            request_body['vnfInstanceName'] = vnf_instance_name

        if vnf_instance_description:
            request_body['vnfInstanceDescription'] = vnf_instance_description

        return self._create_vnf_instance_from_body(request_body)

    def _create_vnf_instance_from_body(self, request_body):
        resp, response_body = self.http_client.do_request(
            self.base_vnf_instances_url,
            "POST",
            body=jsonutils.dumps(request_body))

        return resp, response_body

    def _delete_vnf_instance(self, id):
        url = os.path.join(self.base_vnf_instances_url, id)
        resp, body = self.http_client.do_request(url, "DELETE")

        return resp, body

    def _show_vnf_instance(self, id):
        show_url = os.path.join(self.base_vnf_instances_url, id)
        resp, vnf_instance = self.http_client.do_request(show_url, "GET")

        return resp, vnf_instance

    def _list_vnf_instance(self, **kwargs):
        resp, vnf_instances = self.http_client.do_request(
            self.base_vnf_instances_url, "GET")

        return resp, vnf_instances

    def _wait_vnf_instance(self, id,
            instantiation_state=fields.VnfInstanceState.INSTANTIATED,
            timeout=VNF_INSTANTIATE_TIMEOUT):
        start_time = int(time.time())
        while True:
            resp, body = self._show_vnf_instance(id)
            if body['instantiationState'] == instantiation_state:
                break

            if ((int(time.time()) - start_time) > timeout):
                error = ("Vnf instance %(id)s status is %(current)s, "
                         "expected status should be %(expected)s")
                self.fail(error % {"id": id,
                    "current": body['instantiationState'],
                    "expected": instantiation_state})

            time.sleep(5)

    def _instantiate_vnf_instance(self, id, request_body):
        url = os.path.join(self.base_vnf_instances_url, id, "instantiate")
        resp, body = self.http_client.do_request(url, "POST",
                body=jsonutils.dumps(request_body))

        return resp, body

    def _heal_vnf_instance(self, vnf_instance_id, request_body):
        url = \
            os.path.join(self.base_vnf_instances_url, vnf_instance_id, "heal")
        resp, body = self.http_client.do_request(url, "POST",
                body=jsonutils.dumps(request_body))

        return resp, body

    def _terminate_vnf_instance(self, id, request_body):
        url = os.path.join(self.base_vnf_instances_url, id, "terminate")
        resp, body = self.http_client.do_request(url, "POST",
                body=jsonutils.dumps(request_body))

        return resp, body

    def _wait_terminate_vnf_instance(self, id, timeout=None):
        start_time = int(time.time())

        self._wait_vnf_instance(id,
            instantiation_state=fields.VnfInstanceState.NOT_INSTANTIATED,
            timeout=timeout)

        # If gracefulTerminationTimeout is set, check whether vnf
        # instantiation_state is set to NOT_INSTANTIATED after
        # gracefulTerminationTimeout seconds.
        if timeout and int(time.time()) - start_time < timeout:
            self.fail("Vnf is terminated before graceful termination"
                      "timeout period")
        else:
            return

        # wait for status completion
        time.sleep(VNF_DELETE_COMPLETION_WAIT)

    def _get_heat_stack(self, vnf_instance_id, prefix_id='vnflcm_'):
        try:
            stacks = self.h_client.stacks.list()
        except Exception:
            print("heat-stacks does not exists.")
            return None

        target_stack_name = prefix_id + vnf_instance_id
        target_stakcs = list(
            filter(
                lambda x: x.stack_name == target_stack_name,
                stacks))

        if len(target_stakcs) == 0:
            return None

        return target_stakcs[0]

    def _get_heat_resource_list(self, stack_id, nested_depth=0):
        try:
            resources = self.h_client.resources.list(
                stack_id, nested_depth=nested_depth)
        except Exception:
            print("heat-stacks-resources does not exists.")
            return None

        return resources

    def _get_heat_resource(self, stack_id, resource_name):
        try:
            resource = self.h_client.resources.get(
                stack_id, resource_name)
        except Exception:
            print("heat-stacks-resource does not exists.")
            return None

        return resource

    def _get_image_id_from_resource_attributes(self, stack_resource_details):
        if stack_resource_details is None:
            return None
        if not hasattr(stack_resource_details, 'attributes'):
            return None

        return stack_resource_details.attributes.get('image', {}).get('id')

    def _get_vnfc_instance_id_list(
            self,
            stack_id,
            resource_type='OS::Nova::Server',
            nested_depth=2,
            limit=2):
        resources = self._get_heat_resource_list(
            stack_id, nested_depth=nested_depth)
        if resources is None:
            return None

        return [r.physical_resource_id for r in resources[:limit]
            if r.resource_type == resource_type]

    def assert_http_header_location_for_create(self, response_header):
        """Validate URI in location header for CreateVNF

        {apiRoot}/vnflcm/v1/vnf_instances/{vnfInstanceId}/instantiate
        """
        location = response_header.get(
            "Location") or response_header.get("location")
        self.assertIsNotNone(location)
        uri = urlparse(location)
        self.assertIn(uri.scheme, ['http', 'https'])
        self.assertRegex(
            uri.path,
            r'^/(?P<apiRoot>[^/]*?/)?vnflcm/v1/vnf_instances/' +
            UUID_RE)

    def assert_http_header_location_for_lcm_op_occs(self, response_header):
        """Validate URI in location header for various LCMs

        {apiRoot}/vnflcm/v1/vnf_lcm_op_occs/{vnfLcmOpOccId}
        """
        location = response_header.get(
            "Location") or response_header.get("location")
        self.assertIsNotNone(location)
        uri = urlparse(location)
        self.assertIn(uri.scheme, ['http', 'https'])
        self.assertRegex(
            uri.path,
            r'^/(?P<apiRoot>[^/]*?/)?vnflcm/v1/vnf_lcm_op_occs/' +
            UUID_RE)

    def assert_http_header_location_for_subscription(self, response_header):
        """Validate URI in location header for Subscription

        {apiRoot}/vnflcm/v1/subscriptions/{subscriptionId}
        """
        location = response_header.get(
            "Location") or response_header.get("location")
        self.assertIsNotNone(location)
        uri = urlparse(location)
        self.assertIn(uri.scheme, ['http', 'https'])
        self.assertRegex(
            uri.path,
            r'^/(?P<apiRoot>[^/]*?/)?vnflcm/v1/subscriptions/' +
            UUID_RE)

    def assert_instantiation_state(
            self,
            vnf_instance_body,
            expected_instantiation_state=fields.VnfInstanceState.INSTANTIATED):
        # FT-checkpoint: Instantiation state(VNF instance)
        self.assertEqual(
            expected_instantiation_state,
            vnf_instance_body['instantiationState'])

    def assert_vnf_state(
            self,
            vnf_instance_body,
            expected_vnf_state=fields.VnfOperationalStateType.STARTED):
        # FT-checkpoint: vnf_state
        self.assertEqual(
            expected_vnf_state,
            vnf_instance_body['instantiatedVnfInfo']['vnfState'])

    def assert_heat_stack_status(
            self,
            vnf_instance_id,
            expected_stack_status=infra_cnst.STACK_CREATE_COMPLETE):
        stack = self._get_heat_stack(vnf_instance_id)
        self.assertEqual(
            expected_stack_status,
            stack.stack_status)

    def assert_heat_resource_status(
            self,
            vnf_instance,
            expected_glance_image=None,
            expected_resource_status=None):

        def assert_glance_image(stack_id, resource_name):
            resource_details = self._get_heat_resource(stack_id, resource_name)
            image = self._get_image_id_from_resource_attributes(
                resource_details)
            if image:
                self.assertEqual(expected_glance_image, image.status)

        stack = self._get_heat_stack(vnf_instance['id'])
        resources = self._get_heat_resource_list(stack.id, 2)
        self.assertIsNotNone(resources)

        for resource in resources:
            # FT-checkpoint: resource status
            self.assertEqual(expected_resource_status,
                resource.resource_status)

            # FT-checkpoint: Glance-image
            if expected_glance_image:
                assert_glance_image(stack.id, resource.resource_name)

    def assert_heat_resource_status_is_none(
            self,
            stack_id,
            resources_name_list=None,
            glance_image_id_list=None):
        resources_name_list = resources_name_list or []
        for resource_name in resources_name_list:
            resource = self._get_heat_resource(stack_id, resource_name)
            self.assertIsNone(resource)

        glance_image_id_list = glance_image_id_list or []
        for glance_image_id in glance_image_id_list:
            image = self._get_glance_image(glance_image_id)
            self.assertIsNone(image)

    def _wait_lcm_done(self, expected_operation_status=None):
        start_time = int(time.time())
        while True:

            actual_status = None
            vnf_lcm_op_occ_id = None
            notify_mock_responses = FAKE_SERVER_MANAGER.get_history(
                MOCK_NOTIFY_CALLBACK_URL)
            for res in notify_mock_responses:

                if expected_operation_status is None:
                    return

                actual_status = res.request_body.get('operationState', '')
                vnf_lcm_op_occ_id = res.request_body.get('vnfLcmOpOccId', '')
                if actual_status == expected_operation_status:
                    return

            if ((int(time.time()) - start_time) > VNF_LCM_DONE_TIMEOUT):
                if actual_status:
                    error = (
                        "LCM incomplete timeout, %s is %s," +
                        "expected status should be %s")
                    self.fail(
                        error % {
                            "vnf_lcm_op_occ_id": vnf_lcm_op_occ_id,
                            "expected": expected_operation_status,
                            "actual": actual_status})
                else:
                    self.fail("LCM incomplete timeout")

            time.sleep(RETRY_WAIT_TIME)

    def _wait_stack_update(self, vnf_instance_id, expected_status):
        timeout = VNF_HEAL_TIMEOUT
        start_time = int(time.time())
        while True:
            stack = self._get_heat_stack(vnf_instance_id)
            if stack.stack_status == expected_status:
                break

            if ((int(time.time()) - start_time) > timeout):
                error = ("Stack %(id)s status is %(current)s, expected status "
                        "should be %(expected)s")
                self.fail(error % {"vnf_instance_name": vnf_instance_id,
                    "current": stack.status,
                    "expected": expected_status})

            time.sleep(RETRY_WAIT_TIME)

    def assert_create_vnf(self, resp, vnf_instance):
        self.assertEqual(201, resp.status_code)

        self.assert_http_header_location_for_create(resp.headers)
        self.assert_instantiation_state(
            vnf_instance,
            fields.VnfInstanceState.NOT_INSTANTIATED)

        # FT-checkpoint: Notification
        notify_mock_responses = FAKE_SERVER_MANAGER.get_history(
            MOCK_NOTIFY_CALLBACK_URL)
        FAKE_SERVER_MANAGER.clear_history(MOCK_NOTIFY_CALLBACK_URL)
        self.assertEqual(1, len(notify_mock_responses))
        self.assert_notification_mock_response(
            notify_mock_responses[0],
            'VnfIdentifierCreationNotification')

    def assert_delete_vnf(self, resp, vnf_instance_id):
        self.assertEqual(204, resp.status_code)

        resp, _ = self._show_vnf_instance(vnf_instance_id)
        self.assertEqual(404, resp.status_code)

        # FT-checkpoint: Notification
        notify_mock_responses = FAKE_SERVER_MANAGER.get_history(
            MOCK_NOTIFY_CALLBACK_URL)
        FAKE_SERVER_MANAGER.clear_history(MOCK_NOTIFY_CALLBACK_URL)
        self.assertEqual(1, len(notify_mock_responses))
        self.assert_notification_mock_response(
            notify_mock_responses[0],
            'VnfIdentifierDeletionNotification')

    def assert_instantiate_vnf(
            self,
            resp,
            vnf_instance_id):
        self.assertEqual(202, resp.status_code)
        resp, vnf_instance = self._show_vnf_instance(vnf_instance_id)
        self.assert_vnf_state(vnf_instance)

        self.assert_heat_stack_status(vnf_instance['id'])
        self.assert_heat_resource_status(
            vnf_instance,
            expected_glance_image='active',
            expected_resource_status='CREATE_COMPLETE')

        # FT-checkpoint: Notification
        notify_mock_responses = FAKE_SERVER_MANAGER.get_history(
            MOCK_NOTIFY_CALLBACK_URL)
        FAKE_SERVER_MANAGER.clear_history(MOCK_NOTIFY_CALLBACK_URL)

        self.assertEqual(3, len(notify_mock_responses))
        self.assert_notification_mock_response(
            notify_mock_responses[0],
            'VnfLcmOperationOccurrenceNotification',
            'STARTING')

        self.assert_notification_mock_response(
            notify_mock_responses[1],
            'VnfLcmOperationOccurrenceNotification',
            'PROCESSING')

        self.assert_notification_mock_response(
            notify_mock_responses[2],
            'VnfLcmOperationOccurrenceNotification',
            'COMPLETED')

    def assert_heal_vnf(
            self,
            resp,
            vnf_instance_id,
            expected_stack_status='UPDATE_COMPLETE'):
        self.assertEqual(202, resp.status_code)

        resp, vnf_instance = self._show_vnf_instance(vnf_instance_id)
        self.assert_vnf_state(vnf_instance)
        self.assert_instantiation_state(vnf_instance)

        self.assert_heat_stack_status(
            vnf_instance['id'],
            expected_stack_status=expected_stack_status)

        # FT-checkpoint: Notification
        notify_mock_responses = FAKE_SERVER_MANAGER.get_history(
            MOCK_NOTIFY_CALLBACK_URL)
        FAKE_SERVER_MANAGER.clear_history(MOCK_NOTIFY_CALLBACK_URL)

        self.assertEqual(3, len(notify_mock_responses))
        self.assert_notification_mock_response(
            notify_mock_responses[0],
            'VnfLcmOperationOccurrenceNotification',
            'STARTING')

        self.assert_notification_mock_response(
            notify_mock_responses[1],
            'VnfLcmOperationOccurrenceNotification',
            'PROCESSING')

        self.assert_notification_mock_response(
            notify_mock_responses[2],
            'VnfLcmOperationOccurrenceNotification',
            'COMPLETED')

    def assert_terminate_vnf(
            self,
            resp,
            vnf_instance_id,
            stack_id,
            resource_name_list,
            glance_image_id_list):
        self.assertEqual(202, resp.status_code)

        resp, vnf_instance = self._show_vnf_instance(vnf_instance_id)
        self.assert_instantiation_state(
            vnf_instance,
            fields.VnfInstanceState.NOT_INSTANTIATED)

        # FT-checkpoint: Heat stack status.
        stack = self._get_heat_stack(vnf_instance_id)
        self.assertIsNone(stack)

        self.assert_heat_resource_status_is_none(
            stack_id,
            resources_name_list=resource_name_list,
            glance_image_id_list=glance_image_id_list)

        # FT-checkpoint: Notification
        notify_mock_responses = FAKE_SERVER_MANAGER.get_history(
            MOCK_NOTIFY_CALLBACK_URL)
        FAKE_SERVER_MANAGER.clear_history(MOCK_NOTIFY_CALLBACK_URL)

        self.assertEqual(3, len(notify_mock_responses))
        self.assert_notification_mock_response(
            notify_mock_responses[0],
            'VnfLcmOperationOccurrenceNotification',
            'STARTING')

        self.assert_notification_mock_response(
            notify_mock_responses[1],
            'VnfLcmOperationOccurrenceNotification',
            'PROCESSING')

        self.assert_notification_mock_response(
            notify_mock_responses[2],
            'VnfLcmOperationOccurrenceNotification',
            'COMPLETED')

    def assert_notification_mock_response(
            self,
            notify_mock_response,
            expected_notify_types,
            expected_operation_status=None):
        self.assertEqual(204, notify_mock_response.status_code)

        self.assertEqual(
            expected_notify_types,
            notify_mock_response.request_body['notificationType'])

        if expected_operation_status:
            self.assertEqual(
                expected_operation_status,
                notify_mock_response.request_body['operationState'])

    def _create_network(self, name):
        # First, we have to check network name passed by caller is
        # already exists or not.
        netlist = self.neutronclient().list_networks(name=name)
        if netlist is not None:
            print('%s is already exist' % name)

        # OK, we can create this.
        net = self.neutronclient().create_network({'network': {'name': name}})
        net_id = net['network']['id']
        self.addCleanup(self.neutronclient().delete_network, net_id)

        return net_id

    def _create_subnet(self, network):
        body = {'subnet': {'network_id': network['id'],
                'name': "subnet-%s" % uuidutils.generate_uuid(),
                'cidr': "22.22.{}.0/24".format(str(len(self.ext_subnets) % 2)),
                'ip_version': 4,
                'gateway_ip': '22.22.0.1',
                "enable_dhcp": True}}

        subnet = self.neutronclient().create_subnet(body=body)["subnet"]
        self.addCleanup(self.neutronclient().delete_subnet, subnet['id'])
        return subnet['id']

    def _create_port(self, network_id):
        body = {'port': {'network_id': network_id}}
        port = self.neutronclient().create_port(body=body)["port"]
        self.addCleanup(self.neutronclient().delete_port, port['id'])
        return port['id']

    def assert_subscription_show(self, resp, response_body):
        """Assert that subscription informations has mandatory keys."""
        self.assertEqual(200, resp.status_code)

        self.assertIsNotNone(response_body.get('id'))
        _filter = response_body.get('filter')
        self.assertIsNotNone(_filter)
        self.assertIsNotNone(_filter.get('notificationTypes'))
        self.assertIsNotNone(_filter.get('operationTypes'))
        self.assertIsNotNone(response_body.get('callbackUri'))
        _links = response_body.get('_links')
        self.assertIsNotNone(_links)
        self.assertIsNotNone(_links.get('self'))
        self.assertIsNotNone(_links.get('self').get('href'))
