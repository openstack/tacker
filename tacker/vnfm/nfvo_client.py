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
import requests
from tacker import auth
import time
import zipfile

from oslo_config import cfg
from oslo_log import log as logging

LOG = logging.getLogger(__name__)


class UndefinedExternalSettingException(Exception):
    pass


class FaliedDownloadContentException(Exception):
    pass


class _Connect:

    def __init__(self, retry_num=0, retry_wait=0, timeout=0):
        self.retry_num = retry_num
        self.retry_wait = retry_wait
        self.timeout = timeout

    def replace_placeholder_url(self, base_url, path, *params):
        replace_placeholder_url = os.path.join(base_url, path)
        try:
            return replace_placeholder_url.format(*params)
        except Exception:
            return replace_placeholder_url

    def request(self, *args, **kwargs):
        return self.__request(
            auth.auth_manager.get_auth_client().request,
            *args,
            timeout=self.timeout,
            **kwargs)

    def __request(self, request_function, *args, **kwargs):
        response = None
        for retry_cnt in range(self.retry_num + 1):
            LOG.info("Connecting to <{ip}:{port}>, count=<{count}>".format(
                ip=args[0], port=args[1], count=retry_cnt))
            if 'headers' in kwargs:
                LOG.info("[REQ] HEADERS={}".format(kwargs['headers']))

            if 'data' in kwargs:
                LOG.info("[REQ] BODY={}".format(kwargs['data']))

            elif 'json' in kwargs:
                LOG.info("[REQ] BODY={}".format(kwargs['json']))

            try:
                response = request_function(*args, **kwargs)
                if 200 <= response.status_code <= 299:
                    return response

                LOG.error("Connected error. Failed http status=<{}>".format(
                    response.status_code))
            except requests.exceptions.ConnectTimeout as e:
                LOG.error("Connected error. details=<{}>".format(e))

            if retry_cnt < self.retry_num:
                time.sleep(self.retry_wait)

        raise requests.exceptions.RequestException(response=response)


