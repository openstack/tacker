# Copyright (c) 2012 OpenStack Foundation.
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

from oslo_config import cfg
from oslo_policy import policy as common_policy
from oslo_utils import uuidutils
from urllib import parse as urlparse
import webob
from webob import exc
import webtest

from tacker.api import api_common
from tacker.api import extensions
from tacker.api.v1 import attributes
from tacker.api.v1 import base as v2_base
from tacker.api.v1 import router
from tacker.common import exceptions as n_exc
from tacker import context
from tacker import manager
from tacker import policy
from tacker.tests import base
from tacker.tests import fake_notifier
from tacker.tests.unit import testlib_api


ROOTDIR = os.path.dirname(os.path.dirname(__file__))
EXTDIR = os.path.join(ROOTDIR, 'unit/extensions')

_uuid = uuidutils.generate_uuid


def _get_path(resource, id=None, action=None, fmt=None):
    path = '/%s' % resource

    if id is not None:
        path = path + '/%s' % id

    if action is not None:
        path = path + '/%s' % action

    if fmt is not None:
        path = path + '.%s' % fmt

    return path


class ResourceIndexTestCase(base.BaseTestCase):
    def test_index_json(self):
        index = webtest.TestApp(router.Index({'foo': 'bar'}))
        res = index.get('')

        self.assertIn('resources', res.json)
        self.assertEqual(1, len(res.json['resources']))

        resource = res.json['resources'][0]
        self.assertIn('collection', resource)
        self.assertEqual('bar', resource['collection'])

        self.assertIn('name', resource)
        self.assertEqual('foo', resource['name'])

        self.assertIn('links', resource)
        self.assertEqual(1, len(resource['links']))

        link = resource['links'][0]
        self.assertIn('href', link)
        self.assertEqual('http://localhost/bar', link['href'])
        self.assertIn('rel', link)
        self.assertEqual('self', link['rel'])


class APIv2TestBase(base.BaseTestCase):
    def setUp(self):
        super(APIv2TestBase, self).setUp()
        self.skipTest("Not ready yet")
        plugin = 'tacker.tacker_plugin_base_v2.TackerPluginBaseV2'
        # Ensure existing ExtensionManager is not used
        extensions.PluginAwareExtensionManager._instance = None
        # Create the default configurations
        self.config_parse()
        # Update the plugin
        self.setup_coreplugin(plugin)
        cfg.CONF.set_override('allow_pagination', True)
        cfg.CONF.set_override('allow_sorting', True)
        self._plugin_patcher = mock.patch(plugin, autospec=True)
        self.plugin = self._plugin_patcher.start()
        instance = self.plugin.return_value
        instance._TackerPluginBaseV2__native_pagination_support = True
        instance._TackerPluginBaseV2__native_sorting_support = True

        api = router.APIRouter()
        self.api = webtest.TestApp(api)


class _ArgMatcher(object):
    """An adapter to assist mock assertions, used to custom compare."""

    def __init__(self, cmp, obj):
        self.cmp = cmp
        self.obj = obj

    def __eq__(self, other):
        return self.cmp(self.obj, other)

    def __ne__(self, other):
        return not self.__eq__(other)


def _list_cmp(l1, l2):
    return set(l1) == set(l2)


