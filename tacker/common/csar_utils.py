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
from copy import deepcopy
import hashlib
import os
import re
import shutil

import yaml

from oslo_log import log as logging
from oslo_utils import encodeutils
from oslo_utils import excutils
from six.moves.urllib.parse import urlparse
from toscaparser.prereq.csar import CSAR
from toscaparser.tosca_template import ToscaTemplate
import zipfile

from tacker.common import exceptions
import tacker.conf
from tacker.extensions import vnfm
import urllib.request as urllib2


HASH_DICT = {
    'sha-224': hashlib.sha224,
    'sha-256': hashlib.sha256,
    'sha-384': hashlib.sha384,
    'sha-512': hashlib.sha512
}
CONF = tacker.conf.CONF
LOG = logging.getLogger(__name__)
TOSCA_META = 'TOSCA-Metadata/TOSCA.meta'
ARTIFACT_KEYS = ['Source', 'Algorithm', 'Hash']
IMAGE_FORMAT_LIST = ['raw', 'vhd', 'vhdx', 'vmdk', 'vdi', 'iso', 'ploop',
                   'qcow2', 'aki', 'ari', 'ami', 'img']


def _check_type(custom_def, node_type, type_list):
    for node_data_type, node_data_type_value in custom_def.items():
        if node_data_type == node_type and node_type in type_list:
            return True, node_data_type_value
        for k, v in node_data_type_value.items():
            if k == 'derived_from':
                if v in type_list and node_type == node_data_type:
                    return True, node_data_type_value
    return False, None


def _get_sw_image_artifact(artifacts):
    if not artifacts:
        return

    for artifact_value in artifacts.values():
        if isinstance(artifact_value, dict):
            if artifact_value.get('type') == 'tosca.artifacts.nfv.SwImage':
                return artifact_value
        elif isinstance(artifact_value, str):
            return {'file': artifact_value}


def _update_default_vnfd_data(node_value, node_type_value):
    vnf_properties = node_value['properties']
    type_properties = node_type_value['properties']
    for property_key, property_value in type_properties.items():
        if property_key == 'descriptor_id':
            # if descriptor_id is parameterized, then get the value from the
            # default property and set it in the vnf_properties.
            if vnf_properties and isinstance(
                    vnf_properties.get('descriptor_id'), dict):
                vnf_properties['descriptor_id'] = property_value.get("default")
    return vnf_properties


def _get_vnf_data(nodetemplates):
    type_list = ['tosca.nodes.nfv.VNF']
    for nt in nodetemplates:
        for node_name, node_value in nt.templates.items():
            type_status, node_type_value = _check_type(nt.custom_def,
                                            node_value['type'], type_list)
            if type_status and node_type_value:
                return _update_default_vnfd_data(node_value, node_type_value)


def _get_instantiation_levels(policies):
    if policies:
        for policy in policies:
            if policy.type_definition.type == \
                    'tosca.policies.nfv.InstantiationLevels':
                return policy.properties


def _update_flavour_data_from_vnf(custom_defs, node_tpl, flavour):
    type_list = ['tosca.nodes.nfv.VNF']

    type_status, _ = _check_type(custom_defs, node_tpl['type'], type_list)
    if type_status and node_tpl['properties']:
        vnf_properties = node_tpl['properties']
        if 'flavour_description' in vnf_properties:
            flavour.update(
                {'flavour_description': vnf_properties[
                    'flavour_description']})

        if 'flavour_id' in vnf_properties and isinstance(
                vnf_properties['flavour_id'], str):
            flavour.update({'flavour_id': vnf_properties['flavour_id']})


def _get_software_image(custom_defs, nodetemplate_name, node_tpl):
    type_list = ['tosca.nodes.nfv.Vdu.Compute',
                 'tosca.nodes.nfv.Vdu.VirtualBlockStorage']
    type_status, _ = _check_type(custom_defs, node_tpl['type'], type_list)
    if type_status:
        properties = node_tpl['properties']
        sw_image_artifact = _get_sw_image_artifact(node_tpl.get('artifacts'))
        if sw_image_artifact:
            image_path = sw_image_artifact['file'].lstrip("./")
            properties['sw_image_data'].update(
                {'software_image_id': nodetemplate_name,
                'image_path': image_path})
            sw_image_data = properties['sw_image_data']
            if 'metadata' in sw_image_artifact:
                sw_image_data.update({'metadata':
                    sw_image_artifact['metadata']})
            return sw_image_data


