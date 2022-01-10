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
import json
import os
import tempfile
import time
from urllib.parse import urlparse
import yaml
import zipfile

from novaclient import client as nova_client
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
VNF_LCM_DONE_TIMEOUT = 1200
RETRY_WAIT_TIME = 5
FAKE_SERVER_MANAGER = FakeServerManager()
FAKE_SERVER_PORT = 9990
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
        if (200 <= resp.status_code < 300) and (
                body['onboardingState'] == "ONBOARDED"):
            vnfd_id = body['vnfdId']
            break

        if ((int(time.time()) - start_time) > timeout):
            raise TimeoutError("Failed to onboard vnf package")

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
            raise TimeoutError("Failed to onboard vnf package")

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
            raise TimeoutError("Failed to onboard vnf package")

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

    is_setup_error = False
    # NOTE: If prepare_fake_server is set(by default) then this base
    # class will prepare(create and start) the fake http server which
    # takes time and can add up more time in gate CI. Any child class
    # can set it false. For example, BaseVnfLcmMultiTenantTest which
    # create their own servers for two different tenants.
    prepare_fake_server = True

    @classmethod
    def setUpClass(cls):
        '''Set up test class.

        we set up fake NFVO server for test at here.
        '''
        super(BaseVnfLcmTest, cls).setUpClass()
        if cls.prepare_fake_server:
            cls._prepare_start_fake_server(FAKE_SERVER_MANAGER,
                FAKE_SERVER_PORT)

    @classmethod
    def tearDownClass(cls):
        super(BaseVnfLcmTest, cls).tearDownClass()
        if cls.prepare_fake_server:
            FAKE_SERVER_MANAGER.stop_server()

    def setUp(self):
        super(BaseVnfLcmTest, self).setUp()

        if self.is_setup_error:
            self.fail("Faild, not exists pre-registered image.")

        if self.prepare_fake_server:
            callback_url = os.path.join(MOCK_NOTIFY_CALLBACK_URL,
                self._testMethodName)
            self._clear_history_and_set_callback(FAKE_SERVER_MANAGER,
                callback_url)

        self.tacker_client = base.BaseTackerTest.tacker_http_client()

        self.base_vnf_instances_url = "/vnflcm/v1/vnf_instances"
        self.base_subscriptions_url = "/vnflcm/v1/subscriptions"
        self.base_vnf_lcm_op_occs_url = "/vnflcm/v1/vnf_lcm_op_occs"

        vim_list = self.client.list_vims()
        self.vim = self.get_vim(vim_list, 'VIM0')
        if not self.vim:
            assert False, "vim_list is Empty: Default VIM is missing"
        result = self._create_network_settings()
        self.ext_networks = result.get('ext_networks')
        self.ext_vl = result.get('ext_vl')
        self.ext_mngd_networks = result.get('ext_mngd_networks')
        self.ext_link_ports = result.get('ext_link_ports')
        self.ext_subnets = result.get('ext_subnets')
        self.changed_ext_networks = result.get('changed_ext_networks')
        self.changed_ext_subnets = result.get('changed_ext_subnets')

    @classmethod
    def _prepare_start_fake_server(cls, fake_server,
            fake_server_port):
        fake_server.prepare_http_server(address='localhost',
                port=fake_server_port)
        fake_server.start_server()

    def _clear_history_and_set_callback(self,
            fake_server_manager,
            callback_url):
        fake_server_manager.clear_history(callback_url)
        fake_server_manager.set_callback(
            'POST',
            callback_url,
            status_code=204
        )
        fake_server_manager.set_callback(
            'GET',
            callback_url,
            status_code=204
        )

    def _create_network_settings(self, neutron_client=None):
        if neutron_client is None:
            neutron_client = self.neutronclient()
        # Create external external.
        ext_networks = list()
        # Create external managed networks
        ext_mngd_networks = list()  # Store ids for cleaning.
        # Create external link ports in net0
        ext_link_ports = list()
        # Create external subnet in net1
        ext_subnets = list()  # Store ids for cleaning.
        # Create external networks to change.
        changed_ext_networks = list()
        changed_ext_subnets = list()  # Store ids for cleaning.

        networks = neutron_client.list_networks()
        for nw in networks.get('networks'):
            if nw['name'] == 'net0':
                ext_networks.append(nw['id'])
                ext_vl = _get_external_virtual_links(nw['id'])
                ext_subnets.append(nw['subnets'][0])
                ext_link_ports.append(self._create_port(nw['id'],
                                                 neutron_client))
                ext_link_ports.append(self._create_port(nw['id'],
                                                 neutron_client))
            elif nw['name'] == 'net1':
                ext_mngd_networks.append(nw['id'])

        # create new network.
        ext_net_id, ext_net_name = \
            self._create_network("external_net", neutron_client)
        ext_networks.append(ext_net_id)
        ext_mngd_net_id, _ = \
            self._create_network("external_managed_internal_net",
                    neutron_client)
        ext_mngd_networks.append(ext_mngd_net_id)
        changed_ext_net_id, changed_ext_net_name = \
            self._create_network("changed_external_net", neutron_client)
        changed_ext_networks.append(changed_ext_net_id)

        # Chack how many networks are created.
        networks = neutron_client.list_networks()
        for nw in networks.get('networks'):
            if nw['name'] not in [ext_net_name, changed_ext_net_name]:
                continue

            elif nw['name'] == ext_net_name:
                ext_subnets.append(
                    self._create_subnet(nw,
                                        cidr="22.22.1.0/24",
                                        gateway="22.22.1.1",
                                        neutron_client=neutron_client))
            elif nw['name'] == changed_ext_net_name:
                changed_ext_subnets.append(
                    self._create_subnet(nw,
                                        cidr="22.22.2.0/24",
                                        gateway="22.22.2.1",
                                        neutron_client=neutron_client))
        return {'ext_networks': ext_networks,
                'ext_vl': ext_vl,
                'ext_mngd_networks': ext_mngd_networks,
                'ext_link_ports': ext_link_ports,
                'ext_subnets': ext_subnets,
                'changed_ext_networks': changed_ext_networks,
                'changed_ext_subnets': changed_ext_subnets}

    @classmethod
    def _list_glance_image(cls, filter_name='cirros-0.5.2-x86_64-disk',
            glance_client=None):
        if glance_client is None:
            glance_client = cls.glance_client
        try:
            images = glance_client.images.list()
        except Exception:
            print("glance-image does not exists.", flush=True)
            return []

        if filter_name is None:
            return images

        return list(filter(lambda image: image.name == filter_name, images))

    @classmethod
    def _get_glance_image(cls, image_id, glance_client=None):
        if glance_client is None:
            glance_client = cls.glance_client
        try:
            image = glance_client.images.get(image_id)
        except Exception:
            print("glance-image does not exists.", image_id, flush=True)
            return None

        return image

    @classmethod
    def _create_glance_image(cls, image_data, file_url, glance_client=None):
        if glance_client is None:
            glance_client = cls.glance_client
        image = glance_client.images.create(**image_data)
        glance_client.images.upload(image.id, file_url)

        return image.id

    def _get_glance_image_list_from_stack_resource(
            self, stack_id, stack_resource_name, h_client=None):
        if h_client is None:
            h_client = self.h_client
        image_id_list = []
        for resource_name in stack_resource_name:
            resource_details = self._get_heat_resource(stack_id,
                    resource_name,
                    h_client)
            image = self._get_image_id_from_resource_attributes(
                resource_details)
            if image:
                image_id_list.append(image.id)

        return image_id_list

    @classmethod
    def _list_zone(cls):
        try:
            zone = cls.nova_client.services.list()
        except nova_client.exceptions.ClientException:
            print("availability zone does not exists.", flush=True)
            return []
        return zone

    def _register_subscription(self, request_body, http_client=None):
        if http_client is None:
            http_client = self.http_client
        resp, response_body = http_client.do_request(
            self.base_subscriptions_url,
            "POST",
            body=jsonutils.dumps(request_body))
        return resp, response_body

    def _delete_subscription(self, subscription_id, tacker_client=None):
        if tacker_client is None:
            tacker_client = self.tacker_client
        delete_url = os.path.join(self.base_subscriptions_url, subscription_id)
        resp, body = tacker_client.do_request(delete_url, "DELETE")

        return resp, body

    def _show_subscription(self, subscription_id, tacker_client=None):
        if tacker_client is None:
            tacker_client = self.tacker_client
        show_url = os.path.join(self.base_subscriptions_url, subscription_id)
        resp, body = tacker_client.do_request(show_url, "GET")

        return resp, body

    def _list_subscription(self, tacker_client=None):
        if tacker_client is None:
            tacker_client = self.tacker_client
        resp, body = tacker_client.do_request(
            self.base_subscriptions_url, "GET")

        return resp, body

    def _list_subscription_filter(self, http_client=None, **kwargs):
        if http_client is None:
            http_client = self.http_client
        params = kwargs.get('params', {})
        filter_variable = params['filter']
        subscriptions_list_filter_url = "%s?%s" % (
            self.base_subscriptions_url, filter_variable)

        resp, subscription_body = http_client.do_request(
            subscriptions_list_filter_url, "GET")

        return resp, subscription_body

    def _create_vnf_instance(self, vnfd_id, vnf_instance_name=None,
            vnf_instance_description=None, http_client=None):
        if http_client is None:
            http_client = self.http_client
        request_body = {'vnfdId': vnfd_id}
        if vnf_instance_name:
            request_body['vnfInstanceName'] = vnf_instance_name

        if vnf_instance_description:
            request_body['vnfInstanceDescription'] = vnf_instance_description

        return self._create_vnf_instance_from_body(request_body, http_client)

    def _create_vnf_instance_from_body(self, request_body, http_client=None):
        if http_client is None:
            http_client = self.http_client
        request_body['vnfInstanceName'] = self._testMethodName
        resp, response_body = http_client.do_request(
            self.base_vnf_instances_url,
            "POST",
            body=jsonutils.dumps(request_body))

        return resp, response_body

    def _delete_vnf_instance(self, id, http_client=None):
        if http_client is None:
            http_client = self.http_client
        url = os.path.join(self.base_vnf_instances_url, id)
        resp, body = http_client.do_request(url, "DELETE")

        return resp, body

    def _show_vnf_instance(self, id, http_client=None):
        if http_client is None:
            http_client = self.http_client
        show_url = os.path.join(self.base_vnf_instances_url, id)
        resp, vnf_instance = http_client.do_request(show_url, "GET")

        return resp, vnf_instance

    def _list_vnf_instance(self, http_client=None, **kwargs):
        if http_client is None:
            http_client = self.http_client
        resp, vnf_instances = http_client.do_request(
            self.base_vnf_instances_url, "GET", **kwargs)

        return resp, vnf_instances

    def _wait_vnf_instance(self, id,
            http_client=None,
            instantiation_state=fields.VnfInstanceState.INSTANTIATED,
            timeout=VNF_INSTANTIATE_TIMEOUT):
        if http_client is None:
            http_client = self.http_client
        start_time = int(time.time())
        while True:
            resp, body = self._show_vnf_instance(id, http_client)
            if body['instantiationState'] == instantiation_state:
                break

            if ((int(time.time()) - start_time) > timeout):
                error = ("Vnf instance %(id)s status is %(current)s, "
                         "expected status should be %(expected)s")
                self.fail(error % {"id": id,
                    "current": body['instantiationState'],
                    "expected": instantiation_state})

            time.sleep(5)

    def _instantiate_vnf_instance(self, id, request_body, http_client=None):
        if http_client is None:
            http_client = self.http_client
        url = os.path.join(self.base_vnf_instances_url, id, "instantiate")
        resp, body = http_client.do_request(url, "POST",
                body=jsonutils.dumps(request_body))

        return resp, body

    def _heal_vnf_instance(self, vnf_instance_id, request_body,
            http_client=None):
        if http_client is None:
            http_client = self.http_client
        url = os.path.join(
            self.base_vnf_instances_url,
            vnf_instance_id,
            "heal")
        resp, body = http_client.do_request(url, "POST",
                body=jsonutils.dumps(request_body))

        return resp, body

    def _scale_vnf_instance(self, vnf_instance_id, request_body,
            http_client=None):
        if http_client is None:
            http_client = self.http_client
        url = os.path.join(
            self.base_vnf_instances_url,
            vnf_instance_id,
            "scale")
        resp, body = http_client.do_request(url, "POST",
                body=jsonutils.dumps(request_body))

        return resp, body

    def _terminate_vnf_instance(self, id, request_body, http_client=None):
        if http_client is None:
            http_client = self.http_client
        url = os.path.join(self.base_vnf_instances_url, id, "terminate")
        resp, body = http_client.do_request(url, "POST",
                body=jsonutils.dumps(request_body))

        return resp, body

    def _update_vnf_instance(self, vnf_instance_id, request_body,
            http_client=None):
        if http_client is None:
            http_client = self.http_client
        url = os.path.join(self.base_vnf_instances_url, vnf_instance_id)
        resp, body = http_client.do_request(url, "PATCH",
                body=jsonutils.dumps(request_body))

        return resp, body

    def _change_ext_conn_vnf_instance(self, vnf_instance_id, request_body,
            http_client=None):
        if http_client is None:
            http_client = self.http_client
        url = os.path.join(
            self.base_vnf_instances_url,
            vnf_instance_id,
            "change_ext_conn")
        resp, body = http_client.do_request(url, "POST",
                body=jsonutils.dumps(request_body))

        return resp, body

    def _rollback_op_occs(self, vnf_lcm_op_occs_id, http_client=None):
        if http_client is None:
            http_client = self.http_client
        rollback_url = os.path.join(
            self.base_vnf_lcm_op_occs_url,
            vnf_lcm_op_occs_id, 'rollback')
        resp, response_body = http_client.do_request(
            rollback_url, "POST")

        return resp, response_body

    def _fail_op_occs(self, vnf_lcm_op_occs_id, http_client=None):
        if http_client is None:
            http_client = self.http_client
        fail_url = os.path.join(
            self.base_vnf_lcm_op_occs_url,
            vnf_lcm_op_occs_id, 'fail')
        resp, response_body = http_client.do_request(
            fail_url, "POST")

        return resp, response_body

    def _retry_op_occs(self, vnf_lcm_op_occs_id, http_client=None):
        if http_client is None:
            http_client = self.http_client
        retry_url = os.path.join(
            self.base_vnf_lcm_op_occs_url,
            vnf_lcm_op_occs_id, 'retry')
        resp, response_body = http_client.do_request(
            retry_url, "POST")

        return resp, response_body

    def _show_op_occs(self, vnf_lcm_op_occs_id, http_client=None):
        if http_client is None:
            http_client = self.http_client
        show_url = os.path.join(
            self.base_vnf_lcm_op_occs_url,
            vnf_lcm_op_occs_id)
        resp, response_body = http_client.do_request(
            show_url, "GET")

        return resp, response_body

    def _wait_terminate_vnf_instance(self, id, timeout=None, http_client=None):
        if http_client is None:
            http_client = self.http_client
        start_time = int(time.time())

        self._wait_vnf_instance(id,
            http_client,
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

    def _get_heat_stack(self, vnf_instance_id, h_client=None,
            prefix_id='vnflcm_'):
        if h_client is None:
            h_client = self.h_client
        try:
            stacks = h_client.stacks.list()
        except Exception:
            return None

        target_stack_name = prefix_id + vnf_instance_id
        target_stakcs = list(
            filter(
                lambda x: x.stack_name == target_stack_name,
                stacks))

        if len(target_stakcs) == 0:
            return None

        return target_stakcs[0]

    def _delete_heat_stack(self, stack_id, h_client=None):
        if h_client is None:
            h_client = self.h_client
        h_client.stacks.delete(stack_id)

    def _wait_until_stack_ready(self, stack_id, expected_status,
            h_client=None):
        if h_client is None:
            h_client = self.h_client
        start_time = time.time()
        callback_url = os.path.join(
            MOCK_NOTIFY_CALLBACK_URL,
            self._testMethodName)

        while True:
            stack = h_client.stacks.get(stack_id)
            actual_status = stack.stack_status
            print(
                ("Wait:callback_url=<%s>, " +
                "wait_status=<%s> ") %
                (callback_url, actual_status),
                flush=True)

            if actual_status == expected_status:
                return None

            if time.time() - start_time > VNF_LCM_DONE_TIMEOUT:
                if actual_status:
                    error = (
                        "LCM incomplete timeout, " +
                        " stack %(stack_id)s" +
                        " is %(actual)s," +
                        "expected status should be %(expected)s")
                    self.fail(
                        error % {
                            "stack_id": stack_id,
                            "expected": expected_status,
                            "actual": actual_status})
                else:
                    self.fail("LCM incomplete timeout")

            time.sleep(RETRY_WAIT_TIME)

    def _get_heat_resource_list(self, stack_id, nested_depth=0,
            h_client=None):
        if h_client is None:
            h_client = self.h_client
        try:
            resources = h_client.resources.list(
                stack_id, nested_depth=nested_depth)
        except Exception:
            return None

        return resources

    def _get_heat_resource(self, stack_id, resource_name, h_client=None):
        if h_client is None:
            h_client = self.h_client
        try:
            resource = h_client.resources.get(
                stack_id, resource_name)
        except Exception:
            return None

        return resource

    def _get_heat_stack_template(self, stack_id, nested_depth=0,
            h_client=None):
        if h_client is None:
            h_client = self.h_client
        try:
            template = h_client.stacks.template(stack_id)
        except Exception:
            return None

        return template

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
            limit=2,
            h_client=None):
        if h_client is None:
            h_client = self.h_client
        resources = self._get_heat_resource_list(
            stack_id, nested_depth=nested_depth, h_client=h_client)
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
            h_client=None,
            expected_stack_status=infra_cnst.STACK_CREATE_COMPLETE):
        if h_client is None:
            h_client = self.h_client
        stack = self._get_heat_stack(vnf_instance_id, h_client)
        self.assertEqual(
            expected_stack_status,
            stack.stack_status)

    def assert_heat_resource_status(
            self,
            vnf_instance,
            h_client=None,
            expected_glance_image=None,
            expected_resource_status=None):

        if h_client is None:
            h_client = self.h_client

        def assert_glance_image(stack_id, resource_name, h_client):
            resource_details = self._get_heat_resource(stack_id,
                    resource_name,
                    h_client)
            image = self._get_image_id_from_resource_attributes(
                resource_details)
            if image:
                self.assertEqual(expected_glance_image, image.status)

        stack = self._get_heat_stack(vnf_instance['id'], h_client)
        resources = self._get_heat_resource_list(stack.id,
                nested_depth=2, h_client=h_client)
        self.assertIsNotNone(resources)

        for resource in resources:
            # FT-checkpoint: resource status
            self.assertEqual(expected_resource_status,
                resource.resource_status)

            # FT-checkpoint: Glance-image
            if expected_glance_image:
                assert_glance_image(stack.id, resource.resource_name,
                        h_client)

    def assert_heat_resource_status_is_none(
            self,
            stack_id,
            h_client=None,
            glance_client=None,
            resources_name_list=None,
            glance_image_id_list=None):
        if h_client is None:
            h_client = self.h_client
        if glance_client is None:
            glance_client = self.glance_client
        resources_name_list = resources_name_list or []
        for resource_name in resources_name_list:
            resource = self._get_heat_resource(stack_id,
                    resource_name,
                    h_client)
            self.assertIsNone(resource)

        glance_image_id_list = glance_image_id_list or []
        for glance_image_id in glance_image_id_list:
            image = self._get_glance_image(glance_image_id,
                    glance_client)
            self.assertIsNone(image)

    def _wait_lcm_done(self,
            expected_operation_status=None,
            vnf_instance_id=None,
            fake_server_manager=None):
        if fake_server_manager is None:
            fake_server_manager = FAKE_SERVER_MANAGER
        start_time = int(time.time())
        callback_url = os.path.join(
            MOCK_NOTIFY_CALLBACK_URL,
            self._testMethodName)

        while True:
            actual_status = None
            vnf_lcm_op_occ_id = None
            notify_mock_responses = fake_server_manager.get_history(
                callback_url)
            print(
                ("Wait:callback_url=<%s>, " +
                "wait_status=<%s>, " +
                "vnf_instance_id=<%s>") %
                (callback_url, expected_operation_status, vnf_instance_id),
                flush=True)

            for res in notify_mock_responses:
                if vnf_instance_id != res.request_body.get('vnfInstanceId'):
                    continue

                if expected_operation_status is None:
                    return

                actual_status = res.request_body.get('operationState', '')
                vnf_lcm_op_occ_id = res.request_body.get('vnfLcmOpOccId', '')
                if actual_status == expected_operation_status:
                    return

            if ((int(time.time()) - start_time) > VNF_LCM_DONE_TIMEOUT):
                if actual_status:
                    error = (
                        "LCM incomplete timeout, %(vnf_lcm_op_occ_id)s" +
                        " is %(actual)s," +
                        "expected status should be %(expected)s")
                    self.fail(
                        error % {
                            "vnf_lcm_op_occ_id": vnf_lcm_op_occ_id,
                            "expected": expected_operation_status,
                            "actual": actual_status})
                else:
                    self.fail("LCM incomplete timeout")

            time.sleep(RETRY_WAIT_TIME)

    def _wait_stack_update(self, vnf_instance_id, expected_status,
            h_client=None):
        if h_client is None:
            h_client = self.h_client
        timeout = VNF_HEAL_TIMEOUT
        start_time = int(time.time())
        while True:
            stack = self._get_heat_stack(vnf_instance_id, h_client)
            if stack.stack_status == expected_status:
                break

            if ((int(time.time()) - start_time) > timeout):
                error = ("Stack %(id)s status is %(current)s, expected status "
                        "should be %(expected)s")
                self.fail(error % {"vnf_instance_name": vnf_instance_id,
                    "current": stack.status,
                    "expected": expected_status})

            time.sleep(RETRY_WAIT_TIME)

    def assert_create_vnf(self, resp, vnf_instance,
            fake_server_manager=None):
        if fake_server_manager is None:
            fake_server_manager = FAKE_SERVER_MANAGER
        self.assertEqual(201, resp.status_code)

        self.assert_http_header_location_for_create(resp.headers)
        self.assert_instantiation_state(
            vnf_instance,
            fields.VnfInstanceState.NOT_INSTANTIATED)

        # FT-checkpoint: Notification
        callback_url = os.path.join(
            MOCK_NOTIFY_CALLBACK_URL,
            self._testMethodName)
        notify_mock_responses = self._filter_notify_history(callback_url,
            vnf_instance.get('id'),
            fake_server_manager=fake_server_manager)

        self.assertEqual(1, len(notify_mock_responses))
        self.assert_notification_mock_response(
            notify_mock_responses[0],
            'VnfIdentifierCreationNotification')

    def assert_delete_vnf(self, resp, vnf_instance_id, http_client=None,
            fake_server_manager=None):
        self.assertEqual(204, resp.status_code)

        if http_client is None:
            http_client = self.http_client
        if fake_server_manager is None:
            fake_server_manager = FAKE_SERVER_MANAGER

        resp, _ = self._show_vnf_instance(vnf_instance_id, http_client)
        self.assertEqual(404, resp.status_code)

        # FT-checkpoint: Notification
        callback_url = os.path.join(
            MOCK_NOTIFY_CALLBACK_URL,
            self._testMethodName)
        notify_mock_responses = self._filter_notify_history(callback_url,
            vnf_instance_id, fake_server_manager=fake_server_manager)

        self.assertEqual(1, len(notify_mock_responses))
        self.assert_notification_mock_response(
            notify_mock_responses[0],
            'VnfIdentifierDeletionNotification')

    def assert_instantiate_vnf(
            self,
            resp,
            vnf_instance_id,
            http_client=None,
            h_client=None,
            fake_server_manager=None):
        if http_client is None:
            http_client = self.http_client
        if h_client is None:
            h_client = self.h_client
        if fake_server_manager is None:
            fake_server_manager = FAKE_SERVER_MANAGER

        self.assertEqual(202, resp.status_code)
        resp, vnf_instance = self._show_vnf_instance(vnf_instance_id,
                http_client)
        self.assert_vnf_state(vnf_instance)

        self.assert_heat_stack_status(vnf_instance['id'], h_client)
        self.assert_heat_resource_status(
            vnf_instance,
            h_client,
            expected_glance_image='active',
            expected_resource_status='CREATE_COMPLETE')

        # FT-checkpoint: Notification
        callback_url = os.path.join(
            MOCK_NOTIFY_CALLBACK_URL,
            self._testMethodName)
        notify_mock_responses = self._filter_notify_history(callback_url,
            vnf_instance_id, fake_server_manager=fake_server_manager)

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
            expected_stack_status='UPDATE_COMPLETE',
            http_client=None,
            h_client=None,
            fake_server_manager=None):
        if http_client is None:
            http_client = self.http_client
        if h_client is None:
            h_client = self.h_client
        if fake_server_manager is None:
            fake_server_manager = FAKE_SERVER_MANAGER

        self.assertEqual(202, resp.status_code)

        resp, vnf_instance = self._show_vnf_instance(vnf_instance_id,
                http_client)
        self.assert_vnf_state(vnf_instance)
        self.assert_instantiation_state(vnf_instance)

        self.assert_heat_stack_status(
            vnf_instance['id'],
            h_client,
            expected_stack_status=expected_stack_status)

        # FT-checkpoint: Notification
        callback_url = os.path.join(
            MOCK_NOTIFY_CALLBACK_URL,
            self._testMethodName)
        notify_mock_responses = self._filter_notify_history(callback_url,
            vnf_instance_id, fake_server_manager=fake_server_manager)

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
            glance_image_id_list,
            http_client=None,
            h_client=None,
            glance_client=None,
            fake_server_manager=None):
        if http_client is None:
            http_client = self.http_client
        if h_client is None:
            h_client = self.h_client
        if glance_client is None:
            glance_client = self.glance_client
        if fake_server_manager is None:
            fake_server_manager = FAKE_SERVER_MANAGER

        self.assertEqual(202, resp.status_code)

        resp, vnf_instance = self._show_vnf_instance(vnf_instance_id,
                http_client)
        self.assert_instantiation_state(
            vnf_instance,
            fields.VnfInstanceState.NOT_INSTANTIATED)

        # FT-checkpoint: Heat stack status.
        stack = self._get_heat_stack(vnf_instance_id, h_client)
        self.assertIsNone(stack)

        self.assert_heat_resource_status_is_none(
            stack_id,
            h_client,
            glance_client,
            resources_name_list=resource_name_list,
            glance_image_id_list=glance_image_id_list)

        # FT-checkpoint: Notification
        callback_url = os.path.join(
            MOCK_NOTIFY_CALLBACK_URL,
            self._testMethodName)
        notify_mock_responses = self._filter_notify_history(callback_url,
            vnf_instance_id, fake_server_manager=fake_server_manager)

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

    def assert_scale_vnf(
            self,
            resp,
            vnf_instance_id,
            pre_stack_resource_list,
            post_stack_resource_list,
            scale_type='SCALE_OUT',
            expected_stack_status='CREATE_COMPLETE',
            http_client=None,
            h_client=None,
            fake_server_manager=None):
        if http_client is None:
            http_client = self.http_client
        if h_client is None:
            h_client = self.h_client
        if fake_server_manager is None:
            fake_server_manager = FAKE_SERVER_MANAGER
        self.assertEqual(202, resp.status_code)
        self.assert_http_header_location_for_lcm_op_occs(resp.headers)

        resp, vnf_instance = self._show_vnf_instance(vnf_instance_id,
                http_client)
        self.assert_vnf_state(vnf_instance)
        self.assert_instantiation_state(vnf_instance)

        # check: scaling stack resource count
        if scale_type == 'SCALE_OUT':
            self.assertTrue(len(pre_stack_resource_list) <
                            len(post_stack_resource_list))
        else:
            self.assertTrue(len(pre_stack_resource_list) >
                            len(post_stack_resource_list))

        # check scaleStatus
        scale_status = vnf_instance['instantiatedVnfInfo']['scaleStatus']
        self.assertTrue(len(scale_status) > 0)
        for status in scale_status:
            self.assertIsNotNone(status.get('aspectId'))
            self.assertIsNotNone(status.get('scaleLevel'))

        self.assert_heat_stack_status(
            vnf_instance['id'],
            h_client,
            expected_stack_status=expected_stack_status)

        # FT-checkpoint: Notification
        callback_url = os.path.join(
            MOCK_NOTIFY_CALLBACK_URL,
            self._testMethodName)
        notify_mock_responses = self._filter_notify_history(callback_url,
            vnf_instance_id, fake_server_manager=fake_server_manager)

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

    def assert_rollback_vnf(self, resp, vnf_instance_id,
            fake_server_manager=None):
        self.assertEqual(202, resp.status_code)

        if fake_server_manager is None:
            fake_server_manager = FAKE_SERVER_MANAGER
        # FT-checkpoint: Notification
        callback_url = os.path.join(
            MOCK_NOTIFY_CALLBACK_URL,
            self._testMethodName)
        notify_mock_responses = self._filter_notify_history(callback_url,
            vnf_instance_id, fake_server_manager=fake_server_manager)

        self.assertEqual(2, len(notify_mock_responses))
        self.assert_notification_mock_response(
            notify_mock_responses[0],
            'VnfLcmOperationOccurrenceNotification',
            'ROLLING_BACK')

        self.assert_notification_mock_response(
            notify_mock_responses[1],
            'VnfLcmOperationOccurrenceNotification',
            'ROLLED_BACK')

    def assert_fail_vnf(self, resp, vnf_instance_id,
            fake_server_manager=None):
        self.assertEqual(200, resp.status_code)

        if fake_server_manager is None:
            fake_server_manager = FAKE_SERVER_MANAGER
        # FT-checkpoint: Notification
        callback_url = os.path.join(
            MOCK_NOTIFY_CALLBACK_URL,
            self._testMethodName)
        notify_mock_responses = self._filter_notify_history(callback_url,
            vnf_instance_id, fake_server_manager=fake_server_manager)

        self.assertEqual(1, len(notify_mock_responses))
        self.assert_notification_mock_response(
            notify_mock_responses[0],
            'VnfLcmOperationOccurrenceNotification',
            'FAILED')

    def assert_retry_vnf(self, resp, vnf_instance_id,
            fake_server_manager=None):
        self.assertEqual(202, resp.status_code)

        if fake_server_manager is None:
            fake_server_manager = FAKE_SERVER_MANAGER
        # FT-checkpoint: Notification
        callback_url = os.path.join(
            MOCK_NOTIFY_CALLBACK_URL,
            self._testMethodName)
        notify_mock_responses = self._filter_notify_history(callback_url,
            vnf_instance_id, fake_server_manager=fake_server_manager)

        self.assertEqual(2, len(notify_mock_responses))
        self.assert_notification_mock_response(
            notify_mock_responses[0],
            'VnfLcmOperationOccurrenceNotification',
            'PROCESSING')

        self.assert_notification_mock_response(
            notify_mock_responses[1],
            'VnfLcmOperationOccurrenceNotification',
            'FAILED_TEMP')

    def assert_update_vnf(
            self,
            resp,
            vnf_instance_id,
            expected_stack_status='CREATE_COMPLETE',
            http_client=None,
            h_client=None,
            fake_server_manager=None):
        if http_client is None:
            http_client = self.http_client
        if h_client is None:
            h_client = self.h_client
        if fake_server_manager is None:
            fake_server_manager = FAKE_SERVER_MANAGER
        self.assertEqual(202, resp.status_code)
        self.assert_http_header_location_for_lcm_op_occs(resp.headers)

        resp, vnf_instance = self._show_vnf_instance(vnf_instance_id,
                http_client)
        self.assertEqual(200, resp.status_code)

        self.assert_vnf_state(vnf_instance)
        self.assert_instantiation_state(vnf_instance)

        self.assert_heat_stack_status(
            vnf_instance['id'],
            h_client,
            expected_stack_status=expected_stack_status)

        # FT-checkpoint: Notification
        callback_url = os.path.join(
            MOCK_NOTIFY_CALLBACK_URL,
            self._testMethodName)
        notify_mock_responses = self._filter_notify_history(callback_url,
            vnf_instance_id, fake_server_manager=fake_server_manager)

        self.assertEqual(2, len(notify_mock_responses))
        self.assert_notification_mock_response(
            notify_mock_responses[0],
            'VnfLcmOperationOccurrenceNotification',
            'PROCESSING')

        self.assert_notification_mock_response(
            notify_mock_responses[1],
            'VnfLcmOperationOccurrenceNotification',
            'COMPLETED')

    def assert_notification_get(self, callback_url,
            fake_server_manager=None):
        if fake_server_manager is None:
            fake_server_manager = FAKE_SERVER_MANAGER
        notify_mock_responses = fake_server_manager.get_history(
            callback_url)
        fake_server_manager.clear_history(
            callback_url)
        self.assertEqual(1, len(notify_mock_responses))
        self.assertEqual(204, notify_mock_responses[0].status_code)

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

    def _create_network(self, name, neutron_client=None):
        # First, we have to check network name passed by caller is
        # already exists or not.
        # OK, we can create this.

        if neutron_client is None:
            neutron_client = self.neutronclient()
        try:
            uniq_name = name + '-' + uuidutils.generate_uuid()
            net = \
                self.neutronclient().create_network(
                    {'network': {'name': uniq_name}})
            net_id = net['network']['id']
            self.addCleanup(self._delete_network, net_id)
            print("Create network success, %s" % uniq_name, flush=True)
            return net_id, uniq_name
        except Exception as e:
            self.fail("Failed, create network=<%s>, %s" %
                (uniq_name, e))

    def _create_subnet(self, network, cidr, gateway, neutron_client=None):
        if neutron_client is None:
            neutron_client = self.neutronclient()
        body = {'subnet': {'network_id': network['id'],
                'name': "subnet-%s" % uuidutils.generate_uuid(),
                'cidr': "{}".format(cidr),
                'ip_version': 4,
                'gateway_ip': "{}".format(gateway),
                "enable_dhcp": True}}

        try:
            subnet = neutron_client.create_subnet(body=body)["subnet"]
            self.addCleanup(self._delete_subnet, subnet['id'], neutron_client)
            print("Create subnet success, %s" % subnet['id'], flush=True)
            return subnet['id']
        except Exception as e:
            self.fail("Failed, create subnet for net_id=<%s>, %s" %
                (network['id'], e))

    def _create_port(self, network_id, neutron_client=None):
        if neutron_client is None:
            neutron_client = self.neutronclient()
        body = {'port': {'network_id': network_id}}
        try:
            port = neutron_client.create_port(body=body)["port"]
            self.addCleanup(self._delete_port, port['id'], neutron_client)
            return port['id']
        except Exception as e:
            self.fail("Failed, create port for net_id=<%s>, %s" %
                (network_id, e))

    def _delete_network(self, network_id, neutron_client=None):
        if neutron_client is None:
            neutron_client = self.neutronclient()
        try:
            neutron_client.delete_network(network_id)
        except Exception:
            print("Failed, delete network.", network_id, flush=True)

    def _delete_subnet(self, subnet_id, neutron_client=None):
        if neutron_client is None:
            neutron_client = self.neutronclient()
        try:
            neutron_client.delete_subnet(subnet_id)
        except Exception:
            print("Failed, delete subnet.", subnet_id, flush=True)

    def _delete_port(self, port_id, neutron_client):
        if neutron_client is None:
            neutron_client = self.neutronclient()
        try:
            neutron_client.delete_port(port_id)
        except Exception:
            print("Failed, delete port.", port_id, flush=True)

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

    def _filter_notify_history(self, callback_url, vnf_instance_id,
            fake_server_manager=None):
        if fake_server_manager is None:
            fake_server_manager = FAKE_SERVER_MANAGER
        notify_histories = fake_server_manager.get_history(
            callback_url)
        fake_server_manager.clear_history(callback_url)

        return [
            h for h in notify_histories
            if h.request_body.get('vnfInstanceId') == vnf_instance_id]

    def _get_heat_stack_show(self, vnf_instance_id, resource_name=None,
            h_client=None):
        """Retrieve image name of the resource from stack"""
        if h_client is None:
            h_client = self.h_client
        try:
            stack = self._get_heat_stack(vnf_instance_id, h_client)
            stack_info = h_client.stacks.get(stack.id)
            stack_dict = stack_info.to_dict()
            resource_dict = json.loads(stack_dict['parameters']['nfv'])
        except Exception:
            return None

        if resource_name is None:
            return resource_dict

        return resource_dict['VDU'][resource_name]['image']