class APIv2TestCase(APIv2TestBase):
    def _do_field_list(self, resource, base_fields):
        attr_info = attributes.RESOURCE_ATTRIBUTE_MAP[resource]
        policy_attrs = [name for (name, info) in attr_info.items()
                        if info.get('required_by_policy') or
                        info.get('primary_key')]
        fields = base_fields
        fields.extend(policy_attrs)
        return fields

    def _get_collection_kwargs(self, skipargs=None, **kwargs):
        args_list = ['filters', 'fields', 'sorts', 'limit', 'marker',
                     'page_reverse']
        if skipargs is None:
            skipargs = []
        args_dict = dict((arg, mock.ANY)
                         for arg in set(args_list) - set(skipargs))
        args_dict.update(kwargs)
        return args_dict

    def test_fields(self):
        instance = self.plugin.return_value
        instance.get_networks.return_value = []

        self.api.get(_get_path('networks'), {'fields': 'foo'})
        fields = self._do_field_list('networks', ['foo'])
        kwargs = self._get_collection_kwargs(fields=fields)
        instance.get_networks.assert_called_once_with(mock.ANY, **kwargs)

    def test_fields_multiple(self):
        instance = self.plugin.return_value
        instance.get_networks.return_value = []

        fields = self._do_field_list('networks', ['foo', 'bar'])
        self.api.get(_get_path('networks'), {'fields': ['foo', 'bar']})
        kwargs = self._get_collection_kwargs(fields=fields)
        instance.get_networks.assert_called_once_with(mock.ANY, **kwargs)

    def test_fields_multiple_with_empty(self):
        instance = self.plugin.return_value
        instance.get_networks.return_value = []

        fields = self._do_field_list('networks', ['foo'])
        self.api.get(_get_path('networks'), {'fields': ['foo', '']})
        kwargs = self._get_collection_kwargs(fields=fields)
        instance.get_networks.assert_called_once_with(mock.ANY, **kwargs)

    def test_fields_empty(self):
        instance = self.plugin.return_value
        instance.get_networks.return_value = []

        self.api.get(_get_path('networks'), {'fields': ''})
        kwargs = self._get_collection_kwargs(fields=[])
        instance.get_networks.assert_called_once_with(mock.ANY, **kwargs)

    def test_fields_multiple_empty(self):
        instance = self.plugin.return_value
        instance.get_networks.return_value = []

        self.api.get(_get_path('networks'), {'fields': ['', '']})
        kwargs = self._get_collection_kwargs(fields=[])
        instance.get_networks.assert_called_once_with(mock.ANY, **kwargs)

    def test_filters(self):
        instance = self.plugin.return_value
        instance.get_networks.return_value = []

        self.api.get(_get_path('networks'), {'name': 'bar'})
        filters = {'name': ['bar']}
        kwargs = self._get_collection_kwargs(filters=filters)
        instance.get_networks.assert_called_once_with(mock.ANY, **kwargs)

    def test_filters_empty(self):
        instance = self.plugin.return_value
        instance.get_networks.return_value = []

        self.api.get(_get_path('networks'), {'name': ''})
        filters = {}
        kwargs = self._get_collection_kwargs(filters=filters)
        instance.get_networks.assert_called_once_with(mock.ANY, **kwargs)

    def test_filters_multiple_empty(self):
        instance = self.plugin.return_value
        instance.get_networks.return_value = []

        self.api.get(_get_path('networks'), {'name': ['', '']})
        filters = {}
        kwargs = self._get_collection_kwargs(filters=filters)
        instance.get_networks.assert_called_once_with(mock.ANY, **kwargs)

    def test_filters_multiple_with_empty(self):
        instance = self.plugin.return_value
        instance.get_networks.return_value = []

        self.api.get(_get_path('networks'), {'name': ['bar', '']})
        filters = {'name': ['bar']}
        kwargs = self._get_collection_kwargs(filters=filters)
        instance.get_networks.assert_called_once_with(mock.ANY, **kwargs)

    def test_filters_multiple_values(self):
        instance = self.plugin.return_value
        instance.get_networks.return_value = []

        self.api.get(_get_path('networks'), {'name': ['bar', 'bar2']})
        filters = {'name': ['bar', 'bar2']}
        kwargs = self._get_collection_kwargs(filters=filters)
        instance.get_networks.assert_called_once_with(mock.ANY, **kwargs)

    def test_filters_multiple(self):
        instance = self.plugin.return_value
        instance.get_networks.return_value = []

        self.api.get(_get_path('networks'), {'name': 'bar',
                                             'tenant_id': 'bar2'})
        filters = {'name': ['bar'], 'tenant_id': ['bar2']}
        kwargs = self._get_collection_kwargs(filters=filters)
        instance.get_networks.assert_called_once_with(mock.ANY, **kwargs)

    def test_filters_with_fields(self):
        instance = self.plugin.return_value
        instance.get_networks.return_value = []

        self.api.get(_get_path('networks'), {'name': 'bar', 'fields': 'foo'})
        filters = {'name': ['bar']}
        fields = self._do_field_list('networks', ['foo'])
        kwargs = self._get_collection_kwargs(filters=filters, fields=fields)
        instance.get_networks.assert_called_once_with(mock.ANY, **kwargs)

    def test_filters_with_convert_to(self):
        instance = self.plugin.return_value
        instance.get_ports.return_value = []

        self.api.get(_get_path('ports'), {'admin_state_up': 'true'})
        filters = {'admin_state_up': [True]}
        kwargs = self._get_collection_kwargs(filters=filters)
        instance.get_ports.assert_called_once_with(mock.ANY, **kwargs)

    def test_filters_with_convert_list_to(self):
        instance = self.plugin.return_value
        instance.get_ports.return_value = []

        self.api.get(_get_path('ports'),
                     {'fixed_ips': ['ip_address=foo', 'subnet_id=bar']})
        filters = {'fixed_ips': {'ip_address': ['foo'], 'subnet_id': ['bar']}}
        kwargs = self._get_collection_kwargs(filters=filters)
        instance.get_ports.assert_called_once_with(mock.ANY, **kwargs)

    def test_limit(self):
        instance = self.plugin.return_value
        instance.get_networks.return_value = []

        self.api.get(_get_path('networks'),
                     {'limit': '10'})
        kwargs = self._get_collection_kwargs(limit=10)
        instance.get_networks.assert_called_once_with(mock.ANY, **kwargs)

    def test_limit_with_great_than_max_limit(self):
        cfg.CONF.set_default('pagination_max_limit', '1000')
        instance = self.plugin.return_value
        instance.get_networks.return_value = []

        self.api.get(_get_path('networks'),
                     {'limit': '1001'})
        kwargs = self._get_collection_kwargs(limit=1000)
        instance.get_networks.assert_called_once_with(mock.ANY, **kwargs)

    def test_limit_with_zero(self):
        cfg.CONF.set_default('pagination_max_limit', '1000')
        instance = self.plugin.return_value
        instance.get_networks.return_value = []

        self.api.get(_get_path('networks'), {'limit': '0'})
        kwargs = self._get_collection_kwargs(limit=1000)
        instance.get_networks.assert_called_once_with(mock.ANY, **kwargs)

    def test_limit_with_unspecific(self):
        cfg.CONF.set_default('pagination_max_limit', '1000')
        instance = self.plugin.return_value
        instance.get_networks.return_value = []

        self.api.get(_get_path('networks'))
        kwargs = self._get_collection_kwargs(limit=1000)
        instance.get_networks.assert_called_once_with(mock.ANY, **kwargs)

    def test_limit_with_negative_value(self):
        cfg.CONF.set_default('pagination_max_limit', '1000')
        instance = self.plugin.return_value
        instance.get_networks.return_value = []

        res = self.api.get(_get_path('networks'), {'limit': -1},
                           expect_errors=True)
        self.assertEqual(exc.HTTPBadRequest.code, res.status_int)

    def test_limit_with_non_integer(self):
        instance = self.plugin.return_value
        instance.get_networks.return_value = []

        res = self.api.get(_get_path('networks'),
                           {'limit': 'abc'}, expect_errors=True)
        self.assertEqual(exc.HTTPBadRequest.code, res.status_int)

    def test_limit_with_infinite_pagination_max_limit(self):
        instance = self.plugin.return_value
        instance.get_networks.return_value = []
        cfg.CONF.set_override('pagination_max_limit', 'Infinite')
        self.api.get(_get_path('networks'))
        kwargs = self._get_collection_kwargs(limit=None)
        instance.get_networks.assert_called_once_with(mock.ANY, **kwargs)

    def test_limit_with_negative_pagination_max_limit(self):
        instance = self.plugin.return_value
        instance.get_networks.return_value = []
        cfg.CONF.set_default('pagination_max_limit', '-1')
        self.api.get(_get_path('networks'))
        kwargs = self._get_collection_kwargs(limit=None)
        instance.get_networks.assert_called_once_with(mock.ANY, **kwargs)

    def test_limit_with_non_integer_pagination_max_limit(self):
        instance = self.plugin.return_value
        instance.get_networks.return_value = []
        cfg.CONF.set_default('pagination_max_limit', 'abc')
        self.api.get(_get_path('networks'))
        kwargs = self._get_collection_kwargs(limit=None)
        instance.get_networks.assert_called_once_with(mock.ANY, **kwargs)

    def test_marker(self):
        cfg.CONF.set_override('pagination_max_limit', '1000')
        instance = self.plugin.return_value
        instance.get_networks.return_value = []
        marker = _uuid()
        self.api.get(_get_path('networks'),
                     {'marker': marker})
        kwargs = self._get_collection_kwargs(limit=1000, marker=marker)
        instance.get_networks.assert_called_once_with(mock.ANY, **kwargs)

    def test_page_reverse(self):
        calls = []
        instance = self.plugin.return_value
        instance.get_networks.return_value = []
        self.api.get(_get_path('networks'),
                     {'page_reverse': 'True'})
        kwargs = self._get_collection_kwargs(page_reverse=True)
        calls.append(mock.call.get_networks(mock.ANY, **kwargs))
        instance.get_networks.assert_called_once_with(mock.ANY, **kwargs)

        instance = self.plugin.return_value
        instance.get_networks.return_value = []
        self.api.get(_get_path('networks'),
                     {'page_reverse': 'False'})
        kwargs = self._get_collection_kwargs(page_reverse=False)
        calls.append(mock.call.get_networks(mock.ANY, **kwargs))

    def test_page_reverse_with_non_bool(self):
        instance = self.plugin.return_value
        instance.get_networks.return_value = []

        self.api.get(_get_path('networks'),
                     {'page_reverse': 'abc'})
        kwargs = self._get_collection_kwargs(page_reverse=False)
        instance.get_networks.assert_called_once_with(mock.ANY, **kwargs)

    def test_page_reverse_with_unspecific(self):
        instance = self.plugin.return_value
        instance.get_networks.return_value = []

        self.api.get(_get_path('networks'))
        kwargs = self._get_collection_kwargs(page_reverse=False)
        instance.get_networks.assert_called_once_with(mock.ANY, **kwargs)

    def test_sort(self):
        instance = self.plugin.return_value
        instance.get_networks.return_value = []

        self.api.get(_get_path('networks'),
                     {'sort_key': ['name', 'admin_state_up'],
                      'sort_dir': ['desc', 'asc']})
        kwargs = self._get_collection_kwargs(sorts=[('name', False),
                                                    ('admin_state_up', True),
                                                    ('id', True)])
        instance.get_networks.assert_called_once_with(mock.ANY, **kwargs)

    def test_sort_with_primary_key(self):
        instance = self.plugin.return_value
        instance.get_networks.return_value = []

        self.api.get(_get_path('networks'),
                     {'sort_key': ['name', 'admin_state_up', 'id'],
                      'sort_dir': ['desc', 'asc', 'desc']})
        kwargs = self._get_collection_kwargs(sorts=[('name', False),
                                                    ('admin_state_up', True),
                                                    ('id', False)])
        instance.get_networks.assert_called_once_with(mock.ANY, **kwargs)

    def test_sort_without_direction(self):
        instance = self.plugin.return_value
        instance.get_networks.return_value = []

        res = self.api.get(_get_path('networks'), {'sort_key': ['name']},
                           expect_errors=True)
        self.assertEqual(exc.HTTPBadRequest.code, res.status_int)

    def test_sort_with_invalid_attribute(self):
        instance = self.plugin.return_value
        instance.get_networks.return_value = []

        res = self.api.get(_get_path('networks'),
                           {'sort_key': 'abc',
                            'sort_dir': 'asc'},
                           expect_errors=True)
        self.assertEqual(exc.HTTPBadRequest.code, res.status_int)

    def test_sort_with_invalid_dirs(self):
        instance = self.plugin.return_value
        instance.get_networks.return_value = []

        res = self.api.get(_get_path('networks'),
                           {'sort_key': 'name',
                            'sort_dir': 'abc'},
                           expect_errors=True)
        self.assertEqual(res.status_int, exc.HTTPBadRequest.code)

    def test_emulated_sort(self):
        instance = self.plugin.return_value
        instance._TackerPluginBaseV2__native_pagination_support = False
        instance._TackerPluginBaseV2__native_sorting_support = False
        instance.get_networks.return_value = []
        api = webtest.TestApp(router.APIRouter())
        api.get(_get_path('networks'), {'sort_key': ['name', 'status'],
                                        'sort_dir': ['desc', 'asc']})
        kwargs = self._get_collection_kwargs(
            skipargs=['sorts', 'limit', 'marker', 'page_reverse'])
        instance.get_networks.assert_called_once_with(mock.ANY, **kwargs)

    def test_emulated_sort_without_sort_field(self):
        instance = self.plugin.return_value
        instance._TackerPluginBaseV2__native_pagination_support = False
        instance._TackerPluginBaseV2__native_sorting_support = False
        instance.get_networks.return_value = []
        api = webtest.TestApp(router.APIRouter())
        api.get(_get_path('networks'), {'sort_key': ['name', 'status'],
                                        'sort_dir': ['desc', 'asc'],
                                        'fields': ['subnets']})
        kwargs = self._get_collection_kwargs(
            skipargs=['sorts', 'limit', 'marker', 'page_reverse'],
            fields=_ArgMatcher(_list_cmp, ['name',
                                           'status',
                                           'id',
                                           'subnets',
                                           'shared',
                                           'tenant_id']))
        instance.get_networks.assert_called_once_with(mock.ANY, **kwargs)

    def test_emulated_pagination(self):
        instance = self.plugin.return_value
        instance._TackerPluginBaseV2__native_pagination_support = False
        instance.get_networks.return_value = []
        api = webtest.TestApp(router.APIRouter())
        api.get(_get_path('networks'), {'limit': 10,
                                        'marker': 'foo',
                                        'page_reverse': False})
        kwargs = self._get_collection_kwargs(skipargs=['limit',
                                                       'marker',
                                                       'page_reverse'])
        instance.get_networks.assert_called_once_with(mock.ANY, **kwargs)

    def test_native_pagination_without_native_sorting(self):
        instance = self.plugin.return_value
        instance._TackerPluginBaseV2__native_sorting_support = False
        self.assertRaises(n_exc.Invalid, router.APIRouter)

    def test_native_pagination_without_allow_sorting(self):
        cfg.CONF.set_override('allow_sorting', False)
        instance = self.plugin.return_value
        instance.get_networks.return_value = []
        api = webtest.TestApp(router.APIRouter())
        api.get(_get_path('networks'),
                {'sort_key': ['name', 'admin_state_up'],
                 'sort_dir': ['desc', 'asc']})
        kwargs = self._get_collection_kwargs(sorts=[('name', False),
                                                    ('admin_state_up', True),
                                                    ('id', True)])
        instance.get_networks.assert_called_once_with(mock.ANY, **kwargs)


