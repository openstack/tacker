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

import time
import yaml

from kubernetes import client
from oslo_config import cfg
from oslo_log import log as logging
from oslo_serialization import jsonutils

from tacker.common.container import kubernetes_utils
from tacker.common import log
from tacker.common import utils
from tacker.extensions import vnfm
from tacker.vnfm.infra_drivers import abstract_driver
from tacker.vnfm.infra_drivers.kubernetes import translate_template
from tacker.vnfm.infra_drivers import scale_driver

LOG = logging.getLogger(__name__)
CONF = cfg.CONF

OPTS = [
    cfg.IntOpt('stack_retries',
               default=100,
               help=_("Number of attempts to retry for stack"
                      " creation/deletion")),
    cfg.IntOpt('stack_retry_wait',
               default=5,
               help=_("Wait time (in seconds) between consecutive stack"
                      " create/delete retries")),
]

CONF.register_opts(OPTS, group='kubernetes_vim')


def config_opts():
    return [('kubernetes_vim', OPTS)]


SCALING_POLICY = 'tosca.policies.tacker.Scaling'
COMMA_CHARACTER = ','


def get_scaling_policy_name(action, policy_name):
    return '%s_scale_%s' % (policy_name, action)


class Kubernetes(abstract_driver.VnfAbstractDriver,
                 scale_driver.VnfScaleAbstractDriver):
    """Kubernetes infra driver for hosting containerized vnfs"""

    def __init__(self):
        super(Kubernetes, self).__init__()
        self.STACK_RETRIES = cfg.CONF.kubernetes_vim.stack_retries
        self.STACK_RETRY_WAIT = cfg.CONF.kubernetes_vim.stack_retry_wait
        self.kubernetes = kubernetes_utils.KubernetesHTTPAPI()

    def get_type(self):
        return 'kubernetes'

    def get_name(self):
        return 'kubernetes'

    def get_description(self):
        return 'Kubernetes infra driver'

    @log.log
    def create(self, plugin, context, vnf, auth_attr):
        """Create function

        Create ConfigMap, Deployment, Service and Horizontal Pod Autoscaler
        objects. Return a string that contains all deployment namespace and
        names for tracking resources.
        """
        LOG.debug('vnf %s', vnf)
        # initialize Kubernetes APIs
        auth_cred, file_descriptor = self._get_auth_creds(auth_attr)
        try:
            core_v1_api_client = self.kubernetes.get_core_v1_api_client(
                auth=auth_cred)
            extension_api_client = self.kubernetes.get_extension_api_client(
                auth=auth_cred)
            scaling_api_client = self.kubernetes.get_scaling_api_client(
                auth=auth_cred)
            tosca_to_kubernetes = translate_template.TOSCAToKubernetes(
                vnf=vnf,
                core_v1_api_client=core_v1_api_client,
                extension_api_client=extension_api_client,
                scaling_api_client=scaling_api_client)
            deployment_names = tosca_to_kubernetes.deploy_kubernetes_objects()
        except Exception as e:
            LOG.error('Creating VNF got an error due to %s', e)
            raise
        finally:
            self.clean_authenticate_vim(auth_cred, file_descriptor)
        return deployment_names

    def create_wait(self, plugin, context, vnf_dict, vnf_id, auth_attr):
        """Create wait function

        Create wait function will marked VNF is ACTIVE when all status state
        from Pod objects is RUNNING.
        """
        # initialize Kubernetes APIs
        auth_cred, file_descriptor = self._get_auth_creds(auth_attr)
        try:
            core_v1_api_client = \
                self.kubernetes.get_core_v1_api_client(auth=auth_cred)
            deployment_info = vnf_id.split(COMMA_CHARACTER)
            mgmt_ips = dict()
            pods_information = self._get_pods_information(
                core_v1_api_client=core_v1_api_client,
                deployment_info=deployment_info)
            status = self._get_pod_status(pods_information)
            stack_retries = self.STACK_RETRIES
            error_reason = None
            while status == 'Pending' and stack_retries > 0:
                time.sleep(self.STACK_RETRY_WAIT)
                pods_information = \
                    self._get_pods_information(
                        core_v1_api_client=core_v1_api_client,
                        deployment_info=deployment_info)
                status = self._get_pod_status(pods_information)
                LOG.debug('status: %s', status)
                stack_retries = stack_retries - 1

            LOG.debug('VNF initializing status: %(service_name)s %(status)s',
                      {'service_name': str(deployment_info), 'status': status})
            if stack_retries == 0 and status != 'Running':
                error_reason = _("Resource creation is not completed within"
                                " {wait} seconds as creation of stack {stack}"
                                " is not completed").format(
                    wait=(self.STACK_RETRIES *
                          self.STACK_RETRY_WAIT),
                    stack=vnf_id)
                LOG.warning("VNF Creation failed: %(reason)s",
                            {'reason': error_reason})
                raise vnfm.VNFCreateWaitFailed(reason=error_reason)
            elif stack_retries != 0 and status != 'Running':
                raise vnfm.VNFCreateWaitFailed(reason=error_reason)

            for i in range(0, len(deployment_info), 2):
                namespace = deployment_info[i]
                deployment_name = deployment_info[i + 1]
                service_info = core_v1_api_client.read_namespaced_service(
                    name=deployment_name,
                    namespace=namespace)
                if service_info.metadata.labels.get("management_connection"):
                    vdu_name = service_info.metadata.labels.\
                        get("vdu_name").split("-")[1]
                    mgmt_ip = service_info.spec.cluster_ip
                    mgmt_ips.update({vdu_name: mgmt_ip})
                    vnf_dict['mgmt_ip_address'] = jsonutils.dump_as_bytes(
                        mgmt_ips)
        except Exception as e:
            LOG.error('Creating wait VNF got an error due to %s', e)
            raise
        finally:
            self.clean_authenticate_vim(auth_cred, file_descriptor)

    def _get_pods_information(self, core_v1_api_client, deployment_info):
        """Get pod information"""
        pods_information = list()
        for i in range(0, len(deployment_info), 2):
            namespace = deployment_info[i]
            deployment_name = deployment_info[i + 1]
            respone = \
                core_v1_api_client.list_namespaced_pod(namespace=namespace)
            for item in respone.items:
                if deployment_name in item.metadata.name:
                    pods_information.append(item)
        return pods_information

    def _get_pod_status(self, pods_information):
        pending_flag = False
        unknown_flag = False
        for pod_info in pods_information:
            status = pod_info.status.phase
            if status == 'Pending':
                pending_flag = True
            elif status == 'Unknown':
                unknown_flag = True
        if unknown_flag:
            status = 'Unknown'
        elif pending_flag:
            status = 'Pending'
        else:
            status = 'Running'
        return status

    @log.log
    def update(self, plugin, context, vnf_id, vnf_dict, vnf, auth_attr):
        """Update containerized VNF through ConfigMap data

        In Kubernetes VIM, updating VNF will be updated by updating
        ConfigMap data
        """
        # initialize Kubernetes APIs
        auth_cred, file_descriptor = self._get_auth_creds(auth_attr)
        try:
            core_v1_api_client = \
                self.kubernetes.get_core_v1_api_client(auth=auth_cred)

            # update config attribute
            config_yaml = vnf_dict.get('attributes', {}).get('config', '')
            update_yaml = vnf['vnf'].get('attributes', {}).get('config', '')
            LOG.debug('yaml orig %(orig)s update %(update)s',
                      {'orig': config_yaml, 'update': update_yaml})
            # If config_yaml is None, yaml.safe_load() will raise Attribute
            # Error. So set config_yaml to {}, if it is None.
            if not config_yaml:
                config_dict = {}
            else:
                config_dict = yaml.safe_load(config_yaml) or {}
            update_dict = yaml.safe_load(update_yaml)
            if not update_dict:
                return
            LOG.debug('dict orig %(orig)s update %(update)s',
                      {'orig': config_dict, 'update': update_dict})
            utils.deep_update(config_dict, update_dict)
            LOG.debug('dict new %(new)s update %(update)s',
                      {'new': config_dict, 'update': update_dict})
            new_yaml = yaml.safe_dump(config_dict)
            vnf_dict.setdefault('attributes', {})['config'] = new_yaml

            deployment_info = vnf_id.split(",")
            for i in range(0, len(deployment_info), 2):
                namespace = deployment_info[i]
                deployment_name = deployment_info[i + 1]
                configmap_resp = core_v1_api_client.read_namespaced_config_map(
                    namespace=namespace,
                    name=deployment_name)
                configmap_data = configmap_resp.data
                new_configmap = {key: update_dict.get(key, configmap_data[key])
                                 for key in configmap_data}
                configmap_resp.data = new_configmap
                core_v1_api_client.\
                    patch_namespaced_config_map(namespace=namespace,
                                                name=deployment_name,
                                                body=configmap_resp)
        except Exception as e:
            LOG.error('Updating VNF got an error due to %s', e)
            raise
        finally:
            self.clean_authenticate_vim(auth_cred, file_descriptor)

    @log.log
    def update_wait(self, plugin, context, vnf_id, auth_attr,
                    region_name=None):
        """Update wait function"""
        # TODO(phuoc): do nothing, will update it if we need actions
        pass

    def delete(self, plugin, context, vnf_id, auth_attr, region_name=None):
        """Delete function"""
        # initialize Kubernetes APIs
        auth_cred, file_descriptor = self._get_auth_creds(auth_attr)
        try:
            core_v1_api_client = self.kubernetes.get_core_v1_api_client(
                auth=auth_cred)
            extension_api_client = self.kubernetes.get_extension_api_client(
                auth=auth_cred)
            scaling_api_client = self.kubernetes.get_scaling_api_client(
                auth=auth_cred)
            deployment_names = vnf_id.split(COMMA_CHARACTER)

            for i in range(0, len(deployment_names), 2):
                namespace = deployment_names[i]
                deployment_name = deployment_names[i + 1]
                # delete ConfigMap if it exists
                try:
                    body = {}
                    core_v1_api_client.delete_namespaced_config_map(
                        namespace=namespace,
                        name=deployment_name,
                        body=body)
                    LOG.debug('Successfully deleted ConfigMap %s',
                              deployment_name)
                except Exception as e:
                    LOG.debug(e)
                    pass
                # delete Service if it exists
                try:
                    core_v1_api_client.delete_namespaced_service(
                        namespace=namespace,
                        name=deployment_name)
                    LOG.debug('Successfully deleted Service %s',
                              deployment_name)
                except Exception as e:
                    LOG.debug(e)
                    pass
                # delete Horizon Pod Auto-scaling if it exists
                try:
                    body = client.V1DeleteOptions()
                    scaling_api_client.\
                        delete_namespaced_horizontal_pod_autoscaler(
                            namespace=namespace,
                            name=deployment_name,
                            body=body)
                    LOG.debug('Successfully deleted Horizon Pod Auto-Scaling'
                              '%s', deployment_name)
                except Exception as e:
                    LOG.debug(e)
                    pass
                # delete Deployment if it exists
                try:
                    body = client.V1DeleteOptions(
                        propagation_policy='Foreground',
                        grace_period_seconds=5)
                    extension_api_client.delete_namespaced_deployment(
                        namespace=namespace,
                        name=deployment_name,
                        body=body)
                    LOG.debug('Successfully deleted Deployment %s',
                              deployment_name)
                except Exception as e:
                    LOG.debug(e)
                    pass
        except Exception as e:
            LOG.error('Deleting VNF got an error due to %s', e)
            raise
        finally:
            self.clean_authenticate_vim(auth_cred, file_descriptor)

    def delete_wait(self, plugin, context, vnf_id, auth_attr,
                    region_name=None):
        """Delete wait function

        This function is used to checking a containerized VNF is deleted
        completely or not. We do it by get information of Kubernetes objects.
        When Tacker can not get any information about service, the VNF will be
        marked as deleted.
        """
        # initialize Kubernetes APIs
        auth_cred, file_descriptor = self._get_auth_creds(auth_attr)
        try:
            core_v1_api_client = self.kubernetes.get_core_v1_api_client(
                auth=auth_cred)
            extension_api_client = self.kubernetes.get_extension_api_client(
                auth=auth_cred)
            scaling_api_client = self.kubernetes.get_scaling_api_client(
                auth=auth_cred)

            deployment_names = vnf_id.split(COMMA_CHARACTER)
            keep_going = True
            stack_retries = self.STACK_RETRIES
            while keep_going and stack_retries > 0:
                count = 0
                for i in range(0, len(deployment_names), 2):
                    namespace = deployment_names[i]
                    deployment_name = deployment_names[i + 1]
                    try:
                        core_v1_api_client.read_namespaced_config_map(
                            namespace=namespace,
                            name=deployment_name)
                        count = count + 1
                    except Exception:
                        pass
                    try:
                        core_v1_api_client.read_namespaced_service(
                            namespace=namespace,
                            name=deployment_name)
                        count = count + 1
                    except Exception:
                        pass
                    try:
                        scaling_api_client.\
                            read_namespaced_horizontal_pod_autoscaler(
                                namespace=namespace,
                                name=deployment_name)
                        count = count + 1
                    except Exception:
                        pass
                    try:
                        extension_api_client.read_namespaced_deployment(
                            namespace=namespace,
                            name=deployment_name)
                        count = count + 1
                    except Exception:
                        pass
                stack_retries = stack_retries - 1
                # If one of objects is still alive, keeps on waiting
                if count > 0:
                    keep_going = True
                else:
                    keep_going = False
        except Exception as e:
            LOG.error('Deleting wait VNF got an error due to %s', e)
            raise
        finally:
            self.clean_authenticate_vim(auth_cred, file_descriptor)

    @log.log
    def scale(self, context, plugin, auth_attr, policy, region_name):
        """Scale function

        Scaling VNF is implemented by updating replicas through Kubernetes API.
        The min_replicas and max_replicas is limited by the number of replicas
        of policy scaling when user define VNF descriptor.
        """
        LOG.debug("VNF are scaled by updating instance of deployment")
        # initialize Kubernetes APIs
        auth_cred, file_descriptor = self._get_auth_creds(auth_attr)
        try:
            extension_api_client = self.kubernetes.get_extension_api_client(
                auth=auth_cred)
            scaling_api_client = self.kubernetes.get_scaling_api_client(
                auth=auth_cred)
            deployment_names = policy['instance_id'].split(COMMA_CHARACTER)
            policy_name = policy['name']
            policy_action = policy['action']

            for i in range(0, len(deployment_names), 2):
                namespace = deployment_names[i]
                deployment_name = deployment_names[i + 1]
                deployment_info = extension_api_client.\
                    read_namespaced_deployment(namespace=namespace,
                                               name=deployment_name)
                scaling_info = scaling_api_client.\
                    read_namespaced_horizontal_pod_autoscaler(
                        namespace=namespace,
                        name=deployment_name)

                replicas = deployment_info.status.replicas
                scale_replicas = replicas
                vnf_scaling_name = deployment_info.metadata.labels.\
                    get("scaling_name")
                if vnf_scaling_name == policy_name:
                    if policy_action == 'out':
                        scale_replicas = replicas + 1
                    elif policy_action == 'in':
                        scale_replicas = replicas - 1

                min_replicas = scaling_info.spec.min_replicas
                max_replicas = scaling_info.spec.max_replicas
                if (scale_replicas < min_replicas) or \
                        (scale_replicas > max_replicas):
                    LOG.debug("Scaling replicas is out of range. The number of"
                              " replicas keeps %(number)s replicas",
                              {'number': replicas})
                    scale_replicas = replicas
                deployment_info.spec.replicas = scale_replicas
                extension_api_client.patch_namespaced_deployment_scale(
                    namespace=namespace,
                    name=deployment_name,
                    body=deployment_info)
        except Exception as e:
            LOG.error('Scaling VNF got an error due to %s', e)
            raise
        finally:
            self.clean_authenticate_vim(auth_cred, file_descriptor)

    def scale_wait(self, context, plugin, auth_attr, policy, region_name,
                   last_event_id):
        """Scale wait function

        Scale wait function will marked VNF is ACTIVE when all status state
        from Pod objects is RUNNING.
        """
        # initialize Kubernetes APIs
        auth_cred, file_descriptor = self._get_auth_creds(auth_attr)
        try:
            core_v1_api_client = self.kubernetes.get_core_v1_api_client(
                auth=auth_cred)
            deployment_info = policy['instance_id'].split(",")

            pods_information = self._get_pods_information(
                core_v1_api_client=core_v1_api_client,
                deployment_info=deployment_info)
            status = self._get_pod_status(pods_information)

            stack_retries = self.STACK_RETRIES
            error_reason = None
            while status == 'Pending' and stack_retries > 0:
                time.sleep(self.STACK_RETRY_WAIT)

                pods_information = self._get_pods_information(
                    core_v1_api_client=core_v1_api_client,
                    deployment_info=deployment_info)
                status = self._get_pod_status(pods_information)

                # LOG.debug('status: %s', status)
                stack_retries = stack_retries - 1

            LOG.debug('VNF initializing status: %(service_name)s %(status)s',
                      {'service_name': str(deployment_info), 'status': status})

            if stack_retries == 0 and status != 'Running':
                error_reason = _("Resource creation is not completed within"
                                 " {wait} seconds as creation of stack {stack}"
                                 " is not completed").format(
                    wait=(self.STACK_RETRIES *
                          self.STACK_RETRY_WAIT),
                    stack=policy['instance_id'])
                LOG.error("VNF Creation failed: %(reason)s",
                          {'reason': error_reason})
                raise vnfm.VNFCreateWaitFailed(reason=error_reason)

            elif stack_retries != 0 and status != 'Running':
                raise vnfm.VNFCreateWaitFailed(reason=error_reason)
        except Exception as e:
            LOG.error('Scaling wait VNF got an error due to %s', e)
            raise
        finally:
            self.clean_authenticate_vim(auth_cred, file_descriptor)

    @log.log
    def get_resource_info(self, plugin, context, vnf_info, auth_attr,
                          region_name=None):
        # TODO(phuoc): will update it for other components
        pass

    def _get_auth_creds(self, auth_cred):
        file_descriptor = self._create_ssl_ca_file(auth_cred)
        if ('username' not in auth_cred) and ('password' not in auth_cred):
            auth_cred['username'] = 'None'
            auth_cred['password'] = None
        return auth_cred, file_descriptor

    def _create_ssl_ca_file(self, auth_attr):
        ca_cert = auth_attr['ssl_ca_cert']
        if ca_cert is not None:
            file_descriptor, file_path = \
                self.kubernetes.create_ca_cert_tmp_file(ca_cert)
            auth_attr['ca_cert_file'] = file_path
            return file_descriptor
        else:
            return None

    def clean_authenticate_vim(self, vim_auth, file_descriptor):
        # remove ca_cert_file from vim_obj if it exists
        # close and delete temp ca_cert_file
        if file_descriptor is not None:
            file_path = vim_auth.pop('ca_cert_file')
            self.kubernetes.close_tmp_file(file_descriptor, file_path)

    def heal_vdu(self, plugin, context, vnf_dict, heal_request_data):
        pass
