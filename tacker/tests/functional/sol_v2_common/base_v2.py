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

from tacker.common import utils as common_utils
from tacker.sol_refactored.common import http_client
from tacker.sol_refactored.infra_drivers.openstack import heat_utils
from tacker.sol_refactored.nfvo import glance_utils
from tacker.sol_refactored import objects
from tacker.tests.functional import base_v2

VNFLCM_V2_VERSION = "2.0.0"


class BaseSolV2Test(base_v2.BaseTackerTestV2):
    """Base test case class for SOL v2 functional tests."""

    @classmethod
    def setUpClass(cls):
        super(BaseSolV2Test, cls).setUpClass()

        vim_info = cls.get_vim_info()
        cls.auth_url = vim_info.interfaceInfo['endpoint']
        cls.neutron_client = http_client.HttpClient(cls.auth_handle,
                                                    service_type='network')
        cls.glance_client = http_client.HttpClient(cls.auth_handle,
                                                   service_type='image')
        cls.nova_client = http_client.HttpClient(cls.auth_handle,
                                                 service_type='compute')
        cls.heat_client = heat_utils.HeatClient(vim_info)
        cls.cinder_client = http_client.HttpClient(
            cls.auth_handle, service_type='block-storage')

    @classmethod
    def tearDownClass(cls):
        super(BaseSolV2Test, cls).tearDownClass()

    @classmethod
    def create_vnf_package(cls, sample_path, user_data={},
                           image_path=None, nfvo=False, userdata_path=None,
                           provider=None, vnfd_id=None):

        return super().create_vnf_package(sample_path, user_data=user_data,
                                          image_path=image_path, nfvo=nfvo,
                                          userdata_path=userdata_path,
                                          provider=provider, vnfd_id=vnfd_id)

    def get_network_ids(self, networks):
        path = "/v2.0/networks"
        resp, body = self.neutron_client.do_request(path, "GET")
        net_ids = {}
        for net in body['networks']:
            if net['name'] in networks:
                net_ids[net['name']] = net['id']
        return net_ids

    def get_subnet_ids(self, subnets):
        path = "/v2.0/subnets"
        resp, body = self.neutron_client.do_request(path, "GET")
        subnet_ids = {}
        for subnet in body['subnets']:
            if subnet['name'] in subnets:
                subnet_ids[subnet['name']] = subnet['id']
        return subnet_ids

    def create_network(self, name):
        path = "/v2.0/networks"
        req_body = {
            "network": {
                # "admin_state_up": true,
                "name": name
            }
        }
        try:
            resp, resp_body = self.neutron_client.do_request(
                path, "POST", body=req_body)
            return resp_body['network']['id']
        except Exception as e:
            self.fail("Failed, create network for name=<%s>, %s" %
                (name, e))

    def delete_network(self, net_id):
        path = "/v2.0/networks/{}".format(net_id)
        try:
            self.neutron_client.do_request(path, "DELETE")
        except Exception as e:
            self.fail("Failed, delete network for id=<%s>, %s" %
                (net_id, e))

    def create_subnet(self, net_id, sub_name, sub_range, ip_version):
        path = "/v2.0/subnets"
        req_body = {
            "subnet": {
                "name": sub_name,
                "network_id": net_id,
                "cidr": sub_range,
                "ip_version": ip_version
            }
        }
        try:
            resp, resp_body = self.neutron_client.do_request(
                path, "POST", body=req_body)
            return resp_body['subnet']['id']
        except Exception as e:
            self.fail("Failed, create subnet for name=<%s>, %s" %
                (sub_name, e))

    def delete_subnet(self, sub_id):
        path = "/v2.0/subnets/{}".format(sub_id)
        try:
            self.neutron_client.do_request(path, "DELETE")
        except Exception as e:
            self.fail("Failed, delete subnet for id=<%s>, %s" %
                (sub_id, e))

    def create_port(self, network_id, name):
        path = "/v2.0/ports"
        req_body = {
            'port': {
                'network_id': network_id,
                'name': name
            }
        }
        try:
            resp, resp_body = self.neutron_client.do_request(
                path, "POST", body=req_body)
            return resp_body['port']['id']
        except Exception as e:
            self.fail("Failed, create port for net_id=<%s>, %s" %
                (network_id, e))

    def delete_port(self, port_id):
        path = "/v2.0/ports/{}".format(port_id)
        try:
            self.neutron_client.do_request(path, "DELETE")
        except Exception as e:
            self.fail("Failed, delete port for id=<%s>, %s" %
                (port_id, e))

    def get_image_id(self, image_name):
        path = "/v2.0/images"
        resp, resp_body = self.glance_client.do_request(path, "GET")

        image_id = None
        for image in resp_body.get('images'):
            if image_name == image['name']:
                image_id = image['id']
        return image_id

    def get_server_details(self, server_name):
        path = "/servers/detail"
        resp, resp_body = self.nova_client.do_request(path, "GET")
        if server_name is None:
            return resp_body.get('servers')

        server_details = None
        for server in resp_body.get('servers'):
            if server_name == server['name']:
                server_details = server
        return server_details

    def get_server_details_by_id(self, server_id):
        path = f"/servers/{server_id}"
        resp, resp_body = self.nova_client.do_request(path, "GET")

        return resp_body.get('server', {})

    def get_zone_list(self):
        path = "/os-services"
        resp, resp_body = self.nova_client.do_request(path, "GET")

        zone_name_list = [zone.get("zone") for zone in
                          resp_body.get('services')
                          if zone.get("binary") == 'nova-compute']
        return zone_name_list

    def glance_create_image(
            self, vim_info, filename, sw_data, inst_id, num_vdu=1):
        min_disk = 0
        if 'min_disk' in sw_data:
            min_disk = common_utils.MemoryUnit.convert_unit_size_to_num(
                sw_data['min_disk'], 'GB')

        min_ram = 0
        if 'min_ram' in sw_data:
            min_ram = common_utils.MemoryUnit.convert_unit_size_to_num(
                sw_data['min_ram'], 'MB')

        # NOTE: use tag to find to delete images when terminate vnf instance.
        create_args = {
            'min_disk': min_disk,
            'min_ram': min_ram,
            'disk_format': sw_data.get('disk_format'),
            'container_format': sw_data.get('container_format'),
            'filename': filename,
            'visibility': 'private',
            'tags': [inst_id]
        }
        vim = objects.VimConnectionInfo(
            vimId=vim_info.get("vimId"),
            vimType=vim_info.get("vimType"),
            interfaceInfo=vim_info.get("interfaceInfo"),
            accessInfo=vim_info.get("accessInfo")
        )
        glance_client = glance_utils.GlanceClient(vim)
        if num_vdu == 1:
            vdu = 'VDU2' if 'VDU2' in sw_data else 'VDU2-VirtualStorage'
            image = glance_client.create_image(
                sw_data[vdu]['name'], **create_args)
            return image.id

        vdu = 'VDU1' if 'VDU1' in sw_data else 'VDU1-VirtualStorage'
        image_1 = glance_client.create_image(
            sw_data[vdu]['name'], **create_args)
        vdu = 'VDU2' if 'VDU2' in sw_data else 'VDU2-VirtualStorage'
        image_2 = glance_client.create_image(
            sw_data[vdu]['name'], **create_args)
        return image_1.id, image_2.id

    def glance_delete_image(self, vim_info, image_ids):
        vim = objects.VimConnectionInfo(
            vimId=vim_info.get("vimId"),
            vimType=vim_info.get("vimType"),
            interfaceInfo=vim_info.get("interfaceInfo"),
            accessInfo=vim_info.get("accessInfo")
        )
        glance_client = glance_utils.GlanceClient(vim)
        for image_id in image_ids:
            glance_client.delete_image(image_id)

    def change_ext_conn(self, inst_id, req_body):
        path = f"/vnflcm/v2/vnf_instances/{inst_id}/change_ext_conn"
        return self.tacker_client.do_request(
            path, "POST", body=req_body, version=VNFLCM_V2_VERSION)

    def get_current_vdu_image(
            self, stack_id, stack_name, resource_name):
        vdu_info = self.heat_client.get_resource_info(
            f"{stack_name}/{stack_id}", resource_name)
        if vdu_info.get('attributes').get('image'):
            image_id = vdu_info.get('attributes').get('image').get('id')
        else:
            volume_ids = [volume.get('id') for volume in vdu_info.get(
                'attributes').get('os-extended-volumes:volumes_attached')]
            for volume_id in volume_ids:
                path = f"/volumes/{volume_id}"
                resp, resp_body = self.cinder_client.do_request(path, "GET")
                if resp_body['volume']['volume_image_metadata']:
                    image_id = resp_body['volume'][
                        'volume_image_metadata'].get('image_id')

        return image_id

    def server_notification(self, inst_id, server_id, req_body):
        path = ("/server_notification/vnf_instances/"
                f"{inst_id}/servers/{server_id}/notify")
        return self.tacker_client.do_request(
            path, "POST", body=req_body)
