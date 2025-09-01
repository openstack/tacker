# Copyright (C) 2025 KDDI
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

from oslo_config import cfg
from oslo_config import fixture as config
from tacker.conf import vnf_lcm as vnf_lcm_conf
from tacker.objects import fields
from tacker.vnfm.infra_drivers.openstack import openstack as os_drv
from types import SimpleNamespace
import unittest
from unittest import mock


class TestHealStorageToggleMin(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.conf_fix = config.Config(cfg.CONF)
        self.conf_fix.setUp()
        vnf_lcm_conf.register_opts(cfg.CONF)

        self.driver = os_drv.OpenStack()
        self.recorded = []

        hc_patch = mock.patch(
            'tacker.vnfm.infra_drivers.openstack.openstack.hc.HeatClient')
        self.addCleanup(hc_patch.stop)
        FakeHC = hc_patch.start()
        hc = FakeHC.return_value
        hc.get.return_value = SimpleNamespace(stack_status='CREATE_COMPLETE')

        def rec_mark_unhealthy(*, stack_id, resource_name, **_):
            self.recorded.append(resource_name)

        hc.resource_mark_unhealthy.side_effect = rec_mark_unhealthy
        hc.update.return_value = None

        mock.patch(
            'tacker.vnfm.infra_drivers.openstack.openstack.vnflcm_utils.'
            'get_base_nest_hot_dict',
            return_value=({}, {})
        ).start()
        mock.patch(
            'tacker.vnfm.infra_drivers.openstack.openstack.vnflcm_utils.'
            'get_stack_param',
            return_value={}
        ).start()
        mock.patch(
            'tacker.vnfm.infra_drivers.openstack.openstack.manager.'
            'TackerManager.get_service_plugins',
            return_value={'VNFM': SimpleNamespace(
                get_vnf=lambda *a, **k: {'vnfd_id': 'vnfd-1'})}
        ).start()
        mock.patch(
            'tacker.vnfm.infra_drivers.openstack.openstack.objects.'
            'VnfLcmOpOcc.get_by_vnf_instance_id',
            return_value=SimpleNamespace(
                error_point=fields.ErrorPoint.PRE_VIM_CONTROL)
        ).start()

        mock.patch.object(
            os_drv.OpenStack, '_get_stack_resources',
            return_value={
                'stack-123': {
                    'VDU1': {'physical_resource_id': 'srv-001'},
                    'VDU1-volume': {'physical_resource_id': 'vol-001'},
                    'child_stack': False
                }
            }
        ).start()

        mock.patch(
            'tacker.vnfm.infra_drivers.openstack.openstack.vnflcm_utils.'
            'get_vnfd_dict',
            return_value={
                'flavours': {'flv': {}},
                'topology_template': {}
            }
        ).start()

        vnfc = SimpleNamespace(
            id='vnfc-1',
            vdu_id='VDU1',
            compute_resource=SimpleNamespace(resource_id='srv-001'),
            storage_resource_ids=['s-1'],
        )
        vstorage = SimpleNamespace(
            id='s-1',
            virtual_storage_desc_id='VDU1-volume',
            storage_resource=SimpleNamespace(resource_id='vol-001')
        )
        self.vnf_instance = SimpleNamespace(
            id='vnf-1',
            vnfd_id='vnfd-1',
            instantiated_vnf_info=SimpleNamespace(
                instance_id='stack-123',
                flavour_id='flv',
                vnfc_resource_info=[vnfc],
                virtual_storage_resource_info=[vstorage],
                additional_params=None
            )
        )
        from tacker.objects import vim_connection
        self.vim_info = vim_connection.VimConnectionInfo(
            vim_id='vim-1',
            vim_type='openstack',
            interface_info={},
            access_info={'region': 'RegionOne'},
        )

    def _heal(self, *, default=None, req_val=None, custom_key=None):
        if default is not None:
            self.conf_fix.config(group='vnf_lcm',
                                 heal_vnfc_block_storage=bool(default))
        if custom_key is not None:
            self.conf_fix.config(group='vnf_lcm',
                                 heal_include_block_storage_key=custom_key)
        key = custom_key or cfg.CONF.vnf_lcm.heal_include_block_storage_key
        add_params = {} if req_val is None else {key: req_val}
        heal_req = SimpleNamespace(vnfc_instance_id=['vnfc-1'],
                                   cause=None,
                                   additional_params=add_params)
        self.recorded.clear()
        self.driver.heal_vnf(None, self.vnf_instance, self.vim_info, heal_req)
        return set(self.recorded)

    def test_default_true_when_key_omitted(self):
        marked = self._heal(default=True, req_val=None)
        self.assertEqual({'VDU1', 'VDU1-volume'}, marked)

    def test_default_false_when_key_omitted(self):
        marked = self._heal(default=False, req_val=None)
        self.assertEqual({'VDU1'}, marked)

    def test_request_overrides_true(self):
        marked = self._heal(default=False, req_val=True)
        self.assertEqual({'VDU1', 'VDU1-volume'}, marked)

    def test_request_overrides_false(self):
        marked = self._heal(default=True, req_val=False)
        self.assertEqual({'VDU1'}, marked)

    def test_custom_key(self):
        marked = self._heal(
            default=False, req_val=True, custom_key='recreate_block')
        self.assertEqual({'VDU1', 'VDU1-volume'}, marked)
