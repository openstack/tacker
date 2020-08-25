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

from oslo_serialization import jsonutils

from tacker.common import utils
from tacker.objects import base
from tacker.objects import fields


@base.TackerObjectRegistry.register
class GrantRequest(base.TackerObject):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'vnf_instance_id': fields.StringField(nullable=False),
        'vnf_lcm_op_occ_id': fields.StringField(nullable=False),
        'vnfd_id': fields.StringField(nullable=False),
        'flavour_id': fields.StringField(nullable=True),
        'operation': fields.StringField(nullable=False),
        'is_automatic_invocation': fields.BooleanField(nullable=False,
                                                       default=False),
        'add_resources': fields.ListOfObjectsField(
            'ResourceDefinition', nullable=True, default=[]),
        'remove_resources': fields.ListOfObjectsField(
            'ResourceDefinition', nullable=True, default=[]),
        'placement_constraints': fields.ListOfObjectsField(
            'PlacementConstraint', nullable=True, default=[]),
        '_links': fields.ObjectField(
            'Links', nullable=False)
    }

    @classmethod
    def obj_from_primitive(cls, primitive, context):
        if 'tacker_object.name' in primitive:
            obj_grant_req = super(
                GrantRequest, cls).obj_from_primitive(primitive, context)
        else:
            if 'add_resources' in primitive.keys():
                obj_data = [ResourceDefinition._from_dict(
                    add_rsc) for add_rsc in primitive.get(
                    'add_resources', [])]
                primitive.update({'add_resources': obj_data})
            if 'remove_resources' in primitive.keys():
                obj_data = [ResourceDefinition._from_dict(
                    remove_rsc) for remove_rsc in primitive.get(
                    'remove_resources', [])]
                primitive.update({'add_resources': obj_data})
            if 'placement_constraints' in primitive.keys():
                obj_data = [PlacementConstraint._from_dict(
                    place) for place in primitive.get(
                    'placement_constraints', [])]
                primitive.update({'add_resources': obj_data})
            obj_grant_req = GrantRequest._from_dict(primitive)

        return obj_grant_req

    @classmethod
    def _from_dict(cls, data_dict):
        vnf_instance_id = data_dict.get('vnf_instance_id')
        vnf_lcm_op_occ_id = data_dict.get('vnf_lcm_op_occ_id')
        vnfd_id = data_dict.get('vnfd_id')
        flavour_id = data_dict.get('flavour_id')
        operation = data_dict.get('operation')
        is_automatic_invocation = data_dict.get('is_automatic_invocation')
        add_resources = data_dict.get('add_resources', [])
        remove_resources = data_dict.get('remove_resources', [])
        placement_constraints = data_dict.get('placement_constraints', [])
        links = data_dict.get('_links')

        obj = cls(
            vnf_instance_id=vnf_instance_id,
            vnf_lcm_op_occ_id=vnf_lcm_op_occ_id,
            vnfd_id=vnfd_id,
            flavour_id=flavour_id,
            operation=operation,
            is_automatic_invocation=is_automatic_invocation,
            add_resources=add_resources,
            remove_resources=remove_resources,
            placement_constraints=placement_constraints,
            _links=links)
        return obj

    def to_dict(self):
        data = {'vnf_instance_id': self.vnf_instance_id,
                'vnf_lcm_op_occ_id': self.vnf_lcm_op_occ_id,
                'vnfd_id': self.vnfd_id,
                'flavour_id': self.flavour_id,
                'operation': self.operation,
                'is_automatic_invocation': self.is_automatic_invocation,
                '_links': self._links.to_dict()}
        if self.add_resources:
            add_resources_list = []
            for add_resource in self.add_resources:
                add_resources_list.append(add_resource.to_dict())

            data.update({'add_resources': add_resources_list})
        if self.remove_resources:
            remove_resources_list = []
            for remove_resource in self.remove_resources:
                remove_resources_list.append(remove_resource.to_dict())

            data.update({'remove_resources': remove_resources_list})
        if self.placement_constraints:
            placement_constraints_list = []
            for placement_constraint in self.placement_constraints:
                placement_constraints_list.append(
                    placement_constraint.to_dict())

            data.update({'placement_constraints': placement_constraints_list})
        return data

    def to_request_body(self):
        req_dict = self.to_dict()
        req_dict = utils.convert_snakecase_to_camelcase(req_dict)
        return jsonutils.dumps(req_dict).replace('Links', '_links')