# Note: since all resources use the same controller and validation
# logic, we actually get really good coverage from testing just networks.
class JSONV2TestCase(APIv2TestBase, testlib_api.WebTestCase):
    def setUp(self):
        super(JSONV2TestCase, self).setUp()
        self.skipTest("Not ready yet")

    def _test_list(self, req_tenant_id, real_tenant_id):
        env = {}
        if req_tenant_id:
            env = {'tacker.context': context.Context('', req_tenant_id)}
        input_dict = {'id': uuidutils.generate_uuid(),
                      'name': 'net1',
                      'admin_state_up': True,
                      'status': "ACTIVE",
                      'tenant_id': real_tenant_id,
                      'shared': False,
                      'subnets': []}
        return_value = [input_dict]
        instance = self.plugin.return_value
        instance.get_networks.return_value = return_value

        res = self.api.get(_get_path('networks',
                                     fmt=self.fmt), extra_environ=env)
        res = self.deserialize(res)
        self.assertIn('networks', res)
        if not req_tenant_id or req_tenant_id == real_tenant_id:
            # expect full list returned
            self.assertEqual(1, len(res['networks']))
            output_dict = res['networks'][0]
            input_dict['shared'] = False
            self.assertEqual(len(input_dict), len(output_dict))
            for k, v in input_dict.items():
                self.assertEqual(v, output_dict[k])
        else:
            # expect no results
            self.assertEqual(0, len(res['networks']))

    def test_list_noauth(self):
        self._test_list(None, _uuid())

    def test_list_keystone(self):
        tenant_id = _uuid()
        self._test_list(tenant_id, tenant_id)

    def test_list_keystone_bad(self):
        tenant_id = _uuid()
        self._test_list(tenant_id + "bad", tenant_id)

    def test_list_pagination(self):
        id1 = str(_uuid())
        id2 = str(_uuid())
        input_dict1 = {'id': id1,
                       'name': 'net1',
                       'admin_state_up': True,
                       'status': "ACTIVE",
                       'tenant_id': '',
                       'shared': False,
                       'subnets': []}
        input_dict2 = {'id': id2,
                       'name': 'net2',
                       'admin_state_up': True,
                       'status': "ACTIVE",
                       'tenant_id': '',
                       'shared': False,
                       'subnets': []}
        return_value = [input_dict1, input_dict2]
        instance = self.plugin.return_value
        instance.get_networks.return_value = return_value
        params = {'limit': ['2'],
                  'marker': [str(_uuid())],
                  'sort_key': ['name'],
                  'sort_dir': ['asc']}
        res = self.api.get(_get_path('networks'),
                           params=params).json

        self.assertEqual(2, len(res['networks']))
        self.assertEqual(sorted([id1, id2]),
                         sorted([res['networks'][0]['id'],
                                res['networks'][1]['id']]))

        self.assertIn('networks_links', res)
        next_links = []
        previous_links = []
        for r in res['networks_links']:
            if r['rel'] == 'next':
                next_links.append(r)
            if r['rel'] == 'previous':
                previous_links.append(r)
        self.assertEqual(1, len(next_links))
        self.assertEqual(1, len(previous_links))

        url = urlparse.urlparse(next_links[0]['href'])
        self.assertEqual(_get_path('networks'), url.path)
        params['marker'] = [id2]
        self.assertEqual(params, urlparse.parse_qs(url.query))

        url = urlparse.urlparse(previous_links[0]['href'])
        self.assertEqual(_get_path('networks'), url.path)
        params['marker'] = [id1]
        params['page_reverse'] = ['True']
        self.assertEqual(params, urlparse.parse_qs(url.query))

    def test_list_pagination_with_last_page(self):
        id = str(_uuid())
        input_dict = {'id': id,
                      'name': 'net1',
                      'admin_state_up': True,
                      'status': "ACTIVE",
                      'tenant_id': '',
                      'shared': False,
                      'subnets': []}
        return_value = [input_dict]
        instance = self.plugin.return_value
        instance.get_networks.return_value = return_value
        params = {'limit': ['2'],
                  'marker': str(_uuid())}
        res = self.api.get(_get_path('networks'),
                           params=params).json

        self.assertEqual(1, len(res['networks']))
        self.assertEqual(id, res['networks'][0]['id'])

        self.assertIn('networks_links', res)
        previous_links = []
        for r in res['networks_links']:
            self.assertNotEqual(r['rel'], 'next')
            if r['rel'] == 'previous':
                previous_links.append(r)
        self.assertEqual(1, len(previous_links))

        url = urlparse.urlparse(previous_links[0]['href'])
        self.assertEqual(_get_path('networks'), url.path)
        expect_params = params.copy()
        expect_params['marker'] = [id]
        expect_params['page_reverse'] = ['True']
        self.assertEqual(expect_params, urlparse.parse_qs(url.query))

    def test_list_pagination_with_empty_page(self):
        return_value = []
        instance = self.plugin.return_value
        instance.get_networks.return_value = return_value
        params = {'limit': ['2'],
                  'marker': str(_uuid())}
        res = self.api.get(_get_path('networks'),
                           params=params).json

        self.assertEqual([], res['networks'])

        previous_links = []
        if 'networks_links' in res:
            for r in res['networks_links']:
                self.assertNotEqual(r['rel'], 'next')
                if r['rel'] == 'previous':
                    previous_links.append(r)
        self.assertEqual(1, len(previous_links))

        url = urlparse.urlparse(previous_links[0]['href'])
        self.assertEqual(_get_path('networks'), url.path)
        expect_params = params.copy()
        del expect_params['marker']
        expect_params['page_reverse'] = ['True']
        self.assertEqual(expect_params, urlparse.parse_qs(url.query))

    def test_list_pagination_reverse_with_last_page(self):
        id = str(_uuid())
        input_dict = {'id': id,
                      'name': 'net1',
                      'admin_state_up': True,
                      'status': "ACTIVE",
                      'tenant_id': '',
                      'shared': False,
                      'subnets': []}
        return_value = [input_dict]
        instance = self.plugin.return_value
        instance.get_networks.return_value = return_value
        params = {'limit': ['2'],
                  'marker': [str(_uuid())],
                  'page_reverse': ['True']}
        res = self.api.get(_get_path('networks'),
                           params=params).json

        self.assertEqual(1, len(res['networks']))
        self.assertEqual(id, res['networks'][0]['id'])

        self.assertIn('networks_links', res)
        next_links = []
        for r in res['networks_links']:
            self.assertNotEqual(r['rel'], 'previous')
            if r['rel'] == 'next':
                next_links.append(r)
        self.assertEqual(1, len(next_links))

        url = urlparse.urlparse(next_links[0]['href'])
        self.assertEqual(_get_path('networks'), url.path)
        expected_params = params.copy()
        del expected_params['page_reverse']
        expected_params['marker'] = [id]
        self.assertEqual(expected_params,
                         urlparse.parse_qs(url.query))

    def test_list_pagination_reverse_with_empty_page(self):
        return_value = []
        instance = self.plugin.return_value
        instance.get_networks.return_value = return_value
        params = {'limit': ['2'],
                  'marker': [str(_uuid())],
                  'page_reverse': ['True']}
        res = self.api.get(_get_path('networks'),
                           params=params).json
        self.assertEqual([], res['networks'])

        next_links = []
        if 'networks_links' in res:
            for r in res['networks_links']:
                self.assertNotEqual(r['rel'], 'previous')
                if r['rel'] == 'next':
                    next_links.append(r)
        self.assertEqual(1, len(next_links))

        url = urlparse.urlparse(next_links[0]['href'])
        self.assertEqual(_get_path('networks'), url.path)
        expect_params = params.copy()
        del expect_params['marker']
        del expect_params['page_reverse']
        self.assertEqual(expect_params, urlparse.parse_qs(url.query))

    def test_create(self):
        net_id = _uuid()
        data = {'network': {'name': 'net1', 'admin_state_up': True,
                            'tenant_id': _uuid()}}
        return_value = {'subnets': [], 'status': "ACTIVE",
                        'id': net_id}
        return_value.update(data['network'].copy())

        instance = self.plugin.return_value
        instance.create_network.return_value = return_value
        instance.get_networks_count.return_value = 0

        res = self.api.post(_get_path('networks', fmt=self.fmt),
                            self.serialize(data),
                            content_type='application/' + self.fmt)
        self.assertEqual(exc.HTTPCreated.code, res.status_int)
        res = self.deserialize(res)
        self.assertIn('network', res)
        net = res['network']
        self.assertEqual(net_id, net['id'])
        self.assertEqual("ACTIVE", net['status'])

    def test_create_use_defaults(self):
        net_id = _uuid()
        initial_input = {'network': {'name': 'net1', 'tenant_id': _uuid()}}
        full_input = {'network': {'admin_state_up': True,
                                  'shared': False}}
        full_input['network'].update(initial_input['network'])

        return_value = {'id': net_id, 'status': "ACTIVE"}
        return_value.update(full_input['network'])

        instance = self.plugin.return_value
        instance.create_network.return_value = return_value
        instance.get_networks_count.return_value = 0

        res = self.api.post(_get_path('networks', fmt=self.fmt),
                            self.serialize(initial_input),
                            content_type='application/' + self.fmt)
        instance.create_network.assert_called_with(mock.ANY,
                                                   network=full_input)
        self.assertEqual(exc.HTTPCreated.code, res.status_int)
        res = self.deserialize(res)
        self.assertIn('network', res)
        net = res['network']
        self.assertEqual(net_id, net['id'])
        self.assertEqual(True, net['admin_state_up'])
        self.assertEqual("ACTIVE", net['status'])

    def test_create_no_keystone_env(self):
        data = {'name': 'net1'}
        res = self.api.post(_get_path('networks', fmt=self.fmt),
                            self.serialize(data),
                            content_type='application/' + self.fmt,
                            expect_errors=True)
        self.assertEqual(exc.HTTPBadRequest.code, res.status_int)

    def test_create_with_keystone_env(self):
        tenant_id = _uuid()
        net_id = _uuid()
        env = {'tacker.context': context.Context('', tenant_id)}
        # tenant_id should be fetched from env
        initial_input = {'network': {'name': 'net1'}}
        full_input = {'network': {'admin_state_up': True,
                      'shared': False, 'tenant_id': tenant_id}}
        full_input['network'].update(initial_input['network'])

        return_value = {'id': net_id, 'status': "ACTIVE"}
        return_value.update(full_input['network'])

        instance = self.plugin.return_value
        instance.create_network.return_value = return_value
        instance.get_networks_count.return_value = 0

        res = self.api.post(_get_path('networks', fmt=self.fmt),
                            self.serialize(initial_input),
                            content_type='application/' + self.fmt,
                            extra_environ=env)

        instance.create_network.assert_called_with(mock.ANY,
                                                   network=full_input)
        self.assertEqual(exc.HTTPCreated.code, res.status_int)

    def test_create_bad_keystone_tenant(self):
        tenant_id = _uuid()
        data = {'network': {'name': 'net1', 'tenant_id': tenant_id}}
        env = {'tacker.context': context.Context('', tenant_id + "bad")}
        res = self.api.post(_get_path('networks', fmt=self.fmt),
                            self.serialize(data),
                            content_type='application/' + self.fmt,
                            expect_errors=True,
                            extra_environ=env)
        self.assertEqual(exc.HTTPBadRequest.code, res.status_int)

    def test_create_no_body(self):
        data = {'whoa': None}
        res = self.api.post(_get_path('networks', fmt=self.fmt),
                            self.serialize(data),
                            content_type='application/' + self.fmt,
                            expect_errors=True)
        self.assertEqual(exc.HTTPBadRequest.code, res.status_int)

    def test_create_no_resource(self):
        data = {}
        res = self.api.post(_get_path('networks', fmt=self.fmt),
                            self.serialize(data),
                            content_type='application/' + self.fmt,
                            expect_errors=True)
        self.assertEqual(exc.HTTPBadRequest.code, res.status_int)

    def test_create_missing_attr(self):
        data = {'port': {'what': 'who', 'tenant_id': _uuid()}}
        res = self.api.post(_get_path('ports', fmt=self.fmt),
                            self.serialize(data),
                            content_type='application/' + self.fmt,
                            expect_errors=True)
        self.assertEqual(400, res.status_int)

    def test_create_readonly_attr(self):
        data = {'network': {'name': 'net1', 'tenant_id': _uuid(),
                            'status': "ACTIVE"}}
        res = self.api.post(_get_path('networks', fmt=self.fmt),
                            self.serialize(data),
                            content_type='application/' + self.fmt,
                            expect_errors=True)
        self.assertEqual(400, res.status_int)

    def test_create_bulk(self):
        data = {'networks': [{'name': 'net1',
                              'admin_state_up': True,
                              'tenant_id': _uuid()},
                             {'name': 'net2',
                              'admin_state_up': True,
                              'tenant_id': _uuid()}]}

        def side_effect(context, network):
            net = network.copy()
            net['network'].update({'subnets': []})
            return net['network']

        instance = self.plugin.return_value
        instance.create_network.side_effect = side_effect
        instance.get_networks_count.return_value = 0
        res = self.api.post(_get_path('networks', fmt=self.fmt),
                            self.serialize(data),
                            content_type='application/' + self.fmt)
        self.assertEqual(exc.HTTPCreated.code, res.status_int)

    def test_create_bulk_no_networks(self):
        data = {'networks': []}
        res = self.api.post(_get_path('networks', fmt=self.fmt),
                            self.serialize(data),
                            content_type='application/' + self.fmt,
                            expect_errors=True)
        self.assertEqual(exc.HTTPBadRequest.code, res.status_int)

    def test_create_bulk_missing_attr(self):
        data = {'ports': [{'what': 'who', 'tenant_id': _uuid()}]}
        res = self.api.post(_get_path('ports', fmt=self.fmt),
                            self.serialize(data),
                            content_type='application/' + self.fmt,
                            expect_errors=True)
        self.assertEqual(400, res.status_int)

    def test_create_bulk_partial_body(self):
        data = {'ports': [{'vnf_id': 'vnf_1',
                           'tenant_id': _uuid()},
                          {'tenant_id': _uuid()}]}
        res = self.api.post(_get_path('ports', fmt=self.fmt),
                            self.serialize(data),
                            content_type='application/' + self.fmt,
                            expect_errors=True)
        self.assertEqual(400, res.status_int)

    def test_create_attr_not_specified(self):
        net_id = _uuid()
        tenant_id = _uuid()
        vnf_id = _uuid()
        initial_input = {'port': {'name': '', 'network_id': net_id,
                                  'tenant_id': tenant_id,
                                  'vnf_id': vnf_id,
                                  'admin_state_up': True}}
        full_input = {'port': {'admin_state_up': True,
                               'mac_address': attributes.ATTR_NOT_SPECIFIED,
                               'fixed_ips': attributes.ATTR_NOT_SPECIFIED,
                               'vnf_owner': ''}}
        full_input['port'].update(initial_input['port'])
        return_value = {'id': _uuid(), 'status': 'ACTIVE',
                        'admin_state_up': True,
                        'mac_address': 'ca:fe:de:ad:be:ef',
                        'vnf_id': vnf_id,
                        'vnf_owner': ''}
        return_value.update(initial_input['port'])

        instance = self.plugin.return_value
        instance.get_network.return_value = {'tenant_id': str(tenant_id)}
        instance.get_ports_count.return_value = 1
        instance.create_port.return_value = return_value
        res = self.api.post(_get_path('ports', fmt=self.fmt),
                            self.serialize(initial_input),
                            content_type='application/' + self.fmt)
        instance.create_port.assert_called_with(mock.ANY, port=full_input)
        self.assertEqual(exc.HTTPCreated.code, res.status_int)
        res = self.deserialize(res)
        self.assertIn('port', res)
        port = res['port']
        self.assertEqual(net_id, port['network_id'])
        self.assertEqual('ca:fe:de:ad:be:ef', port['mac_address'])

    def test_create_return_extra_attr(self):
        net_id = _uuid()
        data = {'network': {'name': 'net1', 'admin_state_up': True,
                            'tenant_id': _uuid()}}
        return_value = {'subnets': [], 'status': "ACTIVE",
                        'id': net_id, 'v2attrs:something': "123"}
        return_value.update(data['network'].copy())

        instance = self.plugin.return_value
        instance.create_network.return_value = return_value
        instance.get_networks_count.return_value = 0

        res = self.api.post(_get_path('networks', fmt=self.fmt),
                            self.serialize(data),
                            content_type='application/' + self.fmt)
        self.assertEqual(exc.HTTPCreated.code, res.status_int)
        res = self.deserialize(res)
        self.assertIn('network', res)
        net = res['network']
        self.assertEqual(net_id, net['id'])
        self.assertEqual("ACTIVE", net['status'])
        self.assertNotIn('v2attrs:something', net)

    def test_fields(self):
        return_value = {'name': 'net1', 'admin_state_up': True,
                        'subnets': []}

        instance = self.plugin.return_value
        instance.get_network.return_value = return_value

        self.api.get(_get_path('networks',
                               id=uuidutils.generate_uuid(),
                               fmt=self.fmt))

    def _test_delete(self, req_tenant_id, real_tenant_id, expected_code,
                     expect_errors=False):
        env = {}
        if req_tenant_id:
            env = {'tacker.context': context.Context('', req_tenant_id)}
        instance = self.plugin.return_value
        instance.get_network.return_value = {'tenant_id': real_tenant_id,
                                             'shared': False}
        instance.delete_network.return_value = None

        res = self.api.delete(_get_path('networks',
                                        id=uuidutils.generate_uuid(),
                                        fmt=self.fmt),
                              extra_environ=env,
                              expect_errors=expect_errors)
        self.assertEqual(expected_code, res.status_int)

    def test_delete_noauth(self):
        self._test_delete(None, _uuid(), exc.HTTPNoContent.code)

    def test_delete_keystone(self):
        tenant_id = _uuid()
        self._test_delete(tenant_id, tenant_id, exc.HTTPNoContent.code)

    def test_delete_keystone_bad_tenant(self):
        tenant_id = _uuid()
        self._test_delete(tenant_id + "bad", tenant_id,
                          exc.HTTPNotFound.code, expect_errors=True)

    def _test_get(self, req_tenant_id, real_tenant_id, expected_code,
                  expect_errors=False):
        env = {}
        shared = False
        if req_tenant_id:
            env = {'tacker.context': context.Context('', req_tenant_id)}
            if req_tenant_id.endswith('another'):
                shared = True
                env['tacker.context'].roles = ['tenant_admin']

        data = {'tenant_id': real_tenant_id, 'shared': shared}
        instance = self.plugin.return_value
        instance.get_network.return_value = data

        res = self.api.get(_get_path('networks',
                                     id=uuidutils.generate_uuid(),
                                     fmt=self.fmt),
                           extra_environ=env,
                           expect_errors=expect_errors)
        self.assertEqual(expected_code, res.status_int)
        return res

    def test_get_noauth(self):
        self._test_get(None, _uuid(), 200)

    def test_get_keystone(self):
        tenant_id = _uuid()
        self._test_get(tenant_id, tenant_id, 200)

    def test_get_keystone_bad_tenant(self):
        tenant_id = _uuid()
        self._test_get(tenant_id + "bad", tenant_id,
                       exc.HTTPNotFound.code, expect_errors=True)

    def test_get_keystone_shared_network(self):
        tenant_id = _uuid()
        self._test_get(tenant_id + "another", tenant_id, 200)

    def test_get_keystone_strip_admin_only_attribute(self):
        tenant_id = _uuid()
        # Inject rule in policy engine
        policy.init()
        common_policy._rules['get_network:name'] = common_policy.parse_rule(
            "rule:admin_only")
        res = self._test_get(tenant_id, tenant_id, 200)
        res = self.deserialize(res)
        try:
            self.assertNotIn('name', res['network'])
        finally:
            del common_policy._rules['get_network:name']

    def _test_update(self, req_tenant_id, real_tenant_id, expected_code,
                     expect_errors=False):
        env = {}
        if req_tenant_id:
            env = {'tacker.context': context.Context('', req_tenant_id)}
        # leave out 'name' field intentionally
        data = {'network': {'admin_state_up': True}}
        return_value = {'subnets': []}
        return_value.update(data['network'].copy())

        instance = self.plugin.return_value
        instance.get_network.return_value = {'tenant_id': real_tenant_id,
                                             'shared': False}
        instance.update_network.return_value = return_value

        res = self.api.put(_get_path('networks',
                                     id=uuidutils.generate_uuid(),
                                     fmt=self.fmt),
                           self.serialize(data),
                           extra_environ=env,
                           expect_errors=expect_errors)
        #  Ensure id attribute is included in fields returned by GET call
        #  in update procedure.
        self.assertEqual(1, instance.get_network.call_count)
        self.assertIn('id', instance.get_network.call_args[1]['fields'])
        self.assertEqual(expected_code, res.status_int)

    def test_update_noauth(self):
        self._test_update(None, _uuid(), 200)

    def test_update_keystone(self):
        tenant_id = _uuid()
        self._test_update(tenant_id, tenant_id, 200)

    def test_update_keystone_bad_tenant(self):
        tenant_id = _uuid()
        self._test_update(tenant_id + "bad", tenant_id,
                          exc.HTTPNotFound.code, expect_errors=True)

    def test_update_readonly_field(self):
        data = {'network': {'status': "NANANA"}}
        res = self.api.put(_get_path('networks', id=_uuid()),
                           self.serialize(data),
                           content_type='application/' + self.fmt,
                           expect_errors=True)
        self.assertEqual(400, res.status_int)

    def test_invalid_attribute_field(self):
        data = {'network': {'invalid_key1': "foo1", 'invalid_key2': "foo2"}}
        res = self.api.put(_get_path('networks', id=_uuid()),
                           self.serialize(data),
                           content_type='application/' + self.fmt,
                           expect_errors=True)
        self.assertEqual(res.status_int, 400)


