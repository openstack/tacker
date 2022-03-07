# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


from tacker.vnfm.lcm_user_data.abstract_user_data import AbstractUserData
import tacker.vnfm.lcm_user_data.utils as UserDataUtil

t_vdu = ('tosca.nodes.nfv.Vdu.Compute', )
t_blk = ('tosca.nodes.nfv.Vdu.VirtualBlockStorage', )
t_cpd = ('tosca.nodes.nfv.VduCp', 'tosca.nodes.nfv.VnfExtCp', )

t_anti_affinity = 'tosca.policies.nfv.AntiAffinityRule'
t_affinity = 'tosca.policies.nfv.AffinityRule'
t_grprule = (t_anti_affinity, t_affinity)
t_sc_aspect = ('tosca.policies.nfv.ScalingAspects')
t_vdu_sc_asp_delta = ('tosca.policies.nfv.VduScalingAspectDeltas')
t_vdu_init_delta = ('tosca.policies.nfv.VduInitialDelta')
t_inst_lv = ('tosca.policies.nfv.InstantiationLevels')
t_vdu_inst_lv = ('tosca.policies.nfv.VduInstantiationLevels')


def from_key_arrangement(value, key_arrangement):
    for key in key_arrangement:
        if isinstance(value, list) and key >= len(value):
            return None
        if isinstance(value, dict) and key not in value:
            return None
        value = value[key]
    return value


def get_volumes(value):
    bind_blk_names = dict()
    for idx, el in enumerate(value.get('requirements', [])):
        key = 'virtual_storage'
        if key not in el:
            continue
        vol_name = el[key]
        bind_blk_names[vol_name] = {'order': idx}
    return bind_blk_names


def generate_vdu_compute_dict(val):
    ret = dict()

    key_arrangement = [
        'capabilities',
        'virtual_compute',
        'properties',
        'requested_additional_capabilities',
        'properties',
        'requested_additional_capability_name'
    ]
    flavor_name = from_key_arrangement(val, key_arrangement)
    if flavor_name is not None:
        ret['flavor'] = flavor_name

    key_arrangement = ['properties', 'sw_image_data', 'name']
    image_name = from_key_arrangement(val, key_arrangement)
    if image_name is not None:
        ret['image'] = image_name

    key_arrangement = ['properties', 'boot_order', 0]
    boot_volume = from_key_arrangement(val, key_arrangement)
    if boot_volume is not None:
        ret['boot_volume'] = boot_volume

    volumes = get_volumes(val)
    if len(volumes) > 0:
        ret['volumes'] = volumes
    return ret


def generate_vdu_block_dict(val):
    ret = dict()
    key_arrangement = ['properties', 'sw_image_data', 'name']
    image_name = from_key_arrangement(val, key_arrangement)
    if image_name is not None:
        ret['image'] = image_name
    key = ('properties', 'virtual_block_storage_data', 'size_of_storage')
    volume_size = from_key_arrangement(val, key)
    if volume_size is not None:
        tmp = volume_size.split(" ", 1)
        front = float(tmp[0])
        end = "GB"
        if len(tmp) >= 2:
            end = tmp[1]
        if end == "PB":
            front *= 1000 * 1000
        elif end == "TB":
            front *= 1000
        elif end == "MB":
            front /= 1000
        elif end == "KB":
            front /= 1000 * 1000
        elif end == "B":
            front /= 1000 * 1000 * 1000
        ret['size'] = int(front)
    return ret


def bind_vdu_cpd(val):
    bind_vdu_name = None
    for el in val.get('requirements', []):
        if 'virtual_binding' not in el:
            continue
        bind_vdu_name = el['virtual_binding']
    order = from_key_arrangement(val, ('properties', 'order'))
    if order is None:
        order = 0
    return bind_vdu_name, order


def create_initial_param_dict(vnfd_dict):
    keys = ('topology_template', 'node_templates')
    node_templates = from_key_arrangement(vnfd_dict, keys)
    if node_templates is None:
        return dict()

    vdus = dict()
    blks = dict()
    cps = dict()
    # sequential scanning for each node templates object
    for rsc_id, val in node_templates.items():
        rsc_type = val.get("type", None)
        # in case of vdu compute
        if rsc_type in t_vdu:
            vdus[rsc_id] = generate_vdu_compute_dict(val)
        # in case of vdu block storage
        elif rsc_type in t_blk:
            blks[rsc_id] = generate_vdu_block_dict(val)
        # in case of vdu cpd
        elif rsc_type in t_cpd:
            bind_vdu_name, order = bind_vdu_cpd(val)
            if bind_vdu_name not in cps:
                cps[bind_vdu_name] = dict()
            cps[bind_vdu_name][rsc_id] = {"order": order}
        # unknown type, ignore

    # merge to single vdu info
    for name, info in vdus.items():
        # merge cps
        info['connection_points'] = cps.get(name, {})
        # merge volumes
        for vol_name, vol_info in info.get('volumes', {}).items():
            vol_info.update(blks.get(vol_name, {}))
        # set boot image form volume
        blk = info.get('boot_volume', None)
        if blk is None:
            continue
        info['image'] = blks[blk].get('image', None)

    return vdus


