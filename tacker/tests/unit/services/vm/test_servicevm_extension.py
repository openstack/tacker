# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
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

import copy
import uuid

import mock
from webob import exc

from tacker.extensions import tacker
from tacker.plugins.common import constants
from tacker.tests.unit import test_api_v2
from tacker.tests.unit import test_api_v2_extension


_uuid = lambda: str(uuid.uuid4())
_get_path = test_api_v2._get_path


class TackerExtensionTestCase(test_api_v2_extension.ExtensionTestCase):
    fmt = 'json'

    _DEVICE_TEMPLATE = 'device_template'
    _SERVICE_INSTANCE = 'service_instance'
    _DEVICE = 'device'

    _PATH_TACKER = 'tacker'
    _PATH_DEVICE_TEMPLATES = _PATH_TACKER + '/device-templates'
    _PATH_SERVICE_INSTANCES = _PATH_TACKER + '/service-instances'
    _PATH_DEVICES = _PATH_TACKER + '/devices'

    def setUp(self):
        super(TackerExtensionTestCase, self).setUp()
        self._setUpExtension(
            'tacker.extensions.tacker.TackerPluginBase',
            constants.TACKER, tacker.RESOURCE_ATTRIBUTE_MAP,
            tacker.Tacker, self._PATH_TACKER,
            translate_resource_name=True, use_quota=True)

    # hosting device template
    def test_device_template_create(self):
        template_id = _uuid()
        data = {
            self._DEVICE_TEMPLATE: {
                'tenant_id': _uuid(),
                'name': 'template0',
                'description': 'mytemplate0',
                'service_types': [{'service_type': 'SERVICE0'},
                                  {'service_type': 'SERVICE1'}],
                'infra_driver': 'noop',
                'mgmt_driver': 'noop',
                'attributes': {'key0': 'value0', 'key1': 'value1'},
            }
        }
        return_value = copy.copy(data[self._DEVICE_TEMPLATE])
        return_value.update({'id': template_id})

        instance = self.plugin.return_value
        instance.create_device_template.return_value = return_value
        res = self.api.post(
            _get_path(self._PATH_DEVICE_TEMPLATES, fmt=self.fmt),
            self.serialize(data), content_type='application/%s' % self.fmt)
        instance.create_device_template.assert_called_with(
            mock.ANY, device_template=data)
        self.assertEqual(exc.HTTPCreated.code, res.status_int)
        res = self.deserialize(res)
        self.assertIn(self._DEVICE_TEMPLATE, res)
        self.assertEqual(return_value, res[self._DEVICE_TEMPLATE])

    def test_device_template_list(self):
        template_id = _uuid()
        return_value = [{
            'id': template_id,
            'tenant_id': _uuid(),
            'name': 'template0',
            'description': 'description0',
            'service_types': [{'service_type': 'SERVICE0'},
                              {'service_type': 'SERVICE1'}],
            'infra_driver': 'noop',
            'mgmt_driver': 'noop',
            'attributes': {'key0': 'value0', 'key1': 'value1'},
        }]
        instance = self.plugin.return_value
        instance.get_device_templates.return_value = return_value

        res = self.api.get(
            _get_path(self._PATH_DEVICE_TEMPLATES, fmt=self.fmt))
        instance.get_device_templates.assert_called_with(
            mock.ANY, fields=mock.ANY, filters=mock.ANY)
        self.assertEqual(exc.HTTPOk.code, res.status_int)

    def test_device_template_get(self):
        template_id = _uuid()
        return_value = {
            'id': template_id,
            'tenant_id': _uuid(),
            'name': 'template0',
            'description': 'description0',
            'service_types': [{'service_type': 'SERVICE0'},
                              {'service_type': 'SERVICE1'}],
            'infra_driver': 'noop',
            'mgmt_driver': 'noop',
            'attributes': {'key0': 'value0', 'key1': 'value1'},
        }
        instance = self.plugin.return_value
        instance.get_device_template.return_value = return_value

        res = self.api.get(_get_path(
            self._PATH_DEVICE_TEMPLATES, id=template_id, fmt=self.fmt))
        instance.get_device_template.assert_called_with(
            mock.ANY, template_id, fields=mock.ANY)
        self.assertEqual(exc.HTTPOk.code, res.status_int)
        res = self.deserialize(res)
        self.assertIn(self._DEVICE_TEMPLATE, res)
        self.assertEqual(return_value, res[self._DEVICE_TEMPLATE])

    def test_device_template_delete(self):
        self._test_entity_delete(self._DEVICE_TEMPLATE)

    # logical service instance
    def test_service_instance_list(self):
        return_value = [{
            'id': _uuid(),
            'tenant_id': _uuid(),
            'name': 'instance0',
            'service_type_id': _uuid(),
            'service_table_id': _uuid(),
            'mgmt_driver': 'noop',
            'mgmt_address': 'no-address',
            'service_contexts': [
                {'network_id': _uuid(), },
                {'network_id': _uuid(), },
            ],
            'status': 'ACTIVE',
        }]
        instance = self.plugin.return_value
        instance.get_service_instances.return_value = return_value

        res = self.api.get(
            _get_path(self._PATH_SERVICE_INSTANCES, fmt=self.fmt))
        instance.get_service_instances.assert_called_with(
            mock.ANY, fields=mock.ANY, filters=mock.ANY)
        self.assertEqual(exc.HTTPOk.code, res.status_int)

    def test_service_instance_get(self):
        service_instance_id = _uuid()
        return_value = {
            'id': service_instance_id,
            'tenant_id': _uuid(),
            'name': 'instance0',
            'service_type_id': _uuid(),
            'service_table_id': _uuid(),
            'mgmt_driver': 'noop',
            'mgmt_address': 'no-address',
            'service_contexts': [
                {'network_id': _uuid(), },
                {'network_id': _uuid(), },
            ],
            'status': 'ACTIVE',
        }
        instance = self.plugin.return_value
        instance.get_service_instance.return_value = return_value

        res = self.api.get(
            _get_path(self._PATH_SERVICE_INSTANCES,
                      id=service_instance_id, fmt=self.fmt))
        self.assertEqual(exc.HTTPOk.code, res.status_int)
        res = self.deserialize(res)
        self.assertIn(self._SERVICE_INSTANCE, res)
        self.assertEqual(return_value, res[self._SERVICE_INSTANCE])

    # hosting device
    def test_device_create(self):
        data = {
            self._DEVICE: {
                'tenant_id': _uuid(),
                'template_id': _uuid(),
                'kwargs': {'key0': 'arg0', 'key1': 'arg1'},
                'service_contexts': [{'network_id': _uuid()},
                                     {'network_id': _uuid()}],
            }
        }
        return_value = copy.copy(data[self._DEVICE])
        return_value.update({
            'id': _uuid(),
            'instance_id': _uuid(),
            'mgmt_address': 'no-address',
            'services': [_uuid(), _uuid()],
            'status': 'ACTIVE', })

        instance = self.plugin.return_value
        instance.create_device.return_value = return_value
        res = self.api.post(
            _get_path(self._PATH_DEVICES, fmt=self.fmt),
            self.serialize(data), content_type='application/%s' % self.fmt)
        instance.create_device.assert_called_with(mock.ANY, device=data)
        self.assertEqual(exc.HTTPCreated.code, res.status_int)
        res = self.deserialize(res)
        self.assertIn(self._DEVICE, res)
        self.assertEqual(return_value, res[self._DEVICE])

    def test_device_list(self):
        return_value = [{
            self._DEVICE: {
                'id': _uuid(),
                'instance_id': _uuid(),
                'mgmt_address': 'no-address',
                'tenant_id': _uuid(),
                'template_id': _uuid(),
                'kwargs': {'key0': 'arg0', 'key1': 'arg1'},
                'service_contexts': [{'network_id': _uuid()},
                                     {'network_id': _uuid()}],
                'services': [_uuid(), _uuid()],
                'status': 'ACTIVE',
            }
        }]
        instance = self.plugin.return_value
        instance.get_device.return_value = return_value

        res = self.api.get(_get_path(self._PATH_DEVICES, fmt=self.fmt))
        instance.get_devices.assert_called_with(
            mock.ANY, fields=mock.ANY, filters=mock.ANY)
        self.assertEqual(exc.HTTPOk.code, res.status_int)

    def test_device_get(self):
        device_id = _uuid()
        return_value = {
            'id': device_id,
            'instance_id': _uuid(),
            'mgmt_address': 'no-address',
            'tenant_id': _uuid(),
            'template_id': _uuid(),
            'kwargs': {'key0': 'arg0', 'key1': 'arg1'},
            'service_contexts': [{'network_id': _uuid()},
                                 {'network_id': _uuid()}],
            'services': [_uuid(), _uuid()],
            'status': 'ACTIVE',
        }
        instance = self.plugin.return_value
        instance.get_device.return_value = return_value

        res = self.api.get(
            _get_path(self._PATH_DEVICES, id=device_id, fmt=self.fmt))
        self.assertEqual(exc.HTTPOk.code, res.status_int)
        res = self.deserialize(res)
        self.assertIn(self._DEVICE, res)
        self.assertEqual(return_value, res[self._DEVICE])

    def test_device_delete(self):
        self._test_entity_delete(self._DEVICE)


class TackerExtensionTestCaseXML(TackerExtensionTestCase):
    fmt = 'xml'
