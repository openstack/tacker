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
import copy
import datetime
import functools
import inspect
import json
import os
import oslo_messaging
import requests
import shutil
import sys
import time
import traceback
import yaml

from glance_store import exceptions as store_exceptions
from oslo_config import cfg
from oslo_log import log as logging
from oslo_serialization import jsonutils
from oslo_service import periodic_task
from oslo_service import service
from oslo_utils import encodeutils
from oslo_utils import excutils
from oslo_utils import timeutils
from oslo_utils import uuidutils
from sqlalchemy import exc as sqlexc
from sqlalchemy.orm import exc as orm_exc

from tacker import auth
from tacker.common import coordination
from tacker.common import csar_utils
from tacker.common import driver_manager
from tacker.common import exceptions
from tacker.common import log
from tacker.common import safe_utils
from tacker.common import topics
from tacker.common import utils
import tacker.conf
from tacker import context as t_context
from tacker.db.common_services import common_services_db
from tacker.db.db_sqlalchemy import models
from tacker.db.nfvo import nfvo_db
from tacker.db.vnfm import vnfm_db
from tacker.extensions import nfvo
from tacker.glance_store import store as glance_store
from tacker import manager
from tacker import objects
from tacker.objects import fields
from tacker.objects.fields import ErrorPoint as EP
from tacker.objects.vnf_lcm_subscriptions import LccnSubscriptionRequest
from tacker.objects.vnf_package import VnfPackagesList
from tacker.objects import vnfd as vnfd_db
from tacker.objects import vnfd_attribute as vnfd_attribute_db
from tacker.plugins.common import constants
from tacker import service as tacker_service
from tacker.sol_refactored.conductor import v2_hook
from tacker.sol_refactored import objects as sol_objects
from tacker import version
from tacker.vnflcm import utils as vnflcm_utils
from tacker.vnflcm import vnflcm_driver
from tacker.vnfm import nfvo_client
from tacker.vnfm import plugin

CONF = tacker.conf.CONF

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


def config_opts():
    return [('keystone_authtoken', OPTS)]


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


@utils.expects_func_args('vnf_lcm_opoccs')
def revert_update_lcm(function):
    """Decorator to revert update_lcm on failure."""
    @functools.wraps(function)
    def decorated_function(self, context, *args, **kwargs):
        try:
            return function(self, context, *args, **kwargs)
        except Exception as exp:
            LOG.error("update vnf_instance failed %s" % exp)
            with excutils.save_and_reraise_exception():
                wrapped_func = safe_utils.get_wrapped_function(function)
                keyed_args = inspect.getcallargs(wrapped_func, self, context,
                                                 *args, **kwargs)
                context = keyed_args['context']
                vnf_lcm_opoccs = keyed_args['vnf_lcm_opoccs']

                try:
                    # update vnf
                    vnf_now = timeutils.utcnow()
                    vnf_obj = objects.vnf.VNF(context=context)
                    vnf_obj.id = vnf_lcm_opoccs.get('vnf_instance_id')
                    vnf_obj.status = 'ERROR'
                    vnf_obj.updated_at = vnf_now
                    vnf_obj.save()

                    e_msg = str(exp)

                    # update lcm_op_occs
                    problem_obj = objects.vnf_lcm_op_occs.ProblemDetails()
                    problem_obj.status = '500'
                    problem_obj.detail = e_msg

                    lcm_op_obj = objects.vnf_lcm_op_occs.VnfLcmOpOcc(
                        context=context)
                    lcm_op_obj.id = vnf_lcm_opoccs.get('id')
                    lcm_op_obj.operation_state =\
                        fields.LcmOccsOperationState.FAILED_TEMP
                    lcm_op_obj.error = problem_obj
                    lcm_op_obj.state_entered_time = vnf_now
                    lcm_op_obj.updated_at = vnf_now
                    lcm_op_obj.save()

                    # Notification
                    notification = {}
                    notification['notificationType'] = \
                        'VnfLcmOperationOccurrenceNotification'
                    notification['notificationStatus'] = 'RESULT'
                    notification['operationState'] = \
                        fields.LcmOccsOperationState.FAILED_TEMP
                    notification['vnfInstanceId'] = vnf_lcm_opoccs.get(
                        'vnf_instance_id')
                    notification['operation'] = 'MODIFY_INFO'
                    notification['isAutomaticInvocation'] = 'False'
                    notification['vnfLcmOpOccId'] = vnf_lcm_opoccs.get('id')
                    notification['error'] = jsonutils.dumps(
                        problem_obj.to_dict())
                    instance_url = self._get_vnf_instance_href(
                        vnf_lcm_opoccs.get('vnf_instance_id'))
                    lcm_url = self._get_vnf_lcm_op_occs_href(
                        vnf_lcm_opoccs.get('id'))
                    notification['_links'] = {
                        'vnfInstance': {
                            'href': instance_url},
                        'vnfLcmOpOcc': {
                            'href': lcm_url}}
                    self.send_notification(context, notification)

                except Exception as msg:
                    LOG.error("revert_update_lcm failed %s" % str(msg))

    return decorated_function


@utils.expects_func_args('vnf_instance', 'vnf_lcm_op_occ_id')
def grant_error_common(function):
    """Decorator to revert upload_vnf_package on failure."""

    @functools.wraps(function)
    def decorated_function(self, context, *args, **kwargs):
        try:
            return function(self, context, *args, **kwargs)
        except Exception:
            with excutils.save_and_reraise_exception():
                wrapped_func = safe_utils.get_wrapped_function(function)
                keyed_args = inspect.getcallargs(wrapped_func, self, context,
                                                 *args, **kwargs)
                context = keyed_args['context']
                vnf_instance = keyed_args['vnf_instance']
                vnf_lcm_op_occ_id = keyed_args['vnf_lcm_op_occ_id']
                try:
                    vnf_lcm_op_occs = objects.VnfLcmOpOcc.get_by_id(
                        context, vnf_lcm_op_occ_id)
                    timestamp = datetime.datetime.utcnow()
                    vnf_lcm_op_occs.operation_state = 'ROLLED_BACK'
                    vnf_lcm_op_occs.state_entered_time = timestamp
                    vnf_lcm_op_occs.save()
                except Exception as e:
                    LOG.warning("Failed to update vnf_lcm_op_occ for vnf "
                                "instance %(id)s. Error: %(error)s",
                                {"id": vnf_instance.id, "error": e})

                try:
                    notification = {}
                    notification['notificationType'] = \
                        'VnfLcmOperationOccurrenceNotification'
                    notification['vnfInstanceId'] = vnf_instance.id
                    notification['notificationStatus'] = 'RESULT'
                    notification['operation'] = vnf_lcm_op_occs.operation
                    notification['operationState'] = 'ROLLED_BACK'
                    notification['isAutomaticInvocation'] = \
                        vnf_lcm_op_occs.is_automatic_invocation
                    notification['vnfLcmOpOccId'] = vnf_lcm_op_occ_id
                    insta_url = CONF.vnf_lcm.endpoint_url + \
                        "/vnflcm/v1/vnf_instances/" + \
                        vnf_instance.id
                    vnflcm_url = CONF.vnf_lcm.endpoint_url + \
                        "/vnflcm/v1/vnf_lcm_op_occs/" + \
                        vnf_lcm_op_occ_id
                    notification['_links'] = {}
                    notification['_links']['vnfInstance'] = {}
                    notification['_links']['vnfInstance']['href'] = insta_url
                    notification['_links']['vnfLcmOpOcc'] = {}
                    notification['_links']['vnfLcmOpOcc']['href'] = vnflcm_url
                    self.send_notification(context, notification)
                except Exception as e:
                    LOG.warning("Failed notification for vnf "
                                "instance %(id)s. Error: %(error)s",
                                {"id": vnf_instance.id, "error": e})

    return decorated_function


