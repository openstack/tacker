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


from oslo_log import log as logging

from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored import objects


LOG = logging.getLogger(__name__)  # not used at the moment


def get_inst(context, inst_id):
    inst = objects.VnfInstanceV2.get_by_id(context, inst_id)
    if inst is None:
        raise sol_ex.VnfInstanceNotFound(inst_id=inst_id)
    return inst


def get_inst_all(context):
    return objects.VnfInstanceV2.get_all(context)


def inst_href(inst_id, endpoint):
    return "{}/vnflcm/v2/vnf_instances/{}".format(endpoint, inst_id)


def make_inst_links(inst, endpoint):
    links = objects.VnfInstanceV2_Links()
    self_href = inst_href(inst.id, endpoint)
    links.self = objects.Link(href=self_href)
    if inst.instantiationState == 'NOT_INSTANTIATED':
        links.instantiate = objects.Link(href=self_href + "/instantiate")
    else:  # 'INSTANTIATED'
        links.terminate = objects.Link(href=self_href + "/terminate")
        links.scale = objects.Link(href=self_href + "/scale")
        links.heal = objects.Link(href=self_href + "/heal")
        links.changeExtConn = objects.Link(href=self_href + "/change_ext_conn")
        links.changeVnfPkg = objects.Link(href=self_href + "/change_vnfpkg")
        # NOTE: add when the operation supported

    return links


# see IETF RFC 7396
def json_merge_patch(target, patch):
    if isinstance(patch, dict):
        if not isinstance(target, dict):
            target = {}
        for key, value in patch.items():
            if value is None:
                if key in target:
                    del target[key]
            else:
                target[key] = json_merge_patch(target.get(key), value)
        return target
    else:
        return patch


def select_vim_info(vim_connection_info):
    # NOTE: It is assumed that vimConnectionInfo has only one item
    # at the moment. If there are multiple items, it is uncertain
    # which item is selected.
    for vim_info in vim_connection_info.values():
        return vim_info
