# Copyright 2017 99cloud, Inc.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
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
import mock
import os
import requests
import tempfile

from tacker.common import exceptions
from tacker import context
from tacker.extensions import vnfm
from tacker.tests.common import helpers
from tacker.tests.unit import base
from tacker.tests.unit.db import utils
from tacker.tests.unit.vnfm.infra_drivers.openstack.fixture_data import client
from tacker.tests.unit.vnfm.infra_drivers.openstack.fixture_data import \
    fixture_data_utils as fd_utils
from tacker.tests import uuidsentinel
from tacker.vnfm.infra_drivers.openstack import openstack


@ddt.ddt
class TestOpenStack(base.FixturedTestCase):
    client_fixture_class = client.ClientFixture
    sdk_connection_fixure_class = client.SdkConnectionFixture

    def setUp(self):
        super(TestOpenStack, self).setUp()
        self.openstack = openstack.OpenStack()
        self.context = context.get_admin_context()
        self.heat_url = client.HEAT_URL
        self.glance_url = client.GLANCE_URL
        self.instance_uuid = uuidsentinel.instance_id
        self.stack_id = uuidsentinel.stack_id
        self.json_headers = {'content-type': 'application/json',
                             'location': 'http://heat-api/stacks/'
                             + self.instance_uuid + '/myStack/60f83b5e'}
        self._mock('tacker.common.clients.OpenstackClients.heat', self.cs)
        mock.patch('tacker.common.clients.OpenstackSdkConnection.'
                   'openstack_connection', return_value=self.sdk_conn).start()
        self.mock_log = mock.patch('tacker.vnfm.infra_drivers.openstack.'
                                   'openstack.LOG').start()
        mock.patch('time.sleep', return_value=None).start()

    def _response_in_wait_until_stack_ready(self, status_list,
                                            stack_outputs=True):
        # response for heat_client's get()
        for status in status_list:
            url = self.heat_url + '/stacks/' + self.instance_uuid
            json = {'stack': fd_utils.get_dummy_stack(stack_outputs,
                                                      status=status)}
            self.requests_mock.register_uri('GET', url, json=json,
                                            headers=self.json_headers)

    def _response_in_resource_get(self, id, res_name=None):
        # response for heat_client's resource_get()
        if res_name:
            url = self.heat_url + '/stacks/' + id + ('/myStack/60f83b5e/'
                                                'resources/') + res_name
        else:
            url = self.heat_url + '/stacks/' + id

        json = {'resource': fd_utils.get_dummy_resource()}
        self.requests_mock.register_uri('GET', url, json=json,
                                        headers=self.json_headers)

    def test_create_wait(self):
        self._response_in_wait_until_stack_ready(["CREATE_IN_PROGRESS",
                                                 "CREATE_COMPLETE"])
        vnf_dict = utils.get_dummy_vnf(instance_id=self.instance_uuid)
        self.openstack.create_wait(None, None,
                                   vnf_dict, self.instance_uuid, None)
        self.mock_log.debug.assert_called_with('outputs %s',
                                         fd_utils.get_dummy_stack()['outputs'])
        self.assertEqual(helpers.compact_byte('{"VDU1": "192.168.120.216"}'),
                         vnf_dict['mgmt_ip_address'])

    def test_create_wait_without_mgmt_ips(self):
        self._response_in_wait_until_stack_ready(["CREATE_IN_PROGRESS",
                                                 "CREATE_COMPLETE"],
                                                 stack_outputs=False)
        vnf_dict = utils.get_dummy_vnf(instance_id=self.instance_uuid)
        self.openstack.create_wait(None, None,
                                   vnf_dict, self.instance_uuid, None)
        self.mock_log.debug.assert_called_with('outputs %s',
                          fd_utils.get_dummy_stack(outputs=False)['outputs'])
        self.assertIsNone(vnf_dict['mgmt_ip_address'])

    def test_create_wait_with_scaling_group_names(self):
        self._response_in_wait_until_stack_ready(["CREATE_IN_PROGRESS",
                                                 "CREATE_COMPLETE"])
        self._response_in_resource_get(self.instance_uuid,
                                       res_name='SP1_group')
        url = self.heat_url + '/stacks/' + self.stack_id + '/resources'
        json = {'resources': [fd_utils.get_dummy_resource()]}
        self.requests_mock.register_uri('GET', url, json=json,
                                        headers=self.json_headers)
        self._response_in_resource_get(self.stack_id)
        vnf_dict = utils.get_dummy_vnf(scaling_group=True)
        self.openstack.create_wait(None, None, vnf_dict, self.instance_uuid,
                                   None)
        self.assertEqual(helpers.compact_byte('{"vdu1": ["test1"]}'),
                         vnf_dict['mgmt_ip_address'])

    def test_create_wait_failed_with_stack_retries_0(self):
        self._response_in_wait_until_stack_ready(["CREATE_IN_PROGRESS"])
        vnf_dict = utils.get_dummy_vnf(instance_id=self.instance_uuid)
        self.assertRaises(vnfm.VNFCreateWaitFailed,
                          self.openstack.create_wait,
                          None, None, vnf_dict, self.instance_uuid, None)

    def test_create_wait_failed_with_stack_retries_not_0(self):
        self._response_in_wait_until_stack_ready(["CREATE_IN_PROGRESS",
                                                 "FAILED"])
        vnf_dict = utils.get_dummy_vnf(instance_id=self.instance_uuid)
        self.assertRaises(vnfm.VNFCreateWaitFailed,
                          self.openstack.create_wait,
                          None, None, vnf_dict, self.instance_uuid, {})

    def _exception_response(self):
        url = self.heat_url + '/stacks/' + self.instance_uuid
        body = {"error": Exception("any stuff")}
        self.requests_mock.register_uri('GET', url, body=body,
                    status_code=404, headers=self.json_headers)

    def test_create_wait_with_exception(self):
        self._exception_response()
        vnf_dict = utils.get_dummy_vnf(instance_id=self.instance_uuid)
        self.assertRaises(vnfm.VNFCreateWaitFailed,
                          self.openstack.create_wait,
                          None, None, vnf_dict, self.instance_uuid, None)

    def test_delete_wait_failed_with_stack_retries_0(self):
        self._response_in_wait_until_stack_ready(["DELETE_IN_PROGRESS"])
        self.assertRaises(vnfm.VNFDeleteWaitFailed,
                          self.openstack.delete_wait,
                          None, None, self.instance_uuid, None, None)

    def test_delete_wait_stack_retries_not_0(self):
        self._response_in_wait_until_stack_ready(["DELETE_IN_PROGRESS",
                                                 "FAILED"])
        self.assertRaises(vnfm.VNFDeleteWaitFailed,
                          self.openstack.delete_wait,
                          None, None, self.instance_uuid, None, None)
        self.mock_log.warning.assert_called_once()

    def test_update_wait(self):
        self._response_in_wait_until_stack_ready(["CREATE_COMPLETE"])
        vnf_dict = utils.get_dummy_vnf(status='PENDING_UPDATE',
                                       instance_id=self.instance_uuid)
        self.openstack.update_wait(None, None, vnf_dict, None)
        self.mock_log.debug.assert_called_with('outputs %s',
                                    fd_utils.get_dummy_stack()['outputs'])
        self.assertEqual(helpers.compact_byte('{"VDU1": "192.168.120.216"}'),
                         vnf_dict['mgmt_ip_address'])

    def test_heal_wait(self):
        self._response_in_wait_until_stack_ready(["UPDATE_IN_PROGRESS",
                                                 "UPDATE_COMPLETE"])
        vnf_dict = utils.get_dummy_vnf(status='PENDING_HEAL',
                                       instance_id=self.instance_uuid)
        self.openstack.heal_wait(None, None, vnf_dict, None)
        self.mock_log.debug.assert_called_with('outputs %s',
                                    fd_utils.get_dummy_stack()['outputs'])
        self.assertEqual(helpers.compact_byte('{"VDU1": "192.168.120.216"}'),
                         vnf_dict['mgmt_ip_address'])

    def test_heal_wait_without_mgmt_ips(self):
        self._response_in_wait_until_stack_ready(["UPDATE_IN_PROGRESS",
                                                 "UPDATE_COMPLETE"],
                                                 stack_outputs=False)
        vnf_dict = utils.get_dummy_vnf(status='PENDING_HEAL',
                                       instance_id=self.instance_uuid)
        self.openstack.heal_wait(None, None, vnf_dict, None)
        self.mock_log.debug.assert_called_with('outputs %s',
                        fd_utils.get_dummy_stack(outputs=False)['outputs'])
        self.assertIsNone(vnf_dict['mgmt_ip_address'])

    def test_heal_wait_failed_with_retries_0(self):
        self._response_in_wait_until_stack_ready(["UPDATE_IN_PROGRESS"])
        vnf_dict = utils.get_dummy_vnf(status='PENDING_HEAL',
                                       instance_id=self.instance_uuid)
        self.assertRaises(vnfm.VNFHealWaitFailed,
                          self.openstack.heal_wait,
                          None, None, vnf_dict,
                          None)

    def test_heal_wait_failed_stack_retries_not_0(self):
        self._response_in_wait_until_stack_ready(["UPDATE_IN_PROGRESS",
                                                 "FAILED"])
        vnf_dict = utils.get_dummy_vnf(status='PENDING_HEAL',
                                       instance_id=self.instance_uuid)
        self.assertRaises(vnfm.VNFHealWaitFailed,
                          self.openstack.heal_wait,
                          None, None, vnf_dict,
                          None)

    def _responses_in_resource_event_list(self, dummy_event):
        # response for heat_client's resource_event_list()
        url = self.heat_url + '/stacks/' + self.instance_uuid
        json = {'stack': [fd_utils.get_dummy_stack()]}
        self.requests_mock.register_uri('GET', url, json=json,
                                        headers=self.json_headers)
        url = self.heat_url + '/stacks/' + self.instance_uuid + (
            '/myStack/60f83b5e/resources/SP1_scale_out/events?limit=1&sort_dir'
            '=desc&sort_keys=event_time')
        json = {'events': [dummy_event]}
        self.requests_mock.register_uri('GET', url, json=json,
                                        headers=self.json_headers)

    def test_scale(self):
        dummy_event = fd_utils.get_dummy_event()
        self._responses_in_resource_event_list(dummy_event)
        # response for heat_client's resource_signal()
        url = self.heat_url + '/stacks/' + self.instance_uuid + (
            '/myStack/60f83b5e/resources/SP1_scale_out/signal')
        self.requests_mock.register_uri('POST', url, json={},
                                        headers=self.json_headers)
        event_id = self.openstack.scale(plugin=self, context=self.context,
                                    auth_attr=None,
                                    policy=fd_utils.get_dummy_policy_dict(),
                                    region_name=None)
        self.assertEqual(dummy_event['id'], event_id)

    def _response_in_resource_get_list(self):
        # response for heat_client's resource_get_list()
        url = self.heat_url + '/stacks/' + self.stack_id + '/resources'
        json = {'resources': [fd_utils.get_dummy_resource()]}
        self.requests_mock.register_uri('GET', url, json=json,
                                        headers=self.json_headers)

    def _test_scale(self, resource_status):
        dummy_event = fd_utils.get_dummy_event(resource_status)
        self._responses_in_resource_event_list(dummy_event)
        self._response_in_resource_get(self.instance_uuid, res_name='G1')
        self._response_in_resource_get_list()
        self._response_in_resource_get(self.stack_id)
        self._response_in_resource_get(self.instance_uuid,
                                       res_name='SP1_group')

    def test_scale_wait_with_different_last_event_id(self):
        self._test_scale("SIGNAL_COMPLETE")
        mgmt_ip = self.openstack.scale_wait(plugin=self, context=self.context,
                                     auth_attr=None,
                                     policy=fd_utils.get_dummy_policy_dict(),
                                     region_name=None,
                                     last_event_id=uuidsentinel.
                                            non_last_event_id)
        self.assertEqual(helpers.compact_byte('{"vdu1": ["test1"]}'),
                         mgmt_ip)

    @ddt.data("SIGNAL_COMPLETE", "CREATE_COMPLETE")
    def test_scale_wait_with_same_last_event_id(self, resource_status):
        self._test_scale(resource_status)
        mgmt_ip = self.openstack.scale_wait(plugin=self,
                                context=self.context,
                                auth_attr=None,
                                policy=fd_utils.get_dummy_policy_dict(),
                                region_name=None,
                                last_event_id=fd_utils.get_dummy_event()['id'])
        self.assertEqual(helpers.compact_byte('{"vdu1": ["test1"]}'),
                         mgmt_ip)

    @mock.patch('tacker.vnfm.infra_drivers.openstack.openstack.LOG')
    def test_scale_wait_failed_with_exception(self, mock_log):
        self._exception_response()
        self.assertRaises(vnfm.VNFScaleWaitFailed,
                          self.openstack.scale_wait,
                          plugin=self, context=self.context, auth_attr=None,
                          policy=fd_utils.get_dummy_policy_dict(),
                          region_name=None,
                          last_event_id=fd_utils.get_dummy_event()['id'])
        mock_log.warning.assert_called_once()

    def _response_in_resource_metadata(self, metadata=None):
        # response for heat_client's resource_metadata()
        url = self.heat_url + '/stacks/' + self.instance_uuid + \
            '/myStack/60f83b5e/resources/SP1_scale_out/metadata'
        json = {'metadata': {'scaling_in_progress': metadata}}
        return self.requests_mock.register_uri('GET', url, json=json,
                                        headers=self.json_headers)

    def test_scale_wait_failed_with_stack_retries_0(self):
        dummy_event = fd_utils.get_dummy_event("CREATE_IN_PROGRESS")
        self._responses_in_resource_event_list(dummy_event)
        self._response_in_resource_metadata(True)
        self.assertRaises(vnfm.VNFScaleWaitFailed,
                          self.openstack.scale_wait,
                          plugin=self, context=self.context, auth_attr=None,
                          policy=fd_utils.get_dummy_policy_dict(),
                          region_name=None,
                          last_event_id=dummy_event['id'])
        self.mock_log.warning.assert_called_once()

    def test_scale_wait_without_resource_metadata(self):
        dummy_event = fd_utils.get_dummy_event("CREATE_IN_PROGRESS")
        self._responses_in_resource_event_list(dummy_event)
        self._response_in_resource_metadata()
        self._response_in_resource_get(self.instance_uuid, res_name='G1')
        self._response_in_resource_get_list()
        self._response_in_resource_get(self.stack_id)
        self._response_in_resource_get(self.instance_uuid,
                                       res_name='SP1_group')
        mgmt_ip = self.openstack.scale_wait(plugin=self, context=self.context,
                                  auth_attr=None,
                                  policy=fd_utils.get_dummy_policy_dict(),
                                  region_name=None,
                                  last_event_id=fd_utils.get_dummy_event()
                                  ['id'])
        error_reason = ('When signal occurred within cool down '
                        'window, no events generated from heat, '
                        'so ignore it')
        self.mock_log.warning.assert_called_once_with(error_reason)
        self.assertEqual(b'{"vdu1": ["test1"]}', mgmt_ip)

    def _responses_in_create_image(self, multiple_responses=False):
        # response for glance_client's create()
        json = fd_utils.get_fake_glance_image_dict()
        url = os.path.join(self.glance_url, 'images')
        if multiple_responses:
            return self.requests_mock.register_uri(
                'POST', url, [{'json': json, 'status_code': 201,
                               'headers': self.json_headers},
                              {'exc': requests.exceptions.ConnectTimeout}])
        else:
            return self.requests_mock.register_uri('POST', url, json=json,
                                            headers=self.json_headers)

    def _responses_in_import_image(self, raise_exception=False):
        # response for glance_client's import()
        json = fd_utils.get_fake_glance_image_dict()
        url = os.path.join(
            self.glance_url, 'images', uuidsentinel.image_id, 'import')

        if raise_exception:
            return self.requests_mock.register_uri('POST', url,
                exc=requests.exceptions.ConnectTimeout)
        else:
            return self.requests_mock.register_uri('POST', url, json=json,
                headers=self.json_headers)

    def _responses_in_get_image(self, image_path=None, status='active',
                                hash_value='hash'):
        # response for glance_client's import()
        json = fd_utils.get_fake_glance_image_dict(image_path=image_path,
                                                   status=status,
                                                   hash_value=hash_value)
        url = os.path.join(
            self.glance_url, 'images', uuidsentinel.image_id)
        return self.requests_mock.register_uri('GET', url, json=json,
                                        headers=self.json_headers)

    def _responses_in_upload_image(self, image_path=None, status='active',
                                   hash_value='hash'):
        # response for glance_client's upload()
        json = fd_utils.get_fake_glance_image_dict(image_path=image_path,
                                                   status=status,
                                                   hash_value=hash_value)
        url = os.path.join(
            self.glance_url, 'images', uuidsentinel.image_id, 'file')
        return self.requests_mock.register_uri('PUT', url, json=json,
                                        headers=self.json_headers)

    def test_pre_instantiation_vnf_image_with_file(self):
        vnf_instance = fd_utils.get_vnf_instance_object()

        # Create a temporary file as the openstacksdk will access it for
        # calculating the hash value.
        image_fd, image_path = tempfile.mkstemp()
        vnf_software_image = fd_utils.get_vnf_software_image_object(
            image_path=image_path)
        vnf_software_images = {'node_name': vnf_software_image}

        upload_image_url = self._responses_in_upload_image(image_path)
        create_image_url = self._responses_in_create_image()
        get_image_url = self._responses_in_get_image(image_path)

        vnf_resources = self.openstack.pre_instantiation_vnf(
            self.context, vnf_instance, None, vnf_software_images)

        image_resource = vnf_resources['node_name'][0]

        os.close(image_fd)
        os.remove(image_path)

        # Asserting the response as per the data given in the fake objects.
        self.assertEqual(image_resource.resource_name,
                         'test-image')
        self.assertEqual(image_resource.resource_status,
                         'CREATED')
        self.assertEqual(image_resource.resource_type,
                         'image')
        self.assertEqual(image_resource.vnf_instance_id,
                         vnf_instance.id)
        self.assertEqual(upload_image_url.call_count, 1)
        self.assertEqual(create_image_url.call_count, 1)
        self.assertEqual(get_image_url.call_count, 2)

    @mock.patch('tacker.common.utils.is_url', mock.MagicMock(
        return_value=True))
    def test_pre_instantiation_vnf_image_with_url(self):
        image_path = "http://fake-url.net"
        vnf_instance = fd_utils.get_vnf_instance_object()

        vnf_software_image = fd_utils.get_vnf_software_image_object(
            image_path=image_path)
        vnf_software_images = {'node_name': vnf_software_image}
        create_image_url = self._responses_in_create_image(image_path)
        import_image_url = self._responses_in_import_image()
        get_image_url = self._responses_in_get_image(image_path)

        vnf_resources = self.openstack.pre_instantiation_vnf(
            self.context, vnf_instance, None, vnf_software_images)

        image_resource = vnf_resources['node_name'][0]

        # Asserting the response as per the data given in the fake objects.
        self.assertEqual(image_resource.resource_name,
                         'test-image')
        self.assertEqual(image_resource.resource_status,
                         'CREATED')
        self.assertEqual(image_resource.resource_type,
                         'image')
        self.assertEqual(image_resource.vnf_instance_id,
                         vnf_instance.id)
        self.assertEqual(create_image_url.call_count, 1)
        self.assertEqual(import_image_url.call_count, 1)
        self.assertEqual(get_image_url.call_count, 1)

    @ddt.data(False, True)
    def test_pre_instantiation_vnf_failed_in_image_creation(
            self, exception_in_delete_image):
        vnf_instance = fd_utils.get_vnf_instance_object()

        vnf_software_image = fd_utils.get_vnf_software_image_object()
        vnf_software_images = {'node_name1': vnf_software_image,
                               'node_name2': vnf_software_image}
        # exception will occur in second iteration of image creation.
        create_image_url = self._responses_in_create_image(
            multiple_responses=True)
        import_image_url = self._responses_in_import_image()
        get_image_url = self._responses_in_get_image()
        delete_image_url = self._response_in_delete_image(
            uuidsentinel.image_id, exception=exception_in_delete_image)
        self.assertRaises(exceptions.VnfPreInstantiationFailed,
                          self.openstack.pre_instantiation_vnf,
                          self.context, vnf_instance, None,
                          vnf_software_images)
        self.assertEqual(create_image_url.call_count, 3)
        self.assertEqual(import_image_url.call_count, 1)
        self.assertEqual(get_image_url.call_count, 1)

        delete_call_count = 2 if exception_in_delete_image else 1
        self.assertEqual(delete_image_url.call_count, delete_call_count)

    @ddt.data(False, True)
    def test_pre_instantiation_vnf_failed_in_image_upload(
            self, exception_in_delete_image):
        vnf_instance = fd_utils.get_vnf_instance_object()
        image_path = '/non/existent/file'
        software_image_update = {'image_path': image_path}
        vnf_software_image = fd_utils.get_vnf_software_image_object(
            **software_image_update)
        vnf_software_images = {'node_name1': vnf_software_image,
                               'node_name2': vnf_software_image}

        # exception will occur in second iteration of image creation.

        # No urls are accessed in this case because openstacksdk fails to
        # access the file when it wants to calculate the hash.
        self._responses_in_create_image(multiple_responses=True)
        self._responses_in_upload_image(image_path)
        self._responses_in_get_image()
        self._response_in_delete_image(uuidsentinel.image_id,
            exception=exception_in_delete_image)
        self.assertRaises(exceptions.VnfPreInstantiationFailed,
                          self.openstack.pre_instantiation_vnf,
                          self.context, vnf_instance, None,
                          vnf_software_images)

    def test_pre_instantiation_vnf_failed_with_mismatch_in_hash_value(self):
        vnf_instance = fd_utils.get_vnf_instance_object()

        vnf_software_image = fd_utils.get_vnf_software_image_object()
        vnf_software_images = {'node_name1': vnf_software_image,
                               'node_name2': vnf_software_image}
        # exception will occur in second iteration of image creation.
        create_image_url = self._responses_in_create_image(
            multiple_responses=True)
        import_image_url = self._responses_in_import_image()
        get_image_url = self._responses_in_get_image(
            hash_value='diff-hash-value')
        delete_image_url = self._response_in_delete_image(
            uuidsentinel.image_id)
        self.assertRaises(exceptions.VnfPreInstantiationFailed,
                          self.openstack.pre_instantiation_vnf,
                          self.context, vnf_instance, None,
                          vnf_software_images)
        self.assertEqual(create_image_url.call_count, 1)
        self.assertEqual(import_image_url.call_count, 1)
        self.assertEqual(get_image_url.call_count, 1)
        self.assertEqual(delete_image_url.call_count, 1)

    def test_pre_instantiation_vnf_with_image_create_wait_failed(self):
        vnf_instance = fd_utils.get_vnf_instance_object()

        vnf_software_image = fd_utils.get_vnf_software_image_object()
        vnf_software_images = {'node_name1': vnf_software_image,
                               'node_name2': vnf_software_image}
        # exception will occurs in second iteration of image creation.
        create_image_url = self._responses_in_create_image()
        import_image_url = self._responses_in_import_image()
        get_image_url = self._responses_in_get_image(status='pending_create')
        self.assertRaises(exceptions.VnfPreInstantiationFailed,
                          self.openstack.pre_instantiation_vnf,
                          self.context, vnf_instance, None,
                          vnf_software_images)
        self.assertEqual(create_image_url.call_count, 1)
        self.assertEqual(import_image_url.call_count, 1)
        self.assertEqual(get_image_url.call_count, 10)

    def _exception_response_in_import_image(self):
        url = os.path.join(self.glance_url, 'images', uuidsentinel.image_id,
                           'import')
        return self.requests_mock.register_uri(
            'POST', url, exc=requests.exceptions.ConnectTimeout)

    def _response_in_delete_image(self, resource_id, exception=False):
        # response for glance_client's delete()
        url = os.path.join(
            self.glance_url, 'images', resource_id)
        if exception:
            return self.requests_mock.register_uri(
                'DELETE', url, exc=requests.exceptions.ConnectTimeout)
        else:
            return self.requests_mock.register_uri('DELETE', url, json={},
                                            status_code=200,
                                            headers=self.json_headers)

    @ddt.data(True, False)
    def test_pre_instantiation_vnf_failed_in_image_import(
            self, exception_in_delete):
        vnf_instance = fd_utils.get_vnf_instance_object()

        vnf_software_image = fd_utils.get_vnf_software_image_object()
        vnf_software_images = {'node_name': vnf_software_image}

        create_image_url = self._responses_in_create_image()
        import_image_exc_url = self._responses_in_import_image(
            raise_exception=True)
        delete_image_url = self._response_in_delete_image(
            uuidsentinel.image_id, exception_in_delete)
        self.assertRaises(exceptions.VnfPreInstantiationFailed,
                          self.openstack.pre_instantiation_vnf,
                          self.context, vnf_instance, None,
                          vnf_software_images)
        self.assertEqual(create_image_url.call_count, 1)
        self.assertEqual(import_image_exc_url.call_count, 2)
        delete_call_count = 2 if exception_in_delete else 1
        self.assertEqual(delete_image_url.call_count, delete_call_count)

    @mock.patch('tacker.vnfm.infra_drivers.openstack.openstack.LOG')
    def test_delete_vnf_instance_resource(self, mock_log):
        vnf_instance = fd_utils.get_vnf_instance_object()
        vnf_resource = fd_utils.get_vnf_resource_object()

        delete_image_url = self._response_in_delete_image(
            vnf_resource.resource_identifier)
        self.openstack.delete_vnf_instance_resource(
            self.context, vnf_instance, None, vnf_resource)
        mock_log.info.assert_called()
        self.assertEqual(delete_image_url.call_count, 1)

    @mock.patch('tacker.vnfm.infra_drivers.openstack.openstack.LOG')
    def test_delete_vnf_instance_resource_failed_with_exception(
            self, mock_log):
        vnf_instance = fd_utils.get_vnf_instance_object()
        vnf_resource = fd_utils.get_vnf_resource_object()

        delete_image_url = self._response_in_delete_image(
            vnf_resource.resource_identifier, exception=True)
        self.openstack.delete_vnf_instance_resource(
            self.context, vnf_instance, None, vnf_resource)
        mock_log.info.assert_called()
        self.assertEqual(delete_image_url.call_count, 2)

    @mock.patch('tacker.vnfm.infra_drivers.openstack.translate_template.'
                'TOSCAToHOT._get_unsupported_resource_props')
    def test_instantiate_vnf(self, mock_get_unsupported_resource_props):
        vim_connection_info = fd_utils.get_vim_connection_info_object()
        inst_req_info = fd_utils.get_instantiate_vnf_request()
        vnfd_dict = fd_utils.get_vnfd_dict()
        grant_response = fd_utils.get_grant_response_dict()

        url = os.path.join(self.heat_url, 'stacks')
        self.requests_mock.register_uri(
            'POST', url, json={'stack': fd_utils.get_dummy_stack()},
            headers=self.json_headers)

        instance_id = self.openstack.instantiate_vnf(
            self.context, None, vnfd_dict, vim_connection_info,
            inst_req_info, grant_response)

        self.assertEqual(uuidsentinel.instance_id, instance_id)

    def _responses_in_stack_list(self, instance_id, resources=None):

        resources = resources or []
        url = os.path.join(self.heat_url, 'stacks', instance_id, 'resources')
        self.requests_mock.register_uri('GET', url,
            json={'resources': resources}, headers=self.json_headers)

        response_list = [{'json': {'stacks': [fd_utils.get_dummy_stack(
            attrs={'parent': uuidsentinel.instance_id})]}},
            {'json': {'stacks': [fd_utils.get_dummy_stack()]}}]

        url = os.path.join(self.heat_url, 'stacks?owner_id=' +
                           instance_id + '&show_nested=True')
        self.requests_mock.register_uri('GET', url, response_list)

    def test_post_vnf_instantiation(self):
        v_s_resource_info = fd_utils.get_virtual_storage_resource_info(
            desc_id="storage1", set_resource_id=False)

        storage_resource_ids = [v_s_resource_info.id]
        vnfc_resource_info = fd_utils.get_vnfc_resource_info(vdu_id="VDU_VNF",
            storage_resource_ids=storage_resource_ids, set_resource_id=False)

        v_l_resource_info = fd_utils.get_virtual_link_resource_info(
            vnfc_resource_info.vnfc_cp_info[0].vnf_link_port_id,
            vnfc_resource_info.vnfc_cp_info[0].id)

        inst_vnf_info = fd_utils.get_vnf_instantiated_info(
            virtual_storage_resource_info=[v_s_resource_info],
            vnf_virtual_link_resource_info=[v_l_resource_info],
            vnfc_resource_info=[vnfc_resource_info])

        vnf_instance = fd_utils.get_vnf_instance_object(
            instantiated_vnf_info=inst_vnf_info)

        vim_connection_info = fd_utils.get_vim_connection_info_object()
        resources = [{'resource_name': vnfc_resource_info.vdu_id,
            'resource_type': vnfc_resource_info.compute_resource.
                vim_level_resource_type,
            'physical_resource_id': uuidsentinel.vdu_resource_id},
            {'resource_name': v_s_resource_info.virtual_storage_desc_id,
            'resource_type': v_s_resource_info.storage_resource.
                vim_level_resource_type,
            'physical_resource_id': uuidsentinel.storage_resource_id},
            {'resource_name': vnfc_resource_info.vnfc_cp_info[0].cpd_id,
            'resource_type': inst_vnf_info.vnf_virtual_link_resource_info[0].
                vnf_link_ports[0].resource_handle.vim_level_resource_type,
            'physical_resource_id': uuidsentinel.cp1_resource_id}]

        self._responses_in_stack_list(inst_vnf_info.instance_id,
            resources=resources)
        self.openstack.post_vnf_instantiation(
            self.context, vnf_instance, vim_connection_info)
        self.assertEqual(vnf_instance.instantiated_vnf_info.
            vnfc_resource_info[0].metadata['stack_id'],
            inst_vnf_info.instance_id)

        # Check if vnfc resource "VDU_VNF" is set with resource_id
        self.assertEqual(uuidsentinel.vdu_resource_id,
            vnf_instance.instantiated_vnf_info.vnfc_resource_info[0].
            compute_resource.resource_id)

        # Check if virtual storage resource "storage1" is set with resource_id
        self.assertEqual(uuidsentinel.storage_resource_id,
            vnf_instance.instantiated_vnf_info.
            virtual_storage_resource_info[0].storage_resource.resource_id)

        # Check if virtual link port "CP1" is set with resource_id
        self.assertEqual(uuidsentinel.cp1_resource_id,
            vnf_instance.instantiated_vnf_info.
            vnf_virtual_link_resource_info[0].vnf_link_ports[0].
            resource_handle.resource_id)

    def test_post_vnf_instantiation_with_ext_managed_virtual_link(self):
        v_s_resource_info = fd_utils.get_virtual_storage_resource_info(
            desc_id="storage1", set_resource_id=False)

        storage_resource_ids = [v_s_resource_info.id]
        vnfc_resource_info = fd_utils.get_vnfc_resource_info(vdu_id="VDU_VNF",
            storage_resource_ids=storage_resource_ids, set_resource_id=False)

        v_l_resource_info = fd_utils.get_virtual_link_resource_info(
            vnfc_resource_info.vnfc_cp_info[0].vnf_link_port_id,
            vnfc_resource_info.vnfc_cp_info[0].id,
            desc_id='ExternalVL1')

        ext_managed_v_l_resource_info = \
            fd_utils.get_ext_managed_virtual_link_resource_info(
                uuidsentinel.virtual_link_port_id,
                uuidsentinel.vnfc_cp_info_id,
                desc_id='ExternalVL1')

        inst_vnf_info = fd_utils.get_vnf_instantiated_info(
            virtual_storage_resource_info=[v_s_resource_info],
            vnf_virtual_link_resource_info=[v_l_resource_info],
            vnfc_resource_info=[vnfc_resource_info],
            ext_managed_virtual_link_info=[ext_managed_v_l_resource_info])

        vnf_instance = fd_utils.get_vnf_instance_object(
            instantiated_vnf_info=inst_vnf_info)

        vim_connection_info = fd_utils.get_vim_connection_info_object()
        resources = [{'resource_name': vnfc_resource_info.vdu_id,
            'resource_type': vnfc_resource_info.compute_resource.
                vim_level_resource_type,
            'physical_resource_id': uuidsentinel.vdu_resource_id},
            {'resource_name': v_s_resource_info.virtual_storage_desc_id,
            'resource_type': v_s_resource_info.storage_resource.
                vim_level_resource_type,
            'physical_resource_id': uuidsentinel.storage_resource_id},
            {'resource_name': vnfc_resource_info.vnfc_cp_info[0].cpd_id,
            'resource_type': inst_vnf_info.vnf_virtual_link_resource_info[0].
                vnf_link_ports[0].resource_handle.vim_level_resource_type,
            'physical_resource_id': uuidsentinel.cp1_resource_id},
            {'resource_name': v_l_resource_info.vnf_virtual_link_desc_id,
            'resource_type': v_l_resource_info.network_resource.
                vim_level_resource_type,
            'physical_resource_id': uuidsentinel.v_l_resource_info_id}]
        self._responses_in_stack_list(inst_vnf_info.instance_id,
            resources=resources)
        self.openstack.post_vnf_instantiation(
            self.context, vnf_instance, vim_connection_info)
        self.assertEqual(vnf_instance.instantiated_vnf_info.
            vnfc_resource_info[0].metadata['stack_id'],
            inst_vnf_info.instance_id)

        # Check if vnfc resource "VDU_VNF" is set with resource_id
        self.assertEqual(uuidsentinel.vdu_resource_id,
            vnf_instance.instantiated_vnf_info.vnfc_resource_info[0].
            compute_resource.resource_id)

        # Check if virtual storage resource "storage1" is set with resource_id
        self.assertEqual(uuidsentinel.storage_resource_id,
            vnf_instance.instantiated_vnf_info.
            virtual_storage_resource_info[0].storage_resource.resource_id)

        # Check if virtual link port "CP1" is set with resource_id
        self.assertEqual(uuidsentinel.cp1_resource_id,
            vnf_instance.instantiated_vnf_info.
            vnf_virtual_link_resource_info[0].vnf_link_ports[0].
            resource_handle.resource_id)

        # Check if ext managed virtual link port is set with resource_id
        self.assertEqual(uuidsentinel.cp1_resource_id,
            vnf_instance.instantiated_vnf_info.
            ext_managed_virtual_link_info[0].vnf_link_ports[0].
            resource_handle.resource_id)