class SubresourceTest(base.BaseTestCase):
    def setUp(self):
        super(SubresourceTest, self).setUp()
        self.skipTest("Not ready yet")

        plugin = 'tacker.tests.unit.test_api_v2.TestSubresourcePlugin'
        extensions.PluginAwareExtensionManager._instance = None

        # Save the global RESOURCE_ATTRIBUTE_MAP
        self.saved_attr_map = {}
        for resource, attrs in (attributes.RESOURCE_ATTRIBUTE_MAP).items():
            self.saved_attr_map[resource] = attrs.copy()

        self.config_parse()
        self.setup_coreplugin(plugin)

        self._plugin_patcher = mock.patch(plugin, autospec=True)
        self.plugin = self._plugin_patcher.start()

        router.SUB_RESOURCES['dummy'] = {
            'collection_name': 'dummies',
            'parent': {'collection_name': 'networks',
                       'member_name': 'network'}
        }
        attributes.RESOURCE_ATTRIBUTE_MAP['dummies'] = {
            'foo': {'allow_post': True, 'allow_put': True,
                    'validate': {'type:string': None},
                    'default': '', 'is_visible': True},
            'tenant_id': {'allow_post': True, 'allow_put': False,
                          'validate': {'type:string': None},
                          'required_by_policy': True,
                          'is_visible': True}
        }
        api = router.APIRouter()
        self.api = webtest.TestApp(api)

    def tearDown(self):
        router.SUB_RESOURCES = {}
        # Restore the global RESOURCE_ATTRIBUTE_MAP
        attributes.RESOURCE_ATTRIBUTE_MAP = self.saved_attr_map
        super(SubresourceTest, self).tearDown()

    def test_index_sub_resource(self):
        instance = self.plugin.return_value

        self.api.get('/networks/id1/dummies')
        instance.get_network_dummies.assert_called_once_with(mock.ANY,
                                                             filters=mock.ANY,
                                                             fields=mock.ANY,
                                                             network_id='id1')

    def test_show_sub_resource(self):
        instance = self.plugin.return_value

        dummy_id = _uuid()
        self.api.get('/networks/id1' + _get_path('dummies', id=dummy_id))
        instance.get_network_dummy.assert_called_once_with(mock.ANY,
                                                           dummy_id,
                                                           network_id='id1',
                                                           fields=mock.ANY)

    def test_create_sub_resource(self):
        instance = self.plugin.return_value

        body = {'dummy': {'foo': 'bar', 'tenant_id': _uuid()}}
        self.api.post_json('/networks/id1/dummies', body)
        instance.create_network_dummy.assert_called_once_with(mock.ANY,
                                                              network_id='id1',
                                                              dummy=body)

    def test_update_sub_resource(self):
        instance = self.plugin.return_value

        dummy_id = _uuid()
        body = {'dummy': {'foo': 'bar'}}
        self.api.put_json('/networks/id1' + _get_path('dummies', id=dummy_id),
                          body)
        instance.update_network_dummy.assert_called_once_with(mock.ANY,
                                                              dummy_id,
                                                              network_id='id1',
                                                              dummy=body)

    def test_delete_sub_resource(self):
        instance = self.plugin.return_value

        dummy_id = _uuid()
        self.api.delete('/networks/id1' + _get_path('dummies', id=dummy_id))
        instance.delete_network_dummy.assert_called_once_with(mock.ANY,
                                                              dummy_id,
                                                              network_id='id1')


