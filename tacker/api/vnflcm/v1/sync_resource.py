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

from oslo_config import cfg
from oslo_log import log as logging

from tacker.common import csar_utils
from tacker.common import exceptions
from tacker.common import utils
from tacker.conductor.conductorrpc import vnf_pkgm_rpc
from tacker.glance_store import store as glance_store
from tacker import objects
from tacker.objects import fields
import tacker.vnfm.nfvo_client as nfvo_client
import time
import webob


CONF = cfg.CONF

LOG = logging.getLogger(__name__)


class SyncVnfPackage:

    vnf_package_rpc_api = vnf_pkgm_rpc.VNFPackageRPCAPI()

    @classmethod
    def create_package(cls, context, vnf_package_info):
        """vnf_package, create a vnf_package_vnfd table."""

        vnf_package_info = utils.convert_camelcase_to_snakecase(
            vnf_package_info)

        try:
            vnf_package = cls.__create_vnf_package(context, vnf_package_info)
        except Exception as exc:
            raise webob.exc.HTTPInternalServerError(
                explanation=exc)

        try:
            artifact_paths = cls._get_artifact_paths(vnf_package_info)
            vnf_package_binary = \
                nfvo_client.VnfPackageRequest.download_vnf_packages(
                    vnf_package.id, artifact_paths)
        except nfvo_client.UndefinedExternalSettingException as exc:
            raise webob.exc.HTTPNotFound(explanation=exc)
        except (nfvo_client.FaliedDownloadContentException, Exception) as exc:
            raise webob.exc.HTTPInternalServerError(
                explanation=exc)

        try:
            (location, size, _, multihash, _) = glance_store.store_csar(
                context, vnf_package.id, vnf_package_binary)

            cls.__update_vnf_package(vnf_package, location, size, multihash)
            cls.vnf_package_rpc_api.upload_vnf_package_content(
                context, vnf_package)
            vnf_package_vnfd = cls._get_vnf_package_vnfd(
                context, vnf_package_info.get('vnfd_id'))
        except Exception as exc:
            raise webob.exc.HTTPInternalServerError(
                explanation=exc)

        return vnf_package_vnfd

    @classmethod
    def _get_artifact_paths(cls, vnf_package_info):
        additional_artifacts = vnf_package_info.get('additional_artifacts')
        if additional_artifacts is None:
            return None

        return [artifact.get('artifact_path')
                for artifact in additional_artifacts
                if 'artifact_path' in artifact]

    @classmethod
    def __store_csar(cls, context, id, body):
        (location, size, checksum, multihash,
         loc_meta) = glance_store.store_csar(context, id, body)
        return location, size, checksum, multihash, loc_meta

    @classmethod
    def __load_csar(cls, context, vnf_package):
        location = vnf_package.location_glance_store
        zip_path = glance_store.load_csar(vnf_package.id, location)
        vnf_data, flavours = csar_utils.load_csar_data(
            context.elevated(), vnf_package.id, zip_path)
        return vnf_data, flavours

    @classmethod
    def __create_vnf_package(cls, context, vnf_package_info):
        """VNF Package Table Registration."""
        vnf_package = objects.VnfPackage(
            context=context,
            id=vnf_package_info.get('id'),
            onboarding_state=fields.PackageOnboardingStateType.CREATED,
            operational_state=fields.PackageOperationalStateType.DISABLED,
            usage_state=fields.PackageUsageStateType.NOT_IN_USE,
            tenant_id=context.project_id
        )
        vnf_package.create()
        return vnf_package

    @classmethod
    def __update_vnf_package(cls, vnf_package, location, size, multihash):
        """VNF Package Table Update."""
        vnf_package.algorithm = CONF.vnf_package.hashing_algorithm
        vnf_package.location_glance_store = location
        vnf_package.hash = multihash
        vnf_package.size = size
        vnf_package.save()

    @classmethod
    def _get_vnf_package_vnfd(cls, context, vnfd_id):
        """Get VNF Package VNFD."""
        for num in range(CONF.vnf_lcm.retry_num):
            try:
                vnfd = objects.VnfPackageVnfd.get_by_id(
                    context,
                    vnfd_id)
                return vnfd
            except exceptions.VnfPackageVnfdNotFound:
                LOG.debug("retry_wait %s" %
                    CONF.vnf_lcm.retry_wait)
                time.sleep(CONF.vnf_lcm.retry_wait)

        return None