def _populate_flavour_data(tosca):
    flavours = []
    if tosca.nested_tosca_templates_with_topology:
        for tp in tosca.nested_tosca_templates_with_topology:
            sw_image_list = []

            # Setting up flavour data
            flavour_id = tp.substitution_mappings.properties.get('flavour_id')
            if flavour_id:
                flavour = {'flavour_id': flavour_id}
                tpl_dict = dict()

                # get from top-vnfd data
                for key, value in tosca.tpl.items():
                    if key in CONF.vnf_package.get_top_list:
                        tpl_dict[key] = value

                # get from lower-vnfd data
                tpl_dict['topology_template'] = dict()
                tpl_dict['topology_template']['policies'] = \
                    tp.tpl.get('policies')
                tpl_dict['topology_template']['node_templates'] = \
                    deepcopy(tp.tpl.get('node_templates'))
                for e_node in CONF.vnf_package.exclude_node:
                    if tpl_dict['topology_template']['node_templates'].\
                            get(e_node):
                        del (tpl_dict['topology_template']
                            ['node_templates'][e_node])
                tpl_dict['topology_template']['inputs'] = \
                    deepcopy(tp.tpl.get('inputs'))
                for del_input in CONF.vnf_package.del_input_list:
                    if tpl_dict['topology_template']['inputs'].get(del_input):
                        del tpl_dict['topology_template']['inputs'][del_input]
                if len(tpl_dict['topology_template']['inputs']) < 1:
                    del tpl_dict['topology_template']['inputs']

                flavour.update({'tpl_dict': tpl_dict})

                instantiation_levels = _get_instantiation_levels(tp.policies)
                if instantiation_levels:
                    flavour.update(
                        {'instantiation_levels': instantiation_levels})

                mgmt_driver = None
                for template_name, node_tpl in \
                        tp.tpl.get('node_templates').items():
                    # check the flavour property in vnf data
                    _update_flavour_data_from_vnf(
                        tp.custom_defs, node_tpl, flavour)
                    if node_tpl['type'] in CONF.vnf_package.get_lower_list:
                        if node_tpl['type'] == "tosca.nodes.nfv.VDU.Tacker":
                            # get mgmt_driver
                            mgmt_driver_flavour = \
                                node_tpl['properties'].get('mgmt_driver')
                            if mgmt_driver_flavour:
                                if mgmt_driver and \
                                        mgmt_driver_flavour != mgmt_driver:
                                    raise vnfm.MultipleMGMTDriversSpecified()
                                mgmt_driver = mgmt_driver_flavour
                                flavour.update({'mgmt_driver': mgmt_driver})

                for template_name, node_tpl in \
                        tp.tpl.get('node_templates').items():
                    # Update the software image data
                    sw_image = _get_software_image(tp.custom_defs,
                                                   template_name,
                                                   node_tpl)
                    if sw_image:
                        sw_image_list.append(sw_image)

                # Add software images for flavour
                if sw_image_list:
                    flavour.update({'sw_images': sw_image_list})

                if flavour:
                    flavours.append(flavour)

    else:
        _get_flavour_data(tosca.topology_template, flavours)

    return flavours


def _get_flavour_data(tp, flavours):
    sw_image_list = []

    # Setting up flavour data
    flavour_id = tp.substitution_mappings.properties.get('flavour_id')
    if flavour_id:
        if isinstance(flavour_id, dict):
            error_msg = "flavour_id should be string and given" \
                        " {}".format(flavour_id)
            raise exceptions.InvalidCSAR(error_msg)
        flavour = {'flavour_id': flavour_id}
    else:
        flavour = {}
    instantiation_levels = _get_instantiation_levels(tp.policies)
    if instantiation_levels:
        flavour.update({'instantiation_levels': instantiation_levels})
    for template_name, node_tpl in tp.tpl.get('node_templates').items():
        # check the flavour property in vnf data
        _update_flavour_data_from_vnf(tp.custom_defs, node_tpl, flavour)

        # Update the software image data
        sw_image = _get_software_image(tp.custom_defs, template_name,
                                       node_tpl)
        if sw_image:
            sw_image_list.append(sw_image)

    # Add software images for flavour
    if sw_image_list:
        flavour.update({'sw_images': sw_image_list})

    if flavour:
        flavours.append(flavour)