class V2Views(base.BaseTestCase):

    def setUp(self):
        super(V2Views, self).setUp()
        self.skipTest("Not ready yet")

    def _view(self, keys, collection, resource):
        data = dict((key, 'value') for key in keys)
        data['fake'] = 'value'
        attr_info = attributes.RESOURCE_ATTRIBUTE_MAP[collection]
        controller = v2_base.Controller(None, collection, resource, attr_info)
        res = controller._view(context.get_admin_context(), data)
        self.assertNotIn('fake', res)
        for key in keys:
            self.assertIn(key, res)

    def test_network(self):
        keys = ('id', 'name', 'subnets', 'admin_state_up', 'status',
                'tenant_id')
        self._view(keys, 'networks', 'network')

    def test_port(self):
        keys = ('id', 'network_id', 'mac_address', 'fixed_ips',
                'vnf_id', 'admin_state_up', 'tenant_id', 'status')
        self._view(keys, 'ports', 'port')

    def test_subnet(self):
        keys = ('id', 'network_id', 'tenant_id', 'gateway_ip',
                'ip_version', 'cidr', 'enable_dhcp')
        self._view(keys, 'subnets', 'subnet')


class NotificationTest(APIv2TestBase):

    def setUp(self):
        super(NotificationTest, self).setUp()
        self.skipTest("Not ready yet")
        fake_notifier.reset()

    def _resource_op_notifier(self, opname, resource, expected_errors=False):
        initial_input = {resource: {'name': 'myname'}}
        instance = self.plugin.return_value
        instance.get_networks.return_value = initial_input
        instance.get_networks_count.return_value = 0
        expected_code = exc.HTTPCreated.code
        if opname == 'create':
            initial_input[resource]['tenant_id'] = _uuid()
            res = self.api.post_json(
                _get_path('networks'),
                initial_input, expect_errors=expected_errors)
        if opname == 'update':
            res = self.api.put_json(
                _get_path('networks', id=_uuid()),
                initial_input, expect_errors=expected_errors)
            expected_code = exc.HTTPOk.code
        if opname == 'delete':
            initial_input[resource]['tenant_id'] = _uuid()
            res = self.api.delete(
                _get_path('networks', id=_uuid()),
                expect_errors=expected_errors)
            expected_code = exc.HTTPNoContent.code

        expected_events = ('.'.join([resource, opname, "start"]),
                           '.'.join([resource, opname, "end"]))
        self.assertEqual(len(expected_events),
                         len(fake_notifier.NOTIFICATIONS))
        for msg, event in zip(fake_notifier.NOTIFICATIONS, expected_events):
            self.assertEqual('INFO', msg['priority'])
            self.assertEqual(event, msg['event_type'])

        self.assertEqual(expected_code, res.status_int)

    def test_network_create_notifer(self):
        self._resource_op_notifier('create', 'network')

    def test_network_delete_notifer(self):
        self._resource_op_notifier('delete', 'network')

    def test_network_update_notifer(self):
        self._resource_op_notifier('update', 'network')


