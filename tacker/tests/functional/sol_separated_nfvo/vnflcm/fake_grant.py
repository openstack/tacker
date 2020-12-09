#
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
import os
from oslo_serialization import jsonutils
from tacker.tests import uuidsentinel


class Grant:
    GRANT_REQ_PATH = '/grant/v1/grants'

    ZONES = [
        {
            "id": uuidsentinel.zone_id,
            "zoneId": "nova",
            "vimConnectionId": uuidsentinel.vim_connection_id
        }
    ]

    ADDITIONAL_PARAMS = {
        "key": "value"
    }

    @staticmethod
    def _make_vim_connection_info(tenant_id):
        access_info = {
            "username": "nfv_user",
            "region": "RegionOne",
            "password": "devstack",
            "tenant": tenant_id
        }

        return [{
            "id": uuidsentinel.vim_connection_id,
            "vimType": "ETSINFV.OPENSTACK_KEYSTONE.v_2",
            "interfaceInfo": {
                "endpoint": "http://127.0.0.1/identity"
            },
            "accessInfo": access_info
        }]

    @staticmethod
    def _make_add_resources(req_add_resources):
        add_resources = []
        for req_add_resource in req_add_resources:
            res_add_resource = {
                "resourceDefinitionId": req_add_resource['id'],
                "vimConnectionId": uuidsentinel.vim_connection_id
            }

            if req_add_resource['type'] == 'COMPUTE':
                res_add_resource["zoneId"] = uuidsentinel.zone_id

            add_resources.append(res_add_resource)

        return add_resources

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
    def _make_vim_assets(image_id, flavour_id="1"):
        # set m1.tiny="1" for flavour_id
        vim_assets = {
            "computeResourceFlavours": [
                {
                    "vimConnectionId": uuidsentinel.vim_connection_id,
                    "vnfdVirtualComputeDescId": "VDU1",
                    "vimFlavourId": flavour_id
                },
                {
                    "vimConnectionId": uuidsentinel.vim_connection_id,
                    "vnfdVirtualComputeDescId": "VDU2",
                    "vimFlavourId": flavour_id
                }
            ],
            "softwareImages": [
                {
                    "vimConnectionId": uuidsentinel.vim_connection_id,
                    "vnfdSoftwareImageId": "VDU1",
                    "vimSoftwareImageId": image_id
                },
                {
                    "vimConnectionId": uuidsentinel.vim_connection_id,
                    "vnfdSoftwareImageId": "VDU2",
                    "vimSoftwareImageId": image_id
                }
            ]
        }

        return vim_assets

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
                    Grant.GRANT_REQ_PATH)},
            "vnfLcmOpOcc": {
                "href": os.path.join(
                    'http://localhost:9890/vnflcm/v1/vnf_lcm_op_occs',
                    request_body['vnfLcmOpOccId'])},
            "vnfInstance": {
                "href": os.path.join(
                    'http://localhost:9890/vnflcm/v1/vnf_instances',
                    request_body['vnfInstanceId'])}}

        return res

    @staticmethod
    def _convert_body_to_dict(body):
        if isinstance(body, str):
            return jsonutils.loads(body)

        return body

    @staticmethod
    def make_inst_response_body(request_body, tenant_id, image_id):
        request_body = Grant._convert_body_to_dict(request_body)
        res = Grant._make_response_template(request_body)
        res["vimConnections"] = Grant._make_vim_connection_info(tenant_id)
        res["zones"] = Grant.ZONES
        if 'addResources' in request_body.keys():
            res["addResources"] = Grant._make_add_resources(
                request_body['addResources'])
        res["vimAssets"] = Grant._make_vim_assets(
            image_id)
        res["additionalParams"] = Grant.ADDITIONAL_PARAMS

        return res

    @staticmethod
    def make_heal_response_body(request_body, tenant_id, image_id):
        request_body = Grant._convert_body_to_dict(request_body)
        res = Grant._make_response_template(request_body)
        res["vimConnections"] = Grant._make_vim_connection_info(tenant_id)
        res["zones"] = Grant.ZONES
        if 'addResources' in request_body.keys():
            res["addResources"] = Grant._make_add_resources(
                request_body['addResources'])
        if 'removeResources' in request_body.keys():
            res["removeResources"] = Grant._make_remove_resources(
                request_body['removeResources'])
        res["vimAssets"] = Grant._make_vim_assets(image_id)

        return res

    @staticmethod
    def make_scaleout_response_body(request_body, tenant_id, image_id):
        request_body = Grant._convert_body_to_dict(request_body)
        res = Grant._make_response_template(request_body)
        res["vimConnections"] = Grant._make_vim_connection_info(tenant_id)
        res["zones"] = Grant.ZONES
        if 'addResources' in request_body.keys():
            res["addResources"] = Grant._make_add_resources(
                request_body['addResources'])
        res["vimAssets"] = Grant._make_vim_assets(
            image_id)

        return res

    @staticmethod
    def make_scalein_response_body(request_body):
        request_body = Grant._convert_body_to_dict(request_body)
        res = Grant._make_response_template(request_body)
        if 'removeResources' in request_body.keys():
            res["removeResources"] = Grant._make_remove_resources(
                request_body['removeResources'])

        return res

    @staticmethod
    def make_term_response_body(request_body):
        request_body = Grant._convert_body_to_dict(request_body)
        res = Grant._make_response_template(request_body)
        if 'removeResources' in request_body.keys():
            res["removeResources"] = Grant._make_remove_resources(
                request_body['removeResources'])

        return res