def _get_instantiation_levels_from_policy(tpl_policies):
    """Get defined instantiation levels

    Getting instantiation levels defined under policy type
    'tosca.policies.nfv.InstantiationLevels'.
    """

    levels = []
    for policy in tpl_policies:
        for key, value in policy.items():
            if value.get('type') == 'tosca.policies.nfv.InstantiationLevels'\
                    and value.get('properties', {}).get('levels', {}):
                levels = value.get('properties').get('levels').keys()
                default_level = value.get(
                    'properties').get('default_level')

                if default_level and default_level not in levels:
                    error_msg = "Level {} not found in defined levels" \
                                " {}".format(default_level,
                                             ",".join(sorted(levels)))
                    raise exceptions.InvalidCSAR(error_msg)
    return levels


def _validate_instantiation_levels(policy, instantiation_levels):
    expected_policy_type = ['tosca.policies.nfv.VduInstantiationLevels',
                            'tosca.policies.nfv.'
                            'VirtualLinkInstantiationLevels']
    for policy_name, policy_tpl in policy.items():
        if policy_tpl.get('type') not in expected_policy_type:
            return

        if not instantiation_levels:
            msg = ('Policy of type'
                   ' "tosca.policies.nfv.InstantiationLevels is not defined.')
            raise exceptions.InvalidCSAR(msg)
        if policy_tpl.get('properties'):
            levels_in_policy = policy_tpl.get(
                'properties').get('levels')

            if levels_in_policy:
                invalid_levels = set(levels_in_policy.keys()) - set(
                    instantiation_levels)
            else:
                invalid_levels = set()

            if invalid_levels:
                error_msg = "Level(s) {} not found in defined levels" \
                            " {}".format(",".join(sorted(invalid_levels)),
                                         ",".join(sorted(instantiation_levels)
                                                  ))
                raise exceptions.InvalidCSAR(error_msg)


def _validate_sw_image_data_for_artifact(node_tpl, template_name):
    artifact_names = []
    artifacts = node_tpl.get('artifacts')
    if not artifacts:
        return

    for key, value in artifacts.items():
        if isinstance(value, dict):
            if value.get('type') == 'tosca.artifacts.nfv.SwImage':
                artifact_names.append(key)
        elif isinstance(value, str):
            artifact_names.append(key)

    if len(artifact_names) > 1:
        error_msg = ('artifacts of type "tosca.artifacts.nfv.SwImage"'
                     ' is added more than one time for'
                     ' node %(node)s.') % {'node': template_name}
        raise exceptions.InvalidCSAR(error_msg)

    if artifact_names and node_tpl.get('properties'):
        if not node_tpl.get('properties').get('sw_image_data'):
            error_msg = ('Node property "sw_image_data" is missing for'
                         ' artifact %(artifact_name)s for node %(node)s.') % {
                'artifact_name': artifact_names[0], 'node': template_name}
            raise exceptions.InvalidCSAR(error_msg)


def _validate_sw_image_data_for_artifacts(tosca):
    for tp in tosca.nested_tosca_templates_with_topology:
        for template_name, node_tpl in tp.tpl.get('node_templates').items():
            _validate_sw_image_data_for_artifact(node_tpl, template_name)

    for template in tosca.nodetemplates:
        _validate_sw_image_data_for_artifact(
            template.entity_tpl, template.name)


def _get_data_from_csar(tosca, context, id):
    for tp in tosca.nested_tosca_templates_with_topology:
        policies = tp.tpl.get("policies")
        if policies:
            levels = _get_instantiation_levels_from_policy(policies)
            for policy_tpl in policies:
                _validate_instantiation_levels(policy_tpl, levels)

    _validate_sw_image_data_for_artifacts(tosca)
    vnf_data = _get_vnf_data(tosca.nodetemplates)
    if not vnf_data:
        error_msg = "VNF properties are mandatory"
        raise exceptions.InvalidCSAR(error_msg)

    flavours = _populate_flavour_data(tosca)
    if not flavours:
        error_msg = "No VNF flavours are available"
        raise exceptions.InvalidCSAR(error_msg)

    csar = CSAR(tosca.input_path, tosca.a_file)
    vnf_artifacts = []
    if csar.validate():
        vnf_artifacts = _get_vnf_artifacts(csar)

    return vnf_data, flavours, vnf_artifacts


