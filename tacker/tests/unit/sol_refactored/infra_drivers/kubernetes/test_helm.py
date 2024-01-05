# Copyright (C) 2022 Nippon Telegraph and Telephone Corporation
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

import os
from unittest import mock

from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.common import vnfd_utils
from tacker.sol_refactored.infra_drivers.kubernetes import helm
from tacker.sol_refactored import objects
from tacker.tests.unit import base
from tacker.tests import utils


CNF_SAMPLE_VNFD_ID = "b1bb0ce7-ebca-4fa7-95ed-4840d70a1177"


class TestHelm(base.TestCase):

    def setUp(self):
        super(TestHelm, self).setUp()
        objects.register_all()
        self.driver = helm.Helm()

        # NOTE: bollow a sample of k8s at the moment since it is enough
        # for current tests.
        sample_dir = utils.test_sample("unit/sol_refactored/samples")
        self.vnfd_1 = vnfd_utils.Vnfd(CNF_SAMPLE_VNFD_ID)
        self.vnfd_1.init_from_csar_dir(os.path.join(sample_dir, "sample2"))

    def test_scale_invalid_parameter(self):
        req = objects.ScaleVnfRequest(
            type='SCALE_OUT',
            aspectId='vdu1_aspect',
            numberOfSteps=1
        )
        inst_vnf_info = objects.VnfInstanceV2_InstantiatedVnfInfo(
            vnfcResourceInfo=[objects.VnfcResourceInfoV2(vduId='VDU1')],
            metadata={
                'namespace': 'default',
                'release_name': 'test-release',
                'helm_chart_path': 'Files/kubernetes/test-chart.tgz',
                'helm_value_names': {'VDU2': {'replica': 'values.replica'}}
            }
        )
        inst = objects.VnfInstanceV2(
            instantiatedVnfInfo=inst_vnf_info
        )
        grant_req = objects.GrantRequestV1(
            addResources=[
                objects.ResourceDefinitionV1(
                    type='COMPUTE',
                    resourceTemplateId='VDU1'
                )
            ]
        )

        expected_ex = sol_ex.HelmParameterNotFound(vdu_name='VDU1')
        ex = self.assertRaises(sol_ex.HelmParameterNotFound,
            self.driver._scale, req, inst, grant_req, mock.Mock(),
            self.vnfd_1, mock.Mock(), mock.Mock())
        self.assertEqual(expected_ex.detail, ex.detail)