class Conductor(manager.Manager, v2_hook.ConductorV2Hook):
    def __init__(self, host, conf=None):
        if conf:
            self.conf = conf
        else:
            self.conf = CONF
        super(Conductor, self).__init__(host=self.conf.host)
        self.vnfm_plugin = plugin.VNFMPlugin()
        self.vnflcm_driver = vnflcm_driver.VnfLcmDriver()
        self.vnf_manager = driver_manager.DriverManager(
            'tacker.tacker.vnfm.drivers',
            cfg.CONF.tacker.infra_driver)

    def start(self):
        coordination.COORDINATOR.start()

    def stop(self):
        coordination.COORDINATOR.stop()

    def init_host(self):
        glance_store.initialize_glance_store()
        self._basic_config_check()

    def _get_vnf_instance_href(self, vnf_instance_id):
        return '{endpoint}/vnflcm/v1/vnf_instances/{id}'.format(
            endpoint=CONF.vnf_lcm.endpoint_url.rstrip("/"),
            id=vnf_instance_id)

    def _get_vnf_lcm_op_occs_href(self, vnf_lcm_op_occs_id):
        return '{endpoint}/vnflcm/v1/vnf_lcm_op_occs/{id}'.format(
            endpoint=CONF.vnf_lcm.endpoint_url.rstrip("/"),
            id=vnf_lcm_op_occs_id)

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
                vnf_sw_image.min_ram = sw_image.get('min_ram')
            else:
                vnf_sw_image.min_ram = 0
        vnf_sw_image.min_disk = sw_image.get('min_disk')
        vnf_sw_image.size = sw_image.get('size')
        vnf_sw_image.image_path = sw_image.get('image_path')
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

        self._onboard_vnfd(context, vnf_package, vnf_data, flavours)

        for flavour in flavours:
            self._create_flavour(context, vnf_package.id, flavour)

    def _onboard_vnfd(self, context, vnf_package, vnf_data, flavours):
        vnfd = vnfd_db.Vnfd(context=context)
        vnfd.id = vnf_data.get('descriptor_id')
        vnfd.tenant_id = context.tenant_id
        vnfd.name = vnf_data.get('product_name') + '-' + \
            vnf_data.get('descriptor_version')
        vnfd.discription = vnf_data.get('discription')
        for flavour in flavours:
            if flavour.get('mgmt_driver'):
                vnfd.mgmt_driver = flavour.get('mgmt_driver')
            break
        vnfd.create()

        for flavour in flavours:
            vnfd_attribute = vnfd_attribute_db.VnfdAttribute(context=context)
            vnfd_attribute.id = uuidutils.generate_uuid()
            vnfd_attribute.vnfd_id = vnf_data.get('descriptor_id')
            vnfd_attribute.key = 'vnfd_' + flavour['flavour_id']
            vnfd_attribute.value = \
                yaml.dump(flavour.get('tpl_dict'), default_flow_style=False)
            vnfd_attribute.create()

    @revert_upload_vnf_package
    def upload_vnf_package_content(self, context, vnf_package):
        vnf_package.onboarding_state = (
            fields.PackageOnboardingStateType.PROCESSING)
        try:
            vnf_package.save()

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

        except Exception as msg:
            raise Exception(msg)

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

        # TODO(h-asahina): stop using these Legacy DB
        if vnf_package.vnfd is not None:
            objects.VnfdAttribute(context).delete(vnf_package.vnfd.vnfd_id)
            objects.Vnfd(context).delete(vnf_package.vnfd.vnfd_id)

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
                msg = ("Exception raised while extracting csar zip file"
                       " Error: %s." % exc_msg)
                raise exceptions.FailedToGetVnfdData(error=msg)
        try:
            return self._read_vnfd_files(csar_path)
        except Exception as e:
            exc_msg = encodeutils.exception_to_unicode(e)
            msg = ("Exception raised while reading csar file"
                   " Error: %s." % exc_msg)
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

    @log.log
    def _change_vnf_status(self, context, vnf_id, state_conditions,
            new_status):
        if isinstance(state_conditions, str):
            state_conditions = {state_conditions}

        '''Change vnf status'''
        with context.session.begin(subtransactions=True):
            updated_values = {'status': new_status,
                              'updated_at': timeutils.utcnow()}
            vnf_model = (context.session
                         .query(vnfm_db.VNF).
                         filter_by(id=vnf_id).first())
            LOG.debug("Change status of vnf %s from %s to %s", vnf_id,
                      vnf_model.status, new_status)
            if not vnf_model:
                raise exceptions.VnfInstanceNotFound(
                    message="VNF {} not found".format(vnf_id))
            if vnf_model.status not in state_conditions:
                raise exceptions.VnfConflictState(
                    message=('Cannot change status to %s while in %s'
                             % (updated_values['status'], vnf_model.status)))
            vnf_model.update(updated_values)

    def _update_vnf_attributes(self, context, vnf_instance, vnf_dict,
            current_statuses, new_status, vim_id=None):
        with context.session.begin(subtransactions=True):
            try:
                modified_attributes = {}
                added_attributes = {}
                updated_values = {
                    'mgmt_ip_address': vnf_dict['mgmt_ip_address'],
                    'status': new_status,
                    'updated_at': timeutils.utcnow()}
                if vim_id:
                    updated_values['vim_id'] = vim_id
                vnf_model = (context.session.query(vnfm_db.VNF).filter_by(
                    id=vnf_dict['id']).first())
                if not vnf_model:
                    raise exceptions.VnfInstanceNotFound(
                        message="VNF {} not found".format(vnf_dict['id']))
                if vnf_model.status not in current_statuses:
                    raise exceptions.VnfConflictState(
                        message='Cannot change status to {} while \
                            in {}'.format(updated_values['status'],
                            vnf_model.status))
                if hasattr(vnf_instance.instantiated_vnf_info, 'instance_id'):
                    instance_id = \
                        vnf_instance.instantiated_vnf_info.instance_id
                    if instance_id:
                        # add instance_id info
                        updated_values.update({'instance_id': instance_id})
                vnf_model.update(updated_values)

                for key, val in vnf_dict['attributes'].items():
                    vnf_attr_model = (context.session.query(
                        vnfm_db.VNFAttribute).
                        filter_by(vnf_id=vnf_dict['id']).
                        filter_by(key=key).first())
                    if vnf_attr_model:
                        modified_attributes.update(
                            {vnf_attr_model.key: vnf_attr_model.value})
                        vnf_attr_model.update({'value': val})
                    else:
                        added_attributes.update({key: val})
                        vnf_attr_model = vnfm_db.VNFAttribute(
                            id=uuidutils.generate_uuid(),
                            vnf_id=vnf_dict['id'],
                            key=key, value=val)
                        context.session.add(vnf_attr_model)

            except Exception as exc:
                with excutils.save_and_reraise_exception():
                    LOG.error("Error in updating tables {}".format(str(exc)))
                    # Roll back modified/added vnf attributes
                    for key, val in modified_attributes.items():
                        vnf_attr_model = (context.session.query(
                            vnfm_db.VNFAttribute).
                            filter_by(vnf_id=vnf_dict['id']).
                            filter_by(key=key).first())
                        if vnf_attr_model:
                            vnf_attr_model.update({'value': val})

                    for key, val in added_attributes.items():
                        vnf_attr_model = (context.session.query(
                            vnfm_db.VNFAttribute).
                            filter_by(vnf_id=vnf_dict['id']).
                            filter_by(key=key).first())
                        if vnf_attr_model:
                            vnf_attr_model.delete()

    @log.log
    def _build_instantiated_vnf_info(self, context, vnf_instance,
            instantiate_vnf_req=None):
        try:
            # if instantiate_vnf_req is not present, create from vnf_instance
            if not instantiate_vnf_req:
                instantiate_vnf_req = objects.InstantiateVnfRequest.\
                    from_vnf_instance(vnf_instance)

            # update instantiated vnf info based on created stack resources
            if hasattr(vnf_instance.instantiated_vnf_info, 'instance_id'):

                # get final vnfd_dict
                vnfd_dict = vnflcm_utils._get_vnfd_dict(context,
                    vnf_instance.vnfd_id,
                    instantiate_vnf_req.flavour_id)

                # get vim_connection info from request
                vim_info = vnflcm_utils._get_vim(context,
                        instantiate_vnf_req.vim_connection_info)

                vim_connection_info = objects.VimConnectionInfo.\
                    obj_from_primitive(vim_info, context)

                if not vnf_instance.instantiated_vnf_info.instance_id:
                    vnflcm_utils._build_instantiated_vnf_info(
                        vnfd_dict, instantiate_vnf_req, vnf_instance,
                        vim_id=vim_connection_info.vim_id)

                if vnf_instance.instantiated_vnf_info.instance_id:
                    self.vnf_manager.invoke(vim_connection_info.vim_type,
                                'post_vnf_instantiation', context=context,
                                vnf_instance=vnf_instance,
                                vim_connection_info=vim_connection_info,
                                instantiate_vnf_req=instantiate_vnf_req)

        except Exception as ex:
            try:
                vnf_instance.instantiated_vnf_info.reinitialize()
                vnf_instance.instantiated_vnf_info.save()
            finally:
                error_msg = "Failed to build instantiation information \
                            for vnf {} because {}".\
                    format(vnf_instance.id, encodeutils.
                        exception_to_unicode(ex))
                LOG.error("_build_instantiated_vnf_info error {}".
                    format(error_msg))
                raise exceptions.TackerException(message=error_msg)

    @log.log
    def _update_instantiated_vnf_info(
            self, context, vnf_instance, heal_vnf_request):
        try:
            vim_info = vnflcm_utils._get_vim(context,
                                             vnf_instance.vim_connection_info)
            vim_connection_info = \
                objects.VimConnectionInfo.obj_from_primitive(
                    vim_info, context)

            self.vnf_manager.invoke(
                vim_connection_info.vim_type, 'post_heal_vnf',
                context=context, vnf_instance=vnf_instance,
                vim_connection_info=vim_connection_info,
                heal_vnf_request=heal_vnf_request)

        except Exception as exp:
            error_msg = \
                "Failed to update instantiation information for vnf {}: {}".\
                format(vnf_instance.id, encodeutils.exception_to_unicode(exp))
            LOG.error("_update_instantiated_vnf_info error {}".
                format(error_msg))
            raise exceptions.TackerException(message=error_msg)

    @log.log
    def _update_instantiated_vnf_info_change_ext_conn(
            self, context, vnf_instance, change_ext_conn_req):
        try:
            vim_info = vnflcm_utils._get_vim(context,
                                             vnf_instance.vim_connection_info)
            vim_connection_info = \
                objects.VimConnectionInfo.obj_from_primitive(
                    vim_info, context)

            self.vnf_manager.invoke(
                vim_connection_info.vim_type, 'post_change_ext_conn_vnf',
                context=context, vnf_instance=vnf_instance,
                vim_connection_info=vim_connection_info)

            vnflcm_utils._update_instantiated_vnf_info(
                change_ext_conn_req, vnf_instance)
            vnf_instance.instantiated_vnf_info.save()
        except Exception as exp:
            error_msg = \
                "Failed to update instantiation information for vnf {}: {}".\
                format(vnf_instance.id, encodeutils.exception_to_unicode(exp))
            raise exceptions.TackerException(message=error_msg)

    @log.log
    def _add_additional_vnf_info(self, context, vnf_instance):
        '''this method adds misc info to 'vnf' table'''
        try:
            if hasattr(vnf_instance.instantiated_vnf_info, 'instance_id'):
                if vnf_instance.instantiated_vnf_info.instance_id:
                    # add instance_id info
                    instance_id = vnf_instance.instantiated_vnf_info.\
                        instance_id
                    with context.session.begin(subtransactions=True):
                        updated_values = {'instance_id': instance_id}
                        context.session.query(vnfm_db.VNF).filter_by(
                            id=vnf_instance.id).update(updated_values)

        except Exception as ex:
            # with excutils.save_and_reraise_exception():
            error_msg = "Failed to add additional vnf info to vnf {}. Details -\
                 {}".format(
                vnf_instance.id, str(ex))
            LOG.error("_add_additional_vnf_info error {}".format(error_msg))
            raise exceptions.TackerException(message=error_msg)

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

    def _get_vnf_link_ports_by_vl(self, vnf_info, ext_vl_id,
            resource_id):
        results = []
        vnf_vl_resource_info = vnf_info.vnf_virtual_link_resource_info
        for vnf_vl_res in vnf_vl_resource_info:
            if ((vnf_vl_res.vnf_virtual_link_desc_id == ext_vl_id) and
                    (vnf_vl_res.network_resource.resource_id != resource_id)):
                results.extend(vnf_vl_res.vnf_link_ports)

        return results

    def _get_vnf_link_ports_by_cp(self, vnf_info, cpd_id=None):
        vnf_vl_resource_info = vnf_info.vnf_virtual_link_resource_info
        vnfc_resource_info = vnf_info.vnfc_resource_info

        def _get_vnf_link_port(vnf_link_port_id):
            for vnf_vl_res in vnf_vl_resource_info:
                for vnf_link_port in vnf_vl_res.vnf_link_ports:
                    if vnf_link_port.id == vnf_link_port_id:
                        return vnf_link_port

        results = []
        for vnfc_resource in vnfc_resource_info:
            for vnfc_cp_info in vnfc_resource.vnfc_cp_info:
                if cpd_id == vnfc_cp_info.cpd_id:
                    results.append(
                        _get_vnf_link_port(vnfc_cp_info.vnf_link_port_id))

        return results

    @grant_error_common
    def _change_ext_conn_grant(
            self,
            context,
            vnf_instance,
            change_ext_conn_req,
            vnf_lcm_op_occ_id):
        if not self._get_grant_execute():
            return

        vnf_inf = vnf_instance.instantiated_vnf_info

        def _create_linkport_rd(linkport, cpd_id):
            rh = linkport.resource_handle
            rd = objects.ResourceDefinition()
            rd.resource = objects.ResourceHandle()
            rd.id = linkport.id
            rd.type = constants.TYPE_LINKPORT
            rd.resource_template_id = cpd_id
            rd.resource.vim_connection_id = rh.vim_connection_id
            rd.resource.resource_id = rh.resource_id
            rd.resource.vim_level_resource_type = rh.vim_level_resource_type
            return rd

        def _get_cpd_id(cp_instance_id):
            vnfc_resource_info = vnf_inf.vnfc_resource_info
            for vnfc_resource in vnfc_resource_info:
                for vnfc_cp_info in vnfc_resource.vnfc_cp_info:
                    if cp_instance_id == vnfc_cp_info.id:
                        return vnfc_cp_info.cpd_id

        update_resources = dict()
        # If network resource of the VirtualLink changed, get all LinkPort
        # resource related to VirtualLink
        for ext_vl in change_ext_conn_req.ext_virtual_links:
            nw_changed_resources = self._get_vnf_link_ports_by_vl(
                vnf_inf, ext_vl.id, ext_vl.resource_id)
            LOG.debug('nw_changed_resources {}'.format(nw_changed_resources))
            if nw_changed_resources:
                for resource in nw_changed_resources:
                    cpd_id = _get_cpd_id(resource.cp_instance_id)
                    update_resources[resource.resource_handle.resource_id] = \
                        _create_linkport_rd(resource, cpd_id)
                continue
            # If network resource of the VirtualLink does not change,
            # Searching vnfc_resource_info table by the cpd_id, if found, get
            # LinkPort resource corresponding the CP.
            # It does not check that the CP status updated or not.
            for ext_cp in ext_vl.ext_cps:
                cp_changed_resources = \
                    self._get_vnf_link_ports_by_cp(vnf_inf, ext_cp.cpd_id)
                LOG.debug('cp_changed_resources {}'.format(
                    cp_changed_resources))
                for resource in cp_changed_resources:
                    update_resources[resource.resource_handle.resource_id] = \
                        _create_linkport_rd(resource, ext_cp.cpd_id)

        update_resources_list = list(update_resources.values())
        LOG.debug("Update Resources: %s", update_resources_list)
        grant_request = self._make_grant_request(
            context,
            vnf_instance,
            vnf_lcm_op_occ_id,
            'CHANGE_EXT_CONN',
            False,
            update_resources=update_resources_list)
        return self._grant(context, grant_request)

    def _grant(self, context, grant_request):
        LOG.info(
            "grant start grant_request[%s]" %
            grant_request.to_request_body())

        response = nfvo_client.GrantRequest().grants(
            json=grant_request.to_request_body())

        res_body = response.json()
        res_dict = utils.convert_camelcase_to_snakecase(res_body)
        LOG.info("grant end res_body[%s]" % res_dict)
        grant_obj = objects.Grant.obj_from_primitive(
            res_dict, context=context)
        if len(grant_request.add_resources) != len(grant_obj.add_resources):
            msg = "grant add resource error"
            raise exceptions.ValidationError(detail=msg)
        if len(
                grant_request.remove_resources) != len(
                grant_obj.remove_resources):
            msg = "grant remove resource error"
            raise exceptions.ValidationError(detail=msg)
        if len(
                grant_request.update_resources) != len(
                grant_obj.update_resources):
            msg = "grant update resource error"
            raise exceptions.ValidationError(detail=msg)
        self._check_res_add_remove_rsc(context, grant_request, grant_obj)

        return grant_obj

    def _check_res_add_remove_rsc(self, context, grant_request, grant_obj):
        for add_resource in grant_request.add_resources:
            match_flg = False
            for rsc in grant_obj.add_resources:
                if add_resource.id == rsc.resource_definition_id:
                    match_flg = True
                    break
            if not match_flg:
                msg = "grant add resource error"
                raise exceptions.ValidationError(detail=msg)

        for remove_resource in grant_request.remove_resources:
            match_flg = False
            for rsc in grant_obj.remove_resources:
                if remove_resource.id == rsc.resource_definition_id:
                    match_flg = True
                    break
            if not match_flg:
                msg = "grant remove resource error"
                raise exceptions.ValidationError(detail=msg)

        for update_resource in grant_request.update_resources:
            match_flg = False
            for rsc in grant_obj.update_resources:
                if update_resource.id == rsc.resource_definition_id:
                    match_flg = True
                    break
            if not match_flg:
                msg = "grant update resource error"
                raise exceptions.ValidationError(detail=msg)

    @grant_error_common
    def _instantiate_grant(self,
                           context,
                           vnf_instance,
                           vnf_dict,
                           instantiate_vnf_request,
                           vnf_lcm_op_occ_id):
        vnfd_dict = vnflcm_utils._get_vnfd_dict(context,
            vnf_dict['vnfd']['id'],
            instantiate_vnf_request.flavour_id)
        inst_level = instantiate_vnf_request.instantiation_level_id
        vnf_instance.instantiated_vnf_info = objects.InstantiatedVnfInfo(
            flavour_id=instantiate_vnf_request.flavour_id,
            instantiation_level_id=inst_level,
            vnf_instance_id=vnf_instance.id)
        vnf_instance.instantiated_vnf_info.reinitialize()
        vnflcm_utils._build_instantiated_vnf_info(vnfd_dict,
                            instantiate_vnf_request, vnf_instance, '')
        if not self._get_grant_execute():
            return

        add_resources = []
        vnf_inf = vnf_instance.instantiated_vnf_info
        for vnfc_resource in vnf_inf.vnfc_resource_info:
            resource = objects.ResourceDefinition()
            resource.id = vnfc_resource.id
            resource.type = constants.TYPE_COMPUTE
            resource.vdu_id = vnfc_resource.vdu_id
            resource.resource_template_id = vnfc_resource.vdu_id
            add_resources.append(resource)

        for vl_resource in vnf_inf.vnf_virtual_link_resource_info:
            resource = objects.ResourceDefinition()
            resource.id = vl_resource.id
            resource.type = constants.TYPE_VL
            resource.resource_template_id = \
                vl_resource.vnf_virtual_link_desc_id
            add_resources.append(resource)
            for cp_resource in vl_resource.vnf_link_ports:
                for vnfc_resource in vnf_inf.vnfc_resource_info:
                    for vnfc_cp_resource in vnfc_resource.vnfc_cp_info:
                        if cp_resource.cp_instance_id == vnfc_cp_resource.id:
                            resource = objects.ResourceDefinition()
                            resource.id = cp_resource.id
                            resource.type = constants.TYPE_LINKPORT
                            resource.vdu_id = vnfc_resource.vdu_id
                            resource.resource_template_id = \
                                vnfc_cp_resource.cpd_id
                            add_resources.append(resource)

        for storage_resource in vnf_inf.virtual_storage_resource_info:
            for vnfc_resource in vnf_inf.vnfc_resource_info:
                if storage_resource.id in vnfc_resource.storage_resource_ids:
                    resource = objects.ResourceDefinition()
                    resource.id = storage_resource.id
                    resource.type = constants.TYPE_STORAGE
                    resource.vdu_id = vnfc_resource.vdu_id
                    resource.resource_template_id = \
                        storage_resource.virtual_storage_desc_id
                    add_resources.append(resource)

        p_c_list = []
        placement_obj_list = []
        topo_temp = vnfd_dict.get('topology_template', {})
        for policy in topo_temp.get('policies', []):
            affinity_type = {
                'tosca.policies.nfv.AntiAffinityRule': 'ANTI_AFFINITY',
                'tosca.policies.nfv.AffinityRule': 'AFFINITY'}
            for policy_name, policy_dict in policy.items():
                if policy_dict['type'] in affinity_type.keys():
                    placement_constraint = objects.PlacementConstraint()
                    key = policy_dict['type']
                    placement_constraint.affinity_or_anti_affinity = (
                        affinity_type[key])
                    placement_constraint.scope = 'ZONE'
                    placement_constraint.resource = []
                    placement_constraint.fallback_best_effort = True
                    for target in policy_dict.get('targets', []):
                        if target in topo_temp.get('groups', []):
                            for member in (topo_temp['groups'][target]
                                    ['members']):
                                for vnfc_rsc in vnf_inf.vnfc_resource_info:
                                    if member == vnfc_rsc.vdu_id:
                                        resource = \
                                            objects.ConstraintResourceRef()
                                        resource.id_type = 'GRANT'
                                        resource.resource_id = vnfc_rsc.id
                                        p_rsc = \
                                            placement_constraint.resource
                                        p_rsc.append(resource)
                                        break
                        else:
                            for vnfc_rsc in vnf_inf.vnfc_resource_info:
                                if target == vnfc_rsc.vdu_id:
                                    resource = \
                                        objects.ConstraintResourceRef()
                                    resource.id_type = 'GRANT'
                                    resource.resource_id = vnfc_rsc.id
                                    p_rsc = placement_constraint.resource
                                    p_rsc.append(resource)
                                    break
                    p_c_list.append(placement_constraint)
                    placement_obj = models.PlacementConstraint()
                    placement_obj.id = uuidutils.generate_uuid()
                    placement_obj.vnf_instance_id = vnf_instance.id
                    placement_obj.affinity_or_anti_affinity = \
                        placement_constraint.affinity_or_anti_affinity
                    placement_obj.scope = placement_constraint.scope
                    placement_obj.server_group_name = policy_name
                    p_c_dict = placement_constraint.to_dict()
                    res_dict = p_c_dict.get('resource', {})
                    res_json = json.dumps(res_dict)
                    placement_obj.resource = res_json
                    placement_obj.created_at = timeutils.utcnow()
                    placement_obj.deleted_at = datetime.datetime.min
                    placement_obj_list.append(placement_obj)

        g_request = self._make_grant_request(context,
                                             vnf_instance,
                                             vnf_lcm_op_occ_id,
                                             'INSTANTIATE',
                                             False,
                                             add_resources=add_resources,
                                             placement_constraints=p_c_list)

        vnf_dict['placement_obj_list'] = placement_obj_list
        vnf_dict['grant'] = self._grant(context, g_request)

    def _get_placement(self, context, vnf_instance):
        return self.vnfm_plugin.get_placement_constraint(context,
                                                         vnf_instance.id)

    @grant_error_common
    def _scale_grant(
            self,
            context,
            vnf_dict,
            vnf_instance,
            scale_vnf_request,
            vnf_lcm_op_occ_id):
        # Check if vnf is in instantiated state.
        vnf_instance = objects.VnfInstance.get_by_id(context,
            vnf_instance.id)
        if vnf_instance.instantiation_state == \
                fields.VnfInstanceState.NOT_INSTANTIATED:
            LOG.error("Scale action cannot be performed on vnf %(id)s "
                      "which is in %(state)s state.",
                      {"id": vnf_instance.id,
                      "state": vnf_instance.instantiation_state})
            raise Exception("Scale action cannot be performed on vnf")

        vim_info = vnflcm_utils._get_vim(
            context, vnf_instance.vim_connection_info)
        vim_connection_info = objects.VimConnectionInfo.obj_from_primitive(
            vim_info, context)
        if scale_vnf_request.type == 'SCALE_IN':
            vnf_dict['action'] = 'in'
            vnf_dict['policy_name'] = scale_vnf_request.aspect_id
            reverse = scale_vnf_request.additional_params.get('is_reverse')
            region_name = vim_connection_info.access_info.get('region_name')
            scale_id_list, scale_name_list, grp_id, res_num = \
                self.vnf_manager.invoke(vim_connection_info.vim_type,
                    'get_scale_in_ids',
                    plugin=self,
                    context=context,
                    vnf_dict=vnf_dict,
                    is_reverse=reverse,
                    auth_attr=vim_connection_info.access_info,
                    region_name=region_name,
                    number_of_steps=scale_vnf_request.number_of_steps)
            vnf_dict['res_num'] = res_num
        else:
            scale_id_list = []
        if not self._get_grant_execute():
            return None, []

        placement_obj_list = self.vnfm_plugin.get_placement_constraint(
            context, vnf_instance.id)
        self.vnf_manager.invoke(
            vim_connection_info.vim_type,
            'get_grant_resource',
            plugin=self,
            vnf_instance=vnf_instance,
            vnf_info=vnf_dict,
            scale_vnf_request=scale_vnf_request,
            placement_obj_list=placement_obj_list,
            vim_connection_info=vim_connection_info,
            del_list=scale_id_list
        )
        vnf_dict['placement_obj_list'] = placement_obj_list

        grant_request = self._make_grant_request(
            context,
            vnf_instance,
            vnf_lcm_op_occ_id,
            'SCALE',
            False,
            add_resources=vnf_dict['addResources'],
            remove_resources=vnf_dict['removeResources'],
            placement_constraints=vnf_dict['placement_constraint_list'])

        vnf_dict['grant'] = self._grant(context, grant_request)

    def _init_remove_resources(self, vnf_inf, rm_resources):
        for vnfc_resource in vnf_inf.vnfc_resource_info:
            resource = objects.ResourceDefinition()
            resource.id = vnfc_resource.id
            resource.type = constants.TYPE_COMPUTE
            resource.vdu_id = vnfc_resource.vdu_id
            resource.resource_template_id = vnfc_resource.vdu_id
            vim_id = vnfc_resource.compute_resource.vim_connection_id
            rsc_id = vnfc_resource.compute_resource.resource_id
            vnfc_rh = objects.ResourceHandle(
                vim_connection_id=vim_id,
                resource_id=rsc_id)
            resource.resource = vnfc_rh
            rm_resources.append(resource)

        for vl_resource in vnf_inf.vnf_virtual_link_resource_info:
            resource = objects.ResourceDefinition()
            resource.id = vl_resource.id
            resource.type = constants.TYPE_VL
            resource.resource_template_id = \
                vl_resource.vnf_virtual_link_desc_id
            vim_id = vl_resource.network_resource.vim_connection_id
            rsc_id = vl_resource.network_resource.resource_id
            vl_rh = objects.ResourceHandle(
                vim_connection_id=vim_id,
                resource_id=rsc_id)
            resource.resource = vl_rh
            rm_resources.append(resource)
            for cp_resource in vl_resource.vnf_link_ports:
                for vnfc_resource in vnf_inf.vnfc_resource_info:
                    for vnfc_cp_resource in vnfc_resource.vnfc_cp_info:
                        if cp_resource.cp_instance_id == \
                                vnfc_cp_resource.id:
                            resource = objects.ResourceDefinition()
                            resource.id = cp_resource.id
                            resource.type = constants.TYPE_LINKPORT
                            resource.vdu_id = vnfc_resource.vdu_id
                            resource.resource_template_id = \
                                vnfc_cp_resource.cpd_id
                            vim_id = \
                                cp_resource.resource_handle. \
                                vim_connection_id
                            rsc_id = cp_resource.resource_handle. \
                                resource_id
                            cp_rh = objects.ResourceHandle(
                                vim_connection_id=vim_id,
                                resource_id=rsc_id)
                            resource.resource = cp_rh
                            rm_resources.append(resource)

        for storage_resource in vnf_inf.virtual_storage_resource_info:
            for vnfc_resource in vnf_inf.vnfc_resource_info:
                if storage_resource.id in \
                        vnfc_resource.storage_resource_ids:
                    resource = objects.ResourceDefinition()
                    resource.id = storage_resource.id
                    resource.type = constants.TYPE_STORAGE
                    resource.vdu_id = vnfc_resource.vdu_id
                    resource.resource_template_id = \
                        storage_resource.virtual_storage_desc_id
                    vim_id = \
                        storage_resource.storage_resource. \
                        vim_connection_id
                    rsc_id = storage_resource.storage_resource.resource_id
                    st_rh = objects.ResourceHandle(
                        vim_connection_id=vim_id,
                        resource_id=rsc_id)
                    resource.resource = st_rh
                    rm_resources.append(resource)

    def _init_add_resources(self, context, vnf_instance, vim_connection_info,
                            add_resources, vnf_inf, placement_obj_list,
                            affinity_list, vnf_dict):
        instantiate_vnf_request = objects.InstantiateVnfRequest. \
            from_vnf_instance(vnf_instance)
        vnfd_dict = vnflcm_utils._get_vnfd_dict(
            context, vnf_instance.vnfd_id,
            instantiate_vnf_request.flavour_id)
        vnf_instance_after = copy.deepcopy(vnf_instance)
        vnf_instance_after.instantiated_vnf_info.reinitialize()
        vnflcm_utils._build_instantiated_vnf_info(
            vnfd_dict, instantiate_vnf_request,
            vnf_instance_after,
            vim_connection_info.vim_id)
        vnf_inf_after = vnf_instance_after.instantiated_vnf_info
        vnfc_rs_ids_list_before = []

        for vnfc_resource in vnf_inf_after.vnfc_resource_info:
            resource = objects.ResourceDefinition()
            resource.id = vnfc_resource.id
            resource.type = constants.TYPE_COMPUTE
            resource.vdu_id = vnfc_resource.vdu_id
            resource.resource_template_id = vnfc_resource.vdu_id
            add_resources.append(resource)

            for vnfc_resource_before in vnf_inf.vnfc_resource_info:
                if vnfc_resource_before.vdu_id == \
                        vnfc_resource.vdu_id and vnfc_resource_before.id \
                        not in vnfc_rs_ids_list_before:
                    key_id = vnfc_resource_before.id
                    vnfc_rs_ids_list_before.append(key_id)
                    break

            for placement_obj in placement_obj_list:
                resource_dict = jsonutils.loads(placement_obj.resource)
                set_flg = False
                for resource in resource_dict:
                    if resource.get('resource_id') == key_id:
                        resource['id_type'] = 'GRANT'
                        resource['resource_id'] = vnfc_resource.id
                        g_name = placement_obj.server_group_name
                        affinity_list.append(g_name)
                        set_flg = True
                        res_json = jsonutils.dump_as_bytes(resource_dict)
                        placement_obj.resource = res_json
                        break
                if set_flg:
                    break

        for vl_resource in vnf_inf_after.vnf_virtual_link_resource_info:
            resource = objects.ResourceDefinition()
            resource.id = vl_resource.id
            resource.type = constants.TYPE_VL
            resource.resource_template_id = \
                vl_resource.vnf_virtual_link_desc_id
            add_resources.append(resource)
            for cp_resource in vl_resource.vnf_link_ports:
                for vnfc_resource in vnf_inf_after.vnfc_resource_info:
                    for vnfc_cp_resource in vnfc_resource.vnfc_cp_info:
                        if cp_resource.cp_instance_id == \
                                vnfc_cp_resource.id:
                            resource = objects.ResourceDefinition()
                            resource.id = cp_resource.id
                            resource.type = constants.TYPE_LINKPORT
                            resource.vdu_id = vnfc_resource.vdu_id
                            resource.resource_template_id = \
                                vnfc_cp_resource.cpd_id
                            add_resources.append(resource)

        for storage_resource in vnf_inf_after. \
                virtual_storage_resource_info:
            for vnfc_resource in vnf_inf_after.vnfc_resource_info:
                if storage_resource.id in \
                        vnfc_resource.storage_resource_ids:
                    resource = objects.ResourceDefinition()
                    resource.id = storage_resource.id
                    resource.type = constants.TYPE_STORAGE
                    resource.vdu_id = vnfc_resource.vdu_id
                    resource.resource_template_id = \
                        storage_resource.virtual_storage_desc_id
                    add_resources.append(resource)
        vnf_dict['vnf_instance_after'] = vnf_instance_after

    @grant_error_common
    def _heal_grant(self,
                    context,
                    vnf_instance,
                    vnf_dict,
                    heal_vnf_request,
                    vnf_lcm_op_occ_id):
        vnf_inf = vnf_instance.instantiated_vnf_info
        if not self._get_grant_execute():
            return

        placement_obj_list = self._get_placement(context, vnf_instance)
        vim_info = vnflcm_utils._get_vim(context,
                                         vnf_instance.vim_connection_info)
        vim_connection_info = \
            objects.VimConnectionInfo.obj_from_primitive(vim_info, context)

        cinder_list = self.vnf_manager.invoke(vim_connection_info.vim_type,
                                              'get_cinder_list',
                                              vnf_info=vnf_dict)

        affinity_list = []
        rm_resources = []
        add_resources = []
        update_resources = []
        if not heal_vnf_request.vnfc_instance_id:
            # init remove_resources
            self._init_remove_resources(vnf_inf, rm_resources)
            # init add_resources
            self._init_add_resources(
                context, vnf_instance, vim_connection_info, add_resources,
                vnf_inf, placement_obj_list, affinity_list, vnf_dict)
        else:
            for vnfc_resource in vnf_inf.vnfc_resource_info:
                vnfc_key = vnfc_resource.id
                if vnfc_key in heal_vnf_request.vnfc_instance_id:
                    resource = objects.ResourceDefinition()
                    resource.id = vnfc_resource.id
                    resource.type = constants.TYPE_COMPUTE
                    resource.vdu_id = vnfc_resource.vdu_id
                    resource.resource_template_id = vnfc_resource.vdu_id
                    vim_id = vnfc_resource.compute_resource.vim_connection_id
                    rsc_id = vnfc_resource.compute_resource.resource_id
                    vnfc_rh = objects.ResourceHandle(
                        vim_connection_id=vim_id,
                        resource_id=rsc_id)
                    resource.resource = vnfc_rh
                    update_resources.append(resource)

                    key_id = vnfc_resource.compute_resource.resource_id
                    for placement_obj in placement_obj_list:
                        resource_dict = jsonutils.loads(placement_obj.resource)
                        set_flg = False
                        for resource in resource_dict:
                            if resource.get('resource_id') == key_id:
                                resource['id_type'] = 'GRANT'
                                resource['resource_id'] = vnfc_resource.id
                                g_name = placement_obj.server_group_name
                                affinity_list.append(g_name)
                                set_flg = True
                                res_json = \
                                    jsonutils.dump_as_bytes(resource_dict)
                                placement_obj.resource = res_json
                                break
                        if set_flg:
                            break

            st_info = vnf_inf.virtual_storage_resource_info
            for storage_resource in st_info:
                if storage_resource.virtual_storage_desc_id in cinder_list:
                    for vnfc_resource in vnf_inf.vnfc_resource_info:
                        id_list = vnfc_resource.storage_resource_ids
                        if storage_resource.id in id_list:
                            resource = objects.ResourceDefinition()
                            resource.id = storage_resource.id
                            resource.type = constants.TYPE_STORAGE
                            resource.vdu_id = vnfc_resource.vdu_id
                            resource.resource_template_id = \
                                storage_resource.virtual_storage_desc_id
                            st_rh = objects.ResourceHandle()
                            st_rh.vim_connection_id = \
                                storage_resource.storage_resource.\
                                vim_connection_id
                            st_rh.resource_id = \
                                storage_resource.storage_resource.resource_id
                            resource.resource = st_rh
                            update_resources.append(resource)

        p_c_list = []
        for placement_obj in placement_obj_list:
            p_constraint = objects.PlacementConstraint()
            p_constraint.affinity_or_anti_affinity = \
                placement_obj.affinity_or_anti_affinity
            p_constraint.scope = placement_obj.scope
            resource_dict = jsonutils.loads(placement_obj.resource)
            p_constraint.resource = []
            for rsc in resource_dict:
                rsc_obj = objects.ConstraintResourceRef()
                rsc_obj.id_type = rsc.get('id_type')
                rsc_obj.resource_id = rsc.get('resource_id')
                p_constraint.resource.append(rsc_obj)
            p_constraint.fallback_best_effort = True
            p_c_list.append(p_constraint)

        g_request = self._make_grant_request(context,
                                             vnf_instance,
                                             vnf_lcm_op_occ_id,
                                             'HEAL',
                                             False,
                                             add_resources=add_resources,
                                             remove_resources=rm_resources,
                                             update_resources=update_resources,
                                             placement_constraints=p_c_list)

        vnf_dict['placement_obj_list'] = placement_obj_list
        vnf_dict['grant'] = self._grant(context, g_request)

    @grant_error_common
    def _terminate_grant(self, context, vnf_instance, vnf_lcm_op_occ_id):
        vnf_inf = vnf_instance.instantiated_vnf_info
        if not self._get_grant_execute():
            return

        rm_resources = []
        for vnfc_resource in vnf_inf.vnfc_resource_info:
            resource = objects.ResourceDefinition()
            resource.id = vnfc_resource.id
            resource.type = constants.TYPE_COMPUTE
            resource.vdu_id = vnfc_resource.vdu_id
            resource.resource_template_id = vnfc_resource.vdu_id
            vim_id = vnfc_resource.compute_resource.vim_connection_id
            rsc_id = vnfc_resource.compute_resource.resource_id
            vnfc_rh = objects.ResourceHandle(
                vim_connection_id=vim_id,
                resource_id=rsc_id)
            resource.resource = vnfc_rh
            rm_resources.append(resource)

        for vl_resource in vnf_inf.vnf_virtual_link_resource_info:
            resource = objects.ResourceDefinition()
            resource.id = vl_resource.id
            resource.type = constants.TYPE_VL
            resource.resource_template_id = \
                vl_resource.vnf_virtual_link_desc_id
            vim_id = vl_resource.network_resource.vim_connection_id
            rsc_id = vl_resource.network_resource.resource_id
            vl_rh = objects.ResourceHandle(
                vim_connection_id=vim_id,
                resource_id=rsc_id)
            resource.resource = vl_rh
            rm_resources.append(resource)
            for cp_resource in vl_resource.vnf_link_ports:
                for vnfc_resource in vnf_inf.vnfc_resource_info:
                    for vnfc_cp_resource in vnfc_resource.vnfc_cp_info:
                        if cp_resource.cp_instance_id == vnfc_cp_resource.id:
                            resource = objects.ResourceDefinition()
                            resource.id = cp_resource.id
                            resource.type = constants.TYPE_LINKPORT
                            resource.vdu_id = vnfc_resource.vdu_id
                            resource.resource_template_id = \
                                vnfc_cp_resource.cpd_id
                            vim_id = \
                                cp_resource.resource_handle.vim_connection_id
                            rsc_id = cp_resource.resource_handle.resource_id
                            cp_rh = objects.ResourceHandle(
                                vim_connection_id=vim_id,
                                resource_id=rsc_id)
                            resource.resource = cp_rh
                            rm_resources.append(resource)

        for storage_resource in vnf_inf.virtual_storage_resource_info:
            for vnfc_resource in vnf_inf.vnfc_resource_info:
                if storage_resource.id in vnfc_resource.storage_resource_ids:
                    resource = objects.ResourceDefinition()
                    resource.id = storage_resource.id
                    resource.type = constants.TYPE_STORAGE
                    resource.vdu_id = vnfc_resource.vdu_id
                    resource.resource_template_id = \
                        storage_resource.virtual_storage_desc_id
                    vim_id = \
                        storage_resource.storage_resource.vim_connection_id
                    rsc_id = storage_resource.storage_resource.resource_id
                    st_rh = objects.ResourceHandle(
                        vim_connection_id=vim_id,
                        resource_id=rsc_id)
                    resource.resource = st_rh
                    rm_resources.append(resource)

        grant_request = self._make_grant_request(context,
                                                 vnf_instance,
                                                 vnf_lcm_op_occ_id,
                                                 'TERMINATE',
                                                 False,
                                                 remove_resources=rm_resources)
        self._grant(context, grant_request)

    def _get_grant_execute(self):
        try:
            nfvo_client.GrantRequest().validate()
        except nfvo_client.UndefinedExternalSettingException:
            return False

        return True

    def _make_grant_request(self, context, vnf_instance,
                            vnf_lcm_op_occ_id, operation,
                            is_automatic_invocation,
                            add_resources=[],
                            remove_resources=[],
                            update_resources=[],
                            placement_constraints=[]):
        grant_request = objects.GrantRequest()
        grant_request.vnf_instance_id = vnf_instance.id
        grant_request.vnf_lcm_op_occ_id = vnf_lcm_op_occ_id
        grant_request.vnfd_id = vnf_instance.vnfd_id
        grant_request.flavour_id = \
            vnf_instance.instantiated_vnf_info.flavour_id
        grant_request.operation = operation
        grant_request.is_automatic_invocation = is_automatic_invocation
        vnflcm_url = CONF.vnf_lcm.endpoint_url + \
            "/vnflcm/v1/vnf_lcm_op_occs/" + vnf_lcm_op_occ_id
        insta_url = CONF.vnf_lcm.endpoint_url + \
            "/vnflcm/v1/vnf_instances/" + vnf_instance.id
        link_vnflcm = objects.Link(href=vnflcm_url)
        link_insta = objects.Link(href=insta_url)
        link = objects.Links(vnf_lcm_op_occ=link_vnflcm,
                             vnf_instance=link_insta)
        grant_request._links = link

        if add_resources:
            grant_request.add_resources = add_resources
        if remove_resources:
            grant_request.remove_resources = remove_resources
        if update_resources:
            grant_request.update_resources = update_resources
        if placement_constraints:
            grant_request.placement_constraints = placement_constraints

        return grant_request

    def _create_placement(self, context, vnf_dict):
        p_list = vnf_dict.get('placement_obj_list', [])
        if len(p_list) == 0:
            return
        self.vnfm_plugin.create_placement_constraint(context,
                                                     p_list)

    def _update_placement(self, context, vnf_dict, vnf_instance):
        self.vnfm_plugin.update_placement_constraint_heal(
            context, vnf_dict, vnf_instance)

    def _delete_placement(self, context, vnf_instance_id):
        self.vnfm_plugin.delete_placement_constraint(context,
                                                     vnf_instance_id)

    def _send_lcm_op_occ_notification(self, context, vnf_lcm_op_occs_id,
            old_vnf_instance, vnf_instance, operation, operation_state,
            **kwargs):

        is_automatic_invocation = \
            kwargs.get('is_automatic_invocation', False)
        error = kwargs.get('error', None)
        # Used for timing control when a failure occurs
        error_point = kwargs.get('error_point', 0)

        if old_vnf_instance:
            vnf_instance_id = old_vnf_instance.id
        else:
            vnf_instance_id = vnf_instance.id

        try:
            LOG.debug("Update vnf lcm %s %s",
                      vnf_lcm_op_occs_id,
                      operation_state)
            vnf_lcm_op_occ = objects.VnfLcmOpOcc.get_by_id(context,
                    vnf_lcm_op_occs_id)
            vnf_lcm_op_occ.operation_state = operation_state
            if operation_state == (
                    fields.LcmOccsOperationState.FAILED_TEMP
                    or operation_state == fields.LcmOccsOperationState.FAILED):
                vnf_lcm_op_occ.error_point = error_point
                error_details = objects.ProblemDetails(
                    context=context,
                    status=500,
                    detail=error
                )
                vnf_lcm_op_occ.error = error_details
            vnf_lcm_op_occ.save()
        except exceptions.VnfInstanceNotFound:
            error_msg = ("Can not find requested vnf instance: %s"
                         % vnf_instance_id)
            raise exceptions.NotificationProcessingError(error=error_msg)
        except sqlexc.SQLAlchemyError:
            error_msg = ("Can not find requested vnf instance: %s"
                         % vnf_instance_id)
            raise exceptions.NotificationProcessingError(error=error_msg)
        except Exception as ex:
            LOG.exception(ex)
            error_msg = ("Failed to update operation state of vnf instance %s"
                         % vnf_instance_id)
            raise exceptions.NotificationProcessingError(error=error_msg)

        # send notification
        try:
            notification_data = {
                'notificationType':
                    fields.LcmOccsNotificationType.VNF_OP_OCC_NOTIFICATION,
                'notificationStatus': fields.LcmOccsNotificationStatus.START,
                'operationState': operation_state,
                'vnfInstanceId': vnf_instance_id,
                'operation': operation,
                'isAutomaticInvocation': is_automatic_invocation,
                'vnfLcmOpOccId': vnf_lcm_op_occs_id,
                '_links': {
                    'vnfInstance': {
                        'href': self._get_vnf_instance_href(
                            vnf_instance_id)},
                    'vnfLcmOpOcc': {
                        'href': self._get_vnf_lcm_op_occs_href(
                            vnf_lcm_op_occs_id)}}}

            if(operation_state == fields.LcmOccsOperationState.COMPLETED or
               operation_state == fields.LcmOccsOperationState.FAILED_TEMP or
               operation_state == fields.LcmOccsOperationState.FAILED):
                affected_resources = vnflcm_utils._get_affected_resources(
                    old_vnf_instance=old_vnf_instance,
                    new_vnf_instance=vnf_instance)
                affected_resources_snake_case = \
                    utils.convert_camelcase_to_snakecase(affected_resources)
                resource_change_obj = \
                    jsonutils.dumps(affected_resources_snake_case)
                changed_resource = objects.ResourceChanges.obj_from_primitive(
                    resource_change_obj, context)
                changed_ext_connectivity = \
                    vnflcm_utils._get_changed_ext_connectivity(
                        old_vnf_instance=old_vnf_instance,
                        new_vnf_instance=vnf_instance)
                vnf_lcm_op_occ.resource_changes = changed_resource
                vnf_lcm_op_occ.changed_ext_connectivity = (
                    changed_ext_connectivity)
                vnf_lcm_op_occ.save()
                notification_data['affectedVnfcs'] = \
                    affected_resources.get('affectedVnfcs', [])
                notification_data['affectedVirtualLinks'] = \
                    affected_resources.get('affectedVirtualLinks', [])
                notification_data['affectedVirtualStorages'] = \
                    affected_resources.get('affectedVirtualStorages', [])
                notification_data['notificationStatus'] = \
                    fields.LcmOccsNotificationStatus.RESULT
                notification_data['changedExtConnectivity'] = \
                    utils.convert_snakecase_to_camelcase(
                        [i.to_dict() for i in changed_ext_connectivity])

                if operation_state == \
                        fields.LcmOccsOperationState.FAILED_TEMP \
                        or operation_state == \
                        fields.LcmOccsOperationState.FAILED:
                    notification_data['error'] = error

            # send notification
            self.send_notification(context, notification_data)
        except Exception as ex:
            LOG.error("Failed to send notification %s. Details: %s"
                      % (vnf_lcm_op_occs_id, str(ex)))

    def send_notification(self, context, notification):
        """Function to send notification to client

           This function is used to send notification
           to client during LCM Operation.

           :returns: 0 if status code of the response is 204
                    -1 if vnf_lcm_subscriptions is not found in the DB
                    -2 if an Internal Server Error occurs
        """

        try:
            LOG.debug("send_notification start notification[%s]"
                      % notification)

            notification = utils.convert_snakecase_to_camelcase(notification)

            if (notification.get('notificationType') ==
                    'VnfLcmOperationOccurrenceNotification'):
                vnf_lcm_subscriptions = \
                    objects.LccnSubscriptionRequest.vnf_lcm_subscriptions_get(
                        context,
                        operation_type=notification.get('operation'),
                        notification_type=notification.get('notificationType')
                    )
            else:
                vnf_lcm_subscriptions = \
                    objects.LccnSubscriptionRequest.vnf_lcm_subscriptions_get(
                        context,
                        notification_type=notification.get('notificationType')
                    )

            vnf_lcm_subscriptions = \
                self._extract_subscriptions(context, vnf_lcm_subscriptions,
                                            notification.get('vnfInstanceId'))

            if not vnf_lcm_subscriptions:
                LOG.warning(
                    "vnf_lcm_subscription not found id[%s]" %
                    notification.get('vnfInstanceId'))
                return -1

            notification['id'] = uuidutils.generate_uuid()

            # Notification shipping
            for line in vnf_lcm_subscriptions:
                notification['subscriptionId'] = line.id
                if (notification.get('notificationType') ==
                        'VnfLcmOperationOccurrenceNotification'):
                    notification['_links']['subscription'] = {}
                    notification['_links']['subscription']['href'] = \
                        CONF.vnf_lcm.endpoint_url + \
                        "/vnflcm/v1/subscriptions/" + line.id
                else:
                    notification['links']['subscription'] = {}
                    notification['links']['subscription']['href'] = \
                        CONF.vnf_lcm.endpoint_url + \
                        "/vnflcm/v1/subscriptions/" + line.id
                notification['timeStamp'] = datetime.datetime.utcnow(
                ).isoformat()
                try:
                    self.__set_auth_subscription(line)

                    for num in range(CONF.vnf_lcm.retry_num):
                        try:
                            LOG.info("send notify[%s]" %
                                json.dumps(notification))
                            auth_client = auth.auth_manager.get_auth_client(
                                notification['subscriptionId'])
                            response = auth_client.post(
                                line.callback_uri,
                                data=json.dumps(notification),
                                timeout=CONF.vnf_lcm.retry_timeout,
                                verify=CONF.vnf_lcm.verify_notification_ssl)
                            if response.status_code == 204:
                                LOG.info(
                                    "send success notify[%s]",
                                    json.dumps(notification))
                                break
                            else:
                                LOG.warning("Notification failed id[%s]"
                                    " status[%s] callback_uri[%s]",
                                    notification['id'], response.status_code,
                                    line.callback_uri)
                                LOG.debug("retry_wait %s",
                                    CONF.vnf_lcm.retry_wait)
                                self._retry_check(num)

                                continue
                        except requests.Timeout as e:
                            LOG.warning("Notification request timed out."
                                " id[%(id)s] callback_uri[%(uri)s]"
                                " reason[%(reason)s]", {
                                    "id": notification['id'],
                                    "uri": line.callback_uri,
                                    "reason": str(e)})
                            self._retry_check(num)
                except Exception as e:
                    LOG.warning("send error[%s]" % str(e))
                    LOG.warning(traceback.format_exc())
                    continue

        except Exception as e:
            LOG.warning("Internal Sever Error[%s]" % str(e))
            LOG.warning(traceback.format_exc())
            return -2
        return 0

    def _extract_subscriptions(self, context, vnf_lcm_subscriptions,
                               vnf_instance_id):

        extract_vnf_lcm_subscriptions = []

        try:
            vnf_instance = objects.VnfInstance.get_by_id(
                context, vnf_instance_id, read_deleted='yes')
        except exceptions.VnfInstanceNotFound:
            LOG.warning("Can not find vnf instance for notification: %s" % id)
            return []

        for subscription in vnf_lcm_subscriptions:
            if subscription.tenant_id == vnf_instance.get("tenant_id"):
                extract_vnf_lcm_subscriptions.append(subscription)

        return extract_vnf_lcm_subscriptions

    def _retry_check(self, retry_count):
        time.sleep(CONF.vnf_lcm.retry_wait)
        if retry_count == CONF.vnf_lcm.retry_num:
            LOG.warning(
                "Number of retries exceeded retry count [%s]" %
                CONF.vnf_lcm.retry_num)

    def test_notification(self, context, vnf_lcm_subscription=None):
        """Function to send test notification to client

           This function is used to send test notification
           to client during Register Subscription.

           :returns: 0 if status code of the response is 204
                    or if CONF.vnf_lcm.test_callback_uri is False,
                    -1 if status code of the response is not 204
        """

        if not CONF.vnf_lcm.test_callback_uri:
            LOG.warning("Callback URI is %s", CONF.vnf_lcm.test_callback_uri)
            return 0

        self.__set_auth_subscription(vnf_lcm_subscription)
        # Notification shipping
        for num in range(CONF.vnf_lcm.retry_num):
            try:
                auth_client = auth.auth_manager.get_auth_client(
                    vnf_lcm_subscription.id)

                notification = {}
                response = auth_client.get(
                    vnf_lcm_subscription.callback_uri,
                    data=json.dumps(notification),
                    timeout=CONF.vnf_lcm.retry_timeout,
                    verify=CONF.vnf_lcm.verify_notification_ssl)

                if response.status_code == 204:
                    return 0
                else:
                    LOG.warning(
                        "Notification failed status[%s] \
                            callback_uri[%s]" %
                        (response.status_code,
                        vnf_lcm_subscription.callback_uri))
                    LOG.debug(
                        "retry_wait %s" %
                        CONF.vnf_lcm.retry_wait)
                    self._retry_check(num)

                    continue
            except requests.Timeout as e:
                LOG.warning("Notification request timed out."
                    " callback_uri[%(uri)s]"
                    " reason[%(reason)s]", {
                        "uri": vnf_lcm_subscription.callback_uri,
                        "reason": str(e)})
                self._retry_check(num)

        # return -1 since the response is not 204
        return -1

    @coordination.synchronized('{vnf_instance[id]}')
    def instantiate(self, context, vnf_instance, vnf_dict, instantiate_vnf,
            vnf_lcm_op_occs_id):

        if vnf_dict['before_error_point'] == fields.ErrorPoint.INITIAL:
            self._instantiate_grant(context,
                vnf_instance,
                vnf_dict,
                instantiate_vnf,
                vnf_lcm_op_occs_id)

        try:
            # Update vnf_lcm_op_occs table and send notification "PROCESSING"
            self._send_lcm_op_occ_notification(
                context=context,
                vnf_lcm_op_occs_id=vnf_lcm_op_occs_id,
                old_vnf_instance=None,
                vnf_instance=vnf_instance,
                operation=fields.LcmOccsOperationType.INSTANTIATE,
                operation_state=fields.LcmOccsOperationState.PROCESSING)
            vnf_dict['current_error_point'] = EP.NOTIFY_PROCESSING

            if vnf_dict['status'] == 'ERROR':
                self._change_vnf_status(context, vnf_instance.id,
                                        constants.ERROR, 'PENDING_CREATE')
            elif vnf_dict['before_error_point'] <= EP.NOTIFY_PROCESSING:
                # change vnf_status
                if vnf_dict['status'] == 'INACTIVE':
                    vnf_dict['status'] = 'PENDING_CREATE'
                self._change_vnf_status(context, vnf_instance.id,
                        constants.INACTIVE, 'PENDING_CREATE')

            if vnf_dict['before_error_point'] <= EP.VNF_CONFIG_END:
                self.vnflcm_driver.instantiate_vnf(context, vnf_instance,
                        vnf_dict, instantiate_vnf)

                self._build_instantiated_vnf_info(context,
                            vnf_instance,
                            instantiate_vnf_req=instantiate_vnf)
                vim_id = instantiate_vnf.vim_connection_info[0].vim_id
                self._update_vnf_attributes(context, vnf_instance, vnf_dict,
                                            constants.PENDING_STATUSES,
                                            constants.ACTIVE, vim_id=vim_id)

            vnf_dict['current_error_point'] = EP.NOTIFY_COMPLETED

            self.vnflcm_driver._vnf_instance_update(context, vnf_instance,
                        instantiation_state=fields.VnfInstanceState.
                        INSTANTIATED, task_state=None)

            self._create_placement(context, vnf_dict)

            # Update vnf_lcm_op_occs table and send notification "COMPLETED"
            self._send_lcm_op_occ_notification(
                context=context,
                vnf_lcm_op_occs_id=vnf_lcm_op_occs_id,
                old_vnf_instance=None,
                vnf_instance=vnf_instance,
                operation=fields.LcmOccsOperationType.INSTANTIATE,
                operation_state=fields.LcmOccsOperationState.COMPLETED)

        except Exception as ex:
            self._change_vnf_status(context, vnf_instance.id,
                                    constants.ALL_STATUSES, 'ERROR')

            self._build_instantiated_vnf_info(context, vnf_instance,
                instantiate_vnf)
            self.vnflcm_driver._vnf_instance_update(context, vnf_instance,
                        task_state=None)

            # Update vnf_lcm_op_occs table and send notification "FAILED_TEMP"
            self._send_lcm_op_occ_notification(
                context=context,
                vnf_lcm_op_occs_id=vnf_lcm_op_occs_id,
                old_vnf_instance=None,
                vnf_instance=vnf_instance,
                operation=fields.LcmOccsOperationType.INSTANTIATE,
                operation_state=fields.LcmOccsOperationState.FAILED_TEMP,
                error=str(ex),
                error_point=vnf_dict['current_error_point']
            )

    @coordination.synchronized('{vnf_instance[id]}')
    def terminate(self, context, vnf_lcm_op_occs_id,
                  vnf_instance, terminate_vnf_req, vnf_dict):

        if vnf_dict['before_error_point'] == EP.INITIAL:
            self._terminate_grant(context,
                vnf_instance,
                vnf_lcm_op_occs_id)

        try:
            old_vnf_instance = copy.deepcopy(vnf_instance)

            # Update vnf_lcm_op_occs table and send notification "PROCESSING"
            self._send_lcm_op_occ_notification(
                context=context,
                vnf_lcm_op_occs_id=vnf_lcm_op_occs_id,
                old_vnf_instance=old_vnf_instance,
                vnf_instance=None,
                operation=fields.LcmOccsOperationType.TERMINATE,
                operation_state=fields.LcmOccsOperationState.PROCESSING)
            vnf_dict['current_error_point'] = EP.NOTIFY_PROCESSING

            if vnf_dict['status'] == 'ERROR':
                self._change_vnf_status(context, vnf_instance.id,
                                        constants.ERROR, 'PENDING_TERMINATE')
            elif vnf_dict['before_error_point'] <= EP.NOTIFY_PROCESSING:
                self._change_vnf_status(context, vnf_instance.id,
                                        constants.ACTIVE, 'PENDING_TERMINATE')

            if vnf_dict['before_error_point'] <= EP.VNF_CONFIG_END:
                self.vnflcm_driver.terminate_vnf(context, vnf_instance,
                                                 terminate_vnf_req, vnf_dict)

                self._delete_placement(context, vnf_instance.id)

                self._change_vnf_status(context, vnf_instance.id,
                                        constants.PENDING_STATUSES, 'INACTIVE')

            vnf_dict['current_error_point'] = EP.NOTIFY_COMPLETED

            self.vnflcm_driver._vnf_instance_update(context, vnf_instance,
                vim_connection_info=[], task_state=None,
                instantiation_state=fields.VnfInstanceState.NOT_INSTANTIATED)
            vnf_instance.instantiated_vnf_info.reinitialize()

            # Update vnf_lcm_op_occs table and send notification "COMPLETED"
            self._send_lcm_op_occ_notification(
                context=context,
                vnf_lcm_op_occs_id=vnf_lcm_op_occs_id,
                old_vnf_instance=old_vnf_instance,
                vnf_instance=None,
                operation=fields.LcmOccsOperationType.TERMINATE,
                operation_state=fields.LcmOccsOperationState.COMPLETED
            )

        except Exception as exc:
            # set vnf_status to error
            self._change_vnf_status(context, vnf_instance.id,
                                    constants.ALL_STATUSES, 'ERROR')

            self.vnflcm_driver._vnf_instance_update(
                context, vnf_instance, task_state=None)

            # Update vnf_lcm_op_occs table and send notification "FAILED_TEMP"
            self._send_lcm_op_occ_notification(
                context=context,
                vnf_lcm_op_occs_id=vnf_lcm_op_occs_id,
                old_vnf_instance=old_vnf_instance,
                vnf_instance=None,
                operation=fields.LcmOccsOperationType.TERMINATE,
                operation_state=fields.LcmOccsOperationState.FAILED_TEMP,
                error=str(exc),
                error_point=vnf_dict['current_error_point']
            )

    def _update_vnf_attributes_stack_param(self, context, vnf_dict, vnf_id,
                                           heal_vnf_request, inst_vnf_info):
        stack_param = vnflcm_utils.get_stack_param(
            context, vnf_dict, heal_vnf_request, inst_vnf_info)

        # update vnf_attribute in DB
        with context.session.begin(subtransactions=True):
            vnf_attr_model = (context.session.query(
                vnfm_db.VNFAttribute).
                filter_by(vnf_id=vnf_id).
                filter_by(key='stack_param').first())

            if vnf_attr_model:
                vnf_attr_model.update({'value': str(stack_param)})

    @coordination.synchronized('{vnf_instance[id]}')
    def heal(self, context, vnf_instance, vnf_dict, heal_vnf_request,
            vnf_lcm_op_occs_id):

        # call notification process
        if vnf_dict['before_error_point'] == EP.INITIAL:
            self._heal_grant(context, vnf_instance, vnf_dict, heal_vnf_request,
                             vnf_lcm_op_occs_id)

        try:
            old_vnf_instance = copy.deepcopy(vnf_instance)

            # Update vnf_lcm_op_occs table and send notification "PROCESSING"
            self._send_lcm_op_occ_notification(
                context=context,
                vnf_lcm_op_occs_id=vnf_lcm_op_occs_id,
                old_vnf_instance=old_vnf_instance,
                vnf_instance=vnf_instance,
                operation=fields.LcmOccsOperationType.HEAL,
                operation_state=fields.LcmOccsOperationState.PROCESSING)
            vnf_dict['current_error_point'] = EP.NOTIFY_PROCESSING

            if vnf_dict['status'] == 'ERROR':
                self._change_vnf_status(context, vnf_instance.id,
                                        constants.ERROR, 'PENDING_HEAL')
            elif vnf_dict['before_error_point'] <= EP.NOTIFY_PROCESSING:
                # update vnf status to PENDING_HEAL
                self._change_vnf_status(context, vnf_instance.id,
                                        constants.ACTIVE,
                                        constants.PENDING_HEAL)

            if vnf_dict['before_error_point'] <= EP.VNF_CONFIG_END:
                self.vnflcm_driver.heal_vnf(context, vnf_instance, vnf_dict,
                                            heal_vnf_request)

                self._update_instantiated_vnf_info(context, vnf_instance,
                                                   heal_vnf_request)

                # update stack_param in vnf_attribute table
                self._update_vnf_attributes_stack_param(
                    context, vnf_dict, vnf_instance.id, heal_vnf_request,
                    vnf_instance.instantiated_vnf_info)

                # update instance_in in vnf_table
                self._add_additional_vnf_info(context, vnf_instance)

                # update vnf status to ACTIVE
                self._change_vnf_status(context, vnf_instance.id,
                                        constants.PENDING_STATUSES,
                                        constants.ACTIVE)

            vnf_dict['current_error_point'] = EP.NOTIFY_COMPLETED

            # during .save() ,instantiated_vnf_info is also saved to DB
            self.vnflcm_driver._vnf_instance_update(context, vnf_instance,
                                                    task_state=None)

            self._update_placement(context, vnf_dict, vnf_instance)

            # update vnf_lcm_op_occs and send notification "COMPLETED"
            self._send_lcm_op_occ_notification(
                context=context,
                vnf_lcm_op_occs_id=vnf_lcm_op_occs_id,
                old_vnf_instance=old_vnf_instance,
                vnf_instance=vnf_instance,
                operation=fields.LcmOccsOperationType.HEAL,
                operation_state=fields.LcmOccsOperationState.COMPLETED
            )
        except Exception as ex:
            # update vnf_status to 'ERROR' and create event with 'ERROR' status
            self._change_vnf_status(context, vnf_instance.id,
                                    constants.ALL_STATUSES, constants.ERROR)

            # call _update_instantiated_vnf_info for notification
            self._update_instantiated_vnf_info(context, vnf_instance,
                                               heal_vnf_request)

            # update vnf_lcm_op_occs and send notification "FAILED_TEMP"
            self._send_lcm_op_occ_notification(
                context=context,
                vnf_lcm_op_occs_id=vnf_lcm_op_occs_id,
                old_vnf_instance=old_vnf_instance,
                vnf_instance=vnf_instance,
                operation=fields.LcmOccsOperationType.HEAL,
                operation_state=fields.LcmOccsOperationState.FAILED_TEMP,
                error=str(ex),
                error_point=vnf_dict['current_error_point']
            )

    @coordination.synchronized('{vnf_instance[id]}')
    def scale(self, context, vnf_info, vnf_instance, scale_vnf_request):
        vnf_lcm_op_occ = vnf_info['vnf_lcm_op_occ']
        vnf_lcm_op_occ_id = vnf_lcm_op_occ.id

        if vnf_info['before_error_point'] == EP.INITIAL:
            self._scale_grant(
                context,
                vnf_info,
                vnf_instance,
                scale_vnf_request,
                vnf_lcm_op_occ_id)

        if vnf_info['status'] == 'ERROR':
            self._change_vnf_status(context, vnf_instance.id,
                                    constants.ERROR,
                                    'PENDING_' + scale_vnf_request.type)

        self.vnflcm_driver.scale_vnf(
            context, vnf_info, vnf_instance, scale_vnf_request)

    def __set_auth_subscription(self, vnf_lcm_subscription):
        def decode(val):
            return val if isinstance(val, str) else val.decode()

        if not vnf_lcm_subscription:
            return

        # TODO(YiFeng) The type of vnf_lcm_subscription should be
        #  LegacyRow or LccnSubscriptionRequest,
        #  else should raise an exception

        if isinstance(vnf_lcm_subscription, LccnSubscriptionRequest):
            if ('authentication' not in vnf_lcm_subscription or
                    not vnf_lcm_subscription.authentication):
                return
        else:
            if (not hasattr(vnf_lcm_subscription, 'authentication') or
                    not vnf_lcm_subscription.authentication):
                return

        subscription_authentication = decode(
            vnf_lcm_subscription.authentication)

        authentication = utils.convert_camelcase_to_snakecase(
            json.loads(subscription_authentication))

        if not authentication:
            return

        auth_params = {}
        auth_type = None
        if 'params_basic' in authentication:
            auth_params = authentication.get('params_basic')
            auth_type = 'BASIC'
        elif 'params_oauth2_client_credentials' in authentication:
            auth_params = authentication.get(
                'params_oauth2_client_credentials')
            auth_type = 'OAUTH2_CLIENT_CREDENTIALS'
        else:
            # TODO(YiFeng) Other callers should handle the exception
            error = _('Unknown auth_type %s') % authentication['auth_type']
            raise exceptions.NotificationProcessingError(error)

        auth.auth_manager.set_auth_client(
            id=decode(vnf_lcm_subscription.id),
            auth_type=auth_type,
            auth_params=auth_params)

    @revert_update_lcm
    def update(
            self,
            context,
            vnf_lcm_opoccs,
            body_data,
            vnfd_pkg_data,
            vnfd_id):
        # input vnf_lcm_op_occs
        now = timeutils.utcnow()
        lcm_op_obj = objects.vnf_lcm_op_occs.VnfLcmOpOcc(context=context)
        lcm_op_obj.id = vnf_lcm_opoccs.get('id')
        lcm_op_obj.operation_state = fields.LcmOccsOperationState.PROCESSING
        lcm_op_obj.state_entered_time = vnf_lcm_opoccs.get(
            'state_entered_time')
        lcm_op_obj.start_time = now
        lcm_op_obj.vnf_instance_id = vnf_lcm_opoccs.get('vnf_instance_id')
        lcm_op_obj.operation = fields.InstanceOperation.MODIFY_INFO
        lcm_op_obj.is_automatic_invocation = 0
        lcm_op_obj.is_cancel_pending = 0
        lcm_op_obj.operation_params = vnf_lcm_opoccs.get('operationParams')
        lcm_op_obj.tenant_id = vnf_lcm_opoccs.get('tenant_id')

        try:
            lcm_op_obj.create()
        except Exception as msg:
            raise Exception(str(msg))

        # Notification
        instance_url = self._get_vnf_instance_href(
            vnf_lcm_opoccs.get('vnf_instance_id'))
        lcm_url = self._get_vnf_lcm_op_occs_href(vnf_lcm_opoccs.get('id'))

        notification_data = {
            'notificationType':
                fields.LcmOccsNotificationType.VNF_OP_OCC_NOTIFICATION,
            'notificationStatus': fields.LcmOccsNotificationStatus.START,
            'operationState': fields.LcmOccsOperationState.PROCESSING,
            'vnfInstanceId': vnf_lcm_opoccs.get('vnf_instance_id'),
            'operation': fields.InstanceOperation.MODIFY_INFO,
            'isAutomaticInvocation': False,
            'vnfLcmOpOccId': vnf_lcm_opoccs.get('id'),
            '_links': {
                'vnfInstance': {
                    'href': instance_url},
                'vnfLcmOpOcc': {
                    'href': lcm_url}}}

        self.send_notification(context, notification_data)

        # update vnf_instance
        state_entered_time = self.vnflcm_driver.modify_vnf(
            context, vnf_lcm_opoccs, body_data, vnfd_pkg_data, vnfd_id)

        # update lcm_op_occs
        if vnfd_pkg_data and len(vnfd_pkg_data) > 0:
            changed_info = \
                objects.vnf_lcm_op_occs.VnfInfoModifications._from_dict(
                    vnfd_pkg_data)
        else:
            changed_info = objects.vnf_lcm_op_occs.VnfInfoModifications()
        if body_data.get('vnf_instance_name'):
            changed_info.vnf_instance_name = body_data.get('vnf_instance_name')
        if body_data.get('vnf_instance_description'):
            changed_info.vnf_instance_description = body_data.get(
                'vnf_instance_description')

        # update vnf_lcm_op_occs
        now = timeutils.utcnow()
        lcm_op_obj.id = vnf_lcm_opoccs.get('id')
        lcm_op_obj.operation_state = fields.LcmOccsOperationState.COMPLETED
        lcm_op_obj.state_entered_time = state_entered_time
        lcm_op_obj.updated_at = now
        lcm_op_obj.changed_info = changed_info

        try:
            lcm_op_obj.save()
        except Exception as msg:
            raise Exception(str(msg))

        # Notification
        notification_data['notificationStatus'] = 'RESULT'
        notification_data['operationState'] = 'COMPLETED'
        notification_data['changed_info'] = changed_info.to_dict()
        self.send_notification(context, notification_data)

    @coordination.synchronized('{vnf_instance[id]}')
    def rollback(self, context, vnf_info, vnf_instance, operation_params):
        self.vnflcm_driver.rollback_vnf(context, vnf_info,
            vnf_instance, operation_params)

    @coordination.synchronized('{vnf_instance[id]}')
    def change_ext_conn(
            self,
            context,
            vnf_instance,
            vnf_dict,
            change_ext_conn_req,
            vnf_lcm_op_occs_id):
        """Perform change external VNF connectivity operation.

        This function will support changing external VNF connectivity
        as defined in ETSI NFV SOL 002 and SOL 003, but now, you can
        specify changing fixedAddresses or numDynamicAddresses in
        ipAddresses attribute in extVirtualLinks.

        Note:
            1. Get grant from NFVO(if needed).
                Request grant information is made from ExtVirtualLinkData
                of ChangeExtConnRequest. If ExtVirtualLinkInfo is changed
                from instantiated VNF, we inform VnfLinkPortInfo related
                to that ExtVirtualLinkInfo. Also, we inform VnfLinkPortInfo
                related to each individual VnfExtCpInfo.
            2. Call vnflcm_driver to change networks.
                Invoke vnflcm_driver to perform change external VNF
                connectivity.
            3. Update VNF information
                Update InstantiatedVnfInfo as a post-processing.

        Args:
            context (Context): context for security/db session.
            vnf_instance (VnfInstance): Information object for VNF instance.
            vnf_dict (dict): Container for error point indication.
            change_ext_conn_req (ChangeExtConnRequest):
            Request object of change external connectivity.
            vnf_lcm_op_occs_id (uuid): self-explanatory :)
        """
        if vnf_dict['before_error_point'] == EP.INITIAL:
            self._change_ext_conn_grant(
                context,
                vnf_instance,
                change_ext_conn_req,
                vnf_lcm_op_occs_id)

        try:
            old_vnf_instance = copy.deepcopy(vnf_instance)
            # Update vnf_lcm_op_occs table and send notification "PROCESSING"
            self._send_lcm_op_occ_notification(
                context=context,
                vnf_lcm_op_occs_id=vnf_lcm_op_occs_id,
                old_vnf_instance=None,
                vnf_instance=vnf_instance,
                operation=fields.LcmOccsOperationType.CHANGE_EXT_CONN,
                operation_state=fields.LcmOccsOperationState.PROCESSING)

            vnf_dict['current_error_point'] = EP.NOTIFY_PROCESSING

            if vnf_dict['status'] == 'ERROR':
                self._change_vnf_status(context, vnf_instance.id,
                                        constants.ERROR,
                                        'PENDING_CHANGE_EXT_CONN')
            elif vnf_dict['before_error_point'] <= EP.NOTIFY_PROCESSING:
                # update vnf status to PENDING_CHANGE_EXT_CONN
                self._change_vnf_status(context, vnf_instance.id,
                                        constants.ACTIVE,
                                        'PENDING_CHANGE_EXT_CONN')

            self.vnflcm_driver.change_ext_conn_vnf(
                context,
                vnf_instance,
                vnf_dict,
                change_ext_conn_req)

            vnf_dict['current_error_point'] = EP.NOTIFY_COMPLETED
            self._update_instantiated_vnf_info_change_ext_conn(
                context, vnf_instance, change_ext_conn_req)
            # update vnf status to ACTIVE
            self._update_vnf_attributes(context, vnf_instance, vnf_dict,
                                        constants.PENDING_STATUSES,
                                        constants.ACTIVE)
            # Update vnf_lcm_op_occs table and send notification "COMPLETED"
            self._send_lcm_op_occ_notification(
                context=context,
                vnf_lcm_op_occs_id=vnf_lcm_op_occs_id,
                old_vnf_instance=old_vnf_instance,
                vnf_instance=vnf_instance,
                operation=fields.LcmOccsOperationType.CHANGE_EXT_CONN,
                operation_state=fields.LcmOccsOperationState.COMPLETED
            )
        except Exception as e:
            # update vnf_status to 'ERROR' and create event with 'ERROR' status
            self._change_vnf_status(context, vnf_instance.id,
                                    constants.ALL_STATUSES, constants.ERROR)

            LOG.error('Failed to execute operation. error={}'.format(e))
            if vnf_dict['current_error_point'] in [EP.INTERNAL_PROCESSING,
                    EP.VNF_CONFIG_END]:
                self._update_instantiated_vnf_info_change_ext_conn(
                    context, vnf_instance, change_ext_conn_req)

            # update vnf_lcm_op_occs and send notification "FAILED_TEMP"
            self._send_lcm_op_occ_notification(
                context=context,
                vnf_lcm_op_occs_id=vnf_lcm_op_occs_id,
                old_vnf_instance=old_vnf_instance,
                vnf_instance=vnf_instance,
                operation=fields.LcmOccsOperationType.CHANGE_EXT_CONN,
                operation_state=fields.LcmOccsOperationState.FAILED_TEMP,
                error=str(e),
                error_point=vnf_dict['current_error_point']
            )


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
    sol_objects.register_all()
    logging.setup(CONF, "tacker")
    oslo_messaging.set_transport_defaults(control_exchange='tacker')
    logging.setup(CONF, "tacker")
    CONF.log_opt_values(LOG, logging.DEBUG)
    server = tacker_service.Service.create(
        binary='tacker-conductor',
        topic=topics.TOPIC_CONDUCTOR,
        manager=manager)
    service.launch(CONF, server, restart_method='mutate').wait()
