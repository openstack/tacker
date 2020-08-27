# Copyright 2015 Brocade Communications System, Inc.
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

from datetime import datetime
from unittest import mock
from unittest.mock import patch

import ddt
import iso8601
from oslo_utils import uuidutils
import yaml

from tacker._i18n import _
from tacker.common import exceptions
from tacker import context
from tacker.db.common_services import common_services_db_plugin
from tacker.db.db_sqlalchemy import models
from tacker.db.nfvo import nfvo_db
from tacker.db.nfvo import ns_db
from tacker.db.vnfm import vnfm_db
from tacker.extensions import vnfm
from tacker import objects
from tacker.objects import heal_vnf_request
from tacker.plugins.common import constants
from tacker.tests.unit.conductor import fakes
from tacker.tests.unit.db import base as db_base
from tacker.tests.unit.db import utils
from tacker.tests.unit.vnflcm import fakes as vnflcm_fakes
from tacker.vnfm import monitor
from tacker.vnfm import plugin


class FakeDriverManager(mock.Mock):
    def invoke(self, *args, **kwargs):
        if 'create' in args:
            return uuidutils.generate_uuid()

        if 'get_resource_info' in args:
            return {'resources': {'name': 'dummy_vnf',
                                  'type': 'dummy',
                                  'id': uuidutils.generate_uuid()}}


class FakeVNFMonitor(mock.Mock):
    def update_vnf_with_maintenance(self, vnf_dict, maintenance_vdus):
        url = 'http://local:9890/v1.0/vnfs/%s/maintenance/%s' % (
            vnf_dict['id'], vnf_dict['tenant_id'])
        return {'url': url,
                'vdus': {'ALL': 'ad7ebc56',
                         'VDU1': '538745a0'}}


class FakeGreenPool(mock.Mock):
    pass


class FakeVimClient(mock.Mock):
    pass


class FakePlugin(mock.Mock):
    pass


class FakeException(Exception):
    pass


class TestVNFMPluginMonitor(db_base.SqlTestCase):
    def setUp(self):
        super(TestVNFMPluginMonitor, self).setUp()
        self._mock_vnf_manager()

    def _mock_vnf_manager(self):
        self._vnf_manager = mock.Mock(wraps=FakeDriverManager())
        self._vnf_manager.__contains__ = mock.Mock(
            return_value=True)
        fake_vnf_manager = mock.Mock()
        fake_vnf_manager.return_value = self._vnf_manager
        self._mock(
            'tacker.common.driver_manager.DriverManager', fake_vnf_manager)

    @mock.patch('tacker.db.vnfm.vnfm_db.VNFMPluginDb.get_vnfs')
    @mock.patch('tacker.vnfm.monitor.VNFMonitor.__run__')
    def test_init_monitoring(self, mock_run, mock_get_vnfs):
        vnf_id = uuidutils.generate_uuid()
        vnfs = [{
            'id': vnf_id,
            'vnf': {
                'id': vnf_id,
                'status': 'ACTIVE',
                'name': 'fake_vnf',
                'attributes': {
                    'monitoring_policy':
                        '{"vdus": '
                        '{"VDU1": {"ping": {"actions": {"failure": "respawn"},'
                        '"name": "ping", "parameters": {"count": 3,'
                        '"interval": 1, "monitoring_delay": 45, "timeout": 2},'
                        '"monitoring_params": {"count": 3, "interval": 1,'
                        '"monitoring_delay": 45, "timeout": 2}}}}}'}
            },
            'name': 'fake_vnf',
            'tenant_id': 'ad7ebc56538745a08ef7c5e97f8bd437',
            'description': 'fake_vnf_description',
            'instance_id': 'da85ea1a-4ec4-4201-bbb2-8d9249eca7ec',
            'vnfd_id': 'eb094833-995e-49f0-a047-dfb56aaf7c4e',
            'vim_id': '6261579e-d6f3-49ad-8bc3-a9cb974778ff',
            'placement_attr': {'region': 'RegionOne'},
            'status': 'ACTIVE',
            'attributes': {
                    'monitoring_policy':
                        '{"vdus": '
                        '{"VDU1": {"ping": {"actions": {"failure": "respawn"},'
                        '"name": "ping", "parameters": {"count": 3,'
                        '"interval": 1, "monitoring_delay": 45, "timeout": 2},'
                        '"monitoring_params": {"count": 3, "interval": 1,'
                        '"monitoring_delay": 45, "timeout": 2}}}}}'},
            'mgmt_ip_address': '{"VDU1": "a.b.c.d"}',
            'deleted_at': datetime.min,
            'mgmt_ip_addresses': 'a.b.c.d'
        }]

        mock_get_vnfs.return_value = vnfs
        # NOTE(bhagyashris): VNFMonitor class is using a singleton pattern
        # and '_hosting_vnfs' is defined as a class level attribute.
        # If one of the unit test adds a VNF to monitor it will show up here
        # provided both the unit tests runs in the same process.
        # Hence, you must reinitialize '_hosting_vnfs' to empty dict.
        monitor.VNFMonitor._hosting_vnfs = dict()
        vnfm_plugin = plugin.VNFMPlugin()
        hosting_vnfs = vnfm_plugin._vnf_monitor._hosting_vnfs.values()
        hosting_vnf = list(hosting_vnfs)[0]['vnf']
        self.assertEqual('{"VDU1": "a.b.c.d"}', hosting_vnf['mgmt_ip_address'])
        self.assertEqual(1, len(hosting_vnfs))


