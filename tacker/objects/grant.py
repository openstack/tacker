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

from tacker import objects
from tacker.objects import base
from tacker.objects import fields


@base.TackerObjectRegistry.register
class Grant(base.TackerObject):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.StringField(nullable=False),
        'vnf_instance_id': fields.StringField(nullable=False),
        'vnf_lcm_op_occ_id': fields.StringField(nullable=False),
        'vim_connections': fields.ListOfObjectsField(
            'VimConnectionInfo', nullable=True, default=[]),
        'zones': fields.ListOfObjectsField(
            'ZoneInfo', nullable=True, default=[]),
        'add_resources': fields.ListOfObjectsField(
            'GrantInfo', nullable=True, default=[]),
        'remove_resources': fields.ListOfObjectsField(
            'GrantInfo', nullable=True, default=[]),
        'vim_assets': fields.ObjectField(
            'VimAssets', nullable=True)
    }

    @classmethod
    def obj_from_primitive(cls, primitive, context):
        if 'tacker_object.name' in primitive:
            obj_grant = super(
                Grant, cls).obj_from_primitive(primitive, context)
        else:
            if 'vim_connections' in primitive.keys():
                obj_data = [objects.VimConnectionInfo._from_dict(
                    vim_conn) for vim_conn in primitive.get(
                    'vim_connections', [])]
                primitive.update({'vim_connections': obj_data})

            if 'zones' in primitive.keys():
                obj_data = [ZoneInfo._from_dict(
                    zone) for zone in primitive.get(
                    'zones', [])]
                primitive.update({'zones': obj_data})

            if 'add_resources' in primitive.keys():
                obj_data = [GrantInfo._from_dict(
                    add_rsc) for add_rsc in primitive.get(
                    'add_resources', [])]
                primitive.update({'add_resources': obj_data})
            if 'remove_resources' in primitive.keys():
                obj_data = [GrantInfo._from_dict(
                    remove_rsc) for remove_rsc in primitive.get(
                    'remove_resources', [])]
                primitive.update({'remove_resources': obj_data})
            if 'vim_assets' in primitive.keys():
                obj_data = VimAssets.obj_from_primitive(
                    primitive.get('vim_assets'), context)
                primitive.update({'vim_assets': obj_data})

            obj_grant = Grant._from_dict(primitive)

        return obj_grant

    @classmethod
    def _from_dict(cls, data_dict):
        id = data_dict.get('id')
        vnf_instance_id = data_dict.get('vnf_instance_id')
        vnf_lcm_op_occ_id = data_dict.get('vnf_lcm_op_occ_id')
        vim_connections = data_dict.get('vim_connections', [])
        zones = data_dict.get('zones', [])
        add_resources = data_dict.get('add_resources', [])
        remove_resources = data_dict.get('remove_resources', [])
        vim_assets = data_dict.get('vim_assets')

        obj = cls(
            id=id,
            vnf_instance_id=vnf_instance_id,
            vnf_lcm_op_occ_id=vnf_lcm_op_occ_id,
            vim_connections=vim_connections,
            zones=zones,
            add_resources=add_resources,
            remove_resources=remove_resources,
            vim_assets=vim_assets)
        return obj


@base.TackerObjectRegistry.register
class ZoneInfo(base.TackerObject):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.StringField(nullable=False),
        'zone_id': fields.StringField(nullable=False),
        'vim_connection_id': fields.StringField(nullable=True)
    }

    @classmethod
    def obj_from_primitive(cls, primitive, context):
        if 'tacker_object.name' in primitive:
            obj_zone_info = super(
                ZoneInfo, cls).obj_from_primitive(primitive, context)
        else:
            obj_zone_info = ZoneInfo._from_dict(primitive)

        return obj_zone_info

    @classmethod
    def _from_dict(cls, data_dict):
        id = data_dict.get('id')
        zone_id = data_dict.get('zone_id')
        vim_connection_id = data_dict.get('vim_connection_id')

        obj = cls(
            id=id,
            zone_id=zone_id,
            vim_connection_id=vim_connection_id)
        return obj