class ExtensionTestCase(base.BaseTestCase):
    def setUp(self):
        super(ExtensionTestCase, self).setUp()
        self.skipTest("Not ready yet")
        plugin = 'tacker.tacker_plugin_base_v2.TackerPluginBaseV2'

        # Ensure existing ExtensionManager is not used
        extensions.PluginAwareExtensionManager._instance = None

        # Save the global RESOURCE_ATTRIBUTE_MAP
        self.saved_attr_map = {}
        for resource, attrs in (attributes.RESOURCE_ATTRIBUTE_MAP).items():
            self.saved_attr_map[resource] = attrs.copy()

        # Create the default configurations
        self.config_parse()

        # Update the plugin and extensions path
        self.setup_coreplugin(plugin)
        cfg.CONF.set_override('api_extensions_path', EXTDIR)

        self._plugin_patcher = mock.patch(plugin, autospec=True)
        self.plugin = self._plugin_patcher.start()

        # Instantiate mock plugin and enable the V2attributes extension
        manager.TackerManager.get_plugin().supported_extension_aliases = (
            ["v2attrs"])

        api = router.APIRouter()
        self.api = webtest.TestApp(api)

    def tearDown(self):
        super(ExtensionTestCase, self).tearDown()
        self.api = None
        self.plugin = None
        # Restore the global RESOURCE_ATTRIBUTE_MAP
        attributes.RESOURCE_ATTRIBUTE_MAP = self.saved_attr_map

    def test_extended_create(self):
        net_id = _uuid()
        initial_input = {'network': {'name': 'net1', 'tenant_id': _uuid(),
                                     'v2attrs:something_else': "abc"}}
        data = {'network': {'admin_state_up': True, 'shared': False}}
        data['network'].update(initial_input['network'])

        return_value = {'subnets': [], 'status': "ACTIVE",
                        'id': net_id,
                        'v2attrs:something': "123"}
        return_value.update(data['network'].copy())

        instance = self.plugin.return_value
        instance.create_network.return_value = return_value
        instance.get_networks_count.return_value = 0

        res = self.api.post_json(_get_path('networks'), initial_input)

        instance.create_network.assert_called_with(mock.ANY,
                                                   network=data)
        self.assertEqual(exc.HTTPCreated.code, res.status_int)
        self.assertIn('network', res.json)
        net = res.json['network']
        self.assertEqual(net_id, net['id'])
        self.assertEqual("ACTIVE", net['status'])
        self.assertEqual("123", net['v2attrs:something'])
        self.assertNotIn('v2attrs:something_else', net)


