# All Rights Reserved.
#
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

import os

import testtools
from toscaparser import tosca_template
from toscaparser.utils import yamlparser
from translator.hot import tosca_translator

from tacker.tosca import utils


class TestSamples(testtools.TestCase):
    """Sample tosca validation.

    Helps to validate the tosca templates provided in the samples folder
    to make sure whether its valid YAML, valid TOSCA and
    possible to translate into HOT template.
    """

    def _get_list_of_sample(self, tosca_files):
        if tosca_files:
            base_path = (os.path.dirname(os.path.abspath(__file__)) +
                         '/../../../samples/tosca-templates/vnfd/')
            if isinstance(tosca_files, list):
                list_of_samples = []
                for tosca_file in tosca_files:
                    sample = base_path + tosca_file
                    list_of_samples.append(sample)
                return list_of_samples

    def _test_samples(self, files):
        if files:
            for f in self._get_list_of_sample(files):
                with open(f, 'r') as _f:
                    yaml_dict = None
                    try:
                        yaml_dict = yamlparser.simple_ordered_parse(_f.read())
                    except:  # noqa
                        pass
                    self.assertIsNotNone(
                        yaml_dict,
                        "Yaml parser failed to parse %s" % f)

                    utils.updateimports(yaml_dict)

                    tosca = None
                    try:
                        tosca = tosca_template.ToscaTemplate(
                            a_file=False,
                            yaml_dict_tpl=yaml_dict)
                    except:  # noqa
                        pass

                    self.assertIsNotNone(
                        tosca,
                        "Tosca parser failed to parse %s" % f)
                    utils.post_process_template(tosca)
                    hot = None
                    try:
                        hot = tosca_translator.TOSCATranslator(tosca,
                                                               {}).translate()
                    except:  # noqa
                        pass

                    self.assertIsNotNone(
                        hot,
                        "Heat-translator failed to translate %s" % f)

    def test_scale_sample(self, tosca_file=['tosca-vnfd-scale.yaml']):
        self._test_samples(tosca_file)

    def test_alarm_sample(self, tosca_file=['tosca-vnfd-alarm-scale.yaml']):
        self._test_samples(tosca_file)

    def test_list_samples(self,
                          files=['tosca-vnfd-scale.yaml',
                                 'tosca-vnfd-alarm-scale.yaml']):
        self._test_samples(files)
