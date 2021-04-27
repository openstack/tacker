# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from oslo_log import log as logging

from tacker.common import log

LOG = logging.getLogger(__name__)


class HOTUpdater(object):
    """Update HOT template."""

    def __init__(self, heatclient):
        self.heatclient = heatclient
        self.template = {}
        self.nested_templates = dict()

    @log.log
    def get_templates_from_stack(self, stack_id):
        """Get template information from the stack.

        Get the template from stack specified by stack_id,
        if stack has scalable resource, get the its child
        template.
        """

        def _get_resource(name, resources):
            for resource in resources:
                if resource.resource_name == name:
                    return resource

        self.template = self.heatclient.stacks.template(stack_id)
        LOG.debug('got main template for stack({}). template={}'.format(
            stack_id, self.template))

        stack_resources = self.heatclient.resource_get_list(stack_id,
            nested_depth=2)
        for resource in stack_resources:
            if resource.resource_type == 'OS::Heat::AutoScalingGroup':
                intermediate_template = self.heatclient.stacks.template(
                    resource.physical_resource_id)

                for resource_id in intermediate_template['resources'].keys():
                    corresponding_resource = _get_resource(resource_id,
                        stack_resources)
                    nested_template = self.heatclient.stacks.template(
                        corresponding_resource.physical_resource_id)
                    LOG.debug('got nested template for stack({}). template={}'
                        .format(corresponding_resource.physical_resource_id,
                        nested_template))
                if nested_template:
                    self.nested_templates[
                        corresponding_resource.resource_type] = nested_template

    @log.log
    def update_resource_property(self,
                                resource_id,
                                resource_types=[],
                                **kwargs):
        """Update attributes of resource properties.

        Get the resource information from template's resources section,
        and update properties using kwargs information.
        If resource type does not include in resource_types, nothing to do.
        """

        def _update(template, resource_id, resource_types, kwargs):
            resource = template.get('resources', {}).get(resource_id)
            if not resource:
                return
            if resource.get('type', {}) not in resource_types:
                return

            resource_properties = resource.get('properties', {})
            if not resource_properties:
                return

            for key, value in kwargs.items():
                if value is not None:
                    resource_properties.update({key: value})
                elif resource_properties.get(key):
                    del resource_properties[key]

        _update(self.template, resource_id, resource_types, kwargs)

        for value in self.nested_templates.values():
            nested_template = value
            _update(nested_template, resource_id, resource_types, kwargs)
