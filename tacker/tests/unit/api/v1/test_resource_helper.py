# Copyright (c) 2014-2018 China Mobile (SuZhou) Software Technology Co.,Ltd.
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

from tacker.api.v1.resource_helper import build_plural_mappings
from tacker.tests import base


class ResourceHelperTestCase(base.BaseTestCase):

    def test_build_plural_mappings(self):
        special_mappings = {}
        resource_map = {
            'vims': {
                'id': {
                    'allow_post': False,
                    'allow_put': False,
                }
            },
            'vnffgs': {
                'id': {
                    'allow_post': False,
                    'allow_put': False,
                }
            },
        }

        expected_res = {'vnffgs': 'vnffg', 'vims': 'vim'}
        result = build_plural_mappings(special_mappings, resource_map)
        self.assertEqual(expected_res, result)

    def test_build_plural_mappings_with_suffix_y(self):
        special_mappings = {}
        resource_map = {
            'policies': {
                'id': {
                    'allow_post': False,
                }
            },
            'vnffgs': {
                'id': {
                    'allow_post': False,
                    'allow_put': False,
                }
            },
        }

        expected_res = {'vnffgs': 'vnffg', 'policies': 'policy'}
        result = build_plural_mappings(special_mappings, resource_map)
        self.assertEqual(expected_res, result)
