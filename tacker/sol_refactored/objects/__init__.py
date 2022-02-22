# Copyright (C) 2021 Nippon Telegraph and Telephone Corporation
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

from tacker.sol_refactored.objects.common import fields  # noqa

# NOTE: You may scratch your head as you see code that imports
# this module and then accesses attributes for objects such as Instance,
# etc, yet you do not see these attributes in here. Never fear, there is
# a little bit of magic. When objects are registered, an attribute is set
# on this module automatically, pointing to the newest/latest version of
# the object.


def register_all():
    # NOTE: You must make sure your object gets imported in this
    # function in order for it to be registered by services that may
    # need to receive it via RPC.
    objects_root = 'tacker.sol_refactored.objects'
    __import__(objects_root + '.common.cp_protocol_data')
    __import__(objects_root + '.common.ext_link_port_data')
    __import__(objects_root + '.common.ext_managed_virtual_link_data')
    __import__(objects_root + '.common.ext_virtual_link_data')
    __import__(objects_root + '.common.ip_over_ethernet_address_data')
    __import__(objects_root + '.common.link')
    __import__(objects_root + '.common.notification_link')
    __import__(objects_root + '.common.problem_details')
    __import__(objects_root + '.common.resource_handle')
    __import__(objects_root + '.common.subscription_authentication')
    __import__(objects_root + '.common.vim_connection_info')
    __import__(objects_root + '.common.vnf_ext_cp_config')
    __import__(objects_root + '.common.vnf_ext_cp_data')
    __import__(objects_root + '.common.vnf_instance_subscription_filter')
    __import__(objects_root + '.v1.constraint_resource_ref')
    __import__(objects_root + '.v1.fields')
    __import__(objects_root + '.v1.grant_info')
    __import__(objects_root + '.v1.grant')
    __import__(objects_root + '.v1.grant_request')
    __import__(objects_root + '.v1.placement_constraint')
    __import__(objects_root + '.v1.resource_definition')
    __import__(objects_root + '.v1.snapshot_resource_definition')
    __import__(objects_root + '.v1.vim_compute_resource_flavour')
    __import__(objects_root + '.v1.vim_constraint')
    __import__(objects_root + '.v1.vim_snapshot_resource')
    __import__(objects_root + '.v1.vim_software_image')
    __import__(objects_root + '.v1.zone_group_info')
    __import__(objects_root + '.v1.zone_info')
    __import__(objects_root + '.v2.affected_ext_link_port')
    __import__(objects_root + '.v2.affected_virtual_link')
    __import__(objects_root + '.v2.affected_virtual_storage')
    __import__(objects_root + '.v2.affected_vnfc')
    __import__(objects_root + '.v2.cancel_mode')
    __import__(objects_root + '.v2.change_current_vnf_pkg_request')
    __import__(objects_root + '.v2.change_ext_vnf_connectivity_request')
    __import__(objects_root + '.v2.change_vnf_flavour_request')
    __import__(objects_root + '.v2.cp_protocol_info')
    __import__(objects_root + '.v2.create_vnf_pkg_info_request')
    __import__(objects_root + '.v2.create_vnf_request')
    __import__(objects_root + '.v2.create_vnf_snapshot_info_request')
    __import__(objects_root + '.v2.create_vnf_snapshot_request')
    __import__(objects_root + '.v2.external_artifacts_access_config')
    __import__(objects_root + '.v2.ext_link_port_info')
    __import__(objects_root + '.v2.ext_managed_virtual_link_info')
    __import__(objects_root + '.v2.ext_virtual_link_info')
    __import__(objects_root + '.v2.fields')
    __import__(objects_root + '.v2.heal_vnf_request')
    __import__(objects_root + '.v2.instantiate_vnf_request')
    __import__(objects_root + '.v2.ip_over_ethernet_address_info')
    __import__(objects_root + '.v2.lccn_links')
    __import__(objects_root + '.v2.lccn_subscription')
    __import__(objects_root + '.v2.lccn_subscription_request')
    __import__(objects_root + '.v2.lifecycle_change_notifications_filter')
    __import__(objects_root + '.v2.modifications_triggered_by_vnf_pkg_change')
    __import__(objects_root + '.v2.monitoring_parameter')
    __import__(objects_root + '.v2.operate_vnf_request')
    __import__(objects_root + '.v2.pkgm_links')
    __import__(objects_root + '.v2.pkgm_notification_filter')
    __import__(objects_root + '.v2.pkgm_subscription_request')
    __import__(objects_root + '.v2.revert_to_vnf_snapshot_request')
    __import__(objects_root + '.v2.scale_info')
    __import__(objects_root + '.v2.scale_vnf_request')
    __import__(objects_root + '.v2.scale_vnf_to_level_request')
    __import__(objects_root + '.v2.terminate_vnf_request')
    __import__(objects_root + '.v2.upload_vnf_package_from_uri_request')
    __import__(objects_root + '.v2.virtual_storage_resource_info')
    __import__(objects_root + '.v2.vnfc_info')
    __import__(objects_root + '.v2.vnfc_info_modifications')
    __import__(objects_root + '.v2.vnfc_resource_info')
    __import__(objects_root + '.v2.vnfc_snapshot_info')
    __import__(objects_root + '.v2.vnf_ext_cp_info')
    __import__(objects_root + '.v2.vnf_identifier_creation_notification')
    __import__(objects_root + '.v2.vnf_identifier_deletion_notification')
    __import__(objects_root + '.v2.vnf_info_modification_request')
    __import__(objects_root + '.v2.vnf_info_modifications')
    __import__(objects_root + '.v2.vnf_instance')
    __import__(objects_root + '.v2.vnf_lcm_operation_occurrence_notification')
    __import__(objects_root + '.v2.vnf_lcm_op_occ')
    __import__(objects_root + '.v2.vnf_link_port_data')
    __import__(objects_root + '.v2.vnf_link_port_info')
    __import__(objects_root + '.v2.vnf_package_artifact_info')
    __import__(objects_root + '.v2.vnf_package_change_notification')
    __import__(objects_root + '.v2.vnf_package_onboarding_notification')
    __import__(objects_root + '.v2.vnf_package_software_image_info')
    __import__(objects_root + '.v2.vnf_pkg_info_modifications')
    __import__(objects_root + '.v2.vnf_pkg_info')
    __import__(objects_root + '.v2.vnf_snapshot_info_modification_request')
    __import__(objects_root + '.v2.vnf_snapshot_info_modifications')
    __import__(objects_root + '.v2.vnf_snapshot_info')
    __import__(objects_root + '.v2.vnf_snapshot')
    __import__(objects_root + '.v2.vnf_state_snapshot_info')
    __import__(objects_root + '.v2.vnf_virtual_link_resource_info')
