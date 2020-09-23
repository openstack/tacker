# Copyright (c) 2019 NTT DATA.
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

import os
import shutil
import tempfile
import testtools
from unittest import mock
import uuid
import zipfile

from tacker.common import csar_utils
from tacker.common import exceptions
from tacker import context
from tacker.tests import constants
from tacker.tests import utils


class TestCSARUtils(testtools.TestCase):

    def setUp(self):
        super(TestCSARUtils, self).setUp()
        self.context = context.get_admin_context()

    @mock.patch('tacker.common.csar_utils.extract_csar_zip_file')
    def test_load_csar_data(self, mock_extract_csar_zip_file):
        file_path, _ = utils.create_csar_with_unique_vnfd_id(
            './tacker/tests/etc/samples/etsi/nfv/'
            'sample_vnfpkg_tosca_vnfd')
        self.addCleanup(os.remove, file_path)
        vnf_data, flavours, vnf_artifacts = csar_utils.load_csar_data(
            self.context, constants.UUID, file_path)
        self.assertEqual(vnf_data['descriptor_version'], '1.0')
        self.assertEqual(vnf_data['vnfm_info'], ['Tacker'])
        self.assertEqual(flavours[0]['flavour_id'], 'simple')
        self.assertIsNotNone(flavours[0]['sw_images'])

    @mock.patch('tacker.common.csar_utils.extract_csar_zip_file')
    def test_load_csar_data_with_single_yaml(
            self, mock_extract_csar_zip_file):
        file_path, _ = utils.create_csar_with_unique_vnfd_id(
            './tacker/tests/etc/samples/etsi/nfv/'
            'sample_vnfpkg_no_meta_single_vnfd')
        self.addCleanup(os.remove, file_path)
        vnf_data, flavours, vnf_artifacts = csar_utils.load_csar_data(
            self.context, constants.UUID, file_path)
        self.assertEqual(vnf_data['descriptor_version'], '1.0')
        self.assertEqual(vnf_data['vnfm_info'], ['Tacker'])
        self.assertEqual(flavours[0]['flavour_id'], 'simple')
        self.assertIsNotNone(flavours[0]['sw_images'])

    def _get_csar_zip_from_dir(self, dir_name):
        csar_dir_path = os.path.join('test_csar_utils_data', dir_name)
        unique_name = str(uuid.uuid4())
        csar_temp_dir = os.path.join('/tmp', unique_name)
        self.addCleanup(shutil.rmtree, csar_temp_dir)
        utils.copy_csar_files(csar_temp_dir, csar_dir_path)
        # Copy contents from 'test_csar_utils_common' to 'csar_temp_dir'.
        common_dir_path = ('./tacker/tests/etc/samples/etsi/nfv/'
                           'test_csar_utils_data/test_csar_utils_common')
        common_yaml_file = os.path.join(common_dir_path,
                                        'Definitions/helloworld3_types.yaml')
        shutil.copy(common_yaml_file,
                    os.path.join(csar_temp_dir, 'Definitions/'))

        shutil.copytree(os.path.join(common_dir_path, "TOSCA-Metadata/"),
                        os.path.join(csar_temp_dir, "TOSCA-Metadata/"))
        # Create temporary zip file from 'csar_temp_dir'
        tempfd, tempname = tempfile.mkstemp(suffix=".zip", dir=csar_temp_dir)
        os.close(tempfd)
        zcsar = zipfile.ZipFile(tempname, 'w')

        for (dpath, _, fnames) in os.walk(csar_temp_dir):
            for fname in fnames:
                src_file = os.path.join(dpath, fname)
                dst_file = os.path.relpath(os.path.join(dpath, fname),
                                           csar_temp_dir)
                zcsar.write(src_file, dst_file)
        zcsar.close()
        return tempname

    @mock.patch('tacker.common.csar_utils.extract_csar_zip_file')
    def test_load_csar_data_in_meta_and_manifest_with_vnf_artifact(
            self, mock_extract_csar_zip_file):
        file_path = utils.create_csar_with_unique_artifact(
            './tacker/tests/etc/samples/etsi/nfv/'
            'sample_vnf_package_csar_in_meta_and_manifest')
        self.addCleanup(os.remove, file_path)
        vnf_data, flavours, vnf_artifacts = csar_utils.load_csar_data(
            self.context, constants.UUID, file_path)
        self.assertEqual(vnf_data['descriptor_version'], '1.0')
        self.assertEqual(vnf_data['vnfm_info'], ['Tacker'])
        self.assertEqual(flavours[0]['flavour_id'], 'simple')
        self.assertIsNotNone(flavours[0]['sw_images'])
        self.assertIsNotNone(vnf_artifacts)
        self.assertIsNotNone(vnf_artifacts[0]['Source'])
        self.assertIsNotNone(vnf_artifacts[0]['Hash'])
        for item in vnf_artifacts:
            flag = item.get('Source').lower().endswith('.img')
            self.assertEqual(flag, False)

    @mock.patch('tacker.common.csar_utils.extract_csar_zip_file')
    def test_load_csar_data_with_single_manifest_with_vnf_artifact(
            self, mock_extract_csar_zip_file):
        file_path = utils.create_csar_with_unique_artifact(
            './tacker/tests/etc/samples/etsi/nfv/'
            'sample_vnf_package_csar_manifest')
        self.addCleanup(os.remove, file_path)
        vnf_data, flavours, vnf_artifacts = csar_utils.load_csar_data(
            self.context, constants.UUID, file_path)
        self.assertEqual(vnf_data['descriptor_version'], '1.0')
        self.assertEqual(vnf_data['vnfm_info'], ['Tacker'])
        self.assertEqual(flavours[0]['flavour_id'], 'simple')
        self.assertIsNotNone(flavours[0]['sw_images'])
        self.assertIsNotNone(vnf_artifacts)
        self.assertIsNotNone(vnf_artifacts[0]['Source'])
        self.assertIsNotNone(vnf_artifacts[0]['Hash'])

    @mock.patch('tacker.common.csar_utils.extract_csar_zip_file')
    def test_load_csar_data_with_single_meta_with_vnf_artifact(
            self, mock_extract_csar_zip_file):
        file_path = utils.create_csar_with_unique_artifact(
            './tacker/tests/etc/samples/etsi/nfv/'
            'sample_vnf_package_csar_meta')
        self.addCleanup(os.remove, file_path)
        vnf_data, flavours, vnf_artifacts = csar_utils.load_csar_data(
            self.context, constants.UUID, file_path)
        self.assertEqual(vnf_data['descriptor_version'], '1.0')
        self.assertEqual(vnf_data['vnfm_info'], ['Tacker'])
        self.assertEqual(flavours[0]['flavour_id'], 'simple')
        self.assertIsNotNone(flavours[0]['sw_images'])
        self.assertIsNotNone(vnf_artifacts)
        self.assertIsNotNone(vnf_artifacts[0]['Source'])
        self.assertIsNotNone(vnf_artifacts[0]['Hash'])

    @mock.patch('tacker.common.csar_utils.extract_csar_zip_file')
    def test_load_csar_data_meta_in_manifest_with_vnf_artifact(
            self, mock_extract_csar_zip_file):
        file_path = utils.create_csar_with_unique_artifact(
            './tacker/tests/etc/samples/etsi/nfv/'
            'sample_vnf_package_csar_meta_in_manifest')
        self.addCleanup(os.remove, file_path)
        vnf_data, flavours, vnf_artifacts = csar_utils.load_csar_data(
            self.context, constants.UUID, file_path)
        self.assertEqual(vnf_data['descriptor_version'], '1.0')
        self.assertEqual(vnf_data['vnfm_info'], ['Tacker'])
        self.assertEqual(flavours[0]['flavour_id'], 'simple')
        self.assertIsNotNone(flavours[0]['sw_images'])
        self.assertIsNotNone(vnf_artifacts)
        self.assertIsNotNone(vnf_artifacts[0]['Source'])
        self.assertIsNotNone(vnf_artifacts[0]['Hash'])

    @mock.patch('tacker.common.csar_utils.extract_csar_zip_file')
    def test_load_csar_data_false_mf_with_vnf_artifact(
            self, mock_extract_csar_zip_file):
        file_path = utils.create_csar_with_unique_artifact(
            './tacker/tests/etc/samples/etsi/nfv/'
            'sample_vnf_package_csar_in_meta_and_manifest_false')
        self.addCleanup(os.remove, file_path)
        manifest_path = 'manifest.mf1'
        exc = self.assertRaises(exceptions.InvalidCSAR,
                                csar_utils.load_csar_data,
                                self.context, constants.UUID, file_path)
        msg = (('The file "%(manifest)s" in the CSAR "%(csar)s" does not '
                'contain valid manifest.') %
               {'manifest': manifest_path, 'csar': file_path})
        self.assertEqual(msg, exc.format_message())

    @mock.patch('tacker.common.csar_utils.extract_csar_zip_file')
    def test_load_csar_data_false_mf_name_with_vnf_artifact(
            self, mock_extract_csar_zip_file):
        file_path = utils.create_csar_with_unique_artifact(
            './tacker/tests/etc/samples/etsi/nfv/'
            'sample_vnf_package_csar_in_single_manifest_false_name')
        self.addCleanup(os.remove, file_path)
        manifest_path = 'VNF1.mf'
        exc = self.assertRaises(exceptions.InvalidCSAR,
                                csar_utils.load_csar_data,
                                self.context, constants.UUID, file_path)
        msg = (('The filename "%(manifest)s" is an invalid name.'
                'The name must be the same as the main template '
                'file name.') %
               {'manifest': manifest_path, 'csar': file_path})
        self.assertEqual(msg, exc.format_message())

    @mock.patch('tacker.common.csar_utils.extract_csar_zip_file')
    def test_load_csar_data_false_hash_with_vnf_artifact(
            self, mock_extract_csar_zip_file):
        file_path = utils.create_csar_with_unique_artifact(
            './tacker/tests/etc/samples/etsi/nfv/'
            'sample_vnf_package_csar_in_meta_and_manifest_false_hash')
        self.addCleanup(os.remove, file_path)
        exc = self.assertRaises(exceptions.InvalidCSAR,
                                csar_utils.load_csar_data,
                                self.context, constants.UUID, file_path)
        hash_code = '27bbdb25d8f4ed6d07d6f6581b86515e8b2f' \
                    '0059b236ef7b6f50d6674b34f02'
        artifact_path = 'Scripts/install.sh'
        msg = (('The hash "%(hash)s" of artifact file '
                '"%(artifact)s" is an invalid value.') %
               {'hash': hash_code, 'artifact': artifact_path})
        self.assertEqual(msg, exc.format_message())

    @mock.patch('tacker.common.csar_utils.extract_csar_zip_file')
    def test_load_csar_data_missing_key_with_vnf_artifact(
            self, mock_extract_csar_zip_file):
        file_path = utils.create_csar_with_unique_artifact(
            './tacker/tests/etc/samples/etsi/nfv/'
            'sample_vnf_package_csar_in_meta_and_manifest_missing_key')
        self.addCleanup(os.remove, file_path)
        exc = self.assertRaises(exceptions.InvalidCSAR,
                                csar_utils.load_csar_data,
                                self.context, constants.UUID, file_path)
        key_name = sorted(['Algorithm'])
        msg = (('One of the artifact information may not have '
                'the key("%(key)s")') % {'key': key_name})
        self.assertEqual(msg, exc.format_message())

    @mock.patch('tacker.common.csar_utils.extract_csar_zip_file')
    def test_load_csar_data_missing_value_with_vnf_artifact(
            self, mock_extract_csar_zip_file):
        file_path = utils.create_csar_with_unique_artifact(
            './tacker/tests/etc/samples/etsi/nfv/'
            'sample_vnf_package_csar_in_meta_and_manifest_missing_value')
        self.addCleanup(os.remove, file_path)
        exc = self.assertRaises(exceptions.InvalidCSAR,
                                csar_utils.load_csar_data,
                                self.context, constants.UUID, file_path)
        key_name = 'Algorithm'
        msg = (('One of the artifact information may not have '
                'the key value("%(key)s")') % {'key': key_name})
        self.assertEqual(msg, exc.format_message())

    @mock.patch('tacker.common.csar_utils.extract_csar_zip_file')
    def test_load_csar_data_false_source_with_vnf_artifact(
            self, mock_extract_csar_zip_file):
        file_path = utils.create_csar_with_unique_artifact(
            './tacker/tests/etc/samples/etsi/nfv/'
            'sample_vnf_package_csar_in_meta_and_manifest_false_source')
        self.addCleanup(os.remove, file_path)
        exc = self.assertRaises(exceptions.InvalidCSAR,
                                csar_utils.load_csar_data,
                                self.context, constants.UUID, file_path)
        artifact_path = 'Scripts/install.s'
        msg = (('The path("%(artifact_path)s") of '
                'artifact Source is an invalid value.') %
               {'artifact_path': artifact_path})
        self.assertEqual(msg, exc.format_message())

    @mock.patch('tacker.common.csar_utils.extract_csar_zip_file')
    def test_load_csar_data_false_algorithm_with_vnf_artifact(
            self, mock_extract_csar_zip_file):
        file_path = utils.create_csar_with_unique_artifact(
            './tacker/tests/etc/samples/etsi/nfv/'
            'sample_vnf_package_csar_in_meta_and_manifest_false_algorithm')
        self.addCleanup(os.remove, file_path)
        exc = self.assertRaises(exceptions.InvalidCSAR,
                                csar_utils.load_csar_data,
                                self.context, constants.UUID, file_path)
        algorithm = 'sha-255'
        artifact_path = 'Scripts/install.sh'
        msg = (('The algorithm("%(algorithm)s") of '
                'artifact("%(artifact_path)s") is '
                'an invalid value.') %
               {'algorithm': algorithm,
                'artifact_path': artifact_path})
        self.assertEqual(msg, exc.format_message())

    @mock.patch('tacker.common.csar_utils.extract_csar_zip_file')
    def test_load_csar_data_without_instantiation_level(
            self, mock_extract_csar_zip_file):
        file_path = self._get_csar_zip_from_dir(
            'csar_without_instantiation_level')
        exc = self.assertRaises(exceptions.InvalidCSAR,
                          csar_utils.load_csar_data,
                          self.context, constants.UUID, file_path)
        msg = ('Policy of type'
               ' "tosca.policies.nfv.InstantiationLevels is not defined.')
        self.assertEqual(msg, exc.format_message())

    @mock.patch('tacker.common.csar_utils.extract_csar_zip_file')
    def test_load_csar_data_with_invalid_instantiation_level(
            self, mock_extract_csar_zip_file):
        file_path = self._get_csar_zip_from_dir(
            'csar_invalid_instantiation_level')
        exc = self.assertRaises(exceptions.InvalidCSAR,
                                csar_utils.load_csar_data,
                                self.context, constants.UUID, file_path)
        levels = ['instantiation_level_1', 'instantiation_level_2']
        msg = ("Level(s) instantiation_level_3 not found in "
               "defined levels %s") % ",".join(sorted(levels))
        self.assertEqual(msg, exc.format_message())

    @mock.patch('tacker.common.csar_utils.extract_csar_zip_file')
    def test_load_csar_data_with_invalid_default_instantiation_level(
            self, mock_extract_csar_zip_file):
        file_path = self._get_csar_zip_from_dir(
            'csar_with_invalid_default_instantiation_level')
        exc = self.assertRaises(exceptions.InvalidCSAR,
                                csar_utils.load_csar_data,
                                self.context, constants.UUID, file_path)
        levels = ['instantiation_level_1', 'instantiation_level_2']
        msg = ("Level instantiation_level_3 not found in "
               "defined levels %s") % ",".join(sorted(levels))
        self.assertEqual(msg, exc.format_message())

    @mock.patch('tacker.common.csar_utils.extract_csar_zip_file')
    def test_load_csar_data_without_vnfd_info(
            self, mock_extract_csar_zip_file):
        file_path = self._get_csar_zip_from_dir(
            'csar_without_vnfd_info')
        exc = self.assertRaises(exceptions.InvalidCSAR,
                                csar_utils.load_csar_data,
                                self.context, constants.UUID, file_path)
        self.assertEqual("VNF properties are mandatory", exc.format_message())

    @mock.patch('tacker.common.csar_utils.extract_csar_zip_file')
    def test_load_csar_data_with_artifacts_and_without_sw_image_data(
            self, mock_extract_csar_zip_file):
        file_path = self._get_csar_zip_from_dir(
            'csar_without_sw_image_data')
        exc = self.assertRaises(exceptions.InvalidCSAR,
                                csar_utils.load_csar_data,
                                self.context, constants.UUID, file_path)
        msg = ('Node property "sw_image_data" is missing for '
               'artifact sw_image for node VDU1.')
        self.assertEqual(msg, exc.format_message())

    @mock.patch('tacker.common.csar_utils.extract_csar_zip_file')
    def test_load_csar_data_with_multiple_sw_image_data(
            self, mock_extract_csar_zip_file):
        file_path = self._get_csar_zip_from_dir(
            'csar_with_multiple_sw_image_data')
        exc = self.assertRaises(exceptions.InvalidCSAR,
                                csar_utils.load_csar_data,
                                self.context, constants.UUID, file_path)
        msg = ('artifacts of type "tosca.artifacts.nfv.SwImage"'
               ' is added more than one time for node VDU1.')
        self.assertEqual(msg, exc.format_message())

    @mock.patch('tacker.common.csar_utils.extract_csar_zip_file')
    def test_csar_with_missing_sw_image_data_in_main_template(
            self, mock_extract_csar_zip_file):
        file_path = self._get_csar_zip_from_dir(
            'csar_with_missing_sw_image_data_in_main_template')
        exc = self.assertRaises(exceptions.InvalidCSAR,
                                csar_utils.load_csar_data,
                                self.context, constants.UUID, file_path)
        msg = ('Node property "sw_image_data" is missing for'
               ' artifact sw_image for node VDU1.')
        self.assertEqual(msg, exc.format_message())

    @mock.patch('tacker.common.csar_utils.extract_csar_zip_file')
    def test_load_csar_data_without_flavour_info(
            self, mock_extract_csar_zip_file):
        file_path = self._get_csar_zip_from_dir('csar_without_flavour_info')
        exc = self.assertRaises(exceptions.InvalidCSAR,
                                csar_utils.load_csar_data,
                                self.context, constants.UUID, file_path)
        self.assertEqual("No VNF flavours are available", exc.format_message())

    @mock.patch('tacker.common.csar_utils.extract_csar_zip_file')
    def test_load_csar_data_without_flavour_info_in_main_template(
            self, mock_extract_csar_zip_file):
        file_path = self._get_csar_zip_from_dir(
            'csar_without_flavour_info_in_main_template')
        exc = self.assertRaises(exceptions.InvalidCSAR,
                                csar_utils.load_csar_data,
                                self.context, constants.UUID, file_path)
        self.assertEqual("No VNF flavours are available",
                         exc.format_message())

    @mock.patch.object(os, 'remove')
    @mock.patch.object(shutil, 'rmtree')
    def test_delete_csar_data(self, mock_rmtree, mock_remove):
        csar_utils.delete_csar_data(constants.UUID)
        mock_rmtree.assert_called()
        mock_remove.assert_called()

    @mock.patch('tacker.common.csar_utils.extract_csar_zip_file')
    def test_load_csar_data_without_policies(
            self, mock_extract_csar_zip_file):
        file_path = self._get_csar_zip_from_dir(
            'csar_without_policies')
        vnf_data, flavours, vnf_artifacts = csar_utils.load_csar_data(
            self.context, constants.UUID, file_path)
        self.assertIsNone(flavours[0].get('instantiation_levels'))
        self.assertEqual(vnf_data['descriptor_version'], '1.0')

    @mock.patch('tacker.common.csar_utils.extract_csar_zip_file')
    def test_load_csar_with_artifacts_short_notation_without_sw_image_data(
            self, mock_extract_csar_zip_file):
        file_path = "./tacker/tests/etc/samples/etsi/nfv/" \
                    "csar_short_notation_for_artifacts_without_sw_image_data"
        zip_name, uniqueid = utils.create_csar_with_unique_vnfd_id(file_path)
        exc = self.assertRaises(exceptions.InvalidCSAR,
                                csar_utils.load_csar_data,
                                self.context, constants.UUID, zip_name)
        msg = ('Node property "sw_image_data" is missing for'
               ' artifact sw_image for node VDU1.')
        self.assertEqual(msg, exc.format_message())
        os.remove(zip_name)

    @mock.patch('tacker.common.csar_utils.extract_csar_zip_file')
    def test_load_csar_data_with_artifacts_short_notation(
            self, mock_extract_csar_zip_file):
        file_path = "./tacker/tests/etc/samples/etsi/nfv/" \
                    "csar_with_short_notation_for_artifacts"
        zip_name, uniqueid = utils.create_csar_with_unique_vnfd_id(file_path)

        vnf_data, flavours, vnf_artifacts = csar_utils.load_csar_data(
            self.context, constants.UUID, zip_name)
        self.assertEqual(vnf_data['descriptor_version'], '1.0')
        self.assertEqual(vnf_data['vnfm_info'], ['Tacker'])
        self.assertEqual(flavours[0]['flavour_id'], 'simple')
        self.assertIsNotNone(flavours[0]['sw_images'])
        os.remove(zip_name)

    @mock.patch('tacker.common.csar_utils.extract_csar_zip_file')
    def test_load_csar_data_with_multiple_sw_image_data_with_short_notation(
            self, mock_extract_csar_zip_file):

        file_path = "./tacker/tests/etc/samples/etsi/nfv/" \
                    "csar_multiple_sw_image_data_with_short_notation"
        zip_name, uniqueid = utils.create_csar_with_unique_vnfd_id(file_path)
        exc = self.assertRaises(exceptions.InvalidCSAR,
                                csar_utils.load_csar_data,
                                self.context, constants.UUID, zip_name)
        msg = ('artifacts of type "tosca.artifacts.nfv.SwImage"'
               ' is added more than one time for node VDU1.')
        self.assertEqual(msg, exc.format_message())
        os.remove(zip_name)
