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

import base64
import datetime
import hashlib
import io
import json
import os
import requests
import shutil
import tempfile
import uuid
import zipfile

import ddt
from oslo_config import cfg
from requests_mock.contrib import fixture as requests_mock_fixture
from tacker import auth
from tacker.tests import base

from tacker.tests.unit.vnfm.infra_drivers.openstack.fixture_data import client
from tacker.tests.unit.vnfpkgm import fakes
from tacker.tests import utils
from tacker.tests import uuidsentinel
import tacker.vnfm.nfvo_client as nfvo_client
from unittest import mock


def _count_mock_history(history, *url):
    req_count = 0
    for mock_history in history:
        actual_url = '{}://{}'.format(mock_history.scheme,
              mock_history.hostname)
        if actual_url in url:
            req_count += 1
    return req_count


@ddt.ddt
class TestVnfPackageRequest(base.BaseTestCase):

    client_fixture_class = client.ClientFixture
    sdk_connection_fixure_class = client.SdkConnectionFixture

    def setUp(self):
        super(TestVnfPackageRequest, self).setUp()
        self.requests_mock = self.useFixture(requests_mock_fixture.Fixture())
        self.url = "http://nfvo.co.jp/vnfpkgm/v1/vnf_packages"
        self.nfvo_url = "http://nfvo.co.jp"
        self.test_package_dir = 'tacker/tests/unit/vnfm/'
        self.headers = {'Content-Type': 'application/json'}

        self.token_endpoint = 'https://oauth2/tokens'
        self.oauth_url = 'https://oauth2'
        self.auth_user_name = 'test_user'
        self.auth_password = 'test_password'

        cfg.CONF.set_override('auth_type', None,
                              group='authentication')
        cfg.CONF.set_override(
            "base_url",
            self.url,
            group='connect_vnf_packages')
        cfg.CONF.set_default(
            name='pipeline',
            group='connect_vnf_packages',
            default=[
                "package_content",
                "vnfd"])
        cfg.CONF.set_override('user_name', self.auth_user_name,
                              group='authentication')
        cfg.CONF.set_override('password', self.auth_password,
                              group='authentication')
        cfg.CONF.set_override('token_endpoint', self.token_endpoint,
                              group='authentication')
        cfg.CONF.set_override('client_id', self.auth_user_name,
                              group='authentication')
        cfg.CONF.set_override('client_password', self.auth_password,
                              group='authentication')
        auth.auth_manager = auth._AuthManager()
        nfvo_client.VnfPackageRequest._connector = nfvo_client._Connect(
            2, 1, 20)

    def tearDown(self):
        super(TestVnfPackageRequest, self).tearDown()
        self.addCleanup(mock.patch.stopall)

    def assert_auth_basic(self, acutual_request):
        actual_auth = acutual_request._request.headers.get("Authorization")
        expected_auth = base64.b64encode(
            '{}:{}'.format(
                self.auth_user_name,
                self.auth_password).encode('utf-8')).decode()
        self.assertEqual("Basic " + expected_auth, actual_auth)

    def assert_auth_client_credentials(self, acutual_request, expected_token):
        actual_auth = acutual_request._request.headers.get(
            "Authorization")
        self.assertEqual("Bearer " + expected_token, actual_auth)

    def assert_zipfile(
            self,
            actual_zip,
            expected_zips,
            expected_artifacts=None):
        expected_artifacts = expected_artifacts if expected_artifacts else []

        def check_zip(expected_zip):
            self.assertIsInstance(expected_zip, zipfile.ZipFile)
            for expected_name in expected_zip.namelist():
                expected_checksum = hashlib.sha256(
                    expected_zip.read(expected_name)).hexdigest()
                actual_checksum = hashlib.sha256(
                    actual_zip.read(expected_name)).hexdigest()
                self.assertEqual(expected_checksum, actual_checksum)

        try:
            self.assertIsInstance(actual_zip, zipfile.ZipFile)
            self.assertIsNone(actual_zip.testzip())

            expected_elm_cnt = sum(
                map(lambda x: len(x.namelist()), expected_zips))
            self.assertEqual(expected_elm_cnt +
                    len(expected_artifacts), len(actual_zip.namelist()))

            for expected_zip in expected_zips:
                check_zip(expected_zip)

            for expected_artifact in expected_artifacts:
                expected_checksum = hashlib.sha256(
                    open(expected_artifact, 'rb').read()).hexdigest()
                actual_checksum = hashlib.sha256(
                    actual_zip.read(expected_artifact)).hexdigest()
                self.assertEqual(expected_checksum, actual_checksum)
        except Exception as e:
            self.fail(e)

    def json_serial_date_to_dict(self, json_obj):
        def json_serial(obj):
            if isinstance(obj, datetime.datetime):
                return obj.isoformat()

            raise TypeError("Type %s not serializable" % type(obj))

        serial_json_str = json.dumps(json_obj, default=json_serial)
        return json.loads(serial_json_str)

    def test_init(self):
        self.assertEqual(self.url, cfg.CONF.connect_vnf_packages.base_url)
        self.assertEqual(["package_content", "vnfd"],
                         cfg.CONF.connect_vnf_packages.pipeline)
        self.assertEqual(2, cfg.CONF.connect_vnf_packages.retry_num)
        self.assertEqual(30, cfg.CONF.connect_vnf_packages.retry_wait)
        self.assertEqual(20, cfg.CONF.connect_vnf_packages.timeout)

    def _make_zip_file_from_sample(self, dir_name, read_vnfd_only=False):
        unique_name = str(uuid.uuid4())
        temp_dir = os.path.join('/tmp', unique_name)
        utils.copy_csar_files(temp_dir, dir_name, read_vnfd_only)
        tempfd, temp_filepath = tempfile.mkstemp(suffix=".zip", dir=temp_dir)
        os.close(tempfd)
        zipfile.ZipFile(temp_filepath, 'w')
        self.addCleanup(shutil.rmtree, temp_dir)
        return temp_filepath

    @ddt.data({'content': 'vnfpkgm1',
    'vnfd': None,
    'artifacts': None},
    {'content': None,
    'vnfd': 'vnfpkgm2',
    'artifacts': None},
        {'content': None,
    'vnfd': None,
    'artifacts': ["vnfd_lcm_user_data.yaml"]},
        {'content': 'vnfpkgm1',
    'vnfd': 'vnfpkgm2',
    'artifacts': ["vnfd_lcm_user_data.yaml"]},
        {'content': 'vnfpkgm1',
    'vnfd': None,
    'artifacts': None},
        {'content': None,
    'vnfd': 'vnfpkgm2',
    'artifacts': ["vnfd_lcm_user_data.yaml"]},
        {'content': 'vnfpkgm1',
    'vnfd': 'vnfpkgm2',
    'artifacts': ["vnfd_lcm_user_data.yaml"]},
    )
    @ddt.unpack
    def test_download_vnf_packages(self, content, vnfd, artifacts):
        fetch_base_url = os.path.join(self.url, uuidsentinel.vnf_pkg_id)
        expected_connect_cnt = 0
        pipelines = []

        if content:
            expected_connect_cnt += 1
            pipelines.append('package_content')
            path = self._make_zip_file_from_sample(content)
            with open(path, 'rb') as test_package_content_zip_obj:
                expected_package_content_zip = zipfile.ZipFile(
                    io.BytesIO(test_package_content_zip_obj.read()))
                test_package_content_zip_obj.seek(0)
                self.requests_mock.register_uri(
                    'GET',
                    os.path.join(
                        fetch_base_url,
                        'package_content'),
                    content=test_package_content_zip_obj.read(),
                    headers={
                        'Content-Type': 'application/zip'},
                    status_code=200)

        if vnfd:
            expected_connect_cnt += 1
            pipelines.append('vnfd')
            path = self._make_zip_file_from_sample(vnfd, read_vnfd_only=True)
            with open(path, 'rb') as test_vnfd_zip_obj:
                expected_vnfd_zip = zipfile.ZipFile(
                    io.BytesIO(test_vnfd_zip_obj.read()))
                test_vnfd_zip_obj.seek(0)
                self.requests_mock.register_uri(
                    'GET',
                    os.path.join(
                        fetch_base_url,
                        'vnfd'),
                    content=test_vnfd_zip_obj.read(),
                    headers={
                        'Content-Type': 'application/zip'},
                    status_code=200)

        if artifacts:
            pipelines.append('artifacts')
            artifacts = [os.path.join("tacker/tests/etc/samples", p)
                         for p in artifacts]
            for artifact_path in artifacts:
                expected_connect_cnt += 1
                with open(artifact_path, 'rb') as artifact_path_obj:
                    self.requests_mock.register_uri(
                        'GET',
                        os.path.join(
                            fetch_base_url,
                            'artifacts',
                            artifact_path),
                        headers={
                            'Content-Type': 'application/octet-stream'},
                        status_code=200,
                        content=artifact_path_obj.read())

        cfg.CONF.set_default(
            name='pipeline',
            group='connect_vnf_packages',
            default=pipelines)

        if artifacts:
            res = nfvo_client.VnfPackageRequest.download_vnf_packages(
                uuidsentinel.vnf_pkg_id, artifacts)
        else:
            res = nfvo_client.VnfPackageRequest.download_vnf_packages(
                uuidsentinel.vnf_pkg_id)

        history = self.requests_mock.request_history
        req_count = _count_mock_history(history, self.nfvo_url)

        self.assertIsInstance(res, io.BytesIO)
        actual_zip = zipfile.ZipFile(res)
        if content and vnfd:
            self.assert_zipfile(
                actual_zip, [
                    expected_package_content_zip,
                    expected_vnfd_zip],
                artifacts)
        elif content:
            self.assert_zipfile(
                actual_zip, [expected_package_content_zip], artifacts)
        elif vnfd:
            self.assert_zipfile(
                actual_zip, [expected_vnfd_zip], artifacts)
        else:
            self.assert_zipfile(
                actual_zip, [], artifacts)

        self.assertEqual(expected_connect_cnt, req_count)

    def test_download_vnf_packages_with_auth_basic(self):
        cfg.CONF.set_override('auth_type', 'BASIC',
                              group='authentication')
        auth.auth_manager = auth._AuthManager()

        expected_connect_cnt = \
            self._download_vnf_packages_all_pipeline_with_assert()
        history = self.requests_mock.request_history
        req_count = _count_mock_history(history, self.nfvo_url)
        self.assertEqual(expected_connect_cnt, req_count)
        for h in history:
            self.assert_auth_basic(h)

    def test_download_vnf_packages_with_auth_client_credentials(self):
        cfg.CONF.set_override('auth_type', 'OAUTH2_CLIENT_CREDENTIALS',
                              group='authentication')

        expected_connect_cnt = 1
        self.requests_mock.register_uri('GET',
            self.token_endpoint,
            json={'access_token': 'test_token', 'token_type': 'bearer'},
            headers={'Content-Type': 'application/json'},
            status_code=200)

        auth.auth_manager = auth._AuthManager()

        expected_connect_cnt += \
            self._download_vnf_packages_all_pipeline_with_assert()
        history = self.requests_mock.request_history
        req_count = _count_mock_history(history, self.nfvo_url, self.oauth_url)
        self.assertEqual(expected_connect_cnt, req_count)
        self.assert_auth_basic(history[0])
        for h in history[1:]:
            self.assert_auth_client_credentials(h, "test_token")

    def _download_vnf_packages_all_pipeline_with_assert(self):
        fetch_base_url = os.path.join(self.url, uuidsentinel.vnf_pkg_id)
        expected_connect_cnt = 0
        pipelines = []

        content = 'vnfpkgm1'
        expected_connect_cnt += 1
        pipelines.append('package_content')
        path = self._make_zip_file_from_sample(content)
        with open(path, 'rb') as test_package_content_zip_obj:
            expected_package_content_zip = zipfile.ZipFile(
                io.BytesIO(test_package_content_zip_obj.read()))
            test_package_content_zip_obj.seek(0)
            self.requests_mock.register_uri(
                'GET',
                os.path.join(
                    fetch_base_url,
                    'package_content'),
                content=test_package_content_zip_obj.read(),
                headers={
                    'Content-Type': 'application/zip'},
                status_code=200)

        vnfd = 'vnfpkgm2'
        expected_connect_cnt += 1
        pipelines.append('vnfd')
        path = self._make_zip_file_from_sample(vnfd, read_vnfd_only=True)
        with open(path, 'rb') as test_vnfd_zip_obj:
            expected_vnfd_zip = zipfile.ZipFile(
                io.BytesIO(test_vnfd_zip_obj.read()))
            test_vnfd_zip_obj.seek(0)
            self.requests_mock.register_uri(
                'GET',
                os.path.join(
                    fetch_base_url,
                    'vnfd'),
                content=test_vnfd_zip_obj.read(),
                headers={
                    'Content-Type': 'application/zip'},
                status_code=200)

        artifacts = ["vnfd_lcm_user_data.yaml"]
        pipelines.append('artifacts')
        artifacts = [os.path.join("tacker/tests/etc/samples", p)
                    for p in artifacts]
        for artifact_path in artifacts:
            expected_connect_cnt += 1
            with open(artifact_path, 'rb') as artifact_path_obj:
                self.requests_mock.register_uri(
                    'GET',
                    os.path.join(
                        fetch_base_url,
                        'artifacts',
                        artifact_path),
                    headers={
                        'Content-Type': 'application/octet-stream'},
                    status_code=200,
                    content=artifact_path_obj.read())

        cfg.CONF.set_default(
            name='pipeline',
            group='connect_vnf_packages',
            default=pipelines)

        res = nfvo_client.VnfPackageRequest.download_vnf_packages(
            uuidsentinel.vnf_pkg_id, artifacts)
        self.assertIsInstance(res, io.BytesIO)

        actual_zip = zipfile.ZipFile(res)
        self.assert_zipfile(
            actual_zip, [
                expected_package_content_zip,
                expected_vnfd_zip], artifacts)

        return expected_connect_cnt

    def test_download_vnf_packages_content_disposition(self):
        fetch_base_url = os.path.join(self.url, uuidsentinel.vnf_pkg_id)
        test_yaml_filepath = os.path.join(
            'tacker/tests/etc/samples',
            'vnfd_lcm_user_data.yaml')
        with open(test_yaml_filepath, 'rb') as test_yaml_obj:
            headers = {
                'Content-Type': 'application/octet-stream',
                'Content-Disposition':
                    'filename={}'.format(test_yaml_filepath)}
            self.requests_mock.register_uri(
                'GET',
                os.path.join(
                    fetch_base_url,
                    'vnfd'),
                content=test_yaml_obj.read(),
                headers=headers,
                status_code=200)

        cfg.CONF.set_default(
            name='pipeline',
            group='connect_vnf_packages',
            default=['vnfd'])

        res = nfvo_client.VnfPackageRequest.download_vnf_packages(
            uuidsentinel.vnf_pkg_id)
        history = self.requests_mock.request_history
        req_count = _count_mock_history(history, self.nfvo_url)
        self.assertEqual(1, req_count)

        self.assertIsInstance(res, io.BytesIO)
        actual_zip = zipfile.ZipFile(res)
        self.assert_zipfile(actual_zip, [], [test_yaml_filepath])

    def test_download_vnf_packages_non_content_disposition_raise_download(
            self):
        fetch_base_url = os.path.join(self.url, uuidsentinel.vnf_pkg_id)
        test_yaml_filepath = os.path.join(
            'tacker/tests/etc/samples',
            'vnfd_lcm_user_data.yaml')
        with open(test_yaml_filepath, 'rb') as test_yaml_obj:
            headers = {'Content-Type': 'application/octet-stream'}
            self.requests_mock.register_uri(
                'GET',
                os.path.join(
                    fetch_base_url,
                    'vnfd'),
                content=test_yaml_obj.read(),
                headers=headers,
                status_code=200)

        cfg.CONF.set_default(
            name='pipeline',
            group='connect_vnf_packages',
            default=['vnfd'])

        self.assertRaises(
            nfvo_client.FaliedDownloadContentException,
            nfvo_client.VnfPackageRequest.download_vnf_packages,
            uuidsentinel.vnf_pkg_id)

        history = self.requests_mock.request_history
        req_count = _count_mock_history(history, self.nfvo_url)
        self.assertEqual(1, req_count)

    def test_download_vnf_packages_with_retry_raise_not_found(self):

        fetch_base_url = os.path.join(self.url, uuidsentinel.vnf_pkg_id)
        self.requests_mock.register_uri(
            'GET',
            os.path.join(
                fetch_base_url,
                'package_content'),
            headers=self.headers,
            status_code=404)

        try:
            nfvo_client.VnfPackageRequest.download_vnf_packages(
                uuidsentinel.vnf_pkg_id)
        except requests.exceptions.RequestException as e:
            self.assertEqual(404, e.response.status_code)

        history = self.requests_mock.request_history
        req_count = _count_mock_history(history, self.nfvo_url)
        self.assertEqual(
            cfg.CONF.connect_vnf_packages.retry_num + 1, req_count)

    def test_download_vnf_packages_with_retry_raise_timeout(self):

        fetch_base_url = os.path.join(self.url, uuidsentinel.vnf_pkg_id)
        self.requests_mock.register_uri(
            'GET',
            os.path.join(
                fetch_base_url,
                'package_content'),
            exc=requests.exceptions.ConnectTimeout)

        try:
            nfvo_client.VnfPackageRequest.download_vnf_packages(
                uuidsentinel.vnf_pkg_id)
        except requests.exceptions.RequestException as e:
            self.assertIsNone(e.response)

        history = self.requests_mock.request_history
        req_count = _count_mock_history(history, self.nfvo_url)
        self.assertEqual(
            cfg.CONF.connect_vnf_packages.retry_num + 1, req_count)

    def test_download_vnf_packages_raise_failed_download_content(self):

        fetch_base_url = os.path.join(self.url, uuidsentinel.vnf_pkg_id)
        self.requests_mock.register_uri('GET', os.path.join(
            fetch_base_url, 'package_content'), content=None)

        self.assertRaises(
            nfvo_client.FaliedDownloadContentException,
            nfvo_client.VnfPackageRequest.download_vnf_packages,
            uuidsentinel.vnf_pkg_id)

        history = self.requests_mock.request_history
        req_count = _count_mock_history(history, self.nfvo_url)
        self.assertEqual(1, req_count)

    @ddt.data(None, "", " ")
    def test_download_vnf_packages_raise_non_baseurl(self, empty_val):
        cfg.CONF.set_override("base_url", empty_val,
                              group='connect_vnf_packages')

        self.assertRaises(
            nfvo_client.UndefinedExternalSettingException,
            nfvo_client.VnfPackageRequest.download_vnf_packages,
            uuidsentinel.vnf_pkg_id)

    @ddt.data(None, [], ["non"])
    def test_download_vnf_packages_raise_non_pipeline(self, empty_val):
        cfg.CONF.set_override('pipeline', empty_val,
                              group='connect_vnf_packages')

        self.assertRaises(
            nfvo_client.UndefinedExternalSettingException,
            nfvo_client.VnfPackageRequest.download_vnf_packages,
            uuidsentinel.vnf_pkg_id)

    def test_index(self):
        response_body = self.json_serial_date_to_dict(
            [fakes.VNFPACKAGE_RESPONSE, fakes.VNFPACKAGE_RESPONSE])
        self.requests_mock.register_uri(
            'GET', self.url, headers=self.headers, json=response_body)

        res = nfvo_client.VnfPackageRequest.index()
        self.assertEqual(200, res.status_code)
        self.assertIsInstance(res.json(), list)
        self.assertEqual(response_body, res.json())
        self.assertEqual(2, len(res.json()))
        self.assertEqual(response_body, json.loads(res.text))

        history = self.requests_mock.request_history
        req_count = _count_mock_history(history, self.nfvo_url)
        self.assertEqual(1, req_count)

    def test_index_with_auth_basic(self):
        cfg.CONF.set_override('auth_type', 'BASIC',
                              group='authentication')
        auth.auth_manager = auth._AuthManager()

        response_body = self.json_serial_date_to_dict(
            [fakes.VNFPACKAGE_RESPONSE, fakes.VNFPACKAGE_RESPONSE])
        self.requests_mock.register_uri(
            'GET', self.url, headers=self.headers, json=response_body)

        res = nfvo_client.VnfPackageRequest.index()
        self.assertEqual(200, res.status_code)
        self.assertIsInstance(res.json(), list)
        self.assertEqual(response_body, res.json())
        self.assertEqual(2, len(res.json()))
        self.assertEqual(response_body, json.loads(res.text))

        history = self.requests_mock.request_history
        req_count = _count_mock_history(history, self.nfvo_url)
        self.assertEqual(1, req_count)
        self.assert_auth_basic(history[0])

    def test_index_with_auth_client_credentials(self):
        cfg.CONF.set_override('auth_type', 'OAUTH2_CLIENT_CREDENTIALS',
                              group='authentication')

        self.requests_mock.register_uri('GET',
            self.token_endpoint,
            json={'access_token': 'test_token', 'token_type': 'bearer'},
            headers={'Content-Type': 'application/json'},
            status_code=200)

        auth.auth_manager = auth._AuthManager()

        response_body = self.json_serial_date_to_dict(
            [fakes.VNFPACKAGE_RESPONSE, fakes.VNFPACKAGE_RESPONSE])
        self.requests_mock.register_uri(
            'GET', self.url, headers=self.headers, json=response_body)

        res = nfvo_client.VnfPackageRequest.index()
        self.assertEqual(200, res.status_code)
        self.assertIsInstance(res.json(), list)
        self.assertEqual(response_body, res.json())
        self.assertEqual(2, len(res.json()))
        self.assertEqual(response_body, json.loads(res.text))

        history = self.requests_mock.request_history
        req_count = _count_mock_history(history, self.nfvo_url, self.oauth_url)
        self.assertEqual(2, req_count)
        self.assert_auth_basic(history[0])
        self.assert_auth_client_credentials(history[1], "test_token")

    def test_index_raise_not_found(self):
        self.requests_mock.register_uri(
            'GET', self.url, headers=self.headers, status_code=404)

        try:
            nfvo_client.VnfPackageRequest.index()
        except requests.exceptions.RequestException as e:
            self.assertEqual(404, e.response.status_code)

        history = self.requests_mock.request_history
        req_count = _count_mock_history(history, self.nfvo_url)
        self.assertEqual(
            cfg.CONF.connect_vnf_packages.retry_num + 1, req_count)

    def test_index_raise_non_baseurl(self):
        cfg.CONF.set_override("base_url", None,
                              group='connect_vnf_packages')

        self.assertRaises(nfvo_client.UndefinedExternalSettingException,
                          nfvo_client.VnfPackageRequest.index)

    def test_show(self):
        response_body = self.json_serial_date_to_dict(
            fakes.VNFPACKAGE_RESPONSE)
        self.requests_mock.register_uri(
            'GET',
            os.path.join(
                self.url,
                uuidsentinel.vnf_pkg_id),
            headers=self.headers,
            json=response_body)

        res = nfvo_client.VnfPackageRequest.show(uuidsentinel.vnf_pkg_id)
        self.assertEqual(200, res.status_code)
        self.assertIsInstance(res.json(), dict)
        self.assertEqual(response_body, res.json())
        self.assertEqual(response_body, json.loads(res.text))

        history = self.requests_mock.request_history
        req_count = _count_mock_history(history, self.nfvo_url)
        self.assertEqual(1, req_count)

    def test_show_with_auth_basic(self):
        cfg.CONF.set_override('auth_type', 'BASIC',
                              group='authentication')
        auth.auth_manager = auth._AuthManager()

        response_body = self.json_serial_date_to_dict(
            fakes.VNFPACKAGE_RESPONSE)
        self.requests_mock.register_uri(
            'GET',
            os.path.join(
                self.url,
                uuidsentinel.vnf_pkg_id),
            headers=self.headers,
            json=response_body)

        res = nfvo_client.VnfPackageRequest.show(uuidsentinel.vnf_pkg_id)
        self.assertEqual(200, res.status_code)
        self.assertIsInstance(res.json(), dict)
        self.assertEqual(response_body, res.json())
        self.assertEqual(response_body, json.loads(res.text))

        history = self.requests_mock.request_history
        req_count = _count_mock_history(history, self.nfvo_url)
        self.assertEqual(1, req_count)
        self.assert_auth_basic(history[0])

    def test_show_with_auth_client_credentials(self):
        cfg.CONF.set_override('auth_type', 'OAUTH2_CLIENT_CREDENTIALS',
                              group='authentication')

        self.requests_mock.register_uri('GET',
            self.token_endpoint,
            json={'access_token': 'test_token', 'token_type': 'bearer'},
            headers={'Content-Type': 'application/json'},
            status_code=200)

        auth.auth_manager = auth._AuthManager()

        response_body = self.json_serial_date_to_dict(
            fakes.VNFPACKAGE_RESPONSE)
        self.requests_mock.register_uri(
            'GET',
            os.path.join(
                self.url,
                uuidsentinel.vnf_pkg_id),
            headers=self.headers,
            json=response_body)

        res = nfvo_client.VnfPackageRequest.show(uuidsentinel.vnf_pkg_id)
        self.assertEqual(200, res.status_code)
        self.assertIsInstance(res.json(), dict)
        self.assertEqual(response_body, res.json())
        self.assertEqual(response_body, json.loads(res.text))

        history = self.requests_mock.request_history
        req_count = _count_mock_history(history, self.nfvo_url, self.oauth_url)
        self.assertEqual(2, req_count)
        self.assert_auth_basic(history[0])
        self.assert_auth_client_credentials(history[1], "test_token")

    def test_show_raise_not_found(self):
        self.requests_mock.register_uri(
            'GET',
            os.path.join(
                self.url,
                uuidsentinel.vnf_pkg_id),
            headers=self.headers,
            status_code=404)

        try:
            nfvo_client.VnfPackageRequest.show(uuidsentinel.vnf_pkg_id)
        except requests.exceptions.RequestException as e:
            self.assertEqual(404, e.response.status_code)

        history = self.requests_mock.request_history
        req_count = _count_mock_history(history, self.nfvo_url)
        self.assertEqual(
            cfg.CONF.connect_vnf_packages.retry_num + 1, req_count)

    def test_show_raise_non_baseurl(self):
        cfg.CONF.set_override("base_url", None,
                              group='connect_vnf_packages')

        self.assertRaises(nfvo_client.UndefinedExternalSettingException,
                          nfvo_client.VnfPackageRequest.show,
                          uuidsentinel.vnf_pkg_id)