@base.TackerObjectRegistry.register
class GrantInfo(base.TackerObject):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'resource_definition_id': fields.StringField(nullable=False),
        'vim_connection_id': fields.StringField(nullable=True),
        'zone_id': fields.StringField(nullable=True)
    }

    @classmethod
    def obj_from_primitive(cls, primitive, context):
        if 'tacker_object.name' in primitive:
            obj_grant_info = super(
                GrantInfo, cls).obj_from_primitive(primitive, context)
        else:
            obj_grant_info = GrantInfo._from_dict(primitive)

        return obj_grant_info

    @classmethod
    def _from_dict(cls, data_dict):
        resource_definition_id = data_dict.get('resource_definition_id')
        vim_connection_id = data_dict.get('vim_connection_id')
        zone_id = data_dict.get('zone_id')

        obj = cls(
            resource_definition_id=resource_definition_id,
            vim_connection_id=vim_connection_id,
            zone_id=zone_id)
        return obj


@base.TackerObjectRegistry.register
class VimAssets(base.TackerObject):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'compute_resource_flavours': fields.ListOfObjectsField(
            'VimComputeResourceFlavour', nullable=True, default=[]),
        'software_images': fields.ListOfObjectsField(
            'VimSoftwareImage', nullable=True, default=[])
    }

    @classmethod
    def obj_from_primitive(cls, primitive, context):
        if 'tacker_object.name' in primitive:
            obj_vim_assets = super(
                VimAssets, cls).obj_from_primitive(primitive, context)
        else:
            if 'compute_resource_flavours' in primitive.keys():
                obj_data = [VimComputeResourceFlavour._from_dict(
                    flavour) for flavour in primitive.get(
                    'compute_resource_flavours', [])]
                primitive.update({'compute_resource_flavours': obj_data})

            if 'software_images' in primitive.keys():
                obj_data = [VimSoftwareImage._from_dict(
                    img) for img in primitive.get(
                    'software_images', [])]
                primitive.update({'software_images': obj_data})
            obj_vim_assets = VimAssets._from_dict(primitive)

        return obj_vim_assets

    @classmethod
    def _from_dict(cls, data_dict):
        compute_resource_flavours = data_dict.get(
            'compute_resource_flavours', [])
        software_images = data_dict.get('software_images', [])

        obj = cls(
            compute_resource_flavours=compute_resource_flavours,
            software_images=software_images)
        return obj


@base.TackerObjectRegistry.register
class VimComputeResourceFlavour(base.TackerObject):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'vim_connection_id': fields.StringField(nullable=True),
        'vnfd_virtual_compute_desc_id': fields.StringField(nullable=False),
        'vim_flavour_id': fields.StringField(nullable=False)
    }

    @classmethod
    def obj_from_primitive(cls, primitive, context):
        if 'tacker_object.name' in primitive:
            obj_flavour = super(
                VimComputeResourceFlavour,
                cls).obj_from_primitive(
                primitive,
                context)
        else:
            obj_flavour = VimComputeResourceFlavour._from_dict(primitive)

        return obj_flavour

    @classmethod
    def _from_dict(cls, data_dict):
        vim_connection_id = data_dict.get('vim_connection_id')
        vnfd_virtual_compute_desc_id = data_dict.get(
            'vnfd_virtual_compute_desc_id')
        vim_flavour_id = data_dict.get('vim_flavour_id')

        obj = cls(
            vim_connection_id=vim_connection_id,
            vnfd_virtual_compute_desc_id=vnfd_virtual_compute_desc_id,
            vim_flavour_id=vim_flavour_id)
        return obj


@base.TackerObjectRegistry.register
class VimSoftwareImage(base.TackerObject):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'vim_connection_id': fields.StringField(nullable=True),
        'vnfd_software_image_id': fields.StringField(nullable=False),
        'vim_software_image_id': fields.StringField(nullable=False)
    }

    @classmethod
    def obj_from_primitive(cls, primitive, context):
        if 'tacker_object.name' in primitive:
            obj_img = super(
                VimSoftwareImage, cls).obj_from_primitive(primitive, context)
        else:
            obj_img = VimSoftwareImage._from_dict(primitive)

        return obj_img

    @classmethod
    def _from_dict(cls, data_dict):
        vim_connection_id = data_dict.get('vim_connection_id')
        vnfd_software_image_id = data_dict.get('vnfd_software_image_id')
        vim_software_image_id = data_dict.get('vim_software_image_id')

        obj = cls(
            vim_connection_id=vim_connection_id,
            vnfd_software_image_id=vnfd_software_image_id,
            vim_software_image_id=vim_software_image_id)
        return obj
