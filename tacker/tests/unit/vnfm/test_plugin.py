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

import ddt
import iso8601
from oslo_utils import uuidutils
import yaml

from tacker import context
from tacker.db.db_sqlalchemy import models
from tacker.db.nfvo import nfvo_db
from tacker.db.vnfm import vnfm_db
from tacker import objects
from tacker.tests.unit.conductor import fakes
from tacker.tests.unit.db import base as db_base
from tacker.tests.unit.db import utils
from tacker.tests.unit.vnflcm import fakes as vnflcm_fakes
from tacker.vnfm import plugin


class FakeDriverManager(mock.Mock):
    def invoke(self, *args, **kwargs):
        if 'create' in args:
            return uuidutils.generate_uuid()

        if 'get_resource_info' in args:
            return {'resources': {'name': 'dummy_vnf',
                                  'type': 'dummy',
                                  'id': uuidutils.generate_uuid()}}


class FakeVimClient(mock.Mock):
    pass


@ddt.ddt
class TestVNFMPlugin(db_base.SqlTestCase):
    def setUp(self):
        super(TestVNFMPlugin, self).setUp()
        self.addCleanup(mock.patch.stopall)
        self.context = context.get_admin_context()
        self._mock_vim_client()
        self._stub_get_vim()
        self._insert_dummy_vim()
        self.vnfm_plugin = plugin.VNFMPlugin()
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
