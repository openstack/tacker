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


import io
import os
import re
import shutil
import tempfile
import zipfile

from oslo_log import log as logging
import yaml

from tacker.sol_refactored.common import exceptions as sol_ex


LOG = logging.getLogger(__name__)


class Vnfd(object):

    def __init__(self, vnfd_id):
        self.vnfd_id = vnfd_id
        self.tosca_meta = {}
        self.definitions = {}
        self.vnfd_flavours = {}
        self.csar_dir = None
        self.csar_dir_is_tmp = False

    def init_from_csar_dir(self, csar_dir):
        self.csar_dir = csar_dir
        self.init_vnfd()

    def init_from_zip_file(self, zip_file):
        # NOTE: This is used when external NFVO is used.
        # TODO(oda-g): There is no delete route at the moment.
        # A possible enhance is that introducing cache management for
        # extracted vnf packages from external NFVO.
        self.csar_dir = tempfile.mkdtemp()
        self.csar_dir_is_tmp = True

        buff = io.BytesIO(zip_file)
        with zipfile.ZipFile(buff, 'r') as zf:
            zf.extractall(self.csar_dir)

        self.init_vnfd()

    def init_vnfd(self):
        # assume TOSCA-Metadata format
        path = os.path.join(self.csar_dir, 'TOSCA-Metadata', 'TOSCA.meta')
        if not os.path.isfile(path):
            raise sol_ex.InvalidVnfdFormat()

        # expand from yaml to dict for TOSCA.meta and Definitions
        with open(path, 'r') as f:
            self.tosca_meta = yaml.safe_load(f.read())

        path = os.path.join(self.csar_dir, 'Definitions')
        for entry in os.listdir(path):
            if entry.endswith(('.yaml', '.yml')):
                with open(os.path.join(path, entry), 'r') as f:
                    content = yaml.safe_load(f.read())
                self.definitions[entry] = content

    def delete(self):
        if self.csar_dir_is_tmp:
            shutil.rmtree(self.csar_dir)

    def get_vnfd_flavour(self, flavour_id):
        if flavour_id in self.vnfd_flavours:
            return self.vnfd_flavours[flavour_id]

        for data in self.definitions.values():
            fid = (data
                   .get('topology_template', {})
                   .get('substitution_mappings', {})
                   .get('properties', {})
                   .get('flavour_id'))
            if fid == flavour_id:
                self.vnfd_flavours[flavour_id] = data
                return data

        # NOT found.
        # NOTE: checked by the caller. basically check is necessary at
        # instantiate start only.

    def get_sw_image(self, flavour_id):
        vnfd = self.get_vnfd_flavour(flavour_id)
        nodes = (vnfd
                 .get('topology_template', {})
                 .get('node_templates', {}))
        types = ['tosca.nodes.nfv.Vdu.Compute',
                 'tosca.nodes.nfv.Vdu.VirtualBlockStorage']
        sw_image = {}
        for name, data in nodes.items():
            if (data['type'] in types and
                    data.get('properties', {}).get('sw_image_data')):
                image = data['properties']['sw_image_data']['name']
                sw_image[name] = image

        return sw_image

    def get_sw_image_data(self, flavour_id):
        vnfd = self.get_vnfd_flavour(flavour_id)
        nodes = (vnfd
                 .get('topology_template', {})
                 .get('node_templates', {}))
        types = ['tosca.nodes.nfv.Vdu.Compute',
                 'tosca.nodes.nfv.Vdu.VirtualBlockStorage']
        sw_image = {}
        for name, data in nodes.items():
            if (data['type'] in types and
                    data.get('properties', {}).get('sw_image_data')):
                sw_image[name] = data['properties']['sw_image_data']
                sw_file = (data
                           .get('artifacts', {})
                           .get('sw_image', {})
                           .get('file'))
                if sw_file:
                    sw_image[name]['file'] = sw_file

        return sw_image

    def get_vnfd_properties(self):
        """return properties used by instantiate"""
        # get from node_templates of VNF of
        # - ['properties']['configurable_properties']
        # - ['properties']['modifiable_attributes']['extensions']
        # - ['properties']['modifiable_attributes']['metadata']
        # NOTE: In etsi_nfv_sol001_vnfd_types.yaml which used by
        # tacker examples, definitions of these properties are commented out.

        prop = {
            'vnfConfigurableProperties': {},
            'extensions': {},
            'metadata': {}
        }
        return prop

    def get_nodes(self, flavour_id, node_type):
        vnfd = self.get_vnfd_flavour(flavour_id)
        nodes = (vnfd
                 .get('topology_template', {})
                 .get('node_templates', {}))

        res = {name: data
            for name, data in nodes.items() if data['type'] == node_type}

        return res

    def get_vdu_nodes(self, flavour_id):
        return self.get_nodes(flavour_id, 'tosca.nodes.nfv.Vdu.Compute')

    def get_storage_nodes(self, flavour_id):
        return self.get_nodes(flavour_id,
                              'tosca.nodes.nfv.Vdu.VirtualBlockStorage')

    def get_virtual_link_nodes(self, flavour_id):
        return self.get_nodes(flavour_id,
                              'tosca.nodes.nfv.VnfVirtualLink')

    def get_vducp_nodes(self, flavour_id):
        return self.get_nodes(flavour_id, 'tosca.nodes.nfv.VduCp')

    def get_vdu_cps(self, flavour_id, vdu_name):
        cp_nodes = self.get_vducp_nodes(flavour_id)
        cps = []
        for cp_name, cp_data in cp_nodes.items():
            reqs = cp_data.get('requirements', [])
            for req in reqs:
                if req.get('virtual_binding') == vdu_name:
                    cps.append(cp_name)
                    break
        return cps

    def get_vdu_storages(self, vdu_node):
        storages = [req['virtual_storage']
                    for req in vdu_node.get('requirements', [])
                    if 'virtual_storage' in req]

        return storages

    def get_base_hot(self, flavour_id):
        # NOTE: this method is openstack specific
        hot_dict = {}
        path = os.path.join(self.csar_dir, 'BaseHOT', flavour_id)
        if not os.path.isdir(path):
            return hot_dict

        for entry in os.listdir(path):
            if entry.endswith(('.yaml', '.yml')):
                with open(os.path.join(path, entry), 'r') as f:
                    content = yaml.safe_load(f.read())
                    hot_dict['template'] = content
                    break

        nested = os.path.join(path, 'nested')
        if not os.path.isdir(nested):
            return hot_dict

        for entry in os.listdir(nested):
            if entry.endswith(('.yaml', '.yml')):
                with open(os.path.join(nested, entry), 'r') as f:
                    content = yaml.safe_load(f.read())
                    hot_dict.setdefault('files', {})
                    hot_dict['files'][entry] = content

        return hot_dict

    def get_vl_name_from_cp(self, flavour_id, cp_data):
        for req in cp_data.get('requirements', []):
            if 'virtual_link' in req:
                return req['virtual_link']

    def get_compute_flavor(self, flavour_id, vdu_name):
        vnfd = self.get_vnfd_flavour(flavour_id)
        flavor = (vnfd.get('topology_template', {})
                      .get('node_templates', {})
                      .get(vdu_name, {})
                      .get('capabilities', {})
                      .get('virtual_compute', {})
                      .get('properties', {})
                      .get('requested_additional_capabilities', {})
                      .get('properties', {})
                      .get('requested_additional_capability_name'))
        if flavor:
            return flavor

    def make_tmp_csar_dir(self):
        # If this fails, 500 which is not caused by programming error
        # but true 'Internal server error' raises.
        tmp_dir = tempfile.mkdtemp()
        # remove tmp_dir because copytree fails if destination exists.
        # NOTE:
        # so mkdtemp is used for getting a unique name at the moment.
        # if py38 or later, copytree supports dirs_exits_ok parameter.
        # It is not necessary to remove tmp_dir, specify
        # 'dirs_exists_ok=True' to copytree instead when tacker support
        # only py38 or later.
        os.rmdir(tmp_dir)
        shutil.copytree(self.csar_dir, tmp_dir,
            ignore=shutil.ignore_patterns('Files'))
        return tmp_dir

    def remove_tmp_csar_dir(self, tmp_dir):
        try:
            shutil.rmtree(tmp_dir)
        except Exception:
            LOG.exception("rmtree %s failed", tmp_dir)
            # as this error does not disturb the process, continue.

    def get_policy_values_by_type(self, flavour_id, policy_type):
        vnfd = self.get_vnfd_flavour(flavour_id)
        policies = (vnfd.get('topology_template', {})
                        .get('policies', []))
        if isinstance(policies, dict):
            policies = [policies]

        ret = [value
            for policy in policies for value in policy.values()
            if value['type'] == policy_type]

        return ret

    def get_default_instantiation_level(self, flavour_id):
        policies = self.get_policy_values_by_type(flavour_id,
                'tosca.policies.nfv.InstantiationLevels')
        if policies:
            return policies[0].get('properties', {}).get('default_level')

    def get_vdu_num(self, flavour_id, vdu_name, instantiation_level):
        policies = self.get_policy_values_by_type(flavour_id,
                'tosca.policies.nfv.VduInstantiationLevels')
        for policy in policies:
            if vdu_name in policy.get('targets', []):
                return (policy.get('properties', {})
                              .get('levels', {})
                              .get(instantiation_level, {})
                              .get('number_of_instances'))
        return 0

    def get_placement_groups(self, flavour_id):
        vnfd = self.get_vnfd_flavour(flavour_id)
        groups = (vnfd.get('topology_template', {})
                      .get('groups', []))
        if isinstance(groups, dict):
            groups = [groups]

        ret = {key: value['members']
            for group in groups for key, value in group.items()
            if value['type'] == 'tosca.groups.nfv.PlacementGroup'}

        return ret

    def _get_targets(self, flavour_id, affinity_type):
        policies = self.get_policy_values_by_type(flavour_id, affinity_type)
        groups = self.get_placement_groups(flavour_id)

        ret = []
        for policy in policies:
            scope = policy['properties']['scope']
            if scope not in ['zone', 'nfvi_node']:
                continue

            targets = []
            for target in policy['targets']:
                if target in list(groups.keys()):
                    targets += groups[target]
                else:
                    targets.append(target)

            ret.append((targets, scope))

        return ret

    def get_affinity_targets(self, flavour_id):
        return self._get_targets(flavour_id,
                'tosca.policies.nfv.AffinityRule')

    def get_anti_affinity_targets(self, flavour_id):
        return self._get_targets(flavour_id,
                'tosca.policies.nfv.AntiAffinityRule')

    def get_interface_script(self, flavour_id, operation):
        vnfd = self.get_vnfd_flavour(flavour_id)
        nodes = (vnfd.get('topology_template', {})
                     .get('node_templates', {}))
        for node in nodes.values():
            if 'interfaces' not in node:
                continue
            op_value = (node['interfaces'].get('Vnflcm', {})
                                          .get(operation))
            if not isinstance(op_value, dict):
                # op_value may be []
                return

            artifact = op_value.get('implementation')
            if artifact is None:
                # no script specified for the operation
                return

            script = (node.get('artifacts', {})
                          .get(artifact, {})
                          .get('file'))
            if script is None:
                # can not happen if vnf package is correct.
                return

            script_type = node['artifacts'][artifact].get('type')
            if script_type != 'tosca.artifacts.Implementation.Python':
                # support python script only at the moment
                msg = "Unsupported script type {}".format(script_type)
                raise sol_ex.SolHttpError422(sol_detail=msg)

            return script

    def get_scale_vdu_and_num(self, flavour_id, aspect_id):
        aspects = self.get_policy_values_by_type(flavour_id,
            'tosca.policies.nfv.ScalingAspects')
        delta = None
        for aspect in aspects:
            value = aspect['properties']['aspects'].get(aspect_id)
            if value is not None:
                # expect there is one delta.
                # NOTE: Tacker does not support non-uniform deltas defined in
                # ETSI NFV SOL001 8. Therefore, uniform delta corresponding
                # to number_of_instances can be set and number_of_instances is
                # the same regardless of scale_level.
                delta = value['step_deltas'][0]
                break

        if delta is None:
            return {}

        aspect_deltas = self.get_policy_values_by_type(flavour_id,
            'tosca.policies.nfv.VduScalingAspectDeltas')
        vdu_num_inst = {}
        for aspect_delta in aspect_deltas:
            if aspect_delta.get('properties', {}).get('aspect') == aspect_id:
                num_inst = (aspect_delta['properties']['deltas']
                            .get(delta, {}).get('number_of_instances'))
                # NOTE: it is not checked whether 'delta' defined in
                # ScaleingAspects exists in VduScalingAspectDeltas at
                # the loading of vnf package. this is a mistake of the
                # VNFD definition.
                if num_inst is None:
                    raise sol_ex.DeltaMissingInVnfd(delta=delta)
                for vdu_name in aspect_delta['targets']:
                    vdu_num_inst[vdu_name] = num_inst

        return vdu_num_inst

    def get_scale_info_from_inst_level(self, flavour_id, inst_level):
        policies = self.get_policy_values_by_type(flavour_id,
            'tosca.policies.nfv.InstantiationLevels')
        for policy in policies:
            return (policy['properties']['levels']
                    .get(inst_level, {})
                    .get('scale_info', {}))
        return {}

    def get_max_scale_level(self, flavour_id, aspect_id):
        aspects = self.get_policy_values_by_type(flavour_id,
            'tosca.policies.nfv.ScalingAspects')
        for aspect in aspects:
            value = aspect['properties']['aspects'].get(aspect_id)
            if value is not None:
                return value['max_scale_level']

        # should not occur
        return 0

    def get_vnf_artifact_files(self):

        def _get_file_contents(path):
            with open(path, 'rb') as file_object:
                content = re.split(b'\n\n+', file_object.read())
            return content

        mani_artifact_files = []
        meta_artifacts_files = []

        if self.tosca_meta.get('ETSI-Entry-Manifest'):
            manifest_path = os.path.join(
                self.csar_dir, self.tosca_meta.get('ETSI-Entry-Manifest'))

            mani_artifact_files = [
                yaml.safe_load(content).get('Source')
                for content in _get_file_contents(manifest_path) if
                yaml.safe_load(content) and
                yaml.safe_load(content).get('Source')]
        else:
            tosca_path = os.path.join(
                self.csar_dir, 'TOSCA-Metadata', 'TOSCA.meta')

            meta_artifacts_files = [
                yaml.safe_load(content).get('Name')
                for content in _get_file_contents(tosca_path) if
                yaml.safe_load(content) and yaml.safe_load(
                    content).get('Name')]

        mani_artifact_files.extend(meta_artifacts_files)
        return mani_artifact_files