class VnfPackageRequest:
    OPTS = [
        cfg.StrOpt('base_url',
                   default=None,
                   help="vnf_packages base_url"),
        cfg.ListOpt('pipeline',
                    default=None,
                    help="Get vnf_packages api pipeline"),
        cfg.IntOpt('retry_num',
                   default=2,
                   help="Number of vnf_packages retry count"),
        cfg.IntOpt('retry_wait',
                   default=30,
                   help="Number of vnf_packages retry wait"),
        cfg.IntOpt('timeout',
                   default=20,
                   help="Number of vnf_packages connect timeout")
    ]
    cfg.CONF.register_opts(OPTS, group='connect_vnf_packages')
    _connector = _Connect(
        cfg.CONF.connect_vnf_packages.retry_num,
        cfg.CONF.connect_vnf_packages.retry_wait,
        cfg.CONF.connect_vnf_packages.timeout)

    @classmethod
    def validate(cls):
        """Check config settings.

        Raises:
            UndefinedExternalSettingException: tacker.conf undefined setting.
        """
        if (not cfg.CONF.connect_vnf_packages.base_url or
                cfg.CONF.connect_vnf_packages.base_url.strip() == ''):
            raise UndefinedExternalSettingException(
                "Vnf package the external setting to 'base_url' undefined.")

    @classmethod
    def _write(cls, vnf_package_zip, response, filename=None):
        def write_zip():
            with zipfile.ZipFile(io.BytesIO(response.content)) as fin:
                for info in fin.infolist():
                    vnf_package_zip.writestr(
                        info.filename, fin.read(info.filename))

        def get_filename():
            content_disposition = response.headers.get('Content-Disposition')
            if not content_disposition:
                return None

            attribute = 'filename='
            return content_disposition[content_disposition.find(
                attribute) + len(attribute):]

        if response.headers.get('Content-Type') == 'application/zip':
            write_zip()
            return

        filename = get_filename() if (not filename) else filename
        if filename:
            vnf_package_zip.writestr(filename, response.content)
            return

        raise FaliedDownloadContentException(
            "Failed response content, vnf_package_zip={}".format(
                vnf_package_zip))

    @classmethod
    def download_vnf_packages(cls, vnf_package_id, artifact_paths=None):
        """Get vnf packages from the nfvo.

        Args:
            vnf_package_id (UUID): VNF Package ID
            artifact_paths (list, optional): artifatcs paths. Defaults to [].

        Returns:
            io.BytesIO: zip archive for vnf packages content.

        Raises:
            takcer.nfvo.nfvo_client.UndefinedExternalSettingException:
                tacker.conf undefined setting.
            requests.exceptions.RequestException:
                Failed connected, download vnf packages.
            takcer.nfvo.nfvo_client.FaliedDownloadContentException:
                Failed content, create vnf package zip file.
        """
        cls.validate()
        if not cfg.CONF.connect_vnf_packages.pipeline or len(
                cfg.CONF.connect_vnf_packages.pipeline) == 0:
            raise UndefinedExternalSettingException(
                "Vnf package the external setting to 'pipeline' undefined.")

        if artifact_paths is None:
            artifact_paths = []

        def download_vnf_package(pipeline_type, vnf_package_zip):
            if pipeline_type == 'package_content':
                cls._download_package_content(vnf_package_zip, vnf_package_id)
            elif pipeline_type == 'vnfd':
                cls._download_vnfd(
                    vnf_package_zip, vnf_package_id)
            elif pipeline_type == 'artifacts':
                cls._download_artifacts(vnf_package_zip, vnf_package_id,
                                        artifact_paths)
            else:
                raise UndefinedExternalSettingException(
                    "Vnf package the external setting to 'pipeline=<{}>' " +
                    "not supported.".format(pipeline_type))

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer,
                        mode='w',
                        compression=zipfile.ZIP_DEFLATED) as vnf_package_zip:
            for pipeline_type in cfg.CONF.connect_vnf_packages.pipeline:
                download_vnf_package(pipeline_type, vnf_package_zip)

            zip_buffer.seek(0)
        return zip_buffer

    @classmethod
    def _download_package_content(cls, vnf_package_zip, vnf_package_id):
        LOG.info("Processing: download vnf_package to package content.")
        request_url = cls._connector.replace_placeholder_url(
            cfg.CONF.connect_vnf_packages.base_url,
            "{}/package_content",
            vnf_package_id)

        headers = {'Accept': 'application/zip'}
        response = cls._connector.request('GET', request_url, headers=headers)
        cls._write(vnf_package_zip, response)

    @classmethod
    def _download_vnfd(cls, vnf_package_zip, vnf_package_id):
        LOG.info("Processing: download vnf_package to vnfd.")
        request_url = cls._connector.replace_placeholder_url(
            cfg.CONF.connect_vnf_packages.base_url,
            "{}/vnfd",
            vnf_package_id)

        # zip format only.
        headers = {'Accept': 'application/zip'}
        response = cls._connector.request('GET', request_url, headers=headers)
        cls._write(vnf_package_zip, response)

    @classmethod
    def _download_artifacts(
            cls,
            vnf_package_zip,
            vnf_package_id,
            artifact_paths):
        LOG.info("Processing: download vnf_package to artifact.")
        for artifact_path in artifact_paths:
            request_url = cls._connector.replace_placeholder_url(
                cfg.CONF.connect_vnf_packages.base_url,
                "{}/artifacts/{}",
                vnf_package_id,
                artifact_path)
            headers = {'Accept': 'application/zip'}
            response = cls._connector.request(
                'GET', request_url, headers=headers)
            cls._write(vnf_package_zip, response, artifact_path)

    @classmethod
    def index(cls, **kwargs):
        """List vnf package.

        Args:
            kwargs:
                any other parameter that can be passed
                    to requests.Session.request.

        Returns:
            requests.Response: individual vnf package.
        """
        cls.validate()

        LOG.info("Processing: index vnf_package.")
        return cls._connector.request(
            'GET', cfg.CONF.connect_vnf_packages.base_url, **kwargs)

    @classmethod
    def show(cls, vnf_package_id, **kwargs):
        """Individual vnf package.

        Args:
            vnf_package_id (UUID): VNF Package ID.

            kwargs:
                any other parameter that can be passed
                    to requests.Session.request.

        Returns:
            requests.Response: individual vnf package.
        """
        cls.validate()

        LOG.info("Processing: show vnf_package.")
        request_url = cls._connector.replace_placeholder_url(
            cfg.CONF.connect_vnf_packages.base_url, vnf_package_id)

        return cls._connector.request('GET', request_url, **kwargs)


class GrantRequest:
    OPTS = [
        cfg.StrOpt('base_url',
                   default=None,
                   help="grant of base_url"),
        cfg.IntOpt('retry_num',
                   default=2,
                   help="Number of grant retry count"),
        cfg.IntOpt('retry_wait',
                   default=30,
                   help="Number of grant retry wait"),
        cfg.IntOpt('timeout',
                   default=20,
                   help="Number of grant connect timeout")
    ]
    cfg.CONF.register_opts(OPTS, group='connect_grant')

    _connector = _Connect(
        cfg.CONF.connect_grant.retry_num,
        cfg.CONF.connect_grant.retry_wait,
        cfg.CONF.connect_grant.timeout)

    @classmethod
    def validate(cls):
        """Check config settings.

        Raises:
            UndefinedExternalSettingException: tacker.conf undefined setting.
        """
        if (not cfg.CONF.connect_grant.base_url or
                cfg.CONF.connect_grant.base_url.strip() == ''):
            raise UndefinedExternalSettingException(
                "Grant the external setting to 'base_url' undefined.")

    @classmethod
    def grants(cls, **kwargs):
        """grants request.

        Args:
            kwargs:
                any other parameter that can be passed
                to requests.Session.request.

        Returns:
            io.BytesIO: zip archive for vnf packages content.

        Raises:
            takcer.nfvo.nfvo_client.UndefinedExternalSettingException:
                tacker.conf undefined setting.
            requests.exceptions.RequestException:
                Failed connected, download vnf packages.
            takcer.nfvo.nfvo_client.FaliedDownloadContentException:
                Failed content, create vnf package zip file.
        """
        cls.validate()
        return cls._connector.request(
            'POST', cfg.CONF.connect_grant.base_url, **kwargs)