@ddt.ddt
class TestVNFMPlugin(db_base.SqlTestCase):
    def setUp(self):
        super(TestVNFMPlugin, self).setUp()
        self.addCleanup(mock.patch.stopall)
        self.context = context.get_admin_context()
        self._mock_vim_client()
        self._stub_get_vim()
        self._mock_vnf_monitor()
        self._mock_vnf_alarm_monitor()
        self._mock_vnf_reservation_monitor()
        self._mock_vnf_maintenance_monitor()
        self._mock_vnf_maintenance_plugin()
        self._insert_dummy_vim()
        self.vnfm_plugin = plugin.VNFMPlugin()
        mock.patch('tacker.db.common_services.common_services_db_plugin.'
                   'CommonServicesPluginDb.create_event'
                   ).start()
        mock.patch('tacker.db.vnfm.vnfm_db.VNFMPluginDb._mgmt_driver_name',
                   return_value='noop').start()
        self.create = mock.patch('tacker.vnfm.infra_drivers.openstack.'
                                 'openstack.OpenStack.create',
                        return_value=uuidutils.generate_uuid()).start()
        self.create_wait = mock.patch('tacker.vnfm.infra_drivers.openstack.'
                                  'openstack.OpenStack.create_wait').start()
        self.update = mock.patch('tacker.vnfm.infra_drivers.openstack.'
                                 'openstack.OpenStack.update').start()
        self.update_wait = mock.patch('tacker.vnfm.infra_drivers.openstack.'
                                    'openstack.OpenStack.update_wait').start()
        self.delete = mock.patch('tacker.vnfm.infra_drivers.openstack.'
                                 'openstack.OpenStack.delete').start()
        self.delete_wait = mock.patch('tacker.vnfm.infra_drivers.openstack.'
                                      'openstack.OpenStack.'
                                      'delete_wait').start()
        self.scale = mock.patch('tacker.vnfm.infra_drivers.openstack.'
                                'openstack.OpenStack.scale',
                                return_value=uuidutils.generate_uuid()).start()
        self.scale_wait = mock.patch('tacker.vnfm.infra_drivers.openstack.'
                                'openstack.OpenStack.scale_wait',
                                return_value=uuidutils.generate_uuid()).start()

        self.heal_wait = mock.patch('tacker.vnfm.infra_drivers.openstack.'
                                    'openstack.OpenStack.heal_wait').start()

        def _fake_spawn(func, *args, **kwargs):
            func(*args, **kwargs)

        mock.patch.object(self.vnfm_plugin, 'spawn_n',
                          _fake_spawn).start()
        self._cos_db_plugin =\
            common_services_db_plugin.CommonServicesPluginDb()

    def _mock_vim_client(self):
        self.vim_client = mock.Mock(wraps=FakeVimClient())
        fake_vim_client = mock.Mock()
        fake_vim_client.return_value = self.vim_client
        self._mock(
            'tacker.vnfm.vim_client.VimClient', fake_vim_client)

    def _stub_get_vim(self):
        vim_obj = {'vim_id': '6261579e-d6f3-49ad-8bc3-a9cb974778ff',
                   'vim_name': 'fake_vim', 'vim_auth':
                   {'auth_url': 'http://localhost/identity', 'password':
                       'test_pw', 'username': 'test_user', 'project_name':
                       'test_project'}, 'vim_type': 'openstack'}
        self.vim_client.get_vim.return_value = vim_obj

    def _mock_vnf_monitor(self):
        self._vnf_monitor = mock.Mock(wraps=FakeVNFMonitor())
        fake_vnf_monitor = mock.Mock()
        fake_vnf_monitor.return_value = self._vnf_monitor
        self._mock(
            'tacker.vnfm.monitor.VNFMonitor', fake_vnf_monitor)

    def _mock_vnf_alarm_monitor(self):
        self._vnf_alarm_monitor = mock.Mock(wraps=FakeVNFMonitor())
        fake_vnf_alarm_monitor = mock.Mock()
        fake_vnf_alarm_monitor.return_value = self._vnf_alarm_monitor
        self._mock(
            'tacker.vnfm.monitor.VNFAlarmMonitor', fake_vnf_alarm_monitor)

    def _mock_vnf_reservation_monitor(self):
        self._vnf_reservation_mon = mock.Mock(wraps=FakeVNFMonitor())
        fake_vnf_reservation_monitor = mock.Mock()
        fake_vnf_reservation_monitor.return_value = self._vnf_reservation_mon
        self._mock(
            'tacker.vnfm.monitor.VNFReservationAlarmMonitor',
            fake_vnf_reservation_monitor)

    def _mock_vnf_maintenance_monitor(self):
        self._vnf_maintenance_mon = mock.Mock(wraps=FakeVNFMonitor())
        fake_vnf_maintenance_monitor = mock.Mock()
        fake_vnf_maintenance_monitor.return_value = self._vnf_maintenance_mon
        self._mock(
            'tacker.vnfm.monitor.VNFMaintenanceAlarmMonitor',
            fake_vnf_maintenance_monitor)

    def _mock_vnf_maintenance_plugin(self):
        self._vnf_maintenance_plugin = mock.Mock(wraps=FakePlugin())
        fake_vnf_maintenance_plugin = mock.Mock()
        fake_vnf_maintenance_plugin.return_value = self._vnf_maintenance_plugin
        self._mock(
            'tacker.plugins.fenix.FenixPlugin',
            fake_vnf_maintenance_plugin)

    def _insert_dummy_vnf_template(self):
        session = self.context.session
        vnf_template = vnfm_db.VNFD(
            id='eb094833-995e-49f0-a047-dfb56aaf7c4e',
            tenant_id='ad7ebc56538745a08ef7c5e97f8bd437',
            name='fake_template',
            description='fake_template_description',
            template_source='onboarded',
            deleted_at=datetime.min)
        session.add(vnf_template)
        session.flush()
        return vnf_template

    def _insert_dummy_vnf_template_inline(self):
        session = self.context.session
        vnf_template = vnfm_db.VNFD(
            id='d58bcc4e-d0cf-11e6-bf26-cec0c932ce01',
            tenant_id='ad7ebc56538745a08ef7c5e97f8bd437',
            name='tmpl-koeak4tqgoqo8cr4-dummy_inline_vnf',
            description='inline_fake_template_description',
            deleted_at=datetime.min,
            template_source='inline')
        session.add(vnf_template)
        session.flush()
        return vnf_template

    def _insert_dummy_vnf(self, status="ACTIVE"):
        session = self.context.session
        vnf_db = vnfm_db.VNF(
            id='6261579e-d6f3-49ad-8bc3-a9cb974778fe',
            tenant_id='ad7ebc56538745a08ef7c5e97f8bd437',
            name='fake_vnf',
            description='fake_vnf_description',
            instance_id='da85ea1a-4ec4-4201-bbb2-8d9249eca7ec',
            vnfd_id='eb094833-995e-49f0-a047-dfb56aaf7c4e',
            vim_id='6261579e-d6f3-49ad-8bc3-a9cb974778ff',
            placement_attr={'region': 'RegionOne'},
            status=status,
            deleted_at=datetime.min)
        session.add(vnf_db)
        session.flush()
        return vnf_db

    def _insert_dummy_pending_vnf(self, context, status='PENDING_DELETE'):
        session = context.session
        vnf_db = vnfm_db.VNF(
            id='6261579e-d6f3-49ad-8bc3-a9cb974778fe',
            tenant_id='ad7ebc56538745a08ef7c5e97f8bd437',
            name='fake_vnf',
            description='fake_vnf_description',
            instance_id='da85ea1a-4ec4-4201-bbb2-8d9249eca7ec',
            vnfd_id='eb094833-995e-49f0-a047-dfb56aaf7c4e',
            vim_id='6261579e-d6f3-49ad-8bc3-a9cb974778ff',
            placement_attr={'region': 'RegionOne'},
            status=status,
            deleted_at=datetime.min)
        session.add(vnf_db)
        session.flush()
        return vnf_db

    def _insert_scaling_attributes_vnf(self):
        session = self.context.session
        vnf_attributes = vnfm_db.VNFAttribute(
            id='7800cb81-7ed1-4cf6-8387-746468522651',
            vnf_id='6261579e-d6f3-49ad-8bc3-a9cb974778fe',
            key='scaling_group_names',
            value='{"SP1": "G1"}'
        )
        session.add(vnf_attributes)
        session.flush()
        return vnf_attributes

    def _insert_scaling_attributes_vnfd(self, invalid_policy_type=False):
        session = self.context.session
        vnfd_attributes = vnfm_db.VNFDAttribute(
            id='7800cb81-7ed1-4cf6-8387-746468522650',
            vnfd_id='eb094833-995e-49f0-a047-dfb56aaf7c4e',
            key='vnfd',
            value=utils.vnfd_scale_tosca_template
        )
        session.add(vnfd_attributes)
        session.flush()
        if invalid_policy_type:
            vnfd_template = yaml.safe_load(vnfd_attributes.value)
            vnfd_template['topology_template']['policies'][0]['SP1']['type'] \
                = "test_invalid_policy_type"
            vnfd_attributes.value = yaml.dump(vnfd_template)
        return vnfd_attributes

    def _insert_dummy_vim(self):
        session = self.context.session
        vim_db = nfvo_db.Vim(
            id='6261579e-d6f3-49ad-8bc3-a9cb974778ff',
            tenant_id='ad7ebc56538745a08ef7c5e97f8bd437',
            name='fake_vim',
            description='fake_vim_description',
            type='test_vim',
            status='Active',
            deleted_at=datetime.min,
            placement_attr={'regions': ['RegionOne']})
        vim_auth_db = nfvo_db.VimAuth(
            vim_id='6261579e-d6f3-49ad-8bc3-a9cb974778ff',
            password='encrypted_pw',
            auth_url='http://localhost/identity',
            vim_project={'name': 'test_project'},
            auth_cred={'username': 'test_user', 'user_domain_id': 'default',
                       'project_domain_id': 'default'})
        session.add(vim_db)
        session.add(vim_auth_db)
        session.flush()

    @mock.patch('tacker.vnfm.plugin.toscautils.updateimports')
    @mock.patch('tacker.vnfm.plugin.ToscaTemplate')
    @mock.patch('tacker.vnfm.plugin.toscautils.get_mgmt_driver')
    def test_create_vnfd(self, mock_get_mgmt_driver, mock_tosca_template,
                        mock_update_imports):
        mock_get_mgmt_driver.return_value = 'noop'
        mock_tosca_template.return_value = mock.ANY

        vnfd_obj = utils.get_dummy_vnfd_obj()
        result = self.vnfm_plugin.create_vnfd(self.context, vnfd_obj)
        self.assertIsNotNone(result)
        self.assertIn('id', result)
        self.assertEqual('dummy_vnfd', result['name'])
        self.assertEqual('dummy_vnfd_description', result['description'])
        self.assertEqual('noop', result['mgmt_driver'])
        self.assertIn('service_types', result)
        self.assertIn('attributes', result)
        self.assertIn('created_at', result)
        self.assertIn('updated_at', result)
        self.assertIn('template_source', result)
        yaml_dict = yaml.safe_load(utils.tosca_vnfd_openwrt)
        mock_tosca_template.assert_called_once_with(
            a_file=False, yaml_dict_tpl=yaml_dict)
        mock_get_mgmt_driver.assert_called_once_with(mock.ANY)
        mock_update_imports.assert_called_once_with(yaml_dict)
        self._cos_db_plugin.create_event.assert_called_once_with(
            self.context, evt_type=constants.RES_EVT_CREATE, res_id=mock.ANY,
            res_state=constants.RES_EVT_ONBOARDED,
            res_type=constants.RES_TYPE_VNFD, tstamp=mock.ANY)

    def test_create_vnfd_without_tosca_definitions_version(self):
        vnfd_obj = utils.get_dummy_vnfd_obj()
        vnfd_obj['vnfd']['attributes']['vnfd'].pop('tosca_definitions_version')
        self.assertRaises(exceptions.Invalid,
                          self.vnfm_plugin.create_vnfd,
                          self.context, vnfd_obj)

    def test_create_vnfd_with_empty_description(self):
        vnfd_obj = utils.get_dummy_vnfd_obj()
        vnfd_obj['vnfd']['description'] = ''
        result = self.vnfm_plugin.create_vnfd(self.context, vnfd_obj)
        self.assertIsNotNone(result)
        # If vnfd description is an empty string, it sets the description of
        # vnfd to the description that is present in the vnfd tosca template.
        self.assertEqual(yaml.safe_load(
            vnfd_obj['vnfd']['attributes']['vnfd'])['description'],
            result['description'])

    def test_create_vnfd_empty_name(self):
        vnfd_obj = utils.get_dummy_vnfd_obj()
        vnfd_obj['vnfd']['name'] = ''
        result = self.vnfm_plugin.create_vnfd(self.context, vnfd_obj)
        self.assertIsNotNone(result)
        # If vnfd name is an empty string, it sets the name of vnfd to
        # the name that is present in the vnfd tosca template.
        self.assertEqual(yaml.safe_load(vnfd_obj['vnfd']['attributes']
                    ['vnfd'])['metadata']['template_name'], result['name'])

    def test_create_vnfd_with_tosca_parser_failure(self):
        vnfd_obj = utils.get_invalid_vnfd_obj()
        self.assertRaises(vnfm.ToscaParserFailed,
                          self.vnfm_plugin.create_vnfd,
                          self.context, vnfd_obj)

    def test_create_vnfd_no_service_types(self):
        vnfd_obj = utils.get_dummy_vnfd_obj()
        vnfd_obj['vnfd'].pop('service_types')
        self.assertRaises(vnfm.ServiceTypesNotSpecified,
                          self.vnfm_plugin.create_vnfd,
                          self.context, vnfd_obj)

    def test_create_vnfd_without_dict_type_attributes(self):
        vnfd_obj = utils.get_dummy_vnfd_obj()
        # Convert dict to string.
        vnfd_obj['vnfd']['attributes']['vnfd'] = str(
            vnfd_obj['vnfd']['attributes']['vnfd'])
        self.assertRaises(vnfm.InvalidAPIAttributeType,
                          self.vnfm_plugin.create_vnfd,
                          self.context, vnfd_obj)

    def test_create_vnf_sync(self):
        self._insert_dummy_vnf_template()
        vnf_obj = utils.get_dummy_vnf_obj()
        vnf_dict = self.vnfm_plugin.create_vnf_sync(self.context,
                                                    vnf_obj['vnf'])
        self.assertIsNotNone(vnf_dict)
        self.assertEqual('ACTIVE', vnf_dict['status'])
        self._cos_db_plugin.create_event.assert_called_with(
            self.context, evt_type=constants.RES_EVT_CREATE, res_id=mock.ANY,
            res_state=mock.ANY, res_type=constants.RES_TYPE_VNF,
            tstamp=mock.ANY, details=mock.ANY)

    def test_create_vnf_with_vnfd(self):
        self._insert_dummy_vnf_template()
        vnf_obj = utils.get_dummy_vnf_obj()
        result = self.vnfm_plugin.create_vnf(self.context, vnf_obj)
        self.assertIsNotNone(result)
        self.assertIn('id', result)
        self.assertIn('instance_id', result)
        self.assertIn('status', result)
        self.assertIn('attributes', result)
        self.assertIn('mgmt_ip_address', result)
        self.assertIn('created_at', result)
        self.assertIn('updated_at', result)
        self.assertEqual('ACTIVE', result['status'])
        self._cos_db_plugin.create_event.assert_called_with(
            self.context, evt_type=constants.RES_EVT_CREATE, res_id=mock.ANY,
            res_state=mock.ANY, res_type=constants.RES_TYPE_VNF,
            tstamp=mock.ANY, details=mock.ANY)

    @mock.patch('tacker.vnfm.plugin.VNFMPlugin.create_vnfd')
    def test_create_vnf_from_template(self, mock_create_vnfd):
        self._insert_dummy_vnf_template_inline()
        mock_create_vnfd.return_value = {'id':
                'd58bcc4e-d0cf-11e6-bf26-cec0c932ce01'}
        vnf_obj = utils.get_dummy_inline_vnf_obj()
        result = self.vnfm_plugin.create_vnf(self.context, vnf_obj)
        self.assertIsNotNone(result)
        self.assertIn('id', result)
        self.assertIn('instance_id', result)
        self.assertIn('status', result)
        self.assertIn('attributes', result)
        self.assertIn('mgmt_ip_address', result)
        self.assertIn('created_at', result)
        self.assertIn('updated_at', result)
        self.assertEqual('ACTIVE', result['status'])
        mock_create_vnfd.assert_called_once_with(mock.ANY, mock.ANY)
        self._cos_db_plugin.create_event.assert_called_with(
            self.context, evt_type=constants.RES_EVT_CREATE,
            res_id=mock.ANY,
            res_state=mock.ANY, res_type=constants.RES_TYPE_VNF,
            tstamp=mock.ANY, details=mock.ANY)

    def test_create_vnf_with_param_values(self):
        self._insert_dummy_vnf_template()
        vnf_obj = utils.get_dummy_vnf_obj()
        vnf_obj['vnf']['attributes'] = {'param_values':
        {'image_name': 'cirros-0.4.0-x86_64-disk', 'flavor': 'm1.tiny'}}
        result = self.vnfm_plugin.create_vnf(self.context, vnf_obj)
        self.assertIsNotNone(result)
        self.assertEqual(vnf_obj['vnf']['attributes']['param_values'],
                         result['attributes']['param_values'])
        self.assertEqual('ACTIVE', result['status'])

    def test_create_vnf_with_config_option(self):
        self._insert_dummy_vnf_template()
        vnf_obj = utils.get_dummy_vnf_obj()
        config = utils.get_dummy_vnf_config_obj()
        vnf_obj['vnf']['attributes'] = config['vnf']['attributes']
        result = self.vnfm_plugin.create_vnf(self.context, vnf_obj)
        self.assertEqual(vnf_obj['vnf']['attributes']['config'],
                         result['attributes']['config'])
        self.assertEqual('ACTIVE', result['status'])

    def test_create_vnf_fail_with_invalid_infra_driver_exception(self):
        self.vim_client.get_vim.return_value['vim_type'] = 'test_invalid_vim'
        self._insert_dummy_vnf_template()
        vnf_obj = utils.get_dummy_vnf_obj()
        self.assertRaises(vnfm.InvalidInfraDriver,
                          self.vnfm_plugin.create_vnf,
                          self.context, vnf_obj)

    def test_create_vnf_with_invalid_param_and_config_format(self):
        self._insert_dummy_vnf_template()
        vnf_obj = utils.get_dummy_vnf_obj()
        vnf_obj['vnf']['attributes']['param_values'] = 'image_name'
        vnf_obj['vnf']['attributes']['config'] = 'test'
        self.assertRaises(vnfm.InvalidAPIAttributeType,
                          self.vnfm_plugin.create_vnf,
                          self.context, vnf_obj)

    @patch('tacker.vnfm.plugin.VNFMPlugin._delete_vnf')
    def test_create_vnf_fail(self, mock_delete_vnf):
        self._insert_dummy_vnf_template()
        vnf_obj = utils.get_dummy_vnf_obj()
        self.create.side_effect = vnfm.HeatClientException(msg='test')
        self.assertRaises(vnfm.HeatClientException,
                          self.vnfm_plugin.create_vnf,
                          self.context, vnf_obj)
        vnf_id = self.vnfm_plugin._delete_vnf.call_args[0][1]
        mock_delete_vnf.assert_called_once_with(self.context, vnf_id,
                                                force_delete=True)

    def test_create_vnf_create_wait_failed_exception(self):
        self._insert_dummy_vnf_template()
        vnf_obj = utils.get_dummy_vnf_obj()
        self.create_wait.side_effect = vnfm.VNFCreateWaitFailed(
            reason="failed")
        vnf_dict = self.vnfm_plugin.create_vnf(self.context, vnf_obj)
        self.assertEqual(constants.ERROR,
                         vnf_dict['status'])

    @patch('tacker.vnfm.plugin.VNFMPlugin.mgmt_call')
    def test_create_vnf_mgmt_driver_exception(self, mock_mgmt_call):
        self._insert_dummy_vnf_template()
        vnf_obj = utils.get_dummy_vnf_obj()
        mock_mgmt_call.side_effect = exceptions.MgmtDriverException
        vnf_dict = self.vnfm_plugin.create_vnf(self.context, vnf_obj)
        self.assertEqual(constants.ERROR,
                         vnf_dict['status'])

    @patch('tacker.db.vnfm.vnfm_db.VNFMPluginDb._create_vnf_post')
    @patch('tacker.db.vnfm.vnfm_db.VNFMPluginDb._create_vnf_pre')
    @patch('tacker.db.vnfm.vnfm_db.VNFMPluginDb._create_vnf_status')
    def test_create_vnf_with_alarm_url(self, mock_create_vnf_status,
                                       mock_create_vnf_pre,
                                       mock_create_vnf_post):
        self._insert_dummy_vnf_template()
        vnf_obj = utils.get_dummy_vnf_obj()
        alarm_url_dict = {'vdu_hcpu_usage_scaling_out':
                        'http://localhost/identity',
                          'vdu_lcpu_usage_scaling_in':
                        'http://localhost/identity'}
        self._vnf_alarm_monitor.update_vnf_with_alarm.return_value = \
            alarm_url_dict
        dummy_vnf = self._get_dummy_vnf(utils.vnfd_alarm_scale_tosca_template,
                                        status='PENDING_CREATE')
        mock_create_vnf_pre.return_value = dummy_vnf
        vnf_dict = self.vnfm_plugin.create_vnf(self.context, vnf_obj)
        self.assertEqual(alarm_url_dict['vdu_lcpu_usage_scaling_in'],
                         vnf_dict['attributes']['vdu_lcpu_usage_scaling_in'])
        self.assertEqual(alarm_url_dict['vdu_hcpu_usage_scaling_out'],
                         vnf_dict['attributes']['vdu_hcpu_usage_scaling_out'])

    @patch('tacker.vnfm.plugin.VNFMPlugin._create_vnf_wait')
    def test_show_vnf_details_vnf_inactive(self, mock_create_vnf_wait):
        self._insert_dummy_vnf_template()
        vnf_obj = utils.get_dummy_vnf_obj()
        result = self.vnfm_plugin.create_vnf(self.context, vnf_obj)
        self.assertRaises(vnfm.VNFInactive, self.vnfm_plugin.get_vnf_resources,
                          self.context, result['id'])

    @patch('tacker.vnfm.infra_drivers.openstack.openstack.OpenStack.'
           'get_resource_info')
    def test_show_vnf_details_vnf_active(self, mock_get_resource_info):
        self._insert_dummy_vnf_template()
        active_vnf = self._insert_dummy_vnf()
        mock_get_resource_info.return_value = {'resources': {'name':
                                                            'dummy_vnf',
                                                            'type': 'dummy',
                                                            'id':
                                                uuidutils.generate_uuid()}}
        resources = self.vnfm_plugin.get_vnf_resources(self.context,
                                                       active_vnf['id'])[0]
        self.assertIn('name', resources)
        self.assertIn('type', resources)
        self.assertIn('id', resources)

    def test_delete_vnf(self):
        self._insert_dummy_vnf_template()
        dummy_vnf_obj = self._insert_dummy_vnf()
        self.vnfm_plugin.delete_vnf(self.context, dummy_vnf_obj[
            'id'])
        self._vnf_monitor.delete_hosting_vnf.assert_called_with(mock.ANY)
        self.delete.assert_called_with(plugin=mock.ANY, context=mock.ANY,
                                       vnf_id=mock.ANY,
                                       auth_attr=mock.ANY,
                                       region_name=mock.ANY)
        self._cos_db_plugin.create_event.assert_called_with(
            self.context, evt_type=constants.RES_EVT_DELETE, res_id=mock.ANY,
            res_state=mock.ANY, res_type=constants.RES_TYPE_VNF,
            tstamp=mock.ANY, details=mock.ANY)

    def test_delete_vnf_in_pending_state(self):
        # delete_vnf will raise exception when VNF status in PENDING_*
        self._insert_dummy_vnf_template()
        dummy_vnf_obj = self._insert_dummy_pending_vnf(self.context)
        self.assertRaises(vnfm.VNFDeleteFailed,
                          self.vnfm_plugin.delete_vnf,
                          self.context,
                          dummy_vnf_obj['id'])

    @ddt.data('PENDING_DELETE', 'PENDING_CREATE')
    def test_force_delete_vnf(self, status):
        self._insert_dummy_vnf_template()
        dummy_vnf_obj = self._insert_dummy_pending_vnf(self.context, status)
        vnfattr = {'vnf': {'attributes': {'force': True}}}
        self.vnfm_plugin.delete_vnf(self.context, dummy_vnf_obj[
            'id'], vnf=vnfattr)
        self._vnf_monitor.delete_hosting_vnf.assert_called_with(mock.ANY)
        self.delete.assert_called_with(plugin=mock.ANY, context=mock.ANY,
                                       vnf_id=mock.ANY,
                                       auth_attr=mock.ANY,
                                       region_name=mock.ANY)
        self._cos_db_plugin.create_event.assert_called_with(
            self.context, evt_type=constants.RES_EVT_DELETE, res_id=mock.ANY,
            res_state=mock.ANY, res_type=constants.RES_TYPE_VNF,
            tstamp=mock.ANY, details="VNF Delete Complete")

    def test_force_delete_vnf_non_admin(self):
        self._insert_dummy_vnf_template()
        non_admin_context = context.Context(user_id=None,
                                            tenant_id=None,
                                            is_admin=False)
        dummy_vnf_obj = self._insert_dummy_pending_vnf(non_admin_context)
        vnfattr = {'vnf': {'attributes': {'force': True}}}
        self.assertRaises(exceptions.AdminRequired,
                          self.vnfm_plugin.delete_vnf,
                          non_admin_context,
                          dummy_vnf_obj['id'], vnf=vnfattr)

    @patch('tacker.db.vnfm.vnfm_db.VNFMPluginDb._delete_vnf_post')
    def test_delete_vnf_fail(self, mock_delete_vnf_post):
        self.delete.side_effect = FakeException
        self._insert_dummy_vnf_template()
        dummy_device_obj = self._insert_dummy_vnf()
        self.assertRaises(FakeException,
                          self.vnfm_plugin.delete_vnf, self.context,
                          dummy_device_obj['id'])
        self._vnf_monitor.delete_hosting_vnf.assert_called_once_with(
            dummy_device_obj['id'])
        mock_delete_vnf_post.assert_called_once_with(self.context, mock.ANY,
                                                     mock.ANY)
        self._cos_db_plugin.create_event.assert_called_with(
            self.context, evt_type=constants.RES_EVT_DELETE, res_id=mock.ANY,
            res_state=mock.ANY, res_type=constants.RES_TYPE_VNF,
            tstamp=mock.ANY, details=mock.ANY)

    @patch('tacker.db.vnfm.vnfm_db.VNFMPluginDb.set_vnf_error_status_reason')
    def test_delete_vnf_delete_wait_failed_exception(self,
                                            mock_set_vnf_error_status_reason):
        self._insert_dummy_vnf_template()
        dummy_vnf_obj = self._insert_dummy_vnf()
        self.delete_wait.side_effect = vnfm.VNFDeleteWaitFailed(
            reason='failed')
        self.vnfm_plugin.delete_vnf(self.context, dummy_vnf_obj['id'])
        mock_set_vnf_error_status_reason.assert_called_once_with(self.context,
                                                                 mock.ANY,
                                                                 mock.ANY)

    def test_delete_vnf_failed_with_status_pending_create(self):
        self._insert_dummy_vnf_template()
        dummy_device_obj_with_pending_create_status = self. \
            _insert_dummy_vnf(status="PENDING_CREATE")
        self.assertRaises(vnfm.VNFInUse, self.vnfm_plugin.delete_vnf,
                          self.context,
                          dummy_device_obj_with_pending_create_status['id'])

    def _insert_dummy_ns_template(self):
        session = self.context.session
        attributes = {
            u'nsd': 'imports: [VNF1, VNF2]\ntopology_template:\n  inputs:\n  '
                    '  vl1_name: {default: net_mgmt, description: name of VL1'
                    ' virtuallink, type: string}\n    vl2_name: {default: '
                    'net0, description: name of VL2 virtuallink, type: string'
                    '}\n  node_templates:\n    VL1:\n      properties:\n     '
                    '   network_name: {get_input: vl1_name}\n        vendor: '
                    'tacker\n      type: tosca.nodes.nfv.VL\n    VL2:\n      '
                    'properties:\n        network_name: {get_input: vl2_name}'
                    '\n        vendor: tacker\n      type: tosca.nodes.nfv.VL'
                    '\n    VNF1:\n      requirements:\n      - {virtualLink1: '
                    'VL1}\n      - {virtualLink2: VL2}\n      type: tosca.node'
                    's.nfv.VNF1\n    VNF2: {type: tosca.nodes.nfv.VNF2}\ntosca'
                    '_definitions_version: tosca_simple_profile_for_nfv_1_0_0'
                    '\n'}
        nsd_template = ns_db.NSD(
            id='eb094833-995e-49f0-a047-dfb56aaf7c4e',
            tenant_id='ad7ebc56538745a08ef7c5e97f8bd437',
            name='fake_template',
            vnfds={'tosca.nodes.nfv.VNF1': 'vnf1',
                   'tosca.nodes.nfv.VNF2': 'vnf2'},
            description='fake_nsd_template_description',
            deleted_at=datetime.min,
            template_source='onboarded')
        session.add(nsd_template)
        for (key, value) in attributes.items():
            attribute_db = ns_db.NSDAttribute(
                id=uuidutils.generate_uuid(),
                nsd_id='eb094833-995e-49f0-a047-dfb56aaf7c4e',
                key=key,
                value=value)
            session.add(attribute_db)
        session.flush()
        return nsd_template

    def _insert_dummy_ns(self):
        session = self.context.session
        ns = ns_db.NS(
            id='ba6bf017-f6f7-45f1-a280-57b073bf78ea',
            name='dummy_ns',
            tenant_id='ad7ebc56538745a08ef7c5e97f8bd437',
            status='ACTIVE',
            nsd_id='eb094833-995e-49f0-a047-dfb56aaf7c4e',
            vim_id='6261579e-d6f3-49ad-8bc3-a9cb974778ff',
            description='dummy_ns_description',
            vnf_ids='[5761579e-d6f3-49ad-8bc3-a9cb73477846,'
                    '6261579e-d6f3-49ad-8bc3-a9cb974778fe]',
            deleted_at=datetime.min)
        session.add(ns)
        session.flush()
        return ns

    def test_delete_vnf_of_active_ns(self):
        self._insert_dummy_ns_template()
        self._insert_dummy_ns()
        self.assertRaises(vnfm.VNFInUse, self.vnfm_plugin.delete_vnf,
            self.context, '6261579e-d6f3-49ad-8bc3-a9cb974778fe')

    def test_update_vnf(self):
        self._insert_dummy_vnf_template()
        dummy_vnf_obj = self._insert_dummy_vnf()
        vnf_config_obj = utils.get_dummy_vnf_config_obj()
        result = self.vnfm_plugin.update_vnf(self.context, dummy_vnf_obj[
            'id'], vnf_config_obj)
        self.assertIsNotNone(result)
        self.assertEqual(dummy_vnf_obj['id'], result['id'])
        self.assertIn('instance_id', result)
        self.assertIn('status', result)
        self.assertIn('attributes', result)
        self.assertIn('mgmt_ip_address', result)
        self.assertIn('updated_at', result)
        self._cos_db_plugin.create_event.assert_called_with(
            self.context, evt_type=constants.RES_EVT_UPDATE, res_id=mock.ANY,
            res_state=mock.ANY, res_type=constants.RES_TYPE_VNF,
            tstamp=mock.ANY)

    @patch('tacker.db.vnfm.vnfm_db.VNFMPluginDb._update_vnf_post')
    def test_update_vnf_with_exception(self, mock_update_vnf_post):
        self.update.side_effect = FakeException
        self._insert_dummy_vnf_template()
        dummy_device_obj = self._insert_dummy_vnf()
        vnf_config_obj = utils.get_dummy_vnf_config_obj()
        self.assertRaises(FakeException,
                          self.vnfm_plugin.update_vnf, self.context,
                          dummy_device_obj['id'], vnf_config_obj)
        self._vnf_monitor.delete_hosting_vnf.assert_called_once_with(
            dummy_device_obj['id'])
        mock_update_vnf_post.assert_called_once_with(self.context,
                                                     dummy_device_obj['id'],
                                                     constants.ERROR,
                                                     mock.ANY,
                                                     constants.PENDING_UPDATE,
                                                     constants.RES_EVT_UPDATE)

        self._cos_db_plugin.create_event.assert_called_with(
            self.context, evt_type=constants.RES_EVT_UPDATE, res_id=mock.ANY,
            res_state=mock.ANY, res_type=constants.RES_TYPE_VNF,
            tstamp=mock.ANY)

    def test_update_vnf_invalid_config_format(self):
        self._insert_dummy_vnf_template()
        dummy_vnf_obj = self._insert_dummy_vnf()
        vnf_config_obj = utils.get_dummy_vnf_config_obj()
        vnf_config_obj['vnf']['attributes']['config'] = {'vdus': {
            'vdu1': {'config': {'firewall': 'dummy_firewall_values'}}}}
        result = self.vnfm_plugin.update_vnf(self.context, dummy_vnf_obj[
            'id'], vnf_config_obj)
        self.assertEqual(constants.ACTIVE, result['status'])

    @patch('tacker.db.vnfm.vnfm_db.VNFMPluginDb.set_vnf_error_status_reason')
    @mock.patch('tacker.vnfm.plugin.VNFMPlugin.mgmt_call')
    def test_update_vnf_fail_mgmt_driver_error(self, mock_mgmt_call,
                                            mock_set_vnf_error_status_reason):
        self._insert_dummy_vnf_template()
        dummy_vnf_obj = self._insert_dummy_vnf()
        vnf_config_obj = utils.get_dummy_vnf_config_obj()
        mock_mgmt_call.side_effect = exceptions.MgmtDriverException
        vnf_dict = self.vnfm_plugin.update_vnf(self.context,
                                               dummy_vnf_obj['id'],
                                               vnf_config_obj)
        self.assertEqual(constants.ERROR,
                         vnf_dict['status'])
        mock_set_vnf_error_status_reason.assert_called_once_with(self.context,
                                                          dummy_vnf_obj['id'],
                                                   'VNF configuration failed')

    @patch('tacker.db.vnfm.vnfm_db.VNFMPluginDb.set_vnf_error_status_reason')
    def test_update_vnf_fail_update_wait_error(self,
                                            mock_set_vnf_error_status_reason):
        self._insert_dummy_vnf_template()
        dummy_vnf_obj = self._insert_dummy_vnf()
        vnf_config_obj = utils.get_dummy_vnf_config_obj()
        self.update_wait.side_effect = vnfm.VNFUpdateWaitFailed(
            reason='failed')
        self.assertRaises(vnfm.VNFUpdateWaitFailed,
                          self.vnfm_plugin.update_vnf, self.context,
                          dummy_vnf_obj['id'], vnf_config_obj)
        self._vnf_monitor.\
            delete_hosting_vnf.assert_called_once_with(dummy_vnf_obj['id'])
        mock_set_vnf_error_status_reason.assert_called_once_with(self.context,
                                                        dummy_vnf_obj['id'],
                                                    'VNF Update failed')

    def test_update_vnf_param(self):
        self._insert_dummy_vnf_template()
        dummy_device_obj = self._insert_dummy_vnf()
        vnf_param_obj = utils.get_dummy_vnf_param_obj()
        result = self.vnfm_plugin.update_vnf(self.context,
                                             dummy_device_obj['id'],
                                             vnf_param_obj)
        self.assertIsNotNone(result)
        self.assertEqual(dummy_device_obj['id'], result['id'])
        self.assertIn('instance_id', result)
        self.assertIn('status', result)
        self.assertIn('attributes', result)
        self.assertIn('mgmt_ip_address', result)
        self.assertIn('updated_at', result)
        self._cos_db_plugin.create_event.assert_called_with(
            self.context, evt_type=constants.RES_EVT_UPDATE, res_id=mock.ANY,
            res_state=mock.ANY, res_type=constants.RES_TYPE_VNF,
            tstamp=mock.ANY)

    def test_update_vnf_invalid_config_type(self):
        self._insert_dummy_vnf_template()
        dummy_device_obj = self._insert_dummy_vnf()
        vnf_param_obj = utils.get_dummy_vnf_invalid_config_type_obj()
        self.assertRaises(vnfm.InvalidAPIAttributeType,
                          self.vnfm_plugin.update_vnf,
                          self.context,
                          dummy_device_obj['id'],
                          vnf_param_obj)

    def test_update_vnf_invalid_param_type(self):
        self._insert_dummy_vnf_template()
        dummy_device_obj = self._insert_dummy_vnf()
        vnf_param_obj = utils.get_dummy_vnf_invalid_param_type_obj()
        self.assertRaises(vnfm.InvalidAPIAttributeType,
                          self.vnfm_plugin.update_vnf,
                          self.context,
                          dummy_device_obj['id'],
                          vnf_param_obj)

    def test_update_vnf_invalid_param_content(self):
        self.update.side_effect = vnfm.VNFUpdateInvalidInput(
            reason='failed')
        self._insert_dummy_vnf_template()
        dummy_device_obj = self._insert_dummy_vnf()
        vnf_param_obj = utils.get_dummy_vnf_invalid_param_content()
        self.assertRaises(vnfm.VNFUpdateInvalidInput,
                          self.vnfm_plugin.update_vnf,
                          self.context,
                          dummy_device_obj['id'],
                          vnf_param_obj)

    def _get_dummy_scaling_policy(self, type):
        vnf_scale = {}
        vnf_scale['scale'] = {}
        vnf_scale['scale']['type'] = type
        vnf_scale['scale']['policy'] = 'SP1'
        return vnf_scale

    def _get_scaling_vnf(self, type, invalid_policy_type=False):
        # create vnfd
        self._insert_dummy_vnf_template()
        self._insert_scaling_attributes_vnfd(invalid_policy_type)

        # create vnf
        dummy_vnf_obj = self._insert_dummy_vnf()
        self._insert_scaling_attributes_vnf()

        # scale vnf
        vnf_scale = self._get_dummy_scaling_policy(type)
        return dummy_vnf_obj, vnf_scale

    def _test_scale_vnf(self, type):
        dummy_vnf_obj, vnf_scale = self._get_scaling_vnf(type)
        self.vnfm_plugin.create_vnf_scale(
            self.context,
            dummy_vnf_obj['id'],
            vnf_scale)
        # validate
        self.scale.assert_called_once_with(
            plugin=mock.ANY,
            context=mock.ANY,
            auth_attr=mock.ANY,
            policy=mock.ANY,
            region_name=mock.ANY
        )
        self.scale_wait.assert_called_once_with(plugin=self.vnfm_plugin,
                                                context=self.context,
                                                auth_attr=mock.ANY,
                                                policy=mock.ANY,
                                                region_name=mock.ANY,
                                                last_event_id=mock.ANY)
        self._cos_db_plugin.create_event.assert_called_with(
            self.context,
            evt_type=constants.RES_EVT_SCALE,
            res_id='6261579e-d6f3-49ad-8bc3-a9cb974778fe',
            res_state='ACTIVE',
            res_type=constants.RES_TYPE_VNF,
            tstamp=mock.ANY)

    def test_scale_vnf_out(self):
        self._test_scale_vnf('out')

    def test_scale_vnf_in(self):
        self._test_scale_vnf('in')

    @patch('tacker.db.vnfm.vnfm_db.VNFMPluginDb._update_vnf_scaling_status')
    @patch('tacker.db.vnfm.vnfm_db.VNFMPluginDb.set_vnf_error_status_reason')
    def test_scale_vnf_with_vnf_policy_action_exception(self,
                                            mock_set_vnf_error_status_reason,
                                            mock_update_vnf_scaling_status):
        dummy_vnf_obj, vnf_scale = self._get_scaling_vnf('in')
        self.scale.side_effect = FakeException
        self.assertRaises(FakeException,
                          self.vnfm_plugin.create_vnf_scale,
                          self.context, dummy_vnf_obj['id'],
                          vnf_scale)
        mock_update_vnf_scaling_status.assert_called_with(
            self.context, mock.ANY, [constants.PENDING_SCALE_IN],
            constants.ERROR, mock.ANY)
        mock_set_vnf_error_status_reason.assert_called_with(
            self.context, dummy_vnf_obj['id'], mock.ANY)

    @mock.patch('tacker.vnfm.plugin.VNFMPlugin.get_vnf_policies')
    def test_scale_vnf_with_policy_not_found_exception(self,
                                                      mock_get_vnf_policies):
        dummy_vnf_obj, vnf_scale = self._get_scaling_vnf('in')
        mock_get_vnf_policies.return_value = None
        self.assertRaises(exceptions.VnfPolicyNotFound,
                          self.vnfm_plugin.create_vnf_scale,
                          self.context, dummy_vnf_obj['id'],
                          vnf_scale)

    def test_scale_vnf_with_invalid_policy_type(self):
        dummy_vnf_obj, vnf_scale = self._get_scaling_vnf('in',
                                                invalid_policy_type=True)
        self.assertRaises(exceptions.VnfPolicyTypeInvalid,
                          self.vnfm_plugin.create_vnf_scale,
                          self.context, dummy_vnf_obj['id'], vnf_scale)

    def test_scale_vnf_with_invalid_policy_action(self):
        dummy_vnf_obj, vnf_scale = \
            self._get_scaling_vnf('test_invalid_policy_action')
        self.assertRaises(exceptions.VnfPolicyActionInvalid,
                          self.vnfm_plugin.create_vnf_scale,
                          self.context, dummy_vnf_obj['id'], vnf_scale)

    def test_scale_vnf_scale_wait_failed_exception(self):
        dummy_vnf_obj, vnf_scale = \
            self._get_scaling_vnf('in')
        self.scale_wait.side_effect = vnfm.VNFScaleWaitFailed(
            reason='test')
        self.assertRaises(vnfm.VNFScaleWaitFailed,
                          self.vnfm_plugin.create_vnf_scale,
                          self.context, dummy_vnf_obj['id'], vnf_scale)

    def _get_dummy_vnf(self, vnfd_template, status='ACTIVE'):
        dummy_vnf = utils.get_dummy_vnf()
        dummy_vnf['vnfd']['attributes']['vnfd'] = vnfd_template
        dummy_vnf['status'] = status
        dummy_vnf['instance_id'] = '4c00108e-c69d-4624-842d-389c77311c1d'
        dummy_vnf['vim_id'] = '437ac8ef-a8fb-4b6e-8d8a-a5e86a376e8b'
        return dummy_vnf

    def _create_vnf_trigger_data(self, policy_name, action_value):
        vnf_id = "6261579e-d6f3-49ad-8bc3-a9cb974778fe"
        trigger_request = {"trigger": {"action_name": action_value, "params": {
            "credential": "026kll6n", "data": {"current": "alarm",
                                               'alarm_id':
                                    "b7fa9ffd-0a4f-4165-954b-5a8d0672a35f"}},
            "policy_name": policy_name}}
        expected_result = {"action_name": action_value, "params": {
            "credential": "026kll6n", "data": {"current": "alarm",
            "alarm_id": "b7fa9ffd-0a4f-4165-954b-5a8d0672a35f"}},
            "policy_name": policy_name}
        return vnf_id, trigger_request, expected_result

    @patch('tacker.vnfm.policy_actions.autoscaling.autoscaling.'
           'VNFActionAutoscaling.execute_action')
    def _test_create_vnf_trigger(self, mock_execute_action,
                                 policy_name, action_value):
        vnf_id, trigger_request, expected_result = self.\
            _create_vnf_trigger_data(policy_name, action_value)
        self._vnf_alarm_monitor.process_alarm_for_vnf.return_value = True
        trigger_result = self.vnfm_plugin.create_vnf_trigger(self.context,
                                                    vnf_id, trigger_request)
        self.assertEqual(expected_result, trigger_result)

    @patch('tacker.db.vnfm.vnfm_db.VNFMPluginDb.get_vnf')
    def test_create_vnf_trigger_respawn(self, mock_get_vnf):
        dummy_vnf = self._get_dummy_vnf(
            utils.vnfd_alarm_respawn_tosca_template)
        mock_get_vnf.return_value = dummy_vnf
        self._test_create_vnf_trigger(policy_name="vdu_hcpu_usage_respawning",
                                      action_value="respawn")

    @patch('tacker.db.vnfm.vnfm_db.VNFMPluginDb.get_vnf')
    def test_create_vnf_trigger_scale(self, mock_get_vnf):
        dummy_vnf = self._get_dummy_vnf(
            utils.vnfd_alarm_scale_tosca_template)
        mock_get_vnf.return_value = dummy_vnf
        self._test_create_vnf_trigger(policy_name="vdu_hcpu_usage_scaling_out",
                                      action_value="SP1-out")

    @patch('tacker.db.vnfm.vnfm_db.VNFMPluginDb.get_vnf')
    def test_create_vnf_trigger_multi_actions(self, mock_get_vnf):
        dummy_vnf = self._get_dummy_vnf(
            utils.vnfd_alarm_multi_actions_tosca_template)
        mock_get_vnf.return_value = dummy_vnf
        self._test_create_vnf_trigger(policy_name="mon_policy_multi_actions",
                                      action_value="respawn&log")

    @patch('tacker.db.vnfm.vnfm_db.VNFMPluginDb.get_vnf')
    def test_create_vnf_trigger_without_policy_actions(self, mock_get_vnf):
        dummy_vnf = self._get_dummy_vnf(
            utils.vnfd_alarm_multi_actions_tosca_template)
        mock_get_vnf.return_value = dummy_vnf
        vnf_id, trigger_request, _ = self._create_vnf_trigger_data(
            "mon_policy_multi_actions", "respawn&log")
        self._vnf_alarm_monitor.process_alarm_for_vnf.return_value = False
        self.assertRaises(exceptions.AlarmUrlInvalid,
                          self.vnfm_plugin.create_vnf_trigger,
                          self.context,
                          vnf_id, trigger_request)

    @patch('tacker.db.vnfm.vnfm_db.VNFMPluginDb.get_vnf')
    def test_create_vnf_trigger_with_invalid_policy_name(self, mock_get_vnf):
        dummy_vnf = self._get_dummy_vnf(
            utils.vnfd_alarm_multi_actions_tosca_template)
        mock_get_vnf.return_value = dummy_vnf
        vnf_id, trigger_request, _ = self._create_vnf_trigger_data(
            "invalid_policy_name", "respawn&log")
        self.assertRaises(exceptions.TriggerNotFound,
                          self.vnfm_plugin.create_vnf_trigger,
                          self.context,
                          vnf_id, trigger_request)

    @patch('tacker.db.vnfm.vnfm_db.VNFMPluginDb.get_vnf')
    @patch('tacker.vnfm.plugin.LOG')
    def test_create_vnf_trigger_scale_with_invalid_vnf_status(self,
                                                    mock_log, mock_get_vnf):
        dummy_vnf = self._get_dummy_vnf(utils.vnfd_alarm_scale_tosca_template)
        dummy_vnf['status'] = "PENDING_CREATE"
        mock_get_vnf.return_value = dummy_vnf
        vnf_id, trigger_request, expected_result = self. \
            _create_vnf_trigger_data("vdu_hcpu_usage_scaling_out", "SP1-out")
        expected_error_msg = (_("Scaling Policy action skipped due to status"
                                ' %(status)s for vnf %(vnfid)s') %
                              {'status': dummy_vnf['status'],
                               'vnfid': dummy_vnf['id']})
        self._vnf_alarm_monitor.process_alarm_for_vnf.return_value = True
        trigger_result = self.vnfm_plugin.create_vnf_trigger(self.context,
                                                     vnf_id, trigger_request)

        mock_log.info.assert_called_with(expected_error_msg)
        self.assertEqual(expected_result, trigger_result)

    @patch('tacker.db.vnfm.vnfm_db.VNFMPluginDb.get_vnf')
    def test_get_vnf_policies(self, mock_get_vnf):
        vnf_id = "6261579e-d6f3-49ad-8bc3-a9cb974778fe"
        dummy_vnf = self._get_dummy_vnf(
            utils.vnfd_alarm_respawn_tosca_template)
        mock_get_vnf.return_value = dummy_vnf
        policies = self.vnfm_plugin.get_vnf_policies(self.context, vnf_id,
            filters={'name': 'vdu1_cpu_usage_monitoring_policy'})
        self.assertEqual(1, len(policies))

    @mock.patch('tacker.vnfm.plugin.toscautils.get_mgmt_driver')
    def test_mgmt_driver(self, mock_get_mgmt_driver):
        mock_get_mgmt_driver.return_value = 'dummy_mgmt_driver'

        vnfd_obj = utils.get_dummy_vnfd_obj()
        self.assertRaises(vnfm.InvalidMgmtDriver,
                          self.vnfm_plugin.create_vnfd,
                          self.context, vnfd_obj)

    @mock.patch('tacker.vnfm.plugin.VNFMPlugin.get_vnf_policies')
    def test_get_vnf_policy_by_type(self, mock_get_vnf_policies):
        mock_get_vnf_policies.return_value = None

        self.assertRaises(exceptions.VnfPolicyTypeInvalid,
                          self.vnfm_plugin.get_vnf_policy_by_type,
                          self.context,
                          uuidutils.generate_uuid(),
                          policy_type='invalid_policy_type')

    @patch('tacker.vnfm.infra_drivers.openstack.openstack.OpenStack.'
           'heal_vdu')
    @mock.patch('tacker.vnfm.monitor.VNFMonitor.update_hosting_vnf')
    def test_heal_vnf_vdu(self, mock_update_hosting_vnf, mock_heal_vdu):
        self._insert_dummy_vnf_template()
        dummy_device_obj = self._insert_dummy_vnf()
        additional_params_obj = heal_vnf_request.HealVnfAdditionalParams(
            parameter='VDU1',
            cause=["Unable to reach while monitoring resource: 'VDU1'"])
        heal_request_data_obj = heal_vnf_request.HealVnfRequest(
            stack_id=dummy_device_obj['instance_id'],
            cause='VNF monitoring fails.',
            additional_params=[additional_params_obj])
        result = self.vnfm_plugin.heal_vnf(self.context,
                                           dummy_device_obj['id'],
                                           heal_request_data_obj)
        self.assertIsNotNone(result)
        self.assertEqual(dummy_device_obj['id'], result['id'])
        self.assertIn('instance_id', result)
        self.assertIn('status', result)
        self.assertIn('attributes', result)
        self.assertIn('mgmt_ip_address', result)
        self.assertIn('updated_at', result)
        self.assertEqual('ACTIVE', result['status'])
        mock_heal_vdu.assert_called_with(plugin=self.vnfm_plugin,
            context=self.context, vnf_dict=mock.ANY,
            heal_request_data_obj=heal_request_data_obj)

    @patch('tacker.db.vnfm.vnfm_db.VNFMPluginDb.get_vnf')
    def test_create_vnf_trigger_scale_with_reservation(self, mock_get_vnf):
        dummy_vnf = self._get_dummy_vnf(
            utils.vnfd_instance_reservation_alarm_scale_tosca_template)
        mock_get_vnf.return_value = dummy_vnf
        self._test_create_vnf_trigger(policy_name="start_actions",
                                      action_value="SP_RSV-out")

    def test_create_placement_constraint(self):
        res_str = '[{"id_type": "RES_MGMT", "resource_id": ' + \
            '"2c6e5cc7-240d-4458-a683-1fe648351200", ' + \
            '"vim_connection_id": ' + \
            '"2a63bee3-0c43-4568-bcfa-b0cb733e064c"}]'
        placemnt = models.PlacementConstraint(
            id='c2947d8a-2c67-4e8f-ad6f-c0889b351c17',
            vnf_instance_id='7ddc38c3-a116-48b0-bfc1-68d7f306f467',
            affinity_or_anti_affinity='ANTI_AFFINITY',
            scope='ZONE',
            server_group_name='my_compute_placement_policy',
            resource=res_str,
            deleted_at=datetime.min)
        pls_list = [placemnt]
        vnf_inst = models.VnfInstance(
            id='7ddc38c3-a116-48b0-bfc1-68d7f306f467',
            vnf_provider=' ',
            vnf_product_name=' ',
            vnf_software_version=' ',
            vnfd_version=' ',
            vnfd_id='8d86480e-d4e6-4ee0-ba4d-08217118d6cb',
            instantiation_state=' ',
            tenant_id='9b3f0518-bf6b-4982-af32-d282ce577c8f',
            created_at=datetime(
                2020, 1, 1, 1, 1, 1,
                tzinfo=iso8601.UTC),
            vnf_pkg_id=uuidutils.generate_uuid())
        self.context.session.add(vnf_inst)
        self.context.session.flush()

        self.vnfm_plugin.create_placement_constraint(
            self.context, pls_list)

    def test_get_placement_constraint(self):
        res_str = '[{"id_type": "RES_MGMT", "resource_id": ' + \
            '"2c6e5cc7-240d-4458-a683-1fe648351200", ' + \
            '"vim_connection_id": ' + \
            '"2a63bee3-0c43-4568-bcfa-b0cb733e064c"}]'
        placemnt = models.PlacementConstraint(
            id='c2947d8a-2c67-4e8f-ad6f-c0889b351c17',
            vnf_instance_id='7ddc38c3-a116-48b0-bfc1-68d7f306f467',
            affinity_or_anti_affinity='ANTI_AFFINITY',
            scope='ZONE',
            server_group_name='my_compute_placement_policy',
            resource=res_str,
            deleted_at=datetime.min)
        vnf_inst = models.VnfInstance(
            id='7ddc38c3-a116-48b0-bfc1-68d7f306f467',
            vnf_provider=' ',
            vnf_product_name=' ',
            vnf_software_version=' ',
            vnfd_version=' ',
            vnfd_id='8d86480e-d4e6-4ee0-ba4d-08217118d6cb',
            instantiation_state=' ',
            tenant_id='9b3f0518-bf6b-4982-af32-d282ce577c8f',
            created_at=datetime(
                2020, 1, 1, 1, 1, 1,
                tzinfo=iso8601.UTC),
            vnf_pkg_id=uuidutils.generate_uuid())
        self.context.session.add(vnf_inst)
        self.context.session.flush()
        self.context.session.add(placemnt)
        self.context.session.flush()

        res = self.vnfm_plugin.get_placement_constraint(
            self.context, '7ddc38c3-a116-48b0-bfc1-68d7f306f467')
        self.assertEqual(1, len(res))

    def test_update_placement_constraint_heal(self):
        res_str = '[{"id_type": "RES_MGMT", "resource_id": ' + \
            '"2c6e5cc7-240d-4458-a683-1fe648351200", ' + \
            '"vim_connection_id": ' + \
            '"2a63bee3-0c43-4568-bcfa-b0cb733e064c"}]'
        placemnt = models.PlacementConstraint(
            id='c2947d8a-2c67-4e8f-ad6f-c0889b351c17',
            vnf_instance_id='7ddc38c3-a116-48b0-bfc1-68d7f306f467',
            affinity_or_anti_affinity='ANTI_AFFINITY',
            scope='ZONE',
            server_group_name='my_compute_placement_policy',
            resource=res_str,
            deleted_at=datetime.min)
        res_str2 = '[{"id_type": "GRANT", "resource_id": ' + \
            '"4cef1b7e-8e5f-430e-b32e-a7585a61d61c"}]'
        placemnt2 = models.PlacementConstraint(
            id='c2947d8a-2c67-4e8f-ad6f-c0889b351c17',
            vnf_instance_id='7ddc38c3-a116-48b0-bfc1-68d7f306f467',
            affinity_or_anti_affinity='ANTI_AFFINITY',
            scope='ZONE',
            server_group_name='my_compute_placement_policy',
            resource=res_str2,
            deleted_at=datetime.min)
        vnf_inst = models.VnfInstance(
            id='7ddc38c3-a116-48b0-bfc1-68d7f306f467',
            vnf_provider=' ',
            vnf_product_name=' ',
            vnf_software_version=' ',
            vnfd_version=' ',
            vnfd_id='8d86480e-d4e6-4ee0-ba4d-08217118d6cb',
            instantiation_state=' ',
            tenant_id='9b3f0518-bf6b-4982-af32-d282ce577c8f',
            created_at=datetime(
                2020, 1, 1, 1, 1, 1,
                tzinfo=iso8601.UTC),
            vnf_pkg_id=uuidutils.generate_uuid())
        self.context.session.add(vnf_inst)
        self.context.session.flush()
        self.context.session.add(placemnt)
        self.context.session.flush()

        vnf_info = {}
        vnf_info['grant'] = objects.Grant()
        placement_obj_list = []
        placement_obj_list.append(placemnt2)
        vnf_info['placement_obj_list'] = placement_obj_list

        insta = fakes.return_vnf_instance('INSTANTIATED')
        vnfc = objects.VnfcResourceInfo()
        vnfc.id = '4cef1b7e-8e5f-430e-b32e-a7585a61d61c'
        vnfc.vdu_id = 'VDU1'
        c_rsc = objects.ResourceHandle()
        c_rsc.vim_connection_id = '2a63bee3-0c43-4568-bcfa-b0cb733e064c'
        c_rsc.resource_id = '9aa1e075-2aa1-46ce-a27a-35a581190219'
        vnfc.compute_resource = c_rsc
        insta.instantiated_vnf_info.vnfc_resource_info.append(vnfc)

        self.vnfm_plugin.update_placement_constraint_heal(
            self.context, vnf_info, insta)

    def test_delete_placement_constraint(self):
        res_str = '[{"id_type": "RES_MGMT", "resource_id": ' + \
            '"2c6e5cc7-240d-4458-a683-1fe648351200", ' + \
            '"vim_connection_id": ' + \
            '"2a63bee3-0c43-4568-bcfa-b0cb733e064c"}]'
        placemnt = models.PlacementConstraint(
            id='c2947d8a-2c67-4e8f-ad6f-c0889b351c17',
            vnf_instance_id='7ddc38c3-a116-48b0-bfc1-68d7f306f467',
            affinity_or_anti_affinity='ANTI_AFFINITY',
            scope='ZONE',
            server_group_name='my_compute_placement_policy',
            resource=res_str,
            deleted_at=datetime.min)
        vnf_inst = models.VnfInstance(
            id='7ddc38c3-a116-48b0-bfc1-68d7f306f467',
            vnf_provider=' ',
            vnf_product_name=' ',
            vnf_software_version=' ',
            vnfd_version=' ',
            vnfd_id='8d86480e-d4e6-4ee0-ba4d-08217118d6cb',
            instantiation_state=' ',
            tenant_id='9b3f0518-bf6b-4982-af32-d282ce577c8f',
            created_at=datetime(
                2020, 1, 1, 1, 1, 1,
                tzinfo=iso8601.UTC),
            vnf_pkg_id=uuidutils.generate_uuid())
        self.context.session.add(vnf_inst)
        self.context.session.flush()
        self.context.session.add(placemnt)
        self.context.session.flush()

        self.vnfm_plugin.delete_placement_constraint(
            self.context, '7ddc38c3-a116-48b0-bfc1-68d7f306f467')

    def test_update_vnf_rollback_pre_scale(self):
        vnf_info = {}
        vnf_lcm_op_occ = vnflcm_fakes.vnflcm_rollback()
        vnf_info['vnf_lcm_op_occ'] = vnf_lcm_op_occ
        vnf_info['id'] = uuidutils.generate_uuid()
        self.vnfm_plugin._update_vnf_rollback_pre(
            self.context, vnf_info)

    def test_update_vnf_rollback_pre_insta(self):
        vnf_info = {}
        vnf_lcm_op_occ = vnflcm_fakes.vnflcm_rollback_insta()
        vnf_info['vnf_lcm_op_occ'] = vnf_lcm_op_occ
        vnf_info['id'] = uuidutils.generate_uuid()
        self.vnfm_plugin._update_vnf_rollback_pre(
            self.context, vnf_info)

    def test_update_vnf_rollback_scale(self):
        vnf_info = {}
        vnf_lcm_op_occ = vnflcm_fakes.vnflcm_rollback()
        vnf_info['vnf_lcm_op_occ'] = vnf_lcm_op_occ
        vnf_info['id'] = uuidutils.generate_uuid()
        self.vnfm_plugin._update_vnf_rollback(
            self.context, vnf_info,
            'ERROR', 'ACTIVE')

    def test_update_vnf_rollback_insta(self):
        vnf_info = {}
        vnf_lcm_op_occ = vnflcm_fakes.vnflcm_rollback_insta()
        vnf_info['vnf_lcm_op_occ'] = vnf_lcm_op_occ
        vnf_info['id'] = uuidutils.generate_uuid()
        self.vnfm_plugin._update_vnf_rollback(
            self.context, vnf_info,
            'ERROR', 'INACTIVE')

    def test_update_vnf_rollback_status_err_scale(self):
        vnf_info = {}
        vnf_lcm_op_occ = vnflcm_fakes.vnflcm_rollback()
        vnf_info['vnf_lcm_op_occ'] = vnf_lcm_op_occ
        vnf_info['id'] = uuidutils.generate_uuid()
        self.vnfm_plugin.update_vnf_rollback_status_err(
            self.context, vnf_info)

    def test_update_vnf_rollback_status_err_insta(self):
        vnf_info = {}
        vnf_lcm_op_occ = vnflcm_fakes.vnflcm_rollback_insta()
        vnf_info['vnf_lcm_op_occ'] = vnf_lcm_op_occ
        vnf_info['id'] = uuidutils.generate_uuid()
        self.vnfm_plugin.update_vnf_rollback_status_err(
            self.context, vnf_info)
