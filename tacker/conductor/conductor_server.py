# Copyright 2017 OpenStack Foundation
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

import datetime
import functools
import inspect
import os
import shutil
import sys

from glance_store import exceptions as store_exceptions
from oslo_config import cfg
from oslo_log import log as logging
import oslo_messaging
from oslo_service import periodic_task
from oslo_service import service
from oslo_utils import encodeutils
from oslo_utils import excutils
from oslo_utils import timeutils
from sqlalchemy.orm import exc as orm_exc
import yaml

from tacker.common import coordination
from tacker.common import csar_utils
from tacker.common import exceptions
from tacker.common import safe_utils
from tacker.common import topics
from tacker.common import utils
from tacker import context as t_context
from tacker.db.common_services import common_services_db
from tacker.db.nfvo import nfvo_db
from tacker.extensions import nfvo
from tacker.glance_store import store as glance_store
from tacker import manager
from tacker import objects
from tacker.objects import fields
from tacker.objects.vnf_package import VnfPackagesList
from tacker.plugins.common import constants
from tacker import service as tacker_service
from tacker import version
from tacker.vnflcm import vnflcm_driver
from tacker.vnfm import plugin

CONF = cfg.CONF

# NOTE(tpatil): keystone_authtoken opts registered explicitly as conductor
# service doesn't use the keystonemiddleware.authtoken middleware as it's
# used by the tacker.service in the api-paste.ini
OPTS = [cfg.StrOpt('user_domain_id',
                   default='default',
                   help='User Domain Id'),
        cfg.StrOpt('project_domain_id',
                   default='default',
                   help='Project Domain Id'),
        cfg.StrOpt('password',
                   default='default',
                   help='User Password'),
        cfg.StrOpt('username',
                   default='default',
                   help='User Name'),
        cfg.StrOpt('user_domain_name',
                   default='default',
                   help='Use Domain Name'),
        cfg.StrOpt('project_name',
                   default='default',
                   help='Project Name'),
        cfg.StrOpt('project_domain_name',
                   default='default',
                   help='Project Domain Name'),
        cfg.StrOpt('auth_url',
                   default='http://localhost/identity/v3',
                   help='Keystone endpoint')]

cfg.CONF.register_opts(OPTS, 'keystone_authtoken')

LOG = logging.getLogger(__name__)


def _delete_csar(context, vnf_package):
    # Delete from glance store
    glance_store.delete_csar(context, vnf_package.id,
                             vnf_package.location_glance_store)

    csar_utils.delete_csar_data(vnf_package.id)


@utils.expects_func_args('vnf_package')
def revert_upload_vnf_package(function):
    """Decorator to revert upload_vnf_package on failure."""

    @functools.wraps(function)
    def decorated_function(self, context, *args, **kwargs):
        try:
            return function(self, context, *args, **kwargs)
        except Exception as exp:
            with excutils.save_and_reraise_exception():
                wrapped_func = safe_utils.get_wrapped_function(function)
                keyed_args = inspect.getcallargs(wrapped_func, self, context,
                                                 *args, **kwargs)
                context = keyed_args['context']
                vnf_package = keyed_args['vnf_package']
                if not (isinstance(exp, exceptions.UploadFailedToGlanceStore)
                        or isinstance(exp, exceptions.VNFPackageURLInvalid)):
                    # Delete the csar file from the glance store.
                    glance_store.delete_csar(context, vnf_package.id,
                             vnf_package.location_glance_store)

                    csar_utils.delete_csar_data(vnf_package.id)

                # Delete the vnf_deployment_flavour if created.
                if vnf_package.vnf_deployment_flavours:
                    for flavour in vnf_package.vnf_deployment_flavours:
                        flavour.destroy(context)

                # Set the vnf package onboarding status to created,
                # so that user can retry uploading vnf package
                # after correcting the csar zip file.
                vnf_package.onboarding_state = (
                    fields.PackageOnboardingStateType.CREATED)

                vnf_package.save()

    return decorated_function


