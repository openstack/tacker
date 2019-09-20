# Copyright (C) 2019 NTT DATA
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

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import excutils
from oslo_utils import uuidutils
from six.moves import http_client
from six.moves import urllib
import webob

from tacker._i18n import _
from tacker.api.schemas import vnf_packages
from tacker.api import validation
from tacker.api.views import vnf_packages as vnf_packages_view
from tacker.common import exceptions
from tacker.conductor.conductorrpc import vnf_pkgm_rpc
from tacker.glance_store import store as glance_store
from tacker.objects import fields
from tacker.objects import vnf_package as vnf_package_obj
from tacker.policies import vnf_package as vnf_package_policies
from tacker import wsgi

LOG = logging.getLogger(__name__)


CONF = cfg.CONF


class VnfPkgmController(wsgi.Controller):

    _view_builder_class = vnf_packages_view.ViewBuilder

    def __init__(self):
        super(VnfPkgmController, self).__init__()
        self.rpc_api = vnf_pkgm_rpc.VNFPackageRPCAPI()
        glance_store.initialize_glance_store()

    @wsgi.response(http_client.CREATED)
    @wsgi.expected_errors((http_client.BAD_REQUEST, http_client.FORBIDDEN))
    @validation.schema(vnf_packages.create)
    def create(self, request, body):
        context = request.environ['tacker.context']
        context.can(vnf_package_policies.VNFPKGM % 'create')

        vnf_package = vnf_package_obj.VnfPackage(context=request.context)
        vnf_package.onboarding_state = (
            fields.PackageOnboardingStateType.CREATED)
        vnf_package.operational_state = (
            fields.PackageOperationalStateType.DISABLED)
        vnf_package.usage_state = fields.PackageUsageStateType.NOT_IN_USE
        vnf_package.user_data = body.get('userDefinedData', dict())
        vnf_package.tenant_id = request.context.project_id

        vnf_package.create()

        return self._view_builder.create(request, vnf_package)

    @wsgi.response(http_client.OK)
    @wsgi.expected_errors((http_client.FORBIDDEN, http_client.NOT_FOUND))
    def show(self, request, id):
        context = request.environ['tacker.context']
        context.can(vnf_package_policies.VNFPKGM % 'show')

        # check if id is of type uuid format
        if not uuidutils.is_uuid_like(id):
            msg = _("Can not find requested vnf package: %s") % id
            raise webob.exc.HTTPNotFound(explanation=msg)

        try:
            vnf_package = vnf_package_obj.VnfPackage.get_by_id(
                request.context, id,
                expected_attrs=["vnf_deployment_flavours", "vnfd"])
        except exceptions.VnfPackageNotFound:
            msg = _("Can not find requested vnf package: %s") % id
            raise webob.exc.HTTPNotFound(explanation=msg)

        return self._view_builder.show(request, vnf_package)

    @wsgi.response(http_client.OK)
    @wsgi.expected_errors((http_client.FORBIDDEN))
    def index(self, request):
        context = request.environ['tacker.context']
        context.can(vnf_package_policies.VNFPKGM % 'index')

        vnf_packages = vnf_package_obj.VnfPackagesList.get_all(
            request.context,
            expected_attrs=["vnf_deployment_flavours", "vnfd"])

        return self._view_builder.index(request, vnf_packages)

    @wsgi.response(http_client.NO_CONTENT)
    @wsgi.expected_errors((http_client.FORBIDDEN, http_client.NOT_FOUND))
    def delete(self, request, id):
        context = request.environ['tacker.context']
        context.can(vnf_package_policies.VNFPKGM % 'delete')

        # check if id is of type uuid format
        if not uuidutils.is_uuid_like(id):
            msg = _("Can not find requested vnf package: %s") % id
            raise webob.exc.HTTPNotFound(explanation=msg)

        try:
            vnf_package = vnf_package_obj.VnfPackage.get_by_id(
                request.context, id)
        except exceptions.VnfPackageNotFound:
            msg = _("Can not find requested vnf package: %s") % id
            raise webob.exc.HTTPNotFound(explanation=msg)

        if vnf_package.operational_state == \
                fields.PackageUsageStateType.IN_USE:
            msg = _("VNF Package %(id)s usage state is %(state)s")
            raise webob.exc.HTTPConflict(
                explanation=msg % {
                    "id": id,
                    "state": fields.PackageOperationalStateType.ENABLED})

        # Delete vnf_package
        self.rpc_api.delete_vnf_package(context, vnf_package)

    @wsgi.response(http_client.ACCEPTED)
    @wsgi.expected_errors((http_client.FORBIDDEN, http_client.NOT_FOUND,
                           http_client.CONFLICT))
    def upload_vnf_package_content(self, request, id, body):
        context = request.environ['tacker.context']
        context.can(vnf_package_policies.VNFPKGM % 'upload_package_content')

        # check if id is of type uuid format
        if not uuidutils.is_uuid_like(id):
            msg = _("Can not find requested vnf package: %s") % id
            raise webob.exc.HTTPNotFound(explanation=msg)

        try:
            vnf_package = vnf_package_obj.VnfPackage.get_by_id(
                request.context, id)
        except exceptions.VnfPackageNotFound:
            msg = _("Can not find requested vnf package: %s") % id
            raise webob.exc.HTTPNotFound(explanation=msg)

        if vnf_package.onboarding_state != \
           fields.PackageOnboardingStateType.CREATED:
            msg = _("VNF Package %(id)s onboarding state "
                    "is not %(onboarding)s")
            raise webob.exc.HTTPConflict(explanation=msg % {"id": id,
                    "onboarding": fields.PackageOnboardingStateType.CREATED})

        vnf_package.onboarding_state = (
            fields.PackageOnboardingStateType.UPLOADING)

        vnf_package.save()

        try:
            (location, size, checksum, multihash,
            loc_meta) = glance_store.store_csar(context, id, body)
        except exceptions.UploadFailedToGlanceStore:
            with excutils.save_and_reraise_exception():
                vnf_package.onboarding_state = (
                    fields.PackageOnboardingStateType.CREATED)
                vnf_package.save()

        vnf_package.onboarding_state = (
            fields.PackageOnboardingStateType.PROCESSING)

        vnf_package.algorithm = CONF.vnf_package.hashing_algorithm
        vnf_package.hash = multihash
        vnf_package.location_glance_store = location

        vnf_package.save()

        # process vnf_package
        self.rpc_api.upload_vnf_package_content(context, vnf_package)

    @wsgi.response(http_client.ACCEPTED)
    @wsgi.expected_errors((http_client.BAD_REQUEST, http_client.FORBIDDEN,
                           http_client.NOT_FOUND, http_client.CONFLICT))
    @validation.schema(vnf_packages.upload_from_uri)
    def upload_vnf_package_from_uri(self, request, id, body):

        context = request.environ['tacker.context']
        context.can(vnf_package_policies.VNFPKGM % 'upload_from_uri')

        # check if id is of type uuid format
        if not uuidutils.is_uuid_like(id):
            msg = _("Can not find requested vnf package: %s") % id
            raise webob.exc.HTTPNotFound(explanation=msg)

        url = body['addressInformation']
        try:
            data_iter = urllib.request.urlopen(url)
        except Exception:
            data_iter = None
            msg = _("Failed to open URL %s")
            raise webob.exc.HTTPBadRequest(explanation=msg % url)
        finally:
            if hasattr(data_iter, 'close'):
                data_iter.close()

        try:
            vnf_package = vnf_package_obj.VnfPackage.get_by_id(
                request.context, id)
        except exceptions.VnfPackageNotFound:
            msg = _("Can not find requested vnf package: %s") % id
            raise webob.exc.HTTPNotFound(explanation=msg)

        if vnf_package.onboarding_state != \
                fields.PackageOnboardingStateType.CREATED:
            msg = _("VNF Package %(id)s onboarding state is not "
                    "%(onboarding)s")
            raise webob.exc.HTTPConflict(explanation=msg % {"id": id,
                    "onboarding": fields.PackageOnboardingStateType.CREATED})

        vnf_package.onboarding_state = (
            fields.PackageOnboardingStateType.UPLOADING)

        vnf_package.save()

        # process vnf_package
        self.rpc_api.upload_vnf_package_from_uri(context, vnf_package,
                                            body['addressInformation'],
                                            user_name=body.get('userName'),
                                            password=body.get('password'))


def create_resource():
    body_deserializers = {
        'application/zip': wsgi.ZipDeserializer()
    }

    deserializer = wsgi.RequestDeserializer(
        body_deserializers=body_deserializers)
    return wsgi.Resource(VnfPkgmController(), deserializer=deserializer)
