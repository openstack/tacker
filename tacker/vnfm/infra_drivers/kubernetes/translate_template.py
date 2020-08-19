# All Rights Reserved.
#
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

import yaml

from oslo_config import cfg
from oslo_log import log as logging
from toscaparser.utils import yamlparser

from tacker.common import exceptions
from tacker.common import log
from tacker.extensions import common_services as cs
from tacker.extensions import vnfm
from tacker.vnfm.infra_drivers.kubernetes.k8s import translate_inputs
from tacker.vnfm.infra_drivers.kubernetes.k8s import translate_outputs

LOG = logging.getLogger(__name__)
CONF = cfg.CONF


class TOSCAToKubernetes(object):

    def __init__(self, vnf, core_v1_api_client,
                 app_v1_api_client, scaling_api_client):
        self.vnf = vnf
        self.core_v1_api_client = core_v1_api_client
        self.app_v1_api_client = app_v1_api_client
        self.scaling_api_client = scaling_api_client
        self.attributes = {}
        self.vnfd_yaml = None

    def generate_tosca_kube_objects(self):
        """Load TOSCA template and return tosca_kube_objects"""

        vnfd_dict = self.process_input()
        parser = translate_inputs.Parser(vnfd_dict)
        return parser.loader()

    def deploy_kubernetes_objects(self):
        """Translate tosca_kube_objects to Kubernetes objects and deploy them.

        Return a string that contains all deployment namespace and names
        """

        tosca_kube_objects = self.generate_tosca_kube_objects()
        transformer = translate_outputs.Transformer(
            core_v1_api_client=self.core_v1_api_client,
            app_v1_api_client=self.app_v1_api_client,
            scaling_api_client=self.scaling_api_client,
            k8s_client_dict=None
        )
        kubernetes_objects = transformer.transform(tosca_kube_objects)
        deployment_names = transformer.deploy(
            kubernetes_objects=kubernetes_objects)
        # return namespaces and service names for tracking resources
        return deployment_names

    def process_input(self):
        """Process input of vnfd template"""

        self.attributes = self.vnf['vnfd']['attributes'].copy()
        self.vnfd_yaml = self.attributes.pop('vnfd', None)
        if self.vnfd_yaml is None:
            LOG.error("VNFD is not provided, so no vnf is created !!")
            raise exceptions.InvalidInput("VNFD template is None.")
        LOG.debug('vnfd_yaml %s', self.vnfd_yaml)
        vnfd_dict = yamlparser.simple_ordered_parse(self.vnfd_yaml)
        LOG.debug('vnfd_dict %s', vnfd_dict)

        # Read parameter and process inputs
        if 'get_input' in str(vnfd_dict):
            self._process_parameterized_input(self.vnf['attributes'],
                                              vnfd_dict)
        return vnfd_dict

    @log.log
    def _update_params(self, original, paramvalues):
        for key, value in (original).items():
            if not isinstance(value, dict) or 'get_input' not in str(value):
                pass
            elif isinstance(value, dict):
                if 'get_input' in value:
                    if value['get_input'] in paramvalues:
                        original[key] = paramvalues[value['get_input']]
                    else:
                        LOG.debug('Key missing Value: %s', key)
                        raise cs.InputValuesMissing(key=key)
                else:
                    self._update_params(value, paramvalues)

    @log.log
    def _process_parameterized_input(self, attrs, vnfd_dict):
        param_vattrs_yaml = attrs.pop('param_values', None)
        if param_vattrs_yaml:
            try:
                param_vattrs_dict = yaml.safe_load(param_vattrs_yaml)
                LOG.debug('param_vattrs_yaml', param_vattrs_dict)
                for node in vnfd_dict['topology_template']['node_templates'].\
                        values():
                    if 'get_input' in str(node):
                        self._update_params(node, param_vattrs_dict)
            except Exception as e:
                LOG.debug("Not Well Formed: %s", str(e))
                raise vnfm.ParamYAMLNotWellFormed(
                    error_msg_details=str(e))
            else:
                self._update_params(vnfd_dict, param_vattrs_dict)
        else:
            raise cs.ParamYAMLInputMissing()
