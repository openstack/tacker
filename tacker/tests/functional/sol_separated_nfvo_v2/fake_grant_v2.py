# Copyright (C) 2022 Fujitsu
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
import yaml

from oslo_serialization import jsonutils
from oslo_utils import uuidutils

from tacker.tests import utils as base_utils
from tacker.tests import uuidsentinel


class GrantV2:
    GRANT_REQ_PATH = '/grant/v1/grants'
    TOKEN = '/token'

    ZONES = [
        {
            "id": uuidsentinel.zone_id,
            "zoneId": "nova",
            "vimConnectionId": "vim1"
        }
    ]

    ADDITIONAL_PARAMS = {
        "key": "value"
    }

    @staticmethod
    def _make_vim_connection_info():
        access_info = {
            "username": "nfv_user",
            "region": "RegionOne",
            "password": "devstack",
            "project": "nfv",
            "projectDomain": "Default",
            "userDomain": "Default"
        }
        vim_params = yaml.safe_load(base_utils.read_file('local-vim.yaml'))
        vim_params['auth_url'] = f"{vim_params['auth_url']}/v3"
        return {
            "vim1": {
                "vimId": uuidsentinel.vim_connection_id,
                "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_3",
                "interfaceInfo": {"endpoint": vim_params['auth_url']},
                "accessInfo": access_info,
                "extra": {"dummy-key": "dummy-val"}
            }
        }

    @staticmethod
    def make_grant_v2_links(request_body):
        link = {
            "self": {
                # set fake server port.
                "href": os.path.join(
                    'http://localhost:9990',
                    'grant/v1/grants')},
            "vnfLcmOpOcc": {
                "href": os.path.join(
                    'http://localhost:9890/vnflcm/v2/vnf_lcm_op_occs',
                    request_body['vnfLcmOpOccId'])},
            "vnfInstance": {
                "href": os.path.join(
                    'http://localhost:9890/vnflcm/v2/vnf_instances',
                    request_body['vnfInstanceId'])}}

        return link

    @staticmethod
    def _make_add_resources(req_add_resources, zones=None,
                            placement_constraints=None):
        add_resources = []
        for req_add_resource in req_add_resources:
            res_add_resource = {
                "resourceDefinitionId": req_add_resource['id'],
                "vimConnectionId": "vim1"
            }
            if req_add_resource['type'] == 'COMPUTE':
                if placement_constraints:
                    zone_id_dict = (GrantV2.
                                    _get_zone_id_from_placement_constraint(
                                        placement_constraints, zones))
                    if zone_id_dict[req_add_resource['id']]:
                        res_add_resource["zoneId"] = zone_id_dict[
                            req_add_resource['id']]
            add_resources.append(res_add_resource)

        return add_resources

    @staticmethod
    def _get_zone_id_from_placement_constraint(placement_constraints, zones):
        zone_id_dict = {}
        for placement_constraint in placement_constraints:
            for index in range(len(placement_constraint['resource'])):
                if placement_constraint[
                        'affinityOrAntiAffinity'] == 'AFFINITY':
                    # In this fake_grant, if the user set 'AFFINITY'
                    # rule in VNF Package, it will always use the first
                    # `Availability Zone` to create VM.
                    zone_id_dict[placement_constraint[
                        'resource'][index]['resourceId']] = zones[0]['id']
                else:
                    try:
                        zone_id_dict[placement_constraint[
                            'resource'][index]['resourceId']] = zones[
                            index]['id']
                    except IndexError:
                        print(
                            "The number of 'Availability Zone'"
                            "cannot support current case.")
                        raise IndexError

        return zone_id_dict

    @staticmethod
    def _make_zones(zone_name_list):
        zone = []
        for name in zone_name_list:
            zone_dict = {
                "id": uuidutils.generate_uuid(),
                "zoneId": name,
                "vimConnectionId": "vim1"
            }
            zone.append(zone_dict)
        return zone

    @staticmethod
    def _make_remove_resources(req_remove_resources):
        res_remove_resources = []
        for req_remove_resource in req_remove_resources:
            res_remove_resource = {
                "resourceDefinitionId": req_remove_resource['id']
            }

            res_remove_resources.append(res_remove_resource)

        return res_remove_resources

    @staticmethod
    def _make_update_resources(req_update_resources,
                               zones=None, placement_constraints=None):
        res_update_resources = []
        for req_update_resource in req_update_resources:
            res_update_resource = {
                "resourceDefinitionId": req_update_resource['id'],
                "vimConnectionId": "vim1"
            }
            if req_update_resource['type'] == 'COMPUTE':
                if placement_constraints:
                    zone_id_dict = (GrantV2.
                                    _get_zone_id_from_placement_constraint(
                                        placement_constraints, zones))
                    if zone_id_dict[req_update_resource['id']]:
                        res_update_resource["zoneId"] = zone_id_dict[
                            req_update_resource['id']]
            res_update_resources.append(res_update_resource)

        return res_update_resources

    @staticmethod
    def get_vdu_list(add_resources):
        vdu_list = []
        for add_resource in add_resources:
            if add_resource['type'] == 'COMPUTE' or (
                    add_resource['type'] == 'STORAGE'):
                if add_resource.get('vduId'):
                    vdu_list.append(add_resource['vduId'])
                else:
                    vdu_list.append(add_resource['resourceTemplateId'])
        return vdu_list

    @staticmethod
    def _make_vim_assets(add_resources, image_id_dict, flavour_id_dict):
        # set m1.tiny="1" for flavour_id
        vdu_list = GrantV2.get_vdu_list(add_resources)
        flavors = [GrantV2._generate_flavour(vdu, flavour_id_dict)
                   for vdu in vdu_list if flavour_id_dict.get(vdu)]
        images = [GrantV2._generate_image(vdu, image_id_dict)
                  for vdu in vdu_list if image_id_dict.get(vdu)]

        vim_assets = {
            'computeResourceFlavours': flavors,
            'softwareImages': images,
        }

        return vim_assets

    @staticmethod
    def _generate_flavour(vdu, flavour_id_dict):
        if flavour_id_dict.get(vdu):
            return {
                "vimConnectionId": "vim1",
                "vnfdVirtualComputeDescId": vdu,
                "vimFlavourId": flavour_id_dict[vdu]
            }
        return None

    @staticmethod
    def _generate_image(vdu, image_id_dict):
        if image_id_dict.get(vdu):
            return {
                "vimConnectionId": "vim1",
                "vnfdSoftwareImageId": vdu,
                "vimSoftwareImageId": image_id_dict[vdu]
            }
        return None

    @staticmethod
    def _make_response_template(request_body):
        res = {
            "id": uuidsentinel.__getattr__(request_body['vnfLcmOpOccId']),
            "vnfInstanceId": request_body['vnfInstanceId'],
            "vnfLcmOpOccId": request_body['vnfLcmOpOccId'],
        }
        res["_links"] = {
            "self": {
                # set fake server port.
                "href": os.path.join(
                    'http://localhost:9990',
                    GrantV2.GRANT_REQ_PATH)},
            "vnfLcmOpOcc": {
                "href": os.path.join(
                    'http://localhost:9890/vnflcm/v2/vnf_lcm_op_occs',
                    request_body['vnfLcmOpOccId'])},
            "vnfInstance": {
                "href": os.path.join(
                    'http://localhost:9890/vnflcm/v2/vnf_instances',
                    request_body['vnfInstanceId'])}}

        return res

    @staticmethod
    def convert_body_to_dict(body):
        if isinstance(body, str):
            return jsonutils.loads(body)

        return body

    @staticmethod
    def make_inst_response_body(
            request_body, image_id_dict,
            flavour_id_dict, zone_name_list,
            password=None):
        request_body = GrantV2.convert_body_to_dict(request_body)
        res = GrantV2._make_response_template(request_body)
        res["vimConnectionInfo"] = GrantV2._make_vim_connection_info()
        if password:
            # Normally, password, client_secret, and bearer_token are not
            # specified at the same time, but this time they are all included
            # for the DB registration test.
            accessInfo = res["vimConnectionInfo"]["vim1"]["accessInfo"]
            accessInfo["password"] = password
            accessInfo["client_secret"] = password
            accessInfo["bearer_token"] = password
        res["zones"] = GrantV2._make_zones(zone_name_list)
        if 'addResources' in request_body.keys():
            res["addResources"] = GrantV2._make_add_resources(
                request_body['addResources'], res["zones"],
                request_body.get('placementConstraints'))
            res["vimAssets"] = GrantV2._make_vim_assets(
                request_body['addResources'],
                image_id_dict,
                flavour_id_dict)
        res["additionalParams"] = GrantV2.ADDITIONAL_PARAMS

        return res

    @staticmethod
    def make_heal_response_body(request_body, image_id_dict,
                                flavour_id_dict, zone_name_list):
        request_body = GrantV2.convert_body_to_dict(request_body)
        res = GrantV2._make_response_template(request_body)
        res["vimConnectionInfo"] = GrantV2._make_vim_connection_info()
        res["zones"] = GrantV2._make_zones(zone_name_list)
        if 'addResources' in request_body.keys():
            res["addResources"] = GrantV2._make_add_resources(
                request_body['addResources'], res["zones"],
                request_body.get('placementConstraints'))
            res["vimAssets"] = GrantV2._make_vim_assets(
                request_body['addResources'],
                image_id_dict,
                flavour_id_dict)
        if 'removeResources' in request_body.keys():
            res["removeResources"] = GrantV2._make_remove_resources(
                request_body['removeResources'])
        if 'updateResources' in request_body.keys():
            res["updateResources"] = GrantV2._make_update_resources(
                request_body['updateResources'], res["zones"],
                request_body.get('placementConstraints'))
        return res

    @staticmethod
    def make_scale_response_body(
            request_body, image_id_dict, flavour_id_dict,
            zone_name_list):
        request_body = GrantV2.convert_body_to_dict(request_body)
        res = GrantV2._make_response_template(request_body)
        if 'addResources' in request_body.keys():
            res["zones"] = GrantV2._make_zones(zone_name_list)
            res["addResources"] = GrantV2._make_add_resources(
                request_body['addResources'], res["zones"],
                request_body.get('placementConstraints'))
            res["vimAssets"] = GrantV2._make_vim_assets(
                request_body['addResources'],
                image_id_dict,
                flavour_id_dict)
            res["vimConnectionInfo"] = GrantV2._make_vim_connection_info()
        if 'removeResources' in request_body.keys():
            res["removeResources"] = GrantV2._make_remove_resources(
                request_body['removeResources'])

        return res

    @staticmethod
    def make_term_response_body(request_body):
        request_body = GrantV2.convert_body_to_dict(request_body)
        res = GrantV2._make_response_template(request_body)
        if 'removeResources' in request_body.keys():
            res["removeResources"] = GrantV2._make_remove_resources(
                request_body['removeResources'])

        return res

    @staticmethod
    def make_change_ext_conn_response_body(
            request_body, zone_name_list):
        request_body = GrantV2.convert_body_to_dict(request_body)
        res = GrantV2._make_response_template(request_body)
        res["vimConnectionInfo"] = GrantV2._make_vim_connection_info()
        res["zones"] = GrantV2._make_zones(zone_name_list)
        if 'updateResources' in request_body.keys():
            res["updateResources"] = GrantV2._make_update_resources(
                request_body['updateResources'], res["zones"],
                request_body.get('placementConstraints'))
        res["additionalParams"] = GrantV2.ADDITIONAL_PARAMS

        return res

    @staticmethod
    def make_change_vnfpkg_response_body(
            request_body, image_id_dict, flavour_id_dict):
        request_body = GrantV2.convert_body_to_dict(request_body)
        res = GrantV2._make_response_template(request_body)
        if 'addResources' in request_body.keys():
            res["addResources"] = GrantV2._make_add_resources(
                request_body['addResources'])
            res["vimAssets"] = GrantV2._make_vim_assets(
                request_body['addResources'],
                image_id_dict,
                flavour_id_dict)
        if 'removeResources' in request_body.keys():
            res["removeResources"] = GrantV2._make_remove_resources(
                request_body['removeResources'])
        if 'updateResources' in request_body.keys():
            res["updateResources"] = GrantV2._make_update_resources(
                request_body['updateResources'])

        return res

    @staticmethod
    def get_sw_image(package_dir, vnfd_path):
        csar_package_path = package_dir
        yaml_file = os.path.join(csar_package_path,
                                 vnfd_path)
        with open(yaml_file, 'r', encoding='utf-8') as f:
            config_content = yaml.safe_load(f.read())

        nodes = (config_content
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

    @staticmethod
    def get_compute_flavor(package_dir, vnfd_path):
        csar_package_path = package_dir
        yaml_file = os.path.join(csar_package_path,
                                 vnfd_path)
        with open(yaml_file, 'r', encoding='utf-8') as f:
            config_content = yaml.safe_load(f.read())

        nodes = (config_content
                 .get('topology_template', {})
                 .get('node_templates', {}))
        types = ['tosca.nodes.nfv.Vdu.Compute',
                 'tosca.nodes.nfv.Vdu.VirtualBlockStorage']
        flavor = {}
        for name, data in nodes.items():
            if (data['type'] in types and
                    data.get('capabilities', {})
                        .get('virtual_compute', {})
                        .get('properties', {})
                        .get('requested_additional_capabilities', {})
                        .get('properties')):
                flavour = data['capabilities']['virtual_compute'][
                    'properties']['requested_additional_capabilities'][
                    'properties']['requested_additional_capability_name']
                flavor[name] = flavour

        return flavor

    @staticmethod
    def get_sw_data(package_dir, vnfd_path):
        csar_package_path = package_dir
        yaml_file = os.path.join(csar_package_path,
                                 vnfd_path)
        with open(yaml_file, 'r', encoding='utf-8') as f:
            config_content = yaml.safe_load(f.read())

        nodes = (config_content
                 .get('topology_template', {})
                 .get('node_templates', {}))
        types = ['tosca.nodes.nfv.Vdu.Compute',
                 'tosca.nodes.nfv.Vdu.VirtualBlockStorage']
        sw_data = {}
        for name, data in nodes.items():
            if (data['type'] in types and
                    data.get('properties', {}).get('sw_image_data')):
                image_data = data['properties']['sw_image_data']
                sw_data[name] = image_data

        return sw_data