class Conductor(manager.Manager):
    def __init__(self, host, conf=None):
        if conf:
            self.conf = conf
        else:
            self.conf = CONF
        super(Conductor, self).__init__(host=self.conf.host)
        self.vnfm_plugin = plugin.VNFMPlugin()
        self.vnflcm_driver = vnflcm_driver.VnfLcmDriver()

    def start(self):
        coordination.COORDINATOR.start()

    def stop(self):
        coordination.COORDINATOR.stop()

    def init_host(self):
        glance_store.initialize_glance_store()
        self._basic_config_check()

    def _basic_config_check(self):
        if not os.path.isdir(CONF.vnf_package.vnf_package_csar_path):
            LOG.error("Config option 'vnf_package_csar_path' is not "
                      "configured correctly. VNF package CSAR path directory"
                      " %s doesn't exist",
                      CONF.vnf_package.vnf_package_csar_path)
            sys.exit(1)

    def update_vim(self, context, vim_id, status):
        t_admin_context = t_context.get_admin_context()
        update_time = timeutils.utcnow()
        with t_admin_context.session.begin(subtransactions=True):
            try:
                query = t_admin_context.session.query(nfvo_db.Vim)
                query.filter(
                    nfvo_db.Vim.id == vim_id).update(
                        {'status': status,
                         'updated_at': update_time})
            except orm_exc.NoResultFound:
                raise nfvo.VimNotFoundException(vim_id=vim_id)
            event_db = common_services_db.Event(
                resource_id=vim_id,
                resource_type=constants.RES_TYPE_VIM,
                resource_state=status,
                event_details="",
                event_type=constants.RES_EVT_MONITOR,
                timestamp=update_time)
            t_admin_context.session.add(event_db)
        return status

    def _create_software_images(self, context, sw_image, flavour_uuid):
        vnf_sw_image = objects.VnfSoftwareImage(context=context)
        vnf_sw_image.flavour_uuid = flavour_uuid
        vnf_sw_image.name = sw_image.get('name')

        # TODO(nirajsingh) Provider is mandatory as per SOL005 but it's not
        # a required parameter in SwImageData as per SOL001. SOL001 will be
        # amended to make `provider` a required parameter as per
        # 'https://docbox.etsi.org/ISG/NFV/SOL/05-CONTRIBUTIONS/2019/
        # NFVSOL000338_SOL001ed271_SwImage_Provider.docx'.
        vnf_sw_image.provider = sw_image.get('provider', "")

        vnf_sw_image.version = sw_image.get('version')
        if sw_image.get('checksum'):
            checksum = sw_image.get('checksum')
            if checksum.get('algorithm'):
                vnf_sw_image.algorithm = checksum.get('algorithm')
            if checksum.get('hash'):
                vnf_sw_image.hash = checksum.get('hash')
            vnf_sw_image.container_format = sw_image.get('container_format')
            vnf_sw_image.disk_format = sw_image.get('disk_format')
            if sw_image.get('min_ram'):
                min_ram = sw_image.get('min_ram')
                vnf_sw_image.min_ram = int(min_ram.split()[0])
            else:
                vnf_sw_image.min_ram = 0
        vnf_sw_image.min_disk = int(sw_image.get('min_disk').split()[0])
        vnf_sw_image.size = int(sw_image.get('size').split()[0])
        vnf_sw_image.image_path = ''
        vnf_sw_image.software_image_id = sw_image['software_image_id']
        vnf_sw_image.metadata = sw_image.get('metadata', dict())
        vnf_sw_image.create()

    def _create_flavour(self, context, package_uuid, flavour):
        deploy_flavour = objects.VnfDeploymentFlavour(context=context)
        deploy_flavour.package_uuid = package_uuid
        deploy_flavour.flavour_id = flavour['flavour_id']
        deploy_flavour.flavour_description = flavour['flavour_description']
        deploy_flavour.instantiation_levels = \
            flavour.get('instantiation_levels')
        deploy_flavour.create()

        sw_images = flavour.get('sw_images')
        if sw_images:
            for sw_image in sw_images:
                self._create_software_images(
                    context, sw_image, deploy_flavour.id)

    def _create_vnf_artifacts(self, context, package_uuid, artifact):
        vnf_artifact = objects.VnfPackageArtifactInfo(context=context)
        vnf_artifact.package_uuid = package_uuid
        vnf_artifact.artifact_path = artifact['Source']
        vnf_artifact.algorithm = artifact['Algorithm']
        vnf_artifact.hash = artifact['Hash']
        vnf_artifact._metadata = {}
        vnf_artifact.create()

    def _onboard_vnf_package(
            self,
            context,
            vnf_package,
            vnf_data,
            flavours,
            vnf_artifacts):
        if vnf_artifacts:
            for artifact in vnf_artifacts:
                self._create_vnf_artifacts(context, vnf_package.id, artifact)

        package_vnfd = objects.VnfPackageVnfd(context=context)
        package_vnfd.package_uuid = vnf_package.id

        package_vnfd.vnfd_id = vnf_data.get('descriptor_id')
        package_vnfd.vnf_provider = vnf_data.get('provider')
        package_vnfd.vnf_product_name = vnf_data.get('product_name')
        package_vnfd.vnf_software_version = vnf_data.get('software_version')
        package_vnfd.vnfd_version = vnf_data.get('descriptor_version')
        package_vnfd.create()

        for flavour in flavours:
            self._create_flavour(context, vnf_package.id, flavour)

    @revert_upload_vnf_package
    def upload_vnf_package_content(self, context, vnf_package):
        location = vnf_package.location_glance_store
        zip_path = glance_store.load_csar(vnf_package.id, location)
        vnf_data, flavours, vnf_artifacts = csar_utils.load_csar_data(
            context.elevated(), vnf_package.id, zip_path)
        self._onboard_vnf_package(
            context,
            vnf_package,
            vnf_data,
            flavours,
            vnf_artifacts)
        vnf_package.onboarding_state = (
            fields.PackageOnboardingStateType.ONBOARDED)
        vnf_package.operational_state = (
            fields.PackageOperationalStateType.ENABLED)

        vnf_package.save()

    @revert_upload_vnf_package
    def upload_vnf_package_from_uri(self, context, vnf_package,
                                    address_information, user_name=None,
                                    password=None):

        body = {"address_information": address_information,
                "user_name": user_name,
                "password": password}
        (location, size, checksum, multihash,
         loc_meta) = glance_store.store_csar(context, vnf_package.id, body)

        vnf_package.onboarding_state = (
            fields.PackageOnboardingStateType.PROCESSING)

        vnf_package.algorithm = CONF.vnf_package.hashing_algorithm
        vnf_package.hash = multihash
        vnf_package.location_glance_store = location
        vnf_package.size = size
        vnf_package.save()

        zip_path = glance_store.load_csar(vnf_package.id, location)
        vnf_data, flavours, vnf_artifacts = csar_utils.load_csar_data(
            context.elevated(), vnf_package.id, zip_path)

        self._onboard_vnf_package(
            context,
            vnf_package,
            vnf_data,
            flavours,
            vnf_artifacts)

        vnf_package.onboarding_state = (
            fields.PackageOnboardingStateType.ONBOARDED)
        vnf_package.operational_state = (
            fields.PackageOperationalStateType.ENABLED)

        vnf_package.save()

    def delete_vnf_package(self, context, vnf_package):
        if (vnf_package.onboarding_state ==
                fields.PackageOnboardingStateType.ONBOARDED):

            _delete_csar(context, vnf_package)

        vnf_package.destroy(context)

    def get_vnf_package_vnfd(self, context, vnf_package):
        csar_path = os.path.join(CONF.vnf_package.vnf_package_csar_path,
                                 vnf_package.id)
        if not os.path.isdir(csar_path):
            location = vnf_package.location_glance_store
            try:
                zip_path = glance_store.load_csar(vnf_package.id, location)
                csar_utils.extract_csar_zip_file(zip_path, csar_path)
            except (store_exceptions.GlanceStoreException) as e:
                exc_msg = encodeutils.exception_to_unicode(e)
                msg = (_("Exception raised from glance store can be "
                         "unrecoverable if it is not related to connection"
                         " error. Error: %s.") % exc_msg)
                raise exceptions.FailedToGetVnfdData(error=msg)
        try:
            return self._read_vnfd_files(csar_path)
        except Exception as e:
            exc_msg = encodeutils.exception_to_unicode(e)
            msg = (_("Exception raised while reading csar file"
                     " Error: %s.") % exc_msg)
            raise exceptions.FailedToGetVnfdData(error=msg)

    def _read_vnfd_files(self, csar_path):
        """Creating a dictionary with file path as key and file data as value.

        It will contain YAML files representing the VNFD, and information
        necessary to navigate the ZIP file and to identify the file that is
        the entry point for parsing the VNFD such as TOSCA-meta is included.
        """

        def _add_recursively_imported_files(imported_yamls, file_path_and_data,
                                            dir_of_parent_definition_file=''):
            for file in imported_yamls:
                file_path = os.path.join(
                    csar_path, dir_of_parent_definition_file, file)
                with open(file_path) as f:
                    file_data = yaml.safe_load(f)
                dest_file_path = os.path.abspath(file_path).split(
                    csar_path + '/')[-1]
                file_path_and_data[dest_file_path] = yaml.dump(file_data)

                if file_data.get('imports'):
                    dir_of_parent_definition_file = '/'.join(
                        file_path.split('/')[:-1])
                    _add_recursively_imported_files(
                        file_data['imports'], file_path_and_data,
                        dir_of_parent_definition_file)

        file_path_and_data = {}
        if 'TOSCA-Metadata' in os.listdir(csar_path) and os.path.isdir(
                os.path.join(csar_path, 'TOSCA-Metadata')):
            # This is CSAR containing a TOSCA-Metadata directory, which
            # includes the TOSCA.meta metadata file providing an entry
            # information for processing a CSAR file.
            with open(os.path.join(
                    csar_path, 'TOSCA-Metadata', 'TOSCA.meta')) as f:
                tosca_meta_data = yaml.safe_load(f)
            file_path_and_data['TOSCA-Metadata/TOSCA.meta'] = yaml.dump(
                tosca_meta_data)
            entry_defination_file = tosca_meta_data['Entry-Definitions']
            _add_recursively_imported_files([entry_defination_file],
                                            file_path_and_data)
        else:
            # This is a CSAR without a TOSCA-Metadata directory and containing
            # a single yaml file with a .yml or .yaml extension at the root of
            # the archive.
            root_yaml_file = sorted(
                os.listdir(csar_path),
                key=lambda item: item.endswith(('yaml', '.yml')))[-1]
            src_path = os.path.join(csar_path, root_yaml_file)
            with open(src_path) as f:
                file_data = yaml.safe_load(f)
            file_path_and_data[root_yaml_file] = yaml.dump(file_data)

        return file_path_and_data

    @periodic_task.periodic_task(spacing=CONF.vnf_package_delete_interval)
    def _run_cleanup_vnf_packages(self, context):
        """Delete orphan extracted csar zip and files from extracted path

        This periodic task will get all deleted packages for the period
        (now - CONF.vnf_package_delete_interval) and delete any left out
        csar zip files and vnf packages files from the extracted path.
        """

        time_duration = datetime.datetime.utcnow() - datetime.timedelta(
            seconds=CONF.vnf_package_delete_interval)
        filters = {'field': 'deleted_at', 'model': 'VnfPackage',
                   'value': time_duration,
                   'op': '>='}
        deleted_vnf_packages = VnfPackagesList.get_by_filters(
            context.elevated(), read_deleted='only', filters=filters)
        for vnf_pack in deleted_vnf_packages:
            csar_zip_temp_path = (CONF.vnf_package.vnf_package_csar_path +
                                  vnf_pack.id)
            csar_path = (CONF.vnf_package.vnf_package_csar_path +
                         vnf_pack.id + '.zip')
            try:
                if os.path.exists(csar_zip_temp_path):
                    shutil.rmtree(csar_zip_temp_path)
                    os.remove(csar_path)
            except OSError:
                LOG.warning("Failed to delete csar zip %(zip)s and"
                            " folder $(folder)s for vnf package %(uuid)s.",
                            {'zip': csar_path, 'folder': csar_zip_temp_path,
                             'uuid': vnf_pack.id})

    @coordination.synchronized('{vnf_instance[id]}')
    def instantiate(self, context, vnf_instance, instantiate_vnf):
        # Check if vnf is already instantiated.
        vnf_instance = objects.VnfInstance.get_by_id(context,
            vnf_instance.id)
        if vnf_instance.instantiation_state == \
           fields.VnfInstanceState.INSTANTIATED:
            LOG.error("Vnf instance %(id)s is already in %(state)s state.",
                     {"id": vnf_instance.id,
                     "state": vnf_instance.instantiation_state})
            return

        self.vnflcm_driver.instantiate_vnf(context, vnf_instance,
                                           instantiate_vnf)

        vnf_package_vnfd = objects.VnfPackageVnfd.get_by_id(context,
                vnf_instance.vnfd_id)
        vnf_package = objects.VnfPackage.get_by_id(context,
                vnf_package_vnfd.package_uuid, expected_attrs=['vnfd'])
        try:
            self._update_package_usage_state(context, vnf_package)
        except Exception:
            LOG.error("Failed to update usage_state of vnf package %s",
                      vnf_package.id)

    @coordination.synchronized('{vnf_package[id]}')
    def _update_package_usage_state(self, context, vnf_package):
        """Update vnf package usage state to IN_USE/NOT_IN_USE

        If vnf package is not used by any of the vnf instances, it's usage
        state should be set to NOT_IN_USE otherwise it should be set to
        IN_USE.
        """
        result = vnf_package.is_package_in_use(context)
        if result:
            vnf_package.usage_state = fields.PackageUsageStateType.IN_USE
        else:
            vnf_package.usage_state = fields.PackageUsageStateType.NOT_IN_USE

        vnf_package.save()

    @coordination.synchronized('{vnf_instance[id]}')
    def terminate(self, context, vnf_instance, terminate_vnf_req):
        # Check if vnf is in instantiated state.
        vnf_instance = objects.VnfInstance.get_by_id(context,
            vnf_instance.id)
        if vnf_instance.instantiation_state == \
                fields.VnfInstanceState.NOT_INSTANTIATED:
            LOG.error("Terminate action cannot be performed on vnf %(id)s "
                      "which is in %(state)s state.",
                      {"id": vnf_instance.id,
                      "state": vnf_instance.instantiation_state})
            return

        self.vnflcm_driver.terminate_vnf(context, vnf_instance,
            terminate_vnf_req)

        vnf_package_vnfd = objects.VnfPackageVnfd.get_by_id(context,
                vnf_instance.vnfd_id)
        vnf_package = objects.VnfPackage.get_by_id(context,
                vnf_package_vnfd.package_uuid, expected_attrs=['vnfd'])
        try:
            self._update_package_usage_state(context, vnf_package)
        except Exception:
            LOG.error("Failed to update usage_state of vnf package %s",
                      vnf_package.id)

    @coordination.synchronized('{vnf_instance[id]}')
    def heal(self, context, vnf_instance, heal_vnf_request):
        # Check if vnf is in instantiated state.
        vnf_instance = objects.VnfInstance.get_by_id(context,
            vnf_instance.id)
        if vnf_instance.instantiation_state == \
                fields.VnfInstanceState.NOT_INSTANTIATED:
            LOG.error("Heal action cannot be performed on vnf %(id)s "
                      "which is in %(state)s state.",
                      {"id": vnf_instance.id,
                      "state": vnf_instance.instantiation_state})
            return

        self.vnflcm_driver.heal_vnf(context, vnf_instance, heal_vnf_request)


def init(args, **kwargs):
    CONF(args=args, project='tacker',
         version='%%prog %s' % version.version_info.release_string(),
         **kwargs)

    # FIXME(ihrachys): if import is put in global, circular import
    # failure occurs
    from tacker.common import rpc as n_rpc
    n_rpc.init(CONF)


def main(manager='tacker.conductor.conductor_server.Conductor'):
    init(sys.argv[1:])
    objects.register_all()
    logging.setup(CONF, "tacker")
    oslo_messaging.set_transport_defaults(control_exchange='tacker')
    logging.setup(CONF, "tacker")
    CONF.log_opt_values(LOG, logging.DEBUG)
    server = tacker_service.Service.create(
        binary='tacker-conductor',
        topic=topics.TOPIC_CONDUCTOR,
        manager=manager)
    service.launch(CONF, server, restart_method='mutate').wait()