class TestSubresourcePlugin(object):
    def get_network_dummies(self, context, network_id,
                            filters=None, fields=None):
        return []

    def get_network_dummy(self, context, id, network_id,
                          fields=None):
        return {}

    def create_network_dummy(self, context, network_id, dummy):
        return {}

    def update_network_dummy(self, context, id, network_id, dummy):
        return {}

    def delete_network_dummy(self, context, id, network_id):
        return


class ListArgsTestCase(base.BaseTestCase):
    def test_list_args(self):
        path = '/?fields=4&foo=3&fields=2&bar=1'
        request = webob.Request.blank(path)
        expect_val = ['2', '4']
        actual_val = api_common.list_args(request, 'fields')
        self.assertEqual(expect_val, sorted(actual_val))

    def test_list_args_with_empty(self):
        path = '/?foo=4&bar=3&baz=2&qux=1'
        request = webob.Request.blank(path)
        self.assertEqual([], api_common.list_args(request, 'fields'))


class FiltersTestCase(base.BaseTestCase):
    def setUp(self):
        super(FiltersTestCase, self).setUp()
        self.skipTest("Not ready yet")

    def test_all_skip_args(self):
        path = '/?fields=4&fields=3&fields=2&fields=1'
        request = webob.Request.blank(path)
        self.assertEqual({}, api_common.get_filters(request, None,
                                                    ["fields"]))

    def test_blank_values(self):
        path = '/?foo=&bar=&baz=&qux='
        request = webob.Request.blank(path)
        self.assertEqual({}, api_common.get_filters(request, {}))

    def test_no_attr_info(self):
        path = '/?foo=4&bar=3&baz=2&qux=1'
        request = webob.Request.blank(path)
        expect_val = {'foo': ['4'], 'bar': ['3'], 'baz': ['2'], 'qux': ['1']}
        actual_val = api_common.get_filters(request, {})
        self.assertEqual(expect_val, actual_val)

    def test_attr_info_without_conversion(self):
        path = '/?foo=4&bar=3&baz=2&qux=1'
        request = webob.Request.blank(path)
        attr_info = {'foo': {'key': 'val'}}
        expect_val = {'foo': ['4'], 'bar': ['3'], 'baz': ['2'], 'qux': ['1']}
        actual_val = api_common.get_filters(request, attr_info)
        self.assertEqual(expect_val, actual_val)

    def test_attr_info_with_convert_list_to(self):
        path = '/?foo=key=4&bar=3&foo=key=2&qux=1'
        request = webob.Request.blank(path)
        attr_info = {
            'foo': {
                'convert_list_to': attributes.convert_kvp_list_to_dict,
            }
        }
        expect_val = {'foo': {'key': ['2', '4']}, 'bar': ['3'], 'qux': ['1']}
        actual_val = api_common.get_filters(request, attr_info)
        self.assertEqual(expect_val, actual_val)

    def test_attr_info_with_convert_to(self):
        path = '/?foo=4&bar=3&baz=2&qux=1'
        request = webob.Request.blank(path)
        attr_info = {'foo': {'convert_to': attributes.convert_to_int}}
        expect_val = {'foo': [4], 'bar': ['3'], 'baz': ['2'], 'qux': ['1']}
        actual_val = api_common.get_filters(request, attr_info)
        self.assertEqual(expect_val, actual_val)


class CreateResourceTestCase(base.BaseTestCase):
    def test_resource_creation(self):
        resource = v2_base.create_resource('fakes', 'fake', None, {})
        self.assertIsInstance(resource, webob.dec.wsgify)