@ddt.ddt
class TestGrantRequest(base.BaseTestCase):

    def setUp(self):
        super(TestGrantRequest, self).setUp()
        self.requests_mock = self.useFixture(requests_mock_fixture.Fixture())
        self.url = "http://nfvo.co.jp/grant/v1/grants"
        self.nfvo_url = 'http://nfvo.co.jp'
        self.headers = {'content-type': 'application/json'}

        self.token_endpoint = 'https://oauth2/tokens'
        self.nfvo_url = 'http://nfvo.co.jp'
        self.oauth_url = 'https://oauth2'
        self.auth_user_name = 'test_user'
        self.auth_password = 'test_password'

        cfg.CONF.set_override('auth_type', None,
                              group='authentication')
        cfg.CONF.set_override("base_url", self.url, group='connect_grant')
        cfg.CONF.set_override('user_name', self.auth_user_name,
                              group='authentication')
        cfg.CONF.set_override('password', self.auth_password,
                              group='authentication')
        cfg.CONF.set_override('token_endpoint', self.token_endpoint,
                              group='authentication')
        cfg.CONF.set_override('client_id', self.auth_user_name,
                              group='authentication')
        cfg.CONF.set_override('client_password', self.auth_password,
                              group='authentication')
        auth.auth_manager = auth._AuthManager()
        nfvo_client.GrantRequest._connector = nfvo_client._Connect(2, 1, 20)

    def tearDown(self):
        super(TestGrantRequest, self).tearDown()
        self.addCleanup(mock.patch.stopall)

    def assert_auth_basic(self, acutual_request):
        actual_auth = acutual_request._request.headers.get("Authorization")
        expected_auth = base64.b64encode(
            '{}:{}'.format(
                self.auth_user_name,
                self.auth_password).encode('utf-8')).decode()
        self.assertEqual("Basic " + expected_auth, actual_auth)

    def assert_auth_client_credentials(self, acutual_request, expected_token):
        actual_auth = acutual_request._request.headers.get(
            "Authorization")
        self.assertEqual("Bearer " + expected_token, actual_auth)

    def create_request_body(self):
        return {
            "vnfInstanceId": uuidsentinel.vnf_instance_id,
            "vnfLcmOpOccId": uuidsentinel.vnf_lcm_op_occ_id,
            "operation": "INST",
            "isAutomaticInvocation": False,
            "links": {
                "vnfLcmOpOcc": {
                    "href":
                        "https://localost/vnfm/vnflcm/v1/vnf_lcm_op_occs/" +
                    uuidsentinel.vnf_lcm_op_occ_id},
                "vnfInstance": {
                    "href": "https://localost/vnfm/vnflcm/v1/vnf_instances/" +
                    uuidsentinel.vnf_instance_id}}}

    def fake_response_body(self):
        return {
            "id": uuidsentinel.grant_id,
            "vnfInstanceId": uuidsentinel.vnf_instance_id,
            "vnfLcmOpOccId": uuidsentinel.vnf_lcm_op_occ_id,
            "additionalParams": {},
            "_links": {
                "self": {
                    "href":
                        "http://nfvo.co.jp/grant/v1/grants/\
                            19533fd4-eacb-4e6f-acd9-b56210a180d7"},
                "vnfLcmOpOcc": {
                    "href":
                        "https://localost/vnfm/vnflcm/v1/vnf_lcm_op_occs/" +
                    uuidsentinel.vnf_lcm_op_occ_id},
                "vnfInstance": {
                    "href": "https://localost/vnfm/vnflcm/v1/vnf_instances/" +
                    uuidsentinel.vnf_instance_id}}}

    def test_init(self):
        self.assertEqual(self.url, cfg.CONF.connect_grant.base_url)
        self.assertEqual(2, cfg.CONF.connect_grant.retry_num)
        self.assertEqual(30, cfg.CONF.connect_grant.retry_wait)
        self.assertEqual(20, cfg.CONF.connect_grant.timeout)

    def test_grants(self):
        response_body = self.fake_response_body()
        self.requests_mock.register_uri(
            'POST',
            self.url,
            json=response_body,
            headers=self.headers,
            status_code=201)

        request_body = self.create_request_body()
        res = nfvo_client.GrantRequest.grants(data=request_body)
        self.assertEqual(response_body, json.loads(res.text))
        self.assertEqual(response_body, res.json())

        history = self.requests_mock.request_history
        req_count = _count_mock_history(history, self.nfvo_url)
        self.assertEqual(1, req_count)

    def test_grants_with_retry_raise_bad_request(self):
        response_body = self.fake_response_body()
        self.requests_mock.register_uri('POST', self.url, json=json.dumps(
            response_body), headers=self.headers, status_code=400)

        request_body = self.create_request_body()
        try:
            nfvo_client.GrantRequest.grants(data=request_body)
        except requests.exceptions.RequestException as e:
            self.assertEqual(400, e.response.status_code)

        history = self.requests_mock.request_history
        req_count = _count_mock_history(history, self.nfvo_url)
        self.assertEqual(
            cfg.CONF.connect_grant.retry_num + 1, req_count)

    def test_grants_with_retry_raise_timeout(self):
        self.requests_mock.register_uri(
            'POST', self.url, exc=requests.exceptions.ConnectTimeout)

        request_body = self.create_request_body()
        try:
            nfvo_client.GrantRequest.grants(data=request_body)
        except requests.exceptions.RequestException as e:
            self.assertIsNone(e.response)

        history = self.requests_mock.request_history
        req_count = _count_mock_history(history, self.nfvo_url)
        self.assertEqual(
            cfg.CONF.connect_grant.retry_num + 1, req_count)

    @ddt.data(None, "", " ")
    def test_grants_raise_non_baseurl(self, empty_val):
        cfg.CONF.set_override("base_url", empty_val, group='connect_grant')
        self.assertRaises(nfvo_client.UndefinedExternalSettingException,
                          nfvo_client.GrantRequest.grants,
                          data={"test": "value1"})

    def test_grants_with_auth_basic(self):
        cfg.CONF.set_override('auth_type', 'BASIC',
                              group='authentication')
        auth.auth_manager = auth._AuthManager()

        response_body = self.fake_response_body()
        self.requests_mock.register_uri(
            'POST',
            self.url,
            json=response_body,
            headers=self.headers,
            status_code=201)

        request_body = self.create_request_body()
        res = nfvo_client.GrantRequest.grants(data=request_body)
        self.assertEqual(response_body, json.loads(res.text))
        self.assertEqual(response_body, res.json())

        history = self.requests_mock.request_history
        req_count = _count_mock_history(history, self.nfvo_url)
        self.assertEqual(1, req_count)
        self.assert_auth_basic(history[0])

    def test_grants_with_auth_client_credentials(self):
        cfg.CONF.set_override('auth_type', 'OAUTH2_CLIENT_CREDENTIALS',
                              group='authentication')

        self.requests_mock.register_uri('GET',
            self.token_endpoint,
            json={'access_token': 'test_token', 'token_type': 'bearer'},
            headers={'Content-Type': 'application/json'},
            status_code=200)

        auth.auth_manager = auth._AuthManager()

        response_body = self.fake_response_body()
        self.requests_mock.register_uri(
            'POST',
            self.url,
            json=response_body,
            headers=self.headers,
            status_code=201)

        request_body = self.create_request_body()
        res = nfvo_client.GrantRequest.grants(data=request_body)
        self.assertEqual(response_body, json.loads(res.text))
        self.assertEqual(response_body, res.json())

        history = self.requests_mock.request_history
        req_count = _count_mock_history(history, self.nfvo_url, self.oauth_url)
        self.assertEqual(2, req_count)
        self.assert_auth_basic(history[0])
        self.assert_auth_client_credentials(history[1], "test_token")
