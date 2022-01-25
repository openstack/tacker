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


from tacker.sol_refactored.api.policies import vnflcm_v2 as vnflcm_policy_v2
from tacker.sol_refactored.api import wsgi as sol_wsgi
from tacker.sol_refactored.controller import vnflcm_v2
from tacker.sol_refactored.controller import vnflcm_versions


class VnflcmVersions(sol_wsgi.SolAPIRouter):

    controller = sol_wsgi.SolResource(
        vnflcm_versions.VnfLcmVersionsController())
    route_list = [("/api_versions", {"GET": "index"})]


class VnflcmAPIRouterV2(sol_wsgi.SolAPIRouter):

    controller = sol_wsgi.SolResource(vnflcm_v2.VnfLcmControllerV2(),
                                      policy_name=vnflcm_policy_v2.POLICY_NAME)
    route_list = [
        ("/vnf_instances", {"GET": "index", "POST": "create"}),
        ("/vnf_instances/{id}",
         {"DELETE": "delete", "GET": "show", "PATCH": "update"}),
        ("/vnf_instances/{id}/instantiate", {"POST": "instantiate"}),
        ("/vnf_instances/{id}/heal", {"POST": "heal"}),
        ("/vnf_instances/{id}/terminate", {"POST": "terminate"}),
        ("/vnf_instances/{id}/scale", {"POST": "scale"}),
        ("/vnf_instances/{id}/change_ext_conn", {"POST": "change_ext_conn"}),
        ("/vnf_instances/{id}/change_vnfpkg", {"POST": "change_vnfpkg"}),
        ("/api_versions", {"GET": "api_versions"}),
        ("/subscriptions", {"GET": "subscription_list",
                            "POST": "subscription_create"}),
        ("/subscriptions/{id}", {"GET": "subscription_show",
                                 "DELETE": "subscription_delete"}),
        ("/vnf_lcm_op_occs", {"GET": "lcm_op_occ_list"}),
        ("/vnf_lcm_op_occs/{id}/retry", {"POST": "lcm_op_occ_retry"}),
        ("/vnf_lcm_op_occs/{id}/rollback", {"POST": "lcm_op_occ_rollback"}),
        ("/vnf_lcm_op_occs/{id}/fail", {"POST": "lcm_op_occ_fail"}),
        # NOTE: 'DELETE' is not defined in the specification. It is for test
        # use since it is convenient to be able to delete under development.
        # It is available when config parameter
        # v2_vnfm.test_enable_lcm_op_occ_delete set to True.
        ("/vnf_lcm_op_occs/{id}", {"GET": "lcm_op_occ_show",
                                   "DELETE": "lcm_op_occ_delete"})
    ]
