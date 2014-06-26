# Copyright 2014 Intel Corporation.
# Copyright 2014 Isaku Yamahata <isaku.yamahata at intel com>
#                               <isaku.yamahata at gmail com>
# All Rights Reserved.
#
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
#
# @author: Isaku Yamahata, Intel Corporation.

from oslo.messaging import target

from tacker.tests import base
from tacker.vm.agent import target as agent_target


class TestTarget(base.BaseTestCase):
    target_str = ('exchange=default,topic=topic,namespace=namespace,'
                  'version=version,server=server,fanout=False')
    target_instance = target.Target('default', 'topic', 'namespace', 'version',
                                    'server', False)

    def test_parse(self):
        t = agent_target.target_parse(self.target_str)
        self.assertEqual(t, self.target_instance)

    def test_str(self):
        t = agent_target.target_str(self.target_instance)
        self.assertEqual(t, self.target_str)
