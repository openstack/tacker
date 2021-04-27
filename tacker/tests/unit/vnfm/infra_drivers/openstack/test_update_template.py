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

from unittest import mock

from heatclient.v1 import resources
from tacker.tests.unit import base
from tacker.tests import uuidsentinel
from tacker.vnfm.infra_drivers.openstack.heat_client import HeatClient
from tacker.vnfm.infra_drivers.openstack.update_template import HOTUpdater


class TestUpdateTemplate(base.TestCase):

    def setUp(self):
        super(TestUpdateTemplate, self).setUp()
        self.maxDiff = None
        self._mock_heatclient()
        self.stack_id = uuidsentinel.stack_id
        self.hot_updater = HOTUpdater(self.heatclient)

    def _mock_heatclient(self):
        self.heatclient = mock.Mock(spec=HeatClient)
        self.heatclient.stacks = mock.Mock()
        self.heatclient.stacks.template.side_effect = [
            self._get_template(),
            self._get_intermediate_template1(),
            self._get_nested_template1(),
            self._get_intermediate_template2(),
            self._get_nested_template2()
        ]
        self.heatclient.resource_get_list.return_value = \
            self._get_stack_resources()

    def test_get_templates_from_stack(self):
        self.hot_updater.get_templates_from_stack(self.stack_id)

        self.assertDictEqual(self._get_template(), self.hot_updater.template)
        self.assertDictEqual(
            {'VDU1.yaml': self._get_nested_template1(),
             'VDU2.yaml': self._get_nested_template2()},
            self.hot_updater.nested_templates)

    def test_update_resource_property(self):
        self.hot_updater.get_templates_from_stack(self.stack_id)

        # Test pattern 1: Change network and CP1(DHCP) address to fixed.
        self.hot_updater.update_resource_property(
            'CP1', ['OS::Neutron::Port'],
            network=uuidsentinel.network_id_cp1_changed,
            fixed_ips=[{'ip_address': '20.20.0.100'}])
        expected = {
            'network': uuidsentinel.network_id_cp1_changed,
            'fixed_ips': [{'ip_address': '20.20.0.100'}]
        }
        self.assertEqual(
            expected,
            self.hot_updater.template['resources']['CP1']['properties'])

        # Test pattern 2: Change network and fixed address.
        self.hot_updater.update_resource_property(
            'CP2', ['OS::Neutron::Port'],
            network=uuidsentinel.network_id_cp2_changed,
            fixed_ips=[{
                'ip_address': '20.20.0.200',
                'subnet': uuidsentinel.subnet_id_cp2_changed
            }])
        expected = {
            'network': uuidsentinel.network_id_cp2_changed,
            'fixed_ips': [{
                'ip_address': '20.20.0.200',
                'subnet': uuidsentinel.subnet_id_cp2_changed,
            }]
        }
        self.assertEqual(
            expected,
            self.hot_updater.template['resources']['CP2']['properties'])

        # Test Pattern 3: Delete fixed_ips property.
        self.hot_updater.update_resource_property(
            'CP3', ['OS::Neutron::Port'],
            network=uuidsentinel.network_id_cp3_changed,
            fixed_ips=None)
        self.assertIsNone(self.hot_updater.nested_templates[
            'VDU1.yaml']['resources']['CP3']['properties'].get('fixed_ips'))

    def test_update_resource_property_not_found(self):
        self.hot_updater.get_templates_from_stack(self.stack_id)

        # Test Pattern 4: Resource does not exist.
        self.hot_updater.update_resource_property(
            'CPX', ['OS::Neutron::Port'],
            network=uuidsentinel.network_id_cpx,
            fixed_ips=[{'ip_address': '20.20.0.100'}])
        self.assertEqual(self._get_template(), self.hot_updater.template)

        # Test Pattern 5: Resource type does not exist.
        self.hot_updater.update_resource_property(
            'CP1', ['OS::Sahara::Cluster'],
            network=uuidsentinel.network_id_cp1_changed,
            fixed_ips=[{'ip_address': '20.20.0.100'}])
        self.assertEqual(self._get_template(), self.hot_updater.template)

        # Test Pattern 6: Resource doess not have properties.
        self.hot_updater.update_resource_property(
            'CP5', ['OS::Neutron::Port'],
            network=uuidsentinel.network_id_cp5,
            fixed_ips=[{'ip_address': '20.20.0.100'}])
        self.assertEqual(self._get_template(), self.hot_updater.template)

    def _get_template(self):
        return {
            'heat_template_version': '2013-05-23',
            'description': 'Simple deployment flavour for Sample VNF',
            'parameters': {},
            'resources': {
                'CP1': {
                    'type': 'OS::Neutron::Port',
                    'properties': {
                        'network': uuidsentinel.network_id_cp1,
                    },
                },
                'CP2': {
                    'type': 'OS::Neutron::Port',
                    'properties': {
                        'network': uuidsentinel.network_id_cp2,
                        'fixed_ips': [{
                            'ip_address': '10.10.0.200',
                            'subnet': uuidsentinel.subnet_id_cp2,
                        }],
                    },
                },
                'CP5': {
                    'type': 'OS::Neutron::Port',
                },
            },
        }

    def _get_intermediate_template1(self):
        return {
            'heat_template_version': '2013-05-23',
            'description': 'Simple deployment flavour for Sample VNF',
            'parameters': {},
            'resources': {
                'xxxxxxxx': {
                    'type': 'VDU1.yaml',
                },
            },
        }

    def _get_intermediate_template2(self):
        return {
            'heat_template_version': '2013-05-23',
            'description': 'Simple deployment flavour for Sample VNF',
            'parameters': {},
            'resources': {
                'yyyyyyyy': {
                    'type': 'VDU2.yaml',
                },
            },
        }

    def _get_nested_template1(self):
        return {
            'heat_template_version': '2013-05-23',
            'description': 'Simple deployment flavour for Sample VNF',
            'parameters': {},
            'resources': {
                'CP3': {
                    'type': 'OS::Neutron::Port',
                    'properties': {
                        'network': uuidsentinel.network_id_cp3,
                        'fixed_ips': [{
                            'subnet': uuidsentinel.subnet_id_cp3,
                        }],
                    },
                },
            },
        }

    def _get_nested_template2(self):
        return {
            'heat_template_version': '2013-05-23',
            'description': 'Simple deployment flavour for Sample VNF',
            'parameters': {},
            'resources': {
                'CP4': {
                    'type': 'OS::Neutron::Port',
                    'properties': {
                        'network': uuidsentinel.network_id_cp4,
                        'fixed_ips': [{
                            'subnet': uuidsentinel.subnet_id_cp4,
                        }],
                    },
                },
            },
        }

    def _get_stack_resources(self):
        def _create_resource(resource_name, resource_type):
            return resources.Resource(None, {
                'resource_name': resource_name,
                'resource_type': resource_type,
                'resource_status': 'CREATE_COMPLETE',
                'physical_resource_id': uuidsentinel.uuid,
            })

        data = [
            ('VDU1_scale_group', 'OS::Heat::AutoScalingGroup'),
            ('xxxxxxxx', 'VDU1.yaml'),
            ('VDU2_scale_group', 'OS::Heat::AutoScalingGroup'),
            ('yyyyyyyy', 'VDU2.yaml'),
            ('CP1', 'OS::Neutron::Port'),
            ('CP2', 'OS::Neutron::Port'),
            ('CP3', 'OS::Neutron::Port'),
            ('CP4', 'OS::Neutron::Port')
        ]
        return [_create_resource(row[0], row[1]) for row in data]