@base.TackerObjectRegistry.register
class ResourceDefinition(base.TackerObject):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.StringField(nullable=False),
        'type': fields.StringField(nullable=False),
        'vdu_id': fields.StringField(nullable=True, default=None),
        'resource_template_id': fields.StringField(nullable=False),
        'resource': fields.ObjectField(
            'ResourceHandle', nullable=True, default=None)
    }

    @classmethod
    def obj_from_primitive(cls, primitive, context):
        if 'tacker_object.name' in primitive:
            obj_grant_req = super(
                ResourceDefinition, cls).\
                obj_from_primitive(primitive, context)
        else:
            if 'resource' in primitive.keys():
                obj_data = ResourceHandle._from_dict(
                    primitive.get('resource'))
                primitive.update({'resource': obj_data})
            obj_grant_req = ResourceDefinition._from_dict(primitive)

        return obj_grant_req

    @classmethod
    def _from_dict(cls, data_dict):
        id = data_dict.get('id')
        type = data_dict.get('type')
        vdu_id = data_dict.get('vdu_id')
        resource_template_id = data_dict.get('resource_template_id')
        resource = data_dict.get('resource')

        obj = cls(
            id=id,
            type=type,
            vdu_id=vdu_id,
            resource_template_id=resource_template_id,
            resource=resource)
        return obj

    def to_dict(self):
        data = {'id': self.id,
                'type': self.type,
                'resource_template_id': self.resource_template_id}
        if self.vdu_id:
            data.update({'vdu_id': self.vdu_id})
        if self.resource:
            data.update({'resource': self.resource.to_dict()})
        return data


@base.TackerObjectRegistry.register
class PlacementConstraint(base.TackerObject):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'affinity_or_anti_affinity': fields.StringField(nullable=False),
        'scope': fields.StringField(nullable=False),
        'resource': fields.ListOfObjectsField(
            'ConstraintResourceRef', nullable=False, default=[]),
        'fallback_best_effort': fields.BooleanField(nullable=False),
    }

    @classmethod
    def obj_from_primitive(cls, primitive, context):
        if 'tacker_object.name' in primitive:
            obj_placement_constraint = super(
                PlacementConstraint, cls).obj_from_primitive(
                primitive, context)
        else:
            if 'resource' in primitive.keys():
                obj_data = [ConstraintResourceRef._from_dict(
                    add_rsc) for add_rsc in primitive.get(
                    'resource', [])]
                primitive.update({'resource': obj_data})
            obj_placement_constraint = PlacementConstraint._from_dict(
                primitive)

        return obj_placement_constraint

    @classmethod
    def _from_dict(cls, data_dict):
        affinity_or_anti_affinity = data_dict.get('affinity_or_anti_affinity')
        scope = data_dict.get('scope')
        resource = data_dict.get('resource')
        fallback_best_effort = data_dict.get('fallback_best_effort')

        obj = cls(
            affinity_or_anti_affinity=affinity_or_anti_affinity,
            scope=scope,
            resource=resource,
            fallback_best_effort=fallback_best_effort)
        return obj

    def to_dict(self):
        data = {'affinity_or_anti_affinity': self.affinity_or_anti_affinity,
                'scope': self.scope,
                'fallback_best_effort': self.fallback_best_effort}
        if self.resource:
            resource_list = []
            for rsc in self.resource:
                resource_list.append(rsc.to_dict())

            data.update({'resource': resource_list})
        return data


