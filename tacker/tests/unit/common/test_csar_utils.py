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

import mock
import os
import shutil
import testtools

from tacker.common import csar_utils
from tacker.common import exceptions
from tacker import context
from tacker.tests import constants


class TestCSARUtils(testtools.TestCase):

    def setUp(self):
        super(TestCSARUtils, self).setUp()
        self.context = context.get_admin_context()
        self.base_path = os.path.dirname(os.path.abspath(__file__))

    def _get_csar_file_path(self, file_name):
        return os.path.join(
            self.base_path, "../../etc/samples", file_name)

    @mock.patch('tacker.common.csar_utils.extract_csar_zip_file')
    def test_load_csar_data(self, mock_extract_csar_zip_file):
        file_path = self._get_csar_file_path("sample_vnf_package_csar.zip")
        vnf_data, flavours = csar_utils.load_csar_data(
            self.context, constants.UUID, file_path)
        self.assertEqual(vnf_data['descriptor_version'], '1.0')
        self.assertEqual(vnf_data['vnfm_info'], ['Tacker'])
        self.assertEqual(flavours[0]['flavour_id'], 'simple')
        self.assertIsNotNone(flavours[0]['sw_images'])

    @mock.patch('tacker.common.csar_utils.extract_csar_zip_file')
    def test_load_csar_data_with_single_yaml(
            self, mock_extract_csar_zip_file):
        file_path = self._get_csar_file_path(
            "sample_vnfpkg_no_meta_single_vnfd.zip")
        vnf_data, flavours = csar_utils.load_csar_data(
            self.context, constants.UUID, file_path)
        self.assertEqual(vnf_data['descriptor_version'], '1.0')
        self.assertEqual(vnf_data['vnfm_info'], ['Tacker'])
        self.assertEqual(flavours[0]['flavour_id'], 'simple')
        self.assertIsNotNone(flavours[0]['sw_images'])

    @mock.patch('tacker.common.csar_utils.extract_csar_zip_file')
    def test_load_csar_data_without_instantiation_level(
            self, mock_extract_csar_zip_file):
        file_path = self._get_csar_file_path(
            "csar_without_instantiation_level.zip")
        exc = self.assertRaises(exceptions.InvalidCSAR,
                          csar_utils.load_csar_data,
                          self.context, constants.UUID, file_path)
        msg = ('Policy of type'
               ' "tosca.policies.nfv.InstantiationLevels is not defined.')
        self.assertEqual(msg, exc.format_message())

    @mock.patch('tacker.common.csar_utils.extract_csar_zip_file')
    def test_load_csar_data_with_invalid_instantiation_level(
            self, mock_extract_csar_zip_file):
        file_path = self._get_csar_file_path(
            "csar_invalid_instantiation_level.zip")
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
        file_path = self._get_csar_file_path(
            "csar_with_invalid_default_instantiation_level.zip")
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
        file_path = self._get_csar_file_path(
            "csar_without_vnfd_info.zip")
        exc = self.assertRaises(exceptions.InvalidCSAR,
                                csar_utils.load_csar_data,
                                self.context, constants.UUID, file_path)
        self.assertEqual("VNF properties are mandatory", exc.format_message())

    @mock.patch('tacker.common.csar_utils.extract_csar_zip_file')
    def test_load_csar_data_with_artifacts_and_without_sw_image_data(
            self, mock_extract_csar_zip_file):
        file_path = self._get_csar_file_path(
            "csar_without_sw_image_data.zip")
        exc = self.assertRaises(exceptions.InvalidCSAR,
                                csar_utils.load_csar_data,
                                self.context, constants.UUID, file_path)
        msg = ('Node property "sw_image_data" is missing for artifact'
               ' type tosca.artifacts.nfv.SwImage for node VDU1.')
        self.assertEqual(msg, exc.format_message())

    @mock.patch('tacker.common.csar_utils.extract_csar_zip_file')
    def test_load_csar_data_with_multiple_sw_image_data(
            self, mock_extract_csar_zip_file):
        file_path = self._get_csar_file_path(
            "csar_with_multiple_sw_image_data.zip")
        exc = self.assertRaises(exceptions.InvalidCSAR,
                                csar_utils.load_csar_data,
                                self.context, constants.UUID, file_path)
        msg = ('artifacts of type "tosca.artifacts.nfv.SwImage"'
               ' is added more than one time for node VDU1.')
        self.assertEqual(msg, exc.format_message())

    @mock.patch('tacker.common.csar_utils.extract_csar_zip_file')
    def test_csar_with_missing_sw_image_data_in_main_template(
            self, mock_extract_csar_zip_file):
        file_path = self._get_csar_file_path(
            "csar_with_missing_sw_image_data_in_main_template.zip")
        exc = self.assertRaises(exceptions.InvalidCSAR,
                                csar_utils.load_csar_data,
                                self.context, constants.UUID, file_path)
        msg = ('Node property "sw_image_data" is missing for artifact'
               ' type tosca.artifacts.nfv.SwImage for node VDU1.')
        self.assertEqual(msg, exc.format_message())

    @mock.patch('tacker.common.csar_utils.extract_csar_zip_file')
    def test_load_csar_data_without_flavour_info(
            self, mock_extract_csar_zip_file):
        file_path = self._get_csar_file_path("csar_without_flavour_info.zip")
        exc = self.assertRaises(exceptions.InvalidCSAR,
                                csar_utils.load_csar_data,
                                self.context, constants.UUID, file_path)
        self.assertEqual("No VNF flavours are available", exc.format_message())

    @mock.patch('tacker.common.csar_utils.extract_csar_zip_file')
    def test_load_csar_data_without_flavour_info_in_main_template(
            self, mock_extract_csar_zip_file):
        file_path = self._get_csar_file_path(
            "csar_without_flavour_info_in_main_template.zip")
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
        file_path = self._get_csar_file_path("csar_without_policies.zip")
        vnf_data, flavours = csar_utils.load_csar_data(
            self.context, constants.UUID, file_path)
        self.assertIsNone(flavours[0].get('instantiation_levels'))
        self.assertEqual(vnf_data['descriptor_version'], '1.0')