def _get_vnf_artifacts(csar):
    vnf_artifacts = []
    if csar.is_tosca_metadata:
        if csar._get_metadata("ETSI-Entry-Manifest"):
            manifest_path = csar._get_metadata("ETSI-Entry-Manifest")
            if manifest_path.lower().endswith(".mf"):
                manifest_data = csar.zfile.read(manifest_path)
                vnf_artifacts = _convert_artifacts(
                    vnf_artifacts, manifest_data, csar)
            else:
                invalid_manifest_err_msg = (
                    ('The file "%(manifest)s" in the CSAR "%(csar)s" does not '
                     'contain valid manifest.') %
                    {'manifest': manifest_path, 'csar': csar.path})
                raise exceptions.InvalidCSAR(invalid_manifest_err_msg)
        tosca_data = csar.zfile.read(TOSCA_META)
        vnf_artifacts = _convert_artifacts(vnf_artifacts, tosca_data, csar)

    else:
        filelist = csar.zfile.namelist()
        main_template_file_name = os.path.splitext(
            csar.main_template_file_name)[0]
        for path in filelist:
            if path.lower().endswith(".mf"):
                manifest_file_name = os.path.splitext(path)[0]
                if manifest_file_name == main_template_file_name:
                    manifest_data = csar.zfile.read(path)
                    vnf_artifacts = _convert_artifacts(
                        vnf_artifacts, manifest_data, csar)
                else:
                    invalid_manifest_err_msg = \
                        (('The filename "%(manifest)s" is an invalid name.'
                          'The name must be the same as the main template '
                          'file name.') %
                        {'manifest': path})
                    raise exceptions.InvalidCSAR(invalid_manifest_err_msg)
    # Deduplication
    vnf_artifacts = [dict(t) for t in set([tuple(d.items())
                          for d in vnf_artifacts])]
    return vnf_artifacts


def _convert_artifacts(vnf_artifacts, artifacts_data, csar):
    artifacts_data_split = re.split(b'\n\n+', artifacts_data)

    for data in artifacts_data_split:
        if re.findall(b'.?Name:.?|.?Source:.?|', data):
            # validate key's existence
            if re.findall(b'.?Algorithm:.?|.?Hash:.?', data):
                artifact_data_dict = yaml.safe_load(data)
                if 'Name' in artifact_data_dict.keys():
                    artifact_data_dict.update(
                        {"Source": artifact_data_dict.pop("Name")})
                if 'Content-Type' in artifact_data_dict.keys():
                    del artifact_data_dict['Content-Type']
                if sorted(ARTIFACT_KEYS) != sorted(artifact_data_dict.keys()):
                    missing_key = list(set(ARTIFACT_KEYS) ^
                                       set(artifact_data_dict.keys()))
                    missing_key = sorted(missing_key)
                    invalid_artifact_err_msg = \
                        (('One of the artifact information '
                          'may not have the key("%(key)s")') %
                         {'key': missing_key})
                    raise exceptions.InvalidCSAR(invalid_artifact_err_msg)
                # validate value's existence
                for key, value in artifact_data_dict.items():
                    if not value:
                        invalid_artifact_err_msg = \
                            (('One of the artifact information may not have '
                              'the key value("%(key)s")') % {'key': key})
                        raise exceptions.InvalidCSAR(invalid_artifact_err_msg)
                artifact_path = artifact_data_dict.get('Source')
                if os.path.splitext(artifact_path)[-1][1:] \
                        in IMAGE_FORMAT_LIST:
                    continue
                else:
                    algorithm = artifact_data_dict.get('Algorithm')
                    hash_code = artifact_data_dict.get('Hash')
                    result = _validate_hash(algorithm, hash_code,
                                            csar, artifact_path)
                    if result:
                        vnf_artifacts.append(artifact_data_dict)
                    else:
                        invalid_artifact_err_msg = \
                            (('The hash "%(hash)s" of artifact file '
                              '"%(artifact)s" is an invalid value.') %
                             {'hash': hash_code, 'artifact': artifact_path})
                        raise exceptions.InvalidCSAR(invalid_artifact_err_msg)

    return vnf_artifacts