@base.TackerObjectRegistry.register
class ConstraintResourceRef(base.TackerObject):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id_type': fields.StringField(nullable=False),
        'resource_id': fields.StringField(nullable=False),
        'vim_connection_id': fields.StringField(nullable=True, default=None),
    }

    @classmethod
    def obj_from_primitive(cls, primitive, context):
        if 'tacker_object.name' in primitive:
            obj_placement_constraint = super(
                ConstraintResourceRef, cls).obj_from_primitive(
                primitive, context)
        else:
            obj_placement_constraint = ConstraintResourceRef._from_dict(
                primitive)

        return obj_placement_constraint

    @classmethod
    def _from_dict(cls, data_dict):
        id_type = data_dict.get('id_type')
        resource_id = data_dict.get('resource_id')
        vim_connection_id = data_dict.get('vim_connection_id')

        obj = cls(
            id_type=id_type,
            resource_id=resource_id,
            vim_connection_id=vim_connection_id)
        return obj

    def to_dict(self):
        data = {'id_type': self.id_type,
                'resource_id': self.resource_id}
        if self.vim_connection_id:
            data.update({'vim_connection_id': self.vim_connection_id})
        return data


@base.TackerObjectRegistry.register
class Links(base.TackerObject):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'vnf_lcm_op_occ': fields.ObjectField(
            'Link', nullable=False),
        'vnf_instance': fields.ObjectField(
            'Link', nullable=False)
    }

    @classmethod
    def obj_from_primitive(cls, primitive, context):
        if 'tacker_object.name' in primitive:
            obj_links = super(
                Links, cls).obj_from_primitive(primitive, context)
        else:
            if 'vnf_lcm_op_occ' in primitive.keys():
                obj_data = Link._from_dict(
                    primitive.get('vnf_lcm_op_occ'))
                primitive.update({'vnf_lcm_op_occ': obj_data})
            if 'vnf_instance' in primitive.keys():
                obj_data = Link._from_dict(
                    primitive.get('vnf_instance'))
                primitive.update({'vnf_instance': obj_data})
            obj_links = Links._from_dict(primitive)

        return obj_links

    @classmethod
    def _from_dict(cls, data_dict):
        vnf_lcm_op_occ = data_dict.get('vnf_lcm_op_occ')
        vnf_instance = data_dict.get('vnf_instance')

        obj = cls(
            vnf_lcm_op_occ=vnf_lcm_op_occ,
            vnf_instance=vnf_instance)
        return obj

    def to_dict(self):
        return {'vnf_lcm_op_occ': self.vnf_lcm_op_occ.to_dict(),
                'vnf_instance': self.vnf_instance.to_dict()}


@base.TackerObjectRegistry.register
class Link(base.TackerObject):

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'href': fields.StringField(nullable=False)
    }

    @classmethod
    def obj_from_primitive(cls, primitive, context):
        if 'tacker_object.name' in primitive:
            obj_link = super(
                Link, cls).obj_from_primitive(primitive, context)
        else:
            obj_link = Link._from_dict(primitive)

        return obj_link

    @classmethod
    def _from_dict(cls, data_dict):
        href = data_dict.get('href')

        obj = cls(
            href=href)
        return obj

    def to_dict(self):
        return {'href': self.href}


@base.TackerObjectRegistry.register
class ResourceHandle(base.TackerObject,
                     base.TackerPersistentObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'vim_connection_id': fields.StringField(nullable=True,
                                                default=None),
        'resource_id': fields.StringField(nullable=False, default=""),
        'vim_level_resource_type': fields.StringField(nullable=True,
                                                      default=None)
    }

    @classmethod
    def obj_from_primitive(cls, primitive, context):
        if 'tacker_object.name' in primitive:
            resource_handle = super(
                ResourceHandle, cls).obj_from_primitive(
                primitive, context)
        else:
            resource_handle = ResourceHandle._from_dict(primitive)

        return resource_handle

    @classmethod
    def _from_dict(cls, data_dict):
        vim_connection_id = data_dict.get('vim_connection_id')
        resource_id = data_dict.get('resource_id', "")
        vim_level_resource_type = data_dict.get('vim_level_resource_type')

        obj = cls(vim_connection_id=vim_connection_id,
                  resource_id=resource_id,
                  vim_level_resource_type=vim_level_resource_type)

        return obj

    def to_dict(self):
        return {'vim_connection_id': self.vim_connection_id,
                'resource_id': self.resource_id,
                'vim_level_resource_type': self.vim_level_resource_type}