def get_cps_instantiate_parameters(inst_req_info):
    connection_points = dict()
    ext_vls = inst_req_info.ext_virtual_links
    if ext_vls is None:
        return {}

    for ext_vl in ext_vls:
        ext_cps = ext_vl.ext_cps
        net_rsc_id = ext_vl.resource_id
        if ext_cps is None:
            continue
        for ext_cp in ext_cps:
            cp_dict = dict()
            connection_points[ext_cp.cpd_id] = cp_dict
            cp_dict['network_id'] = net_rsc_id
            cp_configs = ext_cp.cp_config
            if cp_configs is None:
                continue
            for cp_config in ext_cp.cp_config:
                cp_list = list()
                cp_dict['subnets'] = cp_list
                cp_protos = cp_config.cp_protocol_data
                if cp_protos is None:
                    continue
                for cp_proto in cp_protos:
                    ipoe = cp_proto.ip_over_ethernet
                    if ipoe is None:
                        continue
                    addrs = ipoe.ip_addresses
                    if addrs is None:
                        continue
                    for addr in addrs:
                        port_dict = dict()
                        cp_list.append(port_dict)
                        if addr.subnet_id is not None:
                            port_dict['subnet_id'] = addr.subnet_id
                        ip_addrs = addr.fixed_addresses
                        if ip_addrs is not None:
                            port_dict['fixed_ip_addresses'] = ip_addrs
                        if addr.type is not None:
                            port_dict['ethertype'] = addr.type

    return connection_points


def get_policies(vnfd_dict):
    pols = dict()
    policies = vnfd_dict.get('topology_template', {}).get('policies', [])
    policies_dict = dict()
    for policy in policies:
        policies_dict.update(policy)
    for policy_name, policy_value in policies_dict.items():
        pol_type = policy_value.get('type', None)
        if pol_type in t_grprule:
            tgt_grp = from_key_arrangement(policy_value, ('targets', 0))
            rule = 'anti-affinity'
            if pol_type == t_affinity:
                rule = 'affinity'
            if 'groups' not in pols:
                pols['groups'] = dict()
            pols['groups'][tgt_grp] = rule
        elif pol_type in t_vdu_inst_lv:
            lvs = from_key_arrangement(policy_value, ('properties', 'levels'))
            if 'instantiation_levels' not in pols:
                pols['instantiation_levels'] = dict()
            inst_lvs = pols['instantiation_levels']
            tgts = policy_value.get('targets', [])
            for lv_name, lv_value in lvs.items():
                for tgt in tgts:
                    key = 'number_of_instances'
                    num_of_instance = lv_value.get(key, None)
                    if num_of_instance is None:
                        continue
                    if lv_name not in inst_lvs:
                        inst_lvs[lv_name] = dict()
                    if key not in inst_lvs[lv_name]:
                        inst_lvs[lv_name][key] = dict()
                    inst_lvs[lv_name][key][tgt] = num_of_instance
    return pols


def calculate_current_vdu_size(vnfd_dict, current_aspect):
    policies = vnfd_dict.get('topology_template', {}).get('policies', [])
    policies_dict = dict()
    for policy in policies:
        policies_dict.update(policy)
    aspects = {}
    vdu_aspect = {}
    for policy_name, policy_value in policies_dict.items():
        pol_type = policy_value.get('type', None)
        if pol_type in t_sc_aspect:
            key = ('properties', 'aspects')
            _aspects = from_key_arrangement(policy_value, key)
            for aspect_id, aspect_value in _aspects.items():
                max_scale_level = int(aspect_value.get('max_scale_level', 0))
                step_deltas = aspect_value.get('step_deltas', [])
            aspects[aspect_id] = {'max_scale_level': max_scale_level,
                                  'step_deltas': step_deltas}
        if pol_type in t_vdu_sc_asp_delta:
            key = ('properties', 'aspect')
            aspect_id = from_key_arrangement(policy_value, key)
            key = ('properties', 'deltas')
            deltas = from_key_arrangement(policy_value, key)
            aspect_deltas = {}
            for delta_id, value in deltas.items():
                num_of_ins_delta = int(value['number_of_instances'])
                if aspect_id not in aspect_deltas:
                    aspect_deltas[aspect_id] = {}
                aspect_deltas[aspect_id][delta_id] = num_of_ins_delta

            vdus = from_key_arrangement(policy_value, ('targets', ))
            for vdu in vdus:
                if vdu not in vdu_aspect:
                    vdu_aspect[vdu] = {}
                vdu_aspect[vdu]['aspects'] = aspect_deltas
        if pol_type in t_vdu_init_delta:
            key = ('properties', 'initial_delta', 'number_of_instances')
            initial_num = from_key_arrangement(policy_value, key)
            key = ('properties', 'initial_delta', 'number_of_instances')
            initial_num = from_key_arrangement(policy_value, key)
            vdus = from_key_arrangement(policy_value, ('targets', ))
            for vdu in vdus:
                if vdu not in vdu_aspect:
                    vdu_aspect[vdu] = {}
                vdu_aspect[vdu]['initial_delta'] = initial_num
    output = {}
    for vdu, vdu_aspect_value in vdu_aspect.items():
        vdu_num = vdu_aspect_value['initial_delta']
        if 'aspects' in vdu_aspect_value:
            for aspect_id, aspect_value in vdu_aspect_value['aspects'].items():
                current_level = current_aspect[aspect_id]
                deltas = aspects[aspect_id].get('step_deltas', [])
                max_scale_level = aspects[aspect_id].get('max_scale_level', 0)
                for i in range(max_scale_level - len(deltas)):
                    deltas.append(deltas[-1])
                for i in range(min(current_level, max_scale_level)):
                    delta_id = deltas[i]
                    vdu_num += aspect_value[delta_id]
        output[vdu] = vdu_num
    return output