def _validate_hash(algorithm, hash_code, csar, artifact_path):
    z = zipfile.ZipFile(csar.path)
    algorithm = algorithm.lower()

    # validate Algorithm's value
    if algorithm in HASH_DICT.keys():
        hash_obj = HASH_DICT[algorithm]()
    else:
        invalid_artifact_err_msg = (('The algorithm("%(algorithm)s") of '
                                     'artifact("%(artifact_path)s") is '
                                     'an invalid value.') %
                                    {'algorithm': algorithm,
                                     'artifact_path': artifact_path})
        raise exceptions.InvalidCSAR(invalid_artifact_err_msg)
    filelist = csar.zfile.namelist()

    # validate Source's value
    if artifact_path in filelist:
        hash_obj.update(z.read(artifact_path))
    elif ((urlparse(artifact_path).scheme == 'file') or
          (bool(urlparse(artifact_path).scheme) and
           bool(urlparse(artifact_path).netloc))):
        hash_obj.update(urllib2.urlopen(artifact_path).read())
    else:
        invalid_artifact_err_msg = (('The path("%(artifact_path)s") of '
                                     'artifact Source is an invalid value.') %
                                    {'artifact_path': artifact_path})
        raise exceptions.InvalidCSAR(invalid_artifact_err_msg)

    # validate Hash's value
    if hash_code == hash_obj.hexdigest():
        return True
    else:
        return False


def extract_csar_zip_file(file_path, extract_path):
    try:
        with zipfile.ZipFile(file_path, 'r') as zf:
            zf.extractall(extract_path)
    except (RuntimeError, zipfile.BadZipfile) as exp:
        with excutils.save_and_reraise_exception():
            LOG.error("Error encountered while extracting "
                      "csar zip file %(path)s. Error: %(error)s.",
                      {'path': file_path,
                      'error': encodeutils.exception_to_unicode(exp)})
            exp.reraise = False
            raise exceptions.InvalidZipFile(path=file_path)


def load_csar_data(context, package_uuid, zip_path):

    extract_zip_path = os.path.join(CONF.vnf_package.vnf_package_csar_path,
                                    package_uuid)
    extract_csar_zip_file(zip_path, extract_zip_path)

    try:
        tosca = ToscaTemplate(zip_path, None, True)
        return _get_data_from_csar(tosca, context, package_uuid)
    except exceptions.InvalidCSAR as exp:
        with excutils.save_and_reraise_exception():
            LOG.error("Error processing CSAR file %(path)s for vnf package"
                      " %(uuid)s: Error: %(error)s. ",
                      {'path': zip_path, 'uuid': package_uuid,
                    'error': encodeutils.exception_to_unicode(exp)})
    except Exception as exp:
        with excutils.save_and_reraise_exception():
            LOG.error("Tosca parser failed for vnf package %(uuid)s: "
                      "Error: %(error)s. ", {'uuid': package_uuid,
                      'error': encodeutils.exception_to_unicode(exp)})
            exp.reraise = False
            raise exceptions.InvalidCSAR(encodeutils.exception_to_unicode
                                         (exp))


def delete_csar_data(package_uuid):
    # Remove zip and folder from the vnf_package_csar_path
    csar_zip_temp_path = os.path.join(CONF.vnf_package.vnf_package_csar_path,
                                      package_uuid)
    csar_path = os.path.join(CONF.vnf_package.vnf_package_csar_path,
                 package_uuid + ".zip")

    try:
        shutil.rmtree(csar_zip_temp_path)
        os.remove(csar_path)
    except OSError as exc:
        exc_message = encodeutils.exception_to_unicode(exc)
        msg = _('Failed to delete csar folder: '
                '%(csar_path)s, Error: %(exc)s')
        LOG.warning(msg, {'csar_path': csar_path, 'exc': exc_message})