class ETSICompatibleUserData(AbstractUserData):
    @staticmethod
    def instantiate(base_hot_dict=None, vnfd_dict=None,
                    inst_req_info=None, grant_info=None):
        # Create initial params from vnfd
        # about VDU information
        vdus = create_initial_param_dict(vnfd_dict)
        # Get connection points information(Like IP addr, etc.)
        # from VNF Instantiat Request, ExtVirtualLink section
        cps = get_cps_instantiate_parameters(inst_req_info)
        # Update connection point orders in VDU if present
        for vdu_name, vdu_value in vdus.items():
            vdu_cps = vdu_value.get('connection_points', {})
            for vdu_cp_id, vdu_cp_info in vdu_cps.items():
                if vdu_cp_id not in cps:
                    cps[vdu_cp_id] = dict()
                cps[vdu_cp_id].update(vdu_cp_info)
        # Get policies information from vnfd_dict
        # about instantiation levels and
        # affinity or anti-affinity server group information
        policies = get_policies(vnfd_dict)
        # Update VDU number of instance information
        # from policies to VDU
        selected_instantiation_level = inst_req_info.instantiation_level_id
        keys = ('instantiation_levels',
                selected_instantiation_level,
                'number_of_instances')
        num_of_instances = from_key_arrangement(policies, keys)
        if num_of_instances is not None:
            for vdu_name, vdu_value in vdus.items():
                num_of_instance = num_of_instances.get(vdu_name, None)
                if num_of_instance is None:
                    continue
                vdu_value.update({'number_of_instance': num_of_instance})
        # Get additional params from VNF InstantiateVnfRequest
        api_param = UserDataUtil.get_diff_base_hot_param_from_api(
            base_hot_dict, inst_req_info)

        return {"nfv": {"VDU": vdus, "CP": cps}, **api_param}

    @staticmethod
    def heal(base_hot_dict=None,
             vnfd_dict=None,
             heal_vnf_request=None,
             vnf_instances=None,
             inst_vnf_info=None,
             param=None, vnfc_resource_info=None):
        # Create initial params from vnfd
        # about VDU information
        vdus = create_initial_param_dict(vnfd_dict)

        # in each vnfc which requested heal api,
        # update vdu information from current vnfd
        vnfc_resource_info_list = vnfc_resource_info
        if not isinstance(vnfc_resource_info, list):
            vnfc_resource_info_list = [vnfc_resource_info]

        # Update VDU scale size from VNFD and current vnf scale level
        current_aspect = {}
        for scale_aspect in inst_vnf_info.scale_status:
            aspect_id = scale_aspect.aspect_id
            scale_level = scale_aspect.scale_level
            current_aspect[aspect_id] = scale_level
        size_of_vdus = calculate_current_vdu_size(vnfd_dict, current_aspect)
        for vdu_name, num_of_instance in size_of_vdus.items():
            vdus[vdu_name].update({'number_of_instance': num_of_instance})

        # Replaces healing requested VDU information
        for vnfc in vnfc_resource_info_list:
            vdu_id = vnfc.vdu_id
            param["nfv"]["VDU"][vdu_id] = vdus[vdu_id]

        return param

    @staticmethod
    def scale(base_hot_dict=None,
             vnfd_dict=None,
             scale_vnf_request=None,
             vnf_instances=None,
             inst_vnf_info=None,
             param=None, resource_number=None):

        # Update VDU scale size from VNFD and current vnf scale level
        current_aspect = {}
        for scale_aspect in inst_vnf_info.scale_status:
            aspect_id = scale_aspect.aspect_id
            scale_level = scale_aspect.scale_level
            current_aspect[aspect_id] = scale_level

        next_aspect = current_aspect
        scale_aspect = scale_vnf_request.aspect_id
        scale_enum = {'SCALE_OUT': 1, 'SCALE_IN': -1}
        scale_factor = scale_enum[scale_vnf_request.type]
        scale_step = scale_factor * scale_vnf_request.number_of_steps
        next_aspect[scale_aspect] += scale_step

        size_of_vdus = calculate_current_vdu_size(vnfd_dict, current_aspect)

        for vdu_name, num_of_instance in size_of_vdus.items():
            param['nfv']['VDU'][vdu_name].update(
                {'number_of_instance': num_of_instance})

        return param
